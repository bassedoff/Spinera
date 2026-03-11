# Spinora Architecture Documentation

## Project Overview

Spinora is a Telegram-based giveaway platform featuring a "Wheel of Fortune" mechanic. The system consists of three main runtime components: **Telegram Bot (Python)**, **Backend API (Python/FastAPI)**, and **Mini App Frontend (vanilla JS)**.

**Last Updated:** 2026-03-11 (PHASE 2 Complete - Auth & Trust Boundaries)

---

## 1. Project Map by Directories and Layers

### Root Structure
```
New_spinora/
├── bot/                  # Telegram Bot Layer (Python + aiogram)
├── backend/              # Backend API Layer (Python + FastAPI) [NEW in PHASE 1]
├── web/                  # Frontend Only (Node.js serves static files)
├── data/                 # Data Storage Layer (SQLite production + JSON legacy)
├── logs/                 # Application Logs
└── docs/                 # Documentation (NEW)
```

### 1.1 Bot Layer (`bot/`)
**Runtime:** Python 3.x  
**Entry Point:** `bot/main.py`

**Files:**
- `main.py` - Telegram bot command handlers, callback queries, FSM states
- `config.py` - Environment configuration validation
- `storage.py` - **LEGACY** JSON storage operations for users, posts, giveaways
- `requirements.txt` - Python dependencies (aiogram)

**Responsibilities:**
- Handle `/start` command and main menu
- Post creation flow (photo/video/document/text)
- Giveaway preview display with approve/reject buttons
- Web App data handler (legacy wizard_commit support)

### 1.2 Backend API Layer (`backend/`)
**Runtime:** Python 3.8+ (FastAPI)  
**Entry Point:** `backend/main.py`

**Files:**
- `main.py` - FastAPI REST API server, authentication middleware, CRUD endpoints
- `requirements.txt` - Python dependencies (fastapi, uvicorn, pydantic, aiogram)

**Responsibilities:**
- REST API for creator flow
- User authentication via Telegram init data (HMAC-SHA256 validation) ✅ PHASE 2
- Channel resolution and validation
- Giveaway CRUD operations with ownership verification ✅ PHASE 2
- Serve static Mini App frontend
- Unified SQLite data access layer
- Trust boundary enforcement ✅ PHASE 2

**Key Changes in PHASE 1:**
✅ Replaced Node.js/Express backend (`web/server.js`)  
✅ Eliminated cross-runtime import of Python modules  
✅ Consolidated to single storage backend (SQLite)  
✅ Implemented secure Telegram auth signature validation  

**Key Changes in PHASE 2:**
✅ Centralized authentication service (`backend/auth.py`)  
✅ Server-side ownership verification for all entities  
✅ Trust boundary enforcement between frontend and backend  
✅ Unified user context across all endpoints  
✅ Cryptographic validation of Telegram init data (HMAC-SHA256)  
✅ Auth TTL enforcement (24-hour expiry)  

### 1.3 Frontend (`web/public/`)
**Runtime:** Browser (vanilla JavaScript)  
**Served by:** FastAPI static files mount

**Files:**
- `index.html` - Admin Mini App UI (4-step wizard)
- `styles.css` - UI styles
- `app.js` - Frontend logic, API calls to backend, state management

**Note:** Frontend remains unchanged from PHASE 0. Still uses original wizard UI.
### 1.4 Data Layer (`data/`)
**Storage Engine:** SQLite (production)  
**Legacy:** JSON file (transition period only)

**Files:**
- `db_init.py` - Database schema initialization
- `db_manager.py` - SQLite database operations (users, posts, channels, giveaways)
- `validation.py` - Input validation for channels, giveaways, prizes
- `spinora.db` - SQLite database file (exists, ~28KB)
- `storage.json` - **LEGACY** JSON file storage (exists, has test data)

**Database Schema:**
- `users` - Telegram user records
- `post_drafts` - Post content drafts
- `channels` - Connected Telegram channels with bot permissions
- `giveaways` - Giveaway records with JSON fields for channels/prizes

