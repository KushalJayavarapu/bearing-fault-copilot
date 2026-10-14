### Time to a confident correct call (demo model, held-out 3 hp recordings)

Stream consecutive windows of each held-out demo recording (demo model, never trained on load 3) from many start points. Detected = majority vote of window predictions is the true fault_type AND the mean probability of that class over the windows so far >= HIGH_UNCERTAINTY_BELOW. Time = seconds of signal consumed.

Start points: every 5th window. Windows: 2048 samples (0.171 s), 50% overlap (+0.085 s per extra window).

| fault_type | recordings | start points | median s | worst s | starts never reaching a call |
|---|---|---|---|---|---|
| normal | Normal_3 | 95 | 0.171 | 0.171 | 0 |
| inner_race | IR007_3, IR014_3, IR021_3 | 72 | 0.171 | 1.536 | 0 |
| outer_race | OR007@6_3, OR014@6_3, OR021@6_3 | 72 | 0.171 | 0.853 | 3 (OR014@6_3) |
| ball | B007_3, B014_3, B021_3 | 72 | 0.171 | 0.171 | 0 |
