"""
DouyinStream Pro - WebView Feed Window
Uses PyQt5 WebView to browse Douyin feed and extract videos for HD playback.
No account required - uses Douyin's algorithm-based recommendations.
"""

import sys
from typing import Optional, Callable
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QSplitter
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import QUrl, Qt, pyqtSignal
from PyQt5.QtGui import QFont


class DouyinWebPage(QWebEnginePage):
    """Custom web page to intercept video URLs."""
    
    url_detected = pyqtSignal(str)
    
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        """Intercept navigation requests to detect video URLs."""
        url_str = url.toString()
        
        # Detect Douyin video URLs
        if any(pattern in url_str for pattern in [
            '/video/', 'v.douyin.com', 'www.douyin.com/video'
        ]):
            # Emit signal with video URL
            self.url_detected.emit(url_str)
            # Allow navigation to continue
        
        return True


class WebViewFeedWindow(QMainWindow):
    """
    Feed window with embedded WebView for browsing Douyin.
    Left: WebView showing Douyin feed
    Right: Controls and currently playing video info
    """
    
    def __init__(self, on_video_selected: Optional[Callable[[str], None]] = None):
        super().__init__()
        
        self._on_video_selected = on_video_selected
        self._current_video_url = ""
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Build the UI."""
        self.setWindowTitle("DouyinStream Pro - Feed Mode")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0d0d1a;
            }
            QLabel {
                color: white;
                font-size: 13px;
            }
            QPushButton {
                background-color: #e94560;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff6b6b;
            }
            QPushButton:disabled {
                background-color: #444;
            }
            QFrame#sidebar {
                background-color: #1a1a2e;
                border-radius: 10px;
            }
        """)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout with splitter
        layout = QHBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # Left: WebView
        webview_container = QFrame()
        webview_layout = QVBoxLayout(webview_container)
        webview_layout.setContentsMargins(0, 0, 0, 0)
        
        # WebView
        self._webview = QWebEngineView()
        self._page = DouyinWebPage(self._webview)
        self._page.url_detected.connect(self._on_url_detected)
        self._webview.setPage(self._page)
        
        # Load Douyin main page (recommendations without login)
        self._webview.setUrl(QUrl("https://www.douyin.com/"))
        
        webview_layout.addWidget(self._webview)
        
        # Right: Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(280)
        sidebar.setMaximumWidth(350)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(15, 15, 15, 15)
        sidebar_layout.setSpacing(15)
        
        # Title
        title = QLabel("🎬 Feed Mode")
        title.setFont(QFont("", 16, QFont.Bold))
        sidebar_layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Navega por Douyin normalmente.\n\n"
            "Cuando encuentres un video que te guste,\n"
            "haz clic en 'Reproducir en HD' para verlo\n"
            "en máxima calidad."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #888;")
        sidebar_layout.addWidget(instructions)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #333;")
        sidebar_layout.addWidget(sep)
        
        # Current video info
        self._video_info = QLabel("No hay video detectado")
        self._video_info.setWordWrap(True)
        self._video_info.setStyleSheet("color: #aaa;")
        sidebar_layout.addWidget(self._video_info)
        
        # Play HD button
        self._play_btn = QPushButton("▶ Reproducir en HD")
        self._play_btn.clicked.connect(self._play_current_video)
        self._play_btn.setEnabled(False)
        sidebar_layout.addWidget(self._play_btn)
        
        # Spacer
        sidebar_layout.addStretch()
        
        # Navigation buttons
        nav_frame = QFrame()
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        
        back_btn = QPushButton("← Atrás")
        back_btn.setStyleSheet("background-color: #2d2d44;")
        back_btn.clicked.connect(self._webview.back)
        nav_layout.addWidget(back_btn)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet("background-color: #2d2d44;")
        refresh_btn.clicked.connect(self._webview.reload)
        nav_layout.addWidget(refresh_btn)
        
        sidebar_layout.addWidget(nav_frame)
        
        # URL entry for manual input
        self._url_label = QLabel("URL detectada:")
        self._url_label.setStyleSheet("color: #666; font-size: 10px;")
        sidebar_layout.addWidget(self._url_label)
        
        # Add to splitter
        splitter.addWidget(webview_container)
        splitter.addWidget(sidebar)
        splitter.setSizes([800, 300])
    
    def _on_url_detected(self, url: str):
        """Called when a video URL is detected."""
        self._current_video_url = url
        
        # Update UI
        short_url = url[:50] + "..." if len(url) > 50 else url
        self._video_info.setText(f"🎬 Video detectado:\n{short_url}")
        self._url_label.setText(f"URL: {url[:60]}...")
        self._play_btn.setEnabled(True)
    
    def _play_current_video(self):
        """Play the current detected video in HD."""
        if self._current_video_url and self._on_video_selected:
            self._on_video_selected(self._current_video_url)
    
    def get_current_url(self) -> str:
        """Get the currently detected video URL."""
        return self._current_video_url


def launch_webview_feed(on_video_selected: Optional[Callable[[str], None]] = None):
    """
    Launch the WebView feed window.
    This runs in its own QApplication since we're mixing with tkinter.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    window = WebViewFeedWindow(on_video_selected)
    window.show()
    
    # Don't call app.exec_() if running alongside tkinter
    # The window will be managed by the existing event loop
    return window


# Test
if __name__ == "__main__":
    def on_video(url):
        print(f"Video selected: {url}")
    
    app = QApplication(sys.argv)
    window = WebViewFeedWindow(on_video)
    window.show()
    app.exec_()
