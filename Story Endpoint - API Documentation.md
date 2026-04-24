# Story Endpoint - API Documentation

## Overview

The Story Endpoint provides complete CRUD operations and statistics management for Medium blog posts. Stories are stored in `stories.json` with support for series organization, publishing calendar, and Medium API integration.

## Base URL

```
http://localhost:8000/api/stories
```

---

## Endpoints

### 1. Get All Stories (Dashboard View)

**GET** `/api/stories/list`

Returns all stories with nested `medium` and `linkedin` objects, plus monthly stats for current month.

```bash
curl -X GET "http://localhost:8000/api/stories/list" | jq '.'
```

**Response:**
```json
{
  "stories": [
    {
      "key": "SOLID Principles/SOLID Principles: Part 1",
      "uniqueSlug": "solid-principles-part-1",
      "name": "SOLID Principles: Part 1",
      "title": "SOLID Principles: Part 1",
      "series": "SOLID Principles",
      "status": "Draft",
      "published_date": null,
      "created_date": "2026-04-19",
      "reads": 0,
      "views": 0,
      "claps": 0,
      "responses": 0,
      "member_reads": 0,
      "member_views": 0,
      "nonmember_reads": 0,
      "nonmember_views": 0,
      "medium_earnings": 0,
      "leaderboard": false,
      "medium": { ... },
      "linkedin": null
    }
  ],
  "total": 150,
  "scope": "All Time"
}
```

---

### 2. Get Stories for Specific Month

**GET** `/api/stories/list/{yearmonth}`

Returns stories with stats for a specific month from monthly storage.

```bash
curl -X GET "http://localhost:8000/api/stories/list/2026-04" | jq '.'
```

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `yearmonth` | string | Format: YYYY-MM (e.g., "2026-04") |

---

### 3. Get Single Story by Name

**GET** `/api/stories/story/name/{name}`

Returns a single story by its name (URL decoded).

```bash
curl -X GET "http://localhost:8000/api/stories/story/name/Architectural%20Remediation%20Framework%3A%20Part%201" | jq '.'
```

---

### 4. Get Single Story by Unique Slug

**GET** `/api/stories/story/{unique_slug}`

Returns a single story by its uniqueSlug.

```bash
curl -X GET "http://localhost:8000/api/stories/story/asp-net-core-filters-deep-dive-78cb972195da" | jq '.'
```

---

### 5. Update Story by Name

**PUT** `/api/stories/story/name/{name}`

Updates a story's fields (status, bookmarked, series, etc.).

```bash
curl -X PUT "http://localhost:8000/api/stories/story/name/Architectural%20Remediation%20Framework%3A%20Part%201" \
  -H "Content-Type: application/json" \
  -d '{"status": "Published", "bookmarked": true}' | jq '.'
```

**Request Body Options:**
```json
{
  "status": "Published|Draft|Ready|Done|Published Due",
  "bookmarked": true|false,
  "leaderboard": true|false,
  "series": "Series Name",
  "notes": "Updated notes",
  "publishedDate": "2026-04-24",
  "publishedDueDate": "2026-04-30",
  "medium_url": "https://medium.com/@username/post-title",
  "tags": ["tag1", "tag2"],
  "read_time": 10,
  "word_count": 1500,
  "linkedin_status": "scheduled|posted",
  "linkedin_url": "https://linkedin.com/posts/..."
}
```

---

### 6. Update Story by Unique Slug

**PUT** `/api/stories/story/{unique_slug}`

```bash
curl -X PUT "http://localhost:8000/api/stories/story/asp-net-core-filters-deep-dive-78cb972195da" \
  -H "Content-Type: application/json" \
  -d '{"bookmarked": true}' | jq '.'
```

---

### 7. Delete Story by Unique Slug

**DELETE** `/api/stories/story/{unique_slug}`

```bash
curl -X DELETE "http://localhost:8000/api/stories/story/asp-net-core-filters-deep-dive-78cb972195da" | jq '.'
```

