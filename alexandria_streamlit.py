import subprocess, sys, os, json, hashlib, random, string, base64, re
from datetime import datetime
from collections import defaultdict, Counter

def _pip(pkg):
    try:
        subprocess.check_call([sys.executable,"-m","pip","install",pkg,"-q"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass

try: import plotly.graph_objects as go
except: _pip("plotly"); import plotly.graph_objects as go
try: import numpy as np; from PIL import Image as PILImage
except: _pip("pillow numpy"); import numpy as np; from PIL import Image as PILImage
try: import requests
except: _pip("requests"); import requests

import streamlit as st

st.set_page_config(page_title="Nebula", page_icon="🔬", layout="wide", initial_sidebar_state="collapsed")

DB_FILE = "nebula_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: pass
    return {}

def save_db():
    try:
        prefs_s = {k: dict(v) for k,v in st.session_state.user_prefs.items()}
        with open(DB_FILE,"w",encoding="utf-8") as f:
            json.dump({
                "users": st.session_state.users,
                "feed_posts": st.session_state.feed_posts,
                "folders": st.session_state.folders,
                "user_prefs": prefs_s,
                "saved_articles": st.session_state.saved_articles
            }, f, ensure_ascii=False, indent=2)
    except: pass

def hp(pw): return hashlib.sha256(pw.encode()).hexdigest()
def code6(): return ''.join(random.choices(string.digits, k=6))

def ini(n):
    if not isinstance(n, str): n = str(n)
    parts = n.strip().split()
    return ''.join(w[0].upper() for w in parts[:2]) if parts else "?"

def img_to_b64(file_obj):
    try:
        file_obj.seek(0); data = file_obj.read()
        ext = getattr(file_obj,"name","img.png").split(".")[-1].lower()
        mime = {"jpg":"jpeg","jpeg":"jpeg","png":"png","gif":"gif","webp":"webp"}.get(ext,"png")
        return f"data:image/{mime};base64,{base64.b64encode(data).decode()}"
    except: return None

def time_ago(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        delta = datetime.now() - dt
        if delta.days == 0: return "hoje"
        if delta.days == 1: return "ontem"
        if delta.days < 7: return f"{delta.days}d"
        if delta.days < 30: return f"{delta.days//7}sem"
        return f"{delta.days//30}m"
    except: return date_str

def fmt_num(n):
    try:
        n = int(n)
        if n >= 1000: return f"{n/1000:.1f}k"
        return str(n)
    except: return str(n)

def guser():
    if not isinstance(st.session_state.get("users"), dict): return {}
    return st.session_state.users.get(st.session_state.current_user, {})

def get_photo(email):
    u = st.session_state.get("users", {})
    if not isinstance(u, dict): return None
    return u.get(email, {}).get("photo_b64")

# ─────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Playfair+Display:wght@700;800&display=swap');

:root {
  --bg: #04060e;
  --s1: #080e1c;
  --s2: #0c1424;
  --s3: #101c30;
  --border: #162040;
  --border2: #1e3058;
  --blue: #1d4ed8;
  --blue2: #2563eb;
  --blue3: #3b82f6;
  --blue4: #60a5fa;
  --cyan: #06b6d4;
  --cyan2: #22d3ee;
  --text: #dde6f5;
  --text2: #8ea8cc;
  --muted: #3d5070;
  --ok: #10b981;
  --warn: #f59e0b;
  --err: #ef4444;
  --glass: rgba(10,18,38,0.72);
  --glass2: rgba(16,26,52,0.60);
  --glow: rgba(37,99,235,0.18);
  --r8: 8px; --r12: 12px; --r16: 16px; --r20: 20px; --r28: 28px; --r40: 40px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; }

html, body, .stApp {
  background: var(--bg) !important;
  color: var(--text) !important;
  font-family: 'Outfit', sans-serif !important;
}

/* Ambient */
.stApp::before {
  content: '';
  position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background:
    radial-gradient(ellipse 120% 55% at 5% -5%, rgba(37,99,235,.14) 0%, transparent 55%),
    radial-gradient(ellipse 70% 70% at 95% 100%, rgba(6,182,212,.08) 0%, transparent 50%),
    radial-gradient(ellipse 50% 50% at 50% 50%, rgba(29,78,216,.04) 0%, transparent 100%);
}

.stApp::after {
  content: '';
  position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background-image:
    radial-gradient(1.2px 1.2px at 8% 12%, rgba(147,197,253,.7) 0%, transparent 100%),
    radial-gradient(1px 1px at 25% 40%, rgba(147,197,253,.45) 0%, transparent 100%),
    radial-gradient(1.5px 1.5px at 60% 18%, rgba(96,165,245,.55) 0%, transparent 100%),
    radial-gradient(1px 1px at 78% 65%, rgba(147,197,253,.35) 0%, transparent 100%),
    radial-gradient(1px 1px at 90% 30%, rgba(96,165,245,.4) 0%, transparent 100%),
    radial-gradient(1px 1px at 44% 85%, rgba(147,197,253,.28) 0%, transparent 100%),
    radial-gradient(1px 1px at 15% 75%, rgba(96,165,245,.2) 0%, transparent 100%);
}

[data-testid="collapsedControl"],
section[data-testid="stSidebar"] { display:none !important; }

.block-container {
  padding-top: 0 !important;
  padding-bottom: 5rem !important;
  max-width: 1420px !important;
  position: relative; z-index: 1;
}

/* TYPOGRAPHY */
h1 { font-family: 'Playfair Display', serif !important; font-size: 1.8rem !important; font-weight: 800 !important; letter-spacing: -.02em; }
h2 { font-family: 'Outfit', sans-serif !important; font-size: 1.1rem !important; font-weight: 700 !important; letter-spacing: -.01em; }
h3 { font-family: 'Outfit', sans-serif !important; font-size: .92rem !important; font-weight: 700 !important; }

/* ═══════════════════════════════════════
   TOP NAV — LIQUID GLASS
═══════════════════════════════════════ */
.topnav-wrap {
  position: sticky; top: 0; z-index: 1000;
  background: rgba(4,6,14,0.80);
  backdrop-filter: blur(40px) saturate(220%);
  -webkit-backdrop-filter: blur(40px) saturate(220%);
  border-bottom: 1px solid rgba(30,48,88,0.6);
  padding: 0 1.6rem;
  display: flex; align-items: center; justify-content: space-between;
  height: 60px;
  box-shadow: 0 1px 0 rgba(59,130,246,.06), 0 8px 32px rgba(0,0,0,.35);
}

.topnav-logo {
  font-family: 'Playfair Display', serif;
  font-size: 1.35rem; font-weight: 800;
  background: linear-gradient(135deg, #60a5fa 20%, #22d3ee 80%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text; white-space: nowrap; flex-shrink: 0;
  letter-spacing: -.04em;
}

.topnav-items {
  display: flex; align-items: center; gap: 4px;
  overflow-x: auto; padding: 0 .8rem;
  scrollbar-width: none;
}
.topnav-items::-webkit-scrollbar { display: none; }

/* LIQUID GLASS NAV PILL */
.nav-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: .38rem .88rem;
  border-radius: 50px;
  font-size: .76rem; font-weight: 500;
  white-space: nowrap; cursor: pointer;
  color: var(--text2);
  background: transparent;
  border: 1px solid transparent;
  transition: all .2s cubic-bezier(.4,0,.2,1);
  text-decoration: none;
}
.nav-pill:hover {
  color: var(--text);
  background: rgba(37,99,235,.12);
  border-color: rgba(59,130,246,.2);
}
.nav-pill.active {
  color: #fff;
  background: linear-gradient(135deg, rgba(37,99,235,.55) 0%, rgba(29,78,216,.45) 50%, rgba(6,182,212,.2) 100%);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(96,165,250,.35);
  box-shadow:
    0 2px 16px rgba(37,99,235,.25),
    inset 0 1px 0 rgba(147,197,253,.15),
    inset 0 -1px 0 rgba(0,0,0,.2);
}
.nav-pill-dot {
  width: 5px; height: 5px; border-radius: 50%;
  background: currentColor; opacity: .6;
}

/* TOP NAV CLICK OVERLAY */
.toprow { position:relative; margin-top:-60px; height:60px; z-index:998; }
.toprow .stButton > button {
  background:transparent !important; border:none !important; color:transparent !important;
  font-size:0 !important; box-shadow:none !important; border-radius:50px !important;
  width:100% !important; height:60px !important; padding:0 !important; backdrop-filter:none !important;
}
.toprow .stButton > button:hover {
  background:rgba(59,130,246,.06) !important; transform:none !important; box-shadow:none !important;
}

/* ═══════════════════════════════════════
   GLASS CARD
═══════════════════════════════════════ */
.card {
  background: var(--glass);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border: 1px solid var(--border);
  border-radius: var(--r20);
  box-shadow: 0 4px 32px rgba(0,0,0,.45), inset 0 1px 0 rgba(96,165,250,.05);
  position: relative; overflow: hidden;
  transition: border-color .2s, box-shadow .2s, transform .15s;
}
.card::before {
  content:''; position:absolute; top:0; left:0; right:0; height:1px;
  background: linear-gradient(90deg, transparent, rgba(96,165,250,.2), transparent);
}
.card:hover {
  border-color: var(--border2);
  box-shadow: 0 8px 40px rgba(0,0,0,.5), 0 0 0 1px rgba(59,130,246,.08);
}

/* ═══════════════════════════════════════
   POST CARD
═══════════════════════════════════════ */
.post {
  background: var(--glass);
  backdrop-filter: blur(24px);
  border: 1px solid var(--border);
  border-radius: var(--r20);
  margin-bottom: .85rem;
  overflow: hidden;
  box-shadow: 0 4px 24px rgba(0,0,0,.4), inset 0 1px 0 rgba(96,165,250,.04);
  animation: slideUp .3s cubic-bezier(.34,1.56,.64,1) both;
  transition: border-color .2s, box-shadow .2s;
  position: relative;
}
.post:hover {
  border-color: var(--border2);
  box-shadow: 0 10px 44px rgba(0,0,0,.5);
}
.post::before {
  content:''; position:absolute; top:0; left:0; right:0; height:1px;
  background: linear-gradient(90deg, transparent, rgba(96,165,250,.18), transparent);
  pointer-events: none;
}
@keyframes slideUp {
  from { opacity:0; transform:translateY(14px); }
  to   { opacity:1; transform:translateY(0); }
}

/* ═══════════════════════════════════════
   BUTTONS
═══════════════════════════════════════ */
.stButton > button {
  background: linear-gradient(135deg,
    rgba(30,60,140,.5) 0%,
    rgba(18,40,100,.45) 60%,
    rgba(6,182,212,.12) 100%) !important;
  backdrop-filter: blur(16px) !important;
  -webkit-backdrop-filter: blur(16px) !important;
  border: 1px solid rgba(59,130,246,.2) !important;
  border-radius: var(--r12) !important;
  color: var(--text) !important;
  font-family: 'Outfit', sans-serif !important;
  font-weight: 500 !important;
  font-size: .80rem !important;
  padding: .44rem .85rem !important;
  transition: all .18s cubic-bezier(.4,0,.2,1) !important;
  box-shadow: 0 2px 12px rgba(0,0,0,.28), inset 0 1px 0 rgba(147,197,253,.07) !important;
  letter-spacing: .01em !important;
}
.stButton > button:hover {
  background: linear-gradient(135deg,
    rgba(37,99,235,.65) 0%,
    rgba(29,78,216,.55) 60%,
    rgba(6,182,212,.22) 100%) !important;
  border-color: rgba(96,165,250,.42) !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 22px rgba(37,99,235,.25), inset 0 1px 0 rgba(147,197,253,.12) !important;
}
.stButton > button:active { transform: translateY(0) scale(.97) !important; }

/* ═══════════════════════════════════════
   STORY CIRCLE BUTTONS — override to transparent
═══════════════════════════════════════ */
.story-btn .stButton > button {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  height: auto !important;
  transform: none !important;
}
.story-btn .stButton > button:hover {
  background: transparent !important;
  box-shadow: none !important;
  transform: none !important;
}

/* COMPOSE TRIGGER BUTTON */
.compose-trigger .stButton > button {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  position: absolute !important;
  inset: 0 !important;
  width: 100% !important;
  height: 100% !important;
  padding: 0 !important;
  border-radius: var(--r40) !important;
  opacity: 0 !important;
  cursor: pointer !important;
}

/* INPUTS */
.stTextInput input, .stTextArea textarea {
  background: rgba(4,6,14,.8) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r12) !important;
  color: var(--text) !important;
  font-family: 'Outfit', sans-serif !important;
  font-size: .875rem !important;
  transition: border-color .18s, box-shadow .18s !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: rgba(59,130,246,.5) !important;
  box-shadow: 0 0 0 3px rgba(37,99,235,.1) !important;
}
.stTextInput label, .stTextArea label,
.stSelectbox label, .stFileUploader label, .stNumberInput label {
  color: var(--muted) !important;
  font-size: .66rem !important; letter-spacing: .09em !important;
  text-transform: uppercase !important; font-weight: 600 !important;
}

/* AVATAR */
.av {
  border-radius: 50%;
  background: linear-gradient(135deg, #1e3a8a, #2563eb);
  display: flex; align-items: center; justify-content: center;
  font-family: 'Outfit', sans-serif; font-weight: 700; color: white;
  border: 2px solid rgba(59,130,246,.22);
  flex-shrink: 0; overflow: hidden;
  box-shadow: 0 2px 10px rgba(0,0,0,.4);
}
.av img { width:100%; height:100%; object-fit:cover; border-radius:50%; }

/* TAGS */
.tag {
  display: inline-block;
  background: rgba(37,99,235,.09);
  border: 1px solid rgba(59,130,246,.18);
  border-radius: 20px;
  padding: 2px 9px; font-size: .65rem;
  color: #93c5fd; margin: 2px; font-weight: 500;
}

/* BADGES */
.badge-on   { display:inline-block; background:rgba(245,158,11,.1); border:1px solid rgba(245,158,11,.28); border-radius:20px; padding:2px 9px; font-size:.65rem; font-weight:600; color:#fbbf24; }
.badge-pub  { display:inline-block; background:rgba(16,185,129,.1); border:1px solid rgba(16,185,129,.28); border-radius:20px; padding:2px 9px; font-size:.65rem; font-weight:600; color:#34d399; }
.badge-done { display:inline-block; background:rgba(139,92,246,.1); border:1px solid rgba(139,92,246,.28); border-radius:20px; padding:2px 9px; font-size:.65rem; font-weight:600; color:#a78bfa; }
.badge-rec  { display:inline-block; background:rgba(6,182,212,.1); border:1px solid rgba(6,182,212,.28); border-radius:20px; padding:2px 9px; font-size:.65rem; font-weight:600; color:#22d3ee; }

/* METRIC */
.mbox {
  background: var(--glass); border: 1px solid var(--border);
  border-radius: var(--r16); padding: 1rem; text-align: center;
}
.mval {
  font-family: 'Playfair Display', serif; font-size: 1.85rem; font-weight: 800;
  background: linear-gradient(135deg, var(--blue4), var(--cyan2));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.mlbl { font-size:.64rem; color:var(--muted); margin-top:4px; letter-spacing:.09em; text-transform:uppercase; font-weight:600; }

/* PROG BAR */
.prog-wrap { height:4px; background:rgba(30,64,175,.12); border-radius:4px; overflow:hidden; margin:.2rem 0 .4rem; }
.prog-fill  { height:100%; border-radius:4px; transition: width .6s ease; }

/* CHAT */
.bme   { background:linear-gradient(135deg,rgba(37,99,235,.55),rgba(6,182,212,.22)); border:1px solid rgba(59,130,246,.22); border-radius:18px 18px 4px 18px; padding:.58rem .9rem; max-width:68%; margin-left:auto; margin-bottom:6px; font-size:.83rem; line-height:1.6; }
.bthem { background:rgba(10,16,32,.9); border:1px solid var(--border); border-radius:18px 18px 18px 4px; padding:.58rem .9rem; max-width:68%; margin-bottom:6px; font-size:.83rem; line-height:1.6; }

/* COMMENT */
.cmt { background:rgba(4,6,14,.85); border:1px solid var(--border); border-radius:var(--r12); padding:.55rem .9rem; margin-bottom:.3rem; }

/* SEARCH CARD */
.scard {
  background: var(--glass); border: 1px solid var(--border);
  border-radius: var(--r16); padding: .95rem 1.15rem; margin-bottom: .55rem;
  transition: border-color .18s, transform .15s;
}
.scard:hover { border-color: var(--border2); transform: translateY(-1px); }

/* TABS */
.stTabs [data-baseweb="tab-list"] {
  background: rgba(4,6,14,.85) !important; border-radius: var(--r12) !important;
  padding: 4px !important; gap: 2px !important; border: 1px solid var(--border) !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important; color: var(--muted) !important;
  border-radius: var(--r8) !important; font-size: .78rem !important;
  font-family: 'Outfit', sans-serif !important; font-weight: 500 !important;
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg,rgba(37,99,235,.35),rgba(6,182,212,.15)) !important;
  color: var(--text) !important; border: 1px solid rgba(59,130,246,.28) !important;
}
.stTabs [data-baseweb="tab-panel"] { background:transparent !important; padding-top:.9rem !important; }

/* EXPANDER */
.stExpander { background:var(--glass) !important; border:1px solid var(--border) !important; border-radius:var(--r16) !important; }
.stExpander summary { color:var(--text2) !important; font-size:.82rem !important; }

/* SELECT */
.stSelectbox [data-baseweb="select"] { background:rgba(4,6,14,.8) !important; border:1px solid var(--border) !important; border-radius:var(--r12) !important; }

/* FILE UPLOAD */
.stFileUploader section { background:rgba(4,6,14,.6) !important; border:1.5px dashed rgba(59,130,246,.22) !important; border-radius:var(--r16) !important; }

/* MISC */
::-webkit-scrollbar { width:4px; height:4px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:#162040; border-radius:3px; }
hr { border:none; border-top:1px solid var(--border) !important; margin:1rem 0; }
label { color:var(--text2) !important; }
.stCheckbox label, .stRadio label { color:var(--text) !important; }
.stAlert { background:var(--glass) !important; border:1px solid var(--border) !important; border-radius:var(--r16) !important; }
input[type="number"] { background:rgba(4,6,14,.8) !important; border:1px solid var(--border) !important; border-radius:var(--r12) !important; color:var(--text) !important; }

/* PAGE FADE */
.pw { animation: fadeIn .24s ease both; }
@keyframes fadeIn { from{opacity:0;transform:translateY(7px)} to{opacity:1;transform:translateY(0)} }

/* PROFILE HERO */
.prof-hero {
  background: var(--glass); border: 1px solid var(--border);
  border-radius: var(--r28); padding: 2rem;
  display:flex; gap:1.5rem; align-items:flex-start;
  box-shadow:0 8px 40px rgba(0,0,0,.45), inset 0 1px 0 rgba(96,165,250,.06);
  position:relative; overflow:hidden; margin-bottom:1.2rem;
}
.prof-hero::before { content:''; position:absolute; top:0; left:0; right:0; height:1px; background:linear-gradient(90deg,transparent,rgba(96,165,250,.3),transparent); }
.prof-photo { width:88px; height:88px; border-radius:50%; background:linear-gradient(135deg,#1e3a8a,#2563eb); border:2.5px solid rgba(59,130,246,.3); flex-shrink:0; overflow:hidden; display:flex; align-items:center; justify-content:center; font-size:1.9rem; font-weight:700; color:white; }
.prof-photo img { width:100%; height:100%; object-fit:cover; border-radius:50%; }

/* ONLINE DOT */
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.5;transform:scale(.8)} }
.dot-on  { display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--ok); animation:pulse 2s infinite; margin-right:4px; vertical-align:middle; }
.dot-off { display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--muted); margin-right:4px; vertical-align:middle; }

/* COMPOSE CARD */
.compose-card {
  background: rgba(8,14,28,.95); border: 1px solid rgba(59,130,246,.3);
  border-radius: var(--r20); padding: 1.3rem 1.5rem; margin-bottom: 1rem;
  box-shadow: 0 4px 28px rgba(0,0,0,.4), inset 0 1px 0 rgba(96,165,250,.07);
  animation: fadeIn .2s ease;
}

/* PERSON ROW */
.person-row { display:flex; align-items:center; gap:9px; padding:.45rem .5rem; border-radius:var(--r12); border:1px solid transparent; transition:all .15s; margin-bottom:3px; }
.person-row:hover { background:rgba(37,99,235,.07); border-color:var(--border); }

/* SIDEBAR CARD */
.sc {
  background: var(--glass); border: 1px solid var(--border);
  border-radius: var(--r20); padding: 1.1rem; margin-bottom: .75rem;
}

/* ABOX / PBOX */
.abox { background:rgba(4,6,14,.9); border:1px solid rgba(59,130,246,.22); border-radius:var(--r16); padding:1.05rem; margin-bottom:.8rem; }
.pbox { background:rgba(6,182,212,.04); border:1px solid rgba(6,182,212,.18); border-radius:var(--r16); padding:.95rem; margin-bottom:.7rem; }
.img-rc { background:rgba(6,182,212,.04); border:1px solid rgba(6,182,212,.16); border-radius:var(--r16); padding:.95rem; margin-bottom:.6rem; }

/* DIVIDER TEXT */
.dtxt { display:flex; align-items:center; gap:.75rem; margin:.85rem 0; font-size:.63rem; color:var(--muted); letter-spacing:.09em; text-transform:uppercase; font-weight:600; }
.dtxt::before, .dtxt::after { content:''; flex:1; height:1px; background:var(--border); }

/* STORY RING */
.story-ring {
  width: 64px; height: 64px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.3rem; font-weight: 800; color: white;
  cursor: pointer; transition: all .2s cubic-bezier(.34,1.56,.64,1);
  position: relative;
  box-shadow: 0 4px 16px rgba(0,0,0,.5);
}
.story-ring:hover { transform: scale(1.08); }
.story-ring-active {
  border: 2.5px solid rgba(34,211,238,.8);
  box-shadow: 0 0 0 3px rgba(6,182,212,.2), 0 4px 16px rgba(0,0,0,.5);
}
.story-ring-inactive {
  border: 2.5px solid rgba(59,130,246,.3);
}

/* COMPOSE FLOAT */
.compose-float {
  background: rgba(8,14,28,.98);
  border: 1px solid rgba(59,130,246,.28);
  border-radius: var(--r20);
  padding: 1.1rem 1.35rem;
  margin-bottom: .9rem;
  cursor: pointer;
  transition: border-color .18s;
}
.compose-float:hover { border-color: rgba(59,130,246,.45); }

/* FEED FILTER RADIO — hide default, restyle */
.stRadio > div { display:flex !important; gap:6px !important; flex-wrap:wrap !important; }
.stRadio > div > label {
  background: var(--glass) !important;
  border: 1px solid var(--border) !important;
  border-radius: 50px !important;
  padding: .32rem .85rem !important;
  font-size: .76rem !important; font-weight: 500 !important;
  color: var(--text2) !important;
  cursor: pointer !important;
  transition: all .18s !important;
}
.stRadio > div > label:hover { border-color: var(--border2) !important; color: var(--text) !important; }

/* INPUT NUMBER */
.stNumberInput > div { gap: 4px; }

/* SHARE PANEL */
.share-link { display:inline-flex; align-items:center; gap:5px; padding:.36rem .72rem; border-radius:var(--r8); font-size:.72rem; font-weight:500; text-decoration:none; transition:opacity .15s; }
.share-link:hover { opacity:.75; }
</style>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────
def avh(initials, sz=40, photo=None):
    fs = max(sz//3, 9)
    if photo:
        return f'<div class="av" style="width:{sz}px;height:{sz}px"><img src="{photo}"/></div>'
    return f'<div class="av" style="width:{sz}px;height:{sz}px;font-size:{fs}px">{initials}</div>'

def tags_html(tags):
    return ' '.join(f'<span class="tag">{t}</span>' for t in (tags or []))

def badge(s):
    cls = {"Publicado":"badge-pub","Concluído":"badge-done"}.get(s,"badge-on")
    return f'<span class="{cls}">{s}</span>'

def prog_bar(pct, color="#2563eb"):
    return f'<div class="prog-wrap"><div class="prog-fill" style="width:{pct}%;background:{color}"></div></div>'

# ─────────────────────────────────────────────────
# IMAGE ANALYSIS
# ─────────────────────────────────────────────────
def analyze_image_advanced(uploaded_file):
    try:
        uploaded_file.seek(0)
        img = PILImage.open(uploaded_file).convert("RGB")
        orig = img.size; small = img.resize((512,512))
        arr = np.array(small, dtype=np.float32)
        r, g, b_ch = arr[:,:,0], arr[:,:,1], arr[:,:,2]
        mr, mg, mb = float(r.mean()), float(g.mean()), float(b_ch.mean())
        gray = arr.mean(axis=2)
        gx = np.pad(np.diff(gray,axis=1),((0,0),(0,1)),mode='edge')
        gy = np.pad(np.diff(gray,axis=0),((0,1),(0,0)),mode='edge')
        edge_map = np.sqrt(gx**2+gy**2)
        edge_intensity = float(edge_map.mean())
        h_strength = float(np.abs(gy).mean()); v_strength = float(np.abs(gx).mean())
        d1 = float(np.abs(gx+gy).mean()); d2 = float(np.abs(gx-gy).mean())
        strengths = {"Horizontal":h_strength,"Vertical":v_strength,"Diag A":d1,"Diag B":d2}
        line_dir = max(strengths,key=strengths.get)
        hh, ww = gray.shape[0]//2, gray.shape[1]//2
        q = [gray[:hh,:ww].var(),gray[:hh,ww:].var(),gray[hh:,:ww].var(),gray[hh:,ww:].var()]
        sym = 1.0-(max(q)-min(q))/(max(q)+1e-5)
        left = gray[:,:gray.shape[1]//2]; right = np.fliplr(gray[:,gray.shape[1]//2:])
        lr_sym = 1.0-float(np.abs(left-right).mean())/(gray.mean()+1e-5)
        cx, cy2 = gray.shape[1]//2, gray.shape[0]//2
        y_i, x_i = np.mgrid[0:gray.shape[0],0:gray.shape[1]]
        dist = np.sqrt((x_i-cx)**2+(y_i-cy2)**2)
        rb = np.histogram(dist.ravel(),bins=24,weights=gray.ravel())[0]
        radial_var = float(np.std(rb)/(np.mean(rb)+1e-5))
        has_circular = radial_var < 0.32 and sym > 0.58
        fft_s = np.fft.fftshift(np.abs(np.fft.fft2(gray)))
        hf, wf = fft_s.shape; cm = np.zeros_like(fft_s,dtype=bool)
        cm[hf//2-22:hf//2+22,wf//2-22:wf//2+22] = True
        outside = fft_s[~cm]
        has_grid = float(np.percentile(outside,99)) > float(np.mean(outside))*14
        hist = np.histogram(gray,bins=64,range=(0,255))[0]
        hn = hist/hist.sum(); hn = hn[hn>0]
        entropy = float(-np.sum(hn*np.log2(hn))); contrast = float(gray.std())
        flat = arr.reshape(-1,3); rounded = (flat//32*32).astype(int)
        uniq, counts = np.unique(rounded,axis=0,return_counts=True)
        top_i = np.argsort(-counts)[:8]
        palette = [tuple(int(x) for x in uniq[i]) for i in top_i]
        skin = (r>95)&(g>40)&(b_ch>20)&(r>g)&(r>b_ch)&((r-g)>15)
        skin_pct = float(skin.mean()); blood = (r>120)&(g<80)&(b_ch<80); blood_pct = float(blood.mean())
        warm = mr > mb+15; cool = mb > mr+15
        dom_ch = "R" if mr==max(mr,mg,mb) else ("G" if mg==max(mr,mg,mb) else "B")
        saturation = float((np.maximum.reduce([r,g,b_ch])-np.minimum.reduce([r,g,b_ch])).mean())/(max(mr,mg,mb)+1e-5)
        shapes = []
        if has_circular: shapes.append("Circular")
        if has_grid: shapes.append("Grade / Periódico")
        if sym > 0.78: shapes.append("Alta Simetria")
        if lr_sym > 0.75: shapes.append("Simetria Bilateral")
        if edge_intensity > 32: shapes.append("Contornos Nítidos")
        if not shapes: shapes.append("Irregular")
        if skin_pct > 0.15 and mr > 140:
            cat="Coloração H&E — Histopatologia"; desc=f"Tecido orgânico em {skin_pct*100:.0f}% da área."; kw="hematoxylin eosin HE staining histopathology biopsy tissue"; material="Tecido Biológico"; obj_type="Amostra Histopatológica"
        elif skin_pct > 0.20:
            cat="Histologia / Microscopia Óptica"; desc=f"Tonalidade orgânica em {skin_pct*100:.0f}%."; kw="histology tissue biology microscopy organic"; material="Tecido Biológico"; obj_type="Células, Tecido"
        elif has_grid and edge_intensity > 18:
            cat="Cristalografia / Difração"; desc=f"Padrão periódico via FFT. Intensidade: {edge_intensity:.1f}."; kw="X-ray diffraction crystallography TEM crystal material science"; material="Material Cristalino"; obj_type="Rede Cristalina"
        elif mg > 165 and mr < 125:
            cat="Fluorescência Verde — GFP/FITC"; desc=f"Canal verde dominante (G={mg:.0f})."; kw="GFP green fluorescent protein FITC fluorescence confocal microscopy"; material="Proteínas Fluorescentes"; obj_type="Células Marcadas"
        elif mb > 165 and mr < 110:
            cat="Fluorescência Azul — DAPI/Hoechst"; desc=f"Canal azul dominante (B={mb:.0f})."; kw="DAPI Hoechst nuclear staining DNA chromatin fluorescence microscopy"; material="DNA / Cromatina"; obj_type="Núcleos Celulares"
        elif mr > 185 and mg < 100:
            cat="Imuno-histoquímica (IHC)"; desc=f"Vermelho dominante (R={mr:.0f})."; kw="immunohistochemistry IHC DAB antibody pathology staining"; material="Antígenos Teciduais"; obj_type="Expressão Proteica"
        elif has_circular and edge_intensity > 24:
            cat="Microscopia Celular / Organelas"; desc=f"Estruturas circulares (I={edge_intensity:.1f})."; kw="cell organelle vesicle bacteria microscopy phase contrast"; material="Componentes Celulares"; obj_type="Células, Organelas"
        elif entropy > 6.2 and edge_intensity < 18:
            cat="Imagem Multispectral / Satélite"; desc=f"Entropia alta ({entropy:.2f} bits)."; kw="satellite remote sensing multispectral geospatial"; material="Dados Geoespaciais"; obj_type="Paisagem Espectral"
        elif edge_intensity > 40:
            cat="Gráfico / Diagrama Científico"; desc=f"Bordas muito nítidas (I={edge_intensity:.1f})."; kw="scientific visualization chart diagram data figure"; material="Dados Abstratos"; obj_type="Gráfico, Diagrama"
        elif sym > 0.82:
            cat="Estrutura Molecular / Simétrica"; desc=f"Alta simetria ({sym:.3f})."; kw="molecular structure protein crystal symmetry chemistry"; material="Moléculas, Proteínas"; obj_type="Estrutura Molecular"
        else:
            temp = "quente" if warm else ("fria" if cool else "neutra")
            cat="Imagem Científica Geral"; desc=f"Temperatura {temp}. Brilho médio: {(mr+mg+mb)/3:.0f}/255."; kw="scientific image analysis research"; material="Variado"; obj_type="Imagem Científica"
        conf = min(96,48+edge_intensity/2+entropy*2.8+sym*5+(8 if skin_pct>0.1 else 0)+(6 if has_grid else 0))
        return {
            "category":cat,"description":desc,"kw":kw,"material":material,"object_type":obj_type,
            "confidence":round(conf,1),
            "lines":{"direction":line_dir,"intensity":round(edge_intensity,2),"h":round(h_strength,2),"v":round(v_strength,2),"d1":round(d1,2),"d2":round(d2,2),"strengths":strengths},
            "shapes":shapes,"symmetry":round(sym,3),"lr_symmetry":round(lr_sym,3),
            "circular":has_circular,"grid":has_grid,
            "color":{"r":round(mr,1),"g":round(mg,1),"b":round(mb,1),"warm":warm,"cool":cool,"dom":dom_ch,"sat":round(saturation*100,1)},
            "texture":{"entropy":round(entropy,3),"contrast":round(contrast,2),"complexity":"Alta" if entropy>5.5 else ("Média" if entropy>4 else "Baixa")},
            "palette":palette,"size":orig,"skin_pct":round(skin_pct*100,1),"blood_pct":round(blood_pct*100,1)
        }
    except Exception as e:
        st.error(f"Erro ao analisar: {e}"); return None

# ─────────────────────────────────────────────────
# FOLDER ANALYSIS
# ─────────────────────────────────────────────────
KMAP = {
    "genomica":["Genômica","DNA"],"dna":["DNA","Genômica"],"rna":["RNA"],
    "crispr":["CRISPR","Edição Gênica"],"proteina":["Proteômica"],"celula":["Biologia Celular"],
    "neurociencia":["Neurociência"],"sono":["Sono","Neurociência"],"memoria":["Memória"],
    "ia":["IA","Machine Learning"],"ml":["Machine Learning"],"deep":["Deep Learning"],
    "quantum":["Computação Quântica"],"fisica":["Física"],"quimica":["Química"],
    "astronomia":["Astronomia"],"psicologia":["Psicologia"],"biologia":["Biologia"],
    "medicina":["Medicina"],"cancer":["Oncologia"],"dados":["Ciência de Dados"],
    "tese":["Tese"],"relatorio":["Relatório"],"metodologia":["Metodologia"],
    "ecologia":["Ecologia"],"clima":["Clima"],
}
EMAP = {"pdf":"PDF","docx":"Word","doc":"Word","xlsx":"Planilha","csv":"Dados",
        "txt":"Texto","png":"Imagem","jpg":"Imagem","jpeg":"Imagem","tiff":"Imagem Científica",
        "py":"Código Python","r":"Código R","ipynb":"Notebook Jupyter","pptx":"Apresentação"}

def analyze_folder(folder_name):
    fd = st.session_state.folders.get(folder_name,{})
    files = fd.get("files",[]) if isinstance(fd,dict) else fd
    if not files: return None
    all_tags, file_analyses = set(), []
    for fname in files:
        fl = fname.lower().replace("_"," ").replace("-"," "); ftags = set()
        for kw, ktags in KMAP.items():
            if kw in fl: ftags.update(ktags)
        ext = fname.split(".")[-1].lower() if "." in fname else ""
        ftype = EMAP.get(ext,"Arquivo")
        if not ftags: ftags.add("Pesquisa Geral")
        all_tags.update(ftags)
        file_analyses.append({"file":fname,"type":ftype,"tags":list(ftags),"progress":random.randint(35,98)})
    areas = list(all_tags)[:6]
    return {"tags":list(all_tags)[:12],"summary":f"{len(files)} doc(s) · Áreas: {', '.join(areas)}","file_analyses":file_analyses}

# ─────────────────────────────────────────────────
# SEARCH APIs
# ─────────────────────────────────────────────────
def search_ss(query, limit=8):
    results = []
    try:
        r = requests.get("https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query":query,"limit":limit,"fields":"title,authors,year,abstract,venue,externalIds,openAccessPdf,citationCount"},
            timeout=9)
        if r.status_code == 200:
            for p in r.json().get("data",[]):
                ext = p.get("externalIds",{}) or {}; doi = ext.get("DOI",""); arxiv = ext.get("ArXiv","")
                pdf = p.get("openAccessPdf") or {}
                link = pdf.get("url","") or (f"https://arxiv.org/abs/{arxiv}" if arxiv else (f"https://doi.org/{doi}" if doi else ""))
                alist = p.get("authors",[]) or []
                authors = ", ".join(a.get("name","") for a in alist[:3])
                if len(alist)>3: authors += " et al."
                results.append({"title":p.get("title","Sem título"),"authors":authors or "—","year":p.get("year","?"),"source":p.get("venue","") or "Semantic Scholar","doi":doi or arxiv or "—","abstract":(p.get("abstract","") or "")[:280],"url":link,"citations":p.get("citationCount",0),"origin":"semantic"})
    except: pass
    return results

def search_cr(query, limit=5):
    results = []
    try:
        r = requests.get("https://api.crossref.org/works",
            params={"query":query,"rows":limit,"select":"title,author,issued,abstract,DOI,container-title,is-referenced-by-count","mailto":"nebula@example.com"},timeout=9)
        if r.status_code == 200:
            for p in r.json().get("message",{}).get("items",[]):
                title = (p.get("title") or ["Sem título"])[0]
                ars = p.get("author",[]) or []
                authors = ", ".join(f'{a.get("given","").split()[0] if a.get("given") else ""} {a.get("family","")}'.strip() for a in ars[:3])
                if len(ars)>3: authors += " et al."
                year = (p.get("issued",{}).get("date-parts") or [[None]])[0][0]
                doi = p.get("DOI",""); abstract = re.sub(r'<[^>]+>','',p.get("abstract","") or "")[:280]
                results.append({"title":title,"authors":authors or "—","year":year or "?","source":(p.get("container-title") or ["CrossRef"])[0],"doi":doi,"abstract":abstract,"url":f"https://doi.org/{doi}" if doi else "","citations":p.get("is-referenced-by-count",0),"origin":"crossref"})
    except: pass
    return results

# ─────────────────────────────────────────────────
# RECOMMENDATIONS
# ─────────────────────────────────────────────────
def record(tags, w=1.0):
    email = st.session_state.get("current_user")
    if not email or not tags: return
    prefs = st.session_state.user_prefs.setdefault(email, defaultdict(float))
    for t in tags: prefs[t.lower()] += w

def get_recs(email, n=2):
    prefs = st.session_state.user_prefs.get(email,{})
    if not prefs: return []
    def score(p): return sum(prefs.get(t.lower(),0) for t in p.get("tags",[])+p.get("connections",[]))
    scored = [(score(p),p) for p in st.session_state.feed_posts if email not in p.get("liked_by",[])]
    return [p for s,p in sorted(scored,key=lambda x:-x[0]) if s>0][:n]

def area_to_tags(area):
    a = (area or "").lower()
    M = {"ia":["machine learning","LLM"],"inteligência artificial":["machine learning","LLM"],"machine learning":["deep learning","dados"],"neurociência":["sono","memória"],"biologia":["célula","genômica"],"física":["quantum","astrofísica"],"química":["síntese","molécula"],"medicina":["diagnóstico","terapia"],"astronomia":["cosmologia","galáxia"],"computação":["algoritmo","redes"],"psicologia":["cognição","comportamento"],"ecologia":["biodiversidade","clima"],"genômica":["DNA","CRISPR"],"engenharia":["robótica","sistemas"]}
    for k,v in M.items():
        if k in a: return v
    return [w.strip() for w in a.replace(","," ").split() if len(w)>3][:5]

# ─────────────────────────────────────────────────
# SEED DATA
# ─────────────────────────────────────────────────
SEED_POSTS = [
    {"id":1,"author":"Carlos Mendez","author_email":"carlos@nebula.ai","avatar":"CM","area":"Neurociência","title":"Efeitos da Privação de Sono na Plasticidade Sináptica","abstract":"Investigamos como 24h de privação de sono afetam espinhas dendríticas em ratos Wistar, com redução de 34% na plasticidade hipocampal. Janela crítica identificada nas primeiras 6h de recuperação.","tags":["neurociência","sono","memória","hipocampo"],"likes":47,"comments":[{"user":"Maria Silva","text":"Excelente metodologia! Os dados de confocal estão impecáveis."},{"user":"João Lima","text":"Quais foram os critérios de exclusão dos animais?"}],"status":"Em andamento","date":"2026-02-10","liked_by":[],"saved_by":[],"connections":["sono","memória"],"views":312},
    {"id":2,"author":"Luana Freitas","author_email":"luana@nebula.ai","avatar":"LF","area":"Biomedicina","title":"CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras","abstract":"Vetor AAV9 modificado para entrega de CRISPR no gene DMD com eficiência de 78% em modelos mdx. Publicação em Cell prevista Q2 2026.","tags":["CRISPR","gene terapia","músculo","AAV9"],"likes":93,"comments":[{"user":"Ana","text":"Quando iniciam os trials clínicos?"}],"status":"Publicado","date":"2026-01-28","liked_by":[],"saved_by":[],"connections":["genômica","distrofia"],"views":891},
    {"id":3,"author":"Rafael Souza","author_email":"rafael@nebula.ai","avatar":"RS","area":"Computação","title":"Redes Neurais Quântico-Clássicas para Otimização Combinatória","abstract":"Arquitetura híbrida variacional combinando qubits supercondutores com camadas densas clássicas. TSP resolvido com 40% menos iterações que métodos puramente clássicos.","tags":["quantum ML","otimização","TSP","computação quântica"],"likes":201,"comments":[],"status":"Em andamento","date":"2026-02-15","liked_by":[],"saved_by":[],"connections":["computação quântica"],"views":1240},
    {"id":4,"author":"Priya Nair","author_email":"priya@nebula.ai","avatar":"PN","area":"Astrofísica","title":"Detecção de Matéria Escura via Lentes Gravitacionais Fracas","abstract":"Mapeamento com 100M de galáxias do DES Y3. Tensão de 2.8σ com o modelo ΛCDM em escalas menores que 1 Mpc identificada pela primeira vez.","tags":["astrofísica","matéria escura","cosmologia","DES"],"likes":312,"comments":[],"status":"Publicado","date":"2026-02-01","liked_by":[],"saved_by":[],"connections":["cosmologia"],"views":2180},
    {"id":5,"author":"João Lima","author_email":"joao@nebula.ai","avatar":"JL","area":"Psicologia","title":"Viés de Confirmação em Decisões Médicas Assistidas por IA","abstract":"Estudo duplo-cego com 240 médicos revelou que sistemas de IA mal calibrados amplificam vieses cognitivos em 22% dos casos de diagnóstico.","tags":["psicologia","IA","cognição","medicina"],"likes":78,"comments":[{"user":"Carlos M.","text":"Muito relevante para políticas de saúde digital!"}],"status":"Publicado","date":"2026-02-08","liked_by":[],"saved_by":[],"connections":["cognição","IA"],"views":456},
]

SEED_USERS = {
    "demo@nebula.ai":{"name":"Ana Pesquisadora","password":hp("demo123"),"bio":"Pesquisadora em IA e Ciências Cognitivas | UFMG","area":"Inteligência Artificial","followers":128,"following":47,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "carlos@nebula.ai":{"name":"Carlos Mendez","password":hp("nebula123"),"bio":"Neurocientista | UFMG | Plasticidade sináptica e sono","area":"Neurociência","followers":210,"following":45,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "luana@nebula.ai":{"name":"Luana Freitas","password":hp("nebula123"),"bio":"Biomédica | FIOCRUZ | CRISPR e terapia gênica","area":"Biomedicina","followers":178,"following":62,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "rafael@nebula.ai":{"name":"Rafael Souza","password":hp("nebula123"),"bio":"Computação Quântica | USP | Algoritmos híbridos","area":"Computação","followers":340,"following":88,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "priya@nebula.ai":{"name":"Priya Nair","password":hp("nebula123"),"bio":"Astrofísica | MIT | Dark matter & gravitational lensing","area":"Astrofísica","followers":520,"following":31,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "joao@nebula.ai":{"name":"João Lima","password":hp("nebula123"),"bio":"Psicólogo Cognitivo | UNICAMP | IA e vieses clínicos","area":"Psicologia","followers":95,"following":120,"verified":True,"2fa_enabled":False,"photo_b64":None},
}

CHAT_INIT = {
    "carlos@nebula.ai":[{"from":"carlos@nebula.ai","text":"Oi! Vi seu comentário na pesquisa de sono.","time":"09:14"},{"from":"me","text":"Achei muito interessante a metodologia!","time":"09:16"}],
    "luana@nebula.ai":[{"from":"luana@nebula.ai","text":"Podemos colaborar no próximo projeto?","time":"ontem"}],
    "rafael@nebula.ai":[{"from":"rafael@nebula.ai","text":"Já compartilhei o repositório no GitHub.","time":"08:30"}],
}

# ─────────────────────────────────────────────────
# SESSION INIT
# ─────────────────────────────────────────────────
def init():
    if "initialized" in st.session_state: return
    st.session_state.initialized = True
    disk = load_db()
    disk_users = disk.get("users",{})
    if not isinstance(disk_users,dict): disk_users = {}
    st.session_state.setdefault("users",{**SEED_USERS,**disk_users})
    st.session_state.setdefault("logged_in",False)
    st.session_state.setdefault("current_user",None)
    st.session_state.setdefault("page","login")
    st.session_state.setdefault("profile_view",None)
    disk_prefs = disk.get("user_prefs",{})
    st.session_state.setdefault("user_prefs",{k:defaultdict(float,v) for k,v in disk_prefs.items()})
    st.session_state.setdefault("pending_verify",None)
    st.session_state.setdefault("pending_2fa",None)
    # Sanitize posts on load
    raw_posts = disk.get("feed_posts",[dict(p) for p in SEED_POSTS])
    for p in raw_posts:
        p.setdefault("author_email","")
        p.setdefault("liked_by",[])
        p.setdefault("saved_by",[])
        p.setdefault("comments",[])
        p.setdefault("views",random.randint(80,800))
    st.session_state.setdefault("feed_posts",raw_posts)
    st.session_state.setdefault("folders",disk.get("folders",{}))
    st.session_state.setdefault("chat_contacts",list(SEED_USERS.keys()))
    st.session_state.setdefault("chat_messages",{k:list(v) for k,v in CHAT_INIT.items()})
    st.session_state.setdefault("active_chat",None)
    st.session_state.setdefault("followed",["carlos@nebula.ai","luana@nebula.ai"])
    st.session_state.setdefault("notifications",["Carlos curtiu sua pesquisa","Nova conexão detectada"])
    st.session_state.setdefault("scholar_cache",{})
    st.session_state.setdefault("saved_articles",disk.get("saved_articles",[]))
    st.session_state.setdefault("img_result",None)
    st.session_state.setdefault("search_results",None)
    st.session_state.setdefault("last_sq","")
    st.session_state.setdefault("stats_data",{"h_index":4,"fator_impacto":3.8,"notes":""})
    st.session_state.setdefault("compose_open",False)

init()

# ─────────────────────────────────────────────────
# AUTH PAGES
# ─────────────────────────────────────────────────
def page_login():
    _, col, _ = st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-bottom:3rem">
          <div style="font-family:'Playfair Display',serif;font-size:3.8rem;font-weight:800;
            background:linear-gradient(135deg,#60a5fa 20%,#22d3ee 80%);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            background-clip:text;letter-spacing:-.05em;line-height:1;margin-bottom:.7rem">
            Nebula
          </div>
          <div style="color:#3d5070;font-size:.68rem;letter-spacing:.28em;text-transform:uppercase;font-weight:600">
            Rede do Conhecimento Científico
          </div>
        </div>""", unsafe_allow_html=True)

        tab_in, tab_up = st.tabs(["  Entrar  ","  Criar conta  "])
        with tab_in:
            email = st.text_input("E-mail", placeholder="seu@email.com", key="li_e")
            pw = st.text_input("Senha", placeholder="••••••••", type="password", key="li_p")
            if st.button("Entrar", use_container_width=True, key="btn_li"):
                u = st.session_state.users.get(email)
                if not u: st.error("E-mail não encontrado.")
                elif u["password"] != hp(pw): st.error("Senha incorreta.")
                elif u.get("2fa_enabled"):
                    c = code6(); st.session_state.pending_2fa = {"email":email,"code":c}
                    st.session_state.page = "2fa"; st.rerun()
                else:
                    st.session_state.logged_in = True; st.session_state.current_user = email
                    record(area_to_tags(u.get("area","")),1.0)
                    st.session_state.page = "feed"; st.rerun()
            st.markdown('<div style="text-align:center;color:#3d5070;font-size:.7rem;margin-top:.7rem">Demo: demo@nebula.ai / demo123</div>', unsafe_allow_html=True)
        with tab_up:
            n_name  = st.text_input("Nome completo", key="su_n")
            n_email = st.text_input("E-mail", key="su_e")
            n_area  = st.text_input("Área de pesquisa", key="su_a")
            n_pw    = st.text_input("Senha", type="password", key="su_p")
            n_pw2   = st.text_input("Confirmar senha", type="password", key="su_p2")
            if st.button("Criar conta", use_container_width=True, key="btn_su"):
                if not all([n_name,n_email,n_area,n_pw,n_pw2]): st.error("Preencha todos os campos.")
                elif n_pw != n_pw2: st.error("Senhas não coincidem.")
                elif len(n_pw) < 6: st.error("Mínimo 6 caracteres.")
                elif n_email in st.session_state.users: st.error("E-mail já cadastrado.")
                else:
                    c = code6(); st.session_state.pending_verify = {"email":n_email,"name":n_name,"pw":hp(n_pw),"area":n_area,"code":c}
                    st.session_state.page = "verify_email"; st.rerun()

def page_verify_email():
    pv = st.session_state.pending_verify
    _, col, _ = st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card" style="padding:2rem;text-align:center">
          <div style="font-size:2.8rem;margin-bottom:1rem;opacity:.8">✉</div>
          <h2 style="margin-bottom:.5rem">Verifique seu e-mail</h2>
          <p style="color:#3d5070;font-size:.84rem">Código para <strong style="color:#8ea8cc">{pv['email']}</strong></p>
          <div style="background:rgba(37,99,235,.07);border:1px solid rgba(59,130,246,.18);
            border-radius:14px;padding:1.2rem;margin:1.2rem 0">
            <div style="font-size:.62rem;color:#3d5070;letter-spacing:.12em;text-transform:uppercase;margin-bottom:6px;font-weight:600">Código (demo)</div>
            <div style="font-family:'Playfair Display',serif;font-size:2.8rem;font-weight:800;letter-spacing:.3em;color:#60a5fa">{pv['code']}</div>
          </div>
        </div>""", unsafe_allow_html=True)
        typed = st.text_input("Código de verificação", max_chars=6, key="ev_c")
        if st.button("Verificar", use_container_width=True, key="btn_ev"):
            if typed.strip() == pv["code"]:
                st.session_state.users[pv["email"]] = {"name":pv["name"],"password":pv["pw"],"bio":"","area":pv["area"],"followers":0,"following":0,"verified":True,"2fa_enabled":False,"photo_b64":None}
                save_db(); st.session_state.pending_verify = None
                st.session_state.logged_in = True; st.session_state.current_user = pv["email"]
                record(area_to_tags(pv["area"]),2.0); st.session_state.page = "feed"; st.rerun()
            else: st.error("Código inválido.")
        if st.button("Voltar", key="btn_ev_bk"): st.session_state.page = "login"; st.rerun()

def page_2fa():
    p2 = st.session_state.pending_2fa
    _, col, _ = st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card" style="padding:2rem;text-align:center">
          <div style="font-size:2.8rem;margin-bottom:1rem;opacity:.8">⬡</div>
          <h2>Verificação 2FA</h2>
          <div style="background:rgba(37,99,235,.07);border:1px solid rgba(59,130,246,.18);
            border-radius:14px;padding:1rem;margin:1rem 0">
            <div style="font-size:.62rem;color:#3d5070;text-transform:uppercase;letter-spacing:.10em;margin-bottom:6px;font-weight:600">Código</div>
            <div style="font-family:'Playfair Display',serif;font-size:2.8rem;font-weight:800;letter-spacing:.25em;color:#60a5fa">{p2['code']}</div>
          </div>
        </div>""", unsafe_allow_html=True)
        typed = st.text_input("Código", max_chars=6, key="fa_c", label_visibility="collapsed")
        if st.button("Verificar", use_container_width=True, key="btn_fa"):
            if typed.strip() == p2["code"]:
                st.session_state.logged_in = True; st.session_state.current_user = p2["email"]
                st.session_state.pending_2fa = None; st.session_state.page = "feed"; st.rerun()
            else: st.error("Código inválido.")
        if st.button("Voltar", key="btn_fa_bk"): st.session_state.page = "login"; st.rerun()

# ─────────────────────────────────────────────────
# TOP NAV — LIQUID GLASS
# ─────────────────────────────────────────────────
NAV = [
    ("feed",     "Feed"),
    ("search",   "Artigos"),
    ("knowledge","Conexões"),
    ("folders",  "Pastas"),
    ("analytics","Análises"),
    ("img_search","Imagem"),
    ("chat",     "Chat"),
    ("settings", "Perfil"),
]

def render_topnav():
    u = guser(); name = u.get("name","?"); photo = u.get("photo_b64"); in_ = ini(name)
    cur = st.session_state.page; notif = len(st.session_state.notifications)

    pills = ""
    for key, lbl in NAV:
        active = cur == key
        cls = "nav-pill active" if active else "nav-pill"
        dot = '<span class="nav-pill-dot"></span>' if active else ""
        pills += f'<span class="{cls}">{dot}{lbl}</span>'

    av_inner = f"<img src='{photo}' style='width:100%;height:100%;object-fit:cover;border-radius:50%'/>" if photo else in_
    av_html = (
        f'<div style="width:36px;height:36px;border-radius:50%;'
        f'background:linear-gradient(135deg,#1e3a8a,#2563eb);'
        f'display:flex;align-items:center;justify-content:center;'
        f'font-size:.72rem;font-weight:700;color:white;'
        f'border:2px solid rgba(59,130,246,.25);overflow:hidden;flex-shrink:0;'
        f'box-shadow:0 2px 10px rgba(0,0,0,.4)">{av_inner}</div>'
    )
    nb = (
        f'<span style="background:#ef4444;color:white;border-radius:10px;'
        f'padding:1px 7px;font-size:.60rem;font-weight:700">{notif}</span>'
    ) if notif else ''

    st.markdown(
        f'<div class="topnav-wrap">'
        f'<div class="topnav-logo">Nebula</div>'
        f'<div class="topnav-items">{pills}</div>'
        f'<div style="display:flex;align-items:center;gap:8px;flex-shrink:0">{nb}{av_html}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Invisible clickable overlay row
    st.markdown('<div class="toprow">', unsafe_allow_html=True)
    cols = st.columns([1.5] + [1]*len(NAV) + [.7])
    for i, (key, lbl) in enumerate(NAV):
        with cols[i+1]:
            if st.button(lbl, key=f"tnav_{key}", use_container_width=True):
                st.session_state.profile_view = None
                st.session_state.page = key
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────
# PROFILE PAGE
# ─────────────────────────────────────────────────
def page_profile(target_email):
    tu = st.session_state.users.get(target_email,{})
    if not tu:
        st.error("Perfil não encontrado.")
        if st.button("Voltar", key="bk_err"): st.session_state.profile_view = None; st.rerun()
        return
    tname = tu.get("name","?"); tin = ini(tname); tphoto = tu.get("photo_b64")
    email = st.session_state.current_user; is_me = email == target_email
    is_fol = target_email in st.session_state.followed
    user_posts = [p for p in st.session_state.feed_posts if p.get("author_email") == target_email]
    total_likes = sum(p["likes"] for p in user_posts)

    if st.button("← Voltar", key="back_prof"):
        st.session_state.profile_view = None; st.rerun()

    photo_html = f'<img src="{tphoto}"/>' if tphoto else f'<span style="font-size:2rem">{tin}</span>'
    verified = '<span style="font-size:.7rem;color:#22d3ee;margin-left:6px">✓</span>' if tu.get("verified") else ""

    st.markdown(
        f'<div class="prof-hero">'
        f'<div class="prof-photo">{photo_html}</div>'
        f'<div style="flex:1;z-index:1">'
        f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:.3rem">'
        f'<h1 style="margin:0">{tname}</h1>{verified}</div>'
        f'<div style="color:#60a5fa;font-size:.84rem;margin-bottom:.5rem;font-weight:600">{tu.get("area","")}</div>'
        f'<div style="color:#8ea8cc;font-size:.82rem;line-height:1.68;margin-bottom:1rem;max-width:560px">{tu.get("bio","Sem biografia.")}</div>'
        f'<div style="display:flex;gap:2rem;flex-wrap:wrap">'
        f'<div><span style="font-weight:800;font-family:Playfair Display,serif;font-size:1.1rem">{tu.get("followers",0)}</span><span style="color:#3d5070;font-size:.73rem"> seguidores</span></div>'
        f'<div><span style="font-weight:800;font-family:Playfair Display,serif;font-size:1.1rem">{tu.get("following",0)}</span><span style="color:#3d5070;font-size:.73rem"> seguindo</span></div>'
        f'<div><span style="font-weight:800;font-family:Playfair Display,serif;font-size:1.1rem">{len(user_posts)}</span><span style="color:#3d5070;font-size:.73rem"> pesquisas</span></div>'
        f'<div><span style="font-weight:800;font-family:Playfair Display,serif;font-size:1.1rem">{fmt_num(total_likes)}</span><span style="color:#3d5070;font-size:.73rem"> curtidas</span></div>'
        f'</div></div></div>',
        unsafe_allow_html=True
    )
    if not is_me:
        c1, c2, _ = st.columns([1,1,3])
        with c1:
            lbl = "Seguindo" if is_fol else "Seguir"
            if st.button(lbl, key="pf_fol", use_container_width=True):
                if is_fol: st.session_state.followed.remove(target_email); tu["followers"] = max(0,tu.get("followers",0)-1)
                else: st.session_state.followed.append(target_email); tu["followers"] = tu.get("followers",0)+1
                save_db(); st.rerun()
        with c2:
            if st.button("Mensagem", key="pf_chat", use_container_width=True):
                if target_email not in st.session_state.chat_messages: st.session_state.chat_messages[target_email] = []
                st.session_state.active_chat = target_email; st.session_state.page = "chat"; st.rerun()

    st.markdown('<div class="dtxt">Pesquisas publicadas</div>', unsafe_allow_html=True)
    if user_posts:
        for p in sorted(user_posts,key=lambda x:x.get("date",""),reverse=True):
            render_post(p,ctx="profile",show_author=False)
    else:
        st.markdown('<div class="card" style="padding:2.5rem;text-align:center;color:#3d5070">Nenhuma pesquisa publicada ainda.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────
# POST CARD
# ─────────────────────────────────────────────────
def render_post(post, ctx="feed", show_author=True, compact=False):
    email = st.session_state.current_user
    pid = post["id"]
    liked = email in post.get("liked_by",[])
    saved = email in post.get("saved_by",[])
    aemail = post.get("author_email","")
    aphoto = get_photo(aemail)
    ain = post.get("avatar","??"); aname = post.get("author","?"); aarea = post.get("area","")
    dt = time_ago(post.get("date","")); views = post.get("views",random.randint(80,500))
    abstract = post.get("abstract","")
    if compact and len(abstract)>200: abstract = abstract[:200]+"…"

    if show_author:
        if aphoto:
            av_html = f'<div class="av" style="width:40px;height:40px;font-size:13px"><img src="{aphoto}"/></div>'
        else:
            av_html = f'<div class="av" style="width:40px;height:40px;font-size:13px">{ain}</div>'
        v_mark = " ✓" if st.session_state.users.get(aemail,{}).get("verified") else ""
        header = (
            f'<div style="padding:1rem 1.2rem .65rem;display:flex;align-items:center;gap:10px;border-bottom:1px solid rgba(22,32,64,.8)">'
            f'{av_html}'
            f'<div style="flex:1;min-width:0">'
            f'<div style="font-family:Outfit,sans-serif;font-weight:700;font-size:.88rem;color:#dde6f5">{aname}<span style="font-size:.62rem;color:#22d3ee">{v_mark}</span></div>'
            f'<div style="color:#3d5070;font-size:.67rem;margin-top:1px">{aarea} · {dt}</div>'
            f'</div>{badge(post["status"])}</div>'
        )
    else:
        header = (
            f'<div style="padding:.45rem 1.2rem .25rem;display:flex;justify-content:space-between;align-items:center">'
            f'<span style="color:#3d5070;font-size:.67rem">{dt}</span>{badge(post["status"])}</div>'
        )

    tgs = tags_html(post.get("tags",[]))
    st.markdown(
        f'<div class="post">{header}'
        f'<div style="padding:.8rem 1.2rem">'
        f'<div style="font-family:Playfair Display,serif;font-size:1rem;font-weight:700;margin-bottom:.45rem;line-height:1.45;color:#dde6f5">{post["title"]}</div>'
        f'<div style="color:#8ea8cc;font-size:.82rem;line-height:1.68;margin-bottom:.65rem">{abstract}</div>'
        f'<div>{tgs}</div>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    heart = "❤" if liked else "♡"
    book  = "◆" if saved else "◇"
    nc = len(post.get("comments",[]))

    ca, cb, cc, cd, ce, cf = st.columns([1.1,1,.8,.7,1,1.1])
    with ca:
        if st.button(f"{heart}  {fmt_num(post['likes'])}", key=f"lk_{ctx}_{pid}", use_container_width=True):
            if liked: post["liked_by"].remove(email); post["likes"] = max(0,post["likes"]-1)
            else: post["liked_by"].append(email); post["likes"] += 1; record(post.get("tags",[]),1.5)
            save_db(); st.rerun()
    with cb:
        if st.button(f"Comentar  {nc}", key=f"cm_{ctx}_{pid}", use_container_width=True):
            k = f"cmt_{ctx}_{pid}"; st.session_state[k] = not st.session_state.get(k,False); st.rerun()
    with cc:
        if st.button(book, key=f"sv_{ctx}_{pid}", use_container_width=True):
            if saved: post["saved_by"].remove(email)
            else: post["saved_by"].append(email)
            save_db(); st.rerun()
    with cd:
        if st.button("↗", key=f"sh_{ctx}_{pid}", use_container_width=True):
            k = f"shr_{ctx}_{pid}"; st.session_state[k] = not st.session_state.get(k,False); st.rerun()
    with ce:
        st.markdown(f'<div style="text-align:center;color:#3d5070;font-size:.70rem;padding:.5rem 0;line-height:1">Visualizações<br><span style="color:#8ea8cc;font-weight:600">{fmt_num(views)}</span></div>', unsafe_allow_html=True)
    with cf:
        if show_author and aemail:
            first = aname.split()[0] if aname else "?"
            if st.button(f"Perfil · {first}", key=f"vp_{ctx}_{pid}", use_container_width=True):
                st.session_state.profile_view = aemail; st.rerun()

    if st.session_state.get(f"shr_{ctx}_{pid}",False):
        url = f"https://nebula.ai/post/{pid}"; title_enc = post['title'][:50].replace(" ","%20")
        st.markdown(
            f'<div class="card" style="padding:.9rem 1.2rem;margin-bottom:.5rem">'
            f'<div style="font-family:Outfit,sans-serif;font-weight:700;font-size:.82rem;margin-bottom:.7rem;color:#8ea8cc">Compartilhar pesquisa</div>'
            f'<div style="display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:.6rem">'
            f'<a href="https://twitter.com/intent/tweet?text={title_enc}" target="_blank" class="share-link" style="background:rgba(29,161,242,.1);border:1px solid rgba(29,161,242,.2);color:#1da1f2">X · Twitter</a>'
            f'<a href="https://linkedin.com/sharing/share-offsite/?url={url}" target="_blank" class="share-link" style="background:rgba(10,102,194,.1);border:1px solid rgba(10,102,194,.2);color:#0a66c2">LinkedIn</a>'
            f'<a href="https://wa.me/?text={title_enc}%20{url}" target="_blank" class="share-link" style="background:rgba(37,211,102,.08);border:1px solid rgba(37,211,102,.18);color:#25d366">WhatsApp</a>'
            f'</div>'
            f'<code style="font-size:.68rem;color:#3d5070;background:rgba(0,0,0,.4);padding:3px 8px;border-radius:5px">{url}</code>'
            f'</div>',
            unsafe_allow_html=True
        )

    if st.session_state.get(f"cmt_{ctx}_{pid}",False):
        comments = post.get("comments",[])
        for c in comments:
            c_in = ini(c["user"]); c_email = next((e for e,u in st.session_state.users.items() if u.get("name")==c["user"]),""); c_photo = get_photo(c_email)
            av_c = avh(c_in,28,c_photo)
            st.markdown(f'<div class="cmt"><div style="display:flex;align-items:center;gap:8px;margin-bottom:.25rem">{av_c}<span style="font-size:.76rem;font-weight:600;color:#60a5fa">{c["user"]}</span></div><div style="font-size:.79rem;color:#8ea8cc;line-height:1.55;padding-left:36px">{c["text"]}</div></div>', unsafe_allow_html=True)
        nc_txt = st.text_input("",placeholder="Escreva um comentário…",key=f"ci_{ctx}_{pid}",label_visibility="collapsed")
        if st.button("Enviar", key=f"cs_{ctx}_{pid}"):
            if nc_txt:
                uu = guser(); post["comments"].append({"user":uu.get("name","Você"),"text":nc_txt})
                record(post.get("tags",[]),.8); save_db(); st.rerun()

# ─────────────────────────────────────────────────
# FEED PAGE
# ─────────────────────────────────────────────────
def page_feed():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    email = st.session_state.current_user; u = guser()
    uname = u.get("name","?"); uphoto = u.get("photo_b64"); uin = ini(uname)
    users = st.session_state.users if isinstance(st.session_state.users,dict) else {}

    col_main, col_side = st.columns([2, 0.9], gap="medium")

    with col_main:
        # ════════════════════════════════
        # STORY ROW — fully clickable
        # ════════════════════════════════
        story_researchers = [(ue,ud) for ue,ud in users.items() if ue != email][:6]
        total_stories = 1 + len(story_researchers)
        story_cols = st.columns(total_stories)

        # My story / compose trigger
        with story_cols[0]:
            is_open = st.session_state.get("compose_open",False)
            ring_color = "rgba(34,211,238,.9)" if is_open else "rgba(59,130,246,.5)"
            glow = "0 0 0 3px rgba(6,182,212,.25), 0 4px 16px rgba(0,0,0,.5)" if is_open else "0 4px 16px rgba(0,0,0,.5)"

            if uphoto:
                av_content = f'<img src="{uphoto}" style="width:100%;height:100%;object-fit:cover;border-radius:50%"/>'
            else:
                av_content = f'<div style="font-size:1.2rem;font-weight:800;font-family:Outfit,sans-serif;color:white">{uin}</div>'

            # The + badge
            plus_badge = (
                '<div style="position:absolute;bottom:-2px;right:-2px;'
                'width:20px;height:20px;border-radius:50%;'
                f'background:{"linear-gradient(135deg,#06b6d4,#2563eb)" if is_open else "linear-gradient(135deg,#2563eb,#1d4ed8)"};'
                'border:2px solid #04060e;'
                'display:flex;align-items:center;justify-content:center;'
                'font-size:.8rem;font-weight:900;color:white;'
                'box-shadow:0 2px 8px rgba(0,0,0,.5)">+</div>'
            )

            st.markdown(
                f'<div style="text-align:center;padding:6px 0">'
                f'<div style="position:relative;width:64px;height:64px;margin:0 auto 8px;'
                f'border-radius:50%;'
                f'background:linear-gradient(135deg,#1e3a8a,#2563eb);'
                f'border:2.5px solid {ring_color};'
                f'overflow:hidden;cursor:pointer;'
                f'box-shadow:{glow};'
                f'display:flex;align-items:center;justify-content:center;'
                f'transition:all .2s">'
                f'{av_content}{plus_badge}</div>'
                f'<div style="font-size:.65rem;font-weight:600;color:{"#22d3ee" if is_open else "#60a5fa"}'
                f';letter-spacing:.02em">{"Publicando" if is_open else "Nova Pesquisa"}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            if st.button("Nova Pesquisa", key="story_compose_btn", use_container_width=True,
                         help="Clique para publicar uma nova pesquisa"):
                st.session_state.compose_open = not st.session_state.get("compose_open",False); st.rerun()

        for col_idx, (ue, ud) in enumerate(story_researchers):
            sname = ud.get("name","?"); sin = ini(sname); sphoto = ud.get("photo_b64")
            is_fol = ue in st.session_state.followed
            ring_color = "rgba(34,211,238,.7)" if is_fol else "rgba(59,130,246,.25)"
            online = random.Random(ue).random() > 0.45

            if sphoto:
                photo_content = f'<img src="{sphoto}" style="width:100%;height:100%;object-fit:cover;border-radius:50%"/>'
            else:
                photo_content = f'<span style="font-size:1.2rem;font-weight:700;font-family:Outfit,sans-serif;color:white">{sin}</span>'

            first_name = sname.split()[0]
            short_area = ud.get("area","")[:10]

            online_html = (
                '<div style="width:8px;height:8px;border-radius:50%;background:#10b981;'
                'margin:0 auto 3px;box-shadow:0 0 6px #10b981"></div>'
            ) if online and is_fol else (
                '<div style="height:11px"></div>'
            )

            with story_cols[col_idx+1]:
                st.markdown(
                    f'<div style="text-align:center;padding:6px 0">'
                    f'<div style="position:relative;width:64px;height:64px;margin:0 auto 4px;'
                    f'border-radius:50%;background:linear-gradient(135deg,#1e3a8a,#2563eb);'
                    f'border:2.5px solid {ring_color};overflow:hidden;'
                    f'display:flex;align-items:center;justify-content:center;'
                    f'box-shadow:0 4px 14px rgba(0,0,0,.45);cursor:pointer;'
                    f'transition:transform .2s">'
                    f'{photo_content}</div>'
                    f'{online_html}'
                    f'<div style="font-size:.65rem;font-weight:600;color:#8ea8cc;'
                    f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:72px;margin:0 auto">{first_name}</div>'
                    f'<div style="font-size:.58rem;color:#3d5070;overflow:hidden;'
                    f'text-overflow:ellipsis;white-space:nowrap;max-width:72px;margin:0 auto">{short_area}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                if st.button("Ver Perfil", key=f"story_{ue}", use_container_width=True, help=f"Ver perfil de {sname}"):
                    st.session_state.profile_view = ue; st.rerun()

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        # ════════════════════════════════
        # COMPOSE PANEL
        # ════════════════════════════════
        if st.session_state.get("compose_open",False):
            st.markdown('<div class="compose-card">', unsafe_allow_html=True)
            if uphoto:
                av_c = f'<div class="av" style="width:42px;height:42px"><img src="{uphoto}"/></div>'
            else:
                av_c = f'<div class="av" style="width:42px;height:42px;font-size:14px">{uin}</div>'
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:1rem">'
                f'{av_c}<div>'
                f'<div style="font-family:Outfit,sans-serif;font-size:.92rem;font-weight:700">{uname}</div>'
                f'<div style="font-size:.68rem;color:#3d5070">{u.get("area","Pesquisadora")}</div>'
                f'</div></div>',
                unsafe_allow_html=True
            )

            np_t  = st.text_input("Título da pesquisa *", key="np_t",
                                   placeholder="Ex: Efeitos da meditação na neuroplasticidade…")
            np_ab = st.text_area("Resumo / Abstract *", key="np_ab", height=110,
                                  placeholder="Descreva sua pesquisa, metodologia e resultados principais…")
            c1c, c2c = st.columns(2)
            with c1c:
                np_tg = st.text_input("Tags (separadas por vírgula)", key="np_tg",
                                       placeholder="neurociência, fMRI, cognição")
            with c2c:
                np_st = st.selectbox("Status", ["Em andamento","Publicado","Concluído"], key="np_st")

            col_pub, col_cancel = st.columns([2,1])
            with col_pub:
                if st.button("Publicar Pesquisa", key="btn_pub", use_container_width=True):
                    if not np_t or not np_ab:
                        st.warning("Título e resumo são obrigatórios.")
                    else:
                        tags = [t.strip() for t in np_tg.split(",") if t.strip()] if np_tg else []
                        new_p = {
                            "id": len(st.session_state.feed_posts)+200+random.randint(0,99),
                            "author":uname,"author_email":email,"avatar":uin,"area":u.get("area",""),
                            "title":np_t,"abstract":np_ab,"tags":tags,"likes":0,"comments":[],
                            "status":np_st,"date":datetime.now().strftime("%Y-%m-%d"),
                            "liked_by":[],"saved_by":[],"connections":tags[:3],"views":1
                        }
                        st.session_state.feed_posts.insert(0,new_p)
                        record(tags,2.0); save_db()
                        st.session_state.compose_open = False
                        st.success("Pesquisa publicada com sucesso!")
                        st.rerun()
            with col_cancel:
                if st.button("Cancelar", key="btn_cancel", use_container_width=True):
                    st.session_state.compose_open = False; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        else:
            # COLLAPSED COMPOSE PROMPT — clicking opens compose
            if uphoto:
                av_c2 = f'<div class="av" style="width:38px;height:38px"><img src="{uphoto}"/></div>'
            else:
                av_c2 = f'<div class="av" style="width:38px;height:38px;font-size:12px">{uin}</div>'

            st.markdown(
                f'<div class="compose-float">'
                f'<div style="display:flex;align-items:center;gap:12px">'
                f'{av_c2}'
                f'<div style="flex:1;background:rgba(4,6,14,.55);border:1px solid var(--border);'
                f'border-radius:40px;padding:.55rem 1.1rem;color:#3d5070;font-size:.84rem">'
                f'No que você está pesquisando, {uname.split()[0]}?'
                f'</div></div></div>',
                unsafe_allow_html=True
            )
            if st.button("Clique para escrever sua pesquisa", key="open_compose_from_prompt",
                         use_container_width=True):
                st.session_state.compose_open = True; st.rerun()

        # FILTER
        ff = st.radio("", ["Todos","Seguidos","Salvos","Populares"],
                      horizontal=True, key="ff", label_visibility="collapsed")

        # RECOMMENDATIONS
        recs = get_recs(email,2)
        if recs and "Seguidos" not in ff and "Salvos" not in ff:
            st.markdown('<div class="dtxt"><span class="badge-rec">Recomendado para você</span></div>', unsafe_allow_html=True)
            for p in recs: render_post(p,ctx="rec",compact=True)
            st.markdown('<div class="dtxt">Mais pesquisas</div>', unsafe_allow_html=True)

        # POSTS
        posts = list(st.session_state.feed_posts)
        if "Seguidos" in ff: posts = [p for p in posts if p.get("author_email") in st.session_state.followed]
        elif "Salvos" in ff: posts = [p for p in posts if email in p.get("saved_by",[])]
        elif "Populares" in ff: posts = sorted(posts,key=lambda p:p["likes"],reverse=True)
        else: posts = sorted(posts,key=lambda p:p.get("date",""),reverse=True)

        if not posts:
            st.markdown('<div class="card" style="padding:3.5rem;text-align:center"><div style="font-size:2.5rem;margin-bottom:1rem;opacity:.3">⬡</div><div style="color:#3d5070;font-family:Playfair Display,serif">Nenhuma pesquisa aqui ainda.</div></div>', unsafe_allow_html=True)
        else:
            for p in posts: render_post(p,ctx="feed")

    # ════════════════════════════════
    # SIDEBAR
    # ════════════════════════════════
    with col_side:
        sq = st.text_input("", placeholder="Buscar pesquisadores…", key="ppl_s", label_visibility="collapsed")

        st.markdown('<div class="sc">', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-family:Outfit,sans-serif;font-weight:700;font-size:.84rem;'
            'margin-bottom:.9rem;display:flex;align-items:center;justify-content:space-between">'
            '<span>Quem seguir</span>'
            '<span style="font-size:.65rem;color:#3d5070;font-weight:500">Sugestões</span>'
            '</div>',
            unsafe_allow_html=True
        )
        shown_n = 0
        for ue, ud in list(users.items()):
            if ue == email or shown_n >= 5: continue
            rname = ud.get("name","?")
            if sq and sq.lower() not in rname.lower() and sq.lower() not in ud.get("area","").lower(): continue
            shown_n += 1
            is_fol = ue in st.session_state.followed
            uphoto_r = ud.get("photo_b64"); uin_r = ini(rname)
            online = random.Random(ue+"x").random() > 0.45
            dot = '<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            av_r = avh(uin_r,34,uphoto_r)
            st.markdown(
                f'<div class="person-row">{av_r}'
                f'<div style="flex:1;min-width:0">'
                f'<div style="font-size:.80rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{dot}{rname}</div>'
                f'<div style="font-size:.65rem;color:#3d5070">{ud.get("area","")[:22]}</div>'
                f'</div></div>',
                unsafe_allow_html=True
            )
            cb_f, cb_v = st.columns(2)
            with cb_f:
                lbl_f = "Seguindo" if is_fol else "Seguir"
                if st.button(lbl_f, key=f"sf_{ue}", use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"] = max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"] = ud.get("followers",0)+1
                    save_db(); st.rerun()
            with cb_v:
                if st.button("Perfil", key=f"svr_{ue}", use_container_width=True):
                    st.session_state.profile_view = ue; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sc">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:Outfit,sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.9rem">Em Alta</div>', unsafe_allow_html=True)
        trending = [("Quantum ML","34 pesquisas"),("CRISPR 2026","28 pesquisas"),("Neuroplasticidade","22 pesquisas"),("LLMs Científicos","19 pesquisas"),("Matéria Escura","15 pesquisas")]
        for i, (topic, cnt) in enumerate(trending):
            st.markdown(
                f'<div style="padding:.45rem .5rem;border-radius:var(--r12);border:1px solid transparent;transition:all .15s;margin-bottom:2px;cursor:pointer">'
                f'<div style="font-size:.63rem;color:#3d5070;margin-bottom:1px">#{i+1}</div>'
                f'<div style="font-size:.80rem;font-weight:600">{topic}</div>'
                f'<div style="font-size:.63rem;color:#3d5070">{cnt}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.notifications:
            st.markdown('<div class="sc">', unsafe_allow_html=True)
            st.markdown('<div style="font-family:Outfit,sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.8rem">Atividade</div>', unsafe_allow_html=True)
            for notif in st.session_state.notifications[:3]:
                st.markdown(f'<div style="font-size:.73rem;color:#8ea8cc;padding:.38rem 0;border-bottom:1px solid var(--border)">· {notif}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────
# SEARCH PAGE
# ─────────────────────────────────────────────────
def page_search():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem">Busca Acadêmica</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:#3d5070;font-size:.80rem;margin-bottom:1rem">Semantic Scholar · CrossRef · Nebula</p>', unsafe_allow_html=True)

    c1, c2 = st.columns([4,1])
    with c1: q = st.text_input("",placeholder="Ex: 'CRISPR gene editing' · 'quantum ML'…",key="sq",label_visibility="collapsed")
    with c2:
        if st.button("Buscar",use_container_width=True,key="btn_s"):
            if q:
                with st.spinner("Buscando…"):
                    nebula_r = [p for p in st.session_state.feed_posts if q.lower() in p["title"].lower() or q.lower() in p["abstract"].lower() or any(q.lower() in t.lower() for t in p.get("tags",[]))]
                    ss_r = search_ss(q,6); cr_r = search_cr(q,4)
                    st.session_state.search_results = {"nebula":nebula_r,"ss":ss_r,"cr":cr_r}
                    st.session_state.last_sq = q; record([q.lower()],.3)

    if st.session_state.get("search_results") and st.session_state.get("last_sq"):
        res = st.session_state.search_results
        neb = res.get("nebula",[]); ss = res.get("ss",[]); cr = res.get("cr",[])
        web = ss + [x for x in cr if not any(x["title"].lower()==s["title"].lower() for s in ss)]
        total = len(neb)+len(web)
        tab_all, tab_neb, tab_web = st.tabs([f"  Todos ({total})  ",f"  Nebula ({len(neb)})  ",f"  Internet ({len(web)})  "])
        with tab_all:
            if neb:
                st.markdown('<div style="font-size:.64rem;color:#60a5fa;font-weight:700;margin-bottom:.5rem;letter-spacing:.09em;text-transform:uppercase">Na Nebula</div>', unsafe_allow_html=True)
                for p in neb: render_post(p,ctx="srch_all",compact=True)
            if web:
                if neb: st.markdown('<hr>', unsafe_allow_html=True)
                st.markdown('<div style="font-size:.64rem;color:#22d3ee;font-weight:700;margin-bottom:.5rem;letter-spacing:.09em;text-transform:uppercase">Bases Acadêmicas</div>', unsafe_allow_html=True)
                for idx,a in enumerate(web): render_web_article(a,idx=idx,ctx="all_w")
            if not neb and not web: st.info("Nenhum resultado. Tente outros termos.")
        with tab_neb:
            if neb:
                for p in neb: render_post(p,ctx="srch_neb",compact=True)
            else: st.info("Nenhuma pesquisa na Nebula para estes termos.")
        with tab_web:
            if web:
                for idx,a in enumerate(web): render_web_article(a,idx=idx,ctx="web_t")
            else: st.info("Nenhum artigo online encontrado.")
    st.markdown('</div>', unsafe_allow_html=True)

def render_web_article(a, idx=0, ctx="web"):
    src_color = "#22d3ee" if a.get("origin")=="semantic" else "#a78bfa"
    src_name = "Semantic Scholar" if a.get("origin")=="semantic" else "CrossRef"
    cite = f" · {a['citations']} cit." if a.get("citations") else ""
    uid = re.sub(r'[^a-zA-Z0-9]','',f"{ctx}_{idx}_{str(a.get('doi',''))[:10]}")[:32]
    is_saved = any(s.get('doi')==a.get('doi') for s in st.session_state.saved_articles)
    abstract = (a.get("abstract","") or "")[:260]
    if len(a.get("abstract",""))>260: abstract += "…"
    st.markdown(
        f'<div class="scard">'
        f'<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:.35rem">'
        f'<div style="flex:1;font-family:Playfair Display,serif;font-size:.9rem;font-weight:700">{a["title"]}</div>'
        f'<span style="font-size:.62rem;color:{src_color};background:rgba(6,182,212,.06);border-radius:8px;padding:2px 8px;white-space:nowrap;flex-shrink:0">{src_name}</span>'
        f'</div>'
        f'<div style="color:#3d5070;font-size:.68rem;margin-bottom:.4rem">{a["authors"]} · <em>{a["source"]}</em> · {a["year"]}{cite}</div>'
        f'<div style="color:#8ea8cc;font-size:.79rem;line-height:1.65">{abstract}</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    ca, cb, cc = st.columns(3)
    with ca:
        lbl_sv = "Salvo" if is_saved else "Salvar"
        if st.button(lbl_sv,key=f"svw_{uid}"):
            if is_saved: st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]; st.toast("Removido")
            else: st.session_state.saved_articles.append(a); st.toast("Salvo!")
            save_db(); st.rerun()
    with cb:
        if st.button("Citar APA",key=f"ctw_{uid}"):
            st.toast(f'{a["authors"]} ({a["year"]}). {a["title"]}.')
    with cc:
        if a.get("url"):
            st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:#60a5fa;font-size:.79rem;text-decoration:none;line-height:2.5;display:block">Abrir artigo ↗</a>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────
# KNOWLEDGE PAGE
# ─────────────────────────────────────────────────
def page_knowledge():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem">Rede de Conexões</h1>', unsafe_allow_html=True)
    email = st.session_state.current_user
    users = st.session_state.users if isinstance(st.session_state.users,dict) else {}

    def get_tags(ue):
        ud = users.get(ue,{}); tags = set(area_to_tags(ud.get("area","")))
        for p in st.session_state.feed_posts:
            if p.get("author_email")==ue: tags.update(t.lower() for t in p.get("tags",[]))
        if ue==email:
            for _,fd in st.session_state.folders.items():
                if isinstance(fd,dict): tags.update(t.lower() for t in fd.get("analysis_tags",[]))
        return tags

    rlist = list(users.keys()); rtags = {ue:get_tags(ue) for ue in rlist}
    edges = []
    for i in range(len(rlist)):
        for j in range(i+1,len(rlist)):
            e1,e2 = rlist[i],rlist[j]; common = list(rtags[e1]&rtags[e2])
            is_fol = e2 in st.session_state.followed or e1 in st.session_state.followed
            if common or is_fol: edges.append((e1,e2,common[:5],len(common)+(2 if is_fol else 0)))

    n = len(rlist); pos = {}
    for idx,ue in enumerate(rlist):
        angle = 2*3.14159*idx/max(n,1); r_d = 0.36+0.05*((hash(ue)%5)/4)
        pos[ue] = {"x":0.5+r_d*np.cos(angle),"y":0.5+r_d*np.sin(angle),"z":0.5+0.12*((idx%4)/3-.35)}

    fig = go.Figure()
    for e1,e2,common,strength in edges:
        p1=pos[e1]; p2=pos[e2]; alpha=min(0.55,0.10+strength*0.06)
        fig.add_trace(go.Scatter3d(x=[p1["x"],p2["x"],None],y=[p1["y"],p2["y"],None],z=[p1["z"],p2["z"],None],mode="lines",line=dict(color=f"rgba(59,130,246,{alpha:.2f})",width=min(4,1+strength)),hoverinfo="none",showlegend=False))

    ncolors = ["#22d3ee" if ue==email else ("#60a5fa" if ue in st.session_state.followed else "#2563eb") for ue in rlist]
    nsizes  = [24 if ue==email else (18 if ue in st.session_state.followed else max(12,10+sum(1 for e1,e2,_,__ in edges if e1==ue or e2==ue))) for ue in rlist]
    ntext   = [users.get(ue,{}).get("name","?").split()[0] for ue in rlist]
    nhover  = [f"<b>{users.get(ue,{}).get('name','?')}</b><br>Área: {users.get(ue,{}).get('area','')}<extra></extra>" for ue in rlist]
    fig.add_trace(go.Scatter3d(x=[pos[ue]["x"] for ue in rlist],y=[pos[ue]["y"] for ue in rlist],z=[pos[ue]["z"] for ue in rlist],mode="markers+text",marker=dict(size=nsizes,color=ncolors,opacity=.9,line=dict(color="rgba(147,197,253,.22)",width=1.5)),text=ntext,textposition="top center",textfont=dict(color="#3d5070",size=9,family="Outfit"),hovertemplate=nhover,showlegend=False))
    fig.update_layout(height=480,scene=dict(xaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),yaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),zaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),bgcolor="rgba(0,0,0,0)"),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0),font=dict(color="#3d5070"))
    st.plotly_chart(fig,use_container_width=True)

    c1,c2,c3,c4 = st.columns(4)
    for col,(v,l) in zip([c1,c2,c3,c4],[(len(rlist),"Pesquisadores"),(len(edges),"Conexões"),(len(st.session_state.followed),"Seguindo"),(len(st.session_state.feed_posts),"Pesquisas")]):
        with col: st.markdown(f'<div class="mbox"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>',unsafe_allow_html=True)

    st.markdown("<hr>",unsafe_allow_html=True)
    tab_map,tab_mine,tab_all = st.tabs(["  Mapa  ","  Minhas Conexões  ","  Todos  "])

    with tab_map:
        for e1,e2,common,strength in sorted(edges,key=lambda x:-x[3])[:20]:
            n1=users.get(e1,{}); n2=users.get(e2,{})
            ts = tags_html(common[:4]) if common else '<span style="color:#3d5070;font-size:.70rem">seguimento</span>'
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><span style="font-size:.82rem;font-weight:700;font-family:Outfit,sans-serif;color:#60a5fa">{n1.get("name","?")}</span><span style="color:#3d5070">↔</span><span style="font-size:.82rem;font-weight:700;font-family:Outfit,sans-serif;color:#60a5fa">{n2.get("name","?")}</span><div style="flex:1">{ts}</div><span style="font-size:.67rem;color:#22d3ee;font-weight:700">{strength}</span></div></div>',unsafe_allow_html=True)

    with tab_mine:
        my_conn = [(e1,e2,c,s) for e1,e2,c,s in edges if e1==email or e2==email]
        if not my_conn: st.info("Siga pesquisadores e publique pesquisas para ver conexões.")
        for e1,e2,common,strength in sorted(my_conn,key=lambda x:-x[3]):
            other = e2 if e1==email else e1; od = users.get(other,{})
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">{avh(ini(od.get("name","?")),38,get_photo(other))}<div style="flex:1"><div style="font-weight:700;font-size:.86rem;font-family:Outfit,sans-serif">{od.get("name","?")}</div><div style="font-size:.69rem;color:#3d5070">{od.get("area","")}</div></div>{tags_html(common[:3])}</div></div>',unsafe_allow_html=True)
            cv,cm_b,_ = st.columns([1,1,4])
            with cv:
                if st.button("Perfil",key=f"kv_{other}"): st.session_state.profile_view=other; st.rerun()
            with cm_b:
                if st.button("Chat",key=f"kc_{other}"):
                    if other not in st.session_state.chat_messages: st.session_state.chat_messages[other]=[]
                    st.session_state.active_chat=other; st.session_state.page="chat"; st.rerun()

    with tab_all:
        sq2 = st.text_input("",placeholder="Buscar pesquisadores…",key="all_s",label_visibility="collapsed")
        for ue,ud in users.items():
            if ue==email: continue
            rn=ud.get("name","?"); uarea=ud.get("area","")
            if sq2 and sq2.lower() not in rn.lower() and sq2.lower() not in uarea.lower(): continue
            is_fol=ue in st.session_state.followed
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:10px">{avh(ini(rn),38,get_photo(ue))}<div style="flex:1"><div style="font-size:.86rem;font-weight:700;font-family:Outfit,sans-serif">{rn}</div><div style="font-size:.69rem;color:#3d5070">{uarea}</div></div></div></div>',unsafe_allow_html=True)
            ca2,cb2,cc2=st.columns(3)
            with ca2:
                if st.button("Perfil",key=f"av_{ue}",use_container_width=True): st.session_state.profile_view=ue; st.rerun()
            with cb2:
                if st.button("Seguindo" if is_fol else "Seguir",key=f"af_{ue}",use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"]=max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                    save_db(); st.rerun()
            with cc2:
                if st.button("Chat",key=f"ac_{ue}",use_container_width=True):
                    if ue not in st.session_state.chat_messages: st.session_state.chat_messages[ue]=[]
                    st.session_state.active_chat=ue; st.session_state.page="chat"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────
# FOLDERS PAGE
# ─────────────────────────────────────────────────
def page_folders():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem">Pastas de Pesquisa</h1>', unsafe_allow_html=True)
    c1,c2,_ = st.columns([2,1.2,1.5])
    with c1: nf_name=st.text_input("Nome da pasta",placeholder="Ex: Genômica Comparativa",key="nf_n")
    with c2: nf_desc=st.text_input("Descrição",placeholder="Breve descrição",key="nf_d")
    if st.button("Criar pasta",key="btn_nf"):
        if nf_name.strip():
            if nf_name not in st.session_state.folders:
                st.session_state.folders[nf_name]={"desc":nf_desc,"files":[],"notes":"","analysis_tags":[],"analysis_summary":"","file_analyses":[]}
                save_db(); st.success(f"Pasta '{nf_name}' criada!"); st.rerun()
            else: st.warning("Pasta já existe.")
        else: st.warning("Digite um nome.")
    st.markdown("<hr>",unsafe_allow_html=True)
    if not st.session_state.folders:
        st.markdown('<div class="card" style="text-align:center;padding:4rem"><div style="font-size:2.5rem;margin-bottom:1rem;opacity:.2">▣</div><div style="color:#3d5070;font-family:Playfair Display,serif;font-size:1rem">Nenhuma pasta criada ainda</div></div>',unsafe_allow_html=True)
    else:
        cols = st.columns(3)
        for idx,(fname,fdata) in enumerate(list(st.session_state.folders.items())):
            files=fdata.get("files",[]) if isinstance(fdata,dict) else fdata
            desc=fdata.get("desc","") if isinstance(fdata,dict) else ""
            at=fdata.get("analysis_tags",[]) if isinstance(fdata,dict) else []
            with cols[idx%3]:
                st.markdown(f'<div class="card" style="padding:1.3rem;text-align:center;margin-bottom:.6rem"><div style="font-size:2.2rem;margin-bottom:8px;opacity:.6">▣</div><div style="font-family:Outfit,sans-serif;font-weight:700;font-size:.96rem">{fname}</div><div style="color:#3d5070;font-size:.68rem;margin-top:3px">{desc}</div><div style="color:#60a5fa;font-size:.70rem;margin-top:5px">{len(files)} arquivo(s)</div><div style="margin-top:6px">{tags_html(at[:3])}</div></div>',unsafe_allow_html=True)
                with st.expander(f"Abrir '{fname}'"):
                    up=st.file_uploader("",type=None,key=f"up_{fname}",label_visibility="collapsed")
                    if up:
                        lst=fdata["files"] if isinstance(fdata,dict) else fdata
                        if up.name not in lst: lst.append(up.name)
                        save_db(); st.success(f"'{up.name}' adicionado!"); st.rerun()
                    if files:
                        for f in files: st.markdown(f'<div style="font-size:.78rem;padding:5px 0;color:#8ea8cc;border-bottom:1px solid var(--border)">· {f}</div>',unsafe_allow_html=True)
                    else: st.markdown('<p style="color:#3d5070;font-size:.74rem;text-align:center;padding:.5rem">Faça upload de arquivos acima.</p>',unsafe_allow_html=True)
                    st.markdown("<hr>",unsafe_allow_html=True)
                    if st.button("Analisar documentos",key=f"analyze_{fname}",use_container_width=True):
                        if files:
                            with st.spinner("Analisando…"):
                                result=analyze_folder(fname)
                            if result and isinstance(fdata,dict):
                                fdata["analysis_tags"]=result["tags"]; fdata["analysis_summary"]=result["summary"]; fdata["file_analyses"]=result["file_analyses"]
                                save_db(); record(result["tags"],1.5); st.success("Análise concluída!"); st.rerun()
                        else: st.warning("Adicione arquivos antes.")
                    if isinstance(fdata,dict) and fdata.get("analysis_summary"):
                        st.markdown(f'<div class="abox"><div style="font-size:.64rem;color:#3d5070;text-transform:uppercase;letter-spacing:.07em;margin-bottom:4px;font-weight:600">Resumo</div><div style="font-size:.79rem;color:#8ea8cc">{fdata["analysis_summary"]}</div></div>',unsafe_allow_html=True)
                        if at: st.markdown(tags_html(at),unsafe_allow_html=True)
                    note=st.text_area("Notas",value=fdata.get("notes","") if isinstance(fdata,dict) else "",key=f"note_{fname}",height=70)
                    c_sn,c_del=st.columns(2)
                    with c_sn:
                        if st.button("Salvar nota",key=f"sn_{fname}",use_container_width=True):
                            if isinstance(fdata,dict): fdata["notes"]=note
                            save_db(); st.success("Nota salva!")
                    with c_del:
                        if st.button("Excluir pasta",key=f"df_{fname}",use_container_width=True):
                            del st.session_state.folders[fname]; save_db(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────
# ANALYTICS PAGE
# ─────────────────────────────────────────────────
def page_analytics():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem">Painel de Pesquisa</h1>', unsafe_allow_html=True)
    email = st.session_state.current_user; d = st.session_state.stats_data
    pc = dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",font=dict(color="#3d5070",family="Outfit"),margin=dict(l=10,r=10,t=44,b=10),xaxis=dict(showgrid=False,color="#3d5070"),yaxis=dict(showgrid=True,gridcolor="rgba(22,32,64,.4)",color="#3d5070"))
    tab_folders,tab_pubs,tab_impact,tab_pref = st.tabs(["  Pastas  ","  Publicações  ","  Impacto  ","  Interesses  "])

    with tab_folders:
        folders = st.session_state.folders
        if not folders:
            st.markdown('<div class="card" style="text-align:center;padding:3.5rem"><div style="opacity:.2;font-size:2.5rem;margin-bottom:1rem">▣</div><div style="color:#3d5070;font-family:Playfair Display,serif">Crie pastas e analise documentos.</div></div>',unsafe_allow_html=True)
        else:
            total_files=sum(len(fd.get("files",[]) if isinstance(fd,dict) else fd) for fd in folders.values())
            total_analyzed=sum(1 for fd in folders.values() if isinstance(fd,dict) and fd.get("analysis_tags"))
            all_tags_flat=[t for fd in folders.values() if isinstance(fd,dict) for t in fd.get("analysis_tags",[])]
            c1,c2,c3,c4=st.columns(4)
            for col,(v,l) in zip([c1,c2,c3,c4],[(len(folders),"Pastas"),(total_files,"Arquivos"),(total_analyzed,"Analisadas"),(len(set(all_tags_flat)),"Áreas")]):
                with col: st.markdown(f'<div class="mbox"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>',unsafe_allow_html=True)
            fnames=list(folders.keys()); fcounts=[len(fd.get("files",[]) if isinstance(fd,dict) else fd) for fd in folders.values()]
            if any(c>0 for c in fcounts):
                fig=go.Figure(); fig.add_trace(go.Bar(x=fnames,y=fcounts,marker=dict(color=fcounts,colorscale=[[0,"#0c1424"],[.5,"#2563eb"],[1,"#22d3ee"]],line=dict(color="rgba(59,130,246,.18)",width=1)),text=fcounts,textposition="outside",textfont=dict(color="#8ea8cc",size=11)))
                fig.update_layout(title=dict(text="Arquivos por Pasta",font=dict(color="#dde6f5",family="Playfair Display",size=14)),height=250,**pc); st.plotly_chart(fig,use_container_width=True)
            for fname,fdata in folders.items():
                if not isinstance(fdata,dict): continue
                files=fdata.get("files",[]); fa=fdata.get("file_analyses",[]); at=fdata.get("analysis_tags",[])
                with st.expander(f"{fname} — {len(files)} arquivo(s)"):
                    if not files: st.markdown('<p style="color:#3d5070;font-size:.78rem">Nenhum arquivo.</p>',unsafe_allow_html=True); continue
                    if fa:
                        tc2=Counter(x.get("type","Outro") for x in fa); cp,cprog=st.columns([1,1.5])
                        with cp:
                            fig_pie=go.Figure(go.Pie(labels=list(tc2.keys()),values=list(tc2.values()),hole=0.55,marker=dict(colors=["#2563eb","#06b6d4","#3b82f6","#1e3a8a","#8b5cf6"],line=dict(color=["#04060e"]*10,width=2)),textfont=dict(color="white",size=10)))
                            fig_pie.update_layout(title=dict(text="Tipos",font=dict(color="#dde6f5",family="Outfit",size=12)),height=200,plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",legend=dict(font=dict(color="#3d5070",size=9)),margin=dict(l=0,r=0,t=35,b=0)); st.plotly_chart(fig_pie,use_container_width=True)
                        with cprog:
                            st.markdown('<div style="font-size:.64rem;color:#3d5070;text-transform:uppercase;letter-spacing:.07em;margin-bottom:.6rem;font-weight:600">Progresso por arquivo</div>',unsafe_allow_html=True)
                            for item in fa:
                                prog=item.get("progress",50); color="#10b981" if prog>=80 else ("#f59e0b" if prog>=50 else "#ef4444")
                                st.markdown(f'<div style="margin-bottom:.5rem"><div style="display:flex;justify-content:space-between;font-size:.73rem;margin-bottom:3px"><span style="color:#8ea8cc;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:68%">{item["file"][:26]}</span><span style="color:{color};font-weight:700">{prog}%</span></div>{prog_bar(prog,color)}</div>',unsafe_allow_html=True)
                        if at: st.markdown(f'<div style="margin-top:.5rem">{tags_html(at)}</div>',unsafe_allow_html=True)
                    else: st.markdown('<p style="color:#3d5070;font-size:.78rem">Clique em Analisar para ver métricas.</p>',unsafe_allow_html=True)

    with tab_pubs:
        my_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==email]
        if not my_posts: st.markdown('<div class="card" style="text-align:center;padding:2.5rem;color:#3d5070">Publique pesquisas para ver métricas.</div>',unsafe_allow_html=True)
        else:
            c1,c2,c3=st.columns(3)
            with c1: st.markdown(f'<div class="mbox"><div class="mval">{len(my_posts)}</div><div class="mlbl">Pesquisas</div></div>',unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="mbox"><div class="mval">{sum(p["likes"] for p in my_posts)}</div><div class="mlbl">Curtidas</div></div>',unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="mbox"><div class="mval">{sum(len(p.get("comments",[])) for p in my_posts)}</div><div class="mlbl">Comentários</div></div>',unsafe_allow_html=True)
            st.markdown("<br>",unsafe_allow_html=True)
            titles_s=[p["title"][:18]+"…" for p in my_posts]
            fig_eng=go.Figure()
            fig_eng.add_trace(go.Bar(name="Curtidas",x=titles_s,y=[p["likes"] for p in my_posts],marker_color="#2563eb"))
            fig_eng.add_trace(go.Bar(name="Comentários",x=titles_s,y=[len(p.get("comments",[])) for p in my_posts],marker_color="#06b6d4"))
            fig_eng.update_layout(barmode="group",title=dict(text="Engajamento",font=dict(color="#dde6f5",family="Playfair Display",size=14)),height=250,**pc,legend=dict(font=dict(color="#3d5070"))); st.plotly_chart(fig_eng,use_container_width=True)
            for p in sorted(my_posts,key=lambda x:x.get("date",""),reverse=True):
                st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;justify-content:space-between"><div style="font-family:Playfair Display,serif;font-size:.88rem;font-weight:700">{p["title"][:55]}{"…" if len(p["title"])>55 else ""}</div>{badge(p["status"])}</div><div style="font-size:.71rem;color:#3d5070;margin-top:.4rem">{p.get("date","")} · {p["likes"]} curtidas · {len(p.get("comments",[]))} comentários</div><div style="margin-top:.4rem">{tags_html(p.get("tags",[])[:4])}</div></div>',unsafe_allow_html=True)

    with tab_impact:
        c1,c2,c3=st.columns(3)
        with c1: st.markdown(f'<div class="mbox"><div class="mval">{d.get("h_index",4)}</div><div class="mlbl">Índice H</div></div>',unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="mbox"><div class="mval">{d.get("fator_impacto",3.8):.1f}</div><div class="mlbl">Fator de Impacto</div></div>',unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="mbox"><div class="mval">{len(st.session_state.saved_articles)}</div><div class="mlbl">Artigos Salvos</div></div>',unsafe_allow_html=True)
        st.markdown("<hr>",unsafe_allow_html=True)
        new_h=st.number_input("Índice H",0,200,d.get("h_index",4),key="e_h")
        new_fi=st.number_input("Fator de impacto",0.0,100.0,float(d.get("fator_impacto",3.8)),step=0.1,key="e_fi")
        new_notes=st.text_area("Notas",value=d.get("notes",""),key="e_notes",height=80)
        if st.button("Salvar métricas",key="btn_save_m"): d.update({"h_index":new_h,"fator_impacto":new_fi,"notes":new_notes}); st.success("Métricas salvas!")

    with tab_pref:
        prefs=st.session_state.user_prefs.get(email,{})
        if prefs:
            top=sorted(prefs.items(),key=lambda x:-x[1])[:12]; mx=max(s for _,s in top) if top else 1
            c1,c2=st.columns(2)
            for i,(tag,score) in enumerate(top):
                pct=int(score/mx*100); color="#2563eb" if pct>70 else ("#3b82f6" if pct>40 else "#1e3a8a")
                with (c1 if i%2==0 else c2):
                    st.markdown(f'<div style="display:flex;justify-content:space-between;font-size:.77rem;margin-bottom:3px"><span style="color:#8ea8cc">{tag}</span><span style="color:#60a5fa;font-weight:700">{pct}%</span></div>{prog_bar(pct,color)}',unsafe_allow_html=True)
        else: st.info("Interaja com pesquisas e pastas para construir seu perfil de interesses.")
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────
# IMAGE ANALYSIS PAGE
# ─────────────────────────────────────────────────
def page_img_search():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem">Análise Visual Científica</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:#3d5070;font-size:.80rem;margin-bottom:1.2rem">Detecta padrões, estruturas e conecta com pesquisas similares</p>', unsafe_allow_html=True)
    col_up,col_res = st.columns([1,1.9])
    with col_up:
        st.markdown('<div class="card" style="padding:1.2rem">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:Outfit,sans-serif;font-weight:700;font-size:.88rem;margin-bottom:.7rem">Carregar Imagem</div>', unsafe_allow_html=True)
        img_file=st.file_uploader("",type=["png","jpg","jpeg","webp","tiff"],label_visibility="collapsed",key="img_up")
        if img_file: st.image(img_file,use_container_width=True,caption="Imagem carregada")
        run=st.button("Analisar Imagem",use_container_width=True,key="btn_run")
        st.markdown('<div style="margin-top:.9rem;font-size:.68rem;color:#3d5070;line-height:1.9">Detecção Sobel · FFT · Simetria Radial<br>Análise de Cor · Paleta Dominante<br>Busca de pesquisas similares</div>',unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col_res:
        if run and img_file:
            img_file.seek(0)
            with st.spinner("Analisando padrões, bordas, formas e cores…"):
                rep=analyze_image_advanced(img_file); st.session_state.img_result=rep
            if rep:
                conf_c="#10b981" if rep["confidence"]>80 else ("#f59e0b" if rep["confidence"]>60 else "#ef4444")
                st.markdown(f'<div class="abox"><div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:.55rem"><div><div style="font-size:.62rem;color:#3d5070;letter-spacing:.10em;text-transform:uppercase;margin-bottom:4px;font-weight:600">Categoria</div><div style="font-family:Playfair Display,serif;font-size:1.06rem;font-weight:700;margin-bottom:4px">{rep["category"]}</div></div><div style="background:rgba(0,0,0,.3);border:1px solid var(--border);border-radius:12px;padding:.5rem .9rem;text-align:center;flex-shrink:0"><div style="font-family:Playfair Display,serif;font-size:1.4rem;font-weight:800;color:{conf_c}">{rep["confidence"]}%</div><div style="font-size:.58rem;color:#3d5070;text-transform:uppercase;font-weight:600">confiança</div></div></div><div style="font-size:.80rem;color:#8ea8cc;line-height:1.68;margin-bottom:.55rem">{rep["description"]}</div><div style="display:flex;gap:1.5rem;flex-wrap:wrap;font-size:.69rem;color:#3d5070"><span>Material: <strong style="color:#8ea8cc">{rep["material"]}</strong></span><span>Estrutura: <strong style="color:#8ea8cc">{rep["object_type"]}</strong></span><span>Resolução: <strong style="color:#8ea8cc">{rep["size"][0]}×{rep["size"][1]}</strong></span></div></div>',unsafe_allow_html=True)
                c1,c2,c3=st.columns(3); sym_lbl="Alta" if rep["symmetry"]>0.78 else ("Média" if rep["symmetry"]>0.52 else "Baixa")
                with c1: st.markdown(f'<div class="mbox"><div style="font-family:Outfit,sans-serif;font-size:1rem;font-weight:700;color:#60a5fa">{rep["texture"]["complexity"]}</div><div class="mlbl">Complexidade</div></div>',unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="mbox"><div style="font-family:Outfit,sans-serif;font-size:1rem;font-weight:700;color:#60a5fa">{sym_lbl}</div><div class="mlbl">Simetria ({rep["symmetry"]})</div></div>',unsafe_allow_html=True)
                with c3: st.markdown(f'<div class="mbox"><div style="font-family:Outfit,sans-serif;font-size:1rem;font-weight:700;color:#60a5fa">{rep["lines"]["direction"]}</div><div class="mlbl">Linhas Dom.</div></div>',unsafe_allow_html=True)
                l=rep["lines"]; strengths=l["strengths"]; max_s=max(strengths.values())+0.01
                st.markdown('<div class="pbox"><div style="font-family:Outfit,sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.7rem;color:#22d3ee">Análise de Linhas</div>',unsafe_allow_html=True)
                for dir_name,val in strengths.items():
                    pct=int(val/max_s*100); is_dom=dir_name==l["direction"]; color="#22d3ee" if is_dom else "#2563eb"
                    st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:.38rem"><span style="font-size:.69rem;color:{"#22d3ee" if is_dom else "#3d5070"};width:84px;flex-shrink:0">{"★ " if is_dom else ""}{dir_name}</span><div style="flex:1">{prog_bar(pct,color)}</div><span style="font-size:.68rem;color:#3d5070;width:36px;text-align:right">{val:.2f}</span></div>',unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:.69rem;color:#3d5070;margin-top:.5rem">Intensidade: <strong style="color:#8ea8cc">{l["intensity"]:.2f}</strong> · Formas: <strong style="color:#22d3ee">{" · ".join(rep["shapes"])}</strong></div></div>',unsafe_allow_html=True)
                rv,gv,bv=rep["color"]["r"],rep["color"]["g"],rep["color"]["b"]; hex_c="#{:02x}{:02x}{:02x}".format(int(rv),int(gv),int(bv))
                pal_html="".join(f'<div style="display:flex;flex-direction:column;align-items:center;gap:3px"><div style="width:30px;height:30px;border-radius:8px;background:rgb{str(p)};border:1.5px solid rgba(255,255,255,.08)"></div><div style="font-size:.56rem;color:#3d5070">#{"{:02x}{:02x}{:02x}".format(*p).upper()}</div></div>' for p in rep["palette"][:6])
                temp_str="Quente" if rep["color"]["warm"] else ("Fria" if rep["color"]["cool"] else "Neutra")
                st.markdown(f'<div class="abox"><div style="font-family:Outfit,sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.8rem">Análise de Cor</div><div style="display:flex;gap:14px;align-items:center;margin-bottom:.9rem"><div style="width:46px;height:46px;border-radius:12px;background:{hex_c};border:2px solid var(--border);flex-shrink:0"></div><div style="font-size:.78rem;color:#8ea8cc;line-height:1.75">RGB: <strong>({int(rv)}, {int(gv)}, {int(bv)})</strong> · Hex: <strong>{hex_c.upper()}</strong><br>Canal dominante: <strong>{rep["color"]["dom"]}</strong> · Temperatura: <strong>{temp_str}</strong><br>Saturação: <strong>{rep["color"]["sat"]:.0f}%</strong></div></div><div style="font-size:.66rem;color:#3d5070;margin-bottom:7px;text-transform:uppercase;letter-spacing:.06em;font-weight:600">Paleta dominante</div><div style="display:flex;gap:6px;flex-wrap:wrap">{pal_html}</div><div style="margin-top:.8rem;display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:.77rem;color:#3d5070"><div>Entropia: <strong style="color:#dde6f5">{rep["texture"]["entropy"]} bits</strong></div><div>Contraste: <strong style="color:#dde6f5">{rep["texture"]["contrast"]:.2f}</strong></div></div></div>',unsafe_allow_html=True)
        elif not img_file:
            st.markdown('<div class="card" style="padding:5rem 2rem;text-align:center"><div style="font-size:3.5rem;margin-bottom:1.2rem;opacity:.15">⊞</div><div style="font-family:Playfair Display,serif;font-size:1.05rem;color:#8ea8cc;margin-bottom:.7rem">Carregue uma imagem científica</div><div style="color:#3d5070;font-size:.76rem;line-height:2">PNG · JPG · WEBP · TIFF<br>Microscopia · Cristalografia · Fluorescência · Histologia</div></div>',unsafe_allow_html=True)

    if st.session_state.get("img_result"):
        rep=st.session_state.img_result; st.markdown("<hr>",unsafe_allow_html=True)
        st.markdown('<h2>Pesquisas Relacionadas</h2>',unsafe_allow_html=True)
        kw=rep.get("kw","").lower().split(); cat_words=(rep.get("category","")+" "+rep.get("object_type","")+" "+rep.get("material","")).lower().split(); all_terms=list(set(kw+cat_words))
        tab_neb,tab_fol,tab_web=st.tabs(["  Na Nebula  ","  Nas Pastas  ","  Internet  "])
        with tab_neb:
            neb_r=[]
            for p in st.session_state.feed_posts:
                ptxt=(p.get("title","")+" "+p.get("abstract","")+" "+" ".join(p.get("tags",[]))).lower()
                sc=sum(1 for t in all_terms if len(t)>2 and t in ptxt)
                if sc>0: neb_r.append((sc,p))
            neb_r.sort(key=lambda x:-x[0])
            if neb_r:
                for _,p in neb_r[:4]: render_post(p,ctx="img_neb",compact=True)
            else: st.markdown('<div style="color:#3d5070;font-size:.78rem;padding:1rem">Nenhuma pesquisa similar na Nebula.</div>',unsafe_allow_html=True)
        with tab_fol:
            fm=[]
            for fname,fdata in st.session_state.folders.items():
                if not isinstance(fdata,dict): continue
                ftags=[t.lower() for t in fdata.get("analysis_tags",[])]
                sc=sum(1 for t in all_terms if len(t)>2 and any(t in ft for ft in ftags))
                if sc>0: fm.append((sc,fname,fdata))
            fm.sort(key=lambda x:-x[0])
            if fm:
                for _,fname,fdata in fm[:4]:
                    at=fdata.get("analysis_tags",[]); st.markdown(f'<div class="img-rc"><div style="font-family:Outfit,sans-serif;font-size:.91rem;font-weight:700;margin-bottom:.35rem">{fname}</div><div style="color:#3d5070;font-size:.68rem;margin-bottom:.4rem">{len(fdata.get("files",[]))} arquivos</div><div>{tags_html(at[:6])}</div></div>',unsafe_allow_html=True)
            else: st.markdown('<div style="color:#3d5070;font-size:.78rem;padding:1rem">Nenhum documento relacionado.</div>',unsafe_allow_html=True)
        with tab_web:
            ck=f"img_{rep['kw'][:40]}"
            if ck not in st.session_state.scholar_cache:
                with st.spinner("Buscando artigos…"):
                    q=f"{rep['category']} {rep['object_type']} {rep['material']}"; st.session_state.scholar_cache[ck]=search_ss(q,4)
            web_r=st.session_state.scholar_cache.get(ck,[])
            if web_r:
                for idx,a in enumerate(web_r): render_web_article(a,idx=idx+2000,ctx="img_web")
            else: st.markdown('<div style="color:#3d5070;font-size:.78rem;padding:1rem">Sem resultados online.</div>',unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────
# CHAT PAGE
# ─────────────────────────────────────────────────
def page_chat():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem">Mensagens</h1>', unsafe_allow_html=True)
    col_c,col_m=st.columns([.88,2.8])
    email=st.session_state.current_user
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    with col_c:
        st.markdown('<div style="font-size:.64rem;font-weight:700;color:#3d5070;letter-spacing:.09em;text-transform:uppercase;margin-bottom:.8rem">CONVERSAS</div>',unsafe_allow_html=True)
        shown=set()
        for ue in st.session_state.chat_contacts:
            if ue==email or ue in shown: continue
            shown.add(ue); ud=users.get(ue,{}); uname=ud.get("name","?"); uin=ini(uname); uphoto=ud.get("photo_b64")
            msgs=st.session_state.chat_messages.get(ue,[]); last=msgs[-1]["text"][:24]+"…" if msgs and len(msgs[-1]["text"])>24 else (msgs[-1]["text"] if msgs else "Iniciar conversa")
            active=st.session_state.active_chat==ue; online=random.Random(ue+"c").random()>.42
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            bg="rgba(37,99,235,.16)" if active else "rgba(8,14,28,.85)"; bdr="rgba(59,130,246,.38)" if active else "var(--border)"
            st.markdown(f'<div style="background:{bg};border:1px solid {bdr};border-radius:16px;padding:9px 11px;margin-bottom:5px"><div style="display:flex;align-items:center;gap:8px">{avh(uin,32,uphoto)}<div style="overflow:hidden;flex:1"><div style="font-size:.80rem;font-weight:600;font-family:Outfit,sans-serif">{dot}{uname}</div><div style="font-size:.67rem;color:#3d5070;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{last}</div></div></div></div>',unsafe_allow_html=True)
            if st.button("Abrir",key=f"oc_{ue}",use_container_width=True): st.session_state.active_chat=ue; st.rerun()
        st.markdown("<hr>",unsafe_allow_html=True)
        nc=st.text_input("",placeholder="Adicionar por e-mail…",key="new_ct",label_visibility="collapsed")
        if st.button("Adicionar",key="btn_add_ct",use_container_width=True):
            if nc in users and nc!=email:
                if nc not in st.session_state.chat_contacts: st.session_state.chat_contacts.append(nc)
                st.rerun()
            elif nc: st.toast("Usuário não encontrado.")
    with col_m:
        if st.session_state.active_chat:
            contact=st.session_state.active_chat; cd=users.get(contact,{}); cname=cd.get("name","?"); cin=ini(cname); cphoto=cd.get("photo_b64")
            msgs=st.session_state.chat_messages.get(contact,[]); is_online=random.Random(contact+"o").random()>.35
            dot='<span class="dot-on"></span>' if is_online else '<span class="dot-off"></span>'
            st.markdown(f'<div style="background:rgba(8,14,28,.88);border:1px solid var(--border);border-radius:16px;padding:12px 16px;margin-bottom:1rem;display:flex;align-items:center;gap:12px"><div style="flex-shrink:0">{avh(cin,40,cphoto)}</div><div style="flex:1"><div style="font-weight:700;font-size:.92rem;font-family:Outfit,sans-serif">{dot}{cname}</div><div style="font-size:.68rem;color:#10b981">Criptografia AES-256 ativa</div></div></div>',unsafe_allow_html=True)
            for msg in msgs:
                is_me=msg["from"]=="me"; cls="bme" if is_me else "bthem"; align="right" if is_me else "left"
                st.markdown(f'<div style="display:flex;{"justify-content:flex-end" if is_me else ""}"><div class="{cls}">{msg["text"]}<div style="font-size:.60rem;color:rgba(255,255,255,.25);margin-top:3px;text-align:{align}">{msg["time"]}</div></div></div>',unsafe_allow_html=True)
            st.markdown("<br>",unsafe_allow_html=True)
            c_inp,c_btn=st.columns([5,1])
            with c_inp: nm=st.text_input("",placeholder="Escreva uma mensagem…",key=f"mi_{contact}",label_visibility="collapsed")
            with c_btn:
                st.markdown("<div style='height:6px'></div>",unsafe_allow_html=True)
                if st.button("Enviar",key=f"ms_{contact}",use_container_width=True):
                    if nm:
                        now=datetime.now().strftime("%H:%M"); st.session_state.chat_messages.setdefault(contact,[]).append({"from":"me","text":nm,"time":now}); st.rerun()
        else:
            st.markdown('<div class="card" style="text-align:center;padding:6rem"><div style="font-size:3rem;margin-bottom:1rem;opacity:.15">◻</div><div style="color:#8ea8cc;font-family:Playfair Display,serif;font-size:1rem">Selecione uma conversa</div><div style="font-size:.74rem;color:#3d5070;margin-top:.5rem">Criptografia end-to-end ativa</div></div>',unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────
# SETTINGS PAGE
# ─────────────────────────────────────────────────
def page_settings():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem">Perfil & Configurações</h1>', unsafe_allow_html=True)
    u=guser(); email=st.session_state.current_user; in_=ini(u.get("name","?")); photo=u.get("photo_b64")
    tab_p,tab_s,tab_pr,tab_saved=st.tabs(["  Meu Perfil  ","  Segurança  ","  Privacidade  ","  Artigos Salvos  "])
    with tab_p:
        photo_html=f'<img src="{photo}"/>' if photo else f'<span style="font-size:2rem">{in_}</span>'
        my_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==email]
        st.markdown(f'<div class="prof-hero"><div class="prof-photo">{photo_html}</div><div style="flex:1;z-index:1"><div style="display:flex;align-items:center;gap:8px;margin-bottom:.3rem"><h1 style="margin:0">{u.get("name","?")}</h1><span style="font-size:.7rem;color:#22d3ee">✓</span></div><div style="color:#60a5fa;font-size:.84rem;font-weight:600;margin-bottom:.4rem">{u.get("area","")}</div><div style="color:#8ea8cc;font-size:.82rem;line-height:1.68;margin-bottom:.9rem">{u.get("bio","Sem biografia.")}</div><div style="display:flex;gap:2rem;flex-wrap:wrap"><div><span style="font-weight:800;font-family:Playfair Display,serif">{u.get("followers",0)}</span><span style="color:#3d5070;font-size:.73rem"> seguidores</span></div><div><span style="font-weight:800;font-family:Playfair Display,serif">{u.get("following",0)}</span><span style="color:#3d5070;font-size:.73rem"> seguindo</span></div><div><span style="font-weight:800;font-family:Playfair Display,serif">{len(my_posts)}</span><span style="color:#3d5070;font-size:.73rem"> pesquisas</span></div></div></div></div>',unsafe_allow_html=True)
        ph=st.file_uploader("Foto de perfil",type=["png","jpg","jpeg","webp"],key="ph_up")
        if ph:
            b64=img_to_b64(ph)
            if b64: st.session_state.users[email]["photo_b64"]=b64; save_db(); st.success("Foto atualizada!"); st.rerun()
        st.markdown("<hr>",unsafe_allow_html=True)
        new_n=st.text_input("Nome completo",value=u.get("name",""),key="cfg_n")
        new_a=st.text_input("Área de pesquisa",value=u.get("area",""),key="cfg_a")
        new_b=st.text_area("Biografia",value=u.get("bio",""),key="cfg_b",height=90)
        c_save,c_out=st.columns(2)
        with c_save:
            if st.button("Salvar perfil",key="btn_sp",use_container_width=True):
                st.session_state.users[email]["name"]=new_n; st.session_state.users[email]["area"]=new_a; st.session_state.users[email]["bio"]=new_b
                save_db(); record(area_to_tags(new_a),1.5); st.success("Perfil salvo!"); st.rerun()
        with c_out:
            if st.button("Sair da conta",key="btn_logout",use_container_width=True):
                st.session_state.logged_in=False; st.session_state.current_user=None; st.session_state.page="login"; st.rerun()
    with tab_s:
        st.markdown('<h3>Alterar senha</h3>',unsafe_allow_html=True)
        op=st.text_input("Senha atual",type="password",key="op"); np_=st.text_input("Nova senha",type="password",key="np_"); np2=st.text_input("Confirmar nova",type="password",key="np2")
        if st.button("Alterar senha",key="btn_cpw"):
            if hp(op)!=u.get("password",""): st.error("Senha atual incorreta.")
            elif np_!=np2: st.error("Senhas não coincidem.")
            elif len(np_)<6: st.error("Mínimo 6 caracteres.")
            else: st.session_state.users[email]["password"]=hp(np_); save_db(); st.success("Senha alterada!")
        st.markdown("<hr>",unsafe_allow_html=True)
        en=u.get("2fa_enabled",False)
        st.markdown(f'<div class="card" style="padding:1rem 1.3rem;display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem"><div><div style="font-weight:700;font-size:.88rem;font-family:Outfit,sans-serif">Autenticação 2FA</div><div style="font-size:.71rem;color:#3d5070">{email}</div></div><span style="color:{"#10b981" if en else "#ef4444"};font-size:.80rem;font-weight:700">{"Ativo" if en else "Inativo"}</span></div>',unsafe_allow_html=True)
        if st.button("Desativar 2FA" if en else "Ativar 2FA",key="btn_2fa"):
            st.session_state.users[email]["2fa_enabled"]=not en; save_db(); st.rerun()
    with tab_pr:
        prots=[("AES-256","Criptografia end-to-end nas mensagens"),("SHA-256","Hash seguro de senhas"),("TLS 1.3","Transmissão criptografada de todos os dados")]
        items="".join(f'<div style="display:flex;align-items:center;gap:12px;background:rgba(16,185,129,.05);border:1px solid rgba(16,185,129,.16);border-radius:var(--r16);padding:11px;margin-bottom:8px"><div style="width:26px;height:26px;border-radius:8px;background:rgba(16,185,129,.1);display:flex;align-items:center;justify-content:center;color:#10b981;font-size:.8rem;flex-shrink:0">✓</div><div><div style="font-weight:600;color:#10b981;font-size:.82rem">{n2}</div><div style="font-size:.69rem;color:#3d5070">{d2}</div></div></div>' for n2,d2 in prots)
        st.markdown(f'<div class="card" style="padding:1.2rem"><div style="font-weight:700;font-family:Outfit,sans-serif;margin-bottom:1rem">Proteções Ativas</div>{items}</div>',unsafe_allow_html=True)
    with tab_saved:
        st.markdown('<h3>Artigos Salvos</h3>',unsafe_allow_html=True)
        if st.session_state.saved_articles:
            for idx,a in enumerate(st.session_state.saved_articles):
                render_web_article(a,idx=idx+3000,ctx="saved")
                uid=re.sub(r'[^a-zA-Z0-9]','',f"rm_{a.get('doi','nd')}_{idx}")[:30]
                if st.button("Remover",key=f"rms_{uid}"):
                    st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]
                    save_db(); st.toast("Removido!"); st.rerun()
        else:
            st.markdown('<div class="card" style="text-align:center;padding:2.5rem;color:#3d5070">Nenhum artigo salvo ainda. Use "Salvar" nas buscas.</div>',unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────
def main():
    inject_css()
    if not st.session_state.logged_in:
        p = st.session_state.page
        if p == "verify_email": page_verify_email()
        elif p == "2fa":         page_2fa()
        else:                    page_login()
        return
    render_topnav()
    if st.session_state.profile_view:
        page_profile(st.session_state.profile_view); return
    {
        "feed":       page_feed,
        "search":     page_search,
        "knowledge":  page_knowledge,
        "folders":    page_folders,
        "analytics":  page_analytics,
        "img_search": page_img_search,
        "chat":       page_chat,
        "settings":   page_settings,
    }.get(st.session_state.page, page_feed)()

main()
