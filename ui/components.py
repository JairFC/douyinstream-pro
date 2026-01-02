"""
DouyinStream Pro - Custom UI Components
Modern CTk widgets for the application.
"""

import customtkinter as ctk
from typing import Callable, Optional, List
from PIL import Image
import threading


class ToastNotification(ctk.CTkFrame):
    """
    Animated toast notification for clipboard detection.
    Slides in from top-right and auto-dismisses.
    """
    
    def __init__(self, parent: ctk.CTk, message: str, 
                 on_action: Optional[Callable] = None,
                 action_text: str = "Reproducir",
                 duration_ms: int = 5000) -> None:
        super().__init__(parent, corner_radius=10)
        
        self._parent = parent
        self._on_action = on_action
        self._duration = duration_ms
        self._dismissed = False
        
        # Configure appearance
        self.configure(fg_color=("#1a1a2e", "#1a1a2e"))
        
        # Content frame
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=12)
        
        # Icon
        icon_label = ctk.CTkLabel(
            content, 
            text="🔗", 
            font=ctk.CTkFont(size=24)
        )
        icon_label.pack(side="left", padx=(0, 10))
        
        # Text container
        text_frame = ctk.CTkFrame(content, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True)
        
        # Title
        title = ctk.CTkLabel(
            text_frame,
            text="URL Detectada",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#e94560"
        )
        title.pack(anchor="w")
        
        # Message (truncated URL)
        display_msg = message[:50] + "..." if len(message) > 50 else message
        msg_label = ctk.CTkLabel(
            text_frame,
            text=display_msg,
            font=ctk.CTkFont(size=12),
            text_color="#a0a0a0"
        )
        msg_label.pack(anchor="w")
        
        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(side="right", padx=(10, 0))
        
        if on_action:
            action_btn = ctk.CTkButton(
                btn_frame,
                text=action_text,
                width=90,
                height=32,
                fg_color="#e94560",
                hover_color="#ff6b6b",
                command=self._on_action_click
            )
            action_btn.pack(side="left", padx=(0, 5))
        
        close_btn = ctk.CTkButton(
            btn_frame,
            text="✕",
            width=32,
            height=32,
            fg_color="transparent",
            hover_color="#333",
            command=self.dismiss
        )
        close_btn.pack(side="left")
        
        # Auto-dismiss timer
        if duration_ms > 0:
            self.after(duration_ms, self.dismiss)
    
    def _on_action_click(self) -> None:
        if self._on_action:
            self._on_action()
        self.dismiss()
    
    def show(self, x: int = None, y: int = None) -> None:
        """Show toast at position (default: top-right)."""
        self.update_idletasks()
        
        if x is None:
            x = self._parent.winfo_width() - self.winfo_reqwidth() - 20
        if y is None:
            y = 20
        
        self.place(x=x, y=y)
        self.lift()
    
    def dismiss(self) -> None:
        """Dismiss the toast."""
        if not self._dismissed:
            self._dismissed = True
            self.place_forget()
            self.destroy()


