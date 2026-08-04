**T7 — SignalShap-Fuse vs baselines. Holm–Bonferroni family size $m=5$, composition = {uniform, global, popularity_reference, lightgcn, sasrec}. Declaring the COMPOSITION and not merely the size prevents the family looking chosen after the fact.**

| Dataset          | Baseline             |   Mean ΔNDCG@10 |   Wilcoxon $W$ |   raw $p$ |   Holm $p$ |   Cohen's $d_z$ |
|:-----------------|:---------------------|----------------:|---------------:|----------:|-----------:|----------------:|
| amazon_book_lgcn | uniform              |         0.00275 |         2614.5 |    0      |     0      |           0.062 |
| amazon_book_lgcn | global               |         6e-05   |          161   |    0.7123 |     0.7123 |           0.008 |
| amazon_book_lgcn | popularity_reference |         0.01178 |         2044.5 |    0      |     0      |           0.124 |
| amazon_book_lgcn | lightgcn             |         0.00527 |         9263   |    0      |     0      |           0.062 |
| amazon_book_lgcn | sasrec               |         0.01306 |          540.5 |    0      |     0      |           0.14  |
| gowalla          | uniform              |         0.00598 |        14178   |    0      |     0      |           0.087 |
| gowalla          | global               |         0.00018 |          176   |    0.5375 |     1      |           0.019 |
| gowalla          | popularity_reference |         0.03754 |        21834   |    0      |     0      |           0.22  |
| gowalla          | lightgcn             |        -0.00067 |        93401   |    0.7143 |     1      |          -0.005 |
| gowalla          | sasrec               |         0.04194 |        15360.5 |    0      |     0      |           0.234 |
| ml_1m            | uniform              |         0.01178 |       109570   |    0      |     0      |           0.097 |
| ml_1m            | global               |         0.00013 |         5670.5 |    0.5917 |     0.5917 |           0.006 |
| ml_1m            | popularity_reference |         0.04515 |        76692.5 |    0      |     0      |           0.232 |
| ml_1m            | lightgcn             |         0.02948 |       128173   |    0      |     0      |           0.157 |
| ml_1m            | sasrec               |         0.05699 |        24028   |    0      |     0      |           0.3   |
| yelp2018         | uniform              |         0.00114 |        26419.5 |    0      |     0      |           0.038 |
| yelp2018         | global               |        -1e-05   |         2842   |    0.7565 |     0.7565 |          -0.001 |
| yelp2018         | popularity_reference |         0.01601 |        37818.5 |    0      |     0      |           0.146 |
| yelp2018         | lightgcn             |         0.00423 |       202198   |    0      |     0      |           0.041 |
| yelp2018         | sasrec               |         0.01949 |            0   |    0      |     0      |           0.182 |
