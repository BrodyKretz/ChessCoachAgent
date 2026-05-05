"""
PDF generation for coaching reports.

Coaching report: generates .tex then compiles with xelatex (requires MacTeX / TeX Live).
Falls back to plain ReportLab if xelatex is not found.
Teaching guide: always uses ReportLab (static hardcoded content).
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

# ── LaTeX special-character escaping ─────────────────────────────────────────
# Order matters: backslash must come first.
_LATEX_ESCAPE = [
    ('\\', r'\textbackslash{}'),
    ('&',  r'\&'),
    ('%',  r'\%'),
    ('$',  r'\$'),
    ('#',  r'\#'),
    ('^',  r'\^{}'),
    ('_',  r'\_'),
    ('{',  r'\{'),
    ('}',  r'\}'),
    ('~',  r'\~{}'),
]

def _esc(text: str) -> str:
    for ch, repl in _LATEX_ESCAPE:
        text = text.replace(ch, repl)
    return text


# ── Inline markdown → LaTeX ───────────────────────────────────────────────────

_BACKTICK_RE = re.compile(r'`([^`]+)`')

# Conservative SAN chess notation detector.
# Matches: castling, piece moves (with optional rank/file disambiguation and capture),
# pawn captures, and move-number + pawn-push patterns like "1.e4" or "5...d5".
_CHESS_RE = re.compile(
    r'\b('
    r'O-O-O|O-O'
    r'|[KQRBN][a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#!?]{0,2}'
    r'|[a-h]x[a-h][1-8](?:=[QRBN])?[+#!?]{0,2}'
    r'|\d+\.{1,3}[a-h][1-8][+#!?]{0,2}'
    r'|\d+\.{1,3}[KQRBN][a-h]?[1-8]?x?[a-h][1-8][+#!?]{0,2}'
    r')\b',
    re.ASCII,
)


def _inline(text: str) -> str:
    """Convert an inline markdown span to LaTeX."""
    # Protect backtick spans so their content is not double-escaped or mangled.
    slots: list[str] = []
    placeholders: dict[str, str] = {}

    def protect_backtick(m: re.Match) -> str:
        inner = _esc(m.group(1))
        key = f'__SLOT{len(slots)}__'
        slots.append(key)
        placeholders[key] = r'\texttt{\textbf{' + inner + '}}'
        return key

    text = _BACKTICK_RE.sub(protect_backtick, text)

    # Escape LaTeX special chars in the remaining free text.
    text = _esc(text)

    # Bold: **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', text)

    # Italic: *text*
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\\emph{\1}', text)

    # Auto-detect chess notation outside protected spans and wrap in bold monospace.
    def chess_sub(m: re.Match) -> str:
        token = m.group(0)
        if any(token.startswith(k) or k in token for k in placeholders):
            return token
        return r'\texttt{\textbf{' + token + '}}'

    text = _CHESS_RE.sub(chess_sub, text)

    # Restore protected backtick spans.
    for key, val in placeholders.items():
        text = text.replace(key, val)

    return text


# ── Block-level markdown → LaTeX ─────────────────────────────────────────────

def _convert_body(markdown: str) -> str:
    """Convert markdown text (Claude's coaching report output) to LaTeX body."""
    lines = markdown.splitlines()
    out: list[str] = []
    in_itemize = False
    in_enumerate = False

    def close_list():
        nonlocal in_itemize, in_enumerate
        if in_itemize:
            out.append(r'\end{itemize}')
            in_itemize = False
        if in_enumerate:
            out.append(r'\end{enumerate}')
            in_enumerate = False

    _enum_re = re.compile(r'^\d+\.\s+(.+)')

    for line in lines:
        s = line.strip()

        # Close open lists when a non-list line is encountered.
        is_bullet = s.startswith('- ') or s.startswith('* ')
        is_enum   = bool(_enum_re.match(s))

        if in_itemize and not is_bullet:
            out.append(r'\end{itemize}')
            in_itemize = False
        if in_enumerate and not is_enum:
            out.append(r'\end{enumerate}')
            in_enumerate = False

        if not s:
            out.append('')

        elif s.startswith('# '):
            out.append(f'\\section{{{_inline(s[2:])}}}')

        elif s.startswith('## '):
            out.append(f'\\subsection{{{_inline(s[3:])}}}')

        elif s.startswith('### '):
            out.append(f'\\subsubsection{{{_inline(s[4:])}}}')

        elif s.startswith('---'):
            out.append(r'\vspace{4pt}{\color{neutral}\hrule height 0.4pt}\vspace{4pt}')

        elif is_bullet:
            if not in_itemize:
                out.append(r'\begin{itemize}[leftmargin=16pt, topsep=3pt, itemsep=2pt, parsep=0pt]')
                in_itemize = True
            content = _inline(s[2:])
            out.append(f'  \\item {content}')

        elif is_enum:
            if not in_enumerate:
                out.append(r'\begin{enumerate}[leftmargin=20pt, topsep=3pt, itemsep=2pt, parsep=0pt]')
                in_enumerate = True
            content = _inline(_enum_re.match(s).group(1))
            out.append(f'  \\item {content}')

        else:
            out.append(_inline(s))

    close_list()
    return '\n'.join(out)


# ── LaTeX document builder ────────────────────────────────────────────────────

_PREAMBLE = r"""\documentclass[11pt,a4paper]{article}

%% --- Packages ---
\usepackage[margin=1in, marginparwidth=0.55in, marginparsep=6pt]{geometry}
\usepackage{xcolor}
\usepackage[skins]{tcolorbox}
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage{enumitem}
\usepackage{fontspec}
\usepackage{parskip}

%% --- Colors ---
\definecolor{accent}{HTML}{1f3a5f}
\definecolor{neutral}{HTML}{555555}

%% --- Fonts (macOS system fonts; swap if needed) ---
\setmainfont{Georgia}
\setmonofont{Menlo}[Scale=0.86]

%% --- Section formatting ---
\titleformat{\section}
  {\large\bfseries\color{accent}}{\thesection.}{0.5em}{}
  [\vspace{2pt}\textcolor{accent}{\titlerule[0.5pt]}]

\titleformat{\subsection}
  {\normalsize\bfseries\color{neutral}}{\thesubsection}{0.5em}{}

\titleformat{\subsubsection}
  {\small\bfseries\color{neutral}}{}{0em}{}

\titlespacing{\section}{0pt}{16pt}{6pt}
\titlespacing{\subsection}{0pt}{10pt}{4pt}
\titlespacing{\subsubsection}{0pt}{8pt}{3pt}

%% --- fancyhdr ---
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[L]{\small\color{neutral} PLAYER_USERNAME}
\fancyfoot[R]{\small\color{neutral} \thepage}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0.3pt}
\setlength{\footskip}{22pt}

%% --- List defaults ---
\setlist{topsep=3pt, itemsep=2pt, parsep=0pt}
"""

_TITLE_BLOCK = r"""
\noindent
\begin{tcolorbox}[
  enhanced, sharp corners, arc=0pt,
  colback=accent!8!white, colframe=accent,
  boxrule=0.8pt, left=12pt, right=12pt, top=10pt, bottom=10pt,
]
\begin{minipage}[t]{0.56\linewidth}
  {\LARGE\bfseries\color{accent} PLAYER_USERNAME}\\[3pt]
  {\large\color{neutral} Chess Coaching Report}
\end{minipage}%
\hfill
\begin{minipage}[t]{0.41\linewidth}
  \raggedleft\small\color{neutral}
  \textbf{Generated:} REPORT_DATE\\
  \textbf{Quality score:} QUALITY_SCORE\,/\,100
\end{minipage}
\end{tcolorbox}

\vspace{6pt}
"""


def _build_tex(body_latex: str, username: str, generated_at: str, quality_score: int) -> str:
    username_esc = _esc(username)
    date_esc     = _esc(generated_at)

    preamble = _PREAMBLE.replace('PLAYER_USERNAME', username_esc)
    title    = _TITLE_BLOCK \
                 .replace('PLAYER_USERNAME', username_esc) \
                 .replace('REPORT_DATE',     date_esc) \
                 .replace('QUALITY_SCORE',   str(quality_score))

    return (
        preamble
        + '\n\\begin{document}\n'
        + '\\thispagestyle{fancy}\n'
        + title
        + '\n'
        + body_latex
        + '\n\\end{document}\n'
    )


# ── XeLaTeX compilation ───────────────────────────────────────────────────────

def _compile_latex(tex_path: Path, pdf_out: Path) -> bool:
    """Compile tex_path with xelatex twice (for references). Returns True on success."""
    xelatex = shutil.which('xelatex')
    if not xelatex:
        return False

    out_dir = str(tex_path.parent)
    cmd = [xelatex, '-interaction=nonstopmode', '-output-directory', out_dir, str(tex_path)]

    for _ in range(2):
        subprocess.run(cmd, capture_output=True, cwd=out_dir)

    produced = tex_path.with_suffix('.pdf')
    if produced.exists():
        if produced != pdf_out:
            produced.rename(pdf_out)
        # Clean up auxiliary files.
        for ext in ('.aux', '.log', '.out', '.toc'):
            aux = tex_path.with_suffix(ext)
            if aux.exists():
                aux.unlink()
        return True
    return False


# ── Public API ────────────────────────────────────────────────────────────────

def generate_coaching_pdf(
    markdown_text: str,
    output_path: str,
    username: str,
    generated_at: str,
    quality_score: int = 0,
) -> None:
    """Generate the coaching session PDF from Claude's markdown output."""
    pdf_path = Path(output_path)
    tex_path = pdf_path.with_suffix('.tex')

    body  = _convert_body(markdown_text)
    latex = _build_tex(body, username, generated_at, quality_score)

    tex_path.write_text(latex, encoding='utf-8')

    if _compile_latex(tex_path, pdf_path):
        return

    # Fallback: ReportLab plain text (no markdown parsing) if xelatex missing.
    print("xelatex not found — falling back to ReportLab plain text PDF.")
    _generate_pdf_reportlab(markdown_text, output_path, username, generated_at)


# ── ReportLab fallback ────────────────────────────────────────────────────────
# Used when xelatex is not installed. Renders markdown inline markup correctly
# using ReportLab's XML-based Paragraph tags.

def _rl_escape(text: str) -> str:
    """Escape XML special chars so ReportLab doesn't choke on raw &, <, >."""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _inline_rl(text: str) -> str:
    """Convert markdown inline markup to ReportLab XML paragraph markup."""
    # Protect backtick spans first (their content is escaped separately).
    slots: dict[str, str] = {}
    counter = [0]

    def protect_backtick(m: re.Match) -> str:
        inner = _rl_escape(m.group(1))
        key = f'__SLOT{counter[0]}__'
        slots[key] = f'<font name="Courier" size="9"><b>{inner}</b></font>'
        counter[0] += 1
        return key

    text = _BACKTICK_RE.sub(protect_backtick, text)

    # Escape XML chars in the remaining free text.
    text = _rl_escape(text)

    # Bold: **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

    # Italic: *text*
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)

    # Chess notation → bold monospace.
    def chess_rl(m: re.Match) -> str:
        return f'<font name="Courier" size="9"><b>{m.group(0)}</b></font>'

    text = _CHESS_RE.sub(chess_rl, text)

    # Restore protected slots.
    for key, val in slots.items():
        text = text.replace(key, val)

    return text


