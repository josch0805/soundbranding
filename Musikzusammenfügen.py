import librosa
import soundfile as sf
import numpy as np
import os

# Pfade anpassen
input_folder = "/proj/separated/htdemucs/Mit_Volldampf_voraus_80065887076353"
output_file = "/proj/clips/Output.mp3"

# Liste der zu ladenden Stems
stems = ["audio (3).wav", "drums.wav", "bass.wav", "other.wav"]

audio_sum = None
sr = None

for stem in stems:
    path = os.path.join(input_folder, stem)
    if not os.path.exists(path):
        print(f"Warnung: {path} nicht gefunden, wird übersprungen.")
        continue

    # Laden (mehrkanalig, falls vorhanden)
    y, sr_local = librosa.load(path, sr=44100, mono=False)

    # Immer 2D: (kanäle, samples)
    if y.ndim == 1:
        y = np.expand_dims(y, axis=0)

    if audio_sum is None:
        audio_sum = y
        sr = sr_local
    else:
        # === Kanäle angleichen ===
        if y.shape[0] != audio_sum.shape[0]:
            max_channels = max(y.shape[0], audio_sum.shape[0])
            if y.shape[0] < max_channels:
                y = np.tile(y, (max_channels, 1))[:max_channels, :]
            if audio_sum.shape[0] < max_channels:
                audio_sum = np.tile(audio_sum, (max_channels, 1))[:max_channels, :]

        # === Länge angleichen ===
        max_len = max(y.shape[1], audio_sum.shape[1])
        if y.shape[1] < max_len:
            y = np.pad(y, ((0, 0), (0, max_len - y.shape[1])))
        if audio_sum.shape[1] < max_len:
            audio_sum = np.pad(audio_sum, ((0, 0), (0, max_len - audio_sum.shape[1])))

        # Summieren
        audio_sum += y

# Ergebnis speichern, wenn etwas geladen wurde
if audio_sum is not None and sr is not None:
    # Normalisieren
    max_val = np.max(np.abs(audio_sum))
    if max_val > 0:
        audio_sum = audio_sum / max_val

    # Transponieren: (samples, channels) für speichern
    audio_sum = audio_sum.T
    sf.write(output_file, audio_sum, sr)
    print(f"Kombinierte Datei gespeichert als: {output_file}")
else:
    print("Keine Audiodateien gefunden. Es wurde nichts gespeichert.")
