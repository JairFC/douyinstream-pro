"""
DouyinStream Pro - Stream Checker
Simple, modular stream status checker with threading support.
"""

import logging
from typing import Optional, Dict, Callable
from core.stream_engine import StreamEngine


class StreamChecker:
    """
    Simple stream status checker.
    Checks if streams are live without blocking UI.
    """
    
    def __init__(self, stream_engine: StreamEngine):
        """
        Initialize checker with stream engine.
        
        Args:
            stream_engine: StreamEngine instance for checking streams
        """
        self.engine = stream_engine
        self.checking = False
        self._cache: Dict[str, bool] = {}
    
    def check_single(self, url: str, timeout: int = 5) -> bool:
        """
        Check if a single stream is live.
        
        Args:
            url: Stream URL to check
            timeout: Timeout in seconds (default: 5)
            
        Returns:
            True if stream is live, False otherwise
        """
        try:
            logging.debug(f"[StreamChecker] Checking: {url}")
            
            # Try to get available streams
            streams = self.engine.get_available_streams(url)
            
            is_live = bool(streams)
            
            # Cache result
            self._cache[url] = is_live
            
            logging.debug(f"[StreamChecker] Result: {'LIVE' if is_live else 'OFFLINE'}")
            return is_live
            
        except Exception as e:
            logging.debug(f"[StreamChecker] Error checking {url}: {e}")
            return False
    
    def check_batch(self, urls: list, on_progress: Optional[Callable[[str, str], None]] = None) -> Dict[str, bool]:
        """
        Check multiple streams sequentially.
        
        Args:
            urls: List of URLs to check
            on_progress: Callback(url, status) called for each URL
                        status can be: "checking", "live", "offline"
            
        Returns:
            Dictionary mapping URL to live status
        """
        results = {}
        
        for url in urls:
            # Notify checking
            if on_progress:
                on_progress(url, "checking")
            
            # Check stream
            is_live = self.check_single(url)
            results[url] = is_live
            
            # Notify result
            if on_progress:
                status = "live" if is_live else "offline"
                on_progress(url, status)
        
        return results
    
    def get_cached_status(self, url: str) -> Optional[bool]:
        """
        Get cached status for a URL.
        
        Args:
            url: Stream URL
            
        Returns:
            True if live, False if offline, None if not cached
        """
        return self._cache.get(url)
    
    def clear_cache(self):
        """Clear all cached results."""
        self._cache.clear()
