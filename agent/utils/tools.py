import csv
import os

from firecrawl import FirecrawlApp
from langchain_core.tools import tool
from pypdf import PdfReader
import requests
import markdown

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file


firecrawl = FirecrawlApp(
    api_key=os.environ["FIRECRAWL_API_KEY"]
)


@tool("read_resume")
def read_resume(file_path: str) -> str:
    """Read a PDF resume and return its text."""

    reader = PdfReader(file_path)

    text = []

    for page in reader.pages:
        text.append(page.extract_text() or "")

    return "\n".join(text)


@tool("search_jobs")
def search_jobs(query: str) -> str:
    """Search the web for job postings matching a query."""

    results = firecrawl.search(
        query=query,
        limit=10,
    )

    return str(results)


@tool("crawl_job")
def crawl_job(url: str) -> str:
    """Crawl a job posting URL and return its contents.

    If the website cannot be crawled, return an error message
    instead of raising an exception.
    """

    try:
        result = firecrawl.scrape_url(url)
        return str(result)

    except Exception as e:
        return f"""
            Unable to crawl this job posting.

            URL: {url}

            Reason: {type(e).__name__}: {e}

            Do not treat this as a verified job posting.
            Try another source or skip this job.
        """

@tool("send_email")
def send_email(
    subject: str,
    content: str,
    to_email: str | None = None,
) -> str:
    """Send job recommendations as a formatted HTML email using Brevo."""

    api_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("EMAIL_FROM")
    recipient = to_email or os.getenv("EMAIL_TO")

    if not api_key:
        raise ValueError("BREVO_API_KEY is not configured.")

    if not sender_email:
        raise ValueError("EMAIL_FROM is not configured.")

    if not recipient:
        raise ValueError(
            "No recipient email provided and EMAIL_TO is not configured."
        )

    html_content = markdown.markdown(
        content,
        extensions=["tables"],
    )

    response = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
        },
        json={
            "sender": {
                "email": sender_email,
                "name": "Job Recommendation Agent",
            },
            "to": [
                {"email": recipient}
            ],
            "subject": subject,
            "htmlContent": html_content,
        },
        timeout=30,
    )

    response.raise_for_status()

    return f"Email sent successfully to {recipient}."

TOOLS = [
    read_resume,
    search_jobs,
    crawl_job,
    send_email,
]