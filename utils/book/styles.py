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
    """Return the named paragraph styles used throughout the book."""
    return {
        "page_title": ParagraphStyle(
            "page_title", fontName=TEXT_FONT, fontSize=22, leading=28,
            textColor=TEXT, alignment=1, spaceAfter=18,
        ),
        "chapter_title": ParagraphStyle(
            "chapter_title", fontName=TEXT_FONT_BOLD, fontSize=28, leading=34,
            textColor=TEXT, spaceAfter=16,
        ),
        "section": ParagraphStyle(
            "section", fontName=TEXT_FONT_BOLD, fontSize=14, leading=18,
            textColor=TEXT, spaceBefore=12, spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "body", fontName=TEXT_FONT, fontSize=10.5, leading=15,
            textColor=TEXT, spaceAfter=8,
        ),
        "caption": ParagraphStyle(
            "caption", fontName=TEXT_FONT, fontSize=10, leading=12,
            textColor=TEXT, alignment=1, spaceBefore=6,
        ),
        "muted": ParagraphStyle(
            "muted", fontName=TEXT_FONT, fontSize=9, leading=12,
            textColor=TEXT_MUTED,
        ),
    }
