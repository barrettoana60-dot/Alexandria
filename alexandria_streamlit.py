import subprocess, sys, os, json, hashlib, random, string, re, io, base64, time, math
from datetime import datetime, timedelta
from collections import defaultdict, Counter

# --- Instalação de pacotes silenciosa ---
def _pip(*pkgs):
    for p in pkgs:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", p, "-q"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass

# --- Importações condicionais ---
try: import plotly.graph_objects as go
except: _pip("plotly"); import plotly.graph_objects as go

try: import plotly.express as px
except: pass # plotly.express é parte de plotly, mas a importação direta pode falhar se não estiver instalado

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

# --- Configuração da página Streamlit ---
st.set_page_config(page_title="Nebula Repository", page_icon="🔬", layout="wide", initial_sidebar_state="expanded")

# --- Configurações de Banco de Dados (JSON) ---
DB_FILE = "nebula_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

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
                "repo_metadata":st.session_state.get("repo_metadata",{}),
            },f,ensure_ascii=False,indent=2)
    except: pass

# --- Funções Utilitárias ---
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
def is_online(e): return (hash(e+"on")%3)!=0 # Simula status online/offline

# --- Cores e Estilos ---
GRAD_POOL=["135deg,#0A1929,#1A2F4A","135deg,#0B1E33,#1D3A5A","135deg,#0C2138,#20456A",
           "135deg,#0D253D,#23507A","135deg,#0E2942,#265B8A","135deg,#0F2D47,#29669A"]
def ugrad(e): return f"linear-gradient({GRAD_POOL[hash(e or '')%len(GRAD_POOL)]})"

VIB=["#0A6EBD","#1A7FCC","#2B90DB","#3CA1EA","#4DBBFF","#6A9C89","#7DB09A","#90C4AB"] # Cores para gráficos

# --- Stopwords para extração de palavras-chave ---
STOPWORDS={"de","a","o","que","e","do","da","em","um","para","é","com","uma","os","no","se","na","por",
           "mais","as","dos","como","mas","foi","ao","ele","das","tem","à","seu","sua","ou","ser",
           "the","of","and","to","in","is","it","that","was","he","for","on","are","as","with","they",
           "at","be","this","from","or","one","had","by","but","not","what","all","were","we","when",
           "your","can","said","there","use","an","each","which","she","do","how","their","if","will",
           "up","other","about","out","many","then","them","these","so","also","into","its","than"}

# --- Dados de Exemplo (SEED) ---
SEED_POSTS=[
    {"id":1,"author":"Carlos Mendez","author_email":"carlos@nebula.ai","avatar":"CM","area":"Neurociência",
     "title":"Efeitos da Privação de Sono na Plasticidade Sináptica",
     "abstract":"Investigamos como 24h de privação de sono afetam espinhas dendríticas em ratos Wistar, com redução de 34% na plasticidade hipocampal. Utilizamos microscopia confocal e Western Blot para quantificação proteica. Resultados indicam janela crítica de recuperação de 72h.",
     "tags":["neurociência","sono","memória","hipocampo","plasticidade"],"likes":47,
     "comments":[{"user":"Maria Silva","text":"Excelente metodologia! Já viu relação com BDNF?"}],
     "status":"Em andamento","date":"2026-02-10","liked_by":[],"saved_by":[],"connections":["sono","memória"],"views":312,
     "methodology":"experimental","citations":8,"keywords_extracted":["privação","sono","plasticidade","sináptica","hipocampal"]},
    {"id":2,"author":"Luana Freitas","author_email":"luana@nebula.ai","avatar":"LF","area":"Biomedicina",
     "title":"CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras",
     "abstract":"Vetor AAV9 modificado para entrega de CRISPR no gene DMD com eficiência de 78% em modelos mdx. Análise proteômica confirma restauração parcial da distrofina. Trial clínico fase I planejado para Q3 2026.",
     "tags":["CRISPR","gene terapia","músculo","AAV9","distrofina"],"likes":93,
     "comments":[{"user":"Ana","text":"Quando iniciam os trials?"},{"user":"João Lima","text":"Resultados impressionantes!"}],
     "status":"Publicado","date":"2026-01-28","liked_by":[],"saved_by":[],"connections":["genômica","distrofia"],"views":891,
     "methodology":"experimental","citations":24,"keywords_extracted":["CRISPR","AAV9","distrofia","muscular","gene"]},
    {"id":3,"author":"Rafael Souza","author_email":"rafael@nebula.ai","avatar":"RS","area":"Computação",
     "title":"Redes Neurais Quântico-Clássicas para Otimização Combinatória",
     "abstract":"Arquitetura híbrida variacional combinando qubits supercondutores com camadas densas clássicas. TSP resolvido com 40% menos iterações que algoritmos clássicos em grafos de 100+ nós.",
     "tags":["quantum ML","otimização","TSP","computação quântica","híbrido"],"likes":201,"comments":[],"status":"Em andamento",
     "date":"2026-02-15","liked_by":[],"saved_by":[],"connections":["computação quântica","IA"],"views":1240,
     "methodology":"computacional","citations":31,"keywords_extracted":["quântico","clássico","otimização","combinatória","variacional"]},
    {"id":4,"author":"Priya Nair","author_email":"priya@nebula.ai","avatar":"PN","area":"Astrofísica",
     "title":"Detecção de Matéria Escura via Lentes Gravitacionais Fracas",
     "abstract":"Mapeamento com 100M de galáxias do DES Y3. Tensão de 2.8σ com ΛCDM em escalas < 1 Mpc. Análise de shear cósmico com pipeline bayesiano robusto a efeitos sistemáticos.",
     "tags":["astrofísica","matéria escura","cosmologia","DES","lensing"],"likes":312,"comments":[],
     "status":"Publicado","date":"2026-02-01","liked_by":[],"saved_by":[],"connections":["cosmologia","física"],"views":2180,
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
    "demo@nebula.ai":{"name":"Ana Pesquisadora","password":hp("demo123"),"bio":"Pesquisadora em IA e Ciências Cognitivas | UFMG","area":"Inteligência Artificial","followers":128,"following":47,"verified":True,"2fa_enabled":False,"bolsa_afiliacao":"UFMG","orcid":"0000-0001-2345-6789","h_index":7,"publications":12},
    "carlos@nebula.ai":{"name":"Carlos Mendez","password":hp("nebula123"),"bio":"Neurocientista | UFMG | Plasticidade sináptica e sono","area":"Neurociência","followers":210,"following":45,"verified":True,"2fa_enabled":False,"bolsa_afiliacao":"UFMG","h_index":9,"publications":18},
    "luana@nebula.ai":{"name":"Luana Freitas","password":hp("nebula123"),"bio":"Biomédica | FIOCRUZ | CRISPR e terapia gênica","area":"Biomedicina","followers":178,"following":62,"verified":True,"2fa_enabled":False,"bolsa_afiliacao":"FIOCRUZ","h_index":11,"publications":24},
    "rafael@nebula.ai":{"name":"Rafael Souza","password":hp("nebula123"),"bio":"Computação Quântica | USP | Algoritmos híbridos","area":"Computação","followers":340,"following":88,"verified":True,"2fa_enabled":False,"bolsa_afiliacao":"USP","h_index":14,"publications":31},
    "priya@nebula.ai":{"name":"Priya Nair","password":hp("nebula123"),"bio":"Astrofísica | MIT | Dark matter & gravitational lensing","area":"Astrofísica","followers":520,"following":31,"verified":True,"2fa_enabled":False,"bolsa_afiliacao":"MIT","h_index":22,"publications":47},
    "joao@nebula.ai":{"name":"João Lima","password":hp("nebula123"),"bio":"Psicólogo Cognitivo | UNICAMP | IA e vieses clínicos","area":"Psicologia","followers":95,"following":120,"verified":True,"2fa_enabled":False,"bolsa_afiliacao":"UNICAMP","h_index":6,"publications":14},
}

CHAT_INIT={
    "carlos@nebula.ai":[{"from":"carlos@nebula.ai","text":"Oi! Vi seu comentário na pesquisa sobre LLMs.","time":"09:14"},{"from":"me","text":"Achei muito interessante o paralelo com neurociência!","time":"09:16"}],
    "luana@nebula.ai":[{"from":"luana@nebula.ai","text":"Podemos colaborar no próximo projeto de bioinformática?","time":"ontem"}],
}

# --- Inicialização do Estado da Sessão ---
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

init()

# ================================================
# Chamadas de API (Claude)
# ================================================
def call_claude_vision(img_bytes, prompt, api_key):
    if not api_key or not api_key.startswith("sk-"):
        return None,"Chave API inválida."
    try:
        img=PILImage.open(io.BytesIO(img_bytes))
        buf=io.BytesIO()
        img.convert("RGB").save(buf,format="JPEG",quality=85)
        b64=base64.b64encode(buf.getvalue()).decode()
        resp=requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key":api_key,"anthropic-version":"2023-06-01","content-type":"application/json"},
            json={"model":"claude-3-opus-20240229","max_tokens":1500, # Modelo atualizado
                  "messages":[{"role":"user","content":[
                      {"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":b64}},
                      {"type":"text","text":prompt}]}]},
            timeout=30
        )
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
        "connections":content, # O prompt de conexões é gerado dinamicamente na função page_knowledge
    }
    try:
        resp=requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key":api_key,"anthropic-version":"2023-06-01","content-type":"application/json"},
            json={"model":"claude-3-opus-20240229","max_tokens":1000, # Modelo atualizado
                  "messages":[{"role":"user","content":prompts.get(prompt_type,content)}]},
            timeout=25
        )
        if resp.status_code==200:
            text=resp.json()["content"][0]["text"].strip()
            text=re.sub(r'^```json\s*','',text); text=re.sub(r'\s*```$','',text)
            return json.loads(text),None
        return None,f"HTTP {resp.status_code}"
    except Exception as e: return None,str(e)

