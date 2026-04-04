# Leaderboard Management Feature - README

## Overview

The Leaderboard Management feature allows you to import Medium earnings data from JSON files, manage which stories appear on the leaderboard, and fetch real-time statistics from Medium's API for those stories. All operations are logged for audit and debugging purposes, with comprehensive debug endpoints for troubleshooting.

## Application Architecture - Modular Splitting

The application has been refactored from a single large `index.html` file into a modular structure for better maintainability.

### Original vs Refactored Structure

| Aspect | Original | Refactored |
|--------|----------|------------|
| **HTML** | Single 3000+ line file | Separate component templates |
| **CSS** | Embedded in HTML | External `styles.css` |
| **JavaScript** | All in one script | 10 modular JS files |
| **Logging** | Console only | File-based logging with JSON + TXT |
| **Debugging** | Hard to find issues | 10+ debug endpoints + detailed logs |
| **Maintainability** | Difficult | Easy |
| **Collaboration** | Single file conflicts | Multiple files, less conflicts |
| **Load Time** | Same page load | Cached static files |

### File Structure After Refactoring

```
app/
├── main.py                          # FastAPI application entry point
├── models.py                        # Pydantic data models
├── config.py                        # Configuration settings
├── routers/
│   ├── stories.py                   # Story CRUD & leaderboard endpoints
│   ├── series.py                    # Series management endpoints
│   ├── calendar.py                  # Calendar endpoints
│   └── settings.py                  # Settings endpoints
├── services/
│   ├── story_service.py             # Story business logic
│   ├── file_service.py              # File I/O operations
│   ├── calendar_service.py          # Calendar generation logic
│   ├── medium_stats_fetcher.py      # Medium API integration
│   ├── medium_stats_service.py      # Stats service (fallback)
│   └── app_status_service.py        # App state management
├── static/
│   ├── css/
│   │   └── styles.css               # All CSS styles
│   └── js/
│       ├── main.js                  # App initialization & navigation
│       ├── utils.js                 # Utility functions
│       ├── dashboard.js             # Dashboard view
│       ├── stories.js               # Stories CRUD & table
│       ├── series.js                # Series management
│       ├── calendar.js              # Calendar view
│       ├── settings.js              # Settings view
│       ├── leaderboard.js           # Leaderboard fetch functions
│       ├── linkedin.js              # LinkedIn marketing
│       └── stats.js                 # Stats dashboard
└── templates/
    ├── index.html                   # Main template (includes all components)
    ├── components/
    │   └── sidebar.html             # Sidebar navigation
    └── modals/
        ├── edit-story-modal.html    # Edit story modal
        ├── add-story-modal.html     # Add story modal
        └── stats-modal.html         # Stats dashboard modal
```

### JavaScript Module Responsibilities

| File | Responsibility | Key Functions |
|------|----------------|----------------|
| `main.js` | App initialization, navigation, global state | `loadView()`, event handlers |
| `utils.js` | Shared utilities | `formatNumber()`, `escapeHtml()`, `calcMemberPercent()` |
| `dashboard.js` | Dashboard view | `loadDashboard()` |
| `stories.js` | Stories CRUD, table, filters | `loadStories()`, `renderStoryTable()`, `editStory()`, `saveStoryEdit()` |
| `series.js` | Series management | `loadSeries()`, `addSeries()`, `deleteSeries()` |
| `calendar.js` | Calendar view | `loadCalendar()`, `generateCalendar()` |
| `settings.js` | Settings view | `loadSettings()` |
| `leaderboard.js` | Leaderboard file management | `loadLeaderboardFileList()`, `fetchLeaderboardForMonth()` |
| `linkedin.js` | LinkedIn marketing | `setNowLinkedinTimestamp()`, `clearAllLinkedinData()` |
| `stats.js` | Stats dashboard | `showStatsDashboard()`, `refreshStatsForCurrentMonth()` |

### Benefits of Modular Splitting

1. **Maintainability**: Each feature has its own file, making it easy to find and fix issues
2. **Reusability**: Components can be reused across different views
3. **Collaboration**: Multiple developers can work on different files simultaneously
4. **Debugging**: Clear separation of concerns makes debugging faster
5. **Load Performance**: Static files (CSS, JS) are cached by the browser
6. **Code Organization**: Clear structure with logical grouping

### How Files are Merged at Runtime

The merging happens in two ways:

1. **Server-side (Templates)**: Jinja2 includes combine HTML components
   ```html
   {% include 'components/sidebar.html' %}
   {% include 'modals/edit-story-modal.html' %}
   ```

