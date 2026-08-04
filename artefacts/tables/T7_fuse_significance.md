**T7 — SignalShap-Fuse vs baselines. Holm–Bonferroni family size $m=5$, composition = {uniform, global, popularity_reference, lightgcn, sasrec}. Declaring the COMPOSITION and not merely the size prevents the family looking chosen after the fact.**

| Dataset   | Baseline             |   Mean ΔNDCG@10 |   Wilcoxon $W$ |   raw $p$ |   Holm $p$ |   Cohen's $d_z$ |
|:----------|:---------------------|----------------:|---------------:|----------:|-----------:|----------------:|
| ml_1m     | uniform              |         0.01114 |       114382   |    0      |     0      |           0.092 |
| ml_1m     | global               |        -5e-05   |         5000.5 |    0.9918 |     0.9918 |          -0.003 |
| ml_1m     | popularity_reference |         0.04553 |        78179   |    0      |     0      |           0.233 |
| ml_1m     | lightgcn             |         0.02986 |       130108   |    0      |     0      |           0.159 |
| ml_1m     | sasrec               |         0.05577 |        36833   |    0      |     0      |           0.286 |
