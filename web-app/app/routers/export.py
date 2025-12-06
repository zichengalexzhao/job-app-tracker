"""Export and reporting routes."""

import io
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

import pandas as pd

from app.database import get_db
from app.models import Application, ApplicationStatus, StatusChange, Interview

router = APIRouter(prefix="/export", tags=["export"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def export_page(request: Request, db: Session = Depends(get_db)):
    """Show export and reporting page."""
    # Get summary stats
    total = db.query(func.count(Application.id)).scalar()

    # Status breakdown
    status_counts = {}
    for status in ApplicationStatus:
        count = db.query(func.count(Application.id)).filter(
            Application.status == status
        ).scalar()
        status_counts[status.value] = count

    # Applications per month (last 6 months)
    monthly_data = []
    for i in range(5, -1, -1):
        date = datetime.utcnow() - timedelta(days=30 * i)
        month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i > 0:
            next_month = (date + timedelta(days=32)).replace(day=1)
        else:
            next_month = datetime.utcnow() + timedelta(days=1)

        count = db.query(func.count(Application.id)).filter(
            Application.applied_date >= month_start,
            Application.applied_date < next_month
        ).scalar()

        monthly_data.append({
            "month": month_start.strftime("%b %Y"),
            "count": count
        })

    # Response rate
    total_with_response = status_counts.get('declined', 0) + status_counts.get('interviewing', 0) + \
                         status_counts.get('screening', 0) + status_counts.get('offer', 0) + \
                         status_counts.get('accepted', 0)
    response_rate = (total_with_response / total * 100) if total > 0 else 0

    # Interview rate
    interviewed = status_counts.get('interviewing', 0) + status_counts.get('offer', 0) + \
                  status_counts.get('accepted', 0)
    interview_rate = (interviewed / total * 100) if total > 0 else 0

    # Top companies applied to
    top_companies = db.query(
        Application.company,
        func.count(Application.id).label('count')
    ).group_by(Application.company).order_by(
        func.count(Application.id).desc()
    ).limit(10).all()

    return templates.TemplateResponse("export/index.html", {
        "request": request,
        "total": total,
        "status_counts": status_counts,
        "monthly_data": monthly_data,
        "response_rate": response_rate,
        "interview_rate": interview_rate,
        "top_companies": top_companies,
        "statuses": ApplicationStatus
    })


@router.get("/excel")
async def export_excel(db: Session = Depends(get_db)):
    """Export all applications to Excel."""
    applications = db.query(Application).order_by(Application.applied_date.desc()).all()

    data = []
    for app in applications:
        data.append({
            "Company": app.company,
            "Job Title": app.job_title,
            "Location": app.location,
            "Status": app.status.value if app.status else "",
            "Applied Date": app.applied_date.strftime("%Y-%m-%d") if app.applied_date else "",
            "Last Updated": app.last_updated.strftime("%Y-%m-%d") if app.last_updated else "",
            "Salary Min": app.salary_min or "",
            "Salary Max": app.salary_max or "",
            "Job URL": app.job_url or "",
            "Notes": app.notes or ""
        })

    df = pd.DataFrame(data)

    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Applications', index=False)

        # Auto-adjust column widths
        worksheet = writer.sheets['Applications']
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).map(len).max() if len(df) > 0 else 0,
                len(col)
            ) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)

    output.seek(0)

    filename = f"job_applications_{datetime.utcnow().strftime('%Y%m%d')}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/csv")
async def export_csv(db: Session = Depends(get_db)):
    """Export all applications to CSV."""
    applications = db.query(Application).order_by(Application.applied_date.desc()).all()

    data = []
    for app in applications:
        data.append({
            "Company": app.company,
            "Job Title": app.job_title,
            "Location": app.location,
            "Status": app.status.value if app.status else "",
            "Applied Date": app.applied_date.strftime("%Y-%m-%d") if app.applied_date else "",
            "Last Updated": app.last_updated.strftime("%Y-%m-%d") if app.last_updated else "",
            "Salary Min": app.salary_min or "",
            "Salary Max": app.salary_max or "",
            "Job URL": app.job_url or "",
            "Notes": app.notes or ""
        })

    df = pd.DataFrame(data)

    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    filename = f"job_applications_{datetime.utcnow().strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/interviews/csv")
async def export_interviews_csv(db: Session = Depends(get_db)):
    """Export all interviews to CSV."""
    interviews = db.query(Interview).order_by(Interview.scheduled_at.desc()).all()

    data = []
    for interview in interviews:
        data.append({
            "Company": interview.application.company,
            "Job Title": interview.application.job_title,
            "Interview Type": interview.interview_type.value if interview.interview_type else "",
            "Scheduled Date": interview.scheduled_at.strftime("%Y-%m-%d %H:%M") if interview.scheduled_at else "",
            "Duration (min)": interview.duration_minutes,
            "Location": interview.location,
            "Interviewers": interview.interviewers,
            "Prep Notes": interview.preparation_notes,
            "Post-Interview Notes": interview.post_interview_notes
        })

    df = pd.DataFrame(data)

    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    filename = f"interviews_{datetime.utcnow().strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
