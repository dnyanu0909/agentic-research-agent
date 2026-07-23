"""
FastAPI server. Run with:  uvicorn main:app --reload
Then open static/index.html (served automatically at http://127.0.0.1:8000/)
"""

import json
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent import run_agent, stream_agent

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
def run_stream(goal: str):
    """Server-Sent Events endpoint: pushes each agent step to the
    browser the moment it happens, instead of waiting for the full run."""
    def event_generator():
        for update in stream_agent(goal):
            yield f"data: {json.dumps(update)}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve the frontend at http://127.0.0.1:8000/
app.mount("/", StaticFiles(directory="static", html=True), name="static")
