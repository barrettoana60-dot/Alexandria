import subprocess, sys, os, json, hashlib, random, string, re, io, base64, time
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
except: _pip("PyPDF2")
try: import PyPDF2
except: PyPDF2 = None
try: import openpyxl
except: _pip("openpyxl")
try: import openpyxl
except: openpyxl = None
try: import pandas as pd
except: _pip("pandas"); import pandas as pd

# ML / Image Processing — all optional, pure numpy fallbacks
SKIMAGE_OK = False
SKLEARN_OK = False
SCIPY_OK = False

try:
    from skimage import filters as sk_filters, feature as sk_feature
    from skimage.feature import graycomatrix, graycoprops
    SKIMAGE_OK = True
except Exception:
    try:
        _pip("scikit-image")
        from skimage import filters as sk_filters, feature as sk_feature
        from skimage.feature import graycomatrix, graycoprops
        SKIMAGE_OK = True
    except Exception:
        SKIMAGE_OK = False

try:
    from sklearn.cluster import KMeans
    SKLEARN_OK = True
except Exception:
    try:
        _pip("scikit-learn")
        from sklearn.cluster import KMeans
        SKLEARN_OK = True
    except Exception:
        SKLEARN_OK = False

try:
    from scipy import ndimage as sp_ndimage
    SCIPY_OK = True
except Exception:
    try:
        _pip("scipy")
        from scipy import ndimage as sp_ndimage
        SCIPY_OK = True
    except Exception:
        SCIPY_OK = False

import streamlit as st

st.set_page_config(page_title="Nebula", page_icon="🔬", layout="wide", initial_sidebar_state="expanded")

DB_FILE = "nebula_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def hp(pw): return hashlib.sha256(pw.encode()).hexdigest()
def code6(): return ''.join(random.choices(string.digits,k=6))
def ini(n):
    if not isinstance(n,str): n=str(n)
    p=n.strip().split()
    return ''.join(w[0].upper() for w in p[:2]) if p else "?"
def time_ago(ds):
    try:
        dt=datetime.strptime(ds,"%Y-%m-%d"); d=(datetime.now()-dt).days
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
def is_online(e): return (hash(e+"on")%3)!=0

GRAD_POOL=[
    "135deg,#FFD60A,#FF8C42","135deg,#06D6A0,#4CC9F0","135deg,#FF3B5C,#FF8C42",
    "135deg,#4CC9F0,#B17DFF","135deg,#A8FF78,#78FFD6","135deg,#6C63FF,#48C6EF",
    "135deg,#F7971E,#FFD200","135deg,#FF5F6D,#FFC371",
]
def ugrad(e): return f"linear-gradient({GRAD_POOL[hash(e or '')%len(GRAD_POOL)]})"

STOPWORDS={"de","a","o","que","e","do","da","em","um","para","é","com","uma","os","no","se","na","por","mais","as","dos","como","mas","foi","ao","ele","das","tem","à","seu","sua","ou","ser","quando","muito","há","nos","já","está","eu","também","só","pelo","pela","até","isso","ela","entre","era","depois","sem","mesmo","aos","ter","seus","the","of","and","to","in","is","it","that","was","he","for","on","are","as","with","they","at","be","this","from","or","one","had","by","but","not","what","all","were","we","when","your","can","said","there","use","an","each","which","she","do","how","their","if","will","up","other","about","out","many","then","them","these","so"}

SEED_POSTS=[
    {"id":1,"author":"Carlos Mendez","author_email":"carlos@nebula.ai","avatar":"CM","area":"Neurociência","title":"Efeitos da Privação de Sono na Plasticidade Sináptica","abstract":"Investigamos como 24h de privação de sono afetam espinhas dendríticas em ratos Wistar, com redução de 34% na plasticidade hipocampal.","tags":["neurociência","sono","memória","hipocampo"],"likes":47,"comments":[{"user":"Maria Silva","text":"Excelente metodologia!"}],"status":"Em andamento","date":"2026-02-10","liked_by":[],"saved_by":[],"connections":["sono","memória"],"views":312},
    {"id":2,"author":"Luana Freitas","author_email":"luana@nebula.ai","avatar":"LF","area":"Biomedicina","title":"CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras","abstract":"Vetor AAV9 modificado para entrega de CRISPR no gene DMD com eficiência de 78% em modelos mdx.","tags":["CRISPR","gene terapia","músculo","AAV9"],"likes":93,"comments":[{"user":"Ana","text":"Quando iniciam os trials?"}],"status":"Publicado","date":"2026-01-28","liked_by":[],"saved_by":[],"connections":["genômica","distrofia"],"views":891},
    {"id":3,"author":"Rafael Souza","author_email":"rafael@nebula.ai","avatar":"RS","area":"Computação","title":"Redes Neurais Quântico-Clássicas para Otimização Combinatória","abstract":"Arquitetura híbrida variacional combinando qubits supercondutores com camadas densas clássicas. TSP resolvido com 40% menos iterações.","tags":["quantum ML","otimização","TSP"],"likes":201,"comments":[],"status":"Em andamento","date":"2026-02-15","liked_by":[],"saved_by":[],"connections":["computação quântica"],"views":1240},
    {"id":4,"author":"Priya Nair","author_email":"priya@nebula.ai","avatar":"PN","area":"Astrofísica","title":"Detecção de Matéria Escura via Lentes Gravitacionais Fracas","abstract":"Mapeamento com 100M de galáxias do DES Y3. Tensão de 2.8σ com ΛCDM em escalas < 1 Mpc.","tags":["astrofísica","matéria escura","cosmologia","DES"],"likes":312,"comments":[],"status":"Publicado","date":"2026-02-01","liked_by":[],"saved_by":[],"connections":["cosmologia"],"views":2180},
    {"id":5,"author":"João Lima","author_email":"joao@nebula.ai","avatar":"JL","area":"Psicologia","title":"Viés de Confirmação em Decisões Médicas Assistidas por IA","abstract":"Estudo duplo-cego com 240 médicos revelou que sistemas de IA mal calibrados amplificam vieses cognitivos em 22% dos casos.","tags":["psicologia","IA","cognição","medicina"],"likes":78,"comments":[{"user":"Carlos M.","text":"Muito relevante!"}],"status":"Publicado","date":"2026-02-08","liked_by":[],"saved_by":[],"connections":["cognição","IA"],"views":456},
]
SEED_USERS={
    "demo@nebula.ai":{"name":"Ana Pesquisadora","password":hp("demo123"),"bio":"Pesquisadora em IA e Ciências Cognitivas | UFMG","area":"Inteligência Artificial","followers":128,"following":47,"verified":True,"2fa_enabled":False},
    "carlos@nebula.ai":{"name":"Carlos Mendez","password":hp("nebula123"),"bio":"Neurocientista | UFMG | Plasticidade sináptica e sono","area":"Neurociência","followers":210,"following":45,"verified":True,"2fa_enabled":False},
    "luana@nebula.ai":{"name":"Luana Freitas","password":hp("nebula123"),"bio":"Biomédica | FIOCRUZ | CRISPR e terapia gênica","area":"Biomedicina","followers":178,"following":62,"verified":True,"2fa_enabled":False},
    "rafael@nebula.ai":{"name":"Rafael Souza","password":hp("nebula123"),"bio":"Computação Quântica | USP | Algoritmos híbridos","area":"Computação","followers":340,"following":88,"verified":True,"2fa_enabled":False},
    "priya@nebula.ai":{"name":"Priya Nair","password":hp("nebula123"),"bio":"Astrofísica | MIT | Dark matter & gravitational lensing","area":"Astrofísica","followers":520,"following":31,"verified":True,"2fa_enabled":False},
    "joao@nebula.ai":{"name":"João Lima","password":hp("nebula123"),"bio":"Psicólogo Cognitivo | UNICAMP | IA e vieses clínicos","area":"Psicologia","followers":95,"following":120,"verified":True,"2fa_enabled":False},
}
CHAT_INIT={
    "carlos@nebula.ai":[{"from":"carlos@nebula.ai","text":"Oi! Vi seu comentário na pesquisa.","time":"09:14"},{"from":"me","text":"Achei muito interessante!","time":"09:16"}],
    "luana@nebula.ai":[{"from":"luana@nebula.ai","text":"Podemos colaborar no próximo projeto?","time":"ontem"}],
}

# ── DB ──────────────────────────────────────────
def save_db():
    try:
        with open(DB_FILE,"w",encoding="utf-8") as f:
            json.dump({
                "users":st.session_state.users,
                "feed_posts":st.session_state.feed_posts,
                "folders":st.session_state.folders,
                "user_prefs":{k:dict(v) for k,v in st.session_state.user_prefs.items()},
                "saved_articles":st.session_state.saved_articles,
                "followed":st.session_state.followed,
            },f,ensure_ascii=False,indent=2)
    except: pass

def init():
    if "initialized" in st.session_state: return
    st.session_state.initialized=True
    disk=load_db()
    du=disk.get("users",{})
    if not isinstance(du,dict): du={}
    st.session_state.setdefault("users",{**SEED_USERS,**du})
    st.session_state.setdefault("logged_in",False)
    st.session_state.setdefault("current_user",None)
    st.session_state.setdefault("page","login")
    st.session_state.setdefault("profile_view",None)
    dp=disk.get("user_prefs",{})
    st.session_state.setdefault("user_prefs",{k:defaultdict(float,v) for k,v in dp.items()})
    st.session_state.setdefault("pending_verify",None)
    st.session_state.setdefault("pending_2fa",None)
    rp=disk.get("feed_posts",[dict(p) for p in SEED_POSTS])
    for p in rp: p.setdefault("liked_by",[]); p.setdefault("saved_by",[]); p.setdefault("comments",[]); p.setdefault("views",200)
    st.session_state.setdefault("feed_posts",rp)
    st.session_state.setdefault("folders",disk.get("folders",{}))
    st.session_state.setdefault("folder_files_bytes",{})
    st.session_state.setdefault("chat_contacts",list(SEED_USERS.keys()))
    st.session_state.setdefault("chat_messages",{k:list(v) for k,v in CHAT_INIT.items()})
    st.session_state.setdefault("active_chat",None)
    st.session_state.setdefault("followed",disk.get("followed",["carlos@nebula.ai","luana@nebula.ai"]))
    st.session_state.setdefault("notifications",["Carlos curtiu sua pesquisa","Nova conexão detectada"])
    st.session_state.setdefault("scholar_cache",{})
    st.session_state.setdefault("saved_articles",disk.get("saved_articles",[]))
    st.session_state.setdefault("img_result",None)
    st.session_state.setdefault("search_results",None)
    st.session_state.setdefault("last_sq","")
    st.session_state.setdefault("stats_data",{"h_index":4,"fator_impacto":3.8,"notes":""})
    st.session_state.setdefault("compose_open",False)
    st.session_state.setdefault("anthropic_key","")
    st.session_state.setdefault("ai_conn_cache",{})

init()

