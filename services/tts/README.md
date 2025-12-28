# Module 4: AI TTS Service

This service is the **AI Text-to-Speech (TTS) and Audio Mixing Engine** for the VidLingo platform. It is the final step in the dubbing pipeline, responsible for synthesizing dubbed audio and integrating it with the original video.

## Role

The TTS service automatically detects translated transcription files (`*_translated.json`) and corresponding video files in the shared `downloads/` folder. It performs the following key functions:

1.  **Voice Synthesis**: Utilizes the `edge_tts` library to generate natural-sounding speech from translated text segments. It dynamically selects an appropriate male "Neural" voice based on the `TARGET_LANGUAGE` environment variable (e.g., Polish, English).
2.  **Robust Audio Generation**: Includes advanced error handling with retries and a concurrency semaphore to manage requests to the TTS engine, ensuring stability and preventing rate-limiting issues. If audio generation fails, it gracefully inserts silent segments.
3.  **Audio Track Assembly**: Combines all generated speech segments into a continuous dubbing audio track, precisely aligning them with their original timestamps.
4.  **Audio Mixing & "Ducking"**: Integrates the newly created dubbing track with the original video's audio. It intelligently reduces the volume of the original background audio (a technique known as "ducking") to ensure the dubbed voice is clear and prominent, while retaining ambient sounds.
5.  **Video Remuxing**: Uses `ffmpeg` to seamlessly blend the video stream with the new mixed audio track, producing a final dubbed MP4 video file.

## Technologies

*   **TTS Engine**: Microsoft Edge TTS (`edge_tts` library)
*   **Audio Manipulation**: `pydub`
*   **Video/Audio Processing**: `ffmpeg` (for mixing, ducking, and remuxing)

## Orchestration

This service is managed via the main `docker-compose.yml` file in the project root.
*   **Environment Variables**: The `TARGET_LANGUAGE` environment variable (e.g., `Polish`, `English`, `French`) can be set to control the language of the synthesized voice.
*   **Volume Mounts**: It uses bind mounts to access video and JSON files from `./downloads:/app/downloads` and stores temporary audio outputs in `./temp:/app/temp`.
