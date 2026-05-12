"""Workbook-style teaching copy for each Finding.

Voice target: LearningChess - Lessons for Beginners Vol 1. Direct,
second-person, builds intuition before stating the rule. Embeds the
"in Chess Speak" callout parenthetically in the prose rather than as a
separate box, matching the reference.

Pure functions, no I/O.
"""

from __future__ import annotations

from .layout import Lesson


# Rotated intro openers keyed by position index so consecutive lessons
# don't all start with the same sentence.
_BLUNDER_OPENERS = [
    "Take a look at this position.",
    "Let's study this position carefully.",
    "Here is a critical moment from your game.",
    "This position needs a closer look.",
]
_MATE_OPENERS = [
    "Here is a position where checkmate was hiding.",
    "Look carefully — there was a forced mate on the board.",
    "Mate was right there. Did you see it during the game?",
    "A mating chance slipped by here. Let's find it together.",
]


def _opener(theme: str, idx_zero: int) -> str:
    pool = _MATE_OPENERS if theme == "missed_mate" else _BLUNDER_OPENERS
    return pool[idx_zero % len(pool)]


def _context_phrase(opponent: str | None, move_number: int) -> str:
    """One sentence locating the position in the user's game history."""
    if opponent:
        return f"It came up against {opponent} on move {move_number}."
    return f"It came up on move {move_number}."


def _explain_played(played_san: str, theme: str, cp_loss: int) -> str:
    """One clause: what you played and why it didn't work."""
    if theme == "missed_mate":
        return (
            f"You played <b>{played_san}</b>, which looks reasonable — "
            "but it lets the win slip away."
        )
    if cp_loss >= 1500:
        return (
            f"You played <b>{played_san}</b>, which walks into a forced "
            "losing sequence the engine sees several moves out."
        )
    pawns = max(1, round(cp_loss / 100))
    pawn_word = "pawn" if pawns == 1 else "pawns"
    return (
        f"You played <b>{played_san}</b>, which loses around "
        f"{pawns} {pawn_word} to best play."
    )


def _explain_best(best_san: str, theme: str) -> str:
    """One clause: the best move + a parenthetical 'in Chess Speak' if it fits."""
    base = f"The best move was <b>{best_san}</b>."

    if theme == "missed_mate":
        return base + (
            " It puts the king in check with no escape — checkmate, "
            "and the game would have ended right there."
        )
    if best_san.endswith("#"):
        return base + " That move is checkmate — the game ends."
    if best_san.endswith("+"):
        return base + (
            " The (+) sign means the move gives check — Chess Speak "
            "for attacking the enemy king."
        )
    if "x" in best_san:
        return base + (
            " The x in the middle is Chess Speak for a capture: this "
            "move takes an enemy piece."
        )
    return base + " Set the position up on a board and play through why it works."


def lesson_for(finding, idx: int) -> Lesson:
    """Build the full Lesson record for one Finding (1-indexed)."""
    side_label = "White to play" if finding.side_to_move == "white" else "Black to play"
    heading = f"Position {idx} — {side_label}"

    # Workbook convention: "1. ..." prefix for a black move, "1." for white.
    fill_prefix = "1." if finding.side_to_move == "white" else "1. ..."
    fill_in = f"{fill_prefix} __________"

    intro = f"{_opener(finding.theme, idx - 1)} {_context_phrase(finding.opponent, finding.move_number)}"
    explanation = (
        f"{_explain_played(finding.played_san, finding.theme, finding.cp_loss)} "
        f"{_explain_best(finding.best_san, finding.theme)}"
    )

    return Lesson(
        heading=heading,
        intro=intro,
        fen=finding.fen,
        side=finding.side_to_move,
        prompt="Find the best move.",
        fill_in=fill_in,
        explanation=explanation,
    )
