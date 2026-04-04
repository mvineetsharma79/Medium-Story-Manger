from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import urllib.parse

from app.services.file_service import (
    load_stories_data, save_stories_data, scan_markdown_files,
    parse_series_number
)
from app.models import StoryCreate, StoryUpdate, StoryResponse

logger = logging.getLogger(__name__)


class StoryService:
    @staticmethod
    async def _update_series_counts(data: Dict[str, Any]) -> Dict[str, Any]:
        """Update total_stories and published counts for all series based on status = Published"""
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

        for file_info in discovered:
            story_key = f"{file_info['folder']}/{file_info['name']}"

            if story_key not in stories:
                stories[story_key] = {
                    "name": file_info['name'],
                    "full_name": file_info.get('full_name', file_info['name'] + '.md'),
                    "folder": file_info['folder'],
                    "series": file_info['series'],
                    "raw_path": file_info['raw_path'],
                    "rel_path": file_info['rel_path'],
                    "status": "Draft",
                    "published_date": None,
                    "created_date": datetime.now().strftime("%Y-%m-%d"),
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "tags": [],
                    "read_time": None,
                    "reads": 0,
                    "medium_url": None,
                    "notes": "",
                    "linkedin_status": None,
                    "linkedin_timestamp": None,
                    "linkedin_impressions": 0,
                    "linkedin_url": None,
                    "claps": 0,
                    "responses": 0,
                    "bookmarks": 0,
                    "view_count": 0,
                    "read_ratio": 0,
                    "medium_reading_time": 0,
                    "fan_count": 0,
                    "medium_first_published": None,
                    "medium_last_updated": None,
                    "medium_tags": [],
                    "medium_topics": [],
                    "word_count": 0,
                    "medium_title": None,
                    "medium_subtitle": None,
                    "medium_author": None,
                    "medium_publication": None,
                    "last_stats_update": None,
                    "bookmarked": False,
                    "medium_member_reads": 0,
                    "medium_member_views": 0,
                    "medium_nonmember_reads": 0,
                    "medium_nonmember_views": 0,
                    "medium_total_views": 0,
                    "medium_claps": 0,
                    "medium_replies": 0,
                    "medium_highlights": 0,
                    "medium_new_followers": 0,
                    "medium_read_ratio": 0,
                    "medium_member_read_percentage": 0,
                    "medium_stats_data": None,
                    "medium_stats_updated": None,
                    "lifetime_reads": 0,
                    "lifetime_claps": 0,
                    "lifetime_views": 0,
                    "presentation_count": 0,
                    "lifetime_tags": [],
                    "lifetime_topics": [],
                    "lifetime_stats_data": None,
                    "lifetime_stats_updated": None,
                    "leaderboard": False,
                    "leaderboard_nanos": 0,
                    "leaderboard_lifetime_nanos": 0
                }
                logger.info(f"Added story: {story_key}")

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

        # Update series counts
        for series_name, series_info in series_data.items():
            total = 0
            published = 0
            for story_key in series_info["stories"]:
                if story_key in stories:
                    total += 1
                    if stories[story_key].get("status") == "Published":
                        published += 1
            series_info["total_stories"] = total
            series_info["published"] = published

        data["stories"] = stories
        data["series"] = series_data
        await save_stories_data(data)
        return data

    @staticmethod
    async def get_all_stories() -> List[StoryResponse]:
        data = await load_stories_data()
        stories = data.get("stories", {})
        return [StoryResponse(key=key, **story) for key, story in stories.items()]

    @staticmethod
    async def get_story(story_key: str) -> Optional[StoryResponse]:
        """Get a single story by key with flexible matching"""
        data = await load_stories_data()
        clean_key = story_key.replace('.md', '')
        
        if clean_key in data.get("stories", {}):
            story = data["stories"][clean_key]
            return StoryResponse(key=clean_key, **story)
        
        for key, val in data.get("stories", {}).items():
            if key.lower() == clean_key.lower():
                return StoryResponse(key=key, **val)
        
        normalized_clean = clean_key.replace(':', '').replace('%3A', '').replace(' ', '')
        for key, val in data.get("stories", {}).items():
            normalized_key = key.replace(':', '').replace('%3A', '').replace(' ', '')
            if normalized_key.lower() == normalized_clean.lower():
                return StoryResponse(key=key, **val)
        
        logger.warning(f"Story not found: {story_key} (cleaned: {clean_key})")
        return None

    @staticmethod
    async def create_story(story_data: StoryCreate) -> StoryResponse:
        data = await load_stories_data()
        folder = story_data.folder or "."
        clean_name = story_data.name.strip()
        story_key = f"{folder}/{clean_name}"

        if story_key in data.get("stories", {}):
            raise ValueError(f"Story exists: {story_key}")

        clean_series = story_data.series.strip() if story_data.series else None
        clean_tags = [tag.strip() for tag in story_data.tags if tag.strip()]
        clean_notes = story_data.notes.strip() if story_data.notes else ""
        
        new_story = {
            "name": clean_name,
            "full_name": clean_name + ".md",
            "folder": folder,
            "series": clean_series,
            "raw_path": f"{folder}/{clean_name}.md",
            "rel_path": clean_name,
            "status": "Draft",
            "published_date": None,
            "created_date": story_data.created_date or datetime.now().strftime("%Y-%m-%d"),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tags": clean_tags,
            "read_time": story_data.read_time,
            "reads": 0,
            "medium_url": story_data.medium_url,
            "notes": clean_notes,
            "linkedin_status": None,
            "linkedin_timestamp": None,
            "linkedin_impressions": 0,
            "linkedin_url": None,
            "claps": 0,
            "responses": 0,
            "bookmarks": 0,
            "view_count": 0,
            "read_ratio": 0,
            "medium_reading_time": story_data.medium_reading_time or 0,
            "fan_count": 0,
            "medium_first_published": story_data.medium_first_published,
            "medium_last_updated": None,
            "medium_tags": [],
            "medium_topics": [],
            "word_count": 0,
            "medium_title": None,
            "medium_subtitle": None,
            "medium_author": None,
            "medium_publication": story_data.medium_publication,
            "last_stats_update": None,
            "bookmarked": False,
            "medium_member_reads": 0,
            "medium_member_views": 0,
            "medium_nonmember_reads": 0,
            "medium_nonmember_views": 0,
            "medium_total_views": 0,
            "medium_claps": 0,
            "medium_replies": 0,
            "medium_highlights": 0,
            "medium_new_followers": 0,
            "medium_read_ratio": 0,
            "medium_member_read_percentage": 0,
            "medium_stats_data": None,
            "medium_stats_updated": None,
            "lifetime_reads": 0,
            "lifetime_claps": 0,
            "lifetime_views": 0,
            "presentation_count": 0,
            "lifetime_tags": [],
            "lifetime_topics": [],
            "lifetime_stats_data": None,
            "lifetime_stats_updated": None,
            "leaderboard": False,
            "leaderboard_nanos": 0,
            "leaderboard_lifetime_nanos": 0
        }

        data["stories"][story_key] = new_story
        
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
        return StoryResponse(key=story_key, **new_story)

    @staticmethod
    async def update_story(story_key: str, update_data: StoryUpdate) -> Optional[StoryResponse]:
        data = await load_stories_data()
        clean_key = story_key.replace('.md', '')
        
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
        
        # Track if series is being updated
        series_in_update = 'series' in update_dict
        
        for field, value in update_dict.items():
            if value is not None:
                if isinstance(value, str):
                    story[field] = value.strip()
                elif isinstance(value, list):
                    cleaned_list = []
                    for item in value:
                        if isinstance(item, str):
                            cleaned_list.append(item.strip())
                        else:
                            cleaned_list.append(item)
                    story[field] = cleaned_list
                else:
                    story[field] = value
            else:
                story[field] = None

        story["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        new_series = story.get("series")
        new_status = story.get("status")
        
        # Only update series counts if series was explicitly updated
        if series_in_update and old_series != new_series:
            data = await StoryService._update_series_counts(data)
        elif old_status != new_status:
            data = await StoryService._update_series_counts(data)
        
        await save_stories_data(data)
        return StoryResponse(key=actual_key, **story)

    @staticmethod
    async def publish_story(story_key: str, medium_url: str = None) -> Optional[StoryResponse]:
        return await StoryService.update_story(story_key, StoryUpdate(
            status="Published",
            published_date=datetime.now().strftime("%Y-%m-%d"),
            medium_url=medium_url
        ))

    @staticmethod
    async def delete_story(story_key: str) -> bool:
        data = await load_stories_data()
        clean_key = story_key.replace('.md', '')
        
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
        if series_name:
            series_data = data.get("series", {})
            if series_name in series_data:
                if actual_key in series_data[series_name]["stories"]:
                    series_data[series_name]["stories"].remove(actual_key)
            data["series"] = series_data
        
        del data["stories"][actual_key]
        data = await StoryService._update_series_counts(data)
        
        await save_stories_data(data)
        return True