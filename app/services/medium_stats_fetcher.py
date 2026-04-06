"""
Medium Stats Fetcher - Uses the extracted MediumAPIService
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

from app.services.medium_api_service import get_medium_api_service

logger = logging.getLogger(__name__)


class MediumStatsFetcher:
    """
    Fetches statistics from Medium API using the extracted service.
    This class adds business logic on top of the raw API calls.
    """
    
    def __init__(self):
        self.api_service = get_medium_api_service()
    
    def is_authenticated(self) -> bool:
        """Check if we have valid cookies"""
        return self.api_service.is_authenticated()
    
    def extract_post_id_from_url(self, medium_url: str) -> Optional[str]:
        """Extract post ID from Medium URL"""
        return self.api_service.extract_post_id_from_url(medium_url)
    
    async def fetch_stats_for_date_range(self, medium_url: str, start_date: datetime, end_date: datetime) -> Optional[Dict[str, Any]]:
        """Fetch stats for a custom date range"""
        post_id = self.extract_post_id_from_url(medium_url)
        if not post_id:
            logger.warning(f"Could not extract post ID from URL: {medium_url}")
            return None
        
        response = self.api_service.fetch_stats(post_id, start_date, end_date)
        if response:
            return self.api_service.parse_stats_response(response, post_id)
        return None
    
    async def fetch_lifetime_stats(self, medium_url: str) -> Optional[Dict[str, Any]]:
        """Fetch lifetime stats (readersCount, viewersCount, presentationCount)"""
        post_id = self.extract_post_id_from_url(medium_url)
        if not post_id:
            logger.warning(f"Could not extract post ID from URL: {medium_url}")
            return None
        
        response = self.api_service.fetch_lifetime_stats(post_id)
        if response:
            return self.api_service.parse_lifetime_response(response, post_id)
        return None
    
    async def fetch_complete_stats(self, medium_url: str) -> Optional[Dict[str, Any]]:
        """Fetch complete stats (current month + lifetime totals + metadata)"""
        post_id = self.extract_post_id_from_url(medium_url)
        if not post_id:
            logger.warning(f"Could not extract post ID from URL: {medium_url}")
            return None
        
        # Fetch current month stats
        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1, 0, 0, 0)
        current_response = self.api_service.fetch_stats(post_id, start_of_month, now)
        
        if not current_response:
            return None
        
        result = self.api_service.parse_stats_response(current_response, post_id)
        
        # Fetch lifetime stats
        lifetime_response = self.api_service.fetch_lifetime_stats(post_id)
        if lifetime_response:
            lifetime_data = self.api_service.parse_lifetime_response(lifetime_response, post_id)
            result['lifetime_totals'] = {
                'total_reads': lifetime_data.get('lifetime_reads', 0),
                'total_views': lifetime_data.get('lifetime_views', 0),
                'presentation_count': lifetime_data.get('presentation_count', 0),
            }
        else:
            result['lifetime_totals'] = {'total_reads': 0, 'total_views': 0, 'presentation_count': 0}
        
        result['stats_month'] = datetime.now().strftime("%Y-%m")
        return result
    
    async def fetch_stats_for_month(self, medium_url: str, year: int, month: int) -> Optional[Dict[str, Any]]:
        """Fetch stats for a specific month/year"""
        post_id = self.extract_post_id_from_url(medium_url)
        if not post_id:
            logger.warning(f"Could not extract post ID from URL: {medium_url}")
            return None
        
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        response = self.api_service.fetch_stats(post_id, start_date, end_date)
        if response:
            result = self.api_service.parse_stats_response(response, post_id)
            
            # Also fetch lifetime stats
            lifetime_response = self.api_service.fetch_lifetime_stats(post_id)
            if lifetime_response:
                lifetime_data = self.api_service.parse_lifetime_response(lifetime_response, post_id)
                result['lifetime_totals'] = {
                    'total_reads': lifetime_data.get('lifetime_reads', 0),
                    'total_views': lifetime_data.get('lifetime_views', 0),
                    'presentation_count': lifetime_data.get('presentation_count', 0),
                }
            else:
                result['lifetime_totals'] = {'total_reads': 0, 'total_views': 0, 'presentation_count': 0}
            
            result['stats_month'] = f"{year}-{month:02d}"
            return result
        
        return None
    
    async def fetch_leaderboard_earnings(self, username: str = "mvineetsharma", year: int = None, month: int = None) -> Optional[List[Dict[str, Any]]]:
        """Fetch monthly earnings for leaderboard"""
        if year is None or month is None:
            now = datetime.now()
            year = now.year
            month = now.month
        
        return self.api_service.fetch_leaderboard_earnings(username, year, month)
    
    async def fetch_current_month_stats(self, medium_url: str) -> Optional[Dict[str, Any]]:
        """Fetch current month stats"""
        now = datetime.now()
        return await self.fetch_stats_for_month(medium_url, now.year, now.month)