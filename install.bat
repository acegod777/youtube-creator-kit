@echo off
rem Installs youtube-creator-kit into Claude Code (Windows). Run again to update.
rem Your filled-in channels.md is never overwritten.
setlocal
set "SRC=%~dp0skills\youtube-creator-kit"
set "DST=%USERPROFILE%\.claude\skills\youtube-creator-kit"
set "PROFILE=%USERPROFILE%\.claude\youtube\channels.md"

set "PY=python"
where python >nul 2>nul || set "PY=py"
where %PY% >nul 2>nul || (
  echo Python 3 is needed: https://www.python.org/downloads/
  pause
  exit /b 1
)

echo Running tests first...
%PY% "%~dp0tests\test_tools.py"
if errorlevel 1 (
  echo.
  echo TESTS FAILED - nothing installed.
  pause
  exit /b 1
)

if exist "%DST%" rmdir /s /q "%DST%"
xcopy "%SRC%" "%DST%\" /e /i /q /y >nul
if errorlevel 1 (
  echo Copy failed.
  pause
  exit /b 1
)
if not exist "%PROFILE%" (
  mkdir "%USERPROFILE%\.claude\youtube" 2>nul
  copy "%SRC%\channels.template.md" "%PROFILE%" >nul
  echo Created %PROFILE% - fill in the blanks.
)
echo.
echo Installed to %DST%
echo Start a NEW Claude Code session, then ask for help with titles, or type /youtube-creator-kit
pause
