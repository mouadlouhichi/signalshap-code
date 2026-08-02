**T5 — Main results. ALL METHODS EVALUATED FULL-CATALOG; SignalShap-Fuse scores items outside $C_u$ as $-\infty$, so its candidate-recall ceiling is included in the reported number. Note the two-protocol split: $v(S)$ remains fixed-candidate by definition of the game; only T5 reporting is full-catalog.**

| Dataset   | Method                         |   NDCG@10 |   Recall@20 |   MRR@10 |
|:----------|:-------------------------------|----------:|------------:|---------:|
| ml_1m     | Uniform fusion                 |    0.0526 |      0.1773 |   0.0362 |
| ml_1m     | Globally-tuned fusion          |    0.0637 |      0.2108 |   0.0438 |
| ml_1m     | Popularity (full-catalog ref.) |    0.0183 |      0.0729 |   0.0119 |
| ml_1m     | SignalShap-Fuse                |    0.0639 |      0.2116 |   0.044  |
