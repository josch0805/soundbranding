# API.py
# This file is used to process the JSON files in the files folder and generate songs using the Mureka API.
# It is used to generate songs for the songs folder.

from __future__ import annotations

import json
import itertools
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Union
import logging
import requests

# Configure logging
logging.basicConfig(
    filename='streamlit_log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Konstante Konfiguration
# ──────────────────────────────────────────────────────────────
BASE: str = "https://api.mureka.ai/v1"
API_KEY: str = os.getenv("MUREKA_API_KEY", "op_ma3twdh4M5gm7iiN819wpZ3TrRxvvA8")
HEADERS: Dict[str, str] = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}
FILES_DIR: Path = Path("./files")
OUT_DIR: Path = Path("./output")
POLL_EVERY: int = 3  # Sekunden zwischen Status‑Abfragen
TIMEOUT: int = 120
URL_KEYS: set[str] = {
    "audio_url",
    "url",
    "mp3_url",
    "song_url",
    "oss_key",
    "download_url",
}

# Falls Upload‑IDs gebraucht werden: hier eintragen.
UPLOAD_IDS: List[str] = []


# ──────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ──────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    logger.info(msg)


def die(msg: str) -> None:  # noqa: D401 – kurz & knackig
    logger.error(f"❌ {msg}")
    sys.exit(1)


def post(route: str, body: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"Making POST request to {route}")
    resp = requests.post(
        f"{BASE}{route}", headers=HEADERS, json=body, timeout=TIMEOUT
    )
    if resp.status_code != 200:
        error_msg = f"{route} → {resp.status_code}: {resp.text[:200]}…"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    logger.info(f"Successfully completed POST request to {route}")
    return resp.json()


def complete_upload(uid: str) -> None:
    logger.info(f"Completing upload {uid}")
    post("/uploads/complete", {"upload_id": uid})
    logger.info(f"Successfully completed upload {uid}")


def generate(payload: Dict[str, Any]) -> str:
    logger.info("Generating song with payload")
    data = post("/song/generate", payload)
    tid = data.get("title") or data.get("task_id") or data.get("id")
    if not tid:
        error_msg = f"Keine task_id in Antwort: {data}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    logger.info(f"Successfully generated task with ID: {tid}")
    return tid


def poll_status(tid: str) -> Dict[str, Any]:
    url = f"{BASE}/song/query/{tid}"
    spinner = itertools.cycle("⠋⠙⠹⠸⠼⠴⠦⠧")
    logger.info(f"Starting to poll status for task {tid}")
    
    while True:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            error_msg = f"Polling‑Fehler {resp.status_code}: {resp.text[:120]}…"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        data: Dict[str, Any] = resp.json()
        status = data.get("status")
        
        if status in {"succeeded", "finished"}:
            logger.info(f"Task {tid} completed successfully")
            return data
        if status in {"failed", "rejected", "timeouted", "cancelled"}:
            error_msg = f"Job abgebrochen: {status}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        logger.debug(f"Task {tid} status: {status}")
        print(f"\r{next(spinner)}  {status:<9}", end="", flush=True)
        time.sleep(POLL_EVERY)


def find_url(obj: Union[Dict[str, Any], List[Any]]) -> str | None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in URL_KEYS and isinstance(v, str) and v.startswith("http"):
                return v
            res = find_url(v)
            if res:
                return res
    elif isinstance(obj, list):
        for item in obj:
            res = find_url(item)
            if res:
                return res
    return None


def fallback_stem(song_id: str) -> str | None:
    try:
        logger.info(f"Attempting to get fallback stem for song_id: {song_id}")
        data = post("/song/stem", {"song_id": song_id, "type": "master"})
        url = find_url(data)
        if url:
            logger.info(f"Successfully found fallback stem URL for song_id: {song_id}")
        else:
            logger.warning(f"No fallback stem URL found for song_id: {song_id}")
        return url
    except Exception as exc:
        logger.error(f"Failed to get fallback stem: {exc}")
        return None


