**T5 — Main results. ALL METHODS EVALUATED FULL-CATALOG; SignalShap-Fuse scores items outside $C_u$ as $-\infty$, so its candidate-recall ceiling is included in the reported number. Note the two-protocol split: $v(S)$ remains fixed-candidate by definition of the game; only T5 reporting is full-catalog.**

| Dataset     | Method                         |   NDCG@10 |   Recall@20 |   MRR@10 |
|:------------|:-------------------------------|----------:|------------:|---------:|
| amazon_book | Uniform fusion                 |    0.0076 |      0.0208 |   0.0059 |
| amazon_book | Globally-tuned fusion          |    0.0291 |      0.0792 |   0.02   |
| amazon_book | Popularity (full-catalog ref.) |    0.0287 |      0.0817 |   0.0197 |
| amazon_book | SignalShap-Fuse                |    0.0291 |      0.0792 |   0.02   |
| lastfm_2k   | Uniform fusion                 |    0.0247 |      0.07   |   0.018  |
| lastfm_2k   | Globally-tuned fusion          |    0.0293 |      0.1543 |   0.0163 |
| lastfm_2k   | Popularity (full-catalog ref.) |    0.0199 |      0.15   |   0.0099 |
| lastfm_2k   | SignalShap-Fuse                |    0.0293 |      0.1543 |   0.0163 |
| ml_1m       | Uniform fusion                 |    0.0919 |      0.27   |   0.0646 |
| ml_1m       | Globally-tuned fusion          |    0.1754 |      0.4033 |   0.1324 |
| ml_1m       | Popularity (full-catalog ref.) |    0.1001 |      0.2622 |   0.0626 |
| ml_1m       | SignalShap-Fuse                |    0.1752 |      0.4022 |   0.1312 |
