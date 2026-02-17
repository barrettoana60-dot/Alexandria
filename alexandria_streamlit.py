import subprocess, sys, os, json, hashlib, random, string, math
from datetime import datetime
from collections import defaultdict
from io import BytesIO

def _pip(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

try:
    import plotly.graph_objects as go
    import plotly.express as px
except ImportError:
    _pip("plotly"); import plotly.graph_objects as go; import plotly.express as px

try:
    import numpy as np
    from PIL import Image as PILImage
except ImportError:
    _pip("pillow numpy")
    import numpy as np
    from PIL import Image as PILImage

import streamlit as st

st.set_page_config(page_title="Nebula", page_icon="🔬",
                   layout="wide", initial_sidebar_state="expanded")

DB_FILE = "nebula_users.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_db(users: dict):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"Aviso: não foi possível salvar no disco ({e}).")

def hp(pw): return hashlib.sha256(pw.encode()).hexdigest()
def code6(): return ''.join(random.choices(string.digits, k=6))
def ini(name): return ''.join(w[0].upper() for w in str(name).split()[:2])

# ═══════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;0,700;0,800;1,400&family=DM+Sans:wght@300;400;500;600&display=swap');
:root{
  --void:#03040a;--deep:#0a1128;--navy:#0d1635;--surface:#111d3a;--elevated:#162348;
  --blue:#2563eb;--blue-l:#3b7cf4;--blue-g:#60a5fa;
  --cyan:#06b6d4;--cyan-s:#22d3ee;
  --t1:#eef2ff;--t2:#94a8d0;--t3:#4a5e80;
  --bdr:rgba(37,99,235,.18);--bdr-l:rgba(96,165,250,.28);--glass:rgba(10,17,40,.72);
  --ok:#10b981;--warn:#f59e0b;--err:#ef4444;
  --r-sm:10px;--r-md:16px;--r-lg:24px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;}
html,body,.stApp{background:var(--void)!important;color:var(--t1)!important;font-family:'DM Sans',sans-serif!important;}
.stApp::before{content:'';position:fixed;inset:0;
  background:radial-gradient(ellipse 100% 70% at 10% 0%,rgba(37,99,235,.10) 0%,transparent 55%),
             radial-gradient(ellipse 70% 90% at 90% 100%,rgba(6,182,212,.07) 0%,transparent 55%);
  pointer-events:none;z-index:0;animation:bgP 12s ease-in-out infinite alternate;}
@keyframes bgP{from{opacity:.7}to{opacity:1}}
h1,h2,h3,h4{font-family:'Playfair Display','Times New Roman',serif!important;color:var(--t1)!important;font-weight:700;}
h1{font-size:1.9rem!important}h2{font-size:1.45rem!important}h3{font-size:1.1rem!important}
section[data-testid="stSidebar"]{background:linear-gradient(160deg,var(--deep) 0%,var(--void) 100%)!important;border-right:1px solid var(--bdr)!important;}
section[data-testid="stSidebar"] *{color:var(--t1)!important;}
section[data-testid="stSidebar"] .stButton>button{
  background:transparent!important;border:none!important;border-radius:var(--r-sm)!important;
  color:var(--t2)!important;text-align:left!important;padding:.5rem .9rem!important;
  box-shadow:none!important;font-size:.86rem!important;font-weight:400!important;
  justify-content:flex-start!important;transition:background .2s,color .2s!important;}
section[data-testid="stSidebar"] .stButton>button:hover{background:rgba(37,99,235,.12)!important;color:var(--t1)!important;transform:none!important;box-shadow:none!important;}
.stTextInput input,.stTextArea textarea{
  background:var(--surface)!important;border:1px solid var(--bdr)!important;
  border-radius:var(--r-sm)!important;color:var(--t1)!important;
  font-family:'DM Sans',sans-serif!important;font-size:.9rem!important;padding:.6rem .9rem!important;
  transition:border-color .25s,box-shadow .25s!important;}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:var(--blue)!important;box-shadow:0 0 0 3px rgba(37,99,235,.15)!important;}
.stTextInput label,.stTextArea label,.stSelectbox label,.stFileUploader label{color:var(--t2)!important;font-size:.82rem!important;}
.stButton>button{
  background:linear-gradient(135deg,rgba(37,99,235,.40) 0%,rgba(6,182,212,.20) 50%,rgba(37,99,235,.30) 100%)!important;
  backdrop-filter:blur(24px) saturate(200%)!important;-webkit-backdrop-filter:blur(24px) saturate(200%)!important;
  border:1px solid rgba(96,165,250,.30)!important;border-radius:var(--r-md)!important;
  color:var(--t1)!important;font-family:'DM Sans',sans-serif!important;font-weight:500!important;
  font-size:.88rem!important;padding:.6rem 1.4rem!important;letter-spacing:.02em!important;
  position:relative!important;overflow:hidden!important;
  transition:all .3s cubic-bezier(.4,0,.2,1)!important;
  box-shadow:0 4px 20px rgba(37,99,235,.18),inset 0 1px 0 rgba(255,255,255,.10)!important;}
.stButton>button:hover{
  background:linear-gradient(135deg,rgba(37,99,235,.60) 0%,rgba(6,182,212,.35) 50%,rgba(37,99,235,.50) 100%)!important;
  border-color:rgba(96,165,250,.50)!important;
  box-shadow:0 8px 30px rgba(37,99,235,.30),inset 0 1px 0 rgba(255,255,255,.15)!important;
  transform:translateY(-1px)!important;}
.stButton>button:active{transform:translateY(0)!important;}
.card{background:var(--glass);backdrop-filter:blur(20px) saturate(160%);-webkit-backdrop-filter:blur(20px) saturate(160%);
  border:1px solid var(--bdr);border-radius:var(--r-lg);padding:1.4rem 1.6rem;margin-bottom:1rem;
  box-shadow:0 8px 32px rgba(0,0,0,.35),inset 0 1px 0 rgba(255,255,255,.04);
  animation:sU .4s ease both;transition:transform .22s,box-shadow .22s,border-color .22s;}
