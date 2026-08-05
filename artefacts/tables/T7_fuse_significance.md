**T7 — SignalShap-Fuse vs baselines. Holm–Bonferroni family size $m=5$, composition = {uniform, global, popularity_reference, lightgcn, sasrec}. Declaring the COMPOSITION and not merely the size prevents the family looking chosen after the fact.**

| Dataset            | Baseline             |   Mean ΔNDCG@10 |   Wilcoxon $W$ |   raw $p$ |   Holm $p$ |   Cohen's $d_z$ |
|:-------------------|:---------------------|----------------:|---------------:|----------:|-----------:|----------------:|
| amazon_video_games | uniform              |         0.00615 |        52027.5 |    0      |     0      |           0.076 |
| amazon_video_games | global               |         0.00035 |         5686.5 |    0.0188 |     0.0188 |           0.014 |
| amazon_video_games | popularity_reference |         0.04358 |        15979   |    0      |     0      |           0.25  |
| amazon_video_games | lightgcn             |         0.01483 |        97793   |    0      |     0      |           0.096 |
| amazon_video_games | sasrec               |         0.03487 |        44788.5 |    0      |     0      |           0.199 |
| gowalla_ts         | uniform              |         0.00079 |        11217.5 |    0.0146 |     0.0293 |           0.018 |
| gowalla_ts         | global               |         9e-05   |          521.5 |    0.4946 |     0.4946 |           0.007 |
| gowalla_ts         | popularity_reference |         0.01387 |         5783   |    0      |     0      |           0.142 |
| gowalla_ts         | lightgcn             |         0.00412 |        27313   |    0.0001 |     0.0002 |           0.043 |
| gowalla_ts         | sasrec               |         0.01411 |         6363   |    0      |     0      |           0.137 |
| ml_1m              | uniform              |         0.01114 |       114382   |    0      |     0      |           0.092 |
| ml_1m              | global               |        -5e-05   |         5000.5 |    0.9918 |     0.9918 |          -0.003 |
| ml_1m              | popularity_reference |         0.04553 |        78179   |    0      |     0      |           0.233 |
| ml_1m              | lightgcn             |         0.02986 |       130108   |    0      |     0      |           0.159 |
| ml_1m              | sasrec               |         0.05577 |        36833   |    0      |     0      |           0.286 |
