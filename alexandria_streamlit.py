import subprocess, sys, os, json, hashlib, random, string, base64, re, time
from datetime import datetime, timedelta
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
            json.dump({"users":st.session_state.users,"feed_posts":st.session_state.feed_posts,
                       "folders":st.session_state.folders,"user_prefs":prefs_s,
                       "saved_articles":st.session_state.saved_articles}, f, ensure_ascii=False, indent=2)
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
        if delta.days < 7: return f"{delta.days}d atrás"
        if delta.days < 30: return f"{delta.days//7}sem atrás"
        if delta.days < 365: return f"{delta.days//30}m atrás"
        return f"{delta.days//365}a atrás"
    except: return date_str

# ═══════════════════════════════════════════════════
# CSS — DARK BLUE GLASS SOCIAL NETWORK
# ═══════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600&display=swap');
:root{
  --v:#010409;--deep:#040d1e;--navy:#07132a;--surf:#0a1a35;
  --b900:#0f2040;--b800:#1a3a6b;--b700:#1e4d8c;--b600:#1d5fa8;--b500:#2272c3;
  --b400:#3b8de0;--b300:#60a5f5;--b200:#93c5fd;--b100:#dbeafe;
  --cy:#06b6d4;--cyl:#22d3ee;--cyxl:#67e8f9;
  --t1:#f0f6ff;--t2:#8ba8cc;--t3:#3d5a80;--t4:#1e3050;
  --gb:rgba(7,18,44,.72);--gbs:rgba(10,24,52,.55);
  --gbd:rgba(55,130,215,.15);--gbdl:rgba(90,160,240,.28);--gbdxl:rgba(147,197,253,.42);
  --ok:#10b981;--warn:#f59e0b;--err:#ef4444;--pur:#8b5cf6;
  --r8:8px;--r12:12px;--r18:18px;--r24:24px;--r32:32px;--r40:40px;
}
*,*::before,*::after{box-sizing:border-box;margin:0}
html,body,.stApp{background:var(--v)!important;color:var(--t1)!important;font-family:'DM Sans',sans-serif!important}

/* ── SPACE BG ── */
.stApp::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:
    radial-gradient(ellipse 100% 60% at 10% 5%,rgba(28,90,175,.20) 0%,transparent 55%),
    radial-gradient(ellipse 70% 80% at 90% 95%,rgba(6,182,212,.10) 0%,transparent 50%),
    radial-gradient(ellipse 50% 50% at 50% 30%,rgba(15,32,64,.96) 0%,transparent 70%);
  animation:bgPulse 22s ease-in-out infinite alternate}
@keyframes bgPulse{from{opacity:.7}to{opacity:1}}
.stApp::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:
    radial-gradient(1px 1px at 15% 20%,rgba(147,197,253,.60) 0%,transparent 100%),
    radial-gradient(1.5px 1.5px at 72% 14%,rgba(147,197,253,.50) 0%,transparent 100%),
    radial-gradient(1px 1px at 38% 65%,rgba(96,165,245,.45) 0%,transparent 100%),
    radial-gradient(1px 1px at 91% 44%,rgba(147,197,253,.35) 0%,transparent 100%),
    radial-gradient(1.5px 1.5px at 4% 80%,rgba(96,165,245,.30) 0%,transparent 100%),
    radial-gradient(1px 1px at 56% 88%,rgba(147,197,253,.25) 0%,transparent 100%),
    radial-gradient(1px 1px at 29% 48%,rgba(96,165,245,.20) 0%,transparent 100%),
    radial-gradient(1px 1px at 82% 72%,rgba(147,197,253,.18) 0%,transparent 100%)}

/* ── HIDE SIDEBAR ── */
[data-testid="collapsedControl"],section[data-testid="stSidebar"]{display:none!important}
.block-container{padding-top:0!important;padding-bottom:4rem!important;max-width:1400px!important;position:relative;z-index:1}

/* ── TYPOGRAPHY ── */
h1,h2,h3,h4{font-family:'Syne',sans-serif!important;color:var(--t1)!important;font-weight:700;letter-spacing:-.025em}
h1{font-size:1.7rem!important}h2{font-size:1.25rem!important}h3{font-size:1rem!important}

/* ══ GLASS CARD ══ */
.gc{background:var(--gb);backdrop-filter:blur(28px) saturate(190%);-webkit-backdrop-filter:blur(28px) saturate(190%);
  border:1px solid var(--gbd);border-radius:var(--r24);
  box-shadow:0 8px 36px rgba(0,0,0,.46),0 2px 8px rgba(0,0,0,.28),inset 0 1px 0 rgba(147,197,253,.08);
  position:relative;overflow:hidden;transition:border-color .2s,box-shadow .2s,transform .18s}
.gc::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(96,165,245,.40),transparent);pointer-events:none}
.gc:hover{border-color:var(--gbdl);box-shadow:0 16px 52px rgba(0,0,0,.52),inset 0 1px 0 rgba(147,197,253,.12);transform:translateY(-1px)}

/* ══ SOCIAL POST CARD ══ */
.post-card{background:var(--gb);backdrop-filter:blur(28px) saturate(190%);-webkit-backdrop-filter:blur(28px) saturate(190%);
  border:1px solid var(--gbd);border-radius:var(--r24);
  margin-bottom:.9rem;overflow:hidden;
  box-shadow:0 8px 36px rgba(0,0,0,.44),inset 0 1px 0 rgba(147,197,253,.07);
  animation:slideUp .36s cubic-bezier(.34,1.42,.64,1) both;
  transition:border-color .2s,box-shadow .2s}
.post-card:hover{border-color:var(--gbdl);box-shadow:0 18px 56px rgba(0,0,0,.52),inset 0 1px 0 rgba(147,197,253,.11)}
@keyframes slideUp{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:translateY(0)}}
.post-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(96,165,245,.38),transparent);pointer-events:none}

.post-header{padding:1.1rem 1.3rem .7rem;display:flex;align-items:center;gap:10px;border-bottom:1px solid rgba(55,130,215,.08)}
.post-body{padding:.85rem 1.3rem}
.post-footer{padding:.6rem 1.3rem .85rem;display:flex;align-items:center;gap:4px}

/* ══ STORY CARD ══ */
.story-card{background:linear-gradient(160deg,rgba(20,60,140,.80),rgba(6,182,212,.30));
  border:1.5px solid var(--gbdl);border-radius:var(--r18);padding:1rem .9rem;
  text-align:center;min-width:90px;cursor:pointer;
  transition:all .2s;position:relative;overflow:hidden;flex-shrink:0}
.story-card::before{content:'';position:absolute;inset:0;
  background:linear-gradient(180deg,rgba(147,197,253,.06) 0%,transparent 50%);pointer-events:none}
.story-card:hover{border-color:var(--gbdxl);transform:translateY(-3px);box-shadow:0 10px 30px rgba(34,114,195,.3)}

/* ══ LIQUID GLASS BUTTON ══ */
.stButton>button{
  background:linear-gradient(135deg,rgba(20,70,148,.62),rgba(12,48,110,.52),rgba(6,182,212,.24))!important;
  backdrop-filter:blur(24px) saturate(230%)!important;-webkit-backdrop-filter:blur(24px) saturate(230%)!important;
  border:1px solid rgba(90,158,240,.26)!important;border-radius:var(--r12)!important;
  color:var(--t1)!important;font-family:'DM Sans',sans-serif!important;
  font-weight:500!important;font-size:.83rem!important;letter-spacing:.005em!important;
  padding:.5rem .95rem!important;position:relative!important;overflow:hidden!important;
  transition:all .22s cubic-bezier(.4,0,.2,1)!important;
  box-shadow:0 4px 18px rgba(0,0,0,.38),inset 0 1px 0 rgba(147,197,253,.14),inset 0 -1px 0 rgba(0,0,0,.26)!important}
.stButton>button::after{content:'';position:absolute;top:0;left:0;right:0;height:46%;
  background:linear-gradient(180deg,rgba(147,197,253,.09),transparent);pointer-events:none}
.stButton>button:hover{
  background:linear-gradient(135deg,rgba(34,108,190,.76),rgba(20,70,148,.62),rgba(6,182,212,.34))!important;
  border-color:rgba(147,197,253,.42)!important;
  box-shadow:0 8px 30px rgba(30,100,180,.32),inset 0 1px 0 rgba(147,197,253,.22)!important;
  transform:translateY(-1px)!important}
.stButton>button:active{transform:translateY(0) scale(.97)!important}

/* ══ ACTION BUTTONS (like/comment/share row) ══ */
.action-btn{display:inline-flex;align-items:center;gap:5px;padding:.42rem .85rem;
  border-radius:var(--r12);background:transparent;border:1px solid transparent;
  color:var(--t3);font-size:.80rem;font-weight:500;cursor:pointer;
  transition:all .18s;font-family:'DM Sans',sans-serif}
.action-btn:hover{background:rgba(55,130,215,.10);border-color:rgba(55,130,215,.18);color:var(--t2)}
.action-btn.liked{color:#f43f5e;background:rgba(244,63,94,.08);border-color:rgba(244,63,94,.18)}
.action-btn.saved{color:var(--warn);background:rgba(245,158,11,.08);border-color:rgba(245,158,11,.18)}

/* ══ INPUTS ══ */
.stTextInput input,.stTextArea textarea{
  background:rgba(4,10,22,.78)!important;border:1px solid var(--gbd)!important;
  border-radius:var(--r12)!important;color:var(--t1)!important;
  font-family:'DM Sans',sans-serif!important;font-size:.87rem!important;
  transition:border-color .2s,box-shadow .2s!important}
.stTextInput input:focus,.stTextArea textarea:focus{
  border-color:rgba(90,158,240,.52)!important;
  box-shadow:0 0 0 3px rgba(30,100,180,.14),0 0 24px rgba(30,100,180,.09)!important}
.stTextInput label,.stTextArea label,.stSelectbox label,.stFileUploader label{
  color:var(--t3)!important;font-size:.70rem!important;letter-spacing:.06em!important;text-transform:uppercase!important}

/* ══ AVATAR ══ */
.av{border-radius:50%;background:linear-gradient(135deg,var(--b800),var(--b500));
  display:flex;align-items:center;justify-content:center;
  font-family:'Syne',sans-serif;font-weight:700;color:white;
  border:2px solid rgba(90,158,240,.30);flex-shrink:0;overflow:hidden;
  box-shadow:0 3px 12px rgba(0,0,0,.48)}
.av img{width:100%;height:100%;object-fit:cover;border-radius:50%}

/* ══ AVATAR RING (online indicator) ══ */
.av-ring{position:relative;display:inline-block;flex-shrink:0}
.av-ring .online-dot{position:absolute;bottom:1px;right:1px;width:9px;height:9px;
  border-radius:50%;background:var(--ok);border:2px solid var(--v);z-index:2}

/* ══ TAGS / BADGES ══ */
.tag{display:inline-block;background:rgba(30,90,180,.13);border:1px solid rgba(55,130,215,.22);
  border-radius:20px;padding:2px 10px;font-size:.67rem;color:var(--b300);margin:2px;font-weight:500;
  transition:background .15s,border-color .15s}
.tag:hover{background:rgba(30,90,180,.22);border-color:rgba(90,158,240,.38)}
.badge-on{display:inline-block;background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.28);
  border-radius:20px;padding:2px 10px;font-size:.67rem;font-weight:600;color:#f59e0b}
.badge-pub{display:inline-block;background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.28);
  border-radius:20px;padding:2px 10px;font-size:.67rem;font-weight:600;color:#10b981}
.badge-done{display:inline-block;background:rgba(139,92,246,.12);border:1px solid rgba(139,92,246,.28);
  border-radius:20px;padding:2px 10px;font-size:.67rem;font-weight:600;color:#a78bfa}
.badge-hot{display:inline-block;background:rgba(244,63,94,.12);border:1px solid rgba(244,63,94,.28);
  border-radius:20px;padding:2px 10px;font-size:.67rem;font-weight:600;color:#fb7185}
.badge-rec{display:inline-block;background:rgba(6,182,212,.14);border:1px solid rgba(6,182,212,.28);
  border-radius:20px;padding:2px 10px;font-size:.67rem;font-weight:600;color:var(--cyl)}
.badge-new{display:inline-block;background:rgba(139,92,246,.14);border:1px solid rgba(139,92,246,.28);
  border-radius:20px;padding:2px 10px;font-size:.67rem;font-weight:700;color:#a78bfa;
  animation:newPulse 2s ease infinite}
@keyframes newPulse{0%,100%{opacity:1}50%{opacity:.6}}

/* ══ MBOX ══ */
.mbox{background:var(--gb);backdrop-filter:blur(22px);border:1px solid var(--gbd);
  border-radius:var(--r18);padding:1.1rem;text-align:center;
  box-shadow:0 4px 18px rgba(0,0,0,.30),inset 0 1px 0 rgba(147,197,253,.06)}
.mval{font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;
  background:linear-gradient(135deg,var(--b300),var(--cyl));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.mlbl{font-size:.67rem;color:var(--t3);margin-top:4px;letter-spacing:.06em;text-transform:uppercase}

/* ══ EXPLORE SIDEBAR ══ */
.exp-card{background:var(--gb);backdrop-filter:blur(20px);border:1px solid var(--gbd);
  border-radius:var(--r18);padding:1.1rem;margin-bottom:.8rem;
  box-shadow:0 4px 18px rgba(0,0,0,.28),inset 0 1px 0 rgba(147,197,253,.05)}

/* ══ RESEARCHER MINI CARD ══ */
.res-mini{display:flex;align-items:center;gap:9px;padding:.6rem .7rem;
  border-radius:var(--r12);border:1px solid transparent;
  transition:all .18s;cursor:pointer}
.res-mini:hover{background:rgba(55,130,215,.09);border-color:var(--gbd)}

/* ══ TRENDING TOPIC ══ */
.trend-item{display:flex;align-items:center;justify-content:space-between;
  padding:.55rem .7rem;border-radius:var(--r12);border:1px solid transparent;
  transition:all .18s;cursor:pointer}
.trend-item:hover{background:rgba(55,130,215,.09);border-color:var(--gbd)}

/* ══ COMMENT CARD ══ */
.comment-bubble{background:rgba(7,18,44,.88);border:1px solid var(--gbd);
  border-radius:var(--r12);padding:.7rem 1rem;margin-bottom:.45rem}

/* ══ CHAT BUBBLES ══ */
.bme{background:linear-gradient(135deg,rgba(30,100,180,.50),rgba(6,182,212,.26));
  border:1px solid rgba(90,158,240,.24);border-radius:20px 20px 4px 20px;
  padding:.65rem 1rem;max-width:68%;margin-left:auto;margin-bottom:6px;
  font-size:.84rem;line-height:1.6;box-shadow:0 2px 14px rgba(30,100,180,.24)}
.bthem{background:rgba(7,18,44,.85);border:1px solid var(--gbd);
  border-radius:20px 20px 20px 4px;padding:.65rem 1rem;max-width:68%;margin-bottom:6px;
  font-size:.84rem;line-height:1.6}

/* ══ TABS ══ */
.stTabs [data-baseweb="tab-list"]{background:rgba(4,10,22,.82)!important;
  backdrop-filter:blur(20px)!important;border-radius:var(--r12)!important;
  padding:4px!important;gap:2px!important;border:1px solid var(--gbd)!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--t3)!important;
  border-radius:var(--r8)!important;font-family:'DM Sans',sans-serif!important;font-size:.80rem!important;
  transition:all .15s!important}
.stTabs [aria-selected="true"]{
  background:linear-gradient(135deg,rgba(30,100,180,.38),rgba(6,182,212,.20))!important;
  color:var(--t1)!important;border:1px solid rgba(90,158,240,.28)!important;
  box-shadow:0 2px 8px rgba(30,100,180,.18)!important}
.stTabs [data-baseweb="tab-panel"]{background:transparent!important;padding-top:1rem!important}

/* ══ EXPANDER ══ */
.stExpander{background:var(--gb)!important;backdrop-filter:blur(20px)!important;
  border:1px solid var(--gbd)!important;border-radius:var(--r18)!important}
.stExpander summary{color:var(--t2)!important;font-size:.83rem!important}

/* ══ SELECT / UPLOADER ══ */
.stSelectbox [data-baseweb="select"]{background:rgba(4,10,22,.80)!important;
  border:1px solid var(--gbd)!important;border-radius:var(--r12)!important}
.stFileUploader section{background:rgba(4,10,22,.60)!important;
  border:1.5px dashed rgba(55,130,215,.28)!important;border-radius:var(--r18)!important}

/* ══ MISC ══ */
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--b900);border-radius:3px}
hr{border:none;border-top:1px solid var(--gbd)!important;margin:1rem 0}
label{color:var(--t2)!important}
.stCheckbox label,.stRadio label{color:var(--t1)!important}
.stProgress>div>div{background:linear-gradient(90deg,var(--b500),var(--cy))!important;border-radius:4px!important}
.stAlert{background:var(--gb)!important;border:1px solid var(--gbd)!important;border-radius:var(--r18)!important}
input[type="number"]{background:rgba(4,10,22,.78)!important;border:1px solid var(--gbd)!important;
  border-radius:var(--r12)!important;color:var(--t1)!important}

/* ══ PROFILE HERO ══ */
.prof-hero{background:var(--gb);backdrop-filter:blur(28px);border:1px solid var(--gbd);
  border-radius:var(--r32);padding:2rem;display:flex;gap:1.5rem;align-items:flex-start;
  margin-bottom:1.2rem;box-shadow:0 10px 38px rgba(0,0,0,.46),inset 0 1px 0 rgba(147,197,253,.08);
  position:relative;overflow:hidden}
.prof-hero::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(90,158,240,.48),transparent)}
.prof-hero::after{content:'';position:absolute;top:0;left:0;right:0;height:140px;
  background:linear-gradient(160deg,rgba(30,100,180,.10),rgba(6,182,212,.05),transparent);
  pointer-events:none}

