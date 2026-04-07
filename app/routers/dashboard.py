"""
Dashboard Router - Endpoints for dashboard statistics
All endpoints include curl examples for documentation
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from datetime import datetime
import logging

from app.services.story_service import StoryService
from app.services.monthly_storage_service import MonthlyStorageService
from app.services.app_status_service import AppStatusService
from app.utils import get_current_year_month

logger = logging.getLogger(__name__)
router = APIRouter()


"""
GET /api/dashboard/stats
Description: Get all dashboard statistics - pre-processed by Python

curl -X GET "http://localhost:8000/api/dashboard/stats" | jq '.'
"""
@router.get("/stats")
async def get_dashboard_stats():
    """Get all dashboard statistics - pre-processed by Python"""
    try:
        # Get current mode and month
        mode = await AppStatusService.get_current_mode()
        current_month = await AppStatusService.get_current_month()
        
        # Get current year/month for stats
        year, month = get_current_year_month()
        if current_month.get("year"):
            year = current_month.get("year", year)
            month = current_month.get("month", month)
        
        # Load monthly stats
        monthly_data = await MonthlyStorageService.load_monthly_stats(year, month)
        monthly_stories = monthly_data.get("stories", {})
        
        # Load all stories
        all_stories = await StoryService.get_all_stories()
        
        # Load global leaderboard status (stories that ever had leaderboard)
        leaderboard_stories = await get_leaderboard_stories_set()
        
        # Calculate stats
        stats = {
            "total": len(all_stories),
            "published": 0,
            "draft": 0,
            "ready": 0,
            "done": 0,
            "bookmarked": 0,
            "leaderboard_count": 0,
            "total_reads": 0,
            "total_views": 0,
            "total_claps": 0,
            "member_reads": 0,
            "member_views": 0,
            "read_ratio": 0,
            "recent_stories": [],
            "leaderboard_stories_count": 0,
            "leaderboard_total_reads": 0,
            "leaderboard_total_views": 0,
            "leaderboard_total_claps": 0,
            "mode": mode,
            "current_month": f"{year}-{month:02d}"
        }
        
        for story in all_stories:
            # Count by status
            if story.status == "Published":
                stats["published"] += 1
            elif story.status == "Draft":
                stats["draft"] += 1
            elif story.status == "Ready":
                stats["ready"] += 1
            elif story.status == "Done":
                stats["done"] += 1
            
            if story.bookmarked:
                stats["bookmarked"] += 1
            
            # Get monthly stats for this story
            monthly_stats = monthly_stories.get(story.key, {})
            reads = monthly_stats.get("reads", 0)
            views = monthly_stats.get("view_count", 0)
            claps = monthly_stats.get("claps", 0)
            member_reads = monthly_stats.get("medium_member_reads", 0)
            member_views = monthly_stats.get("medium_member_views", 0)
            
            stats["total_reads"] += reads
            stats["total_views"] += views
            stats["total_claps"] += claps
            stats["member_reads"] += member_reads
            stats["member_views"] += member_views
            
            # Leaderboard stats (stories that ever had leaderboard)
            if story.key in leaderboard_stories:
                stats["leaderboard_count"] += 1
                stats["leaderboard_total_reads"] += reads
                stats["leaderboard_total_views"] += views
                stats["leaderboard_total_claps"] += claps
        
        # Calculate ratios
        if stats["total_views"] > 0:
            stats["read_ratio"] = round((stats["total_reads"] / stats["total_views"]) * 100, 1)
        
        if stats["total_reads"] > 0:
            stats["member_read_percent"] = round((stats["member_reads"] / stats["total_reads"]) * 100, 1)
        else:
            stats["member_read_percent"] = 0
        
        if stats["leaderboard_total_reads"] > 0:
            stats["leaderboard_member_percent"] = round(
                (stats.get("leaderboard_member_reads", 0) / stats["leaderboard_total_reads"]) * 100, 1
            )
        else:
            stats["leaderboard_member_percent"] = 0
        
        # Get recent stories (last 8 by created_date)
        recent = sorted(all_stories, key=lambda x: x.created_date or "", reverse=True)[:8]
        stats["recent_stories"] = [
            {
                "key": s.key,
                "name": s.name,
                "status": s.status,
                "series": s.series,
                "leaderboard": s.key in leaderboard_stories
            }
            for s in recent
        ]
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/dashboard/schedule
Description: Get upcoming schedule - pre-processed by Python

curl -X GET "http://localhost:8000/api/dashboard/schedule" | jq '.'
"""
@router.get("/schedule")
async def get_upcoming_schedule():
    """Get upcoming schedule - pre-processed by Python"""
    try:
        from app.services.calendar_service import CalendarService
        
        calendar, summary = await CalendarService.generate_calendar()
        
        # Take first 8 items for dashboard
        upcoming = calendar[:8]
        
        return {
            "schedule": [
                {
                    "date": c["date"],
                    "name": c["name"],
                    "series": c.get("series"),
                    "story_key": c["story_key"]
                }
                for c in upcoming
            ],
            "total_scheduled": summary.get("total_scheduled", 0),
            "stories_per_week": summary.get("stories_per_week", 3),
            "series_spacing": summary.get("series_spacing_default", 7),
            "remaining": summary.get("remaining_unpublished", 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting schedule: {e}")
        return {"schedule": [], "total_scheduled": 0, "stories_per_week": 3, "series_spacing": 7, "remaining": 0}


async def get_leaderboard_stories_set():
    """Get set of story keys that ever had leaderboard in any month"""
    try:
        available_months = await MonthlyStorageService.get_available_months()
        leaderboard_stories = set()
        
        for month_info in available_months:
            monthly_data = await MonthlyStorageService.load_monthly_stats(
                month_info["year"], month_info["month"]
            )
            for story_key, story_data in monthly_data.get("stories", {}).items():
                if story_data.get("leaderboard", False):
                    leaderboard_stories.add(story_key)
        
        return leaderboard_stories
    except Exception as e:
        logger.error(f"Error getting leaderboard stories: {e}")
        return set()