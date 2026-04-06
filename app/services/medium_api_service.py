"""
Medium API Service - Pure API client for Medium GraphQL calls
Supports Chrome cookie extraction, environment variable fallback, and explicit cookie headers
"""

import os
import json
import sqlite3
import tempfile
import shutil
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import calendar
import requests  # ← ADD THIS IMPORT

logger = logging.getLogger(__name__)

# ============================================
# DEBUG SETTINGS
# ============================================
DEBUG = os.environ.get("MEDIUM_API_DEBUG", "false").lower() == "true"


class MediumAPIService:
    """
    Service to make direct GraphQL calls to Medium API.
    
    GraphQL Endpoint: POST https://medium.com/_/graphql
    
    Cookie Priority:
    1. Extract from Chrome browser (must be open and logged in)
    2. Fallback to environment variables (MEDIUM_COOKIE or MEDIUM_SID+MEDIUM_UID)
    
    Curl equivalent:
    curl -X POST https://medium.com/_/graphql \\
      -H "Content-Type: application/json" \\
      -H "Cookie: sid=xxx; uid=xxx" \\
      -d '{"operationName":"useStatsPostNewChartDataQuery",...}'
    """
    
    GRAPHQL_URL = "https://medium.com/_/graphql"
    USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
    
    def __init__(self):
        self.cookies = None
        self._load_cookies()
    
    def _debug_print(self, title: str, data: Any, max_length: int = 5000):
        """Pretty print debug output if DEBUG is True"""
        if not DEBUG:
            return
        
        print("\n" + "=" * 80)
        print(f"🔍 DEBUG: {title}")
        print("=" * 80)
        
        if isinstance(data, (dict, list)):
            print(json.dumps(data, indent=2, ensure_ascii=False)[:max_length])
        else:
            print(str(data)[:max_length])
        
        if len(str(data)) > max_length:
            print(f"\n... (truncated, showing first {max_length} characters)")
        
        print("=" * 80 + "\n")
    
    # ============================================
    # COOKIE EXTRACTION - Chrome (Priority 1)
    # ============================================
    
    def _get_chrome_cookies(self) -> Optional[Dict[str, str]]:
        """
        Extract Medium cookies from Chrome on Linux.
        
        Chrome must be open and you must be logged into medium.com.
        The cookie database is read while Chrome is running.
        
        Returns: Dictionary of cookies or None if extraction fails.
        """
        cookie_paths = [
            Path.home() / ".config/google-chrome/Default/Cookies",
            Path.home() / ".config/google-chrome/Profile 1/Cookies",
            Path.home() / ".config/google-chrome/Profile 2/Cookies",
            Path.home() / ".config/chromium/Default/Cookies",
        ]
        
        for cookie_path in cookie_paths:
            if cookie_path.exists():
                try:
                    # Copy the cookie database (Chrome may have it locked)
                    temp_db = tempfile.NamedTemporaryFile(delete=False)
                    temp_db.close()
                    shutil.copy2(cookie_path, temp_db.name)
                    
                    conn = sqlite3.connect(temp_db.name)
                    cursor = conn.cursor()
                    
                    # Query for Medium cookies
                    cursor.execute(
                        "SELECT name, value FROM cookies WHERE host_key LIKE '%medium.com%'"
                    )
                    
                    cookies = {}
                    for name, value in cursor.fetchall():
                        if value:  # Only add non-empty values
                            cookies[name] = value
                    
                    conn.close()
                    os.unlink(temp_db.name)
                    
                    # Check if we got the essential cookies
                    if cookies.get('sid') and cookies.get('uid'):
                        self._debug_print("Cookies extracted from Chrome", {
                            k: v[:20] + "..." if len(v) > 20 else v 
                            for k, v in cookies.items()
                        })
                        logger.info(f"✅ Found {len(cookies)} cookies from Chrome")
                        return cookies
                    else:
                        logger.warning(f"Found cookies but missing sid/uid: {list(cookies.keys())}")
                        
                except Exception as e:
                    logger.debug(f"Could not read cookies from {cookie_path}: {e}")
                    continue
        
        return None
    
    # ============================================
    # COOKIE EXTRACTION - Environment (Priority 2)
    # ============================================
    
    def _get_cookies_from_env(self) -> Optional[Dict[str, str]]:
        """
        Get cookies from environment variables.
        
        Two options:
        1. MEDIUM_COOKIE - Full cookie string (copy from browser DevTools)
        2. MEDIUM_SID + MEDIUM_UID - Individual cookies
        
        Example:
        export MEDIUM_COOKIE='sid=xxx; uid=xxx; xsrf=xxx'
        OR
        export MEDIUM_SID='1:xxxxx'
        export MEDIUM_UID='6a63927f9b83'
        """
        # Option 1: Full cookie string
        cookie_string = os.environ.get("MEDIUM_COOKIE")
        if cookie_string:
            cookies = {}
            for item in cookie_string.split('; '):
                if '=' in item:
                    key, value = item.split('=', 1)
                    if value:
                        cookies[key] = value
            if cookies.get('sid') and cookies.get('uid'):
                self._debug_print("Cookies from MEDIUM_COOKIE env var", {
                    k: v[:20] + "..." if len(v) > 20 else v 
                    for k, v in cookies.items()
                })
                logger.info("✅ Loaded cookies from MEDIUM_COOKIE environment variable")
                return cookies
        
        # Option 2: Individual SID and UID
        sid = os.environ.get("MEDIUM_SID")
        uid = os.environ.get("MEDIUM_UID")
        if sid and uid:
            cookies = {"sid": sid, "uid": uid}
            self._debug_print("Cookies from MEDIUM_SID/MEDIUM_UID env vars", {
                "sid": sid[:20] + "...",
                "uid": uid
            })
            logger.info("✅ Loaded cookies from environment variables (SID/UID)")
            return cookies
        
        return None
    
    def _load_cookies(self):
        """
        Load cookies with priority:
        1. Extract from Chrome browser (must be open, logged into Medium)
        2. Fallback to environment variables
        """
        print("\n" + "=" * 60)
        print("🍪 LOADING COOKIES")
        print("=" * 60)
        
        # Priority 1: Chrome browser extraction
        logger.info("Attempting to extract cookies from Chrome...")
        self.cookies = self._get_chrome_cookies()
        
        # Priority 2: Environment variables fallback
        if not self.cookies:
            logger.info("Chrome extraction failed, trying environment variables...")
            self.cookies = self._get_cookies_from_env()
        
        if not self.cookies:
            logger.warning("=" * 60)
            logger.warning("⚠️ No cookies found! To fix:")
            logger.warning("")
            logger.warning("Option 1 - Browser (recommended):")
            logger.warning("  1. Open Chrome and log into medium.com")
            logger.warning("  2. Keep Chrome OPEN (don't close it)")
            logger.warning("  3. Restart this application")
            logger.warning("")
            logger.warning("Option 2 - Environment variables:")
            logger.warning("  export MEDIUM_COOKIE='sid=xxx; uid=xxx; xsrf=xxx'")
            logger.warning("  OR")
            logger.warning("  export MEDIUM_SID='1:xxxxx'")
            logger.warning("  export MEDIUM_UID='6a63927f9b83'")
            logger.warning("=" * 60)
        else:
            logger.info(f"✅ Successfully loaded {len(self.cookies)} cookies")
            logger.info(f"   Cookie keys: {list(self.cookies.keys())}")
        
        print("=" * 60 + "\n")
    
    def is_authenticated(self) -> bool:
        """Check if we have valid cookies for authentication"""
        return self.cookies is not None and self.cookies.get('sid') is not None
    
    # ============================================
    # UTILITY METHODS
    # ============================================
    
    def extract_post_id_from_url(self, medium_url: str) -> Optional[str]:
        """
        Extract post ID from Medium URL.
        
        Example: https://medium.com/@username/post-title-78cb972195da -> 78cb972195da
        
        curl equivalent:
        echo "https://medium.com/@username/post-title-78cb972195da" | awk -F'-' '{print $NF}'
        """
        if not medium_url:
            return None
        
        url = medium_url.rstrip('/')
        parts = url.split('/')
        last_part = parts[-1]
        
        if '-' in last_part:
            post_id = last_part.split('-')[-1]
            if len(post_id) >= 10:
                self._debug_print(f"Extracted post ID", {"url": medium_url, "post_id": post_id})
                return post_id
        
        if len(last_part) >= 10:
            self._debug_print(f"Extracted post ID", {"url": medium_url, "post_id": last_part})
            return last_part
        
        return None
    
    # ============================================
    # DATE UTILITIES - CORRECT MONTH RANGE
    # ============================================
    
    def get_month_timestamps(self, year: int, month: int) -> tuple:
        """
        Get correct start and end timestamps for a month.
        
        CRITICAL: Uses exclusive end date (1st of next month)
        This matches Medium's API expected format.
        
        Example for April 2026:
        startAt = 1775001600000 (April 1, 2026 00:00:00 UTC)
        endAt = 1775520000000   (May 1, 2026 00:00:00 UTC)
        
        Returns: (start_at, end_at) in milliseconds
        """
        # Start of month (UTC) - inclusive
        start_date = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
        start_at = int(start_date.timestamp() * 1000)
        
        # Start of NEXT month (exclusive end)
        if month == 12:
            end_date = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        else:
            end_date = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_at = int(end_date.timestamp() * 1000)
        
        print(f"📅 Date range for {year}-{month:02d}:")
        print(f"   startAt={start_at} ({start_date})")
        print(f"   endAt={end_at} ({end_date})")
        print(f"   Duration: {(end_at - start_at) / 86400000:.0f} days")
        
        return start_at, end_at
    
    # ============================================
    # GRAPHQL PAYLOAD BUILDERS
    # ============================================
    
    def build_stats_payload(self, post_id: str, start_at: int, end_at: int) -> List[Dict]:
        """
        Build GraphQL payload for monthly stats query.
        
        Operation: useStatsPostNewChartDataQuery
        Returns: Post metadata + daily buckets (reads, views, claps, earnings)
        
        curl equivalent:
        curl -X POST https://medium.com/_/graphql \\
          -H "Content-Type: application/json" \\
          -H "graphql-operation: useStatsPostNewChartDataQuery" \\
          -d '{
            "operationName": "useStatsPostNewChartDataQuery",
            "variables": {
              "postId": "78cb972195da",
              "startAt": 1775001600000,
              "endAt": 1775520000000,
              "postStatsDailyBundleInput": {
                "postId": "78cb972195da",
                "fromDayStartsAt": 1775001600000,
                "toDayStartsAt": 1775433600000
              }
            },
            "query": "..."
          }'
        """
        # Use the full query with fragments (exactly as browser uses)
        query = """query useStatsPostNewChartDataQuery($postId: ID!, $startAt: Long!, $endAt: Long!, $postStatsDailyBundleInput: PostStatsDailyBundleInput!) {
  post(id: $postId) {
    id
    earnings {
      dailyEarnings(startAt: $startAt, endAt: $endAt) {
        ...newBucketTimestamps_dailyPostEarning
        __typename
      }
      __typename
    }
    publicationFeaturingEventsConnection(first: 25, after: "") {
      ... on PublicationFeaturingEventsConnection {
        edges {
          node {
            eventType
            occurredAt
            __typename
          }
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
  postStatsDailyBundle(postStatsDailyBundleInput: $postStatsDailyBundleInput) {
    buckets {
      ...newBucketTimestamps_postStatsDailyBundleBucket
      __typename
    }
    __typename
  }
}

fragment newBucketTimestamps_dailyPostEarning on DailyPostEarning {
  periodStartedAt
  amount
  __typename
}

fragment newBucketTimestamps_postStatsDailyBundleBucket on PostStatsDailyBundleBucket {
  dayStartsAt
  membershipType
  readersThatReadCount
  readersThatViewedCount
  readersThatClappedCount
  readersThatRepliedCount
  readersThatHighlightedCount
  readersThatInitiallyFollowedAuthorFromThisPostCount
  __typename
}"""
        
        payload = [{
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
            "query": query
        }]
        
        self._debug_print("Monthly Stats Payload", payload)
        return payload
    
    def build_lifetime_payload(self, post_id: str) -> List[Dict]:
        """
        Build GraphQL payload for lifetime stats query.
        
        Operation: StatsPostFunnelQuery
        Returns: readersCount, viewersCount, presentationCount, feedClickThroughRate
        
        curl equivalent:
        curl -X POST https://medium.com/_/graphql \\
          -H "Content-Type: application/json" \\
          -H "graphql-operation: StatsPostFunnelQuery" \\
          -d '{"operationName":"StatsPostFunnelQuery","variables":{"postStatsTotalBundleInput":{"postId":"78cb972195da"}},"query":"..."}'
        """
        payload = [{
            "operationName": "StatsPostFunnelQuery",
            "variables": {
                "postStatsTotalBundleInput": {
                    "postId": post_id
                }
            },
            "query": """query StatsPostFunnelQuery($postStatsTotalBundleInput: PostStatsTotalBundleInput!) {
  postStatsTotalBundle(postStatsTotalBundleInput: $postStatsTotalBundleInput) {
    post {
      id
      __typename
    }
    readersCount
    viewersCount
    feedClickThroughRate
    presentationCount
    __typename
  }
}"""
        }]
        
        self._debug_print("Lifetime Stats Payload", payload)
        return payload
    
    # ============================================
    # API CALLS - WITH EXPLICIT COOKIE HEADER
    # ============================================
    
    def _make_request(self, url: str, headers: Dict, payload: List[Dict], request_type: str) -> Optional[Dict]:
        """
        Make HTTP request with debug logging and explicit cookie header.
        
        CRITICAL: The cookie must be added as an explicit header, not just via session.
        This is what makes earnings data appear!
        """
        self._debug_print(f"{request_type} Request Headers", headers)
        self._debug_print(f"{request_type} Request Payload", payload)
        
        # CRITICAL: Add cookies as explicit header
        if self.cookies:
            cookie_string = "; ".join([f"{k}={v}" for k, v in self.cookies.items() if v])
            headers["cookie"] = cookie_string
            self._debug_print(f"{request_type} Cookie Header (first 200 chars)", cookie_string[:200] + "...")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                self._debug_print(f"{request_type} Response", response_data)
                return response_data
            else:
                self._debug_print(f"{request_type} Error", {
                    "status_code": response.status_code,
                    "text": response.text[:500]
                })
                return None
        except Exception as e:
            self._debug_print(f"{request_type} Exception", {"error": str(e)})
            return None
    
    def fetch_stats(self, post_id: str, year: int, month: int) -> Optional[Dict]:
        """
        Fetch monthly stats for a specific year and month.
        
        Uses correct date range: 1st of month to 1st of next month.
        Cookies are added as explicit header for authentication.
        
        curl equivalent:
        curl -X POST http://localhost:8000/api/stories/fetch-story-stats/78cb972195da/2026-04
        
        Returns: Raw GraphQL response with earnings data
        """
        if not self.is_authenticated():
            logger.warning("Not authenticated. Cannot fetch stats.")
            return None
        
        start_at, end_at = self.get_month_timestamps(year, month)
        
        logger.info(f"📊 Fetching stats for post_id: {post_id} for {year}-{month:02d}")
        
        payload = self.build_stats_payload(post_id, start_at, end_at)
        
        headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "apollographql-client-name": "lite",
            "apollographql-client-version": "main-20260403-204212-a07bb9cfad",
            "content-type": "application/json",
            "graphql-operation": "useStatsPostNewChartDataQuery",
            "medium-frontend-app": "lite/main-20260403-204212-a07bb9cfad",
            "medium-frontend-path": f"/me/stats/post/{post_id}",
            "medium-frontend-route": "stats-post",
            "origin": "https://medium.com",
            "priority": "u=1, i",
            "referer": f"https://medium.com/me/stats/post/{post_id}",
            "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-bitness": '"64"',
            "sec-ch-ua-full-version": '"143.0.7499.146"',
            "sec-ch-ua-full-version-list": '"Google Chrome";v="143.0.7499.146", "Chromium";v="143.0.7499.146", "Not A(Brand";v="24.0.0.0"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": '"Linux"',
            "sec-ch-ua-platform-version": '"6.17.0"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": self.USER_AGENT
        }
        
        time.sleep(0.5)  # Rate limiting
        response = self._make_request(self.GRAPHQL_URL, headers, payload, f"Monthly Stats {year}-{month:02d}")
        
        if response:
            logger.info(f"✅ Successfully fetched monthly stats for post {post_id}")
        else:
            logger.error(f"❌ Failed to fetch monthly stats for post {post_id}")
        
        return response
    
    def fetch_lifetime_stats(self, post_id: str) -> Optional[Dict]:
        """
        Fetch lifetime stats for a story.
        
        Returns: readersCount, viewersCount, presentationCount, feedClickThroughRate
        
        curl equivalent:
        curl -X POST http://localhost:8000/api/stories/fetch-story-stats/78cb972195da
        """
        if not self.is_authenticated():
            logger.warning("Not authenticated. Cannot fetch lifetime stats.")
            return None
        
        payload = self.build_lifetime_payload(post_id)
        
        headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "apollographql-client-name": "lite",
            "apollographql-client-version": "main-20260403-204212-a07bb9cfad",
            "content-type": "application/json",
            "graphql-operation": "StatsPostFunnelQuery",
            "medium-frontend-app": "lite/main-20260403-204212-a07bb9cfad",
            "medium-frontend-path": f"/me/stats/post/{post_id}",
            "medium-frontend-route": "stats-post",
            "origin": "https://medium.com",
            "priority": "u=1, i",
            "referer": f"https://medium.com/me/stats/post/{post_id}",
            "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-bitness": '"64"',
            "sec-ch-ua-full-version": '"143.0.7499.146"',
            "sec-ch-ua-full-version-list": '"Google Chrome";v="143.0.7499.146", "Chromium";v="143.0.7499.146", "Not A(Brand";v="24.0.0.0"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": '"Linux"',
            "sec-ch-ua-platform-version": '"6.17.0"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": self.USER_AGENT
        }
        
        time.sleep(0.5)
        response = self._make_request(self.GRAPHQL_URL, headers, payload, "Lifetime Stats")
        
        if response:
            logger.info(f"✅ Successfully fetched lifetime stats for post {post_id}")
        else:
            logger.error(f"❌ Failed to fetch lifetime stats for post {post_id}")
        
        return response
    
    # ============================================
    # RESPONSE PARSERS
    # ============================================
    
    def parse_stats_response(self, data: Any, post_id: str) -> Dict[str, Any]:
        """
        Parse the monthly stats response into usable format.
        
        Maps Medium API fields to database fields:
        - data.post.earnings.dailyEarnings[].amount -> earnings (sum in cents)
        - readersThatReadCount (MEMBER) -> member_reads
        - readersThatReadCount (NONMEMBER) -> nonmember_reads
        - readersThatViewedCount (MEMBER) -> member_views
        - readersThatViewedCount (NONMEMBER) -> nonmember_views
        - readersThatClappedCount -> claps
        - readersThatRepliedCount -> responses
        """
        result = {
            'post_id': post_id,
            'fetch_timestamp': datetime.now().isoformat(),
            'title': None,
            'first_published': None,
            'reading_time': 0,
            'word_count': 0,
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
                'earnings': 0,
                'read_ratio': 0,
                'member_read_percentage': 0
            }
        }
        
        if isinstance(data, list) and len(data) > 0:
            response_item = data[0]
            
            if 'data' in response_item:
                stats_data = response_item.get('data', {})
                
                # Parse post metadata and earnings
                post_obj = stats_data.get('post', {})
                if post_obj:
                    result['title'] = post_obj.get('title')
                    
                    first_published = post_obj.get('firstPublishedAt') or post_obj.get('createdAt')
                    if first_published and isinstance(first_published, (int, float)):
                        result['first_published'] = datetime.fromtimestamp(first_published / 1000).isoformat()
                    
                    reading_time = post_obj.get('readingTime')
                    result['reading_time'] = int(round(reading_time)) if reading_time else 0
                    result['word_count'] = post_obj.get('wordCount') or 0
                    
                    # Parse earnings from dailyEarnings array
                    earnings = post_obj.get('earnings', {})
                    daily_earnings = earnings.get('dailyEarnings', [])
                    total_earnings = sum(e.get('amount', 0) for e in daily_earnings)
                    result['totals']['earnings'] = total_earnings
                    
                    if daily_earnings:
                        amounts = [e.get('amount', 0) for e in daily_earnings]
                        logger.info(f"💰 Earnings for {post_id}: {len(daily_earnings)} days, amounts={amounts}, total={total_earnings} cents (${total_earnings/100:.2f})")
                    else:
                        logger.info(f"💰 No earnings data for {post_id}")
                
                # Parse daily buckets
                post_stats = stats_data.get('postStatsDailyBundle', {})
                buckets = post_stats.get('buckets', [])
                
                for bucket in buckets:
                    membership = bucket.get('membershipType', 'UNKNOWN')
                    
                    reads = bucket.get('readersThatReadCount', 0)
                    views = bucket.get('readersThatViewedCount', 0)
                    claps = bucket.get('readersThatClappedCount', 0)
                    replies = bucket.get('readersThatRepliedCount', 0)
                    highlights = bucket.get('readersThatHighlightedCount', 0)
                    new_followers = bucket.get('readersThatInitiallyFollowedAuthorFromThisPostCount', 0)
                    
                    if membership == 'MEMBER':
                        result['totals']['member_reads'] += reads
                        result['totals']['member_views'] += views
                    elif membership == 'NONMEMBER':
                        result['totals']['nonmember_reads'] += reads
                        result['totals']['nonmember_views'] += views
                    
                    result['totals']['total_reads'] += reads
                    result['totals']['total_views'] += views
                    result['totals']['claps'] += claps
                    result['totals']['replies'] += replies
                    result['totals']['highlights'] += highlights
                    result['totals']['new_followers'] += new_followers
        
        # Calculate percentages
        if result['totals']['total_views'] > 0:
            result['totals']['read_ratio'] = round(
                result['totals']['total_reads'] / result['totals']['total_views'] * 100, 1
            )
        
        if result['totals']['total_reads'] > 0:
            result['totals']['member_read_percentage'] = round(
                result['totals']['member_reads'] / result['totals']['total_reads'] * 100, 1
            )
        
        self._debug_print("Parsed Stats", {
            "post_id": result['post_id'],
            "earnings_cents": result['totals']['earnings'],
            "earnings_dollars": f"${result['totals']['earnings']/100:.2f}",
            "totals": result['totals']
        })
        
        return result
    
    def parse_lifetime_response(self, data: Any, post_id: str) -> Dict[str, Any]:
        """
        Parse the lifetime stats response into usable format.
        
        Maps:
        - data.postStatsTotalBundle.readersCount -> lifetime_reads
        - data.postStatsTotalBundle.viewersCount -> lifetime_views
        - data.postStatsTotalBundle.presentationCount -> presentation_count
        - data.postStatsTotalBundle.feedClickThroughRate -> feed_click_through_rate
        """
        result = {
            'lifetime_reads': 0,
            'lifetime_views': 0,
            'presentation_count': 0,
            'feed_click_through_rate': 0.0
        }
        
        if isinstance(data, list) and len(data) > 0:
            response_item = data[0]
            
            if 'data' in response_item:
                bundle_data = response_item.get('data', {}).get('postStatsTotalBundle', {})
                if bundle_data:
                    result['lifetime_reads'] = bundle_data.get('readersCount', 0)
                    result['lifetime_views'] = bundle_data.get('viewersCount', 0)
                    result['presentation_count'] = bundle_data.get('presentationCount', 0)
                    result['feed_click_through_rate'] = bundle_data.get('feedClickThroughRate', 0.0)
        
        self._debug_print("Parsed Lifetime Stats", result)
        
        return result