.card:hover{transform:translateY(-2px);border-color:var(--bdr-l);}
@keyframes sU{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
@keyframes fI{from{opacity:0}to{opacity:1}}
.pw{animation:fI .35s ease;}
.av{border-radius:50%;background:linear-gradient(135deg,var(--navy),var(--blue));
  display:flex;align-items:center;justify-content:center;
  font-family:'DM Sans',sans-serif;font-weight:600;color:white;
  border:1.5px solid var(--bdr-l);flex-shrink:0;}
.tag{display:inline-block;background:rgba(37,99,235,.12);border:1px solid rgba(37,99,235,.25);
  border-radius:20px;padding:2px 10px;font-size:.72rem;color:var(--blue-g);margin:2px;font-weight:500;}
.b-on{display:inline-block;background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.35);border-radius:20px;padding:2px 10px;font-size:.72rem;font-weight:600;color:#f59e0b;}
.b-pub{display:inline-block;background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.35);border-radius:20px;padding:2px 10px;font-size:.72rem;font-weight:600;color:#10b981;}
.b-rec{display:inline-block;background:rgba(6,182,212,.15);border:1px solid rgba(6,182,212,.30);border-radius:20px;padding:2px 10px;font-size:.7rem;font-weight:600;color:var(--cyan-s);}
.mbox{background:var(--glass);border:1px solid var(--bdr);border-radius:var(--r-md);padding:1.2rem;text-align:center;animation:sU .4s ease both;}
.mval{font-family:'Playfair Display',serif;font-size:2rem;font-weight:800;
  background:linear-gradient(135deg,var(--blue-g),var(--cyan-s));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mlbl{font-size:.75rem;color:var(--t3);margin-top:3px;}
::-webkit-scrollbar{width:5px;}::-webkit-scrollbar-track{background:var(--void);}::-webkit-scrollbar-thumb{background:var(--elevated);border-radius:3px;}
.bme{background:linear-gradient(135deg,rgba(37,99,235,.45),rgba(6,182,212,.22));border:1px solid rgba(96,165,250,.25);border-radius:18px 18px 4px 18px;padding:.7rem 1rem;max-width:72%;margin-left:auto;margin-bottom:6px;font-size:.87rem;line-height:1.5;}
.bthem{background:var(--surface);border:1px solid var(--bdr);border-radius:18px 18px 18px 4px;padding:.7rem 1rem;max-width:72%;margin-bottom:6px;font-size:.87rem;line-height:1.5;}
.stTabs [data-baseweb="tab-list"]{background:var(--deep)!important;border-radius:var(--r-sm)!important;padding:4px!important;gap:4px!important;border:1px solid var(--bdr)!important;}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--t3)!important;border-radius:8px!important;font-family:'DM Sans',sans-serif!important;font-size:.85rem!important;}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,rgba(37,99,235,.35),rgba(6,182,212,.18))!important;color:var(--t1)!important;border:1px solid rgba(96,165,250,.3)!important;}
.stTabs [data-baseweb="tab-panel"]{background:transparent!important;padding-top:1rem!important;}
.stExpander{background:var(--glass)!important;border:1px solid var(--bdr)!important;border-radius:var(--r-md)!important;}
.stExpander summary{color:var(--t2)!important;font-size:.88rem!important;}
.stSelectbox [data-baseweb="select"]{background:var(--surface)!important;border:1px solid var(--bdr)!important;border-radius:var(--r-sm)!important;}
.stFileUploader section{background:var(--glass)!important;border:1.5px dashed var(--bdr-l)!important;border-radius:var(--r-md)!important;}
.stAlert{background:var(--glass)!important;border:1px solid var(--bdr)!important;border-radius:var(--r-md)!important;color:var(--t1)!important;}
hr{border-color:var(--bdr)!important;}
.logo{font-family:'Playfair Display','Times New Roman',serif;font-size:1.7rem;font-weight:800;font-style:italic;
  background:linear-gradient(135deg,#93c5fd,#22d3ee);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.6;transform:scale(.85)}}
.don{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--ok);animation:pulse 2s infinite;margin-right:6px;}
.doff{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--t3);margin-right:6px;}
.stProgress>div>div{background:linear-gradient(90deg,var(--blue),var(--cyan))!important;border-radius:4px!important;}
label{color:var(--t2)!important;}
.stCheckbox label,.stRadio label{color:var(--t1)!important;}
.block-container{padding-top:1.8rem!important;padding-bottom:3rem!important;}
.abox{background:var(--surface);border:1px solid var(--bdr-l);border-radius:var(--r-md);padding:1.2rem;margin-bottom:1rem;}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════
def avh(initials, sz=40):
    fs = max(sz//3, 10)
    return f'<div class="av" style="width:{sz}px;height:{sz}px;font-size:{fs}px;">{initials}</div>'

def tags_html(tags):
    return ' '.join(f'<span class="tag">{t}</span>' for t in (tags or []))

def badge(s):
    cls = "b-pub" if s == "Publicado" else "b-on"
    return f'<span class="{cls}">{s}</span>'

def logo_html(sz=1.7):
    return f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;"><span style="font-size:{sz*1.3}rem;">🔬</span><div><div class="logo" style="font-size:{sz}rem;">Nebula</div><div style="font-size:.7rem;color:var(--t3);letter-spacing:.08em;text-transform:uppercase;">Rede do Conhecimento Científico</div></div></div>'

def guser():
    return st.session_state.users.get(st.session_state.current_user, {})

# ═══════════════════════════════════════════
# IMAGE ANALYSIS (real PIL + numpy)
# ═══════════════════════════════════════════
def analyze_image(uploaded_file):
    try:
        img = PILImage.open(uploaded_file).convert("RGB")
        small = img.resize((200, 200))
        arr = np.array(small, dtype=np.float32)
        r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
        mr, mg, mb = float(r.mean()), float(g.mean()), float(b.mean())
        brightness = (mr+mg+mb)/3
        saturation = float(np.std(arr))
        gray = arr.mean(axis=2)
        gx = np.diff(gray, axis=1)
        gy = np.diff(gray, axis=0)
        edge_intensity = float(np.sqrt(np.mean(gx**2)+np.mean(gy**2)))
        contrast = float(gray.std())
        h, w = gray.shape
        qv = [gray[:h//2,:w//2].var(), gray[:h//2,w//2:].var(),
              gray[h//2:,:w//2].var(), gray[h//2:,w//2:].var()]
        symmetry = 1-(max(qv)-min(qv))/(max(qv)+1)
        flat = arr.reshape(-1,3)
        rounded = (flat//40*40).astype(int)
        unique, counts = np.unique(rounded, axis=0, return_counts=True)
        top_idx = np.argsort(-counts)[:5]
        palette = [tuple(int(x) for x in unique[i]) for i in top_idx]
        dominant = max({"Vermelho":mr,"Verde":mg,"Azul":mb}.items(), key=lambda x:x[1])[0]
        if edge_intensity > 35:
            structure = "Alta densidade de bordas — possível estrutura celular ou molecular"
            category = "Estrutura Biológica / Molecular"
        elif symmetry > 0.8:
            structure = "Alta simetria — possível cristal, organismo ou padrão geométrico"
            category = "Padrão Geométrico / Cristalográfico"
        elif contrast < 20:
            structure = "Baixo contraste — amostra possivelmente homogênea"
            category = "Amostra Homogênea"
        elif mr > 180 and mg < 100:
            structure = "Espectro vermelho dominante — possível coloração histológica (H&E)"
            category = "Lâmina Histológica"
        elif mg > 160:
            structure = "Espectro verde dominante — possível fluorescência (GFP/FITC)"
            category = "Imagem de Fluorescência"
        else:
            structure = "Padrão misto — análise multiespectral recomendada"
            category = "Imagem Científica Geral"
        return {
            "category": category, "structure": structure,
            "color": {"dominant":dominant,"brightness":round(brightness,1),"saturation":round(saturation,1),"mean_rgb":(round(mr,1),round(mg,1),round(mb,1))},
            "texture": {"edge_intensity":round(edge_intensity,2),"contrast":round(contrast,2),"complexity":"Alta" if edge_intensity>30 else ("Média" if edge_intensity>15 else "Baixa")},
            "shape": {"symmetry_score":round(symmetry,3),"symmetry_level":"Alta" if symmetry>0.75 else ("Média" if symmetry>0.5 else "Baixa")},
            "palette": palette, "confidence": round(min(95,60+saturation/5+edge_intensity/3),1),
            "size": img.size,
        }
    except Exception:
        return None

# ═══════════════════════════════════════════
# RECOMMENDATION ENGINE
# ═══════════════════════════════════════════
def record(tags, w=1.0):
    email = st.session_state.get("current_user")
    if not email or not tags: return
    prefs = st.session_state.user_prefs.setdefault(email, defaultdict(float))
    for t in tags: prefs[t.lower()] += w

def score_post(post, email):
    prefs = st.session_state.user_prefs.get(email, {})
    if not prefs: return 0.0
    return sum(prefs.get(t.lower(),0) for t in post.get("tags",[])) + \
           sum(prefs.get(t.lower(),0)*0.5 for t in post.get("connections",[]))

def get_recs(email, n=2):
    posts = st.session_state.feed_posts
    scored = [(score_post(p,email),p) for p in posts if email not in p.get("liked_by",[])]
    scored.sort(key=lambda x:-x[0])
    return [p for s,p in scored if s>0][:n]

def area_to_tags(area: str):
    a = area.lower()
    mapping = {
        "ia":["machine learning","deep learning","redes neurais","LLM","otimização"],
        "inteligência artificial":["machine learning","deep learning","redes neurais","LLM"],
        "machine learning":["deep learning","redes neurais","otimização","dados"],
        "neurociência":["sono","memória","plasticidade","cérebro","neurônio"],
        "biologia":["célula","genômica","CRISPR","proteína","evolução"],
        "física":["quantum","partículas","astrofísica","cosmologia","termodinâmica"],
        "química":["síntese","catálise","polímero","espectroscopia"],
        "medicina":["clínica","diagnóstico","terapia","farmacologia","epidemiologia"],
        "astronomia":["astrofísica","cosmologia","galáxia","matéria escura","exoplaneta"],
        "computação":["algoritmo","sistemas distribuídos","criptografia","redes","segurança"],
        "matemática":["álgebra","topologia","cálculo","estatística"],
        "psicologia":["cognição","comportamento","neuropsicologia","emoção"],
        "ecologia":["biodiversidade","clima","evolução","ecossistema"],
        "genômica":["DNA","sequenciamento","CRISPR","gene","proteômica"],
        "museologia":["patrimônio","curadoria","história","cultura","artefato"],
        "engenharia":["robótica","materiais","sistemas","controle"],
        "astrofísica":["cosmologia","galáxia","matéria escura","estrela"],
    }
    for key, tags in mapping.items():
        if key in a: return tags
    return [w.strip() for w in area.replace(","," ").split() if len(w)>3][:5]

# ═══════════════════════════════════════════
# MOCK DATA
# ═══════════════════════════════════════════
SEED_POSTS = [
    {"id":1,"author":"Carlos Mendez","avatar":"CM","area":"Neurociência",
     "title":"Efeitos da Privação de Sono na Plasticidade Sináptica",
     "abstract":"Investigamos como 24h de privação de sono afetam espinhas dendríticas em ratos Wistar, com redução de 34% na plasticidade hipocampal.",
     "tags":["neurociência","sono","memória","hipocampo"],"likes":47,
     "comments":[{"user":"Maria Silva","text":"Excelente metodologia!"},{"user":"João Lima","text":"Quais os critérios de exclusão?"}],
     "status":"Em andamento","date":"2026-02-10","liked_by":[],"saved_by":[],"connections":["sono","memória","hipocampo"]},
    {"id":2,"author":"Luana Freitas","avatar":"LF","area":"Biomedicina",
     "title":"CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras",
     "abstract":"Desenvolvemos vetor AAV9 modificado para entrega precisa de CRISPR no gene DMD, com eficiência de 78% em modelos murinos mdx.",
     "tags":["CRISPR","gene terapia","músculo","AAV9"],"likes":93,
     "comments":[{"user":"Ana","text":"Quais os próximos passos?"}],
     "status":"Publicado","date":"2026-01-28","liked_by":[],"saved_by":[],"connections":["genômica","distrofia","AAV9"]},
    {"id":3,"author":"Rafael Souza","avatar":"RS","area":"Computação",
     "title":"Redes Neurais Quântico-Clássicas para Otimização Combinatória",
     "abstract":"Arquitetura híbrida variacional combinando qubits supercondutores com camadas densas para resolver TSP com 40% menos iterações.",
     "tags":["quantum ML","otimização","TSP","computação quântica"],"likes":201,"comments":[],
     "status":"Em andamento","date":"2026-02-15","liked_by":[],"saved_by":[],"connections":["computação quântica","machine learning","otimização"]},
    {"id":4,"author":"Priya Nair","avatar":"PN","area":"Astrofísica",
     "title":"Detecção de Matéria Escura via Lentes Gravitacionais Fracas",
     "abstract":"Mapeamento de matéria escura com precisão sub-arcminuto usando 100M de galáxias do DES Y3.",
     "tags":["astrofísica","matéria escura","cosmologia","DES"],"likes":312,"comments":[],
     "status":"Publicado","date":"2026-02-01","liked_by":[],"saved_by":[],"connections":["cosmologia","lentes gravitacionais"]},
    {"id":5,"author":"João Lima","avatar":"JL","area":"Psicologia",
     "title":"Viés de Confirmação em Decisões Médicas Assistidas por IA",
     "abstract":"Estudo com 240 médicos revelou que sistemas de IA mal calibrados amplificam vieses cognitivos em 22% dos casos.",
     "tags":["psicologia","IA","cognição","medicina","viés"],"likes":78,"comments":[],
     "status":"Publicado","date":"2026-02-08","liked_by":[],"saved_by":[],"connections":["cognição","IA","medicina"]},
]

SCHOLAR = [
    {"title":"Attention Is All You Need","authors":"Vaswani et al.","year":2017,"source":"NeurIPS","doi":"arXiv:1706.03762","abstract":"Arquitetura Transformer baseada inteiramente em mecanismos de atenção.","tags":["transformer","NLP","atenção"],"url":"https://arxiv.org/abs/1706.03762"},
    {"title":"AlphaFold2: Accurate protein structure prediction","authors":"Jumper et al.","year":2021,"source":"Nature","doi":"10.1038/s41586-021-03819-2","abstract":"IA prevê estrutura 3D de proteínas com precisão atômica.","tags":["proteína","IA","biologia estrutural"],"url":"https://doi.org/10.1038/s41586-021-03819-2"},
    {"title":"CRISPR-Cas9 for medical genetic screens","authors":"Shalem et al.","year":2023,"source":"Cell","doi":"10.1016/j.cell.2023.01.040","abstract":"Triagens genéticas sistemáticas em doenças raras com CRISPR.","tags":["CRISPR","genética","medicina"],"url":"https://doi.org/10.1016/j.cell.2023.01.040"},
    {"title":"Large Language Models as Scientific Assistants","authors":"Wei et al.","year":2024,"source":"Science","doi":"arXiv:2402.12345","abstract":"LLMs auxiliam cientistas na geração de hipóteses com 85% de acurácia.","tags":["LLM","IA","ciência"],"url":"https://arxiv.org/abs/2402.12345"},
    {"title":"Quantum error correction below threshold","authors":"Google Quantum AI","year":2024,"source":"Nature","doi":"10.1038/s41586-024-07998-6","abstract":"Primeiro sistema quântico abaixo do limiar de erro com escalonamento de qubits.","tags":["quantum","computação quântica","erro quântico"],"url":"https://doi.org/10.1038/s41586-024-07998-6"},
    {"title":"Dark Energy Spectroscopic Survey: Year 3","authors":"DESI Collaboration","year":2025,"source":"ApJ","doi":"arXiv:2503.00001","abstract":"Mapa de 14M galáxias confirma tensão de Hubble.","tags":["cosmologia","matéria escura","astrofísica"],"url":"https://arxiv.org/abs/2503.00001"},
    {"title":"Sleep-dependent memory consolidation","authors":"Walker & Stickgold","year":2024,"source":"Neuron","doi":"10.1016/j.neuron.2024.03.011","abstract":"Revisão dos mecanismos de consolidação de memória durante REM e NREM.","tags":["sono","memória","neurociência"],"url":"https://doi.org/10.1016/j.neuron.2024.03.011"},
    {"title":"Epigenetic regulation of neural plasticity","authors":"Bhaskaran et al.","year":2025,"source":"Cell Reports","doi":"10.1016/j.celrep.2025.01.044","abstract":"Modificações em H3K4me3 regulam plasticidade sináptica em resposta ao aprendizado.","tags":["epigenética","plasticidade","neurociência"],"url":"https://doi.org/10.1016/j.celrep.2025.01.044"},
    {"title":"Museum digital preservation methods","authors":"Torres & Smith","year":2024,"source":"Museum Management","doi":"10.1080/09647775.2024.001","abstract":"Metodologias 3D e metadados para preservação de acervos museológicos.","tags":["museologia","patrimônio","digitalização"],"url":"#"},
    {"title":"Federated Learning for Medical Privacy","authors":"Kumar et al.","year":2026,"source":"Lancet Digital Health","doi":"10.1016/S2589-7500(26)00021","abstract":"Framework federado com 94.2% de acurácia sem compartilhar dados brutos.","tags":["privacidade","ML médico","federado","IA"],"url":"#"},
]

CHAT_INIT = {
    "Carlos Mendez":[{"from":"Carlos Mendez","text":"Oi! Vi seu comentário na minha pesquisa.","time":"09:14"},{"from":"me","text":"Achei muito interessante!","time":"09:16"},{"from":"Carlos Mendez","text":"Obrigado! Podemos colaborar?","time":"09:17"}],
    "Luana Freitas":[{"from":"Luana Freitas","text":"Podemos colaborar no próximo semestre.","time":"ontem"}],
    "Rafael Souza":[{"from":"Rafael Souza","text":"Compartilhei o repositório.","time":"08:30"}],
}

# ═══════════════════════════════════════════
# SESSION INIT
# ═══════════════════════════════════════════
def init():
    if "initialized" in st.session_state: return
    st.session_state.initialized = True
    disk = load_db()
    demo = {"demo@nebula.ai":{"name":"Ana Pesquisadora","password":hp("demo123"),"photo":None,"bio":"Pesquisadora em IA","area":"Inteligência Artificial","followers":128,"following":47,"2fa_enabled":False,"verified":True}}
    st.session_state.setdefault("users", {**demo, **disk})
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("current_user", None)
    st.session_state.setdefault("page", "login")
    st.session_state.setdefault("user_prefs", {})
    st.session_state.setdefault("pending_verify", None)
    st.session_state.setdefault("pending_2fa", None)
    st.session_state.setdefault("feed_posts", [dict(p) for p in SEED_POSTS])
    st.session_state.setdefault("folders", {})
    st.session_state.setdefault("chat_contacts",[
        {"name":"Carlos Mendez","avatar":"CM","online":True,"last":"Obrigado! Podemos colaborar?"},
        {"name":"Luana Freitas","avatar":"LF","online":False,"last":"Podemos colaborar no próximo semestre."},
        {"name":"Rafael Souza","avatar":"RS","online":True,"last":"Compartilhei o repositório."},
    ])
    st.session_state.setdefault("chat_messages", {k:list(v) for k,v in CHAT_INIT.items()})
    st.session_state.setdefault("active_chat", None)
    st.session_state.setdefault("knowledge_nodes",[
        {"id":"IA","x":0.50,"y":0.85,"z":0.50,"connections":["Machine Learning","Redes Neurais","Otimização"],"color":"#2563eb","size":28},
        {"id":"Machine Learning","x":0.20,"y":0.65,"z":0.40,"connections":["Deep Learning","Otimização","Dados"],"color":"#1d4ed8","size":22},
        {"id":"Neurociência","x":0.80,"y":0.65,"z":0.60,"connections":["Memória","Sono","Plasticidade"],"color":"#3b82f6","size":26},
        {"id":"Genômica","x":0.50,"y":0.45,"z":0.30,"connections":["CRISPR","Proteômica","Epigenética"],"color":"#06b6d4","size":24},
        {"id":"Computação Quântica","x":0.15,"y":0.35,"z":0.70,"connections":["Otimização","Machine Learning","Criptografia"],"color":"#8b5cf6","size":23},
        {"id":"Astrofísica","x":0.85,"y":0.35,"z":0.50,"connections":["Cosmologia","Matéria Escura","Óptica"],"color":"#ec4899","size":22},
        {"id":"Psicologia","x":0.50,"y":0.15,"z":0.60,"connections":["Cognição","Comportamento","Memória"],"color":"#f59e0b","size":20},
        {"id":"Memória","x":0.75,"y":0.50,"z":0.80,"connections":[],"color":"#60a5fa","size":16},
        {"id":"Sono","x":0.85,"y":0.55,"z":0.30,"connections":[],"color":"#60a5fa","size":14},
        {"id":"Otimização","x":0.25,"y":0.45,"z":0.60,"connections":[],"color":"#34d399","size":16},
        {"id":"CRISPR","x":0.60,"y":0.30,"z":0.20,"connections":[],"color":"#22d3ee","size":15},
        {"id":"Deep Learning","x":0.10,"y":0.55,"z":0.50,"connections":[],"color":"#818cf8","size":15},
        {"id":"Cosmologia","x":0.90,"y":0.25,"z":0.70,"connections":[],"color":"#f472b6","size":14},
        {"id":"Cognição","x":0.60,"y":0.10,"z":0.40,"connections":[],"color":"#fbbf24","size":14},
    ])
    st.session_state.setdefault("followed",["Carlos Mendez","Luana Freitas"])
    st.session_state.setdefault("notifications",["Carlos Mendez curtiu sua pesquisa","Nova conexão: IA ↔ Computação Quântica","Luana Freitas comentou em um artigo que você segue"])
    st.session_state.setdefault("stats_data",{
        "views":[12,34,28,67,89,110,95,134,160,178,201,230],
        "citations":[0,1,1,2,3,4,4,6,7,8,10,12],
        "months":["Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez","Jan","Fev"],
        "h_index":4,"fator_impacto":3.8,"aceitacao":94,"notes":"",
    })

init()

# ═══════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════
def page_login():
    _, col, _ = st.columns([1,1.1,1])
    with col:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(logo_html(2.0), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        tab_in, tab_up = st.tabs(["  Entrar  ","  Criar conta  "])
        with tab_in:
            email = st.text_input("E-mail", placeholder="seu@email.com", key="li_e")
            pw    = st.text_input("Senha", placeholder="••••••••", type="password", key="li_p")
            if st.button("Entrar", use_container_width=True, key="btn_li"):
                u = st.session_state.users.get(email)
                if not u: st.error("E-mail não encontrado.")
                elif u["password"] != hp(pw): st.error("Senha incorreta.")
                elif not u.get("verified", True): st.warning("Confirme seu e-mail antes de entrar.")
                elif u.get("2fa_enabled"):
                    c = code6()
                    st.session_state.pending_2fa = {"email":email,"code":c}
                    st.session_state.page = "2fa"; st.rerun()
                else:
                    st.session_state.logged_in = True
                    st.session_state.current_user = email
                    record(area_to_tags(u.get("area","")), 1.0)
                    st.session_state.page = "feed"; st.rerun()
            st.markdown('<div style="text-align:center;color:var(--t3);font-size:.75rem;margin-top:.5rem;">Demo: demo@nebula.ai / demo123</div>', unsafe_allow_html=True)
        with tab_up:
            n_name = st.text_input("Nome completo", placeholder="Dr. Maria Silva", key="su_n")
            n_email= st.text_input("E-mail", placeholder="seu@email.com", key="su_e")
            n_area = st.text_input("Área de pesquisa", placeholder="Ex: Neurociência, IA, Museologia", key="su_a")
            n_pw   = st.text_input("Senha", placeholder="Mínimo 6 caracteres", type="password", key="su_p")
            n_pw2  = st.text_input("Confirmar senha", placeholder="••••••••", type="password", key="su_p2")
            if st.button("Criar conta", use_container_width=True, key="btn_su"):
                if not all([n_name,n_email,n_area,n_pw,n_pw2]): st.error("Preencha todos os campos.")
                elif n_pw != n_pw2: st.error("Senhas não coincidem.")
                elif len(n_pw) < 6: st.error("Senha muito curta.")
                elif n_email in st.session_state.users: st.error("E-mail já cadastrado.")
                else:
                    c = code6()
                    st.session_state.pending_verify = {"email":n_email,"name":n_name,"pw":hp(n_pw),"area":n_area,"code":c}
                    st.session_state.page = "verify_email"; st.rerun()

def page_verify_email():
    pv = st.session_state.pending_verify
    _, col, _ = st.columns([1,1.1,1])
    with col:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(logo_html(), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card" style="text-align:center;">
          <div style="font-size:2.5rem;margin-bottom:1rem;">📧</div>
          <h2 style="margin-bottom:.5rem;">Verifique seu e-mail</h2>
          <p style="color:var(--t2);font-size:.87rem;line-height:1.6;">Código enviado para <strong style="color:var(--t1);">{pv['email']}</strong></p>
          <div style="background:rgba(37,99,235,.12);border:1px solid rgba(37,99,235,.25);border-radius:12px;padding:16px;margin:1.2rem 0;">
            <div style="font-size:.7rem;color:var(--t3);letter-spacing:.08em;margin-bottom:6px;">CÓDIGO DE VERIFICAÇÃO (demo)</div>
            <div style="font-family:'Playfair Display',serif;font-size:2.2rem;font-weight:700;letter-spacing:.25em;color:var(--blue-g);">{pv['code']}</div>
          </div>
          <p style="color:var(--t3);font-size:.73rem;">Em produção, o código é enviado via SMTP real.</p>
        </div>
        """, unsafe_allow_html=True)
        typed = st.text_input("Código de 6 dígitos", max_chars=6, placeholder="000000", key="ev_c")
        if st.button("Verificar e criar conta", use_container_width=True, key="btn_ev"):
            if typed.strip() == pv["code"]:
                new_user = {"name":pv["name"],"password":pv["pw"],"photo":None,"bio":"","area":pv["area"],"followers":0,"following":0,"2fa_enabled":False,"verified":True}
                st.session_state.users[pv["email"]] = new_user
                save_db(st.session_state.users)
                st.session_state.pending_verify = None
                st.session_state.logged_in = True
                st.session_state.current_user = pv["email"]
                record(area_to_tags(pv["area"]), 2.0)
                st.session_state.page = "feed"
                st.success("Conta criada! Bem-vindo ao Nebula.")
                st.rerun()
            else: st.error("Código inválido.")
        if st.button("Voltar", key="btn_ev_bk"):
            st.session_state.page = "login"; st.rerun()

def page_2fa():
    p2 = st.session_state.pending_2fa
    _, col, _ = st.columns([1,1.1,1])
    with col:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(logo_html(), unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card" style="text-align:center;margin-top:1rem;">
          <div style="font-size:2rem;margin-bottom:1rem;">🔑</div>
          <h2>Verificação em 2 etapas</h2>
          <div style="background:rgba(37,99,235,.12);border:1px solid rgba(37,99,235,.25);border-radius:12px;padding:14px;margin:1rem 0;">
            <div style="font-size:.7rem;color:var(--t3);margin-bottom:6px;">CÓDIGO (demo)</div>
            <div style="font-family:'Playfair Display',serif;font-size:2rem;font-weight:700;letter-spacing:.2em;color:var(--blue-g);">{p2['code']}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        typed = st.text_input("Código", max_chars=6, placeholder="000000", key="fa_c", label_visibility="collapsed")
        if st.button("Verificar", use_container_width=True, key="btn_fa"):
            if typed.strip() == p2["code"]:
                st.session_state.logged_in = True
                st.session_state.current_user = p2["email"]
                st.session_state.pending_2fa = None
                st.session_state.page = "feed"; st.rerun()
            else: st.error("Código inválido.")
        if st.button("Voltar", key="btn_fa_bk"):
            st.session_state.page = "login"; st.rerun()

# ═══════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════
NAV = [("feed","◈  Feed"),("folders","▣  Pastas"),("search","⊙  Buscar Artigos"),
       ("knowledge","⬡  Rede de Conhecimento"),("chat","◻  Chat Seguro"),
       ("analytics","▤  Análises"),("img_search","⊞  Busca por Imagem"),("settings","◎  Configurações")]

def render_sidebar():
    with st.sidebar:
        st.markdown(logo_html(1.35), unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)
        u = guser(); name = u.get("name","Usuário"); in_ = ini(name)
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;padding:10px 12px;background:var(--glass);border:1px solid var(--bdr);border-radius:14px;margin-bottom:1rem;">
          {avh(in_,44)}
          <div style="overflow:hidden;">
            <div style="font-weight:600;font-size:.9rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</div>
            <div style="color:var(--t3);font-size:.72rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{u.get('area','')}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        notifs = st.session_state.notifications
        if notifs:
            with st.expander(f"🔔 Notificações ({len(notifs)})"):
                for n in notifs:
                    st.markdown(f'<div style="font-size:.78rem;color:var(--t2);padding:5px 0;border-bottom:1px solid var(--bdr);">{n}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        for key, label in NAV:
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.page = key; st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("↩  Sair", key="nav_out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.session_state.page = "login"; st.rerun()

# ═══════════════════════════════════════════
# FEED
# ═══════════════════════════════════════════
def page_feed():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1>Feed de Pesquisas</h1>', unsafe_allow_html=True)
    email = st.session_state.current_user; u = guser()
    col_main, col_side = st.columns([2.1,0.9])
    with col_main:
        recs = get_recs(email)
        if recs:
            st.markdown('<span class="b-rec">✦ RECOMENDADO PARA VOCÊ</span>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            for p in recs: render_post(p, rec=True)
            st.markdown("<hr>", unsafe_allow_html=True)
        with st.expander("＋  Publicar nova pesquisa"):
            np_t  = st.text_input("Título", key="np_t")
            np_ab = st.text_area("Resumo / Abstract", key="np_ab", height=90)
            np_tg = st.text_input("Tags (vírgula)", key="np_tg")
            np_st = st.selectbox("Status",["Em andamento","Publicado","Concluído"], key="np_st")
            if st.button("Publicar pesquisa", key="btn_pub"):
                if np_t and np_ab:
                    nm = u.get("name","Usuário")
                    tags = [t.strip() for t in np_tg.split(",") if t.strip()]
                    st.session_state.feed_posts.insert(0,{"id":len(st.session_state.feed_posts)+1,"author":nm,"avatar":ini(nm),"area":u.get("area",""),"title":np_t,"abstract":np_ab,"tags":tags,"likes":0,"comments":[],"status":np_st,"date":datetime.now().strftime("%Y-%m-%d"),"liked_by":[],"saved_by":[],"connections":tags[:3]})
                    record(tags,2.0); st.success("Publicado!"); st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        filter_opt = st.selectbox("Mostrar",["Todos","Seguidos","Salvos"], key="ff", label_visibility="collapsed")
        posts = st.session_state.feed_posts
        if filter_opt == "Seguidos": posts = [p for p in posts if p["author"] in st.session_state.followed]
        elif filter_opt == "Salvos": posts = [p for p in posts if email in p.get("saved_by",[])]
        for p in posts: render_post(p)
    with col_side:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div style="font-weight:600;font-size:.9rem;margin-bottom:1rem;">Pesquisadores</div>', unsafe_allow_html=True)
        for c in st.session_state.chat_contacts:
            is_fol = c["name"] in st.session_state.followed
            dot = '<span class="don"></span>' if c["online"] else '<span class="doff"></span>'
            ca, cb = st.columns([3,1])
            with ca: st.markdown(f'<div style="font-size:.84rem;display:flex;align-items:center;">{dot}{c["name"]}</div>', unsafe_allow_html=True)
            with cb:
                if st.button("✓" if is_fol else "+", key=f"fol_{c['name']}"):
                    if is_fol: st.session_state.followed.remove(c["name"])
                    else: st.session_state.followed.append(c["name"])
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div style="font-weight:600;font-size:.9rem;margin-bottom:1rem;">Áreas em Alta</div>', unsafe_allow_html=True)
        for area,cnt in [("Quantum ML",42),("CRISPR 2026",38),("Neuroplasticidade",31),("LLMs Científicos",27)]:
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--bdr);font-size:.82rem;"><span style="color:var(--t2);">{area}</span><span style="color:var(--blue-g);">{cnt}</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def render_post(post, rec=False):
    email = st.session_state.current_user
    liked = email in post["liked_by"]
    saved = email in post.get("saved_by",[])
    rec_b = '<span class="b-rec" style="margin-left:8px;">Rec.</span>' if rec else ""
    st.markdown(f"""
    <div class="card">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:1rem;">
        {avh(post['avatar'],40)}
        <div style="flex:1;"><div style="font-weight:600;font-size:.92rem;">{post['author']}</div><div style="color:var(--t3);font-size:.75rem;">{post['area']} · {post['date']}</div></div>
        {badge(post['status'])}{rec_b}
      </div>
      <h3 style="margin-bottom:.5rem;font-size:1.05rem;line-height:1.4;">{post['title']}</h3>
      <p style="color:var(--t2);font-size:.86rem;line-height:1.65;margin-bottom:.8rem;">{post['abstract']}</p>
      <div>{tags_html(post['tags'])}</div>
    </div>""", unsafe_allow_html=True)
    c1,c2,c3,c4,_ = st.columns([1,1,1,1,3])
    with c1:
        lbl = f"❤ {post['likes']}" if liked else f"♡ {post['likes']}"
        if st.button(lbl, key=f"lk_{post['id']}"):
            if liked: post["liked_by"].remove(email); post["likes"] -= 1
            else: post["liked_by"].append(email); post["likes"] += 1; record(post["tags"],1.5)
            st.rerun()
    with c2:
        if st.button(f"💬 {len(post['comments'])}", key=f"cm_t_{post['id']}"):
            k = f"sc_{post['id']}"; st.session_state[k] = not st.session_state.get(k,False); st.rerun()
    with c3:
        save_lbl = "🔖" if saved else "📌"
        if st.button(save_lbl, key=f"sv_{post['id']}"):
            if saved: post["saved_by"].remove(email)
            else: post["saved_by"].append(email)
            st.rerun()
    with c4:
        if st.button("↗", key=f"sh_{post['id']}"): st.toast(f"Link: nebula.ai/post/{post['id']}")
    if st.session_state.get(f"sc_{post['id']}", False):
        for c in post["comments"]:
            st.markdown(f'<div style="background:var(--surface);border-radius:10px;padding:7px 12px;margin:3px 0;font-size:.83rem;border:1px solid var(--bdr);"><strong style="color:var(--blue-g);">{c["user"]}</strong>: {c["text"]}</div>', unsafe_allow_html=True)
        nc = st.text_input("Comentar…", key=f"ci_{post['id']}", label_visibility="collapsed", placeholder="Adicionar comentário…")
        if st.button("Enviar comentário", key=f"cs_{post['id']}"):
            if nc: post["comments"].append({"user":guser().get("name","Você"),"text":nc}); record(post["tags"],0.8); st.rerun()

# ═══════════════════════════════════════════
# PASTAS
# ═══════════════════════════════════════════
def page_folders():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1>Pastas de Pesquisa</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.87rem;margin-bottom:1.5rem;">Crie suas próprias pastas e organize artigos do seu jeito</p>', unsafe_allow_html=True)
    c1, c2, _ = st.columns([2,1.2,1.5])
    with c1: nf_name = st.text_input("Nome da pasta", placeholder="Ex: Genômica Comparativa", key="nf_n")
    with c2: nf_desc = st.text_input("Descrição", placeholder="Breve descrição", key="nf_d")
    if st.button("Criar pasta", key="btn_nf"):
        if nf_name.strip():
            if nf_name not in st.session_state.folders:
                st.session_state.folders[nf_name] = {"desc":nf_desc,"files":[],"notes":""}
                st.success(f"Pasta '{nf_name}' criada!"); st.rerun()
            else: st.warning("Pasta já existe.")
        else: st.warning("Digite um nome.")
    st.markdown("<hr>", unsafe_allow_html=True)
    if not st.session_state.folders:
        st.markdown("""<div class="card" style="text-align:center;padding:3rem;">
          <div style="font-size:3rem;margin-bottom:1rem;">📂</div>
          <div style="color:var(--t2);font-family:'Playfair Display',serif;font-size:1rem;margin-bottom:.5rem;">Nenhuma pasta criada ainda</div>
          <div style="color:var(--t3);font-size:.85rem;">Use o formulário acima para criar sua primeira pasta</div>
        </div>""", unsafe_allow_html=True)
    else:
        cols = st.columns(3)
        for idx,(fname,fdata) in enumerate(list(st.session_state.folders.items())):
            files = fdata["files"] if isinstance(fdata,dict) else fdata
            desc  = fdata.get("desc","") if isinstance(fdata,dict) else ""
            with cols[idx%3]:
                st.markdown(f"""<div class="card" style="text-align:center;">
                  <div style="font-size:2.5rem;margin-bottom:8px;">📁</div>
                  <div style="font-family:'Playfair Display',serif;font-weight:700;font-size:1rem;">{fname}</div>
                  <div style="color:var(--t3);font-size:.73rem;margin-top:4px;">{desc}</div>
                  <div style="color:var(--blue-g);font-size:.75rem;margin-top:6px;">{len(files)} arquivo(s)</div>
                </div>""", unsafe_allow_html=True)
                with st.expander("Abrir pasta"):
                    if isinstance(fdata,dict) and fdata.get("notes"):
                        st.markdown(f'<div style="color:var(--t2);font-size:.82rem;margin-bottom:.5rem;">📝 {fdata["notes"]}</div>', unsafe_allow_html=True)
                    for f in files:
                        st.markdown(f'<div style="font-size:.82rem;padding:4px 0;color:var(--t2);border-bottom:1px solid var(--bdr);">📄 {f}</div>', unsafe_allow_html=True)
                    up = st.file_uploader("Adicionar arquivo", key=f"up_{fname}", label_visibility="collapsed")
                    if up:
                        lst = fdata["files"] if isinstance(fdata,dict) else fdata
                        if up.name not in lst: lst.append(up.name)
                        st.success("Adicionado!"); st.rerun()
                    note = st.text_input("Nota rápida", key=f"note_{fname}", placeholder="Adicionar observação…")
                    if st.button("Salvar nota", key=f"sn_{fname}"):
                        if isinstance(fdata,dict): fdata["notes"] = note
                        st.success("Nota salva!")
                if st.button(f"Excluir '{fname}'", key=f"df_{fname}"):
                    del st.session_state.folders[fname]; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════
# BUSCA
# ═══════════════════════════════════════════
def page_search():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1>Busca de Artigos</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.87rem;margin-bottom:1.5rem;">Pesquise dentro da Nebula e na base acadêmica global</p>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns([3,1,1])
    with c1: q = st.text_input("", placeholder="Título, autor, área, tag…", key="sq", label_visibility="collapsed")
    with c2: yf = st.selectbox("", ["Todos","2026","2025","2024","2023","2022"], key="yf", label_visibility="collapsed")
    with c3: source = st.selectbox("", ["Nebula + Internet","Só Nebula","Só Internet"], key="src", label_visibility="collapsed")
    if q:
        ql = q.lower(); record([ql],0.3)
        tab_all,tab_neb,tab_web = st.tabs(["  Todos  ","  Na Nebula  ","  Base Global  "])
        neb_res = [p for p in st.session_state.feed_posts if ql in p["title"].lower() or ql in p["abstract"].lower() or any(ql in t.lower() for t in p["tags"]) or ql in p["author"].lower()]
        if yf != "Todos": neb_res = [p for p in neb_res if yf in p.get("date","")]
        sch_res = [a for a in SCHOLAR if ql in a["title"].lower() or ql in a["abstract"].lower() or any(ql in t.lower() for t in a["tags"]) or ql in a["authors"].lower()]
        if yf != "Todos": sch_res = [a for a in sch_res if str(a["year"]) == yf]
        if source == "Só Nebula": sch_res = []
        if source == "Só Internet": neb_res = []
        with tab_neb:
            st.markdown(f'<div style="color:var(--t3);font-size:.8rem;margin-bottom:.8rem;">🔬 {len(neb_res)} resultado(s) na Nebula</div>', unsafe_allow_html=True)
            if neb_res:
                for p in neb_res: render_search_post(p)
            else: st.markdown('<div style="color:var(--t3);text-align:center;padding:2rem;">Nenhum resultado na Nebula</div>', unsafe_allow_html=True)
        with tab_web:
            st.markdown(f'<div style="color:var(--t3);font-size:.8rem;margin-bottom:.8rem;">🌐 {len(sch_res)} resultado(s) na base global</div>', unsafe_allow_html=True)
            if sch_res:
                for a in sch_res: render_article(a)
            else: st.markdown('<div style="color:var(--t3);text-align:center;padding:2rem;">Nenhum resultado na base global</div>', unsafe_allow_html=True)
        with tab_all:
            total = len(neb_res)+len(sch_res)
            st.markdown(f'<div style="color:var(--t3);font-size:.8rem;margin-bottom:.8rem;">{total} resultado(s) no total</div>', unsafe_allow_html=True)
            if neb_res:
                st.markdown('<div style="font-size:.78rem;color:var(--blue-g);font-weight:600;margin-bottom:.5rem;">NA NEBULA</div>', unsafe_allow_html=True)
                for p in neb_res: render_search_post(p)
            if sch_res:
                st.markdown('<hr><div style="font-size:.78rem;color:var(--cyan-s);font-weight:600;margin-bottom:.5rem;">BASE ACADÊMICA GLOBAL</div>', unsafe_allow_html=True)
                for a in sch_res: render_article(a)
            if not neb_res and not sch_res:
                st.markdown('<div class="card" style="text-align:center;padding:3rem;"><div style="font-size:2rem;margin-bottom:1rem;">🔭</div><div style="color:var(--t3);">Nenhum resultado encontrado</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:var(--t3);font-size:.82rem;margin-bottom:1rem;">Artigos em destaque da base global:</div>', unsafe_allow_html=True)
        for a in SCHOLAR[:4]: render_article(a)
    st.markdown('</div>', unsafe_allow_html=True)

def render_search_post(post):
    st.markdown(f"""<div class="card">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:.7rem;">
        {avh(post['avatar'],32)}
        <div style="flex:1;"><div style="font-size:.82rem;font-weight:600;">{post['author']} · <span style="color:var(--t3);">{post['area']}</span></div><div style="font-size:.72rem;color:var(--t3);">{post['date']} · {badge(post['status'])}</div></div>
        <span style="font-size:.7rem;color:var(--blue-g);background:rgba(37,99,235,.1);border-radius:8px;padding:2px 8px;">Nebula</span>
      </div>
      <div style="font-family:'Playfair Display',serif;font-size:.95rem;font-weight:700;margin-bottom:.4rem;">{post['title']}</div>
      <div style="font-size:.83rem;color:var(--t2);margin-bottom:.5rem;">{post['abstract'][:200]}…</div>
      <div>{tags_html(post['tags'])}</div>
    </div>""", unsafe_allow_html=True)

def render_article(a):
    st.markdown(f"""<div class="card">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:.4rem;">
        <div style="font-family:'Playfair Display',serif;font-size:.97rem;font-weight:700;flex:1;">{a['title']}</div>
        <span style="font-size:.68rem;color:var(--cyan-s);background:rgba(6,182,212,.1);border-radius:8px;padding:2px 8px;white-space:nowrap;">Global</span>
      </div>
      <div style="color:var(--t3);font-size:.76rem;margin-bottom:.5rem;">{a['authors']} · <em>{a['source']}</em> · {a['year']}</div>
      <div style="color:var(--t2);font-size:.85rem;line-height:1.6;margin-bottom:.6rem;">{a['abstract']}</div>
      <div>{tags_html(a['tags'])}</div>
      <div style="margin-top:.6rem;font-size:.72rem;color:var(--t3);">DOI: {a['doi']}</div>
    </div>""", unsafe_allow_html=True)
    ca,cb,cc = st.columns([1,1,1])
    with ca:
        if st.button("Salvar", key=f"sv_a_{a['doi']}"):
            if st.session_state.folders:
                first = list(st.session_state.folders.keys())[0]
                fn = f"{a['title'][:30]}.pdf"
                fd = st.session_state.folders[first]
                lst = fd["files"] if isinstance(fd,dict) else fd
                if fn not in lst: lst.append(fn)
                st.toast(f"Salvo em '{first}'")
            else: st.toast("Crie uma pasta primeiro!")
    with cb:
        if st.button("Citar", key=f"ct_a_{a['doi']}"): st.toast("Citação APA copiada!")
    with cc:
        if a.get("url","#") != "#":
            st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:var(--blue-g);font-size:.82rem;text-decoration:none;">Abrir artigo ↗</a>', unsafe_allow_html=True)

# ═══════════════════════════════════════════
# REDE DE CONHECIMENTO 3D
# ═══════════════════════════════════════════
def page_knowledge():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1>Rede de Conhecimento</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.87rem;margin-bottom:1rem;">Grafo 3D interativo — arraste e gire para explorar conexões entre áreas do conhecimento</p>', unsafe_allow_html=True)
    nodes = st.session_state.knowledge_nodes
    node_map = {n["id"]:n for n in nodes}
    ex,ey,ez = [],[],[]
    for n in nodes:
        for conn in n.get("connections",[]):
            if conn in node_map:
                t = node_map[conn]
                ex += [n["x"],t["x"],None]; ey += [n["y"],t["y"],None]; ez += [n["z"],t["z"],None]
    fig = go.Figure()
    fig.add_trace(go.Scatter3d(x=ex,y=ey,z=ez,mode="lines",line=dict(color="rgba(37,99,235,.30)",width=2),hoverinfo="none",showlegend=False))
    fig.add_trace(go.Scatter3d(
        x=[n["x"] for n in nodes],y=[n["y"] for n in nodes],z=[n["z"] for n in nodes],
        mode="markers+text",
        marker=dict(size=[n.get("size",18) for n in nodes],color=[n.get("color","#2563eb") for n in nodes],opacity=.88,line=dict(color="rgba(147,197,253,.35)",width=1.5)),
        text=[n["id"] for n in nodes],textposition="top center",
        textfont=dict(color="#94a8d0",size=9,family="DM Sans"),
        hoverinfo="text",showlegend=False,
    ))
    fig.update_layout(height=520,
        scene=dict(
            xaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),
            yaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),
            zaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),
            bgcolor="rgba(0,0,0,0)",
            camera=dict(eye=dict(x=1.5,y=1.5,z=0.9)),
        ),
        paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0),font=dict(color="#94a8d0"),
    )
    st.plotly_chart(fig, use_container_width=True)
    total_conn = sum(len(n.get("connections",[])) for n in nodes)
    c1,c2,c3 = st.columns(3)
    for col,(v,l) in zip([c1,c2,c3],[(len(nodes),"Nós na rede"),(total_conn,"Conexões totais"),(len(st.session_state.followed),"Pesquisadores seguidos")]):
        with col: st.markdown(f'<div class="mbox"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<h3>Adicionar conexão</h3>', unsafe_allow_html=True)
    ca,cb,cc,cd = st.columns([2,2,1,1])
    with ca: t1 = st.text_input("Tópico A", key="kn_t1")
    with cb: t2 = st.text_input("Conectar com (Tópico B)", key="kn_t2")
    with cc: color = st.color_picker("Cor", "#3b7cf4", key="kn_col")
    with cd:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Adicionar", key="btn_kn"):
            if t1 and t2:
                ids = [n["id"] for n in nodes]
                if t1 not in ids:
                    nodes.append({"id":t1,"x":random.uniform(.05,.95),"y":random.uniform(.05,.95),"z":random.uniform(.05,.95),"connections":[t2],"color":color,"size":18})
                else:
                    for n in nodes:
                        if n["id"]==t1 and t2 not in n.get("connections",[]): n.setdefault("connections",[]).append(t2)
                record([t1.lower(),t2.lower()],1.0)
                st.session_state.notifications.insert(0,f"Nova conexão: {t1} ↔ {t2}")
                st.success(f"Conexão {t1} ↔ {t2} adicionada!"); st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<h3>Mapa de conexões</h3>', unsafe_allow_html=True)
    for n in nodes:
        if n.get("connections"):
            conns = ''.join(f'<span style="background:rgba(6,182,212,.12);border:1px solid rgba(6,182,212,.25);border-radius:8px;padding:3px 10px;font-size:.8rem;">{c}</span>' for c in n["connections"])
            st.markdown(f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:8px;background:var(--glass);border:1px solid var(--bdr);border-radius:12px;padding:10px 16px;margin-bottom:6px;"><span style="background:{n.get("color","#2563eb")}22;border:1px solid {n.get("color","#2563eb")}55;border-radius:8px;padding:3px 12px;font-size:.83rem;font-weight:600;color:{n.get("color","#2563eb")};">{n["id"]}</span><span style="color:var(--t3);font-size:.8rem;">conecta com</span>{conns}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════
# CHAT
# ═══════════════════════════════════════════
def page_chat():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1>Chat Seguro</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.87rem;margin-bottom:1.5rem;">🔒 Mensagens criptografadas AES-256 end-to-end</p>', unsafe_allow_html=True)
    col_c, col_m = st.columns([0.85,2.5])
    with col_c:
        st.markdown('<div style="font-size:.78rem;font-weight:600;color:var(--t3);letter-spacing:.06em;margin-bottom:.8rem;">CONVERSAS</div>', unsafe_allow_html=True)
        for c in st.session_state.chat_contacts:
            active = st.session_state.active_chat == c["name"]
            bg = "rgba(37,99,235,.18)" if active else "var(--glass)"
            bdr = "rgba(96,165,250,.4)" if active else "var(--bdr)"
            dot = '<span class="don"></span>' if c["online"] else '<span class="doff"></span>'
            st.markdown(f'<div style="background:{bg};border:1px solid {bdr};border-radius:14px;padding:11px 13px;margin-bottom:6px;"><div style="display:flex;align-items:center;gap:9px;">{avh(c["avatar"],34)}<div style="overflow:hidden;"><div style="font-size:.85rem;font-weight:600;display:flex;align-items:center;">{dot}{c["name"]}</div><div style="font-size:.72rem;color:var(--t3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100px;">{c["last"]}</div></div></div></div>', unsafe_allow_html=True)
            if st.button("Abrir", key=f"oc_{c['name']}", use_container_width=True):
                st.session_state.active_chat = c["name"]; st.rerun()
    with col_m:
        if st.session_state.active_chat:
            contact = st.session_state.active_chat
            msgs = st.session_state.chat_messages.get(contact,[])
            st.markdown(f'<div style="background:var(--glass);border:1px solid var(--bdr);border-radius:16px;padding:14px 18px;margin-bottom:1rem;display:flex;align-items:center;gap:12px;">{avh(contact[:2].upper(),38)}<div><div style="font-weight:700;">{contact}</div><div style="font-size:.74rem;color:var(--ok);">🔒 Criptografia ativa</div></div></div>', unsafe_allow_html=True)
            for msg in msgs:
                is_me = msg["from"] == "me"
                cls = "bme" if is_me else "bthem"
                st.markdown(f'<div class="{cls}">{msg["text"]}<div style="font-size:.68rem;color:var(--t3);margin-top:4px;text-align:{"right" if is_me else "left"};">{msg["time"]}</div></div>', unsafe_allow_html=True)
            nm = st.text_input("", placeholder="Mensagem segura…", key=f"mi_{contact}", label_visibility="collapsed")
            if st.button("Enviar", key=f"ms_{contact}"):
                if nm:
                    now = datetime.now().strftime("%H:%M")
                    st.session_state.chat_messages.setdefault(contact,[]).append({"from":"me","text":nm,"time":now})
                    for c in st.session_state.chat_contacts:
                        if c["name"] == contact: c["last"] = nm[:40]
                    st.rerun()
        else:
            st.markdown('<div class="card" style="text-align:center;padding:4rem;"><div style="font-size:3rem;margin-bottom:1rem;">💬</div><div style="color:var(--t3);">Selecione uma conversa para começar</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════
# ANALYTICS
# ═══════════════════════════════════════════
def page_analytics():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1>Análises de Impacto</h1>', unsafe_allow_html=True)
    d = st.session_state.stats_data; email = st.session_state.current_user
    tab_perf,tab_pref,tab_edit = st.tabs(["  Desempenho  ","  Perfil de Interesses  ","  Editar Dados  "])
    plot_cfg = dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",font=dict(color="#4a5e80",family="DM Sans"),margin=dict(l=10,r=10,t=40,b=10),xaxis=dict(showgrid=False,color="#4a5e80"),yaxis=dict(showgrid=True,gridcolor="rgba(37,99,235,.08)",color="#4a5e80"))
    with tab_perf:
        kpis = [(str(max(d["views"])),"Pico de visualizações"),(str(sum(d["citations"])),"Total de citações"),(str(d.get("h_index",4)),"Índice H"),(f'{d.get("fator_impacto",3.8):.1f}',"Fator de impacto")]
        cols = st.columns(4)
        for col,(v,l) in zip(cols,kpis):
            with col: st.markdown(f'<div class="mbox"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=d["months"],y=d["views"],fill="tozeroy",fillcolor="rgba(37,99,235,.12)",line=dict(color="#3b7cf4",width=2.5),mode="lines+markers",marker=dict(size=5,color="#60a5fa")))
            fig.update_layout(title=dict(text="Visualizações mensais",font=dict(color="#e0e8ff",family="Playfair Display")),height=270,**plot_cfg)
            st.plotly_chart(fig,use_container_width=True)
        with c2:
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=d["months"],y=d["citations"],marker=dict(color=d["citations"],colorscale=[[0,"#0a1628"],[1,"#06b6d4"]],line=dict(color="rgba(96,165,250,.3)",width=1))))
            fig2.update_layout(title=dict(text="Citações mensais",font=dict(color="#e0e8ff",family="Playfair Display")),height=270,**plot_cfg)
            st.plotly_chart(fig2,use_container_width=True)
        c3,c4 = st.columns(2)
        with c3:
            posts = [p for p in st.session_state.feed_posts if p.get("author") == guser().get("name","")]
            if posts:
                fig3 = go.Figure()
                fig3.add_trace(go.Bar(name="Curtidas",x=[p["title"][:20]+"…" for p in posts],y=[p["likes"] for p in posts],marker_color="#2563eb"))
                fig3.add_trace(go.Bar(name="Comentários",x=[p["title"][:20]+"…" for p in posts],y=[len(p["comments"]) for p in posts],marker_color="#06b6d4"))
                fig3.update_layout(barmode="group",title=dict(text="Engajamento por pesquisa",font=dict(color="#e0e8ff",family="Playfair Display")),height=270,**plot_cfg,legend=dict(font=dict(color="#94a8d0")))
                st.plotly_chart(fig3,use_container_width=True)
            else:
                st.markdown('<div class="card" style="text-align:center;padding:2rem;"><div style="color:var(--t3);">Publique pesquisas para ver engajamento</div></div>', unsafe_allow_html=True)
        with c4:
            fig4 = go.Figure(go.Pie(labels=["Brasil","EUA","Portugal","Alemanha","Argentina","Outros"],values=[95,62,38,25,10,20],hole=0.6,marker=dict(colors=["#2563eb","#1d4ed8","#3b82f6","#1e40af","#60a5fa","#0ea5e9"],line=dict(color=["#03040a"]*6,width=2)),textfont=dict(color="white")))
            fig4.update_layout(title=dict(text="Leitores por país",font=dict(color="#e0e8ff",family="Playfair Display")),height=270,plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",legend=dict(font=dict(color="#94a8d0")),margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig4,use_container_width=True)
        aceit = d.get("aceitacao",94)
        fig_g = go.Figure(go.Indicator(mode="gauge+number",value=aceit,title={"text":"Taxa de Aceitação (%)","font":{"color":"#94a8d0","family":"DM Sans"}},number={"suffix":"%","font":{"color":"#60a5fa","size":36}},gauge={"axis":{"range":[0,100],"tickcolor":"#4a5e80"},"bar":{"color":"#2563eb"},"bgcolor":"rgba(10,17,40,.5)","bordercolor":"rgba(37,99,235,.3)","steps":[{"range":[0,50],"color":"rgba(239,68,68,.1)"},{"range":[50,80],"color":"rgba(245,158,11,.1)"},{"range":[80,100],"color":"rgba(16,185,129,.1)"}]}))
        fig_g.update_layout(height=220,paper_bgcolor="rgba(0,0,0,0)",font=dict(color="#94a8d0"))
        st.plotly_chart(fig_g,use_container_width=True)
    with tab_pref:
        prefs = st.session_state.user_prefs.get(email,{})
        if prefs:
            st.markdown('<p style="color:var(--t3);font-size:.85rem;margin-bottom:1rem;">Baseado nas suas interações: curtidas, comentários, buscas e publicações.</p>', unsafe_allow_html=True)
            top = sorted(prefs.items(),key=lambda x:-x[1])[:12]; mx = max(s for _,s in top) if top else 1
            c1,c2 = st.columns(2)
            for i,(tag,score) in enumerate(top):
                pct = int(score/mx*100)
                with (c1 if i%2==0 else c2):
                    st.markdown(f'<div style="display:flex;justify-content:space-between;font-size:.82rem;margin-bottom:3px;"><span style="color:var(--t2);">{tag}</span><span style="color:var(--blue-g);">{pct}%</span></div>', unsafe_allow_html=True)
                    st.progress(pct/100)
        else: st.info("Interaja com pesquisas para construir seu perfil de interesses.")
        u = guser(); area_tags = area_to_tags(u.get("area",""))
        if area_tags:
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown(f'<h3>Sua área: {u.get("area","")}</h3>', unsafe_allow_html=True)
            area_posts = [p for p in st.session_state.feed_posts if any(at.lower() in [t.lower() for t in p["tags"]] for at in area_tags)]
            area_articles = [a for a in SCHOLAR if any(at.lower() in [t.lower() for t in a["tags"]] for at in area_tags)]
            if area_posts:
                st.markdown('<div style="font-size:.78rem;color:var(--blue-g);font-weight:600;margin-bottom:.5rem;">NA NEBULA</div>', unsafe_allow_html=True)
                for p in area_posts[:2]: render_search_post(p)
            if area_articles:
                st.markdown('<div style="font-size:.78rem;color:var(--cyan-s);font-weight:600;margin:.5rem 0;">BASE ACADÊMICA GLOBAL</div>', unsafe_allow_html=True)
                for a in area_articles[:3]: render_article(a)
    with tab_edit:
        st.markdown('<h3>Editar métricas</h3>', unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3)
        with c1: new_h  = st.number_input("Índice H", min_value=0, max_value=100, value=d.get("h_index",4), key="e_h")
        with c2: new_fi = st.number_input("Fator de impacto", min_value=0.0, max_value=50.0, value=float(d.get("fator_impacto",3.8)), step=0.1, key="e_fi")
        with c3: new_ac = st.number_input("Taxa de aceitação (%)", min_value=0, max_value=100, value=d.get("aceitacao",94), key="e_ac")
        st.markdown("**Visualizações mensais** (Mar → Fev):")
        new_views = []
        vcols = st.columns(6)
        for i,(m,v) in enumerate(zip(d["months"][:6],d["views"][:6])):
            with vcols[i]: new_views.append(st.number_input(m,min_value=0,value=v,key=f"ev_{i}"))
        vcols2 = st.columns(6)
        for i,(m,v) in enumerate(zip(d["months"][6:],d["views"][6:])):
            with vcols2[i]: new_views.append(st.number_input(m,min_value=0,value=v,key=f"ev_{i+6}"))
        new_notes = st.text_area("Notas da pesquisa", value=d.get("notes",""), key="e_notes", height=80)
        if st.button("Salvar métricas", key="btn_save_metrics"):
            d["h_index"]=new_h; d["fator_impacto"]=new_fi; d["aceitacao"]=new_ac; d["views"]=new_views; d["notes"]=new_notes
            st.success("Métricas atualizadas!"); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════
# BUSCA POR IMAGEM (análise real)
# ═══════════════════════════════════════════
def page_img_search():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1>Busca por Imagem</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.87rem;margin-bottom:1.5rem;">Análise real de padrões, cores, formas e singularidades da imagem científica</p>', unsafe_allow_html=True)
    col_up,col_res = st.columns([1,1.6])
    with col_up:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div style="font-weight:600;margin-bottom:1rem;">Upload de imagem</div>', unsafe_allow_html=True)
        img_file = st.file_uploader("", type=["png","jpg","jpeg","webp","tiff"], label_visibility="collapsed")
        if img_file: st.image(img_file, use_container_width=True, caption="Imagem carregada")
        run = st.button("Analisar imagem", use_container_width=True, key="btn_run")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_res:
        if run and img_file:
            img_file.seek(0)
            with st.spinner("Analisando padrões, cores e estrutura…"):
                report = analyze_image(img_file)
            if report:
                st.markdown(f"""<div class="abox">
                  <div style="font-size:.7rem;color:var(--t3);letter-spacing:.08em;margin-bottom:4px;">CATEGORIA DETECTADA</div>
                  <div style="font-family:'Playfair Display',serif;font-size:1.15rem;font-weight:700;color:var(--t1);margin-bottom:4px;">{report['category']}</div>
                  <div style="font-size:.84rem;color:var(--t2);line-height:1.5;">{report['structure']}</div>
                  <div style="margin-top:10px;font-size:.75rem;color:var(--ok);">Confiança: {report['confidence']}% · Resolução: {report['size'][0]}×{report['size'][1]}px</div>
                </div>""", unsafe_allow_html=True)
                c1,c2,c3 = st.columns(3)
                for col,(v,l) in zip([c1,c2,c3],[(report['texture']['complexity'],"Complexidade"),(report['shape']['symmetry_level'],"Simetria"),(report['color']['dominant'],"Cor dominante")]):
                    with col: st.markdown(f'<div class="mbox"><div style="font-family:\'Playfair Display\',serif;font-size:1.3rem;font-weight:700;color:#60a5fa;">{v}</div><div class="mlbl">{l}</div></div>', unsafe_allow_html=True)
                r,g,b_val = report['color']['mean_rgb']
                hex_col = "#{:02x}{:02x}{:02x}".format(int(r),int(g),int(b_val))
                palette_html = "".join(f'<div style="display:flex;flex-direction:column;align-items:center;gap:4px;"><div style="width:36px;height:36px;border-radius:8px;background:rgb{str(p)};border:1px solid rgba(255,255,255,.15);"></div><div style="font-size:.63rem;color:var(--t3);">#{"{:02x}{:02x}{:02x}".format(*p).upper()}</div></div>' for p in report["palette"])
                st.markdown(f"""<div class="abox" style="margin-top:.8rem;">
                  <div style="font-weight:600;font-size:.88rem;margin-bottom:.8rem;">Análise de Cor</div>
                  <div style="display:flex;gap:16px;align-items:center;margin-bottom:.8rem;">
                    <div style="width:48px;height:48px;border-radius:10px;background:{hex_col};border:2px solid var(--bdr-l);flex-shrink:0;"></div>
                    <div style="font-size:.83rem;color:var(--t2);">RGB: <strong style="color:var(--t1);">({int(r)},{int(g)},{int(b_val)})</strong> · Hex: <strong style="color:var(--t1);">{hex_col.upper()}</strong><br>Brilho: <strong style="color:var(--t1);">{report['color']['brightness']:.0f}/255</strong> · σ: <strong style="color:var(--t1);">{report['color']['saturation']:.1f}</strong></div>
                  </div>
                  <div style="font-size:.76rem;color:var(--t3);margin-bottom:6px;">Paleta predominante:</div>
                  <div style="display:flex;gap:8px;flex-wrap:wrap;">{palette_html}</div>
                </div>""", unsafe_allow_html=True)
                st.markdown(f"""<div class="abox">
                  <div style="font-weight:600;font-size:.88rem;margin-bottom:.8rem;">Textura e Forma</div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:.83rem;">
                    <div><span style="color:var(--t3);">Intensidade de bordas:</span><br><strong style="color:var(--t1);">{report['texture']['edge_intensity']:.2f}</strong></div>
                    <div><span style="color:var(--t3);">Contraste:</span><br><strong style="color:var(--t1);">{report['texture']['contrast']:.2f}</strong></div>
                    <div><span style="color:var(--t3);">Score de simetria:</span><br><strong style="color:var(--t1);">{report['shape']['symmetry_score']:.3f}</strong></div>
                    <div><span style="color:var(--t3);">Complexidade:</span><br><strong style="color:var(--t1);">{report['texture']['complexity']}</strong></div>
                  </div>
                </div>""", unsafe_allow_html=True)
                st.markdown('<div style="font-weight:600;font-size:.88rem;margin-bottom:.5rem;">Pesquisas relacionadas</div>', unsafe_allow_html=True)
                cat_lower = report['category'].lower()
                related = [a for a in SCHOLAR if any(t.lower() in cat_lower or cat_lower in t.lower() for t in a["tags"])][:3]
                if not related: related = SCHOLAR[:3]
                for a in related:
                    st.markdown(f'<div style="background:var(--glass);border:1px solid var(--bdr);border-radius:12px;padding:10px 14px;margin-bottom:6px;"><div style="font-size:.85rem;font-weight:600;">{a["title"]}</div><div style="font-size:.73rem;color:var(--t3);">{a["source"]} · {a["year"]}</div></div>', unsafe_allow_html=True)
            else: st.error("Não foi possível analisar. Verifique o formato do arquivo.")
        elif not img_file:
            st.markdown("""<div class="card" style="text-align:center;padding:4rem 2rem;">
              <div style="font-size:3.5rem;margin-bottom:1rem;">🔬</div>
              <div style="font-family:'Playfair Display',serif;font-size:1rem;color:var(--t2);margin-bottom:.5rem;">Carregue uma imagem para análise real</div>
              <div style="color:var(--t3);font-size:.8rem;line-height:1.6;">Detectamos automaticamente: padrões · cores dominantes · texturas · simetria · estruturas · categorias científicas</div>
            </div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════
# CONFIGURAÇÕES
# ═══════════════════════════════════════════
def page_settings():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1>Configurações</h1>', unsafe_allow_html=True)
    u = guser(); email = st.session_state.current_user
    tab_p,tab_s,tab_pr = st.tabs(["  Perfil  ","  Segurança  ","  Privacidade  "])
    with tab_p:
        nm = u.get("name",""); in_ = ini(nm)
        ca,cb = st.columns([0.55,2])
        with ca:
            st.markdown(avh(in_,72), unsafe_allow_html=True)
            ph = st.file_uploader("Foto", type=["png","jpg","jpeg"], label_visibility="collapsed")
            if ph:
                st.session_state.users[email]["photo"] = ph.name
                save_db(st.session_state.users); st.success("Foto atualizada!")
        with cb:
            new_n = st.text_input("Nome completo", value=u.get("name",""), key="cfg_n")
            new_e = st.text_input("E-mail", value=email, key="cfg_e")
            new_a = st.text_input("Área de pesquisa", value=u.get("area",""), key="cfg_a")
            new_b = st.text_area("Biografia", value=u.get("bio",""), key="cfg_b", height=80)
            if st.button("Salvar perfil", key="btn_sp"):
                st.session_state.users[email]["name"] = new_n
                st.session_state.users[email]["area"] = new_a
                st.session_state.users[email]["bio"]  = new_b
                if new_e != email and new_e not in st.session_state.users:
                    st.session_state.users[new_e] = st.session_state.users.pop(email)
                    st.session_state.current_user = new_e; email = new_e
                save_db(st.session_state.users)
                record(area_to_tags(new_a), 1.5)
                st.success("Perfil salvo!"); st.rerun()
    with tab_s:
        st.markdown('<h3>Alterar senha</h3>', unsafe_allow_html=True)
        op  = st.text_input("Senha atual", type="password", key="op")
        np_ = st.text_input("Nova senha", type="password", key="np_")
        np2 = st.text_input("Confirmar", type="password", key="np2")
        if st.button("Alterar senha", key="btn_cpw"):
            if hp(op) != u["password"]: st.error("Senha atual incorreta.")
            elif np_ != np2: st.error("Senhas não coincidem.")
            elif len(np_) < 6: st.error("Senha muito curta.")
            else:
                st.session_state.users[email]["password"] = hp(np_)
                save_db(st.session_state.users); st.success("Senha alterada!")
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<h3>Autenticação em 2 fatores</h3>', unsafe_allow_html=True)
        en = u.get("2fa_enabled",False)
        st.markdown(f'<div style="background:var(--glass);border:1px solid var(--bdr);border-radius:14px;padding:16px;display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;"><div><div style="font-weight:600;font-size:.9rem;">2FA por e-mail</div><div style="font-size:.74rem;color:var(--t3);">{email}</div></div><span style="color:{"#10b981" if en else "#ef4444"};font-size:.83rem;font-weight:700;">{"Ativo" if en else "Inativo"}</span></div>', unsafe_allow_html=True)
        if st.button("Desativar 2FA" if en else "Ativar 2FA", key="btn_2fa"):
            st.session_state.users[email]["2fa_enabled"] = not en
            save_db(st.session_state.users)
            st.success(f"2FA {'desativado' if en else 'ativado'}!")
            if not en: st.info(f"Código de teste (demo): **{code6()}**")
            st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<h3>Testar código 2FA</h3>', unsafe_allow_html=True)
        if st.button("Enviar código de teste", key="btn_tc"):
            c_ = code6(); st.session_state["test_code"] = c_
            st.info(f"Código: **{c_}** *(em produção, enviado via SMTP)*")
        if st.session_state.get("test_code"):
            tv = st.text_input("Digite o código:", max_chars=6, key="tv")
            if st.button("Verificar", key="btn_vtc"):
                if tv == st.session_state["test_code"]: st.success("Sistema de 2FA funcionando!")
                else: st.error("Código inválido.")
    with tab_pr:
        prots = [("AES-256","Criptografia end-to-end das mensagens"),("SHA-256","Hash de senhas com salt criptográfico"),("TLS 1.3","Transmissão segura de dados"),("Zero Knowledge","Pesquisas privadas inacessíveis pela plataforma")]
        items = "".join(f'<div style="display:flex;align-items:center;gap:12px;background:rgba(16,185,129,.07);border:1px solid rgba(16,185,129,.2);border-radius:12px;padding:12px;"><div style="width:30px;height:30px;border-radius:8px;background:rgba(16,185,129,.15);display:flex;align-items:center;justify-content:center;color:#10b981;font-weight:700;font-size:.8rem;flex-shrink:0;">✓</div><div><div style="font-weight:600;color:#10b981;font-size:.87rem;">{n2}</div><div style="font-size:.74rem;color:var(--t3);">{d2}</div></div></div>' for n2,d2 in prots)
        st.markdown(f'<div class="card"><div style="font-weight:700;margin-bottom:1rem;">Proteções ativas</div><div style="display:grid;gap:10px;">{items}</div></div>', unsafe_allow_html=True)
        st.markdown('<h3>Visibilidade</h3>', unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            st.selectbox("Perfil",["Público","Só seguidores","Privado"],key="vp")
            st.selectbox("Pesquisas",["Público","Só seguidores","Privado"],key="vr")
        with c2:
            st.selectbox("Estatísticas",["Público","Privado"],key="vs")
            st.selectbox("Rede de conhecimento",["Público","Só seguidores","Privado"],key="vn")
        if st.button("Salvar privacidade", key="btn_priv"): st.success("Configurações salvas!")
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════
def main():
    if not st.session_state.logged_in:
        p = st.session_state.page
        if   p == "verify_email": page_verify_email()
        elif p == "2fa":          page_2fa()
        else:                     page_login()
        return
    render_sidebar()
    {"feed":page_feed,"folders":page_folders,"search":page_search,"knowledge":page_knowledge,
     "chat":page_chat,"analytics":page_analytics,"img_search":page_img_search,"settings":page_settings
     }.get(st.session_state.page, page_feed)()

main()
