"""BOS Alarm — Interactive Release Script.

Usage: python release.py  (or just run release.bat)

Steps:
  1. Shows current version
  2. Asks for bump type (major / minor / patch)
  3. Asks for changelog text
  4. Updates version.py
  5. Builds EXE via PyInstaller
  6. Creates ZIP from dist folder
  7. Creates GitHub Release with changelog
"""

import os
import re
import sys
import shutil
import subprocess

REPO = "Skyflow-Network/bos-alarm-app"
VERSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version.py")
SPEC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bos_alarm_v2.spec")
DIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "BOS Alarm")


def read_version() -> tuple[int, int, int]:
    with open(VERSION_FILE, "r") as f:
        content = f.read()
    match = re.search(r'VERSION\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content)
    if not match:
        print("ERROR: Could not parse version from version.py")
        sys.exit(1)
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def write_version(major: int, minor: int, patch: int):
    with open(VERSION_FILE, "w") as f:
        f.write(f'VERSION = "{major}.{minor}.{patch}"\n')


def bump_version(major: int, minor: int, patch: int, bump_type: str) -> tuple[int, int, int]:
    if bump_type == "major":
        return major + 1, 0, 0
    elif bump_type == "minor":
        return major, minor + 1, 0
    elif bump_type == "patch":
        return major, minor, patch + 1
    return major, minor, patch


def run_command(cmd: list[str], description: str, silent: bool = False) -> bool:
    try:
        kwargs = {"capture_output": True, "text": True} if silent else {}
        result = subprocess.run(cmd, **kwargs)
        return result.returncode == 0
    except FileNotFoundError:
        print(f"  ERROR: Command not found: {cmd[0]}")
        return False


def main():
    print("=" * 45)
    print("         BOS Alarm — Release Tool")
    print("=" * 45)
    print()

    # Step 1: Show current version
    major, minor, patch = read_version()
    current = f"{major}.{minor}.{patch}"
    print(f"  Aktuelle Version:  v{current}")
    print()

    # Step 2: Ask for bump type
    print("  Welcher Release-Typ?")
    print()
    print(f"    [0] keine    →  v{current}              (Re-Release)")
    print(f"    [1] patch    →  v{major}.{minor}.{patch + 1}    (Bugfixes)")
    print(f"    [2] minor    →  v{major}.{minor + 1}.0    (Neue Features)")
    print(f"    [3] major    →  v{major + 1}.0.0    (Breaking Changes)")
    print()

    while True:
        choice = input("  Auswahl (0/1/2/3): ").strip()
        if choice in ("0", "1", "2", "3"):
            break
        print("  Bitte 0, 1, 2 oder 3 eingeben.")

    bump_map = {"0": "none", "1": "patch", "2": "minor", "3": "major"}
    new_major, new_minor, new_patch = bump_version(major, minor, patch, bump_map[choice])
    new_version = f"{new_major}.{new_minor}.{new_patch}"

    print()
    if choice == "0":
        print(f"  Version bleibt:  v{current}")
    else:
        print(f"  Neue Version:  v{current}  →  v{new_version}")
    print()

    # Step 3: Ask for changelog
    print("  Changelog (mehrzeilig, leere Zeile zum Beenden):")
    print()
    lines = []
    while True:
        line = input("    > ")
        if line == "":
            break
        lines.append(line)

    if not lines:
        changelog = f"BOS Alarm v{new_version}"
    else:
        changelog = "\n".join(f"- {line}" for line in lines)

    print()
    print("-" * 45)
    print(f"  Version:    v{new_version}")
    print(f"  Changelog:")
    for line in changelog.splitlines():
        print(f"    {line}")
    print("-" * 45)
    print()

    confirm = input("  Release starten? (j/n): ").strip().lower()
    if confirm != "j":
        print("  Abgebrochen.")
        return

    print()

    # Step 4: Update version.py
    print(f"  [1/4] Version aktualisieren → v{new_version}")
    write_version(new_major, new_minor, new_patch)

    # Step 5: Build
    print("  [2/4] EXE bauen...")
    run_command(["pip", "install", "-r", "requirements.txt", "pyinstaller"], "pip install", silent=True)
    if not run_command(["pyinstaller", SPEC_FILE, "--noconfirm"], "pyinstaller", silent=True):
        print("  ERROR: Build fehlgeschlagen!")
        write_version(major, minor, patch)  # rollback
        print("  Version zurückgesetzt.")
        sys.exit(1)
    print("         Build OK.")

    # Step 6: Create ZIP
    print("  [3/4] ZIP erstellen...")
    zip_name = f"BOS-Alarm-v{new_version}"
    zip_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), zip_name)
    if os.path.exists(zip_path + ".zip"):
        os.remove(zip_path + ".zip")
    shutil.make_archive(zip_name, "zip", DIST_DIR)
    zip_file = zip_name + ".zip"
    print(f"         {zip_file}")

    # Step 7: GitHub Release
    print(f"  [4/4] GitHub Release v{new_version}...")
    success = run_command(
        [
            "gh", "release", "create", f"v{new_version}",
            zip_file,
            "--title", f"v{new_version}",
            "--notes", changelog,
            "--repo", REPO,
        ],
        "gh release",
        silent=False,
    )

    # Cleanup ZIP
    if os.path.exists(zip_file):
        os.remove(zip_file)

    if not success:
        print("  ERROR: GitHub Release fehlgeschlagen!")
        print("  Prüfe ob gh authentifiziert ist: gh auth login")
        sys.exit(1)

    print()
    print("=" * 45)
    print(f"  Release v{new_version} veröffentlicht!")
    print("=" * 45)


if __name__ == "__main__":
    main()
