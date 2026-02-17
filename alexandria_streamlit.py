import subprocess, sys

def _install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

try:
    import plotly.graph_objects as go
    import plotly.express as px
except ImportError:
    _install("plotly")
    import plotly.graph_objects as go
    import plotly.express as px

import streamlit as st
import hashlib, random, string, json
from datetime import datetime
from collections import defaultdict

# ════════════════════════════════════════════════════
#  CONFIG
# ════════════════════════════════════════════════════
st.set_page_config(page_title="Nebula", page_icon="🔬", layout="wide",
                   initial_sidebar_state="expanded")

# ════════════════════════════════════════════════════
#  SVG ICONS (minimalist)
# ════════════════════════════════════════════════════
def icon(name: str, size: int = 18, color: str = "currentColor") -> str:
    paths = {
        "microscope": '<path d="M6 2h8M9 2v3M7 5h6l1 2H6L7 5zM5 9h14M8 9v3M16 9v3M5 12h14M8 12l-2 5h12l-2-5M9 19h6"/><circle cx="12" cy="15" r="1"/>',
        "home":       '<path d="M3 12L12 3l9 9M5 10v10h4v-6h6v6h4V10"/>',
        "folder":     '<path d="M3 7a2 2 0 012-2h3l2 2h9a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/>',
        "search":     '<circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>',
        "network":    '<circle cx="12" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/><path d="M12 7v4M9.5 17.5L7 17M14.5 17.5L17 17M12 11l-5 6M12 11l5 6"/>',
        "chat":       '<path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10z"/>',
        "chart":      '<path d="M18 20V10M12 20V4M6 20v-6"/>',
        "image":      '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/>',
        "settings":   '<circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>',
        "logout":     '<path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/>',
        "heart":      '<path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>',
        "comment":    '<path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10z"/>',
        "share":      '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98"/>',
        "plus":       '<path d="M12 5v14M5 12h14"/>',
        "check":      '<path d="M20 6L9 17l-5-5"/>',
        "lock":       '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>',
        "user":       '<path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/>',
        "bell":       '<path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0"/>',
        "send":       '<path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z"/>',
        "star":       '<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>',
        "eye":        '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
        "shield":     '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
        "mail":       '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><path d="M22 6l-10 7L2 6"/>',
        "upload":     '<path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/>',
        "key":        '<path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.778 7.778 5.5 5.5 0 017.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>',
        "zap":        '<path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>',
        "bookmark":   '<path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2v16z"/>',
        "trending":   '<path d="M23 6l-9.5 9.5-5-5L1 18"/><path d="M17 6h6v6"/>',
        "globe":      '<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/>',
    }
    svg_path = paths.get(name, '<circle cx="12" cy="12" r="10"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{svg_path}</svg>'

# ════════════════════════════════════════════════════
#  GLOBAL CSS
# ════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;0,800;1,400&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
  --void:       #03040a;
  --space:      #080d1c;
  --deep:       #0a1128;
  --navy:       #0d1635;
  --surface:    #111d3a;
  --elevated:   #162348;
  --blue-core:  #2563eb;
  --blue-lit:   #3b7cf4;
  --blue-glow:  #60a5fa;
  --cyan:       #06b6d4;
  --cyan-soft:  #22d3ee;
  --text-1:     #eef2ff;
  --text-2:     #94a8d0;
  --text-3:     #4a5e80;
  --border:     rgba(37,99,235,0.18);
  --border-lit: rgba(96,165,250,0.28);
  --glass:      rgba(10,17,40,0.7);
  --glass-top:  rgba(22,35,72,0.5);
  --success:    #10b981;
  --warn:       #f59e0b;
  --danger:     #ef4444;
  --radius-sm:  10px;
  --radius-md:  16px;
  --radius-lg:  24px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; }

html, body, .stApp {
  background: var(--void) !important;
  color: var(--text-1) !important;
  font-family: 'DM Sans', sans-serif !important;
}

/* ── Animated cosmos background ── */
.stApp::before {
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse 100% 70% at 10% 0%,   rgba(37,99,235,0.10) 0%, transparent 55%),
    radial-gradient(ellipse 70%  90% at 90% 100%,  rgba(6,182,212,0.07)  0%, transparent 55%),
    radial-gradient(ellipse 50%  50% at 50% 50%,   rgba(37,99,235,0.04)  0%, transparent 60%);
  pointer-events: none;
  z-index: 0;
  animation: bgPulse 12s ease-in-out infinite alternate;
}
@keyframes bgPulse {
  from { opacity: 0.7; }
  to   { opacity: 1.0; }
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
  background: linear-gradient(160deg, var(--deep) 0%, var(--void) 100%) !important;
  border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] * { color: var(--text-1) !important; }
section[data-testid="stSidebar"] .stButton > button {
  background: transparent !important;
  border: none !important;
  border-radius: var(--radius-sm) !important;
  color: var(--text-2) !important;
  text-align: left !important;
  padding: 0.55rem 0.9rem !important;
  box-shadow: none !important;
  font-size: 0.88rem !important;
  font-weight: 400 !important;
  letter-spacing: 0 !important;
  transition: background 0.2s, color 0.2s !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  background: rgba(37,99,235,0.12) !important;
  color: var(--text-1) !important;
  transform: none !important;
  box-shadow: none !important;
}

/* ── Typography ── */
h1, h2, h3, h4 {
  font-family: 'Playfair Display', 'Times New Roman', serif !important;
  color: var(--text-1) !important;
  letter-spacing: -0.01em;
  font-weight: 700;
}
h1 { font-size: 1.9rem !important; }
h2 { font-size: 1.5rem !important; }
h3 { font-size: 1.15rem !important; }

/* ── Inputs ── */
.stTextInput input, .stTextArea textarea {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  color: var(--text-1) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.9rem !important;
  transition: border-color 0.25s, box-shadow 0.25s !important;
  padding: 0.6rem 0.9rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: var(--blue-core) !important;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.15), 0 0 12px rgba(37,99,235,0.1) !important;
  outline: none !important;
}
.stTextInput label, .stTextArea label { color: var(--text-2) !important; font-size: 0.82rem !important; }

/* ── Liquid Glass Button ── */
.stButton > button {
  background: linear-gradient(135deg,
    rgba(37,99,235,0.4)  0%,
    rgba(6,182,212,0.2)  50%,
    rgba(37,99,235,0.3)  100%) !important;
  backdrop-filter: blur(24px) saturate(200%) !important;
  -webkit-backdrop-filter: blur(24px) saturate(200%) !important;
  border: 1px solid rgba(96,165,250,0.3) !important;
  border-radius: var(--radius-md) !important;
  color: var(--text-1) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 500 !important;
  font-size: 0.88rem !important;
  padding: 0.6rem 1.5rem !important;
  letter-spacing: 0.02em !important;
  position: relative !important;
  overflow: hidden !important;
  transition: all 0.3s cubic-bezier(0.4,0,0.2,1) !important;
  box-shadow:
    0 4px 20px rgba(37,99,235,0.18),
    inset 0 1px 0 rgba(255,255,255,0.10),
    inset 0 -1px 0 rgba(0,0,0,0.15) !important;
}
.stButton > button::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.06) 50%, transparent 100%);
  transform: translateX(-100%);
  transition: transform 0.6s ease !important;
}
.stButton > button:hover::after { transform: translateX(100%); }
.stButton > button:hover {
  background: linear-gradient(135deg,
    rgba(37,99,235,0.6)  0%,
    rgba(6,182,212,0.35) 50%,
    rgba(37,99,235,0.5)  100%) !important;
  border-color: rgba(96,165,250,0.5) !important;
  box-shadow: 0 8px 30px rgba(37,99,235,0.3), inset 0 1px 0 rgba(255,255,255,0.15) !important;
  transform: translateY(-1px) !important;
}
.stButton > button:active { transform: translateY(0px) !important; }

/* ── Cards ── */
.card {
  background: var(--glass);
  backdrop-filter: blur(20px) saturate(160%);
  -webkit-backdrop-filter: blur(20px) saturate(160%);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 1.4rem 1.6rem;
  margin-bottom: 1rem;
  box-shadow: 0 8px 32px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.04);
  animation: slideUp 0.4s ease both;
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
}
.card:hover {
  transform: translateY(-2px);
  border-color: var(--border-lit);
  box-shadow: 0 16px 48px rgba(0,0,0,0.4), 0 0 0 1px rgba(37,99,235,0.12);
}
@keyframes slideUp {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: translateY(0);    }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}
.page-wrap { animation: fadeIn 0.35s ease; }

