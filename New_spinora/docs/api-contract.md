# Spinora API Contract

## Overview

This document describes the API contracts, authentication mechanisms, and trust boundaries for the SpinoraBot platform.

**Last Updated:** 2026-03-11 (PHASE 3 Complete)

---

## Authentication

### Telegram Mini App Authentication

All authenticated endpoints require Telegram WebApp init data to be passed via the `X-Telegram-Init-Data` header.

**Header:** `X-Telegram-Init-Data`

**Format:** URL-encoded string from Telegram WebApp

**Example:**
```
auth_date=1234567890&user=%7B%22id%22%3A123456789%2C%22first_name%22%3A%22Test%22%7D&hash=abc123...
```

### Validation Process

Backend validates Telegram init data using HMAC-SHA256:

1. Parse URL-encoded parameters
2. Extract `user` JSON and `hash`
3. Calculate expected hash using BOT_TOKEN
4. Compare with received hash (constant-time comparison)
5. Check auth_date TTL (24 hours)
6. Extract user identity only after successful validation

**Security Properties:**
- ✅ Never trusts raw user payload
- ✅ Validates cryptographic signature
- ✅ Rejects expired auth data
- ✅ Constant-time hash comparison (prevents timing attacks)

### Development Mode

When `DEV_AUTH_BYPASS=1`, backend uses hardcoded test user:

```json
{
  "id": 123456789,
  "username": "testuser",
  "first_name": "Test",
  "last_name": "",
  "is_authenticated": true
}
```

⚠️ **WARNING:** Never enable in production!

---

## User Context

After successful authentication, request handlers receive:

```python
{
  "id": int,              # Telegram ID
  "username": str,        # Username (may be empty)
  "first_name": str,      # First name
  "last_name": str,       # Last name (may be empty)
  "is_authenticated": True
}
```

**Guarantees:**
- User identity is cryptographically verified
- User record exists in database
- Consistent format across all endpoints

---

## Error Responses

### Authentication Errors

#### 401 Unauthorized — No Init Data
```json
{
  "detail": "Unauthorized: No init data provided"
}
```
**HTTP Headers:**
```
WWW-Authenticate: TelegramInitData
```

#### 401 Unauthorized — Invalid Init Data
```json
{
  "detail": "Unauthorized: Invalid Telegram init data"
}
```
**HTTP Headers:**
```
WWW-Authenticate: TelegramInitData
```

**Causes:**
- Missing `hash` parameter
- Hash mismatch (tampering or wrong BOT_TOKEN)
- Expired auth_date (>24 hours old)
- Malformed user JSON

---

### Authorization Errors

#### 403 Forbidden — Not Owner
```json
{
  "detail": "This giveaway does not belong to you"
}
```

#### 403 Forbidden — No Channel Access
```json
{
  "detail": "You do not have access to this channel"
}
```

#### 403 Forbidden — Bot Cannot Post
```json
{
  "detail": "Bot cannot post to channel {channel_id}"
}
```

---

### Resource Errors

#### 404 Not Found
```json
{
  "detail": "Post draft not found"
}
```

#### 400 Bad Request — Validation
```json
{
  "detail": "Validation failed"
}
```
**HTTP Headers:**
```
X-Validation-Errors: ["Title is required", "At least one prize is required"]
```

---

## Endpoints

### Public Endpoints

#### GET /
Serves Mini App frontend (HTML/CSS/JS)

**Auth:** Not required

---

#### GET /api/health
Health check endpoint

**Response:**
```json
{
  "ok": true,
  "status": "running"
}
```

**Auth:** Not required

---

### Authenticated Endpoints

All following endpoints require valid Telegram init data.

#### GET /api/me
Get current user information

**Auth:** Required

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
Get user's post drafts

**Auth:** Required

**Parameters:**
- `scope` (optional): `drafts` (default)

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
Create a new post draft

**Auth:** Required

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

**Trust Boundary:**
- ✅ Server assigns ownership to authenticated user
- ✅ Client cannot specify owner

---

#### GET /api/channels
Get user's connected channels with status

**Auth:** Required

**Response:**
```json
[
  {
    "id": 1,
    "channel_id": -1001234567890,
    "title": "My Channel",
    "username": "mychannel",
    "type": "channel",
    "bot_is_admin": true,
    "bot_can_post": true,
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
    "members_count": 1250,
    "is_active": true,
    "status": "active",
    "can_use_for_giveaway": true,
    "verified_at": "2026-03-11T10:00:00Z",
    "last_permission_check_at": "2026-03-11T10:00:00Z",
    "created_at": "2026-03-11T09:00:00Z"
  }
]
```

**Channel Status Values:**
- `active` — Bot is admin and can post messages (ready for giveaways)
- `limited` — Bot is admin but cannot post messages (needs permission fix)
- `inactive` — Bot is not admin or verification failed

---

#### POST /api/channels/connect/initiate
Initiate channel connection flow

**Auth:** Required

**Request:**
```json
{
  "identifier": "@mychannel"
}
```

**Response:**
```json
{
  "step": 1,
  "action": "add_bot_to_channel",
  "channel": "@mychannel",
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

**Flow Description:**
1. Client calls this endpoint with channel username
2. Backend returns deep link and instructions
3. User adds bot to channel via Telegram
4. Client calls `/api/channels/connect/verify` to complete

---

#### POST /api/channels/connect/verify
Verify channel connection after bot addition

**Auth:** Required

**Request:**
```json
{
  "identifier": "@mychannel"
}
```

**Success Response:**
```json
{
  "success": true,
  "channel_id": 1,
  "channel": {
    "chat_id": -1001234567890,
    "title": "My Channel",
    "username": "mychannel",
    "type": "channel",
    "is_admin": true,
    "can_post": true,
    "permissions_snapshot": {
      "can_post_messages": true,
      "can_edit_messages": true,
      "can_delete_messages": true
    },
    "members_count": 1250,
    "verified_at": "2026-03-11T10:00:00Z"
  }
}
```

**Verification Steps:**
1. Check channel exists via Telegram API
2. Validate channel type (channel/supergroup)
3. Check bot is member of channel
4. Verify bot has administrator status
5. Confirm bot can post messages
6. Save verified channel to database

**Error Responses:**
```json
// 400 Bad Request - Channel not found
{
  "detail": "Channel not found. Make sure the username is correct or the channel is public."
}

// 400 Bad Request - Bot not member
{
  "detail": "Bot is not a member of this channel. Please add the bot first."
}

// 400 Bad Request - Bot not admin
{
  "detail": "Bot must be an administrator in the channel."
}

// 400 Bad Request - Cannot post
{
  "detail": "Bot must have permission to post messages in the channel."
}
```

**Trust Boundary:**
- ✅ Server verifies channel existence via Telegram API
- ✅ Server checks bot membership and permissions
- ✅ Client cannot spoof verification status
- ✅ Database stores verified channel with permissions snapshot

---

#### POST /api/channels/{channel_id}/reverify
Re-verify existing channel permissions

**Auth:** Required

**Path Parameters:**
- `channel_id`: Integer channel ID

**Success Response:**
```json
{
  "success": true,
  "channel": {
    "id": 1,
    "channel_id": -1001234567890,
    "title": "My Channel",
    "username": "mychannel",
    "bot_is_admin": true,
    "bot_can_post": true,
    "status": "active",
    "can_use_for_giveaway": true,
    "last_permission_check_at": "2026-03-11T11:00:00Z"
  }
}
```

**Use Cases:**
- Bot permissions were changed by channel owner
- Periodic permission health check
- Troubleshooting giveaway publishing issues

**Error Cases:**
```json
// 404 Not Found
{
  "detail": "Channel not found in your channels."
}

