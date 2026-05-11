"""Render a single chess board diagram as a ReportLab Drawing.

The diagram is composable: the caller supplies a position (FEN) and the
side that should appear at the bottom of the board. The diagram is laid
out so the side to move always plays "up the page" — matching the
ChessWins reference and standard chess publication conventions.
"""

from dataclasses import dataclass

from reportlab.graphics.shapes import Drawing, Group, Rect, String

from .styles import (
    BOARD_FRAME,
    CHESS_FONT,
    PIECE_BLACK,
    SQUARE_DARK,
    SQUARE_LIGHT,
    TEXT_FONT,
    TEXT_MUTED,
    register_fonts,
)


# FEN piece letter -> Unicode glyph in Arial Unicode.
# Uppercase = white pieces (outlined glyphs), lowercase = black (filled).
PIECE_GLYPHS = {
    "K": "♔", "Q": "♕", "R": "♖",
    "B": "♗", "N": "♘", "P": "♙",
    "k": "♚", "q": "♛", "r": "♜",
    "b": "♝", "n": "♞", "p": "♟",
}


@dataclass(frozen=True)
class BoardLayout:
    """Cached pixel measurements for one rendered board."""
    size: float          # total drawing edge (board + coord gutters)
    square: float        # edge of one square
    gutter: float        # space reserved for coordinate labels
    board_edge: float    # edge of just the 8x8 square area
    origin: float        # offset from drawing edge to board edge


def _layout(size: float, gutter_ratio: float = 0.08) -> BoardLayout:
    gutter = size * gutter_ratio
    board_edge = size - 2 * gutter
    return BoardLayout(
        size=size,
        square=board_edge / 8,
        gutter=gutter,
        board_edge=board_edge,
        origin=gutter,
    )


def _parse_fen_placement(fen: str) -> list[list[str]]:
    """Return an 8x8 grid of piece chars (or '') indexed [rank][file].

    grid[0] is rank 8 (top from White's perspective);
    grid[7] is rank 1 (bottom). Files are a..h left-to-right.
    """
    placement = fen.split()[0]
    grid: list[list[str]] = []
    for row in placement.split("/"):
        squares: list[str] = []
        for ch in row:
            if ch.isdigit():
                squares.extend([""] * int(ch))
            else:
                squares.append(ch)
        if len(squares) != 8:
            raise ValueError(f"Bad FEN rank '{row}' in '{fen}'")
        grid.append(squares)
    if len(grid) != 8:
        raise ValueError(f"FEN must have 8 ranks: '{fen}'")
    return grid


def render_board(fen: str, side: str = "white", size: float = 150.0) -> Drawing:
    """Return a Drawing of a chess board diagram.

    Args:
        fen: a FEN string (only the placement field is read).
        side: 'white' or 'black' — which side appears at the bottom.
        size: total edge of the drawing in points (includes coord labels).
    """
    register_fonts()
    if side not in {"white", "black"}:
        raise ValueError(f"side must be 'white' or 'black', got {side!r}")

    L = _layout(size)
    grid = _parse_fen_placement(fen)
    d = Drawing(size, size)
    board = Group()

    # Frame: a faint outline around the 8x8 area helps the eye separate
    # the board from the page when the corner squares happen to be light.
    board.add(Rect(
        L.origin - 0.5, L.origin - 0.5,
        L.board_edge + 1, L.board_edge + 1,
        fillColor=None, strokeColor=BOARD_FRAME, strokeWidth=0.5,
    ))

    # Squares + pieces.
    flip = side == "black"
    piece_pt = L.square * 0.78  # tuned so glyphs fill the square nicely

    for row in range(8):
        for col in range(8):
            # Display coords -> board coords (rank/file in FEN grid).
            rank = (7 - row) if not flip else row     # 0 = rank 8 at top (white view)
            file = col if not flip else (7 - col)

            x = L.origin + col * L.square
            y = L.origin + (7 - row) * L.square  # y grows upward in ReportLab

            is_light = (row + col) % 2 == 0
            board.add(Rect(
                x, y, L.square, L.square,
                fillColor=SQUARE_LIGHT if is_light else SQUARE_DARK,
                strokeColor=None,
            ))

            piece = grid[rank][file]
            if piece:
                glyph = PIECE_GLYPHS.get(piece)
                if glyph is None:
                    continue
                # Center the glyph horizontally; nudge vertically because
                # the chess glyphs sit above the font baseline.
                cx = x + L.square / 2
                cy = y + L.square * 0.22
                s = String(cx, cy, glyph,
                           fontName=CHESS_FONT, fontSize=piece_pt,
                           fillColor=PIECE_BLACK, textAnchor="middle")
                board.add(s)

    # Coordinate labels — all four edges, matching the reference.
    coord_pt = L.square * 0.32
    files = list("abcdefgh") if not flip else list("hgfedcba")
    ranks = list("12345678") if not flip else list("87654321")  # 1 at bottom (white view)

    for col, f in enumerate(files):
        cx = L.origin + col * L.square + L.square / 2
        for cy in (L.origin - L.gutter * 0.55, L.origin + L.board_edge + L.gutter * 0.20):
            board.add(String(cx, cy, f.upper(),
                             fontName=TEXT_FONT, fontSize=coord_pt,
                             fillColor=TEXT_MUTED, textAnchor="middle"))

    for row, r in enumerate(ranks):
        # In display: row 0 is top of board, row 7 is bottom. Ranks list is
        # ordered with index 0 = bottom rank, so reverse for top-down draw.
        cy = L.origin + (7 - row) * L.square + L.square / 2 - coord_pt * 0.35
        rank_label = ranks[7 - row]
        for cx in (L.origin - L.gutter * 0.55, L.origin + L.board_edge + L.gutter * 0.55):
            board.add(String(cx, cy, rank_label,
                             fontName=TEXT_FONT, fontSize=coord_pt,
                             fillColor=TEXT_MUTED, textAnchor="middle"))

    d.add(board)
    return d
