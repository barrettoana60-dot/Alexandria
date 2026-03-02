import subprocess, sys, os, json, hashlib, random, string, re, io
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
    "135deg,#FF6B35,#F7C948","135deg,#00C9A7,#845EC2","135deg,#FF4E8A,#FF9A44",
    "135deg,#4ECDC4,#44A1A0","135deg,#A8FF78,#78FFD6","135deg,#6C63FF,#48C6EF",
    "135deg,#F7971E,#FFD200","135deg,#FF5F6D,#FFC371",
]
def ugrad(e): return f"linear-gradient({GRAD_POOL[hash(e or '')%len(GRAD_POOL)]})"

STOPWORDS={"de","a","o","que","e","do","da","em","um","para","é","com","uma","os","no","se","na","por","mais","as","dos","como","mas","foi","ao","ele","das","tem","à","seu","sua","ou","ser","quando","muito","há","nos","já","está","eu","também","só","pelo","pela","até","isso","ela","entre","era","depois","sem","mesmo","aos","ter","seus","the","of","and","to","in","is","it","that","was","he","for","on","are","as","with","they","at","be","this","from","or","one","had","by","but","not","what","all","were","we","when","your","can","said","there","use","an","each","which","she","do","how","their","if","will","up","other","about","out","many","then","them","these","so"}

SEED_POSTS=[
    {"id":1,"author":"Carlos Mendez","author_email":"carlos@nebula.ai","avatar":"CM","area":"Neurociência","title":"Efeitos da Privação de Sono na Plasticidade Sináptica","abstract":"Investigamos como 24h de privação de sono afetam espinhas dendríticas em ratos Wistar, com redução de 34% na plasticidade hipocampal. Janela crítica identificada nas primeiras 6h de recuperação.","tags":["neurociência","sono","memória","hipocampo"],"likes":47,"comments":[{"user":"Maria Silva","text":"Excelente metodologia!"},{"user":"João Lima","text":"Quais os critérios de exclusão?"}],"status":"Em andamento","date":"2026-02-10","liked_by":[],"saved_by":[],"connections":["sono","memória"],"views":312},
    {"id":2,"author":"Luana Freitas","author_email":"luana@nebula.ai","avatar":"LF","area":"Biomedicina","title":"CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras","abstract":"Vetor AAV9 modificado para entrega de CRISPR no gene DMD com eficiência de 78% em modelos mdx. Publicação em Cell prevista Q2 2026.","tags":["CRISPR","gene terapia","músculo","AAV9"],"likes":93,"comments":[{"user":"Ana","text":"Quando iniciam os trials clínicos?"}],"status":"Publicado","date":"2026-01-28","liked_by":[],"saved_by":[],"connections":["genômica","distrofia"],"views":891},
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
    "carlos@nebula.ai":[{"from":"carlos@nebula.ai","text":"Oi! Vi seu comentário na pesquisa de sono.","time":"09:14"},{"from":"me","text":"Achei muito interessante!","time":"09:16"}],
    "luana@nebula.ai":[{"from":"luana@nebula.ai","text":"Podemos colaborar no próximo projeto?","time":"ontem"}],
    "rafael@nebula.ai":[{"from":"rafael@nebula.ai","text":"Já compartilhei o repositório.","time":"08:30"}],
}

@st.cache_resource(show_spinner=False)
def get_db_manager():
    class DB:
        def __init__(self):
            self.load_initial_data(SEED_USERS,SEED_POSTS,CHAT_INIT)
        def load_initial_data(self,su,sp,ci):
            disk=load_db()
            du=disk.get("users",{})
            if not isinstance(du,dict): du={}
            st.session_state.setdefault("users",{**su,**du})
            st.session_state.setdefault("logged_in",False)
            st.session_state.setdefault("current_user",None)
            st.session_state.setdefault("page","login")
            st.session_state.setdefault("profile_view",None)
            dp=disk.get("user_prefs",{})
            st.session_state.setdefault("user_prefs",{k:defaultdict(float,v) for k,v in dp.items()})
            st.session_state.setdefault("pending_verify",None)
            st.session_state.setdefault("pending_2fa",None)
            rp=disk.get("feed_posts",[dict(p) for p in sp])
            for p in rp: p.setdefault("liked_by",[]); p.setdefault("saved_by",[]); p.setdefault("comments",[]); p.setdefault("views",200)
            st.session_state.setdefault("feed_posts",rp)
            st.session_state.setdefault("folders",disk.get("folders",{}))
            st.session_state.setdefault("folder_files_bytes",{})
            st.session_state.setdefault("chat_contacts",list(su.keys()))
            st.session_state.setdefault("chat_messages",{k:list(v) for k,v in ci.items()})
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
            st.session_state.setdefault("initialized",True)
        def save(self):
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
    return DB()

db=get_db_manager()
if "initialized" not in st.session_state: db.load_initial_data(SEED_USERS,SEED_POSTS,CHAT_INIT)

# ── CACHED ANALYSIS FUNCTIONS ──
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
def extract_csv(b):
    try:
        df=pd.read_csv(io.BytesIO(b),nrows=150)
        s=f"Colunas: {', '.join(df.columns.tolist())}\n"
        for c in df.columns[:8]:
            if df[c].dtype==object: s+=f"{c}: {', '.join(str(v) for v in df[c].dropna().head(3))}\n"
            else: s+=f"{c}: min={df[c].min():.2f}, max={df[c].max():.2f}\n"
        return s
    except: return ""

@st.cache_data(show_spinner=False)
def extract_xlsx(b):
    if not openpyxl: return ""
    try:
        wb=openpyxl.load_workbook(io.BytesIO(b),read_only=True,data_only=True); t=""
        for sn in wb.sheetnames[:2]:
            ws=wb[sn]; t+=f"\n=== {sn} ===\n"
            for row in list(ws.iter_rows(max_row=40,values_only=True)):
                rv=[str(v) for v in row if v is not None]
                if rv: t+=" | ".join(rv[:8])+"\n"
        return t[:15000]
    except: return ""

@st.cache_data(show_spinner=False)
def kw_extract(text,n=25):
    if not text: return []
    words=re.findall(r'\b[a-záàâãéêíóôõúüçA-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]{4,}\b',text.lower())
    words=[w for w in words if w not in STOPWORDS]
    if not words: return []
    tf=Counter(words); tot=sum(tf.values())
    return [w for w,_ in sorted({w:c/tot for w,c in tf.items()}.items(),key=lambda x:-x[1])[:n]]

@st.cache_data(show_spinner=False)
def topic_dist(kws):
    tm={"Saúde & Medicina":["saúde","medicina","clínico","health","medical","therapy","disease","cancer"],"Biologia & Genômica":["biologia","genômica","gene","dna","rna","proteína","célula","crispr","genomics"],"Neurociência":["neurociência","neural","cérebro","cognição","memória","neurônio","sono","brain","cognitive"],"Computação & IA":["algoritmo","machine","learning","inteligência","dados","computação","ia","algorithm","deep","quantum"],"Física & Astronomia":["física","quântica","partícula","energia","galáxia","astrofísica","cosmologia","dark"],"Química & Materiais":["química","molécula","síntese","reação","polímero","chemistry","molecule","nanomaterial"],"Engenharia":["engenharia","sistema","robótica","automação","sensor","engineering","robotics"],"Ciências Sociais":["sociedade","cultura","educação","política","economia","social","psicologia","society"],"Ecologia & Clima":["ecologia","clima","ambiente","biodiversidade","ecology","climate","environment"],"Matemática":["matemática","estatística","probabilidade","equação","mathematics","statistics","probability"]}
    s=defaultdict(int)
    for kw in kws:
        for tp,terms in tm.items():
            if any(t in kw or kw in t for t in terms): s[tp]+=1
    return dict(sorted(s.items(),key=lambda x:-x[1])) if s else {"Pesquisa Geral":1}

@st.cache_data(show_spinner=False)
def analyze_doc(fname,fbytes,ftype,area=""):
    r={"file":fname,"type":ftype,"keywords":[],"authors":[],"years":[],"references":[],"topics":{},"references_online":[],"relevance_score":0,"summary":"","strengths":[],"improvements":[],"writing_quality":0,"reading_time":0,"word_count":0,"sentence_complexity":0}
    text=""
    if ftype=="PDF" and fbytes: text=extract_pdf(fbytes)
    elif ftype in ("Planilha","Dados") and fbytes:
        if fname.endswith(".xlsx"): text=extract_xlsx(fbytes)
        elif fname.endswith(".csv"): text=extract_csv(fbytes)
    elif ftype in ("Word","Texto","Markdown") and fbytes:
        try: text=fbytes.decode("utf-8",errors="ignore")
        except: pass
    if text:
        r["keywords"]=kw_extract(text,25)
        r["topics"]=topic_dist(r["keywords"])
        words=len(text.split()); r["word_count"]=words; r["reading_time"]=max(1,round(words/200))
        sents=re.split(r'[.!?]+',text); r["sentence_complexity"]=round(sum(len(s.split()) for s in sents)/max(len(sents),1),1)
        score=50+(15 if len(r["keywords"])>15 else 0)+(15 if words>1000 else 0)+(10 if 10<r["sentence_complexity"]<30 else 0)
        r["writing_quality"]=min(100,score)
        if area:
            aw=area.lower().split(); rel=sum(1 for w in aw if any(w in kw for kw in r["keywords"]))
            r["relevance_score"]=min(100,rel*15+45)
        else: r["relevance_score"]=65
        if len(r["keywords"])>15: r["strengths"].append(f"Vocabulário rico ({len(r['keywords'])} termos)")
        if words>3000: r["strengths"].append(f"Texto detalhado ({words} palavras)")
        if r["writing_quality"]>70: r["strengths"].append("Alta qualidade técnica")
        if words<500: r["improvements"].append("Expandir o conteúdo")
        if r["writing_quality"]<50: r["improvements"].append("Melhorar densidade técnica")
        top3=list(r["topics"].keys())[:3]; top5=r["keywords"][:5]
        r["summary"]=f"{ftype} · {words} palavras · ~{r['reading_time']} min · {', '.join(top3)} · {', '.join(top5)}"
    else:
        r["summary"]=f"Arquivo {ftype} — análise de texto não disponível."; r["relevance_score"]=50
        r["keywords"]=kw_extract(fname.lower().replace("_"," "),5); r["topics"]=topic_dist(r["keywords"])
    return r

