# Spinora Database Migrations

## Overview

This document describes the database migration strategy, storage consolidation approach, and schema evolution for SpinoraBot.

---

## Production Storage Choice

**Decision:** SQLite is the **sole production storage** for all business-critical data.

**Rationale:**
- Single source of truth eliminates race conditions
- Transactional integrity for atomic operations (spins, winners)
- Relational model matches domain complexity
- No cross-runtime conflicts (Python can access SQLite directly)
- Sufficient performance for MVP scale
- Easy deployment (single file, no external DB server needed)

**Future Migration Path:**
- Can upgrade to PostgreSQL with minimal code changes
- SQLAlchemy ORM layer would abstract database differences
- Migration scripts can be run when ready

---

## Legacy JSON Storage Status

### Current State (PHASE 1)

**JSON Location:** `data/storage.json`

**What Uses JSON (Temporarily):**
- `bot/storage.py` — Dual writes during transition period
- `web/storage.js` — **DEPRECATED** (Node.js backend eliminated)
- Legacy webhook handler in bot — Still creates giveaways in JSON for backward compatibility

### Transition Strategy

**PHASE 1 (Current): Dual Write Mode**
```python
# Production flow: write to SQLite
db.create_or_update_user(telegram_id, username, ...)

# Legacy compatibility: also write to JSON
storage.save_user(user_data)  # TODO: Remove in PHASE 3
```

**Purpose:** Maintain backward compatibility with existing Mini App frontend during transition.

**PHASE 2 (Next): Read from SQLite, JSON as Fallback**
```python
# Primary: read from SQLite
user = db.get_user(telegram_id)

# Fallback: check JSON if not found in SQLite (temporary)
if not user:
    user = storage.get_user(telegram_id)  # TODO: Remove in PHASE 3
```

**PHASE 3 (Future): Remove JSON Entirely**
- Delete `bot/storage.py`
- Remove all `storage.*` calls from codebase
- Keep `data/storage.json` as read-only archive (optional)
- Update tests to use SQLite only

### What Stays in JSON (If Anything)

**Short Answer:** Nothing for production flow.

**Possible Exceptions:**
- Development/test fixtures
- Temporary session caches (not business data)
- Debug logs (separate from audit trail)

**Recommendation:** Migrate everything to SQLite. If key-value storage needed later, use Redis or similar, not JSON file.

---

## Schema Changes (PHASE 1)

### New Tables Added

#### 1. participants
**Purpose:** Track user participation in giveaways

```sql
CREATE TABLE IF NOT EXISTS participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    giveaway_id INTEGER NOT NULL,
    telegram_id INTEGER NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    eligibility_status TEXT DEFAULT 'pending',
    UNIQUE(giveaway_id, telegram_id),
    FOREIGN KEY (giveaway_id) REFERENCES giveaways (id),
    FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
);
```

**Migration Notes:**
- No existing data to migrate (feature not yet implemented)
- Will be populated starting PHASE 8 (participant flow)

---

#### 2. spins
**Purpose:** Record spin attempts and results

```sql
CREATE TABLE IF NOT EXISTS spins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id INTEGER NOT NULL,
    giveaway_id INTEGER NOT NULL,
    result_type TEXT NOT NULL,
    prize_id INTEGER,
    spun_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    animation_data TEXT,
    FOREIGN KEY (participant_id) REFERENCES participants (id),
    FOREIGN KEY (giveaway_id) REFERENCES giveaways (id)
);
```

**Migration Notes:**
- No existing data (spin engine not yet implemented)
- Will be populated starting PHASE 9 (spin engine)

---

#### 3. winners
**Purpose:** Track prize distribution

```sql
CREATE TABLE IF NOT EXISTS winners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    giveaway_id INTEGER NOT NULL,
    participant_id INTEGER NOT NULL,
    spin_id INTEGER NOT NULL,
    prize_name TEXT NOT NULL,
    prize_description TEXT,
    status TEXT DEFAULT 'pending_issue',
    manager_comment TEXT,
    issued_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (giveaway_id) REFERENCES giveaways (id),
    FOREIGN KEY (participant_id) REFERENCES participants (id),
    FOREIGN KEY (spin_id) REFERENCES spins (id)
);
```

**Migration Notes:**
- No existing data (winner management not yet implemented)
- Will be populated starting PHASE 10 (winners UI)

---

#### 4. jobs
**Purpose:** Scheduled background tasks

```sql
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    giveaway_id INTEGER,
    job_type TEXT NOT NULL,
    scheduled_at TIMESTAMP NOT NULL,
    executed_at TIMESTAMP,
    status TEXT DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (giveaway_id) REFERENCES giveaways (id)
);
```

