import os
import re
import io
import json
import math
import base64
import zipfile
import hashlib
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

import streamlit as st

# Dependências opcionais com fallbacks
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
    from PIL import Image
except Exception:
    Image = None

try:
    import plotly.graph_objects as go
except Exception:
    go = None

try:
    import plotly.express as px
except Exception:
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
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:
    TfidfVectorizer = None
    cosine_similarity = None

APP_TITLE = "Sistema Folksonomia Digital"
APP_SUBTITLE = "Plataforma de pesquisa, repositório e análise acadêmica"
BASE_DIR = Path("folksonomia_liquid_storage")
DB_FILE = BASE_DIR / "state.json"
FILES_DIR = BASE_DIR / "files"
BASE_DIR.mkdir(exist_ok=True)
FILES_DIR.mkdir(exist_ok=True)

STOPWORDS = {
    "de","da","do","das","dos","a","o","as","os","e","em","para","por","com","um","uma","uns","umas",
    "ao","aos","na","no","nas","nos","que","se","como","mais","menos","entre","sobre","sob","sem",
    "the","of","and","or","in","to","for","by","with","on","at","from","an","is","are","be","this","that",
    "study","paper","research","article","using","used","use","based","analysis","system","model","models"
}

TOPIC_LEXICON = {
    "Inteligência Artificial": [
        "inteligência artificial","ia","machine learning","deep learning","llm","neural","rede neural",
        "modelo de linguagem","aprendizado","classificação","transformer","visão computacional"
    ],
    "Museologia": [
        "museologia","museu","acervo","patrimônio","coleção","documentação museológica","folksonomia",
        "curadoria","exposição","museal","salvaguarda","catalogação"
    ],
    "Ciência da Informação": [
        "informação","indexação","metadados","ontologia","repositório","descrição","documentação","taxonomia",
        "folksonomia","organização da informação","recuperação da informação"
    ],
    "Biologia": [
        "célula","celular","proteína","gene","genômica","dna","rna","crispr","microscopia","tecido","organismo"
    ],
    "Medicina": [
        "clínico","clínica","paciente","diagnóstico","tratamento","doença","hospital","terapia","sintoma"
    ],
    "Computação": [
        "algoritmo","software","sistema","python","streamlit","dados","banco de dados","api","deploy"
    ],
    "Física": [
        "quântico","física","partícula","energia","lente gravitacional","cosmologia","astrofísica","matéria escura"
    ],
    "Psicologia": [
        "cognitivo","psicologia","comportamento","memória","emoção","percepção","viés","aprendizagem"
    ],
    "Educação": [
        "ensino","aprendizagem","escola","universidade","educação","didática","currículo","discente"
    ],
    "Humanidades Digitais": [
        "humanidades digitais","digital","preservação digital","arquivo digital","interoperabilidade","acesso aberto"
    ],
}

METHOD_LEXICON = {
    "Experimental": ["experimento","experimental","ensaio","amostra","laboratório","coleta","medição","teste"],
    "Revisão": ["revisão","estado da arte","scoping review","systematic review","revisão bibliográfica"],
    "Qualitativa": ["entrevista","grupo focal","análise temática","observação","qualitativa","etnográfica"],
    "Quantitativa": ["estatística","quantitativa","amostra","regressão","survey","questionário","variável"],
    "Computacional": ["algoritmo","pipeline","simulação","modelo","rede neural","software","script","streamlit"],
    "Estudo de Caso": ["estudo de caso","case study","caso","instituição","museu específico"],
}

COUNTRY_CODE_TO_NAME = {
    "BR": "Brasil", "US": "Estados Unidos", "GB": "Reino Unido", "FR": "França", "DE": "Alemanha",
    "ES": "Espanha", "PT": "Portugal", "IT": "Itália", "CA": "Canadá", "MX": "México", "AR": "Argentina",
    "CL": "Chile", "CO": "Colômbia", "PE": "Peru", "UY": "Uruguai", "PY": "Paraguai", "JP": "Japão",
    "CN": "China", "KR": "Coreia do Sul", "IN": "Índia", "AU": "Austrália", "NL": "Países Baixos",
    "BE": "Bélgica", "CH": "Suíça", "SE": "Suécia", "NO": "Noruega", "DK": "Dinamarca", "FI": "Finlândia",
    "AT": "Áustria", "IE": "Irlanda", "ZA": "África do Sul"
}

DEMO_USER = {
    "demo@folksonomia.ai": {
        "name": "Usuário Demo",
        "password": hashlib.sha256("demo123".encode()).hexdigest(),
        "area": "Museologia e Ciência da Informação",
        "bio": "Conta de demonstração",
        "history": [],
        "saved_articles": []
    }
}

def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def ensure_repo_dir(repo_slug: str) -> Path:
    p = FILES_DIR / repo_slug
    p.mkdir(parents=True, exist_ok=True)
    return p

def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.UNICODE).strip()
    text = re.sub(r"[-\s]+", "-", text)
    return text or "repositorio"

def initials(name: str) -> str:
    parts = [p for p in (name or "?").split() if p.strip()]
    return "".join(p[0].upper() for p in parts[:2]) or "U"

def load_state():
    if DB_FILE.exists():
        try:
            data = json.loads(DB_FILE.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {}
            return data
        except Exception:
            return {}
    return {}

def save_state():
    data = {
        "users": st.session_state.users,
        "repositories": st.session_state.repositories,
        "saved_articles_global": st.session_state.saved_articles_global,
    }
    DB_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def init_state():
    disk = load_state()
    st.session_state.setdefault("users", {**DEMO_USER, **disk.get("users", {})})
    st.session_state.setdefault("repositories", disk.get("repositories", {}))
    st.session_state.setdefault("saved_articles_global", disk.get("saved_articles_global", []))
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("current_user", None)
    st.session_state.setdefault("page", "dashboard")
    st.session_state.setdefault("search_cache", {})
    st.session_state.setdefault("discovery_result", None)
    st.session_state.setdefault("connections_cache", None)
    st.session_state.setdefault("analysis_cache", None)

def user_data():
    email = st.session_state.get("current_user")
    return st.session_state.users.get(email, {})

def tokenize(text: str):
    text = (text or "").lower()
    text = re.sub(r"[^\w\sáàâãéêíóôõúçü-]", " ", text, flags=re.UNICODE)
    toks = [t for t in text.split() if len(t) > 2 and t not in STOPWORDS]
    return toks

def keyword_scores(text: str, limit: int = 20):
    counts = Counter(tokenize(text))
    return counts.most_common(limit)

def extract_keywords(text: str, limit: int = 20):
    return [k for k, _ in keyword_scores(text, limit)]

def normalize_spaces(text: str):
    return re.sub(r"\s+", " ", (text or "")).strip()

def split_sentences(text: str):
    text = normalize_spaces(text)
    if not text:
        return []
    return re.split(r"(?<=[\.\!\?])\s+", text)

def summarize_text(text: str, max_sentences: int = 4):
    sentences = [s.strip() for s in split_sentences(text) if len(s.strip()) > 35]
    if not sentences:
        return ""
    scores = Counter(tokenize(text))
    ranked = []
    for idx, sent in enumerate(sentences):
        sent_tokens = tokenize(sent)
        if not sent_tokens:
            continue
        score = sum(scores[t] for t in sent_tokens) / max(len(sent_tokens), 1)
        ranked.append((score, idx, sent))
    chosen = sorted(sorted(ranked, reverse=True)[:max_sentences], key=lambda x: x[1])
    summary = " ".join(item[2] for item in chosen)
    return summary[:1200]

def detect_topics(text: str):
    base = text.lower()
    topic_scores = {}
    for topic, terms in TOPIC_LEXICON.items():
        score = 0
        for term in terms:
            if term in base:
                score += 3
            else:
                toks = term.split()
                score += sum(1 for tok in toks if tok in base)
        if score:
            topic_scores[topic] = score
    if not topic_scores:
        topic_scores["Pesquisa Geral"] = 1
    return dict(sorted(topic_scores.items(), key=lambda x: x[1], reverse=True))

def detect_methodology(text: str):
    base = text.lower()
    scores = {}
    for method, terms in METHOD_LEXICON.items():
        score = sum(base.count(term) for term in terms)
        if score:
            scores[method] = score
    if not scores:
        return "Indefinida", {}
    best = max(scores.items(), key=lambda x: x[1])[0]
    return best, scores

def detect_years(text: str):
    years = re.findall(r"\b(19\d{2}|20\d{2})\b", text or "")
    filtered = [int(y) for y in years if 1900 <= int(y) <= datetime.now().year + 1]
    return Counter(filtered)

def guess_title(fname: str, text: str):
    sentences = split_sentences(text[:2000])
    cleaned_name = Path(fname).stem.replace("_", " ").replace("-", " ").strip()
    candidates = []
    for line in text[:1500].splitlines():
        line = normalize_spaces(line)
        if 12 < len(line) < 180:
            candidates.append(line)
    for cand in candidates[:12]:
        if len(cand.split()) >= 4 and cand.lower() not in {"abstract", "resumo"}:
            return cand[:180]
    return cleaned_name[:180]

def guess_authors(text: str):
    header = text[:1500]
    lines = [normalize_spaces(l) for l in header.splitlines() if normalize_spaces(l)]
    patterns = [
        r"(?:autor(?:es)?|authors?)\s*[:\-]\s*([^\n]+)",
        r"(?:por|by)\s+([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][^\n]{5,120})"
    ]
    for pat in patterns:
        m = re.search(pat, header, flags=re.IGNORECASE)
        if m:
            line = normalize_spaces(m.group(1))
            parts = re.split(r",|;| and | e ", line)
            authors = [p.strip() for p in parts if 3 < len(p.strip()) < 60]
            if authors:
                return authors[:8]
    candidates = []
    for line in lines[:8]:
        if re.search(r"[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+ [A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+", line):
            if "universidade" not in line.lower() and "abstract" not in line.lower():
                candidates.append(line)
    joined = " ".join(candidates[:2])
    found = re.findall(r"([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+(?:\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+)+)", joined)
    return found[:6]

def extract_pdf_text(file_bytes: bytes):
    if PyPDF2 is None:
        return ""
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        texts = []
        for page in reader.pages[:30]:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(texts)
    except Exception:
        return ""

def extract_docx_text(file_bytes: bytes):
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
        xml = re.sub(r"</w:p>", "\n", xml)
        xml = re.sub(r"<[^>]+>", " ", xml)
        return normalize_spaces(xml)
    except Exception:
        return ""

def extract_xlsx_text(file_bytes: bytes):
    if openpyxl is None:
        return ""
    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        chunks = []
        for ws in wb.worksheets[:8]:
            for row in ws.iter_rows(values_only=True):
                vals = [str(v) for v in row if v is not None]
                if vals:
                    chunks.append(" | ".join(vals))
        return "\n".join(chunks)
    except Exception:
        return ""

def extract_csv_text(file_bytes: bytes):
    if pd is None:
        try:
            return file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    for sep in [",", ";", "\t"]:
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), sep=sep)
            return df.astype(str).head(300).to_csv(index=False)
        except Exception:
            continue
    try:
        return file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return ""

