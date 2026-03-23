#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NEBULA - Sistema Integrado de Pesquisa Acadêmica
Análise de papers, reconhecimento de pesquisas, busca semantica avançada
Autor: Sistema Nebula v2.0
"""

import streamlit as st
import json
import os
import io
import re
import base64
import hashlib
import subprocess
import sys
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import numpy as np
from PIL import Image as PILImage
import requests

# ===============================================
#  INSTALAÇÃO DE DEPENDÊNCIAS
# ===============================================
def _pip(*pkgs):
    for p in pkgs:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", p, "-q"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass

try:
    import plotly.graph_objects as go
    import plotly.express as px
except:
    _pip("plotly")
    import plotly.graph_objects as go
    import plotly.express as px

try:
    from PIL import Image as PILImage
except:
    _pip("pillow")
    from PIL import Image as PILImage

try:
    import pandas as pd
except:
    _pip("pandas")
    import pandas as pd

SKIMAGE_OK = False
try:
    from skimage import filters as sk_filters, feature as sk_feature
    from skimage.feature import graycomatrix, graycoprops
    SKIMAGE_OK = True
except:
    try:
        _pip("scikit-image")
        from skimage import filters as sk_filters, feature as sk_feature
        from skimage.feature import graycomatrix, graycoprops
        SKIMAGE_OK = True
    except:
        SKIMAGE_OK = False

try:
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_OK = True
except:
    try:
        _pip("scikit-learn")
        from sklearn.cluster import KMeans
        from sklearn.metrics.pairwise import cosine_similarity
        SKLEARN_OK = True
    except:
        SKLEARN_OK = False

# ===============================================
#  CONFIGURAÇÃO STREAMLIT
# ===============================================
st.set_page_config(
    page_title="Nebula - Pesquisa Acadêmica",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_FILE = "nebula_research.json"

# ===============================================
#  BANCO DE DADOS
# ===============================================
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_db():
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "users": st.session_state.users,
                "repositories": st.session_state.repositories,
                "analyses": st.session_state.analyses,
                "connections": st.session_state.connections,
                "saved_papers": st.session_state.saved_papers,
            }, f, ensure_ascii=False, indent=2)
    except:
        pass

def hp(pw):
    """Hash de senha"""
    return hashlib.sha256(pw.encode()).hexdigest()

def ini(n):
    """Gera iniciais do nome"""
    if not isinstance(n, str):
        n = str(n)
    p = n.strip().split()
    return ''.join(w[0].upper() for w in p[:2]) if p else "?"

# ===============================================
#  FUNÇÕES DE ANÁLISE TEXTUAL
# ===============================================
STOPWORDS = {
    "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "é", "com", "uma",
    "os", "no", "se", "na", "por", "mais", "as", "dos", "como", "mas", "foi", "ao",
    "ele", "das", "tem", "à", "seu", "sua", "ou", "ser", "the", "of", "and", "to",
    "in", "is", "it", "that", "was", "he", "for", "on", "are", "as", "with", "they",
    "at", "be", "this", "from", "or", "one", "had", "by", "but", "not", "what", "all"
}

def extract_keywords(text, n=20):
    """Extrai palavras-chave de um texto"""
    if not text:
        return []
    words = re.findall(r'\b[a-záàâãéêíóôõúüçA-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]{4,}\b', text.lower())
    words = [w for w in words if w not in STOPWORDS]
    if not words:
        return []
    tf = Counter(words)
    total = sum(tf.values())
    return [w for w, _ in sorted({w: c/total for w, c in tf.items()}.items(), key=lambda x: -x[1])[:n]]

def classify_research_area(text):
    """Classifica a área de pesquisa baseado no conteúdo"""
    area_keywords = {
        "Biologia Molecular": ["gene", "dna", "rna", "proteína", "célula", "genômica", "crispr", "molecular"],
        "Neurociência": ["neurociência", "neural", "cérebro", "cognição", "memória", "sináptico", "neuroplasticidade"],
        "Inteligência Artificial": ["inteligência", "machine learning", "neural", "algoritmo", "deep learning", "llm", "ia"],
        "Física Quântica": ["quântica", "quantum", "partícula", "energia", "mecânica quântica", "superposição"],
        "Astrofísica": ["astrofísica", "galáxia", "cosmologia", "universo", "estrela", "telescópio", "espaço"],
        "Química": ["química", "molécula", "síntese", "reação", "ligação", "composto", "reativo"],
        "Medicina Clínica": ["clínico", "paciente", "diagnóstico", "tratamento", "terapia", "saúde", "doença"],
        "Ecologia": ["ecologia", "biodiversidade", "ambiente", "sustentável", "clima", "carbono", "espécie"],
        "Engenharia": ["engenharia", "sistema", "automação", "robótica", "sensor", "protocolo", "eficiência"],
        "Matemática": ["matemática", "equação", "teorema", "algoritmo", "probabilidade", "estatística"]
    }
    
    text_lower = text.lower()
    scores = {}
    for area, keywords in area_keywords.items():
        scores[area] = sum(1 for kw in keywords if kw in text_lower)
    
    return max(scores, key=scores.get) if max(scores.values()) > 0 else "Pesquisa Geral"

def extract_metadata(text, filename=""):
    """Extrai metadados de um texto de pesquisa"""
    metadata = {
        "title": "",
        "authors": [],
        "year": None,
        "keywords": extract_keywords(text, 15),
        "area": classify_research_area(text),
        "word_count": len(text.split()),
        "abstract": text[:500] if len(text) > 500 else text,
    }
    
    # Tenta extrair ano
    years = re.findall(r'\b(19|20)\d{2}\b', text)
    if years:
        metadata["year"] = int(years[-1])
    
    # Tenta extrair titulo (primeira linha não vazia com mais de 5 palavras)
    lines = text.split('\n')
    for line in lines[:20]:
        if len(line.split()) > 5:
            metadata["title"] = line.strip()[:100]
            break
    
    return metadata

# ===============================================
#  API CLAUDE
# ===============================================
def call_claude_vision(img_bytes, prompt, api_key):
    """Chama Claude Vision API"""
    if not api_key or not api_key.startswith("sk-"):
        return None, "API key inválida"
    try:
        img = PILImage.open(io.BytesIO(img_bytes))
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()
        
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-opus-4-20250514",
                "max_tokens": 2000,
                "messages": [{
                    "role": "user",
                    "content": [{
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": b64
                        }
                    }, {
                        "type": "text",
                        "text": prompt
                    }]
                }]
            },
            timeout=30
        )
        
        if resp.status_code == 200:
            return resp.json()["content"][0]["text"], None
        return None, f"Erro HTTP {resp.status_code}"
    except Exception as e:
        return None, str(e)

def call_claude_analysis(content, api_key):
    """Chama Claude para análise de pesquisa"""
    if not api_key or not api_key.startswith("sk-"):
        return None, "API key ausente"
    
    prompt = f"""Analise esta pesquisa acadêmica e responda APENAS em JSON válido (sem markdown):
{{
  "resumo_executivo": "<resumo em 2-3 frases>",
  "contribuicoes_principais": ["<contribuição 1>", "<contribuição 2>", "<contribuição 3>"],
  "pontos_fortes": ["<força 1>", "<força 2>", "<força 3>"],
  "areas_melhoria": ["<melhoria 1>", "<melhoria 2>"],
  "relevancia_scientifica": <0-100>,
  "inovacao_score": <0-100>,
  "impacto_potencial": "<Alto/Médio/Baixo>",
  "lacunas_identificadas": ["<lacuna 1>", "<lacuna 2>"],
  "pesquisas_futuras": ["<direção 1>", "<direção 2>"],
  "metodologia_avaliacao": "<descrição>",
  "qualidade_geral": <0-100>
}}

