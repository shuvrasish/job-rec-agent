import asyncio
from datetime import datetime
import os

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from langchain_core.tools import tool
from pypdf import PdfReader
import requests
import resend
from resend.exceptions import ResendError


from dotenv import load_dotenv

from agent.utils.db import get_unsent_job_ids, record_sent_jobs

load_dotenv()  # Load environment variables from .env file


from urllib.parse import urlparse


CAREER_INDEX_PATHS = {
    "/careers",
    "/career",
    "/jobs",
    "/job",
    "/all-jobs",
    "/open-positions",
    "/openings",
    "/job-openings",
    "/opportunities",
    "/job-search",
    "/search",
}


def is_probable_job_posting_url(url: str) -> bool:
    """Return False for obvious career/search/listing pages."""

    if not url:
        return False

    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme not in {"http", "https"}:
        return False

    path = parsed.path.lower().rstrip("/")

    # Exact career/listing pages.
    if path in CAREER_INDEX_PATHS:
        return False

    # Common listing/search pages.
    listing_suffixes = (
        "/all-jobs",
        "/search",
        "/search-results",
        "/job-search",
        "/open-positions",
        "/job-openings",
    )

    if path.endswith(listing_suffixes):
        return False

    return True

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


SEARXNG_URL = os.getenv("SEARXNG_URL")


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

        for result in data.get("results", []):
            url = result.get("url")
            
            if not is_probable_job_posting_url(url):
                continue
    
            results.append({
                "title": result.get("title"),
                "url": url,
                "content": result.get("content"),
            })
            
            if len(results) >= 10:
                break

        return str(results)

    except Exception as e:
        return f"""
            Unable to search the web.

            Query: {query}

            Reason: {type(e).__name__}: {e}
        """

@tool("crawl_job")
def crawl_job(url: str) -> str:
    """
        Crawl and inspect a candidate job URL.

        The URL is NOT considered a verified job posting merely because
        crawling succeeds.

        The caller must inspect the crawled page and determine whether
        it represents one specific active job opening rather than:
        - a careers homepage
        - a job search page
        - a jobs listing page
        - a department/engineering careers page
        - a page containing multiple job postings

        Only an individual job posting should be considered valid.
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

        return f"""
            URL: {url}

            IMPORTANT:
            This URL has passed a basic URL-level heuristic, but it is NOT yet
            verified as an individual job posting.

            PAGE CONTENT:
            {result.markdown}
        """

    except Exception as e:
        return f"""
            Unable to crawl this job posting.

            URL: {url}

            Reason: {type(e).__name__}: {e}

            Do not treat this as a verified job posting.
            Try another source or skip this job.
        """

@tool("filter_unsent_jobs")
def filter_unsent_jobs(
    to_email: str,
    job_ids: list[str],
) -> str:
    """Return only job IDs that have not already been emailed."""

    try:
        unsent = get_unsent_job_ids(
            to_email,
            job_ids,
        )

        return str(sorted(unsent))

    except Exception as e:
        return (
            "Unable to filter previously sent jobs. "
            f"Reason: {type(e).__name__}: {e}"
        )

@tool("send_email")
def send_email(
    subject: str,
    content: str,
    to_email: str | None = None,
    job_ids: list[str] | None = None,
) -> str:
    """Send job recommendations as a formatted HTML email using Resend and record successfully sent job IDs."""

    api_key = os.getenv("RESEND_API_KEY")
    recipient = to_email or os.getenv("EMAIL_TO")

    if not api_key:
        raise ValueError("RESEND_API_KEY is not configured.")

    if not recipient:
        raise ValueError(
            "No recipient email provided and EMAIL_TO is not configured."
        )

    job_ids = list(set(job_ids or []))

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
        raise RuntimeError(
            f"Failed to send email: {error}"
        ) from error

    print("calling recond sent jobs")
    # Email succeeded, so now persist the jobs.
    record_sent_jobs(
        user_email=recipient,
        job_ids=job_ids,
    )

    return (
        f"Email sent successfully to {recipient}. "
        f"Recorded {len(job_ids)} jobs."
    )

TOOLS = [
    read_resume,
    extract_experience,
    search_jobs,
    crawl_job,
    filter_unsent_jobs,
    send_email,
]
