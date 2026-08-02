**T2 — Dataset statistics with the two PRECONDITIONS. Candidate recall is the ceiling on every metric in T5–T7; monotonicity violations determine whether Property 2 applies. Both must be inspected before any attribution number is interpreted. Density is computed as-used, never quoted.**

| Dataset     |   Users |   Items |   Interactions | Density (as used)   |   $N_{max}$ | $|C_u|$ mean±std   |   Candidate recall | Gate (≥0.60)   | Monot. violations   | Prop. 2 applicable   |
|:------------|--------:|--------:|---------------:|:--------------------|------------:|:-------------------|-------------------:|:---------------|:--------------------|:---------------------|
| amazon_book |     nan |     nan |            nan | 0.0000%             |        1000 | 999.8±0.8          |              0.402 | FAIL           | 29/80               | no                   |
| lastfm_2k   |     nan |     nan |            nan | 0.0000%             |         500 | 500.0±0.1          |              0.504 | FAIL           | 19/80               | no                   |
| ml_1m       |    6038 |    3533 |         575276 | 2.6967%             |         600 | 600.0±0.1          |              0.747 | PASS           | 20/80               | no                   |
