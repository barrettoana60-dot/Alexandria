import os
import re
import io
import json
import math
import hashlib
import base64
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
from difflib import SequenceMatcher

import streamlit as st

# =============================
# Optional dependencies
# =============================
try:
    import requests
except Exception:
    requests = None

try:
    import numpy as np
except Exception:
    np = None

try:
    import pandas as pd
except Exception:
    pd = None

try:
    from PIL import Image, ImageOps
except Exception:
    Image = None
    ImageOps = None

try:
    import plotly.graph_objects as go
    import plotly.express as px
except Exception:
    go = None
    px = None

try:
    import PyPDF2
except Exception:
    PyPDF2 = None

try:
    import openpyxl
except Exception:
    openpyxl = None

try:
    from docx import Document
except Exception:
    Document = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:
    TfidfVectorizer = None
    cosine_similarity = None

try:
    import networkx as nx
except Exception:
    nx = None

# =============================
# App config
# =============================
APP_NAME = "Nebula"
APP_TAGLINE = "Pesquisa acadêmica, repositório inteligente e análise conectada"
DATA_DIR = Path("nebula_data")
USERS_FILE = DATA_DIR / "users.json"
REPOS_FILE = DATA_DIR / "repositories.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
FILES_DIR = DATA_DIR / "files"
DATA_DIR.mkdir(exist_ok=True)
FILES_DIR.mkdir(exist_ok=True)

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================
# Dictionaries and metadata
# =============================
STOPWORDS = {
    "de","da","do","das","dos","a","o","as","os","e","em","para","por","com","um","uma","uns","umas",
    "ao","aos","na","no","nas","nos","que","se","como","mais","menos","entre","sobre","sem","ser","são",
    "the","of","and","or","in","to","for","by","with","on","at","from","an","is","are","be","this","that",
    "paper","study","research","article","using","used","analysis","results","method","methods","data",
    "uma","esse","essa","esses","essas","também","ainda","entre","cada","foram","sendo","após"
}

TOPIC_LEXICON = {
    "Museologia": ["museologia","museu","acervo","coleção","documentação museológica","patrimônio","curadoria","folksonomia","catalogação","exposição"],
    "Ciência da Informação": ["metadados","indexação","ontologia","repositório","recuperação da informação","descrição","classificação","taxonomia","folksonomia"],
    "Inteligência Artificial": ["inteligência artificial","machine learning","deep learning","rede neural","llm","modelo de linguagem","aprendizado de máquina","visão computacional"],
    "Preservação Digital": ["preservação digital","arquivo digital","acesso aberto","interoperabilidade","digitalização","dados digitais"],
    "Humanidades Digitais": ["humanidades digitais","humanidades","acervos digitais","digital humanities"],
    "Biologia": ["célula","genômica","gene","proteína","rna","dna","microscopia","organismo","tecido"],
    "Medicina": ["clínico","paciente","diagnóstico","tratamento","hospital","terapia","doença"],
    "Computação": ["algoritmo","software","banco de dados","streamlit","python","api","deploy","sistema"],
    "Educação": ["educação","aprendizagem","ensino","didática","currículo","escola","universidade"],
    "Psicologia": ["cognitivo","psicologia","comportamento","percepção","emoção","memória"],
}

METHOD_LEXICON = {
    "Revisão": ["revisão","estado da arte","systematic review","scoping review","revisão bibliográfica"],
    "Qualitativa": ["entrevista","grupo focal","observação","análise temática","qualitativa","etnográfica"],
    "Quantitativa": ["quantitativa","estatística","survey","questionário","regressão","amostra","variável"],
    "Computacional": ["algoritmo","pipeline","modelo","rede neural","simulação","script","python","streamlit"],
    "Experimental": ["experimental","ensaio","laboratório","coleta","medição","teste","protocolo"],
    "Estudo de Caso": ["estudo de caso","case study","instituição","museu específico"],
}

COUNTRIES = {
    "Brasil": {"aliases": ["brasil","brazil","brasileiro","brasileira","rio de janeiro","são paulo","unirio","usp","ufrj","ufmg","unicamp","fiocruz"], "lat": -14.2350, "lon": -51.9253},
    "Estados Unidos": {"aliases": ["estados unidos","united states","usa","u.s.","mit","harvard","stanford","new york"], "lat": 39.8283, "lon": -98.5795},
    "Reino Unido": {"aliases": ["reino unido","united kingdom","uk","england","oxford","cambridge","london"], "lat": 55.3781, "lon": -3.4360},
    "Portugal": {"aliases": ["portugal","lisboa","porto","universidade lusófona"], "lat": 39.3999, "lon": -8.2245},
    "Espanha": {"aliases": ["espanha","spain","madrid","barcelona"], "lat": 40.4637, "lon": -3.7492},
    "França": {"aliases": ["frança","france","paris"], "lat": 46.2276, "lon": 2.2137},
    "Alemanha": {"aliases": ["alemanha","germany","berlin","munich"], "lat": 51.1657, "lon": 10.4515},
    "Itália": {"aliases": ["itália","italy","rome","roma","milan"], "lat": 41.8719, "lon": 12.5674},
    "Canadá": {"aliases": ["canadá","canada","toronto","montreal"], "lat": 56.1304, "lon": -106.3468},
    "Japão": {"aliases": ["japão","japan","tokyo","kyoto"], "lat": 36.2048, "lon": 138.2529},
    "China": {"aliases": ["china","beijing","shanghai"], "lat": 35.8617, "lon": 104.1954},
    "Índia": {"aliases": ["índia","india","new delhi","mumbai"], "lat": 20.5937, "lon": 78.9629},
    "Argentina": {"aliases": ["argentina","buenos aires"], "lat": -38.4161, "lon": -63.6167},
    "México": {"aliases": ["méxico","mexico","cdmx","ciudad de méxico"], "lat": 23.6345, "lon": -102.5528},
    "Chile": {"aliases": ["chile","santiago"], "lat": -35.6751, "lon": -71.5430},
    "Colômbia": {"aliases": ["colômbia","colombia","bogotá"], "lat": 4.5709, "lon": -74.2973},
}

DEMO_USERS = {
    "demo@nebula.ai": {
        "name": "Usuário Demo",
        "password": hashlib.sha256("demo123".encode()).hexdigest(),
        "area": "Museologia e Inteligência Artificial",
        "bio": "Conta de demonstração do Nebula.",
        "saved_articles": [],
        "search_history": [],
        "interest_profile": {}
    }
}

NAV_ITEMS = [
    ("workspace", "Visão Geral"),
    ("search", "Pesquisa Inteligente"),
    ("repository", "Repositório"),
    ("analytics", "Análises"),
    ("connections", "Conexões"),
    ("account", "Conta"),
]

# =============================
# Utilities
# =============================
def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", (text or "").lower(), flags=re.UNICODE).strip()
    text = re.sub(r"[-\s]+", "-", text)
    return text or "item"


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "")


