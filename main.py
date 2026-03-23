import os
import sys
import logging
import msvcrt

_DIR = os.path.dirname(os.path.abspath(__file__))
LOCK_PATH = os.path.join(_DIR, "bos_alarm_v2.lock")
LOG_PATH = os.path.join(_DIR, "bos_alarm_v2.log")

_lock_file_handle = None


def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


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
