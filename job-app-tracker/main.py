# main.py
"""Main orchestration script for job application tracking."""

import json
import logging
import os
import signal
import sys
from typing import Any, Optional

from scripts.gmail_fetch import fetch_emails, get_email_snippet, get_email_content
from scripts.process_emails import is_job_application, classify_email

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
results: list[dict[str, Any]] = []
interrupted: bool = False
processed_email_ids: set[str] = set()

# Status normalization keywords (case-insensitive)
STATUS_KEYWORDS = {
    "Declined": ["declined", "rejected", "not selected", "not moving forward",
                 "unfortunately", "regret", "will not be", "decided not to"],
    "Offer": ["offer", "accepted", "congratulations", "pleased to offer"],
    "Interviewed": ["interview", "screening", "phone call", "meet with"],
    "Applied": ["applied", "submitted", "received", "application received",
                "thank you for applying", "confirming receipt"]
}


def normalize_status(raw_status: str) -> str:
    """
    Normalize job application status to a standard category.

    Args:
        raw_status: The raw status string from email classification.

    Returns:
        One of: "Declined", "Offer", "Interviewed", or "Applied"
    """
    raw = raw_status.lower().strip()

    for status, keywords in STATUS_KEYWORDS.items():
        if any(keyword in raw for keyword in keywords):
            return status

    # Log unknown statuses for future improvement
    if raw and raw != "unknown":
        logger.warning(f"Unknown status encountered: '{raw_status}' - defaulting to 'Applied'")

    return "Applied"


def parse_classification_details(classification: str) -> dict[str, str]:
    """
    Parse classification response into structured details.

    Args:
        classification: The classification string from OpenAI.

    Returns:
        Dictionary with Company, Job Title, Location, status, and Date fields.
    """
    details = {
        "Company": "",
        "Job Title": "",
        "Location": "",
        "status": "",
        "Date": ""
    }
    for line in classification.splitlines():
        line = line.strip()
        if line.lower().startswith("company:"):
            details["Company"] = line.split(":", 1)[1].strip()
        elif line.lower().startswith("job title:"):
            details["Job Title"] = line.split(":", 1)[1].strip()
        elif line.lower().startswith("location:"):
            details["Location"] = line.split(":", 1)[1].strip()
        elif line.lower().startswith("status:"):
            raw_status = line.split(":", 1)[1].strip()
            details["status"] = normalize_status(raw_status)
    return details


def save_results(filename: str = "data/job_applications.json") -> None:
    """
    Save job application results to JSON file.

    Args:
        filename: Path to the output JSON file.
    """
    os.makedirs("data", exist_ok=True)
    # Create a copy of results without internal email_id
    results_to_save = [{k: v for k, v in r.items() if k != "email_id"} for r in results]
    try:
        with open(filename, "w") as f:
            json.dump(results_to_save, f, indent=4)
        logger.info(f"Saved {len(results_to_save)} records to {filename}")
    except IOError as e:
        logger.error(f"Failed to save results: {e}")


def load_existing_results(filename: str = "data/job_applications.json") -> list[dict[str, Any]]:
    """
    Load existing job application results from JSON file.

    Args:
        filename: Path to the input JSON file.

    Returns:
        List of job application records.
    """
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                content = f.read().strip()
                if not content:
                    return []
                return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Error reading {filename}: {e}")
            return []
        except IOError as e:
            logger.error(f"Failed to load {filename}: {e}")
            return []
    return []


def save_processed_ids(ids: set[str], filename: str = "data/processed_ids.json") -> None:
    """
    Save processed email IDs to JSON file.

    Args:
        ids: Set of processed email IDs.
        filename: Path to the output JSON file.
    """
    os.makedirs("data", exist_ok=True)
    try:
        with open(filename, "w") as f:
            json.dump(list(ids), f)
        logger.info(f"Saved {len(ids)} processed IDs")
    except IOError as e:
        logger.error(f"Failed to save processed IDs: {e}")


def load_processed_ids(filename: str = "data/processed_ids.json") -> set[str]:
    """
    Load processed email IDs from JSON file.

    Args:
        filename: Path to the input JSON file.

    Returns:
        Set of processed email IDs.
    """
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                content = f.read().strip()
                if not content:
                    return set()
                return set(json.loads(content))
        except json.JSONDecodeError as e:
            logger.error(f"Error reading {filename}: {e}")
            return set()
        except IOError as e:
            logger.error(f"Failed to load {filename}: {e}")
            return set()
    return set()


def signal_handler(sig: int, frame: Any) -> None:
    """Handle interrupt signals gracefully."""
    global interrupted
    interrupted = True
    logger.info("Interrupt received, saving progress...")
    save_results()
    save_processed_ids(processed_email_ids)
    sys.exit(0)


def process_all_emails(limit: Optional[int] = None, since_hours: Optional[int] = None) -> list[dict[str, Any]]:
    """
    Fetch and process all job-related emails.

    Args:
        limit: Maximum number of emails to process (None for unlimited).
        since_hours: Only process emails from the last N hours (None for all).

    Returns:
        List of processed job application records.
    """
    global results, interrupted, processed_email_ids
    signal.signal(signal.SIGINT, signal_handler)

    # Load existing state
    results = load_existing_results()
    processed_email_ids = load_processed_ids()
    logger.info(f"Loaded {len(results)} existing records, {len(processed_email_ids)} processed IDs")

    try:
        messages = fetch_emails(since_hours=since_hours)
    except Exception as e:
        logger.error(f"Failed to fetch emails: {e}")
        return results

    logger.info(f"Processing {len(messages)} emails...")

    processed = 0
    for msg in messages:
        if interrupted:
            break

        msg_id = msg['id']
        if msg_id in processed_email_ids:
            continue

        if limit is not None and processed >= limit:
            logger.info("Reached processing limit. Stopping.")
            break

        try:
            snippet = get_email_snippet(msg_id)
            if not is_job_application(snippet):
                processed_email_ids.add(msg_id)
                continue

            email_data = get_email_content(msg_id)
            content = email_data["content"]
            email_date = email_data["date"]

            classification = classify_email(content)
            processed_email_ids.add(msg_id)

            if "not job application" in classification.lower():
                continue

            details = parse_classification_details(classification)
            details["Date"] = email_date
            details["email_id"] = msg_id  # Keep internally for deduplication

            if details["Company"] or details["Job Title"] or details["Location"] or details["status"]:
                logger.info(f"Found: {details['Company']} - {details['Job Title']} ({details['status']})")
                results.append(details)
                processed += 1

                if processed % 10 == 0:
                    save_results()
                    save_processed_ids(processed_email_ids)

        except Exception as e:
            logger.error(f"Error processing email {msg_id}: {e}")
            processed_email_ids.add(msg_id)  # Mark as processed to avoid retry loops
            continue

    if not interrupted:
        save_results()
        save_processed_ids(processed_email_ids)

    return results


if __name__ == '__main__':
    try:
        process_all_emails(limit=None, since_hours=None)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        save_results()
        save_processed_ids(processed_email_ids)
