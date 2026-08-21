# Contributing to Autonomous Research & Report Agent

Thank you for considering contributing! This project is a solo learning project
that is now open to community improvements. Please read the guidelines below
before submitting anything.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)

---

## Code of Conduct

Be respectful, constructive, and welcoming. Harassment of any kind will not be
tolerated.

---

## How Can I Contribute?

### 🐛 Reporting Bugs

Use the [Bug Report](.github/ISSUE_TEMPLATE/bug_report.md) issue template.
Please include:
- Your OS and Python version
- The Ollama model you're using
- Steps to reproduce
- What you expected vs. what happened

### 💡 Suggesting Features

Use the [Feature Request](.github/ISSUE_TEMPLATE/feature_request.md) template.

### 🔧 Submitting Code

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/your-feature-name`
3. Make your changes
4. Run tests: `pytest tests/`
5. Open a Pull Request against `main`

---

## Development Setup

```bash
# 1. Clone your fork
git clone https://github.com/<your-username>/agentic-research-agent.git
cd agentic-research-agent

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install runtime + dev dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Copy environment config
cp .env.example .env
# Edit .env to set your preferred Ollama model

# 5. Make sure Ollama is running
ollama serve
ollama pull mistral

# 6. Run tests
pytest tests/ -v

# 7. Lint your code
ruff check .
```

---

## Pull Request Process

1. Make sure all tests pass (`pytest tests/`)
2. Make sure there are no lint errors (`ruff check .`)
3. Update `CHANGELOG.md` under the `[Unreleased]` section
4. Fill out the PR template fully
5. Link any related issues in the PR description

---

## Coding Standards

- **Style**: Follow PEP 8. We use `ruff` for linting — run `ruff check .` before committing.
- **Docstrings**: All public functions must have a docstring.
- **Type hints**: Use type hints for all function signatures.
- **Tests**: New tools or agent behaviours should come with a test in `tests/`.
- **No secrets in code**: Never hardcode API keys or tokens. Use `.env` / environment variables.

---

## Project Structure Quick Reference

```
agent.py       — LangGraph graph definition, think/critique/review nodes
tools.py       — Tool implementations (web_search, calculator, write_report, wikipedia_lookup)
main.py        — FastAPI server (endpoints + SSE streaming)
static/        — Plain HTML/JS frontend (no build step)
tests/         — Pytest unit tests
reports/       — Generated research reports (auto-created, git-ignored)
```
