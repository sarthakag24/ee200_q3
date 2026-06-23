"""
setup_songs.py  —  Download the song database from Google Drive and build the fingerprint DB.

Usage (run from the app/ directory, or from the project root):
    python setup_songs.py

Requires: gdown  (pip install gdown)
"""
import subprocess
import sys
import os
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent / "app"   # app/ lives next to this script
SONGS_DIR  = SCRIPT_DIR / "songs"

# ── Google Drive folder ID ────────────────────────────────────────────────
GDRIVE_FOLDER_ID = "1UV96lMDwvP-N5Zur6tOPx5OwA6vaDs8N"

def pip_install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

def download_songs():
    SONGS_DIR.mkdir(parents=True, exist_ok=True)

    # Check if we already have songs
    existing = list(SONGS_DIR.glob("*.mp3")) + list(SONGS_DIR.glob("*.wav")) + \
               list(SONGS_DIR.glob("*.flac")) + list(SONGS_DIR.glob("*.ogg")) + \
               list(SONGS_DIR.glob("*.m4a"))
    if existing:
        print(f"Found {len(existing)} existing songs in songs/ — skipping download.")
        return True

    print("Installing gdown for Google Drive download…")
    pip_install("gdown")

    import gdown
    url = f"https://drive.google.com/drive/folders/{GDRIVE_FOLDER_ID}"
    print(f"\nDownloading song library from Google Drive…")
    print(f"URL: {url}\n")

    try:
        gdown.download_folder(
            url=url,
            output=str(SONGS_DIR),
            quiet=False,
            use_cookies=False,
        )
        return True
    except Exception as e:
        print(f"\nERROR downloading from Google Drive: {e}")
        print("\nPlease download the songs manually from:")
        print(f"  https://drive.google.com/drive/folders/{GDRIVE_FOLDER_ID}")
        print(f"and place the audio files in:  {SONGS_DIR.resolve()}")
        return False

def install_requirements():
    req_file = SCRIPT_DIR / "requirements.txt"
    print("Installing Python requirements…")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r",
                           str(req_file), "-q"])

def build_db():
    build_script = SCRIPT_DIR / "build_db.py"
    print("\nBuilding fingerprint database…")
    subprocess.check_call([sys.executable, str(build_script)],
                          cwd=str(SCRIPT_DIR))

def main():
    print("=" * 60)
    print("  EE200 Audio Fingerprinting — Setup")
    print("=" * 60)
    install_requirements()
    ok = download_songs()
    if ok:
        build_db()
        print("\n✓ Setup complete!")
        print(f"  Run: streamlit run {SCRIPT_DIR / 'app.py'}")
    else:
        print("\n! Please add songs manually then run:")
        print(f"  python {SCRIPT_DIR / 'build_db.py'}")

if __name__ == "__main__":
    main()
