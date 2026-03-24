import os
import io
import re
import json
import math
import base64
import secrets
import hashlib
import zipfile
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
    from cryptography.fernet import Fernet
except Exception:
    Fernet = None

try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    import PyPDF2
except Exception:
    PyPDF2 = None

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="Nebula Research",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DB_FILE = "nebula_research_secure_db.json"
APP_SCHEMA_VERSION = 4
MAX_TEXT_CHARS = 80000

STOPWORDS = {
    "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "é", "com", "uma", "os", "no", "se",
    "na", "por", "mais", "as", "dos", "como", "mas", "foi", "ao", "ele", "das", "tem", "à", "seu", "sua",
    "ou", "ser", "muito", "também", "já", "entre", "sobre", "após", "antes", "durante", "cada", "esse", "essa",
    "isso", "estes", "essas", "this", "be", "or", "by", "from", "an", "at", "we", "our", "their", "into",
    "using", "use", "used", "the", "of", "and", "to", "in", "is", "it", "that", "for", "on", "as", "with",
    "are", "between", "after", "before", "during", "were", "was", "has", "have", "had", "been", "will",
    "would", "could", "should", "may", "might", "shall", "não", "ser", "ter", "fazer", "poder", "dever",
    "estar", "ir", "ver", "dar", "vir", "querer", "saber", "quando", "onde", "como", "porque", "quem", "qual",
    "quanto", "todo", "todos", "toda", "todas", "mesmo", "mesma", "seus", "suas", "meu", "minha", "nosso",
    "nossa", "ela", "eles", "elas", "eu", "você", "nos", "their", "which", "whose", "there", "here",
}

