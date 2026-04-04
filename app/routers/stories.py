from fastapi import APIRouter, HTTPException, Query, Path, Request
from typing import List, Optional, Dict, Any
import logging
from urllib.parse import unquote
from datetime import datetime
import time
import re
import json
from pathlib import Path as FilePath

from app.services.story_service import StoryService
from app.services.medium_stats_fetcher import MediumStatsFetcher
from app.models import StoryCreate, StoryUpdate, StoryResponse
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def normalize_url(url: str) -> str:
    """Normalize URL for comparison"""
    if not url:
        return url
    url = url.replace('https://', '').replace('http://', '')
    url = url.rstrip('/')
    return url.lower()


def safe_divide(numerator: float, denominator: float, default: float = 0) -> float:
    """Safely divide two numbers"""
    if denominator == 0:
        return default
    return round(numerator / denominator, 2)


def get_today_date():
    return datetime.now().strftime("%Y-%m-%d")


def write_fetch_log(data_dir: FilePath, operation: str, details: Dict[str, Any]):
    """Write fetch operation log to YYYY-MM.log file"""
    try:
        now = datetime.now()
        log_filename = f"{now.year}-{now.month:02d}.log"
        log_path = data_dir / "logs" / log_filename
        
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        log_entry = {
            "timestamp": now.isoformat(),
            "operation": operation,
            "details": details
        }
        
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        
        logger.info(f"Fetch log written to {log_path}")
        
        summary_path = data_dir / "logs" / f"{now.year}-{now.month:02d}_summary.txt"
        with open(summary_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Operation: {operation}\n")
            f.write(f"Timestamp: {now.isoformat()}\n")
            f.write(f"Files Processed: {details.get('files_processed', 0)}\n")
            f.write(f"Stories Updated: {details.get('updated', 0)}\n")
            f.write(f"Stories Added: {details.get('added', 0)}\n")
            f.write(f"Stories Reset: {details.get('reset', 0)}\n")
            f.write(f"Total Earnings: ${details.get('total_dollars', 0):.2f}\n")
            if details.get('files'):
                f.write(f"Source Files: {', '.join(details.get('files', []))}\n")
            f.write(f"{'='*80}\n")
        
    except Exception as e:
        logger.error(f"Failed to write fetch log: {e}")


def find_leaderboard_json_files(data_dir: FilePath, year: int, month: int) -> List[FilePath]:
    """Find all leaderboard JSON files for a given year and month"""
    found_files = []
    
    patterns = [
        f"leaderboard-{year}-{month:02d}.json",
        f"leaderboard-{year}-{month:02d}.-1.json",
        f"leaderboard-{year}-{month:02d}.-2.json",
        f"leaderboard-{year}-{month:02d}.-3.json",
        f"leaderboard-{year}-{month:02d}.-4.json",
        f"leaderboard-{year}-{month:02d}.-5.json",
        f"leaderboard-{year}-{month:02d}.1.json",
        f"leaderboard-{year}-{month:02d}.2.json",
        f"leaderboard-{year}-{month:02d}.3.json",
        f"leaderboard-{year}-{month:02d}.4.json",
        f"leaderboard-{year}-{month:02d}.5.json",
        f"leaderboard-{year}-{month:02d}*-part*.json",
        f"leaderboard-{year}-{month:02d}*.json",
    ]
    
    for pattern in patterns:
        for file_path in data_dir.glob(pattern):
            if file_path not in found_files and file_path.suffix == '.json':
                found_files.append(file_path)
                logger.info(f"Found leaderboard file: {file_path.name}")
    
    found_files.sort()
    return found_files


def parse_complete_leaderboard_json(file_path: FilePath) -> List[Dict[str, Any]]:
    """Parse a leaderboard JSON file and extract COMPLETE data"""
    stories_list = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list) and len(data) > 0:
            data_obj = data[0].get('data', {})
            user_result = data_obj.get('userResult', {})
        elif isinstance(data, dict):
            data_obj = data.get('data', {})
            user_result = data_obj.get('userResult', {})
        else:
            logger.warning(f"Unexpected JSON structure in {file_path}")
            return stories_list
        
        if user_result.get('__typename') == 'User':
            posts_connection = user_result.get('postsConnection', {})
            edges = posts_connection.get('edges', [])
            
            for edge in edges:
                node = edge.get('node', {})
                earnings = node.get('earnings', {})
                monthly_earnings = earnings.get('monthlyEarnings', {})
                
                nanos = monthly_earnings.get('nanos', 0)
                
                story_data = {
                    'title': node.get('title'),
                    'medium_url': node.get('mediumUrl'),
                    'first_published_at': node.get('firstPublishedAt'),
                    'reading_time': node.get('readingTime'),
                    'word_count': node.get('wordCount', 0),
                    'collection': node.get('collection'),
                    'nanos': nanos,
                    'currency': monthly_earnings.get('currencyCode', 'USD'),
                    'lifetime_nanos': earnings.get('lifetimeEarnings', {}).get('nanos', 0),
                    'source_file': file_path.name,
                    'tags': [],
                    'topics': [],
                    'subtitle': node.get('subtitle', ''),
                    'author': '',
                    'claps': 0,
                    'responses': 0,
                    'bookmarks': 0,
                    'view_count': 0
                }
                
                creator = node.get('creator', {})
                if creator:
                    story_data['author'] = creator.get('name', '')
                
                tags = node.get('tags', [])
                if tags:
                    story_data['tags'] = [tag.get('name') for tag in tags if tag.get('name')]
                
                topics = node.get('topics', [])
                if topics:
                    story_data['topics'] = [topic.get('name') for topic in topics if topic.get('name')]
                
                distribution = node.get('distribution', {})
                if distribution:
                    story_data['claps'] = distribution.get('totalClapCount', 0)
                    story_data['responses'] = distribution.get('totalResponseCount', 0)
                    story_data['bookmarks'] = distribution.get('totalBookmarkCount', 0)
                    story_data['view_count'] = distribution.get('totalViewCount', 0)
                
                stories_list.append(story_data)
                logger.info(f"  Found from {file_path.name}: {node.get('title')} - ${nanos/1000000000:.2f}")
    
    except Exception as e:
        logger.error(f"Error parsing {file_path}: {e}")
    
    return stories_list


