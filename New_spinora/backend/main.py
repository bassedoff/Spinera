"""
Spinora Backend API Server
FastAPI-based REST API for SpinoraBot
"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import uvicorn

from data.db_manager import db
from data.validation import (
    validate_channel_identifier, 
    validate_giveaway_data, 
    validate_bot_permissions,
    validate_prize_data,
    sanitize_text
)
from backend.auth import auth_service, get_authenticated_user
from backend.channel_service import channel_service
from backend.post_draft_service import post_draft_service

# Initialize FastAPI app
app = FastAPI(
    title="Spinora API",
    description="REST API for SpinoraBot Giveaway Platform",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
DEV_AUTH_BYPASS = os.getenv('DEV_AUTH_BYPASS', '0') == '1'

# Mount static files (Mini App frontend)
static_path = Path(__file__).parent.parent / "web" / "public"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


# ============ Pydantic Models ============

class ChannelResolveRequest(BaseModel):
    identifier: str

class PostCreateRequest(BaseModel):
    type: str
    file_id: Optional[str] = None
    text: Optional[str] = ""

class PrizeCreateRequest(BaseModel):
    name: str
    qty: int
    description: Optional[str] = ""
    weight: Optional[int] = 1

class GiveawayCreateRequest(BaseModel):
    title: str
    language: Optional[str] = "en"
    post_draft_id: int
    channels: List[int]
    prizes: List[PrizeCreateRequest]

class WizardDraftRequest(BaseModel):
    step: int
    draft: Dict[str, Any]

class TelegramUser(BaseModel):
    id: int
    username: Optional[str] = ""
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""


# ============ Authentication ============

# Auth functions moved to backend/auth.py
# Using centralized auth service for better security and maintainability


# ============ API Routes ============

@app.get("/")
async def root():
    """Serve Mini App frontend"""
    from fastapi.responses import FileResponse
    return FileResponse(static_path / "index.html")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"ok": True, "status": "running"}

@app.get("/api/me")
async def get_me(current_user: Dict = Depends(get_authenticated_user)):
    """Get current user information"""
    user = db.get_user(current_user['id'])
    
    if not user:
        # Create user if doesn't exist
        db.create_or_update_user(
            telegram_id=current_user['id'],
            username=current_user.get('username', ''),
            first_name=current_user.get('first_name', ''),
            last_name=current_user.get('last_name', '')
        )
        user = db.get_user(current_user['id'])
    
    return user

@app.get("/api/posts")
async def get_posts(
    scope: Optional[str] = "drafts",
    current_user: Dict = Depends(get_authenticated_user)
):
    """Get user's post drafts"""
    telegram_id = current_user['id']
    
    if scope == "drafts":
        posts = db.get_user_posts(telegram_id)
        return posts
    
    return []