@st.cache_data(show_spinner=False)
def analyze_image(b):
    try:
        img=PILImage.open(io.BytesIO(b)).convert("RGB"); orig=img.size
        small=img.resize((512,512)); arr=np.array(small,dtype=np.float32)
        r,g,bc=arr[:,:,0],arr[:,:,1],arr[:,:,2]
        mr,mg,mb=float(r.mean()),float(g.mean()),float(bc.mean())
        gray=arr.mean(axis=2)
        gx=np.pad(np.diff(gray,axis=1),((0,0),(0,1)),mode='edge')
        gy=np.pad(np.diff(gray,axis=0),((0,1),(0,0)),mode='edge')
        ei=float(np.sqrt(gx**2+gy**2).mean())
        hh,ww=gray.shape[0]//2,gray.shape[1]//2
        q=[gray[:hh,:ww].var(),gray[:hh,ww:].var(),gray[hh:,:ww].var(),gray[hh:,ww:].var()]
        sym=1.0-(max(q)-min(q))/(max(q)+1e-5)
        fft_s=np.fft.fftshift(np.abs(np.fft.fft2(gray))); hf,wf=fft_s.shape
        cm=np.zeros_like(fft_s,dtype=bool); cm[hf//2-22:hf//2+22,wf//2-22:wf//2+22]=True
        has_grid=float(np.percentile(fft_s[~cm],99))>float(np.mean(fft_s[~cm]))*14
        hist=np.histogram(gray,bins=64,range=(0,255))[0]; hn=hist/hist.sum(); hn=hn[hn>0]
        ent=float(-np.sum(hn*np.log2(hn)))
        flat=arr.reshape(-1,3); rounded=(flat//32*32).astype(int)
        uniq,counts=np.unique(rounded,axis=0,return_counts=True)
        palette=[tuple(int(x) for x in uniq[i]) for i in np.argsort(-counts)[:8]]
        skin=(r>95)&(g>40)&(bc>20)&(r>g)&(r>bc)&((r-g)>15); sp=float(skin.mean())
        warm=mr>mb+15; cool=mb>mr+15
        shapes=[]
        if sym>0.78: shapes.append("Alta Simetria")
        if has_grid: shapes.append("Grade/Periódico")
        if ei>32: shapes.append("Contornos Nítidos")
        if not shapes: shapes.append("Irregular")
        if sp>0.15 and mr>140: cat,kw,mat,obj="Histopatologia H&E","hematoxylin eosin staining histopathology","Tecido Biológico","Amostra Histopatológica"
        elif has_grid and ei>18: cat,kw,mat,obj="Cristalografia / Difração","X-ray diffraction crystallography TEM","Material Cristalino","Rede Cristalina"
        elif mg>165 and mr<125: cat,kw,mat,obj="Fluorescência GFP/FITC","GFP fluorescence confocal microscopy","Proteínas Fluorescentes","Células Marcadas"
        elif mb>165 and mr<110: cat,kw,mat,obj="Fluorescência DAPI","DAPI nuclear staining DNA","DNA / Cromatina","Núcleos Celulares"
        elif ei>40: cat,kw,mat,obj="Diagrama Científico","scientific visualization chart diagram","Dados","Gráfico"
        elif sym>0.82: cat,kw,mat,obj="Estrutura Molecular","molecular structure protein crystal symmetry","Moléculas","Estrutura Molecular"
        else:
            temp="quente" if warm else("fria" if cool else "neutra")
            cat,kw,mat,obj="Imagem Científica",f"scientific image research microscopy {temp}","Variado","Imagem"
        conf=min(96,48+ei/2+ent*2.8+sym*5+(8 if sp>0.1 else 0)+(6 if has_grid else 0))
        rh=np.histogram(r.ravel(),bins=32,range=(0,255))[0].tolist()
        gh=np.histogram(g.ravel(),bins=32,range=(0,255))[0].tolist()
        bh=np.histogram(bc.ravel(),bins=32,range=(0,255))[0].tolist()
        return {"category":cat,"kw":kw,"material":mat,"object_type":obj,"confidence":round(conf,1),"shapes":shapes,"symmetry":round(sym,3),"color":{"r":round(mr,1),"g":round(mg,1),"b":round(mb,1),"warm":warm,"cool":cool},"texture":{"entropy":round(ent,3),"complexity":"Alta" if ent>5.5 else("Média" if ent>4 else "Baixa")},"palette":palette,"size":orig,"histograms":{"r":rh,"g":gh,"b":bh},"brightness":round(float(gray.mean()),1),"sharpness":round(ei,2),"edge_intensity":ei}
    except Exception as e: st.error(f"Erro: {e}"); return None

EMAP={"pdf":"PDF","docx":"Word","doc":"Word","xlsx":"Planilha","xls":"Planilha","csv":"Dados","txt":"Texto","py":"Código Python","r":"Código R","ipynb":"Notebook","pptx":"Apresentação","png":"Imagem","jpg":"Imagem","jpeg":"Imagem","tiff":"Imagem Científica","md":"Markdown"}
def ftype(fname): return EMAP.get(fname.split(".")[-1].lower() if "." in fname else "","Arquivo")

@st.cache_data(show_spinner=False)
def search_ss(q,lim=6):
    try:
        r=requests.get("https://api.semanticscholar.org/graph/v1/paper/search",params={"query":q,"limit":lim,"fields":"title,authors,year,abstract,venue,externalIds,openAccessPdf,citationCount"},timeout=8)
        if r.status_code==200:
            out=[]
            for p in r.json().get("data",[]):
                ext=p.get("externalIds",{}) or {}; doi=ext.get("DOI",""); arx=ext.get("ArXiv","")
                pdf=p.get("openAccessPdf") or {}
                link=pdf.get("url","") or(f"https://arxiv.org/abs/{arx}" if arx else(f"https://doi.org/{doi}" if doi else ""))
                al=p.get("authors",[]) or []; au=", ".join(a.get("name","") for a in al[:3])
                if len(al)>3: au+=" et al."
                out.append({"title":p.get("title","Sem título"),"authors":au or "—","year":p.get("year","?"),"source":p.get("venue","") or "Semantic Scholar","doi":doi or arx or "—","abstract":(p.get("abstract","") or "")[:250],"url":link,"citations":p.get("citationCount",0),"origin":"semantic"})
            return out
    except: pass
    return []

@st.cache_data(show_spinner=False)
def search_cr(q,lim=4):
    try:
        r=requests.get("https://api.crossref.org/works",params={"query":q,"rows":lim,"select":"title,author,issued,abstract,DOI,container-title,is-referenced-by-count","mailto":"nebula@example.com"},timeout=8)
        if r.status_code==200:
            out=[]
            for p in r.json().get("message",{}).get("items",[]):
                title=(p.get("title") or ["Sem título"])[0]; ars=p.get("author",[]) or []
                au=", ".join(f'{a.get("given","").split()[0] if a.get("given") else ""} {a.get("family","")}'.strip() for a in ars[:3])
                if len(ars)>3: au+=" et al."
                yr=(p.get("issued",{}).get("date-parts") or [[None]])[0][0]; doi=p.get("DOI","")
                ab=re.sub(r'<[^>]+>','',p.get("abstract","") or "")[:250]
                out.append({"title":title,"authors":au or "—","year":yr or "?","source":(p.get("container-title") or ["CrossRef"])[0],"doi":doi,"abstract":ab,"url":f"https://doi.org/{doi}" if doi else "","citations":p.get("is-referenced-by-count",0),"origin":"crossref"})
            return out
    except: pass
    return []

def record(tags,w=1.0):
    e=st.session_state.get("current_user")
    if not e or not tags: return
    p=st.session_state.user_prefs.setdefault(e,defaultdict(float))
    for t in tags: p[t.lower()]+=w
    db.save()

@st.cache_data(show_spinner=False)
def get_recs(email,posts_data,n=2):
    pr=st.session_state.user_prefs.get(email,{})
    if not pr: return []
    def sc(p): return sum(pr.get(t.lower(),0) for t in p.get("tags",[])+p.get("connections",[]))
    scored=[(sc(p),p) for p in posts_data if email not in p.get("liked_by",[])]
    return [p for s,p in sorted(scored,key=lambda x:-x[0]) if s>0][:n]

@st.cache_data(show_spinner=False)
def area_tags(area):
    a=(area or "").lower()
    M={"ia":["machine learning","LLM"],"inteligência artificial":["machine learning","LLM"],"neurociência":["sono","memória","cognição"],"biologia":["célula","genômica"],"física":["quantum","astrofísica"],"medicina":["diagnóstico","terapia"],"astronomia":["cosmologia","galáxia"],"computação":["algoritmo","redes"],"psicologia":["cognição","comportamento"],"genômica":["DNA","CRISPR"]}
    for k,v in M.items():
        if k in a: return v
    return [w.strip() for w in a.replace(","," ").split() if len(w)>3][:5]

# ═══════════════════════════════════════════════════════════
#  CSS — DARK LIQUID GLASS · VIBRANT COLORS · MODERN
# ═══════════════════════════════════════════════════════════
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800;900&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');

:root {
  /* ── Base ── */
  --bg:   #07080F;
  --bg2:  #0D0E1A;
  --bg3:  #141528;

  /* ── Accent Colors ── */
  --yel: #FFD60A;   /* Amarelo vibrante */
  --yel2:#FFEC47;
  --grn: #06D6A0;   /* Verde menta */
  --grn2:#00F5C4;
  --red: #FF3B5C;   /* Vermelho vivo */
  --red2:#FF6B81;
  --blu: #4CC9F0;   /* Azul elétrico */
  --blu2:#7BD3FF;
  --pur: #B17DFF;   /* Roxo accent */
  --orn: #FF8C42;   /* Laranja */

  /* ── Text ── */
  --t0: #FFFFFF;
  --t1: #E8E9F0;
  --t2: #A8ABBE;
  --t3: #6B6F88;
  --t4: #404460;

  /* ── Glass ── */
  --g1:  rgba(255,255,255,0.06);
  --g2:  rgba(255,255,255,0.09);
  --g3:  rgba(255,255,255,0.13);
  --gb1: rgba(255,255,255,0.08);
  --gb2: rgba(255,255,255,0.14);
  --gb3: rgba(255,255,255,0.22);

  /* ── Glow colors ── */
  --gy:  rgba(255,214,10,.18);
  --gg:  rgba(6,214,160,.16);
  --gr2: rgba(255,59,92,.16);
  --gb4: rgba(76,201,240,.16);

  --r8:8px; --r12:12px; --r16:16px; --r20:20px; --r28:28px;
}

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

html,body,.stApp{
  background:var(--bg) !important;
  color:var(--t1) !important;
  font-family:'DM Sans',-apple-system,sans-serif !important;
}

/* ── Ambient background ── */
.stApp::before{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:
    radial-gradient(ellipse 60% 50% at -5% 0%,  rgba(255,214,10,.07) 0%,transparent 60%),
    radial-gradient(ellipse 50% 40% at 105% 0%,  rgba(76,201,240,.07) 0%,transparent 55%),
    radial-gradient(ellipse 40% 50% at 50% 110%, rgba(6,214,160,.06) 0%,transparent 60%),
    radial-gradient(ellipse 30% 30% at 30% 60%,  rgba(177,125,255,.04) 0%,transparent 50%);
}
/* ── Grid noise ── */
.stApp::after{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:linear-gradient(rgba(255,255,255,.012) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.012) 1px,transparent 1px);
  background-size:60px 60px;
}

header[data-testid="stHeader"]{display:none!important}
#MainMenu,footer,.stDeployButton,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
[data-testid="collapsedControl"]{display:none!important}
[data-testid="stSidebarCollapseButton"]{display:none!important}

.block-container{
  padding-top:0!important;padding-bottom:4rem!important;
  max-width:1380px!important;position:relative;z-index:1;
  padding-left:.75rem!important;padding-right:.75rem!important;
}

/* ══════════════ SIDEBAR ══════════════ */
section[data-testid="stSidebar"]{
  background:rgba(10,11,20,0.96)!important;
  backdrop-filter:blur(40px) saturate(180%)!important;
  -webkit-backdrop-filter:blur(40px) saturate(180%)!important;
  border-right:1px solid rgba(255,255,255,.1)!important;
  box-shadow:2px 0 40px rgba(0,0,0,.6),inset -1px 0 0 rgba(255,255,255,.04)!important;
  width:220px!important;min-width:220px!important;max-width:220px!important;
  padding:1.4rem .9rem 1rem!important;
  visibility:visible!important;transform:none!important;
  transition:none!important;
}
section[data-testid="stSidebar"] > div{
  width:220px!important;padding:0!important;overflow-y:auto;overflow-x:hidden;
}
/* Force main content to have margin for sidebar */
.main .block-container{
  padding-left:.75rem!important;
}

/* ── Sidebar logo ── */
.sb-logo{
  display:flex;align-items:center;gap:10px;
  margin-bottom:1.8rem;padding:.3rem .4rem;
}
.sb-logo-icon{
  width:36px;height:36px;border-radius:10px;
  background:linear-gradient(135deg,var(--yel),var(--orn));
  display:flex;align-items:center;justify-content:center;
  font-size:1rem;flex-shrink:0;
  box-shadow:0 0 16px var(--gy),inset 0 1px 0 rgba(255,255,255,.25);
}
.sb-logo-text{
  font-family:'Syne',sans-serif;font-weight:900;font-size:1.25rem;
  letter-spacing:-.04em;
  background:linear-gradient(135deg,var(--yel),var(--grn));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}

/* ── Sidebar section label ── */
.sb-label{
  font-size:.57rem;font-weight:700;color:var(--t4);
  letter-spacing:.14em;text-transform:uppercase;
  padding:0 .5rem;margin-bottom:.45rem;margin-top:1rem;
}

/* ── Nav pills ── */
.snav .stButton>button{
  background:rgba(255,255,255,.04)!important;
  border:1px solid rgba(255,255,255,.07)!important;
  border-radius:var(--r12)!important;
  color:var(--t2)!important;
  font-family:'DM Sans',sans-serif!important;font-weight:500!important;font-size:.86rem!important;
  padding:.54rem .85rem!important;
  width:100%!important;display:flex!important;align-items:center!important;gap:.65rem!important;
  text-align:left!important;justify-content:flex-start!important;
  transition:all .15s!important;box-shadow:none!important;
  height:auto!important;min-height:auto!important;margin-bottom:.22rem!important;
  letter-spacing:.005em!important;
}
.snav .stButton>button:hover{
  background:rgba(255,255,255,.08)!important;border-color:rgba(255,255,255,.14)!important;
  color:var(--t1)!important;transform:none!important;box-shadow:none!important;
}
.snav-a .stButton>button{
  border:1px solid var(--gb2)!important;
  color:var(--t0)!important;font-weight:600!important;
  box-shadow:none!important;
}
.snav-a.yel .stButton>button{color:var(--yel)!important;border-color:rgba(255,214,10,.35)!important;background:rgba(255,214,10,.12)!important;box-shadow:0 0 12px rgba(255,214,10,.08)!important;}
.snav-a.grn .stButton>button{color:var(--grn)!important;border-color:rgba(6,214,160,.35)!important;background:rgba(6,214,160,.12)!important;box-shadow:0 0 12px rgba(6,214,160,.08)!important;}
.snav-a.blu .stButton>button{color:var(--blu)!important;border-color:rgba(76,201,240,.35)!important;background:rgba(76,201,240,.12)!important;box-shadow:0 0 12px rgba(76,201,240,.08)!important;}
.snav-a.red .stButton>button{color:var(--red)!important;border-color:rgba(255,59,92,.35)!important;background:rgba(255,59,92,.12)!important;box-shadow:0 0 12px rgba(255,59,92,.08)!important;}
.snav-a.pur .stButton>button{color:var(--pur)!important;border-color:rgba(177,125,255,.35)!important;background:rgba(177,125,255,.12)!important;box-shadow:0 0 12px rgba(177,125,255,.08)!important;}
.snav-a.orn .stButton>button{color:var(--orn)!important;border-color:rgba(255,140,66,.35)!important;background:rgba(255,140,66,.12)!important;box-shadow:0 0 12px rgba(255,140,66,.08)!important;}

/* ── Sidebar avatar ── */
.sb-user{display:flex;align-items:center;gap:9px;padding:.55rem .5rem;margin-top:auto;}
.sb-av-btn .stButton>button{
  width:36px!important;height:36px!important;min-height:36px!important;
  border-radius:50%!important;padding:0!important;
  font-family:'Syne',sans-serif!important;font-weight:800!important;font-size:.75rem!important;
  color:white!important;border:1.5px solid rgba(255,255,255,.12)!important;
  box-shadow:0 2px 12px rgba(0,0,0,.3)!important;transition:transform .18s!important;
  height:36px!important;min-height:36px!important;
}
.sb-av-btn .stButton>button:hover{transform:scale(1.08)!important;border-color:var(--gb2)!important;}

/* ══════════════ GLOBAL BUTTONS ══════════════ */
.stButton>button{
  background:rgba(255,255,255,.06)!important;
  backdrop-filter:blur(20px) saturate(180%)!important;
  -webkit-backdrop-filter:blur(20px) saturate(180%)!important;
  border:1px solid rgba(255,255,255,.11)!important;
  border-radius:var(--r12)!important;
  color:var(--t2)!important;
  font-family:'DM Sans',sans-serif!important;
  font-weight:500!important;font-size:.80rem!important;
  padding:.44rem .88rem!important;
  transition:background .14s,border-color .14s,color .14s,box-shadow .14s!important;
  box-shadow:0 1px 0 rgba(255,255,255,.04) inset,0 2px 12px rgba(0,0,0,.2)!important;
  letter-spacing:.01em!important;
}
.stButton>button:hover{
  background:rgba(255,255,255,.10)!important;
  border-color:rgba(255,255,255,.18)!important;
  color:var(--t0)!important;
  transform:translateY(-1px)!important;
  box-shadow:0 1px 0 rgba(255,255,255,.07) inset,0 4px 18px rgba(0,0,0,.3)!important;
}
.stButton>button:active{transform:translateY(0) scale(.98)!important;}

/* Yellow CTA */
.btn-yel .stButton>button{
  background:linear-gradient(135deg,rgba(255,214,10,.25),rgba(255,171,0,.18))!important;
  border:1px solid rgba(255,214,10,.4)!important;
  color:var(--yel)!important;font-weight:700!important;
  box-shadow:0 1px 0 rgba(255,255,255,.12) inset,0 4px 20px rgba(255,214,10,.12)!important;
  text-shadow:0 0 20px rgba(255,214,10,.3)!important;
}
.btn-yel .stButton>button:hover{
  background:linear-gradient(135deg,rgba(255,214,10,.35),rgba(255,171,0,.25))!important;
  border-color:rgba(255,214,10,.6)!important;
  box-shadow:0 1px 0 rgba(255,255,255,.15) inset,0 6px 28px rgba(255,214,10,.2)!important;
}

/* Green */
.btn-grn .stButton>button{
  background:linear-gradient(135deg,rgba(6,214,160,.22),rgba(0,179,137,.15))!important;
  border:1px solid rgba(6,214,160,.38)!important;
  color:var(--grn)!important;font-weight:700!important;
  box-shadow:0 1px 0 rgba(255,255,255,.10) inset,0 4px 20px rgba(6,214,160,.10)!important;
}
.btn-grn .stButton>button:hover{
  background:linear-gradient(135deg,rgba(6,214,160,.32),rgba(0,179,137,.22))!important;
  border-color:rgba(6,214,160,.55)!important;
  box-shadow:0 1px 0 rgba(255,255,255,.12) inset,0 6px 28px rgba(6,214,160,.18)!important;
}

/* Red */
.btn-red .stButton>button{
  background:rgba(255,59,92,.12)!important;
  border:1px solid rgba(255,59,92,.3)!important;
  color:var(--red)!important;font-weight:600!important;
  box-shadow:0 1px 0 rgba(255,255,255,.04) inset!important;
}
.btn-red .stButton>button:hover{
  background:rgba(255,59,92,.20)!important;
  border-color:rgba(255,59,92,.5)!important;
  box-shadow:0 4px 18px rgba(255,59,92,.15)!important;
}

/* Blue */
.btn-blu .stButton>button{
  background:rgba(76,201,240,.12)!important;
  border:1px solid rgba(76,201,240,.28)!important;
  color:var(--blu)!important;font-weight:600!important;
}
.btn-blu .stButton>button:hover{
  background:rgba(76,201,240,.20)!important;
  border-color:rgba(76,201,240,.45)!important;
  box-shadow:0 4px 18px rgba(76,201,240,.12)!important;
}

/* Ghost compose */
.btn-ghost .stButton>button{
  background:rgba(255,255,255,.03)!important;
  border:1px solid rgba(255,255,255,.08)!important;
  border-radius:50px!important;color:var(--t4)!important;font-size:.88rem!important;
  text-align:left!important;padding:.72rem 1.4rem!important;
  justify-content:flex-start!important;
  box-shadow:0 1px 0 rgba(255,255,255,.03) inset!important;
}
.btn-ghost .stButton>button:hover{
  background:rgba(255,255,255,.06)!important;
  border-color:rgba(255,255,255,.12)!important;
  color:var(--t2)!important;transform:none!important;
}

/* ══════════════ INPUTS ══════════════ */
.stTextInput input,.stTextArea textarea{
  background:rgba(255,255,255,.04)!important;
  border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;
  color:var(--t1)!important;font-family:'DM Sans',sans-serif!important;font-size:.84rem!important;
  transition:border-color .15s,box-shadow .15s!important;
}
.stTextInput input:focus,.stTextArea textarea:focus{
  border-color:rgba(255,214,10,.4)!important;
  box-shadow:0 0 0 3px rgba(255,214,10,.08)!important;
}
.stTextInput label,.stTextArea label,.stSelectbox label,.stFileUploader label,.stNumberInput label{
  color:var(--t3)!important;font-size:.60rem!important;letter-spacing:.10em!important;
  text-transform:uppercase!important;font-weight:600!important;
}

/* ══════════════ CARDS ══════════════ */
.glass{
  background:rgba(255,255,255,.055);
  backdrop-filter:blur(32px) saturate(180%);
  -webkit-backdrop-filter:blur(32px) saturate(180%);
  border:1px solid rgba(255,255,255,.10);
  border-radius:var(--r20);
  box-shadow:0 0 0 1px rgba(255,255,255,.04) inset,0 4px 32px rgba(0,0,0,.3);
  position:relative;overflow:hidden;
}
.glass::before{
  content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.08),transparent);
  pointer-events:none;
}
.post-card{
  background:rgba(255,255,255,.05);
  border:1px solid rgba(255,255,255,.09);
  border-radius:var(--r20);
  margin-bottom:.65rem;overflow:hidden;position:relative;
  box-shadow:0 0 0 1px rgba(255,255,255,.03) inset,0 2px 20px rgba(0,0,0,.25);
  transition:border-color .14s,box-shadow .14s,transform .14s;
  will-change:transform;
}
.post-card:hover{
  border-color:rgba(255,255,255,.15);
  box-shadow:0 0 0 1px rgba(255,255,255,.05) inset,0 8px 30px rgba(0,0,0,.35);
  transform:translateY(-1px);
}
.post-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.05),transparent);pointer-events:none;}

