"""
DouyinStream Pro - Stream Engine
Core logic for stream detection, URL resolution, and player launching.
"""

import re
import sys
import subprocess
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional
from pathlib import Path

try:
    import streamlink
    from streamlink import Streamlink
    STREAMLINK_AVAILABLE = True
except ImportError:
    STREAMLINK_AVAILABLE = False

from config.settings_manager import get_settings
from core.process_manager import register_process, unregister_process, kill_process_tree


class StreamQuality(Enum):
    """Available stream quality options."""
    BEST = "best"
    P1080 = "1080p,1080p60,best"
    P720 = "720p,720p60,1080p,best"
    P480 = "480p,720p,best"
    AUDIO = "audio_only,audio,worst"


@dataclass
class StreamInfo:
    """Information about a resolved stream."""
    url: str
    title: str
    quality: str
    stream_url: str
    available_qualities: list[str]
    is_live: bool
    streamer_name: str


class StreamEngine:
    """
    Core engine for stream detection and resolution.
    Uses Streamlink API for stream handling.
    Supports multiple platforms: Douyin, TikTok, Twitch, YouTube, Kick, Bilibili, etc.
    """
    
    # URL patterns for supported platforms
    PLATFORM_PATTERNS = {
        "douyin": [
            r'https?://(?:www\.)?douyin\.com/\S+',
            r'https?://v\.douyin\.com/\S+',
            r'https?://live\.douyin\.com/\S+',
        ],
        "tiktok": [
            r'https?://(?:www\.)?tiktok\.com/@[\w.]+/live',
            r'https?://(?:www\.)?tiktok\.com/\S+',
        ],
        "twitch": [
            r'https?://(?:www\.)?twitch\.tv/\w+',
            r'https?://(?:www\.)?twitch\.tv/videos/\d+',
        ],
        "youtube": [
            r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'https?://(?:www\.)?youtube\.com/live/[\w-]+',
            r'https?://youtu\.be/[\w-]+',
            r'https?://(?:www\.)?youtube\.com/channel/[\w-]+/live',
            r'https?://(?:www\.)?youtube\.com/@[\w-]+/live',
        ],
        "kick": [
            r'https?://(?:www\.)?kick\.com/\w+',
        ],
        "bilibili": [
            r'https?://live\.bilibili\.com/\d+',
            r'https?://(?:www\.)?bilibili\.com/video/\w+',
        ],
        # NOTE: CC163 removed - Streamlink doesn't have a plugin for it
        "huya": [
            r'https?://(?:www\.)?huya\.com/\w+',
        ],
        "afreecatv": [
            r'https?://play\.afreecatv\.com/\w+',
            r'https?://(?:www\.)?afreecatv\.com/\w+',
        ],
        "facebook": [
            r'https?://(?:www\.)?facebook\.com/\w+/videos/\d+',
            r'https?://(?:www\.)?facebook\.com/watch/live/',
        ],
        "dailymotion": [
            r'https?://(?:www\.)?dailymotion\.com/video/\w+',
        ],
    }
    
    # Display names for platforms
    PLATFORM_NAMES = {
        "douyin": "🇨🇳 Douyin",
        "tiktok": "🎵 TikTok",
        "twitch": "🟣 Twitch",
        "youtube": "🔴 YouTube",
        "kick": "🟢 Kick",
        "bilibili": "📺 Bilibili",
        "huya": "🐯 Huya",
        "afreecatv": "📡 AfreecaTV",
        "facebook": "📘 Facebook",
        "dailymotion": "📹 Dailymotion",
    }
    
    # Headers to inject for Douyin requests
    DOUYIN_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.douyin.com/",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    
    def __init__(self) -> None:
        self._settings = get_settings()
        self._session: Optional[Streamlink] = None
        self._current_process: Optional[subprocess.Popen] = None
        self._callbacks: dict[str, list[Callable]] = {
            "on_stream_start": [],
            "on_stream_stop": [],
            "on_stream_error": [],
            "on_quality_change": [],
            "on_log": [],
        }
        
        if STREAMLINK_AVAILABLE:
            self._init_session()
    
    def _init_session(self) -> None:
        """Initialize Streamlink session with custom options."""
        self._session = Streamlink()
        
        # Set options for better compatibility
        self._session.set_option("http-headers", self.DOUYIN_HEADERS)
        self._session.set_option("stream-segment-threads", 3)
        self._session.set_option("hls-live-edge", 3)
        self._session.set_option("ringbuffer-size", 32 * 1024 * 1024)  # 32MB buffer
        
        # Twitch-specific options for lower latency and potentially fewer ads
        # Low latency mode (if broadcaster has it enabled)
        self._session.set_option("twitch-low-latency", True)
        # Prefer AV1 codec which may have fewer embed ads
        self._session.set_option("twitch-supported-codecs", "av1,h264")
    
    def _log(self, message: str, level: str = "INFO") -> None:
        """Emit log message to observers."""
        formatted = f"[{level}] {message}"
        for callback in self._callbacks.get("on_log", []):
            try:
                callback(formatted)
            except Exception:
                pass
    
    def add_callback(self, event: str, callback: Callable) -> None:
        """Add a callback for stream events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def remove_callback(self, event: str, callback: Callable) -> None:
        """Remove a callback."""
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL matches any supported platform pattern."""
        return self.detect_platform(url) is not None
    
    def detect_platform(self, url: str) -> Optional[str]:
        """Detect which platform the URL belongs to. Returns platform key or None."""
        for platform, patterns in self.PLATFORM_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, url, re.IGNORECASE):
                    return platform
        return None
    
    def get_platform_name(self, url: str) -> str:
        """Get display name for platform from URL."""
        platform = self.detect_platform(url)
        if platform:
            return self.PLATFORM_NAMES.get(platform, platform.capitalize())
        return "Unknown"
    
    def extract_streamer_name(self, url: str) -> str:
        """Extract streamer name from URL for any supported platform."""
        platform = self.detect_platform(url)
        
        if platform == "douyin":
            match = re.search(r'live\.douyin\.com/(\d+)', url)
            if match:
                return f"room_{match.group(1)}"
        
        elif platform == "tiktok":
            match = re.search(r'tiktok\.com/@([\w.]+)', url)
            if match:
                return match.group(1)
        
        elif platform == "twitch":
            match = re.search(r'twitch\.tv/(\w+)', url)
            if match:
                return match.group(1)
        
        elif platform == "youtube":
            match = re.search(r'youtube\.com/@([\w-]+)', url)
            if match:
                return match.group(1)
            match = re.search(r'youtube\.com/channel/([\w-]+)', url)
            if match:
                return match.group(1)
        
        elif platform == "kick":
            match = re.search(r'kick\.com/(\w+)', url)
            if match:
                return match.group(1)
        
        elif platform == "bilibili":
            match = re.search(r'live\.bilibili\.com/(\d+)', url)
            if match:
                return f"room_{match.group(1)}"
        
        elif platform == "cc163":
            match = re.search(r'cc\.163\.com/(\d+)', url)
            if match:
                return f"room_{match.group(1)}"
        
        elif platform == "huya":
            match = re.search(r'huya\.com/(\w+)', url)
            if match:
                return match.group(1)
        
        return "unknown_streamer"
    
    def check_stream_online(self, url: str) -> Optional[bool]:
        """
        Check if a stream is currently online without playing it.
        Returns True if online, False if offline, None if check failed.
        """
        if not STREAMLINK_AVAILABLE or not self._session:
            return None
        
        try:
            streams = self._session.streams(url)
            return len(streams) > 0
        except Exception:
            return None
    
    def get_available_streams(self, url: str) -> Optional[StreamInfo]:
        """
        Resolve stream URL and get available qualities.
        Returns StreamInfo or None if stream is not available.
        """
        if not STREAMLINK_AVAILABLE:
            self._log("Streamlink no está instalado", "ERROR")
            return None
        
        if not self.is_valid_url(url):
            self._log(f"URL no válida: {url}", "ERROR")
            return None
        
        self._log(f"Resolviendo stream: {url}")
        
        try:
            streams = self._session.streams(url)
            
            if not streams:
                self._log("No se encontraron streams disponibles", "WARNING")
                return None
            
            available = list(streams.keys())
            self._log(f"Calidades disponibles: {available}")
            
            # Get best stream URL for preview
            best_stream = streams.get("best") or list(streams.values())[0]
            stream_url = best_stream.url if hasattr(best_stream, 'url') else str(best_stream)
            
            return StreamInfo(
                url=url,
                title=self.extract_streamer_name(url),
                quality="best",
                stream_url=stream_url,
                available_qualities=available,
                is_live=True,
                streamer_name=self.extract_streamer_name(url)
            )
            
        except Exception as e:
            self._log(f"Error al resolver stream: {e}", "ERROR")
            for callback in self._callbacks.get("on_stream_error", []):
                callback(str(e))
            return None
    
    def get_stream_url(self, url: str, quality: str = "best") -> Optional[str]:
        """Get direct stream URL for given quality."""
        if not STREAMLINK_AVAILABLE or not self._session:
            return None
        
        try:
            streams = self._session.streams(url)
            if not streams:
                return None
            
            # Try requested quality, fall back to best
            qualities_to_try = quality.split(",")
            for q in qualities_to_try:
                q = q.strip()
                if q in streams:
                    stream = streams[q]
                    return stream.url if hasattr(stream, 'url') else None
            
            # Fallback to best
            if "best" in streams:
                stream = streams["best"]
                return stream.url if hasattr(stream, 'url') else None
            
            return None
            
        except Exception as e:
            self._log(f"Error obteniendo URL de stream: {e}", "ERROR")
            return None
    
    def play_in_vlc(self, url: str, quality: str = "best") -> bool:
        """
        Launch stream in external VLC player.
        Returns True if successful.
        """
        vlc_path = self._settings.get("external_player_path")
        
        if not vlc_path or not Path(vlc_path).exists():
            self._log("VLC no encontrado", "ERROR")
            for callback in self._callbacks.get("on_stream_error", []):
                callback("VLC no encontrado. Por favor, configura la ruta en Ajustes.")
            return False
        
        self._log(f"Iniciando stream en VLC: {url} ({quality})")
        
        def _launch():
            try:
                # Use streamlink via python module to guarantee availability
                cmd = [
                    sys.executable, "-m", "streamlink",
                    "--player", vlc_path,
                    "--player-args", "--network-caching=1000 --file-caching=1000",
                    "--http-header", f"User-Agent={self.DOUYIN_HEADERS['User-Agent']}",
                    "--http-header", f"Referer={self.DOUYIN_HEADERS['Referer']}",
                    url,
                    quality
                ]
                
                self._current_process = register_process(subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                ))
                
                for callback in self._callbacks.get("on_stream_start", []):
                    callback(url, quality)
                
                self._log("VLC iniciado correctamente")
                
                # Wait for process to finish
                self._current_process.wait()
                
                unregister_process(self._current_process)
                
                for callback in self._callbacks.get("on_stream_stop", []):
                    callback()
                    
            except Exception as e:
                self._log(f"Error al iniciar VLC: {e}", "ERROR")
                for callback in self._callbacks.get("on_stream_error", []):
                    callback(str(e))
        
        thread = threading.Thread(target=_launch, daemon=True)
        thread.start()
        return True
    
    def play_in_mpv(self, url: str, quality: str = "best") -> bool:
        """Launch stream in external MPV player."""
        import shutil
        mpv_path = shutil.which("mpv")
        
        if not mpv_path:
            # Try common paths
            for path in self._settings.MPV_SEARCH_PATHS:
                if Path(path).exists():
                    mpv_path = path
                    break
        
        if not mpv_path:
            self._log("MPV no encontrado", "ERROR")
            return False
        
        self._log(f"Iniciando stream en MPV: {url}")
        
        def _launch():
            try:
                cmd = [
                    sys.executable, "-m", "streamlink",
                    "--player", mpv_path,
                    "--player-args", "--cache=yes --demuxer-max-bytes=50M",
                    url,
                    quality
                ]
                
                self._current_process = register_process(subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                ))
                
                for callback in self._callbacks.get("on_stream_start", []):
                    callback(url, quality)
                
                self._current_process.wait()
                
                unregister_process(self._current_process)
                
                for callback in self._callbacks.get("on_stream_stop", []):
                    callback()
                    
            except Exception as e:
                self._log(f"Error al iniciar MPV: {e}", "ERROR")
                for callback in self._callbacks.get("on_stream_error", []):
                    callback(str(e))
        
        thread = threading.Thread(target=_launch, daemon=True)
        thread.start()
        return True
    
    def stop_stream(self) -> None:
        """Stop current stream playback."""
        if self._current_process:
            try:
                kill_process_tree(self._current_process)
                self._current_process = None
                self._log("Stream detenido")
                for callback in self._callbacks.get("on_stream_stop", []):
                    callback()
            except Exception as e:
                self._log(f"Error al detener stream: {e}", "ERROR")
    
    def is_playing(self) -> bool:
        """Check if a stream is currently playing."""
        return self._current_process is not None and self._current_process.poll() is None
