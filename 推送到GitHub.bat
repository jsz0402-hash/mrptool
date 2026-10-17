@echo off
chcp 65001 >nul
setlocal
set "PATH=H:\work\git\cmd;%PATH%"
cd /d "%~dp0"
title Push mrptool to GitHub

echo.
echo  ==============================================================
echo    Push mrptool to GitHub
echo  ==============================================================
echo.
echo   BEFORE YOU START, you need two things:
echo.
echo   [1] An EMPTY repository named  mrptool  on GitHub
echo       Create it here:  https://github.com/new
echo       IMPORTANT: do NOT check "Add a README file",
echo                  do NOT add .gitignore, do NOT add a license.
echo.
echo   [2] A Personal Access Token (this replaces your password)
echo       Create it here:  https://github.com/settings/tokens
echo         - Click "Generate new token" -> "Generate new token (classic)"
echo         - Note: mrptool     Expiration: 90 days is fine
echo         - CHECK the box  [x] repo
echo         - Click "Generate token"
echo         - COPY the token now (it is shown only once)
echo.
echo  ==============================================================
echo.

set "DEFUSER=jsz0402-hash"
set /p GHUSER=  Your GitHub username [%DEFUSER%]: 
if "%GHUSER%"=="" set "GHUSER=%DEFUSER%"
if "%GHUSER%"=="" (
  echo.
  echo   Cancelled - nothing was uploaded.
  echo.
  pause
  exit /b 1
)

set "REPO=https://github.com/%GHUSER%/mrptool.git"

echo.
echo   Remote will be:  %REPO%
echo.

git remote remove origin >nul 2>nul
git remote add origin "%REPO%"

echo   Pushing now...
echo   When asked:
echo       Username  ->  your GitHub username
echo       Password  ->  PASTE THE TOKEN (right-click to paste)
echo.
echo   --------------------------------------------------------------
git push -u origin main
set PUSH_RESULT=%errorlevel%
echo   --------------------------------------------------------------
echo.

if not "%PUSH_RESULT%"=="0" (
  echo   FAILED. The most common reasons are:
  echo.
  echo     - The repository "mrptool" does not exist on GitHub yet
  echo     - The username is spelled wrong
  echo     - The token is wrong, expired, or missing the "repo" scope
  echo     - You accidentally initialized the repo with a README,
  echo       so the remote already has commits. Fix with:
  echo           git pull --rebase origin main
  echo       then run this script again.
  echo.
) else (
  echo   SUCCESS! Your project is now live at:
  echo.
  echo       https://github.com/%GHUSER%/mrptool
  echo.
  echo   Share that link with anyone.
  echo.
)

pause
