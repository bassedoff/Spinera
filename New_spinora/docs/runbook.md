# Spinora Runbook

## Quick Start

### Prerequisites

**Required:**
- Python 3.8+ (for bot and backend)
- Node.js 16+ (for frontend only, not backend)
- Telegram Bot Token from @BotFather

**Optional:**
- Virtual environment tool (venv, virtualenv)
- GitHub Codespaces (for cloud development)

**Last Updated:** 2026-03-11 (PHASE 3 Complete)

---

## Local Development Setup

### Step 1: Environment Configuration

Copy and configure environment variables:

```bash
cp .env.example .env
```

Edit `.env`:
```env
# Required
BOT_TOKEN=your_bot_token_from_botfather
PUBLIC_WEBAPP_URL=https://your-domain.com

# Optional (for local development)
PORT=8080
DEV_AUTH_BYPASS=1
DEV_TELEGRAM_ID=123456789
DEV_USERNAME=testuser
DEV_FIRST_NAME=Test
TZ=Europe/Moscow
```

**Important for PHASE 1:**
- `DEV_AUTH_BYPASS=1` enables local testing without real Telegram auth
- Change to `0` in production

---

### Step 2: Install Dependencies

**Backend (Python):**
```bash
cd backend
pip install -r requirements.txt
```

**Bot (Python):**
```bash
cd bot
pip install -r requirements.txt
```

**Frontend (Node.js - static files only):**
```bash
cd web
npm install
```

---

### Step 3: Initialize Database

The database auto-initializes on first backend start, or manually:

```bash
cd data
python db_init.py
```

Expected output:
```
Database initialized at /path/to/data/spinora.db
```

---

### Step 4: Start Services

**Option A: Using Startup Scripts (Recommended)**

Linux/Mac:
```bash
chmod +x start_services.sh
./start_services.sh
```

Windows:
```cmd
start_services.bat
```

**Option B: Manual Start**

Terminal 1 - Backend:
```bash
cd backend
python main.py
```

Terminal 2 - Bot:
```bash
cd bot
python main.py
```

---

### Step 5: Verify Running Services

**Check Health:**
```bash
curl http://localhost:8080/api/health
```

Expected response:
```json
{"ok": true, "status": "running"}
```

**Access Mini App:**
Open browser: `http://localhost:8080`

**Check Logs:**
- Backend: Console output (no separate log file yet)
- Bot: `logs/bot.log`

---

## Architecture Changes (PHASE 1)

### What Changed

**Before PHASE 1:**
```
┌─────────────┐      ┌──────────────┐
│  Bot (Py)   │      │ Web (Node.js)│
│             │      │              │
│ storage.py  │◄────►│ storage.js   │
│   (JSON)    │      │   (JSON)     │
└─────────────┘      └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │data/db_manager│
                     │   (Python!)  │ ← ❌ Cross-runtime import!
                     └──────────────┘
```

**After PHASE 1:**
```
┌─────────────┐      ┌──────────────┐
│  Bot (Py)   │      │Backend (FastAPI)
│             │      │              │
│ db_manager  │◄────►│ db_manager   │
│   (SQLite)  │      │   (SQLite)   │
└─────────────┘      └──────────────┘
         │                    │
         └────────────────────┘
                  │
                  ▼
          ┌──────────────┐
          │   SQLite DB  │
          │ spinora.db   │
          └──────────────┘
```

### Key Differences

1. **Node.js Backend Eliminated**
   - Old: `web/server.js` tried to import Python modules ❌
   - New: `backend/main.py` (FastAPI) ✓

2. **Unified Storage**
   - Old: JSON + SQLite (dual write, race conditions)
   - New: SQLite only (single source of truth)

3. **Legacy JSON Status**
   - Still written by bot during PHASE 1 transition
   - Marked with `# LEGACY` comments
   - Will be removed in PHASE 3

---

## Testing Channel Connection (PHASE 3)

### Prerequisites for Channel Testing

