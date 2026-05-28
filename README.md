# Chess Coach Agent

**A multi-agent AI system that analyzes your Chess.com games, generates personalized coaching plans, and lets you play and practice against an AI coach — all in a custom dark-themed web UI.**

Built with Python, LangGraph, and Claude (Anthropic). Three specialized AI agents collaborate in a pipeline — Analyst → Coach → Critic — each with a distinct role. The Critic can reject weak coaching reports and send them back to the Coach for revision. A separate real-time game engine lets you play chess against Coach King with live coaching feedback. A dedicated practice page serves AI-generated tactics puzzles and opening trainer lines.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [The Three Agents](#3-the-three-agents)
4. [LangGraph: How the Pipeline Works](#4-langgraph-how-the-pipeline-works)
5. [Play vs Coach King](#5-play-vs-coach-king)
6. [Practice Mode](#6-practice-mode)
7. [User Memory System](#7-user-memory-system)
8. [Time Pressure Detection](#8-time-pressure-detection)
9. [Setup & Installation](#9-setup--installation)
10. [Usage](#10-usage)
11. [Output Files](#11-output-files)
12. [File Structure](#12-file-structure)
13. [Version History](#13-version-history)

---

## 1. Project Overview

Chess improvement requires knowing *what* to work on — not just playing more games. This project automates the analysis step: it fetches your recent Chess.com games, identifies patterns and recurring mistakes across all of them, interviews you about your goals and preferred openings, then generates a detailed, personalized coaching plan.

Beyond the coaching report, V3 adds two fully interactive features:

- **Play vs Coach King:** A full chess game against an AI opponent (powered by Claude Haiku for speed). After every player mistake, Coach King slides up a panel in the browser explaining the error, shows the move sequence on a mini board, and lets you step through "what you played" vs "the better move" before minimizing and continuing the game.
- **Practice Mode:** AI-generated tactics puzzles (5 per session, verified by python-chess) and opening trainer lines (server-pre-computed FEN sequences you step through on a board viewer).

**What makes it interesting architecturally:**
- Three Claude instances run sequentially, each with a specific role and prompt
- A feedback loop ensures quality: the Critic grades the Coach's output and can force a revision
- A separate async WebSocket game loop handles real-time chess with concurrent Claude calls (analyze player's move and calculate the coach's response simultaneously using `asyncio.gather`)
- State flows through the LangGraph pipeline in a single typed dictionary — no global variables, no shared mutable state
- Board rendering is done entirely server-side with python-chess; the browser only receives 8×8 arrays and renders Unicode pieces — no chess.js dependency
- User memory persists across sessions via SQLite, so preferences don't need to be re-entered

---

## 2. Architecture

### Coaching Session Pipeline (LangGraph)

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph StateGraph                      │
│                                                             │
│  [START]                                                    │
│     │                                                       │
│     ▼                                                       │
│  memory_check       ← checks SQLite for returning user      │
│     │                                                       │
│     ▼                                                       │
│  analyst_interview  ← asks: how many games? time control?   │
│     │                                                       │
│     ▼                                                       │
│  fetch_games        ← Chess.com API + PGN parser            │
│     │                                                       │
│     ▼                                                       │
│  analyze_games      ← ANALYST AGENT (Claude Sonnet)         │
│     │                                                       │
│     ▼                                                       │
│  coach_interview    ← asks: goals? opening preferences?     │
│     │                                                       │
│     ▼                                                       │
│  generate_lesson ◄──────────────────────────────┐          │
│     │                                           │          │
│     ▼                                           │          │
│  critic_review      ← CRITIC AGENT (Claude)     │          │
│     │                                           │          │
│     ├── score < 70 ──── REGENERATE ─────────────┘          │
│     │                                                       │
│     └── score ≥ 70 ─── APPROVED                            │
│                           │                                 │
│                           ▼                                 │
│                      format_output   ← saves MD + PDF       │
│                           │                                 │
│                         [END]                               │
└─────────────────────────────────────────────────────────────┘
```

### Web Server

```
FastAPI (api/server.py)
├── GET  /            → index.html  (coaching session UI)
├── GET  /play        → play.html   (play vs Coach King)
├── GET  /practice    → practice.html (puzzles + openings)
├── GET  /static/*    → frontend/   (CSS, JS, assets)
├── WS   /ws          → coaching session pipeline (LangGraph)
├── WS   /ws/game     → real-time chess game loop
└── WS   /ws/practice → puzzle + opening line generation
```

### Play vs Coach King — Real-Time Game Loop

```
Client sends move → WebSocket → api/routes/play.py
                                    │
                    asyncio.gather ─┤
                                    ├── analyze_move()   (Claude Haiku)
                                    └── get_coach_move() (Claude Haiku)
                                    │
                    Results merged ─┤
                                    ├── send "move_ok" + mistake (if any)
                                    └── send "coach_move" with next position
```

---

## 3. The Three Agents

### Analyst Agent (`agents/analyst.py`)

**Role:** Identify patterns across all analyzed games — not a move-by-move critique of one game, but recurring themes.

**Input:** List of parsed game summaries (opening played, move string with time-pressure markers, result)

**Output:** Structured report covering opening patterns, middlegame mistakes, endgame technique, time management, and the top 3 priority areas.

**Key design decision:** The Analyst is given the full move string for each game with markers on moves made under severe time pressure. This allows Claude to distinguish errors caused by time scrambles from strategic misunderstandings, which the Coach later uses to prioritize advice.

---

### Coach Agent (`agents/coach.py`)

**Role:** Interview the player about their goals and preferred openings, then generate a personalized training plan.

**Two-step process:**
1. `coach_interview_node` — collects: main goal, preferred first move as White, preferred defense against e4, preferred defense against d4, and focus areas.
2. `generate_lesson_node` — Claude generates a full coaching report using both the Analyst's findings and the player's stated goals.

**On retry:** If the Critic rejects the report, `generate_lesson_node` runs again with the critic's feedback included in the prompt. Claude is told exactly what was weak and must address it.

---

### Critic Agent (`agents/critic.py`)

**Role:** Quality-control gate. Grades the coaching report on four criteria:

| Criterion | Max | Description |
|-----------|-----|-------------|
| Specificity | 25 | References actual game patterns, not generic advice |
| Goal Alignment | 25 | Addresses the player's stated openings and focus areas |
| Actionability | 25 | Recommendations are concrete with specific steps |
| Time Pressure Handling | 25 | Time-pressured mistakes are correctly deprioritized |

**Scoring:** Total out of 100. Pass threshold: 70. Below 70 triggers a regeneration request with specific written feedback. Maximum 3 regeneration attempts — after that, best available version is accepted.

**Output:** Structured JSON with scores, total, approved boolean, feedback string, strengths, and weaknesses.

---

## 4. LangGraph: How the Pipeline Works

LangGraph is a library for building stateful, multi-step AI workflows as a directed graph. This project uses its core primitives:

### StateGraph
The entire application state lives in a single `ChessCoachState` TypedDict (defined in `graph/state.py`). Every node receives the full current state and returns only the keys it wants to update. LangGraph merges those updates before passing state to the next node.

```python
class ChessCoachState(TypedDict):
    username: str
    is_returning_user: bool
    user_data: dict
    num_games: int
    time_control: str
    raw_games: list
    game_summaries: list
    analysis_report: str       # written by Analyst
    player_goals: dict         # written by Coach interview
    coaching_report: str       # written by Coach
    critique_result: dict      # written by Critic
    critique_attempts: int
    final_report: str
    messages: Annotated[list[BaseMessage], add_messages]
```

### Nodes
Each node is a plain Python function with the signature `(state: ChessCoachState) -> dict`. The returned dict contains only the state keys this node is responsible for updating.

### Edges
- `add_edge(A, B)` — A always goes to B
- `add_conditional_edges(A, routing_fn, {"outcome": B, ...})` — the routing function inspects state and returns a string key that maps to the next node

### The Feedback Loop
```python
workflow.add_conditional_edges(
    "critic_review",
    should_regenerate,          # returns "regenerate" or "approved"
    {
        "regenerate": "generate_lesson",   # back to Coach
        "approved": "format_output",       # forward to output
    },
)
```

---

## 5. Play vs Coach King

### How It Works

When you open `/play`, you configure:
- **Your color** (White or Black)
- **Difficulty** — Easy / Medium / Hard / Expert. Each maps to a different Claude Haiku prompt temperature and skill instruction set.
- **Coaching assistance** — Off / Low (blunders only) / Medium / High (all inaccuracies). Controls the move quality threshold for triggering the mistake panel.

The game runs over a WebSocket (`/ws/game`). For every player move:

1. **python-chess** validates the move server-side (no chess.js in the browser)
2. Two Claude Haiku calls run concurrently via `asyncio.gather`:
   - `analyze_move()` — evaluates the player's move and returns a structured mistake object if it's below the coaching threshold
   - `get_coach_move()` — generates Coach King's next move at the configured difficulty
3. The server sends `move_ok` (with optional mistake), then `coach_move` when ready

### Mistake Panel

When a mistake is detected, a panel slides up from the bottom of the screen:
- **Badge** shows BLUNDER / MISTAKE / INACCURACY
- **Explanation** — what went wrong and why
- **Mini board** — shows the position with step-through navigation (← →)
- **Two tabs**: "What you played" and "Better move" — each showing a pre-computed move sequence as `{fen, move}` steps
- Click "Got it — Continue ✓" to minimize and resume the game from where you left off

### Difficulty Levels

| Level | Behavior |
|-------|----------|
| Easy | Claude plays randomly-ish, avoids complex tactics |
| Medium | Solid moves, some tactics but no deep calculation |
| Hard | Strong play, prefers active pieces and initiative |
| Expert | Best move in most positions, aggressive style |

### Board Rendering

No external chess library is used in the browser. The server sends:
- `board`: 8×8 array of piece codes (`wK`, `bP`, `null`, etc.)
- `legal_moves`: `{squareName: [targetSquares...]}` for click-based move selection

The `ChessBoard` class in `chess_utils.js` renders Unicode chess pieces on a CSS grid. Highlights (selected square, legal moves, last move, mistake squares) are applied via CSS classes.

---

## 6. Practice Mode

### Tactics Puzzles

Opening `/practice` and clicking "Load Practice" triggers a WebSocket call to `/ws/practice`. Claude Haiku generates 5 tactical puzzles, each validated by python-chess before being sent to the browser (if the FEN is illegal or the best_move isn't a legal move, the puzzle is discarded).

Each puzzle shows:
- A mini board in the position (oriented for the side to move)
- The tactical theme (fork, pin, skewer, back rank, etc.)
- A SAN input field — type your move and hit Check or Enter
- Correct/wrong feedback with the full explanation revealed after answering

### Opening Trainer

Claude Haiku generates 3 opening lines based on your saved preferences (white opening choice, defenses vs e4 and d4). The server validates each move with python-chess and pre-computes the FEN for every step in the line, then sends `sequence: [{fen, move}, ...]`.

The browser displays:
- A full-size board viewer with ← → step navigation
- Move chips showing the full move sequence (click "Study on board" to load it)
- The opening's description and key ideas

---

## 7. User Memory System

**Implementation:** SQLite database at `data/users.db` (created automatically on first run).

**Schema:**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chess_username TEXT UNIQUE NOT NULL,
    linked_at TEXT NOT NULL,
    last_session TEXT,
    preferred_time_control TEXT DEFAULT 'all',
    white_opening TEXT,
    black_vs_e4 TEXT,
    black_vs_d4 TEXT,
    goals TEXT
)
```

**How it works:**
- When you enter your username for the first time, a row is created
- After each session, your preferences (openings, time control, goals) are updated
- On the next run, entering the same username loads saved preferences and pre-fills prompts
- The Coach interview still shows saved values and lets you press Enter to keep them or type a new answer
- The Practice page uses saved opening preferences to generate relevant opening lines

---

## 8. Time Pressure Detection

Chess.com PGN files include clock annotations in move comments:
```
1. e4 {[%clk 0:05:00]} e5 {[%clk 0:04:58]}
```

The PGN parser (`tools/pgn_parser.py`) extracts these and flags any move where the player had fewer than 30 seconds remaining:

```python
TIME_PRESSURE_THRESHOLD_SECONDS = 30
```

Flagged moves are marked with `⏰` in the move string sent to agents. The Coach is explicitly instructed: *"Note time-pressure mistakes but deprioritize them vs. non-time-pressure errors."* This prevents the system from drilling a player on mistakes they only make when rushing.

---

## 9. Setup & Installation

### Prerequisites
- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com)
- A Chess.com account (free, no API key needed — the public API is open)

### Install

```bash
cd ChessCoachAgent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configure

```bash
# Create .env file and add your key:
echo 'ANTHROPIC_API_KEY=your_key_here' > .env
```

---

## 10. Usage

### Web UI (recommended)
```bash
python run_web.py
# Visit http://127.0.0.1:8000
```

Three pages available:
- **`/`** — Coaching session (full analysis pipeline with live agent visualization)
- **`/play`** — Play vs Coach King (interactive game with real-time coaching)
- **`/practice`** — Puzzles & Openings (AI-generated tactics and opening trainer)

### CLI (coaching pipeline only)
```bash
python main.py
```

**Session flow:**
1. Enter your Chess.com username (or press Enter if returning)
2. Choose how many games to analyze (1–50, default 10)
3. Choose time control: blitz / bullet / rapid / daily / all
4. Wait for games to be fetched and analyzed
5. Answer Coach's questions about your goals and openings
6. Wait for the coaching report to be generated and critiqued
7. Find your report in `outputs/`

---

## 11. Output Files

| File | Description |
|------|-------------|
| `outputs/{username}_report_{timestamp}.md` | Full coaching report in Markdown |
| `outputs/{username}_workbook_{timestamp}.pdf` | Personalized coaching workbook (cover + game summary + analysis + tactics + plan) |
| `data/users.db` | SQLite user memory database (local, gitignored) |

---

## 12. File Structure

```
ChessCoachAgent/
├── agents/
│   ├── analyst.py          # Analyst agent node
│   ├── coach.py            # Coach interview + lesson generation nodes
│   └── critic.py           # Critic review node + routing function
├── api/
│   ├── server.py           # FastAPI app (routes + WebSocket endpoints)
│   ├── session.py          # Coaching session runner (ThreadPoolExecutor bridge)
│   └── routes/
│       ├── play.py         # Real-time game loop (python-chess + Claude Haiku)
│       └── practice.py     # Puzzle + opening line generator (Claude Haiku)
├── frontend/
│   ├── index.html          # Coaching session page
│   ├── play.html           # Play vs Coach King page
│   ├── practice.html       # Practice page (puzzles + openings)
│   ├── app.js              # Coaching session WebSocket client
│   ├── play.js             # Game client (board interaction, mistake panel)
│   ├── practice.js         # Practice client (puzzle checker, opening viewer)
│   ├── chess_utils.js      # ChessBoard class + MoveSequencePlayer
│   ├── style.css           # Dark chess theme, shared UI components
│   └── chess.css           # Board squares, highlights, nav, mistake panel
├── graph/
│   ├── state.py            # ChessCoachState TypedDict
│   └── pipeline.py         # Graph assembly + utility nodes
├── memory/
│   └── user_store.py       # SQLite CRUD for user preferences
├── tools/
│   ├── chess_api.py        # Chess.com public API wrapper
│   ├── engine_findings.py  # Stockfish blunder/missed-mate extraction
│   └── pgn_parser.py       # PGN parsing + time pressure detection
├── utils/
│   ├── character.py        # Coach King ASCII art + macOS TTS
│   ├── events.py           # EventBus singleton (CLI/Web mode switching)
│   ├── stockfish_engine.py # python-chess Stockfish wrapper
│   └── book/               # Personalized workbook PDF builder
│       ├── builder.py      # Top-level: assembles every chapter
│       ├── layout.py       # Page templates, frames, chapter primitives
│       ├── teaching.py     # Per-position teaching prose generator
│       ├── markdown.py     # Markdown → ReportLab flowables
│       ├── styles.py       # Design tokens + paragraph styles
│       ├── board.py        # FEN → board Drawing
│       └── assets/         # Chess Merida Unicode font
├── data/                   # users.db created here at runtime (gitignored)
├── outputs/                # Generated workbooks saved here
├── main.py                 # CLI entry point
├── run_web.py              # Web entry point
├── requirements.txt
├── .env.example
├── VERSION
└── README.md
```

---

## 13. Version History

### V3.0
- **Play vs Coach King** — full interactive chess game at `/play`; 4 difficulty levels; 4 coaching assistance levels; real-time mistake detection using Claude Haiku; mistake panel slides up from bottom with explanation, mini board, and ← → sequence navigation; two tabs showing "your move" and "better move" sequences; Coach King speaks via Web Speech API
- **Practice Mode** — `/practice` page with two tabs: Tactics Puzzles (5 AI-generated, python-chess validated, SAN answer checker with per-puzzle mini board) and Opening Trainer (3 AI-generated lines based on user preferences, server-pre-computed FEN sequences, board viewer with step navigation)
- **Navigation bar** linking all three pages across the site
- **chess.css** — consolidated chess board styling (squares, highlights, mistake panel slide-up animation, tabs, puzzle cards, opening cards)

### V2.0
- Custom web UI with live agent visualization
- FastAPI + WebSocket backend serves a dark chess-themed frontend
- Three agent nodes light up as they become active; arrows animate when data flows between them
- Debug window shows plain-English status in real time
- Coach King's interview moves into the browser with Web Speech API voice
- CLI mode (`main.py`) still works

### V1.0
- Full three-agent pipeline: Analyst → Coach → Critic
- Chess.com public API integration
- PGN parsing with time-pressure detection
- SQLite user memory (persist username + preferences across sessions)
- Coaching report saved as Markdown + PDF
- Teaching guide PDF auto-generated on first run
- CLI interface
