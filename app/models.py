from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from enum import Enum

class StoryStatus(str, Enum):
    DRAFT = "Draft"
    PUBLISHED = "Published"
    ARCHIVED = "Archived"

class StoryCreate(BaseModel):
    name: str
    folder: Optional[str] = None
    series: Optional[str] = None
    tags: List[str] = []
    read_time: Optional[int] = None
    notes: Optional[str] = ""

class StoryUpdate(BaseModel):
    name: Optional[str] = None
    folder: Optional[str] = None
    series: Optional[str] = None
    status: Optional[StoryStatus] = None
    published_date: Optional[str] = None
    tags: Optional[List[str]] = None
    read_time: Optional[int] = None
    medium_url: Optional[str] = None
    notes: Optional[str] = None

class StoryResponse(BaseModel):
    key: str
    name: str
    folder: str
    series: Optional[str]
    rel_path: str
    status: str
    published_date: Optional[str]
    created_date: str
    tags: List[str]
    read_time: Optional[int]
    medium_url: Optional[str]
    notes: str

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