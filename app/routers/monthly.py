"""
Monthly Router - Endpoints for monthly statistics management
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from app.services.monthly_storage_service import MonthlyStorageService
from app.services.story_service import StoryService
from app.services.app_status_service import AppStatusService
from app.models import StoryResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/available-months")
async def get_available_months():
    """Get all available months with monthly stats files"""
    try:
        months = await MonthlyStorageService.get_available_months()
        current_mode = await AppStatusService.get_current_mode()
        current_month = await AppStatusService.get_current_month()
        
        return {
            "months": months,
            "current_mode": current_mode,
            "current_month": current_month,
            "total": len(months)
        }
    except Exception as e:
        logger.error(f"Error getting available months: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stories")
async def get_stories_for_month(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None)
):
    """Get stories for a specific month (merges monthly stats with permanent data)"""
    try:
        # Get the target month
        if year is None or month is None:
            current = await AppStatusService.get_current_month()
            year = current["year"]
            month = current["month"]
        
        # Load monthly stats
        monthly_data = await MonthlyStorageService.load_monthly_stats(year, month)
        monthly_stories = monthly_data.get("stories", {})
        
        # Load all permanent stories
        all_stories = await StoryService.get_all_stories()
        
        # Merge: For each permanent story, add monthly stats if available
        result = []
        for story in all_stories:
            story_dict = story.dict()
            monthly_stats = monthly_stories.get(story.key, {})
            
            # Add monthly stats (with defaults)
            story_dict["monthly_stats"] = {
                "reads": monthly_stats.get("reads", 0),
                "view_count": monthly_stats.get("view_count", 0),
                "claps": monthly_stats.get("claps", 0),
                "responses": monthly_stats.get("responses", 0),
                "medium_member_reads": monthly_stats.get("medium_member_reads", 0),
                "medium_member_views": monthly_stats.get("medium_member_views", 0),
                "medium_nonmember_reads": monthly_stats.get("medium_nonmember_reads", 0),
                "medium_nonmember_views": monthly_stats.get("medium_nonmember_views", 0),
                "medium_read_ratio": monthly_stats.get("medium_read_ratio", 0),
                "medium_member_read_percentage": monthly_stats.get("medium_member_read_percentage", 0),
                "medium_new_followers": monthly_stats.get("medium_new_followers", 0),
                "medium_highlights": monthly_stats.get("medium_highlights", 0),
                "leaderboard": monthly_stats.get("leaderboard", False),
                "leaderboard_nanos": monthly_stats.get("leaderboard_nanos", 0),
                "medium_earnings": monthly_stats.get("medium_earnings", 0),
                "last_stats_update": monthly_stats.get("last_stats_update")
            }
            
            # Add month info
            story_dict["current_month"] = f"{year}-{month:02d}"
            story_dict["has_monthly_data"] = story.key in monthly_stories
            
            result.append(StoryResponse(**story_dict))
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting stories for month: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stories/{story_key:path}")
async def get_story_for_month(
    story_key: str,
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None)
):
    """Get a single story with monthly stats for a specific month"""
    try:
        from urllib.parse import unquote
        decoded_key = unquote(story_key)
        
        # Get the target month
        if year is None or month is None:
            current = await AppStatusService.get_current_month()
            year = current["year"]
            month = current["month"]
        
        # Get permanent story data
        story = await StoryService.get_story(decoded_key)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        # Get monthly stats
        monthly_stats = await MonthlyStorageService.get_story_monthly_stats(
            decoded_key, year, month
        )
        
        story_dict = story.dict()
        story_dict["monthly_stats"] = monthly_stats or {
            "reads": 0,
            "view_count": 0,
            "claps": 0,
            "responses": 0,
            "medium_member_reads": 0,
            "medium_member_views": 0,
            "medium_nonmember_reads": 0,
            "medium_nonmember_views": 0,
            "medium_read_ratio": 0,
            "medium_member_read_percentage": 0,
            "medium_new_followers": 0,
            "medium_highlights": 0,
            "leaderboard": False,
            "leaderboard_nanos": 0,
            "medium_earnings": 0
        }
        story_dict["current_month"] = f"{year}-{month:02d}"
        story_dict["has_monthly_data"] = monthly_stats is not None
        
        return StoryResponse(**story_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting story for month: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/stories/{story_key:path}")
async def update_story_monthly_stats(
    story_key: str,
    year: int,
    month: int,
    stats_data: Dict[str, Any]
):
    """Update a story's monthly stats for a specific month"""
    try:
        from urllib.parse import unquote
        decoded_key = unquote(story_key)
        
        # Get the story to get its title
        story = await StoryService.get_story(decoded_key)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        # Update monthly stats
        success = await MonthlyStorageService.update_story_monthly_stats(
            decoded_key, year, month, stats_data, story.name
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update monthly stats")
        
        return {"message": "Monthly stats updated successfully", "story_key": decoded_key}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating story monthly stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/switch-month")
async def switch_month(year: int, month: int):
    """Switch the current view to a specific month"""
    try:
        # Update app status
        await AppStatusService.set_current_mode("month")
        await AppStatusService.set_current_month(year, month)
        
        month_name = datetime(year, month, 1).strftime("%B %Y")
        
        return {
            "message": f"Switched to {month_name}",
            "year": year,
            "month": month,
            "display": month_name,
            "mode": "month"
        }
        
    except Exception as e:
        logger.error(f"Error switching month: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/switch-to-dashboard")
async def switch_to_dashboard():
    """Switch back to dashboard mode (all stories with current month stats)"""
    try:
        await AppStatusService.set_current_mode("dashboard")
        
        return {
            "message": "Switched to dashboard mode",
            "mode": "dashboard"
        }
        
    except Exception as e:
        logger.error(f"Error switching to dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/story-months/{story_key:path}")
async def get_story_available_months(story_key: str):
    """Get all months where a story has data"""
    try:
        from urllib.parse import unquote
        decoded_key = unquote(story_key)
        
        months = await MonthlyStorageService.get_months_for_story(decoded_key)
        
        return {
            "story_key": decoded_key,
            "months": months,
            "total": len(months)
        }
        
    except Exception as e:
        logger.error(f"Error getting story months: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ensure-story-in-month")
async def ensure_story_in_month(
    story_key: str,
    year: int,
    month: int
):
    """Ensure a story exists in a monthly file (create with zeros if not)"""
    try:
        from urllib.parse import unquote
        decoded_key = unquote(story_key)
        
        story = await StoryService.get_story(decoded_key)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        success = await MonthlyStorageService.ensure_story_in_month(
            decoded_key, year, month, story.name
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to ensure story in month")
        
        return {"message": "Story ensured in month", "story_key": decoded_key}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ensuring story in month: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_monthly_summary(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None)
):
    """Get summary statistics for a specific month"""
    try:
        if year is None or month is None:
            current = await AppStatusService.get_current_month()
            year = current["year"]
            month = current["month"]
        
        summary = await MonthlyStorageService.get_monthly_summary(year, month)
        return summary
        
    except Exception as e:
        logger.error(f"Error getting monthly summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/month")
async def delete_month(year: int, month: int):
    """Delete a monthly stats file entirely"""
    try:
        success = await MonthlyStorageService.delete_month(year, month)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"No data found for {year}-{month:02d}")
        
        return {"message": f"Deleted monthly data for {year}-{month:02d}", "success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting month: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/copy-month")
