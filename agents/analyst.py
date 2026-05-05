"""
Analyst Agent node.
Identifies patterns, mistakes, and recurring weaknesses across all games.
Uses the event bus for output so it works in both CLI and web mode.
"""
from langchain_anthropic import ChatAnthropic
from graph.state import ChessCoachState
from utils.events import bus


def analyze_games_node(state: ChessCoachState) -> dict:
    """LangGraph node: analyzes game_summaries and writes analysis_report."""
    llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0.3)

    summaries = state["game_summaries"]
    username = state["username"]

    bus.node_active("analyst")
    bus.debug(f"Analyst is reading {len(summaries)} games...")

    if not summaries:
        bus.node_complete("analyst")
        return {"analysis_report": "No games found for the selected filters."}

    games_text = _format_games_for_prompt(summaries)

    prompt = f"""You are an expert chess analyst reviewing {len(summaries)} recent games played by {username}.

{games_text}

Legend: ⏰ = move made under severe time pressure (<30 seconds remaining on clock).

Provide a structured analysis with these exact sections:

## Opening Patterns
What openings does {username} play as White and Black? Are they following theory?
Note any early deviations, common mistakes in the opening phase.

## Middlegame Patterns
Identify 2-4 recurring tactical or strategic mistakes. Be specific — reference
move numbers or game patterns, not generic advice.

## Endgame Patterns
How does the player handle endgames? Technique issues, premature trades, etc.

## Time Management
Were time-pressured moves (⏰) frequent? Did time pressure correlate with mistakes?
Estimate whether errors on ⏰ moves were time-caused or would be errors at any speed.

## Top 3 Priority Areas
Rank the 3 most impactful areas to improve, with a one-sentence reason each.

Be specific. Do not give generic chess advice that could apply to anyone."""

    bus.debug("Analyst is identifying patterns across all games...")
    full_response = ""
    for chunk in llm.stream(prompt):
        text = chunk.content
        bus.stream_chunk("analyst", text)
        full_response += text

    bus.debug("Analysis complete. Handing off to Coach King.")
    bus.node_complete("analyst")

    return {"analysis_report": full_response}


def _format_games_for_prompt(summaries: list) -> str:
    lines = []
    for i, g in enumerate(summaries, 1):
        pressure_note = ""
        if g.get("time_pressure_count", 0) > 0:
            pressure_note = (
                f" | ⏰ TIME PRESSURE on {g['time_pressure_count']} "
                f"of their moves (moves {g['time_pressure_move_numbers']})"
            )
        lines.append(
            f"--- Game {i} ---\n"
            f"Result: {g['outcome'].upper()} as {g['player_color']}\n"
            f"Opening: {g['opening_name']} ({g['opening_eco']})\n"
            f"Moves: {g['total_moves']} total{pressure_note}\n"
            f"Time control: {g['time_control_raw']}\n"
            f"Move sequence: {g['move_string']}\n"
        )
    return "\n".join(lines)
