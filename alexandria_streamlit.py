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
    pass # Se não conseguir importar, SKIMAGE_OK permanece False

import streamlit as st

# --- CORREÇÃO AQUI: Removido o emoji do argumento 'icon' ---
st.set_page_config(
    page_title="Nebula - Repositório Científico", layout="wide", initial_sidebar_state="expanded"
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
.glass::before{content:'';position:absolute;inset:0;background:linear-gradient(135deg,rgba(255,255,255,.02),transparent 50%,rgba(255,255,255,.01));pointer-events:none;z-index:1;}
.pw{max-width:800px;margin:0 auto;}
h1{font-family:'Syne',sans-serif;font-weight:900;font-size:1.8rem;letter-spacing:-.04em;background:linear-gradient(135deg,#4CC9F0,#6A9C89);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
h2{font-family:'Syne',sans-serif;font-weight:800;font-size:1.4rem;letter-spacing:-.03em;color:var(--t0);}
h3{font-family:'Syne',sans-serif;font-weight:700;font-size:1.1rem;letter-spacing:-.02em;color:var(--t1);}
.stTabs [data-testid="stTabList"] button{background:var(--bg2);border:1px solid var(--gb1);border-radius:var(--r12);color:var(--t2);font-family:'DM Sans',sans-serif;font-weight:500;font-size:.8rem;padding:.6rem 1.1rem;margin-right:.5rem;transition:all .15s ease-out;}
.stTabs [data-testid="stTabList"] button:hover{background:var(--g2);color:var(--t1);}
.stTabs [data-testid="stTabList"] button[aria-selected="true"]{background:var(--g3);border-color:var(--gb3);color:var(--t0);font-weight:600;}
.stTabs [data-testid="stTabPanel"]{padding-top:1.5rem;}
.stAlert{border-radius:var(--r12);padding:1rem 1.2rem;font-size:.8rem;line-height:1.6;}
.stAlert [data-testid="stMarkdownContainer"]{font-size:.8rem!important;}
.stAlert [data-testid="stMarkdownContainer"] p{margin-bottom:0!important;}
.stAlert [data-testid="stAlertContent"]{display:flex;flex-direction:column;gap:.5rem;}
.stAlert [data-testid="stAlertContent"] svg{display:none;}
.stAlert.st-emotion-cache-1f03k0a{background:rgba(10,110,189,.1)!important;border-color:rgba(10,110,189,.3)!important;color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stMarkdownContainer"]{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a strong{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"]{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] p{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] a{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] span{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] div{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] h1{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] h2{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] h3{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] h4{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] h5{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] h6{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] li{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] ul{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] ol{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] code{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] pre{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] blockquote{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] table{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] th{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] td{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] hr{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] img{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] video{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] audio{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] iframe{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] object{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] embed{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] param{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] source{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] track{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] area{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] map{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] link{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meta{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] style{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] script{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] noscript{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] template{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] slot{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] content{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] shadow{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] data{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] time{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] mark{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] ruby{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] rt{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] rp{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] bdi{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] bdo{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] wbr{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] details{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] summary{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] dialog{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] menu{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] menuitem{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] command{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] label{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] fieldset{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] legend{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] datalist{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] keygen{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] output{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] progress{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] meter{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] form{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] input{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] textarea{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] select{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] button{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] optgroup{color:var(--blu)!important;}
.stAlert.st-emotion-cache-1f03k0a [data-testid="stAlertContent"] option{color:var(--blu)!important;}
.
