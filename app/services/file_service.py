import os
import json
import aiofiles
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

from config import settings

def get_stories_root() -> Path:
    """Get the configured stories root folder"""
    root = Path(settings.stories_root)
    root.mkdir(parents=True, exist_ok=True)
    return root

def get_stories_json_path() -> Path:
    """Get path to stories.json"""
    return get_stories_root() / settings.stories_json

def get_calendar_md_path() -> Path:
    """Get path to publishing calendar markdown"""
    return get_stories_root() / settings.calendar_md

def get_calendar_json_path() -> Path:
    """Get path to publishing calendar JSON"""
    return get_stories_root() / settings.calendar_json

def encode_path_for_markdown(path: str) -> str:
    """Encode special characters for markdown links"""
    parts = path.split('/')
    encoded = []
    for part in parts:
        encoded_part = part.replace(' ', '%20')
        encoded_part = encoded_part.replace('(', '%28')
        encoded_part = encoded_part.replace(')', '%29')
        encoded_part = encoded_part.replace(':', '%3A')
        encoded.append(encoded_part)
    return '/'.join(encoded)

async def load_stories_data() -> Dict[str, Any]:
    """Load stories.json"""
    json_path = get_stories_json_path()
    
    default_data = {
        "version": "1.0",
        "last_updated": datetime.now().isoformat(),
        "stories": {},
        "series": {},
        "calendar_settings": {
            "series_spacing_days": settings.default_series_spacing_days,
            "stories_per_week": settings.default_stories_per_week,
            "preferred_publish_days": settings.preferred_publish_days,
            "start_date": datetime.now().strftime("%Y-%m-%d")
        }
    }
    
    if json_path.exists():
        async with aiofiles.open(json_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            data = json.loads(content)
            # Merge with default settings for missing keys
            for key, value in default_data.items():
                if key not in data:
                    data[key] = value
            return data
    
    return default_data

async def save_stories_data(data: Dict[str, Any]) -> None:
    """Save stories.json"""
    data["last_updated"] = datetime.now().isoformat()
    json_path = get_stories_json_path()
    
    async with aiofiles.open(json_path, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, indent=2, ensure_ascii=False))

async def scan_markdown_files() -> List[Dict[str, str]]:
    """Scan root and subfolders for markdown files"""
    discovered = []
    root = get_stories_root()
    
    if not root.exists():
        return discovered
    
    # Scan root level
    for file in root.iterdir():
        if file.is_file() and file.suffix.lower() == '.md':
            if file.name not in ["Stories.md", "README.md", settings.calendar_md]:
                discovered.append({
                    'name': file.name,
                    'path': str(file),
                    'rel_path': encode_path_for_markdown(file.name),
                    'folder': '.',
                    'series': None
                })
    
    # Scan subfolders (series)
    for item in root.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            folder_name = item.name
            encoded_folder = encode_path_for_markdown(folder_name)
            
            for file in item.iterdir():
                if file.is_file() and file.suffix.lower() == '.md':
                    discovered.append({
                        'name': file.name,
                        'path': str(file),
                        'rel_path': f"{encoded_folder}/{encode_path_for_markdown(file.name)}",
                        'folder': folder_name,
                        'series': folder_name
                    })
    
    return discovered

def parse_series_number(filename: str) -> Optional[int]:
    """Extract part number from filename"""
    part_match = re.search(r'[Pp]art\s*(\d+)', filename)
    if part_match:
        return int(part_match.group(1))
    
    start_match = re.search(r'^(\d+)\s*[-:\.]', filename)
    if start_match:
        return int(start_match.group(1))
    
    return None