2. **Client-side (Browser)**: Static files are loaded in sequence
   ```html
   <link rel="stylesheet" href="/static/css/styles.css">
   <script src="/static/js/utils.js"></script>
   <script src="/static/js/main.js"></script>
   ```

### Script Loading Order (Critical)

The order of script loading in `index.html` matters:

```html
<!-- Core utilities first -->
<script src="/static/js/utils.js"></script>

<!-- Feature modules (order doesn't matter as much) -->
<script src="/static/js/linkedin.js"></script>
<script src="/static/js/leaderboard.js"></script>
<script src="/static/js/dashboard.js"></script>
<script src="/static/js/stories.js"></script>
<script src="/static/js/series.js"></script>
<script src="/static/js/calendar.js"></script>
<script src="/static/js/settings.js"></script>
<script src="/static/js/stats.js"></script>

<!-- Main app (must be last) -->
<script src="/static/js/main.js"></script>
```

### New Files Added

| File | Purpose |
|------|---------|
| `app/services/app_status_service.py` | Manages app state (leaderboard month) |
| `app/static/js/main.js` | Application entry point |
| `app/static/js/utils.js` | Shared utilities |
| `app/static/js/leaderboard.js` | Leaderboard-specific functions |
| `app/static/js/linkedin.js` | LinkedIn marketing functions |
| `app/static/js/stats.js` | Stats dashboard functions |
| `app/static/css/styles.css` | All CSS extracted from HTML |
| `app/templates/components/sidebar.html` | Sidebar component |
| `app/templates/modals/*.html` | Modal components |

## Debugging Endpoints

### Overview

The application includes comprehensive debug endpoints for troubleshooting and development. These endpoints help identify issues with data matching, file detection, and API responses.

### Debug Endpoints List

| Endpoint | Method | Description | Use Case |
|----------|--------|-------------|----------|
| `/api/stories/debug/all` | GET | List all stories with basic info | Quick overview of all stories |
| `/api/stories/debug/urls` | GET | List all stories with Medium URLs | Check URL assignments |
| `/api/stories/debug/keys` | GET | List all story keys | Verify story key format |
| `/api/stories/debug/find/{search}` | GET | Find stories by search term | Locate specific stories |
| `/api/stories/debug/list-all` | GET | List all stories with details | Full story inventory |
| `/api/stories/debug/test-lifetime` | GET | Test lifetime API with known post ID | Verify API authentication |
| `/api/stories/debug/leaderboard-files` | GET | Check leaderboard file discovery | Debug file pattern matching |
| `/api/stories/debug/title-matching` | GET | Compare title normalization | Debug matching issues |
| `/api/stories/logs` | GET | List all log files | Check available logs |
| `/api/stories/logs/{year_month}` | GET | Get detailed logs | Review operation history |

### Using Debug Endpoints

#### 1. Check All Stories
```bash
curl -s "http://localhost:8000/api/stories/debug/all" | jq '.'
```

#### 2. Find Specific Story
```bash
curl -s "http://localhost:8000/api/stories/debug/find/ASP.NET" | jq '.'
```

#### 3. Test Title Matching
```bash
curl -s "http://localhost:8000/api/stories/debug/title-matching" | jq '.matches'
```

#### 4. Check Leaderboard File Detection
```bash
curl -s "http://localhost:8000/api/stories/debug/leaderboard-files" | jq '.'
```

#### 5. Test Lifetime API Authentication
```bash
curl -s "http://localhost:8000/api/stories/debug/test-lifetime" | jq '.'
```

#### 6. List All Story Keys
```bash
curl -s "http://localhost:8000/api/stories/debug/keys" | jq '.keys[:10]'
```

#### 7. List All Stories with Details
```bash
curl -s "http://localhost:8000/api/stories/debug/list-all" | jq '.stories[:5]'
```

#### 8. Check Log Files
```bash
# List all logs
curl -s "http://localhost:8000/api/stories/logs" | jq '.'

# Get logs for April 2026
curl -s "http://localhost:8000/api/stories/logs/2026-04" | jq '.entries[:2]'
```

### Debug Endpoint Implementation

The debug endpoints are implemented in `app/routers/stories.py`:

