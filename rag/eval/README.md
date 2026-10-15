# rag/eval: does a different retrieval query help?

**Owner:** Harshit. For Santos (retrieval) and Kushal (orchestrator). Nothing in `rag/` outside this folder or in `app/` was changed.

**Verdict: no variant clearly beats the current `orchestrator.build_query` (A). Keep it.** Severity in the text neither helps nor hurts, evidence terms add nothing measurable, and the damage-mode vocabulary fixes one request while hurting another. No `build_query_v2` was written. Details and caveats below.

## Run it (one command, any corpus)

```bash
python -m data.fetch_guides && python -m rag.build && python -m rag.eval.query_eval
python -m rag.eval.test_query_eval          # self-check of labels, scoring and variants, no index needed
python -m rag.eval.make_fixtures            # only to regenerate the sensor scenarios (needs the CWRU data and demo model, 2 min)
```

The scenarios do not depend on the guide corpus, so after the guides are replaced the first line is all that is needed. A clean rebuild (index and guide texts deleted) gave byte-identical results. The harness stops if the index is missing or has no BM25/dense part, and if a returned passage is not in the index, so it cannot silently score the mock passages.

Outputs in `results/`: `query_eval.md` (all tables and the conflict listing), `query_eval.json` (request, chunk ids and scores per scenario and variant), `labels_audit.md` (the tag of every indexed passage). They contain chunk ids and titles only, no passage text.

## Scenarios (`fixtures/scenarios.json`)

Real `sensor.predict()` output on the held-out 3 hp windows (demo model never trained on them), sensor JSON only. 72 scenarios:

- **sweep (60):** 6 evenly spaced windows of each of the 10 held-out recordings (every fault type x severity, plus normal).
- **hero (3):** IR021_3 w34, OR007@6_3 w58, OR021@6_3 w63.
- **uncertain (5):** OR014@6_3 w111-115. Window 114 is called ball (0.507) although the recording is outer race.
- **conflict (5):** every window of the 1534 where `orchestrator.evidence_conflict` fires: B021_3 w76 and OR021@6_3 w77, 104, 106, 117. In all five the classifier is right and the competing peak is weak (2.5-2.9x normal).

## How passages are labelled (`labels.json`, derived by `derive_tags`)

- **Fault of a passage.** Bridge-table row: its `Bearing Fault Type`. Synthetic log: its `Fault Type` (`normal` for healthy-machine logs). Guide page: the fault of every bridge row that cites that guide and page (the bridge table already maps pages to faults). Any other guide page is untagged ("general").
- **`routine`:** guide pages whose first 20 words contain `condition monitoring`, `greasing`, `routine` or `lubrication interval`.
- **right-fault hit (hit5):** at least one top-5 passage carries the predicted `fault_type` (for normal: a `normal` or `routine` tag). `right5` counts them.
- **wrong-fault (wrong3, wrong5):** a top-3 (top-5) passage with a tag, other than only `routine`, that does not include the predicted fault. For normal: a passage tagged with a fault and not `normal`/`routine`. Untagged and routine passages are never wrong.
- **actionable/safety step (safety, faulty cases only):** the top-5 text matches `safety_regex` in `labels.json` (`Safety-Critical Action: Yes`, `Safety Critical:`, lockout/LOTO, tag out, de-energise, zero energy).
- **source mix:** mean guide / playbook (bridge table) / log passages in the top 5. `synthetic_bad` counts log passages not flagged `synthetic` with the `[SYNTHETIC DEMO LOG]` notice; it must be 0 and is 0 for every variant.
- `overrides` in `labels.json` replaces the tags of one chunk id (none used; stale ids are reported). Please read `results/labels_audit.md` once: it is the whole labelling.

Scoring is always against the **predicted** fault, as the product does. Where the classifier is wrong (3 of the 12 sweep windows of IR014_3 and OR014@6_3 are called ball) retrieval just follows it.

## Variants

| | query |
|---|---|
| A | `orchestrator.build_query` (imported): `outer race defect, small, deep groove ball bearing: causes and actions` |
| B | A without `, small`. The request still carries `severity`, which the retriever also puts into one of its own sub-queries. |
| B2 | B and `severity=None` (extra, removes severity everywhere) |
| C | A + `; outer race fault frequency BPFO, repeating impacts` for each evidence family (only when evidence is non-empty) |
| D | C + `; ` + the bridge-table damage-mode names of the predicted fault, read from `data/knowledge/bridge_table.md` at run time |

