"""AI Creative Studio (docs/12): URL → script → (silent TTS fallback) → ffmpeg render → creative.

A self-contained renderer; the heavier scrape→script→TTS→render video pipeline in the
repo's `backend/` can be swapped in behind this interface. TTS defaults to a silent
track + on-screen captions (no API key needed), per the TTSProvider contract.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
import uuid

import httpx

from app.core import storage
from app.core.config import settings
from app.core.db import SessionLocal
from app.models.creative import Creative, CreativeSource, ReviewStatus
from app.models.studio import StudioJob, StudioJobStatus
from app.services.creative_processing import make_thumbnail, probe

# Studio "tone" → the video generator's ad_style vocabulary (modern/bold/minimal/playful).
_TONE_TO_STYLE = {"energetic": "bold", "premium": "minimal", "friendly": "playful", "informative": "modern"}

W, H = 1920, 1080
_FONTS = ["C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def _font() -> str:
    for f in _FONTS:
        if os.path.exists(f):
            return f
    return _FONTS[0]


def _clean(text: str, limit: int = 48) -> str:
    text = re.sub(r"[^A-Za-z0-9 .,!?&-]", " ", text or "").strip()
    text = re.sub(r"\s+", " ", text)
    return (text[:limit]).strip() or "Your brand"


def scrape(url: str | None, fallback_name: str) -> dict:
    title, desc = fallback_name, "Now on streaming TV."
    if url:
        try:
            r = httpx.get(url if url.startswith("http") else f"https://{url}", timeout=8.0, follow_redirects=True)
            html = r.text
            m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
            if m:
                title = m.group(1).strip()
            d = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.I)
            if d:
                desc = d.group(1).strip()
        except Exception:  # noqa: BLE001 — scrape is best-effort
            pass
    return {"title": _clean(title, 40), "description": _clean(desc, 60)}


def build_script(scraped: dict, duration_s: int, tone: str, cta: str) -> dict:
    scenes = [
        {"caption": scraped["title"], "voiceover": scraped["title"]},
        {"caption": scraped["description"], "voiceover": scraped["description"]},
        {"caption": cta or "Learn more today", "voiceover": cta or "Learn more today"},
    ]
    if duration_s >= 30:
        scenes.insert(2, {"caption": f"{tone.title()} and made for you", "voiceover": "Made for you"})
    per = duration_s / len(scenes)
    for i, s in enumerate(scenes):
        s["start"], s["end"] = round(i * per, 2), round((i + 1) * per, 2)
    return {"headline": scraped["title"], "scenes": scenes, "cta": cta}


def _render(script: dict, duration_s: int, dst: str) -> None:
    font = _font().replace(":", "\\:")  # escape drive colon for the filtergraph
    draws = []
    for i, s in enumerate(script["scenes"]):
        y = "(h-text_h)/2" if i % 2 == 0 else "(h-text_h)/2+120"
        size = 96 if i == 0 else 64
        draws.append(
            f"drawtext=fontfile='{font}':text='{_clean(s['caption'], 60)}':fontsize={size}:fontcolor=white:"
            f"x=(w-text_w)/2:y={y}:enable='between(t,{s['start']},{s['end']})'"
        )
    vf = f"format=yuv420p,{','.join(draws)}"
    subprocess.run(
        ["ffmpeg", "-y",
         "-f", "lavfi", "-i", f"color=c=0x4f39f6:s={W}x{H}:d={duration_s}:r=30",
         "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-vf", vf, "-t", str(duration_s), "-c:v", "libx264", "-preset", "veryfast",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", dst],
        capture_output=True, text=True, check=True,
    )


async def render_creative(inp: dict) -> dict:
    """Scrape → script → render → upload. Returns creative fields (no DB). Usable in tests."""
    import asyncio

    tmp = tempfile.mkdtemp(prefix="studio_")
    out = os.path.join(tmp, "ad.mp4")
    thumb = os.path.join(tmp, "thumb.jpg")
    try:
        duration = int(inp.get("duration_s", 15))
        scraped = scrape(inp.get("url"), inp.get("business_name") or "Your brand")
        script = build_script(scraped, duration, inp.get("tone", "informative"), inp.get("cta", "Learn more"))
        await asyncio.to_thread(_render, script, duration, out)
        await asyncio.to_thread(make_thumbnail, out, thumb)
        dur_ms, w, h = await asyncio.to_thread(probe, out)
        base = f"creatives/studio/{uuid.uuid4()}"
        vkey = await asyncio.to_thread(storage.upload_file, out, f"{base}/ad.mp4", "video/mp4")
        tkey = await asyncio.to_thread(storage.upload_file, thumb, f"{base}/thumb.jpg", "image/jpeg")
        return {"name": f"Studio — {scraped['title']}"[:200], "script": script, "file_key": vkey,
                "thumbnail_key": tkey, "duration_ms": dur_ms, "width": w, "height": h}
    finally:
        for p in (out, thumb):
            try:
                os.remove(p)
            except OSError:
                pass
        try:
            os.rmdir(tmp)
        except OSError:
            pass


async def render_via_video_app(inp: dict) -> dict:
    """Full narrated generator (backend/): scrape → LLM script → Kokoro TTS → music → ffmpeg.

    Calls the video app over HTTP, downloads the finished MP4, then reuses the same
    probe/thumbnail/upload path as the simple renderer. Requires a business URL.
    """
    import asyncio

    url = (inp.get("url") or "").strip()
    if not url:
        raise ValueError("A business URL is required for AI narration.")
    ad_style = _TONE_TO_STYLE.get(inp.get("tone", "informative"), "modern")
    duration = int(inp.get("duration_s", 15))
    base = settings.video_app_url.rstrip("/")

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as c:
        r = await c.post(f"{base}/api/generate/video", json={"url": url, "ad_style": ad_style, "duration": duration})
        if r.status_code != 200:
            detail = r.text[:300]
            try:
                detail = r.json().get("detail", detail)
            except Exception:  # noqa: BLE001
                pass
            raise RuntimeError(f"Video generator failed ({r.status_code}): {detail}")
        data = (r.json() or {}).get("data") or {}
        video_url = data.get("video_url")
        if not video_url:
            raise RuntimeError("Video generator returned no video_url.")
        src = video_url if video_url.startswith("http") else f"{base}{video_url}"
        dl = await c.get(src)
        dl.raise_for_status()

    tmp = tempfile.mkdtemp(prefix="studio_va_")
    out = os.path.join(tmp, "ad.mp4")
    thumb = os.path.join(tmp, "thumb.jpg")
    try:
        with open(out, "wb") as f:
            f.write(dl.content)
        await asyncio.to_thread(make_thumbnail, out, thumb)
        dur_ms, w, h = await asyncio.to_thread(probe, out)
        key_base = f"creatives/studio/{uuid.uuid4()}"
        vkey = await asyncio.to_thread(storage.upload_file, out, f"{key_base}/ad.mp4", "video/mp4")
        tkey = await asyncio.to_thread(storage.upload_file, thumb, f"{key_base}/thumb.jpg", "image/jpeg")
        name = _clean(data.get("scraped", {}).get("business_name") or inp.get("business_name") or "Your brand", 40)
        return {"name": f"Studio — {name}"[:200], "script": data.get("script") or {}, "file_key": vkey,
                "thumbnail_key": tkey, "duration_ms": dur_ms, "width": w, "height": h}
    finally:
        for p in (out, thumb):
            try:
                os.remove(p)
            except OSError:
                pass
        try:
            os.rmdir(tmp)
        except OSError:
            pass


async def run_studio_job(job_id: str) -> None:
    async with SessionLocal() as db:
        job = await db.get(StudioJob, job_id)
        if job is None:
            return
        job.status = StudioJobStatus.processing
        await db.commit()
        account_id, advertiser_id, inp = job.account_id, job.advertiser_id, job.input or {}

    use_video_app = settings.studio_renderer == "video_app" and bool((inp.get("url") or "").strip())
    try:
        r = await (render_via_video_app(inp) if use_video_app else render_creative(inp))
        async with SessionLocal() as db:
            creative = Creative(
                account_id=account_id, advertiser_id=advertiser_id, name=r["name"],
                source=CreativeSource.studio, file_key=r["file_key"], transcoded_key=r["file_key"],
                thumbnail_key=r["thumbnail_key"], duration_ms=r["duration_ms"], width=r["width"],
                height=r["height"], review_status=ReviewStatus.approved, review_notes="Generated by Studio.",
            )
            db.add(creative)
            await db.flush()
            j = await db.get(StudioJob, job_id)
            if j is None:  # job deleted/cancelled mid-render
                return
            j.status = StudioJobStatus.done
            j.script = r["script"]
            j.output_creative_id = creative.id
            await db.commit()
    except Exception as e:  # noqa: BLE001
        async with SessionLocal() as db:
            j = await db.get(StudioJob, job_id)
            if j is not None:
                j.status = StudioJobStatus.error
                j.error = str(e)[:1000]
                await db.commit()
