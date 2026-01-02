"""
DouyinStream Pro - Embedded VLC Player
Professional VLC player with TRUE multi-monitor fullscreen support.

CRITICAL: VLC cannot change hwnd mid-playback. Solution: stop → set hwnd → restart.
Uses screeninfo for accurate multi-monitor detection.
"""

import os
import sys
from typing import Optional, Callable, Tuple
import customtkinter as ctk
import time

# Try to import python-vlc
try:
    import vlc
    VLC_AVAILABLE = True
except (ImportError, OSError):
    VLC_AVAILABLE = False

# Try to import screeninfo for multi-monitor support
try:
    from screeninfo import get_monitors
    SCREENINFO_AVAILABLE = True
except ImportError:
    SCREENINFO_AVAILABLE = False


def get_monitor_at_point(x: int, y: int) -> Tuple[int, int, int, int]:
    """
    Get the monitor bounds (x, y, width, height) that contains the given point.
    Falls back to primary monitor if screeninfo not available.
    """
    if SCREENINFO_AVAILABLE:
        try:
            for m in get_monitors():
                if m.x <= x < m.x + m.width and m.y <= y < m.y + m.height:
                    return (m.x, m.y, m.width, m.height)
            # Fallback to first monitor
            m = get_monitors()[0]
            return (m.x, m.y, m.width, m.height)
        except Exception:
            pass
    
    # Fallback - assume primary monitor at 0,0
    return (0, 0, 1920, 1080)