VISION_PROMPT="""Você é um especialista em análise de imagens científicas. Analise esta imagem com o máximo de detalhe e responda APENAS em JSON puro, descrevendo o que a imagem É e o que ela REPRESENTA cientificamente:
{
  "tipo": "<tipo da imagem: microscopia óptica/eletrônica, fluorescência, cristalografia, difração, gel eletroforese, western blot, imunofluorescência, histopatologia, gráfico científico, diagrama, espectroscopia, radiografia, tomografia, ressonância, imagem astronômica, imagem celular, imagem molecular, etc>",
  "origem": "<de onde provavelmente vem esta imagem: biologia celular, microbiologia, neurociência, oncologia, genômica, física de partículas, astrofísica, química, materiais, medicina clínica, etc>",
  "descricao_visual": "<descrição científica detalhada do que é visível: estruturas, padrões, cores, organização, características morfológicas, etc.>",
  "representacao_cientifica": "<o que esta imagem representa ou ilustra no contexto científico, qual seu significado ou implicação para a pesquisa>",
  "estruturas_chave": ["<estrutura 1>","<estrutura 2>","<estrutura 3>"],
  "tecnica_experimental": "<técnica experimental provável: H&E staining, DAPI, GFP, confocal, TEM, SEM, fluorescência, difração X, PCR gel, etc>",
  "qualidade_tecnica": "<Alta/Média/Baixa - qualidade técnica da imagem, resolução, contraste, ruído>",
  "confianca_ia": <número de 0 a 100 de confiança na classificação e análise>,
  "termos_busca_relacionados": "<3-5 termos científicos para buscar artigos relacionados>",
  "observacoes_adicionais": "<observações científicas relevantes sobre o conteúdo, possíveis artefatos, ou interpretações>",
  "metodologias_complementares_sugeridas": ["<metodologia 1>","<metodologia 2>"],
  "areas_de_colaboracao_potencial": ["<área 1>","<área 2>"]
}"""

# ================================================
#  BUSCA ACADÊMICA EXTERNA
# ================================================
@st.cache_data(show_spinner=False,ttl=1800)
def search_ss(q,lim=8):
    try:
        r=requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query":q,"limit":lim,
                    "fields":"title,authors,year,abstract,venue,externalIds,openAccessPdf,citationCount,influentialCitationCount,fieldsOfStudy"},
            timeout=10
        )
        if r.status_code==200:
            out=[]
            for p in r.json().get("data",[]):
                ext=p.get("externalIds",{}) or {}
                doi=ext.get("DOI","")
                arx=ext.get("ArXiv","")
                pdf=p.get("openAccessPdf") or {}
                link=pdf.get("url","") or (f"https://arxiv.org/abs/{arx}" if arx else (f"https://doi.org/{doi}" if doi else ""))
                al=p.get("authors",[]) or []
                au=", ".join(a.get("name","") for a in al[:3])
                if len(al)>3: au+=" et al."
                fos=p.get("fieldsOfStudy",[]) or []
                out.append({"title":p.get("title","Sem título"),"authors":au or "—","year":p.get("year","?"),
                            "source":p.get("venue","") or "Semantic Scholar","doi":doi or arx or "—",
                            "abstract":(p.get("abstract","") or "")[:350],"url":link,
                            "citations":p.get("citationCount",0),
                            "influential_citations":p.get("influentialCitationCount",0),
                            "fields":fos[:3],"origin":"semantic"})
            return out
    except: pass
    return []

@st.cache_data(show_spinner=False,ttl=1800)
def search_cr(q,lim=4):
    try:
        r=requests.get(
            "https://api.crossref.org/works",
            params={"query":q,"rows":lim,
                    "select":"title,author,issued,abstract,DOI,container-title,is-referenced-by-count,subject",
                    "mailto":"nebula@example.com"},
            timeout=10
        )
        if r.status_code==200:
            out=[]
            for p in r.json().get("message",{}).get("items",[]):
                title=(p.get("title") or ["?"])[0]
                ars=p.get("author",[]) or []
                au=", ".join(f'{a.get("given","").split()[0] if a.get("given") else ""} {a.get("family","")}'.strip() for a in ars[:3])
                if len(ars)>3: au+=" et al."
                yr=(p.get("issued",{}).get("date-parts") or [[None]])[0][0]
                doi=p.get("DOI","")
                ab=re.sub(r'<[^>]+>','',(p.get("abstract","") or ""))[:350]
                subj=p.get("subject",[])[:3]
                out.append({"title":title,"authors":au or "—","year":yr or "?",
                            "source":(p.get("container-title") or ["CrossRef"])[0],"doi":doi,
                            "abstract":ab,"url":f"https://doi.org/{doi}" if doi else "",
                            "citations":p.get("is-referenced-by-count",0),"fields":subj,"origin":"crossref"})
            return out
    except: pass
    return []

# ================================================
#  EXTRAÇÃO DE TEXTO E PALAVRAS-CHAVE
# ================================================
EMAP={"pdf":"PDF","docx":"Word","xlsx":"Planilha","csv":"Dados","txt":"Texto","py":"Código",
      "md":"Markdown","png":"Imagem","jpg":"Imagem","jpeg":"Imagem","tiff":"Imagem","ipynb":"Notebook"}

def ftype(fname):
    return EMAP.get(fname.split(".")[-1].lower() if "." in fname else "","Arquivo")

@st.cache_data(show_spinner=False)
def extract_pdf(b):
    if PyPDF2 is None: return ""
    try:
        r=PyPDF2.PdfReader(io.BytesIO(b))
        t=""
        for pg in r.pages[:30]: # Limita a 30 páginas para performance
            try: t+=pg.extract_text()+"\n"
            except: pass
        return t[:60000] # Limita o texto extraído
    except: return ""

@st.cache_data(show_spinner=False)
def kw_extract(text,n=30):
    if not text: return []
    words=re.findall(r'\b[a-záàâãéêíóôõúüçA-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]{4,}\b',text.lower())
    words=[w for w in words if w not in STOPWORDS]
    if not words: return []
    tf=Counter(words)
    tot=sum(tf.values())
    bigrams=[]
    ws=text.lower().split()
    for i in range(len(ws)-1):
        bg=f"{ws[i]} {ws[i+1]}"
        if len(ws[i])>3 and len(ws[i+1])>3 and ws[i] not in STOPWORDS and ws[i+1] not in STOPWORDS:
            bigrams.append(bg)
    bg_count=Counter(bigrams)
    single_kw=[w for w,_ in sorted({w:c/tot for w,c in tf.items()}.items(),key=lambda x:-x[1])[:n]]
    top_bg=[bg for bg,c in bg_count.most_common(8) if c>1]
    return (top_bg+single_kw)[:n]

