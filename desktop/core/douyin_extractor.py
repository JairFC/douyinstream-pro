"""
DouyinStream Pro - Douyin Extractor
Custom extractor for Douyin live streams using browser cookies.
Bypasses Streamlink's outdated plugin.
"""

import re
import json
import logging
from typing import Optional
import requests


class DouyinExtractor:
    """
    Custom extractor for Douyin live streams.
    Uses browser cookies to bypass authentication.
    """
    
    def __init__(self, cookies: dict = None):
        """
        Initialize extractor with optional cookies.
        
        Args:
            cookies: Dictionary of cookies from browser
        """
        self.cookies = cookies or {}
        self.session = requests.Session()
        self.session.cookies.update(self.cookies)
        
        # Headers to mimic browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.douyin.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
    
    def extract_stream_url(self, room_url: str) -> Optional[dict]:
        """
        Extract stream URL and metadata from Douyin room.
        Uses adaptive multi-strategy extraction for resilience.
        Automatically resolves CAPTCHA if detected.
        
        Args:
            room_url: Douyin live room URL (e.g., https://live.douyin.com/94782239787)
            
        Returns:
            Dictionary with stream info or None if extraction fails.
        """
        try:
            from core.extraction_strategies import AdaptiveExtractor
            
            # Fetch the page
            response = self.session.get(room_url, timeout=10)
            response.raise_for_status()
            html = response.text
            
            # Detectar CAPTCHA
            if self._is_captcha_page(html):
                logging.warning("[DouyinExtractor] CAPTCHA detectado!")
                logging.warning("[DouyinExtractor] Se abrira Chrome/Edge para que lo resuelvas...")
                
                try:
                    # Resolver CAPTCHA
                    from core.captcha_solver import DouyinCaptchaSolver
                    solver = DouyinCaptchaSolver()
                    
                    cookies = solver.solve_captcha(room_url)
                    
                    # Actualizar cookies
                    self.cookies.update(cookies)
                    self.session.cookies.update(cookies)
                    
                    logging.info("[DouyinExtractor] CAPTCHA resuelto, reintentando...")
                    
                    # Reintentar con cookies válidas
                    response = self.session.get(room_url, timeout=10)
                    response.raise_for_status()
                    html = response.text
                    
                except Exception as e:
                    logging.error(f"[DouyinExtractor] Error resolviendo CAPTCHA: {e}")
                    return None
            
            # Validate HTML size (Douyin returns ~6KB empty page without auth)
            if len(html) < 10000:
                logging.warning("[DouyinExtractor] HTML muy pequeño - posible falta de autenticación")
                logging.warning("[DouyinExtractor] Tamaño: {} bytes (esperado: >100KB)".format(len(html)))
                logging.warning("[DouyinExtractor] Solución: Resuelve el CAPTCHA cuando se abra el navegador")
                return None
            
            # Use adaptive extractor
            extractor = AdaptiveExtractor()
            result = extractor.extract(html, self.cookies)
            
            if result:
                logging.info(f"[DouyinExtractor] Stream encontrado: {result.get('title')}")
                logging.info(f"[DouyinExtractor] Calidades: {list(result.get('qualities', {}).keys())}")
            else:
                logging.warning("[DouyinExtractor] No stream data found - stream may be offline")
            
            return result
            
        except Exception as e:
            logging.error(f"[DouyinExtractor] Error extracting stream: {e}")
            return None
    
    def _is_captcha_page(self, html: str) -> bool:
        """
        Detecta si la página es de CAPTCHA.
        
        Args:
            html: HTML de la página
            
        Returns:
            True si es página de CAPTCHA, False si no
        """
        return 'TTGCaptcha' in html and len(html) < 10000
    
    def _extract_render_data(self, html: str) -> Optional[dict]:
        """Extract stream data from RENDER_DATA variable."""
        try:
            # Look for RENDER_DATA in script tags
            match = re.search(r'<script[^>]*>window\._ROUTER_DATA\s*=\s*({.+?})</script>', html)
            if not match:
                match = re.search(r'<script[^>]*>self\.__pace_f\.push\(\[1,"(\w+:.+?)"\]\)</script>', html)
                if not match:
                    return None
            
            data_str = match.group(1)
            
            # Parse JSON
            if data_str.startswith('"'):
                # Unescape and parse
                data_str = data_str.strip('"')
                data_str = re.sub(r'^\\w+:', '', data_str)
            
            data = json.loads(data_str)
            
            # Navigate to stream data
            # Structure varies, try common paths
            stream_info = self._parse_stream_data(data)
            return stream_info
            
        except Exception as e:
            logging.debug(f"[DouyinExtractor] RENDER_DATA extraction failed: {e}")
            return None
    
    def _extract_pace_data(self, html: str) -> Optional[dict]:
        """Extract stream data from __pace_f.push calls."""
        try:
            # Find all __pace_f.push calls
            matches = re.findall(r'self\.__pace_f\.push\(\[\d+,"(\w+:.+?)"\]\)</script>', html)
            
            for match in matches:
                if 'state' in match and 'streamStore' in match:
                    # Remove prefix and parse
                    data_str = re.sub(r'^\w+:', '', match)
                    data = json.loads(data_str)
                    
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and 'state' in item:
                                stream_info = self._parse_stream_data(item.get('state', {}))
                                if stream_info:
                                    return stream_info
            
            return None
            
        except Exception as e:
            logging.debug(f"[DouyinExtractor] __pace_f extraction failed: {e}")
            return None
    
    def _extract_json_data(self, html: str) -> Optional[dict]:
        """Try to extract any JSON data with stream URLs."""
        try:
            # Look for FLV or M3U8 URLs in any JSON
            flv_matches = re.findall(r'"(https?://[^"]+\.flv[^"]*)"', html)
            m3u8_matches = re.findall(r'"(https?://[^"]+\.m3u8[^"]*)"', html)
            
            if flv_matches or m3u8_matches:
                # Prefer FLV over M3U8 for better compatibility
                url = flv_matches[0] if flv_matches else m3u8_matches[0]
                
                return {
                    'url': url,
                    'title': 'Douyin Live',
                    'author': 'Unknown',
                    'is_live': True,
                    'qualities': {'best': url}
                }
            
            return None
            
        except Exception as e:
            logging.debug(f"[DouyinExtractor] JSON extraction failed: {e}")
            return None
    
    def _parse_stream_data(self, data: dict) -> Optional[dict]:
        """Parse stream data from various JSON structures."""
        try:
            # Try to find room info
            room_info = data.get('roomStore', {}).get('roomInfo', {})
            room = room_info.get('room', {})
            anchor = room_info.get('anchor', {})
            
            title = room.get('title', 'Douyin Live')
            author = anchor.get('nickname', 'Unknown')
            status = room.get('status', 0)
            is_live = status == 2
            
            # Try to find stream URLs
            stream_store = data.get('streamStore', {})
            stream_data = stream_store.get('streamData', {}).get('H264_streamData', {}).get('stream', {})
            
            if not stream_data:
                return None
            
            qualities = {}
            best_url = None
            
            for quality_name, quality_data in stream_data.items():
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
            logging.debug(f"[DouyinExtractor] Stream data parsing failed: {e}")
            return None
