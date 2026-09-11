# routers/generate.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from models.generate import GenerateRequest, VideoRequest
from services.script_generator import generate_ad_script, MODEL
from services.scraper import scrape_business_url
from services.video_assembler import assemble_video
import os

router = APIRouter(prefix="/api", tags=["generate"])


@router.post("/generate/script")
async def generate_script(request: GenerateRequest):
    """Takes brand info → returns ad script only"""
    if not request.business_name.strip():
        raise HTTPException(status_code=400, detail="business_name is required")
    if not request.description.strip():
        raise HTTPException(status_code=400, detail="description is required")
    # ad_style and duration are enforced by the model — see models/generate.py.

    try:
        script = await generate_ad_script(
            business_name=request.business_name,
            description=request.description,
            tagline=request.tagline or "",
            ad_style=request.ad_style,
            duration=request.duration
        )
        return {
            "success": True,
            "data": {
                "script":   script,
                "metadata": {
                    "business_name": request.business_name,
                    "ad_style":      request.ad_style,
                    "duration":      request.duration,
                    "model_used":    MODEL
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/from-url")
async def generate_from_url(request: VideoRequest):
    """Scrape URL → generate script only (no video yet)"""
    url      = request.url.strip()
    ad_style = request.ad_style
    duration = request.duration

    if not url:
        raise HTTPException(status_code=400, detail="url is required")

    try:
        print(f"\n🔗 Pipeline starting for: {url}")
        scraped = await scrape_business_url(url)
        
        if scraped.get("scrape_failed"):
            raise HTTPException(status_code=400, detail=scraped.get("scrape_message", "Could not scrape the provided URL."))

        script  = await generate_ad_script(
            business_name=scraped["business_name"],
            description=scraped["description"],
            tagline=scraped.get("tagline", ""),
            ad_style=ad_style,
            duration=duration
        )
        return {
            "success": True,
            "data": {
                "scraped":  scraped,
                "script":   script,
                "metadata": {"url": url, "ad_style": ad_style, "duration": duration}
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/video")
async def generate_video(request: VideoRequest):
    url      = request.url.strip()
    ad_style = request.ad_style
    duration = request.duration

    if not url:
        raise HTTPException(status_code=400, detail="url is required")

    try:
        # Step 1: Scrape
        print(f"\n🔗 Full video pipeline: {url}")
        scraped = await scrape_business_url(url)

        if scraped.get("scrape_failed"):
            raise HTTPException(status_code=400, detail=scraped.get("scrape_message", "Could not scrape the provided URL."))

        # Step 2: Generate script
        script = await generate_ad_script(
            business_name=scraped["business_name"],
            description=scraped["description"],
            tagline=scraped.get("tagline", ""),
            ad_style=ad_style,
            duration=duration
        )

        # Step 3: Safely extract colors and logo
        # Use 'or' to handle None values from failed scrapes
        colors   = scraped.get("colors") or {
            "primary":   "#1a1a2e",
            "secondary": "#ffffff",
            "accent":    "#6c63ff"
        }
        logo_url = scraped.get("logo_url") or ""

        # Step 4: Assemble video
        video_result = await assemble_video(
            script=script,
            business_name=scraped["business_name"],
            colors=colors,
            logo_url=logo_url,
            duration=duration,
            website_url=url
        )

        return {
            "success": True,
            "data": {
                "video_url": video_result["url"],
                "render_id": video_result["render_id"],
                "script":    script,
                "scraped":   scraped,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Video pipeline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/output/{filename}")
async def serve_video(filename: str):
    """
    GET /api/output/{filename}
    Serves the generated video file to the frontend.

    This handler shadows the StaticFiles mount that used to sit on the same
    path, so it has to do the containment checking StaticFiles did for us:
    strip any directory component, allow only .mp4, and confirm the resolved
    path is still inside output/ before serving it.
    """
    BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.realpath(os.path.join(BASE_DIR, "output"))

    # basename() drops "../" and, on Windows, backslash segments the router
    # does not treat as separators but os.path.join does.
    name = os.path.basename(filename)

    if not name.lower().endswith(".mp4"):
        raise HTTPException(status_code=404, detail="Video not found")

    output_path = os.path.realpath(os.path.join(output_dir, name))

    # Belt and braces: catches symlinks pointing out of the directory.
    if not output_path.startswith(output_dir + os.sep):
        raise HTTPException(status_code=404, detail="Video not found")

    if not os.path.isfile(output_path):
        raise HTTPException(status_code=404, detail="Video not found")

    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename=name
    )