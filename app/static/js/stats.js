"""
Stories Router - Complete endpoints with Medium URL as primary key
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from urllib.parse import unquote
import re

from app.services.story_service import StoryService
from app.services.monthly_storage_service import MonthlyStorageService
from app.services.medium_api_service import get_medium_api_service
from app.models import StoryCreate, StoryUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# HELPER FUNCTIONS
# ============================================

def calculate_percentages(member: int, nonmember: int) -> tuple:
    """Calculate total and percentage"""
    total = member + nonmember
    percent = round((member / total) * 100, 1) if total > 0 else 0
    return total, percent


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
        "medium_earnings": monthly_stats.get("medium_earnings", 0)
    }


# ============================================
# LIST ENDPOINTS
# ============================================

"""
GET /api/stories/list
Description: Dashboard view - All stories from stories.json + current month stats

curl -X GET "http://localhost:8000/api/stories/list" | jq '.'
"""
@router.get("/list")
async def get_dashboard_stories():
    try:
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        
        monthly_data = await MonthlyStorageService.load_monthly_stats(current_year, current_month)
        monthly_stats_map = monthly_data.get("stories", {})
        
        all_stories = await StoryService.get_all_stories()
        
        # Get all stories that ever had leaderboard in ANY month
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
            
            member_reads = monthly_stats.get("medium_member_reads", 0)
            nonmember_reads = monthly_stats.get("medium_nonmember_reads", 0)
            total_reads = member_reads + nonmember_reads
            reads_percent = round((member_reads / total_reads) * 100, 1) if total_reads > 0 else 0
            
            member_views = monthly_stats.get("medium_member_views", 0)
            nonmember_views = monthly_stats.get("medium_nonmember_views", 0)
            total_views = member_views + nonmember_views
            views_percent = round((member_views / total_views) * 100, 1) if total_views > 0 else 0
            
            stories.append({
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
                "leaderboard": leaderboard,
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
        
        return {"stories": stories, "total": len(stories), "scope": "All Time"}
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


# ============================================
# STORY BY IDENTIFIER (Medium URL or Title)
# ============================================

"""
GET /api/stories/story/by-identifier/{identifier}
Description: Get story by Medium URL (preferred) or title (fallback)