Pesquisa:
{content[:3000]}"""
    
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-opus-4-20250514",
                "max_tokens": 1500,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        
        if resp.status_code == 200:
            text = resp.json()["content"][0]["text"].strip()
            # Limpa markdown se houver
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            return json.loads(text), None
        return None, f"HTTP {resp.status_code}"
    except Exception as e:
        return None, str(e)

# ===============================================
#  ANÁLISE DE IMAGENS CIENTÍFICAS
# ===============================================
def analyze_scientific_image(img_bytes):
    """Análise completa de imagem científica com pipeline ML"""
    try:
        img = PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
        w, h = img.size
        scale = min(512/w, 512/h)
        new_w, new_h = int(w*scale), int(h*scale)
        img_r = img.resize((new_w, new_h), PILImage.LANCZOS)
        arr = np.array(img_r, dtype=np.float32)
        
        r_ch, g_ch, b_ch = arr[:,:,0], arr[:,:,1], arr[:,:,2]
        gray = 0.2989*r_ch + 0.5870*g_ch + 0.1140*b_ch
        gray_u8 = gray.astype(np.uint8)
        
        result = {
            "size": (w, h),
            "color_analysis": {
                "r": float(r_ch.mean()),
                "g": float(g_ch.mean()),
                "b": float(b_ch.mean()),
                "brightness": float(gray.mean()),
                "std": float(gray.std())
            },
            "edge_analysis": {},
            "keypoints": 0,
            "texture_complexity": float(gray.std()) / 255.0,
            "image_type": classify_image_type(arr, gray),
            "quality_score": 0
        }
        
        # Análise de bordas (Sobel)
        if SKIMAGE_OK:
            try:
                sx = sk_filters.sobel_h(gray/255.0)
                sy = sk_filters.sobel_v(gray/255.0)
                magnitude = np.sqrt(sx**2 + sy**2)
                result["edge_analysis"]["magnitude"] = float(magnitude.mean())
                result["edge_analysis"]["max_edge"] = float(magnitude.max())
                result["edge_analysis"]["density"] = float((magnitude > magnitude.mean()*1.5).mean())
            except:
                pass
        
        # Detecção de keypoints
        if SKIMAGE_OK:
            try:
                corners = sk_feature.corner_harris(gray/255.0)
                from skimage.feature import corner_peaks
                keypoints = corner_peaks(corners, min_distance=5, threshold_rel=0.05)
                result["keypoints"] = len(keypoints)
            except:
                pass
        
        # Score de qualidade
        result["quality_score"] = min(95, 30 + 
                                     (result["edge_analysis"].get("density", 0)*30) + 
                                     (min(50, result["keypoints"]/2)) +
                                     (result["texture_complexity"]*20))
        
        return result
    except Exception as e:
        return {"error": str(e), "quality_score": 0}

def classify_image_type(arr, gray):
    """Classifica o tipo de imagem científica"""
    r_mean = arr[:,:,0].mean()
    g_mean = arr[:,:,1].mean()
    b_mean = arr[:,:,2].mean()
    
    # Padrões de cor para identificar tipos
    if b_mean > r_mean + 50:
        return "Fluorescência/DAPI"
    elif g_mean > r_mean + 50:
        return "Fluorescência/GFP"
    elif abs(r_mean - g_mean) < 15 and abs(g_mean - b_mean) < 15:
        return "Histopatologia/Grayscale"
    elif gray.std() > 40:
        return "Microscopia/Alta Contrast"
    else:
        return "Microscopia/Padrão"

# ===============================================
#  BUSCA SEMÂNTICA
# ===============================================
def search_semantic_scholar(query, limit=8):
    """Busca em Semantic Scholar"""
    try:
        r = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={
                "query": query,
                "limit": limit,
                "fields": "title,authors,year,abstract,venue,citationCount,openAccessPdf,externalIds"
            },
            timeout=8
        )
        
        if r.status_code == 200:
            results = []
            for p in r.json().get("data", []):
                authors = p.get("authors", [])
                author_str = ", ".join([a.get("name", "") for a in authors[:3]])
                if len(authors) > 3:
                    author_str += " et al."
                
                ext = p.get("externalIds", {}) or {}
                doi = ext.get("DOI", "")
                arxiv = ext.get("ArXiv", "")
                
                pdf = p.get("openAccessPdf") or {}
                url = pdf.get("url", "") or (f"https://arxiv.org/abs/{arxiv}" if arxiv else 
                      (f"https://doi.org/{doi}" if doi else ""))
                
                results.append({
                    "title": p.get("title", "Sem título"),
                    "authors": author_str or "—",
                    "year": p.get("year", "?"),
                    "abstract": (p.get("abstract", "") or "")[:400],
                    "venue": p.get("venue", "Semantic Scholar"),
                    "citations": p.get("citationCount", 0),
                    "url": url,
                    "doi": doi or arxiv or "—",
                    "source": "semantic"
                })
            return results
    except:
        pass
    return []

def search_crossref(query, limit=5):
    """Busca em CrossRef"""
    try:
        r = requests.get(
            "https://api.crossref.org/works",
            params={
                "query": query,
                "rows": limit,
                "select": "title,author,issued,abstract,DOI,container-title,is-referenced-by-count",
                "mailto": "nebula@research.org"
            },
            timeout=8
        )
        
        if r.status_code == 200:
            results = []
            for p in r.json().get("message", {}).get("items", []):
                title = (p.get("title") or ["?"])[0]
                authors = p.get("author", []) or []
                author_str = ", ".join([f"{a.get('given', '').split()[0]} {a.get('family', '')}".strip() 
                                       for a in authors[:3]])
                if len(authors) > 3:
                    author_str += " et al."
                
                year = (p.get("issued", {}).get("date-parts") or [[None]])[0][0]
                doi = p.get("DOI", "")
                abstract = re.sub(r'<[^>]+>', '', p.get("abstract", "") or "")[:400]
                
                results.append({
                    "title": title,
                    "authors": author_str or "—",
                    "year": year or "?",
                    "abstract": abstract,
                    "venue": (p.get("container-title") or ["CrossRef"])[0],
                    "citations": p.get("is-referenced-by-count", 0),
                    "url": f"https://doi.org/{doi}" if doi else "",
                    "doi": doi,
                    "source": "crossref"
                })
            return results
    except:
        pass
    return []

# ===============================================
#  INICIALIZAÇÃO
# ===============================================
def init():
    if "initialized" in st.session_state:
        return
    
    st.session_state.initialized = True
    disk = load_db()
    
    # Usuários
    st.session_state.users = disk.get("users", {
        "usuario@nebula.com": {
            "name": "Pesquisador Principal",
            "password": hp("nebula123"),
            "area": "Biologia Molecular",
            "verified": True
        }
    })
    
    st.session_state.logged_in = False
    st.session_state.current_user = None
    st.session_state.page = "login"
    
    # Repositórios
    st.session_state.repositories = disk.get("repositories", {})
    st.session_state.analyses = disk.get("analyses", {})
    st.session_state.connections = disk.get("connections", {})
    st.session_state.saved_papers = disk.get("saved_papers", [])
    
    # Cache
    st.session_state.search_cache = {}
    st.session_state.analysis_cache = {}

init()

# ===============================================
#  CSS - INTERFACE MODERNA LIQUID GLASS
# ===============================================
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800;900&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');

:root {
  --bg: #060B14;
  --bg2: #0B1220;
  --bg3: #101828;
  --acc: #0D7FE8;
  --acc2: #1A6EC9;
  --teal: #36B8A0;
  --teal2: #2E9D8A;
  --red: #F03E5A;
  --orn: #FF8C42;
  --pur: #9B6FD4;
  --cya: #38C8F0;
  --t0: #FFFFFF;
  --t1: #E2E6F0;
  --t2: #9AA3BC;
  --t3: #5A6180;
  --t4: #2E3450;
  --g1: rgba(255,255,255,.042);
  --g2: rgba(255,255,255,.07);
  --g3: rgba(255,255,255,.11);
  --gb1: rgba(255,255,255,.07);
  --gb2: rgba(255,255,255,.11);
  --gb3: rgba(255,255,255,.18);
}

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body, .stApp {
  background: var(--bg) !important;
  color: var(--t1) !important;
  font-family: 'DM Sans', -apple-system, sans-serif !important;
}

.stApp::before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background:
    radial-gradient(ellipse 55% 45% at -5% 0%, rgba(13,127,232,.08) 0%, transparent 60%),
    radial-gradient(ellipse 45% 35% at 105% 0%, rgba(54,184,160,.07) 0%, transparent 55%),
    radial-gradient(ellipse 35% 45% at 50% 110%, rgba(155,111,212,.05) 0%, transparent 60%);
}

header[data-testid="stHeader"], #MainMenu, footer, .stDeployButton, [data-testid="stToolbar"], [data-testid="stDecoration"] {
  display: none !important;
}

section[data-testid="stSidebar"] {
  display: block !important;
  transform: translateX(0) !important;
  visibility: visible !important;
  background: rgba(4,7,16,.97) !important;
  backdrop-filter: blur(40px) saturate(200%) !important;
  border-right: 1px solid rgba(255,255,255,.07) !important;
  width: 240px !important;
  min-width: 240px !important;
  max-width: 240px !important;
  padding: 1.3rem .9rem 1rem !important;
}

section[data-testid="stSidebar"]>div {
  width: 240px !important;
  padding: 0 !important;
}

section[data-testid="stSidebar"] .stButton>button {
  position: relative;
  overflow: hidden;
  background: rgba(255,255,255,.04) !important;
  backdrop-filter: blur(20px) saturate(180%) !important;
  border: 1px solid rgba(255,255,255,.09) !important;
  border-top-color: rgba(255,255,255,.15) !important;
  border-radius: 12px !important;
  box-shadow: 0 2px 12px rgba(0,0,0,.3), inset 0 1px 0 rgba(255,255,255,.08) !important;
  color: #9AA3BC !important;
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 500 !important;
  font-size: .83rem !important;
  padding: .52rem .9rem !important;
  text-align: left !important;
  width: 100% !important;
  margin-bottom: .18rem !important;
  transition: all .15s cubic-bezier(.4,0,.2,1) !important;
}

section[data-testid="stSidebar"] .stButton>button:hover {
  background: rgba(13,127,232,.12) !important;
  border-color: rgba(13,127,232,.3) !important;
  box-shadow: 0 4px 20px rgba(13,127,232,.15) !important;
  color: #FFFFFF !important;
  transform: translateY(-1px) !important;
}

.stButton>button {
  background: rgba(255,255,255,.07) !important;
  backdrop-filter: blur(12px) !important;
  border: 1px solid rgba(255,255,255,.1) !important;
  border-top-color: rgba(255,255,255,.16) !important;
  border-radius: 10px !important;
  color: #C8CEDE !important;
  font-weight: 500 !important;
  font-size: .82rem !important;
  padding: .45rem .8rem !important;
  box-shadow: 0 2px 8px rgba(0,0,0,.25), inset 0 1px 0 rgba(255,255,255,.07) !important;
  transition: all .12s ease !important;
}

.stButton>button:hover {
  background: rgba(13,127,232,.14) !important;
  border-color: rgba(13,127,232,.28) !important;
  color: #fff !important;
  box-shadow: 0 4px 16px rgba(13,127,232,.2) !important;
  transform: translateY(-1px) !important;
}

.block-container {
  padding-top: .3rem !important;
  padding-bottom: 4rem !important;
  max-width: 1400px !important;
  position: relative;
  z-index: 1;
  padding-left: .9rem !important;
  padding-right: .9rem !important;
}

.stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] {
  background: rgba(255,255,255,.04) !important;
  border: 1px solid var(--gb1) !important;
  border-radius: 12px !important;
  color: var(--t1) !important;
  font-family: 'DM Sans', sans-serif !important;
}

.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: rgba(13,127,232,.5) !important;
  box-shadow: 0 0 0 3px rgba(13,127,232,.1) !important;
}

/* Cards */
.glass {
  background: rgba(255,255,255,.04);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 20px;
  box-shadow: 0 0 0 1px rgba(255,255,255,.03) inset, 0 6px 36px rgba(0,0,0,.35);
  position: relative;
  overflow: hidden;
  padding: 1.2rem;
  margin-bottom: 0.8rem;
}

.glass::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.1), transparent);
  pointer-events: none;
}

.card-research {
  background: rgba(255,255,255,.04);
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 16px;
  padding: 1rem;
  margin-bottom: 0.6rem;
  overflow: hidden;
  box-shadow: 0 2px 24px rgba(0,0,0,.28);
  transition: border-color .15s, transform .15s, box-shadow .15s;
}

.card-research:hover {
  border-color: rgba(13,127,232,.25);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(13,127,232,.1);
}

.stat-box {
  background: rgba(255,255,255,.04);
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 16px;
  padding: 1.2rem;
  text-align: center;
}

.badge {
  display: inline-block;
  background: rgba(13,127,232,.12);
  border: 1px solid rgba(13,127,232,.25);
  border-radius: 50px;
  padding: 4px 12px;
  font-size: 0.65rem;
  font-weight: 700;
  color: #5BAAFF;
  margin-right: 6px;
  margin-bottom: 6px;
}

.tag {
  display: inline-block;
  background: rgba(255,255,255,.05);
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 50px;
  padding: 3px 10px;
  font-size: .62rem;
  color: var(--t2);
  margin: 3px;
  font-weight: 500;
}

h1 {
  font-family: 'Syne', sans-serif !important;
  font-size: 2rem !important;
  font-weight: 800 !important;
  letter-spacing: -.03em;
  color: var(--t0) !important;
}

h2 {
  font-family: 'Syne', sans-serif !important;
  font-size: 1.2rem !important;
  font-weight: 700 !important;
  color: var(--t0) !important;
}

hr {
  border: none;
  border-top: 1px solid rgba(255,255,255,.07) !important;
  margin: .8rem 0 !important;
}

.stTabs [data-baseweb="tab-list"] {
  background: rgba(255,255,255,.03) !important;
  border: 1px solid rgba(255,255,255,.08) !important;
  border-radius: 12px !important;
  padding: 3px !important;
  gap: 2px !important;
}

.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  color: var(--t3) !important;
  border-radius: 9px !important;
  font-size: .74rem !important;
  font-weight: 500 !important;
}

.stTabs [aria-selected="true"] {
  background: rgba(13,127,232,.14) !important;
  color: var(--cya) !important;
  border: 1px solid rgba(13,127,232,.25) !important;
  font-weight: 700 !important;
}

::-webkit-scrollbar {
  width: 4px;
  height: 4px;
}

::-webkit-scrollbar-thumb {
  background: var(--t4);
  border-radius: 4px;
}

.metric-value {
  font-family: 'Syne', sans-serif;
  font-size: 2rem;
  font-weight: 900;
  background: linear-gradient(135deg, var(--acc), var(--cya));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.metric-label {
  font-size: .57rem;
  color: var(--t3);
  margin-top: 4px;
  letter-spacing: .1em;
  text-transform: uppercase;
  font-weight: 700;
}

</style>
""", unsafe_allow_html=True)

