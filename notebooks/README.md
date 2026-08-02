# Notebooks

| Notebook | Purpose |
|---|---|
| `SignalShap_M4_FullStudy.ipynb` | **Full study on Apple Silicon (M4, 48 GB).** Four real corpora, memory-auto-sized, complete suite + paper assets. Start here. |
| `SignalShap_Reproduction.ipynb` | Original walkthrough, small scale, works anywhere (falls back to synthetic without raw data). |

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
