"""
Story Manager - Data Models
Complete mapping with Medium API field sources
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class StoryStatus(str, Enum):
    """Story status values"""
    DRAFT = "Draft"
    DONE = "Done"
    READY = "Ready"
    PUBLISHED = "Published"


# ============================================
# STORY CREATE MODEL
# ============================================

class StoryCreate(BaseModel):
    """
    Create a new story - User input fields only
    No Medium API fields here
    """
    name: str                                    # User input - Story title
    folder: Optional[str] = None                 # User input / Auto from path
    series: Optional[str] = None                 # User input - Series name
    status: Optional[str] = "Draft"              # User input - Draft/Ready/Done/Published
    tags: List[str] = []                         # User input - Comma separated tags
    read_time: Optional[int] = None              # User input - Estimated reading time
    reads: int = 0                               # User input - Fallback value
    created_date: Optional[str] = None           # User input / Auto - Creation date
    notes: Optional[str] = ""                    # User input - Internal notes
    medium_url: Optional[str] = None             # User input - Full Medium URL
    medium_first_published: Optional[str] = None # API: data.post.firstPublishedAt
    medium_publication: Optional[str] = None     # User input - Publication name
    medium_reading_time: Optional[int] = None    # API: data.post.readingTime


# ============================================
# STORY UPDATE MODEL
# ============================================

class StoryUpdate(BaseModel):
    """
    Update story - User input + API fields
    Each field includes source comment
    """
    
    # ==========================================
    # USER INPUT FIELDS
    # ==========================================
    name: Optional[str] = None                      # User input
    folder: Optional[str] = None                    # User input / Auto
    series: Optional[str] = None                    # User input
    status: Optional[StoryStatus] = None            # User input
    published_date: Optional[str] = None            # User input - YYYY-MM-DD
    created_date: Optional[str] = None              # User input / Auto
    tags: Optional[List[str]] = None                # User input
    read_time: Optional[int] = None                 # User input
    reads: Optional[int] = None                     # User input (fallback)
    medium_url: Optional[str] = None                # User input
    notes: Optional[str] = None                     # User input
    medium_publication: Optional[str] = None        # User input
    bookmarked: Optional[bool] = None               # User input (UI toggle)
    
    # LinkedIn Marketing (User input)
    linkedin_status: Optional[str] = None           # User input - scheduled/posted/null
    linkedin_timestamp: Optional[str] = None        # User input - ISO timestamp
    linkedin_impressions: Optional[int] = None      # User input
    linkedin_url: Optional[str] = None              # User input
    
    # Leaderboard (User input / UI toggle)
    leaderboard: Optional[bool] = None              # User input (UI toggle)
    leaderboard_nanos: Optional[int] = None         # User input - Earnings in nanos
    leaderboard_lifetime_nanos: Optional[int] = None # User input
    
    # ==========================================
    # FIELDS FROM MEDIUM API - POST METADATA
    # Source: POST https://medium.com/_/graphql
    # Operation: useStatsPostNewChartDataQuery
    # Response path: data.post.*
    # ==========================================
    medium_first_published: Optional[str] = None    # API: data.post.firstPublishedAt
    medium_reading_time: Optional[int] = None       # API: data.post.readingTime
    word_count: Optional[int] = None                # API: data.post.wordCount
    medium_title: Optional[str] = None              # API: data.post.title
    medium_last_updated: Optional[str] = None       # API: data.post.updatedAt
    medium_author: Optional[str] = None             # API: data.post.creator.name
    medium_tags: Optional[List[str]] = None         # API: data.post.tags[].name
    medium_topics: Optional[List[str]] = None       # API: data.post.topics[].name
    medium_subtitle: Optional[str] = None           # API: data.post.subtitle
    
    # ==========================================
    # FIELDS FROM MEDIUM API - MONTHLY STATS
    # Source: POST https://medium.com/_/graphql
    # Operation: useStatsPostNewChartDataQuery
    # Response path: data.postStatsDailyBundle.buckets[]
    # ==========================================
    medium_member_reads: Optional[int] = None       # API: readersThatReadCount where membershipType="MEMBER"
    medium_member_views: Optional[int] = None       # API: readersThatViewedCount where membershipType="MEMBER"
    medium_nonmember_reads: Optional[int] = None    # API: readersThatReadCount where membershipType="NONMEMBER"
    medium_nonmember_views: Optional[int] = None    # API: readersThatViewedCount where membershipType="NONMEMBER"
    claps: Optional[int] = None                     # API: readersThatClappedCount (sum over all buckets)
    responses: Optional[int] = None                 # API: readersThatRepliedCount (sum over all buckets)
    medium_highlights: Optional[int] = None         # API: readersThatHighlightedCount (sum over all buckets)
    medium_new_followers: Optional[int] = None      # API: readersThatInitiallyFollowedAuthorFromThisPostCount
    view_count: Optional[int] = None                # Calculated: member_views + nonmember_views
    read_ratio: Optional[float] = None              # Calculated: (total_reads / total_views) * 100
    medium_member_read_percentage: Optional[float] = None  # Calculated: (member_reads / total_reads) * 100
    
    # Monthly earnings (sum of daily earnings)
    medium_earnings: Optional[float] = None         # API: sum(data.post.earnings.dailyEarnings[].amount)
    
    # ==========================================
    # FIELDS FROM MEDIUM API - LIFETIME STATS
    # Source: POST https://medium.com/_/graphql
    # Operation: StatsPostFunnelQuery
    # Response path: data.postStatsTotalBundle.*
    # ==========================================
    lifetime_reads: Optional[int] = None            # API: data.postStatsTotalBundle.readersCount
    lifetime_views: Optional[int] = None            # API: data.postStatsTotalBundle.viewersCount
    presentation_count: Optional[int] = None        # API: data.postStatsTotalBundle.presentationCount
    feed_click_through_rate: Optional[float] = None # API: data.postStatsTotalBundle.feedClickThroughRate
    
    # ==========================================
    # OTHER FIELDS (Not from Medium API)
    # ==========================================
    bookmarks: Optional[int] = None                 # API: data.post.distribution.totalBookmarkCount
    fan_count: Optional[int] = None                 # Calculated / Not used
    medium_total_views: Optional[int] = None        # Deprecated, use view_count
    medium_claps: Optional[int] = None              # Deprecated, use claps
    medium_replies: Optional[int] = None            # Deprecated, use responses
    last_stats_update: Optional[str] = None         # System: timestamp of last stats update
    medium_stats_data: Optional[Dict] = None        # System: raw API response cache
    medium_stats_updated: Optional[str] = None      # System: timestamp of raw data
    lifetime_stats_data: Optional[Dict] = None      # System: raw lifetime API response cache
    lifetime_stats_updated: Optional[str] = None    # System: timestamp of lifetime data
    medium_read_ratio: Optional[float] = None       # Deprecated, use read_ratio
    lifetime_claps: Optional[int] = None            # Not available from API, user input only
    lifetime_tags: Optional[List[str]] = None       # User input / Not from API
    lifetime_topics: Optional[List[str]] = None     # User input / Not from API


# ============================================
# STORY RESPONSE MODEL
# ============================================

class StoryResponse(BaseModel):
    """
    Complete story response - Combination of user input + API data
    Used for GET /stories/list, GET /stories/list/{yearmonth}, GET /stories/story/{key}
    """
    key: str                                         # Auto: folder/name
    name: str                                        # User input
    folder: str                                      # Auto
    series: Optional[str] = None                     # User input
    raw_path: Optional[str] = None                   # Auto
    rel_path: str                                    # Auto
    status: str                                      # User input
    published_date: Optional[str] = None             # User input
    created_date: str                                # User input / Auto
    last_updated: Optional[str] = None               # System
    tags: Optional[List[str]] = None                 # User input
    read_time: Optional[int] = None                  # User input
    reads: Optional[int] = 0                         # API: monthly total from monthly db
    medium_url: Optional[str] = None                 # User input
    notes: Optional[str] = ""                        # User input
    linkedin_status: Optional[str] = None            # User input
    linkedin_timestamp: Optional[str] = None         # User input
    linkedin_impressions: Optional[int] = 0          # User input
    linkedin_url: Optional[str] = None               # User input
    claps: Optional[int] = 0                         # API: readersThatClappedCount
    responses: Optional[int] = 0                     # API: readersThatRepliedCount
    bookmarks: Optional[int] = 0                     # API: data.post.distribution.totalBookmarkCount
    view_count: Optional[int] = 0                    # Calculated: member_views + nonmember_views
    read_ratio: Optional[float] = 0                  # Calculated: (reads / views) * 100
    medium_reading_time: Optional[int] = 0           # API: data.post.readingTime
    fan_count: Optional[int] = 0                     # Not used
    medium_first_published: Optional[str] = None     # API: data.post.firstPublishedAt
    medium_last_updated: Optional[str] = None        # API: data.post.updatedAt
    medium_tags: Optional[List[str]] = None          # API: data.post.tags[].name
    medium_topics: Optional[List[str]] = None        # API: data.post.topics[].name
    word_count: Optional[int] = 0                    # API: data.post.wordCount
    medium_title: Optional[str] = None               # API: data.post.title
    medium_subtitle: Optional[str] = None            # API: data.post.subtitle
    medium_author: Optional[str] = None              # API: data.post.creator.name
    medium_publication: Optional[str] = None         # User input
    last_stats_update: Optional[str] = None          # System
    bookmarked: Optional[bool] = False               # User input
    medium_member_reads: Optional[int] = 0           # API: readersThatReadCount (MEMBER)
    medium_member_views: Optional[int] = 0           # API: readersThatViewedCount (MEMBER)
    medium_nonmember_reads: Optional[int] = 0        # API: readersThatReadCount (NONMEMBER)
    medium_nonmember_views: Optional[int] = 0        # API: readersThatViewedCount (NONMEMBER)
    medium_total_views: Optional[int] = 0            # Deprecated
    medium_claps: Optional[int] = 0                  # Deprecated
    medium_replies: Optional[int] = 0                # Deprecated
    medium_highlights: Optional[int] = 0             # API: readersThatHighlightedCount
    medium_new_followers: Optional[int] = 0          # API: readersThatInitiallyFollowedAuthorFromThisPostCount
    medium_read_ratio: Optional[float] = 0           # Deprecated
    medium_member_read_percentage: Optional[float] = 0  # Calculated
    medium_stats_data: Optional[Dict] = None         # System
    medium_stats_updated: Optional[str] = None       # System
    
    # Lifetime stats from API
    lifetime_reads: Optional[int] = 0                # API: data.postStatsTotalBundle.readersCount
    lifetime_claps: Optional[int] = 0                # Not from API
    lifetime_views: Optional[int] = 0                # API: data.postStatsTotalBundle.viewersCount
    presentation_count: Optional[int] = 0            # API: data.postStatsTotalBundle.presentationCount
    feed_click_through_rate: Optional[float] = 0     # API: data.postStatsTotalBundle.feedClickThroughRate
    medium_earnings: Optional[float] = 0             # API: sum(data.post.earnings.dailyEarnings[].amount)
    lifetime_tags: Optional[List[str]] = None        # User input
    lifetime_topics: Optional[List[str]] = None      # User input
    lifetime_stats_data: Optional[Dict] = None       # System
    lifetime_stats_updated: Optional[str] = None     # System
    
    # Leaderboard
    leaderboard: Optional[bool] = False              # User input
    leaderboard_nanos: Optional[int] = 0             # User input
    leaderboard_lifetime_nanos: Optional[int] = 0    # User input

    class Config:
        from_attributes = True


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