import os
import subprocess

# === KONFIGURATION ===

# Eingabedatei mit Originalstimme (WAV, mono, 22050Hz empfohlen)
input_wav = "input/input_voice.wav"

# Ausgabepfad
output_wav = "output/converted_output.wav"

# Modellpfade
rvc_model = "weights/deine_stimme.pth"
index_file = "logs/index/deine_stimme.index"  # optional

# Weitere Parameter
pitch = 0                      # 0 = Originalhöhe beibehalten
index_rate = 0.75              # Wie stark das Index verwendet wird (0.0 - 1.0)
device = "cpu"                 # "cuda" für GPU, "cpu" sonst

# === FUNKTION ZUM AUSFÜHREN DER KONVERTIERUNG ===
def run_rvc_conversion():
    print("🔁 Starte RVC Konvertierung ...")

    command = [
        "python", "infer_cli.py",
        "--model_path", rvc_model,
        "--input_path", input_wav,
        "--output_path", output_wav,
        "--f0method", "pm",
        "--index_path", index_file,
        "--index_rate", str(index_rate),
        "--device", device,
        "--pitch", str(pitch)
    ]

    subprocess.run(command)

    if os.path.exists(output_wav):
        print(f"✅ Fertig! Umgewandelte Datei gespeichert unter: {output_wav}")
    else:
        print("❌ Fehler: Datei wurde nicht erzeugt. Prüfe Pfade und Modell.")

# === AUSFÜHRUNG ===
if __name__ == "__main__":
    run_rvc_conversion()
