#!/usr/bin/env python3
"""Extract float environments from the KBS manuscript by label.

Used by the KAIS main/ESM split. Extracting rather than retyping is the whole
point: every number in a table stays byte-identical to the version that
`check_paper_numbers.py` validates against `artefacts/`, so the split cannot
introduce a transcription error.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "paper-kbs" / "kbs-article.tex"


def float_blocks(text: str | None = None) -> dict[str, tuple[str, str]]:
    """Map label -> (environment, full source including \\begin/\\end)."""
    text = text if text is not None else SRC.read_text(encoding="utf-8")
    out: dict[str, tuple[str, str]] = {}
    pattern = re.compile(
        r"\\begin\{(table\*?|figure\*?|algorithm)\}(.*?)\\end\{\1\}", re.S)
    for m in pattern.finditer(text):
        env, body = m.group(1), m.group(2)
        lab = re.search(r"\\label\{([^}]*)\}", body)
        if lab:
            out[lab.group(1)] = (env, m.group(0))
    return out


def get(label: str, *, star: bool | None = None,
        placement: str | None = None) -> str:
    """Return one float, optionally re-starring and re-placing it.

    `star=False` demotes `table*` to `table`, which is what the single-column
    Springer class needs.
    """
    env, src = float_blocks()[label]
    base = env.rstrip("*")
    if star is not None and base in ("table", "figure"):
        want = base + ("*" if star else "")
        src = src.replace(f"\\begin{{{env}}}", f"\\begin{{{want}}}", 1)
        src = src.replace(f"\\end{{{env}}}", f"\\end{{{want}}}", 1)
    if placement:
        src = re.sub(r"^(\\begin\{[a-z*]+\})(\[[^\]]*\])?",
                     lambda m: m.group(1) + f"[{placement}]", src, count=1)
    return src


if __name__ == "__main__":
    for label, (env, src) in float_blocks().items():
        print(f"{env:9s} {label:28s} {len(src.splitlines()):4d} lines")
