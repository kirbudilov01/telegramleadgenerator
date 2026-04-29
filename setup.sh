#!/bin/bash
set -e

# ─── Colors ────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()  { echo -e "${GREEN}✓${NC} $1"; }
say() { echo -e "${YELLOW}▶${NC} $1"; }
err() { echo -e "${RED}✗ ERROR:${NC} $1"; exit 1; }

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║     Telegram Chat Analyzer — Setup               ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ─── 1. Homebrew ────────────────────────────────────────────────────────────
say "Checking Homebrew..."
if ! command -v brew &>/dev/null; then
    say "Installing Homebrew (may ask for password)..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add brew to PATH for Apple Silicon
    if [[ -f /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
    fi
fi
ok "Homebrew ready"

# ─── 2. Python ──────────────────────────────────────────────────────────────
say "Checking Python 3.11+..."
if ! brew list python@3.11 &>/dev/null; then
    say "Installing Python 3.11..."
    brew install python@3.11
fi
PYTHON=$(brew --prefix python@3.11)/bin/python3.11
ok "Python: $($PYTHON --version)"

# ─── 3. PostgreSQL ──────────────────────────────────────────────────────────
say "Checking PostgreSQL..."
if ! brew list postgresql@18 &>/dev/null 2>&1; then
    if ! brew list postgresql@16 &>/dev/null 2>&1; then
        say "Installing PostgreSQL 18..."
        brew install postgresql@18
    fi
fi

# Start postgres if not running
if ! pg_isready -q 2>/dev/null; then
    say "Starting PostgreSQL..."
    brew services start postgresql@18 2>/dev/null || brew services start postgresql@16 2>/dev/null || true
    sleep 2
fi

if pg_isready -q 2>/dev/null; then
    ok "PostgreSQL running"
else
    err "PostgreSQL failed to start. Try: brew services start postgresql@18"
fi

# ─── 4. Python venv + deps ──────────────────────────────────────────────────
say "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
fi
source venv/bin/activate
say "Installing Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
ok "Python dependencies installed"

# ─── 5. Database ────────────────────────────────────────────────────────────
say "Creating database telegram_export..."
createdb telegram_export 2>/dev/null && ok "Database created" || ok "Database already exists"

# ─── 6. .env setup ──────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}  Открой .env и заполни:${NC}"
    echo -e "${YELLOW}  1. API_ID и API_HASH (с https://my.telegram.org)${NC}"
    echo -e "${YELLOW}  2. TELEGRAM_PHONE (с кодом страны, +7...)${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "  Редактировать: nano .env"
    echo "  Или открыть в Finder: open ."
    echo ""
    read -p "Нажми Enter когда заполнишь .env..." _
else
    ok ".env уже существует"
fi

# ─── 7. Init DB schema ──────────────────────────────────────────────────────
say "Initializing database schema..."
python main.py init-db
ok "Schema ready"

# ─── 8. Auth ────────────────────────────────────────────────────────────────
say "Authorizing Telegram session..."
echo ""
echo "  Сейчас придёт код в Telegram — введи его ниже"
echo ""
python auth.py

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ Setup завершён!                               ║${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}║  Теперь запусти:  bash run.sh                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