def _generate_pdf_reportlab(markdown_text: str, output_path: str, username: str, generated_at: str) -> None:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        topMargin=0.75*inch, bottomMargin=0.75*inch,
        leftMargin=1*inch, rightMargin=1*inch,
    )
    dark = colors.HexColor('#1f3a5f')
    body_color = colors.HexColor('#222222')
    dim_color  = colors.HexColor('#555555')
    styles = {
        'Title':  ParagraphStyle('Title',  fontName='Times-Bold',   fontSize=22, textColor=dark,       spaceAfter=4,  leading=28),
        'Sub':    ParagraphStyle('Sub',    fontName='Times-Roman',  fontSize=11, textColor=dim_color,   spaceAfter=3,  leading=16),
        'H1':     ParagraphStyle('H1',     fontName='Times-Bold',   fontSize=16, textColor=dark,        spaceBefore=12, spaceAfter=4, leading=20),
        'H2':     ParagraphStyle('H2',     fontName='Times-Bold',   fontSize=13, textColor=dark,        spaceBefore=8,  spaceAfter=3, leading=17),
        'H3':     ParagraphStyle('H3',     fontName='Times-BoldItalic', fontSize=11, textColor=dark,    spaceBefore=6,  spaceAfter=2, leading=15),
        'Body':   ParagraphStyle('Body',   fontName='Times-Roman',  fontSize=10, textColor=body_color,  leading=15),
        'Bullet': ParagraphStyle('Bullet', fontName='Times-Roman',  fontSize=10, textColor=body_color,  leading=14, leftIndent=14),
    }

    _enum_re = re.compile(r'^\d+\.\s+(.+)')
    in_list = False
    story = [
        Paragraph('Chess Coaching Report', styles['Title']),
        Paragraph(_rl_escape(username), styles['Sub']),
        Paragraph(_rl_escape(generated_at), styles['Sub']),
        HRFlowable(width='100%', thickness=2, color=dark),
        Spacer(1, 0.15*inch),
    ]

    for line in markdown_text.splitlines():
        s = line.strip()
        if not s:
            story.append(Spacer(1, 0.08*inch))
        elif s.startswith('# '):
            story.append(Paragraph(_inline_rl(s[2:]), styles['H1']))
        elif s.startswith('## '):
            story.append(Paragraph(_inline_rl(s[3:]), styles['H2']))
        elif s.startswith('### '):
            story.append(Paragraph(_inline_rl(s[4:]), styles['H3']))
        elif s.startswith(('- ', '* ')):
            story.append(Paragraph(f'• {_inline_rl(s[2:])}', styles['Bullet']))
        elif _enum_re.match(s):
            story.append(Paragraph(f'• {_inline_rl(_enum_re.match(s).group(1))}', styles['Bullet']))
        elif s.startswith('---'):
            story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#aaa')))
        else:
            story.append(Paragraph(_inline_rl(s), styles['Body']))

    doc.build(story)


