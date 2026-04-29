import asyncio
import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, update, desc, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from db.models import Chat, Message, Contact, Account
from db.session import SessionLocal
from config import settings

logger = logging.getLogger(__name__)


async def batch_insert_messages(messages: List[dict], batch_size: int = 1000) -> int:
    """Insert messages in batches, skipping duplicates. Returns number inserted."""
    db = SessionLocal()
    total_inserted = 0
    try:
        for i in range(0, len(messages), batch_size):
            batch = messages[i : i + batch_size]
            stmt = pg_insert(Message).values(batch).on_conflict_do_nothing(
                index_elements=['account_id', 'chat_id', 'message_id']
            )
            result = db.execute(stmt)
            db.commit()
            inserted = result.rowcount
            total_inserted += inserted
            logger.info(f"Batch: {inserted}/{len(batch)} new messages inserted")
        return total_inserted
    except Exception as e:
        db.rollback()
        logger.error(f"Error inserting messages: {e}")
        raise
    finally:
        db.close()


async def get_or_create_chat(
    db: Session,
    account_id: int,
    chat_id: int,
    contact_username: Optional[str] = None,
    is_group: bool = False,
    title: Optional[str] = None,
) -> Chat:
    """Get existing chat or create new one"""
    stmt = select(Chat).where(
        (Chat.account_id == account_id) & (Chat.chat_id == chat_id)
    )
    chat = db.execute(stmt).scalar_one_or_none()
    
    if not chat:
        chat = Chat(
            account_id=account_id,
            chat_id=chat_id,
            contact_username=contact_username or title,
            is_user=not is_group,
        )
        db.add(chat)
        db.commit()
        logger.info(f"Created new chat entry for chat_id={chat_id}")
    
    return chat


async def update_chat_sync(
    db: Session,
    chat_id: int,
    last_message_id: int
):
    """Update last_synced timestamp and last_message_id for a chat"""
    stmt = update(Chat).where(Chat.id == chat_id).values(
        last_message_id=last_message_id,
        last_synced=func.now()
    )
    db.execute(stmt)
    db.commit()


def extract_media_info(message) -> dict:
    """Extract media metadata from a Telegram message"""
    media_info = {
        'has_media': False,
        'media_type': None,
        'media_file_id': None,
        'media_size': None,
    }
    
    if message.media:
        media_info['has_media'] = True
        
        if message.photo:
            media_info['media_type'] = 'photo'
            media_info['media_file_id'] = str(message.photo.id)
            media_info['media_size'] = message.photo.size if hasattr(message.photo, 'size') else None
        elif message.document:
            media_info['media_type'] = 'document'
            media_info['media_file_id'] = message.document.id
            media_info['media_size'] = message.document.size
        elif message.video:
            media_info['media_type'] = 'video'
            media_info['media_file_id'] = message.video.id
            media_info['media_size'] = message.video.size
        elif message.audio:
            media_info['media_type'] = 'audio'
            media_info['media_file_id'] = message.audio.id
            media_info['media_size'] = message.audio.size
        elif message.voice:
            media_info['media_type'] = 'voice'
            media_info['media_file_id'] = message.voice.id
            media_info['media_size'] = message.voice.size
        else:
            media_info['media_type'] = 'other'
    
    return media_info


def extract_message_data(
    account_id: int,
    chat_db_id: int,
    message,
    sender_id: int
) -> dict:
    """Convert Telegram message to database record format"""
    media_info = extract_media_info(message)
    
    # Extract reply_to_msg_id safely (handles different reply_to types)
    reply_to_msg_id = None
    if message.reply_to:
        try:
            reply_to_msg_id = message.reply_to.reply_to_msg_id
        except AttributeError:
            # Some reply types (like MessageReplyStoryHeader) don't have reply_to_msg_id
            pass
    
    return {
        'account_id': account_id,
        'chat_id': chat_db_id,
        'message_id': message.id,
        'sender_id': sender_id,
        'text': message.text or message.raw_text,
        'timestamp': message.date,
        'has_media': media_info['has_media'],
        'media_type': media_info['media_type'],
        'media_file_id': media_info['media_file_id'],
        'media_size': media_info['media_size'],
        'is_edited': message.edit_date is not None,
        'is_forwarded': message.forward is not None,
        'reply_to_msg_id': reply_to_msg_id,
    }


class RateLimiter:
    """Simple rate limiter to avoid flood control"""
    def __init__(self, max_requests: int = 100, window_seconds: int = 1):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
    
    async def wait(self):
        """Wait if necessary to respect rate limits"""
        now = asyncio.get_event_loop().time()
        # Remove old requests outside the window
        self.requests = [t for t in self.requests if t > now - self.window_seconds]
        
        if len(self.requests) >= self.max_requests:
            sleep_time = self.requests[0] + self.window_seconds - now
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        self.requests.append(now)
