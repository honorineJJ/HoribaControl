@echo off
call .venv\Scripts\activate.bat
horibacontrol hardware-smoke --wavelength 532 --grating 1
pause
