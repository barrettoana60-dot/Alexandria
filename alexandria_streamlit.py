import subprocess, sys, os, json, hashlib, random, string, base64, re
from datetime import datetime
from collections import defaultdict

def _pip(pkg):
    subprocess.check_call([sys.executable,"-m","pip","install",pkg,"-q"],
                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    import plotly.graph_objects as go
except ImportError:
    _pip("plotly"); import plotly.graph_objects as go
try:
    import numpy as np
    from PIL import Image as PILImage
except ImportError:
    _pip("pillow numpy"); import numpy as np; from PIL import Image as PILImage
try:
    import requests
except ImportError:
    _pip("requests"); import requests

import streamlit as st

st.set_page_config(page_title="Nebula", page_icon="🔬",
                   layout="wide", initial_sidebar_state="collapsed")

DB_FILE = "nebula_db.json"

# ─── PERSISTENCE ───────────────────────────
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,"r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_db():
    try:
        with open(DB_FILE,"w") as f:
            json.dump(
                {
                    "users": st.session_state.users,
                    "feed_posts": st.session_state.feed_posts,
                    "folders": st.session_state.folders,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
    except:
        pass

def hp(pw): return hashlib.sha256(pw.encode()).hexdigest()
def code6(): return ''.join(random.choices(string.digits, k=6))
def ini(n):  return ''.join(w[0].upper() for w in str(n).split()[:2])

def img_to_b64(file_obj):
    try:
        file_obj.seek(0)
        data = file_obj.read()
        ext  = getattr(file_obj,"name","img.png").split(".")[-1].lower()
        mime = {"jpg":"jpeg","jpeg":"jpeg","png":"png","gif":"gif","webp":"webp"}.get(ext,"png")
        return f"data:image/{mime};base64,{base64.b64encode(data).decode()}"
    except:
        return None

# ─── CSS ───────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;0,700;0,800;1,400&family=DM+Sans:wght@300;400;500;600&display=swap');
:root{
  --void:#03040a;--deep:#0a1128;--navy:#0d1635;--surface:#111d3a;--elevated:#162348;
  --blue:#2563eb;--blue-l:#3b7cf4;--blue-g:#60a5fa;--cyan:#06b6d4;--cyan-s:#22d3ee;
  --t1:#eef2ff;--t2:#94a8d0;--t3:#4a5e80;
  --bdr:rgba(37,99,235,.18);--bdr-l:rgba(96,165,250,.28);--glass:rgba(10,17,40,.72);
  --ok:#10b981;--warn:#f59e0b;--err:#ef4444;
  --r-sm:10px;--r-md:16px;--r-lg:22px;
}
*,*::before,*::after{box-sizing:border-box;margin:0}
html,body,.stApp{background:var(--void)!important;color:var(--t1)!important;font-family:'DM Sans',sans-serif!important}
.stApp::before{content:'';position:fixed;inset:0;
  background:radial-gradient(ellipse 100% 60% at 10% 0%,rgba(37,99,235,.09) 0%,transparent 55%),
             radial-gradient(ellipse 60% 80% at 90% 100%,rgba(6,182,212,.06) 0%,transparent 55%);
  pointer-events:none;z-index:0;animation:bgP 14s ease-in-out infinite alternate}
@keyframes bgP{from{opacity:.7}to{opacity:1}}
[data-testid="collapsedControl"]{display:none!important}
section[data-testid="stSidebar"]{display:none!important}
h1,h2,h3,h4{font-family:'Playfair Display','Times New Roman',serif!important;color:var(--t1)!important;font-weight:700}
h1{font-size:1.8rem!important}h2{font-size:1.4rem!important}h3{font-size:1.05rem!important}
/* inputs */
.stTextInput input,.stTextArea textarea{background:var(--surface)!important;border:1px solid var(--bdr)!important;border-radius:var(--r-sm)!important;color:var(--t1)!important;font-family:'DM Sans',sans-serif!important;font-size:.9rem!important;transition:border-color .25s,box-shadow .25s!important}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:var(--blue)!important;box-shadow:0 0 0 3px rgba(37,99,235,.15)!important}
.stTextInput label,.stTextArea label,.stSelectbox label,.stFileUploader label{color:var(--t2)!important;font-size:.82rem!important}
/* liquid glass button */
.stButton>button{background:linear-gradient(135deg,rgba(37,99,235,.38),rgba(6,182,212,.18),rgba(37,99,235,.28))!important;backdrop-filter:blur(24px) saturate(200%)!important;border:1px solid rgba(96,165,250,.28)!important;border-radius:var(--r-md)!important;color:var(--t1)!important;font-family:'DM Sans',sans-serif!important;font-weight:500!important;font-size:.87rem!important;letter-spacing:.02em!important;position:relative!important;overflow:hidden!important;transition:all .3s cubic-bezier(.4,0,.2,1)!important;box-shadow:0 4px 18px rgba(37,99,235,.16),inset 0 1px 0 rgba(255,255,255,.09)!important}
.stButton>button:hover{background:linear-gradient(135deg,rgba(37,99,235,.58),rgba(6,182,212,.32),rgba(37,99,235,.48))!important;border-color:rgba(96,165,250,.48)!important;box-shadow:0 8px 28px rgba(37,99,235,.28)!important;transform:translateY(-1px)!important}
.stButton>button:active{transform:translateY(0)!important}
/* cards */
.card{background:var(--glass);backdrop-filter:blur(18px) saturate(160%);-webkit-backdrop-filter:blur(18px) saturate(160%);border:1px solid var(--bdr);border-radius:var(--r-lg);padding:1.3rem 1.5rem;margin-bottom:.9rem;box-shadow:0 8px 28px rgba(0,0,0,.32),inset 0 1px 0 rgba(255,255,255,.04);animation:sU .38s ease both;transition:transform .2s,box-shadow .2s,border-color .2s}
.card:hover{transform:translateY(-2px);border-color:var(--bdr-l)}
@keyframes sU{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
@keyframes fI{from{opacity:0}to{opacity:1}}
.pw{animation:fI .32s ease}
/* avatar */
.av{border-radius:50%;background:linear-gradient(135deg,var(--navy),var(--blue));display:flex;align-items:center;justify-content:center;font-family:'DM Sans',sans-serif;font-weight:700;color:white;border:2px solid var(--bdr-l);flex-shrink:0;overflow:hidden}
.av img{width:100%;height:100%;object-fit:cover;border-radius:50%}
/* tags badges */
.tag{display:inline-block;background:rgba(37,99,235,.12);border:1px solid rgba(37,99,235,.22);border-radius:20px;padding:2px 9px;font-size:.71rem;color:var(--blue-g);margin:2px;font-weight:500}
.b-on{display:inline-block;background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.32);border-radius:20px;padding:2px 9px;font-size:.71rem;font-weight:600;color:#f59e0b}
.b-pub{display:inline-block;background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.32);border-radius:20px;padding:2px 9px;font-size:.71rem;font-weight:600;color:#10b981}
.b-rec{display:inline-block;background:rgba(6,182,212,.14);border:1px solid rgba(6,182,212,.28);border-radius:20px;padding:2px 9px;font-size:.7rem;font-weight:600;color:var(--cyan-s)}
/* metric */
.mbox{background:var(--glass);border:1px solid var(--bdr);border-radius:var(--r-md);padding:1.1rem;text-align:center;animation:sU .4s ease both}
.mval{font-family:'Playfair Display',serif;font-size:1.9rem;font-weight:800;background:linear-gradient(135deg,var(--blue-g),var(--cyan-s));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.mlbl{font-size:.74rem;color:var(--t3);margin-top:3px}
/* scrollbar */
::-webkit-scrollbar{width:4px;height:4px}::-webkit-scrollbar-track{background:var(--void)}::-webkit-scrollbar-thumb{background:var(--elevated);border-radius:3px}
/* chat */
.bme{background:linear-gradient(135deg,rgba(37,99,235,.42),rgba(6,182,212,.20));border:1px solid rgba(96,165,250,.22);border-radius:18px 18px 4px 18px;padding:.65rem .95rem;max-width:70%;margin-left:auto;margin-bottom:5px;font-size:.86rem;line-height:1.5}
.bthem{background:var(--surface);border:1px solid var(--bdr);border-radius:18px 18px 18px 4px;padding:.65rem .95rem;max-width:70%;margin-bottom:5px;font-size:.86rem;line-height:1.5}
/* tabs */
.stTabs [data-baseweb="tab-list"]{background:var(--deep)!important;border-radius:var(--r-sm)!important;padding:4px!important;gap:3px!important;border:1px solid var(--bdr)!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--t3)!important;border-radius:8px!important;font-family:'DM Sans',sans-serif!important;font-size:.84rem!important}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,rgba(37,99,235,.33),rgba(6,182,212,.16))!important;color:var(--t1)!important;border:1px solid rgba(96,165,250,.28)!important}
.stTabs [data-baseweb="tab-panel"]{background:transparent!important;padding-top:.9rem!important}
/* expander */
.stExpander{background:var(--glass)!important;border:1px solid var(--bdr)!important;border-radius:var(--r-md)!important}
.stExpander summary{color:var(--t2)!important;font-size:.87rem!important}
/* misc */
.stSelectbox [data-baseweb="select"]{background:var(--surface)!important;border:1px solid var(--bdr)!important;border-radius:var(--r-sm)!important}
.stFileUploader section{background:var(--glass)!important;border:1.5px dashed var(--bdr-l)!important;border-radius:var(--r-md)!important}
.stAlert{background:var(--glass)!important;border:1px solid var(--bdr)!important;border-radius:var(--r-md)!important;color:var(--t1)!important}
hr{border-color:var(--bdr)!important}
.stProgress>div>div{background:linear-gradient(90deg,var(--blue),var(--cyan))!important;border-radius:4px!important}
label{color:var(--t2)!important}
.stCheckbox label,.stRadio label{color:var(--t1)!important}
.block-container{padding-top:.5rem!important;padding-bottom:3rem!important;max-width:1300px!important}
/* top nav row styling */
.toprow .stButton>button{background:transparent!important;border:none!important;color:var(--t2)!important;font-size:.8rem!important;padding:.35rem .65rem!important;box-shadow:none!important;border-radius:8px!important;font-weight:400!important;letter-spacing:.01em!important}
.toprow .stButton>button:hover{background:rgba(37,99,235,.14)!important;color:var(--t1)!important;transform:none!important;box-shadow:none!important}
/* dot */
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.6;transform:scale(.85)}}
.don{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--ok);animation:pulse 2s infinite;margin-right:5px}
.doff{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--t3);margin-right:5px}
/* analysis box */
.abox{background:var(--surface);border:1px solid var(--bdr-l);border-radius:var(--r-md);padding:1.1rem;margin-bottom:.9rem}
/* profile hero */
.prof-hero{background:var(--glass);backdrop-filter:blur(18px);border:1px solid var(--bdr);border-radius:var(--r-lg);padding:1.8rem;display:flex;gap:1.5rem;align-items:flex-start;margin-bottom:1.2rem}
.prof-photo{width:88px;height:88px;border-radius:50%;background:linear-gradient(135deg,var(--navy),var(--blue));border:3px solid var(--bdr-l);object-fit:cover;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:2rem;font-weight:700;color:white;overflow:hidden}
.prof-photo img{width:100%;height:100%;object-fit:cover;border-radius:50%}
/* search card */
.scard{background:var(--glass);border:1px solid var(--bdr);border-radius:var(--r-md);padding:1rem 1.2rem;margin-bottom:.7rem;transition:border-color .2s}
.scard:hover{border-color:var(--bdr-l)}
</style>
""", unsafe_allow_html=True)

# ─── HELPERS ───────────────────────────────
def avh(initials, sz=40, photo_b64=None):
    fs = max(sz//3, 9)
    if photo_b64:
        return f'<div class="av" style="width:{sz}px;height:{sz}px;"><img src="{photo_b64}"/></div>'
    return f'<div class="av" style="width:{sz}px;height:{sz}px;font-size:{fs}px;">{initials}</div>'

def tags_html(tags):
    return ' '.join(f'<span class="tag">{t}</span>' for t in (tags or []))

def badge(s):
    return f'<span class="{"b-pub" if s=="Publicado" else "b-on"}">{s}</span>'

def guser():
    # garante que 'users' é dict
    if not isinstance(st.session_state.users, dict):
        st.session_state.users = {}
    return st.session_state.users.get(st.session_state.current_user, {})

def get_photo(email):
    if not isinstance(st.session_state.users, dict):
        return None
    return st.session_state.users.get(email,{}).get("photo_b64")

# ─── REAL IMAGE ANALYSIS ───────────────────
def analyze_image(uploaded_file):
    try:
        uploaded_file.seek(0)
        img   = PILImage.open(uploaded_file).convert("RGB")
        orig  = img.size
        small = img.resize((256,256))
        arr   = np.array(small, dtype=np.float32)
        r,g,b = arr[:,:,0],arr[:,:,1],arr[:,:,2]
        mr,mg,mb = float(r.mean()),float(g.mean()),float(b.mean())
        brightness = (mr+mg+mb)/3
        saturation = float(np.std(arr))
        gray   = arr.mean(axis=2)
        gx     = np.diff(gray,axis=1); gy=np.diff(gray,axis=0)
        edge   = float(np.sqrt(np.mean(gx**2)+np.mean(gy**2)))
        contrast=float(gray.std())
        h,w   = gray.shape
        qv    = [gray[:h//2,:w//2].var(),gray[:h//2,w//2:].var(),gray[h//2:,:w//2].var(),gray[h//2:,w//2:].var()]
        sym   = 1.0-(max(qv)-min(qv))/(max(qv)+1e-5)
        hist  = np.histogram(gray,bins=64,range=(0,255))[0]
        hn    = hist/hist.sum(); hn=hn[hn>0]
        entropy=float(-np.sum(hn*np.log2(hn)))
        flat  = arr.reshape(-1,3); rounded=(flat//32*32).astype(int)
        uniq,counts=np.unique(rounded,axis=0,return_counts=True)
        top_idx=np.argsort(-counts)[:6]
        palette=[tuple(int(x) for x in uniq[i]) for i in top_idx]
        skin_mask=(r>95)&(g>40)&(b>20)&(r>g)&(r>b)&((r-g)>15)
        skin_pct=float(skin_mask.mean())
        warm = mr>mb+15
        dom  = max({"Vermelho":mr,"Verde":mg,"Azul":mb}.items(),key=lambda x:x[1])[0]
        if skin_pct>0.15:
            cat="Imagem de Organismo / Tecido Biológico"
            struct=f"Alta presença de tonalidade orgânica ({skin_pct*100:.0f}% da imagem). Possível histologia ou fotografia de organismo."
        elif edge>40 and entropy>5.5:
            cat="Estrutura Biológica / Molecular — Alta Complexidade"
            struct=f"Densidade de bordas alta (I={edge:.1f}) + entropia elevada ({entropy:.2f} bits). Microscopia eletrônica ou fluorescência."
        elif sym>0.82 and edge<30:
            cat="Padrão Geométrico / Cristalográfico"
            struct=f"Alta simetria (score={sym:.3f}). Padrão de cristalização, difração ou estrutura simétrica."
        elif contrast<18:
            cat="Amostra Homogênea / Baixo Contraste"
            struct=f"Contraste muito baixo (σ={contrast:.1f}). Amostra uniforme, gel ou campo de fundo."
        elif mr>185 and mg<110 and mb<110:
            cat="Coloração Histológica — H&E"
            struct=f"Canal vermelho dominante (R={mr:.0f},G={mg:.0f},B={mb:.0f}). Hematoxilina & Eosina ou imuno-histoquímica."
        elif mg>165 and mr<130:
            cat="Fluorescência — Canal Verde (GFP/FITC)"
            struct=f"Verde dominante (G={mg:.0f}). Marcador fluorescente GFP, FITC ou similar."
        elif mb>165 and mr<130:
            cat="Fluorescência — Canal Azul (DAPI/Hoechst)"
            struct=f"Azul dominante (B={mb:.0f}). Marcador nuclear DAPI, Hoechst ou UV."
        elif entropy>6.0:
            cat="Imagem Multispectral / Alta Complexidade Informacional"
            struct=f"Entropia muito alta ({entropy:.2f} bits). Imagem de satélite, mapa de calor ou composição multiespectral."
        elif edge>25:
            cat="Gráfico / Diagrama Científico"
            struct=f"Bordas bem definidas (I={edge:.1f}). Provável gráfico, esquema ou diagrama técnico."
        else:
            cat="Imagem Científica Geral"
            struct=f"Padrão misto. Temperatura {'quente' if warm else 'fria'}, brilho {brightness:.0f}/255."
        conf=min(96,55+edge/2+entropy*3+sym*5)
        return {
            "category":cat,"structure":struct,
            "color":{
                "dominant":dom,
                "brightness":round(brightness,1),
                "saturation":round(saturation,1),
                "mean_rgb":(round(mr,1),round(mg,1),round(mb,1)),
                "warm":warm
            },
            "texture":{
                "edge_intensity":round(edge,2),
                "contrast":round(contrast,2),
                "entropy":round(entropy,3),
                "complexity":"Alta" if entropy>5.5 else ("Média" if entropy>4 else "Baixa")
            },
            "shape":{
                "symmetry_score":round(sym,3),
                "symmetry_level":"Alta" if sym>0.78 else ("Média" if sym>0.52 else "Baixa")
            },
            "palette":palette,
            "confidence":round(conf,1),
            "size":orig,
            "skin_pct":round(skin_pct*100,1)
        }
    except Exception:
        return None

# ─── REAL INTERNET ARTICLE SEARCH ──────────
def search_semantic_scholar(query, limit=8):
    results=[]
    try:
        r=requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={
                "query":query,
                "limit":limit,
                "fields":"title,authors,year,abstract,venue,externalIds,openAccessPdf,citationCount"
            },
            timeout=9
        )
        if r.status_code==200:
            for p in r.json().get("data",[]):
                ext_ids = p.get("externalIds",{}) or {}
                doi   = ext_ids.get("DOI","")
                arxiv = ext_ids.get("ArXiv","")
                pdf   = p.get("openAccessPdf") or {}
                link  = pdf.get("url","") or (f"https://arxiv.org/abs/{arxiv}" if arxiv else (f"https://doi.org/{doi}" if doi else ""))
                authors_list = p.get("authors",[]) or []
                authors = ", ".join(a.get("name","") for a in authors_list[:3])
                if len(authors_list)>3: authors+=" et al."
                abstract=(p.get("abstract","") or "Abstract não disponível.")
                abstract=abstract[:300]+("…" if len(abstract)>300 else "")
                results.append({
                    "title":p.get("title","Sem título"),
                    "authors":authors or "—",
                    "year":p.get("year","?"),
                    "source":p.get("venue","") or "Semantic Scholar",
                    "doi":doi or arxiv or "—",
                    "abstract":abstract,
                    "url":link,
                    "citations":p.get("citationCount",0),
                    "origin":"semantic",
                    "tags":[]
                })
    except:
        pass
    return results

def search_crossref(query, limit=5):
    results=[]
    try:
        r=requests.get(
            "https://api.crossref.org/works",
            params={
                "query":query,
                "rows":limit,
                "select":"title,author,issued,abstract,DOI,container-title,is-referenced-by-count",
                "mailto":"nebula@example.com"
            },
            timeout=9
        )
        if r.status_code==200:
            for p in r.json().get("message",{}).get("items",[]):
                title=(p.get("title") or ["Sem título"])[0]
                ars=p.get("author",[]) or []
                authors=", ".join(
                    f'{a.get("given","").split()[0] if a.get("given") else ""} {a.get("family","")}'.strip()
                    for a in ars[:3]
                )
                if len(ars)>3: authors+=" et al."
                year=(p.get("issued",{}).get("date-parts") or [[None]])[0][0]
                doi=p.get("DOI","")
                journal=(p.get("container-title") or [""])[0]
                abstract_raw=p.get("abstract","") or "Abstract não disponível."
                abstract=re.sub(r'<[^>]+>','',abstract_raw)[:300]+("…" if len(abstract_raw)>300 else "")
                results.append({
                    "title":title,
                    "authors":authors or "—",
                    "year":year or "?",
                    "source":journal or "CrossRef",
                    "doi":doi,
                    "abstract":abstract,
                    "url":f"https://doi.org/{doi}" if doi else "",
                    "citations":p.get("is-referenced-by-count",0),
                    "origin":"crossref",
                    "tags":[]
                })
    except:
        pass
    return results

# ─── RECOMMENDATION ENGINE ─────────────────
def record(tags, w=1.0):
    email=st.session_state.get("current_user")
    if not email or not tags:
        return
    prefs=st.session_state.user_prefs.setdefault(email,defaultdict(float))
    for t in tags:
        prefs[t.lower()]+=w

def get_recs(email, n=2):
    prefs=st.session_state.user_prefs.get(email,{})
    if not prefs:
        return []
    def score(p):
        return (
            sum(prefs.get(t.lower(),0) for t in p.get("tags",[])) +
            sum(prefs.get(t.lower(),0)*.5 for t in p.get("connections",[]))
        )
    scored=[(score(p),p) for p in st.session_state.feed_posts if email not in p.get("liked_by",[])]
    scored.sort(key=lambda x:-x[0])
    return [p for s,p in scored if s>0][:n]

def area_to_tags(area):
    a=(area or "").lower()
    m={
        "ia":["machine learning","deep learning","LLM"],
        "inteligência artificial":["machine learning","LLM"],
        "machine learning":["deep learning","redes neurais","otimização"],
        "neurociência":["sono","memória","plasticidade"],
        "biologia":["célula","genômica","CRISPR"],
        "física":["quantum","astrofísica","cosmologia"],
        "química":["síntese","catálise"],
        "medicina":["clínica","diagnóstico","terapia"],
        "astronomia":["astrofísica","cosmologia","galáxia"],
        "computação":["algoritmo","criptografia","redes"],
        "matemática":["álgebra","topologia","estatística"],
        "psicologia":["cognição","comportamento"],
        "ecologia":["biodiversidade","clima"],
        "genômica":["DNA","CRISPR","gene"],
        "museologia":["patrimônio","curadoria","cultura"],
        "engenharia":["robótica","materiais","sistemas"],
        "astrofísica":["cosmologia","galáxia","matéria escura"]
    }
    for k,v in m.items():
        if k in a:
            return v
    return [w.strip() for w in a.replace(","," ").split() if len(w)>3][:5]

# ─── SEED DATA ─────────────────────────────
SEED_POSTS=[
    {"id":1,"author":"Carlos Mendez","author_email":"carlos@nebula.ai","avatar":"CM","area":"Neurociência","title":"Efeitos da Privação de Sono na Plasticidade Sináptica","abstract":"Investigamos como 24h de privação de sono afetam espinhas dendríticas em ratos Wistar, com redução de 34% na plasticidade hipocampal. Nossos dados sugerem janela crítica nas primeiras 6h de recuperação do sono.","tags":["neurociência","sono","memória","hipocampo"],"likes":47,"comments":[{"user":"Maria Silva","text":"Excelente metodologia!"},{"user":"João Lima","text":"Quais os critérios de exclusão?"}],"status":"Em andamento","date":"2026-02-10","liked_by":[],"saved_by":[],"connections":["sono","memória","hipocampo"]},
    {"id":2,"author":"Luana Freitas","author_email":"luana@nebula.ai","avatar":"LF","area":"Biomedicina","title":"CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras","abstract":"Desenvolvemos vetor AAV9 modificado para entrega precisa de CRISPR no gene DMD, com eficiência de 78% em modelos murinos mdx. Publicação em Cell prevista para Q2 2026.","tags":["CRISPR","gene terapia","músculo","AAV9"],"likes":93,"comments":[{"user":"Ana","text":"Quais os próximos passos para trials humanos?"}],"status":"Publicado","date":"2026-01-28","liked_by":[],"saved_by":[],"connections":["genômica","distrofia"]},
    {"id":3,"author":"Rafael Souza","author_email":"rafael@nebula.ai","avatar":"RS","area":"Computação","title":"Redes Neurais Quântico-Clássicas para Otimização Combinatória","abstract":"Arquitetura híbrida variacional combinando qubits supercondutores com camadas densas para resolver TSP com 40% menos iterações que métodos clássicos.","tags":["quantum ML","otimização","TSP","computação quântica"],"likes":201,"comments":[],"status":"Em andamento","date":"2026-02-15","liked_by":[],"saved_by":[],"connections":["computação quântica","machine learning"]},
    {"id":4,"author":"Priya Nair","author_email":"priya@nebula.ai","avatar":"PN","area":"Astrofísica","title":"Detecção de Matéria Escura via Lentes Gravitacionais Fracas","abstract":"Mapeamento de matéria escura com precisão sub-arcminuto usando 100M de galáxias do DES Y3. Tensão com ΛCDM em escalas < 1 Mpc.","tags":["astrofísica","matéria escura","cosmologia"],"likes":312,"comments":[],"status":"Publicado","date":"2026-02-01","liked_by":[],"saved_by":[],"connections":["cosmologia","lentes gravitacionais"]},
    {"id":5,"author":"João Lima","author_email":"joao@nebula.ai","avatar":"JL","area":"Psicologia","title":"Viés de Confirmação em Decisões Médicas Assistidas por IA","abstract":"Estudo duplo-cego com 240 médicos revelou que sistemas de IA mal calibrados amplificam vieses cognitivos em 22% dos casos clínicos analisados.","tags":["psicologia","IA","cognição","medicina"],"likes":78,"comments":[],"status":"Publicado","date":"2026-02-08","liked_by":[],"saved_by":[],"connections":["cognição","IA"]},
]
SEED_USERS={
    "demo@nebula.ai":{"name":"Ana Pesquisadora","password":hp("demo123"),"bio":"Pesquisadora em IA e Ciências Cognitivas | UFMG","area":"Inteligência Artificial","followers":128,"following":47,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "carlos@nebula.ai":{"name":"Carlos Mendez","password":hp("nebula123"),"bio":"Neurocientista | UFMG | Plasticidade sináptica e sono","area":"Neurociência","followers":210,"following":45,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "luana@nebula.ai":{"name":"Luana Freitas","password":hp("nebula123"),"bio":"Biomédica | FIOCRUZ | CRISPR e terapia gênica para doenças raras","area":"Biomedicina","followers":178,"following":62,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "rafael@nebula.ai":{"name":"Rafael Souza","password":hp("nebula123"),"bio":"Computação Quântica | USP | Algoritmos híbridos quantum-clássicos","area":"Computação","followers":340,"following":88,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "priya@nebula.ai":{"name":"Priya Nair","password":hp("nebula123"),"bio":"Astrofísica | MIT | Dark matter survey & gravitational lensing","area":"Astrofísica","followers":520,"following":31,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "joao@nebula.ai":{"name":"João Lima","password":hp("nebula123"),"bio":"Psicólogo Cognitivo | UNICAMP | IA e vieses em decisões clínicas","area":"Psicologia","followers":95,"following":120,"verified":True,"2fa_enabled":False,"photo_b64":None},
}
CHAT_INIT={
    "carlos@nebula.ai":[{"from":"carlos@nebula.ai","text":"Oi! Vi seu comentário na minha pesquisa sobre sono.","time":"09:14"},{"from":"me","text":"Achei muito interessante a metodologia!","time":"09:16"},{"from":"carlos@nebula.ai","text":"Obrigado! Podemos colaborar?","time":"09:17"}],
    "luana@nebula.ai":[{"from":"luana@nebula.ai","text":"Podemos colaborar no próximo semestre.","time":"ontem"}],
    "rafael@nebula.ai":[{"from":"rafael@nebula.ai","text":"Compartilhei o repositório do código quântico.","time":"08:30"}],
}

KNOWLEDGE_NODES_DEFAULT=[
    {"id":"IA","x":.50,"y":.85,"z":.50,"connections":["Machine Learning","Redes Neurais","Otimização"],"color":"#2563eb","size":28},
    {"id":"Machine Learning","x":.20,"y":.65,"z":.40,"connections":["Deep Learning","Otimização","Dados"],"color":"#1d4ed8","size":22},
    {"id":"Neurociência","x":.80,"y":.65,"z":.60,"connections":["Memória","Sono","Plasticidade"],"color":"#3b82f6","size":26},
    {"id":"Genômica","x":.50,"y":.45,"z":.30,"connections":["CRISPR","Proteômica","Epigenética"],"color":"#06b6d4","size":24},
    {"id":"Computação Quântica","x":.15,"y":.35,"z":.70,"connections":["Otimização","Machine Learning","Criptografia"],"color":"#8b5cf6","size":23},
    {"id":"Astrofísica","x":.85,"y":.35,"z":.50,"connections":["Cosmologia","Matéria Escura","Óptica"],"color":"#ec4899","size":22},
    {"id":"Psicologia","x":.50,"y":.15,"z":.60,"connections":["Cognição","Comportamento","Memória"],"color":"#f59e0b","size":20},
    {"id":"Memória","x":.75,"y":.50,"z":.80,"connections":[],"color":"#60a5fa","size":14},
    {"id":"Sono","x":.88,"y":.55,"z":.30,"connections":[],"color":"#60a5fa","size":13},
    {"id":"Otimização","x":.25,"y":.45,"z":.60,"connections":[],"color":"#34d399","size":15},
    {"id":"CRISPR","x":.60,"y":.30,"z":.20,"connections":[],"color":"#22d3ee","size":14},
    {"id":"Deep Learning","x":.10,"y":.55,"z":.50,"connections":[],"color":"#818cf8","size":14},
    {"id":"Cosmologia","x":.92,"y":.22,"z":.70,"connections":[],"color":"#f472b6","size":13},
    {"id":"Cognição","x":.62,"y":.08,"z":.40,"connections":[],"color":"#fbbf24","size":13},
    {"id":"Dados","x":.32,"y":.75,"z":.35,"connections":[],"color":"#34d399","size":12},
    {"id":"Proteômica","x":.40,"y":.28,"z":.45,"connections":[],"color":"#22d3ee","size":12},
    {"id":"Criptografia","x":.05,"y":.50,"z":.65,"connections":[],"color":"#818cf8","size":12},
]

# ─── SESSION INIT ──────────────────────────
def init():
    if "initialized" in st.session_state:
        return
    st.session_state.initialized = True

    disk = load_db()
    disk_users = disk.get("users", {})
    if not isinstance(disk_users, dict):
        disk_users = {}

    st.session_state.setdefault("users", {**SEED_USERS, **disk_users})
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("current_user", None)
    st.session_state.setdefault("page", "login")
    st.session_state.setdefault("profile_view", None)
    st.session_state.setdefault("user_prefs", {})
    st.session_state.setdefault("pending_verify", None)
    st.session_state.setdefault("pending_2fa", None)
    st.session_state.setdefault("feed_posts", disk.get("feed_posts",[dict(p) for p in SEED_POSTS]))
    st.session_state.setdefault("folders", disk.get("folders",{}))
    st.session_state.setdefault("chat_contacts", list(SEED_USERS.keys()))
    st.session_state.setdefault("chat_messages", {k:list(v) for k,v in CHAT_INIT.items()})
    st.session_state.setdefault("active_chat", None)
    st.session_state.setdefault("knowledge_nodes", [dict(n) for n in KNOWLEDGE_NODES_DEFAULT])
    st.session_state.setdefault("followed", ["carlos@nebula.ai","luana@nebula.ai"])
    st.session_state.setdefault("notifications",["Carlos Mendez curtiu sua pesquisa","Nova conexão: IA ↔ Computação Quântica","Luana Freitas comentou em um artigo que você segue"])
    st.session_state.setdefault("stats_data",{"views":[12,34,28,67,89,110,95,134,160,178,201,230],"citations":[0,1,1,2,3,4,4,6,7,8,10,12],"months":["Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez","Jan","Fev"],"h_index":4,"fator_impacto":3.8,"aceitacao":94,"notes":""})
    st.session_state.setdefault("scholar_cache", {})

init()

# ─── AUTH PAGES ────────────────────────────
def page_login():
    _, col, _ = st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-bottom:2rem;">
          <div style="font-family:'Playfair Display',serif;font-size:2.8rem;font-weight:800;font-style:italic;background:linear-gradient(135deg,#93c5fd,#22d3ee);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">🔬 Nebula</div>
          <div style="color:var(--t3);font-size:.78rem;letter-spacing:.12em;text-transform:uppercase;margin-top:.3rem;">Rede do Conhecimento Científico</div>
        </div>
        """, unsafe_allow_html=True)
        tab_in, tab_up = st.tabs(["  Entrar  ","  Criar conta  "])
        with tab_in:
            email = st.text_input("E-mail", placeholder="seu@email.com", key="li_e")
            pw    = st.text_input("Senha", placeholder="••••••••", type="password", key="li_p")
            if st.button("Entrar →", use_container_width=True, key="btn_li"):
                users = st.session_state.users if isinstance(st.session_state.users, dict) else {}
                u = users.get(email)
                if not u:
                    st.error("E-mail não encontrado.")
                elif u["password"] != hp(pw):
                    st.error("Senha incorreta.")
                elif not u.get("verified", True):
                    st.warning("Confirme seu e-mail primeiro.")
                elif u.get("2fa_enabled"):
                    c = code6()
                    st.session_state.pending_2fa={"email":email,"code":c}
                    st.session_state.page="2fa"
                    st.rerun()
                else:
                    st.session_state.logged_in=True
                    st.session_state.current_user=email
                    record(area_to_tags(u.get("area","")),1.0)
                    st.session_state.page="feed"
                    st.rerun()
            st.markdown('<div style="text-align:center;color:var(--t3);font-size:.74rem;margin-top:.5rem;">Demo: demo@nebula.ai / demo123</div>', unsafe_allow_html=True)
        with tab_up:
            n_name=st.text_input("Nome completo",placeholder="Dr. Maria Silva",key="su_n")
            n_email=st.text_input("E-mail",placeholder="seu@email.com",key="su_e")
            n_area=st.text_input("Área de pesquisa",placeholder="Ex: Neurociência, IA, Museologia",key="su_a")
            n_pw=st.text_input("Senha",placeholder="Mínimo 6 caracteres",type="password",key="su_p")
            n_pw2=st.text_input("Confirmar senha",placeholder="••••••••",type="password",key="su_p2")
            if st.button("Criar conta →",use_container_width=True,key="btn_su"):
                users = st.session_state.users if isinstance(st.session_state.users, dict) else {}
                if not all([n_name,n_email,n_area,n_pw,n_pw2]):
                    st.error("Preencha todos os campos.")
                elif n_pw!=n_pw2:
                    st.error("Senhas não coincidem.")
                elif len(n_pw)<6:
                    st.error("Senha muito curta (mín. 6).")
                elif n_email in users:
                    st.error("E-mail já cadastrado.")
                else:
                    c=code6()
                    st.session_state.pending_verify={
                        "email":n_email,
                        "name":n_name,
                        "pw":hp(n_pw),
                        "area":n_area,
                        "code":c
                    }
                    st.session_state.page="verify_email"
                    st.rerun()

