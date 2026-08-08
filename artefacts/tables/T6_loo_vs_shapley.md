**T6 — LOO vs Shapley per (dataset, source). TWO BASES ARE REPORTED SEPARATELY AND MUST NOT BE COMPARED ACROSS COLUMNS: LOO, Shapley and Gap are single-seed (seed 42) so that the gap is a like-for-like difference on one fitted game; the seed-mean and CI columns aggregate over all seeds. They differ because $v$ is fitted, which is precisely the estimation error the CI quantifies. Mixing the bases within a row would be an error.**

| Dataset      | Source   |   LOO (seed 42) |   Shapley (seed 42) |   Shapley (seed mean) | Seed CI (±1.96 SE)   |   Gap (seed 42) |   Perm. $p$ |
|:-------------|:---------|----------------:|--------------------:|----------------------:|:---------------------|----------------:|------------:|
| Amazon-VG    | cf       |         0.00845 |             0.01982 |               0.0202  | [0.01947, 0.02093]   |         0.01137 |      0.0001 |
| Amazon-VG    | ct       |         2e-05   |             0.00243 |               0.00236 | [0.00210, 0.00263]   |         0.00241 |      0.0001 |
| Amazon-VG    | pop      |         0.00308 |             0.00213 |               0.00221 | [0.00213, 0.00229]   |        -0.00095 |      0.0274 |
| Amazon-VG    | rec      |         0.00023 |             9e-05   |               6e-05   | [0.00002, 0.00010]   |        -0.00013 |      0.082  |
| Amazon-VG    | seq      |         0.00758 |             0.01965 |               0.01948 | [0.01925, 0.01972]   |         0.01208 |      0.0001 |
| Gowalla      | cf       |         0.00729 |             0.00709 |               0.00722 | [0.00701, 0.00743]   |        -0.0002  |      0.8062 |
| Gowalla      | ct       |         0.00528 |             0.00672 |               0.0067  | [0.00661, 0.00679]   |         0.00144 |      0.0375 |
| Gowalla      | pop      |        -0.00151 |             0.00054 |               0.00046 | [0.00038, 0.00054]   |         0.00204 |      0.0001 |
| Gowalla      | rec      |         1e-05   |             0.00036 |               0.00037 | [0.00036, 0.00038]   |         0.00035 |      0.0001 |
| Gowalla      | seq      |         0.0007  |             0.00211 |               0.00224 | [0.00211, 0.00237]   |         0.00141 |      0.0001 |
| MovieLens-1M | cf       |        -0.00519 |             0.0156  |               0.01591 | [0.01549, 0.01632]   |         0.02079 |      0.0001 |
| MovieLens-1M | ct       |         0.00044 |             6e-05   |               1e-05   | [-0.00010, 0.00011]  |        -0.00038 |      0.1193 |
| MovieLens-1M | pop      |         0.00065 |             0.00652 |               0.00658 | [0.00649, 0.00667]   |         0.00587 |      0.0001 |
| MovieLens-1M | rec      |        -5e-05   |             0.00041 |               0.00039 | [0.00014, 0.00064]   |         0.00046 |      0.0369 |
| MovieLens-1M | seq      |         0.01635 |             0.02952 |               0.0299  | [0.02944, 0.03037]   |         0.01317 |      0.0001 |
