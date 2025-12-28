# VidLingo - AI-Powered Video Translation & Dubbing

Welcome to the VidLingo project! This platform is designed to automate the process of video translation and dubbing using modern AI-powered tools. The goal is to take any video with spoken content and produce a version dubbed in a different language.

## 🚀 Modules

This project is built with a modular, service-oriented architecture.

### Module 1: YouTube Downloader (`/services/yt-downloader`)

-   **Status**: ✅ Complete
-   **Description**: A containerized Python service that downloads video and subtitle data from YouTube. It uses `yt-dlp` to fetch the highest quality video (MP4) and any available subtitle tracks (SRT/VTT). This module serves as the primary data-gathering tool for the platform.

### Module 2: AI Translation & Transcription

-   **Status**: 🚧 Planned
-   **Description**: This service will take the text from the downloaded subtitles, or transcribe the audio if no subtitles are available, and translate it into the target language.

### Module 3: AI Voice Synthesis & Dubbing

-   **Status**: 🚧 Planned
-   **Description**: The translated text will be used to generate a new audio track using text-to-speech (TTS) technology. This audio will then be merged with the original video to create the final dubbed version.

## 🛠️ Tech Stack

-   **Backend**: Python
-   **Containerization**: Docker
-   **Automation**: Git, Shell Scripting

## Contributing

This project is currently in the initial development phase. Contribution guidelines will be established as the project matures.

---
