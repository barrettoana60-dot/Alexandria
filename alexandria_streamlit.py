import os
import io
import re
import json
import math
import hashlib
import zipfile
import struct
import zlib
from datetime import datetime
from collections import Counter, defaultdict
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import requests
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image

try:
    import PyPDF2
except Exception:
    PyPDF2 = None

try:
    import pdfplumber
except Exception:
    pdfplumber = None

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="Nebula Research",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DB_FILE = "nebula_research_db.json"
MAX_TEXT_CHARS = 80000

STOPWORDS = {
    "de","a","o","que","e","do","da","em","um","para","é","com","uma","os","no","se","na","por",
    "mais","as","dos","como","mas","foi","ao","ele","das","tem","à","seu","sua","ou","ser","muito",
    "também","já","entre","sobre","após","antes","durante","cada","esse","essa","isso","estes","essas",
    "this","be","or","by","from","an","at","we","our","their","into","using","use","used",
    "the","of","and","to","in","is","it","that","for","on","as","with","are","between","after","before","during",
    "were","was","has","have","had","been","will","would","could","should","may","might","shall",
    "não","ser","ter","fazer","poder","dever","estar","ir","ver","dar","vir","querer","saber",
    "quando","onde","como","porque","quem","qual","quanto","todo","todos","toda","todas","mesmo","mesma",
    "seu","sua","seus","suas","meu","minha","nosso","nossa","ele","ela","eles","elas","eu","você","nos",
}

TOPIC_RULES = {
    "Inteligência Artificial": ["ia","ai","machine learning","deep learning","rede neural","llm","modelo","algoritmo","transformer","gpt","bert","nlp","visão computacional"],
    "Museologia": ["museu","museologia","acervo","coleção","documentação","patrimônio","preservação","museal","curadoria","exposição"],
    "Computação": ["python","software","sistema","banco de dados","api","código","computação","programação","arquitetura","cloud"],
    "Ciência de Dados": ["dados","estatística","análise","modelo preditivo","cluster","classificação","regressão","visualização","dashboard"],
    "Biomedicina": ["célula","gene","proteína","crispr","biologia","biomédica","terapia","amostra","genoma","ensaio clínico"],
    "Neurociência": ["neurônio","cérebro","memória","sono","sináptica","cognitivo","neuro","fMRI","dopamina"],
    "Astrofísica": ["galáxia","cosmologia","matéria escura","lensing","astro","telescópio","gravitacional","buraco negro","exoplaneta"],
    "Psicologia": ["comportamento","psicologia","viés","atenção","emoção","cognição","ansiedade","depressão","terapia cognitiva"],
    "Educação": ["aprendizagem","ensino","estudante","escola","didática","educação","currículo","pedagogia"],
    "Engenharia": ["engenharia","estrutura","material","resistência","circuito","eletrônica","mecânica","termodinâmica"],
    "Direito": ["direito","lei","jurídico","tribunal","contrato","norma","legislação","constitucional"],
    "Economia": ["economia","mercado","inflação","pib","investimento","financeiro","fiscal","monetária"],
}

NATIONALITY_COORDS = {
    "Brasil": {"lat": -14.2, "lon": -51.9},
    "Portugal": {"lat": 39.4, "lon": -8.2},
    "Estados Unidos": {"lat": 37.1, "lon": -95.7},
    "México": {"lat": 23.6, "lon": -102.6},
    "Argentina": {"lat": -38.4, "lon": -63.6},
    "Reino Unido": {"lat": 55.4, "lon": -3.4},
    "França": {"lat": 46.2, "lon": 2.2},
    "Alemanha": {"lat": 51.2, "lon": 10.4},
    "Itália": {"lat": 41.9, "lon": 12.6},
    "Espanha": {"lat": 40.5, "lon": -3.7},
    "Índia": {"lat": 20.6, "lon": 79.0},
    "China": {"lat": 35.9, "lon": 104.2},
    "Japão": {"lat": 36.2, "lon": 138.3},
    "Canadá": {"lat": 56.1, "lon": -106.3},
    "Austrália": {"lat": -25.3, "lon": 133.8},
    "Holanda": {"lat": 52.3, "lon": 4.9},
    "Suécia": {"lat": 60.1, "lon": 18.6},
    "Suíça": {"lat": 46.8, "lon": 8.2},
    "Coreia do Sul": {"lat": 35.9, "lon": 127.8},
    "Singapura": {"lat": 1.3, "lon": 103.8},
}

# ============================================================
# CSS — LIQUID GLASS INTERFACE
# ============================================================
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --bg: #050810;
    --glass: rgba(255,255,255,0.06);
    --glass-border: rgba(255,255,255,0.10);
    --glass-hover: rgba(255,255,255,0.10);
    --text: #eef2ff;
    --muted: #94a3c0;
    --blue: #60a5fa;
    --cyan: #67e8f9;
    --green: #4ade80;
    --yellow: #facc15;
    --purple: #c084fc;
    --red: #f87171;
    --nav-h: 64px;
}

* { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: var(--text);
}

.stApp {
    background:
        radial-gradient(ellipse 80% 50% at 10% -10%, rgba(96,165,250,0.18), transparent),
        radial-gradient(ellipse 60% 40% at 90% 5%, rgba(103,232,249,0.14), transparent),
        radial-gradient(ellipse 50% 60% at 50% 110%, rgba(74,222,128,0.10), transparent),
        var(--bg);
    min-height: 100vh;
}

section[data-testid="stSidebar"] { display: none !important; }

.block-container { padding: 0 1.5rem 3rem 1.5rem !important; max-width: 1400px; }

/* ── NAV BAR ── */
.nebula-nav {
    position: sticky;
    top: 0;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 1.5rem;
    height: var(--nav-h);
    background: rgba(5,8,16,0.72);
    backdrop-filter: blur(24px) saturate(180%);
    -webkit-backdrop-filter: blur(24px) saturate(180%);
    border-bottom: 1px solid var(--glass-border);
    margin-bottom: 2rem;
    margin-left: -1.5rem;
    margin-right: -1.5rem;
    width: calc(100% + 3rem);
}

.nebula-logo {
    font-size: 1.15rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #60a5fa, #67e8f9, #4ade80);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    white-space: nowrap;
}

.nebula-navlinks {
    display: flex;
    gap: 0.35rem;
    align-items: center;
}

.nav-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.48rem 1rem;
    border-radius: 12px;
    font-size: 0.84rem;
    font-weight: 500;
    cursor: pointer;
    border: 1px solid transparent;
    background: transparent;
    color: var(--muted);
    transition: all 0.18s ease;
    white-space: nowrap;
    text-decoration: none;
}

.nav-btn:hover {
    background: var(--glass);
    border-color: var(--glass-border);
    color: var(--text);
}

.nav-btn.active {
    background: rgba(96,165,250,0.14);
    border-color: rgba(96,165,250,0.30);
    color: #93c5fd;
    backdrop-filter: blur(12px);
}

.nav-right {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.nav-user {
    font-size: 0.82rem;
    color: var(--muted);
    padding: 0.3rem 0.75rem;
    border-radius: 10px;
    background: var(--glass);
    border: 1px solid var(--glass-border);
}

.nav-logout {
    padding: 0.38rem 0.85rem;
    border-radius: 10px;
    font-size: 0.82rem;
    font-weight: 500;
    cursor: pointer;
    background: rgba(248,113,113,0.10);
    border: 1px solid rgba(248,113,113,0.22);
    color: #fca5a5;
    transition: all 0.15s;
}

.nav-logout:hover {
    background: rgba(248,113,113,0.20);
}

/* ── GLASS CARD ── */
.glass {
    background: linear-gradient(135deg, rgba(255,255,255,0.07), rgba(255,255,255,0.03));
    border: 1px solid var(--glass-border);
    border-radius: 20px;
    padding: 1.25rem 1.35rem;
    backdrop-filter: blur(20px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.24);
    margin-bottom: 1.25rem;
}

.glass-sm {
    background: linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.025));
    border: 1px solid var(--glass-border);
    border-radius: 16px;
    padding: 0.9rem 1rem;
    backdrop-filter: blur(16px);
}

