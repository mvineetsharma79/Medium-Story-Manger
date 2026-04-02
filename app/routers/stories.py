from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Optional
import logging
from urllib.parse import unquote
from datetime import datetime
import asyncio

from app.services.story_service import StoryService
from app.services.medium_stats_fetcher import MediumStatsFetcher
from app.models import StoryCreate, StoryUpdate, StoryResponse

logger = logging.getLogger(__name__)
router = APIRouter()


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
                    "status": s.status
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
                "medium_url": s.medium_url
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
# MEDIUM STATS ENDPOINTS (Scraping based)
# ============================================

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
        
        # Build dashboard from stored stats
        reads = story.reads or 0
        claps = story.claps or 0
        responses = story.responses or 0
        bookmarks = story.bookmarks or 0
        view_count = story.medium_total_views or 0
        read_ratio = story.medium_read_ratio or 0
        fan_count = story.fan_count or 0
        
        return {
            "story_key": story.key,
            "story_name": story.name,
            "medium_url": story.medium_url,
            "last_stats_update": story.last_stats_update,
            "engagement": {
                "reads": reads,
                "claps": claps,
                "responses": responses,
                "bookmarks": bookmarks,
                "view_count": view_count,
                "read_ratio": read_ratio,
                "fan_count": fan_count
            },
            "content": {
                "word_count": story.word_count or 0,
                "reading_time_minutes": story.medium_reading_time or story.read_time or 0,
                "tags": story.medium_tags or story.tags or [],
                "topics": story.medium_topics or []
            },
            "metadata": {
                "title": story.medium_title or story.name,
                "subtitle": story.medium_subtitle or "",
                "author": story.medium_author or "",
                "publication": story.medium_publication or "",
                "first_published": story.medium_first_published or story.created_date,
                "last_updated": story.medium_last_updated or story.last_updated
            },
            "performance": {
                "claps_per_read": safe_divide(claps, reads),
                "responses_per_read": safe_divide(responses, reads),
                "bookmarks_per_read": safe_divide(bookmarks, reads),
                "views_to_reads": safe_divide(reads * 100, view_count) if view_count else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Get stats dashboard error: {e}")
        return {"error": str(e)}


# ============================================
# MEDIUM STATS FETCHER ENDPOINTS (Working)
# ============================================

@router.post("/fetch-stats")
async def fetch_all_medium_stats():
    """Fetch detailed stats from Medium for all stories with URLs using working fetcher"""
    try:
        logger.info("=" * 60)
        logger.info("FETCH STATS - Starting...")
        
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
        
        logger.info(f"Cookies found: {list(fetcher.cookies.keys())}")
        
        results = await fetcher.fetch_all_stories_stats(stories_with_urls)
        
        logger.info(f"Fetch completed: {results['updated']} updated, {results['failed']} failed")
        
        for detail in results['details']:
            if detail['success'] and 'stats' in detail:
                stats = detail['stats']
                totals = stats.get('totals', {})
                
                await StoryService.update_story(detail['key'], StoryUpdate(
                    reads=totals.get('total_reads', 0),
                    claps=totals.get('claps', 0),
                    responses=totals.get('replies', 0),
                    medium_member_reads=totals.get('member_reads', 0),
                    medium_member_views=totals.get('member_views', 0),
                    medium_nonmember_reads=totals.get('nonmember_reads', 0),
                    medium_nonmember_views=totals.get('nonmember_views', 0),
                    medium_total_views=totals.get('total_views', 0),
                    medium_replies=totals.get('replies', 0),
                    medium_highlights=totals.get('highlights', 0),
                    medium_new_followers=totals.get('new_followers', 0),
                    medium_read_ratio=totals.get('read_ratio', 0),
                    medium_member_read_percentage=totals.get('member_read_percentage', 0),
                    medium_stats_data=stats,
                    medium_stats_updated=datetime.now().isoformat()
                ))
                logger.info(f"✅ Updated {detail['name']}: {totals.get('total_reads', 0)} reads, {totals.get('total_views', 0)} views")
        
        return {
            "message": f"Updated {results['updated']} of {results['total']} stories",
            "results": results
        }

    except Exception as e:
        logger.error(f"Fetch stats error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-stats")
async def sync_all_medium_stats():
    """Fetch and update ALL story statistics from Medium using working fetcher"""
    try:
        logger.info("=" * 60)
        logger.info("SYNC STATS - Starting...")
        
        stories = await StoryService.get_all_stories()
        stories_with_urls = [s for s in stories if s.medium_url]

        if not stories_with_urls:
            return {"message": "No stories with Medium URLs", "updated": 0, "total": 0}

        logger.info(f"Found {len(stories_with_urls)} stories with Medium URLs")

        fetcher = MediumStatsFetcher()
        
        if not fetcher.is_authenticated():
            logger.error("Not authenticated - no valid cookies found")
            return {"error": "Not authenticated. Please log into Medium in your browser, then close browser and try again."}
        
        logger.info(f"Cookies loaded: {list(fetcher.cookies.keys())}")
        
        results = {
            "total": len(stories_with_urls),
            "updated": 0,
            "failed": 0,
            "details": []
        }

        for story in stories_with_urls:
            try:
                logger.info(f"Fetching stats for: {story.name}")
                
                stats = await fetcher.fetch_post_stats(story.medium_url)
                
                if stats:
                    totals = stats.get('totals', {})
                    await StoryService.update_story(story.key, StoryUpdate(
                        reads=totals.get('total_reads', story.reads),
                        claps=totals.get('claps', 0),
                        responses=totals.get('replies', 0),
                        medium_member_reads=totals.get('member_reads', 0),
                        medium_member_views=totals.get('member_views', 0),
                        medium_nonmember_reads=totals.get('nonmember_reads', 0),
                        medium_nonmember_views=totals.get('nonmember_views', 0),
                        medium_total_views=totals.get('total_views', 0),
                        medium_replies=totals.get('replies', 0),
                        medium_highlights=totals.get('highlights', 0),
                        medium_new_followers=totals.get('new_followers', 0),
                        medium_read_ratio=totals.get('read_ratio', 0),
                        medium_member_read_percentage=totals.get('member_read_percentage', 0),
                        medium_stats_data=stats,
                        last_stats_update=datetime.now().isoformat()
                    ))
                    results['updated'] += 1
                    results['details'].append({
                        'key': story.key, 
                        'success': True, 
                        'reads': totals.get('total_reads', 0)
                    })
                    logger.info(f"✅ Updated {story.name}: {totals.get('total_reads', 0)} reads")
                else:
                    results['failed'] += 1
                    results['details'].append({'key': story.key, 'success': False})
                    logger.warning(f"❌ Failed to fetch stats for {story.name}")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                results['failed'] += 1
                results['details'].append({'key': story.key, 'success': False, 'error': str(e)})
                logger.error(f"Error fetching stats for {story.name}: {e}")

        return {
            "message": f"Updated {results['updated']} of {results['total']} stories",
            "results": results
        }

    except Exception as e:
        logger.error(f"Sync stats error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-stats-by-url")
async def sync_stats_by_url(medium_url: str):
    """Fetch and update stats for a story using its Medium URL"""
    try:
        if not medium_url:
            return {"error": "Medium URL is required"}
        
        from urllib.parse import unquote
        decoded_url = unquote(medium_url)
        
        logger.info(f"Syncing stats for URL: {decoded_url}")
        
        all_stories = await StoryService.get_all_stories()
        
        story = None
        for s in all_stories:
            if s.medium_url:
                if s.medium_url.rstrip('/') == decoded_url.rstrip('/'):
                    story = s
                    break
        
        if not story:
            available = [s.medium_url for s in all_stories if s.medium_url]
            return {
                "error": "Story not found",
                "your_url": decoded_url,
                "available_urls": available[:5] if available else []
            }
        
        fetcher = MediumStatsFetcher()
        
        if not fetcher.is_authenticated():
            return {"error": "Not authenticated. Please log into Medium in your browser."}
        
        stats = await fetcher.fetch_post_stats(story.medium_url)
        
        if stats:
            totals = stats.get('totals', {})
            await StoryService.update_story(story.key, StoryUpdate(
                reads=totals.get('total_reads', story.reads),
                claps=totals.get('claps', 0),
                responses=totals.get('replies', 0),
                medium_member_reads=totals.get('member_reads', 0),
                medium_member_views=totals.get('member_views', 0),
                medium_nonmember_reads=totals.get('nonmember_reads', 0),
                medium_nonmember_views=totals.get('nonmember_views', 0),
                medium_total_views=totals.get('total_views', 0),
                medium_replies=totals.get('replies', 0),
                medium_highlights=totals.get('highlights', 0),
                medium_new_followers=totals.get('new_followers', 0),
                medium_read_ratio=totals.get('read_ratio', 0),
                medium_member_read_percentage=totals.get('member_read_percentage', 0),
                medium_stats_data=stats,
                last_stats_update=datetime.now().isoformat(),
                notes=f"{story.notes}\n[Stats: {datetime.now().strftime('%Y-%m-%d %H:%M')}]" if story.notes else f"Stats: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            ))
            return {"message": "Stats updated", "stats": stats, "story_key": story.key}
        return {"message": "Could not fetch stats"}

    except Exception as e:
        logger.error(f"Sync stats by URL error: {e}")
        return {"error": str(e)}


@router.post("/{story_key:path}/fetch-stats")
async def fetch_single_story_stats(story_key: str = Path(...)):
    """Fetch detailed stats for a single story"""
    try:
        decoded_key = unquote(story_key)
        if decoded_key.lower().endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        story = await StoryService.get_story(decoded_key)
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found: {decoded_key}")
        
        if not story.medium_url:
            raise HTTPException(status_code=400, detail="Story has no Medium URL")
        
        logger.info(f"Fetching stats for: {story.name}")
        
        fetcher = MediumStatsFetcher()
        
        if not fetcher.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated. Please log into Medium in your browser.")
        
        stats = await fetcher.fetch_post_stats(story.medium_url)
        
        if stats:
            totals = stats.get('totals', {})
            await StoryService.update_story(decoded_key, StoryUpdate(
                reads=totals.get('total_reads', 0),
                claps=totals.get('claps', 0),
                responses=totals.get('replies', 0),
                medium_member_reads=totals.get('member_reads', 0),
                medium_member_views=totals.get('member_views', 0),
                medium_nonmember_reads=totals.get('nonmember_reads', 0),
                medium_nonmember_views=totals.get('nonmember_views', 0),
                medium_total_views=totals.get('total_views', 0),
                medium_replies=totals.get('replies', 0),
                medium_highlights=totals.get('highlights', 0),
                medium_new_followers=totals.get('new_followers', 0),
                medium_read_ratio=totals.get('read_ratio', 0),
                medium_member_read_percentage=totals.get('member_read_percentage', 0),
                medium_stats_data=stats,
                medium_stats_updated=datetime.now().isoformat()
            ))
            return {"message": "Stats fetched successfully", "stats": stats}
        return {"message": "Could not fetch stats"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fetch story stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{story_key:path}/sync-stats")
async def sync_single_story_stats(story_key: str = Path(...)):
    """Fetch and update stats for a single story using story key"""
    try:
        decoded_key = unquote(story_key)
        if decoded_key.lower().endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        story = await StoryService.get_story(decoded_key)
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found: {decoded_key}")
        
        if not story.medium_url:
            raise HTTPException(status_code=400, detail="Story has no Medium URL")
        
        return await sync_stats_by_url(story.medium_url)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync story stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{story_key:path}/stats-dashboard")
async def get_story_stats_dashboard(story_key: str = Path(...)):
    """Get stats dashboard for a story using story key"""
    try:
        decoded_key = unquote(story_key)
        if decoded_key.lower().endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        story = await StoryService.get_story(decoded_key)
        if not story:
            return {"error": f"Story not found: {decoded_key}"}
        
        if not story.medium_url:
            return {"error": "No Medium URL found for this story", "story_key": story.key}
        
        reads = story.reads or 0
        claps = story.claps or 0
        responses = story.responses or 0
        bookmarks = story.bookmarks or 0
        view_count = story.medium_total_views or 0
        read_ratio = story.medium_read_ratio or 0
        fan_count = story.fan_count or 0
        
        return {
            "story_key": story.key,
            "story_name": story.name,
            "medium_url": story.medium_url,
            "last_stats_update": story.last_stats_update,
            "engagement": {
                "reads": reads,
                "claps": claps,
                "responses": responses,
                "bookmarks": bookmarks,
                "view_count": view_count,
                "read_ratio": read_ratio,
                "fan_count": fan_count
            },
            "content": {
                "word_count": story.word_count or 0,
                "reading_time_minutes": story.medium_reading_time or story.read_time or 0,
                "tags": story.medium_tags or story.tags or [],
                "topics": story.medium_topics or []
            },
            "metadata": {
                "title": story.medium_title or story.name,
                "subtitle": story.medium_subtitle or "",
                "author": story.medium_author or "",
                "publication": story.medium_publication or "",
                "first_published": story.medium_first_published or story.created_date,
                "last_updated": story.medium_last_updated or story.last_updated
            },
            "performance": {
                "claps_per_read": safe_divide(claps, reads),
                "responses_per_read": safe_divide(responses, reads),
                "bookmarks_per_read": safe_divide(bookmarks, reads),
                "views_to_reads": safe_divide(reads * 100, view_count) if view_count else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Get stats dashboard error: {e}")
        return {"error": str(e)}


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