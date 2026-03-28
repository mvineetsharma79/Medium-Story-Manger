from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.routers import stories, series, calendar, settings

app = FastAPI(title="Story Manager", version="1.0.0")

# Mount static files
static_path = Path(__file__).parent.parent / "static"
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Templates
templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

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