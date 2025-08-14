#!/usr/bin/env python3
"""
Robuster Mureka-Client
- optional: /uploads/complete für IDs in UPLOAD_IDS
- /song/generate  ➜  /song/query/<task_id>
- findet Audio-URL rekursiv ODER via POST /song/stem
- lädt finale MP3 nach ./output/

env:
  export MUREKA_API_KEY="op_ma3twdh4M5gm7iiN819wpZ3TrRxvvA8"
"""

from __future__ import annotations
import os, sys, time, json, requests, itertools
from pathlib import Path
from typing import Any, Dict, List, Union

# ---------------------------------------------------------------------------
UPLOAD_IDS: List[str] = []                 # z.B. ["1436211"]
PAYLOAD: Dict[str, Any] = {
    "lyrics": (
        "[Verse]\n"
        "In the stormy night, I wander alone\n"
        "Lost in the rain, feeling like I have been thrown\n"
        "Memories of you, they flash before my eyes\n"
        "Hoping for a moment, just to find some bliss"
    ),
    "model": "auto",
    "prompt": "r&b, slow, passionate, male vocal",
}
# ---------------------------------------------------------------------------
BASE       = "https://api.mureka.ai/v1"
API_KEY    = "op_ma3twdh4M5gm7iiN819wpZ3TrRxvvA8"
HEADERS    = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
OUT_DIR    = Path("./output")
POLL_EVERY = 3
TIMEOUT    = 120
# ---------------------------------------------------------------------------


def die(msg: str) -> None:
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


def post(route: str, body: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(f"{BASE}{route}", headers=HEADERS, json=body, timeout=TIMEOUT)
    if r.status_code != 200:
        die(f"{route} → {r.status_code}: {r.text[:200]}…")
    return r.json()


def complete_upload(uid: str) -> None:
    print(f"↪️  complete upload {uid} …", end=" ")
    post("/uploads/complete", {"upload_id": uid})
    print("done")


def generate() -> str:
    data = post("/song/generate", PAYLOAD)
    tid = data.get("id") or data.get("task_id")
    if not tid:
        die(f"Kein task_id: {data}")
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


# -- Helper ------------------------------------------------------------------
URL_KEYS = {"audio_url", "url", "mp3_url", "song_url", "oss_key", "download_url"}


def find_url(obj: Union[Dict[str, Any], List[Any]]) -> str | None:
    """rekursive Suche nach einem URL-Feld"""
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


# -- Main --------------------------------------------------------------------
def main() -> None:
    if not API_KEY:
        die("env MUREKA_API_KEY fehlt")

    for uid in UPLOAD_IDS:
        complete_upload(uid)

    task_id = generate()
    print(f"🎬 task {task_id} gestartet")

    task = poll(task_id)
    print("✅  fertig")

    url = find_url(task)
    if not url:
        song_id = task.get("song_id") or task_id
        print("ℹ️  keine URL im Task – versuche /song/stem …")
        url = fallback_stem(song_id)

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