def topic_dist(kws):
    tm={
        "Saúde & Medicina":["saúde","medicina","clínico","health","medical","therapy","disease","diagnóstico","tratamento"],
        "Biologia & Genômica":["biologia","genômica","gene","dna","rna","proteína","célula","crispr","genética","organismo","molecular"],
        "Neurociência":["neurociência","neural","cérebro","cognição","memória","sono","brain","sinapse","neurônio","psicologia"],
        "Computação & IA":["algoritmo","machine","learning","inteligência","dados","computação","ia","deep","quantum","rede neural","LLM"],
        "Física & Astronomia":["física","quântica","partícula","energia","galáxia","astrofísica","cosmologia","fóton","campo","lentes gravitacionais"],
        "Química":["química","molécula","síntese","reação","polímero","composto","catálise","ligação"],
        "Engenharia":["engenharia","sistema","robótica","automação","sensor","controle","projeto","eletrônica"],
        "Ciências Sociais":["sociedade","cultura","educação","política","psicologia","comportamento","social","economia"],
        "Ecologia & Ambiente":["ecologia","clima","ambiente","biodiversidade","espécie","habitat","sustentável","poluição"],
        "Matemática & Estatística":["matemática","estatística","probabilidade","equação","modelo","teorema","otimização","análise de dados"]
    }
    s=defaultdict(int)
    for kw in kws:
        for tp,terms in tm.items():
            if any(t in kw or kw in t for t in terms):
                s[tp]+=1
    return dict(sorted(s.items(),key=lambda x:-x[1])) if s else {"Pesquisa Geral":1}

def record(tags,w=1.0):
    e=st.session_state.get("current_user")
    if not e or not tags: return
    p=st.session_state.user_prefs.setdefault(e,defaultdict(float))
    for t in tags: p[t.lower()]+=w
    save_db()

def get_recs(email,n=3):
    pr=st.session_state.user_prefs.get(email,{})
    if not pr: return []
    def sc(p): return sum(pr.get(t.lower(),0) for t in p.get("tags",[])+p.get("connections",[]))
    scored=[(sc(p),p) for p in st.session_state.feed_posts if email not in p.get("liked_by",[])]
    return [p for s,p in sorted(scored,key=lambda x:-x[0]) if s>0][:n]

def area_tags(area):
    a=(area or "").lower()
    M={"ia":["machine learning","LLM","deep learning"],"inteligência artificial":["machine learning","LLM"],
       "neurociência":["sono","memória","cognição","sinapse"],"biologia":["célula","genômica","dna"],
       "física":["quantum","astrofísica","partícula"],"medicina":["diagnóstico","terapia","clínico"],
       "computação":["algoritmo","dados","software"],"química":["molécula","reação","síntese"]}
    for k,v in M.items():
        if k in a: return v
    return [w.strip() for w in a.replace(","," ").split() if len(w)>3][:5]

# ================================================
#  ANÁLISE PROFUNDA DE PESQUISA (Algorítmica)
# ================================================
def deep_analyze_research_algorithmic(post, all_posts):
    """Análise profunda algorítmica de uma pesquisa com métricas, temporal, estatísticas e melhorias."""
    similar_posts=[p for p in all_posts if p["id"]!=post["id"] and
                   any(t in p.get("tags",[]) for t in post.get("tags",[]))]

    all_related_kw=[]
    for p in similar_posts:
        all_related_kw.extend(p.get("tags",[]))
    kw_freq=Counter(all_related_kw)

    # Análise temporal
    try:
        post_date=datetime.strptime(post.get("date","2026-01-01"),"%Y-%m-%d")
        days_since=(datetime.now()-post_date).days
        monthly_views=post.get("views",0)/max(days_since/30,0.1)
    except:
        days_since=0; monthly_views=0

    # Score de impacto calculado
    likes=post.get("likes",0)
    views=post.get("views",1)
    comments=len(post.get("comments",[]))
    citations=post.get("citations",0)
    engagement=(likes*3+comments*5+citations*10)/max(views,1)*100

    # Temas emergentes vs estabelecidos
    tags=post.get("tags",[])
    trend_score=sum(kw_freq.get(t,0) for t in tags)/max(len(tags),1)

    # Lacunas identificadas
    gaps=[]
    abstract=post.get("abstract","").lower()
    if "amostra" not in abstract and "n=" not in abstract and "participantes" not in abstract:
        gaps.append("Tamanho amostral não especificado")
    if "controle" not in abstract and "grupo controle" not in abstract:
        gaps.append("Grupo controle não mencionado")
    if "limitação" not in abstract and "limitation" not in abstract:
        gaps.append("Limitações do estudo não discutidas")
    if "replicação" not in abstract and "reproducib" not in abstract:
        gaps.append("Reprodutibilidade não abordada")

    # Pontos fortes
    strengths=[]
    if citations>20: strengths.append(f"Alta citabilidade ({citations} citações)")
    if engagement>5: strengths.append(f"Alto engajamento ({engagement:.1f}%)")
    if len(tags)>=4: strengths.append("Boa indexação por palavras-chave")
    if post.get("methodology"): strengths.append(f"Metodologia clara: {post.get('methodology')}")

    # Sugestões de melhoria
    improvements=[]
    if likes<50: improvements.append("Aumentar visibilidade - compartilhe em congressos")
    if comments<3: improvements.append("Incentivar discussão - faça perguntas abertas no resumo")
    if not post.get("methodology"): improvements.append("Detalhe melhor a metodologia utilizada")

    # Pesquisadores com interesses similares
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    collab_candidates=[]
    for ue,ud in users.items():
        if ue==post.get("author_email"): continue
        user_tags=set(area_tags(ud.get("area","")))
        for p2 in all_posts:
            if p2.get("author_email")==ue:
                user_tags.update(t.lower() for t in p2.get("tags",[]))
        overlap=set(t.lower() for t in tags) & user_tags
        if overlap:
            collab_candidates.append({"email":ue,"name":ud.get("name","?"),"area":ud.get("area",""),
                                      "overlap":list(overlap)[:4],"score":len(overlap)})
    collab_candidates.sort(key=lambda x:-x["score"])

    return {
        "engagement":round(engagement,2),
        "monthly_views":round(monthly_views,1),
        "days_since":days_since,
        "trend_score":round(trend_score,2),
        "similar_count":len(similar_posts),
        "top_related_kw":[w for w,_ in kw_freq.most_common(8)],
        "gaps":gaps,
        "strengths":strengths,
        "improvements":improvements,
        "collab_candidates":collab_candidates[:5],
        "similar_posts":similar_posts[:4],
        "impact_tier":"Alto" if post.get("citations",0)>20 else ("Médio" if post.get("citations",0)>5 else "Em desenvolvimento"),
    }

# ================================================
#  ML PIPELINE PARA IMAGENS
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
#  ANÁLISE DE DOCUMENTOS
# ================================================
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
        r["strengths"]=[f"Vocabulário técnico rico ({len(r['keywords'])} termos-chave)"] if len(r["keywords"])>15 else []
        if words>2000: r["strengths"].append("Conteúdo extenso e detalhado")
        r["improvements"]=["Expandir o conteúdo com mais detalhes"] if words<500 else []
        if len(r["keywords"])<8: r["improvements"].append("Enriquecer com mais terminologia técnica")
        if r.get("relevance_score",0)<50: r["improvements"].append("Melhorar alinhamento com a área de pesquisa")
        r["summary"]=f"{ftype_str} . {words} palavras . ~{r['reading_time']}min . {', '.join(list(r['topics'].keys())[:2])} . {', '.join(r['keywords'][:4])}"
    else:
        r["summary"]=f"Arquivo {ftype_str} ."; r["relevance_score"]=50
        r["keywords"]=kw_extract(fname.lower(),5); r["topics"]=topic_dist(r["keywords"])
    return r

