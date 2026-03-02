import subprocess, sys, os, json, hashlib, re, io, base64
from datetime import datetime
from collections import defaultdict, Counter
import streamlit as st

st.set_page_config(page_title="Nebula", page_icon="🔬", layout="wide", initial_sidebar_state="expanded")

# ═══════════════════════════════════════════════
#  BOOT — instala libs UMA VEZ (cache_resource)
# ═══════════════════════════════════════════════
@st.cache_resource(show_spinner="⚡ Iniciando Nebula v6…")
def _boot():
    def _pip(*pkgs):
        for p in pkgs:
            try: subprocess.check_call([sys.executable,"-m","pip","install",p,"-q"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except: pass
    try: import numpy as np
    except: _pip("numpy"); import numpy as np
    try: from PIL import Image as PI
    except: _pip("pillow"); from PIL import Image as PI
    try: import plotly.graph_objects as go
    except: _pip("plotly"); import plotly.graph_objects as go
    try: import requests as rq
    except: _pip("requests"); import requests as rq
    KM = None; sk = False
    try: from sklearn.cluster import KMeans; sk=True; KM=KMeans
    except:
        try: _pip("scikit-learn"); from sklearn.cluster import KMeans; sk=True; KM=KMeans
        except: pass
    ski=False; skf_=None
    try:
        from skimage import filters as skf; ski=True; skf_=skf
    except:
        try: _pip("scikit-image"); from skimage import filters as skf; ski=True; skf_=skf
        except: pass
    return {"np":np,"PI":PI,"go":go,"rq":rq,"sk":sk,"KM":KM,"ski":ski,"skf":skf_}

_L = _boot()
np=_L["np"]; PILImage=_L["PI"]; go=_L["go"]; requests=_L["rq"]
SKLEARN_OK=_L["sk"]; SKIMAGE_OK=_L["ski"]; KMeans=_L["KM"]

# ═══════════════════════════════════════════════
#  CONSTANTES
# ═══════════════════════════════════════════════
DB_FILE = "nebula_db.json"
CLAUDE_MODEL = "claude-haiku-4-5"

VIB = ["#00E676","#FFD60A","#4CC9F0","#FF3B5C","#B17DFF","#FF8C42","#FF4E8A","#00C9A7","#7BD3FF","#FFAB00"]

GRAD_POOL = [
    "135deg,#FF6B35,#F7C948","135deg,#00C9A7,#845EC2","135deg,#FF4E8A,#FF9A44",
    "135deg,#4ECDC4,#44A1A0","135deg,#6C63FF,#48C6EF","135deg,#F7971E,#FFD200",
    "135deg,#FF5F6D,#FFC371","135deg,#00E676,#4CC9F0","135deg,#B17DFF,#FF4E8A",
]

STOPWORDS = {"de","a","o","que","e","do","da","em","um","para","é","com","uma","os","no","se","na","por","mais","as","dos","como","mas","foi","ao","ele","das","tem","à","seu","sua","ou","ser","quando","muito","há","nos","já","está","eu","também","só","pelo","pela","até","isso","ela","entre","era","depois","sem","mesmo","aos","ter","seus","the","of","and","to","in","is","it","that","was","he","for","on","are","as","with","they","at","be","this","from","or","one","had","by","but","not","what","all","were","we","when","your","can","said","there","use","an","each","which","she","do","how","their","if","will"}

EMAP = {"pdf":"PDF","docx":"Word","xlsx":"Planilha","csv":"Dados","txt":"Texto","py":"Código","md":"Markdown","r":"Código R","ipynb":"Notebook","png":"Imagem","jpg":"Imagem","jpeg":"Imagem","webp":"Imagem","tiff":"Imagem","gif":"Imagem"}

SEED_POSTS = [
    {"id":1,"author":"Carlos Mendez","author_email":"carlos@nebula.ai","avatar":"CM","area":"Neurociência","title":"Privação de Sono e Plasticidade Sináptica em Ratos Wistar","abstract":"Investigamos como 24h de privação de sono afetam espinhas dendríticas. Redução de 34% na plasticidade hipocampal identificada com janela crítica nas primeiras 6h de recuperação.","tags":["neurociência","sono","memória","hipocampo","plasticidade"],"likes":47,"comments":[{"user":"Maria Silva","text":"Excelente metodologia! Como foi a contagem das espinhas?"}],"status":"Em andamento","date":"2026-02-10","liked_by":[],"saved_by":[],"connections":["sono","memória"],"views":312},
    {"id":2,"author":"Luana Freitas","author_email":"luana@nebula.ai","avatar":"LF","area":"Biomedicina","title":"CRISPR-Cas9 em Distrofias Musculares — Eficiência 78%","abstract":"Vetor AAV9 modificado para entrega de CRISPR no gene DMD com eficiência de 78% em modelos mdx. Redução de 62% nos sintomas em 90 dias. Ensaios fase I aprovados para 2027.","tags":["CRISPR","terapia gênica","DMD","AAV9","músculo"],"likes":93,"comments":[{"user":"Ana Costa","text":"Quando iniciam os trials clínicos?"},{"user":"Pedro ML","text":"Resultado impressionante!"}],"status":"Publicado","date":"2026-01-28","liked_by":[],"saved_by":[],"connections":["genômica","distrofia"],"views":891},
    {"id":3,"author":"Rafael Souza","author_email":"rafael@nebula.ai","avatar":"RS","area":"Computação","title":"Redes Neurais Quântico-Clássicas para TSP — 40% Menos Iterações","abstract":"Arquitetura híbrida variacional combinando qubits supercondutores com camadas densas clássicas. TSP resolvido com 40% menos iterações em instâncias até 128 cidades no IBM Quantum.","tags":["quantum ML","otimização","TSP","variacional","IBM"],"likes":201,"comments":[{"user":"Julia Ramos","text":"Qual a fidelidade dos qubits?"}],"status":"Em andamento","date":"2026-02-15","liked_by":[],"saved_by":[],"connections":["computação quântica","ML"],"views":1240},
    {"id":4,"author":"Priya Nair","author_email":"priya@nebula.ai","avatar":"PN","area":"Astrofísica","title":"Matéria Escura via Lentes Gravitacionais — Tensão 2.8σ","abstract":"Mapeamento com 100M de galáxias do DES Y3. Tensão de 2.8σ com ΛCDM em escalas menores que 1 Mpc. Dados sugerem modificação na equação de estado da energia escura.","tags":["astrofísica","matéria escura","cosmologia","DES","ΛCDM"],"likes":312,"comments":[],"status":"Publicado","date":"2026-02-01","liked_by":[],"saved_by":[],"connections":["cosmologia","energia escura"],"views":2180},
    {"id":5,"author":"João Lima","author_email":"joao@nebula.ai","avatar":"JL","area":"Psicologia","title":"Viés de Confirmação em Decisões Médicas Assistidas por IA","abstract":"Estudo duplo-cego com 240 médicos: IA mal calibrada amplifica vieses cognitivos em 22% dos diagnósticos. Proposta de framework de calibração ativa com feedback contínuo.","tags":["psicologia cognitiva","IA médica","viés","diagnóstico"],"likes":78,"comments":[{"user":"Carlos M.","text":"Muito relevante!"}],"status":"Publicado","date":"2026-02-08","liked_by":[],"saved_by":[],"connections":["cognição","IA clínica"],"views":456},
    {"id":6,"author":"Ana Pesquisadora","author_email":"demo@nebula.ai","avatar":"AP","area":"Inteligência Artificial","title":"LLMs como Ferramentas de Descoberta Científica — Meta-Análise","abstract":"Revisão sistemática de 143 estudos (2020–2026). 67% reportam aceleração no processo de hipótese. Principais desafios: alucinação factual (41%) e viés de seleção (28%).","tags":["LLM","descoberta científica","meta-análise","IA"],"likes":134,"comments":[{"user":"Rafael S.","text":"Inclui modelos multimodais?"}],"status":"Publicado","date":"2026-02-20","liked_by":[],"saved_by":[],"connections":["IA","LLM","ciência"],"views":987},
]

SEED_USERS = {
    "demo@nebula.ai":{"name":"Ana Pesquisadora","password":hashlib.sha256("demo123".encode()).hexdigest(),"bio":"Pesquisadora em IA e Ciências Cognitivas | UFMG | Meta-análises","area":"Inteligência Artificial","followers":128,"following":47,"verified":True,"2fa_enabled":False,"joined":"2024-01-15","publications":8,"citations":342},
    "carlos@nebula.ai":{"name":"Carlos Mendez","password":hashlib.sha256("nebula123".encode()).hexdigest(),"bio":"Neurocientista | UFMG | Plasticidade sináptica e sono","area":"Neurociência","followers":210,"following":45,"verified":True,"2fa_enabled":False,"joined":"2024-02-01","publications":14,"citations":876},
    "luana@nebula.ai":{"name":"Luana Freitas","password":hashlib.sha256("nebula123".encode()).hexdigest(),"bio":"Biomédica | FIOCRUZ | CRISPR e terapia gênica","area":"Biomedicina","followers":178,"following":62,"verified":True,"2fa_enabled":False,"joined":"2024-01-20","publications":11,"citations":534},
    "rafael@nebula.ai":{"name":"Rafael Souza","password":hashlib.sha256("nebula123".encode()).hexdigest(),"bio":"Computação Quântica | USP | Algoritmos híbridos","area":"Computação Quântica","followers":340,"following":88,"verified":True,"2fa_enabled":False,"joined":"2023-11-10","publications":19,"citations":1203},
    "priya@nebula.ai":{"name":"Priya Nair","password":hashlib.sha256("nebula123".encode()).hexdigest(),"bio":"Astrofísica | MIT | Dark matter & gravitational lensing","area":"Astrofísica","followers":520,"following":31,"verified":True,"2fa_enabled":False,"joined":"2023-09-05","publications":27,"citations":3120},
    "joao@nebula.ai":{"name":"João Lima","password":hashlib.sha256("nebula123".encode()).hexdigest(),"bio":"Psicólogo Cognitivo | UNICAMP | IA e vieses clínicos","area":"Psicologia","followers":95,"following":120,"verified":True,"2fa_enabled":False,"joined":"2024-03-01","publications":6,"citations":189},
}

CHAT_INIT = {
    "carlos@nebula.ai":[{"from":"carlos@nebula.ai","text":"Oi! Vi seu trabalho sobre LLMs na ciência.","time":"09:14"},{"from":"me","text":"Oi Carlos! Obrigada. Achei interessante sua pesquisa de sono.","time":"09:16"},{"from":"carlos@nebula.ai","text":"Podemos colaborar? Penso em aplicar LLMs para análise de EEG.","time":"09:17"}],
    "luana@nebula.ai":[{"from":"luana@nebula.ai","text":"Podemos colaborar no próximo projeto CRISPR + IA?","time":"ontem"},{"from":"me","text":"Com certeza! Tenho experiência com modelos preditivos de eficiência.","time":"ontem"}],
}

# ═══════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════
def hp(pw): return hashlib.sha256(pw.encode()).hexdigest()
def ini(n):
    if not isinstance(n,str): n=str(n)
    p=n.strip().split(); return ''.join(w[0].upper() for w in p[:2]) if p else "?"
def time_ago(ds):
    try:
        dt=datetime.strptime(ds,"%Y-%m-%d"); d=(datetime.now()-dt).days
        if d==0: return "hoje"
        if d==1: return "ontem"
        if d<7: return f"{d}d"
        if d<30: return f"{d//7}sem"
        if d<365: return f"{d//30}m"
        return f"{d//365}a"
    except: return ds
def fmt_num(n):
    try: n=int(n); return f"{n/1000:.1f}k" if n>=1000 else str(n)
    except: return str(n)
def guser():
    if not isinstance(st.session_state.get("users"),dict): return {}
    return st.session_state.users.get(st.session_state.current_user,{})
def is_online(e): return (hash(e+"on")%3)!=0
def ugrad(e): return f"linear-gradient({GRAD_POOL[hash(e or '')%len(GRAD_POOL)]})"
def ftype(fname): return EMAP.get(fname.split(".")[-1].lower() if "." in fname else "","Arquivo")
def area_tags(area):
    a=(area or "").lower()
    M={"ia":["machine learning","LLM","redes neurais"],"inteligência artificial":["machine learning","LLM"],"neurociência":["sono","memória","cognição","plasticidade"],"biologia":["célula","genômica","evolução"],"biomedicina":["CRISPR","terapia gênica","proteína"],"física":["quantum","astrofísica","partícula"],"computação":["algoritmo","software"],"computação quântica":["qubit","quantum","variacional"],"medicina":["diagnóstico","terapia","clínico"],"psicologia":["cognição","comportamento","viés"],"astrofísica":["galáxia","cosmologia","matéria escura"]}
    for k,v in M.items():
        if k in a: return v
    return [w.strip() for w in a.replace(","," ").split() if len(w)>3][:5]
def record(tags,w=1.0):
    e=st.session_state.get("current_user")
    if not e or not tags: return
    p=st.session_state.user_prefs.setdefault(e,defaultdict(float))
    for t in tags: p[t.lower()]+=w
def get_recs(email,n=3):
    pr=st.session_state.user_prefs.get(email,{})
    if not pr: return []
    def sc(p): return sum(pr.get(t.lower(),0) for t in p.get("tags",[])+p.get("connections",[]))
    scored=[(sc(p),p) for p in st.session_state.feed_posts if email not in p.get("liked_by",[])]
    return [p for s,p in sorted(scored,key=lambda x:-x[0]) if s>0][:n]

# ═══════════════════════════════════════════════
#  DB
# ═══════════════════════════════════════════════
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def save_db():
    try:
        with open(DB_FILE,"w",encoding="utf-8") as f:
            json.dump({"users":st.session_state.users,"feed_posts":st.session_state.feed_posts,"folders":st.session_state.folders,"user_prefs":{k:dict(v) for k,v in st.session_state.user_prefs.items()},"saved_articles":st.session_state.saved_articles,"followed":st.session_state.followed,"notifications":st.session_state.notifications},f,ensure_ascii=False,indent=2)
    except: pass

def init_state():
    if "initialized" in st.session_state: return
    st.session_state.initialized=True
    disk=load_db()
    du=disk.get("users",{})
    if not isinstance(du,dict): du={}
    st.session_state.setdefault("users",{**SEED_USERS,**du})
    st.session_state.setdefault("logged_in",False)
    st.session_state.setdefault("current_user",None)
    st.session_state.setdefault("page","feed")
    st.session_state.setdefault("profile_view",None)
    dp=disk.get("user_prefs",{})
    st.session_state.setdefault("user_prefs",{k:defaultdict(float,v) for k,v in dp.items()})
    rp=disk.get("feed_posts",[dict(p) for p in SEED_POSTS])
    for p in rp: p.setdefault("liked_by",[]); p.setdefault("saved_by",[]); p.setdefault("comments",[]); p.setdefault("views",200); p.setdefault("shares",0)
    st.session_state.setdefault("feed_posts",rp)
    st.session_state.setdefault("folders",disk.get("folders",{}))
    st.session_state.setdefault("folder_files_bytes",{})
    st.session_state.setdefault("chat_contacts",list(SEED_USERS.keys()))
    st.session_state.setdefault("chat_messages",{k:list(v) for k,v in CHAT_INIT.items()})
    st.session_state.setdefault("active_chat",None)
    st.session_state.setdefault("followed",disk.get("followed",["carlos@nebula.ai","luana@nebula.ai"]))
    st.session_state.setdefault("notifications",disk.get("notifications",["Carlos curtiu sua pesquisa sobre LLMs","Nova conexão sugerida: Rafael Souza","Priya Nair comentou no seu post","3 artigos novos na sua área"]))
    st.session_state.setdefault("scholar_cache",{})
    st.session_state.setdefault("saved_articles",disk.get("saved_articles",[]))
    st.session_state.setdefault("img_result",None)
    st.session_state.setdefault("claude_vision_result",None)
    st.session_state.setdefault("search_results",None)
    st.session_state.setdefault("last_sq","")
    st.session_state.setdefault("stats_data",{"h_index":4,"fator_impacto":3.8,"notes":""})
    st.session_state.setdefault("compose_open",False)
    st.session_state.setdefault("anthropic_key",os.environ.get("ANTHROPIC_API_KEY",""))
    st.session_state.setdefault("ai_conn_cache",{})
    st.session_state.setdefault("show_notif",False)

init_state()

# ═══════════════════════════════════════════════
#  CLAUDE AI — Haiku (rápido + barato)
# ═══════════════════════════════════════════════
def _claude_raw(messages, system="", max_tokens=900):
    key=st.session_state.get("anthropic_key","")
    if not key or not key.startswith("sk-"): return None,"Chave API inválida."
    try:
        body={"model":CLAUDE_MODEL,"max_tokens":max_tokens,"messages":messages}
        if system: body["system"]=system
        r=requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key":key,"anthropic-version":"2023-06-01","content-type":"application/json"},
            json=body,timeout=28)
        if r.status_code==200: return r.json()["content"][0]["text"],None
        return None,r.json().get("error",{}).get("message",f"HTTP {r.status_code}")
    except Exception as e: return None,str(e)

def claude_vision_analyze(img_bytes):
    """Análise REAL com Claude Vision — O QUE É e DO QUE É FEITA."""
    key=st.session_state.get("anthropic_key","")
    if not key or not key.startswith("sk-"): return None,"API key necessária"
    try:
        img=PILImage.open(io.BytesIO(img_bytes))
        buf=io.BytesIO(); img.convert("RGB").save(buf,format="JPEG",quality=82)
        b64=base64.b64encode(buf.getvalue()).decode()
        prompt="""Você é especialista em análise de imagens científicas. Analise com máxima precisão.

Responda APENAS em JSON puro (sem markdown, sem ```):

{
  "o_que_e": "<o que EXATAMENTE é esta imagem: ex 'Microscopia confocal de neurônios corticais corados com DAPI' ou 'Gel SDS-PAGE mostrando bandas proteicas' ou 'Imagem de telescópio Hubble de galáxia espiral'>",
  "de_que_e_feita": "<composição detalhada: estruturas anatômicas, moléculas, materiais, organismos, objetos visíveis>",
  "tipo_imagem": "<tipo técnico exato: H&E histologia, fluorescência DAPI, Western blot, TEM, SEM, confocal, difração X, espectroscopia, gráfico científico, diagrama molecular, imagem astronômica, tomografia, etc>",
  "area_ciencia": "<área científica: neurociência, oncologia, bioquímica, física de partículas, astronomia, cristalografia, etc>",
  "tecnica": "<técnica de aquisição: corte histológico, imunofluorescência, PCR gel, sequenciamento, espectroscopia, simulação, etc>",
  "estruturas": ["<estrutura 1 com localização>","<estrutura 2>","<estrutura 3>"],
  "cores_significado": "<o que cada cor/contraste representa nesta técnica>",
  "escala": "<estimativa de escala: nanômetros, micrômetros, milímetros, parsecs>",
  "qualidade": "<Alta/Média/Baixa com justificativa>",
  "achados_principais": "<observações científicas mais importantes, padrões notáveis, anomalias>",
  "confianca": <número 0-100>,
  "termos_busca": "<4-6 termos científicos para buscar artigos>"
}"""
        r=requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key":key,"anthropic-version":"2023-06-01","content-type":"application/json"},
            json={"model":CLAUDE_MODEL,"max_tokens":1100,"messages":[{"role":"user","content":[{"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":b64}},{"type":"text","text":prompt}]}]},timeout=32)
        if r.status_code==200:
            text=r.json()["content"][0]["text"].strip()
            text=re.sub(r'^```json\s*','',text); text=re.sub(r'\s*```$','',text)
            return json.loads(text),None
        return None,r.json().get("error",{}).get("message",f"HTTP {r.status_code}")
    except Exception as e: return None,str(e)

