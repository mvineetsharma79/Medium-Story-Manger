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
                    # Check status field for "Published"
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
                    "claps": 0, "responses": 0, "bookmarks": 0, "view_count": 0,
                    "read_ratio": 0, "medium_reading_time": 0, "fan_count": 0,
                    "medium_first_published": None, "medium_last_updated": None,
                    "medium_tags": [], "medium_topics": [], "word_count": 0,
                    "medium_title": None, "medium_subtitle": None,
                    "medium_author": None, "medium_publication": None,
                    "last_stats_update": None
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

        # Update series counts - CHECK STATUS, NOT published_date
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
        
        # Try exact match
        if clean_key in data.get("stories", {}):
            story = data["stories"][clean_key]
            return StoryResponse(key=clean_key, **story)
        
        # Try case-insensitive search
        for key, val in data.get("stories", {}).items():
            if key.lower() == clean_key.lower():
                return StoryResponse(key=key, **val)
        
        # Try normalized key (remove special characters)
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
        story_key = f"{folder}/{story_data.name}"

        if story_key in data.get("stories", {}):
            raise ValueError(f"Story exists: {story_key}")

        new_story = {
            "name": story_data.name, "folder": folder, "series": story_data.series,
            "raw_path": f"{folder}/{story_data.name}.md", "rel_path": story_data.name,
            "status": "Draft", "published_date": None,
            "created_date": story_data.created_date or datetime.now().strftime("%Y-%m-%d"),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tags": story_data.tags, "read_time": story_data.read_time,
            "reads": 0, "medium_url": None, "notes": story_data.notes,
            "linkedin_status": None, "linkedin_timestamp": None,
            "linkedin_impressions": 0, "linkedin_url": None,
            "claps": 0, "responses": 0, "bookmarks": 0, "view_count": 0,
            "read_ratio": 0, "medium_reading_time": 0, "fan_count": 0,
            "medium_first_published": None, "medium_last_updated": None,
            "medium_tags": [], "medium_topics": [], "word_count": 0,
            "medium_title": None, "medium_subtitle": None,
            "medium_author": None, "medium_publication": None,
            "last_stats_update": None
        }

        data["stories"][story_key] = new_story
        
        # Update series counts if story belongs to a series
        if story_data.series:
            series_data = data.get("series", {})
            if story_data.series not in series_data:
                series_data[story_data.series] = {
                    "name": story_data.series,
                    "total_stories": 0,
                    "published": 0,
                    "spacing_days": 7,
                    "stories": []
                }
            if story_key not in series_data[story_data.series]["stories"]:
                series_data[story_data.series]["stories"].append(story_key)
            data["series"] = series_data
            # Update series counts
            data = await StoryService._update_series_counts(data)
        
        await save_stories_data(data)
        return StoryResponse(key=story_key, **new_story)

    @staticmethod
    async def update_story(story_key: str, update_data: StoryUpdate) -> Optional[StoryResponse]:
        data = await load_stories_data()
        clean_key = story_key.replace('.md', '')
        
        # Find the actual key if it exists
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

        for field, value in update_dict.items():
            if value is not None:
                story[field] = value

        story["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Check if series changed or status changed to/from Published
        new_series = story.get("series")
        new_status = story.get("status")
        
        if old_series != new_series or old_status != new_status:
            # Update series counts
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

        # Remove from series before deleting
        story = data["stories"][actual_key]
        series_name = story.get("series")
        if series_name:
            series_data = data.get("series", {})
            if series_name in series_data:
                if actual_key in series_data[series_name]["stories"]:
                    series_data[series_name]["stories"].remove(actual_key)
            data["series"] = series_data
        
        del data["stories"][actual_key]
        
        # Update series counts
        data = await StoryService._update_series_counts(data)
        
        await save_stories_data(data)
        return True

    @staticmethod
    async def _save_stories_data(data: Dict[str, Any]) -> None:
        """Internal method to save stories data (used by series router)"""
        await save_stories_data(data)