# Job Recommendation Agent

An AI-powered job recommendation agent that finds, verifies, and ranks software engineering jobs based on your resume and preferences.

The agent uses **LangGraph** to orchestrate the workflow, **Firecrawl** to search and crawl job postings, **Gemini** to analyze and rank jobs, and **Brevo** to send the final recommendations by email.

## Features

- 📄 Reads and analyzes your resume
- 🔎 Searches for relevant software engineering jobs
- 🌐 Crawls job postings to verify details
- 🎯 Matches jobs against your experience and technical skills
- 📊 Scores jobs based on relevance
- 📧 Sends recommendations directly to your email
- 🔗 Prefers direct company job postings
- 🧠 Uses an LLM to decide when and which tools to use
- 🔭 Supports LangSmith tracing for agent observability

## Architecture

```text
                    ┌──────────────┐
                    │    Resume    │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   LangGraph  │
                    │     Agent    │
                    └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │              │
                    ▼              ▼
              ┌──────────┐   ┌──────────┐
              │ Firecrawl│   │  Gemini  │
              │  Search  │   │   LLM    │
              └────┬─────┘   └──────────┘
                   │
                   ▼
              ┌──────────┐
              │  Crawl   │
              │  Jobs    │
              └────┬─────┘
                   │
                   ▼
              ┌──────────┐
              │  Gemini  │
              │  Ranking │
              └────┬─────┘
                   │
                   ▼
              ┌──────────┐
              │  Brevo   │
              │  Email   │
              └──────────┘
```

## Agent Workflow

```text
START
  │
  ▼
LLM
  │
  ├── Tool call required ──► ToolNode
  │                              │
  │                              ▼
  │                             LLM
  │                              │
  │                              └──► ...
  │
  └── No tool call ───────────► END
```

The LLM decides when to:

1. Read the resume
2. Search for jobs
3. Crawl promising job postings
4. Verify job details
5. Rank matching jobs
6. Send the final recommendations by email

## Job Matching

The agent is designed to find roles such as:

- Software Engineer
- Software Development Engineer (SDE)
- Backend Engineer
- Full-Stack Engineer
- Other closely related engineering roles

It evaluates factors such as:

- Years of experience
- Programming languages
- Frameworks
- Databases
- Cloud technologies
- System design experience
- Job responsibilities
- Seniority
- Location
- Posting date
- Overall technical fit

Each verified job receives a **match score from 0–100**.

## Tools

### `read_resume`

Reads the user's PDF resume and extracts the text for analysis.

### `search_jobs`

Uses Firecrawl to search the web for relevant job postings.

### `crawl_job`

Crawls individual job postings to verify information such as:

- Company
- Job title
- Location
- Required experience
- Technologies
- Posting date
- Job status
- Job URL
- Application URL

Failed crawls are handled gracefully so that one unsupported website doesn't stop the entire workflow.

### `send_email`

Converts the generated Markdown recommendation into HTML and sends it using Brevo.

## Example Output

The email contains a table similar to:

| Company      | Job Title         | Location  | Experience | Match | Job Link    |
| ------------ | ----------------- | --------- | ---------- | ----: | ----------- |
| Example Corp | Software Engineer | Bengaluru | 3–5 years  |    94 | Job posting |
| Example Inc  | Backend Engineer  | Hyderabad | 3–6 years  |    89 | Job posting |

It also includes:

- **Top 5 recommendations**
- **Why each job matches**
- **Notable skill gaps**
- Application links when available

## Project Structure

```text
job-rec-agent/
├── agent/
│   ├── __init__.py
│   ├── agent.py
│   └── utils/
│       ├── __init__.py
│       ├── models.py
│       └── tools.py
│
├── resumes/
│   └── resume.pdf
│
├── main.py
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env
├── pyproject.toml
└── uv.lock
```

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Docker (optional)
- Google Gemini API key
- Firecrawl API key
- Brevo API key
- LangSmith account (optional)

## Setup

Clone the repository:

```bash
git clone <repository-url>
cd job-rec-agent
```

Create the virtual environment and install dependencies:

```bash
uv venv --python 3.12
source .venv/bin/activate
uv sync
```

Add your resume:

```text
resumes/resume.pdf
```

Create a `.env` file:

```env
GOOGLE_API_KEY=your-google-api-key
GOOGLE_MODEL=gemini-3.5-flash-lite

FIRECRAWL_API_KEY=your-firecrawl-api-key

BREVO_API_KEY=your-brevo-api-key
EMAIL_FROM=your-email@example.com
EMAIL_TO=your-email@example.com

LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_PROJECT=job-recommendation-agent
```

Do **not** commit `.env` or API keys to the repository.

## Run Locally

Run the agent directly:

```bash
uv run python main.py
```

The agent will:

```text
Resume
  ↓
Analyze skills & experience
  ↓
Search jobs
  ↓
Crawl promising postings
  ↓
Verify & rank
  ↓
Send email
```

## Run with Docker

Build the image:

```bash
docker compose build
```

Run the agent:

```bash
docker compose run --rm job-agent
```

The Docker container uses the same `.env` configuration and resume as the local setup.

## LangSmith

LangSmith tracing can be enabled through:

```env
LANGSMITH_TRACING=true
```

This allows you to inspect:

- LLM calls
- Tool calls
- Tool inputs
- Tool outputs
- Agent execution flow
- Token usage
- Execution latency

This is particularly useful for debugging the agent's search and crawling behavior.

## Design Goals

The project intentionally keeps the agent simple.

The current implementation focuses on:

- Resume-based job matching
- Reliable job verification
- Minimal tool set
- LLM-driven tool selection
- Email delivery

Additional functionality such as job tracking, persistence, dashboards, and automated follow-ups can be added later without changing the core agent architecture.

## Disclaimer

Job availability and job-posting information can change quickly. The agent attempts to verify postings before recommending them, but job details should always be checked on the employer's application page before applying.
