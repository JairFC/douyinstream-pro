"""
DouyinStream Pro v2 - Streams API
Endpoints for stream extraction and playback.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from .models import StreamRequest, StreamInfo, StreamStatus
from core.cookie_manager import CookieManager
from core.douyin_extractor import DouyinExtractor

logger = logging.getLogger(__name__)
router = APIRouter()

# Extractor instance (created on first use)
_extractor: Optional[DouyinExtractor] = None


async def get_extractor() -> DouyinExtractor:
    """Dependency to get extractor instance."""
    global _extractor
    if _extractor is None:
        cookie_manager = CookieManager()
        await cookie_manager.load_cookies()
        _extractor = DouyinExtractor(cookie_manager)
    return _extractor


@router.post("/extract", response_model=StreamInfo)
async def extract_stream(
    request: StreamRequest,
    extractor: DouyinExtractor = Depends(get_extractor)
):
    """
    Extract stream URL from Douyin/TikTok room URL.
    
    Returns stream info including available qualities.
    """
    logger.info(f"📡 Extract request: {request.url}")
    
    result = await extractor.extract_stream(request.url)
    
    if result is None:
        raise HTTPException(status_code=404, detail="Stream not found or offline")
    
    if result.get("error") == "captcha_required":
        raise HTTPException(
            status_code=403, 
            detail={
                "error": "captcha_required",
                "message": "CAPTCHA verification required. Please solve in browser.",
                "url": result.get("url")
            }
        )
    
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    # Select quality
    qualities = result.get("qualities", {})
    stream_url = None
    
    if request.quality.value in qualities:
        stream_url = qualities[request.quality.value]
    elif qualities:
        # Fallback to best available
        stream_url = result.get("url") or list(qualities.values())[0]
    
    return StreamInfo(
        url=request.url,
        stream_url=stream_url,
        title=result.get("title", "Unknown"),
        author=result.get("author", "Unknown"),
        is_live=result.get("is_live", False),
        qualities=qualities
    )


@router.get("/check/{room_id}", response_model=StreamStatus)
async def check_stream_status(
    room_id: str,
    extractor: DouyinExtractor = Depends(get_extractor)
):
    """
    Quick check if a stream is currently live.
    
    Uses cached status when available.
    """
    url = f"https://live.douyin.com/{room_id}"
    
    is_live = await extractor.check_live_status(url)
    
    return StreamStatus(
        url=url,
        is_live=is_live
    )


@router.get("/proxy")
async def proxy_stream(
    url: str,
    extractor: DouyinExtractor = Depends(get_extractor)
):
    """
    Proxy stream URL with proper headers.
    
    This endpoint can be used as the video source to avoid CORS issues.
    """
    # For now, just redirect to the stream URL
    # In production, this would proxy the stream with proper headers
    from fastapi.responses import RedirectResponse
    
    # Validate URL is a stream URL
    if not (url.endswith('.flv') or url.endswith('.m3u8') or '.flv?' in url or '.m3u8?' in url):
        raise HTTPException(status_code=400, detail="Invalid stream URL")
    
    return RedirectResponse(url=url)


@router.post("/refresh-cookies")
async def refresh_cookies():
    """
    Refresh cookies from browser.
    
    Call this after solving CAPTCHA in browser.
    """
    global _extractor
    
    cookie_manager = CookieManager()
    await cookie_manager.load_cookies()
    
    # Reset extractor with new cookies
    if _extractor:
        await _extractor.close()
        _extractor = None
    
    has_valid = cookie_manager.has_valid_cookies()
    count = len(cookie_manager.get_cookies())
    
    return {
        "success": has_valid,
        "cookies_count": count,
        "message": f"Loaded {count} cookies" if has_valid else "No valid Douyin cookies found"
    }
