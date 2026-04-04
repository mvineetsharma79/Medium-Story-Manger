from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging

from app.routers import stories, series, calendar, settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Story Manager", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(stories.router, prefix="/api/stories", tags=["stories"])
app.include_router(series.router, prefix="/api/series", tags=["series"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main dashboard"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("Starting Story Manager API")