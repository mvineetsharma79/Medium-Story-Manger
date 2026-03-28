from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional, List

class Settings(BaseSettings):
    # Application settings
    app_name: str = "Story Manager"
    debug: bool = True
    
    # Stories directory
    stories_root: str = "./stories"
    
    # Publishing calendar settings
    default_series_spacing_days: int = 7
    default_stories_per_week: int = 3
    preferred_publish_days: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday"]
    start_date: Optional[str] = None
    
    # Data directory
    data_dir: str = "./data"
    
    # File paths (derived)
    @property
    def stories_json_path(self) -> Path:
        return Path(self.data_dir) / "stories.json"
    
    @property
    def calendar_json_path(self) -> Path:
        return Path(self.data_dir) / "publishing-calendar.json"
    
    @property
    def calendar_md_path(self) -> Path:
        return Path(self.data_dir) / "publishing-calendar.md"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # ← This allows extra fields without error
    )

settings = Settings()

# Ensure directories exist
Path(settings.stories_root).mkdir(parents=True, exist_ok=True)
Path(settings.data_dir).mkdir(parents=True, exist_ok=True)