# Data and Knowledge Base

**Owner:** Atharva (Data and Knowledge Base)  
**Last updated:** 14 October 2026  

This directory contains the data download utilities, document manifests, curated bridge tables, and synthetic maintenance records required for the Bearing Fault Copilot.

---

## 1. Directory Structure

```text
data/
├── README.md               # Sources, licenses, download and maintenance notes (this file)
├── download_cwru.py        # Automated download and validation script for 40 CWRU files
├── manifest.json           # Catalog of bearing guides (titles, URLs, licenses, retrieval dates)
├── cwru/                   # [Git-ignored] 40 CWRU .mat files and generated index.csv
├── guides/                 # [Git-ignored] Cleaned guide text files with [[page X]] markers
└── knowledge/              # [Committed] Team-curated technical knowledge
    ├── bridge_table.md     # Curated mapping from CWRU fault locations to damage modes & actions
    └── logs_synthetic.csv  # 36 realistic synthetic plant maintenance log entries
```

---

## 2. Data Sources and Licensing

| Source | Description | License / Usage Terms | Retrieval Date |
| :--- | :--- | :--- | :--- |
| **CWRU Bearing Data Center** | 12 kHz drive-end vibration recordings (Normal, Inner Race, Outer Race, Ball at 0.007", 0.014", 0.021" at 4 motor loads). URL: [Case Western Reserve University](https://engineering.case.edu/bearingdatacenter) | Public academic benchmark for vibration research. Cite CWRU Bearing Data Center; no redistribution of raw data in git. | 2026-10-14 |
| **SKF: Bearing damage and failure analysis** | Failure mode definitions, root causes, spalling mechanisms, electrical erosion, and mounting procedures. | Copyrighted manufacturer publication. Referenced and cited by page; raw PDF and full text are kept local and never committed. | 2026-10-14 |
| **Schaeffler (FAG): Rolling Bearing Damage** | Catalog of typical bearing damage, remedies, smearing, wear, and fretting corrosion. | Copyrighted manufacturer publication. Referenced and cited by page; kept local and git-ignored. | 2026-10-14 |
| **Electric Motor Bearing Maintenance Guide** | Motor bearing diagnostic screening, greasing rules, alignment tolerances, and electrical safety. | Public technical bulletin. Kept local and git-ignored. | 2026-10-14 |
| **ISO 15243:2017** | Rolling bearings — Damage and failures — Terms, characteristics and causes. | Proprietary international standard. Failure mode vocabulary borrowed; text is not ingested. | 2026-10-14 |
| **Curated Bridge Table & Synthetic Logs** | Curated fault-to-cause mappings and synthetic factory log records. | Written by the team and released under the repository's MIT License. | 2026-10-14 |

---

## 3. How to Download and Verify the CWRU Dataset

The 40 benchmark recordings comprise:
- 4 normal baseline recordings (`97`, `98`, `99`, `100`)
- 12 inner race fault recordings (`105`-`108`, `169`-`172`, `209`-`212`)
- 12 ball fault recordings (`118`-`121`, `185`-`188`, `222`-`225`)
- 12 outer race fault recordings centered at 6 o'clock (`130`-`133`, `197`-`200`, `234`-`237`)

### Commands:

1. **Generate the index file only (dry run):**
   ```bash
   python data/download_cwru.py --skip-download
   ```

2. **Download all 40 files and verify `DE_time` variables:**
   ```bash
   python data/download_cwru.py
   ```

3. **Verify existing files:**
   ```bash
   python data/download_cwru.py --verify-only
   ```

---

## 4. Curated Knowledge Base

- **Bridge Table (`data/knowledge/bridge_table.md`):** Links experimental CWRU labels (`inner_race`, `outer_race`, `ball`) to industrial damage modes (subsurface fatigue spalling, electrical fluting, abrasive wear, brinelling, skidding), explicit inspection actions, safety-critical flags, and specific guide pages.
- **Synthetic Maintenance Logs (`data/knowledge/logs_synthetic.csv`):** 36 synthetic historical plant maintenance records with fields:
  `entry_id,date,machine_id,machine_type,symptom,fault_type,action_taken,parts_replaced,downtime_hours,technician_note,synthetic`. All rows have `synthetic=true`.
