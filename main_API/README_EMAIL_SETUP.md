# E-Mail-Benachrichtigungen Setup

## Übersicht
Das Anfragen-Management-System sendet automatisch E-Mail-Benachrichtigungen an David, wenn eine neue Anfrage eingeht.

## Konfiguration

### 1. E-Mail-Konfigurationsdatei bearbeiten
Öffnen Sie die Datei `email_config.py` und füllen Sie alle Felder aus:

```python
# Empfänger-E-Mail-Adresse
EMAIL_RECIPIENT = "david@example.com"  # Hier Davids E-Mail-Adresse eintragen

# SMTP-Server-Einstellungen
SMTP_SERVER = "smtp.gmail.com"  # Für Gmail
SMTP_PORT = 587

# Absender-E-Mail-Einstellungen
SMTP_USERNAME = "ihre-email@gmail.com"  # Ihre E-Mail-Adresse
SMTP_PASSWORD = "ihr-app-passwort"      # Ihr App-Passwort
SENDER_EMAIL = "ihre-email@gmail.com"   # Absender-E-Mail
```

### 2. E-Mail-Anbieter-spezifische Einstellungen

#### Gmail
- **SMTP_SERVER**: `smtp.gmail.com`
- **SMTP_PORT**: `587`
- **App-Passwort erforderlich**: 
  1. Gehen Sie zu Google-Konten-Einstellungen
  2. Aktivieren Sie 2-Faktor-Authentifizierung
  3. Erstellen Sie ein App-Passwort unter "Sicherheit"
  4. Verwenden Sie dieses App-Passwort (nicht Ihr normales Passwort!)

#### Outlook/Hotmail
- **SMTP_SERVER**: `smtp-mail.outlook.com`
- **SMTP_PORT**: `587`
- **Passwort**: Ihr normales Passwort

#### Yahoo
- **SMTP_SERVER**: `smtp.mail.yahoo.com`
- **SMTP_PORT**: `587`
- **App-Passwort erforderlich**

### 3. Test der Konfiguration
Nach der Konfiguration können Sie testen, ob die E-Mail-Benachrichtigungen funktionieren, indem Sie eine neue Anfrage über das Formular erstellen.

## E-Mail-Inhalt
Die E-Mail enthält folgende Informationen:
- Firma
- Name des Ansprechpartners
- E-Mail-Adresse
- Telefonnummer
- Ausrichtung (Produktorientiert/Emotionsorientiert)
- Gewünschte Songlänge

## Fehlerbehebung

### E-Mail wird nicht gesendet
1. Prüfen Sie, ob alle Felder in `email_config.py` ausgefüllt sind
2. Überprüfen Sie die SMTP-Einstellungen
3. Stellen Sie sicher, dass App-Passwörter korrekt sind (bei Gmail/Yahoo)
4. Prüfen Sie die Firewall-Einstellungen

### Logs überprüfen
Die E-Mail-Versuche werden in der `streamlit_log` Datei protokolliert.

## Sicherheitshinweise
- Verwenden Sie niemals Ihr normales Passwort für SMTP
- Verwenden Sie App-Passwörter wo möglich
- Halten Sie die `email_config.py` sicher und teilen Sie sie nicht öffentlich
- Erwägen Sie die Verwendung von Umgebungsvariablen für sensible Daten 