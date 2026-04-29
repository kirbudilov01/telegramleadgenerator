#!/bin/bash
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
say()  { echo -e "\n${YELLOW}▶${NC} ${BOLD}$1${NC}"; }
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
err()  { echo -e "\n${RED}✗ ERROR:${NC} $1"; }
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
echo -e "${YELLOW}║   📊  Telegram Lead Generator — Collect & Analyze       ║${NC}"
echo -e "${YELLOW}║          by FABRICBOT ECOSYSTEM                         ║${NC}"
echo -e "${YELLOW}║                                                          ║${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ─── What to collect ─────────────────────────────────────────────────────────
echo -e "  ${BOLD}What to collect?${NC}"
echo ""
echo "  1)  Personal chats only              (faster, recommended for first run)"
echo "  2)  Personal chats + group chats     (slower, more data)"
echo ""
read -p "  Choice [1 or 2, default 1]: " MODE_CHOICE
MODE_CHOICE="${MODE_CHOICE:-1}"

if [[ "$MODE_CHOICE" == "2" ]]; then
    LOAD_FLAGS="--groups"
    MODE_LABEL="personal chats + groups"
else
    LOAD_FLAGS=""
    MODE_LABEL="personal chats only"
fi

# ─── Full or incremental ─────────────────────────────────────────────────────
echo ""
echo -e "  ${BOLD}Run mode?${NC}"
echo ""
echo "  1)  Full collection                  (first time — collects everything)"
echo "  2)  New messages only                (already collected — sync updates)"
echo ""
read -p "  Choice [1 or 2, default 1]: " SYNC_CHOICE
SYNC_CHOICE="${SYNC_CHOICE:-1}"

echo ""
echo -e "  ${CYAN}Collecting:${NC} $MODE_LABEL"
if [[ "$SYNC_CHOICE" == "2" ]]; then
    echo -e "  ${CYAN}Mode:${NC}       new messages only"
else
    echo -e "  ${CYAN}Mode:${NC}       full collection from scratch"
fi
echo ""
read -p "  Press Enter to start..." _

# ─── Step 1: Collect ─────────────────────────────────────────────────────────
say "Step 1/2 — Collecting messages from Telegram"
echo ""
hint "Scope: $MODE_LABEL"
hint "Do NOT close this terminal — progress is shown below"
hint "First run may take several hours depending on your chat history"
echo ""

if [[ "$SYNC_CHOICE" == "2" ]]; then
    python -u main.py sync
    LOAD_EXIT=$?
else
    python -u main.py load $LOAD_FLAGS
    LOAD_EXIT=$?
fi

if [[ $LOAD_EXIT -ne 0 ]]; then
    err "Collection failed (exit code $LOAD_EXIT)"
    echo ""
    hint "Possible causes:"
    hint "  • Telegram rate-limited you — wait 10 minutes and try again"
    hint "  • Wrong credentials in .env — check API_ID, API_HASH, phone"
    hint "  • Session expired — re-run: python auth.py"
    echo ""
    exit 1
fi

ok "Collection complete"
echo ""

# ─── Step 2: Analyze ─────────────────────────────────────────────────────────
say "Step 2/2 — Analyzing chats and building reports"
echo ""
python analyze.py
ANALYZE_EXIT=$?

if [[ $ANALYZE_EXIT -ne 0 ]]; then
    err "Analysis failed (exit code $ANALYZE_EXIT)"
    hint "Check database stats: python main.py stats"
    exit 1
fi

ok "Analysis complete"
echo ""

# ─── Copy to Desktop ─────────────────────────────────────────────────────────
say "Saving results to Desktop..."
mkdir -p "$RESULT_DIR"

for f in exports/analysis_all.csv exports/top100_by_messages.csv exports/top100_by_priority.csv; do
    if [[ ! -f "$f" ]]; then
        err "Output file not found: $f"
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
echo -e "${GREEN}║   ✅  Done! Reports saved to your Desktop                ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║   📁 telegram_analysis_${TIMESTAMP}  ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║      all_chats.csv            — all analyzed chats       ║${NC}"
echo -e "${GREEN}║      top100_priority.csv      — top leads by score ⭐    ║${NC}"
echo -e "${GREEN}║      top100_by_activity.csv   — top by message count     ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