# ════════════════════════════════════════════════
#  REAL AI — CLAUDE VISION API
# ════════════════════════════════════════════════
def call_claude_vision(img_bytes, prompt, api_key):
    """Send image to Claude Vision API for real AI analysis."""
    if not api_key or not api_key.startswith("sk-"):
        return None, "Chave API inválida ou ausente."
    try:
        img = PILImage.open(io.BytesIO(img_bytes))
        # Convert to JPEG for API
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
                "model": "claude-sonnet-20240229", # Using sonnet for faster response, can be opus
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
            err = resp.json().get("error", {}).get("message", f"HTTP {resp.status_code}")
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
    """Use Claude to suggest intelligent connections."""
    if not api_key or not api_key.startswith("sk-"):
        return None, "API key ausente."
    try:
        u = users_data.get(email, {})
        my_posts = [p for p in posts_data if p.get("author_email")==email]
        others = [{
            "email": ue, "name": ud.get("name",""), "area": ud.get("area",""),
            "tags": list({t for p in posts_data if p.get("author_email")==ue for t in p.get("tags",[])})[:8]
        } for ue, ud in users_data.items() if ue != email]
        payload = {
            "meu_perfil": {"area": u.get("area",""), "bio": u.get("bio",""),
                           "tags": list({t for p in my_posts for t in p.get("tags",[])})[:10]},
            "pesquisadores": others[:15]
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
            json={"model": "claude-sonnet-20240229", "max_tokens": 600,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=20
        )
        if resp.status_code == 200:
            text = resp.json()["content"][0]["text"].strip()
            # Corrected regex to remove markdown code block delimiters
            # Using raw string with escaped backticks for robustness
            text = re.sub(r'^```json\s*', '', text, flags=re.DOTALL)
            text = re.sub(r'\s*```

Python
Copiar
import subprocess, sys, os, json, hashlib, random, string, re, io, base64, time
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
except: _pip("PyPDF2")
try: import PyPDF2
except: PyPDF2 = None
try: import openpyxl
except: _pip("openpyxl")
try: import openpyxl
except: openpyxl = None
try: import pandas as pd
except: _pip("pandas"); import pandas as pd

# ML / Image Processing — all optional, pure numpy fallbacks
SKIMAGE_OK = False
SKLEARN_OK = False
SCIPY_OK = False

try:
    from skimage import filters as sk_filters, feature as sk_feature
    from skimage.feature import graycomatrix, graycoprops
    SKIMAGE_OK = True
except Exception:
    try:
        _pip("scikit-image")
        from skimage import filters as sk_filters, feature as sk_feature
        from skimage.feature import graycomatrix, graycoprops
        SKIMAGE_OK = True
    except Exception:
        SKIMAGE_OK = False

try:
    from sklearn.cluster import KMeans
    SKLEARN_OK = True
except Exception:
    try:
        _pip("scikit-learn")
        from sklearn.cluster import KMeans
        SKLEARN_OK = True
    except Exception:
        SKLEARN_OK = False

try:
    from scipy import ndimage as sp_ndimage
    SCIPY_OK = True
except Exception:
    try:
        _pip("scipy")
        from scipy import ndimage as sp_ndimage
        SCIPY_OK = True
    except Exception:
        SCIPY_OK = False

import streamlit as st

st.set_page_config(page_title="Nebula", page_icon="🔬", layout="wide", initial_sidebar_state="expanded")

DB_FILE = "nebula_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def hp(pw): return hashlib.sha256(pw.encode()).hexdigest()
def code6(): return ''.join(random.choices(string.digits,k=6))
def ini(n):
    if not isinstance(n,str): n=str(n)
    p=n.strip().split()
    return ''.join(w[0].upper() for w in p[:2]) if p else "?"
def time_ago(ds):
    try:
        dt=datetime.strptime(ds,"%Y-%m-%d"); d=(datetime.now()-dt).days
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
def is_online(e): return (hash(e+"on")%3)!=0

GRAD_POOL=[
    "135deg,#FFD60A,#FF8C42","135deg,#06D6A0,#4CC9F0","135deg,#FF3B5C,#FF8C42",
    "135deg,#4CC9F0,#B17DFF","135deg,#A8FF78,#78FFD6","135deg,#6C63FF,#48C6EF",
    "135deg,#F7971E,#FFD200","135deg,#FF5F6D,#FFC371",
]
def ugrad(e): return f"linear-gradient({GRAD_POOL[hash(e or '')%len(GRAD_POOL)]})"

STOPWORDS={"de","a","o","que","e","do","da","em","um","para","é","com","uma","os","no","se","na","por","mais","as","dos","como","mas","foi","ao","ele","das","tem","à","seu","sua","ou","ser","quando","muito","há","nos","já","está","eu","também","só","pelo","pela","até","isso","ela","entre","era","depois","sem","mesmo","aos","ter","seus","the","of","and","to","in","is","it","that","was","he","for","on","are","as","with","they","at","be","this","from","or","one","had","by","but","not","what","all","were","we","when","your","can","said","there","use","an","each","which","she","do","how","their","if","will","up","other","about","out","many","then","them","these","so"}

SEED_POSTS=[
    {"id":1,"author":"Carlos Mendez","author_email":"carlos@nebula.ai","avatar":"CM","area":"Neurociência","title":"Efeitos da Privação de Sono na Plasticidade Sináptica","abstract":"Investigamos como 24h de privação de sono afetam espinhas dendríticas em ratos Wistar, com redução de 34% na plasticidade hipocampal.","tags":["neurociência","sono","memória","hipocampo"],"likes":47,"comments":[{"user":"Maria Silva","text":"Excelente metodologia!"}],"status":"Em andamento","date":"2026-02-10","liked_by":[],"saved_by":[],"connections":["sono","memória"],"views":312},
    {"id":2,"author":"Luana Freitas","author_email":"luana@nebula.ai","avatar":"LF","area":"Biomedicina","title":"CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras","abstract":"Vetor AAV9 modificado para entrega de CRISPR no gene DMD com eficiência de 78% em modelos mdx.","tags":["CRISPR","gene terapia","músculo","AAV9"],"likes":93,"comments":[{"user":"Ana","text":"Quando iniciam os trials?"}],"status":"Publicado","date":"2026-01-28","liked_by":[],"saved_by":[],"connections":["genômica","distrofia"],"views":891},
    {"id":3,"author":"Rafael Souza","author_email":"rafael@nebula.ai","avatar":"RS","area":"Computação","title":"Redes Neurais Quântico-Clássicas para Otimização Combinatória","abstract":"Arquitetura híbrida variacional combinando qubits supercondutores com camadas densas clássicas. TSP resolvido com 40% menos iterações.","tags":["quantum ML","otimização","TSP"],"likes":201,"comments":[],"status":"Em andamento","date":"2026-02-15","liked_by":[],"saved_by":[],"connections":["computação quântica"],"views":1240},
    {"id":4,"author":"Priya Nair","author_email":"priya@nebula.ai","avatar":"PN","area":"Astrofísica","title":"Detecção de Matéria Escura via Lentes Gravitacionais Fracas","abstract":"Mapeamento com 100M de galáxias do DES Y3. Tensão de 2.8σ com ΛCDM em escalas < 1 Mpc.","tags":["astrofísica","matéria escura","cosmologia","DES"],"likes":312,"comments":[],"status":"Publicado","date":"2026-02-01","liked_by":[],"saved_by":[],"connections":["cosmologia"],"views":2180},
    {"id":5,"author":"João Lima","author_email":"joao@nebula.ai","avatar":"JL","area":"Psicologia","title":"Viés de Confirmação em Decisões Médicas Assistidas por IA","abstract":"Estudo duplo-cego com 240 médicos revelou que sistemas de IA mal calibrados amplificam vieses cognitivos em 22% dos casos.","tags":["psicologia","IA","cognição","medicina"],"likes":78,"comments":[{"user":"Carlos M.","text":"Muito relevante!"}],"status":"Publicado","date":"2026-02-08","liked_by":[],"saved_by":[],"connections":["cognição","IA"],"views":456},
]
SEED_USERS={
    "demo@nebula.ai":{"name":"Ana Pesquisadora","password":hp("demo123"),"bio":"Pesquisadora em IA e Ciências Cognitivas | UFMG","area":"Inteligência Artificial","followers":128,"following":47,"verified":True,"2fa_enabled":False},
    "carlos@nebula.ai":{"name":"Carlos Mendez","password":hp("nebula123"),"bio":"Neurocientista | UFMG | Plasticidade sináptica e sono","area":"Neurociência","followers":210,"following":45,"verified":True,"2fa_enabled":False},
    "luana@nebula.ai":{"name":"Luana Freitas","password":hp("nebula123"),"bio":"Biomédica | FIOCRUZ | CRISPR e terapia gênica","area":"Biomedicina","followers":178,"following":62,"verified":True,"2fa_enabled":False},
    "rafael@nebula.ai":{"name":"Rafael Souza","password":hp("nebula123"),"bio":"Computação Quântica | USP | Algoritmos híbridos","area":"Computação","followers":340,"following":88,"verified":True,"2fa_enabled":False},
    "priya@nebula.ai":{"name":"Priya Nair","password":hp("nebula123"),"bio":"Astrofísica | MIT | Dark matter & gravitational lensing","area":"Astrofísica","followers":520,"following":31,"verified":True,"2fa_enabled":False},
    "joao@nebula.ai":{"name":"João Lima","password":hp("nebula123"),"bio":"Psicólogo Cognitivo | UNICAMP | IA e vieses clínicos","area":"Psicologia","followers":95,"following":120,"verified":True,"2fa_enabled":False},
}
CHAT_INIT={
    "carlos@nebula.ai":[{"from":"carlos@nebula.ai","text":"Oi! Vi seu comentário na pesquisa.","time":"09:14"},{"from":"me","text":"Achei muito interessante!","time":"09:16"}],
    "luana@nebula.ai":[{"from":"luana@nebula.ai","text":"Podemos colaborar no próximo projeto?","time":"ontem"}],
}

# ── DB ──────────────────────────────────────────
def save_db():
    try:
        with open(DB_FILE,"w",encoding="utf-8") as f:
            json.dump({
                "users":st.session_state.users,
                "feed_posts":st.session_state.feed_posts,
                "folders":st.session_state.folders,
                "user_prefs":{k:dict(v) for k,v in st.session_state.user_prefs.items()},
                "saved_articles":st.session_state.saved_articles,
                "followed":st.session_state.followed,
            },f,ensure_ascii=False,indent=2)
    except: pass

def init():
    if "initialized" in st.session_state: return
    st.session_state.initialized=True
    disk=load_db()
    du=disk.get("users",{})
    if not isinstance(du,dict): du={}
    st.session_state.setdefault("users",{**SEED_USERS,**du})
    st.session_state.setdefault("logged_in",False)
    st.session_state.setdefault("current_user",None)
    st.session_state.setdefault("page","login")
    st.session_state.setdefault("profile_view",None)
    dp=disk.get("user_prefs",{})
    st.session_state.setdefault("user_prefs",{k:defaultdict(float,v) for k,v in dp.items()})
    st.session_state.setdefault("pending_verify",None)
    st.session_state.setdefault("pending_2fa",None)
    rp=disk.get("feed_posts",[dict(p) for p in SEED_POSTS])
    for p in rp: p.setdefault("liked_by",[]); p.setdefault("saved_by",[]); p.setdefault("comments",[]); p.setdefault("views",200)
    st.session_state.setdefault("feed_posts",rp)
    st.session_state.setdefault("folders",disk.get("folders",{}))
    st.session_state.setdefault("folder_files_bytes",{})
    st.session_state.setdefault("chat_contacts",list(SEED_USERS.keys()))
    st.session_state.setdefault("chat_messages",{k:list(v) for k,v in CHAT_INIT.items()})
    st.session_state.setdefault("active_chat",None)
    st.session_state.setdefault("followed",disk.get("followed",["carlos@nebula.ai","luana@nebula.ai"]))
    st.session_state.setdefault("notifications",["Carlos curtiu sua pesquisa","Nova conexão detectada"])
    st.session_state.setdefault("scholar_cache",{})
    st.session_state.setdefault("saved_articles",disk.get("saved_articles",[]))
    st.session_state.setdefault("img_result",None)
    st.session_state.setdefault("search_results",None)
    st.session_state.setdefault("last_sq","")
    st.session_state.setdefault("stats_data",{"h_index":4,"fator_impacto":3.8,"notes":""})
    st.session_state.setdefault("compose_open",False)
    st.session_state.setdefault("anthropic_key","")
    st.session_state.setdefault("ai_conn_cache",{})

init()

# ════════════════════════════════════════════════
#  REAL AI — CLAUDE VISION API
# ════════════════════════════════════════════════
def call_claude_vision(img_bytes, prompt, api_key):
    """Send image to Claude Vision API for real AI analysis."""
    if not api_key or not api_key.startswith("sk-"):
        return None, "Chave API inválida ou ausente."
    try:
        img = PILImage.open(io.BytesIO(img_bytes))
        # Convert to JPEG for API
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
                "model": "claude-sonnet-20240229", # Using sonnet for faster response, can be opus
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
            err = resp.json().get("error", {}).get("message", f"HTTP {resp.status_code}")
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
    """Use Claude to suggest intelligent connections."""
    if not api_key or not api_key.startswith("sk-"):
        return None, "API key ausente."
    try:
        u = users_data.get(email, {})
        my_posts = [p for p in posts_data if p.get("author_email")==email]
        others = [{
            "email": ue, "name": ud.get("name",""), "area": ud.get("area",""),
            "tags": list({t for p in posts_data if p.get("author_email")==ue for t in p.get("tags",[])})[:8]
        } for ue, ud in users_data.items() if ue != email]
        payload = {
            "meu_perfil": {"area": u.get("area",""), "bio": u.get("bio",""),
                           "tags": list({t for p in my_posts for t in p.get("tags",[])})[:10]},
            "pesquisadores": others[:15]
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
            json={"model": "claude-sonnet-20240229", "max_tokens": 600,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=20
        )
        if resp.status_code == 200:
            text = resp.json()["content"][0]["text"].strip()
            # Corrected regex to remove markdown code block delimiters
            # Using raw string with escaped backticks for robustness
            text = re.sub(r'^```json\s*', '', text, flags=re.DOTALL)
            text = re.sub(r'\s*```INNERCHAT_CB_rozk8aw96#x27;, '', text, flags=re.DOTALL)
            return json.loads(text), None
        return None, f"HTTP {resp.status_code}"
    except Exception as e:
        return None, str(e)

# ════════════════════════════════════════════════
#  REAL ML IMAGE ANALYSIS PIPELINE
# ════════════════════════════════════════════════
def sobel_analysis(gray_arr):
    """Multi-directional Sobel edge detection — numpy fallback if skimage unavailable."""
    try:
        if SKIMAGE_OK:
            import skimage.filters as skf
            sx = skf.sobel_h(gray_arr)
            sy = skf.sobel_v(gray_arr)
        else:
            # Pure numpy Sobel
            kx = np.array([[-1,0,1],[-2,0,2],[-1,0,1]], dtype=np.float32)/8.0
            ky = kx.T
            from numpy import pad as nppad
            def conv2d(img, k):
                ph,pw=k.shape[0]//2,k.shape[1]//2
                padded=nppad(img,((ph,ph),(pw,pw)),mode='edge')
                out=np.zeros_like(img)
                for i in range(k.shape[0]):
                    for j in range(k.shape[1]):
                        out+=k[i,j]*padded[i:i+img.shape[0],j:j+img.shape[1]]
                return out
            sx=conv2d(gray_arr.astype(np.float32),kx)
            sy=conv2d(gray_arr.astype(np.float32),ky)
        magnitude = np.sqrt(sx**2 + sy**2)
        direction = np.arctan2(sy, sx) * 180 / np.pi
        # Diagonal via numpy gradient
        try:
            gx2 = np.gradient(gray_arr, axis=1)
            gy2 = np.gradient(gray_arr, axis=0)
        except Exception:
            gx2, gy2 = sx, sy
        return {
            "magnitude": magnitude,
            "horizontal": sx,
            "vertical": sy,
            "mean_edge": float(magnitude.mean()),
            "max_edge": float(magnitude.max()),
            "edge_density": float((magnitude > magnitude.mean()*1.5).mean()),
            "dominant_direction": float(direction.mean()),
            "edge_hist": np.histogram(magnitude, bins=16, range=(0, magnitude.max()+1e-5))[0].tolist()
        }
    except Exception as e:
        # Ultra-safe fallback
        gx = np.gradient(gray_arr.astype(np.float32), axis=1)
        gy = np.gradient(gray_arr.astype(np.float32), axis=0)
        mag = np.sqrt(gx**2+gy**2)
        return {"magnitude":mag,"horizontal":gx,"vertical":gy,
                "mean_edge":float(mag.mean()),"max_edge":float(mag.max()),
                "edge_density":float((mag>mag.mean()*1.5).mean()),
                "dominant_direction":0.0,
                "edge_hist":np.histogram(mag,bins=16)[0].tolist()}

def canny_analysis(gray_uint8):
    """Canny multi-scale edge detection — numpy fallback."""
    try:
        if SKIMAGE_OK:
            from skimage import feature as skf2
            edges_fine   = skf2.canny(gray_uint8/255.0, sigma=1.0)
            edges_med    = skf2.canny(gray_uint8/255.0, sigma=2.0)
            edges_coarse = skf2.canny(gray_uint8/255.0, sigma=3.5)
        else:
            # Numpy gradient-based edge approximation
            g = gray_uint8.astype(np.float32)/255.0
            gx=np.gradient(g,axis=1); gy=np.gradient(g,axis=0); mag=np.sqrt(gx**2+gy**2)
            t1,t2,t3=np.percentile(mag,85),np.percentile(mag,75),np.percentile(mag,65)
            edges_fine=mag>t1; edges_med=mag>t2; edges_coarse=mag>t3
        return {
            "fine": edges_fine, "medium": edges_med, "coarse": edges_coarse,
            "fine_density": float(edges_fine.mean()),
            "medium_density": float(edges_med.mean()),
            "coarse_density": float(edges_coarse.mean()),
            "total_edges": int(edges_fine.sum()),
            "structure_level": "micro" if edges_fine.mean()>0.1 else ("meso" if edges_med.mean()>0.05 else "macro")
        }
    except Exception:
        g=gray_uint8.astype(np.float32)/255.0; gx=np.gradient(g,axis=1); gy=np.gradient(g,axis=0); mag=np.sqrt(gx**2+gy**2)
        e=mag>mag.mean()
        return {"fine":e,"medium":e,"coarse":e,"fine_density":float(e.mean()),
                "medium_density":float(e.mean()),"coarse_density":float(e.mean()),
                "total_edges":int(e.sum()),"structure_level":"meso"}

def orb_keypoints(gray_uint8):
    """ORB feature detection — Harris fallback if ORB unavailable."""
    try:
        if SKIMAGE_OK:
            try:
                from skimage.feature import ORB
                detector = ORB(n_keypoints=200, fast_threshold=0.05)
                detector.detect_and_extract(gray_uint8/255.0)
                kp = detector.keypoints
            except Exception:
                from skimage.feature import corner_harris, corner_peaks
                harris = corner_harris(gray_uint8/255.0)
                kp = corner_peaks(harris, min_distance=8, threshold_rel=0.02)
        else:
            # Numpy: local maxima as keypoints
            g = gray_uint8.astype(np.float32)
            gx = np.gradient(g, axis=1); gy = np.gradient(g, axis=0)
            mag = np.sqrt(gx**2+gy**2)
            # Simple non-max suppression on 8x8 blocks
            step=8; pts=[]
            for i in range(0,mag.shape[0]-step,step):
                for j in range(0,mag.shape[1]-step,step):
                    block=mag[i:i+step,j:j+step]
                    if block.max()>mag.mean()*1.8:
                        yi,xj=np.unravel_index(block.argmax(),block.shape)
                        pts.append([i+yi,j+xj])
            kp=np.array(pts) if pts else np.zeros((0,2))

        scales=np.ones(len(kp))
        if len(kp)>0 and SKLEARN_OK:
            n_cl=min(5,len(kp))
            try:
                kmk=KMeans(n_clusters=n_cl,random_state=42,n_init=5).fit(np.array(kp))
                centers=kmk.cluster_centers_
            except Exception:
                centers=np.array(kp)[:5]
        else:
            centers=np.array(kp)[:5] if len(kp)>0 else np.zeros((0,2))
        return {
            "keypoints": kp,
            "n_keypoints": len(kp),
            "cluster_centers": centers.tolist() if len(centers)>0 else [],
            "scales": scales.tolist(),
            "mean_scale": 1.0,
            "distribution": "uniforme" if len(kp)>5 and np.std(np.array(kp)[:,0])/(np.std(np.array(kp)[:,1])+1e-5)<1.5 else "concentrado"
        }
    except Exception:
        return {"keypoints":np.zeros((0,2)),"n_keypoints":0,"cluster_centers":[],"scales":[],"mean_scale":1.0,"distribution":"n/a"}

def glcm_texture(gray_uint8):
    """GLCM texture — pure numpy fallback if skimage unavailable."""
    try:
        if SKIMAGE_OK:
            from skimage.feature import graycomatrix, graycoprops
            g64 = (gray_uint8 // 4).astype(np.uint8)
            distances=[1,3,5]; angles=[0,np.pi/4,np.pi/2,3*np.pi/4]
            glcm=graycomatrix(g64,distances=distances,angles=angles,levels=64,symmetric=True,normed=True)
            features={}
            for prop in ['contrast','dissimilarity','homogeneity','energy','correlation','ASM']:
                v=graycoprops(glcm,prop)
                features[prop]=float(v.mean())
            features['contrast_std']=float(graycoprops(glcm,'contrast').std())
            features['uniformity']=features['energy']
            features['entropy']=float(-np.sum(glcm[glcm>0]*np.log2(glcm[glcm>0]+1e-12)))
        else:
            # Numpy-based texture statistics
            g=gray_uint8.astype(np.float32)/255.0
            gx=np.gradient(g,axis=1); gy=np.gradient(g,axis=0)
            contrast=float(np.sqrt(gx**2+gy**2).mean()*100)
            homogeneity=float(1.0/(1.0+contrast/50.0))
            # Local variance as energy proxy
            from numpy.lib.stride_tricks import as_strided
            energy=float(np.var(g))
            correlation=float(np.corrcoef(gx.ravel(),gy.ravel())[0,1]) if len(gx.ravel())>1 else 0.5
            hst=np.histogram(g,bins=64)[0]; hn=hst/hst.sum()+1e-12
            entropy_v=float(-np.sum(hn*np.log2(hn)))
            features={"contrast":round(contrast,4),"dissimilarity":round(contrast*0.5,4),
                      "homogeneity":round(homogeneity,4),"energy":round(energy,4),
                      "correlation":round(abs(correlation),4),"ASM":round(energy**2,4),
                      "contrast_std":0.0,"uniformity":round(energy,4),"entropy":round(entropy_v,4)}
        features['texture_type']=classify_texture(features)
        return features
    except Exception as e:
        return {"homogeneity":0.5,"contrast":20.0,"energy":0.1,"correlation":0.7,"ASM":0.01,
                "dissimilarity":10.0,"contrast_std":0.0,"uniformity":0.1,"entropy":4.0,"texture_type":"desconhecido","error":str(e)}

def classify_texture(f):
    if f.get('homogeneity',0) > 0.7: return "homogênea"
    if f.get('contrast',0) > 50: return "altamente texturizada"
    if f.get('energy',0) > 0.1: return "uniforme/periódica"
    if f.get('correlation',0) > 0.8: return "estruturada"
    return "complexa"

def kmeans_colors(img_arr, k=7):
    """KMeans dominant color extraction."""
    if not SKLEARN_OK:
        return [], []
    try:
        h, w = img_arr.shape[:2]
        # Sample pixels for speed
        step = max(1, (h*w) // 4000)
        flat = img_arr.reshape(-1,3)[::step].astype(np.float32)
        km = KMeans(n_clusters=k, random_state=42, n_init=5, max_iter=100).fit(flat)
        centers = km.cluster_centers_.astype(int)
        counts = Counter(km.labels_)
        total = sum(counts.values())
        palette = []
        for i in np.argsort([-counts[j] for j in range(k)]):
            r,g,b = centers[i]
            pct = counts[i]/total*100
            hex_c = "#{:02x}{:02x}{:02x}".format(int(r),int(g),int(b))
            palette.append({"rgb":(int(r),int(g),int(b)), "hex":hex_c, "pct":round(pct,1)})
        # Color temperature classification
        temps = []
        for c in palette[:3]:
            r,g,b = c['rgb']
            if r > b+20: temps.append("quente")
            elif b > r+20: temps.append("fria")
            else: temps.append("neutra")
        return palette, temps
    except:
        return [], []

def fft_analysis(gray_arr):
    """FFT frequency analysis for periodic structures."""
    fft = np.fft.fft2(gray_arr)
    fft_shift = np.fft.fftshift(fft)
    magnitude = np.abs(fft_shift)
    h, w = magnitude.shape
    center = magnitude[h//2-30:h//2+30, w//2-30:w//2+30]
    outer = np.concatenate([magnitude[:h//4,:].ravel(), magnitude[3*h//4:,:].ravel()])
    periodic_score = float(np.percentile(outer,99)) / (float(np.mean(outer))+1e-5)
    # Low/mid/high freq split
    total = magnitude.sum() + 1e-5
    r = min(h,w)//2
    Y,X = np.ogrid[:h,:w]
    dist = np.sqrt((X-w//2)**2+(Y-h//2)**2)
    lf = float(magnitude[dist < r*0.1].sum()/total)
    mf = float(magnitude[(dist>=r*0.1)&(dist<r*0.4)].sum()/total)
    hf = float(magnitude[dist>=r*0.4].sum()/total)
    return {
        "periodic_score": round(periodic_score,2),
        "is_periodic": periodic_score > 12,
        "low_freq": round(lf,3),
        "mid_freq": round(mf,3),
        "high_freq": round(hf,3),
        "dominant_scale": "fina" if hf>0.5 else ("média" if mf>0.3 else "grossa")
    }

def classify_scientific_image(sobel_r, canny_r, glcm_r, orb_r, fft_r, color_info, kmeans_palette):
    """Rule-based scientific image classification using all ML features."""
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

    # Score each category
    scores = {}

    # H&E Histopatologia: pinkish/purplish, high texture, many keypoints
    he_score = 0
    if mr > 140 and mb > 100 and mg < mr: he_score += 30
    if n_kp > 80: he_score += 20
    if contrast > 30: he_score += 20
    if ed > 0.12: he_score += 15
    if glcm_r.get("texture_type") == "complexa": he_score += 15
    scores["Histopatologia H&E"] = he_score

    # DAPI fluorescence: blue dominant
    dapi_score = 0
    if mb > 150 and mb > mr+30: dapi_score += 45
    if entropy > 5.0: dapi_score += 20
    if ed > 0.1: dapi_score += 20
    if n_kp > 30: dapi_score += 15
    scores["Fluorescência DAPI/Nuclear"] = dapi_score

    # GFP fluorescence: green dominant
    gfp_score = 0
    if mg > 150 and mg > mr+30: gfp_score += 45
    if entropy > 4.5: gfp_score += 20
    if ed > 0.08: gfp_score += 20
    scores["Fluorescência GFP/Verde"] = gfp_score

    # Crystallography/TEM: periodic, high FFT periodic score, high symmetry
    xray_score = 0
    if periodic: xray_score += 40
    if sym > 0.75: xray_score += 25
    if hom > 0.7: xray_score += 15
    if fft_r["periodic_score"] > 15: xray_score += 20
    scores["Cristalografia/Difração"] = xray_score

    # Western blot / gel: horizontal bands, low color variation
    wb_score = 0
    if contrast < 15 and hom > 0.8: wb_score += 30
    if abs(mr-mg)<20 and abs(mg-mb)<20: wb_score += 25  # grayscale
    if canny_r["coarse_density"] > canny_r["fine_density"]: wb_score += 25
    scores["Gel/Western Blot"] = wb_score

    # Chart/diagram: very structured, low texture entropy
    chart_score = 0
    if glcm_r.get("energy",0) > 0.15: chart_score += 30
    if hom > 0.85: chart_score += 25
    if n_kp < 30: chart_score += 20
    if entropy < 4.0: chart_score += 25
    scores["Gráfico/Diagrama Científico"] = chart_score

    # Molecular structure: high symmetry, periodic, blue/gray
    mol_score = 0
    if sym > 0.80: mol_score += 35
    if periodic: mol_score += 25
    if corr > 0.8: mol_score += 20
    if abs(mr-mg)<25 and abs(mg-mb)<25: mol_score += 20
    scores["Estrutura Molecular"] = mol_score

    # Confocal microscopy: colorful, multiple channels
    conf_score = 0
    if len(kmeans_palette) > 4: conf_score += 20
    if entropy > 5.5: conf_score += 25
    if n_kp > 50: conf_score += 20
    if ed > 0.10: conf_score += 20
    if contrast > 20: conf_score += 15
    scores["Microscopia Confocal"] = conf_score

    # Astronomy: dark background, bright spots
    astro_score = 0
    if color_info.get("brightness", 128) < 60: astro_score += 35
    if n_kp > 40 and hom > 0.7: astro_score += 25
    if entropy > 5.0: astro_score += 20
    if fft_r["high_freq"] > 0.4: astro_score += 20
    scores["Imagem Astronômica"] = astro_score

    best = max(scores, key=scores.get)
    best_score = scores[best]
    conf = min(96, 40 + best_score * 0.55)

    # Origin classification
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
        "all_scores": dict(sorted(scores.items(), key=lambda x:-x[1])[:5]),
    }

@st.cache_data(show_spinner=False)
def run_full_ml_pipeline(img_bytes):
    """Full ML analysis pipeline: Sobel + Canny + ORB + GLCM + KMeans + FFT."""
    result = {}
    try:
        img = PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
        orig_size = img.size
        # Resize for processing
        w, h = img.size
        scale = min(512/w, 512/h)
        new_w, new_h = int(w*scale), int(h*scale)
        img_r = img.resize((new_w, new_h), PILImage.LANCZOS)
        arr = np.array(img_r, dtype=np.float32)
        r_ch, g_ch, b_ch = arr[:,:,0], arr[:,:,1], arr[:,:,2]
        gray = 0.2989*r_ch + 0.5870*g_ch + 0.1140*b_ch
        gray_u8 = gray.astype(np.uint8)
        mr, mg, mb = float(r_ch.mean()), float(g_ch.mean()), float(b_ch.mean())

        # Symmetry analysis
        hy, hx = gray.shape[0]//2, gray.shape[1]//2
        q = [gray[:hy,:hx].var(), gray[:hy,hx:].var(), gray[hy:,:hx].var(), gray[hy:,hx:].var()]
        sym = 1.0 - (max(q)-min(q)) / (max(q)+1e-5)

        # Entropy
        hst = np.histogram(gray, bins=64, range=(0,255))[0]
        hn = hst/hst.sum(); hn = hn[hn>0]
        entropy = float(-np.sum(hn*np.log2(hn)))

        # Brightness stats
        brightness = float(gray.mean())
        std_bright = float(gray.std())

        color_info = {
            "r": round(mr,1), "g": round(mg,1), "b": round(mb,1),
            "symmetry": round(sym,3), "entropy": round(entropy,3),
            "brightness": round(brightness,1), "std": round(std_bright,1),
            "warm": mr > mb+15, "cool": mb > mr+15
        }

        # Run ML pipeline — all functions have internal fallbacks
        result["color"] = color_info
        result["size"] = orig_size
        result["sobel"] = sobel_analysis(gray/255.0)
        result["canny"] = canny_analysis(gray_u8)
        result["orb"]   = orb_keypoints(gray_u8)
        result["glcm"]  = glcm_texture(gray_u8)

        result["fft"] = fft_analysis(gray/255.0)
        result["kmeans_palette"], result["color_temps"] = kmeans_colors(arr.astype(np.uint8), k=7)

        # Histograms
        rh = np.histogram(r_ch.ravel(), bins=32, range=(0,255))[0].tolist()
        gh = np.histogram(g_ch.ravel(), bins=32, range=(0,255))[0].tolist()
        bh = np.histogram(b_ch.ravel(), bins=32, range=(0,255))[0].tolist()
        result["histograms"] = {"r":rh,"g":gh,"b":bh}

        # Classify
        result["classification"] = classify_scientific_image(
            result["sobel"], result["canny"], result["glcm"],
            result["orb"], result["fft"], color_info, result["kmeans_palette"]
        )

        # Create Sobel visualization (as array for plotly)
        if "magnitude" in result["sobel"]:
            mag_norm = result["sobel"]["magnitude"]
            result["sobel_viz"] = (mag_norm / (mag_norm.max()+1e-5) * 255).astype(np.uint8).tolist()
        result["array_shape"] = [new_h, new_w]
        result["ok"] = True
    except Exception as e:
        result["ok"] = False
        result["error"] = str(e)
    return result

# ── DOC ANALYSIS ────────────────────────────────
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
def kw_extract(text,n=25):
    if not text: return []
    words=re.findall(r'\b[a-záàâãéêíóôõúüçA-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]{4,}\b',text.lower())
    words=[w for w in words if w not in STOPWORDS]
    if not words: return []
    tf=Counter(words); tot=sum(tf.values())
    return [w for w,_ in sorted({w:c/tot for w,c in tf.items()}.items(),key=lambda x:-x[1])[:n]]

def topic_dist(kws):
    tm={"Saúde & Medicina":["saúde","medicina","clínico","health","medical","therapy","disease"],"Biologia":["biologia","genômica","gene","dna","rna","proteína","célula","crispr"],"Neurociência":["neurociência","neural","cérebro","cognição","memória","sono","brain"],"Computação & IA":["algoritmo","machine","learning","inteligência","dados","computação","ia","deep","quantum"],"Física":["física","quântica","partícula","energia","galáxia","astrofísica","cosmologia"],"Química":["química","molécula","síntese","reação","polímero"],"Engenharia":["engenharia","sistema","robótica","automação"],"Ciências Sociais":["sociedade","cultura","educação","política","psicologia"],"Ecologia":["ecologia","clima","ambiente","biodiversidade"],"Matemática":["matemática","estatística","probabilidade","equação"]}
    s=defaultdict(int)
    for kw in kws:
        for tp,terms in tm.items():
            if any(t in kw or kw in t for t in terms): s[tp]+=1
    return dict(sorted(s.items(),key=lambda x:-x[1])) if s else {"Pesquisa Geral":1}

@st.cache_data(show_spinner=False)
def analyze_doc(fname,fbytes,ftype,area=""):
    r={"file":fname,"type":ftype,"keywords":[],"topics":{},"relevance_score":0,"summary":"","strengths":[],"improvements":[],"writing_quality":0,"reading_time":0,"word_count":0}
    text=""
    if ftype=="PDF" and fbytes: text=extract_pdf(fbytes)
    elif fbytes:
        try: text=fbytes.decode("utf-8",errors="ignore")[:40000]
        except: pass
    if text:
        r["keywords"]=kw_extract(text,25)
        r["topics"]=topic_dist(r["keywords"])
        words=len(text.split()); r["word_count"]=words; r["reading_time"]=max(1,round(words/200))
        r["writing_quality"]=min(100,50+(15 if len(r["keywords"])>15 else 0)+(15 if words>1000 else 0)+(10 if r["reading_time"]>3 else 0))
        if area:
            aw=area.lower().split(); rel=sum(1 for w in aw if any(w in kw for kw in r["keywords"]))
            r["relevance_score"]=min(100,rel*15+45)
        else: r["relevance_score"]=65
        r["strengths"]=[f"Vocabulário rico ({len(r['keywords'])} termos)"] if len(r["keywords"])>15 else []
        r["improvements"]=["Expandir o conteúdo"] if words<500 else []
        r["summary"]=f"{ftype} · {words} palavras · ~{r['reading_time']}min · {', '.join(list(r['topics'].keys())[:2])} · {', '.join(r['keywords'][:4])}"
    else:
        r["summary"]=f"Arquivo {ftype}."; r["relevance_score"]=50
        r["keywords"]=kw_extract(fname.lower(),5); r["topics"]=topic_dist(r["keywords"])
    return r

# ── SEARCH ──────────────────────────────────────
@st.cache_data(show_spinner=False)
def search_ss(q,lim=6):
    try:
        r=requests.get("https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query":q,"limit":lim,"fields":"title,authors,year,abstract,venue,externalIds,openAccessPdf,citationCount"},timeout=8)
        if r.status_code==200:
            out=[]
            for p in r.json().get("data",[]):
                ext=p.get("externalIds",{}) or {}; doi=ext.get("DOI",""); arx=ext.get("ArXiv","")
                pdf=p.get("openAccessPdf") or {}
                link=pdf.get("url","") or(f"https://arxiv.org/abs/{arx}" if arx else(f"https://doi.org/{doi}" if doi else ""))
                al=p.get("authors",[]) or []; au=", ".join(a.get("name","") for a in al[:3])
                if len(al)>3: au+=" et al."
                out.append({"title":p.get("title","Sem título"),"authors":au or "—","year":p.get("year","?"),
                    "source":p.get("venue","") or "Semantic Scholar","doi":doi or arx or "—",
                    "abstract":(p.get("abstract","") or "")[:250],"url":link,
                    "citations":p.get("citationCount",0),"origin":"semantic"})
            return out
    except: pass
    return []

@st.cache_data(show_spinner=False)
def search_cr(q,lim=3):
    try:
        r=requests.get("https://api.crossref.org/works",
            params={"query":q,"rows":lim,"select":"title,author,issued,abstract,DOI,container-title,is-referenced-by-count","mailto":"nebula@example.com"},timeout=8)
        if r.status_code==200:
            out=[]
            for p in r.json().get("message",{}).get("items",[]):
                title=(p.get("title") or ["?"])[0]; ars=p.get("author",[]) or []
                au=", ".join(f'{a.get("given","").split()[0] if a.get("given") else ""} {a.get("family","")}'.strip() for a in ars[:3])
                if len(ars)>3: au+=" et al."
                yr=(p.get("issued",{}).get("date-parts") or [[None]])[0][0]
                doi=p.get("DOI",""); ab=re.sub(r'<[^>]+>','',p.get("abstract","") or "")[:250]
                out.append({"title":title,"authors":au or "—","year":yr or "?",
                    "source":(p.get("container-title") or ["CrossRef"])[0],"doi":doi,
                    "abstract":ab,"url":f"https://doi.org/{doi}" if doi else "","citations":p.get("is-referenced-by-count",0),"origin":"crossref"})
            return out
    except: pass
    return []

def record(tags,w=1.0):
    e=st.session_state.get("current_user")
    if not e or not tags: return
    p=st.session_state.user_prefs.setdefault(e,defaultdict(float))
    for t in tags: p[t.lower()]+=w
    save_db()

def get_recs(email,n=2):
    pr=st.session_state.user_prefs.get(email,{})
    if not pr: return []
    def sc(p): return sum(pr.get(t.lower(),0) for t in p.get("tags",[])+p.get("connections",[]))
    scored=[(sc(p),p) for p in st.session_state.feed_posts if email not in p.get("liked_by",[])]
    return [p for s,p in sorted(scored,key=lambda x:-x[0]) if s>0][:n]

def area_tags(area):
    a=(area or "").lower()
    M={"ia":["machine learning","LLM"],"inteligência artificial":["machine learning","LLM"],
       "neurociência":["sono","memória","cognição"],"biologia":["célula","genômica"],
       "física":["quantum","astrofísica"],"medicina":["diagnóstico","terapia"]}
    for k,v in M.items():
        if k in a: return v
    return [w.strip() for w in a.replace(","," ").split() if len(w)>3][:5]

EMAP={"pdf":"PDF","docx":"Word","xlsx":"Planilha","csv":"Dados","txt":"Texto","py":"Código","md":"Markdown","png":"Imagem","jpg":"Imagem","jpeg":"Imagem"}
def ftype(fname): return EMAP.get(fname.split(".")[-1].lower() if "." in fname else "","Arquivo")

VIB=["#FFD60A","#06D6A0","#FF3B5C","#4CC9F0","#B17DFF","#FF8C42","#FF4E8A","#00C9A7","#FFAB00","#7BD3FF"]

# ═══════════════════════════════════════════════════
#  CSS
# ═══════════════════════════════════════════════════
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800;900&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
  --bg:#07080F; --bg2:#0D0E1A; --bg3:#141528;
  --yel:#FFD60A; --yel2:#FFEC47;
  --grn:#06D6A0; --grn2:#00F5C4;
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
.stApp::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;background:radial-gradient(ellipse 60% 50% at -5% 0%,rgba(255,214,10,.07) 0%,transparent 60%),radial-gradient(ellipse 50% 40% at 105% 0%,rgba(76,201,240,.07) 0%,transparent 55%),radial-gradient(ellipse 40% 50% at 50% 110%,rgba(6,214,160,.06) 0%,transparent 60%);}
.stApp::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;background-image:linear-gradient(rgba(255,255,255,.012) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.012) 1px,transparent 1px);background-size:60px 60px;}
header[data-testid="stHeader"],#MainMenu,footer,.stDeployButton,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
[data-testid="stSidebarCollapseButton"]{display:none!important}
/* Force sidebar always open */
section[data-testid="stSidebar"]{
  display:block!important;
  transform:translateX(0)!important;
  visibility:visible!important;
  background:rgba(8,9,18,.99)!important;
  border-right:1px solid rgba(255,255,255,.1)!important;
  width:210px!important;min-width:210px!important;max-width:210px!important;
  padding:1.2rem .8rem 1rem!important;
}
section[data-testid="stSidebar"]>div{width:210px!important;padding:0!important;}
[data-testid="collapsedControl"]{display:none!important}
.block-container{padding-top:.3rem!important;padding-bottom:4rem!important;max-width:1380px!important;position:relative;z-index:1;padding-left:.8rem!important;padding-right:.8rem!important;}
/* ALL buttons - visible, simple */
.stButton>button{
  background:rgba(255,255,255,.09)!important;
  border:1px solid rgba(255,255,255,.14)!important;
  border-radius:10px!important;
  color:#D0D2E0!important;
  -webkit-text-fill-color:#D0D2E0!important;
  font-family:'DM Sans',sans-serif!important;
  font-weight:500!important;font-size:.83rem!important;
  padding:.46rem .8rem!important;
  transition:background .1s!important;
  box-shadow:none!important;
  line-height:1.4!important;
}
.stButton>button:hover{
  background:rgba(255,255,255,.16)!important;
  color:#FFFFFF!important;-webkit-text-fill-color:#FFFFFF!important;
}
.stButton>button:active{transform:scale(.97)!important;}
.stButton>button p,.stButton>button span{color:inherit!important;-webkit-text-fill-color:inherit!important;}
/* Sidebar buttons: left-aligned, full-width */
section[data-testid="stSidebar"] .stButton>button{
  text-align:left!important;
  justify-content:flex-start!important;
  width:100%!important;
  margin-bottom:.15rem!important;
  padding:.5rem .85rem!important;
  font-size:.85rem!important;
}
/* sb-logo and labels */
.sb-logo{display:flex;align-items:center;gap:9px;margin-bottom:1.5rem;padding:.2rem .3rem;}
.sb-logo-icon{width:34px;height:34px;border-radius:10px;background:linear-gradient(135deg,#FFD60A,#FF8C42);display:flex;align-items:center;justify-content:center;font-size:.9rem;flex-shrink:0;}
.sb-logo-txt{font-family:'Syne',sans-serif;font-weight:900;font-size:1.2rem;letter-spacing:-.04em;background:linear-gradient(135deg,#FFD60A,#06D6A0);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.sb-lbl{font-size:.54rem;font-weight:700;color:#404460;letter-spacing:.14em;text-transform:uppercase;padding:0 .2rem;margin-bottom:.35rem;margin-top:.8rem;}
.stTextInput input,.stTextArea textarea{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;color:var(--t1)!important;font-family:'DM Sans',sans-serif!important;font-size:.84rem!important;}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:rgba(255,214,10,.4)!important;box-shadow:0 0 0 3px rgba(255,214,10,.08)!important;}
.stTextInput label,.stTextArea label,.stSelectbox label,.stFileUploader label,.stNumberInput label{color:var(--t3)!important;font-size:.60rem!important;letter-spacing:.10em!important;text-transform:uppercase!important;font-weight:600!important;}
.glass{background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.10);border-radius:var(--r20);box-shadow:0 0 0 1px rgba(255,255,255,.04) inset,0 4px 32px rgba(0,0,0,.3);position:relative;overflow:hidden;}
.glass::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.08),transparent);pointer-events:none;}
.post-card{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.09);border-radius:var(--r20);margin-bottom:.65rem;overflow:hidden;box-shadow:0 2px 20px rgba(0,0,0,.25);transition:border-color .14s,transform .14s;}
.post-card:hover{border-color:rgba(255,255,255,.15);transform:translateY(-1px);}
.sc{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.09);border-radius:var(--r20);padding:.9rem 1rem;margin-bottom:.6rem;}
.scard{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:var(--r16);padding:.8rem 1rem;margin-bottom:.42rem;transition:border-color .13s,transform .13s;}
.scard:hover{border-color:rgba(255,255,255,.14);transform:translateY(-1px);}
.mbox{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.09);border-radius:var(--r16);padding:.9rem;text-align:center;}
.abox{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.10);border-radius:var(--r16);padding:1rem;margin-bottom:.6rem;}
.pbox-grn{background:rgba(6,214,160,.07);border:1px solid rgba(6,214,160,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.55rem;}
.pbox-yel{background:rgba(255,214,10,.07);border:1px solid rgba(255,214,10,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.55rem;}
.pbox-blu{background:rgba(76,201,240,.07);border:1px solid rgba(76,201,240,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.55rem;}
.pbox-pur{background:rgba(177,125,255,.07);border:1px solid rgba(177,125,255,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.55rem;}
.chart-wrap{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);border-radius:var(--r12);padding:.65rem;margin-bottom:.6rem;}
.compose-box{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.11);border-radius:var(--r20);padding:1.1rem 1.3rem;margin-bottom:.8rem;}
.mval-yel{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;background:linear-gradient(135deg,var(--yel),var(--orn));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-grn{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;background:linear-gradient(135deg,var(--grn),var(--blu));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-blu{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;background:linear-gradient(135deg,var(--blu),var(--pur));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-red{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;background:linear-gradient(135deg,var(--red),var(--orn));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mlbl{font-size:.58rem;color:var(--t3);margin-top:4px;letter-spacing:.1em;text-transform:uppercase;font-weight:700;}
.tag{display:inline-block;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.09);border-radius:50px;padding:2px 9px;font-size:.63rem;color:var(--t2);margin:2px;font-weight:500;}
.badge-yel{display:inline-block;background:rgba(255,214,10,.12);border:1px solid rgba(255,214,10,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--yel);}
.badge-grn{display:inline-block;background:rgba(6,214,160,.12);border:1px solid rgba(6,214,160,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--grn);}
.badge-red{display:inline-block;background:rgba(255,59,92,.12);border:1px solid rgba(255,59,92,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--red);}
.badge-blu{display:inline-block;background:rgba(76,201,240,.12);border:1px solid rgba(76,201,240,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--blu);}
.badge-pur{display:inline-block;background:rgba(177,125,255,.12);border:1px solid rgba(177,125,255,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--pur);}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.45;transform:scale(.7)}}
.dot-on{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--grn);animation:pulse 2.5s infinite;margin-right:4px;vertical-align:middle;}
.dot-off{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--t4);margin-right:4px;vertical-align:middle;}
@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.pw{animation:fadeUp .18s ease both;}
.bme{background:linear-gradient(135deg,rgba(255,214,10,.15),rgba(255,140,66,.1));border:1px solid rgba(255,214,10,.2);border-radius:18px 18px 4px 18px;padding:.55rem .88rem;max-width:70%;margin-left:auto;margin-bottom:5px;font-size:.82rem;line-height:1.6;}
.bthem{background:var(--g2);border:1px solid var(--gb1);border-radius:18px 18px 18px 4px;padding:.55rem .88rem;max-width:70%;margin-bottom:5px;font-size:.82rem;line-height:1.6;}
.cmt{background:rgba(255,255,255,.03);border:1px solid var(--gb1);border-radius:var(--r12);padding:.5rem .85rem;margin-bottom:.25rem;}
.stTabs [data-baseweb="tab-list"]{background:rgba(255,255,255,.03)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;padding:3px!important;gap:2px!important;}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--t3)!important;border-radius:9px!important;font-size:.75rem!important;font-family:'DM Sans',sans-serif!important;font-weight:500!important;}
.stTabs [aria-selected="true"]{background:var(--g3)!important;color:var(--yel)!important;border:1px solid rgba(255,214,10,.2)!important;font-weight:700!important;}
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
/* colored accent buttons */
input[type="number"]{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;color:var(--t1)!important;}
/* AI Result card */
.ai-card{background:linear-gradient(135deg,rgba(255,214,10,.06),rgba(6,21



#x27;, '', text, flags=re.DOTALL)
            return json.loads(text), None
        return None, f"HTTP {resp.status_code}"
    except Exception as e:
        return None, str(e)

# ════════════════════════════════════════════════
#  REAL ML IMAGE ANALYSIS PIPELINE
# ════════════════════════════════════════════════
def sobel_analysis(gray_arr):
    """Multi-directional Sobel edge detection — numpy fallback if skimage unavailable."""
    try:
        if SKIMAGE_OK:
            import skimage.filters as skf
            sx = skf.sobel_h(gray_arr)
            sy = skf.sobel_v(gray_arr)
        else:
            # Pure numpy Sobel
            kx = np.array([[-1,0,1],[-2,0,2],[-1,0,1]], dtype=np.float32)/8.0
            ky = kx.T
            from numpy import pad as nppad
            def conv2d(img, k):
                ph,pw=k.shape[0]//2,k.shape[1]//2
                padded=nppad(img,((ph,ph),(pw,pw)),mode='edge')
                out=np.zeros_like(img)
                for i in range(k.shape[0]):
                    for j in range(k.shape[1]):
                        out+=k[i,j]*padded[i:i+img.shape[0],j:j+img.shape[1]]
                return out
            sx=conv2d(gray_arr.astype(np.float32),kx)
            sy=conv2d(gray_arr.astype(np.float32),ky)
        magnitude = np.sqrt(sx**2 + sy**2)
        direction = np.arctan2(sy, sx) * 180 / np.pi
        # Diagonal via numpy gradient
        try:
            gx2 = np.gradient(gray_arr, axis=1)
            gy2 = np.gradient(gray_arr, axis=0)
        except Exception:
            gx2, gy2 = sx, sy
        return {
            "magnitude": magnitude,
            "horizontal": sx,
            "vertical": sy,
            "mean_edge": float(magnitude.mean()),
            "max_edge": float(magnitude.max()),
            "edge_density": float((magnitude > magnitude.mean()*1.5).mean()),
            "dominant_direction": float(direction.mean()),
            "edge_hist": np.histogram(magnitude, bins=16, range=(0, magnitude.max()+1e-5))[0].tolist()
        }
    except Exception as e:
        # Ultra-safe fallback
        gx = np.gradient(gray_arr.astype(np.float32), axis=1)
        gy = np.gradient(gray_arr.astype(np.float32), axis=0)
        mag = np.sqrt(gx**2+gy**2)
        return {"magnitude":mag,"horizontal":gx,"vertical":gy,
                "mean_edge":float(mag.mean()),"max_edge":float(mag.max()),
                "edge_density":float((mag>mag.mean()*1.5).mean()),
                "dominant_direction":0.0,
                "edge_hist":np.histogram(mag,bins=16)[0].tolist()}

def canny_analysis(gray_uint8):
    """Canny multi-scale edge detection — numpy fallback."""
    try:
        if SKIMAGE_OK:
            from skimage import feature as skf2
            edges_fine   = skf2.canny(gray_uint8/255.0, sigma=1.0)
            edges_med    = skf2.canny(gray_uint8/255.0, sigma=2.0)
            edges_coarse = skf2.canny(gray_uint8/255.0, sigma=3.5)
        else:
            # Numpy gradient-based edge approximation
            g = gray_uint8.astype(np.float32)/255.0
            gx=np.gradient(g,axis=1); gy=np.gradient(g,axis=0); mag=np.sqrt(gx**2+gy**2)
            t1,t2,t3=np.percentile(mag,85),np.percentile(mag,75),np.percentile(mag,65)
            edges_fine=mag>t1; edges_med=mag>t2; edges_coarse=mag>t3
        return {
            "fine": edges_fine, "medium": edges_med, "coarse": edges_coarse,
            "fine_density": float(edges_fine.mean()),
            "medium_density": float(edges_med.mean()),
            "coarse_density": float(edges_coarse.mean()),
            "total_edges": int(edges_fine.sum()),
            "structure_level": "micro" if edges_fine.mean()>0.1 else ("meso" if edges_med.mean()>0.05 else "macro")
        }
    except Exception:
        g=gray_uint8.astype(np.float32)/255.0; gx=np.gradient(g,axis=1); gy=np.gradient(g,axis=0); mag=np.sqrt(gx**2+gy**2)
        e=mag>mag.mean()
        return {"fine":e,"medium":e,"coarse":e,"fine_density":float(e.mean()),
                "medium_density":float(e.mean()),"coarse_density":float(e.mean()),
                "total_edges":int(e.sum()),"structure_level":"meso"}

def orb_keypoints(gray_uint8):
    """ORB feature detection — Harris fallback if ORB unavailable."""
    try:
        if SKIMAGE_OK:
            try:
                from skimage.feature import ORB
                detector = ORB(n_keypoints=200, fast_threshold=0.05)
                detector.detect_and_extract(gray_uint8/255.0)
                kp = detector.keypoints
            except Exception:
                from skimage.feature import corner_harris, corner_peaks
                harris = corner_harris(gray_uint8/255.0)
                kp = corner_peaks(harris, min_distance=8, threshold_rel=0.02)
        else:
            # Numpy: local maxima as keypoints
            g = gray_uint8.astype(np.float32)
            gx = np.gradient(g, axis=1); gy = np.gradient(g, axis=0)
            mag = np.sqrt(gx**2+gy**2)
            # Simple non-max suppression on 8x8 blocks
            step=8; pts=[]
            for i in range(0,mag.shape[0]-step,step):
                for j in range(0,mag.shape[1]-step,step):
                    block=mag[i:i+step,j:j+step]
                    if block.max()>mag.mean()*1.8:
                        yi,xj=np.unravel_index(block.argmax(),block.shape)
                        pts.append([i+yi,j+xj])
            kp=np.array(pts) if pts else np.zeros((0,2))

        scales=np.ones(len(kp))
        if len(kp)>0 and SKLEARN_OK:
            n_cl=min(5,len(kp))
            try:
                kmk=KMeans(n_clusters=n_cl,random_state=42,n_init=5).fit(np.array(kp))
                centers=kmk.cluster_centers_
            except Exception:
                centers=np.array(kp)[:5]
        else:
            centers=np.array(kp)[:5] if len(kp)>0 else np.zeros((0,2))
        return {
            "keypoints": kp,
            "n_keypoints": len(kp),
            "cluster_centers": centers.tolist() if len(centers)>0 else [],
            "scales": scales.tolist(),
            "mean_scale": 1.0,
            "distribution": "uniforme" if len(kp)>5 and np.std(np.array(kp)[:,0])/(np.std(np.array(kp)[:,1])+1e-5)<1.5 else "concentrado"
        }
    except Exception:
        return {"keypoints":np.zeros((0,2)),"n_keypoints":0,"cluster_centers":[],"scales":[],"mean_scale":1.0,"distribution":"n/a"}

def glcm_texture(gray_uint8):
    """GLCM texture — pure numpy fallback if skimage unavailable."""
    try:
        if SKIMAGE_OK:
            from skimage.feature import graycomatrix, graycoprops
            g64 = (gray_uint8 // 4).astype(np.uint8)
            distances=[1,3,5]; angles=[0,np.pi/4,np.pi/2,3*np.pi/4]
            glcm=graycomatrix(g64,distances=distances,angles=angles,levels=64,symmetric=True,normed=True)
            features={}
            for prop in ['contrast','dissimilarity','homogeneity','energy','correlation','ASM']:
                v=graycoprops(glcm,prop)
                features[prop]=float(v.mean())
            features['contrast_std']=float(graycoprops(glcm,'contrast').std())
            features['uniformity']=features['energy']
            features['entropy']=float(-np.sum(glcm[glcm>0]*np.log2(glcm[glcm>0]+1e-12)))
        else:
            # Numpy-based texture statistics
            g=gray_uint8.astype(np.float32)/255.0
            gx=np.gradient(g,axis=1); gy=np.gradient(g,axis=0)
            contrast=float(np.sqrt(gx**2+gy**2).mean()*100)
            homogeneity=float(1.0/(1.0+contrast/50.0))
            # Local variance as energy proxy
            from numpy.lib.stride_tricks import as_strided
            energy=float(np.var(g))
            correlation=float(np.corrcoef(gx.ravel(),gy.ravel())[0,1]) if len(gx.ravel())>1 else 0.5
            hst=np.histogram(g,bins=64)[0]; hn=hst/hst.sum()+1e-12
            entropy_v=float(-np.sum(hn*np.log2(hn)))
            features={"contrast":round(contrast,4),"dissimilarity":round(contrast*0.5,4),
                      "homogeneity":round(homogeneity,4),"energy":round(energy,4),
                      "correlation":round(abs(correlation),4),"ASM":round(energy**2,4),
                      "contrast_std":0.0,"uniformity":round(energy,4),"entropy":round(entropy_v,4)}
        features['texture_type']=classify_texture(features)
        return features
    except Exception as e:
        return {"homogeneity":0.5,"contrast":20.0,"energy":0.1,"correlation":0.7,"ASM":0.01,
                "dissimilarity":10.0,"contrast_std":0.0,"uniformity":0.1,"entropy":4.0,"texture_type":"desconhecido","error":str(e)}

def classify_texture(f):
    if f.get('homogeneity',0) > 0.7: return "homogênea"
    if f.get('contrast',0) > 50: return "altamente texturizada"
    if f.get('energy',0) > 0.1: return "uniforme/periódica"
    if f.get('correlation',0) > 0.8: return "estruturada"
    return "complexa"

def kmeans_colors(img_arr, k=7):
    """KMeans dominant color extraction."""
    if not SKLEARN_OK:
        return [], []
    try:
        h, w = img_arr.shape[:2]
        # Sample pixels for speed
        step = max(1, (h*w) // 4000)
        flat = img_arr.reshape(-1,3)[::step].astype(np.float32)
        km = KMeans(n_clusters=k, random_state=42, n_init=5, max_iter=100).fit(flat)
        centers = km.cluster_centers_.astype(int)
        counts = Counter(km.labels_)
        total = sum(counts.values())
        palette = []
        for i in np.argsort([-counts[j] for j in range(k)]):
            r,g,b = centers[i]
            pct = counts[i]/total*100
            hex_c = "#{:02x}{:02x}{:02x}".format(int(r),int(g),int(b))
            palette.append({"rgb":(int(r),int(g),int(b)), "hex":hex_c, "pct":round(pct,1)})
        # Color temperature classification
        temps = []
        for c in palette[:3]:
            r,g,b = c['rgb']
            if r > b+20: temps.append("quente")
            elif b > r+20: temps.append("fria")
            else: temps.append("neutra")
        return palette, temps
    except:
        return [], []

def fft_analysis(gray_arr):
    """FFT frequency analysis for periodic structures."""
    fft = np.fft.fft2(gray_arr)
    fft_shift = np.fft.fftshift(fft)
    magnitude = np.abs(fft_shift)
    h, w = magnitude.shape
    center = magnitude[h//2-30:h//2+30, w//2-30:w//2+30]
    outer = np.concatenate([magnitude[:h//4,:].ravel(), magnitude[3*h//4:,:].ravel()])
    periodic_score = float(np.percentile(outer,99)) / (float(np.mean(outer))+1e-5)
    # Low/mid/high freq split
    total = magnitude.sum() + 1e-5
    r = min(h,w)//2
    Y,X = np.ogrid[:h,:w]
    dist = np.sqrt((X-w//2)**2+(Y-h//2)**2)
    lf = float(magnitude[dist < r*0.1].sum()/total)
    mf = float(magnitude[(dist>=r*0.1)&(dist<r*0.4)].sum()/total)
    hf = float(magnitude[dist>=r*0.4].sum()/total)
    return {
        "periodic_score": round(periodic_score,2),
        "is_periodic": periodic_score > 12,
        "low_freq": round(lf,3),
        "mid_freq": round(mf,3),
        "high_freq": round(hf,3),
        "dominant_scale": "fina" if hf>0.5 else ("média" if mf>0.3 else "grossa")
    }

def classify_scientific_image(sobel_r, canny_r, glcm_r, orb_r, fft_r, color_info, kmeans_palette):
    """Rule-based scientific image classification using all ML features."""
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

    # Score each category
    scores = {}

    # H&E Histopatologia: pinkish/purplish, high texture, many keypoints
    he_score = 0
    if mr > 140 and mb > 100 and mg < mr: he_score += 30
    if n_kp > 80: he_score += 20
    if contrast > 30: he_score += 20
    if ed > 0.12: he_score += 15
    if glcm_r.get("texture_type") == "complexa": he_score += 15
    scores["Histopatologia H&E"] = he_score

    # DAPI fluorescence: blue dominant
    dapi_score = 0
    if mb > 150 and mb > mr+30: dapi_score += 45
    if entropy > 5.0: dapi_score += 20
    if ed > 0.1: dapi_score += 20
    if n_kp > 30: dapi_score += 15
    scores["Fluorescência DAPI/Nuclear"] = dapi_score

    # GFP fluorescence: green dominant
    gfp_score = 0
    if mg > 150 and mg > mr+30: gfp_score += 45
    if entropy > 4.5: gfp_score += 20
    if ed > 0.08: gfp_score += 20
    scores["Fluorescência GFP/Verde"] = gfp_score

    # Crystallography/TEM: periodic, high FFT periodic score, high symmetry
    xray_score = 0
    if periodic: xray_score += 40
    if sym > 0.75: xray_score += 25
    if hom > 0.7: xray_score += 15
    if fft_r["periodic_score"] > 15: xray_score += 20
    scores["Cristalografia/Difração"] = xray_score

    # Western blot / gel: horizontal bands, low color variation
    wb_score = 0
    if contrast < 15 and hom > 0.8: wb_score += 30
    if abs(mr-mg)<20 and abs(mg-mb)<20: wb_score += 25  # grayscale
    if canny_r["coarse_density"] > canny_r["fine_density"]: wb_score += 25
    scores["Gel/Western Blot"] = wb_score

    # Chart/diagram: very structured, low texture entropy
    chart_score = 0
    if glcm_r.get("energy",0) > 0.15: chart_score += 30
    if hom > 0.85: chart_score += 25
    if n_kp < 30: chart_score += 20
    if entropy < 4.0: chart_score += 25
    scores["Gráfico/Diagrama Científico"] = chart_score

    # Molecular structure: high symmetry, periodic, blue/gray
    mol_score = 0
    if sym > 0.80: mol_score += 35
    if periodic: mol_score += 25
    if corr > 0.8: mol_score += 20
    if abs(mr-mg)<25 and abs(mg-mb)<25: mol_score += 20
    scores["Estrutura Molecular"] = mol_score

    # Confocal microscopy: colorful, multiple channels
    conf_score = 0
    if len(kmeans_palette) > 4: conf_score += 20
    if entropy > 5.5: conf_score += 25
    if n_kp > 50: conf_score += 20
    if ed > 0.10: conf_score += 20
    if contrast > 20: conf_score += 15
    scores["Microscopia Confocal"] = conf_score

    # Astronomy: dark background, bright spots
    astro_score = 0
    if color_info.get("brightness", 128) < 60: astro_score += 35
    if n_kp > 40 and hom > 0.7: astro_score += 25
    if entropy > 5.0: astro_score += 20
    if fft_r["high_freq"] > 0.4: astro_score += 20
    scores["Imagem Astronômica"] = astro_score

    best = max(scores, key=scores.get)
    best_score = scores[best]
    conf = min(96, 40 + best_score * 0.55)

    # Origin classification
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
        "all_scores": dict(sorted(scores.items(), key=lambda x:-x[1])[:5]),
    }

@st.cache_data(show_spinner=False)
def run_full_ml_pipeline(img_bytes):
    """Full ML analysis pipeline: Sobel + Canny + ORB + GLCM + KMeans + FFT."""
    result = {}
    try:
        img = PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
        orig_size = img.size
        # Resize for processing
        w, h = img.size
        scale = min(512/w, 512/h)
        new_w, new_h = int(w*scale), int(h*scale)
        img_r = img.resize((new_w, new_h), PILImage.LANCZOS)
        arr = np.array(img_r, dtype=np.float32)
        r_ch, g_ch, b_ch = arr[:,:,0], arr[:,:,1], arr[:,:,2]
        gray = 0.2989*r_ch + 0.5870*g_ch + 0.1140*b_ch
        gray_u8 = gray.astype(np.uint8)
        mr, mg, mb = float(r_ch.mean()), float(g_ch.mean()), float(b_ch.mean())

        # Symmetry analysis
        hy, hx = gray.shape[0]//2, gray.shape[1]//2
        q = [gray[:hy,:hx].var(), gray[:hy,hx:].var(), gray[hy:,:hx].var(), gray[hy:,hx:].var()]
        sym = 1.0 - (max(q)-min(q)) / (max(q)+1e-5)

        # Entropy
        hst = np.histogram(gray, bins=64, range=(0,255))[0]
        hn = hst/hst.sum(); hn = hn[hn>0]
        entropy = float(-np.sum(hn*np.log2(hn)))

        # Brightness stats
        brightness = float(gray.mean())
        std_bright = float(gray.std())

        color_info = {
            "r": round(mr,1), "g": round(mg,1), "b": round(mb,1),
            "symmetry": round(sym,3), "entropy": round(entropy,3),
            "brightness": round(brightness,1), "std": round(std_bright,1),
            "warm": mr > mb+15, "cool": mb > mr+15
        }

        # Run ML pipeline — all functions have internal fallbacks
        result["color"] = color_info
        result["size"] = orig_size
        result["sobel"] = sobel_analysis(gray/255.0)
        result["canny"] = canny_analysis(gray_u8)
        result["orb"]   = orb_keypoints(gray_u8)
        result["glcm"]  = glcm_texture(gray_u8)

        result["fft"] = fft_analysis(gray/255.0)
        result["kmeans_palette"], result["color_temps"] = kmeans_colors(arr.astype(np.uint8), k=7)

        # Histograms
        rh = np.histogram(r_ch.ravel(), bins=32, range=(0,255))[0].tolist()
        gh = np.histogram(g_ch.ravel(), bins=32, range=(0,255))[0].tolist()
        bh = np.histogram(b_ch.ravel(), bins=32, range=(0,255))[0].tolist()
        result["histograms"] = {"r":rh,"g":gh,"b":bh}

        # Classify
        result["classification"] = classify_scientific_image(
            result["sobel"], result["canny"], result["glcm"],
            result["orb"], result["fft"], color_info, result["kmeans_palette"]
        )

        # Create Sobel visualization (as array for plotly)
        if "magnitude" in result["sobel"]:
            mag_norm = result["sobel"]["magnitude"]
            result["sobel_viz"] = (mag_norm / (mag_norm.max()+1e-5) * 255).astype(np.uint8).tolist()
        result["array_shape"] = [new_h, new_w]
        result["ok"] = True
    except Exception as e:
        result["ok"] = False
        result["error"] = str(e)
    return result

# ── DOC ANALYSIS ────────────────────────────────
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
def kw_extract(text,n=25):
    if not text: return []
    words=re.findall(r'\b[a-záàâãéêíóôõúüçA-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]{4,}\b',text.lower())
    words=[w for w in words if w not in STOPWORDS]
    if not words: return []
    tf=Counter(words); tot=sum(tf.values())
    return [w for w,_ in sorted({w:c/tot for w,c in tf.items()}.items(),key=lambda x:-x[1])[:n]]

def topic_dist(kws):
    tm={"Saúde & Medicina":["saúde","medicina","clínico","health","medical","therapy","disease"],"Biologia":["biologia","genômica","gene","dna","rna","proteína","célula","crispr"],"Neurociência":["neurociência","neural","cérebro","cognição","memória","sono","brain"],"Computação & IA":["algoritmo","machine","learning","inteligência","dados","computação","ia","deep","quantum"],"Física":["física","quântica","partícula","energia","galáxia","astrofísica","cosmologia"],"Química":["química","molécula","síntese","reação","polímero"],"Engenharia":["engenharia","sistema","robótica","automação"],"Ciências Sociais":["sociedade","cultura","educação","política","psicologia"],"Ecologia":["ecologia","clima","ambiente","biodiversidade"],"Matemática":["matemática","estatística","probabilidade","equação"]}
    s=defaultdict(int)
    for kw in kws:
        for tp,terms in tm.items():
            if any(t in kw or kw in t for t in terms): s[tp]+=1
    return dict(sorted(s.items(),key=lambda x:-x[1])) if s else {"Pesquisa Geral":1}

@st.cache_data(show_spinner=False)
def analyze_doc(fname,fbytes,ftype,area=""):
    r={"file":fname,"type":ftype,"keywords":[],"topics":{},"relevance_score":0,"summary":"","strengths":[],"improvements":[],"writing_quality":0,"reading_time":0,"word_count":0}
    text=""
    if ftype=="PDF" and fbytes: text=extract_pdf(fbytes)
    elif fbytes:
        try: text=fbytes.decode("utf-8",errors="ignore")[:40000]
        except: pass
    if text:
        r["keywords"]=kw_extract(text,25)
        r["topics"]=topic_dist(r["keywords"])
        words=len(text.split()); r["word_count"]=words; r["reading_time"]=max(1,round(words/200))
        r["writing_quality"]=min(100,50+(15 if len(r["keywords"])>15 else 0)+(15 if words>1000 else 0)+(10 if r["reading_time"]>3 else 0))
        if area:
            aw=area.lower().split(); rel=sum(1 for w in aw if any(w in kw for kw in r["keywords"]))
            r["relevance_score"]=min(100,rel*15+45)
        else: r["relevance_score"]=65
        r["strengths"]=[f"Vocabulário rico ({len(r['keywords'])} termos)"] if len(r["keywords"])>15 else []
        r["improvements"]=["Expandir o conteúdo"] if words<500 else []
        r["summary"]=f"{ftype} · {words} palavras · ~{r['reading_time']}min · {', '.join(list(r['topics'].keys())[:2])} · {', '.join(r['keywords'][:4])}"
    else:
        r["summary"]=f"Arquivo {ftype}."; r["relevance_score"]=50
        r["keywords"]=kw_extract(fname.lower(),5); r["topics"]=topic_dist(r["keywords"])
    return r

# ── SEARCH ──────────────────────────────────────
@st.cache_data(show_spinner=False)
def search_ss(q,lim=6):
    try:
        r=requests.get("https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query":q,"limit":lim,"fields":"title,authors,year,abstract,venue,externalIds,openAccessPdf,citationCount"},timeout=8)
        if r.status_code==200:
            out=[]
            for p in r.json().get("data",[]):
                ext=p.get("externalIds",{}) or {}; doi=ext.get("DOI",""); arx=ext.get("ArXiv","")
                pdf=p.get("openAccessPdf") or {}
                link=pdf.get("url","") or(f"https://arxiv.org/abs/{arx}" if arx else(f"https://doi.org/{doi}" if doi else ""))
                al=p.get("authors",[]) or []; au=", ".join(a.get("name","") for a in al[:3])
                if len(al)>3: au+=" et al."
                out.append({"title":p.get("title","Sem título"),"authors":au or "—","year":p.get("year","?"),
                    "source":p.get("venue","") or "Semantic Scholar","doi":doi or arx or "—",
                    "abstract":(p.get("abstract","") or "")[:250],"url":link,
                    "citations":p.get("citationCount",0),"origin":"semantic"})
            return out
    except: pass
    return []

@st.cache_data(show_spinner=False)
def search_cr(q,lim=3):
    try:
        r=requests.get("https://api.crossref.org/works",
            params={"query":q,"rows":lim,"select":"title,author,issued,abstract,DOI,container-title,is-referenced-by-count","mailto":"nebula@example.com"},timeout=8)
        if r.status_code==200:
            out=[]
            for p in r.json().get("message",{}).get("items",[]):
                title=(p.get("title") or ["?"])[0]; ars=p.get("author",[]) or []
                au=", ".join(f'{a.get("given","").split()[0] if a.get("given") else ""} {a.get("family","")}'.strip() for a in ars[:3])
                if len(ars)>3: au+=" et al."
                yr=(p.get("issued",{}).get("date-parts") or [[None]])[0][0]
                doi=p.get("DOI",""); ab=re.sub(r'<[^>]+>','',p.get("abstract","") or "")[:250]
                out.append({"title":title,"authors":au or "—","year":yr or "?",
                    "source":(p.get("container-title") or ["CrossRef"])[0],"doi":doi,
                    "abstract":ab,"url":f"https://doi.org/{doi}" if doi else "","citations":p.get("is-referenced-by-count",0),"origin":"crossref"})
            return out
    except: pass
    return []

def record(tags,w=1.0):
    e=st.session_state.get("current_user")
    if not e or not tags: return
    p=st.session_state.user_prefs.setdefault(e,defaultdict(float))
    for t in tags: p[t.lower()]+=w
    save_db()

def get_recs(email,n=2):
    pr=st.session_state.user_prefs.get(email,{})
    if not pr: return []
    def sc(p): return sum(pr.get(t.lower(),0) for t in p.get("tags",[])+p.get("connections",[]))
    scored=[(sc(p),p) for p in st.session_state.feed_posts if email not in p.get("liked_by",[])]
    return [p for s,p in sorted(scored,key=lambda x:-x[0]) if s>0][:n]

def area_tags(area):
    a=(area or "").lower()
    M={"ia":["machine learning","LLM"],"inteligência artificial":["machine learning","LLM"],
       "neurociência":["sono","memória","cognição"],"biologia":["célula","genômica"],
       "física":["quantum","astrofísica"],"medicina":["diagnóstico","terapia"]}
    for k,v in M.items():
        if k in a: return v
    return [w.strip() for w in a.replace(","," ").split() if len(w)>3][:5]

EMAP={"pdf":"PDF","docx":"Word","xlsx":"Planilha","csv":"Dados","txt":"Texto","py":"Código","md":"Markdown","png":"Imagem","jpg":"Imagem","jpeg":"Imagem"}
def ftype(fname): return EMAP.get(fname.split(".")[-1].lower() if "." in fname else "","Arquivo")

VIB=["#FFD60A","#06D6A0","#FF3B5C","#4CC9F0","#B17DFF","#FF8C42","#FF4E8A","#00C9A7","#FFAB00","#7BD3FF"]

# ═══════════════════════════════════════════════════
#  CSS
# ═══════════════════════════════════════════════════
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800;900&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
  --bg:#07080F; --bg2:#0D0E1A; --bg3:#141528;
  --yel:#FFD60A; --yel2:#FFEC47;
  --grn:#06D6A0; --grn2:#00F5C4;
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
.stApp::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;background:radial-gradient(ellipse 60% 50% at -5% 0%,rgba(255,214,10,.07) 0%,transparent 60%),radial-gradient(ellipse 50% 40% at 105% 0%,rgba(76,201,240,.07) 0%,transparent 55%),radial-gradient(ellipse 40% 50% at 50% 110%,rgba(6,214,160,.06) 0%,transparent 60%);}
.stApp::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;background-image:linear-gradient(rgba(255,255,255,.012) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.012) 1px,transparent 1px);background-size:60px 60px;}
header[data-testid="stHeader"],#MainMenu,footer,.stDeployButton,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
[data-testid="stSidebarCollapseButton"]{display:none!important}
/* Force sidebar always open */
section[data-testid="stSidebar"]{
  display:block!important;
  transform:translateX(0)!important;
  visibility:visible!important;
  background:rgba(8,9,18,.99)!important;
  border-right:1px solid rgba(255,255,255,.1)!important;
  width:210px!important;min-width:210px!important;max-width:210px!important;
  padding:1.2rem .8rem 1rem!important;
}
section[data-testid="stSidebar"]>div{width:210px!important;padding:0!important;}
[data-testid="collapsedControl"]{display:none!important}
.block-container{padding-top:.3rem!important;padding-bottom:4rem!important;max-width:1380px!important;position:relative;z-index:1;padding-left:.8rem!important;padding-right:.8rem!important;}
/* ALL buttons - visible, simple */
.stButton>button{
  background:rgba(255,255,255,.09)!important;
  border:1px solid rgba(255,255,255,.14)!important;
  border-radius:10px!important;
  color:#D0D2E0!important;
  -webkit-text-fill-color:#D0D2E0!important;
  font-family:'DM Sans',sans-serif!important;
  font-weight:500!important;font-size:.83rem!important;
  padding:.46rem .8rem!important;
  transition:background .1s!important;
  box-shadow:none!important;
  line-height:1.4!important;
}
.stButton>button:hover{
  background:rgba(255,255,255,.16)!important;
  color:#FFFFFF!important;-webkit-text-fill-color:#FFFFFF!important;
}
.stButton>button:active{transform:scale(.97)!important;}
.stButton>button p,.stButton>button span{color:inherit!important;-webkit-text-fill-color:inherit!important;}
/* Sidebar buttons: left-aligned, full-width */
section[data-testid="stSidebar"] .stButton>button{
  text-align:left!important;
  justify-content:flex-start!important;
  width:100%!important;
  margin-bottom:.15rem!important;
  padding:.5rem .85rem!important;
  font-size:.85rem!important;
}
/* sb-logo and labels */
.sb-logo{display:flex;align-items:center;gap:9px;margin-bottom:1.5rem;padding:.2rem .3rem;}
.sb-logo-icon{width:34px;height:34px;border-radius:10px;background:linear-gradient(135deg,#FFD60A,#FF8C42);display:flex;align-items:center;justify-content:center;font-size:.9rem;flex-shrink:0;}
.sb-logo-txt{font-family:'Syne',sans-serif;font-weight:900;font-size:1.2rem;letter-spacing:-.04em;background:linear-gradient(135deg,#FFD60A,#06D6A0);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.sb-lbl{font-size:.54rem;font-weight:700;color:#404460;letter-spacing:.14em;text-transform:uppercase;padding:0 .2rem;margin-bottom:.35rem;margin-top:.8rem;}
.stTextInput input,.stTextArea textarea{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;color:var(--t1)!important;font-family:'DM Sans',sans-serif!important;font-size:.84rem!important;}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:rgba(255,214,10,.4)!important;box-shadow:0 0 0 3px rgba(255,214,10,.08)!important;}
.stTextInput label,.stTextArea label,.stSelectbox label,.stFileUploader label,.stNumberInput label{color:var(--t3)!important;font-size:.60rem!important;letter-spacing:.10em!important;text-transform:uppercase!important;font-weight:600!important;}
.glass{background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.10);border-radius:var(--r20);box-shadow:0 0 0 1px rgba(255,255,255,.04) inset,0 4px 32px rgba(0,0,0,.3);position:relative;overflow:hidden;}
.glass::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.08),transparent);pointer-events:none;}
.post-card{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.09);border-radius:var(--r20);margin-bottom:.65rem;overflow:hidden;box-shadow:0 2px 20px rgba(0,0,0,.25);transition:border-color .14s,transform .14s;}
.post-card:hover{border-color:rgba(255,255,255,.15);transform:translateY(-1px);}
.sc{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.09);border-radius:var(--r20);padding:.9rem 1rem;margin-bottom:.6rem;}
.scard{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:var(--r16);padding:.8rem 1rem;margin-bottom:.42rem;transition:border-color .13s,transform .13s;}
.scard:hover{border-color:rgba(255,255,255,.14);transform:translateY(-1px);}
.mbox{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.09);border-radius:var(--r16);padding:.9rem;text-align:center;}
.abox{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.10);border-radius:var(--r16);padding:1rem;margin-bottom:.6rem;}
.pbox-grn{background:rgba(6,214,160,.07);border:1px solid rgba(6,214,160,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.55rem;}
.pbox-yel{background:rgba(255,214,10,.07);border:1px solid rgba(255,214,10,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.55rem;}
.pbox-blu{background:rgba(76,201,240,.07);border:1px solid rgba(76,201,240,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.55rem;}
.pbox-pur{background:rgba(177,125,255,.07);border:1px solid rgba(177,125,255,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.55rem;}
.chart-wrap{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);border-radius:var(--r12);padding:.65rem;margin-bottom:.6rem;}
.compose-box{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.11);border-radius:var(--r20);padding:1.1rem 1.3rem;margin-bottom:.8rem;}
.mval-yel{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;background:linear-gradient(135deg,var(--yel),var(--orn));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-grn{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;background:linear-gradient(135deg,var(--grn),var(--blu));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-blu{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;background:linear-gradient(135deg,var(--blu),var(--pur));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-red{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;background:linear-gradient(135deg,var(--red),var(--orn));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mlbl{font-size:.58rem;color:var(--t3);margin-top:4px;letter-spacing:.1em;text-transform:uppercase;font-weight:700;}
.tag{display:inline-block;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.09);border-radius:50px;padding:2px 9px;font-size:.63rem;color:var(--t2);margin:2px;font-weight:500;}
.badge-yel{display:inline-block;background:rgba(255,214,10,.12);border:1px solid rgba(255,214,10,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--yel);}
.badge-grn{display:inline-block;background:rgba(6,214,160,.12);border:1px solid rgba(6,214,160,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--grn);}
.badge-red{display:inline-block;background:rgba(255,59,92,.12);border:1px solid rgba(255,59,92,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--red);}
.badge-blu{display:inline-block;background:rgba(76,201,240,.12);border:1px solid rgba(76,201,240,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--blu);}
.badge-pur{display:inline-block;background:rgba(177,125,255,.12);border:1px solid rgba(177,125,255,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--pur);}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.45;transform:scale(.7)}}
.dot-on{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--grn);animation:pulse 2.5s infinite;margin-right:4px;vertical-align:middle;}
.dot-off{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--t4);margin-right:4px;vertical-align:middle;}
@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.pw{animation:fadeUp .18s ease both;}
.bme{background:linear-gradient(135deg,rgba(255,214,10,.15),rgba(255,140,66,.1));border:1px solid rgba(255,214,10,.2);border-radius:18px 18px 4px 18px;padding:.55rem .88rem;max-width:70%;margin-left:auto;margin-bottom:5px;font-size:.82rem;line-height:1.6;}
.bthem{background:var(--g2);border:1px solid var(--gb1);border-radius:18px 18px 18px 4px;padding:.55rem .88rem;max-width:70%;margin-bottom:5px;font-size:.82rem;line-height:1.6;}
.cmt{background:rgba(255,255,255,.03);border:1px solid var(--gb1);border-radius:var(--r12);padding:.5rem .85rem;margin-bottom:.25rem;}
.stTabs [data-baseweb="tab-list"]{background:rgba(255,255,255,.03)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;padding:3px!important;gap:2px!important;}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--t3)!important;border-radius:9px!important;font-size:.75rem!important;font-family:'DM Sans',sans-serif!important;font-weight:500!important;}
.stTabs [aria-selected="true"]{background:var(--g3)!important;color:var(--yel)!important;border:1px solid rgba(255,214,10,.2)!important;font-weight:700!important;}
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
/* colored accent buttons */
input[type="number"]{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;color:var(--t1)!important;}
/* AI Result card */
.ai-card{background:linear-gradient(135deg,rgba(255,214,10,.06),rgba(6,21

