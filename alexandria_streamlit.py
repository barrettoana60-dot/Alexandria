import subprocess, sys, os, json, hashlib, random, string, re, io, base64, time, math
from datetime import datetime, timedelta
from collections import defaultdict, Counter

def _pip(*pkgs):
    for p in pkgs:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", p, "-q"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass

try: import plotly.graph_objects as go
except: _pip("plotly"); import plotly.graph_objects as go

try: import plotly.express as px
except: pass

try:
    import numpy as np
    from PIL import Image as PILImage
except: _pip("pillow","numpy"); import numpy as np; from PIL import Image as PILImage

try: import requests
except: _pip("requests"); import requests

try: import PyPDF2
except: PyPDF2 = None

try: import openpyxl
except: openpyxl = None

try: import pandas as pd
except: pd = None

SKIMAGE_OK = False
SKLEARN_OK = False
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
    except: SKIMAGE_OK = False

try: from sklearn.cluster import KMeans; SKLEARN_OK = True
except:
    try: _pip("scikit-learn"); from sklearn.cluster import KMeans; SKLEARN_OK = True
    except: SKLEARN_OK = False

import streamlit as st

st.set_page_config(page_title="Nebula Repository", page_icon=" ", layout="wide", initial_sidebar_state="expanded") # Removed emoji

DB_FILE = "nebula_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def hp(pw): return hashlib.sha256(pw.encode()).hexdigest()
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
    try:
        n=int(n); return f"{n/1000:.1f}k" if n>=1000 else str(n)
    except: return str(n)
def guser():
    if not isinstance(st.session_state.get("users"),dict): return {}
    return st.session_state.users.get(st.session_state.current_user,{})
def is_online(e): return (hash(e+"on")%3)!=0

# Removed animated gradients, using a fixed dark blue for avatars
AVATAR_BG_COLOR = "#0A1929" 
def ugrad(e): return AVATAR_BG_COLOR

STOPWORDS={"de","a","o","que","e","do","da","em","um","para","é","com","uma","os","no","se","na","por",
           "mais","as","dos","como","mas","foi","ao","ele","das","tem","à","seu","sua","ou","ser",
           "the","of","and","to","in","is","it","that","was","he","for","on","are","as","with","they",
           "at","be","this","from","or","one","had","by","but","not","what","all","were","we","when",
           "your","can","said","there","use","an","each","which","she","do","how","their","if","will",
           "up","other","about","out","many","then","them","these","so","also","into","its","than"}

SEED_POSTS=[
    {"id":1,"author":"Carlos Mendez","author_email":"carlos@nebula.ai","avatar":"CM","area":"Neurociência",
     "title":"Efeitos da Privação de Sono na Plasticidade Sináptica",
     "abstract":"Investigamos como 24h de privação de sono afetam espinhas dendríticas em ratos Wistar, com redução de 34% na plasticidade hipocampal. Utilizamos microscopia confocal e Western Blot para quantificação proteica.",
     "tags":["neurociência","sono","memória","hipocampo","plasticidade"],"likes":47,
     "comments":[{"user":"Maria Silva","text":"Excelente metodologia! Já viu relação com BDNF?"}],
     "status":"Em andamento","date":"2026-02-10","liked_by":[],"saved_by":[],"connections":["sono","memória"],"views":312,
     "methodology":"experimental","citations":8,"keywords_extracted":["privação","sono","plasticidade","sináptica","hipocampal"]},
    {"id":2,"author":"Luana Freitas","author_email":"luana@nebula.ai","avatar":"LF","area":"Biomedicina",
     "title":"CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras",
     "abstract":"Vetor AAV9 modificado para entrega de CRISPR no gene DMD com eficiência de 78% em modelos mdx. Resultados promissores para futuros trials clínicos com análise de off-targets sistemática.",
     "tags":["CRISPR","gene terapia","músculo","AAV9","DMD"],"likes":93,
     "comments":[{"user":"Ana","text":"Quando iniciam os trials?"}],"status":"Publicado",
     "date":"2026-01-28","liked_by":[],"saved_by":[],"connections":["genômica","distrofia"],"views":891,
     "methodology":"experimental","citations":24,"keywords_extracted":["CRISPR","AAV9","distrofia","muscular","gene"]},
    {"id":3,"author":"Rafael Souza","author_email":"rafael@nebula.ai","avatar":"RS","area":"Computação",
     "title":"Redes Neurais Quântico-Clássicas para Otimização Combinatória",
     "abstract":"Arquitetura híbrida variacional combinando qubits supercondutores com camadas densas clássicas. TSP resolvido com 40% menos iterações que algoritmos clássicos em grafos de 100+ nós.",
     "tags":["quantum ML","otimização","TSP","computação quântica","híbrido"],"likes":201,"comments":[],"status":"Em andamento",
     "date":"2026-02-15","liked_by":[],"saved_by":[],"connections":["computação quântica"],"views":1240,
     "methodology":"computacional","citations":31,"keywords_extracted":["quântico","clássico","otimização","combinatória","variacional"]},
    {"id":4,"author":"Priya Nair","author_email":"priya@nebula.ai","avatar":"PN","area":"Astrofísica",
     "title":"Detecção de Matéria Escura via Lentes Gravitacionais Fracas",
     "abstract":"Mapeamento com 100M de galáxias do DES Y3. Tensão de 2.8σ com ΛCDM em escalas < 1 Mpc. Análise de shear cósmico com pipeline bayesiano robusto a efeitos sistemáticos.",
     "tags":["astrofísica","matéria escura","cosmologia","DES","lensing"],"likes":312,"comments":[],
     "status":"Publicado","date":"2026-02-01","liked_by":[],"saved_by":[],"connections":["cosmologia"],"views":2180,
     "methodology":"observacional","citations":67,"keywords_extracted":["matéria","escura","gravitacional","lensing","cosmológico"]},
    {"id":5,"author":"João Lima","author_email":"joao@nebula.ai","avatar":"JL","area":"Psicologia",
     "title":"Viés de Confirmação em Decisões Médicas Assistidas por IA",
     "abstract":"Estudo duplo-cego com 240 médicos revelou que sistemas de IA mal calibrados amplificam vieses cognitivos em 22% dos casos. Proposta de framework de auditoria contínua.",
     "tags":["psicologia","IA","cognição","medicina","viés"],"likes":78,
     "comments":[{"user":"Carlos M.","text":"Muito relevante para o campo clínico!"}],"status":"Publicado",
     "date":"2026-02-08","liked_by":[],"saved_by":[],"connections":["cognição","IA"],"views":456,
     "methodology":"estudo clínico","citations":15,"keywords_extracted":["viés","confirmação","decisão","médica","cognitivo"]},
    {"id":6,"author":"Ana Pesquisadora","author_email":"demo@nebula.ai","avatar":"AP","area":"Inteligência Artificial",
     "title":"LLMs como Motores de Raciocínio Científico: Benchmarks e Limitações",
     "abstract":"Avaliação sistemática de 12 LLMs em tarefas de raciocínio científico cross-domain. Identificamos falhas críticas em inferência causal e propusemos novo benchmark SciReason-2026.",
     "tags":["LLM","raciocínio","benchmark","IA","ciência"],"likes":134,"comments":[],"status":"Em andamento",
     "date":"2026-02-20","liked_by":[],"saved_by":[],"connections":["LLM","benchmarks"],"views":890,
     "methodology":"computacional","citations":22,"keywords_extracted":["LLM","raciocínio","benchmark","científico","inferência"]},
]

SEED_USERS={
    "demo@nebula.ai":{"name":"Ana Pesquisadora","password":hp("demo123"),"bio":"Pesquisadora em IA e Ciências Cognitivas | UFMG","area":"Inteligência Artificial","followers":128,"following":47,"verified":True,"2fa_enabled":False,"scholarship":"UFMG","orcid":"0000-0001-2345-6789","h_index":7,"publications":12},
    "carlos@nebula.ai":{"name":"Carlos Mendez","password":hp("nebula123"),"bio":"Neurocientista | UFMG | Plasticidade sináptica e sono","area":"Neurociência","followers":210,"following":45,"verified":True,"2fa_enabled":False,"scholarship":"UFMG","h_index":9,"publications":18},
    "luana@nebula.ai":{"name":"Luana Freitas","password":hp("nebula123"),"bio":"Biomédica | FIOCRUZ | CRISPR e terapia gênica","area":"Biomedicina","followers":178,"following":62,"verified":True,"2fa_enabled":False,"scholarship":"FIOCRUZ","h_index":11,"publications":24},
    "rafael@nebula.ai":{"name":"Rafael Souza","password":hp("nebula123"),"bio":"Computação Quântica | USP | Algoritmos híbridos","area":"Computação","followers":340,"following":88,"verified":True,"2fa_enabled":False,"scholarship":"USP","h_index":14,"publications":31},
    "priya@nebula.ai":{"name":"Priya Nair","password":hp("nebula123"),"bio":"Astrofísica | MIT | Dark matter & gravitational lensing","area":"Astrofísica","followers":520,"following":31,"verified":True,"2fa_enabled":False,"scholarship":"MIT","h_index":22,"publications":47},
    "joao@nebula.ai":{"name":"João Lima","password":hp("nebula123"),"bio":"Psicólogo Cognitivo | UNICAMP | IA e vieses clínicos","area":"Psicologia","followers":95,"following":120,"verified":True,"2fa_enabled":False,"scholarship":"UNICAMP","h_index":6,"publications":14},
}

CHAT_INIT={
    "carlos@nebula.ai":[{"from":"carlos@nebula.ai","text":"Oi! Vi seu comentário na pesquisa sobre LLMs.","time":"09:14"},{"from":"me","text":"Achei muito interessante o paralelo com neurociência!","time":"09:16"}],
    "luana@nebula.ai":[{"from":"luana@nebula.ai","text":"Podemos colaborar no próximo projeto de bioinformática?","time":"ontem"}],
}

def save_db():
    try:
        with open(DB_FILE,"w",encoding="utf-8") as f:
            json.dump({
                "users":st.session_state.users,"feed_posts":st.session_state.feed_posts,
                "folders":st.session_state.folders,
                "user_prefs":{k:dict(v) for k,v in st.session_state.user_prefs.items()},
                "saved_articles":st.session_state.saved_articles,
                "followed":st.session_state.followed,
                "repo_metadata":st.session_state.get("repo_metadata",{}),
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
    st.session_state.setdefault("page","login") # Default to login
    st.session_state.setdefault("profile_view",None)
    dp=disk.get("user_prefs",{})
    st.session_state.setdefault("user_prefs",{k:defaultdict(float,v) for k,v in dp.items()})
    st.session_state.setdefault("pending_verify",None)
    rp=disk.get("feed_posts",[dict(p) for p in SEED_POSTS])
    for p in rp:
        p.setdefault("liked_by",[])
        p.setdefault("saved_by",[])
        p.setdefault("comments",[])
        p.setdefault("views",200)
        p.setdefault("methodology","")
        p.setdefault("citations",random.randint(0,30))
        p.setdefault("keywords_extracted",[])
    st.session_state.setdefault("feed_posts",rp)
    st.session_state.setdefault("folders",disk.get("folders",{}))
    st.session_state.setdefault("folder_files_bytes",{})
    st.session_state.setdefault("chat_contacts",list(SEED_USERS.keys()))
    st.session_state.setdefault("chat_messages",{k:list(v) for k,v in CHAT_INIT.items()})
    st.session_state.setdefault("active_chat",None)
    st.session_state.setdefault("followed",disk.get("followed",["carlos@nebula.ai","luana@nebula.ai"]))
    st.session_state.setdefault("notifications",["Carlos curtiu sua pesquisa","Nova conexão detectada","Rafael comentou","2 novos artigos relacionados"])
    st.session_state.setdefault("scholar_cache",{})
    st.session_state.setdefault("saved_articles",disk.get("saved_articles",[]))
    st.session_state.setdefault("img_result",None)
    st.session_state.setdefault("search_results",None)
    st.session_state.setdefault("last_sq","")
    st.session_state.setdefault("stats_data",{"h_index":7,"fator_impacto":4.2,"notes":""})
    st.session_state.setdefault("compose_open",False)
    st.session_state.setdefault("anthropic_key","")
    st.session_state.setdefault("ai_conn_cache",{})
    st.session_state.setdefault("ml_cache",{})
    st.session_state.setdefault("repo_metadata",disk.get("repo_metadata",{}))
    st.session_state.setdefault("deep_analysis_cache",{})
    st.session_state.setdefault("conn_analysis_cache",{})
    st.session_state.setdefault("image_analysis_cache",{}) # Cache for Claude Vision analysis

init()

# ================================================
#  API CALLS
# ================================================
def call_claude_vision(img_bytes, prompt, api_key):
    if not api_key or not api_key.startswith("sk-"): return None,"Chave API inválida."
    try:
        img=PILImage.open(io.BytesIO(img_bytes))
        buf=io.BytesIO()
        img.convert("RGB").save(buf,format="JPEG",quality=85)
        b64=base64.b64encode(buf.getvalue()).decode()
        resp=requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key":api_key,"anthropic-version":"2023-06-01","content-type":"application/json"},
            json={"model":"claude-opus-4-20250514","max_tokens":1500,
                  "messages":[{"role":"user","content":[
                      {"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":b64}},
                      {"type":"text","text":prompt}]}]},timeout=30)
        if resp.status_code==200:
            return resp.json()["content"][0]["text"],None
        return None,resp.json().get("error",{}).get("message",f"HTTP {resp.status_code}")
    except Exception as e: return None,str(e)

def call_claude_analysis(content, api_key, prompt_type="research"):
    if not api_key or not api_key.startswith("sk-"): return None,"API key ausente."
    prompts={
        "research":f"""Você é um especialista em análise de pesquisas científicas. Analise esta pesquisa e responda APENAS em JSON puro:
{{
  "resumo_executivo": "<resumo em 2-3 frases>",
  "pontos_fortes": ["<ponto 1>","<ponto 2>","<ponto 3>"],
  "pontos_melhoria": ["<melhoria 1>","<melhoria 2>","<melhoria 3>"],
  "lacunas_identificadas": ["<lacuna 1>","<lacuna 2>"],
  "metodologia_score": <0-100>,
  "inovacao_score": <0-100>,
  "impacto_potencial": "<Alto/Médio/Baixo>",
  "areas_conexas": ["<area 1>","<area 2>","<area 3>"],
  "proximos_passos": ["<passo 1>","<passo 2>"],
  "tendencia_temporal": "<crescente/estável/decrescente>",
  "keywords_emergentes": ["<kw1>","<kw2>","<kw3>"]
}}
Pesquisa: {content}""",
        "connections":content,
        "image_detail":f"""Você é um especialista em análise de imagens científicas. Analise a imagem fornecida em detalhes e responda APENAS em JSON puro, com foco em informações científicas e representação:
{{
  "tipo_imagem": "<tipo da imagem, ex: Microscopia Eletrônica, Gráfico de Barras, Imagem Astronômica>",
  "area_cientifica": "<área científica principal, ex: Biologia Celular, Física de Partículas, Ciência de Dados>",
  "descricao_detalhada": "<descrição completa e objetiva do que é visível na imagem, incluindo cores, formas, texturas, e elementos chave>",
  "elementos_identificados": ["<elemento 1>", "<elemento 2>", "<elemento 3>", "<estrutura ou objeto chave>"],
  "representacao_cientifica": "<o que a imagem representa ou ilustra cientificamente, ex: 'Esta imagem representa a estrutura de um vírus HIV em processo de brotamento...', 'Ilustra a distribuição de galáxias em um aglomerado...', 'Demonstra a correlação entre duas variáveis em um experimento...'>",
  "tecnica_experimental_ou_metodo": "<técnica usada para gerar a imagem, ex: Microscopia de Fluorescência, Simulação Computacional, Observação Telescópica, Eletroforese em Gel>",
  "qualidade_visual": "<Alta/Média/Baixa>",
  "confianca_analise_ia": <0-100>,
  "termos_busca_sugeridos": ["<termo 1>", "<termo 2>", "<termo 3>", "<termos relevantes para busca acadêmica>"],
  "observacoes_adicionais": "<observações científicas relevantes, implicações, ou perguntas que a imagem levanta>",
  "metodologia_sugerida_aprofundamento": "<sugestão de como a imagem poderia ser analisada mais a fundo ou em qual contexto seria útil>",
  "referencias_relacionadas_topicos": ["<tópico de referência 1>", "<tópico de referência 2>"]
}}
""",
    }
    try:
        resp=requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key":api_key,"anthropic-version":"2023-06-01","content-type":"application/json"},
            json={"model":"claude-opus-4-20250514","max_tokens":1000,
                  "messages":[{"role":"user","content":prompts.get(prompt_type,content)}]},timeout=25)
        if resp.status_code==200:
            text=resp.json()["content"][0]["text"].strip()
            text=re.sub(r'^```json\s*','',text); text=re.sub(r'\s*```$','',text)
            return json.loads(text),None
        return None,f"HTTP {resp.status_code}"
    except Exception as e: return None,str(e)

VISION_PROMPT="""Analise esta imagem científica em detalhes e responda APENAS em JSON puro:
{
  "tipo": "<tipo da imagem>",
  "origem": "<área científica>",
  "descricao": "<descrição detalhada>",
  "estruturas": ["<estrutura 1>","<estrutura 2>","<estrutura 3>"],
  "tecnica": "<técnica experimental>",
  "qualidade": "<Alta/Média/Baixa>",
  "confianca": <0-100>,
  "termos_busca": "<3-5 termos para busca>",
  "observacoes": "<observações científicas relevantes>",
  "metodologia_sugerida": "<metodologia para análise aprofundada>",
  "referencias_relacionadas": ["<ref 1>","<ref 2>"]
}"""

# ================================================
#  ML PIPELINE
# ================================================
def sobel_analysis(gray_arr):
    try:
        if SKIMAGE_OK:
            sx=sk_filters.sobel_h(gray_arr); sy=sk_filters.sobel_v(gray_arr)
        else:
            kx=np.array([[-1,0,1],[-2,0,2],[-1,0,1]],dtype=np.float32)/8.0
            def conv2d(img,k):
                ph,pw=k.shape[0]//2,k.shape[1]//2
                padded=np.pad(img,((ph,ph),(pw,pw)),mode='edge')
                out=np.zeros_like(img)
                for i in range(k.shape[0]):
                    for j in range(k.shape[1]): out+=k[i,j]*padded[i:i+img.shape[0],j:j+img.shape[1]]
                return out
            sx=conv2d(gray_arr.astype(np.float32),kx); sy=conv2d(gray_arr.astype(np.float32),kx.T)
        magnitude=np.sqrt(sx**2+sy**2)
        direction=np.arctan2(sy,sx)*180/np.pi
        return {"magnitude":magnitude,"horizontal":sx,"vertical":sy,
                "mean_edge":float(magnitude.mean()),"max_edge":float(magnitude.max()),
                "edge_density":float((magnitude>magnitude.mean()*1.5).mean()),
                "dominant_direction":float(direction.mean()),
                "edge_hist":np.histogram(magnitude,bins=16,range=(0,magnitude.max()+1e-5))[0].tolist()}
    except Exception:
        gx=np.gradient(gray_arr.astype(np.float32),axis=1); gy=np.gradient(gray_arr.astype(np.float32),axis=0)
        mag=np.sqrt(gx**2+gy**2)
        return {"magnitude":mag,"horizontal":gx,"vertical":gy,"mean_edge":float(mag.mean()),
                "max_edge":float(mag.max()),"edge_density":float((mag>mag.mean()*1.5).mean()),
                "dominant_direction":0.0,"edge_hist":np.histogram(mag,bins=16)[0].tolist()}

