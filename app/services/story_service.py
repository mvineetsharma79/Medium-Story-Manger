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
    async def update_story_by_unique_slug(unique_slug: str, update_data: StoryUpdate) -> Optional[Story]:
        """Update story by uniqueSlug"""
        data = await load_stories_data()
        stories = data.get("stories", {})
        
        story_key = None
        for key, story_data in stories.items():
            if story_data.get("uniqueSlug") == unique_slug:
                story_key = key
                break
        
        if not story_key:
            return None
        
        return await StoryService.update_story(story_key, update_data)

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
    
    @staticmethod
    async def fetch_medium_stories(period: str) -> Dict[str, Any]:
        """
        Fetch ALL published posts from Medium API for a specific period.
        
        This method:
        1. Calls MediumAPIService.fetch_medium_stories(period) to get raw posts
        2. For each post, creates or updates the story in stories.json
        3. Updates story level fields ALWAYS
        4. Updates totalStats and totalEarnings ONLY for current period
        5. Updates monthlyStats and monthlyEarnings arrays ALWAYS (create/update by period)
        
        IMPORTANT:
        - folder and series are NEVER updated (remain "Medium" from creation)
        - readingTime, wordCount, clapCount, responsesCount ONLY for current month
        - uniqueSlug is the PRIMARY KEY for story lookup
        
        Args:
            period: Period in YYYY-MM format (e.g., "2026-04")
        
        Returns:
            Dict with success status, counts of new/updated stories
        
        Example:
            result = await StoryService.fetch_medium_stories("2026-04")
            print(f"New: {result['new_stories']}, Updated: {result['updated_stories']}")
        """
        from datetime import datetime as dt_module
        
        # Get current period for comparison (to know if we should update totalStats)
        current_period = dt_module.now().strftime("%Y-%m")
        is_current_period = (period == current_period)
        
        logger.info(f"Fetching Medium stories for period: {period} (is_current_period={is_current_period})")
        
        # Step 1: Call Medium API to get posts
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
        
        posts = api_service.fetch_medium_stories(period)
        
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
        
        # Step 2: Load existing stories.json
        data = await load_stories_data()
        stories = data.get("stories", {})
        series_data = data.get("series", {})
        
        # Ensure "Medium" series exists (for new stories)
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
        
        for post in posts:
            # Extract basic post data
            post_id = post.get('id', '')
            title = post.get('title', '')
            medium_url = post.get('mediumUrl', '')
            unique_slug = post.get('uniqueSlug', '')
            created_at = post.get('createdAt', 0)
            updated_at = post.get('updatedAt', 0)
            first_published_at = post.get('firstPublishedAt')
            
            # Extract stats
            total_stats = post.get('totalStats', {})
            presentations = total_stats.get('presentations', 0)
            views = total_stats.get('views', 0)
            reads = total_stats.get('reads', 0)
            
            # Extract metrics (ONLY update for current period)
            reading_time = post.get('readingTime', 0)
            word_count = post.get('wordCount', 0)
            clap_count = post.get('clapCount', 0)
            responses_count = post.get('responsesCount', 0)
            
            # Extract earnings
            earnings = post.get('earnings', {})
            total_earnings = earnings.get('total', {})
            total_earnings_units = total_earnings.get('units', 0)
            total_earnings_nanos = total_earnings.get('nanos', 0)
            
            monthly_earnings = earnings.get('monthlyEarnings', {})
            monthly_earnings_units = monthly_earnings.get('units', 0)
            monthly_earnings_nanos = monthly_earnings.get('nanos', 0)
            
            # Extract creator info
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
            
            # Extract collection info
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
            
            # Parse published date
            published_date = None
            if first_published_at:
                if isinstance(first_published_at, (int, float)):
                    published_date = dt_module.fromtimestamp(first_published_at / 1000).strftime("%Y-%m-%d")
            
            # Build the medium object (will be stored under story["medium"])
            medium_object = {
                "id": post_id,
                "__typename": "Post",
                "title": title,
                "uniqueSlug": unique_slug,
                "mediumUrl": medium_url,
                "createdAt": created_at,
                "updatedAt": updated_at,
                "firstPublishedAt": first_published_at,
                "readingTime": reading_time if is_current_period else 0,  # Only update for current period
                "wordCount": word_count if is_current_period else 0,      # Only update for current period
                "clapCount": clap_count if is_current_period else 0,      # Only update for current period
                "responsesCount": responses_count if is_current_period else 0,  # Only update for current period
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
            
            # Add totalStats (ONLY update for current period)
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
                    "units": total_earnings_units,
                    "nanos": total_earnings_nanos
                }
            else:
                # For past periods, preserve existing totalStats if they exist
                # Don't overwrite with zero values
                pass
            
            # Add monthlyStats (ALWAYS update for this period)
            # Find existing monthlyStats entry for this period, or create new
            monthly_stats_entry = {
                "period": period,
                "presentations": presentations,
                "views": views,
                "reads": reads
            }
            
            # Add monthlyEarnings (ALWAYS update for this period)
            monthly_earnings_entry = {
                "period": period,
                "currencyCode": monthly_earnings.get('currencyCode', 'USD'),
                "units": monthly_earnings_units,
                "nanos": monthly_earnings_nanos
            }
            
            # Step 3: Find existing story by uniqueSlug (PRIMARY KEY)
            existing_story_key = None
            existing_story_data = None
            
            for key, story_data in stories.items():
                if story_data.get('uniqueSlug') == unique_slug:
                    existing_story_key = key
                    existing_story_data = story_data
                    break
            
            if existing_story_key:
                # UPDATE existing story
                story_data = existing_story_data
                
                # Update story level fields (ALWAYS)
                story_data['title'] = title
                story_data['name'] = title
                story_data['status'] = "Published"
                story_data['publishedDate'] = published_date or story_data.get('publishedDate')
                story_data['lastUpdated'] = dt_module.now().isoformat()
                
                # DO NOT update folder and series (they remain "Medium" from creation)
                
                # Update or create medium object
                if 'medium' not in story_data or story_data['medium'] is None:
                    story_data['medium'] = {}
                
                # Update medium object fields (ALWAYS for id, url, dates, creator, collection)
                story_data['medium']['id'] = post_id
                story_data['medium']['__typename'] = "Post"
                story_data['medium']['title'] = title
                story_data['medium']['uniqueSlug'] = unique_slug
                story_data['medium']['mediumUrl'] = medium_url
                story_data['medium']['createdAt'] = created_at
                story_data['medium']['updatedAt'] = updated_at
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
                
                # Update readingTime, wordCount, clapCount, responsesCount ONLY for current period
                if is_current_period:
                    story_data['medium']['readingTime'] = reading_time
                    story_data['medium']['wordCount'] = word_count
                    story_data['medium']['clapCount'] = clap_count
                    story_data['medium']['responsesCount'] = responses_count
                    
                    # Update totalStats and totalEarnings for current period
                    story_data['medium']['totalStats'] = {
                        "period": "total",
                        "presentations": presentations,
                        "views": views,
                        "reads": reads,
                        "__typename": "SummaryPostStat"
                    }
                    
                    story_data['medium']['totalEarnings'] = {
                        "period": "total",
                        "currencyCode": total_earnings.get('currencyCode', 'USD'),
                        "units": total_earnings_units,
                        "nanos": total_earnings_nanos
                    }
                
                # Update monthlyStats array (ALWAYS)
                if 'monthlyStats' not in story_data['medium']:
                    story_data['medium']['monthlyStats'] = []
                
                # Find existing entry for this period
                found = False
                for i, stat in enumerate(story_data['medium']['monthlyStats']):
                    if stat.get('period') == period:
                        story_data['medium']['monthlyStats'][i] = monthly_stats_entry
                        found = True
                        break
                
                if not found:
                    story_data['medium']['monthlyStats'].append(monthly_stats_entry)
                
                # Update monthlyEarnings array (ALWAYS)
                if 'monthlyEarnings' not in story_data['medium']:
                    story_data['medium']['monthlyEarnings'] = []
                
                # Find existing entry for this period
                found = False
                for i, earn in enumerate(story_data['medium']['monthlyEarnings']):
                    if earn.get('period') == period:
                        story_data['medium']['monthlyEarnings'][i] = monthly_earnings_entry
                        found = True
                        break
                
                if not found:
                    story_data['medium']['monthlyEarnings'].append(monthly_earnings_entry)
                
                updated_count += 1
                processed_posts.append({
                    "uniqueSlug": unique_slug,
                    "title": title,
                    "action": "updated"
                })
                logger.info(f"Updated story: {unique_slug} - {title}")
                
            else:
                # CREATE new story
                story_key = f"Medium Import/{unique_slug}"
                
                # Build the complete story object
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
                    "medium": {
                        "id": post_id,
                        "__typename": "Post",
                        "title": title,
                        "uniqueSlug": unique_slug,
                        "mediumUrl": medium_url,
                        "createdAt": created_at,
                        "updatedAt": updated_at,
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
                        "collection": collection,
                        "monthlyStats": [monthly_stats_entry],
                        "monthlyEarnings": [monthly_earnings_entry]
                    }
                }
                
                # Add totalStats and totalEarnings ONLY for current period
                if is_current_period:
                    new_story["medium"]["totalStats"] = {
                        "period": "total",
                        "presentations": presentations,
                        "views": views,
                        "reads": reads,
                        "__typename": "SummaryPostStat"
                    }
                    new_story["medium"]["totalEarnings"] = {
                        "period": "total",
                        "currencyCode": total_earnings.get('currencyCode', 'USD'),
                        "units": total_earnings_units,
                        "nanos": total_earnings_nanos
                    }
                
                stories[story_key] = new_story
                
                # Add to Medium series
                if story_key not in series_data["Medium"]["stories"]:
                    series_data["Medium"]["stories"].append(story_key)
                
                new_count += 1
                processed_posts.append({
                    "uniqueSlug": unique_slug,
                    "title": title,
                    "action": "created"
                })
                logger.info(f"Created new story: {unique_slug} - {title}")
        
        # Step 4: Update series counts
        series_data["Medium"]["total_stories"] = len(series_data["Medium"]["stories"])
        series_data["Medium"]["published"] = len(series_data["Medium"]["stories"])
        
        # Step 5: Save everything
        data["stories"] = stories
        data["series"] = series_data
        await save_stories_data(data)
        
        logger.info(f"Refresh completed: {new_count} new, {updated_count} updated stories")
        
        return {
            "success": True,
            "message": f"Successfully fetched {len(posts)} posts from Medium",
            "period": period,
            "is_current_period": is_current_period,
            "total_posts": len(posts),
            "new_stories": new_count,
            "updated_stories": updated_count,
            "processed_posts": processed_posts[:20]  # First 20 for response
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
                publishedDate=story_dict.get('publishedDate', story_dict.get('published_date')),
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