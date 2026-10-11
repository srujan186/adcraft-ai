"""Creative processing: ffprobe metadata, automated review, transcode to 1080p, thumbnail.

Review rules (docs/06 creative guidelines + M3 acceptance):
  < 5s           -> rejected
  > 90s          -> rejected
  otherwise      -> approved (non-16:9 is pillar/letter-boxed to 1920x1080 on transcode)
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile

from app.core.db import SessionLocal
from app.core import storage
from app.models.creative import Creative, ReviewStatus

TARGET_W, TARGET_H = 1920, 1080
MIN_MS, MAX_MS = 5_000, 90_000


def probe(path: str) -> tuple[int, int, int]:
    """Return (duration_ms, width, height)."""
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", path],
        capture_output=True, text=True,
    )
    data = json.loads(out.stdout or "{}")
    dur_ms = int(float(data.get("format", {}).get("duration", 0)) * 1000)
    w = h = 0
    for s in data.get("streams", []):
        if s.get("codec_type") == "video":
            w, h = int(s.get("width", 0)), int(s.get("height", 0))
            break
    return dur_ms, w, h


def review_decision(duration_ms: int, width: int, height: int) -> tuple[ReviewStatus, str]:
    if width == 0 or height == 0 or duration_ms == 0:
        return ReviewStatus.rejected, "Could not read the video. Please upload a valid .mp4."
    if duration_ms < MIN_MS:
        return ReviewStatus.rejected, f"Too short ({duration_ms / 1000:.0f}s). Creatives must be 5–90 seconds."
    if duration_ms > MAX_MS:
        return ReviewStatus.rejected, f"Too long ({duration_ms / 1000:.0f}s). Creatives must be 5–90 seconds."
    note = "Approved."
    if abs(width / height - 16 / 9) > 0.05:
        note = "Approved. Non-16:9 source was pillar/letter-boxed to 1920×1080."
    return ReviewStatus.approved, note


def transcode_1080p(src: str, dst: str) -> None:
    vf = (
        f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
        f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", src, "-vf", vf, "-r", "30", "-c:v", "libx264", "-preset", "veryfast",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", dst],
        capture_output=True, text=True, check=True,
    )


def make_thumbnail(src: str, dst: str) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-ss", "1", "-i", src, "-frames:v", "1", "-vf",
         f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
         f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2", dst],
        capture_output=True, text=True, check=True,
    )


async def process_creative(creative_id: str) -> None:
    """Download source, probe, review, transcode+thumbnail if approved, persist."""
    async with SessionLocal() as db:
        creative = await db.get(Creative, creative_id)
        if creative is None or not creative.file_key:
            return
        creative.review_status = ReviewStatus.processing
        await db.commit()

    tmp = tempfile.mkdtemp(prefix="creative_")
    src = os.path.join(tmp, "src.mp4")
    out = os.path.join(tmp, "out.mp4")
    thumb = os.path.join(tmp, "thumb.jpg")
    try:
        await asyncio.to_thread(storage.download_file, creative.file_key, src)
        dur_ms, w, h = await asyncio.to_thread(probe, src)
        status, notes = review_decision(dur_ms, w, h)

        transcoded_key = thumbnail_key = None
        if status == ReviewStatus.approved:
            await asyncio.to_thread(transcode_1080p, src, out)
            await asyncio.to_thread(make_thumbnail, src, thumb)
            base = f"creatives/{creative_id}"
            transcoded_key = await asyncio.to_thread(storage.upload_file, out, f"{base}/1080p.mp4", "video/mp4")
            thumbnail_key = await asyncio.to_thread(storage.upload_file, thumb, f"{base}/thumb.jpg", "image/jpeg")

        async with SessionLocal() as db:
            c = await db.get(Creative, creative_id)
            if c is None:
                return
            c.duration_ms, c.width, c.height = dur_ms, w, h
            c.review_status, c.review_notes = status, notes
            c.transcoded_key, c.thumbnail_key = transcoded_key, thumbnail_key
            await db.commit()
    except Exception as e:  # noqa: BLE001 — never leave a creative stuck "processing"
        async with SessionLocal() as db:
            c = await db.get(Creative, creative_id)
            if c is not None:
                c.review_status = ReviewStatus.rejected
                c.review_notes = f"Processing failed: {e}"[:500]
                await db.commit()
    finally:
        for p in (src, out, thumb):
            try:
                os.remove(p)
            except OSError:
                pass
        try:
            os.rmdir(tmp)
        except OSError:
            pass