```python
@router.get("/debug/all")
async def debug_all():
    """Debug endpoint to list all stories"""
    stories = await StoryService.get_all_stories()
    return {
        "total": len(stories),
        "stories": [
            {
                "key": s.key,
                "name": s.name,
                "medium_url": s.medium_url,
                "status": s.status,
                "leaderboard": s.leaderboard
            }
            for s in stories
        ]
    }

@router.get("/debug/find/{search}")
async def find_story(search: str):
    """Find stories containing search term"""
    stories = await StoryService.get_all_stories()
    matches = [
        {"key": s.key, "name": s.name, "medium_url": s.medium_url}
        for s in stories 
        if search.lower() in s.key.lower() 
        or search.lower() in s.name.lower() 
        or (s.medium_url and search.lower() in s.medium_url.lower())
    ]
    return {"search": search, "matches": matches}

@router.get("/debug/title-matching")
async def debug_title_matching():
    """Debug endpoint to compare title normalization between DB and JSON"""
    # Returns normalized titles for comparison
    ...

@router.get("/debug/leaderboard-files")
async def debug_leaderboard_files():
    """Debug endpoint to check leaderboard file discovery"""
    # Returns all files found and patterns tried
    ...
```

## Logging System

### Overview

All leaderboard fetch operations are logged to both JSON and text files for audit trail and debugging purposes.

### Log Files Location

```
data/logs/
├── 2026-04.log                    # JSON format - detailed operation logs
├── 2026-04_summary.txt            # Human-readable summary
├── 2026-03.log
├── 2026-03_summary.txt
└── ...
```

### Log File Formats

#### JSON Log (`YYYY-MM.log`)
Each line is a JSON object containing complete operation details:

```json
{
  "timestamp": "2026-04-04T10:30:00.123456",
  "operation": "FETCH_LEADERBOARD_2026-04",
  "details": {
    "year": 2026,
    "month": 4,
    "processing_time_ms": 715.921,
    "files_processed": 2,
    "files": ["leaderboard-2026-04-part1.json", "leaderboard-2026-04-part2.json"],
    "reset_count": 5,
    "updated": 3,
    "added": 2,
    "total_nanos": 1610000000,
    "total_dollars": 1.61,
    "files_details": [
      {
        "filename": "leaderboard-2026-04-part1.json",
        "stories_found": 10,
        "processing_time_ms": 350.5
      }
    ],
    "deduplication_details": [...],
    "update_details": [...],
    "add_details": [...]
  }
}
```

#### Summary Log (`YYYY-MM_summary.txt`)
Human-readable format for quick review:

```
================================================================================
Operation: FETCH_LEADERBOARD_2026-04
Timestamp: 2026-04-04T10:30:00.123456
Files Processed: 2
Stories Updated: 3
Stories Added: 2
Stories Reset: 5
Total Earnings: $1.61
Source Files: leaderboard-2026-04-part1.json, leaderboard-2026-04-part2.json
================================================================================
```

### What Gets Logged

| Operation | Logged Information |
|-----------|-------------------|
| **Fetch Leaderboard** | Year, month, files processed, reset count, updated count, added count, total earnings, processing time |
| **Fetch Error** | Error message, traceback, year, month, expected file patterns |
| **Fetch Empty** | Files processed, total stories found (0) |

## Features

### 1. JSON Import (Sidebar)
- **Purpose**: Import earnings data from exported Medium JSON files
- **Location**: Sidebar → "Leaderboard Data" section
- **File Pattern**: `leaderboard-YYYY-MM-partN.json` (supports multiple parts)
- **Logging**: Logs files processed, stories updated/added/reset, total earnings
- **What it does**:
  - Resets ALL stories' `leaderboard` flag to `false`
  - For stories in JSON: Sets `leaderboard=true` and updates all metadata
  - For new stories: Creates them in "Leaderboard" series with `status="Published"`
  - For existing stories: Keeps original series (does NOT change)

### 2. Update Leaderboard Stats
- **Purpose**: Fetch real-time statistics from Medium API for leaderboard stories
- **Location**: Dashboard button, Stories page button
- **Logging**: Logs which stories were updated, success/failure counts
- **What it does**:
  - Finds all stories with `leaderboard=true`
  - Fetches current month stats from Medium API
  - Fetches lifetime stats from Medium API
  - Updates database with fresh stats
  - Updates `lifetime_reads`, `lifetime_views`, `presentation_count`

### 3. Stats Dashboard
- **Purpose**: View detailed statistics for individual stories
- **Location**: Click the graph icon on any story row
- **What it shows**:
  - Current month reads (member/total with percentage)
  - Current month views (member/total with percentage)
  - Claps, responses, highlights
  - Lifetime reads, views, claps
  - Presentation count
  - Read ratio
- **Refresh**: Click "Refresh from Medium" to fetch fresh data for the loaded month

### 4. Leaderboard Month Tracking
- **Purpose**: Track which month's leaderboard is currently loaded
- **Storage**: `data/appstatus.json`
- **Display**: Shows current month in sidebar
- **Usage**: "Update Leaderboard Stats" uses this month for API calls

## Data Files Structure

