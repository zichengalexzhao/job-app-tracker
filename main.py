# main.py
import json
import os
import signal
import sys
from scripts.gmail_fetch import fetch_emails, get_email_snippet, get_email_content
from scripts.process_emails import is_job_application, classify_email

# Global variables
results = []
interrupted = False
processed_email_ids = set()  # Moved to global scope for clarity

def normalize_status(raw_status):
    raw = raw_status.lower().strip()
    if any(word in raw for word in ["declined", "rejected", "not selected"]):
        return "Declined"
    elif any(word in raw for word in ["offer", "accepted"]):
        return "Offer"
    elif "interview" in raw:
        return "Interviewed"
    elif any(word in raw for word in ["applied", "submitted", "received"]):
        return "Applied"
    else:
        return "Applied"

def parse_classification_details(classification):
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

def save_results(filename="data/job_applications.json"):
    os.makedirs("data", exist_ok=True)
    # Create a copy of results without email_id
    results_to_save = [{k: v for k, v in r.items() if k != "email_id"} for r in results]
    with open(filename, "w") as f:
        json.dump(results_to_save, f, indent=4)
    print(f"Saved {len(results_to_save)} records to {filename}")

def load_existing_results(filename="data/job_applications.json"):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return []

def save_processed_ids(ids, filename="data/processed_ids.json"):
    os.makedirs("data", exist_ok=True)
    with open(filename, "w") as f:
        json.dump(list(ids), f)
    print(f"Saved {len(ids)} processed IDs")

def load_processed_ids(filename="data/processed_ids.json"):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return set(json.load(f))
    return set()

def signal_handler(sig, frame):
    global interrupted
    interrupted = True
    print("\nInterrupt received, saving progress...")
    save_results()
    save_processed_ids(processed_email_ids)
    sys.exit(0)

def process_all_emails(limit=None, since_hours=None):
    global results, interrupted, processed_email_ids
    signal.signal(signal.SIGINT, signal_handler)
    
    # Load existing state
    results = load_existing_results()
    processed_email_ids = load_processed_ids()
    print(f"Loaded {len(results)} existing records, {len(processed_email_ids)} processed IDs")
    
    messages = fetch_emails(since_hours=since_hours)
    print(f"Processing {len(messages)} emails...")
    
    processed = 0
    for msg in messages:
        if interrupted:
            break
        
        msg_id = msg['id']
        if msg_id in processed_email_ids:
            continue
        
        if limit is not None and processed >= limit:
            print("Reached processing limit. Stopping.")
            break
        
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
        details["email_id"] = msg_id  # Keep internally
        
        if details["Company"] or details["Job Title"] or details["Location"] or details["status"]:
            print("Extracted Details:")
            print("Email ID:", details["email_id"])  # Still print for debugging
            print("Company:", details["Company"])
            print("Job Title:", details["Job Title"])
            print("Location:", details["Location"])
            print("status:", details["status"])
            print("Date:", details["Date"])
            print("-" * 40)
            results.append(details)
            processed += 1
            
            if processed % 10 == 0:
                save_results()
                save_processed_ids(processed_email_ids)
    
    if not interrupted:
        save_results()
        save_processed_ids(processed_email_ids)
    
    return results

if __name__ == '__main__':
    try:
        process_all_emails(limit=None, since_hours=None)
    except Exception as e:
        print(f"Unexpected error: {e}")
        save_results()
        save_processed_ids(processed_email_ids)