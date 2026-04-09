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
            "published_due": 0,
            "ready": 0,
            "done": 0,
            "draft": 0,
            "bookmarked": 0,
            "leaderboard_count": 0,
            "total_reads": 0,
            "total_views": 0,
            "total_claps": 0,
            "total_presentations": 0,
            "member_reads": 0,
            "member_views": 0,
            "read_ratio": 0,
            "member_read_percent": 0,
            "member_view_percent": 0,
            "recent_stories": [],
            "leaderboard_stories_count": 0,
            "leaderboard_total_reads": 0,
            "leaderboard_total_views": 0,
            "leaderboard_total_claps": 0,
            "leaderboard_member_reads": 0,
            "leaderboard_member_views": 0,
            "leaderboard_member_percent": 0,
            "mode": mode,
            "current_month": f"{year}-{month:02d}"
        }
        
        for story in all_stories:
            # Count by status
            if story.status == "Published":
                stats["published"] += 1
            elif story.status == "Published Due":
                stats["published_due"] += 1
            elif story.status == "Ready":
                stats["ready"] += 1
            elif story.status == "Done":
                stats["done"] += 1
            elif story.status == "Draft":
                stats["draft"] += 1
            
            if story.bookmarked:
                stats["bookmarked"] += 1
            
            # Get monthly stats for this story
            monthly_stats = monthly_stories.get(story.key, {})
            reads = monthly_stats.get("reads", 0)
            views = monthly_stats.get("view_count", 0)
            claps = monthly_stats.get("claps", 0)
            member_reads = monthly_stats.get("medium_member_reads", 0)
            member_views = monthly_stats.get("medium_member_views", 0)
            
            # Get presentations from totalStats if available
            presentations = 0
            if story.medium and story.medium.totalStats:
                presentations = story.medium.totalStats.presentations or 0
            
            stats["total_reads"] += reads
            stats["total_views"] += views
            stats["total_claps"] += claps
            stats["total_presentations"] += presentations
            stats["member_reads"] += member_reads
            stats["member_views"] += member_views
            
            # Leaderboard stats (stories that ever had leaderboard)
            if story.key in leaderboard_stories:
                stats["leaderboard_count"] += 1
                stats["leaderboard_total_reads"] += reads
                stats["leaderboard_total_views"] += views
                stats["leaderboard_total_claps"] += claps
                stats["leaderboard_member_reads"] += member_reads
                stats["leaderboard_member_views"] += member_views
        
        # Calculate ratios
        if stats["total_views"] > 0:
            stats["read_ratio"] = round((stats["total_reads"] / stats["total_views"]) * 100, 1)
        
        if stats["total_reads"] > 0:
            stats["member_read_percent"] = round((stats["member_reads"] / stats["total_reads"]) * 100, 1)
        else:
            stats["member_read_percent"] = 0
        
        if stats["total_views"] > 0:
            stats["member_view_percent"] = round((stats["member_views"] / stats["total_views"]) * 100, 1)
        else:
            stats["member_view_percent"] = 0
        
        if stats["leaderboard_total_reads"] > 0:
            stats["leaderboard_member_percent"] = round(
                (stats["leaderboard_member_reads"] / stats["leaderboard_total_reads"]) * 100, 1
            )
        else:
            stats["leaderboard_member_percent"] = 0
        
        # Get recent stories (last 8 by created_date)
        recent = sorted(all_stories, key=lambda x: x.createdDate or "", reverse=True)[:8]
        stats["recent_stories"] = [
            {
                "key": s.key,
                "name": s.name or s.title,
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


"""
GET /api/dashboard/leaderboard-stories
Description: Get all stories that ever had leaderboard

curl -X GET "http://localhost:8000/api/dashboard/leaderboard-stories" | jq '.'
"""
@router.get("/leaderboard-stories")
async def get_leaderboard_stories():
    """Get all stories that ever had leaderboard with their details"""
    try:
        leaderboard_stories_set = await get_leaderboard_stories_set()
        all_stories = await StoryService.get_all_stories()
        
        # Get current month stats
        year, month = get_current_year_month()
        monthly_data = await MonthlyStorageService.load_monthly_stats(year, month)
        monthly_stories = monthly_data.get("stories", {})
        
        leaderboard_details = []
        for story in all_stories:
            if story.key in leaderboard_stories_set:
                monthly_stats = monthly_stories.get(story.key, {})
                leaderboard_details.append({
                    "key": story.key,
                    "name": story.name or story.title,
                    "series": story.series,
                    "status": story.status,
                    "published_date": story.publishedDate,
                    "reads": monthly_stats.get("reads", 0),
                    "views": monthly_stats.get("view_count", 0),
                    "claps": monthly_stats.get("claps", 0),
                    "member_reads": monthly_stats.get("medium_member_reads", 0),
                    "member_views": monthly_stats.get("medium_member_views", 0),
                    "earnings": monthly_stats.get("medium_earnings", 0),
                    "leaderboard_nanos": monthly_stats.get("leaderboard_nanos", 0)
                })
        
        # Sort by earnings (highest first)
        leaderboard_details.sort(key=lambda x: x.get("earnings", 0), reverse=True)
        
        return {
            "stories": leaderboard_details,
            "total": len(leaderboard_details),
            "total_earnings": sum(s.get("earnings", 0) for s in leaderboard_details),
            "total_earnings_formatted": f"${sum(s.get('earnings', 0) for s in leaderboard_details) / 1000000000:.2f}"
        }
        
    except Exception as e:
        logger.error(f"Error getting leaderboard stories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/dashboard/trends
Description: Get monthly trends for key metrics

curl -X GET "http://localhost:8000/api/dashboard/trends" | jq '.'
"""
@router.get("/trends")
async def get_monthly_trends(limit: int = 6):
    """Get monthly trends for key metrics (last N months)"""
    try:
        available_months = await MonthlyStorageService.get_available_months()
        
        # Take last N months
        recent_months = available_months[:limit]
        
        trends = []
        for month_info in recent_months:
            summary = await MonthlyStorageService.get_monthly_summary(
                month_info["year"], month_info["month"]
            )
            trends.append(summary)
        
        # Calculate percentage changes
        for i, trend in enumerate(trends):
            if i < len(trends) - 1:
                prev = trends[i + 1]
                trend["read_change_percent"] = calculate_change_percent(
                    trend.get("total_reads", 0), prev.get("total_reads", 0)
                )
                trend["view_change_percent"] = calculate_change_percent(
                    trend.get("total_views", 0), prev.get("total_views", 0)
                )
                trend["earning_change_percent"] = calculate_change_percent(
                    trend.get("total_earnings", 0), prev.get("total_earnings", 0)
                )
            else:
                trend["read_change_percent"] = 0
                trend["view_change_percent"] = 0
                trend["earning_change_percent"] = 0
        
        return {
            "trends": trends,
            "total_months": len(trends)
        }
        
    except Exception as e:
        logger.error(f"Error getting monthly trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/dashboard/top-stories
Description: Get top performing stories for current month

curl -X GET "http://localhost:8000/api/dashboard/top-stories" | jq '.'
"""
@router.get("/top-stories")
async def get_top_stories(limit: int = 10, sort_by: str = "reads"):
    """Get top performing stories for current month"""
    try:
        year, month = get_current_year_month()
        monthly_data = await MonthlyStorageService.load_monthly_stats(year, month)
        monthly_stories = monthly_data.get("stories", {})
        
        all_stories = await StoryService.get_all_stories()
        
        # Build list with stats
        stories_with_stats = []
        for story in all_stories:
            stats = monthly_stories.get(story.key, {})
            stories_with_stats.append({
                "key": story.key,
                "name": story.name or story.title,
                "series": story.series,
                "reads": stats.get("reads", 0),
                "views": stats.get("view_count", 0),
                "claps": stats.get("claps", 0),
                "member_reads": stats.get("medium_member_reads", 0),
                "member_views": stats.get("medium_member_views", 0),
                "earnings": stats.get("medium_earnings", 0),
                "leaderboard": stats.get("leaderboard", False),
                "read_ratio": stats.get("medium_read_ratio", 0)
            })
        
        # Sort by specified field
        valid_sort_fields = ["reads", "views", "claps", "earnings", "member_reads"]
        if sort_by not in valid_sort_fields:
            sort_by = "reads"
        
        stories_with_stats.sort(key=lambda x: x.get(sort_by, 0), reverse=True)
        
        return {
            "stories": stories_with_stats[:limit],
            "total": len(stories_with_stats),
            "sort_by": sort_by,
            "month": f"{year}-{month:02d}"
        }
        
    except Exception as e:
        logger.error(f"Error getting top stories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
GET /api/dashboard/quick-stats
Description: Get quick stats for dashboard widgets

curl -X GET "http://localhost:8000/api/dashboard/quick-stats" | jq '.'
"""
@router.get("/quick-stats")
async def get_quick_stats():
    """Get quick stats for dashboard widgets"""
    try:
        year, month = get_current_year_month()
        
        # Get monthly summary
        summary = await MonthlyStorageService.get_monthly_summary(year, month)
        
        # Get all stories
        all_stories = await StoryService.get_all_stories()
        
        # Calculate additional quick stats
        published_this_month = 0
        for story in all_stories:
            if story.publishedDate and story.publishedDate.startswith(f"{year}-{month:02d}"):
                published_this_month += 1
        
        # Get leaderboard count
        leaderboard_stories = await get_leaderboard_stories_set()
        
        return {
            "current_month": f"{year}-{month:02d}",
            "total_stories": len(all_stories),
            "published_this_month": published_this_month,
            "total_reads_this_month": summary.get("total_reads", 0),
            "total_views_this_month": summary.get("total_views", 0),
            "total_earnings_this_month": summary.get("total_earnings", 0),
            "total_earnings_formatted": summary.get("total_earnings_formatted", "$0.00"),
            "leaderboard_stories_count": len(leaderboard_stories),
            "stories_with_data_this_month": summary.get("total_stories", 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting quick stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


def calculate_change_percent(current: int, previous: int) -> float:
    """Calculate percentage change between two values"""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)