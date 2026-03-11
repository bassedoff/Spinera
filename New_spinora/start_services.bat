@echo off
setlocal EnableDelayedExpansion

echo 🚀 Starting SpinoraBot services...

REM Create necessary directories
mkdir logs 2>nul
mkdir data 2>nul
echo 📁 Created logs and data directories

REM Check for .env file
if exist ".env" (
    echo ✅ Environment variables loaded
) else (
    echo ⚠️  No .env file found, using defaults
)

REM Start web server
echo 🌐 Starting web server...
cd web
if not exist "node_modules" (
    echo Installing web dependencies...
    npm install >nul 2>&1
)
start /b node server.js > ..\logs\web.log 2>&1
set WEB_PID=!PID!
cd ..

echo ✅ Web server started
echo 🔗 Miniapp URL: http://localhost:3000

REM Start bot
echo 🤖 Starting Telegram bot...
cd bot
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv >nul 2>&1
)
call venv\Scripts\activate.bat >nul 2>&1
pip install -r requirements.txt >nul 2>&1
start /b python main.py > ..\logs\bot.log 2>&1
set BOT_PID=!PID!
cd ..

echo ✅ Telegram bot started

echo.
echo 🎯 Services are running!
echo ========================
echo Web Server PID: %WEB_PID%
echo Bot PID: %BOT_PID%
echo Miniapp URL: http://localhost:3000
echo.
echo 📋 Log files:
echo   - Web server: logs\web.log
echo   - Bot: logs\bot.log
echo.
echo 🔄 Close this window to stop all services
echo.

REM Wait indefinitely
pause >nul