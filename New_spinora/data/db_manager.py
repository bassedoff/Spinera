import sqlite3
import json
import os
from typing import List, Dict, Optional, Any
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'spinora.db')

class DatabaseManager:
    def __init__(self):
        self.db_path = DB_PATH
        
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    # User operations
    def create_or_update_user(self, telegram_id: int, username: str = "", 
                            first_name: str = "", last_name: str = ""):
        """Create or update user record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users (telegram_id, username, first_name, last_name, created_at)
            VALUES (?, ?, ?, ?, COALESCE(
                (SELECT created_at FROM users WHERE telegram_id = ?),
                CURRENT_TIMESTAMP
            ))
        ''', (telegram_id, username, first_name, last_name, telegram_id))
        
        conn.commit()
        conn.close()
    
    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user by telegram_id"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return {
                'telegram_id': row[0],
                'username': row[1],
                'first_name': row[2],
                'last_name': row[3],
                'created_at': row[4]
            }
        return None
    
    # Post operations
    def create_post_draft(self, telegram_id: int, post_type: str, 
                         file_id: str = None, text: str = "") -> int:
        """Create post draft and return ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO post_drafts (telegram_id, type, file_id, text)
            VALUES (?, ?, ?, ?)
        ''', (telegram_id, post_type, file_id, text))
        
        post_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return post_id
    
    def get_post_draft(self, post_id: int) -> Optional[Dict]:
        """Get post draft by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM post_drafts WHERE id = ?', (post_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'telegram_id': row[1],
                'type': row[2],
                'file_id': row[3],
                'text': row[4],
                'created_at': row[5]
            }
        return None
    
    def get_user_posts(self, telegram_id: int) -> List[Dict]:
        """Get all post drafts for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM post_drafts 
            WHERE telegram_id = ? 
            ORDER BY created_at DESC
        ''', (telegram_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'id': row[0],
            'telegram_id': row[1],
            'type': row[2],
            'file_id': row[3],
            'text': row[4],
            'created_at': row[5]
        } for row in rows]
    
    # Channel operations
    def resolve_and_save_channel(self, telegram_id: int, identifier: str, 
                               channel_data: Dict) -> int:
        """
        Resolve channel by username or ID and save to database
        Returns channel ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if channel already exists for this user
        cursor.execute('''
            SELECT id FROM channels 
            WHERE telegram_id = ? AND (username = ? OR channel_id = ?)
        ''', (telegram_id, 
              channel_data.get('username'),
              channel_data.get('chat_id')))
        
        existing = cursor.fetchone()
        
        if existing:
            channel_id = existing[0]
            # Update existing channel
            cursor.execute('''
                UPDATE channels SET
                    title = ?,
                    username = ?,
                    type = ?,
                    bot_is_admin = ?,
                    bot_can_post = ?,
                    permissions_snapshot = ?,
                    members_count = ?,
                    is_active = ?,
                    verified_at = CURRENT_TIMESTAMP,
                    last_permission_check_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND telegram_id = ?
            ''', (
                channel_data.get('title', ''),
                channel_data.get('username', ''),
                channel_data.get('type', 'channel'),
                channel_data.get('bot_is_admin', False),
                channel_data.get('bot_can_post', False),
                json.dumps(channel_data.get('permissions_snapshot', {})),
                channel_data.get('members_count', 0),
                True,
                channel_id,
                telegram_id
            ))
        else:
            # Create new channel
            cursor.execute('''
                INSERT INTO channels (
                    telegram_id, channel_id, title, username, type,
                    bot_is_admin, bot_can_post, permissions_snapshot,
                    members_count, is_active, verified_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                telegram_id,
                channel_data.get('chat_id'),
                channel_data.get('title', ''),
                channel_data.get('username', ''),
                channel_data.get('type', 'channel'),
                channel_data.get('bot_is_admin', False),
                channel_data.get('bot_can_post', False),
                json.dumps(channel_data.get('permissions_snapshot', {})),
                channel_data.get('members_count', 0),
                True
            ))
            channel_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return channel_id
    
    def get_user_channels(self, telegram_id: int) -> List[Dict]:
        """Get all saved channels for user with enhanced details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, channel_id, title, username, type, bot_is_admin, bot_can_post,
                   permissions_snapshot, members_count, is_active,
                   verified_at, last_permission_check_at, created_at
            FROM channels 
            WHERE telegram_id = ?
            ORDER BY created_at DESC
        ''', (telegram_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        channels = []
        for row in rows:
            channel = {
                'id': row[0],
                'channel_id': row[1],
                'title': row[2],
                'username': row[3],
                'type': row[4],
                'bot_is_admin': bool(row[5]),
                'bot_can_post': bool(row[6]),
                'permissions_snapshot': json.loads(row[7]) if row[7] else {},
                'members_count': row[8],
                'is_active': bool(row[9]),
                'verified_at': row[10],
                'last_permission_check_at': row[11],
                'created_at': row[12]
            }
            
            # Compute status field
            if channel['bot_is_admin'] and channel['bot_can_post']:
                channel['status'] = 'active'
                channel['can_use_for_giveaway'] = True
            elif channel['bot_is_admin']:
                channel['status'] = 'limited'
                channel['can_use_for_giveaway'] = False
            else:
                channel['status'] = 'inactive'
                channel['can_use_for_giveaway'] = False
            
            channels.append(channel)
        
        return channels
    
    # Giveaway operations
    def create_giveaway(self, telegram_id: int, title: str, language: str = 'en',
                       post_draft_id: int = None, channels: List[int] = None,
                       prizes: List[Dict] = None) -> int:
        """Create giveaway and return ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        channels_json = json.dumps(channels or [])
        prizes_json = json.dumps(prizes or [])
        
        cursor.execute('''
            INSERT INTO giveaways 
            (telegram_id, title, language, post_draft_id, channels, prizes, status)
            VALUES (?, ?, ?, ?, ?, ?, 'draft')
        ''', (telegram_id, title, language, post_draft_id, channels_json, prizes_json))
        
        giveaway_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return giveaway_id
    
    def get_giveaway(self, giveaway_id: int) -> Optional[Dict]:
        """Get giveaway by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM giveaways WHERE id = ?', (giveaway_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'telegram_id': row[1],
                'title': row[2],
                'language': row[3],
                'post_draft_id': row[4],
                'channels': json.loads(row[5]) if row[5] else [],
                'prizes': json.loads(row[6]) if row[6] else [],
                'status': row[7],
                'created_at': row[8],
                'updated_at': row[9]
            }
        return None
    
    def update_giveaway_status(self, giveaway_id: int, status: str):
        """Update giveaway status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE giveaways 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, giveaway_id))
        
        conn.commit()
        conn.close()
    
    def get_user_giveaways(self, telegram_id: int, status: str = None) -> List[Dict]:
        """Get user giveaways with optional status filter"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT * FROM giveaways 
                WHERE telegram_id = ? AND status = ?
                ORDER BY created_at DESC
            ''', (telegram_id, status))
        else:
            cursor.execute('''
                SELECT * FROM giveaways 
                WHERE telegram_id = ?
                ORDER BY created_at DESC
            ''', (telegram_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'id': row[0],
            'telegram_id': row[1],
            'title': row[2],
            'description': row[3],
            'language': row[4],
            'post_draft_id': row[5],
            'channels': json.loads(row[6]) if row[6] else [],
            'prizes': json.loads(row[7]) if row[7] else [],
            'type': row[8],
            'start_at': row[9],
            'end_at': row[10],
            'timezone': row[11],
            'status': row[12],
            'public_slug': row[13],
            'deeplink_token': row[14],
            'rules_json': row[15],
            'published_message_id': row[16],
            'published_at': row[17],
            'preview_message_id': row[18],
            'created_at': row[19],
            'updated_at': row[20]
        } for row in rows]
    
    # Participant operations
    def create_or_get_participant(self, giveaway_id: int, telegram_id: int) -> Dict:
        """Create or get participant for a giveaway"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO participants (giveaway_id, telegram_id)
                VALUES (?, ?)
            ''', (giveaway_id, telegram_id))
            
            cursor.execute('''
                SELECT * FROM participants 
                WHERE giveaway_id = ? AND telegram_id = ?
            ''', (giveaway_id, telegram_id))
            
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row[0],
                    'giveaway_id': row[1],
                    'telegram_id': row[2],
                    'joined_at': row[3],
                    'eligibility_status': row[4]
                }
            return None
        finally:
            conn.close()
    
    def update_participant_eligibility(self, participant_id: int, status: str):
        """Update participant eligibility status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE participants 
            SET eligibility_status = ?
            WHERE id = ?
        ''', (status, participant_id))
        
        conn.commit()
        conn.close()
    
    # Spin operations
    def create_spin(self, participant_id: int, giveaway_id: int, 
                   result_type: str, prize_id: int = None, 
                   animation_data: dict = None) -> int:
        """Create a spin record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        animation_json = json.dumps(animation_data) if animation_data else None
        
        cursor.execute('''
            INSERT INTO spins (participant_id, giveaway_id, result_type, prize_id, animation_data)
            VALUES (?, ?, ?, ?, ?)
        ''', (participant_id, giveaway_id, result_type, prize_id, animation_json))
        
        spin_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return spin_id
    
    def has_participated(self, giveaway_id: int, telegram_id: int) -> bool:
        """Check if user has already participated in giveaway"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) 
            FROM spins s
            JOIN participants p ON s.participant_id = p.id
            WHERE p.giveaway_id = ? AND p.telegram_id = ?
        ''', (giveaway_id, telegram_id))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    # Winner operations
    def create_winner(self, giveaway_id: int, participant_id: int, 
                     spin_id: int, prize_name: str, 
                     prize_description: str = None) -> int:
        """Create winner record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO winners (giveaway_id, participant_id, spin_id, prize_name, prize_description)
            VALUES (?, ?, ?, ?, ?)
        ''', (giveaway_id, participant_id, spin_id, prize_name, prize_description))
        
        winner_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return winner_id
    
    def get_winners(self, giveaway_id: int) -> List[Dict]:
        """Get all winners for a giveaway"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM winners 
            WHERE giveaway_id = ?
            ORDER BY created_at DESC
        ''', (giveaway_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'id': row[0],
            'giveaway_id': row[1],
            'participant_id': row[2],
            'spin_id': row[3],
            'prize_name': row[4],
            'prize_description': row[5],
            'status': row[6],
            'manager_comment': row[7],
            'issued_at': row[8],
            'created_at': row[9]
        } for row in rows]
    
    def update_winner_status(self, winner_id: int, status: str, manager_comment: str = None):
        """Update winner status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE winners 
            SET status = ?, manager_comment = ?, issued_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, manager_comment, winner_id))
        
        conn.commit()
        conn.close()
    
    # Job operations
    def create_job(self, giveaway_id: int, job_type: str, 
                  scheduled_at: datetime, payload: dict = None,
                  max_retries: int = 3) -> int:
        """Create a scheduled job"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        payload_json = json.dumps(payload) if payload else None
        
        cursor.execute('''
            INSERT INTO jobs (giveaway_id, job_type, scheduled_at, payload, max_retries)
            VALUES (?, ?, ?, ?, ?)
        ''', (giveaway_id, job_type, scheduled_at, payload_json, max_retries))
        
        job_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return job_id
    
    def get_pending_jobs(self, job_type: str = None) -> List[Dict]:
        """Get pending jobs that are ready to execute"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if job_type:
            cursor.execute('''
                SELECT * FROM jobs 
                WHERE status = 'pending' AND job_type = ? AND scheduled_at <= CURRENT_TIMESTAMP
                ORDER BY scheduled_at ASC
            ''', (job_type,))
        else:
            cursor.execute('''
                SELECT * FROM jobs 
                WHERE status = 'pending' AND scheduled_at <= CURRENT_TIMESTAMP
                ORDER BY scheduled_at ASC
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'id': row[0],
            'giveaway_id': row[1],
            'job_type': row[2],
            'scheduled_at': row[3],
            'executed_at': row[4],
            'status': row[5],
            'retry_count': row[6],
            'max_retries': row[7],
            'error_message': row[8],
            'payload': json.loads(row[9]) if row[9] else {},
            'created_at': row[10]
        } for row in rows]
    
    def update_job_status(self, job_id: int, status: str, error_message: str = None):
        """Update job status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if status == 'completed':
            cursor.execute('''
                UPDATE jobs 
                SET status = ?, executed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, job_id))
        elif status == 'failed' and error_message:
            cursor.execute('''
                UPDATE jobs 
                SET status = ?, error_message = ?, retry_count = retry_count + 1
                WHERE id = ?
            ''', (status, error_message, job_id))
        else:
            cursor.execute('''
                UPDATE jobs 
                SET status = ?
                WHERE id = ?
            ''', (status, job_id))
        
        conn.commit()
        conn.close()
    
    # Audit log operations
    def log_action(self, telegram_id: int, action: str, 
                  giveaway_id: int = None, details: dict = None,
                  ip_address: str = None):
        """Log an audit action"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        details_json = json.dumps(details) if details else None
        
        cursor.execute('''
            INSERT INTO audit_logs (telegram_id, giveaway_id, action, details, ip_address)
            VALUES (?, ?, ?, ?, ?)
        ''', (telegram_id, giveaway_id, action, details_json, ip_address))
        
        conn.commit()
        conn.close()

# Global instance
db = DatabaseManager()