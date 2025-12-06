"""SQLAlchemy database models for job tracking."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class ApplicationStatus(enum.Enum):
    """Job application status enum."""
    SAVED = "saved"           # Bookmarked, not yet applied
    APPLIED = "applied"       # Application submitted
    SCREENING = "screening"   # Initial screening/phone screen
    INTERVIEWING = "interviewing"  # In interview process
    OFFER = "offer"           # Received offer
    ACCEPTED = "accepted"     # Accepted offer
    DECLINED = "declined"     # Rejected by company
    WITHDRAWN = "withdrawn"   # Withdrew application


class Application(Base):
    """Job application record."""
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)

    # Core job info
    company = Column(String(255), nullable=False, index=True)
    job_title = Column(String(255), nullable=False)
    location = Column(String(255), default="")
    job_url = Column(String(512), default="")

    # Application details
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.APPLIED, index=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)

    # Dates
    applied_date = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    response_date = Column(DateTime, nullable=True)

    # Notes and description
    notes = Column(Text, default="")
    job_description = Column(Text, default="")

    # Email tracking
    email_thread_id = Column(String(255), nullable=True, unique=True)
    last_email_date = Column(DateTime, nullable=True)

    # Resume used
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    resume = relationship("Resume", back_populates="applications")

    # Status history
    status_history = relationship("StatusChange", back_populates="application",
                                  order_by="StatusChange.changed_at.desc()")

    # Contacts at company
    contacts = relationship("Contact", back_populates="application")

    def __repr__(self):
        return f"<Application {self.company} - {self.job_title}>"


class StatusChange(Base):
    """Track status changes for an application."""
    __tablename__ = "status_changes"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)

    old_status = Column(Enum(ApplicationStatus), nullable=True)
    new_status = Column(Enum(ApplicationStatus), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String(50), default="manual")  # manual, email, import
    notes = Column(Text, default="")

    application = relationship("Application", back_populates="status_history")


class Resume(Base):
    """Resume/CV storage."""
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # e.g., "Software Engineer Resume"
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    is_default = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    applications = relationship("Application", back_populates="resume")

    def __repr__(self):
        return f"<Resume {self.name}>"


class Contact(Base):
    """Contacts at companies (recruiters, hiring managers, etc.)."""
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)

    name = Column(String(255), nullable=False)
    title = Column(String(255), default="")
    email = Column(String(255), default="")
    linkedin = Column(String(512), default="")
    notes = Column(Text, default="")

    application = relationship("Application", back_populates="contacts")

    def __repr__(self):
        return f"<Contact {self.name}>"


class ProcessedEmail(Base):
    """Track processed Gmail message IDs to avoid duplicates."""
    __tablename__ = "processed_emails"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(255), unique=True, nullable=False, index=True)
    processed_at = Column(DateTime, default=datetime.utcnow)
    is_job_related = Column(Boolean, default=False)


class InterviewType(enum.Enum):
    """Types of interviews."""
    PHONE_SCREEN = "phone_screen"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    ONSITE = "onsite"
    PANEL = "panel"
    FINAL = "final"
    OTHER = "other"


class Interview(Base):
    """Interview tracking with calendar integration."""
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)

    # Interview details
    interview_type = Column(Enum(InterviewType), default=InterviewType.OTHER)
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=60)
    location = Column(String(512), default="")  # Physical address or video link
    interviewers = Column(Text, default="")  # Names of interviewers

    # Notes
    preparation_notes = Column(Text, default="")
    post_interview_notes = Column(Text, default="")

    # Calendar sync
    calendar_event_id = Column(String(255), nullable=True)
    reminder_sent = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    application = relationship("Application", backref="interviews")

    def __repr__(self):
        return f"<Interview {self.interview_type.value} for {self.application_id}>"


class NotificationType(enum.Enum):
    """Types of notifications."""
    STATUS_CHANGE = "status_change"
    INTERVIEW_REMINDER = "interview_reminder"
    FOLLOW_UP_REMINDER = "follow_up_reminder"
    APPLICATION_DEADLINE = "application_deadline"
    WEEKLY_SUMMARY = "weekly_summary"


class Notification(Base):
    """User notifications."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)

    notification_type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Optional link to application
    application = relationship("Application", backref="notifications")

    def __repr__(self):
        return f"<Notification {self.title}>"


class AppSettings(Base):
    """Application settings and configuration."""
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AppSettings {self.key}>"


class FollowUpType(enum.Enum):
    """Types of follow-ups."""
    THANK_YOU = "thank_you"           # Post-interview thank you
    CHECK_STATUS = "check_status"     # Check application status
    NETWORKING = "networking"         # Networking follow-up
    DOCUMENTS = "documents"           # Send additional documents
    NEGOTIATE = "negotiate"           # Salary negotiation
    OTHER = "other"


class FollowUp(Base):
    """Scheduled follow-ups and reminders."""
    __tablename__ = "follow_ups"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)

    follow_up_type = Column(Enum(FollowUpType), default=FollowUpType.CHECK_STATUS)
    scheduled_date = Column(DateTime, nullable=False)
    title = Column(String(255), nullable=False)
    notes = Column(Text, default="")

    # Status
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)

    # Calendar sync
    calendar_event_id = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    application = relationship("Application", backref="follow_ups")

    def __repr__(self):
        return f"<FollowUp {self.title}>"
