from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional

class Settings(BaseSettings):
    # Application settings
    app_name: str = "Story Manager"
    debug: bool = True
    
    # Story root folder - change this to your stories directory
    stories_root: str = str(Path(__file__).parent.parent / "stories")
    
    # Default publishing settings
    default_series_spacing_days: int = 7
    default_stories_per_week: int = 3
    preferred_publish_days: list = ["Monday", "Tuesday", "Wednesday", "Thursday"]
    
    # File paths
    stories_json: str = "stories.json"
    calendar_md: str = "publishing-calendar.md"
    calendar_json: str = "publishing-calendar.json"
    
    class Config:
        env_file = ".env"

settings = Settings()