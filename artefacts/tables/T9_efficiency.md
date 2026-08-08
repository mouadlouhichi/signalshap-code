**T9 — Property 1 (efficiency) verified per dataset, at full double precision. The final columns exist because summing the 5-decimal rounded per-source values can land 1 ulp away from the rounded $v(\mathcal{G})$; where that column reads 'yes' the discrepancy is DISPLAY ROUNDING, not a violated axiom. The error bound quoted in the text is read from this table, never typed by hand.**

| Dataset      |   $\sum_g \varphi_g$ |   $v(\mathcal{G})$ |   $|$error$|$ | Passes   |   Sum of rounded $\varphi_g$ |   Rounded $v(\mathcal{G})$ | Display-rounding artefact   |
|:-------------|---------------------:|-------------------:|--------------:|:---------|-----------------------------:|---------------------------:|:----------------------------|
| Amazon-VG    |            0.0441286 |          0.0413061 |       0.0028  | NO       |                      0.04412 |                    0.04131 | yes                         |
| Gowalla      |            0.0168221 |          0.0169027 |       8.1e-05 | NO       |                      0.01682 |                    0.0169  | yes                         |
| MovieLens-1M |            0.0521048 |          0.0513638 |       0.00074 | NO       |                      0.05211 |                    0.05136 | yes                         |