/* ── METRIC CARDS ── */
.metric-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 1rem; margin-bottom: 1.25rem; }
.metric-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.07), rgba(255,255,255,0.03));
    border: 1px solid var(--glass-border);
    border-radius: 18px;
    padding: 1.1rem 1.2rem;
    min-height: 110px;
    position: relative;
    overflow: hidden;
    backdrop-filter: blur(16px);
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    border-radius: 18px 18px 0 0;
}
.metric-card.blue::before { background: linear-gradient(90deg, #60a5fa, transparent); }
.metric-card.cyan::before { background: linear-gradient(90deg, #67e8f9, transparent); }
.metric-card.green::before { background: linear-gradient(90deg, #4ade80, transparent); }
.metric-card.purple::before { background: linear-gradient(90deg, #c084fc, transparent); }
.metric-card.yellow::before { background: linear-gradient(90deg, #facc15, transparent); }

.metric-label { font-size: 0.72rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.09em; margin-bottom: 0.5rem; }
.metric-value { font-size: 1.9rem; font-weight: 800; color: var(--text); line-height: 1; }
.metric-desc { font-size: 0.78rem; color: var(--muted); margin-top: 0.4rem; }

/* ── SECTION TITLE ── */
.section-title { font-size: 1.05rem; font-weight: 700; margin-bottom: 1rem; color: var(--text); }
.page-title { font-size: 1.8rem; font-weight: 800; margin-bottom: 0.25rem; letter-spacing: -0.02em; }
.page-sub { color: var(--muted); font-size: 0.9rem; margin-bottom: 1.5rem; }

/* ── DOC CARDS ── */
.doc-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.055), rgba(255,255,255,0.02));
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 0.9rem 1rem;
    margin-bottom: 0.7rem;
    transition: border-color 0.15s;
}
.doc-card:hover { border-color: rgba(96,165,250,0.25); }

.tag {
    display: inline-block;
    padding: 0.2rem 0.55rem;
    margin: 0.1rem;
    border-radius: 999px;
    background: rgba(96,165,250,0.12);
    border: 1px solid rgba(96,165,250,0.20);
    color: #bfdbfe;
    font-size: 0.75rem;
    font-weight: 500;
}

.tag-green {
    background: rgba(74,222,128,0.10);
    border-color: rgba(74,222,128,0.20);
    color: #bbf7d0;
}

.tag-purple {
    background: rgba(192,132,252,0.10);
    border-color: rgba(192,132,252,0.20);
    color: #e9d5ff;
}

.small-muted { color: var(--muted); font-size: 0.82rem; }
.divider { border: none; border-top: 1px solid var(--glass-border); margin: 1rem 0; }

/* ── AUTH FORMS ── */
.auth-wrap {
    max-width: 440px;
    margin: 6vh auto 0;
}
.auth-logo-big {
    font-size: 2rem;
    font-weight: 900;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #60a5fa, #67e8f9, #4ade80);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-align: center;
    margin-bottom: 0.3rem;
}
.auth-sub {
    text-align: center;
    color: var(--muted);
    font-size: 0.88rem;
    margin-bottom: 2rem;
}
.auth-tabs {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
}
.auth-tab {
    flex: 1;
    padding: 0.6rem;
    border-radius: 12px;
    border: 1px solid var(--glass-border);
    background: var(--glass);
    color: var(--muted);
    font-size: 0.88rem;
    font-weight: 600;
    cursor: pointer;
    text-align: center;
    transition: all 0.15s;
}
.auth-tab.active {
    background: rgba(96,165,250,0.14);
    border-color: rgba(96,165,250,0.30);
    color: #93c5fd;
}

/* ── ARTICLE CARD ── */
.article-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.055), rgba(255,255,255,0.02));
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 1rem 1.1rem;
    margin-bottom: 0.8rem;
    transition: all 0.15s;
}
.article-card:hover { border-color: rgba(96,165,250,0.25); background: rgba(255,255,255,0.07); }
.article-title { font-size: 0.92rem; font-weight: 600; color: var(--text); margin-bottom: 0.3rem; }
.article-meta { font-size: 0.78rem; color: var(--muted); margin-bottom: 0.4rem; }
.article-abstract { font-size: 0.82rem; color: #cbd5e1; line-height: 1.55; }

/* ── STREAMLIT OVERRIDE ── */
.stButton > button {
    border-radius: 14px !important;
    border: 1px solid var(--glass-border) !important;
    background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03)) !important;
    color: var(--text) !important;
    font-weight: 500 !important;
    transition: all 0.15s !important;
    backdrop-filter: blur(12px) !important;
}
.stButton > button:hover {
    border-color: rgba(96,165,250,0.30) !important;
    background: rgba(96,165,250,0.10) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, rgba(96,165,250,0.22), rgba(103,232,249,0.12)) !important;
    border-color: rgba(96,165,250,0.40) !important;
    color: #93c5fd !important;
}

.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 12px !important;
    color: var(--text) !important;
}

.stFileUploader > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px dashed var(--glass-border) !important;
    border-radius: 14px !important;
}

[data-testid="stExpander"] {
    background: var(--glass) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 14px !important;
}

.stProgress > div > div > div {
    background: linear-gradient(90deg, #60a5fa, #67e8f9) !important;
    border-radius: 99px !important;
}

.stDataFrame { border-radius: 14px !important; }

/* ── ANALYSIS STATS ── */
.stat-row { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 0.75rem; }
.stat-pill {
    padding: 0.3rem 0.75rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    background: rgba(96,165,250,0.10);
    border: 1px solid rgba(96,165,250,0.18);
    color: #93c5fd;
}

/* ── CONNECTION BADGE ── */
.conn-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    background: rgba(74,222,128,0.10);
    border: 1px solid rgba(74,222,128,0.20);
    color: #86efac;
}

