"""
Stories Router - Complete endpoints with curl examples
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from urllib.parse import unquote

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


# ============================================
# LIST ENDPOINTS
# ============================================

"""
GET /api/stories/list
Description: Dashboard view - All stories from stories.json + current month stats
           Leaderboard = TRUE if story ever had leaderboard in ANY month

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
                "created_date": story.created_date,
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
           Leaderboard = TRUE only for this specific month

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
                    "created_date": story.created_date,
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
                    "created_date": None,
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
# FETCH STATS FROM MEDIUM API
# ============================================

"""
POST /api/stories/fetch-story-stats/{post_id}/{yearmonth}
Description: Fetch stats for a specific story and month from Medium API

curl -X POST "http://localhost:8000/api/stories/fetch-story-stats/78cb972195da/2026-04" | jq '.'
"""
@router.post("/fetch-story-stats/{post_id}/{yearmonth}")
async def fetch_story_stats_for_month(post_id: str, yearmonth: str):
    """
    Fetch stats for a specific story and month from Medium API.
    """
    try:
        # Parse yearmonth
        parts = yearmonth.split('-')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid yearmonth format. Use YYYY-MM")
        
        year = int(parts[0])
        month = int(parts[1])
        
        logger.info(f"📊 Fetching stats for post_id: {post_id} for {year}-{month:02d}")
        
        # Use the Medium API service
        api_service = get_medium_api_service()
        
        if not api_service.is_authenticated():
            raise HTTPException(
                status_code=401, 
                detail="Not authenticated. Please log into Medium in your browser and try again."
            )
        
        # Fetch monthly stats from Medium API (pass year and month directly)
        monthly_response = api_service.fetch_stats(post_id, year, month)
        
        if not monthly_response:
            raise HTTPException(status_code=502, detail="Failed to fetch monthly stats from Medium API")
        
        # Parse the monthly response
        parsed_stats = api_service.parse_stats_response(monthly_response, post_id)
        
        # Fetch lifetime stats from Medium API
        lifetime_response = api_service.fetch_lifetime_stats(post_id)
        lifetime_stats = {}
        if lifetime_response:
            lifetime_stats = api_service.parse_lifetime_response(lifetime_response, post_id)
        
        # Find story by post_id in stories.json
        all_stories = await StoryService.get_all_stories()
        story = None
        story_key = None
        
        for s in all_stories:
            if s.medium_url and post_id in s.medium_url:
                story = s
                story_key = s.key
                break
        
        # Prepare result
        result = {
            "success": True,
            "post_id": post_id,
            "yearmonth": yearmonth,
            "story_key": story_key,
            "story_name": story.name if story else None,
            "medium_url": story.medium_url if story else None,
            "stats": {
                "title": parsed_stats.get('title'),
                "first_published": parsed_stats.get('first_published'),
                "reading_time": parsed_stats.get('reading_time'),
                "word_count": parsed_stats.get('word_count'),
                "totals": parsed_stats.get('totals', {})
            },
            "lifetime": {
                "reads": lifetime_stats.get('lifetime_reads', 0),
                "views": lifetime_stats.get('lifetime_views', 0),
                "presentation_count": lifetime_stats.get('presentation_count', 0),
                "feed_click_through_rate": lifetime_stats.get('feed_click_through_rate', 0)
            }
        }
        
        # If story found, update the monthly file and stories.json
        if story and story_key:
            # Prepare monthly stats data
            storage_data = {
                "medium_member_reads": parsed_stats['totals'].get('member_reads', 0),
                "medium_nonmember_reads": parsed_stats['totals'].get('nonmember_reads', 0),
                "medium_member_views": parsed_stats['totals'].get('member_views', 0),
                "medium_nonmember_views": parsed_stats['totals'].get('nonmember_views', 0),
                "claps": parsed_stats['totals'].get('claps', 0),
                "responses": parsed_stats['totals'].get('replies', 0),
                "medium_highlights": parsed_stats['totals'].get('highlights', 0),
                "medium_new_followers": parsed_stats['totals'].get('new_followers', 0),
                "medium_read_ratio": parsed_stats['totals'].get('read_ratio', 0),
                "medium_member_read_percentage": parsed_stats['totals'].get('member_read_percentage', 0),
                "reads": parsed_stats['totals'].get('total_reads', 0),
                "view_count": parsed_stats['totals'].get('total_views', 0),
                "medium_earnings": parsed_stats['totals'].get('earnings', 0)
            }
            
            # Update the monthly file
            await MonthlyStorageService.update_story_monthly_stats(
                story_key, year, month, storage_data, story.name
            )
            
            # Update lifetime stats in stories.json
            if lifetime_stats:
                await StoryService.update_story(story_key, StoryUpdate(
                    lifetime_reads=lifetime_stats.get('lifetime_reads', 0),
                    lifetime_views=lifetime_stats.get('lifetime_views', 0),
                    presentation_count=lifetime_stats.get('presentation_count', 0),
                    feed_click_through_rate=lifetime_stats.get('feed_click_through_rate', 0),
                    medium_first_published=parsed_stats.get('first_published'),
                    medium_reading_time=parsed_stats.get('reading_time'),
                    word_count=parsed_stats.get('word_count'),
                    medium_title=parsed_stats.get('title')
                ))
            
            result["updated"] = True
        else:
            result["updated"] = False
            result["message"] = f"No story found with post_id {post_id} in stories.json"
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching story stats: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/stories/fetch-story-stats/{post_id}
Description: Fetch stats for a story for the current month using post_id