/* ── Avatar ── */
.av {
  border-radius: 50%;
  background: linear-gradient(135deg, var(--navy), var(--blue-core));
  display: flex; align-items: center; justify-content: center;
  font-family: 'DM Sans', sans-serif;
  font-weight: 600;
  color: white;
  border: 1.5px solid var(--border-lit);
  flex-shrink: 0;
}

/* ── Tags ── */
.tag {
  display: inline-block;
  background: rgba(37,99,235,0.12);
  border: 1px solid rgba(37,99,235,0.25);
  border-radius: 20px;
  padding: 2px 10px;
  font-size: 0.72rem;
  color: var(--blue-glow);
  margin: 2px;
  font-weight: 500;
  letter-spacing: 0.01em;
}

/* ── Status ── */
.badge {
  display: inline-block;
  border-radius: 20px;
  padding: 2px 10px;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.03em;
}
.badge-ongoing  { background: rgba(245,158,11,0.12); border:1px solid rgba(245,158,11,0.35); color:#f59e0b; }
.badge-pub      { background: rgba(16,185,129,0.12);  border:1px solid rgba(16,185,129,0.35); color:#10b981; }

/* ── Metric box ── */
.mbox {
  background: var(--glass);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 1.2rem;
  text-align: center;
  animation: slideUp 0.4s ease both;
}
.mval {
  font-family: 'Playfair Display', 'Times New Roman', serif;
  font-size: 2rem; font-weight: 800;
  background: linear-gradient(135deg, var(--blue-glow), var(--cyan-soft));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}
.mlbl { font-size: 0.75rem; color: var(--text-3); margin-top: 3px; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--void); }
::-webkit-scrollbar-thumb { background: var(--elevated); border-radius: 3px; }

/* ── Chat bubbles ── */
.bbl-me {
  background: linear-gradient(135deg, rgba(37,99,235,0.45), rgba(6,182,212,0.22));
  border: 1px solid rgba(96,165,250,0.25);
  border-radius: 18px 18px 4px 18px;
  padding: 0.7rem 1rem;
  max-width: 72%; margin-left: auto; margin-bottom: 6px;
  font-size: 0.87rem; line-height: 1.5;
}
.bbl-them {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px 18px 18px 4px;
  padding: 0.7rem 1rem;
  max-width: 72%; margin-bottom: 6px;
  font-size: 0.87rem; line-height: 1.5;
}

/* ── Logo ── */
.logo {
  font-family: 'Playfair Display', 'Times New Roman', serif;
  font-size: 1.7rem; font-weight: 800; font-style: italic;
  background: linear-gradient(135deg, #93c5fd, #22d3ee);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  letter-spacing: -0.03em;
}
.logo-sub { font-size: 0.72rem; color: var(--text-3); margin-top: -2px; letter-spacing: 0.08em; text-transform: uppercase; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
  background: var(--deep) !important;
  border-radius: var(--radius-sm) !important;
  padding: 4px !important; gap: 4px !important;
  border: 1px solid var(--border) !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  color: var(--text-3) !important;
  border-radius: 8px !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.85rem !important;
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, rgba(37,99,235,0.35), rgba(6,182,212,0.18)) !important;
  color: var(--text-1) !important;
  border: 1px solid rgba(96,165,250,0.3) !important;
}
.stTabs [data-baseweb="tab-panel"] { background: transparent !important; padding-top: 1rem !important; }

/* ── Expander ── */
.stExpander { background: var(--glass) !important; border: 1px solid var(--border) !important; border-radius: var(--radius-md) !important; }
.stExpander summary { color: var(--text-2) !important; font-size: 0.88rem !important; }

/* ── Selectbox ── */
.stSelectbox [data-baseweb="select"] { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: var(--radius-sm) !important; }
.stSelectbox label { color: var(--text-2) !important; font-size: 0.82rem !important; }

/* ── File uploader ── */
.stFileUploader section { background: var(--glass) !important; border: 1.5px dashed var(--border-lit) !important; border-radius: var(--radius-md) !important; }

/* ── Alert ── */
.stAlert { background: var(--glass) !important; border: 1px solid var(--border) !important; border-radius: var(--radius-md) !important; color: var(--text-1) !important; }

/* ── Separator ── */
hr { border-color: var(--border) !important; }

/* ── Pulse dot ── */
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.6; transform: scale(0.85); }
}
.dot-on  { display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--success);  animation: pulse 2s infinite; margin-right:6px; }
.dot-off { display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--text-3); margin-right:6px; }

