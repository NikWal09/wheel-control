@echo off
rem Buduje dist\DDControl\DDControl.exe
python -m pip install -r requirements-dev.txt || exit /b 1
python -m pytest -q || exit /b 1
python -m PyInstaller --noconfirm ddcontrol.spec
