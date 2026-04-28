"""
Stories Router - Complete endpoints with uniqueSlug as primary key
"""


import io
from fastapi import APIRouter, HTTPException, Query, Form, UploadFile, File
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from urllib.parse import unquote
import urllib.request
import urllib.parse
import re
import json
from pathlib import Path
import subprocess
import base64
import os
import shutil
import tempfile
from PIL import Image, ImageDraw, ImageFont
from PIL import ImageOps
import piexif
from config import settings
from app.services.story_service import StoryService
from app.services.monthly_storage_service import MonthlyStorageService
from app.services.medium_api_service import get_medium_api_service
from app.services.app_status_service import AppStatusService
from app.models import StoryCreate, StoryUpdate, StoryResponse
from app.utils import (
    find_story_by_identifier,
    normalize_title,
    normalize_url,
    extract_post_id_from_url,
    calculate_percentages,
    get_current_year_month
)

from app.services.file_service import (
    load_stories_data, save_stories_data, scan_markdown_files,
    parse_series_number
)
from config import settings

logger = logging.getLogger(__name__)
# # Try to import weasyprint, fallback to alternative
# try:
#     from weasyprint import HTML, CSS
#     WEASYPRINT_AVAILABLE = True
# except ImportError:
#     WEASYPRINT_AVAILABLE = False
#     logger.warning("weasyprint not available, table rendering will use alternative method")

# # Try to import markdown
# try:
#     import markdown
#     MARKDOWN_AVAILABLE = True
# except ImportError:
#     MARKDOWN_AVAILABLE = False

# Import Playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Install with: pip install playwright && playwright install chromium")
        
router = APIRouter()


# ============================================
# HELPER FUNCTIONS
# ============================================

def build_story_response(story, monthly_stats: dict) -> dict:
    """Build unified story response object"""
    member_reads = monthly_stats.get("medium_member_reads", 0)
    nonmember_reads = monthly_stats.get("medium_nonmember_reads", 0)
    total_reads = member_reads + nonmember_reads
    reads_percent = round((member_reads / total_reads) * 100, 1) if total_reads > 0 else 0
    
    member_views = monthly_stats.get("medium_member_views", 0)
    nonmember_views = monthly_stats.get("medium_nonmember_views", 0)
    total_views = member_views + nonmember_views
    views_percent = round((member_views / total_views) * 100, 1) if total_views > 0 else 0
    
    return {
        "key": story.key,
        "uniqueSlug": story.uniqueSlug,
        "name": story.name,
        "title": story.title,
        "series": story.series,
        "status": story.status or "Draft",
        "published_date": story.published_date,
        "created_date": story.created_date,
        "bookmarked": story.bookmarked or False,
        "leaderboard": story.leaderboard or False,
        "linkedin_status": story.linkedin_status,
        "linkedin_impressions": story.linkedin_impressions or 0,
        "linkedin_url": story.linkedin_url,
        "member_reads": member_reads,
        "nonmember_reads": nonmember_reads,
        "reads": total_reads,
        "reads_percent": reads_percent,
        "member_views": member_views,
        "nonmember_views": nonmember_views,
        "views": total_views,
        "views_percent": views_percent,
        "claps": monthly_stats.get("claps", 0),
        "responses": monthly_stats.get("responses", 0),
        "leaderboard_nanos": monthly_stats.get("leaderboard_nanos", 0),
        "tags": story.tags or [],
        "notes": story.notes or "",
        "medium_url": story.medium_url,
        "medium_publication": story.medium_publication,
        "medium_first_published": story.medium_first_published,
        "linkedin_timestamp": story.linkedin_timestamp,
        "word_count": story.word_count or 0,
        "reading_time": story.medium_reading_time or story.read_time or 0,
        "presentation_count": story.presentation_count or 0,
        "lifetime_reads": story.lifetime_reads or 0,
        "lifetime_views": story.lifetime_views or 0,
        "lifetime_claps": story.lifetime_claps or 0,
        "feed_click_through_rate": story.feed_click_through_rate or 0,
        "medium_earnings": monthly_stats.get("medium_earnings", 0),
        "medium_new_followers": monthly_stats.get("medium_new_followers", 0),
        "medium_highlights": monthly_stats.get("medium_highlights", 0),
        "raw_path": story.raw_path,
        "rel_path": story.rel_path,
        "folder": story.folder,
        "last_updated": story.last_updated,
        "medium": story.medium.dict() if story.medium else None,
        "linkedin": story.linkedin.dict() if story.linkedin else None
    }


# ============================================
# LIST ENDPOINTS
# ============================================

