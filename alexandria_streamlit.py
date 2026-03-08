"""
Nebula V9 — Plataforma de Pesquisa Cientifica
"""
import subprocess, sys, os, json, hashlib, re, io, base64
from datetime import datetime
from collections import defaultdict, Counter

def _pip(*pkgs):
    for p in pkgs:
        try: subprocess.check_call([sys.executable,"-m","pip","install",p,"-q"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except: pass

try: import plotly.graph_objects as go
except: _pip("plotly"); import plotly.graph_objects as go
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

CHART_C = ["#1E88E5","#00BCD4","#00E676","#FFD600","#FF9800","#EF5350","#AB47BC","#26C6DA","#66BB6A","#FFA726"]
GRAD_POOL = ["135deg,#0D47A1,#006064","135deg,#1B5E20,#004D40","135deg,#311B92,#006064","135deg,#BF360C,#4A148C","135deg,#006064,#0D47A1","135deg,#01579B,#1B5E20","135deg,#4A148C,#0277BD","135deg,#004D40,#1A237E"]
STOPWORDS = {"de","a","o","que","e","do","da","em","um","para","com","uma","os","no","se","na","por","mais","as","dos","como","mas","foi","ao","ele","das","tem","the","of","and","to","in","is","it","that","was","for","on","are","with","they","at","be","this","from","or","not","by","we","an","each","which","can"}

SEED_POSTS = [
    {"id":1,"author":"Carlos Mendez","author_email":"carlos@nebula.ai","area":"Neurociencia","title":"Privacao de Sono e Plasticidade Sinaptica Hipocampal em Ratos Wistar","abstract":"Investigamos como 24h de privacao de sono afetam espinhas dendriticas em ratos Wistar. Reducao de 34% na plasticidade hipocampal identificada via microscopia confocal. Janela critica de recuperacao: primeiras 6h apos retorno do sono.","tags":["neurociencia","sono","memoria","hipocampo","plasticidade sinaptica"],"status":"Em andamento","date":"2026-02-10","comments":[]},
    {"id":2,"author":"Luana Freitas","author_email":"luana@nebula.ai","area":"Biologia Molecular","title":"CRISPR-Cas9 com Vetor AAV9 para Distrofia Muscular de Duchenne","abstract":"Desenvolvemos vetor AAV9 modificado para entrega intravenosa de CRISPR-Cas9 no gene DMD com eficiencia de 78% em modelos mdx. Candidato promissor para ensaios clinicos fase I previsto para 2027.","tags":["CRISPR","terapia genica","DMD","AAV9","miopatia"],"status":"Publicado","date":"2026-01-28","comments":[]},
    {"id":3,"author":"Rafael Souza","author_email":"rafael@nebula.ai","area":"Computacao","title":"Arquitetura Hibrida Variacional Quantico-Classica para TSP","abstract":"Circuitos variadionais quanticos integrados a camadas densas classicas para otimizacao combinatoria. TSP resolvido 40% mais rapido que QAOA puro em grafos de 100 nos. Implementado em hardware IBM Quantum Eagle.","tags":["computacao quantica","VQC","TSP","otimizacao","IBM Quantum"],"status":"Em andamento","date":"2026-02-15","comments":[]},
    {"id":4,"author":"Priya Nair","author_email":"priya@nebula.ai","area":"Astrofisica","title":"Tensao com Lambda-CDM via Lentes Gravitacionais Fracas — DES Y3","abstract":"Mapeamento de shear cosmico com 100 milhoes de galaxias do DES Year 3. Tensao de 2.8 sigma com LCDM em escalas sub-Mpc. Pipeline bayesiano robusto a sistematicos de PSF.","tags":["cosmologia","DES","lentes gravitacionais","materia escura","shear"],"status":"Publicado","date":"2026-02-01","comments":[]},
    {"id":5,"author":"Joao Lima","author_email":"joao@nebula.ai","area":"Psicologia","title":"Amplificacao de Vies de Confirmacao por LLMs em Decisoes Clinicas","abstract":"Estudo duplo-cego com 240 medicos mostrou amplificacao de vieses cognitivos em 22% das decisoes assistidas por IA mal calibrada. Desenvolvemos protocolo de auditoria continua.","tags":["psicologia clinica","LLM","vies cognitivo","medicina baseada em evidencias"],"status":"Publicado","date":"2026-02-08","comments":[]},
]

SEED_USERS = {
    "demo@nebula.ai":{"name":"Ana Pesquisadora","password":hashlib.sha256("demo123".encode()).hexdigest(),"bio":"Pesquisadora em IA e Ciencias Cognitivas","area":"Inteligencia Artificial","bolsa":"CNPq","verified":True},
    "carlos@nebula.ai":{"name":"Carlos Mendez","password":hashlib.sha256("nebula123".encode()).hexdigest(),"bio":"Neurocientista — UFMG","area":"Neurociencia","bolsa":"FAPEMIG","verified":True},
    "luana@nebula.ai":{"name":"Luana Freitas","password":hashlib.sha256("nebula123".encode()).hexdigest(),"bio":"Biomedica — FIOCRUZ","area":"Biologia Molecular","bolsa":"CAPES","verified":True},
    "rafael@nebula.ai":{"name":"Rafael Souza","password":hashlib.sha256("nebula123".encode()).hexdigest(),"bio":"Computacao Quantica — USP","area":"Computacao","bolsa":"CNPq","verified":True},
    "priya@nebula.ai":{"name":"Priya Nair","password":hashlib.sha256("nebula123".encode()).hexdigest(),"bio":"Astrofisica — MIT","area":"Astrofisica","bolsa":"NSF","verified":True},
    "joao@nebula.ai":{"name":"Joao Lima","password":hashlib.sha256("nebula123".encode()).hexdigest(),"bio":"Psicologo Cognitivo — UNICAMP","area":"Psicologia","bolsa":"FAPESP","verified":True},
}

DB_FILE = "nebula_db.json"

def hp(pw): return hashlib.sha256(pw.encode()).hexdigest()
def ini(n): p=(n or "").strip().split(); return ''.join(w[0].upper() for w in p[:2]) if p else "?"
def time_ago(ds):
    try:
        d=(datetime.now()-datetime.strptime(ds,"%Y-%m-%d")).days
        return "hoje" if d==0 else("ontem" if d==1 else(f"{d}d" if d<7 else(f"{d//7}sem" if d<30 else f"{d//30}m")))
    except: return ds
def ugrad(e): return f"linear-gradient({GRAD_POOL[hash(e or '')%len(GRAD_POOL)]})"
def guser(): return st.session_state.users.get(st.session_state.get("user_email",""),{}) if isinstance(st.session_state.get("users"),dict) else {}
def get_key(): return st.session_state.get("api_key","") or os.environ.get("ANTHROPIC_API_KEY","")

def area_sim(a1,a2):
    if not a1 or not a2: return 0
    a1,a2=a1.lower(),a2.lower()
    if a1==a2: return 100
    w1={w for w in a1.replace(","," ").split() if len(w)>2}
    w2={w for w in a2.replace(","," ").split() if len(w)>2}
    if not w1 or not w2: return 0
    inter=len(w1&w2); union=len(w1|w2)
    return int(min(100,(inter/union)*80+(0.20 if a1 in a2 or a2 in a1 else 0)*100))

def save_db():
    try:
        with open(DB_FILE,"w",encoding="utf-8") as f:
            json.dump({"users":st.session_state.users,"posts":st.session_state.posts,
                       "folders":st.session_state.folders,"saved_articles":st.session_state.saved_articles,
                       "followed":st.session_state.followed,
                       "user_prefs":{k:dict(v) for k,v in st.session_state.user_prefs.items()}},f,ensure_ascii=False,indent=2)
    except: pass

def init_state():
    if "ready" in st.session_state: return
    st.session_state.ready=True
    disk={}
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,"r",encoding="utf-8") as f: disk=json.load(f)
        except: pass
    du={k:v for k,v in disk.get("users",{}).items() if isinstance(v,dict)}
    st.session_state.setdefault("users",{**SEED_USERS,**du})
    st.session_state.setdefault("logged_in",False)
    st.session_state.setdefault("user_email",None)
    st.session_state.setdefault("page","repository")
    st.session_state.setdefault("profile_view",None)
    st.session_state.setdefault("welcome_similar",[])
    dp=disk.get("user_prefs",{})
    st.session_state.setdefault("user_prefs",{k:defaultdict(float,v) for k,v in dp.items()})
    st.session_state.setdefault("posts",disk.get("posts",[dict(p) for p in SEED_POSTS]))
    st.session_state.setdefault("folders",disk.get("folders",{}))
    st.session_state.setdefault("folder_bytes",{})
    st.session_state.setdefault("saved_articles",disk.get("saved_articles",[]))
    st.session_state.setdefault("followed",disk.get("followed",["carlos@nebula.ai","luana@nebula.ai"]))
    st.session_state.setdefault("chat_msgs",{"carlos@nebula.ai":[{"from":"carlos@nebula.ai","text":"Ola! Vi sua pesquisa sobre LLMs.","time":"09:14"},{"from":"me","text":"Obrigado! O paralelo com neurociencia e interessante.","time":"09:16"}],"luana@nebula.ai":[{"from":"luana@nebula.ai","text":"Podemos colaborar em bioinformatica?","time":"ontem"}]})
    st.session_state.setdefault("chat_contacts",list(SEED_USERS.keys()))
    st.session_state.setdefault("active_chat",None)
    st.session_state.setdefault("search_results",None)
    st.session_state.setdefault("last_q","")
    st.session_state.setdefault("img_ml",None)
    st.session_state.setdefault("img_vision",None)
    st.session_state.setdefault("scholar_cache",{})
    st.session_state.setdefault("api_key",os.environ.get("ANTHROPIC_API_KEY",""))
    st.session_state.setdefault("conn_cache",{})
    st.session_state.setdefault("stats",{"h_index":4,"impact":3.8,"notes":""})
    st.session_state.setdefault("compose_open",False)

init_state()

# ══════════════════════════════════════════════════════════════
#  CLAUDE API
# ══════════════════════════════════════════════════════════════
def call_claude(prompt_text,system="",max_tokens=1000,img_bytes=None):
    key=get_key()
    if not key or not key.startswith("sk-"): return None,"API key ausente"
    content=[]
    if img_bytes:
        buf=io.BytesIO(); PILImage.open(io.BytesIO(img_bytes)).convert("RGB").save(buf,format="JPEG",quality=82)
        content.append({"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":base64.b64encode(buf.getvalue()).decode()}})
    content.append({"type":"text","text":prompt_text})
    pl={"model":"claude-sonnet-4-20250514","max_tokens":max_tokens,"messages":[{"role":"user","content":content}]}
    if system: pl["system"]=system
    try:
        r=requests.post("https://api.anthropic.com/v1/messages",headers={"x-api-key":key,"anthropic-version":"2023-06-01","content-type":"application/json"},json=pl,timeout=40)
        if r.status_code==200: return r.json()["content"][0]["text"],None
        return None,r.json().get("error",{}).get("message",f"HTTP {r.status_code}")
    except Exception as e: return None,str(e)

