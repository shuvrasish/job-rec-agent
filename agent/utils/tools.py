from datetime import datetime
import os

from firecrawl import FirecrawlApp
from langchain_core.tools import tool
from pypdf import PdfReader
import resend
from resend.exceptions import ResendError


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

@tool("extract_experience")
def extract_experience(start_date: str) -> str:
    """Extract years and months of experience from a start date in YYYY-MM format."""
    
    target_date = datetime.strptime(start_date, "%Y-%m")
    current_date = datetime.now()
    total_months = (target_date.year * 12 + target_date.month) - (current_date.year * 12 + current_date.month)
    years = abs(total_months) // 12
    months = abs(total_months) % 12

    return f"{years} years and {months} months" if years > 0 else f"{months} months"


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
    """Send job recommendations as a formatted HTML email using Resend."""

    api_key = os.getenv("RESEND_API_KEY")
    recipient = to_email or os.getenv("EMAIL_TO")
    
    if not api_key:
        raise ValueError("RESEND_API_KEY is not configured.")

    if not recipient:
        raise ValueError(
            "No recipient email provided and EMAIL_TO is not configured."
        )
    
    resend.api_key = api_key
    
    try:
        params: resend.Emails.SendParams = {
            "from": "Job Scout <onboarding@resend.dev>",
            "to": [recipient],
            "subject": subject,
            "html": content,
            "reply_to": os.getenv("EMAIL_FROM", ""),
        }
        resend.Emails.send(params)
    except ResendError as error:
        raise RuntimeError(f"Failed to send email: {error}") from error

    return f"Email sent successfully to {recipient}."

TOOLS = [
    read_resume,
    extract_experience,
    search_jobs,
    crawl_job,
    send_email
]