**Bot Configuration:**
1. Bot must be created via @BotFather
2. Bot token configured in `.env`
3. Bot must have a username (not just ID)
4. Bot privacy mode should allow adding to channels

**Test Channel Setup:**
1. Create a test Telegram channel (public or private)
2. Make bot an administrator with posting permissions
3. Note the channel username (e.g., `@test_channel`)

---

### Test Scenario 1: Initiate Channel Connection

**Request:**
```bash
curl -X POST http://localhost:8080/api/channels/connect/initiate \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Init-Data: $INIT_DATA" \
  -d '{"identifier": "@test_channel"}'
```

**Expected Response:**
```json
{
  "step": 1,
  "action": "add_bot_to_channel",
  "channel": "@test_channel",
  "bot_username": "SpinoraBot",
  "deep_link": "https://t.me/SpinoraBot?startgroup=true",
  "required_rights": [
    "Post messages",
    "Edit messages",
    "Delete messages",
    "Pin messages"
  ],
  "instructions": [
    "Click the button to add @SpinoraBot to your channel",
    "Select your channel from the list",
    "Grant administrator rights to the bot",
    "Ensure bot has permission to post messages",
    "Return to this page and click 'Verify Connection'"
  ]
}
```

**What to Verify:**
- ✅ Deep link is properly formatted
- ✅ Bot username is correct
- ✅ Instructions are clear
- ✅ Required rights are listed

---

### Test Scenario 2: Verify Channel Connection

**Prerequisites:**
- Bot has been added to channel as admin
- Bot has posting permissions enabled

**Request:**
```bash
curl -X POST http://localhost:8080/api/channels/connect/verify \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Init-Data: $INIT_DATA" \
  -d '{"identifier": "@test_channel"}'
```

**Expected Success Response:**
```json
{
  "success": true,
  "channel_id": 1,
  "channel": {
    "chat_id": -1001234567890,
    "title": "Test Channel",
    "username": "test_channel",
    "type": "channel",
    "is_admin": true,
    "can_post": true,
    "permissions_snapshot": {
      "can_post_messages": true,
      "can_edit_messages": true,
      "can_delete_messages": true,
      "can_restrict_members": false,
      "can_promote_members": false,
      "can_change_info": false,
      "can_invite_users": true,
      "can_pin_messages": true
    },
    "members_count": 15,
    "verified_at": "2026-03-11T10:00:00Z"
  }
}
```

**What to Verify:**
- ✅ All verification steps pass
- ✅ Permissions snapshot is complete
- ✅ Channel metadata is captured
- ✅ Database record created

---

### Test Scenario 3: Get User Channels

**Request:**
```bash
curl -X GET http://localhost:8080/api/channels \
  -H "X-Telegram-Init-Data: $INIT_DATA"
```

**Expected Response:**
```json
[
  {
    "id": 1,
    "channel_id": -1001234567890,
    "title": "Test Channel",
    "username": "test_channel",
    "type": "channel",
    "bot_is_admin": true,
    "bot_can_post": true,
    "permissions_snapshot": {
      "can_post_messages": true,
      "can_edit_messages": true,
      "can_delete_messages": true
    },
    "members_count": 15,
    "is_active": true,
    "status": "active",
    "can_use_for_giveaway": true,
    "verified_at": "2026-03-11T10:00:00Z",
    "last_permission_check_at": "2026-03-11T10:00:00Z",
    "created_at": "2026-03-11T09:00:00Z"
  }
]
```

**What to Verify:**
- ✅ Status field computed correctly (`active`/`limited`/`inactive`)
- ✅ Permissions snapshot preserved
- ✅ Timestamps are accurate
- ✅ `can_use_for_giveaway` matches status

---

### Test Scenario 4: Re-verify Existing Channel

**Request:**
```bash
curl -X POST http://localhost:8080/api/channels/1/reverify \
  -H "X-Telegram-Init-Data: $INIT_DATA"
```

