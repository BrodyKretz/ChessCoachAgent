"""
PGN parsing utilities using python-chess.
Extracts moves, clock times, opening info, and flags time-pressured moves.
"""
import chess.pgn
import io
import re
from typing import Optional

TIME_PRESSURE_THRESHOLD_SECONDS = 30


def parse_game(pgn_string: str, player_username: str) -> Optional[dict]:
    """
    Parse a single PGN game and return structured metadata.
    Returns None if the PGN is invalid.
    """
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_string))
    except Exception:
        return None

    if not game:
        return None

    headers = dict(game.headers)

    # Determine which color the player is
    white_name = headers.get("White", "").lower()
    player_color = "white" if player_username.lower() == white_name else "black"

    # Map result to win/loss/draw from player perspective
    result = headers.get("Result", "*")
    if player_color == "white":
        outcome = {"1-0": "win", "0-1": "loss"}.get(result, "draw")
    else:
        outcome = {"0-1": "win", "1-0": "loss"}.get(result, "draw")

    # Walk moves and extract clock times
    moves = []
    node = game
    half_move = 0
    while node.variations:
        node = node.variations[0]
        half_move += 1
        color = "white" if half_move % 2 == 1 else "black"
        move_number = (half_move + 1) // 2

        clock_seconds = _extract_clock(node.comment or "")
        under_pressure = (
            clock_seconds is not None and clock_seconds < TIME_PRESSURE_THRESHOLD_SECONDS
        )

        try:
            san = node.san()
        except Exception:
            san = str(node.move)

        moves.append({
            "move_number": move_number,
            "color": color,
            "san": san,
            "clock_seconds": clock_seconds,
            "time_pressure": under_pressure,
        })

    # Build a readable move string, marking time-pressured moves with ⏰
    move_string = _build_move_string(moves)

    player_pressure_moves = [
        m["move_number"] for m in moves
        if m["color"] == player_color and m["time_pressure"]
    ]

    return {
        "player_color": player_color,
        "outcome": outcome,
        "opening_eco": headers.get("ECO", "?"),
        "opening_name": headers.get("Opening", "Unknown Opening"),
        "time_control_raw": headers.get("TimeControl", "?"),
        "total_moves": len(moves) // 2,
        "move_string": move_string,
        "time_pressure_count": len(player_pressure_moves),
        "time_pressure_move_numbers": player_pressure_moves,
        "white_player": headers.get("White", "?"),
        "black_player": headers.get("Black", "?"),
        "white_elo": headers.get("WhiteElo", "?"),
        "black_elo": headers.get("BlackElo", "?"),
        "termination": headers.get("Termination", "?"),
    }


def _extract_clock(comment: str) -> Optional[int]:
    """Parse [%clk h:mm:ss] annotation and return total seconds."""
    match = re.search(r'\[%clk (\d+):(\d+):(\d+)\]', comment)
    if match:
        h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return h * 3600 + m * 60 + s
    return None


def _build_move_string(moves: list, max_half_moves: int = 80) -> str:
    """Convert move list to readable algebraic notation string."""
    parts = []
    moves = moves[:max_half_moves]

    i = 0
    while i < len(moves):
        white_move = moves[i] if i < len(moves) else None
        black_move = moves[i + 1] if i + 1 < len(moves) else None

        move_num = moves[i]["move_number"]
        part = f"{move_num}."

        if white_move:
            suffix = "⏰" if white_move["time_pressure"] else ""
            part += f" {white_move['san']}{suffix}"

        if black_move:
            suffix = "⏰" if black_move["time_pressure"] else ""
            part += f" {black_move['san']}{suffix}"

        parts.append(part)
        i += 2

    return " ".join(parts)