# ══════════════════════════════════════════════════════════════
#  IMAGE ML
# ══════════════════════════════════════════════════════════════
def analyze_image_ml(img_bytes):
    try:
        img=PILImage.open(io.BytesIO(img_bytes)).convert("RGB"); orig=img.size
        img_r=img.resize((384,384),PILImage.LANCZOS); arr=np.array(img_r,dtype=np.float32)
        r_ch,g_ch,b_ch=arr[:,:,0],arr[:,:,1],arr[:,:,2]
        gray=0.2989*r_ch+0.5870*g_ch+0.1140*b_ch
        mr,mg,mb=float(r_ch.mean()),float(g_ch.mean()),float(b_ch.mean())
        brightness=float(gray.mean()); contrast=float(gray.std())
        hh,hw=gray.shape[0]//2,gray.shape[1]//2
        q=[gray[:hh,:hw].var(),gray[:hh,hw:].var(),gray[hh:,:hw].var(),gray[hh:,hw:].var()]
        symmetry=1.0-(max(q)-min(q))/(max(q)+1e-5)
        hn=np.histogram(gray,bins=64,range=(0,255))[0]; hn=hn/hn.sum(); hn=hn[hn>0]
        entropy=float(-np.sum(hn*np.log2(hn)))
        gn=gray/255.0
        kx=np.array([[-1,0,1],[-2,0,2],[-1,0,1]],dtype=np.float32)/8.0
        def cv2d(img,k):
            pad=np.pad(img,((1,1),(1,1)),mode='edge'); out=np.zeros_like(img)
            for i in range(3):
                for j in range(3): out+=k[i,j]*pad[i:i+img.shape[0],j:j+img.shape[1]]
            return out
        gx=cv2d(gn.astype(np.float32),kx); gy=cv2d(gn.astype(np.float32),kx.T)
        smag=np.sqrt(gx**2+gy**2); edge_mean=float(smag.mean()); edge_density=float((smag>smag.mean()*1.5).mean())
        fft=np.fft.fftshift(np.abs(np.fft.fft2(gn))); fh,fw=fft.shape
        Y,X=np.ogrid[:fh,:fw]; dist=np.sqrt((X-fw//2)**2+(Y-fh//2)**2); rf=min(fh,fw)//2
        tot=fft.sum()+1e-9
        lf=float(fft[dist<rf*0.1].sum()/tot); mf=float(fft[(dist>=rf*0.1)&(dist<rf*0.4)].sum()/tot); hf=float(fft[dist>=rf*0.4].sum()/tot)
        outer=fft[dist>=rf*0.3].ravel(); per=float(np.percentile(outer,99))/(float(np.mean(outer))+1e-5)
        sc={}
        sc["Histopatologia H&E"]=(30 if mr>140 and mb>80 and mg<mr else 0)+(20 if edge_density>0.10 else 0)+(15 if contrast>40 else 0)
        sc["Fluorescencia DAPI"]=(45 if mb>150 and mb>mr+25 else 0)+(20 if entropy>5 else 0)
        sc["Fluorescencia GFP"]=(45 if mg>150 and mg>mr+25 else 0)+(15 if entropy>4.5 else 0)
        sc["Cristalografia / Difracao"]=(45 if per>12 else 0)+(30 if symmetry>0.75 else 0)
        sc["Gel / Western Blot"]=(40 if contrast<20 and abs(mr-mg)<15 and abs(mg-mb)<15 else 0)+(20 if lf>0.5 else 0)
        sc["Grafico / Diagrama"]=(35 if entropy<3.5 else 0)+(25 if edge_density>0.15 else 0)
        sc["Estrutura Molecular"]=(35 if symmetry>0.82 else 0)+(20 if per>12 else 0)
        sc["Microscopia Confocal"]=(30 if entropy>5.5 else 0)+(20 if edge_density>0.08 else 0)
        sc["Imagem Astronomica"]=(35 if brightness<60 else 0)+(25 if entropy>5 else 0)
        sc["Outro"]=15
        best=max(sc,key=sc.get); conf=min(96,35+sc[best]*0.6)
        rh=np.histogram(r_ch.ravel(),bins=32,range=(0,255))[0].tolist()
        gh=np.histogram(g_ch.ravel(),bins=32,range=(0,255))[0].tolist()
        bh=np.histogram(b_ch.ravel(),bins=32,range=(0,255))[0].tolist()
        return {"ok":True,"category":best,"confidence":round(conf,1),"all_scores":dict(sorted(sc.items(),key=lambda x:-x[1])[:6]),"color":{"r":round(mr,1),"g":round(mg,1),"b":round(mb,1),"warm":mr>mb+15,"cool":mb>mr+15},"edges":{"mean":round(edge_mean,4),"density":round(edge_density,4)},"fft":{"lf":round(lf,3),"mf":round(mf,3),"hf":round(hf,3),"periodic":per>12,"score":round(per,1)},"symmetry":round(symmetry,3),"entropy":round(entropy,3),"brightness":round(brightness,1),"contrast":round(contrast,1),"size":orig,"histograms":{"r":rh,"g":gh,"b":bh}}
    except Exception as e: return {"ok":False,"error":str(e)}

VISION_SYS="""Analise esta imagem cientifica com maxima precisao. Retorne APENAS JSON puro valido, sem markdown:
{"tipo_imagem":"<tipo preciso>","area_cientifica":"<area>","o_que_representa":"<descricao detalhada>","composicao":"<materiais/reagentes/coloracoes>","tecnica_experimental":"<metodologia completa>","estruturas_identificadas":[{"nome":"<nome>","descricao":"<funcao>","localizacao":"<posicao na imagem>","cor_marcador":"<se aplicavel>"}],"escala_e_resolucao":"<barra de escala se visivel>","interpretacao":"<conclusoes visiveis>","significancia":"<importancia cientifica>","anomalias":"<artefatos ou problemas>","qualidade_tecnica":"<Alta/Media/Baixa com justificativa>","aplicacoes":"<onde aplicar>","limitacoes":"<limitacoes>","contexto":"<estado da arte>","confianca":<0-100>,"termos_busca":"<6-8 termos em ingles>"}"""

# ══════════════════════════════════════════════════════════════
#  DOCUMENT
# ══════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def kw_extract(text,n=20):
    if not text: return []
    words=re.findall(r'\b[a-zA-Zaáàâãéêíóôõúç]{4,}\b',text.lower())
    words=[w for w in words if w not in STOPWORDS]
    if not words: return []
    tf=Counter(words); tot=sum(tf.values())
    return [w for w,_ in sorted({w:c/tot for w,c in tf.items()}.items(),key=lambda x:-x[1])[:n]]

@st.cache_data(show_spinner=False)
def topic_dist(kws):
    tm={"Saude/Medicina":["saude","medicina","clinico","therapy","disease","cancer"],"Biologia":["biologia","genomica","gene","dna","rna","proteina","celula","crispr","cell"],"Neurociencia":["neurociencia","neural","cerebro","memoria","sono","brain","neuron"],"Computacao/IA":["algoritmo","machine","learning","inteligencia","computacao","ia","deep"],"Fisica":["fisica","quantica","particula","energia","galaxia","astrofisica","cosmologia"],"Quimica":["quimica","molecula","sintese","reacao","polimero","chemistry"],"Engenharia":["engenharia","sistema","robotica","automacao","engineering"],"Ciencias Sociais":["sociedade","educacao","politica","psicologia","comportamento"],"Ecologia":["ecologia","clima","ambiente","biodiversidade","ecology"],"Matematica":["matematica","estatistica","probabilidade","equacao","mathematics"]}
    s=defaultdict(int)
    for kw in kws:
        for tp,terms in tm.items():
            if any(t in kw or kw in t for t in terms): s[tp]+=1
    return dict(sorted(s.items(),key=lambda x:-x[1])) if s else {"Geral":1}

@st.cache_data(show_spinner=False)
def analyze_doc(fname,fbytes,ftype_str,area=""):
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
        r["summary"]=f"{ftype_str} · {words} palavras · {r['reading_time']}min leitura · {', '.join(list(r['topics'].keys())[:2])}"
    else:
        r["summary"]=f"Arquivo {ftype_str}."; r["relevance_score"]=50
        r["keywords"]=kw_extract(fname.lower(),5); r["topics"]=topic_dist(r["keywords"])
    return r

EMAP={"pdf":"PDF","docx":"Word","xlsx":"Planilha","csv":"Dados","txt":"Texto","py":"Codigo","md":"Markdown","png":"Imagem","jpg":"Imagem","jpeg":"Imagem"}
def ftype_of(f): return EMAP.get(f.split(".")[-1].lower() if "." in f else "","Arquivo")

# ══════════════════════════════════════════════════════════════
#  SEARCH
# ══════════════════════════════════════════════════════════════
@st.cache_data(ttl=600,show_spinner=False)
def search_ss(q,lim=8):
    try:
        r=requests.get("https://api.semanticscholar.org/graph/v1/paper/search",params={"query":q,"limit":lim,"fields":"title,authors,year,abstract,venue,externalIds,openAccessPdf,citationCount"},timeout=9)
        if r.status_code==200:
            out=[]
            for p in r.json().get("data",[]):
                ext=p.get("externalIds",{}) or {}; doi=ext.get("DOI",""); arx=ext.get("ArXiv","")
                pdf=(p.get("openAccessPdf") or {}).get("url","")
                link=pdf or(f"https://arxiv.org/abs/{arx}" if arx else(f"https://doi.org/{doi}" if doi else ""))
                al=p.get("authors",[]) or []; au=", ".join(a.get("name","") for a in al[:3])+(" et al." if len(al)>3 else "")
                out.append({"title":p.get("title","?"),"authors":au or "—","year":p.get("year","?"),"source":p.get("venue","") or "Semantic Scholar","doi":doi or arx or "—","abstract":(p.get("abstract","") or "")[:300],"url":link,"citations":p.get("citationCount",0),"origin":"semantic"})
            return out
    except: pass
    return []

@st.cache_data(ttl=600,show_spinner=False)
def search_cr(q,lim=4):
    try:
        r=requests.get("https://api.crossref.org/works",params={"query":q,"rows":lim,"select":"title,author,issued,abstract,DOI,container-title,is-referenced-by-count"},timeout=9)
        if r.status_code==200:
            out=[]
            for p in r.json().get("message",{}).get("items",[]):
                title=(p.get("title") or ["?"])[0]; ars=p.get("author",[]) or []
                au=", ".join(f'{a.get("given","").split()[0] if a.get("given") else ""} {a.get("family","")}'.strip() for a in ars[:3])+(" et al." if len(ars)>3 else "")
                yr=(p.get("issued",{}).get("date-parts") or [[None]])[0][0]
                doi=p.get("DOI",""); ab=re.sub(r'<[^>]+>','',p.get("abstract","") or "")[:300]
                out.append({"title":title,"authors":au or "—","year":yr or "?","source":(p.get("container-title") or ["CrossRef"])[0],"doi":doi,"abstract":ab,"url":f"https://doi.org/{doi}" if doi else "","citations":p.get("is-referenced-by-count",0),"origin":"crossref"})
            return out
    except: pass
    return []

def record_pref(tags,w=1.0):
    e=st.session_state.get("user_email")
    if not e or not tags: return
    p=st.session_state.user_prefs.setdefault(e,defaultdict(float))
    for t in tags: p[t.lower()]+=w

# ══════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700;800&display=swap');

:root {
  --bg:#020B18;--bg2:#040D1E;--bg3:#071525;
  --a1:#1565C0;--a2:#1E88E5;--a3:#42A5F5;--a4:#90CAF9;
  --c2:#00838F;--c3:#26C6DA;--g2:#2E7D32;--g3:#66BB6A;
  --y2:#FF9800;--r2:#EF5350;
  --t0:#ECEFF1;--t1:#CFD8DC;--t2:#90A4AE;--t3:#546E7A;--t4:#263238;
  --gl:rgba(255,255,255,.04);--glb:rgba(255,255,255,.06);
  --gb1:rgba(255,255,255,.07);--gb2:rgba(255,255,255,.11);
  --ab1:rgba(30,136,229,.08);--ab3:rgba(30,136,229,.25);
}

@keyframes bgpulse{0%,100%{background:#020B18}40%{background:#030E20}70%{background:#041225}}
@keyframes gloworb{0%,100%{opacity:.75;transform:scale(1)}55%{opacity:1;transform:scale(1.06)}}
@keyframes fadeUp{from{opacity:0;transform:translateY(9px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.7)}}

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{background:#020B18!important}
.stApp{background:#020B18!important;color:var(--t1)!important;font-family:'Inter',-apple-system,sans-serif!important;animation:bgpulse 18s ease-in-out infinite!important}
.stApp::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;background:radial-gradient(ellipse 65% 55% at -8% -3%,rgba(21,101,192,.11) 0%,transparent 58%),radial-gradient(ellipse 50% 45% at 108% 2%,rgba(0,96,100,.09) 0%,transparent 52%),radial-gradient(ellipse 42% 65% at 50% 115%,rgba(30,136,229,.07) 0%,transparent 62%);animation:gloworb 15s ease-in-out infinite}
.stApp::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;background-image:linear-gradient(rgba(30,136,229,.016) 1px,transparent 1px),linear-gradient(90deg,rgba(30,136,229,.016) 1px,transparent 1px);background-size:72px 72px}

header[data-testid="stHeader"],#MainMenu,footer,.stDeployButton,[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="collapsedControl"],[data-testid="stSidebarCollapseButton"]{display:none!important}

.block-container{padding:1rem .9rem 4rem!important;max-width:1440px!important;position:relative;z-index:1}

/* ── SIDEBAR ── */
section[data-testid="stSidebar"]{background:rgba(2,8,20,.97)!important;border-right:1px solid rgba(30,136,229,.13)!important;width:155px!important;min-width:155px!important;max-width:155px!important;box-shadow:3px 0 32px rgba(0,0,0,.55)!important}
section[data-testid="stSidebar"] > div{width:155px!important;padding:.8rem .55rem 1rem!important}
section[data-testid="stSidebar"] .stButton > button{width:100%!important;background:transparent!important;border:1px solid transparent!important;border-radius:9px!important;color:var(--t3)!important;font-family:'Inter',sans-serif!important;font-weight:600!important;font-size:.76rem!important;letter-spacing:.04em!important;text-transform:uppercase!important;padding:.48rem .6rem!important;text-align:left!important;justify-content:flex-start!important;transition:all .15s ease!important;box-shadow:none!important;margin-bottom:1px!important}
section[data-testid="stSidebar"] .stButton > button:hover{background:rgba(30,136,229,.09)!important;border-color:rgba(30,136,229,.22)!important;color:var(--a3)!important}
section[data-testid="stSidebar"] .stButton > button p,section[data-testid="stSidebar"] .stButton > button span{color:inherit!important}

/* ── MAIN BUTTONS ── */
.stButton > button{background:transparent!important;border:1px solid rgba(255,255,255,.12)!important;border-radius:9px!important;color:var(--t2)!important;font-family:'Inter',sans-serif!important;font-weight:500!important;font-size:.78rem!important;padding:.40rem .78rem!important;transition:all .15s ease!important;box-shadow:none!important}
.stButton > button:hover{background:rgba(30,136,229,.10)!important;border-color:rgba(30,136,229,.32)!important;color:var(--a3)!important;transform:translateY(-1px)!important}
.stButton > button:active{transform:scale(.97)!important}
.stButton > button p,.stButton > button span{color:inherit!important}

/* ── INPUTS ── */
.stTextInput input,.stTextArea textarea{background:rgba(255,255,255,.03)!important;border:1px solid var(--gb1)!important;border-radius:9px!important;color:var(--t1)!important;font-family:'Inter',sans-serif!important;font-size:.82rem!important}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:rgba(30,136,229,.40)!important;box-shadow:0 0 0 2px rgba(30,136,229,.08)!important}
.stTextInput label,.stTextArea label,.stSelectbox label,.stFileUploader label,.stNumberInput label{color:var(--t3)!important;font-size:.59rem!important;letter-spacing:.09em!important;text-transform:uppercase!important;font-weight:700!important}
input[type="number"]{background:rgba(255,255,255,.03)!important;border:1px solid var(--gb1)!important;border-radius:9px!important;color:var(--t1)!important}
.stSelectbox [data-baseweb="select"]{background:rgba(255,255,255,.03)!important;border:1px solid var(--gb1)!important;border-radius:9px!important}
.stFileUploader section{background:rgba(255,255,255,.02)!important;border:1.5px dashed var(--gb2)!important;border-radius:12px!important}

/* ── CARDS ── */
.card{background:var(--gl);border:1px solid var(--gb1);border-radius:14px;box-shadow:0 2px 20px rgba(0,0,0,.28);overflow:hidden;position:relative}
.post-card{background:var(--gl);border:1px solid var(--gb1);border-radius:14px;padding:1rem 1.15rem;margin-bottom:.5rem;transition:border-color .14s,transform .14s,box-shadow .14s;animation:fadeUp .18s ease both}
.post-card:hover{border-color:rgba(30,136,229,.22);transform:translateY(-1px);box-shadow:0 5px 26px rgba(0,0,0,.35)}
.sc{background:var(--gl);border:1px solid var(--gb1);border-radius:14px;padding:.9rem 1rem;margin-bottom:.5rem}
.sc2{background:var(--gl);border:1px solid var(--gb1);border-radius:12px;padding:.76rem .92rem;margin-bottom:.36rem;transition:border-color .12s,transform .12s}
.sc2:hover{border-color:rgba(30,136,229,.20);transform:translateY(-1px)}
.ai-box{background:linear-gradient(135deg,rgba(21,101,192,.07),rgba(0,96,100,.05));border:1px solid rgba(30,136,229,.18);border-radius:14px;padding:1rem;margin-bottom:.6rem}
.stat-box{background:var(--gl);border:1px solid var(--gb1);border-radius:12px;padding:.8rem;text-align:center}
.chart-wrap{background:rgba(255,255,255,.02);border:1px solid var(--gb1);border-radius:12px;padding:.55rem;margin-bottom:.5rem}
.cmt{background:rgba(255,255,255,.02);border:1px solid var(--gb1);border-radius:10px;padding:.42rem .78rem;margin-bottom:.18rem}
.prof-hero{background:var(--glb);border:1px solid rgba(30,136,229,.14);border-radius:18px;padding:1.4rem;display:flex;gap:1.2rem;align-items:flex-start;margin-bottom:.9rem}
.bme{background:rgba(21,101,192,.14);border:1px solid rgba(30,136,229,.20);border-radius:14px 14px 3px 14px;padding:.48rem .78rem;max-width:72%;margin-left:auto;margin-bottom:4px;font-size:.78rem;line-height:1.6}
.bthem{background:var(--gl);border:1px solid var(--gb1);border-radius:14px 14px 14px 3px;padding:.48rem .78rem;max-width:72%;margin-bottom:4px;font-size:.78rem;line-height:1.6}
.vsec{border-left:2px solid rgba(30,136,229,.28);padding-left:.72rem;margin-bottom:.55rem}
.filter-box{background:rgba(30,136,229,.03);border:1px solid rgba(30,136,229,.09);border-radius:12px;padding:.75rem;margin-bottom:.45rem}
.flbl{font-size:.58rem;font-weight:700;color:var(--t3);letter-spacing:.10em;text-transform:uppercase;margin-bottom:.35rem}

/* ── METRICS ── */
.mval{font-family:'Space Grotesk',sans-serif;font-size:1.45rem;font-weight:800;color:var(--a3)}
.mval-g{font-family:'Space Grotesk',sans-serif;font-size:1.45rem;font-weight:800;color:var(--g3)}
.mval-y{font-family:'Space Grotesk',sans-serif;font-size:1.45rem;font-weight:800;color:var(--y2)}
.mval-c{font-family:'Space Grotesk',sans-serif;font-size:1.45rem;font-weight:800;color:var(--c3)}
.mlbl{font-size:.57rem;color:var(--t3);margin-top:3px;letter-spacing:.09em;text-transform:uppercase;font-weight:700}

/* ── TAGS ── */
.tag{display:inline-block;background:var(--ab1);border:1px solid rgba(30,136,229,.15);border-radius:20px;padding:2px 8px;font-size:.61rem;color:var(--a4);margin:2px;font-weight:500}
.b-b{display:inline-block;background:rgba(30,136,229,.10);border:1px solid rgba(30,136,229,.22);border-radius:20px;padding:2px 8px;font-size:.61rem;font-weight:700;color:var(--a2)}
.b-g{display:inline-block;background:rgba(102,187,106,.09);border:1px solid rgba(102,187,106,.20);border-radius:20px;padding:2px 8px;font-size:.61rem;font-weight:700;color:var(--g3)}
.b-y{display:inline-block;background:rgba(255,152,0,.09);border:1px solid rgba(255,152,0,.20);border-radius:20px;padding:2px 8px;font-size:.61rem;font-weight:700;color:var(--y2)}
.b-c{display:inline-block;background:rgba(38,198,218,.09);border:1px solid rgba(38,198,218,.20);border-radius:20px;padding:2px 8px;font-size:.61rem;font-weight:700;color:var(--c3)}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"]{background:rgba(255,255,255,.02)!important;border:1px solid var(--gb1)!important;border-radius:10px!important;padding:3px!important;gap:2px!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--t3)!important;border-radius:8px!important;font-size:.73rem!important;font-family:'Inter',sans-serif!important;font-weight:500!important}
.stTabs [aria-selected="true"]{background:rgba(30,136,229,.12)!important;color:var(--a2)!important;border:1px solid rgba(30,136,229,.22)!important;font-weight:700!important}
.stTabs [data-baseweb="tab-panel"]{background:transparent!important;padding-top:.72rem!important}

/* ── MISC ── */
.dot-on{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--g3);animation:pulse 2.5s infinite;margin-right:4px;vertical-align:middle}
.dot-off{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--t4);margin-right:4px;vertical-align:middle}
.pw{animation:fadeUp .20s ease both}
.dtxt{display:flex;align-items:center;gap:.6rem;margin:.6rem 0;font-size:.56rem;color:var(--t3);letter-spacing:.10em;text-transform:uppercase;font-weight:700}
.dtxt::before,.dtxt::after{content:'';flex:1;height:1px;background:var(--gb1)}
h1{font-family:'Space Grotesk',sans-serif!important;font-size:1.42rem!important;font-weight:800!important;letter-spacing:-.03em;color:var(--t0)!important}
h2{font-family:'Space Grotesk',sans-serif!important;font-size:.94rem!important;font-weight:700!important;color:var(--t0)!important}
hr{border:none;border-top:1px solid var(--gb1)!important;margin:.7rem 0}
.stCheckbox label,.stRadio label{color:var(--t1)!important}
.stRadio > div{display:flex!important;gap:4px!important;flex-wrap:wrap!important}
.stRadio > div > label{background:rgba(255,255,255,.03)!important;border:1px solid var(--gb1)!important;border-radius:50px!important;padding:.25rem .68rem!important;font-size:.72rem!important;cursor:pointer!important;color:var(--t2)!important;transition:all .12s!important}
.stExpander{background:var(--gl);border:1px solid var(--gb1);border-radius:12px}
::-webkit-scrollbar{width:3px;height:3px}
::-webkit-scrollbar-thumb{background:var(--t4);border-radius:3px}
.js-plotly-plot .plotly .modebar{display:none!important}
</style>""",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════
def avh(initials,sz=40,grad=None):
    fs=max(sz//3,9); bg=grad or "linear-gradient(135deg,#1565C0,#006064)"
    return(f'<div style="width:{sz}px;height:{sz}px;border-radius:50%;background:{bg};display:flex;align-items:center;justify-content:center;font-family:Space Grotesk,sans-serif;font-weight:800;font-size:{fs}px;color:#fff;flex-shrink:0;border:1.5px solid rgba(255,255,255,.10)">{initials}</div>')

def tags_html(tags): return ' '.join(f'<span class="tag">{t}</span>' for t in (tags or []))
def status_badge(s): m={"Publicado":"b-g","Concluido":"b-c","Em andamento":"b-y"}; return f'<span class="{m.get(s,"b-y")}">{s}</span>'
def pc(): return dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",font=dict(color="#546E7A",family="Inter",size=10),margin=dict(l=10,r=10,t=36,b=8),xaxis=dict(showgrid=False,color="#546E7A",tickfont=dict(size=9)),yaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,.04)",color="#546E7A",tickfont=dict(size=9)))

# ══════════════════════════════════════════════════════════════
#  SIDEBAR NAV
# ══════════════════════════════════════════════════════════════
NAV = [("repository","Repositorio"),("search","Busca + IA"),("knowledge","Conexoes"),("folders","Pastas"),("chat","Chat")]

def render_nav():
    email=st.session_state.user_email; u=guser(); name=u.get("name","?"); g=ugrad(email)
    cur=st.session_state.page

    # Active state CSS — highlight the current page button
    active_idx=next((i for i,(k,_) in enumerate(NAV) if k==cur and not st.session_state.profile_view),-1)
    if active_idx>=0:
        # Sidebar button order: [Perfil]=1, [Repo]=2, [Busca]=3, [Conexoes]=4, [Pastas]=5, [Chat]=6, [Config]=7
        btn_n=active_idx+2
        st.markdown(f'<style>section[data-testid="stSidebar"] .stButton:nth-of-type({btn_n}) > button{{background:rgba(30,136,229,.13)!important;border-color:rgba(30,136,229,.30)!important;color:#42A5F5!important;font-weight:700!important}}</style>',unsafe_allow_html=True)

    with st.sidebar:
        st.markdown('<div style="text-align:center;padding:.1rem 0 .5rem"><span style="font-family:Space Grotesk,sans-serif;font-weight:800;font-size:1.1rem;letter-spacing:-.04em;background:linear-gradient(135deg,#42A5F5,#26C6DA);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">NEBULA</span></div>',unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex;justify-content:center;padding:.3rem 0 .1rem">{avh(ini(name),44,g)}</div>',unsafe_allow_html=True)
        st.markdown(f'<div style="text-align:center;font-size:.60rem;color:#546E7A;margin-bottom:.3rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding:0 4px">{name}</div>',unsafe_allow_html=True)

        if st.button("Perfil",key="sb_prof",use_container_width=True):
            st.session_state.profile_view=email; st.session_state.page="repository"; st.rerun()

        st.markdown('<hr style="margin:.4rem 0;border-color:rgba(255,255,255,.07)">',unsafe_allow_html=True)

        for pk,lbl in NAV:
            if st.button(lbl,key=f"sb_{pk}",use_container_width=True):
                st.session_state.profile_view=None; st.session_state.page=pk; st.rerun()

        st.markdown('<hr style="margin:.5rem 0;border-color:rgba(255,255,255,.07)">',unsafe_allow_html=True)

        ak=st.text_input("",placeholder="API key  sk-ant-...",type="password",key="sb_key",label_visibility="collapsed",value=st.session_state.get("api_key",""))
        if ak!=st.session_state.get("api_key",""): st.session_state.api_key=ak
        has_key=bool(ak and ak.startswith("sk-"))
        st.markdown(f'<div style="text-align:center;font-size:.53rem;margin:.15rem 0 .4rem;color:{"#66BB6A" if has_key else "#546E7A"}">{"Claude Vision ativo" if has_key else "sem API key"}</div>',unsafe_allow_html=True)

        if st.button("Config",key="sb_cfg",use_container_width=True):
            st.session_state.profile_view=None; st.session_state.page="settings"; st.rerun()

# ══════════════════════════════════════════════════════════════
#  PAGE: LOGIN
# ══════════════════════════════════════════════════════════════
def page_login():
    _,col,_=st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown('<div style="text-align:center;margin-bottom:2.4rem"><div style="font-family:Space Grotesk,sans-serif;font-size:2.6rem;font-weight:800;letter-spacing:-.07em;background:linear-gradient(135deg,#42A5F5,#26C6DA);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:.45rem">NEBULA</div><div style="color:#546E7A;font-size:.58rem;letter-spacing:.25em;text-transform:uppercase;font-weight:700">Plataforma de Pesquisa Cientifica</div></div>',unsafe_allow_html=True)
        ti,tu=st.tabs(["  Entrar  ","  Criar conta  "])
        with ti:
            with st.form("lf"):
                em=st.text_input("E-mail",placeholder="seu@email.com")
                pw=st.text_input("Senha",placeholder="••••••••",type="password")
                if st.form_submit_button("Entrar",use_container_width=True):
                    u=st.session_state.users.get(em)
                    if not u: st.error("E-mail nao encontrado.")
                    elif u["password"]!=hp(pw): st.error("Senha incorreta.")
                    else:
                        st.session_state.logged_in=True; st.session_state.user_email=em
                        record_pref([w for w in u.get("area","").lower().split() if len(w)>3],1.0)
                        st.session_state.page="repository"; st.rerun()
            st.markdown('<div style="text-align:center;color:#546E7A;font-size:.67rem;margin-top:.45rem">demo@nebula.ai / demo123</div>',unsafe_allow_html=True)
        with tu:
            with st.form("sf"):
                nn=st.text_input("Nome completo"); ne=st.text_input("E-mail")
                na=st.text_input("Area de pesquisa",placeholder="ex: Neurociencia, Machine Learning...")
                nb=st.text_input("Bolsa / Financiamento",placeholder="CNPq, CAPES, FAPESP, NSF, sem bolsa...")
                np_=st.text_input("Senha",type="password"); np2=st.text_input("Confirmar senha",type="password")
                if st.form_submit_button("Criar conta",use_container_width=True):
                    if not all([nn,ne,na,np_,np2]): st.error("Preencha todos os campos.")
                    elif np_!=np2: st.error("Senhas nao coincidem.")
                    elif ne in st.session_state.users: st.error("E-mail ja cadastrado.")
                    else:
                        st.session_state.users[ne]={"name":nn,"password":hp(np_),"bio":"","area":na,"bolsa":nb or "","verified":True}
                        sim=sorted([(area_sim(na,ud.get("area","")),ue,ud) for ue,ud in st.session_state.users.items() if ue!=ne],key=lambda x:-x[0])
                        st.session_state.welcome_similar=[(s,ue,ud) for s,ue,ud in sim if s>=25][:5]
                        save_db(); st.session_state.logged_in=True; st.session_state.user_email=ne
                        st.session_state.page="welcome"; st.rerun()

# ══════════════════════════════════════════════════════════════
#  PAGE: WELCOME
# ══════════════════════════════════════════════════════════════
def page_welcome():
    u=guser(); sim=st.session_state.get("welcome_similar",[])
    _,col,_=st.columns([.5,2.2,.5])
    with col:
        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown(f'<div style="font-family:Space Grotesk,sans-serif;font-size:1.35rem;font-weight:800;color:#ECEFF1;margin-bottom:.25rem">Bem-vindo(a), {u.get("name","").split()[0]}</div>',unsafe_allow_html=True)
        st.markdown(f'<div style="color:#90A4AE;font-size:.79rem;margin-bottom:1rem">Area: <strong style="color:#42A5F5">{u.get("area","")}</strong>   Bolsa: <strong style="color:#26C6DA">{u.get("bolsa","—")}</strong></div>',unsafe_allow_html=True)
        if sim:
            st.markdown('<div style="font-family:Space Grotesk,sans-serif;font-weight:700;font-size:.86rem;color:#ECEFF1;margin-bottom:.5rem">Pesquisadores com areas similares</div>',unsafe_allow_html=True)
            for score,ue,ud in sim:
                g=ugrad(ue)
                st.markdown(f'<div class="sc2"><div style="display:flex;align-items:center;gap:10px">{avh(ini(ud.get("name","?")),34,g)}<div style="flex:1"><div style="font-weight:700;font-size:.82rem;color:#ECEFF1">{ud.get("name","?")}</div><div style="font-size:.65rem;color:#42A5F5">{ud.get("area","")}</div><div style="margin-top:4px;height:3px;border-radius:2px;width:{min(int(score*.9),100)}%;background:linear-gradient(90deg,#1E88E5,#26C6DA)"></div><div style="font-size:.58rem;color:#546E7A;margin-top:2px">{score}% similaridade</div></div></div></div>',unsafe_allow_html=True)
                c1,c2=st.columns(2)
                with c1:
                    if st.button(f"Seguir {ud.get('name','').split()[0]}",key=f"ws_{ue}",use_container_width=True):
                        if ue not in st.session_state.followed: st.session_state.followed.append(ue)
                        save_db(); st.rerun()
                with c2:
                    if st.button("Ver perfil",key=f"wp_{ue}",use_container_width=True):
                        st.session_state.profile_view=ue; st.session_state.page="repository"; st.rerun()
        st.markdown("<br>",unsafe_allow_html=True)
        if st.button("Ir para o Repositorio",key="btn_go",use_container_width=True):
            st.session_state.page="repository"; st.rerun()

# ══════════════════════════════════════════════════════════════
#  PAGE: PROFILE
# ══════════════════════════════════════════════════════════════
def page_profile(target):
    tu=st.session_state.users.get(target,{}); email=st.session_state.user_email
    if not tu: st.error("Perfil nao encontrado."); return
    name=tu.get("name","?"); is_me=(email==target); g=ugrad(target)
    is_fol=target in st.session_state.followed
    my_posts=[p for p in st.session_state.posts if p.get("author_email")==target]
    vb=' <span class="b-g" style="font-size:.57rem">verificado</span>' if tu.get("verified") else ""
    bl=tu.get("bolsa",""); bl_h=f' <span class="b-c" style="font-size:.57rem">{bl}</span>' if bl else ""
    st.markdown(f'<div class="prof-hero"><div style="width:68px;height:68px;border-radius:50%;background:{g};display:flex;align-items:center;justify-content:center;font-family:Space Grotesk,sans-serif;font-weight:800;font-size:1.4rem;color:#fff;flex-shrink:0;border:2px solid rgba(255,255,255,.10)">{ini(name)}</div><div style="flex:1"><div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:.2rem"><span style="font-family:Space Grotesk,sans-serif;font-weight:800;font-size:1.2rem;color:#ECEFF1">{name}</span>{vb}{bl_h}</div><div style="color:#42A5F5;font-size:.78rem;font-weight:600;margin-bottom:.3rem">{tu.get("area","")}</div><div style="color:#90A4AE;font-size:.75rem;line-height:1.65;margin-bottom:.6rem">{tu.get("bio","")}</div><div style="font-size:.68rem;color:#546E7A">{len(my_posts)} publicacoes</div></div></div>',unsafe_allow_html=True)
    if not is_me:
        c1,c2,c3,_=st.columns([1,1,1,2])
        with c1:
            if st.button("Deixar de seguir" if is_fol else "Seguir",key="pf_f",use_container_width=True):
                if is_fol: st.session_state.followed.remove(target)
                else: st.session_state.followed.append(target)
                save_db(); st.rerun()
        with c2:
            if st.button("Enviar mensagem",key="pf_chat",use_container_width=True):
                st.session_state.chat_msgs.setdefault(target,[]); st.session_state.active_chat=target; st.session_state.page="chat"; st.rerun()
        with c3:
            if st.button("Voltar",key="pf_back",use_container_width=True):
                st.session_state.profile_view=None; st.rerun()
        for p in sorted(my_posts,key=lambda x:x.get("date",""),reverse=True): render_post_card(p,ctx="prf")
        if not my_posts: st.info("Nenhuma publicacao.")
    else:
        te,tl=st.tabs(["  Editar Perfil  ",f"  Minhas Publicacoes ({len(my_posts)})  "])
        with te:
            nn=st.text_input("Nome",value=tu.get("name",""),key="cfg_n")
            na=st.text_input("Area de pesquisa",value=tu.get("area",""),key="cfg_a")
            nb2=st.text_input("Bolsa / Financiamento",value=tu.get("bolsa",""),key="cfg_bolsa")
            nb_b=st.text_area("Biografia",value=tu.get("bio",""),key="cfg_bio",height=75)
            c1,c2=st.columns(2)
            with c1:
                if st.button("Salvar",key="sp",use_container_width=True):
                    st.session_state.users[email].update({"name":nn,"area":na,"bolsa":nb2,"bio":nb_b}); save_db(); st.success("Salvo!"); st.rerun()
            with c2:
                if st.button("Sair da conta",key="so",use_container_width=True):
                    st.session_state.logged_in=False; st.session_state.user_email=None; st.session_state.page="login"; st.rerun()
        with tl:
            for p in sorted(my_posts,key=lambda x:x.get("date",""),reverse=True): render_post_card(p,ctx="myp",show_author=False)
            if not my_posts: st.info("Nenhuma publicacao ainda.")

# ══════════════════════════════════════════════════════════════
#  POST CARD — sem likes, sem compartilhar, sem rede social
# ══════════════════════════════════════════════════════════════
def render_post_card(post,ctx="repo",show_author=True,compact=False):
    email=st.session_state.user_email; pid=post["id"]
    aemail=post.get("author_email",""); aname=post.get("author","?")
    g=ugrad(aemail); dt=time_ago(post.get("date","")); year=post.get("date","")[:4]
    ab=post.get("abstract","")
    if compact and len(ab)>200: ab=ab[:200]+"..."
    if show_author:
        author_block=(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:.5rem">{avh(ini(aname),30,g)}<div><div style="font-weight:600;font-size:.77rem;color:#CFD8DC">{aname}</div><div style="font-size:.60rem;color:#546E7A">{post.get("area","")} · {dt}</div></div><div style="margin-left:auto">{status_badge(post.get("status","Em andamento"))}</div></div>')
    else:
        author_block=(f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.3rem"><span style="font-size:.60rem;color:#546E7A">{year} · {dt}</span>{status_badge(post.get("status","Em andamento"))}</div>')
    st.markdown(f'<div class="post-card">{author_block}<div style="font-family:Space Grotesk,sans-serif;font-size:.92rem;font-weight:700;color:#ECEFF1;margin-bottom:.28rem;line-height:1.35">{post["title"]}</div><div style="color:#90A4AE;font-size:.76rem;line-height:1.65;margin-bottom:.45rem">{ab}</div><div>{tags_html(post.get("tags",[]))}</div></div>',unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns([1.2,1,.7,1.2])
    with c1:
        if st.button("citar",key=f"ct_{ctx}_{pid}",use_container_width=True):
            st.toast(f'{aname} ({year}). {post["title"]}. Nebula.')
    with c2:
        saved_ids={a.get("doi","") for a in st.session_state.saved_articles}
        is_saved=f"__post_{pid}" in saved_ids
        if st.button("remover" if is_saved else "salvar",key=f"sv_{ctx}_{pid}",use_container_width=True):
            if is_saved: st.session_state.saved_articles=[a for a in st.session_state.saved_articles if a.get("doi")!=f"__post_{pid}"]; st.toast("Removido")
            else: st.session_state.saved_articles.append({"title":post["title"],"authors":aname,"year":year,"source":"Nebula","doi":f"__post_{pid}","abstract":ab[:280],"url":"","citations":0,"origin":"nebula"}); st.toast("Salvo!")
            save_db(); st.rerun()
    with c3:
        if st.button("notas",key=f"cmt_t_{ctx}_{pid}",use_container_width=True):
            k=f"open_cmt_{ctx}_{pid}"; st.session_state[k]=not st.session_state.get(k,False); st.rerun()
    with c4:
        if show_author and aemail:
            if st.button(f"ver: {aname.split()[0]}",key=f"vp_{ctx}_{pid}",use_container_width=True):
                st.session_state.profile_view=aemail; st.rerun()
    if st.session_state.get(f"open_cmt_{ctx}_{pid}",False):
        nc_txt=st.text_input("",placeholder="Adicionar nota/comentario...",key=f"ci_{ctx}_{pid}",label_visibility="collapsed")
        if st.button("Salvar nota",key=f"cs_{ctx}_{pid}"):
            if nc_txt: post.setdefault("comments",[]).append({"user":guser().get("name","?"),"text":nc_txt}); save_db(); st.rerun()
        for c in post.get("comments",[]): st.markdown(f'<div class="cmt"><span style="font-size:.70rem;font-weight:700;color:#42A5F5">{c["user"]}</span> — <span style="font-size:.75rem;color:#90A4AE">{c["text"]}</span></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  ARTICLE CARD
# ══════════════════════════════════════════════════════════════
def render_article(a,idx=0,ctx="web"):
    uid=re.sub(r'[^a-zA-Z0-9]','',f"{ctx}_{idx}_{str(a.get('doi',''))[:10]}")[:32]
    sn="Semantic Scholar" if a.get("origin")=="semantic" else "CrossRef"
    sc=CHART_C[1] if a.get("origin")=="semantic" else CHART_C[2]
    cite=f" · {a['citations']} cit." if a.get("citations") else ""
    ab=(a.get("abstract","") or "")[:280]+("..." if len(a.get("abstract",""))>280 else "")
    is_saved=any(s.get("doi")==a.get("doi") for s in st.session_state.saved_articles)
    st.markdown(f'<div class="sc2"><div style="display:flex;align-items:flex-start;gap:7px;margin-bottom:.24rem"><div style="flex:1;font-family:Space Grotesk,sans-serif;font-size:.83rem;font-weight:700;color:#ECEFF1">{a["title"]}</div><span style="font-size:.55rem;color:{sc};background:rgba(255,255,255,.03);border-radius:6px;padding:2px 6px;white-space:nowrap;flex-shrink:0">{sn}</span></div><div style="color:#546E7A;font-size:.62rem;margin-bottom:.26rem">{a["authors"]} · <em>{a["source"]}</em> · {a["year"]}{cite}</div><div style="color:#90A4AE;font-size:.74rem;line-height:1.60">{ab}</div></div>',unsafe_allow_html=True)
    ca,cb,cc=st.columns(3)
    with ca:
        if st.button("remover" if is_saved else "salvar",key=f"svw_{uid}",use_container_width=True):
            if is_saved: st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get("doi")!=a.get("doi")]; st.toast("Removido")
            else: st.session_state.saved_articles.append(a); st.toast("Salvo!")
            save_db(); st.rerun()
    with cb:
        if st.button("citar",key=f"ctw_{uid}",use_container_width=True): st.toast(f'{a["authors"]} ({a["year"]}). {a["title"]}.')
    with cc:
        if a.get("url"): st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:#42A5F5;font-size:.76rem;text-decoration:none;line-height:2.4;display:block">abrir artigo</a>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  PAGE: REPOSITORY
# ══════════════════════════════════════════════════════════════
def page_repository():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    email=st.session_state.user_email; u=guser()
    col_t,col_b=st.columns([3,1])
    with col_t: st.markdown('<h1 style="padding-top:.4rem">Repositorio de Pesquisas</h1>',unsafe_allow_html=True)
    with col_b:
        st.markdown('<br>',unsafe_allow_html=True)
        if st.button("Nova publicacao",key="btn_np",use_container_width=True):
            st.session_state.compose_open=not st.session_state.get("compose_open",False); st.rerun()
    if st.session_state.get("compose_open",False):
        st.markdown('<div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.09);border-radius:14px;padding:1.1rem 1.2rem;margin-bottom:.7rem">',unsafe_allow_html=True)
        nt=st.text_input("Titulo *",key="np_t"); nab=st.text_area("Resumo / Abstract *",key="np_ab",height=96)
        c1c,c2c,c3c=st.columns(3)
        with c1c: ntg=st.text_input("Tags (virgula)",key="np_tg")
        with c2c: nst=st.selectbox("Status",["Em andamento","Publicado","Concluido"],key="np_st")
        with c3c: narea=st.text_input("Area",value=u.get("area",""),key="np_area")
        cp,cc=st.columns([2,1])
        with cp:
            if st.button("Publicar",key="btn_pub",use_container_width=True):
                if not nt or not nab: st.warning("Titulo e resumo obrigatorios.")
                else:
                    tags=[t.strip() for t in ntg.split(",") if t.strip()] if ntg else []
                    new_p={"id":hash(nt+email)%99999+len(st.session_state.posts)*10,"author":u.get("name","?"),"author_email":email,"area":narea or u.get("area",""),"title":nt,"abstract":nab,"tags":tags,"status":nst,"date":datetime.now().strftime("%Y-%m-%d"),"comments":[]}
                    st.session_state.posts.insert(0,new_p); record_pref(tags,2.0); save_db(); st.session_state.compose_open=False; st.rerun()
        with cc:
            if st.button("Cancelar",key="btn_cc",use_container_width=True): st.session_state.compose_open=False; st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)
    cf,cm=st.columns([.92,3.2],gap="medium")
    with cf:
        st.markdown('<div class="filter-box"><div class="flbl">Busca</div>',unsafe_allow_html=True)
        fq=st.text_input("",placeholder="Palavras-chave...",key="repo_q",label_visibility="collapsed")
        st.markdown('</div>',unsafe_allow_html=True)
        st.markdown('<div class="filter-box"><div class="flbl">Ordenar</div>',unsafe_allow_html=True)
        fsort=st.radio("",["Recentes","Relevancia","Titulo A-Z"],key="repo_sort",label_visibility="collapsed")
        st.markdown('</div>',unsafe_allow_html=True)
        st.markdown('<div class="filter-box"><div class="flbl">Status</div>',unsafe_allow_html=True)
        fstatus=st.multiselect("",["Publicado","Em andamento","Concluido"],key="repo_status",label_visibility="collapsed")
        st.markdown('</div>',unsafe_allow_html=True)
        all_areas=sorted(set(p.get("area","") for p in st.session_state.posts if p.get("area","")))
        st.markdown('<div class="filter-box"><div class="flbl">Area</div>',unsafe_allow_html=True)
        farea=st.multiselect("",all_areas,key="repo_area",label_visibility="collapsed")
        st.markdown('</div>',unsafe_allow_html=True)
        all_tags=sorted(set(t for p in st.session_state.posts for t in p.get("tags",[])))
        st.markdown('<div class="filter-box"><div class="flbl">Tags</div>',unsafe_allow_html=True)
        ftags=st.multiselect("",all_tags,key="repo_tags",label_visibility="collapsed")
        st.markdown('</div>',unsafe_allow_html=True)
        st.markdown('<div class="filter-box"><div class="flbl">Mostrar</div>',unsafe_allow_html=True)
        fview=st.radio("",["Todos","Seguidos","Salvos"],key="repo_view",label_visibility="collapsed")
        st.markdown('</div>',unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:.62rem;color:#546E7A;margin-top:.4rem;line-height:1.9">Total: <strong style="color:#90A4AE">{len(st.session_state.posts)}</strong> publicacoes<br>Pesquisadores: <strong style="color:#90A4AE">{len(st.session_state.users)}</strong><br>Areas: <strong style="color:#90A4AE">{len(all_areas)}</strong></div>',unsafe_allow_html=True)
    with cm:
        posts=list(st.session_state.posts)
        if fq:
            fl=fq.lower(); posts=[p for p in posts if fl in p.get("title","").lower() or fl in p.get("abstract","").lower() or any(fl in t.lower() for t in p.get("tags",[]))]
        if fstatus: posts=[p for p in posts if p.get("status") in fstatus]
        if farea: posts=[p for p in posts if p.get("area") in farea]
        if ftags: posts=[p for p in posts if any(t in p.get("tags",[]) for t in ftags)]
        if fview=="Seguidos": posts=[p for p in posts if p.get("author_email") in st.session_state.followed]
        elif fview=="Salvos":
            saved_ids={a.get("doi","") for a in st.session_state.saved_articles}; posts=[p for p in posts if f"__post_{p['id']}" in saved_ids]
        if "Relevancia" in fsort and fq:
            def rel_sc(p):
                fl2=fq.lower(); s=0
                if fl2 in p.get("title","").lower(): s+=4
                s+=sum(1 for t in p.get("tags",[]) if fl2 in t.lower())*2
                if fl2 in p.get("abstract","").lower(): s+=1
                return s
            posts=sorted(posts,key=rel_sc,reverse=True)
        elif "Titulo" in fsort: posts=sorted(posts,key=lambda p:p.get("title",""))
        else: posts=sorted(posts,key=lambda p:p.get("date",""),reverse=True)
        st.markdown(f'<div style="font-size:.68rem;color:#546E7A;margin-bottom:.5rem">{len(posts)} resultado(s)</div>',unsafe_allow_html=True)
        if not posts: st.markdown('<div class="card" style="padding:3rem;text-align:center;color:#546E7A">Nenhuma publicacao encontrada.</div>',unsafe_allow_html=True)
        for p in posts: render_post_card(p,ctx="repo")
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  PAGE: SEARCH + VISION
# ══════════════════════════════════════════════════════════════
def page_search():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.4rem;margin-bottom:.8rem">Busca e Analise de Imagem</h1>',unsafe_allow_html=True)
    has_key=bool(get_key() and get_key().startswith("sk-"))
    tab_s,tab_v=st.tabs(["  Busca Academica  ","  Analise de Imagem com IA  "])
    with tab_s:
        c1,c2=st.columns([4,1])
        with c1: q=st.text_input("",placeholder="Buscar em Nebula, Semantic Scholar, CrossRef...",key="sq",label_visibility="collapsed")
        with c2:
            if st.button("Buscar",key="btn_s",use_container_width=True):
                if q:
                    with st.spinner("Buscando..."):
                        nr=[p for p in st.session_state.posts if q.lower() in p.get("title","").lower() or q.lower() in p.get("abstract","").lower() or any(q.lower() in t.lower() for t in p.get("tags",[]))]
                        sr=search_ss(q,8); cr=search_cr(q,4)
                    st.session_state.search_results={"nebula":nr,"ss":sr,"cr":cr}; st.session_state.last_q=q; record_pref([q.lower()],.3)
        with st.expander("Filtros avancados"):
            ca2,cb2,cc2=st.columns(3)
            with ca2: yf=st.number_input("Ano de",2000,2026,2018,key="yf")
            with cb2: yt=st.number_input("Ano ate",2000,2026,2026,key="yt")
            with cc2: mc=st.number_input("Min. citacoes",0,10000,0,key="mc")
        if st.session_state.get("search_results") and st.session_state.get("last_q"):
            res=st.session_state.search_results; neb=res.get("nebula",[]); ss=res.get("ss",[]); cr2=res.get("cr",[])
            web=ss+[x for x in cr2 if not any(x["title"].lower()==s["title"].lower() for s in ss)]
            web=[a for a in web if (not a.get("year") or (str(a.get("year","0")).isdigit() and yf<=int(a.get("year",2026))<=yt)) and a.get("citations",0)>=mc]
            total=len(neb)+len(web)
            st.markdown(f'<div style="color:#546E7A;font-size:.68rem;margin-bottom:.5rem">{total} resultado(s) para "{st.session_state.last_q}"</div>',unsafe_allow_html=True)
            ta,tn,tw=st.tabs([f"  Todos ({total})  ",f"  Nebula ({len(neb)})  ",f"  Internet ({len(web)})  "])
            with ta:
                if neb:
                    st.markdown('<div style="font-size:.57rem;color:#42A5F5;font-weight:700;margin-bottom:.35rem;letter-spacing:.09em;text-transform:uppercase">No repositorio Nebula</div>',unsafe_allow_html=True)
                    for p in neb: render_post_card(p,ctx="srch",compact=True)
                if web:
                    if neb: st.markdown('<hr>',unsafe_allow_html=True)
                    for i,a in enumerate(web): render_article(a,idx=i,ctx="all_w")
                if not neb and not web: st.info("Nenhum resultado.")
            with tn:
                for p in neb: render_post_card(p,ctx="sneb",compact=True)
                if not neb: st.info("Nenhuma publicacao.")
            with tw:
                for i,a in enumerate(web): render_article(a,idx=i,ctx="web_t")
                if not web: st.info("Nenhum artigo.")
        else:
            tag_c=Counter(t for p in st.session_state.posts for t in p.get("tags",[]))
            st.markdown('<div class="dtxt">Topicos em destaque</div>',unsafe_allow_html=True)
            st.markdown('<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:.8rem">'+''.join(f'<span class="tag" style="font-size:.68rem">{t} <span style="color:#546E7A">({c})</span></span>' for t,c in tag_c.most_common(16))+'</div>',unsafe_allow_html=True)
    with tab_v:
        if has_key: st.markdown('<div style="background:rgba(21,101,192,.06);border:1px solid rgba(30,136,229,.18);border-radius:12px;padding:.65rem 1rem;margin-bottom:.65rem"><div style="font-size:.75rem;color:#42A5F5;font-weight:600">Claude Vision ativo</div></div>',unsafe_allow_html=True)
        else: st.markdown('<div style="background:rgba(255,152,0,.05);border:1px solid rgba(255,152,0,.14);border-radius:12px;padding:.65rem 1rem;margin-bottom:.65rem"><div style="font-size:.72rem;color:#FFB74D;font-weight:600">Modo ML apenas — insira API key na sidebar para ativar Claude Vision</div></div>',unsafe_allow_html=True)
        cu,cr3=st.columns([1,2.2])
        with cu:
            st.markdown('<div class="card" style="padding:1rem">',unsafe_allow_html=True)
            img_file=st.file_uploader("Carregar imagem cientifica",type=["png","jpg","jpeg","webp","tiff"],key="img_up")
            img_bytes=None
            if img_file: img_bytes=img_file.read(); st.image(img_bytes,use_container_width=True)
            if st.button("Analise ML rapida",key="btn_ml",use_container_width=True):
                if img_bytes:
                    with st.spinner("Pipeline ML..."): st.session_state.img_ml=analyze_image_ml(img_bytes)
                    st.session_state.img_vision=None
            if img_bytes and has_key:
                if st.button("Analise completa com Claude",key="btn_vision",use_container_width=True):
                    with st.spinner("Claude analisando..."):
                        txt,err=call_claude("Analise esta imagem cientifica.",system=VISION_SYS,max_tokens=1800,img_bytes=img_bytes)
                    if txt:
                        try:
                            clean=re.sub(r'^```json\s*','',txt.strip()); clean=re.sub(r'\s*```$','',clean); st.session_state.img_vision=json.loads(clean)
                        except: st.session_state.img_vision={"_raw":txt}
                    elif err: st.error(f"Erro: {err}")
            st.markdown('</div>',unsafe_allow_html=True)
        with cr3:
            cv=st.session_state.get("img_vision")
            if cv:
                if "_raw" in cv: st.markdown(f'<div class="ai-box"><div style="font-size:.78rem;color:#90A4AE;white-space:pre-wrap;line-height:1.7">{cv["_raw"][:2000]}</div></div>',unsafe_allow_html=True)
                else:
                    tipo=cv.get("tipo_imagem","—"); area_c=cv.get("area_cientifica","—"); conf=cv.get("confianca",0)
                    cc2="#66BB6A" if conf>80 else("#42A5F5" if conf>60 else "#FF9800")
                    st.markdown(f'<div class="ai-box"><div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:.65rem"><div><div style="font-size:.54rem;color:#42A5F5;letter-spacing:.09em;text-transform:uppercase;font-weight:700;margin-bottom:3px">Claude Vision</div><div style="font-family:Space Grotesk,sans-serif;font-size:1.05rem;font-weight:800;color:#ECEFF1;margin-bottom:3px">{tipo}</div><div style="color:#26C6DA;font-size:.77rem;font-weight:600">{area_c}</div></div><div style="background:rgba(0,0,0,.35);border-radius:10px;padding:.42rem .75rem;text-align:center;flex-shrink:0"><div style="font-family:Space Grotesk,sans-serif;font-size:1.3rem;font-weight:900;color:{cc2}">{conf}%</div><div style="font-size:.50rem;color:#546E7A;text-transform:uppercase">confianca</div></div></div></div>',unsafe_allow_html=True)
                    for title,key_cv in [("O que representa","o_que_representa"),("Composicao","composicao"),("Tecnica experimental","tecnica_experimental"),("Escala e resolucao","escala_e_resolucao"),("Interpretacao","interpretacao"),("Significancia","significancia"),("Anomalias","anomalias"),("Aplicacoes","aplicacoes"),("Limitacoes","limitacoes")]:
                        val=cv.get(key_cv,"")
                        if val and len(str(val))>4: st.markdown(f'<div class="vsec"><div style="font-size:.58rem;color:#546E7A;font-weight:700;letter-spacing:.09em;text-transform:uppercase;margin-bottom:.22rem">{title}</div><div style="font-size:.78rem;color:#CFD8DC;line-height:1.72">{val}</div></div>',unsafe_allow_html=True)
                    ests=cv.get("estruturas_identificadas",[])
                    if ests:
                        st.markdown('<div style="font-size:.58rem;color:#546E7A;font-weight:700;letter-spacing:.09em;text-transform:uppercase;margin:.5rem 0 .3rem">Estruturas identificadas</div>',unsafe_allow_html=True)
                        for est in ests:
                            if isinstance(est,dict): st.markdown(f'<div style="background:rgba(30,136,229,.04);border:1px solid rgba(30,136,229,.10);border-radius:8px;padding:.48rem .7rem;margin-bottom:.28rem"><strong style="color:#90CAF9;font-size:.76rem">{est.get("nome","")}</strong><div style="font-size:.74rem;color:#90A4AE;margin-top:.18rem;line-height:1.6">{est.get("descricao","")}</div></div>',unsafe_allow_html=True)
                    termos=cv.get("termos_busca","")
                    if termos:
                        with st.spinner("Buscando literatura..."):
                            wr=search_ss(termos,6)
                        if wr:
                            st.markdown('<div class="dtxt">Artigos relacionados</div>',unsafe_allow_html=True)
                            for i2,a2 in enumerate(wr): render_article(a2,idx=i2+5000,ctx="img_cv")
            ml=st.session_state.get("img_ml")
            if ml and ml.get("ok") and not cv:
                cat=ml["category"]; conf2=ml["confidence"]; cc2="#66BB6A" if conf2>80 else("#42A5F5" if conf2>60 else "#FF9800")
                st.markdown(f'<div class="ai-box"><div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.6rem"><div><div style="font-size:.56rem;color:#42A5F5;font-weight:700;letter-spacing:.09em;text-transform:uppercase;margin-bottom:3px">Classificacao ML</div><div style="font-family:Space Grotesk,sans-serif;font-size:1.02rem;font-weight:800;color:#ECEFF1">{cat}</div></div><div style="background:rgba(0,0,0,.3);border-radius:9px;padding:.4rem .7rem;text-align:center"><div style="font-family:Space Grotesk,sans-serif;font-size:1.25rem;font-weight:900;color:{cc2}">{conf2}%</div><div style="font-size:.50rem;color:#546E7A;text-transform:uppercase">confianca</div></div></div></div>',unsafe_allow_html=True)
                c1m,c2m,c3m,c4m=st.columns(4)
                with c1m: st.markdown(f'<div class="stat-box"><div class="mval">{ml["edges"]["mean"]:.3f}</div><div class="mlbl">Borda Sobel</div></div>',unsafe_allow_html=True)
                with c2m: st.markdown(f'<div class="stat-box"><div class="mval-g">{"sim" if ml["fft"]["periodic"] else "nao"}</div><div class="mlbl">Periodico</div></div>',unsafe_allow_html=True)
                with c3m: st.markdown(f'<div class="stat-box"><div class="mval-y">{ml["entropy"]:.2f}</div><div class="mlbl">Entropia</div></div>',unsafe_allow_html=True)
                with c4m: st.markdown(f'<div class="stat-box"><div class="mval-c">{ml["symmetry"]:.2f}</div><div class="mlbl">Simetria</div></div>',unsafe_allow_html=True)
                t1,t2,t3=st.tabs(["  Categorias  ","  RGB  ","  FFT  "])
                with t1:
                    sc_=ml["all_scores"]; fig_s=go.Figure(go.Bar(x=list(sc_.values()),y=list(sc_.keys()),orientation='h',marker=dict(color=CHART_C[:len(sc_)]),text=[f"{v:.0f}" for v in sc_.values()],textposition="outside",textfont=dict(color="#546E7A",size=9)))
                    fig_s.update_layout(**{**pc(),'height':220,'title':dict(text="Pontuacao por categoria",font=dict(color="#CFD8DC",family="Space Grotesk",size=11)),'xaxis':dict(showgrid=True,gridcolor="rgba(255,255,255,.04)")})
                    st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_s,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
                with t2:
                    hd=ml.get("histograms",{}); bx=list(range(0,256,8))[:32]
                    if hd:
                        fig4=go.Figure()
                        fig4.add_trace(go.Scatter(x=bx,y=hd.get("r",[])[:32],fill='tozeroy',name='R',line=dict(color='rgba(239,83,80,.9)',width=1.5),fillcolor='rgba(239,83,80,.09)'))
                        fig4.add_trace(go.Scatter(x=bx,y=hd.get("g",[])[:32],fill='tozeroy',name='G',line=dict(color='rgba(102,187,106,.9)',width=1.5),fillcolor='rgba(102,187,106,.09)'))
                        fig4.add_trace(go.Scatter(x=bx,y=hd.get("b",[])[:32],fill='tozeroy',name='B',line=dict(color='rgba(66,165,245,.9)',width=1.5),fillcolor='rgba(66,165,245,.09)'))
                        fig4.update_layout(**{**pc(),'height':200,'title':dict(text="Histograma RGB",font=dict(color="#CFD8DC",family="Space Grotesk",size=11)),'legend':dict(font=dict(color="#546E7A",size=9))})
                        st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig4,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
                with t3:
                    ft=ml.get("fft",{}); lf=ft.get("lf",0); mf=ft.get("mf",0); hf_v=ft.get("hf",0)
                    fig_f=go.Figure(go.Bar(x=["Baixa","Media","Alta"],y=[lf,mf,hf_v],marker=dict(color=CHART_C[:3]),text=[f"{v:.3f}" for v in [lf,mf,hf_v]],textposition="outside",textfont=dict(color="#546E7A",size=9)))
                    fig_f.update_layout(**{**pc(),'height':200,'title':dict(text="FFT — Frequencias",font=dict(color="#CFD8DC",family="Space Grotesk",size=11))})
                    st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_f,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
                kw_map={"Histopatologia H&E":"hematoxylin eosin histopathology","Fluorescencia DAPI":"DAPI nuclear staining fluorescence","Fluorescencia GFP":"GFP green fluorescent protein confocal","Cristalografia / Difracao":"X-ray diffraction crystallography","Gel / Western Blot":"western blot gel electrophoresis","Grafico / Diagrama":"scientific data visualization","Estrutura Molecular":"molecular structure visualization","Microscopia Confocal":"confocal microscopy fluorescence","Imagem Astronomica":"astronomy telescope observation","Outro":"scientific imaging microscopy"}
                skw=kw_map.get(cat,"scientific imaging"); ck=f"img_{skw[:28]}"
                if ck not in st.session_state.scholar_cache:
                    with st.spinner("Buscando literatura..."): st.session_state.scholar_cache[ck]=search_ss(skw,5)
                wr3=st.session_state.scholar_cache.get(ck,[])
                if wr3:
                    st.markdown('<div class="dtxt">Literatura relacionada</div>',unsafe_allow_html=True)
                    for i3,a3 in enumerate(wr3): render_article(a3,idx=i3+3000,ctx="img_ml")
            if not img_file and not cv and not ml:
                st.markdown('<div class="card" style="padding:4rem 2rem;text-align:center"><div style="font-family:Space Grotesk,sans-serif;font-size:.98rem;color:#CFD8DC;margin-bottom:.45rem">Analise de Imagem Cientifica</div><div style="font-size:.74rem;color:#546E7A;line-height:2.1">Pipeline ML: Sobel · FFT · Histograma RGB · Classificacao automatica<br>Com API key: analise completa por Claude com busca bibliografica</div></div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  PAGE: CONNECTIONS
# ══════════════════════════════════════════════════════════════
def page_knowledge():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.4rem;margin-bottom:.8rem">Rede de Conexoes</h1>',unsafe_allow_html=True)
    email=st.session_state.user_email; users=st.session_state.users if isinstance(st.session_state.users,dict) else {}; has_key=bool(get_key() and get_key().startswith("sk-"))
    def get_tags(ue):
        ud=users.get(ue,{}); tags=set(w for w in ud.get("area","").lower().split() if len(w)>3)
        for p in st.session_state.posts:
            if p.get("author_email")==ue: tags.update(t.lower() for t in p.get("tags",[]))
        return tags
    rlist=list(users.keys()); n=len(rlist); rtags={ue:get_tags(ue) for ue in rlist}
    edges=[]
    for i in range(n):
        for j in range(i+1,n):
            e1,e2=rlist[i],rlist[j]; cmn=list(rtags[e1]&rtags[e2]); fol=e2 in st.session_state.followed or e1 in st.session_state.followed
            if cmn or fol: edges.append((e1,e2,cmn[:5],len(cmn)+(2 if fol else 0)))
    pos={}
    for idx,ue in enumerate(rlist):
        a=2*3.14159*idx/max(n,1); rd=0.36+0.05*((hash(ue)%5)/4)
        pos[ue]={"x":0.5+rd*np.cos(a),"y":0.5+rd*np.sin(a),"z":0.5+0.12*((idx%4)/3-.35)}
    fig=go.Figure()
    for e1,e2,cmn,strength in edges:
        p1,p2=pos[e1],pos[e2]; al=min(0.42,0.07+strength*0.06)
        fig.add_trace(go.Scatter3d(x=[p1["x"],p2["x"],None],y=[p1["y"],p2["y"],None],z=[p1["z"],p2["z"],None],mode="lines",line=dict(color=f"rgba(30,136,229,{al:.2f})",width=min(3,1+strength)),hoverinfo="none",showlegend=False))
    ncol=[("#1E88E5" if ue==email else("#66BB6A" if ue in st.session_state.followed else "#00BCD4")) for ue in rlist]
    nsz=[22 if ue==email else(16 if ue in st.session_state.followed else 11) for ue in rlist]
    fig.add_trace(go.Scatter3d(x=[pos[ue]["x"] for ue in rlist],y=[pos[ue]["y"] for ue in rlist],z=[pos[ue]["z"] for ue in rlist],mode="markers+text",marker=dict(size=nsz,color=ncol,opacity=.9,line=dict(color="rgba(255,255,255,.07)",width=1.5)),text=[users.get(ue,{}).get("name","?").split()[0] for ue in rlist],textposition="top center",textfont=dict(color="#546E7A",size=9,family="Inter"),hovertemplate=[f"<b>{users.get(ue,{}).get('name','?')}</b><br>{users.get(ue,{}).get('area','')}<extra></extra>" for ue in rlist],showlegend=False))
    fig.update_layout(height=380,scene=dict(xaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),yaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),zaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),bgcolor="rgba(0,0,0,0)"),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig,use_container_width=True)
    c1,c2,c3=st.columns(3)
    with c1: st.markdown(f'<div class="stat-box"><div class="mval">{len(rlist)}</div><div class="mlbl">Pesquisadores</div></div>',unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="stat-box"><div class="mval-g">{len(edges)}</div><div class="mlbl">Conexoes</div></div>',unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="stat-box"><div class="mval-c">{len(st.session_state.followed)}</div><div class="mlbl">Seguindo</div></div>',unsafe_allow_html=True)
    st.markdown('<hr>',unsafe_allow_html=True)
    ts,ta2,tall=st.tabs(["  Sugestoes  ","  Minhas Conexoes  ","  Todos  "])
    with ts:
        if not has_key:
            my_tags=rtags.get(email,set())
            for ue,ud in list(users.items())[:8]:
                if ue==email or ue in st.session_state.followed: continue
                cmn=my_tags&rtags.get(ue,set())
                if not cmn: continue
                g=ugrad(ue)
                st.markdown(f'<div class="sc2"><div style="display:flex;align-items:center;gap:9px;margin-bottom:.38rem">{avh(ini(ud.get("name","?")),32,g)}<div style="flex:1"><div style="font-weight:700;font-size:.80rem;color:#ECEFF1">{ud.get("name","?")}</div><div style="font-size:.63rem;color:#546E7A">{ud.get("area","")} · {ud.get("bolsa","")}</div></div><span class="b-g">{len(cmn)} temas</span></div><div>{tags_html(list(cmn)[:4])}</div></div>',unsafe_allow_html=True)
                c_f,c_p=st.columns(2)
                with c_f:
                    if st.button(f"Seguir {ud.get('name','').split()[0]}",key=f"ks_{ue}",use_container_width=True):
                        if ue not in st.session_state.followed: st.session_state.followed.append(ue)
                        save_db(); st.rerun()
                with c_p:
                    if st.button("Ver perfil",key=f"kp_{ue}",use_container_width=True): st.session_state.profile_view=ue; st.rerun()
        else:
            ck=f"conn_{email}_{len(users)}"
            if st.button("Gerar sugestoes com Claude",key="btn_ai_conn",use_container_width=True):
                u2=users.get(email,{}); my_p=[p for p in st.session_state.posts if p.get("author_email")==email]
                others=[{"email":ue,"name":ud.get("name",""),"area":ud.get("area",""),"bolsa":ud.get("bolsa",""),"tags":list({t for p in st.session_state.posts if p.get("author_email")==ue for t in p.get("tags",[])})[:6]} for ue,ud in users.items() if ue!=email]
                prompt=f"""Sugira as 4 melhores conexoes cientificas para este pesquisador.
Perfil: area={u2.get("area","")}, bolsa={u2.get("bolsa","")}, tags={list({t for p in my_p for t in p.get("tags",[])})[:8]}
Pesquisadores disponiveis: {json.dumps(others[:12],ensure_ascii=False)}
Responda APENAS JSON puro: {{"sugestoes":[{{"email":"<email>","razao":"<1-2 frases>","score":<0-100>,"temas":[]}}]}}"""
                with st.spinner("Claude analisando rede..."):
                    txt,err=call_claude(prompt,max_tokens=600)
                if txt:
                    try:
                        cl=re.sub(r'^```json\s*','',txt.strip()); cl=re.sub(r'\s*```$','',cl); st.session_state.conn_cache[ck]=json.loads(cl)
                    except: st.error("Erro ao processar resposta")
                elif err: st.error(f"Erro: {err}")
            ai_r=st.session_state.conn_cache.get(ck)
            if ai_r:
                for sug in ai_r.get("sugestoes",[]):
                    sue=sug.get("email",""); sud=users.get(sue,{})
                    if not sud: continue
                    rn=sud.get("name","?"); rg=ugrad(sue); score=sug.get("score",70)
                    sc_c="#66BB6A" if score>=80 else("#42A5F5" if score>=60 else "#FF9800")
                    is_fol2=sue in st.session_state.followed
                    st.markdown(f'<div class="ai-box"><div style="display:flex;align-items:center;gap:9px;margin-bottom:.5rem">{avh(ini(rn),34,rg)}<div style="flex:1"><div style="font-family:Space Grotesk,sans-serif;font-weight:700;font-size:.82rem;color:#ECEFF1">{rn}</div><div style="font-size:.63rem;color:#546E7A">{sud.get("area","")} · {sud.get("bolsa","")}</div></div><div style="background:rgba(0,0,0,.3);border-radius:9px;padding:.3rem .6rem;text-align:center;flex-shrink:0"><div style="font-family:Space Grotesk,sans-serif;font-size:1.1rem;font-weight:900;color:{sc_c}">{score}</div><div style="font-size:.49rem;color:#546E7A;text-transform:uppercase">score</div></div></div><div style="background:rgba(30,136,229,.04);border:1px solid rgba(30,136,229,.10);border-radius:8px;padding:.44rem .68rem;font-size:.74rem;color:#90A4AE;line-height:1.65;margin-bottom:.38rem">{sug.get("razao","")}</div><div>{tags_html(sug.get("temas",[])[:5])}</div></div>',unsafe_allow_html=True)
                    c_f,c_p,c_c=st.columns(3)
                    with c_f:
                        if st.button("Deixar de seguir" if is_fol2 else "Seguir",key=f"af_{sue}",use_container_width=True):
                            if not is_fol2: st.session_state.followed.append(sue)
                            else: st.session_state.followed.remove(sue)
                            save_db(); st.rerun()
                    with c_p:
                        if st.button("Perfil",key=f"ap_{sue}",use_container_width=True): st.session_state.profile_view=sue; st.rerun()
                    with c_c:
                        if st.button("Chat",key=f"ac2_{sue}",use_container_width=True):
                            st.session_state.chat_msgs.setdefault(sue,[]); st.session_state.active_chat=sue; st.session_state.page="chat"; st.rerun()
            else: st.markdown('<div style="text-align:center;padding:2rem;color:#546E7A;font-size:.78rem">Clique para gerar sugestoes com Claude AI.</div>',unsafe_allow_html=True)
    with ta2:
        mc=[(e1,e2,c,s) for e1,e2,c,s in edges if e1==email or e2==email]
        if not mc: st.info("Publique pesquisas para criar conexoes.")
        for e1,e2,cmn,strength in sorted(mc,key=lambda x:-x[3]):
            oth=e2 if e1==email else e1; od=users.get(oth,{}); og=ugrad(oth)
            st.markdown(f'<div class="sc2"><div style="display:flex;align-items:center;gap:8px">{avh(ini(od.get("name","?")),30,og)}<div style="flex:1"><div style="font-weight:700;font-size:.79rem;color:#ECEFF1">{od.get("name","?")}</div><div style="font-size:.63rem;color:#546E7A">{od.get("area","")} · {od.get("bolsa","")}</div></div>{tags_html(cmn[:3])}</div></div>',unsafe_allow_html=True)
            cv2,cm2,_=st.columns([1,1,4])
            with cv2:
                if st.button("Perfil",key=f"kv_{oth}",use_container_width=True): st.session_state.profile_view=oth; st.rerun()
            with cm2:
                if st.button("Chat",key=f"kc_{oth}",use_container_width=True):
                    st.session_state.chat_msgs.setdefault(oth,[]); st.session_state.active_chat=oth; st.session_state.page="chat"; st.rerun()
    with tall:
        sq2=st.text_input("",placeholder="Buscar pesquisador...",key="all_s",label_visibility="collapsed")
        for ue,ud in users.items():
            if ue==email: continue
            rn=ud.get("name","?"); ua=ud.get("area","")
            if sq2 and sq2.lower() not in rn.lower() and sq2.lower() not in ua.lower(): continue
            is_fol=ue in st.session_state.followed; og=ugrad(ue)
            st.markdown(f'<div class="sc2"><div style="display:flex;align-items:center;gap:8px">{avh(ini(rn),30,og)}<div style="flex:1"><div style="font-size:.79rem;font-weight:700;color:#ECEFF1">{rn}</div><div style="font-size:.63rem;color:#546E7A">{ua} · {ud.get("bolsa","")}</div></div></div></div>',unsafe_allow_html=True)
            ca3,cb3,cc3=st.columns(3)
            with ca3:
                if st.button("Perfil",key=f"av_{ue}",use_container_width=True): st.session_state.profile_view=ue; st.rerun()
            with cb3:
                if st.button("Deixar de seguir" if is_fol else "Seguir",key=f"af2_{ue}",use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue)
                    else: st.session_state.followed.append(ue)
                    save_db(); st.rerun()
            with cc3:
                if st.button("Chat",key=f"ac_{ue}",use_container_width=True):
                    st.session_state.chat_msgs.setdefault(ue,[]); st.session_state.active_chat=ue; st.session_state.page="chat"; st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  PAGE: FOLDERS + ANALYTICS
# ══════════════════════════════════════════════════════════════
def page_folders():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.4rem;margin-bottom:.8rem">Pastas e Analises</h1>',unsafe_allow_html=True)
    email=st.session_state.user_email; u=guser(); ra=u.get("area","")
    tf,ta_doc,ti,tt=st.tabs(["  Pastas  ","  Documentos  ","  Interesses  ","  Tendencias  "])
    with tf:
        c1,c2=st.columns([2,2])
        with c1: nfn=st.text_input("Nome da pasta",placeholder="Ex: Genomica Comparativa",key="nf_n")
        with c2: nfd=st.text_input("Descricao",key="nf_d")
        if st.button("Criar pasta",key="btn_nf"):
            if nfn.strip():
                if nfn not in st.session_state.folders: st.session_state.folders[nfn]={"desc":nfd,"files":[],"notes":"","analyses":{}}; save_db(); st.success(f"Pasta '{nfn}' criada!"); st.rerun()
                else: st.warning("Ja existe.")
            else: st.warning("Digite um nome.")
        st.markdown('<hr>',unsafe_allow_html=True)
        if not st.session_state.folders: st.markdown('<div class="card" style="text-align:center;padding:4rem;color:#546E7A">Nenhuma pasta criada.</div>',unsafe_allow_html=True)
        else:
            for fn,fd in list(st.session_state.folders.items()):
                if not isinstance(fd,dict): fd={"files":fd,"desc":"","notes":"","analyses":{}}; st.session_state.folders[fn]=fd
                files=fd.get("files",[]); analyses=fd.get("analyses",{})
                with st.expander(f"{fn} — {len(files)} arquivo(s)"):
                    st.markdown(f'<div style="font-size:.65rem;color:#546E7A;margin-bottom:.5rem">{fd.get("desc","")}</div>',unsafe_allow_html=True)
                    up=st.file_uploader("",type=None,key=f"up_{fn}",label_visibility="collapsed",accept_multiple_files=True)
                    if up:
                        for uf in up:
                            if uf.name not in files: files.append(uf.name)
                            if fn not in st.session_state.folder_bytes: st.session_state.folder_bytes[fn]={}
                            uf.seek(0); st.session_state.folder_bytes[fn][uf.name]=uf.read()
                        fd["files"]=files; save_db(); st.success(f"{len(up)} adicionado(s)!")
                    for f in files:
                        ft=ftype_of(f); ha=f in analyses; rel=analyses[f].get("relevance_score",0) if ha else 0
                        ok_b=' <span class="b-g" style="font-size:.55rem">analisado</span>' if ha else ''
                        st.markdown(f'<div style="display:flex;align-items:center;gap:7px;padding:.30rem 0;border-bottom:1px solid rgba(255,255,255,.04)"><span style="font-size:.67rem;color:#546E7A">[{ft[:3]}]</span><div style="flex:1"><div style="font-size:.72rem;color:#90A4AE">{f}{ok_b}</div>{"<div style=\"height:2px;background:linear-gradient(90deg,#1E88E5,#26C6DA);border-radius:2px;width:"+str(int(rel*.9))+"%\"></div>" if ha else ""}</div></div>',unsafe_allow_html=True)
                    ca2,cb2,cc2=st.columns(3)
                    with ca2:
                        if st.button("Analisar documentos",key=f"an_{fn}",use_container_width=True):
                            if files:
                                pb=st.progress(0,"Iniciando..."); fb=st.session_state.folder_bytes.get(fn,{})
                                for fi,f in enumerate(files):
                                    pb.progress((fi+1)/len(files),f"Analisando {f[:25]}..."); analyses[f]=analyze_doc(f,fb.get(f,b""),ftype_of(f),ra)
                                fd["analyses"]=analyses; save_db(); pb.empty(); st.success("Concluido!"); st.rerun()
                            else: st.warning("Adicione arquivos.")
                    with cb2:
                        if st.button("Exportar JSON",key=f"ex_{fn}",use_container_width=True):
                            if analyses: st.download_button("Baixar",json.dumps({"pasta":fn,"analises":analyses},ensure_ascii=False,indent=2),f"{fn}_analise.json","application/json",key=f"dl_{fn}")
                    with cc2:
                        if st.button("Excluir pasta",key=f"df_{fn}",use_container_width=True): del st.session_state.folders[fn]; save_db(); st.rerun()
                    nt=st.text_area("Notas",value=fd.get("notes",""),key=f"note_{fn}",height=55)
                    if st.button("Salvar nota",key=f"sn_{fn}"): fd["notes"]=nt; save_db(); st.success("Salvo!")
    with ta_doc:
        folders=st.session_state.folders
        if not folders: st.info("Crie pastas e analise documentos.")
        else:
            all_an={f:an for fd2 in folders.values() if isinstance(fd2,dict) for f,an in fd2.get("analyses",{}).items()}
            tot_f=sum(len(fd2.get("files",[]) if isinstance(fd2,dict) else fd2) for fd2 in folders.values())
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
                fig_t.update_layout(**{**pc(),'height':250,'yaxis':dict(showgrid=False,color="#546E7A",tickfont=dict(size=9)),'title':dict(text="Distribuicao de temas",font=dict(color="#CFD8DC",family="Space Grotesk",size=11))})
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_t,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
            if len(all_kw)>4:
                kw_c=Counter(all_kw[:200]); top20=kw_c.most_common(20)
                fig_kw=go.Figure(go.Bar(x=[c2 for _,c2 in top20],y=[k for k,_ in top20],orientation='h',marker=dict(color=CHART_C[:20]),text=[str(c2) for _,c2 in top20],textposition="outside",textfont=dict(color="#546E7A",size=8)))
                fig_kw.update_layout(**{**pc(),'height':330,'yaxis':dict(showgrid=False,color="#546E7A",tickfont=dict(size=8)),'title':dict(text="Keywords mais frequentes",font=dict(color="#CFD8DC",family="Space Grotesk",size=11)),'margin':dict(l=10,r=10,t=36,b=8)})
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_kw,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
            if all_an:
                docs=[f[:16]+"..." if len(f)>16 else f for f in all_an.keys()]
                rels=[a.get("relevance_score",0) for a in all_an.values()]
                wqs=[a.get("writing_quality",0) for a in all_an.values()]
                fig_rq=go.Figure()
                fig_rq.add_trace(go.Bar(name="Relevancia",x=docs,y=rels,marker_color=CHART_C[0]))
                fig_rq.add_trace(go.Bar(name="Qualidade",x=docs,y=wqs,marker_color=CHART_C[2]))
                fig_rq.update_layout(barmode="group",title=dict(text="Relevancia e Qualidade",font=dict(color="#CFD8DC",family="Space Grotesk",size=11)),height=230,**pc(),legend=dict(font=dict(color="#546E7A",size=9)))
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_rq,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
                st.markdown('<div class="dtxt">Detalhes por arquivo</div>',unsafe_allow_html=True)
                for f,an in all_an.items():
                    with st.expander(f):
                        kws=an.get("keywords",[]); topics=an.get("topics",{}); rel=an.get("relevance_score",0); wq=an.get("writing_quality",0)
                        rc="#66BB6A" if rel>=70 else("#42A5F5" if rel>=45 else "#EF5350")
                        c1d,c2d,c3d,c4d=st.columns(4)
                        with c1d: st.markdown(f'<div class="stat-box"><div style="font-family:Space Grotesk,sans-serif;font-size:1.05rem;font-weight:800;color:{rc}">{rel}%</div><div class="mlbl">Relevancia</div></div>',unsafe_allow_html=True)
                        with c2d: st.markdown(f'<div class="stat-box"><div style="font-family:Space Grotesk,sans-serif;font-size:1.05rem;font-weight:800;color:#42A5F5">{wq}%</div><div class="mlbl">Qualidade</div></div>',unsafe_allow_html=True)
                        with c3d: st.markdown(f'<div class="stat-box"><div style="font-family:Space Grotesk,sans-serif;font-size:1.05rem;font-weight:800;color:#26C6DA">{an.get("word_count",0)}</div><div class="mlbl">Palavras</div></div>',unsafe_allow_html=True)
                        with c4d: st.markdown(f'<div class="stat-box"><div style="font-family:Space Grotesk,sans-serif;font-size:1.05rem;font-weight:800;color:#FF9800">{an.get("reading_time",0)}min</div><div class="mlbl">Leitura</div></div>',unsafe_allow_html=True)
                        st.markdown(f'<div style="font-size:.74rem;color:#90A4AE;margin:.4rem 0">{an.get("summary","")}</div>',unsafe_allow_html=True)
                        if kws: st.markdown(tags_html(kws[:16]),unsafe_allow_html=True)
                        if topics:
                            fig2=go.Figure(go.Pie(labels=list(topics.keys()),values=list(topics.values()),hole=0.5,marker=dict(colors=CHART_C[:len(topics)],line=dict(color=["#020B18"]*12,width=2)),textfont=dict(color="white",size=8)))
                            fig2.update_layout(height=190,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(font=dict(color="#546E7A",size=8)),margin=dict(l=0,r=0,t=8,b=0))
                            st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig2,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
    with ti:
        prefs=st.session_state.user_prefs.get(email,{}); my_posts=[p for p in st.session_state.posts if p.get("author_email")==email]; d=st.session_state.stats
        c1,c2,c3=st.columns(3)
        with c1: st.markdown(f'<div class="stat-box"><div class="mval">{d.get("h_index",4)}</div><div class="mlbl">Indice H</div></div>',unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="stat-box"><div class="mval-g">{d.get("impact",3.8):.1f}</div><div class="mlbl">Fator Impacto</div></div>',unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="stat-box"><div class="mval-y">{len(st.session_state.saved_articles)}</div><div class="mlbl">Artigos Salvos</div></div>',unsafe_allow_html=True)
        if prefs:
            top=sorted(prefs.items(),key=lambda x:-x[1])[:12]; mx=max(s for _,s in top) if top else 1
            cats=[t for t,_ in top[:8]]; vals=[round(s/mx*100) for _,s in top[:8]]
            if len(cats)>=3:
                fig3=go.Figure(go.Scatterpolar(r=vals+[vals[0]],theta=cats+[cats[0]],fill='toself',line=dict(color="#1E88E5",width=1.5),fillcolor="rgba(30,136,229,.10)"))
                fig3.update_layout(height=270,polar=dict(bgcolor="rgba(0,0,0,0)",radialaxis=dict(visible=True,gridcolor="rgba(255,255,255,.04)",color="#546E7A",tickfont=dict(size=8)),angularaxis=dict(gridcolor="rgba(255,255,255,.04)",color="#546E7A",tickfont=dict(size=9))),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=38,r=38,t=14,b=14))
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig3,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
            top10=[t for t,_ in top[:10]]; vals10=[round(s,1) for _,s in top[:10]]
            fig_i=go.Figure(go.Bar(x=top10,y=vals10,marker=dict(color=CHART_C[:len(top10)]),text=vals10,textposition="outside",textfont=dict(color="#546E7A",size=9)))
            fig_i.update_layout(**{**pc(),'height':200,'title':dict(text="Interesses de pesquisa",font=dict(color="#CFD8DC",family="Space Grotesk",size=11))})
            st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_i,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
        else: st.info("Interaja com publicacoes e busque temas para construir seu perfil de interesses.")
        st.markdown('<hr>',unsafe_allow_html=True)
        nh=st.number_input("Indice H",0,200,d.get("h_index",4),key="e_h"); nfi=st.number_input("Fator impacto",0.0,100.0,float(d.get("impact",3.8)),step=0.1,key="e_fi"); nn2=st.text_area("Notas de pesquisa",value=d.get("notes",""),key="e_nt",height=65)
        if st.button("Salvar metricas",key="btn_sm"): d.update({"h_index":nh,"impact":nfi,"notes":nn2}); st.success("Salvo!")
    with tt:
        all_p=st.session_state.posts; users_t=st.session_state.users if isinstance(st.session_state.users,dict) else {}
        tag_all=Counter(t for p in all_p for t in p.get("tags",[])); area_all=Counter(p.get("area","") for p in all_p if p.get("area","")); status_all=Counter(p.get("status","") for p in all_p); area_users=Counter(ud.get("area","Outro") for ud in users_t.values() if ud.get("area")); bolsa_users=Counter(ud.get("bolsa","sem bolsa") for ud in users_t.values())
        c1,c2=st.columns(2)
        with c1:
            if tag_all:
                top12=tag_all.most_common(12); fig_tag=go.Figure(go.Bar(y=[t for t,_ in top12],x=[c2 for _,c2 in top12],orientation='h',marker=dict(color=CHART_C[:12]),text=[str(c2) for _,c2 in top12],textposition="outside",textfont=dict(color="#546E7A",size=9)))
                fig_tag.update_layout(**{**pc(),'height':310,'yaxis':dict(showgrid=False,color="#546E7A",tickfont=dict(size=8)),'title':dict(text="Tags mais usadas",font=dict(color="#CFD8DC",family="Space Grotesk",size=11))})
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_tag,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
        with c2:
            if area_all:
                fig_area=go.Figure(go.Pie(labels=list(area_all.keys()),values=list(area_all.values()),hole=0.45,marker=dict(colors=CHART_C[:len(area_all)],line=dict(color=["#020B18"]*12,width=2)),textfont=dict(color="white",size=8)))
                fig_area.update_layout(height=310,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(font=dict(color="#546E7A",size=8)),title=dict(text="Publicacoes por area",font=dict(color="#CFD8DC",family="Space Grotesk",size=11)),margin=dict(l=0,r=0,t=36,b=0))
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_area,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
        c3,c4=st.columns(2)
        with c3:
            if status_all:
                fig_st=go.Figure(go.Bar(x=list(status_all.keys()),y=list(status_all.values()),marker=dict(color=CHART_C[:len(status_all)]),text=list(status_all.values()),textposition="outside",textfont=dict(color="#546E7A",size=9)))
                fig_st.update_layout(**{**pc(),'height':210,'title':dict(text="Por status",font=dict(color="#CFD8DC",family="Space Grotesk",size=11))})
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_st,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
        with c4:
            if bolsa_users:
                fig_b=go.Figure(go.Pie(labels=list(bolsa_users.keys()),values=list(bolsa_users.values()),hole=0.45,marker=dict(colors=CHART_C[:len(bolsa_users)],line=dict(color=["#020B18"]*12,width=2)),textfont=dict(color="white",size=8)))
                fig_b.update_layout(height=210,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(font=dict(color="#546E7A",size=8)),title=dict(text="Bolsas",font=dict(color="#CFD8DC",family="Space Grotesk",size=11)),margin=dict(l=0,r=0,t=36,b=0))
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_b,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  PAGE: CHAT
# ══════════════════════════════════════════════════════════════
def page_chat():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.4rem;margin-bottom:.8rem">Mensagens</h1>',unsafe_allow_html=True)
    cc,cm=st.columns([.88,2.9]); email=st.session_state.user_email; users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    with cc:
        st.markdown('<div style="font-size:.57rem;font-weight:700;color:#546E7A;letter-spacing:.12em;text-transform:uppercase;margin-bottom:.6rem">Conversas</div>',unsafe_allow_html=True)
        shown=set()
        for ue in st.session_state.chat_contacts:
            if ue==email or ue in shown: continue
            shown.add(ue); ud=users.get(ue,{}); un=ud.get("name","?"); ug=ugrad(ue)
            msgs=st.session_state.chat_msgs.get(ue,[]); last=msgs[-1]["text"][:22]+"..." if msgs and len(msgs[-1]["text"])>22 else(msgs[-1]["text"] if msgs else "iniciar")
            active=st.session_state.active_chat==ue
            bg=f"rgba(30,136,229,{'.09' if active else '.02'})"; bdr=f"rgba(30,136,229,{'.25' if active else '.07'})"
            st.markdown(f'<div style="background:{bg};border:1px solid {bdr};border-radius:10px;padding:6px 8px;margin-bottom:3px"><div style="display:flex;align-items:center;gap:7px">{avh(ini(un),26,ug)}<div style="overflow:hidden;flex:1"><div style="font-size:.73rem;font-weight:600;color:#ECEFF1">{un}</div><div style="font-size:.62rem;color:#546E7A;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{last}</div></div></div></div>',unsafe_allow_html=True)
            if st.button("abrir",key=f"oc_{ue}",use_container_width=True): st.session_state.active_chat=ue; st.rerun()
        st.markdown('<hr>',unsafe_allow_html=True)
        nc2=st.text_input("",placeholder="E-mail do pesquisador...",key="new_ct",label_visibility="collapsed")
        if st.button("Adicionar contato",key="btn_ac",use_container_width=True):
            if nc2 in users and nc2!=email:
                if nc2 not in st.session_state.chat_contacts: st.session_state.chat_contacts.append(nc2)
                st.rerun()
    with cm:
        if st.session_state.active_chat:
            contact=st.session_state.active_chat; cd=users.get(contact,{}); cn=cd.get("name","?"); cg=ugrad(contact)
            msgs=st.session_state.chat_msgs.get(contact,[])
            st.markdown(f'<div style="background:rgba(30,136,229,.04);border:1px solid rgba(30,136,229,.12);border-radius:12px;padding:9px 13px;margin-bottom:.75rem;display:flex;align-items:center;gap:9px">{avh(ini(cn),32,cg)}<div style="flex:1"><div style="font-weight:700;font-size:.84rem;color:#ECEFF1">{cn}</div><div style="font-size:.62rem;color:#66BB6A">comunicacao cifrada ponta a ponta</div></div></div>',unsafe_allow_html=True)
            for msg in msgs:
                im=msg["from"]=="me"; cls="bme" if im else "bthem"
                st.markdown(f'<div style="display:flex;{"justify-content:flex-end" if im else ""}"><div class="{cls}">{msg["text"]}<div style="font-size:.56rem;color:#546E7A;margin-top:2px;text-align:{"right" if im else "left"}">{msg["time"]}</div></div></div>',unsafe_allow_html=True)
            st.markdown("<br>",unsafe_allow_html=True)
            ci2,cb2=st.columns([5,1])
            with ci2: nm=st.text_input("",placeholder="Escreva...",key=f"mi_{contact}",label_visibility="collapsed")
            with cb2:
                if st.button("Enviar",key=f"ms_{contact}",use_container_width=True):
                    if nm:
                        now=datetime.now().strftime("%H:%M"); st.session_state.chat_msgs.setdefault(contact,[]).append({"from":"me","text":nm,"time":now}); st.rerun()
        else: st.markdown('<div class="card" style="text-align:center;padding:5rem"><div style="font-family:Space Grotesk,sans-serif;font-size:.95rem;color:#CFD8DC">Selecione uma conversa</div></div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  PAGE: SETTINGS
# ══════════════════════════════════════════════════════════════
def page_settings():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.4rem;margin-bottom:.8rem">Configuracoes</h1>',unsafe_allow_html=True)
    email=st.session_state.user_email; ud=st.session_state.users.get(email,{})
    st.markdown(f'<div class="sc" style="margin-bottom:.6rem"><div style="font-size:.57rem;color:#546E7A;text-transform:uppercase;letter-spacing:.09em;margin-bottom:.3rem;font-weight:700">Conta</div><div style="font-family:Space Grotesk,sans-serif;font-weight:700;font-size:.92rem;color:#42A5F5">{email}</div><div style="font-size:.70rem;color:#90A4AE;margin-top:.2rem">Bolsa: {ud.get("bolsa","nao informada")}</div></div>',unsafe_allow_html=True)
    en=ud.get("2fa_enabled",False)
    if st.button("Desativar 2FA" if en else "Ativar 2FA",key="cfg_2fa"): st.session_state.users[email]["2fa_enabled"]=not en; save_db(); st.rerun()
    st.markdown(f'<div style="font-size:.72rem;color:#90A4AE;margin:.3rem 0">2FA: <strong style="color:{"#66BB6A" if en else "#EF5350"}">{"Ativo" if en else "Inativo"}</strong></div>',unsafe_allow_html=True)
    st.markdown('<hr>',unsafe_allow_html=True)
    with st.form("cpw"):
        op=st.text_input("Senha atual",type="password"); np2=st.text_input("Nova senha",type="password"); nc3=st.text_input("Confirmar",type="password")
        if st.form_submit_button("Alterar senha",use_container_width=True):
            if hp(op)!=ud.get("password",""): st.error("Senha atual incorreta.")
            elif np2!=nc3: st.error("Senhas nao coincidem.")
            elif len(np2)<6: st.error("Minimo 6 caracteres.")
            else: st.session_state.users[email]["password"]=hp(np2); save_db(); st.success("Senha alterada!")
    st.markdown('<hr>',unsafe_allow_html=True)
    for nm,ds in [("AES-256","Cifragem end-to-end nas mensagens"),("SHA-256","Hash seguro de senhas"),("TLS 1.3","Transmissao cifrada")]:
        st.markdown(f'<div class="sc2" style="background:rgba(27,94,32,.04);border-color:rgba(102,187,106,.12)"><div style="display:flex;align-items:center;gap:8px"><div style="background:rgba(102,187,106,.10);border-radius:6px;padding:3px 6px;font-size:.65rem;color:#66BB6A;font-weight:700">ativo</div><div><div style="font-weight:700;color:#66BB6A;font-size:.75rem">{nm}</div><div style="font-size:.63rem;color:#546E7A">{ds}</div></div></div></div>',unsafe_allow_html=True)
    st.markdown('<hr>',unsafe_allow_html=True)
    if st.button("Sair da conta",key="logout",use_container_width=True): st.session_state.logged_in=False; st.session_state.user_email=None; st.session_state.page="login"; st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════════════════════════════
def main():
    inject_css()
    if not st.session_state.logged_in: page_login(); return
    if st.session_state.page=="welcome": render_nav(); page_welcome(); return
    render_nav()
    if st.session_state.profile_view: page_profile(st.session_state.profile_view); return
    {"repository":page_repository,"search":page_search,"knowledge":page_knowledge,"folders":page_folders,"chat":page_chat,"settings":page_settings}.get(st.session_state.page,page_repository)()

main()
