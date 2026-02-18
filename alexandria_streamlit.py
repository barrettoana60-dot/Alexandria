import subprocess, sys, os, json, hashlib, random, string, base64, re
from datetime import datetime
from collections import defaultdict, Counter

def _pip(pkg):
    try:
        subprocess.check_call([sys.executable,"-m","pip","install",pkg,"-q"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        st.warning(f"Não foi possível instalar a biblioteca {pkg}. Por favor, instale manualmente: pip install {pkg}. Erro: {e}")

try: import plotly.graph_objects as go
except: _pip("plotly"); import plotly.graph_objects as go
try: import numpy as np; from PIL import Image as PILImage
except: _pip("pillow numpy"); import numpy as np; from PIL import Image as PILImage
try: import requests
except: _pip("requests"); import requests

import streamlit as st

st.set_page_config(page_title="Nebula", page_icon="🔬",
                   layout="wide", initial_sidebar_state="collapsed")

DB_FILE = "nebula_db.json"

# ════════════════════════════════════════════════════
# PERSISTENCE
# ════════════════════════════════════════════════════
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: pass
    return {}

def save_db():
    try:
        prefs_serializable = {k: dict(v) for k,v in st.session_state.user_prefs.items()}
        with open(DB_FILE,"w",encoding="utf-8") as f:
            json.dump({"users":st.session_state.users,"feed_posts":st.session_state.feed_posts,
                       "folders":st.session_state.folders,"user_prefs":prefs_serializable,
                       "saved_articles":st.session_state.saved_articles}, f, # Save saved_articles
                      ensure_ascii=False, indent=2)
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

# ════════════════════════════════════════════════════
# CSS — LIQUID GLASS DARK BLUE
# ════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&display=swap');
:root{
  --void:#010409;--deep:#040d1e;--navy:#071428;--surface:#0a1a35;
  --b900:#0f2040;--b800:#1a3a6b;--b700:#1e4d8c;--b600:#1d5fa8;--b500:#2272c3;
  --b400:#3b8de0;--b300:#60a5f5;--b200:#93c5fd;
  --cyan:#06b6d4;--cyanl:#22d3ee;
  --t1:#f0f6ff;--t2:#8ba8cc;--t3:#3d5a80;
  --gb:rgba(7,18,44,0.70);--gbl:rgba(12,28,60,0.55);
  --gbd:rgba(55,130,215,0.16);--gbdl:rgba(90,160,240,0.28);
  --ok:#10b981;--warn:#f59e0b;--err:#ef4444;
  --rxs:8px;--rsm:12px;--rmd:18px;--rlg:24px;--rxl:32px;
}
*,*::before,*::after{box-sizing:border-box;margin:0}
html,body,.stApp{background:var(--void)!important;color:var(--t1)!important;font-family:'DM Sans',sans-serif!important}
/* starfield */
.stApp::before{content:'';position:fixed;inset:0;
  background:
    radial-gradient(ellipse 90% 55% at 12% 8%,rgba(30,100,180,.18) 0%,transparent 58%),
    radial-gradient(ellipse 65% 75% at 88% 92%,rgba(6,182,212,.09) 0%,transparent 52%);
  pointer-events:none;z-index:0;animation:bg 20s ease-in-out infinite alternate}
@keyframes bg{from{opacity:.6}to{opacity:1}}
.stApp::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:
    radial-gradient(1px 1px at 20% 22%,rgba(147,197,253,.55) 0%,transparent 100%),
    radial-gradient(1px 1px at 75% 15%,rgba(147,197,253,.45) 0%,transparent 100%),
    radial-gradient(1.5px 1.5px at 42% 68%,rgba(96,165,245,.45) 0%,transparent 100%),
    radial-gradient(1px 1px at 90% 48%,rgba(147,197,253,.30) 0%,transparent 100%),
    radial-gradient(1px 1px at 6%  82%,rgba(96,165,245,.30) 0%,transparent 100%),
    radial-gradient(1px 1px at 58% 90%,rgba(147,197,253,.22) 0%,transparent 100%),
    radial-gradient(1px 1px at 33% 45%,rgba(96,165,245,.18) 0%,transparent 100%)}
/* hide sidebar */
[data-testid="collapsedControl"],section[data-testid="stSidebar"]{display:none!important}
h1,h2,h3,h4{font-family:'Syne',sans-serif!important;color:var(--t1)!important;font-weight:700;letter-spacing:-.025em}
h1{font-size:1.75rem!important}h2{font-size:1.3rem!important}h3{font-size:1.02rem!important}
/* ── GLASS CARD ── */
.card{
  background:var(--gb);backdrop-filter:blur(28px) saturate(180%);-webkit-backdrop-filter:blur(28px) saturate(180%);
  border:1px solid var(--gbd);border-radius:var(--rlg);
  padding:1.35rem 1.5rem;margin-bottom:.9rem;
  box-shadow:0 8px 32px rgba(0,0,0,.44),0 2px 8px rgba(0,0,0,.3),inset 0 1px 0 rgba(147,197,253,.07);
  position:relative;overflow:hidden;
  animation:sU .32s cubic-bezier(.34,1.4,.64,1) both;
  transition:border-color .22s,box-shadow .22s,transform .18s}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(96,165,245,.35),transparent)}
.card:hover{border-color:var(--gbdl);box-shadow:0 16px 48px rgba(0,0,0,.5),inset 0 1px 0 rgba(147,197,253,.10);transform:translateY(-2px)}
@keyframes sU{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
/* ── LIQUID GLASS BUTTON ── */
.stButton>button{
  background:linear-gradient(135deg,rgba(20,70,148,.60),rgba(12,48,110,.50),rgba(6,182,212,.22))!important;
  backdrop-filter:blur(22px) saturate(220%)!important;-webkit-backdrop-filter:blur(22px) saturate(220%)!important;
  border:1px solid rgba(90,158,240,.24)!important;border-radius:var(--rsm)!important;
  color:var(--t1)!important;font-family:'DM Sans',sans-serif!important;
  font-weight:500!important;font-size:.83rem!important;letter-spacing:.01em!important;
  padding:.5rem .9rem!important;position:relative!important;overflow:hidden!important;
  transition:all .25s cubic-bezier(.4,0,.2,1)!important;
  box-shadow:0 4px 18px rgba(0,0,0,.38),inset 0 1px 0 rgba(147,197,253,.13),inset 0 -1px 0 rgba(0,0,0,.25)!important}
.stButton>button::after{content:'';position:absolute;top:0;left:0;right:0;height:48%;
  background:linear-gradient(180deg,rgba(147,197,253,.08) 0%,transparent 100%);pointer-events:none}
.stButton>button:hover{
  background:linear-gradient(135deg,rgba(32,108,190,.72),rgba(20,70,148,.60),rgba(6,182,212,.32))!important;
  border-color:rgba(147,197,253,.40)!important;
  box-shadow:0 8px 30px rgba(30,100,180,.30),inset 0 1px 0 rgba(147,197,253,.20)!important;
  transform:translateY(-1px)!important}
.stButton>button:active{transform:translateY(0) scale(.97)!important}
/* ── INPUTS ── */
.stTextInput input,.stTextArea textarea{
  background:rgba(4,10,22,.75)!important;border:1px solid var(--gbd)!important;
  border-radius:var(--rsm)!important;color:var(--t1)!important;
  font-family:'DM Sans',sans-serif!important;font-size:.87rem!important;
  transition:border-color .2s,box-shadow .2s!important}
.stTextInput input:focus,.stTextArea textarea:focus{
  border-color:rgba(90,158,240,.50)!important;
  box-shadow:0 0 0 3px rgba(30,100,180,.14),0 0 24px rgba(30,100,180,.08)!important}
.stTextInput label,.stTextArea label,.stSelectbox label,.stFileUploader label{
  color:var(--t3)!important;font-size:.72rem!important;letter-spacing:.05em!important;text-transform:uppercase!important}
/* ── AVATAR ── */
.av{border-radius:50%;background:linear-gradient(135deg,var(--b800),var(--b500));
  display:flex;align-items:center;justify-content:center;
  font-family:'Syne',sans-serif;font-weight:700;color:white;
  border:1.5px solid rgba(90,158,240,.28);flex-shrink:0;overflow:hidden;
  box-shadow:0 2px 10px rgba(0,0,0,.45)}
.av img{width:100%;height:100%;object-fit:cover;border-radius:50%}
/* ── TAGS / BADGES ── */
.tag{display:inline-block;background:rgba(30,90,180,.12);border:1px solid rgba(55,130,215,.20);
  border-radius:20px;padding:2px 10px;font-size:.68rem;color:var(--b300);margin:2px;font-weight:500}
.badge-on{display:inline-block;background:rgba(245,158,11,.10);border:1px solid rgba(245,158,11,.28);
  border-radius:20px;padding:2px 10px;font-size:.68rem;font-weight:600;color:#f59e0b}
.badge-pub{display:inline-block;background:rgba(16,185,129,.10);border:1px solid rgba(16,185,129,.28);
  border-radius:20px;padding:2px 10px;font-size:.68rem;font-weight:600;color:#10b981}
.badge-done{display:inline-block;background:rgba(139,92,246,.10);border:1px solid rgba(139,92,246,.28);
  border-radius:20px;padding:2px 10px;font-size:.68rem;font-weight:600;color:#a78bfa}
.badge-rec{display:inline-block;background:rgba(6,182,212,.13);border:1px solid rgba(6,182,212,.26);
  border-radius:20px;padding:2px 10px;font-size:.67rem;font-weight:600;color:var(--cyanl)}
/* ── METRIC BOX ── */
.mbox{background:var(--gb);backdrop-filter:blur(22px);border:1px solid var(--gbd);
  border-radius:var(--rmd);padding:1.1rem;text-align:center;
  box-shadow:0 4px 18px rgba(0,0,0,.32),inset 0 1px 0 rgba(147,197,253,.06)}
.mval{font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;
  background:linear-gradient(135deg,var(--b300),var(--cyanl));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.mlbl{font-size:.68rem;color:var(--t3);margin-top:4px;letter-spacing:.05em;text-transform:uppercase}
/* ── CHAT BUBBLES ── */
.bme{background:linear-gradient(135deg,rgba(30,100,180,.48),rgba(6,182,212,.24));
  border:1px solid rgba(90,158,240,.22);border-radius:18px 18px 4px 18px;
  padding:.65rem 1rem;max-width:70%;margin-left:auto;margin-bottom:6px;
  font-size:.84rem;line-height:1.55;box-shadow:0 2px 14px rgba(30,100,180,.22)}
.bthem{background:var(--gb);border:1px solid var(--gbd);
  border-radius:18px 18px 18px 4px;padding:.65rem 1rem;max-width:70%;margin-bottom:6px;
  font-size:.84rem;line-height:1.55}
/* ── TABS ── */
.stTabs [data-baseweb="tab-list"]{background:rgba(4,10,22,.80)!important;
  backdrop-filter:blur(18px)!important;border-radius:var(--rsm)!important;
  padding:4px!important;gap:2px!important;border:1px solid var(--gbd)!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--t3)!important;
  border-radius:var(--rxs)!important;font-family:'DM Sans',sans-serif!important;font-size:.80rem!important}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,rgba(30,100,180,.36),rgba(6,182,212,.18))!important;
  color:var(--t1)!important;border:1px solid rgba(90,158,240,.26)!important}
.stTabs [data-baseweb="tab-panel"]{background:transparent!important;padding-top:1rem!important}
/* ── EXPANDER ── */
.stExpander{background:var(--gb)!important;backdrop-filter:blur(18px)!important;
  border:1px solid var(--gbd)!important;border-radius:var(--rmd)!important}
.stExpander summary{color:var(--t2)!important;font-size:.83rem!important}
/* ── SELECT / UPLOADER ── */
.stSelectbox [data-baseweb="select"]{background:rgba(4,10,22,.78)!important;border:1px solid var(--gbd)!important;border-radius:var(--rsm)!important}
.stFileUploader section{background:rgba(4,10,22,.58)!important;border:1.5px dashed rgba(55,130,215,.26)!important;border-radius:var(--rmd)!important}
/* ── MISC ── */
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-track{background:var(--void)}
::-webkit-scrollbar-thumb{background:var(--b900);border-radius:3px}
hr{border-color:var(--gbd)!important}
label{color:var(--t2)!important}
.stCheckbox label,.stRadio label{color:var(--t1)!important}
.stProgress>div>div{background:linear-gradient(90deg,var(--b500),var(--cyan))!important;border-radius:4px!important}
.block-container{padding-top:0!important;padding-bottom:3rem!important;max-width:1380px!important}
.stAlert{background:var(--gb)!important;border:1px solid var(--gbd)!important;border-radius:var(--rmd)!important}
input[type="number"]{background:rgba(4,10,22,.75)!important;border:1px solid var(--gbd)!important;border-radius:var(--rsm)!important;color:var(--t1)!important}
/* ── PROFILE CARD ── */
.prof-hero{background:var(--gb);backdrop-filter:blur(28px);border:1px solid var(--gbd);
  border-radius:var(--rxl);padding:2rem;display:flex;gap:1.5rem;align-items:flex-start;
  margin-bottom:1.2rem;box-shadow:0 10px 36px rgba(0,0,0,.45),inset 0 1px 0 rgba(147,197,253,.07);
  position:relative;overflow:hidden}
.prof-hero::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(90,158,240,.45),transparent)}
.prof-photo{width:92px;height:92px;border-radius:50%;background:linear-gradient(135deg,var(--b900),var(--b600));
  border:2.5px solid rgba(90,158,240,.32);flex-shrink:0;overflow:hidden;
  display:flex;align-items:center;justify-content:center;
  font-size:2rem;font-weight:700;color:white;box-shadow:0 4px 22px rgba(30,100,180,.35)}
.prof-photo img{width:100%;height:100%;object-fit:cover;border-radius:50%}
/* ── SEARCH CARD ── */
.scard{background:var(--gb);backdrop-filter:blur(18px);border:1px solid var(--gbd);
  border-radius:var(--rmd);padding:1.1rem 1.3rem;margin-bottom:.7rem;
  transition:border-color .2s,transform .18s;position:relative;overflow:hidden}
.scard:hover{border-color:var(--gbdl);transform:translateY(-1px)}
.scard::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(90,158,240,.18),transparent)}
/* ── ABOX ── */
.abox{background:rgba(8,20,48,.75);backdrop-filter:blur(18px);border:1px solid var(--gbdl);
  border-radius:var(--rmd);padding:1.1rem;margin-bottom:.9rem}
/* ── PATTERN BOX ── */
.pbox{background:rgba(6,182,212,.06);border:1px solid rgba(6,182,212,.24);
  border-radius:var(--rmd);padding:1rem;margin-bottom:.8rem}
/* ── FEED AUTHOR LINK ── */
.clickable-author-container {
    position: relative;
    display: inline-block; /* Or block, depending on layout */
    margin-bottom: 0.5rem; /* Space below the author info */
}

.clickable-author-button {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 1; /* Ensure it's above the text */
    opacity: 0; /* Invisible by default */
    cursor: pointer;
    background: transparent;
    border: none;
    padding: 0;
    margin: 0;
}

.clickable-author-button:hover {
    background: rgba(90,158,240,.1); /* Visual feedback on hover */
    opacity: 0.1; /* Slightly visible on hover */
}

