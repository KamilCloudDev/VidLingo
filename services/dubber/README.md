# Module 4: AI Dubbing Service

This service is the final module in the VidLingo pipeline, responsible for synthesizing dubbed audio and integrating it into the final video.

## Role

It takes the translated JSON subtitles and the original video file. It then performs:
-   **Voice Cloning:** Extracts a voice sample from the original video.
-   **Text-to-Speech (TTS):** Generates dubbed audio for each translated segment using the Coqui XTTSv2 model, attempting to match the original speaker's voice.
-   **Audio Alignment:** Stretches or compresses generated audio clips to precisely fit the segment timestamps (isochrony).
-   **Audio Mixing:** Applies a high-pass filter to the original audio (to dim original voices) and mixes it with the newly generated dubbed audio.
-   **Video Remuxing:** Integrates the final mixed audio track back into the video, producing the final dubbed video.

## Orchestration

This service is managed via the main `docker-compose.yml` file. It requires a powerful CPU or GPU for efficient TTS generation. Ensure `COQUI_TOS_AGREED=1` is set in its environment for Coqui TTS models.