# ============================================
# DEBUG ENDPOINTS
# ============================================

@router.get("/debug/all")
async def debug_all():
    """Debug endpoint to list all stories"""
    try:
        stories = await StoryService.get_all_stories()
        return {
            "total": len(stories),
            "stories": [
                {
                    "key": s.key,
                    "name": s.name,
                    "medium_url": s.medium_url,
                    "status": s.status,
                    "medium_first_published": s.medium_first_published,
                    "leaderboard": s.leaderboard
                }
                for s in stories
            ]
        }
    except Exception as e:
        logger.error(f"Debug all error: {e}")
        return {"error": str(e)}


@router.get("/debug/urls")
async def debug_urls():
    """Debug endpoint to list all stories with Medium URLs"""
    try:
        stories = await StoryService.get_all_stories()
        urls_with_keys = [
            {
                "key": s.key,
                "name": s.name,
                "medium_url": s.medium_url,
                "medium_first_published": s.medium_first_published
            }
            for s in stories if s.medium_url
        ]
        return {
            "total": len(urls_with_keys),
            "urls": urls_with_keys
        }
    except Exception as e:
        logger.error(f"Debug URLs error: {e}")
        return {"error": str(e)}


@router.get("/debug/keys")
async def debug_keys():
    """Debug endpoint to list all story keys"""
    try:
        stories = await StoryService.get_all_stories()
        return {
            "total": len(stories),
            "keys": [s.key for s in stories]
        }
    except Exception as e:
        logger.error(f"Debug keys error: {e}")
        return {"error": str(e)}


@router.get("/debug/find/{search}")
async def find_story(search: str):
    """Find stories containing search term"""
    try:
        stories = await StoryService.get_all_stories()
        matches = [
            {"key": s.key, "name": s.name, "medium_url": s.medium_url}
            for s in stories if search.lower() in s.key.lower() or search.lower() in s.name.lower() or (s.medium_url and search.lower() in s.medium_url.lower())
        ]
        return {"search": search, "matches": matches}
    except Exception as e:
        logger.error(f"Find story error: {e}")
        return {"error": str(e)}

