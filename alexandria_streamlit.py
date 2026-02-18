import sys, os, json, hashlib, random, string, base64, re
from datetime import datetime
from collections import defaultdict

import plotly.graph_objects as go
import numpy as np
from PIL import Image as PILImage
import requests

import streamlit as st

st.set_page_config(page_title="Nebula", page_icon="🔬",
                   layout="wide", initial_sidebar_state="collapsed")

DB_FILE = "nebula_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,"r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_db():
    try:
        with open(DB_FILE,"w", encoding="utf-8") as f:
            json.dump({
                "users": st.session_state.users,
                "feed_posts": st.session_state.feed_posts,
                "folders": st.session_state.folders,
                "knowledge_nodes": st.session_state.knowledge_nodes,
                "user_prefs": st.session_state.user_prefs
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

def hp(pw): return hashlib.sha256(pw.encode()).hexdigest()
def code6(): return ''.join(random.choices(string.digits, k=6))
def ini(n):
    if not isinstance(n, str): n = str(n)
    return ''.join(w[0].upper() for w in n.split()[:2])

def img_to_b64(file_obj):
    try:
        file_obj.seek(0)
        data = file_obj.read()
        ext = getattr(file_obj,"name","img.png").split(".")[-1].lower()
        mime = {"jpg":"jpeg","jpeg":"jpeg","png":"png","gif":"gif","webp":"webp"}.get(ext,"png")
        return f"data:image/{mime};base64,{base64.b64encode(data).decode()}"
    except:
        return None

# ─── CSS LIQUID GLASS ─────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,300&display=swap');

:root {
  --void: #010409;
  --deep: #050c1a;
  --navy: #071428;
  --surface: #0a1a35;
  --elevated: #0e2040;
  --panel: #0d1e3d;

  --blue-950: #0a1628;
  --blue-900: #0f2040;
  --blue-800: #1a3a6b;
  --blue-700: #1e4d8c;
  --blue-600: #1d5fa8;
  --blue-500: #2272c3;
  --blue-400: #3b8de0;
  --blue-300: #60a5f5;
  --blue-200: #93c5fd;
  --blue-100: #dbeafe;

  --cyan: #06b6d4;
  --cyan-l: #22d3ee;
  --cyan-xl: #67e8f9;

  --t1: #f0f6ff;
  --t2: #8ba8cc;
  --t3: #3d5a80;
  --t4: #1e3152;

  --glass-bg: rgba(8, 20, 48, 0.65);
  --glass-bg-light: rgba(14, 32, 64, 0.50);
  --glass-border: rgba(59, 141, 224, 0.15);
  --glass-border-l: rgba(96, 165, 245, 0.25);
  --glass-border-xl: rgba(147, 197, 253, 0.35);

  --ok: #10b981;
  --warn: #f59e0b;
  --err: #ef4444;

  --r-xs: 8px;
  --r-sm: 12px;
  --r-md: 18px;
  --r-lg: 24px;
  --r-xl: 32px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; }

html, body, .stApp {
  background: var(--void) !important;
  color: var(--t1) !important;
  font-family: 'DM Sans', sans-serif !important;
}

/* Animated deep-space background */
.stApp::before {
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 50% at 15% 10%, rgba(34, 114, 195, 0.12) 0%, transparent 60%),
    radial-gradient(ellipse 60% 70% at 85% 90%, rgba(6, 182, 212, 0.08) 0%, transparent 55%),
    radial-gradient(ellipse 40% 60% at 50% 50%, rgba(10, 22, 40, 0.95) 0%, transparent 80%);
  pointer-events: none;
  z-index: 0;
  animation: bgBreath 18s ease-in-out infinite alternate;
}

@keyframes bgBreath {
  from { opacity: 0.7; }
  to { opacity: 1; }
}

/* Star field */
.stApp::after {
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    radial-gradient(1px 1px at 20% 30%, rgba(147,197,253,0.4) 0%, transparent 100%),
    radial-gradient(1px 1px at 70% 20%, rgba(147,197,253,0.3) 0%, transparent 100%),
    radial-gradient(1px 1px at 40% 70%, rgba(96,165,245,0.3) 0%, transparent 100%),
    radial-gradient(1px 1px at 90% 50%, rgba(147,197,253,0.2) 0%, transparent 100%),
    radial-gradient(1px 1px at 10% 80%, rgba(96,165,245,0.2) 0%, transparent 100%);
  pointer-events: none;
  z-index: 0;
}

[data-testid="collapsedControl"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }

h1, h2, h3, h4 {
  font-family: 'Syne', sans-serif !important;
  color: var(--t1) !important;
  font-weight: 700;
  letter-spacing: -0.02em;
}
h1 { font-size: 1.75rem !important; }
h2 { font-size: 1.35rem !important; }
h3 { font-size: 1.02rem !important; }

/* ─── LIQUID GLASS BASE ─── */
.lg {
  background: var(--glass-bg);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border: 1px solid var(--glass-border);
  border-radius: var(--r-lg);
  box-shadow:
    0 8px 32px rgba(0,0,0,0.45),
    0 2px 8px rgba(0,0,0,0.3),
    inset 0 1px 0 rgba(147,197,253,0.06),
    inset 0 0 0 1px rgba(59,141,224,0.04);
}

.lg-sm {
  background: var(--glass-bg);
  backdrop-filter: blur(20px) saturate(160%);
  -webkit-backdrop-filter: blur(20px) saturate(160%);
  border: 1px solid var(--glass-border);
  border-radius: var(--r-md);
  box-shadow: 0 4px 16px rgba(0,0,0,0.35), inset 0 1px 0 rgba(147,197,253,0.05);
}

/* ─── CARDS ─── */
.card {
  background: var(--glass-bg);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border: 1px solid var(--glass-border);
  border-radius: var(--r-lg);
  padding: 1.4rem 1.6rem;
  margin-bottom: 1rem;
  box-shadow:
    0 8px 32px rgba(0,0,0,0.4),
    inset 0 1px 0 rgba(147,197,253,0.07);
  animation: slideUp 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  transition: border-color 0.25s, box-shadow 0.25s, transform 0.2s;
  position: relative;
  overflow: hidden;
}

.card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(96,165,245,0.3), transparent);
}

.card:hover {
  border-color: var(--glass-border-l);
  box-shadow: 0 12px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(59,141,224,0.1), inset 0 1px 0 rgba(147,197,253,0.09);
  transform: translateY(-1px);
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ─── LIQUID GLASS BUTTONS ─── */
.stButton > button {
  background: linear-gradient(135deg,
    rgba(22, 75, 156, 0.55) 0%,
    rgba(14, 52, 114, 0.45) 40%,
    rgba(6, 182, 212, 0.20) 100%
  ) !important;
  backdrop-filter: blur(20px) saturate(200%) !important;
  -webkit-backdrop-filter: blur(20px) saturate(200%) !important;
  border: 1px solid rgba(96, 165, 245, 0.22) !important;
  border-radius: var(--r-sm) !important;
  color: var(--t1) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 500 !important;
  font-size: 0.84rem !important;
  letter-spacing: 0.01em !important;
  padding: 0.55rem 1rem !important;
  position: relative !important;
  overflow: hidden !important;
  transition: all 0.28s cubic-bezier(0.4, 0, 0.2, 1) !important;
  box-shadow:
    0 4px 16px rgba(0, 0, 0, 0.35),
    0 1px 0 rgba(147,197,253,0.12) inset,
    0 -1px 0 rgba(0,0,0,0.25) inset !important;
}

.stButton > button::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 50%;
  background: linear-gradient(180deg, rgba(147,197,253,0.08) 0%, transparent 100%);
  border-radius: var(--r-sm) var(--r-sm) 0 0;
  pointer-events: none;
}

.stButton > button:hover {
  background: linear-gradient(135deg,
    rgba(34, 114, 195, 0.70) 0%,
    rgba(22, 75, 156, 0.58) 40%,
    rgba(6, 182, 212, 0.30) 100%
  ) !important;
  border-color: rgba(147, 197, 253, 0.38) !important;
  box-shadow:
    0 8px 28px rgba(34, 114, 195, 0.30),
    0 0 0 1px rgba(96,165,245,0.15),
    inset 0 1px 0 rgba(147,197,253,0.16) !important;
  transform: translateY(-1px) !important;
}

.stButton > button:active {
  transform: translateY(0) scale(0.98) !important;
}

/* ─── INPUTS ─── */
.stTextInput input, .stTextArea textarea {
  background: rgba(5, 12, 26, 0.70) !important;
  border: 1px solid var(--glass-border) !important;
  border-radius: var(--r-sm) !important;
  color: var(--t1) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.88rem !important;
  backdrop-filter: blur(12px) !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}

.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: rgba(96, 165, 245, 0.45) !important;
  box-shadow: 0 0 0 3px rgba(34, 114, 195, 0.12), 0 0 20px rgba(34, 114, 195, 0.08) !important;
}

.stTextInput label, .stTextArea label, .stSelectbox label, .stFileUploader label {
  color: var(--t3) !important;
  font-size: 0.78rem !important;
  font-family: 'DM Sans', sans-serif !important;
  letter-spacing: 0.04em !important;
  text-transform: uppercase !important;
}

/* ─── AVATAR ─── */
.av {
  border-radius: 50%;
  background: linear-gradient(135deg, var(--blue-800), var(--blue-500));
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Syne', sans-serif;
  font-weight: 700;
  color: white;
  border: 1.5px solid rgba(96, 165, 245, 0.25);
  flex-shrink: 0;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.4);
}

.av img { width: 100%; height: 100%; object-fit: cover; border-radius: 50%; }

/* ─── TAGS ─── */
.tag {
  display: inline-block;
  background: rgba(34, 114, 195, 0.12);
  border: 1px solid rgba(59, 141, 224, 0.20);
  border-radius: 20px;
  padding: 2px 10px;
  font-size: 0.70rem;
  color: var(--blue-300);
  margin: 2px;
  font-weight: 500;
  letter-spacing: 0.01em;
}

.badge-on {
  display: inline-block;
  background: rgba(245, 158, 11, 0.10);
  border: 1px solid rgba(245, 158, 11, 0.28);
  border-radius: 20px;
  padding: 2px 10px;
  font-size: 0.70rem;
  font-weight: 600;
  color: #f59e0b;
}

.badge-pub {
  display: inline-block;
  background: rgba(16, 185, 129, 0.10);
  border: 1px solid rgba(16, 185, 129, 0.28);
  border-radius: 20px;
  padding: 2px 10px;
  font-size: 0.70rem;
  font-weight: 600;
  color: #10b981;
}

.badge-rec {
  display: inline-block;
  background: rgba(6, 182, 212, 0.12);
  border: 1px solid rgba(6, 182, 212, 0.25);
  border-radius: 20px;
  padding: 2px 10px;
  font-size: 0.69rem;
  font-weight: 600;
  color: var(--cyan-l);
}

/* ─── METRIC BOXES ─── */
.mbox {
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  border: 1px solid var(--glass-border);
  border-radius: var(--r-md);
  padding: 1.1rem;
  text-align: center;
  animation: slideUp 0.4s ease both;
  box-shadow: 0 4px 16px rgba(0,0,0,0.3), inset 0 1px 0 rgba(147,197,253,0.05);
}
.mval {
  font-family: 'Syne', sans-serif;
  font-size: 2rem;
  font-weight: 800;
  background: linear-gradient(135deg, var(--blue-300), var(--cyan-l));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.mlbl { font-size: 0.72rem; color: var(--t3); margin-top: 4px; letter-spacing: 0.04em; text-transform: uppercase; }

/* ─── SCROLLBAR ─── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--void); }
::-webkit-scrollbar-thumb { background: var(--elevated); border-radius: 3px; }

/* ─── CHAT BUBBLES ─── */
.bme {
  background: linear-gradient(135deg, rgba(34,114,195,0.45), rgba(6,182,212,0.22));
  border: 1px solid rgba(96,165,245,0.20);
  border-radius: 18px 18px 4px 18px;
  padding: 0.65rem 1rem;
  max-width: 72%;
  margin-left: auto;
  margin-bottom: 6px;
  font-size: 0.85rem;
  line-height: 1.55;
  box-shadow: 0 2px 12px rgba(34,114,195,0.2);
}
.bthem {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: 18px 18px 18px 4px;
  padding: 0.65rem 1rem;
  max-width: 72%;
  margin-bottom: 6px;
  font-size: 0.85rem;
  line-height: 1.55;
}

/* ─── TABS ─── */
.stTabs [data-baseweb="tab-list"] {
  background: rgba(5, 12, 26, 0.7) !important;
  backdrop-filter: blur(16px) !important;
  border-radius: var(--r-sm) !important;
  padding: 4px !important;
  gap: 2px !important;
  border: 1px solid var(--glass-border) !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  color: var(--t3) !important;
  border-radius: var(--r-xs) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.82rem !important;
  font-weight: 500 !important;
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, rgba(34,114,195,0.35), rgba(6,182,212,0.18)) !important;
  color: var(--t1) !important;
  border: 1px solid rgba(96,165,245,0.25) !important;
}
.stTabs [data-baseweb="tab-panel"] {
  background: transparent !important;
  padding-top: 1rem !important;
}

/* ─── EXPANDER ─── */
.stExpander {
  background: var(--glass-bg) !important;
  backdrop-filter: blur(16px) !important;
  border: 1px solid var(--glass-border) !important;
  border-radius: var(--r-md) !important;
}
.stExpander summary { color: var(--t2) !important; font-size: 0.85rem !important; }

/* ─── SELECTBOX ─── */
.stSelectbox [data-baseweb="select"] {
  background: rgba(5, 12, 26, 0.70) !important;
  border: 1px solid var(--glass-border) !important;
  border-radius: var(--r-sm) !important;
}