```
data/
├── leaderboard-2026-04-part1.json    # Earnings JSON files
├── leaderboard-2026-04-part2.json
├── stories.json                       # Main stories database
├── appstatus.json                     # App state (current leaderboard month)
└── logs/
    ├── 2026-04.log                    # JSON format logs
    └── 2026-04_summary.txt            # Human-readable logs
```

### Sample `appstatus.json`
```json
{
  "leaderboard_month": "2026-04",
  "last_updated": "2026-04-04T10:30:00.123456"
}
```

## API Endpoints

### Core Endpoints
| Endpoint | Method | Description | Logging |
|----------|--------|-------------|---------|
| `/api/stories/leaderboard-files` | GET | List available JSON files by month | No |
| `/api/stories/fetch-leaderboard-for-month` | POST | Import JSON data for specific month | Yes |
| `/api/stories/update-leaderboard-stats` | POST | Fetch fresh stats from Medium API | No |
| `/api/stories/leaderboard-month` | GET | Get current leaderboard month | No |
| `/api/stories/leaderboard-month?year=X&month=Y` | POST | Set leaderboard month | No |
| `/api/stories/fetch-lifetime-stats/{key}` | POST | Fetch stats for single story | No |

### Debug Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stories/debug/all` | GET | List all stories with basic info |
| `/api/stories/debug/urls` | GET | List all stories with Medium URLs |
| `/api/stories/debug/keys` | GET | List all story keys |
| `/api/stories/debug/find/{search}` | GET | Find stories by search term |
| `/api/stories/debug/list-all` | GET | List all stories with details |
| `/api/stories/debug/test-lifetime` | GET | Test lifetime API with known post ID |
| `/api/stories/debug/leaderboard-files` | GET | Check leaderboard file discovery |
| `/api/stories/debug/title-matching` | GET | Compare title normalization |

### Log Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stories/logs` | GET | List all log files |
| `/api/stories/logs/{year_month}` | GET | Get detailed logs for specific month |

## Data Flow with Logging and Debugging

```
1. User places JSON files in data/ directory
   ↓ [Debug: /debug/leaderboard-files to verify]
2. Sidebar shows available months with file counts
   ↓
3. User clicks "Fetch" for a month
   ↓
4. System writes to log: FETCH_LEADERBOARD_2026-04 started
   ↓
5. System resets all leaderboard flags
   ↓ [Debug: /debug/all to verify reset]
6. For each story in JSON:
   - Existing: Sets leaderboard=true, updates metadata
   - New: Creates story in "Leaderboard" series
   ↓ [Debug: /debug/find/{title} to verify matching]
7. System writes to log: completion details
   ↓
8. User clicks "Update Leaderboard Stats"
   ↓ [Debug: /debug/test-lifetime to verify API auth]
9. System fetches fresh stats from Medium API for leaderboard stories
   ↓
10. Stats are updated (reads, views, claps, lifetime totals)
    ↓ [Debug: /debug/urls to verify URL assignments]
```

## Database Fields

### Current Month Stats (from Medium API)
| Field | Description |
|-------|-------------|
| `reads` | Total reads (member + non-member) |
| `view_count` | Total views (member + non-member) |
| `claps` | Total claps |
| `medium_member_reads` | Reads from Medium members |
| `medium_member_views` | Views from Medium members |
| `medium_nonmember_reads` | Reads from non-members |
| `medium_nonmember_views` | Views from non-members |
| `medium_read_ratio` | (reads/views) * 100 |
| `medium_member_read_percentage` | (member_reads/total_reads) * 100 |

### Lifetime Stats (from Medium API)
| Field | Description |
|-------|-------------|
| `lifetime_reads` | All-time total reads |
| `lifetime_views` | All-time total views |
| `lifetime_claps` | All-time total claps |
| `presentation_count` | How many times the story was presented |

### Leaderboard Earnings (from JSON)
| Field | Description |
|-------|-------------|
| `leaderboard` | Boolean flag (true/false) |
| `leaderboard_nanos` | Monthly earnings in nanos |
| `leaderboard_lifetime_nanos` | Lifetime earnings in nanos |

## UI Components

### Sidebar Leaderboard Section
- Shows available months with file counts
- Each month has a "Fetch" button
- Displays current loaded month prominently

### Dashboard
- Summary cards for total stories, published, ready, etc.
- Leaderboard-specific stats card
- Recent stories list
- Upcoming schedule

### Stories Table
- Columns: Bookmark, Leaderboard, Status, Name, Publish Date, Reads, Views, Claps, Impressions, Lifetime, LinkedIn, Publication, Actions
- Sortable columns
- Filterable by status, series, search, bookmarked, leaderboard
- Click row to edit

