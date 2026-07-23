"""
FastAPI server. Run with:  uvicorn main:app --reload
Then open static/index.html (served automatically at http://127.0.0.1:8000/)
"""

import json
import uuid
from fastapi import FastAPI, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent import run_agent, stream_agent, resume_stream_agent

app = FastAPI(title="Autonomous Research & Report Agent")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


class GoalRequest(BaseModel):
    goal: str


@app.post("/run")
def run(req: GoalRequest):
    result = run_agent(req.goal)
    return {
        "goal": req.goal,
        "steps": result["history"],
        "report": result["draft_report"],
        "final_message": result.get("final_message", ""),
    }


@app.get("/run-stream")
def run_stream(goal: str, thread_id: str = None):
    """Server-Sent Events endpoint: pushes each agent step to the
    browser the moment it happens. Generates a thread_id if not supplied
    so the frontend can resume the same thread via /resume-stream."""
    tid = thread_id or str(uuid.uuid4())
    def event_generator():
        for update in stream_agent(goal, tid):
            yield f"data: {json.dumps(update)}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/resume-stream")
def resume_stream_endpoint(
    thread_id: str = Body(...),
    approved: bool = Body(...),
):
    """Resumes a graph suspended at review_node.
    Pass approved=true to finalise the report, false to send it back
    for revision."""
    def event_generator():
        for update in resume_stream_agent(thread_id, approved):
            yield f"data: {json.dumps(update)}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve the frontend at http://127.0.0.1:8000/
app.mount("/", StaticFiles(directory="static", html=True), name="static")
