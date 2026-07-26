@echo off
REM Runs the yt2audio CLI from the local virtual environment without needing to
REM activate it first. Pass the same arguments you'd pass to yt2audio.
REM   run.bat single "https://youtu.be/..." --format mp3
REM   run.bat playlist "https://youtube.com/playlist?list=..." --video
REM   run.bat batch urls.txt --no-cache
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\yt2audio.exe" (
  echo Not set up yet. Run setup.bat first.
  pause
  exit /b 1
)
".venv\Scripts\yt2audio.exe" %*
endlocal
