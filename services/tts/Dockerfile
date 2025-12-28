FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Instalujemy FFmpeg, który jest kluczowy dla pydub i operacji na audio/wideo
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -U -r requirements.txt

COPY tts.py .

CMD ["python", "tts.py"]