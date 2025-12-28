# Module 2: AI Transcription Engine

This service functions as the **AI Transcription Engine** for the VidLingo platform.

## Role

It automatically detects video files (`.mp4`) made available by the acquisition module (or **manually placed in the `downloads/` folder**) and uses the `faster-whisper` library to perform high-performance, CPU-based speech-to-text conversion.

The output is a structured `.json` file containing the transcribed text segments with precise `start` and `end` timestamps, which is then used by downstream translation and dubbing modules.

## Orchestration

This service is managed via the main `docker-compose.yml` file in the project root.