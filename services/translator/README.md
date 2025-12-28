# Module 3: Cloud AI Translator

This service is the **Cloud AI Translation Engine** for the VidLingo platform, responsible for translating transcribed text into the target language.

## Role

It automatically detects transcription files (`.json`) and uses the **Google Gemini API** (specifically the `gemini-2.5-flash` model) to perform high-quality, context-aware translation. The prompts are specifically engineered to produce natural, cinematic language suitable for professional dubbing and voice-over work.

The service is language-agnostic and can be configured to translate to any language supported by the Gemini API via the `TARGET_LANGUAGE` environment variable.

## Orchestration

This service is managed via the main `docker-compose.yml` file and requires a `GEMINI_API_KEY` to be set in the `.env` file.
