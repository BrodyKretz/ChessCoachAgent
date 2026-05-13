/* ── State ─────────────────────────────────────────────────── */
let openingBoard = null;
let openingSeq   = [];
let openingIdx   = 0;

// Per-puzzle state: {board, data, selectedSq, tries, solved}
const puzzleState = {};

/* ── Init ──────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  openingBoard = new ChessBoard(document.getElementById('opening-board'), {
    orientation: 'white',
    interactive: false,
  });

  const saved = localStorage.getItem('chess_coach_username');
  if (saved) {
    document.getElementById('username-input').value = saved;
    loadAll();   // auto-load with stored username
  }
});

/* ── Tab switching ─────────────────────────────────────────── */
function switchTab(tab) {
  document.getElementById('tab-puzzles').classList.toggle('active',   tab === 'puzzles');
  document.getElementById('tab-openings').classList.toggle('active',  tab === 'openings');
  document.getElementById('pane-puzzles').style.display  = tab === 'puzzles'  ? 'flex' : 'none';
  document.getElementById('pane-openings').style.display = tab === 'openings' ? 'flex' : 'none';
}

/* ── Load both datasets ────────────────────────────────────── */
async function loadAll() {
  const username = document.getElementById('username-input').value.trim();
  if (username) localStorage.setItem('chess_coach_username', username);

  document.getElementById('load-btn').disabled = true;
  clearPuzzles();
  clearOpenings();

  await Promise.all([loadPuzzles(username), loadOpenings(username)]);
  document.getElementById('load-btn').disabled = false;
}

/* ═══════════════════════════════════════════════════════════════
   PUZZLES
═══════════════════════════════════════════════════════════════ */

function clearPuzzles() {
  document.getElementById('puzzles-list').textContent = '';
  document.getElementById('puzzles-empty').style.display = 'none';
  Object.keys(puzzleState).forEach(k => delete puzzleState[k]);
}

