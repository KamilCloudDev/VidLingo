import os
import glob
import json
import logging
import asyncio
import edge_tts
from pydub import AudioSegment, effects
import subprocess
import shutil

# --- Konfiguracja ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "/app/downloads")
TEMP_DIR = "/app/temp/tts_outputs"
TARGET_LANG = os.getenv("TARGET_LANGUAGE", "Polish")
TARGET_BITRATE = "192k"
TARGET_SAMPLE_RATE = 44100
SUPPORTED_EXTENSIONS = [".mp4", ".mkv", ".webm", ".mov", ".avi", ".flv"]

# LIMIT JEDNOCZESNYCH POŁĄCZEŃ (zapobiega blokadzie Rate Limit)
MAX_CONCURRENT_REQUESTS = 3
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

async def find_voice_for_language(lang_name: str) -> str:
    lang_map = {
        "Polish": "pl", "English": "en", "German": "de", 
        "Spanish": "es", "French": "fr", "Italian": "it"
    }
    lang_code = lang_map.get(lang_name, "en")
    
    voices = await edge_tts.list_voices()
    for voice in voices:
        if voice['Gender'] == 'Male' and voice['Locale'].lower().startswith(lang_code) and 'Neural' in voice['Name']:
            logging.info(f"Wybrano głos: {voice['ShortName']}")
            return voice['ShortName']
    return "en-US-ChristopherNeural"

async def generate_segment_audio(text: str, voice: str, output_path: str, retries=5):
    """Generuje audio z semaforem, walidacją rozmiaru i powtórkami."""
    if not text.strip() or text.strip() in [".", "..", "..."]:
        # Tworzy sekundę ciszy dla samych kropek/pustych tekstów
        AudioSegment.silent(duration=1000).export(output_path, format="mp3")
        return

    async with semaphore:
        for attempt in range(retries):
            try:
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(output_path)
                
                # Walidacja: plik musi istnieć i mieć sensowny rozmiar
                if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                    return # Sukces
                
                logging.warning(f"Pusty plik (próba {attempt+1}/{retries}) dla: {text[:15]}...")
            except Exception as e:
                logging.error(f"Błąd (próba {attempt+1}/{retries}) dla: {text[:15]}... -> {e}")
            
            await asyncio.sleep(2 * (attempt + 1)) # Coraz dłuższy czas oczekiwania

        # Jeśli po wszystkich próbach zawiedzie - stwórz ciszę zamiast błędu
        logging.error(f"Ostateczna porażka TTS dla: {text[:20]}. Generowanie ciszy.")
        AudioSegment.silent(duration=1000).export(output_path, format="mp3")

def build_dub_track(generated_files, total_duration_ms):
    logging.info(f"Składanie ścieżki: {len(generated_files)} segmentów.")
    final_track = AudioSegment.silent(duration=total_duration_ms, frame_rate=TARGET_SAMPLE_RATE)
    
    for i, clip in enumerate(generated_files):
        if i % 50 == 0: logging.info(f"Montaż: {i}/{len(generated_files)}")
        
        path = clip["audio_path"]
        if os.path.exists(path) and os.path.getsize(path) > 0:
            try:
                seg = AudioSegment.from_mp3(path).set_frame_rate(TARGET_SAMPLE_RATE)
                seg = effects.normalize(seg)
                final_track = final_track.overlay(seg, position=int(clip["start"] * 1000))
            except Exception as e:
                logging.error(f"Nie można wczytać klipu {path}: {e}")
                
    return final_track

async def main():
    if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR, exist_ok=True)
    
    json_files = glob.glob(os.path.join(DOWNLOADS_DIR, "*_translated.json"))
    if not json_files:
        logging.error("Brak plików *_translated.json")
        return

    for json_path in json_files:
        base_name = os.path.basename(json_path).replace('_translated.json', '')
        video_path = next((os.path.join(DOWNLOADS_DIR, base_name + ext) 
                          for ext in SUPPORTED_EXTENSIONS 
                          if os.path.exists(os.path.join(DOWNLOADS_DIR, base_name + ext))), None)
        
        if not video_path:
            logging.error(f"Pominięto: brak wideo dla {base_name}")
            continue

        logging.info(f"START PROCESU: {os.path.basename(video_path)}")
        with open(json_path, 'r', encoding='utf-8') as f:
            segments = json.load(f)

        voice = await find_voice_for_language(TARGET_LANG)
        tasks = []
        metadata = []

        for i, seg in enumerate(segments):
            txt = seg.get('text', '').strip()
            out_p = os.path.join(TEMP_DIR, f"seg_{i}.mp3")
            metadata.append({"audio_path": out_p, "start": seg.get('start', 0)})
            tasks.append(generate_segment_audio(txt, voice, out_p))

        # Uruchamiamy zadania (semafor wewnątrz zadba o kolejkowanie)
        await asyncio.gather(*tasks)

        # Pobranie czasu trwania
        res = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path], capture_output=True, text=True)
        dur_ms = int(float(res.stdout.strip()) * 1000)
        
        dub_track = build_dub_track(metadata, dur_ms)
        
        # Export
        output_name = base_name + "_FINAL_DUB.mp4"
        dub_track_tmp = os.path.join(TEMP_DIR, "temp_dub.mp3")
        dub_track.export(dub_track_tmp, format="mp3", bitrate=TARGET_BITRATE)
        
        final_cmd = [
            'ffmpeg', '-y', '-i', video_path, '-i', dub_track_tmp,
            '-filter_complex', "[0:a]volume=0.30[bg];[bg][1:a]amix=inputs=2:duration=first:dropout_transition=0[a_out]",
            '-map', '0:v:0', '-map', '[a_out]', '-c:v', 'copy', '-c:a', 'aac', '-preset', 'superfast',
            os.path.join(DOWNLOADS_DIR, output_name)
        ]
        
        logging.info(f"Renderowanie finalnego pliku: {output_name}")
        subprocess.run(final_cmd)
        logging.info(f"SUKCES: {output_name}")

    # shutil.rmtree(TEMP_DIR) # Odkomentuj, jeśli chcesz czyścić po sobie

if __name__ == "__main__":
    asyncio.run(main())