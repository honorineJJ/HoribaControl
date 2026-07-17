@echo off
setlocal
py -3.11 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -e .
echo.
echo Installation terminee.
echo Lancez: .venv\Scripts\python.exe run_gui.py
pause
