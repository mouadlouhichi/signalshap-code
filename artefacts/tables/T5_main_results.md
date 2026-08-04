**T5 — Main results. ALL METHODS EVALUATED FULL-CATALOG; SignalShap-Fuse scores items outside $C_u$ as $-\infty$, so its candidate-recall ceiling is included in the reported number. Note the two-protocol split: $v(S)$ remains fixed-candidate by definition of the game; only T5 reporting is full-catalog.**

| Dataset   | Method                         |   NDCG@10 |   Recall@20 |   MRR@10 |
|:----------|:-------------------------------|----------:|------------:|---------:|
| ml_1m     | Uniform fusion                 |    0.0527 |      0.179  |   0.0365 |
| ml_1m     | Globally-tuned fusion          |    0.0639 |      0.2103 |   0.044  |
| ml_1m     | Popularity (full-catalog ref.) |    0.0183 |      0.0729 |   0.0119 |
| ml_1m     | SignalShap-Fuse                |    0.0638 |      0.2109 |   0.044  |
