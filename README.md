# Story Manager - Technical Content Management System

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

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
| ⭐ **Bookmarking** | Mark important stories and filter by bookmarked status |
| 📈 **Analytics Dashboard** | View total reads, claps, impressions, and performance metrics |
| ⚙️ **Configurable Settings** | Set series spacing, stories per week, preferred publishing days |
| 🎨 **Web Dashboard** | Clean Bootstrap-based UI with sidebar navigation and real-time updates |
| 🔌 **REST API** | Full CRUD operations with OpenAPI documentation |
| 🐳 **Docker Support** | Development with hot reload and production-ready containers |
| 🔒 **Filter Persistence** | Maintains filters across page refreshes and actions |
| 📊 **Sorting** | Sort stories by any column with visual indicators |
| 🚀 **CI/CD Pipeline** | Automated testing, building, and deployment with GitHub Actions |

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

### LinkedIn Tracking Flow

```mermaid
flowchart LR
    subgraph "User Actions"
        A[Click LinkedIn Icon]
        B[Click Schedule Icon]
        C[Click Not Posted Icon]
        D[Clear All LinkedIn Data]
    end
    
    subgraph "UI Layer"
        E[Update UI Fields]
        F[Update Display]
    end
    
    subgraph "API Layer"
        G[PUT /api/stories/{key}]
    end
    
    subgraph "Service Layer"
        H[update_story]
        I[Save to JSON]
    end
    
    A --> E
    B --> E
    C --> E
    D --> E
    E --> F
    E --> G
    G --> H
    H --> I
    I --> F
```

### CI/CD Pipeline Architecture

```mermaid
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

### Project Structure

```mermaid
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
    A --> K[.github/]
    
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
    
    K --> K1[workflows/]
    K1 --> K1a[ci.yml]
    K1 --> K1b[cd.yml]
    K1 --> K1c[docker-build.yml]
    K1 --> K1d[release.yml]
```

### Technology Stack

```mermaid
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

### Database Schema

```mermaid
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
        boolean bookmarked
        string notes
        date last_updated
        date last_stats_update
    }
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
PREFERRED_PUBLISH_DAYS='["Monday","Tuesday","Wednesday","Thursday"]'

# Medium Stats (optional - for authenticated stats)
# MEDIUM_SID="your_medium_sid_cookie"
# MEDIUM_UID="your_medium_uid_cookie"
```

---

## Usage

### Dashboard Navigation

```mermaid
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
        E --> L[Bookmark Stories]
        
        M[Series] --> N[List All Series]
        M --> O[Add Series]
        M --> P[Set Spacing]
        
        Q[Calendar] --> R[View Schedule]
        Q --> S[Regenerate Calendar]
        Q --> T[Quick Publish]
        
        U[Settings] --> V[Configure Spacing]
        U --> W[Set Cadence]
        U --> X[Sync Filesystem]
    end
```

### Story Management

**Stories Table Features:**
- Filter by status (Draft, Done, Ready, Published)
- Filter by series
- Filter by bookmarked
- Search by story name
- Sort by any column (click column header)
- Click any row to edit
- Quick actions: Publish, LinkedIn status, Stats Dashboard, Bookmark, Delete

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
- Click "Clear All LinkedIn Data" button to reset all LinkedIn fields

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
| GET | `/api/stories/debug/keys` | Debug: list all story keys |

---

## Docker Deployment

### Dockerfile

```dockerfile
# Development Stage
FROM python:3.11-slim AS development
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends gcc curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production Stage
FROM python:3.11-slim AS production
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .
RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  story-manager-dev:
    build:
      context: .
      target: development
    container_name: story-manager-dev
    ports:
      - "8000:8000"
    volumes:
      - ./app:/app/app
      - ./static:/app/static
      - ./config.py:/app/config.py
      - ./run.py:/app/run.py
      - ${STORIES_ROOT:-./stories}:/app/stories
      - story-manager-data:/app/data
    environment:
      - DEBUG=true
      - STORIES_ROOT=/app/stories
    env_file:
      - .env
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    restart: unless-stopped

  story-manager-prod:
    build:
      context: .
      target: production
    container_name: story-manager-prod
    ports:
      - "8000:8000"
    volumes:
      - ${STORIES_ROOT:-./stories}:/app/stories
      - story-manager-data:/app/data
    environment:
      - DEBUG=false
      - STORIES_ROOT=/app/stories
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  story-manager-data:
    driver: local
```

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

### GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push, PR | Lint, test, security scan |
| `docker-build.yml` | Push, Tag | Build and push Docker images |
| `cd.yml` | Main, Tag | Deploy to staging/production |
| `release.yml` | Tag | Create GitHub Release |

### Continuous Integration (`ci.yml`)

```yaml
name: CI - Continuous Integration

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -r requirements.txt pytest pytest-cov flake8 black mypy
      - run: flake8 app/ --count --statistics
      - run: black --check app/ --line-length 100
      - run: pytest tests/ -v --cov=app --cov-report=xml
      - uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          format: 'sarif'
      - uses: github/codeql-action/upload-sarif@v3
```

### Docker Build & Publish (`docker-build.yml`)

```yaml
name: Docker Build & Publish

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/metadata-action@v5
        id: meta
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=sha,format=short
      - uses: docker/build-push-action@v5
        with:
          context: .
          target: production
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### Continuous Deployment (`cd.yml`)

```yaml
name: CD - Continuous Deployment

on:
  push:
    branches: [ main ]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment'
        required: true
        default: 'staging'

env:
  DOCKER_IMAGE: ghcr.io/${{ github.repository }}

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USERNAME }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          script: |
            docker pull ${{ env.DOCKER_IMAGE }}:latest
            docker-compose -f docker-compose.staging.yml down
            docker-compose -f docker-compose.staging.yml up -d
      - run: curl -f https://staging.yourdomain.com/health

  deploy-production:
    runs-on: ubuntu-latest
    needs: deploy-staging
    if: startsWith(github.ref, 'refs/tags/v')
    environment: production
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.PRODUCTION_USERNAME }}
          key: ${{ secrets.PRODUCTION_SSH_KEY }}
          script: |
            VERSION=${GITHUB_REF#refs/tags/}
            docker pull ${{ env.DOCKER_IMAGE }}:$VERSION
            docker tag ${{ env.DOCKER_IMAGE }}:$VERSION ${{ env.DOCKER_IMAGE }}:production
            docker-compose -f docker-compose.production.yml down
            docker-compose -f docker-compose.production.yml up -d
      - run: curl -f https://yourdomain.com/health
```

### Release Workflow (`release.yml`)

```yaml
name: Release - Create Release

on:
  push:
    tags: [ 'v*' ]

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: orhun/git-cliff-action@v2
        with:
          config: cliff.toml
          args: --verbose
        env:
          OUTPUT: CHANGELOG.md
      - uses: softprops/action-gh-release@v1
        with:
          body_path: CHANGELOG.md
          files: |
            README.md
            CHANGELOG.md
```

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
| Bookmark not saving | Ensure the field exists in stories.json (added automatically) |

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

# List all story keys
curl "http://localhost:8000/api/stories/debug/keys" | python -m json.tool

# Find story by search term
curl "http://localhost:8000/api/stories/debug/find/github" | python -m json.tool
```

---

## Requirements

### Python Dependencies

```txt
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

Built for technical writers who manage large content libraries across multiple series and platforms. Special thanks to the FastAPI, Bootstrap, Docker, and GitHub Actions communities.

---

*Last updated: 2026-03-29*