def canny_analysis(gray_uint8):
    try:
        if SKIMAGE_OK:
            edges_fine=sk_feature.canny(gray_uint8/255.0,sigma=1.0)
            edges_med=sk_feature.canny(gray_uint8/255.0,sigma=2.0)
            edges_coarse=sk_feature.canny(gray_uint8/255.0,sigma=3.5)
        else:
            g=gray_uint8.astype(np.float32)/255.0
            mag=np.sqrt(np.gradient(g,axis=1)**2+np.gradient(g,axis=0)**2)
            edges_fine=mag>np.percentile(mag,85)
            edges_med=mag>np.percentile(mag,75)
            edges_coarse=mag>np.percentile(mag,65)
        return {"fine":edges_fine,"medium":edges_med,"coarse":edges_coarse,
                "fine_density":float(edges_fine.mean()),"medium_density":float(edges_med.mean()),
                "coarse_density":float(edges_coarse.mean()),"total_edges":int(edges_fine.sum()),
                "structure_level":"micro" if edges_fine.mean()>0.1 else ("meso" if edges_med.mean()>0.05 else "macro")}
    except Exception:
        e=np.zeros_like(gray_uint8,dtype=bool)
        return {"fine":e,"medium":e,"coarse":e,"fine_density":0.0,"medium_density":0.0,
                "coarse_density":0.0,"total_edges":0,"structure_level":"macro"}

def orb_keypoints(gray_uint8):
    try:
        if SKIMAGE_OK:
            try:
                from skimage.feature import ORB
                det=ORB(n_keypoints=200,fast_threshold=0.05)
                det.detect_and_extract(gray_uint8/255.0)
                kp=det.keypoints
            except:
                from skimage.feature import corner_harris,corner_peaks
                harris=corner_harris(gray_uint8/255.0)
                kp=corner_peaks(harris,min_distance=8,threshold_rel=0.02)
        else:
            g=gray_uint8.astype(np.float32)
            mag=np.sqrt(np.gradient(g,axis=1)**2+np.gradient(g,axis=0)**2)
            step=8; pts=[]
            for i in range(0,mag.shape[0]-step,step):
                for j in range(0,mag.shape[1]-step,step):
                    block=mag[i:i+step,j:j+step]
                    if block.max()>mag.mean()*1.8:
                        yi,xj=np.unravel_index(block.argmax(),block.shape)
                        pts.append([i+yi,j+xj])
            kp=np.array(pts) if pts else np.zeros((0,2))
        centers=np.array(kp)[:5].tolist() if len(kp)>0 else []
        if len(kp)>0 and SKLEARN_OK:
            try:
                n_cl=min(5,len(kp))
                kmk=KMeans(n_clusters=n_cl,random_state=42,n_init=5).fit(np.array(kp))
                centers=kmk.cluster_centers_.tolist()
            except: pass
        return {"keypoints":kp,"n_keypoints":len(kp),"cluster_centers":centers,
                "mean_scale":1.0,"distribution":"uniforme" if len(kp)>5 else "concentrado"}
    except Exception:
        return {"keypoints":np.zeros((0,2)),"n_keypoints":0,"cluster_centers":[],"mean_scale":1.0,"distribution":"n/a"}

def glcm_texture(gray_uint8):
    try:
        if SKIMAGE_OK:
            g64=(gray_uint8//4).astype(np.uint8)
            glcm=graycomatrix(g64,distances=[1,3,5],angles=[0,np.pi/4,np.pi/2,3*np.pi/4],levels=64,symmetric=True,normed=True)
            features={}
            for prop in ['contrast','dissimilarity','homogeneity','energy','correlation','ASM']:
                features[prop]=float(graycoprops(glcm,prop).mean())
            features['entropy']=float(-np.sum(glcm[glcm>0]*np.log2(glcm[glcm>0]+1e-12)))
        else:
            g=gray_uint8.astype(np.float32)/255.0
            gx=np.gradient(g,axis=1); gy=np.gradient(g,axis=0)
            contrast=float(np.sqrt(gx**2+gy**2).mean()*100)
            features={"contrast":round(contrast,4),"dissimilarity":round(contrast*0.5,4),
                      "homogeneity":round(1.0/(1.0+contrast/50.0),4),"energy":round(np.var(g),4),
                      "correlation":0.7,"ASM":round(np.var(g)**2,4),"entropy":4.5}
        features['texture_type']="homogênea" if features.get('homogeneity',0)>0.7 else ("texturizada" if features.get('contrast',0)>50 else "estruturada")
        return features
    except Exception as e:
        return {"homogeneity":0.5,"contrast":20.0,"energy":0.1,"correlation":0.7,"ASM":0.01,
                "dissimilarity":10.0,"entropy":4.0,"texture_type":"desconhecido","error":str(e)}

def kmeans_colors(img_arr,k=7):
    if not SKLEARN_OK: return [],[]
    try:
        h,w=img_arr.shape[:2]; step=max(1,(h*w)//4000)
        flat=img_arr.reshape(-1,3)[::step].astype(np.float32)
        km=KMeans(n_clusters=k,random_state=42,n_init=5,max_iter=100).fit(flat)
        centers=km.cluster_centers_.astype(int); counts=Counter(km.labels_); total=sum(counts.values())
        palette=[]
        for i in np.argsort([-counts[j] for j in range(k)]):
            r2,g2,b2=centers[i]; pct=counts[i]/total*100
            palette.append({"rgb":(int(r2),int(g2),int(b2)),"hex":"#{:02x}{:02x}{:02x}".format(int(r2),int(g2),int(b2)),"pct":round(pct,1)})
        return palette,[]
    except: return [],[]

def fft_analysis(gray_arr):
    fft=np.fft.fft2(gray_arr); fft_shift=np.fft.fftshift(fft); magnitude=np.abs(fft_shift)
    h,w=magnitude.shape; total=magnitude.sum()+1e-5; r=min(h,w)//2
    Y,X=np.ogrid[:h,:w]; dist=np.sqrt((X-w//2)**2+(Y-h//2)**2)
    lf=float(magnitude[dist<r*0.1].sum()/total)
    mf=float(magnitude[(dist>=r*0.1)&(dist<r*0.4)].sum()/total)
    hf=float(magnitude[dist>=r*0.4].sum()/total)
    outer=np.concatenate([magnitude[:h//4,:].ravel(),magnitude[3*h//4:,:].ravel()])
    periodic_score=float(np.percentile(outer,99))/(float(np.mean(outer))+1e-5)
    return {"periodic_score":round(periodic_score,2),"is_periodic":periodic_score>12,
            "low_freq":round(lf,3),"mid_freq":round(mf,3),"high_freq":round(hf,3),
            "dominant_scale":"fina" if hf>0.5 else ("média" if mf>0.3 else "grossa")}

def classify_scientific_image(sobel_r,canny_r,glcm_r,orb_r,fft_r,color_info,kmeans_palette):
    ei=sobel_r["mean_edge"]; ed=sobel_r["edge_density"]; sym=color_info["symmetry"]
    entropy=color_info["entropy"]; n_kp=orb_r["n_keypoints"]; periodic=fft_r["is_periodic"]
    hom=glcm_r.get("homogeneity",0.5); contrast=glcm_r.get("contrast",20); corr=glcm_r.get("correlation",0.5)
    mr,mg,mb=color_info["r"],color_info["g"],color_info["b"]; scores={}
    scores["Histopatologia H&E"]=30*(mr>140 and mb>100)+20*(n_kp>80)+20*(contrast>30)+15*(ed>0.12)
    scores["Fluorescência DAPI"]=45*(mb>150 and mb>mr+30)+20*(entropy>5.0)+20*(ed>0.1)+15*(n_kp>30)
    scores["Fluorescência GFP"]=45*(mg>150 and mg>mr+30)+20*(entropy>4.5)+20*(ed>0.08)
    scores["Cristalografia/Difração"]=40*periodic+25*(sym>0.75)+15*(hom>0.7)+20*(fft_r["periodic_score"]>15)
    scores["Gel/Western Blot"]=30*(contrast<15 and hom>0.8)+25*(abs(mr-mg)<20 and abs(mg-mb)<20)+25*(canny_r["coarse_density"]>canny_r["fine_density"])
    scores["Gráfico/Diagrama"]=30*(glcm_r.get("energy",0)>0.15)+25*(hom>0.85)+20*(n_kp<30)+25*(entropy<4.0)
    scores["Microscopia Confocal"]=20*(len(kmeans_palette)>4)+25*(entropy>5.5)+20*(n_kp>50)+20*(ed>0.10)
    scores["Imagem Astronômica"]=35*(color_info.get("brightness",128)<60)+25*(n_kp>40 and hom>0.7)+20*(entropy>5.0)
    best=max(scores,key=scores.get); conf=min(96,40+scores[best]*0.55)
    origin_map={"Histopatologia H&E":"Medicina/Patologia","Fluorescência DAPI":"Biologia Celular",
                "Fluorescência GFP":"Biologia Molecular","Cristalografia/Difração":"Física/Química",
                "Gel/Western Blot":"Bioquímica/Genômica","Gráfico/Diagrama":"Ciência Geral",
                "Microscopia Confocal":"Biologia Celular","Imagem Astronômica":"Astrofísica"}
    search_map={"Histopatologia H&E":"hematoxylin eosin staining histopathology",
                "Fluorescência DAPI":"DAPI nuclear staining fluorescence microscopy",
                "Fluorescência GFP":"GFP green fluorescent protein confocal",
                "Cristalografia/Difração":"X-ray diffraction crystallography structure",
                "Gel/Western Blot":"western blot gel electrophoresis protein",
                "Gráfico/Diagrama":"scientific data visualization chart",
                "Microscopia Confocal":"confocal microscopy fluorescence multichannel",
                "Imagem Astronômica":"astronomy telescope deep field observation"}
    return {"category":best,"confidence":round(conf,1),"origin":origin_map.get(best,"Ciência Geral"),
            "search_kw":search_map.get(best,best),"all_scores":dict(sorted(scores.items(),key=lambda x:-x[1])[:5])}

@st.cache_data(show_spinner=False,ttl=3600)
def run_full_ml_pipeline_cached(img_bytes):
    return _run_pipeline(img_bytes)

def _run_pipeline(img_bytes):
    result={}
    try:
        img=PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
        orig_size=img.size; w,h=img.size; scale=min(384/w,384/h)
        new_w,new_h=int(w*scale),int(h*scale)
        img_r=img.resize((new_w,new_h),PILImage.LANCZOS)
        arr=np.array(img_r,dtype=np.float32)
        r_ch,g_ch,b_ch=arr[:,:,0],arr[:,:,1],arr[:,:,2]
        gray=0.2989*r_ch+0.5870*g_ch+0.1140*b_ch; gray_u8=gray.astype(np.uint8)
        mr,mg,mb=float(r_ch.mean()),float(g_ch.mean()),float(b_ch.mean())
        hy,hx=gray.shape[0]//2,gray.shape[1]//2
        q=[gray[:hy,:hx].var(),gray[:hy,hx:].var(),gray[hy:,:hx].var(),gray[hy:,hx:].var()]
        sym=1.0-(max(q)-min(q))/(max(q)+1e-5)
        hst=np.histogram(gray,bins=64,range=(0,255))[0]; hn=hst/hst.sum(); hn=hn[hn>0]
        entropy=float(-np.sum(hn*np.log2(hn)))
        color_info={"r":round(mr,1),"g":round(mg,1),"b":round(mb,1),"symmetry":round(sym,3),
                    "entropy":round(entropy,3),"brightness":round(float(gray.mean()),1),
                    "std":round(float(gray.std()),1),"warm":mr>mb+15,"cool":mb>mr+15}
        result["color"]=color_info; result["size"]=orig_size
        result["sobel"]=sobel_analysis(gray/255.0)
        result["canny"]=canny_analysis(gray_u8)
        result["orb"]=orb_keypoints(gray_u8)
        result["glcm"]=glcm_texture(gray_u8)
        result["fft"]=fft_analysis(gray/255.0)
        result["kmeans_palette"],result["color_temps"]=kmeans_colors(arr.astype(np.uint8),k=7)
        result["histograms"]={"r":np.histogram(r_ch.ravel(),bins=32,range=(0,255))[0].tolist(),
                               "g":np.histogram(g_ch.ravel(),bins=32,range=(0,255))[0].tolist(),
                               "b":np.histogram(b_ch.ravel(),bins=32,range=(0,255))[0].tolist()}
        result["classification"]=classify_scientific_image(result["sobel"],result["canny"],result["glcm"],
                                                            result["orb"],result["fft"],color_info,result["kmeans_palette"])
        result["array_shape"]=[new_h,new_w]; result["ok"]=True
    except Exception as e: result["ok"]=False; result["error"]=str(e)
    return result

# ================================================
#  DOCUMENT ANALYSIS
# ================================================
@st.cache_data(show_spinner=False)
def extract_pdf(b):
    if PyPDF2 is None: return ""
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
    tm={"Saúde & Medicina":["saúde","medicina","clínico","health","medical","therapy","disease","clinical"],
        "Biologia & Genômica":["biologia","genômica","gene","dna","rna","proteína","célula","crispr","molecular"],
        "Neurociência":["neurociência","neural","cérebro","cognição","memória","sono","brain","sináptico"],
        "Computação & IA":["algoritmo","machine","learning","inteligência","dados","computação","ia","deep","quantum","llm"],
        "Física & Astronomia":["física","quântica","partícula","energia","galáxia","astrofísica","cosmologia","lensing"],
        "Química":["química","molécula","síntese","reação","polímero","ligação","composto"],
        "Engenharia":["engenharia","sistema","robótica","automação","sensor","protocolo"],
        "Ciências Sociais":["sociedade","cultura","educação","política","psicologia","comportamento","cognitivo"],
        "Ecologia & Ambiente":["ecologia","clima","ambiente","biodiversidade","carbono","sustentável"],
        "Matemática & Estatística":["matemática","estatística","probabilidade","equação","teorema","variância"]}
    s=defaultdict(int)
    for kw in kws:
        for tp,terms in tm.items():
            if any(t in kw or kw in t for t in terms): s[tp]+=1
    return dict(sorted(s.items(),key=lambda x:-x[1])) if s else {"Pesquisa Geral":1}

def compute_research_stats(posts):
    """Compute temporal and statistical analysis of research posts."""
    if not posts: return {}
    by_month=defaultdict(list)
    for p in posts:
        d=p.get("date","2026-01-01")
        try: month=d[:7]
        except: month="2026-01"
        by_month[month].append(p)
    months=sorted(by_month.keys())
    monthly_counts=[len(by_month[m]) for m in months]
    monthly_likes=[sum(p["likes"] for p in by_month[m]) for m in months]
    all_tags=Counter(t for p in posts for t in p.get("tags",[]))
    all_areas=Counter(p.get("area","") for p in posts if p.get("area"))
    methodologies=Counter(p.get("methodology","") for p in posts if p.get("methodology"))
    avg_likes=sum(p["likes"] for p in posts)/len(posts) if posts else 0
    avg_views=sum(p.get("views",0) for p in posts)/len(posts) if posts else 0
    return {"months":months,"monthly_counts":monthly_counts,"monthly_likes":monthly_likes,
            "top_tags":dict(all_tags.most_common(10)),"top_areas":dict(all_areas.most_common(8)),
            "methodologies":dict(methodologies.most_common(5)),"avg_likes":round(avg_likes,1),
            "avg_views":round(avg_views,1),"total_citations":sum(p.get("citations",0) for p in posts)}

@st.cache_data(show_spinner=False,ttl=1800)
def search_ss(q,lim=6):
    try:
        r=requests.get("https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query":q,"limit":lim,"fields":"title,authors,year,abstract,venue,externalIds,openAccessPdf,citationCount"},
            timeout=8)
        if r.status_code==200:
            out=[]
            for p in r.json().get("data",[]):
                ext=p.get("externalIds",{})\
                    or{}; doi=ext.get("DOI",""); arx=ext.get("ArXiv","")
                pdf=p.get("openAccessPdf") or{}
                link=pdf.get("url","") or (f"https://arxiv.org/abs/{arx}" if arx else (f"https://doi.org/{doi}" if doi else ""))
                al=p.get("authors",[])\
                    or[]; au=", ".join(a.get("name","") for a in al[:3])
                if len(al)>3: au+=" et al."
                out.append({"title":p.get("title","Sem título"),"authors":au or "—","year":p.get("year","?"),
                            "source":p.get("venue","") or "Semantic Scholar","doi":doi or arx or "—",
                            "abstract":(p.get("abstract","") or "")[:300],"url":link,
                            "citations":p.get("citationCount",0),"origin":"semantic"})
            return out
    except: pass
    return []

@st.cache_data(show_spinner=False,ttl=1800)
def search_cr(q,lim=3):
    try:
        r=requests.get("https://api.crossref.org/works",
            params={"query":q,"rows":lim,"select":"title,author,issued,abstract,DOI,container-title,is-referenced-by-count","mailto":"nebula@example.com"},
            timeout=8)
        if r.status_code==200:
            out=[]
            for p in r.json().get("message",{}).get("items",[]):
                title=(p.get("title") or["?"])[0]
                ars=p.get("author",[]) or[]
                au=", ".join(f'{a.get("given","").split()[0] if a.get("given") else ""} {a.get("family","")}'.strip() for a in ars[:3])
                if len(ars)>3: au+=" et al."
                yr=(p.get("issued",{}).get("date-parts") or[[None]])[0][0]
                doi=p.get("DOI",""); ab=re.sub(r'<[^>]+>','',p.get("abstract","") or "")[:300]
                out.append({"title":title,"authors":au or "—","year":yr or "?",
                            "source":(p.get("container-title") or["CrossRef"])[0],"doi":doi,
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
    M={"ia":["machine learning","LLM"],"inteligência artificial":["machine learning","LLM","deep learning"],
       "neurociência":["sono","memória","cognição","plasticidade"],"biologia":["célula","genômica","proteína"],
       "física":["quantum","astrofísica","energia"],"medicina":["diagnóstico","terapia","clínico"]}
    for k,v in M.items():
        if k in a: return v
    return [w.strip() for w in a.replace(","," ").split() if len(w)>3][:5]

EMAP={"pdf":"PDF","docx":"Word","xlsx":"Planilha","csv":"Dados","txt":"Texto","py":"Código","md":"Markdown","png":"Imagem","jpg":"Imagem","jpeg":"Imagem","tiff":"Imagem","ipynb":"Notebook"}
def ftype(fname): return EMAP.get(fname.split(".")[-1].lower() if "." in fname else "","Arquivo")

# Using a single color for consistency, removed VIB gradient pool
PRIMARY_COLOR = "#0D7FE8"
SECONDARY_COLOR = "#36B8A0"
TERTIARY_COLOR = "#9B6FD4"
WARNING_COLOR = "#FF8C42"
ERROR_COLOR = "#F03E5A"
TEXT_COLOR_LIGHT = "#E2E6F0"
TEXT_COLOR_MEDIUM = "#9AA3BC"
TEXT_COLOR_DARK = "#5A6180"
BG_COLOR_DARK = "#060B14"
BG_COLOR_MEDIUM = "#0B1220"
BG_COLOR_LIGHT = "#101828"
BORDER_COLOR = "rgba(255,255,255,.07)"
BUTTON_HOVER_BG = "rgba(13,127,232,.12)"
BUTTON_HOVER_BORDER = "rgba(13,127,232,.3)"

# ================================================
#  CSS — DARK BLUE + LIQUID GLASS (Modified for transparency and no animations)
# ================================================
def inject_css():
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800;900&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');

:root{{
  --bg:{BG_COLOR_DARK};--bg2:{BG_COLOR_MEDIUM};--bg3:{BG_COLOR_LIGHT};
  --acc:{PRIMARY_COLOR};--acc2:#1A6EC9;--acc3:#0A5CB3;
  --teal:{SECONDARY_COLOR};--teal2:#2E9D8A;
  --red:{ERROR_COLOR};--orn:{WARNING_COLOR};--pur:{TERTIARY_COLOR};--cya:#38C8F0;
  --t0:#FFFFFF;--t1:{TEXT_COLOR_LIGHT};--t2:{TEXT_COLOR_MEDIUM};--t3:{TEXT_COLOR_DARK};--t4:#2E3450;
  --g1:rgba(255,255,255,.042);--g2:rgba(255,255,255,.07);--g3:rgba(255,255,255,.11);
  --gb1:rgba(255,255,255,.07);--gb2:rgba(255,255,255,.11);--gb3:rgba(255,255,255,.18);
  --r8:8px;--r12:12px;--r16:16px;--r20:20px;--r28:28px;
  --gls:rgba(13,127,232,.08);--gls-bdr:rgba(13,127,232,.18);
}}
*,*::before,**::after{{box-sizing:border-box;margin:0;padding:0}}
html,body,.stApp{{background:var(--bg)!important;color:var(--t1)!important;font-family:'DM Sans',-apple-system,sans-serif!important;}}

/* Removed ambient background animations */
.stApp::before, .stApp::after {{
    content: '';
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    background: none !important; /* Remove all background animations */
}}

header[data-testid="stHeader"],#MainMenu,footer,.stDeployButton,[data-testid="stToolbar"],[data-testid="stDecoration"]{{display:none!important}}
[data-testid="stSidebarCollapseButton"],[data-testid="collapsedControl"]{{display:none!important}}

/* ===== SIDEBAR ===== */
section[data-testid="stSidebar"]{{
  display:block!important;transform:translateX(0)!important;visibility:visible!important;
  background:rgba(4,7,16,.97)!important;
  backdrop-filter:blur(40px) saturate(200%)!important;
  -webkit-backdrop-filter:blur(40px) saturate(200%)!important;
  border-right:1px solid rgba(255,255,255,.07)!important;
  box-shadow:4px 0 40px rgba(0,0,0,.5)!important;
  width:220px!important;min-width:220px!important;max-width:220px!important;
  padding:1.3rem .9rem 1rem!important;
}}
section[data-testid="stSidebar"]>div{{width:220px!important;padding:0!important;}}

/* ===== TRANSPARENT BUTTONS — SIDEBAR ===== */
section[data-testid="stSidebar"] .stButton>button{{
  position:relative;overflow:hidden;
  background:transparent!important; /* Transparent background */
  backdrop-filter:none!important; /* No blur */
  -webkit-backdrop-filter:none!important;
  border:1px solid transparent!important; /* Transparent border */
  border-radius:12px!important;
  box-shadow:none!important; /* No shadow */
  color:#9AA3BC!important;-webkit-text-fill-color:#9AA3BC!important;
  font-family:'DM Sans',sans-serif!important;font-weight:500!important;font-size:.83rem!important;
  padding:.52rem .9rem!important;text-align:left!important;justify-content:flex-start!important;
  width:100%!important;margin-bottom:.18rem!important;
  transition:all .15s cubic-bezier(.4,0,.2,1)!important;
}}
section[data-testid="stSidebar"] .stButton>button::before,
section[data-testid="stSidebar"] .stButton>button::after{{
  content:'';position:absolute;pointer-events:none;
  background:none!important; /* Remove button specific effects */
}}
section[data-testid="stSidebar"] .stButton>button:hover{{
  background:{BUTTON_HOVER_BG}!important; /* Subtle hover effect */
  border-color:{BUTTON_HOVER_BORDER}!important; /* Subtle border on hover */
  color:#FFFFFF!important;-webkit-text-fill-color:#FFFFFF!important;
  transform:translateY(-1px)!important;
}}
section[data-testid="stSidebar"] .stButton>button:active{{transform:translateY(0)!important;}}
section[data-testid="stSidebar"] .stButton>button p,
section[data-testid="stSidebar"] .stButton>button span{{color:inherit!important;-webkit-text-fill-color:inherit!important;}}

/* Main buttons - also transparent */
.stButton>button{{
  background:transparent!important;
  backdrop-filter:none!important;
  border:1px solid transparent!important;
  border-radius:10px!important;color:#C8CEDE!important;-webkit-text-fill-color:#C8CEDE!important;
  font-family:'DM Sans',sans-serif!important;font-weight:500!important;font-size:.82rem!important;
  padding:.45rem .8rem!important;
  box-shadow:none!important;
  transition:all .12s ease!important;
}}
.stButton>button:hover{{
  background:{BUTTON_HOVER_BG}!important;
  border-color:{BUTTON_HOVER_BORDER}!important;
  color:#fff!important;-webkit-text-fill-color:#fff!important;
  box-shadow:none!important;
  transform:translateY(-1px)!important;
}}
.stButton>button:active{{transform:translateY(0)!important;}}
.stButton>button p,.stButton>button span{{color:inherit!important;-webkit-text-fill-color:inherit!important;}}

/* Layout */
.block-container{{padding-top:.3rem!important;padding-bottom:4rem!important;max-width:1400px!important;position:relative;z-index:1;padding-left:.9rem!important;padding-right:.9rem!important;}}

/* Inputs */
.stTextInput input,.stTextArea textarea{{
  background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;
  border-radius:var(--r12)!important;color:var(--t1)!important;
  font-family:'DM Sans',sans-serif!important;font-size:.84rem!important;
}}
.stTextInput input:focus,.stTextArea textarea:focus{{
  border-color:rgba(13,127,232,.5)!important;
  box-shadow:0 0 0 3px rgba(13,127,232,.1)!important;
}}
.stTextInput label,.stTextArea label,.stSelectbox label,.stFileUploader label,.stNumberInput label{{
  color:var(--t3)!important;font-size:.59rem!important;letter-spacing:.11em!important;
  text-transform:uppercase!important;font-weight:700!important;
}}

/* Cards */
.glass{{background:rgba(255,255,255,.04);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,.08);border-radius:var(--r20);box-shadow:0 0 0 1px rgba(255,255,255,.03) inset,0 6px 36px rgba(0,0,0,.35);position:relative;overflow:hidden;}}
.glass::before{{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.1),transparent);pointer-events:none;}}

.post-card{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:var(--r20);margin-bottom:.6rem;overflow:hidden;box-shadow:0 2px 24px rgba(0,0,0,.28);transition:border-color .15s,transform .15s,box-shadow .15s;}}
.post-card:hover{{border-color:rgba(13,127,232,.25);transform:translateY(-2px);box-shadow:0 8px 32px rgba(13,127,232,.1);}}

.sc{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:var(--r20);padding:.9rem 1rem;margin-bottom:.6rem;}}
.scard{{background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.07);border-radius:var(--r16);padding:.8rem 1rem;margin-bottom:.42rem;transition:border-color .13s,transform .12s,box-shadow .13s;}}
.scard:hover{{border-color:rgba(13,127,232,.2);transform:translateY(-1px);box-shadow:0 4px 20px rgba(13,127,232,.08);}}

.mbox{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:var(--r16);padding:.9rem;text-align:center;}}
.abox{{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.09);border-radius:var(--r16);padding:1rem;margin-bottom:.6rem;}}

