"""Assemble the personalized 'Key Positions' workbook.

Takes a list of Findings (from tools.engine_findings) and produces a teaching
PDF in the LearningChess-workbook style:

    1. Cover page
    2. Section opener for missed mates (if any)
    3. Teaching pages — 2 positions per page, board + prose + 'Chess Speak'
    4. Section opener for big blunders
    5. More teaching pages
    6. Closing 'Your Progress' page with fill-in score lines

Voice and structure deliberately match the reference workbook so the file
reads as a lesson rather than a dump of engine output.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from reportlab.pdfgen import canvas

from .layout import (
    PAGE_H,
    PAGE_W,
    cover,
    footer,
    header,
    progress_page,
    teaching_pair,
)  # noqa: F401 — header is still used by _emit_section's teaching pages
from .styles import (
    GOLD,
    MARGIN,
    TEXT,
    TEXT_FONT,
    TEXT_FONT_BOLD,
    TEXT_MUTED,
    register_fonts,
)
from .teaching import teaching_for
from .types import BookPuzzle


BRAND = "Chess Coach"
POSITIONS_PER_PAGE = 2

THEME_TITLES = {
    "missed_mate": "Missed Mates",
    "blunder": "Critical Blunders",
}
THEME_SUBTITLES = {
    "missed_mate": "Forcing wins you had on the board",
    "blunder": "Moves that lost the most centipawns",
}
THEME_INTROS = {
    "missed_mate": (
        "A checkmate is when the enemy king is attacked and has nowhere to go. "
        "In each of these positions you had a forced mate during the game — "
        "let's look at the boards and find what was missed."
    ),
    "blunder": (
        "A blunder is a move that hands the opponent something for free — "
        "a piece, an attack, a clean position. Studying your own blunders is "
        "the fastest way to stop making them. Let's look at them one by one."
    ),
}


def _finding_to_puzzle(idx: int, f) -> BookPuzzle:
    return BookPuzzle(
        puzzle_id=idx,
        fen=f.fen,
        side_to_move=f.side_to_move,
        best_uci=f.best_uci,
        best_san=f.best_san,
        is_mate=(f.theme == "missed_mate"),
        move_number=f.move_number,
        opening=f.opening,
        opponent=f.opponent,
        game_date=f.game_date,
    )


def _section_opener(c: canvas.Canvas, theme: str, count: int) -> None:
    """Chapter opener: big title, gold rule, lead paragraph, position count."""
    c.setFillColor(TEXT)
    c.setFont(TEXT_FONT_BOLD, 32)
    c.drawString(MARGIN, PAGE_H - MARGIN - 32, THEME_TITLES[theme])

    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.line(MARGIN, PAGE_H - MARGIN - 42, MARGIN + 60, PAGE_H - MARGIN - 42)

    c.setFillColor(TEXT_MUTED)
    c.setFont(TEXT_FONT, 11)
    c.drawString(MARGIN, PAGE_H - MARGIN - 62, THEME_SUBTITLES[theme])

    # Body intro — broken into ~75-char lines manually so we stay on canvas
    c.setFillColor(TEXT)
    c.setFont(TEXT_FONT, 11.5)
    intro = THEME_INTROS[theme]
    y = PAGE_H - MARGIN - 100
    for line in _wrap_canvas_lines(intro, max_chars=82):
        c.drawString(MARGIN, y, line)
        y -= 16

    c.setFillColor(TEXT)
    c.setFont(TEXT_FONT_BOLD, 13)
    c.drawString(MARGIN, y - 12,
                 f"{count} position{'s' if count != 1 else ''} from your games")


def _wrap_canvas_lines(text: str, max_chars: int) -> list[str]:
    """Lightweight word-wrap for body intros. Good enough for the canvas API."""
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for w in words:
        add = len(w) + (1 if cur else 0)
        if cur_len + add > max_chars and cur:
            lines.append(" ".join(cur))
            cur = [w]
            cur_len = len(w)
        else:
            cur.append(w)
            cur_len += add
    if cur:
        lines.append(" ".join(cur))
    return lines


def _group_by_theme(findings: Sequence) -> dict[str, list]:
    groups: dict[str, list] = {"missed_mate": [], "blunder": []}
    for f in findings:
        groups.setdefault(f.theme, []).append(f)
    return groups


def _teaching_pages_for(count: int) -> int:
    if count == 0:
        return 0
    return (count + POSITIONS_PER_PAGE - 1) // POSITIONS_PER_PAGE


def _section_page_count(count: int) -> int:
    """Section opener + teaching pages, or 0 if empty."""
    if count == 0:
        return 0
    return 1 + _teaching_pages_for(count)


def build_key_positions_pdf(findings: Sequence, username: str,
                            generated_at: str, output_path: str | Path) -> Path:
    """Build the personalized teaching workbook. Returns the output Path."""
    register_fonts()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    groups = _group_by_theme(findings)
    mates_findings = groups.get("missed_mate", [])
    blunder_findings = groups.get("blunder", [])

    mates = [_finding_to_puzzle(i + 1, f) for i, f in enumerate(mates_findings)]
    blunders_start = len(mates) + 1
    blunders = [_finding_to_puzzle(blunders_start + i, f)
                for i, f in enumerate(blunder_findings)]
    ordered = mates + blunders

    if not ordered:
        raise ValueError("No findings to render — refuse to emit empty book.")

    # Page totals (cover + sections + closing 'Your Progress')
    total_pages = 1
    total_pages += _section_page_count(len(mates))
    total_pages += _section_page_count(len(blunders))
    total_pages += 1   # progress page

    c = canvas.Canvas(str(out), pagesize=(PAGE_W, PAGE_H))
    c.setTitle(f"Key Positions — {username}")
    c.setAuthor("Chess Coach Agent")

    # ---- Cover ----
    cover(
        c,
        title="Key Positions",
        subtitle="Lessons drawn from your own games",
        player=username,
        period=generated_at,
    )
    c.showPage()

    page_num = 2

    page_num = _emit_section(
        c, theme="missed_mate", puzzles=mates,
        findings_for_idx=mates_findings, base_idx=1,
        page_num=page_num, total_pages=total_pages,
    )
    page_num = _emit_section(
        c, theme="blunder", puzzles=blunders,
        findings_for_idx=blunder_findings, base_idx=blunders_start,
        page_num=page_num, total_pages=total_pages,
    )

    # ---- Closing Your Progress page (no running header — chapter-style) ----
    progress_page(c, total_positions=len(ordered))
    footer(c, page_num, total_pages)
    c.showPage()

    c.save()
    return out


def _emit_section(c: canvas.Canvas, *, theme: str,
                  puzzles, findings_for_idx, base_idx: int,
                  page_num: int, total_pages: int) -> int:
    """Emit one section: opener + teaching pages. Returns next page_num."""
    if not puzzles:
        return page_num

    # Section opener
    _section_opener(c, theme, len(puzzles))
    footer(c, page_num, total_pages)
    c.showPage()
    page_num += 1

    # Teaching pages, 2 puzzles per page
    section_title = THEME_TITLES[theme]
    for i in range(0, len(puzzles), POSITIONS_PER_PAGE):
        pair_puzzles = puzzles[i: i + POSITIONS_PER_PAGE]
        pair_findings = findings_for_idx[i: i + POSITIONS_PER_PAGE]
        pair = [
            (puz, teaching_for(f, base_idx + i + k))
            for k, (puz, f) in enumerate(zip(pair_puzzles, pair_findings))
        ]
        header(c, BRAND, section_title)
        teaching_pair(c, pair)
        footer(c, page_num, total_pages)
        c.showPage()
        page_num += 1

    return page_num
