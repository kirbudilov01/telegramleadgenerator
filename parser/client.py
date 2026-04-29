import asyncio
import logging
from typing import Optional
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from config import settings

logger = logging.getLogger(__name__)


class TelegramClientManager:
    """Manages Telethon client connection and authentication"""
    
    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self.session_file = "telegram_session"
    
    async def initialize(self) -> TelegramClient:
        """Initialize and authenticate Telegram client using existing session (no interactive auth)"""
        self.client = TelegramClient(
            self.session_file,
            settings.api_id,
            settings.api_hash
        )

        await self.client.connect()

        if not await self.client.is_user_authorized():
            await self.client.disconnect()
            raise RuntimeError(
                "Telegram session is not authorized. "
                "Run 'python auth.py' first to create a valid session."
            )

        logger.info("Telegram client connected using existing session")
        return self.client
    
    async def disconnect(self):
        """Gracefully disconnect the client"""
        if self.client:
            await self.client.disconnect()
            logger.info("Telegram client disconnected")
    
    async def is_authenticated(self) -> bool:
        """Check if client is authenticated"""
        try:
            me = await self.client.get_me()
            return me is not None
        except Exception:
            return False
    
    async def get_client(self) -> TelegramClient:
        """Get the authenticated client"""
        if not self.client:
            await self.initialize()
        return self.client


# Global instance
client_manager = TelegramClientManager()
