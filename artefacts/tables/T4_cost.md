**T4 — Computational cost. The 'laptop CPU, seconds' claim applies to the Shapley computation (32-coalition sweep and downstream analysis); base-scorer training is a separate one-time cost.**

| Dataset            |   Scorers (train once, s) |   Candidates (s) |   32 coalitions (s) |   Total (s) |
|:-------------------|--------------------------:|-----------------:|--------------------:|------------:|
| amazon_video_games |                      7.38 |             9.67 |               10.24 |      111.77 |
| gowalla_ts         |                     57.67 |           554.02 |              386.98 |     1453.78 |
| ml_1m              |                      9.06 |             9.7  |               16.31 |      156.2  |
