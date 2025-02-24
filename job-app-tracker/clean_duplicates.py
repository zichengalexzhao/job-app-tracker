import json
import os

def count_unknown_fields(app):
    """Count the number of 'Unknown' fields in an application record."""
    unknown_count = sum(1 for value in app.values() if value == "Unknown")
    return unknown_count

def clean_duplicates(filename="data/job_applications.json"):
    # Load the existing job applications
    if not os.path.exists(filename):
        print("No job_applications.json found.")
        return
    
    with open(filename, 'r') as f:
        applications = json.load(f)
    
    print(f"Found {len(applications)} records before cleaning.")
    
    # Create dictionaries to track applications by company and job title
    unique_apps = {}
    duplicates_to_remove = []
    
    # Group applications by company and job title
    for i, app in enumerate(applications):
        key = f"{app['Company']}_{app['Job Title']}"
        if key not in unique_apps:
            unique_apps[key] = []
        unique_apps[key].append((i, app))
    
    # Process each group of applications
    for key, app_list in unique_apps.items():
        if len(app_list) > 1:  # Multiple entries for the same job
            # Check for Applied/Declined duplicates
            has_applied = False
            has_declined = False
            for idx, app in app_list:
                if app['status'] == "Applied":
                    has_applied = True
                elif app['status'] == "Declined":
                    has_declined = True
            
            # Remove Applied if Declined exists
            if has_applied and has_declined:
                for idx, app in app_list:
                    if app['status'] == "Applied":
                        duplicates_to_remove.append(idx)
            
            # Handle Interviewed duplicates: keep the most complete record
            interviewed_records = [(idx, app) for idx, app in app_list if app['status'] == "Interviewed"]
            if len(interviewed_records) > 1:  # Multiple Interviewed entries
                # Find the record with the fewest 'Unknown' fields
                best_record = min(interviewed_records, key=lambda x: count_unknown_fields(x[1]))
                # Mark all other Interviewed records for removal
                for idx, app in interviewed_records:
                    if idx != best_record[0]:  # Skip the best record
                        duplicates_to_remove.append(idx)
    
    # Sort duplicates in reverse order to remove from the end first (avoid index shifting)
    duplicates_to_remove = list(set(duplicates_to_remove))  # Remove duplicates in removal list
    duplicates_to_remove.sort(reverse=True)
    
    # Remove duplicates
    for idx in duplicates_to_remove:
        del applications[idx]
    
    # Save the cleaned data
    with open(filename, 'w') as f:
        json.dump(applications, f, indent=4)
    
    print(f"Cleaned {len(duplicates_to_remove)} duplicate entries. Now {len(applications)} records remain.")

if __name__ == '__main__':
    clean_duplicates()