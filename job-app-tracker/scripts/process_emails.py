# scripts/process_emails.py
import os
from dotenv import load_dotenv
import openai

load_dotenv(dotenv_path='config/.env')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in your .env file.")

openai.api_key = OPENAI_API_KEY

def is_job_application(snippet):
    """Quick check if email is job application-related using snippet."""
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": (
                    "Determine if this email snippet is related to a job application "
                    "(e.g., confirmation, rejection, interview). Return 'Yes' or 'No'."
                )
            },
            {"role": "user", "content": snippet}
        ]
    )
    return response.choices[0].message.content.strip().lower() == 'yes'

def classify_email(email_content):
    """Extract details from full email content."""
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert at analyzing job application emails. "
                    "Analyze this email and confirm if it’s a job application-related email "
                    "(e.g., confirmation, rejection, interview invite). "
                    "If not, return only: 'Not Job Application'. "
                    "If yes, extract: "
                    "1. Company name (infer from context if not explicit, else 'Unknown'), "
                    "2. Job title (infer from context if not explicit, else 'Unknown'), "
                    "3. Location (if not found, return 'Unknown'), "
                    "4. Status (e.g., 'Applied', 'Interviewed', 'Offer', 'Declined', or 'Unknown'). "
                    "Return in this format:\n"
                    "Company: [company name]\n"
                    "Job Title: [job title]\n"
                    "Location: [location]\n"
                    "Status: [status]\n"
                )
            },
            {"role": "user", "content": email_content}
        ]
    )
    try:
        classification = response.choices[0].message.content.strip()
        if not classification.startswith("Company:"):
            return "Not Job Application"
        return classification
    except (IndexError, AttributeError, KeyError) as e:
        print(f"Error processing OpenAI response: {e}")
        return "Not Job Application"