---

### 8. Create New Story

**POST** `/api/stories/story`

```bash
curl -X POST "http://localhost:8000/api/stories/story" \
  -H "Content-Type: application/json" \
  -d '{
    "uniqueSlug": "my-new-story",
    "title": "My New Story",
    "folder": "Miscellaneous",
    "series": "Python Tutorials",
    "tags": ["python", "beginner"],
    "read_time": 10,
    "created_date": "2026-04-06",
    "medium_url": "https://medium.com/@username/post-title"
  }' | jq '.'
```

---

### 9. Mark Story as Published

**POST** `/api/stories/story/{unique_slug}/publish`

```bash
curl -X POST "http://localhost:8000/api/stories/story/asp-net-core-filters-deep-dive-78cb972195da/publish" \
  -H "Content-Type: application/json" \
  -d '{"medium_url": "https://medium.com/@username/post-title"}' | jq '.'
```

---

### 10. Sync Filesystem with stories.json

**POST** `/api/stories/sync`

Discovers new markdown files from the stories directory and adds them to `stories.json`.

```bash
curl -X POST "http://localhost:8000/api/stories/sync" | jq '.'
```

**Response:**
```json
{
  "success": true,
  "message": "Sync completed",
  "added": 5,
  "updated": 2,
  "total_stories": 150
}
```

---

## Statistics & Analytics Endpoints

### 11. Refresh Stats for Current Month (All Stories)

**POST** `/api/stories/refresh-stats`

Fetches latest stats from Medium API for all published stories in the current month.

```bash
curl -X POST "http://localhost:8000/api/stories/refresh-stats" | jq '.'
```

---

### 12. Refresh Stats for Specific Period

**POST** `/api/stories/refresh-stats/{period}`

```bash
curl -X POST "http://localhost:8000/api/stories/refresh-stats/2026-04" | jq '.'
```

---

### 13. Refresh Stats for Single Story (Current Month)

**POST** `/api/stories/refresh-story/{postId}`

Fetches lifetime and monthly stats for a specific story from Medium API.

```bash
curl -X POST "http://localhost:8000/api/stories/refresh-story/40793d1e9f2b" | jq '.'
```

---

### 14. Refresh Stats for Single Story (Specific Period)

**POST** `/api/stories/refresh-story/{postId}/{period}`

```bash
curl -X POST "http://localhost:8000/api/stories/refresh-story/40793d1e9f2b/2026-04" | jq '.'
```

**Response:**
```json
{
  "success": true,
  "message": "Stats fetched and saved for 2026-04",
  "post_id": "40793d1e9f2b",
  "period": "2026-04",
  "story_key": "Dotnet Python NodeJS/Achieving 10x Faster Serialization",
  "story_name": "Achieving 10x Faster Serialization in .NET Core",
  "updated_totalStats": {
    "presentations": 7949,
    "views": 4048,
    "reads": 2171
  },
  "updated": true
}
```

---

### 15. Get Total Earnings Across All Months

**GET** `/api/stories/earnings/total`

```bash
curl -X GET "http://localhost:8000/api/stories/earnings/total" | jq '.'
```

**Response:**
```json
{
  "total_earnings": 5870000000,
  "total_nanos": 5870000000,
  "formatted": "$5.87",
  "months_processed": 6
}
```

---

### 16. Get Leaderboard Status for All Stories

**GET** `/api/stories/leaderboard-status`

Returns all stories that ever had leaderboard earnings.

```bash
curl -X GET "http://localhost:8000/api/stories/leaderboard-status" | jq '.'
```

---

### 17. Get Available Months for Dropdown

**GET** `/api/stories/months`

```bash
curl -X GET "http://localhost:8000/api/stories/months" | jq '.'
```

**Response:**
```json
{
  "months": ["2026-04", "2026-03", "2026-02"]
}
```

---

### 18. Get Current Mode and Available Months