# ===============================================
#  PÁGINA: LOGIN
# ===============================================
def page_login():
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-bottom:2.5rem">
            <div style="display:flex;align-items:center;justify-content:center;gap:12px;margin-bottom:.8rem">
                <div style="width:52px;height:52px;border-radius:16px;background:linear-gradient(135deg,#0D7FE8,#36B8A0);display:flex;align-items:center;justify-content:center;font-size:1.8rem;box-shadow:0 0 32px rgba(13,127,232,.35)">🔬</div>
                <div style="font-family:Syne,sans-serif;font-size:2.5rem;font-weight:900;letter-spacing:-.06em;background:linear-gradient(135deg,#0D7FE8,#36B8A0);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">Nebula</div>
            </div>
            <div style="color:var(--t3);font-size:.65rem;letter-spacing:.25em;text-transform:uppercase;font-weight:700">Sistema Avançado de Pesquisa Acadêmica</div>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Entrar", "Criar Conta"])
        
        with tab1:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="seu@email.com")
                password = st.text_input("Senha", type="password", placeholder="••••••••")
                submit = st.form_submit_button("Acessar", use_container_width=True)
                
                if submit:
                    user = st.session_state.users.get(email)
                    if not user:
                        st.error("Email não encontrado")
                    elif user["password"] != hp(password):
                        st.error("Senha incorreta")
                    else:
                        st.session_state.logged_in = True
                        st.session_state.current_user = email
                        st.session_state.page = "repositories"
                        save_db()
                        st.rerun()
            
            st.markdown('<div style="text-align:center;color:var(--t3);font-size:.67rem;margin-top:.7rem">Demo: usuario@nebula.com / nebula123</div>', unsafe_allow_html=True)
        
        with tab2:
            with st.form("signup_form"):
                name = st.text_input("Nome completo")
                email = st.text_input("Email")
                area = st.selectbox("Área de Pesquisa", 
                    ["Biologia Molecular", "Neurociência", "Inteligência Artificial", 
                     "Física Quântica", "Astrofísica", "Química", "Medicina Clínica",
                     "Ecologia", "Engenharia", "Matemática"])
                password = st.text_input("Senha", type="password")
                password_confirm = st.text_input("Confirmar senha", type="password")
                
                submit = st.form_submit_button("Criar Conta", use_container_width=True)
                
                if submit:
                    if not all([name, email, password]):
                        st.error("Preencha todos os campos")
                    elif password != password_confirm:
                        st.error("Senhas não coincidem")
                    elif email in st.session_state.users:
                        st.error("Email já cadastrado")
                    elif len(password) < 6:
                        st.error("Mínimo 6 caracteres")
                    else:
                        st.session_state.users[email] = {
                            "name": name,
                            "password": hp(password),
                            "area": area,
                            "verified": False
                        }
                        save_db()
                        st.session_state.logged_in = True
                        st.session_state.current_user = email
                        st.session_state.page = "repositories"
                        st.rerun()

