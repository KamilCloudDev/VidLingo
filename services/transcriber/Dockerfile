# Use the official Python 3.11 slim image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install ffmpeg, a crucial dependency for audio extraction from video files
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application's code into the container
COPY transcriber.py .

# This command will run when the container starts
CMD ["python", "transcriber.py"]
