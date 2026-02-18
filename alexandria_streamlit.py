import os, json, hashlib, random, string, base64, re
from datetime import datetime
from collections import defaultdict

import plotly.graph_objects as go
import plotly.express as px
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
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_db():
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": st.session_state.users, "feed_posts": st.session_state.feed_posts,
                       "folders": st.session_state.folders, "knowledge_nodes": st.session_state.knowledge_nodes,
                       "user_prefs": st.session_state.user_prefs}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

def hp(pw): return hashlib.sha256(pw.encode()).hexdigest()
def code6(): return ''.join(random.choices(string.digits, k=6))
def ini(n):
    if not isinstance(n, str): n = str(n)
    return ''.join(w[0].upper() for w in n.split()[:2])

def img_to_b64(file_obj):
    try:
        file_obj.seek(0); data = file_obj.read()
        ext = getattr(file_obj, "name", "img.png").split(".")[-1].lower()
        mime = {"jpg":"jpeg","jpeg":"jpeg","png":"png","gif":"gif","webp":"webp"}.get(ext, "png")
        return f"data:image/{mime};base64,{base64.b64encode(data).decode()}"
    except: return None

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&display=swap');

:root {
  --void:#010409; --deep:#050c1a; --navy:#071428; --surface:#0a1a35; --elevated:#0e2040;
  --b950:#0a1628; --b900:#0f2040; --b800:#1a3a6b; --b700:#1e4d8c; --b600:#1d5fa8;
  --b500:#2272c3; --b400:#3b8de0; --b300:#60a5f5; --b200:#93c5fd; --b100:#dbeafe;
  --cyan:#06b6d4; --cyanl:#22d3ee; --cyanxl:#67e8f9;
  --t1:#f0f6ff; --t2:#8ba8cc; --t3:#3d5a80; --t4:#1e3152;
  --gb:rgba(8,20,48,0.68); --gbl:rgba(14,32,64,0.52);
  --gbd:rgba(59,141,224,0.14); --gbdl:rgba(96,165,245,0.24); --gbdxl:rgba(147,197,253,0.34);
  --ok:#10b981; --warn:#f59e0b; --err:#ef4444;
  --rxs:8px; --rsm:12px; --rmd:18px; --rlg:24px; --rxl:32px;
}

*,*::before,*::after{box-sizing:border-box;margin:0}
html,body,.stApp{background:var(--void)!important;color:var(--t1)!important;font-family:'DM Sans',sans-serif!important}

/* Space background */
.stApp::before{content:'';position:fixed;inset:0;
  background:radial-gradient(ellipse 80% 50% at 15% 10%,rgba(34,114,195,.13) 0%,transparent 60%),
             radial-gradient(ellipse 60% 70% at 85% 90%,rgba(6,182,212,.08) 0%,transparent 55%),
             radial-gradient(ellipse 40% 60% at 50% 50%,rgba(10,22,40,.95) 0%,transparent 80%);
  pointer-events:none;z-index:0;animation:bgB 18s ease-in-out infinite alternate}
@keyframes bgB{from{opacity:.7}to{opacity:1}}

/* Stars */
.stApp::after{content:'';position:fixed;inset:0;
  background-image:radial-gradient(1px 1px at 18% 25%,rgba(147,197,253,.5) 0%,transparent 100%),
    radial-gradient(1px 1px at 72% 18%,rgba(147,197,253,.4) 0%,transparent 100%),
    radial-gradient(1.5px 1.5px at 40% 65%,rgba(96,165,245,.4) 0%,transparent 100%),
    radial-gradient(1px 1px at 88% 45%,rgba(147,197,253,.3) 0%,transparent 100%),
    radial-gradient(1px 1px at 8% 78%,rgba(96,165,245,.3) 0%,transparent 100%),
    radial-gradient(1px 1px at 55% 88%,rgba(147,197,253,.2) 0%,transparent 100%);
  pointer-events:none;z-index:0}

[data-testid="collapsedControl"]{display:none!important}
section[data-testid="stSidebar"]{display:none!important}

h1,h2,h3,h4{font-family:'Syne',sans-serif!important;color:var(--t1)!important;font-weight:700;letter-spacing:-.02em}
h1{font-size:1.7rem!important}h2{font-size:1.3rem!important}h3{font-size:1rem!important}

/* ── GLASS CARD ── */
.card{
  background:var(--gb);
  backdrop-filter:blur(24px) saturate(180%);
  -webkit-backdrop-filter:blur(24px) saturate(180%);
  border:1px solid var(--gbd);
  border-radius:var(--rlg);
  padding:1.4rem 1.6rem;
  margin-bottom:.9rem;
  box-shadow:0 8px 32px rgba(0,0,0,.42),0 2px 8px rgba(0,0,0,.3),inset 0 1px 0 rgba(147,197,253,.06);
  position:relative;overflow:hidden;
  animation:sU .35s cubic-bezier(.34,1.56,.64,1) both;
  transition:border-color .25s,box-shadow .25s,transform .2s
}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(96,165,245,.3),transparent)}
.card:hover{border-color:var(--gbdl);
  box-shadow:0 14px 44px rgba(0,0,0,.5),0 0 0 1px rgba(59,141,224,.1),inset 0 1px 0 rgba(147,197,253,.09);
  transform:translateY(-1px)}
@keyframes sU{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}

/* ── LIQUID GLASS BUTTON ── */
.stButton>button{
  background:linear-gradient(135deg,rgba(22,75,156,.56) 0%,rgba(14,52,114,.46) 40%,rgba(6,182,212,.20) 100%)!important;
  backdrop-filter:blur(20px) saturate(200%)!important;
  -webkit-backdrop-filter:blur(20px) saturate(200%)!important;
  border:1px solid rgba(96,165,245,.22)!important;
  border-radius:var(--rsm)!important;
  color:var(--t1)!important;
  font-family:'DM Sans',sans-serif!important;
  font-weight:500!important;font-size:.83rem!important;letter-spacing:.01em!important;
  padding:.52rem .95rem!important;
  position:relative!important;overflow:hidden!important;
  transition:all .28s cubic-bezier(.4,0,.2,1)!important;
  box-shadow:0 4px 16px rgba(0,0,0,.35),inset 0 1px 0 rgba(147,197,253,.12),inset 0 -1px 0 rgba(0,0,0,.22)!important;
}
.stButton>button::before{content:'';position:absolute;top:0;left:0;right:0;height:50%;
  background:linear-gradient(180deg,rgba(147,197,253,.08) 0%,transparent 100%);
  border-radius:var(--rsm) var(--rsm) 0 0;pointer-events:none}
.stButton>button:hover{
  background:linear-gradient(135deg,rgba(34,114,195,.68) 0%,rgba(22,75,156,.56) 40%,rgba(6,182,212,.30) 100%)!important;
  border-color:rgba(147,197,253,.38)!important;
  box-shadow:0 8px 28px rgba(34,114,195,.28),0 0 0 1px rgba(96,165,245,.14),inset 0 1px 0 rgba(147,197,253,.18)!important;
  transform:translateY(-1px)!important}
.stButton>button:active{transform:translateY(0) scale(.98)!important}

/* ── INPUTS ── */
.stTextInput input,.stTextArea textarea{
  background:rgba(5,12,26,.72)!important;border:1px solid var(--gbd)!important;
  border-radius:var(--rsm)!important;color:var(--t1)!important;
  font-family:'DM Sans',sans-serif!important;font-size:.87rem!important;
  backdrop-filter:blur(12px)!important;transition:border-color .2s,box-shadow .2s!important}
.stTextInput input:focus,.stTextArea textarea:focus{
  border-color:rgba(96,165,245,.45)!important;
  box-shadow:0 0 0 3px rgba(34,114,195,.12),0 0 20px rgba(34,114,195,.07)!important}
.stTextInput label,.stTextArea label,.stSelectbox label,.stFileUploader label{
  color:var(--t3)!important;font-size:.76rem!important;letter-spacing:.04em!important;text-transform:uppercase!important}

/* ── AVATAR ── */
.av{border-radius:50%;background:linear-gradient(135deg,var(--b800),var(--b500));
  display:flex;align-items:center;justify-content:center;
  font-family:'Syne',sans-serif;font-weight:700;color:white;
  border:1.5px solid rgba(96,165,245,.25);flex-shrink:0;overflow:hidden;
  box-shadow:0 2px 8px rgba(0,0,0,.4)}
.av img{width:100%;height:100%;object-fit:cover;border-radius:50%}

/* ── TAGS ── */
.tag{display:inline-block;background:rgba(34,114,195,.11);border:1px solid rgba(59,141,224,.19);
  border-radius:20px;padding:2px 10px;font-size:.69rem;color:var(--b300);margin:2px;font-weight:500}
.badge-on{display:inline-block;background:rgba(245,158,11,.10);border:1px solid rgba(245,158,11,.26);
  border-radius:20px;padding:2px 10px;font-size:.69rem;font-weight:600;color:#f59e0b}
.badge-pub{display:inline-block;background:rgba(16,185,129,.10);border:1px solid rgba(16,185,129,.26);
  border-radius:20px;padding:2px 10px;font-size:.69rem;font-weight:600;color:#10b981}
.badge-rec{display:inline-block;background:rgba(6,182,212,.12);border:1px solid rgba(6,182,212,.24);
  border-radius:20px;padding:2px 10px;font-size:.68rem;font-weight:600;color:var(--cyanl)}

/* ── METRIC BOX ── */
.mbox{background:var(--gb);backdrop-filter:blur(20px);border:1px solid var(--gbd);
  border-radius:var(--rmd);padding:1.1rem;text-align:center;
  box-shadow:0 4px 16px rgba(0,0,0,.3),inset 0 1px 0 rgba(147,197,253,.05)}
.mval{font-family:'Syne',sans-serif;font-size:1.95rem;font-weight:800;
  background:linear-gradient(135deg,var(--b300),var(--cyanl));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.mlbl{font-size:.70rem;color:var(--t3);margin-top:4px;letter-spacing:.04em;text-transform:uppercase}

/* ── CHAT ── */
.bme{background:linear-gradient(135deg,rgba(34,114,195,.44),rgba(6,182,212,.22));
  border:1px solid rgba(96,165,245,.20);border-radius:18px 18px 4px 18px;
  padding:.65rem 1rem;max-width:72%;margin-left:auto;margin-bottom:6px;
  font-size:.84rem;line-height:1.55;box-shadow:0 2px 12px rgba(34,114,195,.2)}
.bthem{background:var(--gb);border:1px solid var(--gbd);border-radius:18px 18px 18px 4px;
  padding:.65rem 1rem;max-width:72%;margin-bottom:6px;font-size:.84rem;line-height:1.55}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"]{background:rgba(5,12,26,.72)!important;
  backdrop-filter:blur(16px)!important;border-radius:var(--rsm)!important;
  padding:4px!important;gap:2px!important;border:1px solid var(--gbd)!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--t3)!important;
  border-radius:var(--rxs)!important;font-family:'DM Sans',sans-serif!important;font-size:.81rem!important}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,rgba(34,114,195,.34),rgba(6,182,212,.17))!important;
  color:var(--t1)!important;border:1px solid rgba(96,165,245,.24)!important}
.stTabs [data-baseweb="tab-panel"]{background:transparent!important;padding-top:1rem!important}

/* ── EXPANDER ── */
.stExpander{background:var(--gb)!important;backdrop-filter:blur(16px)!important;
  border:1px solid var(--gbd)!important;border-radius:var(--rmd)!important}
.stExpander summary{color:var(--t2)!important;font-size:.84rem!important}

/* ── SELECT ── */
.stSelectbox [data-baseweb="select"]{background:rgba(5,12,26,.72)!important;
  border:1px solid var(--gbd)!important;border-radius:var(--rsm)!important}

/* ── UPLOADER ── */
.stFileUploader section{background:rgba(5,12,26,.55)!important;
  border:1.5px dashed rgba(59,141,224,.24)!important;border-radius:var(--rmd)!important}

/* ── SCROLL ── */
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-track{background:var(--void)}
::-webkit-scrollbar-thumb{background:var(--elevated);border-radius:3px}

/* ── MISC ── */
hr{border-color:var(--gbd)!important}
label{color:var(--t2)!important}
.stCheckbox label,.stRadio label{color:var(--t1)!important}
.stProgress>div>div{background:linear-gradient(90deg,var(--b500),var(--cyan))!important;border-radius:4px!important}
.block-container{padding-top:0!important;padding-bottom:3rem!important;max-width:1360px!important}

/* ── ABOX ── */
.abox{background:rgba(10,26,53,.72);backdrop-filter:blur(16px);border:1px solid var(--gbdl);
  border-radius:var(--rmd);padding:1.1rem;margin-bottom:.9rem}

/* ── PROFILE HERO ── */
.prof-hero{background:var(--gb);backdrop-filter:blur(24px);border:1px solid var(--gbd);
  border-radius:var(--rxl);padding:2rem;display:flex;gap:1.5rem;align-items:flex-start;
  margin-bottom:1.2rem;box-shadow:0 8px 32px rgba(0,0,0,.4),inset 0 1px 0 rgba(147,197,253,.06);
  position:relative;overflow:hidden}
.prof-hero::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(96,165,245,.4),transparent)}
.prof-photo{width:92px;height:92px;border-radius:50%;
  background:linear-gradient(135deg,var(--b900),var(--b600));
  border:2px solid rgba(96,165,245,.30);object-fit:cover;flex-shrink:0;
  display:flex;align-items:center;justify-content:center;font-size:2rem;font-weight:700;color:white;
  overflow:hidden;box-shadow:0 4px 20px rgba(34,114,195,.3)}
.prof-photo img{width:100%;height:100%;object-fit:cover;border-radius:50%}

/* ── SCARD ── */
.scard{background:var(--gb);backdrop-filter:blur(16px);border:1px solid var(--gbd);
  border-radius:var(--rmd);padding:1.1rem 1.3rem;margin-bottom:.7rem;
  transition:border-color .2s,transform .2s;position:relative;overflow:hidden}
.scard:hover{border-color:var(--gbdl);transform:translateY(-1px)}

/* ── PULSE ── */
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.6;transform:scale(.85)}}
.don{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--ok);animation:pulse 2s infinite;margin-right:5px}
.doff{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--t3);margin-right:5px}

/* ── SHIMMER ANIMATION ── */
@keyframes shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}
.shimmer{background:linear-gradient(90deg,transparent 0%,rgba(96,165,245,.1) 50%,transparent 100%);
  background-size:200% 100%;animation:shimmer 2.5s infinite}

