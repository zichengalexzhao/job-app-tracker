"""Main FastAPI application."""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func

from app.database import init_db, get_db, SessionLocal
from app.models import Application, ApplicationStatus, Notification, Interview, AppSettings
from app.routers import applications, resumes, sync, interviews, notifications, export, followups

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create FastAPI app
app = FastAPI(
    title="Job Tracker",
    description="Personal job application tracking system",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(applications.router)
app.include_router(resumes.router)
app.include_router(sync.router)
app.include_router(interviews.router)
app.include_router(notifications.router)
app.include_router(export.router)
app.include_router(followups.router)


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    init_db()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard with overview stats."""
    db = SessionLocal()
    try:
        # Get counts by status
        status_counts = {}
        for status in ApplicationStatus:
            count = db.query(func.count(Application.id)).filter(
                Application.status == status
            ).scalar()
            status_counts[status.value] = count

        total = sum(status_counts.values())

        # Get recent applications
        recent = db.query(Application).order_by(
            Application.last_updated.desc()
        ).limit(5).all()

        # Get recent status changes
        from app.models import StatusChange
        recent_changes = db.query(StatusChange).order_by(
            StatusChange.changed_at.desc()
        ).limit(10).all()

        # Calculate response rate
        responded = status_counts.get('declined', 0) + status_counts.get('interviewing', 0) + \
                   status_counts.get('screening', 0) + status_counts.get('offer', 0) + \
                   status_counts.get('accepted', 0)
        response_rate = (responded / total * 100) if total > 0 else 0

        # Interview rate
        interviewed = status_counts.get('interviewing', 0) + status_counts.get('offer', 0) + \
                      status_counts.get('accepted', 0)
        interview_rate = (interviewed / total * 100) if total > 0 else 0

        # Notification count
        from datetime import datetime
        unread_notifications = db.query(func.count(Notification.id)).filter(
            Notification.is_read == False
        ).scalar()

        # Upcoming interviews
        upcoming_interviews = db.query(Interview).filter(
            Interview.scheduled_at >= datetime.utcnow()
        ).order_by(Interview.scheduled_at.asc()).limit(3).all()

        # Check if setup is complete
        setup_complete = db.query(AppSettings).filter(
            AppSettings.key == "setup_complete"
        ).first()

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "status_counts": status_counts,
            "total": total,
            "recent": recent,
            "recent_changes": recent_changes,
            "response_rate": response_rate,
            "interview_rate": interview_rate,
            "statuses": ApplicationStatus,
            "unread_notifications": unread_notifications,
            "upcoming_interviews": upcoming_interviews,
            "show_setup_wizard": not setup_complete
        })
    finally:
        db.close()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
