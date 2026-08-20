**T4 — Computational cost. The 'laptop CPU, seconds' claim applies to the Shapley computation (32-coalition sweep and downstream analysis); base-scorer training is a separate one-time cost.**

| Dataset            |   Scorers (train once, s) |   Candidates (s) |   32 coalitions (s) |   Total (s) |
|:-------------------|--------------------------:|-----------------:|--------------------:|------------:|
| ml_1m              |                      8.77 |             7.87 |               11.1  |      110.27 |
| amazon_video_games |                      6.7  |             9.37 |               12.28 |      116.45 |
| gowalla_ts         |                     57.67 |           554.02 |              386.98 |     1453.78 |
