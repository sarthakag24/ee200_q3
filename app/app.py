"""
EE200: Audio Fingerprinting — Streamlit App (Q3B)
Shazam-style song identifier with dark flashy UI.
Uses plotly for all charts (pure Python, no DLL issues).
"""
import streamlit as st
import streamlit.components.v1 as components
import pickle
import numpy as np
import io, time, tempfile, os
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

from fingerprinter import (
    fingerprint_file, match,
    compute_spectrogram, get_peaks, make_hashes, load_audio,
    SR, N_FFT, HOP
)

# ════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="EE200: Audio Fingerprinting",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ════════════════════════════════════════════════════════════════════════════
#  PATHS
# ════════════════════════════════════════════════════════════════════════════
BASE        = Path(__file__).parent
DB_FILE     = BASE / "db" / "fingerprint_db.pkl"
META_FILE   = BASE / "db" / "song_meta.pkl"
SAMPLES_DIR = BASE / "samples"

# ════════════════════════════════════════════════════════════════════════════
#  THEME COLORS
# ════════════════════════════════════════════════════════════════════════════
BG      = "#0a0e0f"
BG2     = "#111518"
BG3     = "#181d20"
BORDER  = "#1e2528"
TEAL    = "#00e5c0"
TEAL2   = "#00b89a"
ORANGE  = "#f59e0b"
TEXT    = "#d4d8db"
TEXTDIM = "#6b7280"

# ════════════════════════════════════════════════════════════════════════════
#  COLOR HELPERS  (plotly 5 & 6 compatible — no px.colors.sample_colorscale)
# ════════════════════════════════════════════════════════════════════════════
def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def viridis_rgb(v):
    """Manual viridis approximation: 0→purple, 0.5→teal, 1→yellow."""
    stops = [
        (0.00, (68,  1,  84)),
        (0.25, (58, 82, 139)),
        (0.50, (32, 144, 140)),
        (0.75, (94, 201, 97)),
        (1.00, (253, 231, 37)),
    ]
    v = max(0.0, min(1.0, v))
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= v <= t1:
            t = (v - t0) / (t1 - t0)
            r, g, b = _lerp(c0, c1, t)
            return f"rgb({r},{g},{b})"
    return "rgb(253,231,37)"

def plasma_rgb(v):
    """Manual plasma approximation: 0→dark purple, 0.5→orange, 1→yellow."""
    stops = [
        (0.00, (13,   8, 135)),
        (0.25, (126, 3, 167)),
        (0.50, (203, 71, 119)),
        (0.75, (248, 149, 64)),
        (1.00, (240, 249, 33)),
    ]
    v = max(0.0, min(1.0, v))
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= v <= t1:
            t = (v - t0) / (t1 - t0)
            r, g, b = _lerp(c0, c1, t)
            return f"rgb({r},{g},{b})"
    return "rgb(240,249,33)"

def make_colors(arr, palette="viridis"):
    """Map a normalized float array to color strings."""
    fn = viridis_rgb if palette == "viridis" else plasma_rgb
    vmax = arr.max() + 1
    return [fn(float(v) / vmax) for v in arr]

# ════════════════════════════════════════════════════════════════════════════
#  PLOTLY DARK LAYOUT BASE
# ════════════════════════════════════════════════════════════════════════════
def dark_layout(title="", xlab="", ylab="", h=300):
    return dict(
        paper_bgcolor=BG,
        plot_bgcolor=BG2,
        font=dict(color=TEXTDIM, size=11, family="JetBrains Mono, monospace"),
        title=dict(text=title, font=dict(color=TEXT, size=13), x=0.02, xanchor="left"),
        xaxis=dict(
            title=xlab, gridcolor=BORDER, zerolinecolor=BORDER,
            tickfont=dict(size=9), title_font=dict(size=10),
        ),
        yaxis=dict(
            title=ylab, gridcolor=BORDER, zerolinecolor=BORDER,
            tickfont=dict(size=9), title_font=dict(size=10),
        ),
        margin=dict(l=55, r=20, t=40, b=45),
        height=h,
        showlegend=False,
    )

# ════════════════════════════════════════════════════════════════════════════
#  CUSTOM CSS
# ════════════════════════════════════════════════════════════════════════════
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --bg:#0a0e0f; --bg2:#111518; --bg3:#181d20; --border:#1e2528;
    --teal:#00e5c0; --teal2:#00b89a; --orange:#f59e0b;
    --text:#d4d8db; --dim:#6b7280;
    --mono:'JetBrains Mono',monospace; --sans:'Inter',sans-serif;
}

html,body,[data-testid="stAppViewContainer"],[data-testid="stApp"],
.main,.block-container{
    background-color:var(--bg) !important;
    color:var(--text) !important;
    font-family:var(--sans) !important;
}
#MainMenu,footer,header,
[data-testid="stDecoration"],
[data-testid="stSidebar"]{ display:none !important; }

