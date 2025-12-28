# Używamy oficjalnego, poprawnego obrazu Coqui TTS dla CPU
FROM ghcr.io/coqui-ai/tts-cpu

# Ustawiamy zmienne środowiskowe
ENV COQUI_TOS_AGREED=1
ENV PYTHONUNBUFFERED=1

# Instalujemy FFmpeg, aby był dostępny w systemowej ścieżce
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Aktualizujemy pip i instalujemy zależności z requirements.txt
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -U pip
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Kopiujemy skrypt aplikacji
COPY dubber.py .

# Ustawiamy domyślną komendę
CMD ["python3", "dubber.py"]