# ================================================
#  CSS — DARK BLUE + LIQUID GLASS
# ================================================
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800;900&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');

:root{
  --bg:#060B14;--bg2:#0B1220;--bg3:#101828;
  --acc:#0D7FE8;--acc2:#1A6EC9;--acc3:#0A5CB3;
  --teal:#36B8A0;--teal2:#2E9D8A;
  --red:#F03E5A;--orn:#FF8C42;--pur:#9B6FD4;--cya:#38C8F0;
  --t0:#FFFFFF;--t1:#E2E6F0;--t2:#9AA3BC;--t3:#5A6180;--t4:#2E3450;
  --g1:rgba(255,255,255,.042);--g2:rgba(255,255,255,.07);--g3:rgba(255,255,255,.11);
  --gb1:rgba(255,255,255,.07);--gb2:rgba(255,255,255,.11);--gb3:rgba(255,255,255,.18);
  --r8:8px;--r12:12px;--r16:16px;--r20:20px;--r28:28px;
  --gls:rgba(13,127,232,.08);--gls-bdr:rgba(13,127,232,.18);
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body,.stApp{background:var(--bg)!important;color:var(--t1)!important;font-family:'DM Sans',-apple-system,sans-serif!important;}

/* Ambient background - subtle blue/black gradient */
.stApp::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:
    radial-gradient(ellipse 55% 45% at -5% 0%,rgba(13,127,232,.04) 0%,transparent 60%),
    radial-gradient(ellipse 45% 35% at 105% 0%,rgba(54,184,160,.03) 0%,transparent 55%),
    radial-gradient(ellipse 35% 45% at 50% 110%,rgba(155,111,212,.02) 0%,transparent 60%),
    radial-gradient(ellipse 30% 30% at 80% 50%,rgba(13,127,232,.02) 0%,transparent 50%);}
.stApp::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:linear-gradient(rgba(255,255,255,.008) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.008) 1px,transparent 1px);
  background-size:80px 80px;}

header[data-testid="stHeader"],#MainMenu,footer,.stDeployButton,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
[data-testid="stSidebarCollapseButton"],[data-testid="collapsedControl"]{display:none!important}

/* ===== SIDEBAR ===== */
section[data-testid="stSidebar"]{
  display:block!important;transform:translateX(0)!important;visibility:visible!important;
  background:rgba(4,7,16,.97)!important;
  backdrop-filter:blur(40px) saturate(200%)!important;
  -webkit-backdrop-filter:blur(40px) saturate(200%)!important;
  border-right:1px solid rgba(255,255,255,.07)!important;
  box-shadow:4px 0 40px rgba(0,0,0,.5)!important;
  width:220px!important;min-width:220px!important;max-width:220px!important;
  padding:1.3rem .9rem 1rem!important;
}
section[data-testid="stSidebar"]>div{width:220px!important;padding:0!important;}

/* ===== LIQUID GLASS BUTTONS — SIDEBAR ===== */
section[data-testid="stSidebar"] .stButton>button{
  position:relative;overflow:hidden;
  background:rgba(255,255,255,.04)!important;
  backdrop-filter:blur(20px) saturate(180%)!important;
  -webkit-backdrop-filter:blur(20px) saturate(180%)!important;
  border:1px solid rgba(255,255,255,.09)!important;
  border-top-color:rgba(255,255,255,.15)!important;
  border-radius:12px!important;
  box-shadow:0 2px 12px rgba(0,0,0,.3),inset 0 1px 0 rgba(255,255,255,.08),inset 0 -1px 0 rgba(0,0,0,.15)!important;
  color:#9AA3BC!important;-webkit-text-fill-color:#9AA3BC!important;
  font-family:'DM Sans',sans-serif!important;font-weight:500!important;font-size:.83rem!important;
  padding:.52rem .9rem!important;text-align:left!important;justify-content:flex-start!important;
  width:100%!important;margin-bottom:.18rem!important;
  transition:all .15s cubic-bezier(.4,0,.2,1)!important;
}
section[data-testid="stSidebar"] .stButton>button::before{
  content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.18),transparent);
  pointer-events:none;
}
section[data-testid="stSidebar"] .stButton>button::after{
  content:'';position:absolute;inset:0;border-radius:12px;
  background:radial-gradient(circle at 50% 0%,rgba(255,255,255,.05),transparent 70%);
  pointer-events:none;
}
section[data-testid="stSidebar"] .stButton>button:hover{
  background:rgba(13,127,232,.12)!important;
  border-color:rgba(13,127,232,.3)!important;
  border-top-color:rgba(13,127,232,.4)!important;
  box-shadow:0 4px 20px rgba(13,127,232,.15),inset 0 1px 0 rgba(255,255,255,.1),inset 0 -1px 0 rgba(0,0,0,.1)!important;
  color:#FFFFFF!important;-webkit-text-fill-color:#FFFFFF!important;
  transform:translateY(-1px)!important;
}
section[data-testid="stSidebar"] .stButton>button:active{transform:translateY(0)!important;}
section[data-testid="stSidebar"] .stButton>button p,
section[data-testid="stSidebar"] .stButton>button span{color:inherit!important;-webkit-text-fill-color:inherit!important;}

/* Main buttons - transparent */
.stButton>button{
  background:transparent!important;
  border:1px solid rgba(255,255,255,.1)!important;
  border-radius:10px!important;color:#C8CEDE!important;-webkit-text-fill-color:#C8CEDE!important;
  font-family:'DM Sans',sans-serif!important;font-weight:500!important;font-size:.82rem!important;
  padding:.45rem .8rem!important;
  box-shadow:none!important;
  transition:all .12s ease!important;
}
.stButton>button:hover{
  background:rgba(13,127,232,.1)!important;
  border-color:rgba(13,127,232,.2)!important;
  color:#fff!important;-webkit-text-fill-color:#fff!important;
  box-shadow:0 2px 8px rgba(13,127,232,.1)!important;
  transform:translateY(-1px)!important;
}
.stButton>button:active{transform:translateY(0)!important;}
.stButton>button p,.stButton>button span{color:inherit!important;-webkit-text-fill-color:inherit!important;}

/* Layout */
.block-container{padding-top:.3rem!important;padding-bottom:4rem!important;max-width:1400px!important;position:relative;z-index:1;padding-left:.9rem!important;padding-right:.9rem!important;}

/* Inputs */
.stTextInput input,.stTextArea textarea{
  background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;
  border-radius:var(--r12)!important;color:var(--t1)!important;
  font-family:'DM Sans',sans-serif!important;font-size:.84rem!important;
}
.stTextInput input:focus,.stTextArea textarea:focus{
  border-color:rgba(13,127,232,.5)!important;
  box-shadow:0 0 0 3px rgba(13,127,232,.1)!important;
}
.stTextInput label,.stTextArea label,.stSelectbox label,.stFileUploader label,.stNumberInput label{
  color:var(--t3)!important;font-size:.59rem!important;letter-spacing:.11em!important;
  text-transform:uppercase!important;font-weight:700!important;
}

/* Cards */
.glass{background:rgba(255,255,255,.04);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,.08);border-radius:var(--r20);box-shadow:0 0 0 1px rgba(255,255,255,.03) inset,0 6px 36px rgba(0,0,0,.35);position:relative;overflow:hidden;}
.glass::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.1),transparent);pointer-events:none;}

.post-card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:var(--r20);margin-bottom:.6rem;overflow:hidden;box-shadow:0 2px 24px rgba(0,0,0,.28);transition:border-color .15s,transform .15s,box-shadow .15s;}
.post-card:hover{border-color:rgba(13,127,232,.25);transform:translateY(-2px);box-shadow:0 8px 32px rgba(13,127,232,.1);}

