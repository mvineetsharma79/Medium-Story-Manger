"""
App Status Service - Manages application state like current leaderboard month and mode
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any
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
    
    @staticmethod
    async def get_current_mode() -> str:
        """Get current view mode: 'dashboard' or 'month'"""
        try:
            status_path = AppStatusService.get_status_path()
            if status_path.exists():
                with open(status_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('current_mode', 'dashboard')
            return 'dashboard'
        except Exception as e:
            logger.error(f"Error reading current mode: {e}")
            return 'dashboard'
    
    @staticmethod
    async def set_current_mode(mode: str) -> bool:
        """Set current view mode: 'dashboard' or 'month'"""
        try:
            status_path = AppStatusService.get_status_path()
            
            data = {}
            if status_path.exists():
                with open(status_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            data['current_mode'] = mode
            data['last_updated'] = datetime.now().isoformat()
            
            with open(status_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Current mode set to: {mode}")
            return True
        except Exception as e:
            logger.error(f"Error setting current mode: {e}")
            return False
    
    @staticmethod
    async def get_current_month() -> Dict[str, Any]:
        """Get the currently selected month for month mode"""
        try:
            status_path = AppStatusService.get_status_path()
            now = datetime.now()
            
            if status_path.exists():
                with open(status_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    month_data = data.get('current_month', {})
                    return {
                        "year": month_data.get('year', now.year),
                        "month": month_data.get('month', now.month),
                        "display": datetime(month_data.get('year', now.year), 
                                          month_data.get('month', now.month), 1).strftime("%b %Y")
                    }
            
            return {"year": now.year, "month": now.month, "display": now.strftime("%b %Y")}
        except Exception as e:
            logger.error(f"Error reading current month: {e}")
            now = datetime.now()
            return {"year": now.year, "month": now.month, "display": now.strftime("%b %Y")}
    
    @staticmethod
    async def set_current_month(year: int, month: int) -> bool:
        """Set the currently selected month for month mode"""
        try:
            status_path = AppStatusService.get_status_path()
            
            data = {}
            if status_path.exists():
                with open(status_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            data['current_month'] = {"year": year, "month": month}
            data['last_updated'] = datetime.now().isoformat()
            
            with open(status_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Current month set to: {year}-{month:02d}")
            return True
        except Exception as e:
            logger.error(f"Error setting current month: {e}")
            return False
    
    @staticmethod
    async def get_all_settings() -> Dict[str, Any]:
        """Get all app status settings"""
        try:
            status_path = AppStatusService.get_status_path()
            if status_path.exists():
                with open(status_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {
                "leaderboard_month": None,
                "current_mode": "dashboard",
                "current_month": {"year": datetime.now().year, "month": datetime.now().month}
            }
        except Exception as e:
            logger.error(f"Error reading settings: {e}")
            return {}