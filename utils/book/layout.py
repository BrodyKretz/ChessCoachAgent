"""Layout primitives for the personalized 'Key Positions' workbook.

Mirrors the LearningChess - Lessons for Beginners workbook reference:
two-column body, inline mini-boards, italic running header on each page,
chapter openers with a numbered title, fill-in-the-blank move lines, and
a closing 'Test' page with Score / Points / Correct / Time fields.

Uses ReportLab Platypus (BaseDocTemplate + PageTemplate + Flowables) so
content reflows naturally across columns and pages — same engine the
reference uses in spirit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from reportlab.graphics import renderPDF
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)
from reportlab.platypus.flowables import Flowable

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
)


PAGE_W, PAGE_H = PAGE_SIZE

# --- Two-column geometry --------------------------------------------------
COL_GAP = 22
COL_W = (CONTENT_W - COL_GAP) / 2

# Inline board size for two-column body content (matches reference: small,
# fits comfortably inside one column).
BOARD_SIZE = COL_W - 6
SMALL_BOARD_SIZE = 150

HEADER_BAND_H = 22       # space reserved at the top for the italic running header
FOOTER_BAND_H = 22       # space at the bottom for the page number

BODY_TOP = PAGE_H - MARGIN - HEADER_BAND_H
BODY_BOTTOM = MARGIN + FOOTER_BAND_H
BODY_H = BODY_TOP - BODY_BOTTOM


# --- Custom flowable wrapping a chess diagram ----------------------------

class BoardFlowable(Flowable):
    """A chess diagram you can drop straight into a Platypus story.

    The reference workbook places boards inline between paragraphs, often
    centered within a column. This flowable reports its own width/height
    so Platypus knows how much vertical space to reserve.
    """

    def __init__(self, fen: str, side: str = "white",
                 size: float = SMALL_BOARD_SIZE, h_align: str = "CENTER"):
        super().__init__()
        self.fen = fen
        self.side = side
        self.size = size
        self.width = size
        self.height = size
        self.hAlign = h_align

    def wrap(self, avail_w, avail_h):
        # If the requested size exceeds the column, shrink to fit.
        if self.size > avail_w:
            self.size = avail_w
            self.width = self.height = self.size
        return (self.width, self.height)

    def draw(self):
        d = render_board(self.fen, side=self.side, size=self.size)
        renderPDF.draw(d, self.canv, 0, 0)


# --- Static page furniture (header / footer / cover) ---------------------

def draw_running_header(canvas, doc) -> None:
    """Italic 'Chess Coach' kicker on the left, volume tag on the right."""
    canvas.saveState()
    canvas.setFont("Times-Italic", 10)
    canvas.setFillColor(TEXT_MUTED)
    y = PAGE_H - MARGIN + 4
    canvas.drawString(MARGIN, y, "Chess Coach — Personalized Lessons")
    canvas.drawRightString(PAGE_W - MARGIN, y,
                           "Volume: Key Positions")
    canvas.setFont(TEXT_FONT, 9)
    canvas.drawCentredString(PAGE_W / 2, MARGIN - 10, str(doc.page))
    canvas.restoreState()


def draw_cover_chrome(canvas, doc) -> None:
    """Cover page chrome — gold tab + series tag. No running header."""
    canvas.saveState()
    # Gold accent bar
    canvas.setFillColor(GOLD)
    canvas.rect(MARGIN, PAGE_H - MARGIN - 8, 80, 4, stroke=0, fill=1)
    # Series tag below the bar
    canvas.setFillColor(TEXT_MUTED)
    canvas.setFont(TEXT_FONT_BOLD, 10)
    canvas.drawString(MARGIN, PAGE_H - MARGIN - 28,
                      "CHESS COACH · PERSONALIZED LESSON")
    canvas.restoreState()


def build_doc(out_path: str, title: str, author: str) -> BaseDocTemplate:
    """Construct the document with cover + two-column body templates."""
    doc = BaseDocTemplate(
        str(out_path),
        pagesize=PAGE_SIZE,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN + HEADER_BAND_H,
        bottomMargin=MARGIN + FOOTER_BAND_H,
        title=title, author=author,
    )

    cover_frame = Frame(
        MARGIN, MARGIN,
        CONTENT_W, PAGE_H - 2 * MARGIN,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        showBoundary=0, id="cover",
    )

    left_frame = Frame(
        MARGIN, BODY_BOTTOM,
        COL_W, BODY_H,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        showBoundary=0, id="left",
    )
    right_frame = Frame(
        MARGIN + COL_W + COL_GAP, BODY_BOTTOM,
        COL_W, BODY_H,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        showBoundary=0, id="right",
    )

    cover_template = PageTemplate(
        id="cover", frames=[cover_frame], onPage=draw_cover_chrome,
    )
    body_template = PageTemplate(
        id="body", frames=[left_frame, right_frame], onPage=draw_running_header,
    )
    doc.addPageTemplates([cover_template, body_template])
    return doc


# --- Cover content flowables --------------------------------------------

def cover_story(styles: dict, title: str, subtitle: str,
                player: str, period: str) -> list:
    """Flowables for the cover page (uses the cover frame)."""
    return [
        Spacer(1, 2.4 * inch),
        Paragraph(title, styles["cover_title"]),
        Paragraph(subtitle, styles["cover_subtitle"]),
        Spacer(1, 0.18 * inch),
        HRFlowable(width=CONTENT_W, thickness=0.4, color=RULE),
        Spacer(1, 2.0 * inch),
        Paragraph("BUILT FROM YOUR OWN GAMES", styles["kicker_dim"]),
        Paragraph(player, styles["cover_player"]),
        Paragraph(period, styles["body_muted"]),
        NextPageTemplate("body"),
        PageBreak(),
    ]


# --- Section opener (chapter) -------------------------------------------

def section_opener_story(styles: dict, number: int, title: str,
                         intro: str, q_lead: str | None,
                         q_options: list[str]) -> list:
    """Chapter opener: '5. Mate in One Move' style heading + intro + Q1."""
    parts: list = [
        Paragraph(f"{number}. {title}", styles["chapter"]),
        Spacer(1, 6),
        Paragraph(intro, styles["body"]),
    ]
    if q_lead and q_options:
        parts.append(Spacer(1, 8))
        parts.append(Paragraph(f"<b>Q1. {q_lead}</b>", styles["body"]))
        parts.append(Spacer(1, 2))
        for i, opt in enumerate(q_options, 1):
            parts.append(Paragraph(f"{i}. {opt}", styles["body_indent"]))
    return parts


# --- Lesson (one position) ----------------------------------------------

@dataclass(frozen=True)
class Lesson:
    """All copy + data needed to typeset one position lesson."""
    heading: str            # e.g. "Position 1 — White to play"
    intro: str              # 1-2 sentences setting up the position
    fen: str
    side: str               # 'white' | 'black'
    prompt: str             # e.g. "Find the best move."
    fill_in: str            # e.g. "1. __________" or "1. … __________"
    explanation: str        # post-answer prose (what was played + best move)


def lesson_story(styles: dict, lesson: Lesson) -> list:
    """Flowables for one lesson, kept together so it doesn't split mid-board."""
    # Use a column-narrowed board so it fits comfortably even after padding.
    board_size = min(BOARD_SIZE, 160)
    return [
        KeepTogether([
            Paragraph(f"<b>{lesson.heading}</b>", styles["lesson_head"]),
            Spacer(1, 3),
            Paragraph(lesson.intro, styles["body"]),
            Spacer(1, 4),
            BoardFlowable(lesson.fen, side=lesson.side, size=board_size),
            Spacer(1, 4),
            Paragraph(lesson.prompt, styles["body"]),
            Paragraph(lesson.fill_in, styles["fill_in"]),
        ]),
        Spacer(1, 4),
        Paragraph(lesson.explanation, styles["body"]),
        Spacer(1, 14),
    ]


