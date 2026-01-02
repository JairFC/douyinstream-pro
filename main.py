"""
DouyinStream Pro - Entry Point
Main launcher for the application.
"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


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
