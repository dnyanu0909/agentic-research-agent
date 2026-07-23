# Autonomous Research & Report Agent

An agentic AI system that takes a research goal, plans its own steps,
calls tools (web search, calculator, file writer) to gather information,
writes a report, then **critiques and revises its own output** before
returning it — all running locally on Ollama, no paid API needed.

## Why this counts as "agentic AI"
- **Planning**: the agent decides its own next action at each step, it isn't a fixed pipeline.
- **Tool use**: it calls real tools (web search, calculator, file writer) and reacts to their output.
- **Autonomy**: it loops (Think → Act → Observe) until it decides the goal is met.
- **Self-improvement**: before finishing, it critiques its own draft report against the goal and revises if it falls short.

## Architecture

```
 goal
   │
   ▼
┌─────────┐   tool call    ┌──────────────┐
│  think  │ ─────────────▶ │ web_search    │
│ (LLM    │                │ calculator    │
│ decides │ ◀───────────── │ write_report  │
│ action) │   observation  └──────────────┘
└────┬────┘
     │ loops until action="finish" or max steps
     ▼
┌───────────┐
│ critique  │──▶ if gaps found, loop back to "think" with feedback
│ (self-    │
│  check)   │──▶ if good, END and return report
└───────────┘
```

Built with **LangGraph** (`agent.py`) as a small 2-node state graph, a
**FastAPI** backend (`main.py`), and a plain HTML/JS terminal-style
frontend (`static/index.html`) — no framework build step needed.

## Setup

1. **Install Ollama** (if you haven't): https://ollama.com
2. **Pull a model** (small + fast recommended for laptop demos):
   ```bash
   ollama pull llama3.1
   # or a smaller/faster option:
   ollama pull qwen2.5:7b
   ```
3. **Install Python deps**:
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. **Run the server**:
   ```bash
   uvicorn main:app --reload
   ```
5. Open **http://127.0.0.1:8000** in your browser and enter a goal, e.g.:
   > "Research the current state of agentic AI and summarize 3 real-world use cases"

Reports are also saved as `.md` files in the `reports/` folder.

To use a different local model: `set OLLAMA_MODEL=qwen2.5:7b` (or `export` on Mac/Linux) before running uvicorn.

## 4-Day Build Plan (mapped to this repo)

**Day 1 — Setup + understand the architecture**
- Install Ollama, pull a model, run `python agent.py "test goal"` from the terminal to confirm the loop works before touching the UI.
- Read through `agent.py` line by line — be ready to explain the think/act/critique loop in the viva.

**Day 2 — Get the core loop solid**
- Run 4-5 different goals through `agent.py` directly. Fix prompt issues if the model outputs bad JSON (tweak `SYSTEM_PROMPT` in `agent.py` if needed — smaller models sometimes need firmer instructions).
- Confirm `web_search`, `calculator`, and `write_report` all work individually (`python -c "from tools import web_search; print(web_search('test'))"`).

**Day 3 — Wire up the UI + the self-improvement step**
- Start the server, test the full flow through the browser.
- Verify the critique loop actually triggers a revision at least once during testing (try a vague goal to force it) — this is your strongest "agentic" talking point in the demo.

**Day 4 — Polish + submission prep**
- Write 2-3 example goals into your report/slides with screenshots of the mission log.
- Note any limitations honestly (small local models are less reliable at JSON output than GPT-4-class models — mention this as a real trade-off you evaluated, it reads well in a viva).
- Prepare the architecture diagram above for your slides.

## Known limitations (mention these — they show understanding, not weakness)
- Local models are smaller than GPT-4-class models, so JSON parsing occasionally fails; the agent retries automatically but isn't perfect.
- `MAX_STEPS` in `agent.py` caps the loop at 6 steps to guarantee termination — a real production agent would use a smarter stopping condition.
- Web search uses DuckDuckGo's free endpoint, which is unofficial and can rate-limit under heavy use.
