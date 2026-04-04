"""
App Status Service - Manages application state like current leaderboard month
"""
import json
from pathlib import Path
from typing import Optional
from datetime import datetime
import logging

from config import settings

logger = logging.getLogger(__name__)


class AppStatusService:
    """Service to manage application status"""
    
    @staticmethod
    def get_status_path() -> Path:
        """Get path to appstatus.json"""
        data_dir = Path(settings.data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "appstatus.json"
    
    @staticmethod
    async def get_leaderboard_month() -> Optional[str]:
        """Get the currently loaded leaderboard month (YYYY-MM format)"""
        try:
            status_path = AppStatusService.get_status_path()
            if status_path.exists():
                with open(status_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('leaderboard_month')
            return None
        except Exception as e:
            logger.error(f"Error reading leaderboard month: {e}")
            return None
    
    @staticmethod
    async def set_leaderboard_month(year: int, month: int) -> bool:
        """Set the currently loaded leaderboard month"""
        try:
            status_path = AppStatusService.get_status_path()
            month_str = f"{year}-{month:02d}"
            
            data = {}
            if status_path.exists():
                with open(status_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            data['leaderboard_month'] = month_str
            data['last_updated'] = datetime.now().isoformat()
            
            with open(status_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Leaderboard month set to: {month_str}")
            return True
        except Exception as e:
            logger.error(f"Error setting leaderboard month: {e}")
            return False
    
    @staticmethod
    async def clear_leaderboard_month() -> bool:
        """Clear the stored leaderboard month"""
        try:
            status_path = AppStatusService.get_status_path()
            if status_path.exists():
                with open(status_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                data['leaderboard_month'] = None
                data['last_updated'] = datetime.now().isoformat()
                
                with open(status_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                logger.info("Leaderboard month cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing leaderboard month: {e}")
            return False