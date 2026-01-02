"""
DouyinStream Pro - Player Manager
Multi-player detection, fallback chain, and control.
"""

import os
import subprocess
import shutil
import winreg
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
from enum import Enum

from config.settings_manager import get_settings


class PlayerType(Enum):
    """Supported player types."""
    VLC = "vlc"
    MPV = "mpv"
    FFPLAY = "ffplay"
    EMBEDDED = "embedded"


@dataclass
class PlayerInfo:
    """Information about a detected player."""
    name: str
    type: PlayerType
    path: str
    version: Optional[str] = None
    embedded_capable: bool = False
    priority: int = 0  # Lower = higher priority


class PlayerManager:
    """
    Manages detection and launching of media players.
    Implements fallback chain: Embedded VLC -> External VLC -> MPV -> ffplay.
    """
    
    # Common installation paths
    VLC_PATHS = [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\VideoLAN\VLC\vlc.exe"),
    ]
    
    MPV_PATHS = [
        r"C:\Program Files\mpv\mpv.exe",
        r"C:\Program Files (x86)\mpv\mpv.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\mpv\mpv.exe"),
        os.path.expandvars(r"%USERPROFILE%\scoop\apps\mpv\current\mpv.exe"),
        os.path.expandvars(r"%USERPROFILE%\scoop\shims\mpv.exe"),
    ]
    
    def __init__(self) -> None:
        self._settings = get_settings()
        self._detected_players: List[PlayerInfo] = []
        self._vlc_available = False
        self._detect_all()
    
    def _detect_all(self) -> None:
        """Detect all available players."""
        self._detected_players.clear()
        
        # Detect VLC
        vlc_path = self._detect_vlc()
        if vlc_path:
            self._detected_players.append(PlayerInfo(
                name="VLC Media Player",
                type=PlayerType.VLC,
                path=vlc_path,
                embedded_capable=True,
                priority=1
            ))
            self._vlc_available = True
        
        # Detect MPV
        mpv_path = self._detect_mpv()
        if mpv_path:
            self._detected_players.append(PlayerInfo(
                name="MPV",
                type=PlayerType.MPV,
                path=mpv_path,
                embedded_capable=False,
                priority=2
            ))
        
        # Detect ffplay
        ffplay_path = self._detect_ffplay()
        if ffplay_path:
            self._detected_players.append(PlayerInfo(
                name="FFplay",
                type=PlayerType.FFPLAY,
                path=ffplay_path,
                embedded_capable=False,
                priority=3
            ))
        
        # Sort by priority
        self._detected_players.sort(key=lambda p: p.priority)
    
    def _detect_vlc(self) -> Optional[str]:
        """Detect VLC via registry and common paths."""
        # Try Windows Registry
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SOFTWARE\VideoLAN\VLC") as key:
                install_dir = winreg.QueryValueEx(key, "InstallDir")[0]
                vlc_path = os.path.join(install_dir, "vlc.exe")
                if os.path.exists(vlc_path):
                    return vlc_path
        except (WindowsError, FileNotFoundError, OSError):
            pass
        
        # Try 32-bit registry on 64-bit Windows
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SOFTWARE\WOW6432Node\VideoLAN\VLC") as key:
                install_dir = winreg.QueryValueEx(key, "InstallDir")[0]
                vlc_path = os.path.join(install_dir, "vlc.exe")
                if os.path.exists(vlc_path):
                    return vlc_path
        except (WindowsError, FileNotFoundError, OSError):
            pass
        
        # Try common paths
        for path in self.VLC_PATHS:
            if os.path.exists(path):
                return path
        
        # Try PATH
        vlc_in_path = shutil.which("vlc")
        if vlc_in_path:
            return vlc_in_path
        
        return None
    
    def _detect_mpv(self) -> Optional[str]:
        """Detect MPV via PATH and common paths."""
        # Try PATH first
        mpv_in_path = shutil.which("mpv")
        if mpv_in_path:
            return mpv_in_path
        
        # Try common paths
        for path in self.MPV_PATHS:
            if os.path.exists(path):
                return path
        
        return None
    
    def _detect_ffplay(self) -> Optional[str]:
        """Detect ffplay (comes with FFmpeg)."""
        return shutil.which("ffplay")
    
    def get_available_players(self) -> List[PlayerInfo]:
        """Get list of all detected players."""
        return self._detected_players.copy()
    
    def get_best_player(self) -> Optional[PlayerInfo]:
        """Get the highest priority available player."""
        if self._detected_players:
            return self._detected_players[0]
        return None
    
    def get_player_by_type(self, player_type: PlayerType) -> Optional[PlayerInfo]:
        """Get a specific player type if available."""
        for player in self._detected_players:
            if player.type == player_type:
                return player
        return None
    
    def is_vlc_available(self) -> bool:
        """Check if VLC is available (required for embedded mode)."""
        return self._vlc_available
    
    def get_vlc_path(self) -> Optional[str]:
        """Get VLC path if available."""
        player = self.get_player_by_type(PlayerType.VLC)
        return player.path if player else None
    
    def get_vlc_lib_path(self) -> Optional[str]:
        """Get VLC library directory for embedded mode."""
        vlc_path = self.get_vlc_path()
        if vlc_path:
            return str(Path(vlc_path).parent)
        return None
    
    def launch_external_player(self, stream_url: str, 
                               player_type: Optional[PlayerType] = None) -> bool:
        """
        Launch stream in external player.
        Uses best available if player_type not specified.
        """
        player = None
        if player_type:
            player = self.get_player_by_type(player_type)
        else:
            player = self.get_best_player()
        
        if not player:
            return False
        
        try:
            if player.type == PlayerType.VLC:
                cmd = [
                    player.path,
                    stream_url,
                    "--network-caching=1000",
                    "--file-caching=1000",
                ]
            elif player.type == PlayerType.MPV:
                cmd = [
                    player.path,
                    stream_url,
                    "--cache=yes",
                    "--demuxer-max-bytes=50M",
                ]
            elif player.type == PlayerType.FFPLAY:
                cmd = [
                    player.path,
                    stream_url,
                    "-autoexit",
                ]
            else:
                return False
            
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            return True
            
        except Exception as e:
            print(f"[PlayerManager] Launch error: {e}")
            return False
    
    def suggest_installation(self) -> str:
        """
        Suggest player installation method.
        Returns installation instructions.
        """
        return """
No se encontró ningún reproductor compatible.

Opciones de instalación:

1. VLC Media Player (Recomendado):
   • Descargar de: https://www.videolan.org/vlc/
   • O ejecutar: winget install VideoLAN.VLC

2. MPV:
   • Instalar con Scoop: scoop install mpv
   • O con Chocolatey: choco install mpv

3. FFmpeg (incluye ffplay):
   • winget install Gyan.FFmpeg
   • O: choco install ffmpeg

Después de instalar, reinicia DouyinStream Pro.
"""
    
    def offer_vlc_download(self) -> str:
        """Return VLC download URL for auto-installation."""
        return "https://get.videolan.org/vlc/3.0.20/win64/vlc-3.0.20-win64.exe"
    
    def refresh(self) -> None:
        """Re-scan for available players."""
        self._detect_all()
