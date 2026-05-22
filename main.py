import os
import sys
import logging
import msvcrt

# Must run before any customtkinter/tkinter import: force System-DPI-Aware (Mode 1).
# CustomTkinter otherwise sets Per-Monitor-Aware (Mode 2), which triggers a
# synchronous widget rescale whenever the window moves between monitors with
# different DPI. In combination with the alarm/helicopter blink timers and the
# background threads that post via .after(), that rescale caused the freezes
# and crashes reported when the window was dragged across monitors.
if sys.platform.startswith("win"):
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

# In a PyInstaller-frozen build, __file__ resolves into _internal/ (the
# bundled library dir, which gets overwritten on every update). Writing
# log/lock/db there causes PermissionError after updates when the file
# is still locked by AV scanning or a lingering old process. Anchor on
# the EXE directory instead — same approach used by updater.py,
# settings_manager.py and setup_wizard.py.
if getattr(sys, "frozen", False):
    _DIR = os.path.dirname(sys.executable)
else:
    _DIR = os.path.dirname(os.path.abspath(__file__))
LOCK_PATH = os.path.join(_DIR, "bos_alarm_v2.lock")
LOG_PATH = os.path.join(_DIR, "bos_alarm_v2.log")

_lock_file_handle = None


def setup_logging():
    """Configure logging. Resilient against a locked log file — never
    let an I/O issue here kill the app before it even starts."""
    fmt = "%(asctime)s  %(levelname)-7s  %(name)s  %(message)s"
    handlers = [logging.StreamHandler(sys.stdout)]

    file_handler = None
    try:
        file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    except (PermissionError, OSError):
        # Primary log file is locked (AV scan, lingering old process
        # after update, etc.). Fall back to a PID-suffixed file so we
        # can still capture diagnostics.
        try:
            fallback = LOG_PATH.replace(".log", f"_{os.getpid()}.log")
            file_handler = logging.FileHandler(fallback, encoding="utf-8")
        except (PermissionError, OSError):
            # Last resort: stderr-only. App must still boot.
            file_handler = None

    if file_handler is not None:
        handlers.insert(0, file_handler)

    logging.basicConfig(level=logging.DEBUG, format=fmt, handlers=handlers)


def acquire_single_instance_lock() -> bool:
    global _lock_file_handle
    try:
        _lock_file_handle = open(LOCK_PATH, "a+")
        msvcrt.locking(_lock_file_handle.fileno(), msvcrt.LK_NBLCK, 1)
        _lock_file_handle.seek(0)
        _lock_file_handle.truncate()
        _lock_file_handle.write(f"pid={os.getpid()}\n")
        _lock_file_handle.flush()
        return True
    except OSError:
        return False
    except Exception as e:
        logging.error(f"Lock error: {e}")
        return False


def main():
    setup_logging()
    log = logging.getLogger("main")

    if not acquire_single_instance_lock():
        log.warning("Another instance is already running. Exiting.")
        sys.exit(1)

    log.info("BOS Alarm starting...")

    from app import App
    app = App()
    app.run()


if __name__ == "__main__":
    main()