### 1.4 Missing Components
❌ **No public Mini App frontend** - Only admin/creator Mini App exists  
❌ **No participant flow** - No screens for giveaway participants  
❌ **No spin engine** - Wheel spinning logic not implemented  
❌ **No scheduler/worker** - No job queue or scheduled publishing  
❌ **No publish flow** - Preview/approve exists but actual channel posting missing  
❌ **No winners management** - Winner tracking not implemented  

---

## 2. Entry Points

### 2.1 Runtime Entrypoints

**Telegram Bot:**
```bash
cd bot
python main.py
```
- Listens for Telegram updates via aiogram
- Handles user commands and callbacks
- Processes Web App data

**Backend API:**
```bash
cd web
npm start
```
- Starts Express server on PORT (default: 3000 or 8080)
- Serves Mini App at root
- Exposes REST API at `/api/*`

**Startup Scripts:**
- `start_services.sh` (Linux/Mac) - Concurrent bot + web server launch
- `start_services.bat` (Windows) - Windows batch equivalent

### 2.2 API Endpoints

**Creator API (Authenticated):**
- `GET /api/me` - Current user info
- `GET /api/posts?scope=drafts` - User's post drafts
- `POST /api/posts` - Create post draft
- `GET /api/wizard/draft` - Get giveaway wizard draft
- `POST /api/wizard/draft` - Save wizard draft step
- `GET /api/giveaways?scope=created` - User's giveaways
- `POST /api/channels/resolve` - Resolve and save channel
- `GET /api/channels` - Get user's channels
- `POST /api/wizard/commit` - Create finalized giveaway
- `POST /api/giveaways` - **LEGACY** alternative create endpoint

**Public API (Missing):**
- ❌ No public giveaway route
- ❌ No eligibility check endpoint
- ❌ No spin endpoint
- ❌ No result retrieval endpoint

---

## 3. Creator Flow (Current State)

### 3.1 How Creator Flow Works Now

**Step 1: User starts bot**
```
User → /start → bot/main.py:cmd_start()
  ↓
Saves user to JSON storage (bot/storage.py)
  ↓
Displays main menu with Web App button
```

**Step 2: Create post draft**
```
Option A: Via Bot
User sends photo/text → bot/main.py:handle_post()
  ↓
Saves to JSON storage with auto-increment ID

Option B: Via Mini App (future, not used)
Mini App → POST /api/posts → saves to JSON
```

**Step 3: Open Mini App**
```
Click "🧩 Запустить приложение"
  ↓
Telegram Mini App opens → loads web/public/index.html
  ↓
Frontend calls GET /api/me (with DEV_AUTH_BYPASS or real init data)
  ↓
Fetches posts via GET /api/posts
```

**Step 4: Wizard Flow (Admin Mini App)**
```
Step 1: Select type (wheel/case) → saved to giveaway_drafts in JSON
Step 2: Settings (title, language, select post) → saved to JSON
Step 3: Add channels (@username or chat_id) → resolved via POST /api/channels/resolve
         → validates format → saves to channels table in SQLite
Step 4: Add prizes (name, quantity) → saved to JSON draft
  ↓
Click "Создать розыгрыш"
  ↓
POST /api/wizard/commit or POST /api/giveaways
  ↓
Creates giveaway in SQLite via db.create_giveaway()
  ↓
Returns giveaway_id
```

**Step 5: Preview and Approval**
```
Frontend sends web_app_data to bot
  ↓
bot/main.py:handle_web_app_data() receives event "giveaway_preview_request"
  ↓
Calls send_giveaway_preview() → fetches from SQLite
  ↓
Sends post content + giveaway header with approve/reject buttons
  ↓
User clicks approve → callback → updates status to 'approved' in SQLite
  ↓
❌ NO ACTUAL PUBLISHING TO CHANNEL HAPPENS (missing implementation)
```

### 3.2 What's Broken/Incomplete in Creator Flow

**Resolved in PHASE 1:**
✅ **Dual storage writes** - Now writing to SQLite first, JSON only for legacy compatibility  
✅ **No scheduling** - Added start_at/end_at/timezone fields to giveaways schema  
✅ **Inconsistent ID systems** - Standardized on SQLite auto-increment integers  
✅ **Cross-runtime imports** - Replaced Node.js backend with Python/FastAPI  
✅ **Unified storage layer** - All entities now use SQLite as single source of truth  