**GET** `/api/stories/mode`

```bash
curl -X GET "http://localhost:8000/api/stories/mode" | jq '.'
```

**Response:**
```json
{
  "mode": "dashboard",
  "current_month": {"year": 2026, "month": 4},
  "available_months": [...]
}
```

---

### 19. Switch to Month View

**POST** `/api/stories/switch-month`

```bash
curl -X POST "http://localhost:8000/api/stories/switch-month?year=2026&month=4" | jq '.'
```

---

### 20. Switch to Dashboard Mode

**POST** `/api/stories/switch-to-dashboard`

```bash
curl -X POST "http://localhost:8000/api/stories/switch-to-dashboard" | jq '.'
```

---

## Story Content Endpoints

### 21. Get Story Markdown Content

**GET** `/api/stories/content/{story_key}`

Returns the raw markdown content of a story file.

```bash
curl -X GET "http://localhost:8000/api/stories/content/SOLID%20Principles/SOLID%20Principles%3A%20Part%201" | jq '.'
```

---

### 22. Save Story Markdown Content

**PUT** `/api/stories/content/{story_key}`

Updates the markdown file content.

```bash
curl -X PUT "http://localhost:8000/api/stories/content/SOLID%20Principles/SOLID%20Principles%3A%20Part%201" \
  -H "Content-Type: application/json" \
  -d '{"content": "# Updated Title\n\nNew content here..."}' | jq '.'
```

---

## Story Status Values

| Status | Description |
|--------|-------------|
| `Draft` | Initial state, not yet ready for publishing |
| `Done` | Content complete, ready for review |
| `Ready` | Reviewed and ready to schedule |
| `Published` | Published on Medium |
| `Published Due` | Scheduled for future publication |

---

## Story Object Structure

```json
{
  "key": "folder/story-name",
  "uniqueSlug": "story-title-slug",
  "name": "Story Title",
  "title": "Story Title",
  "series": "Series Name",
  "status": "Published",
  "createdDate": "2026-04-19",
  "publishedDate": "2026-04-20",
  "publishedDueDate": "2026-04-25",
  "lastUpdated": "2026-04-24T12:23:50.533302",
  "notes": "Story notes",
  "tags": ["tag1", "tag2"],
  "word_count": 1500,
  "read_time": 10,
  "bookmarked": false,
  "leaderboard": false,
  "lifetime_reads": 2171,
  "lifetime_views": 4048,
  "presentation_count": 7949,
  "feed_click_through_rate": 0.17,
  "medium_url": "https://medium.com/...",
  "medium": {
    "id": "post-id",
    "title": "Story Title",
    "uniqueSlug": "story-slug",
    "totalStats": {
      "period": "total",
      "presentations": 7949,
      "views": 4048,
      "reads": 2171
    },
    "monthlyStats": [
      {
        "period": "2026-04",
        "presentations": 7949,
        "views": 4048,
        "reads": 2171,
        "claps": 51,
        "responses": 1,
        "medium_member_reads": 1200,
        "medium_member_views": 2500,
        "medium_nonmember_reads": 971,
        "medium_nonmember_views": 1548,
        "medium_read_ratio": 53.6,
        "medium_member_read_percentage": 55.3,
        "medium_new_followers": 5,
        "medium_highlights": 12
      }
    ],
    "monthlyEarnings": [
      {
        "period": "2026-04",
        "currencyCode": "USD",
        "units": 8,
        "nanos": 40000000
      }
    ]
  },
  "linkedin": {
    "type": "Article",
    "status": "posted",
    "timestamp": "2026-04-23T12:32",
    "impressions": 45,
    "url": "https://linkedin.com/..."
  }
}
```

---

## Error Responses

| Status Code | Description |
|-------------|-------------|
| 400 | Bad request (invalid parameters) |
| 404 | Story not found |
| 500 | Internal server error |

**Error Response Format:**
```json
{
  "detail": "Error message describing the issue"
}
```