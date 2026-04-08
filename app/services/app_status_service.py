"""
App Status Service - Manages application state like current leaderboard month and mode
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from config import settings
from app.services.file_service import load_app_status, save_app_status

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
            data = await load_app_status()
            return data.get('leaderboard_month')
        except Exception as e:
            logger.error(f"Error reading leaderboard month: {e}")
            return None
    
    @staticmethod
    async def set_leaderboard_month(year: int, month: int) -> bool:
        """Set the currently loaded leaderboard month"""
        try:
            data = await load_app_status()
            month_str = f"{year}-{month:02d}"
            
            data['leaderboard_month'] = month_str
            data['last_updated'] = datetime.now().isoformat()
            
            await save_app_status(data)
            logger.info(f"Leaderboard month set to: {month_str}")
            return True
        except Exception as e:
            logger.error(f"Error setting leaderboard month: {e}")
            return False
    
    @staticmethod
    async def clear_leaderboard_month() -> bool:
        """Clear the stored leaderboard month"""
        try:
            data = await load_app_status()
            data['leaderboard_month'] = None
            data['last_updated'] = datetime.now().isoformat()
            
            await save_app_status(data)
            logger.info("Leaderboard month cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing leaderboard month: {e}")
            return False
    
    @staticmethod
    async def get_current_mode() -> str:
        """Get current view mode: 'dashboard' or 'month'"""
        try:
            data = await load_app_status()
            return data.get('current_mode', 'dashboard')
        except Exception as e:
            logger.error(f"Error reading current mode: {e}")
            return 'dashboard'
    
    @staticmethod
    async def set_current_mode(mode: str) -> bool:
        """Set current view mode: 'dashboard' or 'month'"""
        try:
            data = await load_app_status()
            data['current_mode'] = mode
            data['last_updated'] = datetime.now().isoformat()
            
            await save_app_status(data)
            logger.info(f"Current mode set to: {mode}")
            return True
        except Exception as e:
            logger.error(f"Error setting current mode: {e}")
            return False
    
    @staticmethod
    async def get_current_month() -> Dict[str, Any]:
        """Get the currently selected month for month mode"""
        try:
            data = await load_app_status()
            now = datetime.now()
            
            month_data = data.get('current_month', {})
            year = month_data.get('year', now.year)
            month = month_data.get('month', now.month)
            
            return {
                "year": year,
                "month": month,
                "display": datetime(year, month, 1).strftime("%b %Y")
            }
        except Exception as e:
            logger.error(f"Error reading current month: {e}")
            now = datetime.now()
            return {"year": now.year, "month": now.month, "display": now.strftime("%b %Y")}
    
    @staticmethod
    async def set_current_month(year: int, month: int) -> bool:
        """Set the currently selected month for month mode"""
        try:
            data = await load_app_status()
            data['current_month'] = {"year": year, "month": month}
            data['last_updated'] = datetime.now().isoformat()
            
            await save_app_status(data)
            logger.info(f"Current month set to: {year}-{month:02d}")
            return True
        except Exception as e:
            logger.error(f"Error setting current month: {e}")
            return False
    
    @staticmethod
    async def get_medium_username() -> Optional[str]:
        """Get stored Medium username"""
        try:
            data = await load_app_status()
            return data.get('medium_username')
        except Exception as e:
            logger.error(f"Error getting medium username: {e}")
            return None

    @staticmethod
    async def set_medium_username(username: str) -> bool:
        """Set Medium username"""
        try:
            data = await load_app_status()
            data['medium_username'] = username
            data['last_updated'] = datetime.now().isoformat()
            
            await save_app_status(data)
            logger.info(f"Medium username set to: {username}")
            return True
        except Exception as e:
            logger.error(f"Error setting medium username: {e}")
            return False
    
    @staticmethod
    async def get_all_settings() -> Dict[str, Any]:
        """Get all app status settings"""
        try:
            data = await load_app_status()
            return data
        except Exception as e:
            logger.error(f"Error reading settings: {e}")
            return {
                "leaderboard_month": None,
                "current_mode": "dashboard",
                "current_month": {"year": datetime.now().year, "month": datetime.now().month},
                "medium_username": None,
                "last_updated": datetime.now().isoformat()
            }
    
    @staticmethod
    async def update_settings(updates: Dict[str, Any]) -> bool:
        """Update multiple settings at once"""
        try:
            data = await load_app_status()
            
            for key, value in updates.items():
                if value is not None:
                    data[key] = value
            
            data['last_updated'] = datetime.now().isoformat()
            await save_app_status(data)
            logger.info(f"Settings updated: {list(updates.keys())}")
            return True
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return False
    
    @staticmethod
    async def get_last_fetch_time() -> Optional[str]:
        """Get the last time stats were fetched from Medium"""
        try:
            data = await load_app_status()
            return data.get('last_stats_fetch')
        except Exception as e:
            logger.error(f"Error getting last fetch time: {e}")
            return None
    
    @staticmethod
    async def set_last_fetch_time(timestamp: Optional[str] = None) -> bool:
        """Set the last time stats were fetched from Medium"""
        try:
            data = await load_app_status()
            
            if timestamp is None:
                timestamp = datetime.now().isoformat()
            
            data['last_stats_fetch'] = timestamp
            data['last_updated'] = datetime.now().isoformat()
            
            await save_app_status(data)
            logger.info(f"Last fetch time set to: {timestamp}")
            return True
        except Exception as e:
            logger.error(f"Error setting last fetch time: {e}")
            return False
    
    @staticmethod
    async def get_import_status() -> Dict[str, Any]:
        """Get current import status"""
        try:
            data = await load_app_status()
            return {
                "is_importing": data.get('is_importing', False),
                "import_progress": data.get('import_progress', 0),
                "import_total": data.get('import_total', 0),
                "import_current": data.get('import_current', 0),
                "import_started_at": data.get('import_started_at'),
                "import_last_error": data.get('import_last_error')
            }
        except Exception as e:
            logger.error(f"Error getting import status: {e}")
            return {
                "is_importing": False,
                "import_progress": 0,
                "import_total": 0,
                "import_current": 0,
                "import_started_at": None,
                "import_last_error": None
            }
    
    @staticmethod
    async def set_import_status(
        is_importing: bool = False,
        progress: int = 0,
        total: int = 0,
        current: int = 0,
        error: Optional[str] = None
    ) -> bool:
        """Set current import status"""
        try:
            data = await load_app_status()
            
            data['is_importing'] = is_importing
            data['import_progress'] = progress
            data['import_total'] = total
            data['import_current'] = current
            
            if is_importing and not data.get('import_started_at'):
                data['import_started_at'] = datetime.now().isoformat()
            elif not is_importing:
                data['import_completed_at'] = datetime.now().isoformat()
            
            if error:
                data['import_last_error'] = error
            elif error is None and not is_importing:
                data['import_last_error'] = None
            
            data['last_updated'] = datetime.now().isoformat()
            
            await save_app_status(data)
            return True
        except Exception as e:
            logger.error(f"Error setting import status: {e}")
            return False
    
    @staticmethod
    async def reset() -> bool:
        """Reset all app status to defaults"""
        try:
            now = datetime.now()
            default_data = {
                "leaderboard_month": None,
                "current_mode": "dashboard",
                "current_month": {"year": now.year, "month": now.month},
                "medium_username": None,
                "last_stats_fetch": None,
                "is_importing": False,
                "import_progress": 0,
                "import_total": 0,
                "import_current": 0,
                "import_started_at": None,
                "import_completed_at": None,
                "import_last_error": None,
                "last_updated": now.isoformat()
            }
            
            await save_app_status(default_data)
            logger.info("App status reset to defaults")
            return True
        except Exception as e:
            logger.error(f"Error resetting app status: {e}")
            return False
        
# This file includes:

# Leaderboard month management - get_leaderboard_month(), set_leaderboard_month(), clear_leaderboard_month()

# Mode management - get_current_mode(), set_current_mode()

# Current month management - get_current_month(), set_current_month()

# Medium username management - get_medium_username(), set_medium_username()

# Settings management - get_all_settings(), update_settings()

# Fetch time tracking - get_last_fetch_time(), set_last_fetch_time()

# Import status tracking - get_import_status(), set_import_status()

# Reset functionality - reset()

# All methods now use the load_app_status() and save_app_status() functions from file_service.py for consistent file handling.