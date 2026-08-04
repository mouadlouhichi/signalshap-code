**T6 — LOO vs Shapley per (dataset, source). TWO BASES ARE REPORTED SEPARATELY AND MUST NOT BE COMPARED ACROSS COLUMNS: LOO, Shapley and Gap are single-seed (seed 42) so that the gap is a like-for-like difference on one fitted game; the seed-mean and CI columns aggregate over all seeds. They differ because $v$ is fitted, which is precisely the estimation error the CI quantifies. Mixing the bases within a row would be an error.**

| Dataset      | Source   |   LOO (seed 42) |   Shapley (seed 42) |   Shapley (seed mean) | Seed CI (±1.96 SE)   |   Gap (seed 42) |   Perm. $p$ |
|:-------------|:---------|----------------:|--------------------:|----------------------:|:---------------------|----------------:|------------:|
| MovieLens-1M | cf       |        -0.00501 |             0.01547 |               0.01573 | [0.01542, 0.01604]   |         0.02048 |      0.0001 |
| MovieLens-1M | ct       |         0.00083 |             8e-05   |              -6e-05   | [-0.00020, 0.00008]  |        -0.00075 |      0.0048 |
| MovieLens-1M | pop      |         0.00098 |             0.00664 |               0.00651 | [0.00638, 0.00664]   |         0.00565 |      0.0001 |
| MovieLens-1M | rec      |         0.00044 |             0.00071 |               0.00053 | [0.00028, 0.00079]   |         0.00027 |      0.2809 |
| MovieLens-1M | seq      |         0.01673 |             0.02964 |               0.02986 | [0.02953, 0.03019]   |         0.0129  |      0.0001 |
