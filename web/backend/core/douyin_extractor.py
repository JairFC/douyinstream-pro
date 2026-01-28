"""
DouyinStream Pro v2 - Async Douyin Extractor
Modern async implementation using proven desktop extraction strategies.
"""

import re
import json
import logging
from typing import Optional, Dict, List, Any
from urllib.parse import unquote
import httpx

from .cookie_manager import CookieManager
from .extraction_strategies import AdaptiveExtractor

logger = logging.getLogger(__name__)


class DouyinExtractor:
    """
    Async Douyin stream extractor with multi-strategy approach.
    Uses centralized CookieManager for authentication.
    Uses AdaptiveExtractor from desktop for proven extraction.
    """
    
    # Headers that mimic a real browser
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://www.douyin.com/',
    }
    
    def __init__(self, cookie_manager: CookieManager):
        self.cookie_manager = cookie_manager
        self._client: Optional[httpx.AsyncClient] = None
        # Use proven desktop extractor
        self._extractor = AdaptiveExtractor()
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with current cookies."""
        if self._client is None:
            cookies = self.cookie_manager.get_cookies()
            self._client = httpx.AsyncClient(
                headers=self.DEFAULT_HEADERS,
                cookies=cookies,
                timeout=15.0,
                follow_redirects=True
            )
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def extract_stream(self, room_url: str) -> Optional[Dict[str, Any]]:
        """
        Extract stream URL and metadata from Douyin room.
        
        Returns:
            dict with: url, title, author, is_live, qualities
            None if extraction fails or CAPTCHA required
        """
        try:
            logger.info(f"📡 Extracting stream: {room_url}")
            
            client = await self._get_client()
            response = await client.get(room_url)
            response.raise_for_status()
            html = response.text
            
            logger.info(f"📄 HTML size: {len(html)} bytes")
            
            # Debug: Check for key patterns
            has_flv = '.flv' in html
            has_m3u8 = '.m3u8' in html
            has_streamStore = 'streamStore' in html
            has_pace_f = '__pace_f' in html
            logger.info(f"📊 Debug: FLV={has_flv}, M3U8={has_m3u8}, streamStore={has_streamStore}, __pace_f={has_pace_f}")
            
            # Check for CAPTCHA
            if self._is_captcha_page(html):
                logger.warning("🔒 CAPTCHA detected!")
                return {
                    "error": "captcha_required",
                    "url": room_url,
                    "message": "Please solve CAPTCHA in browser"
                }
            
            # Check HTML size (too small = auth issue)
            if len(html) < 10000:
                logger.warning(f"⚠️ HTML too small ({len(html)} bytes)")
                return {
                    "error": "auth_required",
                    "message": "Authentication cookies may be expired"
                }
            
            # Use proven desktop AdaptiveExtractor
            cookies = self.cookie_manager.get_cookies()
            result = self._extractor.extract(html, cookies)
            
            if result:
                logger.info(f"✅ Stream found: {result.get('title', 'Unknown')}")
                # Ensure URL is properly decoded
                if result.get('url'):
                    result['url'] = self._decode_url(result['url'])
                return result
            
            # Check if offline
            if self._check_offline(html):
                logger.info("📴 Stream is offline")
                return await self._extract_offline_info(html)
            
            logger.warning("❌ No stream data found")
            return None
            
        except httpx.TimeoutException:
            logger.error("⏱️ Request timeout")
            return {"error": "timeout"}
        except Exception as e:
            logger.error(f"❌ Extraction error: {e}")
            return {"error": str(e)}
    
    def _decode_url(self, url: str) -> str:
        """Decode URL escapes."""
        url = url.replace('\\u0026', '&')
        url = url.replace('\\u003d', '=')
        url = url.replace('\\u003f', '?')
        url = url.replace('\\u002F', '/')
        url = url.replace('\\/', '/')
        return unquote(url)
    
    def _is_captcha_page(self, html: str) -> bool:
        """Detect CAPTCHA page."""
        return 'TTGCaptcha' in html and len(html) < 10000
    
    def _check_offline(self, html: str) -> bool:
        """Check if stream is offline."""
        offline_keywords = ['未开播', '直播已结束', 'has ended', 'is_live":false']
        return any(kw in html.lower() for kw in offline_keywords)
    
    def _extract_direct_urls(self, html: str) -> Optional[Dict[str, Any]]:
        """Strategy 1: Extract URLs directly using regex."""
        # FLV URLs (preferred)
        flv_pattern = r'"(https?://[^"]+\.flv[^"]*)"'
        flv_matches = re.findall(flv_pattern, html)
        
        # M3U8 URLs (fallback)
        m3u8_pattern = r'"(https?://[^"]+\.m3u8[^"]*)"'
        m3u8_matches = re.findall(m3u8_pattern, html)
        
        if not flv_matches and not m3u8_matches:
            return None
        
        # Decode and select best URL
        def decode_url(url: str) -> str:
            url = unquote(url)
            url = url.replace('\\u002F', '/').replace('\\/', '/')
            return url
        
        # Build qualities dict
        qualities = {}
        for url in flv_matches[:5]:  # Limit to 5
            decoded = decode_url(url)
            # Try to extract quality name from URL
            if 'origin' in decoded.lower() or 'uhd' in decoded.lower():
                qualities['origin'] = decoded
            elif '1080' in decoded:
                qualities['1080p'] = decoded
            elif '720' in decoded:
                qualities['720p'] = decoded
            else:
                qualities[f'quality_{len(qualities)}'] = decoded
        
        # Add m3u8 as fallback
        for url in m3u8_matches[:2]:
            decoded = decode_url(url)
            qualities[f'hls_{len(qualities)}'] = decoded
        
        if not qualities:
            return None
        
        # Select best URL
        best_url = qualities.get('origin') or qualities.get('1080p') or list(qualities.values())[0]
        
        # Try to extract title
        title_match = re.search(r'"title":"([^"]+)"', html)
        title = title_match.group(1) if title_match else "Douyin Live"
        
        # Try to extract author
        author_match = re.search(r'"nickname":"([^"]+)"', html)
        author = author_match.group(1) if author_match else "Unknown"
        
        return {
            'url': best_url,
            'title': title,
            'author': author,
            'is_live': True,
            'qualities': qualities
        }
    
    def _extract_json_wrapper(self, html: str) -> Optional[Dict[str, Any]]:
        """Strategy 2: Extract from __pace_f JSON with wrapper format."""
        pattern = r'self\.__pace_f\.push\(\[\d+,"(\w+:.+?)"\]\)</script>'
        matches = re.findall(pattern, html)
        
        for match in matches:
            if 'streamStore' not in match:
                continue
            
            try:
                # Remove prefix (e.g., "d:")
                data_str = re.sub(r'^\w+:', '', match)
                data_str = data_str.replace('\\"', '"')
                data = json.loads(data_str)
                
                # Handle array wrapper: ["$", "$L12", null, {...}]
                if isinstance(data, list):
                    for item in reversed(data):
                        if isinstance(item, dict) and 'state' in item:
                            return self._parse_stream_state(item['state'])
                
            except json.JSONDecodeError:
                continue
        
        return None
    
    def _extract_legacy_json(self, html: str) -> Optional[Dict[str, Any]]:
        """Strategy 3: Legacy JSON format extraction."""
        # Try RENDER_DATA
        render_pattern = r'window\._ROUTER_DATA\s*=\s*({.+?})</script>'
        match = re.search(render_pattern, html)
        
        if match:
            try:
                data = json.loads(match.group(1))
                return self._parse_stream_state(data)
            except:
                pass
        
        return None
    
    def _parse_stream_state(self, state: Dict) -> Optional[Dict[str, Any]]:
        """Parse stream data from state object."""
        try:
            # Get room info
            room_store = state.get('roomStore', {})
            room_info = room_store.get('roomInfo', {})
            room = room_info.get('room', {})
            anchor = room_info.get('anchor', {})
            
            title = room.get('title', 'Douyin Live')
            author = anchor.get('nickname', 'Unknown')
            status = room.get('status', 0)
            is_live = status == 2
            
            # Get stream URLs
            stream_store = state.get('streamStore', {})
            stream_data = stream_store.get('streamData', {})
            h264_data = stream_data.get('H264_streamData', {})
            streams = h264_data.get('stream', {})
            
            if not streams:
                return None
            
            qualities = {}
            best_url = None
            
            for quality_name, quality_data in streams.items():
                if isinstance(quality_data, dict):
                    main_data = quality_data.get('main', {})
                    flv_url = main_data.get('flv', '')
                    
                    if flv_url:
                        qualities[quality_name] = flv_url
                        if not best_url:
                            best_url = flv_url
            
            if not best_url:
                return None
            
            return {
                'url': best_url,
                'title': title,
                'author': author,
                'is_live': is_live,
                'qualities': qualities
            }
            
        except Exception as e:
            logger.debug(f"Failed to parse stream state: {e}")
            return None
    
    async def _extract_offline_info(self, html: str) -> Dict[str, Any]:
        """Extract info from offline stream page."""
        title_match = re.search(r'"title":"([^"]+)"', html)
        author_match = re.search(r'"nickname":"([^"]+)"', html)
        
        return {
            'url': None,
            'title': title_match.group(1) if title_match else "Offline Stream",
            'author': author_match.group(1) if author_match else "Unknown",
            'is_live': False,
            'qualities': {}
        }
    
    async def check_live_status(self, room_url: str) -> Optional[bool]:
        """
        Quick check if stream is live (without full extraction).
        Uses HEAD request first, then minimal GET if needed.
        """
        try:
            client = await self._get_client()
            
            # Quick GET request
            response = await client.get(room_url)
            html = response.text
            
            # CAPTCHA means we can't check
            if self._is_captcha_page(html):
                return None  # Unknown
            
            # Check for stream indicators
            if '.flv' in html or '.m3u8' in html:
                if 'is_live":true' in html or 'status":2' in html:
                    return True
            
            if self._check_offline(html):
                return False
            
            # Need full extraction to determine
            result = await self._try_strategies(html)
            if result:
                return result.get('is_live', False)
            
            return False
            
        except Exception as e:
            logger.debug(f"Live check failed for {room_url}: {e}")
            return None