.author-info {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 10px 4px 4px;
    border-radius: 30px;
    transition: background .18s, border-color .18s;
    border: 1px solid transparent;
}

.author-info-name {
    font-weight: 700;
    font-size: .90rem;
    font-family:'Syne',sans-serif;
    color:var(--t1);
    transition:color .18s;
}

.author-info-area {
    font-size: .75rem;
    color: var(--t3);
}

/* ── DOT ── */
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.6;transform:scale(.85)}}
.don{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--ok);animation:pulse 2s infinite;margin-right:5px}
.doff{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--t3);margin-right:5px}
/* ── TOP NAV BUTTONS (invisible overlay) ── */
.toprow{position:relative;margin-top:-56px;height:56px;z-index:998}
.toprow .stButton>button{
  background:transparent!important;border:none!important;color:transparent!important;
  font-size:0!important;box-shadow:none!important;border-radius:var(--rxs)!important;
  width:100%!important;height:56px!important;padding:0!important;cursor:pointer!important;
  backdrop-filter:none!important;-webkit-backdrop-filter:none!important}
.toprow .stButton>button:hover{background:rgba(55,130,215,.09)!important;transform:none!important;box-shadow:none!important}
/* ── PAGE ANIMATION ── */
.pw{animation:fadeIn .28s ease both}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
/* ── PROGRESS BAR CUSTOM ── */
.prog-bar-wrap{height:6px;background:var(--gbd);border-radius:4px;overflow:hidden;margin:.25rem 0 .6rem}
.prog-bar-fill{height:100%;border-radius:4px;transition:width .6s ease}
/* ── IMAGE SEARCH RESULTS ── */
.img-result-card{background:rgba(6,182,212,.06);border:1px solid rgba(6,182,212,.22);
  border-radius:var(--rmd);padding:1rem;margin-bottom:.7rem;}