class EmbeddedPlayer(ctk.CTkFrame):
    """
    VLC media player embedded in CTk frame.
    Professional implementation with proper multi-monitor fullscreen.
    """
    
    def __init__(self, parent, vlc_lib_path: Optional[str] = None, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        
        self._parent_window = parent
        self._vlc_lib_path = vlc_lib_path
        self._instance: Optional[vlc.Instance] = None
        self._player: Optional[vlc.MediaPlayer] = None
        self._media: Optional[vlc.Media] = None
        self._event_manager = None
        self._is_playing = False
        self._is_stopping = False  # Prevent recursive stops
        self._volume = 80
        self._current_url = ""
        self._current_quality = "best"  # Store quality for restart
        
        # Fullscreen state
        self._is_fullscreen = False
        self._fullscreen_toplevel = None
        self._fs_video_frame = None
        self._fs_controls_window = None  # Floating controls window
        self._fs_controls = None
        self._fs_controls_visible = True
        self._fs_hide_timer = None
        self._fs_play_btn = None
        self._fs_stats = None
        self._monitor_bounds = None
        
        self._callbacks: dict[str, list[Callable]] = {
            "on_play": [],
            "on_pause": [],
            "on_stop": [],
            "on_error": [],
        }
        
        self.configure(fg_color="#000000")
        
        # Video frame
        self._video_frame = ctk.CTkFrame(self, fg_color="#000000")
        self._video_frame.pack(fill="both", expand=True)
        
        # Placeholder
        self._placeholder = ctk.CTkLabel(
            self._video_frame,
            text="🎬\nDouyinStream Pro\n\nDoble clic para pantalla completa",
            font=ctk.CTkFont(size=20),
            text_color="#444"
        )
        self._placeholder.place(relx=0.5, rely=0.5, anchor="center")
        
        # Controls bar
        self._controls = ctk.CTkFrame(self, fg_color="#1a1a2e", height=50)
        self._controls.pack(fill="x", side="bottom")
        self._controls.pack_propagate(False)
        
        self._build_controls()
        
        # Bind double-click
        self._video_frame.bind("<Double-Button-1>", lambda e: self.toggle_fullscreen())
        
        # Initialize VLC
        if VLC_AVAILABLE:
            self._init_vlc()
    
    def _init_vlc(self) -> bool:
        """Initialize VLC instance with quality-preserving options."""
        try:
            if self._vlc_lib_path:
                os.environ['VLC_PLUGIN_PATH'] = os.path.join(self._vlc_lib_path, 'plugins')
            
            # Minimal options for smooth playback
            # Less is more - VLC defaults are usually optimal
            args = [
                '--quiet',
                '--no-video-title-show',
                
                # Buffering for live streams
                '--network-caching=2000',
                '--live-caching=2000',
                
                # Let VLC manage frame timing naturally
                # (removing aggressive frame options that cause stutter)
                
                # Hardware acceleration if available
                '--avcodec-hw=any',
            ]
            
            self._instance = vlc.Instance(args)
            self._player = self._instance.media_player_new()
            
            # Set up event manager for stream monitoring
            self._event_manager = self._player.event_manager()
            self._event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_vlc_end)
            self._event_manager.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._on_vlc_error)
            
            return True
            
        except Exception as e:
            print(f"[EmbeddedPlayer] VLC init error: {e}")
            return False
    
    def _on_vlc_end(self, event) -> None:
        """Handle VLC end of stream event (called from VLC thread)."""
        print("[EmbeddedPlayer] Stream ended")
        try:
            if self.winfo_exists():
                self.after(100, self._handle_stream_end)
        except Exception:
            pass
    
    def _on_vlc_error(self, event) -> None:
        """Handle VLC error event (called from VLC thread)."""
        print("[EmbeddedPlayer] VLC error occurred")
        try:
            if self.winfo_exists():
                self.after(100, self._handle_stream_error)
        except Exception:
            pass
    
    def _handle_stream_end(self) -> None:
        """Handle stream end gracefully."""
        try:
            if self._is_stopping:
                return
            
            self._is_playing = False
            
            if self.winfo_exists():
                try:
                    self._play_btn.configure(text="▶")
                    self._stats_label.configure(text="Stream terminado")
                except Exception:
                    pass
            
            self._emit("on_stop")
        except Exception as e:
            print(f"[EmbeddedPlayer] Error handling stream end: {e}")
    
    def _handle_stream_error(self) -> None:
        """Handle stream error gracefully."""
        try:
            if self._is_stopping:
                return
            
            self._is_playing = False
            
            if self.winfo_exists():
                try:
                    self._play_btn.configure(text="▶")
                    self._stats_label.configure(text="Error en stream")
                    self._show_placeholder()
                except Exception:
                    pass
            
            self._emit("on_error", "Stream error")
        except Exception as e:
            print(f"[EmbeddedPlayer] Error handling stream error: {e}")
    
    def _build_controls(self) -> None:
        """Build playback control bar."""
        controls_inner = ctk.CTkFrame(self._controls, fg_color="transparent")
        controls_inner.pack(expand=True)
        
        self._play_btn = ctk.CTkButton(
            controls_inner, text="▶", width=40, height=40,
            fg_color="#e94560", hover_color="#ff6b6b",
            font=ctk.CTkFont(size=18), command=self.toggle_play
        )
        self._play_btn.pack(side="left", padx=5)
        
        ctk.CTkButton(
            controls_inner, text="⏹", width=40, height=40,
            fg_color="#2d2d44", hover_color="#3d3d5c",
            font=ctk.CTkFont(size=18), command=self.stop
        ).pack(side="left", padx=5)
        
        ctk.CTkLabel(controls_inner, text="🔊", font=ctk.CTkFont(size=16)).pack(side="left", padx=(20, 5))
        
        self._volume_slider = ctk.CTkSlider(
            controls_inner, from_=0, to=100, width=100, height=16,
            command=self._on_volume_change
        )
        self._volume_slider.pack(side="left", padx=5)
        self._volume_slider.set(self._volume)
        
        ctk.CTkButton(
            controls_inner, text="⛶", width=40, height=40,
            fg_color="#2d2d44", hover_color="#3d3d5c",
            font=ctk.CTkFont(size=18), command=self.enter_fullscreen
        ).pack(side="left", padx=(20, 5))
        
        self._stats_label = ctk.CTkLabel(
            controls_inner, text="", font=ctk.CTkFont(size=11), text_color="#888"
        )
        self._stats_label.pack(side="left", padx=20)
    
    def _get_video_handle(self) -> int:
        """Get handle for normal mode video frame."""
        self._video_frame.update_idletasks()
        return self._video_frame.winfo_id()
    
    def _get_fullscreen_handle(self) -> int:
        """Get handle for fullscreen video frame."""
        if self._fs_video_frame:
            self._fs_video_frame.update_idletasks()
            return self._fs_video_frame.winfo_id()
        return 0
    
    def _set_vlc_window(self, handle: int) -> None:
        """Set VLC output window handle."""
        if not self._player:
            return
        if sys.platform == "win32":
            self._player.set_hwnd(handle)
        elif sys.platform == "darwin":
            self._player.set_nsobject(handle)
        else:
            self._player.set_xwindow(handle)
    
    def play(self, url: str, quality: str = "best") -> bool:
        """Start playing a stream URL."""
        if not VLC_AVAILABLE or not self._player:
            return False
        
        try:
            self._current_url = url
            self._current_quality = quality
            self._placeholder.place_forget()
            
            # Create media with quality-preserving options
            self._media = self._instance.media_new(url)
            self._media.add_option(':http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
            self._media.add_option(':http-referrer=https://www.douyin.com/')
            self._media.add_option(':network-caching=1500')
            
            self._player.set_media(self._media)
            self._set_vlc_window(self._get_video_handle())
            self._player.audio_set_volume(self._volume)
            
            result = self._player.play()
            
            if result == 0:
                self._is_playing = True
                self._play_btn.configure(text="⏸")
                self._emit("on_play")
                self._update_stats()
                return True
            else:
                self._show_placeholder()
                return False
                
        except Exception as e:
            print(f"[EmbeddedPlayer] Play error: {e}")
            self._emit("on_error", str(e))
            self._show_placeholder()
            return False
    
    def _restart_playback_at(self, handle: int) -> None:
        """Restart playback at a specific window handle. Uses same quality."""
        if not self._player or not self._current_url:
            return
        
        # Stop current
        self._player.stop()
        time.sleep(0.05)  # Brief pause
        
        # Set new window BEFORE creating media
        self._set_vlc_window(handle)
        
        # Recreate media with same options
        self._media = self._instance.media_new(self._current_url)
        self._media.add_option(':http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        self._media.add_option(':http-referrer=https://www.douyin.com/')
        self._media.add_option(':network-caching=1500')
        
        self._player.set_media(self._media)
        self._player.audio_set_volume(self._volume)
        self._player.play()
        
        self._is_playing = True
    
    def _show_placeholder(self) -> None:
        self._placeholder.place(relx=0.5, rely=0.5, anchor="center")
    
    def pause(self) -> None:
        if self._player and self._is_playing:
            self._player.pause()
            self._is_playing = False
            self._play_btn.configure(text="▶")
            self._update_fs_play_btn()
            self._emit("on_pause")
    
    def resume(self) -> None:
        if self._player and not self._is_playing:
            self._player.play()
            self._is_playing = True
            self._play_btn.configure(text="⏸")
            self._update_fs_play_btn()
            self._emit("on_play")
    
    def toggle_play(self) -> None:
        if self._is_playing:
            self.pause()
        else:
            self.resume()
    
    def _update_fs_play_btn(self) -> None:
        """Update fullscreen play button state."""
        if self._fs_play_btn:
            try:
                self._fs_play_btn.configure(text="⏸" if self._is_playing else "▶")
            except Exception:
                pass
    
    def stop(self) -> None:
        if self._is_stopping:
            return
        
        self._is_stopping = True
        
        try:
            if self._is_fullscreen:
                self._close_fullscreen_window()
            
            if self._player:
                self._player.stop()
                self._is_playing = False
                self._play_btn.configure(text="▶")
                self._stats_label.configure(text="")
                self._show_placeholder()
                self._emit("on_stop")
        finally:
            self._is_stopping = False
    
    def set_volume(self, volume: int) -> None:
        self._volume = max(0, min(100, volume))
        if self._player:
            self._player.audio_set_volume(self._volume)
        self._volume_slider.set(self._volume)
    
    def _on_volume_change(self, value: float) -> None:
        self._volume = int(value)
        if self._player:
            self._player.audio_set_volume(self._volume)
    
    def enter_fullscreen(self) -> None:
        """Enter fullscreen mode with proper VLC hwnd redirect."""
        if self._is_fullscreen or not self._is_playing or not self._player:
            return
        
        self._is_fullscreen = True
        
        # Get main window position to determine which monitor
        main_window = self.winfo_toplevel()
        main_x = main_window.winfo_x()
        main_y = main_window.winfo_y()
        main_w = main_window.winfo_width()
        main_h = main_window.winfo_height()
        
        center_x = main_x + main_w // 2
        center_y = main_y + main_h // 2
        
        mon_x, mon_y, mon_w, mon_h = get_monitor_at_point(center_x, center_y)
        self._monitor_bounds = (mon_x, mon_y, mon_w, mon_h)
        
        # Create fullscreen video window (black background)
        self._fullscreen_toplevel = ctk.CTkToplevel()
        self._fullscreen_toplevel.title("DouyinStream Pro - Fullscreen")
        self._fullscreen_toplevel.configure(fg_color="#000000")
        self._fullscreen_toplevel.geometry(f"{mon_w}x{mon_h}+{mon_x}+{mon_y}")
        self._fullscreen_toplevel.overrideredirect(True)
        # NOT topmost - allows other windows to appear on top if needed
        self._fullscreen_toplevel.update()
        
        # Video frame inside fullscreen window
        self._fs_video_frame = ctk.CTkFrame(
            self._fullscreen_toplevel,
            fg_color="#000000",
            corner_radius=0
        )
        self._fs_video_frame.pack(fill="both", expand=True)
        
        # Keyboard bindings on fullscreen window
        self._fullscreen_toplevel.bind("<Escape>", self._on_escape_key)
        self._fullscreen_toplevel.bind("<space>", lambda e: self.toggle_play())
        self._fullscreen_toplevel.bind("<Return>", lambda e: self.exit_fullscreen())
        self._fullscreen_toplevel.bind("<Tab>", lambda e: self._toggle_fs_controls())  # TAB to show/hide controls
        self._fullscreen_toplevel.bind("<Button-1>", lambda e: self._toggle_fs_controls())  # Click to toggle
        
        self._fullscreen_toplevel.focus_force()
        
        # Create floating controls window (separate, on top)
        self._fs_controls_window = ctk.CTkToplevel()
        self._fs_controls_window.title("")
        self._fs_controls_window.overrideredirect(True)
        self._fs_controls_window.attributes('-topmost', True)
        self._fs_controls_window.attributes('-alpha', 0.95)
        self._fs_controls_window.configure(fg_color="#1a1a2e")
        
        control_height = 70
        self._fs_controls_window.geometry(f"{mon_w}x{control_height}+{mon_x}+{mon_y + mon_h - control_height}")
        
        self._fs_controls = ctk.CTkFrame(self._fs_controls_window, fg_color="transparent")
        self._fs_controls.pack(fill="both", expand=True)
        self._fs_controls_visible = True
        
        self._build_fullscreen_controls()
        
        # Bindings on controls window
        self._fs_controls_window.bind("<Escape>", self._on_escape_key)
        self._fs_controls_window.bind("<Tab>", lambda e: self._toggle_fs_controls())
        self._fs_controls_window.bind("<Leave>", self._on_controls_leave)
        
        # Wait for window to be ready, then redirect VLC playback
        self._fullscreen_toplevel.after(100, self._redirect_vlc_to_fullscreen)
        
        # NO POLLING - keyboard/click based controls only (zero overhead)
        
        # Start auto-hide timer (5 seconds on start for user to see controls)
        self._fs_hide_timer = self._fs_controls_window.after(5000, self._hide_fs_controls)

    def _start_mouse_polling(self) -> None:
        """Poll mouse position to show controls at bottom edge (VLC steals events)."""
        if not self._is_fullscreen:
            return
        
        try:
            # Get mouse position from root window
            root = self.winfo_toplevel()
            x = root.winfo_pointerx()
            y = root.winfo_pointery()
            
            if self._monitor_bounds:
                mon_x, mon_y, mon_w, mon_h = self._monitor_bounds
                
                # Show controls if mouse is in bottom 120 pixels
                if y > mon_y + mon_h - 120:
                    self._show_fs_controls()
            
            # Continue polling every 300ms (reduced to minimize overhead)
            if self._fullscreen_toplevel:
                self._fullscreen_toplevel.after(300, self._start_mouse_polling)
        except Exception:
            pass

    def _redirect_vlc_to_fullscreen(self) -> None:
        """Redirect VLC rendering to fullscreen window."""
        if not self._fullscreen_toplevel or not self._fs_video_frame:
            return
        
        # Get the hwnd of the fullscreen video frame
        handle = self._get_fullscreen_handle()
        if handle and self._player:
            self._restart_playback_at(handle)

    def _on_fs_mouse_move(self, event) -> None:
        """Show controls when mouse moves to bottom of screen."""
        if not self._is_fullscreen or not self._monitor_bounds:
            return
        
        mon_x, mon_y, mon_w, mon_h = self._monitor_bounds
        # Show controls if mouse is in bottom 100 pixels
        if event.y_root > mon_y + mon_h - 100:
            self._show_fs_controls()

    def _on_controls_leave(self, event) -> None:
        """Start hide timer when mouse leaves controls."""
        if self._fs_hide_timer and self._fs_controls_window:
            try:
                self._fs_controls_window.after_cancel(self._fs_hide_timer)
            except Exception:
                pass
        if self._fs_controls_window:
            self._fs_hide_timer = self._fs_controls_window.after(2000, self._hide_fs_controls)

    def _on_fullscreen_click(self, event) -> None:
        """Handle click in fullscreen - show controls."""
        self._show_fs_controls()
    
    def _show_fs_controls(self) -> None:
        """Show fullscreen controls window."""
        if not self._fs_controls_window:
            return
        
        if not self._fs_controls_visible:
            self._fs_controls_window.deiconify()
            self._fs_controls_window.lift()
            self._fs_controls_visible = True
        
        # Reset hide timer
        if self._fs_hide_timer and self._fs_controls_window:
            try:
                self._fs_controls_window.after_cancel(self._fs_hide_timer)
            except Exception:
                pass
        
        if self._fs_controls_window:
            self._fs_hide_timer = self._fs_controls_window.after(3000, self._hide_fs_controls)
    
    def _toggle_fs_controls(self) -> None:
        """Toggle fullscreen controls visibility (TAB/click)."""
        if self._fs_controls_visible:
            self._hide_fs_controls()
        else:
            self._show_fs_controls()
    
    def _on_escape_key(self, event) -> None:
        """Handle ESC key press."""
        self.exit_fullscreen()
    
    def _start_fullscreen_playback(self) -> None:
        """Restart playback on fullscreen window."""
        if not self._fullscreen_toplevel or not self._fs_video_frame:
            return
        
        handle = self._get_fullscreen_handle()
        if handle:
            self._restart_playback_at(handle)
    
    def _build_fullscreen_controls(self) -> None:
        """Build fullscreen control bar."""
        center = ctk.CTkFrame(self._fs_controls, fg_color="transparent")
        center.pack(expand=True)
        
        # Play/Pause
        self._fs_play_btn = ctk.CTkButton(
            center, text="⏸" if self._is_playing else "▶",
            width=60, height=50, fg_color="#e94560", hover_color="#ff6b6b",
            font=ctk.CTkFont(size=24), command=self.toggle_play
        )
        self._fs_play_btn.pack(side="left", padx=10)
        
        # Stop
        ctk.CTkButton(
            center, text="⏹", width=50, height=50,
            fg_color="#2d2d44", hover_color="#3d3d5c",
            font=ctk.CTkFont(size=20), command=self.stop
        ).pack(side="left", padx=10)
        
        # Volume
        vol_frame = ctk.CTkFrame(center, fg_color="transparent")
        vol_frame.pack(side="left", padx=20)
        
        ctk.CTkLabel(vol_frame, text="🔊", font=ctk.CTkFont(size=18)).pack(side="left", padx=5)
        
        vol_slider = ctk.CTkSlider(
            vol_frame, from_=0, to=100, width=120, height=18,
            command=self._on_volume_change
        )
        vol_slider.pack(side="left")
        vol_slider.set(self._volume)
        
        # Exit button
        ctk.CTkButton(
            center, text="✕ Salir (ESC)", width=130, height=50,
            fg_color="#c0392b", hover_color="#e74c3c",
            font=ctk.CTkFont(size=14, weight="bold"), command=self.exit_fullscreen
        ).pack(side="left", padx=20)
        
        # Stats with FPS
        self._fs_stats = ctk.CTkLabel(
            center, text="", font=ctk.CTkFont(size=12), text_color="#888"
        )
        self._fs_stats.pack(side="left", padx=10)
    
    def _on_fullscreen_motion(self, event) -> None:
        """Show controls on mouse movement."""
        self._show_fs_controls()
    
    def _hide_fs_controls(self) -> None:
        """Hide fullscreen controls window."""
        if self._fs_controls_visible and self._fs_controls_window:
            try:
                self._fs_controls_window.withdraw()
                self._fs_controls_visible = False
            except Exception:
                pass
    
    def _close_fullscreen_window(self) -> None:
        """Close fullscreen mode and controls."""
        self._is_fullscreen = False
        
        # Cancel hide timer
        if self._fs_hide_timer and self._fs_controls_window:
            try:
                self._fs_controls_window.after_cancel(self._fs_hide_timer)
            except Exception:
                pass
        
        # Destroy floating controls window
        if self._fs_controls_window:
            try:
                self._fs_controls_window.destroy()
            except Exception:
                pass
            self._fs_controls_window = None
            self._fs_controls = None
            self._fs_play_btn = None
            self._fs_stats = None
        
        # Destroy fullscreen video window
        if self._fullscreen_toplevel:
            try:
                self._fullscreen_toplevel.destroy()
            except Exception:
                pass
            self._fullscreen_toplevel = None
            self._fs_video_frame = None
    
    def exit_fullscreen(self) -> None:
        """Exit fullscreen mode and restore embedded playback."""
        if not self._is_fullscreen:
            return
        
        # Get main video handle BEFORE destroying windows
        main_handle = self._get_video_handle()
        
        # Close fullscreen windows
        self._close_fullscreen_window()
        
        # Redirect VLC back to embedded player
        if self._player and main_handle:
            self._restart_playback_at(main_handle)
        
        # Focus main window
        try:
            main = self.winfo_toplevel()
            main.focus_force()
            main.lift()
        except Exception:
            pass
    
    def toggle_fullscreen(self) -> None:
        if self._is_fullscreen:
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()
    
    def _get_stats_string(self) -> str:
        """Get stats string including resolution and FPS."""
        try:
            if not self._player:
                return ""
            
            width = self._player.video_get_width()
            height = self._player.video_get_height()
            time_ms = self._player.get_time()
            time_str = f"{time_ms // 60000}:{(time_ms // 1000) % 60:02d}"
            
            # Get FPS
            fps = self._player.get_fps()
            fps_str = f"{fps:.0f}fps" if fps > 0 else ""
            
            return f"{width}x{height} {fps_str}  •  {time_str}"
        except Exception:
            return ""
    
    def _update_stats(self) -> None:
        """Update playback statistics display."""
        if not self._player or not self._is_playing:
            return
        
        try:
            stats = self._get_stats_string()
            self._stats_label.configure(text=stats)
            
            # Update fullscreen stats
            if self._is_fullscreen and self._fs_stats:
                try:
                    self._fs_stats.configure(text=stats)
                except Exception:
                    pass
        except Exception:
            pass
        
        # Schedule next update
        if self._is_playing:
            self.after(1000, self._update_stats)
    
    def is_playing(self) -> bool:
        return self._is_playing
    
    def is_fullscreen(self) -> bool:
        return self._is_fullscreen
    
    def get_volume(self) -> int:
        return self._volume
    
    def add_callback(self, event: str, callback: Callable) -> None:
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def _emit(self, event: str, *args) -> None:
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args)
            except Exception:
                pass
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        if self._is_fullscreen:
            self._close_fullscreen_window()
        
        if self._player:
            try:
                self._player.stop()
                self._player.release()
            except Exception:
                pass
        
        if self._instance:
            try:
                self._instance.release()
            except Exception:
                pass


def is_vlc_available() -> bool:
    return VLC_AVAILABLE
