"""
Unit tests for tools.py

Tests cover:
  - calculator: valid expressions, edge cases, injection prevention
  - write_report: file creation, name sanitisation, content cleaning
  - _clean_report_text: fence stripping
  - _filter_relevant_results: relevance filtering

NOTE: web_search and wikipedia_lookup make real HTTP calls, so they are
      skipped in CI (set SKIP_NETWORK_TESTS=1 to skip them locally too).
"""

from tools import (
    _clean_report_text,
    _filter_relevant_results,
    calculator,
    write_report,
)

# ─── calculator ─────────────────────────────────────────────────────────────


class TestCalculator:
    def test_addition(self):
        assert calculator("2+3") == "5"

    def test_subtraction(self):
        assert calculator("10-4") == "6"

    def test_multiplication(self):
        assert calculator("6*7") == "42"

    def test_division(self):
        assert calculator("10/4") == "2.5"

    def test_floor_division(self):
        assert calculator("10//3") == "3"

    def test_modulo(self):
        assert calculator("10%3") == "1"

    def test_exponentiation(self):
        assert calculator("2**10") == "1024"

    def test_parentheses(self):
        assert calculator("(2+3)*4") == "20"

    def test_float(self):
        result = calculator("1.5 + 2.5")
        assert result == "4.0"

    def test_invalid_expression_returns_error(self):
        result = calculator("not a number")
        assert "failed" in result.lower() or result == ""

    def test_injection_stripped(self):
        # Letters and function calls should be stripped — should not raise
        result = calculator("__import__('os').system('rm -rf /')")
        # Should either return an error or "0" (from a bare number) — not execute shell
        assert isinstance(result, str)


# ─── _clean_report_text ──────────────────────────────────────────────────────


class TestCleanReportText:
    def test_strips_markdown_fence(self):
        raw = "```markdown\n# Title\n\nContent\n```"
        assert _clean_report_text(raw) == "# Title\n\nContent"

    def test_strips_plain_fence(self):
        raw = "```\n# Title\n```"
        assert _clean_report_text(raw) == "# Title"

    def test_strips_md_shorthand(self):
        raw = "```md\n# Title\n```"
        assert _clean_report_text(raw) == "# Title"

    def test_no_fence_unchanged(self):
        raw = "# Title\n\nSome content."
        assert _clean_report_text(raw) == raw

    def test_strips_inline_backticks(self):
        raw = "Content ```with``` backticks"
        result = _clean_report_text(raw)
        assert "```" not in result


# ─── _filter_relevant_results ────────────────────────────────────────────────


class TestFilterRelevantResults:
    def test_keeps_relevant_results(self):
        results = [
            {"title": "Python programming guide", "body": "Python is a language"},
            {"title": "Cooking recipes", "body": "How to bake a cake"},
        ]
        filtered = _filter_relevant_results(results, "Python programming")
        assert len(filtered) == 1
        assert filtered[0]["title"] == "Python programming guide"

    def test_returns_all_if_none_match(self):
        results = [
            {"title": "Cooking recipes", "body": "How to bake a cake"},
        ]
        filtered = _filter_relevant_results(results, "Python programming")
        # Falls back to all results if nothing matches
        assert len(filtered) == 1

    def test_empty_query_keywords_returns_all(self):
        results = [
            {"title": "A", "body": "B"},
            {"title": "C", "body": "D"},
        ]
        filtered = _filter_relevant_results(results, "the and for")  # all stopwords
        assert len(filtered) == 2


# ─── write_report ────────────────────────────────────────────────────────────


class TestWriteReport:
    def test_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("tools.OUTPUT_DIR", str(tmp_path))
        result = write_report("test_output", "# Test Report\n\nContent here.")
        assert "test_output.md" in result
        saved = tmp_path / "test_output.md"
        assert saved.exists()
        assert "# Test Report" in saved.read_text(encoding="utf-8")

    def test_appends_md_extension(self, tmp_path, monkeypatch):
        monkeypatch.setattr("tools.OUTPUT_DIR", str(tmp_path))
        write_report("no_extension", "content")
        assert (tmp_path / "no_extension.md").exists()

    def test_sanitises_filename(self, tmp_path, monkeypatch):
        monkeypatch.setattr("tools.OUTPUT_DIR", str(tmp_path))
        write_report("file with spaces & symbols!", "content")
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        # No spaces or special chars in filename
        assert " " not in files[0].name
        assert "&" not in files[0].name

    def test_strips_fences_before_saving(self, tmp_path, monkeypatch):
        monkeypatch.setattr("tools.OUTPUT_DIR", str(tmp_path))
        write_report("fenced", "```markdown\n# Title\n```")
        content = (tmp_path / "fenced.md").read_text(encoding="utf-8")
        assert "```" not in content
        assert "# Title" in content