**Still Broken (Future Phases):**
❌ **No actual publishing** - Approve only changes status, doesn't post to Telegram (PHASE 7)  
❌ **No job queue** - No scheduler for delayed publishing (PHASE 7)  
❌ **Preview uses legacy webhook** - Relies on web_app_data instead of direct API call (transition period)  

---

## 4. Participant Flow (Expected vs Actual)

### 4.1 How Participant Flow SHOULD Work (Design)

```
Participant clicks giveaway link/deeplink
  ↓
Opens Public Mini App (separate from admin app)
  ↓
Loads specific giveaway by slug/token
  ↓
Eligibility check (not ended, hasn't participated, subscribed if required)
  ↓
Displays wheel spin screen
  ↓
Clicks "Spin" button
  ↓
Server calculates result atomically
  ↓
Decrements prize pool if win
  ↓
Saves Spin record + Winner record
  ↓
Returns result to frontend for animation
  ↓
Shows result screen (win/lose)
  ↓
On re-entry: shows already-saved result
```

### 4.2 How Participant Flow Works NOW

**IT DOESN'T EXIST.**

❌ No public Mini App frontend  
❌ No public giveaway route  
❌ No eligibility checking logic  
❌ No spin engine  
❌ No participant/participation tables in database  
❌ No winner tracking  

The participant flow is **completely absent** from the current codebase.

**Update (PHASE 1 Complete):** Schema ready for participant flow (participants, spins, winners tables added). Business logic to be implemented in PHASE 8-9.

---

## 5. Storage Layers Analysis

### 5.1 JSON Storage (LEGACY)

**Location:** `data/storage.json`

**Structure:**
```json
{
  "users": { "<telegram_id>": {...} },
  "post_drafts": { "<telegram_id>": [{id, type, file_id, text}] },
  "giveaway_drafts": { "<telegram_id>": {step, draft} },
  "giveaways": { "<telegram_id>": [{id: "G-0001", status, config}] },
  "channels": { "<telegram_id>": [...] }
}
```

**Used By:**
- `bot/storage.py` - All bot operations
- `web/storage.js` - All backend operations (mirrors bot/storage.py)
- Both runtimes read/write same file → **RACE CONDITION RISK**

**What Uses It:**
- User registration (bot:cmd_start)
- Post draft creation (bot:handle_post)
- Giveaway wizard draft persistence (Mini App steps)
- Legacy giveaway creation (POST /api/giveaways)

**Problems:**
❌ Dual runtime access (Python + Node) to same file  
❌ No transactional guarantees beyond atomic write  
❌ Inconsistent with SQLite data  
❌ Not suitable for production concurrent access  
❌ Schema-less → no validation enforcement  

### 5.2 SQLite Storage (Production)

**Location:** `data/spinora.db`

**Tables:**
- `users` - telegram_id (PK), username, first_name, last_name, created_at
- `post_drafts` - id (PK), telegram_id (FK), type, file_id, text, created_at
- `channels` - id (PK), telegram_id (FK), channel_id, title, username, is_admin, can_post
- `giveaways` - id (PK), telegram_id (FK), title, language, post_draft_id (FK), channels (JSON), prizes (JSON), status, timestamps

**Used By:**
- `data/db_manager.py` - DatabaseManager class
- `bot/main.py` - Imports db for giveaway operations
- `backend/main.py` - All CRUD operations via auth service

**What Uses It:**
- Channel resolution and storage
- Giveaway creation (POST /api/wizard/commit)
- Giveaway retrieval for preview
- Status updates (approve/reject)

---

## 6. Authentication Architecture (PHASE 2)

### 6.1 Auth Flow

```
Telegram Mini App
       ↓
Sends X-Telegram-Init-Data header with every API request
       ↓
Backend AuthService.validate_telegram_init_data()
       ↓
1. Parse URL-encoded parameters
2. Extract user JSON and hash
3. Calculate HMAC-SHA256 using BOT_TOKEN
4. Compare hashes (constant-time)
5. Check auth_date TTL (24 hours)
       ↓
If valid: Extract user identity + sync to DB
If invalid: Return 401 Unauthorized
       ↓
Request handler receives authenticated user dict
```