/* ─── FILE UPLOADER ─── */
.stFileUploader section {
  background: rgba(5, 12, 26, 0.55) !important;
  border: 1.5px dashed rgba(59, 141, 224, 0.25) !important;
  border-radius: var(--r-md) !important;
}

/* ─── ALERTS ─── */
.stAlert {
  background: var(--glass-bg) !important;
  border: 1px solid var(--glass-border) !important;
  border-radius: var(--r-md) !important;
}

/* ─── PROGRESS ─── */
.stProgress > div > div {
  background: linear-gradient(90deg, var(--blue-500), var(--cyan)) !important;
  border-radius: 4px !important;
}

/* ─── MISC ─── */
hr { border-color: var(--glass-border) !important; }
label { color: var(--t2) !important; }
.stCheckbox label, .stRadio label { color: var(--t1) !important; }
.block-container {
  padding-top: 0 !important;
  padding-bottom: 3rem !important;
  max-width: 1360px !important;
}

/* ─── TOP NAV (functional buttons invisible overlay) ─── */
.toprow .stButton > button {
  background: transparent !important;
  border: none !important;
  color: var(--t3) !important;
  font-size: 0 !important;
  padding: 0.4rem !important;
  box-shadow: none !important;
  border-radius: var(--r-xs) !important;
  width: 100% !important;
  height: 52px !important;
  opacity: 0 !important;
  position: absolute !important;
  top: 0 !important; left: 0 !important;
  cursor: pointer !important;
  z-index: 10 !important;
}

/* ─── PULSE DOT ─── */
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.85); }
}
.don { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--ok); animation: pulse 2s infinite; margin-right: 5px; }
.doff { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--t3); margin-right: 5px; }

/* ─── ANALYSIS BOX ─── */
.abox {
  background: rgba(10, 26, 53, 0.7);
  backdrop-filter: blur(16px);
  border: 1px solid var(--glass-border-l);
  border-radius: var(--r-md);
  padding: 1.1rem;
  margin-bottom: 0.9rem;
}

/* ─── PROFILE HERO ─── */
.prof-hero {
  background: var(--glass-bg);
  backdrop-filter: blur(24px);
  border: 1px solid var(--glass-border);
  border-radius: var(--r-xl);
  padding: 2rem;
  display: flex;
  gap: 1.5rem;
  align-items: flex-start;
  margin-bottom: 1.2rem;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(147,197,253,0.06);
  position: relative;
  overflow: hidden;
}
.prof-hero::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(96,165,245,0.4), transparent);
}

.prof-photo {
  width: 92px; height: 92px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--blue-900), var(--blue-600));
  border: 2px solid rgba(96, 165, 245, 0.30);
  object-fit: cover;
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 2rem; font-weight: 700; color: white;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(34, 114, 195, 0.3);
}
.prof-photo img { width: 100%; height: 100%; object-fit: cover; border-radius: 50%; }

/* ─── SEARCH CARD ─── */
.scard {
  background: var(--glass-bg);
  backdrop-filter: blur(16px);
  border: 1px solid var(--glass-border);
  border-radius: var(--r-md);
  padding: 1.1rem 1.3rem;
  margin-bottom: 0.7rem;
  transition: border-color 0.2s, transform 0.2s;
  position: relative;
  overflow: hidden;
}
.scard:hover {
  border-color: var(--glass-border-l);
  transform: translateY(-1px);
}

/* ─── POST CLICK OVERLAY ─── */
.post-author-overlay {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 72px;
  cursor: pointer;
  z-index: 2;
  border-radius: var(--r-lg) var(--r-lg) 0 0;
}
.post-author-overlay:hover { background: rgba(59,141,224,0.06); }

/* ─── GLOW ACCENTS ─── */
.glow-blue {
  box-shadow: 0 0 20px rgba(34, 114, 195, 0.25), 0 0 40px rgba(34, 114, 195, 0.10);
}

/* ─── SIDEBAR RESEARCHER ITEM ─── */
.researcher-item {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--r-md);
  padding: 9px 12px;
  margin-bottom: 5px;
  transition: border-color 0.2s, background 0.2s;
  cursor: pointer;
}
.researcher-item:hover {
  border-color: var(--glass-border-l);
  background: rgba(14, 32, 64, 0.75);
}

div[data-testid="stHorizontalBlock"] { gap: 3px !important; }

