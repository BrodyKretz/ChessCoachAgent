"""
Coach Agent nodes.
coach_interview_node: collects player goals via bus.ask() (works in CLI + web).
generate_lesson_node: Coach King generates the personalized plan.
"""
from langchain_anthropic import ChatAnthropic
from graph.state import ChessCoachState
from utils.events import bus
from utils.character import COACH_PERSONALITY


def coach_interview_node(state: ChessCoachState) -> dict:
    """LangGraph node: interview the player. bus.ask() handles CLI vs web."""
    user_data = state.get("user_data", {})
    username = state["username"]
    goals = {}

    bus.node_active("coach")
    bus.node_waiting("coach")
    bus.speak(
        f"Hey {username}, before I build your plan, "
        "I have a few quick questions to make it personal."
    )
    bus.debug("Coach King is interviewing you about your goals...")

    # Main goal
    saved = user_data.get("goals")
    suffix = f" (saved: '{saved}' — leave blank to keep)" if saved else ""
    goals["main_goal"] = (
        bus.ask("main_goal", f"What's your main chess goal right now?{suffix}")
        or saved
        or "General improvement"
    )

    # White opening
    saved = user_data.get("white_opening")
    suffix = f" (saved: {saved})" if saved else ""
    goals["white_opening"] = (
        _map(
            bus.ask(
                "white_opening",
                f"As White, what's your preferred first move?{suffix}",
                ["1 = e4", "2 = d4", "3 = c4", "4 = Nf3", "5 = Other (type it)"],
            ),
            {"1": "e4", "2": "d4", "3": "c4", "4": "Nf3"},
        )
        or saved
        or "e4"
    )

    # Black vs e4
    saved = user_data.get("black_vs_e4")
    suffix = f" (saved: {saved})" if saved else ""
    goals["black_vs_e4"] = (
        _map(
            bus.ask(
                "black_vs_e4",
                f"As Black against e4?{suffix}",
                ["1 = 1...e5 Open games", "2 = Sicilian (c5)", "3 = French (e6)", "4 = Caro-Kann (c6)", "5 = Other"],
            ),
            {"1": "1...e5 Open games", "2": "1...c5 Sicilian", "3": "1...e6 French", "4": "1...c6 Caro-Kann"},
        )
        or saved
        or "1...e5 Open games"
    )

    # Black vs d4
    saved = user_data.get("black_vs_d4")
    suffix = f" (saved: {saved})" if saved else ""
    goals["black_vs_d4"] = (
        _map(
            bus.ask(
                "black_vs_d4",
                f"As Black against d4?{suffix}",
                ["1 = 1...d5 (Queen's Gambit lines)", "2 = 1...Nf6 (Indian systems)", "3 = 1...f5 (Dutch)", "4 = Other"],
            ),
            {"1": "1...d5 Queen's Gambit", "2": "1...Nf6 Indian systems", "3": "1...f5 Dutch"},
        )
        or saved
        or "1...d5 Queen's Gambit"
    )

    # Focus areas
    raw = bus.ask(
        "focus_areas",
        "Which areas do you most want to improve? (pick all that apply)",
        ["1 = Openings", "2 = Middlegame tactics", "3 = Strategy / positional", "4 = Endgames", "5 = Time management"],
    )
    area_map = {"1": "openings", "2": "middlegame tactics", "3": "positional strategy", "4": "endgames", "5": "time management"}
    selected = [n.strip() for n in raw.replace(",", " ").split() if n.strip() in area_map]
    goals["focus_areas"] = [area_map[n] for n in selected] or ["openings", "middlegame tactics"]

    bus.speak("Perfect. I have everything I need. Give me a moment to put your plan together.")
    bus.debug("Interview complete. Coach King is writing your personalized plan...")

    return {"player_goals": goals}


def generate_lesson_node(state: ChessCoachState) -> dict:
    """LangGraph node: Coach King writes (or revises) the coaching report."""
    llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0.5)

    analysis = state["analysis_report"]
    goals = state["player_goals"]
    username = state["username"]
    attempts = state.get("critique_attempts", 0)
    prev_critique = state.get("critique_result", {})

    bus.node_active("coach")

    retry_block = ""
    if attempts > 0 and prev_critique.get("feedback"):
        bus.debug(f"Critic rejected the plan. Coach King is revising (attempt {attempts + 1})...")
        retry_block = f"""
IMPORTANT — Your previous coaching report was REJECTED by the critic.
Critic's feedback: "{prev_critique['feedback']}"
Score received: {prev_critique.get('total_score', 'N/A')}/100
Weaknesses: {prev_critique.get('weaknesses', [])}
Address every point. Do not repeat the same mistakes.
"""
    else:
        bus.debug("Coach King is writing your personalized plan...")

    prompt = f"""{COACH_PERSONALITY}

You are writing a personalized chess coaching plan for {username}.

=== GAME ANALYSIS (from Analyst Agent) ===
{analysis}

=== PLAYER PROFILE ===
Goal: {goals.get('main_goal', 'General improvement')}
As White they want to play: {goals.get('white_opening', 'e4')}
As Black vs e4: {goals.get('black_vs_e4', '1...e5')}
As Black vs d4: {goals.get('black_vs_d4', '1...d5')}
Focus areas: {', '.join(goals.get('focus_areas', ['openings']))}
{retry_block}

Write a detailed, personalized coaching report in your warm Coach King voice.

## Opening Repertoire Plan
Tailored to their stated preferences. Give 5-8 key moves/ideas for each opening.
Reference patterns from the game analysis — what are they currently doing wrong,
and what exactly should they change?

## Middlegame Lessons
Address 2-4 specific recurring patterns from the analysis. For each: name the
pattern, explain why it's costing them, give the principle that fixes it.

## Endgame Training
Based on how their games are ending. Name specific endgame types to study.

## Time Management
Only include if time pressure (⏰) appeared frequently.

## Weekly Training Schedule
A concrete 7-day plan with specific, actionable daily tasks.

## Your Coach King Send-Off
End with a warm, personalized 2-4 sentence motivational message to {username}.
Reference their specific goal. Be genuine, not generic.

RULES:
- Every section must reference their actual game patterns — no generic advice.
- For every major principle or lesson, cite a real chess reference: e.g. "As Nimzowitsch explains in My System...", "Silman's How to Reassess Your Chess calls this...", "Capablanca's Chess Fundamentals warns against...". Use real authors and real book titles only.
- Approved references: My System (Nimzowitsch), Chess Fundamentals (Capablanca), How to Reassess Your Chess (Silman), The Amateur's Mind (Silman), Silman's Complete Endgame Course, Logical Chess: Move by Move (Chernev), Zurich 1953 (Bronstein), Winning Chess Tactics (Seirawan), Dvoretsky's Endgame Manual, Think Like a Grandmaster (Kotov).
- Mistakes made under ⏰ time pressure: note briefly, do not prioritize.
- Write as Coach King — warm, encouraging, mentor-like."""

    full_response = ""
    for chunk in llm.stream(prompt):
        text = chunk.content
        bus.stream_chunk("coach", text)
        full_response += text

    if attempts == 0:
        bus.debug("Plan written. Sending to Critic for quality review...")
        bus.speak("Your plan is written. Let me have the Critic check it before I show you.")

    bus.node_complete("coach")

    return {
        "coaching_report": full_response,
        "critique_attempts": attempts + 1,
    }


def _map(raw: str, mapping: dict) -> str:
    return mapping.get(raw.strip(), raw.strip())