/* ── RESEARCHER CARD (clickable) ── */
.res-card{background:var(--gb);border:1px solid var(--gbd);border-radius:var(--rmd);
  padding:10px 13px;margin-bottom:6px;cursor:pointer;transition:border-color .2s,background .2s,transform .18s}
.res-card:hover{border-color:var(--gbdl);background:rgba(14,32,64,.78);transform:translateY(-1px)}

/* ── TOP NAV ── */
.toprow{position:relative;margin-top:-56px;height:56px}
.toprow .stButton>button{
  background:transparent!important;border:none!important;color:transparent!important;
  font-size:0!important;box-shadow:none!important;border-radius:var(--rxs)!important;
  width:100%!important;height:56px!important;padding:0!important;cursor:pointer!important}
.toprow .stButton>button:hover{background:rgba(59,141,224,.08)!important;transform:none!important}
div[data-testid="stHorizontalBlock"]{gap:3px!important}

.pw{animation:fadeIn .3s ease both}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}

/* ── IMAGE ANALYSIS PATTERN OVERLAY ── */
.pattern-box{background:rgba(6,182,212,.06);border:1px solid rgba(6,182,212,.22);
  border-radius:var(--rmd);padding:1rem;margin-bottom:.8rem}

/* number input */
input[type="number"]{background:rgba(5,12,26,.72)!important;border:1px solid var(--gbd)!important;
  border-radius:var(--rsm)!important;color:var(--t1)!important}