::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:var(--bg2)}
::-webkit-scrollbar-thumb{background:var(--teal2);border-radius:3px}

.block-container{
    padding:1.5rem 2.5rem 4rem !important;
    max-width:1200px !important;
}

/* ── Tabs ── */
[data-testid="stTabs"]>div:first-child{
    border-bottom:1px solid var(--border) !important; gap:0 !important;
}
button[data-baseweb="tab"]{
    background:transparent !important; color:var(--dim) !important;
    font-family:var(--mono) !important; font-size:.72rem !important;
    letter-spacing:.08em !important; padding:.55rem 1.1rem !important;
    border:none !important; border-bottom:2px solid transparent !important;
    transition:color .2s,border-color .2s !important;
}
button[data-baseweb="tab"]:hover{ color:var(--teal) !important; }
button[data-baseweb="tab"][aria-selected="true"]{
    color:var(--teal) !important;
    border-bottom:2px solid var(--teal) !important;
    background:transparent !important;
}
[data-testid="stTabPanel"]{
    padding-top:1.2rem !important; background:transparent !important;
}

/* ── Primary buttons ── */
.stButton>button{
    background:var(--teal) !important; color:#000 !important;
    font-family:var(--sans) !important; font-weight:600 !important;
    font-size:.85rem !important; border:none !important;
    border-radius:4px !important; padding:.45rem 1.3rem !important;
    transition:background .15s,transform .1s !important;
}
.stButton>button:hover{
    background:var(--teal2) !important; transform:translateY(-1px) !important;
}
.stButton>button:active{ transform:translateY(0) !important; }

/* ── "Try" ghost buttons (smaller) ── */
button[kind="secondary"]{
    background:transparent !important;
    color:var(--teal) !important;
    border:1px solid var(--teal2) !important;
    font-size:.78rem !important;
    padding:.35rem .9rem !important;
}
button[kind="secondary"]:hover{
    background:var(--teal2) !important; color:#000 !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"]{
    background:var(--bg2) !important;
    border:1px dashed var(--border) !important;
    border-radius:6px !important;
}
[data-testid="stFileUploaderDropzone"]{
    background:var(--bg3) !important;
    border:1px dashed var(--teal2) !important;
    border-radius:6px !important;
}
[data-testid="stFileUploaderDropzone"] span{
    color:var(--dim) !important; font-size:.82rem !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] span{ color:var(--dim) !important; }

/* ── Audio player ── */
audio{
    filter:invert(.88) hue-rotate(155deg) brightness(.85) !important;
    height:30px !important; width:100% !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"]>button{
    background:transparent !important; color:var(--teal) !important;
    border:1px solid var(--teal2) !important; font-size:.8rem !important;
}
[data-testid="stDownloadButton"]>button:hover{
    background:var(--teal2) !important; color:#000 !important;
}

/* ── Spinner ── */
.stSpinner>div{ border-top-color:var(--teal) !important; }

