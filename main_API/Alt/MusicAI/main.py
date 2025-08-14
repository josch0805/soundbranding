def create_request_form():
    """Display and handle the request creation form."""
    st.title("Anfrageformular")
    
    with st.form("request_form", clear_on_submit=True):
        # Basisdaten
        st.markdown("### Unternehmen")
        firma = st.text_input("Firma *", help="Pflichtfeld")
        website = st.text_input("Website URL *", help="Pflichtfeld - Bitte geben Sie die vollständige URL ein (z.B. https://www.example.com)")
        
        # Unternehmensprofil
        st.markdown("### Unternehmensprofil")
        werte = st.text_area("Was macht ihr Unternehmen aus?")
        konkurrenz = st.text_area("Womit grenzen Sie sich von Branchenkollegen ab?")
        philosophie = st.text_area("Worauf legen Sie innerhalb des Betriebes wert? Was ist Ihre Unternehmens-Philosophie?")
        
        # Musikpräferenzen
        st.markdown("### Musikpräferenzen")
        musik_praeferenz = st.text_area("Welche Art von Musik hören Sie gerne? (Mehrere Antworten möglich)")
        musik_firmensong = st.text_area("Welche Art von Musik könnten Sie sich gut für Ihren eigenen Firmensong vorstellen? (Mehrere Antworten möglich)")
        
        # Ausrichtung
        st.markdown("### Ausrichtung")
        ausrichtung = st.radio(
            "Soll der Song eher Produktorientiert oder eher Emotionsorientiert (Wir-Gefühl) ausgerichtet sein?",
            options=['Bitte wählen', 'Produktorientiert', 'Emotionsorientiert (Wir-Gefühl)'],
            index=0
        )
        
        # Songlänge
        st.markdown("### Songlänge")
        songlaenge = st.radio(
            "Wie lang soll der Song in etwa werden?",
            options=[
                'Bitte wählen',
                'Jingle 10 - 20 Sekunden',
                'Kompaktsong 90 - 120 Sekunden',
                'Markensong 120 - 180 Sekunden',
                'Unternehmenshymne 120 - 240 Sekunden',
                'Individueller Jubiläumssong (auf Anfrage)'
            ],
            index=0
        )
        
        # Sonstiges
        st.markdown("### Sonstiges")
        sonstiges = st.text_area("Wünsche, Ideen, Vorschläge")
        
        # Kontaktdaten
        st.markdown("### Kontaktdaten")
        name = st.text_input("Name *", help="Pflichtfeld")
        email = st.text_input("E-Mail Adresse *", help="Pflichtfeld")
        telefon = st.text_input("Telefonnummer *", help="Pflichtfeld")
        
        submitted = st.form_submit_button("Absenden")
        
        if submitted:
            # Validierung bleibt gleich, da "Firma" bereits in der Prüfung enthalten ist
            if not all([firma, name, website, email, telefon]):
                st.error("Bitte füllen Sie alle Pflichtfelder aus (Firma, Name, Website, E-Mail, Telefon).")
                return
            
            if ausrichtung == 'Bitte wählen' or songlaenge == 'Bitte wählen':
                st.error("Bitte treffen Sie eine Auswahl bei Ausrichtung und Songlänge.")
                return
            
            # Validiere und bereinige die URL
            clean_url = validate_url(website)
            if not clean_url:
                st.error("Bitte geben Sie eine gültige Website-URL ein.")
                return
                
            new_request = {
                "Firma": firma,
                "Name": name,
                "Website": clean_url,
                "Werte": werte,
                "Konkurrenz": konkurrenz,
                "Philosophie": philosophie,
                "Musik_Praeferenz": musik_praeferenz,
                "Musik_Firmensong": musik_firmensong,
                "Ausrichtung": ausrichtung,
                "Songlaenge": songlaenge,
                "Sonstiges": sonstiges,
                "Email": email,
                "Telefon": telefon,
                "status": "ausstehend",
                "erstellungsdatum": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            try:
                filename = save_request(new_request)
                if filename:
                    st.success("Ihre Anfrage wurde erfolgreich gespeichert!")
                    st.session_state.form_submitted = True
                else:
                    st.error("Fehler beim Speichern der Anfrage.")
            except Exception as e:
                st.error(f"Fehler beim Speichern der Anfrage: {str(e)}")