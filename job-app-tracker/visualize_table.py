# visualize_table.py
import json
import os
import plotly.graph_objects as go

def generate_markdown_table(data):
    header = "| Company | Job Title | Location | Status | Date |\n| --- | --- | --- | --- | --- |\n"
    rows = ""
    for item in data:
        company = item.get("Company", "").replace("|", "\\|")
        job_title = item.get("Job Title", "").replace("|", "\\|")
        location = item.get("Location", "").replace("|", "\\|")
        status = item.get("status", "").replace("|", "\\|").capitalize()
        date = item.get("Date", "Unknown").replace("|", "\\|")
        rows += f"| {company} | {job_title} | {location} | {status} | {date} |\n"
    return header + rows

def generate_sankey_chart(data):
    # Define all possible status nodes
    labels = ["Applied", "Interviewed", "Offer", "Declined"]
    
    # Count occurrences of each status
    status_counts = {"Applied": 0, "Interviewed": 0, "Offer": 0, "Declined": 0}
    for item in data:
        status = item.get("status", "").capitalize()
        if status in status_counts:
            status_counts[status] += 1
    
    # Define Sankey links (simplified: each status as a standalone flow from a source)
    source = [0, 0, 0, 0]  # All from "Start" (index 0 temporarily replaces full flow)
    target = [0, 1, 2, 3]  # Applied, Interviewed, Offer, Declined
    value = [
        status_counts["Applied"],
        status_counts["Interviewed"],
        status_counts["Offer"],
        status_counts["Declined"]
    ]
    
    # Remove zero-value links
    source = [s for s, v in zip(source, value) if v > 0]
    target = [t for t, v in zip(target, value) if v > 0]
    value = [v for v in value if v > 0]
    
    # Create Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=labels,
            color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]  # Custom colors
        ),
        link=dict(
            source=source,
            target=target,
            value=value,
            color="#cccccc"  # Light gray links
        )
    )])
    
    # Update layout
    fig.update_layout(title_text="Job Application Status Flow", font_size=12)
    
    # Save to HTML file
    os.makedirs("visualizations", exist_ok=True)
    fig.write_html("visualizations/sankey.html")
    print("Sankey chart generated and saved to visualizations/sankey.html")

if __name__ == '__main__':
    # Load results from JSON file
    with open("data/job_applications.json", "r") as f:
        data = json.load(f)
    
    # Sort by date, newest first
    data = sorted(data, key=lambda x: x["Date"], reverse=True)
    
    # Generate and save Markdown table
    table_markdown = generate_markdown_table(data)
    with open("TABLE.md", "w") as f:
        f.write(table_markdown)
    print("Markdown table generated and saved to TABLE.md")
    
    # Generate and save Sankey chart
    generate_sankey_chart(data)