@app.post("/api/posts")
async def create_post(
    post_data: PostCreateRequest,
    current_user: Dict = Depends(get_authenticated_user)
):
    """Create a new post draft"""
    telegram_id = current_user['id']
    
    try:
        post_id = db.create_post_draft(
            telegram_id=telegram_id,
            post_type=post_data.type,
            file_id=post_data.file_id,
            text=post_data.text or ""
        )
        
        return {"id": post_id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create post: {str(e)}")

@app.get("/api/channels")
async def get_channels(current_user: Dict = Depends(get_authenticated_user)):
    """Get user's connected channels with status"""
    telegram_id = current_user['id']
    
    try:
        channels = channel_service.get_user_channels_with_status(telegram_id)
        return channels
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get channels: {str(e)}")

@app.post("/api/channels/connect/initiate")
async def initiate_channel_connect(
    request: ChannelResolveRequest,
    current_user: Dict = Depends(get_authenticated_user)
):
    """
    Initiate channel connection flow
    Returns instructions and deep link for adding bot to channel
    """
    telegram_id = current_user['id']
    identifier = request.identifier
    
    # Validate identifier format
    is_valid, error_msg = validate_channel_identifier(identifier)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    try:
        # Get bot username for deep link
        bot_info = await channel_service.get_bot_info()
        
        if not bot_info:
            raise HTTPException(status_code=500, detail="Bot configuration error")
        
        bot_username = bot_info['username']
        
        # Prepare instructions
        instructions = {
            "step": 1,
            "action": "add_bot_to_channel",
            "channel": identifier,
            "bot_username": bot_username,
            "deep_link": f"https://t.me/{bot_username}?startgroup=true",
            "required_rights": [
                "Post messages",
                "Edit messages",
                "Delete messages",
                "Pin messages"
            ],
            "instructions": [
                f"Click the button to add @{bot_username} to your channel",
                "Select your channel from the list",
                "Grant administrator rights to the bot",
                "Ensure bot has permission to post messages",
                "Return to this page and click 'Verify Connection'"
            ]
        }
        
        return instructions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate connection: {str(e)}")

@app.post("/api/channels/connect/verify")
async def verify_channel_connection(
    request: ChannelResolveRequest,
    current_user: Dict = Depends(get_authenticated_user)
):
    """
    Verify channel connection after bot has been added
    Performs full verification of bot permissions in channel
    """
    telegram_id = current_user['id']
    identifier = request.identifier
    
    # Validate identifier format
    is_valid, error_msg = validate_channel_identifier(identifier)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    try:
        # Perform comprehensive verification
        success, error_message, channel_data = await channel_service.verify_channel(
            telegram_id, identifier
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=error_message)
        
        # Save verified channel to database
        channel_id = channel_service.save_verified_channel(channel_data)
        
        # Return channel info
        return {
            "success": True,
            "channel_id": channel_id,
            "channel": channel_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

@app.post("/api/channels/{channel_id}/reverify")
async def reverify_channel(
    channel_id: int,
    current_user: Dict = Depends(get_authenticated_user)
):
    """
    Re-verify an existing channel's permissions
    Use when bot permissions might have changed
    """
    telegram_id = current_user['id']
    
    try:
        success, error_message, updated_data = await channel_service.reverify_channel(
            telegram_id, channel_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=error_message)
        
        return {
            "success": True,
            "channel": updated_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Re-verification failed: {str(e)}")

@app.post("/api/channels/resolve")
async def resolve_channel(
    request: ChannelResolveRequest,
    current_user: Dict = Depends(get_authenticated_user)
):
    """
    [LEGACY] Resolve channel identifier - DEPRECATED
    Use /api/channels/connect/initiate and /api/channels/connect/verify instead
    """
    telegram_id = current_user['id']
    identifier = request.identifier
    
    # Validate identifier format
    is_valid, error_msg = validate_channel_identifier(identifier)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    try:
        # In dev mode only, simulate channel resolution
        if DEV_AUTH_BYPASS:
            mock_channel = {
                "chat_id": -1001234567890,
                "title": f"Channel {identifier}",
                "username": identifier.lstrip('@'),
                "bot_is_admin": True,
                "bot_can_post": True
            }
            
            saved_channel = db.resolve_and_save_channel(
                telegram_id=telegram_id,
                identifier=identifier,
                channel_data=mock_channel
            )
            
            return saved_channel
        
        # TODO: Implement real Telegram API calls for production
        raise HTTPException(
            status_code=501,
            detail="Channel resolution not implemented in production mode yet"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve channel: {str(e)}")

@app.get("/api/wizard/draft")
async def get_wizard_draft(current_user: Dict = Depends(get_current_user)):
    """Get user's giveaway wizard draft"""
    # For now, return empty draft
    # Can be implemented with session-based storage if needed
    return {}

@app.post("/api/wizard/draft")
async def save_wizard_draft(
    request: WizardDraftRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Save wizard draft (placeholder)"""
    # Placeholder - can be implemented later if needed
    return {"success": True}

@app.post("/api/wizard/commit")
async def commit_giveaway(
    giveaway_data: GiveawayCreateRequest,
    current_user: Dict = Depends(get_authenticated_user)
):
    """Create finalized giveaway from wizard"""
    telegram_id = current_user['id']
    
    # Convert Pydantic model to dict
    data_dict = giveaway_data.dict()
    
    # Validate giveaway data
    is_valid, errors = validate_giveaway_data(data_dict)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Validation failed", headers={"X-Validation-Errors": json.dumps(errors)})
    
    # TRUST BOUNDARY: Verify user owns all channels
    try:
        auth_service.can_user_create_giveaway(telegram_id, giveaway_data.channels)
    except HTTPException as e:
        raise e
    
    # TRUST BOUNDARY: Verify user owns the post draft
    try:
        auth_service.verify_ownership('post_draft', giveaway_data.post_draft_id, telegram_id)
    except HTTPException as e:
        raise e
    
    try:
        # Create giveaway in database
        giveaway_id = db.create_giveaway(
            telegram_id=telegram_id,
            title=giveaway_data.title,
            language=giveaway_data.language,
            post_draft_id=giveaway_data.post_draft_id,
            channels=giveaway_data.channels,
            prizes=[prize.dict() for prize in giveaway_data.prizes]
        )
        
        return {"giveaway_id": giveaway_id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create giveaway: {str(e)}")

@app.get("/api/giveaways")
async def get_giveaways(
    scope: Optional[str] = "created",
    current_user: Dict = Depends(get_authenticated_user)
):
    """Get user's giveaways"""
    telegram_id = current_user['id']
    
    if scope == "created":
        giveaways = db.get_user_giveaways(telegram_id)
        return giveaways
    
    return []

@app.get("/api/giveaways/{giveaway_id}")
async def get_giveaway(giveaway_id: int, current_user: Dict = Depends(get_authenticated_user)):
    """Get specific giveaway by ID"""
    telegram_id = current_user['id']
    
    giveaway = db.get_giveaway(giveaway_id)
    
    if not giveaway:
        raise HTTPException(status_code=404, detail="Giveaway not found")
    
    # TRUST BOUNDARY: Check ownership
    if giveaway['telegram_id'] != telegram_id:
        raise HTTPException(status_code=403, detail="Access denied: This giveaway does not belong to you")
    
    return giveaway


# ============ Error Handlers ============

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Not found"}

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return {"error": "Internal server error"}


# ============ Main Entry Point ============

if __name__ == "__main__":
    # Initialize database
    from data.db_init import init_database
    init_database()
    
    # Start server
    port = int(os.getenv('PORT', 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
