# Job Tracker

A personal job application tracking system with a responsive web interface that works on desktop and mobile.

![Job Tracker Screenshot](https://via.placeholder.com/800x400?text=Job+Tracker+Dashboard)

## Features

- **Dashboard** - Overview of your job search with stats, charts, and recent activity
- **Application Management** - Add, edit, and track job applications with full status history
- **Interview Scheduling** - Track interviews with Google Calendar integration
- **Resume Management** - Upload and manage multiple resume versions
- **Email Sync** - Automatically import applications from Gmail using AI classification
- **Notifications** - Get notified of status changes and upcoming interviews
- **Reports & Export** - Export to Excel/CSV, view charts and analytics
- **Mobile-Friendly** - Responsive design works on any device
- **Local-First** - All data stored locally in SQLite (your data stays yours)

## Easy Installation

### Option 1: One-Command Install (Recommended)

```bash
git clone https://github.com/yourusername/job-tracker.git
cd job-tracker
python install.py
```

Then run:
- **Mac/Linux**: `./start.sh`
- **Windows**: `start.bat`

### Option 2: Manual Install

```bash
git clone https://github.com/yourusername/job-tracker.git
cd job-tracker
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

### Access from Your Phone

1. Find your computer's IP address (e.g., `192.168.1.100`)
2. Make sure your phone is on the same WiFi network
3. Open `http://192.168.1.100:8000` on your phone

## Features in Detail

### Dashboard
- Total applications count
- Response rate and interview rate
- Status breakdown with visual charts
- Recent activity feed
- Upcoming interviews

### Applications
- Add/edit applications with company, title, location, salary range
- Track status changes over time
- Attach job descriptions and notes
- Link to original job posting
- Quick status updates from list view

### Interview Tracking
- Schedule interviews with date, time, duration
- Track interview type (phone screen, technical, onsite, etc.)
- Add interviewer names and meeting links
- Preparation notes and post-interview notes
- **Google Calendar integration** - Sync interviews to your calendar

### Reports & Export
- Export all data to **Excel** or **CSV**
- Visual charts: applications by status, monthly trends
- Response rate and interview rate analytics
- Top companies applied to

### Email Sync (Optional)
Automatically detect and import job application emails:
1. Configure Gmail API (instructions in app)
2. Add your OpenAI API key
3. Click "Sync Now" to import recent emails
4. AI classifies and extracts job details

## Configuration

### Gmail API (Optional - for email sync)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project and enable Gmail API + Calendar API
3. Create OAuth 2.0 credentials (Desktop app type)
4. Download as `config/gmail_credentials.json`
5. Run the app and complete the OAuth flow

### OpenAI API (Optional - for email sync)

1. Get an API key from [OpenAI](https://platform.openai.com/api-keys)
2. Add to `config/.env`:
   ```
   OPENAI_API_KEY=your-key-here
   ```

## Application Statuses

| Status | Description |
|--------|-------------|
| Saved | Bookmarked, not yet applied |
| Applied | Application submitted |
| Screening | Initial phone screen |
| Interviewing | In interview process |
| Offer | Received job offer |
| Accepted | Accepted the offer |
| Declined | Rejected by company |
| Withdrawn | You withdrew application |

## Tech Stack

- **Backend**: FastAPI (Python 3.9+)
- **Database**: SQLite with SQLAlchemy
- **Frontend**: Jinja2 templates with Tailwind CSS
- **AI**: OpenAI GPT-3.5 for email classification
- **Integrations**: Gmail API, Google Calendar API

## Project Structure

```
job-tracker/
├── app/
│   ├── main.py              # FastAPI application
│   ├── database.py          # SQLite configuration
│   ├── models.py            # Database models
│   ├── routers/             # API routes
│   │   ├── applications.py  # Application CRUD
│   │   ├── interviews.py    # Interview management
│   │   ├── resumes.py       # Resume management
│   │   ├── notifications.py # Notifications
│   │   ├── export.py        # Export/reports
│   │   └── sync.py          # Email sync
│   ├── services/            # Business logic
│   │   ├── gmail.py         # Gmail integration
│   │   ├── calendar.py      # Google Calendar
│   │   └── classifier.py    # OpenAI classification
│   └── templates/           # HTML templates
├── data/                    # Your data (gitignored)
│   ├── tracker.db           # SQLite database
│   └── resumes/             # Uploaded files
├── config/                  # Configuration (gitignored)
├── install.py               # Easy installer
├── start.sh                 # Start script (Mac/Linux)
└── start.bat                # Start script (Windows)
```

## Privacy

**Your data stays on your machine.** Nothing is stored in the cloud.

- Database: `data/tracker.db` (local SQLite file)
- Resumes: `data/resumes/` (local folder)
- All config files are gitignored

External API calls (optional features only):
- Gmail API - to fetch your emails
- Google Calendar API - to sync interviews
- OpenAI API - to classify emails

## Contributing

Pull requests welcome! Please open an issue first to discuss changes.

## License

MIT
