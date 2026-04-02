from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Optional
import logging
from urllib.parse import unquote
from datetime import datetime
import time

from app.services.story_service import StoryService
from app.services.medium_stats_fetcher import MediumStatsFetcher
from app.models import StoryCreate, StoryUpdate, StoryResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def normalize_url(url: str) -> str:
    """Normalize URL for comparison"""
    if not url:
        return url
    url = url.replace('https://', '').replace('http://', '')
    url = url.rstrip('/')
    return url.lower()


def safe_divide(numerator: float, denominator: float, default: float = 0) -> float:
    """Safely divide two numbers"""
    if denominator == 0:
        return default
    return round(numerator / denominator, 2)


# ============================================
# DEBUG ENDPOINTS
# ============================================

@router.get("/debug/all")
async def debug_all():
    """Debug endpoint to list all stories"""
    try:
        stories = await StoryService.get_all_stories()
        return {
            "total": len(stories),
            "stories": [
                {
                    "key": s.key,
                    "name": s.name,
                    "medium_url": s.medium_url,
                    "status": s.status,
                    "medium_first_published": s.medium_first_published
                }
                for s in stories
            ]
        }
    except Exception as e:
        logger.error(f"Debug all error: {e}")
        return {"error": str(e)}


@router.get("/debug/urls")
async def debug_urls():
    """Debug endpoint to list all stories with Medium URLs"""
    try:
        stories = await StoryService.get_all_stories()
        urls_with_keys = [
            {
                "key": s.key,
                "name": s.name,
                "medium_url": s.medium_url,
                "medium_first_published": s.medium_first_published
            }
            for s in stories if s.medium_url
        ]
        return {
            "total": len(urls_with_keys),
            "urls": urls_with_keys
        }
    except Exception as e:
        logger.error(f"Debug URLs error: {e}")
        return {"error": str(e)}


@router.get("/debug/keys")
async def debug_keys():
    """Debug endpoint to list all story keys"""
    try:
        stories = await StoryService.get_all_stories()
        return {
            "total": len(stories),
            "keys": [s.key for s in stories]
        }
    except Exception as e:
        logger.error(f"Debug keys error: {e}")
        return {"error": str(e)}


@router.get("/debug/find/{search}")
async def find_story(search: str):
    """Find stories containing search term"""
    try:
        stories = await StoryService.get_all_stories()
        matches = [
            {"key": s.key, "name": s.name, "medium_url": s.medium_url}
            for s in stories if search.lower() in s.key.lower() or search.lower() in s.name.lower() or (s.medium_url and search.lower() in s.medium_url.lower())
        ]
        return {"search": search, "matches": matches}
    except Exception as e:
        logger.error(f"Find story error: {e}")
        return {"error": str(e)}


# ============================================
# MEDIUM STATS ENDPOINTS
# ============================================

@router.get("/stats-by-url")
async def get_stats_dashboard_by_url(medium_url: str):
    """Get stats dashboard for a story using its Medium URL"""
    try:
        if not medium_url:
            return {"error": "Medium URL is required"}
        
        from urllib.parse import unquote
        decoded_url = unquote(medium_url)
        
        all_stories = await StoryService.get_all_stories()
        
        story = None
        normalized_query = normalize_url(decoded_url)
        
        for s in all_stories:
            if s.medium_url:
                if normalize_url(s.medium_url) == normalized_query:
                    story = s
                    break
        
        if not story:
            available = [s.medium_url for s in all_stories if s.medium_url]
            return {
                "error": "Story not found",
                "your_url": decoded_url,
                "available_urls": available[:5] if available else []
            }
        
        return {
            "story_key": story.key,
            "story_name": story.name,
            "medium_url": story.medium_url,
            "last_stats_update": story.last_stats_update,
            "medium_first_published": story.medium_first_published,
            "medium_publication": story.medium_publication,
            "current_month": {
                "reads": story.reads or 0,
                "claps": story.claps or 0,
                "views": story.view_count or 0,
                "responses": story.responses or 0,
                "member_reads": story.medium_member_reads or 0,
                "member_views": story.medium_member_views or 0,
                "nonmember_reads": story.medium_nonmember_reads or 0,
                "nonmember_views": story.medium_nonmember_views or 0,
                "read_ratio": story.read_ratio or 0,
                "member_read_percentage": story.medium_member_read_percentage or 0,
                "new_followers": story.medium_new_followers or 0
            },
            "lifetime": {
                "reads": story.lifetime_reads or 0,
                "views": story.lifetime_views or 0,
                "presentation_count": story.presentation_count or 0
            },
            "content": {
                "word_count": story.word_count or 0,
                "reading_time": story.medium_reading_time or story.read_time or 0
            },
            "metadata": {
                "title": story.medium_title or story.name,
                "first_published": story.medium_first_published or story.created_date,
                "last_updated": story.medium_last_updated or story.last_updated,
                "publication": story.medium_publication or ""
            }
        }
        
    except Exception as e:
        logger.error(f"Get stats dashboard error: {e}")
        return {"error": str(e)}


