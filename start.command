#!/bin/bash
set -e

cd "$(dirname "$0")"

if [[ ! -f ".env" ]] || [[ ! -d "venv" ]]; then
  clear
  echo ""
  echo "Starting first-time setup..."
  echo ""
  bash setup.sh
fi

clear
echo ""
echo "Launching Telegram Lead Generator..."
echo ""
bash run.sh --ultra-noob
