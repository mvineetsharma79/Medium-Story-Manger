"""
Settings Router - Endpoints for application settings
All endpoints include curl examples for documentation
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.services.file_service import load_stories_data, save_stories_data
from app.models import CalendarSettingsUpdate
from config import settings

router = APIRouter()


"""
GET /api/settings/
Description: Get all settings

curl -X GET "http://localhost:8000/api/settings/" | jq '.'
"""
@router.get("/", response_model=Dict[str, Any])
async def get_settings():
    """Get all settings"""
    data = await load_stories_data()
    return data.get("calendar_settings", {})


"""
PUT /api/settings/calendar
Description: Update calendar settings

curl -X PUT "http://localhost:8000/api/settings/calendar" \
  -H "Content-Type: application/json" \
  -d '{
    "series_spacing_days": 7,
    "stories_per_week": 3,
    "preferred_publish_days": ["Monday", "Tuesday", "Wednesday", "Thursday"],
    "start_date": "2026-04-07"
  }' | jq '.'
"""
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


"""
GET /api/settings/stories-root
Description: Get configured stories root folder

curl -X GET "http://localhost:8000/api/settings/stories-root" | jq '.'
"""
@router.get("/stories-root")
async def get_stories_root():
    """Get configured stories root folder"""
    return {"stories_root": settings.stories_root, "data_dir": settings.data_dir}