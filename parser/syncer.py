import asyncio
import logging
from telethon import TelegramClient
from telethon.events import NewMessage
from sqlalchemy.orm import Session
from db.models import Account, Chat
from db.session import SessionLocal
from parser.utils import get_or_create_chat, extract_message_data, RateLimiter
from sqlalchemy import select

logger = logging.getLogger(__name__)


class MessageSyncer:
    """Real-time message synchronization from Telegram"""
    
    def __init__(self, client: TelegramClient):
        self.client = client
        self.running = False
        self.rate_limiter = RateLimiter(max_requests=50, window_seconds=1)
    
    async def start_sync(self):
        """Start listening for new messages"""
        self.running = True
        logger.info("Starting real-time message synchronization")
        
        @self.client.on(NewMessage)
        async def handle_new_message(event):
            await self._process_new_message(event)
        
        # Keep the event handler active
        while self.running:
            await asyncio.sleep(1)
    
    async def stop_sync(self):
        """Stop listening for new messages"""
        self.running = False
        logger.info("Stopped message synchronization")
    
    async def _process_new_message(self, event):
        """Process and store a new message"""
        try:
            # Skip messages from groups and channels
            if event.is_group or event.is_channel:
                return
            
            message = event.message
            chat_id = event.chat_id
            
            await self.rate_limiter.wait()
            
            db = SessionLocal()
            try:
                # Get sender ID
                sender_id = message.sender_id
                if sender_id is None:
                    # For saved messages, use account ID
                    sender_id = (await self.client.get_me()).id
                
                # Get account
                me = await self.client.get_me()
                stmt = select(Account).where(Account.telegram_id == me.id)
                account = db.execute(stmt).scalar_one_or_none()
                
                if not account:
                    logger.warning(f"Account not found, skipping message")
                    return
                
                # Get or create chat
                chat = await get_or_create_chat(
                    db,
                    account.id,
                    chat_id
                )
                
                # Extract message data
                message_data = extract_message_data(
                    account.id,
                    chat.id,
                    message,
                    sender_id
                )
                
                # Save to database
                from db.models import Message
                msg_record = Message(**message_data)
                db.add(msg_record)
                db.commit()
                
                logger.debug(f"Synced message {message.id} from chat {chat_id}")
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error processing new message: {e}")
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"Error in handle_new_message: {e}", exc_info=True)
