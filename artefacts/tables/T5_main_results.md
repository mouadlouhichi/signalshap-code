**T5 — Main results. ALL METHODS EVALUATED FULL-CATALOG; SignalShap-Fuse scores items outside $C_u$ as $-\infty$, so its candidate-recall ceiling is included in the reported number. Note the two-protocol split: $v(S)$ remains fixed-candidate by definition of the game; only T5 reporting is full-catalog.**

| Dataset          | Method                         |   NDCG@10 |   Recall@20 |   MRR@10 |
|:-----------------|:-------------------------------|----------:|------------:|---------:|
| ml_1m            | Uniform fusion                 |    0.0517 |      0.1768 |   0.0358 |
| ml_1m            | Globally-tuned fusion          |    0.0633 |      0.2104 |   0.0437 |
| ml_1m            | Popularity (full-catalog ref.) |    0.0183 |      0.0729 |   0.0119 |
| ml_1m            | SignalShap-Fuse                |    0.0634 |      0.2109 |   0.0437 |
| yelp2018         | Uniform fusion                 |    0.0184 |      0.062  |   0.0127 |
| yelp2018         | Globally-tuned fusion          |    0.0195 |      0.0656 |   0.0136 |
| yelp2018         | Popularity (full-catalog ref.) |    0.0035 |      0.0133 |   0.0024 |
| yelp2018         | SignalShap-Fuse                |    0.0195 |      0.0658 |   0.0136 |
| gowalla          | Uniform fusion                 |    0.0444 |      0.1173 |   0.0336 |
| gowalla          | Globally-tuned fusion          |    0.0502 |      0.1337 |   0.0377 |
| gowalla          | Popularity (full-catalog ref.) |    0.0128 |      0.0366 |   0.0087 |
| gowalla          | SignalShap-Fuse                |    0.0504 |      0.134  |   0.0377 |
| amazon_book_lgcn | Uniform fusion                 |    0.0111 |      0.0341 |   0.0081 |
| amazon_book_lgcn | Globally-tuned fusion          |    0.0138 |      0.0434 |   0.01   |
| amazon_book_lgcn | Popularity (full-catalog ref.) |    0.002  |      0.0062 |   0.0015 |
| amazon_book_lgcn | SignalShap-Fuse                |    0.0138 |      0.0432 |   0.01   |
