import aiohttp
import asyncio
import logging
from typing import List, Optional, Dict, Tuple
from .tiktok_auth import TikTokAuth

logger = logging.getLogger(__name__)


class TikTokService:
    """Complete TikTok API integration with real endpoints."""
    
    def __init__(self):
        self.auth = TikTokAuth()
        self.headers = self.auth.headers.copy()
        self.base_url = "https://www.tiktok.com/api"
        self.targets = {}  # {username: {id, last_video_id, conversation_ids}}
        self.session = None
    
    async def init_session(self):
        """Initialize HTTP session."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def connect_with_session_id(self, session_id: str) -> bool:
        """Connect using session ID."""
        await self.init_session()
        success = await self.auth.auth_with_session_id(session_id)
        if success:
            self.session = self.auth.session
        return success
    
    async def connect_with_credentials(self, username: str, password: str) -> bool:
        """Connect using username and password."""
        await self.init_session()
        success = await self.auth.auth_with_credentials(username, password)
        if success:
            self.session = self.auth.session
        return success
    
    async def get_user_info(self, username: str) -> Optional[Dict]:
        """Get user info by username."""
        if not self.session:
            return None
        
        try:
            url = f"{self.base_url}/user/detail/"
            params = {"uniqueId": username}
            
            async with self.session.get(
                url,
                params=params,
                headers=self.headers,
                cookies=self.auth.get_cookies(),
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "userInfo" in data:
                        return data["userInfo"]["user"]
        except Exception as e:
            logger.error(f"Error getting user info for @{username}: {e}")
        
        return None
    
    async def follow_user(self, username: str) -> bool:
        """Follow a user."""
        if not self.session or not self.auth.is_authenticated():
            logger.error("Not authenticated")
            return False
        
        try:
            user_info = await self.get_user_info(username)
            if not user_info:
                logger.error(f"Could not find user @{username}")
                return False
            
            user_id = user_info.get("id")
            
            url = f"{self.base_url}/user/follow/"
            payload = {"userId": user_id, "action": 1}
            
            async with self.session.post(
                url,
                json=payload,
                headers=self.headers,
                cookies=self.auth.get_cookies(),
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("code") == 0:
                        logger.info(f"✓ Followed @{username}")
                        # Store target info
                        self.targets[username] = {
                            "id": user_id,
                            "last_video_id": None,
                            "last_comment_ids": set()
                        }
                        return True
        except Exception as e:
            logger.error(f"Error following @{username}: {e}")
        
        return False
    
    async def get_user_videos(self, username: str, limit: int = 5) -> List[Dict]:
        """Get recent videos from target user."""
        if not self.session:
            return []
        
        try:
            user_info = await self.get_user_info(username)
            if not user_info:
                return []
            
            user_id = user_info.get("id")
            
            url = f"{self.base_url}/user/posts/"
            params = {"userId": user_id, "count": limit}
            
            async with self.session.get(
                url,
                params=params,
                headers=self.headers,
                cookies=self.auth.get_cookies(),
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "itemList" in data:
                        videos = []
                        for item in data["itemList"]:
                            video = item.get("video", {})
                            videos.append({
                                "id": video.get("id"),
                                "desc": item.get("desc"),
                                "created_at": item.get("createTime"),
                                "stats": item.get("stats", {}),
                            })
                        return videos
        except Exception as e:
            logger.error(f"Error getting videos for @{username}: {e}")
        
        return []
    
    async def get_video_comments(self, video_id: str, limit: int = 10, cursor: str = "") -> Tuple[List[Dict], str]:
        """Get comments on a video. Returns (comments, next_cursor)."""
        if not self.session:
            return [], ""
        
        try:
            url = f"{self.base_url}/comment/list/"
            params = {
                "aweme_id": video_id,
                "count": limit,
                "cursor": cursor
            }
            
            async with self.session.get(
                url,
                params=params,
                headers=self.headers,
                cookies=self.auth.get_cookies(),
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "comments" in data:
                        comments = []
                        for comment in data["comments"]:
                            comments.append({
                                "id": comment.get("cid"),
                                "author": comment.get("user", {}).get("nickname", "Anonymous"),
                                "author_id": comment.get("user", {}).get("uid"),
                                "text": comment.get("text"),
                                "created_at": comment.get("create_time"),
                                "reply_count": comment.get("reply_comment_total", 0)
                            })
                        next_cursor = data.get("cursor", "")
                        return comments, next_cursor
        except Exception as e:
            logger.error(f"Error getting comments for video {video_id}: {e}")
        
        return [], ""
    
    async def post_comment(self, video_id: str, text: str) -> bool:
        """Post a comment on a video."""
        if not self.session or not self.auth.is_authenticated():
            return False
        
        try:
            url = f"{self.base_url}/comment/publish/"
            payload = {
                "aweme_id": video_id,
                "text": text,
                "reply_comment_id": "",
            }
            
            async with self.session.post(
                url,
                json=payload,
                headers=self.headers,
                cookies=self.auth.get_cookies(),
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("code") == 0:
                        logger.info(f"✓ Posted comment: {text[:50]}...")
                        return True
        except Exception as e:
            logger.error(f"Error posting comment: {e}")
        
        return False
    
    async def reply_to_comment(self, video_id: str, comment_id: str, text: str) -> bool:
        """Reply to a specific comment."""
        if not self.session or not self.auth.is_authenticated():
            return False
        
        try:
            url = f"{self.base_url}/comment/publish/"
            payload = {
                "aweme_id": video_id,
                "text": text,
                "reply_comment_id": comment_id,
            }
            
            async with self.session.post(
                url,
                json=payload,
                headers=self.headers,
                cookies=self.auth.get_cookies(),
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("code") == 0:
                        logger.info(f"✓ Replied to comment: {text[:50]}...")
                        return True
        except Exception as e:
            logger.error(f"Error replying to comment: {e}")
        
        return False
    
    async def send_direct_message(self, user_id: str, text: str) -> bool:
        """Send a direct message to a user."""
        if not self.session or not self.auth.is_authenticated():
            return False
        
        try:
            url = f"{self.base_url}/message/send/"
            payload = {
                "receiver_user_id": user_id,
                "content": text,
            }
            
            async with self.session.post(
                url,
                json=payload,
                headers=self.headers,
                cookies=self.auth.get_cookies(),
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("code") == 0:
                        logger.info(f"✓ Sent DM: {text[:50]}...")
                        return True
        except Exception as e:
            logger.error(f"Error sending DM: {e}")
        
        return False
    
    async def get_direct_messages(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get DM conversation with a user."""
        if not self.session or not self.auth.is_authenticated():
            return []
        
        try:
            url = f"{self.base_url}/message/conversation/{user_id}/"
            params = {"limit": limit}
            
            async with self.session.get(
                url,
                params=params,
                headers=self.headers,
                cookies=self.auth.get_cookies(),
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "messages" in data:
                        return data["messages"]
        except Exception as e:
            logger.error(f"Error getting DMs: {e}")
        
        return []
    
    async def close(self):
        """Close session."""
        if self.session:
            await self.session.close()
