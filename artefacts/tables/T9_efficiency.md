**T9 — Property 1 (efficiency) verified per dataset, at full double precision. The final columns exist because summing the 5-decimal rounded per-source values can land 1 ulp away from the rounded $v(\mathcal{G})$; where that column reads 'yes' the discrepancy is DISPLAY ROUNDING, not a violated axiom. The error bound quoted in the text is read from this table, never typed by hand.**

| Dataset      |   $\sum_g \varphi_g$ |   $v(\mathcal{G})$ |   $|$error$|$ | Passes   |   Sum of rounded $\varphi_g$ |   Rounded $v(\mathcal{G})$ | Display-rounding artefact   |
|:-------------|---------------------:|-------------------:|--------------:|:---------|-----------------------------:|---------------------------:|:----------------------------|
| Amazon-Book  |            0.0118195 |          0.0118195 |       1.7e-18 | yes      |                      0.01181 |                    0.01182 | yes                         |
| Gowalla      |            0.0428291 |          0.0428291 |       6.9e-18 | yes      |                      0.04283 |                    0.04283 | no                          |
| MovieLens-1M |            0.0507487 |          0.0507487 |       6.9e-18 | yes      |                      0.05075 |                    0.05075 | no                          |
| Yelp2018     |            0.0173061 |          0.0173061 |       0       | yes      |                      0.01731 |                    0.01731 | no                          |
