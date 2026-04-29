# Telegram Export & Sync System - Project Instructions

## Project Overview
Python-based system to export complete Telegram personal chat history (~1000 dialogs) into PostgreSQL database and maintain real-time synchronization.

## Technology Stack
- **Language**: Python 3.10+
- **Database**: PostgreSQL 14+
- **Async Framework**: asyncio + Telethon
- **ORM**: SQLAlchemy 2.x with Alembic migrations
- **Config**: python-dotenv

## Project Structure
```
telegram-export/
├── .env
├── .env.example
├── requirements.txt
├── config.py
├── main.py
├── export.py
├── db/
│   ├── __init__.py
│   ├── models.py
│   ├── session.py
│   └── schema.sql
├── parser/
│   ├── __init__.py
│   ├── client.py
│   ├── loader.py
│   ├── syncer.py
│   └── utils.py
└── migrations/
    └── versions/
```

## Setup Requirements
1. PostgreSQL 14+ installed and running
2. Python 3.10+
3. Telegram account credentials (API_ID, API_HASH from https://my.telegram.org)

## Key Implementation Notes
- Only parse personal (1-to-1) dialogs, skip groups and channels
- Store only message metadata (file_ids), don't download media files
- Implement automatic retry and rate limiting
- Support full history export + real-time synchronization