.sc{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.09);border-radius:var(--r20);padding:.9rem 1rem;margin-bottom:.6rem;}
.scard{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:var(--r16);padding:.8rem 1rem;margin-bottom:.42rem;transition:border-color .13s,transform .13s;will-change:transform;}
.scard:hover{border-color:rgba(255,255,255,.14);transform:translateY(-1px);}
.mbox{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.09);border-radius:var(--r16);padding:.9rem;text-align:center;}
.abox{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.10);border-radius:var(--r16);padding:1rem;margin-bottom:.6rem;}
.pbox-grn{background:rgba(6,214,160,.07);border:1px solid rgba(6,214,160,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.55rem;}
.pbox-yel{background:rgba(255,214,10,.07);border:1px solid rgba(255,214,10,.18);border-radius:var(--r12);padding:.85rem;margin-bottom:.55rem;}
.chart-wrap{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);border-radius:var(--r12);padding:.65rem;margin-bottom:.6rem;}
.ref-item{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:var(--r12);padding:.5rem .8rem;font-size:.74rem;color:var(--t2);line-height:1.6;margin-bottom:.28rem;}

/* Compose */
.compose-box{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.11);border-radius:var(--r20);padding:1.1rem 1.3rem;margin-bottom:.8rem;}

/* ══════════════ METRICS ══════════════ */
.mval-yel{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;background:linear-gradient(135deg,var(--yel),var(--orn));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-grn{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;background:linear-gradient(135deg,var(--grn),var(--blu));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-blu{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;background:linear-gradient(135deg,var(--blu),var(--pur));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-red{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:900;background:linear-gradient(135deg,var(--red),var(--orn));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mlbl{font-size:.58rem;color:var(--t3);margin-top:4px;letter-spacing:.1em;text-transform:uppercase;font-weight:700;}

/* ══════════════ BADGES / TAGS ══════════════ */
.tag{display:inline-block;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.09);border-radius:50px;padding:2px 9px;font-size:.63rem;color:var(--t2);margin:2px;font-weight:500;}
.badge-yel{display:inline-block;background:rgba(255,214,10,.12);border:1px solid rgba(255,214,10,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--yel);}
.badge-grn{display:inline-block;background:rgba(6,214,160,.12);border:1px solid rgba(6,214,160,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--grn);}
.badge-red{display:inline-block;background:rgba(255,59,92,.12);border:1px solid rgba(255,59,92,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--red);}
.badge-blu{display:inline-block;background:rgba(76,201,240,.12);border:1px solid rgba(76,201,240,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--blu);}
.badge-pur{display:inline-block;background:rgba(177,125,255,.12);border:1px solid rgba(177,125,255,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--pur);}
.badge-orn{display:inline-block;background:rgba(255,140,66,.12);border:1px solid rgba(255,140,66,.25);border-radius:50px;padding:2px 9px;font-size:.63rem;font-weight:700;color:var(--orn);}

/* ══════════════ INDICATORS ══════════════ */
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.45;transform:scale(.7)}}
.dot-on{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--grn);animation:pulse 2.5s infinite;margin-right:4px;vertical-align:middle;}
.dot-off{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--t4);margin-right:4px;vertical-align:middle;}

/* ══════════════ ANIMATIONS ══════════════ */
@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.pw{animation:fadeUp .18s ease both;}

/* ══════════════ CHAT ══════════════ */
.bme{background:linear-gradient(135deg,rgba(255,214,10,.15),rgba(255,140,66,.1));border:1px solid rgba(255,214,10,.2);border-radius:18px 18px 4px 18px;padding:.55rem .88rem;max-width:70%;margin-left:auto;margin-bottom:5px;font-size:.82rem;line-height:1.6;}
.bthem{background:var(--g2);border:1px solid var(--gb1);border-radius:18px 18px 18px 4px;padding:.55rem .88rem;max-width:70%;margin-bottom:5px;font-size:.82rem;line-height:1.6;}
.cmt{background:rgba(255,255,255,.03);border:1px solid var(--gb1);border-radius:var(--r12);padding:.5rem .85rem;margin-bottom:.25rem;}

/* ══════════════ TABS ══════════════ */
.stTabs [data-baseweb="tab-list"]{background:rgba(255,255,255,.03)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;padding:3px!important;gap:2px!important;}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--t3)!important;border-radius:9px!important;font-size:.75rem!important;font-family:'DM Sans',sans-serif!important;font-weight:500!important;}
.stTabs [aria-selected="true"]{background:var(--g3)!important;color:var(--yel)!important;border:1px solid rgba(255,214,10,.2)!important;font-weight:700!important;}
.stTabs [data-baseweb="tab-panel"]{background:transparent!important;padding-top:.8rem!important;}

/* ══════════════ PROFILE ══════════════ */
.prof-hero{background:var(--g1);backdrop-filter:blur(32px);-webkit-backdrop-filter:blur(32px);border:1px solid var(--gb1);border-radius:var(--r28);padding:1.6rem;display:flex;gap:1.2rem;align-items:flex-start;box-shadow:0 6px 40px rgba(0,0,0,.35);margin-bottom:1rem;overflow:hidden;position:relative;}
.prof-hero::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.07),transparent);pointer-events:none;}
.prof-av{width:76px;height:76px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:'Syne',sans-serif;font-weight:800;font-size:1.6rem;color:white;flex-shrink:0;border:2px solid rgba(255,255,255,.12);box-shadow:0 4px 20px rgba(0,0,0,.3);}

