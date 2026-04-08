from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import jinja2
from app.services.medium_api_service import get_medium_api_service
from app.routers import dashboard, stories, series, calendar, settings

app = FastAPI(title="Story Manager")
api_service = get_medium_api_service()

# lifetime_response = api_service.fetch_lifetime_stats('dddc86088f5e')
#lifetime_response = api_service.fetch_all_stories_stats('mvineetsharma', 1)
lifetime_response = api_service.get_story_earnings_medium('mvineetsharma', 2)
# lifetime_response = api_service.get_lifetime_stats('mvineetsharma')

# Mount static files 
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configure templates with multiple directories
templates = Jinja2Templates(directory="app/templates")
templates.env.loader = jinja2.FileSystemLoader([
    Path("app/templates"),
    Path("app/templates/modals")
])

# Include routers
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(stories.router, prefix="/api/stories", tags=["stories"])
app.include_router(series.router, prefix="/api/series", tags=["series"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])

# Page routes - using individual templates
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/stories", response_class=HTMLResponse)
async def stories_page(request: Request):
    return templates.TemplateResponse("stories.html", {"request": request})

@app.get("/series", response_class=HTMLResponse)
async def series_page(request: Request):
    return templates.TemplateResponse("series.html", {"request": request})

@app.get("/calendar", response_class=HTMLResponse)
async def calendar_page(request: Request):
    return templates.TemplateResponse("calendar.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

@app.get("/health")
async def health():
    return {"status": "healthy"}