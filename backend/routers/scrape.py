from fastapi import APIRouter , HTTPException
from models.scrape import ScrapeRequest , ScrapeResponse
from services.scraper import scrape_business_url

router = APIRouter(prefix="/api", tags=["scrape"])

@router.post("/scrape")
async def scrape_url(request: ScrapeRequest):
    """
    POST /api/scrape
    
    Accepts: { "url": "apple.com" }
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


@router.post("/scrape/debug")
async def debug_scrape(request: ScrapeRequest):
    """
    Temporary debug endpoint.
    Shows raw HTML so we can see what the site is actually returning.
    DELETE THIS before production.
    """
    from services.scraper import clean_url
    import httpx

    url = clean_url(request.url)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.5",
    }

    async with httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
        headers=headers
    ) as client:
        response = await client.get(url)

    return {
        "status_code": response.status_code,
        "url_reached": str(response.url),
        "html_length": len(response.text),
        "first_500_chars": response.text[:500],
        "headers_received": dict(response.headers)
    }