# Job Application Tracker

This project automates job application tracking by fetching relevant emails, extracting job details using LLM, and visualizing the data. It runs locally or via GitHub Actions.

![Picture](job-app-tracker/featured.jpg)

## New: Web Application (v2)

A full-featured web application for job tracking is now available in the `web-app/` directory. This new version includes:

- **Responsive Web Interface** - Works on desktop and mobile with dark mode support
- **Full CRUD Operations** - Add, edit, delete applications through the UI
- **Interview Scheduling** - Track interviews with Google Calendar integration
- **Follow-up Reminders** - Set reminders with calendar sync
- **Resume Management** - Upload and track resume versions
- **Email Sync** - Import applications from Gmail using AI classification
- **Reports & Export** - Excel/CSV export and visual analytics

**Quick Start:**
```bash
cd web-app
python install.py
./start.sh  # or start.bat on Windows
```
Open http://localhost:8000 in your browser.

See [web-app/README.md](web-app/README.md) for full documentation.

---

## CLI Version (Original)

## Privacy Notice

**Your job application data is personal and should remain private.**

This tool is designed for **individual use** - each user should:
1. Fork this repository to their own GitHub account
2. Keep their fork **private** (or be aware that public forks expose your job search data)
3. Never commit personal data (`data/job_applications.json`) to a public repository

The data files are excluded from git by default via `.gitignore`. Example templates are provided in `data/*.example.json` to help you get started.

## Features

- **Automated Email Processing**: Fetches job-related emails from Gmail.
- **AI-Powered Classification**: Uses OpenAI to extract job details.
- **Data Cleaning**: Removes duplicate entries.
- **Visualizations**: Generates a [Markdown table](TABLE.md) and a [Sankey chart](visualizations/sankey.html) of job statuses.
- **Automated Updates**: Runs every hour via GitHub Actions.

## Installation

### Prerequisites

- Python 3.11+
- Google API credentials
- OpenAI API key
- Gmail access enabled

### Setup Locally

#### 1. Clone the repository

```bash
git clone https://github.com/yourusername/job-app-tracker.git
cd job-app-tracker
```

#### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

#### 3. Install dependencies

```bash
pip install -r requirements.txt
```

#### 4. Configure API keys

- Place your Gmail credentials in config/gmail_credentials.json
- Save your Gmail token in config/token.json
- Create a .env file in config/ and add:

```ini
OPENAI_API_KEY=your-openai-api-key
```

#### 5. Initialize your data files

Copy the example templates to create your personal data files:
```bash
cp data/job_applications.example.json data/job_applications.json
cp data/processed_ids.example.json data/processed_ids.json
```

#### 6. Run the script

```bash
python job-app-tracker/main.py
```

### Running on Github Actions

The workflow is defined in `.github/workflows/update.yml` and runs every hour.

#### Setting Up Secrets

1. Go to Repository Settings → Secrets and variables → Actions.
2. Add the following secrets:

- `GMAIL_CREDENTIALS`: Your Gmail credentials JSON (as a string).
- `GMAIL_TOKEN`: Your Gmail token JSON (as a string).
- `OPENAI_API_KEY`: Your OpenAI API key.
- `GITHUB_TOKEN`: (Automatically available in GitHub Actions)

#### Workflow Steps

1. Fetches latest emails and classifies job applications.
2. Cleans duplicate entries in the dataset.
3. Generates visualizations of job application statuses.
4. Commits and pushes updates back to the repository.

### Data Processing

- Email Fetching (`gmail_fetch.py`): Connects to Gmail, fetches job-related emails, and extracts content.
- Email Classification (`process_emails.py`): Uses OpenAI to determine if an email is a job application and extracts job details.
- Duplicate Cleaning (`clean_duplicates.py`): Removes redundant job entries.
- Visualization (`visualize_table.py`): Creates a Markdown table and a Sankey chart of job application statuses.

### Contributing

Feel free to submit pull requests or open issues for feature requests and bug fixes.
