"""
Stockfish wrapper using python-chess async engine interface.
"""
import chess
import chess.engine

import os
STOCKFISH_PATH = os.environ.get("STOCKFISH_PATH", "/opt/homebrew/bin/stockfish")

SKILL_MAP = {
    "easy":   3,
    "medium": 8,
    "hard":   15,
    "expert": 20,
}

ANALYSIS_DEPTH = 18


async def _open():
    """Open a fresh async Stockfish process."""
    _, engine = await chess.engine.popen_uci(STOCKFISH_PATH)
    return engine


def _cp(score_obj, turn: chess.Color) -> int:
    """Convert a PovScore to centipawns from `turn`'s perspective."""
    s = score_obj.white() if turn == chess.WHITE else score_obj.black()
    if s.is_mate():
        return 10000 if s.mate() > 0 else -10000
    return s.score()


async def get_best_move(board: chess.Board, difficulty: str) -> chess.Move:
    """Return Stockfish's move at the given skill level."""
    engine = await _open()
    try:
        await engine.configure({"Skill Level": SKILL_MAP.get(difficulty, 8)})
        result = await engine.play(board, chess.engine.Limit(time=0.5))
        return result.move
    finally:
        await engine.quit()


async def analyse_move(board_before: chess.Board, move: chess.Move,
                       depth: int = ANALYSIS_DEPTH) -> dict:
    """
    Analyse a player's move against Stockfish's best.
    Returns: best_move, best_san, cp_loss, quality.
    """
    engine = await _open()
    try:
        await engine.configure({"Skill Level": 20})

        # Best move + eval in one analyse call (pv[0] == best move)
        info_before = await engine.analyse(
            board_before,
            chess.engine.Limit(depth=depth),
            info=chess.engine.INFO_ALL,
        )
        pv = info_before.get("pv", [])
        best_move = pv[0] if pv else move
        best_san  = board_before.san(best_move)
        best_eval = _cp(info_before["score"], board_before.turn)

        # Eval after the played move (opponent's turn → negate)
        board_after = board_before.copy()
        board_after.push(move)
        info_after  = await engine.analyse(board_after, chess.engine.Limit(depth=depth))
        played_eval = -_cp(info_after["score"], board_after.turn)

        cp_loss = max(0, best_eval - played_eval) if (best_eval is not None and played_eval is not None) else 0
        quality = _quality(cp_loss)

        return {
            "best_move":   best_move,
            "best_san":    best_san,
            "best_eval":   best_eval,
            "played_eval": played_eval,
            "cp_loss":     cp_loss,
            "quality":     quality,
        }
    finally:
        await engine.quit()


async def batch_analyse_game(positions: list, depth: int = 12) -> list:
    """
    Analyse multiple (board_before, played_move) pairs with ONE engine instance.
    Much faster than opening a new process per position.

    positions: list of (chess.Board, chess.Move) — board is before the move.
    Returns:   list of dicts with best_move, best_san, cp_loss, quality.
    """
    engine = await _open()
    results = []
    try:
        await engine.configure({"Skill Level": 20})
        for board_before, played_move in positions:
            info_before = await engine.analyse(
                board_before,
                chess.engine.Limit(depth=depth),
                info=chess.engine.INFO_ALL,
            )
            pv = info_before.get("pv", [])
            best_move = pv[0] if pv else played_move
            try:
                best_san = board_before.san(best_move)
            except Exception:
                best_san = best_move.uci()
            best_eval = _cp(info_before["score"], board_before.turn)

            board_after = board_before.copy()
            board_after.push(played_move)
            info_after  = await engine.analyse(board_after, chess.engine.Limit(depth=depth))
            played_eval = -_cp(info_after["score"], board_after.turn)

            cp_loss = max(0, best_eval - played_eval) if (best_eval is not None and played_eval is not None) else 0

            results.append({
                "best_move":   best_move,
                "best_san":    best_san,
                "best_eval":   best_eval,
                "played_eval": played_eval,
                "cp_loss":     cp_loss,
                "quality":     _quality(cp_loss),
            })
    finally:
        await engine.quit()
    return results


async def get_puzzle_best_move(board: chess.Board, depth: int = 20) -> tuple:
    """Return (best_move, cp_advantage) for a puzzle position."""
    engine = await _open()
    try:
        await engine.configure({"Skill Level": 20})
        info = await engine.analyse(board, chess.engine.Limit(depth=depth), info=chess.engine.INFO_ALL)
        pv   = info.get("pv", [])
        best = pv[0] if pv else None
        if best is None:
            result = await engine.play(board, chess.engine.Limit(depth=depth))
            best   = result.move
        advantage = _cp(info["score"], board.turn)
        return best, advantage
    finally:
        await engine.quit()


def _quality(cp_loss: int) -> str:
    if cp_loss >= 200: return "blunder"
    if cp_loss >= 80:  return "mistake"
    if cp_loss >= 30:  return "inaccuracy"
    return "good"
