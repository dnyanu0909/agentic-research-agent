# Autonomous Local Deep Research Agent

An autonomous, stateful deep research agent powered by **LangGraph**, local **Ollama** LLMs, **FastAPI** Server-Sent Events (SSE) streaming, and **Human-in-the-Loop (HITL)** governance.

Runs 100% locally with zero cloud API dependencies, complete data privacy, and zero token costs.

---

## 📋 Overview

Standard AI research agents heavily rely on third-party cloud APIs, introducing data privacy risks, high per-token costs, and frequent context hallucinations when web search results contain keyword false positives. 

This project delivers a **privacy-first, zero-cost alternative**. It executes multi-step web research, filters false-positive search context via deterministic keyword overlap algorithms, sanitizes formatting artifacts, performs strict self-critique, and pauses execution for human approval before saving generated reports to disk.

---

## 🔑 Key Features

* **Zero-API-Cost Infrastructure:** Runs entirely on local open-weights models via Ollama (`mistral`).
* **Deterministic Search Relevance Filtering:** Drops irrelevant web search snippets using non-stopword keyword matching before LLM context ingestion to prevent context hallucinations.
* **Output Sanitization Engine:** Automatically strips raw markdown code fences (` ```markdown ` / ` ``` `) across state updates and disk I/O layers.
* **Multi-Criteria Self-Critique:** Reflects on draft reports to enforce clean formatting, anachronism detection/fact-checking, and exact structural requirements (e.g., item counts).
* **Human-in-the-Loop (HITL) Interrupts:** Uses LangGraph state interruption (`interrupt()`) to pause execution after self-critique, streaming an interactive review card to the browser UI for approval or rejection.
* **Real-Time Event Streaming:** Streams live ReAct thinking logs and report previews over FastAPI Server-Sent Events (SSE).
* **Containerized Deployment:** Fully orchestrated via Docker Compose for single-command startup.

---

## 🛠️ Tech Stack

* **Backend Framework:** Python 3.11, FastAPI, Uvicorn, Pydantic
* **Agentic State Machine:** LangGraph, LangChain-Ollama
* **Local Inference Runtime:** Ollama (Mistral 7B)
* **Containerization:** Docker, Docker Compose
* **Frontend UI:** HTML5, Vanilla JavaScript (Fetch ReadableStream API), Tailwind CSS

---

## 📂 Project Architecture & Workflow

```text
[ think_node ] ──> (Deterministic Search Filter) ──> [ critique_node ]
                                                            │
                                                     (Passes Rules)
                                                            │
                                                            ▼
                                                [ review_node (interrupt) ]
                                                            │
                                            ┌───────────────┴───────────────┐
                                      (Approved)                       (Rejected)
                                            │                               │
                                            ▼                               ▼
                                     [ write_report ]               [ think_node ]
                                  (Saves report to disk)         (Revises with feedback)