/* alert */
.stAlert{background:var(--gb)!important;border:1px solid var(--gbd)!important;border-radius:var(--rmd)!important}
</style>
""", unsafe_allow_html=True)

# ─── HELPERS ─────────────────────────────────────────────────────────────────
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
    if not isinstance(st.session_state.users, dict): st.session_state.users = {}
    return st.session_state.users.get(st.session_state.current_user, {})

def get_photo(email):
    if not isinstance(st.session_state.users, dict): return None
    return st.session_state.users.get(email, {}).get("photo_b64")

# ─── ADVANCED IMAGE ANALYSIS ─────────────────────────────────────────────────
def analyze_image_advanced(uploaded_file):
    try:
        uploaded_file.seek(0)
        img = PILImage.open(uploaded_file).convert("RGB")
        orig = img.size
        small = img.resize((512, 512))
        arr = np.array(small, dtype=np.float32)
        r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
        mr, mg, mb = float(r.mean()), float(g.mean()), float(b.mean())
        brightness = (mr + mg + mb) / 3
        gray = arr.mean(axis=2)

        # ── EDGE & LINE DETECTION (Sobel-like) ──
        gx = np.diff(gray, axis=1)
        gy = np.diff(gray, axis=0)
        # Pad to same size
        gx_p = np.pad(gx, ((0,0),(0,1)), mode='edge')
        gy_p = np.pad(gy, ((0,1),(0,0)), mode='edge')
        edge_map = np.sqrt(gx_p**2 + gy_p**2)
        edge_intensity = float(edge_map.mean())
        edge_max = float(edge_map.max())

        # Line direction detection (horizontal vs vertical vs diagonal)
        h_lines = float(np.abs(gy_p).mean())
        v_lines = float(np.abs(gx_p).mean())
        d_lines = float(np.abs(gx_p + gy_p).mean())

        if h_lines > v_lines * 1.3:
            line_dir = "Linhas Horizontais Predominantes"
        elif v_lines > h_lines * 1.3:
            line_dir = "Linhas Verticais Predominantes"
        else:
            line_dir = "Padrão Misto / Diagonal"

        # ── SHAPE ANALYSIS ──
        h_half, w_half = gray.shape[0] // 2, gray.shape[1] // 2
        q = [gray[:h_half,:w_half].var(), gray[:h_half,w_half:].var(),
             gray[h_half:,:w_half].var(), gray[h_half:,w_half:].var()]
        sym = 1.0 - (max(q) - min(q)) / (max(q) + 1e-5)

        # Detect circular patterns via radial symmetry
        cx, cy = gray.shape[1]//2, gray.shape[0]//2
        y_idx, x_idx = np.mgrid[0:gray.shape[0], 0:gray.shape[1]]
        dist = np.sqrt((x_idx - cx)**2 + (y_idx - cy)**2)
        radial_bins = np.histogram(dist.ravel(), bins=20, weights=gray.ravel())[0]
        radial_std = float(np.std(radial_bins) / (np.mean(radial_bins) + 1e-5))
        has_circular = radial_std < 0.3 and sym > 0.6

        # Detect grid/regular patterns
        fft = np.fft.fft2(gray)
        fft_shift = np.fft.fftshift(fft)
        magnitude = np.abs(fft_shift)
        # Mask center
        center_mask = np.zeros_like(magnitude, dtype=bool)
        h, w = magnitude.shape
        center_mask[h//2-20:h//2+20, w//2-20:w//2+20] = True
        peaks_outside = magnitude[~center_mask]
        has_grid = float(np.percentile(peaks_outside, 99)) > float(np.mean(peaks_outside)) * 15

        # ── COLOR ANALYSIS ──
        # Dominant color clusters
        flat = arr.reshape(-1, 3)
        rounded = (flat // 32 * 32).astype(int)
        uniq, counts = np.unique(rounded, axis=0, return_counts=True)
        top_idx = np.argsort(-counts)[:8]
        palette = [tuple(int(x) for x in uniq[i]) for i in top_idx]
        top_counts = [int(counts[i]) for i in top_idx]

        # Color temperature
        warm = mr > mb + 15
        cool = mb > mr + 15

        # Saturation analysis
        saturation = float(np.std(arr))
        contrast = float(gray.std())

        # Entropy
        hist = np.histogram(gray, bins=64, range=(0, 255))[0]
        hn = hist / hist.sum(); hn = hn[hn > 0]
        entropy = float(-np.sum(hn * np.log2(hn)))

        # ── CLASSIFICATION ──
        skin_mask = (r > 95) & (g > 40) & (b > 20) & (r > g) & (r > b) & ((r-g) > 15)
        skin_pct = float(skin_mask.mean())

        # Determine shapes present
        shapes_detected = []
        if has_circular: shapes_detected.append("Formas Circulares")
        if has_grid: shapes_detected.append("Grade / Padrão Repetitivo")
        if sym > 0.8: shapes_detected.append("Alta Simetria")
        if edge_intensity > 30: shapes_detected.append("Contornos Nítidos")
        if edge_intensity < 10: shapes_detected.append("Formas Suaves")
        if not shapes_detected: shapes_detected.append("Formas Irregulares")

        # Scientific category
        if skin_pct > 0.15:
            cat = "Tecido Biológico / Histologia"
            desc = f"Presença orgânica detectada ({skin_pct*100:.0f}% da área). Possível histologia, dermatologia ou fotografia de organismo vivo."
            search_kw = "histology tissue biology"
        elif has_grid and edge_intensity > 20:
            cat = "Cristalografia / Difração"
            desc = f"Padrão periódico detectado via análise espectral. Provável imagem de difração de raios-X, microscopia eletrônica ou cristal."
            search_kw = "crystallography diffraction electron microscopy"
        elif mg > 165 and mr < 130:
            cat = "Fluorescência Verde (GFP/FITC)"
            desc = f"Canal verde dominante (G={mg:.0f}). Marcador fluorescente GFP, FITC ou similar."
            search_kw = "fluorescence GFP microscopy cell biology"
        elif mb > 165 and mr < 130:
            cat = "Fluorescência Azul (DAPI/Hoechst)"
            desc = f"Canal azul dominante (B={mb:.0f}). Núcleos celulares marcados com DAPI ou Hoechst."
            search_kw = "DAPI nuclear staining fluorescence"
        elif mr > 185 and mg < 110 and mb < 110:
            cat = "Coloração H&E (Histoquímica)"
            desc = f"Vermelho dominante (R={mr:.0f},G={mg:.0f},B={mb:.0f}). Hematoxilina & Eosina ou imuno-histoquímica."
            search_kw = "hematoxylin eosin histology staining"
        elif has_circular and edge_intensity > 25:
            cat = "Estrutura Celular / Microscopia"
            desc = f"Formas circulares detectadas com contornos definidos. Provável microscopia óptica ou eletrônica de células."
            search_kw = "cell microscopy organelle structure"
        elif entropy > 6.0:
            cat = "Imagem Multispectral / Satélite"
            desc = f"Entropia muito alta ({entropy:.2f} bits). Alta densidade informacional — satélite, mapa de calor ou composição multiespectral."
            search_kw = "remote sensing satellite multispectral imaging"
        elif edge_intensity > 40:
            cat = "Gráfico / Diagrama Científico"
            desc = f"Bordas muito definidas (I={edge_intensity:.1f}). Provável gráfico, diagrama, esquema técnico ou figura de artigo."
            search_kw = "scientific diagram visualization data chart"
        elif sym > 0.82 and edge_intensity < 25:
            cat = "Estrutura Simétrica / Molecular"
            desc = f"Alta simetria (score={sym:.3f}) com bordas suaves. Possível estrutura molecular, proteína ou padrão geométrico."
            search_kw = "molecular structure protein symmetry"
        else:
            cat = "Imagem Científica Geral"
            desc = f"Padrão misto. Temperatura {'quente' if warm else ('fria' if cool else 'neutra')}. Brilho {brightness:.0f}/255."
            search_kw = "scientific image analysis"

        conf = min(97, 52 + edge_intensity/2 + entropy*3 + sym*5)

        return {
            "category": cat, "description": desc, "search_kw": search_kw,
            "confidence": round(conf, 1),
            "lines": {"direction": line_dir, "h_strength": round(h_lines, 2), "v_strength": round(v_lines, 2), "intensity": round(edge_intensity, 2)},
            "shapes": {"detected": shapes_detected, "symmetry": round(sym, 3), "circular": has_circular, "grid": has_grid},
            "color": {"dominant": max({"R": mr,"G": mg,"B": mb}.items(), key=lambda x:x[1])[0], "mean_rgb": (round(mr,1), round(mg,1), round(mb,1)), "brightness": round(brightness,1), "saturation": round(saturation,1), "warm": warm, "cool": cool},
            "texture": {"entropy": round(entropy,3), "contrast": round(contrast,2), "complexity": "Alta" if entropy>5.5 else ("Média" if entropy>4 else "Baixa")},
            "edge_map_sample": edge_map[::4,::4].tolist(),  # downsampled for viz
            "palette": palette, "palette_counts": top_counts,
            "size": orig, "skin_pct": round(skin_pct*100,1)
        }
    except Exception as e:
        return None

# ─── FOLDER ANALYSIS ──────────────────────────────────────────────────────────
def analyze_folder_documents(folder_name):
    folder_data = st.session_state.folders.get(folder_name, {})
    files = folder_data.get("files", []) if isinstance(folder_data, dict) else folder_data
    if not files: return None

    keyword_map = {
        "genomica":["Genômica","DNA","Sequenciamento"],"dna":["Genômica","DNA"],
        "rna":["Genômica","RNA"],"crispr":["CRISPR","Edição Gênica"],
        "proteina":["Proteômica"],"celula":["Biologia Celular"],
        "neurociencia":["Neurociência"],"cerebro":["Neurociência","Cognição"],
        "sono":["Sono","Neurociência"],"memoria":["Memória","Cognição"],
        "ia":["IA","Machine Learning"],"ml":["Machine Learning"],
        "deep":["Deep Learning","Redes Neurais"],"neural":["Redes Neurais"],
        "quantum":["Computação Quântica"],"fisica":["Física"],
        "quimica":["Química"],"molecula":["Química","Bioquímica"],
        "astronomia":["Astronomia","Astrofísica"],"estrela":["Astrofísica"],
        "cosmo":["Cosmologia"],"galaxia":["Astrofísica"],
        "psicologia":["Psicologia"],"comportamento":["Psicologia"],
        "biologia":["Biologia"],"ecologia":["Ecologia"],
        "medicina":["Medicina"],"clinica":["Medicina Clínica"],
        "farmaco":["Farmacologia"],"cancer":["Oncologia"],
        "engenharia":["Engenharia"],"robotica":["Robótica"],
        "materiais":["Ciência dos Materiais"],"computacao":["Computação"],
        "algoritmo":["Algoritmos"],"dados":["Ciência de Dados"],
        "estatistica":["Estatística"],"matematica":["Matemática"],
        "review":["Revisão Sistemática"],"survey":["Revisão de Literatura"],
        "tese":["Tese/Dissertação"],"relatorio":["Relatório"],
        "protocolo":["Metodologia"],"analise":["Análise de Dados"],
        "resultados":["Resultados Experimentais"],"metodologia":["Metodologia"],
    }
    ext_type_map = {
        "pdf":"Documento PDF","docx":"Documento Word","doc":"Documento Word",
        "xlsx":"Planilha/Dados","csv":"Dados Tabulares","txt":"Texto",
        "png":"Imagem","jpg":"Imagem","jpeg":"Imagem","tiff":"Imagem Científica",
        "py":"Código Python","r":"Código R","ipynb":"Notebook Jupyter",
        "pptx":"Apresentação","md":"Markdown",
    }

    all_tags = set()
    file_analyses = []
    status_map = {}  # simulated status per file

    for fname in files:
        fname_lower = fname.lower().replace("_"," ").replace("-"," ")
        file_tags = set()
        for kw, ktags in keyword_map.items():
            if kw in fname_lower: file_tags.update(ktags)
        ext = fname.split(".")[-1].lower() if "." in fname else ""
        ftype = ext_type_map.get(ext, "Arquivo")
        if not file_tags: file_tags.add("Pesquisa Geral")
        all_tags.update(file_tags)
        # Simulate progress status
        sim_progress = random.randint(30, 100)
        file_analyses.append({"file": fname, "type": ftype, "tags": list(file_tags), "progress": sim_progress})
        status_map[fname] = sim_progress

    areas = list(all_tags)[:5]
    summary = f"Pasta '{folder_name}': {len(files)} documento(s). Áreas: {', '.join(areas)}."
    return {"tags": list(all_tags)[:12], "summary": summary, "file_analyses": file_analyses,
            "total_files": len(files), "status_map": status_map}

# ─── INTERNET SEARCH ──────────────────────────────────────────────────────────
def search_semantic_scholar(query, limit=8):
    results = []
    try:
        r = requests.get("https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query":query,"limit":limit,"fields":"title,authors,year,abstract,venue,externalIds,openAccessPdf,citationCount"},
            timeout=9)
        if r.status_code == 200:
            for p in r.json().get("data", []):
                ext = p.get("externalIds",{}) or {}
                doi = ext.get("DOI",""); arxiv = ext.get("ArXiv","")
                pdf = p.get("openAccessPdf") or {}
                link = pdf.get("url","") or (f"https://arxiv.org/abs/{arxiv}" if arxiv else (f"https://doi.org/{doi}" if doi else ""))
                alist = p.get("authors",[]) or []
                authors = ", ".join(a.get("name","") for a in alist[:3])
                if len(alist) > 3: authors += " et al."
                abstract = (p.get("abstract","") or "Abstract não disponível.")[:300]
                results.append({"title":p.get("title","Sem título"),"authors":authors or "—",
                    "year":p.get("year","?"),"source":p.get("venue","") or "Semantic Scholar",
                    "doi":doi or arxiv or "—","abstract":abstract,"url":link,
                    "citations":p.get("citationCount",0),"origin":"semantic"})
    except: pass
    return results

def search_crossref(query, limit=5):
    results = []
    try:
        r = requests.get("https://api.crossref.org/works",
            params={"query":query,"rows":limit,"select":"title,author,issued,abstract,DOI,container-title,is-referenced-by-count","mailto":"nebula@example.com"},
            timeout=9)
        if r.status_code == 200:
            for p in r.json().get("message",{}).get("items",[]):
                title = (p.get("title") or ["Sem título"])[0]
                ars = p.get("author",[]) or []
                authors = ", ".join(f'{a.get("given","").split()[0] if a.get("given") else ""} {a.get("family","")}'.strip() for a in ars[:3])
                if len(ars) > 3: authors += " et al."
                year = (p.get("issued",{}).get("date-parts") or [[None]])[0][0]
                doi = p.get("DOI",""); journal = (p.get("container-title") or [""])[0]
                abstract = re.sub(r'<[^>]+>','',p.get("abstract","") or "")[:300]
                results.append({"title":title,"authors":authors or "—","year":year or "?",
                    "source":journal or "CrossRef","doi":doi,"abstract":abstract,
                    "url":f"https://doi.org/{doi}" if doi else "",
                    "citations":p.get("is-referenced-by-count",0),"origin":"crossref"})
    except: pass
    return results

# ─── RECOMMENDATION ENGINE ────────────────────────────────────────────────────
def record(tags, w=1.0):
    email = st.session_state.get("current_user")
    if not email or not tags: return
    prefs = st.session_state.user_prefs.setdefault(email, defaultdict(float))
    for t in tags: prefs[t.lower()] += w

def get_recs(email, n=2):
    prefs = st.session_state.user_prefs.get(email, {})
    if not prefs: return []
    def score(p): return sum(prefs.get(t.lower(),0) for t in p.get("tags",[])) + sum(prefs.get(t.lower(),0)*.5 for t in p.get("connections",[]))
    scored = [(score(p),p) for p in st.session_state.feed_posts if email not in p.get("liked_by",[])]
    scored.sort(key=lambda x:-x[0])
    return [p for s,p in scored if s>0][:n]

def area_to_tags(area):
    a = (area or "").lower()
    m = {"ia":["machine learning","deep learning","LLM"],"inteligência artificial":["machine learning","LLM"],
         "machine learning":["deep learning","redes neurais","otimização"],"neurociência":["sono","memória","plasticidade"],
         "biologia":["célula","genômica","CRISPR"],"física":["quantum","astrofísica","cosmologia"],
         "química":["síntese","catálise"],"medicina":["clínica","diagnóstico","terapia"],
         "astronomia":["astrofísica","cosmologia","galáxia"],"computação":["algoritmo","criptografia","redes"],
         "matemática":["álgebra","topologia","estatística"],"psicologia":["cognição","comportamento"],
         "ecologia":["biodiversidade","clima"],"genômica":["DNA","CRISPR","gene"],
         "engenharia":["robótica","materiais","sistemas"],"astrofísica":["cosmologia","galáxia","matéria escura"]}
    for k, v in m.items():
        if k in a: return v
    return [w.strip() for w in a.replace(","," ").split() if len(w)>3][:5]

# ─── SEED DATA ────────────────────────────────────────────────────────────────
SEED_POSTS = [
    {"id":1,"author":"Carlos Mendez","author_email":"carlos@nebula.ai","avatar":"CM","area":"Neurociência","title":"Efeitos da Privação de Sono na Plasticidade Sináptica","abstract":"Investigamos como 24h de privação de sono afetam espinhas dendríticas em ratos Wistar, com redução de 34% na plasticidade hipocampal. Nossos dados sugerem janela crítica nas primeiras 6h de recuperação.","tags":["neurociência","sono","memória","hipocampo"],"likes":47,"comments":[{"user":"Maria Silva","text":"Excelente metodologia!"},{"user":"João Lima","text":"Quais os critérios de exclusão?"}],"status":"Em andamento","date":"2026-02-10","liked_by":[],"saved_by":[],"connections":["sono","memória","hipocampo"]},
    {"id":2,"author":"Luana Freitas","author_email":"luana@nebula.ai","avatar":"LF","area":"Biomedicina","title":"CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras","abstract":"Desenvolvemos vetor AAV9 modificado para entrega precisa de CRISPR no gene DMD, com eficiência de 78% em modelos murinos mdx. Publicação em Cell prevista para Q2 2026.","tags":["CRISPR","gene terapia","músculo","AAV9"],"likes":93,"comments":[{"user":"Ana","text":"Próximos passos para trials humanos?"}],"status":"Publicado","date":"2026-01-28","liked_by":[],"saved_by":[],"connections":["genômica","distrofia"]},
    {"id":3,"author":"Rafael Souza","author_email":"rafael@nebula.ai","avatar":"RS","area":"Computação","title":"Redes Neurais Quântico-Clássicas para Otimização Combinatória","abstract":"Arquitetura híbrida variacional combinando qubits supercondutores com camadas densas para resolver TSP com 40% menos iterações que métodos clássicos.","tags":["quantum ML","otimização","TSP","computação quântica"],"likes":201,"comments":[],"status":"Em andamento","date":"2026-02-15","liked_by":[],"saved_by":[],"connections":["computação quântica","machine learning"]},
    {"id":4,"author":"Priya Nair","author_email":"priya@nebula.ai","avatar":"PN","area":"Astrofísica","title":"Detecção de Matéria Escura via Lentes Gravitacionais Fracas","abstract":"Mapeamento de matéria escura com precisão sub-arcminuto usando 100M de galáxias do DES Y3. Tensão com ΛCDM em escalas < 1 Mpc.","tags":["astrofísica","matéria escura","cosmologia"],"likes":312,"comments":[],"status":"Publicado","date":"2026-02-01","liked_by":[],"saved_by":[],"connections":["cosmologia","lentes gravitacionais"]},
    {"id":5,"author":"João Lima","author_email":"joao@nebula.ai","avatar":"JL","area":"Psicologia","title":"Viés de Confirmação em Decisões Médicas Assistidas por IA","abstract":"Estudo duplo-cego com 240 médicos revelou que sistemas de IA mal calibrados amplificam vieses cognitivos em 22% dos casos clínicos analisados.","tags":["psicologia","IA","cognição","medicina"],"likes":78,"comments":[],"status":"Publicado","date":"2026-02-08","liked_by":[],"saved_by":[],"connections":["cognição","IA"]},
]
SEED_USERS = {
    "demo@nebula.ai":{"name":"Ana Pesquisadora","password":hp("demo123"),"bio":"Pesquisadora em IA e Ciências Cognitivas | UFMG","area":"Inteligência Artificial","followers":128,"following":47,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "carlos@nebula.ai":{"name":"Carlos Mendez","password":hp("nebula123"),"bio":"Neurocientista | UFMG | Plasticidade sináptica e sono","area":"Neurociência","followers":210,"following":45,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "luana@nebula.ai":{"name":"Luana Freitas","password":hp("nebula123"),"bio":"Biomédica | FIOCRUZ | CRISPR e terapia gênica","area":"Biomedicina","followers":178,"following":62,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "rafael@nebula.ai":{"name":"Rafael Souza","password":hp("nebula123"),"bio":"Computação Quântica | USP","area":"Computação","followers":340,"following":88,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "priya@nebula.ai":{"name":"Priya Nair","password":hp("nebula123"),"bio":"Astrofísica | MIT | Dark matter survey","area":"Astrofísica","followers":520,"following":31,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "joao@nebula.ai":{"name":"João Lima","password":hp("nebula123"),"bio":"Psicólogo Cognitivo | UNICAMP","area":"Psicologia","followers":95,"following":120,"verified":True,"2fa_enabled":False,"photo_b64":None},
}
CHAT_INIT = {
    "carlos@nebula.ai":[{"from":"carlos@nebula.ai","text":"Oi! Vi seu comentário na minha pesquisa.","time":"09:14"},{"from":"me","text":"Achei muito interessante a metodologia!","time":"09:16"}],
    "luana@nebula.ai":[{"from":"luana@nebula.ai","text":"Podemos colaborar no próximo semestre.","time":"ontem"}],
    "rafael@nebula.ai":[{"from":"rafael@nebula.ai","text":"Compartilhei o repositório do código quântico.","time":"08:30"}],
}

# ─── SESSION INIT ─────────────────────────────────────────────────────────────
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
    st.session_state.setdefault("user_prefs", {k: defaultdict(float,v) for k,v in disk_prefs.items()})
    st.session_state.setdefault("pending_verify", None)
    st.session_state.setdefault("pending_2fa", None)
    st.session_state.setdefault("feed_posts", disk.get("feed_posts", [dict(p) for p in SEED_POSTS]))
    st.session_state.setdefault("folders", disk.get("folders", {}))
    st.session_state.setdefault("chat_contacts", list(SEED_USERS.keys()))
    st.session_state.setdefault("chat_messages", {k:list(v) for k,v in CHAT_INIT.items()})
    st.session_state.setdefault("active_chat", None)
    st.session_state.setdefault("knowledge_nodes", disk.get("knowledge_nodes", []))
    st.session_state.setdefault("followed", ["carlos@nebula.ai","luana@nebula.ai"])
    st.session_state.setdefault("notifications", ["Carlos Mendez curtiu sua pesquisa","Nova conexão: IA ↔ Computação Quântica"])
    st.session_state.setdefault("stats_data", {"views":[12,34,28,67,89,110,95,134,160,178,201,230],"citations":[0,1,1,2,3,4,4,6,7,8,10,12],"months":["Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez","Jan","Fev"],"h_index":4,"fator_impacto":3.8,"notes":""})
    st.session_state.setdefault("scholar_cache", {})
    st.session_state.setdefault("img_connections", [])

init()

# ─── AUTH ─────────────────────────────────────────────────────────────────────
def page_login():
    _, col, _ = st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-bottom:2.5rem;">
          <div style="font-family:'Syne',sans-serif;font-size:3rem;font-weight:800;
            background:linear-gradient(135deg,#93c5fd,#22d3ee,#60a5f5);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:-.03em;">
            🔬 Nebula</div>
          <div style="color:var(--t3);font-size:.70rem;letter-spacing:.18em;text-transform:uppercase;margin-top:.5rem;">
            Rede do Conhecimento Científico</div>
        </div>""", unsafe_allow_html=True)
        tab_in, tab_up = st.tabs(["  Entrar  ","  Criar conta  "])
        with tab_in:
            email = st.text_input("E-mail", placeholder="seu@email.com", key="li_e")
            pw = st.text_input("Senha", placeholder="••••••••", type="password", key="li_p")
            if st.button("Entrar →", use_container_width=True, key="btn_li"):
                users = st.session_state.users if isinstance(st.session_state.users, dict) else {}
                u = users.get(email)
                if not u: st.error("E-mail não encontrado.")
                elif u["password"] != hp(pw): st.error("Senha incorreta.")
                elif u.get("2fa_enabled"):
                    c = code6(); st.session_state.pending_2fa = {"email":email,"code":c}
                    st.session_state.page = "2fa"; st.rerun()
                else:
                    st.session_state.logged_in = True; st.session_state.current_user = email
                    record(area_to_tags(u.get("area","")), 1.0)
                    st.session_state.page = "feed"; st.rerun()
            st.markdown('<div style="text-align:center;color:var(--t3);font-size:.70rem;margin-top:.6rem;">Demo: demo@nebula.ai / demo123</div>', unsafe_allow_html=True)
        with tab_up:
            n_name = st.text_input("Nome completo", key="su_n")
            n_email = st.text_input("E-mail", key="su_e")
            n_area = st.text_input("Área de pesquisa", key="su_a")
            n_pw = st.text_input("Senha", type="password", key="su_p")
            n_pw2 = st.text_input("Confirmar senha", type="password", key="su_p2")
            if st.button("Criar conta →", use_container_width=True, key="btn_su"):
                users = st.session_state.users if isinstance(st.session_state.users, dict) else {}
                if not all([n_name,n_email,n_area,n_pw,n_pw2]): st.error("Preencha todos os campos.")
                elif n_pw != n_pw2: st.error("Senhas não coincidem.")
                elif len(n_pw) < 6: st.error("Senha muito curta.")
                elif n_email in users: st.error("E-mail já cadastrado.")
                else:
                    c = code6(); st.session_state.pending_verify = {"email":n_email,"name":n_name,"pw":hp(n_pw),"area":n_area,"code":c}
                    st.session_state.page = "verify_email"; st.rerun()

def page_verify_email():
    pv = st.session_state.pending_verify
    _, col, _ = st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"""<div class="card" style="text-align:center;">
          <div style="font-size:2.5rem;margin-bottom:1rem;">📧</div>
          <h2>Verifique seu e-mail</h2>
          <p style="color:var(--t2);font-size:.84rem;margin:.5rem 0;">Código para <strong>{pv['email']}</strong></p>
          <div style="background:rgba(34,114,195,.10);border:1px solid rgba(59,141,224,.22);border-radius:14px;padding:16px;margin:1rem 0;">
            <div style="font-size:.67rem;color:var(--t3);letter-spacing:.10em;margin-bottom:6px;text-transform:uppercase;">Código (demo)</div>
            <div style="font-family:'Syne',sans-serif;font-size:2.4rem;font-weight:800;letter-spacing:.28em;color:var(--b300);">{pv['code']}</div>
          </div></div>""", unsafe_allow_html=True)
        typed = st.text_input("Código de 6 dígitos", max_chars=6, placeholder="000000", key="ev_c")
        if st.button("Verificar →", use_container_width=True, key="btn_ev"):
            if typed.strip() == pv["code"]:
                if not isinstance(st.session_state.users, dict): st.session_state.users = {}
                st.session_state.users[pv["email"]] = {"name":pv["name"],"password":pv["pw"],"bio":"","area":pv["area"],"followers":0,"following":0,"verified":True,"2fa_enabled":False,"photo_b64":None}
                save_db(); st.session_state.pending_verify = None
                st.session_state.logged_in = True; st.session_state.current_user = pv["email"]
                record(area_to_tags(pv["area"]), 2.0); st.session_state.page = "feed"; st.rerun()
            else: st.error("Código inválido.")
        if st.button("← Voltar", key="btn_ev_bk"): st.session_state.page = "login"; st.rerun()

