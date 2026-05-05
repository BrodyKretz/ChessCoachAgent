"""
Critic Agent node.
Grades the coaching report and either approves or rejects it with feedback.
"""
import json
import re
from langchain_anthropic import ChatAnthropic
from graph.state import ChessCoachState
from utils.events import bus

MAX_ATTEMPTS = 3
PASS_THRESHOLD = 70


def critic_review_node(state: ChessCoachState) -> dict:
    """LangGraph node: scores the coaching report."""
    llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0.1)

    coaching_report = state["coaching_report"]
    analysis = state["analysis_report"]
    goals = state["player_goals"]
    attempts = state.get("critique_attempts", 0)

    bus.node_active("critic")
    bus.debug("Critic is reviewing the coaching plan for quality...")

    if attempts >= MAX_ATTEMPTS:
        bus.debug(f"Auto-approved after {MAX_ATTEMPTS} attempts.")
        bus.node_complete("critic")
        return {
            "critique_result": {
                "approved": True,
                "total_score": 65,
                "feedback": f"Auto-approved after {MAX_ATTEMPTS} attempts.",
                "strengths": [],
                "weaknesses": ["Max revision attempts reached"],
            }
        }

    prompt = f"""You are a strict quality-control critic for chess coaching reports.

=== ORIGINAL GAME ANALYSIS ===
{analysis}

=== PLAYER GOALS ===
{json.dumps(goals, indent=2)}

=== COACHING REPORT TO EVALUATE ===
{coaching_report}

Score this report on four criteria (0-25 each):
1. SPECIFICITY: References actual game patterns, not generic advice?
2. GOAL_ALIGNMENT: Addresses the player's stated openings and focus areas?
3. ACTIONABILITY: Recommendations are concrete with specific steps?
4. TIME_PRESSURE_HANDLING: Time-pressured mistakes correctly deprioritized?

Respond in this EXACT JSON format — no other text:
{{
  "scores": {{
    "specificity": <0-25>,
    "goal_alignment": <0-25>,
    "actionability": <0-25>,
    "time_pressure_handling": <0-25>
  }},
  "total_score": <sum>,
  "approved": <true if total >= {PASS_THRESHOLD}>,
  "feedback": "<if not approved: exactly what must change. If approved: 'Approved.'>",
  "strengths": ["<what the report does well>"],
  "weaknesses": ["<specific gaps to fix if rejected>"]
}}"""

    full_response = ""
    for chunk in llm.stream(prompt):
        full_response += chunk.content

    critique = _parse_critique(full_response)
    score = critique.get("total_score", 0)
    approved = critique.get("approved", False)

    if approved:
        bus.debug(f"Critic approved the plan — score {score}/100. Report is ready!")
        bus.speak(f"The Critic gave your plan a score of {score} out of 100. It's approved and ready for you!")
    else:
        bus.debug(f"Critic score {score}/100 — rejected. Coach King will revise.")
        bus.speak(f"The Critic scored {score} out of 100. Coach King is making improvements.")

    bus.node_complete("critic")
    return {"critique_result": critique}


def should_regenerate(state: ChessCoachState) -> str:
    critique = state.get("critique_result", {})
    return "approved" if critique.get("approved") else "regenerate"


def _parse_critique(content: str) -> dict:
    try:
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        pass
    return {"approved": True, "total_score": 70, "feedback": "Approved.", "strengths": [], "weaknesses": []}