**Expected Response:**
```json
{
  "success": true,
  "channel": {
    "id": 1,
    "channel_id": -1001234567890,
    "title": "Test Channel",
    "username": "test_channel",
    "bot_is_admin": true,
    "bot_can_post": true,
    "status": "active",
    "can_use_for_giveaway": true,
    "last_permission_check_at": "2026-03-11T11:00:00Z"
  }
}
```

**What to Verify:**
- ✅ Permissions re-checked
- ✅ Timestamp updated
- ✅ No duplicate records created
- ✅ Status still accurate

---

### Negative Test Scenarios

#### Error Case 1: Channel Not Found
```json
{
  "detail": "Channel not found. Make sure the username is correct or the channel is public."
}
```

#### Error Case 2: Bot Not Member
```json
{
  "detail": "Bot is not a member of this channel. Please add the bot first."
}
```

#### Error Case 3: Bot Not Admin
```json
{
  "detail": "Bot must be an administrator in the channel."
}
```

#### Error Case 4: Cannot Post Messages
```json
{
  "detail": "Bot must have permission to post messages in the channel."
}
```

---

### Manual Verification Checklist

**Before marking channel as connected:**
- [ ] Channel exists in Telegram
- [ ] Bot is member of channel
- [ ] Bot has administrator status
- [ ] Bot can post messages permission granted
- [ ] Channel saved to database with all fields
- [ ] Status computed as `active` if all checks pass
- [ ] Permissions snapshot captured
- [ ] Timestamps recorded

**Database Verification:**
```sql
SELECT * FROM channels WHERE telegram_id = YOUR_USER_ID;
```

Check fields:
- ✅ `bot_is_admin` = 1
- ✅ `bot_can_post` = 1
- ✅ `is_active` = 1
- ✅ `permissions_snapshot` contains JSON
- ✅ `verified_at` is recent
- ✅ `status` = 'active'

---

## API Endpoints

### Authentication

All endpoints (except `/api/health`) require authentication via Telegram init data.

**Header:** `X-Telegram-Init-Data`

**Dev Mode (DEV_AUTH_BYPASS=1):**
No validation performed, uses hardcoded test user.

**Production Mode:**
Validates HMAC-SHA256 signature using BOT_TOKEN.

---

### Public Endpoints

#### GET /
Serves Mini App frontend (`web/public/index.html`)

#### GET /api/health
Health check.

**Response:**
```json
{
  "ok": true,
  "status": "running"
}
```

---

### Creator Endpoints (Authenticated)

#### GET /api/me
Get current user info.

**Response:**
```json
{
  "telegram_id": 123456789,
  "username": "testuser",
  "first_name": "Test",
  "last_name": "",
  "created_at": "2026-03-11T00:00:00Z"
}
```

---

#### GET /api/posts?scope=drafts
Get user's post drafts.

**Parameters:**
- `scope` (optional): `drafts` (default), other values TBD

**Response:**
```json
[
  {
    "id": 1,
    "telegram_id": 123456789,
    "type": "photo",
    "file_id": "AgAD...",
    "text": "My giveaway post!",
    "created_at": "2026-03-11T00:00:00Z"
  }
]
```

---

#### POST /api/posts
Create a new post draft.

**Request:**
```json
{
  "type": "photo",
  "file_id": "AgAD...",
  "text": "Giveaway announcement"
}
```

**Response:**
```json
{
  "id": 1
}
```

---

#### GET /api/channels
Get user's connected channels.

**Response:**
```json
[
  {
    "id": -1001234567890,
    "title": "My Channel",
    "username": "mychannel",
    "bot_is_admin": true,
    "bot_can_post": true
  }
]
```

---

#### POST /api/channels/resolve
Resolve channel identifier and save.

**Request:**
```json
{
  "identifier": "@mychannel"
}
```

**Response (Dev Mode):**
```json
{
  "id": -1001234567890,
  "title": "Channel @mychannel",
  "username": "mychannel",
  "bot_is_admin": true,
  "bot_can_post": true
}
```

