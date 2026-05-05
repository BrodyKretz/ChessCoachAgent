"""
Shared state definition for the LangGraph pipeline.
Every node reads from and writes back to this TypedDict.
"""
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class ChessCoachState(TypedDict):
    # -- User identity --
    username: str
    is_returning_user: bool
    user_data: dict          # row from SQLite (may be empty for new users)

    # -- Session parameters chosen by analyst interview --
    num_games: int
    time_control: str        # blitz | bullet | rapid | daily | all

    # -- Raw and parsed game data --
    raw_games: list          # dicts from Chess.com API
    game_summaries: list     # dicts from pgn_parser.parse_game()

    # -- Agent outputs --
    analysis_report: str     # from Analyst agent
    player_goals: dict       # from Coach interview
    coaching_report: str     # from Coach agent
    critique_result: dict    # from Critic: {approved, total_score, feedback, ...}

    # -- Control flow --
    critique_attempts: int   # how many times Coach has run
    final_report: str        # formatted final output

    # -- Conversation history (auto-managed by LangGraph) --
    messages: Annotated[list[BaseMessage], add_messages]