@router.get("/debug/test-lifetime")
async def debug_test_lifetime():
    """Test lifetime API with a known post ID"""
    try:
        from app.services.medium_stats_fetcher import MediumStatsFetcher
        import requests
        
        fetcher = MediumStatsFetcher()
        if not fetcher.is_authenticated():
            return {"error": "Not authenticated"}
        
        # Use a known post ID from your JSON file
        post_id = "78cb972195da"  # This is from your leaderboard JSON
        
        session = requests.Session()
        for name, value in fetcher.cookies.items():
            session.cookies.set(name, value, domain=".medium.com", path="/")
        
        url = "https://medium.com/_/graphql"
        payload = fetcher._get_lifetime_payload(post_id)
        headers = fetcher._get_headers_for_lifetime(post_id)
        
        response = session.post(url, headers=headers, json=payload, timeout=30)
        
        return {
            "post_id": post_id,
            "status_code": response.status_code,
            "raw_response": response.json() if response.status_code == 200 else None
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/leaderboard-files")
async def list_leaderboard_files():
    """List all available leaderboard JSON files grouped by month"""
    try:
        data_dir = FilePath(settings.data_dir)
        
        if not data_dir.exists():
            return {"error": "Data directory not found", "files": []}
        
        leaderboard_files = {}
        
        for file_path in data_dir.glob("leaderboard-*.json"):
            filename = file_path.name
            import re
            match = re.search(r'leaderboard-(\d{4}-\d{2})', filename)
            
            if match:
                year_month = match.group(1)
                
                try:
                    year, month = year_month.split('-')
                    month_name = datetime(int(year), int(month), 1).strftime("%b-%Y")
                    
                    if year_month not in leaderboard_files:
                        leaderboard_files[year_month] = {
                            "year_month": year_month,
                            "display_name": month_name,
                            "year": int(year),
                            "month": int(month),
                            "files": []
                        }
                    
                    leaderboard_files[year_month]["files"].append({
                        "filename": filename,
                        "size": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                        "path": str(file_path)
                    })
                except Exception as e:
                    logger.warning(f"Error parsing filename {filename}: {e}")
        
        for year_month in leaderboard_files:
            leaderboard_files[year_month]["files"].sort(key=lambda x: x["filename"])
        
        sorted_files = sorted(leaderboard_files.values(), 
                            key=lambda x: x["year_month"], 
                            reverse=True)
        
        return {
            "leaderboard_files": sorted_files,
            "total_months": len(sorted_files),
            "data_dir": str(data_dir)
        }
        
    except Exception as e:
        logger.error(f"Error listing leaderboard files: {e}")
        return {"error": str(e), "files": []}


@router.get("/logs/{year_month}")
async def get_fetch_logs(year_month: str):
    """Get fetch operation logs for a specific year-month"""
    try:
        data_dir = FilePath(settings.data_dir)
        log_path = data_dir / "logs" / f"{year_month}.log"
        
        if not log_path.exists():
            return {"error": f"No log file found for {year_month}", "path": str(log_path)}
        
        logs = []
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        logs.append(json.loads(line))
                    except:
                        logs.append({"raw": line.strip()})
        
        return {
            "year_month": year_month,
            "log_file": str(log_path),
            "entries": logs,
            "total_entries": len(logs)
        }
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return {"error": str(e)}


@router.get("/logs")
async def list_log_files():
    """List all available fetch log files"""
    try:
        data_dir = FilePath(settings.data_dir)
        logs_dir = data_dir / "logs"
        
        if not logs_dir.exists():
            return {"logs_dir": str(logs_dir), "files": []}
        
        log_files = []
        for file_path in logs_dir.glob("*.log"):
            log_files.append({
                "filename": file_path.name,
                "size": file_path.stat().st_size,
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })
        
        summary_files = []
        for file_path in logs_dir.glob("*_summary.txt"):
            summary_files.append({
                "filename": file_path.name,
                "size": file_path.stat().st_size,
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })
        
        return {
            "logs_dir": str(logs_dir),
            "log_files": sorted(log_files, key=lambda x: x['filename'], reverse=True),
            "summary_files": sorted(summary_files, key=lambda x: x['filename'], reverse=True)
        }
    except Exception as e:
        logger.error(f"Error listing logs: {e}")
        return {"error": str(e)}


# ============================================
# MEDIUM STATS ENDPOINTS
# ============================================

@router.get("/stats-by-url")
async def get_stats_dashboard_by_url(medium_url: str):
    """Get stats dashboard for a story using its Medium URL"""
    try:
        if not medium_url:
            return {"error": "Medium URL is required"}
        
        decoded_url = unquote(medium_url)
        all_stories = await StoryService.get_all_stories()
        
        story = None
        normalized_query = normalize_url(decoded_url)
        
        for s in all_stories:
            if s.medium_url:
                if normalize_url(s.medium_url) == normalized_query:
                    story = s
                    break
        
        if not story:
            available = [s.medium_url for s in all_stories if s.medium_url]
            return {
                "error": "Story not found",
                "your_url": decoded_url,
                "available_urls": available[:5] if available else []
            }
        
        return {
            "story_key": story.key,
            "story_name": story.name,
            "medium_url": story.medium_url,
            "last_stats_update": story.last_stats_update,
            "medium_first_published": story.medium_first_published,
            "medium_publication": story.medium_publication,
            "current_month": {
                "reads": story.reads or 0,
                "claps": story.claps or 0,
                "views": story.view_count or 0,
                "responses": story.responses or 0,
                "member_reads": story.medium_member_reads or 0,
                "member_views": story.medium_member_views or 0,
                "nonmember_reads": story.medium_nonmember_reads or 0,
                "nonmember_views": story.medium_nonmember_views or 0,
                "read_ratio": story.read_ratio or 0,
                "member_read_percentage": story.medium_member_read_percentage or 0,
                "new_followers": story.medium_new_followers or 0
            },
            "lifetime": {
                "reads": story.lifetime_reads or 0,
                "views": story.lifetime_views or 0,
                "presentation_count": story.presentation_count or 0
            },
            "content": {
                "word_count": story.word_count or 0,
                "reading_time": story.medium_reading_time or story.read_time or 0
            },
            "metadata": {
                "title": story.medium_title or story.name,
                "first_published": story.medium_first_published or story.created_date,
                "last_updated": story.medium_last_updated or story.last_updated,
                "publication": story.medium_publication or ""
            }
        }
        
    except Exception as e:
        logger.error(f"Get stats dashboard error: {e}")
        return {"error": str(e)}


@router.post("/fetch-lifetime-stats/{story_key:path}")
async def fetch_complete_story_stats(story_key: str = Path(..., description="The story key")):
    """Fetch current month AND lifetime stats for a single story"""
    try:
        decoded_key = unquote(story_key)
        if decoded_key.lower().endswith('.md'):
            decoded_key = decoded_key[:-3]
        
        logger.info(f"=" * 60)
        logger.info(f"FETCHING COMPLETE STATS FOR: {decoded_key}")
        logger.info(f"=" * 60)
        
        story = await StoryService.get_story(decoded_key)
        if not story:
            raise HTTPException(status_code=404, detail=f"Story not found: {decoded_key}")
        
        if not story.medium_url:
            raise HTTPException(status_code=400, detail="Story has no Medium URL")
        
        logger.info(f"📝 Medium URL: {story.medium_url}")
        
        fetcher = MediumStatsFetcher()
        
        if not fetcher.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        complete_stats = await fetcher.fetch_complete_stats(story.medium_url)
        
        if complete_stats:
            totals = complete_stats.get('totals', {})
            lifetime = complete_stats.get('lifetime_totals', {})
            
            await StoryService.update_story(decoded_key, StoryUpdate(
                reads=totals.get('total_reads', 0),
                claps=totals.get('claps', 0),
                responses=totals.get('replies', 0),
                view_count=totals.get('total_views', 0),
                medium_member_reads=totals.get('member_reads', 0),
                medium_member_views=totals.get('member_views', 0),
                medium_nonmember_reads=totals.get('nonmember_reads', 0),
                medium_nonmember_views=totals.get('nonmember_views', 0),
                medium_read_ratio=totals.get('read_ratio', 0),
                medium_member_read_percentage=totals.get('member_read_percentage', 0),
                medium_new_followers=totals.get('new_followers', 0),
                lifetime_reads=lifetime.get('total_reads', 0),
                lifetime_claps=lifetime.get('claps', 0),
                lifetime_views=lifetime.get('total_views', 0),
                medium_first_published=complete_stats.get('first_published'),
                medium_last_updated=complete_stats.get('last_updated'),
                medium_title=complete_stats.get('title'),
                medium_reading_time=complete_stats.get('reading_time', 0),
                word_count=complete_stats.get('word_count', 0),
                medium_tags=complete_stats.get('post_tags', []),
                medium_topics=complete_stats.get('post_topics', []),
                last_stats_update=datetime.now().isoformat(),
                medium_stats_updated=datetime.now().isoformat(),
                lifetime_stats_updated=datetime.now().isoformat(),
                medium_stats_data=complete_stats,
                lifetime_stats_data=complete_stats
            ))
            
            return {
                "message": "Stats fetched successfully",
                "stats": {
                    "story_key": decoded_key,
                    "story_name": story.name,
                    "medium_url": story.medium_url,
                    "medium_first_published": complete_stats.get('first_published'),
                    "current_month": {
                        "reads": totals.get('total_reads', 0),
                        "claps": totals.get('claps', 0),
                        "views": totals.get('total_views', 0),
                        "responses": totals.get('replies', 0),
                        "member_reads": totals.get('member_reads', 0),
                        "member_views": totals.get('member_views', 0),
                        "read_ratio": totals.get('read_ratio', 0)
                    },
                    "lifetime": {
                        "reads": lifetime.get('total_reads', 0),
                        "claps": lifetime.get('claps', 0),
                        "views": lifetime.get('total_views', 0),
                        "tags": complete_stats.get('post_tags', []),
                        "topics": complete_stats.get('post_topics', [])
                    },
                    "content": {
                        "word_count": complete_stats.get('word_count', 0),
                        "reading_time": complete_stats.get('reading_time', 0),
                        "tags": complete_stats.get('post_tags', []),
                        "topics": complete_stats.get('post_topics', [])
                    },
                    "metadata": {
                        "title": complete_stats.get('title'),
                        "first_published": complete_stats.get('first_published'),
                        "last_updated": complete_stats.get('last_updated')
                    }
                }
            }
        else:
            return {"message": "Could not fetch stats", "error": "No data returned"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fetch stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# LEADERBOARD FETCH ENDPOINTS
# ============================================

@router.post("/fetch-leaderboard-for-month")
async def fetch_leaderboard_for_month(request: Request):
    """Fetch leaderboard data for a specific month/year from JSON files"""
    start_time = datetime.now()
    
    try:
        body = await request.json()
        year = body.get('year')
        month = body.get('month')
        
        if not year or not month:
            return {"error": "Year and month are required"}
        
        logger.info("=" * 60)
        logger.info(f"FETCHING LEADERBOARD FOR {year}-{month:02d}")
        logger.info("=" * 60)
        
        data_dir = FilePath(settings.data_dir)
        json_files = find_leaderboard_json_files(data_dir, year, month)
        
        if not json_files:
            error_msg = f"No leaderboard files found for {year}-{month:02d}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "year": year,
                "month": month,
                "data_dir": str(data_dir)
            }
        
        logger.info(f"Found {len(json_files)} leaderboard file(s): {[f.name for f in json_files]}")
        
        all_earnings = []
        for json_file in json_files:
            earnings = parse_complete_leaderboard_json(json_file)
            all_earnings.extend(earnings)
            logger.info(f"  Found {len(earnings)} stories with data in {json_file.name}")
        
        if not all_earnings:
            return {
                "message": "No stories found in any JSON file", 
                "updated": 0, 
                "added": 0, 
                "files_processed": len(json_files)
            }
        
        unique_earnings = {}
        for earning in all_earnings:
            url = earning.get('medium_url', '').rstrip('/')
            if not url:
                continue
            if url not in unique_earnings:
                unique_earnings[url] = earning
        
        earnings_list = list(unique_earnings.values())
        logger.info(f"Total unique stories after deduplication: {len(earnings_list)}")
        
        # Get all existing stories
        all_stories = await StoryService.get_all_stories()
        logger.info(f"Found {len(all_stories)} existing stories in database")
        
        def normalize_title(title: str) -> str:
            """Simple normalization: lowercase, replace all dashes with hyphen, collapse spaces"""
            if not title:
                return ""
            
            # Convert to lowercase
            normalized = title.lower().strip()
            
            # Remove .md extension if present
            if normalized.endswith('.md'):
                normalized = normalized[:-3]
            
            # Replace all types of dashes/em-dash/en-dash with standard hyphen
            import re
            normalized = re.sub(r'[—–‐‑‒−]', '-', normalized)
            
            # Replace all types of spaces with single space
            normalized = re.sub(r'\s+', ' ', normalized)
            
            # Trim
            return normalized.strip()
        
        # Create a map of existing stories by normalized title
        story_map = {}
        for story in all_stories:
            if story.name:
                normalized = normalize_title(story.name)
                story_map[normalized] = story
                logger.info(f"  DB: \"{story.name}\" -> \"{normalized}\"")
        
        # Reset leaderboard flags
        reset_count = 0
        for story in all_stories:
            if story.leaderboard:
                await StoryService.update_story(story.key, StoryUpdate(
                    leaderboard=False,
                    leaderboard_nanos=0,
                    leaderboard_lifetime_nanos=0
                ))
                reset_count += 1
        logger.info(f"Reset leaderboard flags for {reset_count} stories")
        
        updated_count = 0
        added_count = 0
        total_nanos = 0
        
        for earning in earnings_list:
            nanos = earning.get('nanos', 0)
            lifetime_nanos = earning.get('lifetime_nanos', 0)
            total_nanos += nanos
            
            medium_url = earning.get('medium_url')
            title = earning.get('title')
            first_published_at = earning.get('first_published_at')
            reading_time = earning.get('reading_time', 0)
            word_count = earning.get('word_count', 0)
            collection = earning.get('collection', {})
            publication_slug = collection.get('slug') if collection else None
            publication_name = collection.get('name') if collection else None
            source_file = earning.get('source_file', 'unknown')
            
            tags = earning.get('tags', [])
            topics = earning.get('topics', [])
            subtitle = earning.get('subtitle', '')
            author = earning.get('author', '')
            claps = earning.get('claps', 0)
            responses = earning.get('responses', 0)
            bookmarks = earning.get('bookmarks', 0)
            view_count = earning.get('view_count', 0)
            
            if not medium_url or not title:
                continue
            
            # Normalize JSON title
            normalized_json_title = normalize_title(title)
            logger.info(f"  JSON: \"{title}\" -> \"{normalized_json_title}\"")
            
            # Match by normalized title
            existing_story = story_map.get(normalized_json_title)
            
            reading_time_int = int(round(reading_time)) if reading_time else 0
            
            publish_date = None
            if first_published_at:
                try:
                    publish_date = datetime.fromtimestamp(first_published_at/1000).strftime("%Y-%m-%d")
                except:
                    publish_date = datetime.now().strftime("%Y-%m-%d")
            else:
                publish_date = datetime.now().strftime("%Y-%m-%d")
            
            if existing_story:
                # Update existing story - do NOT change series
                update_data = StoryUpdate(
                    leaderboard=True,
                    leaderboard_nanos=nanos,
                    leaderboard_lifetime_nanos=lifetime_nanos,
                    status="Published",
                    published_date=publish_date,
                    medium_url=medium_url,
                    medium_title=title,
                    medium_subtitle=subtitle,
                    medium_author=author,
                    medium_publication=publication_slug or publication_name,
                    medium_reading_time=reading_time_int,
                    word_count=word_count,
                    medium_tags=tags[:20] if tags else [],
                    medium_topics=topics[:20] if topics else [],
                    claps=claps,
                    responses=responses,
                    bookmarks=bookmarks,
                    view_count=view_count,
                    medium_first_published=datetime.fromtimestamp(first_published_at/1000).isoformat() if first_published_at else None
                )
                
                await StoryService.update_story(existing_story.key, update_data)
                updated_count += 1
                logger.info(f"  ✅ UPDATED: Series \"{existing_story.series}\" (KEPT)")
            else:
                # Create NEW story - goes to "Leaderboard" series
                current_date = datetime.now().strftime("%Y-%m-%d")
                safe_title = title[:200]
                
                new_story = await StoryService.create_story(StoryCreate(
                    name=safe_title,
                    folder="Leaderboard",
                    series="Leaderboard",
                    tags=tags[:10] if tags else [],
                    read_time=reading_time_int if reading_time_int > 0 else None,
                    created_date=current_date,
                    notes=f"Auto-created from leaderboard JSON data for {year}-{month:02d} (source: {source_file})",
                    medium_url=medium_url,
                    medium_first_published=datetime.fromtimestamp(first_published_at/1000).isoformat() if first_published_at else None,
                    medium_publication=publication_slug,
                    medium_reading_time=reading_time_int
                ))
                
                await StoryService.update_story(new_story.key, StoryUpdate(
                    leaderboard=True,
                    leaderboard_nanos=nanos,
                    leaderboard_lifetime_nanos=lifetime_nanos,
                    status="Published",
                    published_date=publish_date,
                    medium_title=title,
                    medium_subtitle=subtitle,
                    medium_author=author,
                    medium_publication=publication_slug or publication_name,
                    medium_reading_time=reading_time_int,
                    word_count=word_count,
                    medium_tags=tags[:20] if tags else [],
                    medium_topics=topics[:20] if topics else [],
                    claps=claps,
                    responses=responses,
                    bookmarks=bookmarks,
                    view_count=view_count
                ))
                
                added_count += 1
                logger.info(f"  ✅ ADDED NEW: Created in Leaderboard series")
        
        end_time = datetime.now()
        processing_time_ms = (end_time - start_time).total_seconds() * 1000
        month_name = datetime(year, month, 1).strftime("%B %Y")
        
        log_details = {
            "year": year,
            "month": month,
            "processing_time_ms": processing_time_ms,
            "files_processed": len(json_files),
            "files": [f.name for f in json_files],
            "reset_count": reset_count,
            "updated": updated_count,
            "added": added_count,
            "total_nanos": total_nanos,
            "total_dollars": total_nanos / 1000000000
        }
        write_fetch_log(data_dir, f"FETCH_LEADERBOARD_{year}-{month:02d}", log_details)
        
        return {
            "message": f"Leaderboard fetched for {month_name}",
            "processing_time_ms": processing_time_ms,
            "year": year,
            "month": month,
            "display_name": month_name,
            "files_processed": len(json_files),
            "reset_count": reset_count,
            "updated": updated_count,
            "added": added_count,
            "total_nanos": total_nanos,
            "total_dollars": total_nanos / 1000000000
        }
        
    except Exception as e:
        logger.error(f"Fetch leaderboard error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}    
    

@router.post("/update-leaderboard-stats")
async def update_leaderboard_stats():
    """Fetch COMPLETE stats (current month + lifetime) for stories with leaderboard flag = true"""
    try:
        logger.info("=" * 60)
        logger.info("UPDATING LEADERBOARD STORIES WITH COMPLETE STATS")
        logger.info("=" * 60)
        
        all_stories = await StoryService.get_all_stories()
        leaderboard_stories = [s for s in all_stories if s.leaderboard is True]
        
        if not leaderboard_stories:
            return {"message": "No leaderboard stories found", "updated": 0, "total": 0}
        
        logger.info(f"Found {len(leaderboard_stories)} leaderboard stories")
        
        fetcher = MediumStatsFetcher()
        
        if not fetcher.is_authenticated():
            logger.error("Not authenticated - no valid cookies found")
            return {"error": "Not authenticated. Please log into Medium in your browser, then close browser and try again."}
        
        results = {
            'total': len(leaderboard_stories),
            'updated': 0,
            'failed': 0,
            'details': []
        }
        
        for i, story in enumerate(leaderboard_stories):
            try:
                logger.info(f"\n📊 ({i+1}/{len(leaderboard_stories)}): {story.name}")
                
                if i > 0:
                    logger.info("   Waiting 3 seconds to avoid rate limiting...")
                    time.sleep(3)
                
                # Fetch complete stats from Medium API
                complete_stats = await fetcher.fetch_complete_stats(story.medium_url)
                
                if complete_stats:
                    # Get current month totals (from _get_current_month_payload)
                    totals = complete_stats.get('totals', {})
                    
                    # Get lifetime totals (from _get_lifetime_payload)
                    lifetime_totals = complete_stats.get('lifetime_totals', {})
                    
                    # Prepare update data with nested objects
                    update_data = StoryUpdate(
                        # Current month totals (updated monthly)
                        medium_member_reads=totals.get('member_reads', 0),
                        medium_nonmember_reads=totals.get('nonmember_reads', 0),
                        reads=totals.get('total_reads', 0),
                        medium_member_views=totals.get('member_views', 0),
                        medium_nonmember_views=totals.get('nonmember_views', 0),
                        view_count=totals.get('total_views', 0),
                        claps=totals.get('claps', 0),
                        responses=totals.get('replies', 0),
                        medium_highlights=totals.get('highlights', 0),
                        medium_new_followers=totals.get('new_followers', 0),
                        medium_read_ratio=totals.get('read_ratio', 0),
                        medium_member_read_percentage=totals.get('member_read_percentage', 0),
                        
                        # Lifetime totals (updated monthly)
                        lifetime_reads=lifetime_totals.get('total_reads', 0),
                        lifetime_views=lifetime_totals.get('total_views', 0),
                        lifetime_claps=lifetime_totals.get('claps', 0),
                        presentation_count=lifetime_totals.get('presentation_count', 0),
                        
                        # Post metadata
                        medium_first_published=complete_stats.get('first_published'),
                        medium_last_updated=complete_stats.get('last_updated'),
                        medium_title=complete_stats.get('title'),
                        medium_reading_time=complete_stats.get('reading_time', 0),
                        word_count=complete_stats.get('word_count', 0),
                        medium_tags=complete_stats.get('post_tags', []),
                        medium_topics=complete_stats.get('post_topics', []),
                        
                        # Update timestamp
                        last_stats_update=datetime.now().isoformat(),
                        medium_stats_updated=datetime.now().isoformat(),
                        lifetime_stats_updated=datetime.now().isoformat(),
                        medium_stats_data=complete_stats,
                        lifetime_stats_data=complete_stats
                    )
                    
                    await StoryService.update_story(story.key, update_data)
                    
                    results['updated'] += 1
                    results['details'].append({
                        'key': story.key,
                        'name': story.name,
                        'success': True,
                        'current_reads': totals.get('total_reads', 0),
                        'lifetime_reads': lifetime_totals.get('total_reads', 0),
                        'presentation_count': lifetime_totals.get('presentation_count', 0)
                    })
                    
                    logger.info(f"   ✅ Updated: Current: {totals.get('total_reads', 0)} reads, {totals.get('total_views', 0)} views")
                    logger.info(f"      Lifetime: {lifetime_totals.get('total_reads', 0)} reads, {lifetime_totals.get('total_views', 0)} views, {lifetime_totals.get('presentation_count', 0)} presentations")
                else:
                    results['failed'] += 1
                    results['details'].append({
                        'key': story.key,
                        'name': story.name,
                        'success': False
                    })
                    logger.warning(f"   ❌ Failed to fetch complete stats")
                    
            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'key': story.key,
                    'name': story.name,
                    'success': False,
                    'error': str(e)
                })
                logger.error(f"   ❌ Error: {e}")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"COMPLETE: {results['updated']}/{results['total']} leaderboard stories updated")
        logger.info(f"{'='*60}")
        
        return {
            "message": f"Updated {results['updated']} of {results['total']} leaderboard stories with complete stats",
            "results": results
        }

    except Exception as e:
        logger.error(f"Update leaderboard stats error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/clear-leaderboard")
