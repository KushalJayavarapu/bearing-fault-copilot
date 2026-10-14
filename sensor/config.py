"""Every decision threshold for the sensor result, in one place."""

# Confidence -> uncertainty.level in the final answer (docs/contract.md section 3).
# 0.60 comes from the task brief. 0.95 was chosen on held-out data (results/confidence_bands.md),
# so the accuracies quoted for the medium and low bands are slightly optimistic.
HIGH_UNCERTAINTY_BELOW = 0.60
LOW_UNCERTAINTY_AT_OR_ABOVE = 0.95


def uncertainty_level(confidence):
    """'high' below 0.60, 'low' at or above 0.95, 'medium' in between."""
    if confidence < HIGH_UNCERTAINTY_BELOW:
        return "high"
    return "low" if confidence >= LOW_UNCERTAINTY_AT_OR_ABOVE else "medium"


if __name__ == "__main__":
    assert [uncertainty_level(c) for c in (0.0, 0.5999, 0.60, 0.9499, 0.95, 1.0)] == ["high", "high", "medium", "medium", "low", "low"]
    print("ok")
