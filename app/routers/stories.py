from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Optional
import logging
from urllib.parse import unquote, quote

from app.services.story_service import StoryService
from app.models import StoryCreate, StoryUpdate, StoryResponse

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/sync", response_model=dict)
async def sync_stories():
    """Sync with filesystem"""
    try:
        data = await StoryService.sync_with_filesystem()
        return {"message": "Sync completed", "total_stories": len(data.get("stories", {}))}
    except Exception as e:
        logger.error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[StoryResponse])
async def list_stories(
    status: Optional[str] = Query(None, description="Filter by status"),
    series: Optional[str] = Query(None, description="Filter by series"),
    folder: Optional[str] = Query(None, description="Filter by folder")
):
    """List all stories with optional filters"""
    try:
        stories = await StoryService.get_all_stories()
        
        if status:
            stories = [s for s in stories if s.status == status]
        if series:
            stories = [s for s in stories if s.series == series]
        if folder:
            stories = [s for s in stories if s.folder == folder]
        
        return stories
    except Exception as e:
        logger.error(f"List stories error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{story_key:path}", response_model=StoryResponse)
async def get_story(story_key: str = Path(..., description="Story key (URL encoded)")):
    """Get a single story"""
    try:
        # Decode the URL-encoded key
        decoded_key = unquote(story_key)
        logger.info(f"Getting story: {decoded_key}")
        
        # Remove .md extension if present
        if decoded_key.lower().endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        story = await StoryService.get_story(decoded_key)
        
        if not story:
            # Try one more time with raw key
            story = await StoryService.get_story(story_key)
        
        if not story:
            logger.warning(f"Story not found: {decoded_key}")
            raise HTTPException(status_code=404, detail=f"Story not found: {decoded_key}")
        
        return story
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get story error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{story_key:path}", response_model=StoryResponse)
async def update_story(
    story_key: str = Path(..., description="Story key (URL encoded)"),
    update_data: StoryUpdate = None
):
    """Update a story"""
    try:
        # Decode the URL-encoded key
        decoded_key = unquote(story_key)
        logger.info(f"Updating story: {decoded_key}")
        
        # Remove .md extension if present
        if decoded_key.lower().endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        if update_data is None:
            update_data = StoryUpdate()
        
        logger.info(f"Update data: {update_data.model_dump() if update_data else 'None'}")
        
        story = await StoryService.update_story(decoded_key, update_data)
        if not story:
            # Try one more time with raw key
            story = await StoryService.update_story(story_key, update_data)
        
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found: {decoded_key}")
        
        return story
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update story error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{story_key:path}/publish", response_model=StoryResponse)
async def publish_story(
    story_key: str = Path(..., description="Story key (URL encoded)"),
    medium_url: Optional[str] = None
):
    """Mark a story as published"""
    try:
        decoded_key = unquote(story_key)
        if decoded_key.lower().endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        story = await StoryService.publish_story(decoded_key, medium_url)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        return story
    except Exception as e:
        logger.error(f"Publish story error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{story_key:path}")
async def delete_story(story_key: str = Path(..., description="Story key (URL encoded)")):
    """Delete a story (from JSON only)"""
    try:
        decoded_key = unquote(story_key)
        if decoded_key.lower().endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        deleted = await StoryService.delete_story(decoded_key)
        if not deleted:
            raise HTTPException(status_code=404, detail="Story not found")
        return {"message": "Story deleted"}
    except Exception as e:
        logger.error(f"Delete story error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/keys")
async def debug_keys():
    """Debug endpoint to list all story keys"""
    stories = await StoryService.get_all_stories()
    keys = [story.key for story in stories]
    return {"total": len(keys), "keys": keys}

@router.get("/debug/find/{search}")
async def find_story(search: str):
    """Find stories containing search term"""
    stories = await StoryService.get_all_stories()
    matches = [{"key": s.key, "name": s.name} for s in stories if search.lower() in s.key.lower() or search.lower() in s.name.lower()]
    return {"search": search, "matches": matches}