def extract_txt_text(file_bytes: bytes):
    try:
        return file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return ""

def file_type(filename: str):
    ext = Path(filename).suffix.lower().strip(".")
    mapping = {
        "pdf": "PDF", "docx": "DOCX", "txt": "TXT", "csv": "CSV", "xlsx": "XLSX",
        "xls": "XLSX", "md": "TXT", "py": "TXT", "json": "TXT", "jpg": "IMG",
        "jpeg": "IMG", "png": "IMG", "webp": "IMG", "bmp": "IMG", "tif": "IMG", "tiff": "IMG"
    }
    return mapping.get(ext, "OUTRO")

def safe_request(url: str, params=None, headers=None, timeout: int = 12):
    if requests is None:
        return None
    try:
        r = requests.get(url, params=params, headers=headers or {}, timeout=timeout)
        if r.status_code == 200:
            return r
    except Exception:
        return None
    return None

def semantic_scholar_search(query: str, limit: int = 6):
    cache_key = f"ss::{query}::{limit}"
    if cache_key in st.session_state.search_cache:
        return st.session_state.search_cache[cache_key]
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,abstract,venue,citationCount,url,externalIds"
    }
    results = []
    r = safe_request(url, params=params)
    if r is not None:
        data = r.json().get("data", [])
        for item in data:
            doi = (item.get("externalIds") or {}).get("DOI", "")
            authors = ", ".join(a.get("name", "") for a in item.get("authors", [])[:4])
            results.append({
                "source": "Semantic Scholar",
                "title": item.get("title", "Sem título"),
                "authors": authors or "Não identificado",
                "year": item.get("year"),
                "abstract": item.get("abstract", "") or "",
                "citations": item.get("citationCount", 0) or 0,
                "url": item.get("url") or (f"https://doi.org/{doi}" if doi else ""),
                "doi": doi,
            })
    st.session_state.search_cache[cache_key] = results
    return results

def crossref_search(query: str, limit: int = 6):
    cache_key = f"cr::{query}::{limit}"
    if cache_key in st.session_state.search_cache:
        return st.session_state.search_cache[cache_key]
    url = "https://api.crossref.org/works"
    params = {
        "query": query,
        "rows": limit,
        "select": "title,author,issued,DOI,abstract,container-title,is-referenced-by-count,URL"
    }
    headers = {"User-Agent": "SistemaFolksonomiaDigital/1.0 (mailto:demo@example.com)"}
    results = []
    r = safe_request(url, params=params, headers=headers)
    if r is not None:
        for item in r.json().get("message", {}).get("items", []):
            title = ((item.get("title") or ["Sem título"])[0] or "Sem título")
            author_parts = []
            for a in item.get("author", [])[:4]:
                nm = " ".join(part for part in [a.get("given", ""), a.get("family", "")] if part).strip()
                if nm:
                    author_parts.append(nm)
            year = None
            try:
                year = item.get("issued", {}).get("date-parts", [[None]])[0][0]
            except Exception:
                year = None
            abs_text = re.sub(r"<[^>]+>", " ", item.get("abstract", "") or "")
            results.append({
                "source": "Crossref",
                "title": title,
                "authors": ", ".join(author_parts) or "Não identificado",
                "year": year,
                "abstract": normalize_spaces(abs_text),
                "citations": item.get("is-referenced-by-count", 0) or 0,
                "url": item.get("URL", "") or "",
                "doi": item.get("DOI", "") or "",
            })
    st.session_state.search_cache[cache_key] = results
    return results

def openalex_search(query: str, limit: int = 4):
    cache_key = f"oa::{query}::{limit}"
    if cache_key in st.session_state.search_cache:
        return st.session_state.search_cache[cache_key]
    url = "https://api.openalex.org/works"
    params = {"search": query, "per-page": limit}
    results = []
    r = safe_request(url, params=params)
    if r is not None:
        for item in r.json().get("results", []):
            authorships = item.get("authorships", []) or []
            author_names = []
            countries = []
            geo_points = []
            for auth in authorships[:8]:
                author = (auth.get("author") or {}).get("display_name")
                if author:
                    author_names.append(author)
                for inst in auth.get("institutions", [])[:2]:
                    cc = inst.get("country_code")
                    geo = inst.get("geo") or {}
                    if cc:
                        countries.append(cc)
                    if geo and geo.get("latitude") is not None and geo.get("longitude") is not None:
                        geo_points.append({
                            "country_code": cc,
                            "country": COUNTRY_CODE_TO_NAME.get(cc or "", cc or "País não identificado"),
                            "lat": geo.get("latitude"),
                            "lon": geo.get("longitude"),
                            "institution": inst.get("display_name", "")
                        })
            results.append({
                "source": "OpenAlex",
                "title": item.get("display_name", "Sem título"),
                "authors": ", ".join(author_names[:4]) or "Não identificado",
                "year": item.get("publication_year"),
                "abstract": "",
                "citations": item.get("cited_by_count", 0) or 0,
                "url": item.get("primary_location", {}).get("landing_page_url", "") or item.get("id", ""),
                "doi": item.get("doi", "") or "",
                "countries": list(dict.fromkeys(countries)),
                "geo_points": geo_points,
            })
    st.session_state.search_cache[cache_key] = results
    return results