/* ── SIMILARITY BAR ── */
.sim-bar-wrap { background: rgba(255,255,255,0.06); border-radius: 999px; height: 5px; margin-top: 0.3rem; }
.sim-bar-fill { height: 5px; border-radius: 999px; background: linear-gradient(90deg, #60a5fa, #4ade80); }

/* Plotly transparent bg */
.js-plotly-plot .plotly { background: transparent !important; }

/* Hide streamlit decorations */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# STATE / PERSISTENCE
# ============================================================
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()

def load_db():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_db():
    data = {
        "users": st.session_state.users,
        "repository": st.session_state.repository,
        "search_history": st.session_state.search_history,
        "user_interest": st.session_state.user_interest,
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def init_state():
    db = load_db()
    st.session_state.setdefault("users", db.get("users", {
        "demo@nebula.ai": {
            "name": "Usuário Demo",
            "password": hash_password("demo123"),
            "research": "Inteligência Artificial aplicada à análise de documentos",
        }
    }))
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("current_user", None)
    st.session_state.setdefault("page", "Dashboard")
    st.session_state.setdefault("repository", db.get("repository", []))
    st.session_state.setdefault("search_history", db.get("search_history", []))
    st.session_state.setdefault("user_interest", db.get("user_interest", {}))
    st.session_state.setdefault("auth_mode", "login")
    st.session_state.setdefault("quick_query", "")

init_state()
inject_css()


# ============================================================
# UTILITIES — TEXT
# ============================================================
def normalize_text(text):
    if not text: return ""
    repl = {'á':'a','à':'a','â':'a','ã':'a','ä':'a','é':'e','ê':'e','è':'e','ë':'e',
            'í':'i','ì':'i','î':'i','ï':'i','ó':'o','ò':'o','ô':'o','õ':'o','ö':'o',
            'ú':'u','ù':'u','û':'u','ü':'u','ç':'c'}
    out = []
    for ch in text.lower():
        out.append(repl.get(ch, ch))
    return re.sub(r'\s+', ' ', ''.join(out)).strip()

def tokenize(text):
    words = re.findall(r"[a-zA-ZÀ-ÿ0-9\-]{3,}", str(text).lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]

def extract_keywords_tfidf(text, top_n=20):
    """TF-IDF like keyword extraction from a single document"""
    if not text: return []
    sentences = re.split(r'[.!?]\s+', text)
    words = tokenize(text)
    if not words: return []
    
    # Term frequency
    tf = Counter(words)
    total = sum(tf.values()) or 1
    
    # Inverse document frequency proxy: penalize very short common words
    # boost words that appear in multiple sentences
    sentence_presence = defaultdict(int)
    for sent in sentences:
        sent_words = set(tokenize(sent))
        for w in sent_words:
            sentence_presence[w] += 1
    
    n_sents = max(len(sentences), 1)
    scores = {}
    for word, count in tf.items():
        if len(word) < 3: continue
        tf_score = count / total
        # IDF-like: words in more sentences get higher score (they're more topical)
        idf_score = math.log(1 + sentence_presence[word])
        # Length bonus: longer words tend to be more specific
        len_bonus = min(len(word) / 10.0, 1.2)
        scores[word] = tf_score * idf_score * len_bonus
    
    return [w for w, _ in sorted(scores.items(), key=lambda x: -x[1])[:top_n]]

def summarize_extractive(text, max_sentences=4):
    """Extractive summarization using sentence scoring"""
    if not text or len(text) < 100:
        return text[:500] if text else "Sem conteúdo disponível."
    
    text_clean = re.sub(r'\n+', ' ', text).strip()
    sentences = re.split(r'(?<=[.!?])\s+', text_clean)
    sentences = [s.strip() for s in sentences if len(s.split()) > 5]
    if not sentences: return text[:500]
    
    word_freq = Counter(tokenize(text))
    total_words = sum(word_freq.values()) or 1
    # Normalize
    for w in word_freq:
        word_freq[w] = word_freq[w] / total_words
    
    scored = []
    for i, sent in enumerate(sentences):
        words = tokenize(sent)
        if not words: continue
        score = sum(word_freq.get(w, 0) for w in words) / len(words)
        # Boost first sentences (abstracts often start with key info)
        if i < 3: score *= 1.4
        # Penalize very short sentences
        if len(words) < 8: score *= 0.6
        scored.append((score, sent))
    
    if not scored: return text[:600]
    top = [s for _, s in sorted(scored, reverse=True)[:max_sentences]]
    # Re-order by original position
    ordered = [s for s in sentences if s in top][:max_sentences]
    return ' '.join(ordered)[:1000]

def detect_topic(text, fallback="Pesquisa Geral"):
    t = normalize_text(text)
    scores = {}
    for topic, terms in TOPIC_RULES.items():
        score = sum(2 if term in t else 0 for term in terms)
        scores[topic] = score
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else fallback

def detect_years(text):
    years = [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", str(text))]
    return sorted(set(y for y in years if 1900 <= y <= datetime.now().year + 2))

def infer_nationality(text):
    t = normalize_text(text)
    for country in NATIONALITY_COORDS:
        if country.lower() in t: return country
    return "Brasil"

def cosine_similarity(text_a, text_b):
    if not text_a or not text_b: return 0.0
    ta = Counter(tokenize(text_a))
    tb = Counter(tokenize(text_b))
    if not ta or not tb: return 0.0
    keys = set(ta) | set(tb)
    dot = sum(ta[k] * tb[k] for k in keys)
    na = math.sqrt(sum(v*v for v in ta.values()))
    nb = math.sqrt(sum(v*v for v in tb.values()))
    if not na or not nb: return 0.0
    return round(dot / (na * nb), 4)

def score_relevance(query, text, keywords):
    q_terms = set(tokenize(query))
    if not q_terms: return 0.0
    doc_terms = set(tokenize(text)) | set(keywords)
    inter = len(q_terms & doc_terms)
    union = len(q_terms | doc_terms) or 1
    return round((inter / union) * 100, 2)

# ============================================================
# PDF / FILE PARSING — REAL ANALYSIS
# ============================================================
def extract_text_from_pdf_bytes(file_bytes):
    """Real PDF text extraction using pdfplumber first, fallback to PyPDF2"""
    text_parts = []
    
    # Try pdfplumber first (better extraction)
    if pdfplumber is not None:
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages[:40]:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            if text_parts:
                return "\n".join(text_parts)[:MAX_TEXT_CHARS]
        except Exception:
            pass
    
    # Fallback to PyPDF2
    if PyPDF2 is not None:
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages[:40]:
                try:
                    t = page.extract_text()
                    if t: text_parts.append(t)
                except: pass
            if text_parts:
                return "\n".join(text_parts)[:MAX_TEXT_CHARS]
        except Exception:
            pass
    
    # Last resort: try to extract raw text from PDF bytes
    try:
        raw = file_bytes.decode('latin-1', errors='ignore')
        # Extract text between BT/ET markers (PDF text objects)
        texts = re.findall(r'\(([^)]{3,})\)', raw)
        clean = ' '.join(t for t in texts if t.isprintable() and len(t) > 3)
        if len(clean) > 200:
            return clean[:MAX_TEXT_CHARS]
    except: pass
    
    return ""

def extract_text_from_docx(file_bytes):
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
        # Extract text from XML tags
        text = re.sub(r"<w:t[^>]*>", "\n", xml)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()[:MAX_TEXT_CHARS]
    except: return ""

def extract_text_from_tabular(file_bytes, suffix):
    try:
        if suffix == "csv":
            df = pd.read_csv(io.BytesIO(file_bytes))
        else:
            df = pd.read_excel(io.BytesIO(file_bytes))
        # Rich description of the spreadsheet
        desc = []
        desc.append(f"Planilha com {len(df)} linhas e {len(df.columns)} colunas.")
        desc.append(f"Colunas: {', '.join(str(c) for c in df.columns[:20])}")
        for col in df.select_dtypes(include=[np.number]).columns[:10]:
            stats = df[col].describe()
            desc.append(f"Coluna '{col}': média={stats['mean']:.2f}, min={stats['min']:.2f}, max={stats['max']:.2f}")
        desc.append("\nAmostra dos dados:")
        desc.append(df.head(20).to_string())
        return "\n".join(desc)[:MAX_TEXT_CHARS]
    except: return ""

def read_text_by_suffix(file_name, file_bytes):
    suffix = file_name.lower().split(".")[-1] if "." in file_name else ""
    if suffix == "pdf":
        return extract_text_from_pdf_bytes(file_bytes)
    if suffix == "docx":
        return extract_text_from_docx(file_bytes)
    if suffix in {"txt", "md", "py", "json"}:
        try: return file_bytes.decode("utf-8", errors="ignore")[:MAX_TEXT_CHARS]
        except: return ""
    if suffix in {"csv", "xlsx", "xls"}:
        return extract_text_from_tabular(file_bytes, suffix)
    return ""

def file_kind(file_name):
    suffix = file_name.lower().split(".")[-1] if "." in file_name else ""
    mapping = {"pdf":"PDF","docx":"Word","txt":"Texto","md":"Markdown",
               "csv":"CSV","xlsx":"Planilha","xls":"Planilha",
               "png":"Imagem","jpg":"Imagem","jpeg":"Imagem","webp":"Imagem",
               "py":"Código","json":"JSON"}
    return mapping.get(suffix, "Arquivo")

def extract_author_from_text(text):
    patterns = [
        r'(?:author|autor|autores|authors)[:\s]+([A-ZÀ-ÿ][A-Za-zÀ-ÿ\s,\.]{5,80})',
        r'(?:by|por)\s+([A-ZÀ-ÿ][A-Za-zÀ-ÿ\s]{5,60})',
        r'\b([A-Z][a-zà-ÿ]+(?:\s+[A-Z][a-zà-ÿ]+){1,3})\s*\n',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            candidate = m.group(1).strip()
            if 5 < len(candidate) < 80:
                return candidate
    return "Desconhecido"

def detect_document_language(text):
    pt_markers = ["que","não","para","com","uma","são","está","sendo","como","pelo","pela","dos","das"]
    en_markers = ["the","and","that","this","with","from","have","been","which","their","abstract"]
    t = text.lower()
    pt_score = sum(1 for m in pt_markers if f' {m} ' in t)
    en_score = sum(1 for m in en_markers if f' {m} ' in t)
    return "Português" if pt_score >= en_score else "Inglês"

def analyze_document_structure(text):
    """Detect sections in academic papers"""
    sections = {}
    section_patterns = {
        "Resumo/Abstract": r'(?:resumo|abstract)\s*[\:\n](.{100,2000}?)(?=\n[A-Z]|\nintrodução|\nintroduction|keywords|palavras)',
        "Introdução": r'(?:introdução|introduction)\s*[\:\n](.{100,2000}?)(?=\n[A-Z]|\nmétodo|\nmaterial)',
        "Metodologia": r'(?:método|metodologia|methodology|methods)\s*[\:\n](.{100,2000}?)(?=\n[A-Z]|\nresultado)',
        "Resultados": r'(?:resultados|results)\s*[\:\n](.{100,2000}?)(?=\n[A-Z]|\ndiscussão|\nconclusão)',
        "Conclusão": r'(?:conclusão|conclusion)\s*[\:\n](.{100,3000}?)(?=\n[A-Z]|\nreferência|$)',
    }
    for name, pattern in section_patterns.items():
        m = re.search(pattern, text, re.I | re.DOTALL)
        if m:
            sections[name] = m.group(1).strip()[:500]
    return sections

def compute_readability(text):
    words = re.findall(r'\w+', text)
    sentences = re.split(r'[.!?]+', text)
    sentences = [s for s in sentences if len(s.split()) > 3]
    if not words or not sentences: return {"clarity": 50, "words": 0, "sentences": 0}
    
    avg_words_per_sent = len(words) / max(len(sentences), 1)
    avg_syllables = sum(max(1, len(re.findall(r'[aeiouáéíóúàèìòùãõâêîôû]', w.lower()))) for w in words) / max(len(words), 1)
    
    # Flesch-like score (simplified)
    score = 100 - (1.015 * avg_words_per_sent) - (84.6 * avg_syllables)
    score = max(0, min(100, score))
    
    return {
        "clarity": round(score, 1),
        "words": len(words),
        "sentences": len(sentences),
        "avg_words_per_sentence": round(avg_words_per_sent, 1),
        "estimated_pages": max(1, round(len(words) / 300)),
        "reading_time_min": max(1, round(len(words) / 200)),
    }

def make_document_record(file_name, file_bytes):
    kind = file_kind(file_name)
    text = read_text_by_suffix(file_name, file_bytes)
    
    is_image = kind == "Imagem"
    image_meta = {}
    if is_image:
        try:
            img = Image.open(io.BytesIO(file_bytes))
            arr = np.array(img.convert("RGB"))
            mean_rgb = arr.reshape(-1,3).mean(axis=0)
            brightness = float(np.mean(np.dot(arr[...,:3], [0.299,0.587,0.114])))
            gray = img.convert("L").resize((8,8))
            arr_g = np.array(gray)
            bits = arr_g > arr_g.mean()
            image_meta = {
                "width": img.width, "height": img.height,
                "brightness": round(brightness, 2),
                "r": round(float(mean_rgb[0]),1), "g": round(float(mean_rgb[1]),1), "b": round(float(mean_rgb[2]),1),
                "hash": "".join("1" if x else "0" for x in bits.flatten())
            }
        except: image_meta = {}
    
    # Deep text analysis
    keywords = extract_keywords_tfidf(text if text else file_name, top_n=25)
    summary = summarize_extractive(text, max_sentences=4) if text else f"Arquivo do tipo {kind}."
    topic = detect_topic(text if text else file_name)
    years = detect_years(text)
    nationality = infer_nationality(text if text else file_name)
    author = extract_author_from_text(text) if text else "Desconhecido"
    language = detect_document_language(text) if text else "Desconhecido"
    sections = analyze_document_structure(text) if text and kind == "PDF" else {}
    readability = compute_readability(text) if text else {}
    
    # Extract references count
    refs_match = re.findall(r'\[\d+\]|\d+\.\s+[A-ZÀ-ÿ][a-zà-ÿ]+', text[-3000:]) if text else []
    ref_count = len(set(refs_match[:50]))
    
    return {
        "id": hashlib.md5(f"{file_name}-{datetime.now().isoformat()}".encode()).hexdigest()[:12],
        "name": file_name,
        "kind": kind,
        "topic": topic,
        "summary": summary,
        "keywords": keywords,
        "author": author,
        "years": years,
        "year": years[0] if years else datetime.now().year,
        "nationality": nationality,
        "language": language,
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "text": text[:12000],
        "full_text_len": len(text),
        "image_meta": image_meta,
        "size_kb": round(len(file_bytes)/1024, 1),
        "sections": sections,
        "readability": readability,
        "ref_count": ref_count,
    }

# ============================================================
# SEARCH & RECOMMENDATION
# ============================================================
def current_user():
    if not st.session_state.current_user: return {}
    return st.session_state.users.get(st.session_state.current_user, {})

def update_user_interest(email, terms):
    if not email: return
    bag = st.session_state.user_interest.get(email, {})
    for t in terms:
        if len(t) >= 3: bag[t] = bag.get(t, 0) + 1
    st.session_state.user_interest[email] = dict(sorted(bag.items(), key=lambda x: -x[1])[:60])
    save_db()

def recommend_terms(email, limit=10):
    profile = st.session_state.user_interest.get(email, {})
    return [t for t, _ in sorted(profile.items(), key=lambda x: -x[1])[:limit]]

def local_search(query, docs):
    results = []
    for doc in docs:
        text = " ".join([doc.get("name",""), doc.get("summary",""),
                         doc.get("topic",""), " ".join(doc.get("keywords",[])),
                         doc.get("text","")[:3000]])
        score = score_relevance(query, text, doc.get("keywords",[]))
        if score > 0:
            item = dict(doc); item["score"] = score; results.append(item)
    return sorted(results, key=lambda x: (-x["score"], x["name"]))

def related_documents(target, docs, limit=8):
    out = []
    target_text = " ".join([target.get("summary",""), " ".join(target.get("keywords",[])), target.get("text","")[:2000]])
    for doc in docs:
        if doc["id"] == target["id"]: continue
        doc_text = " ".join([doc.get("summary",""), " ".join(doc.get("keywords",[])), doc.get("text","")[:2000]])
        sim = cosine_similarity(target_text, doc_text)
        if doc.get("topic") == target.get("topic"): sim += 0.10
        if sim > 0.05:
            d = dict(doc); d["similarity"] = round(sim * 100, 1); out.append(d)
    return sorted(out, key=lambda x: -x["similarity"])[:limit]

def search_semantic_scholar(query, limit=8):
    try:
        resp = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query": query, "limit": limit,
                    "fields": "title,authors,year,abstract,venue,openAccessPdf,externalIds,citationCount"},
            timeout=12)
        if resp.status_code != 200: return []
        data = resp.json().get("data", [])
        out = []
        for item in data:
            authors = ", ".join(a.get("name","") for a in item.get("authors",[])[:4])
            open_pdf = item.get("openAccessPdf") or {}
            doi = (item.get("externalIds") or {}).get("DOI","")
            url = open_pdf.get("url") or (f"https://doi.org/{doi}" if doi else "")
            kw_text = " ".join([item.get("title",""), item.get("abstract","")[:500]])
            out.append({
                "title": item.get("title","Sem título"),
                "authors": authors or "Não informado",
                "year": item.get("year","?"),
                "abstract": (item.get("abstract") or "")[:400],
                "source": item.get("venue","Semantic Scholar"),
                "citations": item.get("citationCount",0),
                "url": url,
                "keywords": extract_keywords_tfidf(kw_text, 8),
                "topic": detect_topic(kw_text),
            })
        return out
    except: return []

def search_crossref(query, limit=5):
    try:
        resp = requests.get(
            "https://api.crossref.org/works",
            params={"query": query, "rows": limit,
                    "select": "title,author,issued,DOI,abstract,container-title,is-referenced-by-count",
                    "mailto": "nebula@research.ai"},
            timeout=12)
        if resp.status_code != 200: return []
        items = resp.json().get("message",{}).get("items",[])
        out = []
        for item in items:
            title = (item.get("title") or ["Sem título"])[0]
            authors_list = item.get("author",[])
            authors = ", ".join(f"{a.get('given','')} {a.get('family','')}".strip() for a in authors_list[:4])
            year = None
            if item.get("issued",{}).get("date-parts"):
                year = item["issued"]["date-parts"][0][0]
            doi = item.get("DOI","")
            abstract = re.sub(r"<[^>]+>"," ", item.get("abstract","") or "")[:400]
            kw_text = f"{title} {abstract}"
            out.append({
                "title": title,
                "authors": authors or "Não informado",
                "year": year or "?",
                "abstract": abstract,
                "source": (item.get("container-title") or ["Crossref"])[0],
                "citations": item.get("is-referenced-by-count",0),
                "url": f"https://doi.org/{doi}" if doi else "",
                "keywords": extract_keywords_tfidf(kw_text, 8),
                "topic": detect_topic(kw_text),
            })
        return out
    except: return []

def recognize_research_intent(query):
    q = normalize_text(query)
    detected_topic = detect_topic(q)
    years = detect_years(q)
    intent = "pesquisa bibliográfica"
    if any(w in q for w in ["imagem","figura","foto","visual"]): intent = "busca visual"
    elif any(w in q for w in ["comparar","conectar","relacionar","semelhante"]): intent = "conexão temática"
    elif any(w in q for w in ["analisar","análise","métricas","tendência"]): intent = "análise"
    keywords = extract_keywords_tfidf(query, 12)
    topic_terms = TOPIC_RULES.get(detected_topic, [])[:5]
    suggestions = []
    for t in keywords + topic_terms:
        if t not in suggestions: suggestions.append(t)
    return {"intent": intent, "topic": detected_topic, "keywords": keywords,
            "search_terms": suggestions[:12], "years": years}

# ============================================================
# RESEARCH CONNECTIONS — REAL SIMILARITY NETWORK
# ============================================================
def build_research_network(docs, external_articles=None, user_research=""):
    """Build a real similarity-based research network"""
    nodes = []
    edges = []
    
    # Add user docs
    for doc in docs:
        doc_text = " ".join([doc.get("summary",""), " ".join(doc.get("keywords",[])),
                              doc.get("text","")[:2000]])
        nodes.append({
            "id": doc["id"],
            "label": doc["name"][:40],
            "type": "local",
            "topic": doc.get("topic",""),
            "text": doc_text,
            "year": doc.get("year",""),
            "author": doc.get("author",""),
        })
    
    # Add external articles
    for i, art in enumerate(external_articles or []):
        art_text = f"{art.get('title','')} {art.get('abstract','')}"
        nodes.append({
            "id": f"ext_{i}",
            "label": art.get("title","")[:40],
            "type": "external",
            "topic": art.get("topic",""),
            "text": art_text,
            "year": art.get("year",""),
            "author": art.get("authors",""),
            "url": art.get("url",""),
        })
    
    # Add user research as central node if present
    if user_research:
        nodes.insert(0, {
            "id": "user_node",
            "label": "Minha Pesquisa",
            "type": "user",
            "topic": detect_topic(user_research),
            "text": user_research,
            "year": datetime.now().year,
            "author": current_user().get("name",""),
        })
    
    # Build edges based on REAL similarity
    threshold = 0.08
    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            sim = cosine_similarity(nodes[i]["text"], nodes[j]["text"])
            # Topic match bonus
            if nodes[i]["topic"] == nodes[j]["topic"] and nodes[i]["topic"]:
                sim += 0.08
            if sim > threshold:
                edges.append({
                    "source": i, "target": j,
                    "weight": round(sim, 3),
                    "same_topic": nodes[i]["topic"] == nodes[j]["topic"]
                })
    
    return nodes, edges

def render_3d_network(nodes, edges):
    """Render a 3D network visualization with Plotly"""
    if len(nodes) < 2: return None
    
    # Position nodes using a simple force-directed layout approximation
    np.random.seed(42)
    n = len(nodes)
    
    # Initialize positions
    pos = np.random.randn(n, 3) * 2
    
    # Simple iterative positioning (spring-like)
    for _ in range(50):
        forces = np.zeros((n, 3))
        for edge in edges:
            i, j = edge["source"], edge["target"]
            if i >= n or j >= n: continue
            diff = pos[j] - pos[i]
            dist = max(np.linalg.norm(diff), 0.01)
            # Attraction
            k = edge["weight"] * 2
            forces[i] += k * diff / dist
            forces[j] -= k * diff / dist
        # Repulsion between all nodes
        for i in range(n):
            for j in range(i+1, n):
                diff = pos[j] - pos[i]
                dist = max(np.linalg.norm(diff), 0.1)
                repulse = 0.5 / (dist**2)
                forces[i] -= repulse * diff / dist
                forces[j] += repulse * diff / dist
        pos += forces * 0.05
        pos = np.clip(pos, -6, 6)
    
    # Color mapping
    type_colors = {
        "user": "#facc15",
        "local": "#60a5fa",
        "external": "#4ade80",
    }
    topic_color_map = {}
    palette = ["#60a5fa","#4ade80","#c084fc","#f97316","#67e8f9","#f87171","#a78bfa","#34d399"]
    unique_topics = list(set(n["topic"] for n in nodes if n.get("topic")))
    for idx, t in enumerate(unique_topics):
        topic_color_map[t] = palette[idx % len(palette)]
    
    # Edge traces
    edge_traces = []
    for edge in edges:
        i, j = edge["source"], edge["target"]
        if i >= n or j >= n: continue
        opacity = min(0.8, edge["weight"] * 2)
        color = "#60a5fa" if edge["same_topic"] else "rgba(148,163,192,0.4)"
        edge_traces.append(go.Scatter3d(
            x=[pos[i,0], pos[j,0], None],
            y=[pos[i,1], pos[j,1], None],
            z=[pos[i,2], pos[j,2], None],
            mode="lines",
            line=dict(color=color, width=max(1, edge["weight"]*5)),
            opacity=opacity,
            hoverinfo="none",
            showlegend=False,
        ))
    
    # Node traces by type
    for node_type, color in type_colors.items():
        type_nodes = [(idx, nd) for idx, nd in enumerate(nodes) if nd["type"] == node_type]
        if not type_nodes: continue
        idxs = [idx for idx, _ in type_nodes]
        nds = [nd for _, nd in type_nodes]
        
        size = {"user": 14, "local": 10, "external": 8}[node_type]
        labels = {"user": "Sua Pesquisa", "local": "Seus Documentos", "external": "Artigos Externos"}
        
        edge_traces.append(go.Scatter3d(
            x=pos[idxs, 0], y=pos[idxs, 1], z=pos[idxs, 2],
            mode="markers+text",
            marker=dict(size=size, color=color, opacity=0.9,
                       line=dict(color="rgba(255,255,255,0.3)", width=1)),
            text=[nd["label"] for nd in nds],
            textposition="top center",
            textfont=dict(size=8, color="#e2e8f0"),
            hovertext=[f"{nd['label']}<br>Tipo: {nd['type']}<br>Tema: {nd['topic']}<br>Ano: {nd['year']}" for nd in nds],
            hoverinfo="text",
            name=labels[node_type],
        ))
    
    layout = go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=600,
        margin=dict(l=0, r=0, t=30, b=0),
        scene=dict(
            bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, showline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, showline=False),
            zaxis=dict(showgrid=False, showticklabels=False, zeroline=False, showline=False),
        ),
        legend=dict(
            font=dict(color="#94a3c0", size=11),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.1)",
            borderwidth=1,
        ),
        title=dict(text="Rede de Conexões entre Pesquisas", font=dict(color="#eef2ff", size=14)),
    )
    
    return go.Figure(data=edge_traces, layout=layout)

