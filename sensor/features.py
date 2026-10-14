"""Per-window features: time domain, FFT band-energy ratios, envelope-spectrum peaks at fault frequencies."""
import numpy as np
from scipy.signal import butter, hilbert, sosfiltfilt
from scipy.stats import kurtosis, skew

from .data_loading import SAMPLE_RATE_HZ

FAULT_MULT = {"bpfi": 5.4152, "bpfo": 3.5848, "bsf": 4.7135, "ftf": 0.39828}  # x shaft Hz, drive end 6205
ENV_FAULTS = ("bpfi", "bpfo", "bsf")
HARMONICS = (1, 2, 3)
BAND = 0.05  # +-5%, rpm is hand-recorded
# ponytail: fixed 2-5 kHz demodulation band chosen up front (never tuned on results); kurtogram if it matters
ENV_SOS = butter(4, [2000, 5000], btype="bandpass", fs=SAMPLE_RATE_HZ, output="sos")

LOUDNESS = ["rms", "peak", "p2p"]
FEATURE_NAMES = (
    LOUDNESS + ["crest", "kurtosis", "skewness"]
    + [f"{k}_{h}x" for k in FAULT_MULT for h in HARMONICS]
    + ["spectral_centroid"]
    + [f"env_{k}_{h}x" for k in ENV_FAULTS for h in HARMONICS]
)
BASELINE = FEATURE_NAMES[:19]  # v1 feature set (no envelope)
VARIANTS = {
    "baseline": BASELINE,
    "+envelope": FEATURE_NAMES,
    "+envelope -loudness": [f for f in FEATURE_NAMES if f not in LOUDNESS],
}


def _band(freqs, fc):
    mask = np.abs(freqs - fc) <= BAND * fc
    mask[np.argmin(np.abs(freqs - fc))] = True  # bins are 5.9 Hz wide; narrow bands would be empty otherwise
    return mask


def envelope_spectrum(w, fs=SAMPLE_RATE_HZ):
    """(n, L) windows -> freqs, (n, L//2+1) envelope amplitude spectrum."""
    env = np.abs(hilbert(sosfiltfilt(ENV_SOS, w, axis=1), axis=1))
    spec = np.abs(np.fft.rfft(env - env.mean(1, keepdims=True), axis=1))
    return np.fft.rfftfreq(w.shape[1], 1 / fs), spec


def envelope_peaks(w, rpm, fs=SAMPLE_RATE_HZ):
    """Per fault freq/harmonic: (peak/median ratio, peak freq Hz), each (n, 9). Ratio is amplitude-free."""
    freqs, spec = envelope_spectrum(w, fs)
    floor = np.median(spec[:, (freqs > 0) & (freqs < 1000)], axis=1)
    ratios, peak_hz = [], []
    for k in ENV_FAULTS:
        for h in HARMONICS:
            idx = np.flatnonzero(_band(freqs, FAULT_MULT[k] * h * rpm / 60))
            best = idx[spec[:, idx].argmax(1)]
            ratios.append(spec[np.arange(len(w)), best] / floor)
            peak_hz.append(freqs[best])
    return np.column_stack(ratios), np.column_stack(peak_hz)


def extract(windows, rpm, fs=SAMPLE_RATE_HZ):
    """windows: (n, L) raw samples -> (n, len(FEATURE_NAMES)) features."""
    w = np.atleast_2d(windows)
    rms = np.sqrt((w ** 2).mean(1))
    peak = np.abs(w).max(1)
    time_feats = [rms, peak, w.max(1) - w.min(1), peak / rms, kurtosis(w, axis=1), skew(w, axis=1)]

    power = np.abs(np.fft.rfft(w - w.mean(1, keepdims=True), axis=1)) ** 2
    freqs = np.fft.rfftfreq(w.shape[1], 1 / fs)
    total = power.sum(1)
    shaft_hz = rpm / 60
    band_feats = [power[:, _band(freqs, m * h * shaft_hz)].sum(1) / total  # fraction of energy
                  for m in FAULT_MULT.values() for h in HARMONICS]
    centroid = (power * freqs).sum(1) / total
    env_ratios, _ = envelope_peaks(w, rpm, fs)
    return np.column_stack(time_feats + band_feats + [centroid, env_ratios])
