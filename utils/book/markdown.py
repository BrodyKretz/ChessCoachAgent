"""Lightweight markdown → ReportLab flowables.

Just enough to render the Analyst and Coach LLM outputs in the workbook
voice — paragraphs, bullets, sub-headings, and inline emphasis. Anything
fancier (tables, code blocks) is out of scope; the LLM output stays in
that subset by construction.
"""

from __future__ import annotations

import re

from reportlab.platypus import Paragraph, Spacer


# ── Inline markup ────────────────────────────────────────────────────────

_BOLD_RE   = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_CODE_RE   = re.compile(r"`([^`]+)`")


def _esc_xml(text: str) -> str:
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))


def inline_markup(text: str) -> str:
    """Convert markdown inline emphasis to ReportLab Paragraph XML markup."""
    # Protect code spans first so their inner content isn't escaped twice.
    slots: dict[str, str] = {}

    def stash_code(m: re.Match) -> str:
        key = f"__CODESLOT_{len(slots)}__"
        slots[key] = f"<font name='Courier' size='9'>{_esc_xml(m.group(1))}</font>"
        return key
    text = _CODE_RE.sub(stash_code, text)

    text = _esc_xml(text)
    text = _BOLD_RE.sub(r"<b>\1</b>", text)
    text = _ITALIC_RE.sub(r"<i>\1</i>", text)

    for k, v in slots.items():
        text = text.replace(k, v)
    return text


# ── Block-level conversion ───────────────────────────────────────────────

_BULLET_RE = re.compile(r"^\s*[-*]\s+(.+)$")
_NUMBERED_RE = re.compile(r"^\s*\d+\.\s+(.+)$")


def markdown_to_flowables(md: str, styles: dict) -> list:
    """Render markdown text as a list of Platypus Flowables.

    Recognized:
        '## ' -> subsection_h
        '### ' -> small heading (subsection_sub)
        '- foo' / '* foo' -> bullet line
        '1. foo' -> numbered bullet line (rendered as a bullet, the
                    workbook style doesn't use the digit visually)
        blank line -> paragraph break
        '---' -> small vertical spacer (treat as section pause)
        everything else -> body paragraph

    Multiple consecutive body lines are joined into one paragraph (markdown
    convention: a paragraph break needs a blank line).
    """
    flow: list = []
    buf: list[str] = []

    def flush_paragraph() -> None:
        if not buf:
            return
        joined = " ".join(s.strip() for s in buf).strip()
        if joined:
            flow.append(Paragraph(inline_markup(joined), styles["body"]))
        buf.clear()

    for raw in md.splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            continue

        if stripped.startswith("# "):
            # Top-level title — caller usually provides this via chapter
            # heading already. Render as a subsection_h so the analyst's
            # internal '# Foo' doesn't dominate the page.
            flush_paragraph()
            flow.append(Paragraph(inline_markup(stripped[2:]),
                                   styles["subsection_h"]))
            continue

        if stripped.startswith("## "):
            flush_paragraph()
            flow.append(Paragraph(inline_markup(stripped[3:]),
                                   styles["subsection_h"]))
            continue

        if stripped.startswith("### "):
            flush_paragraph()
            flow.append(Paragraph(inline_markup(stripped[4:]),
                                   styles["subsection_sub"]))
            continue

        if stripped.startswith("---"):
            flush_paragraph()
            flow.append(Spacer(1, 6))
            continue

        m = _BULLET_RE.match(stripped) or _NUMBERED_RE.match(stripped)
        if m:
            flush_paragraph()
            flow.append(Paragraph(f"• {inline_markup(m.group(1))}",
                                  styles["body_bullet"]))
            continue

        buf.append(stripped)

    flush_paragraph()
    return flow
