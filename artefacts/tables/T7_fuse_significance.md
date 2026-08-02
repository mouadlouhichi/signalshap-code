**T7 — SignalShap-Fuse vs baselines. Holm–Bonferroni family size $m=3$, composition = {uniform, global, popularity_reference}. Declaring the COMPOSITION and not merely the size prevents the family looking chosen after the fact.**

| Dataset   | Baseline             |   Mean ΔNDCG@10 |   Wilcoxon $W$ |   raw $p$ |   Holm $p$ |   Cohen's $d_z$ |
|:----------|:---------------------|----------------:|---------------:|----------:|-----------:|----------------:|
| ml_1m     | uniform              |         0.01131 |         116605 |    0      |     0      |           0.093 |
| ml_1m     | global               |         0.00025 |           6959 |    0.1434 |     0.1434 |           0.01  |
| ml_1m     | popularity_reference |         0.04562 |          78276 |    0      |     0      |           0.234 |