def claude_connections(users_data,posts_data,email):
    """Claude sugere conexões científicas com justificativa real."""
    u=users_data.get(email,{})
    my_posts=[p for p in posts_data if p.get("author_email")==email]
    my_tags=list({t for p in my_posts for t in p.get("tags",[])})[:12]
    others=[{"email":ue,"name":ud.get("name",""),"area":ud.get("area",""),"bio":ud.get("bio","")[:80],"tags":list({t for p in posts_data if p.get("author_email")==ue for t in p.get("tags",[])})[:8],"publications":ud.get("publications",0)} for ue,ud in users_data.items() if ue!=email]
    payload={"meu_perfil":{"nome":u.get("name",""),"area":u.get("area",""),"bio":u.get("bio","")[:100],"tags_pesquisa":my_tags,"publicacoes":u.get("publications",0)},"pesquisadores":others[:14]}
    text,err=_claude_raw([{"role":"user","content":f"""Sistema de recomendação científica. Sugira as 4 melhores colaborações.

Dados: {json.dumps(payload,ensure_ascii=False)}

Critérios: complementaridade científica, potencial interdisciplinar, compatibilidade metodológica.

Responda APENAS JSON puro:
{{"sugestoes":[{{"email":"<email>","razao_cientifica":"<2 frases sobre por que colaborar>","potencial_pesquisa":"<que pesquisa poderiam fazer juntos>","score":<0-100>,"temas_comuns":["<tema1>","<tema2>"]}}]}}"""}],max_tokens=700)
    if text:
        try:
            t=re.sub(r'^```json\s*','',text.strip()); t=re.sub(r'\s*```$','',t)
            return json.loads(t),None
        except: return None,"Erro ao parsear"
    return None,err

def claude_ai_draft(title, area):
    """Claude gera rascunho de resumo científico."""
    text,err=_claude_raw([{"role":"user","content":f"Gere um resumo científico de 100 palavras para a pesquisa: '{title}' na área de {area}. Estilo acadêmico com hipótese, método e resultados esperados. Apenas o texto."}],max_tokens=180)
    return text,err

# ═══════════════════════════════════════════════
#  ML IMAGE PIPELINE — otimizado (192px, cached)
# ═══════════════════════════════════════════════
def sobel_fast(gray_f32):
    """Sobel multi-direcional com numpy/skimage."""
    try:
        if SKIMAGE_OK and _L["skf"]:
            sx=_L["skf"].sobel_h(gray_f32); sy=_L["skf"].sobel_v(gray_f32)
        else:
            kx=np.array([[-1,0,1],[-2,0,2],[-1,0,1]],dtype=np.float32)/8.0
            def c2d(im,k):
                p=np.pad(im,1,mode='edge'); out=np.zeros_like(im)
                for i in range(3):
                    for j in range(3): out+=k[i,j]*p[i:i+im.shape[0],j:j+im.shape[1]]
                return out
            sx=c2d(gray_f32,kx); sy=c2d(gray_f32,kx.T)
        mag=np.sqrt(sx**2+sy**2)
        return {"magnitude":mag,"sx":sx,"sy":sy,"mean":float(mag.mean()),"max":float(mag.max()),"density":float((mag>mag.mean()*1.5).mean()),"hist":np.histogram(mag,bins=20,range=(0,mag.max()+1e-5))[0].tolist()}
    except:
        gx=np.gradient(gray_f32,axis=1); gy=np.gradient(gray_f32,axis=0); mag=np.sqrt(gx**2+gy**2)
        return {"magnitude":mag,"sx":gx,"sy":gy,"mean":float(mag.mean()),"max":float(mag.max()),"density":float((mag>mag.mean()*1.5).mean()),"hist":np.histogram(mag,bins=20)[0].tolist()}

