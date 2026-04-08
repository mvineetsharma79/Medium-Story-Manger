"""
Settings Router - Endpoints for application settings
All endpoints include curl examples for documentation
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from app.services.file_service import load_stories_data, save_stories_data, get_leaderboard_files
from app.services.app_status_service import AppStatusService
from app.models import CalendarSettingsUpdate

logger = logging.getLogger(__name__)

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
    calendar_settings = data.get("calendar_settings", {})
    
    # Also get app status settings
    app_status = await AppStatusService.get_all_settings()
    
    return {
        "calendar": calendar_settings,
        "app_status": app_status
    }


"""
GET /api/settings/calendar
Description: Get calendar settings only

curl -X GET "http://localhost:8000/api/settings/calendar" | jq '.'
"""
@router.get("/calendar", response_model=Dict[str, Any])
async def get_calendar_settings():
    """Get calendar settings only"""
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
    from config import settings
    return {"stories_root": settings.stories_root, "data_dir": settings.data_dir}


"""
GET /api/settings/app-status
Description: Get application status settings

curl -X GET "http://localhost:8000/api/settings/app-status" | jq '.'
"""
@router.get("/app-status")
async def get_app_status():
    """Get application status settings"""
    try:
        status = await AppStatusService.get_all_settings()
        return status
    except Exception as e:
        logger.error(f"Error getting app status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
PUT /api/settings/app-status
Description: Update application status settings

curl -X PUT "http://localhost:8000/api/settings/app-status" \
  -H "Content-Type: application/json" \
  -d '{"current_mode": "month", "current_month": {"year": 2026, "month": 4}}' | jq '.'
"""
@router.put("/app-status")
async def update_app_status(updates: Dict[str, Any]):
    """Update application status settings"""
    try:
        success = await AppStatusService.update_settings(updates)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update app status")
        
        return {"message": "App status updated", "updates": updates}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating app status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/settings/reset-app-status
Description: Reset application status to defaults

curl -X POST "http://localhost:8000/api/settings/reset-app-status" | jq '.'
"""
@router.post("/reset-app-status")
async def reset_app_status():
    """Reset application status to defaults"""
    try:
        success = await AppStatusService.reset()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to reset app status")
        
        return {"message": "App status reset to defaults", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting app status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/settings/leaderboard-files
Description: Get list of leaderboard JSON files

curl -X GET "http://localhost:8000/api/settings/leaderboard-files" | jq '.'
"""
@router.get("/leaderboard-files")
async def list_leaderboard_files():
    """Get list of leaderboard JSON files"""
    try:
        files = get_leaderboard_files()
        return {
            "leaderboard_files": files,
            "total": len(files)
        }
    except Exception as e:
        logger.error(f"Error listing leaderboard files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/settings/medium-username
Description: Get stored Medium username

curl -X GET "http://localhost:8000/api/settings/medium-username" | jq '.'
"""
@router.get("/medium-username")
async def get_medium_username():
    """Get stored Medium username"""
    try:
        username = await AppStatusService.get_medium_username()
        from config import settings
        return {
            "username": username or settings.medium_username,
            "is_configured": username is not None
        }
    except Exception as e:
        logger.error(f"Error getting medium username: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
PUT /api/settings/medium-username
Description: Update stored Medium username

curl -X PUT "http://localhost:8000/api/settings/medium-username" \
  -H "Content-Type: application/json" \
  -d '{"username": "mvineetsharma"}' | jq '.'
"""
@router.put("/medium-username")
async def update_medium_username(username_data: Dict[str, str]):
    """Update stored Medium username"""
    try:
        username = username_data.get("username")
        if not username:
            raise HTTPException(status_code=400, detail="Username is required")
        
        success = await AppStatusService.set_medium_username(username)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update username")
        
        return {"message": "Medium username updated", "username": username}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating medium username: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/settings/last-fetch
Description: Get last stats fetch time

curl -X GET "http://localhost:8000/api/settings/last-fetch" | jq '.'
"""
@router.get("/last-fetch")
async def get_last_fetch_time():
    """Get last stats fetch time"""
    try:
        last_fetch = await AppStatusService.get_last_fetch_time()
        return {
            "last_fetch": last_fetch,
            "formatted": datetime.fromisoformat(last_fetch).strftime("%Y-%m-%d %H:%M:%S") if last_fetch else None
        }
    except Exception as e:
        logger.error(f"Error getting last fetch time: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/settings/last-fetch
Description: Update last stats fetch time

curl -X POST "http://localhost:8000/api/settings/last-fetch" | jq '.'
"""
@router.post("/last-fetch")
async def update_last_fetch_time(timestamp: Optional[str] = None):
    """Update last stats fetch time"""
    try:
        success = await AppStatusService.set_last_fetch_time(timestamp)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update last fetch time")
        
        return {"message": "Last fetch time updated", "timestamp": timestamp or datetime.now().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating last fetch time: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/settings/import-status
Description: Get current import status

curl -X GET "http://localhost:8000/api/settings/import-status" | jq '.'
"""
@router.get("/import-status")
async def get_import_status():
    """Get current import status"""
    try:
        status = await AppStatusService.get_import_status()
        return status
    except Exception as e:
        logger.error(f"Error getting import status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/settings/all
Description: Get all settings in one request

curl -X GET "http://localhost:8000/api/settings/all" | jq '.'
"""
@router.get("/all")
async def get_all_settings():
    """Get all settings in one request"""
    try:
        # Get calendar settings
        data = await load_stories_data()
        calendar_settings = data.get("calendar_settings", {})
        
        # Get app status
        app_status = await AppStatusService.get_all_settings()
        
        # Get stories root
        from config import settings as config_settings
        stories_root = config_settings.stories_root
        data_dir = config_settings.data_dir
        
        # Get leaderboard files
        leaderboard_files = get_leaderboard_files()
        
        return {
            "calendar": calendar_settings,
            "app_status": app_status,
            "paths": {
                "stories_root": stories_root,
                "data_dir": data_dir
            },
            "leaderboard_files": leaderboard_files,
            "version": "2.0.0"
        }
    except Exception as e:
        logger.error(f"Error getting all settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/settings/system-info
Description: Get system information

curl -X GET "http://localhost:8000/api/settings/system-info" | jq '.'
"""
@router.get("/system-info")
async def get_system_info():
    """Get system information"""
    try:
        import platform
        from config import settings
        
        # Count stories
        data = await load_stories_data()
        stories_count = len(data.get("stories", {}))
        series_count = len(data.get("series", {}))
        
        # Get monthly files count
        from app.services.monthly_storage_service import MonthlyStorageService
        months = await MonthlyStorageService.get_available_months()
        
        return {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "stories_root": settings.stories_root,
            "data_dir": settings.data_dir,
            "stories_count": stories_count,
            "series_count": series_count,
            "monthly_files_count": len(months),
            "debug_mode": settings.debug,
            "api_version": "2.0.0"
        }
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        raise HTTPException(status_code=500, detail=str(e))