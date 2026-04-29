import asyncio
import logging
from typing import List, Optional
from telethon import TelegramClient
from telethon.tl.types import User
from sqlalchemy.orm import Session
from sqlalchemy import select
from db.models import Account, Chat, Message, Contact
from db.session import SessionLocal
from parser.utils import (
    get_or_create_chat,
    extract_message_data,
    batch_insert_messages,
    RateLimiter,
    update_chat_sync
)
from config import settings

logger = logging.getLogger(__name__)


class MessageLoader:
    """Loads all messages from personal dialogs into database"""
    
    def __init__(self, client: TelegramClient):
        self.client = client
        self.rate_limiter = RateLimiter(max_requests=100, window_seconds=1)
        self.db = SessionLocal()
    
    async def load_all_dialogs(
        self,
        limit_dialogs: int = None,
        include_groups: bool = False,
        include_bots: bool = False,
        include_channels: bool = False,
    ) -> int:
        """
        Enumerate all dialogs and load their message history.
        Args:
            limit_dialogs: Limit number of dialogs to process (for testing)
            include_groups: Also load group chats
            include_bots: Also load bot dialogs
            include_channels: Also load channel dialogs
        Returns: Total number of messages loaded
        """
        try:
            # Get or create account record
            me = await self.client.get_me()
            account = self._get_or_create_account(me)
            
            logger.info(f"Starting message export for account: {me.username or me.first_name}")
            if include_groups:
                logger.info("Groups mode enabled")
            if include_bots:
                logger.info("Bots mode enabled")
            if include_channels:
                logger.info("Channels mode enabled")
            if limit_dialogs:
                logger.info(f"(Test mode: limiting to {limit_dialogs} dialogs)")
            
            total_messages = 0
            dialog_count = 0
            skipped_count = 0

            def _progress(extra=""):
                bar = f"  📥 Chats: {dialog_count:>4} | Messages: {total_messages:>7,} | Skipped: {skipped_count:>4}"
                if extra:
                    bar += f"  ← {extra}"
                print(bar, flush=True)

            # Iterate through all dialogs
            async for dialog in self.client.iter_dialogs():
                # Stop if limit reached
                if limit_dialogs and dialog_count >= limit_dialogs:
                    break

                # Skip bot dialogs unless explicitly requested
                if getattr(dialog.entity, 'bot', False) and not include_bots:
                    logger.debug(f"Skipping bot dialog: {dialog.name}")
                    skipped_count += 1
                    continue

                # Skip broadcast channels unless explicitly requested.
                # Some group-like dialogs are channel-based in Telegram,
                # so we treat pure channels separately from groups.
                if dialog.is_channel and not dialog.is_group and not include_channels:
                    logger.debug(f"Skipping channel: {dialog.name}")
                    skipped_count += 1
                    continue

                # Skip groups unless include_groups is set
                if dialog.is_group and not include_groups:
                    logger.debug(f"Skipping group: {dialog.name}")
                    skipped_count += 1
                    continue
                
                dialog_count += 1
                _progress(dialog.name[:40] if dialog.name else "")

                # Load messages from this dialog
                is_group = bool(dialog.is_group)
                messages_loaded = await self._load_dialog_messages(
                    account.id,
                    dialog.id,
                    me.id,
                    is_group=is_group
                )
                total_messages += messages_loaded
                _progress(dialog.name[:40] if dialog.name else "")
                
                # Small delay between dialogs to respect rate limits
                await asyncio.sleep(0.1)
            
            print("")
            logger.info(
                f"✓ Export complete: {dialog_count} dialogs, {total_messages:,} total messages (skipped: {skipped_count})"
            )
            return total_messages
            
        except Exception as e:
            logger.error(f"Error during dialog loading: {e}", exc_info=True)
            raise
        finally:
            self.db.close()
    
    async def _load_dialog_messages(
        self,
        account_id: int,
        dialog_id: int,
        my_id: int,
        is_group: bool = False,
    ) -> int:
        """Load all messages from a single dialog"""
        try:
            db = SessionLocal()
            
            # Get or create chat record
            chat_entity = await self.client.get_entity(dialog_id)
            contact_username = getattr(chat_entity, 'username', None)
            chat_title = getattr(chat_entity, 'title', None)  # for groups
            display_name = chat_title or contact_username
            
            chat = await get_or_create_chat(
                db,
                account_id,
                dialog_id,
                contact_username,
                is_group=is_group,
                title=chat_title,
            )
            
            messages_to_insert = []
            message_count = 0
            last_message_id = None
            
            # Fetch all messages from this dialog
            async for message in self.client.iter_messages(
                dialog_id,
                reverse=False,  # Start from oldest
                limit=None  # No limit, get everything
            ):
                await self.rate_limiter.wait()
                
                # Extract message data
                message_data = extract_message_data(
                    account_id,
                    chat.id,
                    message,
                    message.sender_id or my_id
                )
                messages_to_insert.append(message_data)
                last_message_id = message.id
                message_count += 1
                
                # Insert in batches
                if len(messages_to_insert) >= settings.batch_size:
                    await batch_insert_messages(messages_to_insert)
                    messages_to_insert = []
            
            # Insert remaining messages
            if messages_to_insert:
                await batch_insert_messages(messages_to_insert)
            
            # Update chat metadata
            if last_message_id:
                await update_chat_sync(db, chat.id, last_message_id)
            
            logger.debug(f"Loaded {message_count} messages from dialog {dialog_id}")
            db.close()
            return message_count
            
        except Exception as e:
            logger.error(f"Error loading messages from dialog {dialog_id}: {e}")
            db.close()
            return 0
    
    def _get_or_create_account(self, me: User) -> Account:
        """Get or create account record"""
        stmt = select(Account).where(Account.telegram_id == me.id)
        account = self.db.execute(stmt).scalar_one_or_none()
        
        if not account:
            account = Account(
                telegram_id=me.id,
                phone_number=me.phone,
                username=me.username,
                first_name=me.first_name,
                last_name=me.last_name
            )
            self.db.add(account)
            self.db.commit()
            logger.info(f"Created account record for {me.username or me.first_name}")
        else:
            logger.info(f"Found existing account record")
        
        return account
