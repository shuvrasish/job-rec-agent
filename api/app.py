import json
import os
import shutil
import threading
import uuid
from pathlib import Path
from queue import Empty, Queue

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from agent.agent import run_agent_streaming


BASE_DIR = Path(__file__).resolve().parent.parent
RESUME_PATH = BASE_DIR / "resumes" / "resume.pdf"

app = FastAPI(title="Job Scout API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


runs: dict[str, dict] = {}
run_queues: dict[str, Queue] = {}
run_locks: dict[str, threading.Lock] = {}


def publish_event(run_id: str, event: dict):
    queue = run_queues.get(run_id)

    if queue:
        queue.put(event)


def process_agent_update(run_id: str, update: dict):
    for node_name, node_update in update.items():
        if not isinstance(node_update, dict):
            continue

        messages = node_update.get("messages", [])

        for message in messages:
            tool_calls = getattr(message, "tool_calls", None)

            if tool_calls:
                for tool_call in tool_calls:
                    publish_event(
                        run_id,
                        {
                            "type": "tool_call",
                            "tool": tool_call.get("name", "unknown"),
                            "input": tool_call.get("args", {}),
                        },
                    )

            message_type = getattr(message, "type", "")

            if message_type == "tool":
                publish_event(
                    run_id,
                    {
                        "type": "tool_result",
                        "tool": getattr(message, "name", "tool"),
                        "output": str(
                            getattr(message, "content", "")
                        )[:3000],
                    },
                )

                continue

            content = getattr(message, "content", "")

            if isinstance(content, str) and content.strip():
                publish_event(
                    run_id,
                    {
                        "type": "agent",
                        "node": node_name,
                        "message": content,
                    },
                )


def run_job(
    run_id: str,
    resume_path: str,
    to_email: str,
    additional_instructions: str,
):
    try:
        runs[run_id]["status"] = "running"

        publish_event(
            run_id,
            {
                "type": "status",
                "message": "Agent started",
            },
        )

        for update in run_agent_streaming(
            resume_path=resume_path,
            to_email=to_email,
            additional_instructions=additional_instructions,
        ):
            process_agent_update(run_id, update)

        runs[run_id]["status"] = "complete"

        publish_event(
            run_id,
            {
                "type": "complete",
                "message": "Job search completed successfully.",
            },
        )

    except Exception as e:
        runs[run_id]["status"] = "failed"
        runs[run_id]["error"] = str(e)

        publish_event(
            run_id,
            {
                "type": "error",
                "message": f"{type(e).__name__}: {e}",
            },
        )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/status")
def status():
    return {
        "status": "ready",
        "resume_exists": RESUME_PATH.exists(),
    }


@app.post("/api/runs")
async def create_run(
    resume: UploadFile | None = File(None),
    to_email: str = Form(...),
    additional_instructions: str = Form(""),
):
    if not to_email.strip():
        return {
            "error": "Email address is required."
        }

    if resume and resume.filename:
        if not resume.filename.lower().endswith(".pdf"):
            return {
                "error": "Resume must be a PDF."
            }

        RESUME_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with RESUME_PATH.open("wb") as output:
            shutil.copyfileobj(
                resume.file,
                output,
            )

    if not RESUME_PATH.exists():
        return {
            "error": "Please upload a resume first."
        }

    run_id = str(uuid.uuid4())

    runs[run_id] = {
        "id": run_id,
        "status": "starting",
        "error": None,
    }

    run_queues[run_id] = Queue()

    thread = threading.Thread(
        target=run_job,
        args=(
            run_id,
            str(RESUME_PATH.resolve()),
            to_email.strip(),
            additional_instructions.strip(),
        ),
        daemon=True,
    )

    thread.start()

    return {
        "run_id": run_id,
        "status": "starting",
    }


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    run = runs.get(run_id)

    if not run:
        return {
            "error": "Run not found."
        }

    return run


@app.get("/api/runs/{run_id}/events")
def run_events(run_id: str):
    if run_id not in run_queues:
        return {
            "error": "Run not found."
        }

    queue = run_queues[run_id]

    def event_stream():
        while True:
            try:
                event = queue.get(timeout=30)

                yield (
                    f"data: {json.dumps(event)}\n\n"
                )

                if event["type"] in {
                    "complete",
                    "error",
                }:
                    break

            except Empty:
                yield ": keep-alive\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )