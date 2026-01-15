import ctypes
import ctypes.wintypes
from typing import Tuple, List, Optional

# Structs for ctypes
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
    ]

class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", ctypes.wintypes.DWORD),
    ]

def get_monitor_at_point(x: int, y: int) -> Tuple[int, int, int, int]:
    """
    Get the monitor bounds (x, y, w, h) that contains the given point.
    Uses Windows native API for robust multi-monitor support.
    """
    try:
        user32 = ctypes.windll.user32
        
        # MonitorFromPoint constants
        MONITOR_DEFAULTTONULL = 0
        MONITOR_DEFAULTTOPRIMARY = 1
        MONITOR_DEFAULTTONEAREST = 2
        
        pt = POINT()
        pt.x = x
        pt.y = y
        
        # Get handle to monitor
        hMonitor = user32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
        
        # Get monitor info
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi))
        
        # Calculate dimensions
        r = mi.rcMonitor
        return (r.left, r.top, r.right - r.left, r.bottom - r.top)
        
    except Exception as e:
        print(f"[MonitorUtils] Error detecting monitor: {e}")
        # Fallback to standard 1080p primary
        return (0, 0, 1920, 1080)

def get_all_monitors() -> List[Tuple[int, int, int, int]]:
    """
    Get bounds (x, y, w, h) for all connected monitors.
    Uses Windows EnumDisplayMonitors API.
    """
    monitors = []
    
    try:
        user32 = ctypes.windll.user32
        
        # Callback type for EnumDisplayMonitors
        MONITORENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            ctypes.c_void_p,  # hMonitor
            ctypes.c_void_p,  # hdcMonitor
            ctypes.POINTER(RECT),  # lprcMonitor
            ctypes.c_long  # dwData
        )
        
        def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi))
            r = mi.rcMonitor
            monitors.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
            return True
        
        # Enumerate all monitors
        user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(callback), 0)
        
    except Exception as e:
        print(f"[MonitorUtils] Error enumerating monitors: {e}")
        # Fallback to primary
        monitors = [(0, 0, 1920, 1080)]
    
    return monitors if monitors else [(0, 0, 1920, 1080)]


def is_position_visible(x: int, y: int, width: int, height: int, min_visible: int = 50) -> bool:
    """
    Check if a window at (x, y) with given dimensions is at least partially 
    visible on any connected monitor.
    
    Args:
        x, y: Window top-left position
        width, height: Window dimensions
        min_visible: Minimum pixels that must be visible (default 50)
    
    Returns:
        True if at least min_visible pixels of the window are on a monitor
    """
    monitors = get_all_monitors()
    
    for mon_x, mon_y, mon_w, mon_h in monitors:
        # Calculate overlap between window and monitor
        overlap_left = max(x, mon_x)
        overlap_top = max(y, mon_y)
        overlap_right = min(x + width, mon_x + mon_w)
        overlap_bottom = min(y + height, mon_y + mon_h)
        
        overlap_width = overlap_right - overlap_left
        overlap_height = overlap_bottom - overlap_top
        
        # Check if there's meaningful overlap
        if overlap_width >= min_visible and overlap_height >= min_visible:
            return True
    
    return False


def center_window_on_monitor_at(window_handle, x: int, y: int) -> None:
    """
    Center a window on the monitor containing (x, y).
    """
    try:
        mon_x, mon_y, mon_w, mon_h = get_monitor_at_point(x, y)
        
        user32 = ctypes.windll.user32
        rect = RECT()
        user32.GetWindowRect(window_handle, ctypes.byref(rect))
        
        win_w = rect.right - rect.left
        win_h = rect.bottom - rect.top
        
        center_x = mon_x + (mon_w - win_w) // 2
        center_y = mon_y + (mon_h - win_h) // 2
        
        # SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOSIZE
        user32.SetWindowPos(window_handle, 0, center_x, center_y, 0, 0, 0x0004 | 0x0010 | 0x0001)
        
    except Exception as e:
        print(f"[MonitorUtils] Error centering window: {e}")
