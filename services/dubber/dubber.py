import os
import glob
import json
import logging
import subprocess
import torch
import re
from TTS.api import TTS
from pydub import AudioSegment, effects

# --- Konfiguracja ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "/app/downloads")
TEMP_DIR = "/app/temp"
MAX_SPEED_FACTOR = 1.25
TARGET_BITRATE = "192k"
TARGET_SAMPLE_RATE = 44100

def find_media_files():
    """Znajduje pasujące pliki wideo i przetłumaczone napisy."""
    video_files = glob.glob(os.path.join(DOWNLOADS_DIR, "*.mp4"))
    json_files = glob.glob(os.path.join(DOWNLOADS_DIR, "*_translated.json"))
    if not video_files or not json_files: return None, None
    return video_files[0], json_files[0]

def extract_clean_voice_sample(video_path, output_path, segments, total_duration_target=20.0):
    """
    Inteligentne próbkowanie: znajduje i łączy czyste fragmenty mowy do ~20s.
    """
    logging.info("Wyszukiwanie czystych segmentów mowy do klonowania głosu...")
    
    selected_segments = []
    current_duration = 0.0
    for segment in segments:
        text = segment.get('text', '')
        start = float(segment.get('start', 0))
        end = float(segment.get('end', 0))
        duration = end - start
        
        if text and not text.strip().startswith('[') and duration > 1.0:
            selected_segments.append(segment)
            current_duration += duration
            if current_duration >= total_duration_target:
                break
    
    if not selected_segments:
        logging.error("Nie znaleziono odpowiednich segmentów mowy do stworzenia próbki głosu.")
        return False

    logging.info(f"Wybrano {len(selected_segments)} segmentów o łącznej długości {current_duration:.2f}s do stworzenia próbki referencyjnej.")

    temp_clip_paths = []
    concat_list_path = os.path.join(TEMP_DIR, "concat_list.txt")

    try:
        with open(concat_list_path, 'w') as f:
            for i, segment in enumerate(selected_segments):
                start_time = segment['start']
                end_time = segment['end']
                temp_clip_path = os.path.join(TEMP_DIR, f"ref_clip_{i}.wav")
                
                command = [
                    'ffmpeg', '-y', '-i', video_path,
                    '-ss', str(start_time), '-to', str(end_time),
                    '-vn', '-c:a', 'pcm_s16le', '-ar', '24000', '-ac', '1',
                    temp_clip_path
                ]
                subprocess.run(command, check=True, capture_output=True, text=True)
                f.write(f"file '{os.path.basename(temp_clip_path)}'\n")
                temp_clip_paths.append(temp_clip_path)

        # Łączenie klipów w jeden plik referencyjny
        logging.info("Łączenie wyodrębnionych klipów w jeden plik referencyjny...")
        concat_command = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_list_path,
            '-c', 'copy', output_path
        ]
        subprocess.run(concat_command, check=True, capture_output=True, text=True)
        
        logging.info(f"Inteligentna próbka głosu zapisana jako {output_path}")
        return True

    except subprocess.CalledProcessError as e:
        logging.error(f"Błąd FFmpeg podczas tworzenia próbki głosu: {e.stderr}")
        return False
    finally:
        # Sprzątanie tymczasowych plików
        for path in temp_clip_paths:
            if os.path.exists(path): os.remove(path)
        if os.path.exists(concat_list_path): os.remove(concat_list_path)

def preprocess_short_text(text: str, duration: float):
    if duration < 2.0:
        fillers = ["wiesz", "tak naprawdę", "właściwie", "jakby", "po prostu"]
        for filler in fillers:
            text = re.sub(r'\b' + filler + r'\b', '', text, flags=re.IGNORECASE)
        return ' '.join(text.split())
    return text

def time_stretch_audio(input_path, output_path, speed_factor):
    command = ['ffmpeg', '-y', '-i', input_path, '-filter:a', f"atempo={speed_factor}", output_path]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Błąd FFmpeg podczas rozciągania audio: {e.stderr}")
        return False

