"""
Core Shazam-style audio fingerprinting algorithm.
Spectrogram → Constellation peaks → Hash pairs → DB match
"""
import numpy as np
from scipy.ndimage import maximum_filter
import librosa
import time

# ── Constants ────────────────────────────────────────────────────────────────
SR          = 22050   # sample rate
N_FFT       = 2048    # FFT window size
HOP         = 512     # hop length
NEIGHBORHOOD = 20     # local-max window (freq bins × time frames)
PEAK_THRESH  = -60    # dB cutoff — quieter peaks ignored
FAN_OUT      = 15     # anchor → this many target peaks
TIME_WINDOW  = 200    # max time-delta between anchor & target (frames)
MAX_PEAKS    = 5000   # keep only the top N amplitude peaks

# ── Audio loading ────────────────────────────────────────────────────────────
def load_audio(path, sr=SR, duration=None):
    """Load audio file → mono float32 array at `sr` Hz."""
    y, _ = librosa.load(path, sr=sr, mono=True, duration=duration)
    return y, sr

# ── Spectrogram ──────────────────────────────────────────────────────────────
def compute_spectrogram(y, sr=SR, n_fft=N_FFT, hop=HOP):
    """Return log-amplitude spectrogram in dB, shape (freq_bins, time_frames)."""
    D  = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop))
    Sdb = librosa.amplitude_to_db(D, ref=np.max)
    return Sdb

# ── Peak detection ───────────────────────────────────────────────────────────
def get_peaks(S_db, neighborhood=NEIGHBORHOOD, threshold=PEAK_THRESH, max_peaks=MAX_PEAKS):
    """
    Find local maxima in the spectrogram.
    Returns arrays (freq_idx, time_idx) of peak coordinates.
    """
    local_max    = maximum_filter(S_db, size=neighborhood) == S_db
    above_thresh = S_db > threshold
    peaks        = local_max & above_thresh

    freq_idx, time_idx = np.where(peaks)
    if len(freq_idx) == 0:
        return freq_idx, time_idx

    # Keep the strongest MAX_PEAKS
    amplitudes = S_db[freq_idx, time_idx]
    if len(amplitudes) > max_peaks:
        order    = np.argsort(amplitudes)[::-1][:max_peaks]
        freq_idx = freq_idx[order]
        time_idx = time_idx[order]

    return freq_idx, time_idx

# ── Hash generation ──────────────────────────────────────────────────────────
def make_hashes(freq_idx, time_idx, fan_out=FAN_OUT, time_window=TIME_WINDOW):
    """
    Pair each anchor peak with up to `fan_out` future peaks within `time_window`.
    Hash = (freq_anchor, freq_target, delta_t)  → tuple  (hashable, no collision risk)
    Returns list of  (hash_tuple, anchor_time_frame)
    """
    # Sort peaks by time (then freq)
    order = np.argsort(time_idx)
    t_arr = time_idx[order]
    f_arr = freq_idx[order]

    n      = len(t_arr)
    hashes = []

    for i in range(n):
        t1, f1 = int(t_arr[i]), int(f_arr[i])
        count  = 0
        for j in range(i + 1, n):
            t2, f2 = int(t_arr[j]), int(f_arr[j])
            dt = t2 - t1
            if dt <= 0:
                continue
            if dt > time_window:
                break
            hashes.append(((f1, f2, dt), t1))
            count += 1
            if count >= fan_out:
                break

    return hashes

# ── Full fingerprint pipeline ─────────────────────────────────────────────────
def fingerprint_file(path, duration=None):
    """
    Full pipeline for one audio file.
    Returns (hashes, S_db, freq_idx, time_idx, load_time_s)
    """
    t0       = time.perf_counter()
    y, sr    = load_audio(path, duration=duration)
    S_db     = compute_spectrogram(y, sr)
    freq_idx, time_idx = get_peaks(S_db)
    hashes   = make_hashes(freq_idx, time_idx)
    elapsed  = time.perf_counter() - t0
    return hashes, S_db, freq_idx, time_idx, elapsed

# ── Matching ─────────────────────────────────────────────────────────────────
def match(query_hashes, db):
    """
    Query the hash database.

    Returns:
        scores       : dict  song_name → best cluster count
        best_offsets : dict  song_name → winning offset (db_frame − query_frame)
        offset_map   : dict  song_name → {offset: count}
    """
    from collections import defaultdict

    # Accumulate votes: song → offset → count
    offset_map = defaultdict(lambda: defaultdict(int))

    for h, t_q in query_hashes:
        if h in db:
            for song, t_db in db[h]:
                offset = t_db - t_q
                offset_map[song][offset] += 1

    scores       = {}
    best_offsets = {}
    for song, offsets in offset_map.items():
        best_off          = max(offsets, key=offsets.get)
        scores[song]      = offsets[best_off]
        best_offsets[song] = best_off

    return scores, best_offsets, offset_map
