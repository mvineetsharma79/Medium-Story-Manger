# Medium Story Manager - Complete Documentation

## Architecture Overview

```mermaid
flowchart TB
    subgraph UI["UI LAYER"]
        D[Dashboard Page]
        S[Stories Page]
        SE[Series Page]
        C[Calendar Page]
        ST[Settings Page]
    end

    subgraph API["FASTAPI ROUTERS"]
        DR[Dashboard Router]
        SR[Stories Router]
        SER[Series Router]
        CR[Calendar Router]
        STR[Settings Router]
    end

    subgraph SERVICES["SERVICES LAYER"]
        MAS[MediumAPIService<br/>- fetch_stats()<br/>- fetch_lifetime_stats()<br/>- fetch_leaderboard()]
        MSS[MonthlyStorageService<br/>- load_monthly()<br/>- save_monthly()<br/>- update_stats()]
        SS[StoryService<br/>- get_all_stories()<br/>- update_story()<br/>- sync_filesystem()]
        CS[CalendarService<br/>- generate_calendar()<br/>- save_calendar_files()]
    end

    subgraph STORAGE["DATA STORAGE"]
        SJ[stories.json<br/>- Story metadata<br/>- Lifetime stats<br/>- LinkedIn marketing]
        MJ[stories-YYYY-MM.json<br/>- Monthly stats<br/>- Leaderboard flags<br/>- Monthly earnings]
    end

    subgraph EXTERNAL["EXTERNAL API"]
        MA[Medium GraphQL API<br/>https://medium.com/_/graphql]
    end

    UI --> API
    API --> SERVICES
    SERVICES --> STORAGE
    SERVICES --> EXTERNAL
```

---

## Complete Data Flow Diagram

```mermaid
flowchart LR
    subgraph USER["USER ACTION"]
        U1[Click Fetch Stats]
        U2[Open Dashboard]
        U3[Select Month View]
        U4[Toggle Leaderboard]
    end

    subgraph BACKEND["BACKEND PROCESSING"]
        direction TB
        B1[POST /fetch-story-stats/{post_id}/{yearmonth}]
        B2[GET /stories/list]
        B3[GET /stories/list/{yearmonth}]
        B4[PUT /stories/story/{key}/stats/{yearmonth}]
    end

    subgraph API_CALLS["MEDIUM API CALLS"]
        M1[fetch_stats()<br/>useStatsPostNewChartDataQuery]
        M2[fetch_lifetime_stats()<br/>StatsPostFunnelQuery]
        M3[fetch_leaderboard_earnings()<br/>StoryEarningsQuery]
    end

    subgraph DATABASE["DATABASE"]
        DB1[(stories.json)]
        DB2[(stories-YYYY-MM.json)]
    end

    U1 --> B1
    B1 --> M1
    B1 --> M2
    M1 --> DB2
    M2 --> DB1

    U2 --> B2
    B2 --> DB1
    B2 --> DB2

    U3 --> B3
    B3 --> DB2
    B3 --> DB1

    U4 --> B4
    B4 --> DB2
```

---

## Sequence Diagrams

### Monthly Stats Fetch Flow

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant FastAPI
    participant MediumAPI
    participant MonthlyDB
    participant StoriesDB

    User->>Browser: Click "Fetch Stats" button
    Browser->>FastAPI: POST /fetch-story-stats/{post_id}/{yearmonth}
    
    FastAPI->>MediumAPI: fetch_stats(post_id, start_date, end_date)
    MediumAPI->>MediumAPI: Build GraphQL payload
    MediumAPI->>MediumAPI: _make_request()
    MediumAPI->>MediumAPI: POST https://medium.com/_/graphql
    MediumAPI-->>FastAPI: Return monthly stats JSON
    
    FastAPI->>MediumAPI: fetch_lifetime_stats(post_id)
    MediumAPI->>MediumAPI: Build GraphQL payload
    MediumAPI->>MediumAPI: POST https://medium.com/_/graphql
    MediumAPI-->>FastAPI: Return lifetime stats JSON
    
    FastAPI->>FastAPI: Parse both responses
    FastAPI->>MonthlyDB: update_story_monthly_stats()
    FastAPI->>StoriesDB: update_story() (lifetime stats)
    
    FastAPI-->>Browser: Return merged stats
    Browser->>User: Display updated stats
