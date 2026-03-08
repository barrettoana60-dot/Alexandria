"""
Nebula V8 — Plataforma de Conhecimento Cientifico
Dark Blue Animated  |  No Emojis  |  Transparent Buttons
Repository  |  Search + Vision AI  |  AI Connections  |  Analytics in Folders
"""
import subprocess, sys, os, json, hashlib, re, io, base64
from datetime import datetime
from collections import defaultdict, Counter

def _pip(*pkgs):
    for p in pkgs:
        try: subprocess.check_call([sys.executable,"-m","pip","install",p,"-q"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except: pass

try: import plotly.graph_objects as go; import plotly.express as px
except: _pip("plotly"); import plotly.graph_objects as go; import plotly.express as px

try: import numpy as np
except: _pip("numpy"); import numpy as np

try: from PIL import Image as PILImage
except: _pip("pillow"); from PIL import Image as PILImage

try: import requests
except: _pip("requests"); import requests

try: import PyPDF2
except: _pip("PyPDF2")
try: import PyPDF2
except: PyPDF2 = None

import streamlit as st
st.set_page_config(page_title="Nebula", page_icon="N", layout="wide", initial_sidebar_state="expanded")

# ══════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════
DB_FILE = "nebula_db.json"

GRAD_POOL = [
    "135deg,#0D47A1,#01579B","135deg,#0277BD,#006064","135deg,#1B5E20,#004D40",
    "135deg,#4A148C,#311B92","135deg,#BF360C,#880E4F","135deg,#006064,#0D47A1",
    "135deg,#01579B,#1B5E20","135deg,#311B92,#0277BD",
]
AREAS = ["Inteligencia Artificial","Neurociencia","Biologia Molecular","Fisica","Quimica",
         "Medicina","Matematica","Computacao","Astrofisica","Psicologia","Engenharia","Ecologia"]

STOPWORDS = {"de","a","o","que","e","do","da","em","um","para","com","uma","os","no","se",
             "na","por","mais","as","dos","como","mas","foi","ao","ele","das","tem","the",
             "of","and","to","in","is","it","that","was","for","on","are","with","they","at",
             "be","this","from","or","not","by","we","an","each","which","can","their","if"}

SEED_POSTS = [
    {"id":1,"author":"Carlos Mendez","author_email":"carlos@nebula.ai","avatar":"CM","area":"Neurociencia",
     "title":"Efeitos da Privacao de Sono na Plasticidade Sinaptica Hipocampal",
     "abstract":"Investigamos como 24h de privacao de sono afetam espinhas dendriticas em ratos Wistar, com reducao de 34% na plasticidade hipocampal. Identificamos janela critica nas primeiras 6h de recuperacao do sono. Metodologia incluiu microscopia confocal e analise comportamental.",
     "tags":["neurociencia","sono","memoria","hipocampo","plasticidade"],
     "likes":47,"comments":[{"user":"Maria Silva","text":"Excelente metodologia!"},{"user":"Joao Lima","text":"Quais os criterios de exclusao?"}],
     "status":"Em andamento","date":"2026-02-10","liked_by":[],"saved_by":[],"views":312,"area_cat":"Neurociencia"},
    {"id":2,"author":"Luana Freitas","author_email":"luana@nebula.ai","avatar":"LF","area":"Biomedicina",
     "title":"CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras",
     "abstract":"Vetor AAV9 modificado para entrega de CRISPR no gene DMD com eficiencia de 78% em modelos mdx. Resultados promissores para ensaios clinicos fase I. Publicacao em Cell prevista Q2 2026.",
     "tags":["CRISPR","terapia genica","musculo","AAV9","distrofia"],
     "likes":93,"comments":[{"user":"Ana","text":"Quando iniciam os trials?"}],
     "status":"Publicado","date":"2026-01-28","liked_by":[],"saved_by":[],"views":891,"area_cat":"Biologia Molecular"},
    {"id":3,"author":"Rafael Souza","author_email":"rafael@nebula.ai","avatar":"RS","area":"Computacao",
     "title":"Redes Neurais Quantico-Classicas para Otimizacao Combinatoria",
     "abstract":"Arquitetura hibrida variacional combinando qubits supercondutores com camadas densas classicas. TSP resolvido com 40% menos iteracoes que metodos classicos. Implementado em hardware IBM Quantum.",
     "tags":["quantum ML","otimizacao","TSP","qubits"],
     "likes":201,"comments":[],"status":"Em andamento","date":"2026-02-15","liked_by":[],"saved_by":[],"views":1240,"area_cat":"Computacao"},
    {"id":4,"author":"Priya Nair","author_email":"priya@nebula.ai","avatar":"PN","area":"Astrofisica",
     "title":"Deteccao de Materia Escura via Lentes Gravitacionais Fracas",
     "abstract":"Mapeamento com 100M de galaxias do DES Y3. Tensao de 2.8 sigma com Lambda-CDM em escalas < 1 Mpc. Metodologia bayesiana para remocao de sistematicos em shear catalogs.",
     "tags":["astrofisica","materia escura","cosmologia","DES","lentes gravitacionais"],
     "likes":312,"comments":[],"status":"Publicado","date":"2026-02-01","liked_by":[],"saved_by":[],"views":2180,"area_cat":"Astrofisica"},
    {"id":5,"author":"Joao Lima","author_email":"joao@nebula.ai","avatar":"JL","area":"Psicologia",
     "title":"Vies de Confirmacao em Decisoes Medicas Assistidas por IA",
     "abstract":"Estudo duplo-cego com 240 medicos. Sistemas de IA mal calibrados amplificam vieses cognitivos em 22% dos casos. Desenvolvemos framework de auditoria etica para LLMs clinicos.",
     "tags":["psicologia","IA","cognicao","medicina","etica"],
     "likes":78,"comments":[{"user":"Carlos M.","text":"Muito relevante!"}],
     "status":"Publicado","date":"2026-02-08","liked_by":[],"saved_by":[],"views":456,"area_cat":"Psicologia"},
]

SEED_USERS = {
    "demo@nebula.ai":{"name":"Ana Pesquisadora","password":hashlib.sha256("demo123".encode()).hexdigest(),"bio":"Pesquisadora em IA e Ciencias Cognitivas","area":"Inteligencia Artificial","bolsa":"CNPq","followers":128,"following":47,"verified":True},
    "carlos@nebula.ai":{"name":"Carlos Mendez","password":hashlib.sha256("nebula123".encode()).hexdigest(),"bio":"Neurocientista | UFMG","area":"Neurociencia","bolsa":"FAPEMIG","followers":210,"following":45,"verified":True},
    "luana@nebula.ai":{"name":"Luana Freitas","password":hashlib.sha256("nebula123".encode()).hexdigest(),"bio":"Biomedica | FIOCRUZ","area":"Biologia Molecular","bolsa":"CAPES","followers":178,"following":62,"verified":True},
    "rafael@nebula.ai":{"name":"Rafael Souza","password":hashlib.sha256("nebula123".encode()).hexdigest(),"bio":"Computacao Quantica | USP","area":"Computacao","bolsa":"CNPq","followers":340,"following":88,"verified":True},
    "priya@nebula.ai":{"name":"Priya Nair","password":hashlib.sha256("nebula123".encode()).hexdigest(),"bio":"Astrofisica | MIT","area":"Astrofisica","bolsa":"NSF","followers":520,"following":31,"verified":True},
    "joao@nebula.ai":{"name":"Joao Lima","password":hashlib.sha256("nebula123".encode()).hexdigest(),"bio":"Psicologo Cognitivo | UNICAMP","area":"Psicologia","bolsa":"FAPESP","followers":95,"following":120,"verified":True},
}

CHAT_INIT = {
    "carlos@nebula.ai":[{"from":"carlos@nebula.ai","text":"Oi! Vi seu comentario na pesquisa de sono.","time":"09:14"},{"from":"me","text":"Achei muito interessante!","time":"09:16"}],
    "luana@nebula.ai":[{"from":"luana@nebula.ai","text":"Podemos colaborar no proximo projeto?","time":"ontem"}],
}

# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════
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
        return f"{d}d" if d<7 else(f"{d//7}sem" if d<30 else f"{d//30}m")
    except: return ds
def fmt_num(n):
    try: n=int(n); return f"{n/1000:.1f}k" if n>=1000 else str(n)
    except: return str(n)
def ugrad(e): return f"linear-gradient({GRAD_POOL[hash(e or '')%len(GRAD_POOL)]})"
def is_online(e): return (hash(e+"on")%3)!=0
def guser():
    if not isinstance(st.session_state.get("users"),dict): return {}
    return st.session_state.users.get(st.session_state.current_user,{})
def get_api_key(): return st.session_state.get("api_key","") or os.environ.get("ANTHROPIC_API_KEY","")

def area_sim(a1, a2):
    """Simple area similarity score 0-100."""
    if not a1 or not a2: return 0
    a1,a2=a1.lower(),a2.lower()
    if a1==a2: return 100
    # keyword overlap
    w1=set(a1.replace(","," ").split()); w2=set(a2.replace(","," ").split())
    w1={w for w in w1 if len(w)>2}; w2={w for w in w2 if len(w)>2}
    if not w1 or not w2: return 0
    inter=len(w1&w2); union=len(w1|w2)
    jac=inter/union if union else 0
    # substring match
    sub=1.0 if a1 in a2 or a2 in a1 else 0.0
    return int(min(100, (jac*70 + sub*30 + (10 if any(w in a2 for w in w1) else 0))))

def save_db():
    try:
        with open(DB_FILE,"w",encoding="utf-8") as f:
            json.dump({
                "users":st.session_state.users,"feed_posts":st.session_state.feed_posts,
                "folders":st.session_state.folders,"saved_articles":st.session_state.saved_articles,
                "followed":st.session_state.followed,
                "user_prefs":{k:dict(v) for k,v in st.session_state.user_prefs.items()},
            },f,ensure_ascii=False,indent=2)
    except: pass

def init_state():
    if "initialized" in st.session_state: return
    st.session_state.initialized=True
    disk={}
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,"r",encoding="utf-8") as f: disk=json.load(f)
        except: pass
    du=disk.get("users",{}); du={k:v for k,v in du.items() if isinstance(v,dict)}
    st.session_state.setdefault("users",{**SEED_USERS,**du})
    st.session_state.setdefault("logged_in",False)
    st.session_state.setdefault("current_user",None)
    st.session_state.setdefault("page","login")
    st.session_state.setdefault("profile_view",None)
    st.session_state.setdefault("welcome_area","")
    dp=disk.get("user_prefs",{})
    st.session_state.setdefault("user_prefs",{k:defaultdict(float,v) for k,v in dp.items()})
    rp=disk.get("feed_posts",[dict(p) for p in SEED_POSTS])
    for p in rp: p.setdefault("liked_by",[]); p.setdefault("saved_by",[]); p.setdefault("comments",[]); p.setdefault("views",200)
    st.session_state.setdefault("feed_posts",rp)
    st.session_state.setdefault("folders",disk.get("folders",{}))
    st.session_state.setdefault("folder_files_bytes",{})
    st.session_state.setdefault("chat_contacts",list(SEED_USERS.keys()))
    st.session_state.setdefault("chat_messages",{k:list(v) for k,v in CHAT_INIT.items()})
    st.session_state.setdefault("active_chat",None)
    st.session_state.setdefault("followed",disk.get("followed",["carlos@nebula.ai","luana@nebula.ai"]))
    st.session_state.setdefault("saved_articles",disk.get("saved_articles",[]))
    st.session_state.setdefault("img_result",None)
    st.session_state.setdefault("claude_vision_result",None)
    st.session_state.setdefault("search_results",None)
    st.session_state.setdefault("last_sq","")
    st.session_state.setdefault("stats_data",{"h_index":4,"fator_impacto":3.8,"notes":""})
    st.session_state.setdefault("compose_open",False)
    st.session_state.setdefault("scholar_cache",{})
    st.session_state.setdefault("ai_conn_cache",{})
    st.session_state.setdefault("api_key",os.environ.get("ANTHROPIC_API_KEY",""))

init_state()

# ══════════════════════════════════════════════════════════════
#  CLAUDE AI
# ══════════════════════════════════════════════════════════════
def call_claude(user_msgs, system="", max_tokens=1000, img_bytes=None):
    key=get_api_key()
    if not key or not key.startswith("sk-"):
        return None, "API key ausente"
    content=[]
    if img_bytes:
        buf=io.BytesIO()
        PILImage.open(io.BytesIO(img_bytes)).convert("RGB").save(buf,format="JPEG",quality=82)
        content.append({"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":base64.b64encode(buf.getvalue()).decode()}})
    for m in user_msgs: content.append({"type":"text","text":m})
    pl={"model":"claude-sonnet-4-20250514","max_tokens":max_tokens,"messages":[{"role":"user","content":content}]}
    if system: pl["system"]=system
    try:
        r=requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key":key,"anthropic-version":"2023-06-01","content-type":"application/json"},
            json=pl,timeout=35)
        if r.status_code==200: return r.json()["content"][0]["text"],None
        return None, r.json().get("error",{}).get("message",f"HTTP {r.status_code}")
    except Exception as e: return None,str(e)

