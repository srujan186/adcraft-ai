from pydantic import BaseModel
from typing import Optional


class ScrapeRequest(BaseModel):
    url: str


class BrandColors(BaseModel):
    primary: str = "#1a1a2e"
    secondary: str = "#ffffff"
    accent: str = "#6c63ff"

class ScrapeResponse(BaseModel):
    business_name: str
    description: str
    tagline: str
    logo_url: str
    colors: BrandColors
    domain: str
    url: str
    features: list = []
    from_cache: bool = False
    