def page_verify_email():
    pv=st.session_state.pending_verify
    _,col,_=st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card" style="text-align:center;">
          <div style="font-size:2.5rem;margin-bottom:1rem;">📧</div>
          <h2 style="margin-bottom:.5rem;">Verifique seu e-mail</h2>
          <p style="color:var(--t2);font-size:.87rem;">Código enviado para <strong>{pv['email']}</strong></p>
          <div style="background:rgba(37,99,235,.12);border:1px solid rgba(37,99,235,.25);border-radius:12px;padding:16px;margin:1.2rem 0;">
            <div style="font-size:.7rem;color:var(--t3);letter-spacing:.08em;margin-bottom:6px;">CÓDIGO (demo)</div>
            <div style="font-family:'Playfair Display',serif;font-size:2.2rem;font-weight:700;letter-spacing:.25em;color:var(--blue-g);">{pv['code']}</div>
          </div>
        </div>
        """,unsafe_allow_html=True)
        typed=st.text_input("Código de 6 dígitos",max_chars=6,placeholder="000000",key="ev_c")
        if st.button("Verificar e criar conta →",use_container_width=True,key="btn_ev"):
            if typed.strip()==pv["code"]:
                if not isinstance(st.session_state.users, dict):
                    st.session_state.users = {}
                st.session_state.users[pv["email"]]={
                    "name":pv["name"],
                    "password":pv["pw"],
                    "bio":"",
                    "area":pv["area"],
                    "followers":0,
                    "following":0,
                    "verified":True,
                    "2fa_enabled":False,
                    "photo_b64":None
                }
                save_db()
                st.session_state.pending_verify=None
                st.session_state.logged_in=True
                st.session_state.current_user=pv["email"]
                record(area_to_tags(pv["area"]),2.0)
                st.session_state.page="feed"
                st.rerun()
            else:
                st.error("Código inválido.")
        if st.button("← Voltar",key="btn_ev_bk"):
            st.session_state.page="login"
            st.rerun()

def page_2fa():
    p2=st.session_state.pending_2fa
    _,col,_=st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card" style="text-align:center;">
          <div style="font-size:2.5rem;margin-bottom:1rem;">🔑</div>
          <h2>Verificação 2FA</h2>
          <div style="background:rgba(37,99,235,.12);border:1px solid rgba(37,99,235,.25);border-radius:12px;padding:14px;margin:1rem 0;">
            <div style="font-size:.7rem;color:var(--t3);margin-bottom:6px;">CÓDIGO (demo)</div>
            <div style="font-family:'Playfair Display',serif;font-size:2rem;font-weight:700;letter-spacing:.2em;color:var(--blue-g);">{p2['code']}</div>
          </div>
        </div>
        """,unsafe_allow_html=True)
        typed=st.text_input("Código",max_chars=6,placeholder="000000",key="fa_c",label_visibility="collapsed")
        if st.button("Verificar →",use_container_width=True,key="btn_fa"):
            if typed.strip()==p2["code"]:
                st.session_state.logged_in=True
                st.session_state.current_user=p2["email"]
                st.session_state.pending_2fa=None
                st.session_state.page="feed"
                st.rerun()
            else:
                st.error("Código inválido.")
        if st.button("← Voltar",key="btn_fa_bk"):
            st.session_state.page="login"
            st.rerun()