**Production Mode:** Returns 501 Not Implemented (requires Telegram API integration)

---

#### GET /api/giveaways?scope=created
Get user's giveaways.

**Parameters:**
- `scope` (optional): `created` (default), `active`, `ended`, etc.

**Response:**
```json
[
  {
    "id": 1,
    "telegram_id": 123456789,
    "title": "My Giveaway",
    "description": null,
    "language": "en",
    "type": "wheel",
    "post_draft_id": 1,
    "channels": [-1001234567890],
    "prizes": [{"name": "Prize", "qty": 3}],
    "start_at": null,
    "end_at": null,
    "timezone": "UTC",
    "status": "draft",
    "public_slug": null,
    "published_message_id": null,
    "created_at": "2026-03-11T00:00:00Z",
    "updated_at": "2026-03-11T00:00:00Z"
  }
]
```

---

#### GET /api/giveaways/{giveaway_id}
Get specific giveaway by ID.

**Response:** Same structure as above.

**Errors:**
- 404: Giveaway not found
- 403: Access denied (not owner)

---

#### POST /api/wizard/commit
Create finalized giveaway from wizard.

**Request:**
```json
{
  "title": "iPhone Giveaway",
  "language": "en",
  "post_draft_id": 1,
  "channels": [-1001234567890],
  "prizes": [
    {
      "name": "iPhone 15",
      "qty": 1,
      "description": "Latest model",
      "weight": 10
    }
  ]
}
```

**Validation Rules:**
- `title`: 3-100 characters
- `language`: one of `en`, `ru`, `kz`
- `post_draft_id`: required, must exist
- `channels`: at least 1 channel ID
- `prizes`: at least 1 prize with:
  - `name`: required
  - `qty`: positive integer

**Response:**
```json
{
  "giveaway_id": 1
}
```

**Errors:**
- 400: Validation failed (check `X-Validation-Errors` header)
- 500: Database error

---

#### GET /api/wizard/draft
Get user's giveaway wizard draft.

**Response:**
```json
{}
```

Currently returns empty object (placeholder for session-based draft)

---

#### POST /api/wizard/draft
Save wizard draft step.

**Request:**
```json
{
  "step": 2,
  "draft": {
    "title": "My Giveaway",
    "language": "en"
  }
}
```

**Response:**
```json
{
  "success": true
}
```

---

## Troubleshooting

### Backend Won't Start

**Error: Module not found**
```bash
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```bash
cd backend
pip install -r requirements.txt
```

---

**Error: Address already in use**
```
OSError: [Errno 98] Address already in use
```

**Solution:**
```bash
# Find process using port 8080
lsof -i :8080

# Kill it
kill -9 <PID>

# Or change port in .env
PORT=8081
```

---

### Bot Won't Start

**Error: Invalid bot token**
```
aiogram.exceptions.TelegramUnauthorizedError: Unauthorized
```

**Solution:**
1. Check `BOT_TOKEN` in `.env` is correct
2. Get new token from @BotFather
3. Restart bot

---

**Error: Can't find db_manager**
```
ModuleNotFoundError: No module named 'data.db_manager'
```

**Solution:**
Make sure you're running bot from project root or add parent directory to Python path:
```bash
# From project root
PYTHONPATH=. python bot/main.py
```

---

### Database Issues

**Error: Table doesn't exist**
```
sqlite3.OperationalError: no such table: giveaways
```

**Solution:**
```bash
cd data
python db_init.py
```

---

**Error: Duplicate column**
```
sqlite3.OperationalError: duplicate column name
```

**Cause:** Migration script ran twice.

**Solution:** Safe to ignore — column already exists.

---

### Frontend Issues

**Blank page / Nothing loads**

**Check:**
1. Backend is running: `curl http://localhost:8080/api/health`
2. Browser console for JavaScript errors
3. `DEV_AUTH_BYPASS=1` if testing locally

