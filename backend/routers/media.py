# routers/media.py
# Stock imagery for the editor's scene picker.
#
# This is deliberately a thin proxy: it exists so the Pexels key stays on the
# server instead of shipping to the browser. Nothing is downloaded here — the
# response is metadata and the browser loads Pexels' own CDN URLs directly.

from fastapi import APIRouter, HTTPException, Query
from services.pexels import search_photos

router = APIRouter(prefix="/api/media", tags=["media"])


@router.get("/photos")
async def photos(
    query: str = Query(..., min_length=1, max_length=100),
    per_page: int = Query(15, ge=1, le=40),
):
    """
    GET /api/media/photos?query=bakery&per_page=15

    Returns: { "success": true, "data": [{ id, alt, author, thumb, full }] }
    """
    q = query.strip()
    if not q:
        raise HTTPException(status_code=400, detail="query cannot be empty")

    try:
        results = await search_photos(q, per_page)
    except RuntimeError as e:
        # Missing key or an upstream non-200. Both are our problem to explain,
        # not a stack trace to leak.
        print(f"Pexels photo search failed: {e}")
        raise HTTPException(
            status_code=502,
            detail="Stock image search is unavailable right now.",
        )
    except Exception as e:
        print(f"Pexels photo search error: {e}")
        raise HTTPException(
            status_code=502,
            detail="Stock image search is unavailable right now.",
        )

    return {"success": True, "data": results}
