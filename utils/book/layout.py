"""Reusable page primitives: header, footer, cover, puzzle grid, solutions.

All generators compose these to keep the house style consistent. The
canvas-level functions take a live `Canvas` and draw on the current page;
they do NOT call showPage(). The caller controls page breaks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, Paragraph

from .board import render_board
from .styles import (
    CONTENT_W,
    GOLD,
    MARGIN,
    PAGE_SIZE,
    RULE,
    TEXT,
    TEXT_FONT,
    TEXT_FONT_BOLD,
    TEXT_MUTED,
    book_styles,
)
from .teaching import TeachingBlock
from .types import BookPuzzle


PAGE_W, PAGE_H = PAGE_SIZE
PUZZLES_PER_PAGE = 9


def header(c: canvas.Canvas, brand: str, title: str) -> None:
    """Brand mark top-left + centered title."""
    brand_y = PAGE_H - MARGIN + 6
    c.setFillColor(TEXT)
    c.setFont(TEXT_FONT_BOLD, 11)
    c.drawString(MARGIN, brand_y, brand)
    c.setFillColor(GOLD)
    c.rect(MARGIN, brand_y - 5, 28, 2, stroke=0, fill=1)

    c.setFillColor(TEXT)
    c.setFont(TEXT_FONT_BOLD, 22)
    c.drawCentredString(PAGE_W / 2, PAGE_H - MARGIN - 8, title)


def footer(c: canvas.Canvas, page_num: int, total: int) -> None:
    c.setFillColor(TEXT_MUTED)
    c.setFont(TEXT_FONT, 9)
    c.drawCentredString(PAGE_W / 2, MARGIN / 2, f"{page_num} / {total}")


def cover(c: canvas.Canvas, title: str, subtitle: str, player: str, period: str) -> None:
    """A book cover. Big title, accent rule, byline, period."""
    # Top accent block
    c.setFillColor(GOLD)
    c.rect(MARGIN, PAGE_H - MARGIN - 8, 80, 4, stroke=0, fill=1)

    # Series tag
    c.setFillColor(TEXT_MUTED)
    c.setFont(TEXT_FONT_BOLD, 10)
    c.drawString(MARGIN, PAGE_H - MARGIN - 28, "CHESS COACH · PERSONALIZED LESSON")

    # Title (large, multi-line ready)
    c.setFillColor(TEXT)
    c.setFont(TEXT_FONT_BOLD, 42)
    c.drawString(MARGIN, PAGE_H / 2 + 30, title)

    # Subtitle
    c.setFillColor(TEXT)
    c.setFont(TEXT_FONT, 18)
    c.drawString(MARGIN, PAGE_H / 2, subtitle)

    # Divider
    c.setStrokeColor(RULE)
    c.setLineWidth(0.5)
    c.line(MARGIN, PAGE_H / 2 - 28, PAGE_W - MARGIN, PAGE_H / 2 - 28)

    # Byline + period (bottom block)
    by_y = MARGIN + 60
    c.setFillColor(TEXT_MUTED)
    c.setFont(TEXT_FONT, 10)
    c.drawString(MARGIN, by_y + 18, "BUILT FROM YOUR OWN GAMES")
    c.setFillColor(TEXT)
    c.setFont(TEXT_FONT_BOLD, 16)
    c.drawString(MARGIN, by_y, player)
    c.setFillColor(TEXT_MUTED)
    c.setFont(TEXT_FONT, 11)
    c.drawString(MARGIN, by_y - 16, period)


def puzzle_grid(c: canvas.Canvas, puzzles: Sequence[BookPuzzle], start_num: int) -> None:
    """3x3 grid of boards with 'N. Side to play' captions."""
    cols, rows = 3, 3
    cell_gap_x = 18
    cell_gap_y = 28
    grid_top = PAGE_H - MARGIN - 56

    cell_w = (CONTENT_W - cell_gap_x * (cols - 1)) / cols
    board_size = cell_w
    caption_h = 14
    cell_h = board_size + caption_h + 4

    for i, p in enumerate(puzzles[: cols * rows]):
        r = i // cols
        col = i % cols
        x = MARGIN + col * (cell_w + cell_gap_x)
        y_top = grid_top - r * (cell_h + cell_gap_y)
        y_board = y_top - board_size

        d = render_board(p.fen, side=p.side_to_move, size=board_size)
        d.drawOn(c, x, y_board)

        c.setFillColor(TEXT)
        c.setFont(TEXT_FONT, 10.5)
        label = f"{start_num + i}. {'White' if p.side_to_move == 'white' else 'Black'} to play"
        c.drawCentredString(x + board_size / 2, y_board - caption_h, label)


def teaching_pair(c: canvas.Canvas,
                  pair: Sequence[tuple[BookPuzzle, TeachingBlock]]) -> None:
    """Draw up to two teaching cards stacked on one page.

    Each card: board on the left, heading + 3-4 short paragraphs on the right.
    Mirrors the LearningChess workbook flow (diagram → prose → 'In Chess Speak').
    """
    styles = book_styles()
    top = PAGE_H - MARGIN - 56            # leave space for the running header
    card_h = (top - MARGIN) / 2 - 12      # gap between cards
    board_size = min(card_h - 12, 230)
    text_x = MARGIN + board_size + 22
    text_w = CONTENT_W - board_size - 22

    for i, (puz, block) in enumerate(pair[:2]):
        # Position card
        y_card_top = top - i * (card_h + 24)
        y_board = y_card_top - board_size

        # Board
        d = render_board(puz.fen, side=puz.side_to_move, size=board_size)
        d.drawOn(c, MARGIN, y_board)

        # Right column heading + accent rule
        c.setFillColor(TEXT)
        c.setFont(TEXT_FONT_BOLD, 14)
        c.drawString(text_x, y_card_top - 14, block.heading)
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.2)
        c.line(text_x, y_card_top - 22, text_x + 32, y_card_top - 22)

        # Body prose (Paragraph + Frame so we get wrapping for free)
        story_lines = [
            f"{block.opener} {block.context}",
            block.played,
            block.solution,
        ]
        if block.chess_speak:
            story_lines.append(block.chess_speak)

        flow = [Paragraph(line, styles["body"]) for line in story_lines]

        frame = Frame(
            text_x, y_board - 4,                  # x, y of bottom-left
            text_w, y_card_top - 36 - (y_board - 4),  # available width & height
            leftPadding=0, rightPadding=0,
            topPadding=8, bottomPadding=4,
            showBoundary=0,
        )
        frame.addFromList(flow, c)

        # Faint divider between the two cards
        if i == 0 and len(pair) > 1:
            divider_y = y_board - 12
            c.setStrokeColor(RULE)
            c.setLineWidth(0.4)
            c.line(MARGIN, divider_y, MARGIN + CONTENT_W, divider_y)


def progress_page(c: canvas.Canvas, total_positions: int) -> None:
    """Closing 'Your Progress' page in the spirit of the workbook's test footer."""
    c.setFillColor(TEXT)
    c.setFont(TEXT_FONT_BOLD, 28)
    c.drawString(MARGIN, PAGE_H - MARGIN - 30, "Your Progress")

    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.line(MARGIN, PAGE_H - MARGIN - 38, MARGIN + 60, PAGE_H - MARGIN - 38)

    c.setFillColor(TEXT_MUTED)
    c.setFont(TEXT_FONT, 10.5)
    c.drawString(MARGIN, PAGE_H - MARGIN - 58,
                 f"Replay the {total_positions} position"
                 f"{'s' if total_positions != 1 else ''} above on a board. "
                 "Track how you did:")

    # 4 labeled lines for the student to fill in (Score / Correct / Time / Notes)
    line_y = PAGE_H - MARGIN - 110
    label_w = 110
    for label in ("Score:", "Correct:", "Time:", "Notes:"):
        c.setFillColor(TEXT)
        c.setFont(TEXT_FONT_BOLD, 12)
        c.drawString(MARGIN, line_y, label)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.6)
        c.line(MARGIN + label_w, line_y - 2,
               MARGIN + CONTENT_W, line_y - 2)
        line_y -= 36

    # Extra ruled lines for the Notes block
    for _ in range(4):
        c.line(MARGIN, line_y - 2, MARGIN + CONTENT_W, line_y - 2)
        line_y -= 20


