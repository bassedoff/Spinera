import json
import os
import threading
import time
from typing import Dict, Any, Optional
from datetime import datetime

class Storage:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.lock = threading.Lock()
        self._ensure_storage_exists()
    
    def _ensure_storage_exists(self):
        """Create storage file with initial structure if it doesn't exist"""
        if not os.path.exists(self.storage_path):
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            initial_data = {
                "users": {},
                "post_drafts": {},
                "giveaway_drafts": {},
                "giveaways": {},
                "channels": {},
                "counters": {
                    "post_id": 0,
                    "giveaway_id": 0
                }
            }
            self._atomic_write(initial_data)
    
    def _atomic_write(self, data: Dict[Any, Any]):
        """Atomic write to storage file"""
        temp_path = f"{self.storage_path}.tmp"
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.storage_path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e
    
    def _read_storage(self) -> Dict[Any, Any]:
        """Read storage with locking"""
        with self.lock:
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                # Return empty structure if file is corrupted
                return {
                    "users": {},
                    "post_drafts": {},
                    "giveaway_drafts": {},
                    "giveaways": {},
                    "channels": {},
                    "counters": {"post_id": 0, "giveaway_id": 0}
                }
    
    def _write_storage(self, data: Dict[Any, Any]):
        """Write storage with locking"""
        with self.lock:
            self._atomic_write(data)
    
    def get_user(self, telegram_id: str) -> Optional[Dict]:
        """Get user data"""
        storage = self._read_storage()
        return storage["users"].get(str(telegram_id))
    
    def save_user(self, user_data: Dict):
        """Save user data"""
        storage = self._read_storage()
        telegram_id = str(user_data["telegram_id"])
        storage["users"][telegram_id] = user_data
        self._write_storage(storage)
    
    def save_post_draft(self, telegram_id: str, post_data: Dict) -> int:
        """Save post draft and return post ID"""
        storage = self._read_storage()
        telegram_id = str(telegram_id)
        
        # Increment counter
        storage["counters"]["post_id"] += 1
        post_id = storage["counters"]["post_id"]
        
        # Prepare post data
        post_entry = {
            "id": post_id,
            "type": post_data["type"],
            "file_id": post_data.get("file_id"),
            "text": post_data.get("text", ""),
            "created_at": datetime.now().isoformat()
        }
        
        # Save to user's drafts
        if telegram_id not in storage["post_drafts"]:
            storage["post_drafts"][telegram_id] = []
        storage["post_drafts"][telegram_id].append(post_entry)
        
        self._write_storage(storage)
        return post_id
    
    def get_user_posts(self, telegram_id: str) -> list:
        """Get user's post drafts"""
        storage = self._read_storage()
        telegram_id = str(telegram_id)
        return storage["post_drafts"].get(telegram_id, [])
    
    def save_giveaway_draft(self, telegram_id: str, step: int, draft_data: Dict):
        """Save giveaway wizard draft"""
        storage = self._read_storage()
        telegram_id = str(telegram_id)
        
        storage["giveaway_drafts"][telegram_id] = {
            "step": step,
            "draft": draft_data,
            "updated_at": datetime.now().isoformat()
        }
        
        self._write_storage(storage)
    
    def get_giveaway_draft(self, telegram_id: str) -> Optional[Dict]:
        """Get user's giveaway draft"""
        storage = self._read_storage()
        telegram_id = str(telegram_id)
        return storage["giveaway_drafts"].get(telegram_id)
    
    def create_giveaway(self, telegram_id: str, config: Dict) -> str:
        """Create new giveaway and return ID"""
        storage = self._read_storage()
        telegram_id = str(telegram_id)
        
        # Increment counter
        storage["counters"]["giveaway_id"] += 1
        giveaway_id = f"G-{storage['counters']['giveaway_id']:04d}"
        
        # Prepare giveaway data
        giveaway_entry = {
            "id": giveaway_id,
            "status": "created",
            "config": config,
            "created_at": datetime.now().isoformat()
        }
        
        # Save to user's giveaways
        if telegram_id not in storage["giveaways"]:
            storage["giveaways"][telegram_id] = []
        storage["giveaways"][telegram_id].append(giveaway_entry)
        
        self._write_storage(storage)
        return giveaway_id
    
    def get_user_giveaways(self, telegram_id: str) -> list:
        """Get user's giveaways"""
        storage = self._read_storage()
        telegram_id = str(telegram_id)
        return storage["giveaways"].get(telegram_id, [])
    
    def save_channels(self, telegram_id: str, channels: list):
        """Save user's channels"""
        storage = self._read_storage()
        telegram_id = str(telegram_id)
        storage["channels"][telegram_id] = channels
        self._write_storage(storage)
    
    def get_user_channels(self, telegram_id: str) -> list:
        """Get user's channels"""
        storage = self._read_storage()
        telegram_id = str(telegram_id)
        return storage["channels"].get(telegram_id, [])