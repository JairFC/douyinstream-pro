"""
Console Helper - Centers console window on the mouse cursor's monitor.
DPI awareness must be enabled in main.py BEFORE this runs.
"""
import ctypes
import ctypes.wintypes
import time

def get_monitor_at_cursor():
    """Get monitor bounds (x, y, w, h) at current cursor position using Windows API."""
    try:
        user32 = ctypes.windll.user32
        
        # Get cursor position
        point = ctypes.wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(point))
        
        # Get monitor from point
        MONITOR_DEFAULTTONEAREST = 2
        hMonitor = user32.MonitorFromPoint(point, MONITOR_DEFAULTTONEAREST)
        
        # Get monitor info
        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.wintypes.DWORD),
                ("rcMonitor", ctypes.wintypes.RECT),
                ("rcWork", ctypes.wintypes.RECT),
                ("dwFlags", ctypes.wintypes.DWORD),
            ]
        
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi))
        
        r = mi.rcWork  # Use work area (excludes taskbar)
        return (r.left, r.top, r.right - r.left, r.bottom - r.top)
        
    except Exception:
        return (0, 0, 1920, 1080)

def center_console_on_mouse_monitor():
    """Move the console window to the monitor where the mouse cursor is."""
    try:
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        
        hwnd = kernel32.GetConsoleWindow()
        if not hwnd:
            return
        
        # Get monitor bounds at cursor
        mon_x, mon_y, mon_w, mon_h = get_monitor_at_cursor()
        
        # Get current window size
        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        win_w = rect.right - rect.left
        win_h = rect.bottom - rect.top
        
        # Calculate centered position
        x = mon_x + (mon_w - win_w) // 2
        y = mon_y + (mon_h - win_h) // 2
        
        # Move window (SWP_NOSIZE | SWP_NOZORDER)
        user32.SetWindowPos(hwnd, 0, x, y, 0, 0, 0x0001 | 0x0004)
        
    except Exception as e:
        print(f"Console position error: {e}")

if __name__ == "__main__":
    center_console_on_mouse_monitor()
