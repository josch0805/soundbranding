import os
import subprocess
import librosa
import numpy as np
import soundfile as sf
from pydub import AudioSegment
import warnings
import time
import sys
import traceback
import torch

# === KONFIGURATION ===
input_dir = "/proj/main_API/output"
rvc_model_path = "D_test_55.pth"
demucs_model = "htdemucs"
demucs_output_dir = "/proj/separated"
final_output_dir = "/proj/voicecloned"
webui_root = "/proj/Retrieval-based-Voice-Conversion-WebUI"
use_gpu = True

print("🔧 Konfiguration geladen:")
print(f"   Input Dir: {input_dir}")
print(f"   RVC Model: {rvc_model_path}")
print(f"   Demucs Model: {demucs_model}")
print(f"   Output Dir: {final_output_dir}")
print(f"   WebUI Root: {webui_root}")

os.makedirs(final_output_dir, exist_ok=True)
print(f"📁 Output-Verzeichnis erstellt/überprüft: {final_output_dir}")

init_path = os.path.join(webui_root, "configs", "__init__.py")
if not os.path.exists(init_path):
    with open(init_path, "w") as f:
        f.write("")
    print(f"📄 Erstellt: {init_path}")

def run_command(cmd, cwd=None, description=""):
    print(f"\n🚀 Starte: {description or 'Kommando'}")
    print("📄 Befehl:", " ".join(cmd))
    if cwd:
        print(f"📂 Arbeitsverzeichnis: {cwd}")
    
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=True, timeout=300
        )
        elapsed = time.time() - start_time
        print(f"✅ Erfolg in {elapsed:.1f}s:", result.stdout.strip() or "Keine Ausgabe.")
        if result.stderr:
            print("⚠️ STDERR:\n", result.stderr.strip())
    except subprocess.TimeoutExpired:
        print(f"⏰ Zeitüberschreitung bei: {description}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ Fehler bei {description}")
        print("📤 STDOUT:\n", e.stdout)
        print("⚠️ STDERR:\n", e.stderr)
        sys.exit(1)

