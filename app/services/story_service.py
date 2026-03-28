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
    @staticmethod
    async def sync_with_filesystem() -> Dict[str, Any]:
        """Sync stories.json with filesystem, adding new stories"""
        data = await load_stories_data()
        discovered = await scan_markdown_files()
        stories = data.get("stories", {})
        series_data = data.get("series", {})
        
        discovered_keys = set()
        
        for file_info in discovered:
            # Create story key without .md extension
            story_key = f"{file_info['folder']}/{file_info['name']}"
            discovered_keys.add(story_key)
            
            if story_key not in stories:
                # New story - add with defaults
                stories[story_key] = {
                    "name": file_info['name'],
                    "full_name": file_info['full_name'],
                    "folder": file_info['folder'],
                    "series": file_info['series'],
                    "raw_path": file_info['raw_path'],  # Store raw path for display
                    "rel_path": file_info['rel_path'],  # Store encoded path for links
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
                    "linkedin_url": None
                }
                logger.info(f"Added new story: {story_key}")
            else:
                # Update existing story with missing fields
                existing = stories[story_key]
                if "reads" not in existing:
                    existing["reads"] = 0
                if "last_updated" not in existing:
                    existing["last_updated"] = existing.get("created_date", datetime.now().strftime("%Y-%m-%d"))
                if "linkedin_impressions" not in existing:
                    existing["linkedin_impressions"] = 0
                if "raw_path" not in existing:
                    existing["raw_path"] = file_info['raw_path']
        
        # Update series tracking
        for file_info in discovered:
            if file_info['series']:
                story_key = f"{file_info['folder']}/{file_info['name']}"
                if file_info['series'] not in series_data:
                    series_data[file_info['series']] = {
                        "name": file_info['series'],
                        "total_stories": 0,
                        "published": 0,
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
                    if stories[story_key].get("published_date"):
                        published += 1
            series_info["total_stories"] = total
            series_info["published"] = published
        
        data["stories"] = stories
        data["series"] = series_data
        
        await save_stories_data(data)
        return data
    
    @staticmethod
    async def get_all_stories() -> List[StoryResponse]:
        """Get all stories"""
        data = await load_stories_data()
        stories = data.get("stories", {})
        
        return [
            StoryResponse(key=key, **story)
            for key, story in stories.items()
        ]
    
    @staticmethod
    async def get_story(story_key: str) -> Optional[StoryResponse]:
        """Get a single story by key with flexible matching"""
        data = await load_stories_data()
        stories = data.get("stories", {})
        
        # Clean the key
        clean_key = story_key
        if clean_key.lower().endswith('.md'):
            clean_key = clean_key[:-3]
        
        # Try exact match
        if clean_key in stories:
            story = stories[clean_key]
            return StoryResponse(key=clean_key, **story)
        
        # Try URL decoded version
        decoded_key = urllib.parse.unquote(clean_key)
        if decoded_key in stories:
            story = stories[decoded_key]
            return StoryResponse(key=decoded_key, **story)
        
        # Try case-insensitive search
        for key, val in stories.items():
            if key.lower() == clean_key.lower() or key.lower() == decoded_key.lower():
                return StoryResponse(key=key, **val)
        
        # Try partial match (for debugging)
        logger.warning(f"Story not found: {story_key} (cleaned: {clean_key})")
        logger.info(f"Available keys: {list(stories.keys())[:10]}")
        return None
    
    @staticmethod
    async def create_story(story_data: StoryCreate) -> StoryResponse:
        """Create a new story"""
        data = await load_stories_data()
        stories = data.get("stories", {})
        
        folder = story_data.folder or "."
        story_key = f"{folder}/{story_data.name}"
        
        if story_key in stories:
            raise ValueError(f"Story {story_key} already exists")
        
        created_date = story_data.created_date or datetime.now().strftime("%Y-%m-%d")
        
        new_story = {
            "name": story_data.name,
            "full_name": story_data.name + ".md",
            "folder": folder,
            "series": story_data.series,
            "rel_path": story_data.name,
            "status": "Draft",
            "published_date": None,
            "created_date": created_date,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tags": story_data.tags,
            "read_time": story_data.read_time,
            "reads": story_data.reads,
            "medium_url": None,
            "notes": story_data.notes,
            "linkedin_status": None,
            "linkedin_timestamp": None,
            "linkedin_impressions": 0,
            "linkedin_url": None
        }
        
        stories[story_key] = new_story
        
        if story_data.series:
            series_data = data.get("series", {})
            if story_data.series not in series_data:
                series_data[story_data.series] = {
                    "name": story_data.series,
                    "total_stories": 0,
                    "published": 0,
                    "stories": []
                }
            if story_key not in series_data[story_data.series]["stories"]:
                series_data[story_data.series]["stories"].append(story_key)
            data["series"] = series_data
        
        await save_stories_data(data)
        return StoryResponse(key=story_key, **new_story)
    
    @staticmethod
    async def update_story(story_key: str, update_data: StoryUpdate) -> Optional[StoryResponse]:
        """Update a story with flexible key matching"""
        data = await load_stories_data()
        stories = data.get("stories", {})
        
        # Clean the key
        clean_key = story_key
        if clean_key.lower().endswith('.md'):
            clean_key = clean_key[:-3]
        
        # Try to find the actual key
        actual_key = None
        
        if clean_key in stories:
            actual_key = clean_key
        else:
            decoded_key = urllib.parse.unquote(clean_key)
            if decoded_key in stories:
                actual_key = decoded_key
            else:
                # Case-insensitive search
                for key in stories.keys():
                    if key.lower() == clean_key.lower() or key.lower() == decoded_key.lower():
                        actual_key = key
                        break
        
        if not actual_key:
            logger.warning(f"Story not found for update: {story_key} (cleaned: {clean_key})")
            logger.info(f"Available keys: {list(stories.keys())[:10]}")
            return None
        
        story = stories[actual_key]
        update_dict = update_data.model_dump(exclude_unset=True)
        logger.info(f"Updating story {actual_key} with: {update_dict}")
        
        for field, value in update_dict.items():
            if value is not None:
                if field == "status" and hasattr(value, "value"):
                    story[field] = value.value
                else:
                    story[field] = value
        
        story["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if story.get("status") == "Published" and not story.get("published_date"):
            story["published_date"] = datetime.now().strftime("%Y-%m-%d")
        
        if "reads" not in story:
            story["reads"] = 0
        if "linkedin_impressions" not in story:
            story["linkedin_impressions"] = 0
        
        await save_stories_data(data)
        
        logger.info(f"Successfully updated story: {actual_key}")
        return StoryResponse(key=actual_key, **story)
    
    @staticmethod
    async def publish_story(story_key: str, medium_url: Optional[str] = None) -> Optional[StoryResponse]:
        """Mark a story as published"""
        return await StoryService.update_story(story_key, StoryUpdate(
            status="Published",
            published_date=datetime.now().strftime("%Y-%m-%d"),
            medium_url=medium_url
        ))
    
    @staticmethod
    async def delete_story(story_key: str) -> bool:
        """Delete a story from the JSON (not filesystem)"""
        data = await load_stories_data()
        stories = data.get("stories", {})
        
        clean_key = story_key
        if clean_key.lower().endswith('.md'):
            clean_key = clean_key[:-3]
        
        actual_key = None
        if clean_key in stories:
            actual_key = clean_key
        else:
            decoded_key = urllib.parse.unquote(clean_key)
            if decoded_key in stories:
                actual_key = decoded_key
        
        if not actual_key:
            return False
        
        story = stories[actual_key]
        if story.get("series"):
            series_name = story["series"]
            series = data.get("series", {}).get(series_name)
            if series and actual_key in series.get("stories", []):
                series["stories"].remove(actual_key)
        
        del stories[actual_key]
        await save_stories_data(data)
        return True