**T4 — Computational cost. The 'laptop CPU, seconds' claim applies to the Shapley computation (32-coalition sweep and downstream analysis); base-scorer training is a separate one-time cost.**

| Dataset            |   Scorers (train once, s) |   Candidates (s) |   32 coalitions (s) |   Total (s) |
|:-------------------|--------------------------:|-----------------:|--------------------:|------------:|
| amazon_video_games |                      4.84 |             6.54 |                9.82 |       72.22 |
| gowalla_ts         |                     43.68 |           356.19 |              290.99 |      932.17 |
| ml_1m              |                      6.41 |             5.25 |                8.63 |       76.78 |
