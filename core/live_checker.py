"""
DouyinStream Pro - Live Status Checker
Background service to check if favorite streamers are currently live.
"""

import subprocess
import threading
import time
from typing import Callable, Dict, Optional
from dataclasses import dataclass


@dataclass
class LiveStatus:
    """Status of a stream URL."""
    url: str
    is_live: bool
    last_checked: float  # timestamp


class LiveStatusChecker:
    """
    Background service that periodically checks if streams are live.
    Uses streamlink to validate stream availability.
    """
    
    CHECK_INTERVAL = 300  # 5 minutes
    CHECK_TIMEOUT = 10  # seconds per check
    
    def __init__(self) -> None:
        self._statuses: Dict[str, LiveStatus] = {}
        self._callbacks: list[Callable[[str, bool], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._urls_to_check: list[str] = []
        self._lock = threading.Lock()
    
    def add_callback(self, callback: Callable[[str, bool], None]) -> None:
        """Add callback for status updates. Called with (url, is_live)."""
        self._callbacks.append(callback)
    
    def set_urls(self, urls: list[str]) -> None:
        """Set list of URLs to monitor."""
        with self._lock:
            self._urls_to_check = urls.copy()
    
    def add_url(self, url: str) -> None:
        """Add a URL to monitor."""
        with self._lock:
            if url not in self._urls_to_check:
                self._urls_to_check.append(url)
    
    def remove_url(self, url: str) -> None:
        """Remove a URL from monitoring."""
        with self._lock:
            if url in self._urls_to_check:
                self._urls_to_check.remove(url)
            if url in self._statuses:
                del self._statuses[url]
    
    def get_status(self, url: str) -> Optional[bool]:
        """Get cached status for a URL. Returns None if not checked yet."""
        if url in self._statuses:
            return self._statuses[url].is_live
        return None
    
    def start(self) -> None:
        """Start background checking."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._check_loop, daemon=True)
        self._thread.start()
        print("[LiveStatusChecker] Started background thread")
    
    def stop(self) -> None:
        """Stop background checking."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        print("[LiveStatusChecker] Stopped")
    
    def check_now(self, url: str) -> bool:
        """Check a single URL immediately. Returns True if live."""
        return self._check_single(url)
    
    def _check_loop(self) -> None:
        """Background loop that checks all URLs periodically."""
        while self._running:
            # Get URLs to check
            with self._lock:
                urls = self._urls_to_check.copy()
            
            # Check each URL
            for url in urls:
                if not self._running:
                    break
                
                is_live = self._check_single(url)
                
                # Update status
                old_status = self._statuses.get(url)
                self._statuses[url] = LiveStatus(
                    url=url,
                    is_live=is_live,
                    last_checked=time.time()
                )
                
                # Notify if status changed
                if old_status is None or old_status.is_live != is_live:
                    self._notify(url, is_live)
                
                # Small delay between checks
                time.sleep(1)
            
            # Wait for next check interval
            for _ in range(self.CHECK_INTERVAL):
                if not self._running:
                    break
                time.sleep(1)
    
    def _check_single(self, url: str) -> bool:
        """Check if a single URL is live using streamlink Python API."""
        try:
            from streamlink import Streamlink
            
            session = Streamlink()
            streams = session.streams(url)
            
            # If any streams are available, it's live
            return len(streams) > 0
            
        except Exception as e:
            # Stream not available or error
            print(f"[LiveStatusChecker] Error checking {url}: {e}")
            return False
    
    def _notify(self, url: str, is_live: bool) -> None:
        """Notify all callbacks of status change."""
        for callback in self._callbacks:
            try:
                callback(url, is_live)
            except Exception as e:
                print(f"[LiveStatusChecker] Callback error: {e}")


# Singleton instance
_checker: Optional[LiveStatusChecker] = None


def get_live_checker() -> LiveStatusChecker:
    """Get singleton LiveStatusChecker instance."""
    global _checker
    if _checker is None:
        _checker = LiveStatusChecker()
    return _checker
