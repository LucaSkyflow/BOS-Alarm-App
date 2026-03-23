"""Creates a desktop shortcut for BOS Alarm."""

import subprocess
import sys
import os

DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
SHORTCUT_NAME = "BOS Alarm.lnk"
SHORTCUT_PATH = os.path.join(DESKTOP, SHORTCUT_NAME)
WORKING_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = sys.executable.replace("python.exe", "pythonw.exe")
TARGET_SCRIPT = os.path.join(WORKING_DIR, "main.py")
ICON_PATH = r"C:\Users\Luca\Pictures\Blinklicht.ico"


def create_shortcut():
    ps_command = f"""
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('{SHORTCUT_PATH}')
    $Shortcut.TargetPath = '{PYTHON_EXE}'
    $Shortcut.Arguments = '"{TARGET_SCRIPT}"'
    $Shortcut.WorkingDirectory = '{WORKING_DIR}'
    $Shortcut.IconLocation = '{ICON_PATH}'
    $Shortcut.Description = 'BOS Alarm'
    $Shortcut.Save()
    """

    try:
        subprocess.run(
            ["powershell", "-Command", ps_command],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"Shortcut created: {SHORTCUT_PATH}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to create shortcut: {e.stderr}")
        sys.exit(1)


if __name__ == "__main__":
    create_shortcut()
