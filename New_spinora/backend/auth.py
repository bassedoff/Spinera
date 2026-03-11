"""
Spinora Authentication and Authorization Service
Handles Telegram Mini App auth, user context, and ownership verification
"""
import os
import hmac
import hashlib
import json
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Header

from data.db_manager import db


class AuthService:
    """Centralized authentication and authorization service"""
    
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN', '')
        self.dev_auth_bypass = os.getenv('DEV_AUTH_BYPASS', '0') == '1'
        self.dev_telegram_id = os.getenv('DEV_TELEGRAM_ID', '123456789')
        self.dev_username = os.getenv('DEV_USERNAME', 'testuser')
        self.dev_first_name = os.getenv('DEV_FIRST_NAME', 'Test')
    
    def decode_uri_component(self, s: str) -> str:
        """Decode URI component"""
        from urllib.parse import unquote
        return unquote(s.replace('+', '%20'))
    
    def validate_telegram_init_data(self, init_data: str) -> Optional[Dict]:
        """
        Validate Telegram WebApp init data signature
        
        Args:
            init_data: Raw Telegram init data string
            
        Returns:
            User dict if valid, None otherwise
            
        Security:
        - Validates HMAC-SHA256 signature using BOT_TOKEN
        - Rejects missing or malformed hash
        - Rejects expired init data (auth_hash_ttl check)
        """
        if not init_data:
            return None
        
        try:
            # Parse URL-encoded parameters
            params = {}
            for param in init_data.split('&'):
                key, value = param.split('=', 1)
                params[key] = value
            
            # Get hash and user data
            received_hash = params.get('hash')
            user_data = params.get('user')
            
            if not received_hash or not user_data:
                return None
            
            # Decode user JSON
            user_json = json.loads(self.decode_uri_component(user_data))
            
            # Skip signature validation in dev mode
            if not self.dev_auth_bypass and self.bot_token:
                # Check auth date TTL (24 hours)
                auth_date = params.get('auth_date')
                if auth_date:
                    try:
                        auth_timestamp = int(auth_date)
                        now = datetime.now().timestamp()
                        # 24 hours TTL
                        if now - auth_timestamp > 86400:
                            print(f"Auth data expired: {auth_timestamp}")
                            return None
                    except ValueError:
                        return None
                
                # Prepare data for hashing (all params except hash, sorted)
                data_check_arr = []
                for key, value in params.items():
                    if key != 'hash':
                        data_check_arr.append(f"{key}={value}")
                data_check_arr.sort()
                data_check_string = '\n'.join(data_check_arr)
                
                # Calculate HMAC-SHA256
                secret_key = hmac.new(
                    b"WebAppData",
                    self.bot_token.encode(),
                    hashlib.sha256
                ).digest()
                
                calculated_hash = hmac.new(
                    secret_key,
                    data_check_string.encode(),
                    hashlib.sha256
                ).hexdigest()
                
                # Verify hash (constant-time comparison)
                if not hmac.compare_digest(calculated_hash, received_hash):
                    print("Hash mismatch - possible tampering")
                    return None
            
            return user_json
        
        except Exception as e:
            print(f"Auth validation error: {e}")
            return None
    
    def get_current_user(self, x_telegram_init_data: Optional[str]) -> Dict:
        """
        Authenticate user from Telegram init data
        
        Args:
            x_telegram_init_data: Telegram init data from header
            
        Returns:
            Authenticated user dict
            
        Raises:
            HTTPException: 401 Unauthorized if auth fails
        """
        # Dev mode bypass
        if self.dev_auth_bypass:
            return {
                "id": int(self.dev_telegram_id),
                "username": self.dev_username,
                "first_name": self.dev_first_name,
                "last_name": "",
                "is_authenticated": True
            }
        
        # Production mode - validate init data
        if not x_telegram_init_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: No init data provided",
                headers={"WWW-Authenticate": "TelegramInitData"}
            )
        
        user_data = self.validate_telegram_init_data(x_telegram_init_data)
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: Invalid Telegram init data",
                headers={"WWW-Authenticate": "TelegramInitData"}
            )
        
        # Ensure user exists in database
        db.create_or_update_user(
            telegram_id=user_data['id'],
            username=user_data.get('username', ''),
            first_name=user_data.get('first_name', ''),
            last_name=user_data.get('last_name', '')
        )
        
        return {
            "id": user_data['id'],
            "username": user_data.get('username', ''),
            "first_name": user_data.get('first_name', ''),
            "last_name": user_data.get('last_name', ''),
            "is_authenticated": True
        }
    
    def verify_ownership(self, entity_type: str, entity_id: int, telegram_id: int) -> bool:
        """
        Verify that a user owns a specific entity
        
        Args:
            entity_type: Type of entity ('channel', 'post_draft', 'giveaway')
            entity_id: ID of the entity
            telegram_id: Telegram ID of the user to check ownership
            
        Returns:
            True if user owns the entity
            
        Raises:
            HTTPException: 403 Forbidden if not owner
            HTTPException: 404 Not Found if entity doesn't exist
        """
        if entity_type == 'channel':
            # For channels, we check by channel_id (not internal id)
            channels = db.get_user_channels(telegram_id)
            if not any(ch['id'] == entity_id for ch in channels):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You do not have access to this channel"
                )
            return True
            
        elif entity_type == 'post_draft':
            post = db.get_post_draft(entity_id)
            if not post:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Post draft not found"
                )
            if post['telegram_id'] != telegram_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This post draft does not belong to you"
                )
            return True
            
        elif entity_type == 'giveaway':
            giveaway = db.get_giveaway(entity_id)
            if not giveaway:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Giveaway not found"
                )
            if giveaway['telegram_id'] != telegram_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This giveaway does not belong to you"
                )
            return True
        
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")
    
    def get_user_channels_map(self, telegram_id: int) -> Dict[int, Dict]:
        """
        Get user's channels as a map for quick lookup
        
        Args:
            telegram_id: User's Telegram ID
            
        Returns:
            Dict mapping channel_id -> channel data
        """
        channels = db.get_user_channels(telegram_id)
        return {ch['id']: ch for ch in channels}
    
    def verify_channel_access(self, channel_id: int, telegram_id: int) -> Dict:
        """
        Verify user has access to a channel and return channel data
        
        Args:
            channel_id: Channel ID to check
            telegram_id: User's Telegram ID
            
        Returns:
            Channel data if accessible
            
        Raises:
            HTTPException: 403 if no access
        """
        channels = self.get_user_channels_map(telegram_id)
        
        if channel_id not in channels:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this channel"
            )
        
        return channels[channel_id]
    
    def can_user_create_giveaway(self, telegram_id: int, channel_ids: List[int]) -> bool:
        """
        Verify user can create giveaway on specified channels
        
        Args:
            telegram_id: User's Telegram ID
            channel_ids: List of channel IDs for giveaway
            
        Returns:
            True if user has access to all channels
            
        Raises:
            HTTPException: 403 if missing access to any channel
        """
        if not channel_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one channel is required"
            )
        
        user_channels = self.get_user_channels_map(telegram_id)
        
        for channel_id in channel_ids:
            if channel_id not in user_channels:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You do not have access to channel {channel_id}"
                )
            
            channel = user_channels[channel_id]
            if not channel.get('bot_is_admin') or not channel.get('bot_can_post'):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Bot cannot post to channel {channel_id}"
                )
        
        return True


# Global auth service instance
auth_service = AuthService()


# ============ FastAPI Dependencies ============

async def get_authenticated_user(x_telegram_init_data: Optional[str] = Header(None)) -> Dict:
    """
    FastAPI dependency for authenticated user
    
    Usage:
        @app.get("/api/protected")
        async def protected_route(user: Dict = Depends(get_authenticated_user)):
            ...
    """
    return auth_service.get_current_user(x_telegram_init_data)