/* ── Shimmer (loading effect) ── */
@keyframes shimmer {
  from { background-position: -200% 0; }
  to   { background-position:  200% 0; }
}
.shimmer {
  background: linear-gradient(90deg, var(--surface) 25%, var(--elevated) 50%, var(--surface) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.6s infinite;
  border-radius: var(--radius-sm);
  height: 14px;
}

/* ── Progress bar ── */
.stProgress > div > div { background: linear-gradient(90deg, var(--blue-core), var(--cyan)) !important; border-radius: 4px !important; }

/* ── Recommendation pill ── */
.rec-pill {
  display:inline-block;
  background: linear-gradient(135deg, rgba(6,182,212,0.15), rgba(37,99,235,0.15));
  border: 1px solid rgba(6,182,212,0.3);
  border-radius: 20px; padding: 2px 10px;
  font-size: 0.7rem; color: var(--cyan-soft); font-weight: 600;
  letter-spacing: 0.03em;
}

/* ── Input label override ── */
label { color: var(--text-2) !important; }
.stCheckbox label, .stRadio label { color: var(--text-1) !important; }

/* ── Page container ── */
.block-container { padding-top: 1.8rem !important; padding-bottom: 3rem !important; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════
def hp(pw): return hashlib.sha256(pw.encode()).hexdigest()
def code6(): return ''.join(random.choices(string.digits, k=6))
def initials(name): return ''.join(w[0].upper() for w in name.split()[:2])

def av_html(init, sz=40):
    fs = sz // 3
    return (f'<div class="av" style="width:{sz}px;height:{sz}px;font-size:{fs}px;">'
            f'{init}</div>')

def tags_html(tags):
    return ' '.join(f'<span class="tag">{t}</span>' for t in tags)

def status_html(s):
    cls = "badge-pub" if s == "Publicado" else "badge-ongoing"
    return f'<span class="badge {cls}">{s}</span>'

def guser():
    return st.session_state.users.get(st.session_state.current_user, {})

def logo_html(size=1.7):
    return f'''
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
      <div style="color:#60a5fa;">{icon("microscope", 28, "#60a5fa")}</div>
      <div>
        <div class="logo" style="font-size:{size}rem;">Nebula</div>
        <div class="logo-sub">Rede do Conhecimento Científico</div>
      </div>
    </div>'''

# ════════════════════════════════════════════════════
#  RECOMMENDATION ENGINE
# ════════════════════════════════════════════════════
def record_interaction(tag_list, weight=1.0):
    """Record user interest in tags."""
    email = st.session_state.get("current_user")
    if not email or not tag_list:
        return
    prefs = st.session_state.user_prefs.setdefault(email, defaultdict(float))
    for t in tag_list:
        prefs[t.lower()] += weight

def score_post(post, email):
    """Score a post for the current user based on interest overlap."""
    prefs = st.session_state.user_prefs.get(email, {})
    if not prefs:
        return 0.0
    score = 0.0
    for t in post.get("tags", []):
        score += prefs.get(t.lower(), 0)
    for t in post.get("connections", []):
        score += prefs.get(t.lower(), 0) * 0.5
    return score

def recommended_posts(email, n=3):
    """Return top N recommended posts not already liked."""
    posts = st.session_state.feed_posts
    scored = [(score_post(p, email), p) for p in posts
              if email not in p.get("liked_by", [])]
    scored.sort(key=lambda x: -x[0])
    return [p for s, p in scored if s > 0][:n]

# ════════════════════════════════════════════════════
#  SESSION STATE
# ════════════════════════════════════════════════════
def init():
    defs = {
      "logged_in": False,
      "current_user": None,
      "page": "login",
      "user_prefs": {},   # email → {tag: score}
      "users": {
        "demo@nebula.ai": {
          "name": "Ana Pesquisadora",
          "password": hp("demo123"),
          "photo": None,
          "bio": "Pesquisadora em IA e Ciências Cognitivas",
          "area": "Inteligência Artificial",
          "followers": 128,
          "following": 47,
          "2fa_enabled": False,
          "verified": True,
        }
      },
      "pending_verify": None,   # {"email":…, "name":…, "pw":…, "area":…, "code":…}
      "pending_2fa":   None,
      "feed_posts": [
        {
          "id": 1, "author": "Carlos Mendez", "avatar": "CM",
          "area": "Neurociência",
          "title": "Efeitos da Privação de Sono na Plasticidade Sináptica",
          "abstract": "Investigamos como 24h de privação de sono afetam espinhas dendríticas em ratos Wistar, com redução de 34% na plasticidade hipocampal.",
          "tags": ["neurociência","sono","memória","hipocampo"],
          "likes": 47, "comments": [
            {"user":"Maria Silva","text":"Excelente metodologia!"},
            {"user":"João Lima", "text":"Quais foram os critérios de exclusão?"}
          ],
          "status": "Em andamento", "date": "2026-02-10",
          "liked_by": [], "connections": ["sono","memória","hipocampo"],
        },
        {
          "id": 2, "author": "Luana Freitas", "avatar": "LF",
          "area": "Biomedicina",
          "title": "CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras",
          "abstract": "Desenvolvemos vetor AAV9 modificado para entrega precisa de CRISPR no gene DMD, com eficiência de 78% em modelos murinos mdx.",
          "tags": ["CRISPR","gene terapia","músculo","AAV9"],
          "likes": 93, "comments": [
            {"user":"Ana Pesquisadora","text":"Quais são os próximos passos para trials humanos?"}
          ],
          "status": "Publicado", "date": "2026-01-28",
          "liked_by": [], "connections": ["edição genética","distrofia","AAV9"],
        },
        {
          "id": 3, "author": "Rafael Souza", "avatar": "RS",
          "area": "Ciência da Computação",
          "title": "Redes Neurais Quântico-Clássicas para Otimização Combinatória",
          "abstract": "Arquitetura híbrida variacional combinando qubits supercondutores com camadas densas clássicas para resolver TSP com 40% menos iterações.",
          "tags": ["quantum ML","otimização","TSP","computação quântica"],
          "likes": 201, "comments": [],
          "status": "Em andamento", "date": "2026-02-15",
          "liked_by": [], "connections": ["computação quântica","machine learning","otimização"],
        },
        {
          "id": 4, "author": "Priya Nair", "avatar": "PN",
          "area": "Astrofísica",
          "title": "Detecção de Matéria Escura via Lentes Gravitacionais Fracas",
          "abstract": "Usamos catálogo DES Y3 com 100M de galáxias para mapear distribuição de matéria escura com precisão sub-arcminuto.",
          "tags": ["astrofísica","matéria escura","cosmologia","DES"],
          "likes": 312, "comments": [],
          "status": "Publicado", "date": "2026-02-01",
          "liked_by": [], "connections": ["cosmologia","lentes gravitacionais","survey"],
        },
      ],
      "folders": {
        "IA & Machine Learning": ["artigo_gpt4.pdf","redes_conv.pdf"],
        "Bioinformática":        ["genomica_2025.pdf"],
        "Favoritos":             [],
      },
      "chat_contacts": [
        {"name":"Carlos Mendez","avatar":"CM","online":True, "last":"Ótimo, vou revisar!"},
        {"name":"Luana Freitas","avatar":"LF","online":False,"last":"Podemos colaborar no próximo semestre."},
        {"name":"Rafael Souza","avatar":"RS","online":True, "last":"Compartilhei o repositório."},
      ],
      "chat_messages": {
        "Carlos Mendez": [
          {"from":"Carlos Mendez","text":"Oi! Vi seu comentário na minha pesquisa.","time":"09:14"},
          {"from":"me","text":"Achei muito interessante o método que você usou.","time":"09:16"},
          {"from":"Carlos Mendez","text":"Ótimo, vou revisar!","time":"09:17"},
        ],
        "Luana Freitas": [
          {"from":"Luana Freitas","text":"Podemos colaborar no próximo semestre.","time":"ontem"},
        ],
        "Rafael Souza": [
          {"from":"Rafael Souza","text":"Compartilhei o repositório.","time":"08:30"},
        ],
      },
      "active_chat": None,
      "knowledge_nodes": [
        {"id":"IA",                 "connections":["Machine Learning","Otimização","Redes Neurais"]},
        {"id":"Neurociência",       "connections":["Memória","Sono","Plasticidade"]},
        {"id":"Genômica",           "connections":["CRISPR","AAV9","Edição Genética"]},
        {"id":"Computação Quântica","connections":["Otimização","Machine Learning"]},
        {"id":"Astrofísica",        "connections":["Cosmologia","Matéria Escura"]},
      ],
      "followed": ["Carlos Mendez","Luana Freitas"],
      "notifications": [
        "Carlos Mendez curtiu sua pesquisa",
        "Nova conexão: IA ↔ Computação Quântica",
        "Luana Freitas comentou em um artigo que você segue",
      ],
      "stats_data": {
        "views":    [12,34,28,67,89,110,95,134,160,178,201,230],
        "citations":[0,1,1,2,3,4,4,6,7,8,10,12],
        "months":   ["Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez","Jan","Fev"],
      },
    }
    for k, v in defs.items():
        if k not in st.session_state:
            st.session_state[k] = v

init()

# ════════════════════════════════════════════════════
#  PAGE: LOGIN / CADASTRO
# ════════════════════════════════════════════════════
def page_login():
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(logo_html(2.0), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        tab_in, tab_up = st.tabs(["  Entrar  ", "  Criar conta  "])

        # ── LOGIN
        with tab_in:
            email = st.text_input("E-mail", placeholder="seu@email.com",  key="li_e")
            pw    = st.text_input("Senha",  placeholder="••••••••", type="password", key="li_p")
            if st.button("Entrar", use_container_width=True, key="btn_li"):
                u = st.session_state.users.get(email)
                if not u:
                    st.error("E-mail não encontrado.")
                elif u["password"] != hp(pw):
                    st.error("Senha incorreta.")
                elif not u.get("verified", True):
                    st.warning("Confirme seu e-mail antes de entrar.")
                elif u.get("2fa_enabled"):
                    c = code6()
                    st.session_state.pending_2fa = {"email": email, "code": c}
                    st.session_state.page = "2fa"
                    st.rerun()
                else:
                    st.session_state.logged_in = True
                    st.session_state.current_user = email
                    st.session_state.page = "feed"
                    st.rerun()
            st.markdown(f'<div style="text-align:center;color:var(--text-3);font-size:0.78rem;margin-top:0.5rem;">Conta demo: demo@nebula.ai / demo123</div>', unsafe_allow_html=True)

        # ── CADASTRO
        with tab_up:
            n_name  = st.text_input("Nome completo",    placeholder="Dr. Maria Silva",       key="su_n")
            n_email = st.text_input("E-mail",           placeholder="seu@email.com",          key="su_e")
            n_area  = st.text_input("Área de pesquisa", placeholder="Bioinformática, IA…",    key="su_a")
            n_pw    = st.text_input("Senha",            placeholder="Mínimo 6 caracteres", type="password", key="su_p")
            n_pw2   = st.text_input("Confirmar senha",  placeholder="••••••••",           type="password", key="su_p2")
            if st.button("Criar conta e verificar e-mail", use_container_width=True, key="btn_su"):
                if not all([n_name, n_email, n_area, n_pw, n_pw2]):
                    st.error("Preencha todos os campos.")
                elif n_pw != n_pw2:
                    st.error("Senhas não coincidem.")
                elif len(n_pw) < 6:
                    st.error("Senha muito curta.")
                elif n_email in st.session_state.users:
                    st.error("E-mail já cadastrado.")
                else:
                    c = code6()
                    st.session_state.pending_verify = {
                        "email": n_email, "name": n_name,
                        "pw": hp(n_pw), "area": n_area, "code": c
                    }
                    st.session_state.page = "verify_email"
                    st.rerun()

# ════════════════════════════════════════════════════
#  PAGE: VERIFICAR E-MAIL (cadastro)
# ════════════════════════════════════════════════════
def page_verify_email():
    pv = st.session_state.pending_verify
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(logo_html(), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card" style="text-align:center;">
          <div style="color:var(--blue-glow);margin-bottom:1rem;">{icon("mail",40,"#60a5fa")}</div>
          <h2 style="margin-bottom:0.5rem;">Verifique seu e-mail</h2>
          <p style="color:var(--text-2);font-size:0.88rem;line-height:1.6;">
            Um código de 6 dígitos foi enviado para<br>
            <strong style="color:var(--text-1);">{pv['email']}</strong>
          </p>
          <div style="background:rgba(37,99,235,0.12);border:1px solid rgba(37,99,235,0.25);border-radius:12px;padding:12px;margin:1rem 0;">
            <div style="font-size:0.72rem;color:var(--text-3);margin-bottom:4px;">CÓDIGO DE VERIFICAÇÃO (demo)</div>
            <div style="font-family:'Playfair Display',serif;font-size:2rem;font-weight:700;letter-spacing:0.2em;color:var(--blue-glow);">{pv['code']}</div>
          </div>
          <p style="color:var(--text-3);font-size:0.75rem;">Em produção, o código seria enviado via SMTP para o e-mail acima.</p>
        </div>
        """, unsafe_allow_html=True)

        typed = st.text_input("Digite o código de 6 dígitos", max_chars=6, placeholder="000000", key="ev_code")
        if st.button("Verificar e criar conta", use_container_width=True, key="btn_ev"):
            if typed == pv["code"]:
                st.session_state.users[pv["email"]] = {
                    "name": pv["name"], "password": pv["pw"],
                    "photo": None, "bio": "", "area": pv["area"],
                    "followers": 0, "following": 0,
                    "2fa_enabled": False, "verified": True,
                }
                st.session_state.pending_verify = None
                st.session_state.logged_in = True
                st.session_state.current_user = pv["email"]
                st.session_state.page = "feed"
                st.success("Conta verificada! Bem-vindo ao Nebula.")
                st.rerun()
            else:
                st.error("Código inválido.")
        if st.button("← Voltar", key="btn_ev_back"):
            st.session_state.page = "login"
            st.rerun()

# ════════════════════════════════════════════════════
#  PAGE: 2FA
# ════════════════════════════════════════════════════
def page_2fa():
    p2 = st.session_state.pending_2fa
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(logo_html(), unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card" style="text-align:center;margin-top:1rem;">
          <div style="color:var(--blue-glow);margin-bottom:1rem;">{icon("key",36,"#60a5fa")}</div>
          <h2 style="margin-bottom:0.5rem;">Verificação em 2 etapas</h2>
          <p style="color:var(--text-2);font-size:0.87rem;">Código enviado para <strong>{p2['email']}</strong></p>
          <div style="background:rgba(37,99,235,0.12);border:1px solid rgba(37,99,235,0.25);border-radius:12px;padding:12px;margin:1rem 0;">
            <div style="font-size:0.72rem;color:var(--text-3);margin-bottom:4px;">SEU CÓDIGO (demo)</div>
            <div style="font-family:'Playfair Display',serif;font-size:2rem;font-weight:700;letter-spacing:0.2em;color:var(--blue-glow);">{p2['code']}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        typed = st.text_input("Código", max_chars=6, placeholder="000000", key="fa_c", label_visibility="collapsed")
        if st.button("Verificar", use_container_width=True, key="btn_fa"):
            if typed == p2["code"]:
                st.session_state.logged_in = True
                st.session_state.current_user = p2["email"]
                st.session_state.pending_2fa = None
                st.session_state.page = "feed"
                st.rerun()
            else:
                st.error("Código inválido.")
        if st.button("← Voltar", key="btn_fa_back"):
            st.session_state.page = "login"
            st.rerun()

# ════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════
NAV = [
    ("feed",         "home",       "Feed"),
    ("folders",      "folder",     "Pastas"),
    ("search",       "search",     "Buscar Artigos"),
    ("knowledge",    "network",    "Rede de Conhecimento"),
    ("chat",         "chat",       "Chat Seguro"),
    ("analytics",    "chart",      "Análises"),
    ("img_search",   "image",      "Busca por Imagem"),
    ("settings",     "settings",   "Configurações"),
]

def render_sidebar():
    with st.sidebar:
        st.markdown(logo_html(1.4), unsafe_allow_html=True)
        st.markdown("<hr style='margin:0.8rem 0;'>", unsafe_allow_html=True)

        u    = guser()
        name = u.get("name", "Usuário")
        ini  = initials(name)
        area = u.get("area", "")
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;padding:10px 12px;
                    background:var(--glass);border:1px solid var(--border);border-radius:14px;margin-bottom:1rem;">
          {av_html(ini, 44)}
          <div style="overflow:hidden;">
            <div style="font-weight:600;font-size:0.9rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</div>
            <div style="color:var(--text-3);font-size:0.73rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{area}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        notifs = st.session_state.notifications
        if notifs:
            with st.expander(f"{icon('bell',14,'#60a5fa')} Notificações ({len(notifs)})", expanded=False):
                for n in notifs:
                    st.markdown(f'<div style="font-size:0.78rem;color:var(--text-2);padding:5px 0;border-bottom:1px solid var(--border);">{n}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        cur_page = st.session_state.page
        for key, ic, label in NAV:
            active = cur_page == key
            col_ic, col_lb = st.columns([0.18, 0.82])
            with col_ic:
                ic_color = "#60a5fa" if active else "#4a5e80"
                st.markdown(f'<div style="padding-top:8px;">{icon(ic,16,ic_color)}</div>', unsafe_allow_html=True)
            with col_lb:
                lbl_style = f"color:var(--text-1) !important;background:rgba(37,99,235,0.15);" if active else ""
                if st.button(label, key=f"nav_{key}", use_container_width=True):
                    st.session_state.page = key
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        col_ic2, col_lb2 = st.columns([0.18, 0.82])
        with col_ic2:
            st.markdown(f'<div style="padding-top:8px;">{icon("logout",16,"#ef4444")}</div>', unsafe_allow_html=True)
        with col_lb2:
            if st.button("Sair", key="nav_logout", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.current_user = None
                st.session_state.page = "login"
                st.rerun()

# ════════════════════════════════════════════════════
#  PAGE: FEED
# ════════════════════════════════════════════════════
def page_feed():
    st.markdown('<div class="page-wrap">', unsafe_allow_html=True)
    st.markdown('<h1>Feed de Pesquisas</h1>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:var(--text-3);margin-bottom:1.5rem;font-size:0.88rem;">Acompanhe pesquisas em andamento da comunidade científica</p>', unsafe_allow_html=True)

    email = st.session_state.current_user
    col_main, col_side = st.columns([2.1, 0.9])

    with col_main:
        # ── Recommended
        recs = recommended_posts(email)
        if recs:
            st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:0.8rem;">{icon("star",15,"#22d3ee")}<span style="font-size:0.82rem;color:var(--cyan-soft);font-weight:600;letter-spacing:0.04em;">RECOMENDADO PARA VOCÊ</span></div>', unsafe_allow_html=True)
            for p in recs[:2]:
                render_post(p, recommended=True)
            st.markdown("<hr>", unsafe_allow_html=True)

        # ── Publish box
        with st.expander(f"{icon('plus',14,'#60a5fa')} Publicar nova pesquisa"):
            np_t  = st.text_input("Título", key="np_t")
            np_ab = st.text_area("Resumo / Abstract", key="np_ab", height=90)
            np_tg = st.text_input("Tags (separadas por vírgula)", key="np_tg")
            np_st = st.selectbox("Status", ["Em andamento","Publicado","Concluído"], key="np_st")
            if st.button("Publicar", key="btn_pub"):
                if np_t and np_ab:
                    u = guser()
                    nm = u.get("name","Usuário")
                    tags = [t.strip() for t in np_tg.split(",") if t.strip()]
                    st.session_state.feed_posts.insert(0, {
                        "id": len(st.session_state.feed_posts)+1,
                        "author": nm, "avatar": initials(nm),
                        "area": u.get("area",""),
                        "title": np_t, "abstract": np_ab,
                        "tags": tags, "likes": 0,
                        "comments": [], "status": np_st,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "liked_by": [], "connections": tags[:3],
                    })
                    record_interaction(tags, 2.0)
                    st.success("Pesquisa publicada!")
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        for p in st.session_state.feed_posts:
            render_post(p)

    with col_side:
        # Researchers
        st.markdown(f'<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:1rem;font-weight:600;">{icon("user",15,"#60a5fa")} Pesquisadores</div>', unsafe_allow_html=True)
        for c in st.session_state.chat_contacts:
            is_fol = c["name"] in st.session_state.followed
            dot = '<span class="dot-on"></span>' if c["online"] else '<span class="dot-off"></span>'
            c1, c2 = st.columns([3,1])
            with c1:
                st.markdown(f'<div style="font-size:0.85rem;display:flex;align-items:center;">{dot}{c["name"]}</div>', unsafe_allow_html=True)
            with c2:
                lbl = "✓" if is_fol else "+"
                if st.button(lbl, key=f"fol_{c['name']}"):
                    if is_fol: st.session_state.followed.remove(c["name"])
                    else:      st.session_state.followed.append(c["name"])
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # Trending
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:1rem;font-weight:600;">{icon("trending",15,"#60a5fa")} Áreas em Alta</div>', unsafe_allow_html=True)
        for area, cnt in [("Quantum ML",42),("CRISPR 2026",38),("Neuroplasticidade",31),("LLMs Científicos",27)]:
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--border);font-size:0.82rem;"><span style="color:var(--text-2);">{area}</span><span style="color:var(--blue-glow);">{cnt}</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_post(post, recommended=False):
    email = st.session_state.current_user
    liked = email in post["liked_by"]
    rec_badge = f'<span class="rec-pill">{icon("zap",10,"#22d3ee")} Recomendado</span> ' if recommended else ""

    st.markdown(f"""
    <div class="card">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:1rem;">
        {av_html(post['avatar'], 40)}
        <div style="flex:1;">
          <div style="font-weight:600;font-size:0.92rem;">{post['author']}</div>
          <div style="color:var(--text-3);font-size:0.75rem;">{post['area']} · {post['date']}</div>
        </div>
        {rec_badge}{status_html(post['status'])}
      </div>
      <h3 style="margin-bottom:0.5rem;font-size:1.05rem;line-height:1.4;">{post['title']}</h3>
      <p style="color:var(--text-2);font-size:0.86rem;line-height:1.65;margin-bottom:0.8rem;">{post['abstract']}</p>
      <div>{tags_html(post['tags'])}</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, _ = st.columns([1, 1, 1, 4])
    with c1:
        h_ico = icon("heart",14,"#ef4444") if liked else icon("heart",14,"#4a5e80")
        if st.button(f"{post['likes']}", key=f"lk_{post['id']}"):
            if liked:
                post["liked_by"].remove(email); post["likes"] -= 1
            else:
                post["liked_by"].append(email); post["likes"] += 1
                record_interaction(post["tags"], 1.5)
            st.rerun()
    with c2:
        if st.button(f"{len(post['comments'])}", key=f"cm_t_{post['id']}"):
            k = f"sc_{post['id']}"
            st.session_state[k] = not st.session_state.get(k, False)
            record_interaction(post["tags"], 0.5)
            st.rerun()
    with c3:
        if st.button(icon("share",14,"#4a5e80"), key=f"sh_{post['id']}"):
            st.toast("Link copiado!")

    if st.session_state.get(f"sc_{post['id']}", False):
        for c in post["comments"]:
            st.markdown(f'<div style="background:var(--surface);border-radius:10px;padding:7px 12px;margin:3px 0;font-size:0.83rem;border:1px solid var(--border);"><strong style="color:var(--blue-glow);">{c["user"]}</strong>: {c["text"]}</div>', unsafe_allow_html=True)
        nc = st.text_input("Comentar…", key=f"ci_{post['id']}", label_visibility="collapsed", placeholder="Adicionar comentário…")
        if st.button("Enviar", key=f"cs_{post['id']}"):
            if nc:
                post["comments"].append({"user": guser().get("name","Você"), "text": nc})
                record_interaction(post["tags"], 0.8)
                st.rerun()

# ════════════════════════════════════════════════════
#  PAGE: PASTAS
# ════════════════════════════════════════════════════
def page_folders():
    st.markdown('<div class="page-wrap">', unsafe_allow_html=True)
    st.markdown('<h1>Pastas de Pesquisa</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--text-3);font-size:0.87rem;margin-bottom:1.5rem;">Organize artigos e pesquisas por tema</p>', unsafe_allow_html=True)

    c1, _ = st.columns([2, 3])
    with c1:
        nf = st.text_input("", placeholder="Nova pasta…", key="nf", label_visibility="collapsed")
        if st.button(f"{icon('plus',13,'currentColor')} Criar pasta", key="btn_nf"):
            if nf and nf not in st.session_state.folders:
                st.session_state.folders[nf] = []
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    cols = st.columns(3)
    for idx, (fname, files) in enumerate(list(st.session_state.folders.items())):
        with cols[idx % 3]:
            st.markdown(f"""
            <div class="card" style="text-align:center;cursor:pointer;">
              <div style="color:var(--blue-glow);margin-bottom:8px;">{icon("folder",32,"#60a5fa")}</div>
              <div style="font-family:'Playfair Display',serif;font-weight:700;font-size:1rem;">{fname}</div>
              <div style="color:var(--text-3);font-size:0.75rem;margin-top:4px;">{len(files)} arquivo(s)</div>
            </div>
            """, unsafe_allow_html=True)
            with st.expander("Ver arquivos"):
                for f in files:
                    st.markdown(f'<div style="display:flex;align-items:center;gap:8px;font-size:0.82rem;padding:4px 0;color:var(--text-2);">{icon("bookmark",12,"#4a5e80")} {f}</div>', unsafe_allow_html=True)
                up = st.file_uploader("", key=f"up_{fname}", label_visibility="collapsed")
                if up and up.name not in files:
                    files.append(up.name)
                    st.rerun()
            if st.button("Excluir", key=f"df_{fname}"):
                del st.session_state.folders[fname]
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════
#  PAGE: BUSCA DE ARTIGOS
# ════════════════════════════════════════════════════
ARTICLES = [
    {"title":"Transformer Models for Scientific Discovery","authors":"Smith, J. et al.","year":2025,"journal":"Nature Machine Intelligence","doi":"10.1038/s42256-025-0001","abstract":"Novel transformer architecture fine-tuned on PubMed and arXiv for automated hypothesis generation.","tags":["LLM","IA","ciência automatizada"]},
    {"title":"CRISPR-Cas13 for RNA Knockdown in Neurons","authors":"Oliveira, R. et al.","year":2024,"journal":"Cell","doi":"10.1016/j.cell.2024.02.033","abstract":"Eficiência de 92% no knockdown de transcritos em neurônios corticais usando Cas13d.","tags":["CRISPR","neurociência","RNA"]},
    {"title":"Quantum Advantage in Drug Discovery","authors":"Chen, L. et al.","year":2025,"journal":"Science","doi":"10.1126/science.adm1234","abstract":"VQE reduziu espaço de busca conformacional para docking proteína-ligante em 10⁴.","tags":["quantum","fármacos","proteínas"]},
    {"title":"Sleep and Synaptic Homeostasis: 2025 Update","authors":"Tononi, G. et al.","year":2025,"journal":"Neuron","doi":"10.1016/j.neuron.2025.01.010","abstract":"Nova evidência fMRI mostrando normalização overnight da densidade de espinhas.","tags":["sono","sinapses","memória"]},
    {"title":"Federated Learning for Medical Imaging Privacy","authors":"Kumar, P. et al.","year":2026,"journal":"Lancet Digital Health","doi":"10.1016/S2589-7500(26)00021","abstract":"Framework federado atinge 94.2% de acurácia diagnóstica sem compartilhar imagens brutas.","tags":["privacidade","ML médico","federado"]},
    {"title":"Dark Matter Distribution via Weak Gravitational Lensing","authors":"Nair, P. et al.","year":2026,"journal":"ApJ Letters","doi":"10.3847/2041-8213/abc123","abstract":"Mapeamento de matéria escura com precisão sub-arcminuto usando 100M de galáxias do DES Y3.","tags":["astrofísica","matéria escura","cosmologia"]},
]

def page_search():
    st.markdown('<div class="page-wrap">', unsafe_allow_html=True)
    st.markdown('<h1>Busca de Artigos</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--text-3);font-size:0.87rem;margin-bottom:1.5rem;">Base científica exclusiva da plataforma Nebula</p>', unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    with c1:
        q = st.text_input("", placeholder=f"{icon('search',14,'currentColor')}  Buscar por título, autor, tag…", key="sq", label_visibility="collapsed")
    with c2:
        yf = st.selectbox("", ["Todos","2026","2025","2024"], key="yf", label_visibility="collapsed")

    if q:
        ql = q.lower()
        res = [a for a in ARTICLES if ql in a["title"].lower() or ql in a["abstract"].lower() or any(ql in t for t in a["tags"]) or ql in a["authors"].lower()]
        if yf != "Todos": res = [a for a in res if str(a["year"]) == yf]
        # record interest
        for a in res[:3]: record_interaction(a["tags"], 0.5)
        st.markdown(f'<p style="color:var(--text-3);font-size:0.82rem;margin-bottom:1rem;">{len(res)} resultado(s)</p>', unsafe_allow_html=True)
        if res:
            for a in res: render_article(a)
        else:
            st.markdown('<div class="card" style="text-align:center;padding:3rem;"><div style="color:var(--text-3);">Nenhum resultado encontrado</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:var(--text-3);font-size:0.82rem;margin-bottom:1rem;">Artigos em destaque</div>', unsafe_allow_html=True)
        for a in ARTICLES[:4]: render_article(a)
    st.markdown('</div>', unsafe_allow_html=True)

def render_article(a):
    st.markdown(f"""
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.5rem;">
        <div style="flex:1;">
          <h3 style="margin-bottom:0.3rem;font-size:0.98rem;line-height:1.4;">{a['title']}</h3>
          <div style="color:var(--text-3);font-size:0.76rem;margin-bottom:0.5rem;">{a['authors']} · <em>{a['journal']}</em> · {a['year']}</div>
          <p style="color:var(--text-2);font-size:0.85rem;line-height:1.6;margin-bottom:0.6rem;">{a['abstract']}</p>
          <div>{tags_html(a['tags'])}</div>
        </div>
      </div>
      <div style="margin-top:0.6rem;font-size:0.72rem;color:var(--text-3);">DOI: {a['doi']}</div>
    </div>
    """, unsafe_allow_html=True)
    ca, cb, _ = st.columns([1,1,5])
    with ca:
        if st.button("Salvar", key=f"sv_{a['doi']}"):
            first = list(st.session_state.folders.keys())[0]
            fn = f"{a['title'][:28]}.pdf"
            if fn not in st.session_state.folders[first]:
                st.session_state.folders[first].append(fn)
            st.toast("Salvo na primeira pasta!")
    with cb:
        if st.button("Citar", key=f"ct_{a['doi']}"):
            st.toast("Citação copiada!")

# ════════════════════════════════════════════════════
#  PAGE: REDE DE CONHECIMENTO
# ════════════════════════════════════════════════════
def page_knowledge():
    st.markdown('<div class="page-wrap">', unsafe_allow_html=True)
    st.markdown('<h1>Rede de Conhecimento</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--text-3);font-size:0.87rem;margin-bottom:1.5rem;">Conecte tópicos e visualize relações entre áreas do conhecimento</p>', unsafe_allow_html=True)

    # Build graph
    nx = [0.50,0.15,0.85,0.50,0.15,0.85,0.50,0.30,0.70,0.20,0.80,0.50,0.68,0.32]
    ny = [0.90,0.70,0.70,0.50,0.35,0.35,0.20,0.60,0.60,0.50,0.50,0.35,0.78,0.78]
    nlabels = ["IA","Machine Learning","Otimização","Neurociência","Memória","Sono",
               "Genômica","Redes Neurais","Quantum ML","Plasticidade","CRISPR","Proteômica","Astrofísica","Cosmologia"]
    nsizes  = [30,22,22,30,18,18,28,20,24,18,22,20,26,20]
    edges   = [(0,1),(0,2),(0,7),(0,8),(1,8),(1,2),(3,4),(3,5),(3,9),(6,10),(6,11),(8,2),(12,13),(12,1)]

    ex, ey = [], []
    for s, e in edges:
        ex += [nx[s], nx[e], None]
        ey += [ny[s], ny[e], None]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines",
        line=dict(color="rgba(37,99,235,0.3)", width=1.8), hoverinfo="none"))
    fig.add_trace(go.Scatter(x=nx, y=ny, mode="markers+text",
        marker=dict(size=nsizes,
                    color=["#2563eb","#1d4ed8","#1e40af","#3b82f6","#60a5fa",
                           "#93c5fd","#2563eb","#1d4ed8","#06b6d4","#60a5fa",
                           "#3b82f6","#1d4ed8","#0ea5e9","#0284c7"],
                    line=dict(color="rgba(147,197,253,0.4)", width=1.5), opacity=0.92),
        text=nlabels, textposition="top center",
        textfont=dict(color="#94a8d0", size=10, family="DM Sans"),
        hoverinfo="text"))
    fig.update_layout(showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10,r=10,t=10,b=10), height=400,
        xaxis=dict(showgrid=False,zeroline=False,showticklabels=False),
        yaxis=dict(showgrid=False,zeroline=False,showticklabels=False))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown('<h3>Adicionar conexão</h3>', unsafe_allow_html=True)
    ca, cb, cc = st.columns(3)
    with ca: t1 = st.text_input("Tópico A", placeholder="Epigenética", key="t1")
    with cb: t2 = st.text_input("Tópico B", placeholder="Câncer",      key="t2")
    with cc:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Conectar", key="btn_con"):
            if t1 and t2:
                st.session_state.knowledge_nodes.append({"id":t1,"connections":[t2]})
                st.session_state.notifications.insert(0, f"Nova conexão: {t1} ↔ {t2}")
                record_interaction([t1.lower(), t2.lower()], 1.0)
                st.success(f"{t1} ↔ {t2} adicionados!")
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    for node in st.session_state.knowledge_nodes:
        for conn in node["connections"]:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:12px;background:var(--glass);
                        border:1px solid var(--border);border-radius:12px;padding:10px 16px;margin-bottom:6px;">
              <span style="background:rgba(37,99,235,0.18);border-radius:8px;padding:3px 12px;font-size:0.83rem;font-weight:600;">{node['id']}</span>
              <span style="color:var(--text-3);">{icon("trending",14,"#4a5e80")}</span>
              <span style="background:rgba(6,182,212,0.15);border-radius:8px;padding:3px 12px;font-size:0.83rem;font-weight:600;">{conn}</span>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════
#  PAGE: CHAT
# ════════════════════════════════════════════════════
def page_chat():
    st.markdown('<div class="page-wrap">', unsafe_allow_html=True)
    st.markdown('<h1>Chat Seguro</h1>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:var(--text-3);font-size:0.87rem;margin-bottom:1.5rem;display:flex;align-items:center;gap:6px;">{icon("lock",13,"#10b981")} Mensagens criptografadas AES-256 end-to-end</p>', unsafe_allow_html=True)

    col_c, col_m = st.columns([0.85, 2.5])
    with col_c:
        st.markdown('<div style="font-size:0.8rem;font-weight:600;color:var(--text-3);letter-spacing:0.06em;margin-bottom:0.8rem;">CONVERSAS</div>', unsafe_allow_html=True)
        for c in st.session_state.chat_contacts:
            active = st.session_state.active_chat == c["name"]
            bg  = "rgba(37,99,235,0.18)" if active else "var(--glass)"
            bdr = "rgba(96,165,250,0.4)" if active else "var(--border)"
            dot = '<span class="dot-on"></span>' if c["online"] else '<span class="dot-off"></span>'
            st.markdown(f"""
            <div style="background:{bg};border:1px solid {bdr};border-radius:14px;padding:11px 13px;margin-bottom:6px;">
              <div style="display:flex;align-items:center;gap:9px;">
                {av_html(c['avatar'], 34)}
                <div style="overflow:hidden;">
                  <div style="font-size:0.85rem;font-weight:600;display:flex;align-items:center;">{dot}{c['name']}</div>
                  <div style="font-size:0.73rem;color:var(--text-3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100px;">{c['last']}</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Abrir", key=f"oc_{c['name']}", use_container_width=True):
                st.session_state.active_chat = c["name"]
                st.rerun()

    with col_m:
        if st.session_state.active_chat:
            contact = st.session_state.active_chat
            msgs = st.session_state.chat_messages.get(contact, [])
            st.markdown(f"""
            <div style="background:var(--glass);border:1px solid var(--border);border-radius:16px;padding:14px 18px;margin-bottom:1rem;display:flex;align-items:center;gap:12px;">
              {av_html(contact[:2].upper(), 38)}
              <div>
                <div style="font-weight:700;">{contact}</div>
                <div style="font-size:0.75rem;color:var(--success);display:flex;align-items:center;gap:5px;">{icon("shield",11,"#10b981")} Criptografia ativa</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            for msg in msgs:
                is_me = msg["from"] == "me"
                cls   = "bbl-me" if is_me else "bbl-them"
                st.markdown(f'<div class="{cls}">{msg["text"]}<div style="font-size:0.68rem;color:var(--text-3);margin-top:4px;text-align:{"right" if is_me else "left"};">{msg["time"]}</div></div>', unsafe_allow_html=True)
            nm = st.text_input("", placeholder="Mensagem segura…", key=f"mi_{contact}", label_visibility="collapsed")
            if st.button(f"{icon('send',14,'currentColor')} Enviar", key=f"ms_{contact}"):
                if nm:
                    now = datetime.now().strftime("%H:%M")
                    st.session_state.chat_messages.setdefault(contact, []).append({"from":"me","text":nm,"time":now})
                    for c in st.session_state.chat_contacts:
                        if c["name"] == contact: c["last"] = nm[:40]
                    st.rerun()
        else:
            st.markdown(f"""
            <div class="card" style="text-align:center;padding:4rem;">
              <div style="color:var(--text-3);margin-bottom:1rem;">{icon("chat",40,"#1e3a5f")}</div>
              <div style="color:var(--text-3);">Selecione uma conversa</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════
#  PAGE: ANALYTICS
# ════════════════════════════════════════════════════
def page_analytics():
    st.markdown('<div class="page-wrap">', unsafe_allow_html=True)
    st.markdown('<h1>Análises de Impacto</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--text-3);font-size:0.87rem;margin-bottom:1.5rem;">Métricas detalhadas da sua pesquisa</p>', unsafe_allow_html=True)

    d = st.session_state.stats_data
    kpis = [("230","Visualizações","eye"),("12","Citações","bookmark"),("47","Seguidores","user"),("h-4","Índice H","star")]
    cols = st.columns(4)
    for col, (v, l, ic) in zip(cols, kpis):
        with col:
            st.markdown(f'<div class="mbox"><div style="color:var(--blue-glow);margin-bottom:8px;">{icon(ic,22,"#60a5fa")}</div><div class="mval">{v}</div><div class="mlbl">{l}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    plot_cfg = dict(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#4a5e80", family="DM Sans"),
                    margin=dict(l=10,r=10,t=40,b=10),
                    xaxis=dict(showgrid=False, color="#4a5e80"),
                    yaxis=dict(showgrid=True, gridcolor="rgba(37,99,235,0.08)", color="#4a5e80"))

    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=d["months"], y=d["views"], fill="tozeroy",
            fillcolor="rgba(37,99,235,0.12)", line=dict(color="#3b7cf4",width=2.5),
            mode="lines+markers", marker=dict(size=5,color="#60a5fa")))
        fig.update_layout(title=dict(text="Visualizações", font=dict(color="#e0e8ff",family="Playfair Display")),
                          height=260, **plot_cfg)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=d["months"], y=d["citations"],
            marker=dict(color=d["citations"],colorscale=[[0,"#0a1628"],[1,"#06b6d4"]],
                        line=dict(color="rgba(96,165,250,0.3)",width=1))))
        fig2.update_layout(title=dict(text="Citações", font=dict(color="#e0e8ff",family="Playfair Display")),
                           height=260, **plot_cfg)
        st.plotly_chart(fig2, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        fig3 = go.Figure(go.Pie(
            labels=["IA","Neurociência","Genômica","Quantum"], values=[42,28,18,12], hole=0.62,
            marker=dict(colors=["#2563eb","#06b6d4","#60a5fa","#1d4ed8"],
                        line=dict(color=["#03040a"]*4, width=2)),
            textfont=dict(color="white")))
        fig3.update_layout(title=dict(text="Público por área", font=dict(color="#e0e8ff",family="Playfair Display")),
                           height=260, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                           legend=dict(font=dict(color="#94a8d0")), margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(fig3, use_container_width=True)

    with c4:
        fig4 = go.Figure(go.Bar(
            x=[95,62,38,25,10], y=["Brasil","EUA","Portugal","Alemanha","Argentina"], orientation="h",
            marker=dict(color=["#2563eb","#1d4ed8","#3b82f6","#1e40af","#60a5fa"],
                        line=dict(color="rgba(96,165,250,0.3)",width=1))))
        fig4.update_layout(title=dict(text="Leitores por país", font=dict(color="#e0e8ff",family="Playfair Display")),
                           height=260, **plot_cfg)
        st.plotly_chart(fig4, use_container_width=True)

    # Interest profile from recommendation engine
    email = st.session_state.current_user
    prefs = st.session_state.user_prefs.get(email, {})
    if prefs:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<h3>Perfil de Interesses (IA)</h3>', unsafe_allow_html=True)
        st.markdown('<p style="color:var(--text-3);font-size:0.82rem;margin-bottom:1rem;">Baseado nas suas interações na plataforma</p>', unsafe_allow_html=True)
        top = sorted(prefs.items(), key=lambda x: -x[1])[:8]
        mx  = max(s for _,s in top) if top else 1
        for tag, score in top:
            pct = int(score / mx * 100)
            st.markdown(f'<div style="margin-bottom:8px;"><div style="display:flex;justify-content:space-between;font-size:0.82rem;margin-bottom:4px;"><span style="color:var(--text-2);">{tag}</span><span style="color:var(--blue-glow);">{pct}%</span></div></div>', unsafe_allow_html=True)
            st.progress(pct / 100)
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════
#  PAGE: BUSCA POR IMAGEM
# ════════════════════════════════════════════════════
def page_img_search():
    st.markdown('<div class="page-wrap">', unsafe_allow_html=True)
    st.markdown('<h1>Busca por Imagem</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--text-3);font-size:0.87rem;margin-bottom:1.5rem;">Identifique estruturas, organismos ou conceitos e encontre pesquisas relacionadas</p>', unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1.6])
    with c1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<div style="font-weight:600;margin-bottom:1rem;display:flex;align-items:center;gap:8px;">{icon("upload",15,"#60a5fa")} Upload de imagem</div>', unsafe_allow_html=True)
        img = st.file_uploader("", type=["png","jpg","jpeg","webp"], label_visibility="collapsed")
        cat = st.selectbox("Tipo", ["Auto","Estrutura molecular","Célula/Tecido","Organismo","Gráfico científico","Equação"], key="img_cat")
        if st.button(f"{icon('search',13,'currentColor')} Analisar", use_container_width=True, key="btn_img"):
            if img: st.session_state.img_done = True
            else:   st.warning("Faça upload de uma imagem primeiro.")
        if img: st.image(img, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        if st.session_state.get("img_done"):
            st.markdown(f"""
            <div class="card">
              <div style="font-weight:700;margin-bottom:1rem;display:flex;align-items:center;gap:8px;">{icon("zap",15,"#22d3ee")} Análise da IA</div>
              <div style="background:rgba(37,99,235,0.1);border:1px solid rgba(37,99,235,0.2);border-radius:12px;padding:14px;margin-bottom:1rem;">
                <div style="font-size:0.75rem;color:var(--text-3);letter-spacing:0.06em;margin-bottom:4px;">ESTRUTURA DETECTADA</div>
                <div style="font-family:'Playfair Display',serif;font-weight:700;font-size:1.1rem;">Neurônio Piramidal Cortical</div>
                <div style="font-size:0.78rem;color:var(--text-3);margin-top:4px;">Confiança: 87% · Camada V, Córtex Motor</div>
              </div>
              <div style="font-size:0.78rem;color:var(--text-3);margin-bottom:6px;">Termos relacionados:</div>
              {tags_html(["neurônio piramidal","axônio","dendritos","córtex","Layer V"])}
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div style="font-weight:600;margin-bottom:0.8rem;font-size:0.88rem;">Pesquisas encontradas</div>', unsafe_allow_html=True)
            matches = [
                ("Morphology of Layer V Pyramidal Neurons", "94%"),
                ("Dendritic Integration in Cortical Neurons", "88%"),
                ("Cortical Circuit Connectivity and Behavior",  "76%"),
            ]
            for title, pct in matches:
                st.markdown(f"""
                <div style="background:var(--glass);border:1px solid var(--border);border-radius:12px;
                            padding:11px 15px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">
                  <span style="font-size:0.86rem;">{title}</span>
                  <span style="background:rgba(16,185,129,0.12);border:1px solid rgba(16,185,129,0.3);
                               border-radius:12px;padding:2px 10px;font-size:0.73rem;color:#10b981;
                               font-weight:600;white-space:nowrap;margin-left:12px;">{pct}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="card" style="text-align:center;padding:4rem 2rem;">
              <div style="color:var(--text-3);margin-bottom:1rem;">{icon("image",44,"#1e3a5f")}</div>
              <div style="font-family:'Playfair Display',serif;font-size:1rem;color:var(--text-2);margin-bottom:0.5rem;">Carregue uma imagem para começar</div>
              <div style="color:var(--text-3);font-size:0.8rem;">Suportamos estruturas moleculares, células, organismos e gráficos científicos</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════
#  PAGE: CONFIGURAÇÕES
# ════════════════════════════════════════════════════
def page_settings():
    st.markdown('<div class="page-wrap">', unsafe_allow_html=True)
    st.markdown('<h1>Configurações</h1>', unsafe_allow_html=True)

    u     = guser()
    email = st.session_state.current_user
    tab_p, tab_s, tab_pr = st.tabs(["  Perfil  ","  Segurança  ","  Privacidade  "])

    # ── PERFIL
    with tab_p:
        nm   = u.get("name","")
        ini  = initials(nm)
        ca, cb = st.columns([0.6, 2])
        with ca:
            st.markdown(av_html(ini, 72), unsafe_allow_html=True)
            ph = st.file_uploader("Foto", type=["png","jpg","jpeg"], label_visibility="collapsed")
            if ph:
                st.session_state.users[email]["photo"] = ph.name
                st.success("Foto atualizada!")
        with cb:
            new_n  = st.text_input("Nome completo",    value=u.get("name",""),  key="cfg_n")
            new_e  = st.text_input("E-mail",           value=email,             key="cfg_e")
            new_a  = st.text_input("Área de pesquisa", value=u.get("area",""),  key="cfg_a")
            new_b  = st.text_area( "Biografia",        value=u.get("bio",""),   key="cfg_b", height=80)
            if st.button("Salvar perfil", key="btn_sp"):
                st.session_state.users[email]["name"] = new_n
                st.session_state.users[email]["area"] = new_a
                st.session_state.users[email]["bio"]  = new_b
                if new_e != email and new_e not in st.session_state.users:
                    st.session_state.users[new_e] = st.session_state.users.pop(email)
                    st.session_state.current_user = new_e
                st.success("Perfil atualizado!")
                st.rerun()

    # ── SEGURANÇA
    with tab_s:
        st.markdown('<h3>Alterar senha</h3>', unsafe_allow_html=True)
        op  = st.text_input("Senha atual",        type="password", key="op")
        np_ = st.text_input("Nova senha",         type="password", key="np_")
        np2 = st.text_input("Confirmar nova senha",type="password",key="np2")
        if st.button("Alterar senha", key="btn_cpw"):
            if hp(op) != u["password"]:      st.error("Senha atual incorreta.")
            elif np_ != np2:                  st.error("Senhas não coincidem.")
            elif len(np_) < 6:               st.error("Senha muito curta.")
            else:
                st.session_state.users[email]["password"] = hp(np_)
                st.success("Senha alterada!")

        st.markdown("---")
        st.markdown('<h3>Autenticação em 2 fatores</h3>', unsafe_allow_html=True)
        en = u.get("2fa_enabled", False)
        st.markdown(f"""
        <div style="background:var(--glass);border:1px solid var(--border);border-radius:14px;
                    padding:16px;display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;">
          <div style="display:flex;align-items:center;gap:12px;">
            <div>{icon("mail",18,"#60a5fa")}</div>
            <div>
              <div style="font-weight:600;font-size:0.9rem;">2FA por e-mail</div>
              <div style="font-size:0.75rem;color:var(--text-3);">{email}</div>
            </div>
          </div>
          <span style="color:{'#10b981' if en else '#ef4444'};font-size:0.82rem;font-weight:700;">{'Ativo' if en else 'Inativo'}</span>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Desativar 2FA" if en else "Ativar 2FA", key="btn_2fa"):
            st.session_state.users[email]["2fa_enabled"] = not en
            st.success(f"2FA {'desativado' if en else 'ativado'}!")
            if not en:
                demo = code6()
                st.info(f"Código de confirmação (demo): **{demo}**")
            st.rerun()

        st.markdown("---")
        st.markdown('<h3>Testar envio de código</h3>', unsafe_allow_html=True)
        if st.button(f"{icon('mail',13,'currentColor')} Enviar código de teste", key="btn_tc"):
            c = code6()
            st.session_state["test_code"] = c
            st.info(f"Código gerado: **{c}** *(em produção, enviado via SMTP para {email})*")
        if st.session_state.get("test_code"):
            tv = st.text_input("Digite o código para validar:", max_chars=6, key="tv")
            if st.button("Verificar código", key="btn_vtc"):
                if tv == st.session_state["test_code"]:
                    st.success("Código verificado! Sistema de 2FA funcionando.")
                else:
                    st.error("Código inválido.")

    # ── PRIVACIDADE
    with tab_pr:
        st.markdown(f"""
        <div class="card">
          <div style="font-weight:700;margin-bottom:1rem;">Proteções ativas</div>
          <div style="display:grid;gap:10px;">
            {''.join(f"""<div style="display:flex;align-items:center;gap:12px;background:rgba(16,185,129,0.07);border:1px solid rgba(16,185,129,0.2);border-radius:12px;padding:12px;">
              <div>{icon("shield",18,"#10b981")}</div>
              <div><div style="font-weight:600;color:#10b981;font-size:0.88rem;">{name}</div><div style="font-size:0.75rem;color:var(--text-3);">{desc}</div></div>
            </div>""" for name, desc in [
                ("AES-256","Criptografia de mensagens end-to-end"),
                ("SHA-256","Hash de senhas com salt criptográfico"),
                ("TLS 1.3","Transmissão segura de todos os dados"),
                ("Zero Knowledge","Pesquisas privadas inacessíveis pela plataforma"),
            ])}
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<h3>Visibilidade</h3>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.selectbox("Perfil",     ["Público","Só seguidores","Privado"], key="vp")
            st.selectbox("Pesquisas",  ["Público","Só seguidores","Privado"], key="vr")
        with c2:
            st.selectbox("Estatísticas",        ["Público","Privado"], key="vs")
            st.selectbox("Rede de conhecimento",["Público","Só seguidores","Privado"], key="vn")
        if st.button("Salvar privacidade", key="btn_priv"):
            st.success("Configurações salvas!")
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════
#  ROUTER
# ════════════════════════════════════════════════════
def main():
    if not st.session_state.logged_in:
        p = st.session_state.page
        if   p == "verify_email": page_verify_email()
        elif p == "2fa":          page_2fa()
        else:                     page_login()
        return

    render_sidebar()
    p = st.session_state.page
    routes = {
        "feed":       page_feed,
        "folders":    page_folders,
        "search":     page_search,
        "knowledge":  page_knowledge,
        "chat":       page_chat,
        "analytics":  page_analytics,
        "img_search": page_img_search,
        "settings":   page_settings,
    }
    routes.get(p, page_feed)()

if __name__ == "__main__":
    main()
