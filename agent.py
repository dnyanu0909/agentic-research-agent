"""
Autonomous Research & Report Agent
-----------------------------------
A ReAct-style agent built with LangGraph, running entirely on a local
Ollama model (no API keys, no cost).

Loop:  Think -> Act (call a tool) -> Observe -> Think again ... -> Finish
Self-check: before finishing, the agent critiques its own draft report
against the original goal and revises once if it falls short.

This is intentionally a small, readable graph (3 nodes) rather than a
huge framework-heavy build — easy to explain in a viva and easy to demo.
"""

import os
import json
import re
from typing import TypedDict, List, Dict, Any

from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END

from tools import TOOL_REGISTRY, TOOL_DESCRIPTIONS, write_report

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mistral")
MAX_STEPS = 14  # safety cap so the agent can't loop forever

llm = ChatOllama(model=OLLAMA_MODEL, temperature=0.2)


class AgentState(TypedDict):
    goal: str
    history: List[Dict[str, Any]]   # trace of {thought, action, action_input, observation}
    draft_report: str
    step_count: int
    critiqued: bool
    finished: bool
    final_message: str


def _detect_required_count(goal: str):
    """Look for patterns like '3 real-world use cases' in the goal so we
    can enforce that many distinct, separated items in the final report
    instead of letting the model lump them into one vague paragraph."""
    match = re.search(
        r'\b(\d+)\s+(?:real[- ]world\s+)?([a-zA-Z][a-zA-Z\- ]{2,30}?)(?:\.|,|$|\band\b)',
        goal, re.IGNORECASE
    )
    if match:
        count = int(match.group(1))
        noun = match.group(2).strip()
        if 1 < count <= 10:
            return count, noun
    return None, None


SYSTEM_PROMPT = f"""You are an autonomous agent that accomplishes a research goal
step by step by calling tools. You must always reply with ONLY a JSON object,
no other text, in this exact shape:

{{"thought": "<your reasoning about what to do next>",
  "action": "<one of: web_search, calculator, write_report, finish>",
  "action_input": "<the input for that action>"}}

Available tools:
{TOOL_DESCRIPTIONS}

Rules:
- Use web_search to gather facts before writing anything.
- Use write_report ONLY once you have gathered enough information from at
  least one successful web_search. Pass the full report text as
  action_input in the form "filename.md ||| report content".
- The report content MUST follow this structure (Markdown):
    # <Clear, specific title based on the goal>

    ## Summary
    2-3 sentence overview answering the goal directly.

    ## <Section per sub-topic or finding>
    Write in full sentences, not a copy of search snippets. Explain each
    point in your own words. Use one section per distinct sub-topic —
    do not cram everything into one paragraph.

    ## Sources
    A bullet list of the URLs you actually gathered information from
    during web_search (never invent a URL you did not see in an
    observation).
- Use action "finish" only after write_report has succeeded.
- If the goal asks for a specific number of items (e.g. "3 use cases"),
  research and describe EACH one separately — run a distinct search per
  item if needed, don't compress them into one paragraph.
- Use wikipedia_lookup when you want a fuller summary on ONE specific
  entity web_search already surfaced, instead of another generic search.
"""


def _stuck_hint(history: List[Dict[str, Any]]) -> str:
    if len(history) < 2:
        return ""

    # Case 1: two consecutive same-action steps that both reported errors
    last_two = history[-2:]
    same_action = last_two[0]["action"] == last_two[1]["action"]
    both_failed = all(
        any(kw in h["observation"].lower() for kw in ["failed", "unavailable", "rate limit", "error"])
        for h in last_two
    )
    if same_action and both_failed:
        return (
            "\nIMPORTANT: Your last two attempts at the same action both "
            "failed. Do NOT repeat the same query again. Either try a "
            "meaningfully different query, switch to a different tool, "
            "or if you already have enough information, move on to "
            "write_report using what you know so far (state clearly in "
            "the report if some information could not be verified live)."
        )

    # Case 2: 3 or more consecutive web_searches with no write_report yet
    has_report = any(h["action"] == "write_report" for h in history)
    if not has_report:
        tail = history[-3:]
        if len(tail) == 3 and all(h["action"] == "web_search" for h in tail):
            return (
                "\nIMPORTANT: You have run 3 web_searches in a row without "
                "writing the report. You likely have enough information now. "
                "Stop searching and call write_report with everything you "
                "have gathered so far. Do not search again unless a critical "
                "piece of information is completely missing."
            )
    return ""


