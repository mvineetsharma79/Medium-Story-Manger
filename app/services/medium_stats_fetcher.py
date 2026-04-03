"""
Medium Stats Fetcher - Uses browser cookies to fetch authenticated stats
"""

import requests
import json
import sqlite3
import os
import tempfile
import shutil
import time
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class MediumStatsFetcher:
    """Fetch detailed statistics from Medium using browser cookies"""
    
    def __init__(self):
        self.cookies = None
        self._load_cookies()
    
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
    
    def extract_post_id_from_url(self, medium_url: str) -> Optional[str]:
        """Extract post ID from Medium URL"""
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
    
    def _get_headers_for_current_month(self, post_id: str) -> Dict[str, str]:
        """Generate headers for the current month stats GraphQL request"""
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
    
    def _get_headers_for_lifetime(self, post_id: str) -> Dict[str, str]:
        """Generate headers for the lifetime stats GraphQL request"""
        return {
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "apollographql-client-name": "lite",
            "apollographql-client-version": "main-20260402-153718-3db94ea7f3",
            "content-type": "application/json",
            "graphql-operation": "StatsPostFunnelQuery",
            "medium-frontend-app": "lite/main-20260402-153718-3db94ea7f3",
            "medium-frontend-path": f"/me/stats/post/{post_id}",
            "medium-frontend-route": "stats-post",
            "origin": "https://medium.com",
            "priority": "u=1, i",
            "referer": f"https://medium.com/me/stats/post/{post_id}",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        }
    
    def _get_current_month_payload(self, post_id: str) -> List[Dict]:
        """Generate GraphQL payload for current month stats"""
        now = datetime.now(timezone.utc)
        start_of_month = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        start_at = int(start_of_month.timestamp() * 1000)
        end_at = int(now.timestamp() * 1000)

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
    
    def _get_lifetime_payload(self, post_id: str) -> List[Dict]:
        """Generate GraphQL payload for lifetime stats (readersCount, viewersCount, presentationCount)"""
        return [{
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
    
    def _get_leaderboard_payload(self) -> List[Dict]:
        """Generate GraphQL payload for leaderboard earnings"""
        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1, 0, 0, 0)
        start_at = int(start_of_month.timestamp() * 1000)
        end_at = int(now.timestamp() * 1000)
        
        return [{
            "operationName": "StoryEarningsQuery",
            "variables": {
                "username": "mvineetsharma",
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
    
    def _parse_current_month_response(self, data: Any, post_id: str) -> Dict[str, Any]:
        """Parse the current month stats response"""
        result = {
            'post_id': post_id,
            'fetch_timestamp': datetime.now().isoformat(),
            'title': None,
            'first_published': None,
            'last_updated': None,
            'reading_time': 0,
            'word_count': 0,
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
            }
        }
        
        if isinstance(data, list) and len(data) > 0:
            response_item = data[0]
            
            if 'data' in response_item:
                stats_data = response_item.get('data', {})
                
                post_obj = stats_data.get('post', {})
                if post_obj:
                    result['title'] = post_obj.get('title')
                    
                    first_published = post_obj.get('firstPublishedAt') or post_obj.get('createdAt')
                    if first_published and isinstance(first_published, (int, float)):
                        result['first_published'] = datetime.fromtimestamp(first_published / 1000).isoformat()
                    else:
                        result['first_published'] = first_published
                    
                    last_updated = post_obj.get('updatedAt')
                    if last_updated and isinstance(last_updated, (int, float)):
                        result['last_updated'] = datetime.fromtimestamp(last_updated / 1000).isoformat()
                    else:
                        result['last_updated'] = last_updated
                    
                    reading_time = post_obj.get('readingTime')
                    if reading_time:
                        result['reading_time'] = int(round(reading_time))
                    else:
                        result['reading_time'] = 0
                    
                    result['word_count'] = post_obj.get('wordCount') or 0
                
                post_stats = stats_data.get('postStatsDailyBundle', {})
                buckets = post_stats.get('buckets', [])
                
                now = datetime.now()
                start_of_month = datetime(now.year, now.month, 1, 0, 0, 0)
                result['period']['start'] = start_of_month.isoformat()
                result['period']['end'] = now.isoformat()
                
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
        
        return result
    
    def _parse_lifetime_response(self, data: Any, post_id: str) -> Dict[str, Any]:
        """Parse the lifetime stats response (readersCount, viewersCount, presentationCount)"""
        result = {
            'post_id': post_id,
            'fetch_timestamp': datetime.now().isoformat(),
            'lifetime_reads': 0,
            'lifetime_views': 0,
            'presentation_count': 0
        }
        
        if isinstance(data, list) and len(data) > 0:
            response_item = data[0]
            
            if 'data' in response_item:
                bundle_data = response_item.get('data', {}).get('postStatsTotalBundle', {})
                if bundle_data:
                    result['lifetime_reads'] = bundle_data.get('readersCount', 0)
                    result['lifetime_views'] = bundle_data.get('viewersCount', 0)
                    result['presentation_count'] = bundle_data.get('presentationCount', 0)
        
        return result
    
    async def fetch_current_month_stats(self, medium_url: str) -> Optional[Dict[str, Any]]:
        """Fetch current month stats using the working GraphQL API"""
        if not self.is_authenticated():
            logger.warning("Not authenticated. Cannot fetch stats.")
            return None
        
        post_id = self.extract_post_id_from_url(medium_url)
        if not post_id:
            logger.warning(f"Could not extract post ID from URL: {medium_url}")
            return None
        
        logger.info(f"📝 Fetching current month stats for post ID: {post_id}")
        
        session = requests.Session()
        for name, value in self.cookies.items():
            session.cookies.set(name, value, domain=".medium.com", path="/")
        
        url = "https://medium.com/_/graphql"
        payload = self._get_current_month_payload(post_id)
        headers = self._get_headers_for_current_month(post_id)
        
        time.sleep(2)
        
        try:
            response = session.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Successfully fetched current month stats for {post_id}")
                return self._parse_current_month_response(data, post_id)
            else:
                logger.error(f"❌ Failed to fetch current month stats: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error fetching current month stats: {e}")
            return None
    
    async def fetch_lifetime_stats(self, medium_url: str) -> Optional[Dict[str, Any]]:
        """Fetch lifetime stats (readersCount, viewersCount, presentationCount)"""
        if not self.is_authenticated():
            logger.warning("Not authenticated. Cannot fetch lifetime stats.")
            return None
        
        post_id = self.extract_post_id_from_url(medium_url)
        if not post_id:
            logger.warning(f"Could not extract post ID from URL: {medium_url}")
            return None
        
        logger.info(f"📝 Fetching lifetime stats for post ID: {post_id}")
        
        session = requests.Session()
        for name, value in self.cookies.items():
            session.cookies.set(name, value, domain=".medium.com", path="/")
        
        url = "https://medium.com/_/graphql"
        payload = self._get_lifetime_payload(post_id)
        headers = self._get_headers_for_lifetime(post_id)
        
        time.sleep(2)
        
        try:
            response = session.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Successfully fetched lifetime stats for {post_id}")
                return self._parse_lifetime_response(data, post_id)
            else:
                logger.error(f"❌ Failed to fetch lifetime stats: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error fetching lifetime stats: {e}")
            return None
    
    async def fetch_complete_stats(self, medium_url: str) -> Optional[Dict[str, Any]]:
        """Fetch complete stats (current month + lifetime totals + metadata) in one call"""
        if not self.is_authenticated():
            logger.warning("Not authenticated. Cannot fetch stats.")
            return None
        
        post_id = self.extract_post_id_from_url(medium_url)
        if not post_id:
            logger.warning(f"Could not extract post ID from URL: {medium_url}")
            return None
        
        logger.info(f"📝 Fetching complete stats for post ID: {post_id}")
        
        session = requests.Session()
        for name, value in self.cookies.items():
            session.cookies.set(name, value, domain=".medium.com", path="/")
        
        url = "https://medium.com/_/graphql"
        payload = self._get_current_month_payload(post_id)
        headers = self._get_headers_for_current_month(post_id)
        
        time.sleep(2)
        
        try:
            response = session.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Successfully fetched complete stats for {post_id}")
                
                # Parse current month stats
                parsed = self._parse_current_month_response(data, post_id)
                
                # Get lifetime totals and metadata from the same response
                if isinstance(data, list) and len(data) > 0:
                    stats_data = data[0].get('data', {})
                    post_obj = stats_data.get('post', {})
                    
                    # Try to get distribution data for lifetime totals
                    distribution = post_obj.get('distribution', {})
                    if distribution:
                        parsed['lifetime_totals'] = {
                            'total_reads': distribution.get('totalReadCount', 0),
                            'total_views': distribution.get('totalViewCount', 0),
                            'claps': distribution.get('totalClapCount', 0),
                            'replies': distribution.get('totalResponseCount', 0),
                            'bookmarks': distribution.get('totalBookmarkCount', 0)
                        }
                    else:
                        parsed['lifetime_totals'] = {
                            'total_reads': parsed.get('totals', {}).get('total_reads', 0),
                            'total_views': parsed.get('totals', {}).get('total_views', 0),
                            'claps': parsed.get('totals', {}).get('claps', 0),
                            'replies': parsed.get('totals', {}).get('replies', 0),
                            'bookmarks': 0
                        }
                    
                    # Extract tags and topics
                    tags = post_obj.get('tags', [])
                    parsed['post_tags'] = [tag.get('name') for tag in tags if tag.get('name')] if tags else []
                    topics = post_obj.get('topics', [])
                    parsed['post_topics'] = [topic.get('name') for topic in topics if topic.get('name')] if topics else []
                else:
                    parsed['lifetime_totals'] = {'total_reads': 0, 'total_views': 0, 'claps': 0, 'replies': 0, 'bookmarks': 0}
                    parsed['post_tags'] = []
                    parsed['post_topics'] = []
                
                return parsed
            else:
                logger.error(f"❌ Failed to fetch complete stats: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error fetching complete stats: {e}")
            import traceback
            traceback.print_exc()
            return None
    #===================
    async def fetch_leaderboard_earnings(self) -> Optional[List[Dict[str, Any]]]:
        """Fetch monthly earnings for leaderboard"""
        if not self.is_authenticated():
            logger.warning("Not authenticated. Cannot fetch earnings.")
            return None
        
        # Create session with cookies - EXACT same as current month stats
        session = requests.Session()
        
        # Set cookies with proper domain and path
        for name, value in self.cookies.items():
            session.cookies.set(name, value, domain=".medium.com", path="/")
            # Also set for www subdomain
            session.cookies.set(name, value, domain="www.medium.com", path="/")
        
        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1, 0, 0, 0)
        start_at = int(start_of_month.timestamp() * 1000)
        end_at = int(now.timestamp() * 1000)
        
        logger.info(f"📝 Fetching earnings for period: {start_of_month.date()} to {now.date()}")
        
        url = "https://medium.com/_/graphql"
        
        # Use headers similar to current month stats
        headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "apollographql-client-name": "lite",
            "apollographql-client-version": "main-20260402-184826-712bc227d8",
            "content-type": "application/json",
            "graphql-operation": "StoryEarningsQuery",
            "medium-frontend-app": "lite/main-20260402-184826-712bc227d8",
            "medium-frontend-path": "/me/partner/dashboard",
            "medium-frontend-route": "ShowPartnerDashboard",
            "origin": "https://medium.com",
            "priority": "u=1, i",
            "referer": "https://medium.com/me/partner/dashboard",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        }
        
        # Also add the cookie header explicitly
        cookie_str = "; ".join([f"{k}={v}" for k, v in self.cookies.items()])
        headers["cookie"] = cookie_str
        
        payload = [{
            "operationName": "StoryEarningsQuery",
            "variables": {
                "username": "mvineetsharma",
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
        
        try:
            response = session.post(url, headers=headers, json=payload, timeout=30)
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data and len(data) > 0:
                    if 'errors' in data[0]:
                        logger.error(f"GraphQL Errors: {data[0]['errors']}")
                        # Check if it's a cookie expiration issue
                        if "UNAUTHENTICATED" in str(data[0]['errors']):
                            logger.error("Authentication failed. Please:")
                            logger.error("  1. Close your browser completely")
                            logger.error("  2. Open Chrome and log into Medium")
                            logger.error("  3. Keep browser open")
                            logger.error("  4. Run this command again")
                        return []
                    
                    user_result = data[0].get('data', {}).get('userResult', {})
                    
                    if user_result and user_result.get('__typename') == 'User':
                        posts_connection = user_result.get('postsConnection', {})
                        edges = posts_connection.get('edges', [])
                        
                        logger.info(f"Found {len(edges)} stories with earnings")
                        
                        results = []
                        for edge in edges:
                            node = edge.get('node', {})
                            earnings = node.get('earnings', {})
                            monthly_earnings = earnings.get('monthlyEarnings', {})
                            
                            nanos = monthly_earnings.get('nanos', 0)
                            if nanos > 0:
                                results.append({
                                    'title': node.get('title'),
                                    'medium_url': node.get('mediumUrl'),
                                    'first_published_at': node.get('firstPublishedAt'),
                                    'nanos': nanos,
                                    'currency': monthly_earnings.get('currencyCode', 'USD')
                                })
                                logger.info(f"  - {node.get('title')}: ${nanos/1000000000:.2f}")
                        
                        logger.info(f"Total earnings stories: {len(results)}")
                        return results
                    else:
                        logger.warning(f"User result not found: {user_result}")
                        return []
                else:
                    logger.warning("Empty response data")
                    return []
            else:
                logger.error(f"Failed to fetch earnings: HTTP {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching earnings: {e}")
            import traceback
            traceback.print_exc()
            return None
# ====                    
    async def fetch_all_stories_stats(self, stories: List[Dict]) -> Dict[str, Any]:
        """Fetch current month stats for multiple stories"""
        results = {
            'total': len(stories),
            'updated': 0,
            'failed': 0,
            'details': []
        }
        
        for i, story in enumerate(stories):
            try:
                logger.info(f"📊 ({i+1}/{len(stories)}): {story['name'][:50]}...")
                
                if i > 0:
                    time.sleep(3)
                
                details = await self.fetch_current_month_stats(story['medium_url'])
                if details:
                    results['updated'] += 1
                    results['details'].append({
                        'key': story['key'],
                        'name': story['name'],
                        'success': True,
                        'stats': details
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