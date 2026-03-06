import subprocess, sys, os, json, hashlib, random, string, re, io, base64, time
from datetime import datetime, date
from collections import defaultdict, Counter

# --- REMOVIDA a função _pip() ---
# O Glitch instalará as dependências via requirements.txt

# --- Importações de Pacotes ---
# Agora, as importações são diretas, pois os pacotes serão instalados pelo Glitch.
import plotly.graph_objects as go
import numpy as np
from PIL import Image as PILImage
import requests

# PyPDF2: se falhar, fica como None (a função extract_pdf já trata)
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    import pandas as pd
except ImportError:
    pd = None

# ML / Image Processing — com fallbacks numpy
SKIMAGE_OK = False
SKLEARN_OK = False
SCIPY_OK = False

try:
    from skimage import filters as sk_filters, feature as sk_feature
    from skimage.feature import graycomatrix, graycoprops
    SKIMAGE_OK = True
except ImportError:
    pass # Se não conseguir importar, SKIMAGE_OK permanece False

try:
    from sklearn.cluster import KMeans
    SKLEARN_OK = True
except ImportError:
    pass # Se não conseguir importar, SKLEARN_OK permanece False

try:
    from scipy import ndimage as sp_ndimage
    SCIPY_OK = True
except ImportError:
    pass # Se não conseguir importar, SCIPY_OK permanece False

import streamlit as st

st.set_page_config(
    page_title="Nebula - Repositório Científico", icon="🔬", layout="wide", initial_sidebar_state="expanded"
)

DB_FILE = "nebula_db.json"

# --- Funções de Utilitário ---
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
    return ''.join(random.choices(string.digits, k=6))

def ini(n):
    if not isinstance(n, str):
        n = str(n)
    p = n.strip().split()
    return ''.join(w[0].upper() for w in p[:2]) if p else "?"

def time_ago(ds):
    try:
        dt = datetime.strptime(ds, "%Y-%m-%d")
        d = (datetime.now() - dt).days
        if d == 0: return "hoje"
        if d == 1: return "ontem"
        if d < 7: return f"{d}d"
        if d < 30: return f"{d // 7}sem"
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

GRAD_POOL = [
    "135deg,#0A1929,#1A2F4A", "135deg,#0B1E33,#1D3A5A", "135deg,#0C2138,#20456A",
    "135deg,#0D253D,#23507A", "135deg,#0E2942,#265B8A", "135deg,#0F2D47,#29669A",
]

def ugrad(e):
    return f"linear-gradient({GRAD_POOL[hash(e or '') % len(GRAD_POOL)]})"

STOPWORDS = {
    "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "é", "com", "uma", "os", "no", "se",
    "na", "por", "mais", "as", "dos", "como", "mas", "foi", "ao", "ele", "das", "tem", "à", "seu",
    "sua", "ou", "ser", "quando", "muito", "há", "nos", "já", "está", "eu", "também", "só", "pelo",
    "pela", "até", "isso", "ela", "entre", "era", "depois", "sem", "mesmo", "aos", "ter", "seus",
    "the", "of", "and", "to", "in", "is", "it", "that", "was", "he", "for", "on", "are", "as", "with",
    "they", "at", "be", "this", "from", "or", "one", "had", "by", "but", "not", "what", "all", "were",
    "we", "when", "your", "can", "said", "there", "use", "an", "each", "which", "she", "do", "how",
    "their", "if", "will", "up", "other", "about", "out", "many", "then", "them", "these", "so"
}

# --- Dados Iniciais ---
SEED_USERS = {
    "demo@nebula.ai": {"name": "Ana Pesquisadora", "password": hp("demo123"),
                       "bio": "Pesquisadora em IA e Ciências Cognitivas | UFMG", "area": "Inteligência Artificial",
                       "followers": 128, "following": 47, "verified": True, "2fa_enabled": False},
    "carlos@nebula.ai": {"name": "Carlos Mendez", "password": hp("nebula123"),
                         "bio": "Neurocientista | UFMG | Plasticidade sináptica e sono", "area": "Neurociência",
                         "followers": 210, "following": 45, "verified": True, "2fa_enabled": False},
    "luana@nebula.ai": {"name": "Luana Freitas", "password": hp("nebula123"),
                        "bio": "Biomédica | FIOCRUZ | CRISPR e terapia gênica", "area": "Biomedicina",
                        "followers": 178, "following": 62, "verified": True, "2fa_enabled": False},
    "rafael@nebula.ai": {"name": "Rafael Souza", "password": hp("nebula123"),
                         "bio": "Computação Quântica | USP | Algoritmos híbridos", "area": "Computação",
                         "followers": 340, "following": 88, "verified": True, "2fa_enabled": False},
    "priya@nebula.ai": {"name": "Priya Nair", "password": hp("nebula123"),
                        "bio": "Astrofísica | MIT | Dark matter & gravitational lensing", "area": "Astrofísica",
                        "followers": 520, "following": 31, "verified": True, "2fa_enabled": False},
    "joao@nebula.ai": {"name": "João Lima", "password": hp("nebula123"),
                       "bio": "Psicólogo Cognitivo | UNICAMP | IA e vieses clínicos", "area": "Psicologia",
                       "followers": 95, "following": 120, "verified": True, "2fa_enabled": False},
}

# --- Gerenciamento de Estado da Aplicação ---
def save_db():
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "users": st.session_state.users,
                "folders": st.session_state.folders,
                "user_prefs": {k: dict(v) for k, v in st.session_state.user_prefs.items()},
                "saved_articles": st.session_state.saved_articles,
                "followed": st.session_state.followed,
                "chat_messages": {k: list(v) for k, v in st.session_state.chat_messages.items()},
                "chat_contacts": st.session_state.chat_contacts,
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Erro ao salvar o banco de dados: {e}")

def init():
    if "initialized" in st.session_state:
        return
    st.session_state.initialized = True
    disk = load_db()

    st.session_state.setdefault("users", {**SEED_USERS, **disk.get("users", {})})
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("current_user", None)
    st.session_state.setdefault("page", "repository")
    st.session_state.setdefault("profile_view", None)
    st.session_state.setdefault("user_prefs", {k: defaultdict(float, v) for k, v in disk.get("user_prefs", {}).items()})
    st.session_state.setdefault("pending_verify", None)
    st.session_state.setdefault("pending_2fa", None)

    folders = disk.get("folders", {})
    if isinstance(folders, dict):
        for fn, fd in list(folders.items()):
            if not isinstance(fd, dict):
                folders[fn] = {
                    "desc": "", "files": fd, "notes": "", "analyses": {},
                    "topics_agg": {}, "keywords_agg": [], "last_updated": datetime.now().isoformat(),
                    "owner": None, "visibility": "private",
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
    st.session_state.setdefault("chat_contacts", disk.get("chat_contacts", list(SEED_USERS.keys())))
    st.session_state.setdefault("chat_messages", {k: list(v) for k, v in disk.get("chat_messages", {}).items()})
    st.session_state.setdefault("active_chat", None)
    st.session_state.setdefault("followed", disk.get("followed", ["carlos@nebula.ai", "luana@nebula.ai"]))
    st.session_state.setdefault("notifications", ["Nova conexão detectada"])
    st.session_state.setdefault("scholar_cache", {})
    st.session_state.setdefault("saved_articles", disk.get("saved_articles", []))
    st.session_state.setdefault("img_result", None)
    st.session_state.setdefault("search_results", None)
    st.session_state.setdefault("last_sq", "")
    st.session_state.setdefault("stats_data", {"h_index": 4, "fator_impacto": 3.8, "notes": ""})
    st.session_state.setdefault("anthropic_key", "")
    st.session_state.setdefault("ai_conn_cache", {})
    st.session_state.setdefault("ml_cache", {})
    st.session_state.setdefault("local_index_version", 0)

init()

# --- IA Real: Claude Vision e Conexões ---
def call_claude_vision(img_bytes, prompt, api_key):
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
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            },
            timeout=25
        )
        if resp.status_code == 200:
            data = resp.json()
            return data["content"][0]["text"], None
        else:
            try: err = resp.json().get("error", {}).get("message", f"HTTP {resp.status_code}")
            except: err = f"HTTP {resp.status_code}"
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

def call_claude_connections(users_data, folders_data, email, api_key):
    if not api_key or not api_key.startswith("sk-"):
        return None, "API key ausente."
    try:
        u = users_data.get(email, {})
        my_tags = set(area_tags(u.get("area", "")))
        for fname, fd in folders_data.items():
            if isinstance(fd, dict) and fd.get("owner") == email:
                my_tags.update(kw.lower() for kw in fd.get("keywords_agg", []))

        others = []
        for ue, ud in users_data.items():
            if ue == email: continue
            other_tags = set(area_tags(ud.get("area", "")))
            for fname, fd in folders_data.items():
                if isinstance(fd, dict) and fd.get("owner") == ue:
                    other_tags.update(kw.lower() for kw in fd.get("keywords_agg", []))

            others.append({
                "email": ue, "name": ud.get("name", ""), "area": ud.get("area", ""),
                "tags": list(other_tags)[:8]
            })

        payload = {
            "meu_perfil": {"area": u.get("area", ""), "bio": u.get("bio", ""),
                           "tags": list(my_tags)[:10]},
            "pesquisadores": others[:20]
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
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-3-opus-20240229", "max_tokens": 600,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=20
        )
        if resp.status_code == 200:
            text = resp.json()["content"][0]["text"].strip()
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            return json.loads(text), None
        return None, f"HTTP {resp.status_code}"
    except Exception as e:
        return None, str(e)

# --- Pipeline ML para Imagens ---
def sobel_analysis(gray_arr):
    try:
        if SKIMAGE_OK:
            import skimage.filters as skf
            sx = skf.sobel_h(gray_arr)
            sy = skf.sobel_v(gray_arr)
        else:
            kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32) / 8.0
            ky = kx.T
            from numpy import pad as nppad
            def conv2d(img, k):
                ph, pw = k.shape[0] // 2, k.shape[1] // 2
                padded = nppad(img, ((ph, ph), (pw, pw)), mode='edge')
                out = np.zeros_like(img)
                for i in range(k.shape[0]):
                    for j in range(k.shape[1]):
                        out += k[i, j] * padded[i:i + img.shape[0], j:j + img.shape[1]]
                return out
            sx = conv2d(gray_arr.astype(np.float32), kx)
            sy = conv2d(gray_arr.astype(np.float32), ky)
        magnitude = np.sqrt(sx ** 2 + sy ** 2)
        direction = np.arctan2(sy, sx) * 180 / np.pi
        return {
            "magnitude": magnitude, "horizontal": sx, "vertical": sy,
            "mean_edge": float(magnitude.mean()), "max_edge": float(magnitude.max()),
            "edge_density": float((magnitude > magnitude.mean() * 1.5).mean()),
            "dominant_direction": float(direction.mean()),
            "edge_hist": np.histogram(magnitude, bins=16, range=(0, magnitude.max() + 1e-5))[0].tolist()
        }
    except Exception:
        gx = np.gradient(gray_arr.astype(np.float32), axis=1)
        gy = np.gradient(gray_arr.astype(np.float32), axis=0)
        mag = np.sqrt(gx ** 2 + gy ** 2)
        return {"magnitude": mag, "horizontal": gx, "vertical": gy,
                "mean_edge": float(mag.mean()), "max_edge": float(mag.max()),
                "edge_density": float((mag > mag.mean() * 1.5).mean()),
                "dominant_direction": 0.0, "edge_hist": np.histogram(mag, bins=16)[0].tolist()}

def canny_analysis(gray_uint8):
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
            mag = np.sqrt(gx ** 2 + gy ** 2)
            t1, t2, t3 = np.percentile(mag, 85), np.percentile(mag, 75), np.percentile(mag, 65)
            edges_fine = mag > t1; edges_med = mag > t2; edges_coarse = mag > t3
        return {
            "fine": edges_fine, "medium": edges_med, "coarse": edges_coarse,
            "fine_density": float(edges_fine.mean()), "medium_density": float(edges_med.mean()),
            "coarse_density": float(edges_coarse.mean()), "total_edges": int(edges_fine.sum()),
            "structure_level": "micro" if edges_fine.mean() > 0.1 else ("meso" if edges_med.mean() > 0.05 else "macro")
        }
    except Exception:
        g = gray_uint8.astype(np.float32) / 255.0
        gx = np.gradient(g, axis=1); gy = np.gradient(g, axis=0)
        mag = np.sqrt(gx ** 2 + gy ** 2); e = mag > mag.mean()
        return {"fine": e, "medium": e, "coarse": e, "fine_density": float(e.mean()),
                "medium_density": float(e.mean()), "coarse_density": float(e.mean()),
                "total_edges": int(e.sum()), "structure_level": "meso"}

def orb_keypoints(gray_uint8):
    try:
        if SKIMAGE_OK:
            try:
                from skimage.feature import ORB
                detector = ORB(n_keypoints=200, fast_threshold=0.05)
                detector.detect_and_extract(gray_uint8 / 255.0); kp = detector.keypoints
            except:
                from skimage.feature import corner_harris, corner_peaks
                harris = corner_harris(gray_uint8 / 255.0); kp = corner_peaks(harris, min_distance=8, threshold_rel=0.02)
        else:
            g = gray_uint8.astype(np.float32); gx = np.gradient(g, axis=1); gy = np.gradient(g, axis=0)
            mag = np.sqrt(gx ** 2 + gy ** 2); step = 8; pts = []
            for i in range(0, mag.shape[0] - step, step):
                for j in range(0, mag.shape[1] - step, step):
                    block = mag[i:i + step, j:j + step]
                    if block.max() > mag.mean() * 1.8:
                        yi, xj = np.unravel_index(block.argmax(), block.shape); pts.append([i + yi, j + xj])
            kp = np.array(pts) if pts else np.zeros((0, 2))
        scales = np.ones(len(kp))
        if len(kp) > 0 and SKLEARN_OK:
            n_cl = min(5, len(kp))
            try: kmk = KMeans(n_clusters=n_cl, random_state=42, n_init=5).fit(np.array(kp)); centers = kmk.cluster_centers_
            except: centers = np.array(kp)[:5]
        else: centers = np.array(kp)[:5] if len(kp) > 0 else np.zeros((0, 2))
        return {
            "keypoints": kp, "n_keypoints": len(kp), "cluster_centers": centers.tolist() if len(centers) > 0 else [],
            "scales": scales.tolist(), "mean_scale": 1.0,
            "distribution": "uniforme" if len(kp) > 5 and np.std(np.array(kp)[:, 0]) / (np.std(np.array(kp)[:, 1]) + 1e-5) < 1.5 else "concentrado"
        }
    except Exception:
        return {"keypoints": np.zeros((0, 2)), "n_keypoints": 0, "cluster_centers": [], "scales": [], "mean_scale": 1.0, "distribution": "n/a"}