async function loadPuzzles(username) {
  const loading = document.getElementById('puzzles-loading');
  loading.style.display = 'block';
  try {
    const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/practice`);
    await new Promise((resolve, reject) => {
      ws.onopen    = () => ws.send(JSON.stringify({ username, mode: 'puzzles' }));
      ws.onerror   = reject;
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === 'puzzles') {
          if (msg.data && msg.data.length) {
            renderPuzzles(msg.data);
          } else {
            const el = document.getElementById('puzzles-empty');
            el.style.display = 'block';
            el.textContent   = msg.message || 'No tactical puzzles found in your recent games.';
          }
          ws.close();
          resolve();
        } else if (msg.type === 'error') {
          ws.close();
          reject(new Error(msg.message));
        }
      };
    });
  } catch (err) {
    const el = document.getElementById('puzzles-empty');
    el.style.display = 'block';
    el.textContent = `Error: ${err.message || 'Failed to load puzzles'}`;
  } finally {
    loading.style.display = 'none';
  }
}

function renderPuzzles(puzzles) {
  const list = document.getElementById('puzzles-list');
  if (!puzzles || !puzzles.length) {
    document.getElementById('puzzles-empty').style.display = 'block';
    return;
  }

  puzzles.forEach((p, i) => {
    const card = document.createElement('div');
    card.className = 'puzzle-card';
    card.id = `puzzle-card-${i}`;

    /* ── Game-origin header (top of card) ── */
    const header = document.createElement('div');
    header.className = 'puzzle-game-header';
    const titleBits = [`Position ${i + 1}`];
    if (p.opponent) titleBits.push(`vs ${p.opponent}`);
    if (p.move_num) titleBits.push(`move ${p.move_num}`);
    header.textContent = titleBits.join(' · ');
    card.appendChild(header);

    /* ── Body (board + info) ── */
    const body = document.createElement('div');
    body.className = 'puzzle-body';

    /* ── Board ── */
    const boardEl = document.createElement('div');
    boardEl.id = `puzzle-board-${i}`;

    /* ── Info column ── */
    const info = document.createElement('div');
    info.className = 'puzzle-info';

    const theme = document.createElement('div');
    theme.className = 'puzzle-theme';
    theme.textContent = p.theme || 'Tactic';

    const turn = document.createElement('div');
    turn.className = 'puzzle-turn';
    turn.textContent = `${p.side_to_move === 'white' ? 'White' : 'Black'} to move — find the best move.`;

    const hint = document.createElement('div');
    hint.className = 'puzzle-hint';
    hint.textContent = p.you_played
      ? `You played ${p.you_played} during the game. There was something stronger here.`
      : (p.hint || 'Click a piece to see legal moves, then click the destination.');

    const feedback = document.createElement('div');
    feedback.className = 'puzzle-feedback';
    feedback.id = `puzzle-fb-${i}`;

    const tries = document.createElement('div');
    tries.className = 'puzzle-tries';
    tries.id = `puzzle-tries-${i}`;

    info.append(theme, turn, hint, feedback, tries);
    body.append(boardEl, info);
    card.append(body);
    list.appendChild(card);

    /* ── Create interactive board ── */
    const board = new ChessBoard(boardEl, {
      orientation: p.side_to_move === 'white' ? 'white' : 'black',
      squareSize: 52,
      interactive: true,
      onClick: (sq) => onPuzzleClick(i, sq),
    });
    board.setFen(p.fen);

    puzzleState[i] = { board, data: p, selectedSq: null, tries: 0, solved: false };
  });
}

/* ── Puzzle click handler ──────────────────────────────────── */
function onPuzzleClick(idx, sq) {
  const state = puzzleState[idx];
  if (!state || state.solved) return;

  const { board, data } = state;
  const playerColor = data.side_to_move === 'white' ? 'w' : 'b';
  const piece = board.getPiece(sq);

  if (state.selectedSq) {
    const from    = state.selectedSq;
    const targets = data.legal_moves[from] || [];

    if (sq === from) {
      // Deselect
      state.selectedSq = null;
      board.clearHighlights();

    } else if (targets.includes(sq)) {
      // Attempt the move
      state.selectedSq = null;
      board.clearHighlights();
      attemptPuzzleMove(idx, from, sq);

    } else if (piece && piece[0] === playerColor) {
      // Switch selection to a different own piece
      selectPuzzlePiece(idx, sq);

    } else {
      // Invalid target — clear
      state.selectedSq = null;
      board.clearHighlights();
    }
  } else {
    if (piece && piece[0] === playerColor) {
      selectPuzzlePiece(idx, sq);
    }
  }
}

function selectPuzzlePiece(idx, sq) {
  const state = puzzleState[idx];
  state.selectedSq = sq;

  const hl      = { [sq]: 'sel' };
  const targets = state.data.legal_moves[sq] || [];
  for (const dst of targets) {
    hl[dst] = state.board.getPiece(dst) ? 'legal-cap' : 'legal';
  }
  state.board.setHighlights(hl);
}

function attemptPuzzleMove(idx, from, to) {
  const state = puzzleState[idx];
  const { board, data } = state;

  // Build UCI (add queen promotion if needed)
  let uci = from + to;
  const piece = board.getPiece(from);
  if (piece && piece[1] === 'P') {
    const toRank = parseInt(to[1]);
    if (toRank === 8 || toRank === 1) uci += 'q';
  }

  const correct = uci === data.best_move_uci;

  if (correct) {
    // Show move on board then lock
    board.highlightLastMove(from, to);
    state.solved = true;
    showPuzzleFeedback(idx, 'correct',
      `Correct! ${data.explanation}`);
    document.getElementById(`puzzle-card-${idx}`).classList.add('solved');
    document.getElementById(`puzzle-tries-${idx}`).textContent = '';
  } else {
    state.tries++;
    if (state.tries >= 3) {
      state.solved = true;
      // Show the correct move on the board
      board.applyUci(data.best_move_uci);
      showPuzzleFeedback(idx, 'revealed',
        `Best move: ${data.best_move}. ${data.explanation}`);
      document.getElementById(`puzzle-card-${idx}`).classList.add('failed');
    } else {
      showPuzzleFeedback(idx, 'wrong', 'Not quite — try again.');
      document.getElementById(`puzzle-tries-${idx}`).textContent =
        `${3 - state.tries} attempt${3 - state.tries !== 1 ? 's' : ''} remaining`;
    }
  }
}

function showPuzzleFeedback(idx, type, text) {
  const el = document.getElementById(`puzzle-fb-${idx}`);
  el.textContent = text;
  el.className = `puzzle-feedback visible ${type}`;
}

/* ═══════════════════════════════════════════════════════════════
   OPENINGS
═══════════════════════════════════════════════════════════════ */

function clearOpenings() {
  document.getElementById('openings-list').textContent = '';
  document.getElementById('openings-empty').style.display = 'none';
  document.getElementById('opening-viewer').style.display = 'none';
  openingSeq = [];
  openingIdx = 0;
}

async function loadOpenings(username) {
  const loading = document.getElementById('openings-loading');
  loading.style.display = 'block';
  try {
    const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/practice`);
    await new Promise((resolve, reject) => {
      ws.onopen    = () => ws.send(JSON.stringify({ username, mode: 'openings' }));
      ws.onerror   = reject;
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === 'openings')   { renderOpenings(msg.data); ws.close(); resolve(); }
        else if (msg.type === 'error') { ws.close(); reject(new Error(msg.message)); }
      };
    });
  } catch (err) {
    const el = document.getElementById('openings-empty');
    el.style.display = 'block';
    el.textContent = `Error: ${err.message || 'Failed to load openings'}`;
  } finally {
    loading.style.display = 'none';
  }
}

