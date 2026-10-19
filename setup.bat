@echo off
REM Membuat lingkungan .venv dan memasang semua pustaka. Jalankan sekali dari folder ini.
py -3 -m venv .venv || python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo Selesai. Di VS Code: Ctrl+Shift+P ^> "Python: Select Interpreter" ^> pilih ".venv".
echo Jalankan aplikasi dengan jalankan.bat
