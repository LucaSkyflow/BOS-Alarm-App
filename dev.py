"""BOS Alarm — Interactive Dev Tool.

Usage: python dev.py  (or just run dev.bat)

Detects changes, creates branches, commits, PRs and version bumps interactively.
"""

import os
import re
import subprocess
import sys

# ── Helpers ──────────────────────────────────────────────────────────────────

def run(cmd, capture=True, check=False, input_text=None):
    """Run a command. cmd can be a string (shell=True) or list (shell=False)."""
    is_list = isinstance(cmd, list)
    result = subprocess.run(
        cmd, capture_output=capture, text=True,
        shell=not is_list, input=input_text,
    )
    if check and result.returncode != 0:
        display = " ".join(cmd) if is_list else cmd
        print(f"  FEHLER: {display}")
        if result.stderr:
            print(f"  {result.stderr.strip()}")
        sys.exit(1)
    return result

def ask(prompt, options=None, default=None):
    if options:
        while True:
            answer = input(prompt).strip()
            if not answer and default is not None:
                return default
            if answer in options:
                return answer
            print(f"  Bitte eine der Optionen waehlen: {', '.join(options)}")
    else:
        answer = input(prompt).strip()
        return answer if answer else default

def header(text):
    print()
    print(f"  {'─' * 50}")
    print(f"  {text}")
    print(f"  {'─' * 50}")

def current_branch():
    return run("git branch --show-current").stdout.strip()

def has_changes():
    status = run("git status --porcelain").stdout.strip()
    return len(status) > 0

def get_changed_files():
    """Returns (staged, unstaged, untracked) file lists."""
    lines = run("git status --porcelain").stdout.strip().splitlines()
    staged, modified, untracked = [], [], []
    for line in lines:
        if not line.strip():
            continue
        index_status = line[0]
        work_status = line[1]
        filename = line[3:]
        if index_status == '?':
            untracked.append(filename)
        elif index_status != ' ':
            staged.append(filename)
        if work_status != ' ' and index_status != '?':
            modified.append(filename)
    return staged, modified, untracked

