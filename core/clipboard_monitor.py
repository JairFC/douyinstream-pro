"""
DouyinStream Pro - Clipboard Monitor
Smart clipboard listener for automatic URL detection.
"""

import re
import threading
import time
from typing import Callable, Optional
import hashlib

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False


class ClipboardMonitor:
    """
    Daemon thread that monitors clipboard for streaming URLs.
    Supports multiple platforms: Douyin, TikTok, Twitch, YouTube, Kick, Bilibili, etc.
    """
    
    # URL patterns to detect (all supported platforms)
    URL_PATTERNS = [
        # Douyin
        r'https?://(?:www\.)?douyin\.com/\S+',
        r'https?://v\.douyin\.com/\S+',
        r'https?://live\.douyin\.com/\S+',
        # TikTok
        r'https?://(?:www\.)?tiktok\.com/@[\w.]+/live',
        r'https?://(?:www\.)?tiktok\.com/\S+',
        # Twitch
        r'https?://(?:www\.)?twitch\.tv/\w+',
        r'https?://(?:www\.)?twitch\.tv/videos/\d+',
        # YouTube
        r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'https?://(?:www\.)?youtube\.com/live/[\w-]+',
        r'https?://youtu\.be/[\w-]+',
        r'https?://(?:www\.)?youtube\.com/channel/[\w-]+/live',
        r'https?://(?:www\.)?youtube\.com/@[\w-]+/live',
        # Kick
        r'https?://(?:www\.)?kick\.com/\w+',
        # Bilibili
        r'https?://live\.bilibili\.com/\d+',
        r'https?://(?:www\.)?bilibili\.com/video/\w+',
        # NOTE: CC163 not supported by Streamlink
        # Huya
        r'https?://(?:www\.)?huya\.com/\w+',
        # AfreecaTV
        r'https?://play\.afreecatv\.com/\w+',
        r'https?://(?:www\.)?afreecatv\.com/\w+',
        # Facebook
        r'https?://(?:www\.)?facebook\.com/\w+/videos/\d+',
        r'https?://(?:www\.)?facebook\.com/watch/live/',
        # Dailymotion
        r'https?://(?:www\.)?dailymotion\.com/video/\w+',
    ]
    
    def __init__(self, check_interval: float = 0.5) -> None:
        """
        Initialize clipboard monitor.
        
        Args:
            check_interval: Seconds between clipboard checks (default 0.5s)
        """
        self._check_interval = check_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_hash: str = ""
        self._callbacks: list[Callable[[str], None]] = []
        self._enabled = True
    
    def _hash_content(self, content: str) -> str:
        """Generate hash of clipboard content to detect changes."""
        return hashlib.md5(content.encode('utf-8', errors='ignore')).hexdigest()
    
    def _is_valid_url(self, text: str) -> Optional[str]:
        """
        Check if text contains a valid Douyin/TikTok URL.
        Returns the URL if found, None otherwise.
        """
        for pattern in self.URL_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop running in daemon thread."""
        while self._running:
            if self._enabled and PYPERCLIP_AVAILABLE:
                try:
                    content = pyperclip.paste()
                    if content:
                        current_hash = self._hash_content(content)
                        
                        # Only process if content changed
                        if current_hash != self._last_hash:
                            self._last_hash = current_hash
                            
                            # Check for valid URL
                            url = self._is_valid_url(content)
                            if url:
                                self._emit_url_detected(url)
                                
                except Exception:
                    # Silently ignore clipboard access errors
                    pass
            
            time.sleep(self._check_interval)
    
    def _emit_url_detected(self, url: str) -> None:
        """Notify all callbacks of detected URL."""
        for callback in self._callbacks:
            try:
                callback(url)
            except Exception as e:
                print(f"[ClipboardMonitor] Callback error: {e}")
    
    def add_callback(self, callback: Callable[[str], None]) -> None:
        """Add a callback to be called when URL is detected."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[str], None]) -> None:
        """Remove a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def start(self) -> None:
        """Start the clipboard monitor."""
        if self._running:
            return
        
        if not PYPERCLIP_AVAILABLE:
            print("[ClipboardMonitor] pyperclip not installed, monitor disabled")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        print("[ClipboardMonitor] Monitor started")
    
    def stop(self) -> None:
        """Stop the clipboard monitor."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        print("[ClipboardMonitor] Monitor stopped")
    
    def enable(self) -> None:
        """Enable URL detection."""
        self._enabled = True
    
    def disable(self) -> None:
        """Temporarily disable URL detection."""
        self._enabled = False
    
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._running
    
    def is_enabled(self) -> bool:
        """Check if URL detection is enabled."""
        return self._enabled
    
    def clear_last_hash(self) -> None:
        """Clear last hash to re-detect current clipboard content."""
        self._last_hash = ""
