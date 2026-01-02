"""
DouyinStream Pro - Feed Launcher
Launches WebView feed in a separate process to avoid PyQt5/Tkinter conflicts.
"""

import subprocess
import sys
import os
from typing import Optional


def launch_feed_process() -> Optional[subprocess.Popen]:
    """
    Launch the feed WebView in a separate Python process.
    This avoids conflicts between PyQt5 and Tkinter.
    """
    # Get the path to the feed script
    feed_script = os.path.join(os.path.dirname(__file__), "webview_feed.py")
    
    if not os.path.exists(feed_script):
        print(f"[FeedLauncher] Script not found: {feed_script}")
        return None
    
    try:
        # Launch in separate process
        process = subprocess.Popen(
            [sys.executable, feed_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
        )
        print(f"[FeedLauncher] Feed process started (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"[FeedLauncher] Error launching feed: {e}")
        return None


if __name__ == "__main__":
    # Test launch
    proc = launch_feed_process()
    if proc:
        print(f"Feed running with PID: {proc.pid}")
