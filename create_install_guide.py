"""Generates the BOS Alarm installation guide as PDF."""

from fpdf import FPDF


def create_guide():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 14, "BOS Alarm", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, "Installationsanleitung", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    # Intro
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6,
        "Diese Anleitung beschreibt die einmalige Einrichtung der BOS Alarm App. "
        "Nach der Installation aktualisiert sich die App automatisch, sobald ein neues Update verfuegbar ist."
    )
    pdf.ln(4)

    # --- Step 1 ---
    section(pdf, "Schritt 1: GitHub-Account erstellen")
    pdf.multi_cell(0, 6,
        "Falls du noch keinen GitHub-Account hast:\n"
        "1. Oeffne github.com\n"
        "2. Klicke auf 'Sign up' und erstelle einen Account\n"
        "3. Teile deinen Benutzernamen dem Admin mit, damit er dich zum Repository einladen kann"
    )
    pdf.ln(3)

    # --- Step 2 ---
    section(pdf, "Schritt 2: Einladung annehmen")
    pdf.multi_cell(0, 6,
        "Du erhaeltst eine E-Mail von GitHub mit einer Einladung zum Repository "
        "'LucaSkyflow/BOS-Alarm-App'. Klicke auf 'Accept invitation'."
    )
    pdf.ln(3)

    # --- Step 3 ---
    section(pdf, "Schritt 3: GitHub CLI installieren")
    pdf.multi_cell(0, 6,
        "Die GitHub CLI wird benoetigt, damit die App Updates vom privaten Repository laden kann.\n\n"
        "1. Oeffne cli.github.com\n"
        "2. Lade den Windows-Installer herunter und fuehre ihn aus\n"
        "3. Folge dem Installations-Assistenten (Standard-Einstellungen sind OK)"
    )
    pdf.ln(3)

    # --- Step 4 ---
    section(pdf, "Schritt 4: GitHub CLI anmelden")
    pdf.multi_cell(0, 6, "1. Oeffne ein Terminal (Windows-Taste, dann 'cmd' eingeben, Enter)")
    pdf.ln(1)
    pdf.set_font("Courier", "", 11)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, "   gh auth login", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6,
        "2. Waehle folgende Optionen:\n"
        "   - GitHub.com\n"
        "   - HTTPS\n"
        "   - Login with a web browser\n"
        "3. Es wird ein Code angezeigt. Druecke Enter, der Browser oeffnet sich.\n"
        "4. Gib den Code im Browser ein und melde dich mit deinem GitHub-Account an.\n"
        "5. Im Terminal erscheint: 'Logged in as DeinName' - fertig!"
    )
    pdf.ln(3)

    # --- Step 5 ---
    section(pdf, "Schritt 5: App herunterladen")
    pdf.multi_cell(0, 6,
        "1. Oeffne im Browser: github.com/LucaSkyflow/BOS-Alarm-App\n"
        "2. Klicke rechts auf 'Releases'\n"
        "3. Lade das ZIP-Archiv der neuesten Version herunter\n"
        "4. Entpacke das ZIP in einen Ordner deiner Wahl, z.B. C:\\BOS Alarm\\"
    )
    pdf.ln(3)

    # --- Step 6 ---
    section(pdf, "Schritt 6: App starten")
    pdf.multi_cell(0, 6,
        "1. Oeffne den entpackten Ordner\n"
        "2. Starte 'BOS Alarm.exe'\n"
        "3. Die App verbindet sich automatisch und ist einsatzbereit\n\n"
        "Tipp: Erstelle eine Verknuepfung auf dem Desktop fuer schnellen Zugriff."
    )
    pdf.ln(6)

    # --- Auto-Update info ---
    section(pdf, "Automatische Updates")
    pdf.multi_cell(0, 6,
        "Die App prueft bei jedem Start automatisch, ob ein Update verfuegbar ist. "
        "Wenn ja, wird es heruntergeladen und installiert. Die App startet danach automatisch neu.\n\n"
        "Du musst nichts weiter tun. Solange die GitHub CLI eingerichtet ist, "
        "funktionieren Updates automatisch."
    )
    pdf.ln(3)

    # --- Troubleshooting ---
    section(pdf, "Probleme?")
    pdf.multi_cell(0, 6,
        "Update-Status in der App pruefen:\n"
        "  - 'App ist aktuell' (gruen): Alles OK\n"
        "  - 'Update-Check fehlgeschlagen': GitHub CLI pruefen\n\n"
        "GitHub CLI Status pruefen:\n"
        "  Einstellungen-Tab -> Auto-Update -> 'Verbindung pruefen'\n\n"
        "Neu anmelden falls noetig:"
    )
    pdf.ln(1)
    pdf.set_font("Courier", "", 11)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, "   gh auth login", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_font("Helvetica", "", 11)

    # Save
    output_path = "BOS Alarm - Installationsanleitung.pdf"
    pdf.output(output_path)
    print(f"PDF erstellt: {output_path}")


def section(pdf, title):
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)


if __name__ == "__main__":
    create_guide()