@router.post("/fetch-stats")
async def fetch_all_medium_stats():
    """Fetch ONLY current month stats for all stories with URLs"""
    try:
        logger.info("=" * 60)
        logger.info("FETCHING CURRENT MONTH STATS FOR ALL STORIES")
        logger.info("=" * 60)
        
        stories = await StoryService.get_all_stories()
        stories_with_urls = [{"key": s.key, "name": s.name, "medium_url": s.medium_url} 
                            for s in stories if s.medium_url]

        logger.info(f"Found {len(stories_with_urls)} stories with Medium URLs")

        if not stories_with_urls:
            return {"message": "No stories with Medium URLs", "updated": 0, "total": 0}

        fetcher = MediumStatsFetcher()
        
        if not fetcher.is_authenticated():
            logger.error("Not authenticated - no valid cookies found")
            return {"error": "Not authenticated. Please log into Medium in your browser, then close browser and try again."}
        
        results = {
            'total': len(stories_with_urls),
            'updated': 0,
            'failed': 0,
            'details': []
        }
        
        for i, story in enumerate(stories_with_urls):
            try:
                logger.info(f"\n📊 ({i+1}/{len(stories_with_urls)}): {story['name']}")
                
                if i > 0:
                    logger.info("   Waiting 3 seconds to avoid rate limiting...")
                    time.sleep(3)
                
                # Fetch ONLY current month stats
                current_stats = await fetcher.fetch_current_month_stats(story['medium_url'])
                
                if current_stats:
                    totals = current_stats.get('totals', {})
                    
                    await StoryService.update_story(story['key'], StoryUpdate(
                        # Current month stats only
                        reads=totals.get('total_reads', 0),
                        claps=totals.get('claps', 0),
                        responses=totals.get('replies', 0),
                        view_count=totals.get('total_views', 0),
                        medium_member_reads=totals.get('member_reads', 0),
                        medium_member_views=totals.get('member_views', 0),
                        medium_nonmember_reads=totals.get('nonmember_reads', 0),
                        medium_nonmember_views=totals.get('nonmember_views', 0),
                        medium_read_ratio=totals.get('read_ratio', 0),
                        medium_member_read_percentage=totals.get('member_read_percentage', 0),
                        medium_new_followers=totals.get('new_followers', 0),
                        medium_highlights=totals.get('highlights', 0),
                        
                        # Post metadata
                        medium_first_published=current_stats.get('first_published'),
                        medium_last_updated=current_stats.get('last_updated'),
                        medium_title=current_stats.get('title'),
                        medium_reading_time=current_stats.get('reading_time', 0),
                        word_count=current_stats.get('word_count', 0),
                        
                        # Update timestamp
                        last_stats_update=datetime.now().isoformat(),
                        medium_stats_updated=datetime.now().isoformat(),
                        medium_stats_data=current_stats
                    ))
                    
                    results['updated'] += 1
                    results['details'].append({
                        'key': story['key'],
                        'name': story['name'],
                        'success': True,
                        'reads': totals.get('total_reads', 0)
                    })
                    logger.info(f"   ✅ Updated: {totals.get('total_reads', 0)} reads this month")
                else:
                    results['failed'] += 1
                    results['details'].append({
                        'key': story['key'],
                        'name': story['name'],
                        'success': False
                    })
                    logger.warning(f"   ❌ Failed to fetch details")
                    
            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'key': story['key'],
                    'name': story['name'],
                    'success': False,
                    'error': str(e)
                })
                logger.error(f"   ❌ Error: {e}")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"COMPLETE: {results['updated']}/{results['total']} stories updated")
        logger.info(f"{'='*60}")
        
        return {
            "message": f"Updated {results['updated']} of {results['total']} stories",
            "results": results
        }

    except Exception as e:
        logger.error(f"Fetch stats error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fetch-lifetime-stats/{story_key:path}")
