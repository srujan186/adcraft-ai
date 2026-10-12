FROM python:3.13-slim

# ffmpeg for creative transcode (worker); curl for healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# start.sh may arrive with CRLF from a Windows checkout; /bin/sh can't run that.
# var/ holds local-storage uploads; make it writable for hosts that run as a
# non-root user (Hugging Face Spaces runs as uid 1000).
RUN sed -i 's/\r$//' start.sh \
    && mkdir -p var/storage && chmod -R a+rwX var

EXPOSE 8000

# Default = API (migrate, then serve on $PORT or 8000).
# docker-compose overrides `command` for api/worker/scheduler.
CMD ["sh", "start.sh"]
