**T8 — Robustness matrix. CANDIDATE RECALL IS REPORTED PER CELL for the $|C_u|$ sweep: changing $|C_u|$ moves the recall ceiling and hence the level of $v$, so without it the cells are not comparable.**

| Dataset   | Stress test       | Candidate recall   | Top source   | $v(\mathcal{G})$   |
|:----------|:------------------|:-------------------|:-------------|:-------------------|
| ml_1m     | $|C_u|$ = 300     | 0.565              | seq          | 0.05277            |
| ml_1m     | $|C_u|$ = 600     | 0.748              | seq          | 0.05075            |
| ml_1m     | $|C_u|$ = 1200    | 0.890              | seq          | 0.05024            |
| ml_1m     | $\lambda$ = 0.1   | —                  | seq          | —                  |
| ml_1m     | $\lambda$ = 1.0   | —                  | seq          | —                  |
| ml_1m     | $\lambda$ = 10.0  | —                  | seq          | —                  |
| ml_1m     | rescale: identity | —                  | seq          | —                  |
| ml_1m     | rescale: log1p    | —                  | seq          | —                  |
| ml_1m     | rescale: rank     | —                  | seq          | —                  |