---

**Authentication errors**

**In Production:**
```
401 Unauthorized: Invalid init data
```

**Cause:** Telegram init data signature validation failed.

**Solution:**
- Ensure `BOT_TOKEN` matches the bot
- Check system time is synchronized
- Verify Telegram WebApp is sending correct init data

**In Development:**
Set `DEV_AUTH_BYPASS=1` to skip validation.

---

## Common Tasks

### Reset Database

**Warning:** Deletes all data!

```bash
rm data/spinora.db
cd data
python db_init.py
```

---

### View Logs

**Bot logs:**
```bash
tail -f logs/bot.log
```

**Backend logs:**
Currently console output only (consider adding file logging in future)

---

### Backup Data

```bash
# Backup database
cp data/spinora.db data/spinora.db.backup.$(date +%Y%m%d)

# Backup JSON storage (legacy)
cp data/storage.json data/storage.json.backup.$(date +%Y%m%d)
```

---

### Test Authentication

**Dev Mode:**
```bash
curl http://localhost:8080/api/me \
  -H "X-Telegram-Init-Data: dummy"
```

Should return test user data.

**Production Mode:**
Requires valid Telegram init data with signature. Use Telegram Mini App.

---

## Deployment Checklist

### Pre-Deployment

- [ ] Set `DEV_AUTH_BYPASS=0`
- [ ] Set production `PUBLIC_WEBAPP_URL`
- [ ] Use strong `BOT_TOKEN` (keep secret!)
- [ ] Test all API endpoints
- [ ] Run database migrations
- [ ] Set up log rotation
- [ ] Configure backup strategy

### Production Environment

**Required Packages:**
```bash
# Backend
pip install fastapi uvicorn pydantic python-dotenv aiogram

# System dependencies
apt-get install python3-pip sqlite3
```

**Systemd Service (Backend):**
```ini
[Unit]
Description=Spinora Backend API
After=network.target

[Service]
Type=simple
User=spinora
WorkingDirectory=/opt/spinora/backend
Environment=PATH=/opt/spinora/venv/bin
ExecStart=/opt/spinora/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**Systemd Service (Bot):**
```ini
[Unit]
Description=Spinora Telegram Bot
After=network.target

[Service]
Type=simple
User=spinora
WorkingDirectory=/opt/spinora/bot
Environment=PATH=/opt/spinora/venv/bin
ExecStart=/opt/spinora/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Telegram-Init-Data $http_x_telegram_init_data;
    }
}
```

---

## Monitoring

### Health Checks

**Endpoint:** `/api/health`

**Monitoring Script:**
```bash
#!/bin/bash
response=$(curl -s http://localhost:8080/api/health)
if echo "$response" | grep -q '"ok": true'; then
    echo "✓ Backend healthy"
    exit 0
else
    echo "✗ Backend unhealthy"
    exit 1
fi
```

Add to cron:
```bash
*/5 * * * * /opt/spinora/scripts/healthcheck.sh || systemctl restart spinora-backend
```

---

### Database Size

```bash
du -h data/spinora.db
```

Alert if growing too fast (could indicate issue).

---

## Rollback Procedures

### If Backend Update Fails

1. Stop services:
   ```bash
   sudo systemctl stop spinora-backend
   ```

2. Revert code:
   ```bash
   cd /opt/spinora
   git checkout <previous-tag>
   ```

3. Restore database:
   ```bash
   cp data/spinora.db.backup data/spinora.db
   ```

4. Restart:
   ```bash
   sudo systemctl start spinora-backend
   ```

---

## Support Contacts

**Technical Issues:**
- Check logs first
- Review this runbook
- Consult `docs/architecture.md` and `docs/domain-model.md`

**Telegram Bot Issues:**
- Contact @BotFather support
- Check Telegram API status

---

*Document Created: 2026-03-11*  
*Last Updated: 2026-03-11*  
*Version: 1.0*