## Results (sweep, 60 scenarios, real numbers from `results/query_eval.md`)

`hit5` and `safety` are 100% for every variant in every group, so they cannot separate anything. Scenarios in a group repeat requests (the 60 sweep scenarios are only 10 distinct requests under A), so read the `distinct` column, not `n`.

| predicted fault (distinct requests A) | variant | right5 | wrong3 | wrong5 | guide / playbook / log in top 5 |
|---|---|---|---|---|---|
| normal (1) | A, B, B2, C, D | 2.00 | 1.00 | 3.00 | 2.0 / 2.0 / 1.0 (identical) |
| inner_race (3) | A, B, B2 | 3.00 | 1.00 | 2.00 | 0.0 / 5.0 / 0.0 |
| | C | 3.00 | 1.00 | 2.00 | 0.0 / 3.5 / 1.5 |
| | D | 5.00 | 0.00 | 0.00 | 1.0 / 4.0 / 0.0 |
| outer_race (3) | A, B, B2 | 5.00 | 0.00 | 0.00 | 0.0 / 4.0 / 1.0 |
| | C | 5.00 | 0.00 | 0.00 | 0.0 / 3.5 / 1.5 |
| | D | 4.00 | 0.00 | 1.00 | 0.0 / 4.5 / 0.5 |
| ball (3) | A, B, B2, C | 5.00 | 0.00 | 0.00 | 1.0 / 3.0 / 1.0 |
| | D | 5.00 | 0.00 | 0.00 | 1.0 / 3.9 / 0.1 |
| **all (10)** | A, B, B2 | 4.17 | 0.37 | 0.83 | 0.6 / 3.7 / 0.7 |
| | C | 4.17 | 0.37 | 0.83 | 0.6 / 3.2 / 1.3 |
| | D | 4.42 | 0.10 | 0.58 | 0.8 / 3.9 / 0.3 |

Hero (3), uncertain (5) and conflict (5) picks have their own tables, and the top 5 each variant returns for every conflict window is listed, in `results/query_eval.md`. They show nothing the sweep does not.

## What the numbers say

- **B (no severity in the text): no difference.** Over the 10 distinct request pairs the top-5 set never changes, only the order in 3. Severity is not noise, but it is not signal either. Leave it.
- **C (evidence terms): no gain, and a side effect.** Same hit5/right5/wrong in every group; the top-5 set changes in 5 of 13 distinct pairs, always by swapping a bridge-table row for a **synthetic log** (logs 0.7 -> 1.3 per answer). That moves the answer toward the least authoritative source for no measured benefit.
- **D (C + damage modes): a trade, not a win.** It fixes inner race (wrong3 1.00 -> 0.00, right5 3 -> 5) but hurts outer race: all 5 distinct outer-race requests get the inner-race fatigue row (`bridge-table-inner_race-p12-c1`) into the top 5 (right5 5 -> 4, wrong5 0 -> 1). Net wrong5 is better in 3 distinct requests and worse in 5. It cuts logs (0.7 -> 0.3) and slightly raises guide pages (0.6 -> 0.8).
- **Where D's gain really comes from, and it is a corpus issue, not a query issue.** In A, one bridge row, `bridge-table-outer_race-p19-c6` (abrasive wear / contamination groove, tagged outer_race), is rank 2 for **all three** inner-race requests. Its text is generic raceway wear (the matching p19 guide chunk in the local corpus mentions both outer and inner raceways), so counting it as wrong-fault for inner race is debatable. D only pushes that one row out. If Santos or Atharva want to fix it, the table/corpus is the place (for example a matching inner-race wear row or a note that the page applies to both), not the query. I did not test that, since I do not edit the corpus files.
- **Conflict windows: the query does not surface the disagreement.** With BSF and BPFO evidence on an outer-race classification, no variant retrieves a ball passage; with BPFO evidence on a ball classification, C adds one outer-race row (replacing a ball log). Showing the conflict stays the job of the orchestrator's `evidence_conflict` sentence. No special handling was added.
- **Uncertain windows: retrieval inherits the classifier's mistake.** For window 114 (ball at 0.507, true outer race, evidence `[]`) every variant returns only ball passages (wrong5 = 0 for A). With empty evidence C and D cannot help. A fix would need the runner-up class from `probabilities`; not tried.

