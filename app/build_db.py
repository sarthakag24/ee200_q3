"""
Build the fingerprint database from the songs/ directory.
Run once locally; commit db/ to version control for Streamlit deployment.

Usage (from app/ directory):
    python build_db.py
"""
import os, pickle, io, time
import numpy as np
import soundfile as sf
from pathlib import Path
from PIL import Image

from fingerprinter import fingerprint_file, load_audio

# ── Paths ────────────────────────────────────────────────────────────────────
BASE        = Path(__file__).parent
SONGS_DIR   = BASE / "songs"
SAMPLES_DIR = BASE / "samples"
DB_DIR      = BASE / "db"
DB_FILE     = DB_DIR / "fingerprint_db.pkl"
META_FILE   = DB_DIR / "song_meta.pkl"

AUDIO_EXTS      = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".opus"}
SAMPLE_DURATION = 30
SAMPLE_START    = 30
NUM_SAMPLES     = 5

# ── Thumbnail generator (Pillow-based, no matplotlib DLLs needed) ─────────────
def make_thumbnail(freq_idx, time_idx, width=300, height=200):
    """
    Render constellation as a PNG thumbnail using Pillow.
    Dots are colored viridis-style (blue→green→yellow) by frequency.
    """
    img = Image.new("RGB", (width, height), (10, 14, 15))  # #0a0e0f

    if len(freq_idx) == 0:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    t_max = max(time_idx.max(), 1)
    f_max = max(freq_idx.max(), 1)

    # Viridis-ish palette: low freq → blue, mid → teal/green, high → yellow
    def viridis_color(v):  # v in [0,1]
        if v < 0.25:
            r = int(68  + v * 4 * (0))
            g = int(1   + v * 4 * (83))
            b = int(84  + v * 4 * (139 - 84))
        elif v < 0.5:
            t = (v - 0.25) * 4
            r = int(0   + t * 33)
            g = int(83  + t * (145 - 83))
            b = int(139 + t * (140 - 139))
        elif v < 0.75:
            t = (v - 0.5) * 4
            r = int(33  + t * (126 - 33))
            g = int(145 + t * (205 - 145))
            b = int(140 + t * (100 - 140))
        else:
            t = (v - 0.75) * 4
            r = int(126 + t * (253 - 126))
            g = int(205 + t * (231 - 205))
            b = int(100 + t * (37 - 100))
        return (min(255, r), min(255, g), min(255, b))

    px = img.load()
    # Downsample if too many peaks
    max_dots = 8000
    if len(freq_idx) > max_dots:
        idx = np.random.choice(len(freq_idx), max_dots, replace=False)
        f_s = freq_idx[idx]
        t_s = time_idx[idx]
    else:
        f_s, t_s = freq_idx, time_idx

    for f, t in zip(f_s, t_s):
        x = int(t / t_max * (width  - 2))
        y = int((1 - f / f_max) * (height - 2))   # flip y: low freq at bottom
        color = viridis_color(f / f_max)
        # 2×2 dot
        for dx in range(2):
            for dy in range(2):
                xi, yi = x + dx, y + dy
                if 0 <= xi < width and 0 <= yi < height:
                    px[xi, yi] = color

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ── Sample clip generator ─────────────────────────────────────────────────────
def generate_samples(songs):
    SAMPLES_DIR.mkdir(exist_ok=True)
    chosen = songs[:NUM_SAMPLES]
    sample_paths = []
    for i, song_path in enumerate(chosen, start=1):
        out_path = SAMPLES_DIR / f"sample{i}.wav"
        if out_path.exists() and out_path.stat().st_size > 100_000:
            print(f"  sample{i}.wav already exists, skipping.")
            sample_paths.append(out_path)
            continue
        try:
            y, sr = load_audio(str(song_path), duration=SAMPLE_DURATION + SAMPLE_START)
            # Trim leading SAMPLE_START seconds
            start_sample = int(SAMPLE_START * sr)
            y = y[start_sample:]
            sf.write(str(out_path), y, sr)
            print(f"  Generated sample{i}.wav  from '{song_path.stem}'")
            sample_paths.append(out_path)
        except Exception as e:
            print(f"  Could not generate sample{i}: {e}")
    return sample_paths

# ── Main build ────────────────────────────────────────────────────────────────
def build():
    DB_DIR.mkdir(exist_ok=True)
    SONGS_DIR.mkdir(exist_ok=True)

    songs = sorted([f for f in SONGS_DIR.iterdir() if f.suffix.lower() in AUDIO_EXTS])
    if not songs:
        print("No songs found in songs/. Please add audio files first.")
        return

    print(f"Found {len(songs)} songs.")
    print("Generating sample clips...")
    generate_samples(songs)

    db        = {}      # hash_tuple -> [(song_name, anchor_t), ...]
    song_meta = {}      # song_name  -> {hash_count, thumbnail, peaks_time, peaks_freq, n_peaks}

    t_start = time.time()
    for idx, song_path in enumerate(songs, start=1):
        song_name = song_path.stem
        print(f"\n[{idx:>2}/{len(songs)}] Indexing: {song_name}")
        try:
            t0 = time.perf_counter()
            hashes, S_db, freq_idx, time_idx, _ = fingerprint_file(str(song_path))
            elapsed = time.perf_counter() - t0

            for h, t in hashes:
                if h not in db:
                    db[h] = []
                db[h].append((song_name, t))

            thumb = make_thumbnail(freq_idx, time_idx)

            song_meta[song_name] = {
                "hash_count":  len(hashes),
                "thumbnail":   thumb,
                "n_peaks":     len(freq_idx),
                "peaks_time":  time_idx,
                "peaks_freq":  freq_idx,
            }
            print(f"   -> {len(hashes):>8,} hashes | {len(freq_idx):>6,} peaks | {elapsed:.1f}s")

        except Exception as e:
            print(f"   ERROR: {e}")

    total = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"Indexed {len(song_meta)} songs in {total:.1f}s")
    print(f"DB: {len(db):,} unique hashes")
    print("Saving...")

    with open(DB_FILE,   "wb") as f:
        pickle.dump(db,        f, protocol=pickle.HIGHEST_PROTOCOL)
    with open(META_FILE, "wb") as f:
        pickle.dump(song_meta, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"Done!")
    print(f"  db/fingerprint_db.pkl  {DB_FILE.stat().st_size/1e6:.1f} MB")
    print(f"  db/song_meta.pkl       {META_FILE.stat().st_size/1e6:.1f} MB")

if __name__ == "__main__":
    build()
