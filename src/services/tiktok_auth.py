import aiohttp
import json
import asyncio
from typing import Optional, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TikTokAuth:
    """Handle TikTok authentication via session ID or username/password."""
    
    def __init__(self):
        self.session = None
        self.user_id = None
        self.username = None
        self.session_id = None
        self.last_auth = None
        
        # Standard TikTok headers
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://www.tiktok.com",
            "Referer": "https://www.tiktok.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }
    
    async def auth_with_session_id(self, session_id: str) -> bool:
        """
        Authenticate using TikTok session ID extracted from cookies.
        
        How to get session ID:
        1. Open TikTok in browser
        2. Open DevTools (F12)
        3. Go to Application → Cookies → www.tiktok.com
        4. Find "sessionid" cookie and copy its value
        """
        try:
            self.session_id = session_id
            cookies = aiohttp.CookieJar()
            
            async with aiohttp.ClientSession(cookie_jar=cookies) as session:
                # Set session cookie
                session.cookie_jar.update_cookies({"sessionid": session_id})
                
                # Verify session is valid
                async with session.get(
                    "https://www.tiktok.com/api/user/detail/",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "userInfo" in data:
                            user_info = data["userInfo"]["user"]
                            self.user_id = user_info.get("id")
                            self.username = user_info.get("uniqueId")
                            self.last_auth = datetime.now()
                            self.session = session
                            logger.info(f"✓ Authenticated as @{self.username}")
                            return True
                    return False
        except Exception as e:
            logger.error(f"Session ID auth failed: {e}")
            return False
    
    async def auth_with_credentials(self, username: str, password: str) -> bool:
        """
        Authenticate using username and password.
        Note: This requires proper session management and CAPTCHA handling.
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Get login page to extract tokens
                async with session.get(
                    "https://www.tiktok.com/login",
                    headers=self.headers
                ) as resp:
                    if resp.status != 200:
                        logger.error("Could not fetch login page")
                        return False
                
                # Attempt login
                login_data = {
                    "username": username,
                    "password": password,
                    "mix_mode": 1,
                }
                
                async with session.post(
                    "https://www.tiktok.com/api/auth/login/",
                    json=login_data,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("code") == 0:
                            # Extract session from cookies
                            cookies = session.cookie_jar
                            session_id = None
                            for cookie in cookies:
                                if cookie.key == "sessionid":
                                    session_id = cookie.value
                            
                            if session_id:
                                self.session_id = session_id
                                self.username = username
                                self.last_auth = datetime.now()
                                self.session = session
                                logger.info(f"✓ Authenticated as @{username}")
                                return True
                    
                    logger.error(f"Login failed: {await resp.text()}")
                    return False
        
        except Exception as e:
            logger.error(f"Credentials auth failed: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        return self.session is not None and self.user_id is not None
    
    def get_cookies(self) -> Dict:
        """Get current cookies as dict."""
        if self.session_id:
            return {"sessionid": self.session_id}
        return {}
    
    async def close(self):
        """Close session."""
        if self.session:
            await self.session.close()
