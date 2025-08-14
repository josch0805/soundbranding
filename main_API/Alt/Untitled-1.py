#!/usr/bin/env python3
"""
Robuster Mureka-Client (JSON-Input, fester Pfad)
-----------------------------------------------
• liest Song-Beschreibung aus /projekt/MusicAI/Songideen.json
  (kann per -f/--file überschrieben werden)
• optional: /uploads/complete (IDs in UPLOAD_IDS unten eintragen)
• /song/generate  ➜  /song/query/<task_id>
• findet Audio-URL rekursiv oder via /song/stem
• lädt MP3 nach ./output/<task_id>.mp3
"""

from __future__ import annotations
import os, sys, time, json, argparse, itertools, requests
from pathlib import Path
from typing import Any, Dict, List, Union

# ---------------------------------------------------------------------------
UPLOAD_IDS: List[str] = []                 # z. B. ["1436211"]
# ---------------------------------------------------------------------------

BASE        = "https://api.mureka.ai/v1"
API_KEY     = "op_ma3twdh4M5gm7iiN819wpZ3TrRxvvA8"
HEADERS     = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
OUT_DIR     = Path("./output")
POLL_EVERY  = 3
TIMEOUT     = 120
URL_KEYS    = {"audio_url", "url", "mp3_url", "song_url", "oss_key", "download_url"}
DEFAULT_JSON = Path("/projekt/MusicAI/Songideen.json")
# ---------------------------------------------------------------------------


def die(msg: str) -> None:
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


def load_payload(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        die(f"JSON-Datei {path} nicht gefunden.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        die(f"{path}: Ungültiges JSON – {exc}")
    if "lyrics" not in data:
        die(f"{path}: Feld 'lyrics' fehlt.")
    return data


def post(route: str, body: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(f"{BASE}{route}", headers=HEADERS, json=body, timeout=TIMEOUT)
    if r.status_code != 200:
        die(f"{route} → {r.status_code}: {r.text[:200]}…")
    return r.json()


def complete_upload(uid: str) -> None:
    print(f"↪️  complete upload {uid} …", end=" ")
    post("/uploads/complete", {"upload_id": uid})
    print("done")


def generate(payload: Dict[str, Any]) -> str:
    data = post("/song/generate", payload)
    tid = data.get("id") or data.get("task_id")
    if not tid:
        die(f"Keine task_id in Antwort: {data}")
    return tid


def poll(tid: str) -> Dict[str, Any]:
    url = f"{BASE}/song/query/{tid}"
    spin = itertools.cycle("⠋⠙⠹⠸⠼⠴⠦⠧")
    while True:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            die(f"Polling-Fehler {r.status_code}: {r.text[:120]}…")
        data = r.json()
        status = data.get("status")
        if status in {"succeeded", "finished"}:
            return data
        if status in {"failed", "rejected", "timeouted", "cancelled"}:
            die(f"Job abgebrochen: {status}")
        print(f"\r{next(spin)}  {status:<9}", end="", flush=True)
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
        data = post("/song/stem", {"song_id": song_id, "type": "master"})
        return find_url(data)
    except Exception as exc:
        print(f"⚠️  /song/stem fehlgeschlagen: {exc}")
        return None


def download(url: str, tid: str) -> None:
    r = requests.get(url, timeout=TIMEOUT)
    if r.status_code != 200:
        die(f"Download-Fehler {r.status_code}: {r.text[:120]}…")
    OUT_DIR.mkdir(exist_ok=True)
    fn = OUT_DIR / f"{tid}.mp3"
    fn.write_bytes(r.content)
    print(f"\n💾  MP3 gespeichert als {fn}")


def main() -> None:
    if not API_KEY:
        die("env MUREKA_API_KEY fehlt")

    parser = argparse.ArgumentParser(description="Generate Mureka song from JSON")
    parser.add_argument(
        "-f", "--file", default=str(DEFAULT_JSON),
        help=f"Pfad zur JSON-Datei (Default: {DEFAULT_JSON})"
    )
    args = parser.parse_args()
    payload = load_payload(Path(args.file))

    for uid in UPLOAD_IDS:
        complete_upload(uid)

    task_id = generate(payload)
    print(f"🎬 task {task_id} gestartet")

    task = poll(task_id)
    print("✅  fertig")

    url = find_url(task) or fallback_stem(task.get("song_id") or task_id)
    if url:
        download(url, task_id)
    else:
        die(
            "Keine Download-URL gefunden – vollständiges Task-Objekt folgt:\n"
            + json.dumps(task, indent=2, ensure_ascii=False)
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⛔️  Abbruch.")