# ── Teaching guide (ReportLab, static content) ───────────────────────────────

TEACHING_CONTENT = [
    ("title",    "Chess Coach Agent — How It Works"),
    ("subtitle", "A Teaching Guide for the Developer"),
    ("divider",  ""),

    ("h1", "What Is This Project?"),
    ("body", (
        "Chess Coach Agent is a multi-agent AI system that analyzes your Chess.com games "
        "and produces a personalized coaching plan. Three specialized AI agents — each powered "
        "by Claude — collaborate in a pipeline. Each agent has one job, and they pass structured "
        "information between each other through a shared state object."
    )),

    ("h1", "What Is LangGraph?"),
    ("body", (
        "LangGraph is a library built on top of LangChain that lets you define AI workflows as "
        "a directed graph. Each box is a function (a node) and the arrows between boxes are edges. "
        "The graph can loop — an agent can run, get feedback, and run again until the output meets "
        "a quality threshold."
    )),
    ("body", (
        "In this project, the Coach node and Critic node form a feedback loop: if the Critic "
        "scores the coaching report below 70/100, LangGraph sends control back to the Coach "
        "with the critic's feedback included. This continues up to 3 times."
    )),

    ("h1", "The Three Agents"),

    ("h2", "Agent 1: The Analyst"),
    ("body", (
        "The Analyst fetches your recent games from Chess.com's public API, parses the PGN "
        "move notation using python-chess, and sends all the game data to Claude asking for "
        "pattern recognition across games — not a move-by-move analysis of one game, but "
        "recurring themes. Moves made under time pressure (less than 30 seconds) are flagged "
        "so the Coach can deprioritize them."
    )),

    ("h2", "Agent 2: The Coach"),
    ("body", (
        "The Coach has two steps: (1) interview you about your goals and openings, "
        "(2) generate a full coaching plan incorporating the Analyst's findings and your goals. "
        "If the Critic rejects the report, the Coach runs again with the critic's feedback "
        "included in the prompt so Claude knows exactly what to fix."
    )),

    ("h2", "Agent 3: The Critic"),
    ("body", (
        "The Critic is Claude acting as a quality-control judge. It scores the coaching report "
        "across four dimensions: specificity, goal alignment, actionability, and time-pressure "
        "handling. Below 70 = rejection with written feedback. 70 or above = approved. "
        "Maximum 3 regeneration attempts before the best version is accepted."
    )),

    ("h1", "How State Works in LangGraph"),
    ("body", (
        "All agents share a single Python dictionary called ChessCoachState (a TypedDict). "
        "When a node runs, LangGraph passes the full current state. The node returns only the "
        "keys it wants to update. LangGraph merges those updates before passing state to the next node. "
        "No node sees stale data."
    )),

    ("h1", "User Memory"),
    ("body", (
        "Chess.com usernames are saved to a local SQLite database. On future runs the system "
        "recognizes returning users and pre-fills their preferences. Chess.com's API is fully "
        "public — no OAuth or tokens required."
    )),

    ("h1", "Version History"),
    ("body", "V1.0 — Initial CLI pipeline with all three agents."),
    ("body", "V2.0 — Custom web UI with live agent node visualization, WebSocket backend, Web Speech API voice."),
    ("body", "V3.0 — Play vs Coach King (interactive chess with real-time coaching) and Practice mode (puzzles + opening trainer)."),
]


