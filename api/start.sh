#!/bin/sh
# Container entrypoint for hosted deploys (Render, HF Spaces, Koyeb, Cloud Run...).
# Brings the schema up to date, then serves on the port the host assigns.
# docker-compose overrides `command`, so local dev is unaffected.
set -e
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"
