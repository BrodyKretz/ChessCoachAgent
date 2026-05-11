"""
Session runner — called in a background thread by the WebSocket handler.
Handles memory check and kicks off the LangGraph graph.
"""
from memory.user_store import get_user, save_user, update_last_session
from tools.chess_api import validate_user
from utils.events import bus


def run_session(config: dict):
    username = config.get("username", "").strip()
    num_games = int(config.get("num_games", 10))
    time_control = config.get("time_control", "all")
    enable_engine = bool(config.get("enable_engine", False))

    # --- Memory check ---
    bus.node_active("setup")
    bus.debug(f"Checking Chess.com for '{username}'...")

    profile = validate_user(username)
    if profile is None:
        bus.error(f"Username '{username}' not found on Chess.com. Check the spelling.")
        return

    existing = get_user(username)
    if existing:
        user_data = dict(existing)
        bus.debug(f"Welcome back, {username}! Loaded your saved preferences.")
        bus.speak(f"Welcome back {username}! Great to see you again. I've loaded your saved preferences.")
    else:
        save_user(username)
        user_data = {}
        bus.debug(f"Linked new account: {username}")
        bus.speak(f"Great to meet you {username}! I've linked your Chess dot com account. I'll remember you next time.")

    update_last_session(username)
    bus.node_complete("setup")

    # --- Run the LangGraph pipeline ---
    from graph.pipeline import run_coaching_session_web
    run_coaching_session_web(
        username=username,
        num_games=num_games,
        time_control=time_control,
        user_data=user_data,
        enable_engine=enable_engine,
    )
