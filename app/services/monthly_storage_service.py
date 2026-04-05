"""
Monthly Storage Service - Manages stories-YYYY-MM.json files for monthly statistics
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from config import settings

logger = logging.getLogger(__name__)


class MonthlyStorageService:
    """Service to manage monthly statistics storage"""
    
    @staticmethod
    def get_monthly_stats_path(year: int, month: int) -> Path:
        """Get path to stories-YYYY-MM.json"""
        data_dir = Path(settings.data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        month_str = f"{year}-{month:02d}"
        return data_dir / f"stories-{month_str}.json"
    
    @staticmethod
    async def get_available_months() -> List[Dict[str, Any]]:
        """Scan data directory for stories-YYYY-MM.json files"""
        data_dir = Path(settings.data_dir)
        if not data_dir.exists():
            return []
        
        months = []
        for file_path in data_dir.glob("stories-*.json"):
            # Extract YYYY-MM from filename
            filename = file_path.stem  # stories-2026-04
            if filename.startswith("stories-"):
                month_str = filename.replace("stories-", "")
                if len(month_str) == 7 and month_str[4] == '-':
                    try:
                        year, month = month_str.split('-')
                        months.append({
                            "year": int(year),
                            "month": int(month),
                            "display": datetime(int(year), int(month), 1).strftime("%b %Y"),
                            "file_path": str(file_path),
                            "exists": True
                        })
                    except:
                        pass
        
        # Sort by year-month descending (newest first)
        months.sort(key=lambda x: (x["year"], x["month"]), reverse=True)
        return months
    
    @staticmethod
    async def load_monthly_stats(year: int, month: int) -> Dict[str, Any]:
        """Load monthly stats for a specific month"""
        file_path = MonthlyStorageService.get_monthly_stats_path(year, month)
        
        default_data = {
            "month": f"{year}-{month:02d}",
            "last_updated": datetime.now().isoformat(),
            "stories": {}
        }
        
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Ensure required fields exist
                    if "stories" not in data:
                        data["stories"] = {}
                    if "month" not in data:
                        data["month"] = f"{year}-{month:02d}"
                    return data
            except Exception as e:
                logger.error(f"Error loading monthly stats for {year}-{month:02d}: {e}")
                return default_data
        
        return default_data
    
    @staticmethod
    async def save_monthly_stats(year: int, month: int, data: Dict[str, Any]) -> bool:
        """Save monthly stats for a specific month"""
        try:
            file_path = MonthlyStorageService.get_monthly_stats_path(year, month)
            data["last_updated"] = datetime.now().isoformat()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved monthly stats for {year}-{month:02d}")
            return True
        except Exception as e:
            logger.error(f"Error saving monthly stats for {year}-{month:02d}: {e}")
            return False
    
    @staticmethod
    async def get_story_monthly_stats(
        story_key: str, 
        year: int, 
        month: int
    ) -> Optional[Dict[str, Any]]:
        """Get a single story's stats for a specific month"""
        data = await MonthlyStorageService.load_monthly_stats(year, month)
        return data["stories"].get(story_key)
    
    @staticmethod
    async def update_story_monthly_stats(
        story_key: str,
        year: int,
        month: int,
        stats_data: Dict[str, Any],
        title: str = None
    ) -> bool:
        """Update a single story's stats for a specific month"""
        try:
            data = await MonthlyStorageService.load_monthly_stats(year, month)
            
            if story_key not in data["stories"]:
                data["stories"][story_key] = {}
            
            # Update stats
            for key, value in stats_data.items():
                if value is not None:
                    data["stories"][story_key][key] = value
            
            # Store title for reference
            if title:
                data["stories"][story_key]["title"] = title
            
            data["stories"][story_key]["last_stats_update"] = datetime.now().isoformat()
            
            return await MonthlyStorageService.save_monthly_stats(year, month, data)
        except Exception as e:
            logger.error(f"Error updating story monthly stats: {e}")
            return False
    
    @staticmethod
    async def ensure_story_in_month(
        story_key: str,
        year: int,
        month: int,
        title: str
    ) -> bool:
        """Ensure a story exists in a monthly file (create with zeros if not)"""
        data = await MonthlyStorageService.load_monthly_stats(year, month)
        
        if story_key not in data["stories"]:
            data["stories"][story_key] = {
                "title": title,
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
                "last_stats_update": datetime.now().isoformat()
            }
            return await MonthlyStorageService.save_monthly_stats(year, month, data)
        
        return True
    
    @staticmethod
    async def delete_story_from_month(story_key: str, year: int, month: int) -> bool:
        """Remove a story from a monthly file"""
        try:
            data = await MonthlyStorageService.load_monthly_stats(year, month)
            if story_key in data["stories"]:
                del data["stories"][story_key]
                return await MonthlyStorageService.save_monthly_stats(year, month, data)
            return True
        except Exception as e:
            logger.error(f"Error deleting story from month: {e}")
            return False
    
    @staticmethod
    async def get_months_for_story(story_key: str) -> List[Dict[str, Any]]:
        """Get all months where a story has data"""
        months = await MonthlyStorageService.get_available_months()
        result = []
        
        for month_info in months:
            stats = await MonthlyStorageService.get_story_monthly_stats(
                story_key, month_info["year"], month_info["month"]
            )
            if stats:
                result.append({
                    "year": month_info["year"],
                    "month": month_info["month"],
                    "display": month_info["display"],
                    "has_data": True,
                    "leaderboard": stats.get("leaderboard", False)
                })
            else:
                result.append({
                    "year": month_info["year"],
                    "month": month_info["month"],
                    "display": month_info["display"],
                    "has_data": False,
                    "leaderboard": False
                })
        
        return result