.pw { animation: fadeIn 0.3s ease both; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
</style>
""", unsafe_allow_html=True)

# ─── HELPERS ──────────────────────────────
def avh(initials, sz=40, photo_b64=None):
    fs = max(sz // 3, 9)
    if photo_b64:
        return f'<div class="av" style="width:{sz}px;height:{sz}px;"><img src="{photo_b64}"/></div>'
    return f'<div class="av" style="width:{sz}px;height:{sz}px;font-size:{fs}px;">{initials}</div>'

def tags_html(tags):
    return ' '.join(f'<span class="tag">{t}</span>' for t in (tags or []))

def badge(s):
    cls = "badge-pub" if s == "Publicado" else "badge-on"
    return f'<span class="{cls}">{s}</span>'

def guser():
    if not isinstance(st.session_state.users, dict):
        st.session_state.users = {}
    return st.session_state.users.get(st.session_state.current_user, {})

def get_photo(email):
    if not isinstance(st.session_state.users, dict): return None
    return st.session_state.users.get(email, {}).get("photo_b64")

# ─── IMAGE ANALYSIS ──────────────────────
def analyze_image(uploaded_file):
    try:
        uploaded_file.seek(0)
        img = PILImage.open(uploaded_file).convert("RGB")
        orig = img.size
        small = img.resize((256, 256))
        arr = np.array(small, dtype=np.float32)
        r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
        mr, mg, mb = float(r.mean()), float(g.mean()), float(b.mean())
        brightness = (mr + mg + mb) / 3
        saturation = float(np.std(arr))
        gray = arr.mean(axis=2)
        gx = np.diff(gray, axis=1); gy = np.diff(gray, axis=0)
        edge = float(np.sqrt(np.mean(gx**2) + np.mean(gy**2)))
        contrast = float(gray.std())
        h, w = gray.shape
        qv = [gray[:h//2,:w//2].var(), gray[:h//2,w//2:].var(), gray[h//2:,:w//2].var(), gray[h//2:,w//2:].var()]
        sym = 1.0 - (max(qv) - min(qv)) / (max(qv) + 1e-5)
        hist = np.histogram(gray, bins=64, range=(0,255))[0]
        hn = hist / hist.sum(); hn = hn[hn > 0]
        entropy = float(-np.sum(hn * np.log2(hn)))
        flat = arr.reshape(-1, 3); rounded = (flat // 32 * 32).astype(int)
        uniq, counts = np.unique(rounded, axis=0, return_counts=True)
        top_idx = np.argsort(-counts)[:6]
        palette = [tuple(int(x) for x in uniq[i]) for i in top_idx]
        skin_mask = (r > 95) & (g > 40) & (b > 20) & (r > g) & (r > b) & ((r-g) > 15)
        skin_pct = float(skin_mask.mean())
        warm = mr > mb + 15
        dom = max({"Vermelho": mr, "Verde": mg, "Azul": mb}.items(), key=lambda x: x[1])[0]
        if skin_pct > 0.15: cat = "Imagem de Organismo / Tecido Biológico"; struct = f"Alta presença de tonalidade orgânica ({skin_pct*100:.0f}%). Possível histologia."
        elif edge > 40 and entropy > 5.5: cat = "Estrutura Biológica / Molecular — Alta Complexidade"; struct = f"Densidade de bordas alta (I={edge:.1f}) + entropia elevada ({entropy:.2f} bits). Microscopia."
        elif sym > 0.82 and edge < 30: cat = "Padrão Geométrico / Cristalográfico"; struct = f"Alta simetria (score={sym:.3f}). Padrão de cristalização ou difração."
        elif contrast < 18: cat = "Amostra Homogênea / Baixo Contraste"; struct = f"Contraste muito baixo (σ={contrast:.1f}). Amostra uniforme."
        elif mr > 185 and mg < 110 and mb < 110: cat = "Coloração Histológica — H&E"; struct = f"Canal vermelho dominante (R={mr:.0f},G={mg:.0f},B={mb:.0f}). H&E."
        elif mg > 165 and mr < 130: cat = "Fluorescência — Canal Verde (GFP/FITC)"; struct = f"Verde dominante (G={mg:.0f}). GFP, FITC."
        elif mb > 165 and mr < 130: cat = "Fluorescência — Canal Azul (DAPI/Hoechst)"; struct = f"Azul dominante (B={mb:.0f}). DAPI, Hoechst."
        elif entropy > 6.0: cat = "Imagem Multispectral / Alta Complexidade"; struct = f"Entropia muito alta ({entropy:.2f} bits). Multiespectral."
        elif edge > 25: cat = "Gráfico / Diagrama Científico"; struct = f"Bordas bem definidas (I={edge:.1f}). Gráfico ou esquema."
        else: cat = "Imagem Científica Geral"; struct = f"Padrão misto. Temperatura {'quente' if warm else 'fria'}, brilho {brightness:.0f}/255."
        conf = min(96, 55 + edge/2 + entropy*3 + sym*5)
        return {"category": cat, "structure": struct, "color": {"dominant": dom, "brightness": round(brightness,1), "saturation": round(saturation,1), "mean_rgb": (round(mr,1), round(mg,1), round(mb,1)), "warm": warm}, "texture": {"edge_intensity": round(edge,2), "contrast": round(contrast,2), "entropy": round(entropy,3), "complexity": "Alta" if entropy>5.5 else ("Média" if entropy>4 else "Baixa")}, "shape": {"symmetry_score": round(sym,3), "symmetry_level": "Alta" if sym>0.78 else ("Média" if sym>0.52 else "Baixa")}, "palette": palette, "confidence": round(conf,1), "size": orig, "skin_pct": round(skin_pct*100,1)}
    except:
        return None

# ─── DOCUMENT ANALYSIS (real content from uploaded files) ─────────────────
def analyze_folder_documents(folder_name):
    """Analyzes documents in a folder based on their names and extracts relevant tags & summary."""
    folder_data = st.session_state.folders.get(folder_name, {})
    files = folder_data.get("files", []) if isinstance(folder_data, dict) else folder_data

    if not files:
        return None

    all_tags = set()
    file_analyses = []

    keyword_map = {
        "genomica": ["Genômica", "DNA", "Sequenciamento"], "dna": ["Genômica", "DNA"],
        "rna": ["Genômica", "RNA", "Transcrição"], "crispr": ["CRISPR", "Edição Gênica"],
        "proteina": ["Proteômica", "Proteínas"], "celula": ["Biologia Celular", "Citologia"],
        "neurociencia": ["Neurociência", "Neurologia"], "cerebro": ["Neurociência", "Cognição"],
        "sono": ["Sono", "Neurociência"], "memoria": ["Memória", "Cognição"],
        "ia": ["Inteligência Artificial", "Machine Learning"], "ml": ["Machine Learning", "IA"],
        "deep": ["Deep Learning", "Redes Neurais"], "neural": ["Redes Neurais", "Deep Learning"],
        "quantum": ["Computação Quântica", "Física"], "fisica": ["Física", "Ciências Exatas"],
        "quimica": ["Química", "Ciências Exatas"], "molecula": ["Química", "Bioquímica"],
        "astronomia": ["Astronomia", "Astrofísica"], "estrela": ["Astronomia", "Astrofísica"],
        "cosmo": ["Cosmologia", "Astrofísica"], "galaxia": ["Astrofísica", "Cosmologia"],
        "psicologia": ["Psicologia", "Ciências Humanas"], "comportamento": ["Psicologia", "Comportamento"],
        "cogni": ["Cognição", "Psicologia"], "biologia": ["Biologia", "Ciências da Vida"],
        "ecologia": ["Ecologia", "Meio Ambiente"], "clima": ["Clima", "Meio Ambiente"],
        "medicina": ["Medicina", "Saúde"], "clinica": ["Clínica Médica", "Medicina"],
        "farmaco": ["Farmacologia", "Medicina"], "cancer": ["Oncologia", "Medicina"],
        "engenharia": ["Engenharia", "Tecnologia"], "robotica": ["Robótica", "Engenharia"],
        "materiais": ["Ciência dos Materiais", "Engenharia"], "computacao": ["Computação", "TI"],
        "algoritmo": ["Algoritmos", "Computação"], "dados": ["Ciência de Dados", "Analytics"],
        "estatistica": ["Estatística", "Matemática"], "matematica": ["Matemática"],
        "graph": ["Análise de Grafos", "Redes"], "rede": ["Redes", "Sistemas Complexos"],
        "review": ["Revisão Sistemática", "Meta-análise"], "survey": ["Revisão de Literatura"],
        "artigo": ["Publicação Científica"], "paper": ["Publicação Científica"],
        "tese": ["Tese", "Dissertação"], "relatorio": ["Relatório de Pesquisa"],
        "protocolo": ["Metodologia", "Protocolo Experimental"], "metodologia": ["Metodologia"],
        "resultados": ["Resultados Experimentais"], "analise": ["Análise de Dados"],
    }

    for fname in files:
        fname_lower = fname.lower().replace("_", " ").replace("-", " ")
        file_tags = set()
        for kw, ktags in keyword_map.items():
            if kw in fname_lower:
                file_tags.update(ktags)
        if not file_tags:
            ext = fname.split(".")[-1].lower() if "." in fname else ""
            if ext in ["pdf"]: file_tags.add("Documento PDF")
            elif ext in ["docx", "doc"]: file_tags.add("Documento Word")
            elif ext in ["xlsx", "csv"]: file_tags.add("Dados Tabulares")
            elif ext in ["png", "jpg", "jpeg", "tiff"]: file_tags.add("Imagem Científica")
            else: file_tags.add("Pesquisa Geral")
        all_tags.update(file_tags)
        file_analyses.append({"file": fname, "tags": list(file_tags)})

    # Build research summary based on detected areas
    areas = list(all_tags)[:5]
    summary = f"Pasta '{folder_name}' contém {len(files)} documento(s). "
    summary += f"Áreas identificadas: {', '.join(areas)}. "
    summary += f"Análise gerada automaticamente com base nos nomes e tipos de arquivo."

    return {
        "tags": list(all_tags)[:10],
        "summary": summary,
        "file_analyses": file_analyses,
        "total_files": len(files)
    }

# ─── INTERNET SEARCH ─────────────────────
def search_semantic_scholar(query, limit=8):
    results = []
    try:
        r = requests.get("https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query": query, "limit": limit, "fields": "title,authors,year,abstract,venue,externalIds,openAccessPdf,citationCount"},
            timeout=9)
        if r.status_code == 200:
            for p in r.json().get("data", []):
                ext_ids = p.get("externalIds", {}) or {}
                doi = ext_ids.get("DOI", "")
                arxiv = ext_ids.get("ArXiv", "")
                pdf = p.get("openAccessPdf") or {}
                link = pdf.get("url", "") or (f"https://arxiv.org/abs/{arxiv}" if arxiv else (f"https://doi.org/{doi}" if doi else ""))
                authors_list = p.get("authors", []) or []
                authors = ", ".join(a.get("name", "") for a in authors_list[:3])
                if len(authors_list) > 3: authors += " et al."
                abstract = (p.get("abstract", "") or "Abstract não disponível.")
                abstract = abstract[:300] + ("…" if len(abstract) > 300 else "")
                results.append({"title": p.get("title", "Sem título"), "authors": authors or "—", "year": p.get("year", "?"), "source": p.get("venue", "") or "Semantic Scholar", "doi": doi or arxiv or "—", "abstract": abstract, "url": link, "citations": p.get("citationCount", 0), "origin": "semantic", "tags": []})
    except:
        pass
    return results

def search_crossref(query, limit=5):
    results = []
    try:
        r = requests.get("https://api.crossref.org/works",
            params={"query": query, "rows": limit, "select": "title,author,issued,abstract,DOI,container-title,is-referenced-by-count", "mailto": "nebula@example.com"},
            timeout=9)
        if r.status_code == 200:
            for p in r.json().get("message", {}).get("items", []):
                title = (p.get("title") or ["Sem título"])[0]
                ars = p.get("author", []) or []
                authors = ", ".join(f'{a.get("given","").split()[0] if a.get("given") else ""} {a.get("family","")}'.strip() for a in ars[:3])
                if len(ars) > 3: authors += " et al."
                year = (p.get("issued", {}).get("date-parts") or [[None]])[0][0]
                doi = p.get("DOI", "")
                journal = (p.get("container-title") or [""])[0]
                abstract_raw = p.get("abstract", "") or "Abstract não disponível."
                abstract = re.sub(r'<[^>]+>', '', abstract_raw)[:300] + ("…" if len(abstract_raw) > 300 else "")
                results.append({"title": title, "authors": authors or "—", "year": year or "?", "source": journal or "CrossRef", "doi": doi, "abstract": abstract, "url": f"https://doi.org/{doi}" if doi else "", "citations": p.get("is-referenced-by-count", 0), "origin": "crossref", "tags": []})
    except:
        pass
    return results

# ─── RECOMMENDATION ENGINE ──────────────
def record(tags, w=1.0):
    email = st.session_state.get("current_user")
    if not email or not tags: return
    prefs = st.session_state.user_prefs.setdefault(email, defaultdict(float))
    for t in tags:
        prefs[t.lower()] += w

def get_recs(email, n=2):
    prefs = st.session_state.user_prefs.get(email, {})
    if not prefs: return []
    def score(p):
        return (sum(prefs.get(t.lower(), 0) for t in p.get("tags", [])) +
                sum(prefs.get(t.lower(), 0) * .5 for t in p.get("connections", [])))
    scored = [(score(p), p) for p in st.session_state.feed_posts if email not in p.get("liked_by", [])]
    scored.sort(key=lambda x: -x[0])
    return [p for s, p in scored if s > 0][:n]

def area_to_tags(area):
    a = (area or "").lower()
    m = {"ia": ["machine learning","deep learning","LLM"], "inteligência artificial": ["machine learning","LLM"], "machine learning": ["deep learning","redes neurais","otimização"], "neurociência": ["sono","memória","plasticidade"], "biologia": ["célula","genômica","CRISPR"], "física": ["quantum","astrofísica","cosmologia"], "química": ["síntese","catálise"], "medicina": ["clínica","diagnóstico","terapia"], "astronomia": ["astrofísica","cosmologia","galáxia"], "computação": ["algoritmo","criptografia","redes"], "matemática": ["álgebra","topologia","estatística"], "psicologia": ["cognição","comportamento"], "ecologia": ["biodiversidade","clima"], "genômica": ["DNA","CRISPR","gene"], "engenharia": ["robótica","materiais","sistemas"], "astrofísica": ["cosmologia","galáxia","matéria escura"]}
    for k, v in m.items():
        if k in a: return v
    return [w.strip() for w in a.replace(",", " ").split() if len(w) > 3][:5]

# ─── SEED DATA ──────────────────────────
SEED_POSTS = [
    {"id":1,"author":"Carlos Mendez","author_email":"carlos@nebula.ai","avatar":"CM","area":"Neurociência","title":"Efeitos da Privação de Sono na Plasticidade Sináptica","abstract":"Investigamos como 24h de privação de sono afetam espinhas dendríticas em ratos Wistar, com redução de 34% na plasticidade hipocampal. Nossos dados sugerem janela crítica nas primeiras 6h de recuperação do sono.","tags":["neurociência","sono","memória","hipocampo"],"likes":47,"comments":[{"user":"Maria Silva","text":"Excelente metodologia!"},{"user":"João Lima","text":"Quais os critérios de exclusão?"}],"status":"Em andamento","date":"2026-02-10","liked_by":[],"saved_by":[],"connections":["sono","memória","hipocampo"]},
    {"id":2,"author":"Luana Freitas","author_email":"luana@nebula.ai","avatar":"LF","area":"Biomedicina","title":"CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras","abstract":"Desenvolvemos vetor AAV9 modificado para entrega precisa de CRISPR no gene DMD, com eficiência de 78% em modelos murinos mdx. Publicação em Cell prevista para Q2 2026.","tags":["CRISPR","gene terapia","músculo","AAV9"],"likes":93,"comments":[{"user":"Ana","text":"Quais os próximos passos?"}],"status":"Publicado","date":"2026-01-28","liked_by":[],"saved_by":[],"connections":["genômica","distrofia"]},
    {"id":3,"author":"Rafael Souza","author_email":"rafael@nebula.ai","avatar":"RS","area":"Computação","title":"Redes Neurais Quântico-Clássicas para Otimização Combinatória","abstract":"Arquitetura híbrida variacional combinando qubits supercondutores com camadas densas para resolver TSP com 40% menos iterações que métodos clássicos.","tags":["quantum ML","otimização","TSP","computação quântica"],"likes":201,"comments":[],"status":"Em andamento","date":"2026-02-15","liked_by":[],"saved_by":[],"connections":["computação quântica","machine learning"]},
    {"id":4,"author":"Priya Nair","author_email":"priya@nebula.ai","avatar":"PN","area":"Astrofísica","title":"Detecção de Matéria Escura via Lentes Gravitacionais Fracas","abstract":"Mapeamento de matéria escura com precisão sub-arcminuto usando 100M de galáxias do DES Y3. Tensão com ΛCDM em escalas < 1 Mpc.","tags":["astrofísica","matéria escura","cosmologia"],"likes":312,"comments":[],"status":"Publicado","date":"2026-02-01","liked_by":[],"saved_by":[],"connections":["cosmologia","lentes gravitacionais"]},
    {"id":5,"author":"João Lima","author_email":"joao@nebula.ai","avatar":"JL","area":"Psicologia","title":"Viés de Confirmação em Decisões Médicas Assistidas por IA","abstract":"Estudo duplo-cego com 240 médicos revelou que sistemas de IA mal calibrados amplificam vieses cognitivos em 22% dos casos clínicos analisados.","tags":["psicologia","IA","cognição","medicina"],"likes":78,"comments":[],"status":"Publicado","date":"2026-02-08","liked_by":[],"saved_by":[],"connections":["cognição","IA"]},
]

SEED_USERS = {
    "demo@nebula.ai":{"name":"Ana Pesquisadora","password":hp("demo123"),"bio":"Pesquisadora em IA e Ciências Cognitivas | UFMG","area":"Inteligência Artificial","followers":128,"following":47,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "carlos@nebula.ai":{"name":"Carlos Mendez","password":hp("nebula123"),"bio":"Neurocientista | UFMG | Plasticidade sináptica e sono","area":"Neurociência","followers":210,"following":45,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "luana@nebula.ai":{"name":"Luana Freitas","password":hp("nebula123"),"bio":"Biomédica | FIOCRUZ | CRISPR e terapia gênica para doenças raras","area":"Biomedicina","followers":178,"following":62,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "rafael@nebula.ai":{"name":"Rafael Souza","password":hp("nebula123"),"bio":"Computação Quântica | USP | Algoritmos híbridos quantum-clássicos","area":"Computação","followers":340,"following":88,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "priya@nebula.ai":{"name":"Priya Nair","password":hp("nebula123"),"bio":"Astrofísica | MIT | Dark matter survey & gravitational lensing","area":"Astrofísica","followers":520,"following":31,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "joao@nebula.ai":{"name":"João Lima","password":hp("nebula123"),"bio":"Psicólogo Cognitivo | UNICAMP | IA e vieses em decisões clínicas","area":"Psicologia","followers":95,"following":120,"verified":True,"2fa_enabled":False,"photo_b64":None},
}

CHAT_INIT = {
    "carlos@nebula.ai": [{"from":"carlos@nebula.ai","text":"Oi! Vi seu comentário na minha pesquisa sobre sono.","time":"09:14"},{"from":"me","text":"Achei muito interessante a metodologia!","time":"09:16"},{"from":"carlos@nebula.ai","text":"Obrigado! Podemos colaborar?","time":"09:17"}],
    "luana@nebula.ai": [{"from":"luana@nebula.ai","text":"Podemos colaborar no próximo semestre.","time":"ontem"}],
    "rafael@nebula.ai": [{"from":"rafael@nebula.ai","text":"Compartilhei o repositório do código quântico.","time":"08:30"}],
}

KNOWLEDGE_NODES_DEFAULT = [
    {"id":"IA","type":"topic","x":.50,"y":.85,"z":.50,"connections":["Machine Learning","Redes Neurais"],"color":"#2272c3","size":28},
    {"id":"Machine Learning","type":"topic","x":.20,"y":.65,"z":.40,"connections":["Deep Learning","Otimização"],"color":"#1a3a6b","size":22},
    {"id":"Neurociência","type":"topic","x":.80,"y":.65,"z":.60,"connections":["Memória","Sono"],"color":"#3b8de0","size":26},
    {"id":"Genômica","type":"topic","x":.50,"y":.45,"z":.30,"connections":["CRISPR","Proteômica"],"color":"#06b6d4","size":24},
    {"id":"Computação Quântica","type":"topic","x":.15,"y":.35,"z":.70,"connections":["Otimização","Machine Learning"],"color":"#8b5cf6","size":23},
    {"id":"Astrofísica","type":"topic","x":.85,"y":.35,"z":.50,"connections":["Cosmologia","Matéria Escura"],"color":"#ec4899","size":22},
    {"id":"Psicologia","type":"topic","x":.50,"y":.15,"z":.60,"connections":["Cognição","Comportamento"],"color":"#f59e0b","size":20},
    {"id":"Memória","type":"topic","x":.75,"y":.50,"z":.80,"connections":[],"color":"#60a5f5","size":14},
    {"id":"Sono","type":"topic","x":.88,"y":.55,"z":.30,"connections":[],"color":"#60a5f5","size":13},
    {"id":"Otimização","type":"topic","x":.25,"y":.45,"z":.60,"connections":[],"color":"#34d399","size":15},
    {"id":"CRISPR","type":"topic","x":.60,"y":.30,"z":.20,"connections":[],"color":"#22d3ee","size":14},
    {"id":"Deep Learning","type":"topic","x":.10,"y":.55,"z":.50,"connections":[],"color":"#818cf8","size":14},
    {"id":"Cosmologia","type":"topic","x":.92,"y":.22,"z":.70,"connections":[],"color":"#f472b6","size":13},
    {"id":"Cognição","type":"topic","x":.62,"y":.08,"z":.40,"connections":[],"color":"#fbbf24","size":13},
]

# ─── SESSION INIT ────────────────────────
def init():
    if "initialized" in st.session_state: return
    st.session_state.initialized = True
    disk = load_db()
    disk_users = disk.get("users", {})
    if not isinstance(disk_users, dict): disk_users = {}
    st.session_state.setdefault("users", {**SEED_USERS, **disk_users})
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("current_user", None)
    st.session_state.setdefault("page", "login")
    st.session_state.setdefault("profile_view", None)
    disk_prefs = disk.get("user_prefs", {})
    st.session_state.setdefault("user_prefs", {k: defaultdict(float, v) for k, v in disk_prefs.items()})
    st.session_state.setdefault("pending_verify", None)
    st.session_state.setdefault("pending_2fa", None)
    st.session_state.setdefault("feed_posts", disk.get("feed_posts", [dict(p) for p in SEED_POSTS]))
    st.session_state.setdefault("folders", disk.get("folders", {}))
    st.session_state.setdefault("chat_contacts", list(SEED_USERS.keys()))
    st.session_state.setdefault("chat_messages", {k: list(v) for k, v in CHAT_INIT.items()})
    st.session_state.setdefault("active_chat", None)
    disk_nodes = disk.get("knowledge_nodes", [dict(n) for n in KNOWLEDGE_NODES_DEFAULT])
    if not isinstance(disk_nodes, list): disk_nodes = [dict(n) for n in KNOWLEDGE_NODES_DEFAULT]
    st.session_state.setdefault("knowledge_nodes", disk_nodes)
    st.session_state.setdefault("followed", ["carlos@nebula.ai", "luana@nebula.ai"])
    st.session_state.setdefault("notifications", ["Carlos Mendez curtiu sua pesquisa", "Nova conexão: IA ↔ Computação Quântica", "Luana Freitas comentou em um artigo que você segue"])
    st.session_state.setdefault("stats_data", {"views":[12,34,28,67,89,110,95,134,160,178,201,230],"citations":[0,1,1,2,3,4,4,6,7,8,10,12],"months":["Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez","Jan","Fev"],"h_index":4,"fator_impacto":3.8,"aceitacao":94,"notes":""})
    st.session_state.setdefault("scholar_cache", {})

init()

# ─── AUTH PAGES ─────────────────────────
def page_login():
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-bottom:2.5rem;">
          <div style="font-family:'Syne',sans-serif;font-size:3rem;font-weight:800;background:linear-gradient(135deg,#93c5fd,#22d3ee,#60a5f5);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:-0.03em;">🔬 Nebula</div>
          <div style="color:var(--t3);font-size:.72rem;letter-spacing:.18em;text-transform:uppercase;margin-top:.5rem;font-family:'DM Sans',sans-serif;">Rede do Conhecimento Científico</div>
        </div>
        """, unsafe_allow_html=True)
        tab_in, tab_up = st.tabs(["  Entrar  ", "  Criar conta  "])
        with tab_in:
            email = st.text_input("E-mail", placeholder="seu@email.com", key="li_e")
            pw = st.text_input("Senha", placeholder="••••••••", type="password", key="li_p")
            if st.button("Entrar →", use_container_width=True, key="btn_li"):
                users = st.session_state.users if isinstance(st.session_state.users, dict) else {}
                u = users.get(email)
                if not u: st.error("E-mail não encontrado.")
                elif u["password"] != hp(pw): st.error("Senha incorreta.")
                elif not u.get("verified", True): st.warning("Confirme seu e-mail primeiro.")
                elif u.get("2fa_enabled"):
                    c = code6()
                    st.session_state.pending_2fa = {"email": email, "code": c}
                    st.session_state.page = "2fa"; st.rerun()
                else:
                    st.session_state.logged_in = True; st.session_state.current_user = email
                    record(area_to_tags(u.get("area", "")), 1.0)
                    st.session_state.page = "feed"; st.rerun()
            st.markdown('<div style="text-align:center;color:var(--t3);font-size:.72rem;margin-top:.6rem;">Demo: demo@nebula.ai / demo123</div>', unsafe_allow_html=True)
        with tab_up:
            n_name = st.text_input("Nome completo", placeholder="Dr. Maria Silva", key="su_n")
            n_email = st.text_input("E-mail", placeholder="seu@email.com", key="su_e")
            n_area = st.text_input("Área de pesquisa", placeholder="Ex: Neurociência, IA", key="su_a")
            n_pw = st.text_input("Senha", placeholder="Mínimo 6 caracteres", type="password", key="su_p")
            n_pw2 = st.text_input("Confirmar senha", placeholder="••••••••", type="password", key="su_p2")
            if st.button("Criar conta →", use_container_width=True, key="btn_su"):
                users = st.session_state.users if isinstance(st.session_state.users, dict) else {}
                if not all([n_name, n_email, n_area, n_pw, n_pw2]): st.error("Preencha todos os campos.")
                elif n_pw != n_pw2: st.error("Senhas não coincidem.")
                elif len(n_pw) < 6: st.error("Senha muito curta (mín. 6).")
                elif n_email in users: st.error("E-mail já cadastrado.")
                else:
                    c = code6()
                    st.session_state.pending_verify = {"email": n_email, "name": n_name, "pw": hp(n_pw), "area": n_area, "code": c}
                    st.session_state.page = "verify_email"; st.rerun()