# ============================================================
# NAV BAR
# ============================================================
def render_navbar():
    user = current_user()
    pages = ["Dashboard", "Pesquisa Inteligente", "Repositório", "Análise Avançada", "Conexões", "Perfil"]
    
    nav_html = f"""
    <div class="nebula-nav">
        <div class="nebula-logo">Nebula Research</div>
        <div class="nebula-navlinks">
    """
    for p in pages:
        active = "active" if st.session_state.page == p else ""
        nav_html += f'<span class="nav-btn {active}" onclick="">{p}</span>'
    
    nav_html += f"""
        </div>
        <div class="nav-right">
            <span class="nav-user">{user.get('name','')}</span>
        </div>
    </div>
    """
    st.markdown(nav_html, unsafe_allow_html=True)
    
    # Real navigation buttons (hidden via CSS magic using columns)
    cols = st.columns([2] + [1]*len(pages) + [1])
    with cols[0]:
        pass
    page_buttons = []
    for i, p in enumerate(pages):
        with cols[i+1]:
            if st.button(p, key=f"nav_{p}", use_container_width=True):
                st.session_state.page = p
                st.rerun()
    with cols[-1]:
        if st.button("Sair", key="nav_logout"):
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.rerun()

# ============================================================
# AUTH PAGE
# ============================================================
def page_auth():
    st.markdown("""
    <div style="max-width:440px;margin:5vh auto 0;">
        <div class="auth-logo-big">Nebula Research</div>
        <div class="auth-sub">Plataforma inteligente de pesquisa acadêmica</div>
    </div>
    """, unsafe_allow_html=True)
    
    col_l, col_c, col_r = st.columns([1,2,1])
    with col_c:
        # Auth mode tabs
        tab_login, tab_reg = st.tabs(["Entrar", "Criar conta"])
        
        with tab_login:
            st.markdown("<div class='glass' style='margin-top:0.5rem'>", unsafe_allow_html=True)
            email = st.text_input("E-mail", key="li_email", placeholder="seu@email.com")
            password = st.text_input("Senha", type="password", key="li_pass", placeholder="Senha")
            if st.button("Acessar", use_container_width=True, key="li_btn", type="primary"):
                user = st.session_state.users.get(email)
                if user and user["password"] == hash_password(password):
                    st.session_state.logged_in = True
                    st.session_state.current_user = email
                    st.session_state.page = "Dashboard"
                    st.rerun()
                else:
                    st.error("E-mail ou senha inválidos.")
            st.markdown("<div class='small-muted' style='margin-top:0.5rem'>Demo: demo@nebula.ai / demo123</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        with tab_reg:
            st.markdown("<div class='glass' style='margin-top:0.5rem'>", unsafe_allow_html=True)
            name = st.text_input("Nome completo", key="rg_name", placeholder="Seu nome")
            reg_email = st.text_input("E-mail", key="rg_email", placeholder="seu@email.com")
            reg_pass = st.text_input("Senha", type="password", key="rg_pass", placeholder="Crie uma senha")
            research = st.text_input("Área de pesquisa", key="rg_research", placeholder="Ex: Machine learning aplicado à saúde")
            if st.button("Criar conta", use_container_width=True, key="rg_btn", type="primary"):
                if not all([name, reg_email, reg_pass, research]):
                    st.error("Preencha todos os campos.")
                elif reg_email in st.session_state.users:
                    st.error("Este e-mail já está cadastrado.")
                else:
                    st.session_state.users[reg_email] = {
                        "name": name,
                        "password": hash_password(reg_pass),
                        "research": research,
                    }
                    save_db()
                    st.success("Conta criada! Agora acesse na aba Entrar.")
            st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# DASHBOARD
# ============================================================
def page_dashboard():
    user = current_user()
    docs = st.session_state.repository
    research = user.get("research","")
    
    st.markdown(f"<div class='page-title'>Bem-vindo, {user.get('name','').split()[0]}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='page-sub'>{research or 'Configure sua área de pesquisa no Perfil'}</div>", unsafe_allow_html=True)
    
    # Metrics
    df = pd.DataFrame([{
        "topic": d.get("topic"), "author": d.get("author"),
        "year": d.get("year"), "kind": d.get("kind")
    } for d in docs]) if docs else pd.DataFrame()
    
    st.markdown("""
    <div class='metric-grid'>
    """, unsafe_allow_html=True)
    
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, label, val, desc, color in [
        (c1, "Documentos", len(docs), "No repositório", "blue"),
        (c2, "Temas", df["topic"].nunique() if not df.empty else 0, "Identificados", "cyan"),
        (c3, "Autores", df["author"].nunique() if not df.empty else 0, "Detectados", "green"),
        (c4, "Buscas", len(st.session_state.search_history), "Registradas", "purple"),
        (c5, "PDFs", len([d for d in docs if d.get("kind")=="PDF"]), "Analisados", "yellow"),
    ]:
        with col:
            st.markdown(f"""
            <div class='metric-card {color}'>
                <div class='metric-label'>{label}</div>
                <div class='metric-value'>{val}</div>
                <div class='metric-desc'>{desc}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Search results based on user's research
    left, right = st.columns([1.1, 0.9])
    
    with left:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Artigos correlatos à sua pesquisa</div>", unsafe_allow_html=True)
        
        if not research:
            st.info("Defina sua área de pesquisa no Perfil para ver artigos correlatos.")
        else:
            # Get cached or fetch
            cache_key = f"dashboard_articles_{hashlib.md5(research.encode()).hexdigest()[:8]}"
            articles = st.session_state.get(cache_key)
            
            if articles is None:
                with st.spinner("Buscando artigos correlatos..."):
                    terms = extract_keywords_tfidf(research, 6)
                    query = " ".join(terms[:5]) if terms else research
                    articles = search_semantic_scholar(query, limit=6)
                    if not articles:
                        articles = search_crossref(query, limit=4)
                st.session_state[cache_key] = articles
            
            if not articles:
                st.info("Não foi possível carregar artigos agora. Verifique sua conexão.")
            else:
                for art in articles[:5]:
                    # Compute real similarity to user's research
                    art_text = f"{art.get('title','')} {art.get('abstract','')}"
                    sim = cosine_similarity(research, art_text)
                    sim_pct = round(min(sim * 200, 99), 1)  # scale for display
                    
                    url = art.get("url","")
                    title_html = f'<a href="{url}" target="_blank" style="color:#93c5fd;text-decoration:none">{art["title"]}</a>' if url else art["title"]
                    
                    st.markdown(f"""
                    <div class='article-card'>
                        <div class='article-title'>{title_html}</div>
                        <div class='article-meta'>{art.get('authors','')} · {art.get('year','?')} · {art.get('source','')} · {art.get('citations',0)} citações</div>
                        <div class='article-abstract'>{art.get('abstract','')[:250]}...</div>
                        <div style='margin-top:0.5rem'>
                            <span class='tag'>{art.get('topic','')}</span>
                            <span class='tag-green' style='display:inline-block;padding:0.2rem 0.55rem;margin:0.1rem;border-radius:999px;background:rgba(74,222,128,0.10);border:1px solid rgba(74,222,128,0.20);color:#bbf7d0;font-size:0.72rem'>Correlação: {sim_pct}%</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with right:
        # Profile terms
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Seu perfil de interesse</div>", unsafe_allow_html=True)
        profile_terms = recommend_terms(st.session_state.current_user, 20)
        if profile_terms:
            st.markdown("".join([f"<span class='tag'>{t}</span>" for t in profile_terms]), unsafe_allow_html=True)
        else:
            st.info("Faça buscas e envie documentos para o sistema aprender seu perfil.")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Quick search suggestions
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Sugestões de busca</div>", unsafe_allow_html=True)
        suggestions = profile_terms[:5] if profile_terms else [
            "machine learning", "análise documental", "redes neurais", "patrimônio digital", "ciência aberta"
        ]
        for term in suggestions[:4]:
            if st.button(term, key=f"sugg_{term}", use_container_width=True):
                st.session_state.quick_query = term
                st.session_state.page = "Pesquisa Inteligente"
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Recent docs
        if docs:
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Documentos recentes</div>", unsafe_allow_html=True)
            for doc in docs[-3:][::-1]:
                st.markdown(f"""
                <div class='doc-card'>
                    <b style='font-size:0.85rem'>{doc['name'][:45]}</b><br>
                    <span class='small-muted'>{doc['kind']} · {doc['topic']}</span>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# SMART SEARCH
# ============================================================
def page_smart_search():
    st.markdown("<div class='page-title'>Pesquisa Inteligente</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>Busca unificada com análise de intenção, resultados locais e artigos da internet correlacionados</div>", unsafe_allow_html=True)
    
    default_query = st.session_state.get("quick_query", "")
    query = st.text_area("Digite sua pergunta ou tema de pesquisa", value=default_query, height=100,
                         placeholder="Ex: redes neurais para classificação de imagens médicas...")
    
    col_a, col_b = st.columns([3,1])
    with col_b:
        up_image = st.file_uploader("Imagem (opcional)", type=["png","jpg","jpeg","webp"])
    
    if st.button("Executar pesquisa", use_container_width=True, type="primary"):
        if not query and up_image is None:
            st.warning("Digite uma consulta ou envie uma imagem.")
            return
        
        intent_data = recognize_research_intent(query or "imagem científica")
        update_user_interest(st.session_state.current_user, intent_data["search_terms"])
        st.session_state.search_history.append({
            "query": query, "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "intent": intent_data["intent"], "topic": intent_data["topic"],
        })
        save_db()
        
        # Intent analysis
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Análise da sua busca</div>", unsafe_allow_html=True)
        ic1, ic2, ic3 = st.columns(3)
        with ic1: st.info(f"**Intenção:** {intent_data['intent']}")
        with ic2: st.info(f"**Tema:** {intent_data['topic']}")
        with ic3: st.info(f"**Termos-chave:** {', '.join(intent_data['keywords'][:5])}")
        st.markdown("".join([f"<span class='tag'>{t}</span>" for t in intent_data["search_terms"]]), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Fetch results
        search_query = " ".join(intent_data["search_terms"][:6]) or query
        with st.spinner("Buscando artigos..."):
            scholar_results = search_semantic_scholar(search_query, limit=8)
            crossref_results = search_crossref(search_query, limit=4) if len(scholar_results) < 4 else []
        
        local_results = local_search(query, st.session_state.repository)
        
        col_l, col_r = st.columns(2)
        
        with col_l:
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Nos seus documentos</div>", unsafe_allow_html=True)
            if not local_results:
                st.info("Nenhum documento local correspondeu. Envie arquivos no Repositório.")
            else:
                for doc in local_results[:6]:
                    sim_bar = f"<div class='sim-bar-wrap'><div class='sim-bar-fill' style='width:{min(doc['score'],100)}%'></div></div>"
                    st.markdown(f"""
                    <div class='doc-card'>
                        <b>{doc['name']}</b><br>
                        <span class='small-muted'>{doc['kind']} · {doc['topic']} · relevância {doc['score']}%</span>
                        {sim_bar}
                        <div style='margin-top:0.5rem;font-size:0.82rem;color:#cbd5e1'>{doc['summary'][:200]}</div>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col_r:
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Artigos na internet</div>", unsafe_allow_html=True)
            web_results = scholar_results + crossref_results
            if not web_results:
                st.info("Não foi possível recuperar artigos agora.")
            else:
                for art in web_results[:7]:
                    url = art.get("url","")
                    title_html = f'<a href="{url}" target="_blank" style="color:#93c5fd;text-decoration:none">{art["title"]}</a>' if url else art["title"]
                    st.markdown(f"""
                    <div class='article-card'>
                        <div class='article-title'>{title_html}</div>
                        <div class='article-meta'>{art.get('authors','')} · {art.get('year','?')} · {art.get('source','')} · {art.get('citations',0)} cit.</div>
                        <div class='article-abstract'>{art.get('abstract','')[:220]}...</div>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        # External links
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Continuar pesquisando</div>", unsafe_allow_html=True)
        q_enc = quote_plus(search_query)
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"[Google Scholar]( https://scholar.google.com/scholar?q={q_enc})")
        with c2: st.markdown(f"[Semantic Scholar](https://www.semanticscholar.org/search?q={q_enc})")
        with c3: st.markdown(f"[Imagens Google](https://www.google.com/search?tbm=isch&q={q_enc})")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Image search if uploaded
        if up_image is not None:
            img = Image.open(up_image)
            arr = np.array(img.convert("RGB"))
            mean_rgb = arr.reshape(-1,3).mean(axis=0)
            brightness = float(np.mean(np.dot(arr[...,:3],[0.299,0.587,0.114])))
            
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Análise visual</div>", unsafe_allow_html=True)
            vc1, vc2, vc3, vc4 = st.columns(4)
            with vc1:
                st.markdown(f"<div class='metric-card blue'><div class='metric-label'>Largura</div><div class='metric-value'>{img.width}px</div></div>", unsafe_allow_html=True)
            with vc2:
                st.markdown(f"<div class='metric-card cyan'><div class='metric-label'>Altura</div><div class='metric-value'>{img.height}px</div></div>", unsafe_allow_html=True)
            with vc3:
                st.markdown(f"<div class='metric-card green'><div class='metric-label'>Brilho</div><div class='metric-value'>{brightness:.0f}</div></div>", unsafe_allow_html=True)
            with vc4:
                st.markdown(f"<div class='metric-card purple'><div class='metric-label'>Modo</div><div class='metric-value'>{img.mode}</div></div>", unsafe_allow_html=True)
            st.image(img, caption="Imagem enviada", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
    
    st.session_state.quick_query = ""

# ============================================================
# REPOSITORY
# ============================================================
def page_repository():
    st.markdown("<div class='page-title'>Repositório</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>Envie seus documentos para análise completa: texto, palavras-chave, resumo, estrutura e conexões</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    files = st.file_uploader(
        "Adicionar documentos",
        accept_multiple_files=True,
        type=["pdf","docx","txt","md","csv","xlsx","xls","png","jpg","jpeg","webp","py","json"],
    )
    
    if st.button("Analisar e adicionar", use_container_width=True, type="primary"):
        if not files:
            st.warning("Selecione arquivos primeiro.")
        else:
            progress = st.progress(0)
            for idx, up in enumerate(files):
                progress.progress((idx+1)/len(files), text=f"Analisando {up.name}...")
                content = up.getvalue()
                record = make_document_record(up.name, content)
                st.session_state.repository.append(record)
                update_user_interest(st.session_state.current_user, record["keywords"][:12])
            save_db()
            st.success(f"{len(files)} arquivo(s) analisados e adicionados.")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    
    docs = st.session_state.repository
    if not docs:
        st.info("Seu repositório está vazio. Envie documentos acima.")
        return
    
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Documentos catalogados</div>", unsafe_allow_html=True)
    
    search_name = st.text_input("Filtrar por nome, tema, autor ou palavra-chave", placeholder="Buscar...")
    filtered = local_search(search_name, docs) if search_name else docs
    
    for doc in filtered[:50]:
        with st.expander(f"**{doc['name']}** · {doc['kind']} · {doc['topic']}"):
            col_info, col_stats = st.columns([1.5, 1])
            
            with col_info:
                st.markdown(f"**Resumo:**  \n{doc['summary']}")
                st.markdown("**Palavras-chave:**")
                st.markdown("".join([f"<span class='tag'>{k}</span>" for k in doc['keywords'][:18]]), unsafe_allow_html=True)
                
                # Show sections if available (PDFs)
                if doc.get("sections"):
                    st.markdown("**Seções detectadas:**")
                    for sec_name, sec_text in doc["sections"].items():
                        st.markdown(f"*{sec_name}:* {sec_text[:200]}...")
            
            with col_stats:
                st.markdown(f"""
                <div class='glass-sm'>
                    <div class='metric-label'>Metadados</div>
                    <table style='font-size:0.82rem;color:#cbd5e1;width:100%;margin-top:0.4rem'>
                        <tr><td style='color:#94a3c0'>Autor</td><td>{doc.get('author','?')[:30]}</td></tr>
                        <tr><td style='color:#94a3c0'>Ano</td><td>{doc.get('year','?')}</td></tr>
                        <tr><td style='color:#94a3c0'>Idioma</td><td>{doc.get('language','?')}</td></tr>
                        <tr><td style='color:#94a3c0'>Tamanho</td><td>{doc.get('size_kb','?')} KB</td></tr>
                        <tr><td style='color:#94a3c0'>Palavras</td><td>{doc.get('readability',{}).get('words','?')}</td></tr>
                        <tr><td style='color:#94a3c0'>Páginas est.</td><td>{doc.get('readability',{}).get('estimated_pages','?')}</td></tr>
                        <tr><td style='color:#94a3c0'>Leitura</td><td>{doc.get('readability',{}).get('reading_time_min','?')} min</td></tr>
                        <tr><td style='color:#94a3c0'>Referências</td><td>{doc.get('ref_count','?')}</td></tr>
                        <tr><td style='color:#94a3c0'>Clareza</td><td>{doc.get('readability',{}).get('clarity','?')}/100</td></tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)
            
            # Related documents
            related = related_documents(doc, docs, limit=4)
            if related:
                st.markdown("**Documentos relacionados:**")
                for r in related:
                    bar_w = min(int(r['similarity']), 100)
                    st.markdown(f"""
                    <div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.35rem'>
                        <span style='font-size:0.8rem;color:#e2e8f0;flex:1'>{r['name'][:45]}</span>
                        <span style='font-size:0.75rem;color:#94a3c0'>{r['similarity']}%</span>
                    </div>
                    <div class='sim-bar-wrap'><div class='sim-bar-fill' style='width:{bar_w}%'></div></div>
                    """, unsafe_allow_html=True)
    
    st.markdown("<br>")
    if st.button("Limpar repositório", use_container_width=True):
        st.session_state.repository = []
        save_db()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# ADVANCED ANALYSIS
# ============================================================
def page_analysis():
    st.markdown("<div class='page-title'>Análise Avançada</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>Análise estatística, temporal, temática e de conteúdo do seu repositório</div>", unsafe_allow_html=True)
    
    docs = st.session_state.repository
    if not docs:
        st.info("Envie documentos no Repositório para liberar análises.")
        return
    
    df = pd.DataFrame([{
        "name": d.get("name"), "kind": d.get("kind"), "topic": d.get("topic"),
        "author": d.get("author"), "year": d.get("year"), "nationality": d.get("nationality"),
        "size_kb": d.get("size_kb"), "language": d.get("language"),
        "words": d.get("readability",{}).get("words",0),
        "clarity": d.get("readability",{}).get("clarity",0),
        "ref_count": d.get("ref_count",0),
    } for d in docs])
    
    # Summary stats
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Visão geral do acervo</div>", unsafe_allow_html=True)
    s1, s2, s3, s4, s5, s6 = st.columns(6)
    total_words = int(df["words"].sum())
    avg_clarity = round(df["clarity"].mean(), 1) if df["clarity"].any() else 0
    for col, label, val, color in [
        (s1, "Documentos", len(docs), "blue"),
        (s2, "Temas únicos", df["topic"].nunique(), "cyan"),
        (s3, "Autores únicos", df["author"].nunique(), "green"),
        (s4, "Total de palavras", f"{total_words:,}", "purple"),
        (s5, "Clareza média", f"{avg_clarity}/100", "yellow"),
        (s6, "Idiomas", df["language"].nunique(), "blue"),
    ]:
        with col:
            st.markdown(f"""
            <div class='metric-card {color}'>
                <div class='metric-label'>{label}</div>
                <div class='metric-value' style='font-size:1.4rem'>{val}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Charts row 1
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Distribuição por tema</div>", unsafe_allow_html=True)
        topic_count = df["topic"].value_counts().reset_index()
        topic_count.columns = ["Tema","Quantidade"]
        fig = px.bar(topic_count, x="Tema", y="Quantidade", text="Quantidade",
                     color="Quantidade", color_continuous_scale="Blues")
        fig.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#94a3c0"), coloraxis_showscale=False,
                         xaxis=dict(tickangle=-30))
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with c2:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Distribuição temporal</div>", unsafe_allow_html=True)
        year_count = df[df["year"].notna()]["year"].value_counts().sort_index().reset_index()
        year_count.columns = ["Ano","Quantidade"]
        fig = px.area(year_count, x="Ano", y="Quantidade",
                      color_discrete_sequence=["#60a5fa"])
        fig.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#94a3c0"))
        fig.update_traces(fill="tozeroy", line=dict(width=2))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Charts row 2
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Tipos de documento</div>", unsafe_allow_html=True)
        kind_count = df["kind"].value_counts().reset_index()
        kind_count.columns = ["Tipo","Quantidade"]
        fig = px.pie(kind_count, names="Tipo", values="Quantidade", hole=0.5,
                     color_discrete_sequence=["#60a5fa","#4ade80","#c084fc","#f97316","#67e8f9"])
        fig.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#94a3c0"), showlegend=True,
                         legend=dict(bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with c4:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Autores mais frequentes</div>", unsafe_allow_html=True)
        auth_count = df[df["author"]!="Desconhecido"]["author"].value_counts().head(10).reset_index()
        auth_count.columns = ["Autor","Contagem"]
        if not auth_count.empty:
            fig = px.bar(auth_count, x="Contagem", y="Autor", orientation="h",
                         color="Contagem", color_continuous_scale="Greens")
            fig.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                             font=dict(color="#94a3c0"), coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Autores não identificados nos documentos.")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Keyword frequency
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Palavras-chave mais frequentes no acervo</div>", unsafe_allow_html=True)
    all_keywords = []
    for d in docs: all_keywords.extend(d.get("keywords",[]))
    kw_count = Counter(all_keywords).most_common(30)
    if kw_count:
        kw_df = pd.DataFrame(kw_count, columns=["Palavra","Frequência"])
        fig = px.bar(kw_df, x="Palavra", y="Frequência",
                     color="Frequência", color_continuous_scale="Blues")
        fig.update_layout(height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#94a3c0"), coloraxis_showscale=False,
                         xaxis=dict(tickangle=-45))
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Clarity vs size scatter
    if len(docs) > 2:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Clareza vs. Tamanho dos documentos</div>", unsafe_allow_html=True)
        scatter_df = df[df["clarity"] > 0].copy()
        if not scatter_df.empty:
            fig = px.scatter(scatter_df, x="words", y="clarity", color="topic",
                             hover_name="name", size="size_kb",
                             labels={"words":"Palavras","clarity":"Clareza (0-100)","topic":"Tema"},
                             color_discrete_sequence=["#60a5fa","#4ade80","#c084fc","#f97316","#67e8f9","#f87171"])
            fig.update_layout(height=360, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                             font=dict(color="#94a3c0"),
                             legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3c0")))
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Nationality map
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Mapa de origem dos documentos</div>", unsafe_allow_html=True)
    nat_count = df["nationality"].value_counts().reset_index()
    nat_count.columns = ["Nacionalidade","Quantidade"]
    map_rows = []
    for _, row in nat_count.iterrows():
        coords = NATIONALITY_COORDS.get(row["Nacionalidade"])
        if coords:
            map_rows.append({"country": row["Nacionalidade"], "count": row["Quantidade"],
                           "lat": coords["lat"], "lon": coords["lon"]})
    if map_rows:
        map_df = pd.DataFrame(map_rows)
        fig = go.Figure(data=[go.Scattergeo(
            lon=map_df["lon"], lat=map_df["lat"],
            text=map_df["country"] + ": " + map_df["count"].astype(str),
            mode="markers",
            marker=dict(size=map_df["count"]*8+6, opacity=0.85,
                       color=map_df["count"], colorscale="Blues",
                       showscale=True, colorbar=dict(title="Docs")),
        )])
        fig.update_layout(height=440, paper_bgcolor="rgba(0,0,0,0)",
                         geo=dict(bgcolor="rgba(0,0,0,0)", showland=True,
                                  landcolor="rgba(255,255,255,0.06)",
                                  showcountries=True, countrycolor="rgba(255,255,255,0.14)",
                                  showocean=True, oceancolor="rgba(96,165,250,0.04)",
                                  projection_type="natural earth"))
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Summary text
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Resumo analítico automático</div>", unsafe_allow_html=True)
    dominant_topics = ", ".join(df["topic"].value_counts().head(3).index.tolist())
    dominant_authors = ", ".join(df[df["author"]!="Desconhecido"]["author"].value_counts().head(3).index.tolist()) or "não identificados"
    years_range = f"{int(df['year'].min())} a {int(df['year'].max())}" if not df["year"].isna().all() else "não identificado"
    avg_words = int(df["words"].mean()) if df["words"].any() else 0
    
    st.markdown(f"""
    O repositório contém **{len(docs)} documentos** com um total estimado de **{total_words:,} palavras**.
    Os temas predominantes são **{dominant_topics}**. Os autores mais recorrentes são **{dominant_authors}**.
    O intervalo temporal identificado vai de **{years_range}**. A média de palavras por documento é de
    **{avg_words:,}**, com índice médio de clareza de **{avg_clarity}/100**.
    O sistema identificou **{df['language'].value_counts().index[0] if not df['language'].empty else 'N/A'}** como idioma dominante.
    """)
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# CONNECTIONS PAGE — 3D NETWORK
# ============================================================
def page_connections():
    st.markdown("<div class='page-title'>Conexões entre Pesquisas</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>Rede 3D de correlações reais entre seus documentos, artigos externos e sua linha de pesquisa</div>", unsafe_allow_html=True)
    
    user = current_user()
    docs = st.session_state.repository
    research = user.get("research","")
    
    # Controls
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
    with col_ctrl1:
        min_sim = st.slider("Limite mínimo de similaridade", 0.01, 0.30, 0.06, 0.01,
                            help="Conexões com similaridade abaixo deste valor são ocultadas")
    with col_ctrl2:
        include_external = st.checkbox("Incluir artigos externos correlatos", value=True)
    with col_ctrl3:
        n_external = st.slider("Número de artigos externos", 3, 15, 8)
    
    external_articles = []
    if include_external and research:
        cache_key = f"conn_articles_{hashlib.md5(research.encode()).hexdigest()[:8]}_{n_external}"
        external_articles = st.session_state.get(cache_key)
        if external_articles is None:
            with st.spinner("Buscando artigos correlatos..."):
                terms = extract_keywords_tfidf(research, 6)
                query = " ".join(terms[:5]) if terms else research
                external_articles = search_semantic_scholar(query, limit=n_external)
                if len(external_articles) < 4:
                    external_articles += search_crossref(query, limit=4)
            st.session_state[cache_key] = external_articles
    
    total_nodes = len(docs) + len(external_articles) + (1 if research else 0)
    
    if total_nodes < 2:
        st.info("Adicione documentos no Repositório e configure sua pesquisa no Perfil para gerar a rede de conexões.")
        return
    
    # Build network
    nodes, edges = build_research_network(docs, external_articles, research)
    
    # Filter by min similarity
    filtered_edges = [e for e in edges if e["weight"] >= min_sim]
    
    # Stats
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class='metric-card blue'>
            <div class='metric-label'>Nós totais</div>
            <div class='metric-value'>{len(nodes)}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class='metric-card green'>
            <div class='metric-label'>Conexões ativas</div>
            <div class='metric-value'>{len(filtered_edges)}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        avg_w = round(sum(e["weight"] for e in filtered_edges)/max(len(filtered_edges),1)*100, 1)
        st.markdown(f"""<div class='metric-card cyan'>
            <div class='metric-label'>Força média</div>
            <div class='metric-value'>{avg_w}%</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        same_topic = sum(1 for e in filtered_edges if e["same_topic"])
        st.markdown(f"""<div class='metric-card purple'>
            <div class='metric-label'>Mesmo tema</div>
            <div class='metric-value'>{same_topic}</div>
        </div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Legend
    st.markdown("""
    <div class='glass-sm' style='display:flex;gap:1.5rem;flex-wrap:wrap;margin-bottom:1rem;align-items:center'>
        <span style='font-size:0.82rem;color:#94a3c0'>Legenda:</span>
        <span style='font-size:0.82rem'><span style='color:#facc15'>●</span> Sua pesquisa</span>
        <span style='font-size:0.82rem'><span style='color:#60a5fa'>●</span> Seus documentos</span>
        <span style='font-size:0.82rem'><span style='color:#4ade80'>●</span> Artigos externos</span>
        <span style='font-size:0.82rem'><span style='color:#60a5fa;opacity:0.6'>— Mesma área temática  </span></span>
        <span style='font-size:0.82rem'><span style='color:#94a3c0'>— Correlação geral</span></span>
    </div>
    """, unsafe_allow_html=True)
    
    # 3D Network
    fig_3d = render_3d_network(nodes, filtered_edges)
    if fig_3d:
        st.plotly_chart(fig_3d, use_container_width=True)
    else:
        st.info("Não há conexões suficientes para exibir a rede. Tente reduzir o limite mínimo de similaridade.")
    
    # Connection table
    if filtered_edges:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Conexões mais fortes</div>", unsafe_allow_html=True)
        edge_data = []
        for edge in sorted(filtered_edges, key=lambda x: -x["weight"])[:20]:
            i, j = edge["source"], edge["target"]
            if i < len(nodes) and j < len(nodes):
                edge_data.append({
                    "Documento A": nodes[i]["label"],
                    "Documento B": nodes[j]["label"],
                    "Similaridade": f"{edge['weight']*100:.1f}%",
                    "Mesmo tema": "Sim" if edge["same_topic"] else "Não",
                    "Tema": nodes[i]["topic"],
                })
        if edge_data:
            st.dataframe(pd.DataFrame(edge_data), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Most connected nodes
    if nodes:
        node_degree = defaultdict(int)
        for edge in filtered_edges:
            node_degree[edge["source"]] += 1
            node_degree[edge["target"]] += 1
        
        if node_degree:
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Nós mais conectados (hubs de conhecimento)</div>", unsafe_allow_html=True)
            top_nodes = sorted(node_degree.items(), key=lambda x: -x[1])[:10]
            hub_data = []
            for idx, degree in top_nodes:
                if idx < len(nodes):
                    hub_data.append({
                        "Documento/Artigo": nodes[idx]["label"],
                        "Tipo": nodes[idx]["type"],
                        "Tema": nodes[idx]["topic"],
                        "Conexões": degree,
                    })
            if hub_data:
                st.dataframe(pd.DataFrame(hub_data), use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# PROFILE
# ============================================================
def page_profile():
    user = current_user()
    st.markdown("<div class='page-title'>Perfil</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>Configure sua área de pesquisa e veja suas preferências aprendidas</div>", unsafe_allow_html=True)
    
    col_l, col_r = st.columns(2)
    
    with col_l:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Dados do perfil</div>", unsafe_allow_html=True)
        new_name = st.text_input("Nome", value=user.get("name",""))
        new_research = st.text_area("Área de pesquisa", value=user.get("research",""),
                                    height=100, placeholder="Descreva sua linha de pesquisa principal...")
        
        if st.button("Salvar perfil", use_container_width=True, type="primary"):
            st.session_state.users[st.session_state.current_user].update({
                "name": new_name,
                "research": new_research,
            })
            save_db()
            # Clear cached articles when research changes
            for key in list(st.session_state.keys()):
                if key.startswith("dashboard_articles_") or key.startswith("conn_articles_"):
                    del st.session_state[key]
            st.success("Perfil atualizado.")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col_r:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Preferências aprendidas</div>", unsafe_allow_html=True)
        interests = recommend_terms(st.session_state.current_user, 25)
        if interests:
            st.markdown("".join([f"<span class='tag'>{t}</span>" for t in interests]), unsafe_allow_html=True)
        else:
            st.info("Faça buscas e envie documentos para construir seu perfil.")
        
        if interests and st.button("Limpar preferências", use_container_width=True):
            st.session_state.user_interest[st.session_state.current_user] = {}
            save_db()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Histórico de buscas</div>", unsafe_allow_html=True)
        history = st.session_state.search_history
        if history:
            recent = history[-10:][::-1]
            hist_df = pd.DataFrame(recent)[["query","time","topic","intent"]]
            hist_df.columns = ["Consulta","Data","Tema","Intenção"]
            st.dataframe(hist_df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma busca registrada.")
        st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# MAIN
# ============================================================
def main():
    if not st.session_state.logged_in:
        page_auth()
        return
    
    render_navbar()
    
    page = st.session_state.page
    if page == "Dashboard":
        page_dashboard()
    elif page == "Pesquisa Inteligente":
        page_smart_search()
    elif page == "Repositório":
        page_repository()
    elif page == "Análise Avançada":
        page_analysis()
    elif page == "Conexões":
        page_connections()
    elif page == "Perfil":
        page_profile()

if __name__ == "__main__":
    main()
