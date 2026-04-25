from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class StoryStatus(str, Enum):
    """Story status values"""
    DRAFT = "Draft"
    DONE = "Done"
    READY = "Ready"
    PUBLISHED = "Published"
    PUBLISHED_DUE = "Published Due"


class LinkedInPostType(str, Enum):
    """LinkedIn post type"""
    ARTICLE = "Article"
    POST = "Post"


# ============================================
# MEDIUM POST MODELS (for nested "medium" object)
# ============================================

class Stats(BaseModel):
    """Statistics for a specific period"""
    period: str = "total"
    presentations: int = 0
    views: int = 0
    reads: int = 0
    claps: int = 0
    responses: int = 0
    medium_member_reads: int = 0
    medium_member_views: int = 0
    medium_nonmember_reads: int = 0
    medium_nonmember_views: int = 0
    medium_read_ratio: float = 0
    medium_member_read_percentage: float = 0
    medium_new_followers: int = 0
    medium_highlights: int = 0
    feedClickThroughRate: int = 0


class Earning(BaseModel):
    """Earnings for a specific period"""
    period: str = "total"
    currencyCode: str = "USD"
    units: int = 0
    nanos: int = 0
    amount: float =0.0;


class Creator(BaseModel):
    """Creator/author information"""
    id: str
    username: str
    name: str
    bio: str = ""
    imageId: Optional[str] = None
    twitterScreenName: Optional[str] = None
    createdAt: Optional[int] = None


class Collection(BaseModel):
    """Publication/collection information"""
    id: str
    name: str
    slug: str
    domain: str
    subscriberCount: int = 0
    createdAt: int = 0


class Tag(BaseModel):
    """Tag information - can be string or object with id"""
    id: str
    
    @classmethod
    def from_string(cls, tag_str: str) -> "Tag":
        """Create Tag from string"""
        return cls(id=tag_str)


class MediumPost(BaseModel):
    """Complete Medium post from API - stored under story["medium"]"""
    id: str
    __typename: str = "Post"
    title: str
    uniqueSlug: str
    mediumUrl: str
    createdAt: int
    updatedAt: int
    firstPublishedAt: Optional[int] = None
    totalStats: Optional[Stats] = None
    monthlyStats: List[Stats] = []
    readingTime: float = 0
    wordCount: int = 0
    clapCount: int = 0
    responsesCount: int = 0
    voterCount: int = 0
    isLocked: bool = False
    visibility: str = "LOCKED"
    isSeries: bool = False
    isShortform: bool = False
    firstBoostedAt: Optional[int] = None
    license: str = "ALL_RIGHTS_RESERVED"
    tags: List[str] = []  # List of tag strings
    totalEarnings: Optional[Earning] = None
    monthlyEarnings: List[Earning] = []
    creator: Optional[Creator] = None
    collection: Optional[Collection] = None


# ============================================
# LINKEDIN MODEL
# ============================================

class LinkedIn(BaseModel):
    """LinkedIn marketing data - nested inside Story"""
    type: LinkedInPostType = LinkedInPostType.ARTICLE
    status: Optional[str] = None  # "scheduled", "posted", or None
    timestamp: Optional[str] = None
    impressions: int = 0
    url: Optional[str] = None


# ============================================
# STORY MODEL - Primary storage (stories.json)
# ============================================

