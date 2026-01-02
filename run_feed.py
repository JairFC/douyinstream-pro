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
    #douyin-hd-grp {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 2147483647; /* Max Z-Index */
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        pointer-events: none; /* Let clicks pass through container */
    }
    #douyin-hd-btn {
        pointer-events: auto;
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: white;
        padding: 12px 24px;
        border-radius: 12px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        transition: all 0.3s ease;
        display: none;
        align-items: center;
        gap: 8px;
    }
    #douyin-hd-btn:hover {
        background: rgba(255, 255, 255, 0.25);
        transform: translateY(-2px);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.5);
    }
    #douyin-hd-btn.visible {
        display: flex;
        animation: fadeIn 0.5s ease-out;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
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
    // Create Button Container
    if (!document.getElementById('douyin-hd-grp')) {
        var grp = document.createElement('div');
        grp.id = 'douyin-hd-grp';
        document.body.appendChild(grp);
        
        var btn = document.createElement('div');
        btn.id = 'douyin-hd-btn';
        btn.innerHTML = '<span>✨ Ver en HD</span>';
        grp.appendChild(btn);
        
        btn.onclick = function() {
            var currentUrl = window.location.href;
            // Provide visual feedback
            btn.innerHTML = '<span>⌛ Cargando...</span>';
            btn.style.background = 'rgba(46, 204, 113, 0.4)';
            setTimeout(() => {
                 btn.innerHTML = '<span>✨ Ver en HD</span>';
                 btn.style.background = '';
            }, 2000);
            
            pywebview.api.play_hd(currentUrl);
        };
    }
    
    // Logic to detect if a relevant video is present
    setInterval(function() {
        var btn = document.getElementById('douyin-hd-btn');
        var url = window.location.href;
        
        // 1. URL pattern check (Strong signal)
        var isVideoUrl = url.includes('/video/') || url.includes('modal_id=');
        
        // 2. DOM check (Medium signal - is there a video tag?)
        var videos = document.getElementsByTagName('video');
        var hasVideo = false;
        if (videos.length > 0) {
            // Check if any video is actually visible enough
            for(var i=0; i<videos.length; i++) {
                if (videos[i].videoWidth > 100) { // Filter out tiny preview videos
                    hasVideo = true;
                    break;
                }
            }
        }

        if (isVideoUrl || hasVideo) {
            if (!btn.classList.contains('visible')) {
                btn.classList.add('visible');
            }
            // Update title if possible
            try {
               var title = document.title.split(' - ')[0]; // Basic title cleanup
               if (title.length > 20) title = title.substring(0, 20) + '...';
               btn.innerHTML = '<span style="font-size:18px">▶</span> <div><div style="font-size:12px; opacity:0.8">Reproducir</div><div style="font-size:14px">'+title+'</div></div>';
            } catch(e) {}
        } else {
             btn.classList.remove('visible');
        }
    }, 800);
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
