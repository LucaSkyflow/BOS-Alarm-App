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

        # Use PowerShell for the update — more reliable than batch scripts.
        # Waits for this process (by PID) to exit, copies files, restarts app.
        pid = os.getpid()
        exe_path = os.path.join(_APP_DIR, "BOS Alarm.exe")
        log_path = os.path.join(_APP_DIR, "update.log")

        ps_script = os.path.join(tempfile.gettempdir(), "bos_alarm_update.ps1")
        with open(ps_script, "w", encoding="utf-8") as f:
            f.write(f'''
$appPid = {pid}
$source = "{source_dir}"
$target = "{_APP_DIR}"
$logFile = "{log_path}"
$exe = "{exe_path}"

function Log($msg) {{
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}}

Log "Update gestartet (warte auf PID $appPid)"
Log "Quelle: $source"
Log "Ziel: $target"

try {{
    $proc = Get-Process -Id $appPid -ErrorAction Stop
    Log "Prozess gefunden, warte auf Beendigung..."
    $proc.WaitForExit(30000) | Out-Null
    Log "Prozess beendet"
}} catch {{
    Log "Prozess bereits beendet"
}}

Start-Sleep -Seconds 2

Log "Kopiere Update..."
try {{
    Copy-Item -Path "$source\*" -Destination $target -Recurse -Force
    Log "Kopieren erfolgreich"
}} catch {{
    Log "FEHLER beim Kopieren: $_"
    exit 1
}}

if (Test-Path $exe) {{
    Log "Starte App: $exe"
    Start-Process -FilePath $exe -WorkingDirectory $target
    Log "App gestartet"
}} else {{
    Log "FEHLER: $exe nicht gefunden"
}}

Start-Sleep -Seconds 2
Remove-Item -Path $source -Recurse -Force -ErrorAction SilentlyContinue
Log "Update abgeschlossen"
''')

        log.info(f"Launching PowerShell updater (PID={pid})")
        subprocess.Popen(
            f'start /B powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{ps_script}"',
            shell=True,
        )

        return True

    except Exception as e:
        log.error(f"Update download/apply failed: {e}")
        status("Update fehlgeschlagen")
        return False
