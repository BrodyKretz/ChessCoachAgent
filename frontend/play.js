/* ── State ─────────────────────────────────────────────────── */
let ws            = null;
let mainBoard     = null;
let sideBoard     = null;
let seqPlayer     = null;
let playerColor   = 'white';
let selectedSq    = null;
let legalMap      = {};
let gameActive    = false;
let currentMistake = null;
let moveCount     = 0;
let pendingMove   = null;   // {from, to} of the optimistically-applied move
let prevBoardArr  = null;   // snapshot before optimistic update (for revert on invalid)
let awaitingCoach = false;  // true between sending a move and receiving coach_move

/* ── Init ──────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  mainBoard = new ChessBoard(document.getElementById('main-board'), {
    orientation: 'white',
    onClick: onSquareClick,
  });

  sideBoard = new ChessBoard(document.getElementById('side-board'), {
    orientation: 'white',
    mini: true,
    interactive: false,
  });

  seqPlayer = new MoveSequencePlayer(
    sideBoard,
    document.getElementById('side-step-label'),
    document.getElementById('btn-prev'),
    document.getElementById('btn-next'),
  );
});

/* ── Start game ────────────────────────────────────────────── */
function startGame() {
  const difficulty = document.querySelector('input[name="diff"]:checked').value;
  const coaching   = document.querySelector('input[name="coach"]:checked').value;
  playerColor      = document.querySelector('input[name="color"]:checked').value;
  const username   = document.getElementById('username-input').value.trim();

  ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/game`);

  ws.onopen = () => {
    ws.send(JSON.stringify({ difficulty, coaching, player_color: playerColor, username }));
    document.getElementById('setup-panel').style.display = 'none';
    document.getElementById('game-panel').style.display = 'flex';
    mainBoard.setOrientation(playerColor);
    sideBoard.setOrientation(playerColor);
  };

  ws.onmessage = (e) => handleMsg(JSON.parse(e.data));
  ws.onerror   = () => setStatus('Connection error');
  ws.onclose   = () => { if (gameActive) setStatus('Disconnected'); };
}

/* ── Message router ────────────────────────────────────────── */
function handleMsg(msg) {
  switch (msg.type) {
    case 'game_started':
      mainBoard.setBoard(msg.board);
      legalMap      = msg.legal_moves || {};
      gameActive    = true;
      pendingMove   = null;
      prevBoardArr  = null;
      awaitingCoach = playerColor === 'black';  // coach moves first if player is black
      setStatus(playerColor === 'white' ? 'Your turn — White to move' : 'Coach is thinking...');
      coachSay('Let\'s play! I\'m looking forward to our game.');
      break;

    case 'coach_move':
      mainBoard.setBoard(msg.board);
      mainBoard.highlightLastMove(msg.from, msg.to);
      legalMap = msg.legal_moves || {};
      awaitingCoach = false;
      setStatus('Your turn');
      logMove(`Coach: ${msg.san}`);
      coachSay(`I played ${msg.san}.`);
      moveCount++;
      break;

    case 'move_ok':
      // Server confirms move — sync authoritative board state
      mainBoard.setBoard(msg.board);
      if (pendingMove) {
        mainBoard.highlightLastMove(pendingMove.from, pendingMove.to);
        pendingMove = null;
      }
      prevBoardArr = null;
      logMove(`You: ${msg.san}`);
      moveCount++;
      if (moveCount % 5 === 0) {
        coachSay('Good game so far. Keep focusing on the position.');
      }
      setStatus('Coach is thinking...');
      break;

    case 'mistake':
      showMistake(msg.mistake);
      break;

    case 'invalid_move':
      if (prevBoardArr) {
        mainBoard.setBoard(prevBoardArr);
        prevBoardArr = null;
      }
      pendingMove   = null;
      awaitingCoach = false;
      setStatus('Invalid move — try again');
      selectedSq = null;
      mainBoard.clearHighlights();
      break;

    case 'game_over':
      gameActive = false;
      mainBoard.setBoard(msg.board);
      const r = msg.result;
      const winner = r === '1-0' ? 'White wins' : r === '0-1' ? 'Black wins' : 'Draw';
      setStatus(`Game over — ${winner} by ${msg.reason || 'agreement'}`);
      coachSay(`Game over! ${winner}. Well played — every game is a lesson.`);
      document.getElementById('resign-btn').disabled = true;
      break;

    case 'error':
      setStatus('Error: ' + msg.message);
      break;
  }
}

/* ── Board interaction ─────────────────────────────────────── */
function onSquareClick(sq) {
  if (!gameActive || awaitingCoach) return;

  if (selectedSq) {
    const from  = selectedSq;
    const legal = legalMap[from] || [];
    selectedSq  = null;
    mainBoard.clearHighlights();

    if (!legal.includes(sq)) return;   // clicked a non-legal square — deselect only

    const promo = needsPromotion(from, sq) ? 'q' : null;
    const uci   = from + sq + (promo || '');

    // Snapshot before optimistic update so we can revert on invalid_move
    prevBoardArr = mainBoard._boardArr.map(r => [...r]);
    pendingMove  = { from, to: sq };

    mainBoard.applyUci(uci);
    setStatus('Coach is thinking...');

    // Lock input until the coach replies so we can't queue extra moves
    awaitingCoach = true;
    legalMap = {};

    ws.send(JSON.stringify({ type: 'move', from, to: sq, promotion: promo }));
  } else {
    const legal = legalMap[sq];
    if (!legal || legal.length === 0) return;

    selectedSq = sq;
    const hl = { [sq]: 'sel' };
    for (const dst of legal) {
      hl[dst] = mainBoard.getPiece(dst) ? 'legal-cap' : 'legal';
    }
    mainBoard.setHighlights(hl);
  }
}

function needsPromotion(from, to) {
  const fromRank = parseInt(from[1]);
  const toRank   = parseInt(to[1]);
  return (fromRank === 7 && toRank === 8) || (fromRank === 2 && toRank === 1);
}

/* ── Mistake panel ─────────────────────────────────────────── */
function showMistake(mistake) {
  currentMistake = mistake;
  document.getElementById('mistake-badge').textContent    = mistake.quality.toUpperCase();
  document.getElementById('mistake-badge').className      = `mistake-badge ${mistake.quality}`;
  document.getElementById('mistake-your-move').textContent  = `You played: ${mistake.your_move}`;
  document.getElementById('mistake-explanation').textContent = mistake.explanation;
  document.getElementById('mistake-better-move').textContent = mistake.better_move
    ? `Better: ${mistake.better_move} — ${mistake.better_explanation || ''}`
    : '';

  loadSeq('your');
  document.getElementById('mistake-panel').classList.add('visible');

  coachSay(`Hold on — let me show you something. ${mistake.explanation}`);
}

function loadSeq(mode) {
  if (!currentMistake) return;
  const seq = mode === 'your' ? currentMistake.your_sequence : currentMistake.better_sequence;
  if (!seq) return;

  document.getElementById('tab-your').classList.toggle('active',   mode === 'your');
  document.getElementById('tab-better').classList.toggle('active', mode === 'better');

  seqPlayer.load(seq);
}

function seqPrev() { seqPlayer.prev(); }
function seqNext() { seqPlayer.next(); }

function closeMistakePanel() {
  document.getElementById('mistake-panel').classList.remove('visible');
  currentMistake = null;
}

/* ── Controls ──────────────────────────────────────────────── */
function resign() {
  if (!ws || !gameActive) return;
  gameActive = false;
  ws.send(JSON.stringify({ type: 'resign' }));
  coachSay('You resigned. Tough game — review it and come back stronger!');
}

function flipBoard() {
  mainBoard.flip();
  sideBoard.setOrientation(mainBoard.orientation);
}

/* ── UI helpers ────────────────────────────────────────────── */
function setStatus(text) {
  document.getElementById('game-status').textContent = text;
}

function coachSay(text) {
  document.getElementById('coach-comment').textContent = text;
  speak(text);
}

function logMove(text) {
  const log = document.getElementById('move-log');
  const div = document.createElement('div');
  div.className   = 'move-entry';
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function speak(text) {
  if (!window.speechSynthesis) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 0.92; u.pitch = 1.05;
  const voices = speechSynthesis.getVoices();
  const v = voices.find(v => v.name.includes('Daniel') || v.lang === 'en-GB')
         || voices.find(v => v.lang.startsWith('en'));
  if (v) u.voice = v;
  speechSynthesis.speak(u);
}

speechSynthesis.getVoices();
speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();
