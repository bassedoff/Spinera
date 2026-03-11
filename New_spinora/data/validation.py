import re
from typing import List, Dict, Tuple

def validate_channel_identifier(identifier: str) -> Tuple[bool, str]:
    """Validate channel identifier format"""
    if not identifier:
        return False, "Channel identifier is required"
    
    # Check if it's a username format (@username)
    if identifier.startswith('@'):
        username = identifier[1:]
        if len(username) < 5 or len(username) > 32:
            return False, "Username must be 5-32 characters"
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "Username can only contain letters, numbers, and underscores"
        return True, ""
    
    # Check if it's a chat ID (negative number for channels/groups)
    try:
        chat_id = int(identifier)
        if chat_id >= 0:
            return False, "Chat ID must be negative for channels/groups"
        return True, ""
    except ValueError:
        return False, "Invalid chat ID format"

def validate_giveaway_data(data: Dict) -> Tuple[bool, List[str]]:
    """Validate giveaway creation data"""
    errors = []
    
    # Validate title
    if not data.get('title'):
        errors.append("Title is required")
    elif len(data.get('title', '')) < 3:
        errors.append("Title must be at least 3 characters")
    elif len(data.get('title', '')) > 100:
        errors.append("Title must be less than 100 characters")
    
    # Validate language
    valid_languages = ['en', 'ru', 'kz']
    if data.get('language') not in valid_languages:
        errors.append(f"Language must be one of: {', '.join(valid_languages)}")
    
    # Validate post draft ID
    if not data.get('post_draft_id'):
        errors.append("Post draft ID is required")
    
    # Validate channels
    channels = data.get('channels', [])
    if not channels:
        errors.append("At least one channel is required")
    
    # Validate prizes
    prizes = data.get('prizes', [])
    if not prizes:
        errors.append("At least one prize is required")
    
    for i, prize in enumerate(prizes):
        if not prize.get('name'):
            errors.append(f"Prize #{i+1}: Name is required")
        if not prize.get('qty') or prize['qty'] <= 0:
            errors.append(f"Prize #{i+1}: Quantity must be positive")
    
    return len(errors) == 0, errors

def validate_prize_data(prize: Dict) -> Tuple[bool, List[str]]:
    """Validate single prize data"""
    errors = []
    
    if not prize.get('name'):
        errors.append("Prize name is required")
    if not prize.get('qty') or prize['qty'] <= 0:
        errors.append("Prize quantity must be positive")
    
    return len(errors) == 0, errors

def sanitize_text(text: str) -> str:
    """Sanitize text input"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Limit length
    return text[:1000]  # Max 1000 characters

def validate_bot_permissions(channel_data: Dict) -> Tuple[bool, str]:
    """Validate that bot has required permissions in channel"""
    if not channel_data.get('bot_is_admin'):
        return False, "Bot must be admin in the channel"
    
    if not channel_data.get('bot_can_post'):
        return False, "Bot must have permission to post messages"
    
    return True, ""