import os
import glob
import json
import logging
import subprocess
import torch
from TTS.api import TTS
from pydub import AudioSegment

# --- Konfiguracja ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DOWNLOADS_DIR = "/app/downloads"
TEMP_DIR = "/app/temp"

# --- Funkcje pomocnicze ---

def find_media_files():
    """Znajduje pasujące pliki wideo (.mp4) i przetłumaczone napisy (.json)."""
    video_files = glob.glob(os.path.join(DOWNLOADS_DIR, "*.mp4"))
    json_files = glob.glob(os.path.join(DOWNLOADS_DIR, "*_translated.json"))
    
    if not video_files:
        logging.error("Nie znaleziono pliku wideo .mp4 w folderze /app/downloads.")
        return None, None
        
    if not json_files:
        logging.error("Nie znaleziono pliku JSON z tłumaczeniem (*_translated.json) w /app/downloads.")
        return None, None

    # Na razie zakładamy, że jest tylko jeden plik wideo i jedno tłumaczenie
    return video_files[0], json_files[0]

def extract_voice_sample(video_path, output_path, duration=15):
    """
    Wyodrębnia próbkę głosu z pliku wideo za pomocą FFmpeg.
    XTTSv2 wymaga audio 24kHz, mono.
    """
    logging.info(f"Wyodrębnianie {duration}-sekundowej próbki głosu z {os.path.basename(video_path)}...")
    command = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-ss', '0',
        '-t', str(duration),
        '-vn', # Ignoruj wideo
        '-c:a', 'pcm_s16le', # Nieskompresowane audio
        '-ar', '24000', # Wymagana częstotliwość próbkowania dla XTTSv2
        '-ac', '1', # Mono
        output_path
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        logging.info(f"Próbka głosu zapisana jako {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error("Błąd podczas wyodrębniania próbki głosu przez FFmpeg.")
        logging.error(f"FFmpeg stderr: {e.stderr}")
        return False

def generate_dub_segments(tts_model, segments, voice_sample_path):
    """
    Generuje pliki audio dla każdego segmentu tekstu przy użyciu klonowania głosu.
    """
    logging.info(f"Rozpoczynanie generowania {len(segments)} segmentów audio...")
    generated_files = []
    for i, segment in enumerate(segments):
        text = segment['text']
        start_time = float(segment['start'])
        end_time = float(segment['end'])
        
        if not text.strip():
            logging.warning(f"Segment {i+1} jest pusty, pomijanie.")
            continue
            
        clip_path = os.path.join(TEMP_DIR, f"segment_{i+1}.wav")
        
        try:
            logging.info(f"Generowanie segmentu {i+1}/{len(segments)}: \"{text[:50]}...\"")
            tts_model.tts_to_file(
                text=text,
                speaker_wav=voice_sample_path,
                language='pl',
                file_path=clip_path
            )
            generated_files.append((clip_path, start_time, end_time))
        except Exception as e:
            logging.error(f"Nie udało się wygenerować audio dla segmentu {i+1}: {e}")
            
    return generated_files

def align_and_merge_audio(clips, total_duration_ms):
    """
    Dostosowuje czas trwania każdego klipu i łączy je w jedną ścieżkę dźwiękową.
    """
    logging.info("Rozpoczynanie dopasowywania i łączenia segmentów audio...")
    final_track = AudioSegment.silent(duration=total_duration_ms)

    for clip_path, start_time, end_time in clips:
        target_duration_ms = (end_time - start_time) * 1000
        
        if target_duration_ms <= 0:
            logging.warning(f"Segment w {clip_path} ma nieprawidłowy czas trwania. Pomijanie.")
            continue
            
        segment_audio = AudioSegment.from_wav(clip_path)
        original_duration_ms = len(segment_audio)
        
        # Proste dopasowanie prędkości przez zmianę frame rate
        speed_ratio = original_duration_ms / target_duration_ms
        
        if speed_ratio != 1.0:
            logging.info(f"Dopasowywanie prędkości klipu {os.path.basename(clip_path)} (ratio: {speed_ratio:.2f})")
            new_frame_rate = int(segment_audio.frame_rate * speed_ratio)
            aligned_audio = segment_audio._spawn(segment_audio.raw_data, overrides={'frame_rate': new_frame_rate})
            aligned_audio = aligned_audio.set_frame_rate(segment_audio.frame_rate) # Wróć do standardowego frame rate
        else:
            aligned_audio = segment_audio
        
        # Nałóż dopasowany klip na finalną ścieżkę w odpowiednim miejscu
        final_track = final_track.overlay(aligned_audio, position=start_time * 1000)

    return final_track

def mix_and_remux(video_path, dubbed_track, output_filename):
    """
    Tłumi oryginalny głos, miksuje nową ścieżkę i remiksuje finalne wideo.
    """
    logging.info("Rozpoczynanie finalnego miksowania i remiksowania wideo...")
    
    original_audio_filtered_path = os.path.join(TEMP_DIR, "original_audio_filtered.aac")
    dubbed_track_path = os.path.join(TEMP_DIR, "dubbed_track.aac")
    final_output_path = os.path.join(DOWNLOADS_DIR, output_filename)

    # Zapisz nową ścieżkę dubbingu do pliku
    dubbed_track.export(dubbed_track_path, format="aac")

    # 1. Wyodrębnij oryginalne audio i zastosuj filtr górnoprzepustowy, aby stłumić głos
    logging.info("Tłumienie oryginalnej ścieżki wokalnej...")
    filter_command = [
        'ffmpeg', '-y',
        '-i', video_path,             # Wejście 0 (oryginalne wideo)
        '-vn', # Brak video
        '-filter_complex', "[0:a]volume=0.2, highpass=f=300,lowpass=f=3000[a_filtered]", # Tło z mniejszą głośnością i filtrem
        '-map', '[a_filtered]',
        original_audio_filtered_path
    ]
    try:
        subprocess.run(filter_command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        logging.error("Błąd podczas filtrowania oryginalnego audio przez FFmpeg.")
        logging.error(f"FFmpeg stderr: {e.stderr}")
        return False


    # 2. Zmiskuj stłumione oryginalne audio z nową ścieżką dubbingu
    #    i połącz z oryginalnym wideo
    logging.info("Miksowanie ścieżek i remiksowanie z wideo...")
    remux_command = [
        'ffmpeg', '-y',
        '-i', video_path,             # Wejście 0 (oryginalne wideo)
        '-i', dubbed_track_path,      # Wejście 1 (nowy dubbing)
        '-i', original_audio_filtered_path, # Wejście 2 (stłumione tło)
        '-filter_complex', "[1:a][2:a]amix=inputs=2:duration=first[a_out]", # Zmiskuj audio 1 i 2
        '-map', '0:v:0',              # Użyj strumienia wideo z wejścia 0
        '-map', '[a_out]',            # Użyj zmiksowanego wyjścia audio
        '-c:v', 'copy',               # Kopiuj wideo bez re-enkodowania
        '-shortest',                  # Zakończ, gdy najkrótsze wejście się skończy
        output_filename
    ]
    try:
        subprocess.run(remux_command, check=True, capture_output=True, text=True)
        logging.info(f"Finalne wideo z dubbingiem zapisano jako {output_filename}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error("Błąd podczas finalnego remiksowania przez FFmpeg.")
        logging.error(f"FFmpeg stderr: {e.stderr}")
        return False

def main():
    """Główny potok wykonawczy."""
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        
    video_path, json_path = find_media_files()
    if not video_path or not json_path:
        logging.error("Nie znaleziono wymaganych plików wideo lub tłumaczenia.")
        return
        
    voice_sample_path = os.path.join(TEMP_DIR, "reference.wav")
    if not extract_voice_sample(video_path, voice_sample_path):
        return

    # Inicjalizacja TTS
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logging.info(f"Używane urządzenie do TTS: {device}")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=(device=="cuda"))

    with open(json_path, 'r', encoding='utf-8') as f:
        segments = json.load(f)

    # Pobierz czas trwania wideo
    try:
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path], capture_output=True, text=True, check=True)
        total_video_duration = float(result.stdout.strip())
        total_duration_ms = int(total_video_duration * 1000)
    except Exception as e:
        logging.error(f"Nie udało się pobrać czasu trwania wideo: {e}")
        return


    generated_clips_info = generate_dub_segments(tts, segments, voice_sample_path)
    if not generated_clips_info:
        logging.error("Nie udało się wygenerować żadnych klipów audio. Przerywam.")
        return

    dub_track = align_and_merge_audio(generated_clips_info, total_duration_ms)
    
    if not mix_and_remux(video_path, dub_track, "DUBBED_VIDEO_FINAL.mp4"):
        logging.error("Finalny etap miksowania i remiksowania nie powiódł się.")
    
    # Sprzątanie tymczasowych plików
    logging.info("Sprzątanie plików tymczasowych...")
    for clip_path, _, _ in generated_clips_info:
        if os.path.exists(clip_path):
            os.remove(clip_path)
    if os.path.exists(voice_sample_path):
        os.remove(voice_sample_path)
    if os.path.exists(os.path.join(TEMP_DIR, "original_audio_filtered.aac")):
        os.remove(os.path.join(TEMP_DIR, "original_audio_filtered.aac"))
    if os.path.exists(os.path.join(TEMP_DIR, "dubbed_track.aac")):
        os.remove(os.path.join(TEMP_DIR, "dubbed_track.aac"))
    
    # Spróbuj usunąć katalog tymczasowy, jeśli jest pusty
    try:
        os.rmdir(TEMP_DIR)
    except OSError as e:
        logging.warning(f"Nie udało się usunąć katalogu tymczasowego {TEMP_DIR}: {e}")
    
    logging.info("Proces dubbingu zakończony pomyślnie!")

if __name__ == "__main__":
    main()
