#!/bin/bash
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
say()  { echo -e "\n${YELLOW}▶${NC} ${BOLD}$1${NC}"; }
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
err()  { echo -e "\n${RED}✗ ОШИБКА:${NC} $1"; }
hint() { echo -e "  ${CYAN}ℹ${NC}  $1"; }

DESKTOP="$HOME/Desktop"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULT_DIR="$DESKTOP/telegram_analysis_$TIMESTAMP"

cd "$(dirname "$0")"
source venv/bin/activate

clear
echo ""
echo -e "${YELLOW}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║                                                          ║${NC}"
echo -e "${YELLOW}║   📊  Telegram Lead Generator                            ║${NC}"
echo -e "${YELLOW}║                                                          ║${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ─── Выбор режима сбора ──────────────────────────────────────────────────────
echo -e "  ${BOLD}Что собирать?${NC}"
echo ""
echo "  1)  Только личные чаты               (быстрее, рекомендуется)"
echo "  2)  Личные чаты + группы             (медленнее, больше данных)"
echo ""
read -p "  Выбор [1 или 2, по умолчанию 1]: " MODE_CHOICE
MODE_CHOICE="${MODE_CHOICE:-1}"

if [[ "$MODE_CHOICE" == "2" ]]; then
    LOAD_FLAGS="--groups"
    MODE_LABEL="личные чаты + группы"
else
    LOAD_FLAGS=""
    MODE_LABEL="только личные чаты"
fi

# ─── Повторный запуск? ──────────────────────────────────────────────────────
echo ""
echo -e "  ${BOLD}Режим запуска:${NC}"
echo ""
echo "  1)  Полный сбор                      (если запускаешь первый раз)"
echo "  2)  Только новые сообщения           (если сбор уже был)"
echo ""
read -p "  Выбор [1 или 2, по умолчанию 1]: " SYNC_CHOICE
SYNC_CHOICE="${SYNC_CHOICE:-1}"

echo ""
echo -e "  ${CYAN}Режим:${NC} $MODE_LABEL"
if [[ "$SYNC_CHOICE" == "2" ]]; then
    echo -e "  ${CYAN}Сбор:${NC}  только новые сообщения"
else
    echo -e "  ${CYAN}Сбор:${NC}  полный (все чаты с нуля)"
fi
echo ""
read -p "  Нажми Enter чтобы начать..." _

# ─── Collect messages ───────────────────────────────────────────────────────
say "Шаг 1/2 — Сбор сообщений из Telegram"
echo ""
hint "Режим: $MODE_LABEL"
hint "Не закрывай терминал — прогресс отображается ниже"
hint "Первый запуск может занять несколько часов (зависит от количества чатов)"
echo ""

if [[ "$SYNC_CHOICE" == "2" ]]; then
    python -u main.py sync
    LOAD_EXIT=$?
else
    python -u main.py load $LOAD_FLAGS
    LOAD_EXIT=$?
fi

if [[ $LOAD_EXIT -ne 0 ]]; then
    err "Сбор завершился с ошибкой (код $LOAD_EXIT)"
    echo ""
    hint "Возможные причины:"
    hint "  • Telegram замедлил запросы — подожди 10 минут и повтори"
    hint "  • Неверные данные в .env — проверь API_ID, API_HASH, номер"
    hint "  • Сессия устарела — запусти: python auth.py"
    echo ""
    exit 1
fi

ok "Сбор завершён"
echo ""

# ─── Analyze ────────────────────────────────────────────────────────────────
say "Шаг 2/2 — Анализ чатов и формирование отчётов"
echo ""
python analyze.py
ANALYZE_EXIT=$?

if [[ $ANALYZE_EXIT -ne 0 ]]; then
    err "Анализ завершился с ошибкой (код $ANALYZE_EXIT)"
    hint "Проверь статистику базы: python main.py stats"
    exit 1
fi

ok "Анализ завершён"
echo ""

# ─── Copy to Desktop ────────────────────────────────────────────────────────
say "Копируем результаты на Рабочий стол..."
mkdir -p "$RESULT_DIR"

for f in exports/analysis_all.csv exports/top100_by_messages.csv exports/top100_by_priority.csv; do
    if [[ ! -f "$f" ]]; then
        err "Файл не найден: $f"
        exit 1
    fi
done

cp exports/analysis_all.csv       "$RESULT_DIR/all_chats.csv"
cp exports/top100_by_messages.csv "$RESULT_DIR/top100_by_activity.csv"
cp exports/top100_by_priority.csv "$RESULT_DIR/top100_priority.csv"

open "$RESULT_DIR"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║   ✅  Готово! Файлы сохранены на Рабочем столе           ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║   📁 telegram_analysis_${TIMESTAMP}  ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║      all_chats.csv            — все проанализированные   ║${NC}"
echo -e "${GREEN}║      top100_priority.csv      — топ по важности ⭐       ║${NC}"
echo -e "${GREEN}║      top100_by_activity.csv   — топ по активности        ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
