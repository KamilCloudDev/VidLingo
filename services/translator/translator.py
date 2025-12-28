import os
import glob
import json
import logging
import re
from google import genai

# --- Konfiguracja ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "/app/downloads")
MODEL_ID = 'gemini-2.5-flash'
TARGET_LANG = os.getenv("TARGET_LANGUAGE", "Polish")

# --- Konfiguracja Klienta Google Gemini ---
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Krytyczny błąd: Klucz API GEMINI_API_KEY nie został znaleziony w pliku .env.")
    
    client = genai.Client(api_key=api_key)
    logging.info(f"Pomyślnie skonfigurowano klienta Google Gemini. Model: '{MODEL_ID}'. Język docelowy: {TARGET_LANG}")

except Exception as e:
    logging.critical(f"Krytyczny błąd podczas konfiguracji klienta Gemini: {e}")
    client = None

# --- Uniwersalna Instrukcja Systemowa dla Izosynchronicznego Dubbingu ---
SYSTEM_INSTRUCTION = f"""
Role: Act as a Senior Global Localization Lead and Audiovisual Scriptwriter. You specialize in adapting video content for international dubbing, ensuring perfect lip-sync, cultural relevance, and technical compatibility with TTS (Text-to-Speech) engines.

Target Language: [INSERT TARGET LANGUAGE HERE, e.g., Polish, English, Spanish]

Instructions: You will receive a JSON file with "start", "end", and "text" keys. You must transform this content into a professional dubbing script.

1. Holistic Context & Cultural Adaptation
Full-Script Review: Analyze the entire JSON before translating. Detect the source language, tone, and narrative arc.

Pun & Joke Preservation: Identify setups and punchlines (e.g., jokes about balloons/inflation). Adapt them so the humor works naturally in the Target Language. Never leave punchlines blank.

Narrative Continuity: Maintain consistent terminology and forms of address (formal/informal) across all segments.

2. Strict Text Normalization for TTS (Phonetic Precision)
NO DIGITS: You MUST verbalize every number, year, and date into full-word phonetic equivalents in the Target Language.

Example (EN->PL): "2009" -> "dwutysięczny dziewiąty".

Example (PL->EN): "2009" -> "two thousand and nine".

Symbols & Units: Convert all symbols ($, %, @) and abbreviations (Dr., AI, e.g.) into their full spoken forms.

Grammatical Declension: Ensure all verbalized numbers are grammatically declined correctly according to the context of the sentence in the Target Language.

3. Intelligent Isochronic Timing (Dynamic Length Control)
Calculate Linguistic Density: - From Compact to Long (e.g., EN -> PL/DE): Polish/German can be 20% longer. You MUST condense the translation using shorter synonyms and concise phrasing to ensure it fits the original time slot.

From Long to Compact (e.g., PL -> EN): English is often shorter. You MUST naturally expand or pad the text (using descriptive adjectives or filler words like "well," "actually") so the speech covers approximately 90% of the available time.

The Speed-Up Rule: The goal is to avoid both "chipmunk" speed (too much text) and long awkward silences (too little text). The voice must sound natural and steady.

4. Dubbing Aesthetics
Write for the Ear: Use spoken-word syntax. Avoid robotic or literal translations that sound stiff when read aloud.

Sync-Ready Phrasing: If possible, match the "energy" of the original segment. If a segment is a short exclamation, keep the translation short.

5. Technical Requirements
Return ONLY a valid JSON array of objects.

Keep the EXACT "start" and "end" timestamps from the input.

Use UTF-8 encoding for all special characters.

Output should be raw JSON code, no conversational filler or markdown markers."""

def clean_and_extract_json(response_text: str) -> str:
    """
    Solidny "cleaner", który usuwa bloki Markdown (` ```json...``` `) i inne "ozdobniki" AI.
    """
    match = re.search(r'```json\s*(\[.*\])\s*```', response_text, re.DOTALL)
    if match:
        logging.info("Wykryto i usunięto bloki Markdown z odpowiedzi JSON.")
        return match.group(1)
    
    match = re.search(r'\[.*\]', response_text, re.DOTALL)
    if match:
        logging.info("Znaleziono surowy blok JSON w odpowiedzi.")
        return match.group(0)

    logging.error("Odpowiedź modelu nie zawiera prawidłowego bloku JSON (tablicy).")
    raise json.JSONDecodeError("Nie znaleziono prawidłowego JSON w odpowiedzi.", response_text, 0)

def translate_json_files():
    """
    Skanuje pliki JSON, wysyła je do Gemini API do tłumaczenia i zapisuje wyniki.
    """
    if not client:
        logging.error("Klient Gemini nie jest dostępny. Zakończono działanie.")
        return

    files_to_translate = [f for f in glob.glob(os.path.join(DOWNLOADS_DIR, "*.json")) if not f.endswith('_translated.json')] 
    
    if not files_to_translate:
        logging.warning(f"Nie znaleziono plików JSON do tłumaczenia w '{DOWNLOADS_DIR}'.")
        return

    logging.info(f"Znaleziono {len(files_to_translate)} plików do przetłumaczenia.")

    for file_path in files_to_translate:
        try:
            logging.info(f"Przetwarzanie pliku: {os.path.basename(file_path)}")
            with open(file_path, 'r', encoding='utf-8') as f:
                json_content = json.load(f)

            prompt = f"{SYSTEM_INSTRUCTION}\n\nTranslate the following JSON data to {TARGET_LANG}:\n{json.dumps(json_content, ensure_ascii=False)}"
            
            logging.info(f"Wysyłanie zapytania do modelu '{MODEL_ID}'...")
            response = client.models.generate_content(model=MODEL_ID, contents=prompt)

            logging.info("Otrzymano odpowiedź od Gemini API. Uruchamianie cleanera...")
            
            cleaned_json_str = clean_and_extract_json(response.text)
            translated_data = json.loads(cleaned_json_str)

            output_path = file_path.replace(".json", "_translated.json")

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(translated_data, f, indent=4, ensure_ascii=False)

            logging.info(f"Uniwersalny skrypt dubbingowy zapisano pomyślnie do: {os.path.basename(output_path)}")

        except Exception as e:
            logging.error(f"Nie udało się przetworzyć pliku {file_path}: {e}", exc_info=True)

if __name__ == "__main__":
    translate_json_files()