curl -X GET "http://localhost:8000/api/stories/story/by-identifier/https%3A%2F%2Fmedium.com%2F%40username%2Fpost-title-78cb972195da" | jq '.'
curl -X GET "http://localhost:8000/api/stories/story/by-identifier/My%20Story%20Title" | jq '.'
"""
@router.get("/story/by-identifier/{identifier:path}")
async def get_story_by_identifier(identifier: str):
    """
    Get story by Medium URL (preferred) or title (fallback).
    - If identifier is a valid URL, try to find by medium_url
    - Otherwise, try to find by name (title)
    """
    try:
        decoded_identifier = unquote(identifier)
        
        all_stories = await StoryService.get_all_stories()
        story = None
        
        # Check if identifier looks like a URL
        is_url = decoded_identifier.startswith('http://') or decoded_identifier.startswith('https://')
        
        if is_url:
            # Try to find by medium_url
            normalized_url = decoded_identifier.rstrip('/')
            for s in all_stories:
                if s.medium_url and s.medium_url.rstrip('/') == normalized_url:
                    story = s
                    break
        
        # If not found by URL, try by name (title)
        if not story:
            for s in all_stories:
                if s.name and s.name.lower() == decoded_identifier.lower():
                    story = s
                    break
        
        # If still not found, try partial name match
        if not story:
            for s in all_stories:
                if s.name and decoded_identifier.lower() in s.name.lower():
                    story = s
                    break
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found for identifier: {decoded_identifier}")
        
        # Get current month stats
        now = datetime.now()
        monthly_stats = await MonthlyStorageService.get_story_monthly_stats(story.key, now.year, now.month) or {}
        
        return build_story_response(story, monthly_stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting story by identifier: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
PUT /api/stories/story/by-identifier/{identifier}
Description: Update story using Medium URL (preferred) or title (fallback)

curl -X PUT "http://localhost:8000/api/stories/story/by-identifier/https%3A%2F%2Fmedium.com%2F%40username%2Fpost-title-78cb972195da" \
  -H "Content-Type: application/json" \
  -d '{"status":"Published"}' | jq '.'
"""
@router.put("/story/by-identifier/{identifier:path}")
async def update_story_by_identifier(identifier: str, update_data: dict):
    """
    Update story using Medium URL (preferred) or title (fallback).
    """
    try:
        decoded_identifier = unquote(identifier)
        
        all_stories = await StoryService.get_all_stories()
        story = None
        
        # Check if identifier looks like a URL
        is_url = decoded_identifier.startswith('http://') or decoded_identifier.startswith('https://')
        
        if is_url:
            # Try to find by medium_url
            normalized_url = decoded_identifier.rstrip('/')
            for s in all_stories:
                if s.medium_url and s.medium_url.rstrip('/') == normalized_url:
                    story = s
                    break
        
        # If not found by URL, try by name (title)
        if not story:
            for s in all_stories:
                if s.name and s.name.lower() == decoded_identifier.lower():
                    story = s
                    break
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found for identifier: {decoded_identifier}")
        
        update = StoryUpdate(**update_data)
        updated_story = await StoryService.update_story(story.key, update)
        
        if not updated_story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        return {"success": True, "message": "Story updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating story by identifier: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# SINGLE STORY ENDPOINTS (Legacy - by key)
# ============================================

"""
GET /api/stories/story/{story_key}
Description: Get story metadata + current month stats by story key

curl -X GET "http://localhost:8000/api/stories/story/Miscellaneous/My%20Story" | jq '.'
"""
@router.get("/story/{story_key:path}")
async def get_story_with_current_stats(story_key: str):
    try:
        decoded_key = unquote(story_key)
        if decoded_key.endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        story = await StoryService.get_story(decoded_key)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        now = datetime.now()
        monthly_stats = await MonthlyStorageService.get_story_monthly_stats(decoded_key, now.year, now.month) or {}
        
        return build_story_response(story, monthly_stats)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting story with current stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/stories/story/{story_key}/stats
Description: Get all monthly stats for a story

curl -X GET "http://localhost:8000/api/stories/story/Miscellaneous/My%20Story/stats" | jq '.'
"""
@router.get("/story/{story_key:path}/stats")
async def get_story_all_monthly_stats(story_key: str):
    try:
        decoded_key = unquote(story_key)
        if decoded_key.endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        story = await StoryService.get_story(decoded_key)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        available_months = await MonthlyStorageService.get_available_months()
        months_data = []
        
        for month_info in available_months:
            monthly_stats = await MonthlyStorageService.get_story_monthly_stats(
                decoded_key, month_info["year"], month_info["month"]
            )
            if monthly_stats:
                member_reads = monthly_stats.get("medium_member_reads", 0)
                nonmember_reads = monthly_stats.get("medium_nonmember_reads", 0)
                reads = member_reads + nonmember_reads
                reads_percent = round((member_reads / reads) * 100, 1) if reads > 0 else 0
                
                member_views = monthly_stats.get("medium_member_views", 0)
                nonmember_views = monthly_stats.get("medium_nonmember_views", 0)
                views = member_views + nonmember_views
                views_percent = round((member_views / views) * 100, 1) if views > 0 else 0
                
                months_data.append({
                    "yearmonth": f"{month_info['year']}-{month_info['month']:02d}",
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
                    "medium_earnings": monthly_stats.get("medium_earnings", 0)
                })
        
        return {
            "story_key": decoded_key,
            "story_name": story.name,
            "months": months_data,
            "total_months": len(months_data)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting all monthly stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# UPDATE ENDPOINTS
# ============================================

"""
PUT /api/stories/story/{story_key}/stats/{yearmonth}
Description: Update monthly stats in stories-{yearmonth}.json

curl -X PUT "http://localhost:8000/api/stories/story/Miscellaneous/My%20Story/stats/2026-03" \
  -H "Content-Type: application/json" \
  -d '{
    "member_reads": 450,
    "nonmember_reads": 320,
    "member_views": 1200,
    "nonmember_views": 800,
    "claps": 89,
    "responses": 12,
    "leaderboard": true,
    "leaderboard_nanos": 30000000,
    "medium_earnings": 45.50
  }' | jq '.'