def fft_fast(gray_f32):
    fft=np.fft.fftshift(np.fft.fft2(gray_f32)); mag=np.abs(fft)
    h,w=mag.shape; total=mag.sum()+1e-5
    Y,X=np.ogrid[:h,:w]; dist=np.sqrt((X-w//2)**2+(Y-h//2)**2); r=min(h,w)//2
    lf=float(mag[dist<r*0.12].sum()/total); mf=float(mag[(dist>=r*0.12)&(dist<r*0.45)].sum()/total); hf=float(mag[dist>=r*0.45].sum()/total)
    outer=np.concatenate([mag[:h//4,:].ravel(),mag[3*h//4:,:].ravel()])
    per=float(np.percentile(outer,99))/(float(np.mean(outer))+1e-5)
    return {"lf":round(lf,3),"mf":round(mf,3),"hf":round(hf,3),"periodic":per>12,"per_score":round(per,1),"dominant":"fina" if hf>0.5 else("média" if mf>0.3 else "grossa")}

def glcm_fast(gray_u8):
    try:
        if SKIMAGE_OK:
            from skimage.feature import graycomatrix,graycoprops
            g=(gray_u8//4).astype(np.uint8)
            glcm=graycomatrix(g,[1,3],[0,np.pi/4,np.pi/2],levels=64,symmetric=True,normed=True)
            props={p:float(graycoprops(glcm,p).mean()) for p in ['contrast','homogeneity','energy','correlation','dissimilarity']}
            props['entropy']=float(-np.sum(glcm[glcm>0]*np.log2(glcm[glcm>0]+1e-12)))
        else:
            g=gray_u8.astype(np.float32)/255.0; gx=np.gradient(g,axis=1); gy=np.gradient(g,axis=0)
            contrast=float(np.sqrt(gx**2+gy**2).mean()*100); hst=np.histogram(g,bins=64)[0]; hn=hst/hst.sum()+1e-12
            props={"contrast":round(contrast,3),"homogeneity":round(1/(1+contrast/50),3),"energy":round(float(np.var(g)),3),"correlation":0.7,"dissimilarity":round(contrast*0.5,3),"entropy":round(float(-np.sum(hn*np.log2(hn))),3)}
        h=props.get('homogeneity',0.5); c=props.get('contrast',20)
        props['tipo']="homogênea" if h>0.75 else("muito texturizada" if c>50 else("periódica" if props.get('energy',0)>0.1 else "complexa"))
        return props
    except: return {"contrast":20.0,"homogeneity":0.5,"energy":0.1,"correlation":0.7,"dissimilarity":10.0,"entropy":4.0,"tipo":"indefinida"}

def kmeans_fast(arr_u8,k=7):
    if not SKLEARN_OK or KMeans is None: return []
    try:
        h,w=arr_u8.shape[:2]; step=max(1,(h*w)//4000)
        flat=arr_u8.reshape(-1,3)[::step].astype(np.float32)
        km=KMeans(n_clusters=k,random_state=42,n_init=5,max_iter=60).fit(flat)
        centers=km.cluster_centers_.astype(int); counts=Counter(km.labels_); total=sum(counts.values())
        pal=[]
        for i in np.argsort([-counts[j] for j in range(k)]):
            r2,g2,b2=centers[i]; pct=counts[i]/total*100
            temp="quente" if r2>b2+20 else("fria" if b2>r2+20 else "neutra")
            pal.append({"rgb":(int(r2),int(g2),int(b2)),"hex":"#{:02x}{:02x}{:02x}".format(int(r2),int(g2),int(b2)),"pct":round(pct,1),"temp":temp})
        return pal
    except: return []

def classify_ml(sobel_r,fft_r,glcm_r,color,n_kp,pal):
    ei=sobel_r["mean"]; ed=sobel_r["density"]; hom=glcm_r.get("homogeneity",0.5)
    contrast=glcm_r.get("contrast",20); sym=color["sym"]; entropy=color["entropy"]
    mr,mg2,mb=color["r"],color["g"],color["b"]; per=fft_r["periodic"]; per_sc=fft_r["per_score"]
    scores={}
    scores["Histopatologia H&E"]=30*(mr>140 and mb>100 and mg2<mr)+20*(n_kp>80)+20*(contrast>30)+15*(ed>0.12)+15*(entropy>4.5)
    scores["Fluorescência DAPI"]=45*(mb>150 and mb>mr+30)+20*(entropy>5)+20*(ed>0.1)+15*(n_kp>30)
    scores["Fluorescência GFP"]=45*(mg2>150 and mg2>mr+30)+20*(entropy>4.5)+20*(ed>0.08)+15*(n_kp>20)
    scores["Cristalografia/Difração"]=40*per+25*(sym>0.75)+15*(hom>0.7)+20*(per_sc>15)
    scores["Gel/Western Blot"]=35*(contrast<15 and hom>0.8)+25*(abs(mr-mg2)<20 and abs(mg2-mb)<20)+20*(not per)+20*(ed<0.08)
    scores["Gráfico Científico"]=30*(hom>0.85)+25*(n_kp<25)+25*(entropy<4)+20*(not per)
    scores["Estrutura Molecular"]=35*(sym>0.80)+25*per+20*(abs(mr-mg2)<25)+20*(n_kp<50)
    scores["Microscopia Confocal"]=20*(len(pal)>4)+25*(entropy>5.5)+20*(n_kp>50)+20*(ed>0.10)+15*(contrast>20)
    scores["Imagem Astronômica"]=35*(color.get("bright",128)<60)+25*(n_kp>40 and hom>0.7)+20*(entropy>5)+20*(fft_r["hf"]>0.4)
    scores["Microscopia Eletrônica"]=30*(abs(mr-mg2)<15 and abs(mg2-mb)<15)+25*(ed>0.15)+20*(contrast>40)+25*(n_kp>100)
    scores["Espectroscopia"]=30*(entropy<3.5 and hom>0.9)+30*(n_kp<15)+20*(not per)+20*(fft_r["lf"]>0.5)
    best=max(scores,key=scores.get); sc=scores[best]; conf=min(96,38+sc*0.52)
    origins={"Histopatologia H&E":"Medicina/Patologia — tecido corado H&E para diagnóstico histológico","Fluorescência DAPI":"Biologia Celular — núcleos marcados com DAPI (fluoróforo azul UV)","Fluorescência GFP":"Biologia Molecular — proteína fluorescente verde (GFP) expressa","Cristalografia/Difração":"Física/Química Estrutural — padrão de difração de raios-X","Gel/Western Blot":"Bioquímica — proteínas separadas por eletroforese","Gráfico Científico":"Visualização de dados — gráfico ou diagrama científico","Estrutura Molecular":"Química Computacional — estrutura 3D de molécula ou proteína","Microscopia Confocal":"Biologia Celular — imagem multicanal de fluorescência confocal","Imagem Astronômica":"Astrofísica — objeto celeste capturado por telescópio","Microscopia Eletrônica":"Nanociência/Materiais — superfície em escala nanométrica (SEM/TEM)","Espectroscopia":"Química Analítica — perfil espectral ou cromatográfico"}
    kw_map={"Histopatologia H&E":"hematoxylin eosin histopathology tissue diagnosis","Fluorescência DAPI":"DAPI nuclear staining fluorescence microscopy","Fluorescência GFP":"GFP fluorescent protein confocal microscopy","Cristalografia/Difração":"X-ray diffraction crystallography structure","Gel/Western Blot":"western blot electrophoresis protein analysis","Gráfico Científico":"scientific data visualization analysis","Estrutura Molecular":"molecular structure protein visualization","Microscopia Confocal":"confocal microscopy fluorescence multichannel","Imagem Astronômica":"astronomy telescope deep field imaging","Microscopia Eletrônica":"scanning electron microscopy SEM TEM","Espectroscopia":"spectroscopy mass spectrometry analytical"}
    return {"category":best,"confidence":round(conf,1),"origin":origins.get(best,"Ciência Geral"),"kw":kw_map.get(best,best),"scores":dict(sorted(scores.items(),key=lambda x:-x[1])[:6])}

@st.cache_data(max_entries=10,show_spinner=False)
def run_ml_pipeline(img_hash,img_bytes):
    """Pipeline ML completo — cached por hash."""
    result={}
    try:
        img=PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
        orig_size=img.size; w,h=img.size; scale=min(192/w,192/h)
        nw,nh=int(w*scale),int(h*scale)
        img_r=img.resize((nw,nh),PILImage.LANCZOS)
        arr=np.array(img_r,dtype=np.float32)
        r_ch,g_ch,b_ch=arr[:,:,0],arr[:,:,1],arr[:,:,2]
        gray=0.2989*r_ch+0.5870*g_ch+0.1140*b_ch; gray_u8=gray.astype(np.uint8)
        mr,mg2,mb=float(r_ch.mean()),float(g_ch.mean()),float(b_ch.mean())
        hy,hx=gray.shape[0]//2,gray.shape[1]//2
        q=[gray[:hy,:hx].var(),gray[:hy,hx:].var(),gray[hy:,:hx].var(),gray[hy:,hx:].var()]
        sym=1.0-(max(q)-min(q))/(max(q)+1e-5)
        hst=np.histogram(gray,bins=64,range=(0,255))[0]; hn=hst/hst.sum(); hn2=hn[hn>0]
        entropy=float(-np.sum(hn2*np.log2(hn2)))
        color={"r":round(mr,1),"g":round(mg2,1),"b":round(mb,1),"sym":round(sym,3),"entropy":round(entropy,3),"bright":round(float(gray.mean()),1),"std":round(float(gray.std()),1),"warm":mr>mb+15,"cool":mb>mr+15}
        result["color"]=color; result["orig_size"]=orig_size; result["proc_size"]=(nw,nh)
        sobel_r=sobel_fast(gray/255.0); result["sobel"]=sobel_r
        result["fft"]=fft_fast(gray/255.0); result["glcm"]=glcm_fast(gray_u8)
        # Keypoints simples (numpy)
        gx=np.gradient(gray.astype(np.float32),axis=1); gy=np.gradient(gray.astype(np.float32),axis=0); mag_kp=np.sqrt(gx**2+gy**2)
        step=max(1,min(nw,nh)//16); pts=[]
        for i in range(0,nh-step,step):
            for j in range(0,nw-step,step):
                bl=mag_kp[i:i+step,j:j+step]
                if bl.max()>mag_kp.mean()*2.0: yi,xj=np.unravel_index(bl.argmax(),bl.shape); pts.append([i+yi,j+xj])
        result["n_kp"]=len(pts); result["kps"]=pts[:80]
        result["palette"]=kmeans_fast(arr.astype(np.uint8),k=7)
        result["histograms"]={"r":np.histogram(r_ch.ravel(),bins=32,range=(0,255))[0].tolist(),"g":np.histogram(g_ch.ravel(),bins=32,range=(0,255))[0].tolist(),"b":np.histogram(b_ch.ravel(),bins=32,range=(0,255))[0].tolist()}
        result["classification"]=classify_ml(sobel_r,result["fft"],result["glcm"],color,result["n_kp"],result["palette"])
        smag=sobel_r["magnitude"]; result["sobel_map"]=(smag/(smag.max()+1e-5)*255).astype(np.uint8).tolist()
        sx_arr=np.array(sobel_r["sx"]); sy_arr=np.array(sobel_r["sy"]); direction=np.arctan2(sy_arr,sx_arr)*180/np.pi
        result["edge_dir_mean"]=round(float(direction.mean()),1); result["edge_dir_std"]=round(float(direction.std()),1)
        result["ok"]=True
    except Exception as e: result["ok"]=False; result["error"]=str(e)
    return result

# ═══════════════════════════════════════════════
#  BUSCA ACADÊMICA (cached 5min)
# ═══════════════════════════════════════════════
@st.cache_data(show_spinner=False,ttl=300)
def search_ss(q,lim=7):
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
                out.append({"title":p.get("title","Sem título"),"authors":au or "—","year":p.get("year","?"),"source":p.get("venue","") or "Semantic Scholar","doi":doi or arx or "—","abstract":(p.get("abstract","") or "")[:300],"url":link,"citations":p.get("citationCount",0),"origin":"semantic"})
            return out
    except: pass
    return []

@st.cache_data(show_spinner=False,ttl=300)
def search_cr(q,lim=4):
    try:
        r=requests.get("https://api.crossref.org/works",
            params={"query":q,"rows":lim,"select":"title,author,issued,abstract,DOI,container-title,is-referenced-by-count","mailto":"nebula@example.com"},timeout=9)
        if r.status_code==200:
            out=[]
            for p in r.json().get("message",{}).get("items",[]):
                title=(p.get("title") or ["?"])[0]; ars=p.get("author",[]) or []
                au=", ".join(f'{a.get("given","").split()[0] if a.get("given") else ""} {a.get("family","")}'.strip() for a in ars[:3])
                if len(ars)>3: au+=" et al."
                yr=(p.get("issued",{}).get("date-parts") or [[None]])[0][0]; doi=p.get("DOI","")
                ab=re.sub(r'<[^>]+>','',p.get("abstract","") or "")[:300]
                out.append({"title":title,"authors":au or "—","year":yr or "?","source":(p.get("container-title") or ["CrossRef"])[0],"doi":doi,"abstract":ab,"url":f"https://doi.org/{doi}" if doi else "","citations":p.get("is-referenced-by-count",0),"origin":"crossref"})
            return out
    except: pass
    return []

# ═══════════════════════════════════════════════
#  DOC ANALYSIS
# ═══════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def kw_extract(text,n=25):
    if not text: return []
    words=re.findall(r'\b[a-záàâãéêíóôõúüçA-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]{4,}\b',text.lower())
    words=[w for w in words if w not in STOPWORDS]
    if not words: return []
    tf=Counter(words); tot=sum(tf.values())
    return [w for w,_ in sorted({w:c/tot for w,c in tf.items()}.items(),key=lambda x:-x[1])[:n]]

def topic_dist(kws):
    tm={"Saúde & Medicina":["saúde","medicina","clínico","health","therapy","disease"],"Biologia":["biologia","genômica","gene","dna","rna","proteína","célula","crispr"],"Neurociência":["neurociência","neural","cérebro","cognição","memória","sono","brain"],"IA & Computação":["algoritmo","machine","learning","inteligência","dados","ia","deep","quantum"],"Física":["física","quântica","partícula","energia","galáxia","astrofísica","cosmologia"],"Química":["química","molécula","síntese","reação","polímero"],"Engenharia":["engenharia","sistema","robótica","automação"],"Ciências Sociais":["sociedade","cultura","educação","política","psicologia"],"Ecologia":["ecologia","clima","ambiente","biodiversidade"],"Matemática":["matemática","estatística","probabilidade","equação"]}
    s=defaultdict(int)
    for kw in kws:
        for tp,terms in tm.items():
            if any(t in kw or kw in t for t in terms): s[tp]+=1
    return dict(sorted(s.items(),key=lambda x:-x[1])) if s else {"Pesquisa Geral":1}

@st.cache_data(show_spinner=False)
def analyze_doc(fname,fbytes,ftype_str,area=""):
    r={"file":fname,"type":ftype_str,"keywords":[],"topics":{},"relevance_score":50,"summary":"","word_count":0,"reading_time":0,"writing_quality":50,"strengths":[],"gaps":[]}
    text=""
    if fbytes:
        if ftype_str=="PDF":
            try:
                import PyPDF2; reader=PyPDF2.PdfReader(io.BytesIO(fbytes)); t=""
                for pg in reader.pages[:20]:
                    try: t+=pg.extract_text()+"\n"
                    except: pass
                text=t[:35000]
            except: pass
        else:
            try: text=fbytes.decode("utf-8",errors="ignore")[:35000]
            except: pass
    if text:
        r["keywords"]=kw_extract(text,25); words=len(text.split()); r["word_count"]=words; r["reading_time"]=max(1,round(words/200))
        r["topics"]=topic_dist(r["keywords"]); r["writing_quality"]=min(100,50+(12 if len(r["keywords"])>12 else 0)+(15 if words>800 else 0)+(10 if r["reading_time"]>3 else 0)+(13 if len(r["topics"])>1 else 0))
        if area: rel=sum(1 for w in area.lower().split() if any(w in kw for kw in r["keywords"])); r["relevance_score"]=min(100,rel*18+40)
        else: r["relevance_score"]=65
        if len(r["keywords"])>12: r["strengths"].append(f"Vocabulário rico ({len(r['keywords'])} termos)")
        if words<300: r["gaps"].append("Conteúdo curto")
        r["summary"]=f"{ftype_str} · {words} palavras · ~{r['reading_time']}min · {', '.join(r['keywords'][:5])}"
    else:
        r["summary"]=f"Arquivo {ftype_str} — sem texto extraível."
        r["keywords"]=kw_extract(fname.lower(),5); r["topics"]=topic_dist(r["keywords"])
    return r

# ═══════════════════════════════════════════════
#  CSS — AZUL ESCURO + VERDE IA
# ═══════════════════════════════════════════════
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800;900&family=DM+Sans:wght@300;400;500;600;700&display=swap');

:root{
  --bg:#020B1E;--bg2:#040D22;--bg3:#071226;--bg4:#0A1630;
  --grn:#00E676;--grn2:#00FF8A;--grnf:rgba(0,230,118,.10);--grnd:rgba(0,230,118,.14);
  --yel:#FFD60A;--red:#FF3B5C;--blu:#4CC9F0;--pur:#B17DFF;--orn:#FF8C42;
  --t0:#FFFFFF;--t1:#E4E8F4;--t2:#8A92B2;--t3:#3A4260;--t4:#1E2440;
  --gb1:rgba(255,255,255,.06);--gb2:rgba(255,255,255,.10);--gb3:rgba(255,255,255,.16);
  --ai-bg:rgba(0,230,118,.07);--ai-bd:rgba(0,230,118,.20);
  --card:rgba(255,255,255,.04);--card-bd:rgba(255,255,255,.07);
  --r8:8px;--r12:12px;--r16:16px;--r20:20px;--r28:28px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html,body,.stApp{background:var(--bg)!important;color:var(--t1)!important;font-family:'DM Sans',-apple-system,sans-serif!important;}
.stApp::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:radial-gradient(ellipse 80% 55% at -10% -5%,rgba(0,40,180,.10) 0%,transparent 55%),
  radial-gradient(ellipse 55% 45% at 110% -5%,rgba(0,230,118,.07) 0%,transparent 50%),
  radial-gradient(ellipse 40% 55% at 50% 110%,rgba(76,201,240,.05) 0%,transparent 55%);}
.stApp::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:linear-gradient(rgba(0,230,118,.016) 1px,transparent 1px),linear-gradient(90deg,rgba(0,230,118,.016) 1px,transparent 1px);
  background-size:55px 55px;}
header[data-testid="stHeader"],#MainMenu,footer,.stDeployButton,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
[data-testid="stSidebarCollapseButton"]{display:none!important}
section[data-testid="stSidebar"]{
  background:#010813!important;border-right:1px solid rgba(0,230,118,.09)!important;
  width:205px!important;min-width:205px!important;max-width:205px!important;
  padding:.8rem .6rem!important;
}
section[data-testid="stSidebar"]>div{padding:0!important;}
/* NAV RADIO */
section[data-testid="stSidebar"] .stRadio>div{flex-direction:column!important;gap:1px!important;}
section[data-testid="stSidebar"] .stRadio>div>label{
  background:transparent!important;border:1px solid transparent!important;border-radius:8px!important;
  padding:.42rem .68rem!important;font-size:.80rem!important;color:#3A4260!important;
  -webkit-text-fill-color:#3A4260!important;width:100%!important;cursor:pointer!important;margin:0!important;transition:all .10s!important;
}
section[data-testid="stSidebar"] .stRadio>div>label:hover{background:rgba(0,230,118,.08)!important;color:#00E676!important;-webkit-text-fill-color:#00E676!important;border-color:rgba(0,230,118,.18)!important;}
section[data-testid="stSidebar"] .stRadio input[type="radio"]{display:none!important;}
section[data-testid="stSidebar"] .stRadio label div:first-child{display:none!important;}
.block-container{padding-top:.2rem!important;padding-bottom:3rem!important;max-width:1400px!important;z-index:1;padding-left:.75rem!important;padding-right:.75rem!important;}
/* BUTTONS */
.stButton>button{background:rgba(255,255,255,.05)!important;border:1px solid rgba(255,255,255,.09)!important;border-radius:9px!important;color:#7A82A2!important;-webkit-text-fill-color:#7A82A2!important;font-family:'DM Sans',sans-serif!important;font-weight:500!important;font-size:.79rem!important;padding:.38rem .72rem!important;box-shadow:none!important;line-height:1.4!important;transition:all .10s!important;}
.stButton>button:hover{background:rgba(0,230,118,.10)!important;border-color:rgba(0,230,118,.25)!important;color:#00E676!important;-webkit-text-fill-color:#00E676!important;}
.stButton>button:active{transform:scale(.97)!important;}
.stButton>button p,.stButton>button span{color:inherit!important;-webkit-text-fill-color:inherit!important;}
/* INPUTS */
.stTextInput input,.stTextArea textarea{background:rgba(255,255,255,.03)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;color:var(--t1)!important;font-family:'DM Sans',sans-serif!important;font-size:.82rem!important;}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:rgba(0,230,118,.35)!important;box-shadow:0 0 0 2px rgba(0,230,118,.06)!important;}
.stTextInput label,.stTextArea label,.stSelectbox label,.stFileUploader label,.stNumberInput label{color:var(--t3)!important;font-size:.56rem!important;letter-spacing:.10em!important;text-transform:uppercase!important;font-weight:700!important;}
/* CARDS */
.glass{background:var(--card);border:1px solid var(--card-bd);border-radius:var(--r20);box-shadow:0 4px 30px rgba(0,0,0,.35);}
.post-card{background:var(--card);border:1px solid var(--card-bd);border-radius:var(--r16);margin-bottom:.55rem;transition:border-color .12s,transform .12s;}
.post-card:hover{border-color:rgba(0,230,118,.18);transform:translateY(-1px);}
.sc{background:var(--card);border:1px solid var(--card-bd);border-radius:var(--r16);padding:.8rem .85rem;margin-bottom:.5rem;}
.scard{background:rgba(255,255,255,.03);border:1px solid var(--card-bd);border-radius:var(--r12);padding:.65rem .85rem;margin-bottom:.35rem;transition:border-color .11s;}
.scard:hover{border-color:rgba(0,230,118,.16);}
.mbox{background:rgba(255,255,255,.03);border:1px solid var(--gb1);border-radius:var(--r12);padding:.9rem;text-align:center;}
.abox{background:rgba(255,255,255,.04);border:1px solid var(--gb1);border-radius:var(--r12);padding:.8rem;margin-bottom:.45rem;}
.chart-wrap{background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.05);border-radius:var(--r12);padding:.45rem;margin-bottom:.45rem;}
.compose-box{background:rgba(0,230,118,.04);border:1px solid rgba(0,230,118,.12);border-radius:var(--r16);padding:.9rem 1.1rem;margin-bottom:.65rem;}
/* AI CARDS — VERDE */
.ai-card{background:linear-gradient(135deg,rgba(0,230,118,.07),rgba(0,230,118,.03));border:1px solid rgba(0,230,118,.20);border-radius:var(--r16);padding:.85rem;margin-bottom:.55rem;}
.conn-ai{background:linear-gradient(135deg,rgba(0,230,118,.06),rgba(76,201,240,.04));border:1px solid rgba(0,230,118,.16);border-radius:var(--r16);padding:.8rem;margin-bottom:.45rem;}
.api-banner{background:rgba(0,230,118,.05);border:1px solid rgba(0,230,118,.16);border-radius:var(--r12);padding:.7rem .85rem;margin-bottom:.65rem;}
.sobel-card{background:rgba(0,230,118,.04);border:1px solid rgba(0,230,118,.14);border-radius:var(--r16);padding:.8rem;margin-bottom:.5rem;}
.ml-feat{background:rgba(255,255,255,.03);border:1px solid var(--gb1);border-radius:var(--r12);padding:.55rem .78rem;margin-bottom:.32rem;}
.pbox-grn{background:rgba(0,230,118,.05);border:1px solid rgba(0,230,118,.14);border-radius:var(--r12);padding:.65rem;margin-bottom:.4rem;}
.pbox-yel{background:rgba(255,214,10,.05);border:1px solid rgba(255,214,10,.14);border-radius:var(--r12);padding:.65rem;margin-bottom:.4rem;}
.pbox-blu{background:rgba(76,201,240,.05);border:1px solid rgba(76,201,240,.14);border-radius:var(--r12);padding:.65rem;margin-bottom:.4rem;}
.pbox-red{background:rgba(255,59,92,.05);border:1px solid rgba(255,59,92,.14);border-radius:var(--r12);padding:.65rem;margin-bottom:.4rem;}
/* METRIC VALUES */
.mval-grn{font-family:'Syne',sans-serif;font-size:1.55rem;font-weight:900;background:linear-gradient(135deg,#00E676,#4CC9F0);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-yel{font-family:'Syne',sans-serif;font-size:1.55rem;font-weight:900;background:linear-gradient(135deg,#FFD60A,#FF8C42);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-blu{font-family:'Syne',sans-serif;font-size:1.55rem;font-weight:900;background:linear-gradient(135deg,#4CC9F0,#B17DFF);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-red{font-family:'Syne',sans-serif;font-size:1.55rem;font-weight:900;background:linear-gradient(135deg,#FF3B5C,#FF8C42);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mlbl{font-size:.53rem;color:var(--t3);margin-top:3px;letter-spacing:.10em;text-transform:uppercase;font-weight:700;}
/* TAGS & BADGES */
.tag{display:inline-block;background:rgba(0,230,118,.07);border:1px solid rgba(0,230,118,.13);border-radius:50px;padding:1px 8px;font-size:.60rem;color:#00E676;margin:1px;font-weight:500;}
.tag-grey{display:inline-block;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:50px;padding:1px 8px;font-size:.60rem;color:var(--t2);margin:1px;font-weight:500;}
.badge-yel{display:inline-block;background:rgba(255,214,10,.12);border:1px solid rgba(255,214,10,.24);border-radius:50px;padding:1px 8px;font-size:.58rem;font-weight:700;color:#FFD60A;}
.badge-grn{display:inline-block;background:rgba(0,230,118,.12);border:1px solid rgba(0,230,118,.24);border-radius:50px;padding:1px 8px;font-size:.58rem;font-weight:700;color:#00E676;}
.badge-red{display:inline-block;background:rgba(255,59,92,.12);border:1px solid rgba(255,59,92,.24);border-radius:50px;padding:1px 8px;font-size:.58rem;font-weight:700;color:#FF3B5C;}
.badge-blu{display:inline-block;background:rgba(76,201,240,.12);border:1px solid rgba(76,201,240,.24);border-radius:50px;padding:1px 8px;font-size:.58rem;font-weight:700;color:#4CC9F0;}
.badge-pur{display:inline-block;background:rgba(177,125,255,.12);border:1px solid rgba(177,125,255,.24);border-radius:50px;padding:1px 8px;font-size:.58rem;font-weight:700;color:#B17DFF;}
/* ANIMATIONS */
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.35;transform:scale(.65)}}
@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
@keyframes glowPulse{0%,100%{box-shadow:0 0 8px rgba(0,230,118,.2)}50%{box-shadow:0 0 20px rgba(0,230,118,.45)}}
.dot-on{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--grn);animation:pulse 2.3s infinite;margin-right:4px;vertical-align:middle;}
.dot-off{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--t4);margin-right:4px;vertical-align:middle;}
.pw{animation:fadeUp .14s ease both;}
.ai-glow{animation:glowPulse 2s infinite;}
/* CHAT */
.bme{background:linear-gradient(135deg,rgba(0,230,118,.11),rgba(76,201,240,.07));border:1px solid rgba(0,230,118,.14);border-radius:16px 16px 3px 16px;padding:.48rem .78rem;max-width:72%;margin-left:auto;margin-bottom:4px;font-size:.78rem;line-height:1.6;}
.bthem{background:rgba(255,255,255,.05);border:1px solid var(--gb1);border-radius:16px 16px 16px 3px;padding:.48rem .78rem;max-width:72%;margin-bottom:4px;font-size:.78rem;line-height:1.6;}
.cmt{background:rgba(255,255,255,.03);border:1px solid var(--gb1);border-radius:var(--r12);padding:.42rem .78rem;margin-bottom:.2rem;}
/* TABS */
.stTabs [data-baseweb="tab-list"]{background:rgba(255,255,255,.03)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;padding:3px!important;gap:2px!important;}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--t3)!important;border-radius:8px!important;font-size:.72rem!important;font-family:'DM Sans',sans-serif!important;}
.stTabs [aria-selected="true"]{background:rgba(0,230,118,.10)!important;color:#00E676!important;border:1px solid rgba(0,230,118,.20)!important;font-weight:700!important;}
.stTabs [data-baseweb="tab-panel"]{background:transparent!important;padding-top:.65rem!important;}
hr{border:none;border-top:1px solid rgba(255,255,255,.05)!important;margin:.65rem 0;}
.stAlert{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;}
.stSelectbox [data-baseweb="select"]{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;}
.stFileUploader section{background:rgba(255,255,255,.02)!important;border:1.5px dashed rgba(0,230,118,.18)!important;border-radius:var(--r12)!important;}
.stExpander{background:rgba(255,255,255,.03)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;}
::-webkit-scrollbar{width:3px;height:3px;}::-webkit-scrollbar-thumb{background:rgba(0,230,118,.22);border-radius:3px;}
.js-plotly-plot .plotly .modebar{display:none!important;}
.dtxt{display:flex;align-items:center;gap:.55rem;margin:.55rem 0;font-size:.54rem;color:var(--t3);letter-spacing:.10em;text-transform:uppercase;font-weight:700;}
.dtxt::before,.dtxt::after{content:'';flex:1;height:1px;background:var(--gb1);}
h1{font-family:'Syne',sans-serif!important;font-size:1.4rem!important;font-weight:800!important;letter-spacing:-.03em;color:var(--t0)!important;}
h2{font-family:'Syne',sans-serif!important;font-size:.93rem!important;font-weight:700!important;color:var(--t0)!important;}
label{color:var(--t2)!important;}
.stCheckbox label,.stRadio label{color:var(--t1)!important;}
.stRadio>div{display:flex!important;gap:3px!important;flex-wrap:wrap!important;}
.stRadio>div>label{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:50px!important;padding:.24rem .68rem!important;font-size:.70rem!important;cursor:pointer!important;color:var(--t2)!important;}
input[type="number"]{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;color:var(--t1)!important;}
.prof-hero{background:rgba(255,255,255,.03);border:1px solid rgba(0,230,118,.09);border-radius:var(--r28);padding:1.3rem;display:flex;gap:1.1rem;align-items:flex-start;margin-bottom:.85rem;}
</style>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════
#  HTML HELPERS
# ═══════════════════════════════════════════════
def avh(initials,sz=38,grad=None):
    fs=max(sz//3,7); bg=grad or "linear-gradient(135deg,#00E676,#4CC9F0)"
    return f'<div style="width:{sz}px;height:{sz}px;border-radius:50%;background:{bg};display:flex;align-items:center;justify-content:center;font-family:Syne,sans-serif;font-weight:800;font-size:{fs}px;color:white;flex-shrink:0">{initials}</div>'

def tags_html(tags,grey=False):
    cls="tag-grey" if grey else "tag"
    return ' '.join(f'<span class="{cls}">{t}</span>' for t in(tags or []))

def badge(s):
    m={"Publicado":"badge-grn","Concluído":"badge-blu"}
    return f'<span class="{m.get(s,"badge-yel")}">{s}</span>'

def pc_dark(h=None):
    d=dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",font=dict(color="#3A4260",family="DM Sans",size=10),margin=dict(l=8,r=8,t=32,b=8),xaxis=dict(showgrid=False,color="#3A4260",tickfont=dict(size=9)),yaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,.03)",color="#3A4260",tickfont=dict(size=9)))
    if h: d["height"]=h
    return d

# ═══════════════════════════════════════════════
#  NAV
# ═══════════════════════════════════════════════
NAV_LABELS=["🏠  Feed","🔍  Busca","🕸  Conexões IA","📁  Pastas","📊  Análises","🔬  Visão IA","💬  Chat","⚙️  Config"]
NAV_KEYS=["feed","search","knowledge","folders","analytics","img_search","chat","settings"]

def render_nav():
    email=st.session_state.current_user; u=guser(); name=u.get("name","?"); g=ugrad(email); cur=st.session_state.page
    with st.sidebar:
        st.markdown("""<div style="display:flex;align-items:center;gap:8px;margin-bottom:1.1rem;padding:.05rem .1rem">
  <div style="width:28px;height:28px;border-radius:7px;background:linear-gradient(135deg,#00E676,#4CC9F0);display:flex;align-items:center;justify-content:center;font-size:.75rem;flex-shrink:0;box-shadow:0 0 14px rgba(0,230,118,.22)">🔬</div>
  <div style="font-family:Syne,sans-serif;font-weight:900;font-size:1.05rem;letter-spacing:-.04em;background:linear-gradient(135deg,#00E676,#4CC9F0);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">Nebula</div>
  <div style="flex:1"></div><div style="font-size:.48rem;color:#1E2440;font-weight:700;letter-spacing:.08em">v6</div>
</div>""", unsafe_allow_html=True)
        cur_idx=NAV_KEYS.index(cur) if cur in NAV_KEYS else 0
        ac="#00E676"
        st.markdown(f"""<style>
section[data-testid="stSidebar"] .stRadio>div>label:nth-child({cur_idx+1}){{
  background:rgba(0,230,118,.08)!important;border-color:rgba(0,230,118,.22)!important;
  color:{ac}!important;-webkit-text-fill-color:{ac}!important;font-weight:700!important;
}}</style>""", unsafe_allow_html=True)
        choice=st.radio("",NAV_LABELS,index=cur_idx,key="nav_radio",label_visibility="collapsed")
        new_key=NAV_KEYS[NAV_LABELS.index(choice)]
        if new_key!=cur: st.session_state.page=new_key; st.session_state.profile_view=None; st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
        nc=len(st.session_state.notifications)
        nb_lbl=f"🔔 {nc} notif." if nc else "🔔 Notificações"
        if st.button(nb_lbl,key="sb_notif",use_container_width=True):
            st.session_state.show_notif=not st.session_state.get("show_notif",False); st.rerun()
        if st.session_state.get("show_notif",False):
            for n in st.session_state.notifications[:4]:
                st.markdown(f'<div style="background:rgba(0,230,118,.05);border:1px solid rgba(0,230,118,.10);border-radius:7px;padding:.35rem .55rem;margin-bottom:.2rem;font-size:.62rem;color:var(--t2)">{n}</div>', unsafe_allow_html=True)
            if st.button("✓ Limpar",key="sb_clr",use_container_width=True):
                st.session_state.notifications=[]; save_db(); st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<div style="font-size:.50rem;font-weight:700;color:#1E2440;letter-spacing:.12em;text-transform:uppercase;margin-bottom:.25rem">Anthropic API Key</div>', unsafe_allow_html=True)
        ak=st.text_input("",placeholder="sk-ant-api03-…",type="password",key="sb_apikey",label_visibility="collapsed",value=st.session_state.anthropic_key)
        if ak!=st.session_state.anthropic_key: st.session_state.anthropic_key=ak
        if ak and ak.startswith("sk-"):
            st.markdown('<div style="font-size:.51rem;color:#00E676;padding:.06rem .05rem;margin-bottom:.25rem">● Claude IA Ativo</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:.51rem;color:#1E2440;padding:.06rem .05rem;margin-bottom:.25rem">● console.anthropic.com → API Keys</div>', unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)
        ini_=ini(name)
        st.markdown(f'<div style="display:flex;align-items:center;gap:7px;padding:.05rem 0">{avh(ini_,26,g)}<div style="overflow:hidden"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.73rem;color:#FFF;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:112px">{name}</div><div style="font-size:.52rem;color:#3A4260">{u.get("area","")[:17]}</div></div></div>', unsafe_allow_html=True)
        c1s,c2s=st.columns(2)
        with c1s:
            if st.button("👤 Perfil",key="sb_myp",use_container_width=True):
                st.session_state.profile_view=email; st.session_state.page="feed"; st.rerun()
        with c2s:
            if st.button("🚪 Sair",key="sb_out",use_container_width=True):
                st.session_state.logged_in=False; st.session_state.current_user=None; st.session_state.page="feed"; st.rerun()

# ═══════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════
def page_login():
    _,col,_=st.columns([1,1.05,1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""<div style="text-align:center;margin-bottom:2.4rem">
  <div style="display:flex;align-items:center;justify-content:center;gap:11px;margin-bottom:.65rem">
    <div style="width:44px;height:44px;border-radius:12px;background:linear-gradient(135deg,#00E676,#4CC9F0);display:flex;align-items:center;justify-content:center;font-size:1.25rem;box-shadow:0 0 22px rgba(0,230,118,.28)">🔬</div>
    <div style="font-family:Syne,sans-serif;font-size:2.4rem;font-weight:900;letter-spacing:-.06em;background:linear-gradient(135deg,#00E676,#4CC9F0);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">Nebula</div>
  </div>
  <div style="color:#1E2440;font-size:.56rem;letter-spacing:.26em;text-transform:uppercase;font-weight:700">Rede do Conhecimento Científico</div>
</div>""", unsafe_allow_html=True)
        ti,tu=st.tabs(["  🔑 Entrar  ","  ✨ Criar conta  "])
        with ti:
            with st.form("lf"):
                em=st.text_input("E-mail",placeholder="seu@email.com",key="li_e")
                pw=st.text_input("Senha",placeholder="••••••••",type="password",key="li_p")
                s=st.form_submit_button("→  Entrar",use_container_width=True)
                if s:
                    u=st.session_state.users.get(em)
                    if not u: st.error("E-mail não encontrado.")
                    elif u["password"]!=hp(pw): st.error("Senha incorreta.")
                    else:
                        st.session_state.logged_in=True; st.session_state.current_user=em
                        record(area_tags(u.get("area","")),1.0); st.session_state.page="feed"; st.rerun()
            st.markdown('<div style="text-align:center;color:#3A4260;font-size:.64rem;margin-top:.55rem">Demo: demo@nebula.ai / demo123</div>', unsafe_allow_html=True)
        with tu:
            with st.form("sf"):
                nn=st.text_input("Nome completo",key="su_n"); ne=st.text_input("E-mail institucional",key="su_e")
                na=st.text_input("Área de pesquisa",key="su_a"); np_=st.text_input("Senha",type="password",key="su_p"); np2=st.text_input("Confirmar",type="password",key="su_p2")
                if st.form_submit_button("✓  Criar conta",use_container_width=True):
                    if not all([nn,ne,na,np_,np2]): st.error("Preencha todos.")
                    elif np_!=np2: st.error("Senhas não coincidem.")
                    elif ne in st.session_state.users: st.error("E-mail já cadastrado.")
                    elif len(np_)<6: st.error("Mínimo 6 chars.")
                    else:
                        st.session_state.users[ne]={"name":nn,"password":hp(np_),"bio":"","area":na,"followers":0,"following":0,"verified":True,"2fa_enabled":False,"joined":datetime.now().strftime("%Y-%m-%d"),"publications":0,"citations":0}
                        save_db(); st.session_state.logged_in=True; st.session_state.current_user=ne
                        record(area_tags(na),2.0); st.session_state.page="feed"; st.rerun()

# ═══════════════════════════════════════════════
#  PROFILE
# ═══════════════════════════════════════════════
def page_profile(target_email):
    tu=st.session_state.users.get(target_email,{}); email=st.session_state.current_user
    if not tu: st.error("Perfil não encontrado."); return
    tname=tu.get("name","?"); ti=ini(tname); is_me=(email==target_email)
    is_fol=target_email in st.session_state.followed; g=ugrad(target_email)
    user_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==target_email]
    liked_posts=[p for p in st.session_state.feed_posts if target_email in p.get("liked_by",[])]
    total_likes=sum(p["likes"] for p in user_posts); total_views=sum(p.get("views",0) for p in user_posts)
    vb=' <span class="badge-grn" style="font-size:.55rem;vertical-align:middle">✓ Verificado</span>' if tu.get("verified") else ""
    pubs=tu.get("publications",len(user_posts)); cit=tu.get("citations",total_likes*3)
    st.markdown(f"""<div class="prof-hero">
  <div style="width:70px;height:70px;border-radius:50%;background:{g};display:flex;align-items:center;justify-content:center;font-family:Syne,sans-serif;font-weight:800;font-size:1.4rem;color:white;flex-shrink:0">{ti}</div>
  <div style="flex:1;min-width:0">
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:.18rem;flex-wrap:wrap"><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1.2rem;color:var(--t0)">{tname}</span>{vb}</div>
    <div style="color:#00E676;font-size:.76rem;font-weight:600;margin-bottom:.28rem">{tu.get("area","")}</div>
    <div style="color:var(--t2);font-size:.73rem;line-height:1.65;margin-bottom:.6rem">{tu.get("bio","Sem biografia.")}</div>
    <div style="display:flex;gap:1.3rem;flex-wrap:wrap">
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:.94rem;color:var(--t0)">{tu.get("followers",0)}</span><span style="color:var(--t3);font-size:.62rem"> seg.</span></div>
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:.94rem;color:var(--t0)">{pubs}</span><span style="color:var(--t3);font-size:.62rem"> publ.</span></div>
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:.94rem;color:#00E676">{fmt_num(cit)}</span><span style="color:var(--t3);font-size:.62rem"> citações</span></div>
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:.94rem;color:#FFD60A">{fmt_num(total_likes)}</span><span style="color:var(--t3);font-size:.62rem"> curtidas</span></div>
    </div>
    <div style="font-size:.55rem;color:var(--t3);margin-top:.38rem">Membro desde {tu.get("joined","—")}</div>
  </div>
</div>""", unsafe_allow_html=True)
    if not is_me:
        c1,c2,c3,_=st.columns([1,1,1,2])
        with c1:
            if st.button("✓ Seguindo" if is_fol else "+ Seguir",key="su_n",use_container_width=True):
                if is_fol: st.session_state.followed.remove(target_email); tu["followers"]=max(0,tu.get("followers",0)-1)
                else: st.session_state.followed.append(target_email); tu["followers"]=tu.get("followers",0)+1
                save_db(); st.rerun()
        with c2:
            if st.button("💬 Mensagem",key="pf_chat",use_container_width=True):
                st.session_state.chat_messages.setdefault(target_email,[]); st.session_state.active_chat=target_email; st.session_state.page="chat"; st.rerun()
        with c3:
            if st.button("← Voltar",key="pf_back",use_container_width=True): st.session_state.profile_view=None; st.rerun()
        tp,tl=st.tabs([f"  📝 Pesquisas ({len(user_posts)})  ",f"  ❤️ Curtidas ({len(liked_posts)})  "])
        with tp:
            for p in sorted(user_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="profile",show_author=False)
            if not user_posts: st.markdown('<div class="glass" style="padding:2rem;text-align:center;color:var(--t3)">Nenhuma pesquisa publicada.</div>', unsafe_allow_html=True)
        with tl:
            for p in sorted(liked_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="prolk",compact=True)
    else:
        saved_arts=st.session_state.saved_articles
        tm,tl,ts2,ts=st.tabs(["  ✏️ Meus Dados  ",f"  📝 Publicações ({len(user_posts)})  ",f"  ❤️ Curtidas ({len(liked_posts)})  ",f"  🔖 Salvos ({len(saved_arts)})  "])
        with tm:
            new_n=st.text_input("Nome",value=tu.get("name",""),key="cfg_n"); new_a=st.text_input("Área",value=tu.get("area",""),key="cfg_a"); new_b=st.text_area("Bio",value=tu.get("bio",""),key="cfg_b",height=80)
            cs,co=st.columns(2)
            with cs:
                if st.button("💾 Salvar",key="btn_sp",use_container_width=True):
                    st.session_state.users[email].update({"name":new_n,"area":new_a,"bio":new_b}); save_db(); st.success("✓ Salvo!"); st.rerun()
            with co:
                if st.button("🚪 Sair",key="btn_out",use_container_width=True):
                    st.session_state.logged_in=False; st.session_state.current_user=None; st.session_state.page="feed"; st.rerun()
        with tl:
            for p in sorted(user_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="myp",show_author=False)
            if not user_posts: st.markdown('<div class="glass" style="padding:2.5rem;text-align:center;color:var(--t3)">Nenhuma pesquisa ainda.</div>', unsafe_allow_html=True)
        with ts2:
            for p in sorted(liked_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="mylk",compact=True)
        with ts:
            if saved_arts:
                for idx,a in enumerate(saved_arts):
                    render_article(a,idx=idx+3000,ctx="saved")
                    if st.button("🗑 Remover",key=f"rm_sa_{idx}",use_container_width=True):
                        st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]; save_db(); st.rerun()
            else: st.markdown('<div class="glass" style="padding:2.5rem;text-align:center;color:var(--t3)">Nenhum artigo salvo.</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════
#  POST CARD
# ═══════════════════════════════════════════════
def render_post(post,ctx="feed",show_author=True,compact=False):
    email=st.session_state.current_user; pid=post["id"]
    liked=email in post.get("liked_by",[]); saved=email in post.get("saved_by",[])
    aemail=post.get("author_email",""); ain=post.get("avatar","??"); aname=post.get("author","?")
    g=ugrad(aemail); dt=time_ago(post.get("date","")); views=post.get("views",200)
    ab=post.get("abstract","")
    if compact and len(ab)>190: ab=ab[:190]+"…"
    if show_author:
        hdr=(f'<div style="padding:.65rem .95rem .4rem;display:flex;align-items:center;gap:8px;border-bottom:1px solid rgba(255,255,255,.04)">'
             f'{avh(ain,33,g)}<div style="flex:1;min-width:0"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.80rem;color:var(--t0)">{aname}</div>'
             f'<div style="color:var(--t3);font-size:.58rem">{post.get("area","")} · {dt}</div></div>{badge(post["status"])}</div>')
    else:
        hdr=f'<div style="padding:.25rem .95rem .1rem;display:flex;justify-content:space-between;align-items:center"><span style="color:var(--t3);font-size:.58rem">{dt}</span>{badge(post["status"])}</div>'
    st.markdown(f'<div class="post-card">{hdr}<div style="padding:.5rem .95rem"><div style="font-family:Syne,sans-serif;font-size:.90rem;font-weight:700;margin-bottom:.25rem;color:var(--t0)">{post["title"]}</div><div style="color:var(--t2);font-size:.74rem;line-height:1.62;margin-bottom:.4rem">{ab}</div><div>{tags_html(post.get("tags",[]))}</div></div></div>', unsafe_allow_html=True)
    heart="❤️" if liked else "🤍"; book="🔖" if saved else "📌"; nc=len(post.get("comments",[]))
    ca,cb,cc,cd,ce,cf=st.columns([1.1,1,.65,.55,1,1.2])
    with ca:
        if st.button(f"{heart} {fmt_num(post['likes'])}",key=f"lk_{ctx}_{pid}",use_container_width=True):
            if liked: post["liked_by"].remove(email); post["likes"]=max(0,post["likes"]-1)
            else: post["liked_by"].append(email); post["likes"]+=1; record(post.get("tags",[]),1.5)
            save_db(); st.rerun()
    with cb:
        if st.button(f"💬 {nc}" if nc else "💬 Comentar",key=f"cm_{ctx}_{pid}",use_container_width=True):
            k=f"cmt_{ctx}_{pid}"; st.session_state[k]=not st.session_state.get(k,False); st.rerun()
    with cc:
        if st.button(book,key=f"sv_{ctx}_{pid}",use_container_width=True):
            if saved: post["saved_by"].remove(email)
            else: post["saved_by"].append(email)
            save_db(); st.rerun()
    with cd:
        if st.button("↗",key=f"sh_{ctx}_{pid}",use_container_width=True): st.toast(f"Link: nebula.ai/p/{pid}")
    with ce: st.markdown(f'<div style="text-align:center;color:var(--t3);font-size:.62rem;padding:.42rem 0">👁 {fmt_num(views)}</div>', unsafe_allow_html=True)
    with cf:
        if show_author and aemail:
            if st.button(f"👤 {aname.split()[0]}",key=f"vp_{ctx}_{pid}",use_container_width=True):
                st.session_state.profile_view=aemail; st.rerun()
    if st.session_state.get(f"cmt_{ctx}_{pid}",False):
        for c in post.get("comments",[]):
            ci=ini(c["user"]); ce2=next((e for e,u2 in st.session_state.users.items() if u2.get("name")==c["user"]),""); cg=ugrad(ce2)
            st.markdown(f'<div class="cmt"><div style="display:flex;align-items:center;gap:6px;margin-bottom:.14rem">{avh(ci,22,cg)}<span style="font-size:.68rem;font-weight:700;color:#00E676">{c["user"]}</span></div><div style="font-size:.73rem;color:var(--t2);padding-left:28px">{c["text"]}</div></div>', unsafe_allow_html=True)
        nc_txt=st.text_input("",placeholder="Escreva um comentário…",key=f"ci_{ctx}_{pid}",label_visibility="collapsed")
        if st.button("→ Comentar",key=f"cs_{ctx}_{pid}"):
            if nc_txt: uu=guser(); post["comments"].append({"user":uu.get("name","Você"),"text":nc_txt}); record(post.get("tags",[]),.8); save_db(); st.rerun()

# ═══════════════════════════════════════════════
#  FEED
# ═══════════════════════════════════════════════
def page_feed():
    email=st.session_state.current_user; u=guser(); uname=u.get("name","?"); uin=ini(uname); g=ugrad(email)
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    co=st.session_state.get("compose_open",False)
    cm,cs=st.columns([2,.88],gap="medium")
    with cm:
        if co:
            st.markdown(f'<div class="compose-box"><div style="display:flex;align-items:center;gap:8px;margin-bottom:.75rem">{avh(uin,34,g)}<div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.82rem;color:var(--t0)">{uname}</div><div style="font-size:.60rem;color:var(--t3)">{u.get("area","Pesquisador")}</div></div></div>', unsafe_allow_html=True)
            nt=st.text_input("Título da pesquisa *",key="np_t",placeholder="Ex: CRISPR-Cas9 em células-tronco…")
            nab=st.text_area("Resumo *",key="np_ab",height=90,placeholder="Descreva sua pesquisa, metodologia e resultados…")
            c1c,c2c=st.columns(2)
            with c1c: ntg=st.text_input("Tags (vírgula)",key="np_tg",placeholder="neurociência, IA")
            with c2c: nst=st.selectbox("Status",["Em andamento","Publicado","Concluído"],key="np_st")
            cp,cc2,cai=st.columns([2,1,1])
            with cp:
                if st.button("🚀 Publicar",key="btn_pub",use_container_width=True):
                    if not nt or not nab: st.warning("Título e resumo obrigatórios.")
                    else:
                        tags=[t.strip() for t in ntg.split(",") if t.strip()] if ntg else []
                        np3={"id":len(st.session_state.feed_posts)+200+hash(nt)%99,"author":uname,"author_email":email,"avatar":uin,"area":u.get("area",""),"title":nt,"abstract":nab,"tags":tags,"likes":0,"comments":[],"status":nst,"date":datetime.now().strftime("%Y-%m-%d"),"liked_by":[],"saved_by":[],"connections":tags[:3],"views":1,"shares":0}
                        st.session_state.feed_posts.insert(0,np3); record(tags,2.0); save_db(); st.session_state.compose_open=False; st.rerun()
            with cc2:
                if st.button("✕",key="btn_cc",use_container_width=True): st.session_state.compose_open=False; st.rerun()
            with cai:
                if st.button("🤖 Draft IA",key="btn_ai_draft",use_container_width=True):
                    if nt and st.session_state.get("anthropic_key","").startswith("sk-"):
                        with st.spinner("Gerando…"):
                            text,err=claude_ai_draft(nt,u.get("area","ciência"))
                            if text: st.session_state["np_ab"]=text; st.rerun()
                            else: st.error(err)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            ac,bc=st.columns([.06,1],gap="small")
            with ac: st.markdown(f'<div style="padding-top:4px">{avh(uin,32,g)}</div>', unsafe_allow_html=True)
            with bc:
                if st.button(f"Compartilhe sua pesquisa, {uname.split()[0]}…",key="oc",use_container_width=True):
                    st.session_state.compose_open=True; st.rerun()
        ff=st.radio("",["🌐 Todos","👥 Seguidos","🔖 Salvos","🔥 Populares","📅 Recentes"],horizontal=True,key="ff",label_visibility="collapsed")
        recs=get_recs(email,2)
        if recs and "Seguidos" not in ff and "Salvos" not in ff and "Populares" not in ff:
            st.markdown('<div class="dtxt"><span class="badge-grn">✨ Recomendado para você</span></div>', unsafe_allow_html=True)
            for p in recs: render_post(p,ctx="rec",compact=True)
            st.markdown('<div class="dtxt">Mais pesquisas</div>', unsafe_allow_html=True)
        posts=list(st.session_state.feed_posts)
        if "Seguidos" in ff: posts=[p for p in posts if p.get("author_email") in st.session_state.followed]
        elif "Salvos" in ff: posts=[p for p in posts if email in p.get("saved_by",[])]
        elif "Populares" in ff: posts=sorted(posts,key=lambda p:p["likes"],reverse=True)
        elif "Recentes" in ff: posts=sorted(posts,key=lambda p:p.get("date",""),reverse=True)
        else: posts=sorted(posts,key=lambda p:p.get("date",""),reverse=True)
        if not posts: st.markdown('<div class="glass" style="padding:3rem;text-align:center"><div style="font-size:2rem;opacity:.12;margin-bottom:.6rem">🔬</div><div style="color:var(--t3)">Nenhuma pesquisa encontrada.</div></div>', unsafe_allow_html=True)
        else:
            for p in posts: render_post(p,ctx="feed")
    with cs:
        sq=st.text_input("",placeholder="🔍 Buscar pesquisadores…",key="ppl_s",label_visibility="collapsed")
        st.markdown('<div class="sc">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.76rem;margin-bottom:.65rem;display:flex;justify-content:space-between;color:var(--t0)"><span>Sugestões</span><span style="font-size:.58rem;color:var(--t3)">Pesquisadores</span></div>', unsafe_allow_html=True)
        sn=0
        for ue,ud in list(users.items()):
            if ue==email or sn>=6: continue
            rn=ud.get("name","?")
            if sq and sq.lower() not in rn.lower() and sq.lower() not in ud.get("area","").lower(): continue
            sn+=1; is_fol=ue in st.session_state.followed; uin_r=ini(rn); rg=ugrad(ue); online=is_online(ue)
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            st.markdown(f'<div style="display:flex;align-items:center;gap:7px;padding:.28rem 0;border-bottom:1px solid rgba(255,255,255,.04)">{avh(uin_r,26,rg)}<div style="flex:1;min-width:0"><div style="font-size:.71rem;font-weight:600;color:var(--t1)">{dot}{rn}</div><div style="font-size:.56rem;color:var(--t3)">{ud.get("area","")[:22]}</div></div></div>', unsafe_allow_html=True)
            cf2,cv2=st.columns(2)
            with cf2:
                if st.button("✓" if is_fol else "+ Seguir",key=f"sf_{ue}",use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"]=max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                    save_db(); st.rerun()
            with cv2:
                if st.button("👤",key=f"svr_{ue}",use_container_width=True): st.session_state.profile_view=ue; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="sc">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.74rem;margin-bottom:.55rem;color:var(--t0)">🔥 Em Alta</div>', unsafe_allow_html=True)
        for i,(t,c) in enumerate([("Quantum ML","34"),("CRISPR 2026","28"),("Neuroplasticidade","22"),("LLMs Científicos","19"),("Matéria Escura","15"),("Proteômica","12")]):
            st.markdown(f'<div style="padding:.25rem 0;border-bottom:1px solid rgba(255,255,255,.04)"><div style="font-size:.52rem;color:var(--t3)">#{i+1}</div><div style="font-size:.71rem;font-weight:600;color:{VIB[i%len(VIB)]}">{t}</div><div style="font-size:.55rem;color:var(--t3)">{c} pesquisas</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        all_likes=sum(p["likes"] for p in st.session_state.feed_posts); all_views=sum(p.get("views",0) for p in st.session_state.feed_posts)
        st.markdown(f'<div class="sc"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.74rem;margin-bottom:.55rem;color:var(--t0)">📊 Plataforma</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:.4rem;font-size:.65rem"><div style="text-align:center"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.95rem;color:#00E676">{len(st.session_state.feed_posts)}</div><div style="color:var(--t3)">Pesquisas</div></div><div style="text-align:center"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.95rem;color:#FFD60A">{len(st.session_state.users)}</div><div style="color:var(--t3)">Pesquisadores</div></div><div style="text-align:center"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.95rem;color:#4CC9F0">{fmt_num(all_likes)}</div><div style="color:var(--t3)">Curtidas</div></div><div style="text-align:center"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.95rem;color:#B17DFF">{fmt_num(all_views)}</div><div style="color:var(--t3)">Views</div></div></div></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════
#  SEARCH
# ═══════════════════════════════════════════════
def render_article(a,idx=0,ctx="web"):
    sc=VIB[0] if a.get("origin")=="semantic" else VIB[2]; sn="Semantic Scholar" if a.get("origin")=="semantic" else "CrossRef"
    cite=f" · {fmt_num(a['citations'])} cit." if a.get("citations") else ""
    uid=re.sub(r'[^a-zA-Z0-9]','',f"{ctx}_{idx}_{str(a.get('doi',''))[:10]}")[:32]
    is_saved=any(s.get('doi')==a.get('doi') for s in st.session_state.saved_articles)
    ab=(a.get("abstract","") or "")[:280]+("…" if len(a.get("abstract",""))>280 else "")
    st.markdown(f'<div class="scard"><div style="display:flex;align-items:flex-start;gap:6px;margin-bottom:.22rem"><div style="flex:1;font-family:Syne,sans-serif;font-size:.82rem;font-weight:700;color:var(--t0)">{a["title"]}</div><span style="font-size:.54rem;color:{sc};background:rgba(255,255,255,.04);border-radius:6px;padding:2px 6px;white-space:nowrap;flex-shrink:0">{sn}</span></div><div style="color:var(--t3);font-size:.60rem;margin-bottom:.25rem">{a["authors"]} · <em>{a["source"]}</em> · {a["year"]}{cite}</div><div style="color:var(--t2);font-size:.72rem;line-height:1.6">{ab}</div></div>', unsafe_allow_html=True)
    ca,cb,cc=st.columns(3)
    with ca:
        if st.button("🔖 Salvo" if is_saved else "📌 Salvar",key=f"svw_{uid}"):
            if is_saved: st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]; st.toast("Removido")
            else: st.session_state.saved_articles.append(a); st.toast("Artigo salvo!")
            save_db(); st.rerun()
    with cb:
        if st.button("📋 Citar",key=f"ctw_{uid}"): st.toast(f'{a["authors"]} ({a["year"]}). {a["title"]}.')
    with cc:
        if a.get("url"): st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:var(--blu);font-size:.74rem;text-decoration:none;line-height:2.2;display:block">↗ Abrir artigo</a>', unsafe_allow_html=True)

def page_search():
    st.markdown('<h1 style="padding-top:.5rem;margin-bottom:.25rem">🔍 Busca Científica</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.72rem;margin-bottom:.7rem">Semantic Scholar · CrossRef · Plataforma Nebula</p>', unsafe_allow_html=True)
    c1,c2=st.columns([4,1])
    with c1: q=st.text_input("",placeholder="CRISPR · quantum ML · dark matter · neuroplasticidade…",key="sq",label_visibility="collapsed")
    with c2:
        if st.button("🔍 Buscar",key="btn_s",use_container_width=True):
            if q:
                with st.spinner("Buscando em 3 fontes…"):
                    nr=[p for p in st.session_state.feed_posts if q.lower() in p["title"].lower() or q.lower() in p.get("abstract","").lower()]
                    sr=search_ss(q,7); cr=search_cr(q,4)
                    st.session_state.search_results={"nebula":nr,"ss":sr,"cr":cr}; st.session_state.last_sq=q; record([q.lower()],.3)
    if st.session_state.get("search_results") and st.session_state.get("last_sq"):
        res=st.session_state.search_results; neb=res.get("nebula",[]); ss=res.get("ss",[]); cr=res.get("cr",[])
        web=ss+[x for x in cr if not any(x["title"].lower()==s["title"].lower() for s in ss)]
        total=len(neb)+len(web)
        st.markdown(f'<div style="font-size:.62rem;color:var(--t3);margin-bottom:.5rem">{total} resultados para "<em style="color:#00E676">{st.session_state.last_sq}</em>"</div>', unsafe_allow_html=True)
        ta,tn,tw=st.tabs([f"  Todos ({total})  ",f"  🔬 Nebula ({len(neb)})  ",f"  🌐 Internet ({len(web)})  "])
        with ta:
            if neb:
                st.markdown('<div style="font-size:.55rem;color:#00E676;font-weight:700;margin-bottom:.32rem;letter-spacing:.10em;text-transform:uppercase">Na Plataforma Nebula</div>', unsafe_allow_html=True)
                for p in neb: render_post(p,ctx="srch_all",compact=True)
            if web:
                if neb: st.markdown('<hr>', unsafe_allow_html=True)
                st.markdown('<div style="font-size:.55rem;color:var(--blu);font-weight:700;margin-bottom:.32rem;letter-spacing:.10em;text-transform:uppercase">Internet — Semantic Scholar & CrossRef</div>', unsafe_allow_html=True)
                for idx,a in enumerate(web): render_article(a,idx=idx,ctx="all_w")
            if not neb and not web: st.info("Nenhum resultado encontrado.")
        with tn:
            for p in neb: render_post(p,ctx="srch_neb",compact=True)
            if not neb: st.info("Nenhuma pesquisa na plataforma.")
        with tw:
            for idx,a in enumerate(web): render_article(a,idx=idx,ctx="web_t")
            if not web: st.info("Nenhum artigo na internet.")

# ═══════════════════════════════════════════════
#  CONEXÕES + IA VERDE
# ═══════════════════════════════════════════════
def page_knowledge():
    st.markdown('<h1 style="padding-top:.5rem;margin-bottom:.7rem">🕸 Rede de Conexões com IA</h1>', unsafe_allow_html=True)
    email=st.session_state.current_user; users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    api_key=st.session_state.get("anthropic_key",""); rlist=list(users.keys()); n=len(rlist)
    def get_tags(ue):
        ud=users.get(ue,{}); tags=set(area_tags(ud.get("area","")))
        for p in st.session_state.feed_posts:
            if p.get("author_email")==ue: tags.update(t.lower() for t in p.get("tags",[]))
        return tags
    rtags={ue:get_tags(ue) for ue in rlist}
    edges=[]
    for i in range(n):
        for j in range(i+1,n):
            e1,e2=rlist[i],rlist[j]; common=list(rtags[e1]&rtags[e2]); is_fol=e2 in st.session_state.followed or e1 in st.session_state.followed
            if common or is_fol: edges.append((e1,e2,common[:5],len(common)+(2 if is_fol else 0)))
    pos={}
    for idx,ue in enumerate(rlist):
        angle=2*3.14159*idx/max(n,1); rd=0.36+0.05*((hash(ue)%5)/4)
        pos[ue]={"x":0.5+rd*np.cos(angle),"y":0.5+rd*np.sin(angle),"z":0.5+0.12*((idx%4)/3-.35)}
    fig=go.Figure()
    for e1,e2,common,strength in edges:
        p1=pos[e1]; p2=pos[e2]; alpha=min(0.55,0.07+strength*0.07)
        fig.add_trace(go.Scatter3d(x=[p1["x"],p2["x"],None],y=[p1["y"],p2["y"],None],z=[p1["z"],p2["z"],None],mode="lines",line=dict(color=f"rgba(0,230,118,{alpha:.2f})",width=min(3,1+strength)),hoverinfo="none",showlegend=False))
    ncolors=["#FFD60A" if ue==email else("#00E676" if ue in st.session_state.followed else "#4CC9F0") for ue in rlist]
    nsizes=[22 if ue==email else(16 if ue in st.session_state.followed else 10) for ue in rlist]
    fig.add_trace(go.Scatter3d(x=[pos[ue]["x"] for ue in rlist],y=[pos[ue]["y"] for ue in rlist],z=[pos[ue]["z"] for ue in rlist],mode="markers+text",marker=dict(size=nsizes,color=ncolors,opacity=.92,line=dict(color="rgba(0,230,118,.10)",width=1)),text=[users.get(ue,{}).get("name","?").split()[0] for ue in rlist],textposition="top center",textfont=dict(color="#3A4260",size=8,family="DM Sans"),hovertemplate=[f"<b>{users.get(ue,{}).get('name','?')}</b><br>{users.get(ue,{}).get('area','')}<extra></extra>" for ue in rlist],showlegend=False))
    fig.update_layout(height=370,scene=dict(xaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),yaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),zaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),bgcolor="rgba(0,0,0,0)"),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig,use_container_width=True)
    c1,c2,c3,c4=st.columns(4)
    for col,(cls,v,l) in zip([c1,c2,c3,c4],[("mval-yel",len(rlist),"Pesquisadores"),("mval-grn",len(edges),"Conexões"),("mval-blu",len(st.session_state.followed),"Seguindo"),("mval-red",len(st.session_state.feed_posts),"Pesquisas")]):
        with col: st.markdown(f'<div class="mbox"><div class="{cls}">{v}</div><div class="mlbl">{l}</div></div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    tm,tai,tmi,tall=st.tabs(["  🗺 Mapa  ","  🤖 IA Conexões  ","  🔗 Minhas  ","  👥 Todos  "])
    with tm:
        for e1,e2,common,strength in sorted(edges,key=lambda x:-x[3])[:25]:
            n1=users.get(e1,{}); n2=users.get(e2,{}); ts=tags_html(common[:4]) if common else '<span style="color:var(--t3);font-size:.62rem">seguimento</span>'
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">{avh(ini(n1.get("name","?")),26,ugrad(e1))}<span style="font-size:.74rem;font-weight:700;font-family:Syne,sans-serif;color:#00E676">{n1.get("name","?")}</span><span style="color:var(--t3);font-size:.8rem">↔</span>{avh(ini(n2.get("name","?")),26,ugrad(e2))}<span style="font-size:.74rem;font-weight:700;font-family:Syne,sans-serif;color:#00E676">{n2.get("name","?")}</span><div style="flex:1">{ts}</div><span style="font-size:.58rem;color:#00E676;font-weight:700">{strength}pt</span></div></div>', unsafe_allow_html=True)
    with tai:
        st.markdown("""<div class="api-banner">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:.28rem">
    <div style="width:26px;height:26px;border-radius:7px;background:rgba(0,230,118,.14);display:flex;align-items:center;justify-content:center;font-size:.85rem">🤖</div>
    <div style="font-family:Syne,sans-serif;font-weight:700;font-size:.84rem;color:#00E676">Claude Haiku — IA Real de Conexões Científicas</div>
  </div>
  <div style="font-size:.70rem;color:var(--t2);line-height:1.6">Claude analisa perfil, publicações e tags para sugerir colaborações ideais com justificativa científica detalhada</div>
</div>""", unsafe_allow_html=True)
        if not api_key or not api_key.startswith("sk-"):
            st.markdown('<div class="pbox-yel"><div style="font-size:.70rem;color:#FFD60A;font-weight:600;margin-bottom:.2rem">⚠️ API Key necessária</div><div style="font-size:.66rem;color:var(--t2)">Insira chave na barra lateral. Gratuito: <strong>console.anthropic.com</strong> → API Keys</div></div>', unsafe_allow_html=True)
            st.markdown('<div style="font-size:.58rem;color:var(--t3);margin:.45rem 0 .3rem">Sugestões algorítmicas (sem IA):</div>', unsafe_allow_html=True)
            my_tags=rtags.get(email,set()); shown_algo=0
            for ue,ud in list(users.items())[:10]:
                if ue==email or ue in st.session_state.followed or shown_algo>=5: continue
                ct=my_tags&rtags.get(ue,set())
                if len(ct)>0:
                    shown_algo+=1; rg=ugrad(ue); rn=ud.get("name","?")
                    st.markdown(f'<div class="conn-ai"><div style="display:flex;align-items:center;gap:8px;margin-bottom:.42rem">{avh(ini(rn),32,rg)}<div style="flex:1"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.81rem;color:var(--t0)">{rn}</div><div style="font-size:.62rem;color:var(--t3)">{ud.get("area","")}</div></div><span class="badge-grn">{len(ct)} temas</span></div><div style="font-size:.68rem;color:var(--t2);margin-bottom:.4rem">{tags_html(list(ct)[:4])}</div></div>', unsafe_allow_html=True)
                    cf_b,cv_b=st.columns(2)
                    with cf_b:
                        if st.button(f"+ Seguir {rn.split()[0]}",key=f"ais_{ue}",use_container_width=True):
                            if ue not in st.session_state.followed: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                            save_db(); st.rerun()
                    with cv_b:
                        if st.button("👤 Ver",key=f"aip_{ue}",use_container_width=True): st.session_state.profile_view=ue; st.rerun()
        else:
            ck=f"conn_{email}_{len(users)}_{len(st.session_state.feed_posts)}"
            if st.button("🤖 Gerar Sugestões com Claude",key="btn_ai_conn"):
                with st.spinner("Claude Haiku analisando sua rede científica…"):
                    result,err=claude_connections(users,st.session_state.feed_posts,email)
                    if result: st.session_state.ai_conn_cache[ck]=result
                    else: st.error(f"Erro IA: {err}")
            ai_result=st.session_state.ai_conn_cache.get(ck)
            if ai_result:
                for sug in ai_result.get("sugestoes",[]):
                    sue=sug.get("email",""); sud=users.get(sue,{})
                    if not sud: continue
                    rn=sud.get("name","?"); rg=ugrad(sue); score=sug.get("score",70)
                    sc_c="#00E676" if score>=80 else("#FFD60A" if score>=60 else "#FF8C42")
                    temas=sug.get("temas_comuns",[]); is_fol2=sue in st.session_state.followed
                    st.markdown(f"""<div class="conn-ai">
  <div style="display:flex;align-items:center;gap:9px;margin-bottom:.5rem">
    {avh(ini(rn),36,rg)}<div style="flex:1"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.84rem;color:var(--t0)">{rn}</div><div style="font-size:.62rem;color:var(--t3)">{sud.get("area","")} · {sud.get("publications",0)} publ.</div></div>
    <div style="background:rgba(0,0,0,.35);border-radius:9px;padding:.3rem .6rem;text-align:center;flex-shrink:0;border:1px solid rgba(0,230,118,.10)"><div style="font-family:Syne,sans-serif;font-size:1rem;font-weight:900;color:{sc_c}">{score}</div><div style="font-size:.46rem;color:var(--t3);text-transform:uppercase">IA score</div></div>
  </div>
  <div style="background:rgba(0,230,118,.05);border:1px solid rgba(0,230,118,.10);border-radius:9px;padding:.44rem .62rem;margin-bottom:.38rem;font-size:.73rem;color:var(--t2);line-height:1.62">🤖 {sug.get("razao_cientifica","Conexão recomendada")}</div>
  {f'<div style="font-size:.68rem;color:var(--blu);margin-bottom:.35rem;padding:.3rem .6rem;background:rgba(76,201,240,.05);border-radius:7px">💡 {sug.get("potencial_pesquisa","")}</div>' if sug.get("potencial_pesquisa") else ""}
  <div>{tags_html(temas[:5])}</div>
</div>""", unsafe_allow_html=True)
                    c_f,c_p,c_c=st.columns(3)
                    with c_f:
                        if st.button("✓ Seguindo" if is_fol2 else "+ Seguir",key=f"aic_f_{sue}",use_container_width=True):
                            if not is_fol2: st.session_state.followed.append(sue); sud["followers"]=sud.get("followers",0)+1
                            save_db(); st.rerun()
                    with c_p:
                        if st.button("👤 Perfil",key=f"aic_p_{sue}",use_container_width=True): st.session_state.profile_view=sue; st.rerun()
                    with c_c:
                        if st.button("💬 Chat",key=f"aic_c_{sue}",use_container_width=True):
                            st.session_state.chat_messages.setdefault(sue,[]); st.session_state.active_chat=sue; st.session_state.page="chat"; st.rerun()
            else:
                st.markdown('<div style="text-align:center;padding:2rem;color:var(--t3);font-size:.76rem">Clique no botão acima para análise com Claude.</div>', unsafe_allow_html=True)
    with tmi:
        mc=[(e1,e2,c,s) for e1,e2,c,s in edges if e1==email or e2==email]
        if not mc: st.info("Sem conexões ainda.")
        for e1,e2,common,strength in sorted(mc,key=lambda x:-x[3]):
            oth=e2 if e1==email else e1; od=users.get(oth,{}); og=ugrad(oth)
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:8px">{avh(ini(od.get("name","?")),30,og)}<div style="flex:1"><div style="font-weight:700;font-size:.78rem;font-family:Syne,sans-serif;color:var(--t0)">{od.get("name","?")}</div><div style="font-size:.60rem;color:var(--t3)">{od.get("area","")}</div></div>{tags_html(common[:3])}<span style="font-size:.58rem;color:#00E676;font-weight:700;margin-left:4px">{strength}pt</span></div></div>', unsafe_allow_html=True)
            cv,cm2,_=st.columns([1,1,4])
            with cv:
                if st.button("👤 Ver",key=f"kv_{oth}",use_container_width=True): st.session_state.profile_view=oth; st.rerun()
            with cm2:
                if st.button("💬",key=f"kc_{oth}",use_container_width=True):
                    st.session_state.chat_messages.setdefault(oth,[]); st.session_state.active_chat=oth; st.session_state.page="chat"; st.rerun()
    with tall:
        sq2=st.text_input("",placeholder="🔍 Buscar…",key="all_s",label_visibility="collapsed")
        for ue,ud in users.items():
            if ue==email: continue
            rn=ud.get("name","?"); ua=ud.get("area","")
            if sq2 and sq2.lower() not in rn.lower() and sq2.lower() not in ua.lower(): continue
            is_fol=ue in st.session_state.followed; rg=ugrad(ue); online=is_online(ue)
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:8px">{avh(ini(rn),30,rg)}<div style="flex:1"><div style="font-size:.78rem;font-weight:700;font-family:Syne,sans-serif;color:var(--t0)">{dot}{rn}</div><div style="font-size:.62rem;color:var(--t3)">{ua} · {ud.get("publications",0)} publ.</div></div></div></div>', unsafe_allow_html=True)
            ca2,cb2,cc2=st.columns(3)
            with ca2:
                if st.button("👤",key=f"av_{ue}",use_container_width=True): st.session_state.profile_view=ue; st.rerun()
            with cb2:
                if st.button("✓" if is_fol else "+ Seguir",key=f"af_{ue}",use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"]=max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                    save_db(); st.rerun()
            with cc2:
                if st.button("💬",key=f"ac_{ue}",use_container_width=True):
                    st.session_state.chat_messages.setdefault(ue,[]); st.session_state.active_chat=ue; st.session_state.page="chat"; st.rerun()

# ═══════════════════════════════════════════════
#  VISÃO IA — Pipeline ML + Claude Vision REAL
# ═══════════════════════════════════════════════
def page_img_search():
    st.markdown('<h1 style="padding-top:.5rem;margin-bottom:.2rem">🔬 Visão IA Científica</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.70rem;margin-bottom:.65rem">Sobel · ORB Keypoints · GLCM · KMeans · FFT + Claude Vision Real</p>', unsafe_allow_html=True)
    api_key=st.session_state.get("anthropic_key",""); has_api=api_key.startswith("sk-") if api_key else False
    if has_api:
        st.markdown('<div class="api-banner" style="display:flex;align-items:center;gap:8px"><div style="font-size:.95rem">🤖</div><div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.78rem;color:#00E676">Claude Haiku Vision Ativo — Análise Real com IA</div><div style="font-size:.64rem;color:var(--t2)">Identifica O QUE É e DO QUE É FEITA a imagem com IA real</div></div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="pbox-yel"><div style="font-size:.67rem;color:#FFD60A;font-weight:600;margin-bottom:.18rem">💡 Modo ML apenas — sem Claude Vision</div><div style="font-size:.64rem;color:var(--t2)">Insira API key → <strong>console.anthropic.com</strong> → API Keys</div></div>', unsafe_allow_html=True)
    cu,cr=st.columns([1,2.2])
    with cu:
        st.markdown('<div class="glass" style="padding:.85rem">', unsafe_allow_html=True)
        img_file=st.file_uploader("📷 Imagem científica",type=["png","jpg","jpeg","webp","tiff"],key="img_up")
        img_bytes=None
        if img_file:
            img_bytes=img_file.read(); st.image(img_bytes,use_container_width=True)
            try:
                info=PILImage.open(io.BytesIO(img_bytes))
                st.markdown(f'<div style="font-size:.60rem;color:var(--t3);margin-top:.35rem">📐 {info.size[0]}×{info.size[1]}px · {info.mode} · {len(img_bytes)//1024}KB</div>', unsafe_allow_html=True)
            except: pass
        col_b1,col_b2=st.columns(2)
        with col_b1: run_ml=st.button("🔬 Analisar ML",key="btn_run",use_container_width=True,disabled=(img_bytes is None))
        with col_b2: run_claude=st.button("🤖 Claude IA",key="btn_vision",use_container_width=True,disabled=(not img_bytes or not has_api))
        if not has_api and img_bytes:
            st.markdown('<div style="font-size:.58rem;color:var(--t3);text-align:center;margin-top:.25rem">API key → Claude Vision</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("""<div class="pbox-grn" style="margin-top:.5rem">
  <div style="font-size:.62rem;color:#00E676;font-weight:700;margin-bottom:.22rem">📋 Pipeline</div>
  <div style="font-size:.60rem;color:var(--t2);line-height:1.75">
    🔲 Sobel — bordas e gradientes<br>
    📍 Keypoints — features locais<br>
    🎛 GLCM — textura e homog.<br>
    📡 FFT — frequências espaciais<br>
    🎨 KMeans — paleta dominante<br>
    🤖 Claude Vision — IA real
  </div>
</div>""", unsafe_allow_html=True)
    with cr:
        # ── PIPELINE ML ──
        if run_ml and img_bytes:
            img_hash=hashlib.md5(img_bytes[:2048]).hexdigest()
            with st.spinner("Pipeline ML… (≈1-2s)"):
                ml=run_ml_pipeline(img_hash,img_bytes)
            st.session_state.img_result=ml; st.session_state.claude_vision_result=None
        # ── CLAUDE VISION ──
        if run_claude and img_bytes:
            with st.spinner("Claude Haiku analisando imagem… (IA real)"):
                vision_data,err=claude_vision_analyze(img_bytes)
            if err: st.error(f"Erro Claude Vision: {err}")
            else: st.session_state.claude_vision_result=vision_data
            if not st.session_state.img_result:
                img_hash=hashlib.md5(img_bytes[:2048]).hexdigest()
                with st.spinner("Calculando ML…"):
                    ml=run_ml_pipeline(img_hash,img_bytes)
                st.session_state.img_result=ml

        # ── CLAUDE VISION RESULT — PRIMEIRO E DESTAQUE ──
        cv_data=st.session_state.get("claude_vision_result")
        if cv_data:
            conf=cv_data.get("confianca",0); conf_c="#00E676" if conf>=80 else("#FFD60A" if conf>=60 else "#FF3B5C")
            st.markdown(f"""<div class="ai-card ai-glow">
  <div style="font-size:.52rem;color:#00E676;letter-spacing:.10em;text-transform:uppercase;font-weight:700;margin-bottom:.45rem">🤖 CLAUDE HAIKU VISION — ANÁLISE REAL COM IA</div>
  <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:.65rem">
    <div style="flex:1">
      <div style="font-family:Syne,sans-serif;font-size:1.10rem;font-weight:800;color:var(--t0);margin-bottom:.2rem">{cv_data.get("o_que_e","—")}</div>
      <div style="font-size:.72rem;color:#00E676;font-weight:600;margin-bottom:.3rem">{cv_data.get("area_ciencia","")}</div>
      <div style="font-size:.70rem;color:var(--t2);line-height:1.65">{cv_data.get("de_que_e_feita","—")}</div>
    </div>
    <div style="background:rgba(0,0,0,.4);border-radius:10px;padding:.4rem .7rem;text-align:center;flex-shrink:0;border:1px solid rgba(0,230,118,.14)"><div style="font-family:Syne,sans-serif;font-size:1.2rem;font-weight:900;color:{conf_c}">{conf}%</div><div style="font-size:.46rem;color:var(--t3);text-transform:uppercase">confiança IA</div></div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:.45rem;margin-bottom:.5rem">
    <div class="ml-feat"><div style="font-size:.52rem;color:var(--t3);text-transform:uppercase;margin-bottom:.15rem">Tipo de Imagem</div><div style="font-size:.73rem;color:var(--t1)">{cv_data.get("tipo_imagem","—")}</div></div>
    <div class="ml-feat"><div style="font-size:.52rem;color:var(--t3);text-transform:uppercase;margin-bottom:.15rem">Técnica</div><div style="font-size:.73rem;color:var(--t1)">{cv_data.get("tecnica","—")}</div></div>
    <div class="ml-feat"><div style="font-size:.52rem;color:var(--t3);text-transform:uppercase;margin-bottom:.15rem">Escala</div><div style="font-size:.73rem;color:#FFD60A">{cv_data.get("escala","—")}</div></div>
    <div class="ml-feat"><div style="font-size:.52rem;color:var(--t3);text-transform:uppercase;margin-bottom:.15rem">Qualidade</div><div style="font-size:.73rem;color:#4CC9F0">{cv_data.get("qualidade","—")}</div></div>
  </div>
  {f'<div style="background:rgba(0,0,0,.25);border-radius:8px;padding:.45rem .65rem;margin-bottom:.45rem;font-size:.70rem;color:var(--t2);line-height:1.65;border:1px solid rgba(255,255,255,.05)"><strong style="color:var(--t1)">Significado das cores:</strong> {cv_data.get("cores_significado","")}</div>' if cv_data.get("cores_significado") else ""}
  {f'<div style="background:rgba(0,230,118,.06);border:1px solid rgba(0,230,118,.12);border-radius:8px;padding:.45rem .65rem;margin-bottom:.45rem;font-size:.70rem;color:var(--t2);line-height:1.65"><strong style="color:#00E676">🔍 Achados principais:</strong> {cv_data.get("achados_principais","")}</div>' if cv_data.get("achados_principais") else ""}
  {f'<div style="font-size:.65rem;color:var(--t2);margin-bottom:.32rem"><strong style="color:var(--t3)">Estruturas identificadas:</strong> {", ".join(cv_data.get("estruturas",[]))}</div>' if cv_data.get("estruturas") else ""}
</div>""", unsafe_allow_html=True)
            # Buscar artigos com termos da IA
            termos=cv_data.get("termos_busca","")
            if termos:
                st.markdown(f'<div style="font-size:.62rem;color:var(--t3);margin:.35rem 0 .45rem">🔍 Buscando artigos — termos IA: <em style="color:#00E676">{termos}</em></div>', unsafe_allow_html=True)
                with st.spinner("Buscando na literatura…"):
                    wr=search_ss(termos,5)
                if wr:
                    st.markdown('<div style="font-size:.58rem;color:#00E676;font-weight:700;margin-bottom:.32rem;letter-spacing:.08em;text-transform:uppercase">Artigos Relacionados — Semantic Scholar</div>', unsafe_allow_html=True)
                    for idx2,a2 in enumerate(wr): render_article(a2,idx=idx2+5000,ctx="img_claude")

        # ── ML RESULT ──
        ml=st.session_state.get("img_result")
        if ml and ml.get("ok"):
            cls_=ml["classification"]; col_=ml["color"]
            conf_c="#00E676" if cls_["confidence"]>80 else("#FFD60A" if cls_["confidence"]>60 else "#FF3B5C")
            if not cv_data:  # Só mostra card ML se não tem Vision
                st.markdown(f"""<div class="ai-card">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:.5rem">
    <div>
      <div style="font-size:.52rem;color:#00E676;letter-spacing:.10em;text-transform:uppercase;font-weight:700;margin-bottom:3px">🔬 Classificação ML</div>
      <div style="font-family:Syne,sans-serif;font-size:1.05rem;font-weight:800;color:var(--t0);margin-bottom:2px">{cls_["category"]}</div>
      <div style="font-size:.70rem;color:var(--t2);line-height:1.6">{cls_["origin"]}</div>
    </div>
    <div style="background:rgba(0,0,0,.4);border-radius:10px;padding:.42rem .75rem;text-align:center;flex-shrink:0;border:1px solid rgba(0,230,118,.10)"><div style="font-family:Syne,sans-serif;font-size:1.35rem;font-weight:900;color:{conf_c}">{cls_["confidence"]}%</div><div style="font-size:.46rem;color:var(--t3);text-transform:uppercase;font-weight:700">confiança</div></div>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:3px">{"".join(f'<span style="background:rgba(0,230,118,.05);border:1px solid rgba(0,230,118,.10);border-radius:20px;padding:1px 7px;font-size:.56rem;color:var(--t3)">{k}: {v}pt</span>' for k,v in cls_["scores"].items())}</div>
</div>""", unsafe_allow_html=True)
            # MÉTRICAS
            c1m,c2m,c3m,c4m,c5m=st.columns(5)
            with c1m: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:.95rem;font-weight:800;color:#FFD60A">{ml["sobel"]["mean"]:.3f}</div><div class="mlbl">Sobel</div></div>', unsafe_allow_html=True)
            with c2m: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:.95rem;font-weight:800;color:#00E676">{ml.get("n_kp",0)}</div><div class="mlbl">Keypoints</div></div>', unsafe_allow_html=True)
            with c3m: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:.95rem;font-weight:800;color:#4CC9F0">{"Periód." if ml["fft"]["periodic"] else "Aperiód."}</div><div class="mlbl">FFT</div></div>', unsafe_allow_html=True)
            with c4m: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:.95rem;font-weight:800;color:#B17DFF">{ml["glcm"].get("homogeneity",0):.3f}</div><div class="mlbl">Homog.</div></div>', unsafe_allow_html=True)
            with c5m: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:.95rem;font-weight:800;color:#FF8C42">{col_.get("entropy",0):.2f}</div><div class="mlbl">Entropia</div></div>', unsafe_allow_html=True)
            # ANÁLISE TABS
            ts,tk,tfft,trgb=st.tabs(["  🔲 Sobel/Mapa  ","  🎨 KMeans/Cores  ","  📡 FFT/GLCM  ","  📊 RGB  "])
            with ts:
                st.markdown('<div class="sobel-card">', unsafe_allow_html=True)
                st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.80rem;color:#00E676;margin-bottom:.45rem">🔲 Mapeamento Sobel — Detecção de Bordas e Gradientes</div>', unsafe_allow_html=True)
                smag=np.array(ml["sobel_map"],dtype=np.float32); nh,nw=ml["proc_size"][1],ml["proc_size"][0]
                fig_s=go.Figure(go.Heatmap(z=smag,colorscale=[[0,"#020B1E"],[0.25,"#003322"],[0.55,"#005533"],[0.8,"#00E676"],[1.0,"#FFFFFF"]],showscale=True,colorbar=dict(tickfont=dict(color="#3A4260",size=8),thickness=8,len=0.8)))
                fig_s.update_layout(height=200,margin=dict(l=0,r=40,t=5,b=0),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",xaxis=dict(showticklabels=False,showgrid=False),yaxis=dict(showticklabels=False,showgrid=False,scaleanchor='x'))
                st.plotly_chart(fig_s,use_container_width=True)
                st.markdown(f'<div style="font-size:.70rem;color:var(--t2);line-height:1.72;margin-bottom:.42rem">Sobel calcula derivada parcial em X e Y revelando bordas. <strong style="color:var(--t0)">Intensidade média: {ml["sobel"]["mean"]:.4f}</strong> — {"ALTA" if ml["sobel"]["mean"]>0.1 else "baixa"} densidade de bordas. <strong style="color:var(--t0)">Cobertura: {ml["sobel"]["density"]*100:.1f}%</strong> dos pixels. Direção predominante: <strong style="color:#FFD60A">{ml.get("edge_dir_mean",0):.1f}°</strong></div>', unsafe_allow_html=True)
                eh=ml["sobel"]["hist"]
                fig_e=go.Figure(go.Bar(y=eh,x=list(range(len(eh))),marker=dict(color=list(range(len(eh))),colorscale=[[0,"#020B1E"],[.35,"#003322"],[.65,"#00E676"],[1,"#FFFFFF"]])))
                fig_e.update_layout(**pc_dark(145),title=dict(text="Histograma de Intensidades Sobel",font=dict(color="#E4E8F4",family="Syne",size=9)),margin=dict(l=8,r=8,t=28,b=8))
                st.markdown('<div class="chart-wrap">', unsafe_allow_html=True); st.plotly_chart(fig_e,use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)
                # Keypoints overlay
                kps=ml.get("kps",[]); n_kp=ml.get("n_kp",0)
                st.markdown(f'<div class="pbox-grn"><div style="font-size:.62rem;color:#00E676;font-weight:700;margin-bottom:.22rem">ORB Keypoints: {n_kp} detectados</div><div style="font-size:.68rem;color:var(--t2)">Grad. máx: <strong style="color:var(--t0)">{ml["sobel"]["max"]:.4f}</strong> · Direção std: <strong style="color:#FFD60A">{ml.get("edge_dir_std",0):.1f}°</strong></div></div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with tk:
                pal=ml.get("palette",[])
                if pal:
                    st.markdown('<div style="font-size:.60rem;color:var(--t3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:.5rem">KMeans — 7 Clusters Dominantes</div>', unsafe_allow_html=True)
                    for cp in pal:
                        pct=cp.get("pct",0); hex_c=cp.get("hex","#888"); r2,g2,b2=cp.get("rgb",(128,128,128))
                        bar=f'<div style="height:5px;width:{min(int(pct*3.8),100)}%;background:{hex_c};border-radius:2px;margin-top:2px;max-width:100%"></div>'
                        temp_icon="🔥" if cp.get("temp")=="quente" else("❄️" if cp.get("temp")=="fria" else "⚪")
                        st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:.32rem"><div style="width:27px;height:27px;border-radius:6px;background:{hex_c};flex-shrink:0;border:1px solid rgba(255,255,255,.07)"></div><div style="flex:1"><div style="display:flex;justify-content:space-between;font-size:.66rem;color:var(--t2)"><span>{hex_c.upper()} {temp_icon}</span><span>{pct:.1f}%</span></div>{bar}</div><div style="font-size:.56rem;color:var(--t3);width:75px">RGB({r2},{g2},{b2})</div></div>', unsafe_allow_html=True)
                    fig_pal=go.Figure(go.Pie(values=[c["pct"] for c in pal],labels=[c["hex"] for c in pal],marker=dict(colors=[c["hex"] for c in pal],line=dict(color=["#020B1E"]*7,width=2)),textfont=dict(color="white",size=7),hole=0.45))
                    fig_pal.update_layout(height=200,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=5,b=0),legend=dict(font=dict(color="#3A4260",size=7)))
                    st.markdown('<div class="chart-wrap">', unsafe_allow_html=True); st.plotly_chart(fig_pal,use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)
                    warm_pct=sum(c["pct"] for c in pal if c.get("temp")=="quente"); cool_pct=sum(c["pct"] for c in pal if c.get("temp")=="fria")
                    dom="quente" if warm_pct>cool_pct else "fria"
                    st.markdown(f'<div class="ml-feat"><div style="font-size:.68rem;color:var(--t2);line-height:1.7">Temperatura dominante: <strong style="color:{"#FF8C42" if dom=="quente" else "#4CC9F0"}">{dom}</strong>. Simetria: <strong style="color:var(--t0)">{col_.get("sym",0):.3f}</strong>. Entropia: <strong style="color:var(--t0)">{col_.get("entropy",0):.3f}</strong>. RGB médio: ({col_.get("r",0):.0f},{col_.get("g",0):.0f},{col_.get("b",0):.0f})</div></div>', unsafe_allow_html=True)
            with tfft:
                fft_r=ml["fft"]; lf,mf,hf=fft_r["lf"],fft_r["mf"],fft_r["hf"]
                fig_fft=go.Figure(go.Bar(x=["Baixa freq.\n(estruturas grandes)","Média freq.\n(detalhes)","Alta freq.\n(textura/ruído)"],y=[lf,mf,hf],marker=dict(color=["#00E676","#FFD60A","#4CC9F0"]),text=[f"{v:.3f}" for v in [lf,mf,hf]],textposition="outside",textfont=dict(color="#3A4260",size=9)))
                fig_fft.update_layout(**pc_dark(215),title=dict(text="FFT 2D — Frequências Espaciais",font=dict(color="#E4E8F4",family="Syne",size=9)),margin=dict(l=8,r=8,t=28,b=8))
                st.markdown('<div class="chart-wrap">', unsafe_allow_html=True); st.plotly_chart(fig_fft,use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="ml-feat"><div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:.4rem;font-size:.68rem"><div style="color:var(--t2)">Score periódico<br><strong style="color:{"#00E676" if fft_r["periodic"] else "var(--t2)"};font-size:.88rem">{fft_r["per_score"]:.1f}</strong></div><div style="color:var(--t2)">Escala dom.<br><strong style="color:#FFD60A;font-size:.88rem">{fft_r["dominant"]}</strong></div><div style="color:var(--t2)">Estrutura<br><strong style="color:{"#00E676" if fft_r["periodic"] else "var(--t2)"};font-size:.88rem">{"Periódica ✓" if fft_r["periodic"] else "Aperiódica"}</strong></div></div></div>', unsafe_allow_html=True)
                st.markdown("<hr>", unsafe_allow_html=True)
                glcm_r=ml["glcm"]; glcm_vals=[(k,v) for k,v in glcm_r.items() if isinstance(v,float) and k!="tipo"]
                if glcm_vals:
                    fig_gl=go.Figure(go.Bar(x=[k.replace('_',' ').title() for k,_ in glcm_vals],y=[v for _,v in glcm_vals],marker=dict(color=[v for _,v in glcm_vals],colorscale=[[0,"#030A1A"],[.4,"#003322"],[.7,"#00E676"],[1,"#FFD60A"]]),text=[f"{v:.3f}" for _,v in glcm_vals],textposition="outside",textfont=dict(color="#3A4260",size=8)))
                    fig_gl.update_layout(**pc_dark(185),title=dict(text=f"GLCM — Textura: {glcm_r.get('tipo','—')}",font=dict(color="#E4E8F4",family="Syne",size=9)),margin=dict(l=8,r=8,t=28,b=8))
                    st.markdown('<div class="chart-wrap">', unsafe_allow_html=True); st.plotly_chart(fig_gl,use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)
            with trgb:
                h_data=ml.get("histograms",{}); bx=list(range(0,256,8))[:32]
                if h_data:
                    fig4=go.Figure()
                    fig4.add_trace(go.Scatter(x=bx,y=h_data.get("r",[])[:32],fill='tozeroy',name='R',line=dict(color='rgba(255,59,92,.85)',width=1.5),fillcolor='rgba(255,59,92,.07)'))
                    fig4.add_trace(go.Scatter(x=bx,y=h_data.get("g",[])[:32],fill='tozeroy',name='G',line=dict(color='rgba(0,230,118,.85)',width=1.5),fillcolor='rgba(0,230,118,.07)'))
                    fig4.add_trace(go.Scatter(x=bx,y=h_data.get("b",[])[:32],fill='tozeroy',name='B',line=dict(color='rgba(76,201,240,.85)',width=1.5),fillcolor='rgba(76,201,240,.07)'))
                    fig4.update_layout(**pc_dark(210),title=dict(text="Histograma RGB",font=dict(color="#E4E8F4",family="Syne",size=9)),margin=dict(l=8,r=8,t=28,b=8),legend=dict(font=dict(color="#3A4260",size=8)))
                    st.markdown('<div class="chart-wrap">', unsafe_allow_html=True); st.plotly_chart(fig4,use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)
                mr=col_.get("r",128); mg2_=col_.get("g",128); mb_=col_.get("b",128)
                hex_m="#{:02x}{:02x}{:02x}".format(int(mr),int(mg2_),int(mb_)); temp="Quente 🔥" if col_.get("warm") else("Fria ❄️" if col_.get("cool") else "Neutra ⚪")
                dom_ch="R" if mr>mg2_ and mr>mb_ else("G" if mg2_>mb_ else "B"); ch_c="#FF3B5C" if dom_ch=="R" else("#00E676" if dom_ch=="G" else "#4CC9F0")
                st.markdown(f'<div class="ml-feat" style="display:grid;grid-template-columns:repeat(5,1fr);gap:.4rem;font-size:.68rem;text-align:center"><div><div style="width:24px;height:24px;border-radius:5px;background:{hex_m};margin:0 auto .15rem;border:1px solid rgba(255,255,255,.08)"></div><div style="color:var(--t3)">Média</div></div><div><div style="font-weight:700;font-size:.80rem;color:#FFD60A">{temp}</div><div style="color:var(--t3)">Temperatura</div></div><div><div style="font-weight:700;font-size:.80rem;color:#00E676">{col_.get("sym",0):.3f}</div><div style="color:var(--t3)">Simetria</div></div><div><div style="font-weight:700;font-size:.80rem;color:#4CC9F0">{col_.get("entropy",0):.3f}</div><div style="color:var(--t3)">Entropia</div></div><div><div style="font-weight:700;font-size:.80rem;color:{ch_c}">{dom_ch}</div><div style="color:var(--t3)">Canal dom.</div></div></div>', unsafe_allow_html=True)
            # PESQUISAS RELACIONADAS
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.82rem;margin-bottom:.45rem;color:var(--t0)">🔗 Pesquisas Relacionadas</div>', unsafe_allow_html=True)
            tn2,tw2=st.tabs([f"  🔬 Nebula  ","  🌐 Internet  "])
            kw_s=cls_["kw"]; kw_list=kw_s.lower().split()[:6]
            with tn2:
                nr=[(sum(1 for k in kw_list if len(k)>3 and k in (p.get("title","")+" "+p.get("abstract","")).lower()),p) for p in st.session_state.feed_posts]
                nr=[p for s,p in sorted(nr,key=lambda x:-x[0]) if s>0]
                for p in nr[:4]: render_post(p,ctx="img_neb",compact=True)
                if not nr: st.markdown('<div style="color:var(--t3);padding:.8rem">Nenhuma pesquisa similar na plataforma.</div>', unsafe_allow_html=True)
            with tw2:
                ck=f"img_{kw_s[:40]}"
                if ck not in st.session_state.scholar_cache:
                    with st.spinner("Buscando artigos na internet…"): st.session_state.scholar_cache[ck]=search_ss(kw_s,5)
                wr2=st.session_state.scholar_cache.get(ck,[])
                for idx3,a3 in enumerate(wr2): render_article(a3,idx=idx3+3000,ctx="img_web")
                if not wr2: st.markdown('<div style="color:var(--t3);padding:.8rem">Sem resultados na internet.</div>', unsafe_allow_html=True)
        elif not img_file:
            st.markdown('<div class="glass" style="padding:4.5rem 2rem;text-align:center"><div style="font-size:2.8rem;opacity:.12;margin-bottom:1rem">🔬</div><div style="font-family:Syne,sans-serif;font-size:.95rem;color:var(--t1)">Carregue uma imagem científica</div><div style="font-size:.72rem;color:var(--t3);margin-top:.4rem;line-height:1.9">Sobel · ORB · GLCM · KMeans · FFT<br><br>Com API Key:<br>🤖 Claude Vision — análise real com IA<br>O que é a imagem e do que é feita</div></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════
#  FOLDERS
# ═══════════════════════════════════════════════
def page_folders():
    st.markdown('<h1 style="padding-top:.5rem;margin-bottom:.9rem">📁 Pastas de Pesquisa</h1>', unsafe_allow_html=True)
    email=st.session_state.current_user; u=guser(); ra=u.get("area","")
    c1,c2,_=st.columns([2,1.2,1.5])
    with c1: nfn=st.text_input("Nome da pasta",placeholder="Ex: Genômica Comparativa",key="nf_n")
    with c2: nfd=st.text_input("Descrição",key="nf_d")
    if st.button("📁 Criar",key="btn_nf",use_container_width=True):
        if nfn.strip():
            if nfn not in st.session_state.folders: st.session_state.folders[nfn]={"desc":nfd,"files":[],"notes":"","analyses":{}}; save_db(); st.success(f"'{nfn}' criada!"); st.rerun()
            else: st.warning("Já existe.")
        else: st.warning("Digite um nome.")
    st.markdown("<hr>", unsafe_allow_html=True)
    if not st.session_state.folders:
        st.markdown('<div class="glass" style="text-align:center;padding:4rem"><div style="font-size:2.2rem;opacity:.12;margin-bottom:.7rem">📁</div><div style="color:var(--t3)">Nenhuma pasta criada.</div></div>', unsafe_allow_html=True); return
    for fn,fd in list(st.session_state.folders.items()):
        if not isinstance(fd,dict): fd={"files":fd,"desc":"","notes":"","analyses":{}}; st.session_state.folders[fn]=fd
        files=fd.get("files",[]); analyses=fd.get("analyses",{})
        with st.expander(f"📁 {fn} — {len(files)} arquivo(s)"):
            up=st.file_uploader("",type=None,key=f"up_{fn}",label_visibility="collapsed",accept_multiple_files=True)
            if up:
                for uf in up:
                    if uf.name not in files: files.append(uf.name)
                    if fn not in st.session_state.folder_files_bytes: st.session_state.folder_files_bytes[fn]={}
                    uf.seek(0); st.session_state.folder_files_bytes[fn][uf.name]=uf.read()
                fd["files"]=files; save_db(); st.success(f"{len(up)} adicionado(s)!")
            if files:
                for f in files:
                    ft=ftype(f); ha=f in analyses
                    icon={"PDF":"📄","Word":"📝","Planilha":"📊","Dados":"📈","Código":"🐍","Imagem":"🖼","Markdown":"📋"}.get(ft,"📄")
                    ab2=' <span class="badge-grn" style="font-size:.57rem">✓</span>' if ha else ''
                    st.markdown(f'<div style="display:flex;align-items:center;gap:7px;padding:.38rem 0;border-bottom:1px solid rgba(255,255,255,.04)"><span>{icon}</span><span style="font-size:.75rem;color:var(--t2);flex:1">{f}</span>{ab2}</div>', unsafe_allow_html=True)
            ca2,cb2,_=st.columns([1.5,1.5,2])
            with ca2:
                if st.button("🔬 Analisar",key=f"an_{fn}",use_container_width=True):
                    if files:
                        pb=st.progress(0,"Iniciando…"); fb=st.session_state.folder_files_bytes.get(fn,{})
                        for fi,f in enumerate(files):
                            pb.progress((fi+1)/len(files),f"Analisando: {f[:25]}…"); fbytes=fb.get(f,b""); ft2=ftype(f)
                            analyses[f]=analyze_doc(f,fbytes,ft2,ra)
                        fd["analyses"]=analyses; save_db(); pb.empty(); st.success("✓ Completo!"); st.rerun()
                    else: st.warning("Adicione arquivos.")
            with cb2:
                if st.button("🗑 Excluir",key=f"df_{fn}",use_container_width=True):
                    del st.session_state.folders[fn]; save_db(); st.rerun()
            if analyses:
                for f,an in analyses.items():
                    with st.expander(f"🔬 {f}"):
                        kws=an.get("keywords",[]); topics=an.get("topics",{}); rel=an.get("relevance_score",0); wq=an.get("writing_quality",0)
                        rc="#00E676" if rel>=70 else("#FFD60A" if rel>=45 else "#FF3B5C")
                        st.markdown(f'<div class="abox"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.86rem;margin-bottom:.3rem">{f}</div><div style="font-size:.76rem;color:var(--t2)">{an.get("summary","")}</div><div style="display:flex;gap:1.2rem;margin-top:.5rem"><div style="text-align:center"><div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:900;color:{rc}">{rel}%</div><div style="font-size:.55rem;color:var(--t3);text-transform:uppercase">Relevância</div></div><div style="text-align:center"><div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:900;color:#4CC9F0">{wq}%</div><div style="font-size:.55rem;color:var(--t3);text-transform:uppercase">Qualidade</div></div><div style="text-align:center"><div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:900;color:#FF8C42">{an.get("word_count",0)}</div><div style="font-size:.55rem;color:var(--t3);text-transform:uppercase">Palavras</div></div></div></div>', unsafe_allow_html=True)
                        if kws: st.markdown(tags_html(kws[:16]), unsafe_allow_html=True)
                        if topics:
                            fig2=go.Figure(go.Pie(labels=list(topics.keys()),values=list(topics.values()),hole=0.5,marker=dict(colors=VIB[:len(topics)],line=dict(color=["#020B1E"]*15,width=2)),textfont=dict(color="white",size=8)))
                            fig2.update_layout(height=220,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(font=dict(color="#3A4260",size=8)),margin=dict(l=0,r=0,t=10,b=0))
                            st.markdown('<div class="chart-wrap">', unsafe_allow_html=True); st.plotly_chart(fig2,use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════
#  ANALYTICS
# ═══════════════════════════════════════════════
def page_analytics():
    st.markdown('<h1 style="padding-top:.5rem;margin-bottom:.9rem">📊 Painel Analítico</h1>', unsafe_allow_html=True)
    email=st.session_state.current_user; d=st.session_state.stats_data
    tf,tp,ti,tpr=st.tabs(["  📁 Pastas  ","  📝 Publicações  ","  📈 Impacto  ","  🎯 Interesses  "])
    with tf:
        folders=st.session_state.folders
        if not folders: st.markdown('<div class="glass" style="text-align:center;padding:3rem;color:var(--t3)">Crie pastas na aba Pastas.</div>', unsafe_allow_html=True)
        else:
            all_an={f:an for fd in folders.values() if isinstance(fd,dict) for f,an in fd.get("analyses",{}).items()}
            tot_f=sum(len(fd.get("files",[]) if isinstance(fd,dict) else fd) for fd in folders.values())
            all_kw=[kw for an in all_an.values() for kw in an.get("keywords",[])]
            all_top=defaultdict(int)
            for an in all_an.values():
                for t,s in an.get("topics",{}).items(): all_top[t]+=s
            c1,c2,c3,c4=st.columns(4)
            for col,(cls,v,l) in zip([c1,c2,c3,c4],[("mval-yel",len(folders),"Pastas"),("mval-grn",tot_f,"Arquivos"),("mval-blu",len(all_an),"Analisados"),("mval-red",len(set(all_kw[:100])),"Keywords")]):
                with col: st.markdown(f'<div class="mbox"><div class="{cls}">{v}</div><div class="mlbl">{l}</div></div>', unsafe_allow_html=True)
            if all_top:
                fig=go.Figure(go.Bar(x=list(all_top.values())[:8],y=list(all_top.keys())[:8],orientation='h',marker=dict(color=VIB[:8])))
                fig.update_layout(**pc_dark(250),yaxis=dict(showgrid=False,color="#3A4260",tickfont=dict(size=9)),title=dict(text="Temas por frequência",font=dict(color="#E4E8F4",family="Syne",size=9)))
                st.markdown('<div class="chart-wrap">', unsafe_allow_html=True); st.plotly_chart(fig,use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)
    with tp:
        my_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==email]
        if not my_posts: st.markdown('<div class="glass" style="text-align:center;padding:2.5rem;color:var(--t3)">Publique pesquisas no Feed.</div>', unsafe_allow_html=True)
        else:
            c1,c2,c3=st.columns(3)
            with c1: st.markdown(f'<div class="mbox"><div class="mval-yel">{len(my_posts)}</div><div class="mlbl">Pesquisas</div></div>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="mbox"><div class="mval-grn">{sum(p["likes"] for p in my_posts)}</div><div class="mlbl">Curtidas</div></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="mbox"><div class="mval-blu">{sum(len(p.get("comments",[])) for p in my_posts)}</div><div class="mlbl">Comentários</div></div>', unsafe_allow_html=True)
            for p in sorted(my_posts,key=lambda x:x.get("date",""),reverse=True):
                st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;justify-content:space-between"><div style="font-family:Syne,sans-serif;font-size:.85rem;font-weight:700;color:var(--t0)">{p["title"][:55]}</div>{badge(p["status"])}</div><div style="font-size:.68rem;color:var(--t3);margin-top:.35rem">{p.get("date","")} · {p["likes"]} curtidas · {len(p.get("comments",[]))} comentários · 👁 {fmt_num(p.get("views",0))}</div></div>', unsafe_allow_html=True)
    with ti:
        c1,c2,c3=st.columns(3)
        with c1: st.markdown(f'<div class="mbox"><div class="mval-yel">{d.get("h_index",4)}</div><div class="mlbl">Índice H</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="mbox"><div class="mval-grn">{d.get("fator_impacto",3.8):.1f}</div><div class="mlbl">Fator Impacto</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="mbox"><div class="mval-blu">{len(st.session_state.saved_articles)}</div><div class="mlbl">Salvos</div></div>', unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)
        nh=st.number_input("Índice H",0,200,d.get("h_index",4),key="e_h"); nfi=st.number_input("Fator impacto",0.0,100.0,float(d.get("fator_impacto",3.8)),step=0.1,key="e_fi"); nn=st.text_area("Notas",value=d.get("notes",""),key="e_nt",height=70)
        if st.button("💾 Salvar",key="btn_sm"): d.update({"h_index":nh,"fator_impacto":nfi,"notes":nn}); st.success("✓ Salvo!")
    with tpr:
        prefs=st.session_state.user_prefs.get(email,{})
        if prefs:
            top=sorted(prefs.items(),key=lambda x:-x[1])[:12]; mx=max(s for _,s in top) if top else 1
            cats=[t for t,_ in top[:8]]; vals=[round(s/mx*100) for _,s in top[:8]]
            if len(cats)>=3:
                fig3=go.Figure(go.Scatterpolar(r=vals+[vals[0]],theta=cats+[cats[0]],fill='toself',line=dict(color="#00E676",width=1.5),fillcolor="rgba(0,230,118,.08)"))
                fig3.update_layout(height=265,polar=dict(bgcolor="rgba(0,0,0,0)",radialaxis=dict(visible=True,gridcolor="rgba(255,255,255,.04)",color="#3A4260",tickfont=dict(size=8)),angularaxis=dict(gridcolor="rgba(255,255,255,.04)",color="#3A4260",tickfont=dict(size=9))),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=40,r=40,t=15,b=15))
                st.markdown('<div class="chart-wrap">', unsafe_allow_html=True); st.plotly_chart(fig3,use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)
        else: st.info("Interaja com pesquisas para ver interesses.")

# ═══════════════════════════════════════════════
#  CHAT
# ═══════════════════════════════════════════════
def page_chat():
    st.markdown('<h1 style="padding-top:.5rem;margin-bottom:.9rem">💬 Mensagens</h1>', unsafe_allow_html=True)
    cc,cm=st.columns([.85,2.8]); email=st.session_state.current_user
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    with cc:
        st.markdown('<div style="font-size:.58rem;font-weight:700;color:#1E2440;letter-spacing:.12em;text-transform:uppercase;margin-bottom:.7rem">Conversas</div>', unsafe_allow_html=True)
        shown=set()
        for ue in st.session_state.chat_contacts:
            if ue==email or ue in shown: continue
            shown.add(ue); ud=users.get(ue,{}); un=ud.get("name","?"); ui=ini(un); ug=ugrad(ue)
            msgs=st.session_state.chat_messages.get(ue,[]); last=msgs[-1]["text"][:22]+"…" if msgs and len(msgs[-1]["text"])>22 else(msgs[-1]["text"] if msgs else "Iniciar")
            active=st.session_state.active_chat==ue; online=is_online(ue)
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            bg=f"rgba(0,230,118,{'.07' if active else '.03'})"; bdr=f"rgba(0,230,118,{'.20' if active else '.06'})"
            st.markdown(f'<div style="background:{bg};border:1px solid {bdr};border-radius:12px;padding:8px 10px;margin-bottom:4px"><div style="display:flex;align-items:center;gap:7px">{avh(ui,30,ug)}<div style="overflow:hidden;flex:1"><div style="font-size:.76rem;font-weight:600;font-family:Syne,sans-serif;color:var(--t0)">{dot}{un}</div><div style="font-size:.63rem;color:var(--t3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{last}</div></div></div></div>', unsafe_allow_html=True)
            if st.button("→",key=f"oc_{ue}",use_container_width=True): st.session_state.active_chat=ue; st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
        nc2=st.text_input("",placeholder="E-mail…",key="new_ct",label_visibility="collapsed")
        if st.button("+ Adicionar",key="btn_ac",use_container_width=True):
            if nc2 in users and nc2!=email:
                if nc2 not in st.session_state.chat_contacts: st.session_state.chat_contacts.append(nc2)
                st.rerun()
    with cm:
        if st.session_state.active_chat:
            contact=st.session_state.active_chat; cd=users.get(contact,{}); cn=cd.get("name","?"); ci=ini(cn); cg=ugrad(contact)
            msgs=st.session_state.chat_messages.get(contact,[]); online=is_online(contact)
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            st.markdown(f'<div style="background:rgba(0,230,118,.04);border:1px solid rgba(0,230,118,.10);border-radius:14px;padding:10px 14px;margin-bottom:.85rem;display:flex;align-items:center;gap:10px">{avh(ci,36,cg)}<div style="flex:1"><div style="font-weight:700;font-size:.88rem;font-family:Syne,sans-serif;color:var(--t0)">{dot}{cn}</div><div style="font-size:.63rem;color:#00E676">🔒 AES-256 · {cd.get("area","")}</div></div></div>', unsafe_allow_html=True)
            for msg in msgs:
                im=msg["from"]=="me"; cls2="bme" if im else "bthem"
                st.markdown(f'<div style="display:flex;{"justify-content:flex-end" if im else ""}"><div class="{cls2}">{msg["text"]}<div style="font-size:.57rem;color:var(--t3);margin-top:2px;text-align:{"right" if im else "left"}">{msg["time"]}</div></div></div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            ci2,cb2=st.columns([5,1])
            with ci2: nm=st.text_input("",placeholder="Escreva uma mensagem…",key=f"mi_{contact}",label_visibility="collapsed")
            with cb2:
                if st.button("→",key=f"ms_{contact}",use_container_width=True):
                    if nm: now=datetime.now().strftime("%H:%M"); st.session_state.chat_messages.setdefault(contact,[]).append({"from":"me","text":nm,"time":now}); st.rerun()
        else:
            st.markdown('<div class="glass" style="text-align:center;padding:5rem"><div style="font-size:2.2rem;opacity:.10;margin-bottom:.85rem">💬</div><div style="font-family:Syne,sans-serif;font-size:.96rem;color:var(--t1)">Selecione uma conversa</div><div style="font-size:.70rem;color:var(--t3);margin-top:.4rem">🔒 Criptografado end-to-end</div></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════
#  SETTINGS
# ═══════════════════════════════════════════════
def page_settings():
    st.markdown('<h1 style="padding-top:.5rem;margin-bottom:.9rem">⚙️ Configurações</h1>', unsafe_allow_html=True)
    email=st.session_state.current_user; ud=st.session_state.users.get(email,{})
    st.markdown(f'<div class="abox"><div style="font-size:.58rem;color:var(--t3);text-transform:uppercase;letter-spacing:.10em;margin-bottom:.4rem;font-weight:700">Conta</div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.95rem;color:#00E676">{email}</div><div style="font-size:.65rem;color:var(--t3);margin-top:.2rem">Membro desde {ud.get("joined","—")} · {ud.get("publications",0)} publicações · {fmt_num(ud.get("citations",0))} citações</div></div>', unsafe_allow_html=True)
    en=ud.get("2fa_enabled",False)
    if st.button("✕ Desativar 2FA" if en else "✓ Ativar 2FA",key="cfg_2fa"):
        st.session_state.users[email]["2fa_enabled"]=not en; save_db(); st.rerun()
    st.markdown("<hr>", unsafe_allow_html=True)
    with st.form("cpw"):
        op=st.text_input("Senha atual",type="password"); np2=st.text_input("Nova senha",type="password"); nc3=st.text_input("Confirmar",type="password")
        if st.form_submit_button("🔑 Alterar senha",use_container_width=True):
            if hp(op)!=ud.get("password",""): st.error("Senha incorreta.")
            elif np2!=nc3: st.error("Não coincidem.")
            elif len(np2)<6: st.error("Mínimo 6 chars.")
            else: st.session_state.users[email]["password"]=hp(np2); save_db(); st.success("✓ Alterada!")
    st.markdown("<hr>", unsafe_allow_html=True)
    for nm,ds in [("🔒 AES-256","Criptografia end-to-end"),("🔏 SHA-256","Hash de senhas"),("🛡 TLS 1.3","Transmissão segura")]:
        st.markdown(f'<div class="pbox-grn"><div style="display:flex;align-items:center;gap:9px"><div style="width:24px;height:24px;border-radius:7px;background:rgba(0,230,118,.12);display:flex;align-items:center;justify-content:center;color:#00E676;font-size:.72rem">✓</div><div><div style="font-weight:700;color:#00E676;font-size:.78rem">{nm}</div><div style="font-size:.66rem;color:var(--t3)">{ds}</div></div></div></div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(f'<div class="pbox-blu"><div style="font-size:.62rem;color:#4CC9F0;font-weight:700;margin-bottom:.25rem">🤖 IA Ativa: Claude Haiku (claude-haiku-4-5)</div><div style="font-size:.64rem;color:var(--t2);line-height:1.7">Visão IA — O que é e do que é feita cada imagem científica<br>Conexões — Sugestões de colaboração científica<br>Draft IA — Rascunho de resumo de pesquisa</div></div>', unsafe_allow_html=True)
    if st.button("🚪 Sair da conta",key="logout",use_container_width=True):
        st.session_state.logged_in=False; st.session_state.current_user=None; st.session_state.page="feed"; st.rerun()

# ═══════════════════════════════════════════════
#  ROUTER
# ═══════════════════════════════════════════════
def main():
    inject_css()
    if not st.session_state.logged_in:
        page_login(); return
    render_nav()
    if st.session_state.profile_view:
        page_profile(st.session_state.profile_view); return
    {"feed":page_feed,"search":page_search,"knowledge":page_knowledge,"folders":page_folders,"analytics":page_analytics,"img_search":page_img_search,"chat":page_chat,"settings":page_settings}.get(st.session_state.page,page_feed)()

main()
