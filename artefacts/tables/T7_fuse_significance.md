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
| ml_1m              | uniform              |         0.01201 |       109564   |    0      |     0      |           0.098 |
| ml_1m              | global               |         3e-05   |         3063.5 |    0.7701 |     0.7701 |           0.001 |
| ml_1m              | popularity_reference |         0.04498 |        77229.5 |    0      |     0      |           0.231 |
| ml_1m              | lightgcn             |         0.02931 |       127792   |    0      |     0      |           0.156 |
| ml_1m              | sasrec               |         0.04616 |        63732   |    0      |     0      |           0.243 |
