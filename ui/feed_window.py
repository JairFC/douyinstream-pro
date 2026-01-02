"""
DouyinStream Pro - Feed Window
Scrollable video feed with max quality playback using yt-dlp + VLC.
"""

import customtkinter as ctk
from typing import Optional, Callable, List
import threading
from dataclasses import dataclass

from core.video_extractor import get_video_extractor, VideoInfo


@dataclass
class FeedItem:
    """Item in the video feed."""
    url: str
    title: str
    thumbnail: Optional[str] = None
    is_playing: bool = False


class FeedVideoCard(ctk.CTkFrame):
    """Card for a video in the feed."""
    
    def __init__(self, parent, item: FeedItem,
                 on_play: Optional[Callable[[str], None]] = None,
                 on_remove: Optional[Callable[[str], None]] = None,
                 **kwargs) -> None:
        super().__init__(parent, **kwargs)
        
        self._url = item.url
        self._on_play = on_play
        self._on_remove = on_remove
        
        self.configure(
            fg_color="#2d2d44" if not item.is_playing else "#3d5c3d",
            corner_radius=8,
            height=50
        )
        
        # Content
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=8)
        
        # Title
        title_text = item.title[:40] + "..." if len(item.title) > 40 else item.title
        title = ctk.CTkLabel(
            content,
            text=title_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        title.pack(side="left", fill="x", expand=True)
        
        # Play button
        play_btn = ctk.CTkButton(
            content,
            text="▶",
            width=30,
            height=25,
            fg_color="#e94560" if not item.is_playing else "#27ae60",
            hover_color="#ff6b6b",
            command=lambda: on_play(item.url) if on_play else None
        )
        play_btn.pack(side="right", padx=2)
        
        # Remove button
        remove_btn = ctk.CTkButton(
            content,
            text="✕",
            width=25,
            height=25,
            fg_color="#444",
            hover_color="#c0392b",
            command=lambda: on_remove(item.url) if on_remove else None
        )
        remove_btn.pack(side="right", padx=2)
    
    @property
    def url(self) -> str:
        return self._url


class FeedWindow(ctk.CTkToplevel):
    """
    Feed mode window with video list and VLC player.
    User pastes video URLs, app extracts max quality and plays in VLC.
    """
    
    def __init__(self, parent, vlc_lib_path: Optional[str] = None) -> None:
        super().__init__(parent)
        
        self._parent = parent
        self._vlc_lib_path = vlc_lib_path
        self._extractor = get_video_extractor()
        self._feed_items: List[FeedItem] = []
        self._current_index = 0
        self._player = None
        
        self._setup_window()
        self._build_ui()
    
    def _setup_window(self) -> None:
        """Configure window properties."""
        self.title("DouyinStream Pro - Feed Mode")
        self.geometry("1100x700")
        self.minsize(900, 600)
        
        # Center on parent
        self.transient(self._parent)
        self.update_idletasks()
        
        parent_x = self._parent.winfo_rootx()
        parent_y = self._parent.winfo_rooty()
        parent_w = self._parent.winfo_width()
        parent_h = self._parent.winfo_height()
        
        x = parent_x + (parent_w - 1100) // 2
        y = parent_y + (parent_h - 700) // 2
        
        self.geometry(f"1100x700+{x}+{y}")
    
    def _build_ui(self) -> None:
        """Build the feed mode UI."""
        self.configure(fg_color="#0d0d1a")
        
        # Main container
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Left panel: Video list
        left_panel = ctk.CTkFrame(main, width=300, fg_color="#1a1a2e", corner_radius=10)
        left_panel.pack(side="left", fill="y", padx=(0, 10))
        left_panel.pack_propagate(False)
        
        # Header
        header = ctk.CTkFrame(left_panel, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            header,
            text="📋 Lista de Videos",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")
        
        # Add URL input
        input_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        input_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self._url_input = ctk.CTkEntry(
            input_frame,
            placeholder_text="Pega URL de video...",
            height=35
        )
        self._url_input.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self._url_input.bind("<Return>", lambda e: self._add_video())
        
        add_btn = ctk.CTkButton(
            input_frame,
            text="+",
            width=35,
            height=35,
            fg_color="#27ae60",
            hover_color="#2ecc71",
            command=self._add_video
        )
        add_btn.pack(side="right")
        
        # Video list (scrollable)
        self._list_scroll = ctk.CTkScrollableFrame(
            left_panel,
            fg_color="transparent"
        )
        self._list_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Navigation buttons
        nav_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        nav_frame.pack(fill="x", padx=10, pady=10)
        
        self._prev_btn = ctk.CTkButton(
            nav_frame,
            text="⬆ Anterior",
            width=100,
            fg_color="#2d2d44",
            hover_color="#3d3d5c",
            command=self._play_previous
        )
        self._prev_btn.pack(side="left", padx=5)
        
        self._next_btn = ctk.CTkButton(
            nav_frame,
            text="Siguiente ⬇",
            width=100,
            fg_color="#e94560",
            hover_color="#ff6b6b",
            command=self._play_next
        )
        self._next_btn.pack(side="right", padx=5)
        
        # Right panel: VLC Player
        right_panel = ctk.CTkFrame(main, fg_color="#0d0d1a", corner_radius=10)
        right_panel.pack(side="right", fill="both", expand=True)
        
        # Player area
        player_frame = ctk.CTkFrame(right_panel, fg_color="#000", corner_radius=10)
        player_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create VLC player
        try:
            from ui.embedded_player import EmbeddedPlayer
            self._player = EmbeddedPlayer(player_frame, vlc_lib_path=self._vlc_lib_path)
            self._player.pack(fill="both", expand=True)
        except Exception as e:
            print(f"[FeedWindow] VLC error: {e}")
            placeholder = ctk.CTkLabel(
                player_frame,
                text="🎬\n\nReproductor no disponible",
                font=ctk.CTkFont(size=18),
                text_color="#666"
            )
            placeholder.pack(expand=True)
        
        # Status bar
        status_frame = ctk.CTkFrame(right_panel, fg_color="#1a1a2e", height=40, corner_radius=8)
        status_frame.pack(fill="x", padx=10, pady=(0, 10))
        status_frame.pack_propagate(False)
        
        self._status_label = ctk.CTkLabel(
            status_frame,
            text="Agrega URLs de videos para empezar",
            font=ctk.CTkFont(size=12),
            text_color="#888"
        )
        self._status_label.pack(pady=10)
    
    def _add_video(self) -> None:
        """Add a video URL to the feed."""
        url = self._url_input.get().strip()
        if not url:
            return
        
        # Clear input
        self._url_input.delete(0, "end")
        
        # Show loading status
        self._status_label.configure(text=f"🔄 Extrayendo video...")
        
        # Extract video info async
        def on_extract(info: Optional[VideoInfo]):
            if info:
                # Add to feed
                item = FeedItem(
                    url=url,
                    title=info.title,
                    thumbnail=info.thumbnail
                )
                self._feed_items.append(item)
                
                # Update UI on main thread
                self.after(0, self._refresh_list)
                self.after(0, lambda: self._status_label.configure(
                    text=f"✅ Agregado: {info.title[:30]}..."
                ))
                
                # Auto-play if first video
                if len(self._feed_items) == 1:
                    self.after(100, lambda: self._play_video(0))
            else:
                self.after(0, lambda: self._status_label.configure(
                    text="❌ Error al extraer video"
                ))
        
        self._extractor.extract_async(url, on_extract)
    
    def _refresh_list(self) -> None:
        """Refresh the video list UI."""
        # Clear existing
        for widget in self._list_scroll.winfo_children():
            widget.destroy()
        
        # Add cards
        for i, item in enumerate(self._feed_items):
            item.is_playing = (i == self._current_index)
            card = FeedVideoCard(
                self._list_scroll,
                item=item,
                on_play=lambda url, idx=i: self._play_video(idx),
                on_remove=lambda url: self._remove_video(url)
            )
            card.pack(fill="x", pady=3)
    
    def _play_video(self, index: int) -> None:
        """Play video at given index."""
        if index < 0 or index >= len(self._feed_items):
            return
        
        self._current_index = index
        item = self._feed_items[index]
        
        self._status_label.configure(text=f"🎬 Cargando: {item.title[:30]}...")
        self._refresh_list()
        
        # Extract and play
        def on_extract(info: Optional[VideoInfo]):
            if info and self._player:
                self.after(0, lambda: self._player.play_url(info.direct_url))
                self.after(0, lambda: self._status_label.configure(
                    text=f"▶ {info.title[:40]} | {info.quality}"
                ))
            else:
                self.after(0, lambda: self._status_label.configure(
                    text="❌ Error al reproducir"
                ))
        
        self._extractor.extract_async(item.url, on_extract)
    
    def _play_next(self) -> None:
        """Play next video in the list."""
        if self._current_index < len(self._feed_items) - 1:
            self._play_video(self._current_index + 1)
    
    def _play_previous(self) -> None:
        """Play previous video in the list."""
        if self._current_index > 0:
            self._play_video(self._current_index - 1)
    
    def _remove_video(self, url: str) -> None:
        """Remove a video from the feed."""
        self._feed_items = [item for item in self._feed_items if item.url != url]
        
        # Adjust current index if needed
        if self._current_index >= len(self._feed_items):
            self._current_index = max(0, len(self._feed_items) - 1)
        
        self._refresh_list()
    
    def destroy(self) -> None:
        """Clean up before destroying."""
        if self._player:
            self._player.stop()
        super().destroy()