### 6.2 Trust Boundaries

**Frontend Responsibility:**
- Send valid Telegram init data with every request
- Provide entity IDs (channel_id, giveaway_id, post_draft_id)
- Submit user-generated content (titles, descriptions, prizes)

**Backend Responsibility:**
- Cryptographically verify user identity
- Verify ownership of all referenced entities
- Validate business rules (permissions, eligibility)
- Prevent unauthorized access even with valid ID

### 6.3 What Backend Does NOT Trust

❌ **Raw User Identity**
- Frontend sends: `{"id": 123, "username": "test"}`
- Backend does: HMAC-SHA256 validation before extraction
- Why: Client can forge any JSON

❌ **Entity Ownership Claims**
- Frontend sends: `giveaway_id: 5`
- Backend does: Query DB to verify `giveaway.telegram_id == user.id`
- Why: Knowing an ID doesn't grant ownership rights

❌ **Channel Permissions**
- Frontend sends: `channel_id: -1001234567890`
- Backend does: Check `is_admin` and `can_post` flags from DB
- Why: Client cannot verify bot permissions

❌ **Eligibility/Results (Future)**
- Frontend will send: `has_participated: false`
- Backend will: Query spins table atomically
- Why: Fraud prevention (PHASE 9)

### 6.4 Centralized Auth Service

**File:** `backend/auth.py`

**AuthService Class:**
- `validate_telegram_init_data()` — Cryptographic validation
- `get_current_user()` — Extract authenticated user
- `verify_ownership()` — Check entity ownership
- `verify_channel_access()` — Verify channel permissions
- `can_user_create_giveaway()` — Bulk permission check

**Benefits:**
- Single source of truth for auth logic
- Consistent error responses (401 vs 403)
- Easy to audit and test
- No code duplication across endpoints

---

## 7. Channel Connection Architecture (PHASE 3)

### 7.1 Channel Connection Flow

```
Creator (Mini App)
       ↓
POST /api/channels/connect/initiate {identifier: "@channel"}
       ↓
Backend ChannelService.get_bot_info()
       ↓
Returns deep link: https://t.me/BotUsername?startgroup=true
       ↓
User clicks link → Adds bot to channel via Telegram
       ↓
POST /api/channels/connect/verify {identifier: "@channel"}
       ↓
ChannelService.verify_channel() performs checks:
1. get_chat_info() — Channel exists?
2. get_chat_member() — Bot is member?
3. Check status — Bot is admin?
4. Check permissions — Bot can post?
       ↓
All checks pass → save_verified_channel() to database
       ↓
Channel ready for giveaways!
```

### 7.2 Verification Steps

**Step 1: Channel Existence**
- Call Telegram API `getChat(chat_id)`
- Validate channel type (channel/supergroup)
- Extract metadata (title, username, members_count)

**Step 2: Bot Membership**
- Call Telegram API `getChatMember(chat_id, bot_user_id)`
- Verify bot status != 'left'
- Ensure bot is actually in the channel

**Step 3: Administrator Status**
- Check member status == 'administrator'
- Reject if bot is just a member
- Admin rights required for posting

**Step 4: Posting Permissions**
- Verify `can_post_messages` == true
- Check additional permissions (edit, delete, pin)
- Store permissions snapshot in database

### 7.3 Channel Service

**File:** `backend/channel_service.py`

**ChannelService Class:**
- `get_chat_info()` — Get channel metadata from Telegram
- `get_chat_member_info()` — Get bot membership status
- `get_bot_info()` — Get bot's own user info
- `verify_channel()` — Full verification workflow
- `save_verified_channel()` — Save to database with status
- `get_user_channels_with_status()` — List channels with computed status
- `reverify_channel()` — Re-check existing channel permissions

### 7.4 Channel Status Model

**Status Values:**
- `active` — Bot is admin AND can post (ready for giveaways)
- `limited` — Bot is admin but cannot post (needs permission fix)
- `inactive` — Bot is not admin or verification failed

