mport os, sys, subprocess, io, json, hashlib, base64, re, random, math
from datetime import datetime
from collections import defaultdict, Counter

def _pip(*pkgs):
    for p in pkgs:
        try: subprocess.check_call([sys.executable,"-m","pip","install",p,"-q"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except: pass

try: import plotly.graph_objects as go
except: _pip("plotly"); import plotly.graph_objects as go
try: import numpy as np; from PIL import Image as PILImage
except: _pip("pillow","numpy"); import numpy as np; from PIL import Image as PILImage
try: import requests
except: _pip("requests"); import requests
try: import PyPDF2
except: PyPDF2=None
SKIMAGE_OK=False
try:
    from skimage import filters as sk_f, feature as sk_fe
    from skimage.feature import graycomatrix, graycoprops
    SKIMAGE_OK=True
except:
    try: _pip("scikit-image"); from skimage import filters as sk_f; from skimage.feature import graycomatrix, graycoprops; SKIMAGE_OK=True
    except: pass
SKLEARN_OK=False
try: from sklearn.cluster import KMeans; SKLEARN_OK=True
except:
    try: _pip("scikit-learn"); from sklearn.cluster import KMeans; SKLEARN_OK=True
    except: pass

import streamlit as st
st.set_page_config(page_title="Nebula Research",page_icon="N",layout="wide",initial_sidebar_state="expanded")

DB_FILE="nebula_research.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def hp(pw): return hashlib.sha256(pw.encode()).hexdigest()
def ini(n):
    if not isinstance(n,str): n=str(n)
    p=n.strip().split(); return ''.join(w[0].upper() for w in p[:2]) if p else "?"
def time_ago(ds):
    try:
        d=(datetime.now()-datetime.strptime(ds,"%Y-%m-%d")).days
        if d==0: return "hoje"
        if d==1: return "ontem"
        if d<7: return f"{d}d"
        if d<30: return f"{d//7}sem"
        return f"{d//30}m"
    except: return ds
def fmt_num(n):
    try: n=int(n); return f"{n/1000:.1f}k" if n>=1000 else str(n)
    except: return str(n)
def guser():
    if not isinstance(st.session_state.get("users"),dict): return {}
    return st.session_state.users.get(st.session_state.current_user,{})

STOPWORDS={"de","a","o","que","e","do","da","em","um","para","é","com","uma","os","no","se","na","por",
 "mais","as","dos","como","mas","foi","ao","ele","das","tem","à","seu","sua","ou","ser","quando",
 "muito","há","nos","já","está","eu","também","só","pelo","pela","até","isso","ela","entre","era",
 "the","of","and","to","in","is","it","that","was","for","on","are","with","they","at","be","this",
 "from","or","had","by","not","what","all","were","we","when","your","can","use","an","which","do",
 "how","their","if","will","up","other","about","out","many","then","them","these","so","also","have",
 "been","between","after","before","during","while","through","its","than","has","into","after","each"}

NATIONALITY_COORDS={
    "Brasil":(-14.2,-51.9),"Estados Unidos":(37.1,-95.7),"Alemanha":(51.2,10.4),
    "Reino Unido":(55.4,-3.4),"França":(46.2,2.2),"China":(35.9,104.2),
    "Japão":(36.2,138.3),"Índia":(20.6,79.0),"Canadá":(56.1,-106.3),
    "Austrália":(-25.3,133.8),"México":(23.6,-102.6),"Argentina":(-38.4,-63.6),
    "Portugal":(39.4,-8.2),"Espanha":(40.5,-3.7),"Itália":(41.9,12.6),
    "Países Baixos":(52.1,5.3),"Suécia":(60.1,18.6),"Suíça":(46.8,8.2),
    "Coreia do Sul":(35.9,127.8),"Rússia":(61.5,105.3),"Chile":(-35.7,-71.5),
    "Colômbia":(4.6,-74.1),"Peru":(-9.2,-75.0),"África do Sul":(-30.6,22.9),
    "Israel":(31.0,34.9),"Irã":(32.4,53.7),"Turquia":(38.9,35.2),
}

TOPIC_MAP={
    "Saúde & Medicina":["saúde","medicina","clínico","health","medical","therapy","disease","clinical","patient","hospital","diagnóstico","treatment"],
    "Biologia & Genômica":["biologia","genômica","gene","dna","rna","proteína","célula","crispr","molecular","genome","protein","celular"],
    "Neurociência":["neurociência","neural","cérebro","cognição","memória","sono","brain","sináptico","neuron","hippocampus","cortex","fmri"],
    "Computação & IA":["algoritmo","machine","learning","inteligência","dados","computação","deep","quantum","llm","neural","model","rede","software"],
    "Física & Astronomia":["física","quântica","partícula","energia","galáxia","astrofísica","cosmologia","lensing","matter","relatividade","telescope"],
    "Química":["química","molécula","síntese","reação","polímero","composto","chemical","reaction","catalyst","substância"],
    "Engenharia":["engenharia","sistema","robótica","automação","sensor","protocolo","engineering","system","design","mecânica"],
    "Ciências Sociais":["sociedade","cultura","educação","política","psicologia","comportamento","cognitivo","social","behavior","educação"],
    "Ecologia & Ambiente":["ecologia","clima","ambiente","biodiversidade","carbono","sustentável","climate","ecology","meio","ambiental"],
    "Matemática & Estatística":["matemática","estatística","probabilidade","equação","teorema","variance","bayesian","cálculo","álgebra"],
}

SEED_USERS={
    "demo@nebula.ai":{"name":"Ana Pesquisadora","password":hp("demo123"),"bio":"Pesquisadora em IA e Ciências Cognitivas","area":"Inteligência Artificial","verified":True,"nationality":"Brasil"},
    "carlos@nebula.ai":{"name":"Carlos Mendez","password":hp("nebula123"),"bio":"Neurocientista, plasticidade sináptica e sono","area":"Neurociência","verified":True,"nationality":"México"},
    "luana@nebula.ai":{"name":"Luana Freitas","password":hp("nebula123"),"bio":"Biomédica, CRISPR e terapia gênica","area":"Biomedicina","verified":True,"nationality":"Brasil"},
    "rafael@nebula.ai":{"name":"Rafael Souza","password":hp("nebula123"),"bio":"Computação Quântica, algoritmos híbridos","area":"Computação","verified":True,"nationality":"Brasil"},
    "priya@nebula.ai":{"name":"Priya Nair","password":hp("nebula123"),"bio":"Astrofísica, dark matter & gravitational lensing","area":"Astrofísica","verified":True,"nationality":"Índia"},
}

SEED_RESEARCH=[
    {"id":1,"author":"Carlos Mendez","author_email":"carlos@nebula.ai","area":"Neurociência","nationality":"México","year":2026,
     "title":"Efeitos da Privação de Sono na Plasticidade Sináptica",
     "abstract":"Investigamos como 24h de privação de sono afetam espinhas dendríticas em ratos Wistar, com redução de 34% na plasticidade hipocampal. Microscopia confocal e Western Blot para quantificação proteica.",
     "tags":["neurociência","sono","memória","hipocampo","plasticidade"],"methodology":"experimental",
     "citations":8,"views":312,"likes":47,"liked_by":[],"saved_by":[],"date":"2026-02-10","status":"Em andamento"},
    {"id":2,"author":"Luana Freitas","author_email":"luana@nebula.ai","area":"Biomedicina","nationality":"Brasil","year":2026,
     "title":"CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras",
     "abstract":"Vetor AAV9 modificado para entrega de CRISPR no gene DMD com eficiência de 78% em modelos mdx. Resultados promissores para trials clínicos.",
     "tags":["CRISPR","gene terapia","músculo","AAV9","DMD"],"methodology":"experimental",
     "citations":24,"views":891,"likes":93,"liked_by":[],"saved_by":[],"date":"2026-01-28","status":"Publicado"},
    {"id":3,"author":"Rafael Souza","author_email":"rafael@nebula.ai","area":"Computação","nationality":"Brasil","year":2026,
     "title":"Redes Neurais Quântico-Clássicas para Otimização Combinatória",
     "abstract":"Arquitetura híbrida variacional combinando qubits supercondutores com camadas densas clássicas. TSP resolvido com 40% menos iterações.",
     "tags":["quantum ML","otimização","TSP","computação quântica"],"methodology":"computacional",
     "citations":31,"views":1240,"likes":201,"liked_by":[],"saved_by":[],"date":"2026-02-15","status":"Em andamento"},
    {"id":4,"author":"Priya Nair","author_email":"priya@nebula.ai","area":"Astrofísica","nationality":"Índia","year":2026,
     "title":"Detecção de Matéria Escura via Lentes Gravitacionais Fracas",
     "abstract":"Mapeamento com 100M de galáxias do DES Y3. Tensão de 2.8σ com ΛCDM em escalas < 1 Mpc.",
     "tags":["astrofísica","matéria escura","cosmologia","DES"],"methodology":"observacional",
     "citations":67,"views":2180,"likes":312,"liked_by":[],"saved_by":[],"date":"2026-02-01","status":"Publicado"},
]

VIB=["#0A84FF","#30D158","#FF9F0A","#BF5AF2","#FF453A","#32ADE6","#FFD60A","#FF6B35","#64D2FF","#5E5CE6"]

# ── DB ────────────────────────────────────────────────────────────
def save_db():
    try:
        with open(DB_FILE,"w",encoding="utf-8") as f:
            json.dump({"users":st.session_state.users,"research_items":st.session_state.research_items,
                       "folders":st.session_state.folders,
                       "user_prefs":{k:dict(v) for k,v in st.session_state.user_prefs.items()},
                       "saved_articles":st.session_state.saved_articles,
                       "chat_messages":st.session_state.chat_messages},f,ensure_ascii=False,indent=2)
    except: pass

def init():
    if "initialized" in st.session_state: return
    st.session_state.initialized=True
    disk=load_db(); du=disk.get("users",{})
    if not isinstance(du,dict): du={}
    st.session_state.setdefault("users",{**SEED_USERS,**du})
    st.session_state.setdefault("logged_in",False)
    st.session_state.setdefault("current_user",None)
    st.session_state.setdefault("page","login")
    st.session_state.setdefault("profile_view",None)
    dp=disk.get("user_prefs",{})
    st.session_state.setdefault("user_prefs",{k:defaultdict(float,v) for k,v in dp.items()})
    rp=disk.get("research_items",[dict(p) for p in SEED_RESEARCH])
    for p in rp:
        p.setdefault("liked_by",[]); p.setdefault("saved_by",[]); p.setdefault("comments",[])
        p.setdefault("views",200); p.setdefault("citations",random.randint(0,30))
        p.setdefault("nationality","Brasil"); p.setdefault("year",2026)
    st.session_state.setdefault("research_items",rp)
    st.session_state.setdefault("folders",disk.get("folders",{}))
    st.session_state.setdefault("folder_bytes",{})
    st.session_state.setdefault("saved_articles",disk.get("saved_articles",[]))
    st.session_state.setdefault("scholar_cache",{})
    st.session_state.setdefault("search_results",None)
    st.session_state.setdefault("last_sq","")
    st.session_state.setdefault("api_key","")
    st.session_state.setdefault("img_result",None)
    st.session_state.setdefault("chat_messages",disk.get("chat_messages",{}))
    st.session_state.setdefault("active_chat",None)
    st.session_state.setdefault("view_research",None)

init()

# ══════════════════════════════════════════════════
#  USER INTELLIGENCE ENGINE
# ══════════════════════════════════════════════════
def update_profile(tags, w=1.0):
    e=st.session_state.get("current_user")
    if not e or not tags: return
    p=st.session_state.user_prefs.setdefault(e,defaultdict(float))
    for k in list(p.keys()): p[k]*=0.97  # time decay
    for t in tags: p[t.lower().strip()]+=w

def get_interests(email=None, n=20):
    if not email: email=st.session_state.get("current_user")
    p=st.session_state.user_prefs.get(email,{})
    return [k for k,_ in sorted(p.items(),key=lambda x:-x[1])[:n]] if p else []

def get_recommendations(email=None, n=6):
    if not email: email=st.session_state.get("current_user")
    u=st.session_state.users.get(email,{})
    interests=set(get_interests(email,25))
    area_kws=set(w.lower() for w in re.split(r'[\s,]+',u.get("area","")) if len(w)>3)
    interests|=area_kws
    scored=[]
    for item in st.session_state.research_items:
        if item.get("author_email")==email: continue
        tags=set(t.lower() for t in item.get("tags",[]))
        kws=set(k.lower() for k in kw_extract(item.get("abstract",""),10))
        all_terms=tags|kws
        overlap=len(interests&all_terms)
        score=overlap*10+item.get("citations",0)*0.4+item.get("likes",0)*0.2
        scored.append((score,item))
    scored.sort(key=lambda x:-x[0])
    return [item for s,item in scored if s>0][:n]



def _norm_text(v):
    return re.sub(r'\s+', ' ', str(v or '').strip().lower())


def research_terms(item, keyword_limit=10):
    terms = []
    terms.extend(item.get("tags", []))
    terms.extend(kw_extract(item.get("title", ""), 8))
    terms.extend(kw_extract(item.get("abstract", ""), keyword_limit))
    cleaned = {_norm_text(t) for t in terms if _norm_text(t) and len(_norm_text(t)) > 2}
    return cleaned


def similarity(item1, item2):
    t1 = research_terms(item1, 10)
    t2 = research_terms(item2, 10)
    shared = t1 & t2
    union = t1 | t2

    jac = len(shared) / max(1, len(union))

    title1 = set(kw_extract(item1.get("title", ""), 8))
    title2 = set(kw_extract(item2.get("title", ""), 8))
    title_overlap = len(title1 & title2) / max(1, len(title1 | title2))

    abs1 = set(kw_extract(item1.get("abstract", ""), 12))
    abs2 = set(kw_extract(item2.get("abstract", ""), 12))
    abstract_overlap = len(abs1 & abs2) / max(1, len(abs1 | abs2))

    area1 = _norm_text(item1.get("area", ""))
    area2 = _norm_text(item2.get("area", ""))
    meth1 = _norm_text(item1.get("methodology", ""))
    meth2 = _norm_text(item2.get("methodology", ""))
    nat1 = _norm_text(item1.get("nationality", ""))
    nat2 = _norm_text(item2.get("nationality", ""))

    area_bonus = 0.18 if area1 and area1 == area2 else 0.0
    method_bonus = 0.10 if meth1 and meth1 == meth2 else 0.0
    nat_bonus = 0.04 if nat1 and nat1 == nat2 else 0.0

    year_bonus = 0.0
    y1, y2 = item1.get("year"), item2.get("year")
    if isinstance(y1, int) and isinstance(y2, int):
        diff = abs(y1 - y2)
        if diff <= 1:
            year_bonus = 0.08
        elif diff <= 3:
            year_bonus = 0.04

    shared_bonus = min(0.22, len(shared) * 0.035)
    score = jac * 0.46 + title_overlap * 0.18 + abstract_overlap * 0.14 + area_bonus + method_bonus + nat_bonus + year_bonus + shared_bonus
    return round(min(1.0, score), 4)


def connection_details(item1, item2):
    score = similarity(item1, item2)
    shared_terms = sorted(
        research_terms(item1, 10) & research_terms(item2, 10),
        key=lambda x: (-len(x.split()), -len(x), x)
    )[:8]
    reasons = []
    if _norm_text(item1.get("area")) == _norm_text(item2.get("area")) and item1.get("area"):
        reasons.append(f"mesma área: {item1.get('area', '')}")
    if _norm_text(item1.get("methodology")) == _norm_text(item2.get("methodology")) and item1.get("methodology"):
        reasons.append(f"mesma metodologia: {item1.get('methodology', '')}")
    if item1.get("year") and item2.get("year"):
        diff = abs(int(item1.get("year")) - int(item2.get("year")))
        if diff <= 1:
            reasons.append("recorte temporal muito próximo")
        elif diff <= 3:
            reasons.append("recorte temporal compatível")
    if _norm_text(item1.get("nationality")) == _norm_text(item2.get("nationality")) and item1.get("nationality"):
        reasons.append(f"mesma nacionalidade: {item1.get('nationality', '')}")
    if shared_terms:
        reasons.append("termos em comum: " + ", ".join(shared_terms[:4]))
    strength = "forte" if score >= 0.45 else ("média" if score >= 0.28 else "inicial")
    return {
        "score": score,
        "strength": strength,
        "shared_terms": shared_terms,
        "reasons": reasons,
    }


def build_connection_edges(items, threshold=0.22):
    edges = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            det = connection_details(items[i], items[j])
            if det["score"] >= threshold:
                edges.append({
                    "source": items[i],
                    "target": items[j],
                    "score": det["score"],
                    "strength": det["strength"],
                    "shared_terms": det["shared_terms"],
                    "reasons": det["reasons"],
                })
    edges.sort(key=lambda x: (-x["score"], x["source"].get("title", ""), x["target"].get("title", "")))
    return edges


def connection_count_map(items, edges):
    counts = {item["id"]: 0 for item in items}
    for edge in edges:
        counts[edge["source"]["id"]] = counts.get(edge["source"]["id"], 0) + 1
        counts[edge["target"]["id"]] = counts.get(edge["target"]["id"], 0) + 1
    return counts


def find_similar(target, threshold=0.18, n=6):
    results = []
    for item in st.session_state.research_items:
        if item["id"] == target["id"]:
            continue
        sim = similarity(target, item)
        if sim >= threshold:
            results.append((sim, item))
    results.sort(key=lambda x: (-x[0], -x[1].get("citations", 0), x[1].get("title", "")))
    return results[:n]


def folder_similarity(folder_analyses, n=8):
    matches = []
    for item in st.session_state.research_items:
        item_terms = research_terms(item, 8)
        best = None
        for fname, an in folder_analyses.items():
            doc_terms = {_norm_text(k) for k in an.get("keywords", [])[:12] if _norm_text(k)}
            topic_terms = {_norm_text(k) for k in an.get("topics", {}).keys() if _norm_text(k)}
            combined = doc_terms | topic_terms
            overlap = sorted(item_terms & combined)[:8]
            if not overlap:
                continue
            topic_bonus = 0.0
            area = _norm_text(item.get("area", ""))
            if area and any(area in t or t in area for t in topic_terms):
                topic_bonus = 0.12
            score = min(1.0, (len(overlap) / max(4, len(item_terms))) * 0.88 + topic_bonus + (an.get("relevance_score", 0) / 100) * 0.12)
            data = {
                "score": round(score, 4),
                "research": item,
                "document": fname,
                "shared_terms": overlap,
                "topics": list(an.get("topics", {}).keys())[:4],
                "summary": an.get("summary", ""),
            }
            if best is None or data["score"] > best["score"]:
                best = data
        if best and best["score"] >= 0.18:
            matches.append(best)
    matches.sort(key=lambda x: (-x["score"], -x["research"].get("citations", 0), x["research"].get("title", "")))
    return matches[:n]

# ══════════════════════════════════════════════════
#  DOCUMENT ANALYSIS
# ══════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def extract_pdf(b):
    if not PyPDF2: return ""
    try:
        r=PyPDF2.PdfReader(io.BytesIO(b)); t=""
        for pg in r.pages[:20]:
            try: t+=pg.extract_text()+"\n"
            except: pass
        return t[:40000]
    except: return ""

@st.cache_data(show_spinner=False)
def kw_extract(text, n=20):
    if not text: return []
    words=re.findall(r'\b[a-záàâãéêíóôõúüçA-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]{4,}\b',text.lower())
    words=[w for w in words if w not in STOPWORDS]
    if not words: return []
    tf=Counter(words); tot=max(1,sum(tf.values()))
    return [w for w,_ in sorted(tf.items(),key=lambda x:-x[1]/tot)[:n]]

def extract_year_from_text(text):
    years=re.findall(r'\b(19[5-9]\d|20[0-3]\d)\b',text)
    if years: return int(Counter(years).most_common(1)[0][0])
    return None

def extract_authors_from_text(text):
    patterns=[r'(?:Autor(?:es)?|Author(?:s)?)[:\s]+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){1,3})',
              r'(?:Por|By)[:\s]+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){1,2})']
    authors=[]
    for pat in patterns: authors.extend(re.findall(pat,text[:3000])[:3])
    return list(set(a.strip() for a in authors if len(a)>5))[:5]

def extract_nationality_from_text(text):
    text_lower=text.lower()
    for nat in NATIONALITY_COORDS.keys():
        if nat.lower() in text_lower: return nat
    country_hints={"brasil":"Brasil","brazil":"Brasil","usa":"Estados Unidos","united states":"Estados Unidos",
                   "germany":"Alemanha","france":"França","china":"China","japan":"Japão",
                   "india":"Índia","canada":"Canadá","australia":"Austrália","uk":"Reino Unido",
                   "england":"Reino Unido","mexico":"México","argentina":"Argentina",
                   "portugal":"Portugal","spain":"Espanha","italy":"Itália"}
    for hint,nat in country_hints.items():
        if hint in text_lower: return nat
    return None

def topics_from_kws(kws):
    s=defaultdict(int)
    for kw in kws:
        for tp,terms in TOPIC_MAP.items():
            if any(t in kw or kw in t for t in terms): s[tp]+=1
    return dict(sorted(s.items(),key=lambda x:-x[1])) if s else {"Pesquisa Geral":1}

@st.cache_data(show_spinner=False)
def analyze_document(fname, fbytes, ftype_str, area=""):
    r={"file":fname,"type":ftype_str,"keywords":[],"topics":{},"relevance_score":0,"summary":"",
       "strengths":[],"improvements":[],"word_count":0,"authors":[],"year":None,
       "nationality":None,"estimated_year":None,"key_sentences":[]}
    text=""
    if ftype_str=="PDF" and fbytes and PyPDF2:
        text=extract_pdf(fbytes)
    elif fbytes:
        try: text=fbytes.decode("utf-8",errors="ignore")[:40000]
        except: pass
    if text:
        r["keywords"]=kw_extract(text,25); r["topics"]=topics_from_kws(r["keywords"])
        wc=len(text.split()); r["word_count"]=wc
        r["authors"]=extract_authors_from_text(text)
        r["year"]=extract_year_from_text(text)
        r["nationality"]=extract_nationality_from_text(text)
        sents=[s.strip() for s in re.split(r'[.!?]+',text) if 40<len(s.strip())<250]
        r["key_sentences"]=sents[:4]
        if area:
            aw=area.lower().split()
            rel=sum(1 for w in aw if any(w in kw for kw in r["keywords"]))
            r["relevance_score"]=min(100,rel*15+45)
        else: r["relevance_score"]=60
        if len(r["keywords"])>15: r["strengths"].append(f"Vocabulário técnico rico ({len(r['keywords'])} termos)")
        if wc>2000: r["strengths"].append("Documento extenso e detalhado")
        if len(r["topics"])>3: r["strengths"].append("Multidisciplinar")
        if r["authors"]: r["strengths"].append(f"Autoria identificada: {', '.join(r['authors'][:2])}")
        if wc<300: r["improvements"].append("Expandir conteúdo")
        if len(r["keywords"])<8: r["improvements"].append("Enriquecer vocabulário técnico")
        r["summary"]=f"{ftype_str} · {wc:,} palavras · {', '.join(list(r['topics'].keys())[:2])} · {', '.join(r['keywords'][:4])}"
    else:
        r["summary"]=f"Arquivo {ftype_str}"; r["relevance_score"]=50
        r["keywords"]=kw_extract(fname.lower().replace("_"," "),5)
        r["topics"]=topics_from_kws(r["keywords"])
    return r

# ══════════════════════════════════════════════════
#  ML IMAGE PIPELINE
# ══════════════════════════════════════════════════
def sobel_ml(gray):
    kx=np.array([[-1,0,1],[-2,0,2],[-1,0,1]],dtype=np.float32)/8.0
    def conv2d(im,k):
        ph,pw=k.shape[0]//2,k.shape[1]//2
        p=np.pad(im,((ph,ph),(pw,pw)),mode='edge'); out=np.zeros_like(im)
        for i in range(k.shape[0]):
            for j in range(k.shape[1]): out+=k[i,j]*p[i:i+im.shape[0],j:j+im.shape[1]]
        return out
    sx=conv2d(gray.astype(np.float32),kx); sy=conv2d(gray.astype(np.float32),kx.T)
    mag=np.sqrt(sx**2+sy**2)
    return {"mean":float(mag.mean()),"max":float(mag.max()),
            "density":float((mag>mag.mean()*1.5).mean()),
            "hist":np.histogram(mag,bins=16,range=(0,mag.max()+1e-5))[0].tolist()}

def fft_ml(gray):
    fft=np.fft.fftshift(np.abs(np.fft.fft2(gray))); h,w=fft.shape
    total=fft.sum()+1e-5; r=min(h,w)//2; Y,X=np.ogrid[:h,:w]; dist=np.sqrt((X-w//2)**2+(Y-h//2)**2)
    lf=float(fft[dist<r*0.1].sum()/total); mf=float(fft[(dist>=r*0.1)&(dist<r*0.4)].sum()/total)
    outer=float(np.percentile(fft[dist>r*0.5],99))/(float(fft[dist>r*0.5].mean())+1e-5)
    return {"lf":round(lf,3),"mf":round(mf,3),"hf":round(1-lf-mf,3),"periodic_score":round(outer,1),"is_periodic":outer>12}

def texture_ml(gray_u8):
    g=gray_u8.astype(np.float32)/255.0; gx=np.gradient(g,axis=1); gy=np.gradient(g,axis=0)
    contrast=float(np.sqrt(gx**2+gy**2).mean()*100)
    hom=1.0/(1.0+contrast/50.0); energy=float(np.var(g))
    tt="homogênea" if hom>0.7 else ("texturizada" if contrast>50 else "estruturada")
    return {"contrast":round(contrast,3),"homogeneity":round(hom,3),"energy":round(energy,4),"texture_type":tt}

def palette_ml(arr, k=6):
    if not SKLEARN_OK: return []
    try:
        step=max(1,(arr.shape[0]*arr.shape[1])//3000)
        flat=arr.reshape(-1,3)[::step].astype(np.float32)
        km=KMeans(n_clusters=k,random_state=42,n_init=5,max_iter=80).fit(flat)
        cnt=Counter(km.labels_); tot=sum(cnt.values())
        pal=[]
        for i in np.argsort([-cnt[j] for j in range(k)]):
            r2,g2,b2=km.cluster_centers_[i].astype(int)
            pal.append({"rgb":(int(r2),int(g2),int(b2)),"hex":"#{:02x}{:02x}{:02x}".format(int(r2),int(g2),int(b2)),"pct":round(cnt[i]/tot*100,1)})
        return pal
    except: return []

def classify_img(sobel_r, texture_r, color, fft_r):
    mr,mg,mb=color["r"],color["g"],color["b"]; ei=sobel_r["mean"]; hom=texture_r["homogeneity"]
    scores={"Histopatologia H&E":int(mr>140 and mb>100)*30+int(ei>0.05)*20+int(texture_r["contrast"]>30)*20,
            "Fluorescência DAPI":int(mb>150 and mb>mr+30)*45+int(ei>0.08)*20,
            "Fluorescência GFP":int(mg>150 and mg>mr+30)*45+int(ei>0.08)*20,
            "Gel/Western Blot":int(texture_r["contrast"]<15 and hom>0.8)*30+int(abs(mr-mg)<20 and abs(mg-mb)<20)*25,
            "Gráfico/Diagrama":int(texture_r["energy"]>0.15)*30+int(hom>0.85)*25+int(fft_r["lf"]>0.5)*20,
            "Microscopia Confocal":int(ei>0.05)*20+int(sobel_r["density"]>0.10)*25,
            "Imagem Astronômica":int(color.get("brightness",128)<60)*35+int(hom>0.7)*20,
            "Estrutura Molecular":int(fft_r["is_periodic"])*30+int(hom>0.75)*25}
    best=max(scores,key=scores.get); conf=min(94,38+scores[best]*0.55)
    search_map={"Histopatologia H&E":"hematoxylin eosin staining histopathology tissue",
                "Fluorescência DAPI":"DAPI nuclear staining fluorescence microscopy",
                "Fluorescência GFP":"GFP green fluorescent protein confocal imaging",
                "Gel/Western Blot":"western blot gel electrophoresis protein analysis",
                "Gráfico/Diagrama":"scientific data visualization chart",
                "Microscopia Confocal":"confocal microscopy fluorescence multichannel",
                "Imagem Astronômica":"astronomy telescope deep field observation",
                "Estrutura Molecular":"molecular structure crystal protein visualization"}
    return {"category":best,"confidence":round(conf,1),"search_kw":search_map.get(best,best+" scientific"),"all_scores":dict(sorted(scores.items(),key=lambda x:-x[1])[:5])}

@st.cache_data(show_spinner=False,ttl=3600)
def run_ml(img_bytes):
    try:
        img=PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
        orig=img.size; w,h=img.size; s=min(384/w,384/h)
        img_r=img.resize((int(w*s),int(h*s)),PILImage.LANCZOS)
        arr=np.array(img_r,dtype=np.float32)
        r_ch,g_ch,b_ch=arr[:,:,0],arr[:,:,1],arr[:,:,2]
        gray=0.2989*r_ch+0.5870*g_ch+0.1140*b_ch; gray_u8=gray.astype(np.uint8)
        mr,mg,mb=float(r_ch.mean()),float(g_ch.mean()),float(b_ch.mean())
        hst=np.histogram(gray,bins=64,range=(0,255))[0]; hn=hst/(hst.sum()+1e-9); hn=hn[hn>0]
        entropy=float(-np.sum(hn*np.log2(hn+1e-12)))
        color={"r":round(mr,1),"g":round(mg,1),"b":round(mb,1),"entropy":round(entropy,3),
               "brightness":round(float(gray.mean()),1),"warm":mr>mb+15,"cool":mb>mr+15}
        sobel_r=sobel_ml(gray/255.0); texture_r=texture_ml(gray_u8); fft_r=fft_ml(gray/255.0)
        pal=palette_ml(arr.astype(np.uint8),6)
        cls=classify_img(sobel_r,texture_r,color,fft_r)
        rh=np.histogram(r_ch.ravel(),bins=32,range=(0,255))[0].tolist()
        gh=np.histogram(g_ch.ravel(),bins=32,range=(0,255))[0].tolist()
        bh=np.histogram(b_ch.ravel(),bins=32,range=(0,255))[0].tolist()
        return {"ok":True,"size":orig,"color":color,"sobel":sobel_r,"texture":texture_r,
                "fft":fft_r,"palette":pal,"histograms":{"r":rh,"g":gh,"b":bh},"classification":cls}
    except Exception as e: return {"ok":False,"error":str(e)}

# ══════════════════════════════════════════════════
#  API — CLAUDE VISION
# ══════════════════════════════════════════════════
VISION_PROMPT="""Analise esta imagem científica. Responda APENAS em JSON puro sem markdown:
{
  "tipo": "<tipo>",
  "origem": "<área científica>",
  "descricao": "<descrição detalhada>",
  "estruturas": ["<s1>","<s2>","<s3>"],
  "tecnica": "<técnica experimental>",
  "qualidade": "<Alta/Média/Baixa>",
  "confianca": <0-100>,
  "termos_busca": "<4-6 termos para busca acadêmica>",
  "interpretacao": "<interpretação científica>",
  "aviso": "Análise por IA — validar com especialista."
}"""

def call_vision(img_bytes, api_key):
    if not api_key or not api_key.startswith("sk-"): return None,"API key inválida."
    try:
        img=PILImage.open(io.BytesIO(img_bytes)); buf=io.BytesIO()
        img.convert("RGB").save(buf,format="JPEG",quality=82)
        b64=base64.b64encode(buf.getvalue()).decode()
        resp=requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key":api_key,"anthropic-version":"2023-06-01","content-type":"application/json"},
            json={"model":"claude-opus-4-5","max_tokens":1200,
                  "messages":[{"role":"user","content":[
                      {"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":b64}},
                      {"type":"text","text":VISION_PROMPT}]}]},timeout=30)
        if resp.status_code==200: return resp.json()["content"][0]["text"],None
        return None,resp.json().get("error",{}).get("message",f"HTTP {resp.status_code}")
    except Exception as e: return None,str(e)

# ══════════════════════════════════════════════════
#  ACADEMIC SEARCH
# ══════════════════════════════════════════════════
@st.cache_data(show_spinner=False,ttl=1800)
def search_ss(q, lim=8):
    try:
        r=requests.get("https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query":q,"limit":lim,"fields":"title,authors,year,abstract,venue,externalIds,openAccessPdf,citationCount"},timeout=9)
        if r.status_code==200:
            out=[]
            for p in r.json().get("data",[]):
                ext=p.get("externalIds",{}) or {}; doi=ext.get("DOI",""); arx=ext.get("ArXiv","")
                pdf=(p.get("openAccessPdf") or {}).get("url","")
                link=pdf or(f"https://arxiv.org/abs/{arx}" if arx else(f"https://doi.org/{doi}" if doi else ""))
                al=p.get("authors",[]) or []; au=", ".join(a.get("name","") for a in al[:3])
                if len(al)>3: au+=" et al."
                out.append({"title":p.get("title","Sem título"),"authors":au or "—","year":p.get("year","?"),
                            "source":p.get("venue","") or "Semantic Scholar","doi":doi or arx or "—",
                            "abstract":(p.get("abstract","") or "")[:300],"url":link,
                            "citations":p.get("citationCount",0),"origin":"semantic"})
            return out
    except: pass
    return []

