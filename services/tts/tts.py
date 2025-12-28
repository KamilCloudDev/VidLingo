import os
import glob
import json
import logging
import asyncio
import edge_tts
from pydub import AudioSegment, effects
import subprocess

# --- Konfiguracja ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "/app/downloads")
TEMP_DIR = "/app/temp/tts_outputs"
TARGET_LANG = os.getenv("TARGET_LANGUAGE", "Polish")
TARGET_BITRATE = "192k"
TARGET_SAMPLE_RATE = 44100

# --- Logika Wyboru Głosu ---
async def find_voice_for_language(lang: str) -> str:
    """Znajduje odpowiedni męski głos 'Neural' dla danego języka."""
    lang_prefix = lang.split('-')[0].lower()
    voices = await edge_tts.list_voices()
    
    # Preferuj męski głos neural
    for voice in voices:
        if voice['Gender'] == 'Male' and voice['Locale'].lower().startswith(lang_prefix) and 'Neural' in voice['Name']:
            logging.info(f"Znaleziono głos '{voice['ShortName']}' dla języka '{lang}'.")
            return voice['ShortName']
    
    # Fallback na jakikolwiek głos dla danego języka
    for voice in voices:
        if voice['Locale'].lower().startswith(lang_prefix):
            logging.warning(f"Nie znaleziono męskiego głosu Neural. Używam '{voice['ShortName']}' jako fallback dla '{lang}'.")
            return voice['ShortName']
            
    # Ostateczny fallback na domyślny głos angielski
    default_voice = 'en-US-ChristopherNeural'
    logging.error(f"Nie znaleziono żadnego głosu dla języka '{lang}'. Używam domyślnego: {default_voice}")
    return default_voice

async def get_voice_for_tts() -> str:
    """Zwraca predefiniowany głos dla TARGET_LANGUAGE lub wyszukuje odpowiedni."""
    # Priorytet dla konkretnych głosów
    if TARGET_LANG == "Polish":
        # Sprawdzamy dostępność Marka, jeśli nie ma, używamy Zofii
        voices = await edge_tts.list_voices()
        for v in voices:
            if v['ShortName'] == 'pl-PL-MarekNeural':
                logging.info("Używam głosu pl-PL-MarekNeural.")
                return 'pl-PL-MarekNeural'
        logging.warning("Głos 'pl-PL-MarekNeural' nie jest dostępny. Szukam alternatywnego głosu polskiego.")
        for v in voices:
            if v['Locale'] == 'pl-PL' and 'Neural' in v['Name']:
                 logging.info(f"Używam głosu {v['ShortName']} jako alternatywy dla polskiego.")
                 return v['ShortName']
        logging.error("Nie znaleziono żadnego polskiego głosu. Używam fallbacku.")
        return await find_voice_for_language(TARGET_LANG) # Fallback ogólny
        
    elif TARGET_LANG == "English":
        return "en-US-ChristopherNeural"
    
    # Dla innych języków szukaj
    return await find_voice_for_language(TARGET_LANG)

async def generate_segment_audio(text: str, voice: str, output_path: str):
    """Generuje pojedynczy segment audio .mp3."""
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        logging.info(f"Zapisano segment: {os.path.basename(output_path)}")
    except Exception as e:
        logging.error(f"Błąd podczas generowania segmentu dla tekstu '{text[:30]}...': {e}")

def build_dub_track(generated_files, total_duration_ms):
    """Składa finalną ścieżkę dubbingu z wygenerowanych segmentów."""
    logging.info("Budowanie finalnej ścieżki dubbingu na osi czasu...")
    final_track = AudioSegment.silent(duration=total_duration_ms, frame_rate=TARGET_SAMPLE_RATE)

    for clip_info in generated_files:
        try:
            segment_audio = AudioSegment.from_mp3(clip_info["audio_path"])
            segment_audio = segment_audio.set_frame_rate(TARGET_SAMPLE_RATE)
            segment_audio = effects.normalize(segment_audio) # Dodano normalizację
            
            final_track = final_track.overlay(segment_audio, position=clip_info["start"] * 1000)
        except Exception as e:
            logging.error(f"Nie udało się przetworzyć klipu {clip_info['audio_path']}: {e}")
            
    return final_track

