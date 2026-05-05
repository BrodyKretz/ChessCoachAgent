"""
LangGraph pipeline.

Two entry points:
  run_coaching_session()      — CLI mode (uses terminal input/output)
  run_coaching_session_web()  — Web mode (uses EventBus → WebSocket)

Web mode graph skips memory_check and analyst_interview nodes
(those are handled by the FastAPI server + frontend form).
"""
import os
from datetime import datetime
from langgraph.graph import StateGraph, END, START

from graph.state import ChessCoachState
from agents.analyst import analyze_games_node
from agents.coach import coach_interview_node, generate_lesson_node
from agents.critic import critic_review_node, should_regenerate
from memory.user_store import get_user, save_user, update_last_session
from tools.chess_api import validate_user, fetch_recent_games
from tools.pgn_parser import parse_game
from utils.pdf_generator import generate_coaching_pdf
from utils.events import bus


# ---------------------------------------------------------------------------
# Utility nodes
# ---------------------------------------------------------------------------

def memory_check_node(state: ChessCoachState) -> dict:
    """CLI only — web mode handles this in api/session.py."""
    from utils.character import show_coach, coach_says
    show_coach()

    coach_says(
        "Hey there! I'm Coach King, your personal chess mentor. "
        "Let's start by linking your Chess.com account.",
        speak=True,
    )

    raw = input("\n  Enter your Chess.com username: ").strip()
    print(f"  Checking Chess.com for '{raw}'...")
    profile = validate_user(raw)

    if profile is None:
        from utils.character import coach_says as cs
        cs(f"Hmm, I couldn't find '{raw}' on Chess.com. Let's try again.")
        raw = input("  Re-enter username: ").strip()
        profile = validate_user(raw)
        if profile is None:
            raise ValueError(f"Username '{raw}' not found on Chess.com.")

    username = raw
    existing = get_user(username)
    if existing:
        user_data = dict(existing)
        coach_says(f"Welcome back, {username}! I've loaded your saved preferences.", speak=True)
    else:
        save_user(username)
        user_data = {}
        coach_says(f"Great to meet you, {username}! Your account is now linked.", speak=True)

    update_last_session(username)
    return {"username": username, "is_returning_user": bool(existing), "user_data": user_data}


def analyst_interview_node(state: ChessCoachState) -> dict:
    """CLI only — web mode receives these values from the frontend form."""
    from utils.character import coach_says
    coach_says("Now let's set up the analysis. How deep do we dig?")

    raw = input(f"\n  How many recent games to analyze? [default: 10]: ").strip()
    try:
        num_games = max(1, min(int(raw) if raw else 10, 50))
    except ValueError:
        num_games = 10

    user_data = state.get("user_data", {})
    saved_tc = user_data.get("preferred_time_control", "all")
    print(f"\n  Time control? [saved: {saved_tc}]")
    print("  1=blitz  2=bullet  3=rapid  4=daily  5=all")
    raw = input("  > ").strip()
    tc_map = {"1": "blitz", "2": "bullet", "3": "rapid", "4": "daily", "5": "all"}
    time_control = tc_map.get(raw, saved_tc or "all")

    coach_says(
        f"Perfect. I'll analyze your last {num_games} {time_control} games. "
        "Give me a moment to pull them from Chess.com."
    )
    return {"num_games": num_games, "time_control": time_control}


def fetch_games_node(state: ChessCoachState) -> dict:
    """Fetch games from Chess.com and parse PGNs."""
    username = state["username"]
    time_control = state["time_control"]
    num_games = state["num_games"]

    bus.node_active("fetch")
    bus.debug(f"Fetching {num_games} {time_control} games from Chess.com...")

    raw_games = fetch_recent_games(username, time_control, num_games)

    if not raw_games:
        bus.debug(f"No {time_control} games found in the last 6 months.")
        bus.node_complete("fetch")
        return {"raw_games": [], "game_summaries": []}

    bus.debug(f"Found {len(raw_games)} games. Parsing PGN data...")

    summaries = []
    for game in raw_games:
        pgn = game.get("pgn", "")
        if not pgn:
            continue
        parsed = parse_game(pgn, username)
        if parsed:
            parsed["time_class"] = game.get("time_class", "unknown")
            summaries.append(parsed)

    bus.debug(f"Parsed {len(summaries)} valid games. Handing off to Analyst...")
    bus.node_complete("fetch")
    return {"raw_games": raw_games, "game_summaries": summaries}