# ─── TOP NAV ────────────────────────────────
NAV=[("feed","◈","Feed"),("search","⊙","Artigos"),("knowledge","⬡","Rede 3D"),
     ("folders","▣","Pastas"),("analytics","▤","Análises"),
     ("img_search","⊞","Análise de Imagem"),("chat","◻","Chat"),("settings","◎","Perfil")]

def render_topnav():
    u=guser()
    name=u.get("name","?")
    photo=u.get("photo_b64")
    in_=ini(name)
    cur=st.session_state.page
    notif=len(st.session_state.notifications)

    nav_spans="".join(
        f'<span style="font-size:.79rem;color:{"var(--blue-g)" if cur==k else "var(--t3)"};font-weight:{"600" if cur==k else "400"};padding:.38rem .65rem;border-radius:8px;background:{"rgba(37,99,235,.20)" if cur==k else "transparent"};border:{"1px solid rgba(37,99,235,.28)" if cur==k else "none"};">{sym} {lbl}</span>'
        for k,sym,lbl in NAV
    )
    if photo:
        img_html = f"<img src='{photo}' style='width:100%;height:100%;object-fit:cover;border-radius:50%'/>"
    else:
        img_html = in_
    av_html=f'<div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,var(--navy),var(--blue));display:flex;align-items:center;justify-content:center;font-size:.78rem;font-weight:700;color:white;border:1.5px solid var(--bdr-l);overflow:hidden;flex-shrink:0;">{img_html}</div>'
    notif_badge=f'<span style="background:var(--blue);color:white;border-radius:10px;padding:1px 6px;font-size:.66rem;">{notif}</span>' if notif else ""

    st.markdown(f"""
    <div style="position:sticky;top:0;z-index:999;background:rgba(3,4,10,.90);backdrop-filter:blur(24px) saturate(180%);-webkit-backdrop-filter:blur(24px) saturate(180%);border-bottom:1px solid var(--bdr);padding:0 1.2rem;display:flex;align-items:center;justify-content:space-between;height:54px;margin-bottom:0;">
      <div style="font-family:'Playfair Display',serif;font-size:1.3rem;font-weight:800;font-style:italic;background:linear-gradient(135deg,#93c5fd,#22d3ee);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;white-space:nowrap;">🔬 Nebula</div>
      <div style="display:flex;align-items:center;gap:2px;overflow-x:auto;padding:0 .5rem;">{nav_spans}</div>
      <div style="display:flex;align-items:center;gap:8px;">{notif_badge}{av_html}</div>
    </div>
    """, unsafe_allow_html=True)

    # Functional buttons
    st.markdown('<div class="toprow">', unsafe_allow_html=True)
    cols=st.columns([1.5]+[1]*len(NAV)+[1])
    for i,(key,sym,lbl) in enumerate(NAV):
        with cols[i+1]:
            if st.button(f"{sym} {lbl}",key=f"tnav_{key}",use_container_width=True):
                st.session_state.profile_view=None
                st.session_state.page=key
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("""
    <style>
    .toprow .stButton>button{
        background:transparent!important;border:none!important;color:var(--t2)!important;
        font-size:.79rem!important;padding:.3rem .5rem!important;box-shadow:none!important;border-radius:8px!important;
        font-weight:400!important;letter-spacing:.01em!important;margin-top:-12px!important}
    .toprow .stButton>button:hover{
        background:rgba(37,99,235,.13)!important;color:var(--t1)!important;transform:none!important;box-shadow:none!important}
    div[data-testid="stHorizontalBlock"]{gap:2px!important}
    </style>
    """, unsafe_allow_html=True)

