"""
Configuration file for Story Manager application
"""

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Settings:
    """Application settings"""
    
    # ============================================
    # PATH CONFIGURATION
    # ============================================
    
    # Stories root directory - where markdown files are stored
    stories_root: str = os.getenv("STORIES_ROOT", "./stories")
    
    # Data directory - where JSON data files are stored
    data_dir: str = os.getenv("DATA_DIR", "./data")
    
    # ============================================
    # CALENDAR DEFAULTS
    # ============================================
    
    # Default spacing between series parts (in days)
    default_series_spacing_days: int = int(os.getenv("DEFAULT_SERIES_SPACING_DAYS", "7"))
    
    # Default number of stories to publish per week
    default_stories_per_week: int = int(os.getenv("DEFAULT_STORIES_PER_WEEK", "3"))
    
    # Preferred days for publishing (Monday = 0, Sunday = 6)
    preferred_publish_days: List[str] = os.getenv(
        "PREFERRED_PUBLISH_DAYS",
        "Monday,Tuesday,Wednesday,Thursday"
    ).split(",")
    
    # Calendar start date (YYYY-MM-DD)
    start_date: Optional[str] = os.getenv("START_DATE", None)
    
    # ============================================
    # MEDIUM API CONFIGURATION
    # ============================================
    
    # Medium username (default: mvineetsharma)
    medium_username: str = os.getenv("MEDIUM_USERNAME", "mvineetsharma")
    
    # Medium API authentication
    # Option 1: Individual cookies
    medium_sid: Optional[str] = os.getenv("MEDIUM_SID", None)
    medium_uid: Optional[str] = os.getenv("MEDIUM_UID", None)
    
    # Option 2: Full cookie string
    medium_cookie: Optional[str] = os.getenv("MEDIUM_COOKIE", None)
    
    # ============================================
    # API CONFIGURATION
    # ============================================
    
    # API host and port
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    
    # Debug mode
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # CORS settings
    cors_origins: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://localhost:3000").split(",")
    
    # ============================================
    # LOGGING CONFIGURATION
    # ============================================
    
    # Log level
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Log file path
    log_file: Optional[str] = os.getenv("LOG_FILE", None)
    
    # ============================================
    # CACHE CONFIGURATION
    # ============================================
    
    # Cache TTL in seconds
    cache_ttl: int = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes
    
    # Enable caching
    enable_cache: bool = os.getenv("ENABLE_CACHE", "true").lower() == "true"
    
    # ============================================
    # RATE LIMITING
    # ============================================
    
    # Rate limit per minute
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    # ============================================
    # DERIVED PATHS
    # ============================================
    
    @property
    def stories_root_path(self) -> Path:
        """Get stories root as Path object"""
        return Path(self.stories_root)
    
    @property
    def data_dir_path(self) -> Path:
        """Get data directory as Path object"""
        return Path(self.data_dir)
    
    @property
    def stories_json_path(self) -> Path:
        """Get stories.json path"""
        return self.data_dir_path / "stories.json"
    
    @property
    def calendar_json_path(self) -> Path:
        """Get publishing-calendar.json path"""
        return self.data_dir_path / "publishing-calendar.json"
    
    @property
    def calendar_md_path(self) -> Path:
        """Get publishing-calendar.md path"""
        return self.data_dir_path / "publishing-calendar.md"
    
    @property
    def app_status_path(self) -> Path:
        """Get appstatus.json path"""
        return self.data_dir_path / "appstatus.json"
    
    # ============================================
    # VALIDATION METHODS
    # ============================================
    
    def validate(self) -> bool:
        """Validate configuration settings"""
        errors = []
        
        # Check if stories root exists
        if not self.stories_root_path.exists():
            errors.append(f"Stories root does not exist: {self.stories_root}")
        
        # Check if data directory can be created
        try:
            self.data_dir_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create data directory: {e}")
        
        # Validate series spacing
        if self.default_series_spacing_days < 1 or self.default_series_spacing_days > 30:
            errors.append("Series spacing must be between 1 and 30 days")
        
        # Validate stories per week
        if self.default_stories_per_week < 1 or self.default_stories_per_week > 7:
            errors.append("Stories per week must be between 1 and 7")
        
        # Validate preferred days
        valid_days = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
        for day in self.preferred_publish_days:
            if day not in valid_days:
                errors.append(f"Invalid preferred day: {day}")
        
        if errors:
            for error in errors:
                print(f"⚠️ Config validation error: {error}")
            return False
        
        return True
    
    # ============================================
    # DISPLAY METHODS
    # ============================================
    
    def display(self) -> str:
        """Return a formatted string of current settings"""
        lines = [
            "=" * 50,
            "Story Manager Configuration",
            "=" * 50,
            f"Stories Root: {self.stories_root}",
            f"Data Directory: {self.data_dir}",
            "",
            "Calendar Settings:",
            f"  Series Spacing: {self.default_series_spacing_days} days",
            f"  Stories Per Week: {self.default_stories_per_week}",
            f"  Preferred Days: {', '.join(self.preferred_publish_days)}",
            f"  Start Date: {self.start_date or 'Not set'}",
            "",
            "Medium API:",
            f"  Username: {self.medium_username}",
            f"  Authenticated: {bool(self.medium_sid and self.medium_uid) or bool(self.medium_cookie)}",
            "",
            "API Settings:",
            f"  Host: {self.api_host}",
            f"  Port: {self.api_port}",
            f"  Debug: {self.debug}",
            f"  Log Level: {self.log_level}",
            "",
            "Cache:",
            f"  Enabled: {self.enable_cache}",
            f"  TTL: {self.cache_ttl} seconds",
            "=" * 50
        ]
        return "\n".join(lines)


# Create global settings instance
settings = Settings()

# Validate settings on import
if not settings.validate():
    print("⚠️ Configuration validation failed. Some features may not work correctly.")


def get_settings() -> Settings:
    """Get the global settings instance"""
    return settings


def reload_settings():
    """Reload settings from environment variables"""
    global settings
    settings = Settings()
    settings.validate()
    return settings


# ============================================
# ENVIRONMENT VARIABLE HELPERS
# ============================================

def is_development() -> bool:
    """Check if running in development mode"""
    return os.getenv("ENV", "development") == "development"


def is_production() -> bool:
    """Check if running in production mode"""
    return os.getenv("ENV", "development") == "production"


def get_env() -> str:
    """Get current environment"""
    return os.getenv("ENV", "development")


# Print configuration on import (only in debug mode)
if settings.debug:
    print(settings.display())