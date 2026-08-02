**T8 — Robustness matrix. CANDIDATE RECALL IS REPORTED PER CELL for the $|C_u|$ sweep: changing $|C_u|$ moves the recall ceiling and hence the level of $v$, so without it the cells are not comparable.**

| Dataset     | Stress test       | Candidate recall   | Top source   | $v(\mathcal{G})$   |
|:------------|:------------------|:-------------------|:-------------|:-------------------|
| amazon_book | $|C_u|$ = 500     | 0.237              | pop          | 0.02649            |
| amazon_book | $|C_u|$ = 1000    | 0.402              | pop          | 0.02815            |
| amazon_book | $|C_u|$ = 2000    | 0.699              | pop          | 0.02615            |
| amazon_book | $\lambda$ = 0.1   | —                  | pop          | —                  |
| amazon_book | $\lambda$ = 1.0   | —                  | pop          | —                  |
| amazon_book | $\lambda$ = 10.0  | —                  | pop          | —                  |
| amazon_book | rescale: identity | —                  | pop          | —                  |
| amazon_book | rescale: log1p    | —                  | pop          | —                  |
| amazon_book | rescale: rank     | —                  | pop          | —                  |
| lastfm_2k   | $|C_u|$ = 250     | 0.383              | pop          | 0.02292            |
| lastfm_2k   | $|C_u|$ = 500     | 0.504              | pop          | 0.02763            |
| lastfm_2k   | $|C_u|$ = 1000    | 0.724              | pop          | 0.02627            |
| lastfm_2k   | $\lambda$ = 0.1   | —                  | pop          | —                  |
| lastfm_2k   | $\lambda$ = 1.0   | —                  | pop          | —                  |
| lastfm_2k   | $\lambda$ = 10.0  | —                  | pop          | —                  |
| lastfm_2k   | rescale: identity | —                  | pop          | —                  |
| lastfm_2k   | rescale: log1p    | —                  | pop          | —                  |
| lastfm_2k   | rescale: rank     | —                  | pop          | —                  |
| ml_1m       | $|C_u|$ = 300     | 0.566              | seq          | 0.05242            |
| ml_1m       | $|C_u|$ = 600     | 0.747              | seq          | 0.05157            |
| ml_1m       | $|C_u|$ = 1200    | 0.890              | seq          | 0.04976            |
| ml_1m       | $\lambda$ = 0.1   | —                  | seq          | —                  |
| ml_1m       | $\lambda$ = 1.0   | —                  | seq          | —                  |
| ml_1m       | $\lambda$ = 10.0  | —                  | seq          | —                  |
| ml_1m       | rescale: identity | —                  | seq          | —                  |
| ml_1m       | rescale: log1p    | —                  | seq          | —                  |
| ml_1m       | rescale: rank     | —                  | seq          | —                  |