@st.cache_data(show_spinner=False,ttl=1800)
def search_cr(q, lim=4):
    try:
        r=requests.get("https://api.crossref.org/works",
            params={"query":q,"rows":lim,"select":"title,author,issued,abstract,DOI,container-title,is-referenced-by-count"},timeout=8)
        if r.status_code==200:
            out=[]
            for p in r.json().get("message",{}).get("items",[]):
                title=(p.get("title") or["?"])[0]; ars=p.get("author",[]) or []
                au=", ".join(f'{a.get("given","").split()[0] if a.get("given") else ""} {a.get("family","")}'.strip() for a in ars[:3])
                if len(ars)>3: au+=" et al."
                yr=(p.get("issued",{}).get("date-parts") or[[None]])[0][0]
                doi=p.get("DOI",""); ab=re.sub(r'<[^>]+>','',p.get("abstract","") or "")[:300]
                out.append({"title":title,"authors":au or "—","year":yr or "?",
                            "source":(p.get("container-title") or["CrossRef"])[0],"doi":doi,
                            "abstract":ab,"url":f"https://doi.org/{doi}" if doi else "","citations":p.get("is-referenced-by-count",0),"origin":"crossref"})
            return out
    except: pass
    return []

FTYPE_MAP={"pdf":"PDF","docx":"Word","xlsx":"Planilha","csv":"Dados","txt":"Texto","py":"Código","md":"Markdown","png":"Imagem","jpg":"Imagem","jpeg":"Imagem","tiff":"Imagem","ipynb":"Notebook"}
def ftype(fname): return FTYPE_MAP.get(fname.split(".")[-1].lower() if "." in fname else "","Arquivo")

# ══════════════════════════════════════════════════
#  CSS — DARK BLUE LIQUID GLASS
# ══════════════════════════════════════════════════
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800;900&family=Inter:wght@300;400;500;600;700&display=swap');
:root{
  --bg:#03060E;--s1:#060B18;--s2:#0A1020;--s3:#0D1528;
  --acc:#0A84FF;--acc2:#1A6EC9;
  --teal:#30D158;--teal2:#25A244;
  --orn:#FF9F0A;--pur:#BF5AF2;--red:#FF453A;--cya:#32ADE6;--gold:#FFD60A;
  --t0:#FFFFFF;--t1:#D8E4F5;--t2:#7A8FAD;--t3:#3A4D6A;--t4:#1A2840;
  --gb1:rgba(255,255,255,.06);--gb2:rgba(255,255,255,.11);--gb3:rgba(255,255,255,.17);
  --acc-a:rgba(10,132,255,.10);--acc-ab:rgba(10,132,255,.18);--acc-ac:rgba(10,132,255,.28);
  --r8:8px;--r12:12px;--r16:16px;--r20:20px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body,.stApp{background:var(--bg)!important;color:var(--t1)!important;font-family:'Inter',-apple-system,sans-serif!important;}
.stApp::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:radial-gradient(ellipse 65% 50% at -10% -5%,rgba(10,132,255,.055) 0%,transparent 60%),
    radial-gradient(ellipse 55% 45% at 110% -5%,rgba(48,209,88,.045) 0%,transparent 55%),
    radial-gradient(ellipse 45% 55% at 50% 110%,rgba(191,90,242,.035) 0%,transparent 60%);}
header[data-testid="stHeader"],#MainMenu,footer,.stDeployButton,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
[data-testid="stSidebarCollapseButton"],[data-testid="collapsedControl"]{display:none!important}
section[data-testid="stSidebar"]{
  display:block!important;transform:translateX(0)!important;visibility:visible!important;
  background:rgba(3,6,14,.97)!important;border-right:1px solid rgba(255,255,255,.055)!important;
  box-shadow:4px 0 40px rgba(0,0,0,.7)!important;
  width:216px!important;min-width:216px!important;max-width:216px!important;
  padding:1.3rem .9rem 1rem!important;}
section[data-testid="stSidebar"]>div{width:216px!important;padding:0!important;}
.block-container{padding-top:.35rem!important;padding-bottom:4rem!important;max-width:1460px!important;position:relative;z-index:1;padding-left:.75rem!important;padding-right:.75rem!important;}

/* ── LIQUID GLASS BUTTONS ── */
.stButton>button{
  position:relative;overflow:hidden;
  background:linear-gradient(145deg,rgba(255,255,255,.07) 0%,rgba(255,255,255,.025) 100%)!important;
  border:1px solid rgba(255,255,255,.09)!important;
  border-top-color:rgba(255,255,255,.16)!important;
  border-left-color:rgba(255,255,255,.11)!important;
  border-radius:12px!important;
  box-shadow:0 2px 14px rgba(0,0,0,.4),0 1px 0 rgba(255,255,255,.06) inset!important;
  color:#8090B0!important;-webkit-text-fill-color:#8090B0!important;
  font-family:'Inter',sans-serif!important;font-weight:500!important;font-size:.82rem!important;
  padding:.46rem .88rem!important;
  transition:all .17s cubic-bezier(.4,0,.2,1)!important;
  width:100%!important;margin-bottom:.18rem!important;text-align:left!important;
}
.stButton>button::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.2),transparent);pointer-events:none;}
.stButton>button:hover{
  background:linear-gradient(145deg,var(--acc-ab) 0%,rgba(10,132,255,.07) 100%)!important;
  border-color:var(--acc-ac)!important;border-top-color:rgba(10,132,255,.45)!important;
  box-shadow:0 6px 22px rgba(10,132,255,.18),0 1px 0 rgba(255,255,255,.1) inset!important;
  color:var(--t0)!important;-webkit-text-fill-color:var(--t0)!important;
  transform:translateY(-1px)!important;}
.stButton>button:active{transform:scale(.98)!important;box-shadow:0 2px 8px rgba(0,0,0,.3)!important;}
.stButton>button p,.stButton>button span{color:inherit!important;-webkit-text-fill-color:inherit!important;}
section[data-testid="stSidebar"] .stButton>button{padding:.48rem .8rem!important;font-size:.83rem!important;}

/* ── INPUTS ── */
.stTextInput input,.stTextArea textarea{
  background:rgba(255,255,255,.035)!important;border:1px solid rgba(255,255,255,.08)!important;
  border-top-color:rgba(255,255,255,.12)!important;border-radius:12px!important;
  color:var(--t1)!important;font-family:'Inter',sans-serif!important;font-size:.83rem!important;
  box-shadow:inset 0 2px 8px rgba(0,0,0,.25)!important;}
.stTextInput input:focus,.stTextArea textarea:focus{
  border-color:rgba(10,132,255,.45)!important;
  box-shadow:0 0 0 3px rgba(10,132,255,.09),inset 0 2px 8px rgba(0,0,0,.2)!important;}
.stTextInput label,.stTextArea label,.stSelectbox label,.stFileUploader label,.stNumberInput label{
  color:var(--t3)!important;font-size:.57rem!important;letter-spacing:.12em!important;
  text-transform:uppercase!important;font-weight:700!important;}

/* ── SIDEBAR LOGO ── */
.sb-logo{display:flex;align-items:center;gap:9px;margin-bottom:1.4rem;padding:.1rem .2rem}
.sb-logo-icon{width:34px;height:34px;border-radius:10px;background:linear-gradient(135deg,#0A84FF,#30D158);
  display:flex;align-items:center;justify-content:center;font-size:1rem;flex-shrink:0;
  box-shadow:0 0 18px rgba(10,132,255,.3)}
.sb-logo-txt{font-family:'Syne',sans-serif;font-weight:900;font-size:1.2rem;letter-spacing:-.05em;
  background:linear-gradient(135deg,#0A84FF,#30D158);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.sb-lbl{font-size:.52rem;font-weight:700;color:var(--t3);letter-spacing:.14em;text-transform:uppercase;
  padding:0 .15rem;margin-bottom:.32rem;margin-top:.75rem}

/* ── GLASS CARDS ── */
.glass-card{
  background:linear-gradient(145deg,rgba(255,255,255,.05) 0%,rgba(255,255,255,.018) 100%);
  border:1px solid rgba(255,255,255,.075);border-top-color:rgba(255,255,255,.13);
  border-radius:20px;box-shadow:0 8px 40px rgba(0,0,0,.45);position:relative;overflow:hidden;}
.glass-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.14),transparent);pointer-events:none;}
.research-card{
  background:linear-gradient(145deg,rgba(255,255,255,.045) 0%,rgba(255,255,255,.016) 100%);
  border:1px solid rgba(255,255,255,.065);border-top-color:rgba(255,255,255,.11);
  border-radius:16px;margin-bottom:.5rem;overflow:hidden;
  box-shadow:0 4px 24px rgba(0,0,0,.35);
  transition:border-color .17s,transform .17s,box-shadow .17s;position:relative;}
.research-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(10,132,255,.1),transparent);}
.research-card:hover{border-color:rgba(10,132,255,.25);transform:translateY(-2px);box-shadow:0 12px 38px rgba(10,132,255,.1);}
.sc{background:rgba(255,255,255,.038);border:1px solid rgba(255,255,255,.065);border-radius:16px;
  padding:.85rem .95rem;margin-bottom:.5rem;position:relative;}
.sc::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.09),transparent);}
.scard{background:rgba(255,255,255,.028);border:1px solid rgba(255,255,255,.058);border-radius:13px;
  padding:.72rem .92rem;margin-bottom:.38rem;transition:border-color .14s,transform .12s;}
