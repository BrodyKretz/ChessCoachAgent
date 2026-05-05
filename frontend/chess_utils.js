/**
 * Shared chess board rendering utilities.
 * Pieces rendered via Chess.com-style SVG sprites (Lichess cburnett set, open-source).
 * Server sends board state as 8x8 arrays; client only renders.
 */

const PIECE_CDN = 'https://lichess1.org/assets/piece/cburnett/';
const FILES = 'abcdefgh';

/** Parse FEN piece-placement into an 8x8 array (row 0 = rank 8). */
function fenToArray(fen) {
  const rows = fen.split(' ')[0].split('/');
  return rows.map(row => {
    const rank = [];
    for (const ch of row) {
      if (isNaN(ch)) {
        rank.push((ch === ch.toUpperCase() ? 'w' : 'b') + ch.toUpperCase());
      } else {
        for (let i = 0; i < parseInt(ch); i++) rank.push(null);
      }
    }
    return rank;
  });
}

class ChessBoard {
  /**
   * @param {HTMLElement} container
   * @param {object}      opts
   *   orientation:  'white' | 'black'
   *   mini:         boolean  — 36px squares, non-interactive
   *   squareSize:   number   — custom square size in px (default 64)
   *   interactive:  boolean  — fire onClick on clicks
   *   onClick:      (squareName) => void
   */
  constructor(container, opts = {}) {
    this.container   = container;
    this.orientation = opts.orientation  || 'white';
    this.mini        = opts.mini         || false;
    this.squareSize  = opts.squareSize   || (opts.mini ? 36 : 64);
    this.interactive = opts.interactive !== false;
    this.onClick     = opts.onClick      || null;

    this._boardArr   = null;
    this._highlights = {};
    this._squares    = {};

    this._build();
  }

  _build() {
    this.container.className = 'chess-board' + (this.mini ? ' mini' : '');
    // Apply custom size if not the default 64px
    if (!this.mini && this.squareSize !== 64) {
      this.container.style.gridTemplateColumns = `repeat(8, ${this.squareSize}px)`;
      this.container.style.gridTemplateRows    = `repeat(8, ${this.squareSize}px)`;
    } else {
      this.container.style.gridTemplateColumns = '';
      this.container.style.gridTemplateRows    = '';
    }

    this.container.textContent = '';
    this._squares = {};

    const ranks = this.orientation === 'white' ? [7,6,5,4,3,2,1,0] : [0,1,2,3,4,5,6,7];
    const files  = this.orientation === 'white' ? [0,1,2,3,4,5,6,7] : [7,6,5,4,3,2,1,0];

    for (const r of ranks) {
      for (const f of files) {
        const sq  = FILES[f] + (r + 1);
        const div = document.createElement('div');
        div.className  = 'chess-square ' + ((r + f) % 2 !== 0 ? 'light' : 'dark');
        div.dataset.sq = sq;
        if (this.interactive && this.onClick) {
          div.addEventListener('click', () => this.onClick(sq));
        }
        this._squares[sq] = div;
        this.container.appendChild(div);
      }
    }
    this._render();
  }

  _render() {
    for (const [sq, div] of Object.entries(this._squares)) {
      const f     = FILES.indexOf(sq[0]);
      const r     = parseInt(sq[1]) - 1;
      const piece = this._boardArr ? this._boardArr[7 - r][f] : null;

      // Update piece sprite (reuse existing img to avoid flicker)
      let img = div.querySelector('img');
      if (piece) {
        if (!img) {
          img = document.createElement('img');
          img.alt       = piece;
          img.draggable = false;
          div.appendChild(img);
        }
        if (img.dataset.piece !== piece) {
          img.src          = PIECE_CDN + piece + '.svg';
          img.dataset.piece = piece;
        }
      } else if (img) {
        img.remove();
      }

      // Highlights
      div.classList.remove('sel','legal','legal-cap','hl-from','hl-to','hl-mistake','hl-better');
      const hl = this._highlights[sq];
      if (hl) div.classList.add(hl);
    }
  }

  /** Return the piece code at a square ('wK', 'bP', null). */
  getPiece(sq) {
    if (!this._boardArr) return null;
    const f = FILES.indexOf(sq[0]);
    const r = parseInt(sq[1]) - 1;
    return this._boardArr[7 - r]?.[f] ?? null;
  }

  setBoard(arr)    { this._boardArr = arr;          this._render(); }
  setFen(fen)      { this._boardArr = fenToArray(fen); this._render(); }
  setHighlights(h) { this._highlights = h || {};    this._render(); }
  clearHighlights(){ this._highlights = {};          this._render(); }

  highlightLastMove(from, to) {
    this._highlights[from] = 'hl-from';
    this._highlights[to]   = 'hl-to';
    this._render();
  }

  /** Apply a UCI move string (e.g. 'e2e4', 'e7e8q') to the internal board array. */
  applyUci(uci) {
    if (!this._boardArr) return;
    const from = uci.slice(0, 2);
    const to   = uci.slice(2, 4);
    const ff = FILES.indexOf(from[0]), rf = parseInt(from[1]) - 1;
    const ft = FILES.indexOf(to[0]),   rt = parseInt(to[1])   - 1;
    let piece = this._boardArr[7 - rf][ff];
    this._boardArr[7 - rf][ff] = null;
    // Handle promotion: uci[4] is the promo piece letter
    if (uci.length === 5 && piece) {
      piece = piece[0] + uci[4].toUpperCase();
    }
    this._boardArr[7 - rt][ft] = piece;
    this._highlights = { [from]: 'hl-from', [to]: 'hl-to' };
    this._render();
  }

  setOrientation(o) { this.orientation = o; this._build(); }
  flip()             { this.setOrientation(this.orientation === 'white' ? 'black' : 'white'); }
}

/** Step through a pre-computed sequence of {fen, move} dicts. */
class MoveSequencePlayer {
  constructor(miniBoard, labelEl, prevBtn, nextBtn) {
    this.board   = miniBoard;
    this.labelEl = labelEl;
    this.prevBtn = prevBtn;
    this.nextBtn = nextBtn;
    this._seq    = [];
    this._idx    = 0;
  }

  load(sequence) {
    this._seq = sequence || [];
    this._idx = 0;
    this._show();
  }

  prev() { if (this._idx > 0)                   { this._idx--; this._show(); } }
  next() { if (this._idx < this._seq.length - 1) { this._idx++; this._show(); } }

  _show() {
    const step = this._seq[this._idx];
    if (!step) return;
    this.board.setFen(step.fen);
    this.labelEl.textContent = step.move ? `Move: ${step.move}` : 'Starting position';
    this.prevBtn.disabled = this._idx === 0;
    this.nextBtn.disabled = this._idx === this._seq.length - 1;
  }
}
