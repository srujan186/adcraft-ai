from pydantic import BaseModel, Field
from typing import List, Literal, Optional

# The allowed values, in one place. These used to live only as comments below
# and as hand-written `if` checks in routers/generate.py, which meant the two
# generate routes that took a bare dict enforced nothing at all.
AdStyle  = Literal["modern", "bold", "minimal", "playful"]
# A 15s ad cut into more than this is a slideshow, and each extra scene is
# another image fetch and another ffmpeg encode.
MAX_SCENES = 12
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

class RerenderScript(BaseModel):
    """The fields the editor can actually change."""
    headline:          str
    subtext:           str = ""
    cta:               str = ""
    voiceover:         str = ""
    music_style:       str = "upbeat"
    scene_description: str = ""


class EndCard(BaseModel):
    """
    The ad's closing frame: who this is and how to reach them.

    Collected in the editor's Banner tab. Every field is optional -- the card
    renders whichever ones were filled in, and is skipped entirely when they
    are all empty, so an untouched panel costs the ad nothing.
    """
    company_name: str = ""
    phone:        str = ""
    email:        str = ""
    address:      str = ""
    website:      str = ""


class RerenderRequest(BaseModel):
    """
    Re-run assembly against an edited script, without re-scraping or calling
    the LLM again. The editor already has everything the renderer needs.
    """
    business_name: str
    script:        RerenderScript
    duration:      Duration = 15
    url:           Optional[str] = ""
    logo_url:      Optional[str] = ""
    colors:        Optional[dict] = None
    # One image source per scene: a base64 data URL, or an https URL.
    scene_images:  Optional[List[str]] = None
    # The site's own photos, used for any scene the editor did not replace.
    content_images: Optional[List[str]] = None
    # Contact details for the closing card. Omit or leave empty for no card.
    end_card:      Optional[EndCard] = None
    # How many scenes to cut the footage into. The editor sends this when the
    # user has added slots beyond what the site yielded; without it the count
    # was inferred from how many entries carried an image, so an empty new
    # slot had no way to exist.
    scene_count:   Optional[int] = Field(default=None, ge=1, le=MAX_SCENES)
