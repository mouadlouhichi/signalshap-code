# Notebooks

| Notebook | Purpose |
|---|---|
| `SignalShap_Semivalues_Gowalla.ipynb` | **The current one.** The single run still worth doing before submission: semivalues on Gowalla, closing review item H14/#4. Tens of minutes. |
| `SignalShap_Round8_Runs.ipynb` | Every review-round-8 run, in cost order, resumable. Completed; kept for provenance. |
| `SignalShap_M4_FullStudy.ipynb` | Earlier full-study notebook on Apple Silicon. See the warning below before running it. |
| `SignalShap_Reproduction.ipynb` | Original walkthrough, small scale, works anywhere (falls back to synthetic without raw data). |

## Which notebook produces the paper's numbers

`SignalShap_Round8_Runs.ipynb`, and only that one.

`SignalShap_M4_FullStudy.ipynb` runs `yelp2018`, `gowalla` and
`amazon_book_lgcn`: the untimestamped LightGCN benchmark splits. Those are
**not** the corpora this paper reports, which are `ml_1m`,
`amazon_video_games` and `gowalla_ts`. Three of the five players (`rec`,
`seq`, and the decay term of `pop`) need real interaction timestamps, and the
LightGCN splits discard them. Running the M4 notebook will happily produce
artefacts; they will describe different datasets. It is retained because its
memory-sizing walkthrough is still useful, not because it reproduces the
manuscript.

## Running the round-8 notebook

```bash
cd ~/signalshap-code
bash scripts/fetch_benchmarks.sh      # ml-1m, from GroupLens
bash scripts/fetch_timestamped.sh     # gowalla_ts, amazon_video_games
jupyter lab notebooks/SignalShap_Round8_Runs.ipynb
```

Leave `BUDGET_GB` at 24. The reported corpus shapes were produced at that
budget, and `check_paper_shape` refuses to overwrite the paper's artefacts if
a different budget yields a different shape, because a different budget
silently means a different Gowalla.

Prefer a shell? The identical sequence is:

```bash
bash scripts/run_round8_remaining.sh 24
```

The notebook is **generated** by `scripts/make_round8_notebook.py`, and
`tests/test_round8_notebook.py` asserts the committed file matches. If you
edit it in Jupyter, port the change into the generator and re-run it, or CI
will fail.

## Running the M4 notebook

```bash
git clone https://github.com/mouadlouhichi/signalshap-code.git ~/signalshap-code
cd ~/signalshap-code && bash scripts/fetch_benchmarks.sh
pip install -r requirements.txt jupyterlab
jupyter lab notebooks/SignalShap_M4_FullStudy.ipynb
```

### The one knob

`SCORE_BUDGET_GB` (cell 2) caps how much RAM the five dense score matrices may use.
Users per corpus are derived from it rather than guessed:

```
max_users = budget / (5 * n_items * 4 bytes)
```

At the 16 GB default on a 48 GB machine:

| Corpus | Items | Users | Coverage |
|---|---|---|---|
| MovieLens-1M | 3,533 | 6,038 | **full** |
| Yelp2018 | 38,048 | 21,026 | 66% |
| Gowalla | 40,981 | 19,521 | 65% |
| Amazon-Book | 91,599 | 8,733 | 17% |

Amazon-Book at full size needs **96 GB** for the score matrices alone, so subsampling is
unavoidable there and is disclosed in the paper rather than hidden.

Raise the budget if you have headroom; lower it if you hit swap. Results are checkpointed
per corpus, so an interrupted run resumes without repeating finished work.

### Runtime

~45–90 min for all four corpora. The E9 intervention (§5) runs first because it carries the
paper's central claim — if you only have time for one section, run that.

### Notes

- CPU-only throughout; no CUDA, no MPS. NumPy/SciPy pip wheels link against Accelerate on
  M-series and are already well optimised.
- Use a native arm64 Python. Under Rosetta everything works but is markedly slower.
- If a corpus OOMs, lower `SCORE_BUDGET_GB` and re-run that cell only.