"""
@router.put("/story/{story_key:path}/stats/{yearmonth}")
async def update_story_monthly_stats(story_key: str, yearmonth: str, stats_data: dict):
    try:
        parts = yearmonth.split('-')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid yearmonth format")
        year = int(parts[0])
        month = int(parts[1])
        
        decoded_key = unquote(story_key)
        if decoded_key.endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        story = await StoryService.get_story(decoded_key)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        storage_data = {
            "medium_member_reads": stats_data.get("member_reads", 0),
            "medium_nonmember_reads": stats_data.get("nonmember_reads", 0),
            "medium_member_views": stats_data.get("member_views", 0),
            "medium_nonmember_views": stats_data.get("nonmember_views", 0),
            "claps": stats_data.get("claps", 0),
            "responses": stats_data.get("responses", 0),
            "leaderboard": stats_data.get("leaderboard", False),
            "leaderboard_nanos": stats_data.get("leaderboard_nanos", 0),
            "medium_earnings": stats_data.get("medium_earnings", 0)
        }
        
        success = await MonthlyStorageService.update_story_monthly_stats(
            decoded_key, year, month, storage_data, story.name
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update monthly stats")
        
        return {"success": True, "message": "Monthly stats updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating monthly stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# CREATE, DELETE, PUBLISH, SYNC
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
DELETE /api/stories/story/{story_key}
Description: Delete a story

curl -X DELETE "http://localhost:8000/api/stories/story/Miscellaneous/My%20Story" | jq '.'
"""
@router.delete("/story/{story_key:path}")
async def delete_story(story_key: str):
    try:
        decoded_key = unquote(story_key)
        if decoded_key.endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        deleted = await StoryService.delete_story(decoded_key)
        if not deleted:
            raise HTTPException(status_code=404, detail="Story not found")
        
        return {"success": True, "message": "Story deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting story: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/stories/sync
Description: Sync filesystem with stories.json

curl -X POST "http://localhost:8000/api/stories/sync" | jq '.'
"""
@router.post("/sync")
async def sync_stories():
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


# ============================================
# UTILITY ENDPOINTS
# ============================================

"""
GET /api/stories/months
Description: Get list of available months for dropdown

curl -X GET "http://localhost:8000/api/stories/months" | jq '.'
"""
@router.get("/months")
async def get_available_months():
    try:
        months = await MonthlyStorageService.get_available_months()
        formatted_months = [f"{m['year']}-{m['month']:02d}" for m in months]
        formatted_months.sort(reverse=True)
        return {"months": formatted_months}
    except Exception as e:
        logger.error(f"Error getting available months: {e}")
        return {"months": []}


"""
GET /api/stories/leaderboard-status
Description: Get leaderboard status for all stories

curl -X GET "http://localhost:8000/api/stories/leaderboard-status" | jq '.'
"""
@router.get("/leaderboard-status")
async def get_leaderboard_status():
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
            "total_nanos": total_nanos
        }
    except Exception as e:
        logger.error(f"Error getting leaderboard status: {e}")
        return {"leaderboard_stories": [], "total": 0, "total_nanos": 0}


"""
POST /api/stories/fetch-leaderboard-stats/{yearmonth}
Description: Fetch leaderboard stats from Medium API

curl -X POST "http://localhost:8000/api/stories/fetch-leaderboard-stats/2026-03" | jq '.'
"""
@router.post("/fetch-leaderboard-stats/{yearmonth}")
async def fetch_leaderboard_stats(yearmonth: str):
    try:
        parts = yearmonth.split('-')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid yearmonth format")
        
        year = int(parts[0])
        month = int(parts[1])
        
        api_service = get_medium_api_service()
        
        if not api_service.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        earnings = api_service.fetch_leaderboard_earnings("mvineetsharma", year, month)
        
        if not earnings:
            return {"success": False, "message": "No earnings data found", "updated": 0, "added": 0}
        
        all_stories = await StoryService.get_all_stories()
        monthly_data = await MonthlyStorageService.load_monthly_stats(year, month)
        
        updated_count = 0
        added_count = 0
        
        for earning in earnings:
            medium_url = earning.get('medium_url')
            title = earning.get('title')
            nanos = earning.get('nanos', 0)
            
            if not medium_url or not title:
                continue
            
            # Find existing story by URL
            existing_story = None
            for story in all_stories:
                if story.medium_url and story.medium_url.rstrip('/') == medium_url.rstrip('/'):
                    existing_story = story
                    break
            
            if existing_story:
                story_key = existing_story.key
                monthly_data["stories"][story_key] = {
                    "title": title,
                    "leaderboard": True,
                    "leaderboard_nanos": nanos,
                    "medium_url": medium_url,
                    "last_stats_update": datetime.now().isoformat()
                }
                updated_count += 1
            else:
                import re
                story_key = re.sub(r'[^\w\s-]', '', title).lower()
                story_key = re.sub(r'[\s]+', '-', story_key).strip('-')
                story_key = story_key[:100]
                
                monthly_data["stories"][story_key] = {
                    "title": title,
                    "leaderboard": True,
                    "leaderboard_nanos": nanos,
                    "medium_url": medium_url,
                    "last_stats_update": datetime.now().isoformat()
                }
                added_count += 1
        
        await MonthlyStorageService.save_monthly_stats(year, month, monthly_data)
        
        return {
            "success": True,
            "message": f"Leaderboard stats fetched for {yearmonth}",
            "year": year,
            "month": month,
            "updated": updated_count,
            "added": added_count
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching leaderboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))