from fastapi import APIRouter, HTTPException, Query, Path, Request
from typing import List, Optional, Dict, Any
import logging
from urllib.parse import unquote
from datetime import datetime, timedelta
import time
import re
import json
import requests
from pathlib import Path as FilePath

from app.services.story_service import StoryService
from app.services.medium_stats_fetcher import MediumStatsFetcher
from app.services.app_status_service import AppStatusService
from app.services.monthly_storage_service import MonthlyStorageService
from app.models import StoryCreate, StoryUpdate, StoryResponse
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def normalize_url(url: str) -> str:
    """Normalize URL for comparison"""
    if not url:
        return url
    url = url.replace('https://', '').replace('http://', '')
    url = url.rstrip('/')
    return url.lower()


def safe_divide(numerator: float, denominator: float, default: float = 0) -> float:
    """Safely divide two numbers"""
    if denominator == 0:
        return default
    return round(numerator / denominator, 2)


def get_today_date():
    return datetime.now().strftime("%Y-%m-%d")


def write_fetch_log(data_dir: FilePath, operation: str, details: Dict[str, Any]):
    """Write fetch operation log to YYYY-MM.log file"""
    try:
        now = datetime.now()
        log_filename = f"{now.year}-{now.month:02d}.log"
        log_path = data_dir / "logs" / log_filename
        
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        log_entry = {
            "timestamp": now.isoformat(),
            "operation": operation,
            "details": details
        }
        
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        
        logger.info(f"Fetch log written to {log_path}")
        
        summary_path = data_dir / "logs" / f"{now.year}-{now.month:02d}_summary.txt"
        with open(summary_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Operation: {operation}\n")
            f.write(f"Timestamp: {now.isoformat()}\n")
            f.write(f"Files Processed: {details.get('files_processed', 0)}\n")
            f.write(f"Stories Updated: {details.get('updated', 0)}\n")
            f.write(f"Stories Added: {details.get('added', 0)}\n")
            f.write(f"Stories Reset: {details.get('reset', 0)}\n")
            f.write(f"Total Earnings: ${details.get('total_dollars', 0):.2f}\n")
            if details.get('files'):
                f.write(f"Source Files: {', '.join(details.get('files', []))}\n")
            f.write(f"{'='*80}\n")
        
    except Exception as e:
        logger.error(f"Failed to write fetch log: {e}")


def find_leaderboard_json_files(data_dir: FilePath, year: int, month: int) -> List[FilePath]:
    """Find all leaderboard JSON files for a given year and month"""
    found_files = []
    
    patterns = [
        f"leaderboard-{year}-{month:02d}.json",
        f"leaderboard-{year}-{month:02d}.-1.json",
        f"leaderboard-{year}-{month:02d}.-2.json",
        f"leaderboard-{year}-{month:02d}.-3.json",
        f"leaderboard-{year}-{month:02d}.-4.json",
        f"leaderboard-{year}-{month:02d}.-5.json",
        f"leaderboard-{year}-{month:02d}.1.json",
        f"leaderboard-{year}-{month:02d}.2.json",
        f"leaderboard-{year}-{month:02d}.3.json",
        f"leaderboard-{year}-{month:02d}.4.json",
        f"leaderboard-{year}-{month:02d}.5.json",
        f"leaderboard-{year}-{month:02d}*-part*.json",
        f"leaderboard-{year}-{month:02d}*.json",
    ]
    
    for pattern in patterns:
        for file_path in data_dir.glob(pattern):
            if file_path not in found_files and file_path.suffix == '.json':
                found_files.append(file_path)
                logger.info(f"Found leaderboard file: {file_path.name}")
    
    found_files.sort()
    return found_files


def parse_complete_leaderboard_json(file_path: FilePath) -> List[Dict[str, Any]]:
    """Parse a leaderboard JSON file and extract COMPLETE data"""
    stories_list = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list) and len(data) > 0:
            data_obj = data[0].get('data', {})
            user_result = data_obj.get('userResult', {})
        elif isinstance(data, dict):
            data_obj = data.get('data', {})
            user_result = data_obj.get('userResult', {})
        else:
            logger.warning(f"Unexpected JSON structure in {file_path}")
            return stories_list
        
        if user_result.get('__typename') == 'User':
            posts_connection = user_result.get('postsConnection', {})
            edges = posts_connection.get('edges', [])
            
            for edge in edges:
                node = edge.get('node', {})
                earnings = node.get('earnings', {})
                monthly_earnings = earnings.get('monthlyEarnings', {})
                
                nanos = monthly_earnings.get('nanos', 0)
                
                story_data = {
                    'title': node.get('title'),
                    'medium_url': node.get('mediumUrl'),
                    'first_published_at': node.get('firstPublishedAt'),
                    'reading_time': node.get('readingTime'),
                    'word_count': node.get('wordCount', 0),
                    'collection': node.get('collection'),
                    'nanos': nanos,
                    'currency': monthly_earnings.get('currencyCode', 'USD'),
                    'lifetime_nanos': earnings.get('lifetimeEarnings', {}).get('nanos', 0),
                    'source_file': file_path.name,
                    'tags': [],
                    'topics': [],
                    'subtitle': node.get('subtitle', ''),
                    'author': '',
                    'claps': 0,
                    'responses': 0,
                    'bookmarks': 0,
                    'view_count': 0
                }
                
                creator = node.get('creator', {})
                if creator:
                    story_data['author'] = creator.get('name', '')
                
                tags = node.get('tags', [])
                if tags:
                    story_data['tags'] = [tag.get('name') for tag in tags if tag.get('name')]
                
                topics = node.get('topics', [])
                if topics:
                    story_data['topics'] = [topic.get('name') for topic in topics if topic.get('name')]
                
                distribution = node.get('distribution', {})
                if distribution:
                    story_data['claps'] = distribution.get('totalClapCount', 0)
                    story_data['responses'] = distribution.get('totalResponseCount', 0)
                    story_data['bookmarks'] = distribution.get('totalBookmarkCount', 0)
                    story_data['view_count'] = distribution.get('totalViewCount', 0)
                
                stories_list.append(story_data)
                logger.info(f"  Found from {file_path.name}: {node.get('title')} - ${nanos/1000000000:.2f}")
    
    except Exception as e:
        logger.error(f"Error parsing {file_path}: {e}")
    
    return stories_list


# ============================================
# DEBUG ENDPOINTS (Must be FIRST)
# ============================================

