/* ── State ─────────────────────────────────────────────────── */
let reports   = [];
let activeIdx = -1;

/* ── Init ──────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  fetchReports();
});

/* ── Fetch report list ─────────────────────────────────────── */
async function fetchReports() {
  try {
    const res  = await fetch('/api/reports');
    reports    = await res.json();
    renderList();
  } catch (err) {
    const el = document.getElementById('list-empty');
    el.style.display = 'block';
    el.textContent   = 'Failed to load reports.';
  }
}

/* ── Sidebar list ──────────────────────────────────────────── */
function renderList() {
  const body  = document.getElementById('list-body');
  const empty = document.getElementById('list-empty');
  body.textContent = '';

  if (!reports.length) {
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  reports.forEach((r, i) => {
    const item = document.createElement('div');
    item.className = 'report-item';
    item.onclick   = () => openReport(i);

    const user = document.createElement('div');
    user.className   = 'report-item-user';
    user.textContent = r.username;

    const date = document.createElement('div');
    date.className   = 'report-item-date';
    date.textContent = r.date;

    const meta = document.createElement('div');
    meta.className   = 'report-item-meta';
    meta.textContent = r.size_kb + ' KB' + (r.pdf ? '  •  PDF available' : '');

    item.append(user, date, meta);
    body.appendChild(item);
  });
}

/* ── Open a report ─────────────────────────────────────────── */
async function openReport(i) {
  activeIdx = i;

  document.querySelectorAll('.report-item').forEach((el, idx) => {
    el.classList.toggle('active', idx === i);
  });

  const r = reports[i];
  document.getElementById('report-title').textContent = r.username + '  —  ' + r.date;
  document.getElementById('report-actions').style.display = 'flex';

  const body  = document.getElementById('report-body');
  body.textContent = '';

  const spinner = document.createElement('div');
  spinner.id          = 'report-empty';
  spinner.textContent = 'Loading…';
  body.appendChild(spinner);

  try {
    const res  = await fetch('/api/report-content/' + encodeURIComponent(r.filename));
    const data = await res.json();
    body.textContent = '';
    body.appendChild(renderMarkdown(data.content));
  } catch (err) {
    body.textContent = '';
    const msg = document.createElement('div');
    msg.id          = 'report-empty';
    msg.textContent = 'Failed to load report content.';
    body.appendChild(msg);
  }
}

/* ── Download PDF ──────────────────────────────────────────── */
function downloadReport() {
  if (activeIdx < 0) return;
  const r = reports[activeIdx];
  if (r.pdf) {
    const a = document.createElement('a');
    a.href     = '/outputs/' + encodeURIComponent(r.pdf);
    a.download = r.pdf;
    a.click();
  } else {
    alert('No PDF available for this report.');
  }
}

/* ═══════════════════════════════════════════════════════════════
   Markdown renderer — pure DOM, no innerHTML
═══════════════════════════════════════════════════════════════ */

const TOKEN_RE = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;

function inlineEl(container, text) {
  const parts = text.split(TOKEN_RE);
  for (const part of parts) {
    if (part.startsWith('**') && part.endsWith('**')) {
      const b = document.createElement('strong');
      b.textContent = part.slice(2, -2);
      container.appendChild(b);
    } else if (part.startsWith('*') && part.endsWith('*')) {
      const em = document.createElement('em');
      em.textContent = part.slice(1, -1);
      container.appendChild(em);
    } else if (part.startsWith('`') && part.endsWith('`')) {
      const code = document.createElement('code');
      code.textContent = part.slice(1, -1);
      container.appendChild(code);
    } else {
      container.appendChild(document.createTextNode(part));
    }
  }
}

function renderMarkdown(text) {
  const frag  = document.createDocumentFragment();
  const lines = text.split('\n');
  let listEl  = null;

  function flushList() {
    if (listEl) { frag.appendChild(listEl); listEl = null; }
  }

  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i];
    const line = raw.trimEnd();

    if (/^#{1}\s/.test(line)) {
      flushList();
      const h = document.createElement('h1');
      inlineEl(h, line.replace(/^#\s+/, ''));
      frag.appendChild(h);

    } else if (/^#{2}\s/.test(line)) {
      flushList();
      const h = document.createElement('h2');
      inlineEl(h, line.replace(/^##\s+/, ''));
      frag.appendChild(h);

    } else if (/^#{3}\s/.test(line)) {
      flushList();
      const h = document.createElement('h3');
      inlineEl(h, line.replace(/^###\s+/, ''));
      frag.appendChild(h);

    } else if (/^[-*]\s/.test(line)) {
      if (!listEl) listEl = document.createElement('ul');
      const li = document.createElement('li');
      inlineEl(li, line.replace(/^[-*]\s+/, ''));
      listEl.appendChild(li);

    } else if (/^---+$/.test(line.trim())) {
      flushList();
      frag.appendChild(document.createElement('hr'));

    } else if (line.trim() === '') {
      flushList();

    } else {
      flushList();
      const p = document.createElement('p');
      inlineEl(p, line);
      frag.appendChild(p);
    }
  }

  flushList();
  return frag;
}