async def clear_leaderboard():
    """Clear all leaderboard flags"""
    try:
        all_stories = await StoryService.get_all_stories()
        for story in all_stories:
            if story.leaderboard:
                await StoryService.update_story(story.key, StoryUpdate(leaderboard=False, leaderboard_nanos=0))
        return {"message": "All leaderboard flags cleared"}
    except Exception as e:
        logger.error(f"Clear leaderboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# CORE CRUD ENDPOINTS
# ============================================

@router.post("/sync")
async def sync_stories():
    """Sync with filesystem"""
    try:
        result = await StoryService.sync_with_filesystem()
        return {
            "message": "Sync completed",
            "added": result.get("added", 0),
            "updated": result.get("updated", 0),
            "total_stories": result.get("total", 0)
        }
    except Exception as e:
        logger.error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[StoryResponse])
async def list_stories(
    status: Optional[str] = Query(None),
    series: Optional[str] = Query(None),
    folder: Optional[str] = Query(None)
):
    """List all stories with optional filters"""
    stories = await StoryService.get_all_stories()
    if status:
        stories = [s for s in stories if s.status == status]
    if series:
        stories = [s for s in stories if s.series == series]
    if folder:
        stories = [s for s in stories if s.folder == folder]
    return stories


@router.post("/", response_model=StoryResponse, status_code=201)
async def create_story(story_data: StoryCreate):
    """Create a new story"""
    try:
        return await StoryService.create_story(story_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{story_key:path}", response_model=StoryResponse)
async def update_story(
    story_key: str = Path(..., description="The story key"),
    update_data: StoryUpdate = None
):
    """Update a story"""
    decoded_key = unquote(story_key)
    if decoded_key.lower().endswith('.md'):
        decoded_key = decoded_key[:-3]
    if update_data is None:
        update_data = StoryUpdate()
    story = await StoryService.update_story(decoded_key, update_data)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.post("/{story_key:path}/publish", response_model=StoryResponse)
async def publish_story(
    story_key: str = Path(..., description="The story key"),
    medium_url: Optional[str] = None
):
    """Mark a story as published"""
    decoded_key = unquote(story_key)
    if decoded_key.lower().endswith('.md'):
        decoded_key = decoded_key[:-3]
    story = await StoryService.publish_story(decoded_key, medium_url)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.delete("/{story_key:path}")
async def delete_story(story_key: str = Path(..., description="The story key")):
    """Delete a story"""
    decoded_key = unquote(story_key)
    if decoded_key.lower().endswith('.md'):
        decoded_key = decoded_key[:-3]
    deleted = await StoryService.delete_story(decoded_key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Story not found")
    return {"message": "Story deleted"}


@router.get("/{story_key:path}", response_model=StoryResponse)
async def get_story(story_key: str = Path(..., description="The story key")):
    """Get a single story"""
    decoded_key = unquote(story_key)
    if decoded_key.lower().endswith('.md'):
        decoded_key = decoded_key[:-3]
    
    story = await StoryService.get_story(decoded_key)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story

