# ─── Root Dockerfile for Hugging Face Spaces ────────────────────────────────────
# Hugging Face Spaces expects the Dockerfile to be in the root directory.
FROM python:3.12-slim

# System deps for Playwright + audio/video libs
RUN apt-get update && apt-get install -y \
    ffmpeg \
    espeak-ng \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the backend requirements first for caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (needed for web scraping)
RUN playwright install chromium --with-deps

# Copy the backend source code into /app
COPY backend/ .

# Create dirs that must exist
RUN mkdir -p output temp

# Set the port for Hugging Face Spaces (always 7860)
ENV PORT=7860
EXPOSE 7860

# Start FastAPI using uvicorn
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT}
