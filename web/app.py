import os
import shutil
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from agent.agent import run_agent


app = FastAPI(title="Job Recommendation Agent")

templates = Jinja2Templates(directory="web/templates")

RESUME_DIR = Path("resumes")
RESUME_PATH = RESUME_DIR / "resume.pdf"

RESUME_DIR.mkdir(exist_ok=True)

job_status = {
    "status": "idle",
    "message": "",
}

job_lock = threading.Lock()


def run_job(
    resume_path: str,
    to_email: str,
    instructions: str,
):
    global job_status

    try:
        job_status["status"] = "running"
        job_status["message"] = "Agent is running..."

        run_agent(
            resume_path=resume_path,
            to_email=to_email,
            additional_instructions=instructions,
        )

        job_status["status"] = "completed"
        job_status["message"] = "Job completed and email sent."

    except Exception as e:
        job_status["status"] = "failed"
        job_status["message"] = str(e)

    finally:
        job_lock.release()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "status": job_status,
            "resume_exists": RESUME_PATH.exists(),
            "default_email": os.getenv("EMAIL_TO", ""),
        },
    )


@app.get("/status")
def status():
    return job_status


@app.post("/run")
async def run(
    resume: UploadFile | None = File(default=None),
    to_email: str | None = Form(default=None),
    instructions: str | None = Form(default=None),
):
    if resume and resume.filename:
        if not resume.filename.lower().endswith(".pdf"):
            return {
                "status": "error",
                "message": "Resume must be a PDF.",
            }

        if job_lock.locked():
            return {
                "status": "already_running",
                "message": "A job is already running.",
            }

        RESUME_DIR.mkdir(exist_ok=True)

        with RESUME_PATH.open("wb") as buffer:
            shutil.copyfileobj(resume.file, buffer)

    if not RESUME_PATH.exists():
        return {
            "status": "error",
            "message": "No resume found. Upload a resume first.",
        }

    email = to_email or os.getenv("EMAIL_TO")

    if not email:
        return {
            "status": "error",
            "message": "No email address provided and EMAIL_TO is not set.",
        }

    if not job_lock.acquire(blocking=False):
        return {
            "status": "already_running",
            "message": "A job is already running.",
        }

    thread = threading.Thread(
        target=run_job,
        args=(
            str(RESUME_PATH.resolve()),
            email,
            instructions or "",
        ),
        daemon=True,
    )

    thread.start()

    return {
        "status": "started",
        "message": "Job recommendation agent started.",
    }