/* ── Text ── */
.stMarkdown p,p{ color:var(--text) !important; }
h1,h2,h3,h4{ color:#fff !important; font-family:var(--sans) !important; }
hr{ border-color:var(--border) !important; margin:1.2rem 0 !important; }
code{
    background:var(--bg3) !important; color:var(--teal) !important;
    border:1px solid var(--border) !important; border-radius:3px !important;
    padding:0 4px !important; font-family:var(--mono) !important;
    font-size:.82em !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"]{
    background:var(--bg2) !important;
    border:1px solid var(--border) !important;
    border-radius:6px !important;
}

/* ── Selected sample pill ── */
.sample-active{
    display:inline-block;
    background:#0d2a26;
    border:1px solid var(--teal2);
    border-radius:20px;
    padding:.25rem .9rem;
    font-family:var(--mono);
    font-size:.75rem;
    color:var(--teal);
    margin:.6rem 0 1rem;
}
</style>
"""

# ════════════════════════════════════════════════════════════════════════════
#  CURSOR TRAIL
# ════════════════════════════════════════════════════════════════════════════
CURSOR_JS = """
<div id="_cur_host"></div>
<style>*{cursor:none !important}</style>
<script>
(function(){
  const N=22,C=[0,229,192];
  const dots=[];
  let mx=-300,my=-300;
  for(let i=0;i<N;i++){
    const el=document.createElement('div');
    const t=i/N,sz=Math.max(2,10*(1-t*.7)),op=1-t*.88;
    Object.assign(el.style,{
      position:'fixed',borderRadius:'50%',pointerEvents:'none',
      zIndex:'2147483647',transform:'translate(-50%,-50%)',
      width:sz+'px',height:sz+'px',
      background:'rgba('+C[0]+','+C[1]+','+C[2]+','+op+')',
      boxShadow:i===0?'0 0 8px 3px rgba('+C.join(',')+',0.5)':'none',
    });
    document.body.appendChild(el);
    dots.push({el,x:-300,y:-300});
  }
  document.addEventListener('mousemove',e=>{mx=e.clientX;my=e.clientY;});
  (function anim(){
    dots[0].x+=(mx-dots[0].x)*.38;dots[0].y+=(my-dots[0].y)*.38;
    dots[0].el.style.left=dots[0].x+'px';dots[0].el.style.top=dots[0].y+'px';
    for(let i=1;i<N;i++){
      const sp=Math.max(.04,.28-i*.008);
      dots[i].x+=(dots[i-1].x-dots[i].x)*sp;
      dots[i].y+=(dots[i-1].y-dots[i].y)*sp;
      dots[i].el.style.left=dots[i].x+'px';dots[i].el.style.top=dots[i].y+'px';
    }
    requestAnimationFrame(anim);
  })();
})();
</script>
"""

HEADER_HTML = """
<div style="display:flex;align-items:center;gap:.85rem;margin-bottom:.2rem;padding-top:.5rem">
  <div style="width:44px;height:44px;border-radius:10px;flex-shrink:0;
    background:linear-gradient(135deg,#00e5c0,#0097a7);
    display:flex;align-items:center;justify-content:center;
    box-shadow:0 0 18px rgba(0,229,192,.35);">
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <rect x="2"  y="9"  width="2" height="6"  rx="1" fill="#000"/>
      <rect x="6"  y="6"  width="2" height="12" rx="1" fill="#000"/>
      <rect x="10" y="4"  width="2" height="16" rx="1" fill="#000"/>
      <rect x="14" y="7"  width="2" height="10" rx="1" fill="#000"/>
      <rect x="18" y="10" width="2" height="4"  rx="1" fill="#000"/>
    </svg>
  </div>
  <div>
    <div style="font-family:'Inter',sans-serif;font-size:1.7rem;font-weight:700;
                color:#fff;line-height:1.1">
      EE<span style="color:#00e5c0">200</span>: Audio Fingerprinting
    </div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:.62rem;
                letter-spacing:.12em;color:#6b7280;margin-top:2px">
      SIGNALS, SYSTEMS &amp; NETWORKS &nbsp;&middot;&nbsp; PROJECT DEMO
    </div>
  </div>
</div>
<p style="font-size:.85rem;color:#6b7280;margin:.3rem 0 1.2rem">
  Index a library of songs as spectrogram fingerprints, then identify any short clip against it.
</p>
"""

# ════════════════════════════════════════════════════════════════════════════
#  DATABASE LOADER
# ════════════════════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner="Loading fingerprint database…")
def load_db():
    if not DB_FILE.exists():
        # Check if split part files exist and reconstruct in-memory
        parts = sorted(list(DB_FILE.parent.glob("fingerprint_db.pkl.part*")))
        if parts:
            try:
                combined = bytearray()
                for part in parts:
                    with open(part, "rb") as f:
                        combined.extend(f.read())
                db = pickle.loads(combined)
                with open(META_FILE, "rb") as f:
                    song_meta = pickle.load(f)
                return db, song_meta
            except Exception as e:
                st.error(f"Error reconstructing database from parts: {e}")
        return None, None
    with open(DB_FILE,   "rb") as f: db        = pickle.load(f)
    with open(META_FILE, "rb") as f: song_meta = pickle.load(f)
    return db, song_meta

# ════════════════════════════════════════════════════════════════════════════
#  PLOTLY CHART BUILDERS
# ════════════════════════════════════════════════════════════════════════════
def chart_spectrogram(S_db):
    n_freq, n_time = S_db.shape
    freqs = np.linspace(0, SR / 2000, n_freq)
    times = np.arange(n_time) * HOP / SR
    fig = go.Figure(go.Heatmap(
        z=S_db, x=times.tolist(), y=freqs.tolist(),
        colorscale="Hot", zmin=-80, zmax=0,
        showscale=True,
        colorbar=dict(
            title=dict(text="dB", font=dict(size=10, color=TEXTDIM)),
            thickness=10, len=0.85,
            tickfont=dict(size=9, color=TEXTDIM),
        ),
    ))
    fig.update_layout(**dark_layout("Spectrogram (query clip)", "time (s)", "freq (kHz)", h=290))
    return fig

def chart_constellation(freq_idx, time_idx, n_time=None):
    if len(freq_idx) == 0:
        fig = go.Figure()
        fig.update_layout(**dark_layout("Constellation (no peaks found)", h=290))
        return fig
    MAX = 5000
    if len(freq_idx) > MAX:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(freq_idx), MAX, replace=False)
        fx, tx = freq_idx[idx], time_idx[idx]
    else:
        fx, tx = freq_idx, time_idx
    colors = make_colors(fx, "viridis")
    fig = go.Figure(go.Scatter(
        x=tx.tolist(), y=fx.tolist(), mode="markers",
        marker=dict(color=colors, size=2.5, opacity=0.85),
    ))
    if n_time:
        fig.update_xaxes(range=[0, n_time])
    fig.update_layout(**dark_layout(
        f"Constellation  ({len(freq_idx):,} peaks)",
        "time (frames)", "freq bin", h=290))
    return fig

def chart_full_song_fp(meta_entry, best_offset, query_n_frames):
    pt = meta_entry.get("peaks_time", np.array([]))
    pf = meta_entry.get("peaks_freq", np.array([]))
    fig = go.Figure()
    if len(pt) > 0:
        MAX = 8000
        if len(pt) > MAX:
            rng = np.random.default_rng(0)
            idx = rng.choice(len(pt), MAX, replace=False)
            pt2, pf2 = pt[idx], pf[idx]
        else:
            pt2, pf2 = pt, pf
        colors = make_colors(pf2, "plasma")
        fig.add_trace(go.Scatter(
            x=pt2.tolist(), y=pf2.tolist(), mode="markers",
            marker=dict(color=colors, size=2, opacity=0.55),
        ))
    x0 = int(best_offset)
    x1 = int(best_offset + query_n_frames)
    fig.add_vrect(
        x0=x0, x1=x1,
        fillcolor=TEAL, opacity=0.12,
        line_color=TEAL, line_width=1.2,
    )
    fig.add_annotation(
        x=(x0 + x1) / 2, y=1, yref="paper",
        text="query window", showarrow=False,
        font=dict(color=TEAL, size=10),
        bgcolor="rgba(0,229,192,0.1)",
        bordercolor=TEAL, borderwidth=1,
    )
    fig.update_layout(**dark_layout(
        "Full fingerprint of matched song", "time (frames)", "freq bin", h=290))
    return fig

def chart_offset_histogram(offset_map_song, best_offset, best_count):
    if not offset_map_song:
        return go.Figure().update_layout(**dark_layout("Alignment spike", h=290))
    offsets = np.array(list(offset_map_song.keys()), dtype=float)
    counts  = np.array(list(offset_map_song.values()), dtype=float)

    span = offsets.max() - offsets.min()
    bin_size = max(1, int(span / 200))
    bin_min  = (int(offsets.min()) // bin_size) * bin_size
    bin_max  = (int(offsets.max()) // bin_size + 1) * bin_size
    bins     = np.arange(bin_min, bin_max + bin_size, bin_size)
    binned   = np.zeros(len(bins) - 1)
    for o, c in zip(offsets, counts):
        idx = int((o - bin_min) // bin_size)
        if 0 <= idx < len(binned):
            binned[idx] += c
    centers = ((bins[:-1] + bins[1:]) / 2).tolist()

    peak_idx   = int(np.argmax(binned))
    bar_colors = [ORANGE if i == peak_idx else "#1e2a2e" for i in range(len(centers))]

    fig = go.Figure(go.Bar(
        x=centers, y=binned.tolist(),
        marker_color=bar_colors, marker_line_width=0,
    ))
    if centers:
        fig.add_annotation(
            x=centers[peak_idx], y=float(binned[peak_idx]),
            text=f"<b>{int(best_count):,} hashes</b><br>align here",
            showarrow=True, arrowhead=2, arrowcolor=ORANGE, arrowwidth=1.5,
            font=dict(color=ORANGE, size=11), ax=70, ay=-45,
        )
        noise = float(np.median(binned[binned > 0])) if (binned > 0).any() else 1
        fig.add_annotation(
            x=centers[-1], y=max(noise * 2, 1),
            text="chance matches<br>(noise floor)",
            showarrow=False, font=dict(color=TEXTDIM, size=9), xanchor="right",
        )
    fig.update_layout(**dark_layout(
        "The alignment spike",
        "time offset  (database frame − query frame)",
        "# hashes", h=290))
    return fig

# ════════════════════════════════════════════════════════════════════════════
#  HTML HELPERS
# ════════════════════════════════════════════════════════════════════════════
def pipeline_html(times_ms, details):
    steps = [("①","SPECTROGRAM"),("②","CONSTELLATION"),
             ("③","HASHING"),("④","DB LOOKUP"),("⑤","SCORING")]
    total = sum(times_ms)
    html  = ('<div style="display:flex;background:#111518;border:1px solid #1e2528;'
             'border-radius:8px;overflow:hidden;margin:1rem 0">')
    for (num, label), ms, det in zip(steps, times_ms, details):
        html += (f'<div style="flex:1;padding:.7rem .4rem;text-align:center;border-right:1px solid #1e2528">'
                 f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:.58rem;color:#6b7280">{num}</div>'
                 f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:.55rem;color:#6b7280;'
                 f'text-transform:uppercase;letter-spacing:.06em;margin-bottom:2px">{label}</div>'
                 f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:1rem;'
                 f'font-weight:600;color:#00e5c0">{ms:.0f} ms</div>'
                 f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:.58rem;'
                 f'color:#6b7280;margin-top:1px">{det}</div>'
                 f'</div>')
    html += (f'<div style="align-self:center;padding:0 1rem;font-family:\'JetBrains Mono\',monospace;'
             f'font-size:.7rem;color:#6b7280;white-space:nowrap">'
             f'total&nbsp;<b style="color:#00e5c0">{total:.0f} ms</b></div>'
             f'</div>')
    return html

def match_card_html(winner, win_score, runner_up, multiplier):
    return (f'<div style="background:#111518;border:1px solid #00b89a;border-left:3px solid #00e5c0;'
            f'border-radius:8px;padding:1.1rem 1.4rem;margin:.8rem 0">'
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:.63rem;letter-spacing:.12em;'
            f'color:#00e5c0;text-transform:uppercase;margin-bottom:.35rem">&#10003; Match Found</div>'
            f'<div style="font-size:1.9rem;font-weight:700;color:#fff;margin-bottom:.2rem;line-height:1.15">'
            f'{winner}</div>'
            f'<div style="font-size:.8rem;color:#6b7280">'
            f'cluster score <b style="color:#00e5c0">{win_score:,}</b> &nbsp;&middot;&nbsp;'
            f'<b style="color:#00e5c0">{multiplier:.0f}&times;</b> the runner-up'
            f'<span style="color:#6b7280"> ({runner_up})</span></div>'
            f'</div>')

def candidate_bars_html(scores, winner, max_show=5):
    items = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:max_show]
    top   = items[0][1] if items else 1
    html  = '<div style="margin:.4rem 0 1rem">'
    for song, score in items:
        pct     = (score / top) * 100 if top else 0
        is_win  = (song == winner)
        bcol    = "#00e5c0" if is_win else "#1e2528"
        ncol    = "#ffffff" if is_win else "#6b7280"
        html += (f'<div style="display:flex;align-items:center;gap:.7rem;padding:.3rem 0;font-size:.82rem">'
                 f'<div style="flex:0 0 200px;color:{ncol};overflow:hidden;text-overflow:ellipsis;'
                 f'white-space:nowrap" title="{song}">{song}</div>'
                 f'<div style="flex:1;background:#181d20;border-radius:2px;height:6px">'
                 f'<div style="width:{pct:.1f}%;height:6px;border-radius:2px;background:{bcol}"></div></div>'
                 f'<div style="flex:0 0 50px;text-align:right;font-family:\'JetBrains Mono\',monospace;'
                 f'font-size:.75rem;color:#6b7280">{score:,}</div>'
                 f'</div>')
    html += '</div>'
    return html

def step_html(num, tag, title, body=""):
    return (f'<div style="display:flex;align-items:baseline;gap:.5rem;margin:2rem 0 .2rem;'
            f'padding-bottom:.5rem;border-bottom:1px solid #1e2528">'
            f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:.63rem;color:#00e5c0;'
            f'text-transform:uppercase;letter-spacing:.1em">STEP {num}</span>'
            f'<span style="color:#6b7280;font-size:.63rem">&middot;</span>'
            f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:.63rem;color:#6b7280;'
            f'text-transform:uppercase;letter-spacing:.1em">{tag}</span></div>'
            f'<div style="font-size:1.05rem;font-weight:600;color:#fff;margin:.2rem 0 .5rem">{title}</div>'
            + (f'<div style="font-size:.82rem;color:#6b7280;line-height:1.65;margin-bottom:.8rem">'
               f'{body}</div>' if body else ''))

def slabel(text):
    return (f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:.63rem;letter-spacing:.12em;'
            f'color:#6b7280;text-transform:uppercase;margin-bottom:.9rem">{text}</div>')

# ════════════════════════════════════════════════════════════════════════════
#  IDENTIFY PIPELINE
# ════════════════════════════════════════════════════════════════════════════
def run_identify(audio_path, db, song_meta):
    t0    = time.perf_counter()
    y, sr = load_audio(audio_path)
    S_db  = compute_spectrogram(y, sr)
    t_spec = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    freq_idx, time_idx = get_peaks(S_db)
    t_const = (time.perf_counter() - t0) * 1000

    t0     = time.perf_counter()
    hashes = make_hashes(freq_idx, time_idx)
    t_hash = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    scores, best_offsets, offset_map = match(hashes, db)
    t_lookup = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    if not scores:
        return {"winner": None}

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    winner     = sorted_scores[0][0]
    win_score  = sorted_scores[0][1]
    runner_up  = sorted_scores[1][0] if len(sorted_scores) > 1 else "—"
    run_score  = sorted_scores[1][1] if len(sorted_scores) > 1 else 1
    multiplier = win_score / max(run_score, 1)
    t_score    = (time.perf_counter() - t0) * 1000

    return {
        "winner": winner, "win_score": win_score,
        "runner_up": runner_up, "runner_score": run_score,
        "multiplier": multiplier,
        "scores": dict(sorted_scores),
        "best_offset":    best_offsets[winner],
        "offset_map":     dict(offset_map[winner]),
        "S_db":           S_db,
        "freq_idx":       freq_idx,
        "time_idx":       time_idx,
        "hashes":         hashes,
        "n_query_frames": S_db.shape[1],
        "times_ms": [t_spec, t_const, t_hash, t_lookup, t_score],
        "details":  [
            f"{S_db.shape[0]}×{S_db.shape[1]}",
            f"{len(freq_idx):,} peaks",
            f"{len(hashes):,} hashes",
            f"{len(scores)} tracks",
            f"offset {best_offsets[winner]}",
        ],
    }

def show_results(result, song_meta):
    if not result or result.get("winner") is None:
        st.error("No match found in the database.")
        return

    winner     = result["winner"]
    win_score  = result["win_score"]
    runner_up  = result.get("runner_up", "—")
    multiplier = result["multiplier"]

    st.markdown(pipeline_html(result["times_ms"], result["details"]), unsafe_allow_html=True)
    st.markdown(match_card_html(winner, win_score, runner_up, multiplier), unsafe_allow_html=True)
    st.markdown(slabel("CANDIDATE SCORES"), unsafe_allow_html=True)
    st.markdown(candidate_bars_html(result["scores"], winner), unsafe_allow_html=True)

    # Step 1
    st.markdown(step_html("1", "FEATURE EXTRACTION", "From spectrogram to constellation",
        f"The clip was converted into a time-frequency map (left); brighter means louder at that "
        f"frequency and moment. From that rich image, only the "
        f"<b style='color:#00e5c0'>{len(result['freq_idx']):,} most prominent peaks</b> were kept (right). "
        f"Discarding amplitude and phase makes the fingerprint robust to EQ, volume changes, and noise."),
        unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(chart_spectrogram(result["S_db"]),
                        use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.plotly_chart(chart_constellation(result["freq_idx"], result["time_idx"],
                                            result["S_db"].shape[1]),
                        use_container_width=True, config={"displayModeBar": False})

    # Step 2
    st.markdown(step_html("2", "DATABASE SEARCH", "Where in the song?",
        f"The <b style='color:#00e5c0'>{len(result['hashes']):,} fingerprint hashes</b> were looked up "
        f"against every indexed track. Below is the full fingerprint of "
        f"<b style='color:#00e5c0'>{winner}</b> reconstructed from the database — each dot is a stored hash "
        f"anchor. The highlighted window is exactly where the query clip sits inside the full song."),
        unsafe_allow_html=True)
    if winner in song_meta:
        st.plotly_chart(
            chart_full_song_fp(song_meta[winner], result["best_offset"], result["n_query_frames"]),
            use_container_width=True, config={"displayModeBar": False})

    # Step 3
    st.markdown(step_html("3", "THE PROOF", "The alignment spike",
        f"Every matched hash votes for a time offset (database frame minus query frame). Chance matches "
        f"scatter votes randomly, forming a flat noise floor. A genuine match makes them converge: "
        f"<b style='color:#00e5c0'>{win_score:,} hashes agreed on a single offset</b>. "
        f"That spike cannot be a coincidence."),
        unsafe_allow_html=True)
    st.plotly_chart(
        chart_offset_histogram(result["offset_map"], result["best_offset"], result["win_score"]),
        use_container_width=True, config={"displayModeBar": False})

# ════════════════════════════════════════════════════════════════════════════
#  SESSION STATE INIT
# ════════════════════════════════════════════════════════════════════════════
def init_state():
    defaults = {
        "selected_sample": None,   # Path of sample chosen via Try button
        "last_result":     None,   # Last identify result dict
        "result_label":    "",     # Filename/label for last result
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ════════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════════
def main():
    init_state()

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    components.html(CURSOR_JS, height=0, scrolling=False)
    st.markdown(HEADER_HTML, unsafe_allow_html=True)

    db, song_meta = load_db()

    tab_lib, tab_id, tab_batch = st.tabs(["♦  LIBRARY", "⊙  IDENTIFY", "⊟  BATCH"])

    # ════════════════════════════════════════════════════
    #  TAB 1 — LIBRARY
    # ════════════════════════════════════════════════════
    with tab_lib:
        st.markdown(slabel("LIBRARY"), unsafe_allow_html=True)

        if db is None:
            st.markdown(
                '<div style="background:#111518;border:1px dashed #1e2528;border-radius:8px;'
                'padding:2.5rem;text-align:center;margin-top:1rem">'
                '<div style="font-family:\'JetBrains Mono\',monospace;font-size:.8rem;color:#6b7280">'
                'Song indexing is managed by the admin.<br>'
                'Drop a clip in the Identify tab to test the library.</div></div>'
                '<div style="color:#ef4444;font-size:.8rem;margin-top:.8rem">'
                'Database not found — run <code>python build_db.py</code></div>',
                unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="background:#111518;border:1px dashed #1e2528;border-radius:8px;'
                'padding:1.2rem;text-align:center;margin-bottom:1.5rem">'
                '<div style="font-family:\'JetBrains Mono\',monospace;font-size:.78rem;color:#6b7280">'
                'Song indexing is managed by the admin.<br>'
                'Drop a clip in the Identify tab to test the library.</div></div>',
                unsafe_allow_html=True)
            st.markdown(slabel("IN THE DATABASE"), unsafe_allow_html=True)

            songs = sorted(song_meta.keys())
            COLS  = 4
            for row_start in range(0, len(songs), COLS):
                cols = st.columns(COLS)
                for ci, song in enumerate(songs[row_start:row_start + COLS]):
                    meta = song_meta[song]
                    with cols[ci]:
                        if meta.get("thumbnail"):
                            st.image(meta["thumbnail"], use_container_width=True)
                        st.markdown(
                            f'<div style="padding:.25rem 0 1rem">'
                            f'<div style="font-size:.78rem;font-weight:500;color:#d4d8db;'
                            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="{song}">'
                            f'{song}</div>'
                            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:.68rem;'
                            f'color:#6b7280">{meta["hash_count"]:,} hashes</div></div>',
                            unsafe_allow_html=True)

    # ════════════════════════════════════════════════════
    #  TAB 2 — IDENTIFY
    # ════════════════════════════════════════════════════
    with tab_id:
        st.markdown(slabel("SEARCH"), unsafe_allow_html=True)
        st.markdown('<h3 style="margin:0 0 1rem">Identify a clip</h3>', unsafe_allow_html=True)

        if db is None:
            st.error("Database not found. Run `python build_db.py` first.")
        else:
            # ── Upload widget ──────────────────────────────────────────────
            uploaded = st.file_uploader(
                "upload",
                type=["wav", "mp3", "flac", "ogg", "m4a"],
                label_visibility="collapsed",
                help="200 MB per file • WAV, MP3, FLAC, OGG, M4A",
                key="upload_widget",
            )
            # When a new file is uploaded, clear the selected sample & old result
            if uploaded is not None and st.session_state.selected_sample is not None:
                st.session_state.selected_sample = None
                st.session_state.last_result = None

            # ── Sample clips ───────────────────────────────────────────────
            sample_files = (sorted(SAMPLES_DIR.glob("sample*.wav"))
                            if SAMPLES_DIR.exists() else [])
            if sample_files:
                st.markdown(
                    '<div style="font-family:\'JetBrains Mono\',monospace;font-size:.63rem;'
                    'letter-spacing:.1em;color:#6b7280;text-transform:uppercase;'
                    'margin:1.2rem 0 .7rem">OR TRY A SAMPLE</div>',
                    unsafe_allow_html=True)

                for sf_path in sample_files[:5]:
                    c_name, c_audio, c_btn = st.columns([0.12, 0.73, 0.15])
                    with c_name:
                        st.markdown(
                            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:.72rem;'
                            f'color:#6b7280;padding-top:.5rem">{sf_path.stem}</div>',
                            unsafe_allow_html=True)
                    with c_audio:
                        audio_bytes = sf_path.read_bytes()
                        st.audio(audio_bytes, format="audio/wav")
                    with c_btn:
                        # FIX: store in session_state so it survives the next rerun
                        if st.button("Try", key=f"try_{sf_path.stem}",
                                     help=f"Use {sf_path.stem} as query"):
                            st.session_state.selected_sample = sf_path
                            st.session_state.last_result     = None
                            st.rerun()

            # Show which sample is currently selected
            sel = st.session_state.selected_sample
            if sel is not None and uploaded is None:
                st.markdown(
                    f'<div class="sample-active">&#9654; {sel.stem} selected</div>',
                    unsafe_allow_html=True)

            # ── Identify button ────────────────────────────────────────────
            col_btn, col_clr = st.columns([0.15, 0.85])
            with col_btn:
                do_identify = st.button("Identify", type="primary", use_container_width=True)
            with col_clr:
                if st.session_state.last_result and st.button(
                        "✕ Clear", help="Clear result", use_container_width=False):
                    st.session_state.last_result     = None
                    st.session_state.selected_sample = None
                    st.rerun()

            # ── Run identification ─────────────────────────────────────────
            if do_identify:
                # Determine audio source (upload takes priority over sample)
                if uploaded is not None:
                    audio_source = uploaded
                    label = getattr(uploaded, "name", "upload")
                elif st.session_state.selected_sample is not None:
                    audio_source = st.session_state.selected_sample
                    label = audio_source.stem
                else:
                    audio_source = None
                    label = ""

                if audio_source is None:
                    st.warning("Upload a clip **or** click a sample **Try** button first.")
                else:
                    with st.spinner(f"Fingerprinting '{label}'…"):
                        # Write to temp file (handles both UploadedFile and Path)
                        if hasattr(audio_source, "read"):
                            suffix = Path(getattr(audio_source, "name", "clip.wav")).suffix or ".wav"
                            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                            tmp.write(audio_source.read())
                            tmp.close()            # ← must close before librosa reads on Windows
                            audio_path = tmp.name
                            is_tmp = True
                        else:
                            audio_path = str(audio_source)
                            is_tmp     = False
                        try:
                            result = run_identify(audio_path, db, song_meta)
                            st.session_state.last_result  = result
                            st.session_state.result_label = label
                        except Exception as e:
                            st.error(f"Error during identification: {e}")
                            st.session_state.last_result = None
                        finally:
                            if is_tmp and os.path.exists(audio_path):
                                os.unlink(audio_path)

            # ── Display results ────────────────────────────────────────────
            if st.session_state.last_result:
                show_results(st.session_state.last_result, song_meta)

    # ════════════════════════════════════════════════════
    #  TAB 3 — BATCH
    # ════════════════════════════════════════════════════
    with tab_batch:
        st.markdown(slabel("BATCH"), unsafe_allow_html=True)
        st.markdown('<h3 style="margin:0 0 .5rem">Identify many clips at once</h3>',
                    unsafe_allow_html=True)

        if db is None:
            st.error("Database not found. Run `python build_db.py` first.")
        else:
            st.markdown(
                '<div style="font-size:.82rem;color:#6b7280;margin-bottom:1.2rem;line-height:1.6">'
                'Upload a set of query clips. Each is identified against the '
                '<b style="color:#d4d8db">currently indexed library</b>, and the results are written '
                'to a standardised <code>results.csv</code> with columns <code>filename</code>, '
                '<code>prediction</code>. The <code>prediction</code> is the matched track\'s filename '
                'without its extension, or <code>none</code> when no candidate clears the threshold.'
                '</div>',
                unsafe_allow_html=True)

            batch_files = st.file_uploader(
                "Upload query clips",
                type=["wav", "mp3", "flac", "ogg", "m4a"],
                accept_multiple_files=True,
                label_visibility="collapsed",
                key="batch_upload",
            )

            if st.button("Run batch", type="primary"):
                if not batch_files:
                    st.warning("Please upload at least one clip.")
                else:
                    rows  = []
                    prog  = st.progress(0.0, text="Starting…")
                    live  = st.empty()
                    n     = len(batch_files)

                    for i, uf in enumerate(batch_files):
                        pct  = (i + 1) / n
                        prog.progress(pct, text=f"Processing {uf.name}  ({i+1}/{n})…")

                        suffix = Path(uf.name).suffix or ".wav"
                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                        tmp.write(uf.read())
                        tmp.close()                 # close before reading
                        try:
                            res  = run_identify(tmp.name, db, song_meta)
                            pred = res.get("winner") or "none"
                        except Exception:
                            pred = "none"
                        finally:
                            if os.path.exists(tmp.name):
                                os.unlink(tmp.name)

                        rows.append({"filename": uf.name, "prediction": pred})
                        live.dataframe(pd.DataFrame(rows), use_container_width=True)

                    prog.empty()
                    st.markdown(slabel("RESULTS"), unsafe_allow_html=True)
                    st.dataframe(pd.DataFrame(rows), use_container_width=True)

                    matched = sum(1 for r in rows if r["prediction"] != "none")
                    st.markdown(
                        f'<div style="font-size:.8rem;color:#6b7280;margin:.4rem 0">'
                        f'<b style="color:#00e5c0">{matched} / {n}</b> clips matched  '
                        f'({n - matched} returned <code>none</code>).</div>',
                        unsafe_allow_html=True)

                    csv = pd.DataFrame(rows).to_csv(index=False)
                    st.download_button(
                        "⬇ Download results.csv",
                        data=csv, file_name="results.csv", mime="text/csv")

if __name__ == "__main__":
    main()
