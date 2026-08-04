**T2 — Dataset statistics with the two PRECONDITIONS. Candidate recall is the ceiling on every metric in T5–T7; monotonicity violations determine whether Property 2 applies. Both must be inspected before any attribution number is interpreted. Density is computed as-used, never quoted.**

| Dataset          |   Users |   Items |   Interactions | Density (as used)   |   $N_{max}$ | $|C_u|$ mean±std   |   Candidate recall | Gate (≥0.60)   | Monot. violations   | Prop. 2 applicable   |
|:-----------------|--------:|--------:|---------------:|:--------------------|------------:|:-------------------|-------------------:|:---------------|:--------------------|:---------------------|
| amazon_book_lgcn |    7422 |   84348 |         342709 | 0.0547%             |        5000 | 5000.0±0.0         |              0.529 | FAIL           | 10/80               | no                   |
| gowalla          |    5797 |   39005 |         162573 | 0.0719%             |        2500 | 2500.0±0.0         |              0.678 | PASS           | 10/80               | no                   |
| ml_1m            |    6038 |    3533 |         575276 | 2.6967%             |         600 | 600.0±0.1          |              0.748 | PASS           | 26/80               | no                   |
| yelp2018         |   19018 |   38048 |         756903 | 0.1046%             |        5000 | 5000.0±0.2         |              0.818 | PASS           | 0/80                | yes                  |