**Migration Notes:**
- No existing data (scheduler not yet implemented)
- Will be populated starting PHASE 7 (scheduler implementation)

---

#### 5. audit_logs
**Purpose:** Immutable action log

```sql
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    giveaway_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (telegram_id) REFERENCES users (telegram_id),
    FOREIGN KEY (giveaway_id) REFERENCES giveaways (id)
);
```

**Migration Notes:**
- No existing structured audit data
- Logging added progressively through PHASE 10

---

### Extended Tables

#### giveaways (Schema Expansion)

**Old Schema (Before PHASE 1):**
```sql
CREATE TABLE giveaways (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    title TEXT NOT NULL,
    language TEXT DEFAULT 'en',
    post_draft_id INTEGER,
    channels TEXT,
    prizes TEXT,
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ...
);
```

**New Schema (After PHASE 1):**
```sql
CREATE TABLE giveaways (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,                    -- NEW
    language TEXT DEFAULT 'en',
    post_draft_id INTEGER,
    channels TEXT,
    prizes TEXT,
    type TEXT DEFAULT 'wheel',           -- NEW
    start_at TIMESTAMP,                  -- NEW (scheduling)
    end_at TIMESTAMP,                    -- NEW (scheduling)
    timezone TEXT DEFAULT 'UTC',         -- NEW
    status TEXT DEFAULT 'draft',
    public_slug TEXT UNIQUE,             -- NEW (public access)
    deeplink_token TEXT UNIQUE,          -- NEW
    rules_json TEXT,                     -- NEW
    published_message_id TEXT,           -- NEW
    published_at TIMESTAMP,              -- NEW
    preview_message_id TEXT,             -- NEW
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ...
);
```

**Migration Script:**
```python
# Run once to add new columns to existing table
import sqlite3

conn = sqlite3.connect('data/spinora.db')
cursor = conn.cursor()

# Add new columns (IF NOT EXISTS not supported in ALTER TABLE)
columns_to_add = [
    ('description', 'TEXT'),
    ('type', "TEXT DEFAULT 'wheel'"),
    ('start_at', 'TIMESTAMP'),
    ('end_at', 'TIMESTAMP'),
    ('timezone', "TEXT DEFAULT 'UTC'"),
    ('public_slug', 'TEXT UNIQUE'),
    ('deeplink_token', 'TEXT UNIQUE'),
    ('rules_json', 'TEXT'),
    ('published_message_id', 'TEXT'),
    ('published_at', 'TIMESTAMP'),
    ('preview_message_id', 'TEXT')
]

for column_name, column_type in columns_to_add:
    try:
        cursor.execute(f'ALTER TABLE giveaways ADD COLUMN {column_name} {column_type}')
        print(f"Added column: {column_name}")
    except sqlite3.OperationalError as e:
        if 'duplicate column name' in str(e):
            print(f"Column already exists: {column_name}")
        else:
            raise

conn.commit()
conn.close()
```

**Data Migration:**
- Existing giveaways retain old data
- New fields default to NULL or default values
- No data loss occurs

---

## How to Initialize Database

### Fresh Installation

**Option 1: Automatic (Recommended)**
```bash
# Backend auto-initializes on first run
cd backend
python main.py
```

**Option 2: Manual**
```bash
cd data
python db_init.py
```

**Result:**
- Creates `data/spinora.db` if not exists
- Creates all tables with latest schema
- Safe to run multiple times (uses `CREATE TABLE IF NOT EXISTS`)

---

### Migration from Old Schema

If you have an existing `spinora.db` from before PHASE 1:

**Step 1: Backup**
```bash
cp data/spinora.db data/spinora.db.backup
```

