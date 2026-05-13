# Story Stats Widget - README

## Overview

A reusable, expandable/collapsible widget that displays monthly analytics from Medium, including presentations, viewers, readers, followers gained, subscribers gained, and a line chart showing daily viewers/readers trends.

## File Structure

```
app/static/
├── css/
│   └── story-stats-widget.css
├── js/
│   └── story-stats-widget.js
└── templates/
    └── components/
        └── story-stats-widget.html
```

## Backend Implementation

### 1. Medium API Service (`medium_api_service.py`)

```python
def fetch_monthly_stats(self, period: str) -> Optional[Dict[str, Any]]:
    """Fetch aggregated monthly stats for all stories using GraphQL query"""
```

**Input:** `period` - String in "YYYY-MM" format (e.g., "2026-05")

**Output:**
```python
{
    "totals": {
        "presentations": int,
        "viewers": int,
        "readers": int,
        "netFollowersGained": int,
        "netSubscribersGained": int
    },
    "points": [
        {"timestamp": int, "viewers": int, "readers": int}
    ]
}
```

### 2. Story Service (`story_service.py`)

```python
@staticmethod
async def fetch_monthly_stats(period: str) -> Dict[str, Any]:
    """Thin wrapper around medium_api_service"""
```

**Input:** `period` - String in "YYYY-MM" format

**Output:**
```python
{
    "success": bool,
    "period": str,
    "totals": {...},
    "points": [...],
    "message": str (if success=False)
}
```

### 3. API Endpoints (`stories.py`)

```python
GET /api/stories/monthly-stats/
GET /api/stories/monthly-stats/{period}
```

**Response:**
```json
{
    "success": true,
    "period": "2026-05",
    "totals": {
        "presentations": 14990,
        "viewers": 4412,
        "readers": 1068,
        "netFollowersGained": 30,
        "netSubscribersGained": 24
    },
    "points": [
        {"timestamp": 1777593600000, "viewers": 432, "readers": 75},
        {"timestamp": 1777680000000, "viewers": 431, "readers": 85}
    ]
}
```

## Frontend Implementation

### 1. Add to Base Template

```html
<!-- In base.html or stories.html -->
<link rel="stylesheet" href="/static/css/story-stats-widget.css">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="/static/js/story-stats-widget.js"></script>
```

### 2. Add Container in HTML

```html
<!-- Place above stories table -->
<div id="storyStatsWidget"></div>
```

### 3. Widget Initialization

The widget auto-initializes when DOM loads. No additional code needed.

```javascript
// Auto-initializes on DOMContentLoaded
// Global instance available at: window.monthlyStatsWidget
```

## Public Methods

| Method | Description | Example |
|--------|-------------|---------|
| `setYearMonth(year, month)` | Update widget to specific month | `window.monthlyStatsWidget.setYearMonth(2026, 5)` |
| `getCurrentPeriod()` | Get current period string | `window.monthlyStatsWidget.getCurrentPeriod()` // "2026-05" |
| `expand()` | Expand widget body | `window.monthlyStatsWidget.expand()` |
| `collapse()` | Collapse widget body | `window.monthlyStatsWidget.collapse()` |
| `toggle()` | Toggle expand/collapse | `window.monthlyStatsWidget.toggle()` |
| `loadStats()` | Refresh data from API | `window.monthlyStatsWidget.loadStats()` |
| `syncStats()` | Sync fresh data from Medium | `window.monthlyStatsWidget.syncStats()` |

## Events

| Event | Detail | Description |
|-------|--------|-------------|
| `statsPeriodChanged` | `{ year, month, period }` | Fired when user changes month/year in widget |

## Integration Examples

### Parent → Widget (Sync Parent to Widget)

```javascript
// In stories.js after loading month stats
function syncWidgetWithParent() {
    const year = parseInt(document.getElementById('yearSelect').value);
    const month = parseInt(document.getElementById('monthSelect').value);
    if (window.monthlyStatsWidget) {
        window.monthlyStatsWidget.setYearMonth(year, month);
    }
}

// Call after loading parent data
await loadMonthStats();
syncWidgetWithParent();
```

### Widget → Parent (Sync Widget to Parent)

```javascript
// Listen to widget changes
window.addEventListener('statsPeriodChanged', (event) => {
    const { year, month } = event.detail;
    
    // Update parent selectors
    document.getElementById('yearSelect').value = year;
    document.getElementById('monthSelect').value = month;
    
    // Reload parent table data
    loadMonthStats();
});
```

### Two-Way Sync (Complete Example)

```javascript
// In stories.js - Complete integration

// 1. Sync parent → widget when parent changes
async function loadMonthStats() {
    const year = parseInt(yearSelect.value);
    const month = parseInt(monthSelect.value);
    
    // Update widget
    if (window.monthlyStatsWidget) {
        window.monthlyStatsWidget.setYearMonth(year, month);
    }
    
    // Load parent table
    const response = await fetch(`${API_BASE}/stories/monthly-stats/${year}-${month}`);
    // ... render table
}

// 2. Sync widget → parent when widget changes
window.addEventListener('statsPeriodChanged', (event) => {
    yearSelect.value = event.detail.year;
    monthSelect.value = event.detail.month;
    loadMonthStats(); // Reload with new month
});

// 3. Initial sync on page load
document.addEventListener('DOMContentLoaded', () => {
    // Wait for widget to initialize
    setTimeout(() => {
        syncWidgetWithParent();
    }, 500);
});
```

### Refresh Stories Table After Sync

```javascript
// Automatically refreshes parent table when sync completes
// Widget calls window.loadStories() if function exists
// Just ensure loadStories() is globally available

window.loadStories = async function() {
    // Your existing loadStories implementation
};
```

## Features

- **Expandable/Collapsible** - Default collapsed, click header to expand
- **Inline Stats Display** - All metrics in single horizontal line with icons
- **Line Chart** - Daily viewers and readers trends using Chart.js
- **Tooltips** - Hover shows full numbers (not abbreviated)
- **Month/Year Selectors** - Built-in selectors for data exploration
- **Refresh Button** - Reload current data from API
- **Sync Button** - Fetch fresh data from Medium API
- **Auto-sync** - Widget can sync with parent page selectors
- **Responsive** - Adapts to mobile screen sizes

## Dependencies

- Bootstrap Icons (bi CSS classes)
- Chart.js v4.4.0
- Bootstrap 5 (for card, button, select styles)

## Notes

- No data is saved anywhere - all data is fetched live from Medium API
- Widget shows aggregated stats for ALL stories combined (account-level metrics)
- The GraphQL query uses `username` from settings, no `post_id` required
- Tooltips show full numbers (e.g., "24,532" instead of "24.5K")