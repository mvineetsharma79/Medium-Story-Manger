"""
Medium Stats Service - Uses authenticated medium_stats library
"""
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)

# Try to import medium_stats
try:
    from medium_stats.scraper import StatGrabberUser
    MEDIUM_STATS_AVAILABLE = True
    logger.info("medium-stats library loaded successfully")
except ImportError as e:
    MEDIUM_STATS_AVAILABLE = False
    logger.warning(f"medium-stats library not installed: {e}")
    logger.warning("Run: pip install medium-stats")


class MediumStatsService:
    """Service to fetch story statistics using authenticated Medium API"""
    
    def __init__(self, username: str = None):
        """
        Initialize with Medium credentials
        """
        self.username = username or "mvineetsharma"
        self.sid = None
        self.uid = None
        self._load_credentials()
    
    def _load_credentials(self):
        """Load credentials from environment or config file"""
        # Try environment first
        self.sid = os.environ.get("MEDIUM_SID")
        self.uid = os.environ.get("MEDIUM_UID")
        
        if self.sid and self.uid:
            logger.info("Loaded credentials from environment")
            return
        
        # Try config file
        creds_path = os.path.expanduser("~/.medium_creds.ini")
        if Path(creds_path).exists():
            try:
                import configparser
                config = configparser.ConfigParser()
                config.read(creds_path)
                
                if self.username in config:
                    self.sid = config[self.username].get('sid')
                    self.uid = config[self.username].get('uid')
                    logger.info(f"Loaded credentials for {self.username} from {creds_path}")
                    return
            except Exception as e:
                logger.warning(f"Failed to load from file: {e}")
        
        logger.warning("No Medium credentials found. Stats will be limited.")
        logger.info(f"Set environment variables: MEDIUM_SID and MEDIUM_UID")
        logger.info(f"Or create file: ~/.medium_creds.ini with:\n[{self.username}]\nsid=YOUR_SID\nuid=YOUR_UID")
    
    def is_authenticated(self) -> bool:
        """Check if we have valid credentials"""
        return bool(self.sid and self.uid) and MEDIUM_STATS_AVAILABLE
    
    async def get_all_stats(self, medium_url: str, story_key: str = None) -> Dict[str, Any]:
        """
        Fetch all available statistics for a story
        """
        stats = {
            'reads': 0, 'claps': 0, 'responses': 0, 'bookmarks': 0,
            'view_count': 0, 'read_ratio': 0, 'reading_time': 0,
            'fan_count': 0, 'first_published': None, 'last_updated': None,
            'tags': [], 'topics': [], 'word_count': 0, 'title': '',
            'subtitle': '', 'author': '', 'publication': '',
            'medium_url': medium_url, 'fetch_timestamp': datetime.now().isoformat()
        }
        
        # Use the medium_stats library if available
        if self.is_authenticated():
            logger.info("Using authenticated Medium stats API")
            api_stats = await self._fetch_from_api()
            if api_stats and api_stats.get('stories'):
                # Try to find the specific story by title match
                for post in api_stats.get('stories', []):
                    # Extract story slug from URL
                    url_slug = medium_url.split('/')[-1].replace('-', ' ').lower()
                    post_title = post.get('title', '').lower()
                    if url_slug in post_title or post_title in url_slug:
                        stats.update(self._parse_post_stats(post))
                        break
                
                # If no match, use first story
                if stats['reads'] == 0 and api_stats.get('stories'):
                    stats.update(self._parse_post_stats(api_stats['stories'][0]))
                
                logger.info(f"API stats: reads={stats['reads']}, claps={stats['claps']}")
        
        # Also try scraping for additional metadata
        scrape_stats = await self._fetch_from_scraping(medium_url)
        if scrape_stats:
            # Don't override API stats, just add missing metadata
            for key, value in scrape_stats.items():
                if key not in stats or not stats[key]:
                    stats[key] = value
        
        return stats
    
    async def _fetch_from_api(self) -> Optional[Dict[str, Any]]:
        """Fetch stats using authenticated Medium API"""
        try:
            # Run the sync API call in a thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._sync_fetch_from_api)
            return result
        except Exception as e:
            logger.error(f"API fetch error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _sync_fetch_from_api(self) -> Dict[str, Any]:
        """Synchronous API fetch using medium_stats"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)  # Get last 90 days
            
            logger.info(f"Fetching stats from {start_date} to {end_date}")
            
            grabber = StatGrabberUser(
                self.username,
                sid=self.sid,
                uid=self.uid,
                start=start_date,
                stop=end_date
            )
            
            # Get summary stats
            summary_stats = grabber.get_summary_stats()
            logger.info(f"Retrieved {len(summary_stats)} stories from API")
            
            if not summary_stats:
                return {'stories': []}
            
            # Parse stories
            stories = []
            for post in summary_stats:
                stories.append({
                    'title': post.get('title', ''),
                    'reads': post.get('reads', 0),
                    'claps': post.get('upvotes', 0) or post.get('claps', 0),
                    'responses': post.get('responses', 0),
                    'views': post.get('views', 0),
                    'reading_time': post.get('readingTime', 0),
                    'first_published': post.get('firstPublishedAt'),
                    'word_count': post.get('wordCount', 0),
                    'slug': post.get('slug', ''),
                    'post_id': post.get('postId', '')
                })
            
            return {'stories': stories}
            
        except Exception as e:
            logger.error(f"Sync API fetch error: {e}")
            import traceback
            traceback.print_exc()
            return {'stories': []}
    
    def _parse_post_stats(self, post: Dict) -> Dict[str, Any]:
        """Parse stats from a single post"""
        return {
            'reads': post.get('reads', 0),
            'claps': post.get('claps', 0),
            'responses': post.get('responses', 0),
            'view_count': post.get('views', 0),
            'reading_time': post.get('reading_time', 0),
            'title': post.get('title', ''),
            'first_published': post.get('first_published'),
            'word_count': post.get('word_count', 0)
        }
    
    async def _fetch_from_scraping(self, medium_url: str) -> Dict[str, Any]:
        """Fallback to scraping with better headers"""
        stats = {}
        try:
            import aiohttp
            from bs4 import BeautifulSoup
            import re
            import json
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(medium_url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"Page fetch failed: {response.status}")
                        return stats
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract title
                    title_tag = soup.find('title')
                    if title_tag:
                        stats['title'] = title_tag.get_text(strip=True).replace(' – Medium', '')
                    
                    # Extract reading time
                    reading_time_span = soup.find('span', class_=re.compile(r'readingTime'))
                    if reading_time_span:
                        time_match = re.search(r'(\d+)', reading_time_span.get_text())
                        if time_match:
                            stats['reading_time'] = int(time_match.group(1))
                    
                    # Extract tags
                    tag_links = soup.find_all('a', href=re.compile(r'/tag/'))
                    tags = []
                    for tag in tag_links:
                        tag_name = tag.get_text(strip=True)
                        if tag_name and tag_name not in tags:
                            tags.append(tag_name)
                    stats['tags'] = tags[:10]
                    
                    # Extract author
                    author_meta = soup.find('meta', {'name': 'author'})
                    if author_meta and author_meta.get('content'):
                        stats['author'] = author_meta.get('content')
                    
                    # Extract from JSON-LD
                    script_tags = soup.find_all('script', type='application/ld+json')
                    for tag in script_tags:
                        try:
                            data = json.loads(tag.string)
                            if isinstance(data, dict) and data.get('@type') == 'Article':
                                if data.get('wordCount'):
                                    stats['word_count'] = data.get('wordCount')
                                if data.get('datePublished'):
                                    stats['first_published'] = data.get('datePublished')
                                if data.get('author'):
                                    author = data.get('author', {})
                                    if isinstance(author, dict):
                                        stats['author'] = author.get('name', '')
                        except:
                            continue
                    
                    logger.info(f"Scraped: title={stats.get('title')}, reading_time={stats.get('reading_time')}")
                    return stats
                    
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            return stats
    
    async def get_story_stats(self, story_key: str, medium_url: str) -> Optional[Dict]:
        """Get stats for a specific story"""
        return await self.get_all_stats(medium_url, story_key)
    
    async def get_all_stories_stats(self, stories: List[Dict]) -> Dict[str, Any]:
        """Get stats for all stories with Medium URLs"""
        results = {
            'total': len(stories),
            'updated': 0,
            'failed': 0,
            'details': []
        }
        
        # First get all stats from API once
        if self.is_authenticated():
            api_stats = await self._fetch_from_api()
            if api_stats and api_stats.get('stories'):
                # Match each story with API stats
                for story in stories:
                    matched = False
                    for post in api_stats['stories']:
                        # Try to match by title or slug
                        story_name = story['name'].lower()
                        post_title = post.get('title', '').lower()
                        if story_name in post_title or post_title in story_name:
                            stats = self._parse_post_stats(post)
                            results['details'].append({
                                'key': story['key'],
                                'name': story['name'],
                                'success': True,
                                'stats': stats
                            })
                            results['updated'] += 1
                            matched = True
                            break
                    
                    if not matched:
                        # Try scraping for metadata
                        scrape_stats = await self._fetch_from_scraping(story['medium_url'])
                        results['details'].append({
                            'key': story['key'],
                            'name': story['name'],
                            'success': True,
                            'stats': scrape_stats
                        })
                        results['updated'] += 1
            else:
                # Fallback to per-story scraping
                for story in stories:
                    stats = await self._fetch_from_scraping(story['medium_url'])
                    results['details'].append({
                        'key': story['key'],
                        'name': story['name'],
                        'success': True,
                        'stats': stats
                    })
                    results['updated'] += 1
        else:
            # No authentication, use scraping only
            for story in stories:
                stats = await self._fetch_from_scraping(story['medium_url'])
                results['details'].append({
                    'key': story['key'],
                    'name': story['name'],
                    'success': True,
                    'stats': stats
                })
                results['updated'] += 1
        
        return results


# Singleton instance
_medium_service = None

def get_medium_service() -> MediumStatsService:
    global _medium_service
    if _medium_service is None:
        _medium_service = MediumStatsService()
    return _medium_service