def mix_and_remux_video(video_path, dub_track, output_filename="DUBBED_VIDEO_FINAL.mp4"):
    """Implementuje "ducking" audio i miksuje finalną ścieżkę z wideo."""
    logging.info("Rozpoczynanie finalnego miksowania z duckingiem...")
    dub_track_path = os.path.join(TEMP_DIR, "dubbed_track.mp3")
    final_output_path = os.path.join(DOWNLOADS_DIR, output_filename)
    
    dub_track.export(dub_track_path, format="mp3", codec="libmp3lame", bitrate=TARGET_BITRATE)

    command = [
        'ffmpeg', '-y', '-i', video_path, '-i', dub_track_path,
        '-filter_complex', "[0:a]volume=0.1[bg];[bg][1:a]amix=inputs=2:duration=first[a_out]",
        '-map', '0:v:0', '-map', '[a_out]',
        '-c:v', 'copy', '-c:a', 'aac', '-shortest', final_output_path
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        logging.info(f"Finalne wideo z dubbingiem zapisano pomyślnie jako {output_filename}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Błąd FFmpeg podczas remiksowania: {e.stderr}")

async def main():
    if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)
    
    json_files = glob.glob(os.path.join(DOWNLOADS_DIR, "*_translated.json"))
    video_files = glob.glob(os.path.join(DOWNLOADS_DIR, "*.mp4"))

    unprocessed_videos = [v for v in video_files if "DUBBED" not in v]
    if not unprocessed_videos or not json_files:
        logging.warning("Nie znaleziono pasujących plików wideo i/lub tłumaczenia (*_translated.json).")
        return
        
    video_path = unprocessed_videos[0]
    json_path = json_files[0]
    logging.info(f"Znaleziono wideo: {os.path.basename(video_path)} i tłumaczenie: {os.path.basename(json_path)}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        segments = json.load(f)

    voice = await get_voice_for_tts()
    
    tasks = []
    generated_files_metadata = []
    for i, segment in enumerate(segments):
        text = segment.get('text', '').strip()
        if not text: continue
        
        output_path = os.path.join(TEMP_DIR, f"segment_{i+1}.mp3")
        
        # Logika wznawiania: jeśli plik już istnieje, pomijamy generowanie audio
        if os.path.exists(output_path):
            logging.info(f"Segment {i+1} audio już istnieje. Pomijanie generowania.")
        else:
            tasks.append(generate_segment_audio(text, voice, output_path))

        generated_files_metadata.append({"audio_path": output_path, "start": segment.get('start'), "end": segment.get('end')})

    logging.info(f"Rozpoczynanie generowania {len(tasks)} segmentów audio z Microsoft Edge TTS...")
    if tasks: # Uruchamiaj tylko, jeśli są zadania do wykonania
        await asyncio.gather(*tasks)
    else:
        logging.info("Wszystkie segmenty audio już istniały. Pomijam generowanie.")
    logging.info("Generowanie audio zakończone.")

    # Oblicz całkowity czas trwania
    try:
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path], capture_output=True, text=True, check=True)
        total_duration_s = float(result.stdout.strip())
        total_duration_ms = int(total_duration_s * 1000)
    except Exception as e:
        logging.error(f"Nie udało się pobrać czasu trwania wideo: {e}")
        return

    dub_track = build_dub_track(generated_files_metadata, total_duration_ms)
    
    if dub_track:
        mix_and_remux_video(video_path, dub_track)
    
    logging.info("Sprzątanie plików tymczasowych...")
    for f in glob.glob(os.path.join(TEMP_DIR, "*")): os.remove(f)
    os.rmdir(TEMP_DIR)
    
    logging.info("Cały proces dubbingu zakończony!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"Wystąpił krytyczny błąd w głównym wykonaniu: {e}")
