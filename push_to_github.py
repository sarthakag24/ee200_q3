"""
push_to_github.py
=================
Pushes the entire app/ directory to a new GitHub repository
using the GitHub Contents API — no git installation required.

USAGE:
    1. Create a Personal Access Token at:
       https://github.com/settings/tokens/new
       (tick the 'repo' scope, set any expiry)

    2. Edit the three variables below:
         GITHUB_USERNAME   = "your_username"
         GITHUB_TOKEN      = "ghp_xxxxxxxxxxxx"
         REPO_NAME         = "ee200-audio-fingerprinting"

    3. Run:
         python push_to_github.py
"""

import sys, os, base64, json, urllib.request, urllib.error
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# ── EDIT THESE ───────────────────────────────────────────────────────────────
GITHUB_USERNAME = "YOUR_USERNAME_HERE"
GITHUB_TOKEN    = "YOUR_PAT_TOKEN_HERE"
REPO_NAME       = "ee200-audio-fingerprinting"
REPO_DESC       = "EE200 Q3B: Shazam-style audio fingerprinting app built with Streamlit"
PRIVATE         = False   # set True if you want a private repo
# ─────────────────────────────────────────────────────────────────────────────

APP_DIR = Path(__file__).parent / "app"

# Files/dirs to SKIP (too large or not needed in repo)
SKIP_DIRS  = {"songs", "__pycache__", ".streamlit/__pycache__"}
SKIP_FILES = {"fingerprint_db.pkl"}   # 63 MB — too large for GitHub
# NOTE: song_meta.pkl (4.9 MB) IS included — it has thumbnails and metadata

# ────────────────────────────────────────────────────────────────────────────
API = "https://api.github.com"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "Content-Type": "application/json",
    "X-GitHub-Api-Version": "2022-11-28",
}

def gh_request(method, path, body=None):
    url  = f"{API}{path}"
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code

def create_repo():
    print(f"Creating repo '{REPO_NAME}'...")
    body = {"name": REPO_NAME, "description": REPO_DESC,
            "private": PRIVATE, "auto_init": False}
    resp, status = gh_request("POST", "/user/repos", body)
    if status == 201:
        print(f"  Created: {resp['html_url']}")
        return resp["html_url"]
    elif status == 422:
        print(f"  Repo already exists — will push to existing repo.")
        return f"https://github.com/{GITHUB_USERNAME}/{REPO_NAME}"
    else:
        print(f"  ERROR {status}: {resp}")
        sys.exit(1)

def push_file(rel_path: str, content_bytes: bytes):
    """Create or update a file via the GitHub Contents API."""
    b64 = base64.b64encode(content_bytes).decode()
    api_path = f"/repos/{GITHUB_USERNAME}/{REPO_NAME}/contents/{rel_path}"

    # Check if file exists (to get its sha for update)
    existing, status = gh_request("GET", api_path)
    sha = existing.get("sha") if status == 200 else None

    body = {
        "message": f"Add {rel_path}",
        "content": b64,
    }
    if sha:
        body["sha"] = sha
        body["message"] = f"Update {rel_path}"

    _, status = gh_request("PUT", api_path, body)
    return status in (200, 201)

def collect_files():
    """Walk app/ and return list of (relative_path_str, bytes) tuples."""
    files = []
    for path in sorted(APP_DIR.rglob("*")):
        if not path.is_file():
            continue
        # Skip rules
        rel = path.relative_to(APP_DIR)
        parts = rel.parts
        if any(part in SKIP_DIRS or part.startswith("__pycache__") for part in parts):
            continue
        if path.name in SKIP_FILES:
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        # Skip songs directory
        if "songs" in parts:
            continue
        files.append((rel.as_posix(), path.read_bytes()))
    return files

def main():
    if GITHUB_USERNAME == "YOUR_USERNAME_HERE":
        print("ERROR: Please edit GITHUB_USERNAME and GITHUB_TOKEN in this script first!")
        sys.exit(1)

    repo_url = create_repo()
    files    = collect_files()

    print(f"\nPushing {len(files)} files to {repo_url} ...")
    ok_count = 0
    for i, (rel, content) in enumerate(files, 1):
        size_kb = len(content) / 1024
        print(f"  [{i:>2}/{len(files)}]  {rel}  ({size_kb:.0f} KB) ... ", end="", flush=True)
        ok = push_file(rel, content)
        print("OK" if ok else "FAILED")
        if ok:
            ok_count += 1

    print(f"\n{'='*55}")
    print(f"Pushed {ok_count}/{len(files)} files")
    print(f"Repo URL : {repo_url}")
    print(f"\nNOTE: The songs/ folder and fingerprint_db.pkl were NOT pushed")
    print(f"(too large for GitHub). The app still works on Streamlit Cloud")
    print(f"because song_meta.pkl (thumbnails) IS included and the DB can")
    print(f"be rebuilt by running:  python build_db.py  after cloning.")
    print(f"\nTo deploy on Streamlit Community Cloud:")
    print(f"  1. Go to https://share.streamlit.io")
    print(f"  2. Connect your GitHub account")
    print(f"  3. Select repo: {GITHUB_USERNAME}/{REPO_NAME}")
    print(f"  4. Set Main file path: app.py")
    print(f"  5. Click Deploy!")

if __name__ == "__main__":
    main()