curl -X POST "http://localhost:8000/api/stories/fetch-story-stats/78cb972195da" | jq '.'
"""
@router.post("/fetch-story-stats/{post_id}")
async def fetch_story_stats_current_month_by_post_id(post_id: str):
    """Fetch stats for current month using post_id"""
    now = datetime.now()
    yearmonth = f"{now.year}-{now.month:02d}"
    return await fetch_story_stats_for_month(post_id, yearmonth)


# ============================================
# SINGLE STORY ENDPOINTS
# ============================================

"""
GET /api/stories/story/{story_key}/stats
Description: Get all monthly stats for a story (list of months)

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


"""
GET /api/stories/story/{story_key}/{yearmonth}
Description: Get story metadata + specific month stats

curl -X GET "http://localhost:8000/api/stories/story/Miscellaneous/My%20Story/2026-03" | jq '.'
"""
@router.get("/story/{story_key:path}/{yearmonth}")
async def get_story_with_month_stats(story_key: str, yearmonth: str):
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
        
        monthly_stats = await MonthlyStorageService.get_story_monthly_stats(decoded_key, year, month) or {}
        
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
            "status": story.status,
            "published_date": story.published_date,
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
            "created_date": story.created_date,
            "word_count": story.word_count or 0,
            "reading_time": story.medium_reading_time or story.read_time or 0,
            "presentation_count": story.presentation_count or 0,
            "lifetime_reads": story.lifetime_reads or 0,
            "lifetime_views": story.lifetime_views or 0,
            "lifetime_claps": story.lifetime_claps or 0,
            "feed_click_through_rate": story.feed_click_through_rate or 0,
            "medium_earnings": monthly_stats.get("medium_earnings", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_story_with_month_stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/stories/story/{story_key}
Description: Get story metadata + current month stats

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
            "status": story.status,
            "published_date": story.published_date,
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
            "created_date": story.created_date,
            "word_count": story.word_count or 0,
            "reading_time": story.medium_reading_time or story.read_time or 0,
            "presentation_count": story.presentation_count or 0,
            "lifetime_reads": story.lifetime_reads or 0,
            "lifetime_views": story.lifetime_views or 0,
            "lifetime_claps": story.lifetime_claps or 0,
            "feed_click_through_rate": story.feed_click_through_rate or 0,
            "medium_earnings": monthly_stats.get("medium_earnings", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting story with current stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# UPDATE ENDPOINTS
# ============================================

"""
PUT /api/stories/story/{story_key}
Description: Update story metadata in stories.json

curl -X PUT "http://localhost:8000/api/stories/story/Miscellaneous/My%20Story" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "Published",
    "published_date": "2026-03-27",
    "medium_url": "https://medium.com/@username/post-title-78cb972195da",
    "tags": ["python", "tutorial"],
    "notes": "Updated notes",
    "series": "Python Series",
    "linkedin_status": "posted",
    "linkedin_impressions": 1500
  }' | jq '.'
"""
@router.put("/story/{story_key:path}")
async def update_story_metadata(story_key: str, update_data: dict):
    try:
        decoded_key = unquote(story_key)
        if decoded_key.endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        update = StoryUpdate(**update_data)
        story = await StoryService.update_story(decoded_key, update)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        return {"success": True, "message": "Story metadata updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating story metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    "folder": "Python",
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
                "name": story.name
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
POST /api/stories/story/{story_key}/publish
Description: Mark a story as published

curl -X POST "http://localhost:8000/api/stories/story/Miscellaneous/My%20Story/publish" \
  -H "Content-Type: application/json" \
  -d '{
    "medium_url": "https://medium.com/@username/post-title-78cb972195da"
  }' | jq '.'
"""
@router.post("/story/{story_key:path}/publish")
async def publish_story(story_key: str, medium_url: Optional[str] = None):
    try:
        decoded_key = unquote(story_key)
        if decoded_key.endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        story = await StoryService.publish_story(decoded_key, medium_url)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        return {"success": True, "message": "Story marked as published"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing story: {e}")
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
        return {"months": formatted_months}
    except Exception as e:
        logger.error(f"Error getting available months: {e}")
        return {"months": []}


"""
GET /api/stories/leaderboard-status
Description: Get leaderboard status for all stories (True if ever been on leaderboard)

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
Description: Fetch leaderboard stats from JSON files and populate monthly file

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
            return {"success": False, "message": "No earnings data found"}
        
        # Process earnings and update monthly files
        updated_count = 0
        added_count = 0
        
        # Get all existing stories
        all_stories = await StoryService.get_all_stories()
        
        # Load or create monthly file
        monthly_data = await MonthlyStorageService.load_monthly_stats(year, month)
        
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
                # Create a story key from title
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
        
        # Save monthly file
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