async def fetch_lifetime_stats_for_story(story_key: str = Path(...)):
    """Fetch ONLY lifetime stats for a single story (called from Stats Dashboard button)"""
    try:
        decoded_key = unquote(story_key)
        if decoded_key.lower().endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        logger.info(f"=" * 60)
        logger.info(f"FETCHING LIFETIME STATS FOR: {decoded_key}")
        logger.info(f"=" * 60)
        
        story = await StoryService.get_story(decoded_key)
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found: {decoded_key}")
        
        if not story.medium_url:
            raise HTTPException(status_code=400, detail="Story has no Medium URL")
        
        logger.info(f"📝 Medium URL: {story.medium_url}")
        
        fetcher = MediumStatsFetcher()
        
        if not fetcher.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Fetch ONLY lifetime stats
        lifetime_stats = await fetcher.fetch_lifetime_stats(story.medium_url)
        
        if lifetime_stats:
            await StoryService.update_story(decoded_key, StoryUpdate(
                # Lifetime stats only
                lifetime_reads=lifetime_stats.get('lifetime_reads', 0),
                lifetime_views=lifetime_stats.get('lifetime_views', 0),
                presentation_count=lifetime_stats.get('presentation_count', 0),
                lifetime_stats_data=lifetime_stats,
                lifetime_stats_updated=datetime.now().isoformat()
            ))
            
            return {
                "message": "Lifetime stats fetched successfully",
                "stats": {
                    "story_key": decoded_key,
                    "story_name": story.name,
                    "medium_url": story.medium_url,
                    "lifetime": {
                        "reads": lifetime_stats.get('lifetime_reads', 0),
                        "views": lifetime_stats.get('lifetime_views', 0),
                        "presentation_count": lifetime_stats.get('presentation_count', 0)
                    }
                }
            }
        else:
            return {"message": "Could not fetch lifetime stats", "error": "No data returned"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fetch lifetime stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# CORE CRUD ENDPOINTS
# ============================================

@router.post("/sync")
async def sync_stories():
    """Sync with filesystem"""
    try:
        result = await StoryService.sync_with_filesystem()
        return {
            "message": "Sync completed",
            "added": result.get("added", 0),
            "updated": result.get("updated", 0),
            "total_stories": result.get("total", 0)
        }
    except Exception as e:
        logger.error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[StoryResponse])
async def list_stories(
    status: Optional[str] = Query(None),
    series: Optional[str] = Query(None),
    folder: Optional[str] = Query(None)
):
    """List all stories with optional filters"""
    stories = await StoryService.get_all_stories()
    if status:
        stories = [s for s in stories if s.status == status]
    if series:
        stories = [s for s in stories if s.series == series]
    if folder:
        stories = [s for s in stories if s.folder == folder]
    return stories


@router.post("/", response_model=StoryResponse, status_code=201)
async def create_story(story_data: StoryCreate):
    """Create a new story"""
    try:
        return await StoryService.create_story(story_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{story_key:path}", response_model=StoryResponse)
async def update_story(
    story_key: str = Path(...),
    update_data: StoryUpdate = None
):
    """Update a story"""
    decoded_key = unquote(story_key)
    if decoded_key.lower().endswith('.md'):
        decoded_key = decoded_key[:-3]
    if update_data is None:
        update_data = StoryUpdate()
    story = await StoryService.update_story(decoded_key, update_data)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.post("/{story_key:path}/publish", response_model=StoryResponse)
async def publish_story(
    story_key: str = Path(...),
    medium_url: Optional[str] = None
):
    """Mark a story as published"""
    decoded_key = unquote(story_key)
    if decoded_key.lower().endswith('.md'):
        decoded_key = decoded_key[:-3]
    story = await StoryService.publish_story(decoded_key, medium_url)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.delete("/{story_key:path}")
async def delete_story(story_key: str = Path(...)):
    """Delete a story"""
    decoded_key = unquote(story_key)
    if decoded_key.lower().endswith('.md'):
        decoded_key = decoded_key[:-3]
    deleted = await StoryService.delete_story(decoded_key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Story not found")
    return {"message": "Story deleted"}


@router.get("/{story_key:path}", response_model=StoryResponse)
async def get_story(story_key: str = Path(...)):
    """Get a single story"""
    decoded_key = unquote(story_key)
    if decoded_key.lower().endswith('.md'):
        decoded_key = decoded_key[:-3]
    
    story = await StoryService.get_story(decoded_key)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story