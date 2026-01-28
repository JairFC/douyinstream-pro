"""
DouyinStream Pro - Recorder
DVR recording and clip buffer system using ring buffer with segments.
Uses Python module execution for streamlink to avoid PATH issues.
"""

import os
import sys
import subprocess
import threading
import time
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Set
from collections import deque

from config.settings_manager import get_settings
from core.process_manager import register_process, unregister_process, kill_process_tree


@dataclass
class Segment:
    """Represents a recorded segment."""
    path: Path
    timestamp: datetime
    duration_sec: float
    size_bytes: int
    is_active: bool = False  # True if currently being written


class RecorderState:
    """Enum-like class for recorder states."""
    IDLE = "idle"
    RECORDING = "recording"
    BUFFERING = "buffering"


def get_streamlink_cmd() -> list[str]:
    """Get the command to run streamlink, handling PATH issues."""
    # First try direct executable
    streamlink_path = shutil.which("streamlink")
    if streamlink_path:
        return [streamlink_path]
    
    # Fallback to python -m streamlink
    return [sys.executable, "-m", "streamlink"]


def get_ffmpeg_cmd() -> list[str]:
    """Get the command to run ffmpeg."""
    # Try using the helper module first
    try:
        from core.ffmpeg_helper import get_ffmpeg_path, get_install_instructions
        ffmpeg_path = get_ffmpeg_path()
        if ffmpeg_path:
            return [ffmpeg_path]
    except ImportError:
        pass
    
    # Fallback detection
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return [ffmpeg_path]
    
    # Try common locations on Windows
    common_paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        os.path.expandvars(r"%USERPROFILE%\scoop\apps\ffmpeg\current\bin\ffmpeg.exe"),
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return [path]
    
    # Check local app directory
    local_ffmpeg = Path(__file__).parent.parent / "ffmpeg" / "bin" / "ffmpeg.exe"
    if local_ffmpeg.exists():
        return [str(local_ffmpeg)]
    
    # Will fail if not found
    return ["ffmpeg"]


