**T2 — Dataset statistics with the two PRECONDITIONS. Candidate recall is the ceiling on every metric in T5–T7; monotonicity violations determine whether Property 2 applies. Both must be inspected before any attribution number is interpreted. Density is computed as-used, never quoted.**

| Dataset          |   Users |   Items |   Interactions | Density (as used)   |   $N_{max}$ | $|C_u|$ mean±std   |   Candidate recall | Gate (≥0.60)   | Monot. violations   | Prop. 2 applicable   |
|:-----------------|--------:|--------:|---------------:|:--------------------|------------:|:-------------------|-------------------:|:---------------|:--------------------|:---------------------|
| ml_1m            |    6038 |    3533 |         575276 | 2.6967%             |         600 | 600.0±0.1          |              0.748 | PASS           | 26/80               | no                   |
| yelp2018         |   21026 |   38048 |         839455 | 0.1049%             |        5000 | 5000.0±0.2         |              0.818 | PASS           | 0/80                | yes                  |
| gowalla          |   19521 |   40981 |         549280 | 0.0687%             |        2500 | 2500.0±0.0         |              0.678 | PASS           | 10/80               | no                   |
| amazon_book_lgcn |    8733 |   86537 |         398784 | 0.0528%             |        5000 | 5000.0±0.0         |              0.529 | FAIL           | 10/80               | no                   |
