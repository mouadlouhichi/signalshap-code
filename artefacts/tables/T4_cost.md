**T4 — Computational cost. The 'laptop CPU, seconds' claim applies to the Shapley computation (32-coalition sweep and downstream analysis); base-scorer training is a separate one-time cost.**

| Dataset            |   Scorers (train once, s) |   Candidates (s) |   32 coalitions (s) |   Total (s) |
|:-------------------|--------------------------:|-----------------:|--------------------:|------------:|
| amazon_video_games |                      5.03 |             6.74 |                9.68 |       70.63 |
| gowalla_ts         |                     43.18 |           370.49 |              284.64 |      942.89 |
| ml_1m              |                     16.91 |             8.39 |               13.23 |      163.29 |