def search_related_articles(query: str, limit: int = 8):
    ss = semantic_scholar_search(query, limit=limit)
    cr = crossref_search(query, limit=max(4, limit // 2))
    oa = openalex_search(query, limit=max(4, limit // 2))
    merged = []
    seen = set()
    for group in [ss, cr, oa]:
        for item in group:
            key = normalize_spaces(item.get("title", "").lower())
            if key and key not in seen:
                merged.append(item)
                seen.add(key)
    merged.sort(key=lambda x: (x.get("citations") or 0, x.get("year") or 0), reverse=True)
    return merged[:limit]

def find_best_metadata_match(title: str):
    if not title:
        return {}
    candidates = search_related_articles(title, limit=5)
    title_norm = normalize_spaces(title.lower())
    scored = []
    for item in candidates:
        item_norm = normalize_spaces(item.get("title", "").lower())
        overlap = len(set(tokenize(title_norm)) & set(tokenize(item_norm)))
        scored.append((overlap, item))
    if not scored:
        return {}
    return sorted(scored, key=lambda x: x[0], reverse=True)[0][1]

def average_hash(image_obj, hash_size=8):
    if Image is None or np is None:
        return None
    img = image_obj.convert("L").resize((hash_size, hash_size))
    arr = np.asarray(img, dtype=np.float32)
    mean = arr.mean()
    return "".join("1" if p > mean else "0" for p in arr.flatten())

def hamming_distance(a, b):
    if not a or not b or len(a) != len(b):
        return 999
    return sum(ch1 != ch2 for ch1, ch2 in zip(a, b))

def image_descriptor(image_bytes: bytes):
    if Image is None or np is None:
        return {}
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        arr = np.asarray(img, dtype=np.float32)
        brightness = float(arr.mean())
        contrast = float(arr.std())
        hist_r = np.histogram(arr[:, :, 0], bins=16, range=(0, 255))[0].tolist()
        hist_g = np.histogram(arr[:, :, 1], bins=16, range=(0, 255))[0].tolist()
        hist_b = np.histogram(arr[:, :, 2], bins=16, range=(0, 255))[0].tolist()
        return {
            "width": img.size[0],
            "height": img.size[1],
            "brightness": round(brightness, 2),
            "contrast": round(contrast, 2),
            "hash": average_hash(img),
            "hist_r": hist_r,
            "hist_g": hist_g,
            "hist_b": hist_b,
        }
    except Exception:
        return {}

def hist_similarity(a, b):
    if not a or not b:
        return 0.0
    if np is None:
        return 0.0
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    if va.sum() == 0 or vb.sum() == 0:
        return 0.0
    va = va / (va.sum() + 1e-9)
    vb = vb / (vb.sum() + 1e-9)
    return float(1 - np.mean(np.abs(va - vb)))

def search_local_similar_images(target_bytes: bytes):
    target = image_descriptor(target_bytes)
    if not target:
        return []
    results = []
    for repo_name, repo in st.session_state.repositories.items():
        for file_item in repo.get("files", []):
            if file_item.get("kind") != "IMG":
                continue
            fp = Path(file_item.get("path", ""))
            if not fp.exists():
                continue
            other_bytes = fp.read_bytes()
            desc = file_item.get("image_descriptor") or image_descriptor(other_bytes)
            dist = hamming_distance(target.get("hash"), desc.get("hash"))
            sim_hash = max(0, 100 - dist * 4)
            sim_hist = 100 * (
                hist_similarity(target.get("hist_r"), desc.get("hist_r")) * 0.34 +
                hist_similarity(target.get("hist_g"), desc.get("hist_g")) * 0.33 +
                hist_similarity(target.get("hist_b"), desc.get("hist_b")) * 0.33
            )
            score = round(sim_hash * 0.55 + sim_hist * 0.45, 2)
            results.append({
                "repository": repo_name,
                "filename": file_item.get("filename"),
                "path": file_item.get("path"),
                "score": score,
                "descriptor": desc
            })
    return sorted(results, key=lambda x: x["score"], reverse=True)[:12]

def wikimedia_image_search(query: str, limit: int = 8):
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": 800,
        "format": "json",
        "gsrlimit": limit,
        "origin": "*"
    }
    results = []
    r = safe_request(url, params=params, timeout=15)
    if r is not None:
        pages = (r.json().get("query") or {}).get("pages", {})
        for _, page in pages.items():
            info = (page.get("imageinfo") or [{}])[0]
            if info.get("thumburl") or info.get("url"):
                results.append({
                    "title": page.get("title", "").replace("File:", ""),
                    "image_url": info.get("thumburl") or info.get("url"),
                    "page_url": info.get("descriptionurl") or info.get("url") or "",
                    "source": "Wikimedia Commons"
                })
    return results[:limit]

def extract_text_from_file(filename: str, file_bytes: bytes):
    kind = file_type(filename)
    if kind == "PDF":
        return extract_pdf_text(file_bytes)
    if kind == "DOCX":
        return extract_docx_text(file_bytes)
    if kind == "CSV":
        return extract_csv_text(file_bytes)
    if kind == "XLSX":
        return extract_xlsx_text(file_bytes)
    if kind == "TXT":
        return extract_txt_text(file_bytes)
    return ""

def infer_repository_theme(repo):
    analyses = [f.get("analysis", {}) for f in repo.get("files", []) if f.get("analysis")]
    counter = Counter()
    for an in analyses:
        for topic, score in (an.get("topics") or {}).items():
            counter[topic] += score
    if not counter:
        return "Pesquisa"
    return counter.most_common(1)[0][0]

def analyze_document(filename: str, file_bytes: bytes, area_hint: str = ""):
    kind = file_type(filename)
    text = extract_text_from_file(filename, file_bytes)
    analysis = {
        "filename": filename,
        "kind": kind,
        "word_count": 0,
        "reading_time": 0,
        "title": Path(filename).stem,
        "authors": [],
        "year": None,
        "summary": "",
        "keywords": [],
        "topics": {},
        "methodology": "Indefinida",
        "method_scores": {},
        "relevance_score": 50,
        "citations": 0,
        "doi": "",
        "source_url": "",
        "countries": [],
        "geo_points": [],
        "raw_excerpt": text[:2500],
    }
    if kind == "IMG":
        desc = image_descriptor(file_bytes)
        analysis.update({
            "title": Path(filename).stem.replace("_", " "),
            "summary": "Arquivo de imagem carregado no repositório.",
            "keywords": extract_keywords(Path(filename).stem.replace("_", " "), 8),
            "topics": {"Imagem de Pesquisa": 1},
            "image_descriptor": desc,
            "relevance_score": 55
        })
        return analysis

    text = normalize_spaces(text)
    analysis["word_count"] = len(text.split())
    analysis["reading_time"] = max(1, round(analysis["word_count"] / 220)) if analysis["word_count"] else 0
    analysis["title"] = guess_title(filename, text)
    analysis["authors"] = guess_authors(text)
    years = detect_years(text)
    analysis["year"] = years.most_common(1)[0][0] if years else None
    analysis["keywords"] = extract_keywords(text, 24)
    analysis["topics"] = detect_topics(" ".join(analysis["keywords"]) + " " + text[:5000])
    analysis["summary"] = summarize_text(text, max_sentences=4) or "Resumo automático indisponível."
    methodology, method_scores = detect_methodology(text[:12000])
    analysis["methodology"] = methodology
    analysis["method_scores"] = method_scores

    title_match = find_best_metadata_match(analysis["title"])
    if title_match:
        analysis["citations"] = title_match.get("citations", 0) or 0
        analysis["doi"] = title_match.get("doi", "") or ""
        analysis["source_url"] = title_match.get("url", "") or ""
        if not analysis["year"]:
            analysis["year"] = title_match.get("year")
        if not analysis["authors"]:
            authors = [a.strip() for a in (title_match.get("authors") or "").split(",") if a.strip()]
            analysis["authors"] = authors[:8]
        if title_match.get("countries"):
            analysis["countries"] = [COUNTRY_CODE_TO_NAME.get(c, c) for c in title_match.get("countries", [])]
        if title_match.get("geo_points"):
            analysis["geo_points"] = title_match.get("geo_points", [])

    area_hint_norm = area_hint.lower()
    topic_overlap = sum(1 for topic in analysis["topics"] if topic.lower() in area_hint_norm)
    kw_overlap = sum(1 for kw in analysis["keywords"][:12] if kw.lower() in area_hint_norm)
    quality = 0
    quality += 25 if analysis["word_count"] > 800 else 10
    quality += 20 if len(analysis["keywords"]) > 12 else 5
    quality += 20 if analysis["summary"] else 0
    quality += 10 if analysis["year"] else 0
    quality += 15 if analysis["authors"] else 0
    quality += 10 if analysis["citations"] else 0
    analysis["relevance_score"] = min(99, max(35, quality + topic_overlap * 6 + kw_overlap * 3))
    return analysis

def record_user_interest(query: str, topics=None):
    email = st.session_state.get("current_user")
    if not email:
        return
    hist = st.session_state.users[email].setdefault("history", [])
    hist.append({
        "query": query,
        "topics": list((topics or {}).keys())[:6] if isinstance(topics, dict) else [],
        "time": now_str()
    })
    hist[:] = hist[-120:]
    save_state()

def current_interest_profile():
    email = st.session_state.get("current_user")
    user = st.session_state.users.get(email, {})
    area = user.get("area", "")
    topics = Counter()
    kws = Counter(tokenize(area))
    for item in user.get("history", [])[-50:]:
        for topic in item.get("topics", []):
            topics[topic] += 2
        for tok in tokenize(item.get("query", "")):
            kws[tok] += 1
    for repo in st.session_state.repositories.values():
        for f in repo.get("files", []):
            an = f.get("analysis", {})
            for topic, score in (an.get("topics") or {}).items():
                topics[topic] += score
            for kw in an.get("keywords", [])[:10]:
                kws[kw] += 1
    return {
        "topics": dict(topics.most_common(8)),
        "keywords": [k for k, _ in kws.most_common(18)]
    }

def local_document_corpus():
    docs = []
    for repo_name, repo in st.session_state.repositories.items():
        for file_item in repo.get("files", []):
            an = file_item.get("analysis", {})
            if not an or file_item.get("kind") == "IMG":
                continue
            text_blob = " ".join([
                an.get("title", ""),
                an.get("summary", ""),
                " ".join(an.get("keywords", [])),
                " ".join((an.get("topics") or {}).keys()),
                an.get("methodology", ""),
                repo_name,
                repo.get("description", "")
            ])
            docs.append({
                "repository": repo_name,
                "filename": file_item.get("filename"),
                "path": file_item.get("path"),
                "analysis": an,
                "text_blob": text_blob,
            })
    return docs

def local_semantic_search(query: str, limit: int = 12):
    docs = local_document_corpus()
    if not docs:
        return []
    q_blob = normalize_spaces(query)
    if TfidfVectorizer is None or cosine_similarity is None:
        q_tokens = set(tokenize(q_blob))
        scored = []
        for item in docs:
            d_tokens = set(tokenize(item["text_blob"]))
            inter = len(q_tokens & d_tokens)
            union = len(q_tokens | d_tokens) or 1
            score = inter / union
            scored.append((score, item))
        return [
            {
                **item,
                "score": round(score * 100, 2)
            }
            for score, item in sorted(scored, key=lambda x: x[0], reverse=True)[:limit]
            if score > 0
        ]

    corpus = [d["text_blob"] for d in docs] + [q_blob]
    vec = TfidfVectorizer(stop_words=None, ngram_range=(1, 2), min_df=1)
    matrix = vec.fit_transform(corpus)
    sims = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
    ranked = []
    for score, item in sorted(zip(sims, docs), key=lambda x: x[0], reverse=True)[:limit]:
        if score <= 0:
            continue
        ranked.append({
            **item,
            "score": round(float(score) * 100, 2)
        })
    return ranked

def derive_query_suggestions(query: str, profile: dict, local_hits, web_hits):
    suggestions = []
    topics = list(profile.get("topics", {}).keys())
    kws = profile.get("keywords", [])[:6]
    if topics:
        suggestions.append(f"{query} {' '.join(topics[:2])}".strip())
    if kws:
        suggestions.append(f"{query} {' '.join(kws[:3])}".strip())
    if local_hits:
        best_topics = list((local_hits[0].get("analysis", {}).get("topics") or {}).keys())[:2]
        if best_topics:
            suggestions.append(" ".join(best_topics))
    if web_hits:
        latest = [w for w in web_hits if w.get("year")]
        if latest:
            suggestions.append(f"{query} revisão {sorted([w['year'] for w in latest if w.get('year')], reverse=True)[0]}")
    seen = []
    for s in suggestions:
        s = normalize_spaces(s)
        if s and s not in seen and s.lower() != query.lower():
            seen.append(s)
    return seen[:5]

def discover(query: str, image_bytes=None):
    profile = current_interest_profile()
    query_topics = detect_topics(query)
    local_hits = local_semantic_search(query, limit=12)
    web_hits = search_related_articles(query, limit=12)
    local_images = search_local_similar_images(image_bytes) if image_bytes else []
    online_images = wikimedia_image_search(query, limit=8) if query else []

    record_user_interest(query, query_topics)
    result = {
        "query": query,
        "query_topics": query_topics,
        "local_hits": local_hits,
        "web_hits": web_hits,
        "local_images": local_images,
        "online_images": online_images,
        "profile": profile,
        "suggestions": derive_query_suggestions(query, profile, local_hits, web_hits)
    }
    st.session_state.discovery_result = result
    return result

def all_analyses():
    rows = []
    for repo_name, repo in st.session_state.repositories.items():
        for file_item in repo.get("files", []):
            an = file_item.get("analysis")
            if an:
                rows.append({
                    "repository": repo_name,
                    "filename": file_item.get("filename"),
                    **an
                })
    return rows

def compute_connections():
    docs = local_document_corpus()
    if len(docs) < 2:
        return {"nodes": docs, "edges": []}
    edges = []
    texts = [d["text_blob"] for d in docs]
    if TfidfVectorizer is not None and cosine_similarity is not None:
        vec = TfidfVectorizer(stop_words=None, ngram_range=(1, 2), min_df=1)
        mat = vec.fit_transform(texts)
        sims = cosine_similarity(mat)
        for i in range(len(docs)):
            for j in range(i + 1, len(docs)):
                score = float(sims[i, j])
                if score >= 0.20:
                    shared_topics = list(
                        set((docs[i]["analysis"].get("topics") or {}).keys())
                        & set((docs[j]["analysis"].get("topics") or {}).keys())
                    )
                    shared_keywords = list(
                        set(docs[i]["analysis"].get("keywords", [])[:18])
                        & set(docs[j]["analysis"].get("keywords", [])[:18])
                    )
                    edges.append({
                        "source": i,
                        "target": j,
                        "score": round(score * 100, 2),
                        "shared_topics": shared_topics[:5],
                        "shared_keywords": shared_keywords[:8],
                    })
    else:
        for i in range(len(docs)):
            for j in range(i + 1, len(docs)):
                kw1 = set(docs[i]["analysis"].get("keywords", [])[:18])
                kw2 = set(docs[j]["analysis"].get("keywords", [])[:18])
                union = len(kw1 | kw2) or 1
                inter = len(kw1 & kw2)
                score = inter / union
                if score >= 0.15:
                    edges.append({
                        "source": i,
                        "target": j,
                        "score": round(score * 100, 2),
                        "shared_topics": list(set((docs[i]["analysis"].get("topics") or {}).keys()) & set((docs[j]["analysis"].get("topics") or {}).keys())),
                        "shared_keywords": list(kw1 & kw2)[:8],
                    })
    return {"nodes": docs, "edges": sorted(edges, key=lambda x: x["score"], reverse=True)}

def metrics_snapshot():
    repos = st.session_state.repositories
    total_repos = len(repos)
    total_files = sum(len(repo.get("files", [])) for repo in repos.values())
    analyses = all_analyses()
    total_analyzed = len(analyses)
    total_topics = len(set(topic for row in analyses for topic in (row.get("topics") or {}).keys()))
    return {
        "repos": total_repos,
        "files": total_files,
        "analyzed": total_analyzed,
        "topics": total_topics
    }

def build_analysis_dataset():
    rows = all_analyses()
    year_counter = Counter()
    theme_counter = Counter()
    author_counter = Counter()
    method_counter = Counter()
    country_counter = Counter()
    globe_points = []
    for row in rows:
        if row.get("year"):
            year_counter[int(row["year"])] += 1
        if row.get("topics"):
            for topic, score in row["topics"].items():
                theme_counter[topic] += score
        for author in row.get("authors", [])[:6]:
            author_counter[author] += 1
        if row.get("methodology"):
            method_counter[row["methodology"]] += 1
        for country in row.get("countries", [])[:8]:
            country_counter[country] += 1
        for gp in row.get("geo_points", []):
            globe_points.append(gp)
    return {
        "rows": rows,
        "year_counter": year_counter,
        "theme_counter": theme_counter,
        "author_counter": author_counter,
        "method_counter": method_counter,
        "country_counter": country_counter,
        "globe_points": globe_points,
    }

def suggest_articles_for_repository(repo_name: str):
    repo = st.session_state.repositories.get(repo_name, {})
    texts = []
    for item in repo.get("files", []):
        an = item.get("analysis", {})
        texts.extend(an.get("keywords", [])[:8])
        texts.extend(list((an.get("topics") or {}).keys())[:4])
    query = " ".join(list(dict.fromkeys(texts))[:8]) or repo_name
    return search_related_articles(query, limit=8)

def apply_file_analysis(repo_name: str, file_index: int):
    repo = st.session_state.repositories[repo_name]
    file_item = repo["files"][file_index]
    file_path = Path(file_item["path"])
    if not file_path.exists():
        return
    file_bytes = file_path.read_bytes()
    area = user_data().get("area", "")
    analysis = analyze_document(file_item["filename"], file_bytes, area)
    file_item["analysis"] = analysis
    if file_item["kind"] == "IMG":
        file_item["image_descriptor"] = analysis.get("image_descriptor") or image_descriptor(file_bytes)
    save_state()

def batch_analyze_repository(repo_name: str):
    repo = st.session_state.repositories[repo_name]
    for idx in range(len(repo.get("files", []))):
        apply_file_analysis(repo_name, idx)

def liquid_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@500;700;800&family=Inter:wght@300;400;500;600;700;800&display=swap');

        :root{
            --bg:#050814;
            --bg2:#0a1324;
            --bg3:#101c31;
            --glass:rgba(255,255,255,.055);
            --glass2:rgba(255,255,255,.08);
            --border:rgba(255,255,255,.11);
            --text:#eef3ff;
            --muted:#99a6c7;
            --muted2:#7382a5;
            --accent:#6bd0ff;
            --accent2:#88b3ff;
            --accent3:#d0b5ff;
            --danger:#ff6b8a;
        }

        html, body, .stApp{
            background:
                radial-gradient(circle at 10% 0%, rgba(137,183,255,.10), transparent 32%),
                radial-gradient(circle at 100% 0%, rgba(107,208,255,.08), transparent 28%),
                radial-gradient(circle at 50% 100%, rgba(208,181,255,.07), transparent 38%),
                linear-gradient(180deg, #050814 0%, #08101f 100%);
            color: var(--text);
            font-family: 'Inter', sans-serif;
        }

        header, #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"]{
            display:none !important;
        }

        .block-container{
            padding-top:0.55rem !important;
            max-width:1450px !important;
        }

        section[data-testid="stSidebar"]{
            background: rgba(7, 12, 24, .88) !important;
            border-right: 1px solid rgba(255,255,255,.06) !important;
            backdrop-filter: blur(32px) saturate(170%) !important;
        }

        section[data-testid="stSidebar"] > div{
            padding-top: 1rem !important;
        }

        .shell-top{
            background: linear-gradient(90deg, rgba(255,255,255,.03), rgba(255,255,255,.02));
            border: 1px solid rgba(255,255,255,.07);
            border-radius: 24px;
            padding: 18px 24px;
            backdrop-filter: blur(24px);
            box-shadow: 0 8px 30px rgba(0,0,0,.25), inset 0 1px 0 rgba(255,255,255,.05);
            margin-bottom: 18px;
        }

        .shell-title{
            font-family: 'Syne', sans-serif;
            font-size: 2.05rem;
            font-weight: 800;
            letter-spacing: -.04em;
            color: var(--text);
        }

        .shell-brand{
            font-family: 'Syne', sans-serif;
            font-size: 1.05rem;
            font-weight: 700;
            color: #d7e3ff;
            margin-bottom: 4px;
        }

        .muted{
            color: var(--muted);
            font-size: .92rem;
        }

        .hero{
            text-align:center;
            padding: 8px 0 18px 0;
        }

        .hero h1{
            font-family:'Syne', sans-serif !important;
            font-size:3rem !important;
            font-weight:800 !important;
            letter-spacing:-.05em !important;
            color: #f7fbff !important;
            margin-bottom:.2rem !important;
        }

        .hero p{
            color: var(--muted);
            font-size: 1rem;
            margin-bottom: 0;
        }

        .glass-card{
            background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.04));
            border: 1px solid var(--border);
            border-radius: 26px;
            padding: 20px 20px;
            backdrop-filter: blur(28px) saturate(160%);
            box-shadow: 0 12px 38px rgba(0,0,0,.26), inset 0 1px 0 rgba(255,255,255,.08);
            margin-bottom: 12px;
        }

        .metric-card{
            background: linear-gradient(180deg, rgba(255,255,255,.065), rgba(255,255,255,.045));
            border: 1px solid rgba(255,255,255,.10);
            border-radius: 22px;
            padding: 24px 18px;
            min-height: 145px;
            box-shadow: 0 10px 28px rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.06);
        }

        .metric-label{
            color:#d6deef;
            font-size:.86rem;
            text-transform:uppercase;
            letter-spacing:.14em;
            font-weight:700;
            opacity:.95;
        }

        .metric-value{
            font-family:'Syne', sans-serif;
            font-size:3rem;
            font-weight:800;
            letter-spacing:-.04em;
            margin-top:16px;
            color:#eaf4ff;
        }

        .metric-caption{
            color: var(--muted);
            font-size: .9rem;
            margin-top: 10px;
        }

        .soft-title{
            font-family:'Syne', sans-serif;
            font-weight:700;
            font-size:1.9rem;
            letter-spacing:-.03em;
            margin-bottom:.4rem;
        }

        .subline{
            color: var(--muted);
            font-size: .95rem;
            margin-bottom: .8rem;
        }

        .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button{
            background: linear-gradient(180deg, rgba(255,255,255,.10), rgba(255,255,255,.06)) !important;
            border: 1px solid rgba(255,255,255,.15) !important;
            border-radius: 18px !important;
            color: #f6fbff !important;
            box-shadow: 0 8px 20px rgba(0,0,0,.18), inset 0 1px 0 rgba(255,255,255,.08) !important;
            backdrop-filter: blur(18px) !important;
            font-weight: 600 !important;
            padding: .55rem .95rem !important;
        }

        .stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover{
            border-color: rgba(107,208,255,.36) !important;
            background: linear-gradient(180deg, rgba(107,208,255,.17), rgba(255,255,255,.07)) !important;
        }

        .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"], .stNumberInput input{
            background: rgba(255,255,255,.05) !important;
            color: #eef3ff !important;
            border: 1px solid rgba(255,255,255,.12) !important;
            border-radius: 18px !important;
        }

        .stTabs [data-baseweb="tab-list"]{
            gap: 6px;
            background: rgba(255,255,255,.04);
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 20px;
            padding: 8px;
        }

        .stTabs [data-baseweb="tab"]{
            height: 44px;
            border-radius: 14px !important;
            color: var(--muted) !important;
            font-weight: 600;
        }

        .stTabs [aria-selected="true"]{
            background: linear-gradient(180deg, rgba(255,255,255,.11), rgba(107,208,255,.10)) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255,255,255,.16) !important;
        }

        .table-chip{
            display:inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            background: rgba(255,255,255,.08);
            border: 1px solid rgba(255,255,255,.10);
            color:#eef3ff;
            margin: 2px 5px 2px 0;
            font-size: .78rem;
        }

        .repo-row, .article-row, .insight-row{
            background: linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.03));
            border: 1px solid rgba(255,255,255,.09);
            border-radius: 18px;
            padding: 16px 18px;
            margin-bottom: 10px;
        }

        .mini{
            color: var(--muted);
            font-size: .84rem;
        }

        .stFileUploader section{
            background: rgba(255,255,255,.04) !important;
            border: 1.5px dashed rgba(255,255,255,.16) !important;
            border-radius: 18px !important;
        }

        .nav-name{
            font-family:'Syne', sans-serif;
            font-size: 1.2rem;
            font-weight: 700;
            letter-spacing:-.03em;
            color:#f1f6ff;
            margin-bottom: .2rem;
        }

        .nav-mini{
            color: var(--muted);
            font-size: .84rem;
        }

        .profile-badge{
            width:54px;height:54px;border-radius:18px;display:flex;align-items:center;justify-content:center;
            background: linear-gradient(180deg, rgba(255,255,255,.11), rgba(107,208,255,.12));
            border:1px solid rgba(255,255,255,.14);
            font-family:'Syne', sans-serif;font-weight:800;font-size:1.1rem;color:#fff;
        }

        .auth-shell{
            max-width: 560px;
            margin: 4rem auto 0 auto;
            padding: 28px;
            border-radius: 28px;
            background: linear-gradient(180deg, rgba(255,255,255,.07), rgba(255,255,255,.04));
            border: 1px solid rgba(255,255,255,.10);
            backdrop-filter: blur(30px);
            box-shadow: 0 16px 48px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.06);
        }

        .auth-brand{
            text-align:center;
            margin-bottom: 22px;
        }

        .auth-brand h1{
            font-family:'Syne', sans-serif !important;
            font-size:2.4rem !important;
            font-weight:800 !important;
            letter-spacing:-.05em !important;
            margin-bottom:.25rem !important;
        }

        .auth-brand p{
            color: var(--muted);
            margin-bottom: 0;
        }

        .section-sep{
            color: var(--muted2);
            text-transform: uppercase;
            letter-spacing: .15em;
            font-weight: 700;
            font-size: .74rem;
            margin: .25rem 0 .7rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def render_shell(page_title: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div class="shell-top">
            <div class="shell-brand">{APP_TITLE}</div>
            <div class="muted">{APP_SUBTITLE}</div>
        </div>
        <div class="hero">
            <h1>{page_title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_nav():
    with st.sidebar:
        user = user_data()
        st.markdown('<div class="nav-name">Sistema Folksonomia Digital</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-mini">Ambiente de pesquisa, busca e análise</div>', unsafe_allow_html=True)
        st.write("")
        col_a, col_b = st.columns([1, 3])
        with col_a:
            st.markdown(f'<div class="profile-badge">{initials(user.get("name","U"))}</div>', unsafe_allow_html=True)
        with col_b:
            st.markdown(f'<div style="font-weight:700;color:#f3f7ff">{user.get("name","Usuário")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="nav-mini">{user.get("area","Sem área definida")}</div>', unsafe_allow_html=True)
        st.write("")
        nav_items = [
            ("dashboard", "Dashboard"),
            ("discovery", "Pesquisa Inteligente"),
            ("repositories", "Repositórios"),
            ("connections", "Conexões"),
            ("analytics", "Análises"),
            ("account", "Conta"),
        ]
        for key, label in nav_items:
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.page = key
                st.rerun()
        st.write("")
        if st.button("Sair do sistema", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.rerun()

def page_login():
    st.markdown('<div class="auth-shell">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="auth-brand">
            <h1>Sistema Folksonomia Digital</h1>
            <p>Plataforma redesenhada sem feed social, com foco em pesquisa, repositório e análise acadêmica.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    tab_login, tab_signup = st.tabs(["Entrar", "Criar conta"])
    with tab_login:
        with st.form("login_form"):
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
                    st.session_state.page = "dashboard"
                    st.rerun()
        st.caption("Conta de demonstração: demo@folksonomia.ai | senha: demo123")
    with tab_signup:
        with st.form("signup_form"):
            name = st.text_input("Nome completo")
            email = st.text_input("E-mail")
            area = st.text_input("Área de pesquisa")
            password = st.text_input("Senha", type="password")
            password_2 = st.text_input("Confirmar senha", type="password")
            submit = st.form_submit_button("Criar conta", use_container_width=True)
            if submit:
                if not all([name, email, area, password, password_2]):
                    st.error("Preencha todos os campos.")
                elif password != password_2:
                    st.error("As senhas não coincidem.")
                elif email in st.session_state.users:
                    st.error("Este e-mail já está cadastrado.")
                else:
                    st.session_state.users[email] = {
                        "name": name,
                        "password": sha(password),
                        "area": area,
                        "bio": "",
                        "history": [],
                        "saved_articles": []
                    }
                    save_state()
                    st.session_state.logged_in = True
                    st.session_state.current_user = email
                    st.session_state.page = "dashboard"
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def dashboard_metrics():
    snap = metrics_snapshot()
    cols = st.columns(4)
    data = [
        ("TOTAL DE REPOSITÓRIOS", snap["repos"], "repositórios cadastrados"),
        ("ARQUIVOS INDEXADOS", snap["files"], "itens no sistema"),
        ("ARQUIVOS ANALISADOS", snap["analyzed"], "com leitura automática"),
        ("TEMAS IDENTIFICADOS", snap["topics"], "eixos temáticos"),
    ]
    for col, (label, value, caption) in zip(cols, data):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                    <div class="metric-caption">{caption}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

def page_dashboard():
    render_shell("Dashboard Administrativo", f"Bem-vindo, {user_data().get('name','usuário')}")
    dashboard_metrics()
    analysis_data = build_analysis_dataset()
    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="soft-title">Resumo do sistema</div>', unsafe_allow_html=True)
        st.markdown('<div class="subline">Visão consolidada das pesquisas armazenadas e das preferências mais recentes do usuário.</div>', unsafe_allow_html=True)
        profile = current_interest_profile()
        if profile["topics"]:
            st.markdown('<div class="section-sep">Temas dominantes</div>', unsafe_allow_html=True)
            for topic, score in profile["topics"].items():
                st.markdown(f'<span class="table-chip">{topic} ({score})</span>', unsafe_allow_html=True)
        else:
            st.info("Ainda não há histórico suficiente para perfil temático.")
        if profile["keywords"]:
            st.markdown('<div class="section-sep">Palavras-chave predominantes</div>', unsafe_allow_html=True)
            for kw in profile["keywords"][:12]:
                st.markdown(f'<span class="table-chip">{kw}</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="soft-title">Sugestões para começar</div>', unsafe_allow_html=True)
        suggestions = []
        if profile["keywords"]:
            suggestions.extend([
                " ".join(profile["keywords"][:4]),
                " ".join(profile["keywords"][:3] + ["revisão"]),
            ])
        if analysis_data["theme_counter"]:
            top_theme = analysis_data["theme_counter"].most_common(1)[0][0]
            suggestions.append(f"{top_theme} artigos recentes")
        if not suggestions:
            suggestions = [
                "folksonomia museus documentação",
                "inteligência artificial preservação digital",
                "análise de repositório acadêmico"
            ]
        for s in suggestions[:5]:
            if st.button(s, key=f"dash_sug_{s}", use_container_width=True):
                st.session_state.page = "discovery"
                st.session_state.discovery_prefill = s
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="soft-title">Repositórios</div>', unsafe_allow_html=True)
        if not st.session_state.repositories:
            st.info("Crie seu primeiro repositório para iniciar a indexação.")
        else:
            for repo_name, repo in st.session_state.repositories.items():
                analyzed = sum(1 for f in repo.get("files", []) if f.get("analysis"))
                theme = infer_repository_theme(repo)
                st.markdown(
                    f"""
                    <div class="repo-row">
                        <div style="font-weight:700;color:#f2f7ff">{repo_name}</div>
                        <div class="mini">{repo.get("description","Sem descrição")}</div>
                        <div class="mini" style="margin-top:6px">Arquivos: {len(repo.get("files", []))} | Analisados: {analyzed} | Tema principal: {theme}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        st.markdown('</div>', unsafe_allow_html=True)

def render_article_card(article: dict, save_key: str = ""):
    st.markdown('<div class="article-row">', unsafe_allow_html=True)
    st.markdown(f"**{article.get('title','Sem título')}**")
    meta = " | ".join([
        str(article.get("year") or "Ano não identificado"),
        article.get("authors") or "Autores não identificados",
        article.get("source") or "Fonte não identificada"
    ])
    st.caption(meta)
    if article.get("abstract"):
        st.write(article["abstract"][:900])
    c1, c2 = st.columns([1, 1])
    with c1:
        if article.get("url"):
            st.link_button("Abrir referência", article["url"], use_container_width=True)
    with c2:
        if st.button("Salvar referência", key=save_key, use_container_width=True):
            st.session_state.saved_articles_global.append(article)
            user = user_data()
            user.setdefault("saved_articles", []).append(article)
            save_state()
            st.success("Referência salva.")
    st.markdown('</div>', unsafe_allow_html=True)

def page_discovery():
    render_shell("Pesquisa Inteligente", "Busca unificada para artigos, arquivos do sistema e imagens relacionadas")
    if "discovery_prefill" in st.session_state:
        default_q = st.session_state.pop("discovery_prefill")
    else:
        default_q = ""

    top_left, top_right = st.columns([2.2, 1])
    with top_left:
        query = st.text_input("Consulta", value=default_q, placeholder="Digite tema, pergunta, conceito ou problema de pesquisa", key="discovery_query")
    with top_right:
        image_file = st.file_uploader("Imagem opcional para busca visual", type=["png", "jpg", "jpeg", "webp", "bmp"], key="discovery_image")

    if st.button("Executar busca integrada", use_container_width=True):
        if query.strip():
            image_bytes = image_file.read() if image_file else None
            with st.spinner("Analisando consulta e cruzando sistema com internet..."):
                discover(query.strip(), image_bytes=image_bytes)
        else:
            st.warning("Digite uma consulta para iniciar a busca.")

    result = st.session_state.get("discovery_result")
    if not result:
        st.markdown('<div class="glass-card"><div class="soft-title">Busca integrada</div><div class="subline">Esta tela substitui a antiga separação entre busca textual e visão computacional. Agora a mesma consulta verifica arquivos locais, internet e imagens relacionadas.</div></div>', unsafe_allow_html=True)
        return

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="soft-title">Entendimento da consulta</div>', unsafe_allow_html=True)
    st.caption(f"Consulta analisada: {result['query']}")
    for topic, score in result["query_topics"].items():
        st.markdown(f'<span class="table-chip">{topic} ({score})</span>', unsafe_allow_html=True)
    if result["suggestions"]:
        st.markdown('<div class="section-sep">Sugestões de refinamento</div>', unsafe_allow_html=True)
        sug_cols = st.columns(min(5, len(result["suggestions"])))
        for col, sug in zip(sug_cols, result["suggestions"]):
            with col:
                if st.button(sug, key=f"q_sug_{sug}", use_container_width=True):
                    st.session_state.discovery_prefill = sug
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    tabs = st.tabs([
        f"Sistema ({len(result['local_hits'])})",
        f"Internet ({len(result['web_hits'])})",
        f"Imagens locais ({len(result['local_images'])})",
        f"Imagens relacionadas ({len(result['online_images'])})",
    ])

    with tabs[0]:
        if not result["local_hits"]:
            st.info("Nenhum arquivo local compatível foi localizado. Analise seus arquivos dentro dos repositórios para habilitar a busca semântica.")
        else:
            for idx, hit in enumerate(result["local_hits"]):
                an = hit["analysis"]
                st.markdown(
                    f"""
                    <div class="repo-row">
                        <div style="font-weight:700;color:#f7fbff">{an.get('title', hit['filename'])}</div>
                        <div class="mini">Repositório: {hit['repository']} | Arquivo: {hit['filename']} | Similaridade: {hit['score']:.1f}</div>
                        <div class="mini">Autores: {", ".join(an.get('authors', [])[:4]) if an.get('authors') else "Não identificados"} | Ano: {an.get('year') or "Não identificado"} | Método: {an.get('methodology')}</div>
                        <div style="margin-top:10px">{an.get('summary', '')[:900]}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if an.get("keywords"):
                    for kw in an["keywords"][:10]:
                        st.markdown(f'<span class="table-chip">{kw}</span>', unsafe_allow_html=True)

    with tabs[1]:
        if not result["web_hits"]:
            st.info("Nenhuma referência externa foi encontrada no momento.")
        else:
            for idx, article in enumerate(result["web_hits"]):
                render_article_card(article, save_key=f"save_article_{idx}")

    with tabs[2]:
        if not result["local_images"]:
            st.info("Nenhuma imagem semelhante foi encontrada dentro dos repositórios do sistema.")
        else:
            cols = st.columns(2)
            for i, item in enumerate(result["local_images"]):
                with cols[i % 2]:
                    st.markdown(
                        f"""
                        <div class="repo-row">
                            <div style="font-weight:700;color:#f2f8ff">{item['filename']}</div>
                            <div class="mini">Repositório: {item['repository']} | Similaridade visual: {item['score']:.1f}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    try:
                        st.image(item["path"], use_container_width=True)
                    except Exception:
                        pass

    with tabs[3]:
        if not result["online_images"]:
            st.info("Não foi possível localizar imagens relacionadas na internet para esta consulta.")
        else:
            cols = st.columns(2)
            for i, item in enumerate(result["online_images"]):
                with cols[i % 2]:
                    st.markdown(f'<div class="repo-row"><div style="font-weight:700;color:#f2f8ff">{item["title"]}</div><div class="mini">{item["source"]}</div></div>', unsafe_allow_html=True)
                    if item.get("image_url"):
                        st.image(item["image_url"], use_container_width=True)
                    if item.get("page_url"):
                        st.link_button("Abrir página", item["page_url"], use_container_width=True)

def page_repositories():
    render_shell("Repositórios", "Gestão de arquivos, análise automática e sugestões de leitura relacionadas")
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="soft-title">Criar novo repositório</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([2, 3])
    with c1:
        repo_name = st.text_input("Nome do repositório", key="new_repo_name", placeholder="Ex: Estudo de público e museologia")
    with c2:
        repo_desc = st.text_input("Descrição", key="new_repo_desc", placeholder="Objetivo, escopo ou problema de pesquisa")
    if st.button("Criar repositório", use_container_width=True):
        if not repo_name.strip():
            st.warning("Informe o nome do repositório.")
        elif repo_name in st.session_state.repositories:
            st.warning("Já existe um repositório com esse nome.")
        else:
            slug = slugify(repo_name)
            st.session_state.repositories[repo_name] = {
                "slug": slug,
                "description": repo_desc,
                "created_at": now_str(),
                "files": []
            }
            ensure_repo_dir(slug)
            save_state()
            st.success("Repositório criado com sucesso.")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if not st.session_state.repositories:
        st.info("Nenhum repositório cadastrado ainda.")
        return

    for repo_name, repo in list(st.session_state.repositories.items()):
        analyzed = sum(1 for f in repo.get("files", []) if f.get("analysis"))
        with st.expander(f"{repo_name} | Arquivos: {len(repo.get('files', []))} | Analisados: {analyzed}", expanded=False):
            st.caption(repo.get("description", "Sem descrição"))
            up = st.file_uploader(
                f"Adicionar arquivos em {repo_name}",
                key=f"upload_{repo_name}",
                accept_multiple_files=True
            )
            if up:
                repo_dir = ensure_repo_dir(repo["slug"])
                existing_names = {item["filename"] for item in repo["files"]}
                added = 0
                for uf in up:
                    if uf.name in existing_names:
                        continue
                    content = uf.read()
                    file_path = repo_dir / uf.name
                    file_path.write_bytes(content)
                    item = {
                        "filename": uf.name,
                        "path": str(file_path),
                        "kind": file_type(uf.name),
                        "uploaded_at": now_str(),
                        "analysis": {}
                    }
                    if item["kind"] == "IMG":
                        item["image_descriptor"] = image_descriptor(content)
                    repo["files"].append(item)
                    added += 1
                save_state()
                if added:
                    st.success(f"{added} arquivo(s) adicionados.")
                    st.rerun()

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("Analisar tudo", key=f"analyze_all_{repo_name}", use_container_width=True):
                    with st.spinner("Executando análise automática do repositório..."):
                        batch_analyze_repository(repo_name)
                    st.success("Análise concluída.")
                    st.rerun()
            with c2:
                if st.button("Sugerir leituras", key=f"suggest_read_{repo_name}", use_container_width=True):
                    st.session_state[f"suggested_{repo_name}"] = suggest_articles_for_repository(repo_name)
            with c3:
                if st.button("Excluir repositório", key=f"delete_repo_{repo_name}", use_container_width=True):
                    del st.session_state.repositories[repo_name]
                    save_state()
                    st.rerun()

            if repo.get("files"):
                for idx, file_item in enumerate(repo["files"]):
                    analysis = file_item.get("analysis") or {}
                    st.markdown(
                        f"""
                        <div class="repo-row">
                            <div style="font-weight:700;color:#f7fbff">{file_item['filename']}</div>
                            <div class="mini">Tipo: {file_item['kind']} | Enviado em: {file_item['uploaded_at']}</div>
                            <div class="mini">Título identificado: {analysis.get('title','Não analisado')}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    cols = st.columns([1, 1, 3])
                    with cols[0]:
                        if st.button("Analisar arquivo", key=f"an_file_{repo_name}_{idx}", use_container_width=True):
                            with st.spinner("Lendo arquivo e enriquecendo metadados..."):
                                apply_file_analysis(repo_name, idx)
                            st.success("Arquivo analisado.")
                            st.rerun()
                    with cols[1]:
                        if st.button("Excluir arquivo", key=f"del_file_{repo_name}_{idx}", use_container_width=True):
                            fp = Path(file_item["path"])
                            try:
                                if fp.exists():
                                    fp.unlink()
                            except Exception:
                                pass
                            repo["files"].pop(idx)
                            save_state()
                            st.rerun()
                    with cols[2]:
                        if analysis:
                            st.write(f"Resumo: {analysis.get('summary','')[:900]}")
                            meta = [
                                f"Ano: {analysis.get('year') or 'Não identificado'}",
                                f"Método: {analysis.get('methodology') or 'Indefinido'}",
                                f"Relevância: {analysis.get('relevance_score')}",
                                f"Citações: {analysis.get('citations') or 0}",
                            ]
                            st.caption(" | ".join(meta))
                            for kw in analysis.get("keywords", [])[:12]:
                                st.markdown(f'<span class="table-chip">{kw}</span>', unsafe_allow_html=True)
                        elif file_item["kind"] == "IMG":
                            st.caption("Arquivo de imagem pronto para busca visual local.")
                        else:
                            st.caption("Arquivo ainda não analisado.")

            suggestions = st.session_state.get(f"suggested_{repo_name}", [])
            if suggestions:
                st.markdown('<div class="section-sep">Sugestões de leitura relacionadas ao repositório</div>', unsafe_allow_html=True)
                for idx, article in enumerate(suggestions):
                    render_article_card(article, save_key=f"save_repo_article_{repo_name}_{idx}")

def page_connections():
    render_shell("Conexões", "Relações entre pesquisas semelhantes, padrões comuns e proximidades temáticas")
    graph = compute_connections()
    nodes = graph["nodes"]
    edges = graph["edges"]
    if not nodes:
        st.info("Analise arquivos nos repositórios para construir a rede de conexões.")
        return

    if go is not None:
        n = len(nodes)
        xs = [math.cos(2 * math.pi * i / max(1, n)) for i in range(n)]
        ys = [math.sin(2 * math.pi * i / max(1, n)) for i in range(n)]
        fig = go.Figure()
        for edge in edges:
            i = edge["source"]
            j = edge["target"]
            fig.add_trace(
                go.Scatter(
                    x=[xs[i], xs[j]],
                    y=[ys[i], ys[j]],
                    mode="lines",
                    line=dict(width=max(1, edge["score"] / 18), color="rgba(135,196,255,.42)"),
                    hoverinfo="none",
                    showlegend=False
                )
            )
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="markers+text",
                text=[f"{Path(node['filename']).stem[:18]}" for node in nodes],
                textposition="top center",
                marker=dict(size=18, color="#90c5ff", line=dict(color="rgba(255,255,255,.4)", width=1)),
                hovertemplate=[
                    f"<b>{node['analysis'].get('title', node['filename'])}</b><br>{node['repository']}<extra></extra>"
                    for node in nodes
                ],
                showlegend=False
            )
        )
        fig.update_layout(
            height=520,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(showgrid=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, zeroline=False, visible=False),
        )
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">NÓS</div><div class="metric-value">{len(nodes)}</div><div class="metric-caption">documentos na rede</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">ARESTAS</div><div class="metric-value">{len(edges)}</div><div class="metric-caption">conexões significativas</div></div>', unsafe_allow_html=True)
    with c3:
        strengths = [edge["score"] for edge in edges]
        avg = round(sum(strengths) / len(strengths), 1) if strengths else 0
        st.markdown(f'<div class="metric-card"><div class="metric-label">FORÇA MÉDIA</div><div class="metric-value">{avg}</div><div class="metric-caption">nível médio de semelhança</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="soft-title">Relações principais</div>', unsafe_allow_html=True)
    if not edges:
        st.info("Ainda não há conexões suficientes para exibir pares relacionados.")
    else:
        for edge in edges[:20]:
            s = nodes[edge["source"]]
            t = nodes[edge["target"]]
            shared_topics = ", ".join(edge.get("shared_topics") or []) or "sem tema compartilhado explícito"
            shared_keywords = ", ".join(edge.get("shared_keywords") or []) or "sem palavras-chave compartilhadas explícitas"
            st.markdown(
                f"""
                <div class="insight-row">
                    <div style="font-weight:700;color:#f5f9ff">{s['analysis'].get('title', s['filename'])}</div>
                    <div class="mini">conecta com</div>
                    <div style="font-weight:700;color:#f5f9ff">{t['analysis'].get('title', t['filename'])}</div>
                    <div class="mini">Similaridade: {edge['score']:.1f}</div>
                    <div class="mini">Temas em comum: {shared_topics}</div>
                    <div class="mini">Padrões em comum: {shared_keywords}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
    st.markdown('</div>', unsafe_allow_html=True)

def render_simple_bar(counter: Counter, title: str, max_items: int = 10):
    if go is None or not counter:
        return
    items = counter.most_common(max_items)
    fig = go.Figure(
        go.Bar(
            x=[v for _, v in items],
            y=[k for k, _ in items],
            orientation="h",
            text=[v for _, v in items],
            textposition="outside"
        )
    )
    fig.update_layout(
        height=320,
        title=title,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis=dict(showgrid=False, color="#dbe6ff"),
        yaxis=dict(showgrid=False, color="#dbe6ff")
    )
    st.plotly_chart(fig, use_container_width=True)

def render_globe(points):
    if go is None or not points:
        st.info("Ainda não há dados geográficos de afiliação para montar o globo.")
        return
    grouped = defaultdict(lambda: {"lat": [], "lon": [], "count": 0, "country": ""})
    for p in points:
        if p.get("lat") is None or p.get("lon") is None:
            continue
        key = f"{round(p['lat'], 2)}|{round(p['lon'], 2)}|{p.get('country','')}"
        grouped[key]["lat"].append(p["lat"])
        grouped[key]["lon"].append(p["lon"])
        grouped[key]["count"] += 1
        grouped[key]["country"] = p.get("country", "País não identificado")
    fig = go.Figure(
        go.Scattergeo(
            lon=[sum(v["lon"]) / len(v["lon"]) for v in grouped.values()],
            lat=[sum(v["lat"]) / len(v["lat"]) for v in grouped.values()],
            text=[f"{v['country']} | {v['count']} ocorrência(s)" for v in grouped.values()],
            mode="markers",
            marker=dict(size=[8 + v["count"] * 2 for v in grouped.values()], color="#92d4ff", line=dict(color="#ffffff", width=1), opacity=.9)
        )
    )
    fig.update_layout(
        title="Mapa global de países de afiliação identificados",
        height=500,
        geo=dict(
            projection_type="orthographic",
            showland=True,
            landcolor="rgb(33,47,75)",
            showcountries=True,
            countrycolor="rgba(255,255,255,.25)",
            showocean=True,
            oceancolor="rgb(6,13,24)",
            bgcolor="rgba(0,0,0,0)"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=50, b=0)
    )
    st.plotly_chart(fig, use_container_width=True)

def page_analytics():
    render_shell("Análises", "Leitura global de anos, temas, autores, metodologias, países e síntese das pesquisas")
    data = build_analysis_dataset()
    rows = data["rows"]
    if not rows:
        st.info("Analise documentos nos repositórios para ativar o painel analítico.")
        return

    c1, c2, c3, c4 = st.columns(4)
    stats = [
        ("DOCUMENTOS", len(rows), "analisados"),
        ("AUTORES", len(data["author_counter"]), "identificados"),
        ("PAÍSES", len(data["country_counter"]), "mapeados"),
        ("MÉTODOS", len(data["method_counter"]), "classificados"),
    ]
    for col, (label, value, caption) in zip([c1, c2, c3, c4], stats):
        with col:
            st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-caption">{caption}</div></div>', unsafe_allow_html=True)

    t1, t2, t3, t4, t5 = st.tabs(["Ano", "Tema", "Autores", "Nacionalidade", "Síntese"])
    with t1:
        render_simple_bar(data["year_counter"], "Distribuição por ano", max_items=15)
    with t2:
        render_simple_bar(data["theme_counter"], "Distribuição por tema", max_items=12)
        render_simple_bar(data["method_counter"], "Metodologias detectadas", max_items=10)
    with t3:
        render_simple_bar(data["author_counter"], "Autores mais recorrentes", max_items=15)
    with t4:
        render_simple_bar(data["country_counter"], "Países de afiliação", max_items=15)
        render_globe(data["globe_points"])
    with t5:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="soft-title">Síntese automática do corpus</div>', unsafe_allow_html=True)
        top_year = data["year_counter"].most_common(1)[0][0] if data["year_counter"] else "não identificado"
        top_theme = data["theme_counter"].most_common(1)[0][0] if data["theme_counter"] else "não identificado"
        top_method = data["method_counter"].most_common(1)[0][0] if data["method_counter"] else "não identificado"
        top_country = data["country_counter"].most_common(1)[0][0] if data["country_counter"] else "não identificado"
        synthesis = (
            f"O conjunto analisado reúne {len(rows)} documentos. "
            f"O ano mais recorrente é {top_year}. "
            f"O tema com maior presença é {top_theme}. "
            f"A metodologia dominante é {top_method}. "
            f"O país de afiliação que mais aparece é {top_country}. "
            f"As conexões entre documentos devem ser observadas principalmente a partir dos temas recorrentes e da sobreposição de palavras-chave."
        )
        st.write(synthesis)
        st.markdown('<div class="section-sep">Resumos dos documentos</div>', unsafe_allow_html=True)
        for row in rows[:20]:
            st.markdown(
                f"""
                <div class="insight-row">
                    <div style="font-weight:700;color:#f5f9ff">{row.get('title', row.get('filename','Documento'))}</div>
                    <div class="mini">{row.get('repository')} | {row.get('year') or 'Ano não identificado'} | {row.get('methodology')}</div>
                    <div style="margin-top:8px">{row.get('summary','')[:1100]}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

def page_account():
    render_shell("Conta", "Dados do usuário, preferências temáticas e histórico de uso")
    user = user_data()
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="soft-title">Perfil</div>', unsafe_allow_html=True)
    with st.form("account_form"):
        name = st.text_input("Nome", value=user.get("name", ""))
        area = st.text_input("Área de pesquisa", value=user.get("area", ""))
        bio = st.text_area("Biografia", value=user.get("bio", ""), height=120)
        submitted = st.form_submit_button("Salvar alterações", use_container_width=True)
        if submitted:
            email = st.session_state.current_user
            st.session_state.users[email]["name"] = name
            st.session_state.users[email]["area"] = area
            st.session_state.users[email]["bio"] = bio
            save_state()
            st.success("Perfil atualizado.")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    hist = user.get("history", [])
    profile = current_interest_profile()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="soft-title">Interesses inferidos</div>', unsafe_allow_html=True)
        if profile["topics"]:
            for topic, score in profile["topics"].items():
                st.markdown(f'<span class="table-chip">{topic} ({score})</span>', unsafe_allow_html=True)
        if profile["keywords"]:
            st.markdown('<div class="section-sep">Palavras recorrentes</div>', unsafe_allow_html=True)
            for kw in profile["keywords"]:
                st.markdown(f'<span class="table-chip">{kw}</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="soft-title">Histórico recente</div>', unsafe_allow_html=True)
        if not hist:
            st.info("Sem histórico de consultas até o momento.")
        else:
            for item in reversed(hist[-20:]):
                topics = ", ".join(item.get("topics", [])) or "sem tema identificado"
                st.markdown(
                    f"""
                    <div class="insight-row">
                        <div style="font-weight:700;color:#f5f9ff">{item.get('query')}</div>
                        <div class="mini">{item.get('time')}</div>
                        <div class="mini">Temas: {topics}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        st.markdown('</div>', unsafe_allow_html=True)

def main():
    st.set_page_config(page_title=APP_TITLE, layout="wide", initial_sidebar_state="expanded")
    init_state()
    liquid_css()
    if not st.session_state.logged_in:
        page_login()
        return
    render_nav()
    page = st.session_state.get("page", "dashboard")
    pages = {
        "dashboard": page_dashboard,
        "discovery": page_discovery,
        "repositories": page_repositories,
        "connections": page_connections,
        "analytics": page_analytics,
        "account": page_account,
    }
    pages.get(page, page_dashboard)()

if __name__ == "__main__":
    main()
