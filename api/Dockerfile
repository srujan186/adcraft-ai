FROM python:3.13-slim

# ffmpeg for creative transcode (worker); curl for healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Default = API. docker-compose overrides `command` for worker/scheduler.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
