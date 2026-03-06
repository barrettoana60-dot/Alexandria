import subprocess, sys, os, json, hashlib, random, string, re, io, base64, time
from datetime import datetime, date
from collections import defaultdict, Counter

def _pip(*pkgs):
    for p in pkgs:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", p, "-q"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except:
            pass

# Instalações condicionais
try:
    import plotly.graph_objects as go
except:
    _pip("plotly")
    import plotly.graph_objects as go

try:
    import numpy as np
    from PIL import Image as PILImage
except:
    _pip("pillow", "numpy")
    import numpy as np
    from PIL import Image as PILImage

try:
    import requests
except:
    _pip("requests")
    import requests

# PyPDF2: se falhar, fica como None (a função extract_pdf já trata)
try:
    import PyPDF2
except:
    PyPDF2 = None

try:
    import openpyxl
except:
    openpyxl = None

try:
    import pandas as pd
except:
    pd = None

# ML / Image Processing — com fallbacks numpy
SKIMAGE_OK = False
SKLEARN_OK = False
SCIPY_OK = False

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
    SKLEARN_OK = True
except:
    try:
        _pip("scikit-learn")
        from sklearn.cluster import KMeans
        SKLEARN_OK = True
    except:
        SKLEARN_OK = False

try:
    from scipy import ndimage as sp_ndimage
    SCIPY_OK = True
except:
    try:
        _pip("scipy")
        from scipy import ndimage as sp_ndimage
        SCIPY_OK = True
    except:
        SCIPY_OK = False

import streamlit as st

st.set_page_config(
    page_title="Nebula", page_icon="🔬", layout="wide", initial_sidebar_state="expanded"
)

DB_FILE = "nebula_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def hp(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def code6():
    return "".join(random.choices(string.digits, k=6))

def ini(n):
    if not isinstance(n, str):
        n = str(n)
    p = n.strip().split()
    return "".join(w[0].upper() for w in p[:2]) if p else "?"

def time_ago(ds):
    try:
        dt = datetime.strptime(ds, "%Y-%m-%d")
        d = (datetime.now() - dt).days
        if d == 0:
            return "hoje"
        if d == 1:
            return "ontem"
        if d < 7:
            return f"{d}d"
        if d < 30:
            return f"{d // 7}sem"
        return f"{d // 30}m"
    except:
        return ds

def fmt_num(n):
    try:
        n = int(n)
        return f"{n / 1000:.1f}k" if n >= 1000 else str(n)
    except:
        return str(n)

def guser():
    if not isinstance(st.session_state.get("users"), dict):
        return {}
    return st.session_state.users.get(st.session_state.current_user, {})

def is_online(e):
    return (hash(e + "on") % 3) != 0

# Gradientes azul escuro
GRAD_POOL = [
    "135deg,#0A1929,#1A2F4A",
    "135deg,#0B1E33,#1D3A5A",
    "135deg,#0C2138,#20456A",
    "135deg,#0D253D,#23507A",
    "135deg,#0E2942,#265B8A",
    "135deg,#0F2D47,#29669A",
]

def ugrad(e):
    return f"linear-gradient({GRAD_POOL[hash(e or '') % len(GRAD_POOL)]})"

STOPWORDS = {
    "de",
    "a",
    "o",
    "que",
    "e",
    "do",
    "da",
    "em",
    "um",
    "para",
    "é",
    "com",
    "uma",
    "os",
    "no",
    "se",
    "na",
    "por",
    "mais",
    "as",
    "dos",
    "como",
    "mas",
    "foi",
    "ao",
    "ele",
    "das",
    "tem",
    "à",
    "seu",
    "sua",
    "ou",
    "ser",
    "quando",
    "muito",
    "há",
    "nos",
    "já",
    "está",
    "eu",
    "também",
    "só",
    "pelo",
    "pela",
    "até",
    "isso",
    "ela",
    "entre",
    "era",
    "depois",
    "sem",
    "mesmo",
    "aos",
    "ter",
    "seus",
    "the",
    "of",
    "and",
    "to",
    "in",
    "is",
    "it",
    "that",
    "was",
    "he",
    "for",
    "on",
    "are",
    "as",
    "with",
    "they",
    "at",
    "be",
    "this",
    "from",
    "or",
    "one",
    "had",
    "by",
    "but",
    "not",
    "what",
    "all",
    "were",
    "we",
    "when",
    "your",
    "can",
    "said",
    "there",
    "use",
    "an",
    "each",
    "which",
    "she",
    "do",
    "how",
    "their",
    "if",
    "will",
    "up",
    "other",
    "about",
    "out",
    "many",
    "then",
    "them",
    "these",
    "so",
}

SEED_POSTS = [
    {
        "id": 1,
        "author": "Carlos Mendez",
        "author_email": "carlos@nebula.ai",
        "avatar": "CM",
        "area": "Neurociência",
        "title": "Efeitos da Privação de Sono na Plasticidade Sináptica",
        "abstract": "Investigamos como 24h de privação de sono afetam espinhas dendríticas em ratos Wistar, com redução de 34% na plasticidade hipocampal.",
        "tags": ["neurociência", "sono", "memória", "hipocampo"],
        "likes": 47,
        "comments": [{"user": "Maria Silva", "text": "Excelente metodologia!"}],
        "status": "Em andamento",
        "date": "2026-02-10",
        "liked_by": [],
        "saved_by": [],
        "connections": ["sono", "memória"],
        "views": 312,
    },
    {
        "id": 2,
        "author": "Luana Freitas",
        "author_email": "luana@nebula.ai",
        "avatar": "LF",
        "area": "Biomedicina",
        "title": "CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras",
        "abstract": "Vetor AAV9 modificado para entrega de CRISPR no gene DMD com eficiência de 78% em modelos mdx.",
        "tags": ["CRISPR", "gene terapia", "músculo", "AAV9"],
        "likes": 93,
        "comments": [{"user": "Ana", "text": "Quando iniciam os trials?"}],
        "status": "Publicado",
        "date": "2026-01-28",
        "liked_by": [],
        "saved_by": [],
        "connections": ["genômica", "distrofia"],
        "views": 891,
    },
    {
        "id": 3,
        "author": "Rafael Souza",
        "author_email": "rafael@nebula.ai",
        "avatar": "RS",
        "area": "Computação",
        "title": "Redes Neurais Quântico-Clássicas para Otimização Combinatória",
        "abstract": "Arquitetura híbrida variacional combinando qubits supercondutores com camadas densas clássicas. TSP resolvido com 40% menos iterações.",
        "tags": ["quantum ML", "otimização", "TSP"],
        "likes": 201,
        "comments": [],
        "status": "Em andamento",
        "date": "2026-02-15",
        "liked_by": [],
        "saved_by": [],
        "connections": ["computação quântica"],
        "views": 1240,
    },
    {
        "id": 4,
        "author": "Priya Nair",
        "author_email": "priya@nebula.ai",
        "avatar": "PN",
        "area": "Astrofísica",
        "title": "Detecção de Matéria Escura via Lentes Gravitacionais Fracas",
        "abstract": "Mapeamento com 100M de galáxias do DES Y3. Tensão de 2.8σ com ΛCDM em escalas < 1 Mpc.",
        "tags": ["astrofísica", "matéria escura", "cosmologia", "DES"],
        "likes": 312,
        "comments": [],
        "status": "Publicado",
        "date": "2026-02-01",
        "liked_by": [],
        "saved_by": [],
        "connections": ["cosmologia"],
        "views": 2180,
    },
    {
        "id": 5,
        "author": "João Lima",
        "author_email": "joao@nebula.ai",
        "avatar": "JL",
        "area": "Psicologia",
        "title": "Viés de Confirmação em Decisões Médicas Assistidas por IA",
        "abstract": "Estudo duplo-cego com 240 médicos revelou que sistemas de IA mal calibrados amplificam vieses cognitivos em 22% dos casos.",
        "tags": ["psicologia", "IA", "cognição", "medicina"],
        "likes": 78,
        "comments": [{"user": "Carlos M.", "text": "Muito relevante!"}],
        "status": "Publicado",
        "date": "2026-02-08",
        "liked_by": [],
        "saved_by": [],
        "connections": ["cognição", "IA"],
        "views": 456,
    },
]

SEED_USERS = {
    "demo@nebula.ai": {
        "name": "Ana Pesquisadora",
        "password": hp("demo123"),
        "bio": "Pesquisadora em IA e Ciências Cognitivas | UFMG",
        "area": "Inteligência Artificial",
        "followers": 128,
        "following": 47,
        "verified": True,
        "2fa_enabled": False,
    },
    "carlos@nebula.ai": {
        "name": "Carlos Mendez",
        "password": hp("nebula123"),
        "bio": "Neurocientista | UFMG | Plasticidade sináptica e sono",
        "area": "Neurociência",
        "followers": 210,
        "following": 45,
        "verified": True,
        "2fa_enabled": False,
    },
    "luana@nebula.ai": {
        "name": "Luana Freitas",
        "password": hp("nebula123"),
        "bio": "Biomédica | FIOCRUZ | CRISPR e terapia gênica",
        "area": "Biomedicina",
        "followers": 178,
        "following": 62,
        "verified": True,
        "2fa_enabled": False,
    },
    "rafael@nebula.ai": {
        "name": "Rafael Souza",
        "password": hp("nebula123"),
        "bio": "Computação Quântica | USP | Algoritmos híbridos",
        "area": "Computação",
        "followers": 340,
        "following": 88,
        "verified": True,
        "2fa_enabled": False,
    },
    "priya@nebula.ai": {
        "name": "Priya Nair",
        "password": hp("nebula123"),
        "bio": "Astrofísica | MIT | Dark matter & gravitational lensing",
        "area": "Astrofísica",
        "followers": 520,
        "following": 31,
        "verified": True,
        "2fa_enabled": False,
    },
    "joao@nebula.ai": {
        "name": "João Lima",
        "password": hp("nebula123"),
        "bio": "Psicólogo Cognitivo | UNICAMP | IA e vieses clínicos",
        "area": "Psicologia",
        "followers": 95,
        "following": 120,
        "verified": True,
        "2fa_enabled": False,
    },
}

CHAT_INIT = {
    "carlos@nebula.ai": [
        {
            "from": "carlos@nebula.ai",
            "text": "Oi! Vi seu comentário na pesquisa.",
            "time": "09:14",
        },
        {"from": "me", "text": "Achei muito interessante!", "time": "09:16"},
    ],
    "luana@nebula.ai": [
        {
            "from": "luana@nebula.ai",
            "text": "Podemos colaborar no próximo projeto?",
            "time": "ontem",
        }
    ],
}

def save_db():
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "users": st.session_state.users,
                    "feed_posts": st.session_state.feed_posts,
                    "folders": st.session_state.folders,
                    "user_prefs": {
                        k: dict(v) for k, v in st.session_state.user_prefs.items()
                    },
                    "saved_articles": st.session_state.saved_articles,
                    "followed": st.session_state.followed,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
    except:
        pass

def init():
    if "initialized" in st.session_state:
        return
    st.session_state.initialized = True
    disk = load_db()
    du = disk.get("users", {})
    if not isinstance(du, dict):
        du = {}
    st.session_state.setdefault("users", {**SEED_USERS, **du})
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("current_user", None)
    st.session_state.setdefault("page", "repository")
    st.session_state.setdefault("profile_view", None)
    dp = disk.get("user_prefs", {})
    st.session_state.setdefault(
        "user_prefs", {k: defaultdict(float, v) for k, v in dp.items()}
    )
    st.session_state.setdefault("pending_verify", None)
    st.session_state.setdefault("pending_2fa", None)
    rp = disk.get("feed_posts", [dict(p) for p in SEED_POSTS])
    for p in rp:
        p.setdefault("liked_by", [])
        p.setdefault("saved_by", [])
        p.setdefault("comments", [])
        p.setdefault("views", 200)
    st.session_state.setdefault("feed_posts", rp)

    # Pastas: enriquecer se antigas
    folders = disk.get("folders", {})
    if isinstance(folders, dict):
        for fn, fd in list(folders.items()):
            if not isinstance(fd, dict):
                folders[fn] = {
                    "desc": "",
                    "files": fd,
                    "notes": "",
                    "analyses": {},
                    "topics_agg": {},
                    "keywords_agg": [],
                    "last_updated": datetime.now().isoformat(),
                    "owner": None,
                    "visibility": "private",
                }
            else:
                fd.setdefault("desc", "")
                fd.setdefault("files", [])
                fd.setdefault("notes", "")
                fd.setdefault("analyses", {})
                fd.setdefault("topics_agg", {})
                fd.setdefault("keywords_agg", [])
                fd.setdefault("last_updated", datetime.now().isoformat())
                fd.setdefault("owner", None)
                fd.setdefault("visibility", "private")
    else:
        folders = {}
    st.session_state.setdefault("folders", folders)

    st.session_state.setdefault("folder_files_bytes", {})
    st.session_state.setdefault("chat_contacts", list(SEED_USERS.keys()))
    st.session_state.setdefault(
        "chat_messages", {k: list(v) for k, v in CHAT_INIT.items()}
    )
    st.session_state.setdefault("active_chat", None)
    st.session_state.setdefault(
        "followed", disk.get("followed", ["carlos@nebula.ai", "luana@nebula.ai"])
    )
    st.session_state.setdefault(
        "notifications", ["Carlos curtiu sua pesquisa", "Nova conexão detectada"]
    )
    st.session_state.setdefault("scholar_cache", {})
    st.session_state.setdefault("saved_articles", disk.get("saved_articles", []))
    st.session_state.setdefault("img_result", None)
    st.session_state.setdefault("search_results", None)
    st.session_state.setdefault("last_sq", "")
    st.session_state.setdefault(
        "stats_data", {"h_index": 4, "fator_impacto": 3.8, "notes": ""}
    )
    st.session_state.setdefault("compose_open", False)
    st.session_state.setdefault("anthropic_key", "")
    st.session_state.setdefault("ai_conn_cache", {})
    st.session_state.setdefault("ml_cache", {})  # cache para análises ML
    st.session_state.setdefault("local_index_version", 0)