def process_file(latest_file):
    try:
        print(f"\n{'='*60}")
        print(f"🎬 STARTE VERARBEITUNG: {latest_file}")
        print(f"{'='*60}")
        
        input_path = os.path.join(input_dir, latest_file)
        base_name = os.path.splitext(os.path.basename(latest_file))[0]
        temp_wav_path = os.path.join(input_dir, base_name + "_converted.wav")
        
        print(f"📄 Input Pfad: {input_path}")
        print(f"🏷️ Base Name: {base_name}")

        # === SCHRITT 1: MP3 zu WAV Konversion ===
        if latest_file.lower().endswith(".mp3"):
            print(f"\n📍 SCHRITT 1: MP3 zu WAV Konversion")
            print("🔄 Konvertiere MP3 zu WAV...")
            audio = AudioSegment.from_mp3(input_path)
            audio.export(temp_wav_path, format="wav")
            input_wav = temp_wav_path
            print(f"✅ Konvertiert zu: {input_wav}")
        else:
            print(f"\n📍 SCHRITT 1: Input bereits WAV")
            input_wav = input_path
            print(f"✅ Verwende direkt: {input_wav}")

        # === SCHRITT 2: Erste Demucs-Separation (Vocals) ===
        print(f"\n📍 SCHRITT 2: Demucs Vocals Separation")
        vocals_output_dir = os.path.join(demucs_output_dir, "vocals_only")
        print(f"📁 Vocals Output Dir: {vocals_output_dir}")
        
        demucs_vocals_cmd = [
            "demucs",
            "--two-stems=vocals",
            "-n", demucs_model,
            "-o", vocals_output_dir,
            input_wav
        ]
        run_command(demucs_vocals_cmd, description="Demucs Vocals Separation")

        # Pfade für Vocals-Separation
        if base_name.endswith("_converted"):
            sep_dir_vocals = os.path.join(vocals_output_dir, demucs_model, base_name)
        else:
            sep_dir_vocals = os.path.join(vocals_output_dir, demucs_model, base_name + "_converted")

        vocals_path = os.path.join(sep_dir_vocals, "vocals.wav")
        converted_vocals_path = os.path.join(sep_dir_vocals, "vocals_rvc.wav")
        
        print(f"📁 Vocals Verzeichnis: {sep_dir_vocals}")
        print(f"🎤 Original Vocals: {vocals_path}")
        print(f"🎤 RVC Output Pfad: {converted_vocals_path}")
        
        if not os.path.exists(vocals_path):
            raise FileNotFoundError(f"Stimme nicht gefunden: {vocals_path}")
        
        file_size = os.path.getsize(vocals_path) / (1024 * 1024)
        print(f"✅ Vocals gefunden ({file_size:.1f} MB)")

        # === SCHRITT 3: RVC Voice Cloning ===
        print(f"\n📍 SCHRITT 3: RVC Voice Cloning")
        use_gpu = torch.cuda.is_available()
        device_flag = "cuda:0" if use_gpu else "cpu"
        print(f"🔧 GPU verfügbar: {use_gpu}")
        print(f"🔧 Device: {device_flag}")
        print(f"🎭 Model: {os.path.basename(rvc_model_path)}")
        
        rvc_cmd = [
            "python3",
            "tools/infer_cli.py",
            "--model_name", os.path.basename(rvc_model_path),
            "--input_path", vocals_path,
            "--opt_path", converted_vocals_path,
            "--f0method", "rmvpe",
            "--device", device_flag,
            "--is_half", "False"
        ]
        run_command(rvc_cmd, cwd=webui_root, description="RVC Voice Cloning")

        if not os.path.exists(converted_vocals_path):
            print("❌ vocals_rvc.wav wurde nicht erzeugt!")
            sys.exit(1)
        
        cloned_size = os.path.getsize(converted_vocals_path) / (1024 * 1024)
        print(f"✅ Geklonte Vocals erstellt ({cloned_size:.1f} MB)")

        # === SCHRITT 4: Vollständige Demucs-Separation ===
        print(f"\n📍 SCHRITT 4: Demucs Full Separation (alle Stems)")
        full_output_dir = os.path.join(demucs_output_dir, "full_stems")
        print(f"📁 Full Stems Output Dir: {full_output_dir}")
        
        demucs_full_cmd = [
            "demucs",
            "-n", demucs_model,
            "-o", full_output_dir,
            input_wav
        ]
        run_command(demucs_full_cmd, description="Demucs Full Separation")

        # Pfade für Full-Separation
        if base_name.endswith("_converted"):
            sep_dir_full = os.path.join(full_output_dir, demucs_model, base_name)
        else:
            sep_dir_full = os.path.join(full_output_dir, demucs_model, base_name + "_converted")

        print(f"📁 Full Stems Verzeichnis: {sep_dir_full}")

        # === SCHRITT 5: Stem-Suche und Validierung ===
        print(f"\n📍 SCHRITT 5: Stem-Suche und Validierung")
        stem_files = {
            "vocals": converted_vocals_path,  # Use cloned vocals
            "bass": os.path.join(sep_dir_full, "bass.wav"),
            "drums": os.path.join(sep_dir_full, "drums.wav"),
            "other": os.path.join(sep_dir_full, "other.wav")
        }
        
        print(f"🔍 Suche nach 4 Stems:")
        available_stems = {}
        total_size = 0
        for name, path in stem_files.items():
            if os.path.exists(path):
                file_size = os.path.getsize(path) / (1024 * 1024)
                total_size += file_size
                available_stems[name] = path
                print(f"  ✅ {name}: {path} ({file_size:.1f} MB)")
            else:
                print(f"  ❌ {name}: {path} (nicht gefunden)")
        
        print(f"📊 Gefundene Stems: {len(available_stems)}/4 (Total: {total_size:.1f} MB)")
        
        if len(available_stems) < 2:
            print(f"❌ Zu wenige Stems gefunden! Brauche mindestens 2, habe {len(available_stems)}")
            sys.exit(1)

        # === SCHRITT 6: Audio-Kombination ===
        print(f"\n📍 SCHRITT 6: Audio-Kombination")
        
        def combine_stems_properly(file_paths, output_path):
            """Combine stems with proper level management using librosa/soundfile"""
            print(f"🎛️ Starte qualitätserhaltende Kombination von {len(file_paths)} Stems...")
            
            if not file_paths:
                return False
            
            # Load all stems as float32 for proper math
            stems_data = {}
            sample_rates = []
            min_length = float('inf')
            
            # First pass: collect all sample rates to find the highest
            for name, path in file_paths.items():
                audio, sr = librosa.load(path, sr=None, mono=False)
                sample_rates.append(sr)
            
            # Use the highest sample rate for maximum quality
            target_sample_rate = max(sample_rates)
            print(f"🔧 Verwende höchste Sample Rate: {target_sample_rate}Hz für maximale Qualität")
            
            for name, path in file_paths.items():
                print(f"📖 Lade {name}...")
                # Load with target sample rate
                audio, sr = librosa.load(path, sr=target_sample_rate, mono=False)
                
                # Ensure 2D array (channels, samples)
                if audio.ndim == 1:
                    audio = audio.reshape(1, -1)
                
                stems_data[name] = audio
                min_length = min(min_length, audio.shape[1])
                duration = audio.shape[1] / target_sample_rate
                rms = np.sqrt(np.mean(audio**2))
                print(f"   📄 {name}: {audio.shape} ({duration:.1f}s, RMS: {rms:.4f})")
            
            # Trim all to same length
            print(f"🎵 Trimme alle Stems auf {min_length} samples...")
            for name in stems_data:
                stems_data[name] = stems_data[name][:, :min_length]
            
            # Get max channels
            max_channels = max(audio.shape[0] for audio in stems_data.values())
            print(f"🔧 Verwende {max_channels} Kanäle, {target_sample_rate}Hz")
            
            # Ensure all stems have same channel count
            for name, audio in stems_data.items():
                if audio.shape[0] < max_channels:
                    # Duplicate mono to stereo if needed
                    if audio.shape[0] == 1 and max_channels == 2:
                        stems_data[name] = np.repeat(audio, 2, axis=0)
                    else:
                        # Pad with zeros for other cases
                        pad_channels = max_channels - audio.shape[0]
                        zeros = np.zeros((pad_channels, audio.shape[1]))
                        stems_data[name] = np.vstack([audio, zeros])
            
            # NO LEVEL REDUCTION - Pure 1:1 combination for maximum fidelity
            print(f"🎚️ Pure 1:1 Kombination (keine Level-Reduktion)...")
            combined = np.zeros((max_channels, min_length), dtype=np.float32)
            
            for name, audio in stems_data.items():
                # Check RMS
                rms = np.sqrt(np.mean(audio**2))
                combined += audio  # Pure addition, no scaling
                print(f"   🎚️ {name}: RMS {rms:.4f} (keine Reduktion)")
            
            # Only normalize if absolutely necessary (peak > 0.995)
            max_val = np.max(np.abs(combined))
            if max_val > 0.995:  # Only if really hitting the ceiling
                normalize_factor = 0.99 / max_val
                combined *= normalize_factor
                print(f"🔧 Minimal-Normalisierung: Faktor {normalize_factor:.4f} (Max war {max_val:.4f})")
            else:
                print(f"✅ Keine Normalisierung nötig (Max: {max_val:.4f})")
            
            # Final RMS check
            final_rms = np.sqrt(np.mean(combined**2))
            print(f"📊 Finale RMS: {final_rms:.4f}")
            
            # Save with float32 for maximum quality preservation
            print(f"💾 Speichere mit 32-bit float Präzision...")
            
            # Transpose for soundfile (samples, channels)
            if combined.shape[0] > 1:
                combined_for_save = combined.T
            else:
                combined_for_save = combined[0]  # Mono
            
            sf.write(output_path, combined_for_save, target_sample_rate, subtype='FLOAT')
            
            final_size = os.path.getsize(output_path) / (1024 * 1024)
            print(f"✅ Hochqualität-Kombination abgeschlossen ({final_size:.1f} MB)")
            return True

        # --- Kombiniere alle verfügbaren Stems ---
        output_wav_path = os.path.join(final_output_dir, base_name + "_cloned.wav")
        print(f"🎯 Ziel-Datei: {output_wav_path}")
        
        success = combine_stems_properly(available_stems, output_wav_path)
        
        if success:
            print(f"🎼 WAV-Datei gespeichert: {output_wav_path}")
        else:
            print("❌ Fehler beim Kombinieren der Stems!")
            sys.exit(1)

        # === SCHRITT 7: MP3 Export ===
        print(f"\n📍 SCHRITT 7: MP3 Export")
        mp3_path = os.path.join(final_output_dir, base_name + "_cloned.mp3")
        print(f"🎯 MP3 Ziel: {mp3_path}")
        
        print("🔄 Konvertiere WAV zu MP3...")
        audio = AudioSegment.from_wav(output_wav_path)
        audio.export(mp3_path, format="mp3", bitrate="320k")
        
        mp3_size = os.path.getsize(mp3_path) / (1024 * 1024)
        print(f"✅ MP3 exportiert: {mp3_path} ({mp3_size:.1f} MB)")

        # === SCHRITT 8: Aufräumen ===
        print(f"\n📍 SCHRITT 8: Aufräumen")
        cleanup_count = 0
        
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
            print(f"🗑️ Gelöscht: {temp_wav_path}")
            cleanup_count += 1
            
        if os.path.exists(output_wav_path):
            os.remove(output_wav_path)
            print(f"🗑️ Gelöscht: {output_wav_path}")
            cleanup_count += 1
        
        print(f"✅ Aufräumen abgeschlossen ({cleanup_count} Dateien gelöscht)")
        
        print(f"\n🎉 VERARBEITUNG ERFOLGREICH ABGESCHLOSSEN!")
        print(f"📁 Finales Ergebnis: {mp3_path}")
        print(f"{'='*60}")

    except Exception as e:
        print(f"\n💥 FEHLER in process_file:")
        print(f"❌ Fehler: {e}")
        print(f"📍 Traceback:")
        traceback.print_exc()
        print(f"{'='*60}")

print(f"🕵️‍♂️ Starte Überwachung von: {input_dir}")
print(f"⏱️ Überprüfung alle 3 Sekunden...")

already_seen = set(os.listdir(input_dir))
print(f"📋 Bereits vorhandene Dateien: {len(already_seen)}")

while True:
    current_files = set(os.listdir(input_dir))
    new_files = [
        f for f in current_files - already_seen
        if f.lower().endswith((".mp3", ".wav"))
    ]
    
    if new_files:
        print(f"\n🔔 {len(new_files)} neue Dateien erkannt!")
        
    for new_file in sorted(new_files):
        print(f"\n🎵 Neue Datei erkannt: {new_file}")
        process_time = time.time()
        process_file(new_file)
        elapsed = time.time() - process_time
        print(f"⏱️ Gesamte Verarbeitungszeit: {elapsed:.1f} Sekunden")
        
    already_seen = current_files
    time.sleep(3)