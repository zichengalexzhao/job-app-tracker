"""Notification routes."""

from datetime import datetime
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def list_notifications(request: Request, db: Session = Depends(get_db)):
    """List all notifications."""
    notifications = db.query(Notification).order_by(
        Notification.is_read.asc(),
        Notification.created_at.desc()
    ).limit(50).all()

    unread_count = db.query(func.count(Notification.id)).filter(
        Notification.is_read == False
    ).scalar()

    return templates.TemplateResponse("notifications/list.html", {
        "request": request,
        "notifications": notifications,
        "unread_count": unread_count
    })


@router.get("/count")
async def get_notification_count(db: Session = Depends(get_db)):
    """Get unread notification count (for badge)."""
    count = db.query(func.count(Notification.id)).filter(
        Notification.is_read == False
    ).scalar()
    return JSONResponse({"count": count})


@router.post("/{notification_id}/read")
async def mark_as_read(notification_id: int, db: Session = Depends(get_db)):
    """Mark a notification as read."""
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if notification:
        notification.is_read = True
        db.commit()
    return RedirectResponse(url="/notifications/", status_code=303)


@router.post("/read-all")
async def mark_all_as_read(db: Session = Depends(get_db)):
    """Mark all notifications as read."""
    db.query(Notification).filter(Notification.is_read == False).update({"is_read": True})
    db.commit()
    return RedirectResponse(url="/notifications/", status_code=303)


@router.post("/{notification_id}/delete")
async def delete_notification(notification_id: int, db: Session = Depends(get_db)):
    """Delete a notification."""
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if notification:
        db.delete(notification)
        db.commit()
    return RedirectResponse(url="/notifications/", status_code=303)


@router.post("/clear-all")
async def clear_all_notifications(db: Session = Depends(get_db)):
    """Delete all notifications."""
    db.query(Notification).delete()
    db.commit()
    return RedirectResponse(url="/notifications/", status_code=303)
