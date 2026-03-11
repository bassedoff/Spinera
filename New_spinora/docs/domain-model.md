# Spinora Domain Model

## Overview

This document describes the domain entities, their relationships, and business rules for the SpinoraBot platform. The domain model is implemented using SQLite as the production storage backend.

**Last Updated:** 2026-03-11 (PHASE 3 Complete)

---

## Core Entities

### 1. User

**Purpose:** Represents a Telegram user who can create or participate in giveaways.

**Table:** `users`

**Fields:**
- `telegram_id` (INTEGER, PK) — Unique Telegram user ID
- `username` (TEXT) — Telegram username
- `first_name` (TEXT) — User's first name
- `last_name` (TEXT) — User's last name
- `created_at` (TIMESTAMP) — Record creation timestamp

**Relationships:**
- One-to-Many: User → Channels (owner)
- One-to-Many: User → PostDrafts (author)
- One-to-Many: User → Giveaways (creator)
- One-to-Many: User → Participants (participation)
- One-to-Many: User → AuditLogs (actions)

**Constraints:**
- `telegram_id` must be unique
- All users are automatically created/updated on first interaction

**Implementation Status:** ✅ Complete

---

### 2. Channel

**Purpose:** Represents a Telegram channel connected to a user for giveaway publishing.

**Table:** `channels`

**Fields (PHASE 3 Enhanced):**
- `id` (INTEGER, PK) — Auto-increment primary key
- `telegram_id` (INTEGER, FK) — Owner's Telegram ID
- `channel_id` (INTEGER) — Telegram channel chat ID (negative for channels/groups)
- `title` (TEXT) — Channel title
- `username` (TEXT) — Channel username (without @)
- `type` (TEXT) — Channel type: `channel`, `supergroup`
- `bot_is_admin` (BOOLEAN) — Whether bot is admin in channel
- `bot_can_post` (BOOLEAN) — Whether bot can post messages
- `permissions_snapshot` (TEXT/JSON) — JSON snapshot of bot's admin permissions
- `members_count` (INTEGER) — Number of channel members
- `is_active` (BOOLEAN) — Whether channel is active/verified
- `verified_at` (TIMESTAMP) — Last successful verification timestamp
- `last_permission_check_at` (TIMESTAMP) — Last permission re-check timestamp
- `created_at` (TIMESTAMP) — Connection timestamp
- `updated_at` (TIMESTAMP) — Last update timestamp

**Relationships:**
- Many-to-One: Channel → User (owner)
- Many-to-Many: Channel ↔ Giveaway (via channels JSON array)

**Constraints:**
- Unique constraint on `(telegram_id, channel_id)` — user can't connect same channel twice
- `channel_id` must be negative (Telegram channels/groups have negative IDs)
- Bot must have admin rights (`bot_is_admin = true`) and posting permission (`bot_can_post = true`)
- Channel type must be `channel` or `supergroup`

**Permissions Snapshot Fields:**
```json
{
  "can_post_messages": true,
  "can_edit_messages": true,
  "can_delete_messages": true,
  "can_restrict_members": false,
  "can_promote_members": false,
  "can_change_info": false,
  "can_invite_users": true,
  "can_pin_messages": true
}
```

**Computed Status (Business Logic):**
- `active` — Bot is admin AND can post (ready for giveaways)
- `limited` — Bot is admin but cannot post (needs permission fix)
- `inactive` — Bot is not admin or verification failed

