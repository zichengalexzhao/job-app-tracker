"""Resume management routes."""

import os
import shutil
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Resume, Application

router = APIRouter(prefix="/resumes", tags=["resumes"])
templates = Jinja2Templates(directory="app/templates")

RESUME_DIR = "data/resumes"

# Ensure resume directory exists
os.makedirs(RESUME_DIR, exist_ok=True)


@router.get("/", response_class=HTMLResponse)
async def list_resumes(request: Request, db: Session = Depends(get_db)):
    """List all resumes."""
    resumes = db.query(Resume).order_by(Resume.is_default.desc(), Resume.created_at.desc()).all()

    # Count applications per resume
    resume_counts = {}
    for resume in resumes:
        count = db.query(Application).filter(Application.resume_id == resume.id).count()
        resume_counts[resume.id] = count

    return templates.TemplateResponse("resumes/list.html", {
        "request": request,
        "resumes": resumes,
        "resume_counts": resume_counts
    })


@router.get("/upload", response_class=HTMLResponse)
async def upload_form(request: Request):
    """Show upload form."""
    return templates.TemplateResponse("resumes/upload.html", {
        "request": request
    })


@router.post("/upload")
async def upload_resume(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    file: UploadFile = File(...),
    is_default: bool = Form(False)
):
    """Upload a new resume."""
    # Validate file type
    allowed_extensions = {'.pdf', '.doc', '.docx'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Generate unique filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
    filename = f"{timestamp}_{safe_name}{file_ext}"
    file_path = os.path.join(RESUME_DIR, filename)

    # Save file
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # If this is default, unset other defaults
    if is_default:
        db.query(Resume).filter(Resume.is_default == True).update({"is_default": False})

    # Create database record
    resume = Resume(
        name=name,
        filename=file.filename,
        file_path=file_path,
        is_default=is_default
    )
    db.add(resume)
    db.commit()

    return RedirectResponse(url="/resumes/", status_code=303)


@router.get("/{resume_id}/download")
async def download_resume(resume_id: int, db: Session = Depends(get_db)):
    """Download a resume file."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not os.path.exists(resume.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        resume.file_path,
        filename=resume.filename,
        media_type="application/octet-stream"
    )


@router.post("/{resume_id}/default")
async def set_default(resume_id: int, db: Session = Depends(get_db)):
    """Set a resume as default."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Unset other defaults
    db.query(Resume).filter(Resume.is_default == True).update({"is_default": False})

    # Set this one as default
    resume.is_default = True
    db.commit()

    return RedirectResponse(url="/resumes/", status_code=303)


@router.post("/{resume_id}/delete")
async def delete_resume(resume_id: int, db: Session = Depends(get_db)):
    """Delete a resume."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Remove file
    if os.path.exists(resume.file_path):
        os.remove(resume.file_path)

    # Clear resume from applications
    db.query(Application).filter(Application.resume_id == resume_id).update({"resume_id": None})

    # Delete record
    db.delete(resume)
    db.commit()

    return RedirectResponse(url="/resumes/", status_code=303)
