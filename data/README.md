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
| **SKF: Bearing damage and failure analysis** | **Script Only (Not committed)** | © SKF Group. All rights reserved. Strict proprietary manufacturer document; redistribution of full text prohibited without written permission. Passages cited by page and linked to official portal. |
| **Schaeffler (FAG): Rolling Bearing Damage** | **Script Only (Not committed)** | © Schaeffler Technologies AG & Co. KG. All rights reserved. Proprietary manufacturer document; kept strictly local and git-ignored. |
| **Industrial Motor Bearing Maintenance Handbook** | **Script Only (Not committed)** | Derived from U.S. Department of Energy (EERE) public technical literature. Kept local and git-ignored to maintain uniform handling across all guides. |
| **Curated Bridge Table & Synthetic Logs** | **Committed (OK)** | Authored by the team and released under the repository's MIT License. |

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
This writes local text files with `[[page X]]` citation markers into `data/guides/`, which are git-ignored and never committed.
