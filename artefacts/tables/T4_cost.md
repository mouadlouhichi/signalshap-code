**T4 — Computational cost. The 'laptop CPU, seconds' claim applies to the Shapley computation (32-coalition sweep and downstream analysis); base-scorer training is a separate one-time cost.**

| Dataset            |   Scorers (train once, s) |   Candidates (s) |   32 coalitions (s) |   Total (s) |
|:-------------------|--------------------------:|-----------------:|--------------------:|------------:|
| amazon_video_games |                      4.92 |             6.65 |               11.61 |       75.2  |
| gowalla_ts         |                     34.09 |           256.3  |              227.48 |      661.79 |
| ml_1m              |                     16.53 |             8.22 |               16.74 |      195.24 |
