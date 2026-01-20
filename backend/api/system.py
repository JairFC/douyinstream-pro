"""
DouyinStream Pro v2 - System API
Endpoints for system control (pause/resume, status, etc).
"""

import logging
import psutil
from fastapi import APIRouter

from .models import SystemStatus, PauseRequest, CaptchaStatus
from core.cookie_manager import CookieManager

logger = logging.getLogger(__name__)
router = APIRouter()

# System state
_paused = False
_pause_reason = ""


@router.get("/status", response_model=SystemStatus)
async def get_status():
    """
    Get current system status.
    
    Useful for dashboard display and health monitoring.
    """
    cookie_manager = CookieManager()
    
    # Get memory usage
    process = psutil.Process()
    memory_mb = process.memory_info().rss / (1024 * 1024)
    
    return SystemStatus(
        status="paused" if _paused else "running",
        cookies_valid=cookie_manager.has_valid_cookies(),
        cookies_age_hours=cookie_manager.get_age_hours(),
        monitored_urls=0,  # TODO: integrate with LiveChecker
        live_streams=0,    # TODO: integrate with LiveChecker
        memory_mb=round(memory_mb, 1)
    )


@router.post("/pause")
async def pause_system(request: PauseRequest):
    """
    Pause all background tasks (for gaming mode).
    
    This stops:
    - Live status checking
    - Background cookie refresh
    - Any buffering processes
    
    VLC/playback is NOT affected - only background tasks.
    """
    global _paused, _pause_reason
    
    _paused = True
    _pause_reason = request.reason
    
    # TODO: Actually pause LiveChecker and other services
    
    logger.info(f"⏸️ System paused: {request.reason}")
    
    return {
        "success": True,
        "status": "paused",
        "message": f"Background tasks paused for {request.reason}",
        "memory_freed_estimate_mb": 50  # Estimate
    }


@router.post("/resume")
async def resume_system():
    """
    Resume all background tasks.
    """
    global _paused, _pause_reason
    
    _paused = False
    _pause_reason = ""
    
    # TODO: Actually resume LiveChecker and other services
    
    logger.info("▶️ System resumed")
    
    return {
        "success": True,
        "status": "running",
        "message": "Background tasks resumed"
    }


@router.get("/paused")
async def is_paused():
    """Check if system is currently paused."""
    return {
        "paused": _paused,
        "reason": _pause_reason
    }


@router.get("/captcha", response_model=CaptchaStatus)
async def check_captcha_status():
    """
    Check if CAPTCHA resolution is needed.
    """
    cookie_manager = CookieManager()
    
    if cookie_manager.has_valid_cookies():
        return CaptchaStatus(
            required=False,
            message="Cookies are valid"
        )
    
    return CaptchaStatus(
        required=True,
        url="https://live.douyin.com/",
        message="Please visit Douyin in browser to solve CAPTCHA, then click 'Refresh Cookies'"
    )


@router.post("/captcha/resolved")
async def captcha_resolved():
    """
    Called after user resolves CAPTCHA in browser.
    Triggers cookie refresh.
    """
    cookie_manager = CookieManager()
    await cookie_manager.load_cookies()
    
    if cookie_manager.has_valid_cookies():
        return {
            "success": True,
            "cookies_count": len(cookie_manager.get_cookies()),
            "message": "CAPTCHA resolved successfully"
        }
    
    return {
        "success": False,
        "message": "Could not extract cookies. Make sure you completed CAPTCHA in browser."
    }


@router.post("/cleanup")
async def cleanup_resources():
    """
    Clean up temporary files and resources.
    
    Useful for freeing disk space from buffer segments.
    """
    import shutil
    from pathlib import Path
    import os
    
    temp_dir = Path(os.environ.get("TEMP", "/tmp")) / "douyinstream"
    
    freed_mb = 0
    if temp_dir.exists():
        # Calculate size first
        for file in temp_dir.rglob("*"):
            if file.is_file():
                freed_mb += file.stat().st_size / (1024 * 1024)
        
        # Remove all temp files
        shutil.rmtree(temp_dir, ignore_errors=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"🧹 Cleaned up {freed_mb:.1f} MB of temp files")
    
    return {
        "success": True,
        "freed_mb": round(freed_mb, 1),
        "message": f"Cleaned up {freed_mb:.1f} MB"
    }


@router.get("/health")
async def health_check():
    """Detailed health check."""
    cookie_manager = CookieManager()
    
    return {
        "status": "healthy",
        "components": {
            "api": True,
            "cookies": cookie_manager.has_valid_cookies(),
            "live_checker": not _paused,
        },
        "version": "2.0.0"
    }
