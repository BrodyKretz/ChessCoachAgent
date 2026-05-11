"""Smoke-test page that should visually match the ChessWins reference.

Run with:
    python -m utils.book.smoke_test

Outputs to outputs/book_smoke.pdf.
"""

from pathlib import Path

from reportlab.pdfgen import canvas

from .board import render_board
from .styles import (
    CONTENT_W,
    GOLD,
    MARGIN,
    PAGE_SIZE,
    TEXT,
    TEXT_FONT,
    TEXT_FONT_BOLD,
    TEXT_MUTED,
    register_fonts,
)


SMOKE_PUZZLES = [
    ("white", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"),
    ("black", "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR"),
    ("white", "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R"),
    ("black", "r1bqkbnr/pp1ppppp/2n5/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R"),
    ("white", "5rk1/p4ppp/8/8/8/8/PP3PPP/4R1K1"),
    ("black", "6k1/5ppp/8/8/8/8/5PPP/4R2K"),
    ("white", "r3k2r/pp1bbppp/2nq1n2/3pp3/3PP3/2NQ1N2/PP1BBPPP/R3K2R"),
    ("black", "8/5pk1/6p1/8/8/5PP1/6K1/4Q3"),
    ("white", "4r1k1/5ppp/8/8/8/8/5PPP/Q5K1"),
]


def _draw_page_header(c: canvas.Canvas, brand: str, title: str) -> None:
    page_w, page_h = PAGE_SIZE
    brand_y = page_h - MARGIN + 6
    c.setFillColor(TEXT)
    c.setFont(TEXT_FONT_BOLD, 11)
    c.drawString(MARGIN, brand_y, brand)
    c.setFillColor(GOLD)
    c.rect(MARGIN, brand_y - 5, 28, 2, stroke=0, fill=1)

    c.setFillColor(TEXT)
    c.setFont(TEXT_FONT_BOLD, 22)
    c.drawCentredString(page_w / 2, page_h - MARGIN - 8, title)


def _draw_page_footer(c: canvas.Canvas, page_num: int, total: int) -> None:
    page_w, _ = PAGE_SIZE
    c.setFillColor(TEXT_MUTED)
    c.setFont(TEXT_FONT, 9)
    c.drawCentredString(page_w / 2, MARGIN / 2, f"{page_num} / {total}")


def _draw_grid_page(c: canvas.Canvas, puzzles, start_num: int = 1) -> None:
    cols, rows = 3, 3
    cell_gap_x = 18
    cell_gap_y = 28
    grid_top = PAGE_SIZE[1] - MARGIN - 56

    cell_w = (CONTENT_W - cell_gap_x * (cols - 1)) / cols
    board_size = cell_w
    caption_h = 14
    cell_h = board_size + caption_h + 4

    for i, (side, fen) in enumerate(puzzles[: cols * rows]):
        r = i // cols
        col = i % cols
        x = MARGIN + col * (cell_w + cell_gap_x)
        y_top = grid_top - r * (cell_h + cell_gap_y)
        y_board = y_top - board_size

        d = render_board(fen, side=side, size=board_size)
        d.drawOn(c, x, y_board)

        c.setFillColor(TEXT)
        c.setFont(TEXT_FONT, 10.5)
        label = f"{start_num + i}. {'White' if side == 'white' else 'Black'} to play"
        c.drawCentredString(x + board_size / 2, y_board - caption_h, label)


def build_smoke_pdf(output: Path) -> Path:
    register_fonts()
    output.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output), pagesize=PAGE_SIZE)
    _draw_page_header(c, "Chess Coach", "Mate In One Move Puzzles")
    _draw_grid_page(c, SMOKE_PUZZLES, start_num=1)
    _draw_page_footer(c, 1, 1)
    c.showPage()
    c.save()
    return output


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[2] / "outputs" / "book_smoke.pdf"
    path = build_smoke_pdf(out)
    print(f"wrote {path}")
