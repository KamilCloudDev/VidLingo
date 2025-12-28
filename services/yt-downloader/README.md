# Module 1: YouTube Downloader

This service is the primary **Media Acquisition Service** for the VidLingo platform.

## Role

Its sole responsibility is to download video and subtitle data from YouTube. It utilizes `yt-dlp` to fetch the highest quality MP4 video and all available subtitle tracks (`.srt`/`.vtt`), making them available for other modules in the processing pipeline.

## Orchestration

This service is managed via the main `docker-compose.yml` file in the project root.
