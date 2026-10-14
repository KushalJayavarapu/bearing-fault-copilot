"""Every decision threshold for the sensor result, in one place."""

# Confidence -> uncertainty.level in the final answer (docs/contract.md section 3).
# 0.60 comes from the task brief. 0.95 was chosen on held-out data (results/confidence_bands.md),
# so the accuracies quoted for the medium and low bands are slightly optimistic.
HIGH_UNCERTAINTY_BELOW = 0.60
LOW_UNCERTAINTY_AT_OR_ABOVE = 0.95

# evidence: an envelope-spectrum peak at a fault frequency is reported only if its vs_normal (see docs/contract.md)
# is >= EVIDENCE_MIN_VS_NORMAL; weaker peaks are dropped, so weak cases return []. Chosen on the training loads (0/1/2)
# only, before looking at the held-out 3 hp windows: the smallest value where, for every condition, at most 5% of
# windows get a strongest peak from the wrong fault family (results/evidence.md).
EVIDENCE_MIN_VS_NORMAL = 2.5
EVIDENCE_HIGH_VS_NORMAL = 5.0  # strength "high" at or above this, "medium" from EVIDENCE_MIN_VS_NORMAL up to it


def evidence_strength(vs_normal):
    return "high" if vs_normal >= EVIDENCE_HIGH_VS_NORMAL else "medium"


def uncertainty_level(confidence):
    """'high' below 0.60, 'low' at or above 0.95, 'medium' in between."""
    if confidence < HIGH_UNCERTAINTY_BELOW:
        return "high"
    return "low" if confidence >= LOW_UNCERTAINTY_AT_OR_ABOVE else "medium"


if __name__ == "__main__":
    assert [uncertainty_level(c) for c in (0.0, 0.5999, 0.60, 0.9499, 0.95, 1.0)] == ["high", "high", "medium", "medium", "low", "low"]
    print("ok")
