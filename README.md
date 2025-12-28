# VidLingo - AI-Powered Video Translation & Dubbing

Welcome to the VidLingo project! This platform is designed to automate the process of video translation and dubbing using a modular, AI-powered pipeline.

## 🚀 How to Run the Suite

The entire VidLingo suite is managed via Docker Compose, allowing for easy, modular execution of each service.

1.  **Build All Services**:
    Builds the Docker images for all modules defined in the `docker-compose.yml` file.
    ```bash
    docker-compose build
    ```

2.  **Run the Downloader (Module 1)**:
    Downloads a video from the given URL into a shared volume.
    ```bash
    docker-compose run yt-downloader "https://www.youtube.com/watch?v=your-video-id"
    ```

3.  **Run the Transcriber (Module 2)**:
    Scans the shared volume for video files and generates a timestamped transcription JSON file.
    ```bash
    docker-compose run transcriber
    ```

---

## 📦 Modules

This project is built with a modular, service-oriented architecture.

### Module 1: YouTube Downloader (`/services/yt-downloader`)

-   **Status**: ✅ Complete
-   **Description**: A containerized Python service that downloads video and subtitle data from YouTube. It uses `yt-dlp` to fetch the highest quality video (MP4) and any available subtitle tracks (SRT/VTT).

### Module 2: AI Transcription Engine (`/services/transcriber`)

-   **Status**: ✅ Complete
-   **Description**: A high-performance transcription service that uses `faster-whisper` for efficient CPU-based audio-to-text conversion. It produces a detailed JSON file with precise start/end timestamps for each transcribed text segment.

### Module 3: AI Voice Synthesis & Dubbing

-   **Status**: 🚧 Planned
-   **Description**: The translated text will be used to generate a new audio track using text-to-speech (TTS) technology. This audio will then be merged with the original video to create the final dubbed version.

## 🛠️ Tech Stack

-   **Backend**: Python 3.11
-   **Containerization**: Docker, Docker Compose
-   **Core Libraries**: `yt-dlp`, `faster-whisper`
-   **Automation**: Git

## Contributing

This project is currently in the initial development phase. Contribution guidelines will be established as the project matures.

---