@router.get("/debug/all")
async def debug_all():
    """Debug endpoint to list all stories"""
    try:
        stories = await StoryService.get_all_stories()
        return {
            "total": len(stories),
            "stories": [
                {
                    "key": s.key,
                    "name": s.name,
                    "medium_url": s.medium_url,
                    "status": s.status,
                    "medium_first_published": s.medium_first_published,
                    "leaderboard": s.leaderboard
                }
                for s in stories
            ]
        }
    except Exception as e:
        logger.error(f"Debug all error: {e}")
        return {"error": str(e)}


@router.get("/debug/urls")
async def debug_urls():
    """Debug endpoint to list all stories with Medium URLs"""
    try:
        stories = await StoryService.get_all_stories()
        urls_with_keys = [
            {
                "key": s.key,
                "name": s.name,
                "medium_url": s.medium_url,
                "medium_first_published": s.medium_first_published
            }
            for s in stories if s.medium_url
        ]
        return {
            "total": len(urls_with_keys),
            "urls": urls_with_keys
        }
    except Exception as e:
        logger.error(f"Debug URLs error: {e}")
        return {"error": str(e)}


@router.get("/debug/keys")
async def debug_keys():
    """Debug endpoint to list all story keys"""
    try:
        stories = await StoryService.get_all_stories()
        return {
            "total": len(stories),
            "keys": [s.key for s in stories]
        }
    except Exception as e:
        logger.error(f"Debug keys error: {e}")
        return {"error": str(e)}


@router.get("/debug/find/{search}")
async def find_story(search: str):
    """Find stories containing search term"""
    try:
        stories = await StoryService.get_all_stories()
        matches = [
            {"key": s.key, "name": s.name, "medium_url": s.medium_url}
            for s in stories if search.lower() in s.key.lower() or search.lower() in s.name.lower() or (s.medium_url and search.lower() in s.medium_url.lower())
        ]
        return {"search": search, "matches": matches}
    except Exception as e:
        logger.error(f"Find story error: {e}")
        return {"error": str(e)}


@router.get("/debug/list-all")
async def debug_list_all():
    """List all stories with their keys"""
    try:
        stories = await StoryService.get_all_stories()
        return {
            "total": len(stories),
            "stories": [
                {
                    "key": s.key,
                    "name": s.name,
                    "series": s.series,
                    "medium_url": s.medium_url
                }
                for s in stories
            ]
        }
    except Exception as e:
        logger.error(f"Debug list all error: {e}")
        return {"error": str(e)}


@router.get("/debug/monthly-file/{year}/{month}")
async def debug_monthly_file(year: int, month: int):
    """Debug endpoint to check monthly file contents"""
    try:
        monthly_data = await MonthlyStorageService.load_monthly_stats(year, month)
        stories_count = len(monthly_data.get("stories", {}))
        return {
            "year": year,
            "month": month,
            "file_exists": True,
            "story_count": stories_count,
            "stories": list(monthly_data.get("stories", {}).keys())[:20],
            "has_stories": stories_count > 0
        }
    except Exception as e:
        logger.error(f"Debug monthly file error: {e}")
        return {"error": str(e), "year": year, "month": month, "story_count": 0}


# ============================================
# LEADERBOARD MONTH MANAGEMENT ENDPOINTS
# ============================================

@router.get("/leaderboard-month")
async def get_leaderboard_month():
    """Get the currently loaded leaderboard month"""
    try:
        month = await AppStatusService.get_leaderboard_month()
        return {
            "leaderboard_month": month,
            "has_month": month is not None
        }
    except Exception as e:
        logger.error(f"Error getting leaderboard month: {e}")
        return {"error": str(e), "leaderboard_month": None}


@router.post("/leaderboard-month")
async def set_leaderboard_month_endpoint(year: int, month: int):
    """Set the currently loaded leaderboard month"""
    try:
        success = await AppStatusService.set_leaderboard_month(year, month)
        if success:
            month_name = datetime(year, month, 1).strftime("%B %Y")
            return {
                "message": f"Leaderboard month set to {month_name}",
                "leaderboard_month": f"{year}-{month:02d}",
                "success": True
            }
        else:
            return {"error": "Failed to set leaderboard month", "success": False}
    except Exception as e:
        logger.error(f"Error setting leaderboard month: {e}")
        return {"error": str(e), "success": False}


@router.delete("/leaderboard-month")
async def clear_leaderboard_month():
    """Clear the stored leaderboard month"""
    try:
        success = await AppStatusService.clear_leaderboard_month()
        return {"success": success, "message": "Leaderboard month cleared" if success else "Failed to clear"}
    except Exception as e:
        logger.error(f"Error clearing leaderboard month: {e}")
        return {"error": str(e), "success": False}


@router.get("/mode")
async def get_current_mode():
    """Get current view mode (dashboard or month)"""
    try:
        mode = await AppStatusService.get_current_mode()
        current_month = await AppStatusService.get_current_month()
        available_months = await MonthlyStorageService.get_available_months()
        
        return {
            "mode": mode,
            "current_month": current_month,
            "available_months": available_months
        }
    except Exception as e:
        logger.error(f"Error getting mode: {e}")
        return {"mode": "dashboard", "error": str(e)}


@router.post("/switch-to-dashboard")
async def switch_to_dashboard():
    """Switch back to dashboard mode"""
    try:
        await AppStatusService.set_current_mode("dashboard")
        return {"message": "Switched to dashboard mode", "mode": "dashboard"}
    except Exception as e:
        logger.error(f"Error switching to dashboard: {e}")
        return {"error": str(e)}


@router.post("/switch-month")
async def switch_month(year: int, month: int):
    """Switch to a specific month view"""
    try:
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
        return {"error": str(e)}


# ============================================
# MONTHLY STORIES ENDPOINTS (Must be before dynamic routes)
# ============================================