async def copy_month(
    source_year: int,
    source_month: int,
    target_year: int,
    target_month: int
):
    """Copy monthly stats from one month to another"""
    try:
        success = await MonthlyStorageService.copy_monthly_stats(
            source_year, source_month, target_year, target_month
        )
        
        if not success:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to copy from {source_year}-{source_month:02d} to {target_year}-{target_month:02d}"
            )
        
        return {
            "message": f"Copied monthly data from {source_year}-{source_month:02d} to {target_year}-{target_month:02d}",
            "success": True,
            "source": f"{source_year}-{source_month:02d}",
            "target": f"{target_year}-{target_month:02d}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error copying month: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-update")
async def batch_update_monthly_stats(
    year: int,
    month: int,
    updates: Dict[str, Dict[str, Any]]
):
    """Update multiple stories' monthly stats in one operation"""
    try:
        results = await MonthlyStorageService.batch_update_monthly_stats(updates, year, month)
        
        success_count = sum(1 for v in results.values() if v)
        failed_count = len(results) - success_count
        
        return {
            "message": f"Updated {success_count} stories, {failed_count} failed",
            "success": success_count > 0,
            "year": year,
            "month": month,
            "results": results,
            "success_count": success_count,
            "failed_count": failed_count
        }
        
    except Exception as e:
        logger.error(f"Error in batch update: {e}")
        raise HTTPException(status_code=500, detail=str(e))