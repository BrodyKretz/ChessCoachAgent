"""Public data shapes consumed by the book layout layer.

Keeping these in their own module makes the layout/render code reusable
across data sources — the host project plugs in its own fetcher and just
hands BookPuzzle instances to layout.puzzle_grid / layout.solutions_block.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BookPuzzle:
    """One position ready for typesetting in a chapter or grid page."""
    puzzle_id: int
    fen: str
    side_to_move: str        # 'white' | 'black'
    best_uci: str
    best_san: str            # eg "Re3#"
    is_mate: bool            # best move delivers checkmate
    move_number: int
    opening: str | None
    opponent: str | None
    game_date: str | None
