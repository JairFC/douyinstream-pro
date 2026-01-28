"""
DouyinStream Pro - History Manager
Manages stream history with aliases and favorites.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Callable
from threading import Lock

from config.settings_manager import get_settings


@dataclass
class HistoryItem:
    """Represents a history entry."""
    url: str
    title: str
    alias: str
    streamer: str
    last_played: str  # ISO format
    play_count: int
    is_favorite: bool
    quality: str
    thumbnail_path: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'HistoryItem':
        return cls(**data)


class HistoryManager:
    """
    Manages stream history and favorites.
    Persists to JSON files.
    """
    
    MAX_HISTORY = 50  # Maximum history items
    
    def __init__(self) -> None:
        self._settings = get_settings()
        self._lock = Lock()
        
        self._data_dir = Path(__file__).parent.parent / "data"
        self._data_dir.mkdir(exist_ok=True)
        
        self._history_file = self._data_dir / "history.json"
        self._history: List[HistoryItem] = []
        
        self._callbacks: List[Callable[[], None]] = []
        
        self._load_history()
    
    def _load_history(self) -> None:
        """Load history from JSON file."""
        if self._history_file.exists():
            try:
                with open(self._history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._history = [HistoryItem.from_dict(item) for item in data]
            except (json.JSONDecodeError, IOError, TypeError) as e:
                print(f"[HistoryManager] Load error: {e}")
                self._history = []
        else:
            self._history = []
    
    def _save_history(self) -> None:
        """Save history to JSON file."""
        try:
            with open(self._history_file, 'w', encoding='utf-8') as f:
                data = [item.to_dict() for item in self._history]
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[HistoryManager] Save error: {e}")
    
    def _notify_change(self) -> None:
        """Notify observers of history change."""
        for callback in self._callbacks:
            try:
                callback()
            except Exception:
                pass
    
    def add_callback(self, callback: Callable[[], None]) -> None:
        """Add change listener."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def add_entry(self, url: str, streamer: str = "", 
                  quality: str = "best", alias: str = "") -> HistoryItem:
        """
        Add or update a history entry.
        Returns the created/updated item.
        """
        with self._lock:
            # Check if URL already exists
            existing = self.find_by_url(url)
            
            if existing:
                # Update existing entry
                existing.last_played = datetime.now().isoformat()
                existing.play_count += 1
                if alias:
                    existing.alias = alias
                if quality:
                    existing.quality = quality
                
                # Move to front
                self._history.remove(existing)
                self._history.insert(0, existing)
                
                self._save_history()
                self._notify_change()
                return existing
            
            # Create new entry
            item = HistoryItem(
                url=url,
                title=streamer or self._extract_title(url),
                alias=alias or "",
                streamer=streamer or self._extract_title(url),
                last_played=datetime.now().isoformat(),
                play_count=1,
                is_favorite=False,
                quality=quality,
                thumbnail_path=None
            )
            
            self._history.insert(0, item)
            
            # Trim history if too long (keep favorites)
            while len(self._history) > self.MAX_HISTORY:
                # Find last non-favorite to remove
                for i in range(len(self._history) - 1, -1, -1):
                    if not self._history[i].is_favorite:
                        del self._history[i]
                        break
                else:
                    break  # All are favorites
            
            self._save_history()
            self._notify_change()
            return item
    
    def _extract_title(self, url: str) -> str:
        """Extract a display title from URL."""
        import re
        
        # Try room ID
        match = re.search(r'live\.douyin\.com/(\d+)', url)
        if match:
            return f"Room {match.group(1)}"
        
        # Try TikTok username
        match = re.search(r'tiktok\.com/@([\w.]+)', url)
        if match:
            return f"@{match.group(1)}"
        
        # Try v.douyin short link
        match = re.search(r'v\.douyin\.com/(\w+)', url)
        if match:
            return f"Douyin {match.group(1)}"
        
        return "Stream"
    
    def find_by_url(self, url: str) -> Optional[HistoryItem]:
        """Find history item by URL."""
        for item in self._history:
            if item.url == url:
                return item
        return None
    
    def set_alias(self, url: str, alias: str) -> bool:
        """Set alias for a history item."""
        with self._lock:
            item = self.find_by_url(url)
            if item:
                item.alias = alias
                self._save_history()
                self._notify_change()
                return True
            return False
    
    def toggle_favorite(self, url: str) -> bool:
        """Toggle favorite status. Returns new status."""
        with self._lock:
            item = self.find_by_url(url)
            if item:
                item.is_favorite = not item.is_favorite
                self._save_history()
                self._notify_change()
                return item.is_favorite
            return False
    
    def set_favorite(self, url: str, is_favorite: bool) -> None:
        """Set favorite status explicitly."""
        with self._lock:
            item = self.find_by_url(url)
            if item:
                item.is_favorite = is_favorite
                self._save_history()
                self._notify_change()
    
    def remove_entry(self, url: str) -> bool:
        """Remove a history entry."""
        with self._lock:
            item = self.find_by_url(url)
            if item:
                self._history.remove(item)
                self._save_history()
                self._notify_change()
                return True
            return False
    
    def get_all(self) -> List[HistoryItem]:
        """Get all history items (newest first)."""
        return self._history.copy()
    
    def get_favorites(self) -> List[HistoryItem]:
        """Get only favorite items."""
        return [item for item in self._history if item.is_favorite]
    
    def get_recent(self, limit: int = 10) -> List[HistoryItem]:
        """Get recent non-favorite items."""
        items = [item for item in self._history if not item.is_favorite]
        return items[:limit]
    
    def clear_non_favorites(self) -> None:
        """Clear all non-favorite history."""
        with self._lock:
            self._history = [item for item in self._history if item.is_favorite]
            self._save_history()
            self._notify_change()
    
    def export_to_json(self, filepath: Path) -> bool:
        """Export history to external JSON file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                data = [item.to_dict() for item in self._history]
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except IOError:
            return False
    
    def import_from_json(self, filepath: Path) -> int:
        """Import history from JSON file. Returns count of imported items."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                imported = 0
                for item_data in data:
                    if 'url' in item_data:
                        item = HistoryItem.from_dict(item_data)
                        if not self.find_by_url(item.url):
                            with self._lock:
                                self._history.append(item)
                            imported += 1
                
                if imported > 0:
                    self._save_history()
                    self._notify_change()
                
                return imported
        except (json.JSONDecodeError, IOError, TypeError):
            return 0