@router.get("/month/{year}/{month}")
async def get_stories_for_month(year: int, month: int):
    """Get stories for a specific month from monthly file only"""
    try:
        logger.info(f"Loading stories for month: {year}-{month:02d}")
        
        # Load monthly stats
        monthly_data = await MonthlyStorageService.load_monthly_stats(year, month)
        monthly_stories = monthly_data.get("stories", {})
        
        if not monthly_stories:
            logger.info(f"No stories found in monthly file for {year}-{month:02d}")
            return []
        
        logger.info(f"Found {len(monthly_stories)} stories in monthly file")
        
        # Get all permanent stories for metadata
        all_stories = await StoryService.get_all_stories()
        story_map = {s.key: s for s in all_stories}
        
        # Build response
        result = []
        for story_key, monthly_stats in monthly_stories.items():
            # Try to find in permanent storage
            story = story_map.get(story_key)
            
            if story:
                story_dict = story.dict()
                story_dict["monthly_stats"] = monthly_stats
                story_dict["current_month"] = f"{year}-{month:02d}"
                result.append(StoryResponse(**story_dict))
            else:
                # Create a minimal response for stories only in monthly file
                result.append({
                    "key": story_key,
                    "name": monthly_stats.get("title", story_key),
                    "folder": "Miscellaneous",  # Changed from "Leaderboard"
                    "series": "Miscellaneous",  # Changed from "Leaderboard"
                    "rel_path": story_key,
                    "status": "Published",
                    "created_date": datetime.now().strftime("%Y-%m-%d"),
                    "monthly_stats": monthly_stats,
                    "current_month": f"{year}-{month:02d}",
                    "reads": monthly_stats.get("reads", 0),
                    "view_count": monthly_stats.get("view_count", 0),
                    "claps": monthly_stats.get("claps", 0),
                    "leaderboard": monthly_stats.get("leaderboard", False),
                    "medium_url": monthly_stats.get("medium_url", ""),
                    "medium_title": monthly_stats.get("title", ""),
                    "lifetime_reads": 0,
                    "lifetime_views": 0,
                    "lifetime_claps": 0,
                    "presentation_count": 0
                })
        
        logger.info(f"Returning {len(result)} stories for {year}-{month:02d}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting stories for month: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-story-monthly-stats/{story_key:path}")
