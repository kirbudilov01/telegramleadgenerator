from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseSettings):
    # Telegram API
    api_id: int = int(os.getenv("API_ID", "0"))
    api_hash: str = os.getenv("API_HASH", "")
    telegram_phone: str = os.getenv("TELEGRAM_PHONE", "")
    
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/telegram_export"
    )
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Parser settings
    max_workers: int = int(os.getenv("MAX_WORKERS", "5"))
    batch_size: int = int(os.getenv("BATCH_SIZE", "1000"))
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
