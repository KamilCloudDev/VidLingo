FROM ghcr.io/coqui-ai/tts:latest-cpu

ENV COQUI_TOS_AGREED=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -U pip
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY dubber.py .

CMD ["python3", "dubber.py"]
