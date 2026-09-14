# routers/generate.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from models.generate import GenerateRequest, RerenderRequest, VideoRequest
from services.script_generator import generate_ad_script, MODEL
from services.scraper import scrape_business_url
from services.video_assembler import assemble_video
import os

router = APIRouter(prefix="/api", tags=["generate"])


def _fail(where: str, exc: Exception, message: str) -> HTTPException:
    """
    Log the real error, hand the client a sentence it can act on.

    These handlers used to `raise HTTPException(detail=str(e))`, which put
    ffmpeg stderr, absolute paths and upstream URLs straight into the
    browser -- the frontend renders `detail` verbatim to the user.
    """
    import traceback

    print(f"\u274c {where}: {type(exc).__name__}: {exc}")
    traceback.print_exc()
    return HTTPException(status_code=500, detail=message)


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
        raise _fail(
            "Script generation failed", e,
            "Could not write the ad script. Please try again.",
        )


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
        raise _fail(
            "from-url pipeline failed", e,
            "Could not build a script from that URL. Please try again.",
        )


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
            website_url=url,
            content_images=scraped.get("images") or [],
        )

        return {
            "success": True,
            "data": {
                "video_url":   video_result["url"],
                "render_id":   video_result["render_id"],
                "scene_count": video_result.get("scene_count"),
                "scene_sources": video_result.get("scene_sources", []),
                "script":      script,
                "scraped":     scraped,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise _fail(
            "Video pipeline failed", e,
            "Could not finish rendering your ad. Please try again.",
        )


@router.post("/generate/rerender")
async def rerender_video(request: RerenderRequest):
    """
    POST /api/generate/rerender

    Re-renders an ad from an edited script. Deliberately skips both the scrape
    and the LLM: the editor is holding the final copy, so re-deriving it would
    only risk changing what the user just wrote.
    """
    script = request.script.model_dump()

    if not script["headline"].strip():
        raise HTTPException(status_code=400, detail="headline is required")

    colors = request.colors or {
        "primary":   "#1a1a2e",
        "secondary": "#ffffff",
        "accent":    "#6c63ff",
    }

    try:
        print(f"\n🔁 Re-render for: {request.business_name}")
        result = await assemble_video(
            script=script,
            business_name=request.business_name,
            colors=colors,
            logo_url=request.logo_url or "",
            duration=request.duration,
            website_url=request.url or "",
            scene_images=request.scene_images or [],
            content_images=request.content_images or [],
            end_card=request.end_card.model_dump() if request.end_card else None,
            scene_count=request.scene_count,
        )
        return {
            "success": True,
            "data": {
                "video_url":   result["url"],
                "render_id":   result["render_id"],
                "scene_count": result.get("scene_count"),
                "scene_sources": result.get("scene_sources", []),
                "has_end_card": result.get("has_end_card", False),
                "end_card_at": result.get("end_card_at"),
                "script":      script,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Re-render error: {e}")
        raise HTTPException(status_code=500, detail="Re-render failed. Please try again.")


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