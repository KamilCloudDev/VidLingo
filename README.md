# VidLingo - AI-Powered Video Translation & Dubbing

Welcome to the VidLingo project! This platform is designed to automate the process of video translation and dubbing using a modular, AI-powered pipeline.

## 🚀 How to Run the Suite

The entire VidLingo suite is managed via Docker Compose, allowing for easy, modular execution of each service. All generated media will appear in the local `downloads` folder.

1.  **Build All Services**:
    Builds the Docker images for all modules.
    ```bash
    docker-compose build
    ```

2.  **Run the Downloader (Module 1)**:
    Downloads a video from a given URL into the shared `./downloads` folder.
    ```bash
    docker-compose run yt-downloader "https://www.youtube.com/watch?v=your-video-id"
    ```

3.  **Run the Transcriber (Module 2)**:
    Scans the `./downloads` folder for videos and generates a timestamped transcription JSON file.
    ```bash
    docker-compose run transcriber
    ```

4.  **Run the Translator (Module 3)**:
    Scans the `./downloads` folder for transcription files and translates them using the configured cloud AI. You can specify the target language using the `TARGET_LANGUAGE` environment variable.
    ```bash
    docker-compose run --env TARGET_LANGUAGE=French translator
    # Or for Polish (default):
    # docker-compose run translator
    ```

---

## 📦 Modules

This project is built with a modular, service-oriented architecture. Each service has its own README file for detailed information.

### Module 1: YouTube Downloader (`/services/yt-downloader`)
-   **Status**: ✅ Complete
-   **Description**: A containerized Python service for media acquisition. More details in its [local README](./services/yt-downloader/README.md).

### Module 2: AI Transcription Engine (`/services/transcriber`)
-   **Status**: ✅ Complete
-   **Description**: A high-performance transcription service using `faster-whisper` on CPU. More details in its [local README](./services/transcriber/README.md).

### Module 3: Cloud AI Translator (`/services/translator`)
-   **Status**: ✅ Complete
-   **Description**: A cloud-native translation service using Google's Gemini API for dubbing-ready text. More details in its [local README](./services/translator/README.md).

## 🛠️ Tech Stack

-   **Backend**: Python 3.11
-   **AI / ML**: `faster-whisper`, Google Gemini API
-   **Containerization**: Docker, Docker Compose
-   **Core Libraries**: `yt-dlp`
-   **Automation**: Git

## Contributing

This project is in its initial development phase. Contribution guidelines will be established as the project matures.

---