def download(url: str, tid: str, original_data: dict) -> Path:
    logger.info(f"Starting download for task {tid}")
    resp = requests.get(url, timeout=TIMEOUT)
    if resp.status_code != 200:
        error_msg = f"Download‑Fehler {resp.status_code}: {resp.text[:120]}…"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
        
    OUT_DIR.mkdir(exist_ok=True)
    
    # Get title from original data
    title = original_data.get("Titel", "")
    logger.debug(f"Original title: '{title}'")
    
    # Fallback to Songidee if no title
    if not title or title.strip() == "":
        title = original_data.get("Songidee", f"song_{tid}")
        logger.debug(f"Using fallback title: '{title[:50] if len(title) > 50 else title}...'")
        if len(title) > 50:
            title = title[:50]
    
    # Clean title for filename
    original_title = title
    title = "".join(c for c in title if c.isalnum() or c in [' ', '-', '_']).strip()
    title = title.replace(' ', '_')
    logger.debug(f"Cleaned title: '{original_title}' -> '{title}'")
    
    # Final fallback if title is empty
    if not title:
        title = f"song_{tid}"
        logger.debug(f"Using final fallback title: '{title}'")
    
    # Combine title and task ID for filename
    fn = OUT_DIR / f"{title}_{tid}.mp3"
    fn.write_bytes(resp.content)
    logger.info(f"Successfully downloaded and saved MP3 as {fn}")
    return fn


def process_job(json_path: Union[str, Path], force_process: bool = False) -> None:
    """Process a job from a JSON file.
    
    Args:
        json_path: Path to the JSON file (can be string or Path object)
        force_process: Whether to force processing even if status doesn't match
    """
    # Convert string path to Path object if necessary
    if isinstance(json_path, str):
        json_path = Path(json_path)
    
    logger.info(f"Processing job for file: {json_path}")

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
    except ValueError as exc:
        error_msg = f"Invalid JSON: {exc}"
        logger.error(error_msg)
        data = {"Status": "fehler", "message": error_msg}
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump([data], f, ensure_ascii=False, indent=2)
        return

    if data.get("Status") != "An Mureka weitergegeben" and not force_process:
        logger.info(f"Skipping {json_path} (no pending job)")
        return

    try:
        # Create payload for Mureka API
        payload = {
            "lyrics": data.get("Lyrics", ""),
            "model": "auto",
            "prompt": data.get("Description", ""),
            "title": data.get("Titel", ""),
            #"genre": "pop",
            #"temperature": 0.8
        }
        logger.info(f"Created payload for task with title: {payload.get('title', 'No title')}")

        # Handle optional uploads
        for uid in UPLOAD_IDS:
            complete_upload(uid)

        task_id = generate(payload)
        logger.info(f"Started task {task_id}")
        task = poll_status(task_id)
        logger.info("Task completed successfully")

        url = find_url(task) or fallback_stem(task.get("song_id") or task_id)
        if not url:
            error_msg = "No download URL found"
            logger.error(f"{error_msg} - Full task object: {json.dumps(task, indent=2, ensure_ascii=False)}")
            raise RuntimeError(error_msg)

        mp3_path = download(url, task_id, data)
        logger.info(f"Successfully downloaded MP3 to {mp3_path}")

        # Update data with new information
        data.update(
            {
                "Status": "fertig",
                "task_id": task_id,
                "output_path": str(mp3_path),
                "message": "OK",
            }
        )
        logger.info("Updated job data with success status")

    except Exception as exc:
        error_msg = str(exc)
        logger.error(f"Error processing job: {error_msg}")
        data.update({"Status": "fehler", "message": error_msg})

    # Write updated data back to file
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump([data], f, ensure_ascii=False, indent=2)
    logger.info(f"Updated JSON file: {json_path}")


def watch_folder(poll_interval: int = 10) -> None:
    FILES_DIR.mkdir(exist_ok=True)
    logger.info(f"Starting batch client - watching {FILES_DIR.resolve()}")
    
    if not API_KEY:
        die("env MUREKA_API_KEY fehlt oder ist leer")

    while True:
        for json_file in FILES_DIR.glob("*.json"):
            process_job(json_file)
        time.sleep(poll_interval)


if __name__ == "__main__":
    try:
        watch_folder()
    except Exception as e:
        logger.error(f"Fatal error in main loop: {str(e)}")
        sys.exit(1)
