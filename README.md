# Job Application Tracker

This project automates job application tracking by fetching relevant emails, extracting job details using AI, and visualizing the data. It runs locally or via GitHub Actions.

## Features

- **Automated Email Processing**: Fetches job-related emails from Gmail.
- **AI-Powered Classification**: Uses OpenAI to extract job details.
- **Data Cleaning**: Removes duplicate entries.
- **Visualizations**: Generates a [Markdown table](TABLE.md) and a [Sankey chart](visualizations/sankey.html) of job statuses.
- **Automated Updates**: Runs every hour via GitHub Actions.

## Installation

### Prerequisites

- Python 3.9+
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

#### 5. Run the script

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