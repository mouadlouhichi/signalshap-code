**T9 — Property 1 (efficiency) verified per dataset, at full double precision. The final columns exist because summing the 5-decimal rounded per-source values can land 1 ulp away from the rounded $v(\mathcal{G})$; where that column reads 'yes' the discrepancy is DISPLAY ROUNDING, not a violated axiom. The error bound quoted in the text is read from this table, never typed by hand.**

| Dataset            |   $\sum_g \varphi_g$ |   $v(\mathcal{G})$ |   $|$error$|$ | Passes   |   Sum of rounded $\varphi_g$ |   Rounded $v(\mathcal{G})$ | Display-rounding artefact   |
|:-------------------|---------------------:|-------------------:|--------------:|:---------|-----------------------------:|---------------------------:|:----------------------------|
| amazon_video_games |            0.0406937 |          0.0406937 |       0       | yes      |                      0.04069 |                    0.04069 | no                          |
| gowalla_ts         |            0.0206932 |          0.0206932 |       0       | yes      |                      0.02071 |                    0.02069 | yes                         |
| MovieLens-1M       |            0.0514955 |          0.0514955 |       6.9e-18 | yes      |                      0.0515  |                    0.0515  | no                          |
