import asyncio
import logging
from pathlib import Path
from telethon import TelegramClient
from sqlalchemy import select, update
from db.models import Account, Chat, Message
from db.session import SessionLocal

logger = logging.getLogger(__name__)


class VoiceDownloader:
    """Downloads voice messages for specific contacts"""

    def __init__(self, client: TelegramClient, output_dir: str = "./media/voices"):
        self.client = client
        self.output_dir = Path(output_dir)

    async def download_voices_for_contact(self, username: str) -> int:
        """
        Download all voice messages from a specific contact.
        Returns number of files downloaded.
        """
        db = SessionLocal()
        try:
            # Find account
            me = await self.client.get_me()
            stmt = select(Account).where(Account.telegram_id == me.id)
            account = db.execute(stmt).scalar_one_or_none()
            if not account:
                logger.error("No account found in DB, run 'load' first")
                return 0

            # Find chat by username
            stmt = select(Chat).where(
                (Chat.account_id == account.id) &
                (Chat.contact_username == username.lstrip('@'))
            )
            chat = db.execute(stmt).scalar_one_or_none()
            if not chat:
                logger.error(f"Chat with @{username} not found in DB")
                return 0

            # Create output directory for this contact
            contact_dir = self.output_dir / username.lstrip('@')
            contact_dir.mkdir(parents=True, exist_ok=True)

            # Find all voice messages not yet downloaded
            stmt = select(Message).where(
                (Message.chat_id == chat.id) &
                (Message.media_type == 'voice') &
                (Message.media_local_path == None)
            ).order_by(Message.timestamp)
            voice_messages = db.execute(stmt).scalars().all()

            total = len(voice_messages)
            if total == 0:
                logger.info(f"No voice messages to download for @{username}")
                return 0

            logger.info(f"Found {total} voice messages from @{username}, starting download...")
            downloaded = 0

            for i, msg in enumerate(voice_messages, 1):
                try:
                    # Get the actual Telegram message to download from
                    tg_msg = await self.client.get_messages(
                        chat.chat_id, ids=msg.message_id
                    )
                    if not tg_msg or not tg_msg.voice:
                        logger.debug(f"Message {msg.message_id} has no voice, skipping")
                        continue

                    # Download to local file
                    filename = f"{msg.timestamp.strftime('%Y%m%d_%H%M%S')}_{msg.message_id}.ogg"
                    local_path = contact_dir / filename

                    if local_path.exists():
                        # Already downloaded, just update DB
                        db.execute(
                            update(Message).where(Message.id == msg.id).values(
                                media_local_path=str(local_path)
                            )
                        )
                        db.commit()
                        downloaded += 1
                        continue

                    await self.client.download_media(tg_msg, file=str(local_path))

                    # Update DB with local path
                    db.execute(
                        update(Message).where(Message.id == msg.id).values(
                            media_local_path=str(local_path)
                        )
                    )
                    db.commit()
                    downloaded += 1

                    if i % 50 == 0 or i == total:
                        logger.info(f"  Progress: {i}/{total} ({downloaded} downloaded)")

                    # Small delay to respect rate limits
                    await asyncio.sleep(0.3)

                except Exception as e:
                    logger.error(f"Error downloading voice {msg.message_id}: {e}")
                    continue

            logger.info(f"✓ Done: {downloaded}/{total} voice messages downloaded to {contact_dir}")
            return downloaded

        finally:
            db.close()
