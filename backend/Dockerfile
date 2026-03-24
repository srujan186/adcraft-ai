# ─── Backend Dockerfile ───────────────────────────────────────────────────────
FROM python:3.12-slim

# System deps for Playwright + audio/video libs
RUN apt-get update && apt-get install -y \
    ffmpeg \
    espeak-ng \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium --with-deps

# Copy source
COPY . .

# Create dirs that must exist
RUN mkdir -p output temp

# PORT=7860 for Hugging Face Spaces, 8000 for local/Docker Compose
ENV PORT=7860
EXPOSE 7860

CMD uvicorn server:app --host 0.0.0.0 --port ${PORT}