.prof-photo{width:88px;height:88px;border-radius:50%;background:linear-gradient(135deg,var(--b900),var(--b600));
  border:2.5px solid rgba(90,158,240,.35);flex-shrink:0;overflow:hidden;
  display:flex;align-items:center;justify-content:center;
  font-size:1.9rem;font-weight:700;color:white;box-shadow:0 4px 22px rgba(30,100,180,.38);z-index:1}
.prof-photo img{width:100%;height:100%;object-fit:cover;border-radius:50%}

/* ══ SEARCH CARD ══ */
.scard{background:var(--gb);backdrop-filter:blur(20px);border:1px solid var(--gbd);
  border-radius:var(--r18);padding:1.1rem 1.3rem;margin-bottom:.7rem;
  transition:border-color .2s,transform .18s;position:relative;overflow:hidden}
.scard:hover{border-color:var(--gbdl);transform:translateY(-1px)}
.scard::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(90,158,240,.18),transparent)}

/* ══ ABOX / PBOX ══ */
.abox{background:rgba(8,20,50,.78);backdrop-filter:blur(18px);border:1px solid var(--gbdl);
  border-radius:var(--r18);padding:1.15rem;margin-bottom:.9rem}
.pbox{background:rgba(6,182,212,.05);border:1px solid rgba(6,182,212,.22);
  border-radius:var(--r18);padding:1rem;margin-bottom:.8rem}

/* ══ PROGRESS BAR ══ */
.prog-wrap{height:5px;background:var(--gbd);border-radius:4px;overflow:hidden;margin:.2rem 0 .5rem}
.prog-fill{height:100%;border-radius:4px;transition:width .7s ease}

/* ══ TOP NAV ══ */
.toprow{position:relative;margin-top:-56px;height:56px;z-index:998}
.toprow .stButton>button{
  background:transparent!important;border:none!important;color:transparent!important;
  font-size:0!important;box-shadow:none!important;border-radius:var(--r8)!important;
  width:100%!important;height:56px!important;padding:0!important;
  backdrop-filter:none!important;-webkit-backdrop-filter:none!important}
.toprow .stButton>button:hover{background:rgba(55,130,215,.10)!important;transform:none!important;box-shadow:none!important}

/* ══ PAGE ANIM ══ */
.pw{animation:fadeIn .28s ease both}
@keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}

/* ══ PULSING DOT ══ */
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.6;transform:scale(.82)}}
.don{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--ok);animation:pulse 2s infinite;margin-right:5px}
.doff{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--t3);margin-right:5px}

/* ══ NOTIFY BADGE ══ */
.notif-dot{position:absolute;top:3px;right:3px;width:7px;height:7px;border-radius:50%;
  background:var(--err);border:1.5px solid var(--v)}

/* ══ NEW POST COMPOSE ══ */
.compose-card{background:var(--gb);backdrop-filter:blur(28px);border:1px solid var(--gbdl);
  border-radius:var(--r24);padding:1.15rem 1.3rem;margin-bottom:1rem;
  box-shadow:0 6px 28px rgba(0,0,0,.38),inset 0 1px 0 rgba(147,197,253,.09)}
.compose-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(96,165,245,.45),transparent)}

/* ══ DIVIDER WITH TEXT ══ */
.div-txt{display:flex;align-items:center;gap:.8rem;margin:.9rem 0;
  font-size:.68rem;color:var(--t3);letter-spacing:.06em;text-transform:uppercase}
.div-txt::before,.div-txt::after{content:'';flex:1;height:1px;background:var(--gbd)}

/* ══ IMAGE ANALYSIS ══ */
.img-result-card{background:rgba(6,182,212,.06);border:1px solid rgba(6,182,212,.20);
  border-radius:var(--r18);padding:1rem;margin-bottom:.7rem;
  transition:border-color .18s}
.img-result-card:hover{border-color:rgba(6,182,212,.38)}

/* ══ GLOW PULSE ══ */
@keyframes glowPulse{0%,100%{box-shadow:0 0 0 0 rgba(6,182,212,.0)}50%{box-shadow:0 0 22px 4px rgba(6,182,212,.18)}}

/* ══ STAGGER ANIM ══ */
.s1{animation-delay:.05s}.s2{animation-delay:.10s}.s3{animation-delay:.15s}
.s4{animation-delay:.20s}.s5{animation-delay:.25s}

/* ══ LIKE HEART ANIM ══ */
@keyframes heartPop{0%{transform:scale(1)}40%{transform:scale(1.3)}70%{transform:scale(.95)}100%{transform:scale(1)}}
.heart-pop{animation:heartPop .35s ease both}

