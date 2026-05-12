/* ── State ──────────────────────────────────────────────────── */
let ws = null;
let currentAgent = null;
let outputBlocks = {};
let pdfPath = null;
let currentQuestionId = null;
let revisionCount = 0;

/* ── WebSocket ──────────────────────────────────────────────── */
function startSession(e) {
  e.preventDefault();

  const username = document.getElementById('input-username').value.trim();
  const numGames = parseInt(document.getElementById('input-games').value) || 10;
  const timeCtrl = document.getElementById('input-tc').value;
  const enableEngine = document.getElementById('input-engine').checked;

  if (!username) return;

  setStatus('active', 'Connecting...');
  document.getElementById('start-btn').disabled = true;

  ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);

  ws.onopen = () => {
    ws.send(JSON.stringify({
      type: 'start', username, num_games: numGames,
      time_control: timeCtrl, enable_engine: enableEngine
    }));
    setStatus('active', 'Session running');
    addDebug('▶', `Session started for ${username}${enableEngine ? ' (engine analysis on)' : ''}`);
    markEngineSkipped(!enableEngine);
  };

  ws.onmessage = (e) => handleMessage(JSON.parse(e.data));

  ws.onerror = () => {
    setStatus('error', 'Connection error');
    addDebug('✗', 'WebSocket error — is the server running?');
  };

  ws.onclose = () => {
    if (document.getElementById('complete-card').classList.contains('visible')) return;
    setStatus('', 'Disconnected');
  };
}

/* ── Message router ─────────────────────────────────────────── */
function handleMessage(msg) {
  switch (msg.type) {
    case 'node':     updateNode(msg.node, msg.status);           break;
    case 'debug':    addDebug('▶', msg.message);                 break;
    case 'stream':   appendStream(msg.agent, msg.text);          break;
    case 'speak':    speak(msg.text);                            break;
    case 'question': showQuestion(msg.id, msg.question, msg.options || []); break;
    case 'complete':
      pdfPath = msg.pdf_path;
      showComplete();
      break;
    case 'error':    addDebug('✗', msg.message); setStatus('error', 'Error'); break;
  }
}

/* ── Node pipeline UI ───────────────────────────────────────── */
const NODE_MAP = {
  analyst: 'analyst', engine: 'engine', coach: 'coach', critic: 'critic'
};
const BADGES   = { active: 'Working...', complete: 'Done ✓', waiting: 'Waiting for you...' };

function updateNode(nodeName, status) {
  const mapped = NODE_MAP[nodeName];
  if (!mapped) return;

  const el    = document.getElementById(`node-${mapped}`);
  const badge = document.getElementById(`badge-${mapped}`);
  if (!el) return;

  el.classList.remove('active', 'complete', 'waiting');
  el.classList.add(status);
  badge.textContent = BADGES[status] || status;
  updateArrows(mapped, status);

  if (window.setAgentSprite) {
    const spriteState = status === 'active' ? 'thinking' : status === 'waiting' ? 'talking' : 'idle';
    setAgentSprite(mapped, spriteState);
  }

  if (mapped === 'coach' && status === 'active' && revisionCount > 0) {
    document.getElementById('feedback-label').classList.add('visible');
  }
}

function markEngineSkipped(skipped) {
  const node  = document.getElementById('node-engine');
  const badge = document.getElementById('badge-engine');
  if (!node || !badge) return;
  if (skipped) {
    node.classList.add('skipped');
    badge.textContent = 'Skipped';
  } else {
    node.classList.remove('skipped');
    badge.textContent = '—';
  }
}

function updateArrows(node, status) {
  const arrowMap = {
    engine: 'arrow-analyst-engine',
    coach:  'arrow-engine-coach',
    critic: 'arrow-coach-critic',
  };
  document.querySelectorAll('.pipe-arrow').forEach(a => a.classList.remove('active'));
  if (status === 'active' && arrowMap[node]) {
    const el = document.getElementById(arrowMap[node]);
    if (el) el.classList.add('active');
  }
}

/* ── Streaming output ───────────────────────────────────────── */
const AGENT_LABELS = { analyst: 'Analyst', coach: 'Coach King', critic: 'Critic' };

