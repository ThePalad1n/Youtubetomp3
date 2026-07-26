@echo off
REM One-step local setup for Windows. Double-click this file, or run it from a
REM terminal in the repo folder. It creates a virtual environment, installs
REM yt2audio with the CLI, and checks that ffmpeg is present.
setlocal

cd /d "%~dp0"

echo === Checking Python ===
where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    set "PY=python"
  ) else (
    echo Python was not found. Install Python 3.10 or newer from https://www.python.org/downloads/ and re-run this script.
    pause
    exit /b 1
  )
)
%PY% --version

echo.
echo === Creating virtual environment (.venv) ===
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
) else (
  echo .venv already exists, reusing it.
)

echo.
echo === Installing yt2audio + CLI ===
call ".venv\Scripts\python.exe" -m pip install --upgrade pip
call ".venv\Scripts\python.exe" -m pip install -e ".[cli]"
if %errorlevel% neq 0 (
  echo Install failed. Scroll up for the error.
  pause
  exit /b 1
)

echo.
echo === Checking ffmpeg ===
where ffmpeg >nul 2>nul
if %errorlevel%==0 (
  echo ffmpeg found on PATH.
) else (
  echo ffmpeg was NOT found on PATH. mp3 extraction and mp4 merging need it.
  echo Install it with:  winget install --id Gyan.FFmpeg
  echo Then open a NEW terminal so PATH refreshes, and re-run this script.
)

echo.
echo === Done ===
echo Run downloads with run.bat, for example:
echo   run.bat single "https://www.youtube.com/watch?v=..." --format mp3
echo   run.bat single "https://www.youtube.com/watch?v=..." --video
echo.
echo Turn your VPN on before downloading. Add --no-cache to leave no local yt-dlp cache.
pause
endlocal