# --- Prose chapter (no positions, just markdown body) -------------------

def prose_chapter_story(styles: dict, number: int, title: str,
                        lead: str, body_flowables: list) -> list:
    """Chapter opener + a prose body. Used for analyst/coach markdown."""
    return [
        Paragraph(f"{number}. {title}", styles["chapter"]),
        Spacer(1, 6),
        Paragraph(lead, styles["body"]),
        Spacer(1, 8),
        *body_flowables,
        Spacer(1, 8),
    ]


# --- Games-summary chapter ----------------------------------------------

def games_chapter_story(styles: dict, number: int,
                        username: str,
                        games: list[dict],
                        time_control: str) -> list:
    """Chapter 1: an at-a-glance log of the games this session was built from."""
    if not games:
        return []

    record = {"win": 0, "loss": 0, "draw": 0}
    for g in games:
        record[g.get("outcome", "draw")] = record.get(g.get("outcome", "draw"), 0) + 1

    lead = (
        f"This workbook is built from your last {len(games)} {time_control} games. "
        f"You finished {record['win']}–{record['loss']}–{record['draw']} "
        "(wins–losses–draws). Take a look at the table below — every diagram and "
        "lesson later in this book comes from one of these games."
    )

    parts: list = [
        Paragraph(f"{number}. Your Recent Games", styles["chapter"]),
        Spacer(1, 6),
        Paragraph(lead, styles["body"]),
        Spacer(1, 10),
    ]

    # One line per game, formatted like a workbook bullet.
    for i, g in enumerate(games, 1):
        color = g.get("player_color", "?").title()
        opp = (g.get("black_player") if g.get("player_color") == "white"
               else g.get("white_player")) or "Unknown"
        opening = g.get("opening_name") or "Unknown opening"
        outcome = g.get("outcome", "draw").title()
        moves = g.get("total_moves", "?")
        line = (
            f"<b>Game {i}</b> — {color} vs <b>{opp}</b>. "
            f"<i>{opening}</i>. <b>{outcome}</b> in {moves} moves."
        )
        parts.append(Paragraph(line, styles["body_bullet"]))
    return parts


# --- Closing 'Test' page ------------------------------------------------

def test_page_story(styles: dict, total_positions: int) -> list:
    """Closing test/scoring page (Score / Points / Correct / Time)."""
    fill_w = 140  # px of underline
    score_line = "<font color='#7a7a7a'>" + ("_" * 22) + "</font>"

    label_lines = [
        ("Score:",   score_line + " %"),
        ("Points:",  score_line),
        ("Correct:", score_line),
        ("Time:",    score_line),
    ]

    parts: list = [
        Paragraph("Test", styles["chapter_centered"]),
        Spacer(1, 8),
        Paragraph(
            f"Replay the {total_positions} position"
            f"{'s' if total_positions != 1 else ''} above on a board and "
            "see how you do. Track your result below.",
            styles["body"]),
        Spacer(1, 20),
    ]
    for label, line in label_lines:
        parts.append(Paragraph(
            f"<b>{label}</b>&nbsp;&nbsp;&nbsp;&nbsp;{line}",
            styles["body_score"],
        ))
        parts.append(Spacer(1, 10))
    return parts
