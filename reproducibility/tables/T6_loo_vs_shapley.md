**T6 — LOO vs Shapley per (dataset, source). TWO BASES ARE REPORTED SEPARATELY AND MUST NOT BE COMPARED ACROSS COLUMNS: LOO, Shapley and Gap are single-seed (seed 42) so that the gap is a like-for-like difference on one fitted game; the seed-mean and CI columns aggregate over all seeds. They differ because $v$ is fitted, which is precisely the estimation error the CI quantifies. Mixing the bases within a row would be an error.**

| Dataset      | Source   |   LOO (seed 42) |   Shapley (seed 42) |   Shapley (seed mean) | Seed CI (±1.96 SE)   |   Gap (seed 42) |   Perm. $p$ |
|:-------------|:---------|----------------:|--------------------:|----------------------:|:---------------------|----------------:|------------:|
| MovieLens-1M | cf       |        -0.0048  |             0.01538 |               0.01578 | [0.01531, 0.01626]   |         0.02018 |      0.0001 |
| MovieLens-1M | ct       |         0.00115 |             2e-05   |              -3e-05   | [-0.00010, 0.00004]  |        -0.00112 |      0.0001 |
| MovieLens-1M | pop      |         0.0012  |             0.00648 |               0.0065  | [0.00647, 0.00654]   |         0.00528 |      0.0001 |
| MovieLens-1M | rec      |         0.00033 |             0.00053 |               0.00038 | [0.00013, 0.00062]   |         0.0002  |      0.375  |
| MovieLens-1M | seq      |         0.01672 |             0.02927 |               0.02982 | [0.02922, 0.03041]   |         0.01255 |      0.0001 |
| Amazon-VG    | cf       |         0.00844 |             0.01925 |               0.01965 | [0.01889, 0.02042]   |         0.01081 |      0.0001 |
| Amazon-VG    | ct       |         2e-05   |             0.00187 |               0.00181 | [0.00153, 0.00210]   |         0.00185 |      0.0001 |
| Amazon-VG    | pop      |         0.00308 |             0.00157 |               0.00167 | [0.00157, 0.00177]   |        -0.00151 |      0.0003 |
| Amazon-VG    | rec      |         0.00017 |            -0.00048 |              -0.0005  | [-0.00054, -0.00046] |        -0.00066 |      0.0001 |
| Amazon-VG    | seq      |         0.00762 |             0.0191  |               0.01894 | [0.01873, 0.01915]   |         0.01148 |      0.0001 |
| Gowalla      | cf       |         0.00729 |             0.00711 |               0.00724 | [0.00703, 0.00745]   |        -0.00018 |      0.821  |
| Gowalla      | ct       |         0.00528 |             0.00674 |               0.00672 | [0.00664, 0.00681]   |         0.00146 |      0.036  |
| Gowalla      | pop      |        -0.00151 |             0.00055 |               0.00049 | [0.00041, 0.00056]   |         0.00206 |      0.0001 |
| Gowalla      | rec      |         1e-05   |             0.00038 |               0.00039 | [0.00037, 0.00041]   |         0.00037 |      0.0001 |
| Gowalla      | seq      |         0.0007  |             0.00213 |               0.00226 | [0.00213, 0.00240]   |         0.00143 |      0.0001 |
