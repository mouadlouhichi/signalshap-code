**T8 — Robustness matrix. CANDIDATE RECALL IS REPORTED PER CELL for the $|C_u|$ sweep: changing $|C_u|$ moves the recall ceiling and hence the level of $v$, so without it the cells are not comparable.**

| Dataset     | Stress test       | Candidate recall   | Top source   | $v(\mathcal{G})$   |
|:------------|:------------------|:-------------------|:-------------|:-------------------|
| ml_1m       | $|C_u|$ = 40      | 0.346              | seq          | 0.13366            |
| ml_1m       | $|C_u|$ = 80      | 0.462              | seq          | 0.13514            |
| ml_1m       | $|C_u|$ = 160     | 0.642              | seq          | 0.13958            |
| ml_1m       | $\lambda$ = 0.1   | —                  | seq          | —                  |
| ml_1m       | $\lambda$ = 1.0   | —                  | seq          | —                  |
| ml_1m       | $\lambda$ = 10.0  | —                  | seq          | —                  |
| ml_1m       | rescale: identity | —                  | seq          | —                  |
| ml_1m       | rescale: log1p    | —                  | seq          | —                  |
| ml_1m       | rescale: rank     | —                  | seq          | —                  |
| lastfm_2k   | $|C_u|$ = 50      | 0.139              | pop          | 0.01972            |
| lastfm_2k   | $|C_u|$ = 100     | 0.221              | pop          | 0.01998            |
| lastfm_2k   | $|C_u|$ = 200     | 0.346              | pop          | 0.02433            |
| lastfm_2k   | $\lambda$ = 0.1   | —                  | pop          | —                  |
| lastfm_2k   | $\lambda$ = 1.0   | —                  | pop          | —                  |
| lastfm_2k   | $\lambda$ = 10.0  | —                  | pop          | —                  |
| lastfm_2k   | rescale: identity | —                  | pop          | —                  |
| lastfm_2k   | rescale: log1p    | —                  | pop          | —                  |
| lastfm_2k   | rescale: rank     | —                  | pop          | —                  |
| amazon_book | $|C_u|$ = 60      | 0.086              | pop          | 0.02394            |
| amazon_book | $|C_u|$ = 120     | 0.117              | pop          | 0.02603            |
| amazon_book | $|C_u|$ = 240     | 0.164              | pop          | 0.02607            |
| amazon_book | $\lambda$ = 0.1   | —                  | pop          | —                  |
| amazon_book | $\lambda$ = 1.0   | —                  | pop          | —                  |
| amazon_book | $\lambda$ = 10.0  | —                  | pop          | —                  |
| amazon_book | rescale: identity | —                  | pop          | —                  |
| amazon_book | rescale: log1p    | —                  | pop          | —                  |
| amazon_book | rescale: rank     | —                  | pop          | —                  |
