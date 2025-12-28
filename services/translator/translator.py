import os
import glob
import json
import logging
import re
from google import genai

# --- Konfiguracja ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "/app/downloads")
MODEL_ID = 'gemini-2.5-flash' # Zmieniono model na gemini-2.5-flash zgodnie z instrukcją
TARGET_LANG = os.getenv("TARGET_LANGUAGE", "Polish") # Dynamiczny język docelowy

def list_available_models():
    """Listuje wszystkie dostępne modele Gemini dla danego klucza API."""
    try:
        logging.info("--- Dostępne Modele Gemini ---")
        for m in genai.list_models():
            # Sprawdzamy, czy model wspiera metodę 'generateContent'
            if 'generateContent' in m.supported_generation_methods:
                logging.info(f"Model: {m.name}")
        logging.info("---------------------------------")
    except Exception as e:
        logging.error(f"Nie udało się pobrać listy modeli: {e}")

# --- Konfiguracja Klienta Google Gemini ---
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Krytyczny błąd: Klucz API GEMINI_API_KEY nie został znaleziony w .env.")
    
    client = genai.Client(api_key=api_key)
    
    logging.info(f"Pomyślnie skonfigurowano klienta Google Gemini. Model: '{MODEL_ID}'. Język docelowy: {TARGET_LANG}")

except Exception as e:
    logging.critical(f"Krytyczny błąd podczas konfiguracji klienta Gemini: {e}")
    client = None

# --- Instrukcja Systemowa (zorientowana na dubbing) ---
SYSTEM_INSTRUCTION = f"""You are a professional dubbing adapter. Translate the English subtitles to {TARGET_LANG}.

CRUCIAL RULES:
1.  **Isochrony:** The spoken duration in {TARGET_LANG} must match the original timestamps. Your translation should aim for a similar length and syllable count to the original to facilitate voice-over synchronization.
2.  **Easy Pronunciation:** The text must be natural and easy for a voice-over actor to speak. Avoid awkward phrasing or overly complex words.
3.  **Capture Meaning, Not Words:** Do not translate literally. Rephrase sentences to make them sound natural and powerful in {TARGET_LANG}.
4.  **Output Format:** Return ONLY a raw JSON array. Do not include any markdown, explanations, or additional text outside the JSON array.
"""

def clean_json(response_text: str) -> str:
    """
    Używa regex, aby wyodrębnić tylko tablicę JSON z odpowiedzi, usuwając markdown i inne "chatter".
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

    # Skanuje pliki .json, ignorując te już przetłumaczone (_translated.json)
    # i ignorując też pliki z poprzednich prób (_PL.json)
    files_to_translate = [
        f for f in glob.glob(os.path.join(DOWNLOADS_DIR, "*.json"))
        if not f.endswith('_translated.json') and not f.endswith('_PL.json')
    ]
    
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
            
            cleaned_json_str = clean_json(response.text)
            translated_data = json.loads(cleaned_json_str)

            # Zapisywanie z nowym przyrostkiem '_translated.json'
            base_filename = os.path.splitext(os.path.basename(file_path))[0]
            output_path = os.path.join(DOWNLOADS_DIR, f"{base_filename}_translated.json")

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(translated_data, f, indent=4, ensure_ascii=False)

            logging.info(f"Dubbing-ready tłumaczenie zapisano pomyślnie do: {os.path.basename(output_path)}")

        except google_exceptions.NotFound as e:
            logging.error(f"BŁĄD KRYTYCZNY: Model '{MODEL_ID}' nie został znaleziony lub nie masz do niego dostępu.")
            logging.error("Powyżej znajduje się lista dostępnych modeli. Sprawdź, czy używasz poprawnej nazwy.")
            logging.error(f"Szczegóły błędu: {e}")
            break
        except Exception as e:
            logging.error(f"Nie udało się przetworzyć pliku {file_path}: {e}", exc_info=True)

if __name__ == "__main__":
    translate_json_files()
