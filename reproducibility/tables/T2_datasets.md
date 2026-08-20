**T2 — Dataset statistics with the two PRECONDITIONS. Candidate recall is the ceiling on every metric in T5–T7; monotonicity violations determine whether Property 2 applies. Both must be inspected before any attribution number is interpreted. Density is computed as-used, never quoted.**

| Dataset      |   Users |   Items |   Interactions | Density (as used)   |   $N_{max}$ | $|C_u|$ mean±std   |   Candidate recall | Gate (≥0.60)   | Monot. violations   | Prop. 2 applicable   |
|:-------------|--------:|--------:|---------------:|:--------------------|------------:|:-------------------|-------------------:|:---------------|:--------------------|:---------------------|
| MovieLens-1M |    6038 |    3533 |         575276 | 2.6967%             |         600 | 600.0±0.1          |              0.748 | PASS           | 26/80               | no                   |
| Amazon-VG    |    7120 |    3516 |         117468 | 0.4692%             |         600 | 600.0±0.1          |              0.589 | FAIL           | 14/80               | no                   |
| Gowalla      |    8865 |   82134 |         542970 | 0.0746%             |       11623 | 11619.3±10.4       |              0.45  | FAIL           | 13/80               | no                   |
