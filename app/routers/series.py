"""
Series Router - Endpoints for series management
All endpoints include curl examples for documentation
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import logging

from app.services.story_service import StoryService
from app.models import SeriesResponse, SeriesCreate, SeriesUpdate
from app.services.file_service import save_stories_data, load_stories_data
from app.utils import parse_series_number

logger = logging.getLogger(__name__)
router = APIRouter()


"""
GET /api/series/
Description: List all series

curl -X GET "http://localhost:8000/api/series/" | jq '.'
"""
@router.get("/", response_model=List[SeriesResponse])
async def list_series():
    """List all series"""
    try:
        data = await load_stories_data()
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
    except Exception as e:
        logger.error(f"List series error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/series/list
Description: Get all series with computed stats - used by frontend

curl -X GET "http://localhost:8000/api/series/list" | jq '.'
"""
@router.get("/list")
async def get_series_list():
    """Get all series with computed stats - used by frontend series.js"""
    try:
        data = await load_stories_data()
        series_data = data.get("series", {})
        settings = data.get("calendar_settings", {})
        default_spacing = settings.get("series_spacing_days", 7)
        
        result = []
        for name, info in series_data.items():
            total_stories = info.get("total_stories", 0)
            published = info.get("published", 0)
            progress_percent = round((published / max(total_stories, 1)) * 100, 1)
            
            result.append({
                "name": name,
                "total_stories": total_stories,
                "published": published,
                "spacing_days": info.get("spacing_days", default_spacing),
                "progress_percent": progress_percent
            })
        
        return {"series": result, "total": len(result)}
        
    except Exception as e:
        logger.error(f"Error getting series list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/series/{series_name}
Description: Get a single series

curl -X GET "http://localhost:8000/api/series/SOLID%20Principles" | jq '.'
"""
@router.get("/{series_name}", response_model=SeriesResponse)
async def get_series(series_name: str):
    """Get a single series"""
    try:
        data = await load_stories_data()
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get series error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/series/
Description: Create a new series

curl -X POST "http://localhost:8000/api/series/" \
  -H "Content-Type: application/json" \
  -d '{"name": "Python Tutorials", "spacing_days": 7}' | jq '.'
"""
@router.post("/", response_model=SeriesResponse, status_code=201)
async def create_series(series_data: SeriesCreate):
    """Create a new series"""
    try:
        data = await load_stories_data()
        series = data.get("series", {})
        
        clean_name = series_data.name.strip()
        
        if clean_name in series:
            raise HTTPException(status_code=400, detail="Series already exists")
        
        series[clean_name] = {
            "name": clean_name,
            "total_stories": 0,
            "published": 0,
            "spacing_days": series_data.spacing_days or 7,
            "stories": []
        }
        
        await save_stories_data(data)
        
        return SeriesResponse(
            name=clean_name,
            total_stories=0,
            published=0,
            spacing_days=series_data.spacing_days or 7,
            stories=[]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create series error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
PUT /api/series/{series_name}
Description: Update a series (rename or change spacing)

curl -X PUT "http://localhost:8000/api/series/Python%20Tutorials" \
  -H "Content-Type: application/json" \
  -d '{"name": "Python Advanced", "spacing_days": 10}' | jq '.'
"""
@router.put("/{series_name}", response_model=SeriesResponse)
async def update_series(series_name: str, update_data: SeriesUpdate):
    """Update a series (rename or change spacing)"""
    try:
        data = await load_stories_data()
        series = data.get("series", {})
        stories = data.get("stories", {})
        
        if series_name not in series:
            raise HTTPException(status_code=404, detail="Series not found")
        
        if update_data.name:
            new_name = update_data.name.strip()
            old_name = series_name
            
            if new_name == old_name:
                pass
            elif new_name in series:
                raise HTTPException(status_code=400, detail="Series with new name already exists")
            else:
                series[new_name] = series.pop(old_name)
                series[new_name]["name"] = new_name
                
                for story_key in series[new_name]["stories"]:
                    if story_key in stories:
                        stories[story_key]["series"] = new_name
                
                series_name = new_name
        
        if update_data.spacing_days:
            series[series_name]["spacing_days"] = update_data.spacing_days
        
        data["stories"] = stories
        data["series"] = series
        
        await save_stories_data(data)
        
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update series error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
DELETE /api/series/{series_name}
Description: Delete a series

curl -X DELETE "http://localhost:8000/api/series/Python%20Tutorials" | jq '.'
"""
@router.delete("/{series_name}")
async def delete_series(series_name: str):
    """Delete a series"""
    try:
        data = await load_stories_data()
        series = data.get("series", {})
        
        if series_name not in series:
            raise HTTPException(status_code=404, detail="Series not found")
        
        stories = data.get("stories", {})
        for story_key in series[series_name].get("stories", []):
            if story_key in stories:
                stories[story_key]["series"] = None
        
        del series[series_name]
        
        data["stories"] = stories
        data["series"] = series
        
        await save_stories_data(data)
        
        return {"message": f"Series '{series_name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete series error: {e}")
        raise HTTPException(status_code=500, detail=str(e))