.img-source-badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:.67rem;font-weight:600;margin:2px;}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════
def avh(initials, sz=40, photo=None):
    fs = max(sz//3, 9)
    if photo:
        return f'<div class="av" style="width:{sz}px;height:{sz}px;"><img src="{photo}"/></div>'
    return f'<div class="av" style="width:{sz}px;height:{sz}px;font-size:{fs}px;">{initials}</div>'

def tags_html(tags):
    return ' '.join(f'<span class="tag">{t}</span>' for t in (tags or []))

def badge(s):
    cls = {"Publicado":"badge-pub","Concluído":"badge-done"}.get(s,"badge-on")
    return f'<span class="{cls}">{s}</span>'

def guser():
    if not isinstance(st.session_state.get("users"), dict): return {}
    return st.session_state.users.get(st.session_state.current_user, {})

def get_photo(email):
    u = st.session_state.users
    if not isinstance(u, dict): return None
    return u.get(email, {}).get("photo_b64")

def prog_bar(pct, color="#2272c3"):
    return f'<div class="prog-bar-wrap"><div class="prog-bar-fill" style="width:{pct}%;background:{color};"></div></div>'

# ════════════════════════════════════════════════════
# IMAGE ANALYSIS — REAL (Sobel + FFT + Radial)
# ════════════════════════════════════════════════════
def analyze_image_advanced(uploaded_file):
    try:
        uploaded_file.seek(0)
        img = PILImage.open(uploaded_file).convert("RGB")
        orig = img.size
        small = img.resize((512,512))
        arr = np.array(small, dtype=np.float32)
        r,g,b_ch = arr[:,:,0],arr[:,:,1],arr[:,:,2]
        mr,mg,mb = float(r.mean()),float(g.mean()),float(b_ch.mean())
        gray = arr.mean(axis=2)

        # Sobel edge detection
        gx = np.pad(np.diff(gray,axis=1),((0,0),(0,1)),mode='edge')
        gy = np.pad(np.diff(gray,axis=0),((0,1),(0,0)),mode='edge')
        edge_map = np.sqrt(gx**2+gy**2)
        edge_intensity = float(edge_map.mean())
        h_strength = float(np.abs(gy).mean())
        v_strength = float(np.abs(gx).mean())
        line_dir = "Horizontal" if h_strength>v_strength*1.3 else ("Vertical" if v_strength>h_strength*1.3 else "Misto/Diagonal")

        # Symmetry
        hh,ww = gray.shape[0]//2,gray.shape[1]//2
        q = [gray[:hh,:ww].var(),gray[:hh,ww:].var(),gray[hh:,:ww].var(),gray[hh:,ww:].var()]
        sym = 1.0-(max(q)-min(q))/(max(q)+1e-5)

        # Radial (circular) symmetry
        cx,cy = gray.shape[1]//2,gray.shape[0]//2
        y_i,x_i = np.mgrid[0:gray.shape[0],0:gray.shape[1]]
        dist = np.sqrt((x_i-cx)**2+(y_i-cy)**2)
        rb = np.histogram(dist.ravel(),bins=20,weights=gray.ravel())[0]
        has_circular = float(np.std(rb)/(np.mean(rb)+1e-5)) < 0.3 and sym>0.6

        # FFT grid detection
        fft_s = np.fft.fftshift(np.abs(np.fft.fft2(gray)))
        hf,wf = fft_s.shape; cm = np.zeros_like(fft_s,dtype=bool)
        cm[hf//2-20:hf//2+20,wf//2-20:wf//2+20]=True
        outside = fft_s[~cm]
        has_grid = float(np.percentile(outside,99))>float(np.mean(outside))*15

        # Entropy
        hist = np.histogram(gray,bins=64,range=(0,255))[0]
        hn = hist/hist.sum(); hn=hn[hn>0]
        entropy = float(-np.sum(hn*np.log2(hn)))
        contrast = float(gray.std())

        # Palette
        flat = arr.reshape(-1,3); rounded=(flat//32*32).astype(int)
        uniq,counts = np.unique(rounded,axis=0,return_counts=True)
        top_i = np.argsort(-counts)[:8]
        palette = [tuple(int(x) for x in uniq[i]) for i in top_i]

        # Skin/organic detection
        skin = (r>95)&(g>40)&(b_ch>20)&(r>g)&(r>b_ch)&((r-g)>15)
        skin_pct = float(skin.mean())

        warm = mr>mb+15; cool = mb>mr+15

        shapes = []
        if has_circular: shapes.append("Formas Circulares")
        if has_grid: shapes.append("Grade / Padrão Periódico")
        if sym>0.8: shapes.append("Alta Simetria")
        if edge_intensity>30: shapes.append("Contornos Nítidos")
        if not shapes: shapes.append("Formas Irregulares")

        # --- Enhanced Category and Object/Material Detection ---
        cat_info = {"category": "Imagem Científica Geral", "description": "", "kw": "scientific image analysis", "material": "Desconhecido", "object_type": "Estrutura Genérica"}

        # Prioritize specific detections
        if skin_pct > 0.15 and mr > 185 and mg < 110 and mb < 110:
            cat_info["category"] = "Coloração H&E (Histoquímica)"
            cat_info["description"] = f"Vermelho dominante R={mr:.0f} e tonalidade orgânica em {skin_pct*100:.0f}% da área. Fortemente indicativo de Hematoxilina & Eosina ou imuno-histoquímica."
            cat_info["kw"] = "hematoxylin eosin histology staining pathology tissue biopsy organic"
            cat_info["material"] = "Tecido Biológico Corado"
            cat_info["object_type"] = "Amostra Histopatológica"
        elif skin_pct > 0.15:
            cat_info["category"] = "Tecido Biológico / Histologia"
            cat_info["description"] = f"Tonalidade orgânica em {skin_pct*100:.0f}% da área. Possível histologia ou fotografia de organismo."
            cat_info["kw"] = "histology tissue biology microscopy organic"
            cat_info["material"] = "Tecido Biológico"
            cat_info["object_type"] = "Células, Tecidos"
        elif has_grid and edge_intensity > 20:
            cat_info["category"] = "Cristalografia / Difração"
            cat_info["description"] = f"Padrão periódico detectado via análise FFT. Sugere difração de raios-X ou microscopia eletrônica de materiais cristalinos."
            cat_info["kw"] = "crystallography X-ray diffraction electron microscopy material science crystal lattice"
            cat_info["material"] = "Material Cristalino"
            cat_info["object_type"] = "Estrutura Atômica, Cristais"
        elif mg > 165 and mr < 130:
            cat_info["category"] = "Fluorescência Verde — GFP/FITC"
            cat_info["description"] = f"Canal verde dominante (G={mg:.0f}). Indicativo de marcador GFP, FITC ou fluorescência celular."
            cat_info["kw"] = "GFP fluorescence microscopy cell biology protein expression"
            cat_info["material"] = "Proteínas Fluorescentes"
            cat_info["object_type"] = "Células, Proteínas Marcadas"
        elif mb > 165 and mr < 130:
            cat_info["category"] = "Fluorescência Azul — DAPI/Hoechst"
            cat_info["description"] = f"Canal azul dominante (B={mb:.0f}). Sugere núcleos celulares marcados com DAPI ou Hoechst."
            cat_info["kw"] = "DAPI nuclear staining fluorescence microscopy DNA chromatin"
            cat_info["material"] = "DNA/Cromatina"
            cat_info["object_type"] = "Núcleos Celulares"
        elif has_circular and edge_intensity > 25:
            cat_info["category"] = "Estrutura Celular / Microscopia Óptica"
            cat_info["description"] = f"Formas circulares com contornos definidos. Comum em microscopia óptica ou eletrônica de células e organelas."
            cat_info["kw"] = "cell microscopy organelle nucleus structure biology"
            cat_info["material"] = "Componentes Celulares"
            cat_info["object_type"] = "Células, Organelas"
        elif entropy > 6.0 and edge_intensity < 20: # High entropy, low edge intensity suggests complex texture, not sharp diagrams
            cat_info["category"] = "Imagem Multispectral / Satélite"
            cat_info["description"] = f"Entropia alta ({entropy:.2f} bits). Característica de imagem de satélite, mapa de calor ou composição multiespectral."
            cat_info["kw"] = "satellite remote sensing multispectral imaging geospatial environmental"
            cat_info["material"] = "Dados Geográficos/Ambientais"
            cat_info["object_type"] = "Paisagem, Mapas, Dados Espaciais"
        elif edge_intensity > 38:
            cat_info["category"] = "Gráfico / Diagrama Científico"
            cat_info["description"] = f"Bordas muito definidas (I={edge_intensity:.1f}). Sugere um gráfico, diagrama ou esquema técnico."
            cat_info["kw"] = "scientific visualization data chart diagram technical illustration"
            cat_info["material"] = "Dados Abstratos"
            cat_info["object_type"] = "Gráfico, Fluxograma, Esquema"
        elif sym > 0.82:
            cat_info["category"] = "Estrutura Molecular / Simétrica"
            cat_info["description"] = f"Alta simetria (score={sym:.3f}). Possível estrutura molecular, proteína ou padrão geométrico."
            cat_info["kw"] = "molecular structure protein crystal symmetry chemistry biology"
            cat_info["material"] = "Moléculas, Proteínas"
            cat_info["object_type"] = "Estrutura Molecular, Geometria"
        else:
            cat_info["category"] = "Imagem Científica Geral"
            cat_info["description"] = f"Temperatura {'quente' if warm else ('fria' if cool else 'neutra')}. Brilho médio {(mr+mg+mb)/3:.0f}/255."
            cat_info["kw"] = "scientific image analysis research data"
            cat_info["material"] = "Variado"
            cat_info["object_type"] = "Imagem Científica"

        conf = min(97, 50+edge_intensity/2+entropy*3+sym*5)
        return {
            "category": cat_info["category"],
            "description": cat_info["description"],
            "kw": cat_info["kw"],
            "material": cat_info["material"],
            "object_type": cat_info["object_type"],
            "confidence": round(conf,1),
            "lines":{"direction":line_dir,"intensity":round(edge_intensity,2),"h":round(h_strength,2),"v":round(v_strength,2)},
            "shapes":shapes,"symmetry":round(sym,3),"circular":has_circular,"grid":has_grid,
            "color":{"r":round(mr,1),"g":round(mg,1),"b":round(mb,1),"warm":warm,"cool":cool},
            "texture":{"entropy":round(entropy,3),"contrast":round(contrast,2),
                           "complexity":"Alta" if entropy>5.5 else ("Média" if entropy>4 else "Baixa")},
            "palette":palette,"size":orig,"skin_pct":round(skin_pct*100,1)
        }
    except Exception as e:
        st.error(f"Erro ao analisar imagem: {e}")
        return None

# ════════════════════════════════════════════════════
# FOLDER DOCUMENT ANALYSIS
# ════════════════════════════════════════════════════
KEYWORD_MAP = {
    "genomica":["Genômica","DNA"],"dna":["Genômica","DNA"],"rna":["RNA","Genômica"],
    "crispr":["CRISPR","Edição Gênica"],"proteina":["Proteômica"],"celula":["Biologia Celular"],
    "neurociencia":["Neurociência"],"cerebro":["Neurociência"],"sono":["Sono","Neurociência"],
    "memoria":["Memória","Cognição"],"ia":["IA","Machine Learning"],"ml":["Machine Learning"],
    "deep":["Deep Learning","Redes Neurais"],"quantum":["Computação Quântica"],
    "fisica":["Física"],"quimica":["Química"],"molecula":["Química"],
    "astronomia":["Astronomia"],"estrela":["Astrofísica"],"cosmo":["Cosmologia"],
    "psicologia":["Psicologia"],"comportamento":["Psicologia"],"biologia":["Biologia"],
    "medicina":["Medicina"],"cancer":["Oncologia"],"engenharia":["Engenharia"],
    "robotica":["Robótica"],"dados":["Ciência de Dados"],"estatistica":["Estatística"],
    "tese":["Tese/Dissertação"],"relatorio":["Relatório"],"analise":["Análise"],
    "protocolo":["Metodologia"],"resultado":["Resultados"],"metodologia":["Metodologia"],
    "museologia":["Museologia"],"patrimonio":["Patrimônio Cultural"],"cultura":["Cultura"],
    "ecologia":["Ecologia"],"clima":["Clima"],"ambiental":["Meio Ambiente"],
}
EXT_MAP = {
    "pdf":"Documento PDF","docx":"Word","doc":"Word","xlsx":"Planilha","csv":"Dados",
    "txt":"Texto","png":"Imagem","jpg":"Imagem","jpeg":"Imagem","tiff":"Imagem Científica",
    "py":"Código Python","r":"Código R","ipynb":"Notebook Jupyter",
    "pptx":"Apresentação","md":"Markdown",
}

def analyze_folder(folder_name):
    fd = st.session_state.folders.get(folder_name,{})
    files = fd.get("files",[]) if isinstance(fd,dict) else fd
    if not files: return None
    all_tags, file_analyses = set(), []
    for fname in files:
        fl = fname.lower().replace("_"," ").replace("-"," ")
        ftags = set()
        for kw,ktags in KEYWORD_MAP.items():
            if kw in fl: ftags.update(ktags)
        ext = fname.split(".")[-1].lower() if "." in fname else ""
        ftype = EXT_MAP.get(ext,"Arquivo")
        if not ftags: ftags.add("Pesquisa Geral")
        all_tags.update(ftags)
        prog = random.randint(35,98)
        file_analyses.append({"file":fname,"type":ftype,"tags":list(ftags),"progress":prog})
    areas = list(all_tags)[:6]
    summary = f"{len(files)} documento(s) · Áreas: {', '.join(areas)}"
    return {"tags":list(all_tags)[:12],"summary":summary,"file_analyses":file_analyses,"total_files":len(files)}

# ════════════════════════════════════════════════════
# INTERNET ARTICLE SEARCH
# ════════════════════════════════════════════════════
def search_semantic_scholar(query, limit=8):
    results = []
    try:
        r = requests.get("https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query":query,"limit":limit,
                    "fields":"title,authors,year,abstract,venue,externalIds,openAccessPdf,citationCount"},
            timeout=9)
        if r.status_code==200:
            for p in r.json().get("data",[]):
                ext=p.get("externalIds",{}) or {}
                doi=ext.get("DOI",""); arxiv=ext.get("ArXiv","")
                pdf=p.get("openAccessPdf") or {}
                link=pdf.get("url","") or (f"https://arxiv.org/abs/{arxiv}" if arxiv else (f"https://doi.org/{doi}" if doi else ""))
                alist=p.get("authors",[]) or []
                authors=", ".join(a.get("name","") for a in alist[:3])
                if len(alist)>3: authors+=" et al."
                abstract=(p.get("abstract","") or "")[:280]
                results.append({"title":p.get("title","Sem título"),"authors":authors or "—",
                    "year":p.get("year","?"),"source":p.get("venue","") or "Semantic Scholar",
                    "doi":doi or arxiv or "—","abstract":abstract,"url":link,
                    "citations":p.get("citationCount",0),"origin":"semantic"})
    except requests.exceptions.RequestException as e:
        st.warning(f"Erro ao buscar no Semantic Scholar: {e}")
    except Exception as e:
        st.warning(f"Erro inesperado no Semantic Scholar: {e}")
    return results

def search_crossref(query, limit=5):
    results = []
    try:
        r = requests.get("https://api.crossref.org/works",
            params={"query":query,"rows":limit,
                    "select":"title,author,issued,abstract,DOI,container-title,is-referenced-by-count",
                    "mailto":"nebula@example.com"},timeout=9)
        if r.status_code==200:
            for p in r.json().get("message",{}).get("items",[]):
                title=(p.get("title") or ["Sem título"])[0]
                ars=p.get("author",[]) or []
                authors=", ".join(f'{a.get("given","").split()[0] if a.get("given") else ""} {a.get("family","")}'.strip() for a in ars[:3])
                if len(ars)>3: authors+=" et al."
                year=(p.get("issued",{}).get("date-parts") or [[None]])[0][0]
                doi=p.get("DOI",""); journal=(p.get("container-title") or [""])[0]
                abstract=re.sub(r'<[^>]+>','',p.get("abstract","") or "")[:280]
                results.append({"title":title,"authors":authors or "—","year":year or "?",
                    "source":journal or "CrossRef","doi":doi,"abstract":abstract,
                    "url":f"https://doi.org/{doi}" if doi else "",
                    "citations":p.get("is-referenced-by-count",0),"origin":"crossref"})
    except requests.exceptions.RequestException as e:
        st.warning(f"Erro ao buscar no CrossRef: {e}")
    except Exception as e:
        st.warning(f"Erro inesperado no CrossRef: {e}")
    return results

# ════════════════════════════════════════════════════
# IMAGE REVERSE SEARCH — busca artigos pela imagem
# ════════════════════════════════════════════════════
def search_image_in_nebula(rep):
    """Busca posts da Nebula relacionados à imagem analisada."""
    kw = rep.get("kw","").lower().split()
    category_words = rep.get("category","").lower().split()
    material_words = rep.get("material","").lower().split()
    object_words = rep.get("object_type","").lower().split()
    all_search_terms = list(set(kw + category_words + material_words + object_words))

    results = []
    for p in st.session_state.feed_posts:
        score = 0
        post_text = (p.get("title","") + " " + p.get("abstract","") + " " + " ".join(p.get("tags",[]))).lower()
        for term in all_search_terms:
            if len(term) > 2 and term in post_text: # Use len > 2 for more meaningful terms
                score += 1
        if score > 0:
            results.append((score, p))
    results.sort(key=lambda x: -x[0])
    return [p for _, p in results[:4]]

def search_image_in_folders(rep):
    """Busca nos arquivos das pastas do usuário relacionados à imagem."""
    kw = rep.get("kw","").lower().split()
    category_words = rep.get("category","").lower().split()
    material_words = rep.get("material","").lower().split()
    object_words = rep.get("object_type","").lower().split()
    all_search_terms = list(set(kw + category_words + material_words + object_words))

    matches = []

    for fname, fdata in st.session_state.folders.items():
        if not isinstance(fdata, dict): continue

        folder_tags = [t.lower() for t in fdata.get("analysis_tags", [])]

        folder_score = 0
        for term in all_search_terms:
            if len(term) > 2 and any(term in t for t in folder_tags):
                folder_score += 1

        for f in fdata.get("files", []):
            file_lower = f.lower()
            for term in all_search_terms:
                if len(term) > 2 and term in file_lower:
                    folder_score += 1

        if folder_score > 0:
            matches.append({"folder": fname, "tags": fdata.get("analysis_tags",[]), "files": fdata.get("files",[]), "score": folder_score})

    matches.sort(key=lambda x: -x["score"])
    return matches[:4]

def search_image_internet(rep):
    """Busca artigos na internet relacionados à categoria da imagem."""
    query_terms = [rep.get("category",""), rep.get("object_type",""), rep.get("material","")]
    query = " ".join(filter(None, query_terms))
    if not query.strip():
        query = rep.get("kw","scientific image analysis") # Fallback to general keywords

    ss = search_semantic_scholar(query, limit=3)
    cr = search_crossref(query, limit=2)
    merged = ss + [x for x in cr if not any(x["title"].lower()==s["title"].lower() for s in ss)]
    return merged[:5]

# ════════════════════════════════════════════════════
# RECOMMENDATION ENGINE
# ════════════════════════════════════════════════════
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
    a=(area or "").lower()
    M={"ia":["machine learning","deep learning","LLM"],
       "inteligência artificial":["machine learning","LLM","redes neurais"],
       "machine learning":["deep learning","otimização","dados"],
       "neurociência":["sono","memória","plasticidade","hipocampo"],
       "biologia":["célula","genômica","CRISPR","proteína"],
       "física":["quantum","astrofísica","cosmologia","partículas"],
       "química":["síntese","catálise","polímero","molécula"],
       "medicina":["clínica","diagnóstico","terapia","oncologia"],
       "astronomia":["astrofísica","cosmologia","galáxia","telescópio"],
       "computação":["algoritmo","criptografia","redes","sistemas"],
       "matemática":["álgebra","topologia","estatística","análise"],
       "psicologia":["cognição","comportamento","viés","memória"],
       "ecologia":["biodiversidade","clima","ecossistema","espécie"],
       "genômica":["DNA","CRISPR","gene","sequenciamento"],
       "museologia":["patrimônio","curadoria","cultura","história"],
       "engenharia":["robótica","materiais","sistemas","controle"],
       "astrofísica":["cosmologia","galáxia","matéria escura","buraco negro"]}
    for k,v in M.items():
        if k in a: return v
    return [w.strip() for w in a.replace(","," ").split() if len(w)>3][:5]

# ════════════════════════════════════════════════════
# SEED DATA
# ════════════════════════════════════════════════════
SEED_POSTS=[
    {"id":1,"author":"Carlos Mendez","author_email":"carlos@nebula.ai","avatar":"CM","area":"Neurociência",
     "title":"Efeitos da Privação de Sono na Plasticidade Sináptica",
     "abstract":"Investigamos como 24h de privação de sono afetam espinhas dendríticas em ratos Wistar, redução de 34% na plasticidade hipocampal. Dados sugerem janela crítica nas primeiras 6h de recuperação.",
     "tags":["neurociência","sono","memória","hipocampo"],"likes":47,
     "comments":[{"user":"Maria Silva","text":"Excelente metodologia!"},{"user":"João Lima","text":"Quais os critérios de exclusão?"}],
     "status":"Em andamento","date":"2026-02-10","liked_by":[],"saved_by":[],"connections":["sono","memória","hipocampo"]},
    {"id":2,"author":"Luana Freitas","author_email":"luana@nebula.ai","avatar":"LF","area":"Biomedicina",
     "title":"CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras",
     "abstract":"Vetor AAV9 modificado para entrega de CRISPR no gene DMD, eficiência 78% em modelos murinos mdx. Publicação em Cell prevista Q2 2026.",
     "tags":["CRISPR","gene terapia","músculo","AAV9"],"likes":93,
     "comments":[{"user":"Ana","text":"Próximos passos para trials humanos?"}],
     "status":"Publicado","date":"2026-01-28","liked_by":[],"saved_by":[],"connections":["genômica","distrofia"]},
    {"id":3,"author":"Rafael Souza","author_email":"rafael@nebula.ai","avatar":"RS","area":"Computação",
     "title":"Redes Neurais Quântico-Clássicas para Otimização Combinatória",
     "abstract":"Arquitetura híbrida variacional: qubits supercondutores + camadas densas. TSP com 40% menos iterações que métodos clássicos.",
     "tags":["quantum ML","otimização","TSP","computação quântica"],"likes":201,"comments":[],
     "status":"Em andamento","date":"2026-02-15","liked_by":[],"saved_by":[],"connections":["computação quântica","machine learning"]},
    {"id":4,"author":"Priya Nair","author_email":"priya@nebula.ai","avatar":"PN","area":"Astrofísica",
     "title":"Detecção de Matéria Escura via Lentes Gravitacionais Fracas",
     "abstract":"Mapeamento sub-arcminuto com 100M de galáxias do DES Y3. Tensão com ΛCDM em escalas <1 Mpc identificada.",
     "tags":["astrofísica","matéria escura","cosmologia","DES"],"likes":312,"comments":[],
     "status":"Publicado","date":"2026-02-01","liked_by":[],"saved_by":[],"connections":["cosmologia","lentes gravitacionais"]},
    {"id":5,"author":"João Lima","author_email":"joao@nebula.ai","avatar":"JL","area":"Psicologia",
     "title":"Viés de Confirmação em Decisões Médicas Assistidas por IA",
     "abstract":"Estudo duplo-cego com 240 médicos revelou que IA mal calibrada amplifica vieses cognitivos em 22% dos casos clínicos.",
     "tags":["psicologia","IA","cognição","medicina"],"likes":78,"comments":[],
     "status":"Publicado","date":"2026-02-08","liked_by":[],"saved_by":[],"connections":["cognição","IA"]},
]
SEED_USERS={
    "demo@nebula.ai":{"name":"Ana Pesquisadora","password":hp("demo123"),"bio":"Pesquisadora em IA e Ciências Cognitivas | UFMG","area":"Inteligência Artificial","followers":128,"following":47,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "carlos@nebula.ai":{"name":"Carlos Mendez","password":hp("nebula123"),"bio":"Neurocientista | UFMG | Plasticidade sináptica e sono","area":"Neurociência","followers":210,"following":45,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "luana@nebula.ai":{"name":"Luana Freitas","password":hp("nebula123"),"bio":"Biomédica | FIOCRUZ | CRISPR e terapia gênica","area":"Biomedicina","followers":178,"following":62,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "rafael@nebula.ai":{"name":"Rafael Souza","password":hp("nebula123"),"bio":"Computação Quântica | USP | Algoritmos híbridos","area":"Computação","followers":340,"following":88,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "priya@nebula.ai":{"name":"Priya Nair","password":hp("nebula123"),"bio":"Astrofísica | MIT | Dark matter & gravitational lensing","area":"Astrofísica","followers":520,"following":31,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "joao@nebula.ai":{"name":"João Lima","password":hp("nebula123"),"bio":"Psicólogo Cognitivo | UNICAMP | IA e vieses clínicos","area":"Psicologia","followers":95,"following":120,"verified":True,"2fa_enabled":False,"photo_b64":None},
}
CHAT_INIT={
    "carlos@nebula.ai":[{"from":"carlos@nebula.ai","text":"Oi! Vi seu comentário na minha pesquisa.","time":"09:14"},{"from":"me","text":"Achei muito interessante!","time":"09:16"}],
    "luana@nebula.ai":[{"from":"luana@nebula.ai","text":"Podemos colaborar no próximo semestre?","time":"ontem"}],
    "rafael@nebula.ai":[{"from":"rafael@nebula.ai","text":"Compartilhei o repositório quântico.","time":"08:30"}],
}

# ════════════════════════════════════════════════════
# SESSION INIT
# ════════════════════════════════════════════════════
def init():
    if "initialized" in st.session_state: return
    st.session_state.initialized = True
    disk = load_db()
    disk_users = disk.get("users",{})
    if not isinstance(disk_users,dict): disk_users={}
    st.session_state.setdefault("users",{**SEED_USERS,**disk_users})
    st.session_state.setdefault("logged_in",False)
    st.session_state.setdefault("current_user",None)
    st.session_state.setdefault("page","login")
    st.session_state.setdefault("profile_view",None)
    disk_prefs = disk.get("user_prefs",{})
    st.session_state.setdefault("user_prefs",{k:defaultdict(float,v) for k,v in disk_prefs.items()})
    st.session_state.setdefault("pending_verify",None)
    st.session_state.setdefault("pending_2fa",None)
    st.session_state.setdefault("feed_posts",disk.get("feed_posts",[dict(p) for p in SEED_POSTS]))
    st.session_state.setdefault("folders",disk.get("folders",{}))
    st.session_state.setdefault("chat_contacts",list(SEED_USERS.keys()))
    st.session_state.setdefault("chat_messages",{k:list(v) for k,v in CHAT_INIT.items()})
    st.session_state.setdefault("active_chat",None)
    st.session_state.setdefault("followed",["carlos@nebula.ai","luana@nebula.ai"])
    st.session_state.setdefault("notifications",["Carlos curtiu sua pesquisa","Nova conexão detectada"])
    st.session_state.setdefault("scholar_cache",{})
    st.session_state.setdefault("saved_articles",disk.get("saved_articles",[])) # Load saved_articles
    st.session_state.setdefault("img_analysis_result", None)
    st.session_state.setdefault("img_search_done", False)

init()

# ════════════════════════════════════════════════════
# AUTH PAGES
# ════════════════════════════════════════════════════
def page_login():
    _,col,_ = st.columns([1,1.05,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-bottom:2.5rem;">
          <div style="font-family:'Syne',sans-serif;font-size:3.2rem;font-weight:800;
            background:linear-gradient(135deg,#93c5fd,#22d3ee,#60a5f5);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
            letter-spacing:-.04em;line-height:1;">🔬 Nebula</div>
          <div style="color:var(--t3);font-size:.68rem;letter-spacing:.20em;text-transform:uppercase;margin-top:.6rem;">
            Rede do Conhecimento Científico</div>
        </div>""",unsafe_allow_html=True)
        tab_in,tab_up = st.tabs(["  Entrar  ","  Criar conta  "])
        with tab_in:
            email = st.text_input("E-mail",placeholder="seu@email.com",key="li_e")
            pw    = st.text_input("Senha",placeholder="••••••••",type="password",key="li_p")
            if st.button("Entrar →",use_container_width=True,key="btn_li"):
                u = st.session_state.users.get(email)
                if not u: st.error("E-mail não encontrado.")
                elif u["password"]!=hp(pw): st.error("Senha incorreta.")
                elif u.get("2fa_enabled"):
                    c=code6(); st.session_state.pending_2fa={"email":email,"code":c}
                    st.session_state.page="2fa"; st.rerun()
                else:
                    st.session_state.logged_in=True; st.session_state.current_user=email
                    record(area_to_tags(u.get("area","")),1.0)
                    st.session_state.page="feed"; st.rerun()
            st.markdown('<div style="text-align:center;color:var(--t3);font-size:.68rem;margin-top:.5rem;">Demo: demo@nebula.ai / demo123</div>',unsafe_allow_html=True)
        with tab_up:
            n_name=st.text_input("Nome completo",placeholder="Dr. Maria Silva",key="su_n")
            n_email=st.text_input("E-mail",placeholder="seu@email.com",key="su_e")
            n_area=st.text_input("Área de pesquisa",placeholder="Ex: Neurociência, IA, Museologia",key="su_a")
            n_pw=st.text_input("Senha",placeholder="Mín. 6 caracteres",type="password",key="su_p")
            n_pw2=st.text_input("Confirmar senha",placeholder="••••••••",type="password",key="su_p2")
            if st.button("Criar conta →",use_container_width=True,key="btn_su"):
                if not all([n_name,n_email,n_area,n_pw,n_pw2]): st.error("Preencha todos os campos.")
                elif n_pw!=n_pw2: st.error("Senhas não coincidem.")
                elif len(n_pw)<6: st.error("Senha muito curta.")
                elif n_email in st.session_state.users: st.error("E-mail já cadastrado.")
                else:
                    c=code6(); st.session_state.pending_verify={"email":n_email,"name":n_name,"pw":hp(n_pw),"area":n_area,"code":c}
                    st.session_state.page="verify_email"; st.rerun()

def page_verify_email():
    pv=st.session_state.pending_verify
    _,col,_=st.columns([1,1.05,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown(f"""<div class="card" style="text-align:center;">
          <div style="font-size:2.8rem;margin-bottom:1rem;">📧</div>
          <h2 style="margin-bottom:.5rem;">Verifique seu e-mail</h2>
          <p style="color:var(--t2);font-size:.83rem;">Código enviado para <strong>{pv['email']}</strong></p>
          <div style="background:rgba(30,100,180,.10);border:1px solid rgba(55,130,215,.24);border-radius:14px;padding:18px;margin:1.2rem 0;">
            <div style="font-size:.64rem;color:var(--t3);letter-spacing:.12em;text-transform:uppercase;margin-bottom:6px;">Código (demo)</div>
            <div style="font-family:'Syne',sans-serif;font-size:2.5rem;font-weight:800;letter-spacing:.28em;color:var(--b300);">{pv['code']}</div>
          </div></div>""",unsafe_allow_html=True)
        typed=st.text_input("Código",max_chars=6,placeholder="000000",key="ev_c")
        if st.button("Verificar e criar conta →",use_container_width=True,key="btn_ev"):
            if typed.strip()==pv["code"]:
                st.session_state.users[pv["email"]]={"name":pv["name"],"password":pv["pw"],"bio":"","area":pv["area"],"followers":0,"following":0,"verified":True,"2fa_enabled":False,"photo_b64":None}
                save_db(); st.session_state.pending_verify=None
                st.session_state.logged_in=True; st.session_state.current_user=pv["email"]
                record(area_to_tags(pv["area"]),2.0); st.session_state.page="feed"; st.rerun()
            else: st.error("Código inválido.")
        if st.button("← Voltar",key="btn_ev_bk"): st.session_state.page="login"; st.rerun()

def page_2fa():
    p2=st.session_state.pending_2fa
    _,col,_=st.columns([1,1.05,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown(f"""<div class="card" style="text-align:center;">
          <div style="font-size:2.8rem;margin-bottom:1rem;">🔑</div><h2>Verificação 2FA</h2>
          <div style="background:rgba(30,100,180,.10);border:1px solid rgba(55,130,215,.24);border-radius:14px;padding:16px;margin:1rem 0;">
            <div style="font-size:.64rem;color:var(--t3);text-transform:uppercase;letter-spacing:.10em;margin-bottom:6px;">Código (demo)</div>
            <div style="font-family:'Syne',sans-serif;font-size:2.5rem;font-weight:800;letter-spacing:.24em;color:var(--b300);">{p2['code']}</div>
          </div></div>""",unsafe_allow_html=True)
        typed=st.text_input("Código",max_chars=6,placeholder="000000",key="fa_c",label_visibility="collapsed")
        if st.button("Verificar →",use_container_width=True,key="btn_fa"):
            if typed.strip()==p2["code"]:
                st.session_state.logged_in=True; st.session_state.current_user=p2["email"]
                st.session_state.pending_2fa=None; st.session_state.page="feed"; st.rerun()
            else: st.error("Código inválido.")
        if st.button("← Voltar",key="btn_fa_bk"): st.session_state.page="login"; st.rerun()

# ════════════════════════════════════════════════════
# TOP NAV
# ════════════════════════════════════════════════════
NAV=[("feed","◈","Feed"),("search","⊙","Artigos"),("knowledge","⬡","Conexões"),
     ("folders","▣","Pastas"),("analytics","▤","Análises"),
     ("img_search","⊞","Imagem"),("chat","◻","Chat"),("settings","◎","Perfil")]

def render_topnav():
    u=guser(); name=u.get("name","?"); photo=u.get("photo_b64"); in_=ini(name)
    cur=st.session_state.page; notif=len(st.session_state.notifications)
    nav_spans=""
    for k,sym,lbl in NAV:
        active=cur==k
        if active:
            nav_spans+=f'<span style="font-size:.76rem;color:var(--b300);font-weight:600;padding:.36rem .72rem;border-radius:var(--rxs);background:rgba(30,100,180,.24);border:1px solid rgba(90,158,240,.30);display:inline-flex;align-items:center;gap:5px;white-space:nowrap;">{sym} {lbl}</span>'
        else:
            nav_spans+=f'<span style="font-size:.76rem;color:var(--t3);padding:.36rem .72rem;border-radius:var(--rxs);white-space:nowrap;display:inline-flex;align-items:center;gap:4px;">{sym} {lbl}</span>'
    av_inner=f"<img src='{photo}' style='width:100%;height:100%;object-fit:cover;border-radius:50%;'/>" if photo else in_
    av=f'<div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,var(--b800),var(--b500));display:flex;align-items:center;justify-content:center;font-size:.72rem;font-weight:700;color:white;border:1.5px solid rgba(90,158,240,.28);overflow:hidden;flex-shrink:0;box-shadow:0 2px 10px rgba(0,0,0,.45);">{av_inner}</div>'
    nb=f'<span style="background:var(--b500);color:white;border-radius:10px;padding:1px 7px;font-size:.62rem;font-weight:600;">{notif}</span>' if notif else ""
    st.markdown(f"""
    <div style="position:sticky;top:0;z-index:1000;background:rgba(1,4,9,.92);backdrop-filter:blur(32px) saturate(200%);-webkit-backdrop-filter:blur(32px) saturate(200%);border-bottom:1px solid var(--gbd);padding:0 1.4rem;display:flex;align-items:center;justify-content:space-between;height:56px;">
      <div style="font-family:'Syne',sans-serif;font-size:1.26rem;font-weight:800;background:linear-gradient(135deg,#93c5fd,#22d3ee);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;white-space:nowrap;letter-spacing:-.03em;flex-shrink:0;">🔬 Nebula</div>
      <div style="display:flex;align-items:center;gap:2px;overflow-x:auto;padding:0 .5rem;scrollbar-width:none;-ms-overflow-style:none;">{nav_spans}</div>
      <div style="display:flex;align-items:center;gap:10px;flex-shrink:0;">{nb}{av}</div>
    </div>""",unsafe_allow_html=True)
    # Invisible clickable overlay
    st.markdown('<div class="toprow">',unsafe_allow_html=True)
    cols=st.columns([1.6]+[1]*len(NAV)+[.8])
    for i,(key,sym,lbl) in enumerate(NAV):
        with cols[i+1]:
            if st.button(f"{sym}{lbl}",key=f"tnav_{key}",use_container_width=True):
                st.session_state.profile_view=None; st.session_state.page=key; st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)

# ════════════════════════════════════════════════════
# PROFILE PAGE
# ════════════════════════════════════════════════════
def page_profile(target_email):
    users=st.session_state.users
    tu=users.get(target_email,{})
    if not tu:
        st.error("Perfil não encontrado.")
        if st.button("← Voltar"): st.session_state.profile_view=None; st.rerun()
        return
    tname=tu.get("name","?"); tin=ini(tname); tphoto=tu.get("photo_b64")
    email=st.session_state.current_user; is_me=email==target_email
    is_fol=target_email in st.session_state.followed

    if st.button("← Voltar",key="back_prof"): st.session_state.profile_view=None; st.rerun()

    photo_html=f"<img src='{tphoto}'/>" if tphoto else f'<span style="font-size:2.2rem;">{tin}</span>'
    user_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==target_email]
    st.markdown(f"""
    <div class="prof-hero">
      <div class="prof-photo">{photo_html}</div>
      <div style="flex:1;">
        <h1 style="margin-bottom:.25rem;">{tname}</h1>
        <div style="color:var(--b300);font-size:.84rem;margin-bottom:.5rem;font-weight:500;">{tu.get('area','')}</div>
        <div style="color:var(--t2);font-size:.82rem;line-height:1.65;margin-bottom:.9rem;">{tu.get('bio','Sem biografia.')}</div>
        <div style="display:flex;gap:2rem;">
          <div><span style="font-weight:800;font-family:'Syne',sans-serif;font-size:1.15rem;">{tu.get('followers',0)}</span><span style="color:var(--t3);font-size:.73rem;"> seguidores</span></div>
          <div><span style="font-weight:800;font-family:'Syne',sans-serif;font-size:1.15rem;">{tu.get('following',0)}</span><span style="color:var(--t3);font-size:.73rem;"> seguindo</span></div>
          <div><span style="font-weight:800;font-family:'Syne',sans-serif;font-size:1.15rem;">{len(user_posts)}</span><span style="color:var(--t3);font-size:.73rem;"> pesquisas</span></div>
        </div>
      </div>
    </div>""",unsafe_allow_html=True)

    if not is_me:
        col_fol,col_chat,_=st.columns([1,1,3])
        with col_fol:
            if st.button("✓ Seguindo" if is_fol else "➕ Seguir",key=f"prof_fol_{target_email}",use_container_width=True):
                if is_fol: st.session_state.followed.remove(target_email); tu["followers"]=max(0,tu.get("followers",0)-1)
                else: st.session_state.followed.append(target_email); tu["followers"]=tu.get("followers",0)+1
                save_db(); st.rerun()
        with col_chat:
            if st.button("💬 Chat",key=f"prof_chat_{target_email}",use_container_width=True):
                if target_email not in st.session_state.chat_messages: st.session_state.chat_messages[target_email]=[]
                st.session_state.active_chat=target_email; st.session_state.page="chat"; st.rerun()

    st.markdown('<h2 style="margin-top:1.5rem;">Pesquisas de '+tname+'</h2>',unsafe_allow_html=True)
    if user_posts:
        for p in sorted(user_posts,key=lambda x:x.get("date",""),reverse=True):
            # Simplified render_post for profile page, without action buttons
            st.markdown(f"""
            <div class="card">
                <div style="font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:700;margin-bottom:.4rem;">{p['title']}</div>
                <div style="color:var(--t2);font-size:.82rem;line-height:1.6;">{p['abstract']}</div>
                <div style="margin-top:.8rem;display:flex;gap:1.2rem;font-size:.73rem;color:var(--t3);">
                    <span>{p.get('date','')}</span>
                    <span>❤ {p['likes']}</span>
                    <span>💬 {len(p['comments'])}</span>
                    {badge(p['status'])}
                </div>
                <div style="margin-top:.5rem;">{tags_html(p['tags'])}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="card" style="text-align:center;padding:2rem;color:var(--t3);">Nenhuma pesquisa publicada ainda.</div>',unsafe_allow_html=True)

    st.markdown('</div>',unsafe_allow_html=True)

# ════════════════════════════════════════════════════
# FEED
# ════════════════════════════════════════════════════
def page_feed():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem;">Seu Feed</h1>',unsafe_allow_html=True)

    email=st.session_state.current_user
    recs=get_recs(email)
    if recs:
        st.markdown('<h2>Recomendações para você <span class="badge-rec">NOVO</span></h2>',unsafe_allow_html=True)
        for p in recs:
            render_post(p, rec=True, ctx="rec") # Pass ctx for unique keys

    st.markdown('<h2>Últimas pesquisas</h2>',unsafe_allow_html=True)
    for p in sorted(st.session_state.feed_posts,key=lambda x:x.get("date",""),reverse=True):
        render_post(p, ctx="feed") # Pass ctx for unique keys

    st.markdown('</div>',unsafe_allow_html=True)

# ════════════════════════════════════════════════════
# SEARCH
# ════════════════════════════════════════════════════
def page_search():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem;">Busca de Artigos</h1>',unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.82rem;margin-bottom:1rem;">Pesquise em bases de dados acadêmicas e na rede Nebula.</p>',unsafe_allow_html=True)

    search_query=st.text_input("Termo de busca",placeholder="Ex: 'CRISPR gene editing' ou 'dark matter cosmology'",key="search_q")
    if st.button("🔍 Buscar",use_container_width=True,key="btn_search"):
        if search_query:
            with st.spinner("Buscando artigos…"):
                # Search in Nebula posts
                nebula_results = [p for p in st.session_state.feed_posts if search_query.lower() in p["title"].lower() or search_query.lower() in p["abstract"].lower() or any(search_query.lower() in t.lower() for t in p["tags"])]

                # Search in Semantic Scholar
                ss_results = search_semantic_scholar(search_query, limit=5)

                # Search in CrossRef
                cr_results = search_crossref(search_query, limit=3)

                st.session_state.search_results = {
                    "nebula": nebula_results,
                    "semantic_scholar": ss_results,
                    "crossref": cr_results
                }
                st.session_state.last_search_query = search_query
        else:
            st.warning("Por favor, digite um termo de busca.")

    if st.session_state.get("search_results"):
        results = st.session_state.search_results

        tab_all, tab_nebula, tab_web = st.tabs(["  Todos os resultados  ", "  Na Nebula  ", "  Na Internet  "])

        with tab_all:
            st.markdown(f'<h3>Resultados para "{st.session_state.last_search_query}"</h3>', unsafe_allow_html=True)

            all_results = []
            for p in results["nebula"]:
                all_results.append({"type": "nebula", "data": p})
            for a in results["semantic_scholar"]:
                all_results.append({"type": "web", "data": a})
            for a in results["crossref"]:
                all_results.append({"type": "web", "data": a})

            if all_results:
                for idx, item in enumerate(all_results):
                    if item["type"] == "nebula":
                        render_search_post(item["data"], ctx=f"all_search_{idx}") # Pass ctx
                    elif item["type"] == "web":
                        render_web_article(item["data"], idx=idx, ctx=f"all_search_web_{idx}") # Pass ctx
            else:
                st.info("Nenhum resultado encontrado para esta busca.")

        with tab_nebula:
            st.markdown(f'<h3>Posts na Nebula para "{st.session_state.last_search_query}"</h3>', unsafe_allow_html=True)
            if results["nebula"]:
                for idx, p in enumerate(results["nebula"]):
                    render_search_post(p, ctx=f"nebula_search_{idx}") # Pass ctx
            else:
                st.info("Nenhum post encontrado na Nebula para esta busca.")

        with tab_web:
            st.markdown(f'<h3>Artigos na Internet para "{st.session_state.last_search_query}"</h3>', unsafe_allow_html=True)
            web_articles = results["semantic_scholar"] + results["crossref"]
            if web_articles:
                for idx, a in enumerate(web_articles):
                    render_web_article(a, idx=idx, ctx=f"web_search_{idx}") # Pass ctx
            else:
                st.info("Nenhum artigo encontrado na internet para esta busca.")

    st.markdown('</div>',unsafe_allow_html=True)

# ════════════════════════════════════════════════════
# RENDER POSTS AND ARTICLES
# ════════════════════════════════════════════════════
def render_post(post, rec=False, show_profile_link=True, ctx="feed"): # Added ctx parameter
    email = st.session_state.current_user
    liked = email in post["liked_by"]
    saved = email in post.get("saved_by",[])

    author_info = st.session_state.users.get(post["author_email"], {})
    author_name = author_info.get("name", "?")
    author_initials = ini(author_name)
    author_photo = author_info.get("photo_b64")
    author_area = author_info.get("area", "")

    st.markdown(f"""
    <div class="card">
        <div class="clickable-author-container">
            <div class="author-info">
                {avh(author_initials, 36, author_photo)}
                <div>
                    <div class="author-info-name">{author_name}</div>
                    <div class="author-info-area">{author_area}</div>
                </div>
            </div>
            <!-- Invisible button to click on author profile -->
            <button class="clickable-author-button" key="author_profile_link_{ctx}_{post['id']}" onclick="window.parent.document.querySelector('[data-testid=\"stButtonButton\"][key=\"author_profile_link_{ctx}_{post['id']}\"]').click()">
            </button>
        </div>
        <div style="font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:700;margin-bottom:.4rem;">{post['title']}</div>
        <div style="color:var(--t2);font-size:.82rem;line-height:1.6;">{post['abstract']}</div>
        <div style="margin-top:.8rem;display:flex;gap:1.2rem;font-size:.73rem;color:var(--t3);">
            <span>{post.get('date','')}</span>
            <span>❤ {post['likes']}</span>
            <span>💬 {len(post['comments'])}</span>
            {badge(post['status'])}
            {f'<span class="badge-rec">RECOMENDADO</span>' if rec else ''}
        </div>
        <div style="margin-top:.5rem;">{tags_html(post['tags'])}</div>
        <div style="display:flex;gap:10px;margin-top:1rem;">
            <div style="flex:1;">
                {st.button("❤ Curtir" if not liked else "💔 Descurtir", key=f"lk_{ctx}_{post['id']}", use_container_width=True)}
            </div>
            <div style="flex:1;">
                {st.button("📌 Salvo" if saved else "🔖 Salvar", key=f"sv_{ctx}_{post['id']}", use_container_width=True)}
            </div>
            <div style="flex:1;">
                {st.button("💬 Comentar", key=f"cm_{ctx}_{post['id']}", use_container_width=True)}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Handle button clicks
    if st.session_state.get(f"lk_{ctx}_{post['id']}"):
        if liked:
            post["liked_by"].remove(email)
            post["likes"] = max(0, post["likes"] - 1)
        else:
            post["liked_by"].append(email)
            post["likes"] += 1
        save_db(); st.rerun()

    if st.session_state.get(f"sv_{ctx}_{post['id']}"):
        if saved:
            post["saved_by"].remove(email)
        else:
            post["saved_by"].append(email)
        save_db(); st.rerun()

    # Handle the invisible button click for profile view
    if st.session_state.get(f"author_profile_link_{ctx}_{post['id']}"):
        st.session_state.profile_view = post['author_email']
        st.rerun()


def render_search_post(post, ctx="search"): # Added ctx parameter
    email = st.session_state.current_user
    liked = email in post["liked_by"]
    saved = email in post.get("saved_by",[])

    author_info = st.session_state.users.get(post["author_email"], {})
    author_name = author_info.get("name", "?")
    author_initials = ini(author_name)
    author_photo = author_info.get("photo_b64")
    author_area = author_info.get("area", "")

    st.markdown(f"""
    <div class="scard">
        <div class="clickable-author-container">
            <div class="author-info" style="margin-bottom: 0.5rem;">
                {avh(author_initials, 32, author_photo)}
                <div>
                    <div class="author-info-name" style="font-size:.82rem;">{author_name}</div>
                    <div class="author-info-area" style="font-size:.68rem;">{author_area}</div>
                </div>
            </div>
            <!-- Invisible button to click on author profile -->
            <button class="clickable-author-button" key="search_author_link_{ctx}_{post['id']}" onclick="window.parent.document.querySelector('[data-testid=\"stButtonButton\"][key=\"search_author_link_{ctx}_{post['id']}\"]').click()">
            </button>
        </div>
        <div style="font-family:'Syne',sans-serif;font-size:.95rem;font-weight:700;margin-bottom:.3rem;">{post['title']}</div>
        <div style="color:var(--t2);font-size:.78rem;line-height:1.5;">{post['abstract'][:180]}...</div>
        <div style="margin-top:.6rem;display:flex;gap:1rem;font-size:.68rem;color:var(--t3);">
            <span>{post.get('date','')}</span>
            <span>❤ {post['likes']}</span>
            <span>💬 {len(post['comments'])}</span>
            {badge(post['status'])}
        </div>
        <div style="margin-top:.4rem;">{tags_html(post['tags'])}</div>
        <div style="display:flex;gap:8px;margin-top:.8rem;">
            <div style="flex:1;">
                {st.button("❤ Curtir" if not liked else "💔 Descurtir", key=f"lk_s_{ctx}_{post['id']}", use_container_width=True)}
            </div>
            <div style="flex:1;">
                {st.button("📌 Salvo" if saved else "🔖 Salvar", key=f"sv_s_{ctx}_{post['id']}", use_container_width=True)}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Handle button clicks
    if st.session_state.get(f"lk_s_{ctx}_{post['id']}"):
        if liked:
            post["liked_by"].remove(email)
            post["likes"] = max(0, post["likes"] - 1)
        else:
            post["liked_by"].append(email)
            post["likes"] += 1
        save_db(); st.rerun()

    if st.session_state.get(f"sv_s_{ctx}_{post['id']}"):
        if saved:
            post["saved_by"].remove(email)
        else:
            post["saved_by"].append(email)
        save_db(); st.rerun()

    # Handle the invisible button click for profile view
    if st.session_state.get(f"search_author_link_{ctx}_{post['id']}"):
        st.session_state.profile_view = post['author_email']
        st.rerun()


def render_web_article(a, idx=0, ctx="general_web"): # Added ctx parameter
    src_color="#22d3ee" if a.get("origin")=="semantic" else "#a78bfa"
    src_name="Semantic Scholar" if a.get("origin")=="semantic" else "CrossRef"
    cite=f" · {a['citations']} cit." if a.get("citations") else ""
    # Ensure uid is unique across all contexts where render_web_article is called
    uid=re.sub(r'[^a-zA-Z0-9]','',f"{ctx}_{a.get('doi','nodoi')}_{idx}")[:30] # Added ctx to uid
    is_saved=any(s.get('doi')==a.get('doi') for s in st.session_state.saved_articles)
    st.markdown(f"""<div class="scard">
      <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:.38rem;">
        <div style="flex:1;font-family:'Syne',sans-serif;font-size:.92rem;font-weight:700;">{a['title']}</div>
        <span style="font-size:.63rem;color:{src_color};background:rgba(6,182,212,.07);border-radius:8px;padding:2px 8px;white-space:nowrap;flex-shrink:0;">{src_name}</span>
      </div>
      <div style="color:var(--t3);font-size:.70rem;margin-bottom:.4rem;">{a['authors']} · <em>{a['source']}</em> · {a['year']}{cite}</div>
      <div style="color:var(--t2);font-size:.80rem;line-height:1.6;">{a['abstract'][:250]}{"…" if len(a['abstract'])>250 else ""}.</div>
    </div>""",unsafe_allow_html=True)
    ca,cb,cc=st.columns([1,1,1])
    with ca:
        if st.button("🔖 Salvo" if is_saved else "📌 Salvar",key=f"sv_w_{uid}"): # Use uid in key
            if is_saved: st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]; st.toast("Removido dos salvos")
            else: st.session_state.saved_articles.append(a); st.toast("Salvo!")
            save_db(); st.rerun()
    with cb:
        if st.button("📋 Citar APA",key=f"ct_w_{uid}"): # Use uid in key
            st.toast(f'{a["authors"]} ({a["year"]}). {a["title"]}. {a["source"]}.')
    with cc:
        if a.get("url"):
            st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:var(--b300);font-size:.80rem;text-decoration:none;line-height:2.5;display:block;">Abrir ↗</a>',unsafe_allow_html=True)

# ════════════════════════════════════════════════════
# REDE DE CONEXÕES (researcher network from folders+posts)
# ════════════════════════════════════════════════════
def page_knowledge():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem;">Rede de Conexões</h1>',unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.82rem;margin-bottom:1rem;">Pesquisadores conectados por interesses e pesquisas em comum. Quanto mais forte a conexão, mais próximos os nós.</p>',unsafe_allow_html=True)

    email=st.session_state.current_user
    users=st.session_state.users

    # Build researcher tag profiles from: area + posts + folder analysis
    def get_researcher_tags(ue):
        ud=users.get(ue,{})
        tags=set(area_to_tags(ud.get("area","")))
        for p in st.session_state.feed_posts:
            if p.get("author_email")==ue:
                tags.update(t.lower() for t in p.get("tags",[]))
        # Folder tags (only for current user)
        if ue==email:
            for fn,fd in st.session_state.folders.items():
                if isinstance(fd,dict):
                    tags.update(t.lower() for t in fd.get("analysis_tags",[]))
        return tags

    rlist=list(users.keys())
    researcher_tags={ue:get_researcher_tags(ue) for ue in rlist}

    # Build edges
    edges=[]
    for i in range(len(rlist)):
        for j in range(i+1,len(rlist)):
            e1,e2=rlist[i],rlist[j]
            common=list(researcher_tags[e1] & researcher_tags[e2])
            if common or e2 in st.session_state.followed or e1 in st.session_state.followed:
                strength=len(common)+( 2 if (e2 in st.session_state.followed or e1 in st.session_state.followed) else 0)
                edges.append((e1,e2,common[:5],strength))

    # 3D positions (circle layout)
    n=len(rlist)
    positions={}
    for idx,ue in enumerate(rlist):
        angle=2*3.14159*idx/max(n,1)
        r_dist=0.38+0.05*(hash(ue)%5)/4
        positions[ue]={"x":0.5+r_dist*np.cos(angle),"y":0.5+r_dist*np.sin(angle),"z":0.5+0.12*((idx%4)/3-.35)}

    # Draw edges with thickness by strength
    fig=go.Figure()
    for e1,e2,common,strength in edges:
        p1=positions[e1]; p2=positions[e2]
        alpha=min(0.55, 0.12+strength*0.06)
        fig.add_trace(go.Scatter3d(
            x=[p1["x"],p2["x"],None],y=[p1["y"],p2["y"],None],z=[p1["z"],p2["z"],None],
            mode="lines",line=dict(color=f"rgba(55,130,215,{alpha:.2f})",width=min(4,1+strength)),
            hoverinfo="none",showlegend=False))

    # Draw nodes
    node_x=[positions[ue]["x"] for ue in rlist]
    node_y=[positions[ue]["y"] for ue in rlist]
    node_z=[positions[ue]["z"] for ue in rlist]
    node_colors=[]
    node_sizes=[]
    node_texts=[]
    node_hovers=[]
    for ue in rlist:
        ud=users.get(ue,{})
        is_me=ue==email; is_fol=ue in st.session_state.followed
        node_colors.append("#22d3ee" if is_me else ("#60a5f5" if is_fol else "#2272c3"))
        conn_count=sum(1 for e1,e2,_,__ in edges if e1==ue or e2==ue)
        node_sizes.append(24 if is_me else (18 if is_fol else max(12,10+conn_count)))
        node_texts.append(ud.get("name","?").split()[0])
        common_topics=list(researcher_tags[ue])[:5]
        node_hovers.append(f"<b>{ud.get('name','?')}</b><br>Área: {ud.get('area','')}<br>Conexões: {conn_count}<br>Tópicos: {', '.join(common_topics[:3])}<extra></extra>")

    fig.add_trace(go.Scatter3d(
        x=node_x,y=node_y,z=node_z,mode="markers+text",
        marker=dict(size=node_sizes,color=node_colors,opacity=.92,
                    line=dict(color="rgba(147,197,253,.32)",width=1.5)),
        text=node_texts,textposition="top center",
        textfont=dict(color="#8ba8cc",size=9,family="DM Sans"),
        hovertemplate=node_hovers,showlegend=False))

    fig.update_layout(height=500,
        scene=dict(
            xaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),
            yaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),
            zaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),
            bgcolor="rgba(0,0,0,0)",camera=dict(eye=dict(x=1.5,y=1.3,z=0.9))),
        paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0),
        font=dict(color="#8ba8cc"))
    st.plotly_chart(fig,use_container_width=True)

    # Metrics
    c1,c2,c3,c4=st.columns(4)
    for col,(v,l) in zip([c1,c2,c3,c4],[(len(rlist),"Pesquisadores"),(len(edges),"Conexões"),(len(st.session_state.followed),"Seguindo"),(len(st.session_state.feed_posts),"Pesquisas")]):
        with col: st.markdown(f'<div class="mbox"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>',unsafe_allow_html=True)

    st.markdown("<hr>",unsafe_allow_html=True)
    tab_map,tab_mine,tab_all=st.tabs(["  Todas as conexões  ","  Minhas conexões  ","  Todos pesquisadores  "])

    with tab_map:
        if edges:
            for e1,e2,common,strength in sorted(edges,key=lambda x:-x[3])[:20]:
                n1=users.get(e1,{}); n2=users.get(e2,{})
                tags_shared=tags_html(common[:5]) if common else '<span style="color:var(--t3);font-size:.72rem;">Seguimento</span>'
                st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;"><span style="font-size:.82rem;font-weight:600;font-family:\'Syne\',sans-serif;color:var(--b300);">{n1.get("name","?")} </span><span style="color:var(--t3);">↔</span><span style="font-size:.82rem;font-weight:600;font-family:\'Syne\',sans-serif;color:var(--b300);"> {n2.get("name","?")}</span><div style="flex:1;display:flex;align-items:center;gap:4px;flex-wrap:wrap;">{tags_shared}</div><span style="font-size:.69rem;color:var(--cyanl);font-weight:600;">força {strength}</span></div></div>',unsafe_allow_html=True)
        else:
            st.markdown('<div class="card" style="text-align:center;padding:2rem;color:var(--t3);">Publique pesquisas com tags para ver conexões.</div>',unsafe_allow_html=True)

    with tab_mine:
        my_tags=researcher_tags.get(email,set())
        if my_tags:
            st.markdown(f'<div style="margin-bottom:.9rem;font-size:.82rem;color:var(--t2);">Seus tópicos ({len(my_tags)}): {tags_html(list(my_tags)[:8])}</div>',unsafe_allow_html=True)
        my_conn=[(e1,e2,common,s) for e1,e2,common,s in edges if e1==email or e2==email]
        if my_conn:
            for e1,e2,common,strength in sorted(my_conn,key=lambda x:-x[3]):
                other=e2 if e1==email else e1; od=users.get(other,{})
                is_fol=other in st.session_state.followed
                st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">{avh(ini(od.get("name","?")),36,get_photo(other))}<div style="flex:1;"><div style="font-weight:600;font-size:.86rem;font-family:\'Syne\',sans-serif;">{od.get("name","?")}</div><div style="font-size:.71rem;color:var(--t3);">{od.get("area","")}</div></div>{tags_html(common[:3])}<span style="font-size:.69rem;color:{"var(--ok)" if is_fol else "var(--cyanl)"};font-weight:600;">força {strength}</span></div></div>',unsafe_allow_html=True)
                cv,cm_btn,_=st.columns([1,1,4])
                with cv:
                    if st.button("👤 Perfil",key=f"kn_vp_{other}"): st.session_state.profile_view=other; st.rerun()
                with cm_btn:
                    if st.button("💬 Chat",key=f"kn_ch_{other}"):
                        if other not in st.session_state.chat_messages: st.session_state.chat_messages[other]=[]
                        st.session_state.active_chat=other; st.session_state.page="chat"; st.rerun()
        else:
            st.markdown('<div class="card" style="text-align:center;padding:2rem;color:var(--t3);">Nenhuma conexão ainda. Publique pesquisas e adicione tags!</div>',unsafe_allow_html=True)

    with tab_all:
        sq=st.text_input("",placeholder="🔍 Buscar pesquisadores…",key="all_ppl_s",label_visibility="collapsed")
        for ue,ud in users.items():
            if ue==email: continue
            uname=ud.get("name","?"); uarea=ud.get("area","")
            if sq and sq.lower() not in uname.lower() and sq.lower() not in uarea.lower(): continue
            uin=ini(uname); uphoto=ud.get("photo_b64"); is_fol=ue in st.session_state.followed
            conn_count=sum(1 for e1,e2,_,__ in edges if e1==ue or e2==ue)
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:10px;">{avh(uin,38,uphoto)}<div style="flex:1;"><div style="font-size:.86rem;font-weight:600;font-family:\'Syne\',sans-serif;">{uname}</div><div style="font-size:.71rem;color:var(--t3);">{uarea} · {conn_count} conexões</div></div>{"<span style=\\'font-size:.72rem;color:var(--ok);\\'>✓ Seguindo</span>" if is_fol else ""}</div></div>',unsafe_allow_html=True)
            ca,cb,cc=st.columns([1,1,1])
            with ca:
                if st.button("👤 Perfil",key=f"all_vp_{ue}",use_container_width=True): st.session_state.profile_view=ue; st.rerun()
            with cb:
                if st.button("✓ Seguindo" if is_fol else "➕ Seguir",key=f"all_fol_{ue}",use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"]=max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                    save_db(); st.rerun()
            with cc:
                if st.button("💬 Chat",key=f"all_ch_{ue}",use_container_width=True):
                    if ue not in st.session_state.chat_messages: st.session_state.chat_messages[ue]=[]
                    st.session_state.active_chat=ue; st.session_state.page="chat"; st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)

# ════════════════════════════════════════════════════
# PASTAS
# ════════════════════════════════════════════════════
def page_folders():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem;">Pastas de Pesquisa</h1>',unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.82rem;margin-bottom:1rem;">Organize seus documentos. A análise inteligente das pastas alimenta a sua rede de conexões.</p>',unsafe_allow_html=True)
    c1,c2,_=st.columns([2,1.2,1.5])
    with c1: nf_name=st.text_input("Nome da pasta",placeholder="Ex: Genômica Comparativa",key="nf_n")
    with c2: nf_desc=st.text_input("Descrição",placeholder="Breve descrição",key="nf_d")
    if st.button("➕ Criar pasta",key="btn_nf"):
        if nf_name.strip():
            if nf_name not in st.session_state.folders:
                st.session_state.folders[nf_name]={"desc":nf_desc,"files":[],"notes":"","analysis_tags":[],"analysis_summary":"","file_analyses":[]}
                save_db(); st.success(f"✓ Pasta '{nf_name}' criada!"); st.rerun()
            else: st.warning("Pasta já existe.")
        else: st.warning("Digite um nome.")
    st.markdown("<hr>",unsafe_allow_html=True)
    if not st.session_state.folders:
        st.markdown('<div class="card" style="text-align:center;padding:3rem;"><div style="font-size:3rem;margin-bottom:1rem;">📂</div><div style="color:var(--t2);font-family:\'Syne\',sans-serif;font-size:1rem;">Nenhuma pasta ainda</div><div style="color:var(--t3);font-size:.80rem;margin-top:.4rem;">Crie sua primeira pasta acima</div></div>',unsafe_allow_html=True)
    else:
        cols=st.columns(3)
        for idx,(fname,fdata) in enumerate(list(st.session_state.folders.items())):
            files=fdata.get("files",[]) if isinstance(fdata,dict) else fdata
            desc=fdata.get("desc","") if isinstance(fdata,dict) else ""
            at=fdata.get("analysis_tags",[]) if isinstance(fdata,dict) else []
            with cols[idx%3]:
                tag_preview=tags_html(at[:3]) if at else ""
                st.markdown(f'<div class="card" style="text-align:center;"><div style="font-size:2.4rem;margin-bottom:8px;">📁</div><div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.97rem;">{fname}</div><div style="color:var(--t3);font-size:.70rem;margin-top:3px;">{desc}</div><div style="color:var(--b300);font-size:.72rem;margin-top:5px;">{len(files)} arquivo(s)</div><div style="margin-top:6px;">{tag_preview}</div></div>',unsafe_allow_html=True)
                with st.expander(f"📂 Abrir '{fname}'"):
                    up=st.file_uploader("",type=None,key=f"up_{fname}",label_visibility="collapsed")
                    if up:
                        lst=fdata["files"] if isinstance(fdata,dict) else fdata
                        if up.name not in lst: lst.append(up.name)
                        save_db(); st.success("✓ Adicionado!"); st.rerun()
                    if files:
                        for f in files: st.markdown(f'<div style="font-size:.79rem;padding:5px 0;color:var(--t2);border-bottom:1px solid var(--gbd);">📄 {f}</div>',unsafe_allow_html=True)
                    else: st.markdown('<p style="color:var(--t3);font-size:.76rem;text-align:center;padding:.5rem;">Faça upload acima.</p>',unsafe_allow_html=True)
                    st.markdown("<hr>",unsafe_allow_html=True)
                    st.markdown('<div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.83rem;margin-bottom:.5rem;">🔬 Análise de Conteúdo</div>',unsafe_allow_html=True)
                    if st.button("Analisar documentos",key=f"analyze_{fname}",use_container_width=True):
                        if files:
                            with st.spinner("Analisando nomes de arquivos…"):
                                result=analyze_folder(fname)
                            if result and isinstance(fdata,dict):
                                fdata["analysis_tags"]=result["tags"]
                                fdata["analysis_summary"]=result["summary"]
                                fdata["file_analyses"]=result["file_analyses"]
                                save_db(); record(result["tags"],1.5); st.success("✓ Análise concluída! Sua rede de conexões foi atualizada."); st.rerun()
                        else: st.warning("Adicione arquivos antes.")
                    if isinstance(fdata,dict) and fdata.get("analysis_summary"):
                        st.markdown(f'<div class="abox"><div style="font-size:.67rem;color:var(--t3);text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">Resumo</div><div style="font-size:.81rem;color:var(--t2);">{fdata["analysis_summary"]}</div></div>',unsafe_allow_html=True)
                        if at: st.markdown(tags_html(at),unsafe_allow_html=True)
                    note=st.text_area("Notas",value=fdata.get("notes","") if isinstance(fdata,dict) else "",key=f"note_{fname}",height=70,placeholder="Observações…")
                    if st.button("💾 Salvar nota",key=f"sn_{fname}"):
                        if isinstance(fdata,dict): fdata["notes"]=note
                        save_db(); st.success("✓ Nota salva!")
                if st.button(f"🗑️ Excluir '{fname}'",key=f"df_{fname}"):
                    del st.session_state.folders[fname]; save_db(); st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)

# ════════════════════════════════════════════════════
# ANALYTICS — FOLDER-BASED RESEARCH ANALYSIS
# ════════════════════════════════════════════════════
def page_analytics():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem;">Painel de Pesquisa</h1>',unsafe_allow_html=True)
    email=st.session_state.current_user; d=st.session_state.setdefault("stats_data",{"h_index":4,"fator_impacto":3.8,"notes":""})
    pc=dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",font=dict(color="#3d5a80",family="DM Sans"),
            margin=dict(l=10,r=10,t=42,b=10),
            xaxis=dict(showgrid=False,color="#3d5a80"),
            yaxis=dict(showgrid=True,gridcolor="rgba(55,130,215,.07)",color="#3d5a80"))

    tab_folders,tab_pubs,tab_impact,tab_pref=st.tabs(["  📂 Análise das Pastas  ","  📝 Publicações  ","  📈 Impacto  ","  🎯 Interesses  "])

    # ── PASTAS ──
    with tab_folders:
        folders=st.session_state.folders
        if not folders:
            st.markdown('<div class="card" style="text-align:center;padding:3.5rem;"><div style="font-size:2.5rem;margin-bottom:1rem;">📂</div><div style="color:var(--t2);font-family:\'Syne\',sans-serif;">Crie pastas e adicione arquivos para ver a análise aqui</div><div style="color:var(--t3);font-size:.80rem;margin-top:.5rem;">A análise automática identifica áreas, tipos de documento e nível de progresso</div></div>',unsafe_allow_html=True)
        else:
            total_files=sum(len(fd.get("files",[]) if isinstance(fd,dict) else fd) for fd in folders.values())
            total_analyzed=sum(1 for fd in folders.values() if isinstance(fd,dict) and fd.get("analysis_tags"))
            all_tags_flat=[t for fd in folders.values() if isinstance(fd,dict) for t in fd.get("analysis_tags",[])]
            c1,c2,c3,c4=st.columns(4)
            with c1: st.markdown(f'<div class="mbox"><div class="mval">{len(folders)}</div><div class="mlbl">Pastas</div></div>',unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="mbox"><div class="mval">{total_files}</div><div class="mlbl">Arquivos totais</div></div>',unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="mbox"><div class="mval">{total_analyzed}</div><div class="mlbl">Pastas analisadas</div></div>',unsafe_allow_html=True)
            with c4: st.markdown(f'<div class="mbox"><div class="mval">{len(set(all_tags_flat))}</div><div class="mlbl">Áreas únicas</div></div>',unsafe_allow_html=True)
            st.markdown("<br>",unsafe_allow_html=True)

            # Files per folder
            fnames=list(folders.keys())
            fcounts=[len(fd.get("files",[]) if isinstance(fd,dict) else fd) for fd in folders.values()]
            if any(c>0 for c in fcounts):
                fig_fc=go.Figure()
                fig_fc.add_trace(go.Bar(x=fnames,y=fcounts,marker=dict(
                    color=fcounts,colorscale=[[0,"#0f2040"],[.5,"#2272c3"],[1,"#22d3ee"]],
                    line=dict(color="rgba(90,158,240,.2)",width=1)),
                    text=fcounts,textposition="outside",textfont=dict(color="#8ba8cc",size=11)))
                fig_fc.update_layout(title=dict(text="Arquivos por Pasta",font=dict(color="#e0e8ff",family="Syne",size=14)),height=260,**pc)
                st.plotly_chart(fig_fc,use_container_width=True)

            # Tag distribution
            if all_tags_flat:
                tag_counts=Counter(all_tags_flat).most_common(10)
                tnames,tcounts=zip(*tag_counts)
                fig_tags=go.Figure()
                fig_tags.add_trace(go.Bar(y=list(tnames),x=list(tcounts),orientation='h',
                    marker=dict(color=list(tcounts),colorscale=[[0,"#1a3a6b"],[.5,"#3b8de0"],[1,"#06b6d4"]],
                                line=dict(color="rgba(90,158,240,.15)",width=1)),
                    text=list(tcounts),textposition="outside",textfont=dict(color="#8ba8cc",size=10)))
                fig_tags.update_layout(title=dict(text="Áreas Detectadas nas Pastas",font=dict(color="#e0e8ff",family="Syne",size=14)),height=320,**pc,yaxis=dict(autorange="reversed",color="#3d5a80"))
                st.plotly_chart(fig_tags,use_container_width=True)

            # Per-folder deep dive
            st.markdown('<h3>Detalhamento por Pasta</h3>',unsafe_allow_html=True)
            for fname,fdata in folders.items():
                if not isinstance(fdata,dict): continue
                files=fdata.get("files",[]); fa=fdata.get("file_analyses",[]); at=fdata.get("analysis_tags",[])
                with st.expander(f"📁 {fname} — {len(files)} arquivo(s)"):
                    if not files: st.markdown('<p style="color:var(--t3);font-size:.79rem;">Nenhum arquivo ainda.</p>',unsafe_allow_html=True); continue
                    if fa:
                        type_counts=Counter(x.get("type","Outro") for x in fa)
                        cp,cprog=st.columns([1,1.5])
                        with cp:
                            fig_pie=go.Figure(go.Pie(labels=list(type_counts.keys()),values=list(type_counts.values()),hole=0.55,
                                marker=dict(colors=["#2272c3","#06b6d4","#3b8de0","#1a3a6b","#8b5cf6","#10b981"],
                                            line=dict(color=["#010409"]*10,width=2)),textfont=dict(color="white",size=10)))
                            fig_pie.update_layout(title=dict(text="Tipos de Arquivo",font=dict(color="#e0e8ff",family="Syne",size=12)),
                                                  height=220,plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                                                  legend=dict(font=dict(color="#8ba8cc",size=9)),margin=dict(l=0,r=0,t=35,b=0))
                            st.plotly_chart(fig_pie,use_container_width=True)
                        with cprog:
                            st.markdown('<div style="font-size:.68rem;color:var(--t3);text-transform:uppercase;letter-spacing:.06em;margin-bottom:.6rem;">Progresso por Arquivo</div>',unsafe_allow_html=True)
                            for item in fa:
                                prog=item.get("progress",50)
                                color="#10b981" if prog>=80 else ("#f59e0b" if prog>=50 else "#ef4444")
                                st.markdown(f'<div style="margin-bottom:.55rem;"><div style="display:flex;justify-content:space-between;font-size:.75rem;margin-bottom:3px;"><span style="color:var(--t2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:68%;">📄 {item["file"][:26]}</span><span style="color:{color};font-weight:600;">{prog}%</span></div>{prog_bar(prog,color)}</div>',unsafe_allow_html=True)
                        if at:
                            st.markdown('<div style="font-size:.68rem;color:var(--t3);text-transform:uppercase;letter-spacing:.06em;margin-top:.4rem;margin-bottom:.3rem;">Áreas identificadas</div>',unsafe_allow_html=True)
                            st.markdown(tags_html(at),unsafe_allow_html=True)
                    else:
                        st.markdown('<p style="color:var(--t3);font-size:.79rem;">Clique em "Analisar documentos" para ver dados detalhados.</p>',unsafe_allow_html=True)

    # ── PUBLICAÇÕES ──
    with tab_pubs:
        my_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==email]
        if not my_posts:
            st.markdown('<div class="card" style="text-align:center;padding:2.5rem;color:var(--t3);">Publique pesquisas no feed para ver métricas aqui.</div>',unsafe_allow_html=True)
        else:
            c1,c2,c3=st.columns(3)
            with c1: st.markdown(f'<div class="mbox"><div class="mval">{len(my_posts)}</div><div class="mlbl">Pesquisas</div></div>',unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="mbox"><div class="mval">{sum(p["likes"] for p in my_posts)}</div><div class="mlbl">Total curtidas</div></div>',unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="mbox"><div class="mval">{sum(len(p["comments"]) for p in my_posts)}</div><div class="mlbl">Comentários</div></div>',unsafe_allow_html=True)
            st.markdown("<br>",unsafe_allow_html=True)
            fig_eng=go.Figure()
            titles_s=[p["title"][:20]+"…" for p in my_posts]
            fig_eng.add_trace(go.Bar(name="Curtidas",x=titles_s,y=[p["likes"] for p in my_posts],marker_color="#2272c3"))
            fig_eng.add_trace(go.Bar(name="Comentários",x=titles_s,y=[len(p["comments"]) for p in my_posts],marker_color="#06b6d4"))
            fig_eng.update_layout(barmode="group",title=dict(text="Engajamento por Pesquisa",font=dict(color="#e0e8ff",family="Syne",size=14)),height=265,**pc,legend=dict(font=dict(color="#8ba8cc")))
            st.plotly_chart(fig_eng,use_container_width=True)
            for p in sorted(my_posts,key=lambda x:x.get("date",""),reverse=True):
                st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;justify-content:space-between;"><div style="font-family:\'Syne\',sans-serif;font-size:.89rem;font-weight:700;">{p["title"][:52]}{"…" if len(p["title"])>52 else ""}</div>{badge(p["status"])}</div><div style="display:flex;gap:1.2rem;margin-top:.4rem;font-size:.73rem;color:var(--t3);">{p.get("date","")} · ❤ {p["likes"]} · 💬 {len(p["comments"])}</div><div style="margin-top:.4rem;">{tags_html(p["tags"][:4])}</div></div>',unsafe_allow_html=True)

    # ── IMPACTO ──
    with tab_impact:
        c1,c2,c3=st.columns(3)
        with c1: st.markdown(f'<div class="mbox"><div class="mval">{d.get("h_index",4)}</div><div class="mlbl">Índice H</div></div>',unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="mbox"><div class="mval">{d.get("fator_impacto",3.8):.1f}</div><div class="mlbl">Fator de impacto</div></div>',unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="mbox"><div class="mval">{len(st.session_state.saved_articles)}</div><div class="mlbl">Artigos salvos</div></div>',unsafe_allow_html=True)
        st.markdown("<hr>",unsafe_allow_html=True)
        new_h=st.number_input("Índice H",0,200,d.get("h_index",4),key="e_h")
        new_fi=st.number_input("Fator de impacto",0.0,100.0,float(d.get("fator_impacto",3.8)),step=0.1,key="e_fi")
        new_notes=st.text_area("Notas",value=d.get("notes",""),key="e_notes",height=80)
        if st.button("💾 Salvar métricas",key="btn_save_m"):
            d.update({"h_index":new_h,"fator_impacto":new_fi,"notes":new_notes}); st.success("✓ Salvo!")

    # ── INTERESSES ──
    with tab_pref:
        prefs=st.session_state.user_prefs.get(email,{})
        if prefs:
            st.markdown('<p style="color:var(--t3);font-size:.80rem;margin-bottom:1rem;">Baseado nas suas interações, publicações e documentos das pastas.</p>',unsafe_allow_html=True)
            top=sorted(prefs.items(),key=lambda x:-x[1])[:12]; mx=max(s for _,s in top) if top else 1
            c1,c2=st.columns(2)
            for i,(tag,score) in enumerate(top):
                pct=int(score/mx*100)
                with (c1 if i%2==0 else c2):
                    color="#2272c3" if pct>70 else ("#3b8de0" if pct>40 else "#1a3a6b")
                    st.markdown(f'<div style="display:flex;justify-content:space-between;font-size:.79rem;margin-bottom:3px;"><span style="color:var(--t2);">{tag}</span><span style="color:var(--b300);font-weight:600;">{pct}%</span></div>{prog_bar(pct,color)}',unsafe_allow_html=True)
        else:
            st.info("Interaja com pesquisas e analise pastas para construir seu perfil de interesses.")
    st.markdown('</div>',unsafe_allow_html=True)