init()

# ================================================
#  IA REAL — CLAUDE VISION (opcional)
# ================================================
def call_claude_vision(img_bytes, prompt, api_key):
    """Envia imagem para Claude Vision API e retorna análise."""
    if not api_key or not api_key.startswith("sk-"):
        return None, "Chave API inválida ou ausente."
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
                "content-type": "application/json",
            },
            json={
                "model": "claude-3-opus-20240229",
                "max_tokens": 1200,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": b64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            },
            timeout=25,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data["content"][0]["text"], None
        else:
            try:
                err = resp.json().get("error", {}).get(
                    "message", f"HTTP {resp.status_code}"
                )
            except:
                err = f"HTTP {resp.status_code}"
            return None, err
    except Exception as e:
        return None, str(e)

VISION_PROMPT = """Você é um especialista em análise de imagens científicas. Analise esta imagem com máximo detalhe e responda em JSON exatamente neste formato (sem markdown, só JSON puro):

{
  "tipo": "<tipo da imagem: microscopia óptica/eletrônica, fluorescência, cristalografia, difração, gel eletroforese, western blot, imunofluorescência, histopatologia, gráfico científico, diagrama, espectroscopia, radiografia, tomografia, ressonância, imagem astronômica, imagem celular, imagem molecular, etc>",
  "origem": "<de onde provavelmente vem esta imagem: biologia celular, microbiologia, neurociência, oncologia, genômica, física de partículas, astrofísica, química, materiais, medicina clínica, etc>",
  "descricao": "<descrição científica detalhada do que é visível: estruturas, padrões, cores, organização>",
  "estruturas": ["<estrutura 1>", "<estrutura 2>", "<estrutura 3>"],
  "tecnica": "<técnica experimental provável: H&E staining, DAPI, GFP, confocal, TEM, SEM, fluorescência, difração X, PCR gel, etc>",
  "qualidade": "<Alta/Média/Baixa - qualidade técnica da imagem>",
  "confianca": <número de 0 a 100 de confiança na classificação>,
  "termos_busca": "<3-5 termos científicos para buscar artigos relacionados>",
  "observacoes": "<observações científicas relevantes sobre o conteúdo>"
}"""

def call_claude_connections(users_data, posts_data, email, api_key):
    """Usa Claude para sugerir conexões inteligentes."""
    if not api_key or not api_key.startswith("sk-"):
        return None, "API key ausente."
    try:
        u = users_data.get(email, {})
        my_posts = [p for p in posts_data if p.get("author_email") == email]
        others = [
            {
                "email": ue,
                "name": ud.get("name", ""),
                "area": ud.get("area", ""),
                "tags": list(
                    {
                        t
                        for p in posts_data
                        if p.get("author_email") == ue
                        for t in p.get("tags", [])
                    }
                )[:8],
            }
            for ue, ud in users_data.items()
            if ue != email
        ]
        payload = {
            "meu_perfil": {
                "area": u.get("area", ""),
                "bio": u.get("bio", ""),
                "tags": list({t for p in my_posts for t in p.get("tags", [])})[:10],
            },
            "pesquisadores": others[:20],
        }
        prompt = f"""Você é um sistema de recomendação de conexões científicas. Dado meu perfil e outros pesquisadores, sugira as 4 melhores conexões com justificativa científica.

Dados:
{json.dumps(payload, ensure_ascii=False)}

Responda APENAS em JSON puro (sem markdown):
{{
  "sugestoes": [
    {{"email": "<email>", "razao": "<explicação científica de 1-2 frases>", "score": <0-100>, "temas_comuns": ["<tema1>", "<tema2>"]}}
  ]
}}"""
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-3-opus-20240229",
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=20,
        )
        if resp.status_code == 200:
            text = resp.json()["content"][0]["text"].strip()
            text = re.sub(r"^```json\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            return json.loads(text), None
        return None, f"HTTP {resp.status_code}"
    except Exception as e:
        return None, str(e)

# ================================================
#  PIPELINE ML PARA IMAGENS (com fallback numpy)
# ================================================
def sobel_analysis(gray_arr):
    """Detecção de bordas Sobel multi-direcional."""
    try:
        if SKIMAGE_OK:
            import skimage.filters as skf

            sx = skf.sobel_h(gray_arr)
            sy = skf.sobel_v(gray_arr)
        else:
            # Fallback numpy
            kx = (
                np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32) / 8.0
            )
            ky = kx.T
            from numpy import pad as nppad

            def conv2d(img, k):
                ph, pw = k.shape[0] // 2, k.shape[1] // 2
                padded = nppad(img, ((ph, ph), (pw, pw)), mode="edge")
                out = np.zeros_like(img)
                for i in range(k.shape[0]):
                    for j in range(k.shape[1]):
                        out += k[i, j] * padded[i : i + img.shape[0], j : j + img.shape[1]]
                return out

            sx = conv2d(gray_arr.astype(np.float32), kx)
            sy = conv2d(gray_arr.astype(np.float32), ky)
        magnitude = np.sqrt(sx**2 + sy**2)
        direction = np.arctan2(sy, sx) * 180 / np.pi
        try:
            gx2 = np.gradient(gray_arr, axis=1)
            gy2 = np.gradient(gray_arr, axis=0)
        except:
            gx2, gy2 = sx, sy
        return {
            "magnitude": magnitude,
            "horizontal": sx,
            "vertical": sy,
            "mean_edge": float(magnitude.mean()),
            "max_edge": float(magnitude.max()),
            "edge_density": float(
                (magnitude > magnitude.mean() * 1.5).mean()
            ),
            "dominant_direction": float(direction.mean()),
            "edge_hist": np.histogram(
                magnitude, bins=16, range=(0, magnitude.max() + 1e-5)
            )[0].tolist(),
        }
    except Exception:
        gx = np.gradient(gray_arr.astype(np.float32), axis=1)
        gy = np.gradient(gray_arr.astype(np.float32), axis=0)
        mag = np.sqrt(gx**2 + gy**2)
        return {
            "magnitude": mag,
            "horizontal": gx,
            "vertical": gy,
            "mean_edge": float(mag.mean()),
            "max_edge": float(mag.max()),
            "edge_density": float((mag > mag.mean() * 1.5).mean()),
            "dominant_direction": 0.0,
            "edge_hist": np.histogram(mag, bins=16)[0].tolist(),
        }

def canny_analysis(gray_uint8):
    """Detecção de bordas Canny multi-escala."""
    try:
        if SKIMAGE_OK:
            from skimage import feature as skf2

            edges_fine = skf2.canny(gray_uint8 / 255.0, sigma=1.0)
            edges_med = skf2.canny(gray_uint8 / 255.0, sigma=2.0)
            edges_coarse = skf2.canny(gray_uint8 / 255.0, sigma=3.5)
        else:
            g = gray_uint8.astype(np.float32) / 255.0
            gx = np.gradient(g, axis=1)
            gy = np.gradient(g, axis=0)
            mag = np.sqrt(gx**2 + gy**2)
            t1, t2, t3 = (
                np.percentile(mag, 85),
                np.percentile(mag, 75),
                np.percentile(mag, 65),
            )
            edges_fine = mag > t1
            edges_med = mag > t2
            edges_coarse = mag > t3
        return {
            "fine": edges_fine,
            "medium": edges_med,
            "coarse": edges_coarse,
            "fine_density": float(edges_fine.mean()),
            "medium_density": float(edges_med.mean()),
            "coarse_density": float(edges_coarse.mean()),
            "total_edges": int(edges_fine.sum()),
            "structure_level": "micro"
            if edges_fine.mean() > 0.1
            else ("meso" if edges_med.mean() > 0.05 else "macro"),
        }
    except Exception:
        g = gray_uint8.astype(np.float32) / 255.0
        gx = np.gradient(g, axis=1)
        gy = np.gradient(g, axis=0)
        mag = np.sqrt(gx**2 + gy**2)
        e = mag > mag.mean()
        return {
            "fine": e,
            "medium": e,
            "coarse": e,
            "fine_density": float(e.mean()),
            "medium_density": float(e.mean()),
            "coarse_density": float(e.mean()),
            "total_edges": int(e.sum()),
            "structure_level": "meso",
        }

def orb_keypoints(gray_uint8):
    """Detecção de keypoints ORB."""
    try:
        if SKIMAGE_OK:
            try:
                from skimage.feature import ORB

                detector = ORB(n_keypoints=200, fast_threshold=0.05)
                detector.detect_and_extract(gray_uint8 / 255.0)
                kp = detector.keypoints
            except:
                from skimage.feature import corner_harris, corner_peaks

                harris = corner_harris(gray_uint8 / 255.0)
                kp = corner_peaks(
                    harris, min_distance=8, threshold_rel=0.02
                )
        else:
            g = gray_uint8.astype(np.float32)
            gx = np.gradient(g, axis=1)
            gy = np.gradient(g, axis=0)
            mag = np.sqrt(gx**2 + gy**2)
            step = 8
            pts = []
            for i in range(0, mag.shape[0] - step, step):
                for j in range(0, mag.shape[1] - step, step):
                    block = mag[i : i + step, j : j + step]
                    if block.max() > mag.mean() * 1.8:
                        yi, xj = np.unravel_index(block.argmax(), block.shape)
                        pts.append([i + yi, j + xj])
            kp = np.array(pts) if pts else np.zeros((0, 2))

        scales = np.ones(len(kp))
        if len(kp) > 0 and SKLEARN_OK:
            n_cl = min(5, len(kp))
            try:
                kmk = KMeans(
                    n_clusters=n_cl, random_state=42, n_init=5
                ).fit(np.array(kp))
                centers = kmk.cluster_centers_
            except:
                centers = np.array(kp)[:5]
        else:
            centers = np.array(kp)[:5] if len(kp) > 0 else np.zeros((0, 2))
        return {
            "keypoints": kp,
            "n_keypoints": len(kp),
            "cluster_centers": centers.tolist() if len(centers) > 0 else [],
            "scales": scales.tolist(),
            "mean_scale": 1.0,
            "distribution": "uniforme"
            if len(kp) > 5
            and np.std(np.array(kp)[:, 0])
            / (np.std(np.array(kp)[:, 1]) + 1e-5)
            < 1.5
            else "concentrado",
        }
    except Exception:
        return {
            "keypoints": np.zeros((0, 2)),
            "n_keypoints": 0,
            "cluster_centers": [],
            "scales": [],
            "mean_scale": 1.0,
            "distribution": "n/a",
        }

