"""
DouyinStream Pro - FFmpeg Helper
Utilities for FFmpeg detection and auto-download.
"""

import os
import sys
import shutil
import subprocess
import urllib.request
import zipfile
import threading
from pathlib import Path
from typing import Callable, Optional

from config.settings_manager import get_settings


# FFmpeg download URLs (essentials build - smaller)
FFMPEG_DOWNLOAD_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
FFMPEG_ESSENTIALS_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def get_ffmpeg_path() -> Optional[str]:
    """Get path to ffmpeg executable if available."""
    # Check PATH first
    ffmpeg_in_path = shutil.which("ffmpeg")
    if ffmpeg_in_path:
        return ffmpeg_in_path
    
    # Check local installation
    settings = get_settings()
    local_ffmpeg = Path(settings.get_download_path()) / "ffmpeg" / "bin" / "ffmpeg.exe"
    if local_ffmpeg.exists():
        return str(local_ffmpeg)
    
    # Check app directory
    app_ffmpeg = Path(__file__).parent.parent / "ffmpeg" / "bin" / "ffmpeg.exe"
    if app_ffmpeg.exists():
        return str(app_ffmpeg)
    
    # Check common Windows paths
    common_paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        os.path.expandvars(r"%USERPROFILE%\scoop\apps\ffmpeg\current\bin\ffmpeg.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_*\ffmpeg-*\bin\ffmpeg.exe"),
    ]
    
    for path in common_paths:
        # Handle wildcards
        if "*" in path:
            from glob import glob
            matches = glob(path)
            if matches:
                return matches[0]
        elif os.path.exists(path):
            return path
    
    return None


def is_ffmpeg_available() -> bool:
    """Check if FFmpeg is available on the system."""
    return get_ffmpeg_path() is not None


def download_ffmpeg(
    target_dir: Optional[Path] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
    on_complete: Optional[Callable[[bool, str], None]] = None
) -> None:
    """
    Download and extract FFmpeg to target directory.
    
    Args:
        target_dir: Directory to extract to (default: app/ffmpeg)
        on_progress: Callback (bytes_downloaded, total_bytes)
        on_complete: Callback (success, message)
    """
    
    def _download():
        try:
            if target_dir is None:
                dest = Path(__file__).parent.parent / "ffmpeg"
            else:
                dest = target_dir
            
            dest.mkdir(parents=True, exist_ok=True)
            zip_path = dest / "ffmpeg.zip"
            
            # Download with progress
            def reporthook(block_num, block_size, total_size):
                if on_progress:
                    downloaded = block_num * block_size
                    on_progress(downloaded, total_size)
            
            print(f"[FFmpeg] Downloading from {FFMPEG_ESSENTIALS_URL}...")
            urllib.request.urlretrieve(
                FFMPEG_ESSENTIALS_URL,
                str(zip_path),
                reporthook=reporthook
            )
            
            print("[FFmpeg] Extracting...")
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Find the inner directory name (varies by version)
                inner_dirs = [n for n in zf.namelist() if n.endswith('/') and n.count('/') == 1]
                inner_dir = inner_dirs[0] if inner_dirs else ""
                
                # Extract bin directory contents
                for member in zf.namelist():
                    if '/bin/' in member and member.endswith('.exe'):
                        # Extract to dest/bin/
                        filename = os.path.basename(member)
                        bin_dir = dest / "bin"
                        bin_dir.mkdir(exist_ok=True)
                        
                        with zf.open(member) as src:
                            with open(bin_dir / filename, 'wb') as dst:
                                dst.write(src.read())
            
            # Cleanup zip
            zip_path.unlink()
            
            # Verify
            ffmpeg_exe = dest / "bin" / "ffmpeg.exe"
            if ffmpeg_exe.exists():
                print(f"[FFmpeg] Installed to {ffmpeg_exe}")
                if on_complete:
                    on_complete(True, str(ffmpeg_exe))
            else:
                if on_complete:
                    on_complete(False, "FFmpeg extraction failed")
                    
        except Exception as e:
            print(f"[FFmpeg] Download error: {e}")
            if on_complete:
                on_complete(False, str(e))
    
    thread = threading.Thread(target=_download, daemon=True)
    thread.start()


def get_install_instructions() -> str:
    """Get FFmpeg installation instructions."""
    return """
═══════════════════════════════════════════════════════
  FFmpeg no está instalado
═══════════════════════════════════════════════════════

FFmpeg es necesario para guardar clips y combinar segmentos.

OPCIÓN 1: Instalación automática con winget (Recomendado)
   Abre PowerShell como administrador y ejecuta:
   
   winget install Gyan.FFmpeg

OPCIÓN 2: Instalación con Chocolatey
   choco install ffmpeg

OPCIÓN 3: Instalación con Scoop
   scoop install ffmpeg

OPCIÓN 4: Descarga manual
   1. Ve a: https://www.gyan.dev/ffmpeg/builds/
   2. Descarga "ffmpeg-release-essentials.zip"
   3. Extrae a C:\\ffmpeg
   4. Agrega C:\\ffmpeg\\bin al PATH

Después de instalar, reinicia DouyinStream Pro.
═══════════════════════════════════════════════════════
"""
