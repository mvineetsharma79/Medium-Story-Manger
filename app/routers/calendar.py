from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import json
import logging
from app.services.calendar_service import CalendarService
from app.models import CalendarResponse

logger = logging.getLogger(__name__)

# Create the router instance - THIS IS CRITICAL
router = APIRouter()

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
                    "name": story.get("name", story_key),
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