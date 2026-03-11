"""
Spinora Channel Service
Handles Telegram channel connection, verification, and management
"""
import os
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from data.db_manager import db


class ChannelService:
    """Service for managing Telegram channel connections and verification"""
    
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN', '')
    
    async def get_chat_info(self, chat_id: str) -> Optional[Dict]:
        """
        Get channel information from Telegram API
        
        Args:
            chat_id: Channel username (with @) or numeric ID
            
        Returns:
            Channel info dict or None if error
            
        Telegram API: https://core.telegram.org/bots/api#getchat
        """
        if not self.bot_token:
            return None
        
        try:
            import aiohttp
            
            # Prepare chat identifier
            if chat_id.startswith('@'):
                identifier = chat_id  # Username format
            else:
                try:
                    # Numeric ID
                    chat_num = int(chat_id)
                    identifier = str(chat_num)
                except ValueError:
                    return None
            
            # Call Telegram getChat
            url = f"https://api.telegram.org/bot{self.bot_token}/getChat"
            params = {"chat_id": identifier}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    result = await response.json()
                    
                    if result.get('ok'):
                        chat_data = result['result']
                        return {
                            'chat_id': chat_data['id'],
                            'title': chat_data.get('title', ''),
                            'username': chat_data.get('username', ''),
                            'type': chat_data.get('type', 'unknown'),
                            'description': chat_data.get('description', ''),
                            'members_count': chat_data.get('members_count', 0)
                        }
                    else:
                        print(f"Telegram API error: {result}")
                        return None
                        
        except Exception as e:
            print(f"Error getting chat info: {e}")
            return None
    
    async def get_chat_member_info(self, chat_id: str, user_id: int) -> Optional[Dict]:
        """
        Get bot's membership status in a channel
        
        Args:
            chat_id: Channel identifier
            user_id: Bot's user ID (from getMe)
            
        Returns:
            Member info dict or None
            
        Telegram API: https://core.telegram.org/bots/api#getchatmember
        """
        if not self.bot_token:
            return None
        
        try:
            import aiohttp
            
            # Prepare chat identifier
            if chat_id.startswith('@'):
                identifier = chat_id
            else:
                identifier = str(chat_id)
            
            url = f"https://api.telegram.org/bot{self.bot_token}/getChatMember"
            params = {
                "chat_id": identifier,
                "user_id": user_id
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    result = await response.json()
                    
                    if result.get('ok'):
                        member_data = result['result']
                        return {
                            'status': member_data['status'],
                            'user': member_data.get('user', {}),
                            'is_anonymous': member_data.get('is_anonymous', False),
                            'can_be_edited': member_data.get('can_be_edited', False),
                            'can_post_messages': member_data.get('can_post_messages', False),
                            'can_edit_messages': member_data.get('can_edit_messages', False),
                            'can_delete_messages': member_data.get('can_delete_messages', False),
                            'can_restrict_members': member_data.get('can_restrict_members', False),
                            'can_promote_members': member_data.get('can_promote_members', False),
                            'can_change_info': member_data.get('can_change_info', False),
                            'can_invite_users': member_data.get('can_invite_users', False),
                            'can_pin_messages': member_data.get('can_pin_messages', False),
                        }
                    else:
                        print(f"Telegram API error: {result}")
                        return None
                        
        except Exception as e:
            print(f"Error getting chat member info: {e}")
            return None
    
    async def get_bot_info(self) -> Optional[Dict]:
        """
        Get bot's own information
        
        Returns:
            Bot info dict or None
            
        Telegram API: https://core.telegram.org/bots/api#getme
        """
        if not self.bot_token:
            return None
        
        try:
            import aiohttp
            
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    result = await response.json()
                    
                    if result.get('ok'):
                        user_data = result['result']
                        return {
                            'id': user_data['id'],
                            'is_bot': user_data['is_bot'],
                            'first_name': user_data.get('first_name', ''),
                            'username': user_data.get('username', ''),
                            'can_join_groups': user_data.get('can_join_groups', False),
                            'can_read_all_group_messages': user_data.get('can_read_all_group_messages', False),
                            'supports_inline_queries': user_data.get('supports_inline_queries', False),
                        }
                    else:
                        print(f"Telegram API error: {result}")
                        return None
                        
        except Exception as e:
            print(f"Error getting bot info: {e}")
            return None
    
    async def verify_channel(self, telegram_id: int, channel_identifier: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Verify channel and bot permissions
        
        Args:
            telegram_id: User's Telegram ID (channel owner)
            channel_identifier: Channel username (@channel) or ID
            
        Returns:
            (success, error_message, channel_data)
            
        Verification steps:
        1. Check channel exists
        2. Check bot is member
        3. Check bot is admin
        4. Check bot can post messages
        5. Save to database if all checks pass
        """
        # Step 1: Get channel info
        chat_info = await self.get_chat_info(channel_identifier)
        
        if not chat_info:
            return False, "Channel not found. Make sure the username is correct or the channel is public.", None
        
        # Validate channel type (should be channel or supergroup)
        if chat_info['type'] not in ['channel', 'supergroup']:
            return False, "Only channels and supergroups are supported.", None
        
        # Step 2: Get bot info to check membership
        bot_info = await self.get_bot_info()
        
        if not bot_info:
            return False, "Bot configuration error. Please contact support.", None
        
        # Step 3: Check bot membership and permissions
        member_info = await self.get_chat_member_info(str(chat_info['chat_id']), bot_info['id'])
        
        if not member_info:
            return False, "Cannot verify bot membership. Please try again.", None
        
        # Check if bot is in the channel
        if member_info['status'] == 'left':
            return False, "Bot is not a member of this channel. Please add the bot first.", None
        
        # Check if bot is admin
        if member_info['status'] != 'administrator':
            return False, "Bot must be an administrator in the channel.", None
        
        # Check if bot can post messages
        if not member_info.get('can_post_messages', False):
            return False, "Bot must have permission to post messages in the channel.", None
        
        # All checks passed - prepare channel data
        channel_data = {
            'telegram_id': telegram_id,
            'channel_id': chat_info['chat_id'],
            'title': chat_info['title'],
            'username': chat_info.get('username', ''),
            'type': chat_info['type'],
            'is_admin': True,
            'can_post': True,
            'permissions_snapshot': {
                'can_post_messages': member_info['can_post_messages'],
                'can_edit_messages': member_info.get('can_edit_messages', False),
                'can_delete_messages': member_info.get('can_delete_messages', False),
                'can_restrict_members': member_info.get('can_restrict_members', False),
                'can_promote_members': member_info.get('can_promote_members', False),
                'can_change_info': member_info.get('can_change_info', False),
                'can_invite_users': member_info.get('can_invite_users', False),
                'can_pin_messages': member_info.get('can_pin_messages', False),
            },
            'members_count': chat_info.get('members_count', 0),
            'verified_at': datetime.now().isoformat()
        }
        
        return True, "", channel_data
    
    def save_verified_channel(self, channel_data: Dict) -> int:
        """
        Save or update verified channel in database
        
        Args:
            channel_data: Verified channel information
            
        Returns:
            Channel ID
        """
        return db.resolve_and_save_channel(
            telegram_id=channel_data['telegram_id'],
            identifier=f"@{channel_data['username']}" if channel_data['username'] else str(channel_data['channel_id']),
            channel_data={
                'chat_id': channel_data['channel_id'],
                'title': channel_data['title'],
                'username': channel_data['username'],
                'bot_is_admin': channel_data['is_admin'],
                'bot_can_post': channel_data['can_post'],
                'type': channel_data['type'],
                'permissions_snapshot': channel_data['permissions_snapshot'],
                'members_count': channel_data['members_count'],
            }
        )
    
    def get_user_channels_with_status(self, telegram_id: int) -> List[Dict]:
        """
        Get all user channels with detailed status
        
        Args:
            telegram_id: User's Telegram ID
            
        Returns:
            List of channel dicts with status information
        """
        channels = db.get_user_channels(telegram_id)
        
        # Enhance with computed status fields
        enhanced_channels = []
        for ch in channels:
            enhanced = ch.copy()
            
            # Determine connection status
            if ch.get('bot_is_admin') and ch.get('bot_can_post'):
                enhanced['status'] = 'active'
                enhanced['can_use_for_giveaway'] = True
            elif ch.get('bot_is_admin'):
                enhanced['status'] = 'limited'
                enhanced['can_use_for_giveaway'] = False
            else:
                enhanced['status'] = 'inactive'
                enhanced['can_use_for_giveaway'] = False
            
            enhanced_channels.append(enhanced)
        
        return enhanced_channels
    
    async def reverify_channel(self, telegram_id: int, channel_id: int) -> Tuple[bool, str, Optional[Dict]]:
        """
        Re-verify an existing channel's permissions
        
        Args:
            telegram_id: User's Telegram ID
            channel_id: Channel's numeric ID
            
        Returns:
            (success, error_message, updated_channel_data)
        """
        # Get current channel from DB
        channels = db.get_user_channels(telegram_id)
        existing_channel = next((ch for ch in channels if ch['id'] == channel_id), None)
        
        if not existing_channel:
            return False, "Channel not found in your channels.", None
        
        # Use channel username or ID for verification
        identifier = f"@{existing_channel['username']}" if existing_channel['username'] else str(channel_id)
        
        # Run verification
        success, error_msg, channel_data = await self.verify_channel(telegram_id, identifier)
        
        if success:
            # Update existing channel
            updated_data = {
                'chat_id': channel_data['channel_id'],
                'title': channel_data['title'],
                'username': channel_data['username'],
                'bot_is_admin': channel_data['is_admin'],
                'bot_can_post': channel_data['can_post'],
                'type': channel_data['type'],
                'permissions_snapshot': channel_data['permissions_snapshot'],
                'members_count': channel_data['members_count'],
            }
            
            # Save updated channel
            db.resolve_and_save_channel(telegram_id, identifier, updated_data)
            
            return True, "", channel_data
        else:
            return False, error_msg, None


# Global channel service instance
channel_service = ChannelService()