function appendStream(agent, text) {
  const body = document.getElementById('output-body');

  if (window.setAgentSprite) setAgentSprite(agent, 'talking');

  if (currentAgent !== agent) {
    currentAgent = agent;

    const block = document.createElement('div');
    block.className = `output-block ${agent}`;

    const tag = document.createElement('div');
    tag.className = 'agent-tag';
    tag.textContent = AGENT_LABELS[agent] || agent;

    const content = document.createElement('div');
    content.className = 'agent-text';

    block.appendChild(tag);
    block.appendChild(content);
    body.appendChild(block);
    outputBlocks[agent] = content;
  }

  const target = outputBlocks[agent];
  if (target) {
    target.textContent += text;
    body.scrollTop = body.scrollHeight;
  }
}

/* ── Debug window ───────────────────────────────────────────── */
const ICON_COLORS = { '▶': '#39ff6e', '✓': '#4caf7d', '✗': '#d05b5b', '!': '#c9a84c' };

function addDebug(icon, message) {
  const body = document.getElementById('debug-body');

  const line = document.createElement('div');
  line.className = 'debug-line';

  const iconEl = document.createElement('span');
  iconEl.className = 'debug-icon';
  iconEl.style.color = ICON_COLORS[icon] || '#39ff6e';
  iconEl.textContent = icon;

  const msgEl = document.createElement('span');
  msgEl.textContent = message;

  line.appendChild(iconEl);
  line.appendChild(msgEl);
  body.appendChild(line);
  body.scrollTop = body.scrollHeight;
}

/* ── Question / Coach interview ─────────────────────────────── */
function showQuestion(id, question, options) {
  currentQuestionId = id;
  hideSetupForm();
  document.getElementById('complete-card').classList.remove('visible');

  document.getElementById('question-text').textContent = question;
  document.getElementById('interaction-header').textContent = 'Coach King';

  const optEl = document.getElementById('question-options');
  optEl.textContent = '';
  options.forEach(opt => {
    const div = document.createElement('div');
    div.textContent = opt;
    optEl.appendChild(div);
  });

  document.getElementById('answer-input').value = '';
  document.getElementById('question-card').classList.add('visible');
  document.getElementById('answer-input').focus();
  updateNode('coach', 'waiting');
}

function submitAnswer() {
  const val = document.getElementById('answer-input').value.trim();
  if (!ws) return;

  ws.send(JSON.stringify({ type: 'answer', id: currentQuestionId, value: val }));
  addDebug('▶', `Your answer: "${val}"`);

  document.getElementById('question-card').classList.remove('visible');
  document.getElementById('interaction-header').textContent = 'Session';
  currentQuestionId = null;
  updateNode('coach', 'active');
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey && currentQuestionId) {
    e.preventDefault();
    submitAnswer();
  }
});

/* ── Complete ───────────────────────────────────────────────── */
function showComplete() {
  setStatus('', 'Complete');
  document.getElementById('status-dot').classList.remove('active');
  hideSetupForm();
  document.getElementById('question-card').classList.remove('visible');
  document.getElementById('complete-card').classList.add('visible');
  document.getElementById('interaction-header').textContent = 'Workbook Ready';
  addDebug('✓', 'Workbook saved to outputs/ folder.');
}

function downloadPdf() {
  if (!pdfPath) return;
  const filename = pdfPath.split('/').pop();
  window.open(`/outputs/${filename}`, '_blank');
}

function resetSession() { location.reload(); }

/* ── Status ─────────────────────────────────────────────────── */
function setStatus(state, text) {
  const dot = document.getElementById('status-dot');
  dot.className = state === 'active' ? 'active' : (state === 'error' ? 'error' : '');
  document.getElementById('status-text').textContent = text;
}

function hideSetupForm() {
  document.getElementById('setup-form').style.display = 'none';
}

/* ── Web Speech API ─────────────────────────────────────────── */
function speak(text) {
  if (!window.speechSynthesis) return;
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 0.92;
  utter.pitch = 1.05;
  const voices = speechSynthesis.getVoices();
  const preferred = voices.find(v =>
    v.name.includes('Daniel') || v.name.includes('Alex') || v.lang === 'en-GB'
  ) || voices.find(v => v.lang.startsWith('en'));
  if (preferred) utter.voice = preferred;
  speechSynthesis.speak(utter);
}

speechSynthesis.getVoices();
speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();
