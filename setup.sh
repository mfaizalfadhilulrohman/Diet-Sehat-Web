#!/usr/bin/env bash
# Membuat lingkungan .venv dan memasang semua pustaka. Jalankan sekali: bash setup.sh
python3 -m venv .venv && . .venv/bin/activate && python -m pip install --upgrade pip && python -m pip install -r requirements.txt
echo "Selesai. Di VS Code: Ctrl+Shift+P > Python: Select Interpreter > pilih .venv. Jalankan: . .venv/bin/activate && flask --app app run"