/* ══════════════ MISC ══════════════ */
hr{border:none;border-top:1px solid var(--gb1)!important;margin:.8rem 0;}
.stAlert{background:var(--g1)!important;border:1px solid var(--gb1)!important;border-radius:var(--r16)!important;}
.stSelectbox [data-baseweb="select"]{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;}
.stFileUploader section{background:rgba(255,255,255,.03)!important;border:1.5px dashed var(--gb2)!important;border-radius:var(--r16)!important;}
.stExpander{background:var(--g1);border:1px solid var(--gb1);border-radius:var(--r16);}
.stRadio>div{display:flex!important;gap:4px!important;flex-wrap:wrap!important;}
.stRadio>div>label{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:50px!important;padding:.28rem .78rem!important;font-size:.74rem!important;cursor:pointer!important;color:var(--t2)!important;}
.stRadio>div>label:hover{border-color:var(--gb2)!important;color:var(--t1)!important;}
input[type="number"]{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;color:var(--t1)!important;}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-thumb{background:var(--t4);border-radius:4px;}
.js-plotly-plot .plotly .modebar{display:none!important;}
.dtxt{display:flex;align-items:center;gap:.7rem;margin:.75rem 0;font-size:.58rem;color:var(--t3);letter-spacing:.10em;text-transform:uppercase;font-weight:700;}
.dtxt::before,.dtxt::after{content:'';flex:1;height:1px;background:var(--gb1);}
h1{font-family:'Syne',sans-serif!important;font-size:1.55rem!important;font-weight:800!important;letter-spacing:-.03em;color:var(--t0)!important;}
h2{font-family:'Syne',sans-serif!important;font-size:1rem!important;font-weight:700!important;color:var(--t0)!important;}
h3{font-family:'DM Sans',sans-serif!important;font-size:.88rem!important;font-weight:600!important;color:var(--t1)!important;}
label{color:var(--t2)!important;}
.stCheckbox label,.stRadio label{color:var(--t1)!important;}
</style>""", unsafe_allow_html=True)

# ════════════ HTML HELPERS ════════════
def avh(initials,sz=40,grad=None):
    fs=max(sz//3,9); bg=grad or "linear-gradient(135deg,#FFD60A,#FF8C42)"
    return f'<div style="width:{sz}px;height:{sz}px;border-radius:50%;background:{bg};display:flex;align-items:center;justify-content:center;font-family:Syne,sans-serif;font-weight:800;font-size:{fs}px;color:white;flex-shrink:0;border:1.5px solid rgba(255,255,255,.12);box-shadow:0 2px 10px rgba(0,0,0,.3)">{initials}</div>'

def tags_html(tags): return ' '.join(f'<span class="tag">{t}</span>' for t in(tags or []))

def badge(s):
    m={"Publicado":"badge-grn","Concluído":"badge-pur"}
    return f'<span class="{m.get(s,"badge-yel")}">{s}</span>'

def pc_dark():
    return dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#6B6F88",family="DM Sans",size=11),
                margin=dict(l=10,r=10,t=38,b=10),
                xaxis=dict(showgrid=False,color="#6B6F88",tickfont=dict(size=10)),
                yaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,.04)",color="#6B6F88",tickfont=dict(size=10)))

@st.cache_data(show_spinner=False)
def get_utags(ue,area,posts_tuple):
    tags=set(area_tags(area))
    for pe in posts_tuple:
        if pe[0]==ue: tags.update(t.lower() for t in pe[1])
    return frozenset(tags)

VIB=["#FFD60A","#06D6A0","#FF3B5C","#4CC9F0","#B17DFF","#FF8C42","#FF4E8A","#00C9A7","#FFAB00","#7BD3FF"]

# ════════════ AUTH ════════════
def page_login():
    _,col,_=st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
<div style="text-align:center;margin-bottom:2.8rem">
  <div style="display:flex;align-items:center;justify-content:center;gap:12px;margin-bottom:.8rem">
    <div style="width:48px;height:48px;border-radius:14px;background:linear-gradient(135deg,#FFD60A,#FF8C42);display:flex;align-items:center;justify-content:center;font-size:1.4rem;box-shadow:0 0 24px rgba(255,214,10,.3)">🔬</div>
    <div style="font-family:Syne,sans-serif;font-size:2.6rem;font-weight:900;letter-spacing:-.06em;background:linear-gradient(135deg,#FFD60A,#06D6A0);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">Nebula</div>
  </div>
  <div style="color:var(--t3);font-size:.60rem;letter-spacing:.26em;text-transform:uppercase;font-weight:700">Rede do Conhecimento Científico</div>
</div>""", unsafe_allow_html=True)
        ti,tu=st.tabs(["  🔑 Entrar  ","  ✨ Criar conta  "])
        with ti:
            with st.form("lf"):
                em=st.text_input("E-mail",placeholder="seu@email.com",key="li_e")
                pw=st.text_input("Senha",placeholder="••••••••",type="password",key="li_p")
                st.markdown('<div class="btn-yel">', unsafe_allow_html=True)
                s=st.form_submit_button("→  Entrar",use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                if s:
                    u=st.session_state.users.get(em)
                    if not u: st.error("E-mail não encontrado.")
                    elif u["password"]!=hp(pw): st.error("Senha incorreta.")
                    elif u.get("2fa_enabled"):
                        c=code6(); st.session_state.pending_2fa={"email":em,"code":c}; st.session_state.page="2fa"; st.rerun()
                    else:
                        st.session_state.logged_in=True; st.session_state.current_user=em
                        record(area_tags(u.get("area","")),1.0); st.session_state.page="feed"; st.rerun()
            st.markdown('<div style="text-align:center;color:var(--t3);font-size:.68rem;margin-top:.7rem">Demo: demo@nebula.ai / demo123</div>', unsafe_allow_html=True)
        with tu:
            with st.form("sf"):
                nn=st.text_input("Nome completo",key="su_n")
                ne=st.text_input("E-mail",key="su_e")
                na=st.text_input("Área de pesquisa",key="su_a")
                np=st.text_input("Senha",type="password",key="su_p")
                np2=st.text_input("Confirmar senha",type="password",key="su_p2")
                st.markdown('<div class="btn-grn">', unsafe_allow_html=True)
                s2=st.form_submit_button("✓  Criar conta",use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                if s2:
                    if not all([nn,ne,na,np,np2]): st.error("Preencha todos os campos.")
                    elif np!=np2: st.error("Senhas não coincidem.")
                    elif len(np)<6: st.error("Mínimo 6 caracteres.")
                    elif ne in st.session_state.users: st.error("E-mail já cadastrado.")
                    else:
                        c=code6(); st.session_state.pending_verify={"email":ne,"name":nn,"pw":hp(np),"area":na,"code":c}; st.session_state.page="verify_email"; st.rerun()

def page_verify_email():
    pv=st.session_state.pending_verify; _,col,_=st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f'<div class="glass" style="padding:2rem;text-align:center"><div style="font-size:2rem;margin-bottom:.7rem">✉️</div><h2>Verifique seu e-mail</h2><p style="color:var(--t2);font-size:.82rem;margin:.4rem 0 1rem">Código para <strong style="color:var(--yel)">{pv["email"]}</strong></p><div style="background:rgba(255,255,255,.04);border:1px solid var(--gb1);border-radius:12px;padding:1rem;margin-bottom:1rem"><div style="font-size:.57rem;color:var(--t3);text-transform:uppercase;letter-spacing:.12em;margin-bottom:5px;font-weight:700">Código (demo)</div><div style="font-family:Syne,sans-serif;font-size:2.4rem;font-weight:900;letter-spacing:.28em;color:var(--yel)">{pv["code"]}</div></div></div>', unsafe_allow_html=True)
        with st.form("vf"):
            typed=st.text_input("Código",max_chars=6,key="ev_c")
            st.markdown('<div class="btn-yel">', unsafe_allow_html=True)
            s=st.form_submit_button("✓  Verificar",use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if s:
                if typed.strip()==pv["code"]:
                    st.session_state.users[pv["email"]]={"name":pv["name"],"password":pv["pw"],"bio":"","area":pv["area"],"followers":0,"following":0,"verified":True,"2fa_enabled":False}
                    db.save(); st.session_state.pending_verify=None; st.session_state.logged_in=True; st.session_state.current_user=pv["email"]; record(area_tags(pv["area"]),2.0); st.session_state.page="feed"; st.rerun()
                else: st.error("Código inválido.")

def page_2fa():
    p2=st.session_state.pending_2fa; _,col,_=st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f'<div class="glass" style="padding:2rem;text-align:center"><div style="font-size:2rem;margin-bottom:.7rem">🔑</div><h2>Verificação 2FA</h2><div style="background:rgba(255,255,255,.04);border:1px solid var(--gb1);border-radius:12px;padding:.9rem;margin:1rem 0"><div style="font-family:Syne,sans-serif;font-size:2.4rem;font-weight:900;letter-spacing:.26em;color:var(--yel)">{p2["code"]}</div></div></div>', unsafe_allow_html=True)
        with st.form("2ff"):
            typed=st.text_input("Código",max_chars=6,key="fa_c",label_visibility="collapsed")
            st.markdown('<div class="btn-yel">', unsafe_allow_html=True)
            s=st.form_submit_button("✓  Verificar",use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if s:
                if typed.strip()==p2["code"]:
                    st.session_state.logged_in=True; st.session_state.current_user=p2["email"]; st.session_state.pending_2fa=None; st.session_state.page="feed"; st.rerun()
                else: st.error("Código inválido.")

# ════════════ SIDEBAR ════════════
NAV=[
    ("feed","🏠 Feed","yel"),
    ("search","🔍 Busca","blu"),
    ("knowledge","🕸 Conexões","grn"),
    ("folders","📁 Pastas","orn"),
    ("analytics","📊 Análises","pur"),
    ("img_search","🔬 Imagem","blu"),
    ("chat","💬 Chat","grn"),
    ("settings","⚙️ Config","red"),
]

def render_sidebar():
    email=st.session_state.current_user; u=guser(); name=u.get("name","?"); ini_=ini(name)
    g=ugrad(email); cur=st.session_state.page
    with st.sidebar:
        # Logo
        st.markdown('<div class="sb-logo"><div class="sb-logo-icon">🔬</div><div class="sb-logo-text">Nebula</div></div>', unsafe_allow_html=True)
        # Nav
        st.markdown('<div class="sb-label">Navegação</div>', unsafe_allow_html=True)
        for key,label,col in NAV:
            if key=="profile_self":
                is_a=(st.session_state.profile_view==email)
            else:
                is_a=(cur==key and not st.session_state.profile_view)
            cls=f"snav snav-a {col}" if is_a else "snav"
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(label,key=f"sb_{key}",use_container_width=True):
                if key=="profile_self":
                    st.session_state.profile_view=email; st.session_state.page="feed"
                else:
                    st.session_state.profile_view=None; st.session_state.page=key
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        # Divider + user
        st.markdown("<hr>", unsafe_allow_html=True)
        notif=len(st.session_state.notifications)
        nb_html=f'<div style="position:absolute;top:-3px;right:-3px;background:var(--red);color:white;width:14px;height:14px;border-radius:50%;font-size:.45rem;display:flex;align-items:center;justify-content:center;font-weight:800;border:1.5px solid var(--bg)">{notif}</div>' if notif else ""
        st.markdown(f'<div style="display:flex;align-items:center;gap:10px;padding:.3rem .2rem"><div style="position:relative">{nb_html}{avh(ini_,34,g)}</div><div style="flex:1;min-width:0"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.82rem;color:var(--t0);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{name}</div><div style="font-size:.62rem;color:var(--t3)">{u.get("area","Pesquisador")[:20]}</div></div></div>', unsafe_allow_html=True)
        st.markdown('<div class="snav">', unsafe_allow_html=True)
        if st.button("👤 Meu Perfil", key="sb_myprofile", use_container_width=True):
            st.session_state.profile_view=email; st.session_state.page="feed"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ════════════ PROFILE ════════════
def page_profile(target_email):
    tu=st.session_state.users.get(target_email,{}); email=st.session_state.current_user
    if not tu: st.error("Perfil não encontrado."); return
    tname=tu.get("name","?"); ti=ini(tname); is_me=(email==target_email)
    is_fol=target_email in st.session_state.followed; g=ugrad(target_email)
    user_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==target_email]
    liked_posts=[p for p in st.session_state.feed_posts if target_email in p.get("liked_by",[])]
    total_likes=sum(p["likes"] for p in user_posts)
    vb=f' <span class="badge-grn" style="font-size:.6rem">✓ Ver</span>' if tu.get("verified") else ""
    st.markdown(f"""
<div class="prof-hero">
  <div class="prof-av" style="background:{g}">{ti}</div>
  <div style="flex:1">
    <div style="display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:.22rem">
      <span style="font-family:Syne,sans-serif;font-weight:800;font-size:1.35rem;color:var(--t0)">{tname}</span>{vb}
    </div>
    <div style="color:var(--yel);font-size:.80rem;font-weight:600;margin-bottom:.38rem">{tu.get("area","")}</div>
    <div style="color:var(--t2);font-size:.78rem;line-height:1.7;margin-bottom:.75rem">{tu.get("bio","Sem biografia.")}</div>
    <div style="display:flex;gap:1.6rem;flex-wrap:wrap">
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1rem;color:var(--t0)">{tu.get("followers",0)}</span><span style="color:var(--t3);font-size:.68rem"> seguidores</span></div>
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1rem;color:var(--t0)">{tu.get("following",0)}</span><span style="color:var(--t3);font-size:.68rem"> seguindo</span></div>
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1rem;color:var(--t0)">{len(user_posts)}</span><span style="color:var(--t3);font-size:.68rem"> pesquisas</span></div>
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1rem;color:var(--yel)">{fmt_num(total_likes)}</span><span style="color:var(--t3);font-size:.68rem"> curtidas</span></div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)
    if not is_me:
        c1,c2,c3,_=st.columns([1,1,1,2])
        with c1:
            cls="btn-grn" if is_fol else "btn-yel"
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button("✓ Seguindo" if is_fol else "+ Seguir",key="pf_fol",use_container_width=True):
                if is_fol: st.session_state.followed.remove(target_email); tu["followers"]=max(0,tu.get("followers",0)-1)
                else: st.session_state.followed.append(target_email); tu["followers"]=tu.get("followers",0)+1
                db.save(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="btn-blu">', unsafe_allow_html=True)
            if st.button("💬 Mensagem",key="pf_chat",use_container_width=True):
                if target_email not in st.session_state.chat_messages: st.session_state.chat_messages[target_email]=[]
                st.session_state.active_chat=target_email; st.session_state.page="chat"; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c3:
            if st.button("← Voltar",key="pf_back",use_container_width=True):
                st.session_state.profile_view=None; st.rerun()
        tp,tl=st.tabs([f"  📝 Pesquisas ({len(user_posts)})  ",f"  ❤️ Curtidas ({len(liked_posts)})  "])
        with tp:
            for p in sorted(user_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="profile",show_author=False)
            if not user_posts: st.markdown('<div class="glass" style="padding:2rem;text-align:center;color:var(--t3)">Nenhuma pesquisa publicada.</div>', unsafe_allow_html=True)
        with tl:
            for p in sorted(liked_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="prof_liked",compact=True)
            if not liked_posts: st.markdown('<div class="glass" style="padding:2rem;text-align:center;color:var(--t3)">Nenhuma curtida.</div>', unsafe_allow_html=True)
    else:
        # My profile tabs
        d=st.session_state.stats_data
        saved_arts=st.session_state.saved_articles
        tm,tl,ts2,ts=st.tabs([
            "  ✏️ Meus Dados  ",
            f"  📝 Publicações ({len(user_posts)})  ",
            f"  ❤️ Curtidas ({len(liked_posts)})  ",
            f"  🔖 Salvos ({len(saved_arts)})  ",
        ])
        with tm:
            new_n=st.text_input("Nome completo",value=tu.get("name",""),key="cfg_n")
            new_a=st.text_input("Área de pesquisa",value=tu.get("area",""),key="cfg_a")
            new_b=st.text_area("Biografia",value=tu.get("bio",""),key="cfg_b",height=80)
            cs,co=st.columns(2)
            with cs:
                st.markdown('<div class="btn-yel">', unsafe_allow_html=True)
                if st.button("💾 Salvar",key="btn_sp",use_container_width=True):
                    st.session_state.users[email].update({"name":new_n,"area":new_a,"bio":new_b}); db.save(); record(area_tags(new_a),1.5); st.success("✓ Salvo!"); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with co:
                st.markdown('<div class="btn-red">', unsafe_allow_html=True)
                if st.button("🚪 Sair",key="btn_out",use_container_width=True):
                    st.session_state.logged_in=False; st.session_state.current_user=None; st.session_state.page="login"; st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('<hr>', unsafe_allow_html=True)
            with st.form("cpf"):
                op=st.text_input("Senha atual",type="password",key="op")
                np_=st.text_input("Nova senha",type="password",key="np_")
                np2=st.text_input("Confirmar",type="password",key="np2")
                if st.form_submit_button("🔑 Alterar Senha"):
                    if hp(op)!=tu.get("password",""): st.error("Senha atual incorreta.")
                    elif np_!=np2: st.error("Não coincidem.")
                    elif len(np_)<6: st.error("Mínimo 6 caracteres.")
                    else: st.session_state.users[email]["password"]=hp(np_); db.save(); st.success("✓ Alterada!")
            en=tu.get("2fa_enabled",False)
            cls2="btn-red" if en else "btn-grn"
            st.markdown(f'<div class="{cls2}">', unsafe_allow_html=True)
            if st.button("✕ Desativar 2FA" if en else "✓ Ativar 2FA",key="btn_2fa"):
                st.session_state.users[email]["2fa_enabled"]=not en; db.save(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with tl:
            if user_posts:
                for p in sorted(user_posts,key=lambda x:x.get("date",""),reverse=True):
                    render_post(p,ctx="myp",show_author=False)
            else:
                st.markdown('<div class="glass" style="padding:2.5rem;text-align:center;color:var(--t3)"><div style="font-size:1.8rem;opacity:.2;margin-bottom:.5rem">📝</div>Nenhuma pesquisa publicada ainda.</div>', unsafe_allow_html=True)
        with ts2:
            if liked_posts:
                for p in sorted(liked_posts,key=lambda x:x.get("date",""),reverse=True):
                    render_post(p,ctx="mylk",compact=True)
            else:
                st.markdown('<div class="glass" style="padding:2.5rem;text-align:center;color:var(--t3)"><div style="font-size:1.8rem;opacity:.2;margin-bottom:.5rem">❤️</div>Nenhuma curtida ainda.</div>', unsafe_allow_html=True)
        with ts:
            if saved_arts:
                for idx,a in enumerate(saved_arts):
                    render_article(a,idx=idx+3000,ctx="saved")
                    uid2=re.sub(r'[^a-zA-Z0-9]','',f"rms_{a.get('doi','nd')}_{idx}")[:30]
                    st.markdown('<div class="btn-red">', unsafe_allow_html=True)
                    if st.button("🗑 Remover",key=f"rm_sa_{uid2}"):
                        st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]
                        db.save(); st.toast("Removido!"); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="glass" style="padding:2.5rem;text-align:center;color:var(--t3)"><div style="font-size:1.8rem;opacity:.2;margin-bottom:.5rem">🔖</div>Nenhum artigo salvo ainda.<br><span style="font-size:.72rem">Use a busca acadêmica para salvar artigos.</span></div>', unsafe_allow_html=True)

# ════════════ POST ════════════
def render_post(post,ctx="feed",show_author=True,compact=False):
    email=st.session_state.current_user; pid=post["id"]
    liked=email in post.get("liked_by",[]); saved=email in post.get("saved_by",[])
    aemail=post.get("author_email",""); ain=post.get("avatar","??"); aname=post.get("author","?")
    g=ugrad(aemail); dt=time_ago(post.get("date","")); views=post.get("views",200)
    ab=post.get("abstract","")
    if compact and len(ab)>200: ab=ab[:200]+"…"
    if show_author:
        hdr=(f'<div style="padding:.8rem 1.1rem .55rem;display:flex;align-items:center;gap:9px;border-bottom:1px solid rgba(255,255,255,.04)">'
             f'{avh(ain,38,g)}<div style="flex:1;min-width:0">'
             f'<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.85rem;color:var(--t0)">{aname}{"  ✓" if st.session_state.users.get(aemail,{}).get("verified") else ""}</div>'
             f'<div style="color:var(--t3);font-size:.63rem">{post.get("area","")} · {dt}</div>'
             f'</div>{badge(post["status"])}</div>')
    else:
        hdr=f'<div style="padding:.35rem 1.1rem .15rem;display:flex;justify-content:space-between;align-items:center"><span style="color:var(--t3);font-size:.63rem">{dt}</span>{badge(post["status"])}</div>'
    st.markdown(f'<div class="post-card">{hdr}<div style="padding:.65rem 1.1rem"><div style="font-family:Syne,sans-serif;font-size:.96rem;font-weight:700;margin-bottom:.32rem;line-height:1.35;color:var(--t0)">{post["title"]}</div><div style="color:var(--t2);font-size:.79rem;line-height:1.65;margin-bottom:.5rem">{ab}</div><div>{tags_html(post.get("tags",[]))}</div></div></div>', unsafe_allow_html=True)
    heart="❤️" if liked else "🤍"; book="🔖" if saved else "📌"; nc=len(post.get("comments",[]))
    ca,cb,cc,cd,ce,cf=st.columns([1.1,1,.65,.55,1,1.1])
    with ca:
        if st.button(f"{heart} {fmt_num(post['likes'])}",key=f"lk_{ctx}_{pid}",use_container_width=True):
            if liked: post["liked_by"].remove(email); post["likes"]=max(0,post["likes"]-1)
            else: post["liked_by"].append(email); post["likes"]+=1; record(post.get("tags",[]),1.5)
            db.save(); st.rerun()
    with cb:
        if st.button(f"💬 {nc}" if nc else "💬",key=f"cm_{ctx}_{pid}",use_container_width=True):
            k=f"cmt_{ctx}_{pid}"; st.session_state[k]=not st.session_state.get(k,False); st.rerun()
    with cc:
        if st.button(book,key=f"sv_{ctx}_{pid}",use_container_width=True):
            if saved: post["saved_by"].remove(email)
            else: post["saved_by"].append(email)
            db.save(); st.rerun()
    with cd:
        if st.button("↗",key=f"sh_{ctx}_{pid}",use_container_width=True):
            k=f"shr_{ctx}_{pid}"; st.session_state[k]=not st.session_state.get(k,False); st.rerun()
    with ce:
        st.markdown(f'<div style="text-align:center;color:var(--t3);font-size:.67rem;padding:.48rem 0">👁 {fmt_num(views)}</div>', unsafe_allow_html=True)
    with cf:
        if show_author and aemail:
            if st.button(f"👤 {aname.split()[0]}",key=f"vp_{ctx}_{pid}",use_container_width=True):
                st.session_state.profile_view=aemail; st.rerun()
    if st.session_state.get(f"shr_{ctx}_{pid}",False):
        url=f"https://nebula.ai/post/{pid}"; te=post['title'][:50].replace(" ","%20")
        st.markdown(f'<div class="glass" style="padding:.8rem 1.1rem;margin-bottom:.45rem"><div style="font-weight:600;font-size:.78rem;margin-bottom:.55rem;color:var(--t2)">↗ Compartilhar</div><div style="display:flex;gap:.4rem;flex-wrap:wrap"><a href="https://twitter.com/intent/tweet?text={te}" target="_blank" style="text-decoration:none"><div style="background:rgba(29,161,242,.08);border:1px solid rgba(29,161,242,.18);border-radius:8px;padding:.3rem .65rem;font-size:.70rem;color:#1da1f2">𝕏 Twitter</div></a><a href="https://linkedin.com/sharing/share-offsite/?url={url}" target="_blank" style="text-decoration:none"><div style="background:rgba(10,102,194,.08);border:1px solid rgba(10,102,194,.18);border-radius:8px;padding:.3rem .65rem;font-size:.70rem;color:#0a66c2">in LinkedIn</div></a><a href="https://wa.me/?text={te}%20{url}" target="_blank" style="text-decoration:none"><div style="background:rgba(37,211,102,.07);border:1px solid rgba(37,211,102,.14);border-radius:8px;padding:.3rem .65rem;font-size:.70rem;color:#25d366">📱 WhatsApp</div></a></div></div>', unsafe_allow_html=True)
    if st.session_state.get(f"cmt_{ctx}_{pid}",False):
        for c in post.get("comments",[]):
            ci=ini(c["user"]); ce2=next((e for e,u in st.session_state.users.items() if u.get("name")==c["user"]),""); cg=ugrad(ce2)
            st.markdown(f'<div class="cmt"><div style="display:flex;align-items:center;gap:7px;margin-bottom:.2rem">{avh(ci,26,cg)}<span style="font-size:.73rem;font-weight:700;color:var(--yel)">{c["user"]}</span></div><div style="font-size:.78rem;color:var(--t2);line-height:1.55;padding-left:33px">{c["text"]}</div></div>', unsafe_allow_html=True)
        nc_txt=st.text_input("",placeholder="Escreva um comentário…",key=f"ci_{ctx}_{pid}",label_visibility="collapsed")
        if st.button("→ Enviar",key=f"cs_{ctx}_{pid}"):
            if nc_txt: uu=guser(); post["comments"].append({"user":uu.get("name","Você"),"text":nc_txt}); record(post.get("tags",[]),.8); db.save(); st.rerun()

# ════════════ FEED ════════════
def page_feed():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    email=st.session_state.current_user; u=guser(); uname=u.get("name","?"); uin=ini(uname); g=ugrad(email)
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    co=st.session_state.get("compose_open",False)
    cm,cs=st.columns([2,.9],gap="medium")
    with cm:
        if co:
            st.markdown(f'<div class="compose-box"><div style="display:flex;align-items:center;gap:9px;margin-bottom:.9rem">{avh(uin,40,g)}<div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.88rem;color:var(--t0)">{uname}</div><div style="font-size:.65rem;color:var(--t3)">{u.get("area","Pesquisador")}</div></div></div>', unsafe_allow_html=True)
            nt=st.text_input("Título *",key="np_t",placeholder="Título da pesquisa…")
            nab=st.text_area("Resumo *",key="np_ab",height=100,placeholder="Descreva sua pesquisa…")
            c1c,c2c=st.columns(2)
            with c1c: ntg=st.text_input("Tags (vírgula)",key="np_tg",placeholder="neurociência, IA")
            with c2c: nst=st.selectbox("Status",["Em andamento","Publicado","Concluído"],key="np_st")
            cp,cc=st.columns([2,1])
            with cp:
                st.markdown('<div class="btn-yel">', unsafe_allow_html=True)
                if st.button("🚀 Publicar",key="btn_pub",use_container_width=True):
                    if not nt or not nab: st.warning("Título e resumo obrigatórios.")
                    else:
                        tags=[t.strip() for t in ntg.split(",") if t.strip()] if ntg else []
                        np2={"id":len(st.session_state.feed_posts)+200+hash(nt)%99,"author":uname,"author_email":email,"avatar":uin,"area":u.get("area",""),"title":nt,"abstract":nab,"tags":tags,"likes":0,"comments":[],"status":nst,"date":datetime.now().strftime("%Y-%m-%d"),"liked_by":[],"saved_by":[],"connections":tags[:3],"views":1}
                        st.session_state.feed_posts.insert(0,np2); record(tags,2.0); db.save(); st.session_state.compose_open=False; st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with cc:
                if st.button("✕ Cancelar",key="btn_cc",use_container_width=True): st.session_state.compose_open=False; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            ac,bc=st.columns([.05,1],gap="small")
            with ac: st.markdown(f'<div style="padding-top:6px">{avh(uin,38,g)}</div>', unsafe_allow_html=True)
            with bc:
                st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
                if st.button(f"No que está pesquisando, {uname.split()[0]}?",key="oc",use_container_width=True):
                    st.session_state.compose_open=True; st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        ff=st.radio("",["🌐 Todos","👥 Seguidos","🔖 Salvos","🔥 Populares"],horizontal=True,key="ff",label_visibility="collapsed")
        recs=get_recs(email,st.session_state.feed_posts,2)
        if recs and "Seguidos" not in ff and "Salvos" not in ff:
            st.markdown('<div class="dtxt"><span class="badge-yel">✨ Recomendado</span></div>', unsafe_allow_html=True)
            for p in recs: render_post(p,ctx="rec",compact=True)
            st.markdown('<div class="dtxt">Mais pesquisas</div>', unsafe_allow_html=True)
        posts=list(st.session_state.feed_posts)
        if "Seguidos" in ff: posts=[p for p in posts if p.get("author_email") in st.session_state.followed]
        elif "Salvos" in ff: posts=[p for p in posts if email in p.get("saved_by",[])]
        elif "Populares" in ff: posts=sorted(posts,key=lambda p:p["likes"],reverse=True)
        else: posts=sorted(posts,key=lambda p:p.get("date",""),reverse=True)
        if not posts: st.markdown('<div class="glass" style="padding:3rem;text-align:center"><div style="font-size:2rem;opacity:.2;margin-bottom:.7rem">🔬</div><div style="color:var(--t3)">Nenhuma pesquisa aqui ainda.</div></div>', unsafe_allow_html=True)
        else:
            for p in posts: render_post(p,ctx="feed")
    with cs:
        sq=st.text_input("",placeholder="🔍 Buscar pesquisadores…",key="ppl_s",label_visibility="collapsed")
        st.markdown('<div class="sc">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.80rem;margin-bottom:.8rem;display:flex;justify-content:space-between;color:var(--t0)"><span>Quem seguir</span><span style="font-size:.62rem;color:var(--t3);font-weight:400">Sugestões</span></div>', unsafe_allow_html=True)
        sn=0
        for ue,ud in list(users.items()):
            if ue==email or sn>=5: continue
            rn=ud.get("name","?")
            if sq and sq.lower() not in rn.lower() and sq.lower() not in ud.get("area","").lower(): continue
            sn+=1; is_fol=ue in st.session_state.followed; uin_r=ini(rn); rg=ugrad(ue); online=is_online(ue)
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:.38rem 0;border-bottom:1px solid rgba(255,255,255,.04)">{avh(uin_r,30,rg)}<div style="flex:1;min-width:0"><div style="font-size:.76rem;font-weight:600;color:var(--t1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{dot}{rn}</div><div style="font-size:.60rem;color:var(--t3)">{ud.get("area","")[:20]}</div></div></div>', unsafe_allow_html=True)
            cf2,cv2=st.columns(2)
            with cf2:
                cls="btn-grn" if is_fol else ""
                st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
                if st.button("✓ Seg." if is_fol else "+ Seguir",key=f"sf_{ue}",use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"]=max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                    db.save(); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with cv2:
                if st.button("👤",key=f"svr_{ue}",use_container_width=True): st.session_state.profile_view=ue; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="sc">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.80rem;margin-bottom:.75rem;color:var(--t0)">🔥 Em Alta</div>', unsafe_allow_html=True)
        trending=[("Quantum ML","34"),("CRISPR 2026","28"),("Neuroplasticidade","22"),("LLMs Científicos","19"),("Matéria Escura","15")]
        for i,(t,c) in enumerate(trending):
            col_=VIB[i]
            st.markdown(f'<div style="padding:.32rem 0;border-bottom:1px solid rgba(255,255,255,.04)"><div style="font-size:.57rem;color:var(--t3)">#{i+1}</div><div style="font-size:.76rem;font-weight:600;color:{col_}">{t}</div><div style="font-size:.58rem;color:var(--t3)">{c} pesquisas</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        if st.session_state.notifications:
            st.markdown('<div class="sc">', unsafe_allow_html=True)
            st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.80rem;margin-bottom:.7rem;color:var(--t0)">🔔 Atividade</div>', unsafe_allow_html=True)
            for notif in st.session_state.notifications[:3]:
                st.markdown(f'<div style="font-size:.70rem;color:var(--t2);padding:.28rem 0;border-bottom:1px solid rgba(255,255,255,.04)">· {notif}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════ SEARCH ════════════
def render_article(a,idx=0,ctx="web"):
    sc=VIB[1] if a.get("origin")=="semantic" else VIB[2]; sn="Semantic Scholar" if a.get("origin")=="semantic" else "CrossRef"
    cite=f" · {a['citations']} cit." if a.get("citations") else ""
    uid=re.sub(r'[^a-zA-Z0-9]','',f"{ctx}_{idx}_{str(a.get('doi',''))[:10]}")[:32]
    is_saved=any(s.get('doi')==a.get('doi') for s in st.session_state.saved_articles)
    ab=(a.get("abstract","") or "")[:250]+("…" if len(a.get("abstract",""))>250 else "")
    st.markdown(f'<div class="scard"><div style="display:flex;align-items:flex-start;gap:7px;margin-bottom:.28rem"><div style="flex:1;font-family:Syne,sans-serif;font-size:.86rem;font-weight:700;color:var(--t0)">{a["title"]}</div><span style="font-size:.58rem;color:{sc};background:rgba(255,255,255,.04);border-radius:7px;padding:2px 7px;white-space:nowrap;flex-shrink:0">{sn}</span></div><div style="color:var(--t3);font-size:.64rem;margin-bottom:.3rem">{a["authors"]} · <em>{a["source"]}</em> · {a["year"]}{cite}</div><div style="color:var(--t2);font-size:.76rem;line-height:1.62">{ab}</div></div>', unsafe_allow_html=True)
    ca,cb,cc=st.columns(3)
    with ca:
        cls="btn-grn" if is_saved else ""
        st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
        if st.button("🔖 Salvo" if is_saved else "📌 Salvar",key=f"svw_{uid}"):
            if is_saved: st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]; st.toast("Removido")
            else: st.session_state.saved_articles.append(a); st.toast("Salvo!")
            db.save(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with cb:
        if st.button("📋 Citar",key=f"ctw_{uid}"): st.toast(f'{a["authors"]} ({a["year"]}). {a["title"]}.')
    with cc:
        if a.get("url"): st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:var(--blu);font-size:.78rem;text-decoration:none;line-height:2.4;display:block">↗ Abrir artigo</a>', unsafe_allow_html=True)

def page_search():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.3rem">🔍 Busca Acadêmica</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.76rem;margin-bottom:.85rem">Semantic Scholar · CrossRef · Nebula</p>', unsafe_allow_html=True)
    c1,c2=st.columns([4,1])
    with c1: q=st.text_input("",placeholder="CRISPR · quantum ML · dark matter · neuroplasticidade…",key="sq",label_visibility="collapsed")
    with c2:
        st.markdown('<div class="btn-yel">', unsafe_allow_html=True)
        if st.button("🔍 Buscar",use_container_width=True,key="btn_s"):
            if q:
                with st.spinner("Buscando…"):
                    nr=[p for p in st.session_state.feed_posts if q.lower() in p["title"].lower() or q.lower() in p["abstract"].lower() or any(q.lower() in t.lower() for t in p.get("tags",[]))]
                    sr=search_ss(q,6); cr=search_cr(q,4); st.session_state.search_results={"nebula":nr,"ss":sr,"cr":cr}; st.session_state.last_sq=q; record([q.lower()],.3)
        st.markdown('</div>', unsafe_allow_html=True)
    if st.session_state.get("search_results") and st.session_state.get("last_sq"):
        res=st.session_state.search_results; neb=res.get("nebula",[]); ss=res.get("ss",[]); cr=res.get("cr",[])
        web=ss+[x for x in cr if not any(x["title"].lower()==s["title"].lower() for s in ss)]
        ta,tn,tw=st.tabs([f"  Todos ({len(neb)+len(web)})  ",f"  🔬 Nebula ({len(neb)})  ",f"  🌐 Internet ({len(web)})  "])
        with ta:
            if neb:
                st.markdown('<div style="font-size:.59rem;color:var(--yel);font-weight:700;margin-bottom:.4rem;letter-spacing:.10em;text-transform:uppercase">Na Nebula</div>', unsafe_allow_html=True)
                for p in neb: render_post(p,ctx="srch_all",compact=True)
            if web:
                if neb: st.markdown('<hr>', unsafe_allow_html=True)
                st.markdown('<div style="font-size:.59rem;color:var(--grn);font-weight:700;margin-bottom:.4rem;letter-spacing:.10em;text-transform:uppercase">Bases Acadêmicas</div>', unsafe_allow_html=True)
                for idx,a in enumerate(web): render_article(a,idx=idx,ctx="all_w")
            if not neb and not web: st.info("Nenhum resultado.")
        with tn:
            for p in neb: render_post(p,ctx="srch_neb",compact=True)
            if not neb: st.info("Nenhuma pesquisa na Nebula.")
        with tw:
            for idx,a in enumerate(web): render_article(a,idx=idx,ctx="web_t")
            if not web: st.info("Nenhum artigo online.")
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════ KNOWLEDGE ════════════
def page_knowledge():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.9rem">🕸 Rede de Conexões</h1>', unsafe_allow_html=True)
    email=st.session_state.current_user; users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    rlist=list(users.keys())
    posts_tuple=tuple((p.get("author_email",""),p.get("tags",[])) for p in st.session_state.feed_posts)
    rtags={ue:get_utags(ue,users.get(ue,{}).get("area",""),posts_tuple) for ue in rlist}
    edges=[]
    for i in range(len(rlist)):
        for j in range(i+1,len(rlist)):
            e1,e2=rlist[i],rlist[j]; common=list(rtags[e1]&rtags[e2])
            is_fol=e2 in st.session_state.followed or e1 in st.session_state.followed
            if common or is_fol: edges.append((e1,e2,common[:5],len(common)+(2 if is_fol else 0)))
    n=len(rlist); pos={}
    for idx,ue in enumerate(rlist):
        angle=2*3.14159*idx/max(n,1); rd=0.36+0.05*((hash(ue)%5)/4)
        pos[ue]={"x":0.5+rd*np.cos(angle),"y":0.5+rd*np.sin(angle),"z":0.5+0.12*((idx%4)/3-.35)}
    fig=go.Figure()
    for e1,e2,common,strength in edges:
        p1=pos[e1]; p2=pos[e2]; alpha=min(0.45,0.08+strength*0.06)
        fig.add_trace(go.Scatter3d(x=[p1["x"],p2["x"],None],y=[p1["y"],p2["y"],None],z=[p1["z"],p2["z"],None],mode="lines",line=dict(color=f"rgba(255,214,10,{alpha:.2f})",width=min(3,1+strength)),hoverinfo="none",showlegend=False))
    ncolors=["#FFD60A" if ue==email else("#06D6A0" if ue in st.session_state.followed else "#4CC9F0") for ue in rlist]
    nsizes=[22 if ue==email else(16 if ue in st.session_state.followed else max(10,8+sum(1 for e1,e2,_,__ in edges if e1==ue or e2==ue))) for ue in rlist]
    fig.add_trace(go.Scatter3d(x=[pos[ue]["x"] for ue in rlist],y=[pos[ue]["y"] for ue in rlist],z=[pos[ue]["z"] for ue in rlist],mode="markers+text",marker=dict(size=nsizes,color=ncolors,opacity=.9,line=dict(color="rgba(255,255,255,.08)",width=1.5)),text=[users.get(ue,{}).get("name","?").split()[0] for ue in rlist],textposition="top center",textfont=dict(color="#6B6F88",size=9,family="DM Sans"),hovertemplate=[f"<b>{users.get(ue,{}).get('name','?')}</b><br>{users.get(ue,{}).get('area','')}<extra></extra>" for ue in rlist],showlegend=False))
    fig.update_layout(height=400,scene=dict(xaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),yaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),zaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),bgcolor="rgba(0,0,0,0)"),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig,use_container_width=True)
    c1,c2,c3,c4=st.columns(4)
    mvals=[("mval-yel",len(rlist),"Pesquisadores"),("mval-grn",len(edges),"Conexões"),("mval-blu",len(st.session_state.followed),"Seguindo"),("mval-red",len(st.session_state.feed_posts),"Pesquisas")]
    for col,(cls,v,l) in zip([c1,c2,c3,c4],mvals):
        with col: st.markdown(f'<div class="mbox"><div class="{cls}">{v}</div><div class="mlbl">{l}</div></div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    tm,tmi,tall=st.tabs(["  🗺 Mapa  ","  🔗 Minhas Conexões  ","  👥 Todos  "])
    with tm:
        for e1,e2,common,strength in sorted(edges,key=lambda x:-x[3])[:20]:
            n1=users.get(e1,{}); n2=users.get(e2,{}); ts=tags_html(common[:4]) if common else '<span style="color:var(--t3);font-size:.66rem">seguimento</span>'
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:7px;flex-wrap:wrap"><span style="font-size:.78rem;font-weight:700;font-family:Syne,sans-serif;color:var(--yel)">{n1.get("name","?")}</span><span style="color:var(--t3)">↔</span><span style="font-size:.78rem;font-weight:700;font-family:Syne,sans-serif;color:var(--yel)">{n2.get("name","?")}</span><div style="flex:1">{ts}</div><span style="font-size:.63rem;color:var(--grn);font-weight:700">{strength}pt</span></div></div>', unsafe_allow_html=True)
    with tmi:
        mc=[(e1,e2,c,s) for e1,e2,c,s in edges if e1==email or e2==email]
        if not mc: st.info("Siga pesquisadores e publique pesquisas.")
        for e1,e2,common,strength in sorted(mc,key=lambda x:-x[3]):
            oth=e2 if e1==email else e1; od=users.get(oth,{}); og=ugrad(oth)
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:9px;flex-wrap:wrap">{avh(ini(od.get("name","?")),34,og)}<div style="flex:1"><div style="font-weight:700;font-size:.82rem;font-family:Syne,sans-serif;color:var(--t0)">{od.get("name","?")}</div><div style="font-size:.66rem;color:var(--t3)">{od.get("area","")}</div></div>{tags_html(common[:3])}</div></div>', unsafe_allow_html=True)
            cv,cm2,_=st.columns([1,1,4])
            with cv:
                if st.button("👤",key=f"kv_{oth}",use_container_width=True): st.session_state.profile_view=oth; st.rerun()
            with cm2:
                if st.button("💬",key=f"kc_{oth}",use_container_width=True):
                    if oth not in st.session_state.chat_messages: st.session_state.chat_messages[oth]=[]
                    st.session_state.active_chat=oth; st.session_state.page="chat"; st.rerun()
    with tall:
        sq2=st.text_input("",placeholder="🔍 Buscar…",key="all_s",label_visibility="collapsed")
        for ue,ud in users.items():
            if ue==email: continue
            rn=ud.get("name","?"); ua=ud.get("area","")
            if sq2 and sq2.lower() not in rn.lower() and sq2.lower() not in ua.lower(): continue
            is_fol=ue in st.session_state.followed; rg=ugrad(ue)
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:9px">{avh(ini(rn),34,rg)}<div style="flex:1"><div style="font-size:.82rem;font-weight:700;font-family:Syne,sans-serif;color:var(--t0)">{rn}</div><div style="font-size:.66rem;color:var(--t3)">{ua}</div></div></div></div>', unsafe_allow_html=True)
            ca2,cb2,cc2=st.columns(3)
            with ca2:
                if st.button("👤 Perfil",key=f"av_{ue}",use_container_width=True): st.session_state.profile_view=ue; st.rerun()
            with cb2:
                cls="btn-grn" if is_fol else "btn-yel"
                st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
                if st.button("✓ Seg." if is_fol else "+ Seguir",key=f"af_{ue}",use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"]=max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                    db.save(); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with cc2:
                if st.button("💬 Chat",key=f"ac_{ue}",use_container_width=True):
                    if ue not in st.session_state.chat_messages: st.session_state.chat_messages[ue]=[]
                    st.session_state.active_chat=ue; st.session_state.page="chat"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════ FOLDERS ════════════
def render_doc_analysis(fname,analysis):
    if not analysis: return
    kws=analysis.get("keywords",[]); topics=analysis.get("topics",{})
    rel=analysis.get("relevance_score",0); wq=analysis.get("writing_quality",0)
    rt=analysis.get("reading_time",0); wc=analysis.get("word_count",0)
    rc="var(--grn)" if rel>=70 else("var(--yel)" if rel>=45 else "var(--red)")
    wc2="var(--grn)" if wq>=70 else("var(--yel)" if wq>=45 else "var(--red)")
    wl="Excelente" if wq>=80 else("Boa" if wq>=60 else("Regular" if wq>=40 else "Básica"))
    st.markdown(f'<div class="abox"><div style="display:flex;justify-content:space-between;align-items:flex-start;gap:9px;margin-bottom:.5rem"><div style="flex:1"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.86rem;color:var(--t0);margin-bottom:.25rem">{fname}</div><div style="font-size:.76rem;color:var(--t2);line-height:1.62">{analysis.get("summary","")}</div></div><div style="display:flex;gap:.7rem;flex-shrink:0"><div style="text-align:center"><div style="font-family:Syne,sans-serif;font-size:1.15rem;font-weight:900;color:{rc}">{rel}%</div><div style="font-size:.55rem;color:var(--t3);text-transform:uppercase;letter-spacing:.07em">Relevância</div></div><div style="text-align:center"><div style="font-family:Syne,sans-serif;font-size:1.15rem;font-weight:900;color:{wc2}">{wq}%</div><div style="font-size:.55rem;color:var(--t3);text-transform:uppercase;letter-spacing:.07em">Qualidade</div></div></div></div><div style="display:flex;gap:1rem;flex-wrap:wrap;font-size:.63rem;color:var(--t3)"><span>📖 ~{rt} min</span><span>📝 {wc} palavras</span><span>🔑 {len(kws)} keywords</span><span>✍️ <strong style="color:{wc2}">{wl}</strong></span></div></div>', unsafe_allow_html=True)
    tk,tt,ti=st.tabs(["  🔑 Keywords  ","  🎯 Temas  ","  ✨ Melhorias  "])
    with tk:
        if kws:
            w=[max(1,25-i) for i in range(len(kws))]
            fig=go.Figure(go.Bar(x=w[:18],y=kws[:18],orientation='h',marker=dict(color=w[:18],colorscale=[[0,"#1A1B2E"],[.4,"#FF3B5C"],[.7,"#FFD60A"],[1,"#06D6A0"]],line=dict(color="#0D0E1A",width=1)),text=kws[:18],textposition='inside',textfont=dict(color='white',size=8)))
            fig.update_layout(**{**pc_dark(),'height':max(280,len(kws[:18])*16),'yaxis':dict(showticklabels=False),'title':dict(text="TF-IDF Keywords",font=dict(color="#E8E9F0",family="Syne",size=11))})
            st.markdown('<div class="chart-wrap">', unsafe_allow_html=True); st.plotly_chart(fig,use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(tags_html(kws[:20]), unsafe_allow_html=True)
        else: st.info("Palavras-chave não extraídas.")
    with tt:
        if topics:
            fig2=go.Figure(go.Pie(labels=list(topics.keys()),values=list(topics.values()),hole=0.5,marker=dict(colors=VIB[:len(topics)],line=dict(color=["#07080F"]*15,width=2)),textfont=dict(color="white",size=8)))
            fig2.update_layout(height=260,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(font=dict(color="#6B6F88",size=8)),margin=dict(l=0,r=0,t=10,b=0))
            st.markdown('<div class="chart-wrap">', unsafe_allow_html=True); st.plotly_chart(fig2,use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)
    with ti:
        if analysis.get("strengths"): 
            st.markdown('<div class="sb-label" style="padding:0">✓ Pontos Fortes</div>', unsafe_allow_html=True)
            for s in analysis["strengths"]: st.markdown(f'<div class="pbox-grn" style="margin-bottom:.25rem">✓ {s}</div>', unsafe_allow_html=True)
        if analysis.get("improvements"):
            st.markdown('<div class="sb-label" style="padding:0;margin-top:.6rem">→ Sugestões</div>', unsafe_allow_html=True)
            for imp in analysis["improvements"]: st.markdown(f'<div class="pbox-yel" style="margin-bottom:.25rem">→ {imp}</div>', unsafe_allow_html=True)

def page_folders():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.9rem">📁 Pastas de Pesquisa</h1>', unsafe_allow_html=True)
    email=st.session_state.current_user; u=guser(); ra=u.get("area","")
    c1,c2,_=st.columns([2,1.2,1.5])
    with c1: nfn=st.text_input("Nome da pasta",placeholder="Ex: Genômica Comparativa",key="nf_n")
    with c2: nfd=st.text_input("Descrição",placeholder="Breve descrição",key="nf_d")
    st.markdown('<div class="btn-yel" style="display:inline-block">', unsafe_allow_html=True)
    if st.button("📁 Criar pasta",key="btn_nf"):
        if nfn.strip():
            if nfn not in st.session_state.folders: st.session_state.folders[nfn]={"desc":nfd,"files":[],"notes":"","analyses":{}}; db.save(); st.success(f"Pasta '{nfn}' criada!"); st.rerun()
            else: st.warning("Pasta já existe.")
        else: st.warning("Digite um nome.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    if not st.session_state.folders:
        st.markdown('<div class="glass" style="text-align:center;padding:4rem"><div style="font-size:2.2rem;opacity:.2;margin-bottom:.7rem">📁</div><div style="color:var(--t3)">Nenhuma pasta criada</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True); return
    folder_cols=st.columns(3)
    for idx,(fn,fd) in enumerate(list(st.session_state.folders.items())):
        if not isinstance(fd,dict): fd={"files":fd,"desc":"","notes":"","analyses":{}}; st.session_state.folders[fn]=fd
        files=fd.get("files",[]); analyses=fd.get("analyses",{}); atags=list({t for an in analyses.values() for t in an.get("keywords",[])[:3]})
        with folder_cols[idx%3]:
            col_=VIB[idx%len(VIB)]
            st.markdown(f'<div class="glass" style="padding:1rem;text-align:center;margin-bottom:.5rem;border-top:2px solid {col_}"><div style="font-size:1.6rem;opacity:.5;margin-bottom:5px">📁</div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.88rem;color:var(--t0)">{fn}</div><div style="color:var(--t3);font-size:.63rem;margin-top:2px">{fd.get("desc","")}</div><div style="margin-top:.32rem;font-size:.66rem;color:{col_}">{len(files)} arquivo(s) · {len(analyses)} analisado(s)</div><div style="margin-top:.3rem">{tags_html(atags[:3])}</div></div>', unsafe_allow_html=True)
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
                fd["files"]=files; db.save(); st.success(f"{len(up)} arquivo(s) adicionado(s)!")
            if files:
                for f in files:
                    ft=ftype(f); ha=f in analyses
                    icon={"PDF":"📄","Word":"📝","Planilha":"📊","Dados":"📈","Código Python":"🐍","Notebook":"📓","Apresentação":"📽","Imagem":"🖼","Markdown":"📋"}.get(ft,"📄")
                    ab2=f'<span class="badge-grn" style="font-size:.57rem;margin-left:5px">✓</span>' if ha else ''
                    st.markdown(f'<div style="display:flex;align-items:center;gap:7px;padding:.38rem 0;border-bottom:1px solid rgba(255,255,255,.04)"><span>{icon}</span><span style="font-size:.75rem;color:var(--t2);flex:1">{f}</span>{ab2}</div>', unsafe_allow_html=True)
            else: st.markdown('<p style="color:var(--t3);font-size:.72rem;text-align:center;padding:.45rem">Arraste arquivos — PDF, DOCX, XLSX, CSV…</p>', unsafe_allow_html=True)
            st.markdown('<hr>', unsafe_allow_html=True)
            ca2,cb2,_=st.columns([1.5,1.5,2])
            with ca2:
                st.markdown('<div class="btn-yel">', unsafe_allow_html=True)
                if st.button("🔬 Analisar",key=f"an_{fn}",use_container_width=True):
                    if files:
                        pb=st.progress(0,"Iniciando…"); fb=st.session_state.folder_files_bytes.get(fn,{})
                        for fi,f in enumerate(files):
                            pb.progress((fi+1)/len(files),f"Analisando: {f[:28]}…"); fbytes=fb.get(f,b""); ft=ftype(f)
                            analyses[f]=analyze_doc(f,fbytes,ft,ra)
                        fd["analyses"]=analyses; db.save(); pb.empty(); st.success("✓ Análise completa!"); st.rerun()
                    else: st.warning("Adicione arquivos antes.")
                st.markdown('</div>', unsafe_allow_html=True)
            with cb2:
                st.markdown('<div class="btn-red">', unsafe_allow_html=True)
                if st.button("🗑 Excluir",key=f"df_{fn}",use_container_width=True):
                    del st.session_state.folders[fn]
                    if fn in st.session_state.folder_files_bytes: del st.session_state.folder_files_bytes[fn]
                    db.save(); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            if analyses:
                st.markdown('<div class="dtxt">Análises Inteligentes</div>', unsafe_allow_html=True)
                for f,an in analyses.items():
                    with st.expander(f"🔬 {f}"): render_doc_analysis(f,an)
            note=st.text_area("Notas",value=fd.get("notes",""),key=f"nt_{fn}",height=60)
            if st.button("💾 Salvar nota",key=f"sn_{fn}"): fd["notes"]=note; db.save(); st.success("✓ Nota salva!")
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════ ANALYTICS ════════════
def page_analytics():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.9rem">📊 Painel de Pesquisa</h1>', unsafe_allow_html=True)
    email=st.session_state.current_user; d=st.session_state.stats_data
    tf,tp,ti,tpr=st.tabs(["  📁 Pastas  ","  📝 Publicações  ","  📈 Impacto  ","  🎯 Interesses  "])
    with tf:
        folders=st.session_state.folders
        if not folders: st.markdown('<div class="glass" style="text-align:center;padding:3rem;color:var(--t3)">Crie pastas e analise documentos.</div>', unsafe_allow_html=True)
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
                fig.update_layout(**{**pc_dark(),'height':250,'yaxis':dict(showgrid=False,color="#6B6F88",tickfont=dict(size=9)),'title':dict(text="Temas por Pastas",font=dict(color="#E8E9F0",family="Syne",size=11))})
                st.markdown('<div class="chart-wrap">', unsafe_allow_html=True); st.plotly_chart(fig,use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)
    with tp:
        my_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==email]
        if not my_posts: st.markdown('<div class="glass" style="text-align:center;padding:2.5rem;color:var(--t3)">Publique pesquisas para ver métricas.</div>', unsafe_allow_html=True)
        else:
            c1,c2,c3=st.columns(3)
            with c1: st.markdown(f'<div class="mbox"><div class="mval-yel">{len(my_posts)}</div><div class="mlbl">Pesquisas</div></div>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="mbox"><div class="mval-grn">{sum(p["likes"] for p in my_posts)}</div><div class="mlbl">Curtidas</div></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="mbox"><div class="mval-blu">{sum(len(p.get("comments",[])) for p in my_posts)}</div><div class="mlbl">Comentários</div></div>', unsafe_allow_html=True)
            titles_s=[p["title"][:16]+"…" for p in my_posts]
            fig2=go.Figure()
            fig2.add_trace(go.Bar(name="Curtidas",x=titles_s,y=[p["likes"] for p in my_posts],marker_color=VIB[0]))
            fig2.add_trace(go.Bar(name="Comentários",x=titles_s,y=[len(p.get("comments",[])) for p in my_posts],marker_color=VIB[1]))
            fig2.update_layout(barmode="group",height=230,**pc_dark(),title=dict(text="Engajamento",font=dict(color="#E8E9F0",family="Syne",size=11)),legend=dict(font=dict(color="#6B6F88")))
            st.markdown('<div class="chart-wrap">', unsafe_allow_html=True); st.plotly_chart(fig2,use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)
            for p in sorted(my_posts,key=lambda x:x.get("date",""),reverse=True):
                st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;justify-content:space-between"><div style="font-family:Syne,sans-serif;font-size:.85rem;font-weight:700;color:var(--t0)">{p["title"][:55]}{"…" if len(p["title"])>55 else ""}</div>{badge(p["status"])}</div><div style="font-size:.68rem;color:var(--t3);margin-top:.35rem">{p.get("date","")} · {p["likes"]} curtidas · {len(p.get("comments",[]))} comentários · {p.get("views",0)} views</div><div style="margin-top:.3rem">{tags_html(p.get("tags",[])[:4])}</div></div>', unsafe_allow_html=True)
    with ti:
        c1,c2,c3=st.columns(3)
        with c1: st.markdown(f'<div class="mbox"><div class="mval-yel">{d.get("h_index",4)}</div><div class="mlbl">Índice H</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="mbox"><div class="mval-grn">{d.get("fator_impacto",3.8):.1f}</div><div class="mlbl">Fator de Impacto</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="mbox"><div class="mval-blu">{len(st.session_state.saved_articles)}</div><div class="mlbl">Artigos Salvos</div></div>', unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)
        nh=st.number_input("Índice H",0,200,d.get("h_index",4),key="e_h"); nfi=st.number_input("Fator de impacto",0.0,100.0,float(d.get("fator_impacto",3.8)),step=0.1,key="e_fi"); nn=st.text_area("Notas",value=d.get("notes",""),key="e_nt",height=70)
        st.markdown('<div class="btn-yel">', unsafe_allow_html=True)
        if st.button("💾 Salvar métricas",key="btn_sm"): d.update({"h_index":nh,"fator_impacto":nfi,"notes":nn}); db.save(); st.success("✓ Salvo!")
        st.markdown('</div>', unsafe_allow_html=True)
    with tpr:
        prefs=st.session_state.user_prefs.get(email,{})
        if prefs:
            top=sorted(prefs.items(),key=lambda x:-x[1])[:14]; mx=max(s for _,s in top) if top else 1
            cats=[t for t,_ in top[:8]]; vals=[round(s/mx*100) for _,s in top[:8]]
            if len(cats)>=3:
                fig3=go.Figure(go.Scatterpolar(r=vals+[vals[0]],theta=cats+[cats[0]],fill='toself',line=dict(color="#FFD60A"),fillcolor="rgba(255,214,10,.10)"))
                fig3.update_layout(height=265,polar=dict(bgcolor="rgba(0,0,0,0)",radialaxis=dict(visible=True,gridcolor="rgba(255,255,255,.04)",color="#6B6F88",tickfont=dict(size=8)),angularaxis=dict(gridcolor="rgba(255,255,255,.04)",color="#6B6F88",tickfont=dict(size=9))),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=40,r=40,t=15,b=15))
                st.markdown('<div class="chart-wrap">', unsafe_allow_html=True); st.plotly_chart(fig3,use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)
            c1,c2=st.columns(2)
            for i,(tag,score) in enumerate(top):
                with(c1 if i%2==0 else c2): st.markdown(f'<div style="display:flex;justify-content:space-between;font-size:.75rem;margin-bottom:2px"><span style="color:var(--t2)">{tag}</span><span style="color:var(--yel);font-weight:700">{round(score,1)}</span></div>', unsafe_allow_html=True)
        else: st.info("Interaja com pesquisas para construir seu perfil.")
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════ IMAGE ANALYSIS ════════════
def page_img_search():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.3rem">🔬 Análise Visual Científica</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.76rem;margin-bottom:1rem">Detecta padrões, estruturas e conecta com pesquisas similares</p>', unsafe_allow_html=True)
    cu,cr=st.columns([1,1.9])
    with cu:
        st.markdown('<div class="glass" style="padding:1rem">', unsafe_allow_html=True)
        img_file=st.file_uploader("📷 Carregar Imagem",type=["png","jpg","jpeg","webp","tiff"],key="img_up")
        ib=None
        if img_file: ib=img_file.read(); st.image(ib,use_container_width=True,caption="Imagem carregada")
        st.markdown('<div class="btn-yel">', unsafe_allow_html=True)
        run=st.button("🔬 Analisar",use_container_width=True,key="btn_run")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="pbox-yel" style="margin-top:.8rem"><div style="font-size:.65rem;color:var(--yel);font-weight:700;margin-bottom:2px">⚠️ Aviso IA</div><div style="font-size:.62rem;color:var(--t2);line-height:1.62">Análise computacional. Não substitui especialistas.</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with cr:
        if run and ib:
            with st.spinner("Analisando…"): rep=analyze_image(ib); st.session_state.img_result=rep
            if rep:
                cc=VIB[1] if rep["confidence"]>80 else(VIB[0] if rep["confidence"]>60 else VIB[2])
                st.markdown(f'<div class="abox"><div style="display:flex;align-items:flex-start;justify-content:space-between;gap:9px;margin-bottom:.5rem"><div><div style="font-size:.57rem;color:var(--t3);letter-spacing:.10em;text-transform:uppercase;margin-bottom:3px;font-weight:700">Categoria</div><div style="font-family:Syne,sans-serif;font-size:1.05rem;font-weight:800;color:var(--t0);margin-bottom:3px">{rep["category"]}</div></div><div style="background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:.5rem .85rem;text-align:center;flex-shrink:0"><div style="font-family:Syne,sans-serif;font-size:1.45rem;font-weight:900;color:{cc}">{rep["confidence"]}%</div><div style="font-size:.55rem;color:var(--t3);text-transform:uppercase;font-weight:700">confiança</div></div></div><div style="display:flex;gap:1.3rem;flex-wrap:wrap;font-size:.63rem;color:var(--t3)"><span>Material: <strong style="color:var(--t1)">{rep["material"]}</strong></span><span>Res: <strong style="color:var(--t1)">{rep["size"][0]}×{rep["size"][1]}</strong></span><span>Brilho: <strong style="color:var(--t1)">{rep["brightness"]}</strong></span></div></div>', unsafe_allow_html=True)
                c1,c2,c3=st.columns(3)
                sl="Alta" if rep["symmetry"]>0.78 else("Média" if rep["symmetry"]>0.52 else "Baixa")
                with c1: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:.95rem;font-weight:800;color:var(--yel)">{rep["texture"]["complexity"]}</div><div class="mlbl">Complexidade</div></div>', unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:.95rem;font-weight:800;color:var(--grn)">{sl}</div><div class="mlbl">Simetria</div></div>', unsafe_allow_html=True)
                with c3: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:.95rem;font-weight:800;color:var(--blu)">{rep.get("shapes",["—"])[0]}</div><div class="mlbl">Forma</div></div>', unsafe_allow_html=True)
                rv,gv,bv=rep["color"]["r"],rep["color"]["g"],rep["color"]["b"]
                hx="#{:02x}{:02x}{:02x}".format(int(rv),int(gv),int(bv))
                pl="".join(f'<div style="width:24px;height:24px;border-radius:5px;background:rgb{str(p)};border:1.5px solid rgba(255,255,255,.08)"></div>' for p in rep["palette"][:7])
                ts="Quente" if rep["color"]["warm"] else("Fria" if rep["color"]["cool"] else "Neutra")
                st.markdown(f'<div class="abox"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.80rem;margin-bottom:.68rem;color:var(--t0)">🎨 Cor & Paleta</div><div style="display:flex;gap:9px;align-items:center;margin-bottom:.7rem"><div style="width:38px;height:38px;border-radius:9px;background:{hx};border:1.5px solid rgba(255,255,255,.08);flex-shrink:0"></div><div style="font-size:.75rem;color:var(--t2);line-height:1.75">RGB: <strong style="color:var(--t1)">({int(rv)},{int(gv)},{int(bv)})</strong> · {hx.upper()}<br>Temp: <strong style="color:var(--t1)">{ts}</strong></div></div><div style="display:flex;gap:4px;flex-wrap:wrap">{pl}</div></div>', unsafe_allow_html=True)
                if rep.get("histograms"):
                    h=rep["histograms"]; bx=list(range(0,256,8))[:32]; fig4=go.Figure()
                    fig4.add_trace(go.Scatter(x=bx,y=h["r"][:32],fill='tozeroy',name='R',line=dict(color='rgba(255,59,92,.9)',width=1.5),fillcolor='rgba(255,59,92,.10)'))
                    fig4.add_trace(go.Scatter(x=bx,y=h["g"][:32],fill='tozeroy',name='G',line=dict(color='rgba(6,214,160,.9)',width=1.5),fillcolor='rgba(6,214,160,.10)'))
                    fig4.add_trace(go.Scatter(x=bx,y=h["b"][:32],fill='tozeroy',name='B',line=dict(color='rgba(76,201,240,.9)',width=1.5),fillcolor='rgba(76,201,240,.10)'))
                    layout4={**pc_dark()}; layout4.update({"height":165,"title":dict(text="Histograma RGB",font=dict(color="#E8E9F0",family="Syne",size=10)),"legend":dict(font=dict(color="#6B6F88",size=9)),"margin":dict(l=10,r=10,t=30,b=8)})
                    fig4.update_layout(**layout4)
                    st.markdown('<div class="chart-wrap">', unsafe_allow_html=True); st.plotly_chart(fig4,use_container_width=True); st.markdown('</div>', unsafe_allow_html=True)
        elif not img_file:
            st.markdown('<div class="glass" style="padding:4.5rem 2rem;text-align:center"><div style="font-size:2.8rem;opacity:.18;margin-bottom:1rem">🔬</div><div style="font-family:Syne,sans-serif;font-size:1rem;color:var(--t1)">Carregue uma imagem científica</div><div style="font-size:.72rem;color:var(--t3);margin-top:.4rem;line-height:1.9">PNG · JPG · WEBP · TIFF<br>Microscopia · Cristalografia · Fluorescência</div></div>', unsafe_allow_html=True)
    if st.session_state.get("img_result"):
        rep=st.session_state.img_result; st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<h2 style="margin-bottom:.6rem">🔗 Pesquisas Relacionadas</h2>', unsafe_allow_html=True)
        kw=(rep.get("kw","")+" "+rep.get("category","")).lower().split(); at=list(set(kw))
        tn2,tf2,tw2=st.tabs(["  🔬 Na Nebula  ","  📁 Nas Pastas  ","  🌐 Internet  "])
        with tn2:
            nr=sorted([(sum(1 for t in at if len(t)>2 and t in (p.get("title","")+" "+p.get("abstract","")+" "+" ".join(p.get("tags",[]))).lower()),p) for p in st.session_state.feed_posts],key=lambda x:-x[0])
            nr=[p for s,p in nr if s>0]
            for p in nr[:4]: render_post(p,ctx="img_neb",compact=True)
            if not nr: st.markdown('<div style="color:var(--t3);padding:.8rem">Nenhuma pesquisa similar.</div>', unsafe_allow_html=True)
        with tf2:
            fm=[]
            for fn2,fd2 in st.session_state.folders.items():
                if not isinstance(fd2,dict): continue
                fkw=list({kw2 for an2 in fd2.get("analyses",{}).values() for kw2 in an2.get("keywords",[])})
                sc2=sum(1 for t in at if len(t)>2 and any(t in ft2 for ft2 in fkw))
                if sc2>0: fm.append((sc2,fn2,fd2))
            fm.sort(key=lambda x:-x[0])
            for _,fn2,fd2 in fm[:4]:
                ak=list({kw2 for an2 in fd2.get("analyses",{}).values() for kw2 in an2.get("keywords",[])[:4]})
                st.markdown(f'<div class="scard"><div style="font-family:Syne,sans-serif;font-size:.86rem;font-weight:700;color:var(--t0);margin-bottom:.25rem">📁 {fn2}</div><div style="color:var(--t3);font-size:.64rem;margin-bottom:.32rem">{len(fd2.get("files",[]))} arquivos</div><div>{tags_html(ak[:5])}</div></div>', unsafe_allow_html=True)
            if not fm: st.markdown('<div style="color:var(--t3);padding:.8rem">Nenhum documento relacionado.</div>', unsafe_allow_html=True)
        with tw2:
            ck=f"img_{rep['kw'][:38]}"
            if ck not in st.session_state.scholar_cache:
                with st.spinner("Buscando artigos…"): st.session_state.scholar_cache[ck]=search_ss(f"{rep['category']} {rep['object_type']} {rep['material']}",4)
            wr=st.session_state.scholar_cache.get(ck,[])
            for idx,a in enumerate(wr): render_article(a,idx=idx+2000,ctx="img_web")
            if not wr: st.markdown('<div style="color:var(--t3);padding:.8rem">Sem resultados online.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════ CHAT ════════════
def page_chat():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.9rem">💬 Mensagens</h1>', unsafe_allow_html=True)
    cc,cm=st.columns([.85,2.8]); email=st.session_state.current_user
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    with cc:
        st.markdown('<div style="font-size:.58rem;font-weight:700;color:var(--t4);letter-spacing:.12em;text-transform:uppercase;margin-bottom:.7rem">Conversas</div>', unsafe_allow_html=True)
        shown=set()
        for ue in st.session_state.chat_contacts:
            if ue==email or ue in shown: continue
            shown.add(ue); ud=users.get(ue,{}); un=ud.get("name","?"); ui=ini(un); ug=ugrad(ue)
            msgs=st.session_state.chat_messages.get(ue,[]); last=msgs[-1]["text"][:22]+"…" if msgs and len(msgs[-1]["text"])>22 else(msgs[-1]["text"] if msgs else "Iniciar")
            active=st.session_state.active_chat==ue; online=is_online(ue)
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            bg=f"rgba(255,255,255,{'.09' if active else '.04'})"; bdr=f"rgba(255,255,255,{'.18' if active else '.08'})"
            st.markdown(f'<div style="background:{bg};border:1px solid {bdr};border-radius:12px;padding:8px 10px;margin-bottom:4px"><div style="display:flex;align-items:center;gap:7px">{avh(ui,30,ug)}<div style="overflow:hidden;flex:1"><div style="font-size:.76rem;font-weight:600;font-family:Syne,sans-serif;color:var(--t0)">{dot}{un}</div><div style="font-size:.63rem;color:var(--t3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{last}</div></div></div></div>', unsafe_allow_html=True)
            if st.button("→",key=f"oc_{ue}",use_container_width=True): st.session_state.active_chat=ue; st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
        nc2=st.text_input("",placeholder="E-mail para adicionar…",key="new_ct",label_visibility="collapsed")
        if st.button("+ Adicionar",key="btn_ac",use_container_width=True):
            if nc2 in users and nc2!=email:
                if nc2 not in st.session_state.chat_contacts: st.session_state.chat_contacts.append(nc2)
                st.rerun()
            elif nc2: st.toast("Usuário não encontrado.")
    with cm:
        if st.session_state.active_chat:
            contact=st.session_state.active_chat; cd=users.get(contact,{}); cn=cd.get("name","?"); ci=ini(cn); cg=ugrad(contact)
            msgs=st.session_state.chat_messages.get(contact,[]); online=is_online(contact)
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            st.markdown(f'<div style="background:var(--g2);border:1px solid var(--gb1);border-radius:14px;padding:10px 14px;margin-bottom:.85rem;display:flex;align-items:center;gap:10px">{avh(ci,36,cg)}<div style="flex:1"><div style="font-weight:700;font-size:.88rem;font-family:Syne,sans-serif;color:var(--t0)">{dot}{cn}</div><div style="font-size:.63rem;color:var(--grn)">🔒 AES-256 ativo</div></div></div>', unsafe_allow_html=True)
            for msg in msgs:
                im=msg["from"]=="me"; cls="bme" if im else "bthem"
                st.markdown(f'<div style="display:flex;{"justify-content:flex-end" if im else ""}"><div class="{cls}">{msg["text"]}<div style="font-size:.57rem;color:var(--t3);margin-top:2px;text-align:{"right" if im else "left"}">{msg["time"]}</div></div></div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            ci2,cb2=st.columns([5,1])
            with ci2: nm=st.text_input("",placeholder="Escreva uma mensagem…",key=f"mi_{contact}",label_visibility="collapsed")
            with cb2:
                st.markdown("<div style='height:5px'></div>", unsafe_allow_html=True)
                st.markdown('<div class="btn-yel">', unsafe_allow_html=True)
                if st.button("→",key=f"ms_{contact}",use_container_width=True):
                    if nm:
                        now=datetime.now().strftime("%H:%M"); st.session_state.chat_messages.setdefault(contact,[]).append({"from":"me","text":nm,"time":now}); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="glass" style="text-align:center;padding:5rem"><div style="font-size:2.2rem;opacity:.15;margin-bottom:.85rem">💬</div><div style="font-family:Syne,sans-serif;font-size:.96rem;color:var(--t1)">Selecione uma conversa</div><div style="font-size:.70rem;color:var(--t3);margin-top:.4rem">🔒 End-to-end criptografado</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════ SETTINGS ════════════
def page_settings():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.9rem">⚙️ Configurações</h1>', unsafe_allow_html=True)
    email=st.session_state.current_user; ud=st.session_state.users.get(email,{})
    st.markdown(f'<div class="abox"><div style="font-size:.58rem;color:var(--t3);text-transform:uppercase;letter-spacing:.10em;margin-bottom:.4rem;font-weight:700">E-mail da conta</div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.95rem;color:var(--yel)">{email}</div></div>', unsafe_allow_html=True)
    en=ud.get("2fa_enabled",False)
    st.markdown(f'<div class="abox" style="margin-top:.5rem"><div style="display:flex;align-items:center;justify-content:space-between"><div><div style="font-weight:700;font-size:.85rem;color:var(--t0)">🔐 Autenticação 2FA</div><div style="font-size:.68rem;color:var(--t3);margin-top:2px">{"Ativo — código exigido no login" if en else "Inativo — mais segurança com 2FA"}</div></div><span class="{"badge-grn" if en else "badge-red"}">{("Ativo" if en else "Inativo")}</span></div></div>', unsafe_allow_html=True)
    cls2="btn-red" if en else "btn-grn"
    st.markdown(f'<div class="{cls2}">', unsafe_allow_html=True)
    if st.button("✕ Desativar 2FA" if en else "✓ Ativar 2FA",key="cfg_2fa"):
        st.session_state.users[email]["2fa_enabled"]=not en; db.save(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<h2 style="margin-bottom:.7rem">🔑 Alterar senha</h2>', unsafe_allow_html=True)
    with st.form("cpw"):
        op=st.text_input("Senha atual",type="password",key="op"); np2=st.text_input("Nova senha",type="password",key="np2"); nc3=st.text_input("Confirmar",type="password",key="nc3")
        st.markdown('<div class="btn-yel">', unsafe_allow_html=True)
        if st.form_submit_button("🔑 Alterar Senha",use_container_width=True):
            if hp(op)!=ud.get("password",""): st.error("Senha atual incorreta.")
            elif np2!=nc3: st.error("Não coincidem.")
            elif len(np2)<6: st.error("Mínimo 6 caracteres.")
            else: st.session_state.users[email]["password"]=hp(np2); db.save(); st.success("✓ Alterada!")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<h2 style="margin-bottom:.7rem">🛡 Protocolos Ativos</h2>', unsafe_allow_html=True)
    for nm,ds in [("🔒 AES-256","Criptografia end-to-end"),("🔏 SHA-256","Hash de senhas"),("🛡 TLS 1.3","Transmissão segura")]:
        st.markdown(f'<div class="pbox-grn"><div style="display:flex;align-items:center;gap:9px"><div style="width:24px;height:24px;border-radius:7px;background:rgba(6,214,160,.12);display:flex;align-items:center;justify-content:center;color:var(--grn);font-size:.72rem;flex-shrink:0">✓</div><div><div style="font-weight:700;color:var(--grn);font-size:.78rem">{nm}</div><div style="font-size:.66rem;color:var(--t3)">{ds}</div></div></div></div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="btn-red">', unsafe_allow_html=True)
    if st.button("🚪 Sair da Conta",key="logout",use_container_width=True):
        st.session_state.logged_in=False; st.session_state.current_user=None; st.session_state.page="login"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════ ROUTER ════════════
def main():
    inject_css()
    if not st.session_state.logged_in:
        p=st.session_state.page
        if p=="verify_email": page_verify_email()
        elif p=="2fa": page_2fa()
        else: page_login()
        return
    render_sidebar()
    if st.session_state.profile_view: page_profile(st.session_state.profile_view); return
    {
        "feed":page_feed,"search":page_search,"knowledge":page_knowledge,
        "folders":page_folders,"analytics":page_analytics,"img_search":page_img_search,
        "chat":page_chat,"settings":page_settings,
    }.get(st.session_state.page,page_feed)()

main()
