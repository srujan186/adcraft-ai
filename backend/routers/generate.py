# routers/generate.py
# Handles POST /api/generate
# Takes brand data → returns ad script
# Actual logic lives in services/script_generator.py
# Add this import at the top
# routers/generate.py

from fastapi import APIRouter, HTTPException
from models.generate import GenerateRequest
from services.script_generator import generate_ad_script
from services.scraper import scrape_business_url

# router MUST be defined before any @router decorators
router = APIRouter(prefix="/api", tags=["generate"])


@router.post("/generate/script")
async def generate_script(request: GenerateRequest):
    """
    POST /api/generate/script
    Takes brand info directly → returns ad script
    """

    if not request.business_name.strip():
        raise HTTPException(
            status_code=400,
            detail="business_name is required"
        )

    if not request.description.strip():
        raise HTTPException(
            status_code=400,
            detail="description is required"
        )

    valid_styles = ["modern", "bold", "minimal", "playful"]
    if request.ad_style not in valid_styles:
        raise HTTPException(
            status_code=400,
            detail=f"ad_style must be one of: {valid_styles}"
        )

    if request.duration not in [15, 30]:
        raise HTTPException(
            status_code=400,
            detail="duration must be 15 or 30"
        )

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
                "script": script,
                "metadata": {
                    "business_name": request.business_name,
                    "ad_style":      request.ad_style,
                    "duration":      request.duration,
                    "model_used":    "llama-3.3-70b-versatile"
                }
            }
        }

    except Exception as e:
        print(f"❌ Script generation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Script generation failed: {str(e)}"
        )


@router.post("/generate/from-url")
async def generate_from_url(request: dict):
    """
    POST /api/generate/from-url

    Full pipeline in one call:
    1. Scrape the URL
    2. Generate ad script from scraped data
    3. Return everything together
    """

    url      = request.get("url", "")
    ad_style = request.get("ad_style", "modern")
    duration = request.get("duration", 15)

    if not url:
        raise HTTPException(
            status_code=400,
            detail="url is required"
        )

    if ad_style not in ["modern", "bold", "minimal", "playful"]:
        ad_style = "modern"

    if duration not in [15, 30]:
        duration = 15

    try:
        # Step 1: Scrape the URL
        print(f"\n🔗 Full pipeline starting for: {url}")
        scraped = await scrape_business_url(url)

        # Step 2: Generate script from scraped data
        script = await generate_ad_script(
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
                "metadata": {
                    "url":      url,
                    "ad_style": ad_style,
                    "duration": duration,
                }
            }
        }

    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )