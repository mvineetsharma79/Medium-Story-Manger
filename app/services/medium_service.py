"""
Medium Stats Service - Fetches story statistics from Medium without API keys
"""
import aiohttp
import asyncio
import re
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class MediumService:
    """Service to fetch story statistics from Medium"""

    def __init__(self):
        self.session = None
        self.user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    async def _get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def get_all_stats(self, medium_url: str) -> Dict[str, Any]:
        """Fetch all available statistics from a Medium story"""
        stats = {
            'reads': 0, 'claps': 0, 'responses': 0, 'bookmarks': 0,
            'view_count': 0, 'read_ratio': 0, 'reading_time': 0,
            'fan_count': 0, 'first_published': None, 'last_updated': None,
            'tags': [], 'topics': [], 'word_count': 0, 'title': '',
            'subtitle': '', 'author': '', 'publication': '',
            'medium_url': medium_url, 'fetch_timestamp': datetime.now().isoformat()
        }

        try:
            # Fetch from the page
            page_stats = await self._fetch_from_page(medium_url)
            if page_stats:
                logger.info(f"Page stats retrieved: {page_stats}")
                stats.update(page_stats)

            # Try RSS feed
            rss_stats = await self._fetch_from_rss(medium_url)
            if rss_stats:
                logger.info(f"RSS stats retrieved: {rss_stats}")
                stats.update(rss_stats)

            return stats

        except Exception as e:
            logger.error(f"Error fetching stats: {e}")
            return stats

    async def _fetch_from_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch stats by scraping the story page"""
        session = await self._get_session()
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

        try:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Page fetch failed with status {response.status}")
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                stats = {}

                # Extract title
                title_tag = soup.find('title')
                if title_tag:
                    stats['title'] = title_tag.get_text(strip=True).replace(' – Medium', '')

                # Extract author
                author_link = soup.find('a', {'rel': 'author'})
                if author_link:
                    stats['author'] = author_link.get_text(strip=True)

                # Extract publication date
                pub_meta = soup.find('meta', {'property': 'article:published_time'})
                if pub_meta and pub_meta.get('content'):
                    stats['first_published'] = pub_meta.get('content')

                # Extract reading time
                reading_time_span = soup.find('span', class_=re.compile(r'readingTime'))
                if reading_time_span:
                    time_text = reading_time_span.get_text(strip=True)
                    match = re.search(r'(\d+)', time_text)
                    if match:
                        stats['reading_time'] = int(match.group(1))

                # Extract tags
                tag_links = soup.find_all('a', href=re.compile(r'/tag/'))
                tags = []
                for tag in tag_links:
                    tag_name = tag.get_text(strip=True)
                    if tag_name and tag_name not in tags:
                        tags.append(tag_name)
                stats['tags'] = tags[:10]

                # Extract publication
                pub_link = soup.find('a', href=re.compile(r'/publication'))
                if pub_link:
                    stats['publication'] = pub_link.get_text(strip=True)

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
                            if data.get('dateModified'):
                                stats['last_updated'] = data.get('dateModified')
                            if data.get('headline'):
                                stats['title'] = data.get('headline')
                            if data.get('description'):
                                stats['subtitle'] = data.get('description')
                            
                            # Extract interaction stats
                            interactions = data.get('interactionStatistic', [])
                            if isinstance(interactions, dict):
                                interactions = [interactions]
                            
                            for stat in interactions:
                                name = stat.get('name', '')
                                count = stat.get('userInteractionCount', 0)
                                if name == 'Reads':
                                    stats['reads'] = count
                                elif name == 'Claps':
                                    stats['claps'] = count
                                elif name == 'Responses':
                                    stats['responses'] = count
                    except:
                        continue

                # Try to extract from Apollo state (Medium's React data)
                for tag in soup.find_all('script'):
                    if tag.string and 'window.__APOLLO_STATE__' in tag.string:
                        try:
                            json_match = re.search(r'window\.__APOLLO_STATE__\s*=\s*({.*?});', tag.string, re.DOTALL)
                            if json_match:
                                data = json.loads(json_match.group(1))
                                for key, value in data.items():
                                    if 'Post' in key and isinstance(value, dict):
                                        if 'distribution' in value:
                                            dist = value['distribution']
                                            stats['claps'] = dist.get('totalClapCount', stats.get('claps', 0))
                                            stats['responses'] = dist.get('totalResponseCount', stats.get('responses', 0))
                                            stats['bookmarks'] = dist.get('totalBookmarkCount', stats.get('bookmarks', 0))
                                            stats['view_count'] = dist.get('totalViewCount', stats.get('view_count', 0))
                                            stats['reads'] = dist.get('totalReadCount', stats.get('reads', 0))
                                        if 'readingTime' in value:
                                            stats['reading_time'] = value['readingTime']
                                        if 'wordCount' in value:
                                            stats['word_count'] = value['wordCount']
                                        if 'title' in value:
                                            stats['title'] = value['title']
                                        break
                        except Exception as e:
                            logger.debug(f"Apollo parse error: {e}")

                # Extract claps from UI
                if stats.get('claps', 0) == 0:
                    clap_button = soup.find('button', {'data-action': 'show-claps'})
                    if clap_button:
                        clap_span = clap_button.find('span')
                        if clap_span:
                            clap_text = clap_span.get_text(strip=True)
                            if clap_text:
                                clap_num = re.sub(r'[^0-9]', '', clap_text)
                                if clap_num:
                                    stats['claps'] = int(clap_num)

                logger.info(f"Extracted: title={stats.get('title')}, reading_time={stats.get('reading_time')}, tags={len(stats.get('tags', []))}")
                return stats if stats else None

        except Exception as e:
            logger.error(f"Page fetch error: {e}")
            return None

    async def _fetch_from_rss(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch stats from Medium's RSS feed"""
        username_match = re.search(r'@([^/]+)', url) or re.search(r'//([^.]+)\.medium\.com', url)
        if not username_match:
            return None

        username = username_match.group(1)
        rss_url = f"https://medium.com/feed/@{username}"

        session = await self._get_session()
        try:
            async with session.get(rss_url, headers={'User-Agent': self.user_agent}) as response:
                if response.status != 200:
                    return None

                text = await response.text()
                import xml.etree.ElementTree as ET
                root = ET.fromstring(text)

                story_title_from_url = url.split('/')[-1].replace('-', ' ')

                for item in root.findall('.//item'):
                    link_elem = item.find('link')
                    title_elem = item.find('title')
                    
                    if link_elem is not None and link_elem.text:
                        if link_elem.text in url or (title_elem is not None and story_title_from_url.lower() in title_elem.text.lower()):
                            stats = {}

                            if title_elem is not None:
                                stats['title'] = title_elem.text

                            pub_elem = item.find('pubDate')
                            if pub_elem is not None:
                                stats['first_published'] = pub_elem.text

                            categories = item.findall('category')
                            if categories:
                                stats['tags'] = [cat.text for cat in categories if cat.text][:10]

                            return stats

        except Exception as e:
            logger.debug(f"RSS fetch failed: {e}")

        return None

    async def update_story_stats(self, story_key: str, medium_url: str) -> Optional[Dict]:
        """Update a single story's stats"""
        if not medium_url:
            return None

        logger.info(f"Fetching stats for story {story_key} from {medium_url}")
        stats = await self.get_all_stats(medium_url)
        
        if stats:
            result = {
                'reads': stats.get('reads', 0),
                'claps': stats.get('claps', 0),
                'responses': stats.get('responses', 0),
                'bookmarks': stats.get('bookmarks', 0),
                'view_count': stats.get('view_count', 0),
                'read_ratio': stats.get('read_ratio', 0),
                'reading_time': stats.get('reading_time', 0),
                'fan_count': stats.get('fan_count', 0),
                'first_published': stats.get('first_published'),
                'last_updated': stats.get('last_updated'),
                'tags': stats.get('tags', []),
                'topics': stats.get('topics', []),
                'word_count': stats.get('word_count', 0),
                'title': stats.get('title', ''),
                'subtitle': stats.get('subtitle', ''),
                'author': stats.get('author', ''),
                'publication': stats.get('publication', ''),
                'last_stats_update': datetime.now().isoformat()
            }
            return result
        return None

    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()