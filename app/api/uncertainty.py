"""Uncertainty level from the sensor confidence.

Bands come from Harshit's held-out measurements (sensor/results/confidence_bands.md):
  high   confidence < 0.60
  medium 0.60 <= confidence < 0.95
  low    confidence >= 0.95
The bands were chosen on held-out data, so do not call them "calibrated".
These copies must match sensor/config.py (uncertainty_level); test_api.test_uncertainty_matches_the_sensor_package checks it.
"""
HIGH_BELOW = 0.60
LOW_FROM = 0.95


def level(confidence: float) -> str:
    if confidence < HIGH_BELOW:
        return "high"
    if confidence >= LOW_FROM:
        return "low"
    return "medium"


NOTES = {
    "high": "Low confidence ({pct}%). Treat this label as a hint only and arrange a manual inspection.",
    "medium": "Moderate confidence ({pct}%). Confirm with a manual check before acting.",
    "low": "High confidence ({pct}%) on lab-trained data. Confirm before acting on safety-critical steps.",
}


def note(lvl: str, confidence: float) -> str:
    return NOTES[lvl].format(pct=round(confidence * 100))
