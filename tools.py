"""
Tools available to the agent.
Each tool is a plain Python function with a clear docstring — the agent
picks which one to call and with what arguments (see agent.py).
"""

import os
import re
import ast
import time
import operator as op
import requests
from duckduckgo_search import DDGS
try:
    from duckduckgo_search.exceptions import RatelimitException, DuckDuckGoSearchException
except ImportError:
    class RatelimitException(Exception):
        pass
    class DuckDuckGoSearchException(Exception):
        pass

# Where generated reports get saved
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)

_SEARCH_CACHE = {}


def _wikipedia_fallback(query: str) -> str:
    """Free, keyless fallback for factual queries when DDG is throttling."""
    try:
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query", "list": "search", "srsearch": query,
                "format": "json", "srlimit": 3,
            },
            timeout=8,
            headers={"User-Agent": "research-agent-demo/1.0"},
        )
        hits = resp.json().get("query", {}).get("search", [])
        if not hits:
            return ""
        lines = []
        for h in hits:
            title = h.get("title", "")
            snippet = re.sub("<[^>]+>", "", h.get("snippet", ""))
            url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
            lines.append(f"- {title}: {snippet}\n  Source: {url}")
        return "Wikipedia fallback results:\n" + "\n".join(lines)
    except Exception:
        return ""


def web_search(query: str, max_results: int = 5) -> str:
    """Search the web; retries across backends on rate limits, falls
    back to Wikipedia if all of them fail."""
    if query in _SEARCH_CACHE:
        return _SEARCH_CACHE[query] + "\n(repeated query — reusing previous result, try a different query instead)"

    backends = ["html", "lite"]
    last_error = "unknown error"

    for backend in backends:
        for attempt in range(2):
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=max_results, backend=backend))
                if results:
                    lines = []
                    for i, r in enumerate(results, 1):
                        title = r.get("title", "")
                        body = r.get("body", "")
                        href = r.get("href", "")
                        lines.append(f"{i}. {title}\n   {body}\n   Source: {href}")
                    formatted = "\n".join(lines)
                    _SEARCH_CACHE[query] = formatted
                    return formatted
            except RatelimitException:
                last_error = f"rate limited ({backend})"
                time.sleep(2 * (attempt + 1))
            except Exception as e:
                last_error = str(e)
                time.sleep(1)

    fallback = _wikipedia_fallback(query)
    if fallback:
        _SEARCH_CACHE[query] = fallback
        return fallback

    result = (f"Web search unavailable right now ({last_error}). "
              f"Do not retry this exact query — either rephrase it once, "
              f"or proceed using general knowledge and note that live "
              f"search was unavailable.")
    _SEARCH_CACHE[query] = result
    return result


# --- Safe calculator (no eval()) ---------------------------------------

_ALLOWED_OPS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
    ast.Div: op.truediv, ast.Pow: op.pow, ast.USub: op.neg,
    ast.Mod: op.mod, ast.FloorDiv: op.floordiv,
}


def _eval_node(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("Unsupported expression")


def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression safely, e.g. '(12+8)*3/2'.
    Supports + - * / // % ** and parentheses. No variables or functions."""
    try:
        cleaned = re.sub(r"[^0-9\.\+\-\*\/\%\(\)\s]", "", expression)
        tree = ast.parse(cleaned, mode="eval")
        result = _eval_node(tree.body)
        return str(result)
    except Exception as e:
        return f"Calculation failed: {e}"


def write_report(filename: str, content: str) -> str:
    """Write the final report/content to a text file in the reports/
    folder and return the path it was saved to."""
    safe_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", filename)
    if not safe_name.endswith(".md"):
        safe_name += ".md"
    path = os.path.join(OUTPUT_DIR, safe_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Report saved to {path}"


def wikipedia_lookup(topic: str) -> str:
    """Fetch a fuller summary of ONE specific topic/entity from Wikipedia.
    Use this to go deeper on something web_search already surfaced,
    rather than repeating a generic web_search on the same subject."""
    try:
        resp = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic.strip().replace(' ', '_')}",
            timeout=8,
            headers={"User-Agent": "research-agent-demo/1.0"},
        )
        if resp.status_code != 200:
            return f"No Wikipedia page found for '{topic}'."
        data = resp.json()
        extract = data.get("extract", "")
        url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
        if not extract:
            return f"No summary available for '{topic}'."
        return f"{extract}\nSource: {url}"
    except Exception as e:
        return f"Wikipedia lookup failed: {e}"


# Registry the agent uses to look up tools by name
TOOL_REGISTRY = {
    "web_search": web_search,
    "wikipedia_lookup": wikipedia_lookup,
    "calculator": calculator,
    "write_report": write_report,
}

TOOL_DESCRIPTIONS = """\
- web_search(query: str) -> search the web for information
- wikipedia_lookup(topic: str) -> get a fuller summary of ONE specific topic/entity (use after web_search surfaces a name worth digging into)
- calculator(expression: str) -> evaluate a math expression
- write_report(filename: str, content: str) -> save the final report to disk
"""
