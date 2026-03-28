from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Optional
import logging
from urllib.parse import unquote
from datetime import datetime
import asyncio

from app.services.story_service import StoryService
from app.services.medium_service import MediumService
from app.models import StoryCreate, StoryUpdate, StoryResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# DEBUG ENDPOINTS - MUST COME BEFORE CATCH-ALL ROUTES
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


@router.get("/stats-by-url")
async def get_stats_dashboard_by_url(medium_url: str):
    """Get stats dashboard for a story using its Medium URL"""
    try:
        if not medium_url:
            return {"error": "Medium URL is required"}
        
        from urllib.parse import unquote
        decoded_url = unquote(medium_url)
        
        logger.info(f"Looking for story with URL: {decoded_url}")
        
        all_stories = await StoryService.get_all_stories()
        
        def normalize_url(url: str) -> str:
            if not url:
                return url
            url = url.replace('https://', '').replace('http://', '')
            url = url.rstrip('/')
            return url.lower()
        
        normalized_query = normalize_url(decoded_url)
        
        story = None
        for s in all_stories:
            if s.medium_url:
                normalized_stored = normalize_url(s.medium_url)
                if normalized_stored == normalized_query:
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
            "engagement": {
                "reads": story.reads or 0,
                "claps": story.claps or 0,
                "responses": story.responses or 0,
                "bookmarks": story.bookmarks or 0,
                "view_count": story.view_count or 0,
                "read_ratio": story.read_ratio or 0,
                "fan_count": story.fan_count or 0
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
                "claps_per_read": round((story.claps or 0) / (story.reads or 1), 2),
                "responses_per_read": round((story.responses or 0) / (story.reads or 1), 2),
                "bookmarks_per_read": round((story.bookmarks or 0) / (story.reads or 1), 2),
                "views_to_reads": round((story.reads or 0) / (story.view_count or 1) * 100, 1) if story.view_count else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Get stats dashboard error: {e}")
        return {"error": str(e)}


@router.post("/sync-stats-by-url")
async def sync_stats_by_url(medium_url: str):
    """Fetch and update stats for a story using its Medium URL"""
    try:
        if not medium_url:
            return {"error": "Medium URL is required"}
        
        from urllib.parse import unquote
        decoded_url = unquote(medium_url)
        
        all_stories = await StoryService.get_all_stories()
        
        def normalize_url(url: str) -> str:
            if not url:
                return url
            url = url.replace('https://', '').replace('http://', '')
            url = url.rstrip('/')
            return url.lower()
        
        normalized_query = normalize_url(decoded_url)
        
        story = None
        for s in all_stories:
            if s.medium_url:
                normalized_stored = normalize_url(s.medium_url)
                if normalized_stored == normalized_query:
                    story = s
                    break
        
        if not story:
            available = [s.medium_url for s in all_stories if s.medium_url]
            return {
                "error": "Story not found",
                "your_url": decoded_url,
                "available_urls": available[:5] if available else []
            }
        
        medium = MediumService()
        stats = await medium.update_story_stats(story.key, story.medium_url)
        await medium.close()
        
        if stats:
            await StoryService.update_story(story.key, StoryUpdate(
                reads=stats.get('reads', story.reads),
                claps=stats.get('claps', 0),
                responses=stats.get('responses', 0),
                bookmarks=stats.get('bookmarks', 0),
                view_count=stats.get('view_count', 0),
                read_ratio=stats.get('read_ratio', 0),
                medium_reading_time=stats.get('reading_time', 0),
                fan_count=stats.get('fan_count', 0),
                medium_first_published=stats.get('first_published'),
                medium_last_updated=stats.get('last_updated'),
                medium_tags=stats.get('tags', []),
                medium_topics=stats.get('topics', []),
                word_count=stats.get('word_count', 0),
                medium_title=stats.get('title'),
                medium_subtitle=stats.get('subtitle'),
                medium_author=stats.get('author'),
                medium_publication=stats.get('publication'),
                last_stats_update=datetime.now().isoformat()
            ))
            return {"message": "Stats updated", "stats": stats, "story_key": story.key}
        return {"message": "Could not fetch stats"}

    except Exception as e:
        logger.error(f"Sync stats by URL error: {e}")
        return {"error": str(e)}


@router.post("/sync-stats")
async def sync_all_medium_stats():
    """Fetch and update ALL story statistics from Medium"""
    try:
        stories = await StoryService.get_all_stories()
        stories_with_urls = [s for s in stories if s.medium_url]

        if not stories_with_urls:
            return {"message": "No stories with Medium URLs", "updated": 0, "total": 0}

        medium = MediumService()
        results = {
            "total": len(stories_with_urls),
            "updated": 0,
            "failed": 0,
            "details": []
        }

        for story in stories_with_urls:
            try:
                logger.info(f"Fetching stats for: {story.name}")
                stats = await medium.update_story_stats(story.key, story.medium_url)
                
                if stats:
                    await StoryService.update_story(story.key, StoryUpdate(
                        reads=stats.get('reads', story.reads),
                        claps=stats.get('claps', 0),
                        responses=stats.get('responses', 0),
                        bookmarks=stats.get('bookmarks', 0),
                        view_count=stats.get('view_count', 0),
                        read_ratio=stats.get('read_ratio', 0),
                        medium_reading_time=stats.get('reading_time', 0),
                        fan_count=stats.get('fan_count', 0),
                        medium_first_published=stats.get('first_published'),
                        medium_last_updated=stats.get('last_updated'),
                        medium_tags=stats.get('tags', []),
                        medium_topics=stats.get('topics', []),
                        word_count=stats.get('word_count', 0),
                        medium_title=stats.get('title'),
                        medium_subtitle=stats.get('subtitle'),
                        medium_author=stats.get('author'),
                        medium_publication=stats.get('publication'),
                        last_stats_update=datetime.now().isoformat()
                    ))
                    results['updated'] += 1
                    results['details'].append({'key': story.key, 'success': True})
                else:
                    results['failed'] += 1
                    results['details'].append({'key': story.key, 'success': False})
                
                await asyncio.sleep(2)
                
            except Exception as e:
                results['failed'] += 1
                results['details'].append({'key': story.key, 'success': False, 'error': str(e)})

        await medium.close()
        
        return {
            "message": f"Updated {results['updated']} of {results['total']} stories",
            "results": results
        }

    except Exception as e:
        return {"error": str(e)}


# ============================================
# CORE CRUD ENDPOINTS
# ============================================

@router.post("/sync")
async def sync_stories():
    try:
        data = await StoryService.sync_with_filesystem()
        return {"message": "Sync completed", "total_stories": len(data.get("stories", {}))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[StoryResponse])
async def list_stories(
    status: Optional[str] = Query(None),
    series: Optional[str] = Query(None),
    folder: Optional[str] = Query(None)
):
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
    try:
        return await StoryService.create_story(story_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{story_key:path}", response_model=StoryResponse)
async def update_story(
    story_key: str = Path(...),
    update_data: StoryUpdate = None
):
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
    decoded_key = unquote(story_key)
    if decoded_key.lower().endswith('.md'):
        decoded_key = decoded_key[:-3]
    story = await StoryService.publish_story(decoded_key, medium_url)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.delete("/{story_key:path}")
async def delete_story(story_key: str = Path(...)):
    decoded_key = unquote(story_key)
    if decoded_key.lower().endswith('.md'):
        decoded_key = decoded_key[:-3]
    deleted = await StoryService.delete_story(decoded_key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Story not found")
    return {"message": "Story deleted"}


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
        
        return await get_stats_dashboard_by_url(story.medium_url)

    except Exception as e:
        logger.error(f"Get stats dashboard error: {e}")
        return {"error": str(e)}


@router.post("/{story_key:path}/sync-stats")
async def sync_single_story_stats(story_key: str = Path(...)):
    """Fetch and update stats for a single story using story key"""
    try:
        decoded_key = unquote(story_key)
        if decoded_key.lower().endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        story = await StoryService.get_story(decoded_key)
        if not story:
            return {"error": f"Story not found: {decoded_key}"}
        
        if not story.medium_url:
            return {"error": "Story has no Medium URL"}
        
        return await sync_stats_by_url(story.medium_url)

    except Exception as e:
        logger.error(f"Sync story stats error: {e}")
        return {"error": str(e)}


@router.get("/{story_key:path}", response_model=StoryResponse)
async def get_story(story_key: str = Path(...)):
    decoded_key = unquote(story_key)
    if decoded_key.lower().endswith('.md'):
        decoded_key = decoded_key[:-3]
    
    story = await StoryService.get_story(decoded_key)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story