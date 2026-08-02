**T4 — Computational cost. The 'laptop CPU, seconds' claim applies to the Shapley computation (32-coalition sweep and downstream analysis); base-scorer training is a separate one-time cost.**

| Dataset     |   Scorers (train once, s) |   Candidates (s) |   32 coalitions (s) |   Total (s) |
|:------------|--------------------------:|-----------------:|--------------------:|------------:|
| amazon_book |                      3.95 |             4.41 |                5.96 |       14.54 |
| lastfm_2k   |                      2.59 |             0.97 |                1.53 |        5.22 |
| ml_1m       |                     16.22 |             8.12 |               16.59 |       44.64 |
