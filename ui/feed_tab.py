"""
DouyinStream Pro - Feed Tab
Control center for the Feed Process (WebView2).
Display status and logs from the feed.
"""

import customtkinter as ctk
import subprocess
import sys
import os
import threading
from typing import Optional, Callable


class FeedTab(ctk.CTkFrame):
    """
    Tab for managing the Feed Mode.
    Launches 'run_feed.py' and listens for video clicks.
    """
    
    def __init__(self, master, on_play_hd: Callable[[str], None], **kwargs):
        super().__init__(master, **kwargs)
        
        self._on_play_hd = on_play_hd
        self._process: Optional[subprocess.Popen] = None
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Build the UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # Header
        header = ctk.CTkLabel(
            self, 
            text="📋 Feed Mode (WebView2)",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        header.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="w")
        
        # Description
        desc = ctk.CTkLabel(
            self,
            text=(
                "Navega por Douyin usando el motor Edge integrado.\n"
                "El algoritmo aprenderá de tus gustos automáticamente.\n"
                "Haz clic en el botón flotante '▶ Ver en HD' para reproducir aquí."
            ),
            font=ctk.CTkFont(size=14),
            justify="left",
            text_color="#aaa"
        )
        desc.grid(row=1, column=0, pady=(0, 20), padx=20, sticky="w")
        
        # Controls
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="nsew", padx=20)
        
        self._btn_launch = ctk.CTkButton(
            controls,
            text="🚀 Abrir Ventana de Feed",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            fg_color="#e94560",
            hover_color="#ff6b6b",
            command=self._launch_feed
        )
        self._btn_launch.pack(fill="x", pady=10)
        
        self._status_label = ctk.CTkLabel(
            controls,
            text="Estado: Inactivo",
            font=ctk.CTkFont(size=12),
            text_color="#666"
        )
        self._status_label.pack(pady=5)
        
        # Detected Videos Log
        ctk.CTkLabel(controls, text="Historial de Sesión:", anchor="w").pack(fill="x", pady=(20, 5))
        
        self._log_box = ctk.CTkTextbox(controls, height=200)
        self._log_box.pack(fill="x", expand=True)
        self._log_box.configure(state="disabled")
    
    def _launch_feed(self):
        """Launch the separate feed process."""
        if self._process and self._process.poll() is None:
            # Already running, focus it? (Hard to do without HWND)
            self._log_msg("⚠️ El Feed ya está corriendo")
            return
            
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "run_feed.py")
        
        if not os.path.exists(script_path):
            self._log_msg(f"❌ Error: No encuentro {script_path}")
            return
        
        try:
            # Launch process with pipe for stdout
            self._process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
            )
            
            self._status_label.configure(text="Estado: 🟢 Ejecutando", text_color="#2ecc71")
            self._btn_launch.configure(text="🔄 Reiniciar Feed", fg_color="#555")
            self._log_msg("🚀 Feed iniciado (WebView2)")
            
            # Start monitoring thread
            self._stop_event.clear()
            self._monitor_thread = threading.Thread(target=self._monitor_process, daemon=True)
            self._monitor_thread.start()
            
        except Exception as e:
            self._log_msg(f"❌ Error al iniciar: {e}")
    
    def _monitor_process(self):
        """Read stdout from feed process."""
        if not self._process:
            return
            
        while not self._stop_event.is_set():
            if self._process.poll() is not None:
                # Process died
                self.after(0, lambda: self._status_label.configure(text="Estado: ⚫ Detenido", text_color="#666"))
                self.after(0, lambda: self._btn_launch.configure(text="🚀 Abrir Ventana de Feed", fg_color="#e94560"))
                self.after(0, lambda: self._log_msg("⏹ Feed cerrado"))
                break
            
            # Read line
            line = self._process.stdout.readline()
            if line:
                line = line.strip()
                if line.startswith("VIDEO_HD:"):
                    url = line.split(":", 1)[1]
                    self.after(0, lambda u=url: self._handle_video(u))
                elif line:
                    # Debug log?
                    pass
    
    def _handle_video(self, url):
        """Handle Play HD request."""
        self._log_msg(f"🎬 Solicitud HD: {url[:40]}...")
        if self._on_play_hd:
            self._on_play_hd(url)
    
    def _log_msg(self, msg):
        """Add message to log."""
        self._log_box.configure(state="normal")
        self._log_box.insert("end", f"{msg}\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")
    
    def cleanup(self):
        """Kill process on exit."""
        self._stop_event.set()
        if self._process:
            self._process.terminate()
            self._process = None
