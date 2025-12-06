"""Follow-up scheduling routes."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FollowUp, FollowUpType, Application, Notification, NotificationType
from app.services.calendar import calendar_service

router = APIRouter(prefix="/followups", tags=["followups"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def list_followups(request: Request, db: Session = Depends(get_db)):
    """List all follow-ups."""
    now = datetime.utcnow()

    # Pending follow-ups
    pending = db.query(FollowUp).filter(
        FollowUp.is_completed == False,
        FollowUp.scheduled_date >= now
    ).order_by(FollowUp.scheduled_date.asc()).all()

    # Overdue follow-ups
    overdue = db.query(FollowUp).filter(
        FollowUp.is_completed == False,
        FollowUp.scheduled_date < now
    ).order_by(FollowUp.scheduled_date.desc()).all()

    # Completed follow-ups (recent)
    completed = db.query(FollowUp).filter(
        FollowUp.is_completed == True
    ).order_by(FollowUp.completed_at.desc()).limit(10).all()

    return templates.TemplateResponse("followups/list.html", {
        "request": request,
        "pending": pending,
        "overdue": overdue,
        "completed": completed,
        "follow_up_types": FollowUpType
    })


@router.get("/new/{app_id}", response_class=HTMLResponse)
async def new_followup_form(request: Request, app_id: int, db: Session = Depends(get_db)):
    """Show form to schedule new follow-up."""
    application = db.query(Application).filter(Application.id == app_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    return templates.TemplateResponse("followups/form.html", {
        "request": request,
        "application": application,
        "followup": None,
        "follow_up_types": FollowUpType,
        "is_edit": False
    })


@router.post("/new/{app_id}")
async def create_followup(
    request: Request,
    app_id: int,
    db: Session = Depends(get_db),
    follow_up_type: str = Form(...),
    scheduled_date: str = Form(...),
    scheduled_time: str = Form("09:00"),
    title: str = Form(...),
    notes: str = Form(""),
    add_to_calendar: bool = Form(False)
):
    """Create a new follow-up."""
    application = db.query(Application).filter(Application.id == app_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Parse datetime
    try:
        scheduled_at = datetime.strptime(f"{scheduled_date} {scheduled_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date/time format")

    # Get follow-up type
    try:
        fu_type = FollowUpType(follow_up_type)
    except ValueError:
        fu_type = FollowUpType.OTHER

    followup = FollowUp(
        application_id=app_id,
        follow_up_type=fu_type,
        scheduled_date=scheduled_at,
        title=title,
        notes=notes
    )

    db.add(followup)
    db.flush()

    # Add to Google Calendar if requested
    if add_to_calendar and calendar_service.is_configured():
        event_id = calendar_service.create_event(
            title=f"Follow-up: {application.company} - {title}",
            description=f"Follow-up for {application.job_title} at {application.company}\n\nType: {fu_type.value}\n\nNotes:\n{notes}",
            location="",
            start_time=scheduled_at,
            duration_minutes=30,
            reminder_minutes=60  # 1 hour reminder
        )
        if event_id:
            followup.calendar_event_id = event_id

    # Create notification
    notification = Notification(
        application_id=app_id,
        notification_type=NotificationType.FOLLOW_UP_REMINDER,
        title=f"Follow-up Scheduled: {application.company}",
        message=f"Reminder to {title} on {scheduled_at.strftime('%B %d at %I:%M %p')}"
    )
    db.add(notification)

    db.commit()

    return RedirectResponse(url=f"/applications/{app_id}", status_code=303)


@router.post("/{followup_id}/complete")
async def mark_complete(followup_id: int, db: Session = Depends(get_db)):
    """Mark a follow-up as completed."""
    followup = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not followup:
        raise HTTPException(status_code=404, detail="Follow-up not found")

    followup.is_completed = True
    followup.completed_at = datetime.utcnow()
    db.commit()

    return RedirectResponse(url="/followups/", status_code=303)


@router.post("/{followup_id}/delete")
async def delete_followup(followup_id: int, db: Session = Depends(get_db)):
    """Delete a follow-up."""
    followup = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not followup:
        raise HTTPException(status_code=404, detail="Follow-up not found")

    app_id = followup.application_id

    # Delete from Google Calendar if synced
    if followup.calendar_event_id and calendar_service.is_configured():
        calendar_service.delete_event(followup.calendar_event_id)

    db.delete(followup)
    db.commit()

    return RedirectResponse(url=f"/applications/{app_id}", status_code=303)
