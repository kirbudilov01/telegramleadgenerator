# Setup Instructions

Follow these steps to get the Telegram Export & Sync system up and running.

## 1. Prerequisites

- Python 3.10+ (tested with 3.14.3)
- PostgreSQL 14+ installed and running
- Telegram account with API credentials

## 2. Install Dependencies

```bash
# The dependencies are already installed in venv
# If needed, reinstall:
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Get Telegram API Credentials

1. Visit https://my.telegram.org
2. Sign in with your Telegram phone number
3. Go to "API development tools"
4. Create a new application
5. Note your:
   - API_ID
   - API_HASH
   - Phone number (use format: +1234567890)

## 4. Configure Environment

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit `.env` with your actual credentials:
```
API_ID=your_api_id_here
API_HASH=your_api_hash_here
TELEGRAM_PHONE=+1234567890
DATABASE_URL=postgresql://username:password@localhost:5432/telegram_export
LOG_LEVEL=INFO
```

### Database Setup

Create PostgreSQL database:
```bash
# Using psql
createdb telegram_export

# Or if you need to specify user:
createdb -U postgres telegram_export
```

## 5. Initialize Database Schema

```bash
source venv/bin/activate
python main.py init-db
```

This creates all necessary tables in PostgreSQL.

## 6. Test Configuration

```bash
source venv/bin/activate
python main.py stats
```

If this works without errors, your setup is complete!

## 7. Start Exporting

### Full History Export (One-time)

```bash
python main.py load
```

**Important**: First time running this will:
- Show your account info
- Might ask for 2FA code if enabled on your Telegram
- Enumerate all your personal dialogs
- Load entire message history (this takes time depending on message count)

Typical timeline for 1000 dialogs with 100k+ messages: 2-8 hours

### Real-time Synchronization

After the initial load, start real-time sync:

```bash
python main.py sync
```

This will:
- Listen for new incoming messages in personal chats
- Automatically save them to the database
- Run in the background indefinitely (until you press Ctrl+C)

You can run this in a `screen` or `tmux` session to keep it running.

### Export Data

```bash
# Export to JSON
python main.py export json

# Export to CSV
python main.py export csv
```

Files appear in `./exports/` directory.

## 8. Check Progress

```bash
python main.py stats
```

Shows:
- Total chats processed
- Total messages exported
- Messages with media
- Edit and forward statistics

## Troubleshooting

### "Connection refused" to PostgreSQL
- Ensure PostgreSQL is running: `brew services start postgresql@14`
- Check DATABASE_URL in .env
- Verify database exists: `psql -l`

### "Flood wait" errors during export
- Normal! Telethon handles this automatically
- It will backoff and retry
- Consider running export overnight for large accounts

### Session file errors
- Delete `telegram_session.session` and re-run
- You'll need to authenticate again with phone + code

### Out of memory
- The system batches inserts (1000 at a time)
- If still hitting memory issues, reduce BATCH_SIZE in .env

## Next Steps

1. Verify PostgreSQL is running
2. Create your `.env` file with Telegram credentials
3. Run `python main.py init-db` to initialize database
4. Run `python main.py load` to export your message history
5. Run `python main.py sync` in background to keep it updated

Good luck!
