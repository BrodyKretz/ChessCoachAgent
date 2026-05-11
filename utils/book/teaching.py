"""Workbook-style teaching prose for each Finding.

The voice mirrors the LearningChess beginner workbook: direct, conversational,
second-person, builds intuition before stating the rule. Templates rotate so
consecutive pages don't read identically.

Pure functions, no I/O — easy to unit-test and to reuse from anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass


# Rotated opener lines keyed by position index (mod len).
_BLUNDER_OPENERS = [
    "Take a look at this position.",
    "Let's study this position carefully.",
    "Here's a critical moment from one of your games.",
    "This position needs a closer look.",
]

_MATE_OPENERS = [
    "Here's a position where a checkmate was hiding.",
    "Take a careful look — there was a forced mate on the board.",
    "Mate was right there. Did you spot it during the game?",
    "A mating chance slipped by here. Let's find it together.",
]


def _opener(theme: str, idx: int) -> str:
    pool = _MATE_OPENERS if theme == "missed_mate" else _BLUNDER_OPENERS
    return pool[idx % len(pool)]


def _ctx_phrase(opponent: str | None, move_number: int) -> str:
    if opponent:
        return f"It came up against {opponent} on move {move_number}."
    return f"It came up on move {move_number}."


def _played_clause(played_san: str, theme: str, cp_loss: int) -> str:
    """One sentence describing what was played and why it didn't work."""
    if theme == "missed_mate":
        return (
            f"You played <b>{played_san}</b>, which is a reasonable-looking move — "
            f"but it lets the win slip away."
        )
    # A cp_loss above ~1500 almost always means the position swung from playable
    # to lost — usually a forced losing sequence rather than literal material loss.
    if cp_loss >= 1500:
        return (
            f"You played <b>{played_san}</b> — but this walks into a forced "
            f"losing sequence the engine sees several moves out."
        )
    pawns = round(cp_loss / 100)
    pawn_word = "pawn" if pawns == 1 else "pawns"
    if cp_loss >= 500:
        return (
            f"You played <b>{played_san}</b> — but this loses around "
            f"{pawns} {pawn_word} of material to best play."
        )
    return (
        f"You played <b>{played_san}</b>. The engine sees this as roughly "
        f"a {pawns}-{pawn_word} mistake."
    )


def _solution_clause(best_san: str, theme: str) -> str:
    if theme == "missed_mate":
        return (
            f"The winning move was <b>{best_san}</b>. "
            "It puts the king in check with no escape — checkmate."
        )
    return (
        f"The best move was <b>{best_san}</b>. "
        "Play through it on a board and ask yourself why it works."
    )


def _chess_speak(theme: str, best_san: str) -> str | None:
    """Optional 'In Chess Speak' callout when the move tells us something concrete."""
    if theme == "missed_mate":
        return (
            "<i>In Chess Speak:</i> a check the opponent cannot answer is called "
            "<b>checkmate</b> — the game ends instantly."
        )
    if best_san.endswith("+"):
        return (
            "<i>In Chess Speak:</i> when a move attacks the king, we call it a "
            "<b>check</b> — marked by the (+) sign."
        )
    if "x" in best_san:
        return (
            "<i>In Chess Speak:</i> a move that takes an enemy piece is called a "
            "<b>capture</b> — written with an x in the middle."
        )
    return None


@dataclass(frozen=True)
class TeachingBlock:
    """Rendered prose for one position. Strings are ReportLab-paragraph-ready."""
    heading: str                # e.g. "Position 3 — Black to play"
    opener: str                 # 1 sentence
    context: str                # 1 sentence
    played: str                 # 1 sentence, contains <b>played</b>
    solution: str               # 1 sentence, contains <b>best</b>
    chess_speak: str | None     # 0-1 sentence callout


def teaching_for(finding, idx: int) -> TeachingBlock:
    """Build the teaching block for one Finding (1-indexed `idx`)."""
    side_label = "White to play" if finding.side_to_move == "white" else "Black to play"
    heading = f"Position {idx} — {side_label}"

    return TeachingBlock(
        heading=heading,
        opener=_opener(finding.theme, idx - 1),
        context=_ctx_phrase(finding.opponent, finding.move_number),
        played=_played_clause(finding.played_san, finding.theme, finding.cp_loss),
        solution=_solution_clause(finding.best_san, finding.theme),
        chess_speak=_chess_speak(finding.theme, finding.best_san),
    )
