// Pixel-art character sprites: Witch (Analyst), Wizard (Coach), Old Man (Critic)
// Each sprite is a 12x16 pixel grid rendered as SVG at 4x scale (48x64 px).
// States: idle | talking | thinking

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

  // ── Witch (Analyst) ─────────────────────────────────────────
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

  // ── Wizard (Coach King) ──────────────────────────────────────
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

  // ── Old Man (Critic) ─────────────────────────────────────────
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
  svg.style.display = 'block';

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

function renderSprite(agent, state) {
  const el = document.getElementById(`sprite-${agent}`);
  if (!el) return;
  el.textContent = '';
  el.appendChild(buildSVGElement(agent, state));
}

const currentStates = { analyst: 'idle', coach: 'idle', critic: 'idle' };

window.setAgentSprite = function (agent, state) {
  if (!FRAMES[agent] || !FRAMES[agent][state]) return;
  if (currentStates[agent] === state) return;
  currentStates[agent] = state;
  renderSprite(agent, state);
};

function init() {
  ['analyst', 'coach', 'critic'].forEach(agent => renderSprite(agent, 'idle'));
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

})();
