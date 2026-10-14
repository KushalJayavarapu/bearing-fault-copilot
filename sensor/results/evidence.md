### evidence(): non-empty rate and strongest-peak family

Cells: % windows non-empty / strongest peak = true family / strongest peak = wrong family.

#### Threshold sweep on training loads 0/1/2 (used to choose EVIDENCE_MIN_VS_NORMAL)

| condition | T = 1 | T = 1.5 | T = 2 | T = 2.5 | T = 3 | T = 4 |
|---|---|---|---|---|---|---|
| Normal | 3% / 0% / 3% | 0% / 0% / 0% | 0% / 0% / 0% | 0% / 0% / 0% | 0% / 0% / 0% | 0% / 0% / 0% |
| IR007 | 100% / 100% / 0% | 100% / 100% / 0% | 100% / 100% / 0% | 100% / 100% / 0% | 100% / 100% / 0% | 99% / 99% / 0% |
| IR014 | 100% / 100% / 0% | 100% / 100% / 0% | 94% / 94% / 0% | 44% / 44% / 0% | 6% / 6% / 0% | 0% / 0% / 0% |
| IR021 | 100% / 100% / 0% | 100% / 100% / 0% | 100% / 100% / 0% | 100% / 100% / 0% | 100% / 100% / 0% | 99% / 99% / 0% |
| B007 | 76% / 12% / 64% | 15% / 1% / 14% | 2% / 1% / 1% | 0% / 0% / 0% | 0% / 0% / 0% | 0% / 0% / 0% |
| B014 | 88% / 68% / 20% | 42% / 38% / 5% | 15% / 14% / 1% | 3% / 3% / 0% | 0% / 0% / 0% | 0% / 0% / 0% |
| B021 | 97% / 18% / 79% | 73% / 14% / 59% | 27% / 8% / 20% | 8% / 5% / 3% | 3% / 3% / 0% | 0% / 0% / 0% |
| OR007@6 | 100% / 100% / 0% | 100% / 100% / 0% | 100% / 100% / 0% | 100% / 100% / 0% | 100% / 100% / 0% | 100% / 100% / 0% |
| OR014@6 | 53% / 2% / 51% | 7% / 0% / 6% | 0% / 0% / 0% | 0% / 0% / 0% | 0% / 0% / 0% | 0% / 0% / 0% |
| OR021@6 | 100% / 100% / 0% | 100% / 100% / 0% | 100% / 100% / 0% | 95% / 95% / 0% | 69% / 69% / 0% | 10% / 10% / 0% |
| **worst wrong-family rate** | **79%** | **59%** | **20%** | **3%** | **0%** | **0%** |

Rule: smallest T with wrong-family rate <= 5% for every condition -> **2.5** (configured EVIDENCE_MIN_VS_NORMAL = 2.5).

#### Held-out 3 hp windows, before (T = 1) and after (T = 2.5)

| fault type | recordings | windows | non-empty before | non-empty after | right family after | wrong family after |
|---|---|---|---|---|---|---|
| normal | Normal_3 | 473 | 1.7% | 0.0% | 0.0% | 0.0% |
| **normal** | **all** | **473** | **1.7%** | **0.0%** | **0.0%** | **0.0%** |
| inner_race | IR007_3 | 119 | 100.0% | 100.0% | 100.0% | 0.0% |
| inner_race | IR014_3 | 117 | 100.0% | 0.9% | 0.9% | 0.0% |
| inner_race | IR021_3 | 118 | 100.0% | 100.0% | 100.0% | 0.0% |
| **inner_race** | **all** | **354** | **100.0%** | **67.2%** | **67.2%** | **0.0%** |
| outer_race | OR007@6_3 | 118 | 100.0% | 100.0% | 100.0% | 0.0% |
| outer_race | OR014@6_3 | 118 | 40.7% | 0.0% | 0.0% | 0.0% |
| outer_race | OR021@6_3 | 118 | 100.0% | 76.3% | 72.9% | 3.4% |
| **outer_race** | **all** | **354** | **80.2%** | **58.8%** | **57.6%** | **1.1%** |
| ball | B007_3 | 117 | 76.9% | 0.0% | 0.0% | 0.0% |
| ball | B014_3 | 118 | 94.9% | 12.7% | 12.7% | 0.0% |
| ball | B021_3 | 118 | 99.2% | 0.8% | 0.0% | 0.8% |
| **ball** | **all** | **353** | **90.4%** | **4.5%** | **4.2%** | **0.3%** |

#### Held-out 3 hp windows: precision and disagreement with the classifier (T = 2.5, demo model)

Precision = among windows with non-empty evidence, strongest peak names the true fault family. Disagreement = evidence non-empty and its strongest peak names a different family than the classifier's fault_type (a classifier call of normal with non-empty evidence counts as disagreement).

| fault type | windows | evidence non-empty | precision | disagreement (of all windows) | disagreement (of non-empty) |
|---|---|---|---|---|---|
| normal | 473 | 0.0% (0) | n/a (0 non-empty) | 0.0% (0) | n/a |
| inner_race | 354 | 67.2% (238) | 100.0% (238/238) | 0.0% (0) | 0.0% (0/238) |
| outer_race | 354 | 58.8% (208) | 98.1% (204/208) | 1.1% (4) | 1.9% (4/208) |
| ball | 353 | 4.5% (16) | 93.8% (15/16) | 0.3% (1) | 6.2% (1/16) |

#### OR014@6_3 (uncertain demo pick, true fault outer_race), windows 111-115

| window | classifier fault_type | evidence |
|---|---|---|
| 111 | outer_race | [] |
| 112 | outer_race | [] |
| 113 | outer_race | [] |
| 114 | ball | [] |
| 115 | outer_race | [] |

All 118 OR014@6_3 windows: evidence non-empty in 0.
