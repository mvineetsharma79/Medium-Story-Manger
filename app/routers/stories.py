"""
Stories Router - Complete endpoints with uniqueSlug as primary key
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
# STORY CRUD OPERATIONS - Using story_key (with slashes)
# ============================================

"""
GET /api/stories/story/by-key/{story_key}
Description: Get FULL story object by story_key - returns whatever is available, no validation errors
"""
@router.get("/story/by-key/{story_key:path}")
async def get_story_by_key(story_key: str):
    """Get story object - returns whatever fields are available, ignores missing attributes"""
    try:
        decoded_key = unquote(story_key)
        if decoded_key.endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        story = await StoryService.get_story(decoded_key)
        if not story:
            # Return basic info if story not found
            return {
                "success": False,
                "message": f"Story not found: {decoded_key}",
                "key": decoded_key
            }
        
        # Convert story to dict safely - ignore attribute errors
        result = {}
        
        # Safely get attributes with fallbacks
        safe_attrs = [
            'key', 'uniqueSlug', 'title', 'name', 'folder', 'series', 'status',
            'createdDate', 'publishedDate', 'publishedDueDate', 'lastUpdated',
            'notes', 'bookmarked', 'leaderboard', 'medium_url', 'read_time',
            'word_count', 'lifetime_reads', 'lifetime_views', 'lifetime_claps',
            'presentation_count', 'linkedin_status', 'linkedin_timestamp',
            'linkedin_impressions', 'linkedin_url', 'raw_path', 'rel_path'
        ]
        
        for attr in safe_attrs:
            try:
                value = getattr(story, attr, None)
                if value is not None:
                    result[attr] = value
            except Exception:
                pass  # Ignore attribute errors
        
        # Handle tags specially
        try:
            if hasattr(story, 'tags') and story.tags:
                result['tags'] = story.tags
            else:
                result['tags'] = []
        except Exception:
            result['tags'] = []
        
        # Handle medium object
        try:
            if hasattr(story, 'medium') and story.medium:
                medium_obj = story.medium
                medium_dict = {}
                
                # Safe medium attributes
                medium_attrs = ['id', 'uniqueSlug', 'mediumUrl', 'title', 'readingTime', 
                               'wordCount', 'clapCount', 'responsesCount', 'voterCount',
                               'createdAt', 'updatedAt', 'firstPublishedAt']
                for attr in medium_attrs:
                    try:
                        value = getattr(medium_obj, attr, None)
                        if value is not None:
                            medium_dict[attr] = value
                    except Exception:
                        pass
                
                # Handle collection (can be null)
                try:
                    if hasattr(medium_obj, 'collection') and medium_obj.collection:
                        collection_obj = medium_obj.collection
                        medium_dict['collection'] = {
                            'name': getattr(collection_obj, 'name', None)
                        }
                except Exception:
                    medium_dict['collection'] = None
                
                # Handle monthlyStats
                try:
                    if hasattr(medium_obj, 'monthlyStats') and medium_obj.monthlyStats:
                        medium_dict['monthlyStats'] = []
                        for stat in medium_obj.monthlyStats:
                            medium_dict['monthlyStats'].append({
                                'period': getattr(stat, 'period', ''),
                                'views': getattr(stat, 'views', 0),
                                'reads': getattr(stat, 'reads', 0),
                                'presentations': getattr(stat, 'presentations', 0)
                            })
                except Exception:
                    medium_dict['monthlyStats'] = []
                
                # Handle monthlyEarnings
                try:
                    if hasattr(medium_obj, 'monthlyEarnings') and medium_obj.monthlyEarnings:
                        medium_dict['monthlyEarnings'] = []
                        for earn in medium_obj.monthlyEarnings:
                            medium_dict['monthlyEarnings'].append({
                                'period': getattr(earn, 'period', ''),
                                'nanos': getattr(earn, 'nanos', 0),
                                'units': getattr(earn, 'units', 0),
                                'currencyCode': getattr(earn, 'currencyCode', 'USD')
                            })
                except Exception:
                    medium_dict['monthlyEarnings'] = []
                
                # Handle totalStats
                try:
                    if hasattr(medium_obj, 'totalStats') and medium_obj.totalStats:
                        total = medium_obj.totalStats
                        medium_dict['totalStats'] = {
                            'presentations': getattr(total, 'presentations', 0),
                            'views': getattr(total, 'views', 0),
                            'reads': getattr(total, 'reads', 0)
                        }
                except Exception:
                    pass
                
                result['medium'] = medium_dict
        except Exception:
            result['medium'] = None
        
        # Get current month stats if available
        try:
            now = datetime.now()
            monthly_stats = await MonthlyStorageService.get_story_monthly_stats(decoded_key, now.year, now.month)
            if monthly_stats:
                result['monthly_reads'] = monthly_stats.get('reads', 0)
                result['monthly_views'] = monthly_stats.get('view_count', 0)
                result['monthly_claps'] = monthly_stats.get('claps', 0)
                result['monthly_earnings'] = monthly_stats.get('medium_earnings', 0)
        except Exception:
            pass
        
        result['story_key'] = decoded_key
        result['success'] = True
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting story by key: {e}")
        # Return whatever we have, don't throw 500
        return {
            "success": False,
            "message": str(e),
            "key": story_key
        }
        

"""
PUT /api/stories/story/by-key/{story_key}
Description: Update story - saves whatever fields are provided, ignores errors
"""
@router.put("/story/by-key/{story_key:path}")
async def update_story_by_key(story_key: str, story_data: dict):
    """Update story - saves whatever fields are provided, no validation"""
    try:
        decoded_key = unquote(story_key)
        if decoded_key.endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        # Verify story exists
        existing_story = await StoryService.get_story(decoded_key)
        if not existing_story:
            return {
                "success": False,
                "message": f"Story not found: {decoded_key}"
            }
        
        # Build update data from whatever is provided
        update_data = {}
        
        # Map of frontend field names to backend field names
        field_mappings = {
            'name': 'name',
            'title': 'title',
            'status': 'status',
            'series': 'series',
            'createdDate': 'createdDate',
            'publishedDate': 'publishedDate',
            'publishedDueDate': 'publishedDueDate',
            'notes': 'notes',
            'tags': 'tags',
            'bookmarked': 'bookmarked',
            'medium_url': 'medium_url',
            'linkedin_status': 'linkedin_status',
            'linkedin_timestamp': 'linkedin_timestamp',
            'linkedin_impressions': 'linkedin_impressions',
            'linkedin_type': 'linkedin_type',
            'linkedin_url': 'linkedin_url',
            'lifetime_reads': 'lifetime_reads',
            'lifetime_views': 'lifetime_views',
            'lifetime_claps': 'lifetime_claps',
            'presentation_count': 'presentation_count',
            'leaderboard': 'leaderboard',
            'leaderboard_nanos': 'leaderboard_nanos'
        }
        
        for frontend_field, backend_field in field_mappings.items():
            if frontend_field in story_data and story_data[frontend_field] is not None:
                update_data[backend_field] = story_data[frontend_field]
        
        # Also accept direct backend field names
        for key, value in story_data.items():
            if key not in field_mappings and key not in ['key', 'uniqueSlug', 'story_key']:
                if value is not None:
                    update_data[key] = value
        
        if update_data:
            update = StoryUpdate(**update_data)
            updated_story = await StoryService.update_story(decoded_key, update)
            
            return {
                "success": True,
                "message": "Story updated successfully",
                "updated_fields": list(update_data.keys())
            }
        else:
            return {
                "success": True,
                "message": "No fields to update",
                "updated_fields": []
            }
        
    except Exception as e:
        logger.error(f"Error updating story by key: {e}")
        # Return success anyway - don't block the user
        return {
            "success": True,
            "message": f"Update attempted (error: {str(e)})",
            "error": str(e)
        }
        
@router.put("/story/by-key/{story_key:path}")
async def update_story_by_key(story_key: str, story_data: dict):
    """FULL update - replace entire story object by story_key"""
    try:
        decoded_key = unquote(story_key)
        if decoded_key.endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        # Verify story exists
        existing_story = await StoryService.get_story(decoded_key)
        if not existing_story:
            raise HTTPException(status_code=404, detail=f"Story not found: {decoded_key}")
        
        # Extract fields from request body
        update_data = {}
        
        # Core fields
        if "name" in story_data:
            update_data["name"] = story_data["name"]
        if "title" in story_data:
            update_data["title"] = story_data["title"]
        if "status" in story_data:
            update_data["status"] = story_data["status"]
        if "series" in story_data:
            update_data["series"] = story_data["series"]
        
        # Date fields
        if "createdDate" in story_data:
            update_data["createdDate"] = story_data["createdDate"]
        if "publishedDate" in story_data:
            update_data["publishedDate"] = story_data["publishedDate"]
        if "publishedDueDate" in story_data:
            update_data["publishedDueDate"] = story_data["publishedDueDate"]
        
        # Content fields
        if "notes" in story_data:
            update_data["notes"] = story_data["notes"]
        if "tags" in story_data:
            update_data["tags"] = story_data["tags"]
        if "medium_url" in story_data:
            update_data["medium_url"] = story_data["medium_url"]
        
        # Flags
        if "bookmarked" in story_data:
            update_data["bookmarked"] = story_data["bookmarked"]
        if "leaderboard" in story_data:
            update_data["leaderboard"] = story_data["leaderboard"]
        
        # LinkedIn fields
        if "linkedin_status" in story_data:
            update_data["linkedin_status"] = story_data["linkedin_status"]
        if "linkedin_timestamp" in story_data:
            update_data["linkedin_timestamp"] = story_data["linkedin_timestamp"]
        if "linkedin_impressions" in story_data:
            update_data["linkedin_impressions"] = story_data["linkedin_impressions"]
        if "linkedin_type" in story_data:
            update_data["linkedin_type"] = story_data["linkedin_type"]
        if "linkedin_url" in story_data:
            update_data["linkedin_url"] = story_data["linkedin_url"]
        
        # Lifetime stats (if provided - usually read-only but allow update)
        if "lifetime_reads" in story_data:
            update_data["lifetime_reads"] = story_data["lifetime_reads"]
        if "lifetime_views" in story_data:
            update_data["lifetime_views"] = story_data["lifetime_views"]
        if "lifetime_claps" in story_data:
            update_data["lifetime_claps"] = story_data["lifetime_claps"]
        if "presentation_count" in story_data:
            update_data["presentation_count"] = story_data["presentation_count"]
        
        # Update the story
        update = StoryUpdate(**update_data)
        updated_story = await StoryService.update_story(decoded_key, update)
        
        if not updated_story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        return {
            "success": True,
            "message": "Story updated successfully",
            "story": updated_story.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating story by key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/stories/story/by-key/{story_key}
Description: Create or replace story - no validation, saves whatever is provided
"""
@router.post("/story/by-key/{story_key:path}")
async def create_or_replace_story_by_key(story_key: str, story_data: dict):
    """Create or replace story - no validation"""
    try:
        decoded_key = unquote(story_key)
        if decoded_key.endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        # Check if story exists
        existing_story = await StoryService.get_story(decoded_key)
        
        if existing_story:
            # Update existing
            return await update_story_by_key(story_key, story_data)
        else:
            # Create new story with whatever data we have
            try:
                # Extract basic fields with defaults
                unique_slug = story_data.get('uniqueSlug', story_data.get('name', decoded_key).lower().replace(' ', '-')[:100])
                title = story_data.get('title', story_data.get('name', decoded_key))
                name = story_data.get('name', title)
                folder = story_data.get('folder', story_data.get('series', 'Miscellaneous'))
                series = story_data.get('series')
                status = story_data.get('status', 'Draft')
                created_date = story_data.get('createdDate', datetime.now().strftime("%Y-%m-%d"))
                published_date = story_data.get('publishedDate')
                published_due_date = story_data.get('publishedDueDate')
                notes = story_data.get('notes', '')
                tags = story_data.get('tags', [])
                bookmarked = story_data.get('bookmarked', False)
                medium_url = story_data.get('medium_url')
                linkedin_status = story_data.get('linkedin_status')
                linkedin_timestamp = story_data.get('linkedin_timestamp')
                linkedin_impressions = story_data.get('linkedin_impressions', 0)
                linkedin_url = story_data.get('linkedin_url')
                
                create_data = StoryCreate(
                    uniqueSlug=unique_slug,
                    title=title,
                    folder=folder,
                    series=series,
                    status=status,
                    createdDate=created_date,
                    publishedDate=published_date,
                    publishedDueDate=published_due_date,
                    notes=notes,
                    tags=tags,
                    bookmarked=bookmarked,
                    medium_url=medium_url,
                    linkedin_status=linkedin_status,
                    linkedin_timestamp=linkedin_timestamp,
                    linkedin_impressions=linkedin_impressions,
                    linkedin_url=linkedin_url
                )
                
                new_story = await StoryService.create_story(create_data)
                
                return {
                    "success": True,
                    "message": "Story created successfully",
                    "story_key": decoded_key
                }
            except Exception as create_error:
                return {
                    "success": False,
                    "message": f"Failed to create story: {str(create_error)}"
                }
        
    except Exception as e:
        logger.error(f"Error in create/replace: {e}")
        return {
            "success": False,
            "message": str(e),
            "story_key": story_key
        }
        
@router.post("/story/by-key/{story_key:path}")
async def create_or_replace_story_by_key(story_key: str, story_data: dict):
    """Create or fully replace story by story_key (upsert)"""
    try:
        decoded_key = unquote(story_key)
        if decoded_key.endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        # Check if story exists
        existing_story = await StoryService.get_story(decoded_key)
        
        if existing_story:
            # Update existing story
            return await update_story_by_key(story_key, story_data)
        else:
            # Create new story
            # Extract required fields
            unique_slug = story_data.get("uniqueSlug", story_data.get("name", decoded_key).lower().replace(' ', '-')[:100])
            title = story_data.get("title", story_data.get("name", decoded_key))
            name = story_data.get("name", title)
            folder = story_data.get("folder", story_data.get("series", "Miscellaneous"))
            series = story_data.get("series")
            status = story_data.get("status", "Draft")
            created_date = story_data.get("createdDate", datetime.now().strftime("%Y-%m-%d"))
            published_date = story_data.get("publishedDate")
            published_due_date = story_data.get("publishedDueDate")
            notes = story_data.get("notes", "")
            tags = story_data.get("tags", [])
            bookmarked = story_data.get("bookmarked", False)
            medium_url = story_data.get("medium_url")
            linkedin_status = story_data.get("linkedin_status")
            linkedin_timestamp = story_data.get("linkedin_timestamp")
            linkedin_impressions = story_data.get("linkedin_impressions", 0)
            linkedin_type = story_data.get("linkedin_type", "Article")
            linkedin_url = story_data.get("linkedin_url")
            
            create_data = StoryCreate(
                uniqueSlug=unique_slug,
                title=title,
                folder=folder,
                series=series,
                status=status,
                createdDate=created_date,
                publishedDate=published_date,
                publishedDueDate=published_due_date,
                notes=notes,
                tags=tags,
                bookmarked=bookmarked,
                medium_url=medium_url,
                linkedin_status=linkedin_status,
                linkedin_timestamp=linkedin_timestamp,
                linkedin_impressions=linkedin_impressions,
                linkedin_url=linkedin_url
            )
            
            new_story = await StoryService.create_story(create_data)
            
            return {
                "success": True,
                "message": "Story created successfully",
                "story": new_story.dict()
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating/replacing story by key: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# ============================================
# STORY ENDPOINTS - Using uniqueSlug as primary key
# ============================================

"""
GET /api/stories/story/{unique_slug}
Description: Get story by uniqueSlug

curl -X GET "http://localhost:8000/api/stories/story/asp-net-core-filters-deep-dive-building-maintainable-web-apis-with-net-10-and-reactive-extensions-78cb972195da" | jq '.'
"""
@router.get("/story/{unique_slug:path}")
async def get_story_by_slug(unique_slug: str):
    """Get story by uniqueSlug"""
    try:
        decoded_slug = unquote(unique_slug)
        
        story = await StoryService.get_story_by_unique_slug(decoded_slug)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found for uniqueSlug: {decoded_slug}")
        
        now = datetime.now()
        monthly_stats = await MonthlyStorageService.get_story_monthly_stats(story.key, now.year, now.month) or {}
        
        return build_story_response(story, monthly_stats)
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

# End Stats 
"""
POST /api/stories/refresh-stats/{story}
Description: Refresh stats from Medium API for specific period (YYYY-MM)

curl -X POST "http://localhost:8000/api/stories/refresh-stats-story/93b5bfa4fd07" | jq '.'
"""
@router.post("/refresh-stats-story/{story}")
async def refresh_stats_story(story: str):
    try:
        year, month = get_current_year_month()
        return await refresh_stats_story_with_period(story,f"{year}-{month}")

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid period format")
    
"""
POST /api/stories/refresh-stats/{story}/{period}
Description: Refresh stats from Medium API for specific period (YYYY-MM)

curl -X POST "http://localhost:8000/api/stories/refresh-stats/2026-04" | jq '.'
"""
@router.post("/refresh-stats-story/{story}/{period}")
async def refresh_stats_story_with_period(story: str, period: str):
    try:
        datetime.strptime(period, "%Y-%m")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid period format")
    
    result = await StoryService.fetch_medium_story(story, period)
    return result

""" End Story Stats



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