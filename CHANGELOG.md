# Autonomous Research & Report Agent — Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] — 2026-08-21

### Added
- **Human-in-the-loop review step**: agent pauses at `review_node` after the
  self-critique pass and streams an `approval_required` event to the frontend;
  the user can approve or reject with optional feedback.
- `/resume-stream` endpoint to resume a paused LangGraph thread after human review.
- `wikipedia_lookup` tool for deeper summaries on specific named entities without
  burning additional DuckDuckGo quota.
- Intelligent "stuck" detection: agent is nudged to stop searching and write when
  it repeats the same action three times in a row.
- Budget warning injected into the prompt when `MAX_STEPS` is nearly exhausted.
- Relevance filtering on web search results to reduce hallucination from
  unrelated pages.
- Community files: `LICENSE`, `CONTRIBUTING.md`, issue templates, PR template,
  GitHub Actions CI, `CHANGELOG.md`, `.env.example`.
- Unit test suite under `tests/`.

### Changed
- `InMemorySaver` checkpointer moved to module level so thread state persists
  across `/run-stream` and `/resume-stream` in the same process.
- Report content is cleaned of markdown code fences before saving to disk.

### Fixed
- DuckDuckGo rate-limit handling now retries across `html` and `lite` backends
  before falling back to Wikipedia.

---

## [1.0.0] — 2026-08-18

### Added
- Initial ReAct-style agent loop (`Think → Act → Observe`) built with **LangGraph**.
- Tools: `web_search`, `calculator`, `write_report`.
- **Self-critique step**: agent evaluates its own draft report and revises if it
  does not meet the original goal.
- **FastAPI** backend with `/run` (synchronous) and `/run-stream` (SSE) endpoints.
- Terminal-style HTML/JS frontend — no build step, no framework.
- **Docker** support via `Dockerfile` and `docker-compose.yml`.
- Runs fully offline on local **Ollama** models — zero API costs.
- Reports auto-saved as `.md` files to the `reports/` folder.
