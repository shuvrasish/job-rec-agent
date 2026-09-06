# Job Scout

AI-powered job recommendation agent built with **LangGraph**.

Job Scout uses your resume to find relevant Software Engineering jobs, verify job postings, evaluate the match, and send the recommendations to your email.

## Features

- Resume-based job search
- Search for recently posted Software Engineering roles
- Resume/job match scoring
- Job posting verification
- Email recommendations via Brevo
- Live agent activity in the web UI
- LangSmith tracing
- Run locally, on a Raspberry Pi, or with GitHub Actions

## Tech Stack

- Python 3.14
- LangGraph
- Google Gemini
- Firecrawl
- FastAPI
- HTMX
- Tailwind CSS
- daisyUI
- Brevo
- LangSmith
- Docker

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
├── web/
│   ├── __init__.py
│   ├── app.py
│   └── templates/
│       └── index.html
├── resumes/
│   └── resume.pdf
├── .github/
│   └── workflows/
│       └── job-agent.yml
├── main.py
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── uv.lock
```

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- Docker (for Raspberry Pi deployment)
- Google Gemini API key
- Firecrawl API key
- Brevo API key
- LangSmith API key (optional)

## Environment Variables

Create a `.env` file:

```env
GOOGLE_API_KEY="your-google-api-key"
GOOGLE_MODEL="gemini-3.5-flash-lite"

FIRECRAWL_API_KEY="your-firecrawl-api-key"

BREVO_API_KEY="your-brevo-api-key"
EMAIL_FROM="your-email@example.com"
EMAIL_TO="your-email@example.com"

LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY="your-langsmith-api-key"
LANGSMITH_PROJECT="job-recommendation-agent"
```

Do not commit `.env`.

## Local Setup

Install Python 3.14:

```bash
uv python install 3.14
uv python pin 3.14
```

Install dependencies:

```bash
uv sync
```

For the web UI:

```bash
uv sync --group web
```

Add your resume:

```text
resumes/resume.pdf
```

## Run the Agent

Run the agent without the web UI:

```bash
uv run python main.py
```

The agent will search for jobs, evaluate the matches, and send the recommendations to `EMAIL_TO`.

## Run the Web UI

Start the FastAPI server:

```bash
uv run uvicorn web.app:app --reload --port 8080
```

Open:

```text
http://localhost:8080
```

### Using the UI

1. Upload or replace your resume.
2. Enter the email address for the recommendations.
3. Optionally provide additional search instructions.
4. Click **Find matching jobs**.
5. Monitor the agent's live activity.
6. Receive the final recommendations by email.

The activity panel shows:

- Agent messages
- Tool calls
- Tool inputs
- Tool results
- Errors
- Completion status

## Raspberry Pi

Clone the repository:

```bash
git clone <repository-url>
cd job-rec-agent
```

Create `.env` and add your API keys.

Add your resume:

```text
resumes/resume.pdf
```

Build and start the application:

```bash
docker compose up -d --build
```

Check the container:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f
```

The application runs on port `8080`.

### Access through Tailscale

If you want direct access through your Pi's Tailscale hostname:

```text
https://aether.taild24737.ts.net:8080/
```

Use:

```yaml
ports:
  - "8080:8080"
```

in `docker-compose.yml`.

If Tailscale Serve was previously configured, remove it:

```bash
sudo tailscale serve reset
```

Check Tailscale:

```bash
tailscale status
```

> HTTPS on port `8080` requires TLS to be configured for the application. If the application is serving plain HTTP, use `http://aether.taild24737.ts.net:8080/`.

## Run Automatically with Cron

On the Raspberry Pi or another machine, edit your crontab:

```bash
crontab -e
```

Run the agent every 3 hours:

```cron
0 */3 * * * cd /home/YOUR_USERNAME/job-rec-agent && /usr/bin/docker compose run --rm job-agent uv run python main.py >> /home/YOUR_USERNAME/job-rec-agent/cron.log 2>&1
```

Check the cron configuration:

```bash
crontab -l
```

View logs:

```bash
tail -f ~/job-rec-agent/cron.log
```

Test the command manually:

```bash
cd ~/job-rec-agent
docker compose run --rm job-agent uv run python main.py
```

## GitHub Actions

GitHub Actions can run the agent without the web UI.

### Add Repository Secrets

Go to:

**GitHub → Repository → Settings → Secrets and variables → Actions**

Add:

```text
GOOGLE_API_KEY
GOOGLE_MODEL
FIRECRAWL_API_KEY
BREVO_API_KEY
EMAIL_FROM
EMAIL_TO
LANGSMITH_TRACING
LANGSMITH_ENDPOINT
LANGSMITH_API_KEY
LANGSMITH_PROJECT
RESUME_BASE64
```

## Security

Never commit:

```text
.env
resumes/resume.pdf
```

Keep API keys in environment variables or GitHub Actions secrets.