function renderOpenings(lines) {
  const list = document.getElementById('openings-list');
  if (!lines || !lines.length) {
    document.getElementById('openings-empty').style.display = 'block';
    return;
  }

  lines.forEach(line => {
    const card = document.createElement('div');
    card.className = 'opening-card';

    const header = document.createElement('div');
    header.className = 'opening-header';
    header.onclick = () => loadOpeningViewer(line);

    const title = document.createElement('div');
    title.className = 'opening-title';
    title.textContent = line.name || 'Opening';

    const pill = document.createElement('div');
    pill.className = `opening-color-pill ${line.color || 'white'}`;
    pill.textContent = line.color === 'black' ? 'Black' : 'White';

    header.append(title, pill);

    const body = document.createElement('div');
    body.className = 'opening-body';

    const movesRow = document.createElement('div');
    movesRow.className = 'opening-moves';
    (line.moves || []).forEach((m, mi) => {
      const chip = document.createElement('div');
      chip.className = 'opening-move-chip';
      chip.textContent = mi % 2 === 0 ? `${Math.floor(mi/2)+1}. ${m}` : m;
      movesRow.appendChild(chip);
    });

    const desc = document.createElement('div');
    desc.className = 'opening-description';
    desc.textContent = line.description || '';

    const ideas = document.createElement('div');
    ideas.className = 'opening-key-ideas';
    ideas.textContent = line.key_ideas ? `Key ideas: ${line.key_ideas}` : '';

    const studyBtn = document.createElement('button');
    studyBtn.className = 'btn btn-secondary';
    studyBtn.style.cssText = 'margin-top:10px;font-size:12px;';
    studyBtn.textContent = 'Study on board →';
    studyBtn.onclick = (e) => { e.stopPropagation(); loadOpeningViewer(line); };

    body.append(movesRow, desc, ideas, studyBtn);
    card.append(header, body);
    list.appendChild(card);
  });
}

/* ── Opening board viewer ──────────────────────────────────── */
function loadOpeningViewer(line) {
  const viewer = document.getElementById('opening-viewer');
  viewer.style.display = 'flex';
  viewer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  document.getElementById('opening-viewer-title').textContent = line.name || '';
  document.getElementById('opening-viewer-desc').textContent  = line.description || '';
  document.getElementById('opening-viewer-ideas').textContent = line.key_ideas ? `Key ideas: ${line.key_ideas}` : '';

  openingBoard.setOrientation(line.color === 'black' ? 'black' : 'white');
  openingSeq = line.sequence || [];
  openingIdx = 0;
  showOpeningStep();
}

function showOpeningStep() {
  const step = openingSeq[openingIdx];
  if (!step) return;
  openingBoard.setFen(step.fen);

  const label = document.getElementById('opening-step-label');
  if (step.move) {
    const half = openingIdx - 1;
    const num  = Math.floor(half / 2) + 1;
    const side = half % 2 === 0 ? 'White' : 'Black';
    label.textContent = `Move ${num} (${side}): ${step.move}`;
  } else {
    label.textContent = 'Starting position';
  }

  document.getElementById('op-prev').disabled = openingIdx === 0;
  document.getElementById('op-next').disabled = openingIdx === openingSeq.length - 1;
}

function opPrev() { if (openingIdx > 0)                    { openingIdx--; showOpeningStep(); } }
function opNext() { if (openingIdx < openingSeq.length - 1) { openingIdx++; showOpeningStep(); } }
