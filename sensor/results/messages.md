# Messages (copy the text inside each block)

## Reply to Kushal: model and data on a fresh clone

```text
Script that builds, not committed files: python -m sensor.build. It downloads the 40 recordings, checks each one's size and SHA-256 against sensor/cwru_manifest.json, and trains the models. No manual steps.
Why: the team rule keeps data and weights out of git; the CWRU license is still unchecked, so we shouldn't redistribute the data or a model derived from it; and the build is deterministic (seed 42) and quick.
Measured on my laptop: the 40 files are 140.3 MB and took 281 s to download, because the CWRU server cuts every transfer after about 3 s and the downloader resumes. Training takes 5.5 s. The model files are 1.41 MB (demo, the default) and 1.81 MB. A rerun with everything in place is a 0.2 s no-op.
The SHA-256 check matters: we already got truncated .mat files from those cut-off transfers. A file is now only accepted when its size and hash match the manifest; otherwise it retries 3 times and then stops the build loudly.
For the Dockerfile: RUN python -m sensor.build at image build time, so the live demo never downloads anything.
evidence is documented in docs/contract.md section 1, below the unchanged sample, so your test_api still passes (10 passed): optional, a missing field means [], and it can disagree with fault_type (5 of 1534 held-out windows), so please show the disagreement rather than hide it. Thresholds and uncertainty_level(confidence) are in sensor/config.py, so the TODO in app/api/uncertainty.py can import them from there; I haven't touched app/. predict() with evidence: median 88 ms (p95 108 ms) for meta.latency_ms.classifier.
```

## Reply to Kushal: data and licence

```text
Data and licence: the CWRU Bearing Data Center pages have no dataset license or terms of use (checked 14 Oct 2026), only a site-wide copyright footer and generic university website terms. So we use the data with attribution but don't redistribute it: the repo has only the download script and the SHA-256 manifest, and any Docker image that contains the data must not go to a public registry.
At runtime, the demo model needs only the model file (1.41 MB) and the 10 held-out 3 hp recordings (34.2 MB); the healthy baseline is inside the model file. python -m sensor.build --runtime-only DIR copies just those 10, hash-checked, so the final image stage can copy the model plus DIR. list_recordings() then lists only those 10, and any other recording raises a clear FileNotFoundError.
The source, terms and citation (Smith and Randall 2015, MSSP 64-65:100-131, doi:10.1016/j.ymssp.2015.04.021, checked against the DOI) are now in sensor/README.md.
```

## Team chat summary (end of day 14 Oct)

```text
Sensor end of day (Harshit): #2 and #4 merged; #8 open for Kushal (data terms + citation, runtime-only data subset). Full handover: sensor/STATUS.md.
Numbers: 99.0% fault-type accuracy at a motor load the model never saw (macro-F1 0.989, severity 97.7%, majority baseline 27.7%); 40-100% on bearings it never saw. Demo model on the held-out 3 hp: 96.4%. predict() median 88 ms.
Demo: heroes IR021_3 (windows 0-68), OR007@6_3 (0-117), OR021@6_3 (56-71). Uncertain pick: OR014@6_3 windows 111-115 (wrong call, confidence below 0.6, evidence empty).
@Karthiik: the Docker image contains CWRU data (no license found), so build it on the host or use a private registry, never a public one. Use python -m sensor.build --runtime-only for the final stage (10 files, 34.2 MB).
@Santos @Karan: evidence is optional and can disagree with fault_type; show that, don't hide it. uncertainty.level comes from sensor.config.
Tomorrow: I'm helping Santos with the retrieval query built from fault_type, severity and evidence.
```
