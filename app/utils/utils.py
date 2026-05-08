"""
Shared Utility Functions
Used across stories, series, calendar, settings, and dashboard routers
"""

import re
import unicodedata
from typing import List, Optional, Any, Dict, Tuple
from datetime import datetime
from urllib.parse import unquote


def normalize_url(url: str) -> str:
    """
    Normalize URL by removing trailing slashes and standardizing format
    
    Args:
        url: URL string to normalize
        
    Returns:
        Normalized URL without trailing slash
    """
    if not url:
        return ""
    return url.rstrip('/')


def normalize_title(title: str) -> str:
    """
    Normalize title to create a consistent key for matching
    
    Steps:
    1. URL decode first (handles %20, %3A, etc.)
    2. Convert to lowercase
    3. Normalize unicode characters (NFKD + ASCII)
    4. Replace spaces and special characters with hyphens
    5. Collapse multiple hyphens
    6. Strip leading/trailing hyphens
    
    Args:
        title: Title string to normalize
        
    Returns:
        Normalized title string suitable for matching
    """
    if not title:
        return ""
    
    # Step 1: URL decode
    title = unquote(title)
    
    # Step 2: Convert to lowercase
    title = title.lower()
    
    # Step 3: Normalize unicode characters
    title = unicodedata.normalize('NFKD', title).encode('ASCII', 'ignore').decode('ASCII')
    
    # Step 4: Replace spaces and special characters with hyphens
    title = re.sub(r'[^\w\s-]', '', title)
    title = re.sub(r'[\s]+', '-', title)
    
    # Step 5: Remove multiple hyphens
    title = re.sub(r'-+', '-', title)
    
    # Step 6: Strip hyphens from start and end
    title = title.strip('-')
    
    # Limit length to 100 characters
    title = title[:100]
    
    return title


def extract_post_id_from_url(medium_url: str) -> Optional[str]:
    """
    Extract post ID from Medium URL
    
    Medium URL formats:
    - https://medium.com/@username/post-title-78cb972195da
    - https://mvineetsharma.medium.com/post-title-78cb972195da
    - https://medium.com/p/78cb972195da
    - https://blog.devgenius.io/post-title-78cb972195da
    
    Args:
        medium_url: Full Medium URL
        
    Returns:
        Extracted post ID or None if not found
    """
    if not medium_url:
        return None
    
    url = medium_url.rstrip('/')
    parts = url.split('/')
    last_part = parts[-1]
    
    # Check for post ID at the end of URL (after hyphen)
    if '-' in last_part:
        post_id = last_part.split('-')[-1]
        if len(post_id) >= 10 and re.match(r'^[a-f0-9]+$', post_id):
            return post_id
    
    # Check if last part itself is a post ID
    if len(last_part) >= 10 and re.match(r'^[a-f0-9]+$', last_part):
        return last_part
    
    return None

def normalize_filename(filename: str) -> str:
    """
    Normalize filename by removing trailing slashes and standardizing format
    
    Args:
        filename: Filename string to normalize
        
    Returns:
        Normalized filename without trailing slash
    """

    if not filename:
        return "untitled"
    filename = filename.replace(' ', '-')
    filename = re.sub(r'[^a-zA-Z0-9\-]', '', filename)
    filename = filename.lower()
    filename = filename.strip('-')
    return filename if filename else "untitled"

def find_story_by_identifier(stories: List[Any], identifier: str) -> Optional[Any]:
    """
    Find story by medium_url (preferred) or normalized title (fallback)
    
    Search order:
    1. Exact match by medium_url (after URL normalization)
    2. Exact match by name/title (case-insensitive)
    3. Match by normalized title
    4. Partial match by name (last resort)
    
    Args:
        stories: List of story objects (must have medium_url and name attributes)
        identifier: Story identifier (could be URL or title)
        
    Returns:
        Story object if found, None otherwise
    """
    if not identifier or not stories:
        return None
    
    decoded_identifier = unquote(identifier)
    
    # Check if identifier looks like a URL
    is_url = decoded_identifier.startswith('http://') or decoded_identifier.startswith('https://')
    
    if is_url:
        # Try to find by medium_url
        normalized_identifier = normalize_url(decoded_identifier)
        for story in stories:
            if hasattr(story, 'medium_url') and story.medium_url:
                if normalize_url(story.medium_url) == normalized_identifier:
                    return story
    
    # If not found by URL or not a URL, try by name (title)
    for story in stories:
        story_name = getattr(story, 'name', None) or getattr(story, 'title', None)
        if story_name and story_name.lower() == decoded_identifier.lower():
            return story
    
    # Try by normalized title
    normalized_identifier = normalize_title(decoded_identifier)
    for story in stories:
        story_name = getattr(story, 'name', None) or getattr(story, 'title', None)
        if story_name and normalize_title(story_name) == normalized_identifier:
            return story
    
    # Try partial match as last resort
    for story in stories:
        story_name = getattr(story, 'name', None) or getattr(story, 'title', None)
        if story_name and decoded_identifier.lower() in story_name.lower():
            return story
    
    return None