def solutions_intro(c: canvas.Canvas) -> None:
    """Section opener for the solutions chapter."""
    c.setFillColor(TEXT)
    c.setFont(TEXT_FONT_BOLD, 28)
    c.drawString(MARGIN, PAGE_H - MARGIN - 30, "Solutions")

    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.line(MARGIN, PAGE_H - MARGIN - 38, MARGIN + 60, PAGE_H - MARGIN - 38)

    c.setFillColor(TEXT_MUTED)
    c.setFont(TEXT_FONT, 10.5)
    c.drawString(MARGIN, PAGE_H - MARGIN - 58,
                 "Each solution is the move you missed in the game itself.")


def solutions_block(c: canvas.Canvas, puzzles: Sequence[BookPuzzle],
                    start_num: int, y_start: float) -> float:
    """Draw a two-column list of (number, move, context). Returns next y."""
    col_gap = 24
    col_w = (CONTENT_W - col_gap) / 2
    line_h = 32
    n = len(puzzles)
    rows_per_col = (n + 1) // 2

    for i, p in enumerate(puzzles):
        col = i // rows_per_col
        row = i % rows_per_col
        x = MARGIN + col * (col_w + col_gap)
        y = y_start - row * line_h

        # Puzzle number (gold, bold, hanging)
        c.setFillColor(GOLD)
        c.setFont(TEXT_FONT_BOLD, 11)
        c.drawString(x, y, f"{start_num + i}.")

        # Move in SAN
        c.setFillColor(TEXT)
        c.setFont(TEXT_FONT_BOLD, 12)
        c.drawString(x + 22, y, p.best_san)

        # Context: opening + opponent
        ctx_bits = []
        if p.opening:
            ctx_bits.append(p.opening)
        if p.opponent and p.game_date:
            ctx_bits.append(f"vs {p.opponent}, {p.game_date}")
        elif p.opponent:
            ctx_bits.append(f"vs {p.opponent}")
        ctx = " · ".join(ctx_bits)
        if ctx:
            c.setFillColor(TEXT_MUTED)
            c.setFont(TEXT_FONT, 9)
            c.drawString(x + 22, y - 12, _truncate(ctx, 52))

    return y_start - rows_per_col * line_h


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


@dataclass(frozen=True)
class PageCounter:
    """Inflates 1-indexed page numbers as we draw."""
    total: int

    def label(self, page_num: int) -> str:
        return f"{page_num} / {self.total}"
