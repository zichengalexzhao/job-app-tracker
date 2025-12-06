"""Application CRUD routes."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Application, ApplicationStatus, StatusChange, Resume

router = APIRouter(prefix="/applications", tags=["applications"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def list_applications(
    request: Request,
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort: str = Query("newest")
):
    """List all applications with optional filtering."""
    query = db.query(Application)

    # Filter by status
    if status and status != "all":
        try:
            status_enum = ApplicationStatus(status)
            query = query.filter(Application.status == status_enum)
        except ValueError:
            pass

    # Search by company or title
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Application.company.ilike(search_term)) |
            (Application.job_title.ilike(search_term))
        )

    # Sort
    if sort == "newest":
        query = query.order_by(Application.applied_date.desc())
    elif sort == "oldest":
        query = query.order_by(Application.applied_date.asc())
    elif sort == "company":
        query = query.order_by(Application.company.asc())
    elif sort == "updated":
        query = query.order_by(Application.last_updated.desc())

    applications = query.all()

    # Get status counts for filter badges
    status_counts = {}
    for s in ApplicationStatus:
        count = db.query(func.count(Application.id)).filter(
            Application.status == s
        ).scalar()
        status_counts[s.value] = count

    total_count = db.query(func.count(Application.id)).scalar()

    return templates.TemplateResponse("applications/list.html", {
        "request": request,
        "applications": applications,
        "statuses": ApplicationStatus,
        "status_counts": status_counts,
        "total_count": total_count,
        "current_status": status,
        "current_search": search or "",
        "current_sort": sort
    })


@router.get("/new", response_class=HTMLResponse)
async def new_application_form(request: Request, db: Session = Depends(get_db)):
    """Show form to create new application."""
    resumes = db.query(Resume).order_by(Resume.is_default.desc()).all()
    return templates.TemplateResponse("applications/form.html", {
        "request": request,
        "application": None,
        "statuses": ApplicationStatus,
        "resumes": resumes,
        "is_edit": False
    })


@router.post("/new")
async def create_application(
    request: Request,
    db: Session = Depends(get_db),
    company: str = Form(...),
    job_title: str = Form(...),
    location: str = Form(""),
    job_url: str = Form(""),
    status: str = Form("applied"),
    salary_min: Optional[int] = Form(None),
    salary_max: Optional[int] = Form(None),
    applied_date: Optional[str] = Form(None),
    notes: str = Form(""),
    job_description: str = Form(""),
    resume_id: Optional[int] = Form(None)
):
    """Create a new application."""
    try:
        status_enum = ApplicationStatus(status)
    except ValueError:
        status_enum = ApplicationStatus.APPLIED

    # Parse date
    if applied_date:
        try:
            parsed_date = datetime.strptime(applied_date, "%Y-%m-%d")
        except ValueError:
            parsed_date = datetime.utcnow()
    else:
        parsed_date = datetime.utcnow()

    application = Application(
        company=company,
        job_title=job_title,
        location=location,
        job_url=job_url,
        status=status_enum,
        salary_min=salary_min if salary_min else None,
        salary_max=salary_max if salary_max else None,
        applied_date=parsed_date,
        notes=notes,
        job_description=job_description,
        resume_id=resume_id if resume_id else None
    )

    db.add(application)
    db.commit()

    # Record initial status
    status_change = StatusChange(
        application_id=application.id,
        old_status=None,
        new_status=status_enum,
        source="manual"
    )
    db.add(status_change)
    db.commit()

    return RedirectResponse(url=f"/applications/{application.id}", status_code=303)


@router.get("/{app_id}", response_class=HTMLResponse)
async def view_application(request: Request, app_id: int, db: Session = Depends(get_db)):
    """View a single application."""
    application = db.query(Application).filter(Application.id == app_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    return templates.TemplateResponse("applications/detail.html", {
        "request": request,
        "application": application,
        "statuses": ApplicationStatus
    })


@router.get("/{app_id}/edit", response_class=HTMLResponse)
async def edit_application_form(request: Request, app_id: int, db: Session = Depends(get_db)):
    """Show form to edit application."""
    application = db.query(Application).filter(Application.id == app_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    resumes = db.query(Resume).order_by(Resume.is_default.desc()).all()

    return templates.TemplateResponse("applications/form.html", {
        "request": request,
        "application": application,
        "statuses": ApplicationStatus,
        "resumes": resumes,
        "is_edit": True
    })


@router.post("/{app_id}/edit")
async def update_application(
    request: Request,
    app_id: int,
    db: Session = Depends(get_db),
    company: str = Form(...),
    job_title: str = Form(...),
    location: str = Form(""),
    job_url: str = Form(""),
    status: str = Form("applied"),
    salary_min: Optional[int] = Form(None),
    salary_max: Optional[int] = Form(None),
    applied_date: Optional[str] = Form(None),
    notes: str = Form(""),
    job_description: str = Form(""),
    resume_id: Optional[int] = Form(None)
):
    """Update an application."""
    application = db.query(Application).filter(Application.id == app_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    try:
        new_status = ApplicationStatus(status)
    except ValueError:
        new_status = application.status

    # Track status change
    if application.status != new_status:
        status_change = StatusChange(
            application_id=application.id,
            old_status=application.status,
            new_status=new_status,
            source="manual"
        )
        db.add(status_change)
        application.response_date = datetime.utcnow()

    # Parse date
    if applied_date:
        try:
            application.applied_date = datetime.strptime(applied_date, "%Y-%m-%d")
        except ValueError:
            pass

    application.company = company
    application.job_title = job_title
    application.location = location
    application.job_url = job_url
    application.status = new_status
    application.salary_min = salary_min if salary_min else None
    application.salary_max = salary_max if salary_max else None
    application.notes = notes
    application.job_description = job_description
    application.resume_id = resume_id if resume_id else None

    db.commit()

    return RedirectResponse(url=f"/applications/{app_id}", status_code=303)


@router.post("/{app_id}/status")
async def quick_update_status(
    app_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db)
):
    """Quick status update (for dropdown on list view)."""
    application = db.query(Application).filter(Application.id == app_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    try:
        new_status = ApplicationStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")

    if application.status != new_status:
        status_change = StatusChange(
            application_id=application.id,
            old_status=application.status,
            new_status=new_status,
            source="manual"
        )
        db.add(status_change)
        application.status = new_status
        application.response_date = datetime.utcnow()
        db.commit()

    return RedirectResponse(url="/applications/", status_code=303)


@router.post("/{app_id}/delete")
async def delete_application(app_id: int, db: Session = Depends(get_db)):
    """Delete an application."""
    application = db.query(Application).filter(Application.id == app_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Delete related records
    db.query(StatusChange).filter(StatusChange.application_id == app_id).delete()
    db.delete(application)
    db.commit()

    return RedirectResponse(url="/applications/", status_code=303)
