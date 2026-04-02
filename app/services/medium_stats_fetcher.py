"""
Medium Stats Fetcher - Uses the exact same logic as the working ms.py script
"""

import requests
import json
import sqlite3
import os
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class MediumStatsFetcher:
    """Fetch detailed statistics from Medium using the same approach as ms.py"""
    
    def __init__(self):
        self.cookies = None
        self._load_cookies()
    
    def _get_chrome_cookies_linux(self) -> Optional[Dict[str, str]]:
        """Extract Medium cookies from Chrome on Linux - Same as ms.py"""
        cookie_paths = [
            Path.home() / ".config/google-chrome/Default/Cookies",
            Path.home() / ".config/google-chrome/Profile 1/Cookies",
            Path.home() / ".config/google-chrome/Profile 2/Cookies",
            Path.home() / ".config/chromium/Default/Cookies",
        ]
        
        for cookie_path in cookie_paths:
            if cookie_path.exists():
                try:
                    temp_db = tempfile.NamedTemporaryFile(delete=False)
                    temp_db.close()
                    shutil.copy2(cookie_path, temp_db.name)
                    
                    conn = sqlite3.connect(temp_db.name)
                    cursor = conn.cursor()
                    
                    cursor.execute(
                        "SELECT name, value FROM cookies WHERE host_key LIKE '%medium.com%'"
                    )
                    
                    cookies = {name: value for name, value in cursor.fetchall()}
                    conn.close()
                    os.unlink(temp_db.name)
                    
                    if cookies and 'sid' in cookies:
                        logger.info(f"✅ Found {len(cookies)} cookies from Chrome")
                        return cookies
                except Exception as e:
                    logger.debug(f"Could not read cookies from {cookie_path}: {e}")
                    continue
        
        return None
    
    def _get_firefox_cookies(self) -> Optional[Dict[str, str]]:
        """Extract Medium cookies from Firefox"""
        firefox_profiles = list(Path.home().glob(".mozilla/firefox/*.default*"))
        
        for profile in firefox_profiles:
            cookie_path = profile / "cookies.sqlite"
            if cookie_path.exists():
                try:
                    temp_db = tempfile.NamedTemporaryFile(delete=False)
                    temp_db.close()
                    shutil.copy2(cookie_path, temp_db.name)
                    
                    conn = sqlite3.connect(temp_db.name)
                    cursor = conn.cursor()
                    
                    cursor.execute(
                        "SELECT name, value FROM moz_cookies WHERE host LIKE '%medium.com%'"
                    )
                    
                    cookies = {name: value for name, value in cursor.fetchall()}
                    conn.close()
                    os.unlink(temp_db.name)
                    
                    if cookies and 'sid' in cookies:
                        logger.info(f"✅ Found {len(cookies)} cookies from Firefox")
                        return cookies
                except Exception as e:
                    logger.debug(f"Could not read Firefox cookies: {e}")
                    continue
        
        return None
    
    def _load_cookies(self):
        """Load cookies from browser - Same as ms.py"""
        import platform
        system = platform.system()
        
        logger.info(f"Detected OS: {system}")
        
        if system == "Linux":
            self.cookies = self._get_chrome_cookies_linux()
            if not self.cookies:
                self.cookies = self._get_firefox_cookies()
        elif system == "Darwin":
            # For macOS, you may need to adjust the path
            self.cookies = self._get_chrome_cookies_linux()  # Chrome on Mac has different path
            if not self.cookies:
                self.cookies = self._get_firefox_cookies()
        else:
            logger.warning(f"Automatic cookie extraction not fully supported on {system}")
        
        if not self.cookies:
            logger.warning("Could not load cookies from browser")
            logger.info("Make sure you are logged into Medium and browser is closed")
        else:
            logger.info(f"🍪 Loaded cookies: {list(self.cookies.keys())}")
    
    def is_authenticated(self) -> bool:
        """Check if we have valid cookies"""
        return self.cookies is not None and 'sid' in self.cookies
    
    def extract_post_id_from_url(self, medium_url: str) -> Optional[str]:
        """Extract post ID from Medium URL - Same as ms.py"""
        if not medium_url:
            return None
        
        url = medium_url.rstrip('/')
        parts = url.split('/')
        last_part = parts[-1]
        
        if '-' in last_part:
            post_id = last_part.split('-')[-1]
            if len(post_id) >= 10:
                return post_id
        
        if len(last_part) >= 10:
            return last_part
        
        return None
    
    def _get_headers(self, post_id: str) -> Dict[str, str]:
        """Generate headers for the GraphQL request - Exactly as in ms.py"""
        return {
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "apollographql-client-name": "lite",
            "apollographql-client-version": "main-20260401-140543-04b3dba818",
            "content-type": "application/json",
            "graphql-operation": "useStatsPostNewChartDataQuery",
            "medium-frontend-app": "lite/main-20260401-140543-04b3dba818",
            "medium-frontend-path": f"/me/stats/post/{post_id}",
            "medium-frontend-route": "stats-post",
            "origin": "https://medium.com",
            "priority": "u=1, i",
            "referer": f"https://medium.com/me/stats/post/{post_id}",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        }
    
    def _get_graphql_payload(self, post_id: str) -> List[Dict]:
        """Generate GraphQL payload for current month stats - Exactly as in ms.py"""
        now = datetime.now(timezone.utc)
        start_of_month = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        start_at = int(start_of_month.timestamp() * 1000)
        end_at = int(now.timestamp() * 1000)
        
        logger.info(f"📝 start: {start_at}")
        logger.info(f"📝 end: {end_at}")

        return [{
            "operationName": "useStatsPostNewChartDataQuery",
            "variables": {
                "postId": post_id,
                "startAt": start_at,
                "endAt": end_at,
                "postStatsDailyBundleInput": {
                    "postId": post_id,
                    "fromDayStartsAt": start_at,
                    "toDayStartsAt": end_at
                }
            },
            "query": """query useStatsPostNewChartDataQuery($postId: ID!, $startAt: Long!, $endAt: Long!, $postStatsDailyBundleInput: PostStatsDailyBundleInput!) {
  post(id: $postId) {
    id
    earnings {
      dailyEarnings(startAt: $startAt, endAt: $endAt) {
        periodStartedAt
        amount
        __typename
      }
      __typename
    }
    __typename
  }
  postStatsDailyBundle(postStatsDailyBundleInput: $postStatsDailyBundleInput) {
    buckets {
      dayStartsAt
      membershipType
      readersThatReadCount
      readersThatViewedCount
      readersThatClappedCount
      readersThatRepliedCount
      readersThatHighlightedCount
      readersThatInitiallyFollowedAuthorFromThisPostCount
      __typename
    }
    __typename
  }
}"""
        }]
    
    async def fetch_post_stats(self, medium_url: str) -> Optional[Dict[str, Any]]:
        """Fetch statistics for a single post - Exactly the same as ms.py"""
        if not self.is_authenticated():
            logger.warning("Not authenticated. Cannot fetch stats.")
            return None
        
        post_id = self.extract_post_id_from_url(medium_url)
        if not post_id:
            logger.warning(f"Could not extract post ID from URL: {medium_url}")
            return None
        
        logger.info(f"📝 Fetching stats for post ID: {post_id}")
        
        # Create session and add cookies - same as ms.py
        session = requests.Session()
        for name, value in self.cookies.items():
            session.cookies.set(name, value, domain=".medium.com", path="/")
        
        url = "https://medium.com/_/graphql"
        payload = self._get_graphql_payload(post_id)
        headers = self._get_headers(post_id)
        
        try:
            response = session.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Successfully fetched stats for {post_id}")
                return self._parse_stats_response(data, post_id)
            else:
                logger.error(f"❌ Failed to fetch stats: HTTP {response.status_code}")
                if response.status_code == 403:
                    logger.error("   403 Forbidden - Your cookies may be expired")
                    logger.info("   Solution: Log out of Medium, log back in, close browser, then try again")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error fetching stats: {e}")
            return None
    
    def _parse_stats_response(self, data: Any, post_id: str) -> Dict[str, Any]:
        """Parse the GraphQL response - Same as ms.py"""
        stats = {
            'post_id': post_id,
            'fetch_timestamp': datetime.now().isoformat(),
            'period': {
                'start': None,
                'end': None
            },
            'totals': {
                'member_reads': 0,
                'member_views': 0,
                'nonmember_reads': 0,
                'nonmember_views': 0,
                'total_reads': 0,
                'total_views': 0,
                'claps': 0,
                'replies': 0,
                'highlights': 0,
                'new_followers': 0,
                'read_ratio': 0,
                'member_read_percentage': 0
            },
            'daily_breakdown': []
        }
        
        if isinstance(data, list) and len(data) > 0:
            stats_data = data[0].get('data', {})
            post_stats = stats_data.get('postStatsDailyBundle', {})
            buckets = post_stats.get('buckets', [])
            
            now = datetime.now()
            start_of_month = datetime(now.year, now.month, 1, 0, 0, 0)
            stats['period']['start'] = start_of_month.isoformat()
            stats['period']['end'] = now.isoformat()
            
            for bucket in buckets:
                date = datetime.fromtimestamp(bucket['dayStartsAt'] / 1000).strftime('%Y-%m-%d')
                membership = bucket.get('membershipType', 'UNKNOWN')
                
                reads = bucket.get('readersThatReadCount', 0)
                views = bucket.get('readersThatViewedCount', 0)
                claps = bucket.get('readersThatClappedCount', 0)
                replies = bucket.get('readersThatRepliedCount', 0)
                highlights = bucket.get('readersThatHighlightedCount', 0)
                new_followers = bucket.get('readersThatInitiallyFollowedAuthorFromThisPostCount', 0)
                
                stats['daily_breakdown'].append({
                    'date': date,
                    'membership_type': membership,
                    'reads': reads,
                    'views': views,
                    'claps': claps,
                    'replies': replies,
                    'highlights': highlights,
                    'new_followers': new_followers
                })
                
                if membership == 'MEMBER':
                    stats['totals']['member_reads'] += reads
                    stats['totals']['member_views'] += views
                elif membership == 'NONMEMBER':
                    stats['totals']['nonmember_reads'] += reads
                    stats['totals']['nonmember_views'] += views
                
                stats['totals']['total_reads'] += reads
                stats['totals']['total_views'] += views
                stats['totals']['claps'] += claps
                stats['totals']['replies'] += replies
                stats['totals']['highlights'] += highlights
                stats['totals']['new_followers'] += new_followers
        
        # Calculate derived metrics
        if stats['totals']['total_views'] > 0:
            stats['totals']['read_ratio'] = round(
                stats['totals']['total_reads'] / stats['totals']['total_views'] * 100, 1
            )
        
        if stats['totals']['total_reads'] > 0:
            stats['totals']['member_read_percentage'] = round(
                stats['totals']['member_reads'] / stats['totals']['total_reads'] * 100, 1
            )
        
        return stats
    
    async def fetch_all_stories_stats(self, stories: List[Dict]) -> Dict[str, Any]:
        """Fetch stats for multiple stories"""
        results = {
            'total': len(stories),
            'updated': 0,
            'failed': 0,
            'details': []
        }
        
        for i, story in enumerate(stories):
            try:
                logger.info(f"📊 ({i+1}/{len(stories)}): {story['name'][:50]}...")
                stats = await self.fetch_post_stats(story['medium_url'])
                if stats:
                    results['updated'] += 1
                    results['details'].append({
                        'key': story['key'],
                        'name': story['name'],
                        'success': True,
                        'stats': stats
                    })
                else:
                    results['failed'] += 1
                    results['details'].append({
                        'key': story['key'],
                        'name': story['name'],
                        'success': False
                    })
            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'key': story['key'],
                    'name': story['name'],
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    # Add this method to debug cookie loading
def debug_cookies(self):
    """Debug method to check cookies"""
    if self.cookies:
        print(f"Cookies present: {list(self.cookies.keys())}")
        print(f"Has sid: {'sid' in self.cookies}")
        if 'sid' in self.cookies:
            print(f"sid length: {len(self.cookies['sid'])}")
    else:
        print("No cookies loaded")