"""Extract teachable positions from a session's games using Stockfish.

A "finding" is a single position where the user made a noteworthy mistake
or missed a tactic. The book layer uses these as the source-of-truth for
diagram pages — every diagram comes from a real game the user played.

This module is kept independent of LangGraph so it can be called from
anywhere (pipeline node, CLI tool, tests).
"""

from __future__ import annotations

import asyncio
import io
from dataclasses import dataclass
from typing import Sequence

import chess
import chess.pgn

from utils.stockfish_engine import batch_analyse_game


# Centipawn loss above which a move counts as a blunder for book selection.
BLUNDER_CP = 200

# Cap on how many of the user's moves to analyse per game (perf safeguard).
MAX_MOVES_PER_GAME = 60


@dataclass(frozen=True)
class Finding:
    """One teachable position pulled from a real game."""
    game_index: int           # which game in the session (0-based)
    move_number: int
    fen: str                  # position before the user's move
    side_to_move: str         # 'white' | 'black' — always the user's color here
    played_uci: str
    played_san: str
    best_uci: str
    best_san: str
    cp_loss: int
    theme: str                # 'missed_mate' | 'blunder'
    opening: str | None
    opponent: str | None
    game_date: str | None


async def _findings_for_game(game_idx: int, pgn: str, username: str,
                             depth: int, raw_meta: dict) -> list[Finding]:
    """Analyse one game and return findings for the user's mistakes."""
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        return []

    headers = dict(game.headers)
    white_name = headers.get("White", "").lower()
    user_color = chess.WHITE if username.lower() == white_name else chess.BLACK
    opponent = headers.get("Black" if user_color == chess.WHITE else "White")
    game_date = headers.get("Date") or raw_meta.get("end_time_iso")
    opening = headers.get("Opening")

    # Build (board_before, played_move) only for the user's turns.
    positions: list[tuple[chess.Board, chess.Move]] = []
    move_numbers: list[int] = []
    board = game.board()
    node = game
    half_move = 0
    while node.variations:
        node = node.variations[0]
        half_move += 1
        move = node.move
        is_user_turn = board.turn == user_color
        if is_user_turn and len(positions) < MAX_MOVES_PER_GAME:
            positions.append((board.copy(), move))
            move_numbers.append((half_move + 1) // 2)
        board.push(move)

    if not positions:
        return []

    results = await batch_analyse_game(positions, depth=depth)

    findings: list[Finding] = []
    for (board_before, played), res, mv_num in zip(positions, results, move_numbers):
        cp_loss = int(res.get("cp_loss") or 0)
        best_move = res.get("best_move")
        if best_move is None or cp_loss < BLUNDER_CP:
            # Not severe enough to put in a book; keep the page count tight.
            continue

        # Was the missed move a forced mate?
        is_missed_mate = False
        try:
            after_best = board_before.copy()
            after_best.push(best_move)
            is_missed_mate = after_best.is_checkmate()
        except Exception:
            pass

        try:
            played_san = board_before.san(played)
        except Exception:
            played_san = played.uci()

        findings.append(Finding(
            game_index=game_idx,
            move_number=mv_num,
            fen=board_before.fen(),
            side_to_move="white" if board_before.turn == chess.WHITE else "black",
            played_uci=played.uci(),
            played_san=played_san,
            best_uci=best_move.uci(),
            best_san=res.get("best_san") or best_move.uci(),
            cp_loss=cp_loss,
            theme="missed_mate" if is_missed_mate else "blunder",
            opening=opening,
            opponent=opponent,
            game_date=game_date,
        ))
    return findings


async def _gather(raw_games: Sequence[dict], username: str, depth: int) -> list[Finding]:
    """Run analysis sequentially — keeping one Stockfish process per game.

    Parallelism would help but each process needs its own engine; the
    serial loop is simpler and good enough at this depth.
    """
    out: list[Finding] = []
    for i, g in enumerate(raw_games):
        pgn = g.get("pgn", "")
        if not pgn:
            continue
        try:
            out.extend(await _findings_for_game(i, pgn, username, depth, g))
        except Exception:
            # One bad game shouldn't sink the whole book.
            continue
    return out


def collect_findings(raw_games: Sequence[dict], username: str,
                     depth: int = 12, top_n: int | None = None) -> list[Finding]:
    """Public entry point: returns Findings ranked by severity (mate first, then cp_loss)."""
    if not raw_games:
        return []
    findings = asyncio.run(_gather(raw_games, username, depth))

    # Sort: missed mates first, then by cp_loss desc.
    findings.sort(
        key=lambda f: (0 if f.theme == "missed_mate" else 1, -f.cp_loss),
    )
    if top_n is not None:
        findings = findings[:top_n]
    return findings
