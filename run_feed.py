"""
DouyinStream Pro - Feed Process
Runs the modern WebView (Edge) for Douyin feed.
Communicates with main app via stdout.
"""

import webview
import sys
import threading
import time
import os

class FeedApi:
    """API exposed to JavaScript."""
    
    def play_hd(self, url):
        """Called from JS when user clicks 'Play HD'."""
        # Print special tag for main app to parse
        print(f"VIDEO_HD:{url}", flush=True)

def inject_styles(window):
    """Inject CSS for the HD button."""
    css = """
    #douyin-hd-btn {
        position: fixed;
        bottom: 100px;
        right: 20px;
        z-index: 99999;
        background: linear-gradient(45deg, #ff0050, #00f2ea);
        color: white;
        padding: 12px 24px;
        border-radius: 30px;
        font-family: sans-serif;
        font-weight: bold;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        border: 2px solid white;
        transition: transform 0.2s;
        display: none; /* Hidden by default */
    }
    #douyin-hd-btn:hover {
        transform: scale(1.05);
    }
    """
    # Inject CSS
    js = f"""
    var style = document.createElement('style');
    style.innerHTML = `{css}`;
    document.head.appendChild(style);
    """
    window.evaluate_js(js)

def inject_interface(window):
    """Inject the button and detection logic."""
    js = """
    // Create Button
    if (!document.getElementById('douyin-hd-btn')) {
        var btn = document.createElement('div');
        btn.id = 'douyin-hd-btn';
        btn.innerHTML = '▶ Ver en HD';
        document.body.appendChild(btn);
        
        btn.onclick = function() {
            var currentUrl = window.location.href;
            pywebview.api.play_hd(currentUrl);
        };
    }
    
    // Monitor URL changes and Show/Hide button
    setInterval(function() {
        var url = window.location.href;
        var btn = document.getElementById('douyin-hd-btn');
        
        // Simple heuristic: Show button if we are on a likely video page or modal
        var isVideo = url.includes('/video/') || url.includes('modal_id=');
        
        // Also check if there is a video element playing
        var videos = document.getElementsByTagName('video');
        var hasVideo = videos.length > 0;

        if (isVideo || hasVideo) {
            btn.style.display = 'block';
            try {
               // Update text if we can find title
               var title = document.title;
               if (title.length > 15) title = title.substring(0, 15) + '...';
               btn.innerHTML = '▶ Ver en HD <br><span style="font-size:10px">' + title + '</span>';
            } catch(e) {}
        } else {
             btn.style.display = 'none';
        }
    }, 1000);
    """
    window.evaluate_js(js)

def on_loaded(window):
    """Called when DOM is ready."""
    # Wait a bit for page load then inject
    time.sleep(1)
    inject_styles(window)
    inject_interface(window)

if __name__ == '__main__':
    # Ensure data dir exists (absolute path)
    data_dir = os.path.abspath("data/webview_cache")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)

    api = FeedApi()
    
    # Create window with Edge WebView2
    window = webview.create_window(
        'Douyin Feed - DouyinStream Pro',
        'https://www.douyin.com',
        js_api=api,
        width=1280,
        height=800,
        background_color='#000000',
        text_select=True
    )
    
    # Start (this blocks)
    webview.start(on_loaded, window, private_mode=False, storage_path=data_dir)
