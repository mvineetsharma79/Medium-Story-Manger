from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from app.services.story_service import StoryService
from app.models import SeriesResponse, SeriesCreate, SeriesUpdate

router = APIRouter()


@router.get("/", response_model=List[SeriesResponse])
async def list_series():
    """List all series"""
    data = await StoryService.sync_with_filesystem()
    series_data = data.get("series", {})
    settings = data.get("calendar_settings", {})
    default_spacing = settings.get("series_spacing_days", 7)
    
    result = []
    for name, info in series_data.items():
        result.append(SeriesResponse(
            name=name,
            total_stories=info.get("total_stories", 0),
            published=info.get("published", 0),
            spacing_days=info.get("spacing_days", default_spacing),
            stories=info.get("stories", [])
        ))
    
    return result


@router.get("/{series_name}", response_model=SeriesResponse)
async def get_series(series_name: str):
    """Get a single series"""
    data = await StoryService.sync_with_filesystem()
    series_data = data.get("series", {})
    
    if series_name not in series_data:
        raise HTTPException(status_code=404, detail="Series not found")
    
    settings = data.get("calendar_settings", {})
    default_spacing = settings.get("series_spacing_days", 7)
    info = series_data[series_name]
    
    return SeriesResponse(
        name=series_name,
        total_stories=info.get("total_stories", 0),
        published=info.get("published", 0),
        spacing_days=info.get("spacing_days", default_spacing),
        stories=info.get("stories", [])
    )


@router.post("/", response_model=SeriesResponse, status_code=201)
async def create_series(series_data: SeriesCreate):
    """Create a new series"""
    data = await StoryService.sync_with_filesystem()
    series = data.get("series", {})
    
    if series_data.name in series:
        raise HTTPException(status_code=400, detail="Series already exists")
    
    series[series_data.name] = {
        "name": series_data.name,
        "total_stories": 0,
        "published": 0,
        "spacing_days": series_data.spacing_days,
        "stories": []
    }
    
    await StoryService._save_stories_data(data)
    
    return SeriesResponse(
        name=series_data.name,
        total_stories=0,
        published=0,
        spacing_days=series_data.spacing_days or 7,
        stories=[]
    )


@router.put("/{series_name}", response_model=SeriesResponse)
async def update_series(series_name: str, update_data: SeriesUpdate):
    """Update a series"""
    data = await StoryService.sync_with_filesystem()
    series = data.get("series", {})
    
    if series_name not in series:
        raise HTTPException(status_code=404, detail="Series not found")
    
    if update_data.name:
        # Rename series
        series[update_data.name] = series.pop(series_name)
        series_name = update_data.name
    
    if update_data.spacing_days:
        series[series_name]["spacing_days"] = update_data.spacing_days
    
    await StoryService._save_stories_data(data)
    
    settings = data.get("calendar_settings", {})
    default_spacing = settings.get("series_spacing_days", 7)
    info = series[series_name]
    
    return SeriesResponse(
        name=series_name,
        total_stories=info.get("total_stories", 0),
        published=info.get("published", 0),
        spacing_days=info.get("spacing_days", default_spacing),
        stories=info.get("stories", [])
    )


@router.delete("/{series_name}")
async def delete_series(series_name: str):
    """Delete a series"""
    data = await StoryService.sync_with_filesystem()
    series = data.get("series", {})
    
    if series_name not in series:
        raise HTTPException(status_code=404, detail="Series not found")
    
    del series[series_name]
    await StoryService._save_stories_data(data)
    
    return {"message": "Series deleted"}