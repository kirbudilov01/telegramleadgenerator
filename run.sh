#!/bin/bash
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
say() { echo -e "${YELLOW}▶${NC} $1"; }
ok()  { echo -e "${GREEN}✓${NC} $1"; }

DESKTOP="$HOME/Desktop"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULT_DIR="$DESKTOP/telegram_analysis_$TIMESTAMP"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║     Telegram Chat Analyzer — Run                 ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")"
source venv/bin/activate

# ─── Collect messages ───────────────────────────────────────────────────────
say "Шаг 1/2: Собираем сообщения из Telegram (может занять несколько часов)..."
echo "  Прогресс отображается ниже. Не закрывай терминал."
echo ""
python -u main.py load
ok "Сбор завершён"
echo ""

# ─── Analyze ────────────────────────────────────────────────────────────────
say "Шаг 2/2: Анализируем чаты и формируем отчёты..."
echo ""
python analyze.py
ok "Анализ завершён"
echo ""

# ─── Copy to Desktop ────────────────────────────────────────────────────────
say "Копируем результаты на рабочий стол..."
mkdir -p "$RESULT_DIR"
cp exports/analysis_all.csv       "$RESULT_DIR/all_chats.csv"
cp exports/top100_by_messages.csv "$RESULT_DIR/top100_by_activity.csv"
cp exports/top100_by_priority.csv "$RESULT_DIR/top100_priority.csv"

# Открываем папку в Finder
open "$RESULT_DIR"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ Готово! Файлы на рабочем столе:              ║${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}║  📁 telegram_analysis_${TIMESTAMP}  ║${NC}"
echo -e "${GREEN}║     • all_chats.csv          — все чаты          ║${NC}"
echo -e "${GREEN}║     • top100_priority.csv    — топ по важности   ║${NC}"
echo -e "${GREEN}║     • top100_by_activity.csv — топ по активности ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
