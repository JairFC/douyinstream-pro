"""
DouyinStream Pro - Main Application Window
Primary UI and application logic.
"""

import customtkinter as ctk
from typing import Optional
import threading
from pathlib import Path

from config.settings_manager import get_settings, SettingsManager
from core.stream_engine import StreamEngine
from core.clipboard_monitor import ClipboardMonitor
from core.recorder import Recorder, RecorderState
from core.player_manager import PlayerManager, PlayerType
from core.history_manager import HistoryManager
from core.live_checker import get_live_checker

from ui.components import (
    ToastNotification,
    StatusIndicator,
    QualitySelector,
    HistoryCard,
    BufferProgressBar,
    ConsoleViewer,
    AliasEditDialog
)
from ui.embedded_player import EmbeddedPlayer, is_vlc_available
from ui.feed_window import FeedWindow


class DouyinStreamApp(ctk.CTk):
    """
    Main application window for DouyinStream Pro.
    Integrates all components and manages application state.
    """
    
    APP_TITLE = "DouyinStream Pro"
    APP_VERSION = "1.0.0"
    
    def __init__(self) -> None:
        super().__init__()
        
        # Initialize core components
        self._settings = get_settings()
        self._stream_engine = StreamEngine()
        self._clipboard_monitor = ClipboardMonitor()
        self._recorder = Recorder()
        self._player_manager = PlayerManager()
        self._history_manager = HistoryManager()
        self._live_checker = get_live_checker()
        
        # Track history cards for live status updates
        self._history_cards: dict[str, HistoryCard] = {}
        
        # State
        self._current_url: str = ""
        self._current_quality: str = "best"
        self._is_recording = False
        self._active_toast: Optional[ToastNotification] = None
        self._cinema_mode = False  # Cinema mode: hides UI, maximizes video
        
        # Configure window
        self._setup_window()
        
        # Build UI
        self._build_ui()
        
        # Setup callbacks
        self._setup_callbacks()
        
        # Start clipboard monitor
        if self._settings.get("auto_clipboard"):
            self._clipboard_monitor.start()
        
        # Start live status checker (disabled temporarily - causes crashes)
        # TODO: Fix callback scope and re-enable
        # self._live_checker.add_callback(self._on_live_status_change)
        # self._start_live_checker()
        
        # Initial checks
        self._check_player_availability()
        
        self._log("DouyinStream Pro iniciado")
    
    def _setup_window(self) -> None:
        """Configure main window properties."""
        self.title(self.APP_TITLE)
        
        # Set geometry from settings or default
        geometry = self._settings.get("window_geometry", "1200x800")
        self.geometry(geometry)
        self.minsize(900, 600)
        
        # Theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Icon (if available)
        icon_path = Path(__file__).parent.parent / "assets" / "icon.ico"
        if icon_path.exists():
            self.iconbitmap(str(icon_path))
        
        # Save geometry on close
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Cinema mode: F11 to toggle, ESC to exit
        self.bind("<F11>", lambda e: self._toggle_cinema_mode())
        self.bind("<Escape>", lambda e: self._exit_cinema_mode())
    
    def _build_ui(self) -> None:
        """Build the main UI layout."""
        # Main container
        self._main_container = ctk.CTkFrame(self, fg_color="transparent")
        self._main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left panel (main content)
        self._left_panel = ctk.CTkFrame(self._main_container, fg_color="transparent")
        self._left_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Right sidebar container (includes toggle button + collapsible content)
        self._sidebar_container = ctk.CTkFrame(self._main_container, fg_color="transparent")
        self._sidebar_container.pack(side="right", fill="y")
        
        # Toggle button (always visible)
        self._sidebar_toggle = ctk.CTkButton(
            self._sidebar_container,
            text="◀",
            width=20,
            height=60,
            fg_color="#1a1a2e",
            hover_color="#2d2d44",
            corner_radius=5,
            font=ctk.CTkFont(size=14),
            command=self._toggle_sidebar
        )
        self._sidebar_toggle.pack(side="left", fill="y", padx=(0, 2))
        
        # Right panel content (collapsible)
        self._sidebar_collapsed = False
        self._right_panel = ctk.CTkFrame(
            self._sidebar_container, 
            width=280,
            fg_color="#1a1a2e",
            corner_radius=10
        )
        self._right_panel.pack(side="left", fill="y")
        self._right_panel.pack_propagate(False)
        
        self._build_left_panel()
        self._build_right_panel()
    
    def _build_left_panel(self) -> None:
        """Build left panel with player and controls."""
        # Header
        header = ctk.CTkFrame(self._left_panel, fg_color="transparent", height=50)
        header.pack(fill="x", pady=(0, 10))
        header.pack_propagate(False)
        
        title_label = ctk.CTkLabel(
            header,
            text="🎬 DouyinStream Pro",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(side="left")
        
        # Status indicator
        self._status = StatusIndicator(header)
        self._status.pack(side="right", padx=10)
        
        # Player area
        player_frame = ctk.CTkFrame(self._left_panel, fg_color="#0d0d1a", corner_radius=10)
        player_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Embedded player (if VLC available) or placeholder
        if is_vlc_available():
            vlc_path = self._player_manager.get_vlc_lib_path()
            self._player = EmbeddedPlayer(player_frame, vlc_lib_path=vlc_path)
            self._player.pack(fill="both", expand=True, padx=5, pady=5)
        else:
            placeholder = ctk.CTkLabel(
                player_frame,
                text="🎬\n\nReproductor Externo\n(VLC/MPV)",
                font=ctk.CTkFont(size=18),
                text_color="#444"
            )
            placeholder.pack(expand=True)
            self._player = None
        
        # URL input bar
        self._url_frame = ctk.CTkFrame(self._left_panel, fg_color="#1a1a2e", corner_radius=10)
        self._url_frame.pack(fill="x", pady=(0, 10))
        
        url_inner = ctk.CTkFrame(self._url_frame, fg_color="transparent")
        url_inner.pack(fill="x", padx=15, pady=12)
        
        url_label = ctk.CTkLabel(
            url_inner,
            text="🔗",
            font=ctk.CTkFont(size=16)
        )
        url_label.pack(side="left", padx=(0, 10))
        
        self._url_entry = ctk.CTkEntry(
            url_inner,
            placeholder_text="Pega una URL de Douyin o TikTok...",
            height=40,
            font=ctk.CTkFont(size=13)
        )
        self._url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._url_entry.bind("<Return>", lambda e: self._play_stream())
        
        self._play_btn = ctk.CTkButton(
            url_inner,
            text="▶ Reproducir",
            width=120,
            height=40,
            fg_color="#e94560",
            hover_color="#ff6b6b",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._play_stream
        )
        self._play_btn.pack(side="left")
        
        # Buffer progress (compact, next to URL)
        self._buffer_bar = BufferProgressBar(url_inner)
        self._buffer_bar.pack(side="right", padx=10)
        
        # Settings section (collapsible) - includes all controls
        self._settings_frame = ctk.CTkFrame(self._left_panel, fg_color="#1a1a2e", corner_radius=10)
        self._settings_frame.pack(fill="x", pady=(0, 10))
        
        # Collapsible header
        settings_header = ctk.CTkFrame(self._settings_frame, fg_color="transparent", cursor="hand2")
        settings_header.pack(fill="x", padx=15, pady=(12, 0))
        settings_header.bind("<Button-1>", lambda e: self._toggle_settings())
        
        self._settings_collapsed = False
        self._settings_arrow = ctk.CTkLabel(
            settings_header, text="▼", font=ctk.CTkFont(size=12), width=20
        )
        self._settings_arrow.pack(side="left")
        self._settings_arrow.bind("<Button-1>", lambda e: self._toggle_settings())
        
        settings_title = ctk.CTkLabel(
            settings_header, text="⚙️ Configuración", font=ctk.CTkFont(size=13, weight="bold")
        )
        settings_title.pack(side="left")
        settings_title.bind("<Button-1>", lambda e: self._toggle_settings())
        
        # Collapsible content
        self._settings_content = ctk.CTkFrame(self._settings_frame, fg_color="transparent")
        self._settings_content.pack(fill="x", padx=15, pady=(5, 12))
        
        # Row 1: Quality + Recording controls
        controls_row = ctk.CTkFrame(self._settings_content, fg_color="transparent")
        controls_row.pack(fill="x", pady=(0, 8))
        
        # Quality selector
        self._quality_selector = QualitySelector(
            controls_row,
            on_change=self._on_quality_change
        )
        self._quality_selector.pack(side="left")
        
        # Record button
        self._rec_btn = ctk.CTkButton(
            controls_row,
            text="🔴 REC",
            width=70,
            height=28,
            fg_color="#2d2d44",
            hover_color="#c0392b",
            command=self._toggle_recording
        )
        self._rec_btn.pack(side="left", padx=(15, 5))
        
        # Clip button
        self._clip_btn = ctk.CTkButton(
            controls_row,
            text="💾 Clip",
            width=70,
            height=28,
            fg_color="#2d2d44",
            hover_color="#27ae60",
            command=self._save_clip
        )
        self._clip_btn.pack(side="left", padx=5)
        
        # Feed Mode button
        self._feed_btn = ctk.CTkButton(
            controls_row,
            text="📋 Feed",
            width=70,
            height=28,
            fg_color="#9b59b6",
            hover_color="#8e44ad",
            command=self._open_feed_mode
        )
        self._feed_btn.pack(side="left", padx=5)
        
        # Row 2: Buffer toggle + duration
        buffer_row = ctk.CTkFrame(self._settings_content, fg_color="transparent")
        buffer_row.pack(fill="x", pady=5)
        
        # Buffer ON/OFF toggle
        self._buffer_enabled = True
        self._buffer_toggle_btn = ctk.CTkButton(
            buffer_row,
            text="🔴 Buffer ON",
            width=100,
            height=28,
            fg_color="#27ae60",
            hover_color="#2ecc71",
            command=self._toggle_buffer
        )
        self._buffer_toggle_btn.pack(side="left")
        
        # Duration slider (compact)
        current_buffer_min = self._settings.get("clip_buffer_minutes", 3)
        self._buffer_duration_label = ctk.CTkLabel(
            buffer_row, text=f"{current_buffer_min} min",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#e94560"
        )
        self._buffer_duration_label.pack(side="right", padx=5)
        
        self._buffer_slider = ctk.CTkSlider(
            buffer_row, from_=1, to=10, number_of_steps=9, width=100,
            command=self._on_buffer_slider_change
        )
        self._buffer_slider.pack(side="right", padx=5)
        self._buffer_slider.set(current_buffer_min)
        
        ctk.CTkLabel(buffer_row, text="⏱️", font=ctk.CTkFont(size=11)).pack(side="right")
        
        # Player mode selector
        player_row = ctk.CTkFrame(self._settings_content, fg_color="transparent")
        player_row.pack(fill="x", pady=5)
        
        ctk.CTkLabel(
            player_row, text="Reproductor:", font=ctk.CTkFont(size=12)
        ).pack(side="left")
        
        players = self._player_manager.get_available_players()
        player_names = ["Embebido (VLC)"] if is_vlc_available() else []
        player_names += [p.name for p in players]
        
        if not player_names:
            player_names = ["Ninguno detectado"]
        
        self._player_dropdown = ctk.CTkOptionMenu(
            player_row, values=player_names, width=150,
            fg_color="#2d2d44", button_color="#3d3d5c"
        )
        self._player_dropdown.pack(side="left", padx=10)
        
        # Paths row (more compact)
        paths_row = ctk.CTkFrame(self._settings_content, fg_color="transparent")
        paths_row.pack(fill="x", pady=5)
        
        download_path = self._settings.get("download_path", "")
        display_path = download_path[-30:] if len(download_path) > 30 else download_path
        self._download_path_label = ctk.CTkLabel(
            paths_row, text=f"📁 ...{display_path}",
            font=ctk.CTkFont(size=10), text_color="#888"
        )
        self._download_path_label.pack(side="left")
        
        ctk.CTkButton(
            paths_row, text="Cambiar", width=60, height=24,
            fg_color="#2d2d44", hover_color="#3d3d5c",
            command=self._browse_download_path
        ).pack(side="right")
        
        # Clipboard and FFmpeg row
        extras_row = ctk.CTkFrame(self._settings_content, fg_color="transparent")
        extras_row.pack(fill="x", pady=5)
        
        ctk.CTkLabel(
            extras_row, text="Clipboard:", font=ctk.CTkFont(size=11)
        ).pack(side="left")
        
        self._clipboard_switch = ctk.CTkSwitch(extras_row, text="", width=40, command=self._toggle_clipboard_monitor)
        self._clipboard_switch.pack(side="left", padx=5)
        if self._settings.get("auto_clipboard"):
            self._clipboard_switch.select()
        
        # FFmpeg status
        from core.ffmpeg_helper import is_ffmpeg_available
        ffmpeg_status = "✅ FFmpeg" if is_ffmpeg_available() else "❌ FFmpeg"
        ffmpeg_color = "#27ae60" if is_ffmpeg_available() else "#e74c3c"
        self._ffmpeg_label = ctk.CTkLabel(
            extras_row, text=ffmpeg_status,
            font=ctk.CTkFont(size=10), text_color=ffmpeg_color
        )
        self._ffmpeg_label.pack(side="right")
        
        # Console viewer
        self._console = ConsoleViewer(self._left_panel)
        self._console.pack(fill="x")
    
    def _build_right_panel(self) -> None:
        """Build right panel with favorites and history."""
        # Favorites section
        fav_header = ctk.CTkFrame(self._right_panel, fg_color="transparent")
        fav_header.pack(fill="x", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(
            fav_header,
            text="⭐ Favoritos",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")
        
        # Favorites list
        self._fav_scroll = ctk.CTkScrollableFrame(
            self._right_panel,
            fg_color="transparent",
            height=200
        )
        self._fav_scroll.pack(fill="x", padx=10, pady=5)
        
        # Separator
        sep = ctk.CTkFrame(self._right_panel, height=1, fg_color="#333")
        sep.pack(fill="x", padx=15, pady=10)
        
        # Recent section
        recent_header = ctk.CTkFrame(self._right_panel, fg_color="transparent")
        recent_header.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(
            recent_header,
            text="📜 Recientes",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")
        
        clear_btn = ctk.CTkButton(
            recent_header,
            text="Limpiar",
            width=60,
            height=24,
            fg_color="#2d2d44",
            hover_color="#3d3d5c",
            font=ctk.CTkFont(size=11),
            command=self._clear_history
        )
        clear_btn.pack(side="right")
        
        # Recent list
        self._recent_scroll = ctk.CTkScrollableFrame(
            self._right_panel,
            fg_color="transparent"
        )
        self._recent_scroll.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Load initial history
        self._refresh_history()
    
    def _setup_callbacks(self) -> None:
        """Setup event callbacks for core components."""
        # Clipboard monitor
        self._clipboard_monitor.add_callback(self._on_clipboard_url)
        
        # Stream engine
        self._stream_engine.add_callback("on_stream_start", self._on_stream_start)
        self._stream_engine.add_callback("on_stream_stop", self._on_stream_stop)
        self._stream_engine.add_callback("on_stream_error", self._on_stream_error)
        self._stream_engine.add_callback("on_log", self._log)
        
        # Recorder
        self._recorder.add_callback("on_state_change", self._on_recorder_state)
        self._recorder.add_callback("on_segment_added", self._on_buffer_update)
        self._recorder.add_callback("on_clip_saved", self._on_clip_saved)
        self._recorder.add_callback("on_log", self._log)
        
        # History
        self._history_manager.add_callback(self._refresh_history)
        
        # Settings
        self._settings.add_observer(self._on_setting_change)
    
    def _check_player_availability(self) -> None:
        """Check for available players and warn if none found."""
        players = self._player_manager.get_available_players()
        
        if not players and not is_vlc_available():
            self._log("⚠️ No se encontró ningún reproductor compatible", "WARNING")
            self._status.set_state("error", "Sin reproductor")
            
            # Show installation suggestion
            msg = self._player_manager.suggest_installation()
            self._log(msg)
        else:
            self._status.set_state("offline", "Listo")
    
    def _log(self, message: str, level: str = "INFO") -> None:
        """Log message to console."""
        self._console.log(f"[{level}] {message}")
    
    def _on_clipboard_url(self, url: str) -> None:
        """Handle URL detected in clipboard."""
        self._log(f"URL detectada: {url}")
        
        # Show toast notification
        def play_action():
            self._url_entry.delete(0, "end")
            self._url_entry.insert(0, url)
            self._play_stream()
        
        # Remove existing toast if any
        if self._active_toast:
            try:
                self._active_toast.dismiss()
            except Exception:
                pass
        
        self._active_toast = ToastNotification(
            self,
            message=url,
            on_action=play_action,
            action_text="Reproducir"
        )
        self._active_toast.show()
    
    def _play_stream(self) -> None:
        """Play stream from URL entry (Async)."""
        url = self._url_entry.get().strip()
        
        if not url:
            self._log("Por favor, ingresa una URL", "WARNING")
            return
        
        if not self._stream_engine.is_valid_url(url):
            self._log("URL no válida. Debe ser de Douyin o TikTok.", "ERROR")
            return
        
        # Disable controls
        self._play_btn.configure(state="disabled", text="⌛")
        self._url_entry.configure(state="disabled")
        
        self._current_url = url
        self._current_quality = self._quality_selector.get_value()
        
        self._status.set_state("connecting", "Conectando...")
        self._status.start_blink()
        
        def _connect_task():
            try:
                # Try embedded player first (VLC)
                if self._player and is_vlc_available():
                    self.after(0, lambda: self._log(f"Resolviendo URL: {url}..."))
                    
                    # This blocking call now runs in thread
                    stream_url = self._stream_engine.get_stream_url(url, self._current_quality)
                    
                    if stream_url:
                        self.after(0, lambda: self._start_embedded_player(url, stream_url))
                        return
                    else:
                        self.after(0, lambda: self._handle_connect_error("No se pudo obtener la URL del stream"))
                        return
                
                # Fallback to external player
                self.after(0, lambda: self._log("Iniciando reproductor externo..."))
                if self._stream_engine.play_in_vlc(url, self._current_quality):
                    self.after(0, lambda: self._start_external_buffer(url))
                elif self._stream_engine.play_in_mpv(url, self._current_quality):
                    self.after(0, lambda: self._start_external_buffer(url))
                else:
                    self.after(0, lambda: self._handle_connect_error("No se pudo iniciar ningún reproductor"))

            except Exception as e:
                import traceback
                trace = traceback.format_exc()
                self.after(0, lambda: self._handle_connect_error(f"Error inesperado: {str(e)}\n{trace}"))
        
        # Run in background thread
        threading.Thread(target=_connect_task, daemon=True).start()

    def _start_embedded_player(self, url: str, stream_url: str) -> None:
        """Start embedded player on main thread."""
        try:
            if self._player.play(stream_url, self._current_quality):
                self._on_stream_start(url, self._current_quality)
                # Start buffer with direct stream URL
                self._recorder.start_buffer(url, self._current_quality, stream_url=stream_url)
            else:
                self._handle_connect_error("Error al iniciar reproducción en VLC embebido")
        except Exception as e:
            self._handle_connect_error(f"Error crítico en player: {e}")
            
        self._reset_controls()

    def _start_external_buffer(self, url: str) -> None:
        """Start buffer for external player."""
        self._recorder.start_buffer(url, self._current_quality)
        self._reset_controls()

    def _handle_connect_error(self, error: str) -> None:
        """Handle connection error on main thread."""
        self._log(error, "ERROR")
        self._status.stop_blink()
        self._status.set_state("error", "Error")
        self._reset_controls()
        
    def _reset_controls(self) -> None:
        """Re-enable controls."""
        try:
            self._play_btn.configure(state="normal", text="▶ Reproducir")
            self._url_entry.configure(state="normal")
        except Exception:
            pass
    
    def _on_stream_start(self, url: str, quality: str) -> None:
        """Handle stream start."""
        self._status.stop_blink()
        self._status.set_state("streaming", "En vivo")
        
        # Add to history
        streamer = self._stream_engine.extract_streamer_name(url)
        self._history_manager.add_entry(url, streamer, quality)
        
        self._log(f"Reproduciendo: {url}")
    
    def _on_stream_stop(self) -> None:
        """Handle stream stop (pause/fullscreen toggle)."""
        self._status.set_state("offline", "Detenido")
        # NOTE: Don't stop buffer here! User might just be pausing or toggling fullscreen.
        # Buffer will be cleared when switching to a different stream URL.
    
    def _on_stream_error(self, error: str) -> None:
        """Handle stream error gracefully."""
        self._status.stop_blink()
        self._status.set_state("error", "Error")
        self._log(f"Error: {error}", "ERROR")
        # NOTE: Don't stop buffer on errors. User might want to save what was buffered
        # before the error occurred.
    
    def _on_quality_change(self, quality: str) -> None:
        """Handle quality change - restarts stream with new quality."""
        old_quality = self._current_quality
        self._current_quality = quality
        self._log(f"Calidad cambiada a: {quality}")
        
        # If playing, restart with new quality
        if self._current_url and (self._stream_engine.is_playing() or (self._player and self._player.is_playing())):
            self._log("Reiniciando stream con nueva calidad...")
            
            # NOTE: Don't stop buffer here! start_buffer is smart enough to preserve
            # segments when the URL is the same. This allows quality changes without
            # losing buffered content.
            
            # Stop current playback
            if self._player:
                self._player.stop()
            self._stream_engine.stop_stream()
            
            # Get new stream URL with the new quality
            stream_url = self._stream_engine.get_stream_url(self._current_url, quality)
            
            if stream_url and self._player:
                # Restart with new quality URL
                if self._player.play(stream_url, quality):
                    self._on_stream_start(self._current_url, quality)
                    # start_buffer will preserve existing segments for same URL, update stream_url
                    self._recorder.start_buffer(self._current_url, quality, stream_url=stream_url)
                    self._log(f"Stream reiniciado con calidad: {quality}")
                else:
                    self._log("Error al reiniciar stream", "ERROR")
            else:
                # Fallback to full restart
                self._play_stream()
    
    def _toggle_recording(self) -> None:
        """Toggle recording on/off."""
        if self._recorder.get_state() == RecorderState.RECORDING:
            self._recorder.stop_recording()
            self._rec_btn.configure(text="🔴 REC", fg_color="#2d2d44")
            self._is_recording = False
        else:
            if not self._current_url:
                self._log("Primero reproduce un stream", "WARNING")
                return
            
            # Generate filename
            streamer = self._stream_engine.extract_streamer_name(self._current_url)
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{streamer}_{timestamp}.mp4"
            
            if self._recorder.start_recording(self._current_url, self._current_quality, filename):
                self._rec_btn.configure(text="⏹ Detener", fg_color="#c0392b")
                self._is_recording = True
    
    def _on_recorder_state(self, state: str) -> None:
        """Handle recorder state change."""
        if state == RecorderState.RECORDING:
            self._status.set_state("recording", "Grabando")
        elif state == RecorderState.BUFFERING:
            pass  # Don't change status for buffering
    
    def _on_buffer_update(self, current: int, max_segments: int) -> None:
        """Update buffer progress bar."""
        segment_duration = self._settings.get("segment_duration_sec", 5)  # Sync with recorder default
        current_seconds = current * segment_duration
        max_seconds = max_segments * segment_duration
        self._buffer_bar.update_buffer(current_seconds, max_seconds)
    
    def _save_clip(self) -> None:
        """Save current buffer as clip (runs in background thread)."""
        if not self._current_url:
            self._log("No hay buffer para guardar", "WARNING")
            return
        
        streamer = self._stream_engine.extract_streamer_name(self._current_url)
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"clip_{streamer}_{timestamp}.mp4"
        
        self._log("Guardando clip en segundo plano...")
        self._clip_btn.configure(state="disabled", text="Guardando...")
        
        # Run in background thread to prevent UI freeze
        def save_in_background():
            try:
                path = self._recorder.save_clip(filename)
                # Update UI from main thread
                self.after(0, lambda: self._on_clip_complete(path))
            except Exception as e:
                self.after(0, lambda: self._on_clip_error(str(e)))
        
        import threading
        thread = threading.Thread(target=save_in_background, daemon=True)
        thread.start()
    
    def _on_clip_complete(self, path) -> None:
        """Handle clip save completion (called from main thread)."""
        self._clip_btn.configure(state="normal", text="📎 Guardar Clip")
        if path:
            self._log(f"✅ Clip guardado: {path}")
        else:
            self._log("Error al guardar clip", "ERROR")
    
    def _on_clip_error(self, error: str) -> None:
        """Handle clip save error."""
        self._clip_btn.configure(state="normal", text="📎 Guardar Clip")
        self._log(f"Error guardando clip: {error}", "ERROR")
    
    def _on_clip_saved(self, path: Path) -> None:
        """Handle clip saved event."""
        self._log(f"✅ Clip guardado: {path}")
    
    def _on_buffer_slider_change(self, value: float) -> None:
        """Update buffer duration label when slider moves."""
        minutes = int(value)
        self._buffer_duration_label.configure(text=f"{minutes} min")
    
    def _apply_buffer_settings(self) -> None:
        """Apply new buffer settings (requires buffer restart)."""
        new_duration = int(self._buffer_slider.get())
        current_duration = self._settings.get("clip_buffer_minutes", 3)
        
        if new_duration == current_duration:
            self._log("Duración del buffer sin cambios")
            return
        
        # Save setting
        self._settings.set("clip_buffer_minutes", new_duration)
        self._log(f"Buffer configurado a {new_duration} minutos")
        
        # Restart buffer if currently buffering
        if self._recorder.get_state() == "buffering" and self._current_url:
            self._log("Reiniciando buffer con nueva duración...")
            # Stop current buffer
            self._recorder.stop_buffer()
            self._recorder.clear_buffer()
            
            # Get stream URL if available
            stream_url = self._stream_engine.get_stream_url(self._current_url, self._current_quality) or ""
            
            # Restart
            self._recorder.start_buffer(self._current_url, self._current_quality, stream_url)
            self._log(f"✅ Buffer reiniciado ({new_duration} min)")
        else:
            self._log("Cambio aplicado. Se usará en el próximo stream.")
    
    def _toggle_settings(self) -> None:
        """Toggle settings section collapse/expand."""
        if self._settings_collapsed:
            # Expand
            self._settings_content.pack(fill="x", padx=15, pady=(5, 12))
            self._settings_arrow.configure(text="▼")
            self._settings_collapsed = False
        else:
            # Collapse
            self._settings_content.pack_forget()
            self._settings_arrow.configure(text="▶")
            self._settings_collapsed = True
    
    def _toggle_buffer(self) -> None:
        """Toggle buffer recording on/off."""
        if self._buffer_enabled:
            # Turn OFF
            self._buffer_enabled = False
            self._recorder.stop_buffer()
            self._recorder.clear_buffer()
            self._buffer_toggle_btn.configure(
                text="⚫ Buffer OFF",
                fg_color="#666666",
                hover_color="#888888"
            )
            self._buffer_slider.configure(state="normal")  # Enable slider when buffer is off
            self._log("Buffer desactivado - Puedes modificar la duración")
        else:
            # Turn ON
            self._buffer_enabled = True
            new_duration = int(self._buffer_slider.get())
            self._settings.set("clip_buffer_minutes", new_duration)
            
            self._buffer_toggle_btn.configure(
                text="🔴 Buffer ON",
                fg_color="#27ae60",
                hover_color="#2ecc71"
            )
            self._buffer_slider.configure(state="disabled")  # Disable slider when buffer is on
            
            # Start buffer if there's an active stream
            if self._current_url:
                stream_url = self._stream_engine.get_stream_url(self._current_url, self._current_quality) or ""
                self._recorder.start_buffer(self._current_url, self._current_quality, stream_url)
                self._log(f"Buffer activado ({new_duration} min)")
            else:
                self._log("Buffer listo - Se activará con el próximo stream")
    
    def _toggle_sidebar(self) -> None:
        """Toggle right sidebar visibility."""
        if self._sidebar_collapsed:
            # Expand
            self._right_panel.pack(side="left", fill="y")
            self._sidebar_toggle.configure(text="◀")
            self._sidebar_collapsed = False
        else:
            # Collapse
            self._right_panel.pack_forget()
            self._sidebar_toggle.configure(text="▶")
            self._sidebar_collapsed = True
    
    def _toggle_cinema_mode(self) -> None:
        """Toggle cinema mode - maximizes video, hides all UI."""
        if self._cinema_mode:
            self._exit_cinema_mode()
        else:
            self._enter_cinema_mode()
    
    def _enter_cinema_mode(self) -> None:
        """Enter cinema mode - borderless maximized window with only video."""
        if self._cinema_mode:
            return
        
        self._cinema_mode = True
        
        # Save current geometry for restore
        self._pre_cinema_geometry = self.geometry()
        self._pre_cinema_state = self.state()
        
        # Hide all UI elements
        self._url_frame.pack_forget() if hasattr(self, '_url_frame') else None
        self._settings_frame.pack_forget() if hasattr(self, '_settings_frame') else None
        self._console.pack_forget()
        self._sidebar_container.pack_forget()
        
        # Make window borderless and maximize
        self.overrideredirect(True)
        
        # Get current monitor dimensions
        from ui.embedded_player import get_monitor_at_point
        x = self.winfo_x() + self.winfo_width() // 2
        y = self.winfo_y() + self.winfo_height() // 2
        mon_x, mon_y, mon_w, mon_h = get_monitor_at_point(x, y)
        
        self.geometry(f"{mon_w}x{mon_h}+{mon_x}+{mon_y}")
        self.update()
        
        self._log("🎬 Modo Cine activado (F11 o ESC para salir)")
    
    def _exit_cinema_mode(self) -> None:
        """Exit cinema mode - restore UI and window borders."""
        if not self._cinema_mode:
            return
        
        self._cinema_mode = False
        
        # Restore window borders
        self.overrideredirect(False)
        
        # Restore geometry
        if hasattr(self, '_pre_cinema_geometry'):
            self.geometry(self._pre_cinema_geometry)
        
        # Re-show all UI elements in correct order (bottom to top)
        # These are packed in left_panel from top to bottom:
        # 1. player (always visible, expands)
        # 2. url_frame
        # 3. settings_frame
        # 4. console
        
        # Restore left panel elements (after player which stays)
        if hasattr(self, '_url_frame'):
            self._url_frame.pack(fill="x", pady=(0, 10))
        if hasattr(self, '_settings_frame'):
            self._settings_frame.pack(fill="x", pady=(0, 10))
        if hasattr(self, '_console'):
            self._console.pack(fill="x")
        
        # Restore sidebar
        self._sidebar_container.pack(side="right", fill="y")
        
        self.update()
        
        self._log("Modo normal restaurado")
    
    def _start_live_checker(self) -> None:
        """Start the live status checker with current favorites/recent URLs."""
        # DISABLED: Causes crashes due to callback scope issues
        # TODO: Fix properly and re-enable
        return
        
        urls = []
        for item in self._history_manager.get_favorites():
            urls.append(item.url)
        for item in self._history_manager.get_recent(15):
            if item.url not in urls:
                urls.append(item.url)
        
        self._live_checker.set_urls(urls)
        self._live_checker.start()
        self._log("🔍 Monitor de estado en vivo iniciado")
    
    def _on_live_status_change(self, url: str, is_live: bool) -> None:
        """Callback when a stream's live status changes."""
        # Capture self for closure
        app = self
        
        # Update UI on main thread
        def update():
            try:
                # Update the card if it exists
                if url in app._history_cards:
                    app._history_cards[url].set_live_status(is_live)
                
                # Show toast for favorites going live
                if is_live:
                    for item in app._history_manager.get_favorites():
                        if item.url == url:
                            name = item.alias or item.title or url[:30]
                            app._show_toast(f"🟢 ¡{name} está en vivo!", "success")
                            break
            except Exception as e:
                print(f"[App] Error in live status update: {e}")
        
        self.after(0, update)
    
    def _refresh_history(self) -> None:
        """Refresh favorites and recent lists."""
        # Clear existing cards
        for widget in self._fav_scroll.winfo_children():
            widget.destroy()
        for widget in self._recent_scroll.winfo_children():
            widget.destroy()
        
        # Reset cards tracking
        self._history_cards.clear()
        urls_to_check = []
        
        # Add favorites
        for item in self._history_manager.get_favorites():
            card = HistoryCard(
                self._fav_scroll,
                url=item.url,
                title=item.title,
                alias=item.alias,
                is_favorite=True,
                play_count=item.play_count,
                on_play=self._play_from_history,
                on_edit_alias=self._edit_alias,
                on_toggle_favorite=lambda u: self._history_manager.toggle_favorite(u),
                on_delete=lambda u: self._history_manager.remove_entry(u)
            )
            card.pack(fill="x", pady=3)
            
            # Track card and set cached live status
            self._history_cards[item.url] = card
            urls_to_check.append(item.url)
            cached_status = self._live_checker.get_status(item.url)
            card.set_live_status(cached_status)
        
        # Add recent
        for item in self._history_manager.get_recent(15):
            card = HistoryCard(
                self._recent_scroll,
                url=item.url,
                title=item.title,
                alias=item.alias,
                is_favorite=False,
                play_count=item.play_count,
                on_play=self._play_from_history,
                on_edit_alias=self._edit_alias,
                on_toggle_favorite=lambda u: self._history_manager.toggle_favorite(u),
                on_delete=lambda u: self._history_manager.remove_entry(u)
            )
            card.pack(fill="x", pady=3)
            
            # Track card and set cached live status
            self._history_cards[item.url] = card
            if item.url not in urls_to_check:
                urls_to_check.append(item.url)
            cached_status = self._live_checker.get_status(item.url)
            card.set_live_status(cached_status)
        
        # Update live checker with URLs to monitor
        self._live_checker.set_urls(urls_to_check)
    
    def _play_from_history(self, url: str) -> None:
        """Play stream from history."""
        self._url_entry.delete(0, "end")
        self._url_entry.insert(0, url)
        self._play_stream()
    
    def _edit_alias(self, url: str, current_alias: str) -> None:
        """Open alias edit dialog."""
        def save_alias(new_alias: str):
            self._history_manager.set_alias(url, new_alias)
            self._log(f"Alias actualizado: {new_alias}")
        
        dialog = AliasEditDialog(self, current_alias, save_alias)
    
    def _open_feed_mode(self) -> None:
        """Open Feed Mode window in separate process."""
        try:
            from ui.feed_launcher import launch_feed_process
            
            # Launch in separate process to avoid PyQt5/Tkinter conflicts
            self._feed_process = launch_feed_process()
            
            if self._feed_process:
                self._log("📋 Feed Mode abierto en nueva ventana")
                self._show_toast("Feed Mode abierto", "success")
            else:
                self._log("❌ Error al abrir Feed Mode")
                self._show_toast("Error al abrir Feed", "error")
                
        except Exception as e:
            self._log(f"❌ Error Feed: {e}")
            self._show_toast(f"Error: {e}", "error")
    
    def _clear_history(self) -> None:
        """Clear non-favorite history."""
        self._history_manager.clear_non_favorites()
        self._log("Historial limpiado")
    
    def _toggle_clipboard_monitor(self) -> None:
        """Toggle clipboard monitoring."""
        if self._clipboard_switch.get():
            self._clipboard_monitor.start()
            self._settings.set("auto_clipboard", True)
            self._log("Smart Clipboard activado")
        else:
            self._clipboard_monitor.stop()
            self._settings.set("auto_clipboard", False)
            self._log("Smart Clipboard desactivado")
    
    def _browse_vlc(self) -> None:
        """Open file dialog to find VLC."""
        from tkinter import filedialog
        
        path = filedialog.askopenfilename(
            title="Selecciona vlc.exe",
            filetypes=[("Ejecutable", "*.exe"), ("Todos", "*.*")]
        )
        
        if path:
            self._settings.set("external_player_path", path)
            self._vlc_path_label.configure(text=f"VLC: {path}")
            self._log(f"VLC configurado: {path}")
            
            # Refresh player manager
            self._player_manager.refresh()
    
    def _browse_download_path(self) -> None:
        """Open folder dialog to select download path."""
        from tkinter import filedialog
        
        current_path = self._settings.get("download_path", "")
        
        path = filedialog.askdirectory(
            title="Selecciona carpeta de descargas",
            initialdir=current_path
        )
        
        if path:
            self._settings.set("download_path", path)
            display_path = path[-40:] if len(path) > 40 else path
            self._download_path_label.configure(
                text=f"📁 Descargas: ...{display_path}" if len(path) > 40 else f"📁 Descargas: {display_path}"
            )
            self._log(f"Carpeta de descargas: {path}")
    
    def _install_ffmpeg(self) -> None:
        """Show FFmpeg installation dialog."""
        from core.ffmpeg_helper import get_install_instructions
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Instalar FFmpeg")
        dialog.geometry("550x400")
        dialog.transient(self)
        dialog.grab_set()
        
        # Title
        ctk.CTkLabel(
            dialog,
            text="📦 FFmpeg es necesario para guardar clips",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=20)
        
        # Instructions
        text = ctk.CTkTextbox(
            dialog,
            height=200,
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        text.pack(fill="both", expand=True, padx=20, pady=10)
        text.insert("1.0", get_install_instructions())
        text.configure(state="disabled")
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        def run_winget():
            import subprocess
            self._log("Ejecutando: winget install Gyan.FFmpeg")
            try:
                # Run winget in a new terminal
                subprocess.Popen(
                    ["powershell", "-Command", "Start-Process", "powershell", 
                     "-ArgumentList", "'-Command winget install Gyan.FFmpeg; Read-Host \"Presiona Enter para cerrar\"'", 
                     "-Verb", "RunAs"],
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                self._log("Instalación iniciada. Reinicia la app después de instalar.")
            except Exception as e:
                self._log(f"Error: {e}", "ERROR")
            dialog.destroy()
        
        ctk.CTkButton(
            btn_frame,
            text="🚀 Instalar con winget",
            width=180,
            height=40,
            fg_color="#27ae60",
            hover_color="#2ecc71",
            command=run_winget
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            btn_frame,
            text="Cerrar",
            width=100,
            height=40,
            fg_color="#666",
            hover_color="#888",
            command=dialog.destroy
        ).pack(side="left", padx=10)
    
    def _on_setting_change(self, key: str, value) -> None:
        """Handle setting change."""
        self._log(f"Configuración actualizada: {key} = {value}")
    
    def _on_close(self) -> None:
        """Handle window close - clean up all resources."""
        self._log("Cerrando aplicación...")
        
        # Save window geometry
        try:
            self._settings.set("window_geometry", self.geometry())
        except Exception:
            pass
        
        # Stop player first (releases VLC resources)
        if self._player:
            try:
                self._player.cleanup()
            except Exception:
                pass
        
        # Stop recorder (kills all subprocesses)
        try:
            self._recorder.cleanup()
        except Exception:
            pass
        
        # Stop stream engine
        try:
            self._stream_engine.stop_stream()
        except Exception:
            pass
        
        # Stop clipboard monitor
        try:
            self._clipboard_monitor.stop()
        except Exception:
            pass
        
        self.destroy()
    
    def run(self) -> None:
        """Start the application main loop."""
        self.mainloop()
