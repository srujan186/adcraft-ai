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

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