class Story(BaseModel):
    """Complete story - main storage model"""
    # Core identification
    uniqueSlug: str
    title: str
    key: Optional[str] = None  # Derived from folder/title
    
    # Organization
    folder: str = "Miscellaneous"
    series: Optional[str] = None
    
    # Status and dates
    status: str = "Draft"
    createdDate: Optional[str] = None
    publishedDate: Optional[str] = None
    publishedDueDate: Optional[str] = None
    lastUpdated: Optional[str] = None
    
    # Content metadata
    notes: str = ""
    tags: Optional[List[str]] = None
    word_count: Optional[int] = None
    read_time: Optional[int] = None
    
    # Flags
    bookmarked: bool = False
    leaderboard: bool = False
    
    # Medium API data (nested)
    medium: Optional[MediumPost] = None
    
    # LinkedIn marketing data (nested)
    linkedin: Optional[LinkedIn] = None
    
    # Legacy fields (for backward compatibility)
    name: Optional[str] = None  # Alias for title
    medium_url: Optional[str] = None
    medium_publication: Optional[str] = None
    medium_first_published: Optional[str] = None
    medium_reading_time: Optional[int] = None
    medium_new_followers: Optional[int] = 0
    lifetime_reads: Optional[int] = 0
    lifetime_views: Optional[int] = 0
    lifetime_claps: Optional[int] = 0
    presentation_count: Optional[int] = 0
    feed_click_through_rate: Optional[float] = 0
    
    # Legacy LinkedIn fields (moved to nested object)
    linkedin_status: Optional[str] = None
    linkedin_timestamp: Optional[str] = None
    linkedin_impressions: Optional[int] = 0
    linkedin_url: Optional[str] = None
    
    # Computed fields (not stored)
    reads: Optional[int] = 0
    view_count: Optional[int] = 0
    claps: Optional[int] = 0
    responses: Optional[int] = 0
    
    def dict(self, *args, **kwargs):
        """Override dict to handle nested objects properly"""
        result = super().dict(*args, **kwargs)
        # Remove None values for cleaner storage
        return {k: v for k, v in result.items() if v is not None}


class StoryCreate(BaseModel):
    """Create a new story"""
    uniqueSlug: str
    title: str
    folder: Optional[str] = "Miscellaneous"
    series: Optional[str] = None
    status: Optional[str] = "Draft"
    createdDate: Optional[str] = None
    publishedDate: Optional[str] = None
    publishedDueDate: Optional[str] = None
    notes: Optional[str] = ""
    tags: Optional[List[str]] = None
    bookmarked: bool = False
    leaderboard: bool = False
    medium_url: Optional[str] = None
    medium_publication: Optional[str] = None
    medium_first_published: Optional[str] = None
    medium_reading_time: Optional[int] = None
    read_time: Optional[int] = None
    word_count: Optional[int] = None
    linkedin_status: Optional[str] = None
    linkedin_timestamp: Optional[str] = None
    linkedin_impressions: Optional[int] = 0
    linkedin_url: Optional[str] = None


class StoryUpdate(BaseModel):
    """Update a story"""
    uniqueSlug: Optional[str] = None
    title: Optional[str] = None
    folder: Optional[str] = None
    series: Optional[str] = None
    status: Optional[str] = None
    publishedDate: Optional[str] = None
    publishedDueDate: Optional[str] = None
    createdDate: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    bookmarked: Optional[bool] = None
    leaderboard: Optional[bool] = None
    medium_url: Optional[str] = None
    medium_publication: Optional[str] = None
    medium_first_published: Optional[str] = None
    medium_reading_time: Optional[int] = None
    read_time: Optional[int] = None
    word_count: Optional[int] = None
    linkedin_status: Optional[str] = None
    linkedin_timestamp: Optional[str] = None
    linkedin_impressions: Optional[int] = None
    linkedin_url: Optional[str] = None
    lifetime_reads: Optional[int] = None
    lifetime_views: Optional[int] = None
    lifetime_claps: Optional[int] = None
    presentation_count: Optional[int] = None
    feed_click_through_rate: Optional[float] = None
    leaderboard_nanos: Optional[int] = None
    lastUpdated: Optional[str] = None
    last_stats_update: Optional[str] = None


# ============================================
# CALENDAR MODELS
# ============================================

class CalendarSettingsUpdate(BaseModel):
    """Update calendar settings"""
    series_spacing_days: Optional[int] = Field(None, ge=5, le=14)
    stories_per_week: Optional[int] = Field(None, ge=1, le=7)
    preferred_publish_days: Optional[List[str]] = None
    start_date: Optional[str] = None


class CalendarEntry(BaseModel):
    """Calendar entry"""
    date: str
    weekday: str
    story_key: str
    name: str
    series: Optional[str] = None
    part: Optional[int] = None
    read_time: Optional[int] = None


class CalendarResponse(BaseModel):
    """Calendar response"""
    generated: str
    summary: Dict[str, Any]
    schedule: List[CalendarEntry] = []


