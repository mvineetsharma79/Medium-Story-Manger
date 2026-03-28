# Story Manager - Technical Content Management System

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

A professional content management system for technical writers and developers to manage stories, series, publishing schedules, and track performance metrics. Built with FastAPI and designed for writers with large content libraries.

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Data Management](#data-management)
- [API Documentation](#api-documentation)
- [Docker Deployment](#docker-deployment)
- [CI/CD Pipeline](#cicd-pipeline)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

| Feature | Description |
|---------|-------------|
| 📚 **Story Management** | Create, read, update, delete, and publish stories with full metadata |
| 📁 **Series Organization** | Group stories into series with configurable spacing between parts |
| 📅 **Publishing Calendar** | Auto-generate optimized publishing schedules based on series spacing and weekly cadence |
| 🔄 **Filesystem Sync** | Automatically discover new markdown files and sync with JSON database (never deletes) |
| 📊 **Medium Stats** | Fetch story statistics (claps, responses, reading time, tags) from Medium |
| 🔗 **LinkedIn Tracking** | Track LinkedIn post status, timestamp, impressions, and URL for each story |
| ⚙️ **Configurable Settings** | Set series spacing, stories per week, preferred publishing days |
| 🎨 **Web Dashboard** | Clean Bootstrap-based UI with sidebar navigation and real-time updates |
| 🔌 **REST API** | Full CRUD operations with OpenAPI documentation |
| 🐳 **Docker Support** | Development with hot reload and production-ready containers |
| 🔒 **Filter Persistence** | Maintains filters across page refreshes and actions |

---

## Quick Start

### Docker (Fastest)

```bash
# Clone the repository
git clone https://github.com/yourusername/story-manager.git
cd story-manager

# Copy environment configuration
cp .env.example .env

# Edit .env with your stories directory path
# STORIES_ROOT=/path/to/your/stories

# Start the application
docker-compose up story-manager-dev

# Open browser to http://localhost:8000
```

### Local Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env

# Run the application
python run.py
```

---

## Architecture

### System Architecture Diagram

```mermaid
---
config:
  theme: base
  layout: elk
---
graph TB
    subgraph "Client Layer"
        A[Web Browser]
        B[REST API Client]
    end

    subgraph "Presentation Layer"
        C[FastAPI Application]
        D[Jinja2 Templates]
        E[Static Files]
    end

    subgraph "Business Logic Layer"
        F[Story Service]
        G[Series Service]
        H[Calendar Service]
        I[Stats Service]
    end

    subgraph "Data Access Layer"
        J[File Service]
        K[JSON Storage]
        L[Markdown Files]
    end

    subgraph "External Services"
        M[Medium.com]
        N[LinkedIn API]
    end

    A --> C
    B --> C
    C --> D
    C --> E
    C --> F
    C --> G
    C --> H
    C --> I
    
    F --> J
    G --> J
    H --> J
    I --> J
    
    J --> K
    J --> L
    
    I --> M
    F --> N
```

### Docker Container Architecture

```mermaid
---
config:
  theme: base
  layout: elk
---
graph TB
    subgraph "Docker Host"
        subgraph "Development Container"
            A[uvicorn --reload]
            B[Mounted Source Code]
            C[Mounted Stories Directory]
        end
        
        subgraph "Production Container"
            D[gunicorn]
            E[uvicorn workers]
            F[Static Files]
        end
        
        subgraph "Optional Services"
            G[nginx Proxy]
            H[Auto-heal]
        end
        
        subgraph "Persistent Volumes"
            I[stories.json]
            J[calendar.json]
            K[User Stories]
        end
    end
    
    A --> B
    A --> C
    D --> E
    D --> F
    G --> D
    H --> D
    
    C -.-> K
    D -.-> I
    D -.-> J
```

### Data Flow Diagram

```mermaid
---
config:
  theme: base
  layout: elk
---
sequenceDiagram
    participant User
    participant Dashboard
    participant API
    participant StoryService
    participant FileService
    participant JSON
    participant Filesystem

    User->>Dashboard: Click "Sync Stories"
    Dashboard->>API: POST /api/stories/sync
    API->>StoryService: sync_with_filesystem()
    StoryService->>FileService: scan_markdown_files()
    FileService->>Filesystem: Read directory structure
    Filesystem-->>FileService: Return markdown files
    FileService-->>StoryService: List of discovered files
    StoryService->>JSON: Load existing stories.json
    StoryService->>StoryService: Compare and merge (ADD/UPDATE only)
    StoryService->>JSON: Save updated stories.json
    StoryService-->>API: Return sync results
    API-->>Dashboard: Updated story list
    Dashboard-->>User: Display stories
```

### Publishing Calendar Generation

```mermaid
---
config:
  theme: base
  layout: elk
---
flowchart TD
    A[Start Calendar Generation] --> B[Load stories.json]
    B --> C[Filter Unpublished Stories]
    C --> D[Group by Series]
    D --> E[Sort by Part Number]
    
    E --> F{Series Spacing?}
    F -->|Custom| G[Use Series Spacing]
    F -->|Default| H[Use Global Spacing]
    
    G --> I[Check Last Published Date]
    H --> I
    
    I --> J[Calculate Next Available Date]
    J --> K{Within Weekly Cadence?}
    
    K -->|Yes| L[Schedule Story]
    K -->|No| M[Move to Next Week]
    
    M --> J
    
    L --> N{More Stories?}
    N -->|Yes| E
    N -->|No| O[Generate Calendar Output]
    
    O --> P[Save calendar.json]
    O --> Q[Save calendar.md]
    O --> R[Return to API]
```

### Medium Stats Flow

```mermaid
flowchart LR
    subgraph "User Action"
        A[Click Stats Button]
        B[Click Sync All Stats]
    end
    
    subgraph "API Layer"
        C[/stats-by-url/]
        D[/sync-stats/]
        E[/{key}/sync-stats/]
    end
    
    subgraph "Service Layer"
        F[MediumStatsService]
        G[Get Story by URL]
        H[Fetch from Medium]
    end
    
    subgraph "Data Sources"
        I[Medium.com Page]
        J[Medium RSS Feed]
        K[Medium GraphQL]
    end
    
    subgraph "Storage"
        L[stories.json]
    end
    
    A --> C
    B --> D
    C --> G
    D --> F
    E --> F
    F --> H
    H --> I
    H --> J
    H --> K
    F --> L
```

### Project Structure

```mermaid
---
config:
  theme: base
  layout: elk
---
graph TD
    A[story-manager/] --> B[app/]
    A --> C[tests/]
    A --> D[data/]
    A --> E[stories/]
    A --> F[config.py]
    A --> G[Dockerfile]
    A --> H[docker-compose.yml]
    A --> I[requirements.txt]
    A --> J[README.md]
    
    B --> B1[main.py]
    B --> B2[models.py]
    B --> B3[templates/]
    B --> B4[routers/]
    B --> B5[services/]
    
    B3 --> B3a[index.html]
    
    B4 --> B4a[stories.py]
    B4 --> B4b[series.py]
    B4 --> B4c[calendar.py]
    B4 --> B4d[settings.py]
    
    B5 --> B5a[story_service.py]
    B5 --> B5b[calendar_service.py]
    B5 --> B5c[file_service.py]
    B5 --> B5d[medium_stats_service.py]
    
    D --> D1[stories.json]
    D --> D2[publishing-calendar.json]
    D --> D3[publishing-calendar.md]
    
    E --> E1[Series Folder 1/]
    E --> E2[Series Folder 2/]
    E --> E3[Standalone Stories/]
```

### Technology Stack

```mermaid
---
config:
  theme: base
  layout: elk
---
graph LR
    subgraph "Frontend"
        A[HTML5]
        B[Bootstrap 5]
        C[JavaScript]
        D[Mermaid.js]
    end
    
    subgraph "Backend"
        E[FastAPI]
        F[Python 3.11]
        G[Pydantic]
        H[Jinja2]
    end
    
    subgraph "Data"
        I[JSON]
        J[Markdown]
        K[File System]
    end
    
    subgraph "External APIs"
        L[Medium Scraping]
        M[Medium RSS]
        N[Medium GraphQL]
    end
    
    subgraph "Infrastructure"
        O[Docker]
        P[GitHub Actions]
        Q[GHCR]
    end
    
    A --> E
    B --> A
    C --> A
    D --> C
    
    E --> F
    E --> G
    E --> H
    
    E --> I
    E --> J
    E --> K
    
    E --> L
    E --> M
    E --> N
    
    O --> E
    P --> O
    Q --> P
```

---

## Installation

### Prerequisites

- Python 3.9 or higher
- pip
- Git (optional)
- Docker (optional)

### Docker Installation (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/story-manager.git
cd story-manager

# 2. Create environment configuration
cp .env.example .env

# 3. Edit .env with your stories directory path
#    STORIES_ROOT=/absolute/path/to/your/stories

# 4. Create stories directory if needed
mkdir -p /path/to/your/stories

# 5. Start the application
docker-compose up story-manager-dev

# 6. Open browser to http://localhost:8000
```

### Local Development Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/story-manager.git
cd story-manager

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Copy and configure environment
cp .env.example .env

# 5. Run the application
python run.py
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | "Story Manager" | Application display name |
| `DEBUG` | false | Enable debug mode (auto-reload) |
| `STORIES_ROOT` | "./stories" | Path to stories directory |
| `DATA_DIR` | "./data" | Directory for JSON data files |
| `DEFAULT_SERIES_SPACING_DAYS` | 7 | Default days between series parts |
| `DEFAULT_STORIES_PER_WEEK` | 3 | Maximum stories per week |
| `PREFERRED_PUBLISH_DAYS` | ["Monday","Tuesday","Wednesday","Thursday"] | Preferred days to publish |
| `MEDIUM_SID` | (optional) | Medium session cookie for stats |
| `MEDIUM_UID` | (optional) | Medium user ID cookie for stats |

### `.env.example`

```bash
# Application Settings
APP_NAME="Story Manager"
DEBUG=true

# Stories Directory
STORIES_ROOT="./stories"

# Data Directory
DATA_DIR="./data"

# Publishing Calendar Settings
DEFAULT_SERIES_SPACING_DAYS=7
DEFAULT_STORIES_PER_WEEK=3
PREFERRED_PUBLISH_DAYS='["Monday", "Tuesday", "Wednesday", "Thursday"]'

# Medium Stats (optional - for authenticated stats)
# MEDIUM_SID="your_medium_sid_cookie"
# MEDIUM_UID="your_medium_uid_cookie"
```

---

## Usage

### Dashboard Navigation

```mermaid
---
config:
  theme: base
  layout: elk
---
graph TD
    subgraph "Dashboard Navigation"
        A[Dashboard] --> B[Overview Stats]
        A --> C[Recent Stories]
        A --> D[Upcoming Schedule]
        
        E[Stories] --> F[List All Stories]
        E --> G[Add Story]
        E --> H[Edit Story]
        E --> I[Publish Story]
        E --> J[Stats Dashboard]
        E --> K[LinkedIn Quick Actions]
        
        L[Series] --> M[List All Series]
        L --> N[Add Series]
        L --> O[Set Spacing]
        
        P[Calendar] --> Q[View Schedule]
        P --> R[Regenerate Calendar]
        P --> S[Quick Publish]
        
        T[Settings] --> U[Configure Spacing]
        T --> V[Set Cadence]
        T --> W[Sync Filesystem]
    end
```

### Story Management

**Stories Table Features:**
- Filter by status (Draft, Done, Ready, Published)
- Filter by series
- Search by story name
- Click any row to edit
- Quick actions: Publish, LinkedIn status, Stats Dashboard, Delete

**Edit Story Modal:**
- Status: Draft, Done, Ready, Published
- Created/Published dates (editable with "Today" button)
- Read time, Medium reads
- Tags
- Medium URL (required for stats)
- LinkedIn marketing: Status, timestamp, impressions, URL
- Notes

### LinkedIn Status Tracking

| Status | Icon | Description |
|--------|------|-------------|
| Not Posted | ❌ | Story not yet shared on LinkedIn |
| Scheduled | 📅 | Planned post with timestamp |
| Posted | ✅ | Shared with timestamp and optional URL |

**Quick Actions:**
- Click LinkedIn icon to mark as Posted
- Click Calendar icon to mark as Scheduled
- Click X-circle icon to clear status

### Medium Stats Dashboard

Fetches publicly available statistics from Medium:

| Stat | Availability |
|------|--------------|
| Claps | ✅ Always available |
| Responses | ✅ Always available |
| Reading time | ✅ Always available |
| Word count | ✅ Available in page source |
| Tags | ✅ Available |
| Title/Subtitle | ✅ Always available |
| Author | ✅ Always available |
| Publication | ✅ Available |
| Reads | ❌ Requires Partner Program |
| View counts | ❌ Requires Partner Program |

**To fetch stats:**
1. Add Medium URL to a story in edit mode
2. Click the stats button (graph icon) in stories table
3. Use "Refresh Stats" to fetch latest data
4. Use "Sync All Stats" to update all stories at once

### Publishing Calendar

The calendar generator automatically schedules unpublished stories based on:

1. **Series spacing** - Ensures adequate time between parts of the same series (5-14 days)
2. **Weekly cadence** - Limits stories per week (1-7)
3. **Preferred days** - Schedules on your chosen publishing days
4. **Part ordering** - Respects story order within series

---

## Data Management

### Story File Structure

Stories are markdown files organized in folders by series:

```
stories/
├── AI Engineering/
│   ├── AI Agent Engineering 1 - Foundation.md
│   ├── AI Agent Engineering 2 - Building Your First Agent.md
│   └── ...
├── SOLID Principles/
│   ├── SOLID Principles Part 1 - Single Responsibility.md
│   ├── SOLID Principles Part 2 - Open-Closed.md
│   └── ...
├── GitHub Copilot/
│   └── GitHub Copilot The AI-Powered Development Ecosystem.md
└── standalone-story.md
```

### Data Storage

| File | Purpose |
|------|---------|
| `data/stories.json` | Source of truth - all story metadata |
| `data/publishing-calendar.json` | Generated calendar data |
| `data/publishing-calendar.md` | Human-readable calendar |

### Sync Behavior

The sync operation:
- ✅ **Adds** new stories discovered in the `STORIES_ROOT` directory
- ✅ **Updates** file metadata for existing stories (path, name, folder)
- ❌ **Never deletes** stories from the database (preserves all your data even if source files are removed)

### Database Schema

```mermaid
---
config:
  theme: base
  layout: elk
---
erDiagram
    SERIES ||--o{ STORY : contains
    SERIES {
        string name
        int total_stories
        int published
        int spacing_days
        array stories
    }
    STORY {
        string key
        string name
        string folder
        string series
        string status
        date published_date
        date created_date
        array tags
        int read_time
        int reads
        int claps
        int responses
        int bookmarks
        int view_count
        string medium_url
        string linkedin_status
        string linkedin_timestamp
        int linkedin_impressions
        string linkedin_url
        string notes
        date last_updated
        date last_stats_update
    }
```

---

## API Documentation

Once running, interactive API documentation is available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/stories/sync` | Sync with filesystem |
| GET | `/api/stories/` | List all stories |
| GET | `/api/stories/{key}` | Get a specific story |
| POST | `/api/stories/` | Create a new story |
| PUT | `/api/stories/{key}` | Update a story |
| POST | `/api/stories/{key}/publish` | Mark as published |
| DELETE | `/api/stories/{key}` | Delete a story |
| GET | `/api/series/` | List all series |
| POST | `/api/series/` | Create a series |
| PUT | `/api/series/{name}` | Update a series |
| DELETE | `/api/series/{name}` | Delete a series |
| GET | `/api/calendar/` | Get publishing calendar |
| POST | `/api/calendar/generate` | Generate calendar |
| GET | `/api/stories/stats-by-url` | Get Medium stats by URL |
| POST | `/api/stories/sync-stats` | Sync all Medium stats |
| POST | `/api/stories/{key}/sync-stats` | Sync stats for a single story |
| GET | `/api/stories/debug/all` | Debug: list all stories |
| GET | `/api/stories/debug/urls` | Debug: list all URLs |

---

## Docker Deployment

### Docker Commands

| Command | Description |
|---------|-------------|
| `docker-compose up` | Start containers (foreground) |
| `docker-compose up -d` | Start containers (background) |
| `docker-compose down` | Stop and remove containers |
| `docker-compose logs -f` | View live logs |
| `docker-compose exec story-manager-dev /bin/bash` | Open shell in container |
| `docker-compose build` | Rebuild images |
| `docker-compose down -v` | Remove containers and volumes |

### Production Deployment

```bash
# Build and start production containers
docker-compose up story-manager-prod -d

# With Nginx reverse proxy
docker-compose --profile with-nginx up -d
```

### Backup and Restore

```bash
# Backup JSON data
docker run --rm \
  -v story-manager-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/story-manager-backup.tar.gz -C /data .

# Restore from backup
docker run --rm \
  -v story-manager-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/story-manager-backup.tar.gz -C /data
```

---

## CI/CD Pipeline

```mermaid
---
config:
  theme: base
  layout: elk
---
graph LR
    subgraph "Trigger"
        A[Push to main]
        B[Pull Request]
        C[Tag v*]
    end
    
    subgraph "CI Pipeline"
        D[Lint & Format]
        E[Security Scan]
        F[Run Tests]
        G[Build Docker]
    end
    
    subgraph "Build Pipeline"
        H[Build Dev Image]
        I[Build Prod Image]
        J[Push to GHCR]
    end
    
    subgraph "CD Pipeline"
        K[Deploy to Staging]
        L[Health Check]
        M[Manual Approval]
        N[Deploy to Production]
    end
    
    subgraph "Release"
        O[Create Release]
        P[Generate Changelog]
        Q[Update Tags]
    end
    
    A --> D
    B --> D
    C --> O
    
    D --> E
    E --> F
    F --> G
    
    G --> H
    H --> I
    I --> J
    
    J --> K
    K --> L
    L --> M
    M --> N
    
    O --> P
    P --> Q
```

### GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push, PR | Lint, test, security scan |
| `docker-build.yml` | Push, Tag | Build and push Docker images |
| `cd.yml` | Main, Tag | Deploy to staging/production |
| `release.yml` | Tag | Create GitHub Release |

---

## Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| Port already in use | Change port in `run.py` or `docker-compose.yml` |
| Stories not found | Check `STORIES_ROOT` in `.env` and ensure directory exists |
| Medium stats not working | Add Medium URL to story first; ensure story is public |
| LinkedIn clear not working | Use the "Clear All LinkedIn Data" button in edit modal |
| Division by zero error | Stories with 0 reads will show 0 in performance metrics |
| Sync not updating | Check file permissions on stories directory |

### View Logs

```bash
# Docker logs
docker-compose logs -f story-manager-dev

# Local logs
python run.py
```

### Debug Endpoints

```bash
# List all stories
curl "http://localhost:8000/api/stories/debug/all" | python -m json.tool

# List all stories with Medium URLs
curl "http://localhost:8000/api/stories/debug/urls" | python -m json.tool

# Find story by search term
curl "http://localhost:8000/api/stories/debug/find/github" | python -m json.tool
```

---

## Requirements

- Python 3.9+
- pip
- Docker (optional)

### Python Dependencies

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
jinja2==3.1.4
python-multipart==0.0.20
pydantic==2.10.3
pydantic-settings==2.6.0
aiofiles==24.1.0
python-dotenv==1.0.1
aiohttp==3.9.5
beautifulsoup4==4.12.3
lxml==5.2.1
```

---

## License

MIT License - Use freely for personal and commercial projects.

---

## Acknowledgments

Built for technical writers who manage large content libraries across multiple series and platforms. Special thanks to the FastAPI, Bootstrap, and Docker communities.
