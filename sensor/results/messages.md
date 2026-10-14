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

## Team chat summary

```text
Sensor update (Harshit): follow-up PR (sensor/harshit-evidence) adds the optional evidence field, the uncertainty bands and a one-command build.
Build: python -m sensor.build downloads and SHA-256-checks the 40 recordings, then trains (about 5 minutes the first time, mostly the slow CWRU server; 0.2 s when everything is already there).
Uncertainty: uncertainty_level(confidence) gives high below 0.60 (from the brief), medium, and low at or above 0.95 (chosen on held-out data, so the band accuracies are slightly optimistic).
Evidence: physics peaks behind each call. When present, it's right 94-100% of the time. It's empty for healthy windows and almost always empty for ball faults.
Demo: heroes IR021_3 (windows 0-68) and OR007@6_3 (0-117). Uncertain pick OR014@6_3 windows 111-115, where the model wrongly says ball at 0.51 confidence and evidence is empty. Picks are in sensor/results/demo_picks.md.
Headline unchanged: 99.0% fault-type accuracy at a motor load the model never saw; 40-100% on bearings it never saw.
```
