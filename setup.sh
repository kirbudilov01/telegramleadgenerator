#!/bin/bash
set -e

# ─── Colors ─────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
say()  { echo -e "\n${YELLOW}▶${NC} ${BOLD}$1${NC}"; }
hint() { echo -e "  ${CYAN}ℹ${NC}  $1"; }
err()  { echo -e "\n${RED}✗ ERROR:${NC} $1"; exit 1; }
step() { echo -e "\n${BOLD}${YELLOW}[$1/8]${NC} ${BOLD}$2${NC}"; }

clear
echo ""
echo -e "${YELLOW}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║                                                          ║${NC}"
echo -e "${YELLOW}║   📊  Telegram Lead Generator — Setup                   ║${NC}"
echo -e "${YELLOW}║          by FABRICBOT ECOSYSTEM                         ║${NC}"
echo -e "${YELLOW}║                                                          ║${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  This script will install everything automatically:"
echo "  Homebrew → Python 3.11 → PostgreSQL → dependencies → auth"
echo ""
echo -e "  ${BOLD}Before you begin, make sure you have:${NC}"
echo ""
echo "  1. A Telegram account (phone number with country code)"
echo "  2. API credentials from https://my.telegram.org"
echo "     → Log in → API development tools → Create app"
echo "     → Copy  App api_id  and  App api_hash"
echo ""
read -p "  Press Enter to start setup..." _

# ─── 1. Homebrew ─────────────────────────────────────────────────────────────
step 1 "Homebrew (macOS package manager)"
if ! command -v brew &>/dev/null; then
    hint "Homebrew not found — installing (may ask for your password)..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if [[ -f /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
    fi
fi
ok "Homebrew ready"

# ─── 2. Python ───────────────────────────────────────────────────────────────
step 2 "Python 3.11"
if ! brew list python@3.11 &>/dev/null; then
    hint "Installing Python 3.11..."
    brew install python@3.11
fi
PYTHON=$(brew --prefix python@3.11)/bin/python3.11
ok "Python: $($PYTHON --version)"

# ─── 3. PostgreSQL ───────────────────────────────────────────────────────────
step 3 "PostgreSQL (local database)"
if ! brew list postgresql@18 &>/dev/null 2>&1; then
    if ! brew list postgresql@16 &>/dev/null 2>&1; then
        hint "Installing PostgreSQL 18..."
        brew install postgresql@18
    fi
fi

if ! pg_isready -q 2>/dev/null; then
    hint "Starting PostgreSQL..."
    brew services start postgresql@18 2>/dev/null || brew services start postgresql@16 2>/dev/null || true
    sleep 2
fi

if pg_isready -q 2>/dev/null; then
    ok "PostgreSQL is running"
else
    err "PostgreSQL failed to start. Try manually: brew services start postgresql@18"
fi

# ─── 4. Python venv + deps ───────────────────────────────────────────────────
step 4 "Python dependencies"
if [ ! -d "venv" ]; then
    hint "Creating virtual environment..."
    $PYTHON -m venv venv
fi
source venv/bin/activate
hint "Installing packages (Telethon, SQLAlchemy, psycopg2...)..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
ok "All packages installed"

# ─── 5. Database ─────────────────────────────────────────────────────────────
step 5 "Database"
createdb telegram_export 2>/dev/null && ok "Database 'telegram_export' created" || ok "Database 'telegram_export' already exists"

# ─── 6. API credentials ──────────────────────────────────────────────────────
step 6 "Telegram API credentials"

if [ ! -f ".env" ]; then
    cp .env.example .env
fi

