"""
Utils Package - Shared utility functions across the application
"""

from app.utils.utils import (
    # URL and title normalization
    normalize_url,
    normalize_title,
    normalize_filename,  # Add this line
    
    # Post ID extraction
    extract_post_id_from_url,
    
    # Story resolution
    find_story_by_identifier,
    
    # Statistics helpers
    calculate_percentages,
    format_number,
    format_currency,
    
    # Series parsing
    parse_series_number,
    
    # Date utilities
    get_current_year_month,
    validate_year_month,
    parse_date,
    format_date,
    get_month_range,
    
    # Dictionary utilities
    merge_dicts,
    safe_get,
    
    # List utilities
    chunk_list,
    remove_duplicates
)

__all__ = [
    # URL and title normalization
    'normalize_url',
    'normalize_title',
    'normalize_filename',  # Add this line


    
    # Post ID extraction
    'extract_post_id_from_url',
    
    # Story resolution
    'find_story_by_identifier',
    
    # Statistics helpers
    'calculate_percentages',
    'format_number',
    'format_currency',
    
    # Series parsing
    'parse_series_number',
    
    # Date utilities
    'get_current_year_month',
    'validate_year_month',
    'parse_date',
    'format_date',
    'get_month_range',
    
    # Dictionary utilities
    'merge_dicts',
    'safe_get',
    
    # List utilities
    'chunk_list',
    'remove_duplicates'
]