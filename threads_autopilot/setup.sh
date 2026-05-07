#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "[1/5] Checking Python..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python3 is required"
  exit 1
fi

echo "[2/5] Creating venv (if missing)..."
if [ ! -d venv ]; then
  python3 -m venv venv
fi

source venv/bin/activate

echo "[3/5] Installing packages..."
pip install -q -r requirements.txt

echo "[4/5] Installing Chromium for Playwright..."
playwright install chromium

echo "[5/5] Preparing local config..."
if [ ! -f config.json ]; then
  cp config.example.json config.json
fi
if [ ! -f persona.txt ]; then
  cp persona.example.txt persona.txt
fi

echo "Done. Next steps:"
echo "1) Edit config.json and persona.txt"
echo "2) Login once:   source venv/bin/activate && python autopilot.py --setup-login"
echo "3) Dry run:      python autopilot.py --once --dry-run --profile safe"
echo "4) Night run:    python autopilot.py --profile safe"