### Edit Story Modal
- Edit status, publication, dates, tags
- View current month and lifetime stats
- Manage LinkedIn marketing data
- Toggle leaderboard status manually
- Edit earnings (nanos)

## Configuration

### Rate Limiting
All API calls have delays to avoid rate limiting:
- Between stories: 0.5 seconds
- Between API calls per story: 0.5 seconds

### Timeouts
- API requests: 30 seconds timeout

### File Patterns for JSON
The system looks for files matching:
- `leaderboard-YYYY-MM.json`
- `leaderboard-YYYY-MM-partN.json`
- `leaderboard-YYYY-MM.-N.json`
- `leaderboard-YYYY-MM.N.json`
- Any file with `leaderboard-YYYY-MM` in the name

## Troubleshooting Guide

### Issue: No leaderboard files found
```bash
# Debug: Check what files are detected
curl -s "http://localhost:8000/api/stories/debug/leaderboard-files" | jq '.'

# Manual check
ls -la data/ | grep leaderboard
```

### Issue: Stories not matching during import
```bash
# Debug: Check title normalization
curl -s "http://localhost:8000/api/stories/debug/title-matching" | jq '.matches'

# Find specific story
curl -s "http://localhost:8000/api/stories/debug/find/ASP.NET" | jq '.'
```

### Issue: Authentication problems
```bash
# Debug: Test lifetime API authentication
curl -s "http://localhost:8000/api/stories/debug/test-lifetime" | jq '.'
```

### Issue: Stats not updating
```bash
# Debug: Check story URLs
curl -s "http://localhost:8000/api/stories/debug/urls" | jq '.urls[:5]'

# Check all stories
curl -s "http://localhost:8000/api/stories/debug/all" | jq '.stories[:5]'
```

### Issue: Calendar UI broken
```bash
# Debug: Check calendar API response
curl -s "http://localhost:8000/api/calendar/" | jq '.'
```

### Issue: Logs not being written
```bash
# Debug: Check log files
curl -s "http://localhost:8000/api/stories/logs" | jq '.'

# Check directory permissions
ls -la data/logs/
```

## Development Setup

### Prerequisites
- Python 3.8+
- FastAPI
- Bootstrap 5
- Modern web browser

### Running the App
```bash
cd /path/to/Medium-Story-Manger
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Accessing the App
- Open browser to `http://localhost:8000`

### Viewing Logs
```bash
# Watch JSON logs in real-time
tail -f data/logs/2026-04.log | jq '.'

# Watch summary logs
tail -f data/logs/2026-04_summary.txt
```

### Running Debug Checks
```bash
# Quick health check
curl -s "http://localhost:8000/health" | jq '.'

# Full debug
curl -s "http://localhost:8000/api/stories/debug/all" | jq '.total'
```

### Making Changes to CSS
- Edit `app/static/css/styles.css`
- Refresh browser (cached CSS may need hard refresh)

### Making Changes to JavaScript
- Edit the specific JS file in `app/static/js/`
- Refresh browser

### Making Changes to Templates
- Edit the specific HTML file in `app/templates/`
- Server auto-reloads (with `--reload` flag)

## Dependencies

- FastAPI - Web framework
- Bootstrap 5 - UI components
- Bootstrap Icons - Icons
- requests - HTTP calls to Medium API
- BeautifulSoup4 - HTML parsing (fallback)
- Jinja2 - Template engine
- jq - JSON processor (for command-line debugging)

## Version History

### v2.0.0 (Current)
- **Modular Refactoring**: Split monolithic HTML into modular components
- **External CSS**: All styles moved to `styles.css`
- **Modular JavaScript**: Split into 10 focused JS files
- **Debug Endpoints**: 10+ endpoints for comprehensive troubleshooting
- **Logging System**: JSON and text logging for fetch operations
- **Log API Endpoints**: `/logs` and `/logs/{year_month}` for viewing logs
- **Leaderboard Month Tracking**: Added `appstatus.json` for state management
- **Month-Specific Stats**: Can fetch stats for any loaded month, not just current
- **Fixed Title Normalization**: Better matching for stories with different dash types
- **Added Lifetime Stats**: `lifetime_reads`, `lifetime_views`, `presentation_count`
- **Stats Dashboard**: New modal to view detailed story statistics
- **Reduced API Delays**: From 3 seconds to 0.5 seconds
- **Fixed Calendar UI**: Proper HTML table rendering
- **Fixed Modal Backdrop**: Proper cleanup when closing modals

### v1.0.0
- Initial JSON import functionality
- Basic leaderboard management
- Current month stats fetching
- Single file architecture
- Console-only logging
- No debug endpoints