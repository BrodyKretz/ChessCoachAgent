"""Design tokens for the personalized chess book.

One source of truth for page size, margins, palette, and fonts so every
generator produces output with the same house style.
"""

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# --- Page ---------------------------------------------------------------

PAGE_SIZE = LETTER                  # 612 x 792 pt
MARGIN = 54                         # 0.75"
CONTENT_W = PAGE_SIZE[0] - 2 * MARGIN
CONTENT_H = PAGE_SIZE[1] - 2 * MARGIN


# --- Palette ------------------------------------------------------------
# Matched to the ChessWins reference: light gray "dark" squares on a white
# page. Gold accent is from the web app (--gold).

PAGE_BG       = HexColor("#ffffff")
TEXT          = HexColor("#1a1a1a")
TEXT_MUTED    = HexColor("#7a7a7a")
RULE          = HexColor("#d8d8d8")
GOLD          = HexColor("#e2b04a")

SQUARE_LIGHT  = HexColor("#ffffff")
SQUARE_DARK   = HexColor("#d8d8d8")
BOARD_FRAME   = HexColor("#bdbdbd")

PIECE_BLACK   = HexColor("#1a1a1a")
PIECE_WHITE   = HexColor("#ffffff")
PIECE_OUTLINE = HexColor("#1a1a1a")


# --- Fonts --------------------------------------------------------------
# Helvetica is built into ReportLab. For chess glyphs we register Arial
# Unicode which ships with macOS and contains the chess piece codepoints.

TEXT_FONT       = "Helvetica"
TEXT_FONT_BOLD  = "Helvetica-Bold"
CHESS_FONT      = "ChessMeridaUnicode"

_CHESS_FONT_PATH = Path(__file__).parent / "assets" / "ChessMeridaUnicode.ttf"


def register_fonts() -> None:
    """Idempotent font registration. Safe to call from any entry point."""
    if CHESS_FONT in pdfmetrics.getRegisteredFontNames():
        return
    if not _CHESS_FONT_PATH.exists():
        raise RuntimeError(
            f"Chess font missing at {_CHESS_FONT_PATH}. "
            "See pipeline/book/assets/ — Chess Merida Unicode is required."
        )
    pdfmetrics.registerFont(TTFont(CHESS_FONT, str(_CHESS_FONT_PATH)))


# --- Paragraph styles ---------------------------------------------------

def book_styles() -> dict[str, ParagraphStyle]:
    """Named paragraph styles for the workbook-style PDF.

    Voice/visual target: LearningChess - Lessons for Beginners Vol 1.
    Times-family serif body, bold for chapter and lesson headings, italic
    running header. Fill-in lines use a monospaced underline.
    """
    return {
        # Cover-page styles
        "cover_title": ParagraphStyle(
            "cover_title", fontName="Times-Bold", fontSize=42, leading=46,
            textColor=TEXT, spaceAfter=4,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle", fontName="Times-Roman", fontSize=18, leading=22,
            textColor=TEXT, spaceAfter=4,
        ),
        "cover_player": ParagraphStyle(
            "cover_player", fontName="Times-Bold", fontSize=16, leading=20,
            textColor=TEXT, spaceAfter=4,
        ),
        "kicker_dim": ParagraphStyle(
            "kicker_dim", fontName="Times-Bold", fontSize=9, leading=12,
            textColor=TEXT_MUTED, spaceAfter=2,
        ),

        # Body styles for the two-column lesson pages
        "chapter": ParagraphStyle(
            "chapter", fontName="Times-Bold", fontSize=20, leading=24,
            textColor=TEXT, spaceBefore=0, spaceAfter=6,
        ),
        "chapter_centered": ParagraphStyle(
            "chapter_centered", fontName="Times-Bold", fontSize=18, leading=22,
            textColor=TEXT, alignment=1, spaceAfter=10,
        ),
        "lesson_head": ParagraphStyle(
            "lesson_head", fontName="Times-Bold", fontSize=11, leading=14,
            textColor=TEXT, spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "body", fontName="Times-Roman", fontSize=10.5, leading=14,
            textColor=TEXT, spaceAfter=4, alignment=4,   # 4 = justified
        ),
        "body_muted": ParagraphStyle(
            "body_muted", fontName="Times-Roman", fontSize=10.5, leading=14,
            textColor=TEXT_MUTED, spaceAfter=4,
        ),
        "body_indent": ParagraphStyle(
            "body_indent", fontName="Times-Roman", fontSize=10.5, leading=14,
            textColor=TEXT, leftIndent=14, spaceAfter=2,
        ),
        "body_score": ParagraphStyle(
            "body_score", fontName="Times-Roman", fontSize=12, leading=18,
            textColor=TEXT, spaceAfter=4,
        ),
        "fill_in": ParagraphStyle(
            "fill_in", fontName="Times-Bold", fontSize=11, leading=16,
            textColor=TEXT, spaceAfter=8,
        ),
    }