**Constraints:**
- Channel must pass full verification before use in giveaway
- Bot permissions rechecked on every verify operation
- Only channels with status `active` can be used for publishing
- Verification is idempotent (updates existing record, doesn't duplicate)

**Business Rules:**
- Channel identity verified via Telegram API (getChat)
- Bot membership verified via Telegram API (getChatMember)
- Admin status required for posting capability
- Posting permission explicitly checked and stored
- Permissions snapshot captured at verification time
- Channel metadata (title, username, members) refreshed on reverify
- Lost permissions detected and channel marked as `inactive`

**Implementation Status:** ✅ Complete (PHASE 3)

---

### 3. PostDraft

**Purpose:** Represents a draft post (text/media) that will be used in a giveaway.

**Table:** `post_drafts`

**Fields:**
- `id` (INTEGER, PK) — Auto-increment primary key
- `telegram_id` (INTEGER, FK) — Author's Telegram ID
- `type` (TEXT) — Post type: `text`, `photo`, `video`, `document`
- `file_id` (TEXT, nullable) — Telegram file ID for media posts
- `text` (TEXT) — Post caption/text content
- `created_at` (TIMESTAMP) — Creation timestamp

**Relationships:**
- Many-to-One: PostDraft → User (author)
- One-to-Many: PostDraft → Giveaway (used in)

**Constraints:**
- `type` must be one of: `text`, `photo`, `video`, `document`
- If `type` is `photo/video/document`, `file_id` is required
- Maximum text length: 4096 characters (Telegram limit)

**Business Rules:**
- Post drafts are reusable across multiple giveaways
- Drafts can be created via bot or Mini App
- Only the author can use their drafts

**Implementation Status:** ✅ Complete

---

### 4. Giveaway

**Purpose:** Central entity representing a giveaway campaign with all configuration and state.

**Table:** `giveaways`

**Fields:**
- `id` (INTEGER, PK) — Auto-increment primary key
- `telegram_id` (INTEGER, FK) — Creator's Telegram ID
- `title` (TEXT) — Giveaway title (3-100 chars)
- `description` (TEXT, nullable) — Optional description
- `language` (TEXT) — Language code: `en`, `ru`, `kz`
- `type` (TEXT) — Giveaway type: `wheel` (default), `case`
- `post_draft_id` (INTEGER, FK, nullable) — Associated post draft
- `channels` (TEXT) — JSON array of channel IDs for publishing
- `prizes` (TEXT) — JSON array of prize configurations
- `start_at` (TIMESTAMP, nullable) — Scheduled start time
- `end_at` (TIMESTAMP, nullable) — Participation deadline
- `timezone` (TEXT) — Timezone for display (default: `UTC`)
- `status` (TEXT) — Current status (see Status Transitions below)
- `public_slug` (TEXT, UNIQUE, nullable) — Public access slug
- `deeplink_token` (TEXT, UNIQUE, nullable) — Telegram deeplink token
- `rules_json` (TEXT, nullable) — Custom rules configuration
- `published_message_id` (TEXT, nullable) — Message ID in channel
- `published_at` (TIMESTAMP, nullable) — Actual publication time
- `preview_message_id` (TEXT, nullable) — Preview message ID in bot
- `created_at` (TIMESTAMP) — Creation timestamp
- `updated_at` (TIMESTAMP) — Last update timestamp

**Status Values:**
- `draft` — Initial state during creation
- `pending_preview` — Ready for preview
- `preview_sent` — Preview sent to creator
- `approved` — Creator approved for publishing
- `rejected` — Creator rejected, needs edits
- `active` — Published and accepting participants
- `ended` — Participation window closed
- `failed` — Publication or other error occurred
- `cancelled` — Cancelled by creator

**Status Transitions:**
```
draft → pending_preview → preview_sent → approved → active → ended
  ↓          ↓                  ↓             ↓
rejected ← edit            cancelled      failed
```

**Relationships:**
- Many-to-One: Giveaway → User (creator)
- Many-to-One: Giveaway → PostDraft (content)
- One-to-Many: Giveaway → Participants
- One-to-Many: Giveaway → Spins
- One-to-Many: Giveaway → Winners
- One-to-Many: Giveaway → Jobs
- One-to-Many: Giveaway → AuditLogs

**Constraints:**
- `title` length: 3-100 characters
- `language` must be one of: `en`, `ru`, `kz`
- `end_at` must be > `start_at` (if both set)
- At least one channel required
- At least one prize required
- `public_slug` and `deeplink_token` must be unique when set

**Business Rules:**
- Giveaways are private to creator until published
- Once active, configuration changes are restricted
- Participants can only join active giveaways
- Ended giveaways cannot accept new participants

**Implementation Status:** ✅ Core fields complete, some fields reserved for future phases

---

### 5. Participant

**Purpose:** Tracks a user's participation in a specific giveaway.

**Table:** `participants`

**Fields:**
- `id` (INTEGER, PK) — Auto-increment primary key
- `giveaway_id` (INTEGER, FK) — Associated giveaway
- `telegram_id` (INTEGER, FK) — Participant's Telegram ID
- `joined_at` (TIMESTAMP) — Join timestamp
- `eligibility_status` (TEXT) — Current eligibility: `pending`, `eligible`, `ineligible`

**Relationships:**
- Many-to-One: Participant → Giveaway
- Many-to-One: Participant → User
- One-to-One: Participant → Spin (one spin per participant per giveaway)
- One-to-Many: Participant → Winners (can win multiple times in theory)

**Constraints:**
- Unique constraint on `(giveaway_id, telegram_id)` — user can participate once per giveaway
- Each participant can only have one spin

**Business Rules:**
- Eligibility checked before allowing spin
- Once participated, cannot participate again in same giveaway
- Participant record created on first interaction with giveaway

**Implementation Status:** ✅ Schema ready, logic to be implemented in PHASE 8-9

---

### 6. Spin

**Purpose:** Records a spin attempt and its result.

**Table:** `spins`

**Fields:**
- `id` (INTEGER, PK) — Auto-increment primary key
- `participant_id` (INTEGER, FK) — Who spun
- `giveaway_id` (INTEGER, FK) — Which giveaway
- `result_type` (TEXT) — Result: `win` or `lose`
- `prize_id` (INTEGER, nullable) — Won prize index (null if lose)
- `spun_at` (TIMESTAMP) — Spin timestamp
- `animation_data` (TEXT, nullable) — JSON for frontend animation

**Relationships:**
- Many-to-One: Spin → Participant
- Many-to-One: Spin → Giveaway
- One-to-One: Spin → Winner (if win)

**Constraints:**
- One spin per participant per giveaway (enforced at application level)
- `result_type` must be `win` or `lose`
- If `result_type` = `win`, `prize_id` is required

**Business Rules:**
- Spin result calculated server-side to prevent fraud
- Atomic transaction: check eligibility → calculate result → decrement prize → save spin
- Animation data stored for replayability
- Cannot change result after spin is saved

**Implementation Status:** ✅ Schema ready, engine to be implemented in PHASE 9

---

### 7. Winner

**Purpose:** Tracks prize distribution and issue status.

**Table:** `winners`

**Fields:**
- `id` (INTEGER, PK) — Auto-increment primary key
- `giveaway_id` (INTEGER, FK) — Associated giveaway
- `participant_id` (INTEGER, FK) — Winner's participation record
- `spin_id` (INTEGER, FK) — Winning spin record
- `prize_name` (TEXT) — Name of won prize
- `prize_description` (TEXT, nullable) — Prize details
- `status` (TEXT) — Issue status: `pending_issue`, `issued`, `cancelled`
- `manager_comment` (TEXT, nullable) — Manual note from creator
- `issued_at` (TIMESTAMP, nullable) — When prize was marked as issued
- `created_at` (TIMESTAMP) — Record creation timestamp

**Relationships:**
- Many-to-One: Winner → Giveaway
- Many-to-One: Winner → Participant
- Many-to-One: Winner → Spin

**Constraints:**
- `status` must be one of: `pending_issue`, `issued`, `cancelled`
- Linked to exactly one spin

**Business Rules:**
- Winner created automatically on winning spin
- Creator can manually mark as issued
- Pending winners visible in creator dashboard
- Can export winners list

**Implementation Status:** ✅ Schema ready, management UI to be implemented in PHASE 10

---

### 8. Job

**Purpose:** Scheduled background tasks for automation.

**Table:** `jobs`

**Fields:**
- `id` (INTEGER, PK) — Auto-increment primary key
- `giveaway_id` (INTEGER, FK, nullable) — Associated giveaway (null for system jobs)
- `job_type` (TEXT) — Task type: `publish`, `finish`, `recheck_channel`, `notify`
- `scheduled_at` (TIMESTAMP) — When to execute
- `executed_at` (TIMESTAMP, nullable) — Actual execution time
- `status` (TEXT) — Job status: `pending`, `running`, `completed`, `failed`, `retry`
- `retry_count` (INTEGER) — Number of retry attempts
- `max_retries` (INTEGER) — Maximum retry limit (default: 3)
- `error_message` (TEXT, nullable) — Last error details
- `payload` (TEXT, nullable) — JSON job parameters
- `created_at` (TIMESTAMP) — Creation timestamp

**Job Types:**
- `publish` — Publish giveaway to channel at scheduled time
- `finish` — End giveaway and close participation
- `recheck_channel` — Verify bot still has admin rights
- `notify` — Send notifications to creator/participants

**Relationships:**
- Many-to-One: Job → Giveaway

**Constraints:**
- `job_type` determines required payload structure
- Jobs auto-retry up to `max_retries` on failure

**Business Rules:**
- Scheduler worker processes pending jobs
- Failed jobs retry with exponential backoff
- Completed jobs logged for audit trail

**Implementation Status:** ✅ Schema ready, scheduler to be implemented in PHASE 7

---

### 9. AuditLog

**Purpose:** Immutable log of important system actions.

**Table:** `audit_logs`

**Fields:**
- `id` (INTEGER, PK) — Auto-increment primary key
- `telegram_id` (INTEGER, FK, nullable) — User who performed action (null for system actions)
- `giveaway_id` (INTEGER, FK, nullable) — Related giveaway
- `action` (TEXT) — Action type
- `details` (TEXT, nullable) — JSON with action-specific details
- `ip_address` (TEXT, nullable) — Request IP (for API actions)
- `created_at` (TIMESTAMP) — Action timestamp

**Action Types:**
- `create` — Giveaway/post/channel created
- `edit` — Entity modified
- `preview` — Preview requested/sent
- `approve` / `reject` / `cancel` — Giveaway decision
- `publish` — Published to channel
- `spin` — Participant spun wheel
- `win` — Winner determined
- `issue_prize` — Prize marked as issued
- `delete` — Entity deleted

**Relationships:**
- Many-to-One: AuditLog → User (actor)
- Many-to-One: AuditLog → Giveaway (subject)

**Constraints:**
- Audit logs are append-only (no updates/deletes)
- Critical actions must be logged

**Business Rules:**
- Retention policy: keep logs for 1 year
- Viewable in creator dashboard for their giveaways
- System actions logged with `telegram_id` = null

**Implementation Status:** ✅ Schema ready, logging to be added throughout PHASE 10

---

## Entity Relationship Diagram

```
┌─────────────┐
│    User     │
│ (telegram_id│──┐
└─────────────┘  │
                 │
        ┌────────┼────────────────────────────────┐
        │        │                                │
        │        │                                │
        ▼        ▼                                ▼
┌─────────────┐ ┌─────────────┐         ┌─────────────┐
│   Channel   │ │ PostDraft   │         │  Giveaway   │
│(channel_id) │ │   (id)      │         │    (id)     │
└─────────────┘ └─────────────┘         └─────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    ▼                         ▼                         ▼
            ┌─────────────┐           ┌─────────────┐           ┌─────────────┐
            │ Participant │           │    Spin     │           │   Winner    │
            │    (id)     │◄──────────│    (id)     │◄──────────│    (id)     │
            └─────────────┘           └─────────────┘           └─────────────┘
                    │
                    ▼
            ┌─────────────┐
            │    Audit    │
            │     Log     │
            └─────────────┘
```

---

## Data Integrity Rules

### Foreign Key Enforcement

All foreign keys are defined but SQLite doesn't enforce them by default. Application layer must:

1. Check parent entity exists before creating child
2. Handle orphaned records on parent deletion
3. Use transactions for multi-table operations

### JSON Field Validation

Fields storing JSON arrays (`channels`, `prizes`, `payload`, `details`):

1. Always validate JSON structure before saving
2. Use consistent schema across application
3. Document expected structure in code comments

Example prize structure:
```json
[
  {
    "name": "iPhone 15",
    "description": "Latest model, 256GB",
    "qty": 3,
    "remaining": 3,
    "weight": 10
  }
]
```

Example channels structure:
```json
[-1001234567890, -1009876543210]
```

---

## Indexes (Recommended)

Add these indexes for performance (not yet in schema):

```sql
-- Faster user lookups
CREATE INDEX idx_users_telegram ON users(telegram_id);

-- Faster post drafts by user
CREATE INDEX idx_post_drafts_user ON post_drafts(telegram_id);

-- Faster channel queries
CREATE INDEX idx_channels_user ON channels(telegram_id);
CREATE UNIQUE INDEX idx_channels_unique ON channels(telegram_id, channel_id);

-- Faster giveaway queries
CREATE INDEX idx_giveaways_user ON giveaways(telegram_id);
CREATE INDEX idx_giveaways_status ON giveaways(status);
CREATE INDEX idx_giveaways_public ON giveaways(public_slug);

-- Faster participant queries
CREATE INDEX idx_participants_giveaway ON participants(giveaway_id);
CREATE UNIQUE INDEX idx_participants_unique ON participants(giveaway_id, telegram_id);

-- Faster spin queries
CREATE INDEX idx_spins_participant ON spins(participant_id);
CREATE INDEX idx_spins_giveaway ON spins(giveaway_id);

-- Faster winner queries
CREATE INDEX idx_winners_giveaway ON winners(giveaway_id);

-- Faster job scheduling
CREATE INDEX idx_jobs_status_scheduled ON jobs(status, scheduled_at);

-- Faster audit queries
CREATE INDEX idx_audit_user ON audit_logs(telegram_id);
CREATE INDEX idx_audit_giveaway ON audit_logs(giveaway_id);
```

---

## Migration Notes

### From JSON Storage

During PHASE 1 transition:

1. **Users:** Read from JSON, write to both JSON + SQLite temporarily
2. **PostDrafts:** Create in SQLite first, mirror to JSON for backward compatibility
3. **Giveaways:** New giveaways created in SQLite only; legacy endpoint writes to both
4. **Channels:** Already in SQLite; no migration needed

**Deprecation Path:**
- PHASE 1: Dual write (SQLite + JSON)
- PHASE 2: Read from SQLite, JSON as fallback
- PHASE 3: Remove JSON entirely

---

## Implementation Status Summary

| Entity | Schema | CRUD Methods | Business Logic | UI Integration |
|--------|--------|--------------|----------------|----------------|
| User | ✅ | ✅ | ✅ | ✅ |
| Channel | ✅ | ✅ | ⚠️ Partial | ⚠️ Basic |
| PostDraft | ✅ | ✅ | ✅ | ✅ |
| Giveaway | ✅ | ✅ Basic | ⚠️ Partial | ⚠️ Basic |
| Participant | ✅ | ⚠️ Basic | ❌ TODO | ❌ TODO |
| Spin | ✅ | ⚠️ Basic | ❌ TODO | ❌ TODO |
| Winner | ✅ | ⚠️ Basic | ❌ TODO | ❌ TODO |
| Job | ✅ | ⚠️ Basic | ❌ TODO | ❌ TODO |
| AuditLog | ✅ | ⚠️ Basic | ❌ TODO | ❌ TODO |

**Legend:**
- ✅ Complete
- ⚠️ Partial (schema exists, methods need enhancement)
- ❌ Not started

---

*Document Created: 2026-03-11*  
*Last Updated: 2026-03-11*  
*Version: 1.0*
