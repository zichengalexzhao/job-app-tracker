"""Email sync routes."""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, ApplicationStatus, StatusChange, ProcessedEmail
from app.services.gmail import gmail_service
from app.services.classifier import classifier

router = APIRouter(prefix="/sync", tags=["sync"])
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


STATUS_MAP = {
    'applied': ApplicationStatus.APPLIED,
    'screening': ApplicationStatus.SCREENING,
    'interviewing': ApplicationStatus.INTERVIEWING,
    'offer': ApplicationStatus.OFFER,
    'declined': ApplicationStatus.DECLINED,
    'withdrawn': ApplicationStatus.WITHDRAWN,
}


@router.get("/", response_class=HTMLResponse)
async def sync_status(request: Request, db: Session = Depends(get_db)):
    """Show sync status and configuration."""
    gmail_configured = gmail_service.is_configured()
    openai_configured = classifier.is_configured()

    # Get sync stats
    total_processed = db.query(ProcessedEmail).count()
    job_related = db.query(ProcessedEmail).filter(ProcessedEmail.is_job_related == True).count()

    return templates.TemplateResponse("sync/status.html", {
        "request": request,
        "gmail_configured": gmail_configured,
        "openai_configured": openai_configured,
        "total_processed": total_processed,
        "job_related": job_related
    })


@router.post("/run")
async def run_sync(
    request: Request,
    db: Session = Depends(get_db),
    hours: int = 24
):
    """Run email sync."""
    if not gmail_service.is_configured():
        return RedirectResponse(url="/sync/?error=gmail", status_code=303)

    if not classifier.is_configured():
        return RedirectResponse(url="/sync/?error=openai", status_code=303)

    # Authenticate Gmail
    if not gmail_service.authenticate():
        return RedirectResponse(url="/sync/?error=auth", status_code=303)

    # Fetch messages
    messages = gmail_service.fetch_messages(since_hours=hours)
    logger.info(f"Fetched {len(messages)} messages")

    new_applications = 0
    updated_applications = 0

    for msg in messages:
        msg_id = msg['id']

        # Check if already processed
        existing = db.query(ProcessedEmail).filter(
            ProcessedEmail.message_id == msg_id
        ).first()

        if existing:
            continue

        # Get message content
        content = gmail_service.get_message_content(msg_id)
        if not content:
            continue

        # Quick check if job-related
        is_job = classifier.is_job_related(content.get('snippet', ''))

        # Record as processed
        processed = ProcessedEmail(
            message_id=msg_id,
            is_job_related=is_job
        )
        db.add(processed)

        if not is_job:
            continue

        # Full classification
        full_content = f"From: {content.get('from', '')}\nSubject: {content.get('subject', '')}\n\n{content.get('body', '')}"
        details = classifier.classify_email(full_content)

        if not details:
            continue

        # Map status
        status_str = details.get('status', 'applied').lower()
        status = STATUS_MAP.get(status_str, ApplicationStatus.APPLIED)

        # Check for existing application by thread
        thread_id = content.get('thread_id')
        existing_app = None

        if thread_id:
            existing_app = db.query(Application).filter(
                Application.email_thread_id == thread_id
            ).first()

        if existing_app:
            # Update existing application if status changed
            if existing_app.status != status:
                old_status = existing_app.status
                existing_app.status = status
                existing_app.last_email_date = content.get('date')

                status_change = StatusChange(
                    application_id=existing_app.id,
                    old_status=old_status,
                    new_status=status,
                    source="email"
                )
                db.add(status_change)
                updated_applications += 1

                logger.info(f"Updated {existing_app.company}: {old_status.value} -> {status.value}")
        else:
            # Create new application
            app = Application(
                company=details.get('company', 'Unknown'),
                job_title=details.get('job_title', 'Unknown'),
                location=details.get('location', 'Unknown'),
                status=status,
                email_thread_id=thread_id,
                last_email_date=content.get('date'),
                applied_date=content.get('date') or datetime.utcnow()
            )
            db.add(app)
            db.flush()  # Get the ID

            # Record initial status
            status_change = StatusChange(
                application_id=app.id,
                old_status=None,
                new_status=status,
                source="email"
            )
            db.add(status_change)
            new_applications += 1

            logger.info(f"Added {app.company} - {app.job_title}")

    db.commit()

    return RedirectResponse(
        url=f"/sync/?success=1&new={new_applications}&updated={updated_applications}",
        status_code=303
    )
