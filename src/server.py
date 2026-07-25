import os
import json
import asyncio
from typing import Optional, List
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import logging

from services.groq_service import GroqService
from services.tiktok_service import TikTokService
from services.distortion_service import DistortionService
from services.language_processor import LanguageProcessor

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown."""
    logger.info("🚀 StillAliveGhost server starting...")
    yield
    logger.info("🛑 Server shutting down...")

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

groq_service = GroqService(api_key=os.getenv("GROQ_API_KEY"))
tiktok_service = TikTokService()
distortion_service = DistortionService()

# Global bot state
bot_state = {
    "authenticated": False,
    "running": False,
    "creature_name": "Существо",
    "language": "ru",
    "font_mode": "normal",
    "targets": [],  # List of target usernames
    "target_styles": {},  # {username: style_dict}
    "who_count": {},  # Track "Who are you?" questions per user
    "conversation_history": {},  # {target: [messages]}
    "comment_mode": True,
    "dm_mode": True,
}

active_connections = []


class ConnectionRequest(BaseModel):
    session_id: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    auth_method: str = "session"  # "session" or "credentials"


class BotSettingsRequest(BaseModel):
    creature_name: str
    language: str  # "ru" or "en"
    font_mode: str  # "normal" or "distorted"
    comment_mode: bool
    dm_mode: bool


class TargetRequest(BaseModel):
    usernames: List[str]  # Multiple targets


class ControlRequest(BaseModel):
    action: str  # "start" or "stop"


async def broadcast_log(message: str):
    """Send log to all WebSocket clients."""
    for connection in active_connections:
        try:
            await connection.send_json({"type": "log", "message": message})
        except:
            pass


@app.post("/api/connect")
async def connect_tiktok(request: ConnectionRequest):
    """Authenticate with TikTok via session ID or credentials."""
    try:
        if request.auth_method == "session":
            if not request.session_id:
                raise HTTPException(status_code=400, detail="Session ID required")
            success = await tiktok_service.connect_with_session_id(request.session_id)
        else:
            if not request.username or not request.password:
                raise HTTPException(status_code=400, detail="Username and password required")
            success = await tiktok_service.connect_with_credentials(
                request.username, request.password
            )
        
        if not success:
            raise HTTPException(status_code=401, detail="Authentication failed")
        
        bot_state["authenticated"] = True
        await broadcast_log("✓ Connected to TikTok")
        return {
            "status": "connected",
            "username": tiktok_service.auth.username
        }
    except Exception as e:
        logger.error(f"Connection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/settings")
async def update_settings(request: BotSettingsRequest):
    """Update bot personality and language settings."""
    bot_state["creature_name"] = request.creature_name
    bot_state["language"] = request.language
    bot_state["font_mode"] = request.font_mode
    bot_state["comment_mode"] = request.comment_mode
    bot_state["dm_mode"] = request.dm_mode
    
    await broadcast_log(
        f"⚙ Bot: {request.creature_name} | "
        f"Lang: {request.language} | "
        f"Font: {request.font_mode}"
    )
    return {"status": "updated"}


@app.post("/api/targets")
async def set_targets(request: TargetRequest):
    """Set multiple target users."""
    if not bot_state["authenticated"]:
        raise HTTPException(status_code=400, detail="Not authenticated")
    
    for username in request.usernames:
        followed = await tiktok_service.follow_user(username)
        if followed:
            bot_state["targets"].append(username)
            bot_state["conversation_history"][username] = []
            bot_state["who_count"][username] = 0
            await broadcast_log(f"👁 Targeting: @{username}")
        else:
            await broadcast_log(f"⚠ Failed to follow @{username}")
    
    return {"status": "targets_set", "targets": bot_state["targets"]}


@app.post("/api/control")
async def control_bot(request: ControlRequest):
    """Start or stop the bot."""
    if not bot_state["authenticated"]:
        raise HTTPException(status_code=400, detail="Not authenticated")
    
    if not bot_state["targets"]:
        raise HTTPException(status_code=400, detail="No targets set")
    
    if request.action == "start":
        bot_state["running"] = True
        await broadcast_log("🔴 HUNTING STARTED")
        asyncio.create_task(hunting_loop())
        return {"status": "hunting"}
    elif request.action == "stop":
        bot_state["running"] = False
        await broadcast_log("⚫ HUNTING STOPPED")
        return {"status": "stopped"}
    
    raise HTTPException(status_code=400, detail="Invalid action")


async def hunting_loop():
    """Main bot loop monitoring all targets."""
    while bot_state["running"]:
        try:
            for target in bot_state["targets"]:
                if not bot_state["running"]:
                    break
                
                # Scan for new videos
                if bot_state["comment_mode"]:
                    videos = await tiktok_service.get_user_videos(target, limit=3)
                    for video in videos:
                        comments, _ = await tiktok_service.get_video_comments(video["id"], limit=5)
                        
                        for comment in comments:
                            # Analyze target's writing style
                            style = LanguageProcessor(bot_state["language"]).analyze_style(comment["text"])
                            bot_state["target_styles"][target] = style
                            
                            # Generate response
                            context = f"{comment['author']}: {comment['text']}"
                            response = await groq_service.generate_response(
                                context=context,
                                creature_name=bot_state["creature_name"],
                                language=bot_state["language"],
                                target_style=style,
                                conversation_history=bot_state["conversation_history"].get(target, [])
                            )
                            
                            # Apply distortion if enabled
                            if bot_state["font_mode"] == "distorted":
                                response = distortion_service.full_distortion(response, bot_state["language"])
                            
                            # Sometimes copy and distort original text
                            if comment["text"] and len(comment["text"]) > 10:
                                import random
                                if random.random() < 0.3:
                                    distorted_copy = distortion_service.copy_with_distortion(
                                        comment["text"][:50],
                                        bot_state["language"]
                                    )
                                    response = f"{distorted_copy}\n{response}"
                            
                            # Post comment
                            posted = await tiktok_service.post_comment(video["id"], response)
                            if posted:
                                await broadcast_log(f"💬 @{target}: {response[:50]}...")
                                
                                # Update history
                                if target not in bot_state["conversation_history"]:
                                    bot_state["conversation_history"][target] = []
                                bot_state["conversation_history"][target].append({
                                    "role": "assistant",
                                    "content": response
                                })
                            
                            await asyncio.sleep(2)
                
                # Check DMs if enabled
                if bot_state["dm_mode"]:
                    user_info = await tiktok_service.get_user_info(target)
                    if user_info:
                        user_id = user_info.get("id")
                        messages = await tiktok_service.get_direct_messages(user_id, limit=5)
                        
                        for msg in messages:
                            # Skip own messages
                            if msg.get("sender_id") == tiktok_service.auth.user_id:
                                continue
                            
                            # Check if asked "Who are you?"
                            msg_text = msg.get("content", "").lower()
                            if "кто ты" in msg_text or "who are you" in msg_text.lower():
                                bot_state["who_count"][target] = bot_state["who_count"].get(target, 0) + 1
                            
                            # Generate response
                            response = await groq_service.generate_response(
                                context=msg.get("content", ""),
                                creature_name=bot_state["creature_name"],
                                language=bot_state["language"],
                                conversation_history=bot_state["conversation_history"].get(target, [])
                            )
                            
                            # Add name if asked twice
                            if bot_state["who_count"].get(target, 0) >= 2:
                                response = f"{bot_state['creature_name']}"
                                bot_state["who_count"][target] = 0  # Reset counter
                            
                            if bot_state["font_mode"] == "distorted":
                                response = distortion_service.full_distortion(response, bot_state["language"])
                            
                            # Send DM
                            sent = await tiktok_service.send_direct_message(user_id, response)
                            if sent:
                                await broadcast_log(f"📨 DM to @{target}: {response[:50]}...")
                            
                            await asyncio.sleep(3)
                
                await asyncio.sleep(10)
            
            await asyncio.sleep(30)
        except Exception as e:
            await broadcast_log(f"⚠ Error: {e}")
            await asyncio.sleep(10)


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket for real-time logs."""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            await websocket.receive_text()
    except:
        pass
    finally:
        active_connections.remove(websocket)


@app.get("/api/status")
async def get_status():
    """Get current bot state."""
    return {
        "authenticated": bot_state["authenticated"],
        "running": bot_state["running"],
        "targets": bot_state["targets"],
        "creature_name": bot_state["creature_name"],
        "language": bot_state["language"],
        "font_mode": bot_state["font_mode"],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