**Step 2: Run Migration Script**
Create `data/migrate_phase1.py`:
```python
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'spinora.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Add new columns to giveaways
    columns_to_add = [
        ('description', 'TEXT'),
        ('type', "TEXT DEFAULT 'wheel'"),
        ('start_at', 'TIMESTAMP'),
        ('end_at', 'TIMESTAMP'),
        ('timezone', "TEXT DEFAULT 'UTC'"),
        ('public_slug', 'TEXT UNIQUE'),
        ('deeplink_token', 'TEXT UNIQUE'),
        ('rules_json', 'TEXT'),
        ('published_message_id', 'TEXT'),
        ('published_at', 'TIMESTAMP'),
        ('preview_message_id', 'TEXT')
    ]
    
    for column_name, column_type in columns_to_add:
        try:
            cursor.execute(f'ALTER TABLE giveaways ADD COLUMN {column_name} {column_type}')
            print(f"✓ Added column: {column_name}")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e):
                print(f"⊘ Column already exists: {column_name}")
            else:
                raise
    
    # Create new tables (safe to run if tables exist)
    create_tables_sql = '''
    -- participants table
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        giveaway_id INTEGER NOT NULL,
        telegram_id INTEGER NOT NULL,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        eligibility_status TEXT DEFAULT 'pending',
        UNIQUE(giveaway_id, telegram_id),
        FOREIGN KEY (giveaway_id) REFERENCES giveaways (id),
        FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
    );
    
    -- spins table
    CREATE TABLE IF NOT EXISTS spins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        participant_id INTEGER NOT NULL,
        giveaway_id INTEGER NOT NULL,
        result_type TEXT NOT NULL,
        prize_id INTEGER,
        spun_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        animation_data TEXT,
        FOREIGN KEY (participant_id) REFERENCES participants (id),
        FOREIGN KEY (giveaway_id) REFERENCES giveaways (id)
    );
    
    -- winners table
    CREATE TABLE IF NOT EXISTS winners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        giveaway_id INTEGER NOT NULL,
        participant_id INTEGER NOT NULL,
        spin_id INTEGER NOT NULL,
        prize_name TEXT NOT NULL,
        prize_description TEXT,
        status TEXT DEFAULT 'pending_issue',
        manager_comment TEXT,
        issued_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (giveaway_id) REFERENCES giveaways (id),
        FOREIGN KEY (participant_id) REFERENCES participants (id),
        FOREIGN KEY (spin_id) REFERENCES spins (id)
    );
    
    -- jobs table
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        giveaway_id INTEGER,
        job_type TEXT NOT NULL,
        scheduled_at TIMESTAMP NOT NULL,
        executed_at TIMESTAMP,
        status TEXT DEFAULT 'pending',
        retry_count INTEGER DEFAULT 0,
        max_retries INTEGER DEFAULT 3,
        error_message TEXT,
        payload TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (giveaway_id) REFERENCES giveaways (id)
    );
    
    -- audit_logs table
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER,
        giveaway_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        ip_address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (telegram_id) REFERENCES users (telegram_id),
        FOREIGN KEY (giveaway_id) REFERENCES giveaways (id)
    );
    '''
    
    cursor.executescript(create_tables_sql)
    print("✓ Created new tables")
    
    conn.commit()
    conn.close()
    print("✓ Migration complete")

if __name__ == "__main__":
    migrate()
```

Run it:
```bash
cd data
python migrate_phase1.py
```

**Step 3: Verify**
```bash
cd data
sqlite3 spinora.db ".schema"
```

Check that all new tables and columns exist.

---

## Transitional Adapters

### During PHASE 1: Dual Write

**Pattern:**
```python
# Production: SQLite
post_id = db.create_post_draft(
    telegram_id=user_id,
    post_type='photo',
    file_id=file_id,
    text=text
)

# Legacy compatibility: JSON
storage.save_post_draft(str(user_id), {
    'type': 'photo',
    'file_id': file_id,
    'text': text
})
```

**Where Used:**
- `bot/main.py:cmd_start()` — User creation
- `bot/main.py:handle_post()` — Post drafts
- `bot/main.py:handle_web_app_data()` — Giveaway creation (legacy path)

**Removal Timeline:**
- Mark with `# LEGACY` comments
- Remove in PHASE 3 after frontend fully migrated to direct API calls

---

## Rollback Procedures

### If Migration Fails

**Scenario:** Migration script fails partway through.

**Recovery:**
1. Stop application
2. Restore backup:
   ```bash
   cp data/spinora.db.backup data/spinora.db
   ```
3. Fix migration script
4. Re-run migration

### If New Code Has Bugs

**Scenario:** PHASE 1 code causes issues.

**Rollback Steps:**
1. Revert to previous git commit:
   ```bash
   git checkout <previous-commit>
   ```
2. Restore old database:
   ```bash
   cp data/spinora.db.backup data/spinora.db
   ```
3. Restart services

**Why This Works:**
- Old schema is subset of new schema
- Backward compatible (new columns are nullable)
- Can downgrade code without data loss

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-11 | PHASE 1: Consolidated to SQLite, added new tables, extended giveaways schema |
| 0.x | Previous | Dual JSON + SQLite storage (deprecated) |

---

## Next Migration Steps (Future Phases)

### PHASE 2: Indexes
Add performance indexes (see domain-model.md for recommended list)

### PHASE 7: Jobs Scheduler
Populate jobs table with initial scheduler implementation

### PHASE 8-10: Participant Flow
Activate participants, spins, winners tables

### Future: PostgreSQL Migration
When scaling requires it:
1. Add SQLAlchemy ORM layer
2. Create PostgreSQL migration script
3. Test with production data volume
4. Cutover with minimal downtime

---

*Document Created: 2026-03-11*  
*Last Updated: 2026-03-11*  
*Version: 1.0*
