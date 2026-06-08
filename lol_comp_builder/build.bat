@echo off
setlocal
python scripts\generate_icon.py
pyinstaller --clean --noconfirm build.spec
endlocal
