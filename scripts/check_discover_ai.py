#!/usr/bin/env python3
"""Check the manuscript against Discover AI submission guidelines.

Springer states that artwork problems are the single most common reason
submissions are returned BEFORE peer review, so these are worth automating
rather than eyeballing. Run before every submission:

    python scripts/check_discover_ai.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "paper" / "sn-article.tex"
BIB = ROOT / "paper" / "paper.bib"
FIGS = ROOT / "paper" / "figures"


def check() -> list[str]:
    bad: list[str] = []
    if not TEX.exists():
        return ["manuscript not found"]
    t = TEX.read_text()

    opts = re.search(r"documentclass\[([^\]]*)\]", t)
    if not opts or "Numbered" not in opts.group(1):
        bad.append("citations must be numeric [n]: add the 'Numbered' class option")

    if re.search(r"\\subsubsection", t):
        bad.append("more than three heading levels")

    # floats must be cited in consecutive numerical order
    for kind in ("fig", "tab"):
        labels = re.findall(rf"\\label\{{{kind}:(\w+)\}}", t)
        order: list[str] = []
        for m in re.finditer(rf"\\ref\{{{kind}:(\w+)\}}", t):
            if m.group(1) not in order:
                order.append(m.group(1))
        if set(labels) - set(order):
            bad.append(f"{kind} never cited in text: {sorted(set(labels)-set(order))}")
        elif labels != order:
            bad.append(f"{kind} labels not in first-citation order: {labels} vs {order}")

    ab = re.search(r"\\abstract\{(.*?)\n\n\\keywords", t, re.S)
    if ab:
        n = len(re.sub(r"\\[a-zA-Z]+|[{}$&%]", " ", ab.group(1)).split())
        if n > 250:
            bad.append(f"abstract is {n} words (limit 250)")

    for abbr, full in [("NDCG", "cumulative gain"), ("LOO", "leave-one-out")]:
        if abbr in t and full not in t.lower():
            bad.append(f"{abbr} used but never defined at first mention")

    # Springer: name figure files Fig<n>
    used = re.findall(r"includegraphics\[[^]]*\]\{([^}]+)\}", t)
    for f in used:
        if not re.match(r"Fig\d+\.", f):
            bad.append(f"figure file '{f}' should be named Fig<n>.<ext>")
        if not (FIGS / f).exists():
            bad.append(f"figure file missing: {f}")

    for decl in ("Funding", "Competing interests", "Ethics approval",
                 "Data availability", "Code availability"):
        if decl not in t:
            bad.append(f"missing declaration: {decl}")
    if "[To be completed" in t:
        bad.append("a declaration is still a placeholder")

    if t.count("{") != t.count("}"):
        bad.append("unbalanced braces")
    if t.count("$") % 2:
        bad.append("unbalanced math delimiters")

    labels = set(re.findall(r"\\label\{([^}]+)\}", t))
    refs = set(re.findall(r"\\ref\{([^}]+)\}", t))
    if refs - labels:
        bad.append(f"broken \\ref: {sorted(refs - labels)}")

    # TikZ figures: verify every node reference resolves and libraries are
    # loaded. A malformed picture fails at compile time with an error that is
    # often hard to localise, so it is cheaper to check statically.
    for pic in re.findall(r"\\begin\{tikzpicture\}(.*?)\\end\{tikzpicture\}", t, re.S):
        if pic.count("{") != pic.count("}"):
            bad.append("unbalanced braces inside a tikzpicture")
        if len(re.findall(r"\\node", pic)) != len(re.findall(r"\\node\[[^\]]*\][^;]*;", pic)):
            bad.append("a \\node in tikzpicture is not terminated with ';'")
        if len(re.findall(r"\\draw", pic)) != len(re.findall(r"\\draw\[[^\]]*\][^;]*;", pic)):
            bad.append("a \\draw in tikzpicture is not terminated with ';'")
        declared = set(re.findall(r"^\s*(\w+)/\.style", t, re.M))
        used = set(re.findall(r"\\node\[(\w+)", pic)) | set(re.findall(r"\\draw\[(\w+)", pic))
        undeclared = used - declared - {"fit"}
        if undeclared:
            bad.append(f"undeclared tikz styles: {sorted(undeclared)}")
        libs = re.search(r"usetikzlibrary\{([^}]*)\}", t)
        loaded = {l.strip() for l in libs.group(1).split(",")} if libs else set()
        for lib, needed in (("arrows.meta", "Stealth" in pic),
                            ("positioning", "=of " in pic),
                            ("fit", "fit=" in pic),
                            ("backgrounds", "background layer" in pic)):
            if needed and lib not in loaded:
                bad.append(f"tikz library '{lib}' used but not loaded")

    if BIB.exists():
        cited = {c.strip() for g in re.findall(r"\\cite[a-z]*\{([^}]*)\}", t)
                 for c in g.split(",")}
        keys = set(re.findall(r"@\w+\{([^,]+),", BIB.read_text()))
        if cited - keys:
            bad.append(f"citations with no bib entry: {sorted(cited - keys)}")

    return bad


if __name__ == "__main__":
    problems = check()
    if problems:
        print("DISCOVER AI COMPLIANCE ISSUES:")
        for p in problems:
            print("  -", p)
        sys.exit(1 if "--strict" in sys.argv else 0)
    print("manuscript complies with Discover AI submission guidelines")