class CollapsibleSection(ctk.CTkFrame):
    """
    Collapsible section with header and expandable content.
    Click header to toggle content visibility.
    """
    
    def __init__(self, parent, title: str, icon: str = "", 
                 expanded: bool = True, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        
        self._title = title
        self._icon = icon
        self._expanded = expanded
        
        self.configure(fg_color="#1a1a2e", corner_radius=10)
        
        # Header (always visible)
        self._header = ctk.CTkFrame(self, fg_color="transparent", cursor="hand2")
        self._header.pack(fill="x", padx=10, pady=(8, 0))
        
        # Header left side
        header_left = ctk.CTkFrame(self._header, fg_color="transparent")
        header_left.pack(side="left", fill="x", expand=True)
        
        # Collapse indicator
        self._arrow = ctk.CTkLabel(
            header_left,
            text="▼" if expanded else "▶",
            font=ctk.CTkFont(size=10),
            text_color="#888"
        )
        self._arrow.pack(side="left", padx=(0, 5))
        
        # Title with icon
        title_text = f"{icon} {title}" if icon else title
        self._title_label = ctk.CTkLabel(
            header_left,
            text=title_text,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self._title_label.pack(side="left")
        
        # Content frame (collapsible)
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        if expanded:
            self._content.pack(fill="both", expand=True, padx=10, pady=8)
        
        # Bind click events
        self._header.bind("<Button-1>", lambda e: self.toggle())
        self._arrow.bind("<Button-1>", lambda e: self.toggle())
        self._title_label.bind("<Button-1>", lambda e: self.toggle())
        header_left.bind("<Button-1>", lambda e: self.toggle())
    
    def get_content_frame(self) -> ctk.CTkFrame:
        """Get the content frame to add widgets to."""
        return self._content
    
    def toggle(self) -> None:
        """Toggle expanded/collapsed state."""
        self._expanded = not self._expanded
        
        if self._expanded:
            self._arrow.configure(text="▼")
            self._content.pack(fill="both", expand=True, padx=10, pady=8)
        else:
            self._arrow.configure(text="▶")
            self._content.pack_forget()
    
    def expand(self) -> None:
        """Expand the section."""
        if not self._expanded:
            self.toggle()
    
    def collapse(self) -> None:
        """Collapse the section."""
        if self._expanded:
            self.toggle()
    
    def is_expanded(self) -> bool:
        return self._expanded


class StatusIndicator(ctk.CTkFrame):
    """
    LED-style status indicator.
    Shows different colors for different states.
    """
    
    COLORS = {
        "offline": "#666666",
        "connecting": "#f39c12",
        "streaming": "#27ae60",
        "recording": "#e74c3c",
        "buffering": "#3498db",
        "error": "#c0392b"
    }
    
    def __init__(self, parent, size: int = 12, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        
        self._size = size
        self._state = "offline"
        self._blinking = False
        
        self.configure(fg_color="transparent")
        
        # LED dot
        self._led = ctk.CTkLabel(
            self,
            text="●",
            font=ctk.CTkFont(size=size),
            text_color=self.COLORS["offline"]
        )
        self._led.pack()
        
        # Status text
        self._label = ctk.CTkLabel(
            self,
            text="Offline",
            font=ctk.CTkFont(size=11),
            text_color="#888"
        )
        self._label.pack()
    
    def set_state(self, state: str, text: str = None) -> None:
        """Update indicator state."""
        self._state = state
        color = self.COLORS.get(state, self.COLORS["offline"])
        self._led.configure(text_color=color)
        
        if text:
            self._label.configure(text=text)
        else:
            self._label.configure(text=state.capitalize())
    
    def start_blink(self) -> None:
        """Start blinking animation."""
        self._blinking = True
        self._blink_cycle()
    
    def stop_blink(self) -> None:
        """Stop blinking animation."""
        self._blinking = False
    
    def _blink_cycle(self) -> None:
        if self._blinking:
            current = self._led.cget("text_color")
            new_color = "#333" if current != "#333" else self.COLORS.get(self._state, "#666")
            self._led.configure(text_color=new_color)
            self.after(500, self._blink_cycle)


class QualitySelector(ctk.CTkFrame):
    """
    Dropdown for stream quality selection.
    Supports live switching.
    """
    
    QUALITIES = [
        ("Origin (Mejor)", "best"),
        ("1080p", "1080p,1080p60,best"),
        ("720p", "720p,720p60,1080p,best"),
        ("480p", "480p,720p,best"),
        ("Solo Audio", "audio_only,audio,worst"),
    ]
    
    def __init__(self, parent, on_change: Optional[Callable[[str], None]] = None, 
                 **kwargs) -> None:
        super().__init__(parent, **kwargs)
        
        self._on_change = on_change
        self._current_value = "best"
        
        self.configure(fg_color="transparent")
        
        # Label
        label = ctk.CTkLabel(
            self,
            text="Calidad:",
            font=ctk.CTkFont(size=12)
        )
        label.pack(side="left", padx=(0, 5))
        
        # Dropdown
        values = [q[0] for q in self.QUALITIES]
        self._dropdown = ctk.CTkOptionMenu(
            self,
            values=values,
            width=140,
            height=28,
            fg_color="#2d2d44",
            button_color="#3d3d5c",
            button_hover_color="#4d4d6c",
            dropdown_fg_color="#2d2d44",
            dropdown_hover_color="#3d3d5c",
            command=self._on_select
        )
        self._dropdown.pack(side="left")
        self._dropdown.set(values[0])
    
    def _on_select(self, display_name: str) -> None:
        for name, value in self.QUALITIES:
            if name == display_name:
                self._current_value = value
                if self._on_change:
                    self._on_change(value)
                break
    
    def get_value(self) -> str:
        return self._current_value
    
    def set_value(self, value: str) -> None:
        for name, val in self.QUALITIES:
            if val == value:
                self._dropdown.set(name)
                self._current_value = value
                break


class HistoryCard(ctk.CTkFrame):
    """
    Card widget for history/favorites display.
    Shows alias, streamer info, and context actions.
    """
    
    def __init__(self, parent, 
                 url: str,
                 title: str,
                 alias: str = "",
                 is_favorite: bool = False,
                 play_count: int = 0,
                 on_play: Optional[Callable] = None,
                 on_edit_alias: Optional[Callable] = None,
                 on_toggle_favorite: Optional[Callable] = None,
                 on_delete: Optional[Callable] = None,
                 **kwargs) -> None:
        super().__init__(parent, **kwargs)
        
        self._url = url
        self._alias = alias
        self._is_favorite = is_favorite
        self._on_play = on_play
        self._on_edit_alias = on_edit_alias
        self._on_toggle_favorite = on_toggle_favorite
        self._on_delete = on_delete
        
        self.configure(
            fg_color=("#2d2d44", "#2d2d44"),
            corner_radius=8,
            height=60
        )
        
        # Main content
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=8)
        
        # Left side: info
        info_frame = ctk.CTkFrame(content, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)
        
        # Title row with live status indicator
        title_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        title_row.pack(anchor="w")
        
        # Live status indicator (🟢 live, ⚫ offline, ⚪ unknown)
        self._live_status: Optional[bool] = None
        self._status_indicator = ctk.CTkLabel(
            title_row,
            text="⚪",  # Unknown initially
            font=ctk.CTkFont(size=10),
            text_color="#666"
        )
        self._status_indicator.pack(side="left", padx=(0, 4))
        
        # Title/Alias
        display_text = alias if alias else title
        self._title_label = ctk.CTkLabel(
            title_row,
            text=display_text,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        )
        self._title_label.pack(side="left")
        
        # Subtitle (URL preview)
        url_preview = url[:40] + "..." if len(url) > 40 else url
        subtitle = ctk.CTkLabel(
            info_frame,
            text=f"▶ {play_count}  •  {url_preview}",
            font=ctk.CTkFont(size=10),
            text_color="#888",
            anchor="w"
        )
        subtitle.pack(anchor="w")
        
        # Right side: actions
        action_frame = ctk.CTkFrame(content, fg_color="transparent")
        action_frame.pack(side="right")
        
        # Favorite star
        fav_text = "★" if is_favorite else "☆"
        fav_color = "#f1c40f" if is_favorite else "#666"
        self._fav_btn = ctk.CTkButton(
            action_frame,
            text=fav_text,
            width=30,
            height=30,
            fg_color="transparent",
            hover_color="#3d3d5c",
            text_color=fav_color,
            font=ctk.CTkFont(family="Arial", size=20),  # Force Arial for unicode support
            command=self._toggle_favorite
        )
        self._fav_btn.pack(side="left", padx=2)
        
        # Play button
        play_btn = ctk.CTkButton(
            action_frame,
            text="▶",
            width=30,
            height=30,
            fg_color="#e94560",
            hover_color="#ff6b6b",
            command=self._play
        )
        play_btn.pack(side="left", padx=2)
        
        # Bind right-click for context menu
        self.bind("<Button-3>", self._show_context_menu)
        content.bind("<Button-3>", self._show_context_menu)
        info_frame.bind("<Button-3>", self._show_context_menu)
        self._title_label.bind("<Button-3>", self._show_context_menu)
        
        # Bind left-click to play (single click on card area)
        self.bind("<Button-1>", lambda e: self._play())
        content.bind("<Button-1>", lambda e: self._play())
        info_frame.bind("<Button-1>", lambda e: self._play())
        self._title_label.bind("<Button-1>", lambda e: self._play())
        subtitle.bind("<Button-1>", lambda e: self._play())
        
        # Add hover effect
        self.bind("<Enter>", lambda e: self.configure(fg_color="#3d3d5c"))
        self.bind("<Leave>", lambda e: self.configure(fg_color="#2d2d44"))
        
        # Change cursor to hand to indicate clickable
        self.configure(cursor="hand2")
        content.configure(cursor="hand2")
        info_frame.configure(cursor="hand2")
    
    def _play(self) -> None:
        if self._on_play:
            self._on_play(self._url)
    
    def _toggle_favorite(self) -> None:
        if self._on_toggle_favorite:
            self._on_toggle_favorite(self._url)
        self._is_favorite = not self._is_favorite
        self._fav_btn.configure(
            text="★" if self._is_favorite else "☆",
            text_color="#f1c40f" if self._is_favorite else "#666"
        )
    
    def _show_context_menu(self, event) -> None:
        """Show right-click context menu."""
        menu = ctk.CTkFrame(self.winfo_toplevel(), fg_color="#2d2d44", corner_radius=8)
        
        # Edit alias
        edit_btn = ctk.CTkButton(
            menu,
            text="✏️ Editar Alias",
            fg_color="transparent",
            hover_color="#3d3d5c",
            anchor="w",
            command=lambda: [menu.destroy(), self._edit_alias()]
        )
        edit_btn.pack(fill="x", padx=5, pady=2)
        
        # Toggle favorite
        fav_text = "☆ Quitar Favorito" if self._is_favorite else "★ Añadir Favorito"
        fav_btn = ctk.CTkButton(
            menu,
            text=fav_text,
            fg_color="transparent",
            hover_color="#3d3d5c",
            anchor="w",
            command=lambda: [menu.destroy(), self._toggle_favorite()]
        )
        fav_btn.pack(fill="x", padx=5, pady=2)
        
        # Delete
        del_btn = ctk.CTkButton(
            menu,
            text="🗑️ Eliminar",
            fg_color="transparent",
            hover_color="#e74c3c",
            anchor="w",
            command=lambda: [menu.destroy(), self._delete()]
        )
        del_btn.pack(fill="x", padx=5, pady=2)
        
        # Position menu at mouse location (relative to toplevel window)
        toplevel = self.winfo_toplevel()
        menu_x = event.x_root - toplevel.winfo_rootx()
        menu_y = event.y_root - toplevel.winfo_rooty()
        menu.place(x=menu_x, y=menu_y)
        menu.lift()
        
        # Close on click outside
        def close_menu(e):
            if e.widget != menu and not str(e.widget).startswith(str(menu)):
                menu.destroy()
        
        self.winfo_toplevel().bind("<Button-1>", close_menu, add="+")
    
    def _edit_alias(self) -> None:
        if self._on_edit_alias:
            self._on_edit_alias(self._url, self._alias)
    
    def _delete(self) -> None:
        if self._on_delete:
            self._on_delete(self._url)
    
    @property
    def url(self) -> str:
        """Get the URL for this card."""
        return self._url
    
    def set_live_status(self, is_live: Optional[bool]) -> None:
        """Update the live status indicator.
        
        Args:
            is_live: True = live (🟢), False = offline (⚫), None = unknown (⚪)
        """
        self._live_status = is_live
        
        if is_live is True:
            self._status_indicator.configure(text="🟢", text_color="#2ecc71")
        elif is_live is False:
            self._status_indicator.configure(text="🔴", text_color="#e74c3c")  # Red for offline
        else:
            self._status_indicator.configure(text="⚪", text_color="#888")


class BufferProgressBar(ctk.CTkFrame):
    """
    Progress bar showing clip buffer status.
    Displays current buffer vs max capacity.
    """
    
    def __init__(self, parent, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        
        self.configure(fg_color="transparent")
        
        # Label
        self._label = ctk.CTkLabel(
            self,
            text="Buffer: 0:00 / 3:00",
            font=ctk.CTkFont(size=11),
            text_color="#888"
        )
        self._label.pack(anchor="w")
        
        # Progress bar
        self._progress = ctk.CTkProgressBar(
            self,
            width=200,
            height=8,
            fg_color="#2d2d44",
            progress_color="#3498db"
        )
        self._progress.pack(fill="x", pady=(2, 0))
        self._progress.set(0)
    
    def update_buffer(self, current_seconds: float, max_seconds: float) -> None:
        """Update buffer display."""
        progress = min(current_seconds / max_seconds, 1.0) if max_seconds > 0 else 0
        self._progress.set(progress)
        
        current_str = f"{int(current_seconds // 60)}:{int(current_seconds % 60):02d}"
        max_str = f"{int(max_seconds // 60)}:{int(max_seconds % 60):02d}"
        self._label.configure(text=f"Buffer: {current_str} / {max_str}")
        
        # Change color when full
        if progress >= 1.0:
            self._progress.configure(progress_color="#27ae60")
        else:
            self._progress.configure(progress_color="#3498db")


class ConsoleViewer(ctk.CTkFrame):
    """
    Collapsible console/log viewer widget.
    Shows debug output in scrollable text area.
    """
    
    MAX_LINES = 500
    
    def __init__(self, parent, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        
        self._expanded = False
        self._lines: List[str] = []
        
        self.configure(fg_color="#1a1a2e", corner_radius=8)
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=5)
        
        self._toggle_btn = ctk.CTkButton(
            header,
            text="📋 Console ▼",
            fg_color="transparent",
            hover_color="#2d2d44",
            anchor="w",
            command=self.toggle
        )
        self._toggle_btn.pack(side="left")
        
        clear_btn = ctk.CTkButton(
            header,
            text="Limpiar",
            width=60,
            height=24,
            fg_color="#2d2d44",
            hover_color="#3d3d5c",
            font=ctk.CTkFont(size=11),
            command=self.clear
        )
        clear_btn.pack(side="right")
        
        # Text area (initially hidden)
        self._text_frame = ctk.CTkFrame(self, fg_color="transparent")
        
        self._textbox = ctk.CTkTextbox(
            self._text_frame,
            height=150,
            fg_color="#0d0d1a",
            text_color="#00ff00",
            font=ctk.CTkFont(family="Consolas", size=11),
            state="disabled"
        )
        self._textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    
    def toggle(self) -> None:
        """Toggle console visibility."""
        self._expanded = not self._expanded
        
        if self._expanded:
            self._text_frame.pack(fill="both", expand=True)
            self._toggle_btn.configure(text="📋 Console ▲")
        else:
            self._text_frame.pack_forget()
            self._toggle_btn.configure(text="📋 Console ▼")
    
    def log(self, message: str) -> None:
        """Add log message."""
        self._lines.append(message)
        
        # Trim if too many lines
        if len(self._lines) > self.MAX_LINES:
            self._lines = self._lines[-self.MAX_LINES:]
        
        self._textbox.configure(state="normal")
        self._textbox.insert("end", message + "\n")
        self._textbox.see("end")
        self._textbox.configure(state="disabled")
    
    def clear(self) -> None:
        """Clear console."""
        self._lines.clear()
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.configure(state="disabled")
    
    def is_expanded(self) -> bool:
        return self._expanded


class AliasEditDialog(ctk.CTkToplevel):
    """
    Modal dialog for editing stream alias.
    """
    
    def __init__(self, parent, current_alias: str = "",
                 on_save: Optional[Callable[[str], None]] = None) -> None:
        super().__init__(parent)
        
        self._on_save = on_save
        self._result: Optional[str] = None
        
        self.title("Editar Alias")
        self.resizable(False, False)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Calculate center position on parent window
        self.withdraw()  # Hide while positioning
        self.update_idletasks()
        
        dialog_w = 400
        dialog_h = 150
        
        # Get parent position and size
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        
        # Center on parent
        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2
        
        self.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")
        self.deiconify()  # Show now that it's positioned
        
        # Content
        ctk.CTkLabel(
            self,
            text="Nombre/Alias del Stream:",
            font=ctk.CTkFont(size=13)
        ).pack(pady=(20, 5))
        
        self._entry = ctk.CTkEntry(
            self,
            width=300,
            height=35,
            placeholder_text="Ej: Mi streamer favorito"
        )
        self._entry.pack(pady=5)
        self._entry.insert(0, current_alias)
        
        # Force focus after dialog is shown
        self.after(100, lambda: self._entry.focus_force())
        
        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            width=100,
            fg_color="#666",
            hover_color="#888",
            command=self.destroy
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Guardar",
            width=100,
            fg_color="#e94560",
            hover_color="#ff6b6b",
            command=self._save
        ).pack(side="left", padx=5)
        
        # Enter key to save
        self._entry.bind("<Return>", lambda e: self._save())
    
    def _save(self) -> None:
        alias = self._entry.get().strip()
        if self._on_save:
            self._on_save(alias)
        self.destroy()
