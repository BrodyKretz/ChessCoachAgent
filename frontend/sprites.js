// Pixel-art character sprites: Witch (Analyst), Wizard (Coach), Old Man (Critic)
// Each sprite is a 12x16 pixel grid rendered as SVG at 4x scale (48x64 px).
// States: idle | talking | thinking
//
// Animation behaviours:
//   idle    — random blink every 3-7 s (briefly show squint frame)
//   talking — mouth toggles open/closed at ~4 fps
//   thinking — eyes alternate squint/normal every 1.1 s

(function () {

const PALS = {
  analyst: {
    k:'#1e1038', v:'#4a2070', H:'#180828', h:'#2d1250',
    S:'#f2c090', e:'#1a1a30', u:'#b85060', O:'#7a1a28',
    P:'#3d0e58', p:'#7030a0',
    C:'#90e0ff', c:'#40a8e0', D:'#1050b0', G:'#ffffff',
    _:'#7070a0',
  },
  coach: {
    H:'#3a1f78', h:'#6644c0', '*':'#f0d060',
    S:'#f5c890', e:'#1a1a30', u:'#b85060', O:'#7a1a28',
    B:'#e8e8f8', b:'#9898b8',
    R:'#1e1260', r:'#3a2888', t:'#c9a84c', s:'#8b6020',
    _:'#7070a0',
  },
  critic: {
    W:'#e4e8f8', w:'#a8b0cc', S:'#e8b878',
    e:'#2a2a40', u:'#b85060', O:'#7a1a28',
    B:'#e4e8f8', b:'#a8b0cc',
    G:'#3c2810', g:'#5c4028', T:'#907850',
    l:'#5a6090', r:'#cc8050', _:'#7070a0',
  },
};

const FRAMES = {

  analyst: {
    idle: [
      '.....k......',
      '....kvk.....',
      '...kvvvk....',
      '..kHvvvHk...',
      '.HHkvvvkHH..',
      '.HHHkkkHHH..',
      '.HHSSSSSHH..',
      '.HHSeSSeHH..',
      '.HHSSSSSHH..',
      '.HHSSuSSHH..',
      '.HHpPPPpHH..',
      '.pP.CCC.Pp..',
      '.pPCcDDcCPp.',
      '.pPCDGDDCPp.',
      '.pPCcDDcCPp.',
      '.pPP.CCC.Pp.',
    ],
    talking: [
      '.....k......',
      '....kvk.....',
      '...kvvvk....',
      '..kHvvvHk...',
      '.HHkvvvkHH..',
      '.HHHkkkHHH..',
      '.HHSSSSSHH..',
      '.HHSeSSeHH..',
      '.HHSSSSSHH..',
      '.HHSuOuSHH..',
      '.HHpPPPpHH..',
      '.pP.CCC.Pp..',
      '.pPCcDDcCPp.',
      '.pPCDGDDCPp.',
      '.pPCcDDcCPp.',
      '.pPP.CCC.Pp.',
    ],
    thinking: [
      '.....k......',
      '....kvk.....',
      '...kvvvk....',
      '..kHvvvHk...',
      '.HHkvvvkHH..',
      '.HHHkkkHHH..',
      '.HHSSSSSHH..',
      '.HHS_SS_HH..',
      '.HHSSSSSHH..',
      '.HHSSuSSHH..',
      '.HHpPPPpHH..',
      '.pP.CCC.Pp..',
      '.pPCcDDcCPp.',
      '.pPCDGGGCPp.',
      '.pPCcDDcCPp.',
      '.pPP.CCC.Pp.',
    ],
  },

  coach: {
    idle: [
      '.....*......',
      '....HhH.....',
      '...HhhhH....',
      '..HhhhhhH...',
      '.HHhhhhhhH..',
      'HhhhhhhhhhH.',
      '............',
      '..SSSSSSS...',
      '..SeSSSeS...',
      '..SSSSSSS...',
      '..SSuuuSS...',
      '..BBBBBBB...',
      '.BBBBBBBBB..',
      'sRRRRRRRRR..',
      'sRRrRRRrRR..',
      'stRRRRRRRt..',
    ],
    talking: [
      '.....*......',
      '....HhH.....',
      '...HhhhH....',
      '..HhhhhhH...',
      '.HHhhhhhhH..',
      'HhhhhhhhhhH.',
      '............',
      '..SSSSSSS...',
      '..SeSSSeS...',
      '..SSSSSSS...',
      '..SuOOOuS...',
      '..BBBBBBB...',
      '.BBBBBBBBB..',
      'sRRRRRRRRR..',
      'sRRrRRRrRR..',
      'stRRRRRRRt..',
    ],
    thinking: [
      '.....*......',
      '....HhH.....',
      '...HhhhH....',
      '..HhhhhhH...',
      '.HHhhhhhhH..',
      'HhhhhhhhhhH.',
      '............',
      '..SSSSSSS...',
      '..S_SSS_S...',
      '..SSSSSSS...',
      '..SSSuSSS...',
      '..BBBBBBB...',
      '.BBBBBBBBB..',
      'sRRRRRRRRR..',
      'sRRrRRRrRR..',
      'stRRRRRRRt..',
    ],
  },

  critic: {
    idle: [
      'WW........WW',
      'WW.SSSSSS.WW',
      '.WSBBSSBBSW.',
      '.wSleSSleSw.',
      '.wSSSrSSSw..',
      '.wSSuuuSSw..',
      '.wBBBBBBBw..',
      '.BBBBBBBBBw.',
      '.BBBbBBbBBB.',
      '.GGGGGGGGGw.',
      '.GgGGGGGgGG.',
      '.GGGgGGgGGG.',
      '.TGGGGGGGGT.',
      '.GGGGGGGGG..',
      '..GGGGGGG...',
      '............',
    ],
    talking: [
      'WW........WW',
      'WW.SSSSSS.WW',
      '.WSBBSSBBSW.',
      '.wSleSSleSw.',
      '.wSSSrSSSw..',
      '.wSSuOuSSw..',
      '.wBBBBBBBw..',
      '.BBBBBBBBBw.',
      '.BBBbBBbBBB.',
      '.GGGGGGGGGw.',
      '.GgGGGGGgGG.',
      '.GGGgGGgGGG.',
      '.TGGGGGGGGT.',
      '.GGGGGGGGG..',
      '..GGGGGGG...',
      '............',
    ],
    thinking: [
      'WW........WW',
      'WW.SSSSSS.WW',
      '.WSbBSSBbSW.',
      '.wSl_SSl_Sw.',
      '.wSSSrSSSw..',
      '.wSSSSuSSw..',
      '.wBBBBBBBw..',
      '.BBBBBBBBBw.',
      '.BBBbBBbBBB.',
      '.GGGGGGGGGw.',
      '.GgGGGGGgGG.',
      '.GGGgGGgGGG.',
      '.TGGGGGGGGT.',
      '.GGGGGGGGG..',
      '..GGGGGGG...',
      '............',
    ],
  },
};

// ── SVG construction ───────────────────────────────────────────

const SVG_NS = 'http://www.w3.org/2000/svg';

function buildSVGElement(agent, state) {
  const rows = FRAMES[agent][state];
  const pal  = PALS[agent];
  const W = rows[0].length;
  const H = rows.length;

  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('width',  String(W * 4));
  svg.setAttribute('height', String(H * 4));
  svg.style.imageRendering = 'pixelated';
  svg.style.display = 'none';

  for (let y = 0; y < H; y++) {
    const row = rows[y];
    for (let x = 0; x < W; x++) {
      const ch = row[x];
      if (ch !== '.' && pal[ch]) {
        const rect = document.createElementNS(SVG_NS, 'rect');
        rect.setAttribute('x',      String(x));
        rect.setAttribute('y',      String(y));
        rect.setAttribute('width',  '1');
        rect.setAttribute('height', '1');
        rect.setAttribute('fill',   pal[ch]);
        svg.appendChild(rect);
      }
    }
  }
  return svg;
}

// ── Frame cache (pre-built SVG elements, toggled via display) ──

const cache = {};   // cache[agent][state] = SVGElement

function preloadAll() {
  ['analyst', 'coach', 'critic'].forEach(agent => {
    cache[agent] = {};
    ['idle', 'talking', 'thinking'].forEach(state => {
      cache[agent][state] = buildSVGElement(agent, state);
    });
  });
}

function showFrame(agent, state) {
  const el = document.getElementById(`sprite-${agent}`);
  if (!el || !cache[agent]) return;

  if (!el._loaded) {
    el.textContent = '';
    Object.values(cache[agent]).forEach(svg => el.appendChild(svg));
    el._loaded = true;
  }

  Object.entries(cache[agent]).forEach(([s, svg]) => {
    svg.style.display = s === state ? 'block' : 'none';
  });
}

// ── Animation engine ───────────────────────────────────────────

const anim = {};  // anim[agent] = { behavior, interval, timeout }

function setBehavior(agent, behavior) {
  const s = anim[agent] || (anim[agent] = {});
  clearInterval(s.interval); s.interval = null;
  clearTimeout(s.timeout);   s.timeout  = null;
  s.behavior = behavior;

  if (behavior === 'talking') {
    // Toggle mouth open/closed at ~4 fps
    let alt = false;
    showFrame(agent, 'talking');
    s.interval = setInterval(() => {
      showFrame(agent, alt ? 'idle' : 'talking');
      alt = !alt;
    }, 220);

  } else if (behavior === 'thinking') {
    // Squint eyes slowly, like deep focus
    let alt = false;
    showFrame(agent, 'thinking');
    s.interval = setInterval(() => {
      showFrame(agent, alt ? 'idle' : 'thinking');
      alt = !alt;
    }, 1100);

  } else {
    // Idle: show normal frame and schedule random blinks
    showFrame(agent, 'idle');
    scheduleBlink(agent);
  }
}

function scheduleBlink(agent) {
  const s = anim[agent];
  if (!s) return;
  const delay = 3000 + Math.random() * 5000;
  s.timeout = setTimeout(() => {
    if (s.behavior !== 'idle') return;
    showFrame(agent, 'thinking');          // squint = blink
    setTimeout(() => {
      if (s.behavior === 'idle') {
        showFrame(agent, 'idle');
        scheduleBlink(agent);              // schedule the next one
      }
    }, 140);
  }, delay);
}

// ── Public API ─────────────────────────────────────────────────

window.setAgentSprite = function (agent, state) {
  if (!FRAMES[agent] || !FRAMES[agent][state]) return;
  setBehavior(agent, state);
};

// ── Init ───────────────────────────────────────────────────────

function init() {
  preloadAll();
  ['analyst', 'coach', 'critic'].forEach(agent => setBehavior(agent, 'idle'));
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

})();
