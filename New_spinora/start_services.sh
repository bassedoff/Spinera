#!/bin/bash

# SpinoraBot Services Startup Script

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Define log directory
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR" "$SCRIPT_DIR/data"

cd "$SCRIPT_DIR"

echo "🚀 Starting SpinoraBot services..."

# Load environment variables
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
  echo "✅ Environment variables loaded"
else
  echo "⚠️ .env file not found"
fi

# Self-check: verify required vars
if [ -z "${BOT_TOKEN:-}" ]; then
  echo "❌ BOT_TOKEN not set"
  exit 1
fi

if [ -z "${PUBLIC_WEBAPP_URL:-}" ]; then
  echo "❌ PUBLIC_WEBAPP_URL not set"
  exit 1
fi

echo "✅ Configuration OK"

# Kill any existing processes
pkill -f "node server.js" 2>/dev/null || true
pkill -f "bot/main.py" 2>/dev/null || true
pkill -f "aiogram" 2>/dev/null || true

# Trap to kill background processes on exit
trap "kill 0" EXIT

# Wait a moment
sleep 2

echo "Starting web server on port ${PORT:-8080}..."
cd "$SCRIPT_DIR/web"
npm install >/dev/null 2>&1
node server.js > "$LOG_DIR/web.log" 2>&1 &
WEBSERVER_PID=$!

# Wait for web server to start
sleep 3

# Check if web server is running
if ! kill -0 $WEBSERVER_PID 2>/dev/null; then
  echo "❌ Web server failed to start"
  cat "$LOG_DIR/web.log"
  exit 1
fi

echo "✅ Web server running (PID: $WEBSERVER_PID)"

echo "Starting Telegram bot..."
cd "$SCRIPT_DIR/bot"
pip install -r requirements.txt >/dev/null 2>&1
python3 main.py > "$LOG_DIR/bot.log" 2>&1 &
BOT_PID=$!

# Wait a bit for bot to initialize
sleep 2

# Check if bot is running
if ! kill -0 $BOT_PID 2>/dev/null; then
  echo "❌ Telegram bot failed to start"
  tail -n 80 "$LOG_DIR/bot.log"
  exit 1
fi

echo "✅ Telegram bot running (PID: $BOT_PID)"

echo ""
echo "🌐 Web App URL: $PUBLIC_WEBAPP_URL"
echo ""
echo "📋 Process IDs:"
echo "  - Web server: $WEBSERVER_PID"
echo "  - Telegram bot: $BOT_PID"
echo ""
echo "📋 Log files:"
echo "  - Web server: $LOG_DIR/web.log"
echo "  - Telegram bot: $LOG_DIR/bot.log"
echo ""
echo "🔧 To view logs in real-time:"
echo "  tail -f $LOG_DIR/web.log"
echo "  tail -f $LOG_DIR/bot.log"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for processes
wait