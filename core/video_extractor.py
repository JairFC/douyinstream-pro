"""
DouyinStream Pro - Video Extractor
Uses yt-dlp Python API to extract video URLs in maximum quality.
"""

import threading
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
    Uses yt-dlp Python API directly (no subprocess).
    """
    
    def __init__(self) -> None:
        self._ydl_opts = {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
    
    def extract(self, url: str) -> Optional[VideoInfo]:
        """
        Extract video URL synchronously.
        Returns VideoInfo with direct playable URL or None on error.
        """
        try:
            import yt_dlp
            
            with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    print("[VideoExtractor] No info extracted")
                    return None
                
                # Get direct URL
                direct_url = info.get('url', '')
                
                # If no direct URL, try formats
                if not direct_url:
                    formats = info.get('formats', [])
                    if formats:
                        # Get best format (last one is usually best)
                        best = formats[-1]
                        direct_url = best.get('url', '')
                
                # Try requested_formats for merged streams
                if not direct_url:
                    req_formats = info.get('requested_formats', [])
                    if req_formats:
                        # Use video stream
                        for fmt in req_formats:
                            if fmt.get('vcodec', 'none') != 'none':
                                direct_url = fmt.get('url', '')
                                break
                
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
                
        except ImportError:
            print("[VideoExtractor] yt-dlp not installed. Run: pip install yt-dlp")
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
        info = self.extract(url)
        return info.direct_url if info else None


# Singleton instance
_extractor: Optional[VideoExtractor] = None


def get_video_extractor() -> VideoExtractor:
    """Get singleton VideoExtractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = VideoExtractor()
    return _extractor
