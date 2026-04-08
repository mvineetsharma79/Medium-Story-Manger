"""
Stories Router - Complete endpoints with Medium URL as primary key
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from urllib.parse import unquote
import re
import json
from pathlib import Path

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
router = APIRouter()


# ============================================
# HELPER FUNCTIONS
# ============================================

async def resolve_story(identifier: str):
    """
    Resolve story by medium_url first, then by name
    Returns story object or None
    """
    decoded_identifier = unquote(identifier)
    all_stories = await StoryService.get_all_stories()
    
    # Step 1: Check if it's a URL and try to find by medium_url
    is_url = decoded_identifier.startswith('http://') or decoded_identifier.startswith('https://')
    
    if is_url:
        normalized_url = normalize_url(decoded_identifier)
        for story in all_stories:
            if story.medium_url and normalize_url(story.medium_url) == normalized_url:
                return story
    
    # Step 2: Try exact name match
    for story in all_stories:
        if story.name == decoded_identifier:
            return story
    
    # Step 3: Try normalized name match
    normalized_name = normalize_title(decoded_identifier)
    for story in all_stories:
        if normalize_title(story.name) == normalized_name:
            return story
    
    # Step 4: Try partial name match (last resort)
    for story in all_stories:
        if story.name and decoded_identifier.lower() in story.name.lower():
            return story
    
    return None


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
        "name": story.name,
        "series": story.series,
        "status": story.status or "Draft",
        "published_date": story.published_date,
        "created_date": story.created_date,
        "bookmarked": story.bookmarked or False,
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
        "leaderboard": monthly_stats.get("leaderboard", False),
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
        "total_followers": story.medium_new_followers or 0
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
        # Get current year/month for monthly stats (if needed for leaderboard flag)
        year, month = get_current_year_month()
        
        # Load monthly stats to check leaderboard flag for current month
        monthly_data = await MonthlyStorageService.load_monthly_stats(year, month)
        monthly_stats_map = monthly_data.get("stories", {})
        
        # Get all stories as Story objects (with nested medium and linkedin)
        all_stories = await StoryService.get_all_stories()
        
        # Get all stories that ever had leaderboard in ANY month (for dashboard mode)
        available_months = await MonthlyStorageService.get_available_months()
        leaderboard_stories_set = set()
        for month_info in available_months:
            month_data = await MonthlyStorageService.load_monthly_stats(month_info["year"], month_info["month"])
            for story_key, story_data in month_data.get("stories", {}).items():
                if story_data.get("leaderboard", False):
                    leaderboard_stories_set.add(story_key)
        
        # Build response with nested structure
        stories = []
        for story in all_stories:
            # Get monthly stats for current month
            monthly_stats = monthly_stats_map.get(story.key, {})
            
            # Determine leaderboard flag (true if ever on leaderboard in any month)
            leaderboard = story.key in leaderboard_stories_set
            
            # Convert story to dict with nested structure
            story_dict = story.dict()
            
            # Add monthly-specific fields (not stored in story object)
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
                    "name": story.name,
                    "series": story.series,
                    "status": story.status or "Published",
                    "published_date": story.published_date,
                    "created_date": story.created_date,
                    "bookmarked": story.bookmarked or False,
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
                    "leaderboard": monthly_stats.get("leaderboard", False),
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
                    "name": monthly_stats.get("title", story_key),
                    "series": None,
                    "status": "Published",
                    "published_date": None,
                    "created_date": None,
                    "bookmarked": False,
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
                    "leaderboard": monthly_stats.get("leaderboard", False),
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
                "name": s.name,
                "status": s.status,
                "series": s.series,
                "reads": s.reads,
                "created_date": s.created_date,
                "published_date": s.published_date,
                "medium_url": s.medium_url,
                "bookmarked": s.bookmarked
            }
            for s in all_stories
        ]
    except Exception as e:
        logger.error(f"Error getting all stories: {e}")
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
        total_nanos = 0
        
        for month_info in available_months:
            monthly_data = await MonthlyStorageService.load_monthly_stats(
                month_info["year"], month_info["month"]
            )
            for story_key, story_data in monthly_data.get("stories", {}).items():
                if story_data.get("leaderboard", False):
                    leaderboard_stories.add(story_key)
                    total_nanos += story_data.get("leaderboard_nanos", 0)
        
        return {
            "leaderboard_stories": list(leaderboard_stories),
            "total": len(leaderboard_stories),
            "total_nanos": total_nanos,
            "formatted": f"${total_nanos / 1000000000:.2f}"
        }
    except Exception as e:
        logger.error(f"Error getting leaderboard status: {e}")
        return {"leaderboard_stories": [], "total": 0, "total_nanos": 0, "formatted": "$0.00"}


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


# ============================================
# STORY ENDPOINTS - Smart resolution (medium_url first, then name)
# ============================================

"""
GET /api/stories/story/{identifier}
Description: Get story by medium_url (preferred) or name (fallback)

curl -X GET "http://localhost:8000/api/stories/story/https%3A%2F%2Fmedium.com%2F%40username%2Fpost-title-78cb972195da" | jq '.'
curl -X GET "http://localhost:8000/api/stories/story/My%20Story%20Title" | jq '.'
"""
@router.get("/story/{identifier:path}")
async def get_story(identifier: str):
    """Get story by medium_url (preferred) or name (fallback)."""
    try:
        story = await resolve_story(identifier)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found: {unquote(identifier)}")
        
        year, month = get_current_year_month()
        monthly_stats = await MonthlyStorageService.get_story_monthly_stats(story.key, year, month) or {}
        
        return build_story_response(story, monthly_stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting story: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
PUT /api/stories/story/{identifier}
Description: Update story by medium_url (preferred) or name (fallback)

curl -X PUT "http://localhost:8000/api/stories/story/https%3A%2F%2Fmedium.com%2F%40username%2Fpost-title-78cb972195da" \
  -H "Content-Type: application/json" \
  -d '{"status":"Published"}' | jq '.'
"""
@router.put("/story/{identifier:path}")
async def update_story(identifier: str, update_data: dict):
    """Update story by medium_url (preferred) or name (fallback)."""
    try:
        story = await resolve_story(identifier)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found: {unquote(identifier)}")
        
        update = StoryUpdate(**update_data)
        updated_story = await StoryService.update_story(story.key, update)
        
        if not updated_story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        return {"success": True, "message": "Story updated", "story": updated_story.dict()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating story: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
DELETE /api/stories/story/{identifier}
Description: Delete story by medium_url (preferred) or name (fallback)

curl -X DELETE "http://localhost:8000/api/stories/story/https%3A%2F%2Fmedium.com%2F%40username%2Fpost-title-78cb972195da" | jq '.'
"""
@router.delete("/story/{identifier:path}")
async def delete_story(identifier: str):
    """Delete story by medium_url (preferred) or name (fallback)."""
    try:
        story = await resolve_story(identifier)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found: {unquote(identifier)}")
        
        deleted = await StoryService.delete_story(story.key)
        if not deleted:
            raise HTTPException(status_code=404, detail="Story not found")
        
        # Remove from all monthly files
        available_months = await MonthlyStorageService.get_available_months()
        for month_info in available_months:
            await MonthlyStorageService.delete_story_from_month(
                story.key, month_info["year"], month_info["month"]
            )
        
        return {"success": True, "message": "Story deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting story: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/stories/story/{identifier}/publish
Description: Mark a story as published

curl -X POST "http://localhost:8000/api/stories/story/https%3A%2F%2Fmedium.com%2F%40username%2Fpost-title-78cb972195da/publish" \
  -H "Content-Type: application/json" \
  -d '{"medium_url": "https://medium.com/@username/post-title-123"}' | jq '.'
"""
@router.post("/story/{identifier:path}/publish")
async def publish_story(identifier: str, publish_data: dict = None):
    """Mark a story as published by medium_url (preferred) or name (fallback)."""
    try:
        story = await resolve_story(identifier)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found: {unquote(identifier)}")
        
        medium_url = publish_data.get("medium_url") if publish_data else None
        
        updated_story = await StoryService.publish_story(story.key, medium_url)
        if not updated_story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        return {"success": True, "message": "Story marked as published"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing story: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# STATS ENDPOINTS - Smart resolution
# ============================================

"""
GET /api/stories/stats/{identifier}/{yearmonth}
Description: Get monthly stats by medium_url (preferred) or name (fallback)

curl -X GET "http://localhost:8000/api/stories/stats/https%3A%2F%2Fmedium.com%2F%40username%2Fpost-title-123/2026-03" | jq '.'
"""
@router.get("/stats/{identifier:path}/{yearmonth}")
async def get_story_stats(identifier: str, yearmonth: str):
    """Get monthly stats by medium_url (preferred) or name (fallback)."""
    try:
        parts = yearmonth.split('-')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid yearmonth format")
        year = int(parts[0])
        month = int(parts[1])
        
        story = await resolve_story(identifier)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found: {unquote(identifier)}")
        
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
        logger.error(f"Error getting story stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
PUT /api/stories/stats/{identifier}/{yearmonth}
Description: Update monthly stats by medium_url (preferred) or name (fallback)

curl -X PUT "http://localhost:8000/api/stories/stats/https%3A%2F%2Fmedium.com%2F%40username%2Fpost-title-123/2026-03" \
  -H "Content-Type: application/json" \
  -d '{"leaderboard": true, "leaderboard_nanos": 30000000}' | jq '.'
"""
@router.put("/stats/{identifier:path}/{yearmonth}")
async def update_story_stats(identifier: str, yearmonth: str, stats_data: dict):
    """Update monthly stats by medium_url (preferred) or name (fallback)."""
    try:
        parts = yearmonth.split('-')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid yearmonth format")
        year = int(parts[0])
        month = int(parts[1])
        
        story = await resolve_story(identifier)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found: {unquote(identifier)}")
        
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
        
        return {"success": True, "message": "Monthly stats updated", "story_key": story.key, "story_name": story.name}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating story stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# STORY MONTHS ENDPOINTS
# ============================================

"""
GET /api/stories/story-months/{identifier}
Description: Get all months where a story has data

curl -X GET "http://localhost:8000/api/stories/story-months/https%3A%2F%2Fmedium.com%2F%40username%2Fpost-title-123" | jq '.'
"""
@router.get("/story-months/{identifier:path}")
async def get_story_months(identifier: str):
    """Get all months where a story has data by medium_url (preferred) or name (fallback)."""
    try:
        story = await resolve_story(identifier)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found: {unquote(identifier)}")
        
        months = await MonthlyStorageService.get_months_for_story(story.key)
        
        return {
            "story_key": story.key,
            "story_name": story.name,
            "months": months,
            "total": len(months)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting story months: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/stories/ensure-story-in-month
Description: Ensure a story exists in monthly data

curl -X POST "http://localhost:8000/api/stories/ensure-story-in-month?identifier=https%3A%2F%2Fmedium.com%2F%40username%2Fpost-title-123&year=2026&month=4" | jq '.'
"""
@router.post("/ensure-story-in-month")
async def ensure_story_in_month_endpoint(
    identifier: str,
    year: int,
    month: int
):
    """Ensure a story exists in monthly data by medium_url (preferred) or name (fallback)."""
    try:
        story = await resolve_story(identifier)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found: {unquote(identifier)}")
        
        success = await MonthlyStorageService.ensure_story_in_month(
            story.key, year, month, story.name
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to ensure story in month")
        
        return {"success": True, "message": "Story ensured in month", "story_key": story.key, "story_name": story.name}
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
    "name": "My New Story",
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
GET /api/stories/stats-by-url
Description: Get stats by Medium URL (legacy, use /stats/{identifier} instead)

curl -X GET "http://localhost:8000/api/stories/stats-by-url?medium_url=https://medium.com/@username/post-title-123" | jq '.'
"""
@router.get("/stats-by-url")
async def get_stats_by_url(medium_url: str):
    """Get stats by Medium URL (legacy)"""
    try:
        story = await resolve_story(medium_url)
        
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
async def fetch_and_save_story_stats(post_id: str, yearmonth: str, story_identifier: str = None):
    """
    Fetch monthly stats for a specific story from Medium API and SAVE to monthly DB.
    
    Args:
        post_id: Medium post ID
        yearmonth: Year-month in YYYY-MM format
        story_identifier: Optional story name or URL (if not provided, will try to find by post_id)
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
        
        # Find story by post_id or provided identifier
        story = None
        if story_identifier:
            story = await resolve_story(story_identifier)
        
        if not story:
            # Try to find story by post_id in medium_url
            all_stories = await StoryService.get_all_stories()
            for s in all_stories:
                if s.medium_url and post_id in s.medium_url:
                    story = s
                    break
        
        if not story:
            return {
                "success": False, 
                "message": "Story not found. Please provide story_identifier parameter.",
                "stats": None,
                "saved": False
            }
        
        # Fetch stats from API
        response = api_service.get_story_metadata_medium(post_id, year, month)
        
        if not response:
            return {"success": False, "message": "No stats found from Medium API", "stats": None, "saved": False}
        
        parsed_stats = api_service.parse_stats_response(response, post_id)
        totals = parsed_stats.get("totals", {})
        
        # Prepare data for saving
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
        
        # Ensure story exists in monthly DB
        await MonthlyStorageService.ensure_story_in_month(
            story.key, year, month, story.name
        )
        
        # Save to monthly DB
        save_success = await MonthlyStorageService.update_story_monthly_stats(
            story.key, year, month, monthly_data, story.name
        )
        
        return {
            "success": True,
            "message": f"Stats fetched and saved for {yearmonth}",
            "stats": totals,
            "saved": save_success,
            "story_name": story.name,
            "story_key": story.key,
            "yearmonth": yearmonth
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching story stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/stories/fetch-lifetime-stats/{identifier}
Description: Fetch and SAVE lifetime + monthly stats for a story

curl -X POST "http://localhost:8000/api/stories/fetch-lifetime-stats/https%3A%2F%2Fmedium.com%2F%40username%2Fpost-title-123" | jq '.'
"""
@router.post("/fetch-lifetime-stats/{identifier:path}")
async def fetch_and_save_lifetime_stats(identifier: str, year: int = None, month: int = None):
    """
    Fetch lifetime stats for a story from Medium API and SAVE to both places.
    """
    try:
        story = await resolve_story(identifier)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found: {unquote(identifier)}")
        
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
        
        # Fetch lifetime stats
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
        
        # Fetch monthly stats
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
    # ONLY validation
    try:
        datetime.strptime(period, "%Y-%m")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid period format")
    
    # DIRECTLY call StoryService - NO pre-check for existing stories
    result = await StoryService.fetch_medium_stories(period)
    return result

"""
GET /api/stories/import-logs
Description: Get import logs

curl -X GET "http://localhost:8000/api/stories/import-logs" | jq '.'
"""
@router.get("/import-logs")
async def get_import_logs(limit: int = 50):
    """Get import logs"""
    try:
        # Simple implementation - read from a log file if exists
        log_file = Path(settings.data_dir) / "import_logs.json"
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
                return {"success": True, "logs": logs[:limit], "total": len(logs)}
        return {"success": True, "logs": [], "total": 0}
    except Exception as e:
        logger.error(f"Error getting import logs: {e}")
        return {"success": True, "logs": [], "total": 0}

@router.get("/debug/raw-response")
async def debug_raw_response(period: str = "2026-04"):
    """Debug endpoint to see raw API response"""
    from app.services.medium_api_service import get_medium_api_service
    
    api_service = get_medium_api_service()
    
    if not api_service.is_authenticated():
        return {"error": "Not authenticated"}
    
    # Parse period
    parts = period.split('-')
    year = int(parts[0])
    month = int(parts[1])
    
    start_at, end_at = api_service.get_month_timestamps(year, month)
    
    from config import settings
    username = settings.medium_username
    
    # Make raw request
    query = """query StoryEarningsQuery($username: ID!, $first: Int!, $after: String!, $startAt: Long!, $endAt: Long!) {
    userResult(username: $username) {
        ... on User {
            postsConnection(first: $first, after: $after, timeRange: {startAt: $startAt, endAt: $endAt}) {
                edges {
                    node {
                        title
                        uniqueSlug
                        mediumUrl
                    }
                }
            }
        }
    }
    }"""
    
    variables = {
        "username": username,
        "first": 10,
        "after": "",
        "startAt": start_at,
        "endAt": end_at
    }
    
    payload = api_service._build_graphql_request("StoryEarningsQuery", variables, query, username, "debug")
    headers = api_service._get_common_headers(username, "StoryEarningsQuery")
    
    response = api_service._make_request(api_service.GRAPHQL_URL, headers, payload, "Debug")
    
    return {
        "period": period,
        "start_at": start_at,
        "end_at": end_at,
        "username": username,
        "response": response
    }