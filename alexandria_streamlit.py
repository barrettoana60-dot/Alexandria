from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

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
    import plotly.express as px
    import plotly.graph_objects as go
except Exception:
    px = None
    go = None

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

APP_NAME = "Nebula"
APP_DIR = Path("nebula_app_data")
USERS_FILE = APP_DIR / "users.json"
REPOS_FILE = APP_DIR / "repos.json"
APP_DIR.mkdir(exist_ok=True)
FILES_DIR = APP_DIR / "files"
FILES_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title=APP_NAME, layout="wide", initial_sidebar_state="collapsed")

STOPWORDS = {
    "de","da","do","das","dos","a","o","as","os","e","em","para","por","com","um","uma","uns","umas",
    "ao","aos","na","no","nas","nos","que","se","como","mais","menos","entre","sobre","sem","ser","são",
    "the","of","and","or","in","to","for","by","with","on","at","from","an","is","are","be","this","that",
    "paper","study","research","article","using","used","analysis","results","method","methods","data","dos","das",
    "também","ainda","entre","cada","foram","sendo","após","sobre","porque","where","which","into","within",
}

THEMES = {
    "Museologia": ["museologia","museu","museus","acervo","acervos","coleção","coleções","curadoria","catalogação","folksonomia","documentação museológica","patrimônio","exposição"],
    "Ciência da Informação": ["metadados","indexação","descrição","classificação","taxonomia","ontologia","recuperação da informação","repositório","dados"],
    "Inteligência Artificial": ["inteligência artificial","machine learning","deep learning","llm","modelo","rede neural","visão computacional","aprendizado de máquina"],
    "Preservação Digital": ["preservação digital","digitalização","arquivo digital","interoperabilidade","repositório institucional","acesso aberto"],
    "Humanidades Digitais": ["humanidades digitais","digital humanities","cultura digital","acervos digitais"],
    "Computação": ["python","streamlit","algoritmo","sistema","interface","software","banco de dados","api"],
    "Educação": ["educação","aprendizagem","ensino","didática","estudantes","universidade","escola"],
    "Saúde": ["saúde","hospital","paciente","tratamento","diagnóstico","doença"],
}

METHODS = {
    "Revisão": ["revisão","estado da arte","systematic review","scoping review","revisão bibliográfica"],
    "Qualitativa": ["qualitativa","entrevista","grupo focal","observação","análise temática","etnográfica"],
    "Quantitativa": ["quantitativa","questionário","survey","estatística","regressão","amostra","variável"],
    "Computacional": ["algoritmo","pipeline","modelo","simulação","python","streamlit","classificação automática"],
    "Experimental": ["experimental","laboratório","teste","protocolo","medição"],
    "Estudo de Caso": ["estudo de caso","case study","instituição","museu específico"],
}

COUNTRIES = {
    "Brasil": {"aliases": ["brasil","brazil","rio de janeiro","são paulo","unirio","ufrj","usp","unicamp","ufmg","fiocruz"], "lat": -14.2350, "lon": -51.9253},
    "Estados Unidos": {"aliases": ["united states","usa","harvard","mit","stanford","new york"], "lat": 39.8283, "lon": -98.5795},
    "Reino Unido": {"aliases": ["united kingdom","uk","oxford","cambridge","london"], "lat": 55.3781, "lon": -3.4360},
    "Portugal": {"aliases": ["portugal","lisboa","porto","lusófona"], "lat": 39.3999, "lon": -8.2245},
    "França": {"aliases": ["france","paris","frança"], "lat": 46.2276, "lon": 2.2137},
    "Espanha": {"aliases": ["spain","espanha","madrid","barcelona"], "lat": 40.4637, "lon": -3.7492},
    "Alemanha": {"aliases": ["germany","alemanha","berlin"], "lat": 51.1657, "lon": 10.4515},
    "Itália": {"aliases": ["italy","itália","rome","roma","milan"], "lat": 41.8719, "lon": 12.5674},
    "Canadá": {"aliases": ["canada","canadá","toronto","montreal"], "lat": 56.1304, "lon": -106.3468},
    "Argentina": {"aliases": ["argentina","buenos aires"], "lat": -38.4161, "lon": -63.6167},
    "México": {"aliases": ["méxico","mexico","cdmx"], "lat": 23.6345, "lon": -102.5528},
    "Chile": {"aliases": ["chile","santiago"], "lat": -35.6751, "lon": -71.5430},
    "Colômbia": {"aliases": ["colombia","colômbia","bogotá"], "lat": 4.5709, "lon": -74.2973},
    "Japão": {"aliases": ["japan","japão","tokyo","kyoto"], "lat": 36.2048, "lon": 138.2529},
    "Índia": {"aliases": ["india","índia","mumbai","new delhi"], "lat": 20.5937, "lon": 78.9629},
    "China": {"aliases": ["china","beijing","shanghai"], "lat": 35.8617, "lon": 104.1954},
}

NAV = [
    ("dashboard", "Visão Geral"),
    ("search", "Pesquisa Inteligente"),
    ("repository", "Repositório"),
    ("analytics", "Análises"),
    ("connections", "Conexões"),
    ("account", "Conta"),
]


def css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg1: #030710;
            --bg2: #071830;
            --bg3: #0b1f44;
            --glass: rgba(14, 24, 46, 0.62);
            --glass2: rgba(255,255,255,0.06);
            --line: rgba(155, 192, 255, 0.16);
            --text: #edf4ff;
            --muted: #95a6c7;
            --accent: #9fd1ff;
            --accent2: #caa7ff;
            --shadow: 0 10px 40px rgba(0,0,0,.35);
        }
        html, body, [data-testid="stAppViewContainer"], .stApp {
            background:
                radial-gradient(circle at 20% 0%, rgba(48, 94, 182, 0.25), transparent 30%),
                radial-gradient(circle at 80% 0%, rgba(170, 112, 255, 0.18), transparent 32%),
                linear-gradient(180deg, var(--bg1), #041224 38%, #05172d 100%);
            color: var(--text);
        }
        [data-testid="stHeader"] {background: transparent;}
        .block-container {padding-top: 1rem; padding-bottom: 2rem; max-width: 100%;}
        .nebula-shell {padding: 0.6rem 0.8rem 1rem 0.8rem;}
        .nebula-sidebar {
            position: sticky; top: 0.7rem; min-height: calc(100vh - 1.4rem);
            border: 1px solid var(--line); border-radius: 28px;
            background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
            backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
            box-shadow: var(--shadow);
            padding: 1rem;
        }
        .nebula-logo-wrap {display:flex; align-items:center; gap:.8rem; margin-bottom:1rem;}
        .nebula-logo {
            width: 54px; height: 54px; border-radius: 18px; border:1px solid var(--line);
            background: linear-gradient(135deg, rgba(159,209,255,.18), rgba(202,167,255,.14));
            display:flex; align-items:center; justify-content:center;
        }
        .nebula-brand {font-size: 2.15rem; font-weight: 800; letter-spacing: -0.05em; margin:0; line-height:1;}
        .nebula-brand-sub {color: var(--muted); font-size: .92rem; margin-top:.25rem;}
        .nav-title {color: var(--muted); font-size: .72rem; letter-spacing: .14em; text-transform: uppercase; margin:.9rem 0 .4rem 0;}
        .page-title {font-size: 2.15rem; line-height:1.05; font-weight: 800; margin:0; letter-spacing:-.05em;}
        .page-subtitle {color: var(--muted); font-size: 1rem; margin-top:.35rem; margin-bottom:1rem;}
        .glass-card {
            border: 1px solid var(--line); border-radius: 24px; padding: 1rem 1.05rem;
            background: linear-gradient(180deg, rgba(255,255,255,.07), rgba(255,255,255,.03));
            backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
            box-shadow: var(--shadow);
            height: 100%;
        }
        .glass-bar {
            border: 1px solid var(--line); border-radius: 999px; height: 38px;
            background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02));
            backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
        }
        .metric-label {font-size:.74rem; text-transform: uppercase; letter-spacing:.18em; color:#bcc7df; font-weight:700;}
        .metric-value {font-size:2.4rem; font-weight:800; letter-spacing:-.06em; margin-top:.6rem; color:#eff4ff;}
        .metric-sub {color:var(--muted); font-size:.95rem; margin-top:.45rem;}
        .section-title {font-size:1.45rem; font-weight:800; letter-spacing:-.04em; margin:.2rem 0 .4rem 0;}
        .section-text {color: var(--muted);}
        .stButton > button {
            width: 100%;
            border-radius: 18px;
            border: 1px solid rgba(180, 208, 255, 0.18);
            background: linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,.04));
            color: #edf4ff;
            min-height: 46px;
            font-weight: 700;
            box-shadow: inset 0 1px 0 rgba(255,255,255,.08), 0 8px 24px rgba(0,0,0,.18);
        }
        .stButton > button:hover {
            border-color: rgba(159, 209, 255, 0.45);
            color: #ffffff;
        }
        .nav-active .stButton > button {
            border-color: rgba(159,209,255,.55) !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,.12), 0 10px 26px rgba(12,41,94,.45) !important;
            background: linear-gradient(180deg, rgba(120,165,255,.18), rgba(255,255,255,.05)) !important;
        }
        div[data-testid="stFileUploader"] section {
            border-radius: 22px !important; border: 1px dashed rgba(159,209,255,.26) !important;
            background: rgba(255,255,255,.035) !important;
        }
        .tiny {font-size:.82rem; color:var(--muted);}
        .chip {
            display:inline-block; padding:.28rem .6rem; border-radius:999px; font-size:.72rem;
            border:1px solid var(--line); background:rgba(255,255,255,.05); margin:.15rem .25rem .15rem 0;
        }
        .res-item {border-bottom:1px solid rgba(255,255,255,.08); padding:.7rem 0;}
        .res-item:last-child {border-bottom:none;}
        .doc-title {font-size:1rem; font-weight:700; color:#eef5ff; margin-bottom:.18rem;}
        .doc-meta {font-size:.82rem; color:var(--muted); margin-bottom:.28rem;}
        .doc-snippet {font-size:.92rem; color:#dbe7ff;}
        .small-table table {font-size:.9rem;}
        [data-testid="stSidebar"] {display:none;}
        .stTextInput > div > div, .stTextArea textarea, .stSelectbox [data-baseweb="select"] > div, .stMultiSelect [data-baseweb="select"] > div {
            border-radius: 18px !important;
            background: rgba(255,255,255,.05) !important;
            border: 1px solid rgba(170,195,255,.14) !important;
            color: #eff4ff !important;
        }
        .stTabs [data-baseweb="tab-list"] {gap: .3rem;}
        .stTabs [data-baseweb="tab"] {
            border-radius: 16px; border:1px solid rgba(255,255,255,.08); background:rgba(255,255,255,.03);
            color:#dce8ff; padding:.4rem .9rem;
        }
        .stTabs [aria-selected="true"] {background:rgba(110,150,255,.14) !important; border-color:rgba(159,209,255,.38) !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def microscope_svg() -> str:
    raw = """
    <svg width="30" height="30" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M23 12h10l9 12-6 4-9-12h-4V12Z" fill="url(#g1)"/>
      <rect x="31" y="22" width="8" height="19" rx="4" fill="#EAF3FF" fill-opacity="0.9"/>
      <path d="M22 40c0-4.4 3.6-8 8-8h10c5.5 0 10 4.5 10 10v3H22v-5Z" fill="url(#g2)"/>
      <path d="M14 50h38" stroke="#EAF3FF" stroke-opacity="0.92" stroke-width="4" stroke-linecap="round"/>
      <circle cx="20" cy="46" r="5" fill="#C9A9FF" fill-opacity="0.92"/>
      <defs>
        <linearGradient id="g1" x1="19" y1="10" x2="44" y2="34" gradientUnits="userSpaceOnUse">
          <stop stop-color="#9FD1FF"/>
          <stop offset="1" stop-color="#CAA7FF"/>
        </linearGradient>
        <linearGradient id="g2" x1="22" y1="32" x2="50" y2="49" gradientUnits="userSpaceOnUse">
          <stop stop-color="#9FD1FF" stop-opacity="0.9"/>
          <stop offset="1" stop-color="#CAA7FF" stop-opacity="0.85"/>
        </linearGradient>
      </defs>
    </svg>
    """
    return base64.b64encode(raw.encode()).decode()


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", strip_html(text or "")).strip()


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", (text or "").lower(), flags=re.UNICODE).strip()
    return re.sub(r"[-\s]+", "-", text) or "item"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def safe_load(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def safe_dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def tokenize(text: str) -> list[str]:
    clean = strip_html((text or "").lower())
    clean = re.sub(r"[^\w\sáàâãéêíóôõúçü-]", " ", clean, flags=re.UNICODE)
    return [t for t in clean.split() if len(t) > 2 and t not in STOPWORDS]


def sentence_split(text: str) -> list[str]:
    items = re.split(r"(?<=[\.!?])\s+", normalize(text))
    return [s.strip() for s in items if len(s.strip()) > 30]


def guess_title(file_name: str, text: str) -> str:
    lines = [normalize(x) for x in (text or "").splitlines() if normalize(x)]
    for ln in lines[:8]:
        if 12 <= len(ln) <= 180:
            return ln
    base = Path(file_name).stem.replace("_", " ").replace("-", " ")
    return base.title()


def guess_authors(text: str) -> list[str]:
    authors: list[str] = []
    lines = [normalize(x) for x in (text or "").splitlines() if normalize(x)]
    candidate_block = " ".join(lines[:12])
    patterns = [
        r"(?:autores?|authors?)\s*[:\-]\s*([^\n\.]{6,220})",
        r"(?:por|by)\s+([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç'\-]+(?:\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç'\-]+){0,4}(?:\s*,\s*[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç'\-]+(?:\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-Za-zÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç'\-]+){0,4})*)",
    ]
    for pat in patterns:
        m = re.search(pat, candidate_block, re.IGNORECASE)
        if m:
            raw = m.group(1)
            for part in re.split(r"\s*,\s*|\s+;\s*|\s+and\s+|\s+e\s+", raw):
                p = normalize(part)
                if 4 <= len(p) <= 80 and any(ch.isalpha() for ch in p):
                    authors.append(p)
    if authors:
        return list(dict.fromkeys(authors))[:8]
    title_like = [ln for ln in lines[1:5] if 5 <= len(ln) <= 120 and sum(1 for c in ln if c.isupper()) < len(ln) * 0.8]
    for ln in title_like:
        if re.fullmatch(r"[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][\wÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç'\-]+(?:\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][\wÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç'\-]+){1,4}", ln):
            authors.append(ln)
    return list(dict.fromkeys(authors))[:8]


def guess_years(text: str) -> list[int]:
    years = [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", text or "")]
    current = datetime.now().year + 1
    return [y for y in years if 1900 <= y <= current]


def infer_themes(text: str) -> list[str]:
    t = (text or "").lower()
    scores = []
    for theme, lex in THEMES.items():
        score = sum(2 if term in t else 0 for term in lex)
        if score:
            scores.append((theme, score))
    return [x[0] for x in sorted(scores, key=lambda k: (-k[1], k[0]))[:4]]


def infer_method(text: str) -> str:
    t = (text or "").lower()
    scores = []
    for method, lex in METHODS.items():
        score = sum(2 if term in t else 0 for term in lex)
        if score:
            scores.append((method, score))
    return sorted(scores, key=lambda x: (-x[1], x[0]))[0][0] if scores else "Não identificado"


def infer_countries(text: str) -> list[str]:
    t = (text or "").lower()
    hits = []
    for country, meta in COUNTRIES.items():
        count = sum(1 for alias in meta["aliases"] if alias in t)
        if count:
            hits.append((country, count))
    return [c for c, _ in sorted(hits, key=lambda x: (-x[1], x[0]))[:5]]


def top_keywords(text: str, limit: int = 18) -> list[str]:
    toks = tokenize(text)
    cnt = Counter(toks)
    return [w for w, _ in cnt.most_common(limit)]


def summarize(text: str, max_sentences: int = 4) -> str:
    sents = sentence_split(text)
    if not sents:
        return "Resumo não identificado no conteúdo."
    joined = " ".join(sents[:20])
    kws = set(top_keywords(joined, 20))
    scored = []
    for idx, sent in enumerate(sents[:30]):
        score = sum(1 for tk in tokenize(sent) if tk in kws) + max(0, 8 - idx)
        scored.append((score, idx, sent))
    chosen = [s for _, _, s in sorted(scored, key=lambda x: (-x[0], x[1]))[:max_sentences]]
    return " ".join(chosen)


def local_text_search_score(query: str, text: str, title: str = "") -> float:
    q = tokenize(query)
    if not q:
        return 0.0
    corpus = f"{title} {text}".lower()
    overlap = sum(3 for tok in q if tok in corpus)
    exact = 12 if query.lower().strip() in corpus else 0
    return float(overlap + exact)


def ensure_defaults() -> None:
    if "users" not in st.session_state:
        st.session_state.users = safe_load(USERS_FILE, {
            "demo@nebula.ai": {
                "name": "Conta Demo",
                "password": sha("demo123"),
                "area": "Pesquisa Acadêmica",
                "bio": "Conta inicial do sistema.",
                "search_history": [],
            }
        })
    if "repos" not in st.session_state:
        st.session_state.repos = safe_load(REPOS_FILE, {})
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "current_user" not in st.session_state:
        st.session_state.current_user = None
    if "page" not in st.session_state:
        st.session_state.page = "dashboard"
    if "last_query" not in st.session_state:
        st.session_state.last_query = ""


def persist() -> None:
    safe_dump(USERS_FILE, st.session_state.users)
    safe_dump(REPOS_FILE, st.session_state.repos)


def current_user() -> dict[str, Any]:
    email = st.session_state.current_user
    return st.session_state.users.get(email, {}) if email else {}


def current_user_repos() -> dict[str, Any]:
    email = st.session_state.current_user
    return st.session_state.repos.setdefault(email, {}) if email else {}


def user_repo_dir(repo_slug: str) -> Path:
    email = st.session_state.current_user or "anon"
    email_slug = slugify(email)
    path = FILES_DIR / email_slug / repo_slug
    path.mkdir(parents=True, exist_ok=True)
    return path


def extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    try:
        if suffix in {".txt", ".md", ".json", ".csv"}:
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix in {".pdf"} and PyPDF2:
            text = []
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages[:40]:
                    page_text = page.extract_text() or ""
                    if page_text:
                        text.append(page_text)
            return "\n".join(text)
        if suffix in {".docx"} and Document:
            doc = Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs)
        if suffix in {".xlsx", ".xls"} and openpyxl:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            chunks = []
            for ws in wb.worksheets[:6]:
                chunks.append(f"Planilha: {ws.title}")
                for row in ws.iter_rows(min_row=1, max_row=40, values_only=True):
                    vals = [str(v) for v in row if v is not None]
                    if vals:
                        chunks.append(" | ".join(vals))
            return "\n".join(chunks)
    except Exception:
        return ""
    return ""


def average_hash(path: Path) -> str | None:
    if not Image or not ImageOps:
        return None
    try:
        img = Image.open(path).convert("L")
        img = ImageOps.fit(img, (8, 8))
        arr = np.array(img) if np is not None else None
        if arr is None:
            return None
        threshold = arr.mean()
        bits = "".join("1" if pxv > threshold else "0" for pxv in arr.flatten())
        return f"{int(bits, 2):016x}"
    except Exception:
        return None


def hamming_distance(hash1: str, hash2: str) -> int:
    return bin(int(hash1, 16) ^ int(hash2, 16)).count("1")


def analyze_document(path: Path) -> dict[str, Any]:
    ext = path.suffix.lower()
    text = extract_text_from_file(path) if ext not in {".png", ".jpg", ".jpeg", ".webp"} else ""
    title = guess_title(path.name, text)
    years = guess_years(text)
    authors = guess_authors(text)
    analysis = {
        "file_name": path.name,
        "file_path": str(path),
        "extension": ext,
        "title": title,
        "text": text,
        "summary": summarize(text) if text else "Arquivo visual. Use a busca por imagem para encontrar itens semelhantes.",
        "authors": authors,
        "year": Counter(years).most_common(1)[0][0] if years else None,
        "themes": infer_themes(text),
        "method": infer_method(text) if text else "Não identificado",
        "keywords": top_keywords(text, 20),
        "countries": infer_countries(text),
        "created_at": now(),
    }
    if ext in {".png", ".jpg", ".jpeg", ".webp"}:
        analysis["image_hash"] = average_hash(path)
    return analysis


def reanalyze_all() -> list[dict[str, Any]]:
    docs = []
    repos = current_user_repos()
    for repo_slug, repo in repos.items():
        for item in repo.get("documents", []):
            p = Path(item["file_path"])
            if p.exists():
                analysis = analyze_document(p)
                item["analysis"] = analysis
                docs.append(analysis)
    persist()
    return docs


def all_documents() -> list[dict[str, Any]]:
    docs = []
    repos = current_user_repos()
    for _, repo in repos.items():
        for item in repo.get("documents", []):
            analysis = item.get("analysis")
            if analysis:
                docs.append(analysis)
    return docs


def semantic_scholar_search(query: str, limit: int = 8) -> list[dict[str, Any]]:
    if not requests or not query.strip():
        return []
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,abstract,url,venue,citationCount,openAccessPdf"
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json().get("data", [])
        results = []
        for item in data:
            results.append({
                "source": "Semantic Scholar",
                "title": item.get("title") or "Sem título",
                "authors": ", ".join(a.get("name", "") for a in item.get("authors", [])[:5]),
                "year": item.get("year"),
                "abstract": normalize(item.get("abstract", "")),
                "url": item.get("url") or item.get("openAccessPdf", {}).get("url", ""),
                "venue": item.get("venue", ""),
                "score": item.get("citationCount", 0),
            })
        return results
    except Exception:
        return []


def crossref_search(query: str, limit: int = 8) -> list[dict[str, Any]]:
    if not requests or not query.strip():
        return []
    url = "https://api.crossref.org/works"
    params = {"query.bibliographic": query, "rows": limit}
    headers = {"User-Agent": "NebulaAcademicApp/1.0 (mailto:example@example.com)"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=20)
        r.raise_for_status()
        items = r.json().get("message", {}).get("items", [])
        results = []
        for item in items:
            authors = []
            for a in item.get("author", [])[:5]:
                nm = " ".join(filter(None, [a.get("given"), a.get("family")]))
                if nm:
                    authors.append(nm)
            title = (item.get("title") or ["Sem título"])[0]
            abstract = normalize(re.sub(r"<[^>]+>", " ", item.get("abstract", "")))
            year = None
            parts = item.get("issued", {}).get("date-parts", [])
            if parts and parts[0]:
                year = parts[0][0]
            results.append({
                "source": "Crossref",
                "title": title,
                "authors": ", ".join(authors),
                "year": year,
                "abstract": abstract,
                "url": item.get("URL", ""),
                "venue": (item.get("container-title") or [""])[0],
                "score": item.get("is-referenced-by-count", 0),
            })
        return results
    except Exception:
        return []


def commons_image_search(query: str, limit: int = 8) -> list[dict[str, Any]]:
    if not requests or not query.strip():
        return []
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": 500,
        "format": "json",
        "origin": "*",
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", {})
        out = []
        for _, page in pages.items():
            info = (page.get("imageinfo") or [{}])[0]
            out.append({
                "title": page.get("title", ""),
                "url": info.get("descriptionurl", ""),
                "thumb": info.get("thumburl", info.get("url", "")),
            })
        return out
    except Exception:
        return []


def build_query_suggestions(query: str, docs: list[dict[str, Any]]) -> list[str]:
    base_tokens = top_keywords(query, 6)
    suggestions = []
    for theme, words in THEMES.items():
        if any(tok in " ".join(words) for tok in base_tokens):
            suggestions.append(f"{query} revisão sistemática")
            suggestions.append(f"{query} museus OR acervos")
            suggestions.append(f"{query} metadata OR folksonomia")
    corpus_words = []
    for d in docs:
        corpus_words.extend(d.get("keywords", [])[:5])
    for kw, _ in Counter(corpus_words).most_common(5):
        if kw not in query.lower():
            suggestions.append(f"{query} {kw}")
    if not suggestions:
        suggestions = [
            f"{query} estado da arte",
            f"{query} revisão bibliográfica",
            f"{query} museologia digital",
        ]
    return list(dict.fromkeys(suggestions))[:6]


def classify_query_intent(query: str) -> dict[str, Any]:
    q = normalize(query).lower()
    tokens = tokenize(q)
    if not q.strip():
        return {"intent": "geral", "label": "Consulta geral", "filters": [], "explanation": "Nenhuma consulta fornecida."}
    filters = []
    if re.search(r"\b(19|20)\d{2}\b", q):
        filters.append("ano")
    if any(tok in {"autor", "authors", "pesquisador", "pesquisadora"} for tok in tokens):
        filters.append("autor")
    if any(tok in {"imagem", "figura", "foto", "visual", "semelhante"} for tok in tokens):
        filters.append("imagem")
    if any(tok in {"método", "metodo", "metodologia", "survey", "revisão", "revisao"} for tok in tokens):
        filters.append("método")
    theme_hits = []
    for theme, words in THEMES.items():
        if any(w in q for w in words[:8]):
            theme_hits.append(theme)
    if theme_hits:
        filters.append("tema")
    if any(tok in {"autor", "authors", "pesquisador", "pesquisadora"} for tok in tokens):
        label = "Busca orientada a autoria"
        intent = "author"
    elif "imagem" in filters:
        label = "Busca visual e textual"
        intent = "visual"
    elif "ano" in filters and "tema" in filters:
        label = "Busca temática com recorte temporal"
        intent = "theme_time"
    elif "tema" in filters:
        label = "Busca temática"
        intent = "theme"
    elif "método" in filters:
        label = "Busca por metodologia"
        intent = "method"
    else:
        label = "Consulta acadêmica geral"
        intent = "general"
    explanation = "O algoritmo leu a consulta e priorizou texto, título, temas, método, ano e resultados externos compatíveis com o padrão detectado."
    return {"intent": intent, "label": label, "filters": filters, "themes": theme_hits[:4], "explanation": explanation}


def infer_user_interest_profile(user: dict[str, Any], docs: list[dict[str, Any]]) -> dict[str, Any]:
    themes = Counter()
    keywords = Counter()
    methods = Counter()
    years = Counter()
    search_history = user.get("search_history", [])
    for item in search_history[:30]:
        q = item.get("query", "")
        for t in infer_themes(q):
            themes[t] += 3
        for k in top_keywords(q, 8):
            keywords[k] += 2
        m = infer_method(q)
        if m != "Não identificado":
            methods[m] += 2
    for d in docs:
        for t in d.get("themes", []):
            themes[t] += 1
        for k in d.get("keywords", [])[:12]:
            keywords[k] += 1
        if d.get("method"):
            methods[d["method"]] += 1
        if d.get("year"):
            years[d["year"]] += 1
    preferred_themes = [k for k, _ in themes.most_common(6)]
    preferred_keywords = [k for k, _ in keywords.most_common(12)]
    preferred_methods = [k for k, _ in methods.most_common(4)]
    return {
        "themes": themes,
        "keywords": keywords,
        "methods": methods,
        "years": years,
        "preferred_themes": preferred_themes,
        "preferred_keywords": preferred_keywords,
        "preferred_methods": preferred_methods,
    }


def repo_research_suggestions(repo_docs: list[dict[str, Any]]) -> list[str]:
    if not repo_docs:
        return []
    profile = gather_corpus_profile(repo_docs)
    base_theme = profile["themes"].most_common(1)[0][0] if profile["themes"] else "pesquisa acadêmica"
    base_keywords = [k for k, _ in profile["keywords"].most_common(6)]
    method = profile["methods"].most_common(1)[0][0] if profile["methods"] else "revisão"
    suggestions = [
        f"{base_theme} revisão sistemática",
        f"{base_theme} {method}",
        f"{base_theme} tendências recentes",
    ]
    for kw in base_keywords[:4]:
        suggestions.append(f"{base_theme} {kw}")
        suggestions.append(f"{kw} museus OR repositórios")
    return list(dict.fromkeys([s.strip() for s in suggestions if s.strip()]))[:8]


def related_repo_articles(repo_docs: list[dict[str, Any]], limit: int = 4) -> list[dict[str, Any]]:
    suggestions = repo_research_suggestions(repo_docs)
    if not suggestions:
        return []
    query = suggestions[0]
    results = semantic_scholar_search(query, limit)
    if len(results) < limit:
        seen = {normalize(r.get("title", "")) for r in results}
        for item in crossref_search(query, limit):
            key = normalize(item.get("title", ""))
            if key not in seen:
                results.append(item)
                seen.add(key)
            if len(results) >= limit:
                break
    return results[:limit]


def search_local_documents(query: str, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = []
    for d in docs:
        score = local_text_search_score(query, d.get("text", ""), d.get("title", ""))
        if score > 0:
            text = d.get("text", "")
            snippet = summarize(text, 2) if text else "Arquivo visual."
            scored.append({**d, "score": score, "snippet": snippet})
    return sorted(scored, key=lambda x: x["score"], reverse=True)[:12]


def find_local_similar_images(repo_docs: list[dict[str, Any]], reference_hash: str | None) -> list[dict[str, Any]]:
    if not reference_hash:
        return []
    out = []
    for d in repo_docs:
        img_hash = d.get("image_hash")
        if img_hash and img_hash != reference_hash:
            out.append({**d, "distance": hamming_distance(reference_hash, img_hash)})
    return sorted(out, key=lambda x: x["distance"])[:10]


def gather_corpus_profile(docs: list[dict[str, Any]]) -> dict[str, Any]:
    years = Counter()
    themes = Counter()
    methods = Counter()
    authors = Counter()
    countries = Counter()
    keywords = Counter()
    for d in docs:
        if d.get("year"):
            years[d["year"]] += 1
        for x in d.get("themes", []):
            themes[x] += 1
        methods[d.get("method", "Não identificado")] += 1
        for x in d.get("authors", []):
            authors[x] += 1
        for x in d.get("countries", []):
            countries[x] += 1
        for x in d.get("keywords", [])[:10]:
            keywords[x] += 1
    return {
        "years": years,
        "themes": themes,
        "methods": methods,
        "authors": authors,
        "countries": countries,
        "keywords": keywords,
    }


def similarities(docs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], Any]:
    if len(docs) < 2:
        return [], None
    texts = [f"{d.get('title','')} {d.get('summary','')} {' '.join(d.get('keywords',[]))} {' '.join(d.get('themes',[]))} {d.get('method','')} {' '.join(d.get('authors', []))}" for d in docs]
    if TfidfVectorizer and cosine_similarity:
        vec = TfidfVectorizer(max_features=1500, stop_words=list(STOPWORDS), ngram_range=(1, 2))
        mat = vec.fit_transform(texts)
        sim = cosine_similarity(mat)
    else:
        sim = np.eye(len(docs)) if np is not None else [[1 if i == j else 0 for j in range(len(docs))] for i in range(len(docs))]
    pairs = []
    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            score = float(sim[i][j]) if np is not None or TfidfVectorizer else float(sim[i][j])
            overlap_themes = sorted(set(docs[i].get("themes", [])) & set(docs[j].get("themes", [])))
            overlap_keywords = sorted(set(docs[i].get("keywords", [])) & set(docs[j].get("keywords", [])))[:6]
            same_method = docs[i].get("method") == docs[j].get("method") and docs[i].get("method") not in {"", "Não identificado"}
            if score >= 0.12 or overlap_themes or overlap_keywords or same_method:
                reasons = []
                if overlap_themes:
                    reasons.append("tema em comum: " + ", ".join(overlap_themes[:4]))
                if overlap_keywords:
                    reasons.append("palavras-chave comuns: " + ", ".join(overlap_keywords[:5]))
                if same_method:
                    reasons.append("mesma metodologia")
                if score >= 0.22:
                    reasons.append("proximidade textual alta")
                pairs.append({
                    "Documento A": docs[i].get("title", "Documento A"),
                    "Documento B": docs[j].get("title", "Documento B"),
                    "Similaridade": round(score, 3),
                    "Temas em comum": ", ".join(overlap_themes) if overlap_themes else "—",
                    "Palavras-chave em comum": ", ".join(overlap_keywords) if overlap_keywords else "—",
                    "Métodos": f"{docs[i].get('method')} / {docs[j].get('method')}",
                    "Leitura do algoritmo": " | ".join(reasons) if reasons else "Relação fraca"
                })
    pairs = sorted(pairs, key=lambda x: x["Similaridade"], reverse=True)
    return pairs[:40], sim


def network_figure(docs: list[dict[str, Any]], sim_matrix: Any):
    if go is None or nx is None or sim_matrix is None or len(docs) < 2:
        return None
    G = nx.Graph()
    for i, d in enumerate(docs):
        G.add_node(i, label=d.get("title", f"Doc {i+1}"))
    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            score = float(sim_matrix[i][j])
            if score >= 0.16:
                G.add_edge(i, j, weight=score)
    if not G.edges:
        return None
    pos = nx.spring_layout(G, seed=42, k=1.1)
    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]
        x1, y1 = pos[e[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    node_x, node_y, texts = [], [], []
    for n in G.nodes():
        x, y = pos[n]
        node_x.append(x)
        node_y.append(y)
        texts.append(G.nodes[n]["label"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=1), hoverinfo="none"))
    fig.add_trace(go.Scatter(x=node_x, y=node_y, mode="markers+text", text=[t[:24] for t in texts], textposition="top center", marker=dict(size=18), hovertext=texts, hoverinfo="text"))
    fig.update_layout(height=500, margin=dict(l=0, r=0, t=20, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


def register_search(query: str) -> None:
    email = st.session_state.current_user
    if not email or not query.strip():
        return
    user = st.session_state.users[email]
    hist = user.setdefault("search_history", [])
    hist.insert(0, {"query": query, "at": now()})
    user["search_history"] = hist[:20]
    persist()


def render_metric(label: str, value: Any, sub: str) -> None:
    st.markdown(
        f"""
        <div class='glass-card'>
            <div class='metric-label'>{label}</div>
            <div class='metric-value'>{value}</div>
            <div class='metric-sub'>{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_login() -> None:
    css()
    st.markdown("<div class='nebula-shell'>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.4, 1.4, 1.4])
    with col2:
        logo = microscope_svg()
        st.markdown(
            f"""
            <div class='glass-card' style='margin-top:3rem;'>
                <div class='nebula-logo-wrap'>
                    <div class='nebula-logo'><img src='data:image/svg+xml;base64,{logo}' width='30'/></div>
                    <div>
                        <div class='nebula-brand'>Nebula</div>
                        <div class='nebula-brand-sub'>Repositório acadêmico, busca inteligente e análise conectada.</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        tabs = st.tabs(["Entrar", "Criar conta"])
        with tabs[0]:
            email = st.text_input("E-mail", key="login_email")
            password = st.text_input("Senha", type="password", key="login_password")
            if st.button("Acessar Nebula", key="btn_login"):
                user = st.session_state.users.get(email)
                if user and user.get("password") == sha(password):
                    st.session_state.logged_in = True
                    st.session_state.current_user = email
                    st.session_state.page = "dashboard"
                    st.rerun()
                else:
                    st.error("E-mail ou senha inválidos.")
            st.caption("Conta demo: demo@nebula.ai | senha: demo123")
        with tabs[1]:
            name = st.text_input("Nome completo", key="signup_name")
            area = st.text_input("Área de pesquisa", key="signup_area")
            email2 = st.text_input("E-mail de acesso", key="signup_email")
            password2 = st.text_input("Senha", type="password", key="signup_password")
            bio = st.text_area("Descrição curta", key="signup_bio", height=90)
            if st.button("Criar conta", key="btn_signup"):
                if not (name.strip() and email2.strip() and password2.strip()):
                    st.warning("Preencha nome, e-mail e senha.")
                elif email2 in st.session_state.users:
                    st.warning("Este e-mail já existe.")
                else:
                    st.session_state.users[email2] = {
                        "name": name.strip(),
                        "password": sha(password2),
                        "area": area.strip(),
                        "bio": bio.strip(),
                        "search_history": [],
                    }
                    persist()
                    st.success("Conta criada. Entre com seu e-mail e senha.")
    st.markdown("</div>", unsafe_allow_html=True)


def render_nav_column() -> None:
    logo = microscope_svg()
    user = current_user()
    st.markdown(
        f"""
        <div class='nebula-sidebar'>
            <div class='nebula-logo-wrap'>
                <div class='nebula-logo'><img src='data:image/svg+xml;base64,{logo}' width='30'/></div>
                <div>
                    <div class='nebula-brand' style='font-size:2rem;'>Nebula</div>
                    <div class='nebula-brand-sub'>Busca acadêmica e análise conectada</div>
                </div>
            </div>
            <div class='glass-card' style='padding:.85rem .95rem; margin-bottom:.8rem;'>
                <div class='metric-label'>Usuário</div>
                <div style='font-size:1.05rem;font-weight:700;margin-top:.35rem'>{user.get('name','')}</div>
                <div class='tiny'>{user.get('area','')}</div>
            </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div class='nav-title'>Navegação</div>", unsafe_allow_html=True)
    for key, label in NAV:
        wrap_cls = "nav-active" if st.session_state.page == key else ""
        st.markdown(f"<div class='{wrap_cls}'>", unsafe_allow_html=True)
        if st.button(label, key=f"nav_{key}"):
            st.session_state.page = key
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='nav-title'>Sessão</div>", unsafe_allow_html=True)
    if st.button("Reanalisar base", key="reanalisar"):
        reanalyze_all()
        st.success("Base atualizada.")
    if st.button("Sair", key="logout"):
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_dashboard() -> None:
    docs = all_documents()
    repos = current_user_repos()
    profile = gather_corpus_profile(docs)
    hist = current_user().get("search_history", [])

    st.markdown("<div class='page-title'>Nebula</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>Interface lateral em liquid glass, repositório acadêmico e análise conectada em um único ambiente.</div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric("Repositórios", len(repos), "Pastas inteligentes disponíveis")
    with c2:
        render_metric("Arquivos", len(docs), "Documentos e imagens no sistema")
    with c3:
        render_metric("Análises", sum(1 for d in docs if d.get("summary")), "Arquivos com análise estruturada")
    with c4:
        render_metric("Temas", len(profile["themes"]), "Temas inferidos pelo algoritmo")

    a, b = st.columns(2)
    with a:
        st.markdown("<div class='glass-bar'></div>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Perfil de interesse do usuário</div>", unsafe_allow_html=True)
        if profile["themes"]:
            st.write(" ".join(f"<span class='chip'>{k}</span>" for k, _ in profile["themes"].most_common(8)), unsafe_allow_html=True)
        else:
            st.markdown("<div class='section-text'>Nenhum item disponível.</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Histórico recente</div>", unsafe_allow_html=True)
        if hist:
            for item in hist[:6]:
                st.markdown(f"<div class='res-item'><div class='doc-title'>{item['query']}</div><div class='doc-meta'>{item['at']}</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='section-text'>Ainda não há buscas registradas.</div>", unsafe_allow_html=True)
    with b:
        st.markdown("<div class='glass-bar'></div>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Pulso da base</div>", unsafe_allow_html=True)
        if profile["keywords"]:
            for k, v in profile["keywords"].most_common(12):
                st.markdown(f"<span class='chip'>{k} · {v}</span>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='section-text'>Nenhum item disponível.</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Métodos mais frequentes</div>", unsafe_allow_html=True)
        if profile["methods"]:
            for k, v in profile["methods"].most_common(8):
                st.markdown(f"<div class='res-item'><div class='doc-title'>{k}</div><div class='doc-meta'>{v} ocorrência(s)</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='section-text'>Nenhum item disponível.</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown("<div class='glass-bar'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Repositórios do sistema</div>", unsafe_allow_html=True)
    if repos:
        for slug, repo in repos.items():
            st.markdown(f"<div class='res-item'><div class='doc-title'>{repo.get('name','')}</div><div class='doc-meta'>{len(repo.get('documents', []))} arquivo(s) · {repo.get('description','')}</div></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='section-text'>Nenhum repositório criado ainda. Vá em Repositório para criar o primeiro.</div>", unsafe_allow_html=True)


def render_repository() -> None:
    repos = current_user_repos()
    st.markdown("<div class='page-title'>Repositório</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>Crie pastas acadêmicas, envie arquivos e gere análise automática por documento.</div>", unsafe_allow_html=True)

    with st.container(border=False):
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        c1, c2 = st.columns([1.2, 2])
        with c1:
            repo_name = st.text_input("Nome do repositório", key="repo_name")
        with c2:
            repo_desc = st.text_input("Descrição", key="repo_desc")
        if st.button("Criar repositório", key="create_repo"):
            if repo_name.strip():
                slug = slugify(repo_name)
                if slug not in repos:
                    repos[slug] = {"name": repo_name.strip(), "description": repo_desc.strip(), "created_at": now(), "documents": []}
                    user_repo_dir(slug)
                    persist()
                    st.success("Repositório criado.")
                    st.rerun()
                else:
                    st.warning("Já existe um repositório com esse nome.")
            else:
                st.warning("Digite um nome.")
        st.markdown("</div>", unsafe_allow_html=True)

    if not repos:
        st.info("Nenhum repositório disponível.")
        return

    for slug, repo in repos.items():
        with st.expander(f"{repo.get('name')} · {len(repo.get('documents', []))} arquivo(s)", expanded=False):
            st.caption(repo.get("description", ""))
            uploaded = st.file_uploader(
                f"Enviar arquivos para {repo.get('name')}",
                accept_multiple_files=True,
                key=f"up_{slug}",
                type=["pdf", "docx", "txt", "md", "csv", "xlsx", "xls", "png", "jpg", "jpeg", "webp"],
                label_visibility="collapsed",
            )
            if uploaded:
                target = user_repo_dir(slug)
                for up in uploaded:
                    file_path = target / up.name
                    file_path.write_bytes(up.read())
                    analysis = analyze_document(file_path)
                    repo["documents"].append({
                        "file_name": up.name,
                        "file_path": str(file_path),
                        "uploaded_at": now(),
                        "analysis": analysis,
                    })
                persist()
                st.success(f"{len(uploaded)} arquivo(s) adicionados com análise automática.")
                st.rerun()
            if repo.get("documents"):
                for idx, item in enumerate(repo["documents"]):
                    an = item.get("analysis", {})
                    title = an.get("title") or item.get("file_name")
                    meta = []
                    if an.get("year"):
                        meta.append(str(an["year"]))
                    if an.get("method"):
                        meta.append(an["method"])
                    if an.get("themes"):
                        meta.append(", ".join(an["themes"][:3]))
                    st.markdown(f"<div class='res-item'><div class='doc-title'>{title}</div><div class='doc-meta'>{' · '.join(meta)}</div><div class='doc-snippet'>{an.get('summary','')}</div></div>", unsafe_allow_html=True)
                    cols = st.columns([1,1,1,1])
                    with cols[0]:
                        if st.button("Reanalisar", key=f"rean_{slug}_{idx}"):
                            p = Path(item["file_path"])
                            if p.exists():
                                item["analysis"] = analyze_document(p)
                                persist()
                                st.success("Análise atualizada.")
                                st.rerun()
                    with cols[1]:
                        if Path(item["file_path"]).exists():
                            with open(item["file_path"], "rb") as fh:
                                st.download_button("Baixar", data=fh, file_name=item["file_name"], key=f"dl_{slug}_{idx}")
                    with cols[2]:
                        if st.button("Excluir", key=f"del_{slug}_{idx}"):
                            try:
                                Path(item["file_path"]).unlink(missing_ok=True)
                            except Exception:
                                pass
                            repo["documents"].pop(idx)
                            persist()
                            st.rerun()
                    with cols[3]:
                        if st.button("Usar na busca", key=f"use_{slug}_{idx}"):
                            st.session_state.last_query = title
                            st.session_state.page = "search"
                            st.rerun()
            else:
                st.caption("Ainda não há arquivos neste repositório.")


def render_search() -> None:
    docs = all_documents()
    st.markdown("<div class='page-title'>Pesquisa Inteligente</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>Busca unificada em documentos locais, artigos na internet e imagens semelhantes.</div>", unsafe_allow_html=True)

    query = st.text_input("Consulta", value=st.session_state.last_query, placeholder="Tema, artigo, autor, conceito ou objeto visual", key="smart_query")
    ref_doc_titles = [d.get("title", d.get("file_name", "")) for d in docs if d.get("extension") in {".png", ".jpg", ".jpeg", ".webp"}]
    selected_image = st.selectbox("Imagem local de referência", options=[""] + ref_doc_titles, index=0)

    if st.button("Pesquisar", key="run_search"):
        st.session_state.last_query = query
        register_search(query)

    if not query.strip() and not selected_image:
        st.info("Digite uma consulta ou selecione uma imagem local para busca semelhante.")
        return

    local_results = search_local_documents(query, docs) if query.strip() else []
    web_articles = semantic_scholar_search(query, 6) + crossref_search(query, 6) if query.strip() else []
    web_articles = sorted(web_articles, key=lambda x: (x.get("year") or 0, x.get("score") or 0), reverse=True)[:12]
    suggestions = build_query_suggestions(query or selected_image, docs)

    reference_hash = None
    if selected_image:
        for d in docs:
            if d.get("title") == selected_image:
                reference_hash = d.get("image_hash")
                break
    local_similar = find_local_similar_images(docs, reference_hash) if reference_hash else []
    web_images = commons_image_search(query or selected_image, 8)

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Sugestões de pesquisa</div>", unsafe_allow_html=True)
    st.write(" ".join(f"<span class='chip'>{s}</span>" for s in suggestions), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Resultados locais", "Artigos na internet", "Imagens semelhantes"])
    with tab1:
        if local_results:
            for item in local_results:
                st.markdown(f"<div class='res-item'><div class='doc-title'>{item.get('title')}</div><div class='doc-meta'>{item.get('year','')} · {', '.join(item.get('themes',[])[:3])}</div><div class='doc-snippet'>{item.get('snippet')}</div></div>", unsafe_allow_html=True)
        else:
            st.caption("Nenhum documento local coincidiu com a consulta.")
    with tab2:
        if web_articles:
            for item in web_articles:
                title = item.get("title", "Sem título")
                authors = item.get("authors", "")
                year = item.get("year", "")
                venue = item.get("venue", "")
                abstract = item.get("abstract", "") or "Resumo não disponível na fonte."
                link = item.get("url", "")
                st.markdown(f"<div class='res-item'><div class='doc-title'>{title}</div><div class='doc-meta'>{item.get('source')} · {authors} · {year} · {venue}</div><div class='doc-snippet'>{abstract[:700]}</div></div>", unsafe_allow_html=True)
                if link:
                    st.link_button("Abrir referência", link)
        else:
            st.caption("Nenhum artigo externo retornado. Confira sua conexão ou refine a consulta.")
    with tab3:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<div class='section-title'>Imagens locais semelhantes</div>", unsafe_allow_html=True)
            if local_similar:
                for item in local_similar:
                    st.markdown(f"<div class='res-item'><div class='doc-title'>{item.get('title')}</div><div class='doc-meta'>Distância visual: {item.get('distance')}</div></div>", unsafe_allow_html=True)
            else:
                st.caption("Nenhuma imagem semelhante encontrada nas pastas do usuário.")
        with c2:
            st.markdown("<div class='section-title'>Imagens da internet</div>", unsafe_allow_html=True)
            if web_images:
                for img in web_images:
                    st.markdown(f"<div class='res-item'><div class='doc-title'>{img.get('title')}</div></div>", unsafe_allow_html=True)
                    if img.get("thumb"):
                        st.image(img["thumb"], use_container_width=True)
                    if img.get("url"):
                        st.link_button("Abrir página", img["url"], key=f"img_{img.get('title')}")
            else:
                st.caption("Nenhuma imagem web retornada para a consulta.")


def render_analytics() -> None:
    docs = all_documents()
    st.markdown("<div class='page-title'>Análises</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>Leitura estruturada da base: ano, temas, autores, países e resumos inferidos.</div>", unsafe_allow_html=True)
    if not docs:
        st.info("Envie documentos no repositório para gerar análise.")
        return
    profile = gather_corpus_profile(docs)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric("Documentos", len(docs), "Itens analisados")
    with c2:
        render_metric("Autores", len(profile["authors"]), "Autores identificados")
    with c3:
        render_metric("Países", len(profile["countries"]), "Países inferidos")
    with c4:
        render_metric("Palavras-chave", len(profile["keywords"]), "Termos relevantes")

    if px and pd:
        top_years = pd.DataFrame(profile["years"].most_common(), columns=["Ano", "Quantidade"])
        top_themes = pd.DataFrame(profile["themes"].most_common(), columns=["Tema", "Quantidade"])
        top_methods = pd.DataFrame(profile["methods"].most_common(), columns=["Método", "Quantidade"])
        top_authors = pd.DataFrame(profile["authors"].most_common(12), columns=["Autor", "Quantidade"])

        a, b = st.columns(2)
        with a:
            if not top_years.empty:
                fig = px.bar(top_years.sort_values("Ano"), x="Ano", y="Quantidade", title="Distribuição por ano")
                fig.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem ano detectado ainda.")
        with b:
            if not top_themes.empty:
                fig = px.pie(top_themes, names="Tema", values="Quantidade", title="Distribuição por tema")
                fig.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem temas detectados.")

        a2, b2 = st.columns(2)
        with a2:
            if not top_methods.empty:
                fig = px.bar(top_methods, x="Método", y="Quantidade", title="Métodos detectados")
                fig.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
        with b2:
            if not top_authors.empty:
                fig = px.bar(top_authors, x="Quantidade", y="Autor", orientation="h", title="Autores mais recorrentes")
                fig.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

        if profile["countries"] and go:
            geo_rows = []
            for country, qtd in profile["countries"].most_common():
                meta = COUNTRIES.get(country)
                if meta:
                    geo_rows.append({"country": country, "qtd": qtd, "lat": meta["lat"], "lon": meta["lon"]})
            if geo_rows:
                geo = pd.DataFrame(geo_rows)
                fig = go.Figure(go.Scattergeo(
                    lon=geo["lon"], lat=geo["lat"], text=geo["country"] + " · " + geo["qtd"].astype(str),
                    mode="markers+text", textposition="top center", marker=dict(size=geo["qtd"] * 8)
                ))
                fig.update_geos(projection_type="orthographic", showland=True, landcolor="rgb(15,28,55)", showocean=True, oceancolor="rgb(4,13,28)")
                fig.update_layout(title="Mapa 3D estilizado de nacionalidade/afiliação detectada", height=520, paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

    st.markdown("<div class='section-title'>Resumo analítico da base</div>", unsafe_allow_html=True)
    theme_text = ", ".join(k for k, _ in profile["themes"].most_common(5)) or "sem temas predominantes"
    method_text = ", ".join(k for k, _ in profile["methods"].most_common(4))
    keyword_text = ", ".join(k for k, _ in profile["keywords"].most_common(10))
    st.markdown(
        f"<div class='glass-card'><div class='doc-snippet'>A base atual concentra-se principalmente em <b>{theme_text}</b>. Os métodos mais recorrentes são <b>{method_text}</b>. Os termos mais frequentes indicam ênfase em <b>{keyword_text}</b>. O algoritmo também identificou padrões de autoria, periodicidade por ano e distribuição geográfica por afiliação ou referência institucional no corpo dos textos.</div></div>",
        unsafe_allow_html=True,
    )

    rows = []
    for d in docs:
        rows.append({
            "Título": d.get("title"),
            "Ano": d.get("year"),
            "Autores": ", ".join(d.get("authors", [])[:4]),
            "Tema": ", ".join(d.get("themes", [])[:3]),
            "Método": d.get("method"),
            "Países": ", ".join(d.get("countries", [])[:3]),
            "Resumo": d.get("summary", "")[:300],
        })
    if pd is not None:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_connections() -> None:
    docs = all_documents()
    st.markdown("<div class='page-title'>Conexões</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>Relações entre pesquisas semelhantes por texto, tema, método, autoria e palavras-chave.</div>", unsafe_allow_html=True)
    if len(docs) < 2:
        st.info("Adicione pelo menos dois documentos para gerar conexões.")
        return
    pairs, sim_matrix = similarities(docs)
    if pairs:
        st.markdown("<div class='section-title'>Pares conectados</div>", unsafe_allow_html=True)
        if pd is not None:
            st.dataframe(pd.DataFrame(pairs), use_container_width=True, hide_index=True)
        else:
            for p in pairs:
                st.write(p)
    else:
        st.caption("Ainda não surgiram conexões fortes entre os documentos.")

    fig = network_figure(docs, sim_matrix)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<div class='section-title'>Leitura de padrões em comum</div>", unsafe_allow_html=True)
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    if pairs:
        for item in pairs[:8]:
            st.markdown(
                f"<div class='res-item'><div class='doc-title'>{item['Documento A']} ↔ {item['Documento B']}</div><div class='doc-meta'>Similaridade {item['Similaridade']} · {item['Temas em comum']}</div><div class='doc-snippet'>{item['Leitura do algoritmo']}</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown("<div class='section-text'>Com mais documentos, o sistema mostrará blocos temáticos, interseções metodológicas e proximidade textual.</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_account() -> None:
    user = current_user()
    st.markdown("<div class='page-title'>Conta</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>Gerencie seus dados de acesso e o perfil de pesquisa.</div>", unsafe_allow_html=True)

    name = st.text_input("Nome", value=user.get("name", ""), key="acc_name")
    area = st.text_input("Área", value=user.get("area", ""), key="acc_area")
    bio = st.text_area("Bio", value=user.get("bio", ""), key="acc_bio", height=120)
    new_pass = st.text_input("Nova senha", value="", type="password", key="acc_pass")
    if st.button("Salvar alterações", key="acc_save"):
        email = st.session_state.current_user
        st.session_state.users[email]["name"] = name.strip()
        st.session_state.users[email]["area"] = area.strip()
        st.session_state.users[email]["bio"] = bio.strip()
        if new_pass.strip():
            st.session_state.users[email]["password"] = sha(new_pass)
        persist()
        st.success("Dados atualizados.")


def render_main() -> None:
    css()
    st.markdown("<div class='nebula-shell'>", unsafe_allow_html=True)
    left, right = st.columns([1.18, 4.12], gap="large")
    with left:
        render_nav_column()
    with right:
        page = st.session_state.page
        if page == "dashboard":
            render_dashboard()
        elif page == "search":
            render_search()
        elif page == "repository":
            render_repository()
        elif page == "analytics":
            render_analytics()
        elif page == "connections":
            render_connections()
        elif page == "account":
            render_account()
    st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    ensure_defaults()
    if not st.session_state.logged_in:
        render_login()
    else:
        render_main()


if __name__ == "__main__":
    main()
