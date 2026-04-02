from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class StoryStatus(str, Enum):
    DRAFT = "Draft"
    DONE = "Done"
    READY = "Ready"
    PUBLISHED = "Published"

class StoryCreate(BaseModel):
    name: str
    folder: Optional[str] = None
    series: Optional[str] = None
    tags: List[str] = []
    read_time: Optional[int] = None
    reads: int = 0
    created_date: Optional[str] = None
    notes: Optional[str] = ""

class StoryUpdate(BaseModel):
    name: Optional[str] = None
    folder: Optional[str] = None
    series: Optional[str] = None
    status: Optional[StoryStatus] = None
    published_date: Optional[str] = None
    created_date: Optional[str] = None
    tags: Optional[List[str]] = None
    read_time: Optional[int] = None
    reads: Optional[int] = None
    medium_url: Optional[str] = None
    notes: Optional[str] = None
    linkedin_status: Optional[str] = None
    linkedin_timestamp: Optional[str] = None
    linkedin_impressions: Optional[int] = None
    linkedin_url: Optional[str] = None
    claps: Optional[int] = None
    responses: Optional[int] = None
    bookmarks: Optional[int] = None
    view_count: Optional[int] = None
    read_ratio: Optional[float] = None
    medium_reading_time: Optional[int] = None
    fan_count: Optional[int] = None
    medium_first_published: Optional[str] = None
    medium_last_updated: Optional[str] = None
    medium_tags: Optional[List[str]] = None
    medium_topics: Optional[List[str]] = None
    word_count: Optional[int] = None
    medium_title: Optional[str] = None
    medium_subtitle: Optional[str] = None
    medium_author: Optional[str] = None
    medium_publication: Optional[str] = None
    last_stats_update: Optional[str] = None
    bookmarked: Optional[bool] = None
    # Add to StoryUpdate class:
    medium_member_reads: Optional[int] = None
    medium_member_views: Optional[int] = None
    medium_nonmember_reads: Optional[int] = None
    medium_nonmember_views: Optional[int] = None
    medium_total_views: Optional[int] = None
    medium_claps: Optional[int] = None
    medium_replies: Optional[int] = None
    medium_highlights: Optional[int] = None
    medium_new_followers: Optional[int] = None
    medium_read_ratio: Optional[float] = None
    medium_member_read_percentage: Optional[float] = None
    medium_stats_data: Optional[Dict] = None
    medium_stats_updated: Optional[str] = None


class StoryResponse(BaseModel):
    key: str
    name: str
    folder: str
    series: Optional[str]
    raw_path: Optional[str] = None
    rel_path: str
    status: str
    published_date: Optional[str]
    created_date: str
    last_updated: Optional[str] = None
    tags: List[str]
    read_time: Optional[int]
    reads: int = 0
    medium_url: Optional[str]
    notes: str
    linkedin_status: Optional[str] = None
    linkedin_timestamp: Optional[str] = None
    linkedin_impressions: Optional[int] = 0
    linkedin_url: Optional[str] = None
    claps: Optional[int] = 0
    responses: Optional[int] = 0
    bookmarks: Optional[int] = 0
    view_count: Optional[int] = 0
    read_ratio: Optional[float] = 0
    medium_reading_time: Optional[int] = 0
    fan_count: Optional[int] = 0
    medium_first_published: Optional[str] = None
    medium_last_updated: Optional[str] = None
    medium_tags: Optional[List[str]] = []
    medium_topics: Optional[List[str]] = []
    word_count: Optional[int] = 0
    medium_title: Optional[str] = None
    medium_subtitle: Optional[str] = None
    medium_author: Optional[str] = None
    medium_publication: Optional[str] = None
    last_stats_update: Optional[str] = None
    bookmarked: bool = False
    # Add to StoryResponse class:
    medium_member_reads: int = 0
    medium_member_views: int = 0
    medium_nonmember_reads: int = 0
    medium_nonmember_views: int = 0
    medium_total_views: int = 0
    medium_claps: int = 0
    medium_replies: int = 0
    medium_highlights: int = 0
    medium_new_followers: int = 0
    medium_read_ratio: float = 0
    medium_member_read_percentage: float = 0
    medium_stats_data: Optional[Dict] = None
    medium_stats_updated: Optional[str] = None


class SeriesCreate(BaseModel):
    name: str
    spacing_days: Optional[int] = 7

class SeriesUpdate(BaseModel):
    name: Optional[str] = None
    spacing_days: Optional[int] = None

class SeriesResponse(BaseModel):
    name: str
    total_stories: int
    published: int
    spacing_days: int
    stories: List[str]

class CalendarSettingsUpdate(BaseModel):
    series_spacing_days: Optional[int] = Field(None, ge=5, le=14)
    stories_per_week: Optional[int] = Field(None, ge=1, le=7)
    preferred_publish_days: Optional[List[str]] = None
    start_date: Optional[str] = None

class CalendarEntry(BaseModel):
    date: str
    weekday: str
    story_key: str
    name: str
    series: Optional[str]
    part: Optional[int]
    read_time: Optional[int]

class CalendarResponse(BaseModel):
    generated: str
    summary: Dict[str, Any]
    schedule: List[CalendarEntry]