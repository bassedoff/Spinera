import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'spinora.db')

def init_database():
    """Initialize database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Post drafts table - enhanced with content metadata and validation
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS post_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('text', 'photo', 'video', 'document')),
            file_id TEXT,
            text TEXT DEFAULT '',
            caption TEXT DEFAULT '',
            media_type TEXT,
            file_size INTEGER,
            file_unique_id TEXT,
            duration INTEGER,  -- for video/audio
            width INTEGER,     -- for photo/video
            height INTEGER,    -- for photo/video
            mime_type TEXT,
            is_processed BOOLEAN DEFAULT FALSE,
            processed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
        )
    ''')
    
    # Channels table - enhanced with verification and permission tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            title TEXT,
            username TEXT,
            type TEXT DEFAULT 'channel',
            bot_is_admin BOOLEAN DEFAULT FALSE,
            bot_can_post BOOLEAN DEFAULT FALSE,
            permissions_snapshot TEXT,  -- JSON of admin permissions
            members_count INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            verified_at TIMESTAMP,
            last_permission_check_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users (telegram_id),
            UNIQUE(telegram_id, channel_id)
        )
    ''')
    
    # Giveaways table - extended with scheduling and public access fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS giveaways (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            language TEXT DEFAULT 'en',
            post_draft_id INTEGER,
            channels TEXT,  -- JSON array of channel_ids
            prizes TEXT,    -- JSON array of prizes
            type TEXT DEFAULT 'wheel',  -- wheel/case
            start_at TIMESTAMP,
            end_at TIMESTAMP,
            timezone TEXT DEFAULT 'UTC',
            status TEXT DEFAULT 'draft',  -- draft/pending_preview/preview_sent/approved/rejected/active/ended/failed/cancelled
            public_slug TEXT UNIQUE,
            deeplink_token TEXT UNIQUE,
            rules_json TEXT,
            published_message_id TEXT,
            published_at TIMESTAMP,
            preview_message_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users (telegram_id),
            FOREIGN KEY (post_draft_id) REFERENCES post_drafts (id)
        )
    ''')
    
    # Participants table - for tracking giveaway participants
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            giveaway_id INTEGER NOT NULL,
            telegram_id INTEGER NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            eligibility_status TEXT DEFAULT 'pending',  -- pending/eligible/ineligible
            UNIQUE(giveaway_id, telegram_id),
            FOREIGN KEY (giveaway_id) REFERENCES giveaways (id),
            FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
        )
    ''')
    
    # Spins table - for tracking spin attempts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS spins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_id INTEGER NOT NULL,
            giveaway_id INTEGER NOT NULL,
            result_type TEXT NOT NULL,  -- win/lose
            prize_id INTEGER,  -- null if lose
            spun_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            animation_data TEXT,  -- JSON for frontend animation
            FOREIGN KEY (participant_id) REFERENCES participants (id),
            FOREIGN KEY (giveaway_id) REFERENCES giveaways (id)
        )
    ''')
    
    # Winners table - for tracking prize distribution
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS winners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            giveaway_id INTEGER NOT NULL,
            participant_id INTEGER NOT NULL,
            spin_id INTEGER NOT NULL,
            prize_name TEXT NOT NULL,
            prize_description TEXT,
            status TEXT DEFAULT 'pending_issue',  -- pending_issue/issued/cancelled
            manager_comment TEXT,
            issued_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (giveaway_id) REFERENCES giveaways (id),
            FOREIGN KEY (participant_id) REFERENCES participants (id),
            FOREIGN KEY (spin_id) REFERENCES spins (id)
        )
    ''')
    
    # Jobs table - for scheduled tasks
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            giveaway_id INTEGER,
            job_type TEXT NOT NULL,  -- publish/finish/recheck_channel/notify
            scheduled_at TIMESTAMP NOT NULL,
            executed_at TIMESTAMP,
            status TEXT DEFAULT 'pending',  -- pending/running/completed/failed/retry
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            error_message TEXT,
            payload TEXT,  -- JSON payload for job
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (giveaway_id) REFERENCES giveaways (id)
        )
    ''')
    
    # Audit log table - for tracking important actions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            giveaway_id INTEGER,
            action TEXT NOT NULL,  -- create/edit/preview/approve/reject/cancel/publish/spin/win/etc
            details TEXT,  -- JSON with action details
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users (telegram_id),
            FOREIGN KEY (giveaway_id) REFERENCES giveaways (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

if __name__ == "__main__":
    init_database()