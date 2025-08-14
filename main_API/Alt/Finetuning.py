import os
import sys
import time
import json
import glob
import argparse
import requests

def upload_file(filepath, api_key):
    """
    Lädt eine einzelne Audiodatei hoch und gibt die file_id zurück.
    """
    url = "https://api.mureka.ai/v1/uploads"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    files = {
        "file": open(filepath, "rb")
    }
    data = {
        "purpose": "finetune"
    }
    resp = requests.post(url, headers=headers, files=files, data=data)
    if resp.status_code != 200:
        print(f"[ERROR] Upload von '{filepath}' fehlgeschlagen (Status {resp.status_code}): {resp.text}")
        sys.exit(1)
    resp_json = resp.json()
    file_id = resp_json.get("id")
    if not file_id:
        print(f"[ERROR] Keine file_id in der Antwort für '{filepath}': {resp.text}")
        sys.exit(1)
    print(f"✅ '{os.path.basename(filepath)}' hochgeladen → file_id = {file_id}")
    return file_id

def create_finetune_job(file_ids, base_model, suffix, api_key):
    """
    Erstellt den Fine-Tuning-Job und gibt die finetune_id zurück.
    """
    url = "https://api.mureka.ai/v1/finetuning/create"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "base_model": base_model,
        "suffix": suffix,
        "training_data": file_ids
    }
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        print(f"[ERROR] Fine-Tuning-Job erstellen fehlgeschlagen (Status {resp.status_code}): {resp.text}")
        sys.exit(1)
    resp_json = resp.json()
    finetune_id = resp_json.get("id")
    if not finetune_id:
        print(f"[ERROR] Keine finetune_id in der Antwort: {resp.text}")
        sys.exit(1)
    print(f"🚀 Fine-Tuning-Job gestartet → finetune_id = {finetune_id}")
    return finetune_id

def wait_for_finetune(finetune_id, api_key, interval=60):
    """
    Fragt alle 'interval' Sekunden den Status des Jobs ab, bis er 'succeeded' oder 'failed' ist.
    Gibt das gesamte Antwort-JSON der letzten Abfrage zurück.
    """
    url = f"https://api.mureka.ai/v1/finetuning/{finetune_id}"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    print(f"⏳ Warte auf Abschluss des Fine-Tuning-Jobs (Polling alle {interval} s)…")
    while True:
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            print(f"[ERROR] Status-Abfrage fehlgeschlagen (Status {resp.status_code}): {resp.text}")
            sys.exit(1)
        resp_json = resp.json()
        status = resp_json.get("status")
        print(f"   → Status: {status}")
        if status == "succeeded":
            print("✅ Fine-Tuning erfolgreich abgeschlossen.")
            return resp_json
        elif status == "failed":
            print("[ERROR] Fine-Tuning-Job ist fehlgeschlagen.")
            if "logs" in resp_json:
                print("Logs:", json.dumps(resp_json["logs"], indent=2, ensure_ascii=False))
            sys.exit(1)
        time.sleep(interval)

def generate_song_from_json(song_json_path, model_name, api_key):
    """
    Liest eine JSON-Datei mit Parametern für die Song-Generierung, ergänzt das Modell,
    sendet den Request an die API und gibt die Antwort zurück.
    """
    if not os.path.isfile(song_json_path):
        print(f"[ERROR] Song-JSON-Datei '{song_json_path}' existiert nicht.")
        sys.exit(1)

    with open(song_json_path, "r", encoding="utf-8") as f:
        try:
            song_payload = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Konnte JSON nicht parsen: {e}")
            sys.exit(1)

    if not isinstance(song_payload, dict):
        print("[ERROR] Die Song-JSON muss ein Objekt (Dictionary) sein.")
        sys.exit(1)

    # Modellname ergänzen / überschreiben
    song_payload["model"] = model_name

    # Anfrage an den Song-Generate-Endpunkt
    url = "https://api.mureka.ai/v1/song/generate"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    resp = requests.post(url, headers=headers, json=song_payload)
    if resp.status_code != 200:
        print(f"[ERROR] Song-Generierung fehlgeschlagen (Status {resp.status_code}): {resp.text}")
        sys.exit(1)

    return resp.json()

