**T4 — Computational cost. The 'laptop CPU, seconds' claim applies to the Shapley computation (32-coalition sweep and downstream analysis); base-scorer training is a separate one-time cost.**

| Dataset     |   Scorers (train once, s) |   Candidates (s) |   32 coalitions (s) |   Total (s) |
|:------------|--------------------------:|-----------------:|--------------------:|------------:|
| ml_1m       |                      1.94 |             0.26 |                0.63 |        2.99 |
| lastfm_2k   |                      2.51 |             0.24 |                0.52 |        3.37 |
| amazon_book |                      3.93 |             0.44 |                1.03 |        5.59 |
