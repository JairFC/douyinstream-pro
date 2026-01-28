"""
DouyinStream Pro v2 - Pydantic Models
Request/Response schemas for API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


class StreamQuality(str, Enum):
    BEST = "best"
    ORIGIN = "origin"
    P1080 = "1080p"
    P720 = "720p"
    P480 = "480p"


# ============ Stream Models ============

class StreamRequest(BaseModel):
    """Request to extract/play a stream."""
    url: str = Field(..., description="Douyin/TikTok room URL")
    quality: StreamQuality = Field(default=StreamQuality.BEST)


class StreamInfo(BaseModel):
    """Stream information response."""
    url: str
    stream_url: Optional[str] = None
    title: str = "Unknown"
    author: str = "Unknown"
    is_live: bool = False
    qualities: Dict[str, str] = Field(default_factory=dict)
    error: Optional[str] = None


class StreamStatus(BaseModel):
    """Stream status for live checking."""
    url: str
    is_live: Optional[bool] = None
    last_checked: Optional[datetime] = None
    title: Optional[str] = None
    author: Optional[str] = None


# ============ Favorite Models ============

class Favorite(BaseModel):
    """Favorite stream entry."""
    url: str
    alias: str = ""
    play_count: int = 0
    added_at: datetime = Field(default_factory=datetime.now)
    last_played: Optional[datetime] = None


class FavoriteCreate(BaseModel):
    """Create a new favorite."""
    url: str
    alias: str = ""


class FavoriteUpdate(BaseModel):
    """Update favorite properties."""
    alias: Optional[str] = None


class FavoritesList(BaseModel):
    """List of favorites with live status."""
    favorites: List[Favorite]
    live_urls: List[str] = Field(default_factory=list)


# ============ System Models ============

class SystemStatus(BaseModel):
    """System status response."""
    status: str  # "running", "paused", "stopped"
    cookies_valid: bool
    cookies_age_hours: Optional[float] = None
    monitored_urls: int = 0
    live_streams: int = 0
    memory_mb: Optional[float] = None


class PauseRequest(BaseModel):
    """Request to pause system (gaming mode)."""
    reason: str = "gaming"


class CaptchaStatus(BaseModel):
    """CAPTCHA status response."""
    required: bool
    url: Optional[str] = None
    message: str = ""


# ============ Recording Models ============

class RecordingRequest(BaseModel):
    """Start recording request."""
    url: str
    quality: StreamQuality = StreamQuality.BEST
    filename: Optional[str] = None


class RecordingStatus(BaseModel):
    """Recording status."""
    active: bool
    url: Optional[str] = None
    filename: Optional[str] = None
    duration_seconds: float = 0
    size_mb: float = 0


class ClipRequest(BaseModel):
    """Save clip from buffer."""
    duration_seconds: int = Field(default=180, ge=10, le=600)
    filename: Optional[str] = None


# ============ Config Models ============

class AppSettings(BaseModel):
    """Application settings."""
    default_quality: StreamQuality = StreamQuality.BEST
    auto_switch_enabled: bool = True
    check_interval_seconds: int = 300
    buffer_duration_seconds: int = 180
    download_path: str = ""
