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

# ─── Collection profile ──────────────────────────────────────────────────────
echo -e "  ${BOLD}Choose collection profile:${NC}"
echo ""
echo "  1)  Smart Filter (recommended)       personal only, no bots/channels"
echo "  2)  Custom selection                 choose what to include"
echo ""
read -p "  Choice [1 or 2, default 1]: " PROFILE_CHOICE
PROFILE_CHOICE="${PROFILE_CHOICE:-1}"

LOAD_FLAGS=""
MODE_LABEL="Smart Filter"

if [[ "$PROFILE_CHOICE" == "2" ]]; then
    MODE_LABEL="Custom"
    echo ""
    echo -e "  ${BOLD}Custom selection:${NC}"
    echo ""
    read -p "  Include group chats? [y/N]: " INCLUDE_GROUPS
    read -p "  Include bot dialogs? [y/N]: " INCLUDE_BOTS
    read -p "  Include channels? [y/N]: " INCLUDE_CHANNELS

    if [[ "$INCLUDE_GROUPS" =~ ^[Yy]$ ]]; then
        LOAD_FLAGS+=" --groups"
    fi
    if [[ "$INCLUDE_BOTS" =~ ^[Yy]$ ]]; then
        LOAD_FLAGS+=" --bots"
    fi
    if [[ "$INCLUDE_CHANNELS" =~ ^[Yy]$ ]]; then
        LOAD_FLAGS+=" --channels"
    fi
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
echo -e "  ${CYAN}Profile:${NC}    $MODE_LABEL"
if [[ -n "$LOAD_FLAGS" ]]; then
    echo -e "  ${CYAN}Flags:${NC}      $LOAD_FLAGS"
else
    echo -e "  ${CYAN}Flags:${NC}      (none)"
fi
echo ""
read -p "  Press Enter to start..." _

# ─── Step 1: Collect ─────────────────────────────────────────────────────────
say "Step 1/2 — Collecting messages from Telegram"
echo ""
hint "Profile: $MODE_LABEL"
hint "Do NOT close this terminal — progress is shown below"
hint "First run may take several hours depending on your chat history"
echo ""

if [[ "$SYNC_CHOICE" == "2" ]]; then
    python -u main.py sync
    LOAD_EXIT=$?
else
    python -u main.py load ${LOAD_FLAGS}
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

# ─── Full raw CSV export ─────────────────────────────────────────────────────
say "Creating full raw CSV export (entire collected history)..."
python -u main.py export csv
EXPORT_EXIT=$?

if [[ $EXPORT_EXIT -ne 0 ]]; then
    err "Raw CSV export failed (exit code $EXPORT_EXIT)"
    hint "You still have analysis CSV files. Try again with: python main.py export csv"
    exit 1
fi

RAW_CSV=$(ls -t exports/telegram_export_*.csv 2>/dev/null | head -n 1)
if [[ -z "$RAW_CSV" ]]; then
    err "Raw CSV file not found after export"
    exit 1
fi

ok "Full raw CSV export created"
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
cp "$RAW_CSV"                     "$RESULT_DIR/full_history_raw.csv"

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
echo -e "${GREEN}║      full_history_raw.csv     — complete raw export      ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "  ${BOLD}Optional:${NC} open local AI chat over these results"
echo ""
read -p "  Launch local AI chat now? [y/N]: " AI_CHOICE
if [[ "$AI_CHOICE" =~ ^[Yy]$ ]]; then
    echo ""
    hint "Requires Ollama running locally"
    hint "If needed: install from https://ollama.com and run: ollama pull llama3.1"
    echo ""
    python local_ai_chat.py --results-dir "$RESULT_DIR" --model llama3.1 || true
fi
