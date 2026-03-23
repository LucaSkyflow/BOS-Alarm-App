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
    section(pdf, "Schritt 1: App herunterladen")
    pdf.multi_cell(0, 6,
        "1. Oeffne im Browser: github.com/LucaSkyflow/BOS-Alarm-App\n"
        "2. Klicke rechts auf 'Releases'\n"
        "3. Lade das ZIP-Archiv der neuesten Version herunter\n"
        "4. Entpacke das ZIP in einen beliebigen Ordner"
    )
    pdf.ln(3)

    # --- Step 2 ---
    section(pdf, "Schritt 2: Setup ausfuehren")
    pdf.multi_cell(0, 6,
        "1. Oeffne den entpackten Ordner\n"
        "2. Starte 'Setup.exe'\n"
        "3. Der Assistent fuehrt dich durch die Einrichtung:\n"
        "   - Installationsordner waehlen\n"
        "   - MQTT-Zugangsdaten eingeben (erhaeltst du vom Administrator)\n"
        "   - Optional: Philips Hue Bridge konfigurieren\n"
        "   - Desktop-Verknuepfung erstellen\n"
        "4. Die App startet automatisch nach der Einrichtung"
    )
    pdf.ln(3)

    # --- Step 3 ---
    section(pdf, "Schritt 3: Fertig!")
    pdf.multi_cell(0, 6,
        "Die App ist jetzt einsatzbereit. Du kannst sie ueber die\n"
        "Desktop-Verknuepfung oder direkt ueber 'BOS Alarm.exe'\n"
        "im Installationsordner starten."
    )
    pdf.ln(6)

    # --- Auto-Update info ---
    section(pdf, "Automatische Updates")
    pdf.multi_cell(0, 6,
        "Die App prueft bei jedem Start automatisch, ob ein Update verfuegbar ist. "
        "Wenn ja, wird es heruntergeladen und installiert. Die App startet danach automatisch neu.\n\n"
        "Es ist keine weitere Einrichtung noetig — Updates funktionieren automatisch."
    )
    pdf.ln(3)

    # --- Troubleshooting ---
    section(pdf, "Probleme?")
    pdf.multi_cell(0, 6,
        "Update-Status in der App pruefen:\n"
        "  - 'App ist aktuell' (gruen): Alles OK\n"
        "  - 'Update-Check fehlgeschlagen': Internetverbindung pruefen\n\n"
        "MQTT-Verbindung pruefen:\n"
        "  Einstellungen-Tab -> MQTT Einstellungen\n"
        "  Stelle sicher, dass Broker, Username und Passwort korrekt sind.\n\n"
        "Einrichtung wiederholen:\n"
        "  Starte 'Setup.exe' erneut, um die Zugangsdaten zu aendern."
    )

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
