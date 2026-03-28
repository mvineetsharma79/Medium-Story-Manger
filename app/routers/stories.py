from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from app.services.story_service import StoryService
from app.models import StoryCreate, StoryUpdate, StoryResponse

router = APIRouter()

@router.post("/sync", response_model=dict)
async def sync_stories():
    """Sync with filesystem"""
    data = await StoryService.sync_with_filesystem()
    return {"message": "Sync completed", "total_stories": len(data.get("stories", {}))}

@router.get("/", response_model=List[StoryResponse])
async def list_stories(
    status: Optional[str] = Query(None, description="Filter by status"),
    series: Optional[str] = Query(None, description="Filter by series"),
    folder: Optional[str] = Query(None, description="Filter by folder")
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

@router.get("/{story_key}", response_model=StoryResponse)
async def get_story(story_key: str):
    """Get a single story"""
    story = await StoryService.get_story(story_key)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story

@router.post("/", response_model=StoryResponse, status_code=201)
async def create_story(story_data: StoryCreate):
    """Create a new story"""
    try:
        return await StoryService.create_story(story_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{story_key}", response_model=StoryResponse)
async def update_story(story_key: str, update_data: StoryUpdate):
    """Update a story"""
    story = await StoryService.update_story(story_key, update_data)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story

@router.post("/{story_key}/publish", response_model=StoryResponse)
async def publish_story(story_key: str, medium_url: Optional[str] = None):
    """Mark a story as published"""
    story = await StoryService.publish_story(story_key, medium_url)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story

@router.delete("/{story_key}")
async def delete_story(story_key: str):
    """Delete a story (from JSON only)"""
    deleted = await StoryService.delete_story(story_key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Story not found")
    return {"message": "Story deleted"}