# ===============================================
#  PÁGINA: REPOSITÓRIOS
# ===============================================
def page_repositories():
    st.markdown('<div style="padding-top:1rem">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1.5])
    
    with col1:
        st.markdown('<h1>Meus Repositórios de Pesquisa</h1>', unsafe_allow_html=True)
    
    with col2:
        if st.button("Novo Repositório", use_container_width=True):
            st.session_state.show_new_repo = True
    
    if st.session_state.get("show_new_repo"):
        with st.expander("Criar Novo Repositório", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                repo_name = st.text_input("Nome do Repositório")
            with col2:
                repo_type = st.selectbox("Tipo", ["Projeto", "Dataset", "Review", "Outro"])
            
            description = st.text_area("Descrição", height=80)
            
            if st.button("Criar"):
                if repo_name:
                    if repo_name not in st.session_state.repositories:
                        st.session_state.repositories[repo_name] = {
                            "type": repo_type,
                            "description": description,
                            "papers": [],
                            "created": datetime.now().isoformat(),
                            "updated": datetime.now().isoformat()
                        }
                        save_db()
                        st.session_state.show_new_repo = False
                        st.success(f"Repositório '{repo_name}' criado!")
                        st.rerun()
                    else:
                        st.warning("Já existe repositório com este nome")
                else:
                    st.warning("Digite um nome para o repositório")
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    if not st.session_state.repositories:
        st.markdown("""
        <div class="glass" style="text-align:center;padding:3rem">
            <div style="font-size:2.5rem;opacity:.15;margin-bottom:1rem">📁</div>
            <div style="font-family:Syne,sans-serif;font-size:1.1rem;color:var(--t1)">Nenhum repositório criado</div>
            <div style="font-size:.75rem;color:var(--t3);margin-top:.5rem">Crie seu primeiro repositório para começar a adicionar pesquisas</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for repo_name, repo_data in st.session_state.repositories.items():
            with st.expander(f"📁 {repo_name} - {len(repo_data.get('papers', []))} papers"):
                st.markdown(f"**Tipo:** {repo_data['type']} | **Descrição:** {repo_data['description']}")
                
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown("**Adicionar Paper**")
                    with st.form(f"upload_{repo_name}"):
                        paper_title = st.text_input("Título do Paper")
                        paper_authors = st.text_input("Autores")
                        paper_year = st.number_input("Ano", 1900, 2100, 2024)
                        paper_file = st.file_uploader("Arquivo (PDF/TXT)", 
                                                      type=["pdf", "txt"],
                                                      key=f"file_{repo_name}")
                        
                        if st.form_submit_button("Adicionar"):
                            if paper_title and paper_file:
                                content = paper_file.read().decode("utf-8", errors="ignore")
                                
                                paper = {
                                    "title": paper_title,
                                    "authors": paper_authors,
                                    "year": paper_year,
                                    "content": content,
                                    "metadata": extract_metadata(content, paper_title),
                                    "analysis": None,
                                    "added": datetime.now().isoformat()
                                }
                                
                                repo_data["papers"].append(paper)
                                st.session_state.repositories[repo_name] = repo_data
                                save_db()
                                st.success("Paper adicionado!")
                                st.rerun()
                
                with col2:
                    if st.button("Analisar Tudo", key=f"analyze_{repo_name}"):
                        st.session_state.analyzing_repo = repo_name
                
                with col3:
                    if st.button("Deletar", key=f"delete_{repo_name}"):
                        del st.session_state.repositories[repo_name]
                        save_db()
                        st.rerun()
                
                # Lista de papers
                st.markdown("**Papers no Repositório:**")
                for idx, paper in enumerate(repo_data.get("papers", [])):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"""
                        **{paper['title']}**
                        
                        Autores: {paper['authors']} | Ano: {paper['year']}
                        
                        Área: {paper['metadata'].get('area', 'Geral')} | Palavras-chave: {', '.join(paper['metadata'].get('keywords', [])[:5])}
                        """)
                    with col2:
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("Analisar", key=f"analyze_paper_{repo_name}_{idx}"):
                                st.session_state.analyzing_paper = (repo_name, idx)
                        with col_b:
                            if st.button("Remover", key=f"remove_paper_{repo_name}_{idx}"):
                                repo_data["papers"].pop(idx)
                                save_db()
                                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# ===============================================
#  PÁGINA: ANÁLISE
# ===============================================
def page_analysis():
    st.markdown('<div style="padding-top:1rem">', unsafe_allow_html=True)
    st.markdown('<h1>Análise Avançada de Pesquisas</h1>', unsafe_allow_html=True)
    
    if not st.session_state.repositories:
        st.warning("Adicione papers aos repositórios primeiro")
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    # Coletar todos os papers
    all_papers = []
    for repo_name, repo_data in st.session_state.repositories.items():
        for paper in repo_data.get("papers", []):
            paper["repo"] = repo_name
            all_papers.append(paper)
    
    if not all_papers:
        st.warning("Nenhum paper adicionado")
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    # Estatísticas gerais
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="stat-box"><div class="metric-value">{len(all_papers)}</div><div class="metric-label">Papers Analisados</div></div>', unsafe_allow_html=True)
    with col2:
        avg_year = sum(p.get("year", 2024) for p in all_papers) / len(all_papers)
        st.markdown(f'<div class="stat-box"><div class="metric-value">{int(avg_year)}</div><div class="metric-label">Ano Médio</div></div>', unsafe_allow_html=True)
    with col3:
        areas = Counter(p['metadata'].get('area', 'Geral') for p in all_papers)
        st.markdown(f'<div class="stat-box"><div class="metric-value">{len(areas)}</div><div class="metric-label">Áreas Diferentes</div></div>', unsafe_allow_html=True)
    with col4:
        all_kw = set()
        for p in all_papers:
            all_kw.update(p['metadata'].get('keywords', []))
        st.markdown(f'<div class="stat-box"><div class="metric-value">{len(all_kw)}</div><div class="metric-label">Palavras-Chave Únicas</div></div>', unsafe_allow_html=True)
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # Gráficos de análise
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Distribuição Temporal",
        "Áreas de Pesquisa",
        "Palavras-Chave",
        "Mapa 3D de Nacionalidades",
        "Conexões"
    ])
    
    with tab1:
        st.markdown("**Distribuição de Papers por Ano**")
        years = Counter(p.get("year", 2024) for p in all_papers)
        
        if years:
            fig = go.Figure(data=[
                go.Bar(
                    x=sorted(years.keys()),
                    y=[years[y] for y in sorted(years.keys())],
                    marker=dict(
                        color=list(range(len(years))),
                        colorscale=[[0,"#0A1929"],[1,"#0D7FE8"]]
                    )
                )
            ])
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#5A6180", family="DM Sans"),
                height=400,
                margin=dict(l=40, r=40, t=40, b=40)
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.markdown("**Papers por Área de Pesquisa**")
        areas = Counter(p['metadata'].get('area', 'Geral') for p in all_papers)
        
        fig = go.Figure(data=[
            go.Pie(
                labels=list(areas.keys()),
                values=list(areas.values()),
                marker=dict(colors=["#0D7FE8", "#36B8A0", "#38C8F0", "#FF8C42", "#9B6FD4"])
            )
        ])
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#5A6180"),
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.markdown("**Palavras-Chave Mais Frequentes**")
        all_kw_list = []
        for p in all_papers:
            all_kw_list.extend(p['metadata'].get('keywords', [])[:10])
        
        kw_freq = Counter(all_kw_list)
        top_kw = dict(kw_freq.most_common(15))
        
        if top_kw:
            fig = go.Figure(data=[
                go.Bar(
                    y=list(top_kw.keys()),
                    x=list(top_kw.values()),
                    orientation='h',
                    marker=dict(color=list(range(len(top_kw))),
                               colorscale=[[0,"#0D7FE8"],[1,"#36B8A0"]])
                )
            ])
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#5A6180"),
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.markdown("**Mapa 3D de Autores por Localização**")
        st.info("Análise de nacionalidade dos autores (requer dados de localização dos papers)")
        
        # Simulação de mapa 3D com países aleatórios
        countries_sample = {
            "Brasil": 8,
            "Estados Unidos": 12,
            "China": 10,
            "Alemanha": 6,
            "Reino Unido": 7,
            "Canadá": 5,
            "França": 4,
            "Japão": 6,
            "Austrália": 3,
            "Índia": 4
        }
        
        if countries_sample:
            fig = go.Figure(data=[
                go.Scattergeo(
                    locations=list(countries_sample.keys()),
                    text=list(countries_sample.keys()),
                    mode='markers+text',
                    marker=dict(
                        size=[v*2 for v in countries_sample.values()],
                        color=list(countries_sample.values()),
                        colorscale='Viridis',
                        showscale=True
                    )
                )
            ])
            fig.update_layout(
                geo=dict(projection_type="natural earth"),
                height=500,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#5A6180")
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab5:
        st.markdown("**Análise de Conexões entre Pesquisas**")
        
        # Criar matriz de similaridade entre papers baseada em palavras-chave
        similarity_data = []
        
        for i, paper1 in enumerate(all_papers):
            for j, paper2 in enumerate(all_papers[i+1:], start=i+1):
                kw1 = set(paper1['metadata'].get('keywords', []))
                kw2 = set(paper2['metadata'].get('keywords', []))
                
                if kw1 and kw2:
                    similarity = len(kw1 & kw2) / len(kw1 | kw2)
                    if similarity > 0.2:
                        similarity_data.append({
                            "paper1": paper1["title"][:30],
                            "paper2": paper2["title"][:30],
                            "similarity": similarity,
                            "common_kw": list(kw1 & kw2)[:5]
                        })
        
        similarity_data.sort(key=lambda x: x["similarity"], reverse=True)
        
        st.markdown("**Conexões Encontradas:**")
        for conn in similarity_data[:10]:
            st.markdown(f"""
            **{conn['paper1']}** ↔ **{conn['paper2']}**
            
            Similaridade: {conn['similarity']:.0%} | Palavras-chave comuns: {', '.join(conn['common_kw'])}
            """)
            st.markdown("<hr>", unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ===============================================
#  PÁGINA: BUSCA E VISÃO IA
# ===============================================
def page_search_vision():
    st.markdown('<div style="padding-top:1rem">', unsafe_allow_html=True)
    st.markdown('<h1>Busca Inteligente e Visão IA</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.76rem;margin-bottom:1rem">Integração de busca semântica, reconhecimento de imagens científicas e busca na literatura</p>', unsafe_allow_html=True)
    
    api_key = st.session_state.get("anthropic_key", "")
    has_api = api_key.startswith("sk-") if api_key else False
    
    if has_api:
        st.markdown('<div class="glass"><strong>Claude Vision Ativo</strong> - Análise real de imagens com IA habilitada</div>', unsafe_allow_html=True)
    else:
        st.info("Insira sua API key do Claude nas configurações para ativar Vision")
    
    tab1, tab2, tab3 = st.tabs(["Busca por Texto", "Análise de Imagem", "Busca Avançada"])
    
    with tab1:
        st.markdown("**Buscar na Literatura Acadêmica**")
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            query = st.text_input("Digite sua busca", placeholder="Ex: aprendizado de máquina em biologia")
        
        with col2:
            source = st.selectbox("Fonte", ["Semantic Scholar", "CrossRef", "Ambos"])
        
        with col3:
            search_btn = st.button("Buscar", use_container_width=True)
        
        if search_btn and query:
            st.markdown("**Resultados:**")
            
            results = []
            if source in ["Semantic Scholar", "Ambos"]:
                with st.spinner("Buscando em Semantic Scholar..."):
                    results.extend(search_semantic_scholar(query, 8))
            
            if source in ["CrossRef", "Ambos"]:
                with st.spinner("Buscando em CrossRef..."):
                    results.extend(search_crossref(query, 5))
            
            if results:
                for idx, paper in enumerate(results):
                    with st.container():
                        st.markdown(f"""
                        **{paper['title']}**
                        
                        Autores: {paper['authors']} | Ano: {paper['year']}
                        
                        Fonte: {paper['venue']} | Citações: {paper['citations']}
                        
                        {paper['abstract']}
                        """)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("Salvar", key=f"save_{idx}"):
                                st.session_state.saved_papers.append(paper)
                                save_db()
                                st.success("Salvo!")
                        with col2:
                            if paper.get("url"):
                                st.markdown(f'<a href="{paper["url"]}" target="_blank">Abrir PDF</a>', unsafe_allow_html=True)
                        with col3:
                            st.write(f"DOI: {paper.get('doi', 'N/A')}")
                        
                        st.markdown("<hr>", unsafe_allow_html=True)
            else:
                st.warning("Nenhum resultado encontrado")
    
    with tab2:
        st.markdown("**Análise de Imagem Científica**")
        
        uploaded_image = st.file_uploader("Carregue uma imagem científica", 
                                          type=["png", "jpg", "jpeg", "webp"])
        
        if uploaded_image:
            img_bytes = uploaded_image.read()
            st.image(img_bytes, width=300)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Análise ML"):
                    with st.spinner("Analisando imagem..."):
                        analysis = analyze_scientific_image(img_bytes)
                        
                        st.markdown("**Resultado da Análise ML:**")
                        st.json({
                            "tipo_imagem": analysis.get("image_type"),
                            "qualidade": f"{analysis.get('quality_score', 0):.0f}%",
                            "tamanho": analysis.get("size"),
                            "keypoints": analysis.get("keypoints"),
                            "complexidade_textura": f"{analysis.get('texture_complexity', 0):.2f}"
                        })
            
            with col2:
                if has_api and st.button("Análise Claude Vision"):
                    prompt = """Analise esta imagem científica e identifique:
1. Tipo de imagem (ex: microscopia, histopatologia, etc)
2. Técnica utilizada
3. Possíveis aplicações
4. Qualidade da imagem
5. Sugestões para pesquisas relacionadas"""
                    
                    with st.spinner("Claude analisando..."):
                        result, error = call_claude_vision(img_bytes, prompt, api_key)
                        if result:
                            st.markdown("**Análise Claude Vision:**")
                            st.write(result)
                        elif error:
                            st.error(f"Erro: {error}")
    
    with tab3:
        st.markdown("**Busca Avançada com Filtros**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            year_from = st.number_input("Ano a partir de", 1900, 2100, 2020)
        with col2:
            year_to = st.number_input("Até ano", 1900, 2100, 2024)
        with col3:
            min_citations = st.number_input("Mínimo de citações", 0, 1000, 0)
        
        search_text = st.text_input("Termo de busca avançado")
        
        if st.button("Buscar com Filtros"):
            results = search_semantic_scholar(search_text, 15)
            
            filtered = [p for p in results 
                       if (year_from <= p.get('year', 2024) <= year_to and 
                           p.get('citations', 0) >= min_citations)]
            
            st.markdown(f"**Encontrados: {len(filtered)} papers**")
            for paper in filtered:
                st.markdown(f"**{paper['title']}** ({paper['year']}) - {paper['citations']} citações")
    
    st.markdown('</div>', unsafe_allow_html=True)

# ===============================================
#  PÁGINA: CONEXÕES
# ===============================================
def page_connections():
    st.markdown('<div style="padding-top:1rem">', unsafe_allow_html=True)
    st.markdown('<h1>Mapa de Conexões entre Pesquisas</h1>', unsafe_allow_html=True)
    
    # Coletar todos os papers
    all_papers = []
    for repo_name, repo_data in st.session_state.repositories.items():
        for paper in repo_data.get("papers", []):
            paper["repo"] = repo_name
            all_papers.append(paper)
    
    if len(all_papers) < 2:
        st.warning("Adicione ao menos 2 papers para ver conexões")
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    # Criar grafo de conexões
    nodes = []
    edges = []
    
    for idx, paper in enumerate(all_papers):
        nodes.append({
            "id": idx,
            "label": paper["title"][:25],
            "area": paper["metadata"]["area"]
        })
    
    # Encontrar conexões baseadas em palavras-chave
    for i in range(len(all_papers)):
        for j in range(i+1, len(all_papers)):
            kw1 = set(all_papers[i]['metadata'].get('keywords', []))
            kw2 = set(all_papers[j]['metadata'].get('keywords', []))
            
            if kw1 and kw2:
                common = kw1 & kw2
                if len(common) > 0:
                    similarity = len(common) / len(kw1 | kw2)
                    edges.append({
                        "source": i,
                        "target": j,
                        "weight": similarity,
                        "common_kw": list(common)[:3]
                    })
    
    # Grafo 2D/3D com plotly
    edge_x = []
    edge_y = []
    
    # Posições circulares
    positions = {}
    n = len(nodes)
    for i, node in enumerate(nodes):
        angle = 2 * np.pi * i / n
        positions[i] = (np.cos(angle), np.sin(angle))
    
    for edge in edges:
        x0, y0 = positions[edge["source"]]
        x1, y1 = positions[edge["target"]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    # Nós
    node_x = [positions[n["id"]][0] for n in nodes]
    node_y = [positions[n["id"]][1] for n in nodes]
    
    node_text = [n["label"] for n in nodes]
    node_color = [hash(n["area"]) % 256 for n in nodes]
    
    fig = go.Figure()
    
    # Edges
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y,
        mode='lines',
        line=dict(width=0.5, color='rgba(13,127,232,0.2)'),
        hoverinfo='none',
        showlegend=False
    ))
    
    # Nodes
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="top center",
        hoverinfo='text',
        marker=dict(
            showscale=True,
            color=node_color,
            colorscale='Viridis',
            size=20,
            line=dict(width=2, color='rgba(255,255,255,0.1)')
        ),
        showlegend=False
    ))
    
    fig.update_layout(
        title="Grafo de Conexões entre Pesquisas",
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=40),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=600,
        font=dict(color="#5A6180")
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Estatísticas
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("**Análise de Conexões:**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Papers", len(all_papers))
    with col2:
        st.metric("Conexões Encontradas", len(edges))
    with col3:
        if edges:
            avg_strength = np.mean([e["weight"] for e in edges])
            st.metric("Força Média", f"{avg_strength:.2f}")
    
    # Lista de conexões mais fortes
    st.markdown("**Conexões Mais Fortes:**")
    strong_edges = sorted(edges, key=lambda x: x["weight"], reverse=True)[:10]
    
    for edge in strong_edges:
        paper1 = all_papers[edge["source"]]
        paper2 = all_papers[edge["target"]]
        st.markdown(f"""
        **{paper1['title']}** ↔ **{paper2['title']}**
        
        Força: {edge['weight']:.0%} | Palavras-chave comuns: {', '.join(edge['common_kw'])}
        """)
        st.markdown("<hr>", unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ===============================================
#  PÁGINA: CONFIGURAÇÕES
# ===============================================
def page_settings():
    st.markdown('<div style="padding-top:1rem">', unsafe_allow_html=True)
    st.markdown('<h1>Configurações</h1>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Perfil", "API"])
    
    with tab1:
        email = st.session_state.current_user
        user = st.session_state.users.get(email, {})
        
        st.markdown(f"**Email:** {email}")
        
        name = st.text_input("Nome", value=user.get("name", ""))
        area = st.selectbox("Área de Pesquisa", 
            ["Biologia Molecular", "Neurociência", "Inteligência Artificial", 
             "Física Quântica", "Astrofísica", "Química", "Medicina Clínica",
             "Ecologia", "Engenharia", "Matemática"],
            index=0)
        
        if st.button("Salvar Perfil"):
            st.session_state.users[email]["name"] = name
            st.session_state.users[email]["area"] = area
            save_db()
            st.success("Perfil atualizado!")
        
        st.markdown("<hr>", unsafe_allow_html=True)
        
        if st.button("Sair", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.session_state.page = "login"
            st.rerun()
    
    with tab2:
        st.markdown("**Claude API Key**")
        api_key = st.text_input("API Key", 
                               value=st.session_state.get("anthropic_key", ""),
                               type="password",
                               placeholder="sk-ant-...")
        
        if api_key != st.session_state.get("anthropic_key", ""):
            st.session_state.anthropic_key = api_key
            st.success("API Key atualizada")
        
        if api_key.startswith("sk-"):
            st.info("Claude Vision está ativo")
        else:
            st.warning("Insira uma API key válida para ativar Claude Vision")
    
    st.markdown('</div>', unsafe_allow_html=True)

# ===============================================
#  NAVEGAÇÃO
# ===============================================
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;margin-bottom:2rem">
            <div style="font-size:2.2rem;margin-bottom:.5rem">🔬</div>
            <div style="font-family:Syne,sans-serif;font-weight:900;font-size:1.3rem;background:linear-gradient(135deg,#0D7FE8,#36B8A0);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">Nebula</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<hr>", unsafe_allow_html=True)
        
        if st.button("📁 Repositórios", use_container_width=True):
            st.session_state.page = "repositories"
            st.rerun()
        
        if st.button("📊 Análise", use_container_width=True):
            st.session_state.page = "analysis"
            st.rerun()
        
        if st.button("🔍 Busca & Visão IA", use_container_width=True):
            st.session_state.page = "search_vision"
            st.rerun()
        
        if st.button("🕸 Conexões", use_container_width=True):
            st.session_state.page = "connections"
            st.rerun()
        
        if st.button("⚙️ Configurações", use_container_width=True):
            st.session_state.page = "settings"
            st.rerun()
        
        st.markdown("<hr>", unsafe_allow_html=True)
        
        user = st.session_state.users.get(st.session_state.current_user, {})
        st.markdown(f"""
        **{user.get('name', 'Usuário')}**
        
        {user.get('area', 'Pesquisador')}
        """)

# ===============================================
#  MAIN
# ===============================================
def main():
    inject_css()
    
    if not st.session_state.logged_in:
        page_login()
        return
    
    render_sidebar()
    
    page_map = {
        "repositories": page_repositories,
        "analysis": page_analysis,
        "search_vision": page_search_vision,
        "connections": page_connections,
        "settings": page_settings,
    }
    
    current_page = st.session_state.get("page", "repositories")
    if current_page in page_map:
        page_map[current_page]()
    else:
        st.error("Página não encontrada")

if __name__ == "__main__":
    main()