.sc{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:var(--r20);padding:.9rem 1rem;margin-bottom:.6rem;}
.scard{background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.07);border-radius:var(--r16);padding:.8rem 1rem;margin-bottom:.42rem;transition:border-color .13s,transform .12s,box-shadow .13s;}
.scard:hover{border-color:rgba(13,127,232,.2);transform:translateY(-1px);box-shadow:0 4px 20px rgba(13,127,232,.08);}

.mbox{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:var(--r16);padding:.9rem;text-align:center;}
.abox{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.09);border-radius:var(--r16);padding:1rem;margin-bottom:.6rem;}

/* Analysis boxes */
.pbox-acc{background:rgba(13,127,232,.06);border:1px solid rgba(13,127,232,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.5rem;}
.pbox-teal{background:rgba(54,184,160,.06);border:1px solid rgba(54,184,160,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.5rem;}
.pbox-pur{background:rgba(155,111,212,.06);border:1px solid rgba(155,111,212,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.5rem;}
.pbox-red{background:rgba(240,62,90,.06);border:1px solid rgba(240,62,90,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.5rem;}
.pbox-orn{background:rgba(255,140,66,.06);border:1px solid rgba(255,140,66,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.5rem;}

/* AI cards */
.ai-card{background:linear-gradient(135deg,rgba(13,127,232,.07),rgba(54,184,160,.04));border:1px solid rgba(13,127,232,.2);border-radius:var(--r16);padding:1.1rem;margin-bottom:.7rem;position:relative;overflow:hidden;}
.ai-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(13,127,232,.3),transparent);}

.conn-card{background:linear-gradient(135deg,rgba(54,184,160,.06),rgba(13,127,232,.04));border:1px solid rgba(54,184,160,.2);border-radius:var(--r16);padding:1rem;margin-bottom:.6rem;position:relative;}
.conn-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(54,184,160,.3),transparent);}

.repo-card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:var(--r16);padding:1rem;margin-bottom:.5rem;transition:all .15s;}
.repo-card:hover{border-color:rgba(13,127,232,.22);box-shadow:0 4px 20px rgba(13,127,232,.08);}

.chart-wrap{background:rgba(255,255,255,.025);border:1px solid rgba(255,255,255,.06);border-radius:var(--r12);padding:.6rem;margin-bottom:.6rem;}

.compose-box{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:var(--r20);padding:1.1rem 1.3rem;margin-bottom:.8rem;}

/* Metric values */
.mval-acc{font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:900;background:linear-gradient(135deg,var(--acc),var(--cya));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-teal{font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:900;background:linear-gradient(135deg,var(--teal),var(--cya));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-pur{font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:900;background:linear-gradient(135deg,var(--pur),var(--acc));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-red{font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:900;background:linear-gradient(135deg,var(--red),var(--orn));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mlbl{font-size:.57rem;color:var(--t3);margin-top:4px;letter-spacing:.1em;text-transform:uppercase;font-weight:700;}

/* Badges & tags */
.tag{display:inline-block;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);border-radius:50px;padding:2px 9px;font-size:.62rem;color:var(--t2);margin:2px;font-weight:500;}
.badge-acc{display:inline-block;background:rgba(13,127,232,.12);border:1px solid rgba(13,127,232,.25);border-radius:50px;padding:2px 9px;font-size:.62rem;font-weight:700;color:#5BAAFF;}
.badge-teal{display:inline-block;background:rgba(54,184,160,.12);border:1px solid rgba(54,184,160,.25);border-radius:50px;padding:2px 9px;font-size:.62rem;font-weight:700;color:#36B8A0;}
.badge-red{display:inline-block;background:rgba(240,62,90,.12);border:1px solid rgba(240,62,90,.25);border-radius:50px;padding:2px 9px;font-size:.62rem;font-weight:700;color:var(--red);}
.badge-pur{display:inline-block;background:rgba(155,111,212,.12);border:1px solid rgba(155,111,212,.25);border-radius:50px;padding:2px 9px;font-size:.62rem;font-weight:700;color:#B98FE8;}
.badge-orn{display:inline-block;background:rgba(255,140,66,.12);border:1px solid rgba(255,140,66,.25);border-radius:50px;padding:2px 9px;font-size:.62rem;font-weight:700;color:var(--orn);}

@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.7)}}
.dot-on{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--teal);animation:pulse 2.5s infinite;margin-right:4px;vertical-align:middle;}
.dot-off{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--t4);margin-right:4px;vertical-align:middle;}

@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.pw{animation:fadeUp .2s ease both;}

/* Chat bubbles */
.bme{background:linear-gradient(135deg,rgba(13,127,232,.2),rgba(54,184,160,.1));border:1px solid rgba(13,127,232,.25);border-radius:18px 18px 4px 18px;padding:.55rem .88rem;max-width:70%;margin-left:auto;margin-bottom:5px;font-size:.82rem;line-height:1.6;}
.bthem{background:var(--g2);border:1px solid var(--gb1);border-radius:18px 18px 18px 4px;padding:.55rem .88rem;max-width:70%;margin-bottom:5px;font-size:.82rem;line-height:1.6;}
.cmt{background:rgba(255,255,255,.03);border:1px solid var(--gb1);border-radius:var(--r12);padding:.5rem .85rem;margin-bottom:.25rem;}

/* Tabs */
.stTabs [data-baseweb="tab-list"]{background:rgba(255,255,255,.03)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;padding:3px!important;gap:2px!important;}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--t3)!important;border-radius:9px!important;font-size:.74rem!important;font-family:'DM Sans',sans-serif!important;font-weight:500!important;}
.stTabs [aria-selected="true"]{background:rgba(13,127,232,.14)!important;color:var(--cya)!important;border:1px solid rgba(13,127,232,.25)!important;font-weight:700!important;}
.stTabs [data-baseweb="tab-panel"]{background:transparent!important;padding-top:.8rem!important;}

/* Profile */
.prof-hero{background:rgba(255,255,255,.04);backdrop-filter:blur(32px);border:1px solid rgba(255,255,255,.09);border-radius:var(--r28);padding:1.6rem;display:flex;gap:1.2rem;align-items:flex-start;box-shadow:0 8px 48px rgba(0,0,0,.4);margin-bottom:1rem;}
.prof-av{width:76px;height:76px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:'Syne',sans-serif;font-weight:800;font-size:1.6rem;color:white;flex-shrink:0;border:2px solid rgba(255,255,255,.12);}

/* Misc */
hr{border:none;border-top:1px solid rgba(255,255,255,.07)!important;margin:.8rem 0;}
.stAlert{background:var(--g1)!important;border:1px solid var(--gb1)!important;border-radius:var(--r16)!important;}
.stSelectbox [data-baseweb="select"]{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;}
.stFileUploader section{background:rgba(255,255,255,.03)!important;border:1.5px dashed var(--gb2)!important;border-radius:var(--r16)!important;}
.stExpander{background:var(--g1);border:1px solid var(--gb1);border-radius:var(--r16);}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-thumb{background:var(--t4);border-radius:4px;}
.js-plotly-plot .plotly .modebar{display:none!important;}

.dtxt{display:flex;align-items:center;gap:.7rem;margin:.75rem 0;font-size:.57rem;color:var(--t3);letter-spacing:.10em;text-transform:uppercase;font-weight:700;}
.dtxt::before,.dtxt::after{content:'';flex:1;height:1px;background:var(--gb1);}

