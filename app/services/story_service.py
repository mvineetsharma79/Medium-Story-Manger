from typing import List, Dict, Any, Optional
from datetime import datetime
import re

from app.services.file_service import (
    load_stories_data, save_stories_data, scan_markdown_files,
    parse_series_number
)
from app.models import StoryCreate, StoryUpdate, StoryResponse

class StoryService:
    @staticmethod
    async def sync_with_filesystem() -> Dict[str, Any]:
        """Sync stories.json with filesystem, adding new stories"""
        data = await load_stories_data()
        discovered = await scan_markdown_files()
        stories = data.get("stories", {})
        series_data = data.get("series", {})
        
        discovered_keys = set()
        
        for file_info in discovered:
            story_key = file_info['name'] if file_info['folder'] == '.' else f"{file_info['folder']}/{file_info['name']}"
            discovered_keys.add(story_key)
            
            if story_key not in stories:
                # New story - add with defaults
                stories[story_key] = {
                    "name": file_info['name'],
                    "folder": file_info['folder'],
                    "series": file_info['series'],
                    "rel_path": file_info['rel_path'],
                    "status": "Draft",
                    "published_date": None,
                    "created_date": datetime.now().strftime("%Y-%m-%d"),
                    "tags": [],
                    "read_time": None,
                    "medium_url": None,
                    "notes": ""
                }
            
            # Update series tracking
            if file_info['series']:
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
        """Get a single story by key"""
        data = await load_stories_data()
        story = data.get("stories", {}).get(story_key)
        
        if story:
            return StoryResponse(key=story_key, **story)
        return None
    
    @staticmethod
    async def create_story(story_data: StoryCreate) -> StoryResponse:
        """Create a new story"""
        data = await load_stories_data()
        stories = data.get("stories", {})
        
        # Generate story key
        folder = story_data.folder or "."
        story_key = f"{folder}/{story_data.name}" if folder != "." else story_data.name
        
        if story_key in stories:
            raise ValueError(f"Story {story_key} already exists")
        
        new_story = {
            "name": story_data.name,
            "folder": folder,
            "series": story_data.series,
            "rel_path": story_data.name,  # Will be updated on sync
            "status": "Draft",
            "published_date": None,
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "tags": story_data.tags,
            "read_time": story_data.read_time,
            "medium_url": None,
            "notes": story_data.notes
        }
        
        stories[story_key] = new_story
        
        # Update series if applicable
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
        """Update a story"""
        data = await load_stories_data()
        stories = data.get("stories", {})
        
        if story_key not in stories:
            return None
        
        story = stories[story_key]
        
        # Update fields
        for field, value in update_data.model_dump(exclude_unset=True).items():
            if value is not None:
                story[field] = value
        
        # Update series counts if series changed
        await save_stories_data(data)
        
        return StoryResponse(key=story_key, **story)
    
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
        
        if story_key not in stories:
            return False
        
        # Remove from series
        story = stories[story_key]
        if story.get("series"):
            series_name = story["series"]
            series = data.get("series", {}).get(series_name)
            if series and story_key in series.get("stories", []):
                series["stories"].remove(story_key)
        
        del stories[story_key]
        
        await save_stories_data(data)
        return True