/* Analysis boxes */
.pbox-acc{{background:rgba(13,127,232,.06);border:1px solid rgba(13,127,232,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.5rem;}}
.pbox-teal{{background:rgba(54,184,160,.06);border:1px solid rgba(54,184,160,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.5rem;}}
.pbox-pur{{background:rgba(155,111,212,.06);border:1px solid rgba(155,111,212,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.5rem;}}
.pbox-red{{background:rgba(240,62,90,.06);border:1px solid rgba(240,62,90,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.5rem;}}
.pbox-orn{{background:rgba(255,140,66,.06);border:1px solid rgba(255,140,66,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.5rem;}}

/* AI cards */
.ai-card{{background:linear-gradient(135deg,rgba(13,127,232,.07),rgba(54,184,160,.04));border:1px solid rgba(13,127,232,.2);border-radius:var(--r16);padding:1.1rem;margin-bottom:.7rem;position:relative;overflow:hidden;}}
.ai-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(13,127,232,.3),transparent);}}

.conn-card{{background:linear-gradient(135deg,rgba(54,184,160,.06),rgba(13,127,232,.04));border:1px solid rgba(54,184,160,.2);border-radius:var(--r16);padding:1rem;margin-bottom:.6rem;position:relative;}}
.conn-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(54,184,160,.3),transparent);}}

.repo-card{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:var(--r16);padding:1rem;margin-bottom:.5rem;transition:all .15s;}}
.repo-card:hover{{border-color:rgba(13,127,232,.22);box-shadow:0 4px 20px rgba(13,127,232,.08);}}

.chart-wrap{{background:rgba(255,255,255,.025);border:1px solid rgba(255,255,255,.06);border-radius:var(--r12);padding:.6rem;margin-bottom:.6rem;}}

.compose-box{{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:var(--r20);padding:1.1rem 1.3rem;margin-bottom:.8rem;}}

/* Metric values */
.mval-acc{{font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:900;background:linear-gradient(135deg,var(--acc),var(--cya));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}}
.mval-teal{{font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:900;background:linear-gradient(135deg,var(--teal),var(--cya));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}}
.mval-pur{{font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:900;background:linear-gradient(135deg,var(--pur),var(--acc));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}}
.mval-red{{font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:900;background:linear-gradient(135deg,var(--red),var(--orn));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}}
.mlbl{{font-size:.57rem;color:var(--t3);margin-top:4px;letter-spacing:.1em;text-transform:uppercase;font-weight:700;}}