def glcm_texture(gray_uint8):
    """Textura GLCM."""
    try:
        if SKIMAGE_OK:
            from skimage.feature import graycomatrix, graycoprops

            g64 = (gray_uint8 // 4).astype(np.uint8)
            distances = [1, 3, 5]
            angles = [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]
            glcm = graycomatrix(
                g64,
                distances=distances,
                angles=angles,
                levels=64,
                symmetric=True,
                normed=True,
            )
            features = {}
            for prop in [
                "contrast",
                "dissimilarity",
                "homogeneity",
                "energy",
                "correlation",
                "ASM",
            ]:
                v = graycoprops(glcm, prop)
                features[prop] = float(v.mean())
            features["contrast_std"] = float(
                graycoprops(glcm, "contrast").std()
            )
            features["uniformity"] = features["energy"]
            features["entropy"] = float(
                -np.sum(
                    glcm[glcm > 0] * np.log2(glcm[glcm > 0] + 1e-12)
                )
            )
        else:
            g = gray_uint8.astype(np.float32) / 255.0
            gx = np.gradient(g, axis=1)
            gy = np.gradient(g, axis=0)
            contrast = float(np.sqrt(gx**2 + gy**2).mean() * 100)
            homogeneity = float(1.0 / (1.0 + contrast / 50.0))
            energy = float(np.var(g))
            correlation = float(
                np.corrcoef(gx.ravel(), gy.ravel())[0, 1]
            ) if len(gx.ravel()) > 1 else 0.5
            hst = np.histogram(g, bins=64)[0]
            hn = hst / hst.sum() + 1e-12
            entropy_v = float(-np.sum(hn * np.log2(hn)))
            features = {
                "contrast": round(contrast, 4),
                "dissimilarity": round(contrast * 0.5, 4),
                "homogeneity": round(homogeneity, 4),
                "energy": round(energy, 4),
                "correlation": round(abs(correlation), 4),
                "ASM": round(energy**2, 4),
                "contrast_std": 0.0,
                "uniformity": round(energy, 4),
                "entropy": round(entropy_v, 4),
            }
        features["texture_type"] = classify_texture(features)
        return features
    except Exception as e:
        return {
            "homogeneity": 0.5,
            "contrast": 20.0,
            "energy": 0.1,
            "correlation": 0.7,
            "ASM": 0.01,
            "dissimilarity": 10.0,
            "contrast_std": 0.0,
            "uniformity": 0.1,
            "entropy": 4.0,
            "texture_type": "desconhecido",
            "error": str(e),
        }

def classify_texture(f):
    if f.get("homogeneity", 0) > 0.7:
        return "homogênea"
    if f.get("contrast", 0) > 50:
        return "altamente texturizada"
    if f.get("energy", 0) > 0.1:
        return "uniforme/periódica"
    if f.get("correlation", 0) > 0.8:
        return "estruturada"
    return "complexa"

def kmeans_colors(img_arr, k=7):
    """Cores dominantes via KMeans."""
    if not SKLEARN_OK:
        return [], []
    try:
        h, w = img_arr.shape[:2]
        step = max(1, (h * w) // 4000)
        flat = img_arr.reshape(-1, 3)[::step].astype(np.float32)
        km = KMeans(
            n_clusters=k, random_state=42, n_init=5, max_iter=100
        ).fit(flat)
        centers = km.cluster_centers_.astype(int)
        counts = Counter(km.labels_)
        total = sum(counts.values())
        palette = []
        for i in np.argsort([-counts[j] for j in range(k)]):
            r, g, b = centers[i]
            pct = counts[i] / total * 100
            hex_c = "#{:02x}{:02x}{:02x}".format(int(r), int(g), int(b))
            palette.append(
                {
                    "rgb": (int(r), int(g), int(b)),
                    "hex": hex_c,
                    "pct": round(pct, 1),
                }
            )
        temps = []
        for c in palette[:3]:
            r, g, b = c["rgb"]
            if r > b + 20:
                temps.append("quente")
            elif b > r + 20:
                temps.append("fria")
            else:
                temps.append("neutra")
        return palette, temps
    except:
        return [], []

def fft_analysis(gray_arr):
    """Análise de frequência via FFT."""
    fft = np.fft.fft2(gray_arr)
    fft_shift = np.fft.fftshift(fft)
    magnitude = np.abs(fft_shift)
    h, w = magnitude.shape
    center = magnitude[h // 2 - 30 : h // 2 + 30, w // 2 - 30 : w // 2 + 30]
    outer = np.concatenate(
        [magnitude[: h // 4, :].ravel(), magnitude[3 * h // 4 :, :].ravel()]
    )
    periodic_score = float(np.percentile(outer, 99)) / (
        float(np.mean(outer)) + 1e-5
    )
    total = magnitude.sum() + 1e-5
    r = min(h, w) // 2
    Y, X = np.ogrid[:h, :w]
    dist = np.sqrt((X - w // 2) ** 2 + (Y - h // 2) ** 2)
    lf = float(magnitude[dist < r * 0.1].sum() / total)
    mf = float(
        magnitude[(dist >= r * 0.1) & (dist < r * 0.4)].sum() / total
    )
    hf = float(magnitude[dist >= r * 0.4].sum() / total)
    return {
        "periodic_score": round(periodic_score, 2),
        "is_periodic": periodic_score > 12,
        "low_freq": round(lf, 3),
        "mid_freq": round(mf, 3),
        "high_freq": round(hf, 3),
        "dominant_scale": "fina"
        if hf > 0.5
        else ("média" if mf > 0.3 else "grossa"),
    }

def classify_scientific_image(
    sobel_r, canny_r, glcm_r, orb_r, fft_r, color_info, kmeans_palette
):
    """Classificação baseada em regras usando todas as features."""
    ei = sobel_r["mean_edge"]
    ed = sobel_r["edge_density"]
    sym = color_info["symmetry"]
    entropy = color_info["entropy"]
    n_kp = orb_r["n_keypoints"]
    periodic = fft_r["is_periodic"]
    hom = glcm_r.get("homogeneity", 0.5)
    contrast = glcm_r.get("contrast", 20)
    corr = glcm_r.get("correlation", 0.5)
    mr, mg, mb = color_info["r"], color_info["g"], color_info["b"]

    scores = {}

    # H&E Histopathology
    he_score = 0
    if mr > 140 and mb > 100 and mg < mr:
        he_score += 30
    if n_kp > 80:
        he_score += 20
    if contrast > 30:
        he_score += 20
    if ed > 0.12:
        he_score += 15
    if glcm_r.get("texture_type") == "complexa":
        he_score += 15
    scores["Histopatologia H&E"] = he_score

    # DAPI
    dapi_score = 0
    if mb > 150 and mb > mr + 30:
        dapi_score += 45
    if entropy > 5.0:
        dapi_score += 20
    if ed > 0.1:
        dapi_score += 20
    if n_kp > 30:
        dapi_score += 15
    scores["Fluorescência DAPI/Nuclear"] = dapi_score

    # GFP
    gfp_score = 0
    if mg > 150 and mg > mr + 30:
        gfp_score += 45
    if entropy > 4.5:
        gfp_score += 20
    if ed > 0.08:
        gfp_score += 20
    scores["Fluorescência GFP/Verde"] = gfp_score

    # Cristalografia
    xray_score = 0
    if periodic:
        xray_score += 40
    if sym > 0.75:
        xray_score += 25
    if hom > 0.7:
        xray_score += 15
    if fft_r["periodic_score"] > 15:
        xray_score += 20
    scores["Cristalografia/Difração"] = xray_score

    # Western blot
    wb_score = 0
    if contrast < 15 and hom > 0.8:
        wb_score += 30
    if abs(mr - mg) < 20 and abs(mg - mb) < 20:
        wb_score += 25
    if canny_r["coarse_density"] > canny_r["fine_density"]:
        wb_score += 25
    scores["Gel/Western Blot"] = wb_score

    # Gráfico/Diagrama
    chart_score = 0
    if glcm_r.get("energy", 0) > 0.15:
        chart_score += 30
    if hom > 0.85:
        chart_score += 25
    if n_kp < 30:
        chart_score += 20
    if entropy < 4.0:
        chart_score += 25
    scores["Gráfico/Diagrama Científico"] = chart_score

    # Estrutura molecular
    mol_score = 0
    if sym > 0.80:
        mol_score += 35
    if periodic:
        mol_score += 25
    if corr > 0.8:
        mol_score += 20
    if abs(mr - mg) < 25 and abs(mg - mb) < 25:
        mol_score += 20
    scores["Estrutura Molecular"] = mol_score

    # Confocal
    conf_score = 0
    if len(kmeans_palette) > 4:
        conf_score += 20
    if entropy > 5.5:
        conf_score += 25
    if n_kp > 50:
        conf_score += 20
    if ed > 0.10:
        conf_score += 20
    if contrast > 20:
        conf_score += 15
    scores["Microscopia Confocal"] = conf_score

    # Astronomia
    astro_score = 0
    if color_info.get("brightness", 128) < 60:
        astro_score += 35
    if n_kp > 40 and hom > 0.7:
        astro_score += 25
    if entropy > 5.0:
        astro_score += 20
    if fft_r["high_freq"] > 0.4:
        astro_score += 20
    scores["Imagem Astronômica"] = astro_score

    best = max(scores, key=scores.get)
    best_score = scores[best]
    conf = min(96, 40 + best_score * 0.55)

    origin_map = {
        "Histopatologia H&E": "Medicina/Patologia — análise de tecidos corados para diagnóstico",
        "Fluorescência DAPI/Nuclear": "Biologia Celular — marcação de DNA/núcleos com fluoróforo azul",
        "Fluorescência GFP/Verde": "Biologia Molecular — expressão de proteínas fluorescentes verdes",
        "Cristalografia/Difração": "Física/Química — análise de estrutura cristalina por difração",
        "Gel/Western Blot": "Bioquímica/Genômica — separação eletroforética de proteínas/DNA",
        "Gráfico/Diagrama Científico": "Ciência em geral — visualização de dados ou esquema",
        "Estrutura Molecular": "Química Computacional — visualização de moléculas ou cristais",
        "Microscopia Confocal": "Biologia Celular — imagem multicanal de fluorescência confocal",
        "Imagem Astronômica": "Astrofísica — observação de objetos celestes ou fenômenos cósmicos",
    }
    search_map = {
        "Histopatologia H&E": "hematoxylin eosin staining histopathology tissue diagnosis",
        "Fluorescência DAPI/Nuclear": "DAPI nuclear staining fluorescence microscopy cells",
        "Fluorescência GFP/Verde": "GFP green fluorescent protein confocal microscopy",
        "Cristalografia/Difração": "X-ray diffraction crystallography crystal structure",
        "Gel/Western Blot": "western blot gel electrophoresis protein DNA analysis",
        "Gráfico/Diagrama Científico": "scientific data visualization chart analysis",
        "Estrutura Molecular": "molecular structure protein crystal visualization",
        "Microscopia Confocal": "confocal microscopy fluorescence multichannel imaging",
        "Imagem Astronômica": "astronomy deep field observation telescope imaging",
    }
    return {
        "category": best,
        "confidence": round(conf, 1),
        "origin": origin_map.get(best, "Ciência Geral"),
        "search_kw": search_map.get(best, best + " scientific imaging"),
        "all_scores": dict(
            sorted(scores.items(), key=lambda x: -x[1])[:5]
        ),
    }

@st.cache_data(show_spinner=False, ttl=3600)
def run_full_ml_pipeline_cached(img_bytes):
    """Versão cacheada do pipeline ML completo."""
    return run_full_ml_pipeline(img_bytes)

def run_full_ml_pipeline(img_bytes):
    """Pipeline ML completo: Sobel + Canny + ORB + GLCM + KMeans + FFT."""
    result = {}
    try:
        img = PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
        orig_size = img.size
        w, h = img.size
        scale = min(384 / w, 384 / h)
        new_w, new_h = int(w * scale), int(h * scale)
        img_r = img.resize((new_w, new_h), PILImage.LANCZOS)
        arr = np.array(img_r, dtype=np.float32)
        r_ch, g_ch, b_ch = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        gray = 0.2989 * r_ch + 0.5870 * g_ch + 0.1140 * b_ch
        gray_u8 = gray.astype(np.uint8)
        mr, mg, mb = float(r_ch.mean()), float(g_ch.mean()), float(b_ch.mean())

        hy, hx = gray.shape[0] // 2, gray.shape[1] // 2
        q = [
            gray[:hy, :hx].var(),
            gray[:hy, hx:].var(),
            gray[hy:, :hx].var(),
            gray[hy:, hx:].var(),
        ]
        sym = 1.0 - (max(q) - min(q)) / (max(q) + 1e-5)

        hst = np.histogram(gray, bins=64, range=(0, 255))[0]
        hn = hst / hst.sum()
        hn = hn[hn > 0]
        entropy = float(-np.sum(hn * np.log2(hn)))

        brightness = float(gray.mean())
        std_bright = float(gray.std())

        color_info = {
            "r": round(mr, 1),
            "g": round(mg, 1),
            "b": round(mb, 1),
            "symmetry": round(sym, 3),
            "entropy": round(entropy, 3),
            "brightness": round(brightness, 1),
            "std": round(std_bright, 1),
            "warm": mr > mb + 15,
            "cool": mb > mr + 15,
        }

        result["color"] = color_info
        result["size"] = orig_size
        result["sobel"] = sobel_analysis(gray / 255.0)
        result["canny"] = canny_analysis(gray_u8)
        result["orb"] = orb_keypoints(gray_u8)
        result["glcm"] = glcm_texture(gray_u8)
        result["fft"] = fft_analysis(gray / 255.0)
        result["kmeans_palette"], result["color_temps"] = kmeans_colors(
            arr.astype(np.uint8), k=7
        )

        rh = np.histogram(r_ch.ravel(), bins=32, range=(0, 255))[0].tolist()
        gh = np.histogram(g_ch.ravel(), bins=32, range=(0, 255))[0].tolist()
        bh = np.histogram(b_ch.ravel(), bins=32, range=(0, 255))[0].tolist()
        result["histograms"] = {"r": rh, "g": gh, "b": bh}

        result["classification"] = classify_scientific_image(
            result["sobel"],
            result["canny"],
            result["glcm"],
            result["orb"],
            result["fft"],
            color_info,
            result["kmeans_palette"],
        )

        if "magnitude" in result["sobel"]:
            mag_norm = result["sobel"]["magnitude"]
            result["sobel_viz"] = (
                mag_norm / (mag_norm.max() + 1e-5) * 255
            ).astype(np.uint8).tolist()
        result["array_shape"] = [new_h, new_w]
        result["ok"] = True
    except Exception as e:
        result["ok"] = False
        result["error"] = str(e)
    return result

def analyze_image_file(fname, img_bytes):
    """Metadados de imagem para armazenar nas pastas (repositório)."""
    try:
        ml = run_full_ml_pipeline(img_bytes)
        if not ml.get("ok"):
            return None
        return {
            "classification": ml.get("classification", {}),
            "color": ml.get("color", {}),
            "fft": ml.get("fft", {}),
            "glcm": ml.get("glcm", {}),
            "orb": {
                "n_keypoints": ml.get("orb", {}).get("n_keypoints", 0),
                "distribution": ml.get("orb", {}).get("distribution", "n/a"),
            },
        }
    except:
        return None

# Funções para análise de documentos (com cache)
@st.cache_data(show_spinner=False)
def extract_pdf(b):
    if PyPDF2 is None:
        return ""
    try:
        r = PyPDF2.PdfReader(io.BytesIO(b))
        t = ""
        for pg in r.pages[:20]:
            try:
                t += pg.extract_text() + "\n"
            except:
                pass
        return t[:40000]
    except:
        return ""

@st.cache_data(show_spinner=False)
def kw_extract(text, n=25):
    if not text:
        return []
    words = re.findall(
        r"\b[a-záàâãéêíóôõúüçA-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]{4,}\b", text.lower()
    )
    words = [w for w in words if w not in STOPWORDS]
    if not words:
        return []
    tf = Counter(words)
    tot = sum(tf.values())
    return [
        w
        for w, _ in sorted(
            {w: c / tot for w, c in tf.items()}.items(),
            key=lambda x: -x[1],
        )[:n]
    ]

def topic_dist(kws):
    tm = {
        "Saúde & Medicina": [
            "saúde",
            "medicina",
            "clínico",
            "health",
            "medical",
            "therapy",
            "disease",
        ],
        "Biologia": [
            "biologia",
            "genômica",
            "gene",
            "dna",
            "rna",
            "proteína",
            "célula",
            "crispr",
        ],
        "Neurociência": [
            "neurociência",
            "neural",
            "cérebro",
            "cognição",
            "memória",
            "sono",
            "brain",
        ],
        "Computação & IA": [
            "algoritmo",
            "machine",
            "learning",
            "inteligência",
            "dados",
            "computação",
            "ia",
            "deep",
            "quantum",
        ],
        "Física": [
            "física",
            "quântica",
            "partícula",
            "energia",
            "galáxia",
            "astrofísica",
            "cosmologia",
        ],
        "Química": [
            "química",
            "molécula",
            "síntese",
            "reação",
            "polímero",
        ],
        "Engenharia": [
            "engenharia",
            "sistema",
            "robótica",
            "automação",
        ],
        "Ciências Sociais": [
            "sociedade",
            "cultura",
            "educação",
            "política",
            "psicologia",
        ],
        "Ecologia": [
            "ecologia",
            "clima",
            "ambiente",
            "biodiversidade",
        ],
        "Matemática": [
            "matemática",
            "estatística",
            "probabilidade",
            "equação",
        ],
    }
    s = defaultdict(int)
    for kw in kws:
        for tp, terms in tm.items():
            if any(t in kw or kw in t for t in terms):
                s[tp] += 1
    return dict(sorted(s.items(), key=lambda x: -x[1])) if s else {
        "Pesquisa Geral": 1
    }

def analyze_quality(text):
    """Heurísticas simples para sugerir melhorias no texto científico."""
    text_l = text.lower()
    hints = []
    if (
        "método" not in text_l
        and "metodologia" not in text_l
        and "methods" not in text_l
    ):
        hints.append(
            "Descrever melhor a metodologia (seção de métodos pouco explícita)."
        )
    if "result" not in text_l and "resultado" not in text_l:
        hints.append(
            "Apresentar resultados de forma mais clara (poucos marcadores de resultado)."
        )
    if "conclus" not in text_l:
        hints.append("Adicionar ou fortalecer a seção de conclusões.")
    if text.count("%") + text.count("p=") < 2:
        hints.append(
            "Pode faltar detalhamento estatístico (poucas menções a testes/valores)."
        )
    return hints

@st.cache_data(show_spinner=False)
def analyze_doc(fname, fbytes, ftype, area=""):
    r = {
        "file": fname,
        "type": ftype,
        "keywords": [],
        "topics": {},
        "relevance_score": 0,
        "summary": "",
        "strengths": [],
        "improvements": [],
        "writing_quality": 0,
        "reading_time": 0,
        "word_count": 0,
    }
    text = ""
    if ftype == "PDF" and fbytes:
        text = extract_pdf(fbytes)
    elif fbytes:
        try:
            text = fbytes.decode("utf-8", errors="ignore")[:40000]
        except:
            pass
    if text:
        r["keywords"] = kw_extract(text, 25)
        r["topics"] = topic_dist(r["keywords"])
        words = len(text.split())
        r["word_count"] = words
        r["reading_time"] = max(1, round(words / 200))
        r["writing_quality"] = min(
            100,
            50
            + (15 if len(r["keywords"]) > 15 else 0)
            + (15 if words > 1000 else 0)
            + (10 if r["reading_time"] > 3 else 0),
        )
        if area:
            aw = area.lower().split()
            rel = sum(
                1 for w in aw if any(w in kw for kw in r["keywords"])
            )
            r["relevance_score"] = min(100, rel * 15 + 45)
        else:
            r["relevance_score"] = 65
        base_strengths = []
        if len(r["keywords"]) > 15:
            base_strengths.append(
                f"Vocabulário rico ({len(r['keywords'])} termos relevantes)."
            )
        if words > 1500:
            base_strengths.append(
                "Texto extenso, possivelmente cobrindo introdução, métodos e discussão."
            )
        r["strengths"] = base_strengths
        r["improvements"] = analyze_quality(text)
        r["summary"] = (
            f"{ftype} · {words} palavras · ~{r['reading_time']}min · "
            f"{', '.join(list(r['topics'].keys())[:2])} · "
            f"{', '.join(r['keywords'][:4])}"
        )
    else:
        r["summary"] = f"Arquivo {ftype}."
        r["relevance_score"] = 50
        r["keywords"] = kw_extract(fname.lower(), 5)
        r["topics"] = topic_dist(r["keywords"])
    return r

# Funções de busca acadêmica (com cache)
@st.cache_data(show_spinner=False, ttl=1800)
def search_ss(q, lim=6):
    try:
        r = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={
                "query": q,
                "limit": lim,
                "fields": "title,authors,year,abstract,venue,externalIds,openAccessPdf,citationCount",
            },
            timeout=8,
        )
        if r.status_code == 200:
            out = []
            for p in r.json().get("data", []):
                ext = p.get("externalIds", {}) or {}
                doi = ext.get("DOI", "")
                arx = ext.get("ArXiv", "")
                pdf = p.get("openAccessPdf") or {}
                link = pdf.get("url", "") or (
                    f"https://arxiv.org/abs/{arx}"
                    if arx
                    else (f"https://doi.org/{doi}" if doi else "")
                )
                al = p.get("authors", []) or []
                au = ", ".join(a.get("name", "") for a in al[:3])
                if len(al) > 3:
                    au += " et al."
                out.append(
                    {
                        "title": p.get("title", "Sem título"),
                        "authors": au or "—",
                        "year": p.get("year", "?"),
                        "source": p.get("venue", "") or "Semantic Scholar",
                        "doi": doi or arx or "—",
                        "abstract": (p.get("abstract", "") or "")[:250],
                        "url": link,
                        "citations": p.get("citationCount", 0),
                        "origin": "semantic",
                    }
                )
            return out
    except:
        pass
    return []

@st.cache_data(show_spinner=False, ttl=1800)
def search_cr(q, lim=3):
    try:
        r = requests.get(
            "https://api.crossref.org/works",
            params={
                "query": q,
                "rows": lim,
                "select": "title,author,issued,abstract,DOI,container-title,is-referenced-by-count",
                "mailto": "nebula@example.com",
            },
            timeout=8,
        )
        if r.status_code == 200:
            out = []
            for p in (
                r.json()
                .get("message", {})
                .get("items", [])
            ):
                title = (p.get("title") or ["?"])[0]
                ars = p.get("author", []) or []
                au = ", ".join(
                    f"{a.get('given', '').split()[0] if a.get('given') else ''} {a.get('family', '')}".strip()
                    for a in ars[:3]
                )
                if len(ars) > 3:
                    au += " et al."
                yr = (
                    p.get("issued", {})
                    .get("date-parts")
                    or [[None]]
                )[0][0]
                doi = p.get("DOI", "")
                ab = re.sub(
                    r"<[^>]+>",
                    "",
                    p.get("abstract", "") or "",
                )[:250]
                out.append(
                    {
                        "title": title,
                        "authors": au or "—",
                        "year": yr or "?",
                        "source": (p.get("container-title") or ["CrossRef"])[
                            0
                        ],
                        "doi": doi,
                        "abstract": ab,
                        "url": f"https://doi.org/{doi}" if doi else "",
                        "citations": p.get(
                            "is-referenced-by-count", 0
                        ),
                        "origin": "crossref",
                    }
                )
            return out
    except:
        pass
    return []

def record(tags, w=1.0):
    e = st.session_state.get("current_user")
    if not e or not tags:
        return
    p = st.session_state.user_prefs.setdefault(
        e, defaultdict(float)
    )
    for t in tags:
        p[t.lower()] += w
    save_db()

def get_recs(email, n=2):
    pr = st.session_state.user_prefs.get(email, {})
    if not pr:
        return []

    def sc(p):
        return sum(
            pr.get(t.lower(), 0)
            for t in p.get("tags", []) + p.get("connections", [])
        )

    scored = [
        (sc(p), p)
        for p in st.session_state.feed_posts
        if email not in p.get("liked_by", [])
    ]
    return [
        p for s, p in sorted(scored, key=lambda x: -x[0]) if s > 0
    ][:n]

def area_tags(area):
    a = (area or "").lower()
    M = {
        "ia": ["machine learning", "LLM"],
        "inteligência artificial": ["machine learning", "LLM"],
        "neurociência": ["sono", "memória", "cognição"],
        "biologia": ["célula", "genômica"],
        "física": ["quantum", "astrofísica"],
        "medicina": ["diagnóstico", "terapia"],
    }
    for k, v in M.items():
        if k in a:
            return v
    return [
        w.strip()
        for w in a.replace(",", " ").split()
        if len(w) > 3
    ][:5]

EMAP = {
    "pdf": "PDF",
    "docx": "Word",
    "xlsx": "Planilha",
    "csv": "Dados",
    "txt": "Texto",
    "py": "Código",
    "md": "Markdown",
    "png": "Imagem",
    "jpg": "Imagem",
    "jpeg": "Imagem",
    "webp": "Imagem",
    "tiff": "Imagem",
}

def ftype(fname):
    return EMAP.get(
        fname.split(".")[-1].lower() if "." in fname else "", "Arquivo"
    )

VIB = [
    "#0A1929",
    "#1A2F4A",
    "#1D3A5A",
    "#20456A",
    "#23507A",
    "#265B8A",
    "#29669A",
    "#2C71AA",
    "#2F7CBA",
    "#3287CA",
]

# ================================================
#  INDEX LOCAL E VETORES DE INTERESSE
# ================================================
@st.cache_data(show_spinner=False, ttl=600)
def build_local_index(users, feed_posts, folders, version):
    """Índice unificado: posts + docs de pastas (repositório)."""
    docs = []

    for p in feed_posts:
        text = (
            (p.get("title", "") or "")
            + " "
            + (p.get("abstract", "") or "")
        ).lower()
        tags = [t.lower() for t in p.get("tags", [])]
        docs.append(
            {
                "type": "post",
                "id": f"post_{p['id']}",
                "title": p.get("title", "Sem título"),
                "authors": p.get("author", ""),
                "year": p.get("date", "")[:4],
                "source": "Nebula Feed",
                "text": text,
                "tags": tags,
                "meta": p,
            }
        )

    for fname, folder in folders.items():
        if not isinstance(folder, dict):
            continue
        owner = folder.get("owner")
        owner_name = users.get(owner, {}).get("name", "") if owner else ""
        for f, an in folder.get("analyses", {}).items():
            text = " ".join(
                [
                    an.get("summary", ""),
                    " ".join(an.get("keywords", [])),
                    " ".join(list(an.get("topics", {}).keys())),
                ]
            ).lower()
            docs.append(
                {
                    "type": "folder_doc",
                    "id": f"folder_{fname}_{f}",
                    "title": f"{f} ({fname})",
                    "authors": owner_name,
                    "year": "",
                    "source": f"Pasta: {fname}",
                    "text": text,
                    "tags": an.get("keywords", []),
                    "meta": {
                        "folder": fname,
                        "file": f,
                        "analysis": an,
                        "owner": owner,
                    },
                }
            )

    return docs

def search_local(q, docs, topk=20):
    """Busca simples baseada em palavras-chave / tags no índice local."""
    if not q.strip():
        return []
    q_words = kw_extract(q, 15)
    results = []
    for d in docs:
        score = 0
        text = d["text"]
        for w in q_words:
            if w in text:
                score += 3
        for t in d.get("tags", []):
            if any(w in t.lower() for w in q_words):
                score += 2
        if score > 0:
            results.append((score, d))
    results.sort(key=lambda x: -x[0])
    return [d for s, d in results[:topk]]

def recompute_folder_aggregates(folder):
    topics_sum = defaultdict(int)
    kw_counter = Counter()
    for an in folder.get("analyses", {}).values():
        for t, s in an.get("topics", {}).items():
            topics_sum[t] += s
        for kw in an.get("keywords", []):
            kw_counter[kw] += 1
    folder["topics_agg"] = dict(
        sorted(topics_sum.items(), key=lambda x: -x[1])[:12]
    )
    folder["keywords_agg"] = [
        kw for kw, _ in kw_counter.most_common(30)
    ]
    folder["last_updated"] = datetime.now().isoformat()

def build_user_interest_vectors(users, feed_posts, folders):
    vocab = Counter()
    per_user = defaultdict(Counter)

    for p in feed_posts:
        ue = p.get("author_email")
        if not ue:
            continue
        kws = kw_extract(
            (p.get("title", "") or "")
            + " "
            + (p.get("abstract", "") or ""),
            15,
        )
        for k in kws + p.get("tags", []):
            k = k.lower()
            vocab[k] += 1
            per_user[ue][k] += 2

    for fname, fd in folders.items():
        if not isinstance(fd, dict):
            continue
        owner = fd.get("owner")
        if not owner:
            continue
        for kw in fd.get("keywords_agg", []):
            vocab[kw] += 1
            per_user[owner][kw] += 1

    vectors = {}
    for ue, ctr in per_user.items():
        total = sum(ctr.values()) or 1
        vectors[ue] = {k: v / total for k, v in ctr.items()}
    return vectors

def user_similarity(u_vecs, u1, u2):
    v1 = u_vecs.get(u1, {})
    v2 = u_vecs.get(u2, {})
    if not v1 or not v2:
        return 0.0
    common = set(v1) & set(v2)
    if not common:
        return 0.0
    num = sum(v1[k] * v2[k] for k in common)
    d1 = sum(v * v for v in v1.values()) ** 0.5
    d2 = sum(v * v for v in v2.values()) ** 0.5
    if d1 * d2 == 0:
        return 0.0
    return num / (d1 * d2)

def find_similar_images(ml_result, folders):
    target_cat = ml_result.get("classification", {}).get(
        "category", ""
    )
    target_color = ml_result.get("color", {})
    results = []

    for fname, fd in folders.items():
        if not isinstance(fd, dict):
            continue
        for f, an in fd.get("analyses", {}).items():
            im = an.get("image_meta")
            if not im:
                continue
            score = 0
            if im.get("classification", {}).get("category") == target_cat:
                score += 40
            col = im.get("color", {})
            if col and target_color:
                dr = abs(col.get("r", 0) - target_color.get("r", 0))
                dg = abs(col.get("g", 0) - target_color.get("g", 0))
                db = abs(col.get("b", 0) - target_color.get("b", 0))
                color_score = max(0, 30 - (dr + dg + db) / 10)
                score += color_score
            if score > 0:
                results.append((score, fname, f, an))
    results.sort(key=lambda x: -x[0])
    return results[:6]

# ================================================
#  CSS (Azul Escuro "Liquid Glass")
# ================================================
def inject_css():
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800;900&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
  --bg:#050712; --bg2:#0B0F1A; --bg3:#121724;
  --yel:#0A6EBD; --yel2:#1F5E9E;
  --grn:#6A9C89; --grn2:#7D9D8A;
  --red:#FF3B5C; --red2:#FF6B81;
  --blu:#4CC9F0; --blu2:#7BD3FF;
  --pur:#B17DFF; --orn:#FF8C42;
  --t0:#FFFFFF; --t1:#E8E9F0; --t2:#A8ABBE; --t3:#6B6F88; --t4:#404460;
  --g1:rgba(255,255,255,.06); --g2:rgba(255,255,255,.09); --g3:rgba(255,255,255,.13);
  --gb1:rgba(255,255,255,.08); --gb2:rgba(255,255,255,.14); --gb3:rgba(255,255,255,.22);
  --r8:8px; --r12:12px; --r16:16px; --r20:20px; --r28:28px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body,.stApp{background:var(--bg)!important;color:var(--t1)!important;font-family:'DM Sans',-apple-system,sans-serif!important;}
.stApp::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;background:
  radial-gradient(ellipse 60% 50% at -5% 0%,rgba(10,110,189,.09) 0%,transparent 60%),
  radial-gradient(ellipse 50% 40% at 105% 0%,rgba(76,201,240,.09) 0%,transparent 55%),
  radial-gradient(ellipse 40% 50% at 50% 110%,rgba(106,156,137,.07) 0%,transparent 60%);
}
.stApp::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:linear-gradient(rgba(255,255,255,.018) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(255,255,255,.018) 1px,transparent 1px);
  background-size:60px 60px;
}
header[data-testid="stHeader"],#MainMenu,footer,.stDeployButton,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
[data-testid="stSidebarCollapseButton"]{display:none!important}
section[data-testid="stSidebar"]{
  display:block!important;
  transform:translateX(0)!important;
  visibility:visible!important;
  background:linear-gradient(180deg, rgba(8,13,26,0.97), rgba(7,10,20,0.98))!important;
  border-right:1px solid rgba(255,255,255,.18)!important;
  width:230px!important;min-width:230px!important;max-width:230px!important;
  padding:1.2rem .9rem 1.2rem!important;
  backdrop-filter: blur(22px) saturate(135%)!important;
  box-shadow: 4px 0 32px rgba(0,0,0,.75)!important;
}
section[data-testid="stSidebar"]>div{width:230px!important;padding:0!important;}
[data-testid="collapsedControl"]{display:none!important}
.block-container{padding-top:.3rem!important;padding-bottom:4rem!important;max-width:1380px!important;position:relative;z-index:1;padding-left:.8rem!important;padding-right:.8rem!important;}
.stButton>button{
  background:radial-gradient(circle at 0% 0%, rgba(255,255,255,.18), rgba(255,255,255,.05))!important;
  border:1px solid rgba(255,255,255,.22)!important;
  border-radius:10px!important;
  color:#D0D2E0!important;
  -webkit-text-fill-color:#D0D2E0!important;
  font-family:'DM Sans',sans-serif!important;
  font-weight:500!important;font-size:.83rem!important;
  padding:.46rem .8rem!important;
  transition:background .12s, transform .06s!important;
  box-shadow:0 0 0 1px rgba(255,255,255,.04) inset, 0 10px 28px rgba(0,0,0,.55)!important;
  line-height:1.4!important;
}
.stButton>button:hover{
  background:radial-gradient(circle at 0% 0%, rgba(255,255,255,.25), rgba(255,255,255,.10))!important;
  color:#FFFFFF!important;-webkit-text-fill-color:#FFFFFF!important;
}
.stButton>button:active{transform:scale(.97)!important;}
.stButton>button p,.stButton>button span{color:inherit!important;-webkit-text-fill-color:inherit!important;}
section[data-testid="stSidebar"] .stButton>button{
  text-align:left!important;
  justify-content:flex-start!important;
  width:100%!important;
  margin-bottom:.18rem!important;
  padding:.5rem .9rem!important;
  font-size:.85rem!important;
}
.sb-logo{display:flex;align-items:center;gap:9px;margin-bottom:1.5rem;padding:.2rem .3rem;}
.sb-logo-icon{width:34px;height:34px;border-radius:12px;background:radial-gradient(circle at 0% 0%,rgba(76,201,240,.95),rgba(10,110,189,.9));display:flex;align-items:center;justify-content:center;font-size:.9rem;flex-shrink:0;box-shadow:0 0 24px rgba(76,201,240,.5);}
.sb-logo-txt{font-family:'Syne',sans-serif;font-weight:900;font-size:1.3rem;letter-spacing:-.06em;background:linear-gradient(135deg,#4CC9F0,#6A9C89);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.sb-lbl{font-size:.54rem;font-weight:700;color:#6B6F88;letter-spacing:.16em;text-transform:uppercase;padding:0 .2rem;margin-bottom:.35rem;margin-top:.8rem;}
.stTextInput input,.stTextArea textarea{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;color:var(--t1)!important;font-family:'DM Sans',sans-serif!important;font-size:.84rem!important;}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:rgba(10,110,189,.4)!important;box-shadow:0 0 0 3px rgba(10,110,189,.12)!important;}
.stTextInput label,.stTextArea label,.stSelectbox label,.stFileUploader label,.stNumberInput label{color:var(--t3)!important;font-size:.60rem!important;letter-spacing:.10em!important;text-transform:uppercase!important;font-weight:600!important;}
.glass{background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.10);border-radius:var(--r20);box-shadow:0 0 0 1px rgba(255,255,255,.04) inset,0 4px 32px rgba(0,0,0,.3);position:relative;overflow:hidden;}
.glass::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.12),transparent);pointer-events:none;}
.post-card{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.09);border-radius:var(--r20);margin-bottom:.65rem;overflow:hidden;box-shadow:0 2px 20px rgba(0,0,0,.25);transition:border-color .14s,transform .14s;}
.post-card:hover{border-color:rgba(255,255,255,.15);transform:translateY(-1px);}
.sc{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.09);border-radius:var(--r20);padding:.9rem 1rem;margin-bottom:.6rem;}
.scard{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:var(--r16);padding:.8rem 1rem;margin-bottom:.42rem;transition:border-color .13s,transform .13s;}
.scard:hover{border-color:rgba(255,255,255,.14);transform:translateY(-1px);}
.mbox{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.09);border-radius:var(--r16);padding:.9rem;text-align:center;}
.abox{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.10);border-radius:var(--r16);padding:1rem;margin-bottom:.6rem;}
.pbox-grn{background:rgba(106,156,137,.07);border:1px solid rgba(106,156,137,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.55rem;}
.pbox-yel{background:rgba(10,110,189,.07);border:1px solid rgba(10,110,189,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.55rem;}
.pbox-blu{background:rgba(76,201,240,.07);border:1px solid rgba(76,201,240,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.55rem;}
.pbox-pur{background:rgba(177,125,255,.07);border:1px solid rgba(177,125,255,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.55rem;}
.chart-wrap{background:rgba(5,7,18,.9);border:1px solid rgba(255,255,255,.09);border-radius:var(--r12);padding:.65rem;margin-bottom:.6rem;}
.compose-box{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.11);border-radius:var(--r20);padding:1.1rem 1.3rem;margin-bottom:.8rem;}
.mval-yel{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;background:linear-gradient(135deg,var(--yel),var(--orn));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-grn{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;background:linear-gradient(135deg,var(--grn),var(--blu));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-blu{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;background:linear-gradient(135deg,var(--blu),var(--pur));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-red{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;background:linear-gradient(135deg,var(--red),var(--orn));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mlbl{font-size:.58rem;color:var(--t3);margin-top:4px;letter-spacing:.1em;text-transform:uppercase;font-weight:700;}
.tag{display:inline-block;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.09);border-radius:50px;padding:2px 9px;font-size:.63rem;color:var(--t2);margin:2px;font-weight:500;}
.badge-yel{display:inline-block;background:rgba(10,110,189,.12);border:1px solid rgba(10,110,189,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--yel);}
.badge-grn{display:inline-block;background:rgba(106,156,137,.12);border:1px solid rgba(106,156,137,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--grn);}
.badge-red{display:inline-block;background:rgba(255,59,92,.12);border:1px solid rgba(255,59,92,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--red);}
.badge-blu{display:inline-block;background:rgba(76,201,240,.12);border:1px solid rgba(76,201,240,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--blu);}
.badge-pur{display:inline-block;background:rgba(177,125,255,.12);border:1px solid rgba(177,125,255,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--pur);}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.45;transform:scale(.7)}}
.dot-on{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--grn);animation:pulse 2.5s infinite;margin-right:4px;vertical-align:middle;}
.dot-off{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--t4);margin-right:4px;vertical-align:middle;}
@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.pw{animation:fadeUp .18s ease both;}
.bme{background:linear-gradient(135deg,rgba(10,110,189,.18),rgba(76,201,240,.08));border:1px solid rgba(10,110,189,.35);border-radius:18px 18px 4px 18px;padding:.55rem .88rem;max-width:70%;margin-left:auto;margin-bottom:5px;font-size:.82rem;line-height:1.6;}
.bthem{background:var(--g2);border:1px solid var(--gb1);border-radius:18px 18px 18px 4px;padding:.55rem .88rem;max-width:70%;margin-bottom:5px;font-size:.82rem;line-height:1.6;}
.cmt{background:rgba(255,255,255,.03);border:1px solid var(--gb1);border-radius:var(--r12);padding:.5rem .85rem;margin-bottom:.25rem;}
.stTabs [data-baseweb="tab-list"]{background:rgba(255,255,255,.03)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;padding:3px!important;gap:2px!important;}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--t3)!important;border-radius:9px!important;font-size:.75rem!important;font-family:'DM Sans',sans-serif!important;font-weight:500!important;}
.stTabs [aria-selected="true"]{background:var(--g3)!important;color:var(--yel)!important;border:1px solid rgba(10,110,189,.3)!important;font-weight:700!important;}
.stTabs [data-baseweb="tab-panel"]{background:transparent!important;padding-top:.8rem!important;}
.prof-hero{background:var(--g1);backdrop-filter:blur(32px);border:1px solid var(--gb1);border-radius:var(--r28);padding:1.6rem;display:flex;gap:1.2rem;align-items:flex-start;box-shadow:0 6px 40px rgba(0,0,0,.35);margin-bottom:1rem;}
.prof-av{width:76px;height:76px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:'Syne',sans-serif;font-weight:800;font-size:1.6rem;color:white;flex-shrink:0;border:2px solid rgba(255,255,255,.12);}
hr{border:none;border-top:1px solid var(--gb1)!important;margin:.8rem 0;}
.stAlert{background:var(--g1)!important;border:1px solid var(--gb1)!important;border-radius:var(--r16)!important;}
.stSelectbox [data-baseweb="select"]{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;}
.stFileUploader section{background:rgba(255,255,255,.03)!important;border:1.5px dashed var(--gb2)!important;border-radius:var(--r16)!important;}
.stExpander{background:var(--g1);border:1px solid var(--gb1);border-radius:var(--r16);}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-thumb{background:var(--t4);border-radius:4px;}
.js-plotly-plot .plotly .modebar{display:none!important;}
.dtxt{display:flex;align-items:center;gap:.7rem;margin:.75rem 0;font-size:.58rem;color:var(--t3);letter-spacing:.10em;text-transform:uppercase;font-weight:700;}
.dtxt::before,.dtxt::after{content:'';flex:1;height:1px;background:var(--gb1);}
h1{font-family:'Syne',sans-serif!important;font-size:1.55rem!important;font-weight:800!important;letter-spacing:-.03em;color:var(--t0)!important;}
h2{font-family:'Syne',sans-serif!important;font-size:1rem!important;font-weight:700!important;color:var(--t0)!important;}
label{color:var(--t2)!important;}
.stCheckbox label,.stRadio label{color:var(--t1)!important;}
.stRadio>div{display:flex!important;gap:4px!important;flex-wrap:wrap!important;}
.stRadio>div>label{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:50px!important;padding:.28rem .78rem!important;font-size:.74rem!important;cursor:pointer!important;color:var(--t2)!important;}
input[type="number"]{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;color:var(--t1)!important;}
.ai-card{background:linear-gradient(135deg,rgba(10,110,189,.10),rgba(106,156,137,.06));border:1px solid rgba(10,110,189,.25);border-radius:var(--r16);padding:1rem;margin-bottom:.6rem;}
.ml-feat{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:var(--r12);padding:.65rem .85rem;margin-bottom:.38rem;}
.api-banner{background:linear-gradient(135deg,rgba(177,125,255,.08),rgba(76,201,240,.06));border:1px solid rgba(177,125,255,.22);border-radius:var(--r16);padding:.9rem 1.1rem;margin-bottom:.8rem;}
.conn-ai{background:linear-gradient(135deg,rgba(106,156,137,.08),rgba(76,201,240,.05));border:1px solid rgba(106,156,137,.22);border-radius:var(--r16);padding:1rem;margin-bottom:.6rem;}
</style>
""",
        unsafe_allow_html=True,
    )

# Helpers HTML
_COLORS = {
    "yel": ("#0A6EBD", "rgba(10,110,189,.14)", "rgba(10,110,189,.4)"),
    "grn": ("#6A9C89", "rgba(106,156,137,.14)", "rgba(106,156,137,.4)"),
    "blu": ("#4CC9F0", "rgba(76,201,240,.12)", "rgba(76,201,240,.35)"),
    "red": ("#FF3B5C", "rgba(255,59,92,.12)", "rgba(255,59,92,.35)"),
    "pur": ("#B17DFF", "rgba(177,125,255,.12)", "rgba(177,125,255,.35)"),
    "orn": ("#FF8C42", "rgba(255,140,66,.12)", "rgba(255,140,66,.35)"),
    "t1": ("#E8E9F0", "rgba(255,255,255,.08)", "rgba(255,255,255,.18)"),
    "t2": ("#A8ABBE", "rgba(255,255,255,.05)", "rgba(255,255,255,.12)"),
}

def avh(initials, sz=40, grad=None):
    fs = max(sz // 3, 9)
    bg = grad or "linear-gradient(135deg,#0A6EBD,#6A9C89)"
    return f'<div style="width:{sz}px;height:{sz}px;border-radius:50%;background:{bg};display:flex;align-items:center;justify-content:center;font-family:Syne,sans-serif;font-weight:800;font-size:{fs}px;color:white;flex-shrink:0;border:1.5px solid rgba(255,255,255,.12)">{initials}</div>'

def tags_html(tags):
    return " ".join(
        f'<span class="tag">{t}</span>' for t in (tags or [])
    )

def badge(s):
    m = {"Publicado": "badge-grn", "Concluído": "badge-pur"}
    return f'<span class="{m.get(s, "badge-yel")}">{s}</span>'

def pc_dark():
    return dict(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#6B6F88", family="DM Sans", size=11),
        margin=dict(l=10, r=10, t=38, b=10),
        xaxis=dict(showgrid=False, color="#6B6F88", tickfont=dict(size=10)),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,.04)",
            color="#6B6F88",
            tickfont=dict(size=10),
        ),
    )

# ================================================
#  PÁGINAS
# ================================================
def page_login():
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            """<div style="text-align:center;margin-bottom:2.8rem">
  <div style="display:flex;align-items:center;justify-content:center;gap:12px;margin-bottom:.8rem">
    <div style="width:48px;height:48px;border-radius:14px;background:linear-gradient(135deg,#4CC9F0,#0A6EBD);display:flex;align-items:center;justify-content:center;font-size:1.4rem;box-shadow:0 0 24px rgba(76,201,240,.45)">🔬</div>
    <div style="font-family:Syne,sans-serif;font-size:2.6rem;font-weight:900;letter-spacing:-.06em;background:linear-gradient(135deg,#4CC9F0,#6A9C89);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">Nebula</div>
  </div>
  <div style="color:var(--t3);font-size:.60rem;letter-spacing:.26em;text-transform:uppercase;font-weight:700">Repositório de Conhecimento Científico</div>
