"""
DouyinStream Pro - Video Extractor
Uses yt-dlp to extract video URLs in maximum quality.
"""

import subprocess
import threading
import json
from typing import Callable, Optional
from dataclasses import dataclass


@dataclass
class VideoInfo:
    """Information about an extracted video."""
    url: str
    direct_url: str
    title: str
    quality: str
    duration: Optional[int]  # seconds
    thumbnail: Optional[str]


class VideoExtractor:
    """
    Extracts video URLs using yt-dlp for maximum quality playback.
    Works with Douyin, TikTok, and many other platforms.
    """
    
    TIMEOUT = 30  # seconds
    
    def __init__(self) -> None:
        self._yt_dlp_path = "yt-dlp"  # Assumes in PATH
    
    def extract(self, url: str) -> Optional[VideoInfo]:
        """
        Extract video URL synchronously.
        Returns VideoInfo with direct playable URL or None on error.
        """
        try:
            # Get JSON info from yt-dlp
            result = subprocess.run(
                [
                    self._yt_dlp_path,
                    '--dump-json',
                    '--no-playlist',
                    '-f', 'best',
                    url
                ],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT
            )
            
            if result.returncode != 0:
                print(f"[VideoExtractor] yt-dlp error: {result.stderr}")
                return None
            
            # Parse JSON
            info = json.loads(result.stdout)
            
            # Get direct URL
            direct_url = info.get('url', '')
            if not direct_url:
                # Try formats
                formats = info.get('formats', [])
                if formats:
                    # Get best format
                    best = formats[-1]
                    direct_url = best.get('url', '')
            
            if not direct_url:
                print("[VideoExtractor] No direct URL found")
                return None
            
            return VideoInfo(
                url=url,
                direct_url=direct_url,
                title=info.get('title', 'Unknown'),
                quality=info.get('format', 'best'),
                duration=info.get('duration'),
                thumbnail=info.get('thumbnail')
            )
            
        except subprocess.TimeoutExpired:
            print(f"[VideoExtractor] Timeout extracting {url}")
            return None
        except json.JSONDecodeError as e:
            print(f"[VideoExtractor] JSON error: {e}")
            return None
        except FileNotFoundError:
            print("[VideoExtractor] yt-dlp not found")
            return None
        except Exception as e:
            print(f"[VideoExtractor] Error: {e}")
            return None
    
    def extract_async(self, url: str, callback: Callable[[Optional[VideoInfo]], None]) -> None:
        """
        Extract video URL asynchronously.
        Calls callback with VideoInfo or None on completion.
        """
        def worker():
            result = self.extract(url)
            callback(result)
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
    
    def get_direct_url(self, url: str) -> Optional[str]:
        """Quick method to just get the direct playable URL."""
        try:
            result = subprocess.run(
                [self._yt_dlp_path, '-g', '-f', 'best', url],
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split('\n')[0]
            
            return None
            
        except Exception as e:
            print(f"[VideoExtractor] Error getting direct URL: {e}")
            return None


# Singleton instance
_extractor: Optional[VideoExtractor] = None


def get_video_extractor() -> VideoExtractor:
    """Get singleton VideoExtractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = VideoExtractor()
    return _extractor
