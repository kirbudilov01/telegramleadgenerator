#!/bin/bash
set -e

# ─── Colors ────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
say()  { echo -e "\n${YELLOW}▶${NC} ${BOLD}$1${NC}"; }
hint() { echo -e "  ${CYAN}ℹ${NC}  $1"; }
err()  { echo -e "\n${RED}✗ ОШИБКА:${NC} $1"; exit 1; }
step() { echo -e "\n${BOLD}${YELLOW}[$1/8]${NC} ${BOLD}$2${NC}"; }

clear
echo ""
echo -e "${YELLOW}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║                                                          ║${NC}"
echo -e "${YELLOW}║   📊  Telegram Lead Generator — Установка               ║${NC}"
echo -e "${YELLOW}║                                                          ║${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Этот скрипт автоматически установит всё необходимое"
echo "  и настроит подключение к Telegram."
echo ""
read -p "  Нажми Enter чтобы начать..." _

# ─── 1. Homebrew ────────────────────────────────────────────────────────────
step 1 "Homebrew (менеджер пакетов macOS)"
if ! command -v brew &>/dev/null; then
    hint "Homebrew не найден — устанавливаю (может запросить пароль)..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if [[ -f /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
    fi
fi
ok "Homebrew готов"

# ─── 2. Python ──────────────────────────────────────────────────────────────
step 2 "Python 3.11"
if ! brew list python@3.11 &>/dev/null; then
    hint "Устанавливаю Python 3.11..."
    brew install python@3.11
fi
PYTHON=$(brew --prefix python@3.11)/bin/python3.11
ok "Python: $($PYTHON --version)"

# ─── 3. PostgreSQL ──────────────────────────────────────────────────────────
step 3 "PostgreSQL (база данных)"
if ! brew list postgresql@18 &>/dev/null 2>&1; then
    if ! brew list postgresql@16 &>/dev/null 2>&1; then
        hint "Устанавливаю PostgreSQL 18..."
        brew install postgresql@18
    fi
fi

if ! pg_isready -q 2>/dev/null; then
    hint "Запускаю PostgreSQL..."
    brew services start postgresql@18 2>/dev/null || brew services start postgresql@16 2>/dev/null || true
    sleep 2
fi

if pg_isready -q 2>/dev/null; then
    ok "PostgreSQL запущен"
else
    err "PostgreSQL не запустился. Попробуй вручную: brew services start postgresql@18"
fi

# ─── 4. Python venv + deps ──────────────────────────────────────────────────
step 4 "Python-зависимости"
if [ ! -d "venv" ]; then
    hint "Создаю виртуальное окружение..."
    $PYTHON -m venv venv
fi
source venv/bin/activate
hint "Устанавливаю пакеты (Telethon, SQLAlchemy, psycopg2...)..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
ok "Все пакеты установлены"

# ─── 5. Database ────────────────────────────────────────────────────────────
step 5 "База данных"
createdb telegram_export 2>/dev/null && ok "База данных создана" || ok "База данных уже существует"

# ─── 6. .env — API ключи ────────────────────────────────────────────────────
step 6 "Telegram API ключи"

if [ ! -f ".env" ]; then
    cp .env.example .env
fi

# Считываем уже существующие значения
source_val() { grep "^$1=" .env 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'"; }
CUR_API_ID=$(source_val API_ID)
CUR_API_HASH=$(source_val API_HASH)
CUR_PHONE=$(source_val TELEGRAM_PHONE)

# --- API_ID ---
if [ -z "$CUR_API_ID" ]; then
    echo ""
    echo -e "  ${BOLD}Где взять API_ID и API_HASH:${NC}"
    echo ""
    hint "1. Открой в браузере:  https://my.telegram.org"
    hint "2. Войди под своим номером телефона"
    hint "3. Нажми  «API development tools»"
    hint "4. Создай приложение (название — любое, например MyApp)"
    hint "5. Скопируй  App api_id  и  App api_hash"
    echo ""
    read -p "  Введи API_ID (только цифры): " INPUT_API_ID
    while ! [[ "$INPUT_API_ID" =~ ^[0-9]+$ ]]; do
        echo -e "  ${RED}✗${NC} API_ID должен состоять только из цифр"
        read -p "  Введи API_ID: " INPUT_API_ID
    done
    # Записываем в .env
    if grep -q "^API_ID=" .env; then
        sed -i '' "s|^API_ID=.*|API_ID=$INPUT_API_ID|" .env
    else
        echo "API_ID=$INPUT_API_ID" >> .env
    fi
    ok "API_ID сохранён"
else
    ok "API_ID уже задан (${CUR_API_ID})"
fi

# --- API_HASH ---
if [ -z "$CUR_API_HASH" ]; then
    echo ""
    read -p "  Введи API_HASH (32 символа): " INPUT_API_HASH
    while [ ${#INPUT_API_HASH} -lt 10 ]; do
        echo -e "  ${RED}✗${NC} API_HASH слишком короткий, попробуй ещё раз"
        read -p "  Введи API_HASH: " INPUT_API_HASH
    done
    if grep -q "^API_HASH=" .env; then
        sed -i '' "s|^API_HASH=.*|API_HASH=$INPUT_API_HASH|" .env
    else
        echo "API_HASH=$INPUT_API_HASH" >> .env
    fi
    ok "API_HASH сохранён"
else
    ok "API_HASH уже задан"
fi

# --- PHONE ---
if [ -z "$CUR_PHONE" ]; then
    echo ""
    echo -e "  ${BOLD}Номер телефона Telegram:${NC}"
    hint "Формат: +79991234567 (с кодом страны, без пробелов)"
    echo ""
    read -p "  Введи номер телефона: " INPUT_PHONE
    while ! [[ "$INPUT_PHONE" =~ ^\+[0-9]{7,15}$ ]]; do
        echo -e "  ${RED}✗${NC} Неверный формат. Пример: +79991234567"
        read -p "  Введи номер телефона: " INPUT_PHONE
    done
    if grep -q "^TELEGRAM_PHONE=" .env; then
        sed -i '' "s|^TELEGRAM_PHONE=.*|TELEGRAM_PHONE=$INPUT_PHONE|" .env
    else
        echo "TELEGRAM_PHONE=$INPUT_PHONE" >> .env
    fi
    ok "Номер телефона сохранён"
else
    ok "Номер телефона уже задан ($CUR_PHONE)"
fi

# DATABASE_URL — ставим дефолтный если не задан
if [ -z "$(source_val DATABASE_URL)" ]; then
    DB_USER=$(whoami)
    if grep -q "^DATABASE_URL=" .env; then
        sed -i '' "s|^DATABASE_URL=.*|DATABASE_URL=postgresql://$DB_USER@localhost:5432/telegram_export|" .env
    else
        echo "DATABASE_URL=postgresql://$DB_USER@localhost:5432/telegram_export" >> .env
    fi
fi

# ─── 7. Init DB schema ──────────────────────────────────────────────────────
step 7 "Инициализация схемы базы данных"
python main.py init-db
ok "Схема создана"

# ─── 8. Авторизация Telegram ────────────────────────────────────────────────
step 8 "Авторизация в Telegram"
echo ""
echo -e "  ${BOLD}Сейчас Telegram пришлёт код подтверждения.${NC}"
hint "Открой Telegram на телефоне или в приложении"
hint "Введи код когда появится запрос ниже"
echo ""
python auth.py

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║   ✅  Установка завершена успешно!                       ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║   Теперь запусти сбор данных:                            ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║      bash run.sh                                         ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║   CSV-отчёты появятся на Рабочем столе                   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