def main():
    parser = argparse.ArgumentParser(
        description="Mureka AI: Komplettes Fine-Tuning mit anschließender Song-Generierung aus JSON"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        required=True,
        help="Pfad zum Ordner mit den Audiodateien für das Fine-Tuning (bis max. 200 Files, .wav oder .mp3)."
    )
    parser.add_argument(
        "--base-model",
        type=str,
        default="V6",
        help="Name des Basis-Modells (z. B. 'V6' oder 'O1')."
    )
    parser.add_argument(
        "--suffix",
        type=str,
        required=True,
        help="Suffix für das neue Modell (max. 32 Zeichen, Kleinbuchstaben, Zahlen, Bindestriche)."
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        help="Sekundenintervall zwischen Status-Abfragen (Standard: 60 s)."
    )
    parser.add_argument(
        "--song-json",
        type=str,
        required=True,
        help="Pfad zur JSON-Datei mit Parametern für die Song-Generierung."
    )
    args = parser.parse_args()

    # API-Key aus Umgebungsvariable lesen
    api_key = os.getenv("MUREKA_API_KEY")
    if not api_key:
        print("[ERROR] Umgebungsvariable MUREKA_API_KEY nicht gesetzt.")
        sys.exit(1)

    # 1. Audiodateien sammeln
    datenpfad = os.path.abspath(args.data_dir)
    if not os.path.isdir(datenpfad):
        print(f"[ERROR] Ordner '{datenpfad}' existiert nicht.")
        sys.exit(1)

    # Unterstützte Dateiendungen: .wav, .mp3
    audio_dateien = sorted(
        glob.glob(os.path.join(datenpfad, "*.wav")) +
        glob.glob(os.path.join(datenpfad, "*.mp3"))
    )

    if not audio_dateien:
        print(f"[ERROR] Keine .wav- oder .mp3-Dateien in '{datenpfad}' gefunden.")
        sys.exit(1)

    if len(audio_dateien) > 200:
        print(f"[WARNING] Es wurden {len(audio_dateien)} Dateien gefunden. Mureka erlaubt max. 200 Files pro Job.")
        print("Bitte reduziere die Anzahl auf 200 oder weniger.")
        sys.exit(1)

    print(f"🔍 Gefundene Audiodateien ({len(audio_dateien)}):")
    for f in audio_dateien:
        print("   -", os.path.basename(f))

    # 2. Dateien hochladen und file_ids sammeln
    file_ids = []
    print("\n⬆️  Beginne mit dem Hochladen der Dateien…")
    for filepath in audio_dateien:
        file_id = upload_file(filepath, api_key)
        file_ids.append(file_id)

    # 3. Fine-Tuning-Job erstellen
    print("\n🛠️  Erstelle Fine-Tuning-Job…")
    finetune_id = create_finetune_job(file_ids, args.base_model, args.suffix, api_key)

    # 4. Auf Abschluss warten
    result_json = wait_for_finetune(finetune_id, api_key, args.poll_interval)

    # 5. Neues Modell ausgeben
    new_model = result_json.get("model")
    if not new_model:
        print("[WARN] Kein 'model'-Feld in der Antwort gefunden. Sieh dir das JSON an:")
        print(json.dumps(result_json, indent=2, ensure_ascii=False))
        sys.exit(1)

    print(f"\n🎉 Dein feingetuntes Modell heißt: '{new_model}'")

    # 6. Song-Generierung aus JSON
    print("\n🎵 Generiere jetzt einen Song mit deinem neuen Modell unter Verwendung der JSON-Daten…")
    song_response = generate_song_from_json(args.song_json, new_model, api_key)

    # 7. Ausgabe der Song-Response
    # Erwartetes Feld: "audio_url"
    audio_url = song_response.get("audio_url") or song_response.get("songs", [{}])[0].get("mp3_url")
    title = song_response.get("title") or song_response.get("songs", [{}])[0].get("title")
    song_id = song_response.get("id") or song_response.get("songs", [{}])[0].get("song_id")

    print("\n➤ Song-Generierung erfolgreich.")
    if title:
        print(f"   • Title: {title}")
    if song_id:
        print(f"   • Song-ID: {song_id}")
    if audio_url:
        print(f"   • MP3-URL: {audio_url}")
        print("     → Zum Herunterladen: curl -L \"{}\" -o \"{}.mp3\"".format(audio_url, title or song_id))
    else:
        print("[WARN] Keine 'audio_url' oder 'mp3_url' in der Antwort gefunden. Ausgabe der gesamten JSON-Antwort:")
        print(json.dumps(song_response, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
