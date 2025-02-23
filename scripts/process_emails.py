# scripts/process_emails.py
import os
from dotenv import load_dotenv
import openai

# Load environment variables from the .env file located in config/
load_dotenv(dotenv_path='config/.env')

# Retrieve the OpenAI API key from the environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in your .env file.")

# Set the API key for OpenAI
openai.api_key = OPENAI_API_KEY

def classify_email(email_content):
    """
    Uses OpenAI's GPT to extract job application details from the given email content.
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # or "gpt-4" if you have access
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract job application details (company, job title, location, status) "
                    "from the following email. If it is not a job application, return 'Not Job Application'."
                )
            },
            {"role": "user", "content": email_content}
        ]
    )
    return response.choices[0].message.content

if __name__ == '__main__':
    # For demonstration, we simulate an email content.
    sample_email = (
        "Dear Applicant, We have received your application for the Data Scientist position "
        "at OpenAI in San Francisco. We will review your resume and get back to you shortly."
    )
    result = classify_email(sample_email)
    print("OpenAI GPT Extraction Result:")
    print(result)
