# services/pexels.py
# ONE job: search Pexels for relevant video footage
# and download it to our temp folder

import os
import re
import aiohttp
import aiofiles
from dotenv import load_dotenv

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PEXELS_API_URL = "https://api.pexels.com/videos"


# ═══════════════════════════════════════════════════════
# SECTION 1 — HELPER FUNCTIONS (defined first)
# ═══════════════════════════════════════════════════════

def extract_search_query(scene_description: str) -> str:
    """
    Extract a clean search query from scene description.

    Input:  "Scene 1: Developers coding together on laptops"
    Output: "developers coding together"
    """
    # Take first scene only
    if "Scene" in scene_description:
        first_scene = scene_description.split("Scene")[1]
    else:
        first_scene = scene_description

    # Remove "1:", "2:" numbering
    first_scene = re.sub(r'^\s*\d+:\s*', '', first_scene)

    # Take first 5 words max
    words = first_scene.strip().split()[:5]
    query = " ".join(words)

    print(f"  🔍 Extracted search query: '{query}'")
    return query


def get_best_video_url(video: dict, target_width: int = 1280) -> str:
    """
    From a Pexels video object, get the best quality
    video file URL closest to our target resolution.

    Pexels gives multiple quality versions of each video.
    We want 1280x720 — good quality without huge file size.
    """
    video_files = video.get("video_files", [])

    if not video_files:
        return ""

    # Filter for MP4 files only
    mp4_files = [
        f for f in video_files
        if f.get("file_type") == "video/mp4"
    ]

    if not mp4_files:
        return ""

    # Sort by how close width is to our target
    mp4_files.sort(
        key=lambda f: abs(f.get("width", 0) - target_width)
    )

    best = mp4_files[0]
    print(f"  📹 Selected video: {best.get('width')}x{best.get('height')}")
    return best.get("link", "")


# ═══════════════════════════════════════════════════════
# SECTION 2 — API FUNCTIONS
# ═══════════════════════════════════════════════════════

async def search_videos(query: str, per_page: int = 5) -> list:
    """
    Search Pexels for videos matching the query.
    Returns list of video data dictionaries.
    """
    headers = {
        "Authorization": PEXELS_API_KEY
    }
    params = {
        "query":       query,
        "per_page":    per_page,
        "size":        "medium",
        "orientation": "landscape"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{PEXELS_API_URL}/search",
            headers=headers,
            params=params
        ) as response:
            if response.status != 200:
                raise Exception(f"Pexels API error: {response.status}")
            data = await response.json()

    videos = data.get("videos", [])
    print(f"  🎬 Pexels found {len(videos)} videos for: '{query}'")
    return videos


async def download_video(url: str, output_path: str) -> str:
    """
    Download a video file from URL to local path.
    Downloads in chunks to handle large files efficiently.
    """
    print(f"  ⬇️  Downloading video...")

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Download failed: {response.status}")

            total_size   = int(response.headers.get("content-length", 0))
            downloaded   = 0
            last_reported = 0

            async with aiofiles.open(output_path, "wb") as f:
                async for chunk in response.content.iter_chunked(8192):
                    await f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        progress = int((downloaded / total_size) * 100)
                        if progress >= last_reported + 25:
                            last_reported = progress
                            kb_done  = downloaded // 1024
                            kb_total = total_size // 1024
                            print(f"  ⬇️  {progress}% ({kb_done}KB of {kb_total}KB)")

    print(f"  ✅ Video downloaded: {output_path}")
    return output_path


# ═══════════════════════════════════════════════════════
# SECTION 3 — MAIN FUNCTION (defined last)
# ═══════════════════════════════════════════════════════

async def get_background_video(
    scene_description: str,
    output_path:       str,
    fallback_queries:  list = None
) -> str:
    """
    Main function — finds and downloads the best
    background video for our ad.

    Tries primary query first, then fallbacks.
    Always finds something rather than failing.
    """

    # Extract search query from scene description
    primary_query = extract_search_query(scene_description)

    # Fallback queries if primary fails
    if not fallback_queries:
        fallback_queries = [
            "business professional",
            "modern office",
            "technology",
            "success team",
        ]

    all_queries = [primary_query] + fallback_queries

    for query in all_queries:
        try:
            print(f"  🔍 Searching Pexels: '{query}'")
            videos = await search_videos(query, per_page=3)

            if not videos:
                print(f"  ⚠️  No results for '{query}' — trying next")
                continue

            # Get URL of best quality version
            video_url = get_best_video_url(videos[0])

            if not video_url:
                print(f"  ⚠️  No MP4 found — trying next query")
                continue

            # Download it
            await download_video(video_url, output_path)
            return output_path

        except Exception as e:
            print(f"  ⚠️  Query '{query}' failed: {e}")
            continue

    raise Exception(
        "Could not find or download any background video "
        "after trying all queries"
    )