def _ask_llm(state: AgentState) -> Dict[str, Any]:
    history_text = "\n".join(
        f"Step {i+1}: thought={h['thought']!r} action={h['action']} "
        f"input={h['action_input']!r} observation={h['observation'][:300]!r}"
        for i, h in enumerate(state["history"])
    )
    count, noun = _detect_required_count(state["goal"])
    count_hint = ""
    if count:
        count_hint = (
            f"\nThe goal specifically asks for {count} {noun}. Research "
            f"and report on EACH of the {count} separately — the final "
            f"report body must contain exactly {count} distinct, clearly "
            f"separated '##' subsections for these, not one combined "
            f"paragraph."
        )
    steps_left = MAX_STEPS - state["step_count"]
    budget_warning = ""
    if steps_left <= 4 and not any(h["action"] == "write_report" for h in state["history"]):
        budget_warning = (
            f"\nURGENT: Only {steps_left} step(s) remaining before the "
            f"hard limit. You MUST call write_report on the very next "
            f"step using everything gathered so far — do not search again."
        )
    prompt = (
        f"{SYSTEM_PROMPT}\n\nGoal: {state['goal']}\n"
        f"{count_hint}\n\n"
        f"History so far:\n{history_text or '(none yet)'}"
        f"{_stuck_hint(state['history'])}"
        f"{budget_warning}\n\n"
        f"What is the next step? Respond with JSON only."
    )
    response = llm.invoke(prompt)
    text = response.content.strip()
    # Be forgiving if the model wraps JSON in markdown fences
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {"thought": "Could not parse a plan; retrying.", "action": "web_search",
                "action_input": state["goal"]}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"thought": "JSON parse error; retrying search.", "action": "web_search",
                "action_input": state["goal"]}


def think_node(state: AgentState) -> AgentState:
    decision = _ask_llm(state)
    action = decision.get("action", "web_search")
    action_input = decision.get("action_input", state["goal"])
    thought = decision.get("thought", "")

    if action == "finish":
        state["finished"] = True
        state["final_message"] = thought
        return state

    if action == "write_report":
        # action_input format: "filename ||| content"
        if "|||" in action_input:
            filename, content = action_input.split("|||", 1)
        else:
            filename, content = "report.md", action_input
        observation = write_report(filename.strip(), content.strip())
        state["draft_report"] = content.strip()
    elif action in TOOL_REGISTRY:
        observation = TOOL_REGISTRY[action](action_input)
    else:
        observation = f"Unknown action '{action}', skipping."

    state["history"].append({
        "thought": thought, "action": action,
        "action_input": action_input, "observation": observation,
    })
    state["step_count"] += 1
    return state


def critique_node(state: AgentState) -> AgentState:
    """One self-check pass on the draft report before we truly finish —
    this is the 'self-improving' piece of the agent."""
    if state["critiqued"] or not state["draft_report"]:
        state["finished"] = True
        return state

    count, noun = _detect_required_count(state["goal"])
    count_note = ""
    if count:
        count_note = (
            f" (3) The goal asked for {count} {noun} specifically — "
            f"confirm the report has exactly {count} distinct, clearly "
            f"separated subsections covering these, not fewer and not "
            f"merged together."
        )

    prompt = (
        f"Goal: {state['goal']}\n\nDraft report:\n{state['draft_report']}\n\n"
        "Check these things: (1) Does this report fully and accurately "
        "address the goal? (2) Does it follow the required structure — a "
        "'# Title', a '## Summary', clearly separated '##' sections per "
        "sub-topic written in full sentences (not raw copied snippets), "
        f"and a '## Sources' list?{count_note} "
        "Reply with ONLY 'GOOD' if all are true, or a short specific "
        "instruction for what to fix if not."
    )
    verdict = llm.invoke(prompt).content.strip()
    state["critiqued"] = True

    if verdict.upper().startswith("GOOD"):
        state["finished"] = True
        state["final_message"] = "Report approved by self-critique step."
    else:
        # Feed the critique back in as a new goal note so the agent
        # revises the report on its next loop instead of stopping.
        state["history"].append({
            "thought": "Self-critique found gaps; revising.",
            "action": "critique", "action_input": "", "observation": verdict,
        })
        state["finished"] = False
    return state


def route_after_think(state: AgentState) -> str:
    if state["finished"]:
        return "critique"
    if state["step_count"] >= MAX_STEPS:
        return "critique"
    return "think"


def route_after_critique(state: AgentState) -> str:
    return END if state["finished"] else "think"


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("think", think_node)
    graph.add_node("critique", critique_node)
    graph.set_entry_point("think")
    graph.add_conditional_edges("think", route_after_think, {"think": "think", "critique": "critique"})
    graph.add_conditional_edges("critique", route_after_critique, {"think": "think", END: END})
    return graph.compile()


def run_agent(goal: str) -> Dict[str, Any]:
    app = build_graph()
    initial_state: AgentState = {
        "goal": goal, "history": [], "draft_report": "",
        "step_count": 0, "critiqued": False, "finished": False, "final_message": "",
    }
    result = app.invoke(initial_state, {"recursion_limit": 50})
    return result


def stream_agent(goal: str):
    """Like run_agent, but yields each step the moment it happens instead
    of waiting for the whole graph to finish. Used by the /run-stream
    endpoint so the UI can show the agent thinking live."""
    app = build_graph()
    initial_state: AgentState = {
        "goal": goal, "history": [], "draft_report": "",
        "step_count": 0, "critiqued": False, "finished": False, "final_message": "",
    }
    seen = 0
    latest_state = initial_state
    for latest_state in app.stream(initial_state, {"recursion_limit": 50}, stream_mode="values"):
        history = latest_state.get("history", [])
        while seen < len(history):
            yield {"type": "step", "step": history[seen]}
            seen += 1
    yield {
        "type": "final",
        "report": latest_state.get("draft_report", ""),
        "final_message": latest_state.get("final_message", ""),
    }


if __name__ == "__main__":
    import sys
    goal = " ".join(sys.argv[1:]) or "Research the basics of agentic AI and write a short report."
    final = run_agent(goal)
    print(json.dumps(final, indent=2))
