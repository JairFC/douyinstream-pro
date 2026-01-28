"""
DouyinStream Pro v2 - Centralized Cookie Manager
Singleton pattern for managing all Douyin authentication cookies.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Optional
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

# Cookie file location
DATA_DIR = Path(__file__).parent.parent / "data"
COOKIES_FILE = DATA_DIR / "douyin_cookies.json"


class CookieManager:
    """
    Centralized cookie management for all Douyin requests.
    Ensures all modules share the same authentication state.
    """
    
    # Singleton
    _instance: Optional["CookieManager"] = None
    
    def __new__(cls) -> "CookieManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._cookies: Dict[str, str] = {}
        self._last_updated: Optional[float] = None
        self._lock = asyncio.Lock()
        
        # Ensure data directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    async def load_cookies(self) -> Dict[str, str]:
        """Load cookies from file or extract from browser."""
        async with self._lock:
            # Try file first
            if COOKIES_FILE.exists():
                try:
                    with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    saved_at = data.get('saved_at', 0)
                    age_hours = (time.time() - saved_at) / 3600
                    
                    # Valid for 24 hours
                    if age_hours < 24:
                        self._cookies = data.get('cookies', {})
                        self._last_updated = saved_at
                        logger.info(f"✅ Loaded {len(self._cookies)} cookies from file (age: {age_hours:.1f}h)")
                        return self._cookies
                    else:
                        logger.warning(f"⚠️ Cookies expired ({age_hours:.1f}h > 24h)")
                except Exception as e:
                    logger.error(f"Error loading cookies: {e}")
            
            # Try browser extraction
            await self._extract_from_browser()
            return self._cookies
    
    async def _extract_from_browser(self) -> None:
        """Extract cookies from browser (runs in thread pool)."""
        loop = asyncio.get_event_loop()
        try:
            cookies = await loop.run_in_executor(None, self._sync_extract_browser)
            if cookies:
                self._cookies = cookies
                self._last_updated = time.time()
                await self.save_cookies()
        except Exception as e:
            logger.warning(f"Browser cookie extraction failed: {e}")
    
    def _sync_extract_browser(self) -> Dict[str, str]:
        """Synchronous browser cookie extraction."""
        cookies = {}
        
        try:
            import browser_cookie3
            
            # Try browsers in order
            browsers = [
                ('Chrome', browser_cookie3.chrome),
                ('Edge', browser_cookie3.edge),
                ('Firefox', browser_cookie3.firefox),
            ]
            
            for name, browser_func in browsers:
                try:
                    cj = browser_func(domain_name='.douyin.com')
                    for c in cj:
                        cookies[c.name] = c.value
                    
                    if cookies:
                        logger.info(f"✅ Extracted {len(cookies)} cookies from {name}")
                        break
                except Exception as e:
                    logger.debug(f"{name} extraction failed: {e}")
                    continue
        except ImportError:
            logger.warning("browser-cookie3 not installed")
        
        return cookies
    
    async def save_cookies(self) -> None:
        """Persist cookies to file."""
        async with self._lock:
            try:
                with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
                    json.dump({
                        'cookies': self._cookies,
                        'saved_at': time.time(),
                        'saved_at_str': datetime.now().isoformat()
                    }, f, indent=2)
                logger.info(f"💾 Saved {len(self._cookies)} cookies to file")
            except Exception as e:
                logger.error(f"Error saving cookies: {e}")
    
    async def update_cookies(self, new_cookies: Dict[str, str]) -> None:
        """Update cookies with new values (e.g., after CAPTCHA resolution)."""
        async with self._lock:
            self._cookies.update(new_cookies)
            self._last_updated = time.time()
        await self.save_cookies()
        logger.info(f"🔄 Updated cookies: {len(new_cookies)} new, {len(self._cookies)} total")
    
    def get_cookies(self) -> Dict[str, str]:
        """Get current cookies (thread-safe read)."""
        return self._cookies.copy()
    
    def get_cookie_header(self) -> str:
        """Get cookies formatted for HTTP header."""
        return "; ".join(f"{k}={v}" for k, v in self._cookies.items())
    
    def has_valid_cookies(self) -> bool:
        """Check if we have potentially valid cookies."""
        if not self._cookies:
            return False
        
        # Check for important Douyin cookies
        important = ['ttwid', '__ac_nonce', 'sessionid', 'sid_guard']
        has_important = any(name in self._cookies for name in important)
        
        return has_important
    
    def get_age_hours(self) -> Optional[float]:
        """Get cookie age in hours."""
        if self._last_updated:
            return (time.time() - self._last_updated) / 3600
        return None
    
    def clear(self) -> None:
        """Clear all cookies."""
        self._cookies.clear()
        self._last_updated = None
        if COOKIES_FILE.exists():
            COOKIES_FILE.unlink()
        logger.info("🗑️ Cookies cleared")