</div>""",
            unsafe_allow_html=True,
        )
        ti, tu = st.tabs(["  🔑 Entrar  ", "  ✨ Criar conta  "])
        with ti:
            with st.form("lf"):
                em = st.text_input(
                    "E-mail", placeholder="seu@email.com", key="li_e"
                )
                pw = st.text_input(
                    "Senha", placeholder="••••••••", type="password", key="li_p"
                )
                s = st.form_submit_button("→  Entrar", use_container_width=True)
                if s:
                    u = st.session_state.users.get(em)
                    if not u:
                        st.error("E-mail não encontrado.")
                    elif u["password"] != hp(pw):
                        st.error("Senha incorreta.")
                    else:
                        st.session_state.logged_in = True
                        st.session_state.current_user = em
                        record(area_tags(u.get("area", "")), 1.0)
                        st.session_state.page = "repository"
                        st.rerun()
            st.markdown(
                '<div style="text-align:center;color:var(--t3);font-size:.68rem;margin-top:.7rem">Demo: demo@nebula.ai / demo123</div>',
                unsafe_allow_html=True,
            )
        with tu:
            with st.form("sf"):
                nn = st.text_input("Nome completo", key="su_n")
                ne = st.text_input("E-mail", key="su_e")
                na = st.text_input("Área de pesquisa", key="su_a")
                np_ = st.text_input(
                    "Senha", type="password", key="su_p"
                )
                np2 = st.text_input(
                    "Confirmar", type="password", key="su_p2"
                )
                s2 = st.form_submit_button(
                    "✓  Criar conta", use_container_width=True
                )
                if s2:
                    if not all([nn, ne, na, np_, np2]):
                        st.error("Preencha todos os campos.")
                    elif np_ != np2:
                        st.error("Senhas não coincidem.")
                    elif ne in st.session_state.users:
                        st.error("E-mail já cadastrado.")
                    else:
                        st.session_state.users[ne] = {
                            "name": nn,
                            "password": hp(np_),
                            "bio": "",
                            "area": na,
                            "followers": 0,
                            "following": 0,
                            "verified": True,
                            "2fa_enabled": False,
                        }
                        save_db()
                        st.session_state.logged_in = True
                        st.session_state.current_user = ne
                        record(area_tags(na), 2.0)
                        st.session_state.page = "repository"
                        st.rerun()

# Navegação
NAV = [
    ("repository", "📚 Repositório", "yel"),
    ("search", "🔍 Busca", "blu"),
    ("knowledge", "🕸 Conexões IA", "grn"),
    ("feed", "🏠 Feed Social", "orn"),
    ("analytics", "📊 Análises", "pur"),
    ("img_search", "🔬 Visão IA", "blu"),
    ("chat", "💬 Chat", "grn"),
    ("settings", "⚙️ Config", "red"),
]

def render_nav():
    email = st.session_state.current_user
    u = guser()
    name = u.get("name", "?")
    ini_ = ini(name)
    g = ugrad(email)
    cur = st.session_state.page

    with st.sidebar:
        st.markdown(
            '<div class="sb-logo"><div class="sb-logo-icon">🔬</div><div class="sb-logo-txt">Nebula</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="sb-lbl">Navegação</div>',
            unsafe_allow_html=True,
        )

        active_styles = ""
        for i, (key, label, col) in enumerate(NAV):
            is_a = (cur == key and not st.session_state.profile_view)
            if is_a:
                colors = {
                    "yel": "#0A6EBD",
                    "grn": "#6A9C89",
                    "blu": "#4CC9F0",
                    "red": "#FF3B5C",
                    "pur": "#B17DFF",
                    "orn": "#FF8C42",
                }
                c = colors.get(col, "#0A6EBD")
                active_styles += (
                    f'section[data-testid="stSidebar"] [data-testid="stVerticalBlock"]'
                    f' > [data-testid="stVerticalBlock"]:nth-child({i + 2})'
                    f' .stButton>button{{'
                    f"color:{c}!important;-webkit-text-fill-color:{c}!important;"
                    f"background:radial-gradient(circle at 0% 0%, rgba(255,255,255,.28), rgba(255,255,255,.12))!important;"
                    f"border-color:{c}60!important;"
                    f"font-weight:700!important;}}"
                )
        if active_styles:
            st.markdown(
                f"<style>{active_styles}</style>",
                unsafe_allow_html=True,
            )

        for key, label, col in NAV:
            if st.button(label, key=f"sb_{key}", use_container_width=True):
                st.session_state.profile_view = None
                st.session_state.page = key
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(
            '<div class="sb-lbl">API Key</div>', unsafe_allow_html=True
        )
        ak = st.text_input(
            "",
            placeholder="sk-ant-...",
            type="password",
            key="sb_apikey",
            label_visibility="collapsed",
            value=st.session_state.anthropic_key,
        )
        if ak != st.session_state.anthropic_key:
            st.session_state.anthropic_key = ak
        if ak and ak.startswith("sk-"):
            st.markdown(
                '<div style="font-size:.55rem;color:#6A9C89;padding:.1rem .2rem">● Claude Vision ativo</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="font-size:.55rem;color:#555770;padding:.1rem .2rem">● Insira chave para IA</div>',
                unsafe_allow_html=True,
            )
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;padding:.2rem .1rem">{avh(ini_, 32, g)}<div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.78rem;color:#FFF;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:120px">{name}</div><div style="font-size:.58rem;color:#6B6F88">{u.get("area", "")[:18]}</div></div></div>',
            unsafe_allow_html=True,
        )
        if st.button(
            "👤 Meu Perfil", key="sb_myprofile", use_container_width=True
        ):
            st.session_state.profile_view = email
            st.session_state.page = "repository"
            st.rerun()

def page_profile(target_email):
    tu = st.session_state.users.get(target_email, {})
    email = st.session_state.current_user
    if not tu:
        st.error("Perfil não encontrado.")
        return
    tname = tu.get("name", "?")
    ti = ini(tname)
    is_me = (email == target_email)
    is_fol = target_email in st.session_state.followed
    g = ugrad(target_email)
    user_posts = [
        p
        for p in st.session_state.feed_posts
        if p.get("author_email") == target_email
    ]
    liked_posts = [
        p
        for p in st.session_state.feed_posts
        if target_email in p.get("liked_by", [])
    ]
    total_likes = sum(p["likes"] for p in user_posts)
    vb = f' <span class="badge-grn" style="font-size:.6rem">✓</span>' if tu.get("verified") else ""
    st.markdown(
        f"""<div class="prof-hero">
  <div class="prof-av" style="background:{g}">{ti}</div>
  <div style="flex:1">
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:.22rem">
      <span style="font-family:Syne,sans-serif;font-weight:800;font-size:1.35rem;color:var(--t0)">{tname}</span>{vb}
    </div>
    <div style="color:var(--yel);font-size:.80rem;font-weight:600;margin-bottom:.38rem">{tu.get("area", "")}</div>
    <div style="color:var(--t2);font-size:.78rem;line-height:1.7;margin-bottom:.75rem">{tu.get("bio", "Sem biografia.")}</div>
    <div style="display:flex;gap:1.6rem;flex-wrap:wrap">
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1rem;color:var(--t0)">{tu.get("followers", 0)}</span><span style="color:var(--t3);font-size:.68rem"> seguidores</span></div>
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1rem;color:var(--t0)">{tu.get("following", 0)}</span><span style="color:var(--t3);font-size:.68rem"> seguindo</span></div>
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1rem;color:var(--t0)">{len(user_posts)}</span><span style="color:var(--t3);font-size:.68rem"> pesquisas</span></div>
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1rem;color:var(--yel)">{fmt_num(total_likes)}</span><span style="color:var(--t3);font-size:.68rem"> curtidas</span></div>
    </div>
  </div>
