#!/bin/bash
# Quick Setup Checklist - Run these commands in order

echo "Telegram Export & Sync - Quick Setup"
echo "===================================="
echo ""

# Step 1: PostgreSQL
echo "[ ] Step 1: Create PostgreSQL database"
echo "Run: createdb telegram_export"
echo ""

# Step 2: Environment
echo "[ ] Step 2: Create .env file with your credentials"
echo "Run: cp .env.example .env"
echo "Then edit .env with:"
echo "  - API_ID (from https://my.telegram.org)"
echo "  - API_HASH (from https://my.telegram.org)"
echo "  - TELEGRAM_PHONE (+1234567890 format)"
echo "  - DATABASE_URL (if not localhost)"
echo ""

# Step 3: Activate venv
echo "[ ] Step 3: Activate Python virtual environment"
echo "Run: source venv/bin/activate"
echo ""

# Step 4: Initialize database
echo "[ ] Step 4: Initialize database schema"
echo "Run: python main.py init-db"
echo ""

# Step 5: Load messages
echo "[ ] Step 5: Load all messages from Telegram"
echo "Run: python main.py load"
echo "This may take 2-8 hours depending on message count"
echo ""

# Step 6: Start sync
echo "[ ] Step 6: (Optional) Start real-time sync"
echo "Run: python main.py sync"
echo "Keep this running in background with 'screen' or 'tmux'"
echo ""

# Step 7: Export
echo "[ ] Step 7: Export your data"
echo "Run: python main.py export json"
echo "Or:  python main.py export csv"
echo ""

echo "Setup checklist complete!"
echo ""
echo "For more details, see SETUP.md or README.md"
