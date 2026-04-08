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

def get_app_status_path() -> Path:
    """Get path to appstatus.json"""
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "appstatus.json"

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
    exclude_patterns = [
        "Image Prompt",
        "Stories.md",
        "README.md",
        "publishing-calendar.md",
        ".DS_Store",
        "Thumbs.db"
    ]
    for pattern in exclude_patterns:
        if pattern in filename:
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
                # Ensure all default keys exist
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
    """
    Scan only subfolders for markdown files.
    
    Returns a list of dictionaries with keys:
    - name: Story name without .md extension
    - full_name: Full filename with .md extension
    - path: Absolute path to file
    - raw_path: Raw relative path for display
    - rel_path: Encoded path for markdown links
    - folder: Folder name (series name)
    - series: Series name (same as folder)
    """
    discovered = []
    root = get_stories_root()
    
    if not root.exists():
        print(f"Stories root does not exist: {root}")
        return discovered
    
    for item in root.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            folder_name = item.name
            
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
                        'raw_path': raw_path,
                        'rel_path': encoded_path,
                        'folder': folder_name,
                        'series': folder_name  # Series name equals folder name
                    })
    
    print(f"Found {len(discovered)} markdown files in series folders")
    for d in discovered:
        print(f"  - {d['folder']}/{d['name']}")
    
    return discovered

def parse_series_number(filename: str) -> Optional[int]:
    """
    Extract part number from filename.
    
    Supports formats:
    - "Part X" or "part X" (case insensitive)
    - "X." or "X:" or "X-" at beginning
    - "X -" pattern
    - "X: " pattern
    
    Args:
        filename: Story filename or title
        
    Returns:
        Part number as integer or None if not found
    """
    if not filename:
        return None
    
    # Check for "Part X" pattern (case insensitive)
    part_match = re.search(r'[Pp]art\s*(\d+)', filename)
    if part_match:
        return int(part_match.group(1))
    
    # Check for number at beginning with separator
    start_match = re.search(r'^(\d+)\s*[-:\.]', filename)
    if start_match:
        return int(start_match.group(1))
    
    # Check for "X - Title" pattern
    dash_match = re.search(r'^(\d+)\s*-', filename)
    if dash_match:
        return int(dash_match.group(1))
    
    # Check for "X: Title" pattern
    colon_match = re.search(r'^(\d+)\s*:', filename)
    if colon_match:
        return int(colon_match.group(1))
    
    return None

async def load_app_status() -> Dict[str, Any]:
    """Load appstatus.json"""
    status_path = get_app_status_path()
    
    default_status = {
        "leaderboard_month": None,
        "current_mode": "dashboard",
        "current_month": {
            "year": datetime.now().year,
            "month": datetime.now().month
        },
        "medium_username": None,
        "last_updated": datetime.now().isoformat()
    }
    
    if status_path.exists():
        try:
            with open(status_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure all default keys exist
                for key, value in default_status.items():
                    if key not in data:
                        data[key] = value
                return data
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading appstatus.json: {e}")
            return default_status
    
    return default_status

async def save_app_status(data: Dict[str, Any]) -> None:
    """Save appstatus.json"""
    data["last_updated"] = datetime.now().isoformat()
    status_path = get_app_status_path()
    status_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(status_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved app status to {status_path}")

async def get_monthly_stats_path(year: int, month: int) -> Path:
    """Get path to stories-YYYY-MM.json"""
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    month_str = f"{year}-{month:02d}"
    return data_dir / f"stories-{month_str}.json"

async def load_monthly_stats(year: int, month: int) -> Dict[str, Any]:
    """Load monthly stats for a specific month"""
    file_path = await get_monthly_stats_path(year, month)
    
    default_data = {
        "month": f"{year}-{month:02d}",
        "last_updated": datetime.now().isoformat(),
        "stories": {}
    }
    
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "stories" not in data:
                    data["stories"] = {}
                if "month" not in data:
                    data["month"] = f"{year}-{month:02d}"
                return data
        except Exception as e:
            print(f"Error loading monthly stats for {year}-{month:02d}: {e}")
            return default_data
    
    return default_data

async def save_monthly_stats(year: int, month: int, data: Dict[str, Any]) -> bool:
    """Save monthly stats for a specific month"""
    try:
        file_path = await get_monthly_stats_path(year, month)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        data["last_updated"] = datetime.now().isoformat()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved monthly stats for {year}-{month:02d}")
        return True
    except Exception as e:
        print(f"Error saving monthly stats for {year}-{month:02d}: {e}")
        return False

async def get_available_months() -> List[Dict[str, Any]]:
    """Scan data directory for stories-YYYY-MM.json files"""
    data_dir = Path(settings.data_dir)
    if not data_dir.exists():
        return []
    
    months = []
    for file_path in data_dir.glob("stories-*.json"):
        filename = file_path.stem
        if filename.startswith("stories-"):
            month_str = filename.replace("stories-", "")
            if len(month_str) == 7 and month_str[4] == '-':
                try:
                    year, month = month_str.split('-')
                    months.append({
                        "year": int(year),
                        "month": int(month),
                        "display": datetime(int(year), int(month), 1).strftime("%b %Y"),
                        "file_path": str(file_path),
                        "exists": True
                    })
                except:
                    pass
    
    months.sort(key=lambda x: (x["year"], x["month"]), reverse=True)
    return months

def get_leaderboard_files() -> List[Dict[str, Any]]:
    """Get all leaderboard-*.json files"""
    data_dir = Path(settings.data_dir)
    if not data_dir.exists():
        return []
    
    leaderboard_files = []
    for file_path in data_dir.glob("leaderboard-*.json"):
        match = re.search(r'leaderboard-(\d{4})-(\d{2})', file_path.name)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            leaderboard_files.append({
                "year": year,
                "month": month,
                "display": datetime(year, month, 1).strftime("%B %Y"),
                "file_path": str(file_path),
                "name": file_path.name
            })
    
    leaderboard_files.sort(key=lambda x: (x["year"], x["month"]), reverse=True)
    return leaderboard_files