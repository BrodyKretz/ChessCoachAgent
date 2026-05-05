"""
Game session WebSocket handler.
Stockfish plays moves and evaluates quality; Claude explains mistakes and cites principles.
"""
import asyncio
import chess
import json
import re
from anthropic import AsyncAnthropic
from utils.stockfish_engine import get_best_move, analyse_move

client = AsyncAnthropic()

COACH_FLAGS = {
    "off":    [],
    "low":    ["blunder"],
    "medium": ["blunder", "mistake"],
    "high":   ["blunder", "mistake", "inaccuracy"],
}

CHESS_REFERENCES = (
    "Silman's Complete Endgame Course (Silman), "
    "My System (Nimzowitsch), "
    "Chess Fundamentals (Capablanca), "
    "The Amateur's Mind (Silman), "
    "Logical Chess: Move by Move (Chernev), "
    "How to Reassess Your Chess (Silman), "
    "Zurich 1953 (Bronstein), "
    "Dvoretsky's Endgame Manual"
)


# ---------------------------------------------------------------------------
# Board utilities
# ---------------------------------------------------------------------------

def board_to_array(board: chess.Board) -> list:
    out = []
    for rank in range(7, -1, -1):
        row = []
        for file in range(8):
            p = board.piece_at(chess.square(file, rank))
            row.append((("w" if p.color else "b") + p.symbol().upper()) if p else None)
        out.append(row)
    return out


def legal_moves_map(board: chess.Board) -> dict:
    m = {}
    for mv in board.legal_moves:
        src = chess.square_name(mv.from_square)
        m.setdefault(src, []).append(chess.square_name(mv.to_square))
    return m


def apply_uci_moves(fen: str, uci_moves: list[str]) -> list[dict]:
    board = chess.Board(fen)
    steps = [{"fen": board.fen(), "move": None}]
    for uci in uci_moves:
        try:
            mv = chess.Move.from_uci(uci)
            if mv not in board.legal_moves:
                break
            san = board.san(mv)
            board.push(mv)
            steps.append({"fen": board.fen(), "move": san})
        except Exception:
            break
    return steps


# ---------------------------------------------------------------------------
# Stockfish + Claude explanation
# ---------------------------------------------------------------------------

