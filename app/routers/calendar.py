from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from app.services.calendar_service import CalendarService
from app.models import CalendarResponse

router = APIRouter()

@router.get("/", response_model=CalendarResponse)
async def get_calendar():
    """Get the publishing calendar"""
    try:
        return await CalendarService.save_calendar_files()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate")
async def generate_calendar():
    """Generate and save calendar files"""
    try:
        response = await CalendarService.save_calendar_files()
        return {"message": "Calendar generated", "scheduled": response.summary["total_scheduled"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))