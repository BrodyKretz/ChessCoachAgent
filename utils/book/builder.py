"""Assemble the full personalized coaching workbook.

Layout target: LearningChess - Lessons for Beginners Vol 1.

The book is one PDF, multiple chapters, all in the same workbook voice:

    Cover
    1. Your Recent Games    -- table-style summary of the session's games
    2. Game Analysis        -- Analyst LLM markdown rendered as prose
    3. Missed Mates         -- engine_findings, one lesson per position (if any)
    4. Critical Blunders    -- engine_findings, one lesson per position (if any)
    5. Your Coaching Plan   -- Coach LLM markdown rendered as prose
    Test                    -- closing page with score/points/correct/time fields

Engine-driven chapters (3, 4) are only emitted when the user opted in to
the engine analysis and Stockfish produced findings. The book still
prints cleanly without them — the rest of the chapters are always present.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from reportlab.platypus import PageBreak, Spacer

from .layout import (
    build_doc,
    cover_story,
    games_chapter_story,
    lesson_story,
    prose_chapter_story,
    puzzle_grid_chapter_story,
    section_opener_story,
    test_page_story,
)
from .markdown import markdown_to_flowables
from .styles import book_styles, register_fonts
from .teaching import lesson_for


THEME_DATA = {
    "missed_mate": {
        "title": "Missed Mates",
        "intro": (
            "A checkmate is when the enemy king is in check and has nowhere "
            "to go — the game ends right there. In every position in this "
            "chapter, you had a forced mate on the board during the game. "
            "Let's set them up, find them together, and lock the pattern in."
        ),
        "q_lead": "We give mate when we...",
        "q_options": [
            "capture the opponent's last piece.",
            "give check and the king cannot get out of it.",
            "push our king to the back rank.",
        ],
    },
    "blunder": {
        "title": "Critical Blunders",
        "intro": (
            "A blunder is a move that hands the opponent something for free "
            "— a piece, an attack, or a winning position. Studying your own "
            "blunders is the fastest way to stop making them. Each of these "
            "positions came from one of your recent games."
        ),
        "q_lead": "What is the best way to learn from a blunder?",
        "q_options": [
            "Move on quickly and try not to think about it.",
            "Look up the best move and replay the position by hand.",
            "Avoid that opening forever.",
        ],
    },
}


def _group_by_theme(findings: Sequence) -> dict[str, list]:
    groups: dict[str, list] = {"missed_mate": [], "blunder": []}
    for f in findings:
        groups.setdefault(f.theme, []).append(f)
    return groups


def build_workbook_pdf(
    output_path: str | Path,
    *,
    username: str,
    generated_at: str,
    game_summaries: list[dict] | None = None,
    time_control: str = "all",
    analysis_md: str = "",
    coaching_md: str = "",
    findings: Sequence = (),
) -> Path:
    """Build the full personalized workbook PDF. Returns the output Path."""
    register_fonts()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    doc = build_doc(str(out),
                    title=f"Coaching Workbook — {username}",
                    author="Chess Coach Agent")
    styles = book_styles()

    story: list = []

    # ---- Cover ----------------------------------------------------------
    story.extend(cover_story(
        styles,
        title="Coaching Workbook",
        subtitle="Personalized lessons from your games",
        player=username,
        period=generated_at,
    ))

    chapter_no = 0

    # ---- Chapter 1: Your Recent Games -----------------------------------
    if game_summaries:
        chapter_no += 1
        story.extend(games_chapter_story(
            styles, number=chapter_no,
            username=username, games=game_summaries,
            time_control=time_control,
        ))
        story.append(PageBreak())

    # ---- Chapter 2: Game Analysis (Analyst LLM output) ------------------
    if analysis_md.strip():
        chapter_no += 1
        story.extend(prose_chapter_story(
            styles, number=chapter_no, title="Game Analysis",
            lead=(
                "This chapter walks through the patterns the coach noticed "
                "across your games. Read it slowly — the goal is to see your "
                "own play through fresh eyes, not just to skim a checklist."
            ),
            body_flowables=markdown_to_flowables(analysis_md, styles),
        ))
        story.append(PageBreak())

    # ---- Chapter 3-4: Tactics (engine findings) -------------------------
    groups = _group_by_theme(findings)
    position_no = 0
    for theme in ("missed_mate", "blunder"):
        in_theme = groups.get(theme, [])
        if not in_theme:
            continue

        chapter_no += 1
        meta = THEME_DATA[theme]
        story.extend(section_opener_story(
            styles, number=chapter_no,
            title=meta["title"], intro=meta["intro"],
            q_lead=meta["q_lead"], q_options=meta["q_options"],
        ))
        story.append(Spacer(1, 10))

        for f in in_theme:
            position_no += 1
            story.extend(lesson_story(styles, lesson_for(f, position_no)))

        story.append(PageBreak())

    # ---- Chapter 5: Your Coaching Plan (Coach LLM output) --------------
    if coaching_md.strip():
        chapter_no += 1
        story.extend(prose_chapter_story(
            styles, number=chapter_no, title="Your Coaching Plan",
            lead=(
                "Here is the personal practice plan the coach drew up for "
                "you, based on the games above. Treat it as a menu — start "
                "with one item this week and build from there."
            ),
            body_flowables=markdown_to_flowables(coaching_md, styles),
        ))
        story.append(PageBreak())

    # ---- Chapter 6: Puzzles from Your Games -----------------------------
    # 3x3 grid of mini-boards mirroring the ChessWins mate-in-one PDF —
    # bare puzzles drawn from your real mistakes. Solutions are in the
    # teaching chapters above; this section is for re-testing yourself.
    if findings:
        chapter_no += 1
        story.extend(puzzle_grid_chapter_story(
            styles, number=chapter_no, title="Puzzles from Your Games",
            lead=(
                "Each diagram below is a real position from one of your "
                "games where you went wrong. Try to find the move on your "
                "own — the answers are in the chapters above. Come back to "
                "this page in a week and see if you've internalized the "
                "pattern."
            ),
            findings=list(findings),
        ))

    # ---- Closing Test page ---------------------------------------------
    if position_no > 0:
        story.extend(test_page_story(styles, total_positions=position_no))
    else:
        # No engine analysis ran — still print a closing reflection page
        # so the back of the book isn't empty.
        story.extend(test_page_story(styles, total_positions=0))

    doc.build(story)
    return out


# ----------------------------------------------------------------------
# Backwards-compatible thin wrapper. Old callers passed `findings,
# username, generated_at, output_path` positionally; preserve that.

def build_key_positions_pdf(findings, username: str, generated_at: str,
                            output_path: str | Path) -> Path:
    """Compatibility shim — emits the tactics-only book (no prose chapters)."""
    return build_workbook_pdf(
        output_path,
        username=username,
        generated_at=generated_at,
        findings=findings,
    )
