# Data and Knowledge Base

**Owner:** Atharva (Data and Knowledge Base)  
**Last updated:** 14 October 2026  

This directory contains the knowledge manifest, curated bridge tables, synthetic maintenance records, and guide extraction utilities for the Bearing Fault Copilot.

---

## 1. Directory Structure

```text
data/
├── README.md               # Sources, licenses, citations and terms of use (this file)
├── manifest.json           # Catalog of bearing guides (titles, URLs, licenses, page counts)
├── fetch_guides.py         # Utility script to set up local guide texts (git-ignored)
├── cwru/                   # [Git-ignored] CWRU benchmark files and index (managed by sensor.build)
├── guides/                 # [Git-ignored] Cleaned guide text files with [[page X]] markers
└── knowledge/              # [Committed] Team-curated technical knowledge
    ├── bridge_table.md     # Curated mapping from CWRU fault locations to damage modes & actions
    ├── logs_synthetic.csv  # 36 realistic synthetic plant maintenance log entries
    └── eval_questions.json # 12 independent maintenance questions for retrieval benchmarking
```

---

## 2. Publisher Terms & Copyright Disclosures

Our repository is public and MIT-compliant. To strictly respect publisher copyrights and terms of use:

| Source | Status in Git | Publisher Copyright Terms |
| :--- | :---: | :--- |
| **Team reference notes: bearing damage modes (ISO 15243 classes)** | **Script Only (Not committed)** | Written by the team (MIT). Not a copy of the SKF document or any other publication. The `[[page N]]` markers are section breaks, not page numbers of a real document. |
| **Team reference notes: bearing damage causes and remedies** | **Script Only (Not committed)** | Written by the team (MIT). Not a copy of any Schaeffler document. |
| **Team reference notes: electric motor bearing maintenance and lubrication** | **Script Only (Not committed)** | Written by the team (MIT). Not a copy of any U.S. Department of Energy document. |
| **Curated Bridge Table & Synthetic Logs** | **Committed (OK)** | Authored by the team and released under the repository's MIT License. The bridge table's page references are unverified (see the note in the file). The 36 log entries are synthetic and are marked as such in answers. |

---

## 3. CWRU Bearing Data Center Citation & Acknowledgement

Vibration acceleration recordings are sourced from the **Case Western Reserve University (CWRU) Bearing Data Center**:
- Website: https://engineering.case.edu/bearingdatacenter
- Citation / Acknowledgment:
  > *Case Western Reserve University Bearing Data Center. Data collected under the direction of Prof. Kenneth A. Loparo, Department of Mechanical and Aerospace Engineering, Case Western Reserve University, Cleveland, OH, USA.*

CWRU benchmark download and verification is managed centrally by Harshit's sensor pipeline with SHA-256 hash checks via:
```bash
python -m sensor.build
```

---

## 4. Setting Up Local Guide Texts

To extract and prepare the local cleaned guide text files in `data/guides/` prior to building the RAG index:
```bash
python -m data.fetch_guides
```
This writes the team's reference notes, with `[[page X]]` section markers (not real page numbers), into `data/guides/`, which is git-ignored. The app does not show page numbers unless `CITE_PAGES=true`.