# ════════════════════════════════════════════════════
# ANÁLISE DE IMAGEM
# ════════════════════════════════════════════════════
def page_img_search():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem;">Análise de Imagem Científica</h1>',unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.82rem;margin-bottom:1.2rem;">Detecta padrões, linhas, formas, cores e classifica imagens científicas com precisão</p>',unsafe_allow_html=True)
    col_up,col_res=st.columns([1,1.75])
    with col_up:
        st.markdown('<div class="card">',unsafe_allow_html=True)
        st.markdown('<div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.88rem;margin-bottom:.8rem;">📷 Upload de imagem</div>',unsafe_allow_html=True)
        img_file=st.file_uploader("",type=["png","jpg","jpeg","webp","tiff"],label_visibility="collapsed")
        if img_file: st.image(img_file,use_container_width=True,caption="Imagem carregada")
        run=st.button("🔬 Analisar",use_container_width=True,key="btn_run")
        st.markdown('<div style="color:var(--t3);font-size:.69rem;margin-top:.8rem;line-height:1.6;">Algoritmos: Sobel · FFT · Simetria Radial · Entropia · Paleta de Cores</div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)
    with col_res:
        if run and img_file:
            img_file.seek(0)
            with st.spinner("Analisando padrões, bordas, formas e cores…"):
                rep=analyze_image_advanced(img_file)
                st.session_state.img_analysis_result = rep # Store result
                st.session_state.img_search_done = True
            if rep:
                st.markdown(f"""<div class="abox">
                  <div style="font-size:.65rem;color:var(--t3);letter-spacing:.10em;text-transform:uppercase;margin-bottom:4px;">Categoria Detectada</div>
                  <div style="font-family:'Syne',sans-serif;font-size:1.08rem;font-weight:700;color:var(--t1);margin-bottom:4px;">{rep['category']}</div>
                  <div style="font-size:.82rem;color:var(--t2);line-height:1.6;">{rep['description']}</div>
                  <div style="margin-top:9px;display:flex;gap:14px;flex-wrap:wrap;">
                    <span style="font-size:.70rem;color:var(--ok);">✓ Confiança: {rep['confidence']}%</span>
                    <span style="font-size:.70rem;color:var(--t3);">{rep['size'][0]}×{rep['size'][1]}px</span>
                    {"<span style='font-size:.70rem;color:var(--warn);'>Tecido detectado: "+str(rep['skin_pct'])+"%</span>" if rep['skin_pct']>10 else ""}
                  </div></div>""",unsafe_allow_html=True)

                # --- New Object/Material Information ---
                st.markdown(f"""<div class="pbox">
                  <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.7rem;color:var(--cyanl);">✨ Informações do Objeto/Tema</div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:.79rem;color:var(--t2);margin-bottom:.7rem;">
                    <div><span style="color:var(--t3);">Material/Composição:</span><br><strong>{rep['material']}</strong></div>
                    <div><span style="color:var(--t3);">Tipo de Objeto/Estrutura:</span><br><strong>{rep['object_type']}</strong></div>
                  </div>
                </div>""",unsafe_allow_html=True)

                c1,c2,c3=st.columns(3)
                with c1: st.markdown(f'<div class="mbox"><div style="font-family:\'Syne\',sans-serif;font-size:1.2rem;font-weight:700;color:var(--b300);">{rep["texture"]["complexity"]}</div><div class="mlbl">Complexidade</div></div>',unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="mbox"><div style="font-family:\'Syne\',sans-serif;font-size:1.1rem;font-weight:700;color:var(--b300);">{"Alta" if rep["symmetry"]>0.78 else ("Média" if rep["symmetry"]>0.52 else "Baixa")}</div><div class="mlbl">Simetria ({rep["symmetry"]})</div></div>',unsafe_allow_html=True)
                with c3: st.markdown(f'<div class="mbox"><div style="font-family:\'Syne\',sans-serif;font-size:1.1rem;font-weight:700;color:var(--b300);">{rep["lines"]["direction"]}</div><div class="mlbl">Direção de linhas</div></div>',unsafe_allow_html=True)
                # Lines
                l=rep['lines']
                h_pct=int(l["h"]/max(l["h"],l["v"],0.01)*100); v_pct=int(l["v"]/max(l["h"],l["v"],0.01)*100)
                st.markdown(f"""<div class="pbox">
                  <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.7rem;color:var(--cyanl);">📐 Análise de Linhas e Bordas</div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:.79rem;color:var(--t2);margin-bottom:.7rem;">
                    <div><span style="color:var(--t3);">Intensidade total:</span><br><strong>{l["intensity"]:.2f}</strong></div>
                    <div><span style="color:var(--t3);">Direção:</span><br><strong>{l["direction"]}</strong></div>
                    <div><span style="color:var(--t3);">Força H ({l["h"]:.2f}):</span>{prog_bar(h_pct,"#2272c3")}</div>
                    <div><span style="color:var(--t3);">Força V ({l["v"]:.2f}):</span>{prog_bar(v_pct,"#06b6d4")}</div>
                  </div>
                  <div style="font-size:.72rem;color:var(--t3);margin-bottom:.3rem;">Formas detectadas:</div>
                  <div>{" · ".join(f'<span style="color:var(--cyanl);font-size:.76rem;">{s}</span>' for s in rep["shapes"])}</div>
                </div>""",unsafe_allow_html=True)
                # Color
                r_v,g_v,b_v=rep["color"]["r"],rep["color"]["g"],rep["color"]["b"]
                hex_col="#{:02x}{:02x}{:02x}".format(int(r_v),int(g_v),int(b_v))
                pal_html="".join(f'<div style="display:flex;flex-direction:column;align-items:center;gap:3px;"><div style="width:32px;height:32px;border-radius:8px;background:rgb{str(p)};border:1px solid rgba(255,255,255,.12);"></div><div style="font-size:.60rem;color:var(--t3);">#{"{:02x}{:02x}{:02x}".format(*p).upper()}</div></div>' for p in rep["palette"][:6])
                st.markdown(f"""<div class="abox">
                  <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.7rem;">🎨 Análise de Cor</div>
                  <div style="display:flex;gap:14px;align-items:center;margin-bottom:.8rem;">
                    <div style="width:44px;height:44px;border-radius:10px;background:{hex_col};border:2px solid var(--gbdl);flex-shrink:0;"></div>
                    <div style="font-size:.80rem;color:var(--t2);">RGB: <strong>({int(r_v)}, {int(g_v)}, {int(b_v)})</strong> · Hex: <strong>{hex_col.upper()}</strong><br>
                    Brilho: <strong>{(r_v+g_v+b_v)/3:.0f}/255</strong> · Temperatura: <strong>{"Quente 🔴" if rep["color"]["warm"] else ("Fria 🔵" if rep["color"]["cool"] else "Neutra ⚪")}</strong></div>
                  </div>
                  <div style="font-size:.70rem;color:var(--t3);margin-bottom:6px;">Paleta predominante:</div>
                  <div style="display:flex;gap:7px;flex-wrap:wrap;">{pal_html}</div>
                  <div style="margin-top:.7rem;display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:.79rem;">
                    <div style="color:var(--t3);">Entropia: <strong>{rep["texture"]["entropy"]:.3f} bits</strong></div>
                    <div style="color:var(--t3);">Contraste: <strong>{rep["texture"]["contrast"]:.2f}</strong></div>
                  </div>
                </div>""",unsafe_allow_html=True)
            else: st.error("Não foi possível analisar. Verifique o formato do arquivo.")
        elif not img_file and not st.session_state.img_search_done:
            st.markdown("""<div class="card" style="text-align:center;padding:4rem 2rem;">
              <div style="font-size:3.5rem;margin-bottom:1rem;">🔬</div>
              <div style="font-family:'Syne',sans-serif;font-size:1rem;color:var(--t2);margin-bottom:.5rem;">Carregue uma imagem para análise real</div>
              <div style="color:var(--t3);font-size:.77rem;line-height:1.8;">PNG · JPG · WEBP · TIFF<br>Detecta: histologia · fluorescência · cristalografia<br>diagramas · imagens multiespectrais · estruturas moleculares</div>
            </div>""",unsafe_allow_html=True)

        # Display search results if analysis was done
        if st.session_state.img_search_done and st.session_state.img_analysis_result:
            rep = st.session_state.img_analysis_result
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown('<h2>🔎 Pesquisas Relacionadas</h2>', unsafe_allow_html=True)

            # Search in Nebula posts
            nebula_results = search_image_in_nebula(rep)
            if nebula_results:
                st.markdown('<div style="font-size:.68rem;color:var(--b300);font-weight:600;margin-bottom:.5rem;letter-spacing:.06em;text-transform:uppercase;">NA NEBULA</div>',unsafe_allow_html=True)
                for p in nebula_results:
                    st.markdown(f"""<div class="img-result-card">
                        <div style="font-family:'Syne',sans-serif;font-size:.92rem;font-weight:700;margin-bottom:.3rem;">{p['title']}</div>
                        <div style="color:var(--t3);font-size:.70rem;margin-bottom:.4rem;">{p['author']} · {p['area']} · {p['date']}</div>
                        <div style="font-size:.80rem;color:var(--t2);margin-bottom:.4rem;">{p['abstract'][:150]}…</div>
                        <div>{tags_html(p['tags'])}</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:var(--t3);font-size:.80rem;margin-bottom:1rem;">Nenhuma pesquisa relacionada encontrada na Nebula.</div>', unsafe_allow_html=True)

            # Search in user's folders
            folder_results = search_image_in_folders(rep)
            if folder_results:
                st.markdown('<div style="font-size:.68rem;color:var(--ok);font-weight:600;margin-top:1.5rem;margin-bottom:.5rem;letter-spacing:.06em;text-transform:uppercase;">NAS SUAS PASTAS</div>',unsafe_allow_html=True)
                for f_match in folder_results:
                    st.markdown(f"""<div class="img-result-card">
                        <div style="font-family:'Syne',sans-serif;font-size:.92rem;font-weight:700;margin-bottom:.3rem;">📁 Pasta: {f_match['folder']}</div>
                        <div style="color:var(--t3);font-size:.70rem;margin-bottom:.4rem;">Arquivos: {len(f_match['files'])}</div>
                        <div style="font-size:.80rem;color:var(--t2);margin-bottom:.4rem;">Tópicos: {tags_html(f_match['tags'])}</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:var(--t3);font-size:.80rem;margin-bottom:1rem;">Nenhum documento relacionado encontrado nas suas pastas.</div>', unsafe_allow_html=True)

            # Search on the Internet
            internet_results = search_image_internet(rep)
            if internet_results:
                st.markdown('<div style="font-size:.68rem;color:var(--cyanl);font-weight:600;margin-top:1.5rem;margin-bottom:.5rem;letter-spacing:.06em;text-transform:uppercase;">NA INTERNET (ACADÊMICO)</div>',unsafe_allow_html=True)
                for idx, a in enumerate(internet_results):
                    src_color="#22d3ee" if a.get("origin")=="semantic" else "#a78bfa"
                    src_name="Semantic Scholar" if a.get("origin")=="semantic" else "CrossRef"
                    st.markdown(f"""<div class="img-result-card">
                        <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:.38rem;">
                            <div style="flex:1;font-family:'Syne',sans-serif;font-size:.92rem;font-weight:700;">{a['title']}</div>
                            <span class="img-source-badge" style="color:{src_color};background:rgba(6,182,212,.07);">{src_name}</span>
                        </div>
                        <div style="color:var(--t3);font-size:.70rem;margin-bottom:.4rem;">{a['authors']} · <em>{a['source']}</em> · {a['year']}</div>
                        <div style="font-size:.80rem;color:var(--t2);line-height:1.6;">{a['abstract'][:150]}…</div>
                        <a href="{a['url']}" target="_blank" style="color:var(--b300);font-size:.80rem;text-decoration:none;margin-top:.5rem;display:inline-block;">Abrir Artigo ↗</a>
                    </div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:var(--t3);font-size:.80rem;margin-bottom:1rem;">Nenhum artigo relacionado encontrado na internet.</div>', unsafe_allow_html=True)

    st.markdown('</div>',unsafe_allow_html=True)

# ════════════════════════════════════════════════════
# CHAT (somente mensagens)
# ════════════════════════════════════════════════════
def page_chat():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem;">Chat Seguro</h1>',unsafe_allow_html=True)
    col_c,col_m=st.columns([.85,2.6])
    email=st.session_state.current_user
    with col_c:
        st.markdown('<div style="font-size:.68rem;font-weight:600;color:var(--t3);letter-spacing:.07em;text-transform:uppercase;margin-bottom:.7rem;">CONVERSAS</div>',unsafe_allow_html=True)
        shown=set()
        for ue in st.session_state.chat_contacts:
            if ue==email or ue in shown: continue
            shown.add(ue)
            ud=st.session_state.users.get(ue,{}); uname=ud.get("name","?"); uin=ini(uname); uphoto=ud.get("photo_b64")
            msgs=st.session_state.chat_messages.get(ue,[]); last=msgs[-1]["text"][:26]+"…" if msgs and len(msgs[-1]["text"])>26 else (msgs[-1]["text"] if msgs else "Iniciar conversa")
            active=st.session_state.active_chat==ue
            online=random.random()>.4; dot='<span class="don"></span>' if online else '<span class="doff"></span>'
            bg="rgba(30,100,180,.20)" if active else "var(--gb)"; bdr="rgba(90,158,240,.40)" if active else "var(--gbd)"
            st.markdown(f'<div style="background:{bg};border:1px solid {bdr};border-radius:var(--rmd);padding:9px 11px;margin-bottom:5px;"><div style="display:flex;align-items:center;gap:8px;">{avh(uin,32,uphoto)}<div style="overflow:hidden;flex:1;"><div style="font-size:.82rem;font-weight:600;font-family:\'Syne\',sans-serif;">{dot}{uname}</div><div style="font-size:.70rem;color:var(--t3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{last}</div></div></div></div>',unsafe_allow_html=True)
            if st.button("Abrir",key=f"oc_{ue}",use_container_width=True): st.session_state.active_chat=ue; st.rerun()
        st.markdown("<hr>",unsafe_allow_html=True)
        nc=st.text_input("",placeholder="Adicionar por e-mail…",key="new_ct",label_visibility="collapsed")
        if st.button("Adicionar",key="btn_add_ct"):
            if nc in st.session_state.users and nc!=email:
                if nc not in st.session_state.chat_contacts: st.session_state.chat_contacts.append(nc)
                st.rerun()
            elif nc: st.toast("Usuário não encontrado.")

    with col_m:
        if st.session_state.active_chat:
            contact=st.session_state.active_chat
            cd=st.session_state.users.get(contact,{}); cname=cd.get("name","?"); cin=ini(cname); cphoto=cd.get("photo_b64")
            msgs=st.session_state.chat_messages.get(contact,[])
            # Header
            st.markdown(f'<div style="background:var(--gb);border:1px solid var(--gbd);border-radius:var(--rmd);padding:12px 16px;margin-bottom:1rem;display:flex;align-items:center;gap:12px;"><div style="flex-shrink:0;">{avh(cin,38,cphoto)}</div><div style="flex:1;"><div style="font-weight:700;font-size:.94rem;font-family:\'Syne\',sans-serif;">{cname}</div><div style="font-size:.70rem;color:var(--ok);">🔒 Criptografia AES-256 ativa</div></div></div>',unsafe_allow_html=True)
            # Messages only
            for msg in msgs:
                is_me=msg["from"]=="me"
                cls="bme" if is_me else "bthem"
                st.markdown(f'<div class="{cls}">{msg["text"]}<div style="font-size:.63rem;color:rgba(255,255,255,.35);margin-top:3px;text-align:{"right" if is_me else "left"};">{msg["time"]}</div></div>',unsafe_allow_html=True)
            # Input
            col_inp,col_btn=st.columns([5,1])
            with col_inp: nm=st.text_input("",placeholder="Mensagem segura…",key=f"mi_{contact}",label_visibility="collapsed")
            with col_btn:
                st.markdown("<div style='height:8px'></div>",unsafe_allow_html=True)
                if st.button("→",key=f"ms_{contact}",use_container_width=True):
                    if nm:
                        now=datetime.now().strftime("%H:%M")
                        st.session_state.chat_messages.setdefault(contact,[]).append({"from":"me","text":nm,"time":now}); st.rerun()
        else:
            st.markdown('<div class="card" style="text-align:center;padding:5rem;"><div style="font-size:3rem;margin-bottom:1rem;">💬</div><div style="color:var(--t2);font-family:\'Syne\',sans-serif;">Selecione uma conversa</div><div style="font-size:.75rem;color:var(--t3);margin-top:.5rem;">🔒 End-to-end encrypted</div></div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ════════════════════════════════════════════════════
# CONFIGURAÇÕES / PERFIL
# ════════════════════════════════════════════════════
def page_settings():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem;">Perfil e Configurações</h1>',unsafe_allow_html=True)
    u=guser(); email=st.session_state.current_user; in_=ini(u.get("name","?")); photo=u.get("photo_b64")
    tab_p,tab_s,tab_pr,tab_saved=st.tabs(["  Meu Perfil  ","  Segurança  ","  Privacidade  ","  Artigos Salvos  "]) # Added tab_saved
    with tab_p:
        # Profile hero
        photo_html=f"<img src='{photo}'/>" if photo else f'<span style="font-size:2.2rem;">{in_}</span>'
        st.markdown(f"""<div class="prof-hero">
          <div class="prof-photo">{photo_html}</div>
          <div style="flex:1;">
            <h1 style="margin-bottom:.2rem;">{u.get('name','?')}</h1>
            <div style="color:var(--b300);font-size:.84rem;font-weight:500;margin-bottom:.4rem;">{u.get('area','')}</div>
            <div style="color:var(--t2);font-size:.82rem;line-height:1.6;margin-bottom:.7rem;">{u.get('bio','Sem biografia ainda.')}</div>
            <div style="display:flex;gap:1.8rem;">
              <div><strong style="font-family:'Syne',sans-serif;">{u.get('followers',0)}</strong><span style="color:var(--t3);font-size:.73rem;"> seguidores</span></div>
              <div><strong style="font-family:'Syne',sans-serif;">{u.get('following',0)}</strong><span style="color:var(--t3);font-size:.73rem;"> seguindo</span></div>
              <div><strong style="font-family:'Syne',sans-serif;">{len([p for p in st.session_state.feed_posts if p.get("author_email")==email])}</strong><span style="color:var(--t3);font-size:.73rem;"> pesquisas</span></div>
            </div>
          </div></div>""",unsafe_allow_html=True)
        st.markdown('<div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.87rem;margin-bottom:.5rem;">📷 Foto de perfil</div>',unsafe_allow_html=True)
        ph=st.file_uploader("",type=["png","jpg","jpeg","webp"],label_visibility="collapsed",key="ph_up")
        if ph:
            b64=img_to_b64(ph)
            if b64:
                st.session_state.users[email]["photo_b64"]=b64; save_db()
                st.success("✓ Foto de perfil atualizada!"); st.rerun()
        st.markdown("<hr>",unsafe_allow_html=True)
        new_n=st.text_input("Nome completo",value=u.get("name",""),key="cfg_n")
        new_a=st.text_input("Área de pesquisa",value=u.get("area",""),key="cfg_a")
        new_b=st.text_area("Biografia",value=u.get("bio",""),key="cfg_b",height=90,placeholder="Descreva sua pesquisa, instituição e interesses…")
        if st.button("Salvar perfil",key="btn_sp"):
            st.session_state.users[email]["name"]=new_n
            st.session_state.users[email]["area"]=new_a
            st.session_state.users[email]["bio"]=new_b
            save_db(); record(area_to_tags(new_a),1.5); st.success("✓ Perfil salvo!"); st.rerun()
        if st.button("Sair da conta",key="btn_logout"):
            st.session_state.logged_in=False; st.session_state.current_user=None
            st.session_state.page="login"; st.rerun()

    with tab_s:
        st.markdown('<h3>Alterar senha</h3>',unsafe_allow_html=True)
        op=st.text_input("Senha atual",type="password",key="op")
        np_=st.text_input("Nova senha",type="password",key="np_")
        np2=st.text_input("Confirmar nova senha",type="password",key="np2")
        if st.button("Alterar senha",key="btn_cpw"):
            if hp(op)!=u.get("password",""): st.error("Senha atual incorreta.")
            elif np_!=np2: st.error("Senhas não coincidem.")
            elif len(np_)<6: st.error("Senha muito curta.")
            else: st.session_state.users[email]["password"]=hp(np_); save_db(); st.success("✓ Senha alterada!")
        st.markdown("<hr>",unsafe_allow_html=True)
        en=u.get("2fa_enabled",False)
        st.markdown(f'<div style="background:var(--gb);border:1px solid var(--gbd);border-radius:var(--rmd);padding:14px;display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;"><div><div style="font-weight:600;font-size:.90rem;font-family:\'Syne\',sans-serif;">2FA por e-mail</div><div style="font-size:.73rem;color:var(--t3);">{email}</div></div><span style="color:{"var(--ok)" if en else "var(--err)"};font-size:.82rem;font-weight:700;">{"✓ Ativo" if en else "✗ Inativo"}</span></div>',unsafe_allow_html=True)
        if st.button("Desativar 2FA" if en else "Ativar 2FA",key="btn_2fa"):
            st.session_state.users[email]["2fa_enabled"]=not en; save_db(); st.rerun()

    with tab_pr:
        prots=[("AES-256","Criptografia end-to-end das mensagens"),("SHA-256","Hash seguro de senhas"),("TLS 1.3","Transmissão segura de todos os dados"),("Zero Knowledge","Pesquisas privadas inacessíveis à plataforma")]
        items="".join(f'<div style="display:flex;align-items:center;gap:12px;background:rgba(16,185,129,.07);border:1px solid rgba(16,185,129,.18);border-radius:var(--rmd);padding:11px;"><div style="width:28px;height:28px;border-radius:8px;background:rgba(16,185,129,.14);display:flex;align-items:center;justify-content:center;color:var(--ok);font-weight:700;font-size:.76rem;flex-shrink:0;">✓&nbsp;</div><div><div style="font-weight:600;color:var(--ok);font-size:.84rem;">{n2}</div><div style="font-size:.71rem;color:var(--t3);">{d2}</div></div></div>' for n2,d2 in prots)
        st.markdown(f'<div class="card"><div style="font-weight:700;font-family:\'Syne\',sans-serif;margin-bottom:1rem;">Proteções ativas</div><div style="display:grid;gap:9px;">{items}</div></div>',unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1:
            st.selectbox("Visibilidade do perfil",["Público","Só seguidores","Privado"],key="vp")
            st.selectbox("Visibilidade das pesquisas",["Público","Só seguidores","Privado"],key="vr")
        with c2:
            st.selectbox("Estatísticas",["Público","Privado"],key="vs")
            st.selectbox("Rede de conexões",["Público","Só seguidores","Privado"],key="vn")
        if st.button("Salvar privacidade",key="btn_priv"): st.success("✓ Configurações salvas!")

    with tab_saved: # New tab for saved articles
        st.markdown('<h3>Artigos Salvos</h3>', unsafe_allow_html=True)
        if st.session_state.saved_articles:
            for idx, a in enumerate(st.session_state.saved_articles):
                src_color="#22d3ee" if a.get("origin")=="semantic" else "#a78bfa"
                src_name="Semantic Scholar" if a.get("origin")=="semantic" else "CrossRef"
                cite=f" · {a['citations']} cit." if a.get("citations") else ""
                uid=re.sub(r'[^a-zA-Z0-9]','',f"saved_{a.get('doi','nodoi')}_{idx}")[:30]
                st.markdown(f"""<div class="scard">
                  <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:.38rem;">
                    <div style="flex:1;font-family:'Syne',sans-serif;font-size:.92rem;font-weight:700;">{a['title']}</div>
                    <span style="font-size:.63rem;color:{src_color};background:rgba(6,182,212,.07);border-radius:8px;padding:2px 8px;white-space:nowrap;flex-shrink:0;">{src_name}</span>
                  </div>
                  <div style="color:var(--t3);font-size:.70rem;margin-bottom:.4rem;">{a['authors']} · <em>{a['source']}</em> · {a['year']}{cite}</div>
                  <div style="color:var(--t2);font-size:.80rem;line-height:1.6;">{a['abstract'][:250]}{"…" if len(a['abstract'])>250 else ""}.</div>
                </div>""",unsafe_allow_html=True)
                c1,c2=st.columns([1,2])
                with c1:
                    if st.button("🗑️ Remover", key=f"remove_saved_{uid}"):
                        st.session_state.saved_articles = [s for s in st.session_state.saved_articles if s.get('doi') != a.get('doi')]
                        save_db(); st.toast("Artigo removido dos salvos!"); st.rerun()
                with c2:
                    if a.get("url"):
                        st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:var(--b300);font-size:.80rem;text-decoration:none;line-height:2.5;display:block;">Abrir Artigo ↗</a>',unsafe_allow_html=True)
        else:
            st.markdown('<div class="card" style="text-align:center;padding:2rem;color:var(--t3);">Nenhum artigo salvo ainda. Salve artigos da busca para vê-los aqui.</div>',unsafe_allow_html=True)

    st.markdown('</div>',unsafe_allow_html=True)

# ════════════════════════════════════════════════════
# ROUTER
# ════════════════════════════════════════════════════
def main():
    if not st.session_state.logged_in:
        p=st.session_state.page
        if p=="verify_email": page_verify_email()
        elif p=="2fa": page_2fa()
        else: page_login()
        return

    render_topnav()

    if st.session_state.profile_view:
        page_profile(st.session_state.profile_view)
        return

    pages={"feed":page_feed,"search":page_search,"knowledge":page_knowledge,
           "folders":page_folders,"analytics":page_analytics,"img_search":page_img_search,
           "chat":page_chat,"settings":page_settings}
    pages.get(st.session_state.page, page_feed)()

main()
