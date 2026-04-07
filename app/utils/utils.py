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


def find_story_by_identifier(stories: List[Any], identifier: str) -> Optional[Any]:
    """
    Find story by medium_url (preferred) or normalized title (fallback)
    
    Search order:
    1. Exact match by medium_url (after URL normalization)
    2. Exact match by name/title (case-insensitive)
    3. Match by normalized title
    
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
            if story.medium_url and normalize_url(story.medium_url) == normalized_identifier:
                return story
    
    # If not found by URL or not a URL, try by name (title)
    for story in stories:
        if story.name and story.name.lower() == decoded_identifier.lower():
            return story
    
    # Try by normalized title
    normalized_identifier = normalize_title(decoded_identifier)
    for story in stories:
        if normalize_title(story.name) == normalized_identifier:
            return story
    
    # Try partial match as last resort
    for story in stories:
        if story.name and decoded_identifier.lower() in story.name.lower():
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
    
    Args:
        filename: Story filename or title
        
    Returns:
        Part number as integer or None if not found
    """
    if not filename:
        return None
    
    # Check for "Part X" pattern
    part_match = re.search(r'[Pp]art\s*(\d+)', filename)
    if part_match:
        return int(part_match.group(1))
    
    # Check for number at beginning with separator
    start_match = re.search(r'^(\d+)\s*[-:\.]', filename)
    if start_match:
        return int(start_match.group(1))
    
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