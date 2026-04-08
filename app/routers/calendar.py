"""
Calendar Router - Endpoints for publishing calendar management
All endpoints include curl examples for documentation
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import json
import logging
from datetime import datetime

from app.services.calendar_service import CalendarService
from app.models import CalendarResponse
from app.services.file_service import load_stories_data

logger = logging.getLogger(__name__)

# Create the router instance
router = APIRouter()


"""
GET /api/calendar/
Description: Get the publishing calendar

curl -X GET "http://localhost:8000/api/calendar/" | jq '.'
"""
@router.get("/", response_model=CalendarResponse)
async def get_calendar():
    """Get the publishing calendar"""
    try:
        return await CalendarService.save_calendar_files()
    except Exception as e:
        print(f"Calendar error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/calendar/generate
Description: Generate and save calendar files

curl -X POST "http://localhost:8000/api/calendar/generate" | jq '.'
"""
@router.post("/generate")
async def generate_calendar():
    """Generate and save calendar files"""
    try:
        response = await CalendarService.save_calendar_files()
        return {"message": "Calendar generated", "scheduled": response.summary.get("total_scheduled", 0)}
    except Exception as e:
        print(f"Generate calendar error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/calendar/debug
Description: Debug endpoint to check calendar data

curl -X GET "http://localhost:8000/api/calendar/debug" | jq '.'
"""
@router.get("/debug")
async def debug_calendar():
    """Debug endpoint to check calendar data"""
    try:
        from app.services.file_service import load_stories_data
        
        data = await load_stories_data()
        stories = data.get("stories", {})
        
        # Get unpublished stories count
        unpublished = []
        for story_key, story in stories.items():
            if story.get("published_date") is None and story.get("status") != "Archived":
                unpublished.append({
                    "key": story_key,
                    "name": story.get("name", story.get("title", story_key)),
                    "series": story.get("series"),
                    "status": story.get("status"),
                    "published_date": story.get("published_date")
                })
        
        # Get series data
        series_data = data.get("series", {})
        
        # Get calendar settings
        settings = data.get("calendar_settings", {})
        
        return {
            "total_stories": len(stories),
            "unpublished_stories": len(unpublished),
            "unpublished_sample": unpublished[:10],
            "total_series": len(series_data),
            "series_list": list(series_data.keys())[:20],
            "calendar_settings": settings
        }
    except Exception as e:
        print(f"Debug calendar error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


"""
GET /api/calendar/schedule
Description: Get calendar schedule

curl -X GET "http://localhost:8000/api/calendar/schedule" | jq '.'
"""
@router.get("/schedule")
async def get_calendar_schedule():
    """Get calendar schedule"""
    try:
        response = await CalendarService.save_calendar_files()
        return {
            "schedule": [
                {
                    "date": c.date,
                    "weekday": c.weekday,
                    "name": c.name,
                    "series": c.series,
                    "part": c.part,
                    "read_time": c.read_time,
                    "story_key": c.story_key
                }
                for c in response.schedule
            ],
            "summary": response.summary
        }
    except Exception as e:
        logger.error(f"Error getting calendar schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/calendar/upcoming
Description: Get upcoming schedule (next N entries)

curl -X GET "http://localhost:8000/api/calendar/upcoming?limit=10" | jq '.'
"""
@router.get("/upcoming")
async def get_upcoming_schedule(limit: int = 10):
    """Get upcoming schedule entries"""
    try:
        upcoming = await CalendarService.get_upcoming_schedule(limit)
        return {
            "schedule": upcoming,
            "total": len(upcoming),
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error getting upcoming schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/calendar/stats
Description: Get calendar statistics

curl -X GET "http://localhost:8000/api/calendar/stats" | jq '.'
"""
@router.get("/stats")
async def get_calendar_stats():
    """Get calendar statistics without generating full calendar"""
    try:
        stats = await CalendarService.get_calendar_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting calendar stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/calendar/reset
Description: Reset calendar settings to defaults

curl -X POST "http://localhost:8000/api/calendar/reset" | jq '.'
"""
@router.post("/reset")
async def reset_calendar_settings():
    """Reset calendar settings to defaults"""
    try:
        from app.services.file_service import save_stories_data, load_stories_data
        from config import settings as config_settings
        
        data = await load_stories_data()
        
        default_settings = {
            "series_spacing_days": config_settings.default_series_spacing_days,
            "stories_per_week": config_settings.default_stories_per_week,
            "preferred_publish_days": config_settings.preferred_publish_days,
            "start_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        data["calendar_settings"] = default_settings
        await save_stories_data(data)
        
        return {"message": "Calendar settings reset to defaults", "settings": default_settings}
    except Exception as e:
        logger.error(f"Error resetting calendar settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/calendar/preview
Description: Preview calendar without saving

curl -X POST "http://localhost:8000/api/calendar/preview" \
  -H "Content-Type: application/json" \
  -d '{
    "stories_per_week": 4,
    "series_spacing_days": 5,
    "preferred_publish_days": ["Monday", "Wednesday", "Friday"],
    "start_date": "2026-04-15"
  }' | jq '.'
"""
@router.post("/preview")
async def preview_calendar(settings_preview: Dict[str, Any]):
    """Preview calendar with temporary settings without saving"""
    try:
        from app.services.calendar_service import CalendarService
        from app.services.file_service import load_stories_data
        
        # Load current data
        data = await load_stories_data()
        original_settings = data.get("calendar_settings", {})
        
        # Apply preview settings temporarily
        data["calendar_settings"] = {
            **original_settings,
            **settings_preview
        }
        
        # Generate calendar with temporary settings
        calendar, summary = await CalendarService.generate_calendar()
        
        # Restore original settings (don't save)
        
        return {
            "schedule": calendar[:20],  # Limit to 20 for preview
            "summary": summary,
            "preview_settings": settings_preview
        }
    except Exception as e:
        logger.error(f"Error previewing calendar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/calendar/export/markdown
Description: Export calendar as markdown

curl -X GET "http://localhost:8000/api/calendar/export/markdown" | jq '.'
"""
@router.get("/export/markdown")
async def export_calendar_markdown():
    """Export calendar as markdown"""
    try:
        from app.services.calendar_service import CalendarService
        from app.services.file_service import get_calendar_md_path
        
        # Generate calendar files
        await CalendarService.save_calendar_files()
        
        # Read the markdown file
        md_path = get_calendar_md_path()
        if md_path.exists():
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "success": True,
                "content": content,
                "file_path": str(md_path)
            }
        else:
            return {
                "success": False,
                "message": "Calendar markdown file not found"
            }
    except Exception as e:
        logger.error(f"Error exporting calendar markdown: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/calendar/export/json
Description: Export calendar as JSON

curl -X GET "http://localhost:8000/api/calendar/export/json" | jq '.'
"""
@router.get("/export/json")
async def export_calendar_json():
    """Export calendar as JSON"""
    try:
        from app.services.calendar_service import CalendarService
        from app.services.file_service import get_calendar_json_path
        
        # Generate calendar files
        response = await CalendarService.save_calendar_files()
        
        # Read the JSON file
        json_path = get_calendar_json_path()
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            return {
                "success": True,
                "content": content,
                "file_path": str(json_path)
            }
        else:
            return {
                "success": False,
                "message": "Calendar JSON file not found"
            }
    except Exception as e:
        logger.error(f"Error exporting calendar JSON: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/calendar/regenerate-series
Description: Regenerate calendar for a specific series

curl -X POST "http://localhost:8000/api/calendar/regenerate-series?series_name=Python%20Tutorials" | jq '.'
"""
@router.post("/regenerate-series")
async def regenerate_series_calendar(series_name: str):
    """Regenerate calendar for a specific series only"""
    try:
        from urllib.parse import unquote
        decoded_name = unquote(series_name)
        
        data = await load_stories_data()
        series_data = data.get("series", {})
        
        if decoded_name not in series_data:
            raise HTTPException(status_code=404, detail="Series not found")
        
        # Get unpublished stories for this series
        stories = data.get("stories", {})
        unpublished = []
        
        for story_key in series_data[decoded_name].get("stories", []):
            if story_key in stories:
                story = stories[story_key]
                if story.get("published_date") is None and story.get("status") != "Archived":
                    unpublished.append({
                        "key": story_key,
                        "name": story.get("name", story.get("title", story_key)),
                        "series": decoded_name
                    })
        
        return {
            "series_name": decoded_name,
            "unpublished_stories": len(unpublished),
            "stories": unpublished
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating series calendar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/calendar/available-dates
Description: Get available publish dates based on settings

curl -X GET "http://localhost:8000/api/calendar/available-dates?limit=30" | jq '.'
"""
@router.get("/available-dates")
async def get_available_dates(limit: int = 30):
    """Get available publish dates based on current settings"""
    try:
        data = await load_stories_data()
        settings = data.get("calendar_settings", {})
        
        stories_per_week = settings.get("stories_per_week", 3)
        start_date = datetime.strptime(
            settings.get("start_date", datetime.now().strftime("%Y-%m-%d")),
            "%Y-%m-%d"
        )
        preferred_days = settings.get("preferred_publish_days", ["Monday", "Tuesday", "Wednesday", "Thursday"])
        
        day_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, 
                   "Friday": 4, "Saturday": 5, "Sunday": 6}
        preferred_weekdays = [day_map[d] for d in preferred_days if d in day_map]
        
        if not preferred_weekdays:
            preferred_weekdays = [0, 1, 2, 3]
        
        dates = []
        current_date = start_date
        published_this_week = 0
        
        while len(dates) < limit:
            if published_this_week >= stories_per_week:
                days_to_next_week = 7 - current_date.weekday()
                current_date += __import__('datetime').timedelta(days=days_to_next_week)
                published_this_week = 0
                continue
            
            while current_date.weekday() not in preferred_weekdays:
                current_date += __import__('datetime').timedelta(days=1)
            
            dates.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "weekday": current_date.strftime("%A")
            })
            
            published_this_week += 1
            current_date += __import__('datetime').timedelta(days=1)
        
        return {
            "available_dates": dates,
            "settings": {
                "stories_per_week": stories_per_week,
                "preferred_days": preferred_days,
                "start_date": start_date.strftime("%Y-%m-%d")
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting available dates: {e}")
        raise HTTPException(status_code=500, detail=str(e))