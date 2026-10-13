from fastapi import APIRouter , HTTPException
from models.scrape import ScrapeRequest
from services.scraper import scrape_business_url

router = APIRouter(prefix="/api", tags=["scrape"])

@router.post("/scrape")
async def scrape_url(request: ScrapeRequest):
    """
    POST /api/scrape
    
    Accepts: { "url": "brand.example" }
    Returns: brand information extracted from the URL
    """

    if not request.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    try:
        data = await scrape_business_url(request.url)
        return {"success": True, "data": data}

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Scrape error: {error_msg}")

        # Give the user a helpful message based on what went wrong
        if "403" in error_msg or "blocked" in error_msg.lower():
            user_message = (
                "This website has bot protection and cannot be scraped automatically. "
                "Please try a different URL."
            )
        elif "timeout" in error_msg.lower():
            user_message = "Website took too long to respond. Please try again."
        elif "too little" in error_msg.lower():
            user_message = (
                "This website requires JavaScript to load. "
                "Our system will retry with a full browser."
            )
        else:
            user_message = f"Could not analyze this URL: {error_msg}"

        raise HTTPException(status_code=500, detail=user_message)
