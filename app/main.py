from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import jinja2
import logging
from contextlib import asynccontextmanager

from app.services.medium_api_service import get_medium_api_service
from app.routers import dashboard, stories, series, calendar, settings as settings_router, monthly
from config import settings
from app.services.file_service import get_stories_root

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting Story Manager API...")
    
    # Initialize Medium API service (cookies will be loaded)
    api_service = get_medium_api_service()
    if api_service.is_authenticated():
        logger.info("✅ Medium API authenticated")
    else:
        logger.warning("⚠️ Medium API not authenticated - stats fetching will be limited")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Story Manager API...")


# Create FastAPI app
app = FastAPI(
    title="Story Manager API",
    description="""
    Story Manager API for managing Medium blog posts, series, publishing calendar, and statistics.
    
    ## Features
    
    - **Stories**: CRUD operations for blog posts with Medium API integration
    - **Series**: Manage blog series with custom spacing
    - **Calendar**: Auto-generate publishing schedule based on series spacing
    - **Dashboard**: Real-time statistics and analytics
    - **Monthly Stats**: Track performance metrics per month
    - **Leaderboard**: Track top-performing stories
    
    ## Authentication
    
    The Medium API requires authentication via cookies. Cookies are automatically
    extracted from Chrome browser or can be set via environment variables:
    - `MEDIUM_SID` and `MEDIUM_UID` - Individual cookie values
    - `MEDIUM_COOKIE` - Full cookie string
    """,
    version="2.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Mount stories folder for image access
stories_root = get_stories_root()
app.mount("/static/stories", StaticFiles(directory=str(stories_root)), name="stories")
app.mount("/sp", StaticFiles(directory="../stories", html=True), name="sp")

# Configure templates with multiple directories
templates = Jinja2Templates(directory="app/templates")
templates.env.loader = jinja2.FileSystemLoader([
    Path("app/templates"),
    Path("app/templates/modals"),
    Path("app/templates/components")
])

# ============================================
# INCLUDE ROUTERS
# ============================================

app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(stories.router, prefix="/api/stories", tags=["stories"])
app.include_router(series.router, prefix="/api/series", tags=["series"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["settings"])
app.include_router(monthly.router, prefix="/api/monthly", tags=["monthly"])

# ============================================
# PAGE ROUTES
# ============================================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - redirects to dashboard"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/stories", response_class=HTMLResponse)
async def stories_page(request: Request):
    """Stories listing page"""
    return templates.TemplateResponse("stories.html", {"request": request})


@app.get("/series", response_class=HTMLResponse)
async def series_page(request: Request):
    """Series management page"""
    return templates.TemplateResponse("series.html", {"request": request})


@app.get("/calendar", response_class=HTMLResponse)
async def calendar_page(request: Request):
    """Publishing calendar page"""
    return templates.TemplateResponse("calendar.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page"""
    return templates.TemplateResponse("settings.html", {"request": request})


# ============================================
# SERVE IMAGES FOR PREVIEW - MUST BE BEFORE story-preview route
# ============================================
@app.get("/story-preview/images/{filename:path}")
async def serve_preview_image(filename: str):
    """Serve images from stories folder for preview page"""
    from pathlib import Path
    
    stories_root = get_stories_root()
    
    # Try to find the image in different locations
    possible_paths = [
        stories_root / "images" / filename,
        stories_root / filename,
    ]
    
    for path in possible_paths:
        if path.exists() and path.is_file():
            logger.info(f"Serving image: {path}")
            return FileResponse(path)
    
    # Search recursively in stories folder
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp', '*.svg']:
        for found_file in stories_root.rglob(ext):
            if found_file.name == Path(filename).name:
                logger.info(f"Serving image from recursive search: {found_file}")
                return FileResponse(found_file)
    
    logger.warning(f"Image not found: {filename}")
    raise HTTPException(status_code=404, detail=f"Image not found: {filename}")


# ============================================
# STORY PREVIEW PAGE ROUTE
# ============================================
@app.get("/story-preview/{story_key:path}", response_class=HTMLResponse)
async def story_preview_page(request: Request, story_key: str):
    """Story preview/edit page"""
    from urllib.parse import unquote
    from app.services.story_service import StoryService
    
    decoded_key = unquote(story_key)
    story = await StoryService.get_story(decoded_key)
    
    if not story:
        return templates.TemplateResponse("dashboard.html", {"request": request, "error": "Story not found"})
    
    return templates.TemplateResponse("story_preview.html", {
        "request": request,
        "story": story,
        "story_key": decoded_key
    })


# ============================================
# HEALTH AND STATUS ENDPOINTS
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    api_service = get_medium_api_service()
    return {
        "status": "healthy",
        "timestamp": __import__('datetime').datetime.now().isoformat(),
        "version": "2.0.0",
        "medium_authenticated": api_service.is_authenticated()
    }


@app.get("/api/status")
async def api_status():
    """API status endpoint with detailed info"""
    api_service = get_medium_api_service()
    return {
        "success": True,
        "status": "running",
        "version": "2.0.0",
        "medium": {
            "authenticated": api_service.is_authenticated(),
            "cookies_loaded": api_service.cookies is not None
        }
    }


# ============================================
# ERROR HANDLERS
# ============================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler"""
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request},
        status_code=404
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Custom 500 handler"""
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "error": str(exc)},
        status_code=500
    )


# ============================================
# ROOT PATHS INFO
# ============================================

@app.get("/api")
async def api_root():
    """API root endpoint with available endpoints"""
    return {
        "name": "Story Manager API",
        "version": "2.0.0",
        "endpoints": {
            "dashboard": "/api/dashboard",
            "stories": "/api/stories",
            "series": "/api/series",
            "calendar": "/api/calendar",
            "settings": "/api/settings",
            "monthly": "/api/monthly",
            "health": "/health",
            "status": "/api/status"
        },
        "documentation": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )