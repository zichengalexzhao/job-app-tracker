# main.py
import json
from scripts.gmail_fetch import fetch_emails, get_email_content
from scripts.process_emails import classify_email

def normalize_status(raw_status):
    raw = raw_status.lower()
    if any(word in raw for word in ["applied", "submitted", "received"]):
        return "Applied"
    elif any(word in raw for word in ["declined", "rejected", "not selected"]):
        return "Declined"
    elif "interview" in raw:
        return "Interviewed"
    elif "offer" in raw:
        return "Offer"
    else:
        return "Applied"

def parse_classification_details(classification):
    details = {
        "Company": "",
        "Job Title": "",
        "Location": "",
        "status": ""
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

def process_all_emails(limit=None):
    messages = fetch_emails()
    print(f"Processing {len(messages)} emails...\n")
    
    results = []
    processed = 0
    for msg in messages:
        if limit is not None and processed >= limit:
            print("Reached processing limit. Stopping.")
            break
        
        msg_id = msg['id']
        content = get_email_content(msg_id)
        classification = classify_email(content)
        
        # Skip emails that are clearly not job applications
        if "not job application" in classification.lower():
            continue
        
        details = parse_classification_details(classification)
        
        # Only save if at least one field is non-empty
        if details["Company"] or details["Job Title"] or details["Location"] or details["status"]:
            print("Extracted Details:")
            print("Company:", details["Company"])
            print("Job Title:", details["Job Title"])
            print("Location:", details["Location"])
            print("status:", details["status"])
            print("-" * 40)
            results.append(details)
            processed += 1

    return results

def save_results(results, filename="data/job_applications.json"):
    # Ensure the data folder exists
    import os
    os.makedirs("data", exist_ok=True)
    with open(filename, "w") as f:
        json.dump(results, f, indent=4)
    print(f"Saved {len(results)} records to {filename}")

if __name__ == '__main__':
    try:
        results = process_all_emails(limit=10)
        save_results(results)  # Save the processed data into data/job_applications.json
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