/* ══ DIVIDER NAV ══ */
div[data-testid="stHorizontalBlock"]{gap:2px!important}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════
def avh(initials, sz=40, photo=None):
    fs = max(sz//3, 9)
    if photo:
        return f'<div class="av" style="width:{sz}px;height:{sz}px;"><img src="{photo}"/></div>'
    return f'<div class="av" style="width:{sz}px;height:{sz}px;font-size:{fs}px;">{initials}</div>'

def avh_ring(initials, sz=40, photo=None, online=False):
    av = avh(initials, sz, photo)
    dot = f'<div class="online-dot"></div>' if online else ''
    return f'<div class="av-ring">{av}{dot}</div>'

def tags_html(tags):
    return ' '.join(f'<span class="tag">{t}</span>' for t in (tags or []))

def badge(s):
    cls = {"Publicado":"badge-pub","Concluído":"badge-done"}.get(s,"badge-on")
    return f'<span class="{cls}">{s}</span>'

def prog_bar(pct, color="#2272c3"):
    return f'<div class="prog-wrap"><div class="prog-fill" style="width:{pct}%;background:{color};"></div></div>'

def guser():
    if not isinstance(st.session_state.get("users"), dict): return {}
    return st.session_state.users.get(st.session_state.current_user, {})

def get_photo(email):
    u = st.session_state.get("users", {})
    if not isinstance(u, dict): return None
    return u.get(email, {}).get("photo_b64")

def fmt_num(n):
    if n >= 1000: return f"{n/1000:.1f}k"
    return str(n)

# ═══════════════════════════════════════════════════
# ADVANCED IMAGE ANALYSIS
# ═══════════════════════════════════════════════════
def analyze_image_advanced(uploaded_file):
    try:
        uploaded_file.seek(0)
        img = PILImage.open(uploaded_file).convert("RGB")
        orig = img.size
        small = img.resize((512, 512))
        arr = np.array(small, dtype=np.float32)
        r, g, b_ch = arr[:,:,0], arr[:,:,1], arr[:,:,2]
        mr, mg, mb = float(r.mean()), float(g.mean()), float(b_ch.mean())
        gray = arr.mean(axis=2)
        brightness = (mr + mg + mb) / 3

        # ── SOBEL EDGE DETECTION ──
        gx = np.pad(np.diff(gray, axis=1), ((0,0),(0,1)), mode='edge')
        gy = np.pad(np.diff(gray, axis=0), ((0,1),(0,0)), mode='edge')
        edge_map = np.sqrt(gx**2 + gy**2)
        edge_intensity = float(edge_map.mean())
        edge_max = float(edge_map.max())
        h_strength = float(np.abs(gy).mean())
        v_strength = float(np.abs(gx).mean())

        # Line direction with diagonals
        diag1 = float(np.abs(gx + gy).mean())
        diag2 = float(np.abs(gx - gy).mean())
        strengths = {"Horizontal": h_strength, "Vertical": v_strength, "Diagonal ↗": diag1, "Diagonal ↘": diag2}
        line_dir = max(strengths, key=strengths.get)

        # ── SYMMETRY ANALYSIS ──
        hh, ww = gray.shape[0]//2, gray.shape[1]//2
        q = [gray[:hh,:ww].var(), gray[:hh,ww:].var(), gray[hh:,:ww].var(), gray[hh:,ww:].var()]
        sym = 1.0 - (max(q)-min(q)) / (max(q)+1e-5)

        # Bilateral symmetry (left-right)
        left = gray[:, :gray.shape[1]//2]
        right = np.fliplr(gray[:, gray.shape[1]//2:])
        lr_sym = 1.0 - float(np.abs(left - right).mean()) / (gray.mean() + 1e-5)

        # ── RADIAL/CIRCULAR ANALYSIS ──
        cx, cy = gray.shape[1]//2, gray.shape[0]//2
        y_i, x_i = np.mgrid[0:gray.shape[0], 0:gray.shape[1]]
        dist = np.sqrt((x_i-cx)**2 + (y_i-cy)**2)
        rb = np.histogram(dist.ravel(), bins=24, weights=gray.ravel())[0]
        radial_var = float(np.std(rb)/(np.mean(rb)+1e-5))
        has_circular = radial_var < 0.32 and sym > 0.58

        # ── FFT GRID/PATTERN DETECTION ──
        fft_s = np.fft.fftshift(np.abs(np.fft.fft2(gray)))
        hf, wf = fft_s.shape
        cm = np.zeros_like(fft_s, dtype=bool)
        cm[hf//2-22:hf//2+22, wf//2-22:wf//2+22] = True
        outside = fft_s[~cm]
        has_grid = float(np.percentile(outside, 99)) > float(np.mean(outside)) * 14

        # ── FREQUENCY ANALYSIS (detail level) ──
        fft_mag = np.abs(np.fft.fft2(gray))
        low_freq = float(np.mean(fft_mag[:8, :8]))
        high_freq = float(np.mean(fft_mag[50:, 50:]))
        freq_ratio = high_freq / (low_freq + 1e-5)
        is_high_freq = freq_ratio > 0.12

        # ── TEXTURE / ENTROPY ──
        hist = np.histogram(gray, bins=64, range=(0,255))[0]
        hn = hist/hist.sum(); hn = hn[hn>0]
        entropy = float(-np.sum(hn*np.log2(hn)))
        contrast = float(gray.std())

        # Local variance (texture roughness)
        from numpy.lib.stride_tricks import sliding_window_view
        try:
            win = sliding_window_view(gray, (8,8))[::4, ::4]
            local_vars = win.var(axis=(-2,-1))
            texture_roughness = float(local_vars.mean())
        except:
            texture_roughness = contrast

        # ── COLOR ANALYSIS ──
        flat = arr.reshape(-1, 3)
        rounded = (flat//32*32).astype(int)
        uniq, counts = np.unique(rounded, axis=0, return_counts=True)
        top_i = np.argsort(-counts)[:8]
        palette = [tuple(int(x) for x in uniq[i]) for i in top_i]
        palette_counts = [int(counts[i]) for i in top_i]

        # Color diversity
        color_diversity = float(len(uniq)) / 512.0

        warm = mr > mb + 15
        cool = mb > mr + 15
        neutral = not warm and not cool
        temp_str = "Quente 🔴" if warm else ("Fria 🔵" if cool else "Neutra ⚪")

        # Dominant channel
        dom_ch = "Vermelho" if mr == max(mr,mg,mb) else ("Verde" if mg == max(mr,mg,mb) else "Azul")

        # Saturation
        max_rgb = np.maximum.reduce([r,g,b_ch])
        min_rgb = np.minimum.reduce([r,g,b_ch])
        saturation = float((max_rgb - min_rgb).mean()) / (max_rgb.mean() + 1e-5)

        # ── BIOLOGICAL DETECTION ──
        skin = (r>95)&(g>40)&(b_ch>20)&(r>g)&(r>b_ch)&((r-g)>15)&((r-b_ch)>15)
        skin_pct = float(skin.mean())

        # Blood detection (high red, low green/blue)
        blood = (r>120)&(g<80)&(b_ch<80)
        blood_pct = float(blood.mean())

        # ── SHAPES ──
        shapes = []
        if has_circular: shapes.append("Formas Circulares")
        if has_grid: shapes.append("Grade / Padrão Periódico")
        if sym > 0.78: shapes.append("Alta Simetria")
        if lr_sym > 0.75: shapes.append("Simetria Bilateral")
        if edge_intensity > 32: shapes.append("Contornos Nítidos")
        if edge_intensity < 8: shapes.append("Bordas Suaves")
        if is_high_freq: shapes.append("Textura Fina/Granular")
        if not shapes: shapes.append("Formas Irregulares")

        # ── CLASSIFICATION ──
        cat = "Imagem Científica Geral"
        desc = ""
        kw = "scientific image analysis"
        material = "Desconhecido"
        obj_type = "Estrutura Genérica"
        subcategory = ""

        if skin_pct > 0.15 and blood_pct > 0.05 and mr > 140:
            cat = "Coloração H&E — Histopatologia"
            desc = f"Tecido corado com Hematoxilina & Eosina. Área orgânica: {skin_pct*100:.0f}%, área de hematoxilina (roxo): estimado por padrão de cor."
            kw = "hematoxylin eosin HE staining histopathology biopsy tissue cancer pathology"
            material = "Tecido Biológico Corado"
            obj_type = "Amostra Histopatológica"
            subcategory = "Possível diagnóstico de biópsias ou tecidos neoplásicos"
        elif skin_pct > 0.20:
            cat = "Tecido Biológico / Histologia Óptica"
            desc = f"Predominância de tonalidade orgânica ({skin_pct*100:.0f}% da área). Typical de microscopia óptica de células ou organismos."
            kw = "histology optical microscopy tissue cell biology organism"
            material = "Tecido Biológico"
            obj_type = "Células, Tecido Vivo"
            subcategory = f"Simetria: {sym:.2f} | Entropia: {entropy:.2f}"
        elif has_grid and edge_intensity > 18:
            cat = "Cristalografia / Padrão de Difração"
            desc = f"Padrão periódico detectado (FFT). Intensidade de borda: {edge_intensity:.1f}. Indicativo de difração de raios-X, LEED ou microscopia eletrônica de transmissão (TEM)."
            kw = "X-ray diffraction crystallography TEM LEED crystal material science lattice"
            material = "Material Cristalino"
            obj_type = "Rede Cristalina, Estrutura Atômica"
            subcategory = "Análise FFT confirma periodicidade"
        elif mg > 165 and mr < 125 and mb < 145:
            cat = "Fluorescência Verde — GFP / FITC"
            desc = f"Canal verde dominante (G={mg:.0f}, R={mr:.0f}). Marcador GFP, FITC ou fluorescência de organelas verdes (cloroplastos, mitocôndrias)."
            kw = "GFP green fluorescent protein FITC fluorescence confocal microscopy cell biology"
            material = "Proteínas Fluorescentes / Organelas"
            obj_type = "Células Vivas Marcadas"
            subcategory = "Possível microscopia confocal ou widefield"
        elif mb > 165 and mr < 110:
            cat = "Fluorescência Azul — DAPI / Hoechst"
            desc = f"Canal azul dominante (B={mb:.0f}). Marcação nuclear com DAPI ou Hoechst. Visualização de DNA/cromatina."
            kw = "DAPI Hoechst nuclear staining DNA chromatin fluorescence microscopy cell division"
            material = "DNA / Cromatina"
            obj_type = "Núcleos Celulares"
            subcategory = "Útil para contagem celular e análise de ciclo celular"
        elif mr > 185 and mg < 100 and mb < 120:
            cat = "Imuno-histoquímica (IHC) / Vermelho"
            desc = f"Canal vermelho muito dominante (R={mr:.0f}). Marcador DAB ou imuno-histoquímica convencional."
            kw = "immunohistochemistry IHC DAB antibody marker pathology staining"
            material = "Antígenos Teciduais"
            obj_type = "Expressão Proteica em Tecido"
            subcategory = "Análise semi-quantitativa por DAB possível"
        elif has_circular and edge_intensity > 24 and entropy > 4.5:
            cat = "Microscopia Celular / Organelas"
            desc = f"Estruturas circulares com bordas definidas (I={edge_intensity:.1f}). Células, organelas, vesículas ou microorganismos."
            kw = "cell organelle vesicle bacteria microscopy phase contrast fluorescence"
            material = "Componentes Celulares"
            obj_type = "Células, Organelas, Bactérias"
            subcategory = f"Simetria radial: {radial_var:.3f} | Tamanho: {orig[0]}×{orig[1]}"
        elif entropy > 6.2 and edge_intensity < 18 and color_diversity > 0.4:
            cat = "Imagem Multispectral / Sensoriamento Remoto"
            desc = f"Entropia muito alta ({entropy:.2f} bits) com distribuição de cor diversa ({color_diversity*100:.0f}% de variação). Característico de imagens de satélite ou composição multiespectral."
            kw = "satellite remote sensing multispectral hyperspectral Landsat Sentinel geospatial"
            material = "Dados Geoespaciais"
            obj_type = "Paisagem, Composição Espectral"
            subcategory = "Possível análise de vegetação (NDVI) ou cobertura de solo"
        elif edge_intensity > 40 and entropy < 5.0 and not has_grid:
            cat = "Gráfico / Diagrama / Esquema Técnico"
            desc = f"Bordas muito nítidas (I={edge_intensity:.1f}) com complexidade moderada. Característico de gráficos de dados, diagramas ou figuras de artigos científicos."
            kw = "scientific visualization chart diagram graph data figure publication technical"
            material = "Dados Abstratos"
            obj_type = "Gráfico, Fluxograma, Diagrama"
            subcategory = "Análise de estrutura: pode conter eixos, curvas, barras"
        elif sym > 0.82 and not has_grid and edge_intensity < 28:
            cat = "Estrutura Molecular / Simétrica"
            desc = f"Alta simetria global ({sym:.3f}) com simetria bilateral ({lr_sym:.3f}). Sugere molécula, proteína, vírus ou padrão geométrico científico."
            kw = "molecular structure protein crystal virus symmetry chemistry biochemistry"
            material = "Moléculas, Proteínas"
            obj_type = "Estrutura Molecular / Vírus"
            subcategory = "Possível renderização 3D ou cristalografia de proteína"
        else:
            cat = "Imagem Científica — Perfil Misto"
            desc = f"Temperatura de cor {temp_str}. Brilho médio {brightness:.0f}/255. Complexidade de textura {entropy:.2f} bits. Nenhum padrão dominante altamente específico detectado."
            kw = "scientific image analysis research biology chemistry physics"
            material = "Variado"
            obj_type = "Imagem Científica"
            subcategory = f"Canais: R={mr:.0f} G={mg:.0f} B={mb:.0f} | Saturação: {saturation*100:.0f}%"

        conf = min(96, 48 + edge_intensity/2 + entropy*2.8 + sym*5 + (8 if skin_pct>0.1 else 0) + (6 if has_grid else 0) + (4 if has_circular else 0))

        return {
            "category": cat, "description": desc, "subcategory": subcategory,
            "kw": kw, "material": material, "object_type": obj_type,
            "confidence": round(conf, 1),
            "lines": {"direction": line_dir, "intensity": round(edge_intensity, 2),
                      "max": round(edge_max, 1), "h": round(h_strength, 2), "v": round(v_strength, 2),
                      "d1": round(diag1, 2), "d2": round(diag2, 2),
                      "strengths": {k: round(v, 2) for k,v in strengths.items()}},
            "shapes": shapes,
            "symmetry": round(sym, 3), "lr_symmetry": round(lr_sym, 3),
            "circular": has_circular, "grid": has_grid,
            "radial_var": round(radial_var, 3),
            "color": {"r": round(mr,1), "g": round(mg,1), "b": round(mb,1),
                      "warm": warm, "cool": cool, "temp": temp_str,
                      "dominant": dom_ch, "saturation": round(saturation*100, 1),
                      "diversity": round(color_diversity*100, 1)},
            "texture": {"entropy": round(entropy, 3), "contrast": round(contrast, 2),
                        "roughness": round(texture_roughness, 1),
                        "complexity": "Alta" if entropy>5.5 else ("Média" if entropy>4 else "Baixa"),
                        "freq_ratio": round(freq_ratio, 4)},
            "palette": palette, "palette_counts": palette_counts,
            "size": orig, "skin_pct": round(skin_pct*100, 1),
            "blood_pct": round(blood_pct*100, 1)
        }
    except Exception as e:
        st.error(f"Erro ao analisar: {e}")
        return None

# ═══════════════════════════════════════════════════
# FOLDER ANALYSIS
# ═══════════════════════════════════════════════════
KMAP = {
    "genomica":["Genômica","DNA"],"dna":["DNA","Genômica"],"rna":["RNA","Genômica"],
    "crispr":["CRISPR","Edição Gênica"],"proteina":["Proteômica"],"celula":["Biologia Celular"],
    "neurociencia":["Neurociência"],"cerebro":["Neurociência","Cognição"],"sono":["Sono","Neurociência"],
    "memoria":["Memória","Cognição"],"ia":["IA","Machine Learning"],"ml":["Machine Learning"],
    "deep":["Deep Learning","Redes Neurais"],"quantum":["Computação Quântica"],
    "fisica":["Física"],"quimica":["Química"],"molecula":["Química","Bioquímica"],
    "astronomia":["Astronomia"],"estrela":["Astrofísica"],"cosmo":["Cosmologia"],
    "psicologia":["Psicologia"],"comportamento":["Psicologia"],"biologia":["Biologia"],
    "medicina":["Medicina"],"cancer":["Oncologia"],"engenharia":["Engenharia"],
    "robotica":["Robótica"],"dados":["Ciência de Dados"],"estatistica":["Estatística"],
    "tese":["Tese/Dissertação"],"relatorio":["Relatório"],"analise":["Análise"],
    "protocolo":["Metodologia"],"resultado":["Resultados"],"metodologia":["Metodologia"],
    "ecologia":["Ecologia"],"clima":["Clima"],"ambiental":["Meio Ambiente"],
}
EMAP = {"pdf":"PDF","docx":"Word","doc":"Word","xlsx":"Planilha","csv":"Dados",
        "txt":"Texto","png":"Imagem","jpg":"Imagem","jpeg":"Imagem","tiff":"Imagem Científica",
        "py":"Código Python","r":"Código R","ipynb":"Notebook Jupyter","pptx":"Apresentação","md":"Markdown"}

def analyze_folder(folder_name):
    fd = st.session_state.folders.get(folder_name, {})
    files = fd.get("files",[]) if isinstance(fd,dict) else fd
    if not files: return None
    all_tags, file_analyses = set(), []
    for fname in files:
        fl = fname.lower().replace("_"," ").replace("-"," ")
        ftags = set()
        for kw,ktags in KMAP.items():
            if kw in fl: ftags.update(ktags)
        ext = fname.split(".")[-1].lower() if "." in fname else ""
        ftype = EMAP.get(ext,"Arquivo")
        if not ftags: ftags.add("Pesquisa Geral")
        all_tags.update(ftags)
        prog = random.randint(35, 98)
        file_analyses.append({"file":fname,"type":ftype,"tags":list(ftags),"progress":prog})
    areas = list(all_tags)[:6]
    return {"tags":list(all_tags)[:12],"summary":f"{len(files)} doc(s) · Áreas: {', '.join(areas)}",
            "file_analyses":file_analyses,"total_files":len(files)}

# ═══════════════════════════════════════════════════
# INTERNET SEARCH
# ═══════════════════════════════════════════════════
def search_ss(query, limit=8):
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
                results.append({"title":p.get("title","Sem título"),"authors":authors or "—",
                    "year":p.get("year","?"),"source":p.get("venue","") or "Semantic Scholar",
                    "doi":doi or arxiv or "—","abstract":(p.get("abstract","") or "")[:280],
                    "url":link,"citations":p.get("citationCount",0),"origin":"semantic"})
    except: pass
    return results

def search_cr(query, limit=5):
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
                doi=p.get("DOI","")
                abstract=re.sub(r'<[^>]+>','',p.get("abstract","") or "")[:280]
                results.append({"title":title,"authors":authors or "—","year":year or "?",
                    "source":(p.get("container-title") or ["CrossRef"])[0],"doi":doi,
                    "abstract":abstract,"url":f"https://doi.org/{doi}" if doi else "",
                    "citations":p.get("is-referenced-by-count",0),"origin":"crossref"})
    except: pass
    return results

# ═══════════════════════════════════════════════════
# RECOMMENDATION ENGINE
# ═══════════════════════════════════════════════════
def record(tags, w=1.0):
    email = st.session_state.get("current_user")
    if not email or not tags: return
    prefs = st.session_state.user_prefs.setdefault(email, defaultdict(float))
    for t in tags: prefs[t.lower()] += w

def get_recs(email, n=3):
    prefs = st.session_state.user_prefs.get(email, {})
    if not prefs: return []
    def score(p): return sum(prefs.get(t.lower(),0) for t in p.get("tags",[])+p.get("connections",[]))
    scored = [(score(p),p) for p in st.session_state.feed_posts if email not in p.get("liked_by",[])]
    return [p for s,p in sorted(scored, key=lambda x:-x[0]) if s>0][:n]

def area_to_tags(area):
    a = (area or "").lower()
    M = {"ia":["machine learning","deep learning","LLM"],"inteligência artificial":["machine learning","LLM"],
         "machine learning":["deep learning","otimização","dados"],"neurociência":["sono","memória","plasticidade"],
         "biologia":["célula","genômica","CRISPR"],"física":["quantum","astrofísica","cosmologia"],
         "química":["síntese","catálise","molécula"],"medicina":["clínica","diagnóstico","terapia"],
         "astronomia":["astrofísica","cosmologia","galáxia"],"computação":["algoritmo","criptografia","redes"],
         "matemática":["álgebra","topologia","estatística"],"psicologia":["cognição","comportamento","viés"],
         "ecologia":["biodiversidade","clima","ecossistema"],"genômica":["DNA","CRISPR","gene"],
         "engenharia":["robótica","materiais","sistemas"],"astrofísica":["cosmologia","galáxia","matéria escura"]}
    for k,v in M.items():
        if k in a: return v
    return [w.strip() for w in a.replace(","," ").split() if len(w)>3][:5]

# ═══════════════════════════════════════════════════
# SEED DATA
# ═══════════════════════════════════════════════════
SEED_POSTS = [
    {"id":1,"author":"Carlos Mendez","author_email":"carlos@nebula.ai","avatar":"CM","area":"Neurociência",
     "title":"Efeitos da Privação de Sono na Plasticidade Sináptica",
     "abstract":"Investigamos como 24h de privação de sono afetam espinhas dendríticas em ratos Wistar, com redução de 34% na plasticidade hipocampal. Nossos dados sugerem uma janela crítica nas primeiras 6h de recuperação com implicações importantes para o tratamento de distúrbios do sono.",
     "tags":["neurociência","sono","memória","hipocampo"],"likes":47,
     "comments":[{"user":"Maria Silva","text":"Excelente metodologia! Como foi feito o controle?"},{"user":"João Lima","text":"Quais os critérios de exclusão dos animais?"},{"user":"Ana P.","text":"Fantástico! Tem preprint disponível?"}],
     "status":"Em andamento","date":"2026-02-10","liked_by":[],"saved_by":[],"connections":["sono","memória","hipocampo"],"views":312},
    {"id":2,"author":"Luana Freitas","author_email":"luana@nebula.ai","avatar":"LF","area":"Biomedicina",
     "title":"CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras",
     "abstract":"Desenvolvemos vetor AAV9 modificado para entrega precisa de CRISPR no gene DMD, com eficiência de 78% em modelos murinos mdx. Os resultados mostram restauração parcial da distrofina. Publicação em Cell prevista para Q2 2026.",
     "tags":["CRISPR","gene terapia","músculo","AAV9"],"likes":93,
     "comments":[{"user":"Ana","text":"Próximos passos para trials humanos?"},{"user":"Pedro R.","text":"78% de eficiência é impressionante!"}],
     "status":"Publicado","date":"2026-01-28","liked_by":[],"saved_by":[],"connections":["genômica","distrofia"],"views":891},
    {"id":3,"author":"Rafael Souza","author_email":"rafael@nebula.ai","avatar":"RS","area":"Computação",
     "title":"Redes Neurais Quântico-Clássicas para Otimização Combinatória",
     "abstract":"Arquitetura híbrida variacional combinando qubits supercondutores com camadas densas clássicas para resolver TSP com 40% menos iterações. Demonstramos vantagem quântica em instâncias com n>50 cidades.",
     "tags":["quantum ML","otimização","TSP","computação quântica"],"likes":201,
     "comments":[{"user":"Priya N.","text":"Incrível resultado! Qual hardware quântico?"}],
     "status":"Em andamento","date":"2026-02-15","liked_by":[],"saved_by":[],"connections":["computação quântica","machine learning"],"views":1240},
    {"id":4,"author":"Priya Nair","author_email":"priya@nebula.ai","avatar":"PN","area":"Astrofísica",
     "title":"Detecção de Matéria Escura via Lentes Gravitacionais Fracas em DES Y3",
     "abstract":"Mapeamento de matéria escura com precisão sub-arcminuto usando 100M de galáxias do Dark Energy Survey Y3. Identificamos tensão com ΛCDM em escalas < 1 Mpc que pode indicar nova física.",
     "tags":["astrofísica","matéria escura","cosmologia","DES"],"likes":312,
     "comments":[],
     "status":"Publicado","date":"2026-02-01","liked_by":[],"saved_by":[],"connections":["cosmologia","lentes gravitacionais"],"views":2180},
    {"id":5,"author":"João Lima","author_email":"joao@nebula.ai","avatar":"JL","area":"Psicologia",
     "title":"Viés de Confirmação em Decisões Médicas Assistidas por IA",
     "abstract":"Estudo duplo-cego com 240 médicos revelou que sistemas de IA mal calibrados amplificam vieses cognitivos em 22% dos casos clínicos analisados. Propomos framework de auditoria contínua.",
     "tags":["psicologia","IA","cognição","medicina"],"likes":78,
     "comments":[{"user":"Carlos M.","text":"Muito importante para a prática clínica!"}],
     "status":"Publicado","date":"2026-02-08","liked_by":[],"saved_by":[],"connections":["cognição","IA"],"views":456},
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
    "carlos@nebula.ai":[{"from":"carlos@nebula.ai","text":"Oi! Vi seu comentário na minha pesquisa.","time":"09:14"},{"from":"me","text":"Achei muito interessante a metodologia!","time":"09:16"}],
    "luana@nebula.ai":[{"from":"luana@nebula.ai","text":"Podemos colaborar no próximo semestre?","time":"ontem"}],
    "rafael@nebula.ai":[{"from":"rafael@nebula.ai","text":"Compartilhei o repositório quântico.","time":"08:30"}],
}

# ═══════════════════════════════════════════════════
# SESSION INIT
# ═══════════════════════════════════════════════════
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
    st.session_state.setdefault("user_prefs", {k:defaultdict(float,v) for k,v in disk_prefs.items()})
    st.session_state.setdefault("pending_verify", None)
    st.session_state.setdefault("pending_2fa", None)
    st.session_state.setdefault("feed_posts", disk.get("feed_posts", [dict(p) for p in SEED_POSTS]))
    st.session_state.setdefault("folders", disk.get("folders", {}))
    st.session_state.setdefault("chat_contacts", list(SEED_USERS.keys()))
    st.session_state.setdefault("chat_messages", {k:list(v) for k,v in CHAT_INIT.items()})
    st.session_state.setdefault("active_chat", None)
    st.session_state.setdefault("followed", ["carlos@nebula.ai","luana@nebula.ai"])
    st.session_state.setdefault("notifications", ["Carlos Mendez curtiu sua pesquisa","Nova conexão: IA ↔ Neurociência"])
    st.session_state.setdefault("scholar_cache", {})
    st.session_state.setdefault("saved_articles", disk.get("saved_articles", []))
    st.session_state.setdefault("img_result", None)
    st.session_state.setdefault("search_results", None)
    st.session_state.setdefault("last_sq", "")
    st.session_state.setdefault("stats_data", {"h_index":4,"fator_impacto":3.8,"notes":""})
    st.session_state.setdefault("compose_open", False)

init()

# ═══════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════
def page_login():
    _, col, _ = st.columns([1,1.05,1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-bottom:2.8rem;">
          <div style="font-family:'Syne',sans-serif;font-size:3.4rem;font-weight:800;
            background:linear-gradient(135deg,#93c5fd,#22d3ee,#60a5f5);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
            letter-spacing:-.05em;line-height:1;margin-bottom:.5rem;">🔬 Nebula</div>
          <div style="color:var(--t3);font-size:.68rem;letter-spacing:.22em;text-transform:uppercase;">
            Rede do Conhecimento Científico</div>
        </div>""", unsafe_allow_html=True)
        with st.container():
            tab_in, tab_up = st.tabs(["  Entrar  ","  Criar conta  "])
            with tab_in:
                email = st.text_input("E-mail", placeholder="seu@email.com", key="li_e")
                pw = st.text_input("Senha", placeholder="••••••••", type="password", key="li_p")
                if st.button("Entrar →", use_container_width=True, key="btn_li"):
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
                st.markdown('<div style="text-align:center;color:var(--t3);font-size:.68rem;margin-top:.6rem;">Demo: demo@nebula.ai / demo123</div>', unsafe_allow_html=True)
            with tab_up:
                n_name=st.text_input("Nome completo", key="su_n")
                n_email=st.text_input("E-mail", key="su_e")
                n_area=st.text_input("Área de pesquisa", key="su_a")
                n_pw=st.text_input("Senha", type="password", key="su_p")
                n_pw2=st.text_input("Confirmar senha", type="password", key="su_p2")
                if st.button("Criar conta →", use_container_width=True, key="btn_su"):
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
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"""<div class="gc" style="padding:2rem;text-align:center;">
          <div style="font-size:2.8rem;margin-bottom:1rem;">📧</div>
          <h2 style="margin-bottom:.5rem;">Verifique seu e-mail</h2>
          <p style="color:var(--t2);font-size:.83rem;">Código para <strong>{pv['email']}</strong></p>
          <div style="background:rgba(30,100,180,.10);border:1px solid rgba(55,130,215,.24);
            border-radius:var(--r18);padding:18px;margin:1.2rem 0;">
            <div style="font-size:.63rem;color:var(--t3);letter-spacing:.12em;text-transform:uppercase;margin-bottom:6px;">Código (demo)</div>
            <div style="font-family:'Syne',sans-serif;font-size:2.6rem;font-weight:800;letter-spacing:.3em;color:var(--b300);">{pv['code']}</div>
          </div></div>""", unsafe_allow_html=True)
        typed=st.text_input("Código", max_chars=6, placeholder="000000", key="ev_c")
        if st.button("Verificar →", use_container_width=True, key="btn_ev"):
            if typed.strip()==pv["code"]:
                st.session_state.users[pv["email"]]={"name":pv["name"],"password":pv["pw"],"bio":"","area":pv["area"],"followers":0,"following":0,"verified":True,"2fa_enabled":False,"photo_b64":None}
                save_db(); st.session_state.pending_verify=None
                st.session_state.logged_in=True; st.session_state.current_user=pv["email"]
                record(area_to_tags(pv["area"]),2.0); st.session_state.page="feed"; st.rerun()
            else: st.error("Código inválido.")
        if st.button("← Voltar", key="btn_ev_bk"): st.session_state.page="login"; st.rerun()

def page_2fa():
    p2=st.session_state.pending_2fa
    _,col,_=st.columns([1,1.05,1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"""<div class="gc" style="padding:2rem;text-align:center;">
          <div style="font-size:2.8rem;margin-bottom:1rem;">🔑</div><h2>Verificação 2FA</h2>
          <div style="background:rgba(30,100,180,.10);border:1px solid rgba(55,130,215,.24);
            border-radius:var(--r18);padding:16px;margin:1rem 0;">
            <div style="font-size:.63rem;color:var(--t3);text-transform:uppercase;letter-spacing:.10em;margin-bottom:6px;">Código (demo)</div>
            <div style="font-family:'Syne',sans-serif;font-size:2.6rem;font-weight:800;letter-spacing:.25em;color:var(--b300);">{p2['code']}</div>
          </div></div>""", unsafe_allow_html=True)
        typed=st.text_input("Código", max_chars=6, placeholder="000000", key="fa_c", label_visibility="collapsed")
        if st.button("Verificar →", use_container_width=True, key="btn_fa"):
            if typed.strip()==p2["code"]:
                st.session_state.logged_in=True; st.session_state.current_user=p2["email"]
                st.session_state.pending_2fa=None; st.session_state.page="feed"; st.rerun()
            else: st.error("Código inválido.")
        if st.button("← Voltar", key="btn_fa_bk"): st.session_state.page="login"; st.rerun()

# ═══════════════════════════════════════════════════
# TOP NAV
# ═══════════════════════════════════════════════════
NAV = [("feed","◈","Feed"),("search","⊙","Artigos"),("knowledge","⬡","Conexões"),
       ("folders","▣","Pastas"),("analytics","▤","Análises"),
       ("img_search","⊞","Imagem"),("chat","◻","Chat"),("settings","◎","Perfil")]

def render_topnav():
    u=guser(); name=u.get("name","?"); photo=u.get("photo_b64"); in_=ini(name)
    cur=st.session_state.page; notif=len(st.session_state.notifications)
    spans=""
    for k,sym,lbl in NAV:
        active=cur==k
        if active:
            spans+=f'<span style="font-size:.76rem;color:var(--b300);font-weight:600;padding:.36rem .75rem;border-radius:var(--r8);background:rgba(30,100,180,.26);border:1px solid rgba(90,158,240,.32);display:inline-flex;align-items:center;gap:5px;white-space:nowrap;letter-spacing:.005em;">{sym} {lbl}</span>'
        else:
            spans+=f'<span style="font-size:.76rem;color:var(--t3);padding:.36rem .75rem;border-radius:var(--r8);white-space:nowrap;display:inline-flex;align-items:center;gap:4px;letter-spacing:.005em;transition:color .15s;">{sym} {lbl}</span>'
    av_inner=f"<img src='{photo}' style='width:100%;height:100%;object-fit:cover;border-radius:50%;'/>" if photo else in_
    av_div=f'<div style="width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,var(--b800),var(--b500));display:flex;align-items:center;justify-content:center;font-size:.74rem;font-weight:700;color:white;border:2px solid rgba(90,158,240,.30);overflow:hidden;flex-shrink:0;box-shadow:0 3px 12px rgba(0,0,0,.48);">{av_inner}</div>'
    nb=f'<div style="position:relative;"><div style="font-size:.80rem;color:var(--t3);padding:.3rem .5rem;border-radius:var(--r8);border:1px solid var(--gbd);background:rgba(7,18,44,.55);">🔔</div><div class="notif-dot"></div></div>' if notif else ''
    st.markdown(f"""
    <div style="position:sticky;top:0;z-index:1000;background:rgba(1,4,9,.94);
      backdrop-filter:blur(36px) saturate(210%);-webkit-backdrop-filter:blur(36px) saturate(210%);
      border-bottom:1px solid var(--gbd);padding:0 1.5rem;
      display:flex;align-items:center;justify-content:space-between;height:56px;">
      <div style="font-family:'Syne',sans-serif;font-size:1.28rem;font-weight:800;
        background:linear-gradient(135deg,#93c5fd,#22d3ee);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
        background-clip:text;white-space:nowrap;letter-spacing:-.04em;flex-shrink:0;">🔬 Nebula</div>
      <div style="display:flex;align-items:center;gap:2px;overflow-x:auto;padding:0 .6rem;scrollbar-width:none;">{spans}</div>
      <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">{nb}{av_div}</div>
    </div>""", unsafe_allow_html=True)
    st.markdown('<div class="toprow">', unsafe_allow_html=True)
    cols = st.columns([1.6]+[1]*len(NAV)+[.8])
    for i,(key,sym,lbl) in enumerate(NAV):
        with cols[i+1]:
            if st.button(f"{sym}{lbl}", key=f"tnav_{key}", use_container_width=True):
                st.session_state.profile_view=None; st.session_state.page=key; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# PROFILE PAGE
# ═══════════════════════════════════════════════════
def page_profile(target_email):
    tu = st.session_state.users.get(target_email, {})
    if not tu:
        st.error("Perfil não encontrado.")
        if st.button("← Voltar", key="bk_err"): st.session_state.profile_view=None; st.rerun()
        return
    tname=tu.get("name","?"); tin=ini(tname); tphoto=tu.get("photo_b64")
    email=st.session_state.current_user; is_me=email==target_email
    is_fol=target_email in st.session_state.followed
    user_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==target_email]

    if st.button("← Voltar", key="back_prof"): st.session_state.profile_view=None; st.rerun()
    photo_html=f"<img src='{tphoto}'/>" if tphoto else f'<span style="font-size:2rem;">{tin}</span>'
    total_likes = sum(p["likes"] for p in user_posts)
    total_views = sum(p.get("views",0) for p in user_posts)
    st.markdown(f"""
    <div class="prof-hero">
      <div class="prof-photo">{photo_html}</div>
      <div style="flex:1;z-index:1;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:.25rem;">
          <h1 style="margin:0;">{tname}</h1>
          {"<span style='font-size:.72rem;color:var(--cy);'>✓ Verificado</span>" if tu.get("verified") else ""}
        </div>
        <div style="color:var(--b300);font-size:.84rem;margin-bottom:.5rem;font-weight:500;">@{tname.lower().replace(' ','_')} · {tu.get("area","")}</div>
        <div style="color:var(--t2);font-size:.82rem;line-height:1.65;margin-bottom:.9rem;max-width:560px;">{tu.get("bio","Sem biografia.")}</div>
        <div style="display:flex;gap:2rem;flex-wrap:wrap;">
          <div><span style="font-weight:800;font-family:'Syne',sans-serif;font-size:1.15rem;">{tu.get("followers",0)}</span><span style="color:var(--t3);font-size:.73rem;"> seguidores</span></div>
          <div><span style="font-weight:800;font-family:'Syne',sans-serif;font-size:1.15rem;">{tu.get("following",0)}</span><span style="color:var(--t3);font-size:.73rem;"> seguindo</span></div>
          <div><span style="font-weight:800;font-family:'Syne',sans-serif;font-size:1.15rem;">{len(user_posts)}</span><span style="color:var(--t3);font-size:.73rem;"> pesquisas</span></div>
          <div><span style="font-weight:800;font-family:'Syne',sans-serif;font-size:1.15rem;">{fmt_num(total_likes)}</span><span style="color:var(--t3);font-size:.73rem;"> curtidas</span></div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    if not is_me:
        c1,c2,_ = st.columns([1,1,3])
        with c1:
            if st.button("✓ Seguindo" if is_fol else "➕ Seguir", key=f"pf_fol", use_container_width=True):
                if is_fol: st.session_state.followed.remove(target_email); tu["followers"]=max(0,tu.get("followers",0)-1)
                else: st.session_state.followed.append(target_email); tu["followers"]=tu.get("followers",0)+1
                save_db(); st.rerun()
        with c2:
            if st.button("💬 Mensagem", key=f"pf_chat", use_container_width=True):
                if target_email not in st.session_state.chat_messages: st.session_state.chat_messages[target_email]=[]
                st.session_state.active_chat=target_email; st.session_state.page="chat"; st.rerun()

    st.markdown('<div class="div-txt">Pesquisas</div>', unsafe_allow_html=True)
    if user_posts:
        for p in sorted(user_posts, key=lambda x:x.get("date",""), reverse=True):
            render_post_card(p, ctx="profile", show_author=False)
    else:
        st.markdown('<div class="gc" style="padding:2rem;text-align:center;color:var(--t3);">Nenhuma pesquisa publicada ainda.</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# POST CARD — SOCIAL NETWORK STYLE
# ═══════════════════════════════════════════════════
def render_post_card(post, ctx="feed", show_author=True, compact=False):
    email = st.session_state.current_user
    pid = post["id"]; liked = email in post.get("liked_by",[]); saved = email in post.get("saved_by",[])
    aemail = post.get("author_email",""); aphoto = get_photo(aemail); ain = post.get("avatar","??")
    aname = post.get("author","?"); aarea = post.get("area","")
    dt = time_ago(post.get("date",""))
    views = post.get("views", random.randint(50,500))

    # Post header
    if show_author:
        photo_html = f"<img src='{aphoto}'/>" if aphoto else ""
        av_html = f'<div class="av" style="width:44px;height:44px;font-size:14px;">{photo_html if aphoto else ain}</div>'
        header_html = f"""
        <div class="post-header">
          {av_html}
          <div style="flex:1;min-width:0;">
            <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:.91rem;display:flex;align-items:center;gap:6px;">
              {aname}
              {"<span style='font-size:.62rem;color:var(--cy);'>✓</span>" if st.session_state.users.get(aemail,{}).get("verified") else ""}
            </div>
            <div style="color:var(--t3);font-size:.70rem;margin-top:1px;">{aarea} · {dt}</div>
          </div>
          {badge(post["status"])}
        </div>"""
    else:
        header_html = f'<div style="padding:.6rem 1.3rem .4rem;display:flex;align-items:center;justify-content:space-between;"><span style="color:var(--t3);font-size:.70rem;">{dt}</span>{badge(post["status"])}</div>'

    # Abstract truncation
    abstract = post.get("abstract","")
    if len(abstract) > 220 and compact:
        abstract = abstract[:220] + "…"

    st.markdown(f"""
    <div class="post-card" style="position:relative;">
      {header_html}
      <div class="post-body">
        <div style="font-family:'Syne',sans-serif;font-size:1.04rem;font-weight:700;margin-bottom:.5rem;line-height:1.4;color:var(--t1);">{post["title"]}</div>
        <div style="color:var(--t2);font-size:.83rem;line-height:1.68;margin-bottom:.8rem;">{abstract}</div>
        <div style="display:flex;flex-wrap:wrap;gap:0;">{tags_html(post["tags"])}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # Action bar
    heart = "❤️" if liked else "🤍"
    book = "🔖" if saved else "📌"
    num_comments = len(post.get("comments",[]))

    c_like, c_cmt, c_save, c_share, c_view, c_auth = st.columns([1.2,1.1,.9,.9,1.2,1.2])
    with c_like:
        if st.button(f"{heart} {fmt_num(post['likes'])}", key=f"lk_{ctx}_{pid}", use_container_width=True):
            if liked: post["liked_by"].remove(email); post["likes"]=max(0,post["likes"]-1)
            else: post["liked_by"].append(email); post["likes"]+=1; record(post["tags"],1.5)
            save_db(); st.rerun()
    with c_cmt:
        if st.button(f"💬 {num_comments}", key=f"cmt_{ctx}_{pid}", use_container_width=True):
            k=f"show_cmt_{ctx}_{pid}"; st.session_state[k]=not st.session_state.get(k,False); st.rerun()
    with c_save:
        if st.button(book, key=f"sv_{ctx}_{pid}", use_container_width=True):
            if saved: post["saved_by"].remove(email)
            else: post["saved_by"].append(email)
            save_db(); st.rerun()
    with c_share:
        if st.button("↗", key=f"sh_{ctx}_{pid}", use_container_width=True):
            k=f"show_sh_{ctx}_{pid}"; st.session_state[k]=not st.session_state.get(k,False); st.rerun()
    with c_view:
        st.markdown(f'<div style="text-align:center;color:var(--t3);font-size:.73rem;padding:.5rem 0;">👁 {fmt_num(views)}</div>', unsafe_allow_html=True)
    with c_auth:
        if show_author and aemail:
            if st.button(f"👤 {aname.split()[0]}", key=f"vp_{ctx}_{pid}", use_container_width=True):
                st.session_state.profile_view=aemail; st.rerun()

    # Share panel
    if st.session_state.get(f"show_sh_{ctx}_{pid}", False):
        url = f"https://nebula.ai/post/{pid}"
        st.markdown(f"""<div class="gc" style="padding:1rem 1.3rem;margin-bottom:.5rem;">
          <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.7rem;">Compartilhar pesquisa</div>
          <div style="display:flex;gap:.5rem;flex-wrap:wrap;">
            <a href="https://twitter.com/intent/tweet?text={post['title'][:50]}&url={url}" target="_blank" style="text-decoration:none;">
              <div style="background:rgba(29,161,242,.12);border:1px solid rgba(29,161,242,.24);border-radius:var(--r8);padding:.42rem .75rem;font-size:.73rem;color:#1da1f2;">𝕏 Twitter</div></a>
            <a href="https://linkedin.com/sharing/share-offsite/?url={url}" target="_blank" style="text-decoration:none;">
              <div style="background:rgba(10,102,194,.12);border:1px solid rgba(10,102,194,.24);border-radius:var(--r8);padding:.42rem .75rem;font-size:.73rem;color:#0a66c2;">in LinkedIn</div></a>
            <a href="https://wa.me/?text={post['title'][:50]}+{url}" target="_blank" style="text-decoration:none;">
              <div style="background:rgba(37,211,102,.10);border:1px solid rgba(37,211,102,.22);border-radius:var(--r8);padding:.42rem .75rem;font-size:.73rem;color:#25d366;">📱 WhatsApp</div></a>
          </div>
          <div style="margin-top:.7rem;"><code style="font-size:.72rem;color:var(--t3);background:rgba(0,0,0,.3);padding:3px 8px;border-radius:5px;">{url}</code></div>
        </div>""", unsafe_allow_html=True)

    # Comments panel
    if st.session_state.get(f"show_cmt_{ctx}_{pid}", False):
        comments = post.get("comments", [])
        if comments:
            for ci, c in enumerate(comments):
                c_ini = ini(c["user"])
                c_photo = get_photo(next((e for e,u in st.session_state.users.items() if u.get("name")==c["user"]),""))
                av_c = avh(c_ini, 28, c_photo)
                st.markdown(f"""<div class="comment-bubble">
                  <div style="display:flex;align-items:center;gap:8px;margin-bottom:.3rem;">
                    {av_c}<span style="font-size:.78rem;font-weight:600;color:var(--b300);">{c["user"]}</span>
                  </div>
                  <div style="font-size:.82rem;color:var(--t2);line-height:1.55;padding-left:36px;">{c["text"]}</div>
                </div>""", unsafe_allow_html=True)
        nc = st.text_input("", placeholder="Escreva um comentário…", key=f"ci_{ctx}_{pid}", label_visibility="collapsed")
        if st.button("Comentar", key=f"cs_{ctx}_{pid}"):
            if nc:
                u=guser()
                post["comments"].append({"user":u.get("name","Você"),"text":nc})
                record(post["tags"],.8); save_db(); st.rerun()

# ═══════════════════════════════════════════════════
# FEED PAGE
# ═══════════════════════════════════════════════════
def page_feed():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    email = st.session_state.current_user; u = guser()
    uname = u.get("name","?"); uphoto = u.get("photo_b64"); uin = ini(uname)

    # ── TWO COLUMN LAYOUT ──
    col_main, col_side = st.columns([1.95, 0.95], gap="medium")

    with col_main:
        # ── STORIES ROW ──
        users = st.session_state.users if isinstance(st.session_state.users,dict) else {}
        story_researchers = [(ue,ud) for ue,ud in users.items() if ue!=email][:6]

        story_html = ""
        for ue, ud in story_researchers:
            sname = ud.get("name","?"); sin = ini(sname); sphoto = ud.get("photo_b64")
            is_fol = ue in st.session_state.followed
            border_color = "rgba(34,211,238,.60)" if is_fol else "rgba(55,130,215,.28)"
            photo_inner = f"<img src='{sphoto}' style='width:100%;height:100%;object-fit:cover;border-radius:50%;'/>" if sphoto else f'<span style="font-size:1rem;font-weight:700;font-family:\'Syne\',sans-serif;">{sin}</span>'
            story_html += f"""
            <div class="story-card">
              <div style="width:48px;height:48px;border-radius:50%;background:linear-gradient(135deg,var(--b800),var(--b500));
                display:flex;align-items:center;justify-content:center;margin:0 auto .55rem;
                border:2.5px solid {border_color};overflow:hidden;box-shadow:0 3px 14px rgba(0,0,0,.48);">{photo_inner}</div>
              <div style="font-size:.67rem;font-weight:600;color:var(--t2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:80px;">{sname.split()[0]}</div>
              <div style="font-size:.58rem;color:var(--t3);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{ud.get("area","")[:14]}</div>
              {"<div style='margin-top:5px;width:6px;height:6px;border-radius:50%;background:var(--ok);margin:5px auto 0;box-shadow:0 0 6px var(--ok);'></div>" if is_fol else ""}
            </div>"""

        st.markdown(f"""
        <div style="display:flex;gap:.65rem;overflow-x:auto;padding:.5rem 0 1rem;margin-bottom:.4rem;scrollbar-width:none;">
          <div class="story-card" style="background:linear-gradient(160deg,rgba(30,100,180,.55),rgba(6,182,212,.22));border-style:dashed;">
            <div style="width:48px;height:48px;border-radius:50%;background:rgba(55,130,215,.20);
              display:flex;align-items:center;justify-content:center;margin:0 auto .55rem;
              border:2px dashed rgba(90,158,240,.40);font-size:1.3rem;">+</div>
            <div style="font-size:.67rem;font-weight:600;color:var(--cyl);">Publicar</div>
          </div>
          {story_html}
        </div>""", unsafe_allow_html=True)

        # ── COMPOSE POST ──
        compose_open = st.session_state.get("compose_open", False)
        av_compose = avh(uin, 40, uphoto)
        st.markdown(f"""
        <div class="compose-card" style="position:relative;">
          <div style="display:flex;align-items:center;gap:12px;">
            {av_compose}
            <div style="flex:1;background:rgba(4,10,22,.55);border:1px solid var(--gbd);
              border-radius:var(--r40);padding:.6rem 1.1rem;cursor:text;color:var(--t3);font-size:.85rem;">
              No que você está pesquisando hoje, {uname.split()[0]}?
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

        if st.button("✏️ Nova pesquisa", key="toggle_compose", use_container_width=False):
            st.session_state.compose_open = not compose_open; st.rerun()

        if st.session_state.get("compose_open", False):
            with st.container():
                st.markdown('<div class="compose-card" style="position:relative;margin-top:.4rem;">', unsafe_allow_html=True)
                np_t = st.text_input("Título da pesquisa*", key="np_t", placeholder="Ex: Efeitos da meditação na neuroplasticidade…")
                np_ab = st.text_area("Resumo / Abstract*", key="np_ab", height=110, placeholder="Descreva sua pesquisa, metodologia e principais resultados…")
                cc1, cc2 = st.columns(2)
                with cc1: np_tg = st.text_input("Tags (vírgula)", key="np_tg", placeholder="neurociência, fMRI, cognição")
                with cc2: np_st = st.selectbox("Status", ["Em andamento","Publicado","Concluído"], key="np_st")
                if st.button("🚀 Publicar pesquisa", key="btn_pub", use_container_width=True):
                    if np_t and np_ab:
                        tags = [t.strip() for t in np_tg.split(",") if t.strip()]
                        new_post = {"id":len(st.session_state.feed_posts)+100+random.randint(0,99),
                            "author":uname,"author_email":email,"avatar":uin,"area":u.get("area",""),
                            "title":np_t,"abstract":np_ab,"tags":tags,"likes":0,"comments":[],
                            "status":np_st,"date":datetime.now().strftime("%Y-%m-%d"),"liked_by":[],"saved_by":[],"connections":tags[:3],"views":1}
                        st.session_state.feed_posts.insert(0, new_post)
                        record(tags, 2.0); save_db()
                        st.session_state.compose_open=False
                        st.success("✓ Pesquisa publicada!"); st.rerun()
                    else: st.warning("Título e resumo são obrigatórios.")
                st.markdown('</div>', unsafe_allow_html=True)

        # ── FEED FILTER ──
        filter_opts = ["🌐 Todos","👥 Seguidos","🔖 Salvos","🔥 Populares"]
        ff = st.radio("", filter_opts, horizontal=True, key="ff", label_visibility="collapsed")

        # ── RECOMMENDATIONS ──
        recs = get_recs(email, 2)
        if recs and "Seguidos" not in ff and "Salvos" not in ff:
            st.markdown(f'<div class="div-txt"><span class="badge-new">✦ RECOMENDADO</span></div>', unsafe_allow_html=True)
            for p in recs:
                render_post_card(p, ctx="rec", compact=True)
            st.markdown('<div class="div-txt">Mais pesquisas</div>', unsafe_allow_html=True)

        # ── MAIN FEED ──
        posts = list(st.session_state.feed_posts)
        if "Seguidos" in ff:
            posts = [p for p in posts if p.get("author_email") in st.session_state.followed]
        elif "Salvos" in ff:
            posts = [p for p in posts if email in p.get("saved_by",[])]
        elif "Populares" in ff:
            posts = sorted(posts, key=lambda p: p["likes"], reverse=True)
        else:
            posts = sorted(posts, key=lambda p: p.get("date",""), reverse=True)

        if not posts:
            st.markdown('<div class="gc" style="padding:3rem;text-align:center;"><div style="font-size:2.5rem;margin-bottom:1rem;">🔬</div><div style="color:var(--t2);">Nenhuma pesquisa aqui ainda.</div></div>', unsafe_allow_html=True)
        else:
            for p in posts:
                render_post_card(p, ctx="feed")

    # ── RIGHT SIDEBAR ──
    with col_side:
        # Search researchers
        sq = st.text_input("", placeholder="🔍 Buscar pesquisadores…", key="ppl_s", label_visibility="collapsed")

        # Who to follow
        st.markdown(f"""<div class="exp-card">
          <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.9rem;display:flex;align-items:center;justify-content:space-between;">
            <span>Quem seguir</span>
            <span style="font-size:.67rem;color:var(--t3);">Sugestões</span>
          </div>""", unsafe_allow_html=True)

        shown = 0
        for ue, ud in list(users.items()):
            if ue==email or shown>=5: continue
            uname_r = ud.get("name","?")
            if sq and sq.lower() not in uname_r.lower() and sq.lower() not in ud.get("area","").lower(): continue
            shown += 1
            is_fol = ue in st.session_state.followed
            uphoto_r = ud.get("photo_b64"); uin_r = ini(uname_r)
            online = random.random() > 0.45

            r_av = avh_ring(uin_r, 36, uphoto_r, online)
            st.markdown(f"""<div class="res-mini">
              {r_av}
              <div style="flex:1;min-width:0;">
                <div style="font-size:.81rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{uname_r}</div>
                <div style="font-size:.67rem;color:var(--t3);">{ud.get("area","")[:18]}</div>
              </div>
            </div>""", unsafe_allow_html=True)

            cb_fol, cb_view = st.columns([1,1])
            with cb_fol:
                lbl = "✓" if is_fol else "➕"
                if st.button(lbl, key=f"sf_{ue}", use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"]=max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                    save_db(); st.rerun()
            with cb_view:
                if st.button("👤", key=f"sv_r_{ue}", use_container_width=True):
                    st.session_state.profile_view=ue; st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        # Trending topics
        st.markdown(f"""<div class="exp-card">
          <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.9rem;">🔥 Trending</div>""", unsafe_allow_html=True)

        trending = [("Quantum ML","34 pesquisas"),("CRISPR 2026","28 pesquisas"),
                    ("Neuroplasticidade","22 pesquisas"),("LLMs Científicos","19 pesquisas"),("Matéria Escura","15 pesquisas")]
        for i,(topic,cnt) in enumerate(trending):
            st.markdown(f"""<div class="trend-item">
              <div>
                <div style="font-size:.69rem;color:var(--t3);margin-bottom:1px;">#{i+1} Tendência</div>
                <div style="font-size:.81rem;font-weight:600;">{topic}</div>
                <div style="font-size:.66rem;color:var(--t3);">{cnt}</div>
              </div>
              <span style="font-size:.69rem;color:var(--cy);">→</span>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Activity feed (notifications)
        if st.session_state.notifications:
            st.markdown(f"""<div class="exp-card">
              <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.9rem;">🔔 Atividade</div>""", unsafe_allow_html=True)
            for notif in st.session_state.notifications[:3]:
                st.markdown(f'<div style="font-size:.76rem;color:var(--t2);padding:.45rem 0;border-bottom:1px solid rgba(55,130,215,.07);">• {notif}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# SEARCH
# ═══════════════════════════════════════════════════
def page_search():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem;">Busca Acadêmica</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.82rem;margin-bottom:1rem;">Busca simultânea na Nebula, Semantic Scholar e CrossRef</p>', unsafe_allow_html=True)

    c1, c2 = st.columns([4, 1])
    with c1: q = st.text_input("", placeholder="Ex: 'CRISPR gene editing' · 'quantum machine learning' · 'dark matter'…", key="sq", label_visibility="collapsed")
    with c2:
        if st.button("🔍 Buscar", use_container_width=True, key="btn_s"):
            if q:
                with st.spinner("Buscando em bases acadêmicas…"):
                    nebula_r = [p for p in st.session_state.feed_posts
                                if q.lower() in p["title"].lower() or q.lower() in p["abstract"].lower()
                                or any(q.lower() in t.lower() for t in p["tags"])]
                    ss_r = search_ss(q, 6)
                    cr_r = search_cr(q, 4)
                    st.session_state.search_results = {"nebula":nebula_r,"ss":ss_r,"cr":cr_r}
                    st.session_state.last_sq = q
                    record([q.lower()], .3)

    if q and not st.session_state.get("search_results"):
        pass
    elif not q:
        # Suggestions
        u = guser()
        tags = area_to_tags(u.get("area",""))
        if tags:
            st.markdown(f'<div style="color:var(--t2);font-size:.81rem;margin:.8rem 0 .5rem;">💡 Sugestões para <strong>{u.get("area","")}</strong>:</div>', unsafe_allow_html=True)
            cols = st.columns(5)
            for i,t in enumerate(tags[:5]):
                with cols[i%5]:
                    if st.button(f"🔎 {t}", key=f"sug_{t}", use_container_width=True):
                        st.session_state.sq = t; st.rerun()

    if st.session_state.get("search_results") and st.session_state.get("last_sq"):
        results = st.session_state.search_results
        neb = results.get("nebula",[]); ss = results.get("ss",[]); cr = results.get("cr",[])
        web = ss + [x for x in cr if not any(x["title"].lower()==s["title"].lower() for s in ss)]
        total = len(neb)+len(web)

        tab_all, tab_neb, tab_web = st.tabs([f"  Todos ({total})  ",f"  Nebula ({len(neb)})  ",f"  Internet ({len(web)})  "])

        with tab_all:
            if neb:
                st.markdown('<div style="font-size:.68rem;color:var(--b300);font-weight:600;margin-bottom:.5rem;letter-spacing:.06em;text-transform:uppercase;">NEBULA</div>', unsafe_allow_html=True)
                for p in neb: render_post_card(p, ctx="s_all", compact=True)
            if web:
                if neb: st.markdown('<hr>', unsafe_allow_html=True)
                st.markdown('<div style="font-size:.68rem;color:var(--cyl);font-weight:600;margin-bottom:.5rem;letter-spacing:.06em;text-transform:uppercase;">BASES ACADÊMICAS</div>', unsafe_allow_html=True)
                for idx,a in enumerate(web): render_web_article(a, idx=idx, ctx="all_web")
            if not neb and not web:
                st.markdown('<div class="gc" style="padding:3rem;text-align:center;color:var(--t3);">Nenhum resultado. Tente outros termos.</div>', unsafe_allow_html=True)

        with tab_neb:
            if neb:
                for p in neb: render_post_card(p, ctx="s_neb", compact=True)
            else: st.info("Nenhum post encontrado na Nebula.")

        with tab_web:
            if web:
                for idx,a in enumerate(web): render_web_article(a, idx=idx, ctx="web_tab")
            else: st.info("Nenhum artigo encontrado online.")

    st.markdown('</div>', unsafe_allow_html=True)

def render_web_article(a, idx=0, ctx="web"):
    src_color="#22d3ee" if a.get("origin")=="semantic" else "#a78bfa"
    src_name="Semantic Scholar" if a.get("origin")=="semantic" else "CrossRef"
    cite=f" · {a['citations']} cit." if a.get("citations") else ""
    uid = re.sub(r'[^a-zA-Z0-9]','',f"{ctx}_{idx}_{str(a.get('doi',''))[:10]}")[:32]
    is_saved=any(s.get('doi')==a.get('doi') for s in st.session_state.saved_articles)
    abstract = a.get("abstract","")
    if len(abstract) > 260: abstract = abstract[:260] + "…"
    st.markdown(f"""<div class="scard">
      <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:.38rem;">
        <div style="flex:1;font-family:'Syne',sans-serif;font-size:.92rem;font-weight:700;">{a["title"]}</div>
        <span style="font-size:.63rem;color:{src_color};background:rgba(6,182,212,.07);border-radius:8px;padding:2px 8px;white-space:nowrap;flex-shrink:0;">{src_name}</span>
      </div>
      <div style="color:var(--t3);font-size:.70rem;margin-bottom:.42rem;">{a["authors"]} · <em>{a["source"]}</em> · {a["year"]}{cite}</div>
      <div style="color:var(--t2);font-size:.80rem;line-height:1.62;">{abstract}</div>
    </div>""", unsafe_allow_html=True)
    ca,cb,cc=st.columns([1,1,1])
    with ca:
        if st.button("🔖 Salvo" if is_saved else "📌 Salvar", key=f"svw_{uid}"):
            if is_saved: st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]; st.toast("Removido")
            else: st.session_state.saved_articles.append(a); st.toast("Salvo!")
            save_db(); st.rerun()
    with cb:
        if st.button("📋 Citar APA", key=f"ctw_{uid}"):
            st.toast(f'{a["authors"]} ({a["year"]}). {a["title"]}.')
    with cc:
        if a.get("url"):
            st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:var(--b300);font-size:.80rem;text-decoration:none;line-height:2.5;display:block;">Abrir ↗</a>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# KNOWLEDGE / CONNECTIONS
# ═══════════════════════════════════════════════════
def page_knowledge():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem;">Rede de Conexões</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.82rem;margin-bottom:1rem;">Pesquisadores conectados por tópicos em comum. Força da conexão baseada em tags compartilhadas.</p>', unsafe_allow_html=True)

    email = st.session_state.current_user
    users = st.session_state.users if isinstance(st.session_state.users,dict) else {}

    def get_tags(ue):
        ud=users.get(ue,{}); tags=set(area_to_tags(ud.get("area","")))
        for p in st.session_state.feed_posts:
            if p.get("author_email")==ue: tags.update(t.lower() for t in p.get("tags",[]))
        if ue==email:
            for fn,fd in st.session_state.folders.items():
                if isinstance(fd,dict): tags.update(t.lower() for t in fd.get("analysis_tags",[]))
        return tags

    rlist = list(users.keys())
    rtags = {ue:get_tags(ue) for ue in rlist}

    edges = []
    for i in range(len(rlist)):
        for j in range(i+1,len(rlist)):
            e1,e2=rlist[i],rlist[j]
            common=list(rtags[e1]&rtags[e2])
            is_fol = e2 in st.session_state.followed or e1 in st.session_state.followed
            if common or is_fol:
                strength=len(common)+(2 if is_fol else 0)
                edges.append((e1,e2,common[:5],strength))

    n=len(rlist); positions={}
    for idx,ue in enumerate(rlist):
        angle=2*3.14159*idx/max(n,1)
        r_dist=0.36+0.05*((hash(ue)%5)/4)
        positions[ue]={"x":0.5+r_dist*np.cos(angle),"y":0.5+r_dist*np.sin(angle),"z":0.5+0.12*((idx%4)/3-.35)}

    fig=go.Figure()
    for e1,e2,common,strength in edges:
        p1=positions[e1]; p2=positions[e2]
        alpha=min(0.55,0.10+strength*0.06)
        fig.add_trace(go.Scatter3d(x=[p1["x"],p2["x"],None],y=[p1["y"],p2["y"],None],z=[p1["z"],p2["z"],None],
            mode="lines",line=dict(color=f"rgba(55,130,215,{alpha:.2f})",width=min(4,1+strength)),
            hoverinfo="none",showlegend=False))

    nxyz=[[positions[ue]["x"],positions[ue]["y"],positions[ue]["z"]] for ue in rlist]
    ncolors=["#22d3ee" if ue==email else ("#60a5f5" if ue in st.session_state.followed else "#2272c3") for ue in rlist]
    nsizes=[24 if ue==email else (18 if ue in st.session_state.followed else max(12,10+sum(1 for e1,e2,_,__ in edges if e1==ue or e2==ue))) for ue in rlist]
    ntext=[users.get(ue,{}).get("name","?").split()[0] for ue in rlist]
    nhover=[f"<b>{users.get(ue,{}).get('name','?')}</b><br>Área: {users.get(ue,{}).get('area','')}<br>Conexões: {sum(1 for e1,e2,_,__ in edges if e1==ue or e2==ue)}<extra></extra>" for ue in rlist]
    fig.add_trace(go.Scatter3d(x=[p[0] for p in nxyz],y=[p[1] for p in nxyz],z=[p[2] for p in nxyz],
        mode="markers+text",marker=dict(size=nsizes,color=ncolors,opacity=.92,line=dict(color="rgba(147,197,253,.32)",width=1.5)),
        text=ntext,textposition="top center",textfont=dict(color="#8ba8cc",size=9,family="DM Sans"),
        hovertemplate=nhover,showlegend=False))
    fig.update_layout(height=490,
        scene=dict(xaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),
                   yaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),
                   zaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),
                   bgcolor="rgba(0,0,0,0)",camera=dict(eye=dict(x=1.5,y=1.3,z=0.9))),
        paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0),font=dict(color="#8ba8cc"))
    st.plotly_chart(fig,use_container_width=True)

    c1,c2,c3,c4=st.columns(4)
    for col,(v,l) in zip([c1,c2,c3,c4],[(len(rlist),"Pesquisadores"),(len(edges),"Conexões"),(len(st.session_state.followed),"Seguindo"),(len(st.session_state.feed_posts),"Pesquisas")]):
        with col: st.markdown(f'<div class="mbox"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>', unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    tab_map,tab_mine,tab_all=st.tabs(["  Mapa de Conexões  ","  Minhas Conexões  ","  Todos  "])

    with tab_map:
        if edges:
            for e1,e2,common,strength in sorted(edges,key=lambda x:-x[3])[:20]:
                n1=users.get(e1,{}); n2=users.get(e2,{})
                tags_s=tags_html(common[:4]) if common else '<span style="color:var(--t3);font-size:.72rem;">seguindo</span>'
                st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;"><span style="font-size:.82rem;font-weight:600;font-family:\'Syne\',sans-serif;color:var(--b300);">{n1.get("name","?")}</span><span style="color:var(--t3);">↔</span><span style="font-size:.82rem;font-weight:600;font-family:\'Syne\',sans-serif;color:var(--b300);">{n2.get("name","?")}</span><div style="flex:1;display:flex;flex-wrap:wrap;">{tags_s}</div><span style="font-size:.68rem;color:var(--cyl);font-weight:700;">⚡{strength}</span></div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="gc" style="text-align:center;padding:2.5rem;color:var(--t3);">Publique pesquisas com tags para ver conexões.</div>', unsafe_allow_html=True)

    with tab_mine:
        my_tags=rtags.get(email,set())
        if my_tags: st.markdown(f'<div style="margin-bottom:.9rem;font-size:.82rem;color:var(--t2);">Seus tópicos: {tags_html(list(my_tags)[:8])}</div>', unsafe_allow_html=True)
        my_conn=[(e1,e2,c,s) for e1,e2,c,s in edges if e1==email or e2==email]
        if my_conn:
            for e1,e2,common,strength in sorted(my_conn,key=lambda x:-x[3]):
                other=e2 if e1==email else e1; od=users.get(other,{})
                st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">{avh(ini(od.get("name","?")),38,get_photo(other))}<div style="flex:1;"><div style="font-weight:600;font-size:.87rem;font-family:\'Syne\',sans-serif;">{od.get("name","?")}</div><div style="font-size:.71rem;color:var(--t3);">{od.get("area","")}</div></div>{tags_html(common[:3])}</div></div>', unsafe_allow_html=True)
                cv,cm_b,_=st.columns([1,1,4])
                with cv:
                    if st.button("👤 Perfil",key=f"kv_{other}"):st.session_state.profile_view=other;st.rerun()
                with cm_b:
                    if st.button("💬 Chat",key=f"kc_{other}"):
                        if other not in st.session_state.chat_messages:st.session_state.chat_messages[other]=[]
                        st.session_state.active_chat=other;st.session_state.page="chat";st.rerun()
        else: st.markdown('<div class="gc" style="text-align:center;padding:2.5rem;color:var(--t3);">Nenhuma conexão ainda. Publique pesquisas!</div>', unsafe_allow_html=True)

    with tab_all:
        sq2=st.text_input("",placeholder="🔍 Buscar…",key="all_s",label_visibility="collapsed")
        for ue,ud in users.items():
            if ue==email: continue
            uname_r=ud.get("name","?"); uarea=ud.get("area","")
            if sq2 and sq2.lower() not in uname_r.lower() and sq2.lower() not in uarea.lower(): continue
            is_fol=ue in st.session_state.followed; conn_n=sum(1 for e1,e2,_,__ in edges if e1==ue or e2==ue)
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:10px;">{avh(ini(uname_r),38,get_photo(ue))}<div style="flex:1;"><div style="font-size:.87rem;font-weight:600;font-family:\'Syne\',sans-serif;">{uname_r}</div><div style="font-size:.71rem;color:var(--t3);">{uarea} · {conn_n} conexões</div></div>{"<span style=\\'color:var(--ok);font-size:.72rem;\\'>✓ Seguindo</span>" if is_fol else ""}</div></div>', unsafe_allow_html=True)
            ca2,cb2,cc2=st.columns([1,1,1])
            with ca2:
                if st.button("👤 Perfil",key=f"av_{ue}",use_container_width=True):st.session_state.profile_view=ue;st.rerun()
            with cb2:
                if st.button("✓ Seguindo" if is_fol else "➕ Seguir",key=f"af_{ue}",use_container_width=True):
                    if is_fol:st.session_state.followed.remove(ue);ud["followers"]=max(0,ud.get("followers",0)-1)
                    else:st.session_state.followed.append(ue);ud["followers"]=ud.get("followers",0)+1
                    save_db();st.rerun()
            with cc2:
                if st.button("💬 Chat",key=f"ac_{ue}",use_container_width=True):
                    if ue not in st.session_state.chat_messages:st.session_state.chat_messages[ue]=[]
                    st.session_state.active_chat=ue;st.session_state.page="chat";st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# FOLDERS
# ═══════════════════════════════════════════════════
def page_folders():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem;">Pastas de Pesquisa</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.82rem;margin-bottom:1rem;">Organize seus documentos. A análise inteligente alimenta sua rede de conexões.</p>', unsafe_allow_html=True)
    c1,c2,_=st.columns([2,1.2,1.5])
    with c1: nf_name=st.text_input("Nome da pasta",placeholder="Ex: Genômica Comparativa",key="nf_n")
    with c2: nf_desc=st.text_input("Descrição",placeholder="Breve descrição",key="nf_d")
    if st.button("➕ Criar pasta",key="btn_nf"):
        if nf_name.strip():
            if nf_name not in st.session_state.folders:
                st.session_state.folders[nf_name]={"desc":nf_desc,"files":[],"notes":"","analysis_tags":[],"analysis_summary":"","file_analyses":[]}
                save_db(); st.success(f"✓ '{nf_name}' criada!"); st.rerun()
            else: st.warning("Pasta já existe.")
        else: st.warning("Digite um nome.")
    st.markdown("<hr>", unsafe_allow_html=True)
    if not st.session_state.folders:
        st.markdown('<div class="gc" style="text-align:center;padding:3.5rem;"><div style="font-size:3rem;margin-bottom:1rem;">📂</div><div style="color:var(--t2);font-family:\'Syne\',sans-serif;font-size:1rem;">Nenhuma pasta ainda</div></div>', unsafe_allow_html=True)
    else:
        cols=st.columns(3)
        for idx,(fname,fdata) in enumerate(list(st.session_state.folders.items())):
            files=fdata.get("files",[]) if isinstance(fdata,dict) else fdata
            desc=fdata.get("desc","") if isinstance(fdata,dict) else ""
            at=fdata.get("analysis_tags",[]) if isinstance(fdata,dict) else []
            with cols[idx%3]:
                tag_p=tags_html(at[:3]) if at else ""
                st.markdown(f'<div class="gc" style="padding:1.2rem;text-align:center;margin-bottom:.6rem;"><div style="font-size:2.4rem;margin-bottom:8px;">📁</div><div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.96rem;">{fname}</div><div style="color:var(--t3);font-size:.70rem;margin-top:3px;">{desc}</div><div style="color:var(--b300);font-size:.71rem;margin-top:5px;">{len(files)} arquivo(s)</div><div style="margin-top:6px;">{tag_p}</div></div>', unsafe_allow_html=True)
                with st.expander(f"📂 Abrir '{fname}'"):
                    up=st.file_uploader("",type=None,key=f"up_{fname}",label_visibility="collapsed")
                    if up:
                        lst=fdata["files"] if isinstance(fdata,dict) else fdata
                        if up.name not in lst: lst.append(up.name)
                        save_db(); st.success("✓ Adicionado!"); st.rerun()
                    if files:
                        for f in files: st.markdown(f'<div style="font-size:.79rem;padding:5px 0;color:var(--t2);border-bottom:1px solid var(--gbd);">📄 {f}</div>', unsafe_allow_html=True)
                    else: st.markdown('<p style="color:var(--t3);font-size:.76rem;text-align:center;padding:.5rem;">Faça upload acima.</p>', unsafe_allow_html=True)
                    st.markdown("<hr>", unsafe_allow_html=True)
                    if st.button("🔬 Analisar documentos",key=f"analyze_{fname}",use_container_width=True):
                        if files:
                            with st.spinner("Analisando…"):
                                result=analyze_folder(fname)
                            if result and isinstance(fdata,dict):
                                fdata["analysis_tags"]=result["tags"]; fdata["analysis_summary"]=result["summary"]
                                fdata["file_analyses"]=result["file_analyses"]
                                save_db(); record(result["tags"],1.5); st.success("✓ Análise concluída!"); st.rerun()
                        else: st.warning("Adicione arquivos antes.")
                    if isinstance(fdata,dict) and fdata.get("analysis_summary"):
                        st.markdown(f'<div class="abox"><div style="font-size:.67rem;color:var(--t3);text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">Resumo</div><div style="font-size:.81rem;color:var(--t2);">{fdata["analysis_summary"]}</div></div>', unsafe_allow_html=True)
                        if at: st.markdown(tags_html(at), unsafe_allow_html=True)
                    note=st.text_area("Notas",value=fdata.get("notes","") if isinstance(fdata,dict) else "",key=f"note_{fname}",height=70,placeholder="Observações…")
                    c_sn,c_del=st.columns(2)
                    with c_sn:
                        if st.button("💾 Salvar nota",key=f"sn_{fname}",use_container_width=True):
                            if isinstance(fdata,dict): fdata["notes"]=note
                            save_db(); st.success("✓ Salvo!")
                    with c_del:
                        if st.button(f"🗑️ Excluir",key=f"df_{fname}",use_container_width=True):
                            del st.session_state.folders[fname]; save_db(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# ANALYTICS
# ═══════════════════════════════════════════════════
def page_analytics():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem;">Painel de Pesquisa</h1>', unsafe_allow_html=True)
    email=st.session_state.current_user; d=st.session_state.stats_data
    pc=dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#3d5a80",family="DM Sans"),margin=dict(l=10,r=10,t=42,b=10),
            xaxis=dict(showgrid=False,color="#3d5a80"),yaxis=dict(showgrid=True,gridcolor="rgba(55,130,215,.07)",color="#3d5a80"))

    tab_folders,tab_pubs,tab_impact,tab_pref=st.tabs(["  📂 Pastas  ","  📝 Publicações  ","  📈 Impacto  ","  🎯 Interesses  "])

    with tab_folders:
        folders=st.session_state.folders
        if not folders:
            st.markdown('<div class="gc" style="text-align:center;padding:3.5rem;"><div style="font-size:2.5rem;margin-bottom:1rem;">📂</div><div style="color:var(--t2);font-family:\'Syne\',sans-serif;">Crie pastas e analise documentos para ver dados aqui.</div></div>', unsafe_allow_html=True)
        else:
            total_files=sum(len(fd.get("files",[]) if isinstance(fd,dict) else fd) for fd in folders.values())
            total_analyzed=sum(1 for fd in folders.values() if isinstance(fd,dict) and fd.get("analysis_tags"))
            all_tags_flat=[t for fd in folders.values() if isinstance(fd,dict) for t in fd.get("analysis_tags",[])]
            c1,c2,c3,c4=st.columns(4)
            with c1: st.markdown(f'<div class="mbox"><div class="mval">{len(folders)}</div><div class="mlbl">Pastas</div></div>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="mbox"><div class="mval">{total_files}</div><div class="mlbl">Arquivos</div></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="mbox"><div class="mval">{total_analyzed}</div><div class="mlbl">Analisadas</div></div>', unsafe_allow_html=True)
            with c4: st.markdown(f'<div class="mbox"><div class="mval">{len(set(all_tags_flat))}</div><div class="mlbl">Áreas únicas</div></div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            fnames=list(folders.keys()); fcounts=[len(fd.get("files",[]) if isinstance(fd,dict) else fd) for fd in folders.values()]
            if any(c>0 for c in fcounts):
                fig_fc=go.Figure()
                fig_fc.add_trace(go.Bar(x=fnames,y=fcounts,marker=dict(color=fcounts,colorscale=[[0,"#0f2040"],[.5,"#2272c3"],[1,"#22d3ee"]],line=dict(color="rgba(90,158,240,.2)",width=1)),text=fcounts,textposition="outside",textfont=dict(color="#8ba8cc",size=11)))
                fig_fc.update_layout(title=dict(text="Arquivos por Pasta",font=dict(color="#e0e8ff",family="Syne",size=14)),height=260,**pc)
                st.plotly_chart(fig_fc,use_container_width=True)
            if all_tags_flat:
                tc=Counter(all_tags_flat).most_common(10); tnames,tcounts=zip(*tc)
                fig_tags=go.Figure()
                fig_tags.add_trace(go.Bar(y=list(tnames),x=list(tcounts),orientation='h',marker=dict(color=list(tcounts),colorscale=[[0,"#1a3a6b"],[.5,"#3b8de0"],[1,"#06b6d4"]],line=dict(color="rgba(90,158,240,.15)",width=1)),text=list(tcounts),textposition="outside",textfont=dict(color="#8ba8cc",size=10)))
                fig_tags.update_layout(title=dict(text="Áreas nas Pastas",font=dict(color="#e0e8ff",family="Syne",size=14)),height=320,**pc,yaxis=dict(autorange="reversed",color="#3d5a80"))
                st.plotly_chart(fig_tags,use_container_width=True)
            st.markdown('<h3>Detalhamento por Pasta</h3>', unsafe_allow_html=True)
            for fname,fdata in folders.items():
                if not isinstance(fdata,dict): continue
                files=fdata.get("files",[]); fa=fdata.get("file_analyses",[]); at=fdata.get("analysis_tags",[])
                with st.expander(f"📁 {fname} — {len(files)} arquivo(s)"):
                    if not files: st.markdown('<p style="color:var(--t3);font-size:.79rem;">Nenhum arquivo.</p>', unsafe_allow_html=True); continue
                    if fa:
                        tc2=Counter(x.get("type","Outro") for x in fa)
                        cp,cprog=st.columns([1,1.5])
                        with cp:
                            fig_pie=go.Figure(go.Pie(labels=list(tc2.keys()),values=list(tc2.values()),hole=0.55,marker=dict(colors=["#2272c3","#06b6d4","#3b8de0","#1a3a6b","#8b5cf6","#10b981"],line=dict(color=["#010409"]*10,width=2)),textfont=dict(color="white",size=10)))
                            fig_pie.update_layout(title=dict(text="Tipos",font=dict(color="#e0e8ff",family="Syne",size=12)),height=200,plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",legend=dict(font=dict(color="#8ba8cc",size=9)),margin=dict(l=0,r=0,t=35,b=0))
                            st.plotly_chart(fig_pie,use_container_width=True)
                        with cprog:
                            st.markdown('<div style="font-size:.68rem;color:var(--t3);text-transform:uppercase;letter-spacing:.06em;margin-bottom:.6rem;">Progresso por Arquivo</div>', unsafe_allow_html=True)
                            for item in fa:
                                prog=item.get("progress",50)
                                color="#10b981" if prog>=80 else ("#f59e0b" if prog>=50 else "#ef4444")
                                st.markdown(f'<div style="margin-bottom:.55rem;"><div style="display:flex;justify-content:space-between;font-size:.75rem;margin-bottom:3px;"><span style="color:var(--t2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:68%;">📄 {item["file"][:26]}</span><span style="color:{color};font-weight:600;">{prog}%</span></div>{prog_bar(prog,color)}</div>', unsafe_allow_html=True)
                        if at: st.markdown(f'<div style="margin-top:.4rem;">{tags_html(at)}</div>', unsafe_allow_html=True)
                    else: st.markdown('<p style="color:var(--t3);font-size:.79rem;">Clique em "Analisar documentos" na pasta.</p>', unsafe_allow_html=True)

    with tab_pubs:
        my_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==email]
        if not my_posts: st.markdown('<div class="gc" style="text-align:center;padding:2.5rem;color:var(--t3);">Publique pesquisas para ver métricas.</div>', unsafe_allow_html=True)
        else:
            c1,c2,c3=st.columns(3)
            with c1: st.markdown(f'<div class="mbox"><div class="mval">{len(my_posts)}</div><div class="mlbl">Pesquisas</div></div>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="mbox"><div class="mval">{sum(p["likes"] for p in my_posts)}</div><div class="mlbl">Curtidas</div></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="mbox"><div class="mval">{sum(len(p["comments"]) for p in my_posts)}</div><div class="mlbl">Comentários</div></div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            fig_eng=go.Figure()
            titles_s=[p["title"][:18]+"…" for p in my_posts]
            fig_eng.add_trace(go.Bar(name="Curtidas",x=titles_s,y=[p["likes"] for p in my_posts],marker_color="#2272c3"))
            fig_eng.add_trace(go.Bar(name="Comentários",x=titles_s,y=[len(p["comments"]) for p in my_posts],marker_color="#06b6d4"))
            fig_eng.update_layout(barmode="group",title=dict(text="Engajamento",font=dict(color="#e0e8ff",family="Syne",size=14)),height=260,**pc,legend=dict(font=dict(color="#8ba8cc")))
            st.plotly_chart(fig_eng,use_container_width=True)
            for p in sorted(my_posts,key=lambda x:x.get("date",""),reverse=True):
                st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;justify-content:space-between;"><div style="font-family:\'Syne\',sans-serif;font-size:.89rem;font-weight:700;">{p["title"][:55]}{"…" if len(p["title"])>55 else ""}</div>{badge(p["status"])}</div><div style="font-size:.73rem;color:var(--t3);margin-top:.4rem;">{p.get("date","")} · ❤ {p["likes"]} · 💬 {len(p["comments"])} · 👁 {fmt_num(p.get("views",0))}</div><div style="margin-top:.4rem;">{tags_html(p["tags"][:4])}</div></div>', unsafe_allow_html=True)

    with tab_impact:
        c1,c2,c3=st.columns(3)
        with c1: st.markdown(f'<div class="mbox"><div class="mval">{d.get("h_index",4)}</div><div class="mlbl">Índice H</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="mbox"><div class="mval">{d.get("fator_impacto",3.8):.1f}</div><div class="mlbl">Fator de impacto</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="mbox"><div class="mval">{len(st.session_state.saved_articles)}</div><div class="mlbl">Artigos salvos</div></div>', unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)
        new_h=st.number_input("Índice H",0,200,d.get("h_index",4),key="e_h")
        new_fi=st.number_input("Fator de impacto",0.0,100.0,float(d.get("fator_impacto",3.8)),step=0.1,key="e_fi")
        new_notes=st.text_area("Notas",value=d.get("notes",""),key="e_notes",height=80)
        if st.button("💾 Salvar",key="btn_save_m"): d.update({"h_index":new_h,"fator_impacto":new_fi,"notes":new_notes}); st.success("✓ Salvo!")

    with tab_pref:
        prefs=st.session_state.user_prefs.get(email,{})
        if prefs:
            st.markdown('<p style="color:var(--t3);font-size:.80rem;margin-bottom:1rem;">Baseado em interações, publicações e documentos.</p>', unsafe_allow_html=True)
            top=sorted(prefs.items(),key=lambda x:-x[1])[:12]; mx=max(s for _,s in top) if top else 1
            c1,c2=st.columns(2)
            for i,(tag,score) in enumerate(top):
                pct=int(score/mx*100)
                color="#2272c3" if pct>70 else ("#3b8de0" if pct>40 else "#1a3a6b")
                with (c1 if i%2==0 else c2):
                    st.markdown(f'<div style="display:flex;justify-content:space-between;font-size:.79rem;margin-bottom:3px;"><span style="color:var(--t2);">{tag}</span><span style="color:var(--b300);font-weight:600;">{pct}%</span></div>{prog_bar(pct,color)}', unsafe_allow_html=True)
        else: st.info("Interaja com pesquisas para construir seu perfil.")
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# IMAGE ANALYSIS PAGE
# ═══════════════════════════════════════════════════
def page_img_search():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem;">Análise Visual Científica</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.82rem;margin-bottom:1.2rem;">Detecta padrões, linhas, formas, cores e estruturas · Classifica com IA · Conecta com pesquisas similares na rede</p>', unsafe_allow_html=True)

    col_up, col_res = st.columns([1, 1.85])
    with col_up:
        st.markdown('<div class="gc" style="padding:1.2rem;">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.88rem;margin-bottom:.7rem;">📷 Carregar Imagem</div>', unsafe_allow_html=True)
        img_file = st.file_uploader("", type=["png","jpg","jpeg","webp","tiff"], label_visibility="collapsed", key="img_up")
        if img_file: st.image(img_file, use_container_width=True, caption="Imagem carregada")
        run = st.button("🔬 Analisar Imagem", use_container_width=True, key="btn_run")
        st.markdown("""<div style="margin-top:.9rem;font-size:.70rem;color:var(--t3);line-height:1.75;">
          <div>🧮 Sobel · FFT · Simetria Radial</div>
          <div>🎨 Análise de Cor · Paleta Dominante</div>
          <div>🔗 Conexões com pesquisas similares</div>
          <div>🌐 Artigos académicos relacionados</div>
        </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_res:
        if run and img_file:
            img_file.seek(0)
            with st.spinner("Analisando padrões, bordas, formas e cores…"):
                rep = analyze_image_advanced(img_file)
                st.session_state.img_result = rep
            if rep:
                # ── CATEGORY + CONFIDENCE ──
                conf_color = "#10b981" if rep["confidence"]>80 else ("#f59e0b" if rep["confidence"]>60 else "#ef4444")
                st.markdown(f"""<div class="abox" style="animation:glowPulse 3s ease infinite;">
                  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:.5rem;">
                    <div>
                      <div style="font-size:.64rem;color:var(--t3);letter-spacing:.10em;text-transform:uppercase;margin-bottom:4px;">Categoria Detectada</div>
                      <div style="font-family:'Syne',sans-serif;font-size:1.08rem;font-weight:700;color:var(--t1);margin-bottom:4px;">{rep["category"]}</div>
                    </div>
                    <div style="background:rgba(0,0,0,.3);border:1px solid rgba(55,130,215,.2);border-radius:var(--r12);padding:.5rem .9rem;text-align:center;flex-shrink:0;">
                      <div style="font-family:'Syne',sans-serif;font-size:1.4rem;font-weight:800;color:{conf_color};">{rep["confidence"]}%</div>
                      <div style="font-size:.60rem;color:var(--t3);text-transform:uppercase;letter-spacing:.05em;">confiança</div>
                    </div>
                  </div>
                  <div style="font-size:.82rem;color:var(--t2);line-height:1.65;margin-bottom:.55rem;">{rep["description"]}</div>
                  {"<div style='font-size:.76rem;color:var(--cyl);margin-bottom:.4rem;'>ℹ " + rep['subcategory'] + "</div>" if rep.get('subcategory') else ""}
                  <div style="display:flex;gap:1.5rem;flex-wrap:wrap;margin-top:.5rem;">
                    <div style="font-size:.71rem;color:var(--t3);">Material: <strong style="color:var(--t2);">{rep["material"]}</strong></div>
                    <div style="font-size:.71rem;color:var(--t3);">Estrutura: <strong style="color:var(--t2);">{rep["object_type"]}</strong></div>
                    <div style="font-size:.71rem;color:var(--t3);">Resolução: <strong style="color:var(--t2);">{rep["size"][0]}×{rep["size"][1]}</strong></div>
                    {"<div style='font-size:.71rem;color:var(--warn);'>Orgânico: " + str(rep["skin_pct"]) + "%</div>" if rep["skin_pct"]>10 else ""}
                  </div>
                </div>""", unsafe_allow_html=True)

                # ── 3 METRIC BOXES ──
                c1,c2,c3=st.columns(3)
                with c1: st.markdown(f'<div class="mbox"><div style="font-family:\'Syne\',sans-serif;font-size:1.1rem;font-weight:700;color:var(--b300);">{rep["texture"]["complexity"]}</div><div class="mlbl">Complexidade</div></div>', unsafe_allow_html=True)
                with c2: sym_level="Alta" if rep["symmetry"]>0.78 else ("Média" if rep["symmetry"]>0.52 else "Baixa"); st.markdown(f'<div class="mbox"><div style="font-family:\'Syne\',sans-serif;font-size:1.1rem;font-weight:700;color:var(--b300);">{sym_level}</div><div class="mlbl">Simetria ({rep["symmetry"]})</div></div>', unsafe_allow_html=True)
                with c3: st.markdown(f'<div class="mbox"><div style="font-family:\'Syne\',sans-serif;font-size:1.1rem;font-weight:700;color:var(--b300);">{rep["lines"]["direction"]}</div><div class="mlbl">Linhas</div></div>', unsafe_allow_html=True)

                # ── LINE ANALYSIS CHART ──
                l = rep["lines"]
                strengths = l["strengths"]
                max_s = max(strengths.values()) + 0.01
                st.markdown(f"""<div class="pbox">
                  <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:.85rem;margin-bottom:.7rem;color:var(--cyl);">📐 Análise de Linhas e Bordas</div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:.79rem;color:var(--t2);margin-bottom:.8rem;">
                    <div><span style="color:var(--t3);">Intensidade total:</span><br><strong style="font-size:.95rem;">{l["intensity"]:.2f}</strong></div>
                    <div><span style="color:var(--t3);">Intensidade máx:</span><br><strong style="font-size:.95rem;">{l["max"]:.1f}</strong></div>
                  </div>
                  <div style="font-size:.70rem;color:var(--t3);text-transform:uppercase;letter-spacing:.05em;margin-bottom:.5rem;">Força por direção</div>""", unsafe_allow_html=True)
                for dir_name, val in strengths.items():
                    pct = int(val/max_s*100)
                    is_dom = dir_name == l["direction"]
                    color = "#22d3ee" if is_dom else "#2272c3"
                    st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:.4rem;"><span style="font-size:.72rem;color:{"var(--cyl)" if is_dom else "var(--t3)"};width:90px;flex-shrink:0;">{"★" if is_dom else " "} {dir_name}</span><div style="flex:1;">{prog_bar(pct,color)}</div><span style="font-size:.70rem;color:var(--t3);width:38px;text-align:right;">{val:.2f}</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:.72rem;color:var(--t3);margin-top:.6rem;">Formas: {" · ".join(f"<span style=\'color:var(--cyl);\'>{s}</span>" for s in rep["shapes"])}</div></div>', unsafe_allow_html=True)

                # ── TEXTURE RADAR CHART ──
                radar_cats = ["Entropia", "Contraste", "Bordas", "Simetria", "Sim. Bilateral"]
                radar_max = [8.0, 128.0, 80.0, 1.0, 1.0]
                radar_vals = [rep["texture"]["entropy"], rep["texture"]["contrast"], rep["lines"]["intensity"], rep["symmetry"], rep["lr_symmetry"]]
                radar_norm = [min(v/m, 1)*100 for v,m in zip(radar_vals, radar_max)]
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(r=radar_norm+[radar_norm[0]], theta=radar_cats+[radar_cats[0]],
                    fill='toself', fillcolor='rgba(34,114,195,.18)', line=dict(color='#3b8de0',width=2),
                    marker=dict(color='#22d3ee',size=5)))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,100],tickfont=dict(color="#3d5a80",size=8),gridcolor="rgba(55,130,215,.10)"),angularaxis=dict(tickfont=dict(color="#8ba8cc",size=9)),bgcolor="rgba(0,0,0,0)"),paper_bgcolor="rgba(0,0,0,0)",height=220,margin=dict(l=35,r=35,t=20,b=20),font=dict(color="#8ba8cc",family="DM Sans"),showlegend=False)
                st.plotly_chart(fig_radar, use_container_width=True)

                # ── COLOR ANALYSIS ──
                r_v, g_v, b_v = rep["color"]["r"], rep["color"]["g"], rep["color"]["b"]
                hex_col = "#{:02x}{:02x}{:02x}".format(int(r_v),int(g_v),int(b_v))
                pal_html = "".join(f'<div style="display:flex;flex-direction:column;align-items:center;gap:3px;"><div style="width:34px;height:34px;border-radius:9px;background:rgb{str(p)};border:1.5px solid rgba(255,255,255,.12);box-shadow:0 2px 8px rgba(0,0,0,.5);"></div><div style="font-size:.58rem;color:var(--t3);">#{"{:02x}{:02x}{:02x}".format(*p).upper()}</div></div>' for p in rep["palette"][:6])
                st.markdown(f"""<div class="abox">
                  <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:.85rem;margin-bottom:.8rem;">🎨 Análise de Cor</div>
                  <div style="display:flex;gap:14px;align-items:center;margin-bottom:.9rem;">
                    <div style="width:48px;height:48px;border-radius:12px;background:{hex_col};border:2px solid var(--gbdl);flex-shrink:0;box-shadow:0 4px 16px rgba(0,0,0,.6);"></div>
                    <div style="font-size:.80rem;color:var(--t2);line-height:1.75;">
                      RGB: <strong style="color:var(--t1);">({int(r_v)}, {int(g_v)}, {int(b_v)})</strong> · Hex: <strong style="color:var(--t1);">{hex_col.upper()}</strong><br>
                      Canal dom.: <strong style="color:var(--t1);">{rep["color"]["dominant"]}</strong> · Temp.: <strong style="color:var(--t1);">{rep["color"]["temp"]}</strong><br>
                      Saturação: <strong style="color:var(--t1);">{rep["color"]["saturation"]:.0f}%</strong> · Diversidade: <strong style="color:var(--t1);">{rep["color"]["diversity"]:.0f}%</strong>
                    </div>
                  </div>
                  <div style="font-size:.70rem;color:var(--t3);margin-bottom:7px;text-transform:uppercase;letter-spacing:.05em;">Paleta dominante</div>
                  <div style="display:flex;gap:7px;flex-wrap:wrap;">{pal_html}</div>
                  <div style="margin-top:.8rem;display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:.79rem;color:var(--t3);">
                    <div>Entropia: <strong style="color:var(--t1);">{rep["texture"]["entropy"]} bits</strong></div>
                    <div>Contraste: <strong style="color:var(--t1);">{rep["texture"]["contrast"]:.2f}</strong></div>
                    {"<div>Tecido detect.: <strong style='color:var(--warn);'>"+str(rep['skin_pct'])+"% </strong></div>" if rep["skin_pct"]>10 else ""}
                    {"<div>Região sanguínea: <strong style='color:#ef4444;'>"+str(rep['blood_pct'])+"% </strong></div>" if rep["blood_pct"]>5 else ""}
                  </div>
                </div>""", unsafe_allow_html=True)
            else:
                st.error("Não foi possível analisar. Verifique o formato.")

        elif not img_file:
            st.markdown("""<div class="gc" style="padding:5rem 2rem;text-align:center;">
              <div style="font-size:4rem;margin-bottom:1.2rem;opacity:.7;">🔬</div>
              <div style="font-family:'Syne',sans-serif;font-size:1.05rem;color:var(--t2);margin-bottom:.7rem;">Carregue uma imagem científica</div>
              <div style="color:var(--t3);font-size:.78rem;line-height:1.85;">
                PNG · JPG · WEBP · TIFF<br>
                Microscopia · Cristalografia · Fluorescência<br>
                Histologia · Satélite · Diagramas · Molecular
              </div>
            </div>""", unsafe_allow_html=True)

    # ── CONNECTIONS SECTION ──
    if st.session_state.get("img_result"):
        rep = st.session_state.img_result
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<h2>🔎 Pesquisas Relacionadas</h2>', unsafe_allow_html=True)
        st.markdown(f'<p style="color:var(--t3);font-size:.80rem;margin-bottom:1rem;">Buscando por: <em>{rep["category"]} · {rep["object_type"]}</em></p>', unsafe_allow_html=True)

        tab_neb, tab_folders_tab, tab_web = st.tabs(["  Na Nebula  ","  Nas Pastas  ","  Internet  "])

        with tab_neb:
            # Search Nebula posts
            kw = rep.get("kw","").lower().split()
            cat_words = rep.get("category","").lower().split() + rep.get("object_type","").lower().split() + rep.get("material","").lower().split()
            all_terms = list(set(kw + cat_words))
            neb_results = []
            for p in st.session_state.feed_posts:
                ptxt = (p.get("title","")+" "+p.get("abstract","")+" "+" ".join(p.get("tags",[]))).lower()
                sc = sum(1 for t in all_terms if len(t)>2 and t in ptxt)
                if sc>0: neb_results.append((sc,p))
            neb_results.sort(key=lambda x:-x[0])
            if neb_results:
                for _,p in neb_results[:4]:
                    render_post_card(p, ctx="img_neb", compact=True)
            else:
                st.markdown('<div style="color:var(--t3);font-size:.80rem;padding:1rem;">Nenhuma pesquisa similar na Nebula.</div>', unsafe_allow_html=True)

        with tab_folders_tab:
            folder_matches = []
            for fname, fdata in st.session_state.folders.items():
                if not isinstance(fdata,dict): continue
                ftags = [t.lower() for t in fdata.get("analysis_tags",[])]
                sc = sum(1 for t in all_terms if len(t)>2 and any(t in ft for ft in ftags))
                if sc>0: folder_matches.append((sc,fname,fdata))
            folder_matches.sort(key=lambda x:-x[0])
            if folder_matches:
                for _,fname,fdata in folder_matches[:4]:
                    at = fdata.get("analysis_tags",[])
                    st.markdown(f"""<div class="img-result-card">
                      <div style="font-family:'Syne',sans-serif;font-size:.92rem;font-weight:700;margin-bottom:.35rem;">📁 {fname}</div>
                      <div style="color:var(--t3);font-size:.70rem;margin-bottom:.4rem;">{len(fdata.get("files",[]))} arquivos</div>
                      <div>{tags_html(at[:6])}</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:var(--t3);font-size:.80rem;padding:1rem;">Nenhum documento relacionado nas pastas. Adicione e analise documentos!</div>', unsafe_allow_html=True)

        with tab_web:
            cache_k = f"img_{rep['kw'][:40]}"
            if cache_k not in st.session_state.scholar_cache:
                with st.spinner("Buscando artigos relacionados…"):
                    query = f"{rep['category']} {rep['object_type']} {rep['material']}"
                    web = search_ss(query, 4)
                    st.session_state.scholar_cache[cache_k] = web
            web_r = st.session_state.scholar_cache.get(cache_k,[])
            if web_r:
                for idx,a in enumerate(web_r): render_web_article(a, idx=idx+2000, ctx="img_web")
            else:
                st.markdown('<div style="color:var(--t3);font-size:.80rem;padding:1rem;">Sem resultados online.</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# CHAT
# ═══════════════════════════════════════════════════
def page_chat():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem;">Mensagens</h1>', unsafe_allow_html=True)
    col_c, col_m = st.columns([.88, 2.7])
    email = st.session_state.current_user
    users = st.session_state.users if isinstance(st.session_state.users,dict) else {}

    with col_c:
        st.markdown('<div style="font-size:.68rem;font-weight:600;color:var(--t3);letter-spacing:.08em;text-transform:uppercase;margin-bottom:.8rem;">CONVERSAS</div>', unsafe_allow_html=True)
        shown = set()
        for ue in st.session_state.chat_contacts:
            if ue==email or ue in shown: continue
            shown.add(ue)
            ud = users.get(ue,{}); uname=ud.get("name","?"); uin=ini(uname); uphoto=ud.get("photo_b64")
            msgs=st.session_state.chat_messages.get(ue,[]); last_msg=msgs[-1]["text"][:28]+"…" if msgs and len(msgs[-1]["text"])>28 else (msgs[-1]["text"] if msgs else "Iniciar conversa")
            active=st.session_state.active_chat==ue; online=random.random()>.42
            dot='<span class="don"></span>' if online else '<span class="doff"></span>'
            bg="rgba(30,100,180,.22)" if active else "var(--gb)"; bdr="rgba(90,158,240,.40)" if active else "var(--gbd)"
            unread = random.randint(0,3) if not active and msgs else 0
            unread_html = f'<div style="background:var(--b500);color:white;border-radius:10px;padding:1px 6px;font-size:.62rem;font-weight:600;min-width:18px;text-align:center;">{unread}</div>' if unread > 0 else ''
            st.markdown(f'<div style="background:{bg};border:1px solid {bdr};border-radius:var(--r18);padding:9px 11px;margin-bottom:5px;"><div style="display:flex;align-items:center;gap:8px;">{avh_ring(uin,34,uphoto,online)}<div style="overflow:hidden;flex:1;"><div style="font-size:.82rem;font-weight:600;font-family:\'Syne\',sans-serif;display:flex;align-items:center;">{dot}{uname}</div><div style="font-size:.70rem;color:var(--t3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{last_msg}</div></div>{unread_html}</div></div>', unsafe_allow_html=True)
            if st.button("Abrir", key=f"oc_{ue}", use_container_width=True):
                st.session_state.active_chat=ue; st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
        nc=st.text_input("",placeholder="Adicionar por e-mail…",key="new_ct",label_visibility="collapsed")
        if st.button("➕",key="btn_add_ct",use_container_width=True):
            if nc in users and nc!=email:
                if nc not in st.session_state.chat_contacts: st.session_state.chat_contacts.append(nc)
                st.rerun()
            elif nc: st.toast("Usuário não encontrado.")

    with col_m:
        if st.session_state.active_chat:
            contact=st.session_state.active_chat
            cd=users.get(contact,{}); cname=cd.get("name","?"); cin=ini(cname); cphoto=cd.get("photo_b64")
            msgs=st.session_state.chat_messages.get(contact,[])
            is_online=random.random()>.35
            dot='<span class="don"></span>' if is_online else '<span class="doff"></span>'
            st.markdown(f'<div style="background:var(--gb);border:1px solid var(--gbd);border-radius:var(--r18);padding:13px 16px;margin-bottom:1rem;display:flex;align-items:center;gap:12px;"><div style="flex-shrink:0;">{avh_ring(cin,40,cphoto,is_online)}</div><div style="flex:1;"><div style="font-weight:700;font-size:.94rem;font-family:\'Syne\',sans-serif;display:flex;align-items:center;">{dot}{cname}</div><div style="font-size:.70rem;color:var(--ok);">🔒 AES-256</div></div></div>', unsafe_allow_html=True)
            for msg in msgs:
                is_me=msg["from"]=="me"
                cls="bme" if is_me else "bthem"
                align="right" if is_me else "left"
                st.markdown(f'<div style="display:flex;{"justify-content:flex-end" if is_me else ""}"><div class="{cls}">{msg["text"]}<div style="font-size:.62rem;color:rgba(255,255,255,.35);margin-top:3px;text-align:{align};">{msg["time"]} {"✓✓" if is_me else ""}</div></div></div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            c_inp,c_btn=st.columns([5,1])
            with c_inp: nm=st.text_input("",placeholder="Escreva sua mensagem…",key=f"mi_{contact}",label_visibility="collapsed")
            with c_btn:
                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
                if st.button("→",key=f"ms_{contact}",use_container_width=True):
                    if nm:
                        now=datetime.now().strftime("%H:%M")
                        st.session_state.chat_messages.setdefault(contact,[]).append({"from":"me","text":nm,"time":now}); st.rerun()
        else:
            st.markdown('<div class="gc" style="text-align:center;padding:6rem;"><div style="font-size:3.5rem;margin-bottom:1rem;">💬</div><div style="color:var(--t2);font-family:\'Syne\',sans-serif;font-size:1rem;">Selecione uma conversa</div><div style="font-size:.76rem;color:var(--t3);margin-top:.5rem;">🔒 Criptografia end-to-end</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════
def page_settings():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1.4rem;">Perfil e Configurações</h1>', unsafe_allow_html=True)
    u=guser(); email=st.session_state.current_user; in_=ini(u.get("name","?")); photo=u.get("photo_b64")
    tab_p,tab_s,tab_pr,tab_saved=st.tabs(["  Meu Perfil  ","  Segurança  ","  Privacidade  ","  Artigos Salvos  "])

    with tab_p:
        photo_html=f"<img src='{photo}'/>" if photo else f'<span style="font-size:2.2rem;">{in_}</span>'
        my_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==email]
        total_likes=sum(p["likes"] for p in my_posts)
        st.markdown(f"""<div class="prof-hero">
          <div class="prof-photo">{photo_html}</div>
          <div style="flex:1;z-index:1;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:.25rem;">
              <h1 style="margin:0;">{u.get("name","?")}</h1>
              <span style="font-size:.72rem;color:var(--cy);">✓ Verificado</span>
            </div>
            <div style="color:var(--b300);font-size:.84rem;font-weight:500;margin-bottom:.4rem;">@{u.get("name","").lower().replace(" ","_")} · {u.get("area","")}</div>
            <div style="color:var(--t2);font-size:.82rem;line-height:1.65;margin-bottom:.9rem;">{u.get("bio","Sem biografia.")}</div>
            <div style="display:flex;gap:2rem;">
              <div><span style="font-weight:800;font-family:'Syne',sans-serif;">{u.get("followers",0)}</span><span style="color:var(--t3);font-size:.73rem;"> seguidores</span></div>
              <div><span style="font-weight:800;font-family:'Syne',sans-serif;">{u.get("following",0)}</span><span style="color:var(--t3);font-size:.73rem;"> seguindo</span></div>
              <div><span style="font-weight:800;font-family:'Syne',sans-serif;">{len(my_posts)}</span><span style="color:var(--t3);font-size:.73rem;"> pesquisas</span></div>
              <div><span style="font-weight:800;font-family:'Syne',sans-serif;">{fmt_num(total_likes)}</span><span style="color:var(--t3);font-size:.73rem;"> curtidas</span></div>
            </div>
          </div></div>""", unsafe_allow_html=True)
        st.markdown('<div style="font-family:\'Syne\',sans-serif;font-weight:700;font-size:.87rem;margin-bottom:.5rem;">📷 Foto de perfil</div>', unsafe_allow_html=True)
        ph=st.file_uploader("",type=["png","jpg","jpeg","webp"],label_visibility="collapsed",key="ph_up")
        if ph:
            b64=img_to_b64(ph)
            if b64: st.session_state.users[email]["photo_b64"]=b64; save_db(); st.success("✓ Foto atualizada!"); st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
        new_n=st.text_input("Nome completo",value=u.get("name",""),key="cfg_n")
        new_a=st.text_input("Área de pesquisa",value=u.get("area",""),key="cfg_a")
        new_b=st.text_area("Biografia",value=u.get("bio",""),key="cfg_b",height=90,placeholder="Descreva sua pesquisa e interesses…")
        c_save,c_out=st.columns(2)
        with c_save:
            if st.button("💾 Salvar perfil",key="btn_sp",use_container_width=True):
                st.session_state.users[email]["name"]=new_n; st.session_state.users[email]["area"]=new_a
                st.session_state.users[email]["bio"]=new_b; save_db(); record(area_to_tags(new_a),1.5); st.success("✓ Perfil salvo!"); st.rerun()
        with c_out:
            if st.button("Sair da conta",key="btn_logout",use_container_width=True):
                st.session_state.logged_in=False; st.session_state.current_user=None; st.session_state.page="login"; st.rerun()

    with tab_s:
        st.markdown('<h3>Alterar senha</h3>', unsafe_allow_html=True)
        op=st.text_input("Senha atual",type="password",key="op")
        np_=st.text_input("Nova senha",type="password",key="np_")
        np2=st.text_input("Confirmar",type="password",key="np2")
        if st.button("Alterar senha",key="btn_cpw"):
            if hp(op)!=u.get("password",""): st.error("Senha incorreta.")
            elif np_!=np2: st.error("Senhas não coincidem.")
            elif len(np_)<6: st.error("Senha muito curta.")
            else: st.session_state.users[email]["password"]=hp(np_); save_db(); st.success("✓ Senha alterada!")
        st.markdown("<hr>", unsafe_allow_html=True)
        en=u.get("2fa_enabled",False)
        st.markdown(f'<div class="gc" style="padding:1rem 1.3rem;display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;"><div><div style="font-weight:600;font-size:.90rem;font-family:\'Syne\',sans-serif;">2FA por e-mail</div><div style="font-size:.73rem;color:var(--t3);">{email}</div></div><span style="color:{"var(--ok)" if en else "var(--err)"};font-size:.82rem;font-weight:700;">{"✓ Ativo" if en else "✗ Inativo"}</span></div>', unsafe_allow_html=True)
        if st.button("Desativar 2FA" if en else "Ativar 2FA",key="btn_2fa"):
            st.session_state.users[email]["2fa_enabled"]=not en; save_db(); st.rerun()

    with tab_pr:
        prots=[("AES-256","Criptografia end-to-end"),("SHA-256","Hash seguro de senhas"),("TLS 1.3","Transmissão segura"),("Zero Knowledge","Pesquisas privadas protegidas")]
        items="".join(f'<div style="display:flex;align-items:center;gap:12px;background:rgba(16,185,129,.07);border:1px solid rgba(16,185,129,.18);border-radius:var(--r18);padding:11px;"><div style="width:28px;height:28px;border-radius:8px;background:rgba(16,185,129,.14);display:flex;align-items:center;justify-content:center;color:var(--ok);font-weight:700;font-size:.76rem;flex-shrink:0;">✓</div><div><div style="font-weight:600;color:var(--ok);font-size:.84rem;">{n2}</div><div style="font-size:.71rem;color:var(--t3);">{d2}</div></div></div>' for n2,d2 in prots)
        st.markdown(f'<div class="gc" style="padding:1.2rem;"><div style="font-weight:700;font-family:\'Syne\',sans-serif;margin-bottom:1rem;">Proteções ativas</div><div style="display:grid;gap:9px;">{items}</div></div>', unsafe_allow_html=True)

    with tab_saved:
        st.markdown('<h3>Artigos Salvos</h3>', unsafe_allow_html=True)
        if st.session_state.saved_articles:
            for idx,a in enumerate(st.session_state.saved_articles):
                uid=re.sub(r'[^a-zA-Z0-9]','',f"saved_{a.get('doi','nd')}_{idx}")[:30]
                render_web_article(a, idx=idx+3000, ctx="saved")
                if st.button("🗑️ Remover",key=f"rm_s_{uid}"):
                    st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]
                    save_db(); st.toast("Removido!"); st.rerun()
        else:
            st.markdown('<div class="gc" style="text-align:center;padding:2.5rem;color:var(--t3);">Nenhum artigo salvo. Salve artigos da busca!</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════
def main():
    if not st.session_state.logged_in:
        p=st.session_state.page
        if p=="verify_email": page_verify_email()
        elif p=="2fa": page_2fa()
        else: page_login()
        return
    render_topnav()
    if st.session_state.profile_view:
        page_profile(st.session_state.profile_view); return
    {"feed":page_feed,"search":page_search,"knowledge":page_knowledge,
     "folders":page_folders,"analytics":page_analytics,"img_search":page_img_search,
     "chat":page_chat,"settings":page_settings}.get(st.session_state.page, page_feed)()

main()