def generate_teaching_guide(output_path: str = 'TEACHING_GUIDE.pdf') -> None:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        topMargin=0.75*inch, bottomMargin=0.75*inch,
        leftMargin=1*inch, rightMargin=1*inch,
    )
    dark       = colors.HexColor('#1f3a5f')
    body_color = colors.HexColor('#222222')
    dim_color  = colors.HexColor('#555555')
    styles = {
        'Title': ParagraphStyle('Title', fontName='Times-Bold',        fontSize=24, textColor=dark,       spaceAfter=6,  leading=30),
        'Sub':   ParagraphStyle('Sub',   fontName='Times-Roman',       fontSize=11, textColor=dim_color,   spaceAfter=4,  leading=16),
        'H1':    ParagraphStyle('H1',    fontName='Times-Bold',        fontSize=16, textColor=dark,        spaceBefore=10, spaceAfter=4, leading=20),
        'H2':    ParagraphStyle('H2',    fontName='Times-Bold',        fontSize=13, textColor=dark,        spaceBefore=6,  spaceAfter=3, leading=17),
        'Body':  ParagraphStyle('Body',  fontName='Times-Roman',       fontSize=10, textColor=body_color,  leading=15),
    }

    story = []
    for kind, content in TEACHING_CONTENT:
        if kind == 'title':
            story.append(Paragraph(content, styles['Title']))
            story.append(Spacer(1, 0.1*inch))
        elif kind == 'subtitle':
            story.append(Paragraph(content, styles['Sub']))
            story.append(Spacer(1, 0.2*inch))
        elif kind == 'divider':
            story.append(HRFlowable(width='100%', thickness=2, color=dark))
            story.append(Spacer(1, 0.2*inch))
        elif kind == 'h1':
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph(content, styles['H1']))
            story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#aaa')))
            story.append(Spacer(1, 0.05*inch))
        elif kind == 'h2':
            story.append(Spacer(1, 0.1*inch))
            story.append(Paragraph(content, styles['H2']))
        elif kind == 'body':
            story.append(Paragraph(content, styles['Body']))
            story.append(Spacer(1, 0.08*inch))

    doc.build(story)
    print(f'Teaching guide written to {output_path}')
