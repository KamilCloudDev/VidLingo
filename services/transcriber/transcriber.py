import os
import glob
import json
import logging
import re
from faster_whisper import WhisperModel
from typing import Iterator, List, Dict, Any

# --- Konfiguracja ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "/app/downloads")
MODEL_SIZE = "base"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"
MAX_SEGMENT_DURATION_S = 6.0  # Dążymy do segmentów o długości 5-7 sekund
SILENCE_THRESHOLD_S = 0.75   # Przerwa w mowie, która wymusza nowy segment

def regroup_words_into_segments(segments: Iterator[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Przetwarza wyjście z faster-whisper z włączonymi znacznikami czasu na poziomie słów
    i grupuje słowa w nowe, krótsze i bardziej logiczne segmenty.
    """
    logging.info("Rozpoczynanie re-segmentacji na podstawie znaczników czasu na poziomie słów...")
    final_segments = []
    current_segment_words = []
    
    # Flatten all words from all segments into a single list
    all_words = [word for segment in segments for word in segment.words]
    if not all_words:
        return []

    for i, word in enumerate(all_words):
        # --- Filtracja segmentów bez mowy (np. [Laughter]) ---
        # Sprawdzamy, czy słowo jest w nawiasach i pomijamy je
        if word.word.strip().startswith('[') and word.word.strip().endswith(']'):
            continue

        if not current_segment_words:
            # Rozpocznij nowy segment
            current_segment_start_time = word.start
        
        current_segment_words.append(word.word)
        current_segment_end_time = word.end
        
        # Sprawdź, czy należy zakończyć bieżący segment
        is_last_word = (i == len(all_words) - 1)
        ends_with_punctuation = word.word.strip().endswith(('.', '?', '!'))
        duration_exceeded = (current_segment_end_time - current_segment_start_time) > MAX_SEGMENT_DURATION_S
        
        # Sprawdź, czy po bieżącym słowie następuje długa pauza
        long_silence_after = False
        if not is_last_word:
            next_word_start = all_words[i+1].start
            if (next_word_start - current_segment_end_time) > SILENCE_THRESHOLD_S:
                long_silence_after = True

        if is_last_word or ends_with_punctuation or duration_exceeded or long_silence_after:
            text = "".join(current_segment_words).strip()
            if text:
                new_segment = {
                    "start": round(current_segment_start_time, 3),
                    "end": round(current_segment_end_time, 3),
                    "text": text
                }
                final_segments.append(new_segment)
            
            # Zresetuj dla następnego segmentu
            current_segment_words = []

    return final_segments

def transcribe_videos():
    """
    Skanuje folder w poszukiwaniu plików wideo, transkrybuje je z precyzyjną segmentacją
    i zapisuje wyniki jako pliki JSON.
    """
    logging.info(f"Ładowanie modelu faster-whisper '{MODEL_SIZE}' dla {DEVICE}...")
    try:
        model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    except Exception as e:
        logging.error(f"Nie udało się załadować modelu Whisper: {e}")
        return
    logging.info("Model załadowany pomyślnie.")
    
    video_files = glob.glob(os.path.join(DOWNLOADS_DIR, "*.mp4"))
    if not video_files:
        logging.warning(f"Nie znaleziono plików wideo .mp4 w '{DOWNLOADS_DIR}'. Zakończono.")
        return

    logging.info(f"Znaleziono {len(video_files)} wideo do transkrypcji.")

    for video_path in video_files:
        try:
            base_filename = os.path.splitext(os.path.basename(video_path))[0]
            json_output_path = os.path.join(DOWNLOADS_DIR, f"{base_filename}.json")

            if os.path.exists(json_output_path):
                logging.info(f"Plik transkrypcji dla {os.path.basename(video_path)} już istnieje. Pomijanie.")
                continue

            logging.info(f"Rozpoczynanie transkrypcji dla: {os.path.basename(video_path)}")
            
            # --- Kluczowy krok: włączenie word_timestamps=True ---
            segments_iterator, info = model.transcribe(video_path, word_timestamps=True)
            
            logging.info(f"Wykryty język: '{info.language}' (prawdopodobieństwo: {info.language_probability:.2f})")

            # Przetwarzanie i grupowanie słów w precyzyjne segmenty
            precise_segments = regroup_words_into_segments(segments_iterator)

            # Zapisz wynik do pliku JSON
            with open(json_output_path, 'w', encoding='utf-8') as f:
                json.dump(precise_segments, f, indent=4, ensure_ascii=False)

            logging.info(f"Precyzyjna transkrypcja zapisana do: {os.path.basename(json_output_path)}")

        except Exception as e:
            logging.error(f"Nie udało się przetworzyć pliku {video_path}: {e}", exc_info=True)

if __name__ == "__main__":
    transcribe_videos()