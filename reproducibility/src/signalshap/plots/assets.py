"""Paper assets: figures F1-F7 and tables T1-T8 (spec §13).

Every number here is read from artefacts/ JSON -- nothing is hand-typed, per
spec §14 rule 1. Tables are emitted as both Markdown (for review) and LaTeX
(for the Springer template).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..config import ARTEFACTS, SOURCES
from ..segments.segments import SEGMENT_NAMES

FIG = ARTEFACTS / "figures"
TAB = ARTEFACTS / "tables"

# Springer Nature artwork rules (Discover AI submission guidelines):
#   * lettering in a sans-serif face at 8-12 pt, with minimal size variance
#     within a figure -- no 8 pt axis ticks next to 20 pt labels;
#   * no titles or captions inside the artwork (captions live in the text);
#   * 300 dpi minimum for halftones.
# Artwork problems are the single most common reason submissions are returned
# before peer review, so these are set globally rather than per figure.
SN_FONT_MIN = 8
plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 300,
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 9,
    "axes.titlesize": 10, "axes.labelsize": 9,
    "xtick.labelsize": SN_FONT_MIN, "ytick.labelsize": SN_FONT_MIN,
    "legend.fontsize": SN_FONT_MIN,
    "axes.grid": True, "grid.alpha": 0.3, "axes.spines.top": False,
    "axes.spines.right": False, "figure.autolayout": True,
})

# Monochrome throughout. Every figure in this paper is printed black-only, so
# a source's identity must be carried by GREY LEVEL plus MARKER SHAPE, never by
# hue alone. This is the convention in the game-theoretic XAI literature and it
# has two practical consequences the reviewer asked for: the figures survive
# greyscale reproduction, and they are colourblind-safe by construction.
# Grey levels are spaced >=0.16 apart so adjacent bars stay distinguishable
# after halftoning; the shapes disambiguate the rest.
# Colour is restored for the DATA figures. Only the architecture diagram
# (Fig 1) is black-only, matching the convention in the game-theoretic XAI
# literature for schematics. Data plots keep colour because it carries
# information here -- five sources across three corpora is a lot to encode --
# but every source ALSO gets a distinct marker and hatch, so the figures stay
# readable in greyscale and for colour-vision deficiency. The palette is
# Okabe-Ito, which is colourblind-safe by construction.
PALETTE = {"cf": "#0072B2", "ct": "#D55E00", "pop": "#009E73",
           "rec": "#CC79A7", "seq": "#E69F00"}

#: Per-source marker, so a source is identifiable in a scatter without colour.
SOURCE_MARK = {"cf": "o", "ct": "s", "pop": "^", "rec": "D", "seq": "v"}

#: Segment colours (Okabe-Ito, colourblind-safe), for the per-segment panels.
SEGMENT_COLOURS = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00"]

#: Method colours for grouped bar charts (Okabe-Ito, colourblind-safe).
BAR_COLOURS = ["#999999", "#E69F00", "#56B4E9", "#009E73", "#0072B2", "#D55E00"]

#: Per-source hatch, so a source is identifiable in a bar chart without colour.
SOURCE_HATCH = {"cf": "", "ct": "///", "pop": "...", "rec": "xxx", "seq": "\\\\"}

#: Publication names. Internal identifiers (ml_1m, amazon_book_lgcn) are for
#: filenames and JSON keys; artwork and tables use the corpus names a reader
#: recognises.
DISPLAY = {"ml_1m": "MovieLens-1M",
           # The timestamped corpora the study actually uses. These were
           # missing, so raw loader identifiers ("gowalla_ts",
           # "amazon_video_games") leaked into figure legends and table rows
           # while the withdrawn LightGCN splits kept tidy names.
           "gowalla_ts": "Gowalla", "amazon_video_games": "Amazon-VG",
           # Withdrawn pilot corpora, retained so archived artefacts still
           # render with readable names.
           "yelp2018": "Yelp2018", "gowalla": "Gowalla (LightGCN)",
           "amazon_book_lgcn": "Amazon-Book", "lastfm_2k": "LastFM-2K",
           "amazon_book": "Amazon-Book"}


def disp(name: str) -> str:
    return DISPLAY.get(name, name)


def _dirs() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)


#: Reporting order for corpora: dense to sparse, matching Table 1 and every
#: table in the manuscript.
PAPER_ORDER = ("ml_1m", "amazon_video_games", "gowalla_ts")


def corpus_order(results: dict) -> list[str]:
    """Corpora in the manuscript's dense-to-sparse order.

    `results` is built by globbing `results_*.json`, so its natural order is
    ALPHABETICAL: amazon_video_games, gowalla_ts, ml_1m. Every table in the
    paper reports dense to sparse, and MovieLens carries the main claims, so
    a figure in alphabetical order silently disagrees with the text beside it
    and buries the reference corpus in the right-hand panel.

    F3 already worked around this locally; the other figures did not, so a
    regeneration reordered five of seven panels. Shared here so the ordering
    is one decision rather than six.
    """
    known = [n for n in PAPER_ORDER if n in results]
    return known + [n for n in sorted(results) if n not in PAPER_ORDER]


def _tex_safe(x):
    """Escape LaTeX specials in generated cells, leaving intentional math alone."""
    if not isinstance(x, str):
        return x
    if x.count("$") >= 2:          # contains math: escape only outside $...$
        parts = x.split("$")
        for i in range(0, len(parts), 2):   # even indices are outside math
            parts[i] = (parts[i].replace("_", r"\_").replace("&", r"\&")
                        .replace("%", r"\%").replace("#", r"\#")
                        .replace("—", "--").replace("±", r"\,$\pm$\,"))
        return "$".join(parts)
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                 ("_", r"\_"), ("#", r"\#"), ("—", "--"), ("±", r"$\pm$"),
                 ("≥", r"$\geq$"), ("Δ", r"$\Delta$"), ("τ", r"$\tau$"),
                 ("λ", r"$\lambda$"), ("φ", r"$\varphi$")):
        x = x.replace(a, b)
    return x


def _save_table(df: pd.DataFrame, name: str, caption: str) -> None:
    """Emit Markdown (review), LaTeX (Springer template), and CSV.

    LaTeX output is escaped so `\input{}` compiles directly -- generated cells
    can legitimately contain _, &, %, and en-dashes.
    """
    _dirs()
    (TAB / f"{name}.md").write_text(f"**{caption}**\n\n{df.to_markdown(index=False)}\n")
    df.to_csv(TAB / f"{name}.csv", index=False)

    tex = df.copy()
    tex.columns = [_tex_safe(c) for c in tex.columns]
    for c in tex.columns:
        tex[c] = tex[c].map(_tex_safe)
    body = tex.to_latex(index=False, escape=False, longtable=False,
                        column_format="l" * len(tex.columns))
    (TAB / f"{name}.tex").write_text(
        "\\begin{table}[htbp]\n\\centering\n\\footnotesize\n"
        f"\\caption{{{_tex_safe(caption)}}}\n\\label{{tab:{name}}}\n"
        f"{body}\\end{{table}}\n"
    )


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #


def fig1_workflow() -> Path:
    """F1: the pipeline, five sources -> 32 coalitions -> Shapley -> fusion."""
    _dirs()
    fig, ax = plt.subplots(figsize=(11, 3.1))
    ax.axis("off")
    # Monochrome, matching the TikZ version in the manuscript. Stage identity is
    # carried by FILL LEVEL and LINE WEIGHT rather than hue, so the figure
    # survives greyscale printing and is colourblind-safe by construction. The
    # two stages that produce the paper's actual output -- the coalition game
    # and the Shapley values -- are drawn with a heavier rule so the eye lands
    # on them first. Fill levels stay >=5 percentage points apart to remain
    # separable after halftoning.
    steps = [
        ("5 signal\nsources", 0.96, 1.1),
        ("union top-$N_g$\ncandidates $C_u$\n(coalition-independent)", 0.91, 1.1),
        ("$2^5=32$\ncoalitions\n$v(S)$", 0.84, 2.0),
        ("exact Shapley\n$\\varphi_g$", 0.84, 2.0),
        ("segments +\nSignalShap-Fuse\n(Appendix A: no gain)", 1.00, 1.1),
    ]
    for i, (txt, shade, lw) in enumerate(steps):
        x = i * 2.15
        ax.add_patch(plt.Rectangle((x, 0.3), 1.75, 1.1, facecolor=str(shade),
                                   edgecolor="black", linewidth=lw))
        ax.text(x + 0.875, 0.85, txt, ha="center", va="center",
                fontsize=SN_FONT_MIN, color="black")
        if i < len(steps) - 1:
            ax.annotate("", xy=(x + 2.1, 0.85), xytext=(x + 1.78, 0.85),
                        arrowprops=dict(arrowstyle="->", lw=1.4, color="black"))
    ax.text(5.4, 0.02, "candidate set is identical for every coalition — "
            "differences in $v(S)$ reflect fusion, not retrieval",
            ha="center", fontsize=SN_FONT_MIN, style="italic", color="black")
    ax.set_xlim(-0.2, 11); ax.set_ylim(-0.1, 1.6)
    p = FIG / "F1_workflow.png"
    fig.savefig(p, bbox_inches="tight"); plt.close(fig)
    return p


def _ten_seed_ci(name: str) -> dict | None:
    """Ten-seed mean and 95% interval per source, if the artefact exists."""
    import json
    from pathlib import Path as _P
    f = _P("artefacts") / "final_seed_ci.json"
    if not f.exists():
        return None
    try:
        d = json.loads(f.read_text()).get(name, {}).get("ci")
    except (json.JSONDecodeError, OSError):
        return None
    return d if d and all(g in d for g in SOURCES) else None


def fig2_shapley_shares(results: dict) -> Path:
    """F2: per-source Shapley shares with seed CIs (main text, spec §2.7)."""
    _dirs()
    names = corpus_order(results)
    fig, axes = plt.subplots(1, len(names), figsize=(3.6 * len(names), 3.1), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, name in zip(axes, names):
        r = results[name]
        phi = r["e1_source_share"]["shapley"]
        # Prefer the ten-seed artefact over the three main-study seeds: the
        # ten-seed run is the paper's primary uncertainty estimate, and
        # plotting 1.96 SE from n = 3 understated it.
        ten = _ten_seed_ci(name)
        if ten:
            vals = [ten[g]["mean"] for g in SOURCES]
            err = [[ten[g]["mean"] - ten[g]["lo"] for g in SOURCES],
                   [ten[g]["hi"] - ten[g]["mean"] for g in SOURCES]]
        else:
            ci = r.get("multi_seed", {}).get("ci", {})
            vals = [phi[g] for g in SOURCES]
            err = [ci.get(g, {}).get("std", 0.0) for g in SOURCES]
        bars = ax.bar(SOURCES, vals, yerr=err, capsize=3,
                      color=[PALETTE[g] for g in SOURCES], edgecolor="black",
                      linewidth=0.8, error_kw={"ecolor": "black"})
        for bar, g in zip(bars, SOURCES):
            bar.set_hatch(SOURCE_HATCH[g])
        ax.axhline(0, color="black", lw=0.8)
        # The panel label must be the grand value of the SAME aggregation
        # level as the bars. Showing seed-42 v(G) above ten-seed bars made the
        # figure appear to violate efficiency: by efficiency the bars sum to
        # the ten-seed mean v(G), which differs from the seed-42 value (on
        # Gowalla by 24%).
        if ten:
            vg = sum(ten[g]["mean"] for g in SOURCES)
            lab = f"{disp(name)}\n$\\overline{{v(\\mathcal{{G}})}}$={vg:.4f} (10 seeds)"
        else:
            lab = (f"{disp(name)}\n$v(\\mathcal{{G}})$="
                   f"{r['e1_source_share']['v_grand']:.4f}")
        ax.set_title(lab, fontsize=9)
        ax.set_xlabel("source")
    axes[0].set_ylabel("Shapley value $\\varphi_g$")
    p = FIG / "F2_shapley_shares.png"
    fig.savefig(p, bbox_inches="tight"); plt.close(fig)
    return p


def _ten_seed_loo_gap(name: str) -> dict | None:
    """Ten-seed mean LOO and Shapley per source, if the artefact has them."""
    import json
    from pathlib import Path as _P
    f = _P("artefacts") / "final_seed_ci.json"
    if not f.exists():
        return None
    try:
        d = json.loads(f.read_text()).get(name)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(d, dict) or "loo_ci" not in d or "ci" not in d:
        return None
    if not all(g in d["loo_ci"] and g in d["ci"] for g in SOURCES):
        return None
    return {"loo": {g: d["loo_ci"][g]["mean"] for g in SOURCES},
            "shapley": {g: d["ci"][g]["mean"] for g in SOURCES}}


def fig3_loo_vs_shapley(results: dict) -> Path:
    """F3: LOO vs Shapley scatter -- the empirical content of Property 2."""
    _dirs()
    fig, ax = plt.subplots(figsize=(5.2, 4.6))
    # Source -> marker shape, corpus -> marker size. Neither encoding uses
    # colour, so all 15 (corpus, source) points remain separable in greyscale.
    # Largest marker for the corpus that carries the main claims, so the eye
    # lands on MovieLens first. Sorting by name would put amazon_video_games
    # first and invert the emphasis.
    _order = corpus_order(results)
    sizes = {n: s for n, s in zip(_order, (115, 62, 30, 30))}
    for name, r in ((k, results[k]) for k in _order):
        # Ten-seed means where the artefact has them, so this figure sits at
        # the same aggregation level as the LOO-vs-Shapley table. It used to
        # plot seed-42 points beneath ten-seed prose.
        e2 = r["e2_loo_vs_shapley"]
        ten = _ten_seed_loo_gap(name)
        if ten:
            e2 = {"loo": ten["loo"], "shapley": ten["shapley"]}
        for g in SOURCES:
            ax.scatter(e2["loo"][g], e2["shapley"][g], s=sizes.get(name, 70),
                       marker=SOURCE_MARK[g], color=PALETTE[g],
                       edgecolor="black", linewidth=0.7, zorder=3)
    lims = np.array(ax.get_xlim() + ax.get_ylim())
    lo, hi = lims.min(), lims.max()
    ax.plot([lo, hi], [lo, hi], "--", color="black", lw=1, zorder=1,
            label="LOO = Shapley")
    ax.axhline(0, color="black", lw=0.5, zorder=1)
    ax.axvline(0, color="black", lw=0.5, zorder=1)
    ax.set_xlabel("LOO attribution"); ax.set_ylabel("Shapley value $\\varphi_g$")
    # No internal figure number (asset order != paper order) and no em dash.
    ax.set_title("Ranking-stage LOO vs Shapley, ten-seed means\n"
                 "(points off the diagonal: the two rules disagree)",
                 fontsize=10)
    handles = [plt.Line2D([], [], marker=SOURCE_MARK[g], ls="",
                          color=PALETTE[g], mec="black", label=g)
               for g in SOURCES]
    handles += [plt.Line2D([], [], marker="o", ls="", color="white",
                           mec="black", ms=(sizes.get(n, 70) / 12) ** 0.5 * 2,
                           label=DISPLAY.get(n, n))
                for n in _order]
    ax.legend(handles=handles, fontsize=SN_FONT_MIN, ncol=2, loc="best")
    p = FIG / "F3_loo_vs_shapley.png"
    fig.savefig(p, bbox_inches="tight"); plt.close(fig)
    return p


def fig4_redundancy_heatmap(results: dict) -> Path:
    """F4: Kendall tau redundancy. pop-cf and rec-ct are PRE-REGISTERED."""
    _dirs()
    names = corpus_order(results)
    fig, axes = plt.subplots(1, len(names), figsize=(3.5 * len(names), 3.2))
    fig.set_layout_engine("none")       # we place the colorbar axes by hand
    axes = np.atleast_1d(axes)
    for ax, name in zip(axes, names):
        tau = results[name]["e2_loo_vs_shapley"]["kendall_tau"]
        M = np.eye(len(SOURCES))
        for i, a in enumerate(SOURCES):
            for j, b in enumerate(SOURCES):
                if i < j:
                    M[i, j] = M[j, i] = tau.get(f"{a}|{b}", tau.get(f"{b}|{a}", 0.0))
        # Diverging map centred on zero: this quantity is signed, and a
        # sequential greyscale hides the sign that the figure is about.
        # RdBu is replaced by a colourblind-safe diverging alternative.
        im = ax.imshow(M, cmap="PuOr_r", vmin=-1, vmax=1)
        ax.set_xticks(range(len(SOURCES)), SOURCES, fontsize=8)
        ax.set_yticks(range(len(SOURCES)), SOURCES, fontsize=8)
        ax.set_title(disp(name), fontsize=9); ax.grid(False)
        for i in range(len(SOURCES)):
            for j in range(len(SOURCES)):
                ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=SN_FONT_MIN,
                        color="white" if abs(M[i, j]) > 0.6 else "black")
    # Reserve space on the right and place the bar there, rather than letting
    # colorbar() steal width from the last panel -- that produced a bar
    # overlapping the matrix, which a reviewer flagged twice.
    fig.subplots_adjust(right=0.88)
    cax = fig.add_axes([0.90, 0.15, 0.015, 0.7])
    fig.colorbar(im, cax=cax, label="Kendall $\\tau$")
    p = FIG / "F4_redundancy_heatmap.png"
    fig.savefig(p)                      # no bbox_inches: it would undo the axes
    plt.close(fig)
    return p


def fig5_segment_radar(results: dict) -> Path:
    """F5: segment-level Shapley profiles (C4 heterogeneity).

    Point-range plot, not a radar chart. Radar encodes magnitude as radius and
    therefore area, which exaggerates differences quadratically and makes
    near-identical profiles look distinct; it also has no natural zero when
    values can be negative, which ours can. A shared linear axis lets a reader
    read the actual Shapley value per segment and see overlap honestly. The
    name is kept for artefact continuity.

    Monochrome: segments are distinguished by marker shape and grey level, so
    the figure survives greyscale reproduction.
    """
    _dirs()
    names = corpus_order(results)
    # Larger panels rather than smaller type: sn-jnl caps artwork text at 8pt
    # and SN_FONT_MIN is already there, so readability at journal-column width
    # has to come from geometry. A reviewer found the six panels hard to read.
    fig, axes = plt.subplots(1, len(names), figsize=(4.3 * len(names), 4.2),
                             sharey=True)
    axes = np.atleast_1d(axes)
    # Colour, like the other data figures -- four overlapping segments per
    # source are hard to separate by grey level alone at this marker size.
    # Shape still disambiguates, so the panel survives greyscale printing.
    seg_mark = {s: m for s, m in zip(SEGMENT_NAMES, ("o", "s", "^", "D", "v"))}
    seg_grey = {s: c for s, c in zip(SEGMENT_NAMES, SEGMENT_COLOURS)}
    xpos = np.arange(len(SOURCES))
    for ax, name in zip(axes, names):
        prof = results[name]["e3_segments"]["profiles"]
        live = [s for s in SEGMENT_NAMES if prof.get(s, {}).get("n_users", 0)]
        # Small horizontal offsets so coincident points remain countable.
        offs = np.linspace(-0.22, 0.22, max(len(live), 1))
        for seg, off in zip(live, offs):
            v = [prof[seg].get(g, 0.0) for g in SOURCES]
            ax.plot(xpos + off, v, ls="none", marker=seg_mark[seg], ms=7,
                    color=seg_grey[seg], mec="black", mew=0.6,
                    label=f"{seg} (n={prof[seg]['n_users']:,})")
        ax.axhline(0, color="black", lw=0.6)
        ax.set_xticks(xpos, SOURCES, fontsize=SN_FONT_MIN)
        ax.set_title(disp(name), fontsize=9)
        ax.tick_params(labelsize=SN_FONT_MIN)
        # One legend per panel: segment sizes differ by corpus, and a single
        # shared legend showed only the last panel's counts while appearing to
        # describe all three.
        ax.legend(fontsize=SN_FONT_MIN, loc="best", framealpha=0.9)
    axes[0].set_ylabel("segment Shapley value $\\varphi_g$")
    p = FIG / "F5_segment_radar.png"
    fig.savefig(p, bbox_inches="tight"); plt.close(fig)
    return p


def fig6_fuse_gain(results: dict) -> Path:
    """F6: SignalShap-Fuse lift, full-catalog protocol (spec §7)."""
    _dirs()
    names = corpus_order(results)
    # Every comparator the caption names must actually appear. A reviewer
    # flagged twice that the caption claimed separation from neural and
    # heuristic baselines while the chart showed only the three fusion
    # variants.
    methods = ["popularity_reference", "sasrec", "lightgcn",
               "uniform", "global", "signalshap_fuse"]
    labels = ["popularity", "SASRec", "LightGCN",
              "uniform", "globally-tuned", "SignalShap-Fuse"]
    fig, ax = plt.subplots(figsize=(1.9 * len(names) + 3.2, 3.4))
    w, x = 0.8 / len(methods), np.arange(len(names))
    for i, (m, lab) in enumerate(zip(methods, labels)):
        vals = [results[n]["e4_signalshap_fuse"]["full_catalog"][m]["ndcg_at_10"]
                for n in names]
        off = (i - (len(methods) - 1) / 2) * w
        b = ax.bar(x + off, vals, w, label=lab, edgecolor="black",
                   linewidth=0.7, color=BAR_COLOURS[i % len(BAR_COLOURS)],
                   hatch=("", "///", "...", "xxx", "\\\\", "")[i % 6])
        ax.bar_label(b, fmt="%.3f", fontsize=SN_FONT_MIN, padding=1.5)
    ax.set_xticks(x, [disp(n) for n in names]); ax.set_ylabel("NDCG@10 (full catalog)")
    # No internal figure number: the asset's F-number is its generation order,
    # not its position in the paper, and printing "F6" on the panel that the
    # manuscript labels Figure 7 confused a reviewer. The LaTeX caption is the
    # single source of truth for numbering.
    ax.set_title("SignalShap-Fuse vs fusion baselines\n"
                 "(full-catalog: items outside $C_u$ scored as misses)", fontsize=9.5)
    ax.legend(fontsize=8)
    p = FIG / "F6_fuse_gain.png"
    fig.savefig(p, bbox_inches="tight"); plt.close(fig)
    return p


def fig7_robustness(results: dict) -> Path:
    """F7: robustness small-multiples, with recall annotated per cell."""
    _dirs()
    names = corpus_order(results)
    fig, axes = plt.subplots(2, len(names), figsize=(3.5 * len(names), 5.4), squeeze=False)
    for j, name in enumerate(names):
        rb = results[name]["e5_robustness"]

        ax = axes[0][j]
        sweep = rb["candidate_size"]
        keys = sorted(sweep, key=lambda k: sweep[k]["n_max"])
        for g in SOURCES:
            ax.plot([sweep[k]["n_max"] for k in keys],
                    [sweep[k]["shapley"][g] for k in keys],
                    marker=SOURCE_MARK[g], ms=4, color=PALETTE[g], mec="black",
                    mew=0.5, label=g, lw=1.2)
        for k in keys:
            ax.annotate(f"r={sweep[k]['candidate_recall']:.2f}",
                        (sweep[k]["n_max"], ax.get_ylim()[0]), fontsize=SN_FONT_MIN,
                        ha="center", va="bottom", color="black")
        ax.set_title(f"{disp(name)}: $|C_u|$ sweep", fontsize=9)
        ax.set_xlabel("$N_{max}$"); ax.set_ylabel("$\\varphi_g$" if j == 0 else "")

        ax = axes[1][j]
        lam = rb["lambda_sensitivity"]
        lk = sorted(lam, key=lambda k: float(k.split("_")[1]))
        for g in SOURCES:
            ax.plot([float(k.split("_")[1]) for k in lk], [lam[k][g] for k in lk],
                    marker=SOURCE_MARK[g], ms=4, color=PALETTE[g], mec="black",
                    mew=0.5, ls="--", lw=1.2)
        ax.set_xscale("log"); ax.set_title(f"{disp(name)}: $\\lambda$ sensitivity", fontsize=9)
        ax.set_xlabel("$\\lambda$ (frozen = 1.0)")
        ax.set_ylabel("$\\varphi_g$" if j == 0 else "")
    axes[0][0].legend(fontsize=SN_FONT_MIN, ncol=2)
    p = FIG / "F7_robustness.png"
    fig.savefig(p, bbox_inches="tight"); plt.close(fig)
    return p


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #


def table1_positioning() -> pd.DataFrame:
    df = pd.DataFrame([
        ["SHAP / LIME / IG", "input features", "per-prediction", "no", "sampled or exact-small"],
        ["Ablation / LOO", "components", "global", "no", "exact but redundancy-blind"],
        ["LightGCN / SASRec", "n/a (models)", "n/a", "no", "n/a"],
        ["DyHuCoG", "hybrid components", "global", "partial", "Monte-Carlo"],
        ["SignalShap (ours)", "architectural sources", "global + per-user",
         "yes (segment-adaptive)", "exact, 32 coalitions"],
    ], columns=["Method", "Unit of attribution", "Granularity",
                "Closes the loop?", "Shapley computation"])
    _save_table(df, "T1_positioning",
                "T1 — Positioning: SignalShap attributes at the architectural-source "
                "level, which is a different game from feature-level XAI.")
    return df


def table2_datasets(results: dict, stats: dict) -> pd.DataFrame:
    rows = []
    for name, r in ((k, results[k]) for k in corpus_order(results)):
        # Authoritative source is the RUN's own stats, not dataset_stats.json:
        # auto-downsizing can shrink a corpus after the global stats file was
        # written, and printing the pre-downsize counts beside post-downsize
        # results would misstate the scale every downstream number was computed at.
        s = r.get("dataset_stats") or stats.get(name, {})
        glob_s = stats.get(name, {})
        if glob_s.get("users") and s.get("users") and glob_s["users"] != s["users"]:
            print(f"  [T2] {name}: using run scale {s['users']:,} users "
                  f"(dataset_stats.json says {glob_s['users']:,} -- pre-downsize)")
        e0a, e0b = r["e0a_candidates"], r["e0b_monotonicity"]
        rows.append({
            "Dataset": disp(name), "Users": s.get("users"), "Items": s.get("items"),
            "Interactions": s.get("interactions"),
            "Density (as used)": f"{s.get('density', 0) * 100:.4f}%",
            "$N_{max}$": e0a["n_max"],
            "$|C_u|$ mean±std": f"{e0a['abs_size_mean']:.1f}±{e0a['abs_size_std']:.1f}",
            "Candidate recall": f"{e0a['candidate_recall']:.3f}",
            "Gate (≥0.60)": "PASS" if e0a["gate_passes"] else "FAIL",
            "Monot. violations": f"{e0b['violations']}/{e0b['pairs_checked']}",
            "Prop. 2 applicable": "yes" if e0b["property2_applicable"] else "no",
        })
    df = pd.DataFrame(rows)
    _save_table(df, "T2_datasets",
                "T2 — Dataset statistics with the two PRECONDITIONS. Candidate "
                "recall is the ceiling on every metric in T5–T7; monotonicity "
                "violations determine whether Property 2 applies. Both must be "
                "inspected before any attribution number is interpreted. "
                "Density is computed as-used, never quoted.")
    return df


def table3_notation() -> pd.DataFrame:
    df = pd.DataFrame([
        ["$\\mathcal{G}$", "signal sources (players), $|\\mathcal{G}|=5$"],
        ["$S \\subseteq \\mathcal{G}$", "a coalition; there are $2^5=32$"],
        ["$C_u$", "coalition-independent candidate set for user $u$"],
        ["$N_{max}^{(d)}$", "pre-registered candidate cap, per dataset"],
        ["$z_{u,g,i}$", "per-user, per-source z-normalised score"],
        ["$w_g^{(S)}$", "ridge fusion weight, frozen $\\lambda$"],
        ["$v(S)$", "mean NDCG@10 over $C_u$ minus $v_0$"],
        ["$v_0$", "NDCG@10 of one frozen permutation (cosmetic offset)"],
        ["$\\varphi_g$", "exact Shapley value of source $g$"],
        ["LOO$(g)$", "$v(\\mathcal{G}) - v(\\mathcal{G} \\setminus \\{g\\})$"],
    ], columns=["Symbol", "Meaning"])
    _save_table(df, "T3_notation", "T3 — Notation.")
    return df


def table_efficiency(results: dict) -> pd.DataFrame:
    """Efficiency check, read from the artefact -- never hardcoded in prose.

    Two traps this table exists to avoid:
      * quoting a stale bound in the text while the JSON says something else;
      * printing rounded per-source values whose sum is 1 ulp off the rounded
        v(G), which looks like a violated axiom but is only display rounding.
    """
    rows = []
    for name, r in ((k, results[k]) for k in corpus_order(results)):
        e = r["e1_source_share"]["efficiency"]
        phi = r["e1_source_share"]["shapley"]
        rounded_sum = round(sum(round(v, 5) for v in phi.values()), 5)
        rows.append({
            "Dataset": disp(name),
            "$\\sum_g \\varphi_g$": f"{e['sum_phi']:.17g}",
            "$v(\\mathcal{G})$": f"{e['v_grand']:.17g}",
            "$|$error$|$": f"{e['abs_error']:.1e}",
            "Passes": "yes" if e["passes"] else "NO",
            "Sum of rounded $\\varphi_g$": f"{rounded_sum:.5f}",
            "Rounded $v(\\mathcal{G})$": f"{round(e['v_grand'], 5):.5f}",
            "Display-rounding artefact": (
                "yes" if abs(rounded_sum - round(e["v_grand"], 5)) > 1e-12 else "no"
            ),
        })
    df = pd.DataFrame(rows)
    _save_table(df, "T9_efficiency",
                "T9 — Property 1 (efficiency) verified per dataset, at full "
                "double precision. The final columns exist because summing the "
                "5-decimal rounded per-source values can land 1 ulp away from "
                "the rounded $v(\\mathcal{G})$; where that column reads 'yes' the "
                "discrepancy is DISPLAY ROUNDING, not a violated axiom. The "
                "error bound quoted in the text is read from this table, never "
                "typed by hand.")
    return df


def table4_cost(results: dict) -> pd.DataFrame:
    rows = []
    for name, r in ((k, results[k]) for k in corpus_order(results)):
        t = r["timings_sec"]
        rows.append({
            "Dataset": name,
            "Scorers (train once, s)": f"{t.get('scorers', 0):.2f}",
            "Candidates (s)": f"{t.get('candidates', 0):.2f}",
            "32 coalitions (s)": f"{t.get('game_32_coalitions', 0):.2f}",
            "Total (s)": f"{sum(t.values()):.2f}",
        })
    df = pd.DataFrame(rows)
    _save_table(df, "T4_cost",
                "T4 — Computational cost. The 'laptop CPU, seconds' claim applies "
                "to the Shapley computation (32-coalition sweep and downstream "
                "analysis); base-scorer training is a separate one-time cost.")
    return df


def table5_main_results(results: dict) -> pd.DataFrame:
    rows = []
    for name, r in ((k, results[k]) for k in corpus_order(results)):
        for m, lab in [("uniform", "Uniform fusion"), ("global", "Globally-tuned fusion"),
                       ("popularity_reference", "Popularity (full-catalog ref.)"),
                       ("signalshap_fuse", "SignalShap-Fuse")]:
            fc = r["e4_signalshap_fuse"]["full_catalog"][m]
            rows.append({
                "Dataset": name, "Method": lab,
                "NDCG@10": f"{fc['ndcg_at_10']:.4f}",
                "Recall@20": f"{fc['recall_at_20']:.4f}",
                "MRR@10": f"{fc['mrr_at_10']:.4f}",
            })
    df = pd.DataFrame(rows)
    _save_table(df, "T5_main_results",
                "T5 — Main results. ALL METHODS EVALUATED FULL-CATALOG; "
                "SignalShap-Fuse scores items outside $C_u$ as $-\\infty$, so its "
                "candidate-recall ceiling is included in the reported number. "
                "Note the two-protocol split: $v(S)$ remains fixed-candidate by "
                "definition of the game; only T5 reporting is full-catalog.")
    return df


def table6_loo_vs_shapley(results: dict) -> pd.DataFrame:
    rows = []
    for name, r in ((k, results[k]) for k in corpus_order(results)):
        e2 = r["e2_loo_vs_shapley"]
        ci = r.get("multi_seed", {}).get("ci", {})
        for g in SOURCES:
            c = ci.get(g, {})
            has_ci = bool(c) and c.get("n_seeds", 0) > 1
            mean = c.get("mean", e2["shapley"][g])
            rows.append({
                "Dataset": disp(name), "Source": g,
                "LOO (seed 42)": f"{e2['loo'][g]:.5f}",
                "Shapley (seed 42)": f"{e2['shapley'][g]:.5f}",
                "Shapley (seed mean)": f"{mean:.5f}" if has_ci else "n/a",
                "Seed CI (±1.96 SE)": (
                    f"[{c.get('lo', 0):.5f}, {c.get('hi', 0):.5f}]" if has_ci else "n/a"
                ),
                "Gap (seed 42)": f"{e2['gap'][g]:.5f}",
                "Perm. $p$": f"{e2['permutation_tests'][g]['p_value']:.4f}",
            })
    df = pd.DataFrame(rows)
    _save_table(df, "T6_loo_vs_shapley",
                "T6 — LOO vs Shapley per (dataset, source). TWO BASES ARE "
                "REPORTED SEPARATELY AND MUST NOT BE COMPARED ACROSS COLUMNS: "
                "LOO, Shapley and Gap are single-seed (seed 42) so that the gap "
                "is a like-for-like difference on one fitted game; the seed-mean "
                "and CI columns aggregate over all seeds. They differ because "
                "$v$ is fitted, which is precisely the estimation error the CI "
                "quantifies. Mixing the bases within a row would be an error.")
    return df


def table7_fuse_significance(results: dict) -> pd.DataFrame:
    rows = []
    for name, r in ((k, results[k]) for k in corpus_order(results)):
        e4 = r["e4_signalshap_fuse"]
        holm = e4["holm_bonferroni"]
        for b, t in e4["wilcoxon"].items():
            rows.append({
                "Dataset": name, "Baseline": b,
                "Mean ΔNDCG@10": f"{t['mean_diff']:+.5f}",
                "Wilcoxon $W$": f"{t['statistic']:.1f}",
                "raw $p$": f"{t['p_value']:.4f}",
                "Holm $p$": f"{holm['corrected'].get(b, 1.0):.4f}",
                "Cohen's $d_z$": f"{t['d_z']:+.3f}",
            })
    df = pd.DataFrame(rows)
    fam = next(iter(results.values()))["e4_signalshap_fuse"]["holm_bonferroni"]
    _save_table(df, "T7_fuse_significance",
                f"T7 — SignalShap-Fuse vs baselines. Holm–Bonferroni family size "
                f"$m={fam['family_size']}$, composition = "
                f"{{{', '.join(fam['family_composition'])}}}. Declaring the "
                f"COMPOSITION and not merely the size prevents the family looking "
                f"chosen after the fact.")
    return df


def table8_robustness(results: dict) -> pd.DataFrame:
    rows = []
    for name, r in ((k, results[k]) for k in corpus_order(results)):
        rb = r["e5_robustness"]
        for k, cell in rb["candidate_size"].items():
            rows.append({
                "Dataset": name, "Stress test": f"$|C_u|$ = {cell['n_max']}",
                "Candidate recall": f"{cell['candidate_recall']:.3f}",
                "Top source": max(cell["shapley"], key=cell["shapley"].get),
                "$v(\\mathcal{G})$": f"{cell['v_grand']:.5f}",
            })
        for k, phi in rb["lambda_sensitivity"].items():
            rows.append({
                "Dataset": name, "Stress test": f"$\\lambda$ = {k.split('_')[1]}",
                "Candidate recall": "—", "Top source": max(phi, key=phi.get),
                "$v(\\mathcal{G})$": "—",
            })
        for k, phi in rb["monotone_rescaling"].items():
            rows.append({
                "Dataset": name, "Stress test": f"rescale: {k}",
                "Candidate recall": "—", "Top source": max(phi, key=phi.get),
                "$v(\\mathcal{G})$": "—",
            })
    df = pd.DataFrame(rows)
    _save_table(df, "T8_robustness",
                "T8 — Robustness matrix. CANDIDATE RECALL IS REPORTED PER CELL for "
                "the $|C_u|$ sweep: changing $|C_u|$ moves the recall ceiling and "
                "hence the level of $v$, so without it the cells are not comparable.")
    return df


def generate_all_assets(results: dict, stats: dict) -> dict:
    """Produce F1-F7 and T1-T8 from artefact JSON only."""
    _dirs()
    figs = {
        "F1": fig1_workflow(), "F2": fig2_shapley_shares(results),
        "F3": fig3_loo_vs_shapley(results), "F4": fig4_redundancy_heatmap(results),
        "F5": fig5_segment_radar(results), "F6": fig6_fuse_gain(results),
        "F7": fig7_robustness(results),
    }
    tabs = {
        "T1": table1_positioning(), "T2": table2_datasets(results, stats),
        "T3": table3_notation(), "T4": table4_cost(results),
        "T5": table5_main_results(results), "T6": table6_loo_vs_shapley(results),
        "T7": table7_fuse_significance(results), "T8": table8_robustness(results),
        "T9": table_efficiency(results),
    }
    return {"figures": {k: str(v) for k, v in figs.items()},
            "tables": {k: f"{TAB}/{k}_*.md" for k in tabs}}
