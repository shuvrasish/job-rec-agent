import json
import os
import shutil
import threading
from pathlib import Path
from queue import Empty, Queue

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from agent.agent import run_agent_streaming


BASE_DIR = Path(__file__).resolve().parent.parent
RESUME_PATH = BASE_DIR / "resumes" / "resume.pdf"

app = FastAPI(title="Job Scout")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

event_queue: Queue = Queue()
job_lock = threading.Lock()

job_status = "ready"


def publish_event(event: dict):
    event_queue.put(event)


def run_job(
    resume_path: str,
    to_email: str,
    additional_instructions: str,
):
    global job_status

    try:
        job_status = "running"

        publish_event({
            "type": "status",
            "message": "Agent started",
        })

        for update in run_agent_streaming(
            resume_path=resume_path,
            to_email=to_email,
            additional_instructions=additional_instructions,
        ):
            process_agent_update(update)

        job_status = "complete"

        publish_event({
            "type": "complete",
            "message": "Job search completed successfully.",
        })

    except Exception as e:
        job_status = "failed"

        publish_event({
            "type": "error",
            "message": f"{type(e).__name__}: {e}",
        })

    finally:
        if job_lock.locked():
            job_lock.release()


def process_agent_update(update: dict):
    for node_name, node_update in update.items():

        if not isinstance(node_update, dict):
            continue

        messages = node_update.get("messages", [])

        for message in messages:
            # Tool calls made by the LLM
            tool_calls = getattr(message, "tool_calls", None)

            if tool_calls:
                for tool_call in tool_calls:
                    publish_event({
                        "type": "tool_call",
                        "tool": tool_call.get("name", "unknown"),
                        "input": tool_call.get("args", {}),
                    })

            # Tool results
            message_type = getattr(message, "type", "")

            if message_type == "tool":
                output = str(getattr(message, "content", ""))

                publish_event({
                    "type": "tool_result",
                    "tool": getattr(message, "name", "tool"),
                    "output": output[:3000],
                })

                continue

            # Agent response
            content = getattr(message, "content", "")

            if isinstance(content, str) and content.strip():
                publish_event({
                    "type": "agent",
                    "node": node_name,
                    "message": content,
                })


def event_stream():
    while True:
        try:
            event = event_queue.get(timeout=30)

            yield f"data: {json.dumps(event)}\n\n"

            if event.get("type") in {"complete", "error"}:
                break

        except Empty:
            yield ": keep-alive\n\n"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "status": job_status,
            "resume_exists": RESUME_PATH.exists(),
            "default_email": os.getenv("EMAIL_TO", ""),
        },
    )


@app.get("/events")
async def events():
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.post("/run")
async def run_agent_endpoint(
    resume: UploadFile | None = File(None),
    to_email: str = Form(...),
    additional_instructions: str = Form(""),
):
    global job_status

    if not to_email.strip():
        return HTMLResponse(
            """
            <div class="alert alert-error">
                <span>Email address is required.</span>
            </div>
            """,
            status_code=400,
        )

    # Replace saved resume if a new one was uploaded.
    if resume and resume.filename:
        if not resume.filename.lower().endswith(".pdf"):
            return HTMLResponse(
                """
                <div class="alert alert-error">
                    <span>Resume must be a PDF.</span>
                </div>
                """,
                status_code=400,
            )

        RESUME_PATH.parent.mkdir(parents=True, exist_ok=True)

        with RESUME_PATH.open("wb") as output:
            shutil.copyfileobj(resume.file, output)

    if not RESUME_PATH.exists():
        return HTMLResponse(
            """
            <div class="alert alert-error">
                <span>Please upload a resume first.</span>
            </div>
            """,
            status_code=400,
        )

    if not job_lock.acquire(blocking=False):
        return HTMLResponse(
            """
            <div class="alert alert-warning">
                <span>A job search is already running.</span>
            </div>
            """,
            status_code=409,
        )

    # Clear old events.
    while True:
        try:
            event_queue.get_nowait()
        except Empty:
            break

    job_status = "running"

    thread = threading.Thread(
        target=run_job,
        args=(
            str(RESUME_PATH.resolve()),
            to_email.strip(),
            additional_instructions.strip(),
        ),
        daemon=True,
    )

    thread.start()

    return HTMLResponse(
        """
        <div class="alert alert-success">
            <span>Agent started. Watch the activity below.</span>
        </div>
        """
    )


@app.get("/status")
async def status():
    return {
        "status": job_status,
        "resume_exists": RESUME_PATH.exists(),
    }