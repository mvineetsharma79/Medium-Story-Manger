"""
Medium API Service - Pure API client for Medium GraphQL calls
Each method includes source comments and curl equivalents
"""

import os
import json
import requests
import sqlite3
import tempfile
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# ============================================
# DEBUG SETTINGS
# ============================================
DEBUG = os.environ.get("MEDIUM_API_DEBUG", "false").lower() == "true"


class MediumAPIService:
    """
    Service to make direct GraphQL calls to Medium API.
    
    GraphQL Endpoint: POST https://medium.com/_/graphql
    
    Available Operations:
    1. useStatsPostNewChartDataQuery - Monthly stats
    2. StatsPostFunnelQuery - Lifetime stats
    3. StoryEarningsQuery - Leaderboard earnings
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
    # COOKIE MANAGEMENT
    # ============================================
    
    def _get_chrome_cookies_linux(self) -> Optional[Dict[str, str]]:
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
                    cookies = {name: value for name, value in cursor.fetchall()}
                    conn.close()
                    os.unlink(temp_db.name)
                    
                    if cookies and 'sid' in cookies:
                        self._debug_print("Cookies extracted from Chrome", cookies)
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
                        self._debug_print("Cookies extracted from Firefox", cookies)
                        logger.info(f"✅ Found {len(cookies)} cookies from Firefox")
                        return cookies
                except Exception as e:
                    logger.debug(f"Could not read Firefox cookies: {e}")
                    continue
        
        return None
    
    def _load_cookies(self):
        """Load cookies from browser"""
        import platform
        system = platform.system()
        
        logger.info(f"Detected OS: {system}")
        
        if system == "Linux":
            self.cookies = self._get_chrome_cookies_linux()
            if not self.cookies:
                self.cookies = self._get_firefox_cookies()
        elif system == "Darwin":
            self.cookies = self._get_chrome_cookies_linux()
            if not self.cookies:
                self.cookies = self._get_firefox_cookies()
        else:
            logger.warning(f"Automatic cookie extraction not fully supported on {system}")
        
        if not self.cookies:
            logger.warning("Could not load cookies from browser")
        else:
            logger.info(f"🍪 Loaded cookies: {list(self.cookies.keys())}")
    
    def is_authenticated(self) -> bool:
        """Check if we have valid cookies"""
        return self.cookies is not None and 'sid' in self.cookies
    
    # ============================================
    # UTILITY METHODS
    # ============================================
    
    def extract_post_id_from_url(self, medium_url: str) -> Optional[str]:
        """
        Extract post ID from Medium URL
        Example: https://medium.com/@username/post-title-78cb972195da -> 78cb972195da
        """
        if not medium_url:
            return None
        
        url = medium_url.rstrip('/')
        parts = url.split('/')
        last_part = parts[-1]
        
        if '-' in last_part:
            post_id = last_part.split('-')[-1]
            if len(post_id) >= 10:
                self._debug_print(f"Extracted post ID from URL", {"url": medium_url, "post_id": post_id})
                return post_id
        
        if len(last_part) >= 10:
            self._debug_print(f"Extracted post ID from URL", {"url": medium_url, "post_id": last_part})
            return last_part
        
        return None
    
    def get_session(self) -> requests.Session:
        """Get authenticated session with cookies"""
        session = requests.Session()
        if self.cookies:
            for name, value in self.cookies.items():
                session.cookies.set(name, value, domain=".medium.com", path="/")
        return session
    
    # ============================================
    # GRAPHQL PAYLOAD BUILDERS
    # ============================================
    
    def build_stats_payload(self, post_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Build GraphQL payload for monthly stats query.
        
        Operation: useStatsPostNewChartDataQuery
        Returns: Post metadata + daily buckets (reads, views, claps, replies, highlights, followers)
        """
        start_at = int(start_date.timestamp() * 1000)
        end_at = int(end_date.timestamp() * 1000)
        
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
            "query": """query useStatsPostNewChartDataQuery($postId: ID!, $startAt: Long!, $endAt: Long!, $postStatsDailyBundleInput: PostStatsDailyBundleInput!) {
  post(id: $postId) {
    id
    title
    createdAt
    firstPublishedAt
    updatedAt
    readingTime
    wordCount
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
        
        self._debug_print("Monthly Stats Payload", {
            "post_id": post_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "payload": payload
        })
        
        return payload
    
    def build_lifetime_payload(self, post_id: str) -> List[Dict]:
        """
        Build GraphQL payload for lifetime stats query.
        
        Operation: StatsPostFunnelQuery
        Returns: readersCount, viewersCount, presentationCount, feedClickThroughRate
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
        
        self._debug_print("Lifetime Stats Payload", {
            "post_id": post_id,
            "payload": payload
        })
        
        return payload
    
    def build_leaderboard_payload(self, username: str, start_at: int, end_at: int) -> List[Dict]:
        """
        Build GraphQL payload for leaderboard earnings query.
        
        Operation: StoryEarningsQuery
        Returns: List of stories with monthly earnings (nanos)
        """
        payload = [{
            "operationName": "StoryEarningsQuery",
            "variables": {
                "username": username,
                "first": 50,
                "after": "",
                "startAt": start_at,
                "endAt": end_at
            },
            "query": """query StoryEarningsQuery($username: ID!, $first: Int!, $after: String!, $startAt: Long!, $endAt: Long!) {
                userResult(username: $username) {
                    __typename
                    ... on User {
                        id
                        postsConnection(
                            first: $first
                            after: $after
                            orderBy: {lifetimeEarnings: DESC}
                            filter: {published: true}
                            timeRange: {startAt: $startAt, endAt: $endAt}
                        ) {
                            edges {
                                node {
                                    id
                                    firstPublishedAt
                                    earnings {
                                        monthlyEarnings: total(input: {between: {startAt: $startAt, endAt: $endAt}}) {
                                            currencyCode
                                            nanos
                                            units
                                        }
                                    }
                                    title
                                    mediumUrl
                                }
                            }
                            pageInfo {
                                hasNextPage
                                endCursor
                            }
                        }
                    }
                }
            }"""
        }]
        
        self._debug_print("Leaderboard Payload", {
            "username": username,
            "start_at": start_at,
            "end_at": end_at,
            "payload": payload
        })
        
        return payload
    
    # ============================================
    # API CALLS
    # ============================================
    
    def _make_request(self, url: str, headers: Dict, payload: List[Dict], request_type: str) -> Optional[Dict]:
        """Make HTTP request with debug logging"""
        self._debug_print(f"{request_type} Request Headers", headers)
        self._debug_print(f"{request_type} Request Payload", payload)
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            self._debug_print(f"{request_type} Response Status", {
                "status_code": response.status_code,
                "reason": response.reason
            })
            
            if response.status_code == 200:
                response_data = response.json()
                self._debug_print(f"{request_type} Response Body (Full)", response_data)
                return response_data
            else:
                self._debug_print(f"{request_type} Error Response", {
                    "status_code": response.status_code,
                    "text": response.text
                })
                return None
        except Exception as e:
            self._debug_print(f"{request_type} Exception", {"error": str(e)})
            return None
    
    def fetch_stats(self, post_id: str, start_date: datetime, end_date: datetime) -> Optional[Dict]:
        """
        Fetch monthly stats for a date range.
        
        Source: POST https://medium.com/_/graphql
        Operation: useStatsPostNewChartDataQuery
        
        curl equivalent (internal, not directly callable):
        curl -X POST https://medium.com/_/graphql \\
          -H "Content-Type: application/json" \\
          -H "graphql-operation: useStatsPostNewChartDataQuery" \\
          -d '{"operationName":"useStatsPostNewChartDataQuery",...}'
        """
        if not self.is_authenticated():
            logger.warning("Not authenticated. Cannot fetch stats.")
            return None
        
        payload = self.build_stats_payload(post_id, start_date, end_date)
        
        headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "apollographql-client-name": "lite",
            "apollographql-client-version": "main-20260401-140543-04b3dba818",
            "content-type": "application/json",
            "graphql-operation": "useStatsPostNewChartDataQuery",
            "origin": "https://medium.com",
            "referer": f"https://medium.com/me/stats/post/{post_id}",
            "user-agent": self.USER_AGENT
        }
        
        time.sleep(0.5)  # Rate limiting
        response = self._make_request(self.GRAPHQL_URL, headers, payload, "Monthly Stats")
        
        if response:
            logger.info(f"✅ Successfully fetched monthly stats for post {post_id}")
            self._debug_print("Monthly Stats Summary", self._format_monthly_stats_summary(response, post_id))
        else:
            logger.error(f"❌ Failed to fetch monthly stats for post {post_id}")
        
        return response
    
    def fetch_lifetime_stats(self, post_id: str) -> Optional[Dict]:
        """
        Fetch lifetime stats for a story.
        
        Source: POST https://medium.com/_/graphql
        Operation: StatsPostFunnelQuery
        
        curl equivalent (internal, not directly callable):
        curl -X POST https://medium.com/_/graphql \\
          -H "Content-Type: application/json" \\
          -H "graphql-operation: StatsPostFunnelQuery" \\
          -d '{"operationName":"StatsPostFunnelQuery",...}'
        """
        if not self.is_authenticated():
            logger.warning("Not authenticated. Cannot fetch lifetime stats.")
            return None
        
        payload = self.build_lifetime_payload(post_id)
        
        headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "apollographql-client-name": "lite",
            "apollographql-client-version": "main-20260402-153718-3db94ea7f3",
            "content-type": "application/json",
            "graphql-operation": "StatsPostFunnelQuery",
            "origin": "https://medium.com",
            "referer": f"https://medium.com/me/stats/post/{post_id}",
            "user-agent": self.USER_AGENT
        }
        
        time.sleep(0.5)
        response = self._make_request(self.GRAPHQL_URL, headers, payload, "Lifetime Stats")
        
        if response:
            logger.info(f"✅ Successfully fetched lifetime stats for post {post_id}")
            self._debug_print("Lifetime Stats Summary", self._format_lifetime_stats_summary(response, post_id))
        else:
            logger.error(f"❌ Failed to fetch lifetime stats for post {post_id}")
        
        return response
    
    def fetch_leaderboard_earnings(self, username: str, year: int, month: int) -> Optional[List[Dict]]:
        """
        Fetch monthly earnings for leaderboard.
        
        Source: POST https://medium.com/_/graphql
        Operation: StoryEarningsQuery
        
        curl equivalent (internal, not directly callable):
        curl -X POST https://medium.com/_/graphql \\
          -H "Content-Type: application/json" \\
          -H "graphql-operation: StoryEarningsQuery" \\
          -d '{"operationName":"StoryEarningsQuery",...}'
        """
        if not self.is_authenticated():
            logger.warning("Not authenticated. Cannot fetch earnings.")
            return None
        
        start_of_month = datetime(year, month, 1, 0, 0, 0)
        if month == 12:
            end_of_month = datetime(year + 1, 1, 1, 0, 0, 0) - timedelta(seconds=1)
        else:
            end_of_month = datetime(year, month + 1, 1, 0, 0, 0) - timedelta(seconds=1)
        
        start_at = int(start_of_month.timestamp() * 1000)
        end_at = int(end_of_month.timestamp() * 1000)
        
        payload = self.build_leaderboard_payload(username, start_at, end_at)
        
        headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "apollographql-client-name": "lite",
            "apollographql-client-version": "main-20260402-184826-712bc227d8",
            "content-type": "application/json",
            "graphql-operation": "StoryEarningsQuery",
            "origin": "https://medium.com",
            "referer": "https://medium.com/me/partner/dashboard",
            "user-agent": self.USER_AGENT
        }
        
        time.sleep(0.5)
        response = self._make_request(self.GRAPHQL_URL, headers, payload, "Leaderboard Earnings")
        
        if not response:
            logger.error("Failed to fetch earnings")
            return None
        
        if response and len(response) > 0:
            if 'errors' in response[0]:
                self._debug_print("GraphQL Errors", response[0]['errors'])
                logger.error(f"GraphQL Errors: {response[0]['errors']}")
                return []
            
            user_result = response[0].get('data', {}).get('userResult', {})
            
            if user_result and user_result.get('__typename') == 'User':
                posts_connection = user_result.get('postsConnection', {})
                edges = posts_connection.get('edges', [])
                
                results = []
                for edge in edges:
                    node = edge.get('node', {})
                    earnings = node.get('earnings', {})
                    monthly_earnings = earnings.get('monthlyEarnings', {})
                    
                    nanos = monthly_earnings.get('nanos', 0)
                    results.append({
                        'title': node.get('title'),
                        'medium_url': node.get('mediumUrl'),
                        'first_published_at': node.get('firstPublishedAt'),
                        'nanos': nanos,
                        'currency': monthly_earnings.get('currencyCode', 'USD')
                    })
                
                self._debug_print("Parsed Leaderboard Results", {
                    "count": len(results),
                    "results": results[:10]
                })
                
                return results
        
        return None
    
    # ============================================
    # RESPONSE PARSERS
    # ============================================
    
    def _format_monthly_stats_summary(self, data: Any, post_id: str) -> Dict[str, Any]:
        """Extract and format monthly stats summary for debug output"""
        summary = {
            "post_id": post_id,
            "title": None,
            "totals": {
                "member_reads": 0,
                "member_views": 0,
                "nonmember_reads": 0,
                "nonmember_views": 0,
                "total_reads": 0,
                "total_views": 0,
                "claps": 0,
                "replies": 0,
                "highlights": 0,
                "new_followers": 0
            }
        }
        
        if isinstance(data, list) and len(data) > 0:
            response_item = data[0]
            
            if 'data' in response_item:
                stats_data = response_item.get('data', {})
                
                post_obj = stats_data.get('post', {})
                if post_obj:
                    summary['title'] = post_obj.get('title')
                
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
                        summary['totals']['member_reads'] += reads
                        summary['totals']['member_views'] += views
                    elif membership == 'NONMEMBER':
                        summary['totals']['nonmember_reads'] += reads
                        summary['totals']['nonmember_views'] += views
                    
                    summary['totals']['total_reads'] += reads
                    summary['totals']['total_views'] += views
                    summary['totals']['claps'] += claps
                    summary['totals']['replies'] += replies
                    summary['totals']['highlights'] += highlights
                    summary['totals']['new_followers'] += new_followers
        
        if summary['totals']['total_views'] > 0:
            summary['totals']['read_ratio'] = round(
                summary['totals']['total_reads'] / summary['totals']['total_views'] * 100, 1
            )
        
        if summary['totals']['total_reads'] > 0:
            summary['totals']['member_read_percentage'] = round(
                summary['totals']['member_reads'] / summary['totals']['total_reads'] * 100, 1
            )
        
        return summary
    
    def _format_lifetime_stats_summary(self, data: Any, post_id: str) -> Dict[str, Any]:
        """Extract and format lifetime stats summary for debug output"""
        summary = {
            "post_id": post_id,
            "lifetime_reads": 0,
            "lifetime_views": 0,
            "presentation_count": 0,
            "feed_click_through_rate": 0
        }
        
        if isinstance(data, list) and len(data) > 0:
            response_item = data[0]
            
            if 'data' in response_item:
                bundle_data = response_item.get('data', {}).get('postStatsTotalBundle', {})
                if bundle_data:
                    summary['lifetime_reads'] = bundle_data.get('readersCount', 0)
                    summary['lifetime_views'] = bundle_data.get('viewersCount', 0)
                    summary['presentation_count'] = bundle_data.get('presentationCount', 0)
                    summary['feed_click_through_rate'] = bundle_data.get('feedClickThroughRate', 0)
        
        return summary
    
    def parse_stats_response(self, data: Any, post_id: str) -> Dict[str, Any]:
        """
        Parse the monthly stats response into usable format.
        
        Maps Medium API fields to database fields:
        - readersThatReadCount (MEMBER) -> medium_member_reads
        - readersThatReadCount (NONMEMBER) -> medium_nonmember_reads
        - readersThatViewedCount (MEMBER) -> medium_member_views
        - readersThatViewedCount (NONMEMBER) -> medium_nonmember_views
        - readersThatClappedCount -> claps
        - readersThatRepliedCount -> responses
        - readersThatHighlightedCount -> medium_highlights
        - readersThatInitiallyFollowedAuthorFromThisPostCount -> medium_new_followers
        - sum(dailyEarnings[].amount) -> medium_earnings
        """
        result = {
            'post_id': post_id,
            'fetch_timestamp': datetime.now().isoformat(),
            'title': None,
            'first_published': None,
            'last_updated': None,
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
                'read_ratio': 0,
                'member_read_percentage': 0,
                'earnings': 0.0
            }
        }
        
        if isinstance(data, list) and len(data) > 0:
            response_item = data[0]
            
            if 'data' in response_item:
                stats_data = response_item.get('data', {})
                
                # Parse post metadata
                post_obj = stats_data.get('post', {})
                if post_obj:
                    result['title'] = post_obj.get('title')
                    
                    first_published = post_obj.get('firstPublishedAt') or post_obj.get('createdAt')
                    if first_published and isinstance(first_published, (int, float)):
                        result['first_published'] = datetime.fromtimestamp(first_published / 1000).isoformat()
                    
                    last_updated = post_obj.get('updatedAt')
                    if last_updated and isinstance(last_updated, (int, float)):
                        result['last_updated'] = datetime.fromtimestamp(last_updated / 1000).isoformat()
                    
                    reading_time = post_obj.get('readingTime')
                    result['reading_time'] = int(round(reading_time)) if reading_time else 0
                    result['word_count'] = post_obj.get('wordCount') or 0
                    
                    # Parse earnings
                    earnings = post_obj.get('earnings', {})
                    daily_earnings = earnings.get('dailyEarnings', [])
                    total_earnings = sum(e.get('amount', 0) for e in daily_earnings)
                    result['totals']['earnings'] = total_earnings
                
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
        
        if result['totals']['total_views'] > 0:
            result['totals']['read_ratio'] = round(
                result['totals']['total_reads'] / result['totals']['total_views'] * 100, 1
            )
        
        if result['totals']['total_reads'] > 0:
            result['totals']['member_read_percentage'] = round(
                result['totals']['member_reads'] / result['totals']['total_reads'] * 100, 1
            )
        
        self._debug_print("Parsed Monthly Stats", {
            "post_id": result['post_id'],
            "title": result['title'],
            "totals": result['totals']
        })
        
        return result
    
    def parse_lifetime_response(self, data: Any, post_id: str) -> Dict[str, Any]:
        """
        Parse the lifetime stats response into usable format.
        
        Maps Medium API fields to database fields:
        - readersCount -> lifetime_reads
        - viewersCount -> lifetime_views
        - presentationCount -> presentation_count
        - feedClickThroughRate -> feed_click_through_rate
        """
        result = {
            'post_id': post_id,
            'fetch_timestamp': datetime.now().isoformat(),
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
        
        self._debug_print("Parsed Lifetime Stats", {
            "post_id": result['post_id'],
            "lifetime_reads": result['lifetime_reads'],
            "lifetime_views": result['lifetime_views'],
            "presentation_count": result['presentation_count'],
            "feed_click_through_rate": result['feed_click_through_rate']
        })
        
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