import streamlit as st
import json
import os
from typing import List, Dict
from datetime import datetime
import re
from urllib.parse import urlparse
from API import process_job
import logging

# Configure logging
logging.basicConfig(
    filename='streamlit_log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ANFRAGEN_DIR = os.path.join(BASE_DIR, 'files')
STATUS_COLORS = {
    'ausstehend': 'orange',
    'freigegeben': 'green',
    'in Bearbeitung': 'blue',
    'abgelehnt': 'red'
}

# Im Constants-Bereich, die Tabs definieren
TABS = ["Anfrageformular", "Freigabe", "Songideen", "Songs", "David-Style", "Stems"]

# Initialisiere session state für Formulare
if 'form_submitted' not in st.session_state:
    st.session_state.form_submitted = False

def get_all_requests() -> List[Dict]:
    """Load all requests from JSON files."""
    requests = []
    try:
        if os.path.exists(ANFRAGEN_DIR):
            files = os.listdir(ANFRAGEN_DIR)
            
            for filename in files:
                if filename.endswith('.json') and filename.startswith('Anfr_'):
                    file_path = os.path.join(ANFRAGEN_DIR, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            request = json.load(file)
                            request['filename'] = filename
                            requests.append(request)
                    except Exception as e:
                        st.error(f"Fehler beim Laden der Datei {filename}: {str(e)}")
        else:
            st.warning(f"Verzeichnis {ANFRAGEN_DIR} existiert nicht!")
        
    except Exception as e:
        st.error(f"Fehler beim Laden der Anfragen: {str(e)}")
    return requests

def save_request(request: Dict) -> None:
    """Save single request to a JSON file."""
    try:
        if not os.path.exists(ANFRAGEN_DIR):
            os.makedirs(ANFRAGEN_DIR)
            logger.info(f"Created directory: {ANFRAGEN_DIR}")
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_firma = ''.join(c for c in request['Firma'] if c.isalnum() or c in [' ', '_', '-'])
        safe_firma = safe_firma.replace(' ', '_')
        filename = f"Anfr_{safe_firma}_{timestamp}.json"
        
        file_path = os.path.join(ANFRAGEN_DIR, filename)
        
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(request, file, indent=4, ensure_ascii=False)
            
        if os.path.exists(file_path):
            logger.info(f"Successfully saved request for company: {request['Firma']}")
            return filename
        logger.error(f"Failed to save request for company: {request['Firma']}")
        return None
    except Exception as e:
        logger.error(f"Error saving request: {str(e)}")
        st.error(f"Fehler beim Speichern: {str(e)}")
        return None

def update_request_status(filename: str, new_status: str) -> None:
    """Update status of a specific request."""
    try:
        file_path = os.path.join(ANFRAGEN_DIR, filename)
        with open(file_path, 'r', encoding='utf-8') as file:
            request = json.load(file)
        
        old_status = request.get('status', 'unknown')
        request['status'] = new_status
        
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(request, file, indent=4, ensure_ascii=False)
            
        logger.info(f"Updated request status from '{old_status}' to '{new_status}' for file: {filename}")
    except Exception as e:
        logger.error(f"Error updating request status: {str(e)}")
        st.error(f"Fehler beim Aktualisieren des Status: {str(e)}")

def get_requests_with_dates() -> List[tuple]:
    """Get requests with their creation dates, sorted by newest first."""
    try:
        if not os.path.exists(ANFRAGEN_DIR):
            return []
            
        files = os.listdir(ANFRAGEN_DIR)
        requests = [f for f in files if f.endswith('.json') and f.startswith('Anfr_')]
        
        # Erstelle Liste mit (filename, creation_time, request_data)
        requests_with_dates = []
        for req_file in requests:
            file_path = os.path.join(ANFRAGEN_DIR, req_file)
            creation_time = os.path.getctime(file_path)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    request_data = json.load(file)
                    request_data['filename'] = req_file
                    requests_with_dates.append((req_file, creation_time, request_data))
            except Exception as e:
                st.error(f"Fehler beim Laden der Datei {req_file}: {str(e)}")
        
        # Sortiere nach Erstellungsdatum (neueste zuerst)
        requests_with_dates.sort(key=lambda x: x[1], reverse=True)
        return requests_with_dates
    except Exception as e:
        st.error(f"Fehler beim Laden der Anfragen: {str(e)}")
        return []

def filter_requests(requests: List[tuple], search_term: str) -> List[tuple]:
    """Filter requests based on search term."""
    if not search_term:
        return requests
    
    search_term = search_term.lower()
    filtered = []
    for req_file, creation_time, request_data in requests:
        if (search_term in request_data.get('Firma', '').lower() or 
            search_term in request_data.get('Name', '').lower() or
            search_term in req_file.lower()):
            filtered.append((req_file, creation_time, request_data))
    return filtered

def archive_request(filename: str) -> bool:
    """Archive a request by renaming with Archiv_ prefix."""
    try:
        old_path = os.path.join(ANFRAGEN_DIR, filename)
        new_filename = filename.replace('Anfr_', 'Archiv_Anfr_')
        new_path = os.path.join(ANFRAGEN_DIR, new_filename)
        
        os.rename(old_path, new_path)
        logger.info(f"Successfully archived request: {filename}")
        return True
    except Exception as e:
        logger.error(f"Error archiving request {filename}: {str(e)}")
        st.error(f"Fehler beim Archivieren: {str(e)}")
        return False

def restore_request(filename: str) -> bool:
    """Restore an archived request by removing Archiv_ prefix."""
    try:
        old_path = os.path.join(ANFRAGEN_DIR, filename)
        new_filename = filename.replace('Archiv_Anfr_', 'Anfr_')
        new_path = os.path.join(ANFRAGEN_DIR, new_filename)
        
        os.rename(old_path, new_path)
        logger.info(f"Successfully restored request from archive: {filename}")
        return True
    except Exception as e:
        logger.error(f"Error restoring request {filename}: {str(e)}")
        st.error(f"Fehler beim Wiederherstellen: {str(e)}")
        return False

def validate_url(url: str) -> str:
    """Validate and clean URL."""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    try:
        result = urlparse(url)
        return url if all([result.scheme, result.netloc]) else ''
    except:
        return ''

def create_request_form():
    """Display and handle the request creation form."""
    st.title("Anfrageformular")
    
    # Initialisiere session state für Formularfelder
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {
            'firma': '',
            'website': '',
            'werte': '',
            'konkurrenz': '',
            'philosophie': '',
            'musik_praeferenz': '',
            'musik_firmensong': '',
            'ausrichtung': 0,
            'songlaenge': 0,
            'sonstiges': '',
            'name': '',
            'email': '',
            'telefon': ''
        }
    
    with st.form("request_form", clear_on_submit=False):  # clear_on_submit auf False gesetzt
        # Basisdaten
        st.markdown("### Unternehmen")
        firma = st.text_input("Firma *", value=st.session_state.form_data['firma'], help="Pflichtfeld")
        website = st.text_input("Website URL", value=st.session_state.form_data['website'], help="Bitte geben Sie die vollständige URL ein (z.B. https://www.example.com)")
        
        # Unternehmensprofil
        st.markdown("### Unternehmensprofil")
        werte = st.text_area("Was macht ihr Unternehmen aus?", value=st.session_state.form_data['werte'])
        konkurrenz = st.text_area("Womit grenzen Sie sich von Branchenkollegen ab?", value=st.session_state.form_data['konkurrenz'])
        philosophie = st.text_area("Worauf legen Sie innerhalb des Betriebes wert? Was ist Ihre Unternehmens-Philosophie?", value=st.session_state.form_data['philosophie'])
        
        # Musikpräferenzen
        st.markdown("### Musikpräferenzen")
        musik_praeferenz = st.text_area("Welche Art von Musik hören Sie gerne? (Mehrere Antworten möglich)", value=st.session_state.form_data['musik_praeferenz'])
        musik_firmensong = st.text_area("Welche Art von Musik könnten Sie sich gut für Ihren eigenen Firmensong vorstellen? (Mehrere Antworten möglich)", value=st.session_state.form_data['musik_firmensong'])
        
        # Ausrichtung
        st.markdown("### Ausrichtung")
        ausrichtung = st.radio(
            "Soll der Song eher Produktorientiert oder eher Emotionsorientiert (Wir-Gefühl) ausgerichtet sein?",
            options=['Bitte wählen', 'Produktorientiert', 'Emotionsorientiert (Wir-Gefühl)'],
            index=st.session_state.form_data['ausrichtung']
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
            index=st.session_state.form_data['songlaenge']
        )
        
        # Sonstiges
        st.markdown("### Sonstiges")
        sonstiges = st.text_area("Wünsche, Ideen, Vorschläge", value=st.session_state.form_data['sonstiges'])
        
        # Kontaktdaten
        st.markdown("### Kontaktdaten")
        name = st.text_input("Name *", value=st.session_state.form_data['name'], help="Pflichtfeld")
        email = st.text_input("E-Mail Adresse *", value=st.session_state.form_data['email'], help="Pflichtfeld")
        telefon = st.text_input("Telefonnummer", value=st.session_state.form_data['telefon'])
        
        # Aktualisiere session state mit aktuellen Werten
        st.session_state.form_data.update({
            'firma': firma,
            'website': website,
            'werte': werte,
            'konkurrenz': konkurrenz,
            'philosophie': philosophie,
            'musik_praeferenz': musik_praeferenz,
            'musik_firmensong': musik_firmensong,
            'ausrichtung': ['Bitte wählen', 'Produktorientiert', 'Emotionsorientiert (Wir-Gefühl)'].index(ausrichtung),
            'songlaenge': [
                'Bitte wählen',
                'Jingle 10 - 20 Sekunden',
                'Kompaktsong 90 - 120 Sekunden',
                'Markensong 120 - 180 Sekunden',
                'Unternehmenshymne 120 - 240 Sekunden',
                'Individueller Jubiläumssong (auf Anfrage)'
            ].index(songlaenge),
            'sonstiges': sonstiges,
            'name': name,
            'email': email,
            'telefon': telefon
        })
        
        submitted = st.form_submit_button("Absenden")
        
        if submitted:
            # Angepasste Validierung ohne Website und Telefon
            if not all([firma, name, email]):
                st.error("Bitte füllen Sie alle Pflichtfelder aus (Firma, Name, E-Mail).")
                return
            
            if ausrichtung == 'Bitte wählen' or songlaenge == 'Bitte wählen':
                st.error("Bitte treffen Sie eine Auswahl bei Ausrichtung und Songlänge.")
                return
            
            # Validiere URL nur wenn angegeben
            clean_url = ""
            if website:
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
                    # Erfolgsmeldung direkt hier anzeigen
                    st.success("✅ Ihre Anfrage wurde erfolgreich gespeichert!")
                    # Formular nach erfolgreichem Speichern zurücksetzen
                    st.session_state.form_data = {
                        'firma': '',
                        'website': '',
                        'werte': '',
                        'konkurrenz': '',
                        'philosophie': '',
                        'musik_praeferenz': '',
                        'musik_firmensong': '',
                        'ausrichtung': 0,
                        'songlaenge': 0,
                        'sonstiges': '',
                        'name': '',
                        'email': '',
                        'telefon': ''
                    }
                    st.session_state.form_submitted = True
                else:
                    st.error("Fehler beim Speichern der Anfrage.")
            except Exception as e:
                st.error(f"Fehler beim Speichern der Anfrage: {str(e)}")

def display_approval_section():
    """Display and handle the approval section."""
    st.title("Freigabe")
    
    # Initialisiere Session State für Suchfeld
    if 'requests_search' not in st.session_state:
        st.session_state.requests_search = ""
    
    try:
        # Tabs für aktuelle Anfragen und Archiv
        tab1, tab2 = st.tabs(["Aktuelle Anfragen", "Archiv"])
        
        with tab1:
            st.markdown("### Aktuelle Anfragen")
            
            # Suchleiste mit Clear-Button
            col_search, col_clear = st.columns([5, 1])
            
            with col_search:
                search_term = st.text_input(
                    "Anfrage suchen:",
                    value=st.session_state.requests_search,
                    placeholder="Firma, Name oder Dateiname eingeben...",
                    key="current_requests_search"
                )
            
            with col_clear:
                if st.button("❌", key="clear_requests_search", help="Suche löschen"):
                    st.session_state.requests_search = ""
                    st.rerun()
            
            st.session_state.requests_search = search_term
            
            # Lade und filtere Anfragen
            requests_with_dates = get_requests_with_dates()
            filtered_requests = filter_requests(requests_with_dates, search_term)
            
            if search_term:
                st.markdown(f"*{len(filtered_requests)} Anfrage(n) gefunden für '{search_term}'*")
            
            if not filtered_requests:
                if search_term:
                    st.info("Keine Anfragen gefunden, die dem Suchbegriff entsprechen.")
                else:
                    st.info("Keine Anfragen vorhanden.")
            else:
                # Zeige Anfragen
                for req_file, creation_time, request in filtered_requests:
                    creation_date = datetime.fromtimestamp(creation_time).strftime("%d.%m.%Y %H:%M")
                    status = request.get('status', 'ausstehend')
                    
                    # Status-Icon basierend auf Status
                    status_icon = {
                        'ausstehend': '⏳',
                        'freigegeben': '✅',
                        'in Bearbeitung': '🔄',
                        'abgelehnt': '❌'
                    }.get(status, '⏳')
                    
                    # Erweiterbarer Container für jede Anfrage
                    with st.expander(f"{status_icon} {request.get('Firma', 'Unbekannte Firma')} - {request.get('Name', 'Unbekannter Name')} - *{creation_date}*"):
                        
                        # Anzeige der Anfragedetails
                        col_info, col_status = st.columns([3, 1])
                        
                        with col_info:
                            st.markdown("#### Unternehmensdetails")
                            st.write(f"**Firma:** {request.get('Firma', '')}")
                            st.write(f"**Name:** {request.get('Name', '')}")
                            st.write(f"**Website:** {request.get('Website', 'Keine Website angegeben')}")
                            st.write(f"**E-Mail:** {request.get('Email', '')}")
                            st.write(f"**Telefon:** {request.get('Telefon', 'Nicht angegeben')}")
                            
                            st.markdown("#### Unternehmensprofil")
                            st.write(f"**Werte und Inhalte:** {request.get('Werte', '')}")
                            st.write(f"**Abgrenzung zur Konkurrenz:** {request.get('Konkurrenz', '')}")
                            st.write(f"**Unternehmensphilosophie:** {request.get('Philosophie', '')}")
                            
                            st.markdown("#### Musikpräferenzen")
                            st.write(f"**Musikstil Präferenz:** {request.get('Musik_Praeferenz', '')}")
                            st.write(f"**Gewünschter Musikstil:** {request.get('Musik_Firmensong', '')}")
                            st.write(f"**Ausrichtung:** {request.get('Ausrichtung', '')}")
                            st.write(f"**Songlänge:** {request.get('Songlaenge', '')}")
                            
                            if request.get('Sonstiges', ''):
                                st.markdown("#### Sonstiges")
                                st.write(request.get('Sonstiges', ''))
                        
                        with col_status:
                            st.markdown("#### Status & Aktionen")
                            
                            # Status-Anzeige mit Farbe
                            st.markdown(
                                f"**Aktueller Status:**<br/>:{STATUS_COLORS.get(status, 'gray')}[{status.upper()}]",
                                unsafe_allow_html=True
                            )
                            
                            st.markdown("---")
                            
                            # Action Buttons
                            col_btn1, col_btn2 = st.columns(2)
                            
                            with col_btn1:
                                if st.button("✅ Freigeben", key=f"approve_{req_file}", use_container_width=True):
                                    update_request_status(req_file, 'freigegeben')
                                    st.success("Anfrage freigegeben!")
                                    st.rerun()
                                
                                if st.button("🔄 In Bearbeitung", key=f"processing_{req_file}", use_container_width=True):
                                    update_request_status(req_file, 'in Bearbeitung')
                                    st.success("Status geändert!")
                                    st.rerun()
                            
                            with col_btn2:
                                if st.button("❌ Ablehnen", key=f"reject_{req_file}", use_container_width=True):
                                    update_request_status(req_file, 'abgelehnt')
                                    st.success("Anfrage abgelehnt!")
                                    st.rerun()
                                
                                if st.button("📦 Archivieren", key=f"archive_{req_file}", use_container_width=True):
                                    if archive_request(req_file):
                                        st.success(f"Anfrage von {request.get('Firma', 'Unbekannt')} wurde archiviert!")
                                        st.rerun()
        
        with tab2:
            st.markdown("### Archivierte Anfragen")
            
            # Suchleiste für Archiv mit Clear-Button
            col_archive_search, col_archive_clear = st.columns([5, 1])
            
            with col_archive_search:
                archive_search_term = st.text_input(
                    "Archivierte Anfragen suchen:",
                    placeholder="Firma, Name oder Dateiname eingeben...",
                    key="archive_requests_search"
                )
            
            with col_archive_clear:
                if st.button("❌", key="clear_archive_requests_search", help="Suche löschen"):
                    st.rerun()
            
            # Lade archivierte Anfragen
            try:
                files = os.listdir(ANFRAGEN_DIR)
                archived_requests = [f for f in files if f.endswith('.json') and f.startswith('Archiv_Anfr_')]
                
                # Erstelle Liste mit Daten für archivierte Anfragen
                archived_with_dates = []
                for req_file in archived_requests:
                    file_path = os.path.join(ANFRAGEN_DIR, req_file)
                    creation_time = os.path.getctime(file_path)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            request_data = json.load(file)
                            request_data['filename'] = req_file
                            archived_with_dates.append((req_file, creation_time, request_data))
                    except Exception as e:
                        st.error(f"Fehler beim Laden der Datei {req_file}: {str(e)}")
                
                archived_with_dates.sort(key=lambda x: x[1], reverse=True)
                filtered_archived = filter_requests(archived_with_dates, archive_search_term)
                
                if archive_search_term:
                    st.markdown(f"*{len(filtered_archived)} archivierte Anfrage(n) gefunden für '{archive_search_term}'*")
                
                if not filtered_archived:
                    if archive_search_term:
                        st.info("Keine archivierten Anfragen gefunden, die dem Suchbegriff entsprechen.")
                    else:
                        st.info("Keine archivierten Anfragen vorhanden.")
                else:
                    for req_file, creation_time, request in filtered_archived:
                        creation_date = datetime.fromtimestamp(creation_time).strftime("%d.%m.%Y %H:%M")
                        status = request.get('status', 'ausstehend')
                        
                        with st.expander(f"📦 {request.get('Firma', 'Unbekannte Firma')} - {request.get('Name', 'Unbekannter Name')} - *{creation_date}*"):
                            col_restore, col_details = st.columns([1, 4])
                            
                            with col_restore:
                                if st.button("🔄 Wiederherstellen", key=f"restore_{req_file}"):
                                    if restore_request(req_file):
                                        st.success(f"Anfrage von {request.get('Firma', 'Unbekannt')} wurde wiederhergestellt!")
                                        st.rerun()
                            
                            with col_details:
                                details_key = f"details_{req_file}"
                                if details_key not in st.session_state:
                                    st.session_state[details_key] = False
                                if st.button("Vollständige Details anzeigen", key=f"btn_{req_file}"):
                                    st.session_state[details_key] = not st.session_state[details_key]
                                if st.session_state[details_key]:
                                    st.write(f"**Website:** {request.get('Website', 'Keine Website angegeben')}")
                                    st.write(f"**Telefon:** {request.get('Telefon', 'Nicht angegeben')}")
                                    st.write(f"**Werte:** {request.get('Werte', '')}")
                                    st.write(f"**Konkurrenz:** {request.get('Konkurrenz', '')}")
                                    st.write(f"**Philosophie:** {request.get('Philosophie', '')}")
                                    st.write(f"**Musikpräferenz:** {request.get('Musik_Praeferenz', '')}")
                                    st.write(f"**Firmensong-Stil:** {request.get('Musik_Firmensong', '')}")
                                    st.write(f"**Ausrichtung:** {request.get('Ausrichtung', '')}")
                                    st.write(f"**Songlänge:** {request.get('Songlaenge', '')}")
                                    if request.get('Sonstiges', ''):
                                        st.write(f"**Sonstiges:** {request.get('Sonstiges', '')}")
                
            except Exception as e:
                st.error(f"Fehler beim Laden der archivierten Anfragen: {str(e)}")
                
    except Exception as e:
        st.error(f"Fehler in der Freigabe-Sektion: {str(e)}")

def save_songidee(filename: str, songidee: Dict) -> None:
    """Save edited songidee back to file."""
    try:
        file_path = os.path.join(ANFRAGEN_DIR, filename)
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(songidee, file, indent=4, ensure_ascii=False)
        st.success("Änderungen wurden erfolgreich gespeichert!")
    except Exception as e:
        st.error(f"Fehler beim Speichern: {str(e)}")

def get_songideen_with_dates() -> List[tuple]:
    """Get songideen with their creation dates, sorted by newest first."""
    try:
        if not os.path.exists(ANFRAGEN_DIR):
            return []
            
        files = os.listdir(ANFRAGEN_DIR)
        songideen = [f for f in files if f.endswith('.json') and f.startswith('Song_')]
        
        # Erstelle Liste mit (filename, creation_time, title)
        songideen_with_dates = []
        for song_file in songideen:
            file_path = os.path.join(ANFRAGEN_DIR, song_file)
            creation_time = os.path.getctime(file_path)
            
            # Versuche Titel aus der JSON-Datei zu lesen
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    songidee_data = json.load(file)
                    if isinstance(songidee_data, list) and songidee_data:
                        title = songidee_data[0].get('Titel', song_file.replace('.json', '').replace('Song_', ''))
                    else:
                        title = song_file.replace('.json', '').replace('Song_', '')
            except:
                title = song_file.replace('.json', '').replace('Song_', '')
            
            songideen_with_dates.append((song_file, creation_time, title))
        
        # Sortiere nach Erstellungsdatum (neueste zuerst)
        songideen_with_dates.sort(key=lambda x: x[1], reverse=True)
        return songideen_with_dates
    except Exception as e:
        st.error(f"Fehler beim Laden der Songideen: {str(e)}")
        return []

def filter_songideen(songideen: List[tuple], search_term: str) -> List[tuple]:
    """Filter songideen based on search term."""
    if not search_term:
        return songideen
    
    search_term = search_term.lower()
    filtered = []
    for song_file, creation_time, title in songideen:
        if search_term in title.lower() or search_term in song_file.lower():
            filtered.append((song_file, creation_time, title))
    return filtered

def archive_songidee(filename: str) -> bool:
    """Archive a songidee by renaming with Archiv_ prefix."""
    try:
        old_path = os.path.join(ANFRAGEN_DIR, filename)
        new_filename = filename.replace('Song_', 'Archiv_Song_')
        new_path = os.path.join(ANFRAGEN_DIR, new_filename)
        
        os.rename(old_path, new_path)
        return True
    except Exception as e:
        st.error(f"Fehler beim Archivieren: {str(e)}")
        return False

def restore_songidee(filename: str) -> bool:
    """Restore an archived songidee by removing Archiv_ prefix."""
    try:
        old_path = os.path.join(ANFRAGEN_DIR, filename)
        new_filename = filename.replace('Archiv_Song_', 'Song_')
        new_path = os.path.join(ANFRAGEN_DIR, new_filename)
        
        os.rename(old_path, new_path)
        return True
    except Exception as e:
        st.error(f"Fehler beim Wiederherstellen: {str(e)}")
        return False

def display_songideen_section():
    """Display and handle the songideen section."""
    st.title("Songideen")
    
    # Initialisiere Session State für Suchfeld
    if 'songideen_search' not in st.session_state:
        st.session_state.songideen_search = ""
    
    try:
        # Tabs für aktuelle Songideen und Archiv
        tab1, tab2 = st.tabs(["Aktuelle Songideen", "Archiv"])
        
        with tab1:
            st.markdown("### Aktuelle Songideen")
            
            # Suchleiste mit Clear-Button
            col_search, col_clear = st.columns([5, 1])
            
            with col_search:
                search_term = st.text_input(
                    "Songidee suchen:",
                    value=st.session_state.songideen_search,
                    placeholder="Titel oder Dateiname eingeben...",
                    key="current_songideen_search"
                )
            
            with col_clear:
                if st.button("❌", key="clear_songideen_search", help="Suche löschen"):
                    st.session_state.songideen_search = ""
                    st.rerun()
            
            st.session_state.songideen_search = search_term
            
            # Lade und filtere Songideen
            songideen_with_dates = get_songideen_with_dates()
            filtered_songideen = filter_songideen(songideen_with_dates, search_term)
            
            if search_term:
                st.markdown(f"*{len(filtered_songideen)} Songidee(n) gefunden für '{search_term}'*")
            
            if not filtered_songideen:
                if search_term:
                    st.info("Keine Songideen gefunden, die dem Suchbegriff entsprechen.")
                else:
                    st.info("Keine Songideen vorhanden.")
            else:
                # Zeige Songideen
                for song_file, creation_time, title in filtered_songideen:
                    creation_date = datetime.fromtimestamp(creation_time).strftime("%d.%m.%Y %H:%M")
                    
                    # Erweiterbarer Container für jede Songidee
                    with st.expander(f"🎵 {title} - *{creation_date}*"):
                        file_path = os.path.join(ANFRAGEN_DIR, song_file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as file:
                                songideen_list = json.load(file)
                                songidee = songideen_list[0] if isinstance(songideen_list, list) else songideen_list
                            
                            # Editierbare Felder
                            with st.form(f"edit_songidee_form_{song_file}"):
                                edited_titel = st.text_input(
                                    "Titel",
                                    value=songidee.get('Titel', title),
                                    help="Dieser Titel wird für die MP3-Datei verwendet",
                                    key=f"titel_{song_file}"
                                )
                                
                                edited_firma = st.text_input(
                                    "Firma",
                                    value=songidee.get('Firma', ''),
                                    key=f"firma_{song_file}"
                                )
                                
                                edited_songidee = st.text_area(
                                    "Songidee",
                                    value=songidee.get('Songidee', ''),
                                    height=200,
                                    key=f"songidee_{song_file}"
                                )
                                
                                edited_begruendung = st.text_area(
                                    "Begründung",
                                    value=songidee.get('Begründung', ''),
                                    height=150,
                                    key=f"begruendung_{song_file}"
                                )
                                
                                edited_lyrics = st.text_area(
                                    "Lyrics",
                                    value=songidee.get('Lyrics', ''),
                                    height=200,
                                    key=f"lyrics_{song_file}"
                                )
                                
                                edited_description = st.text_area(
                                    "Description",
                                    value=songidee.get('Description', ''),
                                    height=100,
                                    key=f"description_{song_file}"
                                )
                                
                                edited_status = st.text_input(
                                    "Status",
                                    value=songidee.get('Status', ''),
                                    key=f"status_{song_file}"
                                )
                                
                                # Drei Buttons nebeneinander
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    submit_button = st.form_submit_button("💾 Speichern")
                                with col2:
                                    create_song_button = st.form_submit_button("🎤 Song erstellen")
                                with col3:
                                    archive_button = st.form_submit_button("📦 Archivieren")
                                
                                if submit_button:
                                    updated_songidee = [{
                                        'Titel': edited_titel,
                                        'Firma': edited_firma,
                                        'Songidee': edited_songidee,
                                        'Begründung': edited_begruendung,
                                        'Lyrics': edited_lyrics,
                                        'Description': edited_description,
                                        'Status': edited_status
                                    }]
                                    
                                    try:
                                        with open(file_path, 'w', encoding='utf-8') as file:
                                            json.dump(updated_songidee, file, indent=2, ensure_ascii=False)
                                        st.success("Änderungen wurden erfolgreich gespeichert!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Fehler beim Speichern der Änderungen: {str(e)}")
                                        
                                if create_song_button:
                                    if not edited_titel.strip():
                                        st.error("Bitte geben Sie einen Titel ein, bevor Sie den Song erstellen.")
                                    else:
                                        updated_songidee = [{
                                            'Titel': edited_titel,
                                            'Firma': edited_firma,
                                            'Songidee': edited_songidee,
                                            'Begründung': edited_begruendung,
                                            'Lyrics': edited_lyrics,
                                            'Description': edited_description,
                                            'Status': "An Mureka weitergegeben"
                                        }]
                                        
                                        try:
                                            with open(file_path, 'w', encoding='utf-8') as file:
                                                json.dump(updated_songidee, file, indent=2, ensure_ascii=False)
                                                
                                            logger.info(f"Starting song processing for file: {file_path}")
                                            # Convert to absolute path if it's not already
                                            abs_file_path = os.path.abspath(file_path)
                                            process_job(abs_file_path)
                                            logger.info(f"Successfully processed song job for file: {file_path}")
                                            st.success("Song wurde an Mureka weitergegeben!")
                                            st.rerun()
                                        except Exception as e:
                                            logger.error(f"Error processing song job for file {file_path}: {str(e)}")
                                            st.error(f"Fehler beim Weitergeben des Songs: {str(e)}")
                                
                                if archive_button:
                                    if archive_songidee(song_file):
                                        st.success(f"'{title}' wurde archiviert!")
                                        st.rerun()
                            
                        except Exception as e:
                            st.error(f"Fehler beim Laden der Datei {song_file}: {str(e)}")
        
        with tab2:
            st.markdown("### Archivierte Songideen")
            
            # Suchleiste für Archiv mit Clear-Button
            col_archive_search, col_archive_clear = st.columns([5, 1])
            
            with col_archive_search:
                archive_search_term = st.text_input(
                    "Archivierte Songideen suchen:",
                    placeholder="Titel oder Dateiname eingeben...",
                    key="archive_songideen_search"
                )
            
            with col_archive_clear:
                if st.button("❌", key="clear_archive_songideen_search", help="Suche löschen"):
                    st.rerun()
            
            # Lade archivierte Songideen
            try:
                files = os.listdir(ANFRAGEN_DIR)
                archived_songideen = [f for f in files if f.endswith('.json') and f.startswith('Archiv_Song_')]
                
                # Erstelle Liste mit Daten für archivierte Songideen
                archived_with_dates = []
                for song_file in archived_songideen:
                    file_path = os.path.join(ANFRAGEN_DIR, song_file)
                    creation_time = os.path.getctime(file_path)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            songidee_data = json.load(file)
                            if isinstance(songidee_data, list) and songidee_data:
                                title = songidee_data[0].get('Titel', song_file.replace('.json', '').replace('Archiv_Song_', ''))
                            else:
                                title = song_file.replace('.json', '').replace('Archiv_Song_', '')
                    except:
                        title = song_file.replace('.json', '').replace('Archiv_Song_', '')
                    
                    archived_with_dates.append((song_file, creation_time, title))
                
                archived_with_dates.sort(key=lambda x: x[1], reverse=True)
                filtered_archived = filter_songideen(archived_with_dates, archive_search_term)
                
                if archive_search_term:
                    st.markdown(f"*{len(filtered_archived)} archivierte Songidee(n) gefunden für '{archive_search_term}'*")
                
                if not filtered_archived:
                    if archive_search_term:
                        st.info("Keine archivierten Songideen gefunden, die dem Suchbegriff entsprechen.")
                    else:
                        st.info("Keine archivierten Songideen vorhanden.")
                else:
                    for song_file, creation_time, title in filtered_archived:
                        creation_date = datetime.fromtimestamp(creation_time).strftime("%d.%m.%Y %H:%M")
                        
                        with st.expander(f"📦 {title} - *{creation_date}*"):
                            if st.button("Wiederherstellen", key=f"restore_{song_file}"):
                                if restore_songidee(song_file):
                                    st.success(f"'{title}' wurde wiederhergestellt!")
                                    st.rerun()
                            
                            details_key = f"details_{song_file}"
                            if details_key not in st.session_state:
                                st.session_state[details_key] = False
                            if st.button("Vollständige Details anzeigen", key=f"btn_{song_file}"):
                                st.session_state[details_key] = not st.session_state[details_key]
                            if st.session_state[details_key]:
                                file_path = os.path.join(ANFRAGEN_DIR, song_file)
                                try:
                                    with open(file_path, 'r', encoding='utf-8') as file:
                                        songideen_list = json.load(file)
                                        songidee = songideen_list[0] if isinstance(songideen_list, list) else songideen_list
                                    
                                    st.text_area("Songidee", songidee.get('Songidee', ''), disabled=True, key=f"arch_songidee_{song_file}")
                                    st.text_area("Begründung", songidee.get('Begründung', ''), disabled=True, key=f"arch_begruendung_{song_file}")
                                    st.text_area("Lyrics", songidee.get('Lyrics', ''), disabled=True, key=f"arch_lyrics_{song_file}")
                                    st.text_input("Status", songidee.get('Status', ''), disabled=True, key=f"arch_status_{song_file}")
                                
                                except Exception as e:
                                    st.error(f"Fehler beim Laden der Datei {song_file}: {str(e)}")
                
            except Exception as e:
                st.error(f"Fehler beim Laden der archivierten Songideen: {str(e)}")
                
    except Exception as e:
        st.error(f"Fehler beim Laden der Songideen: {str(e)}")

def move_song_to_archive(song_filename: str) -> bool:
    """Move song from output to archive folder."""
    try:
        output_dir = os.path.join(BASE_DIR, 'output')
        archive_dir = os.path.join(output_dir, 'archiv')
        
        # Erstelle Archiv-Ordner falls er nicht existiert
        if not os.path.exists(archive_dir):
            os.makedirs(archive_dir)
            logger.info(f"Created archive directory: {archive_dir}")
        
        source_path = os.path.join(output_dir, song_filename)
        dest_path = os.path.join(archive_dir, song_filename)
        
        # Verschiebe die Datei
        os.rename(source_path, dest_path)
        logger.info(f"Successfully archived song: {song_filename}")
        return True
    except Exception as e:
        logger.error(f"Error archiving song {song_filename}: {str(e)}")
        st.error(f"Fehler beim Archivieren: {str(e)}")
        return False

def move_song_from_archive(song_filename: str) -> bool:
    """Move song from archive back to output folder."""
    try:
        output_dir = os.path.join(BASE_DIR, 'output')
        archive_dir = os.path.join(output_dir, 'archiv')
        
        source_path = os.path.join(archive_dir, song_filename)
        dest_path = os.path.join(output_dir, song_filename)
        
        # Verschiebe die Datei zurück
        os.rename(source_path, dest_path)
        logger.info(f"Successfully restored song from archive: {song_filename}")
        return True
    except Exception as e:
        logger.error(f"Error restoring song {song_filename}: {str(e)}")
        st.error(f"Fehler beim Wiederherstellen: {str(e)}")
        return False

def get_songs_with_dates(directory: str) -> List[tuple]:
    """Get songs with their creation dates, sorted by newest first."""
    try:
        if not os.path.exists(directory):
            return []
            
        files = os.listdir(directory)
        songs = [f for f in files if f.endswith('.mp3')]
        
        # Erstelle Liste mit (filename, creation_time)
        songs_with_dates = []
        for song in songs:
            file_path = os.path.join(directory, song)
            creation_time = os.path.getctime(file_path)
            songs_with_dates.append((song, creation_time))
        
        # Sortiere nach Erstellungsdatum (neueste zuerst)
        songs_with_dates.sort(key=lambda x: x[1], reverse=True)
        return songs_with_dates
    except Exception as e:
        st.error(f"Fehler beim Laden der Songs: {str(e)}")
        return []

def filter_songs(songs: List[tuple], search_term: str) -> List[tuple]:
    """Filter songs based on search term."""
    if not search_term:
        return songs
    
    search_term = search_term.lower()
    filtered = []
    for song, creation_time in songs:
        if search_term in song.lower():
            filtered.append((song, creation_time))
    return filtered

def display_song_list(songs: List[tuple], directory: str, is_archive: bool = False):
    """Display list of songs with player, download, and archive buttons."""
    if not songs:
        if is_archive:
            st.info("Keine archivierten Songs vorhanden.")
        else:
            st.info("Keine Songs im Output-Ordner vorhanden.")
        return
    
    for song, creation_time in songs:
        with st.container():
            # Zeige Erstellungsdatum
            creation_date = datetime.fromtimestamp(creation_time).strftime("%d.%m.%Y %H:%M")
            st.markdown(f"### {song.replace('.mp3', '').replace('_', ' ')}")
            st.markdown(f"*Erstellt am: {creation_date}*")
            
            # Layout: Player, Download, Archive/Restore Button
            col1, col2, col3 = st.columns([4, 1, 1])
            
            audio_path = os.path.join(directory, song)
            with open(audio_path, 'rb') as audio_file:
                audio_bytes = audio_file.read()
                
                # MP3-Player
                with col1:
                    st.audio(audio_bytes, format='audio/mp3')
                
                # Download-Button
                with col2:
                    st.download_button(
                        label="⬇️ Download",
                        data=audio_bytes,
                        file_name=song,
                        mime="audio/mpeg",
                        key=f"download_{song}_{is_archive}"
                    )
                
                # Archive/Restore Button
                with col3:
                    if is_archive:
                        if st.button("Wiederherstellen", key=f"restore_{song}"):
                            if move_song_from_archive(song):
                                st.success(f"'{song}' wurde wiederhergestellt!")
                                st.rerun()
                    else:
                        if st.button("Archivieren", key=f"archive_{song}"):
                            if move_song_to_archive(song):
                                st.success(f"'{song}' wurde archiviert!")
                                st.rerun()
            
            st.divider()

def display_songs_section():
    """Display songs from output directory with search and archive functionality."""
    st.title("Songs")
    
    # Initialisiere Session State für Suchfeld
    if 'song_search' not in st.session_state:
        st.session_state.song_search = ""
    
    try:
        output_dir = os.path.join(BASE_DIR, 'output')
        archive_dir = os.path.join(output_dir, 'archiv')
        
        # Erstelle Output-Ordner falls er nicht existiert
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Tabs für aktuelle Songs und Archiv
        tab1, tab2 = st.tabs(["Aktuelle Songs", "Archiv"])
        
        with tab1:
            st.markdown("### Aktuelle Songs")
            
            # Suchleiste mit Clear-Button
            col_search, col_clear = st.columns([5, 1])
            
            with col_search:
                search_term = st.text_input(
                    "Song suchen:",
                    value=st.session_state.song_search,
                    placeholder="Song-Titel eingeben...",
                    key="current_search"
                )
            
            with col_clear:
                if st.button("❌", key="clear_current_search", help="Suche löschen"):
                    st.session_state.song_search = ""
                    st.rerun()
            
            st.session_state.song_search = search_term
            
            # Lade und filtere Songs
            songs_with_dates = get_songs_with_dates(output_dir)
            filtered_songs = filter_songs(songs_with_dates, search_term)
            
            if search_term:
                st.markdown(f"*{len(filtered_songs)} Song(s) gefunden für '{search_term}'*")
            
            # Zeige Songs
            display_song_list(filtered_songs, output_dir, is_archive=False)
        
        with tab2:
            st.markdown("### Archivierte Songs")
            
            # Suchleiste für Archiv mit Clear-Button
            col_archive_search, col_archive_clear = st.columns([5, 1])
            
            with col_archive_search:
                archive_search_term = st.text_input(
                    "Archivierte Songs suchen:",
                    placeholder="Song-Titel eingeben...",
                    key="archive_search"
                )
            
            with col_archive_clear:
                if st.button("❌", key="clear_archive_search", help="Suche löschen"):
                    st.rerun()
            
            # Lade und filtere archivierte Songs
            archived_songs_with_dates = get_songs_with_dates(archive_dir)
            filtered_archived_songs = filter_songs(archived_songs_with_dates, archive_search_term)
            
            if archive_search_term:
                st.markdown(f"*{len(filtered_archived_songs)} archivierte(r) Song(s) gefunden für '{archive_search_term}'*")
            
            # Zeige archivierte Songs
            display_song_list(filtered_archived_songs, archive_dir, is_archive=True)
    
    except Exception as e:
        st.error(f"Fehler beim Laden der Songs: {str(e)}")

def get_david_style_songs_with_dates() -> List[tuple]:
    """Get David-Style songs with their creation dates, sorted by newest first."""
    try:
        voicecloned_dir = "/proj/voicecloned"
        if not os.path.exists(voicecloned_dir):
            return []
            
        files = os.listdir(voicecloned_dir)
        songs = [f for f in files if f.endswith('.mp3')]
        
        # Erstelle Liste mit (filename, creation_time)
        songs_with_dates = []
        for song in songs:
            file_path = os.path.join(voicecloned_dir, song)
            creation_time = os.path.getctime(file_path)
            songs_with_dates.append((song, creation_time))
        
        # Sortiere nach Erstellungsdatum (neueste zuerst)
        songs_with_dates.sort(key=lambda x: x[1], reverse=True)
        return songs_with_dates
    except Exception as e:
        st.error(f"Fehler beim Laden der David-Style Songs: {str(e)}")
        return []

def filter_david_style_songs(songs: List[tuple], search_term: str) -> List[tuple]:
    """Filter David-Style songs based on search term."""
    if not search_term:
        return songs
    
    search_term = search_term.lower()
    filtered = []
    for song, creation_time in songs:
        if search_term in song.lower():
            filtered.append((song, creation_time))
    return filtered

def display_david_style_song_list(songs: List[tuple]):
    """Display list of David-Style songs with player and download buttons."""
    if not songs:
        st.info("Keine David-Style Songs im voicecloned-Ordner vorhanden.")
        return
    
    for song, creation_time in songs:
        with st.container():
            # Zeige Erstellungsdatum
            creation_date = datetime.fromtimestamp(creation_time).strftime("%d.%m.%Y %H:%M")
            st.markdown(f"### {song.replace('.mp3', '').replace('_', ' ')}")
            st.markdown(f"*Erstellt am: {creation_date}*")
            
            # Layout: Player und Download Button
            col1, col2 = st.columns([4, 1])
            
            audio_path = os.path.join("/proj/voicecloned", song)
            try:
                with open(audio_path, 'rb') as audio_file:
                    audio_bytes = audio_file.read()
                    
                    # MP3-Player
                    with col1:
                        st.audio(audio_bytes, format='audio/mp3')
                    
                    # Download-Button
                    with col2:
                        st.download_button(
                            label="⬇️ Download",
                            data=audio_bytes,
                            file_name=song,
                            mime="audio/mpeg",
                            key=f"download_david_{song}"
                        )
            except Exception as e:
                st.error(f"Fehler beim Laden der Datei {song}: {str(e)}")
            
            st.divider()

def display_david_style_section():
    """Display David-Style songs from voicecloned directory with search functionality."""
    st.title("David-Style")
    
    try:
        voicecloned_dir = "/proj/voicecloned"
        
        # Prüfe ob Verzeichnis existiert
        if not os.path.exists(voicecloned_dir):
            st.error(f"Das Verzeichnis {voicecloned_dir} existiert nicht!")
            return
        
        st.markdown("### David-Style Songs")
        
        # Suchleiste mit Clear-Button
        col_search, col_clear = st.columns([5, 1])
        
        with col_search:
            search_term = st.text_input(
                "David-Style Song suchen:",
                placeholder="Song-Titel eingeben...",
                key="david_style_search"
            )
        
        with col_clear:
            if st.button("❌", key="clear_david_style_search", help="Suche löschen"):
                st.rerun()
        
        # Lade und filtere Songs
        songs_with_dates = get_david_style_songs_with_dates()
        filtered_songs = filter_david_style_songs(songs_with_dates, search_term)
        
        if search_term:
            st.markdown(f"*{len(filtered_songs)} David-Style Song(s) gefunden für '{search_term}'*")
        
        # Zeige Songs
        display_david_style_song_list(filtered_songs)
    
    except Exception as e:
        st.error(f"Fehler beim Laden der David-Style Songs: {str(e)}")

def get_vocals_only_songs_with_dates() -> List[tuple]:
    """Get Vocals-Only songs with their creation dates, sorted by newest first."""
    try:
        vocals_dir = "/proj/separated/vocals_only/htdemucs"
        if not os.path.exists(vocals_dir):
            return []
            
        # Get all subdirectories (each represents a song)
        song_dirs = []
        for item in os.listdir(vocals_dir):
            item_path = os.path.join(vocals_dir, item)
            if os.path.isdir(item_path):
                # Check if vocals_rvc.wav exists in this directory
                vocals_file = os.path.join(item_path, "vocals_rvc.wav")
                no_vocals_file = os.path.join(item_path, "no_vocals.wav")
                if os.path.exists(vocals_file):
                    creation_time = os.path.getctime(vocals_file)
                    song_dirs.append((item, creation_time, vocals_file, no_vocals_file))
        
        # Sort by creation date (newest first)
        song_dirs.sort(key=lambda x: x[1], reverse=True)
        return song_dirs
    except Exception as e:
        st.error(f"Fehler beim Laden der Stems: {str(e)}")
        return []

def filter_vocals_only_songs(songs: List[tuple], search_term: str) -> List[tuple]:
    """Filter Vocals-Only songs based on search term."""
    if not search_term:
        return songs
    
    search_term = search_term.lower()
    filtered = []
    for song_name, creation_time, vocals_file, no_vocals_file in songs:
        if search_term in song_name.lower():
            filtered.append((song_name, creation_time, vocals_file, no_vocals_file))
    return filtered

def display_vocals_only_song_list(songs: List[tuple]):
    """Display list of Vocals-Only songs with player and download buttons."""
    if not songs:
        st.info("Keine Stems im vocals_only-Ordner vorhanden.")
        return
    
    for song_name, creation_time, vocals_file, no_vocals_file in songs:
        # Create a container with border styling
        st.markdown(f"""
        <div style="
            padding: 20px;
            margin: 20px 0;
        ">
        """, unsafe_allow_html=True)
        
        # Show song name as main title
        creation_date = datetime.fromtimestamp(creation_time).strftime("%d.%m.%Y %H:%M")
        st.markdown(f"## {song_name}")
        st.markdown(f"*Erstellt am: {creation_date}*")
        
        # Create two columns for the two audio files
        col1, col2 = st.columns(2)
        
        # Vocals RVC (Geklonte Stimme)
        with col1:
            st.markdown("**Geklonte Stimme (vocals_rvc.wav)**")
            try:
                if os.path.exists(vocals_file):
                    with open(vocals_file, 'rb') as audio_file:
                        audio_bytes = audio_file.read()
                        
                        # Audio Player
                        st.audio(audio_bytes, format='audio/wav')
                        
                        # Download Button
                        st.download_button(
                            label="Download geklonte Stimme",
                            data=audio_bytes,
                            file_name=f"{song_name}_vocals_rvc.wav",
                            mime="audio/wav",
                            key=f"download_vocals_rvc_{song_name}"
                        )
                else:
                    st.error("vocals_rvc.wav nicht gefunden")
            except Exception as e:
                st.error(f"Fehler beim Laden der vocals_rvc.wav: {str(e)}")
        
        # No Vocals (Instrumente)
        with col2:
            st.markdown("**Instrumente (no_vocals.wav)**")
            try:
                if os.path.exists(no_vocals_file):
                    with open(no_vocals_file, 'rb') as audio_file:
                        audio_bytes = audio_file.read()
                        
                        # Audio Player
                        st.audio(audio_bytes, format='audio/wav')
                        
                        # Download Button
                        st.download_button(
                            label="Download Instrumente",
                            data=audio_bytes,
                            file_name=f"{song_name}_no_vocals.wav",
                            mime="audio/wav",
                            key=f"download_no_vocals_{song_name}"
                        )
                else:
                    st.error("no_vocals.wav nicht gefunden")
            except Exception as e:
                st.error(f"Fehler beim Laden der no_vocals.wav: {str(e)}")
        
        # Close the container
        st.markdown("</div>", unsafe_allow_html=True)

def display_vocals_only_section():
    """Display Vocals-Only songs from vocals_only directory with search functionality."""
    st.title("Stems")
    
    try:
        vocals_dir = "/proj/separated/vocals_only/htdemucs"
        
        # Check if directory exists
        if not os.path.exists(vocals_dir):
            st.error(f"Das Verzeichnis {vocals_dir} existiert nicht!")
            return
        
        st.markdown("### Stems")
        
        # Search bar with Clear Button
        col_search, col_clear = st.columns([5, 1])
        
        with col_search:
            search_term = st.text_input(
                "Stems suchen:",
                placeholder="Song-Titel eingeben...",
                key="vocals_only_search"
            )
        
        with col_clear:
            if st.button("❌", key="clear_vocals_only_search", help="Suche löschen"):
                st.rerun()
        
        # Load and filter songs
        songs_with_dates = get_vocals_only_songs_with_dates()
        filtered_songs = filter_vocals_only_songs(songs_with_dates, search_term)
        
        if search_term:
            st.markdown(f"*{len(filtered_songs)} Stems gefunden für '{search_term}'*")
        
        # Show songs
        display_vocals_only_song_list(filtered_songs)
    
    except Exception as e:
        st.error(f"Fehler beim Laden der Vocals-Only Songs: {str(e)}")

def main():
    """Main application."""
    try:
        logger.info("Starting Streamlit application")
        st.set_page_config(
            page_title="Anfragen Management",
            page_icon="📝",
            layout="wide"
        )
        
        # CSS-Datei global laden (falls vorhanden)
        css_file_path = "style.css"  # Pfad zu Ihrer CSS-Datei
        if os.path.exists(css_file_path):
            with open(css_file_path, 'r', encoding='utf-8') as f:
                st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
                logger.info(f"CSS file loaded: {css_file_path}")
        
    except Exception as e:
        logger.error(f"Error during application startup: {str(e)}")
        pass
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(TABS)
    
    with tab1:
        create_request_form()
    
    with tab2:
        display_approval_section()
        
    with tab3:
        display_songideen_section()
        
    with tab4:
        display_songs_section()
        
    with tab5:
        display_david_style_section()
        
    with tab6:
        display_vocals_only_section()
        
    logger.info("Application shutdown")

if __name__ == "__main__":
    main()