async def explain_mistake(
    fen_before: str,
    player_san: str,
    best_san: str,
    cp_loss: int,
    quality: str,
) -> dict:
    """Ask Claude to explain WHY Stockfish flagged this move, citing real references."""
    prompt = (
        f"You are a chess coach explaining a {quality} to your student.\n\n"
        f"Position (FEN): {fen_before}\n"
        f"Student played: {player_san}\n"
        f"Stockfish's best move: {best_san}\n"
        f"Centipawn loss: {cp_loss}\n\n"
        "Explain in 2-3 sentences why this move is a " + quality + ", "
        "what tactical or positional principle was violated, and what the better move achieves.\n"
        "You MUST cite at least one reference from this list to support your teaching point: "
        f"{CHESS_REFERENCES}\n\n"
        'Respond with ONLY valid JSON:\n'
        '{"explanation":"...","better_explanation":"why best_san is stronger",'
        '"reference":"Author, Book Title"}'
    )
    try:
        r = await client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        m = re.search(r"\{.*\}", r.content[0].text, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception:
        pass
    return {
        "explanation": f"Stockfish evaluated this as a {quality} ({cp_loss} centipawns lost). Best was {best_san}.",
        "better_explanation": f"{best_san} keeps a strong position.",
        "reference": "",
    }


async def build_mistake_packet(
    fen_before: str,
    player_san: str,
    player_move: chess.Move,
    analysis: dict,
    coaching: str,
) -> dict | None:
    flags = COACH_FLAGS.get(coaching, [])
    quality = analysis["quality"]
    if quality == "good" or quality not in flags:
        return None

    explanation_data = await explain_mistake(
        fen_before,
        player_san,
        analysis["best_san"],
        analysis["cp_loss"],
        quality,
    )

    # Build visual sequences
    board_after = chess.Board(fen_before)
    board_after.push(player_move)
    your_seq = [{"fen": fen_before, "move": player_san}, {"fen": board_after.fen(), "move": None}]

    best_move = analysis["best_move"]
    board_best = chess.Board(fen_before)
    board_best.push(best_move)
    better_seq = [{"fen": fen_before, "move": None}, {"fen": board_best.fen(), "move": analysis["best_san"]}]

    ref = explanation_data.get("reference", "")
    full_explanation = explanation_data.get("explanation", "")
    if ref:
        full_explanation += f" (cf. {ref})"

    return {
        "quality":            quality,
        "your_move":          player_san,
        "explanation":        full_explanation,
        "better_move":        analysis["best_san"],
        "better_explanation": explanation_data.get("better_explanation", ""),
        "fen_before":         fen_before,
        "your_sequence":      your_seq,
        "better_sequence":    better_seq,
        "cp_loss":            analysis["cp_loss"],
    }


# ---------------------------------------------------------------------------
# Game loop
# ---------------------------------------------------------------------------

async def run_game(websocket, config: dict):
    difficulty   = config.get("difficulty", "medium")
    coaching     = config.get("coaching", "medium")
    pc_str       = config.get("player_color", "white")
    player_color = chess.WHITE if pc_str == "white" else chess.BLACK
    board        = chess.Board()

    await websocket.send_json({
        "type":         "game_started",
        "board":        board_to_array(board),
        "fen":          board.fen(),
        "player_color": pc_str,
        "legal_moves":  legal_moves_map(board),
    })

    if player_color == chess.BLACK:
        mv = await get_best_move(board, difficulty)
        san = board.san(mv)
        board.push(mv)
        await websocket.send_json({
            "type":  "coach_move",
            "san":   san,
            "from":  chess.square_name(mv.from_square),
            "to":    chess.square_name(mv.to_square),
            "board": board_to_array(board),
            "fen":   board.fen(),
            "legal_moves": legal_moves_map(board),
        })

    while not board.is_game_over():
        msg = await websocket.receive_json()

        if msg.get("type") == "resign":
            await websocket.send_json({
                "type": "game_over", "result": "resigned",
                "board": board_to_array(board), "reason": "resignation",
            })
            return

        if msg.get("type") != "move":
            continue

        try:
            promo = msg.get("promotion")
            mv = chess.Move(
                chess.parse_square(msg["from"]),
                chess.parse_square(msg["to"]),
                promotion=chess.piece_type_from_symbol(promo.upper()) if promo else None,
            )
        except Exception:
            await websocket.send_json({"type": "invalid_move"})
            continue

        if mv not in board.legal_moves:
            await websocket.send_json({"type": "invalid_move"})
            continue

        fen_before = board.fen()
        san        = board.san(mv)
        board.push(mv)

        if board.is_game_over():
            await websocket.send_json({
                "type": "game_over", "result": board.result(),
                "board": board_to_array(board), "reason": _end_reason(board),
            })
            return

        # Confirm the player's move immediately — no waiting for Stockfish
        await websocket.send_json({
            "type":  "move_ok",
            "san":   san,
            "board": board_to_array(board),
            "fen":   board.fen(),
        })

        # Now run Stockfish for coach move + analysis concurrently
        analysis_raw, coach_mv = await asyncio.gather(
            analyse_move(chess.Board(fen_before), mv),
            get_best_move(board, difficulty),
        )

        # Send mistake as a separate message so it doesn't block coach_move
        mistake = await build_mistake_packet(fen_before, san, mv, analysis_raw, coaching)
        if mistake:
            await websocket.send_json({"type": "mistake", "mistake": mistake})

        coach_san = board.san(coach_mv)
        board.push(coach_mv)

        await websocket.send_json({
            "type":  "coach_move",
            "san":   coach_san,
            "from":  chess.square_name(coach_mv.from_square),
            "to":    chess.square_name(coach_mv.to_square),
            "board": board_to_array(board),
            "fen":   board.fen(),
            "legal_moves": legal_moves_map(board),
        })

    await websocket.send_json({
        "type": "game_over", "result": board.result(),
        "board": board_to_array(board), "reason": _end_reason(board),
    })


def _end_reason(b: chess.Board) -> str:
    if b.is_checkmate():              return "checkmate"
    if b.is_stalemate():              return "stalemate"
    if b.is_insufficient_material(): return "insufficient material"
    if b.is_fifty_moves():           return "50-move rule"
    if b.is_repetition():            return "threefold repetition"
    return "draw"
