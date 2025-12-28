import os
import glob
import json
import logging
from faster_whisper import WhisperModel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
# Model size: "tiny", "base", "small", "medium", "large-v2"
# "base" is a good starting point. For CPU, smaller is faster.
MODEL_SIZE = "base"
DEVICE = "cpu"
COMPUTE_TYPE = "int8" # CPU optimization
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "/app/downloads")

def transcribe_videos():
    """
    Scans the downloads directory for .mp4 files, transcribes them,
    and saves the output as JSON files.
    """
    logging.info(f"Loading faster-whisper model '{MODEL_SIZE}' for {DEVICE}...")
    try:
        model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    except Exception as e:
        logging.error(f"Failed to load the Whisper model: {e}")
        return

    logging.info("Model loaded successfully.")
    
    video_files = glob.glob(os.path.join(DOWNLOADS_DIR, "*.mp4"))
    
    if not video_files:
        logging.warning(f"No .mp4 video files found in '{DOWNLOADS_DIR}'. Exiting.")
        return

    logging.info(f"Found {len(video_files)} video(s) to transcribe.")

    for video_path in video_files:
        try:
            logging.info(f"Starting transcription for: {os.path.basename(video_path)}")
            
            # The 'transcribe' method handles audio extraction automatically
            segments, info = model.transcribe(video_path, word_timestamps=False)

            logging.info(f"Detected language '{info.language}' with probability {info.language_probability:.2f}")

            # Prepare data for JSON output
            output_data = []
            for segment in segments:
                output_data.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text
                })

            # Save to JSON file
            base_filename = os.path.splitext(os.path.basename(video_path))[0]
            json_output_path = os.path.join(DOWNLOADS_DIR, f"{base_filename}.json")

            with open(json_output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=4, ensure_ascii=False)

            logging.info(f"Transcription saved to: {json_output_path}")

        except Exception as e:
            logging.error(f"Failed to transcribe {video_path}: {e}")

if __name__ == "__main__":
    transcribe_videos()
