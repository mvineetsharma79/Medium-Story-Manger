"""
Calendar Router - Endpoints for publishing calendar management
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
from collections import defaultdict

from app.models import CalendarResponse, CalendarEntry
from app.services.file_service import load_stories_data, save_stories_data
from app.services.story_service import StoryService
from app.models import StoryUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=CalendarResponse)
async def get_calendar():
    """Get calendar - reads publishedDueDate from ALL stories"""
    try:
        data = await load_stories_data()
        stories = data.get("stories", {})
        
        schedule = []
        
        for story_key, story in stories.items():
            due_date = story.get("publishedDueDate")
            
            if due_date:
                # Clean the date format
                if 'T' in due_date:
                    due_date = due_date.split('T')[0]
                
                # Parse date to get weekday
                try:
                    date_obj = datetime.strptime(due_date, "%Y-%m-%d")
                    weekday = date_obj.strftime("%A")
                except:
                    weekday = "Unknown"
                
                schedule.append({
                    "date": due_date,
                    "weekday": weekday,
                    "story_key": story_key,
                    "name": story.get("name", story.get("title", story_key)),
                    "series": story.get("series"),
                    "part": None,
                    "read_time": story.get("read_time", story.get("medium_reading_time", 0))
                })
        
        schedule.sort(key=lambda x: x["date"])
        
        date_counts = defaultdict(int)
        for entry in schedule:
            date_counts[entry["date"]] += 1
        
        return CalendarResponse(
            generated=datetime.now().isoformat(),
            summary={
                "total_scheduled": len(schedule),
                "dates_with_stories": len(date_counts),
                "max_stories_per_day": max(date_counts.values()) if date_counts else 0
            },
            schedule=[CalendarEntry(**entry) for entry in schedule]
        )
        
    except Exception as e:
        logger.error(f"Calendar error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule-drafts")
async def schedule_draft_stories():
    """
    Schedule draft stories without due dates.
    Simple algorithm: for each story, find first date with <2 stories.
    """
    try:
        data = await load_stories_data()
        stories = data.get("stories", {})
        
        # Count existing publishedDueDate per date
        occupied = defaultdict(int)
        for story_key, story in stories.items():
            due = story.get("publishedDueDate")
            if due:
                if 'T' in due:
                    due = due.split('T')[0]
                occupied[due] += 1
        
        # Get all draft stories without due dates
        drafts = []
        for story_key, story in stories.items():
            due = story.get("publishedDueDate")
            status = story.get("status", "Draft")
            if not due and status == "Draft":
                drafts.append({
                    "key": story_key,
                    "name": story.get("name", story.get("title", story_key)),
                    "series": story.get("series"),
                    "createdDate": story.get("createdDate") or "9999-12-31"
                })
        
        if not drafts:
            return {"success": True, "message": "No drafts found", "scheduled": 0}
        
        # Sort by series size (largest first)
        series_size = defaultdict(int)
        for d in drafts:
            series_size[d["series"] or "STANDALONE"] += 1
        drafts.sort(key=lambda x: -series_size[x["series"] or "STANDALONE"])
        
        scheduled = []
        start_date = datetime.now() + timedelta(days=1)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for story in drafts:
            # For each story, find first available date
            check_date = start_date
            days_checked = 0
            
            while days_checked < 365:
                date_str = check_date.strftime("%Y-%m-%d")
                current = occupied.get(date_str, 0)
                
                if current < 2:
                    # Schedule here
                    stories[story["key"]]["publishedDueDate"] = date_str
                    occupied[date_str] = current + 1
                    scheduled.append({
                        "date": date_str,
                        "name": story["name"],
                        "series": story["series"]
                    })
                    break
                
                check_date += timedelta(days=1)
                days_checked += 1
        
        # Save
        await save_stories_data(data)
        
        # Summary
        summary = defaultdict(list)
        for s in scheduled:
            summary[s["date"]].append(s["name"])
        
        return {
            "success": True,
            "scheduled": len(scheduled),
            "schedule_summary": dict(sorted(summary.items())),
            "scheduled_stories": scheduled[:50]
        }
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/clear-due-dates")
async def clear_due_dates(clear_data: Dict[str, str] = None):
    """
    Clear publishedDueDate from stories by status.
    Default: Clear ONLY Draft stories.
    """
    try:
        data = await load_stories_data()
        stories = data.get("stories", {})
        
        status_filter = "Draft"
        if clear_data and clear_data.get("status"):
            status_filter = clear_data.get("status")
        
        cleared_count = 0
        
        for story_key, story in stories.items():
            status = story.get("status", "Draft")
            due_date = story.get("publishedDueDate")
            
            should_clear = False
            if status_filter.lower() == "all":
                should_clear = bool(due_date)
            elif status == status_filter:
                should_clear = bool(due_date)
            
            if should_clear:
                story["publishedDueDate"] = None
                cleared_count += 1
        
        await save_stories_data(data)
        
        return {
            "success": True,
            "message": f"Cleared due dates for {cleared_count} stories",
            "cleared_count": cleared_count
        }
        
    except Exception as e:
        logger.error(f"Error clearing due dates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-single-due-date/{story_key:path}")
async def clear_single_due_date(story_key: str):
    """Clear publishedDueDate from a single story"""
    try:
        from urllib.parse import unquote
        
        decoded_key = unquote(story_key)
        
        story = await StoryService.get_story(decoded_key)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        update_data = {"publishedDueDate": None}
        updated_story = await StoryService.update_story(story.key, StoryUpdate(**update_data))
        
        if not updated_story:
            raise HTTPException(status_code=500, detail="Failed to clear due date")
        
        return {
            "success": True,
            "message": "Published due date cleared",
            "story_key": story.key,
            "story_name": story.name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing due date: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schedule")
async def get_calendar_schedule():
    """Get calendar schedule (compatibility endpoint)"""
    try:
        data = await load_stories_data()
        stories = data.get("stories", {})
        
        schedule = []
        for story_key, story in stories.items():
            due_date = story.get("publishedDate")
            if due_date:
                if 'T' in due_date:
                    due_date = due_date.split('T')[0]
                
                schedule.append({
                    "date": due_date,
                    "story_key": story_key,
                    "name": story.get("name", story.get("title", story_key)),
                    "series": story.get("series"),
                    "status": story.get("status", "Draft")
                })
        
        schedule.sort(key=lambda x: x["date"])
        
        return {"schedule": schedule, "total": len(schedule)}
        
    except Exception as e:
        logger.error(f"Error getting calendar schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upcoming")
async def get_upcoming_schedule(limit: int = 10):
    """Get upcoming schedule entries"""
    try:
        data = await load_stories_data()
        stories = data.get("stories", {})
        
        today = datetime.now().date()
        
        upcoming = []
        for story_key, story in stories.items():
            due_date = story.get("publishedDueDate")
            if due_date:
                if 'T' in due_date:
                    due_date = due_date.split('T')[0]
                
                try:
                    due_date_obj = datetime.strptime(due_date, "%Y-%m-%d").date()
                    if due_date_obj >= today:
                        upcoming.append({
                            "date": due_date,
                            "story_key": story_key,
                            "name": story.get("name", story.get("title", story_key)),
                            "series": story.get("series")
                        })
                except:
                    pass
        
        upcoming.sort(key=lambda x: x["date"])
        
        return {"schedule": upcoming[:limit], "total": len(upcoming), "limit": limit}
        
    except Exception as e:
        logger.error(f"Error getting upcoming schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_calendar_stats():
    """Get calendar statistics"""
    try:
        data = await load_stories_data()
        stories = data.get("stories", {})
        
        date_counts = defaultdict(int)
        status_counts = defaultdict(int)
        
        for story_key, story in stories.items():
            due_date = story.get("publishedDueDate")
            if due_date:
                if 'T' in due_date:
                    due_date = due_date.split('T')[0]
                date_counts[due_date] += 1
                status_counts[story.get("status", "Draft")] += 1
        
        return {
            "total_stories_with_due_dates": len([s for s in stories.values() if s.get("publishedDueDate")]),
            "unique_dates": len(date_counts),
            "max_stories_per_day": max(date_counts.values()) if date_counts else 0,
            "status_breakdown": dict(status_counts)
        }
        
    except Exception as e:
        logger.error(f"Error getting calendar stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))