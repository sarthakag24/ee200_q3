"""
Fast parallel downloader for Google Drive songs using urllib + threading.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import urllib.request
import urllib.error
import os
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

SONGS_DIR = Path(r'c:\ee200_q3\app\songs')
SONGS_DIR.mkdir(parents=True, exist_ok=True)

FILES = {
    "A Day In The Life.mp3":               "1py5PxQ2-NsczhJoARK-dX4fana8iotXQ",
    "A Hard Day's Night.mp3":              "1L9SL6wjfE7rtyFhkkCk-0wYhKs0AFS2A",
    "Across The Universe.mp3":             "1gAWM8oCZAb1UjXN8UWcxPZ_G0N8cQYni",
    "Back In The U.S.S.R..mp3":            "1cT35ShMp7ur9bZgm88KUVcIL2O2rXjih",
    "Blackbird.mp3":                       "1CVUME6OvZ_n62e7_JLrjU85a3y6_ZLMW",
    "Bohemian Rhapsody.mp3":               "1-FbYD8LBlG-YVuw0yxBJ76v9AiBv1nzv",
    "Can't Buy Me Love.mp3":               "1xB476UTdo3dzUe5DNoTd6OfF1M9KsdNk",
    "Crazy Little Thing Called Love.mp3":  "15fvnUmi2kIU-W4I1HedUYgTfnC2awpBU",
    "Day Tripper.mp3":                     "19M2s4X1Z9aOV-u2KUPW2IR9FDeBdbGDQ",
    "Don't Stop Me Now.mp3":               "1GS4kZh2OVxogXgpLkvnVGc--uC6oA4ku",
    "Drive My Car.mp3":                    "1Jj07UVd8N4iBNmoNDc5N_wSy9bdqmpMr",
    "Eight Days A Week.mp3":               "1RAHG5snwFOe4fvx7DrK5zGIh0vL3lSDk",
    "Eleanor Rigby.mp3":                   "1SblFwcoip0AIb8JRvGlxUf_jkN27DBeU",
    "Get Back.mp3":                        "1xJOuVSSF20vlNp2E72-q3C3AMII4hQFh",
    "Hello, Goodbye.mp3":                  "1aqDhY8bVzwK-pJChgd5AWXOihQlrY2qk",
    "Help!.mp3":                           "1zMFQ0gPZiI7OLaV1HIlFz9AoPDX5dpYt",
    "Helter Skelter.mp3":                  "1z9yYDrov6d4_FrTxGT_FZm6XO66Siobu",
    "Hey Jude.mp3":                        "12C4-teeWMDccmiihZtamcFAcRiRMqMJ4",
    "I Am The Walrus.mp3":                 "1Xh-gtH5-QiiF3JyKFg0vLCr9DJbApSii",
    "I Saw Her Standing There.mp3":        "1dka88rQhPvEaJNiCUfJunYinaxKR7Ol6",
    "I Want It All.mp3":                   "1dMbnVUKvFtxffPh-v_9RfAcbjxxZ7-1m",
    "I Want To Hold Your Hand.mp3":        "1MvYOkXoeuwLJOlPO2mKOT5WG4FqJwTtf",
    "I'll Follow The Sun.mp3":             "1HYbIdaft4klwAccdWXW0dBYPJvZ29p28",
    "I've Got A Feeling.mp3":              "1mxRJToXfi8NTQNsZji6Gii7h85nS8EEm",
    "In My Life.mp3":                      "16GurU1pDaEbgCjUVapjrkGbhsNhSDZNS",
    "Killer Queen.mp3":                    "1TK570obz8rMUKwBfxOK46qJXKTPQ_QQC",
    "Let It Be.mp3":                       "1T6pMsTi9TMz-_rGef9Z4pY9Z5R0OviFM",
    "Love Me Do.mp3":                      "1X83x8_09gAGWbcPNSwtuWwr28gLJ14_Z",
    "Lucy In The Sky With Diamonds.mp3":   "1-viCk2LOFWRsSS6uZ5GZ1zvl6fLPrrgN",
    "Never Gonna Give You Up.mp3":         "1mPcEQZ7ccF3wQS-Uji97hzqj_Rweg7pJ",
    "Norwegian Wood (This Bird Has Flown).mp3": "1tVU7L50YdKiasn2SXAIJIiia5EQwGIG4",
    "Penny Lane.mp3":                      "12ddCCz6pY2IGxTwIX95TMuGzKUEXUMEC",
    "Radio Ga Ga.mp3":                     "17Bg2ZVoZ_oHfywU29GUNHbpuRSIVQhE5",
    "Revolution.mp3":                      "1-4u9xvqiLnS_V2IzrwGYvVitCbf97s1p",
    "Sgt. Pepper's Lonely Hearts Club Band.mp3": "1IlRXdFQJyMYqp5bzaN7_6vdGQztckVvy",
    "She Said She Said.mp3":               "131i7mMQ1cg9a-bk-CYHj1l5lZ0Gnk0IN",
    "Somebody To Love.mp3":                "1va3srczJSv-i95B--fO9aQtoa6xKdaMY",
    "Something.mp3":                       "1XeFr3bUc7-z44vOPQgcqIo2yplfeCjMy",
    "Taxman.mp3":                          "1MDaBxHeB1msDI1zPpANOUZwIKT76X1o2",
    "The Long And Winding Road.mp3":       "1SBdzWbbekSX4IwqrUj1pttqctGus8lrp",
    "Two Of Us.mp3":                       "1Ag515CqCtMUZuARXbfTPMtDVj6Vsj3cf",
    "Under Pressure.mp3":                  "1BGZ4aP57m430m8AAtPRvr7w3gXNMZi7J",
    "We Are The Champions.mp3":            "1vgAV4cXzIarUujCGmJ7PF21dhItILEJg",
    "We Can Work It Out.mp3":              "1QV12_zyfqJBadKhe6jW-iVjm2K0-Awfn",
    "We Will Rock You.mp3":                "1SmlrIme4iL4dYIQpigwU43BECOeoy_SH",
    "While My Guitar Gently Weeps.mp3":    "1IO3RZLp0yttGzI5vb7QwG9o7RlZ08gP5",
    "With A Little Help From My Friends.mp3": "1cSPLp8OCNSEb8a_rugg4Cb4A_J-2Ocyw",
    "Within You Without You.mp3":          "1GkP3higlrc8ZctPj4Odnjjh40T-AXQwy",
    "Yesterday.mp3":                       "1IPJl_pecKzWuc__kiUi6FTcYjCrPygfC",
    "You Really Got A Hold On Me.mp3":     "1F1RbGa2MhUDow92_hoA9SnITKutVvl9r",
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': '*/*',
}
MIN_SIZE = 500_000   # 500 KB minimum valid file
CHUNK    = 65536
lock     = threading.Lock()
done     = 0
total    = len(FILES)

def download_one(name, fid):
    global done
    out = SONGS_DIR / name
    if out.exists() and out.stat().st_size > MIN_SIZE:
        with lock:
            done += 1
            print(f"[{done:>2}/{total}] SKIP  {name}  ({out.stat().st_size/1e6:.1f} MB)")
        return name, True, "cached"

    url = f"https://drive.google.com/uc?export=download&id={fid}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=60) as resp:
            ct = resp.headers.get('Content-Type', '')
            # Check for virus warning redirect (HTML page)
            if 'text/html' in ct:
                # Need to follow the confirm link
                html = resp.read().decode('utf-8', errors='ignore')
                import re
                m = re.search(r'href="(/uc\?[^"]+confirm[^"]+)"', html)
                if m:
                    confirm_url = 'https://drive.google.com' + m.group(1).replace('&amp;', '&')
                    req2 = urllib.request.Request(confirm_url, headers=HEADERS)
                    with urllib.request.urlopen(req2, timeout=120) as resp2:
                        data = resp2.read()
                else:
                    data = b''
            else:
                data = resp.read()

        if len(data) > MIN_SIZE:
            out.write_bytes(data)
            with lock:
                done += 1
                print(f"[{done:>2}/{total}] OK    {name}  ({len(data)/1e6:.1f} MB)")
            return name, True, f"{len(data)/1e6:.1f} MB"
        else:
            with lock:
                done += 1
                print(f"[{done:>2}/{total}] SMALL {name}  ({len(data)} bytes) — may need manual download")
            return name, False, f"only {len(data)} bytes"

    except Exception as e:
        with lock:
            done += 1
            print(f"[{done:>2}/{total}] ERR   {name}  {e}")
        return name, False, str(e)

print(f"Downloading {total} songs to {SONGS_DIR} ...")
print("(Using 8 parallel threads)\n")

t0 = time.time()
failed = []
with ThreadPoolExecutor(max_workers=8) as pool:
    futures = {pool.submit(download_one, name, fid): name
               for name, fid in FILES.items()}
    for fut in as_completed(futures):
        name, ok, info = fut.result()
        if not ok:
            failed.append((name, info))

elapsed = time.time() - t0
print(f"\n{'='*55}")
print(f"Done in {elapsed:.0f}s  —  {total - len(failed)}/{total} songs downloaded")
if failed:
    print(f"\nFailed ({len(failed)}):")
    for n, reason in failed:
        print(f"  - {n}: {reason}")
