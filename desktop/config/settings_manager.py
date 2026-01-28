"""
DouyinStream Pro - Settings Manager
Singleton pattern for centralized configuration management.
"""

import json
import os
import winreg
from pathlib import Path
from typing import Any, Callable, Optional
from threading import Lock


class SettingsManager:
    """
    Singleton configuration manager with auto-persistence and observer pattern.
    Handles VLC/MPV detection, user preferences, and runtime settings.
    """
    
    _instance: Optional['SettingsManager'] = None
    _lock: Lock = Lock()
    
    # Default settings
    DEFAULTS: dict[str, Any] = {
        "player_mode": "embedded",  # "embedded" or "external"
        "external_player_path": "",
        "preferred_player": "vlc",  # "vlc", "mpv", "ffplay"
        "default_quality": "best",
        "clip_buffer_minutes": 3,
        "segment_duration_sec": 10,
        "download_path": str(Path.home() / "Downloads" / "Douyin_Rips"),
        "ui_language": "es",
        "theme": "dark",
        "auto_clipboard": True,
        "show_console": False,
        "volume": 80,
        "window_geometry": "1200x800",
    }
    
    # Common VLC installation paths on Windows
    VLC_SEARCH_PATHS: list[str] = [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\VideoLAN\VLC\vlc.exe"),
        os.path.expandvars(r"%APPDATA%\VLC\vlc.exe"),
    ]
    
    # Common MPV paths
    MPV_SEARCH_PATHS: list[str] = [
        r"C:\Program Files\mpv\mpv.exe",
        r"C:\Program Files (x86)\mpv\mpv.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\mpv\mpv.exe"),
        os.path.expandvars(r"%USERPROFILE%\scoop\apps\mpv\current\mpv.exe"),
    ]
    
    def __new__(cls) -> 'SettingsManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
            
        self._initialized = True
        self._observers: list[Callable[[str, Any], None]] = []
        self._settings: dict[str, Any] = {}
        
        # Setup data directory
        self._data_dir = Path(__file__).parent.parent / "data"
        self._data_dir.mkdir(exist_ok=True)
        self._settings_file = self._data_dir / "settings.json"
        
        # Load or create settings
        self._load_settings()
        
        # Auto-detect players if not configured
        if not self._settings.get("external_player_path"):
            detected = self._detect_vlc() or self._detect_mpv()
            if detected:
                self._settings["external_player_path"] = detected
                self._save_settings()
    
    def _load_settings(self) -> None:
        """Load settings from JSON file or create defaults."""
        if self._settings_file.exists():
            try:
                with open(self._settings_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge with defaults to handle new settings
                    self._settings = {**self.DEFAULTS, **loaded}
            except (json.JSONDecodeError, IOError):
                self._settings = self.DEFAULTS.copy()
        else:
            self._settings = self.DEFAULTS.copy()
            self._save_settings()
    
    def _save_settings(self) -> None:
        """Persist settings to JSON file."""
        try:
            with open(self._settings_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[SettingsManager] Error saving settings: {e}")
    
    def _detect_vlc(self) -> Optional[str]:
        """
        Detect VLC installation via Windows Registry and common paths.
        Returns path to vlc.exe if found.
        """
        # Try Windows Registry first
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SOFTWARE\VideoLAN\VLC") as key:
                install_dir = winreg.QueryValueEx(key, "InstallDir")[0]
                vlc_path = os.path.join(install_dir, "vlc.exe")
                if os.path.exists(vlc_path):
                    return vlc_path
        except (WindowsError, FileNotFoundError):
            pass
        
        # Try common paths
        for path in self.VLC_SEARCH_PATHS:
            if os.path.exists(path):
                return path
        
        return None
    
    def _detect_mpv(self) -> Optional[str]:
        """
        Detect MPV installation via PATH and common locations.
        Returns path to mpv.exe if found.
        """
        # Check PATH
        import shutil
        mpv_in_path = shutil.which("mpv")
        if mpv_in_path:
            return mpv_in_path
        
        # Try common paths
        for path in self.MPV_SEARCH_PATHS:
            if os.path.exists(path):
                return path
        
        return None
    
    def _detect_ffplay(self) -> Optional[str]:
        """Detect ffplay (comes with FFmpeg)."""
        import shutil
        return shutil.which("ffplay")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self._settings.get(key, default if default is not None else self.DEFAULTS.get(key))
    
    def set(self, key: str, value: Any) -> None:
        """Set a setting value and notify observers."""
        old_value = self._settings.get(key)
        if old_value != value:
            self._settings[key] = value
            self._save_settings()
            self._notify_observers(key, value)
    
    def get_all(self) -> dict[str, Any]:
        """Get all settings as a dictionary."""
        return self._settings.copy()
    
    def add_observer(self, callback: Callable[[str, Any], None]) -> None:
        """Add an observer to be notified of setting changes."""
        if callback not in self._observers:
            self._observers.append(callback)
    
    def remove_observer(self, callback: Callable[[str, Any], None]) -> None:
        """Remove an observer."""
        if callback in self._observers:
            self._observers.remove(callback)
    
    def _notify_observers(self, key: str, value: Any) -> None:
        """Notify all observers of a setting change."""
        for callback in self._observers:
            try:
                callback(key, value)
            except Exception as e:
                print(f"[SettingsManager] Observer error: {e}")
    
    def get_available_players(self) -> list[dict[str, str]]:
        """
        Get list of all available media players.
        Returns list of dicts with 'name', 'type', and 'path'.
        """
        players = []
        
        # Check VLC
        vlc_path = self._detect_vlc()
        if vlc_path:
            players.append({
                "name": "VLC Media Player",
                "type": "vlc",
                "path": vlc_path,
                "embedded_capable": True
            })
        
        # Check MPV
        mpv_path = self._detect_mpv()
        if mpv_path:
            players.append({
                "name": "MPV",
                "type": "mpv", 
                "path": mpv_path,
                "embedded_capable": False
            })
        
        # Check ffplay
        ffplay_path = self._detect_ffplay()
        if ffplay_path:
            players.append({
                "name": "FFplay",
                "type": "ffplay",
                "path": ffplay_path,
                "embedded_capable": False
            })
        
        return players
    
    def get_download_path(self) -> Path:
        """Get download path, creating it if necessary."""
        path = Path(self.get("download_path"))
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_temp_path(self) -> Path:
        """Get temp path for buffer segments."""
        temp_path = Path(os.environ.get("TEMP", "/tmp")) / "douyinstream"
        temp_path.mkdir(parents=True, exist_ok=True)
        return temp_path


# Convenience function to get singleton instance
def get_settings() -> SettingsManager:
    """Get the singleton SettingsManager instance."""
    return SettingsManager()
