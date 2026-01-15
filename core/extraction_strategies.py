"""
DouyinStream Pro - Extraction Strategies
Multi-strategy extraction system for resilient stream URL detection.
"""

import re
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from datetime import datetime
import os


class ExtractionStrategy(ABC):
    """Base class for extraction strategies."""
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.priority = 0  # Lower = higher priority
        self.success_count = 0
        self.failure_count = 0
    
    @abstractmethod
    def can_extract(self, html: str) -> bool:
        """Check if this strategy can be applied to the HTML."""
        pass
    
    @abstractmethod
    def extract(self, html: str, cookies: dict = None) -> Optional[Dict]:
        """
        Extract stream data from HTML.
        
        Returns:
            dict with keys: url, title, author, is_live, qualities
            None if extraction fails
        """
        pass
    
    def log_success(self):
        """Log successful extraction."""
        self.success_count += 1
        logging.info(f"[{self.name}] ✓ Success (total: {self.success_count})")
    
    def log_failure(self, error: str = ""):
        """Log failed extraction."""
        self.failure_count += 1
        logging.debug(f"[{self.name}] ✗ Failed (total: {self.failure_count}): {error}")


class DirectURLStrategy(ExtractionStrategy):
    """
    Strategy 1: Direct URL extraction using regex.
    Most robust - doesn't depend on JSON structure.
    """
    
    def __init__(self):
        super().__init__()
        self.priority = 1  # Highest priority
    
    def can_extract(self, html: str) -> bool:
        """Check if FLV or M3U8 URLs are present."""
        return bool(re.search(r'\.flv["\']', html) or re.search(r'\.m3u8["\']', html))
    
    def extract(self, html: str, cookies: dict = None) -> Optional[Dict]:
        """Extract URLs directly from HTML."""
        try:
            # Find FLV URLs
            flv_urls = re.findall(r'"(https?://[^"]+\.flv[^"]*)"', html)
            
            # Find M3U8 URLs
            m3u8_urls = re.findall(r'"(https?://[^"]+\.m3u8[^"]*)"', html)
            
            if not flv_urls and not m3u8_urls:
                self.log_failure("No URLs found")
                return None
            
            # Prefer FLV over M3U8
            best_url = flv_urls[0] if flv_urls else m3u8_urls[0]
            
            # Extract quality variants
            qualities = {}
            for url in (flv_urls + m3u8_urls)[:10]:
                quality_match = re.search(r'_(sd|hd|uhd|origin|ld)\.', url)
                if quality_match:
                    quality = quality_match.group(1)
                    if quality not in qualities:
                        qualities[quality] = url
            
            if not qualities:
                qualities['best'] = best_url
            
            # Extract metadata
            title = "Douyin Live"
            author = "Unknown"
            
            title_match = re.search(r'"title":"([^"]+)"', html)
            if title_match:
                title = title_match.group(1)
            
            author_match = re.search(r'"nickname":"([^"]+)"', html)
            if author_match:
                author = author_match.group(1)
            
            self.log_success()
            
            return {
                'url': best_url,
                'title': title,
                'author': author,
                'is_live': True,
                'qualities': qualities
            }
            
        except Exception as e:
            self.log_failure(str(e))
            return None


class JSONWrapperStrategy(ExtractionStrategy):
    """
    Strategy 2: JSON parsing with wrapper handling.
    Handles new format: d:["$","$L12",null,{...}]
    """
    
    def __init__(self):
        super().__init__()
        self.priority = 2
    
    def can_extract(self, html: str) -> bool:
        """Check if __pace_f with streamStore is present."""
        return bool(re.search(r'__pace_f.*streamStore', html))
    
    def extract(self, html: str, cookies: dict = None) -> Optional[Dict]:
        """Extract from JSON with wrapper."""
        try:
            # Find __pace_f.push calls with streamStore
            pattern = re.compile(r'self\.__pace_f\.push\(\[(\d+),"(\w+:.+?)"\]\)</script>')
            matches = pattern.findall(html)
            
            stream_matches = [m for m in matches if 'streamStore' in m[1]]
            
            if not stream_matches:
                self.log_failure("No streamStore found")
                return None
            
            data_str = stream_matches[0][1]
            
            # Remove prefix (e.g., "d:")
            data_str = re.sub(r'^\w+:', '', data_str)
            
            # Unescape quotes
            data_str = data_str.replace('\\"', '"')
            
            # Parse JSON
            data = json.loads(data_str)
            
            # Handle wrapper format: ["$", "$L12", null, {...}]
            state = None
            if isinstance(data, list):
                for item in reversed(data):
                    if isinstance(item, dict) and 'state' in item:
                        state = item['state']
                        break
            
            if not state:
                self.log_failure("No state found in JSON")
                return None
            
            # Extract room info
            room_store = state.get('roomStore', {})
            room_info = room_store.get('roomInfo', {})
            room = room_info.get('room', {})
            anchor = room_info.get('anchor', {})
            
            title = room.get('title', 'Douyin Live')
            author = anchor.get('nickname', 'Unknown')
            status = room.get('status', 0)
            is_live = (status == 2)
            
            # Extract stream URLs
            stream_store = state.get('streamStore', {})
            stream_data = stream_store.get('streamData', {})
            h264_data = stream_data.get('H264_streamData', {})
            stream = h264_data.get('stream', {})
            
            if not stream:
                self.log_failure("No stream data")
                return None
            
            qualities = {}
            best_url = None
            
            for quality_name, quality_data in stream.items():
                if isinstance(quality_data, dict):
                    main_data = quality_data.get('main', {})
                    flv_url = main_data.get('flv', '')
                    
                    if flv_url:
                        qualities[quality_name] = flv_url
                        if not best_url:
                            best_url = flv_url
            
            if not best_url:
                self.log_failure("No URLs in stream data")
                return None
            
            self.log_success()
            
            return {
                'url': best_url,
                'title': title,
                'author': author,
                'is_live': is_live,
                'qualities': qualities
            }
            
        except Exception as e:
            self.log_failure(str(e))
            return None