async def update_story_monthly_stats_endpoint(
    story_key: str = Path(..., description="The story key"),
    year: int = Query(...),
    month: int = Query(...),
    stats_data: Dict[str, Any] = None
):
    """Update a story's monthly stats for a specific month"""
    try:
        from urllib.parse import unquote
        decoded_key = unquote(story_key)
        if decoded_key.lower().endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        story = await StoryService.get_story(decoded_key)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        success = await MonthlyStorageService.update_story_monthly_stats(
            decoded_key, year, month, stats_data or {}, story.name
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update monthly stats")
        
        return {"message": "Monthly stats updated successfully", "story_key": decoded_key}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating story monthly stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/story-months/{story_key:path}")
async def get_story_available_months(story_key: str):
    """Get all months where a story has data"""
    try:
        from urllib.parse import unquote
        decoded_key = unquote(story_key)
        if decoded_key.lower().endswith('.md'):
            decoded_key = decoded_key[:-3]
        
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
async def ensure_story_in_month(story_key: str, year: int, month: int):
    """Ensure a story exists in a monthly file"""
    try:
        from urllib.parse import unquote
        decoded_key = unquote(story_key)
        if decoded_key.lower().endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        story = await StoryService.get_story(decoded_key)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        success = await MonthlyStorageService.ensure_story_in_month(
            decoded_key, year, month, story.name
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to ensure story in month")
        
        return {"message": "Story added to month", "story_key": decoded_key}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ensuring story in month: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# LEADERBOARD FILE MANAGEMENT ENDPOINTS
# ============================================

@router.get("/leaderboard-files")
async def list_leaderboard_files():
    """List all available leaderboard JSON files grouped by month"""
    try:
        data_dir = FilePath(settings.data_dir)
        
        if not data_dir.exists():
            return {"error": "Data directory not found", "files": []}
        
        leaderboard_files = {}
        
        for file_path in data_dir.glob("leaderboard-*.json"):
            filename = file_path.name
            match = re.search(r'leaderboard-(\d{4}-\d{2})', filename)
            
            if match:
                year_month = match.group(1)
                
                try:
                    year, month = year_month.split('-')
                    month_name = datetime(int(year), int(month), 1).strftime("%b-%Y")
                    
                    if year_month not in leaderboard_files:
                        leaderboard_files[year_month] = {
                            "year_month": year_month,
                            "display_name": month_name,
                            "year": int(year),
                            "month": int(month),
                            "files": []
                        }
                    
                    leaderboard_files[year_month]["files"].append({
                        "filename": filename,
                        "size": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                        "path": str(file_path)
                    })
                except Exception as e:
                    logger.warning(f"Error parsing filename {filename}: {e}")
        
        for year_month in leaderboard_files:
            leaderboard_files[year_month]["files"].sort(key=lambda x: x["filename"])
        
        sorted_files = sorted(leaderboard_files.values(), 
                            key=lambda x: x["year_month"], 
                            reverse=True)
        
        return {
            "leaderboard_files": sorted_files,
            "total_months": len(sorted_files),
            "data_dir": str(data_dir)
        }
        
    except Exception as e:
        logger.error(f"Error listing leaderboard files: {e}")
        return {"error": str(e), "files": []}


@router.get("/logs/{year_month}")
async def get_fetch_logs(year_month: str):
    """Get fetch operation logs for a specific year-month"""
    try:
        data_dir = FilePath(settings.data_dir)
        log_path = data_dir / "logs" / f"{year_month}.log"
        
        if not log_path.exists():
            return {"error": f"No log file found for {year_month}", "path": str(log_path)}
        
        logs = []
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        logs.append(json.loads(line))
                    except:
                        logs.append({"raw": line.strip()})
        
        return {
            "year_month": year_month,
            "log_file": str(log_path),
            "entries": logs,
            "total_entries": len(logs)
        }
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return {"error": str(e)}


@router.get("/logs")
async def list_log_files():
    """List all available fetch log files"""
    try:
        data_dir = FilePath(settings.data_dir)
        logs_dir = data_dir / "logs"
        
        if not logs_dir.exists():
            return {"logs_dir": str(logs_dir), "files": []}
        
        log_files = []
        for file_path in logs_dir.glob("*.log"):
            log_files.append({
                "filename": file_path.name,
                "size": file_path.stat().st_size,
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })
        
        summary_files = []
        for file_path in logs_dir.glob("*_summary.txt"):
            summary_files.append({
                "filename": file_path.name,
                "size": file_path.stat().st_size,
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })
        
        return {
            "logs_dir": str(logs_dir),
            "log_files": sorted(log_files, key=lambda x: x['filename'], reverse=True),
            "summary_files": sorted(summary_files, key=lambda x: x['filename'], reverse=True)
        }
    except Exception as e:
        logger.error(f"Error listing logs: {e}")
        return {"error": str(e)}


# ============================================
# MEDIUM STATS ENDPOINTS
# ============================================

@router.get("/stats-by-url")
async def get_stats_dashboard_by_url(medium_url: str):
    """Get stats dashboard for a story using its Medium URL"""
    try:
        if not medium_url:
            return {"error": "Medium URL is required"}
        
        decoded_url = unquote(medium_url)
        all_stories = await StoryService.get_all_stories()
        
        story = None
        normalized_query = normalize_url(decoded_url)
        
        for s in all_stories:
            if s.medium_url:
                if normalize_url(s.medium_url) == normalized_query:
                    story = s
                    break
        
        if not story:
            available = [s.medium_url for s in all_stories if s.medium_url]
            return {
                "error": "Story not found",
                "your_url": decoded_url,
                "available_urls": available[:5] if available else []
            }
        
        # Get current mode to determine which month's stats to show
        mode = await AppStatusService.get_current_mode()
        if mode == "month":
            current_month = await AppStatusService.get_current_month()
            year = current_month["year"]
            month = current_month["month"]
        else:
            now = datetime.now()
            year = now.year
            month = now.month
        
        monthly_stats = await MonthlyStorageService.get_story_monthly_stats(
            story.key, year, month
        ) or {}
        
        return {
            "story_key": story.key,
            "story_name": story.name,
            "medium_url": story.medium_url,
            "last_stats_update": monthly_stats.get("last_stats_update"),
            "medium_first_published": story.medium_first_published,
            "medium_publication": story.medium_publication,
            "current_month": {
                "reads": monthly_stats.get("reads", 0),
                "claps": monthly_stats.get("claps", 0),
                "views": monthly_stats.get("view_count", 0),
                "responses": monthly_stats.get("responses", 0),
                "member_reads": monthly_stats.get("medium_member_reads", 0),
                "member_views": monthly_stats.get("medium_member_views", 0),
                "nonmember_reads": monthly_stats.get("medium_nonmember_reads", 0),
                "nonmember_views": monthly_stats.get("medium_nonmember_views", 0),
                "read_ratio": monthly_stats.get("medium_read_ratio", 0),
                "member_read_percentage": monthly_stats.get("medium_member_read_percentage", 0),
                "new_followers": monthly_stats.get("medium_new_followers", 0)
            },
            "lifetime": {
                "reads": 0,
                "views": 0,
                "presentation_count": 0
            },
            "content": {
                "word_count": story.word_count or 0,
                "reading_time": story.medium_reading_time or story.read_time or 0
            },
            "metadata": {
                "title": story.medium_title or story.name,
                "first_published": story.medium_first_published or story.created_date,
                "last_updated": story.last_updated,
                "publication": story.medium_publication or ""
            }
        }
        
    except Exception as e:
        logger.error(f"Get stats dashboard error: {e}")
        return {"error": str(e)}


@router.post("/fetch-lifetime-stats/{story_key:path}")
async def fetch_complete_story_stats(
    story_key: str = Path(..., description="The story key"),
    year: Optional[int] = None,
    month: Optional[int] = None
):
    """Fetch stats for a single story for a specific month"""
    try:
        decoded_key = unquote(story_key)
        if decoded_key.lower().endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        # Determine which month to fetch stats for
        if year is None or month is None:
            mode = await AppStatusService.get_current_mode()
            if mode == "month":
                current = await AppStatusService.get_current_month()
                year = current["year"]
                month = current["month"]
            else:
                now = datetime.now()
                year = now.year
                month = now.month
        
        logger.info(f"=" * 60)
        logger.info(f"FETCHING STATS FOR: {decoded_key} for {year}-{month:02d}")
        logger.info(f"=" * 60)
        
        story = await StoryService.get_story(decoded_key)
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found: {decoded_key}")
        
        if not story.medium_url:
            raise HTTPException(status_code=400, detail="Story has no Medium URL")
        
        logger.info(f"📝 Medium URL: {story.medium_url}")
        
        fetcher = MediumStatsFetcher()
        
        if not fetcher.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Fetch stats for the specific month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        month_stats = await fetcher.fetch_stats_for_date_range(story.medium_url, start_date, end_date)
        
        if month_stats:
            totals = month_stats.get('totals', {})
            
            # Update monthly stats in monthly file
            await MonthlyStorageService.update_story_monthly_stats(
                decoded_key, year, month, {
                    "reads": totals.get('total_reads', 0),
                    "view_count": totals.get('total_views', 0),
                    "claps": totals.get('claps', 0),
                    "responses": totals.get('replies', 0),
                    "medium_member_reads": totals.get('member_reads', 0),
                    "medium_member_views": totals.get('member_views', 0),
                    "medium_nonmember_reads": totals.get('nonmember_reads', 0),
                    "medium_nonmember_views": totals.get('nonmember_views', 0),
                    "medium_read_ratio": totals.get('read_ratio', 0),
                    "medium_member_read_percentage": totals.get('member_read_percentage', 0),
                    "medium_new_followers": totals.get('new_followers', 0),
                    "medium_highlights": totals.get('highlights', 0),
                }, story.name
            )
            
            month_name = datetime(year, month, 1).strftime("%B %Y")
            
            return {
                "message": f"Stats fetched successfully for {month_name}",
                "stats_month": f"{year}-{month:02d}",
                "stats_month_display": month_name,
                "stats": {
                    "story_key": decoded_key,
                    "story_name": story.name,
                    "medium_url": story.medium_url,
                    "medium_first_published": story.medium_first_published,
                    "last_stats_update": datetime.now().isoformat(),
                    "current_month": {
                        "reads": totals.get('total_reads', 0),
                        "claps": totals.get('claps', 0),
                        "views": totals.get('total_views', 0),
                        "responses": totals.get('replies', 0),
                        "member_reads": totals.get('member_reads', 0),
                        "member_views": totals.get('member_views', 0),
                        "read_ratio": totals.get('read_ratio', 0)
                    },
                    "lifetime": {
                        "reads": 0,
                        "claps": 0,
                        "views": 0,
                        "presentation_count": 0
                    },
                    "content": {
                        "word_count": month_stats.get('word_count', 0),
                        "reading_time": month_stats.get('reading_time', 0)
                    },
                    "metadata": {
                        "title": month_stats.get('title'),
                        "first_published": month_stats.get('first_published'),
                        "last_updated": month_stats.get('last_updated')
                    }
                }
            }
        else:
            return {"message": "Could not fetch stats", "error": "No data returned"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fetch stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# LEADERBOARD FETCH ENDPOINTS
# ============================================

@router.post("/fetch-leaderboard-for-month")
async def fetch_leaderboard_for_month(request: Request):
    """Fetch leaderboard data for a specific month/year from JSON files"""
    start_time = datetime.now()
    
    try:
        body = await request.json()
        year = body.get('year')
        month = body.get('month')
        
        if not year or not month:
            return {"error": "Year and month are required"}
        
        logger.info("=" * 60)
        logger.info(f"FETCHING LEADERBOARD FOR {year}-{month:02d}")
        logger.info("=" * 60)
        
        data_dir = FilePath(settings.data_dir)
        json_files = find_leaderboard_json_files(data_dir, year, month)
        
        if not json_files:
            error_msg = f"No leaderboard files found for {year}-{month:02d}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "year": year,
                "month": month,
                "data_dir": str(data_dir)
            }
        
        logger.info(f"Found {len(json_files)} leaderboard file(s): {[f.name for f in json_files]}")
        
        all_earnings = []
        for json_file in json_files:
            earnings = parse_complete_leaderboard_json(json_file)
            all_earnings.extend(earnings)
            logger.info(f"  Found {len(earnings)} stories with data in {json_file.name}")
        
        if not all_earnings:
            return {
                "message": "No stories found in any JSON file", 
                "updated": 0, 
                "added": 0, 
                "files_processed": len(json_files)
            }
        
        unique_earnings = {}
        for earning in all_earnings:
            url = earning.get('medium_url', '').rstrip('/')
            if not url:
                continue
            if url not in unique_earnings:
                unique_earnings[url] = earning
        
        earnings_list = list(unique_earnings.values())
        logger.info(f"Total unique stories after deduplication: {len(earnings_list)}")
        
        # Get all existing stories
        all_stories = await StoryService.get_all_stories()
        logger.info(f"Found {len(all_stories)} existing stories in database")
        
        def normalize_title(title: str) -> str:
            if not title:
                return ""
            normalized = title.lower().strip()
            if normalized.endswith('.md'):
                normalized = normalized[:-3]
            normalized = re.sub(r'[—–‐‑‒−]', '-', normalized)
            normalized = re.sub(r'\s+', ' ', normalized)
            return normalized.strip()
        
        # Create a map of existing stories by normalized title
        story_map = {}
        for story in all_stories:
            if story.name:
                normalized = normalize_title(story.name)
                story_map[normalized] = story
        
        # Load or create monthly file
        monthly_data = await MonthlyStorageService.load_monthly_stats(year, month)
        
        updated_count = 0
        added_count = 0
        
        for earning in earnings_list:
            medium_url = earning.get('medium_url')
            title = earning.get('title')
            first_published_at = earning.get('first_published_at')
            reading_time = earning.get('reading_time', 0)
            word_count = earning.get('word_count', 0)
            collection = earning.get('collection', {})
            publication_slug = collection.get('slug') if collection else None
            publication_name = collection.get('name') if collection else None
            source_file = earning.get('source_file', 'unknown')
            
            tags = earning.get('tags', [])
            topics = earning.get('topics', [])
            subtitle = earning.get('subtitle', '')
            author = earning.get('author', '')
            claps = earning.get('claps', 0)
            responses = earning.get('responses', 0)
            bookmarks = earning.get('bookmarks', 0)
            view_count = earning.get('view_count', 0)
            
            if not medium_url or not title:
                continue
            
            normalized_json_title = normalize_title(title)
            existing_story = story_map.get(normalized_json_title)
            
            reading_time_int = int(round(reading_time)) if reading_time else 0
            
            publish_date = None
            if first_published_at:
                try:
                    publish_date = datetime.fromtimestamp(first_published_at/1000).strftime("%Y-%m-%d")
                except:
                    publish_date = datetime.now().strftime("%Y-%m-%d")
            else:
                publish_date = datetime.now().strftime("%Y-%m-%d")
            
            # Create a story key
            story_key = re.sub(r'[^\w\s-]', '', title).lower()
            story_key = re.sub(r'[\s]+', '-', story_key).strip('-')
            story_key = story_key[:100]
            
            if existing_story:
                story_key = existing_story.key
                # UPDATE existing story: set status to Published and update metadata
                await StoryService.update_story(existing_story.key, StoryUpdate(
                    status="Published",
                    medium_url=medium_url,
                    medium_title=title,
                    medium_subtitle=subtitle,
                    medium_author=author,
                    medium_publication=publication_slug or publication_name,
                    medium_reading_time=reading_time_int,
                    word_count=word_count,
                    medium_tags=tags[:20] if tags else [],
                    medium_topics=topics[:20] if topics else [],
                    published_date=publish_date,
                    medium_first_published=datetime.fromtimestamp(first_published_at/1000).isoformat() if first_published_at else None
                ))
                updated_count += 1
                logger.info(f"✅ Updated existing story metadata and status to Published: {title}")
            else:
                # Create NEW story with basic metadata
                current_date = datetime.now().strftime("%Y-%m-%d")
                safe_title = title[:200]
                
                new_story = await StoryService.create_story(StoryCreate(
                    name=safe_title,
                    folder="Miscellaneous",
                    series="Miscellaneous",
                    tags=tags[:10] if tags else [],
                    read_time=reading_time_int if reading_time_int > 0 else None,
                    created_date=current_date,
                    notes=f"Auto-created from leaderboard JSON data for {year}-{month:02d} (source: {source_file})",
                    medium_url=medium_url,
                    medium_first_published=datetime.fromtimestamp(first_published_at/1000).isoformat() if first_published_at else None,
                    medium_publication=publication_slug,
                    medium_reading_time=reading_time_int
                ))
                story_key = new_story.key
                
                # EXPLICITLY UPDATE status to Published and add metadata
                await StoryService.update_story(story_key, StoryUpdate(
                    status="Published",
                    published_date=publish_date,
                    medium_title=title,
                    medium_subtitle=subtitle,
                    medium_author=author,
                    medium_publication=publication_slug or publication_name,
                    medium_reading_time=reading_time_int,
                    word_count=word_count,
                    medium_tags=tags[:20] if tags else [],
                    medium_topics=topics[:20] if topics else [],
                    claps=claps,
                    responses=responses,
                    bookmarks=bookmarks,
                    view_count=view_count
                ))
                added_count += 1
                logger.info(f"✅ Created new story with status Published: {title}")
            
            # Update monthly file with leaderboard=true
            monthly_data["stories"][story_key] = {
                "title": title,
                "reads": view_count,
                "view_count": view_count,
                "claps": claps,
                "responses": responses,
                "medium_member_reads": 0,
                "medium_member_views": 0,
                "medium_nonmember_reads": 0,
                "medium_nonmember_views": 0,
                "medium_read_ratio": 0,
                "medium_member_read_percentage": 0,
                "medium_new_followers": 0,
                "medium_highlights": 0,
                "leaderboard": True,
                "leaderboard_nanos": earning.get('nanos', 0),
                "medium_url": medium_url,
                "medium_title": title,
                "medium_subtitle": subtitle,
                "medium_author": author,
                "medium_publication": publication_slug or publication_name,
                "medium_reading_time": reading_time_int,
                "word_count": word_count,
                "medium_tags": tags[:20] if tags else [],
                "medium_topics": topics[:20] if topics else [],
                "published_date": publish_date,
                "first_published_at": first_published_at
            }
        
        # Save monthly file
        await MonthlyStorageService.save_monthly_stats(year, month, monthly_data)
        
        # After successful fetch, save the month and switch to month mode
        await AppStatusService.set_leaderboard_month(year, month)
        await AppStatusService.set_current_mode("month")
        await AppStatusService.set_current_month(year, month)
        
        end_time = datetime.now()
        processing_time_ms = (end_time - start_time).total_seconds() * 1000
        month_name = datetime(year, month, 1).strftime("%B %Y")
        
        log_details = {
            "year": year,
            "month": month,
            "processing_time_ms": processing_time_ms,
            "files_processed": len(json_files),
            "files": [f.name for f in json_files],
            "updated": updated_count,
            "added": added_count,
            "total_stories_in_month": len(monthly_data.get("stories", {})),
            "total_nanos": 0
        }
        write_fetch_log(data_dir, f"FETCH_LEADERBOARD_{year}-{month:02d}", log_details)
        
        return {
            "message": f"Leaderboard fetched for {month_name}",
            "processing_time_ms": processing_time_ms,
            "year": year,
            "month": month,
            "display_name": month_name,
            "files_processed": len(json_files),
            "updated": updated_count,
            "added": added_count,
            "total_stories": len(monthly_data.get("stories", {})),
            "mode": "month"
        }
        
    except Exception as e:
        logger.error(f"Fetch leaderboard error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
    
@router.post("/import-all-leaderboard")
async def import_all_leaderboard():
    """One-time bulk import from all leaderboard JSON files"""
    try:
        data_dir = FilePath(settings.data_dir)
        leaderboard_files = list(data_dir.glob("leaderboard-*.json"))
        
        if not leaderboard_files:
            return {"error": "No leaderboard files found", "files_processed": 0}
        
        def normalize_title(title: str) -> str:
            if not title:
                return ""
            normalized = title.lower().strip()
            if normalized.endswith('.md'):
                normalized = normalized[:-3]
            normalized = re.sub(r'[—–‐‑‒−]', '-', normalized)
            normalized = re.sub(r'\s+', ' ', normalized)
            normalized = re.sub(r'[^\w\s-]', '', normalized)
            return normalized.strip()
        
        # Group files by month
        months_data = {}
        for file_path in leaderboard_files:
            match = re.search(r'leaderboard-(\d{4}-\d{2})', file_path.name)
            if match:
                year_month = match.group(1)
                if year_month not in months_data:
                    months_data[year_month] = []
                months_data[year_month].append(file_path)
        
        total_stories = 0
        months_imported = 0
        
        # Get all existing stories once for matching
        all_existing_stories = await StoryService.get_all_stories()
        
        # Create a map of normalized titles to existing stories
        existing_story_map = {}
        for story in all_existing_stories:
            if story.name:
                normalized = normalize_title(story.name)
                existing_story_map[normalized] = story
        
        for year_month, files in months_data.items():
            year, month = map(int, year_month.split('-'))
            all_earnings = []
            
            for file_path in files:
                earnings = parse_complete_leaderboard_json(file_path)
                all_earnings.extend(earnings)
            
            # Deduplicate by URL and title
            unique_earnings = {}
            for earning in all_earnings:
                url = earning.get('medium_url', '').rstrip('/')
                title = earning.get('title', '')
                if title:
                    normalized_title = normalize_title(title)
                    if normalized_title not in unique_earnings:
                        unique_earnings[normalized_title] = earning
            
            # Load or create monthly file
            monthly_data = await MonthlyStorageService.load_monthly_stats(year, month)
            
            for normalized_title, earning in unique_earnings.items():
                title = earning.get('title', '')
                medium_url = earning.get('medium_url', '')
                
                if not title:
                    continue
                
                # Try to find existing story by normalized title
                existing_story = existing_story_map.get(normalized_title)
                
                # Also try to find by URL if title match fails
                if not existing_story and medium_url:
                    for story in all_existing_stories:
                        if story.medium_url and story.medium_url.rstrip('/') == medium_url.rstrip('/'):
                            existing_story = story
                            break
                
                # Create a story key from title
                story_key = re.sub(r'[^\w\s-]', '', title).lower()
                story_key = re.sub(r'[\s]+', '-', story_key).strip('-')
                story_key = story_key[:100]
                
                if existing_story:
                    story_key = existing_story.key
                    # UPDATE existing story: set status to Published and update metadata
                    await StoryService.update_story(existing_story.key, StoryUpdate(
                        status="Published",
                        medium_url=medium_url,
                        medium_title=title,
                        medium_author=earning.get('author', ''),
                        medium_publication=earning.get('collection', {}).get('slug') if earning.get('collection') else None,
                        medium_reading_time=int(round(earning.get('reading_time', 0))),
                        word_count=earning.get('word_count', 0),
                        medium_tags=earning.get('tags', [])[:20],
                        medium_topics=earning.get('topics', [])[:20],
                        published_date=datetime.fromtimestamp(earning.get('first_published_at', 0)/1000).strftime("%Y-%m-%d") if earning.get('first_published_at') else None,
                        medium_first_published=datetime.fromtimestamp(earning.get('first_published_at', 0)/1000).isoformat() if earning.get('first_published_at') else None
                    ))
                    logger.info(f"✅ Updated existing story metadata and status to Published: '{title}'")
                else:
                    # Create NEW story with basic metadata
                    current_date = datetime.now().strftime("%Y-%m-%d")
                    safe_title = title[:200]
                    
                    new_story = await StoryService.create_story(StoryCreate(
                        name=safe_title,
                        folder="Miscellaneous",
                        series="Miscellaneous",
                        tags=earning.get('tags', [])[:10],
                        read_time=int(round(earning.get('reading_time', 0))),
                        created_date=current_date,
                        notes=f"Auto-created from leaderboard JSON data for {year_month}",
                        medium_url=medium_url,
                        medium_first_published=datetime.fromtimestamp(earning.get('first_published_at', 0)/1000).isoformat() if earning.get('first_published_at') else None,
                        medium_publication=earning.get('collection', {}).get('slug') if earning.get('collection') else None,
                        medium_reading_time=int(round(earning.get('reading_time', 0)))
                    ))
                    story_key = new_story.key
                    
                    # EXPLICITLY UPDATE status to Published and add metadata
                    await StoryService.update_story(story_key, StoryUpdate(
                        status="Published",
                        published_date=datetime.fromtimestamp(earning.get('first_published_at', 0)/1000).strftime("%Y-%m-%d") if earning.get('first_published_at') else current_date,
                        medium_title=title,
                        medium_author=earning.get('author', ''),
                        medium_publication=earning.get('collection', {}).get('slug') if earning.get('collection') else None,
                        medium_reading_time=int(round(earning.get('reading_time', 0))),
                        word_count=earning.get('word_count', 0),
                        medium_tags=earning.get('tags', [])[:20],
                        medium_topics=earning.get('topics', [])[:20]
                    ))
                    
                    existing_story_map[normalized_title] = new_story
                    logger.info(f"✅ Created new story with status Published: '{title}'")
                
                # Save to monthly file with leaderboard=true
                monthly_data["stories"][story_key] = {
                    "title": title,
                    "reads": earning.get('view_count', 0),
                    "view_count": earning.get('view_count', 0),
                    "claps": earning.get('claps', 0),
                    "responses": earning.get('responses', 0),
                    "medium_member_reads": 0,
                    "medium_member_views": 0,
                    "medium_nonmember_reads": 0,
                    "medium_nonmember_views": 0,
                    "medium_read_ratio": 0,
                    "medium_member_read_percentage": 0,
                    "medium_new_followers": 0,
                    "medium_highlights": 0,
                    "leaderboard": True,
                    "leaderboard_nanos": earning.get('nanos', 0),
                    "medium_url": medium_url,
                    "medium_title": title,
                    "medium_author": earning.get('author', ''),
                    "medium_publication": earning.get('collection', {}).get('slug') if earning.get('collection') else None,
                    "medium_reading_time": int(round(earning.get('reading_time', 0))),
                    "word_count": earning.get('word_count', 0),
                    "medium_tags": earning.get('tags', [])[:20],
                    "medium_topics": earning.get('topics', [])[:20],
                    "published_date": datetime.fromtimestamp(earning.get('first_published_at', 0)/1000).strftime("%Y-%m-%d") if earning.get('first_published_at') else None
                }
                total_stories += 1
            
            await MonthlyStorageService.save_monthly_stats(year, month, monthly_data)
            months_imported += 1
            logger.info(f"Imported {len(unique_earnings)} stories for {year_month} with leaderboard=true and status=Published")
        
        return {
            "message": f"Successfully imported {months_imported} months",
            "files_processed": len(leaderboard_files),
            "months_imported": months_imported,
            "total_stories": total_stories
        }
        
    except Exception as e:
        logger.error(f"Import leaderboard error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
    
@router.post("/update-leaderboard-stats")
async def update_leaderboard_stats(year: Optional[int] = None, month: Optional[int] = None):
    """Fetch stats for stories with leaderboard flag = true for a specific month"""
    try:
        # Determine which month to fetch stats for
        if year is None or month is None:
            mode = await AppStatusService.get_current_mode()
            if mode == "month":
                current = await AppStatusService.get_current_month()
                year = current["year"]
                month = current["month"]
                logger.info(f"Month mode: using selected month {year}-{month:02d}")
            else:
                now = datetime.now()
                year = now.year
                month = now.month
                logger.info(f"Dashboard mode: using current month {year}-{month:02d}")
        
        logger.info("=" * 60)
        logger.info(f"UPDATING LEADERBOARD STORIES FOR {year}-{month:02d}")
        logger.info("=" * 60)
        
        # Load monthly stats to get stories with leaderboard=true
        monthly_data = await MonthlyStorageService.load_monthly_stats(year, month)
        monthly_stories = monthly_data.get("stories", {})
        
        # Get stories that have leaderboard=true in this month
        leaderboard_stories_keys = [
            key for key, data in monthly_stories.items() 
            if data.get("leaderboard", False)
        ]
        
        if not leaderboard_stories_keys:
            return {"message": "No leaderboard stories found for this month", "updated": 0, "total": 0}
        
        logger.info(f"Found {len(leaderboard_stories_keys)} leaderboard stories for {year}-{month:02d}")
        
        # Get full story objects
        all_stories = await StoryService.get_all_stories()
        story_map = {s.key: s for s in all_stories}
        
        leaderboard_stories = [story_map[key] for key in leaderboard_stories_keys if key in story_map]
        
        if not leaderboard_stories:
            return {"message": "No leaderboard stories found in permanent storage", "updated": 0, "total": 0}
        
        fetcher = MediumStatsFetcher()
        
        if not fetcher.is_authenticated():
            logger.error("Not authenticated - no valid cookies found")
            return {"error": "Not authenticated. Please log into Medium in your browser, then close browser and try again."}
        
        results = {
            'total': len(leaderboard_stories),
            'updated': 0,
            'failed': 0,
            'details': [],
            'stats_month': f"{year}-{month:02d}"
        }
        
        # Date range for the selected month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        for i, story in enumerate(leaderboard_stories):
            try:
                logger.info(f"\n📊 ({i+1}/{len(leaderboard_stories)}): {story.name}")
                
                if i > 0:
                    logger.info("   Waiting 0.5 seconds to avoid rate limiting...")
                    time.sleep(0.5)
                
                month_stats = await fetcher.fetch_stats_for_date_range(story.medium_url, start_date, end_date)
                
                if month_stats:
                    totals = month_stats.get('totals', {})
                    
                    # Update monthly stats
                    await MonthlyStorageService.update_story_monthly_stats(
                        story.key, year, month, {
                            "reads": totals.get('total_reads', 0),
                            "view_count": totals.get('total_views', 0),
                            "claps": totals.get('claps', 0),
                            "responses": totals.get('replies', 0),
                            "medium_member_reads": totals.get('member_reads', 0),
                            "medium_member_views": totals.get('member_views', 0),
                            "medium_nonmember_reads": totals.get('nonmember_reads', 0),
                            "medium_nonmember_views": totals.get('nonmember_views', 0),
                            "medium_read_ratio": totals.get('read_ratio', 0),
                            "medium_member_read_percentage": totals.get('member_read_percentage', 0),
                            "medium_new_followers": totals.get('new_followers', 0),
                            "medium_highlights": totals.get('highlights', 0),
                        }, story.name
                    )
                    
                    results['updated'] += 1
                    results['details'].append({
                        'key': story.key,
                        'name': story.name,
                        'success': True,
                        'reads': totals.get('total_reads', 0),
                        'views': totals.get('total_views', 0)
                    })
                    
                    logger.info(f"   ✅ Updated for {year}-{month:02d}: {totals.get('total_reads', 0)} reads, {totals.get('total_views', 0)} views")
                else:
                    results['failed'] += 1
                    results['details'].append({
                        'key': story.key,
                        'name': story.name,
                        'success': False
                    })
                    logger.warning(f"   ❌ Failed to fetch stats for {year}-{month:02d}")
                    
            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'key': story.key,
                    'name': story.name,
                    'success': False,
                    'error': str(e)
                })
                logger.error(f"   ❌ Error: {e}")
        
        month_name = datetime(year, month, 1).strftime("%B %Y")
        logger.info(f"\n{'='*60}")
        logger.info(f"COMPLETE: {results['updated']}/{results['total']} stories updated for {month_name}")
        logger.info(f"{'='*60}")
        
        return {
            "message": f"Updated {results['updated']} of {results['total']} leaderboard stories for {month_name}",
            "results": results,
            "stats_month": f"{year}-{month:02d}",
            "display_name": month_name
        }

    except Exception as e:
        logger.error(f"Update leaderboard stats error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-leaderboard")
async def clear_leaderboard():
    """Clear all leaderboard flags (from monthly files)"""
    try:
        months = await MonthlyStorageService.get_available_months()
        cleared_count = 0
        
        for month_info in months:
            data = await MonthlyStorageService.load_monthly_stats(month_info["year"], month_info["month"])
            changed = False
            
            for story_key, story_data in data.get("stories", {}).items():
                if story_data.get("leaderboard", False):
                    story_data["leaderboard"] = False
                    changed = True
            
            if changed:
                await MonthlyStorageService.save_monthly_stats(month_info["year"], month_info["month"], data)
                cleared_count += 1
        
        return {"message": f"Cleared leaderboard flags from {cleared_count} months"}
    except Exception as e:
        logger.error(f"Clear leaderboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# CORE CRUD ENDPOINTS (Must be LAST)
# ============================================

@router.post("/sync")
async def sync_stories():
    """Sync with filesystem"""
    try:
        result = await StoryService.sync_with_filesystem()
        return {
            "message": "Sync completed",
            "added": result.get("added", 0),
            "updated": result.get("updated", 0),
            "total_stories": result.get("total", 0)
        }
    except Exception as e:
        logger.error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[StoryResponse])
async def list_stories(
    status: Optional[str] = Query(None),
    series: Optional[str] = Query(None),
    folder: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None)
):
    """List all stories with optional filters - can also filter by month"""
    try:
        stories = await StoryService.get_all_stories()
        
        if status:
            stories = [s for s in stories if s.status == status]
        if series:
            stories = [s for s in stories if s.series == series]
        if folder:
            stories = [s for s in stories if s.folder == folder]
        
        if year and month:
            monthly_data = await MonthlyStorageService.load_monthly_stats(year, month)
            monthly_stories = monthly_data.get("stories", {})
            
            result = []
            for story in stories:
                story_dict = story.dict()
                monthly_stats = monthly_stories.get(story.key, {})
                story_dict["monthly_stats"] = monthly_stats
                result.append(StoryResponse(**story_dict))
            return result
        
        return stories
        
    except Exception as e:
        logger.error(f"List stories error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=StoryResponse, status_code=201)
async def create_story(story_data: StoryCreate):
    """Create a new story"""
    try:
        return await StoryService.create_story(story_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{story_key:path}", response_model=StoryResponse)
async def update_story(
    story_key: str = Path(..., description="The story key"),
    update_data: StoryUpdate = None
):
    """Update a story"""
    decoded_key = unquote(story_key)
    if decoded_key.lower().endswith('.md'):
        decoded_key = decoded_key[:-3]
    if update_data is None:
        update_data = StoryUpdate()
    story = await StoryService.update_story(decoded_key, update_data)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.post("/{story_key:path}/publish", response_model=StoryResponse)
async def publish_story(
    story_key: str = Path(..., description="The story key"),
    medium_url: Optional[str] = None
):
    """Mark a story as published"""
    decoded_key = unquote(story_key)
    if decoded_key.lower().endswith('.md'):
        decoded_key = decoded_key[:-3]
    story = await StoryService.publish_story(decoded_key, medium_url)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.delete("/{story_key:path}")
async def delete_story(story_key: str = Path(..., description="The story key")):
    """Delete a story"""
    decoded_key = unquote(story_key)
    if decoded_key.lower().endswith('.md'):
        decoded_key = decoded_key[:-3]
    deleted = await StoryService.delete_story(decoded_key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Story not found")
    return {"message": "Story deleted"}


@router.get("/{story_key:path}", response_model=StoryResponse)
async def get_story(story_key: str = Path(..., description="The story key")):
    """Get a single story"""
    decoded_key = unquote(story_key)
    if decoded_key.lower().endswith('.md'):
        decoded_key = decoded_key[:-3]
    
    story = await StoryService.get_story(decoded_key)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story

@router.get("/leaderboard-status")
async def get_leaderboard_status():
    """Get leaderboard status for all stories (True if ever been on leaderboard in any month)"""
    try:
        from app.services.monthly_storage_service import MonthlyStorageService
        
        available_months = await MonthlyStorageService.get_available_months()
        
        leaderboard_stories = set()
        story_leaderboard_months = {}
        
        for month_info in available_months:
            monthly_data = await MonthlyStorageService.load_monthly_stats(
                month_info["year"], month_info["month"]
            )
            monthly_stories = monthly_data.get("stories", {})
            
            for story_key, story_data in monthly_stories.items():
                if story_data.get("leaderboard", False):
                    leaderboard_stories.add(story_key)
                    if story_key not in story_leaderboard_months:
                        story_leaderboard_months[story_key] = []
                    story_leaderboard_months[story_key].append({
                        "year": month_info["year"],
                        "month": month_info["month"],
                        "display": month_info["display"]
                    })
        
        return {
            "leaderboard_stories": list(leaderboard_stories),
            "story_months": story_leaderboard_months,
            "total": len(leaderboard_stories)
        }
    except Exception as e:
        logger.error(f"Error getting leaderboard status: {e}")
        return {"leaderboard_stories": [], "story_months": {}, "total": 0}