</div>""",
        unsafe_allow_html=True,
    )
    if not is_me:
        c1, c2, c3, _ = st.columns([1, 1, 1, 2])
        with c1:
            st.markdown('<div>', unsafe_allow_html=True)
            if st.button(
                "✓ Seguindo" if is_fol else "+ Seguir",
                key="su_n",
                use_container_width=True,
            ):
                if is_fol:
                    st.session_state.followed.remove(target_email)
                    tu["followers"] = max(
                        0, tu.get("followers", 0) - 1
                    )
                else:
                    st.session_state.followed.append(target_email)
                    tu["followers"] = tu.get("followers", 0) + 1
                save_db()
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        with c2:
            if st.button(
                "💬 Mensagem",
                key="pf_chat",
                use_container_width=True,
            ):
                st.session_state.chat_messages.setdefault(
                    target_email, []
                )
                st.session_state.active_chat = target_email
                st.session_state.page = "chat"
                st.rerun()
        with c3:
            if st.button(
                "← Voltar", key="pf_back", use_container_width=True
            ):
                st.session_state.profile_view = None
                st.rerun()
        tp, tl = st.tabs(
            [
                f"  📝 Pesquisas ({len(user_posts)})  ",
                f"  ❤️ Curtidas ({len(liked_posts)})  ",
            ]
        )
        with tp:
            for p in sorted(
                user_posts,
                key=lambda x: x.get("date", ""),
                reverse=True,
            ):
                render_post(p, ctx="profile", show_author=False)
            if not user_posts:
                st.markdown(
                    '<div class="glass" style="padding:2rem;text-align:center;color:var(--t3)">Nenhuma pesquisa publicada.</div>',
                    unsafe_allow_html=True,
                )
        with tl:
            for p in sorted(
                liked_posts,
                key=lambda x: x.get("date", ""),
                reverse=True,
            ):
                render_post(p, ctx="prof_liked", compact=True)
            if not liked_posts:
                st.markdown(
                    '<div class="glass" style="padding:2rem;text-align:center;color:var(--t3)">Nenhuma curtida.</div>',
                    unsafe_allow_html=True,
                )
    else:
        saved_arts = st.session_state.saved_articles
        tm, tl, ts2, ts = st.tabs(
            [
                "  ✏️ Meus Dados  ",
                f"  📝 Publicações ({len(user_posts)})  ",
                f"  ❤️ Curtidas ({len(liked_posts)})  ",
                f"  🔖 Salvos ({len(saved_arts)})  ",
            ]
        )
        with tm:
            new_n = st.text_input(
                "Nome", value=tu.get("name", ""), key="cfg_n"
            )
            new_a = st.text_input(
                "Área", value=tu.get("area", ""), key="cfg_a"
            )
            new_b = st.text_area(
                "Bio", value=tu.get("bio", ""), key="cfg_b", height=80
            )
            cs, co = st.columns(2)
            with cs:
                if st.button(
                    "💾 Salvar", key="btn_sp", use_container_width=True
                ):
                    st.session_state.users[email].update(
                        {"name": new_n, "area": new_a, "bio": new_b}
                    )
                    save_db()
                    st.success("✓ Salvo!")
                    st.rerun()
            with co:
                if st.button(
                    "🚪 Sair", key="btn_out", use_container_width=True
                ):
                    st.session_state.logged_in = False
                    st.session_state.current_user = None
                    st.session_state.page = "login"
                    st.rerun()
        with tl:
            if user_posts:
                for p in sorted(
                    user_posts,
                    key=lambda x: x.get("date", ""),
                    reverse=True,
                ):
                    render_post(p, ctx="myp", show_author=False)
            else:
                st.markdown(
                    '<div class="glass" style="padding:2.5rem;text-align:center;color:var(--t3)">Nenhuma pesquisa ainda.</div>',
                    unsafe_allow_html=True,
                )
        with ts2:
            if liked_posts:
                for p in sorted(
                    liked_posts,
                    key=lambda x: x.get("date", ""),
                    reverse=True,
                ):
                    render_post(p, ctx="mylk", compact=True)
            else:
                st.markdown(
                    '<div class="glass" style="padding:2.5rem;text-align:center;color:var(--t3)">Nenhuma curtida ainda.</div>',
                    unsafe_allow_html=True,
                )
        with ts:
            if saved_arts:
                for idx, a in enumerate(saved_arts):
                    render_article(a, idx=idx + 3000, ctx="saved")
                    uid2 = re.sub(
                        r"[^a-zA-Z0-9]", "", f"rms_{idx}"
                    )[:20]
                    if st.button(
                        "🗑 Remover",
                        key=f"rm_sa_{uid2}",
                        use_container_width=True,
                    ):
                        st.session_state.saved_articles = [
                            s
                            for s in st.session_state.saved_articles
                            if s.get("doi") != a.get("doi")
                        ]
                        save_db()
                        st.rerun()
            else:
                st.markdown(
                    '<div class="glass" style="padding:2.5rem;text-align:center;color:var(--t3)">Nenhum artigo salvo.</div>',
                    unsafe_allow_html=True,
                )

def render_post(post, ctx="feed", show_author=True, compact=False):
    email = st.session_state.current_user
    pid = post["id"]
    liked = email in post.get("liked_by", [])
    saved = email in post.get("saved_by", [])
    aemail = post.get("author_email", "")
    ain = post.get("avatar", "??")
    aname = post.get("author", "?")
    g = ugrad(aemail)
    dt = time_ago(post.get("date", ""))
    views = post.get("views", 200)
    ab = post.get("abstract", "")
    if compact and len(ab) > 200:
        ab = ab[:200] + "…"
    if show_author:
        hdr = (
            f'<div style="padding:.8rem 1.1rem .55rem;display:flex;align-items:center;gap:9px;border-bottom:1px solid rgba(255,255,255,.04)">'
            f"{avh(ain, 38, g)}<div style=\"flex:1;min-width:0\">"
            f'<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.85rem;color:var(--t0)">{aname}</div>'
            f'<div style="color:var(--t3);font-size:.63rem">{post.get("area", "")} · {dt}</div>'
            f"</div>{badge(post['status'])}</div>"
        )
    else:
        hdr = f'<div style="padding:.35rem 1.1rem .15rem;display:flex;justify-content:space-between;align-items:center"><span style="color:var(--t3);font-size:.63rem">{dt}</span>{badge(post["status"])}</div>'
    st.markdown(
        f'<div class="post-card">{hdr}<div style="padding:.65rem 1.1rem"><div style="font-family:Syne,sans-serif;font-size:.96rem;font-weight:700;margin-bottom:.32rem;color:var(--t0)">{post["title"]}</div><div style="color:var(--t2);font-size:.79rem;line-height:1.65;margin-bottom:.5rem">{ab}</div><div>{tags_html(post.get("tags", []))}</div></div></div>',
        unsafe_allow_html=True,
    )
    heart = "❤️" if liked else "🤍"
    book = "🔖" if saved else "📌"
    nc = len(post.get("comments", []))
    ca, cb, cc, cd, ce, cf = st.columns(
        [1.1, 1, 0.65, 0.55, 1, 1.1]
    )
    with ca:
        if st.button(
            f"{heart} {fmt_num(post['likes'])}",
            key=f"lk_{ctx}_{pid}",
            use_container_width=True,
        ):
            if liked:
                post["liked_by"].remove(email)
                post["likes"] = max(0, post["likes"] - 1)
            else:
                post["liked_by"].append(email)
                post["likes"] += 1
                record(post.get("tags", []), 1.5)
            save_db()
            st.rerun()
    with cb:
        if st.button(
            f"💬 {nc}" if nc else "💬",
            key=f"cm_{ctx}_{pid}",
            use_container_width=True,
        ):
            k = f"cmt_{ctx}_{pid}"
            st.session_state[k] = not st.session_state.get(k, False)
            st.rerun()
    with cc:
        if st.button(
            book, key=f"sv_{ctx}_{pid}", use_container_width=True
        ):
            if saved:
                post["saved_by"].remove(email)
            else:
                post["saved_by"].append(email)
            save_db()
            st.rerun()
    with cd:
        if st.button(
            "↗", key=f"sh_{ctx}_{pid}", use_container_width=True
        ):
            k = f"shr_{ctx}_{pid}"
            st.session_state[k] = not st.session_state.get(k, False)
            st.rerun()
    with ce:
        st.markdown(
            f'<div style="text-align:center;color:var(--t3);font-size:.67rem;padding:.48rem 0">👁 {fmt_num(views)}</div>',
            unsafe_allow_html=True,
        )
    with cf:
        if show_author and aemail:
            if st.button(
                f"👤 {aname.split()[0]}",
                key=f"vp_{ctx}_{pid}",
                use_container_width=True,
            ):
                st.session_state.profile_view = aemail
                st.rerun()
    if st.session_state.get(f"cmt_{ctx}_{pid}", False):
        for c in post.get("comments", []):
            ci = ini(c["user"])
            ce2 = next(
                (
                    e
                    for e, u in st.session_state.users.items()
                    if u.get("name") == c["user"]
                ),
                "",
            )
            cg = ugrad(ce2)
            st.markdown(
                f'<div class="cmt"><div style="display:flex;align-items:center;gap:7px;margin-bottom:.2rem">{avh(ci, 26, cg)}<span style="font-size:.73rem;font-weight:700;color:var(--yel)">{c["user"]}</span></div><div style="font-size:.78rem;color:var(--t2);line-height:1.55;padding-left:33px">{c["text"]}</div></div>',
                unsafe_allow_html=True,
            )
        nc_txt = st.text_input(
            "",
            placeholder="Escreva um comentário…",
            key=f"ci_{ctx}_{pid}",
            label_visibility="collapsed",
        )
        if st.button("→ Enviar", key=f"cs_{ctx}_{pid}"):
            if nc_txt:
                uu = guser()
                post["comments"].append(
                    {"user": uu.get("name", "Você"), "text": nc_txt}
                )
                record(post.get("tags", []), 0.8)
                save_db()
                st.rerun()

def page_feed():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    email = st.session_state.current_user
    u = guser()
    uname = u.get("name", "?")
    uin = ini(uname)
    g = ugrad(email)
    users = (
        st.session_state.users
        if isinstance(st.session_state.users, dict)
        else {}
    )
    co = st.session_state.get("compose_open", False)
    cm, cs = st.columns([2, 0.9], gap="medium")
    with cm:
        if co:
            st.markdown(
                f'<div class="compose-box"><div style="display:flex;align-items:center;gap:9px;margin-bottom:.9rem">{avh(uin, 40, g)}<div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.88rem;color:var(--t0)">{uname}</div><div style="font-size:.65rem;color:var(--t3)">{u.get("area", "Pesquisador")}</div></div></div>',
                unsafe_allow_html=True,
            )
            nt = st.text_input(
                "Título *", key="np_t", placeholder="Título da pesquisa…"
            )
            nab = st.text_area(
                "Resumo *", key="np_ab", height=100, placeholder="Descreva sua pesquisa…"
            )
            c1c, c2c = st.columns(2)
            with c1c:
                ntg = st.text_input(
                    "Tags (vírgula)", key="np_tg", placeholder="neurociência, IA"
                )
            with c2c:
                nst = st.selectbox(
                    "Status",
                    ["Em andamento", "Publicado", "Concluído"],
                    key="np_st",
                )
            cp, cc = st.columns([2, 1])
            with cp:
                if st.button(
                    "🚀 Publicar",
                    key="btn_pub",
                    use_container_width=True,
                ):
                    if not nt or not nab:
                        st.warning("Título e resumo obrigatórios.")
                    else:
                        tags = (
                            [t.strip() for t in ntg.split(",") if t.strip()]
                            if ntg
                            else []
                        )
                        np2 = {
                            "id": len(st.session_state.feed_posts)
                            + 200
                            + hash(nt) % 99,
                            "author": uname,
                            "author_email": email,
                            "avatar": uin,
                            "area": u.get("area", ""),
                            "title": nt,
                            "abstract": nab,
                            "tags": tags,
                            "likes": 0,
                            "comments": [],
                            "status": nst,
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "liked_by": [],
                            "saved_by": [],
                            "connections": tags[:3],
                            "views": 1,
                        }
                        st.session_state.feed_posts.insert(0, np2)
                        record(tags, 2.0)
                        save_db()
                        st.session_state.compose_open = False
                        st.session_state.local_index_version += 1
                        st.rerun()
            with cc:
                if st.button(
                    "✕ Cancelar",
                    key="btn_cc",
                    use_container_width=True,
                ):
                    st.session_state.compose_open = False
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            ac, bc = st.columns([0.05, 1], gap="small")
            with ac:
                st.markdown(
                    f'<div style="padding-top:6px">{avh(uin, 38, g)}</div>',
                    unsafe_allow_html=True,
                )
            with bc:
                if st.button(
                    f"No que está pesquisando, {uname.split()[0]}?",
                    key="oc",
                    use_container_width=True,
                ):
                    st.session_state.compose_open = True
                    st.rerun()
        ff = st.radio(
            "",
            ["🌐 Todos", "👥 Seguidos", "🔖 Salvos", "🔥 Populares"],
            horizontal=True,
            key="ff",
            label_visibility="collapsed",
        )
        recs = get_recs(email, 2)
        if recs and "Seguidos" not in ff and "Salvos" not in ff:
            st.markdown(
                '<div class="dtxt"><span class="badge-yel">✨ Recomendado</span></div>',
                unsafe_allow_html=True,
            )
            for p in recs:
                render_post(p, ctx="rec", compact=True)
            st.markdown(
                '<div class="dtxt">Mais pesquisas</div>',
                unsafe_allow_html=True,
            )
        posts = list(st.session_state.feed_posts)
        if "Seguidos" in ff:
            posts = [
                p
                for p in posts
                if p.get("author_email") in st.session_state.followed
            ]
        elif "Salvos" in ff:
            posts = [
                p
                for p in posts
                if email in p.get("saved_by", [])
            ]
        elif "Populares" in ff:
            posts = sorted(
                posts, key=lambda p: p["likes"], reverse=True
            )
        else:
            posts = sorted(
                posts, key=lambda p: p.get("date", ""), reverse=True
            )
        if not posts:
            st.markdown(
                '<div class="glass" style="padding:3rem;text-align:center"><div style="font-size:2rem;opacity:.2;margin-bottom:.7rem">🔬</div><div style="color:var(--t3)">Nenhuma pesquisa.</div></div>',
                unsafe_allow_html=True,
            )
        else:
            for p in posts:
                render_post(p, ctx="feed")
    with cs:
        sq = st.text_input(
            "",
            placeholder="🔍 Buscar pesquisadores…",
            key="ppl_s",
            label_visibility="collapsed",
        )
        st.markdown('<div class="sc">', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.80rem;margin-bottom:.8rem;display:flex;justify-content:space-between;color:var(--t0)"><span>Quem seguir</span><span style="font-size:.62rem;color:var(--t3);font-weight:400">Sugestões</span></div>',
            unsafe_allow_html=True,
        )
        sn = 0
        for ue, ud in list(users.items()):
            if ue == email or sn >= 5:
                continue
            rn = ud.get("name", "?")
            if (
                sq
                and sq.lower() not in rn.lower()
                and sq.lower() not in ud.get("area", "").lower()
            ):
                continue
            sn += 1
            is_fol = ue in st.session_state.followed
            uin_r = ini(rn)
            rg = ugrad(ue)
            online = is_online(ue)
            dot = (
                '<span class="dot-on"></span>'
                if online
                else '<span class="dot-off"></span>'
            )
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;padding:.38rem 0;border-bottom:1px solid rgba(255,255,255,.04)">{avh(uin_r, 30, rg)}<div style="flex:1;min-width:0"><div style="font-size:.76rem;font-weight:600;color:var(--t1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{dot}{rn}</div><div style="font-size:.60rem;color:var(--t3)">{ud.get("area", "")[:20]}</div></div></div>',
                unsafe_allow_html=True,
            )
            cf2, cv2 = st.columns(2)
            with cf2:
                st.markdown('<div>', unsafe_allow_html=True)
                if st.button(
                    "✓ Seg." if is_fol else "+ Seguir",
                    key=f"sf_{ue}",
                    use_container_width=True,
                ):
                    if is_fol:
                        st.session_state.followed.remove(ue)
                        ud["followers"] = max(
                            0, ud.get("followers", 0) - 1
                        )
                    else:
                        st.session_state.followed.append(ue)
                        ud["followers"] = ud.get("followers", 0) + 1
                    save_db()
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            with cv2:
                if st.button(
                    "👤 Ver",
                    key=f"svr_{ue}",
                    use_container_width=True,
                ):
                    st.session_state.profile_view = ue
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="sc">', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.80rem;margin-bottom:.75rem;color:var(--t0)">🔥 Em Alta</div>',
            unsafe_allow_html=True,
        )
        for i, (t, c) in enumerate(
            [
                ("Quantum ML", "34"),
                ("CRISPR 2026", "28"),
                ("Neuroplasticidade", "22"),
                ("LLMs Científicos", "19"),
                ("Matéria Escura", "15"),
            ]
        ):
            st.markdown(
                f'<div style="padding:.32rem 0;border-bottom:1px solid rgba(255,255,255,.04)"><div style="font-size:.57rem;color:var(--t3)">#{i + 1}</div><div style="font-size:.76rem;font-weight:600;color:{VIB[i]}">{t}</div><div style="font-size:.58rem;color:var(--t3)">{c} pesquisas</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def render_article(a, idx=0, ctx="web"):
    sc = (
        VIB[1]
        if a.get("origin") == "semantic"
        else VIB[2]
    )
    sn = (
        "Semantic Scholar"
        if a.get("origin") == "semantic"
        else "CrossRef"
    )
    cite = f" · {a['citations']} cit." if a.get("citations") else ""
    uid = re.sub(
        r"[^a-zA-Z0-9]",
        "",
        f"{ctx}_{idx}_{str(a.get('doi', ''))[:10]}",
    )[:32]
    is_saved = any(
        s.get("doi") == a.get("doi")
        for s in st.session_state.saved_articles
    )
    ab = (a.get("abstract", "") or "")[:250] + (
        "…" if len(a.get("abstract", "")) > 250 else ""
    )
    st.markdown(
        f'<div class="scard"><div style="display:flex;align-items:flex-start;gap:7px;margin-bottom:.28rem"><div style="flex:1;font-family:Syne,sans-serif;font-size:.86rem;font-weight:700;color:var(--t0)">{a["title"]}</div><span style="font-size:.58rem;color:{sc};background:rgba(255,255,255,.04);border-radius:7px;padding:2px 7px;white-space:nowrap;flex-shrink:0">{sn}</span></div><div style="color:var(--t3);font-size:.64rem;margin-bottom:.3rem">{a["authors"]} · <em>{a["source"]}</em> · {a["year"]}{cite}</div><div style="color:var(--t2);font-size:.76rem;line-height:1.62">{ab}</div></div>',
        unsafe_allow_html=True,
    )
    ca, cb, cc = st.columns(3)
    with ca:
        st.markdown('<div>', unsafe_allow_html=True)
        if st.button(
            "🔖 Salvo" if is_saved else "📌 Salvar",
            key=f"svw_{uid}",
        ):
            if is_saved:
                st.session_state.saved_articles = [
                    s
                    for s in st.session_state.saved_articles
                    if s.get("doi") != a.get("doi")
                ]
                st.toast("Removido")
            else:
                st.session_state.saved_articles.append(a)
                st.toast("Salvo!")
            save_db()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with cb:
        if st.button("📋 Citar", key=f"ctw_{uid}"):
            st.toast(
                f'{a["authors"]} ({a["year"]}). {a["title"]}.'
            )
    with cc:
        if a.get("url"):
            st.markdown(
                f'<a href="{a["url"]}" target="_blank" style="color:var(--blu);font-size:.78rem;text-decoration:none;line-height:2.4;display:block">↗ Abrir</a>',
                unsafe_allow_html=True,
            )

def page_search():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown(
        '<h1 style="padding-top:.8rem;margin-bottom:.3rem">🔍 Busca Acadêmica & Repositório</h1>',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns([4, 1])
    with c1:
        q = st.text_input(
            "",
            placeholder="CRISPR · quantum ML · dark matter…",
            key="sq",
            label_visibility="collapsed",
        )
    with c2:
        if st.button("🔍 Buscar", key="btn_s", use_container_width=True):
            if q:
                with st.spinner("Varredura completa (repositório + web)…"):
                    docs = build_local_index(
                        st.session_state.users,
                        st.session_state.feed_posts,
                        st.session_state.folders,
                        st.session_state.local_index_version,
                    )
                    local_results = search_local(q, docs, topk=25)
                    ssr = search_ss(q, 6)
                    crr = search_cr(q, 4)
                    # merge
                    web = ssr + [
                        x
                        for x in crr
                        if not any(
                            x["title"].lower() == s["title"].lower()
                            for s in ssr
                        )
                    ]
                    st.session_state.search_results = {
                        "local": local_results,
                        "web": web,
                    }
                    st.session_state.last_sq = q
                    record([q.lower()], 0.4)
    if (
        st.session_state.get("search_results")
        and st.session_state.get("last_sq")
    ):
        res = st.session_state.search_results
        local = res.get("local", [])
        web = res.get("web", [])
        repo_docs = [d for d in local if d["type"] == "folder_doc"]
        posts = [d for d in local if d["type"] == "post"]

        ta, tr, tn, tw = st.tabs(
            [
                f"  Todos ({len(local) + len(web)})  ",
                f"  📚 Repositório ({len(repo_docs)})  ",
                f"  🔬 Nebula Feed ({len(posts)})  ",
                f"  🌐 Internet ({len(web)})  ",
            ]
        )

        def render_repo_doc(doc):
            meta = doc["meta"]
            an = meta["analysis"]
            folder = meta["folder"]
            f = meta["file"]
            rel = an.get("relevance_score", 0)
            topics = list(an.get("topics", {}).keys())[:3]
            kws = an.get("keywords", [])[:8]
            st.markdown(
                f"""<div class="scard">
    <div style="font-family:Syne,sans-serif;font-size:.86rem;font-weight:700;color:var(--t0);margin-bottom:.2rem">
        📁 {doc["title"]}
    </div>
    <div style="font-size:.64rem:var(--t3);margin-bottom:.25rem">
        Pasta: <strong>{folder}</strong> · Relevância: <span style="color:var(--yel)">{rel}%</span>
    </div>
    <div style="font-size:.73rem;color:var(--t2);margin-bottom:.3rem">
        Temas: {", ".join(topics) if topics else "—"}
    </div>
    <div>{tags_html(kws)}</div>
