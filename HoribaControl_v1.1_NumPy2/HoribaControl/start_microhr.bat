@echo off
setlocal
if not exist .venv\Scripts\python.exe (
  echo Environnement absent. Lancez install_windows.bat.
  pause
  exit /b 1
)
.venv\Scripts\python.exe run_gui.py
