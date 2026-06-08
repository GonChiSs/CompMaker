@echo off
setlocal
python scripts\generate_icon.py
pyinstaller --clean --noconfirm --distpath dist_release --workpath build_release build.spec
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
  "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer.iss
) else (
  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
)
endlocal
