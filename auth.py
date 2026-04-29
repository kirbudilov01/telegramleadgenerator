"""
One-time interactive authentication script.
Run this once to create/refresh the telegram_session.session file.
After this, 'python main.py load' can run headlessly.
"""
import asyncio
from telethon import TelegramClient
from config import settings


async def main():
    client = TelegramClient("telegram_session", settings.api_id, settings.api_hash)
    await client.start(phone=settings.telegram_phone)
    me = await client.get_me()
    print(f"✓ Authenticated as: {me.first_name} (@{me.username})")
    print("Session saved to telegram_session.session")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
