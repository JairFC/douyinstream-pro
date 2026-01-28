"""
DouyinStream Pro - Entry Point
Main launcher for the application.
"""

import sys
import os
import ctypes

# CRITICAL: Enable DPI awareness BEFORE any window is created
# This ensures Tkinter and Windows API use the same coordinate system
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try to center console on the active monitor (where mouse is)
try:
    import console_helper
    console_helper.center_console_on_mouse_monitor()
except ImportError:
    pass

def main() -> None:
    """Main entry point for DouyinStream Pro."""
    try:
        # Import and run application
        from ui.app import DouyinStreamApp
        
        app = DouyinStreamApp()
        app.run()
        
    except ImportError as e:
        print(f"Error de importación: {e}")
        print("\nAsegúrate de instalar las dependencias:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
        
    except Exception as e:
        print(f"Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
