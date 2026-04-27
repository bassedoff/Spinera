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
    
    # Post operations - PHASE 4 Enhanced
    def create_post_draft(self, telegram_id: int, post_type: str, 
                         file_id: str = None, text: str = "",
                         caption: str = "", media_type: str = None,
                         file_size: int = None, file_unique_id: str = None,
                         duration: int = None, width: int = None,
                         height: int = None, mime_type: str = None) -> int:
        """Create post draft and return ID (PHASE 4 enhanced)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO post_drafts (
                telegram_id, type, file_id, text, caption,
                media_type, file_size, file_unique_id,
                duration, width, height, mime_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (telegram_id, post_type, file_id, text, caption,
              media_type, file_size, file_unique_id,
              duration, width, height, mime_type))
        
        post_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return post_id
    
    def get_post_draft(self, post_id: int) -> Optional[Dict]:
        """Get post draft by ID (PHASE 4 enhanced)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM post_drafts WHERE id = ?', (post_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            # Get column names from cursor description for safety
            columns = [description[0] for description in cursor.description]
            post_dict = dict(zip(columns, row))
            
            # Convert to expected format with safe defaults
            return {
                'id': post_dict['id'],
                'telegram_id': post_dict['telegram_id'],
                'type': post_dict['type'],
                'file_id': post_dict['file_id'],
                'text': post_dict['text'],
                'caption': post_dict.get('caption', ''),
                'media_type': post_dict.get('media_type'),
                'file_size': post_dict.get('file_size'),
                'file_unique_id': post_dict.get('file_unique_id'),
                'duration': post_dict.get('duration'),
                'width': post_dict.get('width'),
                'height': post_dict.get('height'),
                'mime_type': post_dict.get('mime_type'),
                'is_processed': bool(post_dict.get('is_processed', False)),
                'processed_at': post_dict.get('processed_at'),
                'created_at': post_dict.get('created_at'),
                'updated_at': post_dict.get('updated_at')
            }
        return None
    
    def get_user_posts(self, telegram_id: int) -> List[Dict]:
        """Get all post drafts for user (PHASE 4 enhanced)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM post_drafts 
            WHERE telegram_id = ? 
            ORDER BY created_at DESC
        ''', (telegram_id,))
        
        rows = cursor.fetchall()
        
        # Get column names from cursor description
        columns = [description[0] for description in cursor.description]
        conn.close()
        
        # Convert rows to dictionaries using column names
        posts = []
        for row in rows:
            post_dict = dict(zip(columns, row))
            # Convert to expected format
            post = {
                'id': post_dict['id'],
                'telegram_id': post_dict['telegram_id'],
                'type': post_dict['type'],
                'file_id': post_dict['file_id'],
                'text': post_dict['text'],
                'caption': post_dict.get('caption', ''),
                'media_type': post_dict.get('media_type'),
                'file_size': post_dict.get('file_size'),
                'file_unique_id': post_dict.get('file_unique_id'),
                'duration': post_dict.get('duration'),
                'width': post_dict.get('width'),
                'height': post_dict.get('height'),
                'mime_type': post_dict.get('mime_type'),
                'is_processed': bool(post_dict.get('is_processed', False)),
                'created_at': post_dict.get('created_at'),
                'updated_at': post_dict.get('updated_at')
            }
            posts.append(post)
        
        return posts
    
    # Channel operations
    def resolve_and_save_channel(self, telegram_id: int, identifier: str, 
                               channel_data: Dict) -> int:
        """
        Resolve channel by username or ID and save to database
        Returns channel ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
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
                
                # Get old channel_id for logging
                cursor.execute('SELECT channel_id FROM channels WHERE id = ?', (channel_id,))
                old_row = cursor.fetchone()
                old_channel_id = old_row[0] if old_row else None
                new_channel_id = channel_data.get('chat_id')
                
                # Log if channel_id is changing (stale data repair)
                if old_channel_id != new_channel_id:
                    print(f"🔄 Updating channel_id for channel {channel_id}: {old_channel_id} -> {new_channel_id}")
                
                # Update existing channel - INCLUDING channel_id!
                cursor.execute('''
                    UPDATE channels SET
                        channel_id = ?,
                        title = ?,
                        username = ?,
                        type = ?,
                        bot_is_admin = ?,
                        bot_can_post = ?,
                        permissions_snapshot = ?,
                        members_count = ?,
                        is_active = ?,
                        photo_url = COALESCE(?, photo_url),
                        verified_at = CURRENT_TIMESTAMP,
                        last_permission_check_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND telegram_id = ?
                ''', (
                    new_channel_id,  # <-- THIS WAS MISSING!
                    channel_data.get('title', ''),
                    channel_data.get('username', ''),
                    channel_data.get('type', 'channel'),
                    channel_data.get('bot_is_admin', False),
                    channel_data.get('bot_can_post', False),
                    json.dumps(channel_data.get('permissions_snapshot', {})),
                    channel_data.get('members_count', 0),
                    True,
                    channel_data.get('photo_url'),
                    channel_id,
                    telegram_id
                ))
            else:
                # Create new channel
                cursor.execute('''
                    INSERT INTO channels (
                        telegram_id, channel_id, title, username, type,
                        bot_is_admin, bot_can_post, permissions_snapshot,
                        members_count, is_active, photo_url, verified_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
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
                    True,
                    channel_data.get('photo_url')
                ))
                channel_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            
            return channel_id
            
        except Exception as e:
            print(f"❌ Error in resolve_and_save_channel: {e}")
            conn.close()
            raise
    
    def get_user_channels(self, telegram_id: int) -> List[Dict]:
        """Get all saved channels for user with enhanced details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, channel_id, title, username, type, bot_is_admin, bot_can_post,
                   permissions_snapshot, members_count, is_active,
                   verified_at, last_permission_check_at, created_at, photo_url
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
                'created_at': row[12],
                'photo_url': row[13]
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
    def _generate_deeplink_token(self) -> str:
        """Generate unique deeplink token for giveaway"""
        import secrets
        import string
        alphabet = string.ascii_lowercase + string.digits
        return 'gw_' + ''.join(secrets.choice(alphabet) for _ in range(8))
    
    def _generate_public_slug(self, title: str) -> str:
        """Generate human-readable slug from title"""
        import re
        import secrets
        import string
        # Transliterate common Cyrillic to Latin
        cyrillic_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '',
            'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
        }
        
        # Convert to lowercase and replace cyrillic
        slug = title.lower()
        for cyr, lat in cyrillic_map.items():
            slug = slug.replace(cyr, lat)
        
        # Keep only alphanumeric and spaces
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        # Replace spaces with hyphens
        slug = re.sub(r'[\s_]+', '-', slug)
        # Remove consecutive hyphens
        slug = re.sub(r'-+', '-', slug)
        # Trim hyphens
        slug = slug.strip('-')
        # Limit length
        slug = slug[:30]
        
        # Add random suffix for uniqueness
        suffix = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(4))
        return f"{slug}-{suffix}" if slug else f"giveaway-{suffix}"
    
    def create_giveaway(self, telegram_id: int, title: str, language: str = 'en',
                       post_draft_id: int = None, channels: List[int] = None,
                       prizes: List[Dict] = None, button_text: str = 'Участвовать',
                       button_color: str = 'blue', button_style: str = None,
                       giveaway_type: str = 'wheel',
                       required_channel_ids: List[int] = None,
                       publish_channel_ids: List[int] = None,
                       result_channel_ids: List[int] = None,
                       start_mode: str = 'immediate',
                       start_at: str = None, end_at: str = None,
                       timezone: str = 'UTC', winners_count: int = 1,
                       story_promo_enabled: bool = False,
                       rb_promo_enabled: bool = False,
                       mascot_id: str = None,
                       publish_results_in_source_post: bool = True,
                       reward_mode: str = 'inventory',
                       use_outcome_engine: bool = False,
                       outcomes: List[Dict] = None) -> int:
        """Create giveaway with auto-generated public identity and return ID
        
        Extended rules are stored in rules_json field.
        Type is stored in dedicated column.
        Dates use existing start_at, end_at, timezone columns.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Use publish_channel_ids as primary, fall back to channels for backward compat
        publish_ids = publish_channel_ids or channels or []
        channels_json = json.dumps(publish_ids)
        prizes_json = json.dumps(prizes or [])
        
        # Store extended config in rules_json
        rules = {
            'button_text': button_text,
            'button_preview_color': button_color,  # Renamed for clarity
            'button_style': button_style,  # Normalized Telegram style (primary/success/danger/None)
            'required_channel_ids': required_channel_ids or [],
            'publish_channel_ids': publish_ids,
            'result_channel_ids': result_channel_ids or [],
            'start_mode': start_mode,
            'start_at': start_at,  # Store in rules_json for approve callback
            'end_at': end_at,  # Store in rules_json for reference
            'winners_count': winners_count,
            'story_promo_enabled': story_promo_enabled,
            'rb_promo_enabled': rb_promo_enabled,
            'mascot_id': mascot_id,
            'publish_results_in_source_post': publish_results_in_source_post,
            'reward_mode': reward_mode,
            'use_outcome_engine': use_outcome_engine
        }
        rules_json = json.dumps(rules)
        
        # Determine outcome_mode column value
        outcome_mode_val = 'transparent_weighted' if use_outcome_engine else 'inventory'
        
        # Generate public identity
        deeplink_token = self._generate_deeplink_token()
        public_slug = self._generate_public_slug(title)
        
        cursor.execute('''
            INSERT INTO giveaways 
            (telegram_id, title, language, post_draft_id, channels, prizes, status, 
             type, start_at, end_at, timezone,
             deeplink_token, public_slug, rules_json,
             outcome_mode, use_outcome_engine)
            VALUES (?, ?, ?, ?, ?, ?, 'draft', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (telegram_id, title, language, post_draft_id, channels_json, prizes_json,
              giveaway_type, start_at, end_at, timezone,
              deeplink_token, public_slug, rules_json,
              outcome_mode_val, use_outcome_engine))
        
        giveaway_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✅ Created giveaway {giveaway_id} with deeplink_token={deeplink_token}, public_slug={public_slug}, reward_mode={reward_mode}, use_outcome_engine={use_outcome_engine}")
        return giveaway_id
    
    def create_outcomes_batch(self, giveaway_id: int, outcomes: List[Dict]) -> int:
        """Create multiple outcomes for a probability-mode giveaway.
        
        Each outcome dict should have keys:
        - outcome_type (required): 'prize'|'coupon'|'blank'|'consolation'|'custom'
        - title (required)
        - description, prize_ref_name, base_weight, max_qty, is_unlimited,
          rarity_tier, sort_order, public_label, color, icon
        """
        count = 0
        for outcome_data in (outcomes or []):
            self.create_outcome(giveaway_id, outcome_data)
            count += 1
        return count
    
    def ensure_public_identity(self, giveaway_id: int) -> Dict[str, str]:
        """Ensure giveaway has public identity (deeplink_token and public_slug)
        
        Returns dict with deeplink_token and public_slug
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT deeplink_token, public_slug FROM giveaways WHERE id = ?', (giveaway_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            raise ValueError(f"Giveaway {giveaway_id} not found")
        
        deeplink_token, public_slug = row
        
        # Generate if missing
        if not deeplink_token or not public_slug:
            if not deeplink_token:
                deeplink_token = self._generate_deeplink_token()
            if not public_slug:
                cursor.execute('SELECT title FROM giveaways WHERE id = ?', (giveaway_id,))
                title = cursor.fetchone()[0]
                public_slug = self._generate_public_slug(title)
            
            cursor.execute('''
                UPDATE giveaways 
                SET deeplink_token = ?, public_slug = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (deeplink_token, public_slug, giveaway_id))
            
            conn.commit()
            print(f"✅ Ensured public identity for giveaway {giveaway_id}: token={deeplink_token}, slug={public_slug}")
        
        conn.close()
        return {'deeplink_token': deeplink_token, 'public_slug': public_slug}
    
    def get_giveaway_by_deeplink_token(self, token: str) -> Optional[Dict]:
        """Get giveaway by deeplink token - excludes deleted giveaways"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Exclude deleted giveaways from public access
        cursor.execute(
            'SELECT * FROM giveaways WHERE deeplink_token = ? AND COALESCE(is_deleted, 0) = 0',
            (token,)
        )
        row = cursor.fetchone()
        
        if row:
            columns = [description[0] for description in cursor.description]
            giveaway_dict = dict(zip(columns, row))
            conn.close()
            
            return {
                'id': giveaway_dict['id'],
                'telegram_id': giveaway_dict['telegram_id'],
                'title': giveaway_dict['title'],
                'description': giveaway_dict.get('description'),
                'language': giveaway_dict.get('language', 'en'),
                'post_draft_id': giveaway_dict.get('post_draft_id'),
                'channels': json.loads(giveaway_dict.get('channels', '[]') or '[]'),
                'prizes': json.loads(giveaway_dict.get('prizes', '[]') or '[]'),
                'type': giveaway_dict.get('type', 'wheel'),
                'start_at': giveaway_dict.get('start_at'),
                'end_at': giveaway_dict.get('end_at'),
                'timezone': giveaway_dict.get('timezone', 'UTC'),
                'status': giveaway_dict.get('status', 'draft'),
                'public_slug': giveaway_dict.get('public_slug'),
                'deeplink_token': giveaway_dict.get('deeplink_token'),
                'rules_json': giveaway_dict.get('rules_json'),
                'published_message_id': giveaway_dict.get('published_message_id'),
                'published_at': giveaway_dict.get('published_at'),
                'preview_message_id': giveaway_dict.get('preview_message_id'),
                'created_at': giveaway_dict.get('created_at'),
                'updated_at': giveaway_dict.get('updated_at'),
                'is_deleted': giveaway_dict.get('is_deleted', 0)
            }
        
        conn.close()
        return None
    
    def get_giveaway(self, giveaway_id: int) -> Optional[Dict]:
        """Get giveaway by ID - uses cursor.description for safe column mapping"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM giveaways WHERE id = ?', (giveaway_id,))
        row = cursor.fetchone()
        
        if row:
            # Get column names from cursor description for safety
            columns = [description[0] for description in cursor.description]
            giveaway_dict = dict(zip(columns, row))
            conn.close()
            
            # Convert to expected format with safe defaults
            result = {
                'id': giveaway_dict['id'],
                'telegram_id': giveaway_dict['telegram_id'],
                'title': giveaway_dict['title'],
                'description': giveaway_dict.get('description'),
                'language': giveaway_dict.get('language', 'en'),
                'post_draft_id': giveaway_dict.get('post_draft_id'),
                'channels': json.loads(giveaway_dict.get('channels', '[]') or '[]'),
                'prizes': json.loads(giveaway_dict.get('prizes', '[]') or '[]'),
                'type': giveaway_dict.get('type', 'wheel'),
                'start_at': giveaway_dict.get('start_at'),
                'end_at': giveaway_dict.get('end_at'),
                'timezone': giveaway_dict.get('timezone', 'UTC'),
                'status': giveaway_dict.get('status', 'draft'),
                'public_slug': giveaway_dict.get('public_slug'),
                'deeplink_token': giveaway_dict.get('deeplink_token'),
                'rules_json': giveaway_dict.get('rules_json'),
                'published_message_id': giveaway_dict.get('published_message_id'),
                'published_at': giveaway_dict.get('published_at'),
                'preview_message_id': giveaway_dict.get('preview_message_id'),
                'created_at': giveaway_dict.get('created_at'),
                'updated_at': giveaway_dict.get('updated_at'),
                'is_deleted': giveaway_dict.get('is_deleted', 0),  # Soft delete flag
                # Parsed rules_json fields for convenience
                'required_channel_ids': [],
                'publish_channel_ids': [],
                'result_channel_ids': [],
                'button_text': 'Участвовать',
                'button_preview_color': 'blue',
                'button_style': None,
                'start_mode': 'immediate',
                'winners_count': 1,
                'story_promo_enabled': False,
                'rb_promo_enabled': False,
                'mascot_id': None,
                'publish_results_in_source_post': True
            }
                
            # Parse rules_json and merge into response
            if giveaway_dict.get('rules_json'):
                try:
                    rules = json.loads(giveaway_dict['rules_json'])
                    result['required_channel_ids'] = rules.get('required_channel_ids', [])
                    result['publish_channel_ids'] = rules.get('publish_channel_ids', [])
                    result['result_channel_ids'] = rules.get('result_channel_ids', [])
                    result['button_text'] = rules.get('button_text', 'Участвовать')
                    result['button_preview_color'] = rules.get('button_preview_color', rules.get('button_color', 'blue'))
                    result['button_style'] = rules.get('button_style')
                    result['start_mode'] = rules.get('start_mode', 'immediate')
                    result['winners_count'] = rules.get('winners_count', 1)
                    result['story_promo_enabled'] = rules.get('story_promo_enabled', False)
                    result['rb_promo_enabled'] = rules.get('rb_promo_enabled', False)
                    result['mascot_id'] = rules.get('mascot_id')
                    result['publish_results_in_source_post'] = rules.get('publish_results_in_source_post', True)
                    result['reward_mode'] = rules.get('reward_mode', 'inventory')
                    result['use_outcome_engine'] = rules.get('use_outcome_engine', False)
                except (json.JSONDecodeError, TypeError):
                    pass
                
            # Also read from dedicated columns (take precedence over rules_json)
            if giveaway_dict.get('use_outcome_engine') is not None:
                result['use_outcome_engine'] = bool(giveaway_dict['use_outcome_engine'])
            if giveaway_dict.get('outcome_mode') is not None:
                result['outcome_mode'] = giveaway_dict['outcome_mode']
            # Ensure reward_mode defaults if not set
            if 'reward_mode' not in result or result['reward_mode'] is None:
                result['reward_mode'] = 'inventory'
                
            return result
    
        conn.close()
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
    
    def set_giveaway_preview_message_id(self, giveaway_id: int, message_id: int):
        """Save preview message ID for giveaway"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE giveaways 
            SET preview_message_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (message_id, giveaway_id))
        
        conn.commit()
        conn.close()

    def soft_delete_giveaway(self, giveaway_id: int) -> None:
        """Soft delete a giveaway by setting is_deleted flag"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE giveaways 
            SET is_deleted = 1, status = 'deleted', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (giveaway_id,))
        
        conn.commit()
        conn.close()
    
    def cancel_pending_jobs(self, giveaway_id: int) -> None:
        """Cancel all pending jobs for a giveaway"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE jobs 
            SET status = 'cancelled', error_message = 'Giveaway deleted'
            WHERE giveaway_id = ? AND status IN ('pending', 'scheduled')
        ''', (giveaway_id,))
        
        conn.commit()
        conn.close()
    
    def get_channels_by_ids(self, channel_ids: List[int]) -> List[Dict]:
        """Get channels by internal IDs (for publish flow)"""
        if not channel_ids:
            return []
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        placeholders = ','.join('?' * len(channel_ids))
        cursor.execute(f'''
            SELECT id, channel_id, title, username, type, bot_is_admin, bot_can_post
            FROM channels 
            WHERE id IN ({placeholders})
        ''', channel_ids)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'id': row[0],
            'channel_id': row[1],  # Telegram chat_id
            'title': row[2],
            'username': row[3],
            'type': row[4],
            'bot_is_admin': bool(row[5]),
            'bot_can_post': bool(row[6])
        } for row in rows]
    
    def update_channel_id(self, internal_id: int, new_channel_id: int) -> bool:
        """Update channel_id for a channel (used in self-heal during publish)
        
        Args:
            internal_id: Internal channel ID (primary key)
            new_channel_id: New Telegram chat_id
            
        Returns:
            True if updated successfully
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE channels 
                SET channel_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_channel_id, internal_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Error updating channel_id: {e}")
            conn.close()
            return False
    
    def get_channels_with_username(self, telegram_id: int = None) -> List[Dict]:
        """Get channels that have a username (candidates for repair)
        
        Args:
            telegram_id: Optional user ID to filter by
            
        Returns:
            List of channels with username field populated
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if telegram_id:
            cursor.execute('''
                SELECT id, channel_id, title, username, telegram_id
                FROM channels 
                WHERE telegram_id = ? AND username IS NOT NULL AND username != ''
            ''', (telegram_id,))
        else:
            cursor.execute('''
                SELECT id, channel_id, title, username, telegram_id
                FROM channels 
                WHERE username IS NOT NULL AND username != ''
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'id': row[0],
            'channel_id': row[1],
            'title': row[2],
            'username': row[3],
            'telegram_id': row[4]
        } for row in rows]
    
    def get_suspicious_channels(self) -> List[Dict]:
        """Get channels with potentially stale/mock channel_ids
        
        Returns channels where channel_id looks like a mock/dev value:
        - channel_id = -1001234567890 (the original mock value)
        - channel_id in range -1000000000000 to -1000001000000 (dev mock range)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, channel_id, title, username, telegram_id
            FROM channels 
            WHERE channel_id = -1001234567890
               OR (channel_id < -1000000000000 AND channel_id > -1000001000000)
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'id': row[0],
            'channel_id': row[1],
            'title': row[2],
            'username': row[3],
            'telegram_id': row[4]
        } for row in rows]
    
    def save_publish_result(self, giveaway_id: int, published_message_ids: Dict[str, int], 
                           status: str = 'active'):
        """Save publish result after successful posting to channels
        
        Args:
            giveaway_id: Giveaway ID
            published_message_ids: Dict mapping channel_id to message_id, e.g. {"-100123": 456}
            status: New status (default 'active')
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        published_message_id_json = json.dumps(published_message_ids)
        
        cursor.execute('''
            UPDATE giveaways 
            SET published_message_id = ?, published_at = CURRENT_TIMESTAMP, 
                status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (published_message_id_json, status, giveaway_id))
        
        conn.commit()
        conn.close()
    
    def _normalize_giveaway_row(self, row, cursor_description) -> Dict:
        """Convert a raw giveaway row to a normalized dict using cursor.description.
        Includes rules_json parsing, lifecycle normalization, and status_group."""
        columns = [d[0] for d in cursor_description]
        g = dict(zip(columns, row))
        
        result = {
            'id': g['id'],
            'telegram_id': g['telegram_id'],
            'title': g['title'],
            'description': g.get('description'),
            'language': g.get('language', 'en'),
            'post_draft_id': g.get('post_draft_id'),
            'channels': json.loads(g.get('channels', '[]') or '[]'),
            'prizes': json.loads(g.get('prizes', '[]') or '[]'),
            'type': g.get('type', 'wheel'),
            'start_at': g.get('start_at'),
            'end_at': g.get('end_at'),
            'timezone': g.get('timezone', 'UTC'),
            'status': g.get('status', 'draft'),
            'public_slug': g.get('public_slug'),
            'deeplink_token': g.get('deeplink_token'),
            'rules_json': g.get('rules_json'),
            'published_message_id': g.get('published_message_id'),
            'published_at': g.get('published_at'),
            'preview_message_id': g.get('preview_message_id'),
            'created_at': g.get('created_at'),
            'updated_at': g.get('updated_at'),
            # Parsed rules_json fields
            'required_channel_ids': [],
            'publish_channel_ids': [],
            'result_channel_ids': [],
            'button_text': 'Участвовать',
            'button_preview_color': 'blue',
            'button_style': None,
            'start_mode': 'immediate',
            'winners_count': 1,
            'story_promo_enabled': False,
            'rb_promo_enabled': False,
            'mascot_id': None,
            'publish_results_in_source_post': True
        }
        
        # Parse rules_json and merge
        if g.get('rules_json'):
            try:
                rules = json.loads(g['rules_json'])
                result['required_channel_ids'] = rules.get('required_channel_ids', [])
                result['publish_channel_ids'] = rules.get('publish_channel_ids', [])
                result['result_channel_ids'] = rules.get('result_channel_ids', [])
                result['button_text'] = rules.get('button_text', 'Участвовать')
                result['button_preview_color'] = rules.get('button_preview_color', rules.get('button_color', 'blue'))
                result['button_style'] = rules.get('button_style')
                result['start_mode'] = rules.get('start_mode', 'immediate')
                result['winners_count'] = rules.get('winners_count', 1)
                result['story_promo_enabled'] = rules.get('story_promo_enabled', False)
                result['rb_promo_enabled'] = rules.get('rb_promo_enabled', False)
                result['mascot_id'] = rules.get('mascot_id')
                result['publish_results_in_source_post'] = rules.get('publish_results_in_source_post', True)
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Lazy lifecycle normalization: active but expired -> ended
        if result['status'] == 'active' and result['end_at']:
            try:
                from datetime import timezone as _tz
                end_dt = datetime.fromisoformat(result['end_at'])
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=_tz.utc)
                if datetime.now(_tz.utc) > end_dt:
                    result['status'] = 'ended'
                    result['_lifecycle_changed'] = True  # Signal to persist
            except (ValueError, TypeError):
                pass
        
        # Compute status_group
        status_group_map = {
            'active': 'active',
            'draft': 'waiting', 'pending_preview': 'waiting', 'preview_sent': 'waiting', 'approved': 'waiting',
            'ended': 'ended',
            'rejected': 'cancelled', 'cancelled': 'cancelled',
            'failed': 'failed'
        }
        result['status_group'] = status_group_map.get(result['status'], 'waiting')
        
        return result
    
    def get_user_giveaways(self, telegram_id: int, status: str = None) -> List[Dict]:
        """Get user giveaways with optional status filter - uses safe cursor.description mapping
        
        Includes lazy lifecycle normalization: active giveaways past end_at are
        normalized to 'ended' and persisted back to the database.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT * FROM giveaways 
                WHERE telegram_id = ? AND status = ? AND COALESCE(is_deleted, 0) = 0
                ORDER BY created_at DESC
            ''', (telegram_id, status))
        else:
            cursor.execute('''
                SELECT * FROM giveaways 
                WHERE telegram_id = ? AND COALESCE(is_deleted, 0) = 0
                ORDER BY created_at DESC
            ''', (telegram_id,))
        
        rows = cursor.fetchall()
        desc = cursor.description
        conn.close()
        
        results = []
        for row in rows:
            normalized = self._normalize_giveaway_row(row, desc)
            # Persist lifecycle transitions (active -> ended)
            if normalized.get('_lifecycle_changed'):
                self._persist_lifecycle_status(normalized['id'], normalized['status'])
            results.append(normalized)
        return results
    
    def get_user_giveaways_by_statuses(self, telegram_id: int, statuses: List[str]) -> List[Dict]:
        """Get user giveaways filtered by multiple statuses - uses safe cursor.description mapping
        
        Includes lazy lifecycle normalization and persistence.
        """
        if not statuses:
            return []
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        placeholders = ','.join('?' * len(statuses))
        cursor.execute(f'''
            SELECT * FROM giveaways 
            WHERE telegram_id = ? AND status IN ({placeholders}) AND COALESCE(is_deleted, 0) = 0
            ORDER BY created_at DESC
        ''', [telegram_id] + statuses)
        
        rows = cursor.fetchall()
        desc = cursor.description
        conn.close()
        
        results = []
        for row in rows:
            normalized = self._normalize_giveaway_row(row, desc)
            if normalized.get('_lifecycle_changed'):
                self._persist_lifecycle_status(normalized['id'], normalized['status'])
            results.append(normalized)
        return results
    
    def get_giveaways_using_post(self, post_id: int) -> List[Dict]:
        """Get all giveaways that use a specific post draft"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, status FROM giveaways 
            WHERE post_draft_id = ?
            ORDER BY created_at DESC
        ''', (post_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{'id': row[0], 'title': row[1], 'status': row[2]} for row in rows]
    
    def get_giveaways_using_channel(self, channel_id: int) -> List[Dict]:
        """Get all giveaways that use a specific channel (single-pass, no N+1)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, title, status, channels FROM giveaways')
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description] if cursor.description else []
        conn.close()
        
        result = []
        for row in rows:
            d = dict(zip(columns, row))
            try:
                channels = json.loads(d.get('channels', '[]') or '[]')
            except (json.JSONDecodeError, TypeError):
                channels = []
            if channel_id in channels:
                result.append({'id': d['id'], 'title': d['title'], 'status': d['status']})
        
        return result
    
    def delete_post_draft(self, post_id: int) -> bool:
        """Delete a post draft by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM post_drafts WHERE id = ?', (post_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
    
    def delete_channel(self, channel_id: int) -> bool:
        """Delete a channel by internal ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM channels WHERE id = ?', (channel_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
    
    def _persist_lifecycle_status(self, giveaway_id: int, new_status: str):
        """Persist a lifecycle status change to the database.
        
        Called lazily when _normalize_giveaway_row detects a transition
        (e.g. active -> ended). Uses a separate connection to avoid
        interfering with any ongoing transaction.
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE giveaways 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status != ?
            ''', (new_status, giveaway_id, new_status))
            conn.commit()
            conn.close()
            print(f"✅ Persisted lifecycle transition for giveaway {giveaway_id}: -> {new_status}")
        except Exception as e:
            print(f"⚠️ Failed to persist lifecycle status for giveaway {giveaway_id}: {e}")

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
    
    def update_spin_result(self, spin_id: int, result_type: str, prize_name: str = None, animation_data: dict = None):
        """Update spin with result (for outcome engine two-phase commit)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        animation_json = json.dumps(animation_data) if animation_data else None
        
        cursor.execute('''
            UPDATE spins 
            SET result_type = ?, prize_name = ?, animation_data = ?, spun_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (result_type, prize_name, animation_json, spin_id))
        
        conn.commit()
        conn.close()
    
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
        """Get all winners for a giveaway - uses cursor.description for safe mapping"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM winners 
            WHERE giveaway_id = ?
            ORDER BY created_at DESC
        ''', (giveaway_id,))
        
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description] if cursor.description else []
        conn.close()
        
        result = []
        for row in rows:
            d = dict(zip(columns, row))
            result.append({
                'id': d.get('id'),
                'giveaway_id': d.get('giveaway_id'),
                'participant_id': d.get('participant_id'),
                'spin_id': d.get('spin_id'),
                'prize_name': d.get('prize_name'),
                'prize_description': d.get('prize_description'),
                'status': d.get('status', 'pending_issue'),
                'manager_comment': d.get('manager_comment'),
                'issued_at': d.get('issued_at'),
                'created_at': d.get('created_at')
            })
        return result
    
    def update_winner_status(self, winner_id: int, status: str, manager_comment: str = None):
        """Update winner status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Only set issued_at when status is 'issued'
        if status == 'issued':
            cursor.execute('''
                UPDATE winners
                SET status = ?, manager_comment = ?, issued_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, manager_comment, winner_id))
        else:
            cursor.execute('''
                UPDATE winners
                SET status = ?, manager_comment = ?
                WHERE id = ?
            ''', (status, manager_comment, winner_id))
        
        conn.commit()
        conn.close()
    
    def count_participants(self, giveaway_id: int) -> int:
        """Count participants for a giveaway"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM participants WHERE giveaway_id = ?', (giveaway_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_giveaway_admin_summary(self, giveaway_id: int) -> Optional[Dict]:
        """Get giveaway with admin summary: participant counts, winner stats, prize inventory
        
        Includes lifecycle normalization: active giveaways past end_at are normalized to 'ended'.
        Returns None for deleted giveaways.
        """
        # Use _normalize_giveaway_row for lifecycle normalization
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM giveaways WHERE id = ?', (giveaway_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        desc = cursor.description
        conn.close()
        
        giveaway = self._normalize_giveaway_row(row, desc)
        
        # Block deleted giveaways from admin access
        if giveaway.get('is_deleted', 0):
            return None
        
        # Persist lifecycle transition if needed
        if giveaway.get('_lifecycle_changed'):
            self._persist_lifecycle_status(giveaway['id'], giveaway['status'])
        # Remove internal flag before returning
        giveaway.pop('_lifecycle_changed', None)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Participant count
        cursor.execute('SELECT COUNT(*) FROM participants WHERE giveaway_id = ?', (giveaway_id,))
        participants_count = cursor.fetchone()[0]
        
        # Spins count
        cursor.execute('SELECT COUNT(*) FROM spins WHERE giveaway_id = ?', (giveaway_id,))
        spins_count = cursor.fetchone()[0]
        
        # Winner stats
        cursor.execute('''
            SELECT status, COUNT(*) FROM winners
            WHERE giveaway_id = ? GROUP BY status
        ''', (giveaway_id,))
        winner_stats = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        giveaway['participants_count'] = participants_count
        giveaway['spins_count'] = spins_count
        giveaway['winners_count'] = sum(winner_stats.values())
        giveaway['pending_issue_count'] = winner_stats.get('pending_issue', 0)
        giveaway['issued_count'] = winner_stats.get('issued', 0)
        giveaway['cancelled_count'] = winner_stats.get('cancelled', 0)
        
        # Prize inventory: how many of each prize have been awarded
        prizes = giveaway.get('prizes', [])
        if prizes:
            conn2 = self.get_connection()
            cur2 = conn2.cursor()
            for prize in prizes:
                name = prize.get('name', '')
                cur2.execute(
                    'SELECT COUNT(*) FROM winners WHERE giveaway_id = ? AND prize_name = ?',
                    (giveaway_id, name)
                )
                prize['awarded'] = cur2.fetchone()[0]
                prize['remaining'] = max(0, prize.get('qty', 1) - prize['awarded'])
            conn2.close()
        
        return giveaway
    
    def get_giveaway_winners_detailed(self, giveaway_id: int) -> List[Dict]:
        """Get winners with user data via JOIN"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT w.id, w.participant_id, w.prize_name, w.prize_description,
                   w.status, w.manager_comment, w.issued_at, w.created_at,
                   p.telegram_id, u.username, u.first_name, u.last_name
            FROM winners w
            JOIN participants p ON w.participant_id = p.id
            LEFT JOIN users u ON p.telegram_id = u.telegram_id
            WHERE w.giveaway_id = ?
            ORDER BY w.created_at DESC
        ''', (giveaway_id,))
        
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
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
        elif status == 'cancelled':
            cursor.execute('''
                UPDATE jobs 
                SET status = ?, error_message = 'Cancelled by user'
                WHERE id = ?
            ''', (status, job_id))
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
    
    # Participant operations for public flow
    def get_or_create_participant(self, giveaway_id: int, telegram_id: int) -> Dict:
        """Get existing participant or create new one
        
        Returns participant dict with 'is_new' flag
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if exists
        cursor.execute('''
            SELECT id, giveaway_id, telegram_id, joined_at, eligibility_status
            FROM participants 
            WHERE giveaway_id = ? AND telegram_id = ?
        ''', (giveaway_id, telegram_id))
        
        row = cursor.fetchone()
        
        if row:
            conn.close()
            return {
                'id': row[0],
                'giveaway_id': row[1],
                'telegram_id': row[2],
                'joined_at': row[3],
                'eligibility_status': row[4],
                'is_new': False
            }
        
        # Create new participant
        cursor.execute('''
            INSERT INTO participants (giveaway_id, telegram_id, eligibility_status)
            VALUES (?, ?, 'eligible')
        ''', (giveaway_id, telegram_id))
        
        participant_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            'id': participant_id,
            'giveaway_id': giveaway_id,
            'telegram_id': telegram_id,
            'joined_at': None,
            'eligibility_status': 'eligible',
            'is_new': True
        }
    
    def get_participant(self, giveaway_id: int, telegram_id: int) -> Optional[Dict]:
        """Get participant if exists"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, giveaway_id, telegram_id, joined_at, eligibility_status
            FROM participants 
            WHERE giveaway_id = ? AND telegram_id = ?
        ''', (giveaway_id, telegram_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'giveaway_id': row[1],
                'telegram_id': row[2],
                'joined_at': row[3],
                'eligibility_status': row[4]
            }
        return None
    
    def get_spin_by_participant(self, participant_id: int) -> Optional[Dict]:
        """Get existing spin for participant"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, participant_id, giveaway_id, result_type, prize_id, spun_at, animation_data
            FROM spins 
            WHERE participant_id = ?
        ''', (participant_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'participant_id': row[1],
                'giveaway_id': row[2],
                'result_type': row[3],
                'prize_id': row[4],
                'spun_at': row[5],
                'animation_data': json.loads(row[6]) if row[6] else None
            }
        return None
    
    def get_spin_by_telegram_id(self, giveaway_id: int, telegram_id: int) -> Optional[Dict]:
        """Get existing spin for user in giveaway"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.id, s.participant_id, s.giveaway_id, s.result_type, s.prize_id, s.spun_at, s.animation_data
            FROM spins s
            JOIN participants p ON s.participant_id = p.id
            WHERE s.giveaway_id = ? AND p.telegram_id = ?
        ''', (giveaway_id, telegram_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'participant_id': row[1],
                'giveaway_id': row[2],
                'result_type': row[3],
                'prize_id': row[4],
                'spun_at': row[5],
                'animation_data': json.loads(row[6]) if row[6] else None
            }
        return None
    
    def create_spin_with_result(self, participant_id: int, giveaway_id: int, 
                                 result_type: str, prize_id: int = None,
                                 prize_name: str = None, prize_description: str = None,
                                 animation_data: dict = None) -> Dict:
        """Create spin and optionally winner record
        
        Uses transaction to ensure atomicity.
        
        Returns spin dict
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Start transaction (SQLite auto-starts on first statement)
            animation_json = json.dumps(animation_data) if animation_data else None
            
            # Create spin
            cursor.execute('''
                INSERT INTO spins (participant_id, giveaway_id, result_type, prize_id, animation_data)
                VALUES (?, ?, ?, ?, ?)
            ''', (participant_id, giveaway_id, result_type, prize_id, animation_json))
            
            spin_id = cursor.lastrowid
            
            # If win, create winner record
            # Note: Use 'is not None' check because prize_id can be 0 (first prize)
            if result_type == 'win' and prize_id is not None and prize_name:
                cursor.execute('''
                    INSERT INTO winners (giveaway_id, participant_id, spin_id, prize_name, prize_description)
                    VALUES (?, ?, ?, ?, ?)
                ''', (giveaway_id, participant_id, spin_id, prize_name, prize_description))
            
            conn.commit()
            
            return {
                'id': spin_id,
                'participant_id': participant_id,
                'giveaway_id': giveaway_id,
                'result_type': result_type,
                'prize_id': prize_id,
                'animation_data': animation_data
            }
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def count_winners_for_prize(self, giveaway_id: int, prize_name: str) -> int:
        """Count how many times a specific prize has been won"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM winners 
            WHERE giveaway_id = ? AND prize_name = ?
        ''', (giveaway_id, prize_name))
        
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_participant_spin_count(self, participant_id: int) -> int:
        """Get number of spins for a participant (0-based sequence number)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT COUNT(*) FROM spins WHERE participant_id = ?',
            (participant_id,)
        )
        
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_prize_inventory(self, giveaway_id: int) -> List[Dict]:
        """Get prizes with remaining quantity"""
        giveaway = self.get_giveaway(giveaway_id)
        if not giveaway:
            return []
        
        prizes = giveaway.get('prizes', [])
        
        # Count winners for each prize
        result = []
        for idx, prize in enumerate(prizes):
            prize_name = prize.get('name', '')
            total_qty = prize.get('qty', 1)
            won_count = self.count_winners_for_prize(giveaway_id, prize_name)
            remaining = total_qty - won_count
            
            result.append({
                'index': idx,
                'name': prize_name,
                'description': prize.get('description', ''),
                'weight': prize.get('weight', 1),
                'total_qty': total_qty,
                'won_count': won_count,
                'remaining': remaining
            })
        
        return result
    
    # ============================================
    # FAIR CHANCE OUTCOME ENGINE METHODS
    # ============================================
    
    def create_outcome(self, giveaway_id: int, outcome_data: dict) -> int:
        """Create reward outcome, return outcome_id"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO reward_outcomes (
                giveaway_id, outcome_type, title, description, prize_ref_name,
                base_weight, probability_mode, max_qty, is_unlimited,
                fallback_outcome_id, rarity_tier, sort_order, is_active,
                public_label, color, icon, visual_style
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            giveaway_id,
            outcome_data['outcome_type'],
            outcome_data['title'],
            outcome_data.get('description', ''),
            outcome_data.get('prize_ref_name'),
            outcome_data.get('base_weight', 1),
            outcome_data.get('probability_mode', 'weighted'),
            outcome_data.get('max_qty'),
            outcome_data.get('is_unlimited', False),
            outcome_data.get('fallback_outcome_id'),
            outcome_data.get('rarity_tier', 'common'),
            outcome_data.get('sort_order', 0),
            outcome_data.get('is_active', True),
            outcome_data.get('public_label'),
            outcome_data.get('color', '#808080'),
            outcome_data.get('icon', '🎁'),
            outcome_data.get('visual_style', 'default')
        ))
        
        outcome_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return outcome_id
    
    def get_active_outcomes(self, giveaway_id: int) -> list:
        """Get all active outcomes for giveaway with remaining_qty calculated"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get outcomes with won_count subquery
        cursor.execute('''
            SELECT ro.*,
                   COALESCE(
                       (SELECT COUNT(*) FROM winners w 
                        JOIN spins s ON w.spin_id = s.id 
                        WHERE s.giveaway_id = ? 
                        AND (ro.prize_ref_name IS NULL OR w.prize_name = ro.prize_ref_name)),
                       0
                   ) as won_count
            FROM reward_outcomes ro
            WHERE ro.giveaway_id = ? AND ro.is_active = 1
            ORDER BY ro.sort_order, ro.id
        ''', (giveaway_id, giveaway_id))
        
        outcomes = []
        for row in cursor.fetchall():
            outcome = dict(zip([d[0] for d in cursor.description], row))
            
            # Calculate remaining quantity
            if outcome['is_unlimited']:
                outcome['remaining_qty'] = 999999
            elif outcome['max_qty']:
                outcome['remaining_qty'] = outcome['max_qty'] - outcome['won_count']
            else:
                outcome['remaining_qty'] = 0
            
            outcomes.append(outcome)
        
        conn.close()
        return outcomes
    
    def get_outcomes_for_template(self, giveaway_id: int) -> list:
        """Get lightweight outcome list for template/relaunch — no won_count needed"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT outcome_type, title, description, prize_ref_name,
                   base_weight, probability_mode, max_qty, is_unlimited,
                   rarity_tier, sort_order, public_label, color, icon
            FROM reward_outcomes
            WHERE giveaway_id = ? AND is_active = 1
            ORDER BY sort_order, id
        ''', (giveaway_id,))
        
        outcomes = [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]
        conn.close()
        return outcomes
    
    def get_wheel_layout(self, giveaway_id: int) -> list:
        """Get outcomes formatted for wheel visualization"""
        outcomes = self.get_active_outcomes(giveaway_id)
        
        return [
            {
                'id': o['id'],
                'label': o['public_label'] or o['title'],
                'color': o.get('color', '#808080'),
                'icon': o.get('icon', '🎁'),
                'rarity_tier': o['rarity_tier'],
                'weight': o['base_weight']
            }
            for o in outcomes
        ]
    
    def get_outcome(self, outcome_id: int) -> dict:
        """Get single outcome by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM reward_outcomes WHERE id = ?', (outcome_id,))
        row = cursor.fetchone()
        
        if row:
            outcome = dict(zip([d[0] for d in cursor.description], row))
            
            # Calculate remaining
            if outcome['is_unlimited']:
                outcome['remaining_qty'] = 999999
            elif outcome['max_qty']:
                cursor.execute(
                    'SELECT COUNT(*) FROM winners w JOIN spins s ON w.spin_id = s.id WHERE s.giveaway_id = (SELECT giveaway_id FROM reward_outcomes WHERE id = ?) AND (w.prize_name = ? OR ? IS NULL)',
                    (outcome_id, outcome.get('prize_ref_name'), outcome.get('prize_ref_name'))
                )
                won_count = cursor.fetchone()[0]
                outcome['remaining_qty'] = outcome['max_qty'] - won_count
            else:
                outcome['remaining_qty'] = 0
            
            conn.close()
            return outcome
        
        conn.close()
        return None
    
    def get_blank_outcome(self, giveaway_id: int) -> dict:
        """Get blank/no-win outcome for fallback"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM reward_outcomes 
            WHERE giveaway_id = ? AND outcome_type = 'blank' AND is_active = 1
            ORDER BY is_unlimited DESC, base_weight DESC
            LIMIT 1
        ''', (giveaway_id,))
        
        row = cursor.fetchone()
        
        if row:
            outcome = dict(zip([d[0] for d in cursor.description], row))
            conn.close()
            return outcome
        
        conn.close()
        return None
    
    def save_spin_audit(self, **kwargs):
        """Save spin audit record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO spin_audit (
                giveaway_id, participant_id, spin_id, server_seed_hash,
                roll_value, roll_source, effective_outcomes_snapshot,
                selection_method, chosen_outcome_id, chosen_outcome_type,
                fallback_used
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            kwargs['giveaway_id'],
            kwargs['participant_id'],
            kwargs['spin_id'],
            kwargs['server_seed_hash'],
            kwargs['roll_value'],
            kwargs.get('roll_source'),
            json.dumps(kwargs['effective_outcomes_snapshot']),
            kwargs['selection_method'],
            kwargs['chosen_outcome_id'],
            kwargs['chosen_outcome_type'],
            kwargs.get('fallback_used', False)
        ))
        
        conn.commit()
        conn.close()
    
    def update_giveaway_fairness(self, giveaway_id: int, server_seed: str, server_seed_hash: str):
        """Update giveaway with fairness data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE giveaways 
            SET server_seed = ?, server_seed_hash = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (server_seed, server_seed_hash, giveaway_id))
        
        conn.commit()
        conn.close()
    
    def get_current_odds(self, giveaway_id: int) -> list:
        """Get current odds disclosure for participant UI"""
        outcomes = self.get_active_outcomes(giveaway_id)
        
        if not outcomes:
            return []
        
        # Filter eligible outcomes
        eligible = [o for o in outcomes if o['is_unlimited'] or o['remaining_qty'] > 0]
        
        if not eligible:
            return []
        
        total_weight = sum(o['base_weight'] for o in eligible)
        
        if total_weight == 0:
            return []
        
        odds = []
        for o in eligible:
            probability = (o['base_weight'] / total_weight * 100)
            odds.append({
                'id': o['id'],
                'title': o['public_label'] or o['title'],
                'type': o['outcome_type'],
                'rarity_tier': o['rarity_tier'],
                'probability': round(probability, 2),
                'remaining': o['remaining_qty'] if not o['is_unlimited'] else '∞',
                'color': o.get('color', '#808080'),
                'icon': o.get('icon', '🎁')
            })
        
        return odds
    
    def migrate_giveaway_to_outcomes(self, giveaway_id: int) -> bool:
        """
        Migrate old giveaway from prizes[] to reward_outcomes
        
        Returns True if migration happened, False if already migrated
        """
        giveaway = self.get_giveaway(giveaway_id)
        
        if not giveaway:
            return False
        
        # Check if already migrated
        if giveaway.get('use_outcome_engine'):
            return False
        
        prizes = giveaway.get('prizes', [])
        
        if not prizes:
            # No prizes to migrate
            return False
        
        # Create outcomes from prizes
        for idx, prize in enumerate(prizes):
            outcome_data = {
                'outcome_type': 'prize',
                'title': prize.get('name', f'Prize {idx+1}'),
                'description': prize.get('description', ''),
                'prize_ref_name': prize.get('name'),
                'base_weight': prize.get('weight', 1),
                'max_qty': prize.get('qty', 1),
                'is_unlimited': False,
                'rarity_tier': 'common',
                'sort_order': idx,
                'public_label': prize.get('name'),
                'color': self._get_prize_color(idx),
                'icon': '🎁'
            }
            
            self.create_outcome(giveaway_id, outcome_data)
        
        # Add blank outcome
        blank_data = {
            'outcome_type': 'blank',
            'title': 'Без выигрыша',
            'description': 'К сожалению, в этот раз вам не повезло',
            'base_weight': 50,
            'max_qty': None,
            'is_unlimited': True,
            'rarity_tier': 'blank',
            'sort_order': len(prizes),
            'public_label': 'Без выигрыша',
            'color': '#666666',
            'icon': '😔'
        }
        
        self.create_outcome(giveaway_id, blank_data)
        
        # Enable outcome engine
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE giveaways SET use_outcome_engine = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (giveaway_id,)
        )
        conn.commit()
        conn.close()
        
        return True
    
    def _get_prize_color(self, index: int) -> str:
        """Get default color for prize index"""
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE']
        return colors[index % len(colors)]


# Global instance
db = DatabaseManager()
