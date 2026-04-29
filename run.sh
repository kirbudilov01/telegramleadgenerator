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
ULTRA_NOOB=false

if [[ "${1:-}" == "--ultra-noob" ]]; then
    ULTRA_NOOB=true
fi

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

LOAD_FLAGS=""
MODE_LABEL="Smart Filter"
SYNC_CHOICE="1"

# ─── Collection profile ──────────────────────────────────────────────────────
if [[ "$ULTRA_NOOB" == true ]]; then
    echo -e "  ${BOLD}Ultra Noob Mode is ON ✅${NC}"
    echo ""
    hint "Using recommended preset automatically"
    hint "Profile: Smart Filter (personal chats, no bots/channels)"
    hint "Mode: Full collection"
    echo ""
    read -p "  Press Enter to start with recommended settings..." _
else
    echo -e "  ${BOLD}Choose collection profile:${NC}"
    echo ""
    echo "  1)  Smart Filter (recommended)       personal only, no bots/channels"
    echo "  2)  Custom selection                 choose what to include"
    echo ""
    read -p "  Choice [1 or 2, default 1]: " PROFILE_CHOICE
    PROFILE_CHOICE="${PROFILE_CHOICE:-1}"

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

    # ─── Full or incremental ─────────────────────────────────────────────────
    echo ""
    echo -e "  ${BOLD}Run mode?${NC}"
    echo ""
    echo "  1)  Full collection                  (first time — collects everything)"
    echo "  2)  New messages only                (already collected — sync updates)"
    echo ""
    read -p "  Choice [1 or 2, default 1]: " SYNC_CHOICE
    SYNC_CHOICE="${SYNC_CHOICE:-1}"
fi

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
if [[ "$ULTRA_NOOB" == false ]]; then
    echo ""
    read -p "  Press Enter to start..." _
fi

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

say "Building Excel workbook with separate lead sheets..."
python build_leads_workbook.py --results-dir "$RESULT_DIR" --output "$RESULT_DIR/telegram_leads_bundle.xlsx"
XLSX_EXIT=$?
if [[ $XLSX_EXIT -ne 0 ]]; then
    err "Excel workbook build failed (exit code $XLSX_EXIT)"
    exit 1
fi

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
echo -e "${GREEN}║      telegram_leads_bundle.xlsx — all sheets in one file ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "  ${BOLD}Optional:${NC} open local AI chat over these results"
echo ""
read -p "  Launch local AI chat now? [y/N]: " AI_CHOICE
if [[ "$AI_CHOICE" =~ ^[Yy]$ ]]; then
    echo ""
    AI_PROVIDER="ollama"
    AI_MODEL="llama3.1"

    if [[ "$ULTRA_NOOB" == false ]]; then
        echo "  Choose AI provider:"
        echo "  1) Ollama (local, recommended)"
        echo "  2) OpenAI API"
        echo "  3) Anthropic Claude API"
        echo ""
        read -p "  Choice [1/2/3, default 1]: " AI_PROVIDER_CHOICE
        AI_PROVIDER_CHOICE="${AI_PROVIDER_CHOICE:-1}"

        if [[ "$AI_PROVIDER_CHOICE" == "2" ]]; then
            AI_PROVIDER="openai"
            echo ""
            echo "  Choose OpenAI Cloud model:"
            echo "  1) GPT-5.3-Codex (advanced reasoning/coding)"
            echo "  2) GPT-4o-mini (faster/cheaper)"
            echo ""
            read -p "  Choice [1/2, default 1]: " OPENAI_MODEL_CHOICE
            OPENAI_MODEL_CHOICE="${OPENAI_MODEL_CHOICE:-1}"
            if [[ "$OPENAI_MODEL_CHOICE" == "2" ]]; then
                AI_MODEL="gpt-4o-mini"
            else
                AI_MODEL="gpt-5.3-codex"
            fi
            hint "Requires OPENAI_API_KEY in your environment or .env"
        elif [[ "$AI_PROVIDER_CHOICE" == "3" ]]; then
            AI_PROVIDER="anthropic"
            AI_MODEL="claude-3-5-sonnet-latest"
            hint "Requires ANTHROPIC_API_KEY in your environment or .env"
        else
            hint "Requires Ollama running locally"
            hint "If needed: install from https://ollama.com and run: ollama pull llama3.1"
        fi
    else
        hint "Ultra Noob Mode: launching Ollama with default model llama3.1"
        hint "Requires Ollama running locally"
        hint "If needed: install from https://ollama.com and run: ollama pull llama3.1"
    fi

    echo ""
    python local_ai_chat.py --results-dir "$RESULT_DIR" --provider "$AI_PROVIDER" --model "$AI_MODEL" || true
fi
