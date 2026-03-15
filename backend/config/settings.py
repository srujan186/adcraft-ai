import os
from dotenv import load_dotenv

load_dotenv()

class Settings:

    PORT: int = int(os.getenv("PORT",8000))
    NODE_ENV: str = os.getenv("NODE_ENV" , "development")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL","https://localhost:3000")
    
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CREATOMATE_API_KEY: str = os.getenv("CREATOMATE_API_KEY", "")
    
    # Scraper settings
    SCRAPER_TIMEOUT: int = 15       # seconds to wait for website
    SCRAPER_MAX_RETRIES: int = 3    # how many times to retry on failure
    CACHE_EXPIRY_DAYS: int = 7      # how long to cache scrape results

# Create one instance — everyone imports THIS object
settings = Settings()
