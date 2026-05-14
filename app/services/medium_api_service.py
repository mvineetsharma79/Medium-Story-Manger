"""
Medium API Service - Pure API client for Medium GraphQL calls

This service handles all direct communication with Medium's GraphQL API.
"""

import os
import json
import requests
import sqlite3
import tempfile
import shutil
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import re
import browser_cookie3

logger = logging.getLogger(__name__)

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
        print("=" * 80 + "\n")
    
    # ============================================
    # COOKIE EXTRACTION
    # ============================================
    
    def _get_chrome_cookies(self) -> Optional[Dict[str, str]]:
        """Extract Medium cookies using browser_cookie3 (works with open Chrome)"""
        print("🍪 EXTRACTING COOKIES FROM BROWSER")
        try:
            # Get cookies for medium.com from Chrome
            cj = browser_cookie3.chrome(domain_name='medium.com')
            
            cookies = {}
            for cookie in cj:
                if 'medium.com' in cookie.domain:
                    cookies[cookie.name] = cookie.value
            
            if cookies:
                logger.info(f"Found {len(cookies)} cookies from Chrome")
                #return None
                return cookies
            

        except Exception as e:
            logger.debug(f"Error extracting cookies with browser_cookie3: {e}")
        
        return None
    
    def _get_cookies_from_env(self) -> Optional[Dict[str, str]]:
        """Get cookies from environment variables"""
        cookie_string = os.environ.get("MEDIUM_COOKIE")
        print("🍪 EXTRACTING COOKIES")

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
        """Check if we have valid cookies for authentication"""
        return self.cookies is not None and self.cookies.get('sid') is not None
    
    # ============================================
    # UTILITY METHODS
    # ============================================
    
    def get_month_timestamps(self, year: int, month: int) -> tuple:
        """
        Convert year/month to start and end timestamps (milliseconds).
        
        CRITICAL: 
        - start_at = first day of month at 00:00:00
        - end_at   = last day of month at 23:59:59
        
        Args:
            year: Year (e.g., 2026)
            month: Month (1-12)
        
        Returns:
            Tuple of (start_timestamp, end_timestamp) in milliseconds
        
        Example:
            get_month_timestamps(2026, 4)
            returns: (1746057600000, 1748735999000)
            # April 1, 2026 00:00:00 to April 30, 2026 23:59:59
        """
        from datetime import datetime, timezone, timedelta
        
        # Start of month: first day at 00:00:00
        start_date = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
        start_at = int(start_date.timestamp() * 1000)
        
        # End of month: last day at 23:59:59
        # Get the last day of the month
        if month == 12:
            last_day = 31
        else:
            # Get first day of next month, subtract 1 day to get last day of current month
            next_month = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            last_day = (next_month - timedelta(days=1)).day
        
        end_date = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
        end_at = int(end_date.timestamp() * 1000)
        
        logger.info(f"Month timestamps for {year}-{month:02d}:")
        logger.info(f"  start_at: {start_at} ({start_date})")
        logger.info(f"  end_at:   {end_at} ({end_date})")
        
        return start_at, end_at
    
    def extract_post_id_from_url(self, medium_url: str) -> Optional[str]:
        """
        Extract post ID from Medium URL.
        
        Args:
            medium_url: Full Medium URL
        
        Returns:
            Post ID or None if not found
        """
        if not medium_url:
            return None
        
        url = medium_url.rstrip('/')
        parts = url.split('/')
        last_part = parts[-1]
        
        # Check for post ID at the end of URL (after hyphen)
        if '-' in last_part:
            post_id = last_part.split('-')[-1]
            if len(post_id) >= 10 and re.match(r'^[a-f0-9]+$', post_id):
                return post_id
        
        # Check if last part itself is a post ID
        if len(last_part) >= 10 and re.match(r'^[a-f0-9]+$', last_part):
            return last_part
        
        return None
    
    # ============================================
    # COMMON REQUEST METHOD
    # ============================================
    
    def _make_request(self, url: str, headers: Dict, payload: List[Dict], request_type: str) -> Optional[Dict]:
        """Make HTTP request with debug logging and explicit cookie header"""
        self._debug_print(f"{request_type} Request Headers", headers)
        self._debug_print(f"{request_type} Request Payload", payload)
        
        if self.cookies:
            cookie_string = "; ".join([f"{k}={v}" for k, v in self.cookies.items() if v])
            headers["cookie"] = cookie_string
     
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                self._debug_print(f"{request_type} Response", response_data)
                return response_data
            else:
                self._debug_print(f"{request_type} Error", {"status": response.status_code, "text": response.text[:500]})
                return None
        except Exception as e:
            self._debug_print(f"{request_type} Exception", {"error": str(e)})
            return None
    
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
    # MAIN METHOD: Fetch ALL posts for a period
    # ============================================
    
    def fetch_medium_stat(self, period: str) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch ALL published posts for a specific period (month).
        
        This is the PRIMARY method for refreshing stats. It returns all posts
        with their metadata, stats, and earnings for the specified month.
        
        Args:
            period: Period in YYYY-MM format (e.g., "2026-04")
        
        Returns:
            List of posts with fields:
            - id: Post ID
            - title: Post title
            - mediumUrl: Full Medium URL
            - uniqueSlug: URL slug
            - firstPublishedAt: Publication timestamp
            - readingTime: Estimated reading time
            - wordCount: Word count
            - clapCount: Number of claps
            - responsesCount: Number of responses
            - totalStats: {presentations, views, reads}
            - earnings: {total, monthlyEarnings}
            - creator: Author info
            - collection: Publication info
        
        Example:
            service = MediumAPIService()
            posts = service.fetch_medium_stories("2026-04")
            for post in posts:
                print(f"{post['title']}: {post['totalStats']['reads']} reads")
        
        curl equivalent:
            curl -X POST "http://localhost:8000/api/stories/refresh-stats/2026-04" | jq '.'
        """
        from config import settings
        
        if not self.is_authenticated():
            logger.warning("Not authenticated. Cannot fetch stats.")
            return None
        
        # Parse period to year and month
        try:
            parts = period.split('-')
            year = int(parts[0])
            month = int(parts[1])
        except (ValueError, IndexError):
            logger.error(f"Invalid period format: {period}. Use YYYY-MM")
            return None
        
        username = settings.medium_username
        start_at, end_at = self.get_month_timestamps(year, month)
        #start_at, end_at  = 1775001600000, 1777593599000 # Apr
        #start_at, end_at  = 1772323200000, 1774915200000 # Mar
         
        logger.info(f"Fetching posts for {username} from {start_at} to {end_at}")
        
        # GraphQL query
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
                    id
                    __typename
                    title
                    uniqueSlug
                    mediumUrl
                    createdAt
                    updatedAt
                    firstPublishedAt
                    totalStats {
                        presentations
                        views
                        reads
                        __typename
                    }
                    readingTime
                    wordCount
                    clapCount
                    responsesCount
                    voterCount
                    isLocked
                    visibility
                    isSeries
                    isShortform
                    firstBoostedAt
                    license
                    tags {
                        id
                    }
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
                    creator {
                        id
                        username
                        name
                        bio
                        imageId
                        twitterScreenName
                        createdAt
                    }
                    collection {
                        id
                        name
                        slug
                        domain
                        subscriberCount
                        createdAt
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
            "first": 100,
            "after": "",
            "startAt": start_at,
            "endAt": end_at
        }
        
        payload = self._build_graphql_request("StoryEarningsQuery", variables, query, username, "stats-post")
        headers = self._get_common_headers(username, "StoryEarningsQuery")
        
        time.sleep(0.5)
        response = self._make_request(self.GRAPHQL_URL, headers, payload, f"Fetch Medium Stories {period}")
        
        # DEBUG: Print the response structure to console
        print("\n" + "=" * 80)
        print("RAW API RESPONSE:")
        print("=" * 80)
        print(json.dumps(response, indent=2)[:2000])  # Print first 2000 chars
        print("=" * 80 + "\n")
        
        if not response:
            logger.warning(f"No response from Medium API for {period}")
            return None
        
        # Parse posts from response - FIXED PARSING
        posts = []
        
        # Case 1: response is a list
        if isinstance(response, list) and len(response) > 0:
            response_item = response[0]
            
            # Check for data field
            if 'data' in response_item:
                data_obj = response_item['data']
                
                # Check for userResult
                if 'userResult' in data_obj:
                    user_result = data_obj['userResult']
                    
                    # userResult could be a dict or None
                    if user_result and isinstance(user_result, dict):
                        # Check for postsConnection
                        if 'postsConnection' in user_result:
                            posts_connection = user_result['postsConnection']
                            
                            # Check for edges
                            if 'edges' in posts_connection:
                                edges = posts_connection['edges']
                                
                                for edge in edges:
                                    if 'node' in edge:
                                        node = edge['node']
                                        if node:
                                            posts.append(node)
                                            logger.info(f"Found post: {node.get('title', 'Unknown')}")
        
        # Case 2: direct data structure (fallback)
        if not posts and isinstance(response, dict):
            if 'data' in response:
                user_result = response['data'].get('userResult')
                if user_result:
                    posts_connection = user_result.get('postsConnection', {})
                    edges = posts_connection.get('edges', [])
                    for edge in edges:
                        node = edge.get('node')
                        if node:
                            posts.append(node)
        
        logger.info(f"Parsed {len(posts)} posts from Medium API response")
        
        # Debug: Print first post title if any
        if posts:
            logger.info(f"First post title: {posts[0].get('title', 'Unknown')}")
        else:
            logger.warning("No posts parsed from response. Check response structure above.")
        
        return posts if posts else None
        
    # ============================================
    # METHOD: Fetch stats for a SINGLE story
    # ============================================
    
    # === New Method
    def fetch_medium_story_stats(self, post_id: str, period: str, retType:bool= False) -> Optional[Dict[str, Any]]:
        """Fetch lifetime and monthly stats for a single story from Medium API."""
        if not self.is_authenticated():
            logger.warning("Not authenticated. Cannot fetch story stats.")
            return None
        
        # Parse period
        try:
            parts = period.split('-')
            year = int(parts[0])
            month = int(parts[1])
        except (ValueError, IndexError):
            logger.error(f"Invalid period format: {period}")
            return None
        
        # Get timestamps
        start_at, end_at = self.get_month_timestamps(year, month)
        
        # GraphQL query
        query = """query MergedPostStatsQuery($postStatsTotalBundleInput: PostStatsTotalBundleInput!, $postStatsDailyBundleInput: PostStatsDailyBundleInput!) {
    postStatsTotalBundle(postStatsTotalBundleInput: $postStatsTotalBundleInput) {
        readersCount
        viewersCount
        feedClickThroughRate
        presentationCount
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
    }"""
        
        variables = {
            "postStatsTotalBundleInput": {"postId": post_id},
            "postStatsDailyBundleInput": {
                "postId": post_id,
                "fromDayStartsAt": start_at,
                "toDayStartsAt": end_at
            }
        }
        
        payload = self._build_graphql_request("MergedPostStatsQuery", variables, query, post_id, "stats-post")
        headers = self._get_common_headers(post_id, "MergedPostStatsQuery")
        
        time.sleep(0.5)
        response = self._make_request(self.GRAPHQL_URL, headers, payload, f"Story Stats {post_id} {period}")
        
        # CRITICAL FIX: Check if response is None
        if response is None:
            logger.error(f"Response is None for post {post_id}")
            return None
        
        # Parse the response directly from the list structure
        #return response
        # if retType:
        #     data_obj =response[0].get('data')
        #     logger.error("Data Object:", data_obj.get('postStatsTotalBundle'))
        #     return data_obj.get('postStatsTotalBundle')
            

        return self._parse_direct_from_response(response, post_id, period)


    def fetch_monthly_stats(self, period: str) -> Optional[Dict[str, Any]]:
        """
        Fetch aggregated monthly stats for all stories.
        Uses the exact Graph Query provided - no post_id anywhere.
        
        Args:
            period: Period in YYYY-MM format (e.g., "2026-05")
        
        Returns:
            Dict with totals and points arrays
        """
        if not self.is_authenticated():
            logger.warning("Not authenticated. Cannot fetch monthly stats.")
            return None
        
        # Parse period
        try:
            parts = period.split('-')
            year = int(parts[0])
            month = int(parts[1])
        except (ValueError, IndexError):
            logger.error(f"Invalid period format: {period}")
            return None
        
        start_at, end_at = self.get_month_timestamps(year, month)
        
        # Exact Graph Query from your requirement
        query = """query UserMonthlyStoryStatsTimeseriesQuery($username: ID!, $input: UserPostsAggregateStatsInput!) {
    user(username: $username) {
        id
        postsAggregateTimeseriesStats(input: $input) {
        __typename
        ... on AggregatePostTimeseriesStats {
            totalStats {
            presentations
            viewers
            readers
            netFollowersGained
            netSubscribersGained
            __typename
            }
            points {
            timestamp
            stats {
                total {
                viewers
                readers
                __typename
                }
                __typename
            }
            __typename
            }
            __typename
        }
        }
        __typename
    }
    }"""
        
        from config import settings
        variables = {
            "username": settings.medium_username,
            "input": {
                "startTime": start_at,
                "endTime": end_at
            }
        }
        
        payload = self._build_graphql_request(
            "UserMonthlyStoryStatsTimeseriesQuery",
            variables,
            query,
            "user",
            "stats"
        )
        headers = self._get_common_headers(None, "UserMonthlyStoryStatsTimeseriesQuery")
        
        import time
        time.sleep(0.5)
        response = self._make_request(self.GRAPHQL_URL, headers, payload, f"Monthly Stats {period}")
        
        if not response:
            return None
        
        # Parse response exactly as in your example
        result = {
            "totals": {
                "presentations": 0,
                "viewers": 0,
                "readers": 0,
                "netFollowersGained": 0,
                "netSubscribersGained": 0
            },
            "points": []
        }
        
        if isinstance(response, list) and len(response) > 0:
            data_obj = response[0].get('data', {})
            user_obj = data_obj.get('user', {})
            stats = user_obj.get('postsAggregateTimeseriesStats', {})
            
            # Get totals
            total_stats = stats.get('totalStats', {})
            result["totals"] = {
                "presentations": total_stats.get('presentations', 0),
                "viewers": total_stats.get('viewers', 0),
                "readers": total_stats.get('readers', 0),
                "netFollowersGained": total_stats.get('netFollowersGained', 0),
                "netSubscribersGained": total_stats.get('netSubscribersGained', 0)
            }
            
            # Get points (daily data)
            points = stats.get('points', [])
            for point in points:
                point_stats = point.get('stats', {})
                total = point_stats.get('total', {})
                result["points"].append({
                    "timestamp": point.get('timestamp', 0),
                    "viewers": total.get('viewers', 0),
                    "readers": total.get('readers', 0)
                })
        
        return result

    def fetch_notifications(self, limit: int = 25, to_timestamp: str = None) -> Optional[Dict[str, Any]]:
        """
        Fetch notifications from Medium GraphQL API.
        
        Args:
            limit: Number of notifications to fetch (default 25)
            to_timestamp: Timestamp for pagination (optional)
        
        Returns:
            Raw notification data from Medium API
        """
        if not self.is_authenticated():
            logger.warning("Not authenticated. Cannot fetch notifications.")
            return None
        
        # Build paging options
        paging_options = {
            "limit": limit,
            "page": None,
            "source": None
        }
        
        if to_timestamp:
            paging_options["to"] = to_timestamp
        
        # GraphQL query for notifications
        query = """query NotificationsQuery($pagingOptions: PagingOptions, $activityTypes: [String!]) {
    notificationsConnectionByActivityTypes(
        paging: $pagingOptions
        activityTypes: $activityTypes
    ) {
        notifications {
        __typename
        notificationName
        ...NotificationsList_notification
        }
        pagingInfo {
        next {
            limit
            page
            source
            to
            __typename
        }
        __typename
        }
        __typename
    }
    }

    fragment NotificationsList_notification on Notification {
    __typename
    ...NotificationQuote_notification
    ...NotificationResponseDialog_notification
    ...NotificationResponseCreated_notification
    ...ActorNotificationLayout_notification
    }

    fragment NotificationPostTitle_post on Post {
    id
    title
    __typename
    }

    fragment UserAvatar_user on User {
    id
    imageId
    name
    username
    __typename
    }

    fragment UserAvatarWithBadge_user on User {
    membership {
        tier
        __typename
        id
    }
    ...UserAvatar_user
    __typename
    id
    }

    fragment userUrl_user on User {
    __typename
    id
    customDomainState {
        live {
        domain
        __typename
        }
        __typename
    }
    hasSubdomain
    username
    }

    fragment UserAvatarLinkContainer_user on User {
    ...userUrl_user
    __typename
    id
    }

    fragment UserAvatarWithBadgeAndLink_user on User {
    ...UserAvatarWithBadge_user
    ...UserAvatarLinkContainer_user
    __typename
    id
    }

    fragment isUserVerifiedBookAuthor_user on User {
    verifications {
        isBookAuthor
        __typename
    }
    __typename
    id
    }

    fragment ActorNotificationLayout_user on User {
    id
    name
    ...UserAvatarWithBadgeAndLink_user
    ...isUserVerifiedBookAuthor_user
    ...userUrl_user
    __typename
    }

    fragment ActorNotificationLayout_notification on Notification {
    actor {
        ...ActorNotificationLayout_user
        __typename
        id
    }
    rollupItems {
        actor {
        id
        __typename
        }
        __typename
    }
    isUnread
    occurredAt
    notificationType
    __typename
    }

    fragment NotificationQuote_notification on Notification {
    post {
        id
        mediumUrl
        title
        visibility
        ...NotificationPostTitle_post
        __typename
    }
    quote {
        id
        startOffset
        endOffset
        paragraphs {
        text
        type
        __typename
        }
        __typename
    }
    ...ActorNotificationLayout_notification
    __typename
    }

    fragment NotificationResponseDetails_post on Post {
    content {
        bodyModel {
        paragraphs {
            text
            __typename
        }
        __typename
        }
        __typename
    }
    __typename
    id
    }

    fragment NotificationResponseDialog_notification on Notification {
    post {
        id
        __typename
    }
    responsePost {
        id
        ...NotificationResponseDetails_post
        __typename
    }
    ...ActorNotificationLayout_notification
    __typename
    }

    fragment NotificationResponseCreated_notification on Notification {
    post {
        id
        ...NotificationPostTitle_post
        __typename
    }
    responsePost {
        id
        __typename
    }
    ...ActorNotificationLayout_notification
    __typename
    }"""
        
        variables = {
            "pagingOptions": paging_options,
            "activityTypes": None
        }
        
        payload = self._build_graphql_request(
            "NotificationsQuery",
            variables,
            query,
            "notifications",
            "notifications"
        )
        headers = self._get_common_headers(None, "NotificationsQuery")
        
        import time
        time.sleep(0.5)
        response = self._make_request(self.GRAPHQL_URL, headers, payload, "Fetch Notifications")
        
        if not response:
            return None
        
        # Parse response
        result = {
            "notifications": [],
            "pagingInfo": None
        }
        
        if isinstance(response, list) and len(response) > 0:
            data_obj = response[0].get('data', {})
            notifications_connection = data_obj.get('notificationsConnectionByActivityTypes', {})
            
            result["notifications"] = notifications_connection.get('notifications', [])
            result["pagingInfo"] = notifications_connection.get('pagingInfo', {})
        
        return result

    def _parse_direct_from_response(self, response: Any, post_id: str, period: str) -> Optional[Dict[str, Any]]:
        """Parse response directly from the list structure."""
        
        # Guard against None
        if response is None:
            return None
        
        # Handle response as list (your _make_request returns list)
        if not isinstance(response, list) or len(response) == 0:
            logger.error(f"Response is not a list or empty: {type(response)}")
            return None
        
        # Get first item
        first_item = response[0]
        if not isinstance(first_item, dict):
            logger.error(f"First item is not a dict: {type(first_item)}")
            return None
        
        # Get data object
        data_obj = first_item.get('data')
        if not data_obj:
            logger.error(f"No 'data' key in response")
            return None
        
        # Initialize result
        result = {
            'presentation_count': 0,
            'reads': 0,
            'views': 0,
            'feed_click_through_rate': 0,
            'monthly': {
                'member_reads': 0,
                'member_views': 0,
                'nonmember_reads': 0,
                'nonmember_views': 0,
                'total_reads': 0,
                'total_views': 0,
                'claps': 0,
                'replies': 0,
                'highlights': 0,
                'new_followers': 0
            }
        }
        
        # Extract total stats
        total_bundle = data_obj.get('postStatsTotalBundle', {})
        if total_bundle:
            result['presentation_count'] = total_bundle.get('presentationCount', 0)
            result['reads'] = total_bundle.get('readersCount', 0)
            result['views'] = total_bundle.get('viewersCount', 0)
            result['feed_click_through_rate'] = total_bundle.get('feedClickThroughRate', 0)
        
        # Extract daily buckets
        daily_bundle = data_obj.get('postStatsDailyBundle', {})
        buckets = daily_bundle.get('buckets', [])
        
        for bucket in buckets:
            membership = bucket.get('membershipType')
            reads = bucket.get('readersThatReadCount', 0)
            views = bucket.get('readersThatViewedCount', 0)
            
            if membership == 'MEMBER':
                result['monthly']['member_reads'] += reads
                result['monthly']['member_views'] += views
            elif membership == 'NONMEMBER':
                result['monthly']['nonmember_reads'] += reads
                result['monthly']['nonmember_views'] += views
            
            result['monthly']['total_reads'] += reads
            result['monthly']['total_views'] += views
            result['monthly']['claps'] += bucket.get('readersThatClappedCount', 0)
            result['monthly']['replies'] += bucket.get('readersThatRepliedCount', 0)
            result['monthly']['highlights'] += bucket.get('readersThatHighlightedCount', 0)
            result['monthly']['new_followers'] += bucket.get('readersThatInitiallyFollowedAuthorFromThisPostCount', 0)
        return result    
    # ==============
    
    
    
    def fetch_story_stats(self, post_id: str, period: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed monthly stats for a single story.
        
        This method is used when editing a specific story to get its
        detailed daily breakdown for a month.
        
        Args:
            post_id: Medium post ID (e.g., "78cb972195da")
            year: Year (e.g., 2026)
            month: Month (1-12)
        
        Returns:
            Dict with aggregated totals for the month
        """
        # Parse period to year and month
        try:
            parts = period.split('-')
            year = int(parts[0])
            month = int(parts[1])
        except (ValueError, IndexError):
            logger.error(f"Invalid period format: {period}. Use YYYY-MM")
            return None
        if not self.is_authenticated():
            logger.warning("Not authenticated. Cannot fetch story stats.")
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
        """
        
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
        response = self._make_request(self.GRAPHQL_URL, headers, payload, f"Story Stats {post_id} {year}-{month:02d}")
        
        if not response:
            logger.warning(f"No stats found for post {post_id} in {year}-{month:02d}")
            return None
        
        return self._parse_story_stats_response(response, post_id)
    
    # ============================================
    # RESPONSE PARSERS
    # ============================================
    
    def _parse_story_stats_response(self, data: Any, post_id: str) -> Dict[str, Any]:
        """
        Parse the detailed monthly stats response for a single story.
        
        Args:
            data: Raw API response
            post_id: Post ID for reference
        
        Returns:
            Dict with aggregated totals for the month
        """
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
                
                # Parse earnings from daily data
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


# ============================================
# SINGLETON INSTANCE
# ============================================

_medium_api_service = None

def get_medium_api_service() -> MediumAPIService:
    """Get or create the singleton MediumAPIService instance"""
    global _medium_api_service
    if _medium_api_service is None:
        _medium_api_service = MediumAPIService()
    return _medium_api_service


def set_debug_mode(enabled: bool = True):
    """Enable or disable debug mode for API calls"""
    global DEBUG
    DEBUG = enabled
    print(f"🔍 Medium API Debug mode: {'ON' if DEBUG else 'OFF'}")