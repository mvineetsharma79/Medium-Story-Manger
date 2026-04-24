"""
Story Service - Manages all story CRUD operations and Medium API integration
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import urllib.parse
import re
import unicodedata

from app.services.file_service import (
    load_stories_data, save_stories_data, scan_markdown_files,
    parse_series_number, normalize_story_key
)
from app.services.medium_api_service import get_medium_api_service
from app.models import StoryCreate, StoryUpdate, Story, MediumPost, LinkedIn, LinkedInPostType, Stats, Earning, Creator, Collection, Tag

logger = logging.getLogger(__name__)


class StoryService:
    @staticmethod
    async def _update_series_counts(data: Dict[str, Any]) -> Dict[str, Any]:
        """Update total_stories and published counts for all series"""
        stories = data.get("stories", {})
        series_data = data.get("series", {})
        
        for series_name, series_info in series_data.items():
            total = 0
            published = 0
            for story_key in series_info.get("stories", []):
                if story_key in stories:
                    total += 1
                    if stories[story_key].get("status") == "Published":
                        published += 1
            series_info["total_stories"] = total
            series_info["published"] = published
        
        data["series"] = series_data
        return data

    @staticmethod
    async def sync_with_filesystem() -> Dict[str, Any]:
        """Sync stories.json with filesystem"""
        data = await load_stories_data()
        discovered = await scan_markdown_files()
        stories = data.get("stories", {})
        series_data = data.get("series", {})

        added_count = 0
        updated_count = 0

        for file_info in discovered:
            story_key = normalize_story_key(file_info['folder'], file_info['name'])
            
            # Generate uniqueSlug from filename
            unique_slug = file_info['name'].lower().replace(' ', '-').replace(':', '').replace('/', '-').replace('(', '').replace(')', '')[:100]

            if story_key not in stories:
                # Create new story entry
                stories[story_key] = {
                    "uniqueSlug": unique_slug,
                    "title": file_info['name'],
                    "name": file_info['name'],
                    "full_name": file_info['full_name'],
                    "folder": file_info['folder'],
                    "series": file_info['series'],
                    "raw_path": file_info['raw_path'],
                    "rel_path": file_info['rel_path'],
                    "status": "Draft",
                    "createdDate": datetime.now().strftime("%Y-%m-%d"),
                    "lastUpdated": datetime.now().isoformat(),
                    "notes": "",
                    "bookmarked": False,
                    "leaderboard": False,
                    "tags": [],
                    "read_time": None,
                    "medium_url": None,
                    "linkedin_status": None,
                    "linkedin_timestamp": None,
                    "linkedin_impressions": 0,
                    "linkedin_url": None
                }
                added_count += 1
                logger.info(f"Added story: {story_key}")
            else:
                # Update existing story with any new file info
                existing = stories[story_key]
                if existing.get("raw_path") != file_info['raw_path']:
                    existing["raw_path"] = file_info['raw_path']
                    existing["rel_path"] = file_info['rel_path']
                    updated_count += 1

            # Handle series association
            if file_info['series']:
                if file_info['series'] not in series_data:
                    series_data[file_info['series']] = {
                        "name": file_info['series'],
                        "total_stories": 0,
                        "published": 0,
                        "spacing_days": 7,
                        "stories": []
                    }
                if story_key not in series_data[file_info['series']]["stories"]:
                    series_data[file_info['series']]["stories"].append(story_key)

        data = await StoryService._update_series_counts(data)
        data["stories"] = stories
        data["series"] = series_data
        await save_stories_data(data)
        
        return {
            "added": added_count,
            "updated": updated_count,
            "total": len(stories)
        }

    @staticmethod
    async def get_all_stories() -> List[Story]:
        """Get all stories as Story objects"""
        data = await load_stories_data()
        stories_data = data.get("stories", {})
        stories = []
        
        for key, story_dict in stories_data.items():
            story = await StoryService._dict_to_story(key, story_dict)
            if story:
                stories.append(story)
        
        # Sort by createdDate descending
        stories.sort(key=lambda x: x.createdDate or "", reverse=True)
        return stories

    @staticmethod
    async def get_story(story_key: str) -> Optional[Story]:
        """Get a single story by key"""
        data = await load_stories_data()
        clean_key = story_key.replace('.md', '')
        
        # Exact match
        if clean_key in data.get("stories", {}):
            story_dict = data["stories"][clean_key]
            return await StoryService._dict_to_story(clean_key, story_dict)
        
        # Case-insensitive match
        for key, story_dict in data.get("stories", {}).items():
            if key.lower() == clean_key.lower():
                return await StoryService._dict_to_story(key, story_dict)
        
        return None

    @staticmethod
    async def get_story_by_unique_slug(unique_slug: str) -> Optional[Story]:
        """Get story by uniqueSlug"""
        data = await load_stories_data()
        stories = data.get("stories", {})
        
        for story_key, story_data in stories.items():
            if story_data.get("uniqueSlug") == unique_slug:
                return await StoryService._dict_to_story(story_key, story_data)
        
        return None
    
    @staticmethod
    async def get_story_by_name(name: str) -> Optional[Story]:
        """Get story by uniqueSlug"""
        data = await load_stories_data()
        stories = data.get("stories", {})
        
        for story_key, story_data in stories.items():
            if story_data.get("name") == name:
                return await StoryService._dict_to_story(story_key, story_data)
        
        return None
    
    
    @staticmethod
    async def update_story_by_unique_slug(unique_slug: str, update_data: StoryUpdate) -> Optional[Story]:
        """Update story by uniqueSlug"""
        story = await StoryService.get_story_by_unique_slug(unique_slug)
        if not story:
            return None
        
        return await StoryService.update_story(story.key, update_data)

    @staticmethod
    async def create_story(story_data: StoryCreate) -> Story:
        """Create a new story"""
        data = await load_stories_data()
        folder = story_data.folder or "."
        clean_title = story_data.title.strip()
        story_key = normalize_story_key(folder, clean_title)

        if story_key in data.get("stories", {}):
            raise ValueError(f"Story already exists: {story_key}")

        clean_series = story_data.series.strip() if story_data.series else None
        clean_notes = story_data.notes.strip() if story_data.notes else ""
        
        # Handle medium_url extraction
        medium_url = story_data.medium_url
        medium_publication = story_data.medium_publication
        medium_first_published = story_data.medium_first_published
        medium_reading_time = story_data.medium_reading_time or story_data.read_time
        
        new_story = {
            "uniqueSlug": story_data.uniqueSlug,
            "title": clean_title,
            "name": clean_title,
            "folder": folder,
            "series": clean_series,
            "status": story_data.status or "Draft",
            "createdDate": story_data.createdDate or datetime.now().strftime("%Y-%m-%d"),
            "publishedDate": story_data.publishedDate,
            "publishedDueDate": story_data.publishedDueDate,
            "lastUpdated": datetime.now().isoformat(),
            "notes": clean_notes,
            "tags": story_data.tags or [],
            "bookmarked": story_data.bookmarked or False,
            "leaderboard": story_data.leaderboard or False,
            "medium_url": medium_url,
            "medium_publication": medium_publication,
            "medium_first_published": medium_first_published,
            "medium_reading_time": medium_reading_time,
            "read_time": story_data.read_time,
            "word_count": story_data.word_count,
            "linkedin_status": story_data.linkedin_status,
            "linkedin_timestamp": story_data.linkedin_timestamp,
            "linkedin_impressions": story_data.linkedin_impressions or 0,
            "linkedin_url": story_data.linkedin_url,
            "lifetime_reads": 0,
            "lifetime_views": 0,
            "lifetime_claps": 0,
            "presentation_count": 0
        }

        data["stories"][story_key] = new_story
        
        # Handle series association
        if clean_series:
            series_data = data.get("series", {})
            if clean_series not in series_data:
                series_data[clean_series] = {
                    "name": clean_series,
                    "total_stories": 0,
                    "published": 0,
                    "spacing_days": 7,
                    "stories": []
                }
            if story_key not in series_data[clean_series]["stories"]:
                series_data[clean_series]["stories"].append(story_key)
            data["series"] = series_data
            data = await StoryService._update_series_counts(data)
        
        await save_stories_data(data)
        return await StoryService._dict_to_story(story_key, new_story)

    @staticmethod
    async def update_story(story_key: str, update_data: StoryUpdate) -> Optional[Story]:
        """Update story by key"""
        data = await load_stories_data()
        clean_key = story_key.replace('.md', '')
        
        # Find the actual key (case-insensitive)
        actual_key = None
        if clean_key in data["stories"]:
            actual_key = clean_key
        else:
            for key in data["stories"].keys():
                if key.lower() == clean_key.lower():
                    actual_key = key
                    break
        
        if not actual_key:
            return None

        story = data["stories"][actual_key]
        old_series = story.get("series")
        old_status = story.get("status")
        
        update_dict = update_data.model_dump(exclude_unset=True)
        series_in_update = 'series' in update_dict
        
        for field, value in update_dict.items():
            if value is not None:
                if isinstance(value, str):
                    story[field] = value.strip()
                elif isinstance(value, list):
                    cleaned_list = [item.strip() if isinstance(item, str) else item for item in value]
                    story[field] = cleaned_list
                elif isinstance(value, dict):
                    if field not in story:
                        story[field] = {}
                    for sub_field, sub_value in value.items():
                        if sub_value is not None:
                            story[field][sub_field] = sub_value
                else:
                    story[field] = value
            else:
                # Only set to None if the field exists
                if field in story:
                    story[field] = None

        story["lastUpdated"] = datetime.now().isoformat()
        
        new_series = story.get("series")
        new_status = story.get("status")
        
        # Update series counts if series or status changed
        if series_in_update and old_series != new_series:
            data = await StoryService._update_series_counts(data)
        elif old_status != new_status:
            data = await StoryService._update_series_counts(data)
        
        await save_stories_data(data)
        return await StoryService._dict_to_story(actual_key, story)

    @staticmethod
    async def publish_story(story_key: str, medium_url: str = None) -> Optional[Story]:
        """Publish a story"""
        update_data = {
            "status": "Published",
            "publishedDate": datetime.now().strftime("%Y-%m-%d")
        }
        if medium_url:
            update_data["medium_url"] = medium_url
        
        return await StoryService.update_story(story_key, StoryUpdate(**update_data))

    @staticmethod
    async def delete_story(story_key: str) -> bool:
        """Delete a story"""
        data = await load_stories_data()
        clean_key = story_key.replace('.md', '')
        
        # Find the actual key (case-insensitive)
        actual_key = None
        if clean_key in data["stories"]:
            actual_key = clean_key
        else:
            for key in data["stories"].keys():
                if key.lower() == clean_key.lower():
                    actual_key = key
                    break

        if not actual_key:
            return False

        story = data["stories"][actual_key]
        series_name = story.get("series")
        
        # Remove from series
        if series_name:
            series_data = data.get("series", {})
            if series_name in series_data:
                if actual_key in series_data[series_name]["stories"]:
                    series_data[series_name]["stories"].remove(actual_key)
            data["series"] = series_data
        
        # Delete the story
        del data["stories"][actual_key]
        data = await StoryService._update_series_counts(data)
        
        await save_stories_data(data)
        return True

    # ============================================
    # NEW METHOD: Fetch Medium Stories for a Period
    # ============================================
    
    # ============New Method
    @staticmethod
    async def fetch_medium_story_stats(post_id: str, period: str) -> Dict[str, Any]:
        """Fetch stats for a single story and update stories.json."""
        from datetime import datetime as dt_module
        
        logger.info(f"Fetching story stats for post_id: {post_id}, period: {period}")
        
        api_service = get_medium_api_service()
        
        if not api_service.is_authenticated():
            return {
                "success": False,
                "message": "Not authenticated",
                "post_id": post_id,
                "period": period
            }
        
        response = api_service.fetch_medium_story_stats(post_id, period)
        
        if not response:
            return {
                "success": False,
                "message": f"No stats found",
                "post_id": post_id,
                "period": period
            }
        
        # Direct extraction - NO "lifetime" object
        presentation_count = response.get('presentation_count', 0)
        reads = response.get('reads', 0)
        views = response.get('views', 0)
        feed_ctr = response.get('feed_click_through_rate', 0)
        monthly_data = response.get('monthly', {})
        
        # Find story in stories.json
        data = await load_stories_data()
        stories = data.get("stories", {})
        
        story_key = None
        story_data = None
        
        for key, story in stories.items():
            medium_id = story.get("medium", {}).get("id", "") if story.get("medium") else ""
            if post_id == medium_id:
                story_key = key
                story_data = story
                break
        
        if not story_key:
            return {
                "success": False,
                "message": f"Story not found",
                "post_id": post_id,
                "period": period
            }
        
        # Update top-level fields
        story_data['lifetime_reads'] = reads
        story_data['lifetime_views'] = views
        story_data['presentation_count'] = presentation_count
        story_data['feed_click_through_rate'] = feed_ctr
        story_data['lastUpdated'] = dt_module.now().isoformat()
        
        # Update medium.totalStats
        if 'medium' not in story_data:
            story_data['medium'] = {}
        
        if 'totalStats' in story_data['medium']:
            story_data['medium']['totalStats']['presentations'] = presentation_count
            story_data['medium']['totalStats']['views'] = views
            story_data['medium']['totalStats']['reads'] = reads
        
        # Build monthly entry
        total_reads = monthly_data.get('total_reads', 0)
        total_views = monthly_data.get('total_views', 0)
        member_reads = monthly_data.get('member_reads', 0)
        
        read_ratio = round((total_reads / total_views) * 100, 1) if total_views > 0 else 0
        member_percent = round((member_reads / total_reads) * 100, 1) if total_reads > 0 else 0
        
        monthly_entry = {
            "period": period,
            "presentations": presentation_count,
            "views": total_views,
            "reads": total_reads,
            "claps": monthly_data.get('claps', 0),
            "responses": monthly_data.get('replies', 0),
            "medium_member_reads": monthly_data.get('member_reads', 0),
            "medium_member_views": monthly_data.get('member_views', 0),
            "medium_nonmember_reads": monthly_data.get('nonmember_reads', 0),
            "medium_nonmember_views": monthly_data.get('nonmember_views', 0),
            "medium_read_ratio": read_ratio,
            "medium_member_read_percentage": member_percent,
            "medium_new_followers": monthly_data.get('new_followers', 0),
            "medium_highlights": monthly_data.get('highlights', 0)
        }
        
        # Update medium.monthlyStats
        if 'monthlyStats' not in story_data['medium']:
            story_data['medium']['monthlyStats'] = []
        
        found = False
        for i, stat in enumerate(story_data['medium']['monthlyStats']):
            if stat and stat.get('period') == period:
                story_data['medium']['monthlyStats'][i] = monthly_entry
                found = True
                break
        
        if not found:
            story_data['medium']['monthlyStats'].append(monthly_entry)
        
        story_data['medium']['monthlyStats'].sort(key=lambda x: x.get('period', ''), reverse=True)
        
        await save_stories_data(data)
        
        return {
            "success": True,
            "message": f"Stats saved for {period}",
            "post_id": post_id,
            "period": period,
            "story_key": story_key,
            "story_name": story_data.get('name', story_data.get('title')),
            "updated": True
        }
    # ============New Method END
    
    @staticmethod
    async def fetch_medium_stats(period: str) -> Dict[str, Any]:
        """
        Fetch ALL published posts from Medium API for a specific period.
        
        MATCHES BY EXACT FULL TITLE after normalization.
        """
        from datetime import datetime as dt_module
        
        current_period = dt_module.now().strftime("%Y-%m")
        is_current_period = (period == current_period)
        
        logger.info(f"Fetching Medium stories for period: {period}")
        
        api_service = get_medium_api_service()
        
        if not api_service.is_authenticated():
            return {
                "success": False,
                "message": "Not authenticated. Please login to Medium.",
                "period": period,
                "new_stories": 0,
                "updated_stories": 0,
                "total_posts": 0
            }
        
        posts = api_service.fetch_medium_stat(period)
        
        if not posts:
            return {
                "success": False,
                "message": f"No posts found from Medium API for {period}",
                "period": period,
                "new_stories": 0,
                "updated_stories": 0,
                "total_posts": 0
            }
        
        logger.info(f"Processing {len(posts)} posts from Medium API")
        
        data = await load_stories_data()
        stories = data.get("stories", {})
        series_data = data.get("series", {})
        
        if "Medium" not in series_data:
            series_data["Medium"] = {
                "name": "Medium",
                "total_stories": 0,
                "published": 0,
                "spacing_days": 7,
                "stories": []
            }
        
        new_count = 0
        updated_count = 0
        processed_posts = []
        
        def normalize_title(title: str) -> str:
            """
            Normalize title for exact matching.
            - Preserves FULL title length
            - Only normalizes case, spaces, punctuation, unicode
            - Does NOT remove words or truncate
            """
            if not title:
                return ""
            import unicodedata
            import re
            # Normalize unicode characters (e.g., â€” becomes --)
            title = unicodedata.normalize('NFKD', title)
            # Encode to ASCII, ignore non-ASCII chars (removes diacritics)
            title = title.encode('ASCII', 'ignore').decode('ASCII')
            # Convert to lowercase
            title = title.lower()
            # Replace all whitespace, hyphens, underscores with single space
            title = re.sub(r'[\s\-_]+', ' ', title)
            # Remove all punctuation and special characters (keep alphanumeric and space)
            title = re.sub(r'[^\w\s]', '', title)
            # Collapse multiple spaces to single space
            title = re.sub(r'\s+', ' ', title)
            # Strip leading/trailing spaces
            title = title.strip()
            return title
                
        # Build normalized title mapping from existing stories
        title_to_story_key = {}
        for story_key, story_data in stories.items():
            story_title = story_data.get('title') or story_data.get('name')
            if story_title:
                normalized = normalize_title(story_title)
                title_to_story_key[normalized] = story_key
                logger.debug(f"Mapping: '{normalized}' -> {story_key}")
        
        for post in posts:
            title = post.get('title', '')
            if not title:
                continue
            
            medium_url = post.get('mediumUrl', '')
            unique_slug = post.get('uniqueSlug', '')
            first_published_at = post.get('firstPublishedAt')
            
            # Parse published date from firstPublishedAt
            published_date = None
            if first_published_at:
                if isinstance(first_published_at, (int, float)):
                    published_date = dt_module.fromtimestamp(first_published_at / 1000).strftime("%Y-%m-%d")
            
            # Extract stats
            total_stats = post.get('totalStats', {})
            presentations = total_stats.get('presentations', 0)
            views = total_stats.get('views', 0)
            reads = total_stats.get('reads', 0)
            
            reading_time = post.get('readingTime', 0)
            word_count = post.get('wordCount', 0)
            clap_count = post.get('clapCount', 0)
            responses_count = post.get('responsesCount', 0)
            
            # Extract earnings
            earnings = post.get('earnings', {})
            total_earnings = earnings.get('total', {})
            total_earnings_nanos = total_earnings.get('nanos', 0)
            
            monthly_earnings = earnings.get('monthlyEarnings', {})
            monthly_earnings_nanos = monthly_earnings.get('nanos', 0)
            
            # Extract creator
            creator_data = post.get('creator', {})
            creator = None
            if creator_data:
                creator = {
                    "id": creator_data.get('id', ''),
                    "username": creator_data.get('username', ''),
                    "name": creator_data.get('name', ''),
                    "bio": creator_data.get('bio', ''),
                    "imageId": creator_data.get('imageId'),
                    "twitterScreenName": creator_data.get('twitterScreenName'),
                    "createdAt": creator_data.get('createdAt')
                }
            
            # Extract collection
            collection_data = post.get('collection', {})
            collection = None
            if collection_data:
                collection = {
                    "id": collection_data.get('id', ''),
                    "name": collection_data.get('name', ''),
                    "slug": collection_data.get('slug', ''),
                    "domain": collection_data.get('domain', ''),
                    "subscriberCount": collection_data.get('subscriberCount', 0),
                    "createdAt": collection_data.get('createdAt', 0)
                }
            
            # Extract tags
            tags_data = post.get('tags', [])
            tags = [t.get('id', '') if isinstance(t, dict) else t for t in tags_data]
            
            # Build medium object
            medium_object = {
                "id": post.get('id', ''),
                "__typename": "Post",
                "title": title,
                "uniqueSlug": unique_slug,
                "mediumUrl": medium_url,
                "createdAt": post.get('createdAt', 0),
                "updatedAt": post.get('updatedAt', 0),
                "firstPublishedAt": first_published_at,
                "readingTime": reading_time if is_current_period else 0,
                "wordCount": word_count if is_current_period else 0,
                "clapCount": clap_count if is_current_period else 0,
                "responsesCount": responses_count if is_current_period else 0,
                "voterCount": post.get('voterCount', 0),
                "isLocked": post.get('isLocked', False),
                "visibility": post.get('visibility', 'LOCKED'),
                "isSeries": post.get('isSeries', False),
                "isShortform": post.get('isShortform', False),
                "firstBoostedAt": post.get('firstBoostedAt'),
                "license": post.get('license', 'ALL_RIGHTS_RESERVED'),
                "tags": tags,
                "creator": creator,
                "collection": collection
            }
            
            if is_current_period:
                medium_object["totalStats"] = {
                    "period": "total",
                    "presentations": presentations,
                    "views": views,
                    "reads": reads,
                    "__typename": "SummaryPostStat"
                }
                medium_object["totalEarnings"] = {
                    "period": "total",
                    "currencyCode": total_earnings.get('currencyCode', 'USD'),
                    "units": total_earnings.get('units', 0),
                    "nanos": total_earnings_nanos
                }
            
            monthly_stats_entry = {
                "period": period,
                "presentations": presentations,
                "views": views,
                "reads": reads
            }
            
            monthly_earnings_entry = {
                "period": period,
                "currencyCode": monthly_earnings.get('currencyCode', 'USD'),
                "units": monthly_earnings.get('units', 0),
                "nanos": monthly_earnings_nanos
            }
            
            # EXACT FULL TITLE MATCH after normalization
            normalized_title = normalize_title(title)
            existing_story_key = title_to_story_key.get(normalized_title)
            
            logger.info(f"Post title: '{title}'")
            logger.info(f"Normalized: '{normalized_title}'")
            logger.info(f"Match found: {existing_story_key is not None}")
            
            if existing_story_key:
                # UPDATE existing story
                story_data = stories[existing_story_key]
                
                # Update basic fields
                story_data['title'] = title
                story_data['name'] = title
                story_data['status'] = "Published"
                story_data['publishedDate'] = published_date  # firstPublishedAt saved here
                story_data['lastUpdated'] = dt_module.now().isoformat()
                story_data['medium_url'] = medium_url
                
                # Update or create medium object
                if 'medium' not in story_data:
                    story_data['medium'] = {}
                
                story_data['medium']['id'] = post.get('id', '')
                story_data['medium']['title'] = title
                story_data['medium']['uniqueSlug'] = unique_slug
                story_data['medium']['mediumUrl'] = medium_url
                story_data['medium']['createdAt'] = post.get('createdAt', 0)
                story_data['medium']['updatedAt'] = post.get('updatedAt', 0)
                story_data['medium']['firstPublishedAt'] = first_published_at
                story_data['medium']['voterCount'] = post.get('voterCount', 0)
                story_data['medium']['isLocked'] = post.get('isLocked', False)
                story_data['medium']['visibility'] = post.get('visibility', 'LOCKED')
                story_data['medium']['isSeries'] = post.get('isSeries', False)
                story_data['medium']['isShortform'] = post.get('isShortform', False)
                story_data['medium']['firstBoostedAt'] = post.get('firstBoostedAt')
                story_data['medium']['license'] = post.get('license', 'ALL_RIGHTS_RESERVED')
                story_data['medium']['tags'] = tags
                story_data['medium']['creator'] = creator
                story_data['medium']['collection'] = collection
                
                if is_current_period:
                    story_data['medium']['readingTime'] = reading_time
                    story_data['medium']['wordCount'] = word_count
                    story_data['medium']['clapCount'] = clap_count
                    story_data['medium']['responsesCount'] = responses_count
                    story_data['medium']['totalStats'] = medium_object.get('totalStats')
                    story_data['medium']['totalEarnings'] = medium_object.get('totalEarnings')
                
                # Update monthlyStats
                if 'monthlyStats' not in story_data['medium']:
                    story_data['medium']['monthlyStats'] = []
                
                found = False
                for i, stat in enumerate(story_data['medium']['monthlyStats']):
                    if stat.get('period') == period:
                        story_data['medium']['monthlyStats'][i] = monthly_stats_entry
                        found = True
                        break
                if not found:
                    story_data['medium']['monthlyStats'].append(monthly_stats_entry)
                
                # Update monthlyEarnings
                if 'monthlyEarnings' not in story_data['medium']:
                    story_data['medium']['monthlyEarnings'] = []
                
                found = False
                for i, earn in enumerate(story_data['medium']['monthlyEarnings']):
                    if earn.get('period') == period:
                        story_data['medium']['monthlyEarnings'][i] = monthly_earnings_entry
                        found = True
                        break
                if not found:
                    story_data['medium']['monthlyEarnings'].append(monthly_earnings_entry)
                
                updated_count += 1
                processed_posts.append({"title": title, "action": "updated"})
                logger.info(f"✅ Updated: {title}")
                
            else:
                # CREATE new story
                import re
                # Create a safe story key from normalized title
                safe_key = re.sub(r'[^a-z0-9]+', '-', normalized_title)
                safe_key = safe_key.strip('-')
                story_key = f"Medium Import/{safe_key}"
                
                new_story = {
                    "uniqueSlug": unique_slug,
                    "title": title,
                    "name": title,
                    "folder": "Medium Import",
                    "series": "Medium",
                    "status": "Published",
                    "createdDate": published_date or dt_module.now().strftime("%Y-%m-%d"),
                    "publishedDate": published_date,
                    "lastUpdated": dt_module.now().isoformat(),
                    "notes": f"Imported from refresh for {period}",
                    "tags": tags,
                    "bookmarked": False,
                    "leaderboard": False,
                    "medium_url": medium_url,
                    "medium": medium_object
                }
                
                # Ensure monthlyStats and monthlyEarnings are set
                if 'monthlyStats' not in new_story['medium']:
                    new_story['medium']['monthlyStats'] = [monthly_stats_entry]
                if 'monthlyEarnings' not in new_story['medium']:
                    new_story['medium']['monthlyEarnings'] = [monthly_earnings_entry]
                
                stories[story_key] = new_story
                
                if story_key not in series_data["Medium"]["stories"]:
                    series_data["Medium"]["stories"].append(story_key)
                
                # Add to mapping for future posts in this batch
                title_to_story_key[normalized_title] = story_key
                
                new_count += 1
                processed_posts.append({"title": title, "action": "created"})
                logger.info(f"✨ Created: {title}")
        
        # Update series counts
        series_data["Medium"]["total_stories"] = len(series_data["Medium"]["stories"])
        series_data["Medium"]["published"] = len(series_data["Medium"]["stories"])
        
        data["stories"] = stories
        data["series"] = series_data
        await save_stories_data(data)
        
        logger.info(f"Refresh completed: {new_count} new, {updated_count} updated")
        
        return {
            "success": True,
            "message": f"Successfully fetched {len(posts)} posts from Medium",
            "period": period,
            "is_current_period": is_current_period,
            "total_posts": len(posts),
            "new_stories": new_count,
            "updated_stories": updated_count,
            "processed_posts": processed_posts[:20]
        }
    
    @staticmethod
    async def _dict_to_story(key: str, story_dict: dict) -> Optional[Story]:
        """Convert dictionary to Story object"""
        try:
            # Ensure uniqueSlug exists
            unique_slug = story_dict.get('uniqueSlug')
            if not unique_slug:
                title = story_dict.get('title', story_dict.get('name', key))
                unique_slug = title.lower().replace(' ', '-').replace(':', '').replace('/', '-').replace('(', '').replace(')', '')[:100]
            
            # Parse medium data if present
            medium = None
            medium_data = story_dict.get('medium')
            if medium_data and isinstance(medium_data, dict):
                # Parse totalStats - handle None values
                total_stats_data = medium_data.get('totalStats', {})
                total_stats = None
                if total_stats_data:
                    total_stats = Stats(
                        period=total_stats_data.get('period', 'total'),
                        presentations=total_stats_data.get('presentations') or 0,  # Handle None
                        views=total_stats_data.get('views') or 0,  # Handle None
                        reads=total_stats_data.get('reads') or 0   # Handle None
                    )
                
                # Parse monthlyStats
                monthly_stats_list = []
                for stat in medium_data.get('monthlyStats', []):
                    monthly_stats_list.append(Stats(
                        period=stat.get('period', ''),
                        presentations=stat.get('presentations') or 0,
                        views=stat.get('views') or 0,
                        reads=stat.get('reads') or 0
                    ))
                
                # Parse totalEarnings - handle None values
                total_earnings_data = medium_data.get('totalEarnings', {})
                total_earnings = None
                if total_earnings_data:
                    total_earnings = Earning(
                        period=total_earnings_data.get('period', 'total'),
                        currencyCode=total_earnings_data.get('currencyCode', 'USD'),
                        units=total_earnings_data.get('units') or 0,
                        nanos=total_earnings_data.get('nanos') or 0
                    )
                
                # Parse monthlyEarnings
                monthly_earnings_list = []
                for earn in medium_data.get('monthlyEarnings', []):
                    monthly_earnings_list.append(Earning(
                        period=earn.get('period', ''),
                        currencyCode=earn.get('currencyCode', 'USD'),
                        units=earn.get('units') or 0,
                        nanos=earn.get('nanos') or 0
                    ))
                
                # Parse tags (list of strings)
                tags = medium_data.get('tags', [])
                if tags is None:
                    tags = []
                
                # Parse creator
                creator_data = medium_data.get('creator')
                creator = None
                if creator_data and isinstance(creator_data, dict):
                    creator = Creator(
                        id=creator_data.get('id', ''),
                        username=creator_data.get('username', ''),
                        name=creator_data.get('name', ''),
                        bio=creator_data.get('bio') or '',
                        imageId=creator_data.get('imageId'),
                        twitterScreenName=creator_data.get('twitterScreenName'),
                        createdAt=creator_data.get('createdAt')
                    )
                
                # Parse collection
                collection_data = medium_data.get('collection')
                collection = None
                if collection_data and isinstance(collection_data, dict):
                    collection = Collection(
                        id=collection_data.get('id', ''),
                        name=collection_data.get('name', ''),
                        slug=collection_data.get('slug', ''),
                        domain=collection_data.get('domain', ''),
                        subscriberCount=collection_data.get('subscriberCount') or 0,
                        createdAt=collection_data.get('createdAt') or 0
                    )
                
                medium = MediumPost(
                    id=medium_data.get('id', ''),
                    __typename=medium_data.get('__typename', 'Post'),
                    title=medium_data.get('title', ''),
                    uniqueSlug=medium_data.get('uniqueSlug', unique_slug),
                    mediumUrl=medium_data.get('mediumUrl', ''),
                    createdAt=medium_data.get('createdAt') or 0,
                    updatedAt=medium_data.get('updatedAt') or 0,
                    firstPublishedAt=medium_data.get('firstPublishedAt'),
                    totalStats=total_stats,
                    monthlyStats=monthly_stats_list,
                    readingTime=medium_data.get('readingTime') or 0,
                    wordCount=medium_data.get('wordCount') or 0,
                    clapCount=medium_data.get('clapCount') or 0,
                    responsesCount=medium_data.get('responsesCount') or 0,
                    voterCount=medium_data.get('voterCount') or 0,
                    isLocked=medium_data.get('isLocked', False),
                    visibility=medium_data.get('visibility', 'LOCKED'),
                    isSeries=medium_data.get('isSeries', False),
                    isShortform=medium_data.get('isShortform', False),
                    firstBoostedAt=medium_data.get('firstBoostedAt'),
                    license=medium_data.get('license', 'ALL_RIGHTS_RESERVED'),
                    tags=tags,
                    totalEarnings=total_earnings,
                    monthlyEarnings=monthly_earnings_list,
                    creator=creator,
                    collection=collection
                )
            
            # Parse LinkedIn data
            linkedin = None
            linkedin_data = story_dict.get('linkedin')
            if linkedin_data and isinstance(linkedin_data, dict):
                linkedin = LinkedIn(
                    type=linkedin_data.get('type', LinkedInPostType.ARTICLE),
                    status=linkedin_data.get('status'),
                    timestamp=linkedin_data.get('timestamp'),
                    impressions=linkedin_data.get('impressions') or 0,
                    url=linkedin_data.get('url')
                )
            else:
                # Handle legacy LinkedIn fields
                linkedin_status = story_dict.get('linkedin_status')
                if linkedin_status:
                    linkedin = LinkedIn(
                        type=LinkedInPostType.ARTICLE,
                        status=linkedin_status,
                        timestamp=story_dict.get('linkedin_timestamp'),
                        impressions=story_dict.get('linkedin_impressions') or 0,
                        url=story_dict.get('linkedin_url')
                    )
            
            # Create the Story object with safe value handling
            story = Story(
                uniqueSlug=unique_slug,
                title=story_dict.get('title', story_dict.get('name', key)),
                key=key,
                folder=story_dict.get('folder', 'Miscellaneous'),
                series=story_dict.get('series'),
                status=story_dict.get('status', 'Draft'),
                createdDate=story_dict.get('createdDate', story_dict.get('created_date', '')),
                publishedDate=story_dict.get('publishedDate', story_dict.get('publishedDate')),
                publishedDueDate=story_dict.get('publishedDueDate', story_dict.get('published_due_date')),
                lastUpdated=story_dict.get('lastUpdated', story_dict.get('last_updated')),
                notes=story_dict.get('notes') or '',
                tags=story_dict.get('tags') or [],
                word_count=story_dict.get('word_count') or 0,
                read_time=story_dict.get('read_time') or 0,
                bookmarked=story_dict.get('bookmarked') or False,
                leaderboard=story_dict.get('leaderboard') or False,
                medium=medium,
                linkedin=linkedin,
                # Legacy fields for backward compatibility
                name=story_dict.get('name', story_dict.get('title')),
                medium_url=story_dict.get('medium_url'),
                medium_publication=story_dict.get('medium_publication'),
                medium_first_published=story_dict.get('medium_first_published'),
                medium_reading_time=story_dict.get('medium_reading_time') or 0,
                medium_new_followers=story_dict.get('medium_new_followers') or 0,
                lifetime_reads=story_dict.get('lifetime_reads') or 0,
                lifetime_views=story_dict.get('lifetime_views') or 0,
                lifetime_claps=story_dict.get('lifetime_claps') or 0,
                presentation_count=story_dict.get('presentation_count') or 0,
                feed_click_through_rate=story_dict.get('feed_click_through_rate') or 0,
                linkedin_status=story_dict.get('linkedin_status'),
                linkedin_timestamp=story_dict.get('linkedin_timestamp'),
                linkedin_impressions=story_dict.get('linkedin_impressions') or 0,
                linkedin_url=story_dict.get('linkedin_url')
            )
            
            return story
        except Exception as e:
            logger.error(f"Error converting dict to story for key {key}: {e}")
            import traceback
            traceback.print_exc()
            return None