def page_verify_email():
    pv = st.session_state.pending_verify
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card" style="text-align:center;">
          <div style="font-size:2.5rem;margin-bottom:1rem;">📧</div>
          <h2 style="margin-bottom:.5rem;">Verifique seu e-mail</h2>
          <p style="color:var(--t2);font-size:.85rem;">Código enviado para <strong>{pv['email']}</strong></p>
          <div style="background:rgba(34,114,195,.10);border:1px solid rgba(59,141,224,.22);border-radius:14px;padding:16px;margin:1.2rem 0;">
            <div style="font-size:.68rem;color:var(--t3);letter-spacing:.10em;margin-bottom:6px;text-transform:uppercase;">Código (demo)</div>
            <div style="font-family:'Syne',sans-serif;font-size:2.5rem;font-weight:800;letter-spacing:.28em;color:var(--blue-300);">{pv['code']}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        typed = st.text_input("Código de 6 dígitos", max_chars=6, placeholder="000000", key="ev_c")
        if st.button("Verificar e criar conta →", use_container_width=True, key="btn_ev"):
            if typed.strip() == pv["code"]:
                if not isinstance(st.session_state.users, dict): st.session_state.users = {}
                st.session_state.users[pv["email"]] = {"name": pv["name"], "password": pv["pw"], "bio": "", "area": pv["area"], "followers": 0, "following": 0, "verified": True, "2fa_enabled": False, "photo_b64": None}
                save_db()
                st.session_state.pending_verify = None
                st.session_state.logged_in = True; st.session_state.current_user = pv["email"]
                record(area_to_tags(pv["area"]), 2.0)
                st.session_state.page = "feed"; st.rerun()
            else: st.error("Código inválido.")
        if st.button("← Voltar", key="btn_ev_bk"):
            st.session_state.page = "login"; st.rerun()

def page_2fa():
    p2 = st.session_state.pending_2fa
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card" style="text-align:center;">
          <div style="font-size:2.5rem;margin-bottom:1rem;">🔑</div>
          <h2>Verificação 2FA</h2>
          <div style="background:rgba(34,114,195,.10);border:1px solid rgba(59,141,224,.22);border-radius:14px;padding:14px;margin:1rem 0;">
            <div style="font-size:.68rem;color:var(--t3);margin-bottom:6px;text-transform:uppercase;letter-spacing:.08em;">Código (demo)</div>
            <div style="font-family:'Syne',sans-serif;font-size:2.5rem;font-weight:800;letter-spacing:.22em;color:var(--blue-300);">{p2['code']}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        typed = st.text_input("Código", max_chars=6, placeholder="000000", key="fa_c", label_visibility="collapsed")
        if st.button("Verificar →", use_container_width=True, key="btn_fa"):
            if typed.strip() == p2["code"]:
                st.session_state.logged_in = True; st.session_state.current_user = p2["email"]
                st.session_state.pending_2fa = None; st.session_state.page = "feed"; st.rerun()
            else: st.error("Código inválido.")
        if st.button("← Voltar", key="btn_fa_bk"):
            st.session_state.page = "login"; st.rerun()

# ─── TOP NAV ─────────────────────────────
NAV = [
    ("feed", "◈", "Feed"),
    ("search", "⊙", "Artigos"),
    ("knowledge", "⬡", "Conexões"),
    ("folders", "▣", "Pastas"),
    ("analytics", "▤", "Análises"),
    ("img_search", "⊞", "Imagem"),
    ("chat", "◻", "Chat"),
    ("settings", "◎", "Perfil")
]

def render_topnav():
    u = guser()
    name = u.get("name", "?")
    photo = u.get("photo_b64")
    in_ = ini(name)
    cur = st.session_state.page
    notif = len(st.session_state.notifications)

    nav_items = ""
    for k, sym, lbl in NAV:
        active = cur == k
        if active:
            nav_items += f'<span style="font-size:.78rem;color:var(--blue-300);font-weight:600;padding:.36rem .7rem;border-radius:var(--r-xs);background:rgba(34,114,195,.22);border:1px solid rgba(96,165,245,.28);display:inline-flex;align-items:center;gap:5px;white-space:nowrap;">{sym} {lbl}</span>'
        else:
            nav_items += f'<span style="font-size:.78rem;color:var(--t3);font-weight:400;padding:.36rem .7rem;border-radius:var(--r-xs);white-space:nowrap;display:inline-flex;align-items:center;gap:5px;">{sym} {lbl}</span>'

    if photo:
        img_html = f"<img src='{photo}' style='width:100%;height:100%;object-fit:cover;border-radius:50%'/>"
    else:
        img_html = in_

    av_html = f'<div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,var(--blue-800),var(--blue-500));display:flex;align-items:center;justify-content:center;font-size:.75rem;font-weight:700;color:white;border:1.5px solid rgba(96,165,245,.25);overflow:hidden;flex-shrink:0;box-shadow:0 2px 8px rgba(0,0,0,0.4);">{img_html}</div>'
    notif_badge = f'<span style="background:var(--blue-500);color:white;border-radius:10px;padding:1px 7px;font-size:.64rem;font-weight:600;">{notif}</span>' if notif else ""

    st.markdown(f"""
    <div style="position:sticky;top:0;z-index:999;background:rgba(1,4,9,.88);backdrop-filter:blur(28px) saturate(200%);-webkit-backdrop-filter:blur(28px) saturate(200%);border-bottom:1px solid var(--glass-border);padding:0 1.4rem;display:flex;align-items:center;justify-content:space-between;height:56px;margin-bottom:0;">
      <div style="font-family:'Syne',sans-serif;font-size:1.3rem;font-weight:800;background:linear-gradient(135deg,#93c5fd,#22d3ee);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;white-space:nowrap;letter-spacing:-0.02em;">🔬 Nebula</div>
      <div style="display:flex;align-items:center;gap:2px;overflow-x:auto;padding:0 .5rem;scrollbar-width:none;">{nav_items}</div>
      <div style="display:flex;align-items:center;gap:10px;">{notif_badge}{av_html}</div>
    </div>
    """, unsafe_allow_html=True)

    # Functional invisible buttons overlaid on nav
    st.markdown('<div class="toprow" style="position:relative;height:0;overflow:visible;">', unsafe_allow_html=True)
    cols = st.columns([1.5] + [1] * len(NAV) + [1])
    for i, (key, sym, lbl) in enumerate(NAV):
        with cols[i + 1]:
            if st.button(f"{sym} {lbl}", key=f"tnav_{key}", use_container_width=True):
                st.session_state.profile_view = None
                st.session_state.page = key
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("""
    <style>
    .toprow { position: relative; margin-top: -56px; height: 56px; }
    .toprow .stButton > button {
      background: transparent !important;
      border: none !important;
      color: transparent !important;
      font-size: 0 !important;
      box-shadow: none !important;
      border-radius: var(--r-xs) !important;
      width: 100% !important;
      height: 56px !important;
      padding: 0 !important;
      cursor: pointer !important;
    }
    .toprow .stButton > button:hover { background: rgba(59,141,224,.08) !important; }
    .toprow div[data-testid="stHorizontalBlock"] { gap: 2px !important; }
    </style>
    """, unsafe_allow_html=True)

