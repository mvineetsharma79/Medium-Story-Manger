"""
Medium API Service - Pure API client for Medium GraphQL calls
"""

import os
import json
import requests
import sqlite3
import tempfile
import shutil
import time
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import calendar
import re

logger = logging.getLogger(__name__)

# ============================================
# DEBUG SETTINGS
# ============================================
DEBUG = os.environ.get("MEDIUM_API_DEBUG", "false").lower() == "true"


class MediumAPIService:
    """
    Service to make direct GraphQL calls to Medium API.
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
    # COOKIE EXTRACTION
    # ============================================
    
    def _get_chrome_cookies(self) -> Optional[Dict[str, str]]:
        """Extract Medium cookies from Chrome on Linux"""
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
                    
                    cookies = {}
                    for name, value in cursor.fetchall():
                        if value:
                            cookies[name] = value
                    
                    conn.close()
                    os.unlink(temp_db.name)
                    
                    if cookies.get('sid') and cookies.get('uid'):
                        self._debug_print("Cookies extracted from Chrome", {
                            k: v[:20] + "..." if len(v) > 20 else v 
                            for k, v in cookies.items()
                        })
                        logger.info(f"✅ Found {len(cookies)} cookies from Chrome")
                        return cookies
                        
                except Exception as e:
                    logger.debug(f"Could not read cookies from {cookie_path}: {e}")
                    continue
        
        return None
    
    def _get_cookies_from_env(self) -> Optional[Dict[str, str]]:
        """Get cookies from environment variables"""
        cookie_string = os.environ.get("MEDIUM_COOKIE")
        if cookie_string:
            cookies = {}
            for item in cookie_string.split('; '):
                if '=' in item:
                    key, value = item.split('=', 1)
                    if value:
                        cookies[key] = value
            if cookies.get('sid') and cookies.get('uid'):
                return cookies
        
        sid = os.environ.get("MEDIUM_SID")
        uid = os.environ.get("MEDIUM_UID")
        if sid and uid:
            return {"sid": sid, "uid": uid}
        
        return None
    
    def _load_cookies(self):
        """Load cookies with priority: Chrome -> Environment"""
        print("\n" + "=" * 60)
        print("🍪 LOADING COOKIES")
        print("=" * 60)
        
        self.cookies = self._get_chrome_cookies()
        
        if not self.cookies:
            self.cookies = self._get_cookies_from_env()
        
        if not self.cookies:
            logger.warning("=" * 60)
            logger.warning("⚠️ No cookies found!")
            logger.warning("Open Chrome and log into medium.com, then restart")
            logger.warning("=" * 60)
        else:
            logger.info(f"✅ Loaded {len(self.cookies)} cookies")
        
        print("=" * 60 + "\n")
    
    def is_authenticated(self) -> bool:
        """Check if we have valid cookies"""
        return self.cookies is not None and self.cookies.get('sid') is not None
    
    # ============================================
    # UTILITY METHODS
    # ============================================
    
    def get_month_timestamps(self, year: int, month: int) -> tuple:
        """Get start and end timestamps for a month (start of month to start of next month)"""
        start_date = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
        start_at = int(start_date.timestamp() * 1000)
        
        if month == 12:
            end_date = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        else:
            end_date = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_at = int(end_date.timestamp() * 1000)
        
        return start_at, end_at
    
    # ============================================
    # COMMON REQUEST METHOD
    # ============================================
    
    def _make_request(self, url: str, headers: Dict, payload: List[Dict], request_type: str) -> Optional[Dict]:
        """Make HTTP request with debug logging and explicit cookie header"""
        self._debug_print(f"{request_type} Request Headers", headers)
        self._debug_print(f"{request_type} Request Payload", payload)
        # self._debug_print(f"{request_type} Cookies", self.cookies)
        
        if self.cookies:
            cookie_string = "; ".join([f"{k}={v}" for k, v in self.cookies.items() if v])
            headers["cookie"] = cookie_string
     
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                self._debug_print(f"{request_type} Response", response_data)
                with open('./data/mediumresponse.json', 'w') as file:
                    file.write(response.text)
                    #json.dump(response, file)
                return response_data
            else:
                self._debug_print(f"{request_type} Error", {"status": response.status_code, "text": response.text[:500]})
                return None
        except Exception as e:
            self._debug_print(f"{request_type} Exception", {"error": str(e)})
            return None
    
    # ============================================
    # COMMON GRAPHQL REQUEST BUILDER
    # ============================================
    
    def _build_graphql_request(self, operation_name: str, variables: Dict, query: str, 
                                path: str, route: str) -> List[Dict]:
        """Build a GraphQL request payload"""
        return [{
            "operationName": operation_name,
            "variables": variables,
            "query": query
        }]
    
    def _get_common_headers(self, post_id: str = None, operation: str = None) -> Dict:
        """Get common headers for Medium API requests"""
        headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "apollographql-client-name": "lite",
            "apollographql-client-version": "main-20260403-204212-a07bb9cfad",
            "content-type": "application/json",
            "origin": "https://medium.com",
            "priority": "u=1, i",
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
        
        if operation:
            headers["graphql-operation"] = operation
        
        if post_id:
            headers["medium-frontend-app"] = "lite/main-20260403-204212-a07bb9cfad"
            headers["medium-frontend-path"] = f"/me/stats/post/{post_id}"
            headers["medium-frontend-route"] = "stats-post"
            headers["referer"] = f"https://medium.com/me/stats/post/{post_id}"
        
        return headers
    
    # ============================================
    # MONTHLY STATS (for single story)
    # ============================================
    
    def get_story_metadata_medium(self, post_id: str, year: int, month: int) -> Optional[Dict]:
        """Fetch monthly stats for a specific story and month"""
        if not self.is_authenticated():
            logger.warning("Not authenticated. Cannot fetch stats.")
            return None
        
        start_at, end_at = self.get_month_timestamps(year, month)
        
        query = """query useStatsPostNewChartDataQuery(
        $postId: ID!
        $startAt: Long!
        $endAt: Long!
        $postStatsDailyBundleInput: PostStatsDailyBundleInput!
        ) {
        post(id: $postId) {
            id
            earnings {
            dailyEarnings(startAt: $startAt, endAt: $endAt) {
                periodStartedAt
                amount
            }
            }
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
            }
        }
        }
        }"""
        
        variables = {
            "postId": post_id,
            "startAt": start_at,
            "endAt": end_at,
            "postStatsDailyBundleInput": {
                "postId": post_id,
                "fromDayStartsAt": start_at,
                "toDayStartsAt": end_at
            }
        }
        
        payload = self._build_graphql_request("useStatsPostNewChartDataQuery", variables, query, post_id, "stats-post")
        headers = self._get_common_headers(post_id, "useStatsPostNewChartDataQuery")
        
        time.sleep(0.5)
        return self._make_request(self.GRAPHQL_URL, headers, payload, f"Monthly Stats {year}-{month:02d}")
    
    # ============================================
    # Get Earninngs
    # ============================================

    def  get_story_earnings_medium(self, username, first=10, after="", start_at=None, end_at=None):
        """
        Fetch story earnings for posts within a specific date range
        
        Args:
            username (str): The Medium username
            first (int): Number of posts to fetch (default: 10)
            after (str): Cursor for pagination
            start_at (int): Start timestamp in milliseconds (optional, defaults to current month start)
            end_at (int): End timestamp in milliseconds (optional, defaults to current date)
        
        Returns:
            dict: Story earnings data including monthly and lifetime earnings per post
        """
        from datetime import datetime, timedelta
        end_at= 1775001600000
        # Set default date range if not provided (current month to date)
        if end_at is None:
            end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_at = int(end_date.timestamp() * 1000)
        start_at = 1772323200000
        if start_at is None:
            # Start of current month
            start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            start_at = int(start_date.timestamp() * 1000)
        
        query = """query StoryEarningsQuery($username: ID!, $first: Int!, $after: String!, $startAt: Long!, $endAt: Long!) {
        userResult(username: $username) {
            ... on User {
            id
            username
            name
            
            postsConnection(
                first: $first
                after: $after
                orderBy: {lifetimeEarnings: DESC}
                filter: {published: true}
                timeRange: {startAt: $startAt, endAt: $endAt}
            ) {
                edges {
                node {
                    # Identification
                    id
                    __typename
                    title
                    uniqueSlug
                    mediumUrl
                    
                    # Dates
                    createdAt
                    updatedAt
                    firstPublishedAt
                    
                    # Total
                    totalStats {
                        presentations  # Impressions
                        views         # Clicks
                        reads         # Full reads
                        __typename
                    }                    
                    # Metrics
                    readingTime
                    wordCount
                    clapCount
                    responsesCount
                    voterCount
                    
                    # Status
                    isLocked
                    visibility
                    isSeries
                    isShortform
                    firstBoostedAt
                    license
                    
                    # Tags
                    tags {
                    id
                    }
                    
                    # Earnings
                    earnings {
                    total {
                        currencyCode
                        units
                        nanos
                    }
                    monthlyEarnings: total(input: {between: {startAt: $startAt, endAt: $endAt}}) {
                        currencyCode
                        units
                        nanos
                    }
                    }

                    # Author (removed updatedAt)
                    creator {
                    id
                    username
                    name
                    bio
                    imageId
                    twitterScreenName
                    createdAt
                    # updatedAt - removed (doesn't exist on User)
                    }
                    
                    # Publication (removed updatedAt)
                    collection {
                    id
                    name
                    slug
                    domain
                    subscriberCount
                    createdAt
                    # updatedAt - removed (doesn't exist on Collection)
                    }
                    
                    __typename
                }
                cursor
                }
                pageInfo {
                endCursor
                hasNextPage
                }
            }
            }
        }
        }
        """
        
        variables = {
            "username": username,
            "first": first,
            "after": after,
            "startAt": start_at,
            "endAt": end_at
        }
        
        payload = self._build_graphql_request("StoryEarningsQuery", variables, query, username, "stats-post")
        headers = self._get_common_headers(username, "StoryEarningsQuery")

        time.sleep(0.5)
        output_json = self._make_request(self.GRAPHQL_URL, headers, payload, "Lifetime ALL Stats") 
            

        return output_json
    

    
    # ============================================
    # RESPONSE PARSERS
    # ============================================
    
    def parse_stats_response(self, data: Any, post_id: str) -> Dict[str, Any]:
        """Parse monthly stats response"""
        result = {
            'post_id': post_id,
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
                'earnings': 0
            }
        }
        
        if isinstance(data, list) and len(data) > 0:
            response_item = data[0]
            
            if 'data' in response_item:
                stats_data = response_item.get('data', {})
                
                # Parse earnings
                post_obj = stats_data.get('post', {})
                if post_obj:
                    earnings = post_obj.get('earnings', {})
                    daily_earnings = earnings.get('dailyEarnings', [])
                    result['totals']['earnings'] = sum(e.get('amount', 0) for e in daily_earnings)
                
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
        
        return result
    
    def parse_lifetime_response(self, data: Any, post_id: str) -> Dict[str, Any]:
        """Parse lifetime stats response"""
        result = {
            'lifetime_reads': 0,
            'lifetime_views': 0,
            'presentation_count': 0,
            'feed_click_through_rate': 0
        }
        
        if isinstance(data, list) and len(data) > 0:
            response_item = data[0]
            
            if 'data' in response_item:
                bundle_data = response_item.get('data', {}).get('postStatsTotalBundle', {})
                if bundle_data:
                    result['lifetime_reads'] = bundle_data.get('readersCount', 0)
                    result['lifetime_views'] = bundle_data.get('viewersCount', 0)
                    result['presentation_count'] = bundle_data.get('presentationCount', 0)
                    result['feed_click_through_rate'] = bundle_data.get('feedClickThroughRate', 0)
        
        return result


# ============================================
# SINGLETON INSTANCE
# ============================================

_medium_api_service = None

def get_medium_api_service() -> MediumAPIService:
    global _medium_api_service
    if _medium_api_service is None:
        _medium_api_service = MediumAPIService()
    return _medium_api_service


def set_debug_mode(enabled: bool = True):
    global DEBUG
    DEBUG = enabled
    print(f"🔍 Medium API Debug mode: {'ON' if DEBUG else 'OFF'}")
