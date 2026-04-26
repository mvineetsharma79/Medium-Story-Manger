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
        stories = data.get("stories", {})
        settings = data.get("calendar_settings", {})
        default_spacing = settings.get("series_spacing_days", 7)
        
        result = []
        for name, info in series_data.items():
            total_stories = info.get("total_stories", 0)
            published = info.get("published", 0)
            progress_percent = round((published / max(total_stories, 1)) * 100, 1)
            
            # Get the actual story count
            story_keys = info.get("stories", [])
            actual_story_count = len(story_keys)
            
            # Count stories by status
            status_counts = {
                "Published": 0,
                "Published Due": 0,
                "Ready": 0,
                "Done": 0,
                "Draft": 0
            }
            
            # Calculate total performance metrics for this series (SUM of all stories)
            total_presentations = 0
            total_views = 0
            total_reads = 0
            total_claps = 0
            total_responses = 0
            total_earnings = 0
            
            for story_key in story_keys:
                if story_key in stories:
                    story = stories[story_key]
                    story_status = story.get("status", "Draft")
                    
                    # Count status
                    if story_status in status_counts:
                        status_counts[story_status] += 1
                    else:
                        status_counts["Draft"] += 1
                    
                    # Get from medium.totalStats
                    medium_data = story.get("medium")
                    if medium_data and isinstance(medium_data, dict):
                        total_stats = medium_data.get("totalStats", {})
                        total_presentations += total_stats.get("presentations", 0) or 0
                        total_views += total_stats.get("views", 0) or 0
                        total_reads += total_stats.get("reads", 0) or 0
                        total_claps += medium_data.get("clapCount", 0) or 0
                        total_responses += medium_data.get("responsesCount", 0) or 0
                        total_earnings_data = medium_data.get("totalEarnings", {})
                        total_earnings += total_earnings_data.get("amount", 0) or 0

                        totalEarniings=0
                    else:
                        # Legacy fields
                        total_presentations += story.get("presentation_count", 0) or 0
                        #total_views += story.get("lifetime_views", 0) or 0
                        total_views += story.get("lifetime_views", 0) or 0
                        total_reads += story.get("lifetime_reads", 0) or 0
                        total_claps += story.get("lifetime_claps", 0) or 0
                        total_responses += story.get("responses", 0) or 0
            
            result.append({
                "name": name,
                "total_stories": total_stories,
                "published": published,
                "spacing_days": info.get("spacing_days", default_spacing),
                "progress_percent": progress_percent,
                "story_count": actual_story_count,
                "status_counts": status_counts,
                # Performance metrics (SUM of all stories in series)
                "total_presentations": total_presentations,
                "total_views": total_views,
                "total_reads": total_reads,
                "total_claps": total_claps,
                "total_responses": total_responses,
                "total_earnings" : total_earnings
            })
        #return medium_data    
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
        from urllib.parse import unquote
        decoded_name = unquote(series_name)
        
        data = await load_stories_data()
        series_data = data.get("series", {})
        
        if decoded_name not in series_data:
            raise HTTPException(status_code=404, detail="Series not found")
        
        settings = data.get("calendar_settings", {})
        default_spacing = settings.get("series_spacing_days", 7)
        info = series_data[decoded_name]
        
        return SeriesResponse(
            name=decoded_name,
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
        from urllib.parse import unquote
        decoded_name = unquote(series_name)
        
        data = await load_stories_data()
        series = data.get("series", {})
        stories = data.get("stories", {})
        
        if decoded_name not in series:
            raise HTTPException(status_code=404, detail="Series not found")
        
        if update_data.name:
            new_name = update_data.name.strip()
            old_name = decoded_name
            
            if new_name == old_name:
                pass
            elif new_name in series:
                raise HTTPException(status_code=400, detail="Series with new name already exists")
            else:
                series[new_name] = series.pop(old_name)
                series[new_name]["name"] = new_name
                
                # Update series name in all stories
                for story_key in series[new_name]["stories"]:
                    if story_key in stories:
                        stories[story_key]["series"] = new_name
                
                decoded_name = new_name
        
        if update_data.spacing_days:
            series[decoded_name]["spacing_days"] = update_data.spacing_days
        
        data["stories"] = stories
        data["series"] = series
        
        await save_stories_data(data)
        
        settings = data.get("calendar_settings", {})
        default_spacing = settings.get("series_spacing_days", 7)
        info = series[decoded_name]
        
        return SeriesResponse(
            name=decoded_name,
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
        from urllib.parse import unquote
        decoded_name = unquote(series_name)
        
        data = await load_stories_data()
        series = data.get("series", {})
        
        if decoded_name not in series:
            raise HTTPException(status_code=404, detail="Series not found")
        
        stories = data.get("stories", {})
        
        # Remove series association from all stories in this series
        for story_key in series[decoded_name].get("stories", []):
            if story_key in stories:
                stories[story_key]["series"] = None
        
        # Delete the series
        del series[decoded_name]
        
        data["stories"] = stories
        data["series"] = series
        
        await save_stories_data(data)
        
        return {"message": f"Series '{decoded_name}' deleted successfully", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete series error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/series/{series_name}/stories
Description: Get all stories in a series

curl -X GET "http://localhost:8000/api/series/Python%20Tutorials/stories" | jq '.'
"""
@router.get("/{series_name}/stories")
async def get_series_stories(series_name: str):
    """Get all stories in a series"""
    try:
        from urllib.parse import unquote
        decoded_name = unquote(series_name)
        
        data = await load_stories_data()
        series = data.get("series", {})
        
        if decoded_name not in series:
            raise HTTPException(status_code=404, detail="Series not found")
        
        story_keys = series[decoded_name].get("stories", [])
        all_stories = data.get("stories", {})
        
        stories = []
        for key in story_keys:
            if key in all_stories:
                story = all_stories[key]
                # Extract part number from title
                part_number = parse_series_number(story.get("name", story.get("title", "")))
                
                stories.append({
                    "key": key,
                    "name": story.get("name", story.get("title", key)),
                    "status": story.get("status", "Draft"),
                    "published_date": story.get("publishedDate"),
                    "created_date": story.get("createdDate"),
                    "part": part_number,
                    "read_time": story.get("read_time", story.get("medium_reading_time", 0)),
                    "word_count": story.get("word_count", 0)
                })
        
        # Sort by part number
        stories.sort(key=lambda x: x.get("part", 999))
        
        return {
            "series_name": decoded_name,
            "total_stories": len(stories),
            "published_count": sum(1 for s in stories if s["status"] == "Published"),
            "stories": stories
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting series stories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/series/{series_name}/reorder
Description: Reorder stories in a series

curl -X POST "http://localhost:8000/api/series/Python%20Tutorials/reorder" \
  -H "Content-Type: application/json" \
  -d '{"story_order": ["key1", "key2", "key3"]}' | jq '.'
"""
@router.post("/{series_name}/reorder")
async def reorder_series_stories(series_name: str, order_data: Dict[str, List[str]]):
    """Reorder stories in a series"""
    try:
        from urllib.parse import unquote
        decoded_name = unquote(series_name)
        
        data = await load_stories_data()
        series = data.get("series", {})
        
        if decoded_name not in series:
            raise HTTPException(status_code=404, detail="Series not found")
        
        new_order = order_data.get("story_order", [])
        current_stories = series[decoded_name].get("stories", [])
        
        # Validate that all stories in new_order exist in current_stories
        if set(new_order) != set(current_stories):
            raise HTTPException(status_code=400, detail="Story order does not match existing stories")
        
        # Update the order
        series[decoded_name]["stories"] = new_order
        data["series"] = series
        
        await save_stories_data(data)
        
        return {
            "message": f"Series '{decoded_name}' reordered successfully",
            "story_order": new_order,
            "total_stories": len(new_order)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reordering series: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/series/stats
Description: Get overall series statistics

curl -X GET "http://localhost:8000/api/series/stats" | jq '.'
"""
@router.get("/stats")
async def get_series_stats():
    """Get overall series statistics"""
    try:
        data = await load_stories_data()
        series_data = data.get("series", {})
        
        total_series = len(series_data)
        total_stories_in_series = 0
        total_published_in_series = 0
        
        for series_name, info in series_data.items():
            total_stories_in_series += info.get("total_stories", 0)
            total_published_in_series += info.get("published", 0)
        
        # Count standalone stories (not in any series)
        stories = data.get("stories", {})
        standalone_count = 0
        for story_key, story in stories.items():
            if not story.get("series"):
                standalone_count += 1
        
        return {
            "total_series": total_series,
            "total_stories_in_series": total_stories_in_series,
            "total_published_in_series": total_published_in_series,
            "standalone_stories": standalone_count,
            "average_series_size": round(total_stories_in_series / max(total_series, 1), 1),
            "completion_rate": round((total_published_in_series / max(total_stories_in_series, 1)) * 100, 1)
        }
        
    except Exception as e:
        logger.error(f"Error getting series stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))