.scard:hover{border-color:rgba(10,132,255,.22);transform:translateY(-1px);}
.mbox{background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.065);border-radius:13px;padding:.82rem;text-align:center;}
.abox{background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.07);border-radius:13px;padding:.9rem;margin-bottom:.5rem;}
.chart-wrap{background:rgba(255,255,255,.018);border:1px solid rgba(255,255,255,.05);border-radius:12px;padding:.55rem;margin-bottom:.5rem;}

/* ── COLORED BOXES ── */
.pbox-acc{background:rgba(10,132,255,.05);border:1px solid rgba(10,132,255,.16);border-radius:11px;padding:.75rem;margin-bottom:.42rem;}
.pbox-teal{background:rgba(48,209,88,.05);border:1px solid rgba(48,209,88,.16);border-radius:11px;padding:.75rem;margin-bottom:.42rem;}
.pbox-pur{background:rgba(191,90,242,.05);border:1px solid rgba(191,90,242,.16);border-radius:11px;padding:.75rem;margin-bottom:.42rem;}
.pbox-orn{background:rgba(255,159,10,.05);border:1px solid rgba(255,159,10,.16);border-radius:11px;padding:.75rem;margin-bottom:.42rem;}
.pbox-red{background:rgba(255,69,58,.05);border:1px solid rgba(255,69,58,.16);border-radius:11px;padding:.75rem;margin-bottom:.42rem;}
.ai-card{background:linear-gradient(135deg,rgba(10,132,255,.065),rgba(48,209,88,.04));
  border:1px solid rgba(10,132,255,.18);border-radius:15px;padding:1rem;margin-bottom:.6rem;position:relative;overflow:hidden;}
.ai-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(10,132,255,.32),transparent);}
.conn-card{background:linear-gradient(135deg,rgba(48,209,88,.055),rgba(10,132,255,.035));
  border:1px solid rgba(48,209,88,.18);border-radius:13px;padding:.9rem;margin-bottom:.5rem;position:relative;}
.sim-card{background:linear-gradient(135deg,rgba(191,90,242,.045),rgba(10,132,255,.028));
  border:1px solid rgba(191,90,242,.15);border-radius:13px;padding:.85rem;margin-bottom:.45rem;}
.ai-disc{background:rgba(255,159,10,.04);border:1px solid rgba(255,159,10,.14);border-radius:10px;
  padding:.55rem .8rem;margin-bottom:.55rem;}

