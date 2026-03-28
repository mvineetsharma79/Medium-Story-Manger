import json
import aiofiles
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import urllib.parse

from config import settings

def get_stories_root() -> Path:
    """Get the configured stories root folder"""
    root = Path(settings.stories_root)
    root.mkdir(parents=True, exist_ok=True)
    return root

def get_stories_json_path() -> Path:
    """Get path to stories.json"""
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "stories.json"

def get_calendar_md_path() -> Path:
    """Get path to publishing calendar markdown"""
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "publishing-calendar.md"

def get_calendar_json_path() -> Path:
    """Get path to publishing calendar JSON"""
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "publishing-calendar.json"

def encode_path_for_markdown(path: str) -> str:
    """Encode special characters for markdown links (for display only, not storage)"""
    parts = path.split('/')
    encoded = []
    for part in parts:
        encoded_part = part.replace(' ', '%20')
        encoded_part = encoded_part.replace('(', '%28')
        encoded_part = encoded_part.replace(')', '%29')
        encoded_part = encoded_part.replace(':', '%3A')
        encoded.append(encoded_part)
    return '/'.join(encoded)

def decode_path_for_display(path: str) -> str:
    """Decode URL-encoded path for display"""
    return urllib.parse.unquote(path)

def normalize_story_key(folder: str, filename: str) -> str:
    """Normalize story key - remove .md extension"""
    name_without_ext = filename.replace('.md', '')
    return f"{folder}/{name_without_ext}"

def should_exclude_file(filename: str) -> bool:
    """Check if a file should be excluded"""
    if "Image Prompt" in filename:
        return True
    if filename in ["Stories.md", "README.md", "publishing-calendar.md"]:
        return True
    return False

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
            "start_date": settings.start_date or datetime.now().strftime("%Y-%m-%d")
        }
    }
    
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                content = f.read()
                data = json.loads(content)
                for key, value in default_data.items():
                    if key not in data:
                        data[key] = value
                return data
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading stories.json: {e}")
            return default_data
    
    return default_data

async def save_stories_data(data: Dict[str, Any]) -> None:
    """Save stories.json"""
    data["last_updated"] = datetime.now().isoformat()
    json_path = get_stories_json_path()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved stories data to {json_path}")

async def scan_markdown_files() -> List[Dict[str, str]]:
    """Scan only subfolders for markdown files"""
    discovered = []
    root = get_stories_root()
    
    if not root.exists():
        print(f"Stories root does not exist: {root}")
        return discovered
    
    for item in root.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            folder_name = item.name
            # Store the raw path for display, not encoded
            raw_rel_path = f"{folder_name}/{item.name}"
            
            for file in item.iterdir():
                if file.is_file() and file.suffix.lower() == '.md':
                    filename = file.name
                    
                    if should_exclude_file(filename):
                        print(f"Excluding: {folder_name}/{filename}")
                        continue
                    
                    # Remove .md extension for the name
                    name_without_ext = filename.replace('.md', '')
                    
                    # Store raw path (not encoded) for display
                    raw_path = f"{folder_name}/{filename}"
                    
                    # Store encoded path for markdown links (if needed)
                    encoded_path = encode_path_for_markdown(raw_path)
                    
                    discovered.append({
                        'name': name_without_ext,
                        'full_name': filename,
                        'path': str(file),
                        'raw_path': raw_path,  # Raw path for display
                        'rel_path': encoded_path,  # Encoded path for markdown links
                        'folder': folder_name,
                        'series': folder_name
                    })
    
    print(f"Found {len(discovered)} markdown files in series folders")
    for d in discovered:
        print(f"  - {d['folder']}/{d['name']}")
    
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