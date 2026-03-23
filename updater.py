import os
import sys
import logging
import zipfile
import shutil
import subprocess
import tempfile
import requests

# For PyInstaller frozen apps, use the exe directory as app root
if getattr(sys, "frozen", False):
    _APP_DIR = os.path.dirname(sys.executable)
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))

from version import VERSION

log = logging.getLogger(__name__)

# ---- Configuration ----
GITHUB_API_URL = "https://api.github.com"
REPO = "LucaSkyflow/BOS-Alarm-App"
RELEASE_URL = f"{GITHUB_API_URL}/repos/{REPO}/releases/latest"


def _parse_version(tag: str) -> tuple[int, ...]:
    """Parse a version tag like 'v1.2.3' or '1.2.3' into a comparable tuple."""
    tag = tag.lstrip("v")
    parts = []
    for p in tag.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def check_for_update(on_status=None):
    """Check GitHub for a newer release. Returns (new_version, asset_url) or None.

    on_status: optional callback(str) to report progress messages.
    """
    def status(msg, color="#aaaaaa"):
        log.info(msg)
        if on_status:
            on_status(msg, color)

    try:
        status("Suche nach Updates...")

        headers = {"Accept": "application/vnd.github+json"}
        resp = requests.get(RELEASE_URL, headers=headers, timeout=10)
        if resp.status_code == 404:
            status(f"App ist aktuell (v{VERSION})", "#4caf50")
            log.info("No releases found (404) — likely first run or no releases yet")
            return None
        if resp.status_code != 200:
            status("Update-Check fehlgeschlagen", "#cc4444")
            log.warning(f"GitHub API returned {resp.status_code}")
            return None

        data = resp.json()
        remote_tag = data.get("tag_name", "")
        if not remote_tag:
            return None

        local_ver = _parse_version(VERSION)
        remote_ver = _parse_version(remote_tag)

        if remote_ver <= local_ver:
            status(f"App ist aktuell (v{VERSION})", "#4caf50")
            return None

        # Find the ZIP asset
        asset_url = None
        for asset in data.get("assets", []):
            if asset["name"].endswith(".zip"):
                asset_url = asset["browser_download_url"]
                break

        if not asset_url:
            status("Update gefunden, aber kein ZIP-Asset im Release")
            log.warning("No .zip asset in latest release")
            return None

        display_ver = remote_tag.lstrip("v")
        status(f"Update gefunden: v{display_ver}")
        return display_ver, asset_url

    except requests.RequestException as e:
        log.warning(f"Update check failed: {e}")
        status("Update-Check fehlgeschlagen (Netzwerk)", "#cc4444")
        return None
    except Exception as e:
        log.error(f"Update check error: {e}")
        status("Update-Check fehlgeschlagen", "#cc4444")
        return None


def download_and_apply(asset_url: str, new_version: str, on_status=None):
    """Download the update ZIP, extract it, and launch the update batch script."""
    def status(msg):
        log.info(msg)
        if on_status:
            on_status(msg)

    try:
        status(f"Lade Update v{new_version} herunter...")
        resp = requests.get(asset_url, timeout=120, stream=True)
        resp.raise_for_status()

        # Save ZIP to temp file
        tmp_zip = os.path.join(tempfile.gettempdir(), "bos_alarm_update.zip")
        with open(tmp_zip, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        # Extract to temp folder
        tmp_extract = os.path.join(tempfile.gettempdir(), "bos_alarm_update")
        if os.path.exists(tmp_extract):
            shutil.rmtree(tmp_extract)
        with zipfile.ZipFile(tmp_zip, "r") as zf:
            zf.extractall(tmp_extract)

        # The ZIP might contain a single subfolder (e.g., bos_alarm_v2/)
        # Detect and use that as the source
        entries = os.listdir(tmp_extract)
        if len(entries) == 1 and os.path.isdir(os.path.join(tmp_extract, entries[0])):
            source_dir = os.path.join(tmp_extract, entries[0])
        else:
            source_dir = tmp_extract

        status("Starte Update-Prozess...")

        # Find the update batch script — in frozen builds it's inside _MEIPASS
        if getattr(sys, "frozen", False):
            bat_src = os.path.join(sys._MEIPASS, "_update.bat")
        else:
            bat_src = os.path.join(_APP_DIR, "_update.bat")

        if not os.path.exists(bat_src):
            log.error(f"_update.bat not found at {bat_src}")
            status("Update fehlgeschlagen (_update.bat nicht gefunden)")
            return False

        # Copy batch script to temp so it doesn't get overwritten during update
        bat_tmp = os.path.join(tempfile.gettempdir(), "bos_alarm_update.bat")
        shutil.copy2(bat_src, bat_tmp)

        log.info(f"Launching update: {bat_tmp} {source_dir} {_APP_DIR}")
        subprocess.Popen(
            [bat_tmp, source_dir, _APP_DIR],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        )

        return True

    except Exception as e:
        log.error(f"Update download/apply failed: {e}")
        status("Update fehlgeschlagen")
        return False