class Recorder:
    """
    DVR and clip buffer system.
    Uses ring buffer with segments for efficient memory usage.
    """
    
    def __init__(self) -> None:
        self._settings = get_settings()
        self._state = RecorderState.IDLE
        self._segments: deque[Segment] = deque()
        self._current_url: str = ""
        self._current_quality: str = "best"
        self._stream_url: str = ""  # Direct stream URL for FFmpeg recording
        self._record_process: Optional[subprocess.Popen] = None
        self._buffer_process: Optional[subprocess.Popen] = None
        self._streamlink_process: Optional[subprocess.Popen] = None  # Process feeding FFmpeg
        self._clip_process: Optional[subprocess.Popen] = None
        self._buffer_thread: Optional[threading.Thread] = None
        self._stop_buffer_flag = threading.Event()
        self._lock = threading.Lock()
        
        self._callbacks: dict[str, list[Callable]] = {
            "on_state_change": [],
            "on_segment_added": [],
            "on_recording_complete": [],
            "on_clip_saved": [],
            "on_error": [],
            "on_log": [],
        }
        
        # Ensure temp directory exists
        self._temp_dir = self._settings.get_temp_path()
        self._cleanup_old_segments()
    
    def _log(self, message: str, level: str = "INFO") -> None:
        """Emit log message."""
        formatted = f"[Recorder] [{level}] {message}"
        for callback in self._callbacks.get("on_log", []):
            try:
                callback(formatted)
            except Exception:
                pass
    
    def _emit(self, event: str, *args) -> None:
        """Emit event to callbacks."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args)
            except Exception as e:
                self._log(f"Callback error: {e}", "ERROR")
    
    def add_callback(self, event: str, callback: Callable) -> None:
        """Add event callback."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def _cleanup_old_segments(self) -> None:
        """Remove old segment files from temp directory."""
        try:
            for f in self._temp_dir.glob("segment_*.ts"):
                f.unlink()
        except Exception as e:
            self._log(f"Cleanup error: {e}", "WARNING")
    
    def _get_segment_filename(self) -> str:
        """Generate unique segment filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"segment_{timestamp}.ts"
    
    def _get_max_segments(self) -> int:
        """Calculate max segments based on buffer settings."""
        buffer_minutes = self._settings.get("clip_buffer_minutes", 3)
        segment_duration = self._settings.get("segment_duration_sec", 10)
        return int((buffer_minutes * 60) / segment_duration)
    
    def start_buffer(self, url: str, quality: str = "best", stream_url: str = "") -> bool:
        """
        Start continuous buffering using FFmpeg segmentation.
        """
        # If already buffering same URL, just update metadata if needed
        if self._state == RecorderState.BUFFERING:
            if self._current_url == url:
                self._log("Buffer ya activo para este stream")
                return True
            else:
                self.stop_buffer()
                self.clear_buffer()
        
        self._current_url = url
        self._current_quality = quality
        self._stream_url = stream_url
        self._state = RecorderState.BUFFERING
        self._stop_buffer_flag.clear()
        self._emit("on_state_change", self._state)
        
        # Start monitoring thread first
        self._buffer_thread = threading.Thread(target=self._buffer_loop, daemon=True)
        self._buffer_thread.start()
        
        # Launch continuous FFmpeg process
        self._start_ffmpeg_buffer_process()
        
        return True

    def _start_ffmpeg_buffer_process(self) -> None:
        """Launch the main FFmpeg process for continuous segmentation."""
        try:
            segment_duration = self._settings.get("segment_duration_sec", 5)  # Shorter segments for better precision
            ffmpeg_cmd = get_ffmpeg_cmd()
            
            # Output pattern for segments
            segment_pattern = str(self._temp_dir / "segment_%Y%m%d_%H%M%S.ts")
            list_file = self._temp_dir / "segments.csv"
            
            # Input source
            input_args = []
            if self._stream_url:
                input_args = ["-i", self._stream_url]
            else:
                # Use streamlink pipe if no direct URL
                streamlink_cmd = get_streamlink_cmd()
                sl_cmd = streamlink_cmd + [
                    "--stdout",
                    "--url", self._current_url,
                    "--default-stream", self._current_quality
                ]
                # Start streamlink process to feed ffmpeg
                # Note: We don't track this strictly as a child of ffmpeg, but we should close it
                self._streamlink_process = register_process(subprocess.Popen(
                    sl_cmd, 
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                ))
                input_args = ["-i", "pipe:0"]
            
            cmd = ffmpeg_cmd + [
                "-y",
                "-hide_banner",
                "-loglevel", "error",
            ] + input_args + [
                "-c", "copy",
                "-f", "segment",
                "-segment_time", str(segment_duration),
                "-segment_list", str(list_file),
                "-segment_list_type", "csv",
                "-segment_list_size", "0",  # Keep all in list (we manage deletion)
                "-strftime", "1",
                "-reset_timestamps", "1",
                segment_pattern
            ]
            
            stdin = self._streamlink_process.stdout if not self._stream_url else None
            
            self._log(f"Iniciando FFmpeg continuo (segmentos de {segment_duration}s)...")
            
            self._buffer_process = register_process(subprocess.Popen(
                cmd,
                stdin=stdin,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            ))
            
        except Exception as e:
            self._log(f"Error iniciando FFmpeg: {e}", "ERROR")
            self._state = RecorderState.IDLE

    def _buffer_loop(self) -> None:
        """
        Watch the segment list file and update internal buffer state.
        Never restarts FFmpeg - just manages the generated files.
        """
        list_file = self._temp_dir / "segments.csv"
        processed_files = set()
        max_segments = self._get_max_segments()
        
        while self._state == RecorderState.BUFFERING and not self._stop_buffer_flag.is_set():
            try:
                if not list_file.exists():
                    time.sleep(0.5)
                    continue
                
                # Check process health
                if self._buffer_process and self._buffer_process.poll() is not None:
                    self._log("Proceso FFmpeg terminó inesperadamente. Reiniciando...", "WARNING")
                    self._start_ffmpeg_buffer_process()
                    time.sleep(1)
                    continue

                # Read segment list
                with open(list_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                new_segments_found = False
                
                for line in lines:
                    if not line.strip(): 
                        continue
                        
                    # Format: filename,start_time,end_time
                    parts = line.strip().split(',')
                    if len(parts) >= 1:
                        filename = parts[0]
                        file_path = self._temp_dir / filename
                        
                        if filename not in processed_files and file_path.exists():
                            # New completed segment
                            processed_files.add(filename)
                            
                            try:
                                size = file_path.stat().st_size
                                # Parse timestamp from filename to be safe "segment_YYYYMMDD_HHMMSS.ts"
                                # But using file mod time is easier/safer
                                timestamp = datetime.fromtimestamp(file_path.stat().st_mtime)
                                
                                # Default duration if not parsed
                                duration = float(parts[2]) - float(parts[1]) if len(parts) >= 3 else 5.0
                                
                                seg = Segment(
                                    path=file_path,
                                    timestamp=timestamp,
                                    duration_sec=duration,
                                    size_bytes=size
                                )
                                
                                with self._lock:
                                    self._segments.append(seg)
                                    new_segments_found = True
                                    
                                    # Ring buffer maintenance
                                    while len(self._segments) > max_segments:
                                        old = self._segments.popleft()
                                        if old.path.exists():
                                            try:
                                                old.path.unlink()
                                                processed_files.discard(old.path.name)
                                            except Exception:
                                                pass
                            except Exception as e:
                                pass # File might be locked or gone
                
                if new_segments_found:
                    with self._lock:
                        count = len(self._segments)
                        duration = sum(s.duration_sec for s in self._segments)
                        self._emit("on_segment_added", count, max_segments)
                
                time.sleep(0.5)
                
            except Exception as e:
                # self._log(f"Error monitor buffer: {e}")
                time.sleep(1)
    
    def stop_buffer(self) -> None:
        """Stop buffering (but keep segments for clip saving)."""
        if self._state == RecorderState.BUFFERING:
            self._stop_buffer_flag.set()
            self._state = RecorderState.IDLE
            
            # Aggressively kill buffer process and all children
            if self._buffer_process:
                kill_process_tree(self._buffer_process)
                self._buffer_process = None
            
            # Kill feeding process if exists
            if self._streamlink_process:
                kill_process_tree(self._streamlink_process)
                self._streamlink_process = None
                
            self._emit("on_state_change", self._state)
            self._log("Buffer detenido")
    
    def save_clip(self, filename: Optional[str] = None, clear_after: bool = True) -> Optional[Path]:
        """
        Save current buffer as clip (like NVIDIA Instant Replay).
        - Segments are sorted by timestamp (oldest first)
        - Buffer is cleared after successful save
        - Clip duration depends on how full the buffer is
        
        Args:
            filename: Output filename (auto-generated if None)
            clear_after: Whether to clear buffer after saving (default True)
            
        Returns:
            Path to saved clip, or None on error
        """
        with self._lock:
            if not self._segments:
                self._log("No hay segmentos en buffer para guardar", "WARNING")
                return None
            
            # Log buffer status
            self._log(f"Buffer tiene {len(self._segments)} segmentos en memoria")
            
            # Sort segments by timestamp (oldest first = correct playback order)
            sorted_segments = sorted(self._segments, key=lambda s: s.timestamp)
            
            # Filter only existing files with valid size
            valid_segments = []
            for s in sorted_segments:
                if s.path.exists():
                    size = s.path.stat().st_size
                    if size > 1000:  # At least 1KB
                        valid_segments.append(s)
                        self._log(f"  Segmento válido: {s.path.name} ({size/1024:.1f}KB, {s.timestamp.strftime('%H:%M:%S')})")
                    else:
                        self._log(f"  Segmento muy pequeño: {s.path.name} ({size}B)", "WARNING")
                else:
                    self._log(f"  Segmento no existe: {s.path.name}", "WARNING")
            
            # Find active segment (the one being written right now)
            try:
                # Get all ts files in temp dir
                all_ts_files = list(self._temp_dir.glob("segment_*.ts"))
                if all_ts_files:
                    # Sort by modification time (newest first)
                    all_ts_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                    
                    # The newest one is likely the active one
                    potential_active = all_ts_files[0]
                    
                    # Check if it's already in our known valid segments
                    known_paths = {s.path for s in valid_segments}
                    
                    if potential_active not in known_paths:
                        # It's new! Check if it has data
                        size = potential_active.stat().st_size
                        if size > 1024: # > 1KB
                            # Create a temporary segment for the active part
                            timestamp = datetime.fromtimestamp(potential_active.stat().st_mtime)
                            # Estimate duration from size (very rough approx, assuming 3MB/s for 1080p high bitrate)
                            # Or just assume it's the latest snippet. 
                            # Better: let ffmpeg probe it or just count it.
                            
                            active_seg = Segment(
                                path=potential_active,
                                timestamp=timestamp,
                                duration_sec=1.0, # Placeholder, doesn't matter for concat
                                size_bytes=size
                            )
                            valid_segments.append(active_seg)
                            self._log(f"  ➕ Incluyendo segmento activo (LIVE): {potential_active.name} ({size/1024:.1f}KB)")
            except Exception as e:
                self._log(f"Error buscando segmento activo: {e}", "WARNING")

            if not valid_segments:
                self._log("Ningún segmento válido para guardar", "WARNING")
                return None
            
            # Calculate actual clip duration (approximate now with active segment)
            total_duration = sum(s.duration_sec for s in valid_segments)
            
            self._log(f"Clip total: {len(valid_segments)} segmentos = {total_duration}s")
            
            # Generate output filename
            if not filename:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename = f"clip_{int(total_duration)}s_{timestamp}.mp4"
            
            output_path = self._settings.get_download_path() / filename
            
            # Create concat file for ffmpeg
            concat_file = self._temp_dir / "concat.txt"
            try:
                self._log(f"Concatenando {len(valid_segments)} segmentos...")
                
                # Write concat file with segments in chronological order
                with open(concat_file, 'w', encoding='utf-8') as f:
                    for segment in valid_segments:
                        # Use forward slashes for ffmpeg compatibility
                        escaped_path = str(segment.path.absolute()).replace("\\", "/")
                        f.write(f"file '{escaped_path}'\n")
                
                # Concatenate using ffmpeg
                ffmpeg_cmd = get_ffmpeg_cmd()
                
                # First try with copy (faster)
                cmd = ffmpeg_cmd + [
                    "-y",                     # Overwrite output
                    "-f", "concat",           # Concat demuxer
                    "-safe", "0",             # Allow absolute paths
                    "-i", str(concat_file),   # Input concat file
                    "-fflags", "+genpts",     # Generate presentation timestamps
                    "-c", "copy",             # Copy streams (fast)
                    "-movflags", "+faststart", # Web-compatible MP4
                    str(output_path)
                ]
                
                self._log("Concatenando clips...")
                
                self._clip_process = register_process(subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                ))
                
                # Wait for completion
                stdout, stderr = self._clip_process.communicate()
                result_code = self._clip_process.returncode
                
                # Cleanup tracking
                unregister_process(self._clip_process)
                self._clip_process = None
                
                # If copy failed, try with re-encoding
                if result_code != 0:
                    self._log("Reintentando con re-encoding...", "WARNING")
                    cmd_reencode = ffmpeg_cmd + [
                        "-y",
                        "-f", "concat",
                        "-safe", "0",
                        "-i", str(concat_file),
                        "-c:v", "libx264",
                        "-preset", "fast",
                        "-crf", "23",
                        "-c:a", "aac",
                        "-b:a", "128k",
                        "-movflags", "+faststart",
                        str(output_path)
                    ]
                    
                    self._clip_process = register_process(subprocess.Popen(
                        cmd_reencode,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    ))
                    
                    stdout, stderr = self._clip_process.communicate()
                    result_code = self._clip_process.returncode
                    
                    unregister_process(self._clip_process)
                    self._clip_process = None
                
                if result_code == 0 and output_path.exists():
                    file_size_mb = output_path.stat().st_size / (1024 * 1024)
                    self._log(f"✅ Clip guardado: {output_path.name} ({total_duration:.0f}s, {file_size_mb:.1f}MB)")
                    
                    # Clear buffer after successful save (like Instant Replay)
                    if clear_after:
                        self._clear_segments()
                        self._log("Buffer limpiado - comenzando nuevo buffer")
                    
                    self._emit("on_clip_saved", output_path)
                    return output_path
                else:
                    error_msg = result.stderr.decode('utf-8', errors='ignore')
                    self._log(f"Error FFmpeg: {error_msg[:400]}", "ERROR")
                    return None
                    
            except FileNotFoundError:
                self._log("❌ FFmpeg no encontrado. Instala: winget install Gyan.FFmpeg", "ERROR")
                return None
            except Exception as e:
                self._log(f"Error guardando clip: {e}", "ERROR")
                self._emit("on_error", str(e))
                return None
            finally:
                try:
                    concat_file.unlink()
                except Exception:
                    pass
    
    def _clear_segments(self) -> None:
        """Clear all segments from buffer (internal use)."""
        for segment in self._segments:
            try:
                if segment.path.exists():
                    segment.path.unlink()
            except Exception:
                pass
        self._segments.clear()
    
    def start_recording(self, url: str, quality: str = "best", 
                       filename: Optional[str] = None) -> bool:
        """
        Start direct recording to file.
        Uses streamlink output mode.
        """
        if self._state == RecorderState.RECORDING:
            self._log("Ya hay una grabación activa", "WARNING")
            return False
        
        # Stop buffer if running
        if self._state == RecorderState.BUFFERING:
            self.stop_buffer()
        
        # Generate output filename
        if not filename:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"recording_{timestamp}.mp4"
        
        output_path = self._settings.get_download_path() / filename
        
        self._current_url = url
        self._state = RecorderState.RECORDING
        self._emit("on_state_change", self._state)
        
        def _record():
            streamlink_cmd = get_streamlink_cmd()
            try:
                cmd = streamlink_cmd + [
                    "--http-header", "User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "--http-header", "Referer=https://www.douyin.com/",
                    "-o", str(output_path),
                    "--force",
                    url,
                    quality
                ]
                
                self._record_process = register_process(subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                ))
                
                self._log(f"Grabación iniciada: {output_path}")
                self._record_process.wait()
                
                # Cleanup tracking
                if self._record_process:
                    unregister_process(self._record_process)
                
                if output_path.exists():
                    self._emit("on_recording_complete", output_path)
                    self._log(f"Grabación completada: {output_path}")
                    
            except FileNotFoundError:
                self._log("Streamlink no encontrado", "ERROR")
            except Exception as e:
                self._log(f"Error de grabación: {e}", "ERROR")
                self._emit("on_error", str(e))
            finally:
                self._state = RecorderState.IDLE
                self._emit("on_state_change", self._state)
        
        thread = threading.Thread(target=_record, daemon=True)
        thread.start()
        
        return True
    
    def stop_recording(self) -> Optional[Path]:
        """Stop current recording and return file path."""
        if self._state != RecorderState.RECORDING:
            return None
        
        # Aggressively kill recording process and all children
        kill_process_tree(self._record_process)
        self._record_process = None
        
        self._state = RecorderState.IDLE
        self._emit("on_state_change", self._state)
        self._log("Grabación detenida")
        return None
    
    def get_state(self) -> str:
        """Get current recorder state."""
        return self._state
    
    def get_buffer_status(self) -> tuple[int, int, float]:
        """
        Get buffer status.
        Returns (current_segments, max_segments, buffer_seconds).
        """
        with self._lock:
            current = len(self._segments)
            max_segs = self._get_max_segments()
            duration = sum(s.duration_sec for s in self._segments)
            return (current, max_segs, duration)
    
    def clear_buffer(self) -> None:
        """Clear all buffered segments (public API)."""
        with self._lock:
            self._clear_segments()
        self._log("Buffer limpiado")
    
    def cleanup(self) -> None:
        """Cleanup on shutdown."""
        self.stop_buffer()
        self.stop_recording()
        self.clear_buffer()
