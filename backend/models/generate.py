from pydantic import BaseModel
from typing import Literal, Optional

# The allowed values, in one place. These used to live only as comments below
# and as hand-written `if` checks in routers/generate.py, which meant the two
# generate routes that took a bare dict enforced nothing at all.
AdStyle  = Literal["modern", "bold", "minimal", "playful"]
Duration = Literal[15, 30]


class GenerateRequest(BaseModel):
    """
    What the frontend sends to /api/generate
    All the brand info + user preferences
    """
    business_name: str
    description:   str
    tagline:       Optional[str] = ""
    logo_url:      Optional[str] = ""
    website_url:   Optional[str] = ""
    colors:        Optional[dict] = {}

    # User choices from the generate page
    ad_style: AdStyle = "modern"
    # modern   = clean, professional, confident
    # bold     = high energy, punchy, exciting
    # minimal  = simple, elegant, one big idea
    # playful  = fun, friendly, approachable

    duration: Duration = 15
    # 15 = 15 second ad
    # 30 = 30 second ad


class VideoRequest(BaseModel):
    """
    What the frontend sends to /api/generate/video and /api/generate/from-url.

    Both routes used to take a bare `dict`, so ad_style and duration were never
    checked — duration in particular reaches ffmpeg as an argv element and is
    interpolated into an audio filter string, so a bad value failed deep in the
    pipeline instead of at the door.
    """
    url:      str
    ad_style: AdStyle = "modern"
    duration: Duration = 15


class AdScript(BaseModel):
    """
    The structured ad script returned by Claude/Groq
    Every field maps to something in the video
    """

    headline:        str    # main text on screen (max 8 words)
    subtext:         str    # supporting text (max 15 words)
    cta:             str    # call to action button text
    voiceover:       str    # full spoken script
    music_style:     str    # upbeat/calm/corporate/dramatic
    scene_description: str  # what visuals to show
    color_mood:      str    # vibrant/dark/light/warm/cool
    key_message:     str    # the single core message


class GenerateResponse(BaseModel):
    """
    What we send back to the frontend
    after generating the video
    """
    video_url:     str
    render_id:     str
    thumbnail_url: Optional[str] = ""
    script:        Optional[dict] = {}
    status:        str = "done"