// 400 Bad Request
{
  "detail": "Bot is no longer an administrator in this channel."
}
```

---

#### POST /api/channels/resolve
[LEGACY] Resolve channel identifier — DEPRECATED

**Auth:** Required

**Note:** This endpoint is deprecated. Use `/api/channels/connect/initiate` and `/api/channels/connect/verify` for production-ready channel connection.

**Dev Mode Only Response:**
```json
{
  "id": -1001234567890,
  "title": "Channel @mychannel",
  "username": "mychannel",
  "bot_is_admin": true,
  "bot_can_post": true
}
```

⚠️ **WARNING:** Dev mode only! Production requires full verification flow.

---

#### GET /api/giveaways?scope=created
Get user's giveaways

**Auth:** Required

**Parameters:**
- `scope` (optional): `created` (default), `active`, `ended`

**Response:**
```json
[
  {
    "id": 1,
    "telegram_id": 123456789,
    "title": "iPhone Giveaway",
    "description": null,
    "language": "en",
    "type": "wheel",
    "post_draft_id": 1,
    "channels": [-1001234567890],
    "prizes": [{"name": "iPhone", "qty": 1}],
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
Get specific giveaway by ID

**Auth:** Required

**Path Parameters:**
- `giveaway_id`: Integer giveaway ID

**Response:** Same structure as list endpoint

**Trust Boundary:**
- ✅ Server verifies ownership before returning data
- ✅ Returns 403 if not owner (even with valid ID)
- ✅ Returns 404 if doesn't exist (before ownership check)

**Error Cases:**
```json
// 404 Not Found
{
  "detail": "Giveaway not found"
}

// 403 Forbidden
{
  "detail": "Access denied: This giveaway does not belong to you"
}
```

---

#### POST /api/wizard/commit
Create finalized giveaway from wizard

**Auth:** Required

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

**Response:**
```json
{
  "giveaway_id": 1
}
```

**Trust Boundaries:**
✅ **Channel Ownership Check**
- Verifies user owns ALL channels in array
- Checks bot has posting permissions
- Returns 403 if any channel not owned

✅ **Post Draft Ownership Check**
- Verifies user owns the post draft
- Returns 403 if post belongs to another user
- Returns 404 if post doesn't exist

✅ **Prize Validation**
- Server validates prize structure
- Client cannot inject malformed prizes

✅ **Giveaway Assignment**
- Server assigns ownership to authenticated user
- Client cannot specify different owner

**Validation Rules:**
- Title: 3-100 characters
- Language: `en`, `ru`, `kz`
- At least 1 channel (must be owned)
- At least 1 prize (valid structure)
- Post draft must exist (owned by user)

---

#### GET /api/wizard/draft
Get user's giveaway wizard draft

**Auth:** Required

**Response:**
```json
{}
```

Currently returns empty object (placeholder)

---

#### POST /api/wizard/draft
Save wizard draft step

**Auth:** Required

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

## Trust Boundaries Summary

### What Backend DOES NOT Trust from Client

❌ **User Identity**
- Raw user JSON from client
- Telegram ID without signature validation
- Username/first_name without verification

✅ **How Handled:**
- HMAC-SHA256 signature validation
- Extract identity only after crypto verification
- Database sync after validation

---

❌ **Entity Ownership Claims**
- `channel_id` claiming ownership
- `giveaway_id` without verification
- `post_draft_id` without owner check

✅ **How Handled:**
- Server queries database for actual ownership
- Returns 403 if entity belongs to different user
- Returns 404 before ownership check (no info leakage)

---

❌ **Channel Permissions**
- Client claims about bot admin status
- Client claims about posting rights

✅ **How Handled:**
- Server checks `is_admin` and `can_post` flags from DB
- Validates permissions before giveaway creation
- Rejects if bot cannot post

---

❌ **Eligibility/Result Data (Future)**
- Client claims about already participated
- Client claims about spin result
- Client claims about prize won

✅ **How Handled (PHASE 9):**
- Server calculates eligibility server-side
- Server determines spin result atomically
- Server decrements prize pool transactionally

---

### What Client CAN Control

✅ **Safe Client Inputs:**
- Post content (text, file_id)
- Giveaway title/description
- Prize names and quantities
- Channel identifiers (@username) for resolution
- Language selection

These are validated but not security-sensitive.

---

## Security Checklist

### For Developers

When adding new endpoints, verify:

- [ ] Auth middleware applied (`Depends(get_authenticated_user)`)
- [ ] Ownership checked for all entity references
- [ ] No raw user data trusted from client
- [ ] Proper error responses (401 vs 403 vs 404)
- [ ] No information leakage in error messages
- [ ] Atomic transactions for state changes

---

### For Auditors

Key files to review:

- `backend/auth.py` — Centralized auth logic
- `backend/main.py` — Endpoint implementations
- `.env` — DEV_AUTH_BYPASS setting (must be 0 in prod)

---

## Migration Notes

### PHASE 2 Changes

**Before PHASE 2:**
- Auth logic scattered in main.py
- Manual ownership checks (inconsistent)
- Some endpoints accepted raw user data

**After PHASE 2:**
- Centralized `AuthService` class
- Consistent ownership verification
- All endpoints use auth middleware
- Clear trust boundaries documented

---

## Future Considerations

### Participant Flow (PHASE 8-9)

New endpoints will require:

**Public Giveaway Access:**
```python
GET /api/public/giveaways/{slug}
# Auth: Optional (for analytics)
# No ownership needed - public by design
```

**Spin Action:**
```python
POST /api/public/giveaways/{id}/spin
# Auth: Required
# Trust boundary: Server calculates result
# Client cannot choose prize
```

**Eligibility Check:**
```python
POST /api/public/giveaways/{id}/eligibility
# Auth: Required
# Trust boundary: Server determines eligibility
# Client cannot fake participation status
```

---

*Document Created: 2026-03-11 (PHASE 2)*  
*Version: 1.0*