# ─── PROFILE PAGE ───────────────────────
def page_profile(target_email):
    users = st.session_state.users if isinstance(st.session_state.users, dict) else {}
    tu = users.get(target_email, {})
    if not tu:
        st.error("Perfil não encontrado.")
        if st.button("← Voltar"): st.session_state.profile_view = None; st.rerun()
        return
    tname = tu.get("name", "?")
    tin = ini(tname)
    tphoto = tu.get("photo_b64")
    email = st.session_state.current_user
    is_me = email == target_email
    is_fol = target_email in st.session_state.followed

    if st.button("← Voltar", key="back_prof"):
        st.session_state.profile_view = None; st.rerun()

    st.markdown(f"""
    <div class="prof-hero">
      <div class="prof-photo">{("<img src='"+tphoto+"'/>") if tphoto else f'<span style="font-size:2rem;">{tin}</span>'}</div>
      <div style="flex:1;">
        <h1 style="margin-bottom:.25rem;font-size:1.6rem!important;">{tname}</h1>
        <div style="color:var(--blue-300);font-size:.84rem;margin-bottom:.5rem;font-family:'DM Sans',sans-serif;">{tu.get('area','')}</div>
        <div style="color:var(--t2);font-size:.84rem;line-height:1.65;margin-bottom:.9rem;">{tu.get('bio','Sem biografia.')}</div>
        <div style="display:flex;gap:1.8rem;">
          <div><span style="font-weight:700;font-family:'Syne',sans-serif;font-size:1.1rem;">{tu.get('followers',0)}</span><span style="color:var(--t3);font-size:.76rem;"> seguidores</span></div>
          <div><span style="font-weight:700;font-family:'Syne',sans-serif;font-size:1.1rem;">{tu.get('following',0)}</span><span style="color:var(--t3);font-size:.76rem;"> seguindo</span></div>
          <div><span style="font-weight:700;font-family:'Syne',sans-serif;font-size:1.1rem;">{len([p for p in st.session_state.feed_posts if p.get('author_email')==target_email])}</span><span style="color:var(--t3);font-size:.76rem;"> pesquisas</span></div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if not is_me:
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if st.button("✓ Seguindo" if is_fol else "➕ Seguir", key="btn_pf"):
                if is_fol:
                    st.session_state.followed.remove(target_email)
                    tu["followers"] = max(0, tu.get("followers", 0) - 1)
                else:
                    st.session_state.followed.append(target_email)
                    tu["followers"] = tu.get("followers", 0) + 1
                save_db(); st.rerun()
        with c2:
            if st.button("💬 Mensagem", key="btn_pm"):
                if target_email not in st.session_state.chat_messages:
                    st.session_state.chat_messages[target_email] = []
                st.session_state.active_chat = target_email
                st.session_state.page = "chat"; st.session_state.profile_view = None; st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<h2>Pesquisas</h2>', unsafe_allow_html=True)
    user_posts = [p for p in st.session_state.feed_posts if p.get("author_email") == target_email]
    if user_posts:
        for p in user_posts:
            render_post(p, show_profile_link=False)
    else:
        st.markdown('<div class="card" style="text-align:center;padding:2.5rem;color:var(--t3);">Nenhuma pesquisa publicada ainda.</div>', unsafe_allow_html=True)

# ─── SHARE MODAL ────────────────────────
def share_modal(post_id, title):
    t_enc = title[:80].replace(" ", "+").replace("&", "")
    url = f"https://nebula.ai/post/{post_id}"
    st.markdown(f"""
    <div class="card">
      <div style="font-weight:700;margin-bottom:.3rem;font-size:.88rem;font-family:'Syne',sans-serif;">Compartilhar pesquisa</div>
      <div style="color:var(--t2);font-size:.78rem;margin-bottom:1rem;">{title[:60]}{"…" if len(title)>60 else ""}</div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:.5rem;">
        <a href="https://twitter.com/intent/tweet?text={t_enc}&url={url}" target="_blank" style="text-decoration:none;">
          <div style="background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:var(--r-sm);padding:.7rem .4rem;text-align:center;font-size:.72rem;color:var(--t2);">𝕏<br>Twitter/X</div>
        </a>
        <a href="https://www.linkedin.com/sharing/share-offsite/?url={url}" target="_blank" style="text-decoration:none;">
          <div style="background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:var(--r-sm);padding:.7rem .4rem;text-align:center;font-size:.72rem;color:var(--t2);">in<br>LinkedIn</div>
        </a>
        <a href="https://wa.me/?text={t_enc}+{url}" target="_blank" style="text-decoration:none;">
          <div style="background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:var(--r-sm);padding:.7rem .4rem;text-align:center;font-size:.72rem;color:var(--t2);">📱<br>WhatsApp</div>
        </a>
        <a href="mailto:?subject={t_enc}&body={url}" target="_blank" style="text-decoration:none;">
          <div style="background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:var(--r-sm);padding:.7rem .4rem;text-align:center;font-size:.72rem;color:var(--t2);">✉️<br>E-mail</div>
        </a>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.code(url, language=None)

# ─── FEED PAGE ──────────────────────────
def page_feed():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="margin-bottom:.3rem;padding-top:1.2rem;">Feed de Pesquisas</h1>', unsafe_allow_html=True)
    email = st.session_state.current_user
    u = guser()
    col_main, col_side = st.columns([2.2, 0.9])

    with col_main:
        recs = get_recs(email)
        if recs:
            st.markdown('<span class="badge-rec">✦ RECOMENDADO PARA VOCÊ</span><br>', unsafe_allow_html=True)
            for p in recs:
                render_post(p, rec=True)
            st.markdown("<hr>", unsafe_allow_html=True)

        with st.expander("➕ Publicar nova pesquisa"):
            np_t = st.text_input("Título da pesquisa", key="np_t")
            np_ab = st.text_area("Resumo / Abstract", key="np_ab", height=90)
            np_tg = st.text_input("Tags (separadas por vírgula)", key="np_tg")
            np_st = st.selectbox("Status", ["Em andamento", "Publicado", "Concluído"], key="np_st")
            if st.button("🚀 Publicar", key="btn_pub"):
                if np_t and np_ab:
                    nm = u.get("name", "Usuário")
                    tags = [t.strip() for t in np_tg.split(",") if t.strip()]
                    st.session_state.feed_posts.insert(0, {"id": len(st.session_state.feed_posts)+1, "author": nm, "author_email": email, "avatar": ini(nm), "area": u.get("area", ""), "title": np_t, "abstract": np_ab, "tags": tags, "likes": 0, "comments": [], "status": np_st, "date": datetime.now().strftime("%Y-%m-%d"), "liked_by": [], "saved_by": [], "connections": tags[:3]})
                    record(tags, 2.0); save_db()
                    st.success("✓ Publicado com sucesso!"); st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        ff = st.selectbox("Filtrar", ["Todos", "Seguidos", "Salvos"], key="ff", label_visibility="collapsed")
        posts = st.session_state.feed_posts
        if ff == "Seguidos": posts = [p for p in posts if p.get("author_email") in st.session_state.followed]
        elif ff == "Salvos": posts = [p for p in posts if email in p.get("saved_by", [])]
        for p in posts:
            render_post(p)

    with col_side:
        sq = st.text_input("", placeholder="🔍 Pesquisadores…", key="ppl_s", label_visibility="collapsed")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.85rem;margin-bottom:.9rem;letter-spacing:0.02em;">Pesquisadores</div>', unsafe_allow_html=True)
        users = st.session_state.users if isinstance(st.session_state.users, dict) else {}
        shown = 0
        for ue, ud in list(users.items()):
            if ue == email: continue
            uname = ud.get("name", "?")
            if sq and sq.lower() not in uname.lower() and sq.lower() not in ud.get("area", "").lower(): continue
            if shown >= 6: break
            shown += 1
            uin = ini(uname)
            uphoto = ud.get("photo_b64")
            is_fol = ue in st.session_state.followed

            c_r, c_b = st.columns([3, 1])
            with c_r:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;padding:6px 0;">'
                    f'{avh(uin, 28, uphoto)}'
                    f'<div><div style="font-size:.79rem;font-weight:600;line-height:1.2;">{uname}</div>'
                    f'<div style="font-size:.67rem;color:var(--t3);">{ud.get("area","")[:22]}</div></div>'
                    f'</div>', unsafe_allow_html=True)
                if st.button("👤", key=f"vps_{ue}", use_container_width=True):
                    st.session_state.profile_view = ue; st.rerun()
            with c_b:
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                if st.button("✓" if is_fol else "+", key=f"fol_{ue}", use_container_width=True):
                    if is_fol:
                        st.session_state.followed.remove(ue)
                        ud["followers"] = max(0, ud.get("followers", 0) - 1)
                    else:
                        st.session_state.followed.append(ue)
                        ud["followers"] = ud.get("followers", 0) + 1
                    save_db(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.85rem;margin-bottom:.8rem;">Áreas em Alta</div>', unsafe_allow_html=True)
        for area, cnt in [("Quantum ML", 42), ("CRISPR 2026", 38), ("Neuroplasticidade", 31), ("LLMs Científicos", 27)]:
            pct = cnt / 42
            st.markdown(
                f'<div style="margin-bottom:.7rem;">'
                f'<div style="display:flex;justify-content:space-between;font-size:.78rem;margin-bottom:3px;">'
                f'<span style="color:var(--t2);">{area}</span>'
                f'<span style="color:var(--blue-300);font-weight:600;">{cnt}</span>'
                f'</div>'
                f'<div style="height:3px;background:var(--glass-border);border-radius:2px;">'
                f'<div style="height:100%;width:{int(pct*100)}%;background:linear-gradient(90deg,var(--blue-500),var(--cyan));border-radius:2px;"></div>'
                f'</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def render_post(post, rec=False, show_profile_link=True):
    email = st.session_state.current_user
    liked = email in post["liked_by"]
    saved = email in post.get("saved_by", [])
    aemail = post.get("author_email", "")
    aphoto = get_photo(aemail)
    rec_b = '<span class="badge-rec" style="margin-left:6px;">Rec.</span>' if rec else ""
    ain = post.get("avatar", "??")

    # Post card with clickable author area
    st.markdown(f"""
    <div class="card" id="post-{post['id']}">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:.9rem;">
        {avh(ain, 42, aphoto)}
        <div style="flex:1;">
          <div style="font-weight:600;font-size:.90rem;font-family:'Syne',sans-serif;">{post['author']}</div>
          <div style="color:var(--t3);font-size:.71rem;margin-top:2px;">{post['area']} · {post['date']}</div>
        </div>
        {badge(post['status'])}{rec_b}
      </div>
      <h3 style="margin-bottom:.45rem;font-size:1rem;line-height:1.45;font-family:'Syne',sans-serif;">{post['title']}</h3>
      <p style="color:var(--t2);font-size:.84rem;line-height:1.68;margin-bottom:.8rem;">{post['abstract']}</p>
      <div style="margin-bottom:.2rem;">{tags_html(post['tags'])}</div>
    </div>
    """, unsafe_allow_html=True)

    # Action buttons
    c1, c2, c3, c4, c5, _ = st.columns([1, 1, 0.8, 0.8, 1.2, 1])
    with c1:
        if st.button(f"{'❤' if liked else '♡'} {post['likes']}", key=f"lk_{post['id']}"):
            if liked: post["liked_by"].remove(email); post["likes"] -= 1
            else: post["liked_by"].append(email); post["likes"] += 1; record(post["tags"], 1.5)
            save_db(); st.rerun()
    with c2:
        if st.button(f"💬 {len(post['comments'])}", key=f"cm_t_{post['id']}"):
            k = f"sc_{post['id']}"
            st.session_state[k] = not st.session_state.get(k, False); st.rerun()
    with c3:
        if st.button("🔖" if saved else "📌", key=f"sv_{post['id']}"):
            if saved: post["saved_by"].remove(email)
            else: post["saved_by"].append(email)
            save_db(); st.rerun()
    with c4:
        if st.button("↗", key=f"sh_{post['id']}"):
            k = f"sopen_{post['id']}"
            st.session_state[k] = not st.session_state.get(k, False); st.rerun()
    with c5:
        if show_profile_link and aemail:
            if st.button(f"👤 {post['author'].split()[0]}", key=f"vpa_{post['id']}"):
                st.session_state.profile_view = aemail; st.rerun()

    if st.session_state.get(f"sopen_{post['id']}", False):
        share_modal(post['id'], post['title'])
    if st.session_state.get(f"sc_{post['id']}", False):
        for c in post["comments"]:
            st.markdown(f'<div style="background:rgba(10,26,53,.8);border-radius:10px;padding:8px 14px;margin:3px 0;font-size:.82rem;border:1px solid var(--glass-border);"><strong style="color:var(--blue-300);">{c["user"]}</strong>: {c["text"]}</div>', unsafe_allow_html=True)
        nc = st.text_input("", key=f"ci_{post['id']}", label_visibility="collapsed", placeholder="Adicionar comentário…")
        if st.button("Enviar", key=f"cs_{post['id']}"):
            if nc:
                post["comments"].append({"user": guser().get("name", "Você"), "text": nc})
                record(post["tags"], .8); save_db(); st.rerun()

# ─── SEARCH PAGE ────────────────────────
def _set_search_query(value):
    st.session_state.sq = value

def page_search():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.2rem;">Busca de Artigos</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.83rem;margin-bottom:1rem;">Busca em tempo real via Semantic Scholar + CrossRef + Nebula</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([3, .9, .9])
    with c1: q = st.text_input("", placeholder="Título, autor, DOI, tema…", key="sq", label_visibility="collapsed")
    with c2: src = st.selectbox("", ["Nebula + Internet", "Só Nebula", "Só Internet"], key="src_sel", label_visibility="collapsed")
    with c3: yr = st.selectbox("", ["Todos anos", "2026", "2025", "2024", "2023", "2022"], key="yr_f", label_visibility="collapsed")

    if q:
        ql = q.lower()
        record([ql], .3)
        neb_res = [p for p in st.session_state.feed_posts if ql in p["title"].lower() or ql in p["abstract"].lower() or any(ql in t.lower() for t in p["tags"]) or ql in p["author"].lower()]
        if yr != "Todos anos": neb_res = [p for p in neb_res if yr in p.get("date", "")]
        if src == "Só Internet": neb_res = []
        cache_key = f"{q}|{yr}"
        web_res = []
        if src != "Só Nebula":
            if cache_key not in st.session_state.scholar_cache:
                with st.spinner("Buscando em bases acadêmicas…"):
                    ss = search_semantic_scholar(q, 8)
                    cr = search_crossref(q, 5)
                    merged = ss + [x for x in cr if not any(x["title"].lower() == s["title"].lower() for s in ss)]
                    if yr != "Todos anos": merged = [a for a in merged if str(a.get("year", "")) == yr]
                    st.session_state.scholar_cache[cache_key] = merged
            web_res = st.session_state.scholar_cache.get(cache_key, [])

        tab_all, tab_neb, tab_web = st.tabs([f"  Todos ({len(neb_res)+len(web_res)})  ", f"  Nebula ({len(neb_res)})  ", f"  Internet ({len(web_res)})  "])
        with tab_neb:
            if neb_res:
                for p in neb_res: render_search_post(p)
            else: st.markdown('<div style="color:var(--t3);text-align:center;padding:2rem;">Nenhum resultado na Nebula.</div>', unsafe_allow_html=True)
        with tab_web:
            if src == "Só Nebula": st.info("Busca na internet desativada.")
            elif web_res:
                for a in web_res: render_web_article(a)
            else: st.markdown('<div style="color:var(--t3);text-align:center;padding:2rem;">Sem resultados online.</div>', unsafe_allow_html=True)
        with tab_all:
            if neb_res:
                st.markdown('<div style="font-size:.70rem;color:var(--blue-300);font-weight:600;margin-bottom:.4rem;letter-spacing:.06em;text-transform:uppercase;">NEBULA</div>', unsafe_allow_html=True)
                for p in neb_res: render_search_post(p)
            if web_res:
                if neb_res: st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown('<div style="font-size:.70rem;color:var(--cyan-l);font-weight:600;margin-bottom:.4rem;letter-spacing:.06em;text-transform:uppercase;">BASE ACADÊMICA GLOBAL</div>', unsafe_allow_html=True)
                for a in web_res: render_web_article(a)
            if not neb_res and not web_res:
                st.markdown('<div class="card" style="text-align:center;padding:3rem;"><div style="font-size:2.5rem;margin-bottom:1rem;">🔭</div><div style="color:var(--t3);">Nenhum resultado encontrado</div></div>', unsafe_allow_html=True)
    else:
        u = guser()
        tags = area_to_tags(u.get("area", ""))
        if tags:
            st.markdown(f'<div style="color:var(--t2);font-size:.82rem;margin-bottom:.8rem;">💡 Sugestões para <strong>{u.get("area","")}</strong>:</div>', unsafe_allow_html=True)
            cols = st.columns(5)
            for i, t in enumerate(tags[:5]):
                with cols[i % 5]:
                    st.button(f"🔎 {t}", key=f"sug_{t}", use_container_width=True, on_click=_set_search_query, kwargs={"value": t})
        st.markdown('<p style="color:var(--t3);font-size:.80rem;margin-top:1rem;">Digite um termo para buscar artigos na Nebula e em bases acadêmicas globais em tempo real.</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def render_search_post(post):
    aemail = post.get("author_email", "")
    aphoto = get_photo(aemail)
    ain = post.get("avatar", "??")
    c_main, c_btn = st.columns([8, 1])
    with c_main:
        st.markdown(f"""
        <div class="scard">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:.6rem;">
            {avh(ain, 30, aphoto)}
            <div style="flex:1;">
              <div style="font-size:.80rem;font-weight:600;font-family:'Syne',sans-serif;">{post['author']}</div>
              <div style="font-size:.69rem;color:var(--t3);">{post['area']} · {post['date']} · {badge(post['status'])}</div>
            </div>
            <span style="font-size:.66rem;color:var(--blue-300);background:rgba(34,114,195,.10);border-radius:8px;padding:2px 8px;">Nebula</span>
          </div>
          <div style="font-family:'Syne',sans-serif;font-size:.92rem;font-weight:700;margin-bottom:.3rem;">{post['title']}</div>
          <div style="font-size:.81rem;color:var(--t2);margin-bottom:.4rem;">{post['abstract'][:220]}…</div>
          <div>{tags_html(post['tags'])}</div>
        </div>
        """, unsafe_allow_html=True)
    with c_btn:
        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
        if aemail and st.button("👤", key=f"vpa_s_{post['id']}", use_container_width=True):
            st.session_state.profile_view = aemail; st.rerun()

def render_web_article(a):
    src_color = "#22d3ee" if a.get("origin") == "semantic" else "#a78bfa"
    src_name = "Semantic Scholar" if a.get("origin") == "semantic" else "CrossRef"
    cite = f" · {a['citations']} citações" if a.get("citations") else ""
    st.markdown(f"""
    <div class="scard">
      <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:.35rem;">
        <div style="flex:1;font-family:'Syne',sans-serif;font-size:.92rem;font-weight:700;">{a['title']}</div>
        <span style="font-size:.65rem;color:{src_color};background:rgba(6,182,212,.08);border-radius:8px;padding:2px 8px;white-space:nowrap;flex-shrink:0;">{src_name}</span>
      </div>
      <div style="color:var(--t3);font-size:.71rem;margin-bottom:.4rem;">{a['authors']} · <em>{a['source']}</em> · {a['year']}{cite}</div>
      <div style="color:var(--t2);font-size:.82rem;line-height:1.6;margin-bottom:.4rem;">{a['abstract'][:220]}…</div>
      <div style="font-size:.67rem;color:var(--t3);">ID: {a['doi']}</div>
    </div>
    """, unsafe_allow_html=True)
    ca, cb, cc = st.columns([1, 1, 1])
    with ca:
        if st.button("📌 Salvar", key=f"sv_w_{a['doi'][:18]}_{a['year']}"):
            if st.session_state.folders:
                first = list(st.session_state.folders.keys())[0]
                fn = f"{a['title'][:28]}.pdf"
                fd = st.session_state.folders[first]
                lst = fd["files"] if isinstance(fd, dict) else fd
                if fn not in lst: lst.append(fn)
                save_db(); st.toast(f"Salvo em '{first}'")
            else: st.toast("Crie uma pasta primeiro!")
    with cb:
        if st.button("📋 Citar APA", key=f"ct_w_{a['doi'][:18]}_{a['year']}"):
            st.toast(f'{a["authors"]} ({a["year"]}). {a["title"]}. {a["source"]}.')
    with cc:
        if a.get("url"):
            st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:var(--blue-300);font-size:.80rem;text-decoration:none;line-height:2.4;display:block;padding-top:2px;">Abrir ↗</a>', unsafe_allow_html=True)

# ─── KNOWLEDGE / CONNECTIONS PAGE ──────
def page_knowledge():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.2rem;">Rede de Conexões</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.83rem;margin-bottom:.9rem;">Pesquisadores conectados por interesses, pesquisas e pastas em comum</p>', unsafe_allow_html=True)

    email = st.session_state.current_user
    users = st.session_state.users if isinstance(st.session_state.users, dict) else {}

    # Build researcher nodes and edges based on shared interests/tags
    researcher_nodes = {}
    for ue, ud in users.items():
        tags = area_to_tags(ud.get("area", ""))
        post_tags = []
        for p in st.session_state.feed_posts:
            if p.get("author_email") == ue:
                post_tags.extend(p.get("tags", []))
        folder_tags = []
        if ue == email:
            for fn, fd in st.session_state.folders.items():
                if isinstance(fd, dict):
                    folder_tags.extend(fd.get("analysis_tags", []))
        all_tags = list(set(tags + post_tags + folder_tags))
        researcher_nodes[ue] = {
            "name": ud.get("name", ue),
            "area": ud.get("area", ""),
            "tags": all_tags,
            "followers": ud.get("followers", 0),
            "photo": ud.get("photo_b64"),
            "is_me": ue == email
        }

    # Find connections: researchers share at least 1 common tag
    edges = []
    researcher_list = list(researcher_nodes.keys())
    for i in range(len(researcher_list)):
        for j in range(i + 1, len(researcher_list)):
            e1, e2 = researcher_list[i], researcher_list[j]
            n1, n2 = researcher_nodes[e1], researcher_nodes[e2]
            common = set(t.lower() for t in n1["tags"]) & set(t.lower() for t in n2["tags"])
            if common:
                edges.append((e1, e2, list(common)))
            # Also connect if following
            elif e2 in st.session_state.followed or e1 in st.session_state.followed:
                edges.append((e1, e2, ["Seguindo"]))

    # Assign positions (circular/spiral layout)
    n = len(researcher_list)
    positions = {}
    for idx, ue in enumerate(researcher_list):
        angle = (2 * 3.14159 * idx) / max(n, 1)
        r_dist = 0.35 + 0.15 * (idx % 3) / 2
        positions[ue] = {
            "x": 0.5 + r_dist * (1.6 * (idx % 2 - 0.5)) * (0.5 + 0.5 * (idx / n)),
            "y": 0.5 + r_dist * (1 - 2 * (idx / n)),
            "z": 0.5 + 0.3 * ((idx % 3) / 2 - 0.5)
        }

    # Build plotly 3D figure
    ex, ey, ez, edge_labels = [], [], [], []
    for e1, e2, common in edges:
        p1 = positions.get(e1, {"x": 0.5, "y": 0.5, "z": 0.5})
        p2 = positions.get(e2, {"x": 0.5, "y": 0.5, "z": 0.5})
        ex += [p1["x"], p2["x"], None]
        ey += [p1["y"], p2["y"], None]
        ez += [p1["z"], p2["z"], None]

    node_x = [positions[ue]["x"] for ue in researcher_list]
    node_y = [positions[ue]["y"] for ue in researcher_list]
    node_z = [positions[ue]["z"] for ue in researcher_list]
    node_colors = []
    node_sizes = []
    node_texts = []
    node_hovers = []
    for ue in researcher_list:
        nd = researcher_nodes[ue]
        if nd["is_me"]:
            node_colors.append("#22d3ee")
            node_sizes.append(22)
        elif ue in st.session_state.followed:
            node_colors.append("#3b8de0")
            node_sizes.append(18)
        else:
            node_colors.append("#1a3a6b")
            node_sizes.append(14)
        node_texts.append(nd["name"].split()[0])
        shared_count = sum(1 for e1, e2, _ in edges if e1 == ue or e2 == ue)
        node_hovers.append(f"<b>{nd['name']}</b><br>Área: {nd['area']}<br>Conexões: {shared_count}<br>Tópicos: {', '.join(nd['tags'][:4]) if nd['tags'] else 'N/A'}<extra></extra>")

    fig = go.Figure()
    if ex:
        fig.add_trace(go.Scatter3d(x=ex, y=ey, z=ez, mode="lines", line=dict(color="rgba(59,141,224,0.25)", width=2), hoverinfo="none", showlegend=False))
    fig.add_trace(go.Scatter3d(
        x=node_x, y=node_y, z=node_z,
        mode="markers+text",
        marker=dict(size=node_sizes, color=node_colors, opacity=0.92, line=dict(color="rgba(147,197,253,0.3)", width=1.5)),
        text=node_texts,
        textposition="top center",
        textfont=dict(color="#8ba8cc", size=9, family="DM Sans"),
        hovertemplate=node_hovers,
        showlegend=False,
    ))
    fig.update_layout(
        height=520,
        scene=dict(
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, showbackground=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, showbackground=False),
            zaxis=dict(showgrid=False, zeroline=False, showticklabels=False, showbackground=False),
            bgcolor="rgba(0,0,0,0)",
            camera=dict(eye=dict(x=1.5, y=1.3, z=0.9))
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        font=dict(color="#8ba8cc"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Stats
    c1, c2, c3, c4 = st.columns(4)
    for col, (v, l) in zip([c1, c2, c3, c4], [(len(researcher_list), "Pesquisadores"), (len(edges), "Conexões"), (len(st.session_state.followed), "Seguindo"), (len(st.session_state.feed_posts), "Pesquisas")]):
        with col:
            st.markdown(f'<div class="mbox"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>', unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    tab_map, tab_my = st.tabs(["  Mapa de Conexões  ", "  Minhas Conexões  "])
    with tab_map:
        if edges:
            for e1, e2, common in edges[:20]:
                n1 = researcher_nodes.get(e1, {})
                n2 = researcher_nodes.get(e2, {})
                common_tags = "".join(f'<span class="tag">{c}</span>' for c in common[:4])
                st.markdown(
                    f'<div class="card" style="padding:1rem 1.3rem;">'
                    f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">'
                    f'<span style="font-size:.82rem;font-weight:600;color:var(--blue-300);">{n1.get("name","?")}</span>'
                    f'<span style="color:var(--t3);font-size:.78rem;">↔</span>'
                    f'<span style="font-size:.82rem;font-weight:600;color:var(--blue-300);">{n2.get("name","?")}</span>'
                    f'<span style="color:var(--t3);font-size:.72rem;margin-left:4px;">em comum:</span>'
                    f'{common_tags}'
                    f'</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="card" style="text-align:center;padding:2rem;color:var(--t3);">Siga pesquisadores e publique pesquisas para ver conexões emergir.</div>', unsafe_allow_html=True)

    with tab_my:
        my_tags = researcher_nodes.get(email, {}).get("tags", [])
        if my_tags:
            st.markdown(f'<div style="margin-bottom:.8rem;font-size:.83rem;color:var(--t2);">Seus tópicos de interesse: {tags_html(my_tags[:8])}</div>', unsafe_allow_html=True)
        my_connections = [(e1, e2, common) for e1, e2, common in edges if e1 == email or e2 == email]
        if my_connections:
            for e1, e2, common in my_connections:
                other_email = e2 if e1 == email else e1
                other = researcher_nodes.get(other_email, {})
                st.markdown(
                    f'<div class="card" style="padding:1rem 1.3rem;">'
                    f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">'
                    f'{avh(ini(other.get("name","?")), 32, other.get("photo"))}'
                    f'<div style="flex:1;">'
                    f'<div style="font-size:.84rem;font-weight:600;">{other.get("name","?")}</div>'
                    f'<div style="font-size:.71rem;color:var(--t3);">{other.get("area","")}</div>'
                    f'</div>'
                    f'<div>{tags_html(common[:3])}</div>'
                    f'</div></div>', unsafe_allow_html=True)
                c_v, c_m, _ = st.columns([1, 1, 4])
                with c_v:
                    if st.button("👤 Perfil", key=f"kn_vp_{other_email}"):
                        st.session_state.profile_view = other_email; st.rerun()
                with c_m:
                    if st.button("💬 Chat", key=f"kn_ch_{other_email}"):
                        st.session_state.active_chat = other_email
                        st.session_state.page = "chat"; st.rerun()
        else:
            st.markdown('<div class="card" style="text-align:center;padding:2rem;color:var(--t3);">Nenhuma conexão ainda. Publique pesquisas com tags para conectar com pesquisadores de interesses similares!</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ─── FOLDERS PAGE ───────────────────────
def page_folders():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.2rem;">Pastas de Pesquisa</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.83rem;margin-bottom:1rem;">Organize seus documentos e análise automática de conteúdo por área</p>', unsafe_allow_html=True)

    c1, c2, _ = st.columns([2, 1.2, 1.5])
    with c1: nf_name = st.text_input("Nome da pasta", placeholder="Ex: Genômica Comparativa", key="nf_n")
    with c2: nf_desc = st.text_input("Descrição", placeholder="Breve descrição", key="nf_d")
    if st.button("➕ Criar pasta", key="btn_nf"):
        if nf_name.strip():
            if nf_name not in st.session_state.folders:
                st.session_state.folders[nf_name] = {"desc": nf_desc, "files": [], "notes": "", "analysis_tags": [], "analysis_summary": "", "file_analyses": []}
                save_db(); st.success(f"✓ Pasta '{nf_name}' criada!"); st.rerun()
            else: st.warning("Pasta já existe.")
        else: st.warning("Digite um nome para a pasta.")

    st.markdown("<hr>", unsafe_allow_html=True)

    if not st.session_state.folders:
        st.markdown('<div class="card" style="text-align:center;padding:3rem;"><div style="font-size:3rem;margin-bottom:1rem;">📂</div><div style="color:var(--t2);font-family:\'Syne\',sans-serif;font-size:1rem;font-weight:700;">Nenhuma pasta criada ainda</div><div style="color:var(--t3);font-size:.82rem;margin-top:.4rem;">Use o formulário acima para criar sua primeira pasta de pesquisa</div></div>', unsafe_allow_html=True)
    else:
        cols = st.columns(3)
        for idx, (fname, fdata) in enumerate(list(st.session_state.folders.items())):
            files = fdata["files"] if isinstance(fdata, dict) else fdata
            desc = fdata.get("desc", "") if isinstance(fdata, dict) else ""
            analysis_tags = fdata.get("analysis_tags", []) if isinstance(fdata, dict) else []
            analysis_summary = fdata.get("analysis_summary", "") if isinstance(fdata, dict) else ""
            file_analyses = fdata.get("file_analyses", []) if isinstance(fdata, dict) else []

            with cols[idx % 3]:
                has_analysis = bool(analysis_tags)
                st.markdown(
                    f'<div class="card" style="text-align:center;">'
                    f'<div style="font-size:2.4rem;margin-bottom:8px;">📁</div>'
                    f'<div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.96rem;">{fname}</div>'
                    f'<div style="color:var(--t3);font-size:.70rem;margin-top:3px;">{desc}</div>'
                    f'<div style="color:var(--blue-300);font-size:.73rem;margin-top:6px;">{len(files)} arquivo(s)</div>'
                    f'{"<div style=\'margin-top:6px;\'>" + tags_html(analysis_tags[:3]) + "</div>" if has_analysis else ""}'
                    f'</div>', unsafe_allow_html=True)

                with st.expander(f"📂 Abrir '{fname}'"):
                    # Upload section
                    st.markdown('<div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.5rem;color:var(--t2);">Arquivos</div>', unsafe_allow_html=True)
                    up = st.file_uploader("Adicionar arquivo", key=f"up_{fname}", label_visibility="collapsed")
                    if up:
                        lst = fdata["files"] if isinstance(fdata, dict) else fdata
                        if up.name not in lst: lst.append(up.name)
                        save_db(); st.success("✓ Adicionado!"); st.rerun()

                    if files:
                        for f in files:
                            st.markdown(f'<div style="font-size:.80rem;padding:5px 0;color:var(--t2);border-bottom:1px solid var(--glass-border);display:flex;align-items:center;gap:6px;">📄 {f}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<p style="color:var(--t3);font-size:.78rem;text-align:center;padding:.5rem;">Nenhum arquivo ainda. Faça upload acima.</p>', unsafe_allow_html=True)

                    st.markdown("<hr>", unsafe_allow_html=True)

                    # Analysis section
                    st.markdown('<div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.5rem;color:var(--t2);">🔬 Análise de Pesquisa</div>', unsafe_allow_html=True)

                    if st.button("Analisar documentos da pasta", key=f"analyze_{fname}", use_container_width=True):
                        if files:
                            with st.spinner("Analisando conteúdo dos documentos…"):
                                result = analyze_folder_documents(fname)
                            if result and isinstance(fdata, dict):
                                fdata["analysis_tags"] = result["tags"]
                                fdata["analysis_summary"] = result["summary"]
                                fdata["file_analyses"] = result["file_analyses"]
                                save_db()
                                record(result["tags"], 1.5)
                                st.success("✓ Análise concluída!"); st.rerun()
                        else:
                            st.warning("Adicione arquivos antes de analisar.")

                    if analysis_summary:
                        st.markdown(f"""
                        <div class="abox" style="margin-top:.6rem;">
                          <div style="font-size:.68rem;color:var(--t3);letter-spacing:.06em;text-transform:uppercase;margin-bottom:5px;">Resumo da Análise</div>
                          <div style="font-size:.82rem;color:var(--t2);line-height:1.6;">{analysis_summary}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    if analysis_tags:
                        st.markdown('<div style="font-size:.72rem;color:var(--t3);margin-top:.5rem;margin-bottom:.3rem;text-transform:uppercase;letter-spacing:.05em;">Áreas identificadas</div>', unsafe_allow_html=True)
                        st.markdown(tags_html(analysis_tags), unsafe_allow_html=True)

                    if file_analyses:
                        st.markdown('<div style="font-size:.72rem;color:var(--t3);margin-top:.8rem;margin-bottom:.3rem;text-transform:uppercase;letter-spacing:.05em;">Por arquivo</div>', unsafe_allow_html=True)
                        for fa in file_analyses:
                            st.markdown(
                                f'<div style="background:rgba(10,26,53,.6);border:1px solid var(--glass-border);border-radius:var(--r-sm);padding:8px 12px;margin-bottom:4px;">'
                                f'<div style="font-size:.78rem;font-weight:600;color:var(--t1);margin-bottom:3px;">📄 {fa["file"]}</div>'
                                f'<div>{tags_html(fa["tags"])}</div>'
                                f'</div>', unsafe_allow_html=True)

                    st.markdown("<hr>", unsafe_allow_html=True)

                    # Notes
                    note = st.text_area("Notas", value=fdata.get("notes", "") if isinstance(fdata, dict) else "", key=f"note_{fname}", height=70, placeholder="Observações rápidas…")
                    if st.button("💾 Salvar nota", key=f"sn_{fname}"):
                        if isinstance(fdata, dict): fdata["notes"] = note
                        save_db(); st.success("✓ Nota salva!")

                if st.button(f"🗑️ Excluir '{fname}'", key=f"df_{fname}"):
                    del st.session_state.folders[fname]; save_db(); st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# ─── ANALYTICS PAGE ─────────────────────
def page_analytics():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.2rem;">Análises de Impacto</h1>', unsafe_allow_html=True)
    d = st.session_state.stats_data
    email = st.session_state.current_user

    pc = dict(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#3d5a80", family="DM Sans"), margin=dict(l=10, r=10, t=40, b=10), xaxis=dict(showgrid=False, color="#3d5a80"), yaxis=dict(showgrid=True, gridcolor="rgba(59,141,224,.06)", color="#3d5a80"))

    tab_perf, tab_pref, tab_edit = st.tabs(["  Desempenho  ", "  Interesses  ", "  Editar  "])

    with tab_perf:
        cols = st.columns(4)
        for col, (v, l) in zip(cols, [(str(max(d["views"])), "Pico visualizações"), (str(sum(d["citations"])), "Total citações"), (str(d.get("h_index", 4)), "Índice H"), (f'{d.get("fator_impacto", 3.8):.1f}', "Fator de impacto")]):
            with col: st.markdown(f'<div class="mbox"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=d["months"], y=d["views"], fill="tozeroy", fillcolor="rgba(34,114,195,.09)", line=dict(color="#3b8de0", width=2.5), mode="lines+markers", marker=dict(size=4, color="#60a5f5")))
            fig.update_layout(title=dict(text="Visualizações mensais", font=dict(color="#e0e8ff", family="Syne")), height=240, **pc)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=d["months"], y=d["citations"], marker=dict(color=d["citations"], colorscale=[[0, "#050c1a"], [1, "#06b6d4"]], line=dict(color="rgba(96,165,245,.20)", width=1))))
            fig2.update_layout(title=dict(text="Citações mensais", font=dict(color="#e0e8ff", family="Syne")), height=240, **pc)
            st.plotly_chart(fig2, use_container_width=True)

        my_posts = [p for p in st.session_state.feed_posts if p.get("author_email") == email]
        c3, c4 = st.columns(2)
        with c3:
            if my_posts:
                fig3 = go.Figure()
                fig3.add_trace(go.Bar(name="Curtidas", x=[p["title"][:16]+"…" for p in my_posts], y=[p["likes"] for p in my_posts], marker_color="#2272c3"))
                fig3.add_trace(go.Bar(name="Comentários", x=[p["title"][:16]+"…" for p in my_posts], y=[len(p["comments"]) for p in my_posts], marker_color="#06b6d4"))
                fig3.update_layout(barmode="group", title=dict(text="Engajamento", font=dict(color="#e0e8ff", family="Syne")), height=240, **pc, legend=dict(font=dict(color="#8ba8cc")))
                st.plotly_chart(fig3, use_container_width=True)
        with c4:
            fig4 = go.Figure(go.Pie(labels=["Brasil", "EUA", "Portugal", "Alemanha", "Argentina", "Outros"], values=[95, 62, 38, 25, 10, 20], hole=0.62, marker=dict(colors=["#2272c3", "#1a3a6b", "#3b8de0", "#1e4d8c", "#60a5f5", "#0891b2"], line=dict(color=["#010409"]*6, width=2)), textfont=dict(color="white")))
            fig4.update_layout(title=dict(text="Leitores por país", font=dict(color="#e0e8ff", family="Syne")), height=240, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(font=dict(color="#8ba8cc")), margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig4, use_container_width=True)

        fig_g = go.Figure(go.Indicator(mode="gauge+number", value=d.get("aceitacao", 94), title={"text": "Taxa de Aceitação (%)", "font": {"color": "#8ba8cc", "family": "DM Sans"}}, number={"suffix": "%", "font": {"color": "#60a5f5", "size": 34}}, gauge={"axis": {"range": [0, 100], "tickcolor": "#3d5a80"}, "bar": {"color": "#2272c3"}, "bgcolor": "rgba(10,22,40,.5)", "bordercolor": "rgba(59,141,224,.3)", "steps": [{"range": [0, 50], "color": "rgba(239,68,68,.07)"}, {"range": [50, 80], "color": "rgba(245,158,11,.07)"}, {"range": [80, 100], "color": "rgba(16,185,129,.07)"}]}))
        fig_g.update_layout(height=200, paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#8ba8cc"))
        st.plotly_chart(fig_g, use_container_width=True)

    with tab_pref:
        prefs = st.session_state.user_prefs.get(email, {})
        if prefs:
            st.markdown('<p style="color:var(--t3);font-size:.82rem;margin-bottom:1rem;">Baseado nas suas interações: curtidas, buscas, comentários e publicações.</p>', unsafe_allow_html=True)
            top = sorted(prefs.items(), key=lambda x: -x[1])[:12]
            mx = max(s for _, s in top) if top else 1
            c1, c2 = st.columns(2)
            for i, (tag, score) in enumerate(top):
                pct = int(score / mx * 100)
                with (c1 if i % 2 == 0 else c2):
                    st.markdown(f'<div style="display:flex;justify-content:space-between;font-size:.80rem;margin-bottom:3px;"><span style="color:var(--t2);">{tag}</span><span style="color:var(--blue-300);">{pct}%</span></div>', unsafe_allow_html=True)
                    st.progress(pct / 100)
        else: st.info("Interaja com pesquisas para construir seu perfil de interesses.")

    with tab_edit:
        st.markdown('<h3>Editar métricas</h3>', unsafe_allow_html=True)
        ce1, ce2, ce3 = st.columns(3)
        with ce1: new_h = st.number_input("Índice H", 0, 100, d.get("h_index", 4), key="e_h")
        with ce2: new_fi = st.number_input("Fator de impacto", 0.0, 50.0, float(d.get("fator_impacto", 3.8)), step=0.1, key="e_fi")
        with ce3: new_ac = st.number_input("Aceitação (%)", 0, 100, d.get("aceitacao", 94), key="e_ac")
        new_notes = st.text_area("Notas", value=d.get("notes", ""), key="e_notes", height=80)
        if st.button("💾 Salvar métricas", key="btn_save_m"):
            d.update({"h_index": new_h, "fator_impacto": new_fi, "aceitacao": new_ac, "notes": new_notes})
            st.success("✓ Métricas atualizadas!"); st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# ─── IMAGE ANALYSIS PAGE ────────────────
def page_img_search():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.2rem;">Análise de Imagem Científica</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.83rem;margin-bottom:1.2rem;">Análise automática de padrões, cores, texturas e classificação de imagens científicas</p>', unsafe_allow_html=True)

    col_up, col_res = st.columns([1, 1.7])
    with col_up:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.88rem;margin-bottom:.8rem;">Upload de imagem</div>', unsafe_allow_html=True)
        img_file = st.file_uploader("", type=["png", "jpg", "jpeg", "webp", "tiff"], label_visibility="collapsed")
        if img_file: st.image(img_file, use_container_width=True, caption="Imagem carregada")
        run = st.button("🔬 Analisar imagem", use_container_width=True, key="btn_run")
        st.markdown('<div style="color:var(--t3);font-size:.71rem;margin-top:.8rem;line-height:1.6;">Detectamos: padrões · cores · texturas · simetria · entropia · classificação científica</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_res:
        if run and img_file:
            img_file.seek(0)
            with st.spinner("Analisando…"):
                rep = analyze_image(img_file)
            if rep:
                st.markdown(f"""
                <div class="abox">
                  <div style="font-size:.67rem;color:var(--t3);letter-spacing:.08em;text-transform:uppercase;margin-bottom:5px;">Categoria Detectada</div>
                  <div style="font-family:'Syne',sans-serif;font-size:1.08rem;font-weight:700;color:var(--t1);margin-bottom:5px;">{rep['category']}</div>
                  <div style="font-size:.83rem;color:var(--t2);line-height:1.6;">{rep['structure']}</div>
                  <div style="margin-top:10px;display:flex;gap:12px;flex-wrap:wrap;">
                    <span style="font-size:.72rem;color:var(--ok);">✓ Confiança: {rep['confidence']}%</span>
                    <span style="font-size:.72rem;color:var(--t3);">{rep['size'][0]}×{rep['size'][1]}px</span>
                  </div>
                </div>
                """, unsafe_allow_html=True)
                c1, c2, c3 = st.columns(3)
                for col, (v, l) in zip([c1, c2, c3], [(rep['texture']['complexity'], "Complexidade"), (rep['shape']['symmetry_level'], "Simetria"), (rep['color']['dominant'], "Canal dom.")]):
                    with col: st.markdown(f'<div class="mbox"><div style="font-family:\'Syne\',sans-serif;font-size:1.2rem;font-weight:700;color:#60a5f5;">{v}</div><div class="mlbl">{l}</div></div>', unsafe_allow_html=True)

                r, g, b_v = rep['color']['mean_rgb']
                hex_col = "#{:02x}{:02x}{:02x}".format(int(r), int(g), int(b_v))
                pal_html = "".join(f'<div style="display:flex;flex-direction:column;align-items:center;gap:3px;"><div style="width:32px;height:32px;border-radius:8px;background:rgb{str(p)};border:1px solid rgba(255,255,255,.10);"></div><div style="font-size:.60rem;color:var(--t3);">#{"{:02x}{:02x}{:02x}".format(*p).upper()}</div></div>' for p in rep["palette"])

                st.markdown(f"""
                <div class="abox">
                  <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:.85rem;margin-bottom:.7rem;">Análise de Cor</div>
                  <div style="display:flex;gap:12px;align-items:center;margin-bottom:.8rem;">
                    <div style="width:44px;height:44px;border-radius:10px;background:{hex_col};border:1.5px solid var(--glass-border-l);flex-shrink:0;"></div>
                    <div style="font-size:.81rem;color:var(--t2);">
                      RGB: <strong style="color:var(--t1);">({int(r)}, {int(g)}, {int(b_v)})</strong> · Hex: <strong style="color:var(--t1);">{hex_col.upper()}</strong><br>
                      Brilho: <strong style="color:var(--t1);">{rep['color']['brightness']:.0f}/255</strong> · Temperatura: <strong style="color:var(--t1);">{"Quente 🔴" if rep['color']['warm'] else "Fria 🔵"}</strong>
                    </div>
                  </div>
                  <div style="display:flex;gap:6px;flex-wrap:wrap;">{pal_html}</div>
                </div>
                """, unsafe_allow_html=True)
            else: st.error("Não foi possível analisar. Verifique o formato.")
        elif not img_file:
            st.markdown("""
            <div class="card" style="text-align:center;padding:4rem 2rem;">
              <div style="font-size:3.5rem;margin-bottom:1rem;">🔬</div>
              <div style="font-family:'Syne',sans-serif;font-size:1rem;color:var(--t2);margin-bottom:.5rem;">Carregue uma imagem para análise</div>
              <div style="color:var(--t3);font-size:.78rem;line-height:1.7;">PNG · JPG · WEBP · TIFF</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ─── CHAT PAGE ──────────────────────────
def page_chat():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.2rem;">Chat Seguro</h1>', unsafe_allow_html=True)
    col_c, col_m = st.columns([0.85, 2.5])

    with col_c:
        st.markdown('<div style="font-size:.70rem;font-weight:600;color:var(--t3);letter-spacing:.08em;text-transform:uppercase;margin-bottom:.7rem;">Conversas</div>', unsafe_allow_html=True)
        if not isinstance(st.session_state.users, dict): st.session_state.users = {}

        shown = set()
        for ue in st.session_state.chat_contacts:
            if ue == st.session_state.current_user or ue in shown: continue
            shown.add(ue)
            ud = st.session_state.users.get(ue, {"name": ue, "area": "", "photo_b64": None})
            uname = ud.get("name", "?")
            uin = ini(uname)
            uphoto = ud.get("photo_b64")
            active = st.session_state.active_chat == ue
            msgs = st.session_state.chat_messages.get(ue, [])
            last = msgs[-1]["text"][:26] + "…" if msgs and len(msgs[-1]["text"]) > 26 else (msgs[-1]["text"] if msgs else "Iniciar conversa")
            online = random.random() > .4
            dot = '<span class="don"></span>' if online else '<span class="doff"></span>'
            border = "rgba(96,165,245,.35)" if active else "var(--glass-border)"
            bg = "rgba(34,114,195,.15)" if active else "var(--glass-bg)"
            st.markdown(f'<div style="background:{bg};border:1px solid {border};border-radius:var(--r-md);padding:9px 11px;margin-bottom:5px;"><div style="display:flex;align-items:center;gap:8px;">{avh(uin,30,uphoto)}<div style="overflow:hidden;min-width:0;"><div style="font-size:.81rem;font-weight:600;display:flex;align-items:center;">{dot}{uname}</div><div style="font-size:.69rem;color:var(--t3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{last}</div></div></div></div>', unsafe_allow_html=True)
            if st.button("Abrir", key=f"oc_{ue}", use_container_width=True):
                st.session_state.active_chat = ue; st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)
        new_contact = st.text_input("", placeholder="Adicionar por e-mail…", key="new_ct", label_visibility="collapsed")
        if st.button("➕ Adicionar", key="btn_add_ct"):
            if isinstance(st.session_state.users, dict) and new_contact in st.session_state.users and new_contact != st.session_state.current_user:
                if new_contact not in st.session_state.chat_contacts: st.session_state.chat_contacts.append(new_contact)
                st.rerun()
            elif new_contact: st.toast("Usuário não encontrado.")

    with col_m:
        if st.session_state.active_chat:
            contact = st.session_state.active_chat
            if not isinstance(st.session_state.users, dict): st.session_state.users = {}
            cd = st.session_state.users.get(contact, {"name": contact, "photo_b64": None})
            cname = cd.get("name", "?")
            cin = ini(cname)
            cphoto = cd.get("photo_b64")
            msgs = st.session_state.chat_messages.get(contact, [])

            st.markdown(f'<div style="background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:var(--r-md);padding:12px 16px;margin-bottom:1rem;display:flex;align-items:center;gap:12px;">{avh(cin,38,cphoto)}<div style="flex:1;"><div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.93rem;">{cname}</div><div style="font-size:.71rem;color:var(--ok);">🔒 Criptografia AES-256</div></div></div>', unsafe_allow_html=True)

            for msg in msgs:
                is_me = msg["from"] == "me"
                cls = "bme" if is_me else "bthem"
                align = "right" if is_me else "left"
                st.markdown(f'<div class="{cls}">{msg["text"]}<div style="font-size:.64rem;color:var(--t3);margin-top:3px;text-align:{align};">{msg["time"]}</div></div>', unsafe_allow_html=True)

            nm = st.text_input("", placeholder="Mensagem segura…", key=f"mi_{contact}", label_visibility="collapsed")
            if st.button("Enviar →", key=f"ms_{contact}", use_container_width=True):
                if nm:
                    now = datetime.now().strftime("%H:%M")
                    st.session_state.chat_messages.setdefault(contact, []).append({"from": "me", "text": nm, "time": now})
                    st.rerun()
        else:
            st.markdown('<div class="card" style="text-align:center;padding:4rem;"><div style="font-size:3rem;margin-bottom:1rem;">💬</div><div style="color:var(--t3);">Selecione uma conversa</div><div style="font-size:.77rem;color:var(--t3);margin-top:.5rem;">🔒 Todas as mensagens são criptografadas end-to-end</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ─── SETTINGS / PROFILE PAGE ────────────
def page_settings():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.2rem;">Perfil e Configurações</h1>', unsafe_allow_html=True)
    u = guser()
    email = st.session_state.current_user
    tab_p, tab_s, tab_pr = st.tabs(["  Meu Perfil  ", "  Segurança  ", "  Privacidade  "])

    with tab_p:
        nm = u.get("name", "")
        in_ = ini(nm)
        photo = u.get("photo_b64")
        st.markdown(f"""
        <div class="prof-hero">
          <div class="prof-photo">{("<img src='"+photo+"'/>") if photo else f'<span style="font-size:2rem;">{in_}</span>'}</div>
          <div style="flex:1;">
            <h1 style="margin-bottom:.25rem;font-size:1.55rem!important;">{nm}</h1>
            <div style="color:var(--blue-300);font-size:.84rem;margin-bottom:.4rem;">{u.get('area','')}</div>
            <div style="color:var(--t2);font-size:.83rem;line-height:1.65;margin-bottom:.8rem;">{u.get('bio','Sem biografia.')}</div>
            <div style="display:flex;gap:1.8rem;">
              <span><strong style="font-family:'Syne',sans-serif;font-size:1.1rem;">{u.get('followers',0)}</strong><span style="color:var(--t3);font-size:.75rem;"> seguidores</span></span>
              <span><strong style="font-family:'Syne',sans-serif;font-size:1.1rem;">{u.get('following',0)}</strong><span style="color:var(--t3);font-size:.75rem;"> seguindo</span></span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.85rem;margin-bottom:.5rem;">📷 Foto de perfil</div>', unsafe_allow_html=True)
        ph = st.file_uploader("", type=["png", "jpg", "jpeg", "webp"], label_visibility="collapsed", key="ph_up")
        if ph:
            b64 = img_to_b64(ph)
            if b64:
                if not isinstance(st.session_state.users, dict): st.session_state.users = {}
                st.session_state.users[email]["photo_b64"] = b64
                save_db(); st.success("✓ Foto atualizada!"); st.image(ph, width=100); st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)
        new_n = st.text_input("Nome completo", value=u.get("name", ""), key="cfg_n")
        new_e = st.text_input("E-mail", value=email, key="cfg_e")
        new_a = st.text_input("Área de pesquisa", value=u.get("area", ""), key="cfg_a")
        new_b = st.text_area("Biografia", value=u.get("bio", ""), key="cfg_b", height=90, placeholder="Fale sobre sua pesquisa e interesses…")
        if st.button("💾 Salvar perfil", key="btn_sp"):
            if not isinstance(st.session_state.users, dict): st.session_state.users = {}
            st.session_state.users[email]["name"] = new_n
            st.session_state.users[email]["area"] = new_a
            st.session_state.users[email]["bio"] = new_b
            if new_e != email and new_e not in st.session_state.users:
                st.session_state.users[new_e] = st.session_state.users.pop(email)
                st.session_state.current_user = new_e
            save_db(); record(area_to_tags(new_a), 1.5); st.success("✓ Perfil salvo!"); st.rerun()

    with tab_s:
        st.markdown('<h3>Alterar senha</h3>', unsafe_allow_html=True)
        op = st.text_input("Senha atual", type="password", key="op")
        np_ = st.text_input("Nova senha", type="password", key="np_")
        np2 = st.text_input("Confirmar nova senha", type="password", key="np2")
        if st.button("🔑 Alterar senha", key="btn_cpw"):
            if hp(op) != u["password"]: st.error("Senha atual incorreta.")
            elif np_ != np2: st.error("Senhas não coincidem.")
            elif len(np_) < 6: st.error("Senha muito curta.")
            else:
                if not isinstance(st.session_state.users, dict): st.session_state.users = {}
                st.session_state.users[email]["password"] = hp(np_)
                save_db(); st.success("✓ Senha alterada!")

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<h3>Autenticação em 2 fatores</h3>', unsafe_allow_html=True)
        en = u.get("2fa_enabled", False)
        st.markdown(f'<div class="card" style="display:flex;align-items:center;justify-content:space-between;padding:1rem 1.3rem;"><div><div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.88rem;">2FA por e-mail</div><div style="font-size:.73rem;color:var(--t3);">{email}</div></div><span style="color:{"#10b981" if en else "#ef4444"};font-size:.82rem;font-weight:700;">{"✓ Ativo" if en else "✗ Inativo"}</span></div>', unsafe_allow_html=True)
        if st.button("Desativar 2FA" if en else "Ativar 2FA", key="btn_2fa"):
            if not isinstance(st.session_state.users, dict): st.session_state.users = {}
            st.session_state.users[email]["2fa_enabled"] = not en
            save_db(); st.rerun()

    with tab_pr:
        prots = [("AES-256", "Criptografia end-to-end das mensagens"), ("SHA-256", "Hash de senhas com salt criptográfico"), ("TLS 1.3", "Transmissão segura de todos os dados"), ("Zero Knowledge", "Pesquisas privadas inacessíveis pela plataforma")]
        items = "".join(f'<div style="display:flex;align-items:center;gap:12px;background:rgba(16,185,129,.06);border:1px solid rgba(16,185,129,.15);border-radius:var(--r-md);padding:11px;"><div style="width:28px;height:28px;border-radius:8px;background:rgba(16,185,129,.12);display:flex;align-items:center;justify-content:center;color:#10b981;font-weight:700;font-size:.76rem;flex-shrink:0;">✓</div><div><div style="font-family:\'Syne\',sans-serif;font-weight:700;color:#10b981;font-size:.84rem;">{n2}</div><div style="font-size:.72rem;color:var(--t3);">{d2}</div></div></div>' for n2, d2 in prots)
        st.markdown(f'<div class="card"><div style="font-family:\'Syne\',sans-serif;font-weight:700;margin-bottom:1rem;">Proteções ativas</div><div style="display:grid;gap:8px;">{items}</div></div>', unsafe_allow_html=True)

        st.markdown('<h3>Visibilidade</h3>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.selectbox("Perfil", ["Público", "Só seguidores", "Privado"], key="vp")
            st.selectbox("Pesquisas", ["Público", "Só seguidores", "Privado"], key="vr")
        with c2:
            st.selectbox("Estatísticas", ["Público", "Privado"], key="vs")
            st.selectbox("Rede de conexões", ["Público", "Só seguidores", "Privado"], key="vn")
        if st.button("💾 Salvar privacidade", key="btn_priv"):
            st.success("✓ Configurações de privacidade salvas!")

    st.markdown('</div>', unsafe_allow_html=True)

# ─── ROUTER ─────────────────────────────
def main():
    if not st.session_state.logged_in:
        p = st.session_state.page
        if p == "verify_email": page_verify_email()
        elif p == "2fa": page_2fa()
        else: page_login()
        return

    render_topnav()

    if st.session_state.profile_view:
        page_profile(st.session_state.profile_view)
        return

    {
        "feed": page_feed,
        "search": page_search,
        "knowledge": page_knowledge,
        "folders": page_folders,
        "analytics": page_analytics,
        "img_search": page_img_search,
        "chat": page_chat,
        "settings": page_settings
    }.get(st.session_state.page, page_feed)()

main()