</div>""",
                unsafe_allow_html=True,
            )

        with ta:
            if repo_docs:
                st.markdown(
                    '<div style="font-size:.59rem;color:var(--yel);font-weight:700;margin-bottom:.4rem;letter-spacing:.10em;text-transform:uppercase">No Repositório</div>',
                    unsafe_allow_html=True,
                )
                for d in repo_docs:
                    render_repo_doc(d)
            if posts:
                st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown(
                    '<div style="font-size:.59rem;color:var(--yel);font-weight:700;margin-bottom:.4rem;letter-spacing:.10em;text-transform:uppercase">No Feed</div>',
                    unsafe_allow_html=True,
                )
                for d in posts:
                    render_post(
                        d["meta"], ctx="srch_all", compact=True
                    )
            if web:
                st.markdown("<hr>", unsafe_allow_html=True)
                for idx, a in enumerate(web):
                    render_article(a, idx=idx, ctx="all_w")
            if not repo_docs and not posts and not web:
                st.info("Nenhum resultado.")

        with tr:
            for d in repo_docs:
                render_repo_doc(d)
            if not repo_docs:
                st.info("Nenhum resultado no repositório.")

        with tn:
            for d in posts:
                render_post(d["meta"], ctx="srch_neb", compact=True)
            if not posts:
                st.info("Nenhuma pesquisa no feed.")

        with tw:
            for idx, a in enumerate(web):
                render_article(a, idx=idx, ctx="web_t")
            if not web:
                st.info("Nenhum artigo encontrado na internet.")
    st.markdown("</div>", unsafe_allow_html=True)

def page_knowledge():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown(
        '<h1 style="padding-top:.8rem;margin-bottom:.9rem">🕸 Rede de Conexões com IA</h1>',
        unsafe_allow_html=True,
    )
    email = st.session_state.current_user
    users = (
        st.session_state.users
        if isinstance(st.session_state.users, dict)
        else {}
    )
    api_key = st.session_state.get("anthropic_key", "")

    rlist = list(users.keys())
    n = len(rlist)

    def get_tags(ue):
        ud = users.get(ue, {})
        tags = set(area_tags(ud.get("area", "")))
        for p in st.session_state.feed_posts:
            if p.get("author_email") == ue:
                tags.update(t.lower() for t in p.get("tags", []))
        # pastas
        for fname, fd in st.session_state.folders.items():
            if (
                isinstance(fd, dict)
                and fd.get("owner") == ue
            ):
                tags.update(
                    kw.lower()
                    for kw in fd.get("keywords_agg", [])
                )
        return tags

    rtags = {ue: get_tags(ue) for ue in rlist}
    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            e1, e2 = rlist[i], rlist[j]
            common = list(rtags[e1] & rtags[e2])
            is_fol = (
                e2 in st.session_state.followed
                or e1 in st.session_state.followed
            )
            if common or is_fol:
                edges.append(
                    (
                        e1,
                        e2,
                        common[:5],
                        len(common) + (2 if is_fol else 0),
                    )
                )

    pos = {}
    for idx, ue in enumerate(rlist):
        angle = 2 * 3.14159 * idx / max(n, 1)
        rd = 0.36 + 0.05 * ((hash(ue) % 5) / 4)
        pos[ue] = {
            "x": 0.5 + rd * np.cos(angle),
            "y": 0.5 + rd * np.sin(angle),
            "z": 0.5 + 0.12 * ((idx % 4) / 3 - 0.35),
        }

    fig = go.Figure()
    for e1, e2, common, strength in edges:
        p1 = pos[e1]
        p2 = pos[e2]
        alpha = min(0.45, 0.08 + strength * 0.06)
        fig.add_trace(
            go.Scatter3d(
                x=[p1["x"], p2["x"], None],
                y=[p1["y"], p2["y"], None],
                z=[p1["z"], p2["z"], None],
                mode="lines",
                line=dict(
                    color=f"rgba(10,110,189,{alpha:.2f})",
                    width=min(3, 1 + strength),
                ),
                hoverinfo="none",
                showlegend=False,
            )
        )
    nc = [
        (
            "⭐ Você",
            "#0A6EBD",
        )
        if ue == email
        else (
            ("#6A9C89", "#6A9C89")
            if ue in st.session_state.followed
            else ("#4CC9F0", "#4CC9F0")
        )
        for ue in rlist
    ]
    ncolors = [c[1] for c in nc]
    nsizes = [
        22
        if ue == email
        else (16 if ue in st.session_state.followed else 11)
        for ue in rlist
    ]
    fig.add_trace(
        go.Scatter3d(
            x=[pos[ue]["x"] for ue in rlist],
            y=[pos[ue]["y"] for ue in rlist],
            z=[pos[ue]["z"] for ue in rlist],
            mode="markers+text",
            marker=dict(
                size=nsizes,
                color=ncolors,
                opacity=0.9,
                line=dict(
                    color="rgba(255,255,255,.08)", width=1.5
                ),
            ),
            text=[
                users.get(ue, {}).get("name", "?").split()[0]
                for ue in rlist
            ],
            textposition="top center",
            textfont=dict(
                color="#6B6F88", size=9, family="DM Sans"
            ),
            hovertemplate=[
                f"<b>{users.get(ue, {}).get('name', '?')}</b><br>{users.get(ue, {}).get('area', '')}<extra></extra>"
                for ue in rlist
            ],
            showlegend=False,
        )
    )
    fig.update_layout(
        height=420,
        scene=dict(
            xaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=False,
                showbackground=False,
            ),
            yaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=False,
                showbackground=False,
            ),
            zaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=False,
                showbackground=False,
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)
    for col, (cls, v, l) in zip(
        [c1, c2, c3, c4],
        [
            ("mval-yel", len(rlist), "Pesquisadores"),
            ("mval-grn", len(edges), "Conexões"),
            ("mval-blu", len(st.session_state.followed), "Seguindo"),
            (
                "mval-red",
                len(st.session_state.feed_posts),
                "Pesquisas",
            ),
        ],
    ):
        with col:
            st.markdown(
                f'<div class="mbox"><div class="{cls}">{v}</div><div class="mlbl">{l}</div></div>',
                unsafe_allow_html=True,
            )
    st.markdown("<hr>", unsafe_allow_html=True)

    tm, tai, tmi, tall = st.tabs(
        [
            "  🗺 Mapa  ",
            "  🤖 IA Conexões  ",
            "  🔗 Minhas  ",
            "  👥 Todos  ",
        ]
    )

    with tm:
        for e1, e2, common, strength in sorted(
            edges, key=lambda x: -x[3]
        )[:20]:
            n1 = users.get(e1, {})
            n2 = users.get(e2, {})
            ts = (
                tags_html(common[:4])


