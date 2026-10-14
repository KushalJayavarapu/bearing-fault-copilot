# Bearing Fault Copilot

A "detect, explain, act" maintenance assistant for factory bearings, built for the AMD Developer Hackathon: ACT III (Track 1, Intelligent Industry).

1. A classifier reads a slice of vibration data from the CWRU Bearing Dataset and predicts the fault type and severity.
2. The prediction becomes a search over public bearing maintenance guides (retrieval-augmented generation).
3. An LLM served on AMD GPUs explains the fault and recommends actions, citing the retrieved passages.
4. A human confirms any safety-critical step.

**Status:** work in progress. This README is a placeholder and will be replaced with run instructions before submission.

## Repo layout

| Folder | What lives here |
| --- | --- |
| `sensor/` | Fault classifier |
| `rag/` | Retrieval pipeline over the bearing guides |
| `app/` | API, orchestrator and user interface |
| `data/` | Download scripts, source links and data notes (no raw data) |
| `docs/` | Data contract, dependency graph, demo script, submission text |

## Working on this repo

- Nobody pushes to `main`. Create a branch named `area/yourname-short-task`, for example `sensor/harshit-baseline`.
- Open a pull request into `main`, fill in the template, and get one approval before merging.
- Never commit secrets (use `.env`, copy from `.env.example`), raw data, source PDFs or model weights.
- The shapes of the data passed between parts are in [`docs/contract.md`](docs/contract.md). Who waits on whom is in [`docs/dependency-graph.md`](docs/dependency-graph.md).

## Data and Citations

- **CWRU Bearing Dataset:** Vibration data courtesy of the **Case Western Reserve University Bearing Data Center** (https://engineering.case.edu/bearingdatacenter), collected under the direction of Prof. Kenneth A. Loparo, Department of Mechanical and Aerospace Engineering.
  > Reference: K. A. Loparo, *Bearing Vibration Data*, Case Western Reserve University Bearing Data Center Website.
- Raw benchmark recordings are not stored directly in this repository; see [`data/README.md`](data/README.md) for data management instructions. CWRU data ingestion is managed centrally by `python -m sensor.build`.

## Licence

MIT. See [LICENSE](LICENSE).
