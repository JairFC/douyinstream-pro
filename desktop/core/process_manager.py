"""
DouyinStream Pro - Process Manager
Centralized process tracking and cleanup to prevent orphan processes.
"""

import sys
import subprocess
import threading
import atexit
import time
import os
import weakref
from typing import Set, Optional

# Global registry of all spawned processes
_process_registry: Set[subprocess.Popen] = set()
_registry_lock = threading.Lock()
_active_processes: weakref.WeakSet = weakref.WeakSet()


def register_process(proc: subprocess.Popen) -> subprocess.Popen:
    """
    Register a process for cleanup.
    Returns the process object for chaining.
    """
    if proc is None:
        return None
        
    with _registry_lock:
        _process_registry.add(proc)
        _active_processes.add(proc)
    return proc


def unregister_process(proc: subprocess.Popen) -> None:
    """Unregister a process (e.g. when it finishes normally)."""
    if proc is None:
        return
        
    with _registry_lock:
        _process_registry.discard(proc)


def kill_process_tree(process: Optional[subprocess.Popen]) -> None:
    """
    Aggressively kill a process and all its children.
    Platform independent (Windows/Unix).
    """
    if not process:
        return
    
    # Remove from registry first to avoid double kill attempt in atexit
    unregister_process(process)
    
    try:
        pid = process.pid
        
        # On Windows, use taskkill to kill the entire process tree
        if sys.platform == "win32":
            # First try graceful termination
            try:
                process.terminate()
                # Give it a tiny bit of time to cleanup but don't block long
                try:
                    process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    pass
            except Exception:
                pass
            
            # Now force kill the entire tree if still running
            if process.poll() is None:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
        else:
            # On Unix, kill process group
            import signal
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                time.sleep(0.1)
                if process.poll() is None:
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
            except Exception:
                pass
        
        # Final safety net
        try:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=0.1)
        except Exception:
            pass
            
    except Exception as e:
        # Just swallow errors during kill, we did our best
        pass


def _cleanup_all_processes() -> None:
    """Cleanup handler for atexit."""
    with _registry_lock:
        processes = list(_process_registry)
        _process_registry.clear()
        
    if not processes:
        return
        
    # print(f"Limpiando {len(processes)} procesos huérfanos...")
    
    for proc in processes:
        try:
            if proc.poll() is None:
                kill_process_tree(proc)
        except Exception:
            pass

# Register cleanup handler
atexit.register(_cleanup_all_processes)