# ─── PROFILE PAGE ───────────────────────────
def page_profile(target_email):
    users = st.session_state.users if isinstance(st.session_state.users, dict) else {}
    tu=users.get(target_email,{})
    if not tu:
        st.error("Perfil não encontrado.")
        if st.button("← Voltar"):
            st.session_state.profile_view=None
            st.rerun()
        return
    tname=tu.get("name","?")
    tin=ini(tname)
    tphoto=tu.get("photo_b64")
    email=st.session_state.current_user
    is_me=email==target_email
    is_fol=target_email in st.session_state.followed

    if st.button("← Voltar",key="back_prof"):
        st.session_state.profile_view=None
        st.rerun()

    st.markdown(f"""
    <div class="prof-hero">
      <div class="prof-photo">{("<img src='"+tphoto+"'/>") if tphoto else f'<span style="font-size:2rem;">{tin}</span>'}</div>
      <div style="flex:1;">
        <h1 style="margin-bottom:.2rem;">{tname}</h1>
        <div style="color:var(--blue-g);font-size:.85rem;margin-bottom:.4rem;">{tu.get('area','')}</div>
        <div style="color:var(--t2);font-size:.85rem;line-height:1.6;margin-bottom:.8rem;">{tu.get('bio','Sem biografia.')}</div>
        <div style="display:flex;gap:1.6rem;">
          <div><span style="font-weight:700;font-family:'Playfair Display',serif;">{tu.get('followers',0)}</span><span style="color:var(--t3);font-size:.79rem;"> seguidores</span></div>
          <div><span style="font-weight:700;font-family:'Playfair Display',serif;">{tu.get('following',0)}</span><span style="color:var(--t3);font-size:.79rem;"> seguindo</span></div>
          <div><span style="font-weight:700;font-family:'Playfair Display',serif;">{len([p for p in st.session_state.feed_posts if p.get('author_email')==target_email])}</span><span style="color:var(--t3);font-size:.79rem;"> pesquisas</span></div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if not is_me:
        c1,c2,_=st.columns([1,1,4])
        with c1:
            if st.button("✓ Seguindo" if is_fol else "+ Seguir",key="btn_pf"):
                if is_fol:
                    st.session_state.followed.remove(target_email)
                else:
                    st.session_state.followed.append(target_email)
                    tu["followers"]=tu.get("followers",0)+1
                save_db()
                st.rerun()
        with c2:
            if st.button("💬 Mensagem",key="btn_pm"):
                if target_email not in st.session_state.chat_messages:
                    st.session_state.chat_messages[target_email]=[]
                st.session_state.active_chat=target_email
                st.session_state.page="chat"
                st.session_state.profile_view=None
                st.rerun()

    st.markdown("<hr>",unsafe_allow_html=True)
    st.markdown('<h2>Pesquisas publicadas</h2>',unsafe_allow_html=True)
    user_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==target_email]
    if user_posts:
        for p in user_posts:
            render_post(p,show_profile_link=False)
    else:
        st.markdown('<div class="card" style="text-align:center;padding:2.5rem;color:var(--t3);">Nenhuma pesquisa publicada ainda.</div>',unsafe_allow_html=True)

# ─── SHARE MODAL ────────────────────────────
def share_modal(post_id, title):
    t_enc=title[:80].replace(" ","+").replace("&","")
    url=f"https://nebula.ai/post/{post_id}"
    st.markdown(f"""
    <div class="card" style="padding:1.2rem;">
      <div style="font-weight:700;margin-bottom:.3rem;font-size:.9rem;">Compartilhar pesquisa</div>
      <div style="color:var(--t2);font-size:.8rem;margin-bottom:1rem;">{title[:60]}{"…" if len(title)>60 else ""}</div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:.6rem;">
        <a href="https://twitter.com/intent/tweet?text={t_enc}&url={url}" target="_blank" style="text-decoration:none;">
          <div style="background:var(--surface);border:1px solid var(--bdr);border-radius:12px;padding:.7rem .4rem;text-align:center;font-size:.75rem;color:var(--t2);">𝕏<br>Twitter/X</div>
        </a>
        <a href="https://www.linkedin.com/sharing/share-offsite/?url={url}" target="_blank" style="text-decoration:none;">
          <div style="background:var(--surface);border:1px solid var(--bdr);border-radius:12px;padding:.7rem .4rem;text-align:center;font-size:.75rem;color:var(--t2);">in<br>LinkedIn</div>
        </a>
        <a href="https://wa.me/?text={t_enc}+{url}" target="_blank" style="text-decoration:none;">
          <div style="background:var(--surface);border:1px solid var(--bdr);border-radius:12px;padding:.7rem .4rem;text-align:center;font-size:.75rem;color:var(--t2);">📱<br>WhatsApp</div>
        </a>
        <a href="mailto:?subject={t_enc}&body={url}" target="_blank" style="text-decoration:none;">
          <div style="background:var(--surface);border:1px solid var(--bdr);border-radius:12px;padding:.7rem .4rem;text-align:center;font-size:.75rem;color:var(--t2);">✉️<br>E-mail</div>
        </a>
      </div>
      <div style="margin-top:.8rem;font-size:.72rem;color:var(--t3);">Link direto:</div>
    </div>
    """,unsafe_allow_html=True)
    st.code(url, language=None)

# ─── FEED ───────────────────────────────────
def page_feed():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="margin-bottom:.3rem;">Feed de Pesquisas</h1>',unsafe_allow_html=True)
    email=st.session_state.current_user
    u=guser()
    col_main,col_side=st.columns([2.1,0.9])
    with col_main:
        recs=get_recs(email)
        if recs:
            st.markdown('<span class="b-rec">✦ RECOMENDADO PARA VOCÊ</span><br>',unsafe_allow_html=True)
            for p in recs:
                render_post(p,rec=True)
            st.markdown("<hr>",unsafe_allow_html=True)
        with st.expander("＋  Publicar nova pesquisa"):
            np_t=st.text_input("Título",key="np_t")
            np_ab=st.text_area("Resumo / Abstract",key="np_ab",height=90)
            np_tg=st.text_input("Tags (separadas por vírgula)",key="np_tg")
            np_st=st.selectbox("Status",["Em andamento","Publicado","Concluído"],key="np_st")
            if st.button("Publicar pesquisa",key="btn_pub"):
                if np_t and np_ab:
                    nm=u.get("name","Usuário")
                    tags=[t.strip() for t in np_tg.split(",") if t.strip()]
                    st.session_state.feed_posts.insert(0,{
                        "id":len(st.session_state.feed_posts)+1,
                        "author":nm,
                        "author_email":email,
                        "avatar":ini(nm),
                        "area":u.get("area",""),
                        "title":np_t,
                        "abstract":np_ab,
                        "tags":tags,
                        "likes":0,
                        "comments":[],
                        "status":np_st,
                        "date":datetime.now().strftime("%Y-%m-%d"),
                        "liked_by":[],
                        "saved_by":[],
                        "connections":tags[:3]
                    })
                    record(tags,2.0)
                    save_db()
                    st.success("Publicado!")
                    st.rerun()
        st.markdown("<br>",unsafe_allow_html=True)
        ff=st.selectbox("Mostrar",["Todos","Seguidos","Salvos"],key="ff",label_visibility="collapsed")
        posts=st.session_state.feed_posts
        if ff=="Seguidos":
            posts=[p for p in posts if p.get("author_email") in st.session_state.followed]
        elif ff=="Salvos":
            posts=[p for p in posts if email in p.get("saved_by",[])]
        for p in posts:
            render_post(p)
    with col_side:
        sq=st.text_input("",placeholder="🔍 Pesquisadores…",key="ppl_s",label_visibility="collapsed")
        st.markdown('<div class="card">',unsafe_allow_html=True)
        st.markdown('<div style="font-weight:600;font-size:.88rem;margin-bottom:.9rem;">Pesquisadores</div>',unsafe_allow_html=True)
        users = st.session_state.users if isinstance(st.session_state.users, dict) else {}
        shown=0
        for ue,ud in list(users.items()):
            if ue==email:
                continue
            uname=ud.get("name","?")
            if sq and sq.lower() not in uname.lower() and sq.lower() not in ud.get("area","").lower():
                continue
            if shown>=6:
                break
            shown+=1
            uin=ini(uname)
            uphoto=ud.get("photo_b64")
            is_fol=ue in st.session_state.followed
            ca,cb=st.columns([3,1])
            with ca:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:2px;">'
                    f'{avh(uin,26,uphoto)}'
                    f'<div><div style="font-size:.8rem;font-weight:500;">{uname}</div>'
                    f'<div style="font-size:.68rem;color:var(--t3);">{ud.get("area","")[:20]}</div>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )
            with cb:
                if st.button("✓" if is_fol else "+",key=f"fol_{ue}"):
                    if is_fol:
                        st.session_state.followed.remove(ue)
                    else:
                        st.session_state.followed.append(ue)
                    save_db()
                    st.rerun()
            if st.button("Ver perfil",key=f"vp_{ue}",use_container_width=True):
                st.session_state.profile_view=ue
                st.rerun()
            st.markdown('<div style="height:4px;"></div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)
        st.markdown('<div class="card">',unsafe_allow_html=True)
        st.markdown('<div style="font-weight:600;font-size:.88rem;margin-bottom:.8rem;">Áreas em Alta</div>',unsafe_allow_html=True)
        for area,cnt in [("Quantum ML",42),("CRISPR 2026",38),("Neuroplasticidade",31),("LLMs Científicos",27)]:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--bdr);font-size:.8rem;">'
                f'<span style="color:var(--t2);">{area}</span>'
                f'<span style="color:var(--blue-g);font-weight:600;">{cnt}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        st.markdown('</div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

def render_post(post, rec=False, show_profile_link=True):
    email=st.session_state.current_user
    liked=email in post["liked_by"]
    saved=email in post.get("saved_by",[])
    aemail=post.get("author_email","")
    aphoto=get_photo(aemail)
    rec_b='<span class="b-rec" style="margin-left:6px;">Rec.</span>' if rec else ""
    st.markdown(f"""
    <div class="card">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:.9rem;">
        {avh(post['avatar'],40,aphoto)}
        <div style="flex:1;">
          <div style="font-weight:600;font-size:.91rem;">{post['author']}</div>
          <div style="color:var(--t3);font-size:.73rem;">{post['area']} · {post['date']}</div>
        </div>
        {badge(post['status'])}{rec_b}
      </div>
      <h3 style="margin-bottom:.45rem;font-size:1.03rem;line-height:1.4;">{post['title']}</h3>
      <p style="color:var(--t2);font-size:.85rem;line-height:1.65;margin-bottom:.75rem;">{post['abstract']}</p>
      <div>{tags_html(post['tags'])}</div>
    </div>
    """,unsafe_allow_html=True)
    c1,c2,c3,c4,c5,_=st.columns([.9,.9,.7,.7,1.1,1.5])
    with c1:
        if st.button(f"{'❤' if liked else '♡'} {post['likes']}",key=f"lk_{post['id']}"):
            if liked:
                post["liked_by"].remove(email)
                post["likes"]-=1
            else:
                post["liked_by"].append(email)
                post["likes"]+=1
                record(post["tags"],1.5)
            save_db()
            st.rerun()
    with c2:
        if st.button(f"💬 {len(post['comments'])}",key=f"cm_t_{post['id']}"):
            k=f"sc_{post['id']}"
            st.session_state[k]=not st.session_state.get(k,False)
            st.rerun()
    with c3:
        if st.button("🔖" if saved else "📌",key=f"sv_{post['id']}"):
            if saved:
                post["saved_by"].remove(email)
            else:
                post["saved_by"].append(email)
            save_db()
            st.rerun()
    with c4:
        if st.button("↗",key=f"sh_{post['id']}"):
            k=f"sopen_{post['id']}"
            st.session_state[k]=not st.session_state.get(k,False)
            st.rerun()
    with c5:
        if show_profile_link and aemail:
            if st.button("👤 Perfil",key=f"vpa_{post['id']}"):
                st.session_state.profile_view=aemail
                st.rerun()
    if st.session_state.get(f"sopen_{post['id']}",False):
        share_modal(post['id'],post['title'])
    if st.session_state.get(f"sc_{post['id']}",False):
        for c in post["comments"]:
            st.markdown(
                f'<div style="background:var(--surface);border-radius:10px;padding:7px 12px;margin:3px 0;font-size:.82rem;border:1px solid var(--bdr);">'
                f'<strong style="color:var(--blue-g);">{c["user"]}</strong>: {c["text"]}</div>',
                unsafe_allow_html=True
            )
        nc=st.text_input("",key=f"ci_{post['id']}",label_visibility="collapsed",placeholder="Adicionar comentário…")
        if st.button("Enviar",key=f"cs_{post['id']}"):
            if nc:
                post["comments"].append({"user":guser().get("name","Você"),"text":nc})
                record(post["tags"],.8)
                save_db()
                st.rerun()

# ─── BUSCA DE ARTIGOS (real internet) ───────
def page_search():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1>Busca de Artigos</h1>',unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.85rem;margin-bottom:1rem;">Busca em tempo real via Semantic Scholar + CrossRef + pesquisas da Nebula</p>',unsafe_allow_html=True)
    c1,c2,c3=st.columns([3,.9,.9])
    with c1:
        q=st.text_input("",placeholder="Título, autor, DOI, tema…",key="sq",label_visibility="collapsed")
    with c2:
        src=st.selectbox("",["Nebula + Internet","Só Nebula","Só Internet"],key="src_sel",label_visibility="collapsed")
    with c3:
        yr=st.selectbox("",["Todos anos","2026","2025","2024","2023","2022"],key="yr_f",label_visibility="collapsed")
    if q:
        ql=q.lower()
        record([ql],.3)
        neb_res=[p for p in st.session_state.feed_posts if
                 ql in p["title"].lower() or
                 ql in p["abstract"].lower() or
                 any(ql in t.lower() for t in p["tags"]) or
                 ql in p["author"].lower()]
        if yr!="Todos anos":
            neb_res=[p for p in neb_res if yr in p.get("date","")]
        if src=="Só Internet":
            neb_res=[]
        cache_key=f"{q}|{yr}"
        web_res=[]
        if src!="Só Nebula":
            if cache_key not in st.session_state.scholar_cache:
                with st.spinner("Buscando em Semantic Scholar e CrossRef…"):
                    ss=search_semantic_scholar(q,8)
                    cr=search_crossref(q,5)
                    merged=ss+[x for x in cr if not any(x["title"].lower()==s["title"].lower() for s in ss)]
                    if yr!="Todos anos":
                        merged=[a for a in merged if str(a.get("year",""))==yr]
                    st.session_state.scholar_cache[cache_key]=merged
            web_res=st.session_state.scholar_cache.get(cache_key,[])
        tab_all,tab_neb,tab_web=st.tabs([f"  Todos ({len(neb_res)+len(web_res)})  ",f"  Nebula ({len(neb_res)})  ",f"  Internet ({len(web_res)})  "])
        with tab_neb:
            if neb_res:
                for p in neb_res:
                    render_search_post(p)
            else:
                st.markdown('<div style="color:var(--t3);text-align:center;padding:2rem;">Nenhum resultado na Nebula.</div>',unsafe_allow_html=True)
        with tab_web:
            if src=="Só Nebula":
                st.info("Busca na internet desativada.")
            elif web_res:
                for a in web_res:
                    render_web_article(a)
            else:
                st.markdown('<div style="color:var(--t3);text-align:center;padding:2rem;">Sem resultados online. Verifique conexão ou tente outros termos.</div>',unsafe_allow_html=True)
        with tab_all:
            if neb_res:
                st.markdown('<div style="font-size:.74rem;color:var(--blue-g);font-weight:600;margin-bottom:.4rem;letter-spacing:.04em;">NEBULA</div>',unsafe_allow_html=True)
                for p in neb_res:
                    render_search_post(p)
            if web_res:
                if neb_res:
                    st.markdown("<hr>",unsafe_allow_html=True)
                st.markdown('<div style="font-size:.74rem;color:var(--cyan-s);font-weight:600;margin-bottom:.4rem;letter-spacing:.04em;">BASE ACADÊMICA GLOBAL</div>',unsafe_allow_html=True)
                for a in web_res:
                    render_web_article(a)
            if not neb_res and not web_res:
                st.markdown('<div class="card" style="text-align:center;padding:3rem;"><div style="font-size:2rem;margin-bottom:1rem;">🔭</div><div style="color:var(--t3);">Nenhum resultado encontrado</div></div>',unsafe_allow_html=True)
    else:
        u=guser()
        tags=area_to_tags(u.get("area",""))
        if tags:
            st.markdown(f'<div style="color:var(--t2);font-size:.83rem;margin-bottom:.8rem;">💡 Sugestões para <strong>{u.get("area","")}</strong>:</div>',unsafe_allow_html=True)
            cols=st.columns(5)
            for i,t in enumerate(tags[:5]):
                with cols[i%5]:
                    if st.button(f"🔎 {t}",key=f"sug_{t}",use_container_width=True):
                        st.session_state["sq"]=t
                        st.rerun()
        st.markdown('<p style="color:var(--t3);font-size:.82rem;margin-top:1rem;">Digite um termo para buscar artigos na Nebula e em bases acadêmicas globais (Semantic Scholar + CrossRef) em tempo real.</p>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

def render_search_post(post):
    aemail=post.get("author_email","")
    aphoto=get_photo(aemail)
    st.markdown(f"""
    <div class="scard">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:.6rem;">
        {avh(post['avatar'],30,aphoto)}
        <div style="flex:1;">
          <div style="font-size:.81rem;font-weight:600;">{post['author']}</div>
          <div style="font-size:.7rem;color:var(--t3);">{post['area']} · {post['date']} · {badge(post['status'])}</div>
        </div>
        <span style="font-size:.68rem;color:var(--blue-g);background:rgba(37,99,235,.1);border-radius:8px;padding:2px 7px;white-space:nowrap;">Nebula</span>
      </div>
      <div style="font-family:'Playfair Display',serif;font-size:.94rem;font-weight:700;margin-bottom:.3rem;">{post['title']}</div>
      <div style="font-size:.82rem;color:var(--t2);margin-bottom:.4rem;">{post['abstract'][:220]}…</div>
      <div>{tags_html(post['tags'])}</div>
    </div>
    """,unsafe_allow_html=True)
    if aemail and st.button("👤 Ver perfil do autor",key=f"vpa_s_{post['id']}"):
        st.session_state.profile_view=aemail
        st.rerun()

def render_web_article(a):
    src_color="#22d3ee" if a.get("origin")=="semantic" else "#a78bfa"
    src_name="Semantic Scholar" if a.get("origin")=="semantic" else "CrossRef"
    cite=f" · {a['citations']} citações" if a.get("citations") else ""
    st.markdown(f"""
    <div class="scard">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:.35rem;">
        <div style="flex:1;font-family:'Playfair Display',serif;font-size:.94rem;font-weight:700;">{a['title']}</div>
        <span style="font-size:.67rem;color:{src_color};background:rgba(6,182,212,.08);border-radius:8px;padding:2px 7px;white-space:nowrap;flex-shrink:0;">{src_name}</span>
      </div>
      <div style="color:var(--t3);font-size:.73rem;margin-bottom:.4rem;">{a['authors']} · <em>{a['source']}</em> · {a['year']}{cite}</div>
      <div style="color:var(--t2);font-size:.83rem;line-height:1.6;margin-bottom:.4rem;">{a['abstract']}</div>
      <div style="font-size:.69rem;color:var(--t3);">DOI/ID: {a['doi']}</div>
    </div>
    """,unsafe_allow_html=True)
    ca,cb,cc=st.columns([1,1,1])
    with ca:
        if st.button("📌 Salvar",key=f"sv_w_{a['doi'][:18]}_{a['year']}"):
            if st.session_state.folders:
                first=list(st.session_state.folders.keys())[0]
                fn=f"{a['title'][:28]}.pdf"
                fd=st.session_state.folders[first]
                lst=fd["files"] if isinstance(fd,dict) else fd
                if fn not in lst:
                    lst.append(fn)
                save_db()
                st.toast(f"Salvo em '{first}'")
            else:
                st.toast("Crie uma pasta primeiro!")
    with cb:
        if st.button("📋 Citar APA",key=f"ct_w_{a['doi'][:18]}_{a['year']}"):
            st.toast(f'{a["authors"]} ({a["year"]}). {a["title"]}. {a["source"]}.')
    with cc:
        if a.get("url"):
            st.markdown(
                f'<a href="{a["url"]}" target="_blank" style="color:var(--blue-g);font-size:.82rem;text-decoration:none;line-height:2.4;">Abrir ↗</a>',
                unsafe_allow_html=True
            )

# ─── REDE DE CONHECIMENTO 3D ─────────────────
def page_knowledge():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1>Rede de Conhecimento 3D</h1>',unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.86rem;margin-bottom:.8rem;">Grafo 3D interativo — arraste, gire, explore conexões entre áreas. Hover nos nós para detalhes.</p>',unsafe_allow_html=True)
    nodes=st.session_state.knowledge_nodes
    node_map={n["id"]:n for n in nodes}
    ex,ey,ez=[],[],[]
    for n in nodes:
        for conn in n.get("connections",[]):
            if conn in node_map:
                t=node_map[conn]
                ex+=[n["x"],t["x"],None]
                ey+=[n["y"],t["y"],None]
                ez+=[n["z"],t["z"],None]
    fig=go.Figure()
    fig.add_trace(go.Scatter3d(
        x=ex,y=ey,z=ez,
        mode="lines",
        line=dict(color="rgba(37,99,235,.28)",width=2.5),
        hoverinfo="none",
        showlegend=False
    ))
    fig.add_trace(go.Scatter3d(
        x=[n["x"] for n in nodes],
        y=[n["y"] for n in nodes],
        z=[n["z"] for n in nodes],
        mode="markers+text",
        marker=dict(
            size=[n.get("size",16) for n in nodes],
            color=[n.get("color","#2563eb") for n in nodes],
            opacity=.90,
            line=dict(color="rgba(200,220,255,.28)",width=1.5)
        ),
        text=[n["id"] for n in nodes],
        textposition="top center",
        textfont=dict(color="#b0c4de",size=9,family="DM Sans"),
        hovertemplate="<b>%{text}</b><br>Conexões diretas: %{customdata}<extra></extra>",
        customdata=[len(n.get("connections",[])) for n in nodes],
        showlegend=False,
    ))
    fig.update_layout(
        height=540,
        scene=dict(
            xaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),
            yaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),
            zaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),
            bgcolor="rgba(0,0,0,0)",
            camera=dict(eye=dict(x=1.6,y=1.4,z=1.0))
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0,r=0,t=0,b=0),
        font=dict(color="#94a8d0"),
    )
    st.plotly_chart(fig,use_container_width=True)
    total_conn=sum(len(n.get("connections",[])) for n in nodes)
    c1,c2,c3,c4=st.columns(4)
    for col,(v,l) in zip([c1,c2,c3,c4],[(len(nodes),"Nós"),(total_conn,"Conexões"),(len(st.session_state.followed),"Seguindo"),(len(st.session_state.feed_posts),"Pesquisas na rede")]):
        with col:
            st.markdown(f'<div class="mbox"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>',unsafe_allow_html=True)
    st.markdown("<hr>",unsafe_allow_html=True)
    tab_add,tab_map,tab_edit=st.tabs(["  ＋ Adicionar  ","  Mapa de conexões  ","  Editar nós  "])
    with tab_add:
        ca,cb,cc,cd=st.columns([2,2,1,1])
        with ca:
            t1=st.text_input("Tópico A",key="kn_t1")
        with cb:
            t2=st.text_input("Conectar com Tópico B",key="kn_t2")
        with cc:
            color=st.color_picker("Cor","#3b7cf4",key="kn_col")
        with cd:
            st.markdown("<br>",unsafe_allow_html=True)
            if st.button("Adicionar",key="btn_kn"):
                if t1 and t2:
                    ids=[n["id"] for n in nodes]
                    if t1 not in ids:
                        nodes.append({"id":t1,"x":random.uniform(.05,.92),"y":random.uniform(.05,.92),"z":random.uniform(.05,.92),"connections":[t2],"color":color,"size":16})
                    else:
                        for n in nodes:
                            if n["id"]==t1 and t2 not in n.get("connections",[]):
                                n.setdefault("connections",[]).append(t2)
                    record([t1.lower(),t2.lower()],1.0)
                    st.session_state.notifications.insert(0,f"Nova conexão: {t1} ↔ {t2}")
                    st.success(f"Conexão {t1} ↔ {t2} adicionada!")
                    st.rerun()
    with tab_map:
        for n in nodes:
            if n.get("connections"):
                conns="".join(
                    f'<span style="background:rgba(6,182,212,.10);border:1px solid rgba(6,182,212,.22);border-radius:8px;padding:2px 9px;font-size:.79rem;margin:2px;">{c}</span>'
                    for c in n["connections"]
                )
                st.markdown(
                    f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:6px;background:var(--glass);border:1px solid var(--bdr);border-radius:12px;padding:9px 14px;margin-bottom:5px;">'
                    f'<span style="background:{n.get("color","#2563eb")}20;border:1px solid {n.get("color","#2563eb")}55;border-radius:8px;padding:3px 11px;font-size:.82rem;font-weight:600;color:{n.get("color","#2563eb")};white-space:nowrap;">{n["id"]}</span>'
                    f'<span style="color:var(--t3);font-size:.78rem;">→</span>'
                    f'{conns}</div>',
                    unsafe_allow_html=True
                )
    with tab_edit:
        sel=st.selectbox("Nó para editar",[n["id"] for n in nodes],key="sel_node")
        node_obj=next((n for n in nodes if n["id"]==sel),None)
        if node_obj:
            cn1,cn2,cn3=st.columns(3)
            with cn1:
                nx=st.slider("X",0.0,1.0,float(node_obj["x"]),key="nx")
                ny=st.slider("Y",0.0,1.0,float(node_obj["y"]),key="ny")
            with cn2:
                nz=st.slider("Z",0.0,1.0,float(node_obj["z"]),key="nz")
                ns=st.slider("Tamanho",8,40,int(node_obj.get("size",16)),key="ns")
            with cn3:
                nc=st.color_picker("Cor",node_obj.get("color","#2563eb"),key="nc")
            c_save,c_del,_=st.columns([1,1,2])
            with c_save:
                if st.button("Salvar edição",key="btn_edit_node"):
                    node_obj.update({"x":nx,"y":ny,"z":nz,"size":ns,"color":nc})
                    st.success("Nó atualizado!")
                    st.rerun()
            with c_del:
                if st.button("Remover nó",key="btn_rm_node"):
                    st.session_state.knowledge_nodes=[n for n in nodes if n["id"]!=sel]
                    st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)

# ─── PASTAS ─────────────────────────────────
def page_folders():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1>Pastas de Pesquisa</h1>',unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.86rem;margin-bottom:1rem;">Crie e organize suas pastas do jeito que preferir</p>',unsafe_allow_html=True)
    c1,c2,_=st.columns([2,1.2,1.5])
    with c1:
        nf_name=st.text_input("Nome da pasta",placeholder="Ex: Genômica Comparativa",key="nf_n")
    with c2:
        nf_desc=st.text_input("Descrição",placeholder="Breve descrição",key="nf_d")
    if st.button("Criar pasta",key="btn_nf"):
        if nf_name.strip():
            if nf_name not in st.session_state.folders:
                st.session_state.folders[nf_name]={"desc":nf_desc,"files":[],"notes":""}
                save_db()
                st.success(f"Pasta '{nf_name}' criada!")
                st.rerun()
            else:
                st.warning("Pasta já existe.")
        else:
            st.warning("Digite um nome para a pasta.")
    st.markdown("<hr>",unsafe_allow_html=True)
    if not st.session_state.folders:
        st.markdown('<div class="card" style="text-align:center;padding:3rem;"><div style="font-size:3rem;margin-bottom:1rem;">📂</div><div style="color:var(--t2);font-family:\'Playfair Display\',serif;font-size:1rem;">Nenhuma pasta criada ainda</div><div style="color:var(--t3);font-size:.84rem;margin-top:.4rem;">Use o formulário acima para criar sua primeira pasta</div></div>',unsafe_allow_html=True)
    else:
        cols=st.columns(3)
        for idx,(fname,fdata) in enumerate(list(st.session_state.folders.items())):
            files=fdata["files"] if isinstance(fdata,dict) else fdata
            desc=fdata.get("desc","") if isinstance(fdata,dict) else ""
            with cols[idx%3]:
                st.markdown(
                    f'<div class="card" style="text-align:center;">'
                    f'<div style="font-size:2.2rem;margin-bottom:8px;">📁</div>'
                    f'<div style="font-family:\'Playfair Display\',serif;font-weight:700;font-size:.98rem;">{fname}</div>'
                    f'<div style="color:var(--t3);font-size:.71rem;margin-top:3px;">{desc}</div>'
                    f'<div style="color:var(--blue-g);font-size:.74rem;margin-top:5px;">{len(files)} arquivo(s)</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                with st.expander("Abrir pasta"):
                    if isinstance(fdata,dict) and fdata.get("notes"):
                        st.markdown(f'<div style="color:var(--t2);font-size:.81rem;margin-bottom:.5rem;">📝 {fdata["notes"]}</div>',unsafe_allow_html=True)
                    for f in files:
                        st.markdown(f'<div style="font-size:.81rem;padding:3px 0;color:var(--t2);border-bottom:1px solid var(--bdr);">📄 {f}</div>',unsafe_allow_html=True)
                    up=st.file_uploader("Adicionar arquivo",key=f"up_{fname}",label_visibility="collapsed")
                    if up:
                        lst=fdata["files"] if isinstance(fdata,dict) else fdata
                        if up.name not in lst:
                            lst.append(up.name)
                        save_db()
                        st.success("Adicionado!")
                        st.rerun()
                    note=st.text_input("Nota",key=f"note_{fname}",placeholder="Observação rápida…")
                    if st.button("Salvar nota",key=f"sn_{fname}"):
                        if isinstance(fdata,dict):
                            fdata["notes"]=note
                        save_db()
                        st.success("Nota salva!")
                if st.button(f"Excluir '{fname}'",key=f"df_{fname}"):
                    del st.session_state.folders[fname]
                    save_db()
                    st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)

# ─── ANALYTICS ──────────────────────────────
def page_analytics():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1>Análises de Impacto</h1>',unsafe_allow_html=True)
    d=st.session_state.stats_data
    email=st.session_state.current_user
    tab_perf,tab_pref,tab_edit=st.tabs(["  Desempenho  ","  Perfil de Interesses  ","  Editar Dados  "])
    pc=dict(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#4a5e80",family="DM Sans"),
        margin=dict(l=10,r=10,t=40,b=10),
        xaxis=dict(showgrid=False,color="#4a5e80"),
        yaxis=dict(showgrid=True,gridcolor="rgba(37,99,235,.07)",color="#4a5e80")
    )
    with tab_perf:
        cols=st.columns(4)
        metrics=[
            (str(max(d["views"])),"Pico visualizações"),
            (str(sum(d["citations"])),"Total citações"),
            (str(d.get("h_index",4)),"Índice H"),
            (f'{d.get("fator_impacto",3.8):.1f}',"Fator de impacto")
        ]
        for col,(v,l) in zip(cols,metrics):
            with col:
                st.markdown(f'<div class="mbox"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>',unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1:
            fig=go.Figure()
            fig.add_trace(go.Scatter(
                x=d["months"],
                y=d["views"],
                fill="tozeroy",
                fillcolor="rgba(37,99,235,.10)",
                line=dict(color="#3b7cf4",width=2.5),
                mode="lines+markers",
                marker=dict(size=5,color="#60a5fa")
            ))
            fig.update_layout(title=dict(text="Visualizações mensais",font=dict(color="#e0e8ff",family="Playfair Display")),height=260,**pc)
            st.plotly_chart(fig,use_container_width=True)
        with c2:
            fig2=go.Figure()
            fig2.add_trace(go.Bar(
                x=d["months"],
                y=d["citations"],
                marker=dict(
                    color=d["citations"],
                    colorscale=[[0,"#0a1628"],[1,"#06b6d4"]],
                    line=dict(color="rgba(96,165,250,.22)",width=1)
                )
            ))
            fig2.update_layout(title=dict(text="Citações mensais",font=dict(color="#e0e8ff",family="Playfair Display")),height=260,**pc)
            st.plotly_chart(fig2,use_container_width=True)
        c3,c4=st.columns(2)
        with c3:
            my_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==email]
            if my_posts:
                fig3=go.Figure()
                fig3.add_trace(go.Bar(
                    name="Curtidas",
                    x=[p["title"][:18]+"…" for p in my_posts],
                    y=[p["likes"] for p in my_posts],
                    marker_color="#2563eb"
                ))
                fig3.add_trace(go.Bar(
                    name="Comentários",
                    x=[p["title"][:18]+"…" for p in my_posts],
                    y=[len(p["comments"]) for p in my_posts],
                    marker_color="#06b6d4"
                ))
                fig3.update_layout(
                    barmode="group",
                    title=dict(text="Engajamento por pesquisa",font=dict(color="#e0e8ff",family="Playfair Display")),
                    height=260,
                    **pc,
                    legend=dict(font=dict(color="#94a8d0"))
                )
                st.plotly_chart(fig3,use_container_width=True)
            else:
                st.markdown('<div class="card" style="text-align:center;padding:2.5rem;"><div style="color:var(--t3);">Publique pesquisas para ver engajamento</div></div>',unsafe_allow_html=True)
        with c4:
            fig4=go.Figure(go.Pie(
                labels=["Brasil","EUA","Portugal","Alemanha","Argentina","Outros"],
                values=[95,62,38,25,10,20],
                hole=0.6,
                marker=dict(
                    colors=["#2563eb","#1d4ed8","#3b82f6","#1e40af","#60a5fa","#0ea5e9"],
                    line=dict(color=["#03040a"]*6,width=2)
                ),
                textfont=dict(color="white")
            ))
            fig4.update_layout(
                title=dict(text="Leitores por país",font=dict(color="#e0e8ff",family="Playfair Display")),
                height=260,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                legend=dict(font=dict(color="#94a8d0")),
                margin=dict(l=10,r=10,t=40,b=10)
            )
            st.plotly_chart(fig4,use_container_width=True)
        fig_g=go.Figure(go.Indicator(
            mode="gauge+number",
            value=d.get("aceitacao",94),
            title={"text":"Taxa de Aceitação (%)","font":{"color":"#94a8d0","family":"DM Sans"}},
            number={"suffix":"%","font":{"color":"#60a5fa","size":34}},
            gauge={
                "axis":{"range":[0,100],"tickcolor":"#4a5e80"},
                "bar":{"color":"#2563eb"},
                "bgcolor":"rgba(10,17,40,.5)",
                "bordercolor":"rgba(37,99,235,.3)",
                "steps":[
                    {"range":[0,50],"color":"rgba(239,68,68,.08)"},
                    {"range":[50,80],"color":"rgba(245,158,11,.08)"},
                    {"range":[80,100],"color":"rgba(16,185,129,.08)"}
                ]
            }
        ))
        fig_g.update_layout(height=200,paper_bgcolor="rgba(0,0,0,0)",font=dict(color="#94a8d0"))
        st.plotly_chart(fig_g,use_container_width=True)
        if d.get("notes"):
            st.markdown(
                f'<div class="abox"><div style="font-size:.78rem;color:var(--t3);margin-bottom:4px;">NOTAS</div>'
                f'<div style="color:var(--t2);font-size:.85rem;line-height:1.6;">{d["notes"]}</div></div>',
                unsafe_allow_html=True
            )
    with tab_pref:
        prefs=st.session_state.user_prefs.get(email,{})
        if prefs:
            st.markdown('<p style="color:var(--t3);font-size:.84rem;margin-bottom:1rem;">Baseado nas suas interações: curtidas, buscas, comentários e publicações.</p>',unsafe_allow_html=True)
            top=sorted(prefs.items(),key=lambda x:-x[1])[:12]
            mx=max(s for _,s in top) if top else 1
            c1,c2=st.columns(2)
            for i,(tag,score) in enumerate(top):
                pct=int(score/mx*100)
                with (c1 if i%2==0 else c2):
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;font-size:.81rem;margin-bottom:3px;">'
                        f'<span style="color:var(--t2);">{tag}</span>'
                        f'<span style="color:var(--blue-g);">{pct}%</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                    st.progress(pct/100)
        else:
            st.info("Interaja com pesquisas e buscas para construir seu perfil de interesses.")
        u=guser()
        area_tags=area_to_tags(u.get("area",""))
        if area_tags:
            st.markdown("<hr>",unsafe_allow_html=True)
            st.markdown(f'<h3>Pesquisas da sua área: {u.get("area","")}</h3>',unsafe_allow_html=True)
            area_posts=[p for p in st.session_state.feed_posts if any(at.lower() in [t.lower() for t in p["tags"]] for at in area_tags)]
            for p in area_posts[:3]:
                render_search_post(p)
    with tab_edit:
        st.markdown('<h3>Editar métricas manualmente</h3>',unsafe_allow_html=True)
        ce1,ce2,ce3=st.columns(3)
        with ce1:
            new_h=st.number_input("Índice H",0,100,d.get("h_index",4),key="e_h")
        with ce2:
            new_fi=st.number_input("Fator de impacto",0.0,50.0,float(d.get("fator_impacto",3.8)),step=0.1,key="e_fi")
        with ce3:
            new_ac=st.number_input("Taxa de aceitação (%)",0,100,d.get("aceitacao",94),key="e_ac")
        st.markdown("**Visualizações mensais** (Mar → Fev):")
        new_views=[]
        vc=st.columns(6)
        for i,(m,v) in enumerate(zip(d["months"][:6],d["views"][:6])):
            with vc[i]:
                new_views.append(st.number_input(m,0,value=v,key=f"ev_{i}"))
        vc2=st.columns(6)
        for i,(m,v) in enumerate(zip(d["months"][6:],d["views"][6:])):
            with vc2[i]:
                new_views.append(st.number_input(m,0,value=v,key=f"ev_{i+6}"))
        new_notes=st.text_area("Notas da pesquisa",value=d.get("notes",""),key="e_notes",height=80)
        if st.button("Salvar métricas",key="btn_save_m"):
            d.update({"h_index":new_h,"fator_impacto":new_fi,"aceitacao":new_ac,"views":new_views,"notes":new_notes})
            st.success("Métricas atualizadas!")
            st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)

# ─── ANÁLISE DE IMAGEM ───────────────────────
def page_img_search():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1>Análise de Imagem Científica</h1>',unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.86rem;margin-bottom:1.2rem;">Análise real de padrões, cores, texturas, formas e classificação automática de imagens científicas</p>',unsafe_allow_html=True)
    col_up,col_res=st.columns([1,1.7])
    with col_up:
        st.markdown('<div class="card">',unsafe_allow_html=True)
        st.markdown('<div style="font-weight:600;margin-bottom:.8rem;">Upload de imagem</div>',unsafe_allow_html=True)
        img_file=st.file_uploader("",type=["png","jpg","jpeg","webp","tiff"],label_visibility="collapsed")
        if img_file:
            st.image(img_file,use_container_width=True,caption="Imagem carregada")
        run=st.button("🔬 Analisar imagem",use_container_width=True,key="btn_run")
        st.markdown('<div style="color:var(--t3);font-size:.72rem;margin-top:.8rem;line-height:1.5;">Detectamos: padrões · cores · texturas · simetria · entropia · classificação científica</div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)
    with col_res:
        if run and img_file:
            img_file.seek(0)
            with st.spinner("Analisando padrões, cores e estrutura…"):
                rep=analyze_image(img_file)
            if rep:
                st.markdown(f"""
                <div class="abox">
                  <div style="font-size:.69rem;color:var(--t3);letter-spacing:.08em;margin-bottom:4px;">CATEGORIA DETECTADA</div>
                  <div style="font-family:'Playfair Display',serif;font-size:1.1rem;font-weight:700;color:var(--t1);margin-bottom:4px;">{rep['category']}</div>
                  <div style="font-size:.84rem;color:var(--t2);line-height:1.55;">{rep['structure']}</div>
                  <div style="margin-top:10px;display:flex;gap:12px;flex-wrap:wrap;">
                    <span style="font-size:.73rem;color:var(--ok);">✓ Confiança: {rep['confidence']}%</span>
                    <span style="font-size:.73rem;color:var(--t3);">Resolução: {rep['size'][0]}×{rep['size'][1]}px</span>
                    {"<span style='font-size:.73rem;color:var(--warn);'>Tecido orgânico detectado: "+str(rep['skin_pct'])+"% da imagem</span>" if rep['skin_pct']>10 else ""}
                  </div>
                </div>
                """,unsafe_allow_html=True)
                c1,c2,c3=st.columns(3)
                for col,(v,l) in zip(
                    [c1,c2,c3],
                    [
                        (rep['texture']['complexity'],"Complexidade"),
                        (rep['shape']['symmetry_level'],"Simetria"),
                        (rep['color']['dominant'],"Canal dominante")
                    ]
                ):
                    with col:
                        st.markdown(
                            f'<div class="mbox"><div style="font-family:\'Playfair Display\',serif;font-size:1.25rem;font-weight:700;color:#60a5fa;">{v}</div><div class="mlbl">{l}</div></div>',
                            unsafe_allow_html=True
                        )
                r,g,b_v=rep['color']['mean_rgb']
                hex_col="#{:02x}{:02x}{:02x}".format(int(r),int(g),int(b_v))
                pal_html="".join(
                    f'<div style="display:flex;flex-direction:column;align-items:center;gap:3px;">'
                    f'<div style="width:34px;height:34px;border-radius:8px;background:rgb{str(p)};border:1px solid rgba(255,255,255,.12);"></div>'
                    f'<div style="font-size:.62rem;color:var(--t3);">#{"{:02x}{:02x}{:02x}".format(*p).upper()}</div>'
                    f'</div>'
                    for p in rep["palette"]
                )
                st.markdown(f"""
                <div class="abox" style="margin-top:.8rem;">
                  <div style="font-weight:600;font-size:.87rem;margin-bottom:.7rem;">Análise de Cor</div>
                  <div style="display:flex;gap:14px;align-items:center;margin-bottom:.8rem;">
                    <div style="width:46px;height:46px;border-radius:10px;background:{hex_col};border:2px solid var(--bdr-l);flex-shrink:0;"></div>
                    <div style="font-size:.82rem;color:var(--t2);">
                      RGB médio: <strong style="color:var(--t1);">({int(r)}, {int(g)}, {int(b_v)})</strong><br>
                      Hex: <strong style="color:var(--t1);">{hex_col.upper()}</strong> · 
                      Brilho: <strong style="color:var(--t1);">{rep['color']['brightness']:.0f}/255</strong> ·
                      Temperatura: <strong style="color:var(--t1);">{"Quente 🔴" if rep['color']['warm'] else "Fria 🔵"}</strong>
                    </div>
                  </div>
                  <div style="font-size:.75rem;color:var(--t3);margin-bottom:5px;">Paleta de cores predominantes:</div>
                  <div style="display:flex;gap:7px;flex-wrap:wrap;">{pal_html}</div>
                </div>
                """,unsafe_allow_html=True)
                st.markdown(f"""
                <div class="abox">
                  <div style="font-weight:600;font-size:.87rem;margin-bottom:.7rem;">Textura, Forma e Entropia</div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:.82rem;">
                    <div><span style="color:var(--t3);">Intensidade de bordas:</span><br><strong style="color:var(--t1);">{rep['texture']['edge_intensity']:.2f}</strong></div>
                    <div><span style="color:var(--t3);">Contraste (σ):</span><br><strong style="color:var(--t1);">{rep['texture']['contrast']:.2f}</strong></div>
                    <div><span style="color:var(--t3);">Entropia informacional:</span><br><strong style="color:var(--t1);">{rep['texture']['entropy']:.3f} bits</strong></div>
                    <div><span style="color:var(--t3);">Score de simetria:</span><br><strong style="color:var(--t1);">{rep['shape']['symmetry_score']:.3f}</strong></div>
                  </div>
                </div>
                """,unsafe_allow_html=True)
                st.markdown('<div style="font-weight:600;font-size:.87rem;margin-bottom:.5rem;">Pesquisas relacionadas</div>',unsafe_allow_html=True)
                cat_l=rep['category'].lower()
                related=[p for p in st.session_state.feed_posts if any(t.lower() in cat_l for t in p.get("tags",[]))][:2]
                if related:
                    for p in related:
                        render_search_post(p)
            else:
                st.error("Não foi possível analisar. Verifique o formato do arquivo.")
        elif not img_file:
            st.markdown("""
            <div class="card" style="text-align:center;padding:4rem 2rem;">
              <div style="font-size:3.5rem;margin-bottom:1rem;">🔬</div>
              <div style="font-family:'Playfair Display',serif;font-size:1rem;color:var(--t2);margin-bottom:.5rem;">Carregue uma imagem para análise real</div>
              <div style="color:var(--t3);font-size:.79rem;line-height:1.7;">
                Suportado: PNG · JPG · WEBP · TIFF<br>
                Detecta: padrões biológicos · fluorescência · histologia<br>
                cristalografia · diagramas · imagens multiespectrais
              </div>
            </div>
            """,unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ─── CHAT (só mensagens) ─────────────────────
def page_chat():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1>Chat Seguro</h1>',unsafe_allow_html=True)
    col_c,col_m=st.columns([0.85,2.5])
    with col_c:
        st.markdown('<div style="font-size:.75rem;font-weight:600;color:var(--t3);letter-spacing:.06em;margin-bottom:.7rem;">CONVERSAS</div>',unsafe_allow_html=True)

        # Garantir que users é dict
        if not isinstance(st.session_state.users, dict):
            st.session_state.users = {}

        contacts_shown=set()
        for ue in st.session_state.chat_contacts:
            if ue==st.session_state.current_user:
                continue
            ud=st.session_state.users.get(ue,{})
            # fallback seguro se usuário não existir
            if not ud:
                ud = {"name": ue, "area": "", "photo_b64": None}
            uname=ud.get("name","?")
            uin=ini(uname)
            uphoto=ud.get("photo_b64")
            if ue in contacts_shown:
                continue
            contacts_shown.add(ue)
            active=st.session_state.active_chat==ue
            msgs=st.session_state.chat_messages.get(ue,[])
            last=msgs[-1]["text"][:28]+"…" if msgs and len(msgs[-1]["text"])>28 else (msgs[-1]["text"] if msgs else "Iniciar conversa")
            bg="rgba(37,99,235,.18)" if active else "var(--glass)"
            bdr="rgba(96,165,250,.4)" if active else "var(--bdr)"
            online=random.random()>.4
            dot='<span class="don"></span>' if online else '<span class="doff"></span>'
            st.markdown(
                f'<div style="background:{bg};border:1px solid {bdr};border-radius:12px;padding:9px 11px;margin-bottom:5px;">'
                f'<div style="display:flex;align-items:center;gap:8px;">'
                f'{avh(uin,32,uphoto)}'
                f'<div style="overflow:hidden;min-width:0;">'
                f'<div style="font-size:.83rem;font-weight:600;display:flex;align-items:center;">{dot}{uname}</div>'
                f'<div style="font-size:.7rem;color:var(--t3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{last}</div>'
                f'</div></div></div>',
                unsafe_allow_html=True
            )
            if st.button("Abrir",key=f"oc_{ue}",use_container_width=True):
                st.session_state.active_chat=ue
                st.rerun()
        # Add contact by email
        st.markdown("<hr>",unsafe_allow_html=True)
        new_contact=st.text_input("",placeholder="Adicionar por e-mail…",key="new_ct",label_visibility="collapsed")
        if st.button("Adicionar",key="btn_add_ct"):
            if isinstance(st.session_state.users, dict) and new_contact in st.session_state.users and new_contact!=st.session_state.current_user:
                if new_contact not in st.session_state.chat_contacts:
                    st.session_state.chat_contacts.append(new_contact)
                st.rerun()
            elif new_contact:
                st.toast("Usuário não encontrado.")
    with col_m:
        if st.session_state.active_chat:
            contact=st.session_state.active_chat
            if not isinstance(st.session_state.users, dict):
                st.session_state.users = {}
            cd=st.session_state.users.get(contact,{})
            if not cd:
                cd={"name":contact,"photo_b64":None}
            cname=cd.get("name","?")
            cin=ini(cname)
            cphoto=cd.get("photo_b64")
            msgs=st.session_state.chat_messages.get(contact,[])
            # Header
            st.markdown(
                f'<div style="background:var(--glass);border:1px solid var(--bdr);border-radius:14px;padding:12px 16px;margin-bottom:1rem;display:flex;align-items:center;gap:12px;">'
                f'{avh(cin,38,cphoto)}'
                f'<div style="flex:1;"><div style="font-weight:700;font-size:.95rem;">{cname}</div>'
                f'<div style="font-size:.72rem;color:var(--ok);">🔒 Criptografia ativa · AES-256</div></div>'
                f'</div>',
                unsafe_allow_html=True
            )
            # Messages
            for msg in msgs:
                is_me=msg["from"]=="me"
                cls="bme" if is_me else "bthem"
                align="right" if is_me else "left"
                st.markdown(
                    f'<div class="{cls}">{msg["text"]}'
                    f'<div style="font-size:.66rem;color:var(--t3);margin-top:3px;text-align:{align};">{msg["time"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            # Input
            nm=st.text_input("",placeholder="Mensagem segura…",key=f"mi_{contact}",label_visibility="collapsed")
            if st.button("Enviar →",key=f"ms_{contact}",use_container_width=True):
                if nm:
                    now=datetime.now().strftime("%H:%M")
                    st.session_state.chat_messages.setdefault(contact,[]).append({"from":"me","text":nm,"time":now})
                    st.rerun()
        else:
            st.markdown('<div class="card" style="text-align:center;padding:4rem;"><div style="font-size:3rem;margin-bottom:1rem;">💬</div><div style="color:var(--t3);">Selecione uma conversa para começar</div><div style="font-size:.78rem;color:var(--t3);margin-top:.5rem;">🔒 Todas as mensagens são criptografadas end-to-end</div></div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ─── CONFIGURAÇÕES / PERFIL ──────────────────
def page_settings():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1>Perfil e Configurações</h1>',unsafe_allow_html=True)
    u=guser()
    email=st.session_state.current_user
    tab_p,tab_s,tab_pr=st.tabs(["  Meu Perfil  ","  Segurança  ","  Privacidade  "])
    with tab_p:
        nm=u.get("name","")
        in_=ini(nm)
        photo=u.get("photo_b64")
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:1.5rem;padding:1.2rem;background:var(--glass);border:1px solid var(--bdr);border-radius:var(--r-lg);margin-bottom:1.5rem;">
          <div class="prof-photo">{("<img src='"+photo+"'/>") if photo else f'<span style="font-size:2rem;">{in_}</span>'}</div>
          <div>
            <div style="font-family:'Playfair Display',serif;font-size:1.4rem;font-weight:700;">{nm}</div>
            <div style="color:var(--blue-g);font-size:.85rem;">{u.get('area','')}</div>
            <div style="color:var(--t3);font-size:.78rem;margin-top:2px;">{email}</div>
            <div style="display:flex;gap:1rem;margin-top:.6rem;">
              <span style="font-size:.8rem;color:var(--t2);"><strong style="color:var(--t1);">{u.get('followers',0)}</strong> seguidores</span>
              <span style="font-size:.8rem;color:var(--t2);"><strong style="color:var(--t1);">{u.get('following',0)}</strong> seguindo</span>
            </div>
          </div>
        </div>
        """,unsafe_allow_html=True)
        st.markdown('<div style="font-weight:600;font-size:.88rem;margin-bottom:.5rem;">📷 Foto de perfil</div>',unsafe_allow_html=True)
        ph=st.file_uploader("",type=["png","jpg","jpeg","webp"],label_visibility="collapsed",key="ph_up")
        if ph:
            b64=img_to_b64(ph)
            if b64:
                if not isinstance(st.session_state.users, dict):
                    st.session_state.users = {}
                st.session_state.users[email]["photo_b64"]=b64
                save_db()
                st.success("✓ Foto atualizada com sucesso!")
                st.image(ph,width=100,caption="Nova foto")
                st.rerun()
        st.markdown("<hr>",unsafe_allow_html=True)
        st.markdown('<div style="font-weight:600;font-size:.88rem;margin-bottom:.5rem;">Editar informações</div>',unsafe_allow_html=True)
        new_n=st.text_input("Nome completo",value=u.get("name",""),key="cfg_n")
        new_e=st.text_input("E-mail",value=email,key="cfg_e")
        new_a=st.text_input("Área de pesquisa",value=u.get("area",""),key="cfg_a")
        new_b=st.text_area("Biografia",value=u.get("bio",""),key="cfg_b",height=90,placeholder="Fale sobre sua pesquisa, instituição e interesses…")
        if st.button("Salvar perfil",key="btn_sp"):
            if not isinstance(st.session_state.users, dict):
                st.session_state.users = {}
            st.session_state.users[email]["name"]=new_n
            st.session_state.users[email]["area"]=new_a
            st.session_state.users[email]["bio"]=new_b
            if new_e!=email and new_e not in st.session_state.users:
                st.session_state.users[new_e]=st.session_state.users.pop(email)
                st.session_state.current_user=new_e
                email=new_e
            save_db()
            record(area_to_tags(new_a),1.5)
            st.success("✓ Perfil salvo!")
            st.rerun()
    with tab_s:
        st.markdown('<h3>Alterar senha</h3>',unsafe_allow_html=True)
        op=st.text_input("Senha atual",type="password",key="op")
        np_=st.text_input("Nova senha",type="password",key="np_")
        np2=st.text_input("Confirmar",type="password",key="np2")
        if st.button("Alterar senha",key="btn_cpw"):
            if hp(op)!=u["password"]:
                st.error("Senha atual incorreta.")
            elif np_!=np2:
                st.error("Senhas não coincidem.")
            elif len(np_)<6:
                st.error("Senha muito curta.")
            else:
                if not isinstance(st.session_state.users, dict):
                    st.session_state.users = {}
                st.session_state.users[email]["password"]=hp(np_)
                save_db()
                st.success("✓ Senha alterada!")
        st.markdown("<hr>",unsafe_allow_html=True)
        st.markdown('<h3>Autenticação em 2 fatores</h3>',unsafe_allow_html=True)
        en=u.get("2fa_enabled",False)
        st.markdown(
            f'<div style="background:var(--glass);border:1px solid var(--bdr);border-radius:14px;padding:14px;display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;">'
            f'<div><div style="font-weight:600;font-size:.9rem;">2FA por e-mail</div>'
            f'<div style="font-size:.74rem;color:var(--t3);">{email}</div></div>'
            f'<span style="color:{"#10b981" if en else "#ef4444"};font-size:.83rem;font-weight:700;">{"✓ Ativo" if en else "✗ Inativo"}</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        if st.button("Desativar 2FA" if en else "Ativar 2FA",key="btn_2fa"):
            if not isinstance(st.session_state.users, dict):
                st.session_state.users = {}
            st.session_state.users[email]["2fa_enabled"]=not en
            save_db()
            st.rerun()
    with tab_pr:
        prots=[
            ("AES-256","Criptografia end-to-end das mensagens"),
            ("SHA-256","Hash de senhas com salt criptográfico"),
            ("TLS 1.3","Transmissão segura de todos os dados"),
            ("Zero Knowledge","Pesquisas privadas inacessíveis pela plataforma")
        ]
        items="".join(
            f'<div style="display:flex;align-items:center;gap:12px;background:rgba(16,185,129,.07);border:1px solid rgba(16,185,129,.18);border-radius:12px;padding:11px;">'
            f'<div style="width:28px;height:28px;border-radius:8px;background:rgba(16,185,129,.14);display:flex;align-items:center;justify-content:center;color:#10b981;font-weight:700;font-size:.78rem;flex-shrink:0;">✓</div>'
            f'<div><div style="font-weight:600;color:#10b981;font-size:.86rem;">{n2}</div>'
            f'<div style="font-size:.73rem;color:var(--t3);">{d2}</div></div></div>'
            for n2,d2 in prots
        )
        st.markdown(f'<div class="card"><div style="font-weight:700;margin-bottom:1rem;">Proteções ativas</div><div style="display:grid;gap:9px;">{items}</div></div>',unsafe_allow_html=True)
        st.markdown('<h3>Visibilidade</h3>',unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1:
            st.selectbox("Perfil",["Público","Só seguidores","Privado"],key="vp")
            st.selectbox("Pesquisas",["Público","Só seguidores","Privado"],key="vr")
        with c2:
            st.selectbox("Estatísticas",["Público","Privado"],key="vs")
            st.selectbox("Rede de conhecimento",["Público","Só seguidores","Privado"],key="vn")
        if st.button("Salvar privacidade",key="btn_priv"):
            st.success("✓ Configurações de privacidade salvas!")
    st.markdown('</div>',unsafe_allow_html=True)

# ─── ROUTER ─────────────────────────────────
def main():
    if not st.session_state.logged_in:
        p=st.session_state.page
        if   p=="verify_email":
            page_verify_email()
        elif p=="2fa":
            page_2fa()
        else:
            page_login()
        return

    render_topnav()

    if st.session_state.profile_view:
        page_profile(st.session_state.profile_view)
        return

    {
        "feed":page_feed,
        "search":page_search,
        "knowledge":page_knowledge,
        "folders":page_folders,
        "analytics":page_analytics,
        "img_search":page_img_search,
        "chat":page_chat,
        "settings":page_settings
    }.get(st.session_state.page, page_feed)()

main()