def calculate_percentages(member: int, nonmember: int) -> Tuple[int, float]:
    """
    Calculate total and percentage of member reads/views
    
    Args:
        member: Member count
        nonmember: Non-member count
        
    Returns:
        Tuple of (total, percentage)
    """
    total = member + nonmember
    percent = round((member / total) * 100, 1) if total > 0 else 0
    return total, percent


def parse_series_number(filename: str) -> Optional[int]:
    """
    Extract part number from filename
    
    Supports formats:
    - "Part X" or "part X" (case insensitive)
    - "X." or "X:" or "X-" at beginning
    - "X -" pattern
    - "X: " pattern
    - "X of Y" pattern
    
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
    
    # Check for "X of Y" pattern
    of_match = re.search(r'(\d+)\s+of\s+\d+', filename)
    if of_match:
        return int(of_match.group(1))
    
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


def get_current_year_month() -> Tuple[int, int]:
    """
    Get current year and month as integers
    
    Returns:
        Tuple of (year, month)
    """
    now = datetime.now()
    return now.year, now.month


def format_currency(nanos: int) -> str:
    """
    Format currency from nanos to dollars
    
    Args:
        nanos: Amount in nanos (1/1,000,000,000 of a dollar)
        
    Returns:
        Formatted currency string (e.g., "$1.23")
    """
    if not nanos:
        return "$0.00"
    dollars = nanos / 1000000000
    return f"${dollars:.2f}"


def validate_year_month(year: int, month: int) -> bool:
    """
    Validate year and month values
    
    Args:
        year: Year (e.g., 2026)
        month: Month (1-12)
        
    Returns:
        True if valid, False otherwise
    """
    if not year or not month:
        return False
    if year < 2000 or year > 2100:
        return False
    if month < 1 or month > 12:
        return False
    return True


def format_number(num: int) -> str:
    """
    Format number with K/M suffix
    
    Args:
        num: Number to format
        
    Returns:
        Formatted string (e.g., "1.2K", "1.5M", "123")
    """
    if not num and num != 0:
        return "0"
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse date string in various formats
    
    Args:
        date_str: Date string (YYYY-MM-DD or ISO format)
        
    Returns:
        datetime object or None
    """
    if not date_str:
        return None
    
    try:
        # Try YYYY-MM-DD format
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        try:
            # Try ISO format
            return datetime.fromisoformat(date_str)
        except ValueError:
            return None


def format_date(date_obj: Optional[datetime]) -> Optional[str]:
    """
    Format datetime object to YYYY-MM-DD string
    
    Args:
        date_obj: datetime object
        
    Returns:
        Formatted date string or None
    """
    if not date_obj:
        return None
    return date_obj.strftime("%Y-%m-%d")


def get_month_range(year: int, month: int) -> Tuple[datetime, datetime]:
    """
    Get start and end datetime for a month
    
    Args:
        year: Year
        month: Month (1-12)
        
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    start_date = datetime(year, month, 1, 0, 0, 0)
    
    if month == 12:
        end_date = datetime(year + 1, 1, 1, 0, 0, 0)
    else:
        end_date = datetime(year, month + 1, 1, 0, 0, 0)
    
    return start_date, end_date


def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """
    Recursively merge two dictionaries
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary (overrides dict1)
        
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def safe_get(data: Dict, path: str, default: Any = None) -> Any:
    """
    Safely get nested dictionary value using dot notation path
    
    Args:
        data: Dictionary to navigate
        path: Dot-separated path (e.g., "user.profile.name")
        default: Default value if path not found
        
    Returns:
        Value at path or default
    """
    if not data or not path:
        return default
    
    keys = path.split('.')
    current = data
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """
    Split a list into chunks of specified size
    
    Args:
        lst: List to split
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def remove_duplicates(lst: List, key: Optional[str] = None) -> List:
    """
    Remove duplicates from a list, optionally using a key function
    
    Args:
        lst: List to deduplicate
        key: Optional key to use for comparison
        
    Returns:
        Deduplicated list
    """
    seen = set()
    result = []
    
    for item in lst:
        if key and isinstance(item, dict):
            compare = item.get(key)
        elif key and hasattr(item, key):
            compare = getattr(item, key)
        else:
            compare = item
        
        if compare not in seen:
            seen.add(compare)
            result.append(item)
    
    return result