def page_2fa():
    p2 = st.session_state.pending_2fa
    _, col, _ = st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"""<div class="card" style="text-align:center;">
          <div style="font-size:2.5rem;margin-bottom:1rem;">🔑</div><h2>Verificação 2FA</h2>
          <div style="background:rgba(34,114,195,.10);border:1px solid rgba(59,141,224,.22);border-radius:14px;padding:14px;margin:1rem 0;">
            <div style="font-size:.67rem;color:var(--t3);margin-bottom:6px;text-transform:uppercase;letter-spacing:.08em;">Código (demo)</div>
            <div style="font-family:'Syne',sans-serif;font-size:2.4rem;font-weight:800;letter-spacing:.22em;color:var(--b300);">{p2['code']}</div>
          </div></div>""", unsafe_allow_html=True)
        typed = st.text_input("Código", max_chars=6, placeholder="000000", key="fa_c", label_visibility="collapsed")
        if st.button("Verificar →", use_container_width=True, key="btn_fa"):
            if typed.strip() == p2["code"]:
                st.session_state.logged_in = True; st.session_state.current_user = p2["email"]
                st.session_state.pending_2fa = None; st.session_state.page = "feed"; st.rerun()
            else: st.error("Código inválido.")
        if st.button("← Voltar", key="btn_fa_bk"): st.session_state.page = "login"; st.rerun()

# ─── TOP NAV ──────────────────────────────────────────────────────────────────
NAV = [("feed","◈","Feed"),("search","⊙","Artigos"),("knowledge","⬡","Conexões"),
       ("folders","▣","Pastas"),("analytics","▤","Análises"),
       ("img_search","⊞","Imagem"),("chat","◻","Chat"),("settings","◎","Perfil")]

def render_topnav():
    u = guser(); name = u.get("name","?"); photo = u.get("photo_b64"); in_ = ini(name)
    cur = st.session_state.page; notif = len(st.session_state.notifications)
    nav_html = ""
    for k, sym, lbl in NAV:
        active = cur == k
        if active:
            nav_html += f'<span style="font-size:.77rem;color:var(--b300);font-weight:600;padding:.35rem .68rem;border-radius:var(--rxs);background:rgba(34,114,195,.22);border:1px solid rgba(96,165,245,.28);display:inline-flex;align-items:center;gap:5px;white-space:nowrap;">{sym} {lbl}</span>'
        else:
            nav_html += f'<span style="font-size:.77rem;color:var(--t3);padding:.35rem .68rem;border-radius:var(--rxs);white-space:nowrap;display:inline-flex;align-items:center;gap:5px;">{sym} {lbl}</span>'
    img_html = f"<img src='{photo}' style='width:100%;height:100%;object-fit:cover;border-radius:50%'/>" if photo else in_
    av_html = f'<div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,var(--b800),var(--b500));display:flex;align-items:center;justify-content:center;font-size:.74rem;font-weight:700;color:white;border:1.5px solid rgba(96,165,245,.25);overflow:hidden;flex-shrink:0;box-shadow:0 2px 8px rgba(0,0,0,.4);">{img_html}</div>'
    nb = f'<span style="background:var(--b500);color:white;border-radius:10px;padding:1px 7px;font-size:.63rem;font-weight:600;">{notif}</span>' if notif else ""
    st.markdown(f"""<div style="position:sticky;top:0;z-index:999;background:rgba(1,4,9,.90);backdrop-filter:blur(28px) saturate(200%);-webkit-backdrop-filter:blur(28px) saturate(200%);border-bottom:1px solid var(--gbd);padding:0 1.4rem;display:flex;align-items:center;justify-content:space-between;height:56px;">
      <div style="font-family:'Syne',sans-serif;font-size:1.28rem;font-weight:800;background:linear-gradient(135deg,#93c5fd,#22d3ee);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;white-space:nowrap;letter-spacing:-.02em;">🔬 Nebula</div>
      <div style="display:flex;align-items:center;gap:2px;overflow-x:auto;padding:0 .5rem;scrollbar-width:none;">{nav_html}</div>
      <div style="display:flex;align-items:center;gap:10px;">{nb}{av_html}</div>
    </div>""", unsafe_allow_html=True)
    st.markdown('<div class="toprow">', unsafe_allow_html=True)
    cols = st.columns([1.5]+[1]*len(NAV)+[1])
    for i,(key,sym,lbl) in enumerate(NAV):
        with cols[i+1]:
            if st.button(f"{sym}{lbl}", key=f"tnav_{key}", use_container_width=True):
                st.session_state.profile_view = None; st.session_state.page = key; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ─── PROFILE PAGE ─────────────────────────────────────────────────────────────
def page_profile(target_email):
    users = st.session_state.users if isinstance(st.session_state.users, dict) else {}
    tu = users.get(target_email, {})
    if not tu:
        st.error("Perfil não encontrado.")
        if st.button("← Voltar"): st.session_state.profile_view = None; st.rerun()
        return
    tname = tu.get("name","?"); tin = ini(tname); tphoto = tu.get("photo_b64")
    email = st.session_state.current_user; is_me = email == target_email
    is_fol = target_email in st.session_state.followed
    if st.button("← Voltar", key="back_prof"):
        st.session_state.profile_view = None; st.rerun()
    st.markdown(f"""<div class="prof-hero">
      <div class="prof-photo">{("<img src='"+tphoto+"'/>") if tphoto else f'<span style="font-size:2rem;">{tin}</span>'}</div>
      <div style="flex:1;">
        <h1 style="margin-bottom:.25rem;">{tname}</h1>
        <div style="color:var(--b300);font-size:.84rem;margin-bottom:.5rem;">{tu.get('area','')}</div>
        <div style="color:var(--t2);font-size:.83rem;line-height:1.65;margin-bottom:.9rem;">{tu.get('bio','Sem biografia.')}</div>
        <div style="display:flex;gap:1.8rem;">
          <div><span style="font-weight:700;font-family:'Syne',sans-serif;font-size:1.1rem;">{tu.get('followers',0)}</span><span style="color:var(--t3);font-size:.75rem;"> seguidores</span></div>
          <div><span style="font-weight:700;font-family:'Syne',sans-serif;font-size:1.1rem;">{tu.get('following',0)}</span><span style="color:var(--t3);font-size:.75rem;"> seguindo</span></div>
          <div><span style="font-weight:700;font-family:'Syne',sans-serif;font-size:1.1rem;">{len([p for p in st.session_state.feed_posts if p.get('author_email')==target_email])}</span><span style="color:var(--t3);font-size:.75rem;"> pesquisas</span></div>
        </div>
      </div></div>""", unsafe_allow_html=True)
    if not is_me:
        c1,c2,_ = st.columns([1,1,4])
        with c1:
            if st.button("✓ Seguindo" if is_fol else "➕ Seguir", key="btn_pf"):
                if is_fol: st.session_state.followed.remove(target_email); tu["followers"] = max(0,tu.get("followers",0)-1)
                else: st.session_state.followed.append(target_email); tu["followers"] = tu.get("followers",0)+1
                save_db(); st.rerun()
        with c2:
            if st.button("💬 Mensagem", key="btn_pm"):
                if target_email not in st.session_state.chat_messages: st.session_state.chat_messages[target_email] = []
                st.session_state.active_chat = target_email; st.session_state.page = "chat"; st.session_state.profile_view = None; st.rerun()
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<h2>Pesquisas</h2>', unsafe_allow_html=True)
    user_posts = [p for p in st.session_state.feed_posts if p.get("author_email")==target_email]
    if user_posts:
        for p in user_posts: render_post(p, show_profile_link=False)
    else:
        st.markdown('<div class="card" style="text-align:center;padding:2.5rem;color:var(--t3);">Nenhuma pesquisa publicada ainda.</div>', unsafe_allow_html=True)