def format_output_node(state: ChessCoachState) -> dict:
    """Assemble final report, save markdown + PDF, update user preferences."""
    username = state["username"]
    analysis = state["analysis_report"]
    coaching = state["coaching_report"]
    goals = state["player_goals"]
    critique = state.get("critique_result", {})
    num_games = state.get("num_games", 0)
    time_control = state.get("time_control", "all")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    generated_at = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    final_report = (
        f"# Chess Coaching Report — {username}\n"
        f"Generated: {generated_at}\n"
        f"Games Analyzed: {num_games} ({time_control})\n"
        f"Quality Score: {critique.get('total_score', 'N/A')}/100\n\n"
        f"---\n\n"
        f"## Game Analysis\n\n{analysis}\n\n"
        f"---\n\n"
        f"## Personalized Coaching Plan\n\n{coaching}\n"
    )

    os.makedirs("outputs", exist_ok=True)
    md_path = f"outputs/{username}_report_{timestamp}.md"
    with open(md_path, "w") as f:
        f.write(final_report)

    pdf_path = f"outputs/{username}_report_{timestamp}.pdf"
    generate_coaching_pdf(final_report, pdf_path, username, generated_at)

    save_user(username, {
        "preferred_time_control": time_control,
        "white_opening": goals.get("white_opening"),
        "black_vs_e4": goals.get("black_vs_e4"),
        "black_vs_d4": goals.get("black_vs_d4"),
        "main_goal": goals.get("main_goal"),
    })

    bus.debug("Report saved! Your coaching plan is ready.")
    bus.complete(md_path, pdf_path)

    return {"final_report": final_report}


# ---------------------------------------------------------------------------
# Graph builders
# ---------------------------------------------------------------------------

def _base_graph() -> StateGraph:
    """Nodes shared by both CLI and web graphs."""
    workflow = StateGraph(ChessCoachState)
    workflow.add_node("fetch_games", fetch_games_node)
    workflow.add_node("analyze_games", analyze_games_node)
    workflow.add_node("coach_interview", coach_interview_node)
    workflow.add_node("generate_lesson", generate_lesson_node)
    workflow.add_node("critic_review", critic_review_node)
    workflow.add_node("format_output", format_output_node)

    workflow.add_edge("fetch_games", "analyze_games")
    workflow.add_edge("analyze_games", "coach_interview")
    workflow.add_edge("coach_interview", "generate_lesson")
    workflow.add_edge("generate_lesson", "critic_review")
    workflow.add_conditional_edges(
        "critic_review",
        should_regenerate,
        {"regenerate": "generate_lesson", "approved": "format_output"},
    )
    workflow.add_edge("format_output", END)
    return workflow


def build_cli_graph():
    workflow = _base_graph()
    workflow.add_node("memory_check", memory_check_node)
    workflow.add_node("analyst_interview", analyst_interview_node)
    workflow.add_edge(START, "memory_check")
    workflow.add_edge("memory_check", "analyst_interview")
    workflow.add_edge("analyst_interview", "fetch_games")
    return workflow.compile()


def build_web_graph():
    workflow = _base_graph()
    workflow.add_edge(START, "fetch_games")
    return workflow.compile()


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def run_coaching_session():
    """CLI entry point."""
    bus.setup_cli()
    graph = build_cli_graph()
    initial: ChessCoachState = {
        "username": "", "is_returning_user": False, "user_data": {},
        "num_games": 10, "time_control": "all",
        "raw_games": [], "game_summaries": [],
        "analysis_report": "", "player_goals": {},
        "coaching_report": "", "critique_result": {},
        "critique_attempts": 0, "final_report": "", "messages": [],
    }
    return graph.invoke(initial)


def run_coaching_session_web(username: str, num_games: int, time_control: str, user_data: dict):
    """Web entry point — called from api/session.py in a background thread."""
    graph = build_web_graph()
    initial: ChessCoachState = {
        "username": username,
        "is_returning_user": bool(user_data),
        "user_data": user_data,
        "num_games": num_games,
        "time_control": time_control,
        "raw_games": [], "game_summaries": [],
        "analysis_report": "", "player_goals": {},
        "coaching_report": "", "critique_result": {},
        "critique_attempts": 0, "final_report": "", "messages": [],
    }
    return graph.invoke(initial)
