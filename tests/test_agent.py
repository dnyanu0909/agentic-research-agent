"""
Smoke tests for agent.py and main.py

These tests use mocking to avoid needing a live Ollama instance, so they
run cleanly in CI.  They verify the graph structure and API endpoints are
wired up correctly without performing any real LLM inference.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


# ─── FastAPI endpoint smoke tests ────────────────────────────────────────────

class TestAPIEndpoints:
    """Tests the FastAPI app endpoints without a real Ollama connection."""

    def _get_client(self):
        from main import app
        return TestClient(app)

    def test_health_endpoint(self):
        client = self._get_client()
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_run_endpoint_with_mock_agent(self):
        """POST /run should call run_agent and return structured JSON."""
        mock_result = {
            "history": [
                {
                    "thought": "I need to search for this.",
                    "action": "web_search",
                    "action_input": "test goal",
                    "observation": "Some results here.",
                }
            ],
            "draft_report": "# Test Report\n\nContent.",
            "final_message": "Report approved.",
        }
        with patch("main.run_agent", return_value=mock_result) as mock_run:
            client = self._get_client()
            response = client.post(
                "/run",
                json={"goal": "test research goal"},
            )
        assert response.status_code == 200
        body = response.json()
        assert body["goal"] == "test research goal"
        assert "steps" in body
        assert "report" in body
        mock_run.assert_called_once_with("test research goal")

    def test_run_endpoint_missing_goal_returns_422(self):
        """POST /run without a goal body should return 422 Unprocessable Entity."""
        client = self._get_client()
        response = client.post("/run", json={})
        assert response.status_code == 422


# ─── Agent graph structure tests ─────────────────────────────────────────────

class TestAgentGraph:
    """Tests the LangGraph graph is compiled correctly without LLM calls."""

    def test_build_graph_returns_compiled_graph(self):
        from agent import build_graph
        graph = build_graph()
        # The compiled graph should have an invoke method
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "stream")
        assert hasattr(graph, "get_state")

    def test_agent_state_keys(self):
        """AgentState TypedDict should have all required keys."""
        from agent import AgentState
        required_keys = {
            "goal", "history", "draft_report",
            "step_count", "critiqued", "finished",
            "final_message", "user_approved",
        }
        # TypedDict stores annotations in __annotations__
        assert required_keys.issubset(set(AgentState.__annotations__.keys()))


# ─── _detect_required_count ─────────────────────────────────────────────────

class TestDetectRequiredCount:
    def test_detects_count_in_goal(self):
        from agent import _detect_required_count
        count, noun = _detect_required_count(
            "Research the current state of agentic AI and summarize 3 real-world use cases"
        )
        assert count == 3
        assert "use cases" in noun.lower() or "real" in noun.lower()

    def test_returns_none_for_no_count(self):
        from agent import _detect_required_count
        count, noun = _detect_required_count("Research agentic AI trends")
        assert count is None
        assert noun is None

    def test_ignores_count_over_10(self):
        from agent import _detect_required_count
        count, noun = _detect_required_count("List 50 examples of X")
        assert count is None
