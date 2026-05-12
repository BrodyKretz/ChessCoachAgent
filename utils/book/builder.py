"""Assemble the personalized 'Key Positions' workbook.

Layout target: LearningChess - Lessons for Beginners Vol 1.
    * Cover page (gold tab + series tag + big title + player + date)
    * Italic running header across every body page
    * Two-column flowing body with inline mini-boards
    * Numbered chapters (1. Missed Mates / 2. Critical Blunders) with a
      conversational intro paragraph and a single 'Q1.' multiple-choice
      that frames the chapter theme
    * One lesson per position: short intro, board, "Find the best move."
      prompt, fill-in line ("1. __________"), then an explanation paragraph
    * Closing 'Test' page with Score / Points / Correct / Time fields

The page geometry, frames, and chrome live in layout.py; the prose lives
in teaching.py; this module just orchestrates the story.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from reportlab.platypus import NextPageTemplate, PageBreak, Spacer

from .layout import (
    build_doc,
    cover_story,
    lesson_story,
    section_opener_story,
    test_page_story,
)
from .styles import book_styles, register_fonts
from .teaching import lesson_for


# Chapter copy
CHAPTER_DATA = {
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


def build_key_positions_pdf(findings: Sequence, username: str,
                            generated_at: str, output_path: str | Path) -> Path:
    """Build the personalized workbook. Returns the output Path."""
    register_fonts()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    groups = _group_by_theme(findings)
    mates = groups.get("missed_mate", [])
    blunders = groups.get("blunder", [])

    if not mates and not blunders:
        raise ValueError("No findings to render — refuse to emit empty book.")

    doc = build_doc(str(out),
                    title=f"Key Positions — {username}",
                    author="Chess Coach Agent")
    styles = book_styles()

    story: list = []

    # ---- Cover (uses the special 'cover' page template) -----------------
    story.extend(cover_story(
        styles,
        title="Key Positions",
        subtitle="Personalized lessons from your games",
        player=username,
        period=generated_at,
    ))

    # ---- Chapters --------------------------------------------------------
    chapter_no = 0
    position_no = 0

    for theme in ("missed_mate", "blunder"):
        findings_in_theme = groups.get(theme, [])
        if not findings_in_theme:
            continue

        chapter_no += 1
        meta = CHAPTER_DATA[theme]
        story.extend(section_opener_story(
            styles,
            number=chapter_no,
            title=meta["title"],
            intro=meta["intro"],
            q_lead=meta["q_lead"],
            q_options=meta["q_options"],
        ))
        story.append(Spacer(1, 10))

        # All positions within this chapter, flowing through both columns
        for f in findings_in_theme:
            position_no += 1
            lesson = lesson_for(f, position_no)
            story.extend(lesson_story(styles, lesson))

        # Push the next chapter to a new page so chapter titles aren't
        # buried halfway down a column.
        story.append(PageBreak())

    # ---- Closing Test page ----------------------------------------------
    story.extend(test_page_story(styles, total_positions=position_no))

    doc.build(story)
    return out