def safe_json_load(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_repo_dir(repo_slug: str) -> Path:
    p = FILES_DIR / repo_slug
    p.mkdir(parents=True, exist_ok=True)
    return p


def initials(name: str) -> str:
    parts = [p for p in (name or "?").split() if p.strip()]
    return "".join(p[0].upper() for p in parts[:2]) or "U"


def tokenize(text: str):
    text = strip_html((text or "").lower())
    text = re.sub(r"[^\w\sáàâãéêíóôõúçü-]", " ", text, flags=re.UNICODE)
    return [t for t in text.split() if len(t) > 2 and t not in STOPWORDS]


def keyword_scores(text: str, limit: int = 18):
    counts = Counter(tokenize(text))
    return counts.most_common(limit)


def extract_keywords(text: str, limit: int = 18):
    return [k for k, _ in keyword_scores(text, limit)]


def split_sentences(text: str):
    text = normalize_spaces(text)
    if not text:
        return []
    return re.split(r"(?<=[\.!?])\s+", text)


def similarity_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


def to_download_bytes(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")

# =============================
# State management
# =============================
def load_state():
    users = safe_json_load(USERS_FILE, {})
    repos = safe_json_load(REPOS_FILE, {})
    settings = safe_json_load(SETTINGS_FILE, {})
    if not isinstance(users, dict):
        users = {}
    if not isinstance(repos, dict):
        repos = {}
    if not isinstance(settings, dict):
        settings = {}
    return users, repos, settings


def save_state():
    save_json(USERS_FILE, st.session_state.users)
    save_json(REPOS_FILE, st.session_state.repositories)
    save_json(SETTINGS_FILE, st.session_state.settings)


def init_state():
    users_disk, repos_disk, settings_disk = load_state()
    st.session_state.setdefault("users", {**DEMO_USERS, **users_disk})
    st.session_state.setdefault("repositories", repos_disk)
    st.session_state.setdefault("settings", settings_disk)
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("current_user", None)
    st.session_state.setdefault("page", "workspace")
    st.session_state.setdefault("search_results", None)
    st.session_state.setdefault("local_matches", [])
    st.session_state.setdefault("external_matches", [])
    st.session_state.setdefault("external_images", [])
    st.session_state.setdefault("image_matches", [])
    st.session_state.setdefault("analysis_cache", None)
    st.session_state.setdefault("connections_cache", None)
    st.session_state.setdefault("last_uploaded_image_name", "")


def current_user_data():
    email = st.session_state.get("current_user")
    return st.session_state.users.get(email, {})


def update_user_interest(query: str, keywords=None, topics=None):
    email = st.session_state.get("current_user")
    if not email or email not in st.session_state.users:
        return
    u = st.session_state.users[email]
    profile = u.setdefault("interest_profile", {})
    for item in (keywords or [])[:10]:
        profile[item.lower()] = round(profile.get(item.lower(), 0) + 1.0, 2)
    for item in (topics or [])[:6]:
        profile[item.lower()] = round(profile.get(item.lower(), 0) + 1.5, 2)
    hist = u.setdefault("search_history", [])
    if query.strip():
        hist.insert(0, {"query": query.strip(), "date": now_str()})
        u["search_history"] = hist[:40]
    save_state()

# =============================
# UI helpers
# =============================
def microscope_logo_svg(size: int = 26) -> str:
    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="nebulaMic" x1="8" y1="8" x2="56" y2="56" gradientUnits="userSpaceOnUse">
          <stop stop-color="#89C9FF"/>
          <stop offset="1" stop-color="#CDB7FF"/>
        </linearGradient>
      </defs>
      <path d="M19 48H47" stroke="url(#nebulaMic)" stroke-width="4" stroke-linecap="round"/>
      <path d="M27 48C27 42 31 38 38 36" stroke="url(#nebulaMic)" stroke-width="4" stroke-linecap="round"/>
      <path d="M33 18L42 27" stroke="url(#nebulaMic)" stroke-width="6" stroke-linecap="round"/>
      <path d="M26 12L36 22" stroke="url(#nebulaMic)" stroke-width="6" stroke-linecap="round"/>
      <path d="M24 14C21 17 21 22 24 25L31 32" stroke="url(#nebulaMic)" stroke-width="4" stroke-linecap="round"/>
      <path d="M34 32L44 22C47 19 47 14 44 11" stroke="url(#nebulaMic)" stroke-width="4" stroke-linecap="round"/>
      <circle cx="45" cy="41" r="6" stroke="url(#nebulaMic)" stroke-width="4"/>
      <path d="M20 54H52" stroke="url(#nebulaMic)" stroke-width="4" stroke-linecap="round"/>
    </svg>
    """


def inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@500;700;800&family=Inter:wght@400;500;600;700&display=swap');

        :root {
          --bg:#040812;
          --panel:rgba(12,19,34,.68);
          --panel-2:rgba(18,29,50,.74);
          --line:rgba(255,255,255,.10);
          --line-2:rgba(255,255,255,.06);
          --txt:#EAF2FF;
          --muted:#99A8C7;
          --soft:#7482A1;
          --blue:#8BC8FF;
          --purple:#CBB6FF;
          --pink:#F5B2E6;
          --shadow:0 14px 44px rgba(0,0,0,.38);
          --radius:22px;
          --radius-sm:14px;
        }

        html, body, .stApp {
          background:
            radial-gradient(circle at 0% 0%, rgba(139,200,255,.10), transparent 35%),
            radial-gradient(circle at 100% 10%, rgba(203,182,255,.12), transparent 32%),
            linear-gradient(180deg, #03070f 0%, #071225 55%, #08182f 100%) !important;
          color: var(--txt) !important;
          font-family: 'Inter', sans-serif !important;
        }

        header, #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="collapsedControl"] {
          display:none !important;
        }

        .block-container {
          padding-top: .7rem !important;
          padding-bottom: 2.2rem !important;
          max-width: 1520px !important;
        }

        section[data-testid="stSidebar"] {
          width: 255px !important;
          min-width: 255px !important;
          max-width: 255px !important;
          border-right: 1px solid rgba(255,255,255,.08) !important;
          background: rgba(6,10,19,.78) !important;
          backdrop-filter: blur(24px) saturate(160%) !important;
          -webkit-backdrop-filter: blur(24px) saturate(160%) !important;
          box-shadow: 8px 0 32px rgba(0,0,0,.34) !important;
        }

        section[data-testid="stSidebar"] > div {
          width: 255px !important;
          padding-top: .8rem !important;
        }

        [data-testid="stSidebarCollapseButton"] {
          display:none !important;
        }

        .nebula-side-brand {
          display:flex;
          align-items:center;
          gap:12px;
          margin: .4rem .1rem 1.1rem .1rem;
          padding: .2rem .35rem;
        }

        .nebula-side-logo {
          width:42px;
          height:42px;
          border-radius:14px;
          display:flex;
          align-items:center;
          justify-content:center;
          background: linear-gradient(135deg, rgba(139,200,255,.14), rgba(203,182,255,.16));
          border:1px solid rgba(255,255,255,.12);
          box-shadow: inset 0 1px 0 rgba(255,255,255,.10), 0 8px 20px rgba(0,0,0,.24);
        }

        .nebula-side-name {
          font-family:'Syne', sans-serif;
          font-size:1.14rem;
          font-weight:800;
          letter-spacing:-.03em;
          color:#EAF2FF;
          line-height:1;
        }

        .nebula-side-sub {
          font-size:.70rem;
          color:#91A2C7;
          margin-top:2px;
        }

        .section-label {
          font-size:.64rem;
          color:#7F90B5;
          letter-spacing:.14em;
          text-transform:uppercase;
          font-weight:700;
          margin: .7rem .25rem .35rem .25rem;
        }

        section[data-testid="stSidebar"] .stButton > button,
        .stButton > button {
          border-radius: 16px !important;
          border: 1px solid rgba(255,255,255,.10) !important;
          background: linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,.04)) !important;
          backdrop-filter: blur(18px) saturate(160%) !important;
          -webkit-backdrop-filter: blur(18px) saturate(160%) !important;
          color: #DCE7FF !important;
          box-shadow: inset 0 1px 0 rgba(255,255,255,.11), 0 10px 24px rgba(0,0,0,.20) !important;
          transition: .18s ease all !important;
          font-weight: 600 !important;
          min-height: 44px !important;
        }

        section[data-testid="stSidebar"] .stButton > button:hover,
        .stButton > button:hover {
          transform: translateY(-1px);
          border-color: rgba(139,200,255,.28) !important;
          background: linear-gradient(180deg, rgba(139,200,255,.14), rgba(203,182,255,.08)) !important;
        }

        .glass-card {
          background: linear-gradient(180deg, rgba(18,29,50,.72), rgba(11,19,36,.62));
          border:1px solid rgba(255,255,255,.10);
          border-radius:22px;
          box-shadow: var(--shadow);
          backdrop-filter: blur(20px) saturate(170%);
          -webkit-backdrop-filter: blur(20px) saturate(170%);
          position:relative;
          overflow:hidden;
        }

        .glass-card::before {
          content:"";
          position:absolute;
          top:0; left:0; right:0;
          height:1px;
          background: linear-gradient(90deg, transparent, rgba(255,255,255,.20), transparent);
        }

        .page-head {
          display:flex;
          align-items:flex-start;
          justify-content:space-between;
          gap:18px;
          margin-bottom: 1rem;
        }

        .page-title {
          font-family:'Syne', sans-serif;
          font-size:2.05rem;
          line-height:1;
          font-weight:800;
          letter-spacing:-.04em;
          color:#F4F7FF;
          margin:0;
        }

        .page-sub {
          color:#93A4C6;
          margin-top:.34rem;
          font-size:.95rem;
        }

        .metric-card {
          padding: 1.05rem 1.1rem;
          min-height: 120px;
        }

        .metric-label {
          font-size:.68rem;
          letter-spacing:.13em;
          text-transform:uppercase;
          color:#8EA0C5;
          font-weight:700;
        }

        .metric-value {
          font-family:'Syne', sans-serif;
          font-size:2rem;
          line-height:1;
          font-weight:800;
          margin-top:1rem;
          color:#EAF2FF;
        }

        .metric-foot {
          color:#8291B3;
          font-size:.82rem;
          margin-top:.55rem;
        }

        .chip {
          display:inline-flex;
          align-items:center;
          gap:6px;
          padding: 5px 10px;
          border-radius:999px;
          border:1px solid rgba(255,255,255,.10);
          background: rgba(255,255,255,.05);
          color:#D7E2FB;
          font-size:.76rem;
          margin: 0 6px 6px 0;
        }

        .mini-title {
          font-family:'Syne', sans-serif;
          font-size:1rem;
          font-weight:700;
          color:#F2F6FF;
          margin-bottom:.65rem;
        }

        .repo-item,
        .result-item,
        .connection-item {
          padding: 1rem 1rem;
          border-radius: 18px;
          border:1px solid rgba(255,255,255,.08);
          background: rgba(255,255,255,.04);
          margin-bottom: .6rem;
        }

        .repo-item:hover,
        .result-item:hover,
        .connection-item:hover {
          border-color: rgba(139,200,255,.24);
          background: rgba(255,255,255,.055);
        }

        .tiny {
          color:#8FA0C4;
          font-size:.78rem;
        }

        .search-panel {
          padding: 1.1rem 1.1rem 1rem 1.1rem;
          margin-bottom: .9rem;
        }

        .auth-shell {
          max-width: 980px;
          margin: 2rem auto 0 auto;
        }

        .auth-card {
          padding: 1.3rem;
        }

        .auth-brand {
          display:flex;
          align-items:center;
          gap:16px;
          margin-bottom:1rem;
        }

        .auth-title {
          font-family:'Syne', sans-serif;
          font-size:2rem;
          font-weight:800;
          letter-spacing:-.05em;
          color:#F2F7FF;
        }

        .auth-sub {
          color:#90A2C8;
          margin-top:.22rem;
        }

        .account-name {
          font-weight:700;
          color:#EEF4FF;
          margin-bottom:2px;
        }

        .stTextInput > div > div > input,
        .stTextArea textarea,
        .stSelectbox > div > div,
        .stFileUploader section,
        .stMultiSelect > div > div {
          border-radius: 16px !important;
          background: rgba(255,255,255,.05) !important;
          border:1px solid rgba(255,255,255,.10) !important;
          color:#EAF2FF !important;
        }

        .stTextInput label,
        .stTextArea label,
        .stSelectbox label,
        .stFileUploader label,
        .stMultiSelect label,
        .stCheckbox label {
          color:#9DB0D7 !important;
        }

        .stTabs [data-baseweb="tab-list"] {
          background: rgba(255,255,255,.04);
          border:1px solid rgba(255,255,255,.08);
          border-radius: 16px;
          padding:4px;
          gap:4px;
        }

        .stTabs [data-baseweb="tab"] {
          color:#93A4C9;
          border-radius: 12px;
          font-weight:600;
        }

        .stTabs [aria-selected="true"] {
          background: linear-gradient(180deg, rgba(139,200,255,.16), rgba(203,182,255,.10)) !important;
          color:#F1F6FF !important;
        }

        hr {
          border:none;
          border-top:1px solid rgba(255,255,255,.08);
          margin:.75rem 0 1rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def glass_open(extra_style: str = ""):
    st.markdown(f'<div class="glass-card" style="{extra_style}">', unsafe_allow_html=True)


def glass_close():
    st.markdown('</div>', unsafe_allow_html=True)


def page_header(title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="page-head">
          <div>
            <div class="page-title">{title}</div>
            <div class="page-sub">{subtitle}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_brand():
    st.markdown(
        f"""
        <div class="nebula-side-brand">
          <div class="nebula-side-logo">{microscope_logo_svg(24)}</div>
          <div>
            <div class="nebula-side-name">Nebula</div>
            <div class="nebula-side-sub">laboratório de pesquisa</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    with st.sidebar:
        sidebar_brand()
        user = current_user_data()
        st.markdown('<div class="section-label">Navegação</div>', unsafe_allow_html=True)
        for key, label in NAV_ITEMS:
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.page = key
                st.rerun()
        st.markdown('<div class="section-label">Conta</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="repo-item" style="padding:.8rem .9rem; margin-bottom:.8rem;">
              <div class="account-name">{user.get('name','Usuário')}</div>
              <div class="tiny">{user.get('area','Sem área definida')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Sair do sistema", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.session_state.page = "workspace"
            st.rerun()

# =============================
# File extraction and analysis
# =============================
def file_type(name: str) -> str:
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    mapping = {
        "pdf": "PDF",
        "txt": "Texto",
        "md": "Markdown",
        "docx": "Word",
        "csv": "CSV",
        "xlsx": "Planilha",
        "xls": "Planilha",
        "png": "Imagem",
        "jpg": "Imagem",
        "jpeg": "Imagem",
        "webp": "Imagem",
        "bmp": "Imagem",
        "gif": "Imagem",
        "py": "Código",
        "json": "JSON",
    }
    return mapping.get(ext, "Arquivo")


def read_pdf_bytes(raw: bytes) -> str:
    if PyPDF2 is None:
        return ""
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(raw))
        texts = []
        for page in reader.pages[:40]:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                pass
        return "\n".join(texts)
    except Exception:
        return ""


def read_docx_bytes(raw: bytes) -> str:
    if Document is None:
        return ""
    try:
        doc = Document(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        return ""


def read_csv_bytes(raw: bytes) -> str:
    if pd is None:
        return raw.decode("utf-8", errors="ignore")
    try:
        df = pd.read_csv(io.BytesIO(raw))
        return df.astype(str).head(500).to_csv(index=False)
    except Exception:
        try:
            df = pd.read_csv(io.BytesIO(raw), sep=";")
            return df.astype(str).head(500).to_csv(index=False)
        except Exception:
            return raw.decode("utf-8", errors="ignore")


def read_xlsx_bytes(raw: bytes) -> str:
    if pd is None:
        return ""
    try:
        xl = pd.ExcelFile(io.BytesIO(raw))
        parts = []
        for sheet in xl.sheet_names[:5]:
            df = xl.parse(sheet).astype(str).head(300)
            parts.append(f"Planilha: {sheet}\n{df.to_csv(index=False)}")
        return "\n\n".join(parts)
    except Exception:
        return ""


def read_textual_bytes(name: str, raw: bytes) -> str:
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext == "pdf":
        return read_pdf_bytes(raw)
    if ext == "docx":
        return read_docx_bytes(raw)
    if ext in {"csv"}:
        return read_csv_bytes(raw)
    if ext in {"xlsx", "xls"}:
        return read_xlsx_bytes(raw)
    if ext in {"txt", "md", "py", "json"}:
        return raw.decode("utf-8", errors="ignore")
    return raw.decode("utf-8", errors="ignore")


def summarize_text(text: str, max_sentences: int = 3) -> str:
    if not text:
        return ""
    text = normalize_spaces(strip_html(text))
    m = re.search(r"\b(resumo|abstract)\b[:\s-]*(.{80,900})", text, flags=re.I)
    if m:
        candidate = m.group(2)
        sents = split_sentences(candidate)
        if sents:
            return " ".join(sents[:max_sentences])[:900]
    sents = split_sentences(text)
    if not sents:
        return text[:420]
    return " ".join(sents[:max_sentences])[:900]


def detect_topics(text: str):
    text_l = (text or "").lower()
    scores = []
    for topic, terms in TOPIC_LEXICON.items():
        score = sum(2 if t in text_l else 0 for t in terms)
        score += sum(1 for kw in extract_keywords(text, 18) if any(t in kw for t in terms))
        if score > 0:
            scores.append((topic, score))
    scores.sort(key=lambda x: x[1], reverse=True)
    return [t for t, _ in scores[:5]]


def detect_method(text: str) -> str:
    text_l = (text or "").lower()
    best = ("Indefinido", 0)
    for method, terms in METHOD_LEXICON.items():
        score = sum(1 for t in terms if t in text_l)
        if score > best[1]:
            best = (method, score)
    return best[0]


def guess_title(name: str, text: str) -> str:
    lines = [normalize_spaces(l) for l in (text or "").splitlines() if normalize_spaces(l)]
    for line in lines[:8]:
        if 12 <= len(line) <= 180 and not re.search(r"^(resumo|abstract|palavras-chave|keywords)\b", line, flags=re.I):
            return line
    return Path(name).stem.replace("_", " ").replace("-", " ").strip().title()


def guess_year(text: str) -> int | None:
    years = re.findall(r"\b(19\d{2}|20\d{2})\b", text or "")
    if not years:
        return None
    counts = Counter(int(y) for y in years if 1900 <= int(y) <= 2100)
    if not counts:
        return None
    return counts.most_common(1)[0][0]


def guess_authors(text: str):
    text = normalize_spaces(strip_html(text or ""))
    patterns = [
        r"(?:autores?|authors?)\s*[:\-]\s*([^\.\n]{5,220})",
        r"(?:por|by)\s+([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][^\.\n]{5,180})",
    ]
    candidates = []
    for pat in patterns:
        m = re.search(pat, text, flags=re.I)
        if m:
            chunk = m.group(1)
            pieces = re.split(r",|;| and | e ", chunk)
            for p in pieces:
                p = normalize_spaces(p)
                if 4 <= len(p) <= 60 and re.search(r"[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ]", p):
                    candidates.append(p)
    if candidates:
        return list(dict.fromkeys(candidates))[:6]
    proper = re.findall(r"\b[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+\b", text)
    proper = [p for p in proper if len(p.split()) == 2]
    return list(dict.fromkeys(proper))[:5]


def detect_countries(text: str):
    text_l = (text or "").lower()
    found = []
    for country, meta in COUNTRIES.items():
        if any(alias in text_l for alias in meta["aliases"]):
            found.append(country)
    return found


def analyze_document(name: str, text: str, source: str = "local", url: str = ""):
    clean = normalize_spaces(strip_html(text or ""))
    kws = extract_keywords(clean, 18)
    title = guess_title(name, clean)
    summary = summarize_text(clean, 3)
    topics = detect_topics(clean)
    method = detect_method(clean)
    year = guess_year(clean)
    authors = guess_authors(clean)
    countries = detect_countries(clean)
    return {
        "name": name,
        "title": title,
        "summary": summary,
        "keywords": kws,
        "topics": topics,
        "method": method,
        "year": year,
        "authors": authors,
        "countries": countries,
        "text_length": len(clean),
        "source": source,
        "url": url,
    }

# =============================
# Local repositories
# =============================
def all_local_documents():
    docs = []
    for repo_id, repo in st.session_state.repositories.items():
        repo_name = repo.get("name", repo_id)
        for file_item in repo.get("files", []):
            item = dict(file_item)
            item["repo_id"] = repo_id
            item["repo_name"] = repo_name
            docs.append(item)
    return docs


def analyzed_local_documents():
    docs = []
    for item in all_local_documents():
        ana = item.get("analysis") or {}
        if ana:
            row = dict(item)
            row.update(ana)
            docs.append(row)
    return docs


def store_uploaded_file(repo_id: str, uploaded_file):
    repo_dir = ensure_repo_dir(repo_id)
    raw = uploaded_file.getvalue()
    digest = hashlib.sha1(raw).hexdigest()
    fname = uploaded_file.name
    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else "bin"
    saved_name = f"{digest[:12]}_{slugify(Path(fname).stem)}.{ext}"
    dest = repo_dir / saved_name
    dest.write_bytes(raw)

    extracted_text = ""
    analysis = {}
    if file_type(fname) != "Imagem":
        extracted_text = read_textual_bytes(fname, raw)
        analysis = analyze_document(fname, extracted_text, source="local") if extracted_text else {}
    else:
        analysis = {
            "name": fname,
            "title": Path(fname).stem,
            "summary": "Arquivo de imagem carregado no repositório.",
            "keywords": [],
            "topics": [],
            "method": "Indefinido",
            "year": None,
            "authors": [],
            "countries": [],
            "text_length": 0,
            "source": "local-image",
            "url": "",
        }

    item = {
        "original_name": fname,
        "stored_name": saved_name,
        "path": str(dest),
        "type": file_type(fname),
        "size": len(raw),
        "sha1": digest,
        "uploaded_at": now_str(),
        "text": extracted_text,
        "analysis": analysis,
    }
    return item

# =============================
# Search intelligence
# =============================
def infer_query_intent(query: str, user_profile: dict):
    q = (query or "").lower()
    intent = "exploratória"
    if any(t in q for t in ["comparar", "diferença", "versus", "vs"]):
        intent = "comparativa"
    elif any(t in q for t in ["metodologia", "método", "protocolo"]):
        intent = "metodológica"
    elif any(t in q for t in ["imagem", "microscopia", "figura", "foto"]):
        intent = "visual"
    elif any(t in q for t in ["artigos", "papers", "referências", "bibliografia"]):
        intent = "bibliográfica"

    base_keywords = extract_keywords(query, 8)
    interests = sorted((user_profile or {}).items(), key=lambda x: x[1], reverse=True)
    suggestions = []
    for kw in base_keywords:
        suggestions.extend([
            f"{kw} revisão sistemática",
            f"{kw} estudo de caso",
            f"{kw} metadados",
        ])
    for kw, _ in interests[:4]:
        if kw not in " ".join(base_keywords):
            suggestions.append(f"{query} {kw}")
    suggestions = list(dict.fromkeys([s for s in suggestions if len(s) < 80]))[:8]

    topics = detect_topics(query)
    return {
        "intent": intent,
        "keywords": base_keywords,
        "topics": topics,
        "suggestions": suggestions,
    }


def local_search(query: str, docs: list, top_n: int = 18):
    if not query.strip() or not docs:
        return []
    corpus = []
    for d in docs:
        ana = d.get("analysis") or {}
        content = " ".join([
            d.get("original_name", ""),
            ana.get("title", ""),
            ana.get("summary", ""),
            " ".join(ana.get("keywords", [])),
            " ".join(ana.get("topics", [])),
            d.get("text", "")[:6000],
        ])
        corpus.append(content)

    scores = []
    if TfidfVectorizer is not None and cosine_similarity is not None:
        try:
            vec = TfidfVectorizer(max_features=4000)
            mat = vec.fit_transform(corpus + [query])
            sims = cosine_similarity(mat[-1], mat[:-1]).flatten().tolist()
            scores = sims
        except Exception:
            scores = []

    if not scores:
        q_terms = set(tokenize(query))
        scores = []
        for content in corpus:
            c_terms = set(tokenize(content))
            overlap = len(q_terms & c_terms)
            score = overlap / max(len(q_terms), 1)
            scores.append(score)

    results = []
    for d, score in zip(docs, scores):
        ana = d.get("analysis") or {}
        title = (ana.get("title") or d.get("original_name", "")).lower()
        bonus = 0
        for piece in query.lower().split():
            if piece and piece in title:
                bonus += 0.08
        final = round(float(score) + bonus, 4)
        if final > 0:
            results.append({
                "score": final,
                "repo_name": d.get("repo_name", ""),
                "path": d.get("path", ""),
                "original_name": d.get("original_name", ""),
                "analysis": ana,
                "type": d.get("type", "Arquivo"),
            })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]

# =============================
# External research APIs
# =============================
def scholar_search_semantic_scholar(query: str, limit: int = 8):
    if requests is None or not query.strip():
        return []
    try:
        resp = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={
                "query": query,
                "limit": limit,
                "fields": "title,authors,year,abstract,venue,externalIds,openAccessPdf,citationCount"
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        items = []
        for paper in resp.json().get("data", []):
            authors = ", ".join(a.get("name", "") for a in (paper.get("authors") or [])[:4])
            ext = paper.get("externalIds") or {}
            doi = ext.get("DOI", "")
            arxiv = ext.get("ArXiv", "")
            pdf = paper.get("openAccessPdf") or {}
            url = pdf.get("url", "") or (f"https://doi.org/{doi}" if doi else (f"https://arxiv.org/abs/{arxiv}" if arxiv else ""))
            text = " ".join([
                paper.get("title", ""),
                authors,
                paper.get("abstract", "") or "",
                paper.get("venue", "") or "",
            ])
            analysis = analyze_document(paper.get("title", "Sem título"), text, source="semantic", url=url)
            analysis["summary"] = paper.get("abstract", "") or analysis.get("summary", "")
            analysis["year"] = paper.get("year") or analysis.get("year")
            analysis["authors"] = [a.get("name", "") for a in (paper.get("authors") or [])[:6]]
            items.append({
                "origin": "Semantic Scholar",
                "score": paper.get("citationCount", 0),
                "url": url,
                "doi": doi,
                "analysis": analysis,
            })
        return items
    except Exception:
        return []


def scholar_search_crossref(query: str, limit: int = 6):
    if requests is None or not query.strip():
        return []
    try:
        resp = requests.get(
            "https://api.crossref.org/works",
            params={
                "query": query,
                "rows": limit,
                "select": "title,author,issued,abstract,DOI,container-title,is-referenced-by-count",
                "mailto": "nebula@example.com",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        items = []
        for work in resp.json().get("message", {}).get("items", []):
            title = (work.get("title") or ["Sem título"])[0]
            authors = work.get("author") or []
            author_names = []
            for a in authors[:6]:
                joined = " ".join(p for p in [a.get("given", ""), a.get("family", "")] if p).strip()
                if joined:
                    author_names.append(joined)
            year = None
            date_parts = (work.get("issued", {}) or {}).get("date-parts") or []
            if date_parts and date_parts[0]:
                year = date_parts[0][0]
            doi = work.get("DOI", "")
            url = f"https://doi.org/{doi}" if doi else ""
            abstract = strip_html(work.get("abstract", "") or "")
            text = " ".join([title, " ".join(author_names), abstract, " ".join(work.get("container-title") or [])])
            analysis = analyze_document(title, text, source="crossref", url=url)
            analysis["summary"] = abstract or analysis.get("summary", "")
            analysis["year"] = year or analysis.get("year")
            analysis["authors"] = author_names
            items.append({
                "origin": "Crossref",
                "score": work.get("is-referenced-by-count", 0),
                "url": url,
                "doi": doi,
                "analysis": analysis,
            })
        return items
    except Exception:
        return []


def scholar_search(query: str):
    results = scholar_search_semantic_scholar(query, 8) + scholar_search_crossref(query, 6)
    dedup = {}
    for item in results:
        title = slugify(item.get("analysis", {}).get("title", "sem-titulo"))
        if title not in dedup or item.get("score", 0) > dedup[title].get("score", 0):
            dedup[title] = item
    merged = list(dedup.values())
    merged.sort(key=lambda x: (x.get("score", 0), x.get("analysis", {}).get("year") or 0), reverse=True)
    return merged[:12]

# =============================
# External image API (Wikimedia Commons)
# =============================
def commons_image_search(query: str, limit: int = 10):
    if requests is None or not query.strip():
        return []
    try:
        resp = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": query,
                "gsrnamespace": 6,
                "gsrlimit": limit,
                "prop": "imageinfo",
                "iiprop": "url",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        pages = (resp.json().get("query") or {}).get("pages") or {}
        items = []
        for _, page in pages.items():
            info = (page.get("imageinfo") or [{}])[0]
            url = info.get("url", "")
            if url:
                items.append({
                    "title": page.get("title", "Arquivo"),
                    "url": url,
                    "source": "Wikimedia Commons",
                })
        return items[:limit]
    except Exception:
        return []

# =============================
# Image similarity
# =============================
def open_image_safe(path: str):
    if Image is None:
        return None
    try:
        return Image.open(path).convert("RGB")
    except Exception:
        return None


def average_hash(img, size: int = 8):
    if Image is None or ImageOps is None:
        return None
    try:
        gray = ImageOps.grayscale(img).resize((size, size))
        if np is None:
            pixels = list(gray.getdata())
            avg = sum(pixels) / max(len(pixels), 1)
            bits = "".join("1" if p >= avg else "0" for p in pixels)
            return bits
        arr = np.array(gray)
        avg = arr.mean()
        return "".join("1" if v >= avg else "0" for v in arr.flatten())
    except Exception:
        return None


def hamming_distance(a, b):
    if not a or not b or len(a) != len(b):
        return 999
    return sum(ch1 != ch2 for ch1, ch2 in zip(a, b))


def local_image_similarity(uploaded_bytes: bytes, docs: list):
    if Image is None or not uploaded_bytes:
        return []
    try:
        ref = Image.open(io.BytesIO(uploaded_bytes)).convert("RGB")
    except Exception:
        return []
    ref_hash = average_hash(ref)
    if not ref_hash:
        return []
    matches = []
    for doc in docs:
        if doc.get("type") != "Imagem":
            continue
        img = open_image_safe(doc.get("path", ""))
        if img is None:
            continue
        img_hash = average_hash(img)
        dist = hamming_distance(ref_hash, img_hash)
        sim = max(0.0, 1 - dist / max(len(ref_hash), 1))
        if sim > 0.45:
            matches.append({
                "similarity": round(sim, 3),
                "repo_name": doc.get("repo_name", ""),
                "original_name": doc.get("original_name", ""),
                "path": doc.get("path", ""),
            })
    matches.sort(key=lambda x: x["similarity"], reverse=True)
    return matches[:12]

# =============================
# Analytics and connections
# =============================
def docs_dataframe(docs: list):
    if pd is None:
        return None
    rows = []
    for d in docs:
        rows.append({
            "Título": d.get("title", d.get("original_name", "")),
            "Ano": d.get("year") or "Não identificado",
            "Método": d.get("method") or "Indefinido",
            "Tema principal": ", ".join(d.get("topics", [])[:2]) or "Não identificado",
            "Autores": ", ".join(d.get("authors", [])[:3]) or "Não identificado",
            "Países": ", ".join(d.get("countries", [])[:3]) or "Não identificado",
            "Repositório": d.get("repo_name", ""),
            "Resumo": d.get("summary", ""),
        })
    return pd.DataFrame(rows)


def aggregate_statistics(docs: list):
    years = Counter()
    methods = Counter()
    topics = Counter()
    authors = Counter()
    countries = Counter()
    for d in docs:
        if d.get("year"):
            years[d["year"]] += 1
        methods[d.get("method") or "Indefinido"] += 1
        for t in d.get("topics", [])[:4]:
            topics[t] += 1
        for a in d.get("authors", [])[:4]:
            authors[a] += 1
        for c in d.get("countries", [])[:4]:
            countries[c] += 1
    return {
        "years": years,
        "methods": methods,
        "topics": topics,
        "authors": authors,
        "countries": countries,
    }


def pairwise_connections(docs: list):
    if not docs:
        return []
    corpus = []
    labels = []
    for d in docs:
        labels.append(d.get("title") or d.get("original_name", "Arquivo"))
        corpus.append(" ".join([
            d.get("title", ""),
            d.get("summary", ""),
            " ".join(d.get("keywords", [])),
            " ".join(d.get("topics", [])),
            " ".join(d.get("authors", [])),
        ]))

    matrix = None
    if TfidfVectorizer is not None and cosine_similarity is not None and len(corpus) >= 2:
        try:
            vec = TfidfVectorizer(max_features=4000)
            mat = vec.fit_transform(corpus)
            matrix = cosine_similarity(mat)
        except Exception:
            matrix = None

    connections = []
    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            d1 = docs[i]
            d2 = docs[j]
            score = 0.0
            if matrix is not None:
                score += float(matrix[i][j]) * 0.65
            overlap_k = set(d1.get("keywords", [])) & set(d2.get("keywords", []))
            overlap_t = set(d1.get("topics", [])) & set(d2.get("topics", []))
            overlap_a = set(d1.get("authors", [])) & set(d2.get("authors", []))
            score += min(len(overlap_k) * 0.08, 0.24)
            score += min(len(overlap_t) * 0.10, 0.20)
            score += min(len(overlap_a) * 0.06, 0.12)
            if d1.get("year") and d2.get("year") and abs(int(d1["year"]) - int(d2["year"])) <= 2:
                score += 0.05
            common_patterns = sorted(list(overlap_k | overlap_t | overlap_a))[:10]
            if score >= 0.18:
                connections.append({
                    "a": d1.get("title") or d1.get("original_name", "Arquivo A"),
                    "b": d2.get("title") or d2.get("original_name", "Arquivo B"),
                    "score": round(score, 3),
                    "patterns": common_patterns,
                    "topics": sorted(list(overlap_t)),
                })
    connections.sort(key=lambda x: x["score"], reverse=True)
    return connections


def connection_graph_figure(docs: list, connections: list):
    if go is None or not docs:
        return None
    names = [d.get("title") or d.get("original_name", "Arquivo") for d in docs]
    if nx is not None:
        G = nx.Graph()
        for name in names:
            G.add_node(name)
        for c in connections[:40]:
            G.add_edge(c["a"], c["b"], weight=c["score"])
        pos = nx.spring_layout(G, seed=14, k=1.1)
        nodes = list(G.nodes())
    else:
        nodes = names
        pos = {}
        n = max(len(nodes), 1)
        for idx, node in enumerate(nodes):
            angle = 2 * math.pi * idx / n
            pos[node] = (math.cos(angle), math.sin(angle))

    edge_x, edge_y = [], []
    for c in connections[:40]:
        if c["a"] in pos and c["b"] in pos:
            x0, y0 = pos[c["a"]]
            x1, y1 = pos[c["b"]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

    node_x = [pos[n][0] for n in nodes if n in pos]
    node_y = [pos[n][1] for n in nodes if n in pos]
    node_text = [n for n in nodes if n in pos]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(width=1, color="rgba(180,210,255,.38)"),
        hoverinfo="none",
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        text=node_text,
        textposition="top center",
        hovertext=node_text,
        marker=dict(size=18, color="#8BC8FF", line=dict(width=1, color="#EAF2FF")),
        showlegend=False,
    ))
    fig.update_layout(
        height=520,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


def countries_globe_figure(country_counter: Counter):
    if go is None or not country_counter:
        return None
    lats, lons, sizes, texts = [], [], [], []
    for country, count in country_counter.items():
        meta = COUNTRIES.get(country)
        if not meta:
            continue
        lats.append(meta["lat"])
        lons.append(meta["lon"])
        sizes.append(10 + count * 6)
        texts.append(f"{country} — {count}")
    if not lats:
        return None
    fig = go.Figure(go.Scattergeo(
        lat=lats,
        lon=lons,
        text=texts,
        mode="markers",
        marker=dict(
            size=sizes,
            color="#CBB6FF",
            line=dict(width=1, color="#FFFFFF"),
            opacity=0.86,
        ),
    ))
    fig.update_layout(
        height=540,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        geo=dict(
            projection_type="orthographic",
            showland=True,
            landcolor="rgba(80,102,140,.45)",
            showocean=True,
            oceancolor="rgba(5,14,28,.85)",
            showcountries=True,
            countrycolor="rgba(255,255,255,.18)",
            bgcolor="rgba(0,0,0,0)",
            lataxis_showgrid=True,
            lonaxis_showgrid=True,
            coastlinecolor="rgba(255,255,255,.18)",
        ),
    )
    return fig

# =============================
# Repository suggestions
# =============================
def repo_research_suggestions(repo: dict):
    docs = repo.get("files", [])
    keywords = []
    topics = []
    for item in docs:
        ana = item.get("analysis") or {}
        keywords.extend(ana.get("keywords", [])[:8])
        topics.extend(ana.get("topics", [])[:4])
    kw_counter = Counter(keywords)
    topic_counter = Counter(topics)
    base = [k for k, _ in kw_counter.most_common(5)] + [t for t, _ in topic_counter.most_common(3)]
    base = list(dict.fromkeys(base))
    suggestions = []
    for item in base:
        suggestions.extend([
            f"{item} revisão sistemática",
            f"{item} estado da arte",
            f"{item} estudo comparativo",
        ])
    return suggestions[:8]

# =============================
# Renderers
# =============================
def render_metric(label: str, value: str, foot: str):
    st.markdown(
        f"""
        <div class="glass-card metric-card">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value}</div>
          <div class="metric-foot">{foot}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_keyword_chips(items: list[str]):
    if not items:
        st.caption("Nenhum item disponível.")
        return
    html = "".join([f'<span class="chip">{x}</span>' for x in items])
    st.markdown(html, unsafe_allow_html=True)


def render_local_result(item: dict):
    ana = item.get("analysis") or {}
    st.markdown(
        f"""
        <div class="result-item">
          <div class="mini-title">{ana.get('title', item.get('original_name', 'Arquivo'))}</div>
          <div class="tiny">Repositório: {item.get('repo_name','')} · Tipo: {item.get('type','Arquivo')} · Similaridade: {item.get('score',0):.2f}</div>
          <div style="margin-top:.55rem; color:#D7E1F8;">{ana.get('summary','')}</div>
          <div style="margin-top:.6rem;">{"".join([f'<span class="chip">{k}</span>' for k in ana.get('keywords',[])[:8]])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_external_result(item: dict):
    ana = item.get("analysis") or {}
    url = item.get("url", "")
    title = ana.get("title", "Sem título")
    title_html = f'<a href="{url}" target="_blank" style="color:#F2F6FF;text-decoration:none;">{title}</a>' if url else title
    st.markdown(
        f"""
        <div class="result-item">
          <div class="mini-title">{title_html}</div>
          <div class="tiny">Fonte: {item.get('origin','')} · Ano: {ana.get('year') or 'n/d'} · DOI: {item.get('doi') or 'n/d'}</div>
          <div class="tiny" style="margin-top:.28rem;">Autores: {', '.join(ana.get('authors',[])[:4]) or 'Não identificado'}</div>
          <div style="margin-top:.55rem; color:#D7E1F8;">{ana.get('summary','')}</div>
          <div style="margin-top:.6rem;">{"".join([f'<span class="chip">{k}</span>' for k in ana.get('keywords',[])[:8]])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_repo_card(repo_id: str, repo: dict):
    files = repo.get("files", [])
    analyzed_count = sum(1 for f in files if (f.get("analysis") or {}).get("title"))
    st.markdown(
        f"""
        <div class="repo-item">
          <div class="mini-title">{repo.get('name','Repositório')}</div>
          <div class="tiny">{repo.get('description','')} · {len(files)} arquivo(s) · {analyzed_count} analisado(s)</div>
          <div style="margin-top:.55rem;">{"".join([f'<span class="chip">{t}</span>' for t in repo.get('tags',[])])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# =============================
# Pages
# =============================
def page_login():
    st.markdown('<div class="auth-shell">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="auth-brand">
          <div class="nebula-side-logo" style="width:56px;height:56px;border-radius:18px;">{microscope_logo_svg(30)}</div>
          <div>
            <div class="auth-title">Nebula</div>
            <div class="auth-sub">Ambiente redesenhado sem feed social, sem campo de instituição no cadastro e com pesquisa inteligente unificada.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    glass_open("padding:1rem 1rem 1.15rem 1rem;")
    tab_login, tab_signup = st.tabs(["Entrar", "Criar conta"])
    with tab_login:
        with st.form("form_login"):
            email = st.text_input("E-mail", placeholder="seuemail@dominio.com")
            password = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar", use_container_width=True)
            if submit:
                user = st.session_state.users.get(email)
                if not user:
                    st.error("E-mail não encontrado.")
                elif user.get("password") != sha(password):
                    st.error("Senha incorreta.")
                else:
                    st.session_state.logged_in = True
                    st.session_state.current_user = email
                    st.session_state.page = "workspace"
                    st.rerun()
        st.caption("Conta de demonstração: demo@nebula.ai · senha: demo123")
    with tab_signup:
        with st.form("form_signup"):
            name = st.text_input("Nome completo")
            email = st.text_input("E-mail")
            area = st.text_input("Área de pesquisa", placeholder="Ex.: Museologia, IA, Preservação Digital")
            bio = st.text_area("Bio", height=100)
            password = st.text_input("Senha", type="password")
            password2 = st.text_input("Confirmar senha", type="password")
            submit = st.form_submit_button("Criar conta", use_container_width=True)
            if submit:
                if not all([name.strip(), email.strip(), area.strip(), password.strip(), password2.strip()]):
                    st.error("Preencha os campos obrigatórios.")
                elif password != password2:
                    st.error("As senhas não coincidem.")
                elif email in st.session_state.users:
                    st.error("Este e-mail já está cadastrado.")
                else:
                    st.session_state.users[email] = {
                        "name": name.strip(),
                        "password": sha(password),
                        "area": area.strip(),
                        "bio": bio.strip(),
                        "saved_articles": [],
                        "search_history": [],
                        "interest_profile": {},
                    }
                    save_state()
                    st.success("Conta criada. Agora você já pode entrar no Nebula.")
    glass_close()
    st.markdown('</div>', unsafe_allow_html=True)


def page_workspace():
    page_header("Nebula", "Interface lateral em liquid glass, repositório acadêmico e análise conectada em um único ambiente.")
    docs = analyzed_local_documents()
    all_docs = all_local_documents()
    user = current_user_data()
    stats = aggregate_statistics(docs)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric("Repositórios", str(len(st.session_state.repositories)), "Pastas inteligentes disponíveis")
    with c2:
        render_metric("Arquivos", str(len(all_docs)), "Documentos e imagens no sistema")
    with c3:
        render_metric("Análises", str(len(docs)), "Arquivos com análise estruturada")
    with c4:
        render_metric("Temas", str(len(stats["topics"])), "Temas inferidos pelo algoritmo")

    left, right = st.columns([1.3, 1])
    with left:
        glass_open("padding:1rem 1rem .9rem 1rem; margin-top:.85rem;")
        st.markdown('<div class="mini-title">Perfil de interesse do usuário</div>', unsafe_allow_html=True)
        interests = sorted((user.get("interest_profile") or {}).items(), key=lambda x: x[1], reverse=True)
        render_keyword_chips([k for k, _ in interests[:12]])
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown('<div class="mini-title">Histórico recente</div>', unsafe_allow_html=True)
        history = user.get("search_history") or []
        if history:
            for row in history[:8]:
                st.markdown(f'<div class="repo-item"><div>{row["query"]}</div><div class="tiny">{row["date"]}</div></div>', unsafe_allow_html=True)
        else:
            st.caption("Ainda não há buscas registradas.")
        glass_close()
    with right:
        glass_open("padding:1rem 1rem .9rem 1rem; margin-top:.85rem;")
        st.markdown('<div class="mini-title">Pulso da base</div>', unsafe_allow_html=True)
        render_keyword_chips([k for k, _ in stats["topics"].most_common(10)])
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown('<div class="mini-title">Métodos mais frequentes</div>', unsafe_allow_html=True)
        render_keyword_chips([f"{k} ({v})" for k, v in stats["methods"].most_common(8)])
        glass_close()

    glass_open("padding:1rem 1rem .9rem 1rem; margin-top:.9rem;")
    st.markdown('<div class="mini-title">Repositórios do sistema</div>', unsafe_allow_html=True)
    if st.session_state.repositories:
        for repo_id, repo in st.session_state.repositories.items():
            render_repo_card(repo_id, repo)
    else:
        st.caption("Nenhum repositório criado ainda. Vá em Repositório para criar o primeiro.")
    glass_close()


def page_search():
    page_header("Pesquisa Inteligente", "Busca unificada para artigos, documentos locais, imagens semelhantes e sugestões de pesquisa.")
    user_profile = current_user_data().get("interest_profile") or {}

    glass_open("padding:1rem 1rem .9rem 1rem; margin-bottom:.9rem;")
    st.markdown('<div class="mini-title">Motor de busca unificado</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([2.3, 1])
    with c1:
        query = st.text_input("Consulta", placeholder="Ex.: folksonomia em museus, preservação digital, IA em documentação museológica")
    with c2:
        search_web = st.checkbox("Buscar também na internet", value=True)
    uploaded_image = st.file_uploader("Imagem de referência para busca visual", type=["png", "jpg", "jpeg", "webp", "bmp"])

    repo_options = ["Todos"] + [r.get("name", rid) for rid, r in st.session_state.repositories.items()]
    repo_choice = st.selectbox("Escopo local", repo_options)

    run = st.button("Executar busca", use_container_width=True)
    if run:
        intelligence = infer_query_intent(query, user_profile)
        local_docs = all_local_documents()
        if repo_choice != "Todos":
            local_docs = [d for d in local_docs if d.get("repo_name") == repo_choice]
        local_results = local_search(query, local_docs)
        external_results = scholar_search(query) if search_web else []
        external_images = commons_image_search(query, 10) if search_web else []
        image_matches = local_image_similarity(uploaded_image.getvalue(), local_docs) if uploaded_image else []

        if uploaded_image:
            st.session_state.last_uploaded_image_name = uploaded_image.name
        st.session_state.search_results = intelligence
        st.session_state.local_matches = local_results
        st.session_state.external_matches = external_results
        st.session_state.external_images = external_images
        st.session_state.image_matches = image_matches
        update_user_interest(query, intelligence.get("keywords"), intelligence.get("topics"))

    intelligence = st.session_state.get("search_results")
    if intelligence:
        left, right = st.columns([1.15, 1])
        with left:
            glass_open("padding:1rem 1rem .9rem 1rem;")
            st.markdown('<div class="mini-title">Leitura da consulta</div>', unsafe_allow_html=True)
            st.markdown(f"<div class='tiny'>Intenção inferida: <strong>{intelligence.get('intent','exploratória')}</strong></div>", unsafe_allow_html=True)
            st.markdown("<div style='margin-top:.7rem' class='tiny'>Palavras-chave centrais</div>", unsafe_allow_html=True)
            render_keyword_chips(intelligence.get("keywords") or [])
            st.markdown("<div style='margin-top:.45rem' class='tiny'>Temas relacionados</div>", unsafe_allow_html=True)
            render_keyword_chips(intelligence.get("topics") or [])
            glass_close()
        with right:
            glass_open("padding:1rem 1rem .9rem 1rem;")
            st.markdown('<div class="mini-title">Sugestões de expansão</div>', unsafe_allow_html=True)
            render_keyword_chips(intelligence.get("suggestions") or [])
            glass_close()

        tabs = st.tabs(["Resultados locais", "Artigos da internet", "Imagens semelhantes", "Imagens da internet"])
        with tabs[0]:
            if st.session_state.local_matches:
                for item in st.session_state.local_matches:
                    render_local_result(item)
            else:
                st.caption("Nenhum resultado local encontrado para esta consulta.")
        with tabs[1]:
            if st.session_state.external_matches:
                for item in st.session_state.external_matches:
                    render_external_result(item)
            else:
                st.caption("Nenhum artigo externo encontrado.")
        with tabs[2]:
            if st.session_state.image_matches:
                for m in st.session_state.image_matches:
                    st.markdown(f"<div class='result-item'><div class='mini-title'>{m['original_name']}</div><div class='tiny'>Repositório: {m['repo_name']} · Similaridade: {m['similarity']:.2f}</div></div>", unsafe_allow_html=True)
                    if os.path.exists(m["path"]):
                        st.image(m["path"], use_container_width=True)
            else:
                st.caption("Nenhuma imagem semelhante encontrada nas pastas locais.")
        with tabs[3]:
            if st.session_state.external_images:
                cols = st.columns(2)
                for idx, img in enumerate(st.session_state.external_images[:8]):
                    with cols[idx % 2]:
                        st.markdown(f"<div class='result-item'><div class='mini-title'>{img['title']}</div><div class='tiny'>{img['source']}</div></div>", unsafe_allow_html=True)
                        st.image(img["url"], use_container_width=True)
            else:
                st.caption("Nenhuma imagem externa encontrada para a consulta atual.")
    glass_close()


def page_repository():
    page_header("Repositório", "Gestão de pastas, ingestão de arquivos, análise automática e sugestões de pesquisa por repositório.")

    c1, c2 = st.columns([1.1, 1.9])
    with c1:
        glass_open("padding:1rem 1rem .9rem 1rem;")
        st.markdown('<div class="mini-title">Novo repositório</div>', unsafe_allow_html=True)
        with st.form("create_repo"):
            name = st.text_input("Nome", placeholder="Ex.: Estudos de público")
            desc = st.text_area("Descrição", height=90)
            tags = st.text_input("Tags", placeholder="Ex.: museologia, folksonomia, acessibilidade")
            submit = st.form_submit_button("Criar repositório", use_container_width=True)
            if submit:
                if not name.strip():
                    st.error("Digite um nome para o repositório.")
                else:
                    repo_id = slugify(name)
                    if repo_id in st.session_state.repositories:
                        st.error("Já existe um repositório com esse nome.")
                    else:
                        st.session_state.repositories[repo_id] = {
                            "name": name.strip(),
                            "description": desc.strip(),
                            "tags": [t.strip() for t in tags.split(",") if t.strip()],
                            "created_at": now_str(),
                            "files": [],
                        }
                        save_state()
                        st.success("Repositório criado.")
                        st.rerun()
        glass_close()
    with c2:
        glass_open("padding:1rem 1rem .9rem 1rem;")
        st.markdown('<div class="mini-title">Resumo do repositório</div>', unsafe_allow_html=True)
        render_keyword_chips([r.get("name", rid) for rid, r in st.session_state.repositories.items()])
        glass_close()

    if not st.session_state.repositories:
        return

    repo_names = {r.get("name", rid): rid for rid, r in st.session_state.repositories.items()}
    selected_name = st.selectbox("Escolha um repositório", list(repo_names.keys()))
    repo_id = repo_names[selected_name]
    repo = st.session_state.repositories[repo_id]

    glass_open("padding:1rem 1rem .9rem 1rem; margin-top:.9rem;")
    st.markdown(f'<div class="mini-title">{repo.get("name")}</div>', unsafe_allow_html=True)
    st.caption(repo.get("description", ""))
    render_keyword_chips(repo.get("tags", []))
    uploads = st.file_uploader("Adicionar arquivos", accept_multiple_files=True, key=f"upload_{repo_id}")
    if uploads:
        added = 0
        existing_sha = {f.get("sha1") for f in repo.get("files", [])}
        for up in uploads:
            item = store_uploaded_file(repo_id, up)
            if item["sha1"] not in existing_sha:
                repo.setdefault("files", []).append(item)
                existing_sha.add(item["sha1"])
                added += 1
        st.session_state.repositories[repo_id] = repo
        save_state()
        st.success(f"{added} arquivo(s) adicionados ao repositório.")
        st.rerun()
    glass_close()

    left, right = st.columns([1.5, 1])
    with left:
        glass_open("padding:1rem 1rem .9rem 1rem; margin-top:.8rem;")
        st.markdown('<div class="mini-title">Arquivos do repositório</div>', unsafe_allow_html=True)
        if repo.get("files"):
            for idx, item in enumerate(repo["files"]):
                ana = item.get("analysis") or {}
                st.markdown(
                    f"""
                    <div class="repo-item">
                      <div class="mini-title">{ana.get('title') or item.get('original_name')}</div>
                      <div class="tiny">{item.get('type')} · {item.get('uploaded_at')} · {round(item.get('size',0)/1024,1)} KB</div>
                      <div style="margin-top:.5rem; color:#D7E1F8;">{ana.get('summary','')}</div>
                      <div style="margin-top:.55rem;">{"".join([f'<span class="chip">{k}</span>' for k in ana.get('keywords',[])[:8]])}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                col_a, col_b = st.columns([1, 1])
                with col_a:
                    if item.get("type") == "Imagem" and os.path.exists(item.get("path", "")):
                        st.image(item["path"], use_container_width=True)
                    elif item.get("text"):
                        st.text_area("Conteúdo extraído", value=item["text"][:1800], height=150, key=f"txt_{repo_id}_{idx}")
                with col_b:
                    st.download_button(
                        "Baixar metadados do arquivo",
                        data=to_download_bytes(item),
                        file_name=f"{slugify(item.get('original_name','arquivo'))}_metadados.json",
                        mime="application/json",
                        key=f"dl_meta_{repo_id}_{idx}",
                    )
                    if st.button("Remover arquivo", key=f"rm_file_{repo_id}_{idx}", use_container_width=True):
                        try:
                            if os.path.exists(item.get("path", "")):
                                os.remove(item["path"])
                        except Exception:
                            pass
                        repo["files"].pop(idx)
                        st.session_state.repositories[repo_id] = repo
                        save_state()
                        st.rerun()
                st.markdown("<hr>", unsafe_allow_html=True)
        else:
            st.caption("Nenhum arquivo neste repositório ainda.")
        glass_close()
    with right:
        glass_open("padding:1rem 1rem .9rem 1rem; margin-top:.8rem;")
        st.markdown('<div class="mini-title">Sugestões de pesquisa</div>', unsafe_allow_html=True)
        suggestions = repo_research_suggestions(repo)
        render_keyword_chips(suggestions)
        if suggestions and requests is not None:
            st.markdown('<div class="mini-title" style="margin-top:.85rem;">Artigos relacionados</div>', unsafe_allow_html=True)
            related = scholar_search(suggestions[0])[:4]
            for item in related:
                render_external_result(item)
        glass_close()


def page_analytics():
    page_header("Análises", "Leitura agregada do acervo pesquisado com gráficos por ano, tema, autor, método e distribuição geográfica.")
    docs = analyzed_local_documents()
    if not docs:
        st.info("Adicione arquivos textuais aos repositórios para liberar as análises.")
        return

    stats = aggregate_statistics(docs)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric("Documentos", str(len(docs)), "Arquivos analisados")
    with c2:
        render_metric("Autores", str(len(stats["authors"])), "Autores identificados")
    with c3:
        render_metric("Países", str(len(stats["countries"])), "Países ou afiliações detectados")
    with c4:
        avg_year = int(sum(stats["years"].elements()) / max(sum(stats["years"].values()), 1)) if stats["years"] else 0
        render_metric("Ano médio", str(avg_year) if avg_year else "n/d", "Centro temporal do corpus")

    tabs = st.tabs(["Resumo", "Gráficos", "Globo", "Tabela"])
    with tabs[0]:
        glass_open("padding:1rem 1rem .9rem 1rem;")
        st.markdown('<div class="mini-title">Síntese da pesquisa</div>', unsafe_allow_html=True)
        themes = ", ".join(k for k, _ in stats["topics"].most_common(6)) or "não identificados"
        methods = ", ".join(k for k, _ in stats["methods"].most_common(4)) or "não identificados"
        authors = ", ".join(k for k, _ in stats["authors"].most_common(5)) or "não identificados"
        st.write(
            f"O corpus analisado concentra-se principalmente em {themes}. "
            f"Os métodos predominantes são {methods}. "
            f"Entre os autores mais recorrentes aparecem {authors}."
        )
        st.markdown('<div class="mini-title" style="margin-top:.9rem;">Temas centrais</div>', unsafe_allow_html=True)
        render_keyword_chips([f"{k} ({v})" for k, v in stats["topics"].most_common(12)])
        glass_close()
    with tabs[1]:
        if px is not None and go is not None:
            col_a, col_b = st.columns(2)
            with col_a:
                if stats["years"]:
                    fig = px.bar(x=list(stats["years"].keys()), y=list(stats["years"].values()))
                    fig.update_layout(height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=20, r=20, t=20, b=20))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.caption("Não há anos identificados o suficiente para o gráfico.")
            with col_b:
                fig = px.bar(x=list(stats["topics"].keys())[:10], y=list(stats["topics"].values())[:10])
                fig.update_layout(height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)
            col_c, col_d = st.columns(2)
            with col_c:
                fig = px.bar(x=list(stats["authors"].keys())[:10], y=list(stats["authors"].values())[:10])
                fig.update_layout(height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=20, r=20, t=20, b=20), xaxis_tickangle=-25)
                st.plotly_chart(fig, use_container_width=True)
            with col_d:
                fig = px.pie(values=list(stats["methods"].values()), names=list(stats["methods"].keys()))
                fig.update_layout(height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Plotly não está disponível no ambiente.")
    with tabs[2]:
        fig = countries_globe_figure(stats["countries"])
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("O corpus ainda não tem países suficientes para montar o globo interativo.")
    with tabs[3]:
        df = docs_dataframe(docs)
        if df is not None:
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button(
                "Baixar tabela analítica",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="nebula_analises.csv",
                mime="text/csv",
            )
        else:
            st.caption("Pandas não está disponível para renderizar a tabela.")


def page_connections():
    page_header("Conexões", "Relações entre pesquisas semelhantes, padrões compartilhados e rede de proximidade temática.")
    docs = analyzed_local_documents()
    if len(docs) < 2:
        st.info("São necessários pelo menos dois documentos analisados para calcular conexões.")
        return

    connections = pairwise_connections(docs)
    st.session_state.connections_cache = connections
    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric("Conexões", str(len(connections)), "Pares relevantes identificados")
    with c2:
        avg_score = round(sum(c["score"] for c in connections) / max(len(connections), 1), 2) if connections else 0
        render_metric("Força média", f"{avg_score:.2f}", "Intensidade média das ligações")
    with c3:
        total_patterns = len({p for c in connections for p in c.get("patterns", [])})
        render_metric("Padrões", str(total_patterns), "Vocabulário compartilhado entre pesquisas")

    fig = connection_graph_figure(docs, connections)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)

    glass_open("padding:1rem 1rem .9rem 1rem; margin-top:.4rem;")
    st.markdown('<div class="mini-title">Ligações mais fortes</div>', unsafe_allow_html=True)
    for item in connections[:14]:
        st.markdown(
            f"""
            <div class="connection-item">
              <div class="mini-title" style="font-size:.96rem;">{item['a']}  ·  {item['b']}</div>
              <div class="tiny">Força da conexão: {item['score']:.2f}</div>
              <div style="margin-top:.55rem; color:#D7E1F8;">Padrões em comum: {', '.join(item['patterns']) or 'Sem padrões explícitos'}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    if not connections:
        st.caption("Nenhuma ligação suficientemente forte foi encontrada.")
    glass_close()


def page_account():
    page_header("Conta", "Dados do usuário e configuração pessoal do ambiente Nebula.")
    user = current_user_data()
    email = st.session_state.get("current_user")
    glass_open("padding:1rem 1rem 1rem 1rem;")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        name = st.text_input("Nome", value=user.get("name", ""))
        area = st.text_input("Área de pesquisa", value=user.get("area", ""))
        bio = st.text_area("Bio", value=user.get("bio", ""), height=140)
    with col_b:
        st.text_input("E-mail", value=email or "", disabled=True)
        new_password = st.text_input("Nova senha", type="password")
        confirm_password = st.text_input("Confirmar nova senha", type="password")
    if st.button("Salvar alterações", use_container_width=True):
        if new_password and new_password != confirm_password:
            st.error("As senhas não coincidem.")
        else:
            user["name"] = name.strip()
            user["area"] = area.strip()
            user["bio"] = bio.strip()
            if new_password:
                user["password"] = sha(new_password)
            st.session_state.users[email] = user
            save_state()
            st.success("Conta atualizada.")
    glass_close()

# =============================
# Main app
# =============================
def main():
    inject_css()
    init_state()

    if not st.session_state.logged_in:
        page_login()
        return

    render_sidebar()
    page = st.session_state.get("page", "workspace")

    if page == "workspace":
        page_workspace()
    elif page == "search":
        page_search()
    elif page == "repository":
        page_repository()
    elif page == "analytics":
        page_analytics()
    elif page == "connections":
        page_connections()
    elif page == "account":
        page_account()
    else:
        page_workspace()


if __name__ == "__main__":
    main()