## Caveats

- The decision rule ("clearly beats A") was not written down before the first run. My call: D does not qualify because its gain rests on one passage in 3 distinct requests and it loses on outer race; B and C show nothing.
- `hit5` is saturated at 100% with a 69-passage corpus, so this eval can only see wrong-fault and source mix, not whether the right passage is the *best* one. A larger or replaced corpus may behave differently: rerun the one command.
- Labels come from the bridge table's page-to-fault mapping plus keywords, not from reading every passage. Guide pages the bridge table does not cite are "general" and can never count as a hit or as wrong.
- The retriever builds three of its four sub-queries from `fault_type`/`severity` itself (weights 1.0, 0.9, 1.0 against 2.0 for the request text), so the text of the request only moves ranking at the edges. That is a likely reason B and C change so little.
- The guide pages in this corpus are the texts written into `data/fetch_guides.py`, not extracted from the real PDFs (raised separately). "guide" below means those pages, and every guide-page result here must be rerun once the corpus is replaced.
- `rank-bm25` and `fastembed` are imported by `rag/` but are in no requirements file; I installed them in the repo `.venv` to build the index.

## If a variant is wanted anyway

The switch would be one line in `app/api/orchestrator.py` line 81: `retrieve(build_query(sensor))` -> `retrieve(build_query_v2(sensor))`. There is no `build_query_v2` because nothing qualified; `rag/eval/variants.py` has C and D as functions if you want to try them.

## Variant E: top two classes when confidence is low (proposal only)

`python -m rag.eval.uncertain_eval` (needs the index; fixtures in `fixtures/high_uncertainty.json`, regenerate with `--make-fixtures`, 2 min). Run only on the 80 held-out windows with confidence below `sensor.config.HIGH_UNCERTAINTY_BELOW` (0.60). E: retrieve with A for the top two classes of `probabilities`, interleave, drop repeated chunk ids, keep 5. Scored against the **true** fault. Output: `results/uncertain_eval.md`.

| group (windows) | variant | true-fault passage in top 5 | true-fault passages (of 5) | predicted-class passages (of 5) | guide / playbook / log |
|---|---|---|---|---|---|
| top-1 class wrong (36) | A | 0/36 | 0.00 | 5.00 | 1.0 / 3.0 / 1.0 |
| | E | 36/36 | 1.61 | 2.97 | 0.0 / 5.0 / 0.0 |
| top-1 class right (44) | A | 44/44 | 4.18 | 4.18 | 0.0 / 4.4 / 0.6 |
| | E | 44/44 | 2.59 | 2.59 | 0.0 / 4.4 / 0.6 |
| all (80) | A | 44/80 | 2.30 | 4.55 | 0.5 / 3.8 / 0.8 |
| | E | 80/80 | 2.15 | 2.76 | 0.0 / 4.7 / 0.3 |

- **It does what it is for.** In all 36 misclassified windows the true fault was the classifier's second class, and A retrieves none of its passages. E brings in 1.6 of them on average, including OR014@6_3 window 114 (ball at 0.507, true outer race): E adds `bridge-table-outer_race-p19-c6` and `-p32-c8` next to three ball rows.
- **What it pushes out.** About half the predicted-class passages (5.0 -> 3.0 when the classifier was wrong; 4.2 -> 2.6 true-fault passages when it was right, with the other class filling the gap). All guide pages and logs disappear from the 36 misclassified windows: E's answer there is bridge-table rows only.
- **Net on the 80 windows:** true-fault passages per answer 2.30 -> 2.15, i.e. no gain; E trades presence of the true fault for dilution. Whether that is wanted depends on the human-confirm moment and on how the prompt copes with two candidate faults, which this measurement cannot see.
- **Thin evidence.** 78 of the 80 windows are two recordings (IR014_3 and OR014@6_3, both confused with ball) and there are only 5 distinct class pairs. It says nothing about other bearings, and I did not test whether the second class's probability could tell the cases apart.
- **Not a recommendation to switch.** Nothing in `app/` is changed. Rerun after the corpus is replaced before deciding.
