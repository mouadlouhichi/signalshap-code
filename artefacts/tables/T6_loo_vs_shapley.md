**T6 — LOO vs Shapley per (dataset, source). TWO BASES ARE REPORTED SEPARATELY AND MUST NOT BE COMPARED ACROSS COLUMNS: LOO, Shapley and Gap are single-seed (seed 42) so that the gap is a like-for-like difference on one fitted game; the seed-mean and CI columns aggregate over all seeds. They differ because $v$ is fitted, which is precisely the estimation error the CI quantifies. Mixing the bases within a row would be an error.**

| Dataset            | Source   |   LOO (seed 42) |   Shapley (seed 42) |   Shapley (seed mean) | Seed CI (±1.96 SE)   |   Gap (seed 42) |   Perm. $p$ |
|:-------------------|:---------|----------------:|--------------------:|----------------------:|:---------------------|----------------:|------------:|
| amazon_video_games | cf       |         0.00845 |             0.01952 |               0.01983 | [0.01885, 0.02082]   |         0.01107 |      0.0001 |
| amazon_video_games | ct       |         2e-05   |             0.00213 |               0.002   | [0.00142, 0.00258]   |         0.00211 |      0.0001 |
| amazon_video_games | pop      |         0.00308 |             0.00183 |               0.00185 | [0.00155, 0.00215]   |        -0.00125 |      0.0041 |
| amazon_video_games | rec      |         0.00023 |            -0.00021 |              -0.0003  | [-0.00064, 0.00003]  |        -0.00043 |      0.0013 |
| amazon_video_games | seq      |         0.00758 |             0.01935 |               0.01912 | [0.01886, 0.01939]   |         0.01178 |      0.0001 |
| gowalla_ts         | cf       |         0.00729 |             0.00712 |               0.00724 | [0.00703, 0.00744]   |        -0.00017 |      0.8323 |
| gowalla_ts         | ct       |         0.00528 |             0.00675 |               0.00672 | [0.00663, 0.00681]   |         0.00147 |      0.0343 |
| gowalla_ts         | pop      |        -0.00151 |             0.00057 |               0.00048 | [0.00039, 0.00057]   |         0.00207 |      0.0001 |
| gowalla_ts         | rec      |         1e-05   |             0.00039 |               0.00039 | [0.00038, 0.00039]   |         0.00038 |      0.0001 |
| gowalla_ts         | seq      |         0.0007  |             0.00214 |               0.00226 | [0.00214, 0.00238]   |         0.00144 |      0.0001 |
| MovieLens-1M       | cf       |        -0.00501 |             0.01547 |               0.01573 | [0.01542, 0.01604]   |         0.02048 |      0.0001 |
| MovieLens-1M       | ct       |         0.00083 |             8e-05   |              -6e-05   | [-0.00020, 0.00008]  |        -0.00075 |      0.0048 |
| MovieLens-1M       | pop      |         0.00098 |             0.00664 |               0.00651 | [0.00638, 0.00664]   |         0.00565 |      0.0001 |
| MovieLens-1M       | rec      |         0.00044 |             0.00071 |               0.00053 | [0.00028, 0.00079]   |         0.00027 |      0.2809 |
| MovieLens-1M       | seq      |         0.01673 |             0.02964 |               0.02986 | [0.02953, 0.03019]   |         0.0129  |      0.0001 |
