@echo off
setlocal EnableDelayedExpansion
python scripts\generate_icon.py
pyinstaller --clean --noconfirm --distpath dist_release --workpath build_release build.spec
if errorlevel 1 exit /b %errorlevel%

set "ISCC_PATH="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
  set "ISCC_PATH=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
) else (
  set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)

set "ISCC_EXIT=1"
for /l %%I in (1,1,3) do (
  "%ISCC_PATH%" installer.iss
  set "ISCC_EXIT=!errorlevel!"
  if "!ISCC_EXIT!"=="0" goto :success
  if %%I lss 3 (
    echo Inno Setup bloqueado temporalmente. Reintentando compilacion %%I/3...
    powershell -NoProfile -Command "Start-Sleep -Seconds 2"
  )
)

exit /b %ISCC_EXIT%

:success
endlocal
