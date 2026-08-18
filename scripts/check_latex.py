#!/usr/bin/env python3
"""Static LaTeX checks for sn-article.tex, for when no TeX is installed.

    python scripts/check_latex.py

This does not replace a compile. It catches the specific failures that have
actually cost us a round trip: an undefined control sequence, an unbalanced
environment, a tabular whose rows do not match its column spec, a TikZ style
or library used but not loaded, a figure too tall to place anywhere but a
float page, and the sn-jnl traps (\\orcid needing a file the class does not
ship, amsthm loaded after \\theoremstyle, \\jyear).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
TEX = PAPER / "sn-article.tex"
CLS = PAPER / "sn-jnl.cls"

KERNEL = set("""
begin end documentclass usepackage newcommand renewcommand providecommand newif
section subsection subsubsection paragraph label ref eqref cite citep citet
textbf textit emph texttt textsc textsuperscript underline footnote item
frac dfrac tfrac sum prod int lim log ln exp max min sup inf arg
alpha beta gamma delta epsilon varepsilon zeta eta theta iota kappa lambda mu nu
xi pi rho sigma tau upsilon phi varphi chi psi omega Gamma Delta Theta Lambda Xi
Pi Sigma Upsilon Phi Psi Omega infty partial nabla cdot cdots ldots dots vdots
times div pm mp leq geq neq approx equiv sim simeq propto subset subseteq
subsetneq supset supseteq in notin cup cap bigcup bigcap setminus emptyset
varnothing forall exists neg land lor to gets mapsto rightarrow leftarrow
Rightarrow Leftarrow left right big Big bigg Bigg bigl bigr Bigl Bigr
langle rangle lceil rceil lfloor rfloor lVert rVert
mathbb mathcal mathrm mathbf mathit mathsf mathtt boldsymbol operatorname
text quad qquad hspace vspace hfill vfill newline linebreak par noindent
centering raggedright raggedleft raggedbottom caption includegraphics
toprule midrule bottomrule botrule cmidrule multicolumn multirow
tabular table figure equation align aligned gather itemize enumerate
State Require Ensure If Else EndIf For EndFor While EndWhile Comment
algorithmic algorithm Function EndFunction Return
node draw path fill tikz tikzpicture usetikzlibrary tikzset tikzstyle
newtheorem theoremstyle proof qedhere setcounter
url href textcolor color definecolor
small footnotesize scriptsize tiny normalsize large Large LARGE huge Huge
selectfont fontsize rmfamily sffamily ttfamily bfseries itshape upshape
setlength addtolength newlength smallskip medskip bigskip
title author affil email keywords abstract maketitle appendix backmatter
bmhead sur fnm orgdiv orgname orgaddress city country postcode street
bibliography bibliographystyle makeatletter makeatother
overline underbrace overbrace hat bar vec tilde widetilde widehat
binom sqrt lesssim gtrsim ll gg mid nmid perp parallel angle le ge
succ prec succeq preceq star ast bullet circ oplus otimes top ell
substack nonumber textstyle displaystyle Pr not dagger verb
linewidth textwidth textheight else fi FloatBarrier
resizebox scalebox rotatebox
arraybackslash centering raggedright tabcolsep arrayrulewidth extrarowheight
ddagger ne ge le textbackslash tabularx bottomrule addlinespace
""".split())


def main() -> int:
    tex = TEX.read_text()
    cls = CLS.read_text(encoding="latin-1")
    body = tex[tex.index(r"\begin{document}"):]
    body_nc = re.sub(r"(?<!\\)%.*", "", body)
    all_nc = re.sub(r"(?<!\\)%.*", "", tex)
    bad: list[str] = []

    # 1. undefined control sequences
    defined = set(re.findall(r"\\(?:def|gdef|edef|xdef)\\([a-zA-Z@]+)", cls))
    defined |= set(re.findall(
        r"\\(?:newcommand|renewcommand|providecommand|DeclareRobustCommand"
        r"|DeclareOldFontCommand)\*?\{?\\([a-zA-Z@]+)", cls))
    defined |= set(re.findall(r"\\newenvironment\{(\w+)\}", cls))
    defined |= set(re.findall(
        r"\\(?:newcommand|renewcommand|providecommand|DeclareMathOperator"
        r"|newif\\if)\*?\{?\\?([a-zA-Z@]+)", tex))
    for cond in re.findall(r"\\newif\\if([a-zA-Z@]+)", tex):
        defined |= {cond, "if" + cond, cond + "true", cond + "false"}
    # `\\` is a line break, so `a\\weights` is text, not a control sequence.
    scan = re.sub(r"\\\\[a-zA-Z@]+", " ", body_nc)
    for m in sorted(set(re.findall(r"(?<!\\)\\([a-zA-Z@]+)", scan))):
        if m not in defined and m not in KERNEL:
            bad.append(f"possibly undefined macro \\{m}")

    # 2. environment balance
    for env in ("equation", "align", "algorithm", "algorithmic", "tabular",
                "table", "figure", "itemize", "enumerate", "tikzpicture"):
        b = len(re.findall(r"\\begin\{" + env + r"\*?\}", body_nc))
        e = len(re.findall(r"\\end\{" + env + r"\*?\}", body_nc))
        if b != e:
            bad.append(f"unbalanced {env}: {b} begin vs {e} end")

    # 3. brace balance
    depth = 0
    for line in body_nc.split("\n"):
        stripped = re.sub(r"(?<!\\)\\[{}]", "", line).replace("\\\\", "")
        stripped = re.sub(r"(?<!\\)\\[{}]", "", stripped)
        depth += stripped.count("{") - stripped.count("}")
    if depth:
        bad.append(f"brace depth {depth:+d} at end of body")

    # 4. tabular column counts
    def _split_rows(chunk: str) -> list[str]:
        """Split a tabular body on row terminators.

        A regex split on two backslashes also cuts inside cells such as
        `6\\,038`, because the digit separator and the row terminator share a
        prefix. Scanning character by character and consuming escapes is the
        only reliable way, and it matters: with the naive split two of the five
        rows in Table 1 were never checked and a 10-cell row passed.
        """
        rows, cur, k = [], [], 0
        while k < len(chunk):
            if chunk[k] == "\\" and k + 1 < len(chunk):
                if chunk[k + 1] == "\\":
                    rows.append("".join(cur)); cur = []; k += 2; continue
                cur.append(chunk[k:k + 2]); k += 2; continue
            cur.append(chunk[k]); k += 1
        rows.append("".join(cur))
        return rows

    lines = tex.split("\n")
    i = 0
    while i < len(lines):
        m = re.search(r"\\begin\{tabular\}\{(.*)\}\s*$", lines[i])
        if m:
            core = re.sub(r"@\{[^{}]*\}", "", m.group(1))
            core = re.sub(r"p\{[^{}]*\}", "p", core)
            ncol = len(re.findall(r"[lcrp]", core))
            j = i + 1
            chunk = []
            while j < len(lines) and r"\end{tabular}" not in lines[j]:
                chunk.append(re.sub(r"(?<!\\)%.*", "", lines[j]))
                j += 1
            for row in _split_rows(" ".join(chunk)):
                # Strip leading rules rather than skipping the row: the first
                # data row is glued to \midrule after the join, so filtering on
                # a leading rule silently exempted it. That is how a 10-cell
                # row in a 9-column spec passed.
                row = re.sub(r"\\(?:top|mid|bot|bottom|c)rule(?:\{[^{}]*\})?|\\addlinespace(?:\[[^]]*\])?", " ", row)
                if not row.strip() or "\\multicolumn" in row:
                    continue
                got = len(re.findall(r"(?<!\\)&", row)) + 1
                if got != ncol:
                    bad.append(f"tabular near line {i+1}: row has {got} cells, "
                               f"spec has {ncol}: {row.strip()[:44]!r}")
            i = j
        i += 1

    # 5. tikz styles and libraries
    if r"\begin{tikzpicture}" in all_nc:
        pic = all_nc[all_nc.index(r"\begin{tikzpicture}"):
                     all_nc.index(r"\end{tikzpicture}")]
        styles = set(re.findall(r"(\w+)/\.style", all_nc))
        for mm in re.finditer(r"\\(?:node|draw|path)\s*\[([^\]]*)\]", pic):
            for tok in mm.group(1).split(","):
                name = tok.strip().split("=")[0].strip()
                if re.fullmatch(r"sn[a-z]+", name or "") and name not in styles:
                    bad.append(f"tikz style '{name}' used but not defined")
        libs = "".join(re.findall(r"\\usetikzlibrary\{([^}]*)\}", all_nc))
        for need, why in (("positioning", r"=\s*of\s"), ("arrows", "Stealth"),
                          ("fit", r"fit\s*="), ("calc", r"\(\$")):
            if re.search(why, pic) and need not in libs:
                bad.append(f"tikz library '{need}' needed but not loaded")

    # 6. figures too tall to place outside a float page
    try:
        from PIL import Image
        tw, th = 160.0, 216.0
        topfrac = float(re.search(r"\\renewcommand\{\\topfraction\}\{([\d.]+)\}",
                                  tex).group(1))
        for mm in re.finditer(
                r"\\includegraphics\[width=([^\]]*)\]\{(Fig\d\.png)\}", tex):
            spec, fn = mm.group(1), mm.group(2)
            fm = re.match(r"([\d.]+)\\(?:text|line)width", spec)
            frac = float(fm.group(1)) if fm else 1.0
            w, h = Image.open(PAPER / "figures" / fn).size
            hmm = tw * frac * h / w
            if hmm > topfrac * th:
                bad.append(f"{fn} is {hmm:.0f}mm tall, over topfraction "
                           f"({topfrac*th:.0f}mm): float-page only")
    except Exception:                                    # noqa: BLE001
        pass

    # 7. sn-jnl specific traps
    if re.search(r"(?<!%)\\orcid\{", all_nc):
        bad.append(r"\orcid used: the class does \includegraphics{Orcidlogo.eps}, "
                   "which is not shipped")
    if r"\jyear" in all_nc:
        bad.append(r"\jyear is not defined in this class version")
    i_ams, i_sty = tex.find(r"\usepackage{amsthm}"), tex.find(r"\theoremstyle{")
    if i_sty >= 0 and (i_ams < 0 or i_ams > i_sty):
        bad.append("amsthm must be loaded before \\theoremstyle")
    if r"\graphicspath" not in tex:
        bad.append("no \\graphicspath: figures/ will not be found on Overleaf")

    # 8. float placement discipline
    tight = re.findall(r"\\begin\{(?:figure|table|algorithm)\}\[([^\]]*)\]", all_nc)
    for spec in set(tight):
        if spec in ("h", "H", "t"):
            bad.append(f"restrictive float specifier [{spec}] invites deferral")
    if "placeins" not in tex:
        bad.append("placeins not loaded: deferred floats can migrate to the end")

    if bad:
        print("LATEX ISSUES:")
        for b in bad:
            print("  -", b)
        return 1
    print("latex static checks pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
