import asyncio
import logging
import sys
import structlog
from pathlib import Path

from config import settings
from db.session import engine, Base
from db.models import Account, Chat, Message, Contact
from parser.client import client_manager
from parser.loader import MessageLoader
from parser.syncer import MessageSyncer
from parser.downloader import VoiceDownloader
from export import DataExporter

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
)

logger = logging.getLogger(__name__)


async def init_database():
    """Initialize database schema"""
    logger.info("Initializing database schema...")
    Base.metadata.create_all(engine)
    logger.info("✓ Database schema created/verified")


async def load_command(limit_dialogs: int = None, include_groups: bool = False):
    """Load all messages from Telegram dialogs"""
    if limit_dialogs:
        logger.info(f"TEST MODE: Loading max {limit_dialogs} dialogs")
    else:
        logger.info("Starting full message export...")
    
    try:
        await init_database()
        
        client = await client_manager.initialize()
        loader = MessageLoader(client)
        
        total_messages = await loader.load_all_dialogs(
            limit_dialogs=limit_dialogs,
            include_groups=include_groups,
        )
        
        logger.info(f"✓ Export complete: {total_messages} messages loaded")
        
        # Show export stats
        stats = DataExporter.get_export_stats()
        logger.info(f"Export stats: {stats}")
        
        await client_manager.disconnect()
        
    except Exception as e:
        logger.error(f"Error during load: {e}", exc_info=True)
        sys.exit(1)


async def sync_command():
    """Start real-time message synchronization"""
    logger.info("Starting real-time synchronization...")
    
    try:
        await init_database()
        
        client = await client_manager.initialize()
        syncer = MessageSyncer(client)
        
        await syncer.start_sync()
        
    except KeyboardInterrupt:
        logger.info("Sync interrupted by user")
    except Exception as e:
        logger.error(f"Error during sync: {e}", exc_info=True)
        sys.exit(1)


def export_command(format: str = "json"):
    """Export messages to file"""
    logger.info(f"Exporting messages to {format.upper()}...")
    
    try:
        if format.lower() == "json":
            file_path = DataExporter.export_to_json()
        elif format.lower() == "csv":
            file_path = DataExporter.export_to_csv()
        else:
            logger.error(f"Unknown format: {format}")
            sys.exit(1)
        
        logger.info(f"✓ Export complete: {file_path}")
        
    except Exception as e:
        logger.error(f"Error during export: {e}", exc_info=True)
        sys.exit(1)


def stats_command():
    """Show export statistics"""
    try:
        stats = DataExporter.get_export_stats()
        logger.info(f"Export Statistics:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        sys.exit(1)


async def download_voices_command(username: str):
    """Download voice messages for a specific contact"""
    logger.info(f"Downloading voice messages from @{username}...")
    try:
        await init_database()
        client = await client_manager.initialize()
        downloader = VoiceDownloader(client)
        count = await downloader.download_voices_for_contact(username)
        logger.info(f"✓ Downloaded {count} voice messages")
        await client_manager.disconnect()
    except Exception as e:
        logger.error(f"Error downloading voices: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("""
Telegram Export & Sync Tool

Usage:
  python main.py load [limit]        - Load messages (optionally limit dialogs for testing)
  python main.py sync                - Start real-time synchronization
  python main.py export json|csv     - Export messages to JSON or CSV
  python main.py stats               - Show export statistics
  python main.py init-db             - Initialize database schema
  python main.py download-voice @username - Download voice messages from contact

Examples:
  python main.py load                # Load all dialogs
  python main.py load 10             # Load only 10 dialogs (for testing)
  python main.py download-voice mikekosarev  # Download voices from @mikekosarev
        """)
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command == "load":
        limit_dialogs = None
        include_groups = "--groups" in sys.argv
        args = [a for a in sys.argv[2:] if not a.startswith("--")]
        if args:
            try:
                limit_dialogs = int(args[0])
            except ValueError:
                logger.error(f"Invalid limit: {args[0]}")
                sys.exit(1)
        asyncio.run(load_command(limit_dialogs=limit_dialogs, include_groups=include_groups))
    elif command == "sync":
        asyncio.run(sync_command())
    elif command == "export":
        format = sys.argv[2] if len(sys.argv) > 2 else "json"
        export_command(format)
    elif command == "stats":
        stats_command()
    elif command == "init-db":
        asyncio.run(init_database())
    elif command == "download-voice":
        if len(sys.argv) < 3:
            logger.error("Usage: python main.py download-voice <username>")
            sys.exit(1)
        username = sys.argv[2].lstrip('@')
        asyncio.run(download_voices_command(username))
    else:
        logger.error(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