class LegacyJSONStrategy(ExtractionStrategy):
    """
    Strategy 3: Legacy JSON parsing (old format).
    Fallback in case Douyin reverts changes.
    """
    
    def __init__(self):
        super().__init__()
        self.priority = 3  # Lowest priority
    
    def can_extract(self, html: str) -> bool:
        """Check if __pace_f is present."""
        return bool(re.search(r'__pace_f', html))
    
    def extract(self, html: str, cookies: dict = None) -> Optional[Dict]:
        """Extract from legacy JSON format (no wrapper)."""
        try:
            pattern = re.compile(r'self\.__pace_f\.push\(\[(\d+),"(\w+:.+?)"\]\)</script>')
            matches = pattern.findall(html)
            
            stream_matches = [m for m in matches if 'streamStore' in m[1]]
            
            if not stream_matches:
                self.log_failure("No streamStore found")
                return None
            
            data_str = stream_matches[0][1]
            data_str = re.sub(r'^\w+:', '', data_str)
            
            # Try direct parse (no wrapper)
            data = json.loads(data_str)
            
            # Expect direct array format
            if not isinstance(data, list):
                self.log_failure("Not a list")
                return None
            
            for item in data:
                if isinstance(item, dict) and 'state' in item:
                    # Same extraction logic as JSONWrapperStrategy
                    state = item['state']
                    
                    room_store = state.get('roomStore', {})
                    room_info = room_store.get('roomInfo', {})
                    room = room_info.get('room', {})
                    
                    stream_store = state.get('streamStore', {})
                    stream_data = stream_store.get('streamData', {})
                    h264_data = stream_data.get('H264_streamData', {})
                    stream = h264_data.get('stream', {})
                    
                    if stream:
                        best_url = None
                        qualities = {}
                        
                        for quality_name, quality_data in stream.items():
                            if isinstance(quality_data, dict):
                                flv_url = quality_data.get('main', {}).get('flv', '')
                                if flv_url:
                                    qualities[quality_name] = flv_url
                                    if not best_url:
                                        best_url = flv_url
                        
                        if best_url:
                            self.log_success()
                            return {
                                'url': best_url,
                                'title': room.get('title', 'Douyin Live'),
                                'author': room_info.get('anchor', {}).get('nickname', 'Unknown'),
                                'is_live': True,
                                'qualities': qualities
                            }
            
            self.log_failure("No valid data found")
            return None
            
        except Exception as e:
            self.log_failure(str(e))
            return None


class AdaptiveExtractor:
    """
    Adaptive extractor that tries multiple strategies.
    Caches the last working strategy for optimization.
    """
    
    def __init__(self):
        self.strategies: List[ExtractionStrategy] = [
            DirectURLStrategy(),
            JSONWrapperStrategy(),
            LegacyJSONStrategy(),
        ]
        
        # Sort by priority
        self.strategies.sort(key=lambda s: s.priority)
        
        self.last_working_strategy: Optional[str] = None
        self.cache_file = os.path.join(os.path.dirname(__file__), '.strategy_cache.json')
        
        self._load_cache()
    
    def _load_cache(self):
        """Load cached strategy info."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                    self.last_working_strategy = cache.get('last_working_strategy')
                    logging.debug(f"[AdaptiveExtractor] Loaded cache: {self.last_working_strategy}")
        except Exception as e:
            logging.debug(f"[AdaptiveExtractor] Cache load failed: {e}")
    
    def _save_cache(self, strategy_name: str):
        """Save successful strategy to cache."""
        try:
            cache = {
                'last_working_strategy': strategy_name,
                'last_success': datetime.now().isoformat(),
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache, f)
            logging.debug(f"[AdaptiveExtractor] Saved cache: {strategy_name}")
        except Exception as e:
            logging.debug(f"[AdaptiveExtractor] Cache save failed: {e}")
    
    def extract(self, html: str, cookies: dict = None) -> Optional[Dict]:
        """
        Try strategies in order until one succeeds.
        Prioritizes last working strategy.
        """
        logging.info("[AdaptiveExtractor] Starting extraction...")
        
        # Try last working strategy first
        if self.last_working_strategy:
            for strategy in self.strategies:
                if strategy.name == self.last_working_strategy:
                    logging.info(f"[AdaptiveExtractor] Trying cached strategy: {strategy.name}")
                    if strategy.can_extract(html):
                        result = strategy.extract(html, cookies)
                        if result:
                            logging.info(f"[AdaptiveExtractor] ✓ Cached strategy worked!")
                            return result
                    break
        
        # Try all strategies in priority order
        for strategy in self.strategies:
            if strategy.name == self.last_working_strategy:
                continue  # Already tried
            
            logging.info(f"[AdaptiveExtractor] Trying strategy: {strategy.name}")
            
            if not strategy.can_extract(html):
                logging.debug(f"[AdaptiveExtractor] {strategy.name} cannot extract (pre-check failed)")
                continue
            
            result = strategy.extract(html, cookies)
            
            if result:
                logging.info(f"[AdaptiveExtractor] ✓ Success with {strategy.name}!")
                self.last_working_strategy = strategy.name
                self._save_cache(strategy.name)
                return result
        
        logging.error("[AdaptiveExtractor] All strategies failed")
        return None
    
    def get_stats(self) -> Dict:
        """Get statistics for all strategies."""
        return {
            strategy.name: {
                'success': strategy.success_count,
                'failure': strategy.failure_count,
                'priority': strategy.priority
            }
            for strategy in self.strategies
        }
