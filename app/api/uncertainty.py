"""Uncertainty level from the sensor confidence.

Bands come from Harshit's held-out measurements (sensor/results/confidence_bands.md):
  high   confidence < 0.60
  medium 0.60 <= confidence < 0.95
  low    confidence >= 0.95
The bands were chosen on held-out data, so do not call them "calibrated".
TODO: when the thresholds live in sensor config (Harshit's follow-up PR), import them from there.
"""
HIGH_BELOW = 0.60
LOW_FROM = 0.95


def level(confidence: float) -> str:
    if confidence < HIGH_BELOW:
        return "high"
    if confidence >= LOW_FROM:
        return "low"
    return "medium"