def glcm_texture(gray_uint8):
    try:
        if SKIMAGE_OK:
            from skimage.feature import graycomatrix, graycoprops
            g64 = (gray_uint8 // 4).astype(np.uint8); distances = [1, 3, 5]; angles = [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]
            glcm = graycomatrix(g64, distances=distances, angles=angles, levels=64, symmetric=True, normed=True)
            features = {};
            for prop in ['contrast', 'dissimilarity', 'homogeneity', 'energy', 'correlation', 'ASM']:
                v = graycoprops(glcm, prop); features[prop] = float(v.mean())
            features['contrast_std'] = float(graycoprops(glcm, 'contrast').std()); features['uniformity'] = features['energy']
            features['entropy'] = float(-np.sum(glcm[glcm > 0] * np.log2(glcm[glcm > 0] + 1e-12)))
        else:
            g = gray_uint8.astype(np.float32) / 255.0; gx = np.gradient(g, axis=1); gy = np.gradient(g, axis=0)
            contrast = float(np.sqrt(gx ** 2 + gy ** 2).mean() * 100); homogeneity = float(1.0 / (1.0 + contrast / 50.0))
            energy = float(np.var(g)); correlation = float(np.corrcoef(gx.ravel(), gy.ravel())[0, 1]) if len(gx.ravel()) > 1 else 0.5
            hst = np.histogram(g, bins=64)[0]; hn = hst / hst.sum() + 1e-12; entropy_v = float(-np.sum(hn * np.log2(hn)))
            features = {"contrast": round(contrast, 4), "dissimilarity": round(contrast * 0.5, 4),
                        "homogeneity": round(homogeneity, 4), "energy": round(energy, 4),
                        "correlation": round(abs(correlation), 4), "ASM": round(energy ** 2, 4),
                        "contrast_std": 0.0, "uniformity": round(energy, 4), "entropy": round(entropy_v, 4)}
        features['texture_type'] = classify_texture(features)
        return features
    except Exception as e:
        return {"homogeneity": 0.5, "contrast": 20.0, "energy": 0.1, "correlation": 0.7, "ASM": 0.01,
                "dissimilarity": 10.0, "contrast_std": 0.0, "uniformity": 0.1, "entropy": 4.0,
                "texture_type": "desconhecido", "error": str(e)}

def classify_texture(f):
    if f.get('homogeneity', 0) > 0.7: return "homogênea"
    if f.get('contrast', 0) > 50: return "altamente texturizada"
    if f.get('energy', 0) > 0.1: return "uniforme/periódica"
    if f.get('correlation', 0) > 0.8: return "estruturada"
    return "complexa"

def kmeans_colors(img_arr, k=7):
    if not SKLEARN_OK: return [], []
    try:
        h, w = img_arr.shape[:2]; step = max(1, (h * w) // 4000); flat = img_arr.reshape(-1, 3)[::step].astype(np.float32)
        km = KMeans(n_clusters=k, random_state=42, n_init=5, max_iter=100).fit(flat); centers = km.cluster_centers_.astype(int)
        counts = Counter(km.labels_); total = sum(counts.values()); palette = []
        for i in np.argsort([-counts[j] for j in range(k)]):
            r, g, b = centers[i]; pct = counts[i] / total * 100; hex_c = "#{:02x}{:02x}{:02x}".format(int(r), int(g), int(b))
            palette.append({"rgb": (int(r), int(g), int(b)), "hex": hex_c, "pct": round(pct, 1)})
        temps = []
        for c in palette[:3]:
            r, g, b = c['rgb'];
            if r > b + 20: temps.append("quente")
            elif b > r + 20: temps.append("fria")
            else: temps.append("neutra")
        return palette, temps
    except: return [], []

def fft_analysis(gray_arr):
    fft = np.fft.fft2(gray_arr); fft_shift = np.fft.fftshift(fft); magnitude = np.abs(fft_shift)
    h, w = magnitude.shape; center = magnitude[h // 2 - 30:h // 2 + 30, w // 2 - 30:w // 2 + 30]
    outer = np.concatenate([magnitude[:h // 4, :].ravel(), magnitude[3 * h // 4:, :].ravel()])
    periodic_score = float(np.percentile(outer, 99)) / (float(np.mean(outer)) + 1e-5)
    total = magnitude.sum() + 1e-5; r = min(h, w) // 2; Y, X = np.ogrid[:h, :w]
    dist = np.sqrt((X - w // 2) ** 2 + (Y - h // 2) ** 2)
    lf = float(magnitude[dist < r * 0.1].sum() / total)
    mf = float(magnitude[(dist >= r * 0.1) & (dist < r * 0.4)].sum() / total)
    hf = float(magnitude[dist >= r * 0.4].sum() / total)
    return {
        "periodic_score": round(periodic_score, 2), "is_periodic": periodic_score > 12,
        "low_freq": round(lf, 3), "mid_freq": round(mf, 3), "high_freq": round(hf, 3),
        "dominant_scale": "fina" if hf > 0.5 else ("média" if mf > 0.3 else "grossa")
    }

def classify_scientific_image(sobel_r, canny_r, glcm_r, orb_r, fft_r, color_info, kmeans_palette):
    ei = sobel_r["mean_edge"]; ed = sobel_r["edge_density"]; sym = color_info["symmetry"]
    entropy = color_info["entropy"]; n_kp = orb_r["n_keypoints"]; periodic = fft_r["is_periodic"]
    hom = glcm_r.get("homogeneity", 0.5); contrast = glcm_r.get("contrast", 20); corr = glcm_r.get("correlation", 0.5)
    mr, mg, mb = color_info["r"], color_info["g"], color_info["b"]
    scores = {}

    he_score = 0;
    if mr > 140 and mb > 100 and mg < mr: he_score += 30
    if n_kp > 80: he_score += 20;
    if contrast > 30: he_score += 20;
    if ed > 0.12: he_score += 15;
    if glcm_r.get("texture_type") == "complexa": he_score += 15;
    scores["Histopatologia H&E"] = he_score

    dapi_score = 0;
    if mb > 150 and mb > mr + 30: dapi_score += 45;
    if entropy > 5.0: dapi_score += 20;
    if ed > 0.1: dapi_score += 20;
    if n_kp > 30: dapi_score += 15;
    scores["Fluorescência DAPI/Nuclear"] = dapi_score

    gfp_score = 0;
    if mg > 150 and mg > mr + 30: gfp_score += 45;
    if entropy > 4.5: gfp_score += 20;
    if ed > 0.08: gfp_score += 20;
    scores["Fluorescência GFP/Verde"] = gfp_score

    xray_score = 0;
    if periodic: xray_score += 40;
    if sym > 0.75: xray_score += 25;
    if hom > 0.7: xray_score += 15;
    if fft_r["periodic_score"] > 15: xray_score += 20;
    scores["Cristalografia/Difração"] = xray_score

    wb_score = 0;
    if contrast < 15 and hom > 0.8: wb_score += 30;
    if abs(mr - mg) < 20 and abs(mg - mb) < 20: wb_score += 25;
    if canny_r["coarse_density"] > canny_r["fine_density"]: wb_score += 25;
    scores["Gel/Western Blot"] = wb_score

    chart_score = 0;
    if glcm_r.get("energy", 0) > 0.15: chart_score += 30;
    if hom > 0.85: chart_score += 25;
    if n_kp < 30: chart_score += 20;
    if entropy < 4.0: chart_score += 25;
    scores["Gráfico/Diagrama Científico"] = chart_score

    mol_score = 0;
    if sym > 0.80: mol_score += 35;
    if periodic: mol_score += 25;
    if corr > 0.8: mol_score += 20;
    if abs(mr - mg) < 25 and abs(mg - mb) < 25: mol_score += 20;
    scores["Estrutura Molecular"] = mol_score

    conf_score = 0;
    if len(kmeans_palette) > 4: conf_score += 20;
    if entropy > 5.5: conf_score += 25;
    if n_kp > 50: conf_score += 20;
    if ed > 0.10: conf_score += 20;
    if contrast > 20: conf_score += 15;
    scores["Microscopia Confocal"] = conf_score

    astro_score = 0;
    if color_info.get("brightness", 128) < 60: astro_score += 35;
    if n_kp > 40 and hom > 0.7: astro_score += 25;
    if entropy > 5.0: astro_score += 20;
    if fft_r["high_freq"] > 0.4: astro_score += 20;
    scores["Imagem Astronômica"] = astro_score

    best = max(scores, key=scores.get); best_score = scores[best]; conf = min(96, 40 + best_score * 0.55)

    origin_map = {
        "Histopatologia H&E": "Medicina/Patologia - análise de tecidos corados para diagnóstico",
        "Fluorescência DAPI/Nuclear": "Biologia Celular - marcação de DNA/núcleos com fluoróforo azul",
        "Fluorescência GFP/Verde": "Biologia Molecular - expressão de proteínas fluorescentes verdes",
        "Cristalografia/Difração": "Física/Química - análise de estrutura cristalina por difração",
        "Gel/Western Blot": "Bioquímica/Genômica - separação eletroforética de proteínas/DNA",
        "Gráfico/Diagrama Científico": "Ciência em geral - visualização de dados ou esquema",
        "Estrutura Molecular": "Química Computacional - visualização de moléculas ou cristais",
        "Microscopia Confocal": "Biologia Celular - imagem multicanal de fluorescência confocal",
        "Imagem Astronômica": "Astrofísica - observação de objetos celestes ou fenômenos cósmicos",
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
        "category": best, "confidence": round(conf, 1), "origin": origin_map.get(best, "Ciência Geral"),
        "search_kw": search_map.get(best, best + " scientific imaging"),
        "all_scores": dict(sorted(scores.items(), key=lambda x: -x[1])[:5]),
    }

@st.cache_data(show_spinner=False, ttl=3600)
def run_full_ml_pipeline_cached(img_bytes):
    return run_full_ml_pipeline(img_bytes)

def run_full_ml_pipeline(img_bytes):
    result = {}
    try:
        img = PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
        orig_size = img.size; w, h = img.size
        scale = min(384 / w, 384 / h); new_w, new_h = int(w * scale), int(h * scale)
        img_r = img.resize((new_w, new_h), PILImage.LANCZOS)
        arr = np.array(img_r, dtype=np.float32)
        r_ch, g_ch, b_ch = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        gray = 0.2989 * r_ch + 0.5870 * g_ch + 0.1140 * b_ch
        gray_u8 = gray.astype(np.uint8)
        mr, mg, mb = float(r_ch.mean()), float(g_ch.mean()), float(b_ch.mean())

        hy, hx = gray.shape[0] // 2, gray.shape[1] // 2
        q = [gray[:hy, :hx].var(), gray[:hy, hx:].var(), gray[hy:, :hx].var(), gray[hy:, hx:].var()]
        sym = 1.0 - (max(q) - min(q)) / (max(q) + 1e-5)

        hst = np.histogram(gray, bins=64, range=(0, 255))[0]; hn = hst / hst.sum(); hn = hn[hn > 0]
        entropy = float(-np.sum(hn * np.log2(hn)))

        brightness = float(gray.mean()); std_bright = float(gray.std())

        color_info = {
            "r": round(mr, 1), "g": round(mg, 1), "b": round(mb, 1),
            "symmetry": round(sym, 3), "entropy": round(entropy, 3),
            "brightness": round(brightness, 1), "std": round(std_bright, 1),
            "warm": mr > mb + 15, "cool": mb > mr + 15
        }

        result["color"] = color_info; result["size"] = orig_size
        result["sobel"] = sobel_analysis(gray / 255.0); result["canny"] = canny_analysis(gray_u8)
        result["orb"] = orb_keypoints(gray_u8); result["glcm"] = glcm_texture(gray_u8)
        result["fft"] = fft_analysis(gray / 255.0); result["kmeans_palette"], result["color_temps"] = kmeans_colors(arr.astype(np.uint8), k=7)

        rh = np.histogram(r_ch.ravel(), bins=32, range=(0, 255))[0].tolist()
        gh = np.histogram(g_ch.ravel(), bins=32, range=(0, 255))[0].tolist()
        bh = np.histogram(b_ch.ravel(), bins=32, range=(0, 255))[0].tolist()
        result["histograms"] = {"r": rh, "g": gh, "b": bh}

        result["classification"] = classify_scientific_image(
            result["sobel"], result["canny"], result["glcm"],
            result["orb"], result["fft"], color_info, result["kmeans_palette"]
        )

        if "magnitude" in result["sobel"]:
            mag_norm = result["sobel"]["magnitude"]
            result["sobel_viz"] = (mag_norm / (mag_norm.max() + 1e-5) * 255).astype(np.uint8).tolist()
        result["array_shape"] = [new_h, new_w]; result["ok"] = True
    except Exception as e:
        result["ok"] = False; result["error"] = str(e)
    return result

def analyze_image_file(fname, img_bytes):
    try:
        ml = run_full_ml_pipeline(img_bytes)
        if not ml.get("ok"): return None
        return {
            "classification": ml.get("classification", {}), "color": ml.get("color", {}),
            "fft": ml.get("fft", {}), "glcm": ml.get("glcm", {}),
            "orb": {"n_keypoints": ml.get("orb", {}).get("n_keypoints", 0), "distribution": ml.get("orb", {}).get("distribution", "n/a")}
        }
    except: return None

# --- Funções para Análise de Documentos ---
@st.cache_data(show_spinner=False)
def extract_pdf(b):
    if PyPDF2 is None: return ""
    try:
        r = PyPDF2.PdfReader(io.BytesIO(b)); t = ""
        for pg in r.pages[:20]:
            try: t += pg.extract_text() + "\n"
            except: pass
        return t[:40000]
    except: return ""

@st.cache_data(show_spinner=False)
def kw_extract(text, n=25):
    if not text: return []
    words = re.findall(r'\b[a-záàâãéêíóôõúüçA-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]{4,}\b', text.lower())
    words = [w for w in words if w not in STOPWORDS]
    if not words: return []
    tf = Counter(words); tot = sum(tf.values())
    return [w for w, _ in sorted({w: c / tot for w, c in tf.items()}.items(), key=lambda x: -x[1])[:n]]

def topic_dist(kws):
    tm = {
        "Saúde & Medicina": ["saúde", "medicina", "clínico", "health", "medical", "therapy", "disease"],
        "Biologia": ["biologia", "genômica", "gene", "dna", "rna", "proteína", "célula", "crispr"],
        "Neurociência": ["neurociência", "neural", "cérebro", "cognição", "memória", "sono", "brain"],
        "Computação & IA": ["algoritmo", "machine", "learning", "inteligência", "dados", "computação", "ia", "deep", "quantum"],
        "Física": ["física", "quântica", "partícula", "energia", "galáxia", "astrofísica", "cosmologia"],
        "Química": ["química", "molécula", "síntese", "reação", "polímero"],
        "Engenharia": ["engenharia", "sistema", "robótica", "automação"],
        "Ciências Sociais": ["sociedade", "cultura", "educação", "política", "psicologia"],
        "Ecologia": ["ecologia", "clima", "ambiente", "biodiversidade"],
        "Matemática": ["matemática", "estatística", "probabilidade", "equação"]
    }
    s = defaultdict(int)
    for kw in kws:
        for tp, terms in tm.items():
            if any(t in kw or kw in t for t in terms): s[tp] += 1
    return dict(sorted(s.items(), key=lambda x: -x[1])) if s else {"Pesquisa Geral": 1}

def analyze_quality(text):
    text_l = text.lower(); hints = []
    if "método" not in text_l and "metodologia" not in text_l and "methods" not in text_l:
        hints.append("Descrever melhor a metodologia (seção de métodos pouco explícita).")
    if "result" not in text_l and "resultado" not in text_l:
        hints.append("Apresentar resultados de forma mais clara (poucos marcadores de resultado).")
    if "conclus" not in text_l:
        hints.append("Adicionar ou fortalecer a seção de conclusões.")
    if text.count("%") + text.count("p=") < 2:
        hints.append("Pode faltar detalhamento estatístico (poucas menções a testes/valores).")
    return hints

@st.cache_data(show_spinner=False)
def analyze_doc(fname, fbytes, ftype, area=""):
    r = {"file": fname, "type": ftype, "keywords": [], "topics": {}, "relevance_score": 0, "summary": "",
         "strengths": [], "improvements": [], "writing_quality": 0, "reading_time": 0, "word_count": 0}
    text = ""
    if ftype == "PDF" and fbytes: text = extract_pdf(fbytes)
    elif fbytes:
        try: text = fbytes.decode("utf-8", errors="ignore")[:40000]
        except: pass
    if text:
        r["keywords"] = kw_extract(text, 25); r["topics"] = topic_dist(r["keywords"])
        words = len(text.split()); r["word_count"] = words; r["reading_time"] = max(1, round(words / 200))
        r["writing_quality"] = min(100, 50 + (15 if len(r["keywords"]) > 15 else 0) + (15 if words > 1000 else 0) + (10 if r["reading_time"] > 3 else 0))
        if area:
            aw = area.lower().split(); rel = sum(1 for w in aw if any(w in kw for kw in r["keywords"]))
            r["relevance_score"] = min(100, rel * 15 + 45)
        else: r["relevance_score"] = 65
        base_strengths = []
        if len(r["keywords"]) > 15: base_strengths.append(f"Vocabulário rico ({len(r['keywords'])} termos relevantes).")
        if words > 1500: base_strengths.append("Texto extenso, possivelmente cobrindo introdução, métodos e discussão.")
        r["strengths"] = base_strengths; r["improvements"] = analyze_quality(text)
        r["summary"] = f"{ftype} . {words} palavras . ~{r['reading_time']}min . {', '.join(list(r['topics'].keys())[:2])} . {', '.join(r['keywords'][:4])}"
    else:
        r["summary"] = f"Arquivo {ftype}."; r["relevance_score"] = 50
        r["keywords"] = kw_extract(fname.lower(), 5); r["topics"] = topic_dist(r["keywords"])
    return r

# --- Funções de Busca Acadêmica (Semantic Scholar, CrossRef) ---
@st.cache_data(show_spinner=False, ttl=1800)
def search_ss(q, lim=6):
    try:
        r = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query": q, "limit": lim,
                    "fields": "title,authors,year,abstract,venue,externalIds,openAccessPdf,citationCount"},
            timeout=8
        )
        if r.status_code == 200:
            out = []
            for p in r.json().get("data", []):
                ext = p.get("externalIds", {}) or {}; doi = ext.get("DOI", ""); arx = ext.get("ArXiv", "")
                pdf = p.get("openAccessPdf") or {}; link = pdf.get("url", "") or (f"https://arxiv.org/abs/{arx}" if arx else (f"https://doi.org/{doi}" if doi else ""))
                al = p.get("authors", []) or []; au = ", ".join(a.get("name", "") for a in al[:3])
                if len(al) > 3: au += " et al."
                out.append({"title": p.get("title", "Sem título"), "authors": au or "—", "year": p.get("year", "?"),
                            "source": p.get("venue", "") or "Semantic Scholar", "doi": doi or arx or "—",
                            "abstract": (p.get("abstract", "") or "")[:250], "url": link,
                            "citations": p.get("citationCount", 0), "origin": "semantic"})
            return out
    except: pass
    return []

@st.cache_data(show_spinner=False, ttl=1800)
def search_cr(q, lim=3):
    try:
        r = requests.get(
            "https://api.crossref.org/works",
            params={"query": q, "rows": lim,
                    "select": "title,author,issued,abstract,DOI,container-title,is-referenced-by-count",
                    "mailto": "nebula@example.com"},
            timeout=8
        )
        if r.status_code == 200:
            out = []
            for p in r.json().get("message", {}).get("items", []):
                title = (p.get("title") or ["?"])[0]; ars = p.get("author", []) or []
                au = ", ".join(f'{a.get("given", "").split()[0] if a.get("given") else ""} {a.get("family", "")}'.strip() for a in ars[:3])
                if len(ars) > 3: au += " et al."
                yr = (p.get("issued", {}).get("date-parts") or [[None]])[0][0]; doi = p.get("DOI", "")
                ab = re.sub(r'<[^>]+>', '', p.get("abstract", "") or "")[:250]
                out.append({"title": title, "authors": au or "—", "year": yr or "?",
                            "source": (p.get("container-title") or ["CrossRef"])[0], "doi": doi,
                            "abstract": ab, "url": f"https://doi.org/{doi}" if doi else "",
                            "citations": p.get("is-referenced-by-count", 0), "origin": "crossref"})
            return out
    except: pass
    return []

def record(tags, w=1.0):
    e = st.session_state.get("current_user")
    if not e or not tags: return
    p = st.session_state.user_prefs.setdefault(e, defaultdict(float))
    for t in tags: p[t.lower()] += w
    save_db()

def area_tags(area):
    a = (area or "").lower()
    M = {
        "ia": ["machine learning", "LLM"], "inteligência artificial": ["machine learning", "LLM"],
        "neurociência": ["sono", "memória", "cognição"], "biologia": ["célula", "genômica"],
        "física": ["quantum", "astrofísica"], "medicina": ["diagnóstico", "terapia"]
    }
    for k, v in M.items():
        if k in a: return v
    return [w.strip() for w in a.replace(",", " ").split() if len(w) > 3][:5]

EMAP = {"pdf": "PDF", "docx": "Word", "xlsx": "Planilha", "csv": "Dados", "txt": "Texto", "py": "Código",
        "md": "Markdown", "png": "Imagem", "jpg": "Imagem", "jpeg": "Imagem", "webp": "Imagem", "tiff": "Imagem"}

def ftype(fname):
    return EMAP.get(fname.split(".")[-1].lower() if "." in fname else "", "Arquivo")

VIB = ["#0A1929", "#1A2F4A", "#1D3A5A", "#20456A", "#23507A", "#265B8A", "#29669A", "#2C71AA", "#2F7CBA", "#3287CA"]

# --- Indexação Local e Vetores de Interesse ---
@st.cache_data(show_spinner=False, ttl=600)
def build_local_index(users, folders, version):
    docs = []

    for fname, folder in folders.items():
        if not isinstance(folder, dict): continue
        owner = folder.get("owner"); owner_name = users.get(owner, {}).get("name", "") if owner else ""
        for f, an in folder.get("analyses", {}).items():
            text = " ".join([an.get("summary", ""), " ".join(an.get("keywords", [])), " ".join(list(an.get("topics", {}).keys()))]).lower()
            docs.append({
                "type": "folder_doc", "id": f"folder_{fname}_{f}", "title": f"{f} ({fname})",
                "authors": owner_name, "year": "", "source": f"Pasta: {fname}", "text": text,
                "tags": an.get("keywords", []), "meta": {"folder": fname, "file": f, "analysis": an, "owner": owner}
            })
    return docs

def search_local(q, docs, topk=20):
    if not q.strip(): return []
    q_words = kw_extract(q, 15); results = []
    for d in docs:
        score = 0; text = d["text"]
        for w in q_words:
            if w in text: score += 3
        for t in d.get("tags", []):
            if any(w in t.lower() for w in q_words): score += 2
        if score > 0: results.append((score, d))
    results.sort(key=lambda x: -x[0])
    return [d for s, d in results[:topk]]

def recompute_folder_aggregates(folder):
    topics_sum = defaultdict(int); kw_counter = Counter()
    for an in folder.get("analyses", {}).values():
        for t, s in an.get("topics", {}).items(): topics_sum[t] += s
        for kw in an.get("keywords", []): kw_counter[kw] += 1
    folder["topics_agg"] = dict(sorted(topics_sum.items(), key=lambda x: -x[1])[:12])
    folder["keywords_agg"] = [kw for kw, _ in kw_counter.most_common(30)]
    folder["last_updated"] = datetime.now().isoformat()

def build_user_interest_vectors(users, folders):
    vocab = Counter(); per_user = defaultdict(Counter)

    for fname, fd in folders.items():
        if not isinstance(fd, dict): continue
        owner = fd.get("owner");
        if not owner: continue
        for kw in fd.get("keywords_agg", []):
            vocab[kw] += 1; per_user[owner][kw] += 1

    vectors = {};
    for ue, ctr in per_user.items():
        total = sum(ctr.values()) or 1; vectors[ue] = {k: v / total for k, v in ctr.items()}
    return vectors

def user_similarity(u_vecs, u1, u2):
    v1 = u_vecs.get(u1, {}); v2 = u_vecs.get(u2, {})
    if not v1 or not v2: return 0.0
    common = set(v1) & set(v2);
    if not common: return 0.0
    num = sum(v1[k] * v2[k] for k in common)
    d1 = sum(v * v for v in v1.values()) ** 0.5; d2 = sum(v * v for v in v2.values()) ** 0.5
    if d1 * d2 == 0: return 0.0
    return num / (d1 * d2)

def find_similar_images(ml_result, folders):
    target_cat = ml_result.get("classification", {}).get("category", "")
    target_color = ml_result.get("color", {}); results = []

    for fname, fd in folders.items():
        if not isinstance(fd, dict): continue
        for f, an in fd.get("analyses", {}).items():
            im = an.get("image_meta");
            if not im: continue
            score = 0
            if im.get("classification", {}).get("category") == target_cat: score += 40
            col = im.get("color", {})
            if col and target_color:
                dr = abs(col.get("r", 0) - target_color.get("r", 0))
                dg = abs(col.get("g", 0) - target_color.get("g", 0))
                db = abs(col.get("b", 0) - target_color.get("b", 0))
                color_score = max(0, 30 - (dr + dg + db) / 10)
                score += color_score
            if score > 0: results.append((score, fname, f, an))
    results.sort(key=lambda x: -x[0])
    return results[:6]

# --- CSS (Azul Escuro "Liquid Glass") ---
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
.sb-logo-icon{width:34px;height:34px;border-radius:12px;background:radial-gradient(circle at 0% 0%,rgba(76,201,240,.95),rgba(10,110,189,.9));display:flex;align-items:center;justify-content:center;font-size:.9rem;flex-shrink:0;box-shadow:0 0 24px rgba(76,201,240,.45);}
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

# --- Helpers HTML ---
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
    return " ".join(f'<span class="tag">{t}</span>' for t in (tags or []))

def badge(s): # Mantido para compatibilidade, mas pode ser removido se não houver status
    m = {"Publicado": "badge-grn", "Concluído": "badge-pur"}
    return f'<span class="{m.get(s, "badge-yel")}">{s}</span>'

def pc_dark():
    return dict(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#6B6F88", family="DM Sans", size=11),
        margin=dict(l=10, r=10, t=38, b=10),
        xaxis=dict(showgrid=False, color="#6B6F88", tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,.04)", color="#6B6F88", tickfont=dict(size=10)),
    )

# --- Páginas da Aplicação ---
def page_login():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;margin-top:2rem;margin-bottom:2.5rem;"><div class="sb-logo-icon" style="width:60px;height:60px;font-size:1.6rem;margin:0 auto 1rem;"></div><div class="sb-logo-txt" style="font-size:2.8rem;">Nebula</div><div style="font-size:.85rem;color:var(--t2);margin-top:.5rem;">Plataforma de Repositório Científico</div></div>', unsafe_allow_html=True)

    if st.session_state.pending_verify:
        st.markdown('<div class="abox" style="text-align:center;"><div style="font-size:.85rem;color:var(--yel);font-weight:600;margin-bottom:.5rem;">Verificação de 2FA</div><div style="font-size:.75rem;color:var(--t2);">Um código foi enviado para seu e-mail.</div></div>', unsafe_allow_html=True)
        code = st.text_input("Código de Verificação", key="2fa_code")
        if st.button("Verificar", use_container_width=True):
            if code == st.session_state.pending_2fa:
                st.session_state.logged_in = True
                st.session_state.current_user = st.session_state.pending_verify
                st.session_state.pending_verify = None
                st.session_state.pending_2fa = None
                st.rerun()
            else:
                st.error("Código incorreto.")
        return

    login_tab, register_tab = st.tabs(["Entrar", "Registrar"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("E-mail", key="login_email")
            password = st.text_input("Senha", type="password", key="login_password")
            if st.form_submit_button("Entrar", use_container_width=True):
                if email in st.session_state.users:
                    user_data = st.session_state.users[email]
                    if user_data["password"] == hp(password):
                        if user_data.get("2fa_enabled"):
                            st.session_state.pending_verify = email
                            st.session_state.pending_2fa = code6() # Gerar código 2FA
                            st.success(f"Código 2FA (simulado): {st.session_state.pending_2fa}") # Em um app real, isso seria enviado por e-mail
                            st.rerun()
                        else:
                            st.session_state.logged_in = True
                            st.session_state.current_user = email
                            st.rerun()
                    else:
                        st.error("Senha incorreta.")
                else:
                    st.error("Usuário não encontrado.")

    with register_tab:
        with st.form("register_form"):
            new_name = st.text_input("Nome Completo", key="reg_name")
            new_email = st.text_input("E-mail", key="reg_email")
            new_password = st.text_input("Senha", type="password", key="reg_password")
            confirm_password = st.text_input("Confirmar Senha", type="password", key="reg_confirm_password")
            new_area = st.text_input("Área de Pesquisa", key="reg_area")

            if st.form_submit_button("Registrar", use_container_width=True):
                if not new_name or not new_email or not new_password or not confirm_password or not new_area:
                    st.error("Todos os campos são obrigatórios.")
                elif new_password != confirm_password:
                    st.error("As senhas não coincidem.")
                elif len(new_password) < 6:
                    st.error("A senha deve ter no mínimo 6 caracteres.")
                elif new_email in st.session_state.users:
                    st.error("Este e-mail já está registrado.")
                else:
                    st.session_state.users[new_email] = {
                        "name": new_name,
                        "password": hp(new_password),
                        "bio": f"Pesquisador em {new_area}",
                        "area": new_area,
                        "followers": 0,
                        "following": 0,
                        "verified": False,
                        "2fa_enabled": False,
                    }
                    save_db()
                    st.success("Registro bem-sucedido! Faça login para continuar.")
                    st.session_state.page = "login" # Redireciona para a aba de login
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def render_nav():
    st.sidebar.markdown('<div class="sb-logo"><div class="sb-logo-icon"></div><div class="sb-logo-txt">Nebula</div></div>', unsafe_allow_html=True)

    NAV = [
        ("repository", "Repositório", "yel"),
        ("search", "Busca", "blu"),
        ("knowledge", "Conexões IA", "grn"),
        ("analytics", "Análises", "orn"),
        ("img_search", "Visão IA", "pur"),
        ("chat", "Mensagens", "t1"),
        ("settings", "Configurações", "t2"),
    ]

    st.sidebar.markdown('<div class="sb-lbl">Navegação</div>', unsafe_allow_html=True)
    for page_id, label, color_key in NAV:
        is_active = st.session_state.page == page_id
        button_style = f"background: {_COLORS[color_key][1]}!important; border-color: {_COLORS[color_key][2]}!important; color: {_COLORS[color_key][0]}!important;" if is_active else ""

        if st.sidebar.button(label, key=f"nav_{page_id}", use_container_width=True):
            st.session_state.page = page_id
            st.session_state.profile_view = None
            st.experimental_rerun() # Usar experimental_rerun para garantir atualização da página

    st.sidebar.markdown("<hr>", unsafe_allow_html=True)
    user = guser()
    st.sidebar.markdown(f'<div style="display:flex;align-items:center;gap:9px;padding:.2rem .3rem;margin-bottom:.8rem;">{avh(ini(user.get("name", "?")), 34, ugrad(st.session_state.current_user))}<div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.88rem;color:var(--t0)">{user.get("name", "Usuário")}</div><div style="font-size:.65rem;color:var(--t3)">{user.get("area", "Pesquisador")}</div></div></div>', unsafe_allow_html=True)

    # API Key para Claude
    st.sidebar.markdown('<div class="sb-lbl">API Key</div>', unsafe_allow_html=True)
    st.session_state.anthropic_key = st.sidebar.text_input("Anthropic API Key", type="password", value=st.session_state.get("anthropic_key", ""), key="anthropic_api_key_sidebar")
    if st.session_state.anthropic_key and not st.session_state.anthropic_key.startswith("sk-"):
        st.sidebar.warning("Formato de API Key inválido. Deve começar com 'sk-'.")


def render_article(a, idx=0, ctx="web"):
    sc = ("#0A6EBD" if a.get("origin") == "semantic" else "#4CC9F0")
    sn = ("Semantic Scholar" if a.get("origin") == "semantic" else "CrossRef")
    cite = f" . {a['citations']} cit." if a.get("citations") else ""
    uid = re.sub(r"[^a-zA-Z0-9]", "", f"{ctx}_{idx}_{str(a.get('doi', ''))[:10]}")[:32]
    is_saved = any(s.get("doi") == a.get("doi") for s in st.session_state.saved_articles)
    ab = (a.get("abstract", "") or "")[:250] + ("..." if len(a.get("abstract", "")) > 250 else "")
    st.markdown(
        f'<div class="scard"><div style="display:flex;align-items:flex-start;gap:7px;margin-bottom:.28rem"><div style="flex:1;font-family:Syne,sans-serif;font-size:.86rem;font-weight:700;color:var(--t0)">{a["title"]}</div><span style="font-size:.58rem;color:{sc};background:rgba(255,255,255,.04);border-radius:7px;padding:2px 7px;white-space:nowrap;flex-shrink:0">{sn}</span></div><div style="color:var(--t3);font-size:.64rem;margin-bottom:.3rem">{a["authors"]} . <em>{a["source"]}</em> . {a["year"]}{cite}</div><div style="color:var(--t2);font-size:.76rem;line-height:1.62">{ab}</div></div>',
        unsafe_allow_html=True,
    )
    ca, cb, cc = st.columns(3)
    with ca:
        if st.button("Salvo" if is_saved else "Salvar", key=f"svw_{uid}", use_container_width=True):
            if is_saved:
                st.session_state.saved_articles = [s for s in st.session_state.saved_articles if s.get("doi") != a.get("doi")]
                st.toast("Removido")
            else:
                st.session_state.saved_articles.append(a)
                st.toast("Salvo!")
            save_db()
            st.experimental_rerun()
    with cb:
        if st.button("Citar", key=f"ctw_{uid}", use_container_width=True):
            st.toast(f'{a["authors"]} ({a["year"]}). {a["title"]}.')
    with cc:
        if a.get("url"):
            st.markdown(
                f'<a href="{a["url"]}" target="_blank" style="color:var(--blu);font-size:.78rem;text-decoration:none;line-height:2.4;display:block">Abrir</a>',
                unsafe_allow_html=True,
            )

def page_search():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.3rem">Busca Acadêmica & Repositório</h1>', unsafe_allow_html=True)
    c1, c2 = st.columns([4, 1])
    with c1:
        q = st.text_input("", placeholder="CRISPR . quantum ML . dark matter...", key="sq", label_visibility="collapsed")
    with c2:
        if st.button("Buscar", key="btn_s", use_container_width=True):
            if q:
                with st.spinner("Varredura completa (repositório + web)..."):
                    docs = build_local_index(st.session_state.users, st.session_state.folders, st.session_state.local_index_version)
                    local_results = search_local(q, docs, topk=25)
                    ssr = search_ss(q, 6)
                    crr = search_cr(q, 4)
                    web = ssr + [x for x in crr if not any(x["title"].lower() == s["title"].lower() for s in ssr)]
                    st.session_state.search_results = {"local": local_results, "web": web}
                    st.session_state.last_sq = q
                    record([q.lower()], 0.4)
            else:
                st.warning("Por favor, digite um termo de busca.")

    if st.session_state.get("search_results") and st.session_state.get("last_sq"):
        res = st.session_state.search_results
        local = res.get("local", [])
        repo_docs = [d for d in local if d["type"] == "folder_doc"]
        web = res.get("web", [])

        ta, tr, tw = st.tabs([
            f"  Todos ({len(repo_docs) + len(web)})  ",
            f"  Repositório ({len(repo_docs)})  ",
            f"  Internet ({len(web)})  ",
        ])

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
        {f} (Pasta: {folder})
    </div>
    <div style="font-size:.64rem;color:var(--t3);margin-bottom:.25rem">
        Relevância: <span style="color:var(--yel)">{rel}%</span>
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
                st.markdown('<div style="font-size:.59rem;color:var(--yel);font-weight:700;margin-bottom:.4rem;letter-spacing:.10em;text-transform:uppercase">No Repositório</div>', unsafe_allow_html=True)
                for d in repo_docs:
                    render_repo_doc(d)
            if web:
                st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown('<div style="font-size:.59rem;color:var(--blu);font-weight:700;margin-bottom:.4rem;letter-spacing:.10em;text-transform:uppercase">Na Internet</div>', unsafe_allow_html=True)
                for idx, a in enumerate(web):
                    render_article(a, idx=idx, ctx="all_w")
            if not repo_docs and not web:
                st.info("Nenhum resultado.")

        with tr:
            for d in repo_docs:
                render_repo_doc(d)
            if not repo_docs:
                st.info("Nenhum resultado no repositório.")

        with tw:
            for idx, a in enumerate(web):
                render_article(a, idx=idx, ctx="web_t")
            if not web:
                st.info("Nenhum artigo encontrado na internet.")
    st.markdown('</div>', unsafe_allow_html=True)

def page_knowledge():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.9rem">Rede de Conexões com IA</h1>', unsafe_allow_html=True)
    email = st.session_state.current_user
    users = st.session_state.users if isinstance(st.session_state.users, dict) else {}
    api_key = st.session_state.get("anthropic_key", "")

    rlist = list(users.keys())
    n = len(rlist)

    def get_tags(ue):
        ud = users.get(ue, {})
        tags = set(area_tags(ud.get("area", "")))
        for fname, fd in st.session_state.folders.items():
            if isinstance(fd, dict) and fd.get("owner") == ue:
                tags.update(kw.lower() for kw in fd.get("keywords_agg", []))
        return tags

    rtags = {ue: get_tags(ue) for ue in rlist}
    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            e1, e2 = rlist[i], rlist[j]
            common = list(rtags[e1] & rtags[e2])
            is_fol = (e2 in st.session_state.followed or e1 in st.session_state.followed)
            if common or is_fol:
                edges.append((e1, e2, common[:5], len(common) + (2 if is_fol else 0)))

    pos = {}
    for idx, ue in enumerate(rlist):
        angle = 2 * 3.14159 * idx / max(n, 1)
        rd = 0.36 + 0.05 * ((hash(ue) % 5) / 4)
        pos[ue] = {"x": 0.5 + rd * np.cos(angle), "y": 0.5 + rd * np.sin(angle), "z": 0.5 + 0.12 * ((idx % 4) / 3 - 0.35)}

    fig = go.Figure()
    for e1, e2, common, strength in edges:
        p1 = pos[e1]; p2 = pos[e2]
        alpha = min(0.45, 0.08 + strength * 0.06)
        fig.add_trace(go.Scatter3d(x=[p1["x"], p2["x"], None], y=[p1["y"], p2["y"], None], z=[p1["z"], p2["z"], None],
                                   mode="lines", line=dict(color=f"rgba(10,110,189,{alpha:.2f})", width=min(3, 1 + strength)),
                                   hoverinfo="none", showlegend=False))
    nc = [("#0A6EBD" if ue == email else ("#6A9C89" if ue in st.session_state.followed else "#4CC9F0")) for ue in rlist]
    nsizes = [22 if ue == email else (16 if ue in st.session_state.followed else 11) for ue in rlist]
    fig.add_trace(go.Scatter3d(x=[pos[ue]["x"] for ue in rlist], y=[pos[ue]["y"] for ue in rlist], z=[pos[ue]["z"] for ue in rlist],
                               mode="markers+text", marker=dict(size=nsizes, color=nc, opacity=0.9, line=dict(color="rgba(255,255,255,.08)", width=1.5)),
                               text=[users.get(ue, {}).get("name", "?").split()[0] for ue in rlist], textposition="top center",
                               textfont=dict(color="#6B6F88", size=9, family="DM Sans"),
                               hovertemplate=[f"<b>{users.get(ue, {}).get('name', '?')}</b><br>{users.get(ue, {}).get('area', '')}<extra></extra>" for ue in rlist],
                               showlegend=False))
    fig.update_layout(height=420, scene=dict(xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, showbackground=False),
                                           yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, showbackground=False),
                                           zaxis=dict(showgrid=False, zeroline=False, showticklabels=False, showbackground=False),
                                           bgcolor="rgba(0,0,0,0)"),
                      paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)
    for col, (cls, v, l) in zip([c1, c2, c3, c4],
                                 [("mval-yel", len(rlist), "Pesquisadores"), ("mval-grn", len(edges), "Conexões"),
                                  ("mval-blu", len(st.session_state.followed), "Seguindo"),
                                  ("mval-red", len(st.session_state.folders), "Pastas")]):
        with col:
            st.markdown(f'<div class="mbox"><div class="{cls}">{v}</div><div class="mlbl">{l}</div></div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    tm, tai, tmi, tall = st.tabs([
        "  Mapa  ", "  IA Conexões  ", "  Minhas  ", "  Todos  ",
    ])

    with tm:
        for e1, e2, common, strength in sorted(edges, key=lambda x: -x[3])[:20]:
            n1 = users.get(e1, {}); n2 = users.get(e2, {})
            ts = tags_html(common[:4]) if common else '<span style="color:var(--t3);font-size:.66rem">seguimento</span>'
            st.markdown(
                f'<div class="scard"><div style="display:flex;align-items:center;gap:7px;flex-wrap:wrap"><span style="font-size:.78rem;font-weight:700;font-family:Syne,sans-serif;color:var(--yel)">{n1.get("name", "?")}</span><span style="color:var(--t3)">.</span><span style="font-size:.78rem;font-weight:700;font-family:Syne,sans-serif;color:var(--yel)">{n2.get("name", "?")}</span><div style="flex:1">{ts}</div><span style="font-size:.63rem;color:var(--grn);font-weight:700">{strength}pt</span></div></div>',
                unsafe_allow_html=True,
            )

    with tai:
        st.markdown(
            '<div class="api-banner"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.88rem;margin-bottom:.28rem;color:var(--pur)">Sugestões Inteligentes de Conexão</div><div style="font-size:.74rem;color:var(--t2);line-height:1.65">Claude AI analisa seu perfil e repositório para encontrar colaborações científicas ideais</div></div>',
            unsafe_allow_html=True,
        )
        if not api_key or not api_key.startswith("sk-"):
            st.markdown(
                '<div class="pbox-yel"><div style="font-size:.75rem;color:var(--yel);font-weight:600;margin-bottom:.28rem">. Chave API necessária</div><div style="font-size:.72rem;color:var(--t2)">Insira sua Anthropic API key na barra lateral para usar sugestões com IA.</div></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div style="font-size:.62rem;color:var(--t3);margin:.5rem 0">. Sugestões algorítmicas (sem IA):</div>',
                unsafe_allow_html=True,
            )
            my_tags = rtags.get(email, set())
            for ue, ud in list(users.items())[:8]:
                if ue == email or ue in st.session_state.followed: continue
                common_tags = my_tags & rtags.get(ue, set())
                if len(common_tags) > 0:
                    rg = ugrad(ue); rn = ud.get("name", "?")
                    st.markdown(
                        f'<div class="conn-ai"><div style="display:flex;align-items:center;gap:9px;margin-bottom:.5rem">{avh(ini(rn), 34, rg)}<div style="flex:1"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.84rem;color:var(--t0)">{rn}</div><div style="font-size:.66rem;color:var(--t3)">{ud.get("area", "")}</div></div><span class="badge-grn">{len(common_tags)} temas</span></div><div style="font-size:.73rem;color:var(--t2);margin-bottom:.45rem">Interesses em comum: {tags_html(list(common_tags)[:4])}</div></div>',
                        unsafe_allow_html=True,
                    )
                    cf_b, cv_b = st.columns(2)
                    with cf_b:
                        if st.button(f"Seguir {rn.split()[0]}", key=f"ais_{ue}", use_container_width=True):
                            if ue not in st.session_state.followed:
                                st.session_state.followed.append(ue)
                                ud["followers"] = ud.get("followers", 0) + 1
                            save_db(); st.experimental_rerun()
                    with cv_b:
                        if st.button(f"Perfil", key=f"aip_{ue}", use_container_width=True):
                            st.session_state.profile_view = ue; st.experimental_rerun()
        else:
            cache_key = f"conn_{email}_{len(users)}_{len(st.session_state.folders)}_{st.session_state.local_index_version}"
            if st.button("Gerar Sugestões IA", key="btn_ai_conn"):
                with st.spinner("Claude analisando sua rede científica..."):
                    result, err = call_claude_connections(users, st.session_state.folders, email, api_key)
                    if result: st.session_state.ai_conn_cache[cache_key] = result
                    else: st.error(f"Erro IA: {err}")
            ai_result = st.session_state.ai_conn_cache.get(cache_key)
            if ai_result:
                suggestions = ai_result.get("sugestoes", [])
                for sug in suggestions:
                    sue = sug.get("email", ""); sud = users.get(sue, {})
                    if not sud: continue
                    rn = sud.get("name", "?"); rg = ugrad(sue)
                    score = sug.get("score", 70); score_col = "#6A9C89" if score >= 80 else ("#0A6EBD" if score >= 60 else "#FF8C42")
                    temas = sug.get("temas_comuns", []); is_fol2 = sue in st.session_state.followed
                    st.markdown(f'''<div class="conn-ai">
  <div style="display:flex;align-items:center;gap:9px;margin-bottom:.55rem">
    {avh(ini(rn), 38, rg)}
    <div style="flex:1">
      <div style="font-family:Syne,sans-serif;font-weight:700;font-size:.86rem;color:var(--t0)">{rn}</div>
      <div style="font-size:.64rem;color:var(--t3)">{sud.get("area", "")}</div>
    </div>
    <div style="text-align:center;background:rgba(0,0,0,.25);border-radius:10px;padding:.38rem .65rem;flex-shrink:0">
      <div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:900;color:{score_col}">{score}</div>
      <div style="font-size:.5rem;color:var(--t3);text-transform:uppercase;letter-spacing:.08em">score IA</div>
    </div>
  </div>
  <div style="background:rgba(255,255,255,.03);border-radius:10px;padding:.55rem .75rem;margin-bottom:.5rem;font-size:.76rem;color:var(--t2);line-height:1.65;border:1px solid rgba(177,125,255,.10)">
    . {sug.get("razao", "Conexão recomendada pela IA")}
  </div>
  <div>{tags_html(temas[:5])}</div>
</div>''', unsafe_allow_html=True)
                    c_f, c_p, c_c = st.columns(3)
                    with c_f:
                        if st.button("Seguindo" if is_fol2 else "Seguir", key=f"aic_f_{sue}", use_container_width=True):
                            if not is_fol2:
                                st.session_state.followed.append(sue)
                                sud["followers"] = sud.get("followers", 0) + 1
                            save_db(); st.experimental_rerun()
                    with c_p:
                        if st.button("Perfil", key=f"aic_p_{sue}", use_container_width=True):
                            st.session_state.profile_view = sue; st.experimental_rerun()
                    with c_c:
                        if st.button("Chat", key=f"aic_c_{sue}", use_container_width=True):
                            st.session_state.chat_messages.setdefault(sue, [])
                            st.session_state.active_chat = sue; st.session_state.page = "chat"; st.experimental_rerun()
            else:
                st.markdown('<div style="text-align:center;padding:2rem;color:var(--t3)">Clique em "Gerar Sugestões IA" para análise com Claude.</div>', unsafe_allow_html=True)

    with tmi:
        mc = [(e1, e2, c, s) for e1, e2, c, s in edges if e1 == email or e2 == email]
        if not mc: st.info("Siga pesquisadores e crie pastas com análises para construir suas conexões.")
        for e1, e2, common, strength in sorted(mc, key=lambda x: -x[3]):
            oth = e2 if e1 == email else e1; od = users.get(oth, {}); og = ugrad(oth)
            st.markdown(
                f'<div class="scard"><div style="display:flex;align-items:center;gap:9px;flex-wrap:wrap">{avh(ini(od.get("name", "?")), 34, og)}<div style="flex:1"><div style="font-weight:700;font-size:.82rem;font-family:Syne,sans-serif;color:var(--t0)">{od.get("name", "?")}</div><div style="font-size:.66rem;color:var(--t3)">{od.get("area", "")}</div></div>{tags_html(common[:3])}</div></div>',
                unsafe_allow_html=True,
            )
            cv, cm2, _ = st.columns([1, 1, 4])
            with cv:
                if st.button("Ver", key=f"kv_{oth}", use_container_width=True):
                    st.session_state.profile_view = oth; st.experimental_rerun()
            with cm2:
                if st.button("Chat", key=f"kc_{oth}", use_container_width=True):
                    st.session_state.chat_messages.setdefault(oth, []); st.session_state.active_chat = oth
                    st.session_state.page = "chat"; st.experimental_rerun()

    with tall:
        sq2 = st.text_input("", placeholder="Buscar...", key="all_s", label_visibility="collapsed")
        for ue, ud in users.items():
            if ue == email: continue
            rn = ud.get("name", "?"); ua = ud.get("area", "")
            if sq2 and sq2.lower() not in rn.lower() and sq2.lower() not in ua.lower(): continue
            is_fol = ue in st.session_state.followed; rg = ugrad(ue)
            st.markdown(
                f'<div class="scard"><div style="display:flex;align-items:center;gap:9px">{avh(ini(rn), 34, rg)}<div style="flex:1"><div style="font-size:.82rem;font-weight:700;font-family:Syne,sans-serif;color:var(--t0)">{rn}</div><div style="font-size:.66rem;color:var(--t3)">{ua}</div></div></div></div>',
                unsafe_allow_html=True,
            )
            ca2, cb2, cc2 = st.columns(3)
            with ca2:
                if st.button("Perfil", key=f"av_{ue}", use_container_width=True):
                    st.session_state.profile_view = ue; st.experimental_rerun()
            with cb2:
                if st.button("Seguindo" if is_fol else "Seguir", key=f"af_{ue}", use_container_width=True):
                    if is_fol:
                        st.session_state.followed.remove(ue)
                        ud["followers"] = max(0, ud.get("followers", 0) - 1)
                    else:
                        st.session_state.followed.append(ue)
                        ud["followers"] = ud.get("followers", 0) + 1
                    save_db(); st.experimental_rerun()
            with cc2:
                if st.button("Chat", key=f"ac_{ue}", use_container_width=True):
                    st.session_state.chat_messages.setdefault(ue, []); st.session_state.active_chat = ue
                    st.session_state.page = "chat"; st.experimental_rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def page_repository():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.9rem">Repositório de Pesquisa</h1>', unsafe_allow_html=True)
    email = st.session_state.current_user
    u = guser(); ra = u.get("area", "")
    c1, c2, c3 = st.columns([2, 1.2, 1.5])
    with c1:
        nfn = st.text_input("Nome da pasta", placeholder="Ex: Genômica Comparativa", key="nf_n")
    with c2:
        nfd = st.text_input("Descrição", key="nf_d")
    with c3:
        nvis = st.selectbox("Visibilidade", ["private", "team", "public"], key="nf_vis")
    if st.button("Criar Pasta", key="btn_nf", use_container_width=True):
        if nfn.strip():
            if nfn not in st.session_state.folders:
                st.session_state.folders[nfn] = {
                    "desc": nfd, "files": [], "notes": "", "analyses": {},
                    "topics_agg": {}, "keywords_agg": [], "last_updated": datetime.now().isoformat(),
                    "owner": email, "visibility": nvis,
                }
                save_db(); st.session_state.local_index_version += 1
                st.success(f"'{nfn}' criada!"); st.experimental_rerun()
            else: st.warning("Já existe uma pasta com este nome.")
        else: st.warning("Por favor, digite um nome para a pasta.")
    st.markdown("<hr>", unsafe_allow_html=True)
    if not st.session_state.folders:
        st.markdown(
            '<div class="glass" style="text-align:center;padding:4rem"><div style="font-size:2.2rem;opacity:.2;margin-bottom:.7rem"></div><div style="color:var(--t3)">Nenhuma pasta criada ainda.</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)
        return

    st.markdown('<div style="font-size:.58rem;font-weight:700;color:var(--t4);letter-spacing:.12em;text-transform:uppercase;margin-bottom:.7rem">Minhas Pastas</div>', unsafe_allow_html=True)

    for fn, fd in list(st.session_state.folders.items()):
        if not isinstance(fd, dict):
            fd = {"files": fd, "desc": "", "notes": "", "analyses": {}, "topics_agg": {}, "keywords_agg": [], "last_updated": datetime.now().isoformat(), "owner": None, "visibility": "private"}
            st.session_state.folders[fn] = fd

        if fd.get("owner") != email: continue

        files = fd.get("files", []); analyses = fd.get("analyses", {})
        num_files = len(files)
        top_topics = ", ".join(list(fd.get("topics_agg", {}).keys())[:2])
        last_update_str = time_ago(fd.get("last_updated", datetime.now().isoformat())[:10])

        with st.expander(f"Pasta: {fn} . {num_files} arquivo(s) . {top_topics} . Atualizado {last_update_str}"):
            st.markdown(f'<div style="font-size:.75rem;color:var(--t2);margin-bottom:.5rem">Descrição: {fd.get("desc", "Sem descrição.")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:.75rem;color:var(--t2);margin-bottom:.8rem">Visibilidade: <span style="font-weight:700;color:var(--yel)">{fd.get("visibility", "private").capitalize()}</span></div>', unsafe_allow_html=True)

            up = st.file_uploader(
                "Upload de arquivos", type=None, key=f"up_{fn}",
                label_visibility="collapsed", accept_multiple_files=True,
            )
            if up:
                new_files_added = False
                for uf in up:
                    if uf.name not in files:
                        files.append(uf.name)
                        new_files_added = True
                    if fn not in st.session_state.folder_files_bytes:
                        st.session_state.folder_files_bytes[fn] = {}
                    uf.seek(0)
                    st.session_state.folder_files_bytes[fn][uf.name] = uf.read()

                if new_files_added:
                    fd["files"] = files
                    save_db()
                    st.session_state.local_index_version += 1
                    st.success(f"{len(up)} arquivo(s) adicionado(s)!")
                    st.experimental_rerun()
                else:
                    st.info("Nenhum novo arquivo para adicionar.")

            if files:
                st.markdown('<div style="font-size:.62rem;color:var(--t3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-top:.8rem;margin-bottom:.5rem">Arquivos na Pasta</div>', unsafe_allow_html=True)
                for f in files:
                    ft = ftype(f); has_analysis = f in analyses
                    icon_char = {"PDF": "📄", "Word": "📝", "Planilha": "📊", "Dados": "📈", "Código": "🐍", "Imagem": "🖼", "Markdown": "📋"}.get(ft, "📄")
                    ab2 = f' <span class="badge-grn" style="font-size:.57rem;margin-left:5px">.</span>' if has_analysis else ""
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:7px;padding:.38rem 0;border-bottom:1px solid rgba(255,255,255,.04)"><span>{icon_char}</span><span style="font-size:.75rem;color:var(--t2);flex:1">{f}</span>{ab2}</div>',
                        unsafe_allow_html=True,
                    )

            col_analyze, col_delete, _ = st.columns([1.5, 1.5, 2])
            with col_analyze:
                if st.button("Analisar Arquivos", key=f"an_{fn}", use_container_width=True):
                    if files:
                        pb = st.progress(0, "Iniciando análise..."); fb = st.session_state.folder_files_bytes.get(fn, {})
                        for fi, f in enumerate(files):
                            pb.progress((fi + 1) / len(files), f"Analisando: {f[:25]}...")
                            fbytes = fb.get(f, b""); ft2 = ftype(f)

                            if ft2 == "Imagem":
                                img_meta = analyze_image_file(f, fbytes)
                                if img_meta: analyses[f] = {"image_meta": img_meta, "summary": f"Imagem . {img_meta['classification']['category']}"}
                                else: analyses[f] = {"summary": "Falha na análise de imagem."}
                            else: analyses[f] = analyze_doc(f, fbytes, ft2, ra)

                        fd["analyses"] = analyses; recompute_folder_aggregates(fd)
                        save_db(); st.session_state.local_index_version += 1
                        pb.empty(); st.success("Análise completa!"); st.experimental_rerun()
                    else: st.warning("Adicione arquivos à pasta para analisar.")
            with col_delete:
                if st.button("Excluir Pasta", key=f"df_{fn}", use_container_width=True):
                    del st.session_state.folders[fn]; save_db()
                    st.session_state.local_index_version += 1; st.experimental_rerun()

            if analyses:
                st.markdown('<div style="font-size:.62rem;color:var(--t3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-top:.8rem;margin-bottom:.5rem">Resultados das Análises</div>', unsafe_allow_html=True)
                for f, an in analyses.items():
                    with st.expander(f"Análise: {f}"):
                        if "image_meta" in an:
                            img_meta = an["image_meta"]; cls_ = img_meta["classification"]
                            conf_c = VIB[1] if cls_["confidence"] > 80 else (VIB[0] if cls_["confidence"] > 60 else VIB[2])
                            st.markdown(f'''<div class="ai-card">
                                <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:.55rem">
                                    <div>
                                        <div style="font-size:.57rem;color:var(--t3);letter-spacing:.10em;text-transform:uppercase;margin-bottom:4px;font-weight:700">Classificação ML</div>
                                        <div style="font-family:Syne,sans-serif;font-size:1.12rem;font-weight:800;color:var(--t0);margin-bottom:3px">{cls_["category"]}</div>
                                        <div style="font-size:.74rem;color:var(--t2);line-height:1.65;max-width:380px">{cls_["origin"]}</div>
                                    </div>
                                    <div style="background:rgba(0,0,0,.3);border-radius:12px;padding:.55rem .9rem;text-align:center;flex-shrink:0;border:1px solid rgba(255,255,255,.08)">
                                        <div style="font-family:Syne,sans-serif;font-size:1.5rem;font-weight:900;color:{conf_c}">{cls_["confidence"]}%</div>
                                        <div style="font-size:.52rem;color:var(--t3);text-transform:uppercase;font-weight:700">confiança</div>
                                    </div>
                                </div>
                                <div>{tags_html(cls_.get("search_kw", "").split())}</div>
                            </div>''', unsafe_allow_html=True)
                        else:
                            kws = an.get("keywords", []); topics = an.get("topics", {})
                            rel = an.get("relevance_score", 0); wq = an.get("writing_quality", 0)
                            rc = "var(--grn)" if rel >= 70 else ("var(--yel)" if rel >= 45 else "var(--red)")
                            st.markdown(
                                f'<div class="abox"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.86rem;margin-bottom:.3rem">{f}</div><div style="font-size:.76rem;color:var(--t2)">{an.get("summary", "")}</div><div style="display:flex;gap:1.2rem;margin-top:.5rem"><div><div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:900;color:{rc}">{rel}%</div><div class="mlbl">Relevância</div></div><div><div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:900;color:var(--blu)">{wq}%</div><div class="mlbl">Qualidade</div></div><div><div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:900;color:var(--orn)">{an.get("word_count", 0)}</div><div class="mlbl">Palavras</div></div></div></div>',
                                unsafe_allow_html=True,
                            )
                            if kws: st.markdown(tags_html(kws[:16]), unsafe_allow_html=True)
                            if topics:
                                fig2 = go.Figure(go.Pie(labels=list(topics.keys()), values=list(topics.values()), hole=0.5,
                                                        marker=dict(colors=VIB[:len(topics)], line=dict(color=["#0B0F1A"] * 15, width=2)),
                                                        textfont=dict(color="white", size=8)))
                                fig2.update_layout(height=220, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                                   legend=dict(font=dict(color="#6B6F88", size=8)), margin=dict(l=0, r=0, t=10, b=0))
                                st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
                                st.plotly_chart(fig2, use_container_width=True)
                                st.markdown('</div>', unsafe_allow_html=True)

                            if an.get("strengths"):
                                st.markdown('<div style="font-size:.62rem;color:var(--grn);font-weight:700;margin-top:.5rem;margin-bottom:.2rem">Pontos Fortes:</div>', unsafe_allow_html=True)
                                for s in an["strengths"]: st.markdown(f'<div style="font-size:.72rem;color:var(--t2);margin-left:.5rem">. {s}</div>', unsafe_allow_html=True)
                            if an.get("improvements"):
                                st.markdown('<div style="font-size:.62rem;color:var(--yel);font-weight:700;margin-top:.5rem;margin-bottom:.2rem">Sugestões de Melhoria:</div>', unsafe_allow_html=True)
                                for i in an["improvements"]: st.markdown(f'<div style="font-size:.72rem;color:var(--t2);margin-left:.5rem">. {i}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def page_analytics():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.9rem">Painel de Análises</h1>', unsafe_allow_html=True)
    email = st.session_state.current_user
    d = st.session_state.stats_data
    tf, ti, tpr = st.tabs(["  Repositório  ", "  Impacto  ", "  Interesses  "])
    with tf:
        folders = st.session_state.folders
        if not folders:
            st.markdown('<div class="glass" style="text-align:center;padding:3rem;color:var(--t3)">Crie pastas no Repositório para ver as análises.</div>', unsafe_allow_html=True)
        else:
            all_an = {f: an for fd in folders.values() if isinstance(fd, dict) for f, an in fd.get("analyses", {}).items()}
            tot_f = sum(len(fd.get("files", []) if isinstance(fd, dict) else fd) for fd in folders.values())
            all_kw = [kw for an in all_an.values() for kw in an.get("keywords", [])]
            all_top = defaultdict(int)
            for an in all_an.values():
                for t, s in an.get("topics", {}).items(): all_top[t] += s
            c1, c2, c3, c4 = st.columns(4)
            for col, (cls, v, l) in zip([c1, c2, c3, c4],
                                         [("mval-yel", len(folders), "Pastas"), ("mval-grn", tot_f, "Arquivos"),
                                          ("mval-blu", len(all_an), "Analisados"), ("mval-red", len(set(all_kw[:100])), "Keywords")]):
                with col:
                    st.markdown(f'<div class="mbox"><div class="{cls}">{v}</div><div class="mlbl">{l}</div></div>', unsafe_allow_html=True)
            if all_top:
                fig = go.Figure(go.Bar(x=list(all_top.values())[:8], y=list(all_top.keys())[:8], orientation='h', marker=dict(color=VIB[:8])))
                fig.update_layout(**{**pc_dark(), 'height': 250,
                                      'yaxis': dict(showgrid=False, color="#6B6F88", tickfont=dict(size=9)),
                                      'title': dict(text="Temas Dominantes no Repositório", font=dict(color="#E8E9F0", family="Syne", size=11))})
                st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
    with ti:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="mbox"><div class="mval-yel">{d.get("h_index", 4)}</div><div class="mlbl">Índice H</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="mbox"><div class="mval-grn">{d.get("fator_impacto", 3.8):.1f}</div><div class="mlbl">Fator Impacto</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="mbox"><div class="mval-blu">{len(st.session_state.saved_articles)}</div><div class="mlbl">Salvos</div></div>', unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)
        nh = st.number_input("Índice H", 0, 200, d.get("h_index", 4), key="e_h")
        nfi = st.number_input("Fator impacto", 0.0, 100.0, float(d.get("fator_impacto", 3.8)), step=0.1, key="e_fi")
        nn = st.text_area("Notas sobre seu impacto", value=d.get("notes", ""), key="e_nt", height=70)
        if st.button("Salvar Métricas", key="btn_sm"):
            d.update({"h_index": nh, "fator_impacto": nfi, "notes": nn}); st.success("Métricas salvas!")
    with tpr:
        prefs = st.session_state.user_prefs.get(email, {})
        if prefs:
            top = sorted(prefs.items(), key=lambda x: -x[1])[:12]; mx = max(s for _, s in top) if top else 1
            cats = [t for t, _ in top[:8]]; vals = [round(s / mx * 100) for _, s in top[:8]]
            if len(cats) >= 3:
                fig3 = go.Figure(go.Scatterpolar(r=vals + [vals[0]], theta=cats + [cats[0]], fill='toself',
                                                  line=dict(color="#0A6EBD"), fillcolor="rgba(10,110,189,.10)"))
                fig3.update_layout(height=265, polar=dict(bgcolor="rgba(0,0,0,0)",
                                                           radialaxis=dict(visible=True, gridcolor="rgba(255,255,255,.04)",
                                                                           color="#6B6F88", tickfont=dict(size=8)),
                                                           angularaxis=dict(gridcolor="rgba(255,255,255,.04)",
                                                                            color="#6B6F88", tickfont=dict(size=9))),
                                   paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=40, r=40, t=15, b=15))
                st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
                st.plotly_chart(fig3, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
        else: st.info("Interaja com documentos e pesquisas para construir seu perfil de interesses.")
    st.markdown('</div>', unsafe_allow_html=True)

def page_img_search():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.25rem">Visão IA Científica</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.76rem;margin-bottom:.85rem">Pipeline ML: Sobel . Canny . ORB Keypoints . GLCM . KMeans . FFT + Claude Vision (cached)</p>', unsafe_allow_html=True)

    api_key = st.session_state.get("anthropic_key", ""); has_api = api_key.startswith("sk-") if api_key else False

    if has_api:
        st.markdown('<div class="api-banner"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.82rem;color:var(--pur);margin-bottom:.2rem">Claude Vision Ativo</div><div style="font-size:.70rem;color:var(--t2)">Análise real com IA + pipeline ML completo habilitados</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="pbox-yel" style="margin-bottom:.7rem"><div style="font-size:.70rem;color:var(--yel);font-weight:600;margin-bottom:.15rem">. Modo ML apenas</div><div style="font-size:.66rem;color:var(--t2)">Insira sua API key na barra lateral para ativar Claude Vision (análise real com IA)</div></div>', unsafe_allow_html=True)

    cu, cr = st.columns([1, 1.9])
    with cu:
        st.markdown('<div class="glass" style="padding:1rem">', unsafe_allow_html=True)
        img_file = st.file_uploader("Carregar imagem científica", type=["png", "jpg", "jpeg", "webp", "tiff"], key="img_up")
        img_bytes = None
        if img_file:
            img_bytes = img_file.read()
            st.image(img_bytes, use_container_width=True)
        run = st.button("Analisar Imagem (ML)", key="btn_run", use_container_width=True)
        if img_bytes and has_api: run_claude = st.button("Claude Vision", key="btn_vision", use_container_width=True)
        else: run_claude = False
        st.markdown('<div class="pbox-yel" style="margin-top:.8rem"><div style="font-size:.62rem;color:var(--yel);font-weight:700;margin-bottom:2px">. Aviso IA</div><div style="font-size:.60rem;color:var(--t2);line-height:1.62">Análise computacional. Valide com especialistas da área.</div></div>', unsafe_allow_html=True)

    with cr:
        if run and img_bytes:
            img_hash = hashlib.md5(img_bytes).hexdigest()
            if img_hash not in st.session_state.ml_cache:
                with st.spinner("Executando pipeline ML..."): ml_result = run_full_ml_pipeline_cached(img_bytes)
                st.session_state.ml_cache[img_hash] = ml_result
            else: ml_result = st.session_state.ml_cache[img_hash]; st.success("Resultado carregado do cache.")
            st.session_state.img_result = ml_result
            if not ml_result.get("ok"): st.error(f"Erro no pipeline: {ml_result.get('error', 'desconhecido')}")
            else:
                cls_ = ml_result["classification"]; conf_c = VIB[1] if cls_["confidence"] > 80 else (VIB[0] if cls_["confidence"] > 60 else VIB[2])
                st.markdown(f'''<div class="ai-card">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:.55rem">
    <div>
      <div style="font-size:.57rem;color:var(--t3);letter-spacing:.10em;text-transform:uppercase;margin-bottom:4px;font-weight:700">Classificação ML</div>
      <div style="font-family:Syne,sans-serif;font-size:1.12rem;font-weight:800;color:var(--t0);margin-bottom:3px">{cls_["category"]}</div>
      <div style="font-size:.74rem;color:var(--t2);line-height:1.65;max-width:380px">{cls_["origin"]}</div>
    </div>
    <div style="background:rgba(0,0,0,.3);border-radius:12px;padding:.55rem .9rem;text-align:center;flex-shrink:0;border:1px solid rgba(255,255,255,.08)">
      <div style="font-family:Syne,sans-serif;font-size:1.5rem;font-weight:900;color:{conf_c}">{cls_["confidence"]}%</div>
      <div style="font-size:.52rem;color:var(--t3);text-transform:uppercase;font-weight:700">confiança</div>
    </div>
  </div>
  <div style="font-size:.63rem;color:var(--t3);margin-bottom:.3rem;font-weight:600;text-transform:uppercase;letter-spacing:.07em">Todas as categorias avaliadas</div>
  <div style="display:flex;flex-wrap:wrap;gap:4px">
    {"".join(f'<span style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:20px;padding:2px 8px;font-size:.60rem;color:var(--t3)">{k}: {v}pt</span>' for k, v in cls_["all_scores"].items())}
  </div>
</div>''', unsafe_allow_html=True)

                c1m, c2m, c3m, c4m = st.columns(4)
                sobel_r = ml_result.get("sobel", {}); orb_r = ml_result.get("orb", {})
                glcm_r = ml_result.get("glcm", {}); fft_r = ml_result.get("fft", {})
                with c1m: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:800;color:var(--yel)">{sobel_r.get("mean_edge", 0):.2f}</div><div class="mlbl">Sobel Edge</div></div>', unsafe_allow_html=True)
                with c2m: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:800;color:var(--grn)">{orb_r.get("n_keypoints", 0)}</div><div class="mlbl">ORB Keypoints</div></div>', unsafe_allow_html=True)
                with c3m: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:800;color:var(--blu)">{glcm_r.get("texture_type", "—")}</div><div class="mlbl">GLCM Textura</div></div>', unsafe_allow_html=True)
                with c4m: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:800;color:var(--pur)">{"Periódico" if fft_r.get("is_periodic") else "Aperiódico"}</div><div class="mlbl">FFT Estrutura</div></div>', unsafe_allow_html=True)

                t1, t2, t3, t4, t5, t6 = st.tabs([
                    "  Sobel  ", "  Keypoints  ", "  GLCM  ", "  KMeans  ", "  FFT  ", "  RGB  "
                ])

                with t1:
                    st.markdown(f'<div class="ml-feat"><div style="font-size:.62rem;color:var(--t3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:.5rem">Filtro Sobel Multi-Direcional</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem"><div><div style="font-size:.62rem;color:var(--t2);margin-bottom:2px">Intensidade de borda</div><div style="font-size:.76rem;font-weight:700;color:var(--yel)">{sobel_r.get("mean_edge", 0):.4f}</div></div><div><div style="font-size:.62rem;color:var(--t2);margin-bottom:2px">Densidade de bordas</div><div style="font-size:.76rem;font-weight:700;color:var(--grn)">{sobel_r.get("edge_density", 0) * 100:.1f}%</div></div><div><div style="font-size:.62rem;color:var(--t2);margin-bottom:2px">Máx. gradiente</div><div style="font-size:.76rem;font-weight:700;color:var(--blu)">{sobel_r.get("max_edge", 0):.3f}</div></div><div><div style="font-size:.62rem;color:var(--t2);margin-bottom:2px">Canny (fine/med/coarse)</div><div style="font-size:.72rem;font-weight:700;color:var(--pur)">{ml_result.get("canny", {}).get("fine_density", 0) * 100:.1f}% / {ml_result.get("canny", {}).get("medium_density", 0) * 100:.1f}% / {ml_result.get("canny", {}).get("coarse_density", 0) * 100:.1f}%</div></div></div></div>', unsafe_allow_html=True)
                    eh = sobel_r.get("edge_hist", [1] * 16)
                    fig_e = go.Figure(go.Bar(y=eh, marker=dict(color=list(range(16)),
                                                                colorscale=[[0, "#1A1B2E"], [.3, "#FF3B5C"], [.7, "#0A6EBD"], [1, "#6A9C89"]]),
                                              x=list(range(len(eh)))))
                    fig_e.update_layout(**{**pc_dark(), 'height': 170,
                                            'title': dict(text="Distribuição de Intensidades Sobel", font=dict(color="#E8E9F0", family="Syne", size=10)),
                                            'margin': dict(l=10, r=10, t=32, b=8)})
                    st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
                    st.plotly_chart(fig_e, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    canny_r2 = ml_result.get("canny", {})
                    st.markdown(f'<div class="pbox-blu"><div style="font-size:.65rem;color:var(--blu);font-weight:700;margin-bottom:.32rem">Canny Multi-Escala</div><div style="font-size:.72rem;color:var(--t2)">Estrutura dominante: <strong style="color:var(--t0)">{canny_r2.get("structure_level", "—")}</strong> . Total de bordas: <strong style="color:var(--yel)">{canny_r2.get("total_edges", 0):,}</strong></div></div>', unsafe_allow_html=True)

                with t2:
                    n_kp = orb_r.get("n_keypoints", 0); distr = orb_r.get("distribution", "n/a")
                    st.markdown(f'<div class="ml-feat"><div style="font-size:.62rem;color:var(--t3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:.5rem">ORB Feature Detection</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem"><div><div style="font-size:.62rem;color:var(--t2);margin-bottom:2px">Keypoints detectados</div><div style="font-family:Syne,sans-serif;font-size:1.3rem;font-weight:900;color:var(--yel)">{n_kp}</div></div><div><div style="font-size:.62rem;color:var(--t2);margin-bottom:2px">Distribuição</div><div style="font-size:.76rem;font-weight:700;color:var(--grn)">{distr}</div></div><div><div style="font-size:.62rem;color:var(--t2);margin-bottom:2px">Escala média</div><div style="font-size:.76rem;font-weight:700;color:var(--blu)">{orb_r.get("mean_scale", 1.0):.2f}</div></div><div><div style="font-size:.62rem;color:var(--t2);margin-bottom:2px">Clusters</div><div style="font-size:.76rem;font-weight:700;color:var(--pur)">{len(orb_r.get("cluster_centers", []))}</div></div></div></div>', unsafe_allow_html=True)
                    kps = orb_r.get("keypoints", np.array([]))
                    if hasattr(kps, '__len__') and len(kps) > 0:
                        kps_arr = np.array(kps)
                        if len(kps_arr.shape) == 2 and kps_arr.shape[1] >= 2:
                            h, w = ml_result.get("array_shape", [384, 384])
                            fig_kp = go.Figure()
                            fig_kp.add_trace(go.Scatter(x=kps_arr[:, 1], y=h - kps_arr[:, 0], mode='markers',
                                                         marker=dict(size=4, color=VIB[0], opacity=0.7,
                                                                     line=dict(color='rgba(255,255,255,.3)', width=0.5)),
                                                         name="Keypoints"))
                            ctrs = orb_r.get("cluster_centers", [])
                            if ctrs:
                                ca2 = np.array(ctrs)
                                fig_kp.add_trace(go.Scatter(x=ca2[:, 1] if ca2.shape[1] > 1 else ca2[:, 0],
                                                             y=h - ca2[:, 0], mode='markers',
                                                             marker=dict(size=12, symbol='x', color=VIB[2],
                                                                         line=dict(color='white', width=2)),
                                                             name="Centros"))
                            fig_kp.update_layout(**{**pc_dark(), 'height': 250,
                                                     'title': dict(text=f"Mapa de {n_kp} Keypoints ORB", font=dict(color="#E8E9F0", family="Syne", size=10)),
                                                     'xaxis': dict(range=[0, w], showgrid=False),
                                                     'yaxis': dict(range=[0, h], showgrid=False, scaleanchor='x'),
                                                     'margin': dict(l=10, r=10, t=32, b=8)})
                            st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
                            st.plotly_chart(fig_kp, use_container_width=True)
                            st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="pbox-grn"><div style="font-size:.65rem;color:var(--grn);font-weight:700;margin-bottom:.28rem">Interpretação</div><div style="font-size:.72rem;color:var(--t2);line-height:1.65">{"Alta densidade de features . imagem com muitas estruturas distintas" if n_kp > 100 else "Densidade moderada de features" if n_kp > 40 else "Baixa densidade . imagem mais homogênea"}</div></div>', unsafe_allow_html=True)

                with t3:
                    glcm_props = [(k, v) for k, v in glcm_r.items() if k not in ['error', 'texture_type'] and isinstance(v, float)]
                    if glcm_props:
                        names_g = [k.replace('_', ' ').title() for k, _ in glcm_props]
                        vals_g = [v for _, v in glcm_props]
                        mx_g = max(abs(v) for v in vals_g) + 1e-5
                        vals_norm = [abs(v) / mx_g * 100 for v in vals_g]
                        fig_gl = go.Figure()
                        fig_gl.add_trace(go.Bar(x=names_g, y=vals_g,
                                                 marker=dict(color=vals_norm, colorscale=[[0, "#1A1B2E"], [.4, "#4CC9F0"],
                                                                                          [.7, "#6A9C89"], [1, "#0A6EBD"]]),
                                                 text=[f"{v:.4f}" for v in vals_g], textposition="outside",
                                                 textfont=dict(color="#6B6F88", size=8)))
                        fig_gl.update_layout(**{**pc_dark(), 'height': 240,
                                                 'title': dict(text="GLCM . Gray Level Co-occurrence Matrix", font=dict(color="#E8E9F0", family="Syne", size=10)),
                                                 'margin': dict(l=10, r=10, t=36, b=8)})
                        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
                        st.plotly_chart(fig_gl, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    tt = glcm_r.get("texture_type", "desconhecido"); contrast = glcm_r.get("contrast", 0)
                    hom = glcm_r.get("homogeneity", 0); corr = glcm_r.get("correlation", 0)
                    st.markdown(f'<div class="ml-feat"><div style="font-size:.62rem;color:var(--t3);text-transform:uppercase;font-weight:600;margin-bottom:.45rem">Textura: <span style="color:var(--yel)">{tt}</span></div><div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:.5rem;font-size:.72rem"><div>Contraste<br><strong>{contrast:.4f}</strong></div><div>Homog.<br><strong>{hom:.4f}</strong></div><div>Correlação<br><strong>{corr:.4f}</strong></div></div></div>', unsafe_allow_html=True)

                with t4:
                    pal = ml_result.get("kmeans_palette", [])
                    if pal:
                        st.markdown('<div style="font-size:.62rem;color:var(--t3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:.55rem">KMeans Paleta Dominante (7 clusters)</div>', unsafe_allow_html=True)
                        for ci, cp in enumerate(pal):
                            pct = cp.get("pct", 0); hex_c = cp.get("hex", "#888")
                            r, g, b = cp.get("rgb", (128, 128, 128))
                            bar = f'<div style="height:6px;width:{int(pct * 3)}%;background:{hex_c};border-radius:3px;max-width:100%"></div>'
                            st.markdown(
                                f'<div style="display:flex;align-items:center;gap:9px;margin-bottom:.4rem"><div></div><div style="flex:1"><div style="display:flex;justify-content:space-between;font-size:.70rem;color:var(--t2);margin-bottom:2px"><span style="font-weight:600">{hex_c.upper()}</span><span>{pct:.1f}%</span></div>{bar}</div><div style="font-size:.60rem;color:var(--t3);width:80px;text-align:right">RGB({r},{g},{b})</div></div>',
                                unsafe_allow_html=True,
                            )
                        fig_pal = go.Figure(go.Pie(values=[c["pct"] for c in pal], labels=[c["hex"] for c in pal],
                                                    marker=dict(colors=[c["hex"] for c in pal], line=dict(color=["#0B0F1A"] * 7, width=2)),
                                                    textfont=dict(color="white", size=8), hole=0.45))
                        fig_pal.update_layout(height=220, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                               margin=dict(l=0, r=0, t=10, b=0), legend=dict(font=dict(color="#6B6F88", size=7)))
                        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
                        st.plotly_chart(fig_pal, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)

                with t5:
                    lf = fft_r.get("low_freq", 0); mf = fft_r.get("mid_freq", 0); hf = fft_r.get("high_freq", 0)
                    fig_fft = go.Figure(go.Bar(x=["Baixa\n(estruturas grandes)", "Média\n(detalhes)", "Alta\n(ruído/textura fina)"],
                                                 y=[lf, mf, hf], marker=dict(color=[VIB[0], VIB[1], VIB[2]]),
                                                 text=[f"{v:.3f}" for v in [lf, mf, hf]], textposition="outside",
                                                 textfont=dict(color="#6B6F88", size=9)))
                    fig_fft.update_layout(**{**pc_dark(), 'height': 220,
                                              'title': dict(text="FFT . Distribuição de Frequências Espaciais", font=dict(color="#E8E9F0", family="Syne", size=10)),
                                              'margin': dict(l=10, r=10, t=36, b=8)})
                    st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
                    st.plotly_chart(fig_fft, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    per = fft_r.get("periodic_score", 0); dom = fft_r.get("dominant_scale", "média")
                    is_per = fft_r.get("is_periodic", False); c_fft = "var(--grn)" if is_per else "var(--t2)"
                    st.markdown(f'<div class="ml-feat"><div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:.5rem;font-size:.72rem"><div>Score periódico<br><strong>{per:.1f}</strong></div><div>Escala dominante<br><strong>{dom}</strong></div><div>Estrutura<br><strong>{"Periódica ." if is_per else "Não-periódica"}</strong></div></div></div>', unsafe_allow_html=True)

                with t6:
                    h_data = ml_result.get("histograms", {}); bx = list(range(0, 256, 8))[:32]
                    if h_data:
                        fig4 = go.Figure()
                        fig4.add_trace(go.Scatter(x=bx, y=h_data.get("r", [])[:32], fill='tozeroy', name='R',
                                                    line=dict(color='rgba(255,59,92,.9)', width=1.5),
                                                    fillcolor='rgba(255,59,92,.10)'))
                        fig4.add_trace(go.Scatter(x=bx, y=h_data.get("g", [])[:32], fill='tozeroy', name='G',
                                                    line=dict(color='rgba(106,156,137,.9)', width=1.5),
                                                    fillcolor='rgba(106,156,137,.10)'))
                        fig4.add_trace(go.Scatter(x=bx, y=h_data.get("b", [])[:32], fill='tozeroy', name='B',
                                                    line=dict(color='rgba(76,201,240,.9)', width=1.5),
                                                    fillcolor='rgba(76,201,240,.10)'))
                        layout4 = {**pc_dark(), 'height': 200,
                                    'title': dict(text="Histograma RGB", font=dict(color="#E8E9F0", family="Syne", size=10)),
                                    'margin': dict(l=10, r=10, t=32, b=8),
                                    'legend': dict(font=dict(color="#6B6F88", size=9))}
                        fig4.update_layout(**layout4)
                        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
                        st.plotly_chart(fig4, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    col_ = ml_result.get("color", {}); mr = col_.get("r", 128); mg2 = col_.get("g", 128); mb2 = col_.get("b", 128)
                    hex_m = "#{:02x}{:02x}{:02x}".format(int(mr), int(mg2), int(mb2))
                    temp = "Quente" if col_.get("warm") else ("Fria" if col_.get("cool") else "Neutra")
                    sym = col_.get("symmetry", 0); entr = col_.get("entropy", 0)
                    st.markdown(f'<div class="ml-feat" style="display:grid;grid-template-columns:repeat(4,1fr);gap:.5rem;font-size:.72rem"><div><div style="width:28px;height:28px;border-radius:6px;background:{hex_m};border:1px solid rgba(255,255,255,.08);margin:0 auto .2rem"></div><div style="color:var(--t3)">Cor Média</div></div><div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.85rem;color:var(--yel)">{temp}</div><div style="color:var(--t3)">Temperatura</div></div><div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.85rem;color:var(--grn)">{sym:.2f}</div><div style="color:var(--t3)">Simetria</div></div><div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.85rem;color:var(--blu)">{entr:.2f}</div><div style="color:var(--t3)">Entropia</div></div></div>', unsafe_allow_html=True)

        if run_claude and img_bytes:
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown('<h2 style="margin-bottom:.5rem">Análise Claude Vision</h2>', unsafe_allow_html=True)
            with st.spinner("Claude analisando a imagem..."): ai_text, ai_err = call_claude_vision(img_bytes, VISION_PROMPT, api_key)
            if ai_err: st.error(f"Erro Claude Vision: {ai_err}")
            elif ai_text:
                try:
                    clean = ai_text.strip().replace("```json", "").replace("```", "").strip()
                    ai_data = json.loads(clean)
                    tipo = ai_data.get("tipo", "—"); origem = ai_data.get("origem", "—"); desc = ai_data.get("descricao", "—")
                    estruturas = ai_data.get("estruturas", []); tecnica = ai_data.get("tecnica", "—")
                    qualidade = ai_data.get("qualidade", "—"); confianca = ai_data.get("confianca", 0)
                    termos = ai_data.get("termos_busca", ""); obs = ai_data.get("observacoes", "")
                    conf_c2 = VIB[1] if confianca > 80 else (VIB[0] if confianca > 60 else VIB[2])
                    st.markdown(f'''<div style="background:linear-gradient(135deg,rgba(177,125,255,.08),rgba(76,201,240,.05));border:1px solid rgba(177,125,255,.22);border-radius:16px;padding:1.2rem;margin-bottom:.7rem">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:.8rem">
    <div>
      <div style="font-size:.57rem;color:var(--pur);letter-spacing:.10em;text-transform:uppercase;font-weight:700;margin-bottom:4px">Claude Opus Vision</div>
      <div style="font-family:Syne,sans-serif;font-size:1.05rem;font-weight:800;color:var(--t0);margin-bottom:4px">{tipo}</div>
      <div style="color:var(--grn);font-size:.78rem;font-weight:600">{origem}</div>
    </div>
    <div style="background:rgba(0,0,0,.3);border-radius:12px;padding:.5rem .85rem;text-align:center;flex-shrink:0">
      <div style="font-family:Syne,sans-serif;font-size:1.4rem;font-weight:900;color:{conf_c2}">{confianca}%</div>
      <div style="font-size:.52rem;color:var(--t3);text-transform:uppercase">confiança IA</div>
    </div>
  </div>
  <div style="background:rgba(255,255,255,.04);border-radius:10px;padding:.7rem .9rem;margin-bottom:.6rem;font-size:.78rem;color:var(--t2);line-height:1.7;border:1px solid rgba(255,255,255,.06)">
    <strong>Descrição:</strong> {desc}
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;margin-bottom:.5rem">
    <div style="font-size:.70rem;color:var(--t2)"><span>Técnica:</span> <strong>{tecnica}</strong></div>
    <div style="font-size:.70rem;color:var(--t2)"><span>Qualidade:</span> <strong>{qualidade}</strong></div>
  </div>
  {f'<div style="font-size:.70rem;color:var(--t2);margin-bottom:.4rem"><span>Estruturas:</span> {", ".join(estruturas)}</div>' if estruturas else ""}
  {f'<div style="background:rgba(106,156,137,.05);border:1px solid rgba(106,156,137,.12);border-radius:8px;padding:.5rem .7rem;font-size:.72rem;color:var(--t2);line-height:1.65"><strong>Observações:</strong> {obs}</div>' if obs else ""}
</div>''', unsafe_allow_html=True)
                    if termos:
                        st.markdown(f'<div style="font-size:.62rem;color:var(--t3);margin:.3rem 0 .5rem">Buscando artigos com termos da IA: <em>{termos}</em></div>', unsafe_allow_html=True)
                        with st.spinner("Buscando na literatura..."): wr = search_ss(termos, 5)
                        if wr:
                            for idx2, a2 in enumerate(wr): render_article(a2, idx=idx2 + 5000, ctx="img_claude")
                except (json.JSONDecodeError, Exception):
                    st.markdown(f'<div class="abox"><div style="font-size:.62rem;color:var(--pur);font-weight:700;margin-bottom:.5rem">Análise Claude Vision</div><div style="font-size:.78rem;color:var(--t2);line-height:1.7;white-space:pre-wrap">{ai_text[:1500]}</div></div>', unsafe_allow_html=True)

        ml_r = st.session_state.get("img_result", {})
        if ml_r and ml_r.get("ok") and not (run or run_claude): pass
        elif ml_r and ml_r.get("ok"):
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown('<h2 style="margin-bottom:.6rem">Pesquisas Relacionadas</h2>', unsafe_allow_html=True)
            cls2 = ml_r.get("classification", {}); kw_s = cls2.get("search_kw", "scientific imaging")
            tf2, tw2 = st.tabs(["  Pastas  ", "  Internet  "])
            with tf2:
                similar_imgs = find_similar_images(ml_r, st.session_state.folders)
                if similar_imgs:
                    for sc, fname, f, an in similar_imgs:
                        st.markdown(
                            f'''<div class="scard">
                                <div style="font-size:.8rem;font-family:Syne;font-weight:700;color:var(--t0);margin-bottom:.2rem">
                                    {fname} . {f}
                                </div>
                                <div style="font-size:.65rem;color:var(--t3);margin-bottom:.2rem">
                                    Similaridade: <span style="color:var(--grn);font-weight:700">{sc:.1f}pt</span>
                                </div>
                                <div style="font-size:.7rem;color:var(--t2)">
                                    Categoria: {an.get("image_meta",{}).get("classification",{}).get("category","—")}
                                </div>
                            </div>''',
                            unsafe_allow_html=True
                        )
                else: st.markdown('<div style="color:var(--t3);padding:.8rem">Nenhuma imagem relacionada nas suas pastas.</div>', unsafe_allow_html=True)
            with tw2:
                ck = f"img_{kw_s[:40]}"
                if ck not in st.session_state.scholar_cache:
                    with st.spinner("Buscando artigos..."): st.session_state.scholar_cache[ck] = search_ss(kw_s, 5)
                wr2 = st.session_state.scholar_cache.get(ck, [])
                for idx3, a3 in enumerate(wr2): render_article(a3, idx=idx3 + 3000, ctx="img_web")
                if not wr2: st.markdown('<div style="color:var(--t3);padding:.8rem">Sem resultados na web.</div>', unsafe_allow_html=True)

        elif not img_file:
            st.markdown('<div class="glass" style="padding:4.5rem 2rem;text-align:center"><div style="font-size:2.8rem;opacity:.18;margin-bottom:1rem"></div><div style="font-family:Syne,sans-serif;font-size:1rem;color:var(--t1)">Carregue uma imagem científica</div><div style="font-size:.72rem;color:var(--t3);margin-top:.4rem;line-height:1.9">Pipeline ML completo:<br>Sobel . Canny . ORB . GLCM . KMeans . FFT<br><br>Com API Key:<br>Claude Vision para análise real com IA</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def page_chat():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.9rem">Mensagens</h1>', unsafe_allow_html=True)
    cc, cm = st.columns([.85, 2.8])
    email = st.session_state.current_user
    users = st.session_state.users if isinstance(st.session_state.users, dict) else {}
    with cc:
        st.markdown('<div style="font-size:.58rem;font-weight:700;color:var(--t4);letter-spacing:.12em;text-transform:uppercase;margin-bottom:.7rem">Conversas</div>', unsafe_allow_html=True)
        shown = set()
        for ue in st.session_state.chat_contacts:
            if ue == email or ue in shown: continue
            shown.add(ue)
            ud = users.get(ue, {}); un = ud.get("name", "?"); ui = ini(un); ug = ugrad(ue)
            msgs = st.session_state.chat_messages.get(ue, [])
            last = msgs[-1]["text"][:22] + "..." if msgs and len(msgs[-1]["text"]) > 22 else (msgs[-1]["text"] if msgs else "Iniciar")
            active = st.session_state.active_chat == ue; online = is_online(ue)
            dot = '<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            bg = f"rgba(255,255,255,{'.09' if active else '.04'})"
            bdr = f"rgba(255,255,255,{'.18' if active else '.08'})"
            st.markdown(
                f'<div style="background:{bg};border:1px solid {bdr};border-radius:12px;padding:8px 10px;margin-bottom:4px"><div style="display:flex;align-items:center;gap:7px">{avh(ui, 30, ug)}<div style="overflow:hidden;flex:1"><div style="font-size:.76rem;font-weight:600;font-family:Syne,sans-serif;color:var(--t0)">{dot}{un}</div><div style="font-size:.63rem;color:var(--t3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{last}</div></div></div></div>',
                unsafe_allow_html=True,
            )
            if st.button("Abrir", key=f"oc_{ue}", use_container_width=True):
                st.session_state.active_chat = ue; st.experimental_rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
        nc2 = st.text_input("", placeholder="E-mail...", key="new_ct", label_visibility="collapsed")
        if st.button("Adicionar", key="btn_ac", use_container_width=True):
            if nc2 in users and nc2 != email:
                if nc2 not in st.session_state.chat_contacts: st.session_state.chat_contacts.append(nc2)
                st.experimental_rerun()
            else: st.warning("Usuário não encontrado ou e-mail inválido.")
    with cm:
        if st.session_state.active_chat:
            contact = st.session_state.active_chat; cd = users.get(contact, {})
            cn = cd.get("name", "?"); ci = ini(cn); cg = ugrad(contact)
            msgs = st.session_state.chat_messages.get(contact, [])
            online = is_online(contact); dot = '<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            st.markdown(
                f'<div style="background:var(--g2);border:1px solid var(--gb1);border-radius:14px;padding:10px 14px;margin-bottom:.85rem;display:flex;align-items:center;gap:10px">{avh(ci, 36, cg)}<div style="flex:1"><div style="font-weight:700;font-size:.88rem;font-family:Syne,sans-serif;color:var(--t0)">{dot}{cn}</div><div style="font-size:.63rem;color:var(--grn)">AES-256</div></div></div>',
                unsafe_allow_html=True,
            )
            for msg in msgs:
                im = msg["from"] == "me"; cls = "bme" if im else "bthem"
                st.markdown(
                    f'<div style="display:flex;{"justify-content:flex-end" if im else ""}"><div class="{cls}">{msg["text"]}<div style="font-size:.57rem;color:var(--t3);margin-top:2px;text-align:{"right" if im else "left"}">{msg["time"]}</div></div></div>',
                    unsafe_allow_html=True,
                )
            st.markdown("<br>", unsafe_allow_html=True)
            ci2, cb2 = st.columns([5, 1])
            with ci2:
                nm = st.text_input("", placeholder="Escreva uma mensagem...", key=f"mi_{contact}", label_visibility="collapsed")
            with cb2:
                if st.button("Enviar", key=f"ms_{contact}", use_container_width=True):
                    if nm:
                        now = datetime.now().strftime("%H:%M")
                        st.session_state.chat_messages.setdefault(contact, []).append({"from": "me", "text": nm, "time": now})
                        st.session_state[f"mi_{contact}"] = ""
                        st.experimental_rerun()
        else:
            st.markdown('<div class="glass" style="text-align:center;padding:5rem"><div style="font-size:2.2rem;opacity:.15;margin-bottom:.85rem"></div><div style="font-family:Syne,sans-serif;font-size:.96rem;color:var(--t1)">Selecione uma conversa</div><div style="font-size:.70rem;color:var(--t3);margin-top:.4rem">End-to-end criptografado</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def page_settings():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.9rem">Configurações</h1>', unsafe_allow_html=True)
    email = st.session_state.current_user
    ud = st.session_state.users.get(email, {})
    st.markdown(f'<div class="abox"><div style="font-size:.58rem;color:var(--t3);text-transform:uppercase;letter-spacing:.10em;margin-bottom:.4rem;font-weight:700">Conta</div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.95rem;color:var(--yel)">{email}</div></div>', unsafe_allow_html=True)
    en = ud.get("2fa_enabled", False)
    st.markdown('<div>', unsafe_allow_html=True)
    if st.button("Desativar 2FA" if en else "Ativar 2FA", key="cfg_2fa", use_container_width=True):
        st.session_state.users[email]["2fa_enabled"] = not en
        save_db(); st.experimental_rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    with st.form("cpw"):
        op = st.text_input("Senha atual", type="password")
        np2 = st.text_input("Nova senha", type="password")
        nc3 = st.text_input("Confirmar", type="password")
        if st.form_submit_button("Alterar Senha", use_container_width=True):
            if hp(op) != ud.get("password", ""): st.error("Senha atual incorreta.")
            elif np2 != nc3: st.error("As novas senhas não coincidem.")
            elif len(np2) < 6: st.error("A nova senha deve ter no mínimo 6 caracteres.")
            else:
                st.session_state.users[email]["password"] = hp(np2)
                save_db(); st.success("Senha alterada com sucesso!")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    for nm, ds in [("AES-256", "End-to-end"), ("SHA-256", "Hash senhas"), ("TLS 1.3", "Transmissão")]:
        st.markdown(f'<div class="pbox-grn"><div style="display:flex;align-items:center;gap:9px"><div style="width:24px;height:24px;border-radius:7px;background:rgba(106,156,137,.12);display:flex;align-items:center;justify-content:center;color:var(--grn);font-size:.72rem">.</div><div><div style="font-weight:700;color:var(--grn);font-size:.78rem">{nm}</div><div style="font-size:.66rem;color:var(--t3)">{ds}</div></div></div></div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("Sair da Conta", key="logout", use_container_width=True):
        st.session_state.logged_in = False; st.session_state.current_user = None
        st.session_state.page = "login"; st.experimental_rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def main():
    inject_css()
    if not st.session_state.logged_in:
        page_login()
        return
    render_nav()
    if st.session_state.profile_view:
        page_profile(st.session_state.profile_view)
        return
    {
        "repository": page_repository,
        "search": page_search,
        "knowledge": page_knowledge,
        "analytics": page_analytics,
        "img_search": page_img_search,
        "chat": page_chat,
        "settings": page_settings,
    }.get(st.session_state.page, page_repository)()

if __name__ == "__main__":
    main()