/* Badges & tags */
.tag{{display:inline-block;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);border-radius:50px;padding:2px 9px;font-size:.62rem;color:var(--t2);margin:2px;font-weight:500;}}
.badge-acc{{display:inline-block;background:rgba(13,127,232,.12);border:1px solid rgba(13,127,232,.25);border-radius:50px;padding:2px 9px;font-size:.62rem;font-weight:700;color:#5BAAFF;}}
.badge-teal{{display:inline-block;background:rgba(54,184,160,.12);border:1px solid rgba(54,184,160,.25);border-radius:50px;padding:2px 9px;font-size:.62rem;font-weight:700;color:#36B8A0;}}
.badge-red{{display:inline-block;background:rgba(240,62,90,.12);border:1px solid rgba(240,62,90,.25);border-radius:50px;padding:2px 9px;font-size:.62rem;font-weight:700;color:var(--red);}}
.badge-pur{{display:inline-block;background:rgba(155,111,212,.12);border:1px solid rgba(155,111,212,.25);border-radius:50px;padding:2px 9px;font-size:.62rem;font-weight:700;color:#B98FE8;}}
.badge-orn{{display:inline-block;background:rgba(255,140,66,.12);border:1px solid rgba(255,140,66,.25);border-radius:50px;padding:2px 9px;font-size:.62rem;font-weight:700;color:var(--orn);}}

/* Removed pulse animation for dots */
.dot-on{{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--teal);margin-right:4px;vertical-align:middle;}}
.dot-off{{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--t4);margin-right:4px;vertical-align:middle;}}

@keyframes fadeUp{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
.pw{{animation:fadeUp .2s ease both;}}

/* Chat bubbles */
.bme{{background:linear-gradient(135deg,rgba(13,127,232,.2),rgba(54,184,160,.1));border:1px solid rgba(13,127,232,.25);border-radius:18px 18px 4px 18px;padding:.55rem .88rem;max-width:70%;margin-left:auto;margin-bottom:5px;font-size:.82rem;line-height:1.6;}}
.bthem{{background:var(--g2);border:1px solid var(--gb1);border-radius:18px 18px 18px 4px;padding:.55rem .88rem;max-width:70%;margin-bottom:5px;font-size:.82rem;line-height:1.6;}}
.cmt{{background:rgba(255,255,255,.03);border:1px solid var(--gb1);border-radius:var(--r12);padding:.5rem .85rem;margin-bottom:.25rem;}}

/* Tabs */
.stTabs [data-baseweb="tab-list"]{{background:rgba(255,255,255,.03)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;padding:3px!important;gap:2px!important;}}
.stTabs [data-baseweb="tab"]{{background:transparent!important;color:var(--t3)!important;border-radius:9px!important;font-size:.74rem!important;font-family:'DM Sans',sans-serif!important;font-weight:500!important;}}
.stTabs [aria-selected="true"]{{background:rgba(13,127,232,.14)!important;color:var(--cya)!important;border:1px solid rgba(13,127,232,.25)!important;font-weight:700!important;}}
.stTabs [data-baseweb="tab-panel"]{{background:transparent!important;padding-top:.8rem!important;}}

/* Profile */
.prof-hero{{background:rgba(255,255,255,.04);backdrop-filter:blur(32px);border:1px solid rgba(255,255,255,.09);border-radius:var(--r28);padding:1.6rem;display:flex;gap:1.2rem;align-items:flex-start;box-shadow:0 8px 48px rgba(0,0,0,.4);margin-bottom:1rem;}}
.prof-av{{width:76px;height:76px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:'Syne',sans-serif;font-weight:800;font-size:1.6rem;color:white;flex-shrink:0;border:2px solid rgba(255,255,255,.12);}}

/* Misc */
hr{{border:none;border-top:1px solid rgba(255,255,255,.07)!important;margin:.8rem 0;}}
.stAlert{{background:var(--g1)!important;border:1px solid var(--gb1)!important;border-radius:var(--r16)!important;}}
.stSelectbox [data-baseweb="select"]{{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;}}
.stFileUploader section{{background:rgba(255,255,255,.03)!important;border:1.5px dashed var(--gb2)!important;border-radius:var(--r16)!important;}}
.stExpander{{background:var(--g1);border:1px solid var(--gb1);border-radius:var(--r16);}}
::-webkit-scrollbar{{width:4px;height:4px;}}
::-webkit-scrollbar-thumb{{background:var(--t4);border-radius:4px;}}
.js-plotly-plot .plotly .modebar{{display:none!important;}}

.dtxt{{display:flex;align-items:center;gap:.7rem;margin:.75rem 0;font-size:.57rem;color:var(--t3);letter-spacing:.10em;text-transform:uppercase;font-weight:700;}}
.dtxt::before,.dtxt::after{{content:'';flex:1;height:1px;background:var(--gb1);}}

/* Sidebar logo & labels */
.sb-logo{{display:flex;align-items:center;gap:9px;margin-bottom:1.5rem;padding:.2rem .3rem;}}
.sb-logo-icon{{width:36px;height:36px;border-radius:11px;background:{PRIMARY_COLOR};display:flex;align-items:center;justify-content:center;font-size:.92rem;flex-shrink:0;box-shadow:0 4px 12px rgba(13,127,232,.3);}}
.sb-logo-txt{{font-family:'Syne',sans-serif;font-weight:900;font-size:1.25rem;letter-spacing:-.04em;background:linear-gradient(135deg,{PRIMARY_COLOR},{SECONDARY_COLOR});-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}}
.sb-lbl{{font-size:.53rem;font-weight:700;color:var(--t4);letter-spacing:.14em;text-transform:uppercase;padding:0 .2rem;margin-bottom:.35rem;margin-top:.85rem;}}

h1{{font-family:'Syne',sans-serif!important;font-size:1.55rem!important;font-weight:800!important;letter-spacing:-.03em;color:var(--t0)!important;}}
h2{{font-family:'Syne',sans-serif!important;font-size:1rem!important;font-weight:700!important;color:var(--t0)!important;}}
label{{color:var(--t2)!important;}}
.stCheckbox label,.stRadio label{{color:var(--t1)!important;}}
.stRadio>div{{display:flex!important;gap:4px!important;flex-wrap:wrap!important;}}
.stRadio>div>label{{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:50px!important;padding:.28rem .78rem!important;font-size:.73rem!important;cursor:pointer!important;color:var(--t2)!important;}}
input[type="number"]{{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;color:var(--t1)!important;}}

/* Progress bars */
.prog-bar-track{{background:rgba(255,255,255,.06);border-radius:50px;height:6px;margin:.35rem 0;}}
.prog-bar-fill{{height:6px;border-radius:50px;transition:width .6s ease;}}

/* Score ring */
.score-ring{{position:relative;display:inline-flex;align-items:center;justify-content:center;}}

/* API Banner */
.api-banner{{background:linear-gradient(135deg,rgba(155,111,212,.07),rgba(56,200,240,.05));border:1px solid rgba(155,111,212,.22);border-radius:var(--r16);padding:.9rem 1.1rem;margin-bottom:.8rem;}}
.ml-feat{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:var(--r12);padding:.65rem .85rem;margin-bottom:.38rem;}}

/* Sidebar active state injected dynamically */
</style>""",unsafe_allow_html=True)

# ================================================
#  HTML HELPERS
# ================================================
def avh(initials,sz=40,grad=None):
    fs=max(sz//3,9)
    bg=grad or AVATAR_BG_COLOR # Use fixed color
    return f'<div style="width:{sz}px;height:{sz}px;border-radius:50%;background:{bg};display:flex;align-items:center;justify-content:center;font-family:Syne,sans-serif;font-weight:800;font-size:{fs}px;color:white;flex-shrink:0;border:1.5px solid rgba(255,255,255,.12)">{initials}</div>'

def tags_html(tags):
    return ' '.join(f'<span class="tag">{{t}}</span>' for t in (tags or []))

def badge(s):
    m={"Publicado":"badge-teal","Concluído":"badge-pur"}
    return f'<span class="{m.get(s,"badge-acc")}">{{s}}</span>'

def prog_bar(val,color=PRIMARY_COLOR,max_val=100):
    pct=min(100,val/max_val*100) if max_val>0 else 0
    return f'<div class="prog-bar-track"><div class="prog-bar-fill" style="width:{pct:.0f}%;background:{color}"></div></div>'

def pc_dark():
    return dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color=TEXT_COLOR_DARK,family="DM Sans",size=11),
                margin=dict(l=10,r=10,t=38,b=10),
                xaxis=dict(showgrid=False,color=TEXT_COLOR_DARK,tickfont=dict(size=10)),
                yaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,.04)",color=TEXT_COLOR_DARK,tickfont=dict(size=10)))

# ================================================
#  NAVIGATION
# ================================================
# Changed "feed" to "repository" as the main page
NAV=[("repository","Repositório","acc"),("search","Busca","cya"),("knowledge","Conexões","teal"),
     ("analytics","Análises","pur"),("chat","Chat","teal"),("settings","Configurações","red")]

def render_nav():
    email=st.session_state.current_user
    u=guser(); name=u.get("name","?"); ini_=ini(name); g=ugrad(email); cur=st.session_state.page
    with st.sidebar:
        st.markdown('<div class="sb-logo"><div class="sb-logo-icon"> </div><div class="sb-logo-txt">Nebula</div></div>',unsafe_allow_html=True) # Removed emoji
        st.markdown('<div class="sb-lbl">Navegação</div>',unsafe_allow_html=True)
        # Active highlighting
        active_css=""
        for i,(key,label,col) in enumerate(NAV):
            if cur==key and not st.session_state.profile_view:
                cc_map={"acc":PRIMARY_COLOR,"teal":SECONDARY_COLOR,"cya":"#38C8F0","orn":WARNING_COLOR,"pur":TERTIARY_COLOR,"red":ERROR_COLOR}
                c=cc_map.get(col,PRIMARY_COLOR)
                active_css+=(f'section[data-testid="stSidebar"] [data-testid="stVerticalBlock"]'
                              f' > [data-testid="stVerticalBlock"]:nth-child({i+2})' # Adjust index if needed
                              f' .stButton>button{{color:{c}!important;-webkit-text-fill-color:{c}!important;'
                              f'background:{BUTTON_HOVER_BG}!important;border-color:{c}33!important;font-weight:700!important;'
                              f'box-shadow:0 0 0 1px {c}20 inset,0 4px 16px rgba(13,127,232,.15)!important;}}')
        if active_css: st.markdown(f'<style>{{active_css}}</style>',unsafe_allow_html=True) # Corrected f-string here
        for key,label,col in NAV:
            if st.button(label,key=f"sb_{key}",use_container_width=True):
                st.session_state.profile_view=None
                st.session_state.page=key
                st.rerun()
        # Notifications - Removed emoji
        notifs=st.session_state.get("notifications",[])
        if notifs:
            st.markdown(f'<div style="margin:.6rem .2rem .35rem;font-size:.57rem;color:var(--acc);font-weight:700;letter-spacing:.09em;text-transform:uppercase"> {{len(notifs)}} notificações</div>',unsafe_allow_html=True) # Corrected f-string here
        st.markdown("<hr>",unsafe_allow_html=True)
        st.markdown('<div class="sb-lbl">Claude API Key</div>',unsafe_allow_html=True)
        ak=st.text_input("",placeholder="sk-ant-...",type="password",key="sb_apikey",label_visibility="collapsed",value=st.session_state.anthropic_key)
        if ak!=st.session_state.anthropic_key: st.session_state.anthropic_key=ak
        if ak and ak.startswith("sk-"):
            st.markdown(f'<div style="font-size:.54rem;color:{SECONDARY_COLOR};padding:.1rem .2rem">● Claude ativo — análise IA habilitada</div>',unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="font-size:.54rem;color:var(--t4);padding:.1rem .2rem">● Insira chave para IA avançada</div>',unsafe_allow_html=True)
        st.markdown("<hr>",unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:.2rem .1rem">{{avh(ini_,32,g)}}<div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.78rem;color:#FFF;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:128px">{{name}}</div><div style="font-size:.57rem;color:var(--t3)">{{u.get("area","")[:18]}}</div></div></div>',unsafe_allow_html=True) # Corrected f-string here
        if st.button("Meu Perfil",key="sb_myprofile",use_container_width=True):
            st.session_state.profile_view=email
            st.session_state.page="repository" # Changed to repository as main page
            st.rerun()

# ================================================
#  POST RENDERING (Kept for compatibility, but not directly used in new main flow)
# ================================================
def render_post(post,ctx="feed",show_author=True,compact=False):
    email=st.session_state.current_user; pid=post["id"]
    liked=email in post.get("liked_by",[]); saved=email in post.get("saved_by",[])
    aemail=post.get("author_email",""); ain=post.get("avatar","??"); aname=post.get("author","?")
    g=ugrad(aemail); dt=time_ago(post.get("date","")); views=post.get("views",200)
    ab=post.get("abstract","")
    if compact and len(ab)>220: ab=ab[:220]+"…"
    if show_author:
        hdr=(f'<div style="padding:.75rem 1.1rem .5rem;display:flex;align-items:center;gap:9px;border-bottom:1px solid rgba(255,255,255,.04)">'
             f'{{avh(ain,36,g)}}<div style="flex:1;min-width:0">' # Corrected f-string here
             f'<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.85rem;color:var(--t0)">{{aname}}</div>' # Corrected f-string here
             f'<div style="color:var(--t3);font-size:.62rem">{{post.get("area","")}} · {{dt}}</div>' # Corrected f-string here
             f'</div>{{badge(post["status"])}}</div>') # Corrected f-string here
    else:
        hdr=f'<div style="padding:.3rem 1.1rem .12rem;display:flex;justify-content:space-between;align-items:center"><span style="color:var(--t3);font-size:.62rem">{{dt}}</span>{{badge(post["status"])}}</div>' # Corrected f-string here
    citations=post.get("citations",0)
    cit_html=f'<span style="font-size:.62rem;color:var(--t2);margin-left:8px"> {{citations}} cit.</span>' if citations else "" # Corrected f-string here
    st.markdown(f'<div class="post-card">{{hdr}}<div style="padding:.6rem 1.1rem">' # Corrected f-string here
                f'<div style="font-family:Syne,sans-serif;font-size:.95rem;font-weight:700;margin-bottom:.28rem;color:var(--t0)">{{post["title"]}}{{cit_html}}</div>' # Corrected f-string here
                f'<div style="color:var(--t2);font-size:.78rem;line-height:1.65;margin-bottom:.48rem">{{ab}}</div>' # Corrected f-string here
                f'<div>{{tags_html(post.get("tags",[]))}}</div></div></div>',unsafe_allow_html=True) # Corrected f-string here
    heart=" " if liked else " "; book=" " if saved else " "; nc=len(post.get("comments",[])) # Removed emojis
    ca,cb,cc,cd,ce,cf=st.columns([1.1,1,.65,.55,1,1.1])
    with ca:
        if st.button(f"{heart} {{fmt_num(post['likes'])}}",key=f"lk_{ctx}_{pid}",use_container_width=True): # Corrected f-string here
            if liked: post["liked_by"].remove(email); post["likes"]=max(0,post["likes"]-1)
            else: post["liked_by"].append(email); post["likes"]+=1; record(post.get("tags",[]),1.5)
            save_db(); st.rerun()
    with cb:
        if st.button(f" {{nc}}" if nc else " ",key=f"cm_{ctx}_{pid}",use_container_width=True): # Corrected f-string here
            k=f"cmt_{ctx}_{pid}"; st.session_state[k]=not st.session_state.get(k,False); st.rerun()
    with cc:
        if st.button(book,key=f"sv_{ctx}_{pid}",use_container_width=True):
            if saved: post["saved_by"].remove(email)
            else: post["saved_by"].append(email)
            save_db(); st.rerun()
    with cd:
        if st.button("Análise",key=f"dp_{ctx}_{pid}",use_container_width=True): # Changed emoji to text
            st.session_state[f"deepan_{pid}"]=not st.session_state.get(f"deepan_{pid}",False); st.rerun()
    with ce:
        st.markdown(f'<div style="text-align:center;color:var(--t3);font-size:.66rem;padding:.48rem 0"> {{fmt_num(views)}}</div>',unsafe_allow_html=True) # Corrected f-string here
    with cf:
        if show_author and aemail:
            if st.button(f" {{aname.split()[0]}}",key=f"vp_{ctx}_{pid}",use_container_width=True): # Corrected f-string here
                st.session_state.profile_view=aemail; st.rerun()
    # Deep analysis inline
    if st.session_state.get(f"deepan_{pid}",False):
        render_post_deep_analysis(post,ctx)
    # Comments
    if st.session_state.get(f"cmt_{ctx}_{pid}",False):
        for c in post.get("comments",[]):
            ci=ini(c["user"]); ce2=next((e for e,u in st.session_state.users.items() if u.get("name")==c["user"]),""); cg=ugrad(ce2)
            st.markdown(f'<div class="cmt"><div style="display:flex;align-items:center;gap:7px;margin-bottom:.2rem">{{avh(ci,26,cg)}}<span style="font-size:.73rem;font-weight:700;color:var(--acc)">{{c["user"]}}</span></div><div style="font-size:.78rem;color:var(--t2);line-height:1.55;padding-left:33px">{{c["text"]}}</div></div>',unsafe_allow_html=True) # Corrected f-string here
        nc_txt=st.text_input("",placeholder="Escreva um comentário…",key=f"ci_{ctx}_{pid}",label_visibility="collapsed")
        if st.button("Enviar",key=f"cs_{ctx}_{pid}"): # Removed emoji
            if nc_txt:
                uu=guser(); post["comments"].append({"user":uu.get("name","Você"),"text":nc_txt})
                record(post.get("tags",[]),.8); save_db(); st.rerun()

def render_post_deep_analysis(post,ctx=""):
    """Inline deep analysis of a post with temporal, statistical, improvement insights."""
    pid=post["id"]; cache_key=f"da_{pid}"
    api_key=st.session_state.get("anthropic_key","")
    # Algorithmic analysis (always available)
    title=post.get("title",""); abstract=post.get("abstract","")
    tags=post.get("tags",[]); likes=post["likes"]; views=post.get("views",0)
    citations=post.get("citations",0); status=post.get("status","")
    # Score calculations
    engagement_score=min(100,int((likes*2+views*0.05+citations*3)))
    novelty_score=min(100,len(set(tags))*10+len(abstract)//20)
    completeness=min(100,(30 if title else 0)+(40 if len(abstract)>200 else 20)+(20 if tags else 0)+(10 if status=="Publicado" else 5))
    all_tags=Counter(t for p in st.session_state.feed_posts for t in p.get("tags",[]))
    tag_rarity=sum(1 for t in tags if all_tags.get(t,0)<=2)
    similar_posts=[p for p in st.session_state.feed_posts if p["id"]!=pid and any(t in p.get("tags",[]) for t in tags)]
    st.markdown(f'<div class="ai-card"><div style="font-size:.58rem;color:var(--acc);font-weight:700;letter-spacing:.09em;text-transform:uppercase;margin-bottom:.7rem"> Análise Aprofundada</div>',unsafe_allow_html=True) # Removed emoji
    c1,c2,c3=st.columns(3)
    with c1:
        eg_c=SECONDARY_COLOR if engagement_score>60 else (WARNING_COLOR if engagement_score>30 else ERROR_COLOR)
        st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1.4rem;font-weight:900;color:{eg_c}">{{engagement_score}}</div><div class="mlbl">Engajamento</div></div>',unsafe_allow_html=True) # Corrected f-string here
    with c2:
        st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1.4rem;font-weight:900;color:{TERTIARY_COLOR}">{{novelty_score}}</div><div class="mlbl">Novidade</div></div>',unsafe_allow_html=True) # Corrected f-string here
    with c3:
        cc_=(SECONDARY_COLOR if completeness>80 else WARNING_COLOR)
        st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1.4rem;font-weight:900;color:{cc_}">{{completeness}}%</div><div class="mlbl">Completude</div></div>',unsafe_allow_html=True) # Corrected f-string here
    # Improvement points
    improvements=[]
    if len(abstract)<300: improvements.append("Expandir o resumo com metodologia detalhada") # Removed emoji
    if len(tags)<4: improvements.append("Adicionar mais tags para melhor descoberta") # Removed emoji
    if citations<5: improvements.append("Incluir mais referências bibliográficas") # Removed emoji
    if not post.get("methodology"): improvements.append("Especificar metodologia utilizada") # Removed emoji
    if improvements:
        st.markdown(f'<div class="pbox-orn" style="margin-top:.5rem"><div style="font-size:.65rem;color:var(--orn);font-weight:700;margin-bottom:.4rem"> Sugestões de melhoria</div>{{"".join(f"<div style=\"font-size:.73rem;color:var(--t2);margin-bottom:.22rem\">→ {{imp}}</div>" for imp in improvements)}}</div>',unsafe_allow_html=True) # Corrected f-string here
    if similar_posts:
        st.markdown(f'<div style="font-size:.62rem;color:var(--t3);margin-top:.5rem;font-weight:600"> {{len(similar_posts)}} pesquisas similares na plataforma</div>',unsafe_allow_html=True) # Corrected f-string here
    # AI Analysis button
    if api_key.startswith("sk-") if api_key else False:
        if st.button(f"Análise Claude IA",key=f"claude_an_{ctx}_{pid}"): # Removed emoji
            content=f"Título: {title}\nResumo: {abstract}\nTags: {', '.join(tags)}\nStatus: {status}"
            with st.spinner("Claude analisando…"):
                result,err=call_claude_analysis(content,api_key,"research")
            if result: st.session_state.deep_analysis_cache[cache_key]=result
            elif err: st.error(f"Erro: {{err}}") # Corrected f-string here
        da=st.session_state.deep_analysis_cache.get(cache_key)
        if da:
            st.markdown(f'<div style="margin-top:.6rem;background:rgba(155,111,212,.06);border:1px solid rgba(155,111,212,.18);border-radius:12px;padding:.8rem">'
                        f'<div style="font-size:.62rem;color:#B98FE8;font-weight:700;margin-bottom:.4rem"> Claude IA</div>' # Removed emoji
                        f'<div style="font-size:.75rem;color:var(--t2);line-height:1.7">{{da.get("resumo_executivo","")}}</div>' # Corrected f-string here
                        f'<div style="margin-top:.5rem;font-size:.65rem;color:var(--t3)">Metodologia: <strong style="color:var(--t1)">{{da.get("metodologia_score",0)}}/100</strong> · Inovação: <strong style="color:var(--t1)">{{da.get("inovacao_score",0)}}/100</strong> · Impacto: <strong style="color:var(--teal)">{{da.get("impacto_potencial","—")}}</strong></div>' # Corrected f-string here
                        f'</div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ================================================
#  ARTICLE RENDERING
# ================================================
def render_article(a,idx=0,ctx="web"):
    sc=PRIMARY_COLOR if a.get("origin")=="semantic" else SECONDARY_COLOR
    sn="Semantic Scholar" if a.get("origin")=="semantic" else "CrossRef"
    cite=f" · {{a['citations']}} cit." if a.get("citations") else "" # Corrected f-string here
    uid=re.sub(r'[^a-zA-Z0-9]','',f"{{ctx}}_{{idx}}_{str(a.get('doi',''))[:10]}")[:32] # Corrected f-string here
    is_saved=any(s.get('doi')==a.get('doi') for s in st.session_state.saved_articles)
    ab=(a.get("abstract","") or "")[:280]+("…" if len(a.get("abstract",""))>280 else "")
    year_badge=f'<span style="font-size:.58rem;color:#38C8F0;font-weight:700">{{a.get("year","?")}}</span>' # Corrected f-string here
    st.markdown(f'<div class="scard"><div style="display:flex;align-items:flex-start;gap:7px;margin-bottom:.28rem">'
                f'<div style="flex:1;font-family:Syne,sans-serif;font-size:.86rem;font-weight:700;color:var(--t0)">{{a["title"]}}</div>' # Corrected f-string here
                f'<span style="font-size:.57rem;color:{sc};background:rgba(255,255,255,.04);border-radius:7px;padding:2px 7px;white-space:nowrap;flex-shrink:0">{{sn}}</span></div>' # Corrected f-string here
                f'<div style="color:var(--t3);font-size:.63rem;margin-bottom:.3rem">{{a["authors"]}} · <em>{{a["source"]}}</em> · {{year_badge}}{{cite}}</div>' # Corrected f-string here
                f'<div style="color:var(--t2);font-size:.75rem;line-height:1.62">{{ab}}</div></div>',unsafe_allow_html=True) # Corrected f-string here
    ca,cb,cc=st.columns(3)
    with ca:
        cls="badge-teal" if is_saved else ""
        st.markdown(f'<div class="{cls}">',unsafe_allow_html=True)
        if st.button("Salvo" if is_saved else "Salvar",key=f"svw_{uid}"): # Removed emoji
            if is_saved: st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]; st.toast("Removido")
            else: st.session_state.saved_articles.append(a); st.toast("Salvo!") # Removed emoji
            save_db(); st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)
    with cb:
        if st.button("Citar",key=f"ctw_{uid}"): st.toast(f'{{a["authors"]}} ({{a["year"]}}). {{a["title"]}}.') # Corrected f-string here
    with cc:
        if a.get("url"):
            st.markdown(f'<a href="{{a["url"]}}" target="_blank" style="color:var(--cya);font-size:.78rem;text-decoration:none;line-height:2.4;display:block"> Abrir PDF</a>',unsafe_allow_html=True) # Corrected f-string here

# ================================================
#  PAGE: LOGIN
# ================================================
def page_login():
    _,col,_=st.columns([1,1.05,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown(f"""<div style="text-align:center;margin-bottom:2.8rem">
  <div style="display:flex;align-items:center;justify-content:center;gap:12px;margin-bottom:.8rem">
    <div style="width:52px;height:52px;border-radius:16px;background:{PRIMARY_COLOR};display:flex;align-items:center;justify-content:center;font-size:1.5rem;box-shadow:0 0 32px rgba(13,127,232,.35)"> </div>
    <div style="font-family:Syne,sans-serif;font-size:2.7rem;font-weight:900;letter-spacing:-.06em;background:linear-gradient(135deg,{PRIMARY_COLOR},{SECONDARY_COLOR});-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">Nebula</div>
  </div>
  <div style="color:var(--t3);font-size:.59rem;letter-spacing:.28em;text-transform:uppercase;font-weight:700">Repositório de Conhecimento Científico</div>
</div>""",unsafe_allow_html=True)
        ti,tu=st.tabs(["  Entrar  ","  Criar conta  "]) # Removed emojis
        with ti:
            with st.form("lf"):
                em=st.text_input("E-mail",placeholder="seu@email.com",key="li_e")
                pw=st.text_input("Senha",placeholder="••••••••",type="password",key="li_p")
                s=st.form_submit_button("Entrar na plataforma",use_container_width=True) # Removed emoji
                if s:
                    u=st.session_state.users.get(em)
                    if not u: st.error("E-mail não encontrado.")
                    elif u["password"]!=hp(pw): st.error("Senha incorreta.")
                    else:
                        st.session_state.logged_in=True; st.session_state.current_user=em
                        record(area_tags(u.get("area","")),1.0); st.session_state.page="repository"; st.rerun() # Changed to repository
            st.markdown('<div style="text-align:center;color:var(--t3);font-size:.67rem;margin-top:.7rem">Demo: demo@nebula.ai / demo123</div>',unsafe_allow_html=True)
        with tu:
            with st.form("sf"):
                nn=st.text_input("Nome completo",key="su_n"); ne=st.text_input("E-mail",key="su_e")
                na=st.text_input("Área de pesquisa",key="su_a"); nsch=st.text_input("Bolsa",key="su_sch") # Changed to Bolsa
                np_=st.text_input("Senha",type="password",key="su_p"); np2=st.text_input("Confirmar",type="password",key="su_p2")
                s2=st.form_submit_button("Criar conta",use_container_width=True) # Removed emoji
                if s2:
                    if not all([nn,ne,na,np_,np2]): st.error("Preencha todos os campos.")
                    elif np_!=np2: st.error("Senhas não coincidem.")
                    elif ne in st.session_state.users: st.error("E-mail já cadastrado.")
                    else:
                        st.session_state.users[ne]={"name":nn,"password":hp(np_),"bio":"","area":na,"scholarship":nsch or "", # Changed to scholarship
                                                     "followers":0,"following":0,"verified":True,"2fa_enabled":False,"h_index":0,"publications":0}
                        save_db(); st.session_state.logged_in=True; st.session_state.current_user=ne
                        record(area_tags(na),2.0); st.session_state.page="repository"; st.rerun() # Changed to repository

# ================================================
#  PAGE: PROFILE
# ================================================
def page_profile(target_email):
    tu=st.session_state.users.get(target_email,{})
    email=st.session_state.current_user
    if not tu: st.error("Perfil não encontrado."); return
    tname=tu.get("name","?"); ti=ini(tname); is_me=(email==target_email)
    is_fol=target_email in st.session_state.followed; g=ugrad(target_email)
    user_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==target_email]
    liked_posts=[p for p in st.session_state.feed_posts if target_email in p.get("liked_by",[])]
    total_likes=sum(p["likes"] for p in user_posts); total_citations=sum(p.get("citations",0) for p in user_posts)
    vb=f' <span class="badge-teal" style="font-size:.6rem">Verificado</span>' if tu.get("verified") else "" # Removed emoji
    st.markdown(f"""<div class="prof-hero">
  <div class="prof-av" style="background:{g}">{{ti}}</div>
  <div style="flex:1">
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:.22rem">
      <span style="font-family:Syne,sans-serif;font-weight:800;font-size:1.35rem;color:var(--t0)">{{tname}}</span>{{vb}}
    </div>
    <div style="color:var(--acc);font-size:.80rem;font-weight:600;margin-bottom:.12rem">{{tu.get("area","")}}</div>
    <div style="color:var(--t3);font-size:.70rem;margin-bottom:.3rem">{{tu.get("scholarship","")}} {{ "· ORCID: "+tu.get("orcid","") if tu.get("orcid") else ""}}</div>
    <div style="color:var(--t2);font-size:.77rem;line-height:1.7;margin-bottom:.7rem">{{tu.get("bio","Sem biografia.")}}</div>
    <div style="display:flex;gap:1.6rem;flex-wrap:wrap">
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1rem;color:var(--t0)">{{tu.get("followers",0)}}</span><span style="color:var(--t3);font-size:.67rem"> seguidores</span></div>
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1rem;color:var(--t0)">{{tu.get("following",0)}}</span><span style="color:var(--t3);font-size:.67rem"> seguindo</span></div>
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1rem;color:var(--t0)">{{len(user_posts)}}</span><span style="color:var(--t3);font-size:.67rem"> pesquisas</span></div>
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1rem;color:var(--acc)">{{fmt_num(total_likes)}}</span><span style="color:var(--t3);font-size:.67rem"> curtidas</span></div>
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1rem;color:var(--teal)">{{total_citations}}</span><span style="color:var(--t3);font-size:.67rem"> citações</span></div>
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1rem;color:var(--pur)">{{tu.get("h_index",0)}}</span><span style="color:var(--t3);font-size:.67rem"> h-index</span></div>
    </div>
  </div>
</div>""",unsafe_allow_html=True) # Corrected f-string here
    if not is_me:
        c1,c2,c3,_=st.columns([1,1,1,2])
        with c1:
            if st.button("Seguindo" if is_fol else "Seguir",key="su_n",use_container_width=True): # Removed emoji
                if is_fol: st.session_state.followed.remove(target_email); tu["followers"]=max(0,tu.get("followers",0)-1)
                else: st.session_state.followed.append(target_email); tu["followers"]=tu.get("followers",0)+1
                save_db(); st.rerun()
        with c2:
            if st.button("Mensagem",key="pf_chat",use_container_width=True): # Removed emoji
                st.session_state.chat_messages.setdefault(target_email,[])
                st.session_state.active_chat=target_email; st.session_state.page="chat"; st.rerun()
        with c3:
            if st.button("Voltar",key="pf_back",use_container_width=True): st.session_state.profile_view=None; st.rerun() # Removed emoji
        tp,tl=st.tabs([f"  Pesquisas ({{len(user_posts)}})  ",f"  Curtidas ({{len(liked_posts)}})  "]) # Corrected f-string here
        with tp:
            for p in sorted(user_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="profile",show_author=False)
            if not user_posts: st.markdown(f'<div class="glass" style="padding:2rem;text-align:center;color:var(--t3)">Nenhuma pesquisa publicada.</div>',unsafe_allow_html=True) # Removed emoji
        with tl:
            for p in sorted(liked_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="prof_liked",compact=True)
    else:
        saved_arts=st.session_state.saved_articles
        tm,tl,ts2,ts,tst=st.tabs(["  Meus Dados  ",f"  Publicações ({{len(user_posts)}})  ", # Corrected f-string here
                                    f"  Curtidas ({{len(liked_posts)}})  ",f"  Salvos ({{len(saved_arts)}})  ","  Estatísticas  "]) # Corrected f-string here
        with tm:
            new_n=st.text_input("Nome",value=tu.get("name",""),key="cfg_n")
            new_a=st.text_input("Área",value=tu.get("area",""),key="cfg_a")
            new_sch=st.text_input("Bolsa",value=tu.get("scholarship",""),key="cfg_sch") # Changed to Bolsa
            new_orcid=st.text_input("ORCID",value=tu.get("orcid",""),key="cfg_orc",placeholder="0000-0000-0000-0000")
            new_b=st.text_area("Bio",value=tu.get("bio",""),key="cfg_b",height=80)
            cs,co=st.columns(2)
            with cs:
                if st.button("Salvar",key="btn_sp",use_container_width=True): # Removed emoji
                    st.session_state.users[email].update({"name":new_n,"area":new_a,"bio":new_b,"scholarship":new_sch,"orcid":new_orcid}) # Changed to scholarship
                    save_db(); st.success("Salvo!") # Removed emoji
            with co:
                if st.button("Sair",key="btn_out",use_container_width=True): # Removed emoji
                    st.session_state.logged_in=False; st.session_state.current_user=None; st.session_state.page="login"; st.rerun()
        with tl:
            for p in sorted(user_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="myp",show_author=False)
            if not user_posts: st.markdown(f'<div class="glass" style="padding:2.5rem;text-align:center;color:var(--t3)">Nenhuma pesquisa ainda.</div>',unsafe_allow_html=True) # Removed emoji
        with ts2:
            for p in sorted(liked_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="mylk",compact=True)
        with ts:
            if saved_arts:
                for idx,a in enumerate(saved_arts):
                    render_article(a,idx=idx+3000,ctx="saved")
                    uid2=re.sub(r'[^a-zA-Z0-9]','',f"rms_{{idx}}")[:20] # Corrected f-string here
                    if st.button("Remover",key=f"rm_sa_{uid2}",use_container_width=True): # Removed emoji
                        st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]
                        save_db(); st.rerun()
            else: st.markdown(f'<div class="glass" style="padding:2.5rem;text-align:center;color:var(--t3)">Nenhum artigo salvo.</div>',unsafe_allow_html=True) # Removed emoji
        with tst:
            if user_posts:
                total_v=sum(p.get("views",0) for p in user_posts)
                avg_l=sum(p["likes"] for p in user_posts)/len(user_posts)
                c1,c2,c3,c4=st.columns(4)
                with c1: st.markdown(f'<div class="mbox"><div class="mval-acc">{{total_likes}}</div><div class="mlbl">Total Curtidas</div></div>',unsafe_allow_html=True) # Corrected f-string here
                with c2: st.markdown(f'<div class="mbox"><div class="mval-teal">{{total_citations}}</div><div class="mlbl">Citações</div></div>',unsafe_allow_html=True) # Corrected f-string here
                with c3: st.markdown(f'<div class="mbox"><div class="mval-pur">{{fmt_num(total_v)}}</div><div class="mlbl">Visualizações</div></div>',unsafe_allow_html=True) # Corrected f-string here
                with c4: st.markdown(f'<div class="mbox"><div class="mval-red">{{round(avg_l,1)}}</div><div class="mlbl">Média Curtidas</div></div>',unsafe_allow_html=True) # Corrected f-string here
                # Posts over time
                by_month=defaultdict(int)
                for p in user_posts:
                    try: by_month[p.get("date","")[:7]]+=1
                    except: pass
                months=sorted(by_month.keys()); counts=[by_month[m] for m in months]
                if len(months)>1:
                    fig=go.Figure(go.Scatter(x=months,y=counts,fill='tozeroy',line=dict(color=PRIMARY_COLOR,width=2),fillcolor=f"rgba(13,127,232,.08)",mode="lines+markers",marker=dict(color=PRIMARY_COLOR,size=7)))
                    fig.update_layout(**{**pc_dark(),'height':180,'title':dict(text="Publicações por mês",font=dict(color=TEXT_COLOR_LIGHT,family="Syne",size=10))})
                    st.markdown('<div class="chart-wrap">',unsafe_allow_html=True)
                    st.plotly_chart(fig,use_container_width=True)
                    st.markdown('</div>',unsafe_allow_html=True)

# ================================================
#  PAGE: FEED (Removed, now repository is main)
# ================================================

# ================================================
#  PAGE: SEARCH (Enhanced & Integrated with Vision IA)
# ================================================
def page_search():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.35rem">Busca Acadêmica Avançada</h1>',unsafe_allow_html=True) # Removed emoji
    st.markdown('<p style="color:var(--t3);font-size:.76rem;margin-bottom:.85rem">Varredura em plataforma, Semantic Scholar e CrossRef com análise temporal e estatística</p>',unsafe_allow_html=True)

    # Image Upload for Vision IA
    st.markdown('<div class="glass" style="padding:1rem; margin-bottom: 1rem;">', unsafe_allow_html=True)
    st.markdown('<h2 style="margin-bottom:.5rem">Análise de Imagem Científica (Visão IA)</h2>', unsafe_allow_html=True)
    img_file = st.file_uploader("Carregar imagem científica", type=["png", "jpg", "jpeg", "webp", "tiff"], key="img_up_search")
    img_bytes = None
    if img_file:
        img_bytes = img_file.read()
        st.image(img_bytes, use_container_width=True)

    api_key = st.session_state.get("anthropic_key", "")
    has_api = api_key.startswith("sk-") if api_key else False

    if img_bytes:
        if has_api:
            if st.button("Analisar Imagem com Claude Vision", key="btn_vision_search", use_container_width=True):
                img_hash = hashlib.md5(img_bytes).hexdigest()
                if img_hash not in st.session_state.image_analysis_cache:
                    with st.spinner("Claude Vision analisando imagem em detalhes..."):
                        ai_text, ai_err = call_claude_analysis(img_bytes, api_key, "image_detail")
                    if ai_err:
                        st.error(f"Erro na análise Claude Vision: {{ai_err}}") # Corrected f-string here
                        st.session_state.image_analysis_cache[img_hash] = {"error": ai_err}
                    elif ai_text:
                        try:
                            clean = ai_text.strip().replace("```json", "").replace("```", "").strip()
                            ai_data = json.loads(clean)
                            st.session_state.image_analysis_cache[img_hash] = ai_data
                        except json.JSONDecodeError:
                            st.error("Erro ao decodificar JSON da Claude Vision. Resposta bruta:")
                            st.code(ai_text)
                            st.session_state.image_analysis_cache[img_hash] = {"raw_response": ai_text}
                else:
                    st.info("Análise da imagem carregada do cache.")
                st.rerun()
        else:
            st.warning("Insira sua chave API do Claude para ativar a análise detalhada de imagens com IA.")

    ai_data = None
    if img_bytes:
        img_hash = hashlib.md5(img_bytes).hexdigest()
        ai_data = st.session_state.image_analysis_cache.get(img_hash)

    if ai_data and not ai_data.get("error") and not ai_data.get("raw_response"):
        st.markdown(f'''<div class="ai-card" style="margin-top:1rem;">
  <div style="font-size:.57rem;color:var(--pur);letter-spacing:.10em;text-transform:uppercase;font-weight:700;margin-bottom:.4rem">Claude Vision Analysis</div>
  <div style="font-family:Syne,sans-serif;font-size:1.05rem;font-weight:800;color:var(--t0);margin-bottom:4px">{{ai_data.get("tipo_imagem","Não identificado")}}</div>
  <div style="color:var(--teal);font-size:.78rem;font-weight:600;margin-bottom:.5rem">{{ai_data.get("area_cientifica","Não especificada")}}</div>
  <div style="background:rgba(255,255,255,.04);border-radius:10px;padding:.7rem .9rem;margin-bottom:.5rem;font-size:.77rem;color:var(--t2);line-height:1.7;border:1px solid rgba(255,255,255,.06)">
    {{ai_data.get("descricao_detalhada","Sem descrição detalhada.")}}
  </div>
  <div style="font-size:.70rem;color:var(--t2);margin-bottom:.35rem">Representação Científica: <strong style="color:var(--t1)">{{ai_data.get("representacao_cientifica","Não especificada.")}}</strong></div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;margin-bottom:.4rem">
    <div style="font-size:.70rem;color:var(--t2)">Técnica: <strong style="color:var(--t1)">{{ai_data.get("tecnica_experimental_ou_metodo","Não informada")}}</strong></div>
    <div style="font-size:.70rem;color:var(--t2)">Qualidade: <strong style="color:var(--acc)">{{ai_data.get("qualidade_visual","—")}}</strong></div>
    <div style="font-size:.70rem;color:var(--t2)">Confiança IA: <strong style="color:var(--teal)">{{ai_data.get("confianca_analise_ia",0)}}%</strong></div>
  </div>
  {{f"<div style='font-size:.70rem;color:var(--t2);margin-bottom:.35rem'>Estruturas: {{', '.join(ai_data.get('elementos_identificados',[]))}}</div>" if ai_data.get("elementos_identificados") else ""}}
  {{f"<div style='background:rgba(54,184,160,.05);border:1px solid rgba(54,184,160,.12);border-radius:8px;padding:.5rem .7rem;font-size:.72rem;color:var(--t2);line-height:1.65'><strong style='color:var(--teal)'>Observações:</strong> {{ai_data.get('observacoes_adicionais','')}}</div>" if ai_data.get("observacoes_adicionais") else ""}}
  {{f"<div style='background:rgba(13,127,232,.05);border:1px solid rgba(13,127,232,.12);border-radius:8px;padding:.5rem .7rem;font-size:.72rem;color:var(--t2);line-height:1.65;margin-top:.5rem'><strong style='color:var(--acc)'>Aprofundamento:</strong> {{ai_data.get('metodologia_sugerida_aprofundamento','')}}</div>" if ai_data.get("metodologia_sugerida_aprofundamento") else ""}}
</div>''', unsafe_allow_html=True) # Corrected f-string here

        termos_busca_ia = ai_data.get("termos_busca_sugeridos", [])
        if termos_busca_ia:
            st.markdown(f'<div style="font-size:.62rem;color:var(--t3);margin:.3rem 0 .5rem">Termos de busca sugeridos pela IA: <em>{{", ".join(termos_busca_ia)}}</em></div>', unsafe_allow_html=True) # Corrected f-string here
            # Automatically populate search query with AI terms
            st.session_state.last_sq = ", ".join(termos_busca_ia)

    st.markdown('</div>', unsafe_allow_html=True) # End of glass card for Vision IA

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<h2 style="margin-bottom:.5rem">Busca Textual</h2>', unsafe_allow_html=True)

    c1,c2,c3=st.columns([4,.8,.8])
    with c1: q=st.text_input("",placeholder="CRISPR · quantum ML · dark matter · neuroplasticidade…",key="sq",label_visibility="collapsed", value=st.session_state.last_sq)
    with c2: search_mode=st.selectbox("",["Tudo","Nebula","Internet"],key="s_mode",label_visibility="collapsed")
    with c3:
        if st.button("Buscar",key="btn_s",use_container_width=True): # Removed emoji
            if q:
                with st.spinner("Varrendo plataforma e bases acadêmicas…"):
                    nr=[p for p in st.session_state.feed_posts if q.lower() in p["title"].lower() or q.lower() in p["abstract"].lower() or any(q.lower() in t.lower() for t in p.get("tags",[]))]
                    # Also scan folder files (keywords)
                    folder_matches=[]
                    for fn,fd in st.session_state.folders.items():
                        if not isinstance(fd,dict): continue
                        for fname,an in fd.get("analyses",{}).items():
                            if any(q.lower() in kw.lower() for kw in an.get("keywords",[])):
                                folder_matches.append({"folder":fn,"file":fname,"analysis":an})
                    sr=search_ss(q,8) if search_mode!="Nebula" else []
                    cr=search_cr(q,4) if search_mode!="Nebula" else []
                    st.session_state.search_results={"nebula":nr,"ss":sr,"cr":cr,"folders":folder_matches}
                    st.session_state.last_sq=q
                    record([q.lower()],.3)
    if st.session_state.get("search_results") and st.session_state.get("last_sq"):
        res=st.session_state.search_results
        neb=res.get("nebula",[]); ss=res.get("ss",[]); cr=res.get("cr",[])
        fldr=res.get("folders",[])
        web=ss+[x for x in cr if not any(x["title"].lower()==s["title"].lower() for s in ss)]
        total=len(neb)+len(web)+len(fldr)
        st.markdown(f'<div style="font-size:.65rem;color:var(--t2);margin-bottom:.8rem">Encontrados: <strong style="color:var(--t0)">{{total}}</strong> resultados · {{len(neb)}} na plataforma · {{len(fldr)}} em pastas · {{len(web)}} na internet</div>',unsafe_allow_html=True) # Corrected f-string here
        # Temporal analysis of results
        # Define all_years here to ensure it's always available for the chart
        years_neb=[p.get("date","")[:4] for p in neb if p.get("date")]
        year_counts_neb=Counter(years_neb)
        web_years=[str(a.get("year","")) for a in web if a.get("year")]
        web_year_counts=Counter(web_years)
        all_years=sorted(list(set(list(year_counts_neb.keys()) + list(web_year_counts.keys()))))

        if len(all_years)>1:
            combined={y:year_counts_neb.get(y,0)+web_year_counts.get(y,0) for y in all_years}
            fig_t=go.Figure(go.Bar(x=list(combined.keys()),y=list(combined.values()),
                                    marker=dict(color=list(range(len(combined))),colorscale=[[0,BG_COLOR_DARK],[1,PRIMARY_COLOR]]),
                                    text=list(combined.values()),textposition="outside",textfont=dict(color=TEXT_COLOR_DARK,size=9)))
            fig_t.update_layout(**{**pc_dark(),'height':160,'title':dict(text="Distribuição temporal dos resultados",font=dict(color=TEXT_COLOR_LIGHT,family="Syne",size=10)),'margin':dict(l=10,r=10,t=32,b=8)}) # Removed emoji
            st.markdown('<div class="chart-wrap">',unsafe_allow_html=True)
            st.plotly_chart(fig_t,use_container_width=True)
            st.markdown('</div>',unsafe_allow_html=True)
        ta,tn,tf_tab,tw=st.tabs([f"  Todos ({{total}})  ",f"  Nebula ({{len(neb)}})  ",f"  Pastas ({{len(fldr)}})  ",f"  Internet ({{len(web)}})  "]) # Corrected f-string here
        with ta:
            if neb:
                st.markdown(f'<div style="font-size:.58rem;color:var(--acc);font-weight:700;margin-bottom:.4rem;letter-spacing:.10em;text-transform:uppercase">● Pesquisas na plataforma</div>',unsafe_allow_html=True)
                for p in sorted(neb,key=lambda x:x.get("citations",0),reverse=True): render_post(p,ctx="srch_all",compact=True)
            if fldr:
                st.markdown(f'<div style="font-size:.58rem;color:var(--orn);font-weight:700;margin:.7rem 0 .4rem;letter-spacing:.10em;text-transform:uppercase">● Encontrado nas suas pastas</div>',unsafe_allow_html=True)
                for fm in fldr[:4]:
                    kws=fm["analysis"].get("keywords",[]); rel=fm["analysis"].get("relevance_score",0)
                    st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:7px"><span> </span><div style="flex:1"><div style="font-family:Syne,sans-serif;font-size:.84rem;font-weight:700;color:var(--t0)">{{fm["file"]}}</div><div style="font-size:.63rem;color:var(--t3)">em: {{fm["folder"]}} · relevância: {{rel}}%</div><div style="margin-top:.25rem">{{tags_html(kws[:5])}}</div></div></div></div>',unsafe_allow_html=True) # Corrected f-string here
            if web:
                st.markdown(f'<div style="font-size:.58rem;color:var(--cya);font-weight:700;margin:.7rem 0 .4rem;letter-spacing:.10em;text-transform:uppercase">● Literatura científica</div>',unsafe_allow_html=True)
                for idx,a in enumerate(web): render_article(a,idx=idx,ctx="all_w")
        with tn:
            if neb:
                # Statistical analysis
                avg_likes=sum(p["likes"] for p in neb)/len(neb); avg_cit=sum(p.get("citations",0) for p in neb)/len(neb)
                c1s,c2s,c3s=st.columns(3)
                with c1s: st.markdown(f'<div class="mbox"><div class="mval-acc">{{len(neb)}}</div><div class="mlbl">Resultados</div></div>',unsafe_allow_html=True) # Corrected f-string here
                with c2s: st.markdown(f'<div class="mbox"><div class="mval-teal">{{round(avg_likes,1)}}</div><div class="mlbl">Média Curtidas</div></div>',unsafe_allow_html=True) # Corrected f-string here
                with c3s: st.markdown(f'<div class="mbox"><div class="mval-pur">{{round(avg_cit,1)}}</div><div class="mlbl">Média Citações</div></div>',unsafe_allow_html=True) # Corrected f-string here
                st.markdown('<div style="font-size:.62rem;color:var(--t3);margin:.5rem 0">Ordenado por relevância + citações:</div>',unsafe_allow_html=True)
                for p in sorted(neb,key=lambda x:x.get("citations",0)+x["likes"]*0.5,reverse=True): render_post(p,ctx="srch_neb",compact=True)
            else: st.info("Nenhuma pesquisa na plataforma.")
        with tf_tab:
            if fldr:
                for fm in fldr:
                    kws=fm["analysis"].get("keywords",[]); topics=fm["analysis"].get("topics",{})
                    st.markdown(f'<div class="repo-card"><div style="font-size:.58rem;color:var(--orn);font-weight:700;margin-bottom:.3rem;text-transform:uppercase;letter-spacing:.08em">📁 {{fm["folder"]}}</div><div style="font-family:Syne,sans-serif;font-size:.85rem;font-weight:700;color:var(--t0);margin-bottom:.2rem">{{fm["file"]}}</div><div style="margin:.3rem 0">{{tags_html(kws[:8])}}</div><div style="font-size:.65rem;color:var(--t3)">Temas: {{", ".join(list(topics.keys())[:3])}}</div></div>',unsafe_allow_html=True) # Corrected f-string here
            else: st.markdown('<div style="color:var(--t3);padding:1rem">Nenhum arquivo em pastas corresponde à busca.</div>',unsafe_allow_html=True)
        with tw:
            if web:
                # Citation stats
                total_cit=sum(a.get("citations",0) for a in web); max_cit=max((a.get("citations",0) for a in web),default=0)
                c1w,c2w,c3w=st.columns(3)
                with c1w: st.markdown(f'<div class="mbox"><div class="mval-acc">{{len(web)}}</div><div class="mlbl">Artigos</div></div>',unsafe_allow_html=True) # Corrected f-string here
                with c2w: st.markdown(f'<div class="mbox"><div class="mval-teal">{{total_cit}}</div><div class="mlbl">Total Citações</div></div>',unsafe_allow_html=True) # Corrected f-string here
                with c3w: st.markdown(f'<div class="mbox"><div class="mval-pur">{{max_cit}}</div><div class="mlbl">Máx. Citações</div></div>',unsafe_allow_html=True) # Corrected f-string here
                for idx,a in enumerate(sorted(web,key=lambda x:x.get("citations",0),reverse=True)): render_article(a,idx=idx,ctx="web_t")
            else: st.info("Nenhum artigo encontrado. Verifique conectividade.")
    st.markdown('</div>',unsafe_allow_html=True)

# ================================================
#  PAGE: KNOWLEDGE (Connections)
# ================================================
def page_knowledge():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.4rem">Rede de Conexões Científicas</h1>',unsafe_allow_html=True) # Removed emoji
    st.markdown('<p style="color:var(--t3);font-size:.76rem;margin-bottom:.9rem">Mapa de colaborações, interesses e conexões temáticas na plataforma</p>',unsafe_allow_html=True)
    email=st.session_state.current_user
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    api_key=st.session_state.get("anthropic_key","")

    def get_user_tags(ue):
        ud=users.get(ue,{}); tags=set(area_tags(ud.get("area","")))
        for p in st.session_state.feed_posts:
            if p.get("author_email")==ue: tags.update(t.lower() for t in p.get("tags",[]))
        return tags

    def jaccard(s1,s2):
        if not s1 and not s2: return 0
        inter=len(s1&s2); union=len(s1|s2)
        return inter/union if union>0 else 0

    rlist=list(users.keys()); n=len(rlist)
    rtags={ue:get_user_tags(ue) for ue in rlist}

    # Build connection matrix
    edges=[]
    for i in range(n):
        for j in range(i+1,n):
            e1,e2=rlist[i],rlist[j]
            common=list(rtags[e1]&rtags[e2])
            jac=jaccard(rtags[e1],rtags[e2])
            is_fol=e2 in st.session_state.followed or e1 in st.session_state.followed
            strength=len(common)+(3 if is_fol else 0)
            if common or is_fol: edges.append((e1,e2,common[:6],round(jac,2),strength))

    # 3D graph
    pos={}
    for idx,ue in enumerate(rlist):
        angle=2*3.14159*idx/max(n,1); rd=0.35+0.06*((hash(ue)%5)/4)
        pos[ue]={"x":0.5+rd*np.cos(angle),"y":0.5+rd*np.sin(angle),"z":0.5+0.14*((idx%4)/3-.35)}

    fig=go.Figure()
    for e1,e2,common,jac,strength in edges:
        p1=pos[e1]; p2=pos[e2]; alpha=min(0.5,0.06+strength*0.07)
        fig.add_trace(go.Scatter3d(x=[p1["x"],p2["x"],None],y=[p1["y"],p2["y"],None],z=[p1["z"],p2["z"],None],
                                    mode="lines",line=dict(color=f"rgba(13,127,232,{alpha:.2f})",width=min(4,1+strength//2)),
                                    hoverinfo="none",showlegend=False))
    ncolors=[PRIMARY_COLOR if ue==email else (SECONDARY_COLOR if ue in st.session_state.followed else "#38C8F0") for ue in rlist]
    nsizes=[22 if ue==email else (16 if ue in st.session_state.followed else 10) for ue in rlist]
    fig.add_trace(go.Scatter3d(
        x=[pos[ue]["x"] for ue in rlist],y=[pos[ue]["y"] for ue in rlist],z=[pos[ue]["z"] for ue in rlist],
        mode="markers+text",marker=dict(size=nsizes,color=ncolors,opacity=.9,line=dict(color="rgba(255,255,255,.08)",width=1.5)),
        text=[users.get(ue,{}).get("name","?").split()[0] for ue in rlist],textposition="top center",
        textfont=dict(color=TEXT_COLOR_DARK,size=9,family="DM Sans"),
        hovertemplate=[f"<b>{{users.get(ue,{{}}).get('name','?')}}</b><br>{{users.get(ue,{{}}).get('area','')}}<br>Tags: {{len(rtags.get(ue,set()))}}<extra></extra>" for ue in rlist], # Corrected f-string here
        showlegend=False))
    fig.update_layout(height=420,
                      scene=dict(xaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),
                                 yaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),
                                 zaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),bgcolor="rgba(0,0,0,0)"),
                      paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig,use_container_width=True)

    c1,c2,c3,c4=st.columns(4)
    with c1: st.markdown(f'<div class="mbox"><div class="mval-acc">{{len(rlist)}}</div><div class="mlbl">Pesquisadores</div></div>',unsafe_allow_html=True) # Corrected f-string here
    with c2: st.markdown(f'<div class="mbox"><div class="mval-teal">{{len(edges)}}</div><div class="mlbl">Conexões</div></div>',unsafe_allow_html=True) # Corrected f-string here
    with c3: st.markdown(f'<div class="mbox"><div class="mval-pur">{{len(st.session_state.followed)}}</div><div class="mlbl">Seguindo</div></div>',unsafe_allow_html=True) # Corrected f-string here
    with c4:
        my_tags=rtags.get(email,set())
        potential=sum(1 for ue in rlist if ue!=email and len(my_tags&rtags.get(ue,set()))>0 and ue not in st.session_state.followed)
        st.markdown(f'<div class="mbox"><div class="mval-red">{{potential}}</div><div class="mlbl">Potencial Colabs</div></div>',unsafe_allow_html=True) # Corrected f-string here
    st.markdown("<hr>",unsafe_allow_html=True)

    tm,tsugg,tmat,tmy,tall=st.tabs(["  Conexões  ","  Sugestões  ","  Matriz  ","  Minhas  ","  Todos  "]) # Removed emojis

    with tm:
        sq_conn=st.text_input("",placeholder="Filtrar por tema…",key="conn_sq",label_visibility="collapsed")
        for e1,e2,common,jac,strength in sorted(edges,key=lambda x:-x[4])[:25]:
            n1=users.get(e1,{}); n2=users.get(e2,{})
            if sq_conn and not any(sq_conn.lower() in t.lower() for t in common): continue
            jac_color=SECONDARY_COLOR if jac>0.3 else (PRIMARY_COLOR if jac>0.1 else TEXT_COLOR_DARK)
            ts=tags_html(common[:5]) if common else f'<span style="color:var(--t3);font-size:.63rem">via seguimento</span>'
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:7px;flex-wrap:wrap">'
                        f'{{avh(ini(n1.get("name","?")),28,ugrad(e1))}}' # Corrected f-string here
                        f'<span style="font-size:.78rem;font-weight:700;font-family:Syne,sans-serif;color:var(--t0)">{{n1.get("name","?")}}</span>' # Corrected f-string here
                        f'<span style="color:var(--t3);font-size:.7rem">↔</span>'
                        f'<span style="font-size:.78rem;font-weight:700;font-family:Syne,sans-serif;color:var(--t0)">{{n2.get("name","?")}}</span>' # Corrected f-string here
                        f'{{avh(ini(n2.get("name","?")),28,ugrad(e2))}}' # Corrected f-string here
                        f'<div style="flex:1">{{ts}}</div>' # Corrected f-string here
                        f'<span style="font-size:.62rem;font-weight:700;color:{jac_color}">Jaccard {{jac:.2f}}</span>' # Corrected f-string here
                        f'</div></div>',unsafe_allow_html=True)

    with tsugg:
        st.markdown(f'<div class="api-banner"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.88rem;color:var(--pur);margin-bottom:.25rem"> Sugestões de Colaboração Científica</div><div style="font-size:.73rem;color:var(--t2)">Análise de sobreposição temática, histórico de pesquisa e potencial de colaboração</div></div>',unsafe_allow_html=True) # Removed emoji
        my_tags=rtags.get(email,set())
        my_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==email]
        my_kws=set(kw for p in my_posts for kw in p.get("keywords_extracted",[]))

        suggestions=[]
        for ue,ud in users.items():
            if ue==email: continue
            their_tags=rtags.get(ue,set())
            common_tags=my_tags&their_tags
            their_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==ue]
            their_kws=set(kw for p in their_posts for kw in p.get("keywords_extracted",[]))
            common_kws=my_kws&their_kws
            jac_score=jaccard(my_tags,their_tags)
            topic_overlap=len(common_tags); kw_overlap=len(common_kws)
            collab_score=min(100,int(jac_score*40+topic_overlap*8+kw_overlap*4+(5 if ue in st.session_state.followed else 0)))
            suggestions.append({"email":ue,"ud":ud,"common_tags":list(common_tags)[:6],"common_kws":list(common_kws)[:5],"collab_score":collab_score,"jac":round(jac_score,3),"n_posts":len(their_posts)})

        suggestions.sort(key=lambda x:-x["collab_score"])
        for sug in suggestions[:8]:
            if sug["collab_score"]==0: continue
            sue=sug["email"]; sud=sug["ud"]; rn=sud.get("name","?"); rg=ugrad(sue)
            sc=sug["collab_score"]; is_fol=sue in st.session_state.followed
            sc_c=SECONDARY_COLOR if sc>=70 else (PRIMARY_COLOR if sc>=40 else WARNING_COLOR)
            reason_parts=[]
            if sug["common_tags"]: reason_parts.append(f"{{len(sug['common_tags'])}} áreas em comum") # Corrected f-string here
            if sug["common_kws"]: reason_parts.append(f"{{len(sug['common_kws'])}} palavras-chave sobrepostas") # Corrected f-string here
            if sug["jac"]>0.2: reason_parts.append(f"alta similaridade temática ({{sug['jac']:.0%}})") # Corrected f-string here
            reason="; ".join(reason_parts) if reason_parts else "Áreas relacionadas"
            st.markdown(f'''<div class="conn-card">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:.5rem">
    {{avh(ini(rn),38,rg)}}
    <div style="flex:1">
      <div style="font-family:Syne,sans-serif;font-weight:700;font-size:.88rem;color:var(--t0)">{{rn}} {{ "✓" if sud.get("verified") else ""}}</div>
      <div style="font-size:.64rem;color:var(--t3)">{{sud.get("area","")}} · {{sud.get("scholarship","")}} · {{sug["n_posts"]}} pesquisas</div>
    </div>
    <div style="text-align:center;background:rgba(0,0,0,.25);border-radius:10px;padding:.38rem .65rem;flex-shrink:0">
      <div style="font-family:Syne,sans-serif;font-size:1.15rem;font-weight:900;color:{sc_c}">{{sc}}</div>
      <div style="font-size:.5rem;color:var(--t3);text-transform:uppercase;letter-spacing:.06em">score colab.</div>
    </div>
  </div>
  <div style="background:rgba(255,255,255,.03);border-radius:9px;padding:.5rem .75rem;font-size:.74rem;color:var(--t2);margin-bottom:.42rem;border:1px solid rgba(255,255,255,.06)">
    {{reason}}
  </div>
  <div style="margin-bottom:.3rem">{{tags_html(sug["common_tags"])}}</div>
</div>''',unsafe_allow_html=True) # Corrected f-string here
            cf2,cp2,cc2=st.columns(3)
            with cf2:
                if st.button("Seguindo" if is_fol else "Seguir",key=f"sugg_f_{sue}",use_container_width=True): # Removed emoji
                    if not is_fol: st.session_state.followed.append(sue); sud["followers"]=sud.get("followers",0)+1
                    else: st.session_state.followed.remove(sue); sud["followers"]=max(0,sud.get("followers",0)-1)
                    save_db(); st.rerun()
            with cp2:
                if st.button("Perfil",key=f"sugg_p_{sue}",use_container_width=True): st.session_state.profile_view=sue; st.rerun() # Removed emoji
            with cc2:
                if st.button("Chat",key=f"sugg_c_{sue}",use_container_width=True): # Removed emoji
                    st.session_state.chat_messages.setdefault(sue,[]); st.session_state.active_chat=sue; st.session_state.page="chat"; st.rerun()

    with tmat:
        st.markdown('<div style="font-size:.62rem;color:var(--t3);margin-bottom:.6rem">Matriz de similaridade Jaccard entre todos pesquisadores</div>',unsafe_allow_html=True)
        names=[users.get(ue,{}).get("name","?").split()[0] for ue in rlist]
        matrix=[[round(jaccard(rtags[rlist[i]],rtags[rlist[j]]),2) for j in range(n)] for i in range(n)]
        fig_m=go.Figure(go.Heatmap(z=matrix,x=names,y=names,
                                    colorscale=[[0,BG_COLOR_DARK],[0.3,BG_COLOR_MEDIUM],[0.7,PRIMARY_COLOR],[1,SECONDARY_COLOR]],
                                    zmin=0,zmax=1,text=[[f"{{v:.2f}}" for v in row] for row in matrix], # Corrected f-string here
                                    texttemplate="%{{text}}",textfont=dict(size=8,color="rgba(255,255,255,.5)"))) # Corrected f-string here
        fig_m.update_layout(height=350,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                             font=dict(color=TEXT_COLOR_DARK,size=9),margin=dict(l=80,r=10,t=10,b=80),
                             xaxis=dict(tickfont=dict(size=8)),yaxis=dict(tickfont=dict(size=8)))
        st.markdown('<div class="chart-wrap">',unsafe_allow_html=True)
        st.plotly_chart(fig_m,use_container_width=True)
        st.markdown('</div>',unsafe_allow_html=True)

        # Topic overlap chart
        all_areas=Counter(ud.get("area","") for ud in users.values() if ud.get("area"))
        if all_areas:
            fig_a=go.Figure(go.Bar(x=list(all_areas.keys())[:8],y=list(all_areas.values())[:8],
                                    marker=dict(color=[PRIMARY_COLOR, SECONDARY_COLOR, TERTIARY_COLOR, WARNING_COLOR, ERROR_COLOR, PRIMARY_COLOR, SECONDARY_COLOR, TERTIARY_COLOR]),text=list(all_areas.values())[:8],textposition="outside",textfont=dict(color=TEXT_COLOR_DARK,size=9)))
            fig_a.update_layout(**{**pc_dark(),'height':200,'title':dict(text="Pesquisadores por área",font=dict(color=TEXT_COLOR_LIGHT,family="Syne",size=10))})
            st.markdown('<div class="chart-wrap">',unsafe_allow_html=True)
            st.plotly_chart(fig_a,use_container_width=True)
            st.markdown('</div>',unsafe_allow_html=True)

    with tmy:
        mc=[(e1,e2,c,j,s) for e1,e2,c,j,s in edges if e1==email or e2==email]
        if not mc: st.info("Siga pesquisadores e publique pesquisas.")
        for e1,e2,common,jac,strength in sorted(mc,key=lambda x:-x[4]):
            oth=e2 if e1==email else e1; od=users.get(oth,{}); og=ugrad(oth)
            jac_c=SECONDARY_COLOR if jac>0.3 else PRIMARY_COLOR
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:9px;flex-wrap:wrap">{{avh(ini(od.get("name","?")),34,og)}}<div style="flex:1"><div style="font-weight:700;font-size:.82rem;font-family:Syne,sans-serif;color:var(--t0)">{{od.get("name","?")}}</div><div style="font-size:.65rem;color:var(--t3)">{{od.get("area","")}} · {{od.get("scholarship","")}}</div><div style="margin-top:.25rem">{{tags_html(common[:4])}}</div></div><span style="font-size:.62rem;color:{jac_c};font-weight:700">Jac {{jac:.2f}}</span></div></div>',unsafe_allow_html=True) # Corrected f-string here
            cv2,cm2,_=st.columns([1,1,4])
            with cv2:
                if st.button("Ver",key=f"kv_{oth}",use_container_width=True): st.session_state.profile_view=oth; st.rerun() # Removed emoji
            with cm2:
                if st.button("Chat",key=f"kc_{oth}",use_container_width=True): # Removed emoji
                    st.session_state.chat_messages.setdefault(oth,[]); st.session_state.active_chat=oth; st.session_state.page="chat"; st.rerun()

    with tall:
        sq2=st.text_input("",placeholder="Buscar pesquisador ou área…",key="all_s",label_visibility="collapsed") # Removed emoji
        for ue,ud in users.items():
            if ue==email: continue
            rn=ud.get("name","?"); ua=ud.get("area","")
            if sq2 and sq2.lower() not in rn.lower() and sq2.lower() not in ua.lower(): continue
            is_fol=ue in st.session_state.followed; rg=ugrad(ue)
            common_t=rtags.get(email,set())&rtags.get(ue,set()); jac_s=jaccard(rtags.get(email,set()),rtags.get(ue,set()))
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:9px">{{avh(ini(rn),34,rg)}}<div style="flex:1"><div style="font-size:.82rem;font-weight:700;font-family:Syne,sans-serif;color:var(--t0)">{{rn}}</div><div style="font-size:.63rem;color:var(--t3)">{{ua}} · {{ud.get("scholarship","")}}</div>{{f"<div style='margin-top:.2rem'>{{tags_html(list(common_t)[:3])}}</div>" if common_t else ""}}</div><span style="font-size:.60rem;color:{SECONDARY_COLOR if jac_s>0.2 else TEXT_COLOR_DARK};font-weight:600">Sim. {{jac_s:.0%}}</span></div></div>',unsafe_allow_html=True) # Corrected f-string here
            ca2,cb2,cc2=st.columns(3)
            with ca2:
                if st.button("Perfil",key=f"av_{ue}",use_container_width=True): st.session_state.profile_view=ue; st.rerun() # Removed emoji
            with cb2:
                if st.button("Seguir" if is_fol else "Seguir",key=f"af_{ue}",use_container_width=True): # Removed emoji
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"]=max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                    save_db(); st.rerun()
            with cc2:
                if st.button("Chat",key=f"ac_{ue}",use_container_width=True): # Removed emoji
                    st.session_state.chat_messages.setdefault(ue,[]); st.session_state.active_chat=ue; st.session_state.page="chat"; st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)

# ================================================
#  PAGE: REPOSITORY (Enhanced as main page)
# ================================================
def page_repository():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.35rem">Repositório de Pesquisa</h1>',unsafe_allow_html=True) # Removed emoji
    st.markdown('<p style="color:var(--t3);font-size:.76rem;margin-bottom:.9rem">Gerencie, analise e conecte seus arquivos científicos</p>',unsafe_allow_html=True)
    email=st.session_state.current_user; u=guser(); ra=u.get("area","")
    api_key=st.session_state.get("anthropic_key","")

    # Stats bar
    tot_folders=len(st.session_state.folders)
    tot_files=sum(len(fd.get("files",[]) if isinstance(fd,dict) else fd) for fd in st.session_state.folders.values())
    all_an={f:an for fd in st.session_state.folders.values() if isinstance(fd,dict) for f,an in fd.get("analyses",{}).items()}
    all_kw=[kw for an in all_an.values() for kw in an.get("keywords",[])]
    c1s,c2s,c3s,c4s=st.columns(4)
    with c1s: st.markdown(f'<div class="mbox"><div class="mval-acc">{{tot_folders}}</div><div class="mlbl">Repositórios</div></div>',unsafe_allow_html=True) # Corrected f-string here
    with c2s: st.markdown(f'<div class="mbox"><div class="mval-teal">{{tot_files}}</div><div class="mlbl">Arquivos</div></div>',unsafe_allow_html=True) # Corrected f-string here
    with c3s: st.markdown(f'<div class="mbox"><div class="mval-pur">{{len(all_an)}}</div><div class="mlbl">Analisados</div></div>',unsafe_allow_html=True) # Corrected f-string here
    with c4s: st.markdown(f'<div class="mbox"><div class="mval-red">{{len(set(all_kw[:200]))}}</div><div class="mlbl">Keywords</div></div>',unsafe_allow_html=True) # Corrected f-string here
    st.markdown("<hr>",unsafe_allow_html=True)

    # Create folder
    with st.expander("Novo Repositório"): # Removed emoji
        c1,c2,c3=st.columns([2,1.5,1])
        with c1: nfn=st.text_input("Nome",placeholder="Ex: Genômica Comparativa",key="nf_n")
        with c2: nfd=st.text_input("Descrição",key="nf_d",placeholder="Objetivo desta pasta…")
        with c3: nft=st.selectbox("Tipo",["Projeto","Artigo","Dataset","Revisão","Outro"],key="nf_t")
        if st.button("Criar Repositório",key="btn_nf",use_container_width=True): # Removed emoji
            if nfn.strip():
                if nfn not in st.session_state.folders:
                    st.session_state.folders[nfn]={"desc":nfd,"type":nft,"files":[],"notes":"","analyses":{},"created":datetime.now().strftime("%Y-%m-%d"),"tags":[]}
                    save_db(); st.success(f"Repositório '{{nfn}}' criado!") # Corrected f-string here
                    st.rerun()
                else: st.warning("Já existe.")
            else: st.warning("Digite um nome.")

    if not st.session_state.folders:
        st.markdown(f'<div class="glass" style="text-align:center;padding:4rem"><div style="font-size:2.2rem;opacity:.2;margin-bottom:.7rem"> </div><div style="color:var(--t3)">Nenhum repositório. Crie o primeiro!</div></div>',unsafe_allow_html=True) # Removed emoji
        st.markdown('</div>',unsafe_allow_html=True); return

    # Global repository search (Enhanced)
    st.markdown('<h2 style="margin-top:1.5rem; margin-bottom:.5rem">Busca Detalhada no Repositório</h2>', unsafe_allow_html=True)

    col_search1, col_search2, col_search3 = st.columns([3, 2, 1])
    with col_search1:
        rep_sq = st.text_input("Termo de Busca", placeholder="Buscar por título, conteúdo, tags...", key="rep_sq")
    with col_search2:
        rep_filter_type = st.multiselect("Filtrar por Tipo", ["Projeto", "Artigo", "Dataset", "Revisão", "Outro"], key="rep_filter_type")
    with col_search3:
        rep_min_relevance = st.slider("Relevância Mínima (%)", 0, 100, 0, key="rep_min_relevance")

    filtered_folders = {}
    for fn, fd in st.session_state.folders.items():
        if not isinstance(fd, dict):
            fd = {"files": fd if isinstance(fd, list) else [], "desc": "", "notes": "", "analyses": {}, "created": "", "tags": [], "type": "Projeto"}
            st.session_state.folders[fn] = fd

        files = fd.get("files", [])
        analyses = fd.get("analyses", {})

        # Apply type filter
        if rep_filter_type and fd.get("type") not in rep_filter_type:
            continue

        # Apply search query filter
        if rep_sq:
            kw_match = any(rep_sq.lower() in kw.lower() for an in analyses.values() for kw in an.get("keywords", []))
            file_match = any(rep_sq.lower() in f.lower() for f in files)
            title_match = rep_sq.lower() in fn.lower() or rep_sq.lower() in fd.get("desc", "").lower()

            # Check content of analyzed files
            content_match = False
            for an in analyses.values():
                if rep_sq.lower() in an.get("summary", "").lower():
                    content_match = True
                    break

            if not (kw_match or file_match or title_match or content_match):
                continue

        # Apply relevance filter
        has_relevant_file = False
        if analyses:
            for an in analyses.values():
                if an.get("relevance_score", 0) >= rep_min_relevance:
                    has_relevant_file = True
                    break

        if rep_min_relevance > 0 and not has_relevant_file:
            continue

        filtered_folders[fn] = fd

    if not filtered_folders:
        st.markdown('<div class="glass" style="text-align:center;padding:2rem;color:var(--t3)">Nenhum repositório corresponde aos critérios de busca.</div>', unsafe_allow_html=True)
    else:
        for fn, fd in filtered_folders.items():
            files = fd.get("files", []); analyses = fd.get("analyses", {})
            created = fd.get("created", ""); ftype_badge = fd.get("type", "Projeto")
            badge_map = {"Projeto": "badge-acc", "Artigo": "badge-teal", "Dataset": "badge-pur", "Revisão": "badge-orn", "Outro": "badge-red"}
            badge_cls = badge_map.get(ftype_badge, "badge-acc")
            analyzed_count = len(analyses)

            with st.expander(f"📁 {{fn}} — {{len(files)}} arq. · {{analyzed_count}} analisados"): # Corrected f-string here
                st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:.6rem"><span class="{badge_cls}">{{ftype_badge}}</span><span style="font-size:.65rem;color:var(--t3)">{{fd.get("desc","")}}</span><span style="font-size:.62rem;color:var(--t4);margin-left:auto">Criado: {{created}}</span></div>',unsafe_allow_html=True) # Corrected f-string here

                # Upload
                up=st.file_uploader("Carregar arquivos",type=None,key=f"up_{fn}",label_visibility="collapsed",accept_multiple_files=True) # Removed emoji
                if up:
                    for uf in up:
                        if uf.name not in files: files.append(uf.name)
                        if fn not in st.session_state.folder_files_bytes: st.session_state.folder_files_bytes[fn]={}
                        uf.seek(0); st.session_state.folder_files_bytes[fn][uf.name]=uf.read()
                    fd["files"]=files; save_db(); st.success(f" {{len(up)}} arquivo(s) adicionado(s)!") # Corrected f-string here
                    st.rerun()
                # File list
                if files:
                    for f in files:
                        ft=ftype(f); ha=f in analyses
                        icon={"PDF":" ","Word":" ","Planilha":" ","Dados":" ","Código":" ","Imagem":" ","Markdown":" ","Notebook":" "}.get(ft," ") # Removed emojis
                        an_badge=f'<span class="badge-teal" style="font-size:.55rem">analisado</span>' if ha else "" # Removed emoji
                        rel_score=analyses[f].get("relevance_score",0) if ha else ""
                        rel_bar=prog_bar(rel_score,SECONDARY_COLOR) if ha else ""
                        rm_uid=re.sub(r'[^a-zA-Z0-9]','',f"rmf_{{fn}}_{{f}}")[:28] # Corrected f-string here
                        st.markdown(f'<div style="display:flex;align-items:center;gap:7px;padding:.38rem 0;border-bottom:1px solid rgba(255,255,255,.04)"><span>{{icon}}</span><div style="flex:1"><div style="font-size:.74rem;color:var(--t1);font-weight:500">{{f}} {{an_badge}}</div>{{rel_bar}}</div></div>',unsafe_allow_html=True) # Corrected f-string here

                # Actions
                ca2,cb2,cc2,cd2=st.columns(4)
                with ca2:
                    if st.button("Analisar tudo",key=f"an_{fn}",use_container_width=True): # Removed emoji
                        if files:
                            pb=st.progress(0,"Iniciando análise…")
                            fb=st.session_state.folder_files_bytes.get(fn,{})
                            for fi,f in enumerate(files):
                                pb.progress((fi+1)/len(files),f"Analisando: {{f[:25]}}…") # Corrected f-string here
                                fbytes=fb.get(f,b""); ft2=ftype(f)
                                analyses[f]=_analyze_doc(f,fbytes,ft2,ra)
                            fd["analyses"]=analyses; save_db(); pb.empty(); st.success("Análise concluída!") # Removed emoji
                            st.rerun()
                        else: st.warning("Adicione arquivos primeiro.")
                with cb2:
                    if api_key.startswith("sk-") if api_key else False:
                        if st.button("Claude IA",key=f"ai_{fn}",use_container_width=True): # Removed emoji
                            # Quick summary of folder content
                            all_kws_folder=list({kw for an in analyses.values() for kw in an.get("keywords",[])})[:20]
                            if all_kws_folder:
                                content=f"Pasta: {fn}\nDescrição: {fd.get('desc','')}\nKeywords: {', '.join(all_kws_folder)}\nArquivos: {', '.join(files)}"
                                with st.spinner("Claude analisando pasta…"):
                                    result,err=call_claude_analysis(content,api_key,"research")
                                if result: st.session_state.deep_analysis_cache[f"folder_{fn}"]=result; st.rerun()
                                elif err: st.error(err)
                with cc2:
                    if st.button("Exportar",key=f"ex_{fn}",use_container_width=True): # Removed emoji
                        if analyses:
                            export_data={"repository":fn,"files":files,"analyses":{f:{k:v for k,v in an.items() if k!="topics"} for f,an in analyses.items()}}
                            st.download_button("Baixar JSON",json.dumps(export_data,ensure_ascii=False,indent=2),file_name=f"{{fn}}_analysis.json",mime="application/json",key=f"dl_{fn}") # Corrected f-string here
                with cd2:
                    if st.button("Excluir",key=f"df_{fn}",use_container_width=True): # Removed emoji
                        del st.session_state.folders[fn]; save_db(); st.rerun()

                # Claude AI folder analysis result
                folder_ai=st.session_state.deep_analysis_cache.get(f"folder_{fn}")
                if folder_ai:
                    st.markdown(f'<div class="pbox-pur"><div style="font-size:.62rem;color:#B98FE8;font-weight:700;margin-bottom:.4rem"> Claude IA desta pasta</div>' # Removed emoji
                                f'<div style="font-size:.75rem;color:var(--t2);line-height:1.7;margin-bottom:.4rem">{{folder_ai.get("resumo_executivo","")}}</div>' # Corrected f-string here
                                f'{{"".join(f"<div style=\"font-size:.71rem;color:var(--t2);margin-bottom:.18rem\">→ {{m}}</div>" for m in folder_ai.get("pontos_melhoria",[]))}}' # Corrected f-string here
                                f'</div>',unsafe_allow_html=True)

                # File analyses
                if analyses:
                    st.markdown('<div class="dtxt">Análises de arquivos</div>',unsafe_allow_html=True)
                    for f,an in analyses.items():
                        with st.expander(f" {{f}}"): # Corrected f-string here
                            kws=an.get("keywords",[]); topics=an.get("topics",{}); rel=an.get("relevance_score",0); wq=an.get("writing_quality",0)
                            rc=SECONDARY_COLOR if rel>=70 else (WARNING_COLOR if rel>=45 else ERROR_COLOR)
                            st.markdown(f'<div class="abox"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.86rem;margin-bottom:.28rem">{{f}}</div>' # Corrected f-string here
                                        f'<div style="font-size:.74rem;color:var(--t2);margin-bottom:.45rem">{{an.get("summary","")}}</div>' # Corrected f-string here
                                        f'<div style="display:flex;gap:1.4rem;margin-top:.4rem">'
                                        f'<div style="text-align:center"><div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:900;color:{rc}">{{rel}}%</div><div class="mlbl">Relevância</div></div>' # Corrected f-string here
                                        f'<div style="text-align:center"><div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:900;color:var(--cya)}">{{wq}}%</div><div class="mlbl">Qualidade</div></div>' # Corrected f-string here
                                        f'<div style="text-align:center"><div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:900;color:var(--orn)}">{{an.get("word_count",0)}}</div><div class="mlbl">Palavras</div></div>' # Corrected f-string here
                                        f'<div style="text-align:center"><div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:900;color:var(--pur)}">{{an.get("reading_time",0)}}min</div><div class="mlbl">Leitura</div></div>' # Corrected f-string here
                                        f'</div></div>',unsafe_allow_html=True)
                            if kws: st.markdown(tags_html(kws[:18]),unsafe_allow_html=True)
                            if topics:
                                col1t,col2t=st.columns(2)
                                with col1t:
                                    fig2=go.Figure(go.Pie(labels=list(topics.keys()),values=list(topics.values()),hole=0.5,marker=dict(colors=[PRIMARY_COLOR, SECONDARY_COLOR, TERTIARY_COLOR, WARNING_COLOR, ERROR_COLOR],line=dict(color=[BG_COLOR_DARK]*15,width=2)),textfont=dict(color="white",size=7)))
                                    fig2.update_layout(height=200,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(font=dict(color=TEXT_COLOR_DARK,size=7)),margin=dict(l=0,r=0,t=8,b=0))
                                    st.markdown('<div class="chart-wrap">',unsafe_allow_html=True)
                                    st.plotly_chart(fig2,use_container_width=True)
                                    st.markdown('</div>',unsafe_allow_html=True)
                                with col2t:
                                    # Improvements list
                                    imps=an.get("improvements",[])
                                    if imps:
                                        st.markdown(f'<div class="pbox-orn"><div style="font-size:.60rem;color:var(--orn);font-weight:700;margin-bottom:.3rem"> Melhorias</div>{{"".join(f"<div style=\"font-size:.70rem;color:var(--t2);margin-bottom:.15rem\">→ {{imp}}</div>" for imp in imps)}}</div>',unsafe_allow_html=True) # Corrected f-string here
                                    strs=an.get("strengths",[])
                                    if strs:
                                        st.markdown(f'<div class="pbox-teal"><div style="font-size:.60rem;color:var(--teal);font-weight:700;margin-bottom:.3rem"> Pontos fortes</div>{{"".join(f"<div style=\"font-size:.70rem;color:var(--t2);margin-bottom:.15rem\">✓ {{s}}</div>" for s in strs)}}</div>',unsafe_allow_html=True) # Corrected f-string here

    st.markdown('</div>',unsafe_allow_html=True)

def _analyze_doc(fname,fbytes,ftype_str,area=""):
    r={"file":fname,"type":ftype_str,"keywords":[],"topics":{},"relevance_score":0,"summary":"",
       "strengths":[],"improvements":[],"writing_quality":0,"reading_time":0,"word_count":0}
    text=""
    if ftype_str=="PDF" and fbytes: text=extract_pdf(fbytes)
    elif fbytes:
        try: text=fbytes.decode("utf-8",errors="ignore")[:40000]
        except: pass
    if text:
        r["keywords"]=kw_extract(text,25); r["topics"]=topic_dist(r["keywords"])
        words=len(text.split()); r["word_count"]=words; r["reading_time"]=max(1,round(words/200))
        r["writing_quality"]=min(100,50+(15 if len(r["keywords"])>15 else 0)+(15 if words>1000 else 0)+(10 if r["reading_time"]>3 else 0)+(10 if len(set(r["keywords"]))>10 else 0))
        if area:
            aw=area.lower().split(); rel=sum(1 for w in aw if any(w in kw for kw in r["keywords"]))
            r["relevance_score"]=min(100,rel*15+45)
        else: r["relevance_score"]=60
        r["strengths"]=[f"Vocabulário técnico rico ({{len(r['keywords'])}} termos-chave)"] if len(r["keywords"])>15 else [] # Corrected f-string here
        if words>2000: r["strengths"].append("Conteúdo extenso e detalhado")
        r["improvements"]=["Expandir o conteúdo com mais detalhes"] if words<500 else []
        if len(r["keywords"])<8: r["improvements"].append("Enriquecer com mais terminologia técnica")
        if r.get("relevance_score",0)<50: r["improvements"].append("Melhorar alinhamento com a área de pesquisa")
        r["summary"]=f"{{ftype_str}} · {{words}} palavras · ~{{r['reading_time']}}min · {{', '.join(list(r['topics'].keys())[:2])}} · {{', '.join(r['keywords'][:4])}}" # Corrected f-string here
    else:
        r["summary"]=f"Arquivo {{ftype_str}}."; r["relevance_score"]=50 # Corrected f-string here
        r["keywords"]=kw_extract(fname.lower(),5); r["topics"]=topic_dist(r["keywords"])
    return r

# ================================================
#  PAGE: ANALYTICS (Adjusted to reflect changes)
# ================================================
def page_analytics():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.9rem">Painel de Análises</h1>',unsafe_allow_html=True) # Removed emoji
    email=st.session_state.current_user; ud=guser(); d=st.session_state.stats_data

    # Removed "Repositório" and "Interesses" tabs as their content is now integrated elsewhere
    tf,tp,ti,ttrends=st.tabs(["  Publicações  ","  Impacto  ","  Privacidade  ","  Tendências  "]) # Adjusted tabs

    with tf: # Now "Publicações"
        my_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==email]
        all_posts=st.session_state.feed_posts
        if not my_posts: st.markdown(f'<div class="glass" style="text-align:center;padding:2.5rem;color:var(--t3)">Publique pesquisas para ver análises.</div>',unsafe_allow_html=True) # Removed emoji
        else:
            c1,c2,c3,c4=st.columns(4)
            with c1: st.markdown(f'<div class="mbox"><div class="mval-acc">{{len(my_posts)}}</div><div class="mlbl">Pesquisas</div></div>',unsafe_allow_html=True) # Corrected f-string here
            with c2: st.markdown(f'<div class="mbox"><div class="mval-teal">{{sum(p["likes"] for p in my_posts)}}</div><div class="mlbl">Total Curtidas</div></div>',unsafe_allow_html=True) # Corrected f-string here
            with c3: st.markdown(f'<div class="mbox"><div class="mval-pur">{{sum(p.get("citations",0) for p in my_posts)}}</div><div class="mlbl">Total Citações</div></div>',unsafe_allow_html=True) # Corrected f-string here
            with c4: st.markdown(f'<div class="mbox"><div class="mval-red">{{fmt_num(sum(p.get("views",0) for p in my_posts))}}</div><div class="mlbl">Visualizações</div></div>',unsafe_allow_html=True) # Corrected f-string here
            # Engagement per post
            if len(my_posts)>0:
                fig_eng=go.Figure(go.Bar(x=[p["title"][:30]+"…" if len(p["title"])>30 else p["title"] for p in my_posts],
                                          y=[p["likes"]+p.get("citations",0)*2+len(p.get("comments",[]))*3 for p in my_posts],
                                          marker=dict(color=[PRIMARY_COLOR, SECONDARY_COLOR, TERTIARY_COLOR, WARNING_COLOR, ERROR_COLOR, PRIMARY_COLOR]),text=[f'{{p["likes"]}} ' for p in my_posts],textposition="outside",textfont=dict(color=TEXT_COLOR_DARK,size=8))) # Corrected f-string here
                fig_eng.update_layout(**{**pc_dark(),'height':220,'xaxis':dict(tickangle=-30,tickfont=dict(size=8)),'title':dict(text="Score de engajamento por pesquisa",font=dict(color=TEXT_COLOR_LIGHT,family="Syne",size=10))})
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True)
                st.plotly_chart(fig_eng,use_container_width=True)
                st.markdown('</div>',unsafe_allow_html=True)
            for p in sorted(my_posts,key=lambda x:x.get("date",""),reverse=True):
                st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;justify-content:space-between"><div style="font-family:Syne,sans-serif;font-size:.85rem;font-weight:700;color:var(--t0)">{{p["title"][:55]}}</div>{{badge(p["status"])}}</div><div style="font-size:.67rem;color:var(--t3);margin-top:.32rem">{{p.get("date","")}} · {{p["likes"]}} · {{p.get("citations",0)}} · {{len(p.get("comments",[]))}} · {{fmt_num(p.get("views",0))}}</div></div>',unsafe_allow_html=True) # Corrected f-string here

    with tp: # Now "Impacto"
        c1,c2,c3=st.columns(3)
        with c1: st.markdown(f'<div class="mbox"><div class="mval-acc">{{d.get("h_index",7)}}</div><div class="mlbl">Índice H</div></div>',unsafe_allow_html=True) # Corrected f-string here
        with c2: st.markdown(f'<div class="mbox"><div class="mval-teal">{{d.get("fator_impacto",4.2):.1f}}</div><div class="mlbl">Fator Impacto</div></div>',unsafe_allow_html=True) # Corrected f-string here
        with c3: st.markdown(f'<div class="mbox"><div class="mval-pur">{{len(st.session_state.saved_articles)}}</div><div class="mlbl">Artigos Salvos</div></div>',unsafe_allow_html=True) # Corrected f-string here
        st.markdown("<hr>",unsafe_allow_html=True)
        nh=st.number_input("Índice H",0,200,d.get("h_index",7),key="e_h")
        nfi=st.number_input("Fator impacto",0.0,100.0,float(d.get("fator_impacto",4.2)),step=0.1,key="e_fi")
        nn=st.text_area("Notas de pesquisa",value=d.get("notes",""),key="e_nt",height=80)
        if st.button("Salvar métricas",key="btn_sm"): d.update({"h_index":nh,"fator_impacto":nfi,"notes":nn}); st.success("Salvo!") # Removed emoji

    with ti: # Now "Privacidade" (formerly "Interesses")
        en=ud.get("2fa_enabled",False)
        if st.button("Desativar 2FA" if en else "Ativar 2FA",key="cfg_2fa",use_container_width=True): # Removed emoji
            st.session_state.users[email]["2fa_enabled"]=not en; save_db(); st.rerun()
        st.markdown(f'<div style="font-size:.72rem;color:var(--t2);margin-top:.4rem">2FA: <strong style="color:{SECONDARY_COLOR if en else ERROR_COLOR}">{{"Ativo" if en else "Inativo"}}</strong></div>',unsafe_allow_html=True) # Corrected f-string here
        st.markdown("<hr>",unsafe_allow_html=True)
        st.markdown('<h2 style="margin-bottom:.5rem">Interesses de Pesquisa</h2>', unsafe_allow_html=True)
        prefs=st.session_state.user_prefs.get(email,{})
        if prefs:
            top=sorted(prefs.items(),key=lambda x:-x[1])[:12]; mx=max(s for _,s in top) if top else 1
            cats=[t for t,_ in top[:8]]; vals=[round(s/mx*100) for _,s in top[:8]]
            if len(cats)>=3:
                fig3=go.Figure(go.Scatterpolar(r=vals+[vals[0]],theta=cats+[cats[0]],fill='toself',line=dict(color=PRIMARY_COLOR),fillcolor=f"rgba(13,127,232,.10)"))
                fig3.update_layout(height=270,polar=dict(bgcolor="rgba(0,0,0,0)",radialaxis=dict(visible=True,gridcolor="rgba(255,255,255,.04)",color=TEXT_COLOR_DARK,tickfont=dict(size=8)),angularaxis=dict(gridcolor="rgba(255,255,255,.04)",color=TEXT_COLOR_DARK,tickfont=dict(size=9))),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=40,r=40,t=15,b=15))
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True)
                st.plotly_chart(fig3,use_container_width=True)
                st.markdown('</div>',unsafe_allow_html=True)
            for t,s in top[:10]:
                norm=s/mx*100
                st.markdown(f'<div style="margin-bottom:.3rem"><div style="display:flex;justify-content:space-between;font-size:.71rem;margin-bottom:3px"><span style="color:var(--t1)">{{t}}</span><span style="color:var(--t3)">{{round(norm)}}%</span></div>{{prog_bar(norm,PRIMARY_COLOR)}}</div>',unsafe_allow_html=True) # Corrected f-string here
        else: st.info("Interaja com pesquisas para mapear interesses.")

    with ttrends: # Now "Tendências"
        st.markdown('<div style="font-size:.62rem;color:var(--t3);margin-bottom:.8rem">Análise temporal de tendências na plataforma</div>',unsafe_allow_html=True)
        rs=compute_research_stats(st.session_state.feed_posts)
        if rs.get("months") and len(rs["months"])>1:
            fig_m=go.Figure()
            fig_m.add_trace(go.Scatter(x=rs["months"],y=rs["monthly_counts"],name="Pesquisas",line=dict(color=PRIMARY_COLOR,width=2),fill='tozeroy',fillcolor=f"rgba(13,127,232,.07)"))
            fig_m.add_trace(go.Scatter(x=rs["months"],y=[l//10 for l in rs["monthly_likes"]],name="Curtidas (÷10)",line=dict(color=SECONDARY_COLOR,width=2),yaxis="y"))
            fig_m.update_layout(**{**pc_dark(),'height':200,'title':dict(text="Atividade por mês",font=dict(color=TEXT_COLOR_LIGHT,family="Syne",size=10)),'legend':dict(font=dict(color=TEXT_COLOR_DARK,size=9))})
            st.markdown('<div class="chart-wrap">',unsafe_allow_html=True)
            st.plotly_chart(fig_m,use_container_width=True)
            st.markdown('</div>',unsafe_allow_html=True)
        c1t,c2t=st.columns(2)
        with c1t:
            if rs.get("top_tags"):
                fig_tags=go.Figure(go.Bar(x=list(rs["top_tags"].values()),y=list(rs["top_tags"].keys()),orientation='h',marker=dict(color=[PRIMARY_COLOR, SECONDARY_COLOR, TERTIARY_COLOR, WARNING_COLOR, ERROR_COLOR, PRIMARY_COLOR, SECONDARY_COLOR, TERTIARY_COLOR, WARNING_COLOR, ERROR_COLOR])))
                fig_tags.update_layout(**{**pc_dark(),'height':240,'title':dict(text="Tags mais usadas",font=dict(color=TEXT_COLOR_LIGHT,family="Syne",size=10)),'yaxis':dict(tickfont=dict(size=8))})
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True)
                st.plotly_chart(fig_tags,use_container_width=True)
                st.markdown('</div>',unsafe_allow_html=True)
        with c2t:
            if rs.get("top_areas"):
                fig_areas=go.Figure(go.Pie(labels=list(rs["top_areas"].keys()),values=list(rs["top_areas"].values()),hole=0.5,marker=dict(colors=[PRIMARY_COLOR, SECONDARY_COLOR, TERTIARY_COLOR, WARNING_COLOR, ERROR_COLOR, PRIMARY_COLOR, SECONDARY_COLOR, TERTIARY_COLOR],line=dict(color=[BG_COLOR_DARK]*15,width=2)),textfont=dict(color="white",size=7)))
                fig_areas.update_layout(height=240,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(font=dict(color=TEXT_COLOR_DARK,size=7)),margin=dict(l=0,r=0,t=10,b=0))
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True)
                st.plotly_chart(fig_areas,use_container_width=True)
                st.markdown('</div>',unsafe_allow_html=True)
        c1m,c2m,c3m=st.columns(3)
        with c1m: st.markdown(f'<div class="mbox"><div class="mval-acc">{{rs.get("avg_likes",0)}}</div><div class="mlbl">Média Curtidas</div></div>',unsafe_allow_html=True) # Corrected f-string here
        with c2m: st.markdown(f'<div class="mbox"><div class="mval-teal">{{fmt_num(int(rs.get("avg_views",0)))}}</div><div class="mlbl">Média Views</div></div>',unsafe_allow_html=True) # Corrected f-string here
        with c3m: st.markdown(f'<div class="mbox"><div class="mval-pur">{{rs.get("total_citations",0)}}</div><div class="mlbl">Total Citações</div></div>',unsafe_allow_html=True) # Corrected f-string here
    st.markdown('</div>',unsafe_allow_html=True)

# ================================================
#  PAGE: IMAGE VISION (Removed as a separate page, integrated into Search)
# ================================================

# ================================================
#  PAGE: CHAT
# ================================================
def page_chat():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.9rem">Mensagens</h1>',unsafe_allow_html=True) # Removed emoji
    cc,cm=st.columns([.82,2.8])
    email=st.session_state.current_user; users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    with cc:
        st.markdown('<div style="font-size:.57rem;font-weight:700;color:var(--t4);letter-spacing:.12em;text-transform:uppercase;margin-bottom:.7rem">Conversas</div>',unsafe_allow_html=True)
        shown=set()
        for ue in st.session_state.chat_contacts:
            if ue==email or ue in shown: continue
            shown.add(ue); ud=users.get(ue,{})
            un=ud.get("name","?"); ui=ini(un); ug=ugrad(ue)
            msgs=st.session_state.chat_messages.get(ue,[])
            last=msgs[-1]["text"][:22]+"…" if msgs and len(msgs[-1]["text"])>22 else (msgs[-1]["text"] if msgs else "Iniciar")
            active=st.session_state.active_chat==ue; online=is_online(ue)
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            bg=f"rgba(13,127,232,.1)" if active else "rgba(255,255,255,.04)"; bdr=f"rgba(13,127,232,.25)" if active else "rgba(255,255,255,.08)"
            st.markdown(f'<div style="background:{bg};border:1px solid {bdr};border-radius:12px;padding:8px 10px;margin-bottom:4px"><div style="display:flex;align-items:center;gap:7px">{{avh(ui,30,ug)}}<div style="overflow:hidden;flex:1"><div style="font-size:.75rem;font-weight:600;font-family:Syne,sans-serif;color:var(--t0)">{{dot}}{{un}}</div><div style="font-size:.62rem;color:var(--t3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{last}}</div></div></div></div>',unsafe_allow_html=True) # Corrected f-string here
            if st.button("→",key=f"oc_{ue}",use_container_width=True): st.session_state.active_chat=ue; st.rerun()
        st.markdown("<hr>",unsafe_allow_html=True)
        nc2=st.text_input("",placeholder="E-mail do pesquisador…",key="new_ct",label_visibility="collapsed")
        if st.button("Adicionar",key="btn_ac",use_container_width=True): # Removed emoji
            if nc2 in users and nc2!=email:
                if nc2 not in st.session_state.chat_contacts: st.session_state.chat_contacts.append(nc2)
                st.rerun()
    with cm:
        if st.session_state.active_chat:
            contact=st.session_state.active_chat; cd=users.get(contact,{})
            cn=cd.get("name","?"); ci=ini(cn); cg=ugrad(contact); msgs=st.session_state.chat_messages.get(contact,[])
            online=is_online(contact); dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            st.markdown(f'<div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.09);border-radius:14px;padding:10px 14px;margin-bottom:.85rem;display:flex;align-items:center;gap:10px">{{avh(ci,36,cg)}}<div style="flex:1"><div style="font-weight:700;font-size:.88rem;font-family:Syne,sans-serif;color:var(--t0)">{{dot}}{{cn}}</div><div style="font-size:.63rem;color:var(--teal)">Criptografado E2E</div></div>',unsafe_allow_html=True) # Corrected f-string here
            if st.button("Perfil",key="chat_profile",use_container_width=False): st.session_state.profile_view=contact; st.rerun() # Removed emoji
            st.markdown('</div>',unsafe_allow_html=True)
            for msg in msgs:
                im=msg["from"]=="me"; cls="bme" if im else "bthem"
                st.markdown(f'<div style="display:flex;{{"justify-content:flex-end" if im else ""}}"><div class="{cls}">{{msg["text"]}}<div style="font-size:.56rem;color:var(--t3);margin-top:2px;text-align:{{"right" if im else "left"}}}}">{{msg["time"]}}</div></div></div>',unsafe_allow_html=True) # Corrected f-string here
            st.markdown("<br>",unsafe_allow_html=True)
            ci2,cb2=st.columns([5,1])
            with ci2: nm=st.text_input("",placeholder="Escreva uma mensagem…",key=f"mi_{contact}",label_visibility="collapsed")
            with cb2:
                if st.button("→",key=f"ms_{contact}",use_container_width=True):
                    if nm:
                        now=datetime.now().strftime("%H:%M")
                        st.session_state.chat_messages.setdefault(contact,[]).append({"from":"me","text":nm,"time":now}); st.rerun()
        else:
            st.markdown(f'<div class="glass" style="text-align:center;padding:5rem"><div style="font-size:2.2rem;opacity:.15;margin-bottom:.85rem"> </div><div style="font-family:Syne,sans-serif;font-size:.96rem;color:var(--t1)">Selecione uma conversa</div><div style="font-size:.70rem;color:var(--t3);margin-top:.4rem">Criptografia AES-256 E2E</div></div>',unsafe_allow_html=True) # Removed emoji
    st.markdown('</div>',unsafe_allow_html=True)

# ================================================
#  PAGE: SETTINGS
# ================================================
def page_settings():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.9rem">Configurações</h1>',unsafe_allow_html=True) # Removed emoji
    email=st.session_state.current_user; ud=st.session_state.users.get(email,{})
    ts,tp,tsec=st.tabs(["  Conta  ","  Privacidade  ","  Segurança  "]) # Removed emojis
    with ts:
        st.markdown(f'<div class="abox"><div style="font-size:.57rem;color:var(--t3);text-transform:uppercase;letter-spacing:.10em;margin-bottom:.4rem;font-weight:700">Conta ativa</div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.95rem;color:var(--acc)">{{email}}</div><div style="font-size:.68rem;color:var(--t3);margin-top:.2rem">Membro verificado · {{ud.get("scholarship","")}}</div></div>',unsafe_allow_html=True) # Corrected f-string here
        new_n=st.text_input("Nome",value=ud.get("name",""),key="s_n"); new_a=st.text_input("Área",value=ud.get("area",""),key="s_a")
        new_sch=st.text_input("Bolsa",value=ud.get("scholarship",""),key="s_sch"); new_b=st.text_area("Biografia",value=ud.get("bio",""),key="s_b",height=80) # Changed to scholarship
        c1,c2=st.columns(2)
        with c1:
            if st.button("Salvar perfil",key="btn_sp2",use_container_width=True): # Removed emoji
                st.session_state.users[email].update({"name":new_n,"area":new_a,"bio":new_b,"scholarship":new_sch}); save_db(); st.success("Salvo!") # Removed emoji
        with c2:
            if st.button("Sair da conta",key="btn_logout",use_container_width=True): # Removed emoji
                st.session_state.logged_in=False; st.session_state.current_user=None; st.session_state.page="login"; st.rerun()
    with tp: # Privacy tab
        en=ud.get("2fa_enabled",False)
        if st.button("Desativar 2FA" if en else "Ativar 2FA",key="cfg_2fa",use_container_width=True): # Removed emoji
            st.session_state.users[email]["2fa_enabled"]=not en; save_db(); st.rerun()
        st.markdown(f'<div style="font-size:.72rem;color:var(--t2);margin-top:.4rem">2FA: <strong style="color:{SECONDARY_COLOR if en else ERROR_COLOR}">{{"Ativo" if en else "Inativo"}}</strong></div>',unsafe_allow_html=True) # Corrected f-string here
    with tsec:
        with st.form("cpw"):
            op=st.text_input("Senha atual",type="password"); np2=st.text_input("Nova senha",type="password"); nc3=st.text_input("Confirmar",type="password")
            if st.form_submit_button("Alterar senha",use_container_width=True): # Removed emoji
                if hp(op)!=ud.get("password",""): st.error("Senha atual incorreta.")
                elif np2!=nc3: st.error("Senhas não coincidem.")
                elif len(np2)<6: st.error("Mínimo 6 caracteres.")
                else: st.session_state.users[email]["password"]=hp(np2); save_db(); st.success("Senha alterada!") # Removed emoji
        st.markdown("<hr>",unsafe_allow_html=True)
        for nm,ds,ic in [("AES-256","Mensagens end-to-end"," "),("SHA-256","Hash de senhas"," "),("TLS 1.3","Transmissão segura"," ")]: # Removed emojis
            st.markdown(f'<div class="pbox-teal"><div style="display:flex;align-items:center;gap:9px"><span>{{ic}}</span><div><div style="font-weight:700;color:var(--teal);font-size:.78rem">{{nm}}</div><div style="font-size:.65rem;color:var(--t3)">{{ds}}</div></div><span class="badge-teal" style="margin-left:auto">Ativo</span></div></div>',unsafe_allow_html=True) # Corrected f-string here
    st.markdown('</div>',unsafe_allow_html=True)

# ================================================
#  MAIN
# ================================================
def main():
    inject_css()
    if not st.session_state.logged_in:
        page_login(); return
    render_nav()
    if st.session_state.profile_view:
        page_profile(st.session_state.profile_view); return
    {
        "repository":page_repository, # Set repository as the default/main page
        "search":page_search,
        "knowledge":page_knowledge,
        "analytics":page_analytics,
        "chat":page_chat,
        "settings":page_settings,
    }.get(st.session_state.page,page_repository)() # Default to repository

if __name__=="__main__":
    main()
