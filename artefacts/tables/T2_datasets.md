**T2 — Dataset statistics with the two PRECONDITIONS. Candidate recall is the ceiling on every metric in T5–T7; monotonicity violations determine whether Property 2 applies. Both must be inspected before any attribution number is interpreted. Density is computed as-used, never quoted.**

| Dataset     |   Users |   Items |   Interactions | Density (as used)   |   $N_{max}$ | $|C_u|$ mean±std   |   Candidate recall | Gate (≥0.60)   | Monot. violations   | Prop. 2 applicable   |
|:------------|--------:|--------:|---------------:|:--------------------|------------:|:-------------------|-------------------:|:---------------|:--------------------|:---------------------|
| ml_1m       |     900 |     700 |          28097 | 4.4598%             |          80 | 80.0±0.0           |              0.462 | FAIL           | 14/80               | no                   |
| lastfm_2k   |     700 |    1568 |          11364 | 1.0353%             |         100 | 100.0±0.0          |              0.221 | FAIL           | 24/80               | no                   |
| amazon_book |    1200 |    2564 |          10859 | 0.3529%             |         120 | 120.0±0.0          |              0.117 | FAIL           | 24/80               | no                   |
