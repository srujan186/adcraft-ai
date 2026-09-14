# ─── Backend Dockerfile ───────────────────────────────────────────────────────
FROM python:3.12-slim

# System deps for Playwright + audio/video libs
# fonts-dejavu-core is not optional: Pillow draws the headline, subtext and
# CTA, and with no system font it falls back to a ~10px face and the ad renders
# illegibly while still reporting success.
RUN apt-get update && apt-get install -y \
    ffmpeg \
    espeak-ng \
    libgomp1 \
    fonts-dejavu-core \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium --with-deps

# Copy source.
#
# NOTE: models/*.onnx, models/*.bin and music/*.mp3 are git-lfs files. If the
# build context has not had `git lfs pull` run, this copies 130-byte pointer
# files instead of the real ones — Kokoro then fails to load and every render
# comes out silent. server.py checks for this at startup and says so.
COPY . .

# Create dirs that must exist
RUN mkdir -p output temp

# PORT=7860 for Hugging Face Spaces, 8000 for local/Docker Compose
ENV PORT=7860
EXPOSE 7860

CMD uvicorn server:app --host 0.0.0.0 --port ${PORT}