```

### Dashboard View Flow

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant FastAPI
    participant StoriesDB
    participant MonthlyDB

    User->>Browser: Open Dashboard
    Browser->>FastAPI: GET /stories/list
    
    FastAPI->>StoriesDB: get_all_stories()
    StoriesDB-->>FastAPI: Return all stories metadata
    
    FastAPI->>MonthlyDB: load_monthly_stats(current_year, current_month)
    MonthlyDB-->>FastAPI: Return current month stats
    
    FastAPI->>FastAPI: Merge metadata + monthly stats
    FastAPI->>FastAPI: Calculate leaderboard = EVER (check all months)
    FastAPI->>FastAPI: Calculate percentages
    
    FastAPI-->>Browser: Return merged JSON
    Browser->>Browser: renderStoryTable()
    Browser->>User: Display stories with stats
```

### Month View Flow

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant FastAPI
    participant MonthlyDB
    participant StoriesDB

    User->>Browser: Select month from dropdown
    Browser->>FastAPI: GET /stories/list/2026-03
    
    FastAPI->>MonthlyDB: load_monthly_stats(2026, 3)
    MonthlyDB-->>FastAPI: Return monthly file stories
    
    FastAPI->>StoriesDB: get_all_stories()
    StoriesDB-->>FastAPI: Return lifetime stats
    
    FastAPI->>FastAPI: Merge monthly stats + lifetime stats
    FastAPI->>FastAPI: Calculate leaderboard = MONTH ONLY
    
    FastAPI-->>Browser: Return merged JSON
    Browser->>Browser: renderStoryTable()
    Browser->>User: Display month-specific stats
```

### Leaderboard Toggle Flow

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant FastAPI
    participant MonthlyDB

    User->>Browser: Click trophy icon
    Browser->>Browser: Determine current mode
    
    alt Dashboard Mode
        Browser->>Browser: Use current month
    else Month Mode
        Browser->>Browser: Use selected month
    end
    
    Browser->>FastAPI: PUT /stories/story/{key}/stats/{yearmonth}
    FastAPI->>MonthlyDB: update_story_monthly_stats(key, year, month, {leaderboard: newState})
    MonthlyDB-->>FastAPI: Confirm update
    FastAPI-->>Browser: Return success
    
    Browser->>Browser: Reload current view
    Browser->>User: Display updated trophy icon
```

### Edit Modal Flow

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant FastAPI
    participant StoriesDB
    participant MonthlyDB
    participant MediumAPI

    User->>Browser: Click Edit button on story
    Browser->>FastAPI: GET /stories/story/{key} or /stories/story/{key}/{yearmonth}
    
    alt Dashboard Mode
        FastAPI->>StoriesDB: get_story(key)
        FastAPI->>MonthlyDB: get_story_monthly_stats(key, current_year, current_month)
    else Month Mode
        FastAPI->>StoriesDB: get_story(key)
        FastAPI->>MonthlyDB: get_story_monthly_stats(key, selected_year, selected_month)
    end
    
    FastAPI-->>Browser: Return story + monthly stats
    Browser->>Browser: Open edit modal, populate fields
    
    alt User clicks "Fetch from Medium"
        Browser->>FastAPI: POST /fetch-story-stats/{post_id}/{yearmonth}
        FastAPI->>MediumAPI: fetch_stats() + fetch_lifetime_stats()
        MediumAPI-->>FastAPI: Return fresh stats
        FastAPI->>MonthlyDB: update_story_monthly_stats()
        FastAPI->>StoriesDB: update_story() (lifetime)
        FastAPI-->>Browser: Return updated stats
        Browser->>Browser: Refresh modal with new data
    end
    
    User->>Browser: Click Save
    Browser->>FastAPI: PUT /stories/story/{key} (metadata)
    Browser->>FastAPI: PUT /stories/story/{key}/stats/{yearmonth} (monthly)
    FastAPI-->>Browser: Confirm save
    Browser->>Browser: Close modal, reload view
```

### Calendar Generation Flow

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant FastAPI
    participant StoriesDB
    participant CalendarService

    User->>Browser: Click Generate Calendar
    Browser->>FastAPI: POST /calendar/generate
    
    FastAPI->>StoriesDB: load_stories_data()
    StoriesDB-->>FastAPI: Return stories + series + settings
    
    FastAPI->>CalendarService: generate_calendar()
    
    loop For each unpublished story
        CalendarService->>CalendarService: Calculate next available date
        CalendarService->>CalendarService: Apply series spacing rules
        CalendarService->>CalendarService: Respect preferred publish days
    end
    
    CalendarService->>CalendarService: Save to JSON file
    CalendarService->>CalendarService: Generate Markdown file
    CalendarService-->>FastAPI: Return calendar schedule
    
    FastAPI-->>Browser: Return calendar JSON
    Browser->>Browser: renderCalendarTable()
    Browser->>User: Display schedule
```

---

## REST API Endpoints with curl Examples

### Stories Endpoints

| Method | Endpoint | Description | curl Example |
|--------|----------|-------------|--------------|
| GET | `/api/stories/list` | Dashboard view | `curl -X GET "http://localhost:8000/api/stories/list" \| jq '.'` |
| GET | `/api/stories/list/2026-03` | Month view | `curl -X GET "http://localhost:8000/api/stories/list/2026-03" \| jq '.'` |
| GET | `/api/stories/story/{key}/stats` | All monthly stats for a story | `curl -X GET "http://localhost:8000/api/stories/story/Miscellaneous/My%20Story/stats" \| jq '.'` |
| GET | `/api/stories/story/{key}/2026-03` | Story + specific month stats | `curl -X GET "http://localhost:8000/api/stories/story/Miscellaneous/My%20Story/2026-03" \| jq '.'` |
| GET | `/api/stories/story/{key}` | Story + current month stats | `curl -X GET "http://localhost:8000/api/stories/story/Miscellaneous/My%20Story" \| jq '.'` |
| PUT | `/api/stories/story/{key}` | Update story metadata | `curl -X PUT "http://localhost:8000/api/stories/story/Miscellaneous/My%20Story" -H "Content-Type: application/json" -d '{"status":"Published"}' \| jq '.'` |
| PUT | `/api/stories/story/{key}/stats/2026-03` | Update monthly stats | `curl -X PUT "http://localhost:8000/api/stories/story/Miscellaneous/My%20Story/stats/2026-03" -H "Content-Type: application/json" -d '{"member_reads":450,"claps":89}' \| jq '.'` |
| POST | `/api/stories/story` | Create new story | `curl -X POST "http://localhost:8000/api/stories/story" -H "Content-Type: application/json" -d '{"name":"New Story"}' \| jq '.'` |
| DELETE | `/api/stories/story/{key}` | Delete story | `curl -X DELETE "http://localhost:8000/api/stories/story/Miscellaneous/My%20Story" \| jq '.'` |
| POST | `/api/stories/story/{key}/publish` | Mark as published | `curl -X POST "http://localhost:8000/api/stories/story/Miscellaneous/My%20Story/publish" -d '{"medium_url":"https://..."}' \| jq '.'` |
| POST | `/api/stories/sync` | Sync filesystem | `curl -X POST "http://localhost:8000/api/stories/sync" \| jq '.'` |
| GET | `/api/stories/months` | Get available months | `curl -X GET "http://localhost:8000/api/stories/months" \| jq '.'` |
| GET | `/api/stories/leaderboard-status` | Get stories that ever had leaderboard | `curl -X GET "http://localhost:8000/api/stories/leaderboard-status" \| jq '.'` |
| POST | `/api/stories/fetch-story-stats/{post_id}/2026-03` | Fetch stats from Medium | `curl -X POST "http://localhost:8000/api/stories/fetch-story-stats/78cb972195da/2026-03" \| jq '.'` |
| POST | `/api/stories/fetch-leaderboard-stats/2026-03` | Import leaderboard data | `curl -X POST "http://localhost:8000/api/stories/fetch-leaderboard-stats/2026-03" \| jq '.'` |

### Series Endpoints

| Method | Endpoint | Description | curl Example |
|--------|----------|-------------|--------------|
| GET | `/api/series/` | List all series | `curl -X GET "http://localhost:8000/api/series/" \| jq '.'` |
| POST | `/api/series/` | Create series | `curl -X POST "http://localhost:8000/api/series/" -H "Content-Type: application/json" -d '{"name":"Python","spacing_days":7}' \| jq '.'` |
| PUT | `/api/series/Python` | Update series | `curl -X PUT "http://localhost:8000/api/series/Python" -H "Content-Type: application/json" -d '{"spacing_days":10}' \| jq '.'` |
| DELETE | `/api/series/Python` | Delete series | `curl -X DELETE "http://localhost:8000/api/series/Python" \| jq '.'` |

### Calendar Endpoints

| Method | Endpoint | Description | curl Example |
|--------|----------|-------------|--------------|
| GET | `/api/calendar/` | Get publishing calendar | `curl -X GET "http://localhost:8000/api/calendar/" \| jq '.'` |
| POST | `/api/calendar/generate` | Generate calendar | `curl -X POST "http://localhost:8000/api/calendar/generate" \| jq '.'` |

### Settings Endpoints

| Method | Endpoint | Description | curl Example |
|--------|----------|-------------|--------------|
| GET | `/api/settings/` | Get settings | `curl -X GET "http://localhost:8000/api/settings/" \| jq '.'` |
| PUT | `/api/settings/calendar` | Update calendar settings | `curl -X PUT "http://localhost:8000/api/settings/calendar" -H "Content-Type: application/json" -d '{"stories_per_week":4}' \| jq '.'` |
| GET | `/api/settings/stories-root` | Get stories root | `curl -X GET "http://localhost:8000/api/settings/stories-root" \| jq '.'` |

---

## Medium API to Database Field Mapping

```mermaid
flowchart LR
    subgraph MEDIUM["MEDIUM API RESPONSE"]
        direction TB
        P1["data.post.firstPublishedAt"]
        P2["data.post.readingTime"]
        P3["data.post.wordCount"]
        P4["data.post.title"]
        P5["data.post.creator.name"]
        P6["data.post.tags[].name"]
        P7["data.post.earnings.dailyEarnings[].amount"]
        
        B1["data.postStatsDailyBundle.buckets[].readersThatReadCount (MEMBER)"]
        B2["data.postStatsDailyBundle.buckets[].readersThatReadCount (NONMEMBER)"]
        B3["data.postStatsDailyBundle.buckets[].readersThatViewedCount (MEMBER)"]
        B4["data.postStatsDailyBundle.buckets[].readersThatViewedCount (NONMEMBER)"]
        B5["data.postStatsDailyBundle.buckets[].readersThatClappedCount"]
        B6["data.postStatsDailyBundle.buckets[].readersThatRepliedCount"]
        
        L1["data.postStatsTotalBundle.readersCount"]
        L2["data.postStatsTotalBundle.viewersCount"]
        L3["data.postStatsTotalBundle.presentationCount"]
        L4["data.postStatsTotalBundle.feedClickThroughRate"]
    end

    subgraph STORIES["stories.json"]
        direction TB
        S1["medium_first_published"]
        S2["medium_reading_time"]
        S3["word_count"]
        S4["medium_title"]
        S5["medium_author"]
        S6["medium_tags"]
        S7["lifetime_reads"]
        S8["lifetime_views"]
        S9["presentation_count"]
        S10["feed_click_through_rate"]
    end

    subgraph MONTHLY["stories-YYYY-MM.json"]
        direction TB
        M1["medium_member_reads"]
        M2["medium_nonmember_reads"]
        M3["medium_member_views"]
        M4["medium_nonmember_views"]
        M5["claps"]
        M6["responses"]
        M7["medium_earnings"]
    end

    P1 --> S1
    P2 --> S2
    P3 --> S3
    P4 --> S4
    P5 --> S5
    P6 --> S6
    P7 --> M7

    B1 --> M1
    B2 --> M2
    B3 --> M3
    B4 --> M4
    B5 --> M5
    B6 --> M6

    L1 --> S7
    L2 --> S8
    L3 --> S9
    L4 --> S10
```

---

## Database Schema

```mermaid
erDiagram
    STORIES_JSON {
        string key PK
        string name
        string series
        string status
        string published_date
        string medium_url
        string medium_first_published "API: data.post.firstPublishedAt"
        int medium_reading_time "API: data.post.readingTime"
        int word_count "API: data.post.wordCount"
        int lifetime_reads "API: readersCount"
        int lifetime_views "API: viewersCount"
        int presentation_count "API: presentationCount"
        float feed_click_through_rate "API: feedClickThroughRate"
        boolean bookmarked
        string linkedin_status
        int linkedin_impressions
    }

    MONTHLY_JSON {
        string month PK
        string story_key FK
        int medium_member_reads "API: readersThatReadCount MEMBER"
        int medium_nonmember_reads "API: readersThatReadCount NONMEMBER"
        int medium_member_views "API: readersThatViewedCount MEMBER"
        int medium_nonmember_views "API: readersThatViewedCount NONMEMBER"
        int claps "API: readersThatClappedCount"
        int responses "API: readersThatRepliedCount"
        int medium_highlights "API: readersThatHighlightedCount"
        int medium_new_followers "API: readersThatInitiallyFollowed..."
        float medium_earnings "API: sum(dailyEarnings[].amount)"
        boolean leaderboard
        int leaderboard_nanos
    }

    STORIES_JSON ||--o{ MONTHLY_JSON : "has monthly stats for"
```

### stories.json Structure

```json
{
  "version": "1.0",
  "last_updated": "2026-04-06T12:00:00",
  "stories": {
    "python/advanced-tips": {
      "name": "Advanced Python Tips",
      "series": "Python",
      "status": "Published",
      "published_date": "2026-03-15",
      "medium_url": "https://medium.com/@username/post-title-123abc",
      "medium_first_published": "2026-03-15T10:00:00Z",
      "medium_reading_time": 8,
      "word_count": 1200,
      "lifetime_reads": 5234,
      "lifetime_views": 18750,
      "presentation_count": 5,
      "feed_click_through_rate": 12.8,
      "bookmarked": false,
      "linkedin_status": "posted",
      "linkedin_impressions": 1500
    }
  }
}
```

### stories-2026-03.json Structure

```json
{
  "month": "2026-03",
  "last_updated": "2026-04-06T12:00:00",
  "stories": {
    "python/advanced-tips": {
      "medium_member_reads": 300,
      "medium_nonmember_reads": 200,
      "medium_member_views": 800,
      "medium_nonmember_views": 500,
      "claps": 45,
      "responses": 8,
      "medium_highlights": 12,
      "medium_new_followers": 3,
      "medium_earnings": 12.50,
      "leaderboard": true,
      "leaderboard_nanos": 1250000000
    }
  }
}
```

---

## Service Layer Methods

```mermaid
flowchart TD
    subgraph MAS["MediumAPIService (medium_api_service.py)"]
        M1["fetch_stats(post_id, start_date, end_date)<br/>✅ Makes HTTP call to Medium GraphQL"]
        M2["fetch_lifetime_stats(post_id)<br/>✅ Makes HTTP call to Medium GraphQL"]
        M3["fetch_leaderboard_earnings(username, year, month)<br/>✅ Makes HTTP call to Medium GraphQL"]
        M4["extract_post_id_from_url(medium_url)<br/>❌ No HTTP call"]
        M5["is_authenticated()<br/>❌ No HTTP call"]
        M6["parse_stats_response(data, post_id)<br/>❌ No HTTP call"]
        M7["parse_lifetime_response(data, post_id)<br/>❌ No HTTP call"]
    end

    subgraph MSS["MonthlyStorageService (monthly_storage_service.py)"]
        MS1["load_monthly_stats(year, month)"]
        MS2["save_monthly_stats(year, month, data)"]
        MS3["get_story_monthly_stats(story_key, year, month)"]
        MS4["update_story_monthly_stats(story_key, year, month, stats_data, title)"]
        MS5["get_available_months()"]
        MS6["get_months_for_story(story_key)"]
    end

    subgraph SS["StoryService (story_service.py)"]
        SS1["get_all_stories()"]
        SS2["get_story(story_key)"]
        SS3["create_story(story_data)"]
        SS4["update_story(story_key, update_data)"]
        SS5["delete_story(story_key)"]
        SS6["publish_story(story_key, medium_url)"]
        SS7["sync_with_filesystem()"]
    end

    subgraph CS["CalendarService (calendar_service.py)"]
        CS1["generate_calendar()"]
        CS2["save_calendar_files()"]
    end
```

---

## Total Medium API Calls per Operation

```mermaid
flowchart TD
    subgraph OPERATIONS["User Operations"]
        O1["Fetch stats for 1 story"]
        O2["Fetch leaderboard for a month"]
        O3["Update all leaderboard stories"]
        O4["View dashboard"]
        O5["View month view"]
    end

    subgraph CALLS["Medium API Calls"]
        C1["2 calls<br/>(1 monthly + 1 lifetime)"]
        C2["1 call<br/>(1 leaderboard query)"]
        C3["2 × N stories<br/>(N = number of leaderboard stories)"]
        C4["0 calls<br/>(uses cached data)"]
        C5["0 calls<br/>(uses cached monthly files)"]
    end

    O1 --> C1
    O2 --> C2
    O3 --> C3
    O4 --> C4
    O5 --> C5
```

| Operation | API Calls | Details |
|-----------|-----------|---------|
| Fetch stats for 1 story | **2** | 1 monthly + 1 lifetime |
| Fetch leaderboard for a month | **1** | 1 leaderboard query |
| Update all leaderboard stories | **2 × N** | N = number of leaderboard stories |
| View dashboard | **0** | Uses cached database data |
| View month view | **0** | Uses cached monthly files |

---

## Medium API Details

### GraphQL Endpoint
```
POST https://medium.com/_/graphql
```

### API Call 1: Monthly Stats

| Property | Value |
|----------|-------|
| **Operation Name** | `useStatsPostNewChartDataQuery` |
| **Purpose** | Fetch daily breakdown of stats for a specific month |
| **Input Parameters** | `postId`, `startAt`, `endAt` |
| **Method in Code** | `MediumAPIService.fetch_stats()` |
| **Rate Limit** | 0.5 second delay between calls |

**curl Example:**
```bash
# This is called internally by the backend, not directly
curl -X POST "http://localhost:8000/api/stories/fetch-story-stats/78cb972195da/2026-03"
```

### API Call 2: Lifetime Stats

| Property | Value |
|----------|-------|
| **Operation Name** | `StatsPostFunnelQuery` |
| **Purpose** | Fetch lifetime aggregate stats for a story |
| **Input Parameters** | `postId` |
| **Method in Code** | `MediumAPIService.fetch_lifetime_stats()` |
| **Rate Limit** | 0.5 second delay between calls |

### API Call 3: Leaderboard Earnings

| Property | Value |
|----------|-------|
| **Operation Name** | `StoryEarningsQuery` |
| **Purpose** | Fetch monthly earnings for leaderboard |
| **Input Parameters** | `username`, `startAt`, `endAt`, `first`, `after` |
| **Method in Code** | `MediumAPIService.fetch_leaderboard_earnings()` |
| **Rate Limit** | 0.5 second delay between calls |

**curl Example:**
```bash
curl -X POST "http://localhost:8000/api/stories/fetch-leaderboard-stats/2026-03"
```

---

## Debug Mode

Enable debug mode to see pretty-printed API requests/responses in console:

```bash
export MEDIUM_API_DEBUG=true
uvicorn app.main:app --reload
```

Or in Python:
```python
from app.services.medium_api_service import set_debug_mode
set_debug_mode(True)
```

**Debug output includes:**
- Request headers and payloads
- Response bodies (full JSON)
- Parsed summaries for monthly and lifetime stats
- Extracted post IDs from URLs
- Daily breakdown for monthly stats

---

## Field Source Summary

| Database Field | Source |
|----------------|--------|
| `medium_first_published` | API: `data.post.firstPublishedAt` |
| `medium_reading_time` | API: `data.post.readingTime` |
| `word_count` | API: `data.post.wordCount` |
| `medium_title` | API: `data.post.title` |
| `medium_author` | API: `data.post.creator.name` |
| `medium_tags` | API: `data.post.tags[].name` |
| `medium_member_reads` | API: `readersThatReadCount` (MEMBER) |
| `medium_member_views` | API: `readersThatViewedCount` (MEMBER) |
| `medium_nonmember_reads` | API: `readersThatReadCount` (NONMEMBER) |
| `medium_nonmember_views` | API: `readersThatViewedCount` (NONMEMBER) |
| `claps` | API: `readersThatClappedCount` |
| `responses` | API: `readersThatRepliedCount` |
| `medium_highlights` | API: `readersThatHighlightedCount` |
| `medium_new_followers` | API: `readersThatInitiallyFollowedAuthorFromThisPostCount` |
| `medium_earnings` | API: `sum(data.post.earnings.dailyEarnings[].amount)` |
| `lifetime_reads` | API: `data.postStatsTotalBundle.readersCount` |
| `lifetime_views` | API: `data.postStatsTotalBundle.viewersCount` |
| `presentation_count` | API: `data.postStatsTotalBundle.presentationCount` |
| `feed_click_through_rate` | API: `data.postStatsTotalBundle.feedClickThroughRate` |
| `bookmarks` | API: `data.post.distribution.totalBookmarkCount` |
| `leaderboard` | User input (UI toggle) |
| `leaderboard_nanos` | User input |
| `linkedin_*` | User input |
| `bookmarked` | User input |
| `status` | User input |
| `series` | User input |
| `tags` | User input |
| `notes` | User input |