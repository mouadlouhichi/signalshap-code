**T5 — Main results. ALL METHODS EVALUATED FULL-CATALOG; SignalShap-Fuse scores items outside $C_u$ as $-\infty$, so its candidate-recall ceiling is included in the reported number. Note the two-protocol split: $v(S)$ remains fixed-candidate by definition of the game; only T5 reporting is full-catalog.**

| Dataset   | Method                         |   NDCG@10 |   Recall@20 |   MRR@10 |
|:----------|:-------------------------------|----------:|------------:|---------:|
| ml_1m     | Uniform fusion                 |    0.0517 |      0.1768 |   0.0358 |
| ml_1m     | Globally-tuned fusion          |    0.0633 |      0.2104 |   0.0437 |
| ml_1m     | Popularity (full-catalog ref.) |    0.0183 |      0.0729 |   0.0119 |
| ml_1m     | SignalShap-Fuse                |    0.0634 |      0.2109 |   0.0437 |
