Feature variant **+envelope** (28 features). Seed 42. RandomForest(300 trees, class_weight=balanced), fixed hyperparameters (no tuning). Windows 2048 samples, 50% overlap, 5887 windows from 40 recordings. Severity accuracy is on truly faulty test windows. Baselines = majority class of the training fold.

### Headline: leave-one-load-out

| fold | n_test | fault acc | fault macro-F1 | severity acc | majority baseline (fault) | majority baseline (severity) | % uncertain (<0.6) | acc when confident | acc when uncertain |
|---|---|---|---|---|---|---|---|---|---|
| test 0 hp | 1295 | 1.000 | 1.000 | 0.926 | 0.183 | 0.335 | 0.006 | 1.000 | 1.000 |
| test 1 hp | 1529 | 0.999 | 0.999 | 0.988 | 0.308 | 0.333 | 0.004 | 1.000 | 0.667 |
| test 2 hp | 1529 | 0.997 | 0.996 | 0.994 | 0.309 | 0.334 | 0.004 | 0.999 | 0.500 |
| test 3 hp | 1534 | 0.964 | 0.962 | 1.000 | 0.308 | 0.334 | 0.052 | 0.987 | 0.550 |
| **mean** | | **0.990** | **0.989** | **0.977** | **0.277** | **0.334** | **0.017** | **0.996** | **0.679** |

### Secondary: hold out whole recordings (StratifiedGroupKFold, 4 folds, one recording per condition per fold)

| fold | n_test | fault acc | fault macro-F1 | severity acc | majority baseline (fault) | majority baseline (severity) | % uncertain (<0.6) | acc when confident | acc when uncertain |
|---|---|---|---|---|---|---|---|---|---|
| fold 0 | 1531 | 0.997 | 0.997 | 0.992 | 0.309 | 0.334 | 0.008 | 0.998 | 0.923 |
| fold 1 | 1531 | 1.000 | 1.000 | 0.938 | 0.308 | 0.334 | 0.001 | 1.000 | 1.000 |
| fold 2 | 1529 | 0.999 | 0.999 | 0.945 | 0.308 | 0.333 | 0.009 | 1.000 | 0.846 |
| fold 3 | 1296 | 0.951 | 0.956 | 0.990 | 0.183 | 0.332 | 0.070 | 0.978 | 0.604 |
| **mean** | | **0.987** | **0.988** | **0.966** | **0.277** | **0.333** | **0.022** | **0.994** | **0.843** |

### Stress test: leave one fault size out (bearings never seen in training; severity n/a)

| fold | n_test | fault acc | fault macro-F1 | severity acc | majority baseline (fault) | majority baseline (severity) | % uncertain (<0.6) | acc when confident | acc when uncertain |
|---|---|---|---|---|---|---|---|---|---|
| test size small + Normal_0 | 1649 | 1.000 | 1.000 | nan | 0.144 | nan | 0.031 | 1.000 | 1.000 |
| test size medium + Normal_1 | 1880 | 0.497 | 0.370 | nan | 0.251 | nan | 0.060 | 0.526 | 0.045 |
| test size large + Normal_2 | 1885 | 0.715 | 0.655 | nan | 0.250 | nan | 0.275 | 0.922 | 0.168 |
| **mean** | | **0.737** | **0.675** | **nan** | **0.215** | **nan** | **0.122** | **0.816** | **0.404** |

Holdout folds: fold 0: B007_3, B014_0, B021_2, IR007_1, IR014_1, IR021_2, Normal_3, OR007@6_0, OR014@6_1, OR021@6_0; fold 1: B007_0, B014_2, B021_3, IR007_2, IR014_2, IR021_0, Normal_2, OR007@6_2, OR014@6_2, OR021@6_2; fold 2: B007_2, B014_3, B021_0, IR007_0, IR014_0, IR021_3, Normal_1, OR007@6_1, OR014@6_0, OR021@6_3; fold 3: B007_1, B014_1, B021_1, IR007_3, IR014_3, IR021_1, Normal_0, OR007@6_3, OR014@6_3, OR021@6_1

Top fault_type features (mean RF importance over LOLO folds): p2p (0.123), rms (0.115), env_bpfi_1x (0.104), peak (0.098), spectral_centroid (0.089), bpfo_1x (0.060)