# ============================================
# SERIES MODELS
# ============================================

class SeriesCreate(BaseModel):
    """Create a new series"""
    name: str
    spacing_days: Optional[int] = 7


class SeriesUpdate(BaseModel):
    """Update series"""
    name: Optional[str] = None
    spacing_days: Optional[int] = None


class SeriesResponse(BaseModel):
    """Series response"""
    name: str
    total_stories: int
    published: int
    spacing_days: int
    stories: List[str] = []


# ============================================
# RESPONSE MODELS
# ============================================

class StoryResponse(BaseModel):
    """API response for a story"""
    success: bool
    story: Optional[Story] = None
    message: Optional[str] = None


class StoriesListResponse(BaseModel):
    """API response for list of stories"""
    success: bool
    stories: List[Story] = []
    total: int = 0
    message: Optional[str] = None


# ============================================
# IMPORT LOG MODEL
# ============================================

class ImportLog(BaseModel):
    """Import log for tracking Medium API imports"""
    id: str
    timestamp: str
    username: str
    period: str
    total_posts: int
    new_stories: int
    updated_stories: int
    status: str  # "success", "failed", "partial"
    error_message: Optional[str] = None


# ============================================
# MONTHLY STORAGE MODELS (legacy - kept for compatibility)
# ============================================

class MonthlyStats(BaseModel):
    """Monthly statistics for a story (stored in stories-YYYY-MM.json)"""
    title: Optional[str] = None
    medium_url: Optional[str] = None
    reads: int = 0
    view_count: int = 0
    claps: int = 0
    responses: int = 0
    medium_member_reads: int = 0
    medium_member_views: int = 0
    medium_nonmember_reads: int = 0
    medium_nonmember_views: int = 0
    medium_read_ratio: float = 0
    medium_member_read_percentage: float = 0
    medium_new_followers: int = 0
    medium_highlights: int = 0
    leaderboard: bool = False
    leaderboard_nanos: int = 0
    medium_earnings: int = 0
    published_date: Optional[str] = None
    status: Optional[str] = None
    medium_first_published: Optional[str] = None
    medium_reading_time: Optional[int] = None
    last_stats_update: Optional[str] = None


class MonthlyStorageData(BaseModel):
    """Structure for stories-YYYY-MM.json files"""
    month: str
    last_updated: str
    stories: Dict[str, MonthlyStats] = {}


# ============================================
# APP STATUS MODELS
# ============================================

class AppStatus(BaseModel):
    """Application status stored in appstatus.json"""
    leaderboard_month: Optional[str] = None
    current_mode: str = "dashboard"  # "dashboard" or "month"
    current_month: Dict[str, int] = Field(default_factory=lambda: {"year": 2026, "month": 4})
    medium_username: Optional[str] = None
    last_stats_fetch: Optional[str] = None
    is_importing: bool = False
    import_progress: int = 0
    import_total: int = 0
    import_current: int = 0
    import_started_at: Optional[str] = None
    import_completed_at: Optional[str] = None
    import_last_error: Optional[str] = None
    last_updated: Optional[str] = None
# This file includes:

# 1. **`MediumPost`** - Complete model matching `output.json` structure with nested objects
# 2. **`TotalStats`** - For total statistics (presentations, views, reads)
# 3. **`Earnings`** and **`EarningsAmount`** - For earnings data
# 4. **`Creator`** and **`Collection`** - For author and publication info
# 5. **`Tag`** - For tag information
# 6. **`MonthlyStats`** - For monthly statistics storage
# 7. **`Story`** - Main story model with backward compatibility fields
# 8. **`StoryCreate`** and **`StoryUpdate`** - For CRUD operations
# 9. **`CalendarSettingsUpdate`**, **`CalendarEntry`**, **`CalendarResponse`** - Calendar models
# 10. **`SeriesCreate`**, **`SeriesUpdate`**, **`SeriesResponse`** - Series models
# 11. **`ImportLog`** - For tracking imports
# 12. **`MonthlyStorageData`** - For monthly file structure
# 13. **`AppStatus`** - For application status