TOPIC_RULES = {
    "Inteligência Artificial": ["ia", "ai", "machine learning", "deep learning", "rede neural", "transformer", "gpt", "bert", "llm", "algoritmo", "visão computacional"],
    "Museologia": ["museu", "museologia", "acervo", "coleção", "patrimônio", "documentação", "preservação", "museal", "curadoria", "exposição"],
    "Ciência de Dados": ["dados", "estatística", "análise", "modelo preditivo", "cluster", "classificação", "regressão", "dashboard", "visualização"],
    "Computação": ["python", "software", "sistema", "api", "código", "programação", "arquitetura", "cloud", "backend", "frontend"],
    "Educação": ["aprendizagem", "ensino", "estudante", "currículo", "pedagogia", "didática", "escola"],
    "Psicologia": ["psicologia", "emoção", "cognição", "ansiedade", "atenção", "comportamento"],
    "Biomedicina": ["célula", "gene", "proteína", "biologia", "biomédica", "genoma", "ensaio clínico"],
    "Engenharia": ["engenharia", "estrutura", "material", "circuito", "eletrônica", "mecânica"],
    "Direito": ["direito", "lei", "jurídico", "contrato", "norma", "legislação"],
    "Economia": ["economia", "mercado", "inflação", "pib", "investimento", "fiscal", "monetária"],
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
# CSS
# ============================================================
def inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        :root {
            --bg: #030713;
            --bg2: #07111f;
            --glass: rgba(255,255,255,0.06);
            --glass-border: rgba(147,197,253,0.16);
            --text: #eef2ff;
            --muted: #94a3c0;
            --blue: #60a5fa;
            --cyan: #67e8f9;
            --green: #4ade80;
            --purple: #c084fc;
            --yellow: #facc15;
        }
        * { box-sizing:border-box; }
        html, body, [class*="css"] { font-family:'Inter', sans-serif; color:var(--text); }
        .stApp {
            background:
                radial-gradient(circle at 15% 10%, rgba(96,165,250,.18), transparent 26%),
                radial-gradient(circle at 85% 8%, rgba(103,232,249,.12), transparent 22%),
                radial-gradient(circle at 60% 90%, rgba(59,130,246,.10), transparent 26%),
                linear-gradient(135deg, #030713 0%, #08111f 40%, #020811 100%);
            background-size: 180% 180%;
            animation: gradientShift 18s ease infinite;
        }
        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        .block-container { max-width: 1400px; padding-top: 0.8rem; }
        #MainMenu, footer, header { visibility:hidden; }
        section[data-testid="stSidebar"] { display:none !important; }
        .glass, .glass-sm {
            border-radius: 24px;
            border: 1px solid var(--glass-border);
            background: linear-gradient(135deg, rgba(255,255,255,.06), rgba(255,255,255,.03));
            backdrop-filter: blur(18px) saturate(150%);
            -webkit-backdrop-filter: blur(18px) saturate(150%);
            box-shadow: 0 20px 45px rgba(2,8,23,.22), inset 0 1px 0 rgba(255,255,255,.06);
            padding: 1rem 1.1rem;
            margin-bottom: 1rem;
        }
        .glass-sm { padding: .8rem .9rem; border-radius: 18px; }
        .page-title {
            font-size: 1.8rem; font-weight: 800; letter-spacing: -.03em; color: #f8fafc;
            margin-bottom: .25rem;
        }
        .page-sub { color: var(--muted); margin-bottom: 1rem; }
        .section-title { font-size: 1rem; font-weight: 700; margin-bottom: .9rem; color: #dbeafe; }
        .metric-card {
            border-radius: 20px; padding: 1rem; min-height: 100px;
            border: 1px solid rgba(255,255,255,.08);
            background: linear-gradient(135deg, rgba(255,255,255,.06), rgba(255,255,255,.03));
            box-shadow: 0 12px 28px rgba(2,8,23,.18);
        }
        .metric-card.blue { border-color: rgba(96,165,250,.22); }
        .metric-card.cyan { border-color: rgba(103,232,249,.22); }
        .metric-card.green { border-color: rgba(74,222,128,.22); }
        .metric-card.purple { border-color: rgba(192,132,252,.22); }
        .metric-card.yellow { border-color: rgba(250,204,21,.22); }
        .metric-label { color: var(--muted); font-size: .78rem; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
        .metric-value { font-size: 1.75rem; font-weight: 800; margin-top: .25rem; color: #f8fafc; }
        .metric-desc { font-size: .78rem; color: #bfd7ff; }
        .privacy-pill, .tag, .chain-badge, .user-chip {
            display:inline-block; border-radius:999px; padding:.22rem .58rem; font-size:.76rem; margin:.12rem .18rem .12rem 0;
            background: rgba(96,165,250,.10); color:#dbeafe; border:1px solid rgba(96,165,250,.18);
        }
        .privacy-pill { font-weight: 700; }
        .chain-badge { background: rgba(148,163,184,.08); border-color: rgba(148,163,184,.14); }
        .doc-card, .doc-mini, .article-card {
            border-radius: 18px;
            padding: .85rem .95rem;
            margin-bottom: .75rem;
            background: linear-gradient(135deg, rgba(255,255,255,.05), rgba(96,165,250,.04));
            border: 1px solid rgba(148,163,184,.14);
        }
        .article-title { font-weight:700; color:#bfdbfe; margin-bottom:.2rem; }
        .article-meta, .small-muted { color: var(--muted); font-size: .8rem; }
        .article-abstract, .chat-text { color:#dbeafe; font-size:.84rem; line-height:1.45; }
        .notice-box, .insight-box {
            border-radius: 16px; padding: .85rem 1rem; color:#dbeafe; margin:.65rem 0;
            background: linear-gradient(135deg, rgba(96,165,250,.10), rgba(103,232,249,.04));
            border: 1px solid rgba(96,165,250,.18);
        }
        .soft-table { width:100%; font-size:.84rem; color:#dbeafe; margin-top:.45rem; }
        .soft-table td { padding:.34rem .3rem; border-bottom:1px solid rgba(148,163,184,.08); }
        .sim-bar-wrap { width:100%; height:10px; border-radius:999px; background: rgba(148,163,184,.12); overflow:hidden; margin:.25rem 0 .45rem; }
        .sim-bar-fill { height:100%; border-radius:999px; background: linear-gradient(90deg, #60a5fa, #67e8f9); }
        .chat-shell { max-height: 420px; overflow-y:auto; padding-right:.25rem; }
        .chat-bubble {
            border-radius: 18px; padding: .75rem .9rem; margin-bottom: .65rem; max-width: 90%;
            background: linear-gradient(135deg, rgba(255,255,255,.05), rgba(255,255,255,.03));
            border: 1px solid rgba(148,163,184,.12);
        }
        .chat-bubble.me {
            margin-left:auto;
            background: linear-gradient(135deg, rgba(96,165,250,.14), rgba(103,232,249,.05));
            border-color: rgba(96,165,250,.18);
        }
        .chat-meta { display:flex; justify-content:space-between; gap:.8rem; color:#94a3c0; font-size:.74rem; margin-bottom:.35rem; }
        .nebula-nav {
            position: sticky; top: 0; z-index: 1000; margin-bottom: 1rem; padding: .7rem .9rem;
            display:flex; align-items:center; justify-content:space-between; gap:1rem;
            background: rgba(2,8,23,.72); border:1px solid rgba(255,255,255,.06); border-radius:24px;
            backdrop-filter: blur(18px);
        }
        .nebula-logo {
            font-weight:800; letter-spacing:-.03em; font-size:1.1rem;
            background: linear-gradient(135deg, #60a5fa, #67e8f9, #93c5fd);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
        }
        .nav-user { color:#dbeafe; font-size:.85rem; }
        .auth-logo-big {
            font-size: 2.2rem; font-weight: 800; text-align:center; letter-spacing:-.04em;
            background: linear-gradient(135deg, #60a5fa, #67e8f9, #dbeafe);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
        }
        .auth-sub { text-align:center; color:#94a3c0; margin-top:.35rem; }
        div[data-testid="stButton"] > button {
            border-radius: 16px !important;
            border: 1px solid rgba(147,197,253,.18) !important;
            background: linear-gradient(135deg, rgba(255,255,255,.06), rgba(255,255,255,.03)) !important;
            color: #eef2ff !important;
            backdrop-filter: blur(14px) !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,.06), 0 12px 24px rgba(2,8,23,.16);
        }
        div[data-testid="stButton"] > button[kind="primary"] {
            background: linear-gradient(135deg, rgba(59,130,246,.32), rgba(103,232,249,.14)) !important;
        }
        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
            border-radius: 16px !important;
            background: rgba(255,255,255,.05) !important;
            color:#eef2ff !important;
            border: 1px solid rgba(148,163,184,.18) !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap:.35rem;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 14px; padding: .5rem .9rem; background: rgba(255,255,255,.04);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# ENCRYPTED STORAGE
# ============================================================
def hash_password(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def generate_master_secret() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8")


def _fernet_from_seed(seed_text: str):
    if Fernet is None:
        return None
    seed = hashlib.sha256(seed_text.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(seed)
    return Fernet(key)


def global_fernet():
    secret = st.session_state.get("master_secret") or generate_master_secret()
    return _fernet_from_seed(f"nebula-global::{secret}")


def user_fernet(email: str):
    secret = st.session_state.get("master_secret") or generate_master_secret()
    user = st.session_state.get("users", {}).get(email, {})
    return _fernet_from_seed(f"nebula-user::{secret}::{email}::{user.get('password','')}")


def encrypt_payload(payload, email: str | None = None) -> str:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    f = user_fernet(email) if email else global_fernet()
    if f is None:
        return base64.urlsafe_b64encode(raw).decode("utf-8")
    return f.encrypt(raw).decode("utf-8")


def decrypt_payload(token: str | None, email: str | None = None, default=None):
    if default is None:
        default = {}
    if not token:
        return default
    candidates = []
    try:
        candidates.append(user_fernet(email) if email else global_fernet())
    except Exception:
        pass
    candidates.append(None)
    for f in candidates:
        try:
            if f is None:
                raw = base64.urlsafe_b64decode(str(token).encode("utf-8"))
            else:
                raw = f.decrypt(str(token).encode("utf-8"))
            return json.loads(raw.decode("utf-8"))
        except Exception:
            continue
    return default


def default_users() -> dict:
    return {
        "demo@nebula.ai": {
            "name": "Usuário Demo",
            "password": hash_password("demo123"),
            "research": "Inteligência Artificial aplicada à análise de documentos",
            "profile_visibility": "Conexões",
            "privacy_mode": "Criptografado",
        }
    }


def empty_workspace() -> dict:
    return {"repository": [], "search_history": [], "user_interest": {}}


def load_db() -> dict:
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def persist_current_workspace() -> None:
    owner = st.session_state.get("active_workspace_owner")
    if not owner or owner != st.session_state.get("current_user"):
        return
    payload = {
        "repository": st.session_state.get("repository", []),
        "search_history": st.session_state.get("search_history", []),
        "user_interest": st.session_state.get("user_interest", {}),
    }
    st.session_state.workspaces[owner] = encrypt_payload(payload, email=owner)


def save_db() -> None:
    persist_current_workspace()
    blob = {
        "users": st.session_state.users,
        "workspaces": st.session_state.workspaces,
        "community_messages_enc": encrypt_payload(st.session_state.community_messages),
        "meta": {
            "schema_version": APP_SCHEMA_VERSION,
            "master_secret": st.session_state.master_secret,
            **(st.session_state.get("db_meta", {}) or {}),
        },
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(blob, f, ensure_ascii=False, indent=2)


def clear_active_workspace() -> None:
    st.session_state.repository = []
    st.session_state.search_history = []
    st.session_state.user_interest = {}
    st.session_state.active_workspace_owner = None


def initialize_user_workspace(email: str) -> None:
    if email not in st.session_state.workspaces:
        st.session_state.workspaces[email] = encrypt_payload(empty_workspace(), email=email)


def load_workspace_for_user(email: str) -> None:
    clear_active_workspace()
    initialize_user_workspace(email)
    payload = decrypt_payload(st.session_state.workspaces.get(email), email=email, default=empty_workspace())
    if not isinstance(payload, dict):
        payload = empty_workspace()
    st.session_state.repository = payload.get("repository", []) or []
    st.session_state.search_history = payload.get("search_history", []) or []
    st.session_state.user_interest = payload.get("user_interest", {}) or {}
    st.session_state.active_workspace_owner = email


def login_user(email: str) -> None:
    st.session_state.logged_in = True
    st.session_state.current_user = email
    st.session_state.page = "Dashboard"
    st.session_state.quick_query = ""
    load_workspace_for_user(email)


def logout_user() -> None:
    persist_current_workspace()
    st.session_state.logged_in = False
    st.session_state.current_user = None
    st.session_state.page = "Dashboard"
    st.session_state.quick_query = ""
    clear_active_workspace()


def migrate_legacy_data(db: dict, users: dict, workspaces: dict) -> tuple[dict, dict]:
    if workspaces:
        return workspaces, db.get("meta", {}) or {}
    meta = db.get("meta", {}) or {}
    legacy_repo = db.get("repository", []) or []
    legacy_history = db.get("search_history", []) or []
    legacy_interest = db.get("user_interest", {}) or {}
    if not legacy_repo and not legacy_history and not legacy_interest:
        return workspaces, meta
    payload = {
        "repository": legacy_repo,
        "search_history": legacy_history,
        "user_interest": legacy_interest if isinstance(legacy_interest, dict) else {},
    }
    real_users = [u for u in users if u != "demo@nebula.ai"]
    if len(real_users) == 1:
        workspaces[real_users[0]] = encrypt_payload(payload, email=real_users[0])
    elif len(users) == 1:
        owner = list(users.keys())[0]
        workspaces[owner] = encrypt_payload(payload, email=owner)
    else:
        meta["legacy_workspace_orphan"] = encrypt_payload(payload)
    return workspaces, meta


def init_state() -> None:
    db = load_db()
    users = db.get("users") or default_users()
    meta = db.get("meta") or {}
    workspaces = db.get("workspaces") or {}

    st.session_state.setdefault("master_secret", meta.get("master_secret") or generate_master_secret())
    st.session_state.setdefault("users", users)
    st.session_state.setdefault("db_meta", meta)
    st.session_state.setdefault("workspaces", workspaces)

    if not st.session_state.workspaces:
        migrated_workspaces, migrated_meta = migrate_legacy_data(db, st.session_state.users, {})
        st.session_state.workspaces = migrated_workspaces
        st.session_state.db_meta = migrated_meta

    community = decrypt_payload(db.get("community_messages_enc", ""), default=[])
    if not isinstance(community, list):
        community = db.get("community_messages", []) or []

    st.session_state.setdefault("community_messages", community)
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("current_user", None)
    st.session_state.setdefault("active_workspace_owner", None)
    st.session_state.setdefault("page", "Dashboard")
    st.session_state.setdefault("repository", [])
    st.session_state.setdefault("search_history", [])
    st.session_state.setdefault("user_interest", {})
    st.session_state.setdefault("quick_query", "")

    if st.session_state.logged_in and st.session_state.current_user:
        load_workspace_for_user(st.session_state.current_user)


# ============================================================
# TEXT UTILITIES
# ============================================================
def normalize_text(text: str) -> str:
    if not text:
        return ""
    repl = {
        "á": "a", "à": "a", "â": "a", "ã": "a", "ä": "a", "é": "e", "ê": "e", "è": "e", "ë": "e",
        "í": "i", "ì": "i", "î": "i", "ï": "i", "ó": "o", "ò": "o", "ô": "o", "õ": "o", "ö": "o",
        "ú": "u", "ù": "u", "û": "u", "ü": "u", "ç": "c"
    }
    out = []
    for ch in str(text).lower():
        out.append(repl.get(ch, ch))
    return re.sub(r"\s+", " ", "".join(out)).strip()


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-zA-ZÀ-ÿ0-9\-]{3,}", str(text).lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


def extract_keywords_tfidf(text: str, top_n: int = 20) -> list[str]:
    if not text:
        return []
    words = tokenize(text)
    if not words:
        return []
    tf = Counter(words)
    total = sum(tf.values()) or 1
    sentences = re.split(r"(?<=[.!?])\s+", str(text))
    sentence_presence = defaultdict(int)
    for sent in sentences:
        for word in set(tokenize(sent)):
            sentence_presence[word] += 1
    scores = {}
    for word, count in tf.items():
        tf_score = count / total
        spread = math.log(1 + sentence_presence[word])
        length_bonus = min(len(word) / 10.0, 1.2)
        scores[word] = tf_score * spread * length_bonus
    return [w for w, _ in sorted(scores.items(), key=lambda x: -x[1])[:top_n]]


def summarize_extractive(text: str, max_sentences: int = 4) -> str:
    if not text:
        return "Sem conteúdo disponível."
    text = re.sub(r"\n+", " ", str(text)).strip()
    if len(text) < 180:
        return text[:700]
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) > 5]
    if not sentences:
        return text[:700]
    freq = Counter(tokenize(text))
    total = sum(freq.values()) or 1
    for key in list(freq.keys()):
        freq[key] = freq[key] / total
    scored = []
    for i, sent in enumerate(sentences):
        words = tokenize(sent)
        if not words:
            continue
        score = sum(freq.get(w, 0) for w in words) / len(words)
        if i < 3:
            score *= 1.35
        if len(words) < 8:
            score *= 0.6
        scored.append((score, sent))
    top = {s for _, s in sorted(scored, reverse=True)[:max_sentences]}
    ordered = [s for s in sentences if s in top][:max_sentences]
    return " ".join(ordered)[:1200]


def detect_topic(text: str, fallback: str = "Pesquisa Geral") -> str:
    t = normalize_text(text)
    scores = {}
    for topic, terms in TOPIC_RULES.items():
        scores[topic] = sum(2 for term in terms if normalize_text(term) in t)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else fallback


def detect_years(text: str) -> list[int]:
    years = [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", str(text))]
    return sorted(set(y for y in years if 1900 <= y <= datetime.now().year + 2))


def infer_nationality(text: str) -> str:
    t = normalize_text(text)
    for country in NATIONALITY_COORDS:
        if normalize_text(country) in t:
            return country
    return "Brasil"


def extract_author_from_text(text: str) -> str:
    patterns = [
        r"(?:author|autor|autores|authors)[:\s]+([A-ZÀ-ÿ][A-Za-zÀ-ÿ\s,\.]{5,80})",
        r"(?:by|por)\s+([A-ZÀ-ÿ][A-Za-zÀ-ÿ\s]{5,60})",
        r"\b([A-Z][a-zà-ÿ]+(?:\s+[A-Z][a-zà-ÿ]+){1,3})\s*\n",
    ]
    for pattern in patterns:
        match = re.search(pattern, str(text), re.I)
        if match:
            candidate = match.group(1).strip()
            if 5 < len(candidate) < 80:
                return candidate
    return "Desconhecido"


def detect_document_language(text: str) -> str:
    t = f" {str(text).lower()} "
    pt_markers = [" que ", " não ", " para ", " com ", " uma ", " dos ", " das ", " pelo "]
    en_markers = [" the ", " and ", " this ", " that ", " with ", " from ", " abstract "]
    pt_score = sum(1 for m in pt_markers if m in t)
    en_score = sum(1 for m in en_markers if m in t)
    return "Português" if pt_score >= en_score else "Inglês"


def analyze_document_structure(text: str) -> dict:
    section_patterns = {
        "Resumo/Abstract": r"(?:resumo|abstract)\s*[\:\n](.{80,2200}?)(?=\n[A-ZÁÀÂÃÉÍÓÚ]|\nintrodução|\nintroduction|keywords|palavras)",
        "Introdução": r"(?:introdução|introduction)\s*[\:\n](.{80,2200}?)(?=\n[A-ZÁÀÂÃÉÍÓÚ]|\nmétodo|\nmethod)",
        "Metodologia": r"(?:método|metodologia|methodology|methods)\s*[\:\n](.{80,2200}?)(?=\n[A-ZÁÀÂÃÉÍÓÚ]|\nresultados|\nresults)",
        "Resultados": r"(?:resultados|results)\s*[\:\n](.{80,2200}?)(?=\n[A-ZÁÀÂÃÉÍÓÚ]|\ndiscussão|\nconclusão)",
        "Conclusão": r"(?:conclusão|conclusion)\s*[\:\n](.{80,2600}?)(?=\n[A-ZÁÀÂÃÉÍÓÚ]|\nreferência|$)",
    }
    sections = {}
    for name, pattern in section_patterns.items():
        match = re.search(pattern, str(text), re.I | re.S)
        if match:
            sections[name] = match.group(1).strip()[:650]
    return sections


def compute_readability(text: str) -> dict:
    words = re.findall(r"\w+", str(text))
    sentences = [s for s in re.split(r"[.!?]+", str(text)) if len(s.split()) > 3]
    if not words or not sentences:
        return {"clarity": 50, "words": 0, "sentences": 0, "estimated_pages": 0, "reading_time_min": 0}
    avg_words_per_sent = len(words) / max(len(sentences), 1)
    avg_syllables = sum(max(1, len(re.findall(r"[aeiouáéíóúàèìòùãõâêîôû]", w.lower()))) for w in words) / max(len(words), 1)
    score = 100 - (1.015 * avg_words_per_sent) - (84.6 * avg_syllables)
    score = max(0, min(100, score))
    return {
        "clarity": round(score, 1),
        "words": len(words),
        "sentences": len(sentences),
        "avg_words_per_sentence": round(avg_words_per_sent, 1),
        "estimated_pages": max(1, round(len(words) / 300)) if len(words) else 0,
        "reading_time_min": max(1, round(len(words) / 200)) if len(words) else 0,
    }


def cosine_similarity(text_a: str, text_b: str) -> float:
    ta = Counter(tokenize(text_a))
    tb = Counter(tokenize(text_b))
    if not ta or not tb:
        return 0.0
    keys = set(ta) | set(tb)
    dot = sum(ta[k] * tb[k] for k in keys)
    na = math.sqrt(sum(v * v for v in ta.values()))
    nb = math.sqrt(sum(v * v for v in tb.values()))
    if not na or not nb:
        return 0.0
    return round(dot / (na * nb), 4)


def score_relevance(query: str, text: str, keywords: list[str]) -> float:
    q_terms = set(tokenize(query))
    if not q_terms:
        return 0.0
    doc_terms = set(tokenize(text)) | set(keywords)
    inter = len(q_terms & doc_terms)
    union = len(q_terms | doc_terms) or 1
    return round((inter / union) * 100, 2)


def safe_top_value(series, default: str = "N/A") -> str:
    try:
        s = pd.Series(series).dropna()
        if s.empty:
            return default
        s = s.astype(str).str.strip()
        s = s[s != ""]
        if s.empty:
            return default
        counts = s.value_counts()
        return counts.index[0] if not counts.empty else default
    except Exception:
        return default


# ============================================================
# FILE ANALYSIS
# ============================================================
def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    text_parts = []
    if pdfplumber is not None:
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages[:40]:
                    page_text = page.extract_text() or ""
                    if page_text:
                        text_parts.append(page_text)
            if text_parts:
                return "\n".join(text_parts)[:MAX_TEXT_CHARS]
        except Exception:
            pass
    if PyPDF2 is not None:
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages[:40]:
                try:
                    page_text = page.extract_text() or ""
                    if page_text:
                        text_parts.append(page_text)
                except Exception:
                    pass
            if text_parts:
                return "\n".join(text_parts)[:MAX_TEXT_CHARS]
        except Exception:
            pass
    return ""


def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
        text = re.sub(r"<w:t[^>]*>", "\n", xml)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text)
        return text[:MAX_TEXT_CHARS]
    except Exception:
        return ""


def analyze_tabular_file(file_bytes: bytes, suffix: str) -> dict:
    frames = []
    sheet_names = []
    try:
        if suffix == "csv":
            df = pd.read_csv(io.BytesIO(file_bytes))
            frames = [("CSV", df)]
        else:
            sheets = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
            for name, df in list(sheets.items())[:4]:
                frames.append((str(name), df))
            sheet_names = [name for name, _ in frames]
    except Exception:
        return {"summary": "", "profile": {}}

    desc = []
    profile = {"sheets": [], "numeric_columns": 0, "text_columns": 0, "rows": 0, "cols": 0}
    for name, df in frames:
        local = df.copy()
        num_cols = list(local.select_dtypes(include=[np.number]).columns)
        txt_cols = [c for c in local.columns if c not in num_cols]
        profile["rows"] += int(len(local))
        profile["cols"] = max(profile["cols"], int(len(local.columns)))
        profile["numeric_columns"] += len(num_cols)
        profile["text_columns"] += len(txt_cols)
        profile["sheets"].append({
            "name": name,
            "rows": int(len(local)),
            "cols": int(len(local.columns)),
            "numeric_columns": len(num_cols),
            "text_columns": len(txt_cols),
        })
        desc.append(f"Planilha/aba '{name}' com {len(local)} linhas e {len(local.columns)} colunas.")
        desc.append(f"Colunas principais: {', '.join(str(c) for c in local.columns[:20])}")
        for col in num_cols[:6]:
            sample = local[col].dropna()
            if not sample.empty:
                desc.append(f"Coluna '{col}': média={sample.mean():.2f}, mínimo={sample.min():.2f}, máximo={sample.max():.2f}")
        desc.append("Amostra dos dados:\n" + local.head(12).astype(str).to_string(index=False))
    if sheet_names:
        profile["sheet_names"] = sheet_names
    return {"summary": "\n".join(desc)[:MAX_TEXT_CHARS], "profile": profile}


def analyze_image_bytes(file_bytes: bytes) -> dict:
    try:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        arr = np.array(img)
        mean_rgb = arr.reshape(-1, 3).mean(axis=0)
        brightness = float(np.mean(np.dot(arr[..., :3], [0.299, 0.587, 0.114])))
        gray = np.array(img.convert("L")) / 255.0
        gx = np.abs(np.diff(gray, axis=1)).mean() if gray.shape[1] > 1 else 0
        gy = np.abs(np.diff(gray, axis=0)).mean() if gray.shape[0] > 1 else 0
        edge_density = float((gx + gy) / 2)
        aspect_ratio = round(img.width / max(img.height, 1), 2)
        orientation = "Horizontal" if aspect_ratio > 1.15 else "Vertical" if aspect_ratio < 0.85 else "Quadrada"
        detail_level = "Alta" if edge_density > 0.11 else "Média" if edge_density > 0.05 else "Baixa"
        palette = arr.reshape(-1, 3)
        palette_sample = palette[np.linspace(0, len(palette) - 1, min(len(palette), 2000), dtype=int)] if len(palette) else palette
        unique_colors = np.unique((palette_sample // 32) * 32, axis=0)[:6] if len(palette_sample) else []
        palette_tags = [f"rgb({int(c[0])},{int(c[1])},{int(c[2])})" for c in unique_colors]
        return {
            "width": int(img.width),
            "height": int(img.height),
            "brightness": round(brightness, 2),
            "r": round(float(mean_rgb[0]), 1),
            "g": round(float(mean_rgb[1]), 1),
            "b": round(float(mean_rgb[2]), 1),
            "aspect_ratio": aspect_ratio,
            "orientation": orientation,
            "edge_density": round(edge_density, 4),
            "detail_level": detail_level,
            "palette_tags": palette_tags,
        }
    except Exception:
        return {}


def read_text_by_suffix(file_name: str, file_bytes: bytes) -> str:
    suffix = file_name.lower().split(".")[-1] if "." in file_name else ""
    if suffix == "pdf":
        return extract_text_from_pdf_bytes(file_bytes)
    if suffix == "docx":
        return extract_text_from_docx(file_bytes)
    if suffix in {"txt", "md", "py", "json"}:
        try:
            return file_bytes.decode("utf-8", errors="ignore")[:MAX_TEXT_CHARS]
        except Exception:
            return ""
    if suffix in {"csv", "xlsx", "xls"}:
        return analyze_tabular_file(file_bytes, suffix).get("summary", "")
    return ""


def file_kind(file_name: str) -> str:
    suffix = file_name.lower().split(".")[-1] if "." in file_name else ""
    mapping = {
        "pdf": "PDF", "docx": "Word", "txt": "Texto", "md": "Markdown", "csv": "Planilha", "xlsx": "Planilha", "xls": "Planilha",
        "png": "Imagem", "jpg": "Imagem", "jpeg": "Imagem", "webp": "Imagem", "py": "Código", "json": "JSON",
    }
    return mapping.get(suffix, "Arquivo")


def make_document_record(file_name: str, file_bytes: bytes) -> dict:
    suffix = file_name.lower().split(".")[-1] if "." in file_name else ""
    kind = file_kind(file_name)
    text = read_text_by_suffix(file_name, file_bytes)
    tabular_profile = {}
    image_meta = {}
    modality_notes = []

    if suffix in {"csv", "xlsx", "xls"}:
        table_info = analyze_tabular_file(file_bytes, suffix)
        text = table_info.get("summary", text)
        tabular_profile = table_info.get("profile", {})
        if tabular_profile:
            modality_notes.append(
                f"Estrutura tabular com {tabular_profile.get('rows', 0)} linhas, até {tabular_profile.get('cols', 0)} colunas e {tabular_profile.get('numeric_columns', 0)} colunas numéricas."
            )

    if kind == "Imagem":
        image_meta = analyze_image_bytes(file_bytes)
        if image_meta:
            modality_notes.append(
                f"Imagem {image_meta.get('orientation', 'desconhecida').lower()} com detalhe {image_meta.get('detail_level', 'desconhecido').lower()} e brilho médio {image_meta.get('brightness', 0):.1f}."
            )
            if image_meta.get("palette_tags"):
                modality_notes.append("Paleta dominante aproximada: " + ", ".join(image_meta.get("palette_tags", [])[:4]))

    keywords = extract_keywords_tfidf(text if text else file_name, top_n=25)
    summary = summarize_extractive(text, max_sentences=4) if text else f"Arquivo do tipo {kind}."
    topic = detect_topic(text if text else file_name)
    years = detect_years(text)
    nationality = infer_nationality(text if text else file_name)
    author = extract_author_from_text(text) if text else "Desconhecido"
    language = detect_document_language(text) if text else "Desconhecido"
    sections = analyze_document_structure(text) if text and kind in {"PDF", "Word", "Texto", "Markdown"} else {}
    readability = compute_readability(text) if text else {"clarity": 50, "words": 0, "sentences": 0, "estimated_pages": 0, "reading_time_min": 0}
    refs_match = re.findall(r"\[\d+\]|\d+\.\s+[A-ZÀ-ÿ][a-zà-ÿ]+", text[-3000:]) if text else []
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
        "size_kb": round(len(file_bytes) / 1024, 1),
        "sections": sections,
        "readability": readability,
        "ref_count": ref_count,
        "tabular_profile": tabular_profile,
        "image_meta": image_meta,
        "modality_notes": modality_notes,
    }


# ============================================================
# SEARCH AND CONNECTION HELPERS
# ============================================================
def current_user() -> dict:
    return st.session_state.users.get(st.session_state.get("current_user"), {})


def update_user_interest(email: str, terms: list[str]) -> None:
    if not email:
        return
    bag = st.session_state.get("user_interest", {}) or {}
    for term in terms:
        if len(term) >= 3:
            bag[term] = bag.get(term, 0) + 1
    st.session_state.user_interest = dict(sorted(bag.items(), key=lambda x: -x[1])[:60])


def recommend_terms(email: str, limit: int = 12) -> list[str]:
    if email != st.session_state.get("current_user"):
        payload = decrypt_payload(st.session_state.workspaces.get(email), email=email, default=empty_workspace())
        bag = payload.get("user_interest", {}) if isinstance(payload, dict) else {}
    else:
        bag = st.session_state.get("user_interest", {})
    return [term for term, _ in sorted(bag.items(), key=lambda x: -x[1])[:limit]]


def get_connected_users(email: str, limit: int = 8) -> list[dict]:
    if not email or email not in st.session_state.users:
        return []
    base_user = st.session_state.users.get(email, {})
    base_topic = detect_topic(base_user.get("research", ""), fallback="Pesquisa Geral")
    base_terms = recommend_terms(email, 18)
    base_text = " ".join([base_user.get("research", ""), " ".join(base_terms)])
    out = []
    for other_email, other_user in st.session_state.users.items():
        if other_email == email:
            continue
        other_topic = detect_topic(other_user.get("research", ""), fallback="Pesquisa Geral")
        other_terms = recommend_terms(other_email, 18)
        other_text = " ".join([other_user.get("research", ""), " ".join(other_terms)])
        sim = cosine_similarity(base_text, other_text)
        if base_topic == other_topic and base_topic != "Pesquisa Geral":
            sim += 0.16
        shared_terms = []
        for term in base_terms + extract_keywords_tfidf(base_user.get("research", ""), 8):
            if term in other_terms or term in tokenize(other_user.get("research", "")):
                if term not in shared_terms:
                    shared_terms.append(term)
        if sim > 0.05 or shared_terms or (base_topic == other_topic and base_topic != "Pesquisa Geral"):
            out.append({
                "email": other_email,
                "name": other_user.get("name", other_email),
                "research": other_user.get("research", ""),
                "topic": other_topic,
                "shared_terms": shared_terms[:8],
                "similarity": round(min(sim * 100, 99.0), 1),
                "visibility": other_user.get("profile_visibility", "Conexões"),
            })
    return sorted(out, key=lambda x: (-x["similarity"], x["name"]))[:limit]


def get_available_rooms(email: str) -> list[str]:
    rooms = []
    own_topic = detect_topic(st.session_state.users.get(email, {}).get("research", ""), fallback="Pesquisa Geral")
    if own_topic != "Pesquisa Geral":
        rooms.append(f"Tema · {own_topic}")
    for conn in get_connected_users(email, 12):
        if conn.get("topic") and conn["topic"] != "Pesquisa Geral":
            rooms.append(f"Tema · {conn['topic']}")
    rooms.append("Sala · Interdisciplinar")
    unique = []
    for room in rooms:
        if room not in unique:
            unique.append(room)
    return unique


def dm_thread_id(a: str, b: str) -> str:
    return "dm::" + "::".join(sorted([a, b]))


def post_chat_message(scope: str, target: str, text: str) -> bool:
    clean_text = (text or "").strip()
    if not clean_text:
        return False
    sender_email = st.session_state.current_user
    sender = current_user()
    message = {
        "id": hashlib.md5(f"{sender_email}-{scope}-{target}-{datetime.now().isoformat()}".encode()).hexdigest()[:12],
        "scope": scope,
        "sender_email": sender_email,
        "sender_name": sender.get("name", sender_email),
        "sender_topic": detect_topic(sender.get("research", ""), fallback="Pesquisa Geral"),
        "text": clean_text[:2400],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    if scope == "dm":
        message["thread_id"] = dm_thread_id(sender_email, target)
        message["participants"] = sorted([sender_email, target])
    else:
        message["room"] = target
    st.session_state.community_messages.append(message)
    save_db()
    return True


def get_dm_messages(peer_email: str) -> list[dict]:
    thread_id = dm_thread_id(st.session_state.current_user, peer_email)
    return [m for m in st.session_state.community_messages if m.get("scope") == "dm" and m.get("thread_id") == thread_id][-120:]


def get_room_messages(room: str, only_connections: bool = False) -> list[dict]:
    messages = [m for m in st.session_state.community_messages if m.get("scope") == "room" and m.get("room") == room]
    if only_connections:
        allowed = {st.session_state.current_user}
        allowed.update({u["email"] for u in get_connected_users(st.session_state.current_user, 50)})
        messages = [m for m in messages if m.get("sender_email") in allowed]
    return messages[-120:]


def build_recommendation_query(research: str, docs: list[dict], limit_terms: int = 8) -> str:
    research_terms = extract_keywords_tfidf(research, 8) if research else []
    repo_terms = []
    for doc in docs[:12]:
        repo_terms.extend(doc.get("keywords", [])[:4])
    merged = []
    for term in research_terms + repo_terms:
        if term and term not in merged:
            merged.append(term)
    return " ".join(merged[:limit_terms]) if merged else (research or "pesquisa acadêmica")


def local_search(query: str, docs: list[dict]) -> list[dict]:
    results = []
    for doc in docs:
        text = " ".join([doc.get("name", ""), doc.get("summary", ""), doc.get("topic", ""), " ".join(doc.get("keywords", [])), doc.get("text", "")[:4000]])
        score = score_relevance(query, text, doc.get("keywords", []))
        if score > 0:
            item = dict(doc)
            item["score"] = score
            results.append(item)
    return sorted(results, key=lambda x: (-x["score"], x["name"]))


def related_documents(target: dict, docs: list[dict], limit: int = 6) -> list[dict]:
    out = []
    target_text = " ".join([target.get("summary", ""), " ".join(target.get("keywords", [])), target.get("text", "")[:2000]])
    for doc in docs:
        if doc.get("id") == target.get("id"):
            continue
        doc_text = " ".join([doc.get("summary", ""), " ".join(doc.get("keywords", [])), doc.get("text", "")[:2000]])
        sim = cosine_similarity(target_text, doc_text)
        if doc.get("topic") == target.get("topic") and doc.get("topic"):
            sim += 0.1
        if sim > 0.05:
            item = dict(doc)
            item["similarity"] = round(sim * 100, 1)
            out.append(item)
    return sorted(out, key=lambda x: -x["similarity"])[:limit]


def recognize_research_intent(query: str) -> dict:
    q = normalize_text(query)
    topic = detect_topic(q)
    intent = "pesquisa bibliográfica"
    if any(term in q for term in ["imagem", "foto", "figura", "visual"]):
        intent = "busca visual"
    elif any(term in q for term in ["comparar", "conectar", "semelhante", "relacionar"]):
        intent = "conexão temática"
    elif any(term in q for term in ["analisar", "analise", "métricas", "tendência"]):
        intent = "análise"
    keywords = extract_keywords_tfidf(query, 12)
    suggestions = []
    for term in keywords + TOPIC_RULES.get(topic, [])[:5]:
        if term not in suggestions:
            suggestions.append(term)
    return {
        "intent": intent,
        "topic": topic,
        "keywords": keywords,
        "search_terms": suggestions[:12],
        "years": detect_years(q),
    }


def search_semantic_scholar(query: str, limit: int = 8) -> list[dict]:
    try:
        resp = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query": query, "limit": limit, "fields": "title,authors,year,abstract,venue,openAccessPdf,externalIds,citationCount"},
            timeout=12,
        )
        if resp.status_code != 200:
            return []
        out = []
        for item in resp.json().get("data", []):
            authors = ", ".join(a.get("name", "") for a in item.get("authors", [])[:4])
            doi = (item.get("externalIds") or {}).get("DOI", "")
            open_pdf = item.get("openAccessPdf") or {}
            url = open_pdf.get("url") or (f"https://doi.org/{doi}" if doi else "")
            kw_text = f"{item.get('title','')} {item.get('abstract','')}"
            out.append({
                "title": item.get("title", "Sem título"),
                "authors": authors or "Não informado",
                "year": item.get("year", "?"),
                "abstract": (item.get("abstract") or "")[:420],
                "source": item.get("venue", "Semantic Scholar"),
                "citations": item.get("citationCount", 0),
                "url": url,
                "keywords": extract_keywords_tfidf(kw_text, 8),
                "topic": detect_topic(kw_text),
            })
        return out
    except Exception:
        return []


def search_crossref(query: str, limit: int = 5) -> list[dict]:
    try:
        resp = requests.get(
            "https://api.crossref.org/works",
            params={"query": query, "rows": limit, "select": "title,author,issued,DOI,abstract,container-title,is-referenced-by-count", "mailto": "nebula@research.ai"},
            timeout=12,
        )
        if resp.status_code != 200:
            return []
        out = []
        for item in resp.json().get("message", {}).get("items", []):
            title = (item.get("title") or ["Sem título"])[0]
            authors = ", ".join(f"{a.get('given','')} {a.get('family','')}".strip() for a in item.get("author", [])[:4])
            year = None
            if item.get("issued", {}).get("date-parts"):
                year = item["issued"]["date-parts"][0][0]
            abstract = re.sub(r"<[^>]+>", " ", item.get("abstract", "") or "")[:420]
            doi = item.get("DOI", "")
            kw_text = f"{title} {abstract}"
            out.append({
                "title": title,
                "authors": authors or "Não informado",
                "year": year or "?",
                "abstract": abstract,
                "source": (item.get("container-title") or ["Crossref"])[0],
                "citations": item.get("is-referenced-by-count", 0),
                "url": f"https://doi.org/{doi}" if doi else "",
                "keywords": extract_keywords_tfidf(kw_text, 8),
                "topic": detect_topic(kw_text),
            })
        return out
    except Exception:
        return []


# ============================================================
# 3D NETWORK BUILDERS
# ============================================================
def build_chain_network(docs: list[dict], external_articles: list[dict] | None = None, user_research: str = "", connected_users: list[dict] | None = None):
    nodes: list[dict] = []
    edges: list[dict] = []
    topic_nodes: dict[str, int] = {}

    def add_node(node: dict) -> int:
        nodes.append(node)
        return len(nodes) - 1

    def ensure_topic_node(topic_name: str | None):
        if not topic_name or topic_name == "Pesquisa Geral":
            return None
        if topic_name in topic_nodes:
            return topic_nodes[topic_name]
        idx = add_node({
            "id": f"topic::{topic_name}",
            "label": topic_name[:38],
            "type": "topic",
            "topic": topic_name,
            "text": topic_name,
            "strength": 0.8,
        })
        topic_nodes[topic_name] = idx
        return idx

    user_idx = None
    if user_research:
        user_idx = add_node({
            "id": "researcher_self",
            "label": current_user().get("name", "Meu Perfil")[:42],
            "type": "researcher",
            "topic": detect_topic(user_research),
            "text": user_research,
            "strength": 1.0,
        })
        t_idx = ensure_topic_node(detect_topic(user_research, fallback="Pesquisa Geral"))
        if t_idx is not None:
            edges.append({"source": user_idx, "target": t_idx, "weight": 0.94, "same_topic": True, "relation": "tema-base"})

    for doc in docs[:18]:
        doc_text = " ".join([doc.get("summary", ""), " ".join(doc.get("keywords", [])), doc.get("text", "")[:2200]])
        doc_idx = add_node({
            "id": doc.get("id"),
            "label": doc.get("name", "Documento")[:40],
            "type": "local",
            "topic": doc.get("topic", ""),
            "text": doc_text,
            "strength": 0.82,
        })
        t_idx = ensure_topic_node(doc.get("topic"))
        if t_idx is not None:
            edges.append({"source": doc_idx, "target": t_idx, "weight": 0.78, "same_topic": True, "relation": "documento-tema"})
        if user_idx is not None:
            sim = cosine_similarity(user_research, doc_text) + (0.08 if doc.get("topic") == detect_topic(user_research) else 0)
            edges.append({"source": user_idx, "target": doc_idx, "weight": round(max(sim, 0.14), 3), "same_topic": doc.get("topic") == detect_topic(user_research), "relation": "perfil-documento"})

    for idx_art, art in enumerate(external_articles or []):
        art_text = f"{art.get('title','')} {art.get('abstract','')}"
        art_idx = add_node({
            "id": f"ext_{idx_art}",
            "label": art.get("title", "Artigo")[:40],
            "type": "external",
            "topic": art.get("topic", ""),
            "text": art_text,
            "strength": 0.74,
        })
        t_idx = ensure_topic_node(art.get("topic"))
        if t_idx is not None:
            edges.append({"source": art_idx, "target": t_idx, "weight": 0.74, "same_topic": True, "relation": "artigo-tema"})
        if user_idx is not None:
            sim = cosine_similarity(user_research, art_text) + (0.1 if art.get("topic") == detect_topic(user_research) else 0)
            if sim > 0.06:
                edges.append({"source": user_idx, "target": art_idx, "weight": round(sim, 3), "same_topic": art.get("topic") == detect_topic(user_research), "relation": "perfil-artigo"})

    for conn in connected_users or []:
        conn_text = " ".join([conn.get("research", ""), " ".join(conn.get("shared_terms", []))])
        conn_idx = add_node({
            "id": f"researcher::{conn['email']}",
            "label": conn.get("name", conn["email"])[:40],
            "type": "researcher_peer",
            "topic": conn.get("topic", ""),
            "text": conn_text,
            "strength": max(conn.get("similarity", 0) / 100.0, 0.35),
        })
        t_idx = ensure_topic_node(conn.get("topic"))
        if t_idx is not None:
            edges.append({"source": conn_idx, "target": t_idx, "weight": 0.84, "same_topic": True, "relation": "pesquisador-tema"})
        if user_idx is not None:
            edges.append({"source": user_idx, "target": conn_idx, "weight": round(max(conn.get("similarity", 0) / 100.0, 0.1), 3), "same_topic": conn.get("topic") == detect_topic(user_research), "relation": "pesquisador-pesquisador"})

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if nodes[i]["type"] == "topic" or nodes[j]["type"] == "topic":
                continue
            sim = cosine_similarity(nodes[i].get("text", ""), nodes[j].get("text", ""))
            if nodes[i].get("topic") and nodes[i].get("topic") == nodes[j].get("topic"):
                sim += 0.08
            if sim >= 0.10:
                edges.append({"source": i, "target": j, "weight": round(min(sim, 0.98), 3), "same_topic": nodes[i].get("topic") == nodes[j].get("topic"), "relation": "correlação"})

    return nodes, edges


def render_3d_network(nodes: list[dict], edges: list[dict]):
    if len(nodes) < 2:
        return None
    np.random.seed(42)
    anchors = {
        "researcher": np.array([0.0, 0.0, 0.0]),
        "researcher_peer": np.array([2.4, 2.0, 1.0]),
        "topic": np.array([0.0, 2.6, -1.2]),
        "local": np.array([-2.5, -1.2, 1.8]),
        "external": np.array([2.7, -1.8, -1.0]),
    }
    pos = np.zeros((len(nodes), 3), dtype=float)
    for idx, node in enumerate(nodes):
        pos[idx] = anchors.get(node.get("type"), np.zeros(3)) + np.random.normal(scale=0.9, size=3)
    for _ in range(70):
        forces = np.zeros_like(pos)
        for edge in edges:
            i, j = edge["source"], edge["target"]
            diff = pos[j] - pos[i]
            dist = max(np.linalg.norm(diff), 0.08)
            attract = max(edge["weight"], 0.04) * 0.26
            forces[i] += attract * diff / dist
            forces[j] -= attract * diff / dist
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                diff = pos[j] - pos[i]
                dist = max(np.linalg.norm(diff), 0.15)
                repulse = 0.06 / (dist ** 1.6)
                forces[i] -= repulse * diff / dist
                forces[j] += repulse * diff / dist
        pos += forces
        pos = np.clip(pos, -7, 7)

    styles = {
        "researcher": {"color": "#f8fafc", "size": 15, "name": "Meu perfil"},
        "researcher_peer": {"color": "#38bdf8", "size": 11, "name": "Pesquisadores conectados"},
        "topic": {"color": "#a78bfa", "size": 10, "name": "Temas"},
        "local": {"color": "#60a5fa", "size": 10, "name": "Documentos locais"},
        "external": {"color": "#34d399", "size": 9, "name": "Artigos externos"},
    }
    traces = []
    for edge in edges:
        i, j = edge["source"], edge["target"]
        traces.append(go.Scatter3d(
            x=[pos[i, 0], pos[j, 0], None],
            y=[pos[i, 1], pos[j, 1], None],
            z=[pos[i, 2], pos[j, 2], None],
            mode="lines",
            line=dict(color="rgba(96,165,250,0.40)" if edge.get("same_topic") else "rgba(148,163,184,0.25)", width=max(edge.get("weight", 0.05) * 7, 1.2)),
            hoverinfo="text",
            text=f"{nodes[i]['label']} ↔ {nodes[j]['label']}<br>Força: {edge.get('weight',0)*100:.1f}%<br>Relação: {edge.get('relation','correlação')}",
            showlegend=False,
        ))
    for node_type, style in styles.items():
        idxs = [i for i, node in enumerate(nodes) if node.get("type") == node_type]
        if not idxs:
            continue
        traces.append(go.Scatter3d(
            x=pos[idxs, 0], y=pos[idxs, 1], z=pos[idxs, 2],
            mode="markers+text",
            marker=dict(size=style["size"], color=style["color"], opacity=0.92, line=dict(color="rgba(255,255,255,0.25)", width=1)),
            text=[nodes[i]["label"] for i in idxs],
            textposition="top center",
            textfont=dict(size=8, color="#e2e8f0"),
            hovertext=[f"{nodes[i]['label']}<br>Tipo: {nodes[i].get('type','')}<br>Tema: {nodes[i].get('topic','')}" for i in idxs],
            hoverinfo="text",
            name=style["name"],
        ))
    fig = go.Figure(data=traces)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=690,
        margin=dict(l=0, r=0, t=35, b=0),
        legend=dict(font=dict(color="#dbeafe"), bgcolor="rgba(2,6,23,0.26)"),
        title=dict(text="Cadeia 3D entre perfil, temas, documentos, artigos e pesquisadores", font=dict(color="#eef2ff", size=15)),
        scene=dict(
            bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, showline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, showline=False),
            zaxis=dict(showgrid=False, showticklabels=False, zeroline=False, showline=False),
            camera=dict(eye=dict(x=1.55, y=1.45, z=1.2)),
        ),
    )
    return fig


# ============================================================
# UI BUILDERS
# ============================================================
def render_navbar() -> None:
    st.markdown(
        f"""
        <div class='nebula-nav'>
            <div class='nebula-logo'>Nebula Research</div>
            <div class='nav-user'>{current_user().get('name','')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    pages = ["Dashboard", "Pesquisa Inteligente", "Repositório", "Análise Avançada", "Conexões", "Chat", "Perfil"]
    cols = st.columns([1, 1, 1, 1, 1, 1, 1, 0.9])
    for idx, page in enumerate(pages):
        with cols[idx]:
            if st.button(page, use_container_width=True, key=f"nav_{page}"):
                st.session_state.page = page
                st.rerun()
    with cols[-1]:
        if st.button("Sair", use_container_width=True):
            logout_user()
            st.rerun()


def page_auth() -> None:
    st.markdown(
        """
        <div style='max-width:480px;margin:4vh auto 0;'>
            <div class='auth-logo-big'>Nebula Research</div>
            <div class='auth-sub'>Pesquisa acadêmica com privacidade por perfil, criptografia local e análise multimodal</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, center, right = st.columns([1, 2, 1])
    with center:
        tab_login, tab_register = st.tabs(["Entrar", "Criar conta"])
        with tab_login:
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown("<span class='privacy-pill'>Perfil isolado</span><span class='privacy-pill'>Workspace criptografado</span>", unsafe_allow_html=True)
            email = st.text_input("E-mail", key="login_email")
            password = st.text_input("Senha", type="password", key="login_password")
            if st.button("Acessar", type="primary", use_container_width=True, key="login_btn"):
                user = st.session_state.users.get(email)
                if user and user.get("password") == hash_password(password):
                    login_user(email)
                    st.rerun()
                else:
                    st.error("E-mail ou senha inválidos.")
            st.caption("Demo: demo@nebula.ai / demo123")
            st.markdown("</div>", unsafe_allow_html=True)
        with tab_register:
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            name = st.text_input("Nome completo", key="register_name")
            email = st.text_input("E-mail", key="register_email")
            password = st.text_input("Senha", type="password", key="register_password")
            research = st.text_area("Área de pesquisa", key="register_research", height=90)
            visibility = st.selectbox("Privacidade do perfil", ["Conexões", "Privado", "Público resumido"], index=0, key="register_visibility")
            if st.button("Criar conta", type="primary", use_container_width=True, key="register_btn"):
                if not all([name, email, password, research]):
                    st.error("Preencha todos os campos.")
                elif email in st.session_state.users:
                    st.error("Este e-mail já está cadastrado.")
                else:
                    st.session_state.users[email] = {
                        "name": name,
                        "password": hash_password(password),
                        "research": research,
                        "profile_visibility": visibility,
                        "privacy_mode": "Criptografado",
                    }
                    initialize_user_workspace(email)
                    save_db()
                    st.success("Conta criada com workspace privado separado. Agora entre com sua conta.")
            st.markdown("</div>", unsafe_allow_html=True)


def page_dashboard() -> None:
    user = current_user()
    docs = st.session_state.repository
    research = user.get("research", "")
    connections = get_connected_users(st.session_state.current_user, 6)
    st.markdown(f"<div class='page-title'>Bem-vindo, {user.get('name','').split()[0] if user.get('name') else 'pesquisador'}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='page-sub'>{research or 'Defina sua área de pesquisa no perfil para gerar recomendações melhores.'}</div>", unsafe_allow_html=True)

    df = pd.DataFrame([
        {"topic": d.get("topic"), "author": d.get("author"), "year": d.get("year"), "kind": d.get("kind"), "language": d.get("language")}
        for d in docs
    ]) if docs else pd.DataFrame()

    c1, c2, c3, c4, c5 = st.columns(5)
    cards = [
        (c1, "Documentos", len(docs), "No repositório", "blue"),
        (c2, "Temas", int(df["topic"].nunique()) if not df.empty else 0, "Mapeados", "cyan"),
        (c3, "Conexões", len(connections), "Pesquisadores próximos", "green"),
        (c4, "Buscas", len(st.session_state.search_history), "Neste perfil", "purple"),
        (c5, "Idioma", safe_top_value(df["language"]) if not df.empty else "N/A", "Predominante", "yellow"),
    ]
    for col, label, value, desc, color in cards:
        with col:
            st.markdown(f"<div class='metric-card {color}'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-desc'>{desc}</div></div>", unsafe_allow_html=True)

    left, right = st.columns([1.15, 0.85])
    with left:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Sugestões de artigos para sua pesquisa</div>", unsafe_allow_html=True)
        recommendation_query = build_recommendation_query(research, docs)
        if not recommendation_query.strip():
            st.info("Adicione uma linha de pesquisa no Perfil ou envie documentos ao Repositório para gerar recomendações.")
        else:
            cache_key = f"dashboard_articles_{hashlib.md5(recommendation_query.encode()).hexdigest()[:8]}"
            articles = st.session_state.get(cache_key)
            if articles is None:
                with st.spinner("Buscando artigos..."):
                    articles = search_semantic_scholar(recommendation_query, limit=6)
                    if len(articles) < 4:
                        articles += search_crossref(recommendation_query, limit=4)
                st.session_state[cache_key] = articles
            for art in articles[:6]:
                title = art.get("title", "Sem título")
                link = art.get("url", "")
                title_html = f'<a href="{link}" target="_blank" style="color:#bfdbfe;text-decoration:none">{title}</a>' if link else title
                st.markdown(
                    f"""
                    <div class='article-card'>
                        <div class='article-title'>{title_html}</div>
                        <div class='article-meta'>{art.get('authors','')} · {art.get('year','?')} · {art.get('source','')} · {art.get('citations',0)} cit.</div>
                        <div class='article-abstract'>{art.get('abstract','')[:240]}...</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Privacidade ativa</div>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class='insight-box'>
                Conta atual: <b>{st.session_state.current_user}</b><br>
                Repositório: <b>isolado por perfil</b><br>
                Persistência: <b>criptografada localmente</b><br>
                Visibilidade do perfil: <b>{user.get('profile_visibility', 'Conexões')}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Abrir chat", use_container_width=True):
            st.session_state.page = "Chat"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Termos aprendidos do perfil</div>", unsafe_allow_html=True)
        terms = recommend_terms(st.session_state.current_user, 20)
        if terms:
            st.markdown("".join([f"<span class='tag'>{t}</span>" for t in terms]), unsafe_allow_html=True)
        else:
            st.info("Faça buscas e envie documentos para o sistema aprender seu perfil temático.")
        st.markdown("</div>", unsafe_allow_html=True)


def page_smart_search() -> None:
    st.markdown("<div class='page-title'>Pesquisa Inteligente</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>Busca unificada com análise de intenção, resultados locais e artigos da internet correlacionados</div>", unsafe_allow_html=True)
    default_query = st.session_state.get("quick_query", "")
    query = st.text_area("Digite sua pergunta ou tema de pesquisa", value=default_query, height=100, placeholder="Ex: redes neurais para classificação de imagens médicas")
    col_l, col_r = st.columns([3, 1])
    with col_r:
        uploaded_image = st.file_uploader("Imagem (opcional)", type=["png", "jpg", "jpeg", "webp"], key="smart_search_image")

    if st.button("Executar pesquisa", type="primary", use_container_width=True):
        if not query and uploaded_image is None:
            st.warning("Digite uma consulta ou envie uma imagem.")
            return
        intent_data = recognize_research_intent(query or "imagem científica")
        update_user_interest(st.session_state.current_user, intent_data["search_terms"])
        st.session_state.search_history.append({
            "query": query,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "intent": intent_data["intent"],
            "topic": intent_data["topic"],
        })
        save_db()

        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Análise da sua busca</div>", unsafe_allow_html=True)
        i1, i2, i3 = st.columns(3)
        with i1:
            st.info(f"**Intenção:** {intent_data['intent']}")
        with i2:
            st.info(f"**Tema:** {intent_data['topic']}")
        with i3:
            st.info(f"**Termos-chave:** {', '.join(intent_data['keywords'][:5])}")
        st.markdown("".join([f"<span class='tag'>{term}</span>" for term in intent_data["search_terms"]]), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        search_query = " ".join(intent_data["search_terms"][:6]) or query
        with st.spinner("Buscando artigos..."):
            scholar_results = search_semantic_scholar(search_query, limit=8)
            crossref_results = search_crossref(search_query, limit=4) if len(scholar_results) < 4 else []
        local_results = local_search(query, st.session_state.repository)

        left, right = st.columns(2)
        with left:
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Nos seus documentos</div>", unsafe_allow_html=True)
            if not local_results:
                st.info("Nenhum documento local correspondeu. Envie arquivos no Repositório.")
            else:
                for doc in local_results[:6]:
                    st.markdown(
                        f"""
                        <div class='doc-card'>
                            <b>{doc['name']}</b><br>
                            <span class='small-muted'>{doc['kind']} · {doc['topic']} · relevância {doc['score']}%</span>
                            <div class='sim-bar-wrap'><div class='sim-bar-fill' style='width:{min(doc['score'],100)}%'></div></div>
                            <div style='margin-top:.4rem;color:#dbeafe;font-size:.82rem'>{doc['summary'][:220]}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            st.markdown("</div>", unsafe_allow_html=True)
        with right:
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Artigos na internet</div>", unsafe_allow_html=True)
            web_results = scholar_results + crossref_results
            if not web_results:
                st.info("Não foi possível recuperar artigos agora.")
            else:
                for art in web_results[:7]:
                    url = art.get("url", "")
                    title_html = f'<a href="{url}" target="_blank" style="color:#bfdbfe;text-decoration:none">{art["title"]}</a>' if url else art["title"]
                    st.markdown(
                        f"""
                        <div class='article-card'>
                            <div class='article-title'>{title_html}</div>
                            <div class='article-meta'>{art.get('authors','')} · {art.get('year','?')} · {art.get('source','')} · {art.get('citations',0)} cit.</div>
                            <div class='article-abstract'>{art.get('abstract','')[:240]}...</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Continuar pesquisando</div>", unsafe_allow_html=True)
        q_enc = quote_plus(search_query)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"[Google Scholar](https://scholar.google.com/scholar?q={q_enc})")
        with c2:
            st.markdown(f"[Semantic Scholar](https://www.semanticscholar.org/search?q={q_enc})")
        with c3:
            st.markdown(f"[Google Imagens](https://www.google.com/search?tbm=isch&q={q_enc})")
        st.markdown("</div>", unsafe_allow_html=True)

        if uploaded_image is not None:
            image_data = analyze_image_bytes(uploaded_image.getvalue())
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Análise visual</div>", unsafe_allow_html=True)
            v1, v2, v3, v4 = st.columns(4)
            with v1:
                st.markdown(f"<div class='metric-card blue'><div class='metric-label'>Largura</div><div class='metric-value'>{image_data.get('width','?')}</div></div>", unsafe_allow_html=True)
            with v2:
                st.markdown(f"<div class='metric-card cyan'><div class='metric-label'>Altura</div><div class='metric-value'>{image_data.get('height','?')}</div></div>", unsafe_allow_html=True)
            with v3:
                st.markdown(f"<div class='metric-card green'><div class='metric-label'>Brilho</div><div class='metric-value'>{image_data.get('brightness','?')}</div></div>", unsafe_allow_html=True)
            with v4:
                st.markdown(f"<div class='metric-card purple'><div class='metric-label'>Detalhe</div><div class='metric-value'>{image_data.get('detail_level','?')}</div></div>", unsafe_allow_html=True)
            st.image(uploaded_image, use_container_width=True)
            if image_data.get("palette_tags"):
                st.markdown("".join([f"<span class='chain-badge'>{tag}</span>" for tag in image_data.get("palette_tags", [])[:5]]), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    st.session_state.quick_query = ""


def page_repository() -> None:
    st.markdown("<div class='page-title'>Repositório</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>Seu acervo privado por perfil: análise de imagem, PDF, planilha, texto e código com isolamento criptografado</div>", unsafe_allow_html=True)
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("<span class='privacy-pill'>Escopo do perfil atual</span><span class='privacy-pill'>Dados criptografados em disco</span>", unsafe_allow_html=True)
    files = st.file_uploader(
        "Adicionar documentos",
        accept_multiple_files=True,
        type=["pdf", "docx", "txt", "md", "csv", "xlsx", "xls", "png", "jpg", "jpeg", "webp", "py", "json"],
        help="Cada arquivo é analisado conforme seu tipo e salvo apenas no workspace da conta logada.",
        key="repo_uploader",
    )
    if st.button("Analisar e adicionar", type="primary", use_container_width=True):
        if not files:
            st.warning("Selecione arquivos primeiro.")
        else:
            progress = st.progress(0)
            for idx, up in enumerate(files):
                progress.progress((idx + 1) / len(files), text=f"Analisando {up.name}...")
                record = make_document_record(up.name, up.getvalue())
                st.session_state.repository.append(record)
                update_user_interest(st.session_state.current_user, record.get("keywords", [])[:14])
            save_db()
            st.success(f"{len(files)} arquivo(s) analisados e adicionados ao perfil atual.")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    docs = st.session_state.repository
    if not docs:
        st.info("Seu repositório privado está vazio. Envie documentos acima.")
        return

    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Documentos catalogados</div>", unsafe_allow_html=True)
    filter_text = st.text_input("Filtrar por nome, tema, autor ou palavra-chave", placeholder="Buscar...")
    filtered = local_search(filter_text, docs) if filter_text else docs
    for doc in filtered[:50]:
        with st.expander(f"**{doc['name']}** · {doc['kind']} · {doc['topic']}"):
            left, right = st.columns([1.45, 1])
            with left:
                st.markdown(f"**Resumo:**  \n{doc['summary']}")
                for note in doc.get("modality_notes", [])[:4]:
                    st.markdown(f"<div class='insight-box'>{note}</div>", unsafe_allow_html=True)
                st.markdown("**Palavras-chave:**")
                st.markdown("".join([f"<span class='tag'>{kw}</span>" for kw in doc.get("keywords", [])[:18]]), unsafe_allow_html=True)
                if doc.get("sections"):
                    st.markdown("**Seções detectadas:**")
                    for section_name, section_text in doc.get("sections", {}).items():
                        st.markdown(f"*{section_name}:* {section_text[:240]}...")
                if doc.get("tabular_profile"):
                    tp = doc["tabular_profile"]
                    st.markdown(f"**Perfil tabular:** {tp.get('rows',0)} linhas · até {tp.get('cols',0)} colunas · {tp.get('numeric_columns',0)} colunas numéricas")
                if doc.get("image_meta"):
                    im = doc["image_meta"]
                    st.markdown(f"**Leitura visual:** {im.get('width','?')}×{im.get('height','?')} px · {im.get('orientation','?')} · detalhe {im.get('detail_level','?')} · brilho {im.get('brightness','?')}")
                    if im.get("palette_tags"):
                        st.markdown("".join([f"<span class='chain-badge'>{tag}</span>" for tag in im.get("palette_tags", [])[:5]]), unsafe_allow_html=True)
            with right:
                st.markdown(
                    f"""
                    <div class='glass-sm'>
                        <div class='metric-label'>Metadados</div>
                        <table class='soft-table'>
                            <tr><td style='color:#94a3c0'>Autor</td><td>{doc.get('author','?')[:34]}</td></tr>
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
                    """,
                    unsafe_allow_html=True,
                )
            related = related_documents(doc, docs, 4)
            if related:
                st.markdown("**Documentos relacionados:**")
                for rel in related:
                    width = min(int(rel["similarity"]), 100)
                    st.markdown(
                        f"""
                        <div style='display:flex;align-items:center;gap:.5rem;margin-bottom:.35rem'>
                            <span style='font-size:.8rem;color:#e2e8f0;flex:1'>{rel['name'][:45]}</span>
                            <span style='font-size:.75rem;color:#94a3c0'>{rel['similarity']}%</span>
                        </div>
                        <div class='sim-bar-wrap'><div class='sim-bar-fill' style='width:{width}%'></div></div>
                        """,
                        unsafe_allow_html=True,
                    )
    if st.button("Limpar repositório", use_container_width=True):
        st.session_state.repository = []
        save_db()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def page_analysis() -> None:
    st.markdown("<div class='page-title'>Análise Avançada</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>Leitura estatística, textual, comparativa e 3D do repositório privado do perfil atual</div>", unsafe_allow_html=True)
    docs = st.session_state.repository
    if not docs:
        st.info("Envie documentos no Repositório para liberar análises.")
        return

    df = pd.DataFrame([
        {
            "name": d.get("name"), "kind": d.get("kind"), "topic": d.get("topic"), "author": d.get("author"),
            "year": d.get("year"), "nationality": d.get("nationality"), "size_kb": d.get("size_kb"),
            "language": d.get("language"), "words": d.get("readability", {}).get("words", 0),
            "clarity": d.get("readability", {}).get("clarity", 0), "ref_count": d.get("ref_count", 0),
            "keyword_count": len(d.get("keywords", [])), "sections": len(d.get("sections", {})),
        }
        for d in docs
    ])
    dominant_language = safe_top_value(df["language"], default="N/A")
    dominant_topic = safe_top_value(df["topic"], default="Pesquisa Geral")
    total_words = int(pd.to_numeric(df["words"], errors="coerce").fillna(0).sum())
    clarity_series = pd.to_numeric(df["clarity"], errors="coerce").fillna(0)
    avg_clarity = round(float(clarity_series.mean()), 1) if not clarity_series.empty else 0
    avg_refs = round(float(pd.to_numeric(df["ref_count"], errors="coerce").fillna(0).mean()), 1)

    row = st.columns(6)
    metrics = [
        ("Documentos", len(docs), "blue"), ("Palavras", f"{total_words:,}", "cyan"), ("Tema líder", dominant_topic, "purple"),
        ("Idioma", dominant_language, "green"), ("Clareza média", avg_clarity, "yellow"), ("Refs/doc", avg_refs, "blue"),
    ]
    for col, (label, value, color) in zip(row, metrics):
        with col:
            st.markdown(f"<div class='metric-card {color}'><div class='metric-label'>{label}</div><div class='metric-value' style='font-size:1.28rem'>{value}</div></div>", unsafe_allow_html=True)

    left, right = st.columns([1.15, 0.85])
    with left:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Espaço analítico 3D do acervo</div>", unsafe_allow_html=True)
        scatter_df = df.copy()
        for col_name in ["year", "words", "ref_count", "clarity"]:
            scatter_df[col_name] = pd.to_numeric(scatter_df[col_name], errors="coerce")
        scatter_df = scatter_df.dropna(subset=["year", "words", "ref_count"])
        if not scatter_df.empty:
            fig = px.scatter_3d(scatter_df, x="year", y="words", z="ref_count", color="topic", size="clarity", hover_name="name")
            fig.update_layout(height=560, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#dbeafe"), legend=dict(bgcolor="rgba(0,0,0,0)"))
            fig.update_scenes(bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados insuficientes para o gráfico 3D do acervo.")
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Composição do acervo</div>", unsafe_allow_html=True)
        kinds = df["kind"].dropna().astype(str)
        kinds = kinds[kinds.str.strip() != ""].value_counts().reset_index()
        if not kinds.empty:
            kinds.columns = ["Tipo", "Quantidade"]
            fig = px.pie(kinds, names="Tipo", values="Quantidade", hole=0.52)
            fig.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#dbeafe"), legend=dict(bgcolor="rgba(0,0,0,0)"))
            st.plotly_chart(fig, use_container_width=True)
        topics = df["topic"].dropna().astype(str)
        topics = topics[topics.str.strip() != ""].value_counts().head(8).reset_index()
        if not topics.empty:
            topics.columns = ["Tema", "Quantidade"]
            fig = px.bar(topics, x="Tema", y="Quantidade")
            fig.update_layout(height=240, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#dbeafe"), xaxis=dict(tickangle=-20))
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Mapa 3D de autores por nacionalidade</div>", unsafe_allow_html=True)
    auth_df = df[df["author"].fillna("").astype(str).str.strip().ne("") & df["author"].astype(str).ne("Desconhecido")].copy()
    rows = []
    if not auth_df.empty:
        grouped = auth_df.groupby(["author", "nationality"]).size().reset_index(name="count")
        for _, row in grouped.iterrows():
            coords = NATIONALITY_COORDS.get(row["nationality"])
            if coords:
                rows.append({"Autor": row["author"], "País": row["nationality"], "lon": coords["lon"], "lat": coords["lat"], "z": float(row["count"])})
    if rows:
        map_df = pd.DataFrame(rows)
        fig = go.Figure(data=[go.Scatter3d(
            x=map_df["lon"], y=map_df["lat"], z=map_df["z"], mode="markers+text",
            marker=dict(size=map_df["z"] * 7 + 6, color=map_df["z"], colorscale="Blues", opacity=0.88, showscale=True),
            text=map_df["País"], hovertext=map_df["Autor"] + "<br>" + map_df["País"], hoverinfo="text",
        )])
        fig.update_layout(height=520, paper_bgcolor="rgba(0,0,0,0)", scene=dict(bgcolor="rgba(0,0,0,0)", xaxis_title="Longitude", yaxis_title="Latitude", zaxis_title="Recorrência"), font=dict(color="#dbeafe"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Autores insuficientes para compor o mapa 3D.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Análise comparativa entre documentos</div>", unsafe_allow_html=True)
    selected_docs = docs[:10]
    if len(selected_docs) >= 2:
        labels = [d.get("name", "")[:20] for d in selected_docs]
        matrix = []
        for a in selected_docs:
            row_scores = []
            a_text = " ".join([a.get("summary", ""), " ".join(a.get("keywords", [])), a.get("text", "")[:2000]])
            for b in selected_docs:
                b_text = " ".join([b.get("summary", ""), " ".join(b.get("keywords", [])), b.get("text", "")[:2000]])
                sim = cosine_similarity(a_text, b_text)
                if a.get("topic") == b.get("topic") and a.get("topic"):
                    sim += 0.08
                row_scores.append(round(min(sim, 1.0) * 100, 1))
            matrix.append(row_scores)
        heatmap = go.Figure(data=go.Heatmap(z=matrix, x=labels, y=labels, colorscale="Blues", zmin=0, zmax=100))
        heatmap.update_layout(height=430, paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#dbeafe"), xaxis=dict(tickangle=-30))
        st.plotly_chart(heatmap, use_container_width=True)
    else:
        st.info("Adicione pelo menos dois documentos para a comparação matricial.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Leitura textual e comparativa do repositório</div>", unsafe_allow_html=True)
    topics = df["topic"].dropna().astype(str)
    topics = topics[topics.str.strip() != ""]
    dominant_topics = ", ".join(topics.value_counts().head(3).index.tolist()) if not topics.empty else "não identificados"
    authors = df["author"].dropna().astype(str)
    authors = authors[(authors.str.strip() != "") & (authors != "Desconhecido")]
    dominant_authors = ", ".join(authors.value_counts().head(3).index.tolist()) if not authors.empty else "não identificados"
    year_series = pd.to_numeric(df["year"], errors="coerce").dropna()
    years_range = f"{int(year_series.min())} a {int(year_series.max())}" if not year_series.empty else "não identificado"
    st.markdown(f"<div class='insight-box'>O perfil atual possui <b>{len(docs)} documentos</b>, com predominância dos temas <b>{dominant_topics}</b>. O intervalo temporal observado vai de <b>{years_range}</b> e o idioma dominante é <b>{dominant_language}</b>.</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='insight-box'>Em termos de autoria, aparecem com mais recorrência <b>{dominant_authors}</b>. A clareza média do conjunto está em <b>{avg_clarity}/100</b>, o que ajuda a identificar textos mais densos ou mais acessíveis.</div>", unsafe_allow_html=True)
    selected_name = st.selectbox("Inspecionar documento", options=[d.get("name") for d in docs])
    target = next((d for d in docs if d.get("name") == selected_name), None)
    if target:
        lft, rgt = st.columns([1.2, 0.8])
        with lft:
            st.markdown(f"**Resumo analítico:** {target.get('summary', '')}")
            for name, sec in target.get("sections", {}).items():
                st.markdown(f"**{name}:** {sec[:260]}")
        with rgt:
            st.markdown(f"**Tema:** {target.get('topic','')}  \n**Autor:** {target.get('author','')}  \n**Idioma:** {target.get('language','')}  \n**Referências:** {target.get('ref_count',0)}")
            for note in target.get("modality_notes", [])[:4]:
                st.markdown(f"<span class='chain-badge'>{note}</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def page_connections() -> None:
    st.markdown("<div class='page-title'>Conexões entre Pesquisas</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>Cadeia 3D entre seu perfil, pesquisadores conectados, temas em comum, documentos do repositório e artigos externos</div>", unsafe_allow_html=True)
    docs = st.session_state.repository
    research = current_user().get("research", "")
    connected = get_connected_users(st.session_state.current_user, 10)

    c1, c2, c3 = st.columns(3)
    with c1:
        min_strength = st.slider("Limite mínimo de força", 0.05, 0.55, 0.12, 0.01)
    with c2:
        include_external = st.checkbox("Incluir artigos externos", value=True)
    with c3:
        n_external = st.slider("Artigos externos", 4, 18, 8)

    external_articles = []
    if include_external and research:
        cache_key = f"conn_articles_{hashlib.md5(research.encode()).hexdigest()[:8]}_{n_external}"
        external_articles = st.session_state.get(cache_key)
        if external_articles is None:
            with st.spinner("Buscando artigos correlatos..."):
                query = " ".join(extract_keywords_tfidf(research, 6)[:5]) or research
                external_articles = search_semantic_scholar(query, limit=n_external)
                if len(external_articles) < 4:
                    external_articles += search_crossref(query, limit=4)
            st.session_state[cache_key] = external_articles

    nodes, edges = build_chain_network(docs, external_articles, research, connected)
    filtered_edges = [e for e in edges if e.get("weight", 0) >= min_strength]
    if len(nodes) < 2:
        st.info("Adicione documentos e configure sua linha de pesquisa no Perfil para gerar a cadeia de conexões.")
        return

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"<div class='metric-card blue'><div class='metric-label'>Nós</div><div class='metric-value'>{len(nodes)}</div></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='metric-card cyan'><div class='metric-label'>Conexões ativas</div><div class='metric-value'>{len(filtered_edges)}</div></div>", unsafe_allow_html=True)
    with m3:
        researchers = sum(1 for node in nodes if node.get("type") in {"researcher", "researcher_peer"})
        st.markdown(f"<div class='metric-card green'><div class='metric-label'>Pesquisadores</div><div class='metric-value'>{researchers}</div></div>", unsafe_allow_html=True)
    with m4:
        topics = sum(1 for node in nodes if node.get("type") == "topic")
        st.markdown(f"<div class='metric-card purple'><div class='metric-label'>Temas-pivô</div><div class='metric-value'>{topics}</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("".join([
        "<span class='chain-badge'>Perfil atual</span>",
        "<span class='chain-badge'>Pesquisadores conectados</span>",
        "<span class='chain-badge'>Temas em comum</span>",
        "<span class='chain-badge'>Documentos do seu perfil</span>",
        "<span class='chain-badge'>Artigos externos correlatos</span>",
    ]), unsafe_allow_html=True)
    fig = render_3d_network(nodes, filtered_edges)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Não há conexões suficientes para exibir a rede. Reduza o limite mínimo de força.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Pesquisadores e temas em comum</div>", unsafe_allow_html=True)
    if connected:
        for conn in connected:
            badges = "".join([f"<span class='chain-badge'>{term}</span>" for term in conn.get("shared_terms", [])[:6]]) or "<span class='chain-badge'>tema aproximado</span>"
            st.markdown(
                f"""
                <div class='doc-mini'>
                    <b>{conn['name']}</b><br>
                    <span class='small-muted'>{conn.get('topic','Pesquisa Geral')} · similaridade {conn['similarity']}%</span>
                    <div style='margin-top:.45rem;color:#dbeafe'>{(conn.get('research') or 'Sem linha de pesquisa cadastrada.')[:180]}</div>
                    <div style='margin-top:.45rem'>{badges}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Ainda não há pesquisadores conectados com proximidade temática suficiente.")
    st.markdown("</div>", unsafe_allow_html=True)

    if filtered_edges:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Cadeias mais fortes</div>", unsafe_allow_html=True)
        rows = []
        for edge in sorted(filtered_edges, key=lambda x: -x["weight"])[:24]:
            i, j = edge["source"], edge["target"]
            rows.append({
                "Origem": nodes[i]["label"],
                "Destino": nodes[j]["label"],
                "Força": f"{edge['weight']*100:.1f}%",
                "Relação": edge.get("relation", "correlação"),
                "Tema": nodes[i].get("topic") or nodes[j].get("topic") or "geral",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)


def page_chat() -> None:
    st.markdown("<div class='page-title'>Chat</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>Mensagens entre conexões, salas por tema e histórico salvo com proteção criptografada no banco local</div>", unsafe_allow_html=True)
    current_email = st.session_state.current_user
    connections = get_connected_users(current_email, 14)
    rooms = get_available_rooms(current_email)
    st.markdown("<span class='privacy-pill'>Chat entre conexões</span><span class='privacy-pill'>Mensagens protegidas em disco</span>", unsafe_allow_html=True)

    tab_dm, tab_rooms = st.tabs(["Diretas", "Salas por tema"])
    with tab_dm:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        if not connections:
            st.info("Ainda não há conexões com proximidade temática suficiente para abrir mensagens diretas.")
        else:
            mapping = {f"{c['name']} · {c['topic']} · {c['similarity']}%": c["email"] for c in connections}
            label = st.selectbox("Escolha uma conexão", options=list(mapping.keys()))
            peer_email = mapping[label]
            st.markdown("<div class='notice-box'>Somente você e a conexão selecionada visualizam esta conversa direta.</div>", unsafe_allow_html=True)
            messages = get_dm_messages(peer_email)
            st.markdown("<div class='chat-shell'>", unsafe_allow_html=True)
            for msg in messages:
                bubble_class = "chat-bubble me" if msg.get("sender_email") == current_email else "chat-bubble"
                st.markdown(
                    f"""
                    <div class='{bubble_class}'>
                        <div class='chat-meta'>
                            <span><b>{msg.get('sender_name','Usuário')}</b> · {msg.get('sender_topic','Pesquisa Geral')}</span>
                            <span>{msg.get('created_at','')}</span>
                        </div>
                        <div class='chat-text'>{msg.get('text','')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)
            dm_text = st.text_area("Mensagem direta", height=120, key="dm_text")
            if st.button("Enviar mensagem direta", type="primary", use_container_width=True):
                if post_chat_message("dm", peer_email, dm_text):
                    st.rerun()
                else:
                    st.warning("Escreva uma mensagem antes de enviar.")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_rooms:
        left, right = st.columns([0.9, 1.1])
        with left:
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Suas conexões acadêmicas</div>", unsafe_allow_html=True)
            if connections:
                for conn in connections:
                    shared = ", ".join(conn.get("shared_terms", [])[:4]) or conn.get("topic", "Pesquisa Geral")
                    st.markdown(
                        f"""
                        <div class='doc-mini'>
                            <b>{conn['name']}</b><br>
                            <span class='small-muted'>{conn.get('topic','Pesquisa Geral')} · similaridade {conn['similarity']}%</span>
                            <div style='margin-top:.4rem;color:#dbeafe;font-size:.81rem'>{(conn.get('research') or 'Sem linha de pesquisa cadastrada.')[:170]}</div>
                            <div style='margin-top:.45rem'><span class='tag'>{shared}</span></div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.info("Ainda não há conexões temáticas suficientes. Continue alimentando seu repositório e seu perfil.")
            st.markdown("</div>", unsafe_allow_html=True)
        with right:
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Chat temático</div>", unsafe_allow_html=True)
            room = st.selectbox("Sala", options=rooms, index=0)
            only_connections = st.checkbox("Mostrar somente mensagens das minhas conexões", value=True)
            messages = get_room_messages(room, only_connections=only_connections)
            if not messages:
                st.markdown("<div class='notice-box'>Ainda não há mensagens nesta sala. Você pode iniciar compartilhando um resumo, um artigo ou uma dúvida.</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='chat-shell'>", unsafe_allow_html=True)
                for msg in messages:
                    bubble_class = "chat-bubble me" if msg.get("sender_email") == current_email else "chat-bubble"
                    st.markdown(
                        f"""
                        <div class='{bubble_class}'>
                            <div class='chat-meta'>
                                <span><b>{msg.get('sender_name','Usuário')}</b> · {msg.get('sender_topic','Pesquisa Geral')}</span>
                                <span>{msg.get('created_at','')}</span>
                            </div>
                            <div class='chat-text'>{msg.get('text','')}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                st.markdown("</div>", unsafe_allow_html=True)
            room_text = st.text_area("Enviar mensagem para a sala", height=120, key="room_text")
            if st.button("Publicar na sala", type="primary", use_container_width=True):
                if post_chat_message("room", room, room_text):
                    st.rerun()
                else:
                    st.warning("Escreva uma mensagem antes de publicar.")
            st.markdown("</div>", unsafe_allow_html=True)


def page_profile() -> None:
    user = current_user()
    st.markdown("<div class='page-title'>Perfil</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-sub'>Seu perfil é analisado separadamente, com isolamento por conta e proteção local dos dados</div>", unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Dados do perfil</div>", unsafe_allow_html=True)
        st.markdown("<span class='privacy-pill'>Workspace separado</span><span class='privacy-pill'>Criptografia local</span>", unsafe_allow_html=True)
        name = st.text_input("Nome", value=user.get("name", ""))
        research = st.text_area("Área de pesquisa", value=user.get("research", ""), height=110)
        options = ["Conexões", "Privado", "Público resumido"]
        current_vis = user.get("profile_visibility", "Conexões")
        visibility = st.selectbox("Visibilidade do perfil", options, index=options.index(current_vis) if current_vis in options else 0)
        if st.button("Salvar perfil", type="primary", use_container_width=True):
            st.session_state.users[st.session_state.current_user].update({
                "name": name,
                "research": research,
                "profile_visibility": visibility,
                "privacy_mode": "Criptografado",
            })
            save_db()
            for key in list(st.session_state.keys()):
                if key.startswith("dashboard_articles_") or key.startswith("conn_articles_"):
                    del st.session_state[key]
            st.success("Perfil atualizado com privacidade preservada.")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Proteção de dados</div>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class='insight-box'>
                Conta atual: <b>{st.session_state.current_user}</b><br>
                Modo de privacidade: <b>{user.get('privacy_mode','Criptografado')}</b><br>
                Escopo do repositório: <b>somente este perfil</b><br>
                Chat: <b>diretas entre conexões + salas por tema</b>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Preferências aprendidas</div>", unsafe_allow_html=True)
        interests = recommend_terms(st.session_state.current_user, 25)
        if interests:
            st.markdown("".join([f"<span class='tag'>{term}</span>" for term in interests]), unsafe_allow_html=True)
        else:
            st.info("Faça buscas e envie documentos para construir seu perfil.")
        if interests and st.button("Limpar preferências", use_container_width=True):
            st.session_state.user_interest = {}
            save_db()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Histórico de buscas do perfil</div>", unsafe_allow_html=True)
        history = st.session_state.search_history
        if history:
            recent = history[-10:][::-1]
            hist_df = pd.DataFrame(recent)[["query", "time", "topic", "intent"]]
            hist_df.columns = ["Consulta", "Data", "Tema", "Intenção"]
            st.dataframe(hist_df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma busca registrada neste perfil.")
        st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# MAIN
# ============================================================
def main() -> None:
    init_state()
    inject_css()
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
    elif page == "Chat":
        page_chat()
    elif page == "Perfil":
        page_profile()


if __name__ == "__main__":
    main()
