from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.services.file_service import load_stories_data, save_stories_data
from app.models import CalendarSettingsUpdate
from config import settings

router = APIRouter()

@router.get("/", response_model=Dict[str, Any])
async def get_settings():
    """Get all settings"""
    data = await load_stories_data()
    return data.get("calendar_settings", {})

@router.put("/calendar", response_model=Dict[str, Any])
async def update_calendar_settings(update: CalendarSettingsUpdate):
    """Update calendar settings"""
    data = await load_stories_data()
    
    if "calendar_settings" not in data:
        data["calendar_settings"] = {}
    
    for field, value in update.model_dump(exclude_unset=True).items():
        if value is not None:
            data["calendar_settings"][field] = value
    
    await save_stories_data(data)
    
    return data["calendar_settings"]

@router.get("/stories-root")
async def get_stories_root():
    """Get configured stories root folder"""
    return {"stories_root": settings.stories_root, "data_dir": settings.data_dir}