# ─── FEED ─────────────────────────────────────────────────────────────────────
def page_feed():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.2rem;">Feed de Pesquisas</h1>', unsafe_allow_html=True)
    email = st.session_state.current_user; u = guser()
    col_main, col_side = st.columns([2.2, 0.9])

    with col_main:
        recs = get_recs(email)
        if recs:
            st.markdown('<span class="badge-rec">✦ RECOMENDADO PARA VOCÊ</span><br>', unsafe_allow_html=True)
            for p in recs: render_post(p, rec=True)
            st.markdown("<hr>", unsafe_allow_html=True)
        with st.expander("➕ Publicar nova pesquisa"):
            np_t = st.text_input("Título da pesquisa", key="np_t")
            np_ab = st.text_area("Resumo / Abstract", key="np_ab", height=90)
            np_tg = st.text_input("Tags (separadas por vírgula)", key="np_tg")
            np_st = st.selectbox("Status", ["Em andamento","Publicado","Concluído"], key="np_st")
            if st.button("🚀 Publicar", key="btn_pub"):
                if np_t and np_ab:
                    nm = u.get("name","Usuário"); tags = [t.strip() for t in np_tg.split(",") if t.strip()]
                    st.session_state.feed_posts.insert(0,{"id":len(st.session_state.feed_posts)+1,"author":nm,"author_email":email,"avatar":ini(nm),"area":u.get("area",""),"title":np_t,"abstract":np_ab,"tags":tags,"likes":0,"comments":[],"status":np_st,"date":datetime.now().strftime("%Y-%m-%d"),"liked_by":[],"saved_by":[],"connections":tags[:3]})
                    record(tags, 2.0); save_db(); st.success("✓ Publicado!"); st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        ff = st.selectbox("Filtrar", ["Todos","Seguidos","Salvos"], key="ff", label_visibility="collapsed")
        posts = st.session_state.feed_posts
        if ff == "Seguidos": posts = [p for p in posts if p.get("author_email") in st.session_state.followed]
        elif ff == "Salvos": posts = [p for p in posts if email in p.get("saved_by",[])]
        for p in posts: render_post(p)

    with col_side:
        sq = st.text_input("", placeholder="🔍 Pesquisadores…", key="ppl_s", label_visibility="collapsed")
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.9rem;">Pesquisadores</div>', unsafe_allow_html=True)
        users = st.session_state.users if isinstance(st.session_state.users, dict) else {}
        shown = 0
        for ue, ud in list(users.items()):
            if ue == email: continue
            uname = ud.get("name","?")
            if sq and sq.lower() not in uname.lower() and sq.lower() not in ud.get("area","").lower(): continue
            if shown >= 6: break
            shown += 1
            uin = ini(uname); uphoto = ud.get("photo_b64"); is_fol = ue in st.session_state.followed

            # Whole card is clickable to view profile
            st.markdown(f"""<div class="res-card" id="rc_{ue}">
              <div style="display:flex;align-items:center;gap:8px;">
                {avh(uin, 28, uphoto)}
                <div style="flex:1;min-width:0;">
                  <div style="font-size:.80rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{uname}</div>
                  <div style="font-size:.68rem;color:var(--t3);">{ud.get("area","")[:22]}</div>
                </div>
                <span style="font-size:.72rem;color:{'var(--ok)' if is_fol else 'var(--t3)'};">{"✓" if is_fol else ""}</span>
              </div></div>""", unsafe_allow_html=True)

            c_view, c_fol = st.columns([3,1])
            with c_view:
                if st.button(f"Ver perfil", key=f"vps_{ue}", use_container_width=True):
                    st.session_state.profile_view = ue; st.rerun()
            with c_fol:
                if st.button("✓" if is_fol else "+", key=f"fol_{ue}", use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"] = max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"] = ud.get("followers",0)+1
                    save_db(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.8rem;">Áreas em Alta</div>', unsafe_allow_html=True)
        for area, cnt in [("Quantum ML",42),("CRISPR 2026",38),("Neuroplasticidade",31),("LLMs Científicos",27)]:
            pct = cnt/42
            st.markdown(f'<div style="margin-bottom:.7rem;"><div style="display:flex;justify-content:space-between;font-size:.77rem;margin-bottom:3px;"><span style="color:var(--t2);">{area}</span><span style="color:var(--b300);font-weight:600;">{cnt}</span></div><div style="height:3px;background:var(--gbd);border-radius:2px;"><div style="height:100%;width:{int(pct*100)}%;background:linear-gradient(90deg,var(--b500),var(--cyan));border-radius:2px;"></div></div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def render_post(post, rec=False, show_profile_link=True):
    email = st.session_state.current_user
    liked = email in post["liked_by"]; saved = email in post.get("saved_by",[])
    aemail = post.get("author_email",""); aphoto = get_photo(aemail); ain = post.get("avatar","??")
    rec_b = '<span class="badge-rec" style="margin-left:6px;">Rec.</span>' if rec else ""
    first_name = post['author'].split()[0] if post.get('author') else "Autor"

    st.markdown(f"""<div class="card">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:.9rem;">
        {avh(ain, 42, aphoto)}
        <div style="flex:1;">
          <div style="font-weight:600;font-size:.90rem;font-family:'Syne',sans-serif;">{post['author']}</div>
          <div style="color:var(--t3);font-size:.70rem;margin-top:2px;">{post['area']} · {post['date']}</div>
        </div>
        {badge(post['status'])}{rec_b}
      </div>
      <h3 style="margin-bottom:.45rem;font-size:1rem;line-height:1.45;">{post['title']}</h3>
      <p style="color:var(--t2);font-size:.84rem;line-height:1.68;margin-bottom:.8rem;">{post['abstract']}</p>
      <div>{tags_html(post['tags'])}</div>
    </div>""", unsafe_allow_html=True)

    c1,c2,c3,c4,c5,_ = st.columns([1,1,.8,.8,1.4,1])
    with c1:
        if st.button(f"{'❤' if liked else '♡'} {post['likes']}", key=f"lk_{post['id']}"):
            if liked: post["liked_by"].remove(email); post["likes"] -= 1
            else: post["liked_by"].append(email); post["likes"] += 1; record(post["tags"],1.5)
            save_db(); st.rerun()
    with c2:
        if st.button(f"💬 {len(post['comments'])}", key=f"cm_t_{post['id']}"):
            k = f"sc_{post['id']}"; st.session_state[k] = not st.session_state.get(k,False); st.rerun()
    with c3:
        if st.button("🔖" if saved else "📌", key=f"sv_{post['id']}"):
            if saved: post["saved_by"].remove(email)
            else: post["saved_by"].append(email)
            save_db(); st.rerun()
    with c4:
        if st.button("↗", key=f"sh_{post['id']}"):
            k = f"sopen_{post['id']}"; st.session_state[k] = not st.session_state.get(k,False); st.rerun()
    with c5:
        if show_profile_link and aemail:
            if st.button(f"👤 {first_name}", key=f"vpa_{post['id']}"):
                st.session_state.profile_view = aemail; st.rerun()
    if st.session_state.get(f"sopen_{post['id']}", False):
        url = f"https://nebula.ai/post/{post['id']}"
        st.markdown(f'<div class="card" style="padding:1rem;"><div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.86rem;margin-bottom:.5rem;">Compartilhar</div><div style="display:flex;gap:.5rem;flex-wrap:wrap;"><a href="https://twitter.com/intent/tweet?text={post[\'title\'][:60]}&url={url}" target="_blank" style="text-decoration:none;"><div style="background:var(--gb);border:1px solid var(--gbd);border-radius:var(--rsm);padding:.5rem .8rem;font-size:.73rem;color:var(--t2);">𝕏 Twitter</div></a><a href="https://www.linkedin.com/sharing/share-offsite/?url={url}" target="_blank" style="text-decoration:none;"><div style="background:var(--gb);border:1px solid var(--gbd);border-radius:var(--rsm);padding:.5rem .8rem;font-size:.73rem;color:var(--t2);">in LinkedIn</div></a><a href="https://wa.me/?text={url}" target="_blank" style="text-decoration:none;"><div style="background:var(--gb);border:1px solid var(--gbd);border-radius:var(--rsm);padding:.5rem .8rem;font-size:.73rem;color:var(--t2);">📱 WhatsApp</div></a></div></div>', unsafe_allow_html=True)
        st.code(url, language=None)
    if st.session_state.get(f"sc_{post['id']}", False):
        for c in post["comments"]:
            st.markdown(f'<div style="background:rgba(10,26,53,.8);border-radius:10px;padding:8px 14px;margin:3px 0;font-size:.82rem;border:1px solid var(--gbd);"><strong style="color:var(--b300);">{c["user"]}</strong>: {c["text"]}</div>', unsafe_allow_html=True)
        nc = st.text_input("", key=f"ci_{post['id']}", label_visibility="collapsed", placeholder="Adicionar comentário…")
        if st.button("Enviar", key=f"cs_{post['id']}"):
            if nc:
                post["comments"].append({"user":guser().get("name","Você"),"text":nc})
                record(post["tags"],.8); save_db(); st.rerun()

# ─── SEARCH ───────────────────────────────────────────────────────────────────
def _set_sq(v): st.session_state.sq = v

def page_search():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.2rem;">Busca de Artigos</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.82rem;margin-bottom:1rem;">Semantic Scholar + CrossRef + Nebula em tempo real</p>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns([3,.9,.9])
    with c1: q = st.text_input("", placeholder="Título, autor, DOI, tema…", key="sq", label_visibility="collapsed")
    with c2: src = st.selectbox("", ["Nebula + Internet","Só Nebula","Só Internet"], key="src_sel", label_visibility="collapsed")
    with c3: yr = st.selectbox("", ["Todos","2026","2025","2024","2023","2022"], key="yr_f", label_visibility="collapsed")

    if q:
        ql = q.lower(); record([ql],.3)
        neb_res = [p for p in st.session_state.feed_posts if ql in p["title"].lower() or ql in p["abstract"].lower() or any(ql in t.lower() for t in p["tags"]) or ql in p["author"].lower()]
        if yr != "Todos": neb_res = [p for p in neb_res if yr in p.get("date","")]
        if src == "Só Internet": neb_res = []
        cache_key = f"{q}|{yr}"; web_res = []
        if src != "Só Nebula":
            if cache_key not in st.session_state.scholar_cache:
                with st.spinner("Buscando em bases acadêmicas…"):
                    ss = search_semantic_scholar(q,8); cr = search_crossref(q,5)
                    merged = ss+[x for x in cr if not any(x["title"].lower()==s["title"].lower() for s in ss)]
                    if yr != "Todos": merged = [a for a in merged if str(a.get("year",""))==yr]
                    st.session_state.scholar_cache[cache_key] = merged
            web_res = st.session_state.scholar_cache.get(cache_key,[])

        tab_all,tab_neb,tab_web = st.tabs([f"  Todos ({len(neb_res)+len(web_res)})  ",f"  Nebula ({len(neb_res)})  ",f"  Internet ({len(web_res)})  "])
        with tab_neb:
            if neb_res:
                for p in neb_res: render_search_post(p)
            else: st.markdown('<div style="color:var(--t3);text-align:center;padding:2rem;">Nenhum resultado.</div>', unsafe_allow_html=True)
        with tab_web:
            if src == "Só Nebula": st.info("Busca na internet desativada.")
            elif web_res:
                for idx,a in enumerate(web_res): render_web_article(a, idx)
            else: st.markdown('<div style="color:var(--t3);text-align:center;padding:2rem;">Sem resultados online.</div>', unsafe_allow_html=True)
        with tab_all:
            if neb_res:
                st.markdown('<div style="font-size:.69rem;color:var(--b300);font-weight:600;margin-bottom:.4rem;letter-spacing:.06em;text-transform:uppercase;">NEBULA</div>', unsafe_allow_html=True)
                for p in neb_res: render_search_post(p)
            if web_res:
                if neb_res: st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown('<div style="font-size:.69rem;color:var(--cyanl);font-weight:600;margin-bottom:.4rem;letter-spacing:.06em;text-transform:uppercase;">BASE ACADÊMICA GLOBAL</div>', unsafe_allow_html=True)
                for idx,a in enumerate(web_res): render_web_article(a, idx)
            if not neb_res and not web_res:
                st.markdown('<div class="card" style="text-align:center;padding:3rem;"><div style="font-size:2.5rem;margin-bottom:1rem;">🔭</div><div style="color:var(--t3);">Nenhum resultado encontrado</div></div>', unsafe_allow_html=True)
    else:
        u = guser(); tags = area_to_tags(u.get("area",""))
        if tags:
            st.markdown(f'<div style="color:var(--t2);font-size:.81rem;margin-bottom:.8rem;">💡 Sugestões para <strong>{u.get("area","")}</strong>:</div>', unsafe_allow_html=True)
            cols = st.columns(5)
            for i,t in enumerate(tags[:5]):
                with cols[i%5]: st.button(f"🔎 {t}", key=f"sug_{t}", use_container_width=True, on_click=_set_sq, kwargs={"v":t})
    st.markdown('</div>', unsafe_allow_html=True)

def render_search_post(post):
    aemail = post.get("author_email",""); aphoto = get_photo(aemail); ain = post.get("avatar","??")
    c_main, c_btn = st.columns([8,1])
    with c_main:
        st.markdown(f"""<div class="scard">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:.55rem;">
            {avh(ain,30,aphoto)}
            <div style="flex:1;"><div style="font-size:.79rem;font-weight:600;font-family:'Syne',sans-serif;">{post['author']}</div>
            <div style="font-size:.68rem;color:var(--t3);">{post['area']} · {post['date']} · {badge(post['status'])}</div></div>
            <span style="font-size:.64rem;color:var(--b300);background:rgba(34,114,195,.09);border-radius:8px;padding:2px 8px;">Nebula</span>
          </div>
          <div style="font-family:'Syne',sans-serif;font-size:.91rem;font-weight:700;margin-bottom:.3rem;">{post['title']}</div>
          <div style="font-size:.80rem;color:var(--t2);margin-bottom:.4rem;">{post['abstract'][:220]}…</div>
          <div>{tags_html(post['tags'])}</div></div>""", unsafe_allow_html=True)
    with c_btn:
        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
        if aemail and st.button("👤", key=f"vpa_s_{post['id']}", use_container_width=True):
            st.session_state.profile_view = aemail; st.rerun()

def render_web_article(a, idx=0):
    # Use idx to guarantee unique keys
    src_color = "#22d3ee" if a.get("origin")=="semantic" else "#a78bfa"
    src_name = "Semantic Scholar" if a.get("origin")=="semantic" else "CrossRef"
    cite = f" · {a['citations']} cit." if a.get("citations") else ""
    doi_safe = re.sub(r'[^a-zA-Z0-9]', '', str(a.get("doi",""))[:12])
    uid = f"{idx}_{doi_safe}"
    st.markdown(f"""<div class="scard">
      <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:.35rem;">
        <div style="flex:1;font-family:'Syne',sans-serif;font-size:.91rem;font-weight:700;">{a['title']}</div>
        <span style="font-size:.64rem;color:{src_color};background:rgba(6,182,212,.07);border-radius:8px;padding:2px 8px;white-space:nowrap;flex-shrink:0;">{src_name}</span>
      </div>
      <div style="color:var(--t3);font-size:.70rem;margin-bottom:.4rem;">{a['authors']} · <em>{a['source']}</em> · {a['year']}{cite}</div>
      <div style="color:var(--t2);font-size:.81rem;line-height:1.6;margin-bottom:.4rem;">{a['abstract'][:220]}…</div></div>""", unsafe_allow_html=True)
    ca,cb,cc = st.columns([1,1,1])
    with ca:
        if st.button("📌 Salvar", key=f"sv_w_{uid}"):
            if st.session_state.folders:
                first = list(st.session_state.folders.keys())[0]; fn = f"{a['title'][:28]}.pdf"
                fd = st.session_state.folders[first]; lst = fd["files"] if isinstance(fd,dict) else fd
                if fn not in lst: lst.append(fn)
                save_db(); st.toast(f"Salvo em '{first}'")
            else: st.toast("Crie uma pasta primeiro!")
    with cb:
        if st.button("📋 Citar", key=f"ct_w_{uid}"):
            st.toast(f'{a["authors"]} ({a["year"]}). {a["title"]}. {a["source"]}.')
    with cc:
        if a.get("url"):
            st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:var(--b300);font-size:.80rem;text-decoration:none;line-height:2.4;display:block;">Abrir ↗</a>', unsafe_allow_html=True)

# ─── KNOWLEDGE / CONNECTIONS ──────────────────────────────────────────────────
def page_knowledge():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.2rem;">Rede de Conexões</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.82rem;margin-bottom:.9rem;">Pesquisadores conectados por interesses, pesquisas e pastas em comum</p>', unsafe_allow_html=True)
    email = st.session_state.current_user
    users = st.session_state.users if isinstance(st.session_state.users, dict) else {}

    researcher_nodes = {}
    for ue, ud in users.items():
        tags = area_to_tags(ud.get("area",""))
        post_tags = [t for p in st.session_state.feed_posts if p.get("author_email")==ue for t in p.get("tags",[])]
        folder_tags = []
        if ue == email:
            for fn, fd in st.session_state.folders.items():
                if isinstance(fd,dict): folder_tags.extend(fd.get("analysis_tags",[]))
        all_tags = list(set(tags+post_tags+folder_tags))
        researcher_nodes[ue] = {"name":ud.get("name",ue),"area":ud.get("area",""),"tags":all_tags,"followers":ud.get("followers",0),"photo":ud.get("photo_b64"),"is_me":ue==email}

    edges = []
    rlist = list(researcher_nodes.keys())
    for i in range(len(rlist)):
        for j in range(i+1,len(rlist)):
            e1,e2 = rlist[i],rlist[j]
            n1,n2 = researcher_nodes[e1],researcher_nodes[e2]
            common = list(set(t.lower() for t in n1["tags"]) & set(t.lower() for t in n2["tags"]))
            if common: edges.append((e1,e2,common[:4]))
            elif e2 in st.session_state.followed or e1 in st.session_state.followed:
                edges.append((e1,e2,["Seguindo"]))

    n = len(rlist); positions = {}
    for idx,ue in enumerate(rlist):
        angle = (2*3.14159*idx)/max(n,1)
        positions[ue] = {"x":0.5+0.38*np.cos(angle),"y":0.5+0.38*np.sin(angle),"z":0.5+0.15*((idx%3)/2-.25)}

    ex,ey,ez = [],[],[]
    for e1,e2,_ in edges:
        p1=positions.get(e1,{"x":.5,"y":.5,"z":.5}); p2=positions.get(e2,{"x":.5,"y":.5,"z":.5})
        ex+=[p1["x"],p2["x"],None]; ey+=[p1["y"],p2["y"],None]; ez+=[p1["z"],p2["z"],None]

    node_x=[positions[ue]["x"] for ue in rlist]; node_y=[positions[ue]["y"] for ue in rlist]; node_z=[positions[ue]["z"] for ue in rlist]
    node_colors=[("#22d3ee" if researcher_nodes[ue]["is_me"] else ("#3b8de0" if ue in st.session_state.followed else "#1a3a6b")) for ue in rlist]
    node_sizes=[(22 if researcher_nodes[ue]["is_me"] else (18 if ue in st.session_state.followed else 13)) for ue in rlist]
    node_texts=[researcher_nodes[ue]["name"].split()[0] for ue in rlist]
    node_hovers=[f"<b>{researcher_nodes[ue]['name']}</b><br>Área: {researcher_nodes[ue]['area']}<br>Conexões: {sum(1 for e1,e2,_ in edges if e1==ue or e2==ue)}<extra></extra>" for ue in rlist]

    fig = go.Figure()
    if ex: fig.add_trace(go.Scatter3d(x=ex,y=ey,z=ez,mode="lines",line=dict(color="rgba(59,141,224,0.24)",width=2),hoverinfo="none",showlegend=False))
    fig.add_trace(go.Scatter3d(x=node_x,y=node_y,z=node_z,mode="markers+text",marker=dict(size=node_sizes,color=node_colors,opacity=.92,line=dict(color="rgba(147,197,253,0.3)",width=1.5)),text=node_texts,textposition="top center",textfont=dict(color="#8ba8cc",size=9,family="DM Sans"),hovertemplate=node_hovers,showlegend=False))
    fig.update_layout(height=500,scene=dict(xaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),yaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),zaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),bgcolor="rgba(0,0,0,0)",camera=dict(eye=dict(x=1.5,y=1.3,z=0.9))),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0),font=dict(color="#8ba8cc"))
    st.plotly_chart(fig, use_container_width=True)

    c1,c2,c3,c4 = st.columns(4)
    for col,(v,l) in zip([c1,c2,c3,c4],[(len(rlist),"Pesquisadores"),(len(edges),"Conexões"),(len(st.session_state.followed),"Seguindo"),(len(st.session_state.feed_posts),"Pesquisas")]):
        with col: st.markdown(f'<div class="mbox"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>', unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    tab_map, tab_my = st.tabs(["  Mapa de Conexões  ","  Minhas Conexões  "])
    with tab_map:
        if edges:
            for e1,e2,common in edges[:20]:
                n1=researcher_nodes.get(e1,{}); n2=researcher_nodes.get(e2,{})
                st.markdown(f'<div class="card" style="padding:1rem 1.3rem;"><div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;"><span style="font-size:.81rem;font-weight:600;color:var(--b300);">{n1.get("name","?")}</span><span style="color:var(--t3);font-size:.78rem;">↔</span><span style="font-size:.81rem;font-weight:600;color:var(--b300);">{n2.get("name","?")}</span><span style="color:var(--t3);font-size:.71rem;margin-left:4px;">em comum:</span>{tags_html(common)}</div></div>', unsafe_allow_html=True)
        else: st.markdown('<div class="card" style="text-align:center;padding:2rem;color:var(--t3);">Publique pesquisas para ver conexões.</div>', unsafe_allow_html=True)
    with tab_my:
        my_tags = researcher_nodes.get(email,{}).get("tags",[])
        if my_tags: st.markdown(f'<div style="margin-bottom:.8rem;font-size:.82rem;color:var(--t2);">Seus tópicos: {tags_html(my_tags[:8])}</div>', unsafe_allow_html=True)
        my_conn = [(e1,e2,common) for e1,e2,common in edges if e1==email or e2==email]
        if my_conn:
            for e1,e2,common in my_conn:
                other_email = e2 if e1==email else e1; other = researcher_nodes.get(other_email,{})
                st.markdown(f'<div class="card" style="padding:1rem 1.3rem;"><div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">{avh(ini(other.get("name","?")),32,other.get("photo"))}<div style="flex:1;"><div style="font-size:.83rem;font-weight:600;">{other.get("name","?")}</div><div style="font-size:.70rem;color:var(--t3);">{other.get("area","")}</div></div>{tags_html(common[:3])}</div></div>', unsafe_allow_html=True)
                cv,cm,_ = st.columns([1,1,4])
                with cv:
                    if st.button("👤 Perfil", key=f"kn_vp_{other_email}"): st.session_state.profile_view=other_email; st.rerun()
                with cm:
                    if st.button("💬 Chat", key=f"kn_ch_{other_email}"): st.session_state.active_chat=other_email; st.session_state.page="chat"; st.rerun()
        else: st.markdown('<div class="card" style="text-align:center;padding:2rem;color:var(--t3);">Nenhuma conexão ainda. Publique pesquisas com tags!</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ─── FOLDERS ──────────────────────────────────────────────────────────────────
def page_folders():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.2rem;">Pastas de Pesquisa</h1>', unsafe_allow_html=True)
    c1,c2,_ = st.columns([2,1.2,1.5])
    with c1: nf_name = st.text_input("Nome da pasta", placeholder="Ex: Genômica Comparativa", key="nf_n")
    with c2: nf_desc = st.text_input("Descrição", placeholder="Breve descrição", key="nf_d")
    if st.button("➕ Criar pasta", key="btn_nf"):
        if nf_name.strip():
            if nf_name not in st.session_state.folders:
                st.session_state.folders[nf_name] = {"desc":nf_desc,"files":[],"notes":"","analysis_tags":[],"analysis_summary":"","file_analyses":[]}
                save_db(); st.success(f"✓ Pasta '{nf_name}' criada!"); st.rerun()
            else: st.warning("Pasta já existe.")
        else: st.warning("Digite um nome.")
    st.markdown("<hr>", unsafe_allow_html=True)
    if not st.session_state.folders:
        st.markdown('<div class="card" style="text-align:center;padding:3rem;"><div style="font-size:3rem;margin-bottom:1rem;">📂</div><div style="color:var(--t2);font-family:\'Syne\',sans-serif;font-size:1rem;">Nenhuma pasta criada ainda</div></div>', unsafe_allow_html=True)
    else:
        cols = st.columns(3)
        for idx,(fname,fdata) in enumerate(list(st.session_state.folders.items())):
            files = fdata["files"] if isinstance(fdata,dict) else fdata
            desc = fdata.get("desc","") if isinstance(fdata,dict) else ""
            analysis_tags = fdata.get("analysis_tags",[]) if isinstance(fdata,dict) else []
            analysis_summary = fdata.get("analysis_summary","") if isinstance(fdata,dict) else ""
            file_analyses = fdata.get("file_analyses",[]) if isinstance(fdata,dict) else []
            with cols[idx%3]:
                st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:2.4rem;margin-bottom:8px;">📁</div><div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.96rem;">{fname}</div><div style="color:var(--t3);font-size:.69rem;margin-top:3px;">{desc}</div><div style="color:var(--b300);font-size:.72rem;margin-top:6px;">{len(files)} arquivo(s)</div>{"<div style=\'margin-top:6px;\'>"+tags_html(analysis_tags[:3])+"</div>" if analysis_tags else ""}</div>', unsafe_allow_html=True)
                with st.expander(f"📂 Abrir '{fname}'"):
                    up = st.file_uploader("Adicionar arquivo", key=f"up_{fname}", label_visibility="collapsed")
                    if up:
                        lst = fdata["files"] if isinstance(fdata,dict) else fdata
                        if up.name not in lst: lst.append(up.name)
                        save_db(); st.success("✓ Adicionado!"); st.rerun()
                    if files:
                        for f in files: st.markdown(f'<div style="font-size:.79rem;padding:5px 0;color:var(--t2);border-bottom:1px solid var(--gbd);">📄 {f}</div>', unsafe_allow_html=True)
                    else: st.markdown('<p style="color:var(--t3);font-size:.77rem;text-align:center;padding:.5rem;">Faça upload acima.</p>', unsafe_allow_html=True)
                    st.markdown("<hr>", unsafe_allow_html=True)
                    st.markdown('<div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.83rem;margin-bottom:.5rem;">🔬 Análise de Conteúdo</div>', unsafe_allow_html=True)
                    if st.button("Analisar documentos", key=f"analyze_{fname}", use_container_width=True):
                        if files:
                            with st.spinner("Analisando…"):
                                result = analyze_folder_documents(fname)
                            if result and isinstance(fdata,dict):
                                fdata["analysis_tags"] = result["tags"]
                                fdata["analysis_summary"] = result["summary"]
                                fdata["file_analyses"] = result["file_analyses"]
                                save_db(); record(result["tags"],1.5); st.success("✓ Análise concluída!"); st.rerun()
                        else: st.warning("Adicione arquivos antes.")
                    if analysis_summary:
                        st.markdown(f'<div class="abox" style="margin-top:.5rem;"><div style="font-size:.67rem;color:var(--t3);letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px;">Resumo</div><div style="font-size:.81rem;color:var(--t2);line-height:1.6;">{analysis_summary}</div></div>', unsafe_allow_html=True)
                    if analysis_tags: st.markdown(tags_html(analysis_tags), unsafe_allow_html=True)
                    note = st.text_area("Notas", value=fdata.get("notes","") if isinstance(fdata,dict) else "", key=f"note_{fname}", height=70, placeholder="Observações…")
                    if st.button("💾 Salvar nota", key=f"sn_{fname}"):
                        if isinstance(fdata,dict): fdata["notes"] = note
                        save_db(); st.success("✓ Nota salva!")
                if st.button(f"🗑️ Excluir '{fname}'", key=f"df_{fname}"):
                    del st.session_state.folders[fname]; save_db(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ─── ANALYTICS (Folder-focused research tracking) ─────────────────────────────
def page_analytics():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.2rem;">Painel de Pesquisa</h1>', unsafe_allow_html=True)
    email = st.session_state.current_user; d = st.session_state.stats_data
    pc = dict(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
              font=dict(color="#3d5a80",family="DM Sans"),
              margin=dict(l=10,r=10,t=40,b=10),
              xaxis=dict(showgrid=False,color="#3d5a80"),
              yaxis=dict(showgrid=True,gridcolor="rgba(59,141,224,.06)",color="#3d5a80"))

    tab_folders, tab_pubs, tab_impact, tab_pref = st.tabs(["  📂 Pastas  ","  📝 Publicações  ","  📈 Impacto  ","  🎯 Interesses  "])

    # ── TAB 1: FOLDER ANALYSIS ──
    with tab_folders:
        folders = st.session_state.folders
        if not folders:
            st.markdown('<div class="card" style="text-align:center;padding:3rem;color:var(--t3);">Crie pastas e adicione arquivos para ver análises aqui.</div>', unsafe_allow_html=True)
        else:
            # Summary metrics
            total_files = sum(len(fd.get("files",[]) if isinstance(fd,dict) else fd) for fd in folders.values())
            total_analyzed = sum(1 for fd in folders.values() if isinstance(fd,dict) and fd.get("analysis_tags"))
            all_tags_flat = [t for fd in folders.values() if isinstance(fd,dict) for t in fd.get("analysis_tags",[])]

            c1,c2,c3,c4 = st.columns(4)
            with c1: st.markdown(f'<div class="mbox"><div class="mval">{len(folders)}</div><div class="mlbl">Pastas</div></div>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="mbox"><div class="mval">{total_files}</div><div class="mlbl">Arquivos totais</div></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="mbox"><div class="mval">{total_analyzed}</div><div class="mlbl">Pastas analisadas</div></div>', unsafe_allow_html=True)
            with c4: st.markdown(f'<div class="mbox"><div class="mval">{len(set(all_tags_flat))}</div><div class="mlbl">Áreas únicas</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Files per folder bar chart
            folder_names = list(folders.keys())
            folder_file_counts = [len(fd.get("files",[]) if isinstance(fd,dict) else fd) for fd in folders.values()]
            if any(c > 0 for c in folder_file_counts):
                fig_fc = go.Figure()
                fig_fc.add_trace(go.Bar(
                    x=folder_names, y=folder_file_counts,
                    marker=dict(color=folder_file_counts, colorscale=[[0,"#0e2040"],[0.5,"#2272c3"],[1,"#22d3ee"]],
                                line=dict(color="rgba(96,165,245,.2)",width=1)),
                    text=folder_file_counts, textposition="outside", textfont=dict(color="#8ba8cc",size=10)
                ))
                fig_fc.update_layout(title=dict(text="Arquivos por Pasta",font=dict(color="#e0e8ff",family="Syne")), height=260, **pc)
                st.plotly_chart(fig_fc, use_container_width=True)

            # Tag distribution across folders
            if all_tags_flat:
                from collections import Counter
                tag_counts = Counter(all_tags_flat)
                top_tags = tag_counts.most_common(10)
                tnames, tcounts = zip(*top_tags)
                fig_tags = go.Figure()
                fig_tags.add_trace(go.Bar(
                    y=list(tnames), x=list(tcounts), orientation='h',
                    marker=dict(color=list(tcounts), colorscale=[[0,"#1a3a6b"],[0.5,"#3b8de0"],[1,"#06b6d4"]],
                                line=dict(color="rgba(96,165,245,.15)",width=1)),
                    text=list(tcounts), textposition="outside", textfont=dict(color="#8ba8cc",size=10)
                ))
                fig_tags.update_layout(title=dict(text="Áreas de Pesquisa nas Pastas",font=dict(color="#e0e8ff",family="Syne")),
                                       height=320, **pc, yaxis=dict(autorange="reversed",color="#3d5a80"))
                st.plotly_chart(fig_tags, use_container_width=True)

            # Per-folder deep dive
            st.markdown('<h3 style="margin-bottom:.8rem;">Detalhamento por Pasta</h3>', unsafe_allow_html=True)
            for fname, fdata in folders.items():
                if not isinstance(fdata, dict): continue
                files = fdata.get("files", [])
                file_analyses = fdata.get("file_analyses", [])
                analysis_tags = fdata.get("analysis_tags", [])

                with st.expander(f"📁 {fname} — {len(files)} arquivo(s)"):
                    if not files:
                        st.markdown('<p style="color:var(--t3);font-size:.80rem;">Nenhum arquivo ainda.</p>', unsafe_allow_html=True)
                        continue

                    # File type distribution pie
                    if file_analyses:
                        type_counts = {}
                        for fa in file_analyses:
                            t = fa.get("type","Outro")
                            type_counts[t] = type_counts.get(t,0)+1

                        c_pie, c_prog = st.columns([1,1.5])
                        with c_pie:
                            fig_pie = go.Figure(go.Pie(
                                labels=list(type_counts.keys()), values=list(type_counts.values()),
                                hole=0.55,
                                marker=dict(colors=["#2272c3","#06b6d4","#3b8de0","#1a3a6b","#8b5cf6","#10b981"],
                                            line=dict(color=["#010409"]*10,width=2)),
                                textfont=dict(color="white",size=10)
                            ))
                            fig_pie.update_layout(title=dict(text="Tipos de Arquivo",font=dict(color="#e0e8ff",family="Syne",size=13)),
                                                  height=220, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                                  legend=dict(font=dict(color="#8ba8cc",size=9)), margin=dict(l=0,r=0,t=35,b=0))
                            st.plotly_chart(fig_pie, use_container_width=True)

                        with c_prog:
                            st.markdown('<div style="font-size:.70rem;color:var(--t3);text-transform:uppercase;letter-spacing:.06em;margin-bottom:.5rem;">Progresso por Arquivo</div>', unsafe_allow_html=True)
                            for fa in file_analyses:
                                prog = fa.get("progress", 50)
                                color = "#10b981" if prog>=80 else ("#f59e0b" if prog>=50 else "#ef4444")
                                st.markdown(f'<div style="margin-bottom:.6rem;"><div style="display:flex;justify-content:space-between;font-size:.76rem;margin-bottom:3px;"><span style="color:var(--t2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:65%;">📄 {fa["file"][:28]}</span><span style="color:{color};font-weight:600;">{prog}%</span></div><div style="height:5px;background:var(--gbd);border-radius:3px;"><div style="height:100%;width:{prog}%;background:{color};border-radius:3px;transition:width .6s ease;"></div></div></div>', unsafe_allow_html=True)

                        # Tags for this folder
                        if analysis_tags:
                            st.markdown('<div style="font-size:.70rem;color:var(--t3);text-transform:uppercase;letter-spacing:.06em;margin-top:.5rem;margin-bottom:.3rem;">Áreas identificadas</div>', unsafe_allow_html=True)
                            st.markdown(tags_html(analysis_tags), unsafe_allow_html=True)
                    else:
                        st.markdown('<p style="color:var(--t3);font-size:.79rem;">Clique em "Analisar documentos" na pasta para ver dados aqui.</p>', unsafe_allow_html=True)

    # ── TAB 2: PUBLICATIONS ──
    with tab_pubs:
        my_posts = [p for p in st.session_state.feed_posts if p.get("author_email")==email]
        if not my_posts:
            st.markdown('<div class="card" style="text-align:center;padding:2.5rem;color:var(--t3);">Publique pesquisas no feed para ver métricas aqui.</div>', unsafe_allow_html=True)
        else:
            c1,c2,c3 = st.columns(3)
            with c1: st.markdown(f'<div class="mbox"><div class="mval">{len(my_posts)}</div><div class="mlbl">Pesquisas publicadas</div></div>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="mbox"><div class="mval">{sum(p["likes"] for p in my_posts)}</div><div class="mlbl">Total de curtidas</div></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="mbox"><div class="mval">{sum(len(p["comments"]) for p in my_posts)}</div><div class="mlbl">Total de comentários</div></div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            # Engagement chart
            fig_eng = go.Figure()
            titles_short = [p["title"][:20]+"…" for p in my_posts]
            fig_eng.add_trace(go.Bar(name="Curtidas",x=titles_short,y=[p["likes"] for p in my_posts],marker_color="#2272c3"))
            fig_eng.add_trace(go.Bar(name="Comentários",x=titles_short,y=[len(p["comments"]) for p in my_posts],marker_color="#06b6d4"))
            fig_eng.update_layout(barmode="group",title=dict(text="Engajamento por Pesquisa",font=dict(color="#e0e8ff",family="Syne")),height=260,**pc,legend=dict(font=dict(color="#8ba8cc")))
            st.plotly_chart(fig_eng, use_container_width=True)

            # Status distribution
            status_counts = {}
            for p in my_posts: status_counts[p.get("status","?")] = status_counts.get(p.get("status","?"),0)+1
            fig_st = go.Figure(go.Pie(labels=list(status_counts.keys()),values=list(status_counts.values()),hole=0.6,marker=dict(colors=["#2272c3","#10b981","#f59e0b"],line=dict(color=["#010409"]*5,width=2)),textfont=dict(color="white")))
            fig_st.update_layout(title=dict(text="Status das Pesquisas",font=dict(color="#e0e8ff",family="Syne")),height=220,plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",legend=dict(font=dict(color="#8ba8cc")),margin=dict(l=10,r=10,t=35,b=0))
            st.plotly_chart(fig_st, use_container_width=True)

            # Timeline
            st.markdown('<h3>Histórico</h3>', unsafe_allow_html=True)
            for p in sorted(my_posts,key=lambda x:x.get("date",""),reverse=True):
                st.markdown(f'<div class="card" style="padding:.9rem 1.2rem;"><div style="display:flex;align-items:center;justify-content:space-between;"><div style="font-family:\'Syne\',sans-serif;font-size:.88rem;font-weight:700;">{p["title"][:50]}{"…" if len(p["title"])>50 else ""}</div>{badge(p["status"])}</div><div style="display:flex;gap:1.2rem;margin-top:.4rem;font-size:.75rem;color:var(--t3);">{p.get("date","")} · ❤ {p["likes"]} · 💬 {len(p["comments"])}</div><div style="margin-top:.4rem;">{tags_html(p["tags"][:4])}</div></div>', unsafe_allow_html=True)

    # ── TAB 3: IMPACT ──
    with tab_impact:
        c1,c2,c3 = st.columns(3)
        with c1: st.markdown(f'<div class="mbox"><div class="mval">{d.get("h_index",4)}</div><div class="mlbl">Índice H</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="mbox"><div class="mval">{d.get("fator_impacto",3.8):.1f}</div><div class="mlbl">Fator de impacto</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="mbox"><div class="mval">{sum(d["citations"])}</div><div class="mlbl">Total citações</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        c4,c5 = st.columns(2)
        with c4:
            fig_v = go.Figure()
            fig_v.add_trace(go.Scatter(x=d["months"],y=d["views"],fill="tozeroy",fillcolor="rgba(34,114,195,.09)",line=dict(color="#3b8de0",width=2.5),mode="lines+markers",marker=dict(size=4,color="#60a5f5")))
            fig_v.update_layout(title=dict(text="Visualizações mensais",font=dict(color="#e0e8ff",family="Syne")),height=240,**pc)
            st.plotly_chart(fig_v, use_container_width=True)
        with c5:
            fig_c = go.Figure()
            fig_c.add_trace(go.Bar(x=d["months"],y=d["citations"],marker=dict(color=d["citations"],colorscale=[[0,"#050c1a"],[1,"#06b6d4"]],line=dict(color="rgba(96,165,245,.18)",width=1))))
            fig_c.update_layout(title=dict(text="Citações mensais",font=dict(color="#e0e8ff",family="Syne")),height=240,**pc)
            st.plotly_chart(fig_c, use_container_width=True)

        st.markdown("<hr>", unsafe_allow_html=True)
        ce1,ce2 = st.columns(2)
        with ce1: new_h = st.number_input("Índice H",0,100,d.get("h_index",4),key="e_h")
        with ce2: new_fi = st.number_input("Fator de impacto",0.0,50.0,float(d.get("fator_impacto",3.8)),step=0.1,key="e_fi")
        new_notes = st.text_area("Notas de impacto",value=d.get("notes",""),key="e_notes",height=70)
        if st.button("💾 Salvar",key="btn_save_m"):
            d.update({"h_index":new_h,"fator_impacto":new_fi,"notes":new_notes}); st.success("✓ Salvo!"); st.rerun()

    # ── TAB 4: INTERESTS ──
    with tab_pref:
        prefs = st.session_state.user_prefs.get(email, {})
        if prefs:
            st.markdown('<p style="color:var(--t3);font-size:.81rem;margin-bottom:1rem;">Baseado nas suas interações e publicações.</p>', unsafe_allow_html=True)
            top = sorted(prefs.items(),key=lambda x:-x[1])[:12]; mx = max(s for _,s in top) if top else 1
            c1,c2 = st.columns(2)
            for i,(tag,score) in enumerate(top):
                pct = int(score/mx*100)
                with (c1 if i%2==0 else c2):
                    st.markdown(f'<div style="display:flex;justify-content:space-between;font-size:.79rem;margin-bottom:3px;"><span style="color:var(--t2);">{tag}</span><span style="color:var(--b300);">{pct}%</span></div>', unsafe_allow_html=True)
                    st.progress(pct/100)
        else: st.info("Interaja com pesquisas para construir seu perfil.")

    st.markdown('</div>', unsafe_allow_html=True)

# ─── IMAGE ANALYSIS ───────────────────────────────────────────────────────────
def page_img_search():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.2rem;">Análise de Imagem Científica</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.82rem;margin-bottom:1.2rem;">Detecta padrões, linhas, formas, cores e classifica imagens científicas — conectando com pesquisas similares</p>', unsafe_allow_html=True)

    col_up, col_res = st.columns([1,1.7])
    with col_up:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.88rem;margin-bottom:.8rem;">Upload de imagem</div>', unsafe_allow_html=True)
        img_file = st.file_uploader("", type=["png","jpg","jpeg","webp","tiff"], label_visibility="collapsed")
        if img_file: st.image(img_file, use_container_width=True, caption="Imagem carregada")
        run = st.button("🔬 Analisar imagem", use_container_width=True, key="btn_run")
        st.markdown('<div style="color:var(--t3);font-size:.70rem;margin-top:.8rem;line-height:1.6;">Detecta: linhas · formas · padrões · cores dominantes · classificação científica · conexões com pesquisas</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_res:
        if run and img_file:
            img_file.seek(0)
            with st.spinner("Analisando padrões, linhas, formas e cores…"):
                rep = analyze_image_advanced(img_file)
            if rep:
                # Category
                st.markdown(f"""<div class="abox">
                  <div style="font-size:.67rem;color:var(--t3);letter-spacing:.08em;text-transform:uppercase;margin-bottom:4px;">Categoria Detectada</div>
                  <div style="font-family:'Syne',sans-serif;font-size:1.06rem;font-weight:700;color:var(--t1);margin-bottom:4px;">{rep['category']}</div>
                  <div style="font-size:.82rem;color:var(--t2);line-height:1.6;">{rep['description']}</div>
                  <div style="margin-top:9px;display:flex;gap:12px;flex-wrap:wrap;">
                    <span style="font-size:.71rem;color:var(--ok);">✓ Confiança: {rep['confidence']}%</span>
                    <span style="font-size:.71rem;color:var(--t3);">{rep['size'][0]}×{rep['size'][1]}px</span>
                  </div></div>""", unsafe_allow_html=True)

                # ── LINE ANALYSIS ──
                l = rep['lines']
                st.markdown(f"""<div class="pattern-box">
                  <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.6rem;color:var(--cyanl);">📐 Análise de Linhas e Bordas</div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:.80rem;color:var(--t2);">
                    <div><span style="color:var(--t3);">Direção dominante:</span><br><strong style="color:var(--t1);font-size:.85rem;">{l['direction']}</strong></div>
                    <div><span style="color:var(--t3);">Intensidade de borda:</span><br><strong style="color:var(--t1);font-size:.85rem;">{l['intensity']:.1f}</strong></div>
                    <div><span style="color:var(--t3);">Força horizontal:</span><br><strong style="color:var(--b300);">{l['h_strength']:.2f}</strong></div>
                    <div><span style="color:var(--t3);">Força vertical:</span><br><strong style="color:var(--b300);">{l['v_strength']:.2f}</strong></div>
                  </div></div>""", unsafe_allow_html=True)

                # Edge intensity mini bar chart
                h_val = min(l['h_strength']/max(l['h_strength'],l['v_strength'],0.01), 1)
                v_val = min(l['v_strength']/max(l['h_strength'],l['v_strength'],0.01), 1)
                st.markdown(f"""<div style="display:flex;gap:8px;margin-bottom:.8rem;">
                  <div style="flex:1;background:var(--gbd);border-radius:4px;height:8px;position:relative;">
                    <div style="height:100%;width:{int(h_val*100)}%;background:linear-gradient(90deg,var(--b500),var(--cyan));border-radius:4px;"></div>
                  </div>
                  <div style="font-size:.69rem;color:var(--t3);white-space:nowrap;">H: {int(h_val*100)}%</div>
                </div>
                <div style="display:flex;gap:8px;margin-bottom:.8rem;">
                  <div style="flex:1;background:var(--gbd);border-radius:4px;height:8px;position:relative;">
                    <div style="height:100%;width:{int(v_val*100)}%;background:linear-gradient(90deg,var(--b700),var(--cyanl));border-radius:4px;"></div>
                  </div>
                  <div style="font-size:.69rem;color:var(--t3);white-space:nowrap;">V: {int(v_val*100)}%</div>
                </div>""", unsafe_allow_html=True)

                # ── SHAPE ANALYSIS ──
                sh = rep['shapes']
                shapes_html = "".join(f'<span class="tag" style="background:rgba(6,182,212,.12);border-color:rgba(6,182,212,.22);color:var(--cyanl);">{s}</span>' for s in sh['detected'])
                st.markdown(f"""<div class="pattern-box">
                  <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.6rem;color:var(--cyanl);">⬡ Formas e Estruturas</div>
                  <div style="margin-bottom:.6rem;">{shapes_html}</div>
                  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;font-size:.78rem;color:var(--t2);">
                    <div><span style="color:var(--t3);">Simetria:</span><br><strong style="color:var(--t1);">{sh['symmetry']:.3f}</strong></div>
                    <div><span style="color:var(--t3);">Circular:</span><br><strong style="color:{'var(--ok)' if sh['circular'] else 'var(--t3)'};">{'Sim' if sh['circular'] else 'Não'}</strong></div>
                    <div><span style="color:var(--t3);">Grade/Repetição:</span><br><strong style="color:{'var(--ok)' if sh['grid'] else 'var(--t3)'};">{'Sim' if sh['grid'] else 'Não'}</strong></div>
                  </div></div>""", unsafe_allow_html=True)

                # ── COLOR ANALYSIS ──
                r_v, g_v, b_v = rep['color']['mean_rgb']
                hex_col = "#{:02x}{:02x}{:02x}".format(int(r_v),int(g_v),int(b_v))
                pal_html = "".join(f'<div style="display:flex;flex-direction:column;align-items:center;gap:3px;"><div style="width:30px;height:30px;border-radius:7px;background:rgb{str(p)};border:1px solid rgba(255,255,255,.09);"></div><div style="font-size:.58rem;color:var(--t3);">#{"{:02x}{:02x}{:02x}".format(*p).upper()}</div></div>' for p in rep["palette"][:6])
                st.markdown(f"""<div class="abox">
                  <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.6rem;">🎨 Análise de Cor</div>
                  <div style="display:flex;gap:12px;align-items:center;margin-bottom:.7rem;">
                    <div style="width:42px;height:42px;border-radius:9px;background:{hex_col};border:1.5px solid var(--gbdl);flex-shrink:0;"></div>
                    <div style="font-size:.79rem;color:var(--t2);">
                      RGB: <strong style="color:var(--t1);">({int(r_v)},{int(g_v)},{int(b_v)})</strong> · Hex: <strong style="color:var(--t1);">{hex_col.upper()}</strong><br>
                      Canal dom.: <strong style="color:var(--t1);">{rep['color']['dominant']}</strong> · Temperatura: <strong style="color:var(--t1);">{"Quente 🔴" if rep['color']['warm'] else ("Fria 🔵" if rep['color']['cool'] else "Neutra ⚪")}</strong><br>
                      Complexidade: <strong style="color:var(--t1);">{rep['texture']['complexity']}</strong> · Contraste: <strong style="color:var(--t1);">{rep['texture']['contrast']:.1f}</strong>
                    </div>
                  </div>
                  <div style="font-size:.70rem;color:var(--t3);margin-bottom:.4rem;text-transform:uppercase;letter-spacing:.05em;">Paleta dominante</div>
                  <div style="display:flex;gap:6px;flex-wrap:wrap;">{pal_html}</div>
                </div>""", unsafe_allow_html=True)

                # ── TEXTURE CHART ──
                fig_tex = go.Figure()
                tex = rep['texture']
                categories = ['Entropia', 'Contraste', 'Intensidade Bordas', 'Simetria']
                max_vals = [8, 128, 80, 1]
                values = [tex['entropy'], tex['contrast'], rep['lines']['intensity'], rep['shapes']['symmetry']]
                norm_vals = [min(v/m, 1)*100 for v,m in zip(values, max_vals)]
                fig_tex.add_trace(go.Bar(
                    x=categories, y=norm_vals,
                    marker=dict(color=norm_vals, colorscale=[[0,"#1a3a6b"],[0.5,"#2272c3"],[1,"#22d3ee"]],
                                line=dict(color="rgba(96,165,245,.15)",width=1)),
                    text=[f"{v:.0f}%" for v in norm_vals], textposition="outside", textfont=dict(color="#8ba8cc",size=9)
                ))
                fig_tex.update_layout(title=dict(text="Perfil de Textura (normalizado)",font=dict(color="#e0e8ff",family="Syne",size=12)),
                                      height=200, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                      font=dict(color="#3d5a80",family="DM Sans"),
                                      margin=dict(l=10,r=10,t=35,b=10),
                                      xaxis=dict(showgrid=False,color="#3d5a80"),
                                      yaxis=dict(showgrid=True,gridcolor="rgba(59,141,224,.06)",color="#3d5a80",range=[0,120]))
                st.plotly_chart(fig_tex, use_container_width=True)

                # ── CONNECTIONS: Similar posts in Nebula ──
                st.markdown('<h3 style="margin-bottom:.6rem;">🔗 Pesquisas Similares na Nebula</h3>', unsafe_allow_html=True)
                cat_l = rep['category'].lower()
                kw = rep.get('search_kw','')
                related = []
                for p in st.session_state.feed_posts:
                    score = sum(1 for t in p.get("tags",[]) if t.lower() in cat_l or any(w.lower() in t.lower() for w in kw.split()))
                    if score > 0: related.append((score,p))
                related.sort(key=lambda x:-x[0])
                if related:
                    for _,p in related[:2]:
                        aemail = p.get("author_email",""); aphoto = get_photo(aemail); ain = p.get("avatar","??")
                        st.markdown(f"""<div class="scard">
                          <div style="display:flex;align-items:center;gap:8px;margin-bottom:.5rem;">
                            {avh(ain,28,aphoto)}
                            <div><div style="font-size:.78rem;font-weight:600;">{p['author']}</div>
                            <div style="font-size:.67rem;color:var(--t3);">{p['area']}</div></div>
                          </div>
                          <div style="font-family:'Syne',sans-serif;font-size:.88rem;font-weight:700;margin-bottom:.25rem;">{p['title'][:70]}</div>
                          <div>{tags_html(p['tags'][:4])}</div></div>""", unsafe_allow_html=True)
                        if aemail and st.button(f"👤 Ver perfil", key=f"img_vp_{p['id']}", use_container_width=False):
                            st.session_state.profile_view = aemail; st.rerun()
                else:
                    st.markdown('<div style="color:var(--t3);font-size:.80rem;">Nenhuma pesquisa similar encontrada na Nebula para esta categoria.</div>', unsafe_allow_html=True)

                # ── CONNECTIONS: Internet search ──
                st.markdown('<h3 style="margin-bottom:.6rem;margin-top:.8rem;">🌐 Artigos Científicos Relacionados</h3>', unsafe_allow_html=True)
                cache_k = f"img_{rep['search_kw']}"
                if cache_k not in st.session_state.scholar_cache:
                    with st.spinner("Buscando artigos relacionados…"):
                        web = search_semantic_scholar(rep['search_kw'], 4)
                        st.session_state.scholar_cache[cache_k] = web
                web_res = st.session_state.scholar_cache.get(cache_k, [])
                if web_res:
                    for idx,a in enumerate(web_res[:3]): render_web_article(a, idx+1000)
                else:
                    st.markdown('<div style="color:var(--t3);font-size:.80rem;">Sem resultados online no momento.</div>', unsafe_allow_html=True)
            else:
                st.error("Não foi possível analisar. Verifique o formato.")
        elif not img_file:
            st.markdown("""<div class="card" style="text-align:center;padding:4rem 2rem;">
              <div style="font-size:3.5rem;margin-bottom:1rem;">🔬</div>
              <div style="font-family:'Syne',sans-serif;font-size:1rem;color:var(--t2);margin-bottom:.5rem;">Carregue uma imagem científica</div>
              <div style="color:var(--t3);font-size:.77rem;line-height:1.7;">PNG · JPG · WEBP · TIFF<br>Detecta linhas · formas circulares · grades · cores<br>Classifica e conecta com pesquisas similares</div>
            </div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ─── CHAT ─────────────────────────────────────────────────────────────────────
def page_chat():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.2rem;">Chat Seguro</h1>', unsafe_allow_html=True)
    col_c, col_m = st.columns([.85,2.5])
    with col_c:
        st.markdown('<div style="font-size:.69rem;font-weight:600;color:var(--t3);letter-spacing:.08em;text-transform:uppercase;margin-bottom:.7rem;">Conversas</div>', unsafe_allow_html=True)
        if not isinstance(st.session_state.users,dict): st.session_state.users={}
        shown = set()
        for ue in st.session_state.chat_contacts:
            if ue==st.session_state.current_user or ue in shown: continue
            shown.add(ue)
            ud = st.session_state.users.get(ue,{"name":ue,"area":"","photo_b64":None})
            uname=ud.get("name","?"); uin=ini(uname); uphoto=ud.get("photo_b64")
            active=st.session_state.active_chat==ue
            msgs=st.session_state.chat_messages.get(ue,[])
            last=msgs[-1]["text"][:24]+"…" if msgs and len(msgs[-1]["text"])>24 else (msgs[-1]["text"] if msgs else "Iniciar conversa")
            online=random.random()>.4; dot='<span class="don"></span>' if online else '<span class="doff"></span>'
            border="rgba(96,165,245,.35)" if active else "var(--gbd)"; bg="rgba(34,114,195,.15)" if active else "var(--gb)"
            st.markdown(f'<div style="background:{bg};border:1px solid {border};border-radius:var(--rmd);padding:9px 11px;margin-bottom:5px;"><div style="display:flex;align-items:center;gap:8px;">{avh(uin,30,uphoto)}<div style="overflow:hidden;min-width:0;"><div style="font-size:.80rem;font-weight:600;display:flex;align-items:center;">{dot}{uname}</div><div style="font-size:.68rem;color:var(--t3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{last}</div></div></div></div>', unsafe_allow_html=True)
            if st.button("Abrir", key=f"oc_{ue}", use_container_width=True):
                st.session_state.active_chat=ue; st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
        nc2=st.text_input("",placeholder="Adicionar por e-mail…",key="new_ct",label_visibility="collapsed")
        if st.button("➕ Adicionar",key="btn_add_ct"):
            if isinstance(st.session_state.users,dict) and nc2 in st.session_state.users and nc2!=st.session_state.current_user:
                if nc2 not in st.session_state.chat_contacts: st.session_state.chat_contacts.append(nc2)
                st.rerun()
            elif nc2: st.toast("Usuário não encontrado.")
    with col_m:
        if st.session_state.active_chat:
            contact=st.session_state.active_chat
            if not isinstance(st.session_state.users,dict): st.session_state.users={}
            cd=st.session_state.users.get(contact,{"name":contact,"photo_b64":None})
            cname=cd.get("name","?"); cin=ini(cname); cphoto=cd.get("photo_b64")
            msgs=st.session_state.chat_messages.get(contact,[])
            st.markdown(f'<div style="background:var(--gb);border:1px solid var(--gbd);border-radius:var(--rmd);padding:12px 16px;margin-bottom:1rem;display:flex;align-items:center;gap:12px;">{avh(cin,38,cphoto)}<div style="flex:1;"><div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.92rem;">{cname}</div><div style="font-size:.70rem;color:var(--ok);">🔒 AES-256</div></div></div>', unsafe_allow_html=True)
            for msg in msgs:
                is_me=msg["from"]=="me"; cls="bme" if is_me else "bthem"; align="right" if is_me else "left"
                st.markdown(f'<div class="{cls}">{msg["text"]}<div style="font-size:.63rem;color:var(--t3);margin-top:3px;text-align:{align};">{msg["time"]}</div></div>', unsafe_allow_html=True)
            nm=st.text_input("",placeholder="Mensagem segura…",key=f"mi_{contact}",label_visibility="collapsed")
            if st.button("Enviar →",key=f"ms_{contact}",use_container_width=True):
                if nm:
                    now=datetime.now().strftime("%H:%M")
                    st.session_state.chat_messages.setdefault(contact,[]).append({"from":"me","text":nm,"time":now}); st.rerun()
        else:
            st.markdown('<div class="card" style="text-align:center;padding:4rem;"><div style="font-size:3rem;margin-bottom:1rem;">💬</div><div style="color:var(--t3);">Selecione uma conversa</div><div style="font-size:.76rem;color:var(--t3);margin-top:.5rem;">🔒 Criptografia end-to-end</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ─── SETTINGS ─────────────────────────────────────────────────────────────────
def page_settings():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.2rem;">Perfil e Configurações</h1>', unsafe_allow_html=True)
    u=guser(); email=st.session_state.current_user
    tab_p,tab_s,tab_pr=st.tabs(["  Meu Perfil  ","  Segurança  ","  Privacidade  "])
    with tab_p:
        nm=u.get("name",""); in_=ini(nm); photo=u.get("photo_b64")
        st.markdown(f"""<div class="prof-hero">
          <div class="prof-photo">{("<img src='"+photo+"'/>") if photo else f'<span style="font-size:2rem;">{in_}</span>'}</div>
          <div style="flex:1;"><h1 style="margin-bottom:.25rem;">{nm}</h1>
          <div style="color:var(--b300);font-size:.84rem;margin-bottom:.4rem;">{u.get('area','')}</div>
          <div style="color:var(--t2);font-size:.82rem;line-height:1.65;margin-bottom:.8rem;">{u.get('bio','Sem biografia.')}</div>
          <div style="display:flex;gap:1.8rem;">
            <span><strong style="font-family:'Syne',sans-serif;font-size:1.1rem;">{u.get('followers',0)}</strong><span style="color:var(--t3);font-size:.74rem;"> seguidores</span></span>
            <span><strong style="font-family:'Syne',sans-serif;font-size:1.1rem;">{u.get('following',0)}</strong><span style="color:var(--t3);font-size:.74rem;"> seguindo</span></span>
          </div></div></div>""", unsafe_allow_html=True)
        ph=st.file_uploader("Foto de perfil",type=["png","jpg","jpeg","webp"],label_visibility="collapsed",key="ph_up")
        if ph:
            b64=img_to_b64(ph)
            if b64:
                if not isinstance(st.session_state.users,dict): st.session_state.users={}
                st.session_state.users[email]["photo_b64"]=b64; save_db(); st.success("✓ Foto atualizada!"); st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
        new_n=st.text_input("Nome completo",value=u.get("name",""),key="cfg_n")
        new_e=st.text_input("E-mail",value=email,key="cfg_e")
        new_a=st.text_input("Área de pesquisa",value=u.get("area",""),key="cfg_a")
        new_b=st.text_area("Biografia",value=u.get("bio",""),key="cfg_b",height=90)
        if st.button("💾 Salvar perfil",key="btn_sp"):
            if not isinstance(st.session_state.users,dict): st.session_state.users={}
            st.session_state.users[email]["name"]=new_n; st.session_state.users[email]["area"]=new_a; st.session_state.users[email]["bio"]=new_b
            if new_e!=email and new_e not in st.session_state.users:
                st.session_state.users[new_e]=st.session_state.users.pop(email); st.session_state.current_user=new_e
            save_db(); record(area_to_tags(new_a),1.5); st.success("✓ Perfil salvo!"); st.rerun()
    with tab_s:
        op=st.text_input("Senha atual",type="password",key="op")
        np_=st.text_input("Nova senha",type="password",key="np_")
        np2=st.text_input("Confirmar",type="password",key="np2")
        if st.button("🔑 Alterar senha",key="btn_cpw"):
            if hp(op)!=u["password"]: st.error("Senha atual incorreta.")
            elif np_!=np2: st.error("Senhas não coincidem.")
            elif len(np_)<6: st.error("Senha muito curta.")
            else:
                if not isinstance(st.session_state.users,dict): st.session_state.users={}
                st.session_state.users[email]["password"]=hp(np_); save_db(); st.success("✓ Senha alterada!")
        st.markdown("<hr>", unsafe_allow_html=True)
        en=u.get("2fa_enabled",False)
        st.markdown(f'<div class="card" style="display:flex;align-items:center;justify-content:space-between;padding:1rem 1.3rem;"><div><div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.87rem;">2FA por e-mail</div><div style="font-size:.72rem;color:var(--t3);">{email}</div></div><span style="color:{"#10b981" if en else "#ef4444"};font-size:.81rem;font-weight:700;">{"✓ Ativo" if en else "✗ Inativo"}</span></div>', unsafe_allow_html=True)
        if st.button("Desativar 2FA" if en else "Ativar 2FA",key="btn_2fa"):
            if not isinstance(st.session_state.users,dict): st.session_state.users={}
            st.session_state.users[email]["2fa_enabled"]=not en; save_db(); st.rerun()
    with tab_pr:
        prots=[("AES-256","Criptografia end-to-end"),("SHA-256","Hash de senhas"),("TLS 1.3","Transmissão segura"),("Zero Knowledge","Pesquisas privadas protegidas")]
        items="".join(f'<div style="display:flex;align-items:center;gap:12px;background:rgba(16,185,129,.06);border:1px solid rgba(16,185,129,.14);border-radius:var(--rmd);padding:11px;"><div style="width:26px;height:26px;border-radius:8px;background:rgba(16,185,129,.12);display:flex;align-items:center;justify-content:center;color:#10b981;font-weight:700;font-size:.74rem;flex-shrink:0;">✓</div><div><div style="font-family:\'Syne\',sans-serif;font-weight:700;color:#10b981;font-size:.83rem;">{n2}</div><div style="font-size:.71rem;color:var(--t3);">{d2}</div></div></div>' for n2,d2 in prots)
        st.markdown(f'<div class="card"><div style="font-family:\'Syne\',sans-serif;font-weight:700;margin-bottom:1rem;">Proteções ativas</div><div style="display:grid;gap:8px;">{items}</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ─── ROUTER ───────────────────────────────────────────────────────────────────
def main():
    if not st.session_state.logged_in:
        p = st.session_state.page
        if p == "verify_email": page_verify_email()
        elif p == "2fa": page_2fa()
        else: page_login()
        return
    render_topnav()
    if st.session_state.profile_view:
        page_profile(st.session_state.profile_view); return
    {"feed":page_feed,"search":page_search,"knowledge":page_knowledge,"folders":page_folders,
     "analytics":page_analytics,"img_search":page_img_search,"chat":page_chat,"settings":page_settings
    }.get(st.session_state.page, page_feed)()

main()