# ============================================
# SINGLETON INSTANCE
# ============================================

_medium_api_service = None

def get_medium_api_service() -> MediumAPIService:
    """Get singleton instance of MediumAPIService"""
    global _medium_api_service
    if _medium_api_service is None:
        _medium_api_service = MediumAPIService()
    return _medium_api_service


def set_debug_mode(enabled: bool = True):
    """Enable or disable debug mode globally"""
    global DEBUG
    DEBUG = enabled
    print(f"🔍 Medium API Debug mode: {'ON' if DEBUG else 'OFF'}")


# ============================================
# USAGE EXAMPLES
# ============================================

"""
HOW TO USE:

1. With Chrome cookies (recommended):
   - Open Chrome and log into medium.com
   - Keep Chrome OPEN
   - Run: python -c "from app.services.medium_api_service import get_medium_api_service; s = get_medium_api_service(); print(s.is_authenticated())"

2. With environment variables:
   export MEDIUM_COOKIE='sid=xxx; uid=xxx; xsrf=xxx'
   OR
   export MEDIUM_SID='1:xxxxx'
   export MEDIUM_UID='6a63927f9b83'
   
3. Test API call:
   curl -X POST "http://localhost:8000/api/stories/fetch-story-stats/78cb972195da/2026-04" | jq '.stats.totals.earnings'

4. Enable debug mode:
   export MEDIUM_API_DEBUG=true
   uvicorn app.main:app --reload

EXPECTED OUTPUT for story with earnings:
{
  "earnings": 57,
  "earnings_dollars": "$0.57",
  "member_reads": 38,
  "member_views": 76,
  ...
}
"""