# ══════════════════════════════════════════════════════════════
#  IMAGE ML PIPELINE (fast numpy)
# ══════════════════════════════════════════════════════════════
def analyze_image_ml(img_bytes):
    try:
        img=PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
        orig_w,orig_h=img.size
        img_r=img.resize((384,384),PILImage.LANCZOS)
        arr=np.array(img_r,dtype=np.float32)
        r_ch,g_ch,b_ch=arr[:,:,0],arr[:,:,1],arr[:,:,2]
        gray=0.2989*r_ch+0.5870*g_ch+0.1140*b_ch
        mr,mg,mb=float(r_ch.mean()),float(g_ch.mean()),float(b_ch.mean())
        brightness=float(gray.mean()); contrast=float(gray.std())
        hh,hw=gray.shape[0]//2,gray.shape[1]//2
        q=[gray[:hh,:hw].var(),gray[:hh,hw:].var(),gray[hh:,:hw].var(),gray[hh:,hw:].var()]
        symmetry=1.0-(max(q)-min(q))/(max(q)+1e-5)
        hist=np.histogram(gray,bins=64,range=(0,255))[0]; hn=hist/hist.sum(); hn=hn[hn>0]
        entropy=float(-np.sum(hn*np.log2(hn)))
        # Sobel
        kx=np.array([[-1,0,1],[-2,0,2],[-1,0,1]],dtype=np.float32)/8.0; ky=kx.T
        gn=gray/255.0
        def cv(img,k):
            pad=np.pad(img,((1,1),(1,1)),mode='edge'); out=np.zeros_like(img)
            for i in range(3):
                for j in range(3): out+=k[i,j]*pad[i:i+img.shape[0],j:j+img.shape[1]]
            return out
        gx=cv(gn.astype(np.float32),kx); gy=cv(gn.astype(np.float32),ky)
        sobel_mag=np.sqrt(gx**2+gy**2)
        edge_mean=float(sobel_mag.mean()); edge_density=float((sobel_mag>sobel_mag.mean()*1.5).mean())
        # FFT
        fft=np.fft.fftshift(np.abs(np.fft.fft2(gn))); fh,fw=fft.shape
        Y,X=np.ogrid[:fh,:fw]; dist=np.sqrt((X-fw//2)**2+(Y-fh//2)**2); r_f=min(fh,fw)//2; tot=fft.sum()+1e-9
        lf=float(fft[dist<r_f*0.1].sum()/tot); mf=float(fft[(dist>=r_f*0.1)&(dist<r_f*0.4)].sum()/tot); hf_v=float(fft[dist>=r_f*0.4].sum()/tot)
        outer=fft[dist>=r_f*0.3].ravel(); per_score=float(np.percentile(outer,99))/(float(np.mean(outer))+1e-5)
        # Classification
        sc={}
        sc["Histopatologia H&E"]=(30 if mr>140 and mb>80 and mg<mr else 0)+(20 if edge_density>0.10 else 0)+(20 if contrast>40 else 0)
        sc["Fluorescencia Nuclear DAPI"]=(45 if mb>150 and mb>mr+25 else 0)+(20 if entropy>5 else 0)
        sc["Fluorescencia GFP"]=(45 if mg>150 and mg>mr+25 else 0)+(15 if entropy>4.5 else 0)
        sc["Cristalografia/Difracao"]=(45 if per_score>12 else 0)+(30 if symmetry>0.75 else 0)
        sc["Gel/Western Blot"]=(40 if contrast<20 and abs(mr-mg)<15 and abs(mg-mb)<15 else 0)+(20 if lf>0.5 else 0)
        sc["Grafico/Diagrama"]=(35 if entropy<3.5 else 0)+(25 if edge_density>0.15 else 0)
        sc["Estrutura Molecular"]=(35 if symmetry>0.82 else 0)+(20 if per_score>12 else 0)
        sc["Microscopia Confocal"]=(30 if entropy>5.5 else 0)+(20 if edge_density>0.08 else 0)
        sc["Imagem Astronomica"]=(35 if brightness<60 else 0)+(25 if entropy>5 else 0)
        sc["Imagem Cientifica Geral"]=20
        best=max(sc,key=sc.get); conf=min(96,35+sc[best]*0.6)
        rh=np.histogram(r_ch.ravel(),bins=32,range=(0,255))[0].tolist()
        gh=np.histogram(g_ch.ravel(),bins=32,range=(0,255))[0].tolist()
        bh=np.histogram(b_ch.ravel(),bins=32,range=(0,255))[0].tolist()
        # Sobel viz
        sv=sobel_mag[::4,::4]; sv_norm=(sv/(sv.max()+1e-5)*255).astype(np.uint8).tolist()
        return {"ok":True,"category":best,"confidence":round(conf,1),
                "all_scores":dict(sorted(sc.items(),key=lambda x:-x[1])[:6]),
                "color":{"r":round(mr,1),"g":round(mg,1),"b":round(mb,1),"warm":mr>mb+15,"cool":mb>mr+15},
                "edges":{"mean":round(edge_mean,4),"density":round(edge_density,4)},
                "fft":{"lf":round(lf,3),"mf":round(mf,3),"hf":round(hf_v,3),"periodic":per_score>12,"score":round(per_score,1)},
                "symmetry":round(symmetry,3),"entropy":round(entropy,3),
                "brightness":round(brightness,1),"contrast":round(contrast,1),
                "size":(orig_w,orig_h),"histograms":{"r":rh,"g":gh,"b":bh},
                "sobel_viz":sv_norm,"sobel_shape":[len(sv_norm),len(sv_norm[0]) if sv_norm else 0]}
    except Exception as e: return {"ok":False,"error":str(e)}

VISION_SYSTEM = """Voce e um especialista cientifico de elite com expertise em analise de imagens de pesquisa. Sua tarefa e analisar esta imagem de forma extremamente detalhada e precisa.

Retorne APENAS JSON puro valido, sem markdown, sem codigo fence, sem texto adicional:

{
  "tipo_imagem": "<tipo preciso: ex: Microscopia de Fluorescencia Confocal, Histopatologia H&E, Cristalografia de Raios-X, Microscopia Eletronica de Transmissao TEM, Microscopia Eletronica de Varredura SEM, Western Blot, Gel de Eletroforese, Imunofluorescencia, FISH, PCR, Espectroscopia de Massa, Cromatografia, Tomografia Computadorizada, Ressonancia Magnetica, Radiografia, Imagem Astronomica, Diagrama de Estrutura Molecular, Grafico de Dados Cientificos, etc>",
  "area_cientifica": "<area precisa: Biologia Celular, Biologia Molecular, Neurociencia, Oncologia, Microbiologia, Genetica, Bioquimica, Fisica de Particulas, Astrofisica, Cosmologia, Quimica Organica, Ciencia de Materiais, Medicina Clinica, Patologia, Imunologia, etc>",
  "o_que_representa": "<descricao detalhada do que esta imagem representa cientificamente, o fenomeno ou processo sendo estudado, a hipotese que esta sendo testada ou demonstrada>",
  "composicao": "<do que e feita/composta a estrutura, preparacao ou amostra visivel. Materiais, reagentes, organismos, tecidos, substancias presentes>",
  "tecnica_detalhada": "<descricao tecnica detalhada da metodologia utilizada para criar esta imagem, incluindo preparacao de amostras, instrumentacao, parametros de aquisicao se visiveis>",
  "estruturas_observadas": [
    {"nome": "<nome da estrutura>", "descricao": "<o que e e sua funcao cientifica>", "localizacao": "<onde esta na imagem>"}
  ],
  "parametros_visiveis": "<resolucao, escala, magnificacao, comprimentos de onda, coloracao especifica, marcadores moleculares ou qualquer parametro tecnico visivel>",
  "significancia_cientifica": "<por que esta imagem e importante cientificamente, o que demonstra, que questoes de pesquisa ajuda a responder>",
  "interpretacao_resultados": "<o que os dados ou padroes visiveis indicam, o que os pesquisadores podem concluir a partir desta imagem>",
  "anomalias_artefatos": "<quaisquer anomalias, artefatos tecnico, padroes incomuns ou caracteristicas que merecem atencao>",
  "aplicacoes": "<onde e como estes resultados ou tecnica podem ser aplicados, areas beneficiadas>",
  "limitacoes": "<limitacoes desta tecnica ou interpretacao que pesquisadores devem considerar>",
  "qualidade_tecnica": "<Alta/Media/Baixa e justificativa tecnica da qualidade da imagem>",
  "confianca": <0-100>,
  "termos_busca_en": "<6-8 termos cientificos em ingles para buscar artigos relacionados, separados por espaco>",
  "contexto_historico": "<breve contexto sobre o desenvolvimento desta tecnica ou area de pesquisa>"
}"""

# ══════════════════════════════════════════════════════════════
#  DOCUMENT ANALYSIS
# ══════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def kw_extract(text, n=20):
    if not text: return []
    words=re.findall(r'\b[a-zA-Zaáàâãéêíóôõúüç]{4,}\b',text.lower())
    words=[w for w in words if w not in STOPWORDS]
    if not words: return []
    tf=Counter(words); tot=sum(tf.values())
    return [w for w,_ in sorted({w:c/tot for w,c in tf.items()}.items(),key=lambda x:-x[1])[:n]]

@st.cache_data(show_spinner=False)
def topic_dist(kws):
    tm={"Saude/Medicina":["saude","medicina","clinico","health","medical","therapy","disease","cancer","tumor","patologia"],
        "Biologia":["biologia","genomica","gene","dna","rna","proteina","celula","crispr","cell","molecular","celular"],
        "Neurociencia":["neurociencia","neural","cerebro","cognicao","memoria","sono","brain","neuron","sinaptico"],
        "Computacao/IA":["algoritmo","machine","learning","inteligencia","dados","computacao","ia","deep","quantum","neural"],
        "Fisica":["fisica","quantica","particula","energia","galaxia","astrofisica","cosmologia","physics","onda"],
        "Quimica":["quimica","molecula","sintese","reacao","polimero","chemistry","molecule","composto"],
        "Engenharia":["engenharia","sistema","robotica","automacao","engineering","controle"],
        "Ciencias Sociais":["sociedade","cultura","educacao","politica","psicologia","comportamento"],
        "Ecologia":["ecologia","clima","ambiente","biodiversidade","ecology","sustentabilidade"],
        "Matematica":["matematica","estatistica","probabilidade","equacao","mathematics","calculo"]}
    s=defaultdict(int)
    for kw in kws:
        for tp,terms in tm.items():
            if any(t in kw or kw in t for t in terms): s[tp]+=1
    return dict(sorted(s.items(),key=lambda x:-x[1])) if s else {"Pesquisa Geral":1}

@st.cache_data(show_spinner=False)
def analyze_doc(fname, fbytes, ftype_str, area=""):
    r={"file":fname,"keywords":[],"topics":{},"relevance_score":0,"summary":"","writing_quality":0,"reading_time":0,"word_count":0}
    text=""
    if ftype_str=="PDF" and fbytes and PyPDF2:
        try:
            rd=PyPDF2.PdfReader(io.BytesIO(fbytes)); t=""
            for pg in rd.pages[:15]:
                try: t+=pg.extract_text()+"\n"
                except: pass
            text=t[:30000]
        except: pass
    elif fbytes:
        try: text=fbytes.decode("utf-8",errors="ignore")[:30000]
        except: pass
    if text:
        r["keywords"]=kw_extract(text,20); r["topics"]=topic_dist(r["keywords"])
        words=len(text.split()); r["word_count"]=words; r["reading_time"]=max(1,round(words/200))
        r["writing_quality"]=min(100,50+(15 if len(r["keywords"])>12 else 0)+(15 if words>800 else 0)+(10 if r["reading_time"]>3 else 0))
        if area:
            aw=area.lower().split(); rel=sum(1 for w in aw if any(w in kw for kw in r["keywords"]))
            r["relevance_score"]=min(100,rel*15+45)
        else: r["relevance_score"]=65
        r["summary"]=f"{ftype_str} · {words} palavras · ~{r['reading_time']}min · {', '.join(list(r['topics'].keys())[:2])}"
    else:
        r["summary"]=f"Arquivo {ftype_str}."; r["relevance_score"]=50
        r["keywords"]=kw_extract(fname.lower(),5); r["topics"]=topic_dist(r["keywords"])
    return r

# ══════════════════════════════════════════════════════════════
#  SEARCH APIs
# ══════════════════════════════════════════════════════════════
@st.cache_data(ttl=600,show_spinner=False)
def search_ss(q, lim=8):
    try:
        r=requests.get("https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query":q,"limit":lim,"fields":"title,authors,year,abstract,venue,externalIds,openAccessPdf,citationCount"},timeout=9)
        if r.status_code==200:
            out=[]
            for p in r.json().get("data",[]):
                ext=p.get("externalIds",{}) or {}; doi=ext.get("DOI",""); arx=ext.get("ArXiv","")
                pdf=p.get("openAccessPdf") or {}
                link=pdf.get("url","") or(f"https://arxiv.org/abs/{arx}" if arx else(f"https://doi.org/{doi}" if doi else ""))
                al=p.get("authors",[]) or []; au=", ".join(a.get("name","") for a in al[:3])
                if len(al)>3: au+=" et al."
                out.append({"title":p.get("title","Sem titulo"),"authors":au or "—","year":p.get("year","?"),
                    "source":p.get("venue","") or "Semantic Scholar","doi":doi or arx or "—",
                    "abstract":(p.get("abstract","") or "")[:300],"url":link,
                    "citations":p.get("citationCount",0),"origin":"semantic"})
            return out
    except: pass
    return []

@st.cache_data(ttl=600,show_spinner=False)
def search_cr(q, lim=4):
    try:
        r=requests.get("https://api.crossref.org/works",
            params={"query":q,"rows":lim,"select":"title,author,issued,abstract,DOI,container-title,is-referenced-by-count"},timeout=9)
        if r.status_code==200:
            out=[]
            for p in r.json().get("message",{}).get("items",[]):
                title=(p.get("title") or ["?"])[0]; ars=p.get("author",[]) or []
                au=", ".join(f'{a.get("given","").split()[0] if a.get("given") else ""} {a.get("family","")}'.strip() for a in ars[:3])
                if len(ars)>3: au+=" et al."
                yr=(p.get("issued",{}).get("date-parts") or [[None]])[0][0]
                doi=p.get("DOI",""); ab=re.sub(r'<[^>]+>','',p.get("abstract","") or "")[:300]
                out.append({"title":title,"authors":au or "—","year":yr or "?",
                    "source":(p.get("container-title") or ["CrossRef"])[0],"doi":doi,
                    "abstract":ab,"url":f"https://doi.org/{doi}" if doi else "",
                    "citations":p.get("is-referenced-by-count",0),"origin":"crossref"})
            return out
    except: pass
    return []

def record(tags, w=1.0):
    e=st.session_state.get("current_user")
    if not e or not tags: return
    p=st.session_state.user_prefs.setdefault(e,defaultdict(float))
    for t in tags: p[t.lower()]+=w

EMAP={"pdf":"PDF","docx":"Word","xlsx":"Planilha","csv":"Dados","txt":"Texto","py":"Codigo","md":"Markdown","png":"Imagem","jpg":"Imagem","jpeg":"Imagem"}
def ftype_of(fname): return EMAP.get(fname.split(".")[-1].lower() if "." in fname else "","Arquivo")
CHART_C=["#1E88E5","#00BCD4","#00E676","#FFD600","#FF9800","#EF5350","#AB47BC","#26C6DA","#66BB6A","#FFA726"]

# ══════════════════════════════════════════════════════════════
#  CSS — DARK BLUE, ANIMATED, NO EMOJIS, TRANSPARENT BUTTONS
# ══════════════════════════════════════════════════════════════
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700;800&display=swap');

:root {
  --bg:   #020B18;
  --bg2:  #040D1E;
  --bg3:  #071525;
  --a1:   #1565C0;
  --a2:   #1E88E5;
  --a3:   #42A5F5;
  --a4:   #90CAF9;
  --c1:   #006064;
  --c2:   #00838F;
  --c3:   #26C6DA;
  --g1:   #1B5E20;
  --g2:   #2E7D32;
  --g3:   #66BB6A;
  --y1:   #E65100;
  --y2:   #FF9800;
  --r1:   #B71C1C;
  --r2:   #EF5350;
  --t0:   #ECEFF1;
  --t1:   #CFD8DC;
  --t2:   #90A4AE;
  --t3:   #546E7A;
  --t4:   #263238;
  --gl:   rgba(255,255,255,.04);
  --glb:  rgba(255,255,255,.06);
  --gb1:  rgba(255,255,255,.07);
  --gb2:  rgba(255,255,255,.10);
  --gb3:  rgba(255,255,255,.15);
  --ab1:  rgba(30,136,229,.08);
  --ab2:  rgba(30,136,229,.15);
  --ab3:  rgba(30,136,229,.25);
}

@keyframes bgpulse {
  0%   { background-color: #020B18; }
  25%  { background-color: #030E1F; }
  50%  { background-color: #041222; }
  75%  { background-color: #030E1F; }
  100% { background-color: #020B18; }
}
@keyframes glowshift {
  0%,100% { opacity:.7; transform:scale(1); }
  50%     { opacity:1; transform:scale(1.05); }
}

*, *::before, *::after { box-sizing:border-box; margin:0; padding:0; }
html, body { background:#020B18 !important; }
.stApp {
  background:#020B18 !important;
  color:var(--t1) !important;
  font-family:'Inter',-apple-system,sans-serif !important;
  animation: bgpulse 16s ease-in-out infinite !important;
}
.stApp::before {
  content:''; position:fixed; inset:0; pointer-events:none; z-index:0;
  background:
    radial-gradient(ellipse 60% 50% at -10% -5%, rgba(21,101,192,.11) 0%, transparent 55%),
    radial-gradient(ellipse 50% 40% at 110% 5%,  rgba(0,96,100,.09) 0%,  transparent 50%),
    radial-gradient(ellipse 40% 60% at 50% 110%, rgba(30,136,229,.06) 0%, transparent 60%);
  animation: glowshift 14s ease-in-out infinite;
}
.stApp::after {
  content:''; position:fixed; inset:0; pointer-events:none; z-index:0;
  background-image:
    linear-gradient(rgba(30,136,229,.018) 1px, transparent 1px),
    linear-gradient(90deg, rgba(30,136,229,.018) 1px, transparent 1px);
  background-size:72px 72px;
}

header[data-testid="stHeader"], #MainMenu, footer, .stDeployButton,
[data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="collapsedControl"], [data-testid="stSidebarCollapseButton"] {
  display:none !important;
}
.block-container {
  padding-top:.5rem !important; padding-bottom:4rem !important;
  max-width:1440px !important; position:relative; z-index:1;
  padding-left:.9rem !important; padding-right:.9rem !important;
}

/* ─── SIDEBAR ─── */
section[data-testid="stSidebar"] {
  background:rgba(2,9,22,.96) !important;
  border-right:1px solid rgba(30,136,229,.12) !important;
  width:118px !important; min-width:118px !important; max-width:118px !important;
  box-shadow:2px 0 28px rgba(0,0,0,.55) !important;
}
section[data-testid="stSidebar"] > div {
  padding:.7rem .45rem !important;
  display:flex; flex-direction:column; align-items:stretch; gap:2px;
}

/* ─── ALL BUTTONS TRANSPARENT ─── */
.stButton > button {
  background:transparent !important;
  border:1px solid rgba(255,255,255,.10) !important;
  border-radius:9px !important;
  color:var(--t2) !important;
  font-family:'Inter',sans-serif !important;
  font-weight:500 !important; font-size:.78rem !important;
  padding:.40rem .76rem !important;
  transition:all .16s ease !important;
  box-shadow:none !important;
  letter-spacing:.01em;
}
.stButton > button:hover {
  background:rgba(30,136,229,.10) !important;
  border-color:rgba(30,136,229,.30) !important;
  color:var(--a3) !important;
  transform:translateY(-1px) !important;
}
.stButton > button:active { transform:scale(.97) !important; }
.stButton > button p, .stButton > button span { color:inherit !important; }

/* sidebar buttons */
section[data-testid="stSidebar"] .stButton > button {
  text-align:center !important;
  width:100% !important;
  padding:.5rem .4rem !important;
  font-size:.70rem !important;
  font-weight:600 !important;
  letter-spacing:.03em;
  text-transform:uppercase;
  color:var(--t3) !important;
  border-color:transparent !important;
  border-radius:8px !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  background:rgba(30,136,229,.10) !important;
  border-color:rgba(30,136,229,.22) !important;
  color:var(--a3) !important;
  transform:none !important;
}
.sb-active .stButton > button {
  background:rgba(30,136,229,.14) !important;
  border:1px solid rgba(30,136,229,.30) !important;
  color:var(--a2) !important;
  font-weight:700 !important;
}

/* special button variants */
.btn-primary .stButton > button {
  border-color:rgba(30,136,229,.35) !important;
  color:var(--a3) !important;
}
.btn-primary .stButton > button:hover {
  background:rgba(30,136,229,.15) !important;
  border-color:rgba(30,136,229,.55) !important;
  color:var(--a2) !important;
}
.btn-success .stButton > button { border-color:rgba(102,187,106,.30) !important; color:var(--g3) !important; }
.btn-success .stButton > button:hover { background:rgba(102,187,106,.08) !important; }
.btn-danger .stButton > button { border-color:rgba(239,83,80,.25) !important; color:var(--r2) !important; }
.btn-danger .stButton > button:hover { background:rgba(239,83,80,.08) !important; }

/* ─── INPUTS ─── */
.stTextInput input, .stTextArea textarea {
  background:rgba(255,255,255,.03) !important;
  border:1px solid var(--gb1) !important;
  border-radius:9px !important; color:var(--t1) !important;
  font-family:'Inter',sans-serif !important; font-size:.82rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color:rgba(30,136,229,.40) !important;
  box-shadow:0 0 0 2px rgba(30,136,229,.08) !important;
}
.stTextInput label, .stTextArea label, .stSelectbox label,
.stFileUploader label, .stNumberInput label {
  color:var(--t3) !important; font-size:.59rem !important;
  letter-spacing:.09em !important; text-transform:uppercase !important; font-weight:700 !important;
}
input[type="number"] {
  background:rgba(255,255,255,.03) !important;
  border:1px solid var(--gb1) !important; border-radius:9px !important; color:var(--t1) !important;
}
.stSelectbox [data-baseweb="select"] {
  background:rgba(255,255,255,.03) !important; border:1px solid var(--gb1) !important; border-radius:9px !important;
}
.stFileUploader section {
  background:rgba(255,255,255,.02) !important; border:1.5px dashed var(--gb2) !important; border-radius:12px !important;
}

/* ─── CARDS ─── */
.card {
  background:var(--gl); border:1px solid var(--gb1); border-radius:14px;
  box-shadow:0 2px 18px rgba(0,0,0,.28); position:relative; overflow:hidden;
}
.card::after {
  content:''; position:absolute; top:0; left:0; right:0; height:1px;
  background:linear-gradient(90deg,transparent,rgba(30,136,229,.09),transparent);
  pointer-events:none;
}
.repo-card {
  background:var(--gl); border:1px solid var(--gb1); border-radius:14px;
  padding:.95rem 1.2rem; margin-bottom:.55rem; overflow:hidden;
  transition:border-color .15s, transform .15s, box-shadow .15s;
  animation:fadeUp .18s ease both;
}
.repo-card:hover { border-color:rgba(30,136,229,.22); transform:translateY(-1px); box-shadow:0 4px 24px rgba(0,0,0,.35); }
.sc { background:var(--gl); border:1px solid var(--gb1); border-radius:14px; padding:.9rem 1rem; margin-bottom:.55rem; }
.scard { background:var(--gl); border:1px solid var(--gb1); border-radius:12px; padding:.78rem .95rem; margin-bottom:.38rem; transition:border-color .12s,transform .12s; }
.scard:hover { border-color:rgba(30,136,229,.20); transform:translateY(-1px); }
.ai-box { background:linear-gradient(135deg,rgba(21,101,192,.07),rgba(0,96,100,.05)); border:1px solid rgba(30,136,229,.18); border-radius:14px; padding:1rem; margin-bottom:.6rem; }
.stat-box { background:var(--gl); border:1px solid var(--gb1); border-radius:12px; padding:.82rem; text-align:center; }
.compose-box { background:var(--glb); border:1px solid var(--gb2); border-radius:14px; padding:1.1rem 1.25rem; margin-bottom:.75rem; }
.chart-wrap { background:rgba(255,255,255,.02); border:1px solid var(--gb1); border-radius:12px; padding:.6rem; margin-bottom:.55rem; }
.cmt { background:rgba(255,255,255,.02); border:1px solid var(--gb1); border-radius:10px; padding:.45rem .80rem; margin-bottom:.20rem; }
.prof-hero { background:var(--glb); border:1px solid rgba(30,136,229,.14); border-radius:18px; padding:1.5rem; display:flex; gap:1.2rem; align-items:flex-start; margin-bottom:1rem; }
.bme { background:rgba(21,101,192,.14); border:1px solid rgba(30,136,229,.20); border-radius:16px 16px 4px 16px; padding:.50rem .80rem; max-width:70%; margin-left:auto; margin-bottom:4px; font-size:.79rem; line-height:1.6; }
.bthem { background:var(--gl); border:1px solid var(--gb1); border-radius:16px 16px 16px 4px; padding:.50rem .80rem; max-width:70%; margin-bottom:4px; font-size:.79rem; line-height:1.6; }
.vision-detail { background:rgba(21,101,192,.05); border:1px solid rgba(30,136,229,.15); border-radius:10px; padding:.65rem .85rem; margin-bottom:.38rem; }

/* ─── METRIC VALUES ─── */
.mval  { font-family:'Space Grotesk',sans-serif; font-size:1.5rem; font-weight:800; color:var(--a3); }
.mval-g{ font-family:'Space Grotesk',sans-serif; font-size:1.5rem; font-weight:800; color:var(--g3); }
.mval-y{ font-family:'Space Grotesk',sans-serif; font-size:1.5rem; font-weight:800; color:var(--y2); }
.mval-c{ font-family:'Space Grotesk',sans-serif; font-size:1.5rem; font-weight:800; color:var(--c3); }
.mlbl  { font-size:.57rem; color:var(--t3); margin-top:3px; letter-spacing:.09em; text-transform:uppercase; font-weight:700; }

/* ─── TAGS/BADGES ─── */
.tag   { display:inline-block; background:var(--ab1); border:1px solid var(--ab2); border-radius:20px; padding:2px 8px; font-size:.61rem; color:var(--a4); margin:2px; font-weight:500; }
.badge-b { display:inline-block; background:rgba(30,136,229,.10); border:1px solid rgba(30,136,229,.22); border-radius:20px; padding:2px 8px; font-size:.61rem; font-weight:700; color:var(--a2); }
.badge-g { display:inline-block; background:rgba(102,187,106,.09); border:1px solid rgba(102,187,106,.20); border-radius:20px; padding:2px 8px; font-size:.61rem; font-weight:700; color:var(--g3); }
.badge-y { display:inline-block; background:rgba(255,152,0,.09); border:1px solid rgba(255,152,0,.20); border-radius:20px; padding:2px 8px; font-size:.61rem; font-weight:700; color:var(--y2); }
.badge-c { display:inline-block; background:rgba(38,198,218,.09); border:1px solid rgba(38,198,218,.20); border-radius:20px; padding:2px 8px; font-size:.61rem; font-weight:700; color:var(--c3); }
.badge-r { display:inline-block; background:rgba(239,83,80,.09); border:1px solid rgba(239,83,80,.20); border-radius:20px; padding:2px 8px; font-size:.61rem; font-weight:700; color:var(--r2); }

/* ─── TABS ─── */
.stTabs [data-baseweb="tab-list"] { background:rgba(255,255,255,.02) !important; border:1px solid var(--gb1) !important; border-radius:10px !important; padding:3px !important; gap:2px !important; }
.stTabs [data-baseweb="tab"] { background:transparent !important; color:var(--t3) !important; border-radius:8px !important; font-size:.73rem !important; font-family:'Inter',sans-serif !important; font-weight:500 !important; }
.stTabs [aria-selected="true"] { background:rgba(30,136,229,.12) !important; color:var(--a2) !important; border:1px solid rgba(30,136,229,.22) !important; font-weight:700 !important; }
.stTabs [data-baseweb="tab-panel"] { background:transparent !important; padding-top:.75rem !important; }

/* ─── MISC ─── */
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.4;transform:scale(.7)} }
.dot-on  { display:inline-block; width:6px; height:6px; border-radius:50%; background:var(--g3); animation:pulse 2.5s infinite; margin-right:4px; vertical-align:middle; }
.dot-off { display:inline-block; width:6px; height:6px; border-radius:50%; background:var(--t4); margin-right:4px; vertical-align:middle; }
@keyframes fadeUp { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
.pw { animation:fadeUp .20s ease both; }
.dtxt { display:flex; align-items:center; gap:.6rem; margin:.65rem 0; font-size:.56rem; color:var(--t3); letter-spacing:.10em; text-transform:uppercase; font-weight:700; }
.dtxt::before,.dtxt::after { content:''; flex:1; height:1px; background:var(--gb1); }
h1 { font-family:'Space Grotesk',sans-serif !important; font-size:1.45rem !important; font-weight:800 !important; letter-spacing:-.03em; color:var(--t0) !important; }
h2 { font-family:'Space Grotesk',sans-serif !important; font-size:.96rem !important; font-weight:700 !important; color:var(--t0) !important; }
hr { border:none; border-top:1px solid var(--gb1) !important; margin:.75rem 0; }
label { color:var(--t2) !important; }
.stCheckbox label,.stRadio label { color:var(--t1) !important; }
.stRadio > div { display:flex !important; gap:4px !important; flex-wrap:wrap !important; }
.stRadio > div > label { background:rgba(255,255,255,.03) !important; border:1px solid var(--gb1) !important; border-radius:50px !important; padding:.26rem .70rem !important; font-size:.72rem !important; cursor:pointer !important; color:var(--t2) !important; transition:all .12s !important; }
.stRadio > div > label:hover { border-color:rgba(30,136,229,.30) !important; color:var(--a3) !important; }
.stExpander { background:var(--gl); border:1px solid var(--gb1); border-radius:12px; }
::-webkit-scrollbar { width:3px; height:3px; }
::-webkit-scrollbar-thumb { background:var(--t4); border-radius:3px; }
.js-plotly-plot .plotly .modebar { display:none !important; }

/* ─── REPO FILTER SIDEBAR ─── */
.filter-box { background:rgba(30,136,229,.04); border:1px solid rgba(30,136,229,.10); border-radius:12px; padding:.8rem; margin-bottom:.5rem; }
.filter-label { font-size:.58rem; font-weight:700; color:var(--t3); letter-spacing:.10em; text-transform:uppercase; margin-bottom:.4rem; }

/* ─── VISION AI BLOCKS ─── */
.vision-header { background:linear-gradient(135deg,rgba(21,101,192,.10),rgba(0,96,100,.07)); border:1px solid rgba(30,136,229,.22); border-radius:14px; padding:1.1rem; margin-bottom:.55rem; }
.vision-section { border-left:2px solid rgba(30,136,229,.30); padding-left:.75rem; margin-bottom:.6rem; }
.ml-metric { background:rgba(255,255,255,.03); border:1px solid var(--gb1); border-radius:10px; padding:.55rem .75rem; margin-bottom:.32rem; font-size:.76rem; }
</style>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  HTML HELPERS
# ══════════════════════════════════════════════════════════════
def avh(initials, sz=40, grad=None):
    fs=max(sz//3,9); bg=grad or "linear-gradient(135deg,#1565C0,#006064)"
    return (f'<div style="width:{sz}px;height:{sz}px;border-radius:50%;background:{bg};'
            f'display:flex;align-items:center;justify-content:center;font-family:Space Grotesk,sans-serif;'
            f'font-weight:800;font-size:{fs}px;color:white;flex-shrink:0;'
            f'border:1.5px solid rgba(255,255,255,.10)">{initials}</div>')

def tags_html(tags): return ' '.join(f'<span class="tag">{t}</span>' for t in (tags or []))

def badge(s):
    m={"Publicado":"badge-g","Concluido":"badge-c","Em andamento":"badge-y"}
    return f'<span class="{m.get(s,"badge-y")}">{s}</span>'

def pc_dark():
    return dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#546E7A",family="Inter",size=10),
                margin=dict(l=10,r=10,t=36,b=8),
                xaxis=dict(showgrid=False,color="#546E7A",tickfont=dict(size=9)),
                yaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,.04)",color="#546E7A",tickfont=dict(size=9)))

# ══════════════════════════════════════════════════════════════
#  AUTH — LOGIN + REGISTER (with bolsa + area similarity)
# ══════════════════════════════════════════════════════════════
def page_login():
    _,col,_=st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-bottom:2.5rem">
          <div style="font-family:'Space Grotesk',sans-serif;font-size:2.8rem;font-weight:800;
            letter-spacing:-.06em;background:linear-gradient(135deg,#42A5F5,#26C6DA);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
            margin-bottom:.5rem">NEBULA</div>
          <div style="color:#546E7A;font-size:.58rem;letter-spacing:.26em;text-transform:uppercase;font-weight:700">
            Plataforma de Conhecimento Cientifico
          </div>
        </div>""",unsafe_allow_html=True)

        ti,tu=st.tabs(["  Entrar  ","  Criar conta  "])
        with ti:
            with st.form("lf"):
                em=st.text_input("E-mail",placeholder="seu@email.com",key="li_e")
                pw=st.text_input("Senha",placeholder="••••••••",type="password",key="li_p")
                st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
                sub=st.form_submit_button("Entrar",use_container_width=True)
                st.markdown('</div>',unsafe_allow_html=True)
                if sub:
                    u=st.session_state.users.get(em)
                    if not u: st.error("E-mail nao encontrado.")
                    elif u["password"]!=hp(pw): st.error("Senha incorreta.")
                    else:
                        st.session_state.logged_in=True; st.session_state.current_user=em
                        record([w for w in u.get("area","").lower().split() if len(w)>3],1.0)
                        st.session_state.page="repository"; st.rerun()
            st.markdown('<div style="text-align:center;color:#546E7A;font-size:.67rem;margin-top:.55rem">demo@nebula.ai / demo123</div>',unsafe_allow_html=True)

        with tu:
            with st.form("sf"):
                nn=st.text_input("Nome completo",key="su_n")
                ne=st.text_input("E-mail institucional",key="su_e")
                na=st.text_input("Area de pesquisa",key="su_a",placeholder="ex: Neurociencia, Machine Learning...")
                nb=st.text_input("Bolsa / Financiamento",key="su_b",placeholder="CNPq, CAPES, FAPESP, NSF, sem bolsa...")
                np_=st.text_input("Senha",type="password",key="su_p")
                np2=st.text_input("Confirmar senha",type="password",key="su_p2")
                st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
                s2=st.form_submit_button("Criar conta",use_container_width=True)
                st.markdown('</div>',unsafe_allow_html=True)
                if s2:
                    if not all([nn,ne,na,np_,np2]): st.error("Preencha todos os campos.")
                    elif np_!=np2: st.error("Senhas nao coincidem.")
                    elif ne in st.session_state.users: st.error("E-mail ja cadastrado.")
                    else:
                        st.session_state.users[ne]={"name":nn,"password":hp(np_),"bio":"","area":na,"bolsa":nb or "","followers":0,"following":0,"verified":True}
                        save_db()
                        # Area similarity — find similar users
                        similar=[]
                        for ue,ud in st.session_state.users.items():
                            if ue==ne: continue
                            score=area_sim(na,ud.get("area",""))
                            if score>=25: similar.append((score,ue,ud))
                        similar.sort(key=lambda x:-x[0])
                        st.session_state.welcome_similar=similar[:5]
                        st.session_state.welcome_area=na
                        st.session_state.logged_in=True; st.session_state.current_user=ne
                        st.session_state.page="welcome"; st.rerun()

def page_welcome():
    """Post-registration welcome with area similarity mapping."""
    email=st.session_state.current_user; u=guser()
    sim=st.session_state.get("welcome_similar",[])
    _,col,_=st.columns([.5,2,.5])
    with col:
        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown(f'<div style="font-family:Space Grotesk,sans-serif;font-size:1.4rem;font-weight:800;color:#ECEFF1;margin-bottom:.3rem">Bem-vindo(a), {u.get("name","").split()[0]}</div>',unsafe_allow_html=True)
        st.markdown(f'<div style="color:#90A4AE;font-size:.80rem;margin-bottom:1.2rem">Conta criada. Area registrada: <strong style="color:#42A5F5">{u.get("area","")}</strong></div>',unsafe_allow_html=True)
        if sim:
            st.markdown('<div style="font-family:Space Grotesk,sans-serif;font-weight:700;font-size:.88rem;color:#ECEFF1;margin-bottom:.5rem">Pesquisadores com areas similares encontrados</div>',unsafe_allow_html=True)
            for score,ue,ud in sim:
                g=ugrad(ue)
                bar_w=int(score*0.9)
                st.markdown(f'''<div class="scard">
  <div style="display:flex;align-items:center;gap:10px">
    {avh(ini(ud.get("name","?")),36,g)}
    <div style="flex:1">
      <div style="font-weight:700;font-size:.83rem;color:#ECEFF1">{ud.get("name","?")}</div>
      <div style="font-size:.65rem;color:#42A5F5">{ud.get("area","")}</div>
      <div style="margin-top:4px;height:3px;border-radius:2px;width:{bar_w}%;background:linear-gradient(90deg,#1E88E5,#00BCD4)"></div>
      <div style="font-size:.58rem;color:#546E7A;margin-top:2px">{score}% similaridade</div>
    </div>
  </div>
</div>''',unsafe_allow_html=True)
                c1,c2=st.columns(2)
                with c1:
                    if st.button(f"Seguir {ud.get('name','').split()[0]}", key=f"ws_{ue}", use_container_width=True):
                        if ue not in st.session_state.followed: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                        save_db(); st.rerun()
                with c2:
                    if st.button("Ver perfil", key=f"wp_{ue}", use_container_width=True):
                        st.session_state.profile_view=ue; st.session_state.page="repository"; st.rerun()
        else:
            st.markdown('<div class="scard" style="text-align:center;padding:1.2rem;color:#546E7A">Nenhum pesquisador com area similar encontrado ainda.</div>',unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
        if st.button("Ir para o Repositorio",key="btn_go_repo",use_container_width=True):
            st.session_state.page="repository"; st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  SIDEBAR NAV
# ══════════════════════════════════════════════════════════════
NAV=[("repository","Repo"),("search","Busca"),("knowledge","Rede"),("folders","Pastas"),("chat","Chat")]

def render_nav():
    email=st.session_state.current_user; u=guser(); name=u.get("name","?"); g=ugrad(email)
    cur=st.session_state.page
    with st.sidebar:
        st.markdown(f'<div style="text-align:center;margin-bottom:.4rem"><div style="font-family:Space Grotesk,sans-serif;font-weight:800;font-size:.95rem;letter-spacing:-.04em;background:linear-gradient(135deg,#42A5F5,#26C6DA);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">NEBULA</div></div>',unsafe_allow_html=True)
        st.markdown('<hr style="margin:.35rem 0;opacity:.25">',unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex;justify-content:center;margin:.3rem 0">{avh(ini(name),42,g)}</div>',unsafe_allow_html=True)
        st.markdown(f'<div style="text-align:center;font-size:.60rem;color:#546E7A;margin-bottom:.4rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{name.split()[0]}</div>',unsafe_allow_html=True)
        if st.button("Perfil",key="sb_prof",help=f"Meu Perfil",use_container_width=True):
            st.session_state.profile_view=email; st.rerun()
        st.markdown('<hr style="margin:.35rem 0;opacity:.25">',unsafe_allow_html=True)
        for pk,lbl in NAV:
            is_a=(cur==pk and not st.session_state.profile_view)
            st.markdown(f'<div class="{"sb-active" if is_a else ""}">',unsafe_allow_html=True)
            if st.button(lbl,key=f"sb_{pk}",use_container_width=True):
                st.session_state.profile_view=None; st.session_state.page=pk; st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)
        st.markdown('<hr style="margin:.35rem 0;opacity:.25">',unsafe_allow_html=True)
        ak=st.text_input("",placeholder="sk-ant-...",type="password",key="sb_apikey",
                         label_visibility="collapsed",value=st.session_state.get("api_key",""))
        if ak!=st.session_state.get("api_key",""): st.session_state.api_key=ak
        has_key=bool(ak and ak.startswith("sk-"))
        st.markdown(f'<div style="text-align:center;font-size:.52rem;color:{"#66BB6A" if has_key else "#546E7A"};margin-bottom:.35rem">{"IA ativa" if has_key else "API key"}</div>',unsafe_allow_html=True)
        st.markdown('<div class="">',unsafe_allow_html=True)
        if st.button("Config",key="sb_cfg",use_container_width=True):
            st.session_state.profile_view=None; st.session_state.page="settings"; st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  PROFILE
# ══════════════════════════════════════════════════════════════
def page_profile(target_email):
    tu=st.session_state.users.get(target_email,{}); email=st.session_state.current_user
    if not tu: st.error("Perfil nao encontrado."); return
    tname=tu.get("name","?"); is_me=(email==target_email); g=ugrad(target_email)
    is_fol=target_email in st.session_state.followed
    user_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==target_email]
    liked_posts=[p for p in st.session_state.feed_posts if target_email in p.get("liked_by",[])]
    total_likes=sum(p["likes"] for p in user_posts)
    vb=' <span class="badge-g" style="font-size:.57rem">verificado</span>' if tu.get("verified") else ""
    bolsa=tu.get("bolsa",""); bolsa_html=f' <span class="badge-c" style="font-size:.57rem">{bolsa}</span>' if bolsa else ""
    st.markdown(f"""<div class="prof-hero">
  <div style="width:70px;height:70px;border-radius:50%;background:{g};display:flex;align-items:center;justify-content:center;font-family:Space Grotesk,sans-serif;font-weight:800;font-size:1.45rem;color:white;flex-shrink:0;border:2px solid rgba(255,255,255,.10)">{ini(tname)}</div>
  <div style="flex:1">
    <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:.2rem">
      <span style="font-family:'Space Grotesk',sans-serif;font-weight:800;font-size:1.25rem;color:#ECEFF1">{tname}</span>{vb}{bolsa_html}
    </div>
    <div style="color:#42A5F5;font-size:.78rem;font-weight:600;margin-bottom:.32rem">{tu.get("area","")}</div>
    <div style="color:#90A4AE;font-size:.75rem;line-height:1.65;margin-bottom:.65rem">{tu.get("bio","Sem biografia.")}</div>
    <div style="display:flex;gap:1.5rem;flex-wrap:wrap">
      <div><span style="font-family:'Space Grotesk',sans-serif;font-weight:800;font-size:.96rem;color:#ECEFF1">{tu.get("followers",0)}</span><span style="color:#546E7A;font-size:.65rem"> seguidores</span></div>
      <div><span style="font-family:'Space Grotesk',sans-serif;font-weight:800;font-size:.96rem;color:#ECEFF1">{tu.get("following",0)}</span><span style="color:#546E7A;font-size:.65rem"> seguindo</span></div>
      <div><span style="font-family:'Space Grotesk',sans-serif;font-weight:800;font-size:.96rem;color:#ECEFF1">{len(user_posts)}</span><span style="color:#546E7A;font-size:.65rem"> publicacoes</span></div>
      <div><span style="font-family:'Space Grotesk',sans-serif;font-weight:800;font-size:.96rem;color:#42A5F5">{fmt_num(total_likes)}</span><span style="color:#546E7A;font-size:.65rem"> curtidas</span></div>
    </div>
  </div>
</div>""",unsafe_allow_html=True)
    if not is_me:
        c1,c2,c3,_=st.columns([1,1,1,2])
        with c1:
            st.markdown(f'<div class="{"btn-success" if is_fol else "btn-primary"}">',unsafe_allow_html=True)
            if st.button("Seguindo" if is_fol else "Seguir",key="pf_f",use_container_width=True):
                if is_fol: st.session_state.followed.remove(target_email); tu["followers"]=max(0,tu.get("followers",0)-1)
                else: st.session_state.followed.append(target_email); tu["followers"]=tu.get("followers",0)+1
                save_db(); st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)
        with c2:
            if st.button("Chat",key="pf_chat",use_container_width=True):
                st.session_state.chat_messages.setdefault(target_email,[]); st.session_state.active_chat=target_email; st.session_state.page="chat"; st.rerun()
        with c3:
            if st.button("Voltar",key="pf_back",use_container_width=True): st.session_state.profile_view=None; st.rerun()
        tp,tl=st.tabs([f"  Publicacoes ({len(user_posts)})  ",f"  Curtidas ({len(liked_posts)})  "])
        with tp:
            for p in sorted(user_posts,key=lambda x:x.get("date",""),reverse=True): render_repo_card(p,ctx="prf")
            if not user_posts: st.info("Nenhuma publicacao.")
        with tl:
            for p in sorted(liked_posts,key=lambda x:x.get("date",""),reverse=True): render_repo_card(p,ctx="lk_prf",compact=True)
            if not liked_posts: st.info("Nenhuma curtida.")
    else:
        sa=st.session_state.saved_articles
        te,tl2,ts2,td=st.tabs(["  Editar Perfil  ",f"  Publicacoes ({len(user_posts)})  ",f"  Curtidas ({len(liked_posts)})  ",f"  Salvos ({len(sa)})  "])
        with te:
            nn=st.text_input("Nome",value=tu.get("name",""),key="cfg_n")
            na=st.text_input("Area de pesquisa",value=tu.get("area",""),key="cfg_a")
            nb2=st.text_input("Bolsa/Financiamento",value=tu.get("bolsa",""),key="cfg_b_bolsa")
            nb_b=st.text_area("Bio",value=tu.get("bio",""),key="cfg_b",height=75)
            cs,co=st.columns(2)
            with cs:
                st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
                if st.button("Salvar",key="sp",use_container_width=True):
                    st.session_state.users[email].update({"name":nn,"area":na,"bolsa":nb2,"bio":nb_b}); save_db(); st.success("Salvo!"); st.rerun()
                st.markdown('</div>',unsafe_allow_html=True)
            with co:
                st.markdown('<div class="btn-danger">',unsafe_allow_html=True)
                if st.button("Sair",key="so",use_container_width=True):
                    st.session_state.logged_in=False; st.session_state.current_user=None; st.session_state.page="login"; st.rerun()
                st.markdown('</div>',unsafe_allow_html=True)
        with tl2:
            for p in sorted(user_posts,key=lambda x:x.get("date",""),reverse=True): render_repo_card(p,ctx="myp",show_author=False)
            if not user_posts: st.info("Nenhuma publicacao ainda.")
        with ts2:
            for p in sorted(liked_posts,key=lambda x:x.get("date",""),reverse=True): render_repo_card(p,ctx="mylk",compact=True)
            if not liked_posts: st.info("Nenhuma curtida ainda.")
        with td:
            if sa:
                for idx,a in enumerate(sa): render_article(a,idx=idx+4000,ctx="saved")
            else: st.info("Nenhum artigo salvo.")

# ══════════════════════════════════════════════════════════════
#  REPOSITORY CARD
# ══════════════════════════════════════════════════════════════
def render_repo_card(post, ctx="repo", show_author=True, compact=False):
    email=st.session_state.current_user; pid=post["id"]
    liked=email in post.get("liked_by",[]); saved=email in post.get("saved_by",[])
    aemail=post.get("author_email",""); ain=post.get("avatar","??"); aname=post.get("author","?")
    g=ugrad(aemail); dt=time_ago(post.get("date","")); views=post.get("views",200)
    ab=post.get("abstract","")
    if compact and len(ab)>200: ab=ab[:200]+"..."
    year=post.get("date","")[:4] if post.get("date") else "—"
    nc=len(post.get("comments",[]))

    author_block=""
    if show_author:
        author_block=f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:.55rem">{avh(ain,32,g)}<div><div style="font-weight:600;font-size:.78rem;color:#CFD8DC">{aname}</div><div style="font-size:.61rem;color:#546E7A">{post.get("area","")} · {dt}</div></div><div style="margin-left:auto">{badge(post["status"])}</div></div>'
    else:
        author_block=f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.35rem"><span style="font-size:.61rem;color:#546E7A">{dt} · {year}</span>{badge(post["status"])}</div>'

    st.markdown(f'''<div class="repo-card">
  {author_block}
  <div style="font-family:'Space Grotesk',sans-serif;font-size:.93rem;font-weight:700;color:#ECEFF1;margin-bottom:.28rem;line-height:1.35">{post["title"]}</div>
  <div style="color:#90A4AE;font-size:.76rem;line-height:1.65;margin-bottom:.45rem">{ab}</div>
  <div style="display:flex;align-items:center;gap:.5rem;flex-wrap:wrap">
    {tags_html(post.get("tags",[]))}
    <span style="color:#546E7A;font-size:.60rem;margin-left:auto">{fmt_num(views)} visualizacoes</span>
  </div>
</div>''',unsafe_allow_html=True)

    heart="curtido" if liked else "curtir"; book="salvo" if saved else "salvar"
    ca,cb,cc,cd,ce=st.columns([1,.8,.65,.65,1.2])
    with ca:
        if st.button(f"{heart} {fmt_num(post['likes'])}",key=f"lk_{ctx}_{pid}",use_container_width=True):
            if liked: post["liked_by"].remove(email); post["likes"]=max(0,post["likes"]-1)
            else: post["liked_by"].append(email); post["likes"]+=1; record(post.get("tags",[]),1.5)
            save_db(); st.rerun()
    with cb:
        if st.button(f"coment. {nc}" if nc else "comentar",key=f"cm_{ctx}_{pid}",use_container_width=True):
            k=f"cmt_{ctx}_{pid}"; st.session_state[k]=not st.session_state.get(k,False); st.rerun()
    with cc:
        if st.button(book,key=f"sv_{ctx}_{pid}",use_container_width=True):
            if saved: post["saved_by"].remove(email)
            else: post["saved_by"].append(email)
            save_db(); st.rerun()
    with cd:
        if st.button("citar",key=f"ct_{ctx}_{pid}",use_container_width=True):
            st.toast(f'{aname} ({year}). {post["title"]}. Nebula.')
    with ce:
        if show_author and aemail:
            if st.button(f"ver perfil: {aname.split()[0]}",key=f"vp_{ctx}_{pid}",use_container_width=True):
                st.session_state.profile_view=aemail; st.rerun()

    if st.session_state.get(f"cmt_{ctx}_{pid}",False):
        for c in post.get("comments",[]):
            ci=ini(c["user"]); ce2=next((e for e,u in st.session_state.users.items() if u.get("name")==c["user"]),""); cg=ugrad(ce2)
            st.markdown(f'<div class="cmt"><div style="display:flex;align-items:center;gap:6px;margin-bottom:.15rem">{avh(ci,22,cg)}<span style="font-size:.71rem;font-weight:700;color:#42A5F5">{c["user"]}</span></div><div style="font-size:.76rem;color:#90A4AE;line-height:1.55;padding-left:28px">{c["text"]}</div></div>',unsafe_allow_html=True)
        nc_txt=st.text_input("",placeholder="Escreva um comentario...",key=f"ci_{ctx}_{pid}",label_visibility="collapsed")
        if st.button("Enviar",key=f"cs_{ctx}_{pid}"):
            if nc_txt: uu=guser(); post["comments"].append({"user":uu.get("name","Voce"),"text":nc_txt}); record(post.get("tags",[]),.8); save_db(); st.rerun()

# ══════════════════════════════════════════════════════════════
#  REPOSITORY — Main page (replaces feed, detailed search)
# ══════════════════════════════════════════════════════════════
def page_repository():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    email=st.session_state.current_user; u=guser(); uname=u.get("name","?"); g=ugrad(email)
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}

    # ─ Header with compose ─
    col_t,col_b=st.columns([3,1])
    with col_t: st.markdown('<h1 style="padding-top:.5rem">Repositorio de Pesquisas</h1>',unsafe_allow_html=True)
    with col_b:
        st.markdown('<br>',unsafe_allow_html=True)
        st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
        if st.button("Nova publicacao",key="btn_np",use_container_width=True): st.session_state.compose_open=not st.session_state.get("compose_open",False); st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)

    # ─ Compose form ─
    co=st.session_state.get("compose_open",False)
    if co:
        st.markdown(f'<div class="compose-box"><div style="display:flex;align-items:center;gap:9px;margin-bottom:.85rem">{avh(ini(uname),36,g)}<div><div style="font-family:Space Grotesk,sans-serif;font-weight:700;font-size:.84rem;color:#ECEFF1">{uname}</div><div style="font-size:.62rem;color:#546E7A">{u.get("area","Pesquisador")}</div></div></div>',unsafe_allow_html=True)
        nt=st.text_input("Titulo da pesquisa *",key="np_t")
        nab=st.text_area("Resumo / Abstract *",key="np_ab",height=100)
        c1c,c2c,c3c=st.columns(3)
        with c1c: ntg=st.text_input("Tags (virgula)",key="np_tg")
        with c2c: nst=st.selectbox("Status",["Em andamento","Publicado","Concluido"],key="np_st")
        with c3c: narea=st.text_input("Area",value=u.get("area",""),key="np_area")
        cp,cc=st.columns([2,1])
        with cp:
            st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
            if st.button("Publicar no repositorio",key="btn_pub",use_container_width=True):
                if not nt or not nab: st.warning("Titulo e resumo sao obrigatorios.")
                else:
                    tags=[t.strip() for t in ntg.split(",") if t.strip()] if ntg else []
                    np2={"id":len(st.session_state.feed_posts)+hash(nt)%99+300,"author":uname,"author_email":email,"avatar":ini(uname),"area":narea or u.get("area",""),"title":nt,"abstract":nab,"tags":tags,"likes":0,"comments":[],"status":nst,"date":datetime.now().strftime("%Y-%m-%d"),"liked_by":[],"saved_by":[],"views":1}
                    st.session_state.feed_posts.insert(0,np2); record(tags,2.0); save_db(); st.session_state.compose_open=False; st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)
        with cc:
            if st.button("Cancelar",key="btn_cc",use_container_width=True): st.session_state.compose_open=False; st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)

    # ─ Two-column layout: filters + results ─
    cf,cm=st.columns([.85,3.2],gap="medium")

    with cf:
        st.markdown('<div class="filter-box">',unsafe_allow_html=True)
        st.markdown('<div class="filter-label">Busca</div>',unsafe_allow_html=True)
        fq=st.text_input("",placeholder="Palavras-chave...",key="repo_q",label_visibility="collapsed")
        st.markdown('</div>',unsafe_allow_html=True)

        st.markdown('<div class="filter-box">',unsafe_allow_html=True)
        st.markdown('<div class="filter-label">Ordenar por</div>',unsafe_allow_html=True)
        fsort=st.radio("",["Recentes","Mais curtidos","Mais vistos","Relevancia"],key="repo_sort",label_visibility="collapsed")
        st.markdown('</div>',unsafe_allow_html=True)

        st.markdown('<div class="filter-box">',unsafe_allow_html=True)
        st.markdown('<div class="filter-label">Status</div>',unsafe_allow_html=True)
        fstatus=st.multiselect("",["Publicado","Em andamento","Concluido"],key="repo_status",label_visibility="collapsed")
        st.markdown('</div>',unsafe_allow_html=True)

        all_areas=sorted(set(p.get("area","") for p in st.session_state.feed_posts if p.get("area","")))
        st.markdown('<div class="filter-box">',unsafe_allow_html=True)
        st.markdown('<div class="filter-label">Area</div>',unsafe_allow_html=True)
        farea=st.multiselect("",all_areas,key="repo_area",label_visibility="collapsed")
        st.markdown('</div>',unsafe_allow_html=True)

        all_tags=sorted(set(t for p in st.session_state.feed_posts for t in p.get("tags",[])))
        st.markdown('<div class="filter-box">',unsafe_allow_html=True)
        st.markdown('<div class="filter-label">Tags</div>',unsafe_allow_html=True)
        ftags=st.multiselect("",all_tags,key="repo_tags",label_visibility="collapsed")
        st.markdown('</div>',unsafe_allow_html=True)

        st.markdown('<div class="filter-box">',unsafe_allow_html=True)
        st.markdown('<div class="filter-label">Visualizar</div>',unsafe_allow_html=True)
        fview=st.radio("",["Todos","Seguidos","Salvos"],key="repo_view",label_visibility="collapsed")
        st.markdown('</div>',unsafe_allow_html=True)

        # Stats sidebar
        all_posts=st.session_state.feed_posts
        st.markdown(f'<div style="font-size:.62rem;color:#546E7A;margin-top:.5rem;line-height:1.9">Total: <strong style="color:#90A4AE">{len(all_posts)}</strong> publicacoes<br>Pesquisadores: <strong style="color:#90A4AE">{len(users)}</strong><br>Areas: <strong style="color:#90A4AE">{len(all_areas)}</strong></div>',unsafe_allow_html=True)

    with cm:
        posts=list(st.session_state.feed_posts)
        # Apply filters
        if fq:
            fql=fq.lower()
            posts=[p for p in posts if fql in p.get("title","").lower() or fql in p.get("abstract","").lower() or any(fql in t.lower() for t in p.get("tags",[]))]
        if fstatus: posts=[p for p in posts if p.get("status") in fstatus]
        if farea: posts=[p for p in posts if p.get("area") in farea]
        if ftags: posts=[p for p in posts if any(t in p.get("tags",[]) for t in ftags)]
        if fview=="Seguidos": posts=[p for p in posts if p.get("author_email") in st.session_state.followed]
        elif fview=="Salvos": posts=[p for p in posts if email in p.get("saved_by",[])]
        # Sort
        if "curtidos" in fsort.lower(): posts=sorted(posts,key=lambda p:p["likes"],reverse=True)
        elif "vistos" in fsort.lower(): posts=sorted(posts,key=lambda p:p.get("views",0),reverse=True)
        elif "relevancia" in fsort.lower() and fq:
            def rel_sc(p):
                fql_r=fq.lower(); s=0
                if fql_r in p.get("title","").lower(): s+=3
                if fql_r in p.get("abstract","").lower(): s+=1
                s+=sum(1 for t in p.get("tags",[]) if fql_r in t.lower())*2
                return s
            posts=sorted(posts,key=rel_sc,reverse=True)
        else: posts=sorted(posts,key=lambda p:p.get("date",""),reverse=True)
        # Count
        st.markdown(f'<div style="font-size:.68rem;color:#546E7A;margin-bottom:.55rem">{len(posts)} resultado(s)</div>',unsafe_allow_html=True)
        if not posts:
            st.markdown('<div class="card" style="padding:3rem;text-align:center;color:#546E7A">Nenhuma publicacao encontrada com os filtros selecionados.</div>',unsafe_allow_html=True)
        else:
            for p in posts: render_repo_card(p,ctx="repo")

    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  ARTICLE CARD (web results)
# ══════════════════════════════════════════════════════════════
def render_article(a, idx=0, ctx="web"):
    sc=CHART_C[1] if a.get("origin")=="semantic" else CHART_C[2]
    sn="Semantic Scholar" if a.get("origin")=="semantic" else "CrossRef"
    cite=f" · {a['citations']} citacoes" if a.get("citations") else ""
    uid=re.sub(r'[^a-zA-Z0-9]','',f"{ctx}_{idx}_{str(a.get('doi',''))[:10]}")[:32]
    is_saved=any(s.get('doi')==a.get('doi') for s in st.session_state.saved_articles)
    ab=(a.get("abstract","") or "")[:280]+("..." if len(a.get("abstract",""))>280 else "")
    st.markdown(f'<div class="scard"><div style="display:flex;align-items:flex-start;gap:7px;margin-bottom:.25rem"><div style="flex:1;font-family:Space Grotesk,sans-serif;font-size:.84rem;font-weight:700;color:#ECEFF1">{a["title"]}</div><span style="font-size:.56rem;color:{sc};background:rgba(255,255,255,.03);border-radius:6px;padding:2px 6px;white-space:nowrap;flex-shrink:0">{sn}</span></div><div style="color:#546E7A;font-size:.63rem;margin-bottom:.27rem">{a["authors"]} · <em>{a["source"]}</em> · {a["year"]}{cite}</div><div style="color:#90A4AE;font-size:.74rem;line-height:1.60">{ab}</div></div>',unsafe_allow_html=True)
    ca,cb,cc=st.columns(3)
    with ca:
        st.markdown(f'<div class="{"btn-success" if is_saved else ""}">',unsafe_allow_html=True)
        if st.button("salvo" if is_saved else "salvar",key=f"svw_{uid}"):
            if is_saved: st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]; st.toast("Removido")
            else: st.session_state.saved_articles.append(a); st.toast("Salvo!")
            save_db(); st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)
    with cb:
        if st.button("citar",key=f"ctw_{uid}"): st.toast(f'{a["authors"]} ({a["year"]}). {a["title"]}.')
    with cc:
        if a.get("url"): st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:#42A5F5;font-size:.76rem;text-decoration:none;line-height:2.4;display:block">abrir artigo</a>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  SEARCH + VISION AI (merged page)
# ══════════════════════════════════════════════════════════════
def page_search():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.5rem;margin-bottom:.8rem">Busca e Analise de Imagem</h1>',unsafe_allow_html=True)
    has_key=bool(get_api_key() and get_api_key().startswith("sk-"))

    tab_search,tab_vision=st.tabs(["  Busca Academica  ","  Analise de Imagem com IA  "])

    # ─── TEXT SEARCH ───
    with tab_search:
        c1,c2=st.columns([4,1])
        with c1: q=st.text_input("",placeholder="Buscar em Nebula, Semantic Scholar, CrossRef...",key="sq",label_visibility="collapsed")
        with c2:
            st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
            if st.button("Buscar",key="btn_s",use_container_width=True):
                if q:
                    with st.spinner("Buscando..."):
                        nr=[p for p in st.session_state.feed_posts if q.lower() in p.get("title","").lower() or q.lower() in p.get("abstract","").lower()]
                        sr=search_ss(q,8); cr=search_cr(q,4)
                        st.session_state.search_results={"nebula":nr,"ss":sr,"cr":cr}; st.session_state.last_sq=q; record([q.lower()],.3)
            st.markdown('</div>',unsafe_allow_html=True)

        # Advanced search options
        with st.expander("Filtros avancados"):
            ca2,cb2,cc2=st.columns(3)
            with ca2: year_from=st.number_input("Ano (de)",2000,2026,2020,key="year_from")
            with cb2: year_to=st.number_input("Ano (ate)",2000,2026,2026,key="year_to")
            with cc2: min_cit=st.number_input("Min. citacoes",0,10000,0,key="min_cit")
            src_filter=st.multiselect("Fontes",["Nebula","Semantic Scholar","CrossRef"],default=["Nebula","Semantic Scholar","CrossRef"],key="src_filter")

        if st.session_state.get("search_results") and st.session_state.get("last_sq"):
            res=st.session_state.search_results; neb=res.get("nebula",[]); ss=res.get("ss",[]); cr=res.get("cr",[])
            web=ss+[x for x in cr if not any(x["title"].lower()==s["title"].lower() for s in ss)]
            # Filter by sources
            if "Semantic Scholar" not in src_filter: web=[x for x in web if x.get("origin")!="semantic"]
            if "CrossRef" not in src_filter: web=[x for x in web if x.get("origin")!="crossref"]
            if "Nebula" not in src_filter: neb=[]
            # Filter by year and citations
            web=[a for a in web if (not a.get("year") or str(a.get("year","0")).isdigit() and year_from<=int(a.get("year",2026))<=year_to) and a.get("citations",0)>=min_cit]
            total=len(neb)+len(web)
            st.markdown(f'<div style="color:#546E7A;font-size:.68rem;margin-bottom:.55rem">{total} resultado(s) para "{st.session_state.last_sq}"</div>',unsafe_allow_html=True)
            ta,tn,tw=st.tabs([f"  Todos ({total})  ",f"  Nebula ({len(neb)})  ",f"  Internet ({len(web)})  "])
            with ta:
                if neb:
                    st.markdown('<div style="font-size:.57rem;color:#42A5F5;font-weight:700;margin-bottom:.38rem;letter-spacing:.09em;text-transform:uppercase">No repositorio Nebula</div>',unsafe_allow_html=True)
                    for p in neb: render_repo_card(p,ctx="srch_all",compact=True)
                if web:
                    if neb: st.markdown('<hr>',unsafe_allow_html=True)
                    for idx,a in enumerate(web): render_article(a,idx=idx,ctx="all_w")
                if not neb and not web: st.info("Nenhum resultado.")
            with tn:
                for p in neb: render_repo_card(p,ctx="srch_neb",compact=True)
                if not neb: st.info("Nenhuma publicacao.")
            with tw:
                for idx,a in enumerate(web): render_article(a,idx=idx,ctx="web_t")
                if not web: st.info("Nenhum artigo.")
        else:
            # Trending tags
            tag_count=Counter(t for p in st.session_state.feed_posts for t in p.get("tags",[]))
            st.markdown('<div class="dtxt">Topicos em destaque</div>',unsafe_allow_html=True)
            st.markdown('<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:.8rem">'+''.join(f'<span class="tag" style="cursor:pointer;font-size:.68rem">{t} <span style="color:#546E7A">({c})</span></span>' for t,c in tag_count.most_common(16))+'</div>',unsafe_allow_html=True)

    # ─── VISION AI ───
    with tab_vision:
        if has_key:
            st.markdown('<div style="background:rgba(21,101,192,.06);border:1px solid rgba(30,136,229,.18);border-radius:12px;padding:.7rem 1rem;margin-bottom:.7rem"><div style="font-size:.76rem;color:#42A5F5;font-weight:600">Claude Vision ativo — Analise real com IA habilitada</div></div>',unsafe_allow_html=True)
        else:
            st.markdown('<div style="background:rgba(255,152,0,.05);border:1px solid rgba(255,152,0,.14);border-radius:12px;padding:.7rem 1rem;margin-bottom:.7rem"><div style="font-size:.73rem;color:#FFB74D;font-weight:600">Modo ML — Insira API key na sidebar para ativar Claude Vision</div></div>',unsafe_allow_html=True)

        cu,cr2=st.columns([1,2])
        with cu:
            st.markdown('<div class="card" style="padding:1rem">',unsafe_allow_html=True)
            img_file=st.file_uploader("Carregar imagem cientifica",type=["png","jpg","jpeg","webp","tiff"],key="img_up")
            img_bytes=None
            if img_file: img_bytes=img_file.read(); st.image(img_bytes,use_container_width=True)
            st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
            run_ml=st.button("Analisar (ML rapido)",key="btn_run",use_container_width=True)
            st.markdown('</div>',unsafe_allow_html=True)
            if img_bytes and has_key:
                if st.button("Analisar com Claude AI",key="btn_vision",use_container_width=True):
                    st.session_state["run_vision"]=True
            st.markdown('<div style="margin-top:.7rem;background:rgba(239,83,80,.04);border:1px solid rgba(239,83,80,.10);border-radius:9px;padding:.55rem"><div style="font-size:.60rem;color:#EF9A9A;font-weight:600;margin-bottom:2px">Aviso</div><div style="font-size:.58rem;color:#90A4AE;line-height:1.6">Analise computacional para fins de pesquisa. Valide com especialistas.</div></div>',unsafe_allow_html=True)
            st.markdown('</div>',unsafe_allow_html=True)

        with cr2:
            # Run ML
            if run_ml and img_bytes:
                with st.spinner("Executando pipeline ML..."):
                    ml=analyze_image_ml(img_bytes)
                st.session_state.img_result=ml
                st.session_state.claude_vision_result=None

            # Run Claude Vision
            if st.session_state.get("run_vision") and img_bytes:
                st.session_state["run_vision"]=False
                with st.spinner("Claude analisando imagem em detalhe..."):
                    txt,err=call_claude([],system=VISION_SYSTEM,max_tokens=1800,img_bytes=img_bytes)
                if txt:
                    try:
                        clean=re.sub(r'^```json\s*','',txt.strip()); clean=re.sub(r'\s*```$','',clean)
                        st.session_state.claude_vision_result=json.loads(clean)
                    except: st.session_state.claude_vision_result={"raw":txt}
                elif err: st.error(f"Erro: {err}")

            # Show Claude Vision result (detailed)
            cv_r=st.session_state.get("claude_vision_result")
            if cv_r:
                if "raw" in cv_r:
                    st.markdown(f'<div class="vision-header"><div style="font-size:.60rem;color:#42A5F5;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin-bottom:.45rem">Analise Claude Vision</div><div style="font-size:.80rem;color:#90A4AE;white-space:pre-wrap;line-height:1.7">{cv_r["raw"][:2000]}</div></div>',unsafe_allow_html=True)
                else:
                    tipo=cv_r.get("tipo_imagem","—"); area_c=cv_r.get("area_cientifica","—")
                    conf=cv_r.get("confianca",0); conf_c="#66BB6A" if conf>80 else("#42A5F5" if conf>60 else "#FF9800")
                    st.markdown(f'''<div class="vision-header">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:.7rem">
    <div>
      <div style="font-size:.55rem;color:#42A5F5;letter-spacing:.09em;text-transform:uppercase;font-weight:700;margin-bottom:3px">Claude Vision — Analise Completa</div>
      <div style="font-family:'Space Grotesk',sans-serif;font-size:1.08rem;font-weight:800;color:#ECEFF1;margin-bottom:3px">{tipo}</div>
      <div style="color:#26C6DA;font-size:.78rem;font-weight:600">{area_c}</div>
    </div>
    <div style="background:rgba(0,0,0,.3);border-radius:10px;padding:.45rem .80rem;text-align:center;flex-shrink:0">
      <div style="font-family:'Space Grotesk',sans-serif;font-size:1.35rem;font-weight:900;color:{conf_c}">{conf}%</div>
      <div style="font-size:.50rem;color:#546E7A;text-transform:uppercase">confianca</div>
    </div>
  </div>
</div>''',unsafe_allow_html=True)

                    # Detailed sections
                    sections=[
                        ("O que esta imagem representa",cv_r.get("o_que_representa","")),
                        ("Composicao e materiais",cv_r.get("composicao","")),
                        ("Tecnica experimental",cv_r.get("tecnica_detalhada","")),
                        ("Parametros e escala visiveis",cv_r.get("parametros_visiveis","")),
                        ("Significancia cientifica",cv_r.get("significancia_cientifica","")),
                        ("Interpretacao dos resultados",cv_r.get("interpretacao_resultados","")),
                        ("Anomalias e artefatos",cv_r.get("anomalias_artefatos","")),
                        ("Aplicacoes desta pesquisa",cv_r.get("aplicacoes","")),
                        ("Limitacoes da analise",cv_r.get("limitacoes","")),
                        ("Contexto historico",cv_r.get("contexto_historico","")),
                    ]
                    for title,content in sections:
                        if content and content!="—" and len(content)>4:
                            st.markdown(f'<div class="vision-section"><div style="font-size:.60rem;color:#546E7A;font-weight:700;letter-spacing:.09em;text-transform:uppercase;margin-bottom:.28rem">{title}</div><div style="font-size:.78rem;color:#CFD8DC;line-height:1.72">{content}</div></div>',unsafe_allow_html=True)

                    # Structures
                    ests=cv_r.get("estruturas_observadas",[])
                    if ests:
                        st.markdown('<div style="font-size:.60rem;color:#546E7A;font-weight:700;letter-spacing:.09em;text-transform:uppercase;margin-bottom:.35rem">Estruturas identificadas</div>',unsafe_allow_html=True)
                        for est in ests:
                            if isinstance(est,dict):
                                st.markdown(f'<div class="vision-detail"><div style="font-weight:700;font-size:.78rem;color:#90CAF9;margin-bottom:.15rem">{est.get("nome","")}</div><div style="font-size:.74rem;color:#90A4AE;line-height:1.6">{est.get("descricao","")} <span style="color:#546E7A">{est.get("localizacao","")}</span></div></div>',unsafe_allow_html=True)
                            else:
                                st.markdown(f'<div class="vision-detail"><div style="font-size:.76rem;color:#90A4AE">{est}</div></div>',unsafe_allow_html=True)

                    # Search related articles
                    termos=cv_r.get("termos_busca_en","")
                    qual=cv_r.get("qualidade_tecnica","—")
                    st.markdown(f'<div style="display:flex;gap:.4rem;flex-wrap:wrap;margin:.55rem 0"><span class="badge-b">qualidade: {qual}</span><span class="badge-g">confianca: {conf}%</span></div>',unsafe_allow_html=True)
                    if termos:
                        st.markdown(f'<div style="font-size:.62rem;color:#546E7A;margin:.4rem 0">Buscando artigos relacionados: <em>{termos[:80]}</em></div>',unsafe_allow_html=True)
                        with st.spinner("Buscando literatura..."):
                            wr=search_ss(termos,6)
                        if wr:
                            st.markdown('<div class="dtxt">Artigos relacionados</div>',unsafe_allow_html=True)
                            for idx2,a2 in enumerate(wr): render_article(a2,idx=idx2+5000,ctx="img_claude")

            # Show ML result
            ml_r=st.session_state.get("img_result",{})
            if ml_r and ml_r.get("ok") and not cv_r:
                cls_=ml_r["classification"] if "classification" in ml_r else {}
                cat=ml_r.get("category","—"); conf2=ml_r.get("confidence",0)
                conf_c2="#66BB6A" if conf2>80 else("#42A5F5" if conf2>60 else "#FF9800")
                st.markdown(f'<div class="ai-box"><div style="display:flex;justify-content:space-between;align-items:flex-start"><div><div style="font-size:.58rem;color:#42A5F5;font-weight:700;letter-spacing:.09em;text-transform:uppercase;margin-bottom:3px">Classificacao ML</div><div style="font-family:Space Grotesk,sans-serif;font-size:1.05rem;font-weight:800;color:#ECEFF1">{cat}</div></div><div style="background:rgba(0,0,0,.3);border-radius:10px;padding:.45rem .75rem;text-align:center"><div style="font-family:Space Grotesk,sans-serif;font-size:1.3rem;font-weight:900;color:{conf_c2}">{conf2}%</div><div style="font-size:.50rem;color:#546E7A;text-transform:uppercase">confianca</div></div></div></div>',unsafe_allow_html=True)
                c1m,c2m,c3m,c4m=st.columns(4)
                ed=ml_r.get("edges",{}); fft=ml_r.get("fft",{})
                with c1m: st.markdown(f'<div class="stat-box"><div class="mval">{ed.get("mean",0):.3f}</div><div class="mlbl">Borda Sobel</div></div>',unsafe_allow_html=True)
                with c2m: st.markdown(f'<div class="stat-box"><div class="mval-g">{"sim" if fft.get("periodic") else "nao"}</div><div class="mlbl">Periodico FFT</div></div>',unsafe_allow_html=True)
                with c3m: st.markdown(f'<div class="stat-box"><div class="mval-y">{ml_r.get("entropy",0):.2f}</div><div class="mlbl">Entropia</div></div>',unsafe_allow_html=True)
                with c4m: st.markdown(f'<div class="stat-box"><div class="mval-c">{ml_r.get("symmetry",0):.2f}</div><div class="mlbl">Simetria</div></div>',unsafe_allow_html=True)

                t1,t2,t3=st.tabs(["  Categorias  ","  RGB/Histograma  ","  FFT/Frequencias  "])
                with t1:
                    scores=ml_r.get("all_scores",{})
                    if scores:
                        fig_s=go.Figure(go.Bar(x=list(scores.values()),y=list(scores.keys()),orientation='h',marker=dict(color=CHART_C[:len(scores)]),text=[f"{v:.0f}pt" for v in scores.values()],textposition="outside",textfont=dict(color="#546E7A",size=9)))
                        fig_s.update_layout(**{**pc_dark(),'height':220,'title':dict(text="Pontuacao por categoria",font=dict(color="#CFD8DC",family="Space Grotesk",size=11)),'xaxis':dict(showgrid=True,gridcolor="rgba(255,255,255,.04)")})
                        st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_s,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
                with t2:
                    hd=ml_r.get("histograms",{}); bx=list(range(0,256,8))[:32]
                    if hd:
                        fig4=go.Figure()
                        fig4.add_trace(go.Scatter(x=bx,y=hd.get("r",[])[:32],fill='tozeroy',name='R',line=dict(color='rgba(239,83,80,.9)',width=1.5),fillcolor='rgba(239,83,80,.09)'))
                        fig4.add_trace(go.Scatter(x=bx,y=hd.get("g",[])[:32],fill='tozeroy',name='G',line=dict(color='rgba(102,187,106,.9)',width=1.5),fillcolor='rgba(102,187,106,.09)'))
                        fig4.add_trace(go.Scatter(x=bx,y=hd.get("b",[])[:32],fill='tozeroy',name='B',line=dict(color='rgba(66,165,245,.9)',width=1.5),fillcolor='rgba(66,165,245,.09)'))
                        fig4.update_layout(**{**pc_dark(),'height':200,'title':dict(text="Histograma RGB",font=dict(color="#CFD8DC",family="Space Grotesk",size=11)),'legend':dict(font=dict(color="#546E7A",size=9))})
                        st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig4,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
                    col_=ml_r.get("color",{}); hex_m="#{:02x}{:02x}{:02x}".format(int(col_.get("r",128)),int(col_.get("g",128)),int(col_.get("b",128)))
                    temp="Quente" if col_.get("warm") else("Fria" if col_.get("cool") else "Neutra")
                    st.markdown(f'<div class="ml-metric">Cor media: <strong style="color:#ECEFF1">{hex_m}</strong> · Temperatura: <strong style="color:#ECEFF1">{temp}</strong> · Brilho: <strong style="color:#ECEFF1">{ml_r.get("brightness",0):.0f}/255</strong></div>',unsafe_allow_html=True)
                with t3:
                    fft2=ml_r.get("fft",{}); lf=fft2.get("lf",0); mf=fft2.get("mf",0); hf_v=fft2.get("hf",0)
                    fig_f=go.Figure(go.Bar(x=["Baixa (estruturas grandes)","Media (detalhes)","Alta (textura/ruido)"],y=[lf,mf,hf_v],marker=dict(color=[CHART_C[0],CHART_C[1],CHART_C[2]]),text=[f"{v:.3f}" for v in [lf,mf,hf_v]],textposition="outside",textfont=dict(color="#546E7A",size=9)))
                    fig_f.update_layout(**{**pc_dark(),'height':200,'title':dict(text="FFT — Distribuicao de frequencias",font=dict(color="#CFD8DC",family="Space Grotesk",size=11))})
                    st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_f,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
                    st.markdown(f'<div class="ml-metric">Score periodico: <strong style="color:#ECEFF1">{fft2.get("score",0):.1f}</strong> · Estrutura: <strong style="color:#ECEFF1">{"Periodica" if fft2.get("periodic") else "Aperiodica"}</strong></div>',unsafe_allow_html=True)

                # Related search
                skw={"Histopatologia H&E":"hematoxylin eosin staining histopathology tissue","Fluorescencia Nuclear DAPI":"DAPI nuclear staining fluorescence microscopy","Fluorescencia GFP":"GFP green fluorescent protein confocal","Cristalografia/Difracao":"X-ray diffraction crystallography crystal structure","Gel/Western Blot":"western blot gel electrophoresis protein","Grafico/Diagrama":"scientific data visualization","Estrutura Molecular":"molecular structure visualization","Microscopia Confocal":"confocal microscopy fluorescence","Imagem Astronomica":"astronomy telescope observation","Imagem Cientifica Geral":"scientific imaging microscopy"}.get(cat,"scientific imaging")
                ck=f"img_{skw[:30]}_{cat[:10]}"
                if ck not in st.session_state.scholar_cache:
                    with st.spinner("Buscando artigos relacionados..."): st.session_state.scholar_cache[ck]=search_ss(skw,5)
                wr3=st.session_state.scholar_cache.get(ck,[])
                if wr3:
                    st.markdown('<div class="dtxt">Literatura relacionada</div>',unsafe_allow_html=True)
                    for idx3,a3 in enumerate(wr3): render_article(a3,idx=idx3+3000,ctx="img_ml")
            elif not img_file and not cv_r:
                st.markdown('<div class="card" style="padding:4rem 2rem;text-align:center"><div style="font-family:Space Grotesk,sans-serif;font-size:1rem;color:#CFD8DC;margin-bottom:.45rem">Analise de Imagem Cientifica</div><div style="font-size:.75rem;color:#546E7A;line-height:2">Pipeline ML: Sobel · FFT · RGB · Classificacao<br>Com API key: analise completa com Claude Vision<br><br>Carregue uma imagem para comecar</div></div>',unsafe_allow_html=True)

    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  KNOWLEDGE — AI Connections + 3D Network
# ══════════════════════════════════════════════════════════════
def page_knowledge():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.5rem;margin-bottom:.8rem">Rede de Conexoes</h1>',unsafe_allow_html=True)
    email=st.session_state.current_user; users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    has_key=bool(get_api_key() and get_api_key().startswith("sk-"))

    def get_tags(ue):
        ud=users.get(ue,{}); tags=set(w for w in ud.get("area","").lower().split() if len(w)>3)
        for p in st.session_state.feed_posts:
            if p.get("author_email")==ue: tags.update(t.lower() for t in p.get("tags",[]))
        return tags

    rlist=list(users.keys()); n=len(rlist)
    rtags={ue:get_tags(ue) for ue in rlist}
    edges=[]
    for i in range(n):
        for j in range(i+1,n):
            e1,e2=rlist[i],rlist[j]; common=list(rtags[e1]&rtags[e2])
            is_fol=e2 in st.session_state.followed or e1 in st.session_state.followed
            if common or is_fol: edges.append((e1,e2,common[:5],len(common)+(2 if is_fol else 0)))

    pos={}
    for idx,ue in enumerate(rlist):
        angle=2*3.14159*idx/max(n,1); rd=0.36+0.05*((hash(ue)%5)/4)
        pos[ue]={"x":0.5+rd*np.cos(angle),"y":0.5+rd*np.sin(angle),"z":0.5+0.12*((idx%4)/3-.35)}
    fig=go.Figure()
    for e1,e2,common,strength in edges:
        p1=pos[e1]; p2=pos[e2]; alpha=min(0.42,0.07+strength*0.06)
        fig.add_trace(go.Scatter3d(x=[p1["x"],p2["x"],None],y=[p1["y"],p2["y"],None],z=[p1["z"],p2["z"],None],
            mode="lines",line=dict(color=f"rgba(30,136,229,{alpha:.2f})",width=min(3,1+strength)),hoverinfo="none",showlegend=False))
    ncolors=[("#1E88E5" if ue==email else("#66BB6A" if ue in st.session_state.followed else "#00BCD4")) for ue in rlist]
    nsizes=[22 if ue==email else(16 if ue in st.session_state.followed else 11) for ue in rlist]
    fig.add_trace(go.Scatter3d(x=[pos[ue]["x"] for ue in rlist],y=[pos[ue]["y"] for ue in rlist],z=[pos[ue]["z"] for ue in rlist],
        mode="markers+text",marker=dict(size=nsizes,color=ncolors,opacity=.9,line=dict(color="rgba(255,255,255,.07)",width=1.5)),
        text=[users.get(ue,{}).get("name","?").split()[0] for ue in rlist],textposition="top center",
        textfont=dict(color="#546E7A",size=9,family="Inter"),
        hovertemplate=[f"<b>{users.get(ue,{}).get('name','?')}</b><br>{users.get(ue,{}).get('area','')}<extra></extra>" for ue in rlist],showlegend=False))
    fig.update_layout(height=390,scene=dict(xaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),yaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),zaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),bgcolor="rgba(0,0,0,0)"),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig,use_container_width=True)

    c1,c2,c3,c4=st.columns(4)
    for col,(v,l) in zip([c1,c2,c3,c4],[(len(rlist),"Pesquisadores"),(len(edges),"Conexoes"),(len(st.session_state.followed),"Seguindo"),(len(st.session_state.feed_posts),"Publicacoes")]):
        with col: st.markdown(f'<div class="stat-box"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>',unsafe_allow_html=True)
    st.markdown("<hr>",unsafe_allow_html=True)

    tm,tai,tmi,tall=st.tabs(["  Mapa de Conexoes  ","  Sugestoes IA  ","  Minhas Conexoes  ","  Todos  "])

    with tm:
        for e1,e2,common,strength in sorted(edges,key=lambda x:-x[3])[:20]:
            n1=users.get(e1,{}); n2=users.get(e2,{})
            ts=tags_html(common[:4]) if common else '<span style="color:#546E7A;font-size:.64rem">por seguimento</span>'
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:7px;flex-wrap:wrap"><span style="font-size:.77rem;font-weight:700;font-family:Space Grotesk,sans-serif;color:#42A5F5">{n1.get("name","?")}</span><span style="color:#546E7A">—</span><span style="font-size:.77rem;font-weight:700;font-family:Space Grotesk,sans-serif;color:#42A5F5">{n2.get("name","?")}</span><div style="flex:1">{ts}</div><span style="font-size:.62rem;color:#66BB6A;font-weight:700">{strength}pt</span></div></div>',unsafe_allow_html=True)

    with tai:
        st.markdown('<div class="ai-box"><div style="font-family:Space Grotesk,sans-serif;font-weight:700;font-size:.86rem;margin-bottom:.25rem;color:#42A5F5">Sugestoes Inteligentes de Conexao</div><div style="font-size:.72rem;color:#90A4AE;line-height:1.65">Claude AI analisa seu perfil e pesquisas para sugerir colaboracoes cientificas ideais</div></div>',unsafe_allow_html=True)
        if not has_key:
            my_tags=rtags.get(email,set())
            st.markdown('<div style="font-size:.68rem;color:#FFB74D;margin-bottom:.5rem">Modo algoritmico — insira API key para IA real</div>',unsafe_allow_html=True)
            for ue,ud in list(users.items())[:8]:
                if ue==email or ue in st.session_state.followed: continue
                common_tags=my_tags&rtags.get(ue,set())
                if not common_tags: continue
                rn=ud.get("name","?"); rg=ugrad(ue)
                st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:9px;margin-bottom:.4rem">{avh(ini(rn),32,rg)}<div style="flex:1"><div style="font-weight:700;font-size:.82rem;color:#ECEFF1">{rn}</div><div style="font-size:.63rem;color:#546E7A">{ud.get("area","")}</div></div><span class="badge-g">{len(common_tags)} temas comuns</span></div><div style="margin-bottom:.35rem">{tags_html(list(common_tags)[:4])}</div></div>',unsafe_allow_html=True)
                cf2,cv2=st.columns(2)
                with cf2:
                    if st.button(f"Seguir {rn.split()[0]}",key=f"ais_{ue}",use_container_width=True):
                        if ue not in st.session_state.followed: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                        save_db(); st.rerun()
                with cv2:
                    if st.button("Ver perfil",key=f"aip_{ue}",use_container_width=True): st.session_state.profile_view=ue; st.rerun()
        else:
            ck=f"conn_{email}_{len(users)}_{len(st.session_state.feed_posts)}"
            st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
            if st.button("Gerar sugestoes com IA",key="btn_ai_conn"):
                u2=users.get(email,{}); my_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==email]
                others=[{"email":ue,"name":ud.get("name",""),"area":ud.get("area",""),"tags":list({t for p in st.session_state.feed_posts if p.get("author_email")==ue for t in p.get("tags",[])})[:6]} for ue,ud in users.items() if ue!=email]
                payload={"meu_perfil":{"area":u2.get("area",""),"bio":u2.get("bio",""),"tags":list({t for p in my_posts for t in p.get("tags",[])})[:8]},"pesquisadores":others[:12]}
                prompt=f"""Voce e um sistema de recomendacao cientifica. Sugira 4 melhores conexoes baseado nos dados.
Dados: {json.dumps(payload,ensure_ascii=False)}
Responda APENAS JSON puro: {{"sugestoes":[{{"email":"<email>","razao":"<justificativa 1-2 frases>","score":<0-100>,"temas_comuns":["<t1>","<t2>"]}}]}}"""
                with st.spinner("Analisando rede cientifica..."):
                    txt,err=call_claude([prompt],max_tokens=600)
                if txt:
                    try:
                        clean=re.sub(r'^```json\s*','',txt.strip()); clean=re.sub(r'\s*```$','',clean)
                        st.session_state.ai_conn_cache[ck]=json.loads(clean)
                    except: st.error("Erro ao processar resposta IA")
                elif err: st.error(f"Erro: {err}")
            st.markdown('</div>',unsafe_allow_html=True)
            ai_r=st.session_state.ai_conn_cache.get(ck)
            if ai_r:
                for sug in ai_r.get("sugestoes",[]):
                    sue=sug.get("email",""); sud=users.get(sue,{})
                    if not sud: continue
                    rn=sud.get("name","?"); rg=ugrad(sue); score=sug.get("score",70)
                    sc_c="#66BB6A" if score>=80 else("#42A5F5" if score>=60 else "#FF9800")
                    is_fol2=sue in st.session_state.followed
                    st.markdown(f'''<div class="ai-box">
  <div style="display:flex;align-items:center;gap:9px;margin-bottom:.5rem">
    {avh(ini(rn),36,rg)}
    <div style="flex:1"><div style="font-family:Space Grotesk,sans-serif;font-weight:700;font-size:.84rem;color:#ECEFF1">{rn}</div><div style="font-size:.63rem;color:#546E7A">{sud.get("area","")}</div></div>
    <div style="background:rgba(0,0,0,.3);border-radius:9px;padding:.35rem .6rem;text-align:center;flex-shrink:0"><div style="font-family:Space Grotesk,sans-serif;font-size:1.1rem;font-weight:900;color:{sc_c}">{score}</div><div style="font-size:.49rem;color:#546E7A;text-transform:uppercase">score IA</div></div>
  </div>
  <div style="background:rgba(30,136,229,.05);border:1px solid rgba(30,136,229,.10);border-radius:8px;padding:.48rem .7rem;margin-bottom:.42rem;font-size:.74rem;color:#90A4AE;line-height:1.65">{sug.get("razao","Conexao recomendada")}</div>
  <div>{tags_html(sug.get("temas_comuns",[])[:5])}</div>
</div>''',unsafe_allow_html=True)
                    c_f,c_p,c_c=st.columns(3)
                    with c_f:
                        st.markdown(f'<div class="{"btn-success" if is_fol2 else "btn-primary"}">',unsafe_allow_html=True)
                        if st.button("Seguindo" if is_fol2 else "Seguir",key=f"aic_f_{sue}",use_container_width=True):
                            if not is_fol2: st.session_state.followed.append(sue); sud["followers"]=sud.get("followers",0)+1
                            save_db(); st.rerun()
                        st.markdown('</div>',unsafe_allow_html=True)
                    with c_p:
                        if st.button("Perfil",key=f"aic_p_{sue}",use_container_width=True): st.session_state.profile_view=sue; st.rerun()
                    with c_c:
                        if st.button("Chat",key=f"aic_c_{sue}",use_container_width=True):
                            st.session_state.chat_messages.setdefault(sue,[]); st.session_state.active_chat=sue; st.session_state.page="chat"; st.rerun()
            else:
                st.markdown('<div style="text-align:center;padding:2rem;color:#546E7A">Clique para gerar sugestoes com IA.</div>',unsafe_allow_html=True)

    with tmi:
        mc=[(e1,e2,c,s) for e1,e2,c,s in edges if e1==email or e2==email]
        for e1,e2,common,strength in sorted(mc,key=lambda x:-x[3]):
            oth=e2 if e1==email else e1; od=users.get(oth,{}); og=ugrad(oth)
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:9px">{avh(ini(od.get("name","?")),32,og)}<div style="flex:1"><div style="font-weight:700;font-size:.80rem;color:#ECEFF1">{od.get("name","?")}</div><div style="font-size:.63rem;color:#546E7A">{od.get("area","")}</div></div>{tags_html(common[:3])}</div></div>',unsafe_allow_html=True)
            cv,cm2,_=st.columns([1,1,4])
            with cv:
                if st.button("Perfil",key=f"kv_{oth}",use_container_width=True): st.session_state.profile_view=oth; st.rerun()
            with cm2:
                if st.button("Chat",key=f"kc_{oth}",use_container_width=True):
                    st.session_state.chat_messages.setdefault(oth,[]); st.session_state.active_chat=oth; st.session_state.page="chat"; st.rerun()
        if not mc: st.info("Siga pesquisadores e publique pesquisas para criar conexoes.")

    with tall:
        sq2=st.text_input("",placeholder="Buscar pesquisador...",key="all_s",label_visibility="collapsed")
        for ue,ud in users.items():
            if ue==email: continue
            rn=ud.get("name","?"); ua=ud.get("area","")
            if sq2 and sq2.lower() not in rn.lower() and sq2.lower() not in ua.lower(): continue
            is_fol=ue in st.session_state.followed; rg=ugrad(ue)
            bolsa_ud=ud.get("bolsa","")
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:9px">{avh(ini(rn),32,rg)}<div style="flex:1"><div style="font-size:.80rem;font-weight:700;color:#ECEFF1">{rn}</div><div style="font-size:.63rem;color:#546E7A">{ua}{" · "+bolsa_ud if bolsa_ud else ""}</div></div></div></div>',unsafe_allow_html=True)
            ca2,cb2,cc2=st.columns(3)
            with ca2:
                if st.button("Perfil",key=f"av_{ue}",use_container_width=True): st.session_state.profile_view=ue; st.rerun()
            with cb2:
                st.markdown(f'<div class="{"btn-success" if is_fol else "btn-primary"}">',unsafe_allow_html=True)
                if st.button("Seguindo" if is_fol else "Seguir",key=f"af_{ue}",use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"]=max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                    save_db(); st.rerun()
                st.markdown('</div>',unsafe_allow_html=True)
            with cc2:
                if st.button("Chat",key=f"ac_{ue}",use_container_width=True):
                    st.session_state.chat_messages.setdefault(ue,[]); st.session_state.active_chat=ue; st.session_state.page="chat"; st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  FOLDERS + ALL ANALYTICS (pastas + todos os graficos)
# ══════════════════════════════════════════════════════════════
def page_folders():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.5rem;margin-bottom:.9rem">Pastas e Analises</h1>',unsafe_allow_html=True)
    email=st.session_state.current_user; u=guser(); ra=u.get("area","")

    tf,ta,ti,tt=st.tabs(["  Pastas  ","  Analise de Documentos  ","  Interesses  ","  Tendencias  "])

    # ─── PASTAS ───
    with tf:
        c1,c2,_=st.columns([2,1.2,1.5])
        with c1: nfn=st.text_input("Nome da pasta",placeholder="Ex: Genomica Comparativa",key="nf_n")
        with c2: nfd=st.text_input("Descricao",key="nf_d")
        st.markdown('<div class="btn-primary" style="display:inline-block">',unsafe_allow_html=True)
        if st.button("Criar pasta",key="btn_nf"):
            if nfn.strip():
                if nfn not in st.session_state.folders: st.session_state.folders[nfn]={"desc":nfd,"files":[],"notes":"","analyses":{}}; save_db(); st.success(f"'{nfn}' criada!"); st.rerun()
                else: st.warning("Ja existe.")
            else: st.warning("Digite um nome.")
        st.markdown('</div>',unsafe_allow_html=True)
        st.markdown("<hr>",unsafe_allow_html=True)
        if not st.session_state.folders:
            st.markdown('<div class="card" style="text-align:center;padding:4rem;color:#546E7A">Nenhuma pasta criada ainda.</div>',unsafe_allow_html=True)
        else:
            # Summary grid
            cols=st.columns(min(3,len(st.session_state.folders)))
            for idx,(fn,fd) in enumerate(st.session_state.folders.items()):
                if not isinstance(fd,dict): fd={"files":fd,"desc":"","notes":"","analyses":{}}; st.session_state.folders[fn]=fd
                files=fd.get("files",[]); an_count=len(fd.get("analyses",{}))
                with cols[idx%3]:
                    st.markdown(f'<div class="card" style="padding:1rem;text-align:center;margin-bottom:.45rem"><div style="font-family:Space Grotesk,sans-serif;font-weight:700;font-size:.88rem;color:#ECEFF1;margin-bottom:2px">{fn}</div><div style="color:#546E7A;font-size:.62rem">{fd.get("desc","")}</div><div style="margin-top:.28rem;font-size:.65rem;color:#42A5F5">{len(files)} arq · {an_count} analisados</div></div>',unsafe_allow_html=True)
            st.markdown("<hr>",unsafe_allow_html=True)
            for fn,fd in list(st.session_state.folders.items()):
                if not isinstance(fd,dict): fd={"files":fd,"desc":"","notes":"","analyses":{}}; st.session_state.folders[fn]=fd
                files=fd.get("files",[]); analyses=fd.get("analyses",{})
                with st.expander(f"{fn} — {len(files)} arquivo(s)"):
                    up=st.file_uploader("",type=None,key=f"up_{fn}",label_visibility="collapsed",accept_multiple_files=True)
                    if up:
                        for uf in up:
                            if uf.name not in files: files.append(uf.name)
                            if fn not in st.session_state.folder_files_bytes: st.session_state.folder_files_bytes[fn]={}
                            uf.seek(0); st.session_state.folder_files_bytes[fn][uf.name]=uf.read()
                        fd["files"]=files; save_db(); st.success(f"{len(up)} adicionado(s)!")
                    if files:
                        for f in files:
                            ft=ftype_of(f); ha=f in analyses
                            icons={"PDF":"[PDF]","Word":"[DOC]","Planilha":"[XLS]","Dados":"[CSV]","Codigo":"[PY]","Imagem":"[IMG]","Markdown":"[MD]"}.get(ft,"[ARQ]")
                            ok_badge=f' <span class="badge-g" style="font-size:.55rem">analizado</span>' if ha else ''
                            st.markdown(f'<div style="display:flex;align-items:center;gap:7px;padding:.32rem 0;border-bottom:1px solid rgba(255,255,255,.04)"><span style="font-size:.68rem;color:#546E7A">{icons}</span><span style="font-size:.73rem;color:#90A4AE;flex:1">{f}</span>{ok_badge}</div>',unsafe_allow_html=True)
                    ca2,cb2,_=st.columns([1.5,1.5,2])
                    with ca2:
                        st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
                        if st.button("Analisar documentos",key=f"an_{fn}",use_container_width=True):
                            if files:
                                pb=st.progress(0,"Iniciando..."); fb=st.session_state.folder_files_bytes.get(fn,{})
                                for fi,f in enumerate(files):
                                    pb.progress((fi+1)/len(files),f"Analisando {f[:25]}..."); fbytes=fb.get(f,b""); ft2=ftype_of(f)
                                    analyses[f]=analyze_doc(f,fbytes,ft2,ra)
                                fd["analyses"]=analyses; save_db(); pb.empty(); st.success("Analise concluida!"); st.rerun()
                            else: st.warning("Adicione arquivos.")
                        st.markdown('</div>',unsafe_allow_html=True)
                    with cb2:
                        st.markdown('<div class="btn-danger">',unsafe_allow_html=True)
                        if st.button("Excluir pasta",key=f"df_{fn}",use_container_width=True):
                            del st.session_state.folders[fn]; save_db(); st.rerun()
                        st.markdown('</div>',unsafe_allow_html=True)
                    nt=st.text_area("Notas",value=fd.get("notes",""),key=f"note_{fn}",height=60)
                    if st.button("Salvar nota",key=f"sn_{fn}"):
                        fd["notes"]=nt; save_db(); st.success("Salvo!")

    # ─── ANALISE DE DOCUMENTOS ───
    with ta:
        folders=st.session_state.folders
        if not folders: st.info("Crie pastas e analise documentos para ver resultados.")
        else:
            all_an={f:an for fd in folders.values() if isinstance(fd,dict) for f,an in fd.get("analyses",{}).items()}
            tot_f=sum(len(fd.get("files",[]) if isinstance(fd,dict) else fd) for fd in folders.values())
            all_kw=[kw for an in all_an.values() for kw in an.get("keywords",[])]
            all_top=defaultdict(int)
            for an in all_an.values():
                for t,s in an.get("topics",{}).items(): all_top[t]+=s

            c1,c2,c3,c4=st.columns(4)
            with c1: st.markdown(f'<div class="stat-box"><div class="mval">{len(folders)}</div><div class="mlbl">Pastas</div></div>',unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="stat-box"><div class="mval-g">{tot_f}</div><div class="mlbl">Arquivos</div></div>',unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="stat-box"><div class="mval-y">{len(all_an)}</div><div class="mlbl">Analisados</div></div>',unsafe_allow_html=True)
            with c4: st.markdown(f'<div class="stat-box"><div class="mval-c">{len(set(all_kw[:100]))}</div><div class="mlbl">Keywords</div></div>',unsafe_allow_html=True)

            if all_top:
                fig_t=go.Figure(go.Bar(x=list(all_top.values())[:8],y=list(all_top.keys())[:8],orientation='h',marker=dict(color=CHART_C[:8]),text=list(all_top.values())[:8],textposition="outside",textfont=dict(color="#546E7A",size=9)))
                fig_t.update_layout(**{**pc_dark(),'height':260,'yaxis':dict(showgrid=False,color="#546E7A",tickfont=dict(size=9)),'title':dict(text="Distribuicao de Temas",font=dict(color="#CFD8DC",family="Space Grotesk",size=11))})
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_t,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)

            if all_kw:
                kw_count=Counter(all_kw[:200]); top_kw=kw_count.most_common(20)
                fig_kw=go.Figure(go.Bar(x=[c for _,c in top_kw],y=[k for k,_ in top_kw],orientation='h',marker=dict(color=CHART_C[:20]),text=[str(c) for _,c in top_kw],textposition="outside",textfont=dict(color="#546E7A",size=8)))
                fig_kw.update_layout(**{**pc_dark(),'height':340,'yaxis':dict(showgrid=False,color="#546E7A",tickfont=dict(size=8)),'title':dict(text="Keywords mais frequentes",font=dict(color="#CFD8DC",family="Space Grotesk",size=11)),'margin':dict(l=10,r=10,t=36,b=8)})
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_kw,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)

            # Relevance/quality per doc
            if all_an:
                docs=[f[:18]+"..." if len(f)>18 else f for f in all_an.keys()]
                rels=[a.get("relevance_score",0) for a in all_an.values()]
                wqs=[a.get("writing_quality",0) for a in all_an.values()]
                fig_rq=go.Figure()
                fig_rq.add_trace(go.Bar(name="Relevancia",x=docs,y=rels,marker_color=CHART_C[0]))
                fig_rq.add_trace(go.Bar(name="Qualidade",x=docs,y=wqs,marker_color=CHART_C[2]))
                fig_rq.update_layout(barmode="group",title=dict(text="Relevancia e Qualidade por Documento",font=dict(color="#CFD8DC",family="Space Grotesk",size=11)),height=240,**pc_dark(),legend=dict(font=dict(color="#546E7A",size=9)))
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_rq,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)

            # Per-document details
            st.markdown('<div class="dtxt">Detalhes por documento</div>',unsafe_allow_html=True)
            for f,an in all_an.items():
                with st.expander(f"{f}"):
                    kws=an.get("keywords",[]); topics=an.get("topics",{})
                    rel=an.get("relevance_score",0); wq=an.get("writing_quality",0)
                    rc="#66BB6A" if rel>=70 else("#42A5F5" if rel>=45 else "#EF5350")
                    st.markdown(f'<div class="abox"><div style="font-weight:700;font-size:.85rem;color:#ECEFF1;margin-bottom:.28rem">{f}</div><div style="font-size:.75rem;color:#90A4AE">{an.get("summary","")}</div><div style="display:flex;gap:1.2rem;margin-top:.42rem"><div style="text-align:center"><div style="font-family:Space Grotesk,sans-serif;font-size:1.05rem;font-weight:800;color:{rc}">{rel}%</div><div style="font-size:.53rem;color:#546E7A;text-transform:uppercase">Relevancia</div></div><div style="text-align:center"><div style="font-family:Space Grotesk,sans-serif;font-size:1.05rem;font-weight:800;color:#42A5F5">{wq}%</div><div style="font-size:.53rem;color:#546E7A;text-transform:uppercase">Qualidade</div></div><div style="text-align:center"><div style="font-family:Space Grotesk,sans-serif;font-size:1.05rem;font-weight:800;color:#26C6DA">{an.get("word_count",0)}</div><div style="font-size:.53rem;color:#546E7A;text-transform:uppercase">Palavras</div></div></div></div>',unsafe_allow_html=True)
                    if kws: st.markdown(tags_html(kws[:16]),unsafe_allow_html=True)
                    if topics:
                        fig2=go.Figure(go.Pie(labels=list(topics.keys()),values=list(topics.values()),hole=0.5,marker=dict(colors=CHART_C[:len(topics)],line=dict(color=["#020B18"]*12,width=2)),textfont=dict(color="white",size=8)))
                        fig2.update_layout(height=200,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(font=dict(color="#546E7A",size=8)),margin=dict(l=0,r=0,t=8,b=0))
                        st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig2,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)

    # ─── INTERESSES ───
    with ti:
        email2=st.session_state.current_user; prefs=st.session_state.user_prefs.get(email2,{})
        my_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==email2]
        d=st.session_state.stats_data

        c1,c2,c3=st.columns(3)
        with c1: st.markdown(f'<div class="stat-box"><div class="mval">{d.get("h_index",4)}</div><div class="mlbl">Indice H</div></div>',unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="stat-box"><div class="mval-g">{d.get("fator_impacto",3.8):.1f}</div><div class="mlbl">Fator Impacto</div></div>',unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="stat-box"><div class="mval-y">{len(st.session_state.saved_articles)}</div><div class="mlbl">Artigos Salvos</div></div>',unsafe_allow_html=True)

        if prefs:
            top=sorted(prefs.items(),key=lambda x:-x[1])[:12]; mx=max(s for _,s in top) if top else 1
            cats=[t for t,_ in top[:8]]; vals=[round(s/mx*100) for _,s in top[:8]]
            if len(cats)>=3:
                fig3=go.Figure(go.Scatterpolar(r=vals+[vals[0]],theta=cats+[cats[0]],fill='toself',line=dict(color="#1E88E5",width=1.5),fillcolor="rgba(30,136,229,.10)"))
                fig3.update_layout(height=280,polar=dict(bgcolor="rgba(0,0,0,0)",radialaxis=dict(visible=True,gridcolor="rgba(255,255,255,.04)",color="#546E7A",tickfont=dict(size=8)),angularaxis=dict(gridcolor="rgba(255,255,255,.04)",color="#546E7A",tickfont=dict(size=9))),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=40,r=40,t=15,b=15))
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig3,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
            # Bar chart of interests
            top_names=[t for t,_ in top[:10]]; top_vals=[round(s,1) for _,s in top[:10]]
            fig_i=go.Figure(go.Bar(x=top_names,y=top_vals,marker=dict(color=CHART_C[:len(top_names)]),text=top_vals,textposition="outside",textfont=dict(color="#546E7A",size=9)))
            fig_i.update_layout(**{**pc_dark(),'height':220,'title':dict(text="Seus interesses de pesquisa",font=dict(color="#CFD8DC",family="Space Grotesk",size=11))})
            st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_i,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
        else: st.info("Interaja com publicacoes para construir seu perfil de interesses.")

        if my_posts:
            c1b,c2b,c3b=st.columns(3)
            with c1b: st.markdown(f'<div class="stat-box"><div class="mval">{len(my_posts)}</div><div class="mlbl">Publicacoes</div></div>',unsafe_allow_html=True)
            with c2b: st.markdown(f'<div class="stat-box"><div class="mval-g">{sum(p["likes"] for p in my_posts)}</div><div class="mlbl">Curtidas totais</div></div>',unsafe_allow_html=True)
            with c3b: st.markdown(f'<div class="stat-box"><div class="mval-c">{sum(p.get("views",0) for p in my_posts)}</div><div class="mlbl">Visualizacoes</div></div>',unsafe_allow_html=True)
            # Engagement chart
            titles=[p["title"][:14]+"..." for p in my_posts]
            fig_e=go.Figure()
            fig_e.add_trace(go.Bar(name="Curtidas",x=titles,y=[p["likes"] for p in my_posts],marker_color=CHART_C[0]))
            fig_e.add_trace(go.Bar(name="Comentarios",x=titles,y=[len(p.get("comments",[])) for p in my_posts],marker_color=CHART_C[2]))
            fig_e.update_layout(barmode="group",title=dict(text="Engajamento por publicacao",font=dict(color="#CFD8DC",family="Space Grotesk",size=11)),height=220,**pc_dark(),legend=dict(font=dict(color="#546E7A",size=9)))
            st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_e,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)

        st.markdown("<hr>",unsafe_allow_html=True)
        nh=st.number_input("Indice H",0,200,d.get("h_index",4),key="e_h")
        nfi=st.number_input("Fator impacto",0.0,100.0,float(d.get("fator_impacto",3.8)),step=0.1,key="e_fi")
        nn2=st.text_area("Notas de pesquisa",value=d.get("notes",""),key="e_nt",height=68)
        if st.button("Salvar metricas",key="btn_sm"):
            d.update({"h_index":nh,"fator_impacto":nfi,"notes":nn2}); st.success("Salvo!")

    # ─── TENDENCIAS ───
    with tt:
        all_posts_t=st.session_state.feed_posts
        users_t=st.session_state.users if isinstance(st.session_state.users,dict) else {}

        # Tag frequency heatmap over time
        tag_all=Counter(t for p in all_posts_t for t in p.get("tags",[]))
        area_all=Counter(p.get("area","") for p in all_posts_t if p.get("area",""))
        status_all=Counter(p.get("status","") for p in all_posts_t)

        c1,c2=st.columns(2)
        with c1:
            if tag_all:
                top_tags=tag_all.most_common(12)
                fig_tag=go.Figure(go.Bar(y=[t for t,_ in top_tags],x=[c for _,c in top_tags],orientation='h',marker=dict(color=CHART_C[:len(top_tags)]),text=[str(c) for _,c in top_tags],textposition="outside",textfont=dict(color="#546E7A",size=9)))
                fig_tag.update_layout(**{**pc_dark(),'height':320,'yaxis':dict(showgrid=False,color="#546E7A",tickfont=dict(size=8)),'title':dict(text="Tags mais usadas",font=dict(color="#CFD8DC",family="Space Grotesk",size=11))})
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_tag,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
        with c2:
            if area_all:
                fig_area=go.Figure(go.Pie(labels=list(area_all.keys()),values=list(area_all.values()),hole=0.45,marker=dict(colors=CHART_C[:len(area_all)],line=dict(color=["#020B18"]*12,width=2)),textfont=dict(color="white",size=8)))
                fig_area.update_layout(height=320,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(font=dict(color="#546E7A",size=8)),title=dict(text="Distribuicao por area",font=dict(color="#CFD8DC",family="Space Grotesk",size=11)),margin=dict(l=0,r=0,t=36,b=0))
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_area,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)

        c3,c4=st.columns(2)
        with c3:
            if status_all:
                fig_st=go.Figure(go.Bar(x=list(status_all.keys()),y=list(status_all.values()),marker=dict(color=[CHART_C[1],CHART_C[0],CHART_C[3]][:len(status_all)]),text=list(status_all.values()),textposition="outside",textfont=dict(color="#546E7A",size=9)))
                fig_st.update_layout(**{**pc_dark(),'height':220,'title':dict(text="Publicacoes por status",font=dict(color="#CFD8DC",family="Space Grotesk",size=11))})
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_st,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
        with c4:
            # Area distribution in user base
            area_users=Counter(ud.get("area","Outro") for ud in users_t.values() if ud.get("area"))
            if area_users:
                fig_au=go.Figure(go.Bar(y=list(area_users.keys()),x=list(area_users.values()),orientation='h',marker=dict(color=CHART_C[:len(area_users)]),text=list(area_users.values()),textposition="outside",textfont=dict(color="#546E7A",size=9)))
                fig_au.update_layout(**{**pc_dark(),'height':220,'yaxis':dict(showgrid=False,color="#546E7A",tickfont=dict(size=8)),'title':dict(text="Areas dos pesquisadores",font=dict(color="#CFD8DC",family="Space Grotesk",size=11))})
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_au,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)

        # Top posts by engagement
        top_eng=sorted(all_posts_t,key=lambda p:p["likes"]+len(p.get("comments",[]))*2,reverse=True)[:5]
        st.markdown('<div class="dtxt">Publicacoes com maior engajamento</div>',unsafe_allow_html=True)
        for p in top_eng:
            st.markdown(f'<div class="scard"><div style="display:flex;justify-content:space-between;align-items:center"><div style="font-family:Space Grotesk,sans-serif;font-size:.83rem;font-weight:700;color:#ECEFF1;flex:1">{p["title"][:55]}</div>{badge(p.get("status","Em andamento"))}</div><div style="font-size:.67rem;color:#546E7A;margin-top:.28rem">{p.get("date","")} · {p["likes"]} curtidas · {len(p.get("comments",[]))} comentarios · {p.get("views",0)} views · {p.get("area","")}</div></div>',unsafe_allow_html=True)

    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  CHAT
# ══════════════════════════════════════════════════════════════
def page_chat():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.5rem;margin-bottom:.9rem">Mensagens</h1>',unsafe_allow_html=True)
    cc,cm=st.columns([.85,2.8]); email=st.session_state.current_user
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    with cc:
        st.markdown('<div style="font-size:.57rem;font-weight:700;color:#546E7A;letter-spacing:.12em;text-transform:uppercase;margin-bottom:.65rem">Conversas</div>',unsafe_allow_html=True)
        shown=set()
        for ue in st.session_state.chat_contacts:
            if ue==email or ue in shown: continue
            shown.add(ue); ud=users.get(ue,{}); un=ud.get("name","?"); ug=ugrad(ue)
            msgs=st.session_state.chat_messages.get(ue,[]); last=msgs[-1]["text"][:22]+"..." if msgs and len(msgs[-1]["text"])>22 else(msgs[-1]["text"] if msgs else "Iniciar conversa")
            active=st.session_state.active_chat==ue; online=is_online(ue)
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            bg=f"rgba(30,136,229,{'.08' if active else '.02'})"; bdr=f"rgba(30,136,229,{'.22' if active else '.07'})"
            st.markdown(f'<div style="background:{bg};border:1px solid {bdr};border-radius:11px;padding:7px 9px;margin-bottom:3px"><div style="display:flex;align-items:center;gap:7px">{avh(ini(un),28,ug)}<div style="overflow:hidden;flex:1"><div style="font-size:.74rem;font-weight:600;color:#ECEFF1">{dot}{un}</div><div style="font-size:.62rem;color:#546E7A;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{last}</div></div></div></div>',unsafe_allow_html=True)
            if st.button("abrir",key=f"oc_{ue}",use_container_width=True): st.session_state.active_chat=ue; st.rerun()
        st.markdown("<hr>",unsafe_allow_html=True)
        nc2=st.text_input("",placeholder="E-mail...",key="new_ct",label_visibility="collapsed")
        if st.button("Adicionar",key="btn_ac",use_container_width=True):
            if nc2 in users and nc2!=email:
                if nc2 not in st.session_state.chat_contacts: st.session_state.chat_contacts.append(nc2)
                st.rerun()
    with cm:
        if st.session_state.active_chat:
            contact=st.session_state.active_chat; cd=users.get(contact,{}); cn=cd.get("name","?"); cg=ugrad(contact)
            msgs=st.session_state.chat_messages.get(contact,[]); online=is_online(contact)
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            st.markdown(f'<div style="background:rgba(30,136,229,.04);border:1px solid rgba(30,136,229,.12);border-radius:12px;padding:9px 13px;margin-bottom:.8rem;display:flex;align-items:center;gap:9px">{avh(ini(cn),34,cg)}<div style="flex:1"><div style="font-weight:700;font-size:.86rem;color:#ECEFF1">{dot}{cn}</div><div style="font-size:.62rem;color:#66BB6A">cifrado ponta a ponta</div></div></div>',unsafe_allow_html=True)
            for msg in msgs:
                im=msg["from"]=="me"; cls="bme" if im else "bthem"
                st.markdown(f'<div style="display:flex;{"justify-content:flex-end" if im else ""}"><div class="{cls}">{msg["text"]}<div style="font-size:.56rem;color:#546E7A;margin-top:2px;text-align:{"right" if im else "left"}">{msg["time"]}</div></div></div>',unsafe_allow_html=True)
            st.markdown("<br>",unsafe_allow_html=True)
            ci2,cb2=st.columns([5,1])
            with ci2: nm=st.text_input("",placeholder="Escreva uma mensagem...",key=f"mi_{contact}",label_visibility="collapsed")
            with cb2:
                if st.button("Enviar",key=f"ms_{contact}",use_container_width=True):
                    if nm: now=datetime.now().strftime("%H:%M"); st.session_state.chat_messages.setdefault(contact,[]).append({"from":"me","text":nm,"time":now}); st.rerun()
        else:
            st.markdown('<div class="card" style="text-align:center;padding:5rem"><div style="font-family:Space Grotesk,sans-serif;font-size:.96rem;color:#CFD8DC">Selecione uma conversa</div><div style="font-size:.70rem;color:#546E7A;margin-top:.4rem">Comunicacao cifrada ponta a ponta</div></div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  SETTINGS
# ══════════════════════════════════════════════════════════════
def page_settings():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.5rem;margin-bottom:.9rem">Configuracoes</h1>',unsafe_allow_html=True)
    email=st.session_state.current_user; ud=st.session_state.users.get(email,{})
    st.markdown(f'<div class="abox"><div style="font-size:.57rem;color:#546E7A;text-transform:uppercase;letter-spacing:.09em;margin-bottom:.35rem;font-weight:700">Conta</div><div style="font-family:Space Grotesk,sans-serif;font-weight:700;font-size:.93rem;color:#42A5F5">{email}</div><div style="font-size:.70rem;color:#90A4AE;margin-top:.2rem">Bolsa: {ud.get("bolsa","nao informada")}</div></div>',unsafe_allow_html=True)
    en=ud.get("2fa_enabled",False)
    st.markdown(f'<div class="{"btn-danger" if en else "btn-success"}">',unsafe_allow_html=True)
    if st.button("Desativar 2FA" if en else "Ativar 2FA",key="cfg_2fa"):
        st.session_state.users[email]["2fa_enabled"]=not en; save_db(); st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)
    st.markdown("<hr>",unsafe_allow_html=True)
    with st.form("cpw"):
        op=st.text_input("Senha atual",type="password"); np2=st.text_input("Nova senha",type="password"); nc3=st.text_input("Confirmar",type="password")
        if st.form_submit_button("Alterar senha",use_container_width=True):
            if hp(op)!=ud.get("password",""): st.error("Incorreta.")
            elif np2!=nc3: st.error("Nao coincidem.")
            elif len(np2)<6: st.error("Minimo 6 caracteres.")
            else: st.session_state.users[email]["password"]=hp(np2); save_db(); st.success("Senha alterada!")
    st.markdown("<hr>",unsafe_allow_html=True)
    for nm,ds in [("Cifragem AES-256","End-to-end nas mensagens"),("Hash SHA-256","Senhas com hash seguro"),("TLS 1.3","Transmissao cifrada")]:
        st.markdown(f'<div class="scard" style="background:rgba(27,94,32,.04);border-color:rgba(102,187,106,.12)"><div style="display:flex;align-items:center;gap:9px"><div style="width:22px;height:22px;border-radius:6px;background:rgba(102,187,106,.10);display:flex;align-items:center;justify-content:center;font-size:.70rem;color:#66BB6A">ok</div><div><div style="font-weight:700;color:#66BB6A;font-size:.76rem">{nm}</div><div style="font-size:.64rem;color:#546E7A">{ds}</div></div></div></div>',unsafe_allow_html=True)
    st.markdown("<hr>",unsafe_allow_html=True)
    st.markdown('<div class="btn-danger">',unsafe_allow_html=True)
    if st.button("Sair da conta",key="logout",use_container_width=True):
        st.session_state.logged_in=False; st.session_state.current_user=None; st.session_state.page="login"; st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════════════════════════════
def main():
    inject_css()
    if not st.session_state.logged_in:
        page_login(); return
    if st.session_state.page=="welcome":
        render_nav(); page_welcome(); return
    render_nav()
    if st.session_state.profile_view:
        page_profile(st.session_state.profile_view); return
    {
        "repository": page_repository,
        "search":     page_search,
        "knowledge":  page_knowledge,
        "folders":    page_folders,
        "chat":       page_chat,
        "settings":   page_settings,
    }.get(st.session_state.page, page_repository)()

main()
