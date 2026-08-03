**T7 — SignalShap-Fuse vs baselines. Holm–Bonferroni family size $m=5$, composition = {uniform, global, popularity_reference, lightgcn, sasrec}. Declaring the COMPOSITION and not merely the size prevents the family looking chosen after the fact.**

| Dataset   | Baseline             |   Mean ΔNDCG@10 |   Wilcoxon $W$ |   raw $p$ |   Holm $p$ |   Cohen's $d_z$ |
|:----------|:---------------------|----------------:|---------------:|----------:|-----------:|----------------:|
| ml_1m     | uniform              |         0.01178 |       109570   |    0      |     0      |           0.097 |
| ml_1m     | global               |         0.00013 |         5670.5 |    0.5917 |     0.5917 |           0.006 |
| ml_1m     | popularity_reference |         0.04515 |        76692.5 |    0      |     0      |           0.232 |
| ml_1m     | lightgcn             |         0.02948 |       128173   |    0      |     0      |           0.157 |
| ml_1m     | sasrec               |         0.05699 |        24028   |    0      |     0      |           0.3   |
