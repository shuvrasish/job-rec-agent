import asyncio
from datetime import datetime
import os

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
# from firecrawl import FirecrawlApp
from langchain_core.tools import tool
from pypdf import PdfReader
import requests
import resend
from resend.exceptions import ResendError


from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file


# firecrawl = FirecrawlApp(
#     api_key=os.environ["FIRECRAWL_API_KEY"]
# )


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


SEARXNG_URL = os.getenv(
    "SEARXNG_URL",
    "http://localhost:8080",
)


@tool("search_jobs")
def search_jobs(query: str) -> str:
    """Search the web for job postings matching a query."""

    try:
        response = requests.get(
            f"{SEARXNG_URL}/search",
            params={
                "q": query,
                "format": "json",
            },
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        results = []

        for result in data.get("results", [])[:10]:
            results.append({
                "title": result.get("title"),
                "url": result.get("url"),
                "content": result.get("content"),
            })

        return str(results)

    except Exception as e:
        return f"""
            Unable to search the web.

            Query: {query}

            Reason: {type(e).__name__}: {e}
        """

@tool("crawl_job")
def crawl_job(url: str) -> str:
    """Crawl a job posting URL and return its contents.

    If the website cannot be crawled, return an error message
    instead of raising an exception.
    """

    async def _crawl():
        browser_config = BrowserConfig(
            headless=True,
        )

        crawler_config = CrawlerRunConfig(
            word_count_threshold=50,
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            return await crawler.arun(
                url=url,
                config=crawler_config,
            )

    try:
        result = asyncio.run(_crawl())

        if not result.success:
            return f"""
                Unable to crawl this job posting.

                URL: {url}

                Reason: {result.error_message}

                Do not treat this as a verified job posting.
                Try another source or skip this job.
            """

        return result.markdown

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