/* ── METRIC VALS ── */
.mval-acc{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;
  background:linear-gradient(135deg,#0A84FF,#32ADE6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-teal{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;
  background:linear-gradient(135deg,#30D158,#32ADE6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-pur{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;
  background:linear-gradient(135deg,#BF5AF2,#0A84FF);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-orn{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;
  background:linear-gradient(135deg,#FF9F0A,#FF453A);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mlbl{font-size:.55rem;color:var(--t3);margin-top:4px;letter-spacing:.10em;text-transform:uppercase;font-weight:700}

/* ── BADGES & TAGS ── */
.tag{display:inline-block;background:rgba(10,132,255,.07);border:1px solid rgba(10,132,255,.16);
  border-radius:50px;padding:2px 8px;font-size:.60rem;color:#6AACFF;margin:2px;font-weight:500;}
.tag-teal{display:inline-block;background:rgba(48,209,88,.07);border:1px solid rgba(48,209,88,.16);
  border-radius:50px;padding:2px 8px;font-size:.60rem;color:#5AE07A;margin:2px;font-weight:500;}
.tag-pur{display:inline-block;background:rgba(191,90,242,.07);border:1px solid rgba(191,90,242,.16);
  border-radius:50px;padding:2px 8px;font-size:.60rem;color:#CF9AFF;margin:2px;font-weight:500;}
.badge-acc{display:inline-block;background:rgba(10,132,255,.10);border:1px solid rgba(10,132,255,.22);
  border-radius:50px;padding:2px 9px;font-size:.60rem;font-weight:700;color:#0A84FF;}
.badge-teal{display:inline-block;background:rgba(48,209,88,.10);border:1px solid rgba(48,209,88,.22);
  border-radius:50px;padding:2px 9px;font-size:.60rem;font-weight:700;color:#30D158;}
.badge-orn{display:inline-block;background:rgba(255,159,10,.10);border:1px solid rgba(255,159,10,.22);
  border-radius:50px;padding:2px 9px;font-size:.60rem;font-weight:700;color:#FF9F0A;}
.badge-pur{display:inline-block;background:rgba(191,90,242,.10);border:1px solid rgba(191,90,242,.22);
  border-radius:50px;padding:2px 9px;font-size:.60rem;font-weight:700;color:#BF5AF2;}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"]{background:rgba(255,255,255,.025)!important;
  border:1px solid rgba(255,255,255,.06)!important;border-radius:12px!important;padding:3px!important;gap:2px!important;}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--t3)!important;
  border-radius:9px!important;font-size:.73rem!important;font-family:'Inter',sans-serif!important;font-weight:500!important;}
.stTabs [aria-selected="true"]{background:var(--acc-ab)!important;color:var(--acc)!important;
  border:1px solid var(--acc-ac)!important;font-weight:700!important;}
.stTabs [data-baseweb="tab-panel"]{background:transparent!important;padding-top:.75rem!important;}

/* ── PROFILE HERO ── */
.prof-hero{background:linear-gradient(145deg,rgba(255,255,255,.045) 0%,rgba(255,255,255,.015) 100%);
  border:1px solid rgba(255,255,255,.075);border-top-color:rgba(255,255,255,.12);
  border-radius:22px;padding:1.5rem;display:flex;gap:1.2rem;align-items:flex-start;
  box-shadow:0 8px 40px rgba(0,0,0,.45);margin-bottom:.9rem;}
.av{width:72px;height:72px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-family:'Syne',sans-serif;font-weight:800;font-size:1.5rem;color:white;flex-shrink:0;
  border:2px solid rgba(10,132,255,.2);}

/* ── CHAT ── */
.bme{background:linear-gradient(135deg,rgba(10,132,255,.16),rgba(10,132,255,.08));
  border:1px solid rgba(10,132,255,.22);border-radius:18px 18px 4px 18px;
  padding:.52rem .85rem;max-width:70%;margin-left:auto;margin-bottom:4px;font-size:.81rem;line-height:1.6;}
.bthem{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);
  border-radius:18px 18px 18px 4px;padding:.52rem .85rem;max-width:70%;margin-bottom:4px;
  font-size:.81rem;line-height:1.6;}

@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.7)}}
.dot-on{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--teal);
  animation:pulse 2.5s infinite;margin-right:4px;vertical-align:middle;}
@keyframes fadeUp{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
.pw{animation:fadeUp .16s ease both;}
hr{border:none;border-top:1px solid rgba(255,255,255,.06)!important;margin:.7rem 0;}
.dtxt{display:flex;align-items:center;gap:.65rem;margin:.65rem 0;font-size:.54rem;color:var(--t3);
  letter-spacing:.10em;text-transform:uppercase;font-weight:700;}
.dtxt::before,.dtxt::after{content:'';flex:1;height:1px;background:rgba(255,255,255,.055);}
h1{font-family:'Syne',sans-serif!important;font-size:1.5rem!important;font-weight:800!important;
  letter-spacing:-.03em;color:var(--t0)!important;}
h2{font-family:'Syne',sans-serif!important;font-size:.98rem!important;font-weight:700!important;color:var(--t0)!important;}
label{color:var(--t2)!important;}
.stCheckbox label,.stRadio label{color:var(--t1)!important;}
.stRadio>div{display:flex!important;gap:3px!important;flex-wrap:wrap!important;}
.stRadio>div>label{background:rgba(255,255,255,.04)!important;border:1px solid rgba(255,255,255,.07)!important;
  border-radius:50px!important;padding:.24rem .7rem!important;font-size:.72rem!important;cursor:pointer!important;color:var(--t2)!important;}
.stSelectbox [data-baseweb="select"]{background:rgba(255,255,255,.035)!important;
  border:1px solid rgba(255,255,255,.08)!important;border-radius:12px!important;}
.stFileUploader section{background:rgba(255,255,255,.025)!important;
  border:1.5px dashed rgba(10,132,255,.2)!important;border-radius:14px!important;}
.stExpander{background:rgba(255,255,255,.028);border:1px solid rgba(255,255,255,.06);border-radius:14px;}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-thumb{background:rgba(10,132,255,.2);border-radius:4px;}
.stAlert{background:rgba(255,255,255,.035)!important;border:1px solid rgba(255,255,255,.07)!important;border-radius:14px!important;}
input[type="number"]{background:rgba(255,255,255,.035)!important;border:1px solid rgba(255,255,255,.08)!important;border-radius:12px!important;color:var(--t1)!important;}
</style>""",unsafe_allow_html=True)

# ══════════════════════════════════════════════════
#  HTML HELPERS
# ══════════════════════════════════════════════════
GRADS=["135deg,#0e3a6e,#0A84FF","135deg,#065f46,#30D158","135deg,#4a1d96,#BF5AF2",
       "135deg,#78350f,#FF9F0A","135deg,#7f1d1d,#FF453A","135deg,#134e4a,#32ADE6",
       "135deg,#1e3a8a,#5E5CE6","135deg,#3b1f6e,#BF5AF2"]
def ugrad(e): return f"linear-gradient({GRADS[hash(e or '')%len(GRADS)]})"
def avh(initials, sz=40, grad=None):
    fs=max(sz//3,8); bg=grad or "linear-gradient(135deg,#0A84FF,#30D158)"
    return(f'<div style="width:{sz}px;height:{sz}px;border-radius:50%;background:{bg};'
           f'display:flex;align-items:center;justify-content:center;'
           f'font-family:Syne,sans-serif;font-weight:800;font-size:{fs}px;color:white;'
           f'flex-shrink:0;border:1.5px solid rgba(255,255,255,.12)">{initials}</div>')
def tags_html(tags,cls="tag"): return ''.join(f'<span class="{cls}">{t}</span>' for t in(tags or []))
def badge(s):
    m={"Publicado":"badge-teal","Concluído":"badge-pur"}
    return f'<span class="{m.get(s,"badge-orn")}">{s}</span>'
def pc_dark(title=""):
    t={"text":title,"font":{"color":"#D8E4F5","family":"Syne","size":11}} if title else {}
    return dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#3A4D6A",family="Inter",size=10),
                title=t,margin=dict(l=10,r=10,t=36 if title else 10,b=10),
                xaxis=dict(showgrid=False,color="#3A4D6A",tickfont=dict(size=9)),
                yaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,.03)",color="#3A4D6A",tickfont=dict(size=9)))

# ══════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════
def page_login():
    _,col,_=st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown("""<div style="text-align:center;margin-bottom:2.5rem">
  <div style="display:flex;align-items:center;justify-content:center;gap:12px;margin-bottom:.75rem">
    <div style="width:48px;height:48px;border-radius:14px;background:linear-gradient(135deg,#0A84FF,#30D158);
      display:flex;align-items:center;justify-content:center;font-size:1.3rem;
      box-shadow:0 0 24px rgba(10,132,255,.35)">N</div>
    <div style="font-family:Syne,sans-serif;font-size:2.5rem;font-weight:900;letter-spacing:-.07em;
      background:linear-gradient(135deg,#0A84FF,#30D158);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">Nebula</div>
  </div>
  <div style="color:#3A4D6A;font-size:.58rem;letter-spacing:.28em;text-transform:uppercase;font-weight:700">Plataforma de Pesquisa Científica</div>
</div>""",unsafe_allow_html=True)
        t_in,t_up=st.tabs(["  Entrar  ","  Criar conta  "])
        with t_in:
            with st.form("lf",clear_on_submit=False):
                em=st.text_input("E-mail",placeholder="seu@email.com",key="li_e")
                pw=st.text_input("Senha",placeholder="••••••••",type="password",key="li_p")
                sub=st.form_submit_button("Entrar",use_container_width=True)
                if sub:
                    u=st.session_state.users.get(em)
                    if not u: st.error("E-mail não encontrado.")
                    elif u["password"]!=hp(pw): st.error("Senha incorreta.")
                    else:
                        st.session_state.logged_in=True; st.session_state.current_user=em
                        area=u.get("area","")
                        update_profile([w.lower() for w in re.split(r'[\s,]+',area) if len(w)>3],2.0)
                        st.session_state.page="repository"; st.rerun()
            st.markdown('<div style="text-align:center;color:#3A4D6A;font-size:.64rem;margin-top:.6rem">Demo: demo@nebula.ai / demo123</div>',unsafe_allow_html=True)
        with t_up:
            with st.form("sf",clear_on_submit=False):
                nn=st.text_input("Nome completo",key="su_n")
                ne=st.text_input("E-mail",key="su_e")
                na=st.text_input("Área de pesquisa",key="su_a",placeholder="Ex: Neurociência Computacional")
                n_nat=st.selectbox("Nacionalidade",["Brasil"]+sorted([k for k in NATIONALITY_COORDS if k!="Brasil"]),key="su_nat")
                c1,c2=st.columns(2)
                with c1: np_=st.text_input("Senha",type="password",key="su_p")
                with c2: np2=st.text_input("Confirmar",type="password",key="su_p2")
                sub2=st.form_submit_button("Criar conta",use_container_width=True)
                if sub2:
                    if not all([nn,ne,na,np_,np2]): st.error("Preencha todos os campos.")
                    elif np_!=np2: st.error("Senhas não coincidem.")
                    elif len(np_)<6: st.error("Mínimo 6 caracteres.")
                    elif ne in st.session_state.users: st.error("E-mail já cadastrado.")
                    else:
                        st.session_state.users[ne]={"name":nn,"password":hp(np_),"bio":"","area":na,
                                                    "verified":True,"nationality":n_nat}
                        save_db(); st.session_state.logged_in=True; st.session_state.current_user=ne
                        update_profile([w.lower() for w in re.split(r'[\s,]+',na) if len(w)>3],3.0)
                        st.session_state.page="repository"; st.rerun()

# ══════════════════════════════════════════════════
#  SIDEBAR NAV
# ══════════════════════════════════════════════════
NAV=[("repository","Repositório","acc"),("search","Busca & Visao IA","teal"),
     ("folders","Pastas","orn"),("analysis","Análises","pur"),
     ("connections","Conexoes","teal"),("chat","Chat","acc"),("settings","Config","orn")]

def render_nav():
    email=st.session_state.current_user; u=guser(); cur=st.session_state.page
    g=ugrad(email); in_=ini(u.get("name","?"))
    with st.sidebar:
        st.markdown('<div class="sb-logo"><div class="sb-logo-icon">N</div><div class="sb-logo-txt">Nebula</div></div>',unsafe_allow_html=True)
        ak=st.session_state.get("api_key","")
        st.markdown('<div class="sb-lbl">Menu</div>',unsafe_allow_html=True)
        nav_labels={"repository":"Repositorio","search":"Busca & Visao","folders":"Pastas",
                    "analysis":"Analises","connections":"Conexoes","chat":"Chat","settings":"Configuracoes"}
        act_css=""
        colors={"acc":"#0A84FF","teal":"#30D158","orn":"#FF9F0A","pur":"#BF5AF2"}
        for i,(key,label,col) in enumerate(NAV):
            if cur==key and not st.session_state.profile_view:
                c=colors.get(col,"#0A84FF")
                act_css+=(f'section[data-testid="stSidebar"] [data-testid="stVerticalBlock"]'
                          f' > [data-testid="stVerticalBlock"]:nth-child({i+3}) .stButton>button'
                          f'{{color:{c}!important;-webkit-text-fill-color:{c}!important;'
                          f'background:rgba(10,132,255,.12)!important;'
                          f'border-color:{c}40!important;font-weight:700!important;}}')
        if act_css: st.markdown(f'<style>{act_css}</style>',unsafe_allow_html=True)
        for key,label,_ in NAV:
            if st.button(label,key=f"sb_{key}",use_container_width=True):
                st.session_state.profile_view=None; st.session_state.page=key; st.rerun()
        st.markdown("<hr>",unsafe_allow_html=True)
        st.markdown('<div class="sb-lbl">Anthropic API</div>',unsafe_allow_html=True)
        new_ak=st.text_input("",placeholder="sk-ant-...",type="password",key="sb_api",
                             label_visibility="collapsed",value=ak)
        if new_ak!=ak: st.session_state.api_key=new_ak
        if new_ak and new_ak.startswith("sk-"):
            st.markdown('<div style="font-size:.52rem;color:#30D158;padding:.05rem .15rem">Claude Vision ativo</div>',unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:.52rem;color:#3A4D6A;padding:.05rem .15rem">Insira chave para Claude Vision</div>',unsafe_allow_html=True)
        st.markdown("<hr>",unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:.1rem .1rem">'
                    f'{avh(in_,28,g)}<div><div style="font-weight:700;font-size:.73rem;color:#D8E4F5;'
                    f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:116px">{u.get("name","?")}</div>'
                    f'<div style="font-size:.55rem;color:#3A4D6A">{u.get("area","")[:20]}</div></div></div>',unsafe_allow_html=True)
        if st.button("Meu Perfil",key="sb_me",use_container_width=True):
            st.session_state.profile_view=email; st.rerun()

# ══════════════════════════════════════════════════
#  PROFILE
# ══════════════════════════════════════════════════
def page_profile(target_email):
    tu=st.session_state.users.get(target_email,{})
    if not tu: st.error("Perfil não encontrado."); return
    tname=tu.get("name","?"); is_me=st.session_state.current_user==target_email
    g=ugrad(target_email); in_t=ini(tname)
    user_research=[r for r in st.session_state.research_items if r.get("author_email")==target_email]
    total_cit=sum(r.get("citations",0) for r in user_research)
    vb=f' <span class="badge-teal" style="font-size:.57rem">Verificado</span>' if tu.get("verified") else ""
    st.markdown(f"""<div class="prof-hero">
  <div class="av" style="background:{g}">{in_t}</div>
  <div style="flex:1">
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:.2rem">
      <span style="font-family:Syne,sans-serif;font-weight:800;font-size:1.3rem;color:#fff">{tname}</span>{vb}
    </div>
    <div style="color:#0A84FF;font-size:.78rem;font-weight:600;margin-bottom:.3rem">{tu.get("area","")}</div>
    <div style="color:#7A8FAD;font-size:.75rem;line-height:1.7;margin-bottom:.7rem">{tu.get("bio","Sem bio.")}</div>
    <div style="display:flex;gap:1.5rem;flex-wrap:wrap">
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:.97rem;color:#fff">{len(user_research)}</span>
      <span style="color:#3A4D6A;font-size:.63rem"> pesquisas</span></div>
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:.97rem;color:#30D158">{total_cit}</span>
      <span style="color:#3A4D6A;font-size:.63rem"> citações</span></div>
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:.97rem;color:#BF5AF2">{tu.get("nationality","")}</span></div>
    </div>
  </div>
</div>""",unsafe_allow_html=True)
    if st.button("Voltar",key="pf_back",use_container_width=False): st.session_state.profile_view=None; st.rerun()
    if is_me:
        with st.form("pf_f"):
            n_name=st.text_input("Nome",value=tu.get("name",""))
            n_area=st.text_input("Area",value=tu.get("area",""))
            n_bio=st.text_area("Bio",value=tu.get("bio",""),height=70)
            if st.form_submit_button("Salvar",use_container_width=True):
                st.session_state.users[target_email].update({"name":n_name,"area":n_area,"bio":n_bio})
                save_db(); st.success("Salvo!"); st.rerun()
        if st.button("Sair da conta",key="logout2"): 
            st.session_state.logged_in=False; st.session_state.current_user=None; st.session_state.page="login"; st.rerun()
    for r in sorted(user_research,key=lambda x:x.get("date",""),reverse=True):
        render_research_card(r,show_author=False,ctx="prof")

# ══════════════════════════════════════════════════
#  RESEARCH CARD
# ══════════════════════════════════════════════════


def render_research_card(item, show_author=True, ctx="repo", compact=False, connection_count=None):
    iid = item["id"]
    aemail = item.get("author_email", "")
    aname = item.get("author", "?")
    dt = time_ago(item.get("date", ""))
    g = ugrad(aemail)
    ab = item.get("abstract", "")
    if compact and len(ab) > 180:
        ab = ab[:180] + "..."

    nat = item.get("nationality", "")
    yr = item.get("year", "")
    cit = item.get("citations", 0)
    method = item.get("methodology", "—")
    conn_count = connection_count if connection_count is not None else len(find_similar(item, 0.22, 20))
    detail_key = f"detail_{ctx}_{iid}"

    if show_author:
        hdr = (
            f'<div style="padding:.72rem 1rem .48rem;display:flex;align-items:center;gap:8px;'
            f'border-bottom:1px solid rgba(255,255,255,.04)">'
            f'{avh(ini(aname),34,g)}<div style="flex:1;min-width:0">'
            f'<div style="font-weight:700;font-size:.82rem;color:#fff">{aname}</div>'
            f'<div style="color:#3A4D6A;font-size:.60rem">{item.get("area", "")} · {nat} · {dt}</div>'
            f'</div>{badge(item["status"])}</div>'
        )
    else:
        hdr = (
            f'<div style="padding:.28rem 1rem .1rem;display:flex;justify-content:space-between;align-items:center">'
            f'<span style="color:#3A4D6A;font-size:.59rem">{dt} · {nat}</span>{badge(item["status"])}'
            f'</div>'
        )

    st.markdown(
        f'<div class="research-card">{hdr}'
        f'<div style="padding:.58rem 1rem .32rem">'
        f'<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.94rem;margin-bottom:.26rem;color:#fff;line-height:1.42">{item["title"]}</div>'
        f'<div style="color:#7A8FAD;font-size:.77rem;line-height:1.63;margin-bottom:.55rem">{ab}</div>'
        f'<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:.38rem">{tags_html(item.get("tags", [])[:5])}</div>'
        f'<div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px">'
        f'<div class="scard" style="margin:0;padding:.5rem .65rem"><div style="font-size:.53rem;color:#3A4D6A;text-transform:uppercase;letter-spacing:.08em">Ano</div><div style="font-size:.82rem;color:#D8E4F5;font-weight:700">{yr}</div></div>'
        f'<div class="scard" style="margin:0;padding:.5rem .65rem"><div style="font-size:.53rem;color:#3A4D6A;text-transform:uppercase;letter-spacing:.08em">Citações</div><div style="font-size:.82rem;color:#0A84FF;font-weight:700">{cit}</div></div>'
        f'<div class="scard" style="margin:0;padding:.5rem .65rem"><div style="font-size:.53rem;color:#3A4D6A;text-transform:uppercase;letter-spacing:.08em">Método</div><div style="font-size:.75rem;color:#D8E4F5;font-weight:600">{method}</div></div>'
        f'<div class="scard" style="margin:0;padding:.5rem .65rem"><div style="font-size:.53rem;color:#3A4D6A;text-transform:uppercase;letter-spacing:.08em">Conexões</div><div style="font-size:.82rem;color:#30D158;font-weight:700">{conn_count}</div></div>'
        f'</div></div></div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Mapear conexões", key=f"cn_{ctx}_{iid}", use_container_width=True):
            st.session_state.view_research = item
            st.session_state.page = "connections"
            st.rerun()
    with c2:
        if st.button("Detalhar pesquisa", key=f"dt_{ctx}_{iid}", use_container_width=True):
            st.session_state[detail_key] = not st.session_state.get(detail_key, False)
            st.rerun()

    if st.session_state.get(detail_key, False):
        related = find_similar(item, 0.22, 3)
        st.markdown('<div class="sc">', unsafe_allow_html=True)
        st.markdown(
            f'<div style="font-size:.56rem;color:#0A84FF;text-transform:uppercase;font-weight:700;letter-spacing:.10em;margin-bottom:.45rem">Leitura analítica</div>'
            f'<div style="font-size:.73rem;color:#D8E4F5;line-height:1.7;margin-bottom:.45rem">'
            f'Área: <strong>{item.get("area", "—")}</strong> · Método: <strong>{method}</strong> · Status: <strong>{item.get("status", "—")}</strong>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if related:
            st.markdown('<div style="font-size:.68rem;color:#30D158;font-weight:700;margin-bottom:.35rem">Conexões principais</div>', unsafe_allow_html=True)
            for sim, other in related:
                det = connection_details(item, other)
                st.markdown(
                    f'<div class="sim-card">'
                    f'<div style="display:flex;justify-content:space-between;gap:8px;margin-bottom:.25rem">'
                    f'<div style="font-size:.78rem;font-weight:700;color:#fff">{other["title"][:70]}</div>'
                    f'<div style="font-size:.62rem;color:#30D158;font-weight:800;white-space:nowrap">{round(sim*100)}%</div>'
                    f'</div>'
                    f'<div style="font-size:.62rem;color:#3A4D6A;margin-bottom:.25rem">{other.get("area", "")} · {other.get("methodology", "")}</div>'
                    f'<div style="font-size:.68rem;color:#7A8FAD;margin-bottom:.25rem">{" • ".join(det["reasons"][:3])}</div>'
                    f'{"<div>" + tags_html(det["shared_terms"][:6], "tag-teal") + "</div>" if det["shared_terms"] else ""}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<div style="font-size:.7rem;color:#7A8FAD">Nenhuma conexão forte encontrada ainda para esta pesquisa.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════
#  REPOSITORY — main page
# ══════════════════════════════════════════════════


def page_repository():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.7rem;margin-bottom:.25rem">Repositório de Pesquisa</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:#3A4D6A;font-size:.74rem;margin-bottom:.8rem">Ambiente acadêmico para leitura, comparação e conexão entre pesquisas.</p>', unsafe_allow_html=True)

    email = st.session_state.current_user
    u = guser()
    all_items = list(st.session_state.research_items)
    all_edges = build_connection_edges(all_items, threshold=0.22)
    conn_map = connection_count_map(all_items, all_edges)
    recs = get_recommendations(email, 6)
    interests = get_interests(email, 8)

    col_main, col_side = st.columns([2.25, .95], gap="medium")

    with col_main:
        with st.expander("Publicar nova pesquisa"):
            with st.form("pub_form"):
                title = st.text_input("Título", placeholder="Título da pesquisa...")
                abstract = st.text_area("Resumo / Abstract", height=90, placeholder="Descreva sua pesquisa, metodologia, corpus e resultados...")
                c1, c2, c3 = st.columns(3)
                with c1:
                    tags_in = st.text_input("Tags", placeholder="tag1, tag2, tag3")
                with c2:
                    meth = st.selectbox("Metodologia", ["experimental", "computacional", "observacional", "revisao sistematica", "estudo clinico", "outro"])
                with c3:
                    status = st.selectbox("Status", ["Em andamento", "Publicado", "Concluido"])
                c4, c5 = st.columns(2)
                with c4:
                    year_in = st.number_input("Ano", min_value=1900, max_value=2030, value=datetime.now().year)
                with c5:
                    nat_options = ["Brasil"] + sorted([k for k in NATIONALITY_COORDS if k != "Brasil"])
                    nat_in = st.selectbox("Nacionalidade", nat_options)
                sub = st.form_submit_button("Publicar", use_container_width=True)
                if sub and title and abstract:
                    tags = [t.strip() for t in tags_in.split(",") if t.strip()] if tags_in else []
                    new_r = {
                        "id": int(datetime.now().timestamp()) + random.randint(0, 999),
                        "author": u.get("name", "?"),
                        "author_email": email,
                        "area": u.get("area", ""),
                        "nationality": nat_in,
                        "year": int(year_in),
                        "title": title,
                        "abstract": abstract,
                        "tags": tags,
                        "methodology": meth,
                        "citations": 0,
                        "views": 1,
                        "likes": 0,
                        "liked_by": [],
                        "saved_by": [],
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "status": status,
                    }
                    st.session_state.research_items.insert(0, new_r)
                    update_profile(tags, 2.5)
                    save_db()
                    st.success("Pesquisa publicada!")
                    st.rerun()

        q_col, sort_col = st.columns([3.3, 1.2])
        with q_col:
            repo_query = st.text_input("", placeholder="Pesquisar título, autor, resumo, tag, método ou área...", key="repo_query", label_visibility="collapsed")
        with sort_col:
            sort_mode = st.selectbox("Ordenar por", ["Mais recentes", "Mais conectadas", "Mais citadas", "Relevantes para mim"], key="repo_sort")

        ff = st.radio("", ["Todas", "Minhas", "Por área", "Relacionadas", "Publicadas"], horizontal=True, key="rf2", label_visibility="collapsed")
        items = list(all_items)
        if ff == "Minhas":
            items = [r for r in items if r.get("author_email") == email]
        elif ff == "Por área":
            area = _norm_text(u.get("area", ""))
            items = [r for r in items if area and (area in _norm_text(r.get("area", "")) or area in " ".join([_norm_text(t) for t in r.get("tags", [])]))]
        elif ff == "Relacionadas":
            items = recs if recs else items
        elif ff == "Publicadas":
            items = [r for r in items if _norm_text(r.get("status", "")) == "publicado"]

        if repo_query:
            q = _norm_text(repo_query)
            items = [
                r for r in items
                if q in _norm_text(r.get("title", ""))
                or q in _norm_text(r.get("abstract", ""))
                or q in _norm_text(r.get("author", ""))
                or q in _norm_text(r.get("area", ""))
                or q in _norm_text(r.get("methodology", ""))
                or any(q in _norm_text(t) for t in r.get("tags", []))
            ]

        if sort_mode == "Mais conectadas":
            items = sorted(items, key=lambda x: (conn_map.get(x["id"], 0), x.get("citations", 0), x.get("date", "")), reverse=True)
        elif sort_mode == "Mais citadas":
            items = sorted(items, key=lambda x: (x.get("citations", 0), conn_map.get(x["id"], 0), x.get("date", "")), reverse=True)
        elif sort_mode == "Relevantes para mim":
            interest_set = set(get_interests(email, 20)) | {_norm_text(u.get("area", ""))}
            def personal_score(item):
                item_terms = research_terms(item, 10)
                overlap = len({t for t in interest_set if t} & item_terms)
                return overlap * 10 + conn_map.get(item["id"], 0) * 2 + item.get("citations", 0) * 0.4
            items = sorted(items, key=personal_score, reverse=True)
        else:
            items = sorted(items, key=lambda x: (x.get("date", ""), x.get("citations", 0)), reverse=True)

        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f'<div class="mbox"><div class="mval-acc">{len(items)}</div><div class="mlbl">Pesquisas visíveis</div></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="mbox"><div class="mval-teal">{len(all_edges)}</div><div class="mlbl">Conexões mapeadas</div></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="mbox"><div class="mval-pur">{len(set(r.get("area", "") for r in all_items if r.get("area")))}</div><div class="mlbl">Áreas de pesquisa</div></div>', unsafe_allow_html=True)
        st.markdown('<div style="height:.35rem"></div>', unsafe_allow_html=True)

        if not items:
            st.markdown('<div class="glass-card" style="padding:3.5rem;text-align:center;color:#3A4D6A">Nenhuma pesquisa encontrada para esse recorte.</div>', unsafe_allow_html=True)
        else:
            for r in items:
                render_research_card(r, ctx="repo", connection_count=conn_map.get(r["id"], 0))

    with col_side:
        st.markdown('<div class="sc">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.78rem;margin-bottom:.65rem;color:#fff">Eixos do seu perfil</div>', unsafe_allow_html=True)
        if interests:
            for i, interest in enumerate(interests[:8]):
                pct = max(18, 100 - i * 10)
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:.28rem">'
                    f'<div style="flex:1;font-size:.72rem;color:#7A8FAD;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{interest}</div>'
                    f'<div style="width:{pct}px;height:4px;background:linear-gradient(90deg,#0A84FF,#30D158);border-radius:4px;flex-shrink:0"></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<div style="font-size:.7rem;color:#7A8FAD">Publique pesquisas, busque artigos e analise documentos para enriquecer seu perfil acadêmico.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sc">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.78rem;margin-bottom:.65rem;color:#fff">Referências acadêmicas sugeridas</div>', unsafe_allow_html=True)
        top_interest = " ".join(interests[:3]) if interests else u.get("area", "science")
        ck = f"recs_{email}_{top_interest[:30]}"
        if ck not in st.session_state.scholar_cache:
            try:
                with st.spinner("Buscando referências..."):
                    st.session_state.scholar_cache[ck] = search_ss(top_interest, 4)
            except:
                st.session_state.scholar_cache[ck] = []
        for a in st.session_state.scholar_cache.get(ck, [])[:3]:
            st.markdown(
                f'<div style="padding:.38rem 0;border-bottom:1px solid rgba(255,255,255,.04)">'
                f'<div style="font-size:.74rem;font-weight:600;color:#D8E4F5;line-height:1.4;margin-bottom:.18rem">{a["title"][:65]}...</div>'
                f'<div style="font-size:.59rem;color:#3A4D6A">{a["authors"][:40]} · {a["year"]}{" · " + str(a.get("citations", 0)) + " cit." if a.get("citations") else ""}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if a.get("url"):
                st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:#0A84FF;font-size:.67rem;text-decoration:none">Abrir referência</a>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sc">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.78rem;margin-bottom:.65rem;color:#fff">Temas recorrentes</div>', unsafe_allow_html=True)
        all_tags = Counter(t.lower() for r in all_items for t in r.get("tags", []))
        if all_tags:
            for t, cnt in all_tags.most_common(6):
                st.markdown(
                    f'<div style="padding:.28rem 0;border-bottom:1px solid rgba(255,255,255,.04)">'
                    f'<div style="font-size:.73rem;font-weight:600;color:#0A84FF">{t}</div>'
                    f'<div style="font-size:.57rem;color:#3A4D6A">{cnt} ocorrências no repositório</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<div style="font-size:.7rem;color:#7A8FAD">Ainda não há temas recorrentes cadastrados.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════
#  SEARCH + VISION IA (merged)
# ══════════════════════════════════════════════════
def render_article(a, idx=0, ctx="web"):
    sc="#0A84FF" if a.get("origin")=="semantic" else "#30D158"; sn="S2" if a.get("origin")=="semantic" else "CR"
    cite=f" · {a['citations']} cit." if a.get("citations") else ""
    uid=re.sub(r'[^a-zA-Z0-9]','',f"{ctx}_{idx}_{str(a.get('doi',''))[:8]}")[:28]
    is_saved=any(s.get('doi')==a.get('doi') for s in st.session_state.saved_articles)
    ab=(a.get("abstract","") or "")[:260]
    st.markdown(f'<div class="scard"><div style="display:flex;align-items:flex-start;gap:7px;margin-bottom:.24rem">'
                f'<div style="flex:1;font-family:Syne,sans-serif;font-weight:700;font-size:.84rem;color:#fff">{a["title"]}</div>'
                f'<span style="font-size:.56rem;color:{sc};border:1px solid {sc}30;border-radius:7px;padding:2px 6px;white-space:nowrap;flex-shrink:0">{sn}</span></div>'
                f'<div style="color:#3A4D6A;font-size:.60rem;margin-bottom:.25rem">{a["authors"]} · <em>{a["source"]}</em> · {a["year"]}{cite}</div>'
                f'<div style="color:#7A8FAD;font-size:.74rem;line-height:1.62">{ab}{"..." if len(a.get("abstract",""))>260 else ""}</div></div>',unsafe_allow_html=True)
    ca,cb,cc=st.columns(3)
    with ca:
        lbl="Remover" if is_saved else "Salvar"
        if st.button(lbl,key=f"svw_{uid}"):
            if is_saved: st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]; st.toast("Removido")
            else: st.session_state.saved_articles.append(a); st.toast("Salvo!")
            save_db(); st.rerun()
    with cb:
        if st.button("Citar",key=f"ctw_{uid}"): st.toast(f'{a["authors"]} ({a["year"]}). {a["title"]}.')
    with cc:
        if a.get("url"): st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:#0A84FF;font-size:.75rem;text-decoration:none;line-height:2.3;display:block">Abrir</a>',unsafe_allow_html=True)

def page_search():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.7rem;margin-bottom:.25rem">Busca e Visao IA</h1>',unsafe_allow_html=True)
    st.markdown('<p style="color:#3A4D6A;font-size:.74rem;margin-bottom:.8rem">Busca de artigos · Pesquisa por imagem · Analise de imagem com ML + Claude Vision</p>',unsafe_allow_html=True)
    api_key=st.session_state.get("api_key",""); has_api=bool(api_key and api_key.startswith("sk-"))
    t_text,t_img=st.tabs(["  Busca por texto  ","  Busca por imagem / Vision IA  "])

    with t_text:
        with st.form("sf_text"):
            c1,c2=st.columns([4,1])
            with c1: q=st.text_input("",placeholder="CRISPR · quantum ML · dark matter · neuroplasticidade...",key="sq",label_visibility="collapsed")
            with c2: sub=st.form_submit_button("Buscar",use_container_width=True)
            if sub and q:
                with st.spinner("Buscando..."):
                    nb=[r for r in st.session_state.research_items if q.lower() in r["title"].lower() or q.lower() in r["abstract"].lower()]
                    ss_r=search_ss(q,6); cr_r=search_cr(q,4)
                    st.session_state.search_results={"nebula":nb,"ss":ss_r,"cr":cr_r}; st.session_state.last_sq=q
                    update_profile([q.lower()],0.5)
        # Also search in folders
        if st.session_state.get("search_results") and st.session_state.get("last_sq"):
            q_s=st.session_state.last_sq; res=st.session_state.search_results
            neb=res.get("nebula",[]); ss=res.get("ss",[]); cr=res.get("cr",[])
            web=ss+[x for x in cr if not any(x["title"].lower()==s["title"].lower() for s in ss)]
            # Search in user folders
            folder_matches=[]
            for fn,fd in st.session_state.folders.items():
                if not isinstance(fd,dict): continue
                for fname,an in fd.get("analyses",{}).items():
                    if q_s.lower() in fname.lower() or any(q_s.lower() in kw for kw in an.get("keywords",[])):
                        folder_matches.append({"folder":fn,"file":fname,"keywords":an.get("keywords",[])[:6],"topics":an.get("topics",{}),"relevance":an.get("relevance_score",0)})
            t_all,t_neb,t_web,t_fold=st.tabs([f"Todos ({len(neb)+len(web)})",f"Nebula ({len(neb)})",f"Internet ({len(web)})",f"Suas Pastas ({len(folder_matches)})"])
            with t_all:
                if neb:
                    st.markdown('<div style="font-size:.56rem;color:#0A84FF;font-weight:700;margin-bottom:.35rem;text-transform:uppercase;letter-spacing:.1em">Na Nebula</div>',unsafe_allow_html=True)
                    for r in neb: render_research_card(r,ctx="sa",compact=True)
                if web:
                    if neb: st.markdown('<hr>',unsafe_allow_html=True)
                    st.markdown('<div style="font-size:.56rem;color:#30D158;font-weight:700;margin-bottom:.35rem;text-transform:uppercase;letter-spacing:.1em">Internet</div>',unsafe_allow_html=True)
                    for i,a in enumerate(web): render_article(a,i,"aw")
                if not neb and not web: st.info("Nenhum resultado.")
            with t_neb:
                for r in neb: render_research_card(r,ctx="sn",compact=True)
                if not neb: st.info("Nenhuma pesquisa.")
            with t_web:
                for i,a in enumerate(web): render_article(a,i,"wt")
                if not web: st.info("Nenhum artigo.")
            with t_fold:
                if folder_matches:
                    for fm in folder_matches:
                        st.markdown(f'<div class="scard"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.83rem;color:#fff;margin-bottom:.22rem">{fm["file"]}</div>'
                                    f'<div style="font-size:.63rem;color:#3A4D6A;margin-bottom:.25rem">Pasta: {fm["folder"]} · Relevancia: {fm["relevance"]}%</div>'
                                    f'<div>{tags_html(fm["keywords"][:5])}</div></div>',unsafe_allow_html=True)
                else:
                    st.markdown('<div style="color:#3A4D6A;padding:.8rem">Nenhum resultado nas suas pastas.</div>',unsafe_allow_html=True)

    with t_img:
        st.markdown('<div class="ai-disc"><span style="font-size:.64rem;color:#FF9F0A;font-weight:600">Aviso: </span><span style="font-size:.62rem;color:#7A8FAD">Analise realizada por IA e processamento ML. Resultados podem conter erros — valide com especialista qualificado.</span></div>',unsafe_allow_html=True)
        if has_api:
            st.markdown('<div class="pbox-teal" style="margin-bottom:.6rem"><div style="font-size:.7rem;color:#30D158;font-weight:600">Claude Vision Ativo</div><div style="font-size:.63rem;color:#7A8FAD">Analise real com IA + busca de artigos relacionados + busca em suas pastas</div></div>',unsafe_allow_html=True)
        cu,cr2=st.columns([1,1.8])
        with cu:
            img_f=st.file_uploader("Imagem cientifica",type=["png","jpg","jpeg","webp","tiff"],key="img_up2")
            img_bytes=None
            if img_f: img_f.seek(0); img_bytes=img_f.read(); st.image(img_bytes,use_container_width=True)
            run_ml_btn=st.button("Analisar (Pipeline ML)",key="btn_ml",use_container_width=True)
            run_vision_btn=False
            if img_bytes and has_api:
                run_vision_btn=st.button("Claude Vision (IA Real)",key="btn_cv",use_container_width=True)
        with cr2:
            if img_bytes and run_ml_btn:
                with st.spinner("Executando Sobel · Canny · FFT · Textura..."):
                    ml=run_ml(img_bytes)
                st.session_state.img_result=ml
                if not ml.get("ok"): st.error(ml.get("error","Erro no pipeline"))
                else:
                    cls_=ml["classification"]; col_info=ml["color"]; conf_c=VIB[1] if cls_["confidence"]>80 else(VIB[0] if cls_["confidence"]>60 else VIB[2])
                    st.markdown(f'<div class="ai-card"><div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:.5rem">'
                                f'<div><div style="font-size:.54rem;color:#3A4D6A;text-transform:uppercase;letter-spacing:.10em;margin-bottom:4px">Pipeline ML</div>'
                                f'<div style="font-family:Syne,sans-serif;font-weight:800;font-size:1rem;color:#fff;margin-bottom:2px">{cls_["category"]}</div></div>'
                                f'<div style="text-align:center;background:rgba(0,0,0,.3);border-radius:10px;padding:.4rem .75rem;flex-shrink:0">'
                                f'<div style="font-family:Syne,sans-serif;font-weight:900;font-size:1.4rem;color:{conf_c}">{cls_["confidence"]}%</div>'
                                f'<div style="font-size:.48rem;color:#3A4D6A;text-transform:uppercase">confianca</div></div></div>'
                                f'<div style="font-size:.61rem;color:#3A4D6A;margin-bottom:.25rem">{'  '.join(f"{k}: {v}pt" for k,v in list(cls_["all_scores"].items())[:4])}</div></div>',unsafe_allow_html=True)
                    sb=ml.get("sobel",{}); tx=ml.get("texture",{}); fft_r=ml.get("fft",{})
                    c1m,c2m,c3m,c4m=st.columns(4)
                    with c1m: st.markdown(f'<div class="mbox"><div style="font-weight:800;font-size:.95rem;color:#0A84FF">{sb.get("mean",0):.4f}</div><div class="mlbl">Sobel</div></div>',unsafe_allow_html=True)
                    with c2m: st.markdown(f'<div class="mbox"><div style="font-weight:800;font-size:.95rem;color:#30D158">{tx.get("texture_type","—")}</div><div class="mlbl">Textura</div></div>',unsafe_allow_html=True)
                    with c3m: st.markdown(f'<div class="mbox"><div style="font-weight:800;font-size:.95rem;color:#BF5AF2">{"Perio." if fft_r.get("is_periodic") else "Aperio."}</div><div class="mlbl">FFT</div></div>',unsafe_allow_html=True)
                    with c4m: st.markdown(f'<div class="mbox"><div style="font-weight:800;font-size:.95rem;color:#FF9F0A">{col_info.get("entropy",0):.2f}</div><div class="mlbl">Entropia</div></div>',unsafe_allow_html=True)
                    t_ml1,t_ml2,t_ml3=st.tabs(["  Bordas & FFT  ","  Cores  ","  Histograma  "])
                    with t_ml1:
                        eh=sb.get("hist",[1]*16)
                        fig_e=go.Figure(go.Bar(y=eh,marker=dict(color=list(range(len(eh))),colorscale=[[0,"#0A1020"],[.4,"#0A84FF"],[.8,"#30D158"],[1,"#FFD60A"]])))
                        fig_e.update_layout(**{**pc_dark("Distribuicao Sobel"),'height':155,'margin':dict(l=10,r=10,t=32,b=8)})
                        st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_e,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
                        lf=fft_r.get("lf",0); mf=fft_r.get("mf",0); hf=fft_r.get("hf",0)
                        fig_f=go.Figure(go.Bar(x=["Baixa","Media","Alta"],y=[lf,mf,hf],marker=dict(color=["#0A84FF","#30D158","#BF5AF2"]),text=[f"{v:.3f}" for v in [lf,mf,hf]],textposition="outside",textfont=dict(color="#3A4D6A",size=9)))
                        fig_f.update_layout(**{**pc_dark("FFT Frequencias"),'height':155,'margin':dict(l=10,r=10,t=32,b=8)})
                        st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_f,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
                    with t_ml2:
                        pal=ml.get("palette",[])
                        for cp in pal[:6]:
                            hx=cp.get("hex","#888"); r2,g2,b2=cp.get("rgb",(128,128,128)); pct=cp.get("pct",0)
                            st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:.32rem"><div style="width:26px;height:26px;border-radius:6px;background:{hx};border:1px solid rgba(255,255,255,.1);flex-shrink:0"></div><div style="flex:1"><div style="display:flex;justify-content:space-between;font-size:.66rem;color:#7A8FAD;margin-bottom:2px"><span>{hx.upper()}</span><span>{pct:.1f}%</span></div><div style="height:4px;width:{min(int(pct*3),100)}%;background:{hx};border-radius:3px;max-width:100%"></div></div></div>',unsafe_allow_html=True)
                    with t_ml3:
                        hd=ml.get("histograms",{})
                        if hd:
                            fig4=go.Figure()
                            bx2=list(range(0,256,8))[:32]
                            fig4.add_trace(go.Scatter(x=bx2,y=hd.get("r",[])[:32],fill='tozeroy',name='R',line=dict(color='rgba(255,69,58,.9)',width=1.5),fillcolor='rgba(255,69,58,.08)'))
                            fig4.add_trace(go.Scatter(x=bx2,y=hd.get("g",[])[:32],fill='tozeroy',name='G',line=dict(color='rgba(48,209,88,.9)',width=1.5),fillcolor='rgba(48,209,88,.08)'))
                            fig4.add_trace(go.Scatter(x=bx2,y=hd.get("b",[])[:32],fill='tozeroy',name='B',line=dict(color='rgba(10,132,255,.9)',width=1.5),fillcolor='rgba(10,132,255,.08)'))
                            fig4.update_layout(**{**pc_dark("Histograma RGB"),'height':165,'margin':dict(l=10,r=10,t=32,b=8),'legend':dict(font=dict(color="#3A4D6A",size=8))})
                            st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig4,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
                    # Search related in folders and internet
                    kw_s=cls_["search_kw"]
                    st.markdown('<div class="dtxt">Pesquisas relacionadas</div>',unsafe_allow_html=True)
                    t_r1,t_r2,t_r3=st.tabs(["Nebula","Suas Pastas","Internet"])
                    with t_r1:
                        kl=kw_s.lower().split()[:5]
                        nr=sorted([(sum(1 for k in kl if k in (r.get("title","")+" "+r.get("abstract","")).lower()),r) for r in st.session_state.research_items],key=lambda x:-x[0])
                        for _,r in [x for x in nr if x[0]>0][:4]: render_research_card(r,ctx="img_n",compact=True)
                        if not [x for x in nr if x[0]>0]: st.info("Nenhuma pesquisa similar.")
                    with t_r2:
                        folder_img=[]
                        for fn,fd in st.session_state.folders.items():
                            if not isinstance(fd,dict): continue
                            for fname,an in fd.get("analyses",{}).items():
                                score=sum(1 for k in kl if any(k in kw for kw in an.get("keywords",[])))
                                if score>0: folder_img.append((score,fn,fname,an))
                        folder_img.sort(key=lambda x:-x[0])
                        for _,fn,fname,an in folder_img[:4]:
                            st.markdown(f'<div class="scard"><div style="font-weight:700;font-size:.82rem;color:#fff;margin-bottom:.2rem">{fname}</div>'
                                        f'<div style="font-size:.62rem;color:#3A4D6A">Pasta: {fn}</div>'
                                        f'<div style="margin-top:.25rem">{tags_html(an.get("keywords",[])[:5])}</div></div>',unsafe_allow_html=True)
                        if not folder_img: st.info("Nenhum documento similar nas pastas.")
                    with t_r3:
                        ck_img=f"img_{kw_s[:35]}"
                        if ck_img not in st.session_state.scholar_cache:
                            with st.spinner("Buscando..."):
                                st.session_state.scholar_cache[ck_img]=search_ss(kw_s,5)
                        for i,a in enumerate(st.session_state.scholar_cache.get(ck_img,[])): render_article(a,i,"img_w")
            elif img_bytes and run_vision_btn:
                with st.spinner("Claude analisando a imagem..."):
                    ai_text,ai_err=call_vision(img_bytes,api_key)
                if ai_err: st.error(f"Erro Claude Vision: {ai_err}")
                elif ai_text:
                    try:
                        clean=re.sub(r'```json\s*','',ai_text).replace('```','').strip()
                        ai_d=json.loads(clean)
                        tipo=ai_d.get("tipo","—"); origem=ai_d.get("origem","—"); desc=ai_d.get("descricao","—")
                        estruturas=ai_d.get("estruturas",[]); tecnica=ai_d.get("tecnica","—")
                        confianca=ai_d.get("confianca",0); termos=ai_d.get("termos_busca","")
                        interp=ai_d.get("interpretacao",""); aviso=ai_d.get("aviso","")
                        cc2="#30D158" if confianca>80 else("#0A84FF" if confianca>60 else "#FF9F0A")
                        st.markdown(f'''<div class="ai-card" style="border-color:rgba(48,209,88,.25)">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:.65rem">
    <div>
      <div style="font-size:.53rem;color:#30D158;text-transform:uppercase;letter-spacing:.10em;font-weight:700;margin-bottom:3px">Claude Vision</div>
      <div style="font-family:Syne,sans-serif;font-weight:800;font-size:1rem;color:#fff;margin-bottom:2px">{tipo}</div>
      <div style="color:#30D158;font-size:.74rem;font-weight:600">{origem}</div>
    </div>
    <div style="text-align:center;background:rgba(0,0,0,.3);border-radius:10px;padding:.4rem .75rem;flex-shrink:0">
      <div style="font-family:Syne,sans-serif;font-weight:900;font-size:1.35rem;color:{cc2}">{confianca}%</div>
      <div style="font-size:.47rem;color:#3A4D6A;text-transform:uppercase">confianca</div>
    </div>
  </div>
  <div style="background:rgba(0,0,0,.22);border-radius:9px;padding:.55rem .75rem;margin-bottom:.5rem;font-size:.75rem;color:#D8E4F5;line-height:1.65">{desc}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:.45rem;margin-bottom:.45rem;font-size:.71rem">
    <div style="color:#7A8FAD">Tecnica: <strong style="color:#fff">{tecnica}</strong></div>
    <div style="color:#7A8FAD">Qualidade: <strong style="color:#FF9F0A">{ai_d.get("qualidade","—")}</strong></div>
  </div>
  {f"<div style='font-size:.70rem;color:#7A8FAD;margin-bottom:.35rem'>Estruturas: {', '.join(estruturas)}</div>" if estruturas else ""}
  {f"<div style='background:rgba(48,209,88,.04);border:1px solid rgba(48,209,88,.12);border-radius:8px;padding:.45rem .65rem;font-size:.71rem;color:#7A8FAD;line-height:1.65'>{interp}</div>" if interp else ""}
  {f"<div style='margin-top:.4rem;font-size:.61rem;color:#FF9F0A'>{aviso}</div>" if aviso else ""}
</div>''',unsafe_allow_html=True)
                        if termos:
                            with st.spinner("Buscando artigos..."):
                                art=search_ss(termos,5)
                            st.markdown('<div class="dtxt">Artigos relacionados</div>',unsafe_allow_html=True)
                            for i,a in enumerate(art): render_article(a,i,"cv_w")
                    except:
                        st.markdown(f'<div class="abox"><div style="font-size:.75rem;color:#7A8FAD;white-space:pre-wrap">{ai_text[:1200]}</div></div>',unsafe_allow_html=True)
            elif not img_f:
                st.markdown('<div class="glass-card" style="padding:4rem 2rem;text-align:center;margin-top:.5rem">'
                            '<div style="font-size:2.5rem;opacity:.12;margin-bottom:.85rem">N</div>'
                            '<div style="font-family:Syne,sans-serif;font-size:.96rem;color:#D8E4F5">Carregue uma imagem cientifica</div>'
                            '<div style="font-size:.68rem;color:#3A4D6A;margin-top:.4rem;line-height:1.9">Pipeline ML: Sobel · Canny · FFT · Textura · Paleta<br>Com API Key: Claude Vision para analise real</div></div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════
#  FOLDERS
# ══════════════════════════════════════════════════
def page_folders():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.7rem;margin-bottom:.8rem">Pastas de Pesquisa</h1>',unsafe_allow_html=True)
    u=guser(); ra=u.get("area","")
    with st.form("nff"):
        c1,c2,c3=st.columns([2,1.5,.7])
        with c1: nfn=st.text_input("Nome da pasta",placeholder="Ex: Genomica Comparativa")
        with c2: nfd=st.text_input("Descricao",placeholder="Breve descricao")
        with c3:
            st.markdown('<div style="margin-top:1.65rem">',unsafe_allow_html=True)
            sub_nf=st.form_submit_button("Criar",use_container_width=True)
            st.markdown('</div>',unsafe_allow_html=True)
        if sub_nf:
            if nfn.strip():
                if nfn not in st.session_state.folders: st.session_state.folders[nfn]={"desc":nfd,"files":[],"notes":"","analyses":{}}; save_db(); st.success(f"Pasta '{nfn}' criada!"); st.rerun()
                else: st.warning("Ja existe.")
            else: st.warning("Digite um nome.")
    if not st.session_state.folders:
        st.markdown('<div class="glass-card" style="text-align:center;padding:3.5rem;color:#3A4D6A">Nenhuma pasta criada.</div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True); return
    for fn,fd in list(st.session_state.folders.items()):
        if not isinstance(fd,dict): fd={"files":fd,"desc":"","notes":"","analyses":{}}; st.session_state.folders[fn]=fd
        files=fd.get("files",[]); analyses=fd.get("analyses",{})
        with st.expander(f"{fn}  —  {len(files)} arquivo(s)  ·  {len(analyses)} analise(s)"):
            up=st.file_uploader("",type=None,key=f"up_{fn}",label_visibility="collapsed",accept_multiple_files=True)
            if up:
                fb=st.session_state.folder_bytes.setdefault(fn,{})
                for uf in up:
                    if uf.name not in files: files.append(uf.name)
                    uf.seek(0); fb[uf.name]=uf.read()
                fd["files"]=files; save_db(); st.success(f"{len(up)} arquivo(s) adicionado(s)!")
            icons={"PDF":"[PDF]","Word":"[DOC]","Planilha":"[XLS]","Dados":"[CSV]","Codigo":"[PY]","Imagem":"[IMG]","Markdown":"[MD]","Notebook":"[NB]"}
            for f in files:
                ft2=ftype(f); ha=f in analyses; ic=icons.get(ft2,"[?]")
                ab_=f'  <span class="badge-teal" style="font-size:.54rem">analisado</span>' if ha else ''
                st.markdown(f'<div style="display:flex;align-items:center;gap:7px;padding:.32rem 0;border-bottom:1px solid rgba(255,255,255,.04)"><span style="font-size:.68rem;color:#0A84FF;font-weight:700;width:32px;flex-shrink:0">{ic}</span><span style="font-size:.72rem;color:#7A8FAD;flex:1">{f}</span>{ab_}</div>',unsafe_allow_html=True)
            ca2,cb2,_=st.columns([1.4,1.2,2])
            with ca2:
                if st.button("Analisar",key=f"an_{fn}",use_container_width=True):
                    if files:
                        pb=st.progress(0,"Iniciando..."); fb2=st.session_state.folder_bytes.get(fn,{})
                        for fi,f in enumerate(files):
                            pb.progress((fi+1)/len(files),f"Analisando {f[:25]}...")
                            analyses[f]=analyze_document(f,fb2.get(f,b""),ftype(f),ra)
                            if analyses[f].get("keywords"): update_profile(analyses[f]["keywords"][:5],0.8)
                        fd["analyses"]=analyses; save_db(); pb.empty(); st.success("Analise completa!"); st.rerun()
                    else: st.warning("Adicione arquivos primeiro.")
            with cb2:
                if st.button("Excluir pasta",key=f"df_{fn}",use_container_width=True):
                    del st.session_state.folders[fn]; save_db(); st.rerun()
            if analyses:
                with st.expander(f"Ver analises ({len(analyses)} documentos)"):
                    for f,an in analyses.items():
                        st.markdown(f'<div class="abox"><div style="font-weight:700;font-size:.83rem;margin-bottom:.25rem">{f}</div>'
                                    f'<div style="font-size:.72rem;color:#7A8FAD;margin-bottom:.35rem">{an.get("summary","")}</div>'
                                    f'<div style="display:flex;gap:1rem;margin-bottom:.3rem">'
                                    f'<div style="text-align:center"><div style="font-weight:800;font-size:1rem;color:{"#30D158" if an.get("relevance_score",0)>=70 else "#FF9F0A"}">{an.get("relevance_score",0)}%</div><div style="font-size:.52rem;color:#3A4D6A;text-transform:uppercase">Relevancia</div></div>'
                                    f'<div style="text-align:center"><div style="font-weight:800;font-size:1rem;color:#0A84FF">{an.get("word_count",0):,}</div><div style="font-size:.52rem;color:#3A4D6A;text-transform:uppercase">Palavras</div></div>'
                                    f'{"<div style=text-align:center><div style=font-weight:800;font-size:1rem;color:#BF5AF2>"+str(an.get("year","—"))+"</div><div style=font-size:.52rem;color:#3A4D6A;text-transform:uppercase>Ano</div></div>" if an.get("year") else ""}'
                                    f'</div>'
                                    f'{"<div style=font-size:.71rem;color:#7A8FAD;margin-bottom:.25rem>Autores: "+", ".join(an.get("authors",["—"])[:3])+"</div>" if an.get("authors") else ""}'
                                    f'{"<div style=font-size:.71rem;color:#7A8FAD;margin-bottom:.3rem>Nacionalidade detectada: <strong style=color:#30D158>"+an.get("nationality","—")+"</strong></div>" if an.get("nationality") else ""}'
                                    f'<div>{tags_html(an.get("keywords",[])[:12])}</div></div>',unsafe_allow_html=True)
                        if an.get("key_sentences"):
                            st.markdown('<div style="font-size:.6rem;color:#3A4D6A;text-transform:uppercase;font-weight:700;margin:.4rem 0 .2rem">Frases-chave extraidas</div>',unsafe_allow_html=True)
                            for sent in an["key_sentences"][:2]:
                                st.markdown(f'<div style="background:rgba(10,132,255,.04);border-left:3px solid rgba(10,132,255,.3);border-radius:0 8px 8px 0;padding:.38rem .65rem;margin-bottom:.22rem;font-size:.72rem;color:#7A8FAD;line-height:1.6;font-style:italic">{sent}</div>',unsafe_allow_html=True)
            note=st.text_area("Notas",value=fd.get("notes",""),key=f"nt_{fn}",height=55,label_visibility="collapsed",placeholder="Notas da pasta...")
            if st.button("Salvar nota",key=f"sn_{fn}"): fd["notes"]=note; save_db(); st.success("Salvo!")
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════
#  ANALYSIS — deep analytics + 3D map
# ══════════════════════════════════════════════════
def page_analysis():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.7rem;margin-bottom:.8rem">Analises e Metricas</h1>',unsafe_allow_html=True)
    email=st.session_state.current_user
    t_repo,t_pastas,t_mapa,t_impacto=st.tabs(["  Repositorio  ","  Pastas  ","  Mapa Mundial  ","  Impacto  "])

    with t_repo:
        # Research analytics
        items=st.session_state.research_items
        if not items:
            st.info("Nenhuma pesquisa no repositorio.")
        else:
            c1,c2,c3,c4=st.columns(4)
            with c1: st.markdown(f'<div class="mbox"><div class="mval-acc">{len(items)}</div><div class="mlbl">Pesquisas</div></div>',unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="mbox"><div class="mval-teal">{sum(r.get("citations",0) for r in items)}</div><div class="mlbl">Citacoes</div></div>',unsafe_allow_html=True)
            with c3:
                areas_cnt=Counter(r.get("area","") for r in items)
                st.markdown(f'<div class="mbox"><div class="mval-pur">{len(areas_cnt)}</div><div class="mlbl">Areas</div></div>',unsafe_allow_html=True)
            with c4:
                authors_cnt=Counter(r.get("author","") for r in items)
                st.markdown(f'<div class="mbox"><div class="mval-orn">{len(authors_cnt)}</div><div class="mlbl">Autores</div></div>',unsafe_allow_html=True)

            # Year distribution
            years_cnt=Counter(r.get("year",2026) for r in items)
            if years_cnt:
                ylist=sorted(years_cnt.keys()); yvlist=[years_cnt[y] for y in ylist]
                fig_y=go.Figure(go.Bar(x=[str(y) for y in ylist],y=yvlist,marker=dict(color=yvlist,colorscale=[[0,"#0A1020"],[1,"#0A84FF"]]),text=yvlist,textposition="outside",textfont=dict(color="#3A4D6A",size=9)))
                fig_y.update_layout(**{**pc_dark("Pesquisas por Ano"),'height':200,'margin':dict(l=10,r=10,t=36,b=8)})
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_y,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)

            # Area distribution
            if areas_cnt:
                fig_a=go.Figure(go.Pie(labels=list(areas_cnt.keys()),values=list(areas_cnt.values()),hole=0.52,
                    marker=dict(colors=VIB[:len(areas_cnt)],line=dict(color=["#03060E"]*15,width=2)),textfont=dict(color="white",size=8)))
                fig_a.update_layout(height=240,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                    title=dict(text="Areas de Pesquisa",font=dict(color="#D8E4F5",family="Syne",size=11)),
                    legend=dict(font=dict(color="#3A4D6A",size=8)),margin=dict(l=0,r=0,t=36,b=0))
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_a,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)

            # Top authors
            st.markdown('<div class="dtxt">Top Autores</div>',unsafe_allow_html=True)
            auth_cit={r.get("author","?"):sum(x.get("citations",0) for x in items if x.get("author")==r.get("author")) for r in items}
            for auth,cit in sorted(auth_cit.items(),key=lambda x:-x[1])[:6]:
                nat_a=next((x.get("nationality","") for x in items if x.get("author")==auth),"")
                st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:.32rem 0;border-bottom:1px solid rgba(255,255,255,.04)">'
                            f'{avh(ini(auth),28,ugrad(auth+"@"))}'
                            f'<div style="flex:1"><div style="font-size:.74rem;font-weight:600;color:#D8E4F5">{auth}</div>'
                            f'<div style="font-size:.59rem;color:#3A4D6A">{nat_a}</div></div>'
                            f'<div style="font-weight:700;font-size:.82rem;color:#0A84FF">{cit}</div>'
                            f'<div style="font-size:.55rem;color:#3A4D6A">cit.</div></div>',unsafe_allow_html=True)

            # Methodology breakdown
            meth_cnt=Counter(r.get("methodology","outro") for r in items if r.get("methodology"))
            if meth_cnt:
                fig_m=go.Figure(go.Bar(x=list(meth_cnt.values()),y=list(meth_cnt.keys()),orientation='h',
                    marker=dict(color=list(range(len(meth_cnt))),colorscale=[[0,"#0e3a6e"],[1,"#0A84FF"]]),
                    text=list(meth_cnt.values()),textposition="outside",textfont=dict(color="#3A4D6A",size=9)))
                fig_m.update_layout(**{**pc_dark("Metodologias"),'height':max(140,len(meth_cnt)*35),'margin':dict(l=10,r=10,t=36,b=8),'yaxis':dict(showgrid=False,color="#3A4D6A",tickfont=dict(size=9))})
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_m,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)

    with t_pastas:
        folders=st.session_state.folders
        if not folders: st.info("Crie pastas e analise documentos.")
        else:
            all_an={f:an for fd in folders.values() if isinstance(fd,dict) for f,an in fd.get("analyses",{}).items()}
            if not all_an:
                st.info("Analise os documentos nas pastas primeiro.")
            else:
                tf=sum(len(fd.get("files",[]) if isinstance(fd,dict) else []) for fd in folders.values())
                c1,c2,c3,c4=st.columns(4)
                with c1: st.markdown(f'<div class="mbox"><div class="mval-acc">{len(folders)}</div><div class="mlbl">Pastas</div></div>',unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="mbox"><div class="mval-teal">{tf}</div><div class="mlbl">Arquivos</div></div>',unsafe_allow_html=True)
                with c3: st.markdown(f'<div class="mbox"><div class="mval-pur">{len(all_an)}</div><div class="mlbl">Analisados</div></div>',unsafe_allow_html=True)
                all_kw=[kw for an in all_an.values() for kw in an.get("keywords",[])]
                with c4: st.markdown(f'<div class="mbox"><div class="mval-orn">{len(set(all_kw[:200]))}</div><div class="mlbl">Keywords</div></div>',unsafe_allow_html=True)

                # Year analysis of documents
                doc_years=[an["year"] for an in all_an.values() if an.get("year")]
                if doc_years:
                    yr_cnt=Counter(doc_years)
                    fig_dy=go.Figure(go.Bar(x=[str(y) for y in sorted(yr_cnt.keys())],y=[yr_cnt[y] for y in sorted(yr_cnt.keys())],
                        marker=dict(color=VIB[:len(yr_cnt)]),text=[yr_cnt[y] for y in sorted(yr_cnt.keys())],textposition="outside",textfont=dict(color="#3A4D6A",size=9)))
                    fig_dy.update_layout(**{**pc_dark("Anos dos Documentos"),'height':190,'margin':dict(l=10,r=10,t=36,b=8)})
                    st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_dy,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)

                # Topic distribution of all documents
                all_topics=defaultdict(int)
                for an in all_an.values():
                    for t,s in an.get("topics",{}).items(): all_topics[t]+=s
                if all_topics:
                    fig_tp=go.Figure(go.Pie(labels=list(all_topics.keys())[:10],values=list(all_topics.values())[:10],hole=0.5,
                        marker=dict(colors=VIB[:10],line=dict(color=["#03060E"]*15,width=2)),textfont=dict(color="white",size=8)))
                    fig_tp.update_layout(height=260,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                        title=dict(text="Distribuicao Tematica das Pastas",font=dict(color="#D8E4F5",family="Syne",size=11)),
                        legend=dict(font=dict(color="#3A4D6A",size=8)),margin=dict(l=0,r=0,t=36,b=0))
                    st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_tp,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)

                # Authors from documents
                doc_authors=[]
                for an in all_an.values(): doc_authors.extend(an.get("authors",[]))
                if doc_authors:
                    auth_cnt=Counter(doc_authors)
                    st.markdown('<div class="dtxt">Autores nos documentos</div>',unsafe_allow_html=True)
                    for auth,cnt in auth_cnt.most_common(6):
                        st.markdown(f'<div style="display:flex;align-items:center;gap:7px;padding:.28rem 0;border-bottom:1px solid rgba(255,255,255,.04)">'
                                    f'{avh(ini(auth),26,ugrad(auth+"@"))}'
                                    f'<div style="flex:1;font-size:.72rem;color:#D8E4F5">{auth}</div>'
                                    f'<span class="badge-acc" style="font-size:.55rem">{cnt} doc.</span></div>',unsafe_allow_html=True)

                # Top keywords
                kw_cnt=Counter(all_kw)
                if kw_cnt:
                    top_kw=kw_cnt.most_common(15)
                    fig_kw=go.Figure(go.Bar(x=[c for _,c in top_kw],y=[w for w,_ in top_kw],orientation='h',
                        marker=dict(color=[c for _,c in top_kw],colorscale=[[0,"#0e3a6e"],[1,"#0A84FF"]]),
                        text=[w for w,_ in top_kw],textposition="inside",textfont=dict(color="white",size=8)))
                    fig_kw.update_layout(**{**pc_dark("Top Keywords Globais"),'height':380,'margin':dict(l=10,r=10,t=36,b=8),'yaxis':dict(showticklabels=False)})
                    st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_kw,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)

                # Relevance histogram
                rel_vals=[an.get("relevance_score",0) for an in all_an.values()]
                if rel_vals:
                    fig_rel=go.Figure(go.Histogram(x=rel_vals,nbinsx=10,marker=dict(color="#0A84FF",line=dict(color="#03060E",width=1))))
                    fig_rel.update_layout(**{**pc_dark("Distribuicao de Relevancia"),'height':165,'margin':dict(l=10,r=10,t=36,b=8)})
                    st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_rel,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)

                # Document summaries
                st.markdown('<div class="dtxt">Resumo dos documentos analisados</div>',unsafe_allow_html=True)
                for fname,an in list(all_an.items())[:10]:
                    st.markdown(f'<div class="scard"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.82rem;color:#fff;margin-bottom:.2rem">{fname}</div>'
                                f'<div style="font-size:.7rem;color:#7A8FAD;margin-bottom:.28rem">{an.get("summary","")}</div>'
                                f'<div style="display:flex;gap:1rem;flex-wrap:wrap">'
                                f'<span style="font-size:.62rem;color:{"#30D158" if an.get("relevance_score",0)>=70 else "#FF9F0A"}">{an.get("relevance_score",0)}% relevancia</span>'
                                f'{"<span style=font-size:.62rem;color:#0A84FF>"+str(an.get("year",""))+"</span>" if an.get("year") else ""}'
                                f'{"<span style=font-size:.62rem;color:#BF5AF2>"+an.get("nationality","")+"</span>" if an.get("nationality") else ""}'
                                f'</div>'
                                f'<div style="margin-top:.3rem">{tags_html(an.get("keywords",[])[:8])}</div></div>',unsafe_allow_html=True)

    with t_mapa:
        st.markdown('<h2 style="margin-bottom:.4rem;margin-top:.4rem">Mapa 3D de Nacionalidades</h2>',unsafe_allow_html=True)
        st.markdown('<p style="font-size:.72rem;color:#3A4D6A;margin-bottom:.75rem">Distribuicao geografica dos autores no repositorio e nas pastas de pesquisa</p>',unsafe_allow_html=True)
        # Collect all nationalities
        nat_data=defaultdict(lambda:{"count":0,"names":[],"titles":[]})
        for r in st.session_state.research_items:
            nat=r.get("nationality","")
            if nat and nat in NATIONALITY_COORDS:
                nat_data[nat]["count"]+=1; nat_data[nat]["names"].append(r.get("author","?"))
                nat_data[nat]["titles"].append(r.get("title","")[:35])
        # From folder analyses
        for fd in st.session_state.folders.values():
            if not isinstance(fd,dict): continue
            for an in fd.get("analyses",{}).values():
                nat=an.get("nationality","")
                if nat and nat in NATIONALITY_COORDS:
                    nat_data[nat]["count"]+=1
                    for a in an.get("authors",[]): nat_data[nat]["names"].append(a)
        # Also user profiles
        for ue,ud in st.session_state.users.items():
            nat=ud.get("nationality","")
            if nat and nat in NATIONALITY_COORDS: nat_data[nat]["count"]+=1
        if nat_data:
            lats=[]; lons=[]; sizes=[]; labels=[]; hover_texts=[]; colors_n=[]
            for nat,(lat,lon) in NATIONALITY_COORDS.items():
                cnt=nat_data[nat]["count"]
                if cnt>0:
                    lats.append(lat); lons.append(lon)
                    sizes.append(max(8,min(35,cnt*10)))
                    labels.append(nat); colors_n.append(cnt)
                    names_str=", ".join(list(dict.fromkeys(nat_data[nat]["names"]))[:3])
                    hover_texts.append(f"<b>{nat}</b><br>{cnt} pesquisa(s)<br>{names_str}")
            fig_map=go.Figure()
            fig_map.add_trace(go.Scattergeo(
                lat=lats,lon=lons,
                text=labels,
                hovertext=hover_texts,
                hoverinfo="text",
                mode="markers+text",
                marker=dict(size=sizes,color=colors_n,
                            colorscale=[[0,"#0e3a6e"],[0.5,"#0A84FF"],[1,"#30D158"]],
                            opacity=0.85,line=dict(color="rgba(255,255,255,.2)",width=1.5),
                            colorbar=dict(title="Pesquisas",titlefont=dict(color="#3A4D6A",size=9),tickfont=dict(color="#3A4D6A",size=8),bgcolor="rgba(0,0,0,0)",bordercolor="rgba(255,255,255,.06)")),
                textfont=dict(size=8,color="rgba(255,255,255,.5)"),
                textposition="top center"))
            fig_map.update_geos(
                projection_type="orthographic",
                showland=True,landcolor="rgba(14,58,110,.4)",
                showocean=True,oceancolor="rgba(3,6,14,.8)",
                showcoastlines=True,coastlinecolor="rgba(10,132,255,.2)",coastlinewidth=0.5,
                showframe=False,bgcolor="rgba(3,6,14,0)",
                showlakes=True,lakecolor="rgba(10,132,255,.1)",
                showcountries=True,countrycolor="rgba(255,255,255,.06)",countrywidth=0.3)
            fig_map.update_layout(height=500,paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0,r=0,t=0,b=0),geo=dict(bgcolor="rgba(0,0,0,0)"))
            st.markdown('<div class="glass-card" style="padding:.5rem">',unsafe_allow_html=True)
            st.plotly_chart(fig_map,use_container_width=True)
            st.markdown('</div>',unsafe_allow_html=True)
            # Legend
            st.markdown('<div class="dtxt">Distribuicao por pais</div>',unsafe_allow_html=True)
            cl1,cl2=st.columns(2)
            nat_sorted=sorted(nat_data.items(),key=lambda x:-x[1]["count"])
            for i,(nat,data) in enumerate(nat_sorted):
                with (cl1 if i%2==0 else cl2):
                    st.markdown(f'<div style="display:flex;align-items:center;gap:7px;padding:.28rem 0;border-bottom:1px solid rgba(255,255,255,.04)">'
                                f'<div style="font-size:.72rem;font-weight:600;color:#D8E4F5;flex:1">{nat}</div>'
                                f'<div style="font-weight:800;font-size:.82rem;color:#0A84FF">{data["count"]}</div>'
                                f'<div style="font-size:.55rem;color:#3A4D6A"> pesq.</div></div>',unsafe_allow_html=True)
        else:
            st.info("Nenhuma nacionalidade identificada ainda. Publique pesquisas ou analise documentos com autores de diferentes paises.")

    with t_impacto:
        my_research=[r for r in st.session_state.research_items if r.get("author_email")==email]
        c1,c2,c3=st.columns(3)
        with c1: st.markdown(f'<div class="mbox"><div class="mval-acc">{len(my_research)}</div><div class="mlbl">Minhas pesquisas</div></div>',unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="mbox"><div class="mval-teal">{sum(r.get("citations",0) for r in my_research)}</div><div class="mlbl">Citacoes</div></div>',unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="mbox"><div class="mval-pur">{sum(r.get("likes",0) for r in my_research)}</div><div class="mlbl">Likes</div></div>',unsafe_allow_html=True)
        # Interests radar
        prefs=st.session_state.user_prefs.get(email,{})
        if prefs:
            top=sorted(prefs.items(),key=lambda x:-x[1])[:10]; mx=max(s for _,s in top) if top else 1
            cats=[t for t,_ in top[:8]]; vals=[round(s/mx*100) for _,s in top[:8]]
            if len(cats)>=3:
                fig_r=go.Figure(go.Scatterpolar(r=vals+[vals[0]],theta=cats+[cats[0]],fill='toself',
                    line=dict(color="#0A84FF",width=2),fillcolor="rgba(10,132,255,.08)"))
                fig_r.update_layout(height=260,polar=dict(bgcolor="rgba(0,0,0,0)",
                    radialaxis=dict(visible=True,gridcolor="rgba(255,255,255,.04)",color="#3A4D6A",tickfont=dict(size=7)),
                    angularaxis=dict(gridcolor="rgba(255,255,255,.04)",color="#3A4D6A",tickfont=dict(size=9))),
                    paper_bgcolor="rgba(0,0,0,0)",title=dict(text="Perfil de Interesses",font=dict(color="#D8E4F5",family="Syne",size=11)),
                    margin=dict(l=40,r=40,t=40,b=20))
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_r,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════
#  CONNECTIONS — research similarity graph
# ══════════════════════════════════════════════════


def page_connections():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.7rem;margin-bottom:.25rem">Conexões entre Pesquisas</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:#3A4D6A;font-size:.74rem;margin-bottom:.8rem">Mapeamento semântico entre pesquisas do repositório e documentos das suas pastas.</p>', unsafe_allow_html=True)

    items = list(st.session_state.research_items)
    threshold = st.slider("Limiar mínimo de conexão", min_value=0.12, max_value=0.70, value=0.22, step=0.02)
    edges = build_connection_edges(items, threshold=threshold)
    conn_map = connection_count_map(items, edges)

    grouped = defaultdict(list)
    for item in items:
        grouped[item.get("area", "Sem área")].append(item)

    pos = {}
    areas = list(grouped.keys())
    total_areas = max(1, len(areas))
    for ai, area in enumerate(areas):
        angle = 2 * math.pi * ai / total_areas
        center = {"x": 0.5 + 0.32 * math.cos(angle), "y": 0.5 + 0.32 * math.sin(angle), "z": 0.48 + 0.10 * math.sin(angle * 1.5)}
        group = grouped[area]
        for gi, item in enumerate(group):
            inner_angle = 2 * math.pi * gi / max(1, len(group))
            pos[item["id"]] = {
                "x": center["x"] + 0.12 * math.cos(inner_angle),
                "y": center["y"] + 0.12 * math.sin(inner_angle),
                "z": center["z"] + 0.08 * ((gi % 4) - 1.5) / 3,
            }

    folder_nodes = []
    for fn, fd in st.session_state.folders.items():
        if not isinstance(fd, dict):
            continue
        for fname, an in fd.get("analyses", {}).items():
            node_id = f"folder::{fn}::{fname}"
            idx = len(folder_nodes)
            ang = 2 * math.pi * idx / max(1, len(folder_nodes) + 1)
            pos[node_id] = {"x": 0.5 + 0.48 * math.cos(ang), "y": 0.5 + 0.48 * math.sin(ang), "z": 0.2}
            folder_nodes.append({"id": node_id, "title": fname, "folder": fn, "kws": an.get("keywords", [])[:6]})

    area_colors_map = {area: VIB[i % len(VIB)] for i, area in enumerate(areas)}

    fig = go.Figure()
    for edge in edges[:60]:
        p1 = pos[edge["source"]["id"]]
        p2 = pos[edge["target"]["id"]]
        alpha = min(0.78, 0.15 + edge["score"] * 0.9)
        fig.add_trace(go.Scatter3d(
            x=[p1["x"], p2["x"], None],
            y=[p1["y"], p2["y"], None],
            z=[p1["z"], p2["z"], None],
            mode="lines",
            line=dict(color=f"rgba(10,132,255,{alpha:.2f})", width=max(2, int(edge["score"] * 10))),
            hoverinfo="none",
            showlegend=False,
        ))

    fig.add_trace(go.Scatter3d(
        x=[pos[item["id"]]["x"] for item in items],
        y=[pos[item["id"]]["y"] for item in items],
        z=[pos[item["id"]]["z"] for item in items],
        mode="markers+text",
        marker=dict(
            size=[max(10, min(24, 10 + item.get("citations", 0) // 4 + conn_map.get(item["id"], 0))) for item in items],
            color=[area_colors_map.get(item.get("area", "Sem área"), "#0A84FF") for item in items],
            opacity=.92,
            symbol="circle",
            line=dict(color="rgba(255,255,255,.18)", width=1),
        ),
        text=[item["title"][:18] + "..." for item in items],
        textposition="top center",
        textfont=dict(color="#3A4D6A", size=8, family="Inter"),
        hovertemplate=[
            f"<b>{item['title'][:60]}</b><br>{item.get('area', '')}<br>{item.get('citations', 0)} citações<br>{conn_map.get(item['id'], 0)} conexões<extra></extra>"
            for item in items
        ],
        showlegend=False,
    ))

    if folder_nodes:
        fig.add_trace(go.Scatter3d(
            x=[pos[node["id"]]["x"] for node in folder_nodes],
            y=[pos[node["id"]]["y"] for node in folder_nodes],
            z=[pos[node["id"]]["z"] for node in folder_nodes],
            mode="markers",
            marker=dict(size=8, color="#BF5AF2", opacity=.82, symbol="diamond", line=dict(color="rgba(255,255,255,.18)", width=1)),
            hovertemplate=[f"<b>{node['title']}</b><br>Pasta: {node['folder']}<br>{', '.join(node['kws'][:4])}<extra></extra>" for node in folder_nodes],
            showlegend=False,
        ))

    fig.update_layout(
        height=480,
        scene=dict(
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, showbackground=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, showbackground=False),
            zaxis=dict(showgrid=False, zeroline=False, showticklabels=False, showbackground=False),
            bgcolor="rgba(0,0,0,0)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('<p style="font-size:.63rem;color:#3A4D6A;text-align:center;margin-bottom:.7rem">Esferas = pesquisas do repositório · Diamantes = documentos das pastas · Linhas = compatibilidade semântica</p>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="mbox"><div class="mval-acc">{len(items)}</div><div class="mlbl">Pesquisas</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="mbox"><div class="mval-teal">{len(edges)}</div><div class="mlbl">Conexões ativas</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="mbox"><div class="mval-pur">{len(areas)}</div><div class="mlbl">Áreas conectadas</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="mbox"><div class="mval-orn">{len(folder_nodes)}</div><div class="mlbl">Docs. de pastas</div></div>', unsafe_allow_html=True)

    st.markdown('<hr>', unsafe_allow_html=True)
    t_map, t_focus, t_folder = st.tabs(["  Top conexões  ", "  Pesquisa foco  ", "  Pastas x repositório  "])

    with t_map:
        if not edges:
            st.info("Ainda não há conexões acima do limiar escolhido.")
        else:
            st.markdown('<div style="font-size:.57rem;color:#0A84FF;text-transform:uppercase;font-weight:700;letter-spacing:.10em;margin-bottom:.5rem">Conexões mais fortes do repositório</div>', unsafe_allow_html=True)
            for edge in edges[:18]:
                score_pct = round(edge["score"] * 100)
                sc = "#30D158" if score_pct >= 45 else ("#0A84FF" if score_pct >= 30 else "#FF9F0A")
                st.markdown(
                    f'<div class="conn-card">'
                    f'<div style="display:flex;justify-content:space-between;gap:8px;margin-bottom:.35rem">'
                    f'<div style="font-size:.78rem;font-weight:700;color:#fff;line-height:1.45">{edge["source"]["title"][:64]}</div>'
                    f'<div style="font-size:.61rem;color:{sc};font-weight:800;border:1px solid {sc}30;border-radius:8px;padding:3px 8px;white-space:nowrap">{score_pct}%</div>'
                    f'</div>'
                    f'<div style="font-size:.62rem;color:#3A4D6A;margin-bottom:.2rem">{edge["source"].get("area", "")} → {edge["target"].get("area", "")}</div>'
                    f'<div style="font-size:.76rem;font-weight:700;color:#D8E4F5;margin-bottom:.25rem">{edge["target"]["title"][:64]}</div>'
                    f'<div style="font-size:.68rem;color:#7A8FAD;margin-bottom:.3rem">{" • ".join(edge["reasons"][:4])}</div>'
                    f'{"<div>" + tags_html(edge["shared_terms"][:6], "tag-teal") + "</div>" if edge["shared_terms"] else ""}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    with t_focus:
        target = st.session_state.get("view_research")
        title_lookup = {r["title"][:70]: r for r in items}
        labels = ["— Selecionar —"] + list(title_lookup.keys())
        default_ix = 0
        if target:
            trunc = target.get("title", "")[:70]
            if trunc in labels:
                default_ix = labels.index(trunc)
        selected = st.selectbox("Pesquisa foco", labels, index=default_ix, key="conn_focus_sel")
        if selected != "— Selecionar —":
            target = title_lookup[selected]
            st.session_state.view_research = target

        if not target:
            st.info("Selecione uma pesquisa para abrir o mapa analítico individual.")
        else:
            target_connections = []
            for edge in edges:
                if edge["source"]["id"] == target["id"]:
                    target_connections.append((edge["score"], edge["target"], edge))
                elif edge["target"]["id"] == target["id"]:
                    target_connections.append((edge["score"], edge["source"], edge))
            target_connections.sort(key=lambda x: -x[0])

            st.markdown(
                f'<div class="abox">'
                f'<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.95rem;color:#fff;margin-bottom:.2rem">{target["title"]}</div>'
                f'<div style="font-size:.7rem;color:#0A84FF;margin-bottom:.25rem">{target.get("area", "")} · {target.get("methodology", "")} · {target.get("year", "")}</div>'
                f'<div style="font-size:.74rem;color:#7A8FAD;line-height:1.65;margin-bottom:.35rem">{target.get("abstract", "")[:320]}{"..." if len(target.get("abstract", "")) > 320 else ""}</div>'
                f'<div>{tags_html(target.get("tags", [])[:6])}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f'<div class="mbox"><div class="mval-teal">{len(target_connections)}</div><div class="mlbl">Conexões diretas</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="mbox"><div class="mval-acc">{target.get("citations", 0)}</div><div class="mlbl">Citações</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="mbox"><div class="mval-pur">{conn_map.get(target["id"], 0)}</div><div class="mlbl">Centralidade</div></div>', unsafe_allow_html=True)

            if target_connections:
                st.markdown('<div class="dtxt">Pesquisas conectadas ao foco</div>', unsafe_allow_html=True)
                for score, other, edge in target_connections[:8]:
                    st.markdown(
                        f'<div class="sim-card">'
                        f'<div style="display:flex;justify-content:space-between;gap:8px;margin-bottom:.25rem">'
                        f'<div style="font-size:.8rem;font-weight:700;color:#fff">{other["title"][:72]}</div>'
                        f'<div style="font-size:.62rem;color:#30D158;font-weight:800;white-space:nowrap">{round(score*100)}%</div>'
                        f'</div>'
                        f'<div style="font-size:.62rem;color:#3A4D6A;margin-bottom:.2rem">{other.get("area", "")} · {other.get("methodology", "")} · {other.get("year", "")}</div>'
                        f'<div style="font-size:.69rem;color:#7A8FAD;margin-bottom:.28rem">{" • ".join(edge["reasons"][:4])}</div>'
                        f'{"<div>" + tags_html(edge["shared_terms"][:6], "tag-pur") + "</div>" if edge["shared_terms"] else ""}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                if st.button("Buscar artigos relacionados na internet", key=f"conn_search_{target['id']}"):
                    with st.spinner("Buscando artigos..."):
                        st.session_state.scholar_cache[f"conn_{target['id']}"] = search_ss(target["title"][:70] + " " + " ".join(target.get("tags", [])[:3]), 5)
                arts = st.session_state.scholar_cache.get(f"conn_{target['id']}")
                if arts:
                    st.markdown('<div class="dtxt">Artigos relacionados na internet</div>', unsafe_allow_html=True)
                    for i, a in enumerate(arts):
                        render_article(a, i, "conn_web")
            else:
                st.info("Nenhuma conexão direta encontrada para essa pesquisa com o limiar atual.")

    with t_folder:
        all_analyses = {f: an for fd in st.session_state.folders.values() if isinstance(fd, dict) for f, an in fd.get("analyses", {}).items()}
        if not all_analyses:
            st.info("Analise documentos nas pastas para comparar com o repositório.")
        else:
            matches = folder_similarity(all_analyses, n=10)
            if not matches:
                st.info("Nenhuma relação consistente foi encontrada entre os documentos das pastas e o repositório.")
            else:
                st.markdown('<div style="font-size:.62rem;color:#3A4D6A;margin-bottom:.6rem">Os documentos analisados nas pastas são comparados com as pesquisas do repositório por palavras-chave, tópicos e aderência temática.</div>', unsafe_allow_html=True)
                for match in matches:
                    item = match["research"]
                    st.markdown(
                        f'<div class="conn-card">'
                        f'<div style="display:flex;justify-content:space-between;gap:10px;margin-bottom:.28rem">'
                        f'<div style="font-size:.8rem;font-weight:700;color:#fff">{item["title"][:78]}</div>'
                        f'<div style="font-size:.62rem;color:#BF5AF2;font-weight:800;white-space:nowrap">{round(match["score"]*100)}%</div>'
                        f'</div>'
                        f'<div style="font-size:.62rem;color:#3A4D6A;margin-bottom:.22rem">Documento: {match["document"]}</div>'
                        f'<div style="font-size:.68rem;color:#7A8FAD;margin-bottom:.25rem">{match["summary"][:180]}{"..." if len(match["summary"]) > 180 else ""}</div>'
                        f'<div style="font-size:.64rem;color:#30D158;margin-bottom:.2rem">Termos em comum</div>'
                        f'{"<div>" + tags_html(match["shared_terms"][:7], "tag-teal") + "</div>" if match["shared_terms"] else ""}'
                        f'{"<div style=margin-top:.22rem>" + tags_html(match["topics"][:4], "tag-pur") + "</div>" if match["topics"] else ""}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════
#  CHAT
# ══════════════════════════════════════════════════
def page_chat():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.7rem;margin-bottom:.8rem">Mensagens</h1>',unsafe_allow_html=True)
    email=st.session_state.current_user
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    contacts=[e for e in users if e!=email]
    cc,cm=st.columns([.85,2.7])
    with cc:
        st.markdown('<div style="font-size:.55rem;font-weight:700;color:#3A4D6A;letter-spacing:.12em;text-transform:uppercase;margin-bottom:.65rem">Conversas</div>',unsafe_allow_html=True)
        for ue in contacts:
            ud=users.get(ue,{}); un=ud.get("name","?"); ug=ugrad(ue)
            msgs=st.session_state.chat_messages.get(ue,[]); last=msgs[-1]["text"][:22]+"..." if msgs and len(msgs[-1]["text"])>22 else(msgs[-1]["text"] if msgs else "Iniciar conversa")
            is_act=st.session_state.active_chat==ue
            st.markdown(f'<div style="background:{"rgba(10,132,255,.09)" if is_act else "rgba(255,255,255,.03)"};border:1px solid {"rgba(10,132,255,.25)" if is_act else "rgba(255,255,255,.06)"};border-radius:12px;padding:7px 9px;margin-bottom:3px">'
                        f'<div style="display:flex;align-items:center;gap:7px">{avh(ini(un),28,ug)}'
                        f'<div style="overflow:hidden;flex:1"><div style="font-size:.74rem;font-weight:600;color:#D8E4F5">{un}</div>'
                        f'<div style="font-size:.60rem;color:#3A4D6A;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{last}</div></div></div></div>',unsafe_allow_html=True)
            if st.button("Abrir",key=f"oc_{ue}",use_container_width=True): st.session_state.active_chat=ue; st.rerun()
    with cm:
        ac=st.session_state.active_chat
        if ac and ac in users:
            cd=users.get(ac,{}); cn=cd.get("name","?"); cg=ugrad(ac)
            msgs=st.session_state.chat_messages.get(ac,[])
            st.markdown(f'<div style="display:flex;align-items:center;gap:10px;padding:.55rem 0 .7rem;border-bottom:1px solid rgba(255,255,255,.05);margin-bottom:.65rem">'
                        f'{avh(ini(cn),34,cg)}<div><div style="font-weight:700;font-size:.86rem;color:#fff">{cn}</div><div style="font-size:.62rem;color:#30D158">Criptografado</div></div></div>',unsafe_allow_html=True)
            for msg in msgs:
                is_me=msg["from"]=="me" or msg["from"]==email
                st.markdown(f'<div style="display:flex;{"justify-content:flex-end" if is_me else ""}"><div class="{"bme" if is_me else "bthem"}">{msg["text"]}<div style="font-size:.56rem;color:rgba(255,255,255,.3);margin-top:2px;text-align:{"right" if is_me else "left"}">{msg["time"]}</div></div></div>',unsafe_allow_html=True)
            with st.form(f"mf_{ac}"):
                mc=st.text_input("",placeholder="Mensagem...",key=f"mi_{ac}",label_visibility="collapsed")
                if st.form_submit_button("Enviar",use_container_width=True):
                    if mc:
                        now=datetime.now().strftime("%H:%M")
                        st.session_state.chat_messages.setdefault(ac,[]).append({"from":email,"text":mc,"time":now})
                        save_db(); st.rerun()
        else:
            st.markdown('<div class="glass-card" style="text-align:center;padding:5rem;color:#3A4D6A">Selecione uma conversa</div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════
#  SETTINGS
# ══════════════════════════════════════════════════


def page_settings():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.7rem;margin-bottom:.8rem">Configuracoes</h1>',unsafe_allow_html=True)
    email=st.session_state.current_user; u=guser(); g=ugrad(email)
    st.markdown(f'<div class="prof-hero"><div class="av" style="background:{g}">{ini(u.get("name","?"))}</div>'
                f'<div style="flex:1"><div style="font-family:Syne,sans-serif;font-weight:800;font-size:1.25rem;color:#fff;margin-bottom:.15rem">{u.get("name","?")}</div>'
                f'<div style="color:#0A84FF;font-size:.76rem;font-weight:600;margin-bottom:.25rem">{u.get("area","")}</div>'
                f'<div style="color:#7A8FAD;font-size:.73rem">{email}</div></div></div>',unsafe_allow_html=True)
    t1,t2,t3=st.tabs(["  Perfil  ","  Seguranca  ","  Artigos Salvos  "])
    with t1:
        with st.form("prf"):
            n_name=st.text_input("Nome",value=u.get("name",""))
            n_area=st.text_input("Area",value=u.get("area",""))
            n_bio=st.text_area("Bio",value=u.get("bio",""),height=70)
            nat_options=["Brasil"]+sorted([k for k in NATIONALITY_COORDS if k!="Brasil"])
            current_nat=str(u.get("nationality","Brasil") or "Brasil").strip()
            if current_nat not in nat_options:
                current_nat="Brasil"
            n_nat=st.selectbox("Nacionalidade",nat_options,index=nat_options.index(current_nat))
            if st.form_submit_button("Salvar perfil",use_container_width=True):
                st.session_state.users[email].update({"name":n_name,"area":n_area,"bio":n_bio,"nationality":n_nat})
                save_db(); st.success("Perfil salvo!")
        if st.button("Sair da conta",key="logout",use_container_width=False):
            st.session_state.logged_in=False; st.session_state.current_user=None; st.session_state.page="login"; st.rerun()
    with t2:
        with st.form("cpw"):
            op=st.text_input("Senha atual",type="password"); np_=st.text_input("Nova senha",type="password"); nc=st.text_input("Confirmar",type="password")
            if st.form_submit_button("Alterar senha",use_container_width=True):
                if hp(op)!=u.get("password",""): st.error("Senha incorreta.")
                elif np_!=nc: st.error("Nao coincidem.")
                elif len(np_)<6: st.error("Minimo 6 caracteres.")
                else: st.session_state.users[email]["password"]=hp(np_); save_db(); st.success("Senha alterada!")
    with t3:
        saved=st.session_state.saved_articles
        if saved:
            for i,a in enumerate(saved):
                uid=re.sub(r'[^a-zA-Z0-9]','',f"svt_{i}_{str(a.get('doi',''))[:6]}")[:20]
                st.markdown(f'<div class="scard"><div style="font-weight:700;font-size:.82rem;color:#fff;margin-bottom:.2rem">{a.get("title","?")}</div>'
                            f'<div style="font-size:.63rem;color:#3A4D6A">{a.get("authors","—")} · {a.get("year","?")} · {a.get("source","")}</div></div>',unsafe_allow_html=True)
                c1,c2=st.columns([1,3])
                with c1:
                    if st.button("Remover",key=f"rms_{uid}"):
                        st.session_state.saved_articles.pop(i); save_db(); st.rerun()
                with c2:
                    if a.get("url"): st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:#0A84FF;font-size:.74rem;text-decoration:none;line-height:2.3;display:block">Abrir</a>',unsafe_allow_html=True)
        else: st.markdown('<div class="glass-card" style="padding:2.5rem;text-align:center;color:#3A4D6A">Nenhum artigo salvo.</div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════════════════
def main():
    inject_css()
    if not st.session_state.logged_in:
        page_login(); return
    render_nav()
    if st.session_state.profile_view:
        page_profile(st.session_state.profile_view); return
    {
        "repository":page_repository,"search":page_search,
        "folders":page_folders,"analysis":page_analysis,
        "connections":page_connections,"chat":page_chat,"settings":page_settings,
    }.get(st.session_state.page,page_repository)()

# main() desativado; versões finais estão abaixo
# ==== OVERRIDES 2026-03-24 ====

def inject_extra_css():
    st.markdown("""
    <style>
    section[data-testid="stSidebar"]{display:none!important;}
    div[data-testid="stSidebarCollapsedControl"]{display:none!important;}
    .block-container{padding-top:1rem!important;max-width:1380px!important;}
    .topbar-wrap{position:sticky;top:0;z-index:10;padding:.2rem 0 .9rem;background:linear-gradient(180deg,rgba(3,6,14,.96),rgba(3,6,14,.82),rgba(3,6,14,0));backdrop-filter:blur(16px)}
    .topbrand{display:flex;align-items:center;gap:12px;margin-bottom:.8rem}.topbrand-icon{width:44px;height:44px;border-radius:14px;background:linear-gradient(135deg,#0A84FF,#30D158);display:flex;align-items:center;justify-content:center;font-family:Syne,sans-serif;font-weight:900;color:#fff}.topbrand-title{font-family:Syne,sans-serif;font-size:2rem;font-weight:900;letter-spacing:-.07em;color:#fff}.topbrand-sub{font-size:.71rem;color:#7A8FAD}.glass-nav{padding:.65rem;border-radius:22px;border:1px solid rgba(255,255,255,.08);background:linear-gradient(135deg,rgba(255,255,255,.05),rgba(255,255,255,.02));backdrop-filter:blur(18px);box-shadow:0 18px 40px rgba(0,0,0,.14)}
    .glass-nav .stButton>button{height:54px!important;border-radius:18px!important;background:linear-gradient(135deg,rgba(255,255,255,.09),rgba(255,255,255,.03))!important;border:1px solid rgba(255,255,255,.08)!important;color:#D8E4F5!important;font-weight:700!important}
    .hero-research,.glass-section{padding:1rem 1.05rem;border-radius:24px;border:1px solid rgba(255,255,255,.08);background:linear-gradient(135deg,rgba(255,255,255,.05),rgba(255,255,255,.02));backdrop-filter:blur(20px);box-shadow:0 16px 44px rgba(0,0,0,.14)}
    .hero-mini{font-size:.62rem;color:#7A8FAD;text-transform:uppercase;letter-spacing:.12em;font-weight:700;margin-bottom:.25rem}.hero-title{font-family:Syne,sans-serif;font-size:1.55rem;font-weight:900;letter-spacing:-.05em;color:#fff;margin-bottom:.35rem}.hero-text,.mini-note{font-size:.75rem;color:#91A6C6;line-height:1.7}
    .research-clean{border:1px solid rgba(255,255,255,.07);border-radius:22px;background:linear-gradient(135deg,rgba(255,255,255,.05),rgba(255,255,255,.018));box-shadow:0 16px 40px rgba(0,0,0,.12);margin-bottom:.85rem;overflow:hidden}.research-top{padding:1rem;border-bottom:1px solid rgba(255,255,255,.05)}.research-chip{font-size:.58rem;color:#9AC7FF;border:1px solid rgba(10,132,255,.22);padding:4px 8px;border-radius:999px;background:rgba(10,132,255,.08);display:inline-block;margin:.12rem .2rem .12rem 0}.cluster-row{padding:.6rem .75rem;border-radius:15px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);margin-bottom:.4rem}
    </style>
    """, unsafe_allow_html=True)

def _safe_nat_options(default='Brasil'):
    opts=['Brasil']+sorted([k for k in NATIONALITY_COORDS if k!='Brasil'])
    return opts, (default if default in opts else 'Brasil')

def _repo_external_articles(query, limit=5):
    q=(query or '').strip()
    if not q: return []
    ck=f"extrepo::{q.lower()[:80]}"
    if ck not in st.session_state.scholar_cache:
        try: st.session_state.scholar_cache[ck]=search_ss(q, limit)
        except: st.session_state.scholar_cache[ck]=[]
    return st.session_state.scholar_cache.get(ck, [])

def page_login():
    _,col,_=st.columns([.9,1.15,.9])
    with col:
        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown('<div class="hero-research" style="text-align:center"><div style="display:flex;align-items:center;justify-content:center;gap:12px;margin-bottom:.7rem"><div class="topbrand-icon">N</div><div><div class="topbrand-title" style="font-size:2.35rem">Nebula</div><div class="topbrand-sub" style="letter-spacing:.18em;text-transform:uppercase;font-size:.66rem">Pesquisa científica conectada</div></div></div><div class="hero-text">Entre ou crie uma conta para explorar pesquisas, cruzar documentos das suas pastas e localizar artigos acadêmicos correlatos ao seu tema.</div></div>',unsafe_allow_html=True)
        mode=st.session_state.get('auth_mode','login')
        c1,c2=st.columns(2)
        with c1:
            if st.button('Entrar',key='auth_enter_final',use_container_width=True):
                st.session_state.auth_mode='login'; st.rerun()
        with c2:
            if st.button('Cadastro',key='auth_signup_final',use_container_width=True):
                st.session_state.auth_mode='signup'; st.rerun()
        st.markdown('<div style="height:.45rem"></div>',unsafe_allow_html=True)
        if st.session_state.get('auth_mode','login')=='login':
            with st.form('lf_final'):
                em=st.text_input('E-mail',placeholder='seu@email.com')
                pw=st.text_input('Senha',type='password',placeholder='••••••••')
                if st.form_submit_button('Entrar na plataforma',use_container_width=True):
                    u=st.session_state.users.get(em)
                    if not u:
                        st.error('E-mail não encontrado.')
                    elif u['password']!=hp(pw):
                        st.error('Senha incorreta.')
                    else:
                        st.session_state.logged_in=True
                        st.session_state.current_user=em
                        update_profile([w.lower() for w in re.split(r'[\s,;/]+',u.get('area','')) if len(w)>3],2.0)
                        st.session_state.page='repository'
                        st.rerun()
        else:
            with st.form('sf_final'):
                nn=st.text_input('Nome completo')
                ne=st.text_input('E-mail')
                na=st.text_input('Linha de pesquisa',placeholder='Ex: documentação museológica digital, IA aplicada à preservação')
                c1,c2=st.columns(2)
                with c1:
                    np_=st.text_input('Senha',type='password')
                with c2:
                    np2=st.text_input('Confirmar senha',type='password')
                if st.form_submit_button('Criar conta',use_container_width=True):
                    if not all([nn,ne,na,np_,np2]):
                        st.error('Preencha nome, e-mail, linha de pesquisa e senha.')
                    elif np_!=np2:
                        st.error('Senhas não coincidem.')
                    elif len(np_)<6:
                        st.error('A senha precisa ter no mínimo 6 caracteres.')
                    elif ne in st.session_state.users:
                        st.error('Esse e-mail já está cadastrado.')
                    else:
                        st.session_state.users[ne]={'name':nn,'password':hp(np_),'area':na,'verified':False,'nationality':'Brasil'}
                        save_db()
                        st.success('Conta criada. Agora entre na plataforma.')
                        st.session_state.auth_mode='login'
                        st.rerun()


def render_nav():
    pages=[('repository','Área de pesquisa'),('analysis','Análises'),('connections','Conexões'),('folders','Pastas'),('search','Busca'),('settings','Conta')]
    cur=st.session_state.page
    st.markdown('<div class="topbar-wrap"><div class="topbrand"><div class="topbrand-icon">N</div><div><div class="topbrand-title">Nebula</div><div class="topbrand-sub">Ambiente analítico de pesquisa</div></div></div><div class="glass-nav">',unsafe_allow_html=True)
    cols=st.columns(len(pages))
    for col,(key,label) in zip(cols,pages):
        with col:
            txt=('● '+label) if cur==key and not st.session_state.profile_view else label
            if st.button(txt,key=f'topnav_final_{key}',use_container_width=True):
                st.session_state.profile_view=None
                st.session_state.page=key
                st.rerun()
    st.markdown('</div></div>',unsafe_allow_html=True)


def render_research_card(item, show_author=True, ctx='repo', compact=False, connection_count=None):
    iid=item['id']
    aname=item.get('author','?')
    nat=item.get('nationality','Brasil')
    dt=item.get('date','')
    yr=item.get('year','')
    cit=item.get('citations',0)
    method=item.get('methodology','—')
    ab=(item.get('abstract','') or '').strip()
    conn_count=connection_count if connection_count is not None else len(find_similar(item,0.22,20))
    detail_key=f'detail_{ctx}_{iid}'
    meta=f'{aname} · {item.get("area","")}'
    if nat:
        meta+=f' · {nat}'
    if dt:
        meta+=f' · {dt}'
    st.markdown('<div class="research-clean"><div class="research-top"><div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start"><div style="flex:1"><div style="font-size:.66rem;color:#7A8FAD;font-weight:600">'+meta+'</div><div style="font-family:Syne,sans-serif;font-size:1rem;font-weight:800;color:#fff;line-height:1.35;margin-top:.2rem">'+item.get('title','Sem título')+'</div><div style="font-size:.76rem;color:#91A6C6;line-height:1.68;margin-top:.45rem">'+ab[:380]+('...' if len(ab)>380 else '')+'</div></div>'+badge(item.get('status','Em andamento'))+'</div><div style="margin-top:.45rem"><span class="research-chip">Ano '+str(yr)+'</span><span class="research-chip">'+str(method)+'</span><span class="research-chip">'+str(cit)+' citações</span><span class="research-chip">'+str(conn_count)+' conexões</span></div>'+(('<div style="margin-top:.45rem">'+tags_html(item.get('tags',[])[:6])+'</div>') if item.get('tags') else '')+'</div>',unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        if st.button('Mapear conexões',key=f'cn_final_{ctx}_{iid}',use_container_width=True):
            st.session_state.view_research=item
            st.session_state.page='connections'
            st.rerun()
    with c2:
        if st.button('Ler análise',key=f'dt_final_{ctx}_{iid}',use_container_width=True):
            st.session_state[detail_key]=not st.session_state.get(detail_key,False)
            st.rerun()
    if st.session_state.get(detail_key,False):
        related=find_similar(item,0.22,4)
        st.markdown('<div class="glass-section" style="margin:.15rem .85rem .9rem"><div class="hero-mini">Leitura analítica</div><div class="mini-note" style="margin-bottom:.55rem">Esta pesquisa se posiciona em <strong>'+item.get('area','—')+'</strong>, usa <strong>'+str(method)+'</strong> e possui como termos dominantes: '+(', '.join(research_terms(item,8)) if research_terms(item,8) else 'sem termos dominantes')+'.</div>',unsafe_allow_html=True)
        if related:
            for sim,other in related:
                det=connection_details(item,other)
                st.markdown('<div class="cluster-row"><div style="display:flex;justify-content:space-between;gap:8px"><div style="font-size:.8rem;font-weight:700;color:#fff">'+other.get('title','')[:82]+'</div><div style="font-size:.63rem;color:#30D158;font-weight:800">'+str(round(sim*100))+'%</div></div><div class="mini-note" style="margin:.18rem 0 .25rem">'+other.get('area','')+' · '+other.get('methodology','')+'</div><div class="mini-note">'+' • '.join(det.get('reasons',[])[:3])+'</div>'+(('<div style="margin-top:.35rem">'+tags_html(det.get('shared_terms',[])[:8],'tag-teal')+'</div>') if det.get('shared_terms') else '')+'</div>',unsafe_allow_html=True)
        else:
            st.markdown('<div class="mini-note">Ainda não há conexões suficientemente fortes para esta pesquisa.</div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)


def page_repository():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    u=guser()
    email=st.session_state.current_user
    all_items=list(st.session_state.research_items)
    all_edges=build_connection_edges(all_items,threshold=0.22)
    conn_map=connection_count_map(all_items,all_edges)
    interests=get_interests(email,10)
    recs=get_recommendations(email,8)
    ext_query=' '.join(interests[:4]) if interests else u.get('area','pesquisa acadêmica')
    ext_articles=_repo_external_articles(ext_query,8)
    st.markdown('<div class="hero-research"><div class="hero-mini">Área de pesquisa</div><div class="hero-title">Mapeamento acadêmico da sua linha de pesquisa</div><div class="hero-text">Explore estudos do repositório, veja correlações reais entre pesquisas e acompanhe referências externas alinhadas ao seu eixo principal: <strong>'+u.get('area','—')+'</strong>.</div></div>',unsafe_allow_html=True)
    left,right=st.columns([2.2,1],gap='medium')
    with left:
        q_col,s_col=st.columns([3.3,1.15])
        with q_col:
            repo_query=st.text_input('',placeholder='Pesquisar título, autor, resumo, tag, método ou área...',key='repo_query_final',label_visibility='collapsed')
        with s_col:
            sort_mode=st.selectbox('Ordenar por',['Mais recentes','Mais conectadas','Mais citadas','Mais aderentes ao meu eixo'],key='repo_sort_final')
        ff=st.radio('',['Todas','Minhas','Por área','Correlatas','Publicadas'],horizontal=True,key='repo_filter_final',label_visibility='collapsed')
        items=list(all_items)
        if ff=='Minhas':
            items=[r for r in items if r.get('author_email')==email]
        elif ff=='Por área':
            area=_norm_text(u.get('area',''))
            items=[r for r in items if area and (area in _norm_text(r.get('area','')) or area in _norm_text(r.get('abstract','')))]
        elif ff=='Correlatas':
            items=recs if recs else items
        elif ff=='Publicadas':
            items=[r for r in items if _norm_text(r.get('status',''))=='publicado']
        if repo_query:
            q=_norm_text(repo_query)
            items=[r for r in items if q in _norm_text(r.get('title','')) or q in _norm_text(r.get('author','')) or q in _norm_text(r.get('abstract','')) or q in _norm_text(r.get('area','')) or q in _norm_text(r.get('methodology','')) or any(q in _norm_text(t) for t in r.get('tags',[]))]
        if sort_mode=='Mais conectadas':
            items=sorted(items,key=lambda x:(conn_map.get(x['id'],0),x.get('citations',0),x.get('date','')),reverse=True)
        elif sort_mode=='Mais citadas':
            items=sorted(items,key=lambda x:(x.get('citations',0),conn_map.get(x['id'],0),x.get('date','')),reverse=True)
        elif sort_mode=='Mais aderentes ao meu eixo':
            interest_set=set(get_interests(email,20))|{_norm_text(u.get('area',''))}
            items=sorted(items,key=lambda item:len(set(research_terms(item,12)) & interest_set)*12+conn_map.get(item['id'],0)*2+item.get('citations',0)*0.4,reverse=True)
        else:
            items=sorted(items,key=lambda x:(x.get('date',''),x.get('citations',0)),reverse=True)
        m1,m2,m3=st.columns(3)
        with m1:
            st.markdown(f'<div class="mbox"><div class="mval-acc">{len(items)}</div><div class="mlbl">Pesquisas visíveis</div></div>',unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="mbox"><div class="mval-teal">{len(all_edges)}</div><div class="mlbl">Conexões mapeadas</div></div>',unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="mbox"><div class="mval-pur">{len(set(r.get("area","Sem área") for r in all_items))}</div><div class="mlbl">Áreas de pesquisa</div></div>',unsafe_allow_html=True)
        st.markdown('<div style="height:.35rem"></div>',unsafe_allow_html=True)
        if not items:
            st.markdown('<div class="glass-card" style="padding:3rem;text-align:center;color:#7A8FAD">Nenhuma pesquisa encontrada nesse recorte.</div>',unsafe_allow_html=True)
        else:
            for r in items:
                render_research_card(r,ctx='repo_final',connection_count=conn_map.get(r['id'],0))
    with right:
        st.markdown('<div class="glass-section"><div class="hero-mini">Eixos do seu perfil</div><div style="font-size:.95rem;color:#fff;font-weight:800;line-height:1.4">'+u.get('area','Pesquisa')+'</div><div style="margin-top:.55rem">',unsafe_allow_html=True)
        if interests:
            for i,term in enumerate(interests[:8]):
                pct=max(24,100-i*9)
                st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:.45rem"><div style="flex:1;font-size:.8rem;color:#AFC3DE">{term}</div><div style="width:128px;height:7px;border-radius:999px;background:rgba(255,255,255,.06);overflow:hidden"><div style="width:{pct}%;height:100%;background:linear-gradient(90deg,#0A84FF,#30D158)"></div></div></div>',unsafe_allow_html=True)
        else:
            st.markdown('<div class="mini-note">Ainda sem termos recorrentes suficientes.</div>',unsafe_allow_html=True)
        st.markdown('</div></div>',unsafe_allow_html=True)
        st.markdown('<div style="height:.8rem"></div>',unsafe_allow_html=True)
        st.markdown('<div class="glass-section"><div class="hero-mini">Referências acadêmicas sugeridas</div>',unsafe_allow_html=True)
        if ext_articles:
            for a in ext_articles[:5]:
                title=(a.get('title','Sem título') or 'Sem título')[:82]
                meta=f"{a.get('authors','—')} · {a.get('year','?')} · {a.get('citations',0)} cit."
                st.markdown(f'<div style="padding:.2rem 0 .75rem;border-bottom:1px solid rgba(255,255,255,.06);margin-bottom:.65rem"><div style="font-size:.84rem;color:#fff;font-weight:800;line-height:1.5">{title}</div><div class="mini-note" style="margin-top:.15rem">{meta}</div></div>',unsafe_allow_html=True)
                if a.get('url'):
                    st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:#0A84FF;font-size:.74rem;text-decoration:none">Abrir referência</a>',unsafe_allow_html=True)
        else:
            st.markdown('<div class="mini-note">Nenhuma referência externa encontrada agora para esse eixo.</div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)
        topic_counter=Counter(t.lower() for r in all_items for t in r.get('tags',[]))
        st.markdown('<div style="height:.8rem"></div>',unsafe_allow_html=True)
        st.markdown('<div class="glass-section"><div class="hero-mini">Temas recorrentes</div>',unsafe_allow_html=True)
        if topic_counter:
            for term,cnt in topic_counter.most_common(8):
                st.markdown(f'<div style="padding:.22rem 0 .72rem;border-bottom:1px solid rgba(255,255,255,.05)"><div style="font-size:.8rem;font-weight:700;color:#0A84FF">{term}</div><div class="mini-note">{cnt} ocorrência(s) no repositório</div></div>',unsafe_allow_html=True)
        else:
            st.markdown('<div class="mini-note">Sem recorrências suficientes por enquanto.</div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)


def page_analysis():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<div class="hero-research"><div class="hero-mini">Análise avançada</div><div class="hero-title">Leitura analítica do ecossistema de pesquisa</div><div class="hero-text">Cruza repositório, documentos das pastas, anos, autores, temas, palavras-chave, conexões e correlação externa para revelar padrões da sua base.</div></div>',unsafe_allow_html=True)
    items=list(st.session_state.research_items)
    folders=st.session_state.folders
    all_an={f:an for fd in folders.values() if isinstance(fd,dict) for f,an in fd.get('analyses',{}).items()}
    edges=build_connection_edges(items,threshold=0.22)
    conn_map=connection_count_map(items,edges)
    c1,c2,c3,c4=st.columns(4)
    with c1:
        st.markdown(f'<div class="mbox"><div class="mval-acc">{len(items)}</div><div class="mlbl">Pesquisas</div></div>',unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="mbox"><div class="mval-teal">{len(all_an)}</div><div class="mlbl">Documentos analisados</div></div>',unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="mbox"><div class="mval-pur">{len(edges)}</div><div class="mlbl">Conexões fortes</div></div>',unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="mbox"><div class="mval-orn">{sum(r.get("citations",0) for r in items)}</div><div class="mlbl">Citações totais</div></div>',unsafe_allow_html=True)
    tab1,tab2,tab3,tab4=st.tabs(['  Repositório  ','  Documentos  ','  Conexões  ','  Correlação externa  '])
    with tab1:
        if not items:
            st.info('Nenhuma pesquisa no repositório.')
        else:
            years=Counter(r.get('year',datetime.now().year) for r in items)
            areas=Counter(r.get('area','Sem área') for r in items)
            meth=Counter(r.get('methodology','outro') for r in items)
            tags=Counter(t.lower() for r in items for t in r.get('tags',[]))
            top_conn=sorted(items,key=lambda x:(conn_map.get(x['id'],0),x.get('citations',0)),reverse=True)[:8]
            y1,y2=st.columns(2)
            with y1:
                fig=go.Figure(go.Bar(x=[str(y) for y in sorted(years)],y=[years[y] for y in sorted(years)],text=[years[y] for y in sorted(years)],textposition='outside'))
                fig.update_layout(**{**pc_dark('Evolução por ano'),'height':240})
                st.plotly_chart(fig,use_container_width=True)
            with y2:
                fig=go.Figure(go.Pie(labels=list(areas.keys())[:8],values=list(areas.values())[:8],hole=.52))
                fig.update_layout(height=240,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',title=dict(text='Áreas predominantes',font=dict(color='#D8E4F5',family='Syne',size=12)))
                st.plotly_chart(fig,use_container_width=True)
            m1,m2=st.columns(2)
            with m1:
                fig=go.Figure(go.Bar(x=list(meth.values()),y=list(meth.keys()),orientation='h',text=list(meth.values()),textposition='outside'))
                fig.update_layout(**{**pc_dark('Metodologias'), 'height':320})
                st.plotly_chart(fig,use_container_width=True)
            with m2:
                top_tags=tags.most_common(12)
                if top_tags:
                    fig=go.Figure(go.Bar(x=[c for _,c in top_tags],y=[t for t,_ in top_tags],orientation='h',text=[c for _,c in top_tags],textposition='inside'))
                    fig.update_layout(**{**pc_dark('Palavras-chave dominantes'),'height':320,'yaxis':dict(showticklabels=False)})
                    st.plotly_chart(fig,use_container_width=True)
            st.markdown('<div class="glass-section"><div class="hero-mini">Pesquisas com maior densidade de conexão</div>',unsafe_allow_html=True)
            for r in top_conn:
                st.markdown(f'<div class="cluster-row"><div style="display:flex;justify-content:space-between;gap:8px"><div style="font-size:.8rem;font-weight:700;color:#fff">{r.get("title","")[:88]}</div><div style="font-size:.63rem;color:#30D158;font-weight:800">{conn_map.get(r["id"],0)} conexões</div></div><div class="mini-note">{r.get("area","")} · {r.get("methodology","")} · {r.get("year","")}</div></div>',unsafe_allow_html=True)
            st.markdown('</div>',unsafe_allow_html=True)
    with tab2:
        if not all_an:
            st.info('Analise documentos nas pastas para gerar este painel.')
        else:
            kw=Counter(k for an in all_an.values() for k in an.get('keywords',[]))
            years_doc=Counter(an.get('year') for an in all_an.values() if an.get('year'))
            authors=Counter(a for an in all_an.values() for a in an.get('authors',[]))
            relev=[an.get('relevance_score',0) for an in all_an.values()]
            c1,c2=st.columns(2)
            with c1:
                if years_doc:
                    fig=go.Figure(go.Bar(x=[str(y) for y in sorted(years_doc)],y=[years_doc[y] for y in sorted(years_doc)],text=[years_doc[y] for y in sorted(years_doc)],textposition='outside'))
                    fig.update_layout(**{**pc_dark('Documentos por ano'),'height':240})
                    st.plotly_chart(fig,use_container_width=True)
            with c2:
                if relev:
                    fig=go.Figure(go.Histogram(x=relev,nbinsx=10))
                    fig.update_layout(**{**pc_dark('Distribuição de relevância'),'height':240})
                    st.plotly_chart(fig,use_container_width=True)
            st.markdown('<div class="glass-section"><div class="hero-mini">Autores mais recorrentes</div>',unsafe_allow_html=True)
            for a,c in authors.most_common(10):
                st.markdown(f'<div class="cluster-row"><div style="font-size:.8rem;font-weight:700;color:#fff">{a}</div><div class="mini-note">{c} documento(s)</div></div>',unsafe_allow_html=True)
            st.markdown('</div>',unsafe_allow_html=True)
            if kw:
                fig=go.Figure(go.Bar(x=[c for _,c in kw.most_common(15)],y=[k for k,_ in kw.most_common(15)],orientation='h',text=[c for _,c in kw.most_common(15)],textposition='inside'))
                fig.update_layout(**{**pc_dark('Keywords dominantes das pastas'),'height':420,'yaxis':dict(showticklabels=False)})
                st.plotly_chart(fig,use_container_width=True)
    with tab3:
        if not edges:
            st.info('Ainda não há conexões fortes suficientes para análise comparativa.')
        else:
            ranked=sorted(edges,key=lambda e:e['score'],reverse=True)[:20]
            st.markdown('<div class="glass-section"><div class="hero-mini">Pares de pesquisa com maior correlação</div><div class="mini-note">A força da ligação considera área, método, tags e semelhança textual.</div></div>',unsafe_allow_html=True)
            for edge in ranked:
                det=connection_details(edge['source'],edge['target'])
                st.markdown(f'<div class="cluster-row"><div style="display:flex;justify-content:space-between;gap:8px"><div style="font-size:.84rem;font-weight:800;color:#fff">{edge["source"].get("title","")[:60]}</div><div style="font-size:.66rem;color:#30D158;font-weight:900">{round(edge["score"]*100)}%</div></div><div class="mini-note" style="margin:.25rem 0">↔ {edge["target"].get("title","")[:86]}</div><div class="mini-note">{" • ".join(det.get("reasons",[])[:4])}</div>'+(('<div style="margin-top:.35rem">'+tags_html(det.get('shared_terms',[])[:10],'tag-teal')+'</div>') if det.get('shared_terms') else '')+'</div>',unsafe_allow_html=True)
    with tab4:
        u=guser()
        q=' '.join(get_interests(st.session_state.current_user,6)) or u.get('area','pesquisa científica')
        arts=_repo_external_articles(q,10)
        st.markdown('<div class="glass-section"><div class="hero-mini">Literatura externa correlata</div><div class="mini-note">Busca automática por estudos alinhados ao seu eixo de pesquisa para ampliar comparação bibliográfica.</div></div>',unsafe_allow_html=True)
        if arts:
            for a in arts[:10]:
                title=a.get('title','Sem título')
                meta=f"{a.get('authors','—')} · {a.get('year','?')} · {a.get('source','')}"
                st.markdown(f'<div class="cluster-row"><div style="font-size:.82rem;font-weight:700;color:#fff">{title}</div><div class="mini-note">{meta}</div><div class="mini-note" style="margin-top:.25rem">{(a.get("abstract","") or "")[:260]}{"..." if len(a.get("abstract","") or "")>260 else ""}</div></div>',unsafe_allow_html=True)
                if a.get('url'):
                    st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:#0A84FF;font-size:.7rem;text-decoration:none">Abrir artigo</a>',unsafe_allow_html=True)
        else:
            st.info('Nenhum artigo externo localizado agora para esse eixo.')
    st.markdown('</div>',unsafe_allow_html=True)


def page_connections():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    items=list(st.session_state.research_items)
    threshold=st.slider('Força mínima da conexão',0.12,0.70,0.22,0.02)
    edges=build_connection_edges(items,threshold=threshold)
    st.markdown('<div class="hero-research"><div class="hero-mini">Conexões entre pesquisas</div><div class="hero-title">União real entre pesquisas semelhantes</div><div class="hero-text">O sistema conecta pesquisas por termos compartilhados, metodologia, área e proximidade semântica. Quanto maior a pontuação, mais forte a correlação.</div></div>',unsafe_allow_html=True)
    c1,c2,c3=st.columns(3)
    with c1:
        st.markdown(f'<div class="mbox"><div class="mval-acc">{len(items)}</div><div class="mlbl">Pesquisas avaliadas</div></div>',unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="mbox"><div class="mval-teal">{len(edges)}</div><div class="mlbl">Conexões fortes</div></div>',unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="mbox"><div class="mval-pur">{len(set(tuple(sorted((e["source"]["id"],e["target"]["id"]))) for e in edges)) if edges else 0}</div><div class="mlbl">Pares conectados</div></div>',unsafe_allow_html=True)
    focus=st.session_state.get('view_research')
    if focus:
        st.markdown('<div class="glass-section"><div class="hero-mini">Pesquisa focal</div><div style="font-size:1rem;color:#fff;font-weight:800">'+focus.get('title','')+'</div><div class="mini-note">'+focus.get('area','')+' · '+focus.get('methodology','')+'</div></div><div style="height:.65rem"></div>',unsafe_allow_html=True)
    if not edges:
        st.info('Nenhuma conexão forte encontrada com esse limiar.')
    else:
        for edge in edges[:30]:
            if focus and edge['source']['id']!=focus['id'] and edge['target']['id']!=focus['id']:
                continue
            det=connection_details(edge['source'],edge['target'])
            st.markdown(f'<div class="cluster-row"><div style="display:flex;justify-content:space-between;gap:8px"><div style="font-size:.85rem;font-weight:800;color:#fff">{edge["source"]["title"][:56]}</div><div style="font-size:.66rem;color:#30D158;font-weight:900">{round(edge["score"]*100)}%</div></div><div class="mini-note" style="margin:.25rem 0">↔ {edge["target"]["title"][:76]}</div><div class="mini-note">{" • ".join(det.get("reasons",[])[:4])}</div>'+(('<div style="margin-top:.35rem">'+tags_html(det.get('shared_terms',[])[:10],'tag-teal')+'</div>') if det.get('shared_terms') else '')+'</div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)


def page_settings():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    email=st.session_state.current_user
    u=guser()
    st.markdown('<div class="hero-research"><div class="hero-mini">Conta</div><div class="hero-title">Dados básicos do perfil</div><div class="hero-text">Ajuste apenas o necessário: nome, linha de pesquisa e senha.</div></div>',unsafe_allow_html=True)
    t1,t2=st.tabs(['  Perfil  ','  Segurança  '])
    with t1:
        with st.form('prf_final'):
            n_name=st.text_input('Nome',value=u.get('name',''))
            n_area=st.text_input('Linha de pesquisa',value=u.get('area',''))
            if st.form_submit_button('Salvar perfil',use_container_width=True):
                st.session_state.users[email].update({'name':n_name,'area':n_area})
                save_db()
                st.success('Perfil salvo!')
        if st.button('Sair da conta',key='logout_final'):
            st.session_state.logged_in=False
            st.session_state.current_user=None
            st.session_state.page='login'
            st.rerun()
    with t2:
        with st.form('cpw_final'):
            op=st.text_input('Senha atual',type='password')
            np_=st.text_input('Nova senha',type='password')
            nc=st.text_input('Confirmar',type='password')
            if st.form_submit_button('Alterar senha',use_container_width=True):
                if hp(op)!=u.get('password',''):
                    st.error('Senha incorreta.')
                elif np_!=nc:
                    st.error('As senhas não coincidem.')
                elif len(np_)<6:
                    st.error('Mínimo 6 caracteres.')
                else:
                    st.session_state.users[email]['password']=hp(np_)
                    save_db()
                    st.success('Senha alterada!')
    st.markdown('</div>',unsafe_allow_html=True)


def main():
    inject_css()
    inject_extra_css()
    if not st.session_state.logged_in:
        page_login()
        return
    render_nav()
    if st.session_state.profile_view:
        page_profile(st.session_state.profile_view)
        return
    {'repository':page_repository,'search':page_search,'folders':page_folders,'analysis':page_analysis,'connections':page_connections,'chat':page_chat,'settings':page_settings}.get(st.session_state.page,page_repository)()

main()
