"""
DouyinStream Pro v2 - Live Status Checker
Background service that checks stream status using shared cookies.
"""

import asyncio
import logging
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import time

from .cookie_manager import CookieManager
from .douyin_extractor import DouyinExtractor

logger = logging.getLogger(__name__)


@dataclass
class StreamStatus:
    """Status of a monitored stream."""
    url: str
    is_live: Optional[bool] = None  # None = unknown/checking
    last_checked: Optional[float] = None
    title: Optional[str] = None
    author: Optional[str] = None
    error: Optional[str] = None


class LiveChecker:
    """
    Background service for checking stream live status.
    Uses DouyinExtractor with shared CookieManager.
    """
    
    CHECK_INTERVAL = 300  # 5 minutes between full checks
    STAGGER_DELAY = 2     # 2 seconds between individual checks
    
    def __init__(self, cookie_manager: CookieManager, ws_manager=None):
        self.cookie_manager = cookie_manager
        self.ws_manager = ws_manager
        self._extractor: Optional[DouyinExtractor] = None
        
        self._statuses: Dict[str, StreamStatus] = {}
        self._urls_to_check: List[str] = []
        self._running = False
        self._paused = False
        self._task: Optional[asyncio.Task] = None
    
    async def _get_extractor(self) -> DouyinExtractor:
        if self._extractor is None:
            self._extractor = DouyinExtractor(self.cookie_manager)
        return self._extractor
    
    async def start(self) -> None:
        """Start background checking."""
        if self._running:
            return
        
        self._running = True
        self._paused = False
        self._task = asyncio.create_task(self._check_loop())
        logger.info("▶️ LiveChecker started")
        
        if self.ws_manager:
            await self.ws_manager.log("LiveChecker started", "INFO", "live_checker")
    
    async def stop(self) -> None:
        """Stop background checking."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        if self._extractor:
            await self._extractor.close()
            self._extractor = None
        
        logger.info("⏹️ LiveChecker stopped")
    
    async def pause(self) -> None:
        """Pause checking (for gaming mode)."""
        self._paused = True
        logger.info("⏸️ LiveChecker paused")
        
        if self.ws_manager:
            await self.ws_manager.log("LiveChecker paused for gaming", "INFO", "live_checker")
    
    async def resume(self) -> None:
        """Resume checking."""
        self._paused = False
        logger.info("▶️ LiveChecker resumed")
        
        if self.ws_manager:
            await self.ws_manager.log("LiveChecker resumed", "INFO", "live_checker")
    
    def is_paused(self) -> bool:
        return self._paused
    
    def set_urls(self, urls: List[str]) -> None:
        """Set list of URLs to monitor."""
        self._urls_to_check = urls.copy()
        logger.info(f"📋 Monitoring {len(urls)} URLs")
    
    def add_url(self, url: str) -> None:
        """Add URL to monitoring list."""
        if url not in self._urls_to_check:
            self._urls_to_check.append(url)
            self._statuses[url] = StreamStatus(url=url)
    
    def remove_url(self, url: str) -> None:
        """Remove URL from monitoring."""
        if url in self._urls_to_check:
            self._urls_to_check.remove(url)
        if url in self._statuses:
            del self._statuses[url]
    
    def get_status(self, url: str) -> Optional[StreamStatus]:
        """Get cached status for URL."""
        return self._statuses.get(url)
    
    def get_all_statuses(self) -> Dict[str, StreamStatus]:
        """Get all cached statuses."""
        return self._statuses.copy()
    
    def get_live_streams(self) -> List[str]:
        """Get list of currently live stream URLs."""
        return [url for url, status in self._statuses.items() 
                if status.is_live is True]
    
    async def check_now(self, url: str) -> StreamStatus:
        """Check a single URL immediately."""
        extractor = await self._get_extractor()
        status = StreamStatus(url=url)
        
        try:
            is_live = await extractor.check_live_status(url)
            status.is_live = is_live
            status.last_checked = time.time()
            
            if is_live:
                # Get full info for live streams
                result = await extractor.extract_stream(url)
                if result and not result.get('error'):
                    status.title = result.get('title')
                    status.author = result.get('author')
            
        except Exception as e:
            status.error = str(e)
            logger.error(f"Check failed for {url}: {e}")
        
        self._statuses[url] = status
        
        # Notify via WebSocket
        if self.ws_manager:
            await self.ws_manager.status_update(
                url, 
                "live" if status.is_live else "offline" if status.is_live is False else "unknown",
                {"title": status.title, "author": status.author}
            )
        
        return status
    
    async def _check_loop(self) -> None:
        """Background loop for periodic checking."""
        while self._running:
            # Skip if paused
            if self._paused:
                await asyncio.sleep(5)
                continue
            
            urls = self._urls_to_check.copy()
            
            for url in urls:
                if not self._running or self._paused:
                    break
                
                try:
                    old_status = self._statuses.get(url)
                    new_status = await self.check_now(url)
                    
                    # Notify on status change
                    if old_status and old_status.is_live != new_status.is_live:
                        await self._notify_status_change(url, new_status)
                    
                except Exception as e:
                    logger.error(f"Error checking {url}: {e}")
                
                # Stagger checks to avoid rate limiting
                await asyncio.sleep(self.STAGGER_DELAY)
            
            # Wait for next interval
            for _ in range(self.CHECK_INTERVAL):
                if not self._running:
                    break
                await asyncio.sleep(1)
    
    async def _notify_status_change(self, url: str, status: StreamStatus) -> None:
        """Notify about status change."""
        if status.is_live:
            msg = f"🟢 Stream is LIVE: {status.title or url}"
        else:
            msg = f"⚫ Stream went OFFLINE: {url}"
        
        logger.info(msg)
        
        if self.ws_manager:
            await self.ws_manager.stream_event(
                "status_change",
                {
                    "url": url,
                    "is_live": status.is_live,
                    "title": status.title,
                    "author": status.author
                }
            )
    
    async def find_next_live(self, exclude_url: str = None) -> Optional[str]:
        """
        Find the next live stream from favorites (for auto-switch).
        
        Args:
            exclude_url: URL to exclude (current stream that ended)
        
        Returns:
            URL of next live stream, or None
        """
        for url, status in self._statuses.items():
            if url == exclude_url:
                continue
            if status.is_live is True:
                return url
        
        # No cached live found, do fresh check
        logger.info("🔍 No cached live streams, checking favorites...")
        
        for url in self._urls_to_check:
            if url == exclude_url:
                continue
            
            status = await self.check_now(url)
            if status.is_live:
                return url
        
        return None
