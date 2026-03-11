"""
Spinora Post Draft Service
Handles creation, validation, and management of post drafts
"""
from typing import Optional, Dict, List
from data.db_manager import db


class PostDraftService:
    """Service for managing post drafts with validation and metadata"""
    
    # Supported post types
    SUPPORTED_TYPES = {'text', 'photo', 'video', 'document'}
    
    # Telegram limits
    MAX_TEXT_LENGTH = 4096  # Telegram message limit
    MAX_CAPTION_LENGTH = 1024  # Media caption limit
    
    def validate_post_data(self, post_type: str, text: str = "", 
                          caption: str = "", file_id: str = None) -> tuple[bool, str]:
        """
        Validate post draft data
        
        Args:
            post_type: Type of post (text/photo/video/document)
            text: Text content for text posts
            caption: Caption for media posts
            file_id: Telegram file ID for media posts
            
        Returns:
            (is_valid, error_message)
        """
        # Check type
        if post_type not in self.SUPPORTED_TYPES:
            return False, f"Unsupported post type: {post_type}. Supported: {', '.join(self.SUPPORTED_TYPES)}"
        
        # Validate text posts
        if post_type == 'text':
            if not text or text.strip() == "":
                return False, "Text post cannot be empty"
            if len(text) > self.MAX_TEXT_LENGTH:
                return False, f"Text exceeds maximum length of {self.MAX_TEXT_LENGTH} characters"
        
        # Validate media posts
        elif post_type in {'photo', 'video', 'document'}:
            if not file_id:
                return False, f"Media file_id required for {post_type} post"
            
            if caption and len(caption) > self.MAX_CAPTION_LENGTH:
                return False, f"Caption exceeds maximum length of {self.MAX_CAPTION_LENGTH} characters"
        
        return True, ""
    
    def extract_media_metadata(self, media_obj: Dict) -> Dict:
        """
        Extract metadata from Telegram media object
        
        Args:
            media_obj: Telegram media object from update
            
        Returns:
            Metadata dict with standardized fields
        """
        metadata = {
            'file_size': media_obj.get('file_size'),
            'file_unique_id': media_obj.get('file_unique_id'),
            'mime_type': media_obj.get('mime_type'),
        }
        
        # Photo-specific
        if 'width' in media_obj:
            metadata['width'] = media_obj['width']
            metadata['height'] = media_obj['height']
        
        # Video-specific
        if 'duration' in media_obj:
            metadata['duration'] = media_obj['duration']
            metadata['width'] = media_obj.get('width')
            metadata['height'] = media_obj.get('height')
        
        return metadata
    
    def create_text_post(self, telegram_id: int, text: str) -> tuple[int, str]:
        """
        Create text-only post draft
        
        Args:
            telegram_id: User's Telegram ID
            text: Post text content
            
        Returns:
            (post_id, error_message)
        """
        # Validate
        is_valid, error = self.validate_post_data('text', text=text)
        if not is_valid:
            return 0, error
        
        # Create
        try:
            post_id = db.create_post_draft(
                telegram_id=telegram_id,
                post_type='text',
                text=text
            )
            return post_id, ""
        except Exception as e:
            return 0, f"Database error: {str(e)}"
    
    def create_media_post(self, telegram_id: int, post_type: str,
                         file_id: str, caption: str = "",
                         media_metadata: Dict = None) -> tuple[int, str]:
        """
        Create media post draft (photo/video/document)
        
        Args:
            telegram_id: User's Telegram ID
            post_type: Type of media (photo/video/document)
            file_id: Telegram file ID
            caption: Optional caption
            media_metadata: Optional metadata dict
            
        Returns:
            (post_id, error_message)
        """
        # Validate
        is_valid, error = self.validate_post_data(post_type, caption=caption, file_id=file_id)
        if not is_valid:
            return 0, error
        
        # Create
        try:
            post_id = db.create_post_draft(
                telegram_id=telegram_id,
                post_type=post_type,
                file_id=file_id,
                text="",  # Media posts use caption
                caption=caption,
                media_metadata=media_metadata
            )
            return post_id, ""
        except Exception as e:
            return 0, f"Database error: {str(e)}"
    
    def get_user_posts_with_summary(self, telegram_id: int) -> List[Dict]:
        """
        Get all user posts with display-friendly summary
        
        Args:
            telegram_id: User's Telegram ID
            
        Returns:
            List of post dicts with computed fields
        """
        posts = db.get_user_posts(telegram_id)
        
        # Enhance with display info
        enhanced_posts = []
        for post in posts:
            enhanced = post.copy()
            
            # Add type icon
            type_icons = {
                'text': '📝',
                'photo': '🖼️',
                'video': '🎬',
                'document': '📄'
            }
            enhanced['type_icon'] = type_icons.get(post['type'], '📄')
            
            # Add preview
            if post['type'] == 'text':
                text_preview = (post['text'][:80] + '...') if len(post['text']) > 80 else post['text']
                enhanced['preview'] = text_preview
                enhanced['character_count'] = len(post['text'])
            else:
                enhanced['preview'] = post['caption'] or '[Media without caption]'
                enhanced['has_media'] = bool(post['file_id'])
                enhanced['media_type_display'] = post['type'].capitalize()
            
            enhanced_posts.append(enhanced)
        
        return enhanced_posts
    
    def can_use_post_in_giveaway(self, post_id: int, telegram_id: int) -> tuple[bool, str]:
        """
        Check if post can be used in giveaway
        
        Args:
            post_id: Post draft ID
            telegram_id: User's Telegram ID
            
        Returns:
            (can_use, reason)
        """
        post = db.get_post_draft(post_id)
        
        if not post:
            return False, "Post not found"
        
        if post['telegram_id'] != telegram_id:
            return False, "This post does not belong to you"
        
        if post['type'] == 'text' and not post['text']:
            return False, "Text post is empty"
        
        if post['type'] in {'photo', 'video', 'document'} and not post['file_id']:
            return False, "Media post has no file"
        
        return True, ""


# Global post draft service instance
post_draft_service = PostDraftService()
