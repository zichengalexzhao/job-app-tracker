"""Interview management routes."""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Interview, InterviewType, Application, Notification, NotificationType
from app.services.calendar import calendar_service

router = APIRouter(prefix="/interviews", tags=["interviews"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def list_interviews(request: Request, db: Session = Depends(get_db)):
    """List all upcoming interviews."""
    now = datetime.utcnow()

    # Upcoming interviews
    upcoming = db.query(Interview).filter(
        Interview.scheduled_at >= now
    ).order_by(Interview.scheduled_at.asc()).all()

    # Past interviews
    past = db.query(Interview).filter(
        Interview.scheduled_at < now
    ).order_by(Interview.scheduled_at.desc()).limit(10).all()

    return templates.TemplateResponse("interviews/list.html", {
        "request": request,
        "upcoming": upcoming,
        "past": past,
        "interview_types": InterviewType
    })


@router.get("/new/{app_id}", response_class=HTMLResponse)
async def new_interview_form(request: Request, app_id: int, db: Session = Depends(get_db)):
    """Show form to schedule new interview."""
    application = db.query(Application).filter(Application.id == app_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    return templates.TemplateResponse("interviews/form.html", {
        "request": request,
        "application": application,
        "interview": None,
        "interview_types": InterviewType,
        "is_edit": False
    })


@router.post("/new/{app_id}")
async def create_interview(
    request: Request,
    app_id: int,
    db: Session = Depends(get_db),
    interview_type: str = Form(...),
    scheduled_date: str = Form(...),
    scheduled_time: str = Form(...),
    duration_minutes: int = Form(60),
    location: str = Form(""),
    interviewers: str = Form(""),
    preparation_notes: str = Form(""),
    add_to_calendar: bool = Form(False)
):
    """Create a new interview."""
    application = db.query(Application).filter(Application.id == app_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Parse datetime
    try:
        scheduled_at = datetime.strptime(f"{scheduled_date} {scheduled_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date/time format")

    # Get interview type
    try:
        int_type = InterviewType(interview_type)
    except ValueError:
        int_type = InterviewType.OTHER

    interview = Interview(
        application_id=app_id,
        interview_type=int_type,
        scheduled_at=scheduled_at,
        duration_minutes=duration_minutes,
        location=location,
        interviewers=interviewers,
        preparation_notes=preparation_notes
    )

    db.add(interview)
    db.flush()

    # Add to Google Calendar if requested
    if add_to_calendar and calendar_service.is_configured():
        event_id = calendar_service.create_event(
            title=f"Interview: {application.company} - {application.job_title}",
            description=f"Interview Type: {int_type.value}\nInterviewers: {interviewers}\n\nNotes:\n{preparation_notes}",
            location=location,
            start_time=scheduled_at,
            duration_minutes=duration_minutes
        )
        if event_id:
            interview.calendar_event_id = event_id

    # Create notification
    notification = Notification(
        application_id=app_id,
        notification_type=NotificationType.INTERVIEW_REMINDER,
        title=f"Interview Scheduled: {application.company}",
        message=f"{int_type.value.replace('_', ' ').title()} interview scheduled for {scheduled_at.strftime('%B %d at %I:%M %p')}"
    )
    db.add(notification)

    db.commit()

    return RedirectResponse(url=f"/applications/{app_id}", status_code=303)


@router.get("/{interview_id}/edit", response_class=HTMLResponse)
async def edit_interview_form(request: Request, interview_id: int, db: Session = Depends(get_db)):
    """Show form to edit interview."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    return templates.TemplateResponse("interviews/form.html", {
        "request": request,
        "application": interview.application,
        "interview": interview,
        "interview_types": InterviewType,
        "is_edit": True
    })


@router.post("/{interview_id}/edit")
async def update_interview(
    request: Request,
    interview_id: int,
    db: Session = Depends(get_db),
    interview_type: str = Form(...),
    scheduled_date: str = Form(...),
    scheduled_time: str = Form(...),
    duration_minutes: int = Form(60),
    location: str = Form(""),
    interviewers: str = Form(""),
    preparation_notes: str = Form(""),
    post_interview_notes: str = Form(""),
    update_calendar: bool = Form(False)
):
    """Update an interview."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Parse datetime
    try:
        scheduled_at = datetime.strptime(f"{scheduled_date} {scheduled_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date/time format")

    try:
        int_type = InterviewType(interview_type)
    except ValueError:
        int_type = interview.interview_type

    interview.interview_type = int_type
    interview.scheduled_at = scheduled_at
    interview.duration_minutes = duration_minutes
    interview.location = location
    interview.interviewers = interviewers
    interview.preparation_notes = preparation_notes
    interview.post_interview_notes = post_interview_notes

    # Update Google Calendar if requested
    if update_calendar and interview.calendar_event_id and calendar_service.is_configured():
        calendar_service.update_event(
            event_id=interview.calendar_event_id,
            title=f"Interview: {interview.application.company} - {interview.application.job_title}",
            description=f"Interview Type: {int_type.value}\nInterviewers: {interviewers}\n\nNotes:\n{preparation_notes}",
            location=location,
            start_time=scheduled_at,
            duration_minutes=duration_minutes
        )

    db.commit()

    return RedirectResponse(url=f"/applications/{interview.application_id}", status_code=303)


@router.post("/{interview_id}/delete")
async def delete_interview(interview_id: int, db: Session = Depends(get_db)):
    """Delete an interview."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    app_id = interview.application_id

    # Delete from Google Calendar if synced
    if interview.calendar_event_id and calendar_service.is_configured():
        calendar_service.delete_event(interview.calendar_event_id)

    db.delete(interview)
    db.commit()

    return RedirectResponse(url=f"/applications/{app_id}", status_code=303)
