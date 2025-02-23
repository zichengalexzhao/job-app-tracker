# visualize_table.py
import json

def generate_markdown_table(data):
    # Define the table header
    header = "| Company | Job Title | Location | status |\n| --- | --- | --- | --- |\n"
    rows = ""
    for item in data:
        # For safety, replace any pipe characters to avoid table issues.
        company = item.get("Company", "").replace("|", "\\|")
        job_title = item.get("Job Title", "").replace("|", "\\|")
        location = item.get("Location", "").replace("|", "\\|")
        status = item.get("status", "").replace("|", "\\|")
        rows += f"| {company} | {job_title} | {location} | {status} |\n"
    return header + rows

if __name__ == '__main__':
    # Load your results from a JSON file
    with open("data/job_applications.json", "r") as f:
        data = json.load(f)
    
    table_markdown = generate_markdown_table(data)
    with open("TABLE.md", "w") as f:
        f.write(table_markdown)
    
    print("Markdown table generated and saved to TABLE.md")