source_val() { grep "^$1=" .env 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'"; }
CUR_API_ID=$(source_val API_ID)
CUR_API_HASH=$(source_val API_HASH)
CUR_PHONE=$(source_val TELEGRAM_PHONE)

# --- API_ID ---
if [ -z "$CUR_API_ID" ]; then
    echo ""
    echo -e "  ${BOLD}How to get API_ID and API_HASH:${NC}"
    echo ""
    hint "1. Open in your browser:   https://my.telegram.org"
    hint "2. Sign in with your phone number"
    hint "3. Click  \"API development tools\""
    hint "4. Create an app — any name works (e.g. MyLeads)"
    hint "5. Copy  App api_id  and  App api_hash"
    echo ""
    read -p "  Enter API_ID (numbers only): " INPUT_API_ID
    while ! [[ "$INPUT_API_ID" =~ ^[0-9]+$ ]]; do
        echo -e "  ${RED}✗${NC} API_ID must be numbers only. Try again."
        read -p "  Enter API_ID: " INPUT_API_ID
    done
    if grep -q "^API_ID=" .env; then
        sed -i '' "s|^API_ID=.*|API_ID=$INPUT_API_ID|" .env
    else
        echo "API_ID=$INPUT_API_ID" >> .env
    fi
    ok "API_ID saved"
else
    ok "API_ID already set ($CUR_API_ID)"
fi

# --- API_HASH ---
if [ -z "$CUR_API_HASH" ]; then
    echo ""
    read -p "  Enter API_HASH (32-char string): " INPUT_API_HASH
    while [ ${#INPUT_API_HASH} -lt 10 ]; do
        echo -e "  ${RED}✗${NC} API_HASH looks too short. Try again."
        read -p "  Enter API_HASH: " INPUT_API_HASH
    done
    if grep -q "^API_HASH=" .env; then
        sed -i '' "s|^API_HASH=.*|API_HASH=$INPUT_API_HASH|" .env
    else
        echo "API_HASH=$INPUT_API_HASH" >> .env
    fi
    ok "API_HASH saved"
else
    ok "API_HASH already set"
fi

# --- PHONE ---
if [ -z "$CUR_PHONE" ]; then
    echo ""
    echo -e "  ${BOLD}Your Telegram phone number:${NC}"
    hint "Format: +19991234567 (country code + number, no spaces)"
    echo ""
    read -p "  Enter phone number: " INPUT_PHONE
    while ! [[ "$INPUT_PHONE" =~ ^\+[0-9]{7,15}$ ]]; do
        echo -e "  ${RED}✗${NC} Invalid format. Example: +19991234567"
        read -p "  Enter phone number: " INPUT_PHONE
    done
    if grep -q "^TELEGRAM_PHONE=" .env; then
        sed -i '' "s|^TELEGRAM_PHONE=.*|TELEGRAM_PHONE=$INPUT_PHONE|" .env
    else
        echo "TELEGRAM_PHONE=$INPUT_PHONE" >> .env
    fi
    ok "Phone number saved"
else
    ok "Phone number already set ($CUR_PHONE)"
fi

# DATABASE_URL
if [ -z "$(source_val DATABASE_URL)" ]; then
    DB_USER=$(whoami)
    if grep -q "^DATABASE_URL=" .env; then
        sed -i '' "s|^DATABASE_URL=.*|DATABASE_URL=postgresql://$DB_USER@localhost:5432/telegram_export|" .env
    else
        echo "DATABASE_URL=postgresql://$DB_USER@localhost:5432/telegram_export" >> .env
    fi
fi

# ─── 7. Init DB schema ───────────────────────────────────────────────────────
step 7 "Database schema"
python main.py init-db
ok "Schema ready"

# ─── 8. Telegram auth ────────────────────────────────────────────────────────
step 8 "Telegram authorization"
echo ""
echo -e "  ${BOLD}Telegram will now send a confirmation code to your phone.${NC}"
hint "Open Telegram on your phone or desktop"
hint "Enter the code when prompted below"
echo ""
python auth.py

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║   ✅  Setup complete!                                    ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║   Now run the collector:                                 ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║      bash run.sh                                         ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║   CSV reports will appear on your Desktop                ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