"""
GET /api/stories/list
Description: Dashboard view - All stories from stories.json with nested medium and linkedin objects

curl -X GET "http://localhost:8000/api/stories/list" | jq '.'
"""
@router.get("/list")
async def get_dashboard_stories():
    """Get all stories with nested medium and linkedin objects."""
    try:
        year, month = get_current_year_month()
        
        monthly_data = await MonthlyStorageService.load_monthly_stats(year, month)
        monthly_stats_map = monthly_data.get("stories", {})
        
        all_stories = await StoryService.get_all_stories()
        
        available_months = await MonthlyStorageService.get_available_months()
        leaderboard_stories_set = set()
        for month_info in available_months:
            month_data = await MonthlyStorageService.load_monthly_stats(month_info["year"], month_info["month"])
            for story_key, story_data in month_data.get("stories", {}).items():
                if story_data.get("leaderboard", False):
                    leaderboard_stories_set.add(story_key)
        
        stories = []
        for story in all_stories:
            monthly_stats = monthly_stats_map.get(story.key, {})
            leaderboard = story.key in leaderboard_stories_set
            
            story_dict = story.dict()
            story_dict["reads"] = monthly_stats.get("reads", 0)
            story_dict["views"] = monthly_stats.get("view_count", 0)
            story_dict["claps"] = monthly_stats.get("claps", 0)
            story_dict["responses"] = monthly_stats.get("responses", 0)
            story_dict["member_reads"] = monthly_stats.get("medium_member_reads", 0)
            story_dict["member_views"] = monthly_stats.get("medium_member_views", 0)
            story_dict["nonmember_reads"] = monthly_stats.get("medium_nonmember_reads", 0)
            story_dict["nonmember_views"] = monthly_stats.get("medium_nonmember_views", 0)
            story_dict["medium_earnings"] = monthly_stats.get("medium_earnings", 0)
            story_dict["medium_new_followers"] = monthly_stats.get("medium_new_followers", 0)
            story_dict["leaderboard"] = leaderboard
            story_dict["leaderboard_nanos"] = monthly_stats.get("leaderboard_nanos", 0)
            
            stories.append(story_dict)
        
        return {
            "stories": stories,
            "total": len(stories),
            "scope": "All Time"
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/stories/list/{yearmonth}
Description: Month view - Stories from stories-{yearmonth}.json + lifetime stats

curl -X GET "http://localhost:8000/api/stories/list/2026-03" | jq '.'
"""
@router.get("/list/{yearmonth}")
async def get_month_stories(yearmonth: str):
    """Get stories for a specific month from monthly storage."""
    try:
        parts = yearmonth.split('-')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid yearmonth format. Use YYYY-MM")
        
        year = int(parts[0])
        month = int(parts[1])
        
        monthly_data = await MonthlyStorageService.load_monthly_stats(year, month)
        monthly_stories = monthly_data.get("stories", {})
        
        all_stories = await StoryService.get_all_stories()
        story_map = {s.key: s for s in all_stories}
        
        stories = []
        for story_key, monthly_stats in monthly_stories.items():
            story = story_map.get(story_key)
            
            member_reads = monthly_stats.get("medium_member_reads", 0)
            nonmember_reads = monthly_stats.get("medium_nonmember_reads", 0)
            total_reads = member_reads + nonmember_reads
            reads_percent = round((member_reads / total_reads) * 100, 1) if total_reads > 0 else 0
            
            member_views = monthly_stats.get("medium_member_views", 0)
            nonmember_views = monthly_stats.get("medium_nonmember_views", 0)
            total_views = member_views + nonmember_views
            views_percent = round((member_views / total_views) * 100, 1) if total_views > 0 else 0
            
            if story:
                stories.append({
                    "key": story.key,
                    "uniqueSlug": story.uniqueSlug,
                    "name": story.name,
                    "title": story.title,
                    "series": story.series,
                    "status": story.status or "Published",
                    "published_date": story.published_date,
                    "created_date": story.created_date,
                    "bookmarked": story.bookmarked or False,
                    "leaderboard": monthly_stats.get("leaderboard", False),
                    "linkedin_status": story.linkedin_status,
                    "linkedin_impressions": story.linkedin_impressions or 0,
                    "linkedin_url": story.linkedin_url,
                    "member_reads": member_reads,
                    "nonmember_reads": nonmember_reads,
                    "reads": total_reads,
                    "reads_percent": reads_percent,
                    "member_views": member_views,
                    "nonmember_views": nonmember_views,
                    "views": total_views,
                    "views_percent": views_percent,
                    "claps": monthly_stats.get("claps", 0),
                    "responses": monthly_stats.get("responses", 0),
                    "leaderboard_nanos": monthly_stats.get("leaderboard_nanos", 0),
                    "tags": story.tags or [],
                    "notes": story.notes or "",
                    "medium_url": story.medium_url,
                    "medium_publication": story.medium_publication,
                    "medium_first_published": story.medium_first_published,
                    "linkedin_timestamp": story.linkedin_timestamp,
                    "word_count": story.word_count or 0,
                    "reading_time": story.medium_reading_time or story.read_time or 0,
                    "presentation_count": story.presentation_count or 0,
                    "lifetime_reads": story.lifetime_reads or 0,
                    "lifetime_views": story.lifetime_views or 0,
                    "lifetime_claps": story.lifetime_claps or 0,
                    "feed_click_through_rate": story.feed_click_through_rate or 0,
                    "medium_earnings": monthly_stats.get("medium_earnings", 0)
                })
            else:
                stories.append({
                    "key": story_key,
                    "uniqueSlug": monthly_stats.get("unique_slug", story_key),
                    "name": monthly_stats.get("title", story_key),
                    "title": monthly_stats.get("title", story_key),
                    "series": None,
                    "status": "Published",
                    "published_date": None,
                    "created_date": None,
                    "bookmarked": False,
                    "leaderboard": monthly_stats.get("leaderboard", False),
                    "linkedin_status": None,
                    "linkedin_impressions": 0,
                    "linkedin_url": None,
                    "member_reads": member_reads,
                    "nonmember_reads": nonmember_reads,
                    "reads": total_reads,
                    "reads_percent": reads_percent,
                    "member_views": member_views,
                    "nonmember_views": nonmember_views,
                    "views": total_views,
                    "views_percent": views_percent,
                    "claps": monthly_stats.get("claps", 0),
                    "responses": monthly_stats.get("responses", 0),
                    "leaderboard_nanos": monthly_stats.get("leaderboard_nanos", 0),
                    "tags": [],
                    "notes": "",
                    "medium_url": monthly_stats.get("medium_url"),
                    "medium_publication": None,
                    "medium_first_published": None,
                    "linkedin_timestamp": None,
                    "word_count": 0,
                    "reading_time": 0,
                    "presentation_count": 0,
                    "lifetime_reads": 0,
                    "lifetime_views": 0,
                    "lifetime_claps": 0,
                    "feed_click_through_rate": 0,
                    "medium_earnings": monthly_stats.get("medium_earnings", 0)
                })
        
        return {"stories": stories, "total": len(stories), "scope": yearmonth}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting month stories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/stories/
Description: Get all stories (simple list)

curl -X GET "http://localhost:8000/api/stories/" | jq '.'
"""
@router.get("/")
async def get_all_stories_simple():
    """Get all stories in simple format"""
    try:
        all_stories = await StoryService.get_all_stories()
        return [
            {
                "key": s.key,
                "uniqueSlug": s.uniqueSlug,
                "name": s.name,
                "title": s.title,
                "status": s.status,
                "series": s.series,
                "reads": s.reads,
                "created_date": s.created_date,
                "published_date": s.published_date,
                "medium_url": s.medium_url,
                "bookmarked": s.bookmarked,
                "leaderboard": s.leaderboard
            }
            for s in all_stories
        ]
    except Exception as e:
        logger.error(f"Error getting all stories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# STORY ENDPOINTS - Using uniqueSlug as primary key
# ============================================

"""
GET /api/stories/story/{unique_slug}
Description: Get story by uniqueSlug

curl -X GET "http://localhost:8000/api/stories/story/Architectural%20Remediation%20Framework%3A%20Eliminating%20the%2012%20Silent%20Killers%20in%20.NET%2010%20Web%20APIs%20-%20Part%201" | jq '.'
"""
@router.get("/story/{name:path}")
async def get_story_by_slug(name: str):
    """Get story by uniqueSlug"""
    logger.error(name)
    try:
        decoded_slug = unquote(name)
        
        #story = await StoryService.get_story_by_unique_slug(decoded_slug)
        story = await StoryService.get_story_by_name(name)
        #logger.error(json.dumps(story, default=str, indent=2))
        #logger.error(json.dumps(dict(story), default=str))

        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found for uniqueSlug: {name}")
        
        now = datetime.now()
        monthly_stats = await MonthlyStorageService.get_story_monthly_stats(story.key, now.year, now.month) or {}
        
        return story  
        #return build_story_response(story, monthly_stats)
        

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting story by slug: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"""
PUT /api/stories/story/name/{name:path}
Description: Update story by name (used by edit-story.js)

curl -X PUT "http://localhost:8000/api/stories/story/name/Architectural%20Remediation%20Framework%3A%20Eliminating%20the%2012%20Silent%20Killers%20in%20.NET%2010%20Web%20APIs%20-%20Part%201" \
  -H "Content-Type: application/json" \
  -d '{"status":"Published","bookmarked":true}' | jq '.'
"""
@router.put("/story/{name:path}")
async def update_story_by_name(name: str, update_data: dict):
    """Update story by name"""
    try:
        decoded_name = unquote(name)
        
        story = await StoryService.get_story_by_name(decoded_name)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found for name: {decoded_name}")
        
        update = StoryUpdate(**update_data)
        updated_story = await StoryService.update_story(story.key, update)
        
        if not updated_story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        return {"success": True, "message": "Story updated", "story": updated_story.dict()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating story by name: {e}")
        raise HTTPException(status_code=500, detail=str(e))
"""
GET /api/stories/story/{unique_slug}
Description: Get story by uniqueSlug

curl -X GET "http://localhost:8000/api/stories/story/name/Architectural%20Remediation%20Framework%3A%20Eliminating%20the%2012%20Silent%20Killers%20in%20.NET%2010%20Web%20APIs%20-%20Part%201" | jq '.'
"""
@router.get("/story/name/{postId}:path")
async def get_story_by_name(name: str):
    """Get story by Name"""
    logger.error("name")
    try:
        decoded_slug = unquote(name)
        
        story = await StoryService.get_story_by_unique_slug(decoded_slug)
        #logger.error(json.dumps(story, default=str, indent=2))
        logger.error(json.dumps(dict(story), default=str))

        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found for uniqueSlug: {decoded_slug}")
        
        now = datetime.now()
        monthly_stats = await MonthlyStorageService.get_story_monthly_stats(story.key, now.year, now.month) or {}
        
        return story  
        #return build_story_response(story, monthly_stats)
        

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting story by slug: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"""
PUT /api/stories/story/{unique_slug}
Description: Update story by uniqueSlug

curl -X PUT "http://localhost:8000/api/stories/story/asp-net-core-filters-deep-dive-building-maintainable-web-apis-with-net-10-and-reactive-extensions-78cb972195da" \
  -H "Content-Type: application/json" \
  -d '{"bookmarked": true}' | jq '.'
"""
@router.put("/story/{unique_slug:path}")
async def update_story_by_slug(unique_slug: str, update_data: dict):
    """Update story by uniqueSlug"""
    try:
        decoded_slug = unquote(unique_slug)
        
        story = await StoryService.get_story_by_unique_slug(decoded_slug)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found for uniqueSlug: {decoded_slug}")
        
        update = StoryUpdate(**update_data)
        updated_story = await StoryService.update_story(story.key, update)
        
        if not updated_story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        return {"success": True, "message": "Story updated", "story": updated_story.dict()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating story by slug: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
DELETE /api/stories/story/{unique_slug}
Description: Delete story by uniqueSlug

curl -X DELETE "http://localhost:8000/api/stories/story/asp-net-core-filters-deep-dive-building-maintainable-web-apis-with-net-10-and-reactive-extensions-78cb972195da" | jq '.'
"""
@router.delete("/story/{unique_slug:path}")
async def delete_story_by_slug(unique_slug: str):
    """Delete story by uniqueSlug"""
    try:
        decoded_slug = unquote(unique_slug)
        
        story = await StoryService.get_story_by_unique_slug(decoded_slug)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found for uniqueSlug: {decoded_slug}")
        
        deleted = await StoryService.delete_story(story.key)
        if not deleted:
            raise HTTPException(status_code=404, detail="Story not found")
        
        available_months = await MonthlyStorageService.get_available_months()
        for month_info in available_months:
            await MonthlyStorageService.delete_story_from_month(
                story.key, month_info["year"], month_info["month"]
            )
        
        return {"success": True, "message": "Story deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting story by slug: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/stories/story/{unique_slug}/publish
Description: Mark a story as published by uniqueSlug

curl -X POST "http://localhost:8000/api/stories/story/asp-net-core-filters-deep-dive-building-maintainable-web-apis-with-net-10-and-reactive-extensions-78cb972195da/publish" \
  -H "Content-Type: application/json" \
  -d '{"medium_url": "https://medium.com/@username/post-title-123"}' | jq '.'
"""
@router.post("/story/{unique_slug:path}/publish")
async def publish_story_by_slug(unique_slug: str, publish_data: dict = None):
    """Mark a story as published by uniqueSlug"""
    try:
        decoded_slug = unquote(unique_slug)
        
        story = await StoryService.get_story_by_unique_slug(decoded_slug)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found for uniqueSlug: {decoded_slug}")
        
        medium_url = publish_data.get("medium_url") if publish_data else None
        
        updated_story = await StoryService.publish_story(story.key, medium_url)
        if not updated_story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        return {"success": True, "message": "Story marked as published"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing story by slug: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# STATS ENDPOINTS - Using uniqueSlug
# ============================================

"""
GET /api/stories/stats/{unique_slug}/{yearmonth}
Description: Get monthly stats by uniqueSlug

curl -X GET "http://localhost:8000/api/stories/stats/asp-net-core-filters-deep-dive/2026-03" | jq '.'
"""
@router.get("/stats/{unique_slug:path}/{yearmonth}")
async def get_story_stats_by_slug(unique_slug: str, yearmonth: str):
    """Get monthly stats by uniqueSlug"""
    try:
        parts = yearmonth.split('-')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid yearmonth format")
        year = int(parts[0])
        month = int(parts[1])
        
        decoded_slug = unquote(unique_slug)
        story = await StoryService.get_story_by_unique_slug(decoded_slug)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found for uniqueSlug: {decoded_slug}")
        
        monthly_stats = await MonthlyStorageService.get_story_monthly_stats(story.key, year, month) or {}
        
        member_reads = monthly_stats.get("medium_member_reads", 0)
        nonmember_reads = monthly_stats.get("medium_nonmember_reads", 0)
        reads = member_reads + nonmember_reads
        reads_percent = round((member_reads / reads) * 100, 1) if reads > 0 else 0
        
        member_views = monthly_stats.get("medium_member_views", 0)
        nonmember_views = monthly_stats.get("medium_nonmember_views", 0)
        views = member_views + nonmember_views
        views_percent = round((member_views / views) * 100, 1) if views > 0 else 0
        
        return {
            "story_key": story.key,
            "unique_slug": story.uniqueSlug,
            "story_name": story.name,
            "yearmonth": yearmonth,
            "member_reads": member_reads,
            "nonmember_reads": nonmember_reads,
            "reads": reads,
            "reads_percent": reads_percent,
            "member_views": member_views,
            "nonmember_views": nonmember_views,
            "views": views,
            "views_percent": views_percent,
            "claps": monthly_stats.get("claps", 0),
            "responses": monthly_stats.get("responses", 0),
            "leaderboard": monthly_stats.get("leaderboard", False),
            "leaderboard_nanos": monthly_stats.get("leaderboard_nanos", 0),
            "medium_earnings": monthly_stats.get("medium_earnings", 0),
            "medium_new_followers": monthly_stats.get("medium_new_followers", 0),
            "medium_highlights": monthly_stats.get("medium_highlights", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting story stats by slug: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
PUT /api/stories/stats/{unique_slug}/{yearmonth}
Description: Update monthly stats by uniqueSlug

curl -X PUT "http://localhost:8000/api/stories/stats/asp-net-core-filters-deep-dive/2026-03" \
  -H "Content-Type: application/json" \
  -d '{"leaderboard": true, "leaderboard_nanos": 30000000}' | jq '.'
"""
@router.put("/stats/{unique_slug:path}/{yearmonth}")
async def update_story_stats_by_slug(unique_slug: str, yearmonth: str, stats_data: dict):
    """Update monthly stats by uniqueSlug"""
    try:
        parts = yearmonth.split('-')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid yearmonth format")
        year = int(parts[0])
        month = int(parts[1])
        
        decoded_slug = unquote(unique_slug)
        story = await StoryService.get_story_by_unique_slug(decoded_slug)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found for uniqueSlug: {decoded_slug}")
        
        storage_data = {
            "medium_member_reads": stats_data.get("member_reads", 0),
            "medium_nonmember_reads": stats_data.get("nonmember_reads", 0),
            "medium_member_views": stats_data.get("member_views", 0),
            "medium_nonmember_views": stats_data.get("nonmember_views", 0),
            "claps": stats_data.get("claps", 0),
            "responses": stats_data.get("responses", 0),
            "leaderboard": stats_data.get("leaderboard", False),
            "leaderboard_nanos": stats_data.get("leaderboard_nanos", 0),
            "medium_earnings": stats_data.get("medium_earnings", 0),
            "reads": stats_data.get("reads", 0),
            "view_count": stats_data.get("view_count", stats_data.get("views", 0)),
            "medium_new_followers": stats_data.get("medium_new_followers", 0),
            "medium_highlights": stats_data.get("medium_highlights", 0)
        }
        
        success = await MonthlyStorageService.update_story_monthly_stats(
            story.key, year, month, storage_data, story.name
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update monthly stats")
        
        return {"success": True, "message": "Monthly stats updated", "story_key": story.key, "unique_slug": story.uniqueSlug, "story_name": story.name}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating story stats by slug: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# STORY MONTHS ENDPOINTS - Using uniqueSlug
# ============================================

"""
GET /api/stories/story-months/{unique_slug}
Description: Get all months where a story has data by uniqueSlug

curl -X GET "http://localhost:8000/api/stories/story-months/asp-net-core-filters-deep-dive-building-maintainable-web-apis-with-net-10-and-reactive-extensions-78cb972195da" | jq '.'
"""
@router.get("/story-months/{unique_slug:path}")
async def get_story_months_by_slug(unique_slug: str):
    """Get all months where a story has data by uniqueSlug"""
    try:
        decoded_slug = unquote(unique_slug)
        story = await StoryService.get_story_by_unique_slug(decoded_slug)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found for uniqueSlug: {decoded_slug}")
        
        months = await MonthlyStorageService.get_months_for_story(story.key)
        
        return {
            "story_key": story.key,
            "unique_slug": story.uniqueSlug,
            "story_name": story.name,
            "months": months,
            "total": len(months)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting story months by slug: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/stories/ensure-story-in-month
Description: Ensure a story exists in monthly data by uniqueSlug

curl -X POST "http://localhost:8000/api/stories/ensure-story-in-month?unique_slug=asp-net-core-filters-deep-dive&year=2026&month=4" | jq '.'
"""
@router.post("/ensure-story-in-month")
async def ensure_story_in_month_endpoint(
    unique_slug: str,
    year: int,
    month: int
):
    """Ensure a story exists in monthly data by uniqueSlug"""
    try:
        decoded_slug = unquote(unique_slug)
        story = await StoryService.get_story_by_unique_slug(decoded_slug)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found for uniqueSlug: {decoded_slug}")
        
        success = await MonthlyStorageService.ensure_story_in_month(
            story.key, year, month, story.name
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to ensure story in month")
        
        return {"success": True, "message": "Story ensured in month", "story_key": story.key, "unique_slug": story.uniqueSlug, "story_name": story.name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ensuring story in month: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# CREATE, SYNC, UTILITY ENDPOINTS
# ============================================

"""
POST /api/stories/story
Description: Create a new story

curl -X POST "http://localhost:8000/api/stories/story" \
  -H "Content-Type: application/json" \
  -d '{
    "uniqueSlug": "my-new-story",
    "title": "My New Story",
    "folder": "Miscellaneous",
    "series": "Python Tutorials",
    "tags": ["python", "beginner"],
    "read_time": 10,
    "created_date": "2026-04-06",
    "medium_url": "https://medium.com/@username/post-title-78cb972195da"
  }' | jq '.'
"""
@router.post("/story")
async def create_story(story_data: StoryCreate):
    try:
        story = await StoryService.create_story(story_data)
        return {
            "success": True,
            "message": "Story created",
            "story": {
                "key": story.key,
                "uniqueSlug": story.uniqueSlug,
                "name": story.name,
                "medium_url": story.medium_url
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating story: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/stories/sync
Description: Sync filesystem with stories.json

curl -X POST "http://localhost:8000/api/stories/sync" | jq '.'
"""
@router.post("/sync")
async def sync_stories():
    """Sync filesystem with stories.json - discovers new markdown files"""
    try:
        result = await StoryService.sync_with_filesystem()
        return {
            "success": True,
            "message": "Sync completed",
            "added": result.get("added", 0),
            "updated": result.get("updated", 0),
            "total_stories": result.get("total", 0)
        }
    except Exception as e:
        logger.error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/stories/earnings/total
Description: Get total earnings from all months

curl -X GET "http://localhost:8000/api/stories/earnings/total" | jq '.'
"""
@router.get("/earnings/total")
async def get_total_earnings():
    """Get total earnings across all months."""
    try:
        available_months = await MonthlyStorageService.get_available_months()
        total_earnings = 0
        
        for month_info in available_months:
            monthly_data = await MonthlyStorageService.load_monthly_stats(
                month_info["year"], month_info["month"]
            )
            for story_key, story_data in monthly_data.get("stories", {}).items():
                total_earnings += story_data.get("medium_earnings", 0)
        
        return {
            "total_earnings": total_earnings,
            "total_nanos": total_earnings,
            "formatted": f"${total_earnings / 1000000000:.2f}",
            "months_processed": len(available_months)
        }
    except Exception as e:
        logger.error(f"Error getting total earnings: {e}")
        return {"total_earnings": 0, "total_nanos": 0, "formatted": "$0.00", "months_processed": 0}


"""
GET /api/stories/leaderboard-status
Description: Get leaderboard status for all stories

curl -X GET "http://localhost:8000/api/stories/leaderboard-status" | jq '.'
"""
@router.get("/leaderboard-status")
async def get_leaderboard_status():
    """Get leaderboard status across all months."""
    try:
        available_months = await MonthlyStorageService.get_available_months()
        
        leaderboard_stories = set()
        story_details = {}
        total_nanos = 0
        
        for month_info in available_months:
            monthly_data = await MonthlyStorageService.load_monthly_stats(
                month_info["year"], month_info["month"]
            )
            for story_key, story_data in monthly_data.get("stories", {}).items():
                if story_data.get("leaderboard", False):
                    leaderboard_stories.add(story_key)
                    total_nanos += story_data.get("leaderboard_nanos", 0)
                    if story_key not in story_details:
                        story_details[story_key] = {
                            "title": story_data.get("title", story_key),
                            "months": []
                        }
                    story_details[story_key]["months"].append(f"{month_info['year']}-{month_info['month']:02d}")
        
        return {
            "leaderboard_stories": list(leaderboard_stories),
            "story_details": story_details,
            "total": len(leaderboard_stories),
            "total_nanos": total_nanos,
            "formatted": f"${total_nanos / 1000000000:.2f}"
        }
    except Exception as e:
        logger.error(f"Error getting leaderboard status: {e}")
        return {"leaderboard_stories": [], "story_details": {}, "total": 0, "total_nanos": 0, "formatted": "$0.00"}


"""
GET /api/stories/months
Description: Get list of available months for dropdown

curl -X GET "http://localhost:8000/api/stories/months" | jq '.'
"""
@router.get("/months")
async def get_available_months_list():
    """Get list of available months for dropdown"""
    try:
        months = await MonthlyStorageService.get_available_months()
        formatted_months = [f"{m['year']}-{m['month']:02d}" for m in months]
        formatted_months.sort(reverse=True)
        return {"months": formatted_months}
    except Exception as e:
        logger.error(f"Error getting available months: {e}")
        return {"months": []}


"""
GET /api/stories/mode
Description: Get current mode and available months

curl -X GET "http://localhost:8000/api/stories/mode" | jq '.'
"""
@router.get("/mode")
async def get_current_mode():
    """Get current mode (dashboard/month) and available months"""
    try:
        mode = await AppStatusService.get_current_mode()
        current_month = await AppStatusService.get_current_month()
        available_months = await MonthlyStorageService.get_available_months()
        
        return {
            "mode": mode,
            "current_month": current_month,
            "available_months": available_months
        }
    except Exception as e:
        logger.error(f"Error getting mode: {e}")
        year, month = get_current_year_month()
        return {
            "mode": "dashboard",
            "current_month": {"year": year, "month": month},
            "available_months": []
        }


"""
GET /api/stories/stats-by-url
Description: Get stats by Medium URL (legacy, use /stats/{unique_slug} instead)

curl -X GET "http://localhost:8000/api/stories/stats-by-url?medium_url=https://medium.com/@username/post-title-123" | jq '.'
"""
@router.get("/stats-by-url")
async def get_stats_by_url(medium_url: str):
    """Get stats by Medium URL (legacy)"""
    try:
        story = await StoryService.get_story_by_medium_url(medium_url)
        
        if not story:
            return {"success": False, "message": "Story not found"}
        
        year, month = get_current_year_month()
        monthly_stats = await MonthlyStorageService.get_story_monthly_stats(
            story.key, year, month
        ) or {}
        
        return {
            "success": True,
            "story": {
                "key": story.key,
                "uniqueSlug": story.uniqueSlug,
                "name": story.name
            },
            "current_month": {
                "member_reads": monthly_stats.get("medium_member_reads", 0),
                "nonmember_reads": monthly_stats.get("medium_nonmember_reads", 0),
                "reads": monthly_stats.get("reads", 0),
                "member_views": monthly_stats.get("medium_member_views", 0),
                "nonmember_views": monthly_stats.get("medium_nonmember_views", 0),
                "views": monthly_stats.get("view_count", 0),
                "claps": monthly_stats.get("claps", 0),
                "responses": monthly_stats.get("responses", 0),
                "leaderboard": monthly_stats.get("leaderboard", False),
                "leaderboard_nanos": monthly_stats.get("leaderboard_nanos", 0),
                "medium_earnings": monthly_stats.get("medium_earnings", 0)
            }
        }
    except Exception as e:
        logger.error(f"Error getting stats by URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# MODE SWITCHING ENDPOINTS
# ============================================

"""
POST /api/stories/switch-month
Description: Switch to month view

curl -X POST "http://localhost:8000/api/stories/switch-month?year=2026&month=4" | jq '.'
"""
@router.post("/switch-month")
async def switch_month(year: int, month: int):
    """Switch to month view"""
    try:
        await AppStatusService.set_current_mode("month")
        await AppStatusService.set_current_month(year, month)
        
        month_name = datetime(year, month, 1).strftime("%B %Y")
        
        return {
            "success": True,
            "message": f"Switched to {month_name}",
            "mode": "month",
            "year": year,
            "month": month
        }
    except Exception as e:
        logger.error(f"Error switching month: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/stories/switch-to-dashboard
Description: Switch to dashboard mode

curl -X POST "http://localhost:8000/api/stories/switch-to-dashboard" | jq '.'
"""
@router.post("/switch-to-dashboard")
async def switch_to_dashboard():
    """Switch to dashboard mode"""
    try:
        await AppStatusService.set_current_mode("dashboard")
        
        return {
            "success": True,
            "message": "Switched to dashboard mode",
            "mode": "dashboard"
        }
    except Exception as e:
        logger.error(f"Error switching to dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# STATS FETCHING ENDPOINTS (Medium API)
# ============================================

"""
POST /api/stories/fetch-story-stats/{post_id}/{yearmonth}
Description: Fetch and SAVE monthly stats for a specific story from Medium API

curl -X POST "http://localhost:8000/api/stories/fetch-story-stats/93b5bfa4fd07/2026-04" | jq '.'
"""
@router.post("/fetch-story-stats/{post_id}/{yearmonth}")
async def fetch_and_save_story_stats(post_id: str, yearmonth: str, unique_slug: str = None):
    """
    Fetch monthly stats for a specific story from Medium API and SAVE to monthly DB.
    
    Args:
        post_id: Medium post ID
        yearmonth: Year-month in YYYY-MM format
        unique_slug: Optional uniqueSlug (if not provided, will try to find by post_id)
    """
    try:
        parts = yearmonth.split('-')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid yearmonth format")
        
        year = int(parts[0])
        month = int(parts[1])
        
        api_service = get_medium_api_service()
        
        if not api_service.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        story = None
        if unique_slug:
            story = await StoryService.get_story_by_unique_slug(unquote(unique_slug))
        
        if not story:
            all_stories = await StoryService.get_all_stories()
            for s in all_stories:
                if s.medium_url and post_id in s.medium_url:
                    story = s
                    break
        
        if not story:
            return {
                "success": False, 
                "message": "Story not found. Please provide unique_slug parameter.",
                "stats": None,
                "saved": False
            }
        
        response = api_service.get_story_metadata_medium(post_id, year, month)
        
        if not response:
            return {"success": False, "message": "No stats found from Medium API", "stats": None, "saved": False}
        
        parsed_stats = api_service.parse_stats_response(response, post_id)
        totals = parsed_stats.get("totals", {})
        
        monthly_data = {
            "medium_member_reads": totals.get("member_reads", 0),
            "medium_nonmember_reads": totals.get("nonmember_reads", 0),
            "medium_member_views": totals.get("member_views", 0),
            "medium_nonmember_views": totals.get("nonmember_views", 0),
            "claps": totals.get("claps", 0),
            "responses": totals.get("replies", 0),
            "medium_highlights": totals.get("highlights", 0),
            "medium_new_followers": totals.get("new_followers", 0),
            "medium_earnings": totals.get("earnings", 0),
            "reads": totals.get("total_reads", 0),
            "view_count": totals.get("total_views", 0),
            "last_stats_update": datetime.now().isoformat()
        }
        
        await MonthlyStorageService.ensure_story_in_month(
            story.key, year, month, story.name
        )
        
        save_success = await MonthlyStorageService.update_story_monthly_stats(
            story.key, year, month, monthly_data, story.name
        )
        
        return {
            "success": True,
            "message": f"Stats fetched and saved for {yearmonth}",
            "stats": totals,
            "saved": save_success,
            "story_name": story.name,
            "unique_slug": story.uniqueSlug,
            "story_key": story.key,
            "yearmonth": yearmonth
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching story stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/stories/fetch-lifetime-stats/{unique_slug}
Description: Fetch and SAVE lifetime + monthly stats for a story

curl -X POST "http://localhost:8000/api/stories/fetch-lifetime-stats/asp-net-core-filters-deep-dive-building-maintainable-web-apis-with-net-10-and-reactive-extensions-78cb972195da" | jq '.'
"""
@router.post("/fetch-lifetime-stats/{unique_slug:path}")
async def fetch_and_save_lifetime_stats(unique_slug: str, year: int = None, month: int = None):
    """
    Fetch lifetime stats for a story from Medium API and SAVE to both places.
    """
    try:
        decoded_slug = unquote(unique_slug)
        story = await StoryService.get_story_by_unique_slug(decoded_slug)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found for uniqueSlug: {decoded_slug}")
        
        if not story.medium_url:
            raise HTTPException(status_code=400, detail="Story has no Medium URL")
        
        api_service = get_medium_api_service()
        
        if not api_service.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        post_id = extract_post_id_from_url(story.medium_url)
        if not post_id:
            raise HTTPException(status_code=400, detail="Could not extract post ID from URL")
        
        results = {
            "lifetime": None,
            "monthly": None,
            "story_updated": False,
            "monthly_updated": False
        }
        
        lifetime_response = api_service.get_story_earnings_medium("mvineetsharma", 50)
        
        if lifetime_response:
            if isinstance(lifetime_response, list) and len(lifetime_response) > 0:
                response_item = lifetime_response[0]
                if 'data' in response_item:
                    user_result = response_item['data'].get('userResult', {})
                    if user_result and user_result.get('__typename') == 'User':
                        posts_connection = user_result.get('postsConnection', {})
                        edges = posts_connection.get('edges', [])
                        
                        for edge in edges:
                            node = edge.get('node', {})
                            if node.get('id') == post_id:
                                total_stats = node.get('totalStats', {})
                                results["lifetime"] = {
                                    "lifetime_reads": total_stats.get('reads', 0),
                                    "lifetime_views": total_stats.get('views', 0),
                                    "presentation_count": total_stats.get('presentations', 0),
                                    "feed_click_through_rate": 0
                                }
                                break
        
        if results["lifetime"]:
            update_data = StoryUpdate(
                lifetime_reads=results["lifetime"].get("lifetime_reads", 0),
                lifetime_views=results["lifetime"].get("lifetime_views", 0),
                presentation_count=results["lifetime"].get("presentation_count", 0),
                feed_click_through_rate=results["lifetime"].get("feed_click_through_rate", 0),
                last_stats_update=datetime.now().isoformat()
            )
            updated_story = await StoryService.update_story(story.key, update_data)
            if updated_story:
                results["story_updated"] = True
        
        if year is None or month is None:
            year, month = get_current_year_month()
        
        monthly_response = api_service.get_story_metadata_medium(post_id, year, month)
        
        if monthly_response:
            parsed_monthly = api_service.parse_stats_response(monthly_response, post_id)
            totals = parsed_monthly.get("totals", {})
            results["monthly"] = totals
            
            monthly_data = {
                "medium_member_reads": totals.get("member_reads", 0),
                "medium_nonmember_reads": totals.get("nonmember_reads", 0),
                "medium_member_views": totals.get("member_views", 0),
                "medium_nonmember_views": totals.get("nonmember_views", 0),
                "claps": totals.get("claps", 0),
                "responses": totals.get("replies", 0),
                "medium_highlights": totals.get("highlights", 0),
                "medium_new_followers": totals.get("new_followers", 0),
                "medium_earnings": totals.get("earnings", 0),
                "reads": totals.get("total_reads", 0),
                "view_count": totals.get("total_views", 0),
                "last_stats_update": datetime.now().isoformat()
            }
            
            await MonthlyStorageService.ensure_story_in_month(
                story.key, year, month, story.name
            )
            
            success = await MonthlyStorageService.update_story_monthly_stats(
                story.key, year, month, monthly_data, story.name
            )
            if success:
                results["monthly_updated"] = True
        
        return {
            "success": True,
            "message": "Stats fetched and saved",
            "story_name": story.name,
            "unique_slug": story.uniqueSlug,
            "story_key": story.key,
            "year": year,
            "month": month,
            "lifetime_stats": results.get("lifetime"),
            "monthly_stats": results.get("monthly"),
            "story_updated": results["story_updated"],
            "monthly_updated": results["monthly_updated"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching lifetime stats: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# REFRESH STATS ENDPOINTS
# ============================================

"""
POST /api/stories/refresh-stats
Description: Refresh stats from Medium API for current month

curl -X POST "http://localhost:8000/api/stories/refresh-stats" | jq '.'
"""
@router.post("/refresh-stats")
async def refresh_stats_current_month():
    """Refresh stats from Medium API for current month"""
    try:
        year, month = get_current_year_month()
        return await refresh_stats_with_period(f"{year}-{month}")
    except Exception as e:
        logger.error(f"Error refreshing stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/stories/refresh-stats/{period}
Description: Refresh stats from Medium API for specific period (YYYY-MM)

curl -X POST "http://localhost:8000/api/stories/refresh-stats/2026-04" | jq '.'
"""
@router.post("/refresh-stats/{period}")
async def refresh_stats_with_period(period: str):
    try:
        datetime.strptime(period, "%Y-%m")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid period format")
    
    result = await StoryService.fetch_medium_stats(period)
    return result

# ============================================
# SINGLE STORY STATS FETCHING ENDPOINTS
# ============================================

"""
POST /api/stories/refresh-story/{postId}
Description: Fetch and save stats for a single story for current month

curl -X POST "http://localhost:8000/api/stories/refresh-story/40793d1e9f2b" | jq '.'
"""
@router.post("/refresh-story/{postId}")
async def refresh_story_current_month(postId: str):
    """Fetch stats for a single story for the current month."""
    try:
        year, month = get_current_year_month()
        period = f"{year}-{month:02d}"
        return await refresh_story_with_period(postId, period)
    except Exception as e:
        logger.error(f"Error refreshing story: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/stories/refresh-story/{postId}/{period}
Description: Fetch and save stats for a single story for specific period

curl -X POST "http://localhost:8000/api/stories/refresh-story/40793d1e9f2b/2026-04" | jq '.'
"""
@router.post("/refresh-story/{postId}/{period}")
async def refresh_story_with_period(postId: str, period: str):
    """Fetch stats for a single story for a specific period."""
    try:
        from datetime import datetime
        try:
            datetime.strptime(period, "%Y-%m")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid period format. Use YYYY-MM")
        
        result = await StoryService.fetch_medium_story_stats(postId, period)
        
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("message"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing story stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"""
GET /api/stories/import-logs
Description: Get import logs

curl -X GET "http://localhost:8000/api/stories/import-logs" | jq '.'
"""
@router.get("/import-logs")
async def get_import_logs(limit: int = 50):
    """Get import logs"""
    try:
        log_file = Path(settings.data_dir) / "import_logs.json"
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
                return {"success": True, "logs": logs[:limit], "total": len(logs)}
        return {"success": True, "logs": [], "total": 0}
    except Exception as e:
        logger.error(f"Error getting import logs: {e}")
        return {"success": True, "logs": [], "total": 0}


"""
GET /api/stories/update-story-monthly-stats/{unique_slug}
Description: Update a story's monthly stats for a specific month

curl -X PUT "http://localhost:8000/api/stories/update-story-monthly-stats/asp-net-core-filters-deep-dive?year=2026&month=4" \
  -H "Content-Type: application/json" \
  -d '{"reads": 100, "claps": 50}' | jq '.'
"""
@router.put("/update-story-monthly-stats/{unique_slug:path}")
async def update_story_monthly_stats_endpoint(
    unique_slug: str,
    year: int,
    month: int,
    stats_data: dict
):
    """Update a story's monthly stats for a specific month by uniqueSlug"""
    try:
        decoded_slug = unquote(unique_slug)
        story = await StoryService.get_story_by_unique_slug(decoded_slug)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found for uniqueSlug: {decoded_slug}")
        
        success = await MonthlyStorageService.update_story_monthly_stats(
            story.key, year, month, stats_data, story.name
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update monthly stats")
        
        return {"success": True, "message": "Monthly stats updated", "story_key": story.key, "unique_slug": story.uniqueSlug}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating story monthly stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/stories/debug/unique-slug/{unique_slug}
Description: Debug endpoint to check story by uniqueSlug

curl -X GET "http://localhost:8000/api/stories/debug/unique-slug/asp-net-core-filters-deep-dive" | jq '.'
"""
@router.get("/debug/unique-slug/{unique_slug:path}")
async def debug_story_by_slug(unique_slug: str):
    """Debug endpoint to check story by uniqueSlug"""
    try:
        decoded_slug = unquote(unique_slug)
        story = await StoryService.get_story_by_unique_slug(decoded_slug)
        
        if not story:
            return {"found": False, "unique_slug": decoded_slug}
        
        return {
            "found": True,
            "unique_slug": story.uniqueSlug,
            "key": story.key,
            "name": story.name,
            "title": story.title,
            "status": story.status,
            "bookmarked": story.bookmarked,
            "leaderboard": story.leaderboard
        }
    except Exception as e:
        return {"error": str(e), "unique_slug": unique_slug}


"""
GET /api/stories/monthly-stats/{year}/{month}
Description: Get monthly stats mapping for a specific month

curl -X GET "http://localhost:8000/api/stories/monthly-stats/2026/3" | jq '.'
"""

@router.get("/monthly-stats/{year}/{month}")
async def get_monthly_stats_map(year: int, month: int):
    try:
        if month < 1 or month > 12:
            raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
        
        all_stories = await StoryService.get_all_stories()
        
        stats_map = {}
        target_month_str = f"{year}-{month:02d}"
        
        # DEBUG: Find the ASP.NET story specifically
        print(f"\n{'='*60}")
        print(f"DEBUG: Looking for {target_month_str} earnings")
        print(f"{'='*60}")
        
        for story in all_stories:
            if story.status != "Published":
                continue
            
            # Check if this is the ASP.NET story
            is_aspnet = 'asp-net-core-filters' in story.uniqueSlug.lower()
            
            if is_aspnet:
                print(f"\n📖 Found ASP.NET Story:")
                print(f"   uniqueSlug: {story.uniqueSlug}")
                print(f"   status: {story.status}")
                
                if story.medium:
                    print(f"   Has medium object: YES")
                    print(f"   monthlyEarnings count: {len(story.medium.monthlyEarnings) if story.medium.monthlyEarnings else 0}")
                    
                    if story.medium.monthlyEarnings:
                        for me in story.medium.monthlyEarnings:
                            print(f"     - period: '{me.period}', nanos: {me.nanos}")
                            if me.period == target_month_str:
                                print(f"     ✅ MATCH FOUND for {target_month_str}!")
                    else:
                        print(f"   monthlyEarnings is None or empty")
                else:
                    print(f"   Has medium object: NO")
        
        # Now build the stats map
        stories_with_earnings = 0
        
        for story in all_stories:
            if story.status != "Published":
                continue
            
            story_stats = {
                "reads": 0,
                "views": 0,
                "claps": 0,
                "responses": 0,
                "earnings": 0,
                "leaderboard": False
            }
            
            if story.medium:
                story_stats["claps"] = story.medium.clapCount or 0
                story_stats["responses"] = story.medium.responsesCount or 0
                
                if story.medium.monthlyStats:
                    for monthly_stat in story.medium.monthlyStats:
                        if monthly_stat.period == target_month_str:
                            story_stats["reads"] = monthly_stat.reads or 0
                            story_stats["views"] = monthly_stat.views or 0
                            break
                
                if story.medium.monthlyEarnings:
                    for monthly_earning in story.medium.monthlyEarnings:
                        if monthly_earning.period == target_month_str:
                            story_stats["earnings"] = monthly_earning.nanos or 0
                            story_stats["leaderboard"] = (monthly_earning.nanos or 0) > 0
                            if story_stats["earnings"] > 0:
                                stories_with_earnings += 1
                                print(f"💰 {story.uniqueSlug}: earnings=${story_stats['earnings']/1000000000:.2f}")
                            break
            
            stats_map[story.uniqueSlug] = story_stats
        
        print(f"\n📊 Total published stories: {len(stats_map)}")
        print(f"💰 Stories with earnings > 0: {stories_with_earnings}")
        print(f"{'='*60}\n")
        
        return {
            "success": True,
            "year": year,
            "month": month,
            "yearmonth": target_month_str,
            "stats_map": stats_map,
            "total_stories": len(stats_map),
            "stories_with_earnings": stories_with_earnings
        }
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/content/{story_key:path}")
async def get_story_content(story_key: str):
    """Get the markdown content of a story file"""
    try:
        from urllib.parse import unquote
        from pathlib import Path
        from config import settings
        
        decoded_key = unquote(story_key)
        
        # Get the story
        story = await StoryService.get_story(decoded_key)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        # Get the raw story data from stories.json to access full_name
        from app.services.file_service import load_stories_data
        raw_data = await load_stories_data()
        stories_data = raw_data.get("stories", {})
        
        # Find the raw story data
        raw_story = None
        for key, story_data in stories_data.items():
            if key == decoded_key or key.endswith(decoded_key):
                raw_story = story_data
                break
        
        # Build path using series and full_name from raw data
        stories_root = Path(settings.stories_root)
        
        # Folder = series
        folder = story.series if story.series else "Miscellaneous"
        
        # Filename = full_name from raw data, or construct from name
        filename = None
        if raw_story and raw_story.get('full_name'):
            filename = raw_story.get('full_name')
        else:
            name = story.name or story.title or decoded_key
            filename = f"{name}.md" if not name.endswith('.md') else name
        
        # Clean filename (remove path separators)
        filename = filename.replace('/', '-').replace('\\', '-')
        
        # Final path: ./stories/{folder}/{filename}
        file_path = stories_root / folder / filename
        
        print(f"Looking for file: {file_path}")
        print(f"Folder: {folder}")
        print(f"Filename: {filename}")
        print(f"File exists: {file_path.exists()}")
        
        if not file_path.exists():
            # Try to find the file by searching in the folder
            folder_path = stories_root / folder
            if folder_path.exists():
                # Look for any .md file that matches the name
                search_name = story.name or story.title
                for md_file in folder_path.glob("*.md"):
                    if search_name and (search_name in md_file.stem or md_file.stem in search_name):
                        file_path = md_file
                        filename = md_file.name
                        print(f"Found alternative: {file_path}")
                        break
            
            if not file_path.exists():
                raise HTTPException(
                    status_code=404, 
                    detail=f"File not found: stories/{folder}/{filename}"
                )
        
        # Read the markdown content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "success": True,
            "story_key": story.key,
            "uniqueSlug": story.uniqueSlug,
            "title": story.title,
            "name": story.name,
            "series": story.series,
            "status": story.status,
            "createdDate": story.createdDate,
            "publishedDate": story.publishedDate,
            "publishedDueDate": story.publishedDueDate,
            "notes": story.notes,
            "tags": story.tags,
            "folder": folder,
            "filename": filename,
            "file_path": f"stories/{folder}/{filename}",
            "content": content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting story content: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/content/{story_key:path}")
async def save_story_content(story_key: str, data: Dict[str, str]):
    """Save the markdown content of a story file"""
    try:
        from urllib.parse import unquote
        from pathlib import Path
        from config import settings
        
        decoded_key = unquote(story_key)
        
        # Get the story
        story = await StoryService.get_story(decoded_key)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        # Get the raw story data to access full_name
        from app.services.file_service import load_stories_data
        raw_data = await load_stories_data()
        stories_data = raw_data.get("stories", {})
        
        raw_story = None
        for key, story_data in stories_data.items():
            if key == decoded_key or key.endswith(decoded_key):
                raw_story = story_data
                break
        
        # Build path
        stories_root = Path(settings.stories_root)
        
        # Folder = series
        folder = story.series if story.series else "Miscellaneous"
        
        # Filename from raw data
        filename = None
        if raw_story and raw_story.get('full_name'):
            filename = raw_story.get('full_name')
        else:
            name = story.name or story.title or decoded_key
            filename = f"{name}.md" if not name.endswith('.md') else name
        
        filename = filename.replace('/', '-').replace('\\', '-')
        file_path = stories_root / folder / filename
        
        # If file doesn't exist, try to find it
        if not file_path.exists():
            folder_path = stories_root / folder
            if folder_path.exists():
                search_name = story.name or story.title
                for md_file in folder_path.glob("*.md"):
                    if search_name and (search_name in md_file.stem or md_file.stem in search_name):
                        file_path = md_file
                        filename = md_file.name
                        break
        
        if not file_path.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"File not found: stories/{folder}/{filename}"
            )
        
        # Write the markdown content
        new_content = data.get("content", "")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        # Update story last_updated timestamp
        update_data = StoryUpdate(lastUpdated=datetime.now().isoformat())
        await StoryService.update_story(story.key, update_data)
        
        return {
            "success": True,
            "message": "Story saved successfully",
            "story_key": story.key,
            "file_path": f"stories/{folder}/{filename}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving story content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

#=================
@router.get("/api/debug/test-story-api/{post_id}/{period}")
async def test_story_api(post_id: str, period: str):
    """Test the Medium API call directly."""
    try:
        api_service = get_medium_api_service()
        
        if not api_service.is_authenticated():
            return {"error": "Not authenticated"}
        
        # Parse period
        parts = period.split('-')
        year = int(parts[0])
        month = int(parts[1])
        
        # Get timestamps
        start_at, end_at = api_service.get_month_timestamps(year, month)
        
        # GraphQL query
        query = """query MergedPostStatsQuery($postStatsTotalBundleInput: PostStatsTotalBundleInput!, $postStatsDailyBundleInput: PostStatsDailyBundleInput!) {
          postStatsTotalBundle(postStatsTotalBundleInput: $postStatsTotalBundleInput) {
            readersCount
            viewersCount
            feedClickThroughRate
            presentationCount
          }
          postStatsDailyBundle(postStatsDailyBundleInput: $postStatsDailyBundleInput) {
            buckets {
              dayStartsAt
              membershipType
              readersThatReadCount
              readersThatViewedCount
              readersThatClappedCount
              readersThatRepliedCount
              readersThatHighlightedCount
              readersThatInitiallyFollowedAuthorFromThisPostCount
            }
          }
        }"""
        
        variables = {
            "postStatsTotalBundleInput": {"postId": post_id},
            "postStatsDailyBundleInput": {
                "postId": post_id,
                "fromDayStartsAt": start_at,
                "toDayStartsAt": end_at
            }
        }
        
        # Call the internal method directly
        payload = api_service._build_graphql_request("MergedPostStatsQuery", variables, query, post_id, "stats-post")
        headers = api_service._get_common_headers(post_id, "MergedPostStatsQuery")
        
        # This is the critical call - see what it returns
        response = api_service._make_request(api_service.GRAPHQL_URL, headers, payload, f"Test {post_id} {period}")
        
        return {
            "response_is_none": response is None,
            "response_type": str(type(response)),
            "response": response if response else "No response"
        }
        
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        
# ============================================
# BUILD EXPORT ENDPOINT - Save diagrams and tables as PNG
# ============================================


"""
POST /api/stories/build-export
Description: Build story export with PNG images

This endpoint:
1. Creates folder with story name
2. Creates images subfolder
3. Saves all uploaded PNG images
4. Returns updated markdown content with image references
"""


# ============================================
# BUILD EXPORT ENDPOINT - COMPLETE WORKING VERSION
# ============================================

# Import Playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Install with: pip install playwright && playwright install chromium")


def wrap_image_paths_with_brackets(content: str) -> str:
    """Wrap ALL image paths with <> brackets to handle spaces and special characters"""
    # Match ![alt](path) and wrap path in <>
    pattern = r'(!\[.*?\]\()([^)]+?)(\))'
    
    def replacer(match):
        prefix = match.group(1)  # ![alt](
        path = match.group(2)     # images/filename.png
        suffix = match.group(3)   # )
        
        # Remove existing brackets if any
        clean_path = path.strip('<>')
        
        # Always wrap with brackets
        return f"{prefix}<{clean_path}>{suffix}"
    
    return re.sub(pattern, replacer, content)


def extract_mermaid_blocks(content: str) -> list:
    """Extract mermaid code blocks preserving original formatting"""
    blocks = []
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('```mermaid'):
            start_idx = i
            block_lines = []
            i += 1
            while i < len(lines):
                if lines[i].strip() == '```':
                    block_lines.append(lines[i])
                    break
                block_lines.append(lines[i])
                i += 1
            
            original_text = '\n'.join(lines[start_idx:i+1])
            code_lines = block_lines[:-1] if block_lines else []
            code = '\n'.join(code_lines).strip()
            
            blocks.append({
                'code': code,
                'original_text': original_text
            })
        i += 1
    
    logger.info(f"Extracted {len(blocks)} mermaid blocks")
    return blocks


def extract_markdown_tables(content: str) -> list:
    """Extract markdown tables preserving original formatting"""
    tables = []
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        if '|' in line and not line.startswith('```'):
            table_lines = []
            
            while i < len(lines):
                current = lines[i].strip()
                if '|' in current and not current.startswith('```'):
                    table_lines.append(lines[i])
                    i += 1
                else:
                    break
            
            if len(table_lines) >= 2:
                second_line = table_lines[1].strip()
                is_separator = '---' in second_line or re.search(r'\|[\s\-:|]+\|', second_line)
                
                if is_separator:
                    original_text = '\n'.join(table_lines)
                    tables.append({
                        'markdown': original_text,
                        'original_text': original_text
                    })
            continue
        i += 1
    
    logger.info(f"Extracted {len(tables)} markdown tables")
    return tables


async def render_mermaid_diagram(mermaid_code: str, output_folder: Path, index: int) -> Path:
    """Render mermaid diagram using Playwright"""
    png_file = output_folder / f"diagram-raw-{str(index+1).zfill(2)}.png"
    html_file = output_folder / f"temp-{index}.html"
    
    try:
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 25px;
            background: white;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }}
        .mermaid {{
            text-align: center;
            width: 100%;
            max-width: 1400px;
        }}
        .mermaid svg {{
            width: 100% !important;
            height: auto !important;
            max-width: 1400px;
        }}
    </style>
</head>
<body>
    <pre class="mermaid">
{mermaid_code}
    </pre>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose',
            flowchart: {{ 
                useMaxWidth: true, 
                htmlLabels: true,
                curve: 'basis'
            }}
        }});
    </script>
</body>
</html>"""
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={'width': 1600, 'height': 1200})
            
            await page.goto(f'file://{html_file}', wait_until='networkidle')
            await page.wait_for_selector('.mermaid svg', timeout=30000)
            
            element = await page.query_selector('.mermaid')
            if element:
                await element.screenshot(path=str(png_file))
            
            await browser.close()
        
        if html_file.exists():
            html_file.unlink()
        
        return png_file if png_file.exists() and png_file.stat().st_size > 100 else None
        
    except Exception as e:
        logger.error(f"Render error for diagram {index + 1}: {e}")
        if html_file.exists():
            html_file.unlink()
        return None


async def render_markdown_table(table_markdown: str, output_folder: Path, index: int) -> Path:
    """Render markdown table to PNG"""
    png_file = output_folder / f"table-raw-{str(index+1).zfill(2)}.png"
    
    try:
        html_content = convert_table_to_html(table_markdown)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            temp_html = f.name
        
        cmd = ['wkhtmltoimage', '--quality', '100', '--width', '1200', '--height', '0', temp_html, str(png_file)]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        os.unlink(temp_html)
        
        return png_file if result.returncode == 0 and png_file.exists() and png_file.stat().st_size > 100 else None
        
    except Exception as e:
        logger.error(f"Table render error: {e}")
        return None


def convert_table_to_html(table_markdown: str) -> str:
    """Convert markdown table to HTML with inline formatting support"""
    import re
    
    lines = [line.rstrip('\n') for line in table_markdown.strip().split('\n')]
    
    if len(lines) < 2:
        return '<html><body><p>Invalid table</p></body></html>'
    
    def format_inline(text: str) -> str:
        """Convert markdown inline formatting to HTML"""
        if not text:
            return ''
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__(.+?)__', r'strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        text = re.sub(r'_(.+?)_', r'<em>\1</em>', text)
        text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
        return text
    
    # Parse header
    header_line = lines[0].strip()
    if header_line.startswith('|'):
        header_line = header_line[1:]
    if header_line.endswith('|'):
        header_line = header_line[:-1]
    headers = [cell.strip() for cell in header_line.split('|')]
    
    # Parse alignment
    alignments = []
    if len(lines) > 1 and '---' in lines[1]:
        align_line = lines[1].strip()
        if align_line.startswith('|'):
            align_line = align_line[1:]
        if align_line.endswith('|'):
            align_line = align_line[:-1]
        align_cells = [cell.strip() for cell in align_line.split('|')]
        
        for cell in align_cells:
            if cell.startswith(':') and cell.endswith(':'):
                alignments.append('center')
            elif cell.endswith(':'):
                alignments.append('right')
            else:
                alignments.append('left')
    
    while len(alignments) < len(headers):
        alignments.append('left')
    
    # Parse body rows
    body_rows = []
    for i in range(2, len(lines)):
        line = lines[i].strip()
        if not line:
            continue
        if line.startswith('|'):
            line = line[1:]
        if line.endswith('|'):
            line = line[:-1]
        cells = [cell.strip() for cell in line.split('|')]
        while len(cells) < len(headers):
            cells.append('')
        body_rows.append(cells)
    
    # Build HTML
    html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; background: white; margin: 0; }
        table { border-collapse: collapse; width: 100%; font-size: 14px; line-height: 1.5; }
        th, td { border: 1px solid #ddd; padding: 10px 12px; vertical-align: top; }
        th { background-color: #f5f5f5; font-weight: 600; }
        tr:nth-child(even) { background-color: #fafafa; }
        code { background-color: #f4f4f4; padding: 2px 5px; border-radius: 3px; font-family: monospace; }
        strong { font-weight: 600; color: #2c5a9e; }
        em { font-style: italic; }
    </style>
</head>
<body>
    <table>
        <thead>
            <tr>
'''
    
    for idx, header in enumerate(headers):
        align = alignments[idx]
        html += f'                <th style="text-align: {align}">{format_inline(header)}</th>\n'
    
    html += '''              </tr>
        </thead>
        <tbody>
'''
    
    for row in body_rows:
        html += '              <tr>\n'
        for idx, cell in enumerate(row):
            align = alignments[idx]
            html += f'                <td style="text-align: {align}">{format_inline(cell)}</td>\n'
        html += '              </tr>\n'
    
    html += '''        </tbody>
    </table>
</body>
</html>'''
    
    return html


async def add_footer_to_image(image_path: Path, output_folder: Path, index: int, image_type: str) -> Path:
    """Add attribution footer to image"""
    from PIL import Image, ImageDraw, ImageFont
    
    output_file = output_folder / f"{image_type}-{str(index+1).zfill(2)}.png"
    
    try:
        img = Image.open(image_path)
        
        footer_text = "Vineet Sharma • Medium: mvineetsharma.medium.com • LinkedIn: linkedin.com/in/vineet-sharma-architect"
        footer_height = 35
        padding = 8
        
        new_img = Image.new('RGB', (img.width, img.height + footer_height), color='white')
        new_img.paste(img, (0, 0))
        
        draw = ImageDraw.Draw(new_img)
        font = ImageFont.load_default()
        
        try:
            bbox = draw.textbbox((0, 0), footer_text, font=font)
            text_width = bbox[2] - bbox[0]
            x = (new_img.width - text_width) // 2
            x = max(x, 10)
        except:
            x = 50
        
        draw.text((x, img.height + padding), footer_text, fill='#666666', font=font)
        new_img.save(output_file, 'PNG')
        
        if image_path != output_file and image_path.exists():
            image_path.unlink()
        
        return output_file
        
    except Exception as e:
        logger.error(f"Error adding footer: {e}")
        if image_path != output_file:
            import shutil
            shutil.copy(image_path, output_file)
            if image_path != output_file and image_path.exists():
                image_path.unlink()
        return output_file


async def copy_source_images(content: str, source_images_dir: Path, dest_images_folder: Path) -> list:
    """Copy images referenced in markdown to destination"""
    import shutil
    
    copied_images = []
    
    if not source_images_dir or not source_images_dir.exists():
        logger.info(f"Source images directory not found: {source_images_dir}")
        return copied_images
    
    pattern = r'!\[.*?\]\((<?.*?>?)\)'
    matches = re.findall(pattern, content)
    
    logger.info(f"Found {len(matches)} image references in markdown")
    
    for img_ref in matches:
        clean_ref = img_ref.strip('<>')
        
        if 'diagram-' in clean_ref or 'table-' in clean_ref:
            continue
        
        if clean_ref.startswith('http://') or clean_ref.startswith('https://'):
            continue
        
        img_filename = Path(clean_ref).name
        source_path = source_images_dir / img_filename
        
        if source_path.exists():
            dest_path = dest_images_folder / img_filename
            
            # Handle duplicates
            counter = 1
            original_stem = source_path.stem
            original_ext = source_path.suffix
            while dest_path.exists():
                dest_path = dest_images_folder / f"{original_stem}_{counter}{original_ext}"
                counter += 1
            
            shutil.copy2(source_path, dest_path)
            copied_images.append(dest_path.name)
            logger.info(f"✅ Copied: {img_filename}")
        else:
            logger.warning(f"❌ Image not found: {img_filename}")
    
    return copied_images


@router.post("/build-export-python")
async def build_story_export_python(
    storyKey: str = Form(...),
    storyName: str = Form(...),
    content: str = Form(...)
):
    """Build story export with rendered diagrams and tables as PNG images"""
    try:
        from config import settings
        from app.services.story_service import StoryService
        
        logger.info(f"=== BUILD EXPORT START ===")
        logger.info(f"Story Key: {storyKey}")
        
        # Get the story
        story = await StoryService.get_story(storyKey)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        # Determine paths
        original_folder = story.series if story.series else "Miscellaneous"
        stories_root = Path(settings.stories_root)
        
        # Source paths
        story_name = story.name or story.title or storyKey
        story_filename = f"{story_name}.md" if not story_name.endswith('.md') else story_name
        story_filename = story_filename.replace('/', '-').replace('\\', '-')
        source_md_path = stories_root / original_folder / story_filename
        source_images_dir = source_md_path.parent / "images"
        
        logger.info(f"Source markdown: {source_md_path}")
        logger.info(f"Source images: {source_images_dir}")
        
        # Destination paths
        safe_name = re.sub(r'[<>:"/\\|?*]', '', storyName)
        safe_name = re.sub(r'[\s]+', '-', safe_name).strip('-')[:100]
        
        build_folder = stories_root / original_folder / safe_name
        images_folder = build_folder / "images"
        
        build_folder.mkdir(parents=True, exist_ok=True)
        images_folder.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Build folder: {build_folder}")
        
        # Extract and render diagrams and tables
        mermaid_blocks = extract_mermaid_blocks(content)
        tables = extract_markdown_tables(content)
        
        logger.info(f"Found {len(mermaid_blocks)} diagrams, {len(tables)} tables")
        
        saved_images = []
        
        # Render mermaid diagrams
        if PLAYWRIGHT_AVAILABLE:
            for idx, block in enumerate(mermaid_blocks):
                logger.info(f"Rendering diagram {idx + 1}...")
                png_path = await render_mermaid_diagram(block['code'], images_folder, idx)
                if png_path:
                    img_with_footer = await add_footer_to_image(png_path, images_folder, idx, 'diagram')
                    if img_with_footer:
                        saved_images.append({
                            'type': 'diagram',
                            'filename': img_with_footer.name,
                            'original_text': block['original_text']
                        })
                        logger.info(f"✅ Diagram {idx + 1} rendered")
                    else:
                        logger.warning(f"❌ Failed to add footer to diagram {idx + 1}")
                else:
                    logger.warning(f"❌ Failed to render diagram {idx + 1}")
        
        # Render tables
        for idx, table in enumerate(tables):
            logger.info(f"Rendering table {idx + 1}...")
            png_path = await render_markdown_table(table['markdown'], images_folder, idx)
            if png_path:
                img_with_footer = await add_footer_to_image(png_path, images_folder, idx, 'table')
                if img_with_footer:
                    saved_images.append({
                        'type': 'table',
                        'filename': img_with_footer.name,
                        'original_text': table['original_text']
                    })
                    logger.info(f"✅ Table {idx + 1} rendered")
                else:
                    logger.warning(f"❌ Failed to add footer to table {idx + 1}")
            else:
                logger.warning(f"❌ Failed to render table {idx + 1}")
        
        # Build modified content
        modified_content = content
        
        # Replace diagrams and tables with image references
        for img in saved_images:
            if img['type'] == 'diagram':
                modified_content = modified_content.replace(
                    img['original_text'],
                    f"\n\n![Mermaid Diagram](images/{img['filename']})\n\n"
                )
            else:
                modified_content = modified_content.replace(
                    img['original_text'],
                    f"\n\n![Markdown Table](images/{img['filename']})\n\n"
                )
        
        # Wrap ALL image paths with <> brackets
        modified_content = wrap_image_paths_with_brackets(modified_content)
        
        # Copy source images
        copied_images = await copy_source_images(content, source_images_dir, images_folder)
        
        # Save markdown file
        md_filename = f"{safe_name}.md"
        md_path = build_folder / md_filename
        
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(modified_content)
        
        # Save metadata
        metadata = {
            "original_story_key": storyKey,
            "original_series": original_folder,
            "exported_at": datetime.now().isoformat(),
            "story_title": storyName,
            "diagrams": len([i for i in saved_images if i['type'] == 'diagram']),
            "tables": len([i for i in saved_images if i['type'] == 'table']),
            "source_images": len(copied_images),
            "total_images": len(saved_images) + len(copied_images),
            "build_folder": str(build_folder)
        }
        
        with open(build_folder / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"=== BUILD COMPLETE ===")
        
        return {
            "success": True,
            "folderPath": str(build_folder),
            "imagesSaved": len(saved_images) + len(copied_images),
            "mdFile": md_filename,
            "mdContent": modified_content,
            "diagrams": len([i for i in saved_images if i['type'] == 'diagram']),
            "tables": len([i for i in saved_images if i['type'] == 'table']),
            "copiedImages": len(copied_images)
        }
        
    except Exception as e:
        logger.error(f"Build export error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))