**Database Fields:**
```sql
channels (
  id,
  telegram_id (owner),
  channel_id (Telegram chat ID),
  title,
  username,
  type,
  bot_is_admin,
  bot_can_post,
  permissions_snapshot (JSON),
  members_count,
  is_active,
  verified_at,
  last_permission_check_at,
  created_at,
  updated_at
)
```

### 7.5 Trust Boundaries

**What Backend Does NOT Trust:**
❌ Client claims about channel ownership
❌ Raw channel_id without verification
❌ Assumed bot permissions
✅ Server verifies ALL via Telegram API
✅ Server stores verified state in database
✅ Server computes status from actual permissions

### 7.6 Idempotent Verification

**Repeated verification of same channel:**
- Updates existing record (no duplicates)
- Refreshes permissions snapshot
- Updates timestamps (verified_at, last_permission_check_at)
- Maintains data consistency

### 7.7 Negative Scenarios Handled

✅ Channel not found → Clear error message
✅ Bot not member → Instructions to add bot
✅ Bot not admin → Request admin rights
✅ Bot cannot post → Permission configuration needed
✅ Channel already connected → Update instead of duplicate
✅ Wrong user verifying → Ownership check fails
✅ Telegram API errors → Graceful error handling
✅ Username changed → Resolved via current API call
✅ Permissions lost after connect → Detected on reverify

---

## 8. Runtime Incompatibilities

### 6.1 Critical Conflicts

**RESOLVED in PHASE 1:**

✅ **Dual Storage Access** - Eliminated by removing Node.js backend  
✅ **Mixed Storage Backends** - Consolidated to SQLite as single source of truth  
✅ **Authentication Mismatch** - Implemented proper HMAC-SHA256 validation in FastAPI  
✅ **Cross-Runtime Imports** - Replaced Node.js with Python/FastAPI  

**Legacy Compatibility (Temporary):**
⚠️ Bot still writes to JSON during PHASE 1 transition (marked for removal in PHASE 3)  
⚠️ Frontend still uses old wizard_commit webhook pattern (direct API calls preferred)
```
bot/main.py → storage = Storage(Config.STORAGE_PATH)
              ↓
              Reads/writes data/storage.json

web/server.js → storage = new Storage(path.join(__dirname, '..', 'data', 'storage.json'))
                ↓
                Reads/writes SAME data/storage.json
```

**Problem:** Both Python and Node processes access the same JSON file concurrently without coordination → **DATA CORRUPTION RISK**

**2. Mixed Storage Backends**
```
Channel creation:
  POST /api/channels/resolve → saves to SQLite (db.resolve_and_save_channel)
  
Giveaway creation:
  POST /api/wizard/commit → saves to SQLite (db.create_giveaway)
  BUT also saves to JSON via legacy endpoint POST /api/giveaways

Bot preview:
  Fetches from SQLite (db.get_giveaway)
  
User data:
  Saved to JSON (storage.save_user in bot:cmd_start)
  Never synced to SQLite unless explicitly called
```

**Problem:** Data lives in two places → **INCONSISTENCY GUARANTEED**

**3. Authentication Mismatch**
```
web/server.js:authenticateUser()
  ↓
  DEV_MODE: Uses hardcoded DEV_TELEGRAM_ID
  PROD_MODE: Parses init data WITHOUT signature validation (line 40-41 comment says "will add later")
  
bot/main.py
  ↓
  No auth needed - trusts Telegram user context implicitly
```

**Problem:** Backend auth is insecure - accepts forged init data → **SECURITY VULNERABILITY**

### 6.2 Import Dependencies

**Cross-Runtime Calls:**
```python
# bot/main.py imports from data/
from data.db_manager import db  # ✓ OK - Python module
```

```javascript
// web/server.js imports from data/
const { db } = require('../data/db_manager');  // ❌ WRONG - tries to require Python module
```

**Wait - this should fail!** Let me check if there's a JS version...

Actually, looking at line 8 of server.js:
```javascript
const { db } = require('../data/db_manager');
```

This is trying to import a Python module into Node.js - **THIS SHOULD CRASH**. But the file exists and runs... This needs investigation. Either:
1. There's a compiled/bundled version I didn't see
2. The code never actually executes this path
3. There's a magic bridge I'm unaware of

**RESOLVED in PHASE 1:**

The critical cross-runtime import bug has been **completely eliminated** by:
1. Creating new Python/FastAPI backend (`backend/main.py`)
2. Removing Node.js backend (`web/server.js` deprecated)
3. Both bot and backend now use same Python runtime
4. No more impossible imports

**Old Architecture (Broken):**
```
Node.js backend → tries to import → Python db_manager ❌ CRASH
```

**New Architecture (Working):**
```
Python FastAPI backend → imports → Python db_manager ✓ WORKS
Python Bot → imports → Python db_manager ✓ WORKS
Both share same SQLite database ✓ CONSISTENT
```

---

## 7. Legacy Freeze Section

### 7.1 What Is Considered LEGACY

**DO NOT EXTEND OR BUILD UPON THESE MODULES:**

#### JSON Storage Layer
**Files:** `bot/storage.py`, `web/storage.js`, `data/storage.json`

**Why Legacy:**
- Dual runtime access was fundamentally broken (Python + Node)
- Not suitable for production scale
- Incompatible with relational data model
- Zero transactional integrity

**Mark As Deprecated:**
- `Storage` class in both Python and JS
- All methods: `save_user`, `save_post_draft`, `create_giveaway`, etc.
- `counters` pattern (use DB auto-increment instead)

**Migration Path:**
- ✅ PHASE 1: Move all reads/writes to SQLite via `db_manager.py`
- ⚠️ PHASE 1: Keep JSON read-only for backward compatibility during transition
- ❌ PHASE 3: Remove JSON dependency entirely

**Current Status (PHASE 1):**
- Bot still writes to JSON for backward compatibility (marked with `# LEGACY` comments)
- New code should ONLY use SQLite
- JSON will be fully removed in PHASE 3

#### Legacy Giveaway Creation Endpoint
**File:** `web/server.js` lines 247-263  
**Endpoint:** `POST /api/giveaways`

**Why Legacy:**
- Saves to JSON instead of SQLite
- Bypasses validation layer
- Uses old config structure without proper fields

**Replace With:**
- `POST /api/wizard/commit` which uses SQLite + validation

#### Web App Data Handler in Bot
**File:** `bot/main.py` lines 277-315  
**Handler:** `handle_web_app_data()`

**Why Legacy:**
- Receives structured data via Telegram message instead of direct API call
- Creates giveaway in JSON storage (line 299: `storage.create_giveaway`)
- Duplicates logic that should live in backend API

**Replace With:**
- Direct API call from frontend to `POST /api/wizard/commit`
- Remove webhook-style data passing through bot

#### Insecure Auth Parsing
**File:** `web/server.js` lines 34-56  
**Function:** `authenticateUser()`

**Why Legacy:**
- No signature validation (line 40 comment admits this)
- Trusts client-provided init data blindly
- Vulnerable to forgery attacks

**Replace With:**
- Proper HMAC-SHA256 signature verification using BOT_TOKEN
- Server-side user identity extraction after validation
- TTL enforcement on init data timestamps

#### Wizard Draft System
**Files:** `bot/storage.py` lines 109-126, `web/storage.js` lines 129-146  
**Methods:** `save_giveaway_draft()`, `get_giveaway_draft()`

**Why Legacy:**
- Stores partial wizard state in JSON
- Tied to specific UI step sequence
- Not needed if wizard commits directly to DB

**Replace With:**
- Direct DB writes on each step (optional - could keep session-based draft)
- Or remove draft entirely and require single-shot creation

### 7.2 What Must Be Rewritten, Not Patched

**COMPLETED in PHASE 1:**

✅ **1. Cross-Runtime Module Import** - RESOLVED by creating Python/FastAPI backend  
✅ **2. Dual Storage Logic** - RESOLVED by consolidating to SQLite  
⚠️ **3. Frontend-Backend Contract** - PARTIALLY resolved (legacy webhook still works, but direct API preferred)

**Implementation Details:**
- Created `backend/main.py` (FastAPI) replacing `web/server.js` (Node.js)
- All new code uses SQLite via `db_manager.py`
- Legacy JSON writes marked with `# LEGACY` comments for future removal

**Problem:** Indirect, insecure, duplicates logic.

**Must Rewrite To:** Frontend → Backend API → SQLite direct flow.

### 7.3 What Can Be Kept (With Modifications)

**Safe To Retain:**

✅ **Database Schema** - Core tables are well-designed, just need extension  
✅ **Validation Layer** - `data/validation.py` is solid, runtime-agnostic  
✅ **Bot Command Handlers** - `/start`, post creation logic is sound  
✅ **Mini App UI** - Frontend wizard is functional, just needs backend contract update  
✅ **Preview/Approvers Flow** - Concept works, just needs direct API integration  

---

## 8. Architectural Blockers Summary

### P0 Blockers — RESOLVED in PHASE 1 ✅

**1. Cross-Runtime Import Crash** ✅ FIXED
- Location: `web/server.js:8`
- Solution: Created Python/FastAPI backend (`backend/main.py`)
- Result: No more impossible imports

**2. Insecure Authentication** ✅ FIXED
- Location: Old `web/server.js:authenticateUser()`
- Solution: Implemented HMAC-SHA256 validation in FastAPI
- Result: Proper Telegram init data signature verification

**3. Dual Storage Race Conditions** ✅ FIXED
- Location: `data/storage.json`
- Solution: Consolidated to SQLite as single source of truth
- Result: No more concurrent access conflicts

**4. Missing Participant Infrastructure** ✅ SCHEMA READY
- Location: Database schema
- Solution: Added tables (participants, spins, winners, jobs, audit_logs)
- Result: Schema ready for PHASE 8-9 implementation

### P1 Blockers — Partially Resolved

**5. No Publishing Mechanism** ❌ STILL BROKEN (PHASE 7)
- Location: `bot/main.py:approve_giveaway_callback()`
- Impact: Giveaways never actually published to channels
- Fix: Implement Telegram channel posting + job queue

**6. No Scheduling Support** ✅ SCHEMA READY (PHASE 7)
- Location: Database schema
- Status: Fields added (start_at, end_at, timezone)
- Remaining: Scheduler worker implementation

**7. No Public Route** ❌ STILL BROKEN (PHASE 8)
- Location: Missing from backend + frontend
- Impact: Participants cannot access giveaways
- Fix: Create public giveaway endpoint + separate Mini App

---

## 9. Recommended Target Architecture

### Single-Runtime Approach (Recommended)

```
┌─────────────────────────────────────┐
│      Telegram Bot (aiogram)         │
│                                     │
│  ┌─────────────────────────────┐   │
│  │   FastAPI Backend Server    │   │
│  │   - REST API                │   │
│  │   - Auth Middleware         │   │
│  │   - Scheduler (APScheduler) │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │   SQLite/PostgreSQL         │   │
│  │   - SQLAlchemy ORM          │   │
│  │   - Alembic Migrations      │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
           ↕ serves static files
┌─────────────────────────────────────┐
│   Mini App Frontend (vanilla JS)    │
│   - Admin App                       │
│   - Public App                      │
└─────────────────────────────────────┘
```

**Benefits:**
- Single language (Python)
- No cross-runtime imports
- Unified storage layer
- Easier deployment

---

## 10. Next Steps (PHASE 1 Priorities)

Based on this inventory, the immediate priorities are:

1. **TASK-010**: Fix cross-runtime import crash
   - Decision: Rewrite backend in Python (FastAPI) or create HTTP bridge
   
2. **TASK-011**: Consolidate storage to SQLite only
   - Migrate all JSON reads/writes to DB
   - Deprecate Storage classes

3. **TASK-012**: Extend database schema
   - Add missing fields (start_at, end_at, timezone, public_slug)
   - Add missing tables (participants, spins, winners, jobs)

4. **TASK-020**: Implement secure auth
   - Add HMAC-SHA256 validation
   - Extract user identity server-side

5. **TASK-080**: Build public participant flow
   - Separate public Mini App
   - Public giveaway API endpoint

---

*Document Created: 2026-03-11*  
*Status: Initial Inventory Complete*
