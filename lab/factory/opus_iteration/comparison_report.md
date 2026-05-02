# Path 1 vs Path 2 — Comparison + Best-of-Both Merge

**Date:** 2026-05-03

## Aggregate validation results

| Metric | Path 1 (Disciplined) | Path 2 (Trust-Opus) |
|---|---|---|
| Total rules | 27 | 31 |
| PASS | 9 | 10 |
| WARNING | 9 | 8 |
| FAIL | 9 | 13 |
| Pass rate | 33.3% | 32.3% |
| Pass+Warning | 66.7% | 58.1% |

## Merge result

- Total signatures (deduped logical rules): 37
- Final merged rule count: 37
- Predictions: 37

## Per-signature merge decisions

| merged_id | signature | path1 verdict | path2 verdict | chosen | reason |
|---|---|---|---|---|---|
| kill_001 | DOWN_TRI×Bank×any sub=- verdict=REJECT | FAIL | — | path1 | unique to path1 |
| watch_001 | UP_TRI×any×Choppy sub=- verdict=WATCH | WARNING | WARNING | path1 | chose path1 (WARNING) over path2 (WARNING) |
| win_001 | UP_TRI×Auto×Bear sub=- verdict=TAKE_FULL | FAIL | FAIL | path1 | chose path1 (FAIL) over path2 (FAIL) |
| win_002 | UP_TRI×FMCG×Bear sub=- verdict=TAKE_FULL | FAIL | FAIL | path1 | chose path1 (FAIL) over path2 (FAIL) |
| win_003 | UP_TRI×IT×Bear sub=- verdict=TAKE_FULL | FAIL | FAIL | path1 | chose path1 (FAIL) over path2 (FAIL) |
| win_004 | UP_TRI×Metal×Bear sub=- verdict=TAKE_FULL | FAIL | FAIL | path1 | chose path1 (FAIL) over path2 (FAIL) |
| win_005 | UP_TRI×Pharma×Bear sub=- verdict=TAKE_FULL | FAIL | FAIL | path1 | chose path1 (FAIL) over path2 (FAIL) |
| win_006 | UP_TRI×Infra×Bear sub=- verdict=TAKE_FULL | FAIL | FAIL | path1 | chose path1 (FAIL) over path2 (FAIL) |
| win_007 | BULL_PROXY×any×Bear sub=hot verdict=TAKE_FULL | WARNING | — | path1 | unique to path1 |
| rule_001 | UP_TRI×any×Bull sub=late_bull verdict=SKIP | PASS | PASS | path1 | chose path1 (PASS) over path2 (PASS) |
| rule_002 | BULL_PROXY×any×Bull sub=late_bull verdict=SKIP | WARNING | PASS | path2 | chose path2 (PASS) over path1 (WARNING) |
| rule_003 | UP_TRI×any×Bull sub=recovery_bull verdict=TAKE_FULL | WARNING | WARNING | path1 | chose path1 (WARNING) over path2 (WARNING) |
| rule_004 | BULL_PROXY×any×Bull sub=healthy_bull verdict=TAKE_FULL | WARNING | WARNING | path1 | chose path1 (WARNING) over path2 (WARNING) |
| rule_005 | BULL_PROXY×any×Bear sub=- verdict=REJECT | PASS | PASS | path1 | chose path1 (PASS) over path2 (PASS) |
| rule_006 | BULL_PROXY×any×Bull sub=late_bull verdict=REJECT | PASS | — | path1 | unique to path1 |
| rule_007 | UP_TRI×Health×Bear sub=hot verdict=SKIP | FAIL | FAIL | path1 | chose path1 (FAIL) over path2 (FAIL) |
| rule_008 | UP_TRI×any×Bear sub=- verdict=SKIP | PASS | FAIL | path1 | chose path1 (PASS) over path2 (FAIL) |
| rule_009 | UP_TRI×any×Choppy sub=- verdict=SKIP | PASS | PASS | path1 | chose path1 (PASS) over path2 (PASS) |
| rule_010 | BULL_PROXY×any×Choppy sub=- verdict=REJECT | PASS | PASS | path1 | chose path1 (PASS) over path2 (PASS) |
| rule_011 | DOWN_TRI×any×Bear sub=- verdict=TAKE_SMALL | FAIL | — | path1 | unique to path1 |
| rule_012 | UP_TRI×any×Bear sub=cold verdict=TAKE_FULL | WARNING | FAIL | path1 | chose path1 (WARNING) over path2 (FAIL) |
| rule_013 | UP_TRI×Energy×Bull sub=- verdict=SKIP | WARNING | FAIL | path1 | chose path1 (WARNING) over path2 (FAIL) |
| rule_014 | UP_TRI×any×Bull sub=- verdict=SKIP | WARNING | PASS | path2 | chose path2 (PASS) over path1 (WARNING) |
| rule_015 | DOWN_TRI×Pharma×Choppy sub=- verdict=SKIP | PASS | — | path1 | unique to path1 |
| rule_016 | DOWN_TRI×any×Choppy sub=- verdict=SKIP | PASS | PASS | path1 | chose path1 (PASS) over path2 (PASS) |
| rule_017 | UP_TRI×Metal×Choppy sub=- verdict=SKIP | PASS | PASS | path1 | chose path1 (PASS) over path2 (PASS) |
| rule_018 | DOWN_TRI×any×Choppy sub=- verdict=SKIP | WARNING | — | path1 | unique to path1 |
| rule_019 | DOWN_TRI×Bank×Bear sub=- verdict=REJECT | — | PASS | path2 | unique to path2 |
| rule_020 | BULL_PROXY×any×Bear sub=- verdict=TAKE_FULL | — | FAIL | path2 | unique to path2 |
| rule_021 | UP_TRI×any×Bear sub=hot verdict=TAKE_FULL | — | WARNING | path2 | unique to path2 |
| rule_022 | DOWN_TRI×any×Choppy sub=- verdict=TAKE_FULL | — | FAIL | path2 | unique to path2 |
| rule_023 | UP_TRI×any×Choppy sub=- verdict=TAKE_SMALL | — | WARNING | path2 | unique to path2 |
| rule_024 | DOWN_TRI×any×Choppy sub=- verdict=SKIP | — | PASS | path2 | unique to path2 |
| rule_025 | DOWN_TRI×any×Bear sub=- verdict=TAKE_SMALL | — | FAIL | path2 | unique to path2 |
| rule_026 | DOWN_TRI×any×Bull sub=late_bull verdict=TAKE_SMALL | — | WARNING | path2 | unique to path2 |
| rule_027 | UP_TRI×any×Bear sub=- verdict=SKIP | — | WARNING | path2 | unique to path2 |
| rule_028 | BULL_PROXY×any×Bear sub=hot verdict=TAKE_SMALL | — | WARNING | path2 | unique to path2 |