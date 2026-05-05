"""
Practice content generator.

Puzzles: extracted exclusively from the user's real Chess.com games.
  - Stockfish (depth 16) finds positions where the user missed a tactic.
  - Only tactical best moves are kept (captures, checks, promotions).
  - Positions already winning/losing by >600cp are skipped (game was decided).
  - Returns empty list with a reason string if no puzzles found.

Openings: Claude generates SAN lines, python-chess validates every move.
"""
import chess
import chess.pgn
import io
import json
import re
from anthropic import AsyncAnthropic
from memory.user_store import get_user
from utils.stockfish_engine import batch_analyse_game

client = AsyncAnthropic()

CHESS_REFERENCES = (
    "Silman's Complete Endgame Course (Silman), "
    "My System (Nimzowitsch), "
    "Chess Fundamentals (Capablanca), "
    "The Amateur's Mind (Silman), "
    "Logical Chess: Move by Move (Chernev), "
    "How to Reassess Your Chess (Silman), "
    "Winning Chess Tactics (Seirawan)"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_tactical(board: chess.Board, move: chess.Move) -> bool:
    """True if move is a capture, gives check, or is a promotion."""
    return board.is_capture(move) or board.gives_check(move) or move.promotion is not None


async def _explain(fen: str, best_san: str, you_played: str, cp_loss: int) -> str:
    prompt = (
        f"Chess position (FEN): {fen}\n"
        f"The student played {you_played} but missed {best_san} "
        f"({cp_loss} centipawns lost).\n\n"
        "In 2 sentences explain:\n"
        "1. Why their move was bad (concrete consequence — piece hanging, king exposed, etc.)\n"
        "2. Why the best move is stronger (what it wins or prevents)\n"
        f"Cite ONE book from this list to support your teaching: {CHESS_REFERENCES}\n"
        "Plain text only, 2 sentences maximum."
    )
    try:
        r = await client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return r.content[0].text.strip()
    except Exception:
        return f"You played {you_played} but {best_san} was stronger, winning {cp_loss} centipawns."


# ---------------------------------------------------------------------------
# Game extraction
# ---------------------------------------------------------------------------

async def generate_puzzles(username: str) -> dict:
    """
    Returns {"puzzles": [...], "source": "games"|"none", "message": "..."}
    Always attempts to extract from real games. Never falls back to curated bank.
    """
    if not username:
        return {"puzzles": [], "source": "none",
                "message": "Enter your Chess.com username and click Load to see puzzles from your games."}

    from tools.chess_api import fetch_recent_games

    # Fetch up to 10 recent games across all time controls
    games = fetch_recent_games(username, "all", 10)
    if not games:
        return {"puzzles": [], "source": "none",
                "message": f"No games found for '{username}' on Chess.com. Check the username."}

    # ── Collect positions to analyse ──────────────────────────────────────
    all_positions = []  # [(board_before, played_move, opponent, full_move_num, game_idx)]

    for g_idx, game_data in enumerate(games[:6]):
        pgn_str = game_data.get("pgn", "")
        if not pgn_str:
            continue
        pgn = chess.pgn.read_game(io.StringIO(pgn_str))
        if not pgn:
            continue

        white_name = pgn.headers.get("White", "").lower()
        user_color = chess.WHITE if white_name == username.lower() else chess.BLACK
        opponent   = pgn.headers.get(
            "Black" if user_color == chess.WHITE else "White", "Opponent"
        )

        board    = pgn.board()
        node     = pgn
        half_mv  = 0

        while not node.is_end():
            node    = node.variation(0)
            move    = node.move
            half_mv += 1
            full_mv = (half_mv + 1) // 2

            # User's turn, skip opening (< move 6) and deep endgame (> move 55)
            if board.turn == user_color and 6 <= full_mv <= 55:
                all_positions.append((board.copy(), move, opponent, full_mv))

            board.push(move)

    if not all_positions:
        return {"puzzles": [], "source": "none",
                "message": "Couldn't parse recent games. Try again shortly."}

    # ── Batch Stockfish analysis (single engine, depth 16) ────────────────
    analyses = await batch_analyse_game(
        [(p[0], p[1]) for p in all_positions],
        depth=16,
    )

    # ── Filter for genuine missed tactics ────────────────────────────────
    candidates = []
    for i, (board_before, played_move, opponent, full_mv) in enumerate(all_positions):
        if i >= len(analyses):
            break
        a = analyses[i]

        # Skip if game was already effectively decided before this move
        if a.get("best_eval", 0) is not None and abs(a.get("best_eval", 0)) > 600:
            continue

        # Only keep significant misses
        if a["cp_loss"] < 100:
            continue

        # Best move must be a capture, check, or promotion (clear tactical shot)
        if not _is_tactical(board_before, a["best_move"]):
            continue

        # Skip if best move == what was played (shouldn't happen, but guard)
        if a["best_move"].uci() == played_move.uci():
            continue

        candidates.append((board_before, played_move, opponent, full_mv, a))

    if not candidates:
        return {
            "puzzles": [],
            "source":  "none",
            "message": (
                f"Analyzed {len(all_positions)} positions across your recent games "
                f"but found no clean tactical misses. Play some more games and try again!"
            ),
        }

    # Sort by cp_loss descending — show the biggest missed opportunities first
    candidates.sort(key=lambda x: x[4]["cp_loss"], reverse=True)

    # Deduplicate: skip positions from same game that are within 3 moves of each other
    seen_game_moves: dict = {}
    deduped = []
    for (board_before, played_move, opponent, full_mv, a) in candidates:
        key = opponent
        last = seen_game_moves.get(key, -99)
        if abs(full_mv - last) >= 3:
            deduped.append((board_before, played_move, opponent, full_mv, a))
            seen_game_moves[key] = full_mv
        if len(deduped) >= 5:
            break

    # ── Build puzzle dicts with Claude explanations ───────────────────────
    puzzles = []
    for (board_before, played_move, opponent, full_mv, a) in deduped:
        side          = "white" if board_before.turn == chess.WHITE else "black"
        you_played_san = board_before.san(played_move)
        best_san      = a["best_san"]

        # FEN after the best move (for board reveal on failure)
        board_best = board_before.copy()
        board_best.push(a["best_move"])

        # Legal moves map for click interaction
        lm = {}
        for m in board_before.legal_moves:
            src = chess.square_name(m.from_square)
            lm.setdefault(src, []).append(chess.square_name(m.to_square))

        explanation = await _explain(
            board_before.fen(), best_san, you_played_san, a["cp_loss"]
        )

        puzzles.append({
            "fen":           board_before.fen(),
            "side_to_move":  side,
            "best_move":     best_san,
            "best_move_uci": a["best_move"].uci(),
            "best_move_fen": board_best.fen(),
            "theme":         "Missed Tactic" if a["cp_loss"] >= 200 else "Missed Improvement",
            "hint":          f"You played {you_played_san} vs {opponent} (move {full_mv}) — find the better move.",
            "you_played":    you_played_san,
            "cp_loss":       a["cp_loss"],
            "quality":       a["quality"],
            "explanation":   explanation,
            "legal_moves":   lm,
            "opponent":      opponent,
            "move_num":      full_mv,
            "from_game":     True,
        })

    return {"puzzles": puzzles, "source": "games", "message": ""}


# ---------------------------------------------------------------------------
# Opening lines (unchanged)
# ---------------------------------------------------------------------------

async def generate_opening_lines(username: str) -> list:
    user     = get_user(username) or {}
    white_op = user.get("white_opening", "e4")
    black_e4 = user.get("black_vs_e4",   "1...e5")
    black_d4 = user.get("black_vs_d4",   "1...d5")

    prompt = (
        f"Generate 3 opening lines for a chess student:\n"
        f"- As White: {white_op}\n"
        f"- As Black vs e4: {black_e4}\n"
        f"- As Black vs d4: {black_d4}\n\n"
        "Respond ONLY with a valid JSON array. Each element:\n"
        '{"name":"Opening name","color":"white|black","moves":["e4","e5","Nf3",...],'
        '"description":"2 sentences on main ideas","key_ideas":"concrete goal for this line"}\n\n'
        "Use standard SAN notation. 8-14 moves from the starting position. Main lines only. "
        "Cite a reference book for each line in the description."
    )
    try:
        r = await client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        m = re.search(r"\[.*\]", r.content[0].text, re.DOTALL)
        if not m:
            return []
        raw = json.loads(m.group())
        valid = []
        for line in raw:
            board    = chess.Board()
            sequence = [{"fen": board.fen(), "move": None}]
            good_moves = []
            for san in line.get("moves", []):
                try:
                    board.push(board.parse_san(san))
                    good_moves.append(san)
                    sequence.append({"fen": board.fen(), "move": san})
                except Exception:
                    break
            if good_moves:
                line["moves"]    = good_moves
                line["sequence"] = sequence
                valid.append(line)
        return valid
    except Exception:
        return []