def build_dub_track(tts, segments_json, voice_sample, total_duration_ms):
    logging.info("Budowanie finalnej ścieżki dubbingu z inteligentnym dopasowaniem...")
    final_track = AudioSegment.silent(duration=total_duration_ms, frame_rate=TARGET_SAMPLE_RATE)
    last_clip_real_end_ms = 0

    for i, segment in enumerate(segments_json):
        clip_path = os.path.join(TEMP_DIR, f"segment_{i+1}.wav")
        if not os.path.exists(clip_path):
            duration = float(segment['end']) - float(segment['start'])
            text = preprocess_short_text(segment['text'], duration)
            if not text: continue
            try:
                logging.info(f"Generowanie segmentu {i+1}/{len(segments_json)}...")
                tts.tts_to_file(text=text, speaker_wav=voice_sample, language='pl', file_path=clip_path, speed=1.0)
            except Exception as e:
                logging.error(f"Nie udało się wygenerować audio dla segmentu {i+1}: {e}")
                continue
        else:
            logging.info(f"Segment {i+1} już istnieje, pomijanie generowania.")

        if not os.path.exists(clip_path): continue

        segment_audio = AudioSegment.from_wav(clip_path)
        segment_audio = segment_audio.set_frame_rate(TARGET_SAMPLE_RATE)
        segment_audio = effects.high_pass_filter(segment_audio, 100)
        segment_audio = effects.normalize(segment_audio)
        
        target_start_ms = float(segment['start']) * 1000
        target_duration_ms = (float(segment['end']) - float(segment['start'])) * 1000
        processed_clip = segment_audio
        generated_duration_ms = len(segment_audio)
        
        if generated_duration_ms > target_duration_ms:
            speed_factor = generated_duration_ms / target_duration_ms
            if speed_factor > MAX_SPEED_FACTOR:
                speed_factor = MAX_SPEED_FACTOR
            stretched_path = os.path.join(TEMP_DIR, f"stretched_{i+1}.wav")
            if time_stretch_audio(clip_path, stretched_path, speed_factor):
                processed_clip = AudioSegment.from_wav(stretched_path)
        elif generated_duration_ms < target_duration_ms:
            padding = target_duration_ms - generated_duration_ms
            processed_clip += AudioSegment.silent(duration=padding, frame_rate=TARGET_SAMPLE_RATE)

        real_start_position_ms = max(target_start_ms, last_clip_real_end_ms)
        final_track = final_track.overlay(processed_clip, position=real_start_position_ms)
        last_clip_real_end_ms = real_start_position_ms + len(processed_clip)
        
    return final_track

def mix_and_remux_video(video_path, dub_track, output_filename="DUBBED_VIDEO_FINAL.mp4"):
    logging.info("Rozpoczynanie finalnego miksowania z duckingiem...")
    dub_track_path = os.path.join(TEMP_DIR, "dubbed_track.mp3")
    final_output_path = os.path.join(DOWNLOADS_DIR, output_filename)
    
    dub_track.export(dub_track_path, format="mp3", codec="libmp3lame", bitrate=TARGET_BITRATE)

    command = [
        'ffmpeg', '-y', '-i', video_path, '-i', dub_track_path,
        '-filter_complex', "[0:a]volume=0.1[bg];[1:a]volume=1.0[fg];[bg][fg]amix=inputs=2:duration=first[a_out]",
        '-map', '0:v:0', '-map', '[a_out]',
        '-c:v', 'copy', '-c:a', 'aac', '-shortest', final_output_path
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        logging.info(f"Finalne wideo zapisano pomyślnie jako {os.path.basename(final_output_path)}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Błąd FFmpeg podczas remiksowania: {e.stderr}")

def main():
    if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)
    
    video_path, json_path = find_media_files()
    if not (video_path and json_path):
        logging.error("Nie znaleziono wymaganych plików .mp4 lub *_translated.json.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        segments = json.load(f)
        
    voice_sample_path = os.path.join(TEMP_DIR, "reference.wav")
    if not extract_clean_voice_sample(video_path, voice_sample_path, segments):
        return

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logging.info(f"Używane urządzenie do TTS: {device}")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=(device=="cuda"))

    try:
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path], capture_output=True, text=True, check=True)
        total_duration_ms = int(float(result.stdout.strip()) * 1000)
    except Exception as e:
        logging.error(f"Nie udało się pobrać czasu trwania wideo: {e}")
        return

    dub_track = build_dub_track(tts, segments, voice_sample_path, total_duration_ms)
    
    if dub_track:
        mix_and_remux_video(video_path, dub_track)
    
    logging.info("Sprzątanie plików tymczasowych...")
    for f in glob.glob(os.path.join(TEMP_DIR, "*")): os.remove(f)
    os.rmdir(TEMP_DIR)
    
    logging.info("Proces dubbingu zakończony pomyślnie!")

if __name__ == "__main__":
    main()