def read_version():
    version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version.py")
    with open(version_file, "r") as f:
        content = f.read()
    match = re.search(r'VERSION\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content)
    if not match:
        return 0, 0, 0
    return int(match.group(1)), int(match.group(2)), int(match.group(3))

def write_version(major, minor, patch):
    version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version.py")
    with open(version_file, "w") as f:
        f.write(f'VERSION = "{major}.{minor}.{patch}"\n')

def suggest_bump_type(files):
    """Suggest version bump based on changed files."""
    all_files = " ".join(files).lower()
    # New Python files or new GUI components → minor
    if any(f.endswith(".py") and f.startswith("gui/") for f in files):
        for f in files:
            if f.startswith("gui/") and f.endswith(".py"):
                status = run(f'git status --porcelain -- "{f}"').stdout.strip()
                if status.startswith("??") or status.startswith("A"):
                    return "minor", "Neue GUI-Komponente erkannt"
    if any(f.startswith("??") or f.endswith(".py") for f in files):
        new_py = [f for f in files if run(f'git status --porcelain -- "{f}"').stdout.strip().startswith("??") and f.endswith(".py")]
        if new_py:
            return "minor", "Neue Python-Dateien erkannt"
    # Config, docs, small fixes → patch
    return "patch", "Standard fuer Bugfixes und kleine Aenderungen"

def generate_branch_name(message):
    """Generate a clean branch name from a commit message."""
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', message.lower()).strip()
    words = clean.split()[:4]
    name = "-".join(words) if words else "update"
    # Avoid double dashes and trim
    name = re.sub(r'-+', '-', name).strip('-')[:40]
    return f"dev/{name}"

def generate_commit_message(staged, modified, untracked):
    """Auto-generate a commit message suggestion based on changed files."""
    all_files = staged + modified + untracked
    py_files = [f for f in all_files if f.endswith(".py")]
    gui_files = [f for f in py_files if f.startswith("gui/")]
    other_files = [f for f in all_files if not f.endswith(".py")]

    parts = []
    if gui_files:
        names = [os.path.splitext(os.path.basename(f))[0] for f in gui_files]
        parts.append(f"GUI: {', '.join(names)}")
    non_gui_py = [f for f in py_files if not f.startswith("gui/")]
    if non_gui_py:
        names = [os.path.splitext(os.path.basename(f))[0] for f in non_gui_py]
        parts.append(f"{', '.join(names)}")
    if other_files and not parts:
        parts.append(f"{', '.join(other_files[:3])}")

    if parts:
        return f"Update {'; '.join(parts)}"
    return "Update"


# ── Main Flow ────────────────────────────────────────────────────────────────

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║         BOS Alarm — Dev Tool                 ║")
    print("  ╚══════════════════════════════════════════════╝")

    # ── Check for changes ────────────────────────────────────────────────
    staged, modified, untracked = get_changed_files()
    branch = current_branch()
    major, minor, patch = read_version()

    header(f"Status  (Branch: {branch}  |  Version: v{major}.{minor}.{patch})")

    if not staged and not modified and not untracked:
        print()
        print("  Keine Aenderungen gefunden. Nichts zu tun.")
        print()
        return

    if staged:
        print(f"\n  Staged ({len(staged)}):")
        for f in staged:
            print(f"    + {f}")
    if modified:
        print(f"\n  Geaendert ({len(modified)}):")
        for f in modified:
            print(f"    ~ {f}")
    if untracked:
        print(f"\n  Neu ({len(untracked)}):")
        for f in untracked:
            print(f"    ? {f}")

    # ── Ask what to do ───────────────────────────────────────────────────
    header("Was moechtest du tun?")
    print()
    print("    [1] Commit + PR erstellen        (aendern & veroeffentlichen)")
    print("    [2] Nur committen                (lokal speichern, kein PR)")
    print("    [3] Abbrechen")
    print()
    action = ask("  Auswahl [1]: ", options=["1", "2", "3"], default="1")

    if action == "3":
        print("\n  Abgebrochen.\n")
        return

    # ── Commit message ───────────────────────────────────────────────────
    all_changed = staged + modified + untracked
    suggestion = generate_commit_message(staged, modified, untracked)

    header("Commit")
    print(f"\n  Vorschlag: {suggestion}")
    message = input(f"\n  Commit-Nachricht [{suggestion}]: ").strip()
    if not message:
        message = suggestion

    # ── Version bump (only for PR) ───────────────────────────────────────
    do_bump = False
    new_version = f"{major}.{minor}.{patch}"

    if action == "1":
        header("Release / Versionierung")
        print()
        print("  Soll ein neues Release erstellt werden?")
        print("  (Nach dem Merge wird die App automatisch gebaut und veroeffentlicht)")
        print()

        bump_suggestion, bump_reason = suggest_bump_type(all_changed)
        bump_labels = {"patch": "Bugfix", "minor": "Feature", "major": "Breaking"}

        v_patch = f"v{major}.{minor}.{patch + 1}"
        v_minor = f"v{major}.{minor + 1}.0"
        v_major = f"v{major + 1}.0.0"

        rec = {"patch": "1", "minor": "2", "major": "3"}[bump_suggestion]

        print(f"    [0] Kein Release         (nur Code-Aenderung)")
        print(f"    [1] Patch  → {v_patch}   (Bugfix)")
        print(f"    [2] Minor  → {v_minor}   (Neues Feature)")
        print(f"    [3] Major  → {v_major}   (Breaking Change)")
        print()
        print(f"  Empfehlung: [{rec}] {bump_labels[bump_suggestion]} — {bump_reason}")
        print()

        bump_choice = ask(f"  Auswahl [{rec}]: ", options=["0", "1", "2", "3"], default=rec)

        if bump_choice != "0":
            do_bump = True
            if bump_choice == "1":
                new_version = f"{major}.{minor}.{patch + 1}"
            elif bump_choice == "2":
                new_version = f"{major}.{minor + 1}.0"
            elif bump_choice == "3":
                new_version = f"{major + 1}.0.0"

    # ── Confirmation ─────────────────────────────────────────────────────
    header("Zusammenfassung")
    print()
    print(f"  Nachricht:  {message}")
    print(f"  Dateien:    {len(all_changed)} geaendert")
    if action == "1":
        print(f"  PR:         Ja")
    if do_bump:
        print(f"  Release:    v{major}.{minor}.{patch} → v{new_version}")
    else:
        print(f"  Release:    Nein")
    print()

    confirm = ask("  Ausfuehren? (j/n) [j]: ", options=["j", "n"], default="j")
    if confirm != "j":
        print("\n  Abgebrochen.\n")
        return

    # ── Execute ──────────────────────────────────────────────────────────
    header("Ausfuehrung")

    # 1. Ensure we're on a feature branch (for PRs)
    if action == "1" and branch == "main":
        branch_name = generate_branch_name(message)
        print(f"\n  Branch erstellen: {branch_name}")
        run(["git", "checkout", "-b", branch_name], check=True)
        branch = branch_name

    # 2. Version bump
    if do_bump:
        parts = new_version.split(".")
        write_version(int(parts[0]), int(parts[1]), int(parts[2]))
        print(f"  Version aktualisiert: v{new_version}")

    # 3. Stage all changes
    print("  Dateien stagen...")
    run(["git", "add", "-A"], check=True)

    # 4. Commit
    print(f"  Commit: {message}")
    run(["git", "commit", "-m", message], check=True)

    # 5. Push + PR
    if action == "1":
        print(f"  Push: {branch} -> origin")
        run(["git", "push", "-u", "origin", branch], check=True)

        print("  PR erstellen...")
        pr_title = message
        if do_bump:
            pr_title = f"v{new_version}: {message}"

        pr_result = run([
            "gh", "pr", "create",
            "--title", pr_title,
            "--body", "Automatisch erstellt mit dev.py",
        ])
        if pr_result.returncode == 0:
            pr_url = pr_result.stdout.strip()
            print(f"\n  PR erstellt: {pr_url}")

            print("  Browser oeffnen...")
            os.startfile(pr_url)
        else:
            print(f"  WARNUNG: PR konnte nicht erstellt werden.")
            print(f"  {pr_result.stderr.strip()}")

    # ── Done ─────────────────────────────────────────────────────────────
    print()
    print("  ╔══════════════════════════════════════════════╗")
    if action == "1":
        print("  ║  Fertig! PR im Browser mergen.               ║")
        if do_bump:
            print("  ║  Nach Merge: Build + Release automatisch.    ║")
    else:
        print("  ║  Fertig! Aenderungen lokal gespeichert.       ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()

    # Return to main after PR creation
    if action == "1":
        switch_back = ask("  Zurueck auf main wechseln? (j/n) [j]: ", options=["j", "n"], default="j")
        if switch_back == "j":
            run(["git", "checkout", "main"], check=True)
            print("  Auf main gewechselt.\n")


if __name__ == "__main__":
    main()