/* Sidebar logo & labels */
.sb-logo{display:flex;align-items:center;gap:9px;margin-bottom:1.5rem;padding:.2rem .3rem;}
.sb-logo-icon{width:36px;height:36px;border-radius:11px;background:linear-gradient(135deg,#0D7FE8,#36B8A0);display:flex;align-items:center;justify-content:center;font-size:.92rem;flex-shrink:0;box-shadow:0 4px 12px rgba(13,127,232,.3);}
.sb-logo-txt{font-family:'Syne',sans-serif;font-weight:900;font-size:1.25rem;letter-spacing:-.04em;background:linear-gradient(135deg,#0D7FE8,#36B8A0);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.sb-lbl{font-size:.53rem;font-weight:700;color:var(--t4);letter-spacing:.14em;text-transform:uppercase;padding:0 .2rem;margin-bottom:.35rem;margin-top:.85rem;}

h1{font-family:'Syne',sans-serif!important;font-size:1.55rem!important;font-weight:800!important;letter-spacing:-.03em;color:var(--t0)!important;}
h2{font-family:'Syne',sans-serif!important;font-size:1rem!important;font-weight:700!important;color:var(--t0)!important;}
label{color:var(--t2)!important;}
.stCheckbox label,.stRadio label{color:var(--t1)!important;}
.stRadio>div{display:flex!important;gap:4px!important;flex-wrap:wrap!important;}
.stRadio>div>label{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:50px!important;padding:.28rem .78rem!important;font-size:.73rem!important;cursor:pointer!important;color:var(--t2)!important;}
input[type="number"]{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;color:var(--t1)!important;}

/* Progress bars */
.prog-bar-track{background:rgba(255,255,255,.06);border-radius:50px;height:6px;margin:.35rem 0;}
.prog-bar-fill{height:6px;border-radius:50px;transition:width .6s ease;}

/* Score ring */
.score-ring{position:relative;display:inline-flex;align-items:center;justify-content:center;}

/* API Banner */
.api-banner{background:linear-gradient(135deg,rgba(155,111,212,.07),rgba(56,200,240,.05));border:1px solid rgba(155,111,212,.22);border-radius:var(--r16);padding:.9rem 1.1rem;margin-bottom:.8rem;}
.ml-feat{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:var(--r12);padding:.65rem .85rem;margin-bottom:.38rem;}

/* Sidebar active state injected dynamically */
</style>""",unsafe_allow_html=True)

# ================================================
#  HTML HELPERS
# ================================================
def avh(initials,sz=40,grad=None):
    fs=max(sz//3,9)
    bg=grad or "linear-gradient(135deg,#0D7FE8,#36B8A0)"
    return f'<div style="width:{sz}px;height:{sz}px;border-radius:50%;background:{bg};display:flex;align-items:center;justify-content:center;font-family:Syne,sans-serif;font-weight:800;font-size:{fs}px;color:white;flex-shrink:0;border:1.5px solid rgba(255,255,255,.12)">{initials}</div>'

def tags_html(tags):
    return ' '.join(f'<span class="tag">{t}</span>' for t in (tags or []))

def badge(s):
    m={"Publicado":"badge-teal","Concluído":"badge-pur"}
    return f'<span class="{m.get(s,"badge-acc")}">{s}</span>'

def prog_bar(val,color="#0D7FE8",max_val=100):
    pct=min(100,val/max_val*100) if max_val>0 else 0
    return f'<div class="prog-bar-track"><div class="prog-bar-fill" style="width:{pct:.0f}%;background:{color}"></div></div>'

def pc_dark():
    return dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#5A6180",family="DM Sans",size=11),
                margin=dict(l=10,r=10,t=38,b=10),
                xaxis=dict(showgrid=False,color="#5A6180",tickfont=dict(size=10)),
                yaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,.04)",color="#5A6180",tickfont=dict(size=10)))

# ================================================
#  NAVIGATION
# ================================================
NAV=[("feed","Feed de Pesquisas","acc"),("search","Busca Avançada","cya"),("knowledge","Rede de Conexões","teal"),
     ("repository","Repositório Pessoal","orn"),("analytics","Painel de Análises","pur"),
     ("img_search","Visão IA Científica","acc"),("chat","Mensagens","teal"),("settings","Configurações","red")]

def render_nav():
    email=st.session_state.current_user
    u=guser(); name=u.get("name","?"); ini_=ini(name); g=ugrad(email); cur=st.session_state.page
    with st.sidebar:
        st.markdown('<div class="sb-logo"><div class="sb-logo-icon">🔬</div><div class="sb-logo-txt">Nebula</div></div>',unsafe_allow_html=True)
        st.markdown('<div class="sb-lbl">Navegação</div>',unsafe_allow_html=True)
        # Active highlighting
        active_css=""
        for i,(key,label,col) in enumerate(NAV):
            if cur==key and not st.session_state.profile_view:
                cc_map={"acc":"#0D7FE8","teal":"#36B8A0","cya":"#38C8F0","orn":"#FF8C42","pur":"#9B6FD4","red":"#F03E5A"}
                c=cc_map.get(col,"#0D7FE8")
                active_css+=(f'section[data-testid="stSidebar"] [data-testid="stVerticalBlock"]'
                              f' > [data-testid="stVerticalBlock"]:nth-child({i+2})'
                              f' .stButton>button{{color:{c}!important;-webkit-text-fill-color:{c}!important;'
                              f'background:rgba(13,127,232,.12)!important;border-color:{c}33!important;font-weight:700!important;'
                              f'box-shadow:0 0 0 1px {c}20 inset,0 4px 16px rgba(13,127,232,.15)!important;}}')
        if active_css: st.markdown(f'<style>{active_css}</style>',unsafe_allow_html=True)
        for key,label,col in NAV:
            if st.button(label,key=f"sb_{key}",use_container_width=True):
                st.session_state.profile_view=None
                st.session_state.page=key
                st.rerun()
        # Notifications
        notifs=st.session_state.get("notifications",[])
        if notifs:
            st.markdown(f'<div style="margin:.6rem .2rem .35rem;font-size:.57rem;color:var(--acc);font-weight:700;letter-spacing:.09em;text-transform:uppercase">🔔 {len(notifs)} notificações</div>',unsafe_allow_html=True)
        st.markdown("<hr>",unsafe_allow_html=True)
        st.markdown('<div class="sb-lbl">Claude API Key</div>',unsafe_allow_html=True)
        ak=st.text_input("",placeholder="sk-ant-...",type="password",key="sb_apikey",label_visibility="collapsed",value=st.session_state.anthropic_key)
        if ak!=st.session_state.anthropic_key: st.session_state.anthropic_key=ak; save_db(); st.rerun()
        st.markdown(f'<div style="font-size:.6rem;color:var(--t3);margin-top:.2rem">Status: {"Ativo" if st.session_state.anthropic_key.startswith("sk-") else "Inativo"}</div>',unsafe_allow_html=True)

# ================================================
#  RENDERERS (Posts, Articles)
# ================================================
def render_post(p,ctx="feed",compact=False):
    if not p: return
    email=st.session_state.current_user
    is_liked=email in p.get("liked_by",[])
    is_saved=any(a.get("id")==p["id"] and a.get("origin")=="platform" for a in st.session_state.saved_articles)

    # Deep analysis for post
    deep_analysis_data=st.session_state.deep_analysis_cache.get(f"post_{p['id']}")

    with st.container():
        st.markdown(f'<div class="post-card">',unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:.7rem">',unsafe_allow_html=True)
        st.markdown(avh(p["avatar"],48,ugrad(p["author_email"])),unsafe_allow_html=True)
        st.markdown(f'<div style="flex:1"><div style="font-family:Syne,sans-serif;font-size:.95rem;font-weight:700;color:var(--t0)}">{p["author"]}</div><div style="font-size:.68rem;color:var(--t3)}">{p["area"]} . {time_ago(p["date"])}</div></div>',unsafe_allow_html=True)
        st.markdown(badge(p["status"]),unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True) # Close flex header

        st.markdown(f'<div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:800;color:var(--t1);margin-bottom:.5rem;line-height:1.4">{p["title"]}</div>',unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:.8rem;color:var(--t2);line-height:1.7;margin-bottom:.8rem">{p["abstract"]}</p>',unsafe_allow_html=True)

        if not compact:
            st.markdown(tags_html(p["tags"]),unsafe_allow_html=True)
            st.markdown(f'<div style="display:flex;align-items:center;gap:1rem;margin-top:.8rem;font-size:.75rem;color:var(--t3)"><span>Curtidas: {p["likes"]}</span><span>Comentários: {len(p["comments"])}</span><span>Visualizações: {fmt_num(p["views"])}</span><span>Citações: {p.get("citations",0)}</span></div>',unsafe_allow_html=True)

            c1,c2,c3,c4=st.columns(4)
            with c1:
                if st.button(f'❤️ {"Curtido" if is_liked else "Curtir"}',key=f"like_{ctx}_{p['id']}",use_container_width=True):
                    if is_liked: p["likes"]-=1; p["liked_by"].remove(email)
                    else: p["likes"]+=1; p["liked_by"].append(email); record(p["tags"],1.5)
                    save_db(); st.rerun()
            with c2:
                if st.button(f'💾 {"Salvo" if is_saved else "Salvar"}',key=f"save_{ctx}_{p['id']}",use_container_width=True):
                    if is_saved: st.session_state.saved_articles=[a for a in st.session_state.saved_articles if not (a.get("id")==p["id"] and a.get("origin")=="platform")]
                    else: st.session_state.saved_articles.append({"id":p["id"],"title":p["title"],"authors":p["author"],"year":p["date"][:4],"source":"Nebula","url":"","citations":p.get("citations",0),"origin":"platform"})
                    save_db(); st.rerun()
            with c3:
                if st.button("Análise Profunda",key=f"deep_an_{ctx}_{p['id']}",use_container_width=True):
                    if not deep_analysis_data:
                        with st.spinner("Executando análise profunda…"):
                            deep_analysis_data=deep_analyze_research_algorithmic(p,st.session_state.feed_posts)
                            st.session_state.deep_analysis_cache[f"post_{p['id']}"]=deep_analysis_data
                    st.session_state.show_deep_analysis=p['id']
            with c4:
                if st.button("Comentar",key=f"comment_{ctx}_{p['id']}",use_container_width=True):
                    st.session_state.active_comment_post=p['id']

            # Render deep analysis if active
            if st.session_state.get("show_deep_analysis")==p['id'] and deep_analysis_data:
                st.markdown("<hr>",unsafe_allow_html=True)
                st.markdown('<h3 style="margin-bottom:.6rem">Análise Detalhada da Pesquisa</h3>',unsafe_allow_html=True)

                cda1,cda2,cda3=st.columns(3)
                with cda1: st.markdown(f'<div class="mbox"><div class="mval-acc">{deep_analysis_data.get("engagement",0):.1f}%</div><div class="mlbl">Engajamento</div></div>',unsafe_allow_html=True)
                with cda2: st.markdown(f'<div class="mbox"><div class="mval-teal">{deep_analysis_data.get("monthly_views",0):.1f}</div><div class="mlbl">Views/Mês</div></div>',unsafe_allow_html=True)
                with cda3: st.markdown(f'<div class="mbox"><div class="mval-pur">{deep_analysis_data.get("impact_tier","N/A")}</div><div class="mlbl">Impacto</div></div>',unsafe_allow_html=True)

                st.markdown(f'<div class="pbox-acc"><div style="font-size:.62rem;color:var(--acc);font-weight:700;margin-bottom:.4rem">Pontos Fortes</div>{"".join(f"<div style=\"font-size:.72rem;color:var(--t2);margin-bottom:.15rem\">. {s}</div>" for s in deep_analysis_data.get("strengths",[]))}</div>',unsafe_allow_html=True)
                st.markdown(f'<div class="pbox-orn"><div style="font-size:.62rem;color:var(--orn);font-weight:700;margin-bottom:.4rem">Melhorias Sugeridas</div>{"".join(f"<div style=\"font-size:.72rem;color:var(--t2);margin-bottom:.15rem\">. {s}</div>" for s in deep_analysis_data.get("improvements",[]))}</div>',unsafe_allow_html=True)
                st.markdown(f'<div class="pbox-red"><div style="font-size:.62rem;color:var(--red);font-weight:700;margin-bottom:.4rem">Lacunas Identificadas</div>{"".join(f"<div style=\"font-size:.72rem;color:var(--t2);margin-bottom:.15rem\">. {s}</div>" for s in deep_analysis_data.get("gaps",[]))}</div>',unsafe_allow_html=True)

                if deep_analysis_data.get("collab_candidates"):
                    st.markdown('<div class="dtxt">Potenciais Colaboradores</div>',unsafe_allow_html=True)
                    for cc in deep_analysis_data["collab_candidates"]:
                        st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:7px">{avh(ini(cc["name"]),28,ugrad(cc["email"]))}<div style="flex:1"><div style="font-size:.75rem;font-weight:600;color:var(--t0)}">{cc["name"]}</div><div style="font-size:.62rem;color:var(--t3)}">{cc["area"]}</div></div><span style="font-size:.62rem;color:var(--teal)}">Score: {cc["score"]}</span></div></div>',unsafe_allow_html=True)

                if deep_analysis_data.get("similar_posts"):
                    st.markdown('<div class="dtxt">Pesquisas Similares na Plataforma</div>',unsafe_allow_html=True)
                    for sp in deep_analysis_data["similar_posts"]:
                        st.markdown(f'<div class="scard"><div style="font-family:Syne,sans-serif;font-size:.8rem;font-weight:700;color:var(--t0)}">{sp["title"]}</div><div style="font-size:.65rem;color:var(--t3)}">{sp["author"]} . {time_ago(sp["date"])}</div></div>',unsafe_allow_html=True)

            # Comment section
            if st.session_state.get("active_comment_post")==p['id']:
                st.markdown("<hr>",unsafe_allow_html=True)
                st.markdown('<h3 style="margin-bottom:.6rem">Comentários</h3>',unsafe_allow_html=True)
                for c in p["comments"]:
                    ci=ini(c["user"]); cg=ugrad(c["user"])
                    st.markdown(f'<div class="cmt"><div style="display:flex;align-items:center;gap:7px;margin-bottom:.2rem">{avh(ci,26,cg)}<span style="font-size:.73rem;font-weight:700;color:var(--acc)}}">{c["user"]}</span></div><div style="font-size:.78rem;color:var(--t2);line-height:1.55;padding-left:33px">{c["text"]}</div></div>',unsafe_allow_html=True)
                new_comment=st.text_input("Seu comentário",key=f"new_comment_{p['id']}",label_visibility="collapsed")
                if st.button("Adicionar Comentário",key=f"add_comment_{p['id']}",use_container_width=True):
                    if new_comment:
                        p["comments"].append({"user":guser().get("name","Anônimo"),"text":new_comment})
                        save_db(); st.session_state.active_comment_post=None; st.rerun()

        st.markdown('</div>',unsafe_allow_html=True) # Close post-card

def render_article(a,idx,ctx="search"):
    is_saved=any(sa.get("title")==a["title"] and sa.get("source")==a["source"] for sa in st.session_state.saved_articles)
    st.markdown(f'<div class="scard">',unsafe_allow_html=True)
    st.markdown(f'<div style="font-family:Syne,sans-serif;font-size:.9rem;font-weight:700;color:var(--t0);margin-bottom:.3rem"><a href="{a["url"]}" target="_blank" style="color:inherit;text-decoration:none;">{a["title"]}</a></div>',unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:.72rem;color:var(--t3);margin-bottom:.4rem">{a["authors"]} . {a["year"]} . {a["source"]}</div>',unsafe_allow_html=True)
    st.markdown(f'<p style="font-size:.78rem;color:var(--t2);line-height:1.6;margin-bottom:.6rem">{a["abstract"]}...</p>',unsafe_allow_html=True)
    st.markdown(f'<div style="display:flex;align-items:center;gap:1rem;font-size:.7rem;color:var(--t3)"><span>Citações: {a["citations"]}</span><span>Origem: {a["origin"]}</span></div>',unsafe_allow_html=True)

    c1,c2=st.columns(2)
    with c1:
        if st.button(f'💾 {"Salvo" if is_saved else "Salvar"}',key=f"save_art_{ctx}_{idx}",use_container_width=True):
            if is_saved: st.session_state.saved_articles=[sa for sa in st.session_state.saved_articles if not (sa.get("title")==a["title"] and sa.get("source")==a["source"])]
            else: st.session_state.saved_articles.append(a)
            save_db(); st.rerun()
    with c2:
        if a["url"]:
            st.link_button("Abrir Artigo",a["url"],key=f"open_art_{ctx}_{idx}",use_container_width=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ================================================
#  PAGE: LOGIN
# ================================================
def page_login():
    st.markdown('<div class="pw" style="max-width:400px;margin:3rem auto">',unsafe_allow_html=True)
    st.markdown('<div class="glass" style="padding:2rem;text-align:center">',unsafe_allow_html=True)
    st.markdown('<div style="font-family:Syne,sans-serif;font-weight:900;font-size:2.2rem;letter-spacing:-.04em;background:linear-gradient(135deg,#0D7FE8,#36B8A0);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:.5rem">Nebula</div>',unsafe_allow_html=True)
    st.markdown('<p style="font-size:.85rem;color:var(--t2);margin-bottom:1.5rem">Plataforma de Repositório e Análise Científica</p>',unsafe_allow_html=True)

    if st.session_state.pending_verify:
        email=st.session_state.pending_verify["email"]
        code=st.session_state.pending_verify["code"]
        st.info(f"Código enviado para {email}. Verifique sua caixa de entrada.")
        vc=st.text_input("Código de verificação",key="vcode")
        if st.button("Verificar",use_container_width=True):
            if vc==code:
                st.session_state.users[email]=st.session_state.pending_verify["user_data"]
                st.session_state.logged_in=True
                st.session_state.current_user=email
                st.session_state.pending_verify=None
                save_db(); st.success("Cadastro concluído!"); st.rerun()
            else: st.error("Código incorreto.")
        if st.button("Voltar ao Login",key="back_login"): st.session_state.pending_verify=None; st.rerun()
        st.markdown('</div></div>',unsafe_allow_html=True); return

    if st.session_state.get("show_register",False):
        with st.form("register_form"):
            new_email=st.text_input("Email",key="reg_email")
            new_pass=st.text_input("Senha",type="password",key="reg_pass")
            new_name=st.text_input("Nome Completo",key="reg_name")
            new_area=st.text_input("Área de Pesquisa",key="reg_area")
            new_bolsa=st.text_input("Bolsa/Afiliação",key="reg_bolsa")
            if st.form_submit_button("Registrar",use_container_width=True):
                if new_email and new_pass and new_name and new_area:
                    if new_email in st.session_state.users: st.error("Email já registrado.")
                    else:
                        vcode=''.join(random.choices(string.digits,k=6))
                        st.session_state.pending_verify={
                            "email":new_email,"code":vcode,
                            "user_data":{"name":new_name,"password":hp(new_pass),"bio":"","area":new_area,"followers":0,"following":0,"verified":False,"2fa_enabled":False,"bolsa_afiliacao":new_bolsa,"h_index":0,"publications":0}
                        }
                        st.success(f"Código de verificação: {vcode} (simulado)") # Em um app real, enviaria por email
                        st.rerun()
                else: st.error("Preencha todos os campos obrigatórios.")
        if st.button("Já tenho conta",key="back_to_login"): st.session_state.show_register=False; st.rerun()
    else:
        with st.form("login_form"):
            email=st.text_input("Email",key="login_email")
            password=st.text_input("Senha",type="password",key="login_password")
            if st.form_submit_button("Entrar",use_container_width=True):
                user=st.session_state.users.get(email)
                if user and user["password"]==hp(password):
                    st.session_state.logged_in=True
                    st.session_state.current_user=email
                    st.rerun()
                else: st.error("Email ou senha incorretos.")
        if st.button("Criar conta",use_container_width=True): st.session_state.show_register=True; st.rerun()

    st.markdown('</div></div>',unsafe_allow_html=True)

# ================================================
#  PAGE: FEED (Removed, now part of Repository)
# ================================================
# A página 'feed' foi removida conforme solicitado.
# O conteúdo relevante foi integrado ou substituído por outras funcionalidades.

# ================================================
#  PAGE: PROFILE
# ================================================
def page_profile(target_email):
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown(f'<h1 style="padding-top:.8rem;margin-bottom:.9rem">Perfil do Pesquisador</h1>',unsafe_allow_html=True)

    email=st.session_state.current_user
    target_user_data=st.session_state.users.get(target_email,{})

    if not target_user_data:
        st.error("Usuário não encontrado.")
        if st.button("Voltar",key="prof_back"): st.session_state.profile_view=None; st.rerun()
        st.markdown('</div>',unsafe_allow_html=True); return

    is_my_profile=(email==target_email)
    is_followed=target_email in st.session_state.followed

    # Profile header
    st.markdown(f'<div class="prof-hero" style="background:{ugrad(target_email)}">',unsafe_allow_html=True)
    st.markdown(avh(ini(target_user_data.get("name","?")),76),unsafe_allow_html=True)
    st.markdown(f'<div><div style="font-family:Syne,sans-serif;font-size:1.6rem;font-weight:800;color:var(--t0)}">{target_user_data.get("name","?")}</div><div style="font-size:.85rem;color:var(--t1);margin-top:.2rem">{target_user_data.get("area","")} . {target_user_data.get("bolsa_afiliacao","")}</div><div style="font-size:.7rem;color:var(--t2);margin-top:.5rem">{target_user_data.get("bio","Sem biografia.")}</div></div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

    c1,c2,c3,c4=st.columns(4)
    with c1: st.markdown(f'<div class="mbox"><div class="mval-acc">{target_user_data.get("followers",0)}</div><div class="mlbl">Seguidores</div></div>',unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="mbox"><div class="mval-teal">{target_user_data.get("following",0)}</div><div class="mlbl">Seguindo</div></div>',unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="mbox"><div class="mval-pur">{target_user_data.get("publications",0)}</div><div class="mlbl">Publicações</div></div>',unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="mbox"><div class="mval-red">{target_user_data.get("h_index",0)}</div><div class="mlbl">Índice H</div></div>',unsafe_allow_html=True)

    st.markdown("<hr>",unsafe_allow_html=True)

    if not is_my_profile:
        col1,col2,col3=st.columns(3)
        with col1:
            if st.button("Voltar",key="prof_back",use_container_width=True): st.session_state.profile_view=None; st.rerun()
        with col2:
            if st.button("Seguir" if not is_followed else "Deixar de Seguir",key="prof_follow",use_container_width=True):
                if is_followed:
                    st.session_state.followed.remove(target_email)
                    target_user_data["followers"]=max(0,target_user_data.get("followers",0)-1)
                    st.session_state.users[email]["following"]=max(0,st.session_state.users[email].get("following",0)-1)
                else:
                    st.session_state.followed.append(target_email)
                    target_user_data["followers"]=target_user_data.get("followers",0)+1
                    st.session_state.users[email]["following"]=st.session_state.users[email].get("following",0)+1
                save_db(); st.rerun()
        with col3:
            if st.button("Mensagem",key="prof_chat",use_container_width=True):
                st.session_state.chat_messages.setdefault(target_email,[]); st.session_state.active_chat=target_email; st.session_state.page="chat"; st.rerun()
    else:
        if st.button("Editar Perfil",key="edit_my_profile",use_container_width=True):
            st.session_state.page="settings"; st.session_state.profile_view=None; st.rerun()

    st.markdown("<hr>",unsafe_allow_html=True)

    # User's posts
    user_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==target_email]
    if user_posts:
        st.markdown('<h2 style="margin-bottom:.8rem">Publicações</h2>',unsafe_allow_html=True)
        for p in sorted(user_posts,key=lambda x:x.get("date",""),reverse=True):
            render_post(p,ctx=f"profile_{target_email}",compact=True)
    else:
        st.markdown('<div style="color:var(--t3);padding:.8rem">Nenhuma publicação.</div>',unsafe_allow_html=True)

    st.markdown('</div>',unsafe_allow_html=True)

# ================================================
#  MAIN APP LOGIC
# ================================================
def main():
    inject_css()
    if not st.session_state.logged_in:
        page_login(); return
    render_nav()
    if st.session_state.profile_view:
        page_profile(st.session_state.profile_view); return
    {
        "feed":page_feed,"search":page_search,"knowledge":page_knowledge,
        "repository":page_repository,"analytics":page_analytics,
        "img_search":page_img_search,"chat":page_chat,"settings":page_settings,
    }.get(st.session_state.page,page_repository)() # Default para 'repository'

if __name__=="__main__":
    main()
