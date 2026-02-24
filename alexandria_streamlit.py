import subprocess, sys, os, json, hashlib, random, string, base64, re, io
from datetime import datetime
from collections import defaultdict, Counter

def _pip(*pkgs):
    for p in pkgs:
        try: subprocess.check_call([sys.executable,"-m","pip","install",p,"-q"],
                                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
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

st.set_page_config(page_title="Nebula", page_icon="N", layout="wide",
                   initial_sidebar_state="collapsed")

# ─── DB ───────────────────────────────────────────
DB_FILE = "nebula_db.json"
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: pass
    return {}
def save_db():
    try:
        prefs_s={k:dict(v) for k,v in st.session_state.user_prefs.items()}
        with open(DB_FILE,"w",encoding="utf-8") as f:
            json.dump({"users":st.session_state.users,"feed_posts":st.session_state.feed_posts,
                       "folders":st.session_state.folders,"user_prefs":prefs_s,
                       "saved_articles":st.session_state.saved_articles},f,ensure_ascii=False,indent=2)
    except: pass

# ─── UTILS ────────────────────────────────────────
def hp(pw): return hashlib.sha256(pw.encode()).hexdigest()
def code6(): return ''.join(random.choices(string.digits,k=6))
def ini(n):
    if not isinstance(n,str): n=str(n)
    p=n.strip().split()
    return ''.join(w[0].upper() for w in p[:2]) if p else "?"
def img_to_b64(f):
    try:
        f.seek(0); data=f.read()
        ext=getattr(f,"name","img.png").split(".")[-1].lower()
        mime={"jpg":"jpeg","jpeg":"jpeg","png":"png","gif":"gif","webp":"webp"}.get(ext,"png")
        return f"data:image/{mime};base64,{base64.b64encode(data).decode()}"
    except: return None
def time_ago(ds):
    try:
        d=datetime.strptime(ds,"%Y-%m-%d"); delta=(datetime.now()-d).days
        if delta==0: return "hoje"
        if delta==1: return "ontem"
        if delta<7: return f"{delta}d"
        if delta<30: return f"{delta//7}sem"
        return f"{delta//30}m"
    except: return ds
def fmt_num(n):
    try:
        n=int(n); return f"{n/1000:.1f}k" if n>=1000 else str(n)
    except: return str(n)
def guser():
    if not isinstance(st.session_state.get("users"),dict): return {}
    return st.session_state.users.get(st.session_state.current_user,{})
def get_photo(email):
    u=st.session_state.get("users",{})
    return u.get(email,{}).get("photo_b64") if isinstance(u,dict) else None

STOPWORDS={"de","a","o","que","e","do","da","em","um","para","é","com","uma","os","no","se",
 "na","por","mais","as","dos","como","mas","foi","ao","ele","das","tem","à","seu","sua","ou",
 "ser","quando","muito","há","nos","já","está","eu","também","só","pelo","pela","até","isso",
 "ela","entre","era","depois","sem","mesmo","aos","ter","seus","quem","nas","me","esse","eles",
 "estão","você","tinha","foram","essa","num","nem","suas","meu","às","minha","têm","numa",
 "pelos","pelas","the","of","and","to","in","is","it","that","was","he","for","on","are","as",
 "with","his","they","at","be","this","from","or","one","had","by","not","what","all","were",
 "we","when","your","can","said","there","use","an","each","which","she","do","how","their",
 "if","will","up","other","about","out","many","then","them","these","so","some","her","would",
 "make","like","him","into","time","has","look","two","more","write","go","see","number","no",
 "way","could","people","my","than","first","water","been","call","who","oil","its","now"}

def extract_text_pdf(pdf_bytes):
    if PyPDF2 is None: return ""
    try:
        r=PyPDF2.PdfReader(io.BytesIO(pdf_bytes)); t=""
        for pg in r.pages[:25]:
            try: t+=pg.extract_text()+"\n"
            except: pass
        return t[:50000]
    except: return ""

def extract_text_xlsx(xlsx_bytes):
    if openpyxl is None: return ""
    try:
        wb=openpyxl.load_workbook(io.BytesIO(xlsx_bytes),read_only=True,data_only=True); t=""
        for sn in wb.sheetnames[:3]:
            ws=wb[sn]; t+=f"\n=== {sn} ===\n"
            for row in list(ws.iter_rows(max_row=50,values_only=True)):
                vals=[str(v) for v in row if v is not None]
                if vals: t+=" | ".join(vals[:10])+"\n"
        return t[:20000]
    except: return ""

def extract_text_csv(csv_bytes):
    try:
        df=pd.read_csv(io.BytesIO(csv_bytes),nrows=200)
        s=f"Colunas: {', '.join(df.columns.tolist())}\nLinhas: {len(df)}\n"
        for col in df.columns[:10]:
            if df[col].dtype==object: s+=f"{col}: {', '.join(str(v) for v in df[col].dropna().head(5).tolist())}\n"
            else: s+=f"{col}: min={df[col].min():.2f}, max={df[col].max():.2f}, mean={df[col].mean():.2f}\n"
        return s
    except: return ""

def kw_extract(text, n=25):
    if not text: return []
    words=re.findall(r'\b[a-záàâãéêíóôõúüçA-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]{4,}\b',text.lower())
    words=[w for w in words if w not in STOPWORDS]
    if not words: return []
    tf=Counter(words); tot=sum(tf.values())
    return [w for w,_ in sorted({w:c/tot for w,c in tf.items()}.items(),key=lambda x:-x[1])[:n]]

def extract_authors(text):
    authors=[]
    for pat in [r'(?:Autor(?:es)?|Author(?:s)?)[:\s]+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){1,4})',
                r'(?:Por|By)[:\s]+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){1,3})']:
        authors.extend(re.findall(pat,text)[:4])
    seen=set(); unique=[]
    for a in authors:
        if a.strip().lower() not in seen and len(a.strip())>4: seen.add(a.strip().lower()); unique.append(a.strip())
    return unique[:6]

def extract_years(text):
    years=re.findall(r'\b(19[5-9]\d|20[0-3]\d)\b',text)
    return sorted(Counter(years).items(),key=lambda x:-x[1])[:10]

def extract_refs(text):
    refs=[]
    blocks=re.split(r'\n(?=\[\d+\])',text)
    for b in blocks[1:16]: 
        c=re.sub(r'\s+',' ',b.strip())
        if len(c)>30: refs.append(c[:200])
    if not refs:
        for m in re.findall(r'[A-ZÀ-Ú][a-zà-ú]+(?:,\s[A-ZÀ-Ú]\.)+\s*\(\d{4}\)[^.]+\.',text)[:10]:
            refs.append(m)
    return refs[:12]

TOPIC_MAP={
    "Saúde & Medicina":["saúde","medicina","hospital","doença","paciente","diagnóstico","terapia","clínico","drug","health","medical","clinical","cancer","tumor"],
    "Biologia & Genômica":["biologia","genômica","gene","dna","rna","proteína","célula","vírus","organismo","crispr","genomics","biology","protein","cell"],
    "Neurociência":["neurociência","neural","cérebro","cognição","memória","sinapse","neurônio","sono","brain","neuron","cognitive","memory","sleep","cortex"],
    "Computação & IA":["algoritmo","machine learning","inteligência","rede neural","dados","computação","modelo","ia","algorithm","neural","learning","data","deep","quantum"],
    "Física & Astronomia":["física","quântica","partícula","energia","galáxia","astrofísica","cosmologia","physics","quantum","particle","galaxy","dark matter"],
    "Química & Materiais":["química","molécula","síntese","reação","polímero","nanotecnologia","chemistry","molecule","synthesis","nanomaterial"],
    "Engenharia":["engenharia","sistema","robótica","automação","sensor","circuito","engineering","system","robotics","control"],
    "Ciências Sociais":["sociedade","cultura","educação","política","economia","psicologia","social","society","culture","education","economics","psychology"],
    "Ecologia & Clima":["ecologia","clima","ambiente","biodiversidade","ecossistema","ecology","climate","environment","biodiversity","carbon"],
    "Matemática & Estatística":["matemática","estatística","probabilidade","equação","análise","mathematics","statistics","probability"],
}

def compute_topics(kws):
    sc=defaultdict(int)
    for kw in kws:
        for topic,terms in TOPIC_MAP.items():
            if any(t in kw or kw in t for t in terms): sc[topic]+=1
    return dict(sorted(sc.items(),key=lambda x:-x[1])) if sc else {"Pesquisa Geral":1}

def search_refs_online(kws,n=5):
    if not kws: return []
    try:
        r=requests.get("https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query":" ".join(kws[:5]),"limit":n,
                    "fields":"title,authors,year,abstract,venue,externalIds,citationCount"},timeout=8)
        if r.status_code==200:
            res=[]
            for p in r.json().get("data",[]):
                ext=p.get("externalIds",{}) or {}; doi=ext.get("DOI",""); arxiv=ext.get("ArXiv","")
                url=f"https://arxiv.org/abs/{arxiv}" if arxiv else (f"https://doi.org/{doi}" if doi else "")
                alist=p.get("authors",[]) or []; auth=", ".join(a.get("name","") for a in alist[:3])
                if len(alist)>3: auth+=" et al."
                res.append({"title":p.get("title","?"),"authors":auth or "—","year":p.get("year","?"),
                            "venue":p.get("venue","") or "Sem venue","abstract":(p.get("abstract","") or "")[:200],
                            "url":url,"citations":p.get("citationCount",0),"doi":doi})
            return res
    except: pass
    return []

def get_ftype(fname):
    ext=fname.split(".")[-1].lower() if "." in fname else ""
    return {"pdf":"PDF","docx":"Word","doc":"Word","xlsx":"Planilha","xls":"Planilha",
            "csv":"Dados","txt":"Texto","py":"Código Python","r":"Código R",
            "ipynb":"Notebook","pptx":"Apresentação","md":"Markdown",
            "png":"Imagem","jpg":"Imagem","jpeg":"Imagem"}.get(ext,"Arquivo")

def analyze_document(fname,fbytes,ftype,area=""):
    an={"file":fname,"type":ftype,"keywords":[],"authors":[],"years":[],"references":[],
        "references_online":[],"topics":{},"summary":"","strengths":[],"improvements":[],
        "relevance_score":0,"text_length":0,"progress":random.randint(55,98)}
    text=""
    if ftype=="PDF" and fbytes: text=extract_text_pdf(fbytes)
    elif ftype in("Planilha",) and fbytes:
        if fname.lower().endswith(".csv"): text=extract_text_csv(fbytes)
        else: text=extract_text_xlsx(fbytes)
    elif ftype in("Dados",) and fbytes: text=extract_text_csv(fbytes)
    elif fbytes:
        try: text=fbytes.decode("utf-8",errors="ignore")[:30000]
        except: pass
    an["text_length"]=len(text)
    if text:
        an["keywords"]=kw_extract(text,25); an["authors"]=extract_authors(text)
        an["years"]=extract_years(text); an["references"]=extract_refs(text)
        an["topics"]=compute_topics(an["keywords"])
        if area:
            aw=area.lower().split()
            an["relevance_score"]=min(100,sum(1 for w in aw if any(w in k for k in an["keywords"]))*15+random.randint(20,45))
        else: an["relevance_score"]=random.randint(45,80)
        n_ref=len(an["references"]); n_kw=len(an["keywords"])
        if n_ref>5: an["strengths"].append(f"Boa referenciação ({n_ref} refs encontradas)")
        if n_kw>10: an["strengths"].append("Vocabulário técnico rico")
        if an["authors"]: an["strengths"].append(f"Autoria identificada: {an['authors'][0]}")
        if an["years"]: an["strengths"].append(f"Período: {an['years'][-1][0]}–{an['years'][0][0]}")
        if n_ref<3: an["improvements"].append("Adicionar mais referências bibliográficas")
        if n_kw<5: an["improvements"].append("Expandir vocabulário técnico")
        if not an["authors"]: an["improvements"].append("Incluir autoria explícita")
        top_t=list(an["topics"].keys())[:3]
        an["summary"]=f"{len(text.split())} palavras · Temas: {', '.join(top_t)} · Top kws: {', '.join(an['keywords'][:4])}"
    else:
        an["summary"]=f"Arquivo {ftype} — análise de texto não disponível."
        an["relevance_score"]=random.randint(30,55)
        an["keywords"]=kw_extract(fname.lower().replace("_"," ").replace("-"," "),5)
        an["topics"]=compute_topics(an["keywords"])
    return an

# ─── IMAGE ANALYSIS ────────────────────────────────
def analyze_image_advanced(uploaded_file):
    try:
        uploaded_file.seek(0)
        img=PILImage.open(uploaded_file).convert("RGB"); orig=img.size
        small=img.resize((512,512)); arr=np.array(small,dtype=np.float32)
        r,g,b_ch=arr[:,:,0],arr[:,:,1],arr[:,:,2]
        mr,mg,mb=float(r.mean()),float(g.mean()),float(b_ch.mean())
        gray=arr.mean(axis=2)
        gx=np.pad(np.diff(gray,axis=1),((0,0),(0,1)),mode='edge')
        gy=np.pad(np.diff(gray,axis=0),((0,1),(0,0)),mode='edge')
        edge_intensity=float(np.sqrt(gx**2+gy**2).mean())
        h_s=float(np.abs(gy).mean()); v_s=float(np.abs(gx).mean())
        d1=float(np.abs(gx+gy).mean()); d2=float(np.abs(gx-gy).mean())
        strengths={"Horizontal":h_s,"Vertical":v_s,"Diag A":d1,"Diag B":d2}
        line_dir=max(strengths,key=strengths.get)
        hh,ww=gray.shape[0]//2,gray.shape[1]//2
        q=[gray[:hh,:ww].var(),gray[:hh,ww:].var(),gray[hh:,:ww].var(),gray[hh:,ww:].var()]
        sym=1.0-(max(q)-min(q))/(max(q)+1e-5)
        left=gray[:,:gray.shape[1]//2]; right=np.fliplr(gray[:,gray.shape[1]//2:])
        lr_sym=1.0-float(np.abs(left-right).mean())/(gray.mean()+1e-5)
        cx,cy2=gray.shape[1]//2,gray.shape[0]//2
        y_i,x_i=np.mgrid[0:gray.shape[0],0:gray.shape[1]]
        dist=np.sqrt((x_i-cx)**2+(y_i-cy2)**2)
        rb=np.histogram(dist.ravel(),bins=24,weights=gray.ravel())[0]
        has_circular=float(np.std(rb)/(np.mean(rb)+1e-5))<0.32 and sym>0.58
        fft_s=np.fft.fftshift(np.abs(np.fft.fft2(gray))); hf,wf=fft_s.shape
        cm=np.zeros_like(fft_s,dtype=bool); cm[hf//2-22:hf//2+22,wf//2-22:wf//2+22]=True
        has_grid=float(np.percentile(fft_s[~cm],99))>float(np.mean(fft_s[~cm]))*14
        hist=np.histogram(gray,bins=64,range=(0,255))[0]; hn=hist/hist.sum(); hn=hn[hn>0]
        entropy=float(-np.sum(hn*np.log2(hn))); contrast=float(gray.std())
        flat=arr.reshape(-1,3); rounded=(flat//32*32).astype(int)
        uniq,counts=np.unique(rounded,axis=0,return_counts=True)
        palette=[tuple(int(x) for x in uniq[i]) for i in np.argsort(-counts)[:8]]
        skin=(r>95)&(g>40)&(b_ch>20)&(r>g)&(r>b_ch)&((r-g)>15); skin_pct=float(skin.mean())
        warm=mr>mb+15; cool=mb>mr+15
        dom_ch="R" if mr==max(mr,mg,mb) else ("G" if mg==max(mr,mg,mb) else "B")
        sat=float((np.maximum.reduce([r,g,b_ch])-np.minimum.reduce([r,g,b_ch])).mean())/(max(mr,mg,mb)+1e-5)
        shapes=[]
        if has_circular: shapes.append("Circular")
        if has_grid: shapes.append("Grade/Periódico")
        if sym>0.78: shapes.append("Alta Simetria")
        if lr_sym>0.75: shapes.append("Sim. Bilateral")
        if edge_intensity>32: shapes.append("Contornos Nítidos")
        if not shapes: shapes.append("Irregular")
        if skin_pct>0.15 and mr>140: cat,desc,kw,material,obj_type="Histopatologia H&E",f"Tecido orgânico {skin_pct*100:.0f}%.","hematoxylin eosin HE histopathology","Tecido Biológico","Amostra"
        elif has_grid and edge_intensity>18: cat,desc,kw,material,obj_type="Cristalografia/Difração",f"Padrão periódico. I={edge_intensity:.1f}.","X-ray diffraction crystallography TEM","Material Cristalino","Rede Cristalina"
        elif mg>165 and mr<125: cat,desc,kw,material,obj_type="Fluorescência GFP/FITC",f"Verde dominante (G={mg:.0f}).","GFP FITC fluorescence confocal","Proteínas Fluorescentes","Células Marcadas"
        elif mb>165 and mr<110: cat,desc,kw,material,obj_type="Fluorescência DAPI",f"Azul dominante (B={mb:.0f}).","DAPI nuclear staining DNA","DNA / Cromatina","Núcleos"
        elif has_circular and edge_intensity>24: cat,desc,kw,material,obj_type="Microscopia Celular",f"Circulares. I={edge_intensity:.1f}.","cell organelle vesicle bacteria","Componentes Celulares","Células"
        elif edge_intensity>40: cat,desc,kw,material,obj_type="Diagrama Científico",f"Bordas nítidas I={edge_intensity:.1f}.","scientific visualization chart diagram","Dados","Gráfico"
        elif sym>0.82: cat,desc,kw,material,obj_type="Estrutura Molecular",f"Alta simetria ({sym:.3f}).","molecular structure protein crystal","Moléculas","Estrutura"
        else:
            temp="quente" if warm else ("fria" if cool else "neutra")
            cat,desc,kw,material,obj_type="Imagem Científica Geral",f"Temp. {temp}. Brilho={int((mr+mg+mb)/3)}.","scientific image research","Variado","Imagem"
        conf=min(96,48+edge_intensity/2+entropy*2.8+sym*5+(8 if skin_pct>0.1 else 0)+(6 if has_grid else 0))
        return {"category":cat,"description":desc,"kw":kw,"material":material,"object_type":obj_type,
                "confidence":round(conf,1),"lines":{"direction":line_dir,"intensity":round(edge_intensity,2),"strengths":strengths},
                "shapes":shapes,"symmetry":round(sym,3),
                "color":{"r":round(mr,1),"g":round(mg,1),"b":round(mb,1),"warm":warm,"cool":cool,"dom":dom_ch,"sat":round(sat*100,1)},
                "texture":{"entropy":round(entropy,3),"contrast":round(contrast,2),"complexity":"Alta" if entropy>5.5 else ("Média" if entropy>4 else "Baixa")},
                "palette":palette,"size":orig}
    except Exception as e: st.error(f"Erro: {e}"); return None

# ─── SEARCH ────────────────────────────────────────
def search_ss(query,limit=8):
    res=[]
    try:
        r=requests.get("https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query":query,"limit":limit,"fields":"title,authors,year,abstract,venue,externalIds,openAccessPdf,citationCount"},timeout=9)
        if r.status_code==200:
            for p in r.json().get("data",[]):
                ext=p.get("externalIds",{}) or {}; doi=ext.get("DOI",""); arxiv=ext.get("ArXiv","")
                pdf=p.get("openAccessPdf") or {}
                link=pdf.get("url","") or (f"https://arxiv.org/abs/{arxiv}" if arxiv else (f"https://doi.org/{doi}" if doi else ""))
                alist=p.get("authors",[]) or []; auth=", ".join(a.get("name","") for a in alist[:3])
                if len(alist)>3: auth+=" et al."
                res.append({"title":p.get("title","?"),"authors":auth or "—","year":p.get("year","?"),
                    "source":p.get("venue","") or "Semantic Scholar","doi":doi or "—",
                    "abstract":(p.get("abstract","") or "")[:280],"url":link,
                    "citations":p.get("citationCount",0),"origin":"semantic"})
    except: pass
    return res

def search_cr(query,limit=4):
    res=[]
    try:
        r=requests.get("https://api.crossref.org/works",
            params={"query":query,"rows":limit,"select":"title,author,issued,abstract,DOI,container-title,is-referenced-by-count","mailto":"nebula@example.com"},timeout=9)
        if r.status_code==200:
            for p in r.json().get("message",{}).get("items",[]):
                title=(p.get("title") or ["?"])[0]
                ars=p.get("author",[]) or []
                auth=", ".join(f'{a.get("given","").split()[0] if a.get("given") else ""} {a.get("family","")}'.strip() for a in ars[:3])
                if len(ars)>3: auth+=" et al."
                year=(p.get("issued",{}).get("date-parts") or [[None]])[0][0]
                doi=p.get("DOI",""); abstract=re.sub(r'<[^>]+>','',p.get("abstract","") or "")[:280]
                res.append({"title":title,"authors":auth or "—","year":year or "?",
                    "source":(p.get("container-title") or ["CrossRef"])[0],"doi":doi,
                    "abstract":abstract,"url":f"https://doi.org/{doi}" if doi else "","citations":p.get("is-referenced-by-count",0),"origin":"crossref"})
    except: pass
    return res

# ─── RECS ─────────────────────────────────────────
def record(tags,w=1.0):
    email=st.session_state.get("current_user")
    if not email or not tags: return
    prefs=st.session_state.user_prefs.setdefault(email,defaultdict(float))
    for t in tags: prefs[t.lower()]+=w

def get_recs(email,n=2):
    prefs=st.session_state.user_prefs.get(email,{})
    if not prefs: return []
    def score(p): return sum(prefs.get(t.lower(),0) for t in p.get("tags",[])+p.get("connections",[]))
    scored=[(score(p),p) for p in st.session_state.feed_posts if email not in p.get("liked_by",[])]
    return [p for s,p in sorted(scored,key=lambda x:-x[0]) if s>0][:n]

def area_to_tags(area):
    a=(area or "").lower()
    M={"ia":["machine learning","LLM"],"inteligência artificial":["machine learning","LLM"],
       "neurociência":["sono","memória","cognição"],"biologia":["célula","genômica"],
       "física":["quantum","astrofísica"],"medicina":["diagnóstico","terapia"],
       "astronomia":["cosmologia","galáxia"],"computação":["algoritmo","redes"],
       "psicologia":["cognição","comportamento"],"genômica":["DNA","CRISPR"]}
    for k,v in M.items():
        if k in a: return v
    return [w.strip() for w in a.replace(","," ").split() if len(w)>3][:5]

# ─── SEED ─────────────────────────────────────────
SEED_POSTS=[
    {"id":1,"author":"Carlos Mendez","author_email":"carlos@nebula.ai","avatar":"CM","area":"Neurociência",
     "title":"Efeitos da Privação de Sono na Plasticidade Sináptica",
     "abstract":"Investigamos como 24h de privação de sono afetam espinhas dendríticas em ratos Wistar, com redução de 34% na plasticidade hipocampal. Janela crítica nas primeiras 6h de recuperação.",
     "tags":["neurociência","sono","memória","hipocampo"],"likes":47,
     "comments":[{"user":"Maria Silva","text":"Excelente metodologia!"},{"user":"João Lima","text":"Critérios de exclusão?"}],
     "status":"Em andamento","date":"2026-02-10","liked_by":[],"saved_by":[],"connections":["sono","memória"],"views":312},
    {"id":2,"author":"Luana Freitas","author_email":"luana@nebula.ai","avatar":"LF","area":"Biomedicina",
     "title":"CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras",
     "abstract":"Vetor AAV9 modificado para entrega de CRISPR no gene DMD com eficiência de 78% em modelos mdx. Publicação em Cell prevista Q2 2026.",
     "tags":["CRISPR","gene terapia","músculo","AAV9"],"likes":93,
     "comments":[{"user":"Ana","text":"Quando iniciam os trials?"}],
     "status":"Publicado","date":"2026-01-28","liked_by":[],"saved_by":[],"connections":["genômica","distrofia"],"views":891},
    {"id":3,"author":"Rafael Souza","author_email":"rafael@nebula.ai","avatar":"RS","area":"Computação",
     "title":"Redes Neurais Quântico-Clássicas para Otimização Combinatória",
     "abstract":"Arquitetura híbrida variacional: qubits supercondutores + camadas densas. TSP com 40% menos iterações que métodos clássicos.",
     "tags":["quantum ML","otimização","TSP"],"likes":201,
     "comments":[],"status":"Em andamento","date":"2026-02-15","liked_by":[],"saved_by":[],"connections":["computação quântica"],"views":1240},
    {"id":4,"author":"Priya Nair","author_email":"priya@nebula.ai","avatar":"PN","area":"Astrofísica",
     "title":"Detecção de Matéria Escura via Lentes Gravitacionais Fracas",
     "abstract":"Mapeamento com 100M galáxias do DES Y3. Tensão de 2.8σ com ΛCDM em escalas <1 Mpc.",
     "tags":["astrofísica","matéria escura","cosmologia","DES"],"likes":312,
     "comments":[],"status":"Publicado","date":"2026-02-01","liked_by":[],"saved_by":[],"connections":["cosmologia"],"views":2180},
    {"id":5,"author":"João Lima","author_email":"joao@nebula.ai","avatar":"JL","area":"Psicologia",
     "title":"Viés de Confirmação em Decisões Médicas Assistidas por IA",
     "abstract":"Estudo duplo-cego com 240 médicos revelou que IA mal calibrada amplifica vieses cognitivos em 22% dos casos.",
     "tags":["psicologia","IA","cognição","medicina"],"likes":78,
     "comments":[{"user":"Carlos M.","text":"Muito relevante!"}],
     "status":"Publicado","date":"2026-02-08","liked_by":[],"saved_by":[],"connections":["cognição","IA"],"views":456},
]
SEED_USERS={
    "demo@nebula.ai":{"name":"Ana Pesquisadora","password":hp("demo123"),"bio":"Pesquisadora em IA e Ciências Cognitivas | UFMG","area":"Inteligência Artificial","followers":128,"following":47,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "carlos@nebula.ai":{"name":"Carlos Mendez","password":hp("nebula123"),"bio":"Neurocientista | UFMG","area":"Neurociência","followers":210,"following":45,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "luana@nebula.ai":{"name":"Luana Freitas","password":hp("nebula123"),"bio":"Biomédica | FIOCRUZ","area":"Biomedicina","followers":178,"following":62,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "rafael@nebula.ai":{"name":"Rafael Souza","password":hp("nebula123"),"bio":"Computação Quântica | USP","area":"Computação","followers":340,"following":88,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "priya@nebula.ai":{"name":"Priya Nair","password":hp("nebula123"),"bio":"Astrofísica | MIT","area":"Astrofísica","followers":520,"following":31,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "joao@nebula.ai":{"name":"João Lima","password":hp("nebula123"),"bio":"Psicólogo Cognitivo | UNICAMP","area":"Psicologia","followers":95,"following":120,"verified":True,"2fa_enabled":False,"photo_b64":None},
}
CHAT_INIT={
    "carlos@nebula.ai":[{"from":"carlos@nebula.ai","text":"Oi! Vi seu comentário.","time":"09:14"},{"from":"me","text":"Achei muito interessante!","time":"09:16"}],
    "luana@nebula.ai":[{"from":"luana@nebula.ai","text":"Podemos colaborar?","time":"ontem"}],
    "rafael@nebula.ai":[{"from":"rafael@nebula.ai","text":"Compartilhei o repositório.","time":"08:30"}],
}

# ─── SESSION ───────────────────────────────────────
def init():
    if "initialized" in st.session_state: return
    st.session_state.initialized=True
    disk=load_db(); disk_users=disk.get("users",{})
    if not isinstance(disk_users,dict): disk_users={}
    st.session_state.setdefault("users",{**SEED_USERS,**disk_users})
    st.session_state.setdefault("logged_in",False)
    st.session_state.setdefault("current_user",None)
    st.session_state.setdefault("page","login")
    st.session_state.setdefault("profile_view",None)
    disk_prefs=disk.get("user_prefs",{})
    st.session_state.setdefault("user_prefs",{k:defaultdict(float,v) for k,v in disk_prefs.items()})
    st.session_state.setdefault("pending_verify",None)
    st.session_state.setdefault("pending_2fa",None)
    raw_posts=disk.get("feed_posts",[dict(p) for p in SEED_POSTS])
    for p in raw_posts:
        p.setdefault("author_email",""); p.setdefault("liked_by",[])
        p.setdefault("saved_by",[]); p.setdefault("comments",[])
        p.setdefault("views",random.randint(80,800))
    st.session_state.setdefault("feed_posts",raw_posts)
    st.session_state.setdefault("folders",disk.get("folders",{}))
    st.session_state.setdefault("folder_bytes",{})
    st.session_state.setdefault("chat_contacts",list(SEED_USERS.keys()))
    st.session_state.setdefault("chat_messages",{k:list(v) for k,v in CHAT_INIT.items()})
    st.session_state.setdefault("active_chat",None)
    st.session_state.setdefault("followed",["carlos@nebula.ai","luana@nebula.ai"])
    st.session_state.setdefault("notifications",["Carlos curtiu sua pesquisa","Nova conexão detectada"])
    st.session_state.setdefault("scholar_cache",{})
    st.session_state.setdefault("saved_articles",disk.get("saved_articles",[]))
    st.session_state.setdefault("img_result",None)
    st.session_state.setdefault("search_results",None)
    st.session_state.setdefault("last_sq","")
    st.session_state.setdefault("stats_data",{"h_index":4,"fator_impacto":3.8,"notes":""})
    st.session_state.setdefault("compose_open",False)

init()

# ═══════════════════════════════════════════════════════
# CSS — ORIGINAL DARK BLUE LIQUID GLASS + ICONS + FIXED
# ═══════════════════════════════════════════════════════
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Geist:wght@300;400;500;600;700;800;900&display=swap');

:root {
  --bg: #080c18;
  --surf: #0d1422;
  --surf2: #111827;
  --border: rgba(255,255,255,.07);
  --border2: rgba(255,255,255,.13);
  --blue: #3b82f6;
  --blue-d: #1d4ed8;
  --blue2: #2563eb;
  --cyan: #06b6d4;
  --cyan2: #22d3ee;
  --text: #f1f5f9;
  --text2: #94a3b8;
  --muted: #64748b;
  --ok: #22c55e;
  --glass-bg:  rgba(255,255,255,.04);
  --glass-bg2: rgba(255,255,255,.07);
  --glass-border:  rgba(255,255,255,.08);
  --glass-border2: rgba(255,255,255,.14);
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}

html,body,.stApp{
  background:var(--bg)!important;
  color:var(--text)!important;
  font-family:'Inter',-apple-system,sans-serif!important;
}

/* ── AMBIENT GLOW ── */
.stApp::before{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:
    radial-gradient(ellipse 80% 50% at 20% -10%,rgba(59,130,246,.18) 0%,transparent 60%),
    radial-gradient(ellipse 60% 70% at 80% 110%,rgba(6,182,212,.10) 0%,transparent 55%),
    radial-gradient(ellipse 100% 100% at 50% 50%,rgba(15,23,42,0) 0%,#080c18 70%);
}
/* Stars */
.stApp::after{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:
    radial-gradient(1.2px 1.2px at 10% 14%,rgba(147,197,253,.7) 0%,transparent 100%),
    radial-gradient(1px 1px at 28% 44%,rgba(147,197,253,.45) 0%,transparent 100%),
    radial-gradient(1.3px 1.3px at 60% 18%,rgba(96,165,245,.55) 0%,transparent 100%),
    radial-gradient(1px 1px at 79% 65%,rgba(147,197,253,.35) 0%,transparent 100%),
    radial-gradient(1px 1px at 91% 32%,rgba(96,165,245,.4) 0%,transparent 100%),
    radial-gradient(1px 1px at 46% 87%,rgba(147,197,253,.28) 0%,transparent 100%),
    radial-gradient(1px 1px at 17% 77%,rgba(96,165,245,.2) 0%,transparent 100%);
}

[data-testid="collapsedControl"],
section[data-testid="stSidebar"]{display:none!important;}

.block-container{
  padding-top:0!important;padding-bottom:5rem!important;
  max-width:1380px!important;position:relative;z-index:1;
  padding-left:.75rem!important;padding-right:.75rem!important;
}

/* ── TYPOGRAPHY ── */
h1{font-family:'Geist',sans-serif!important;font-size:1.65rem!important;font-weight:700!important;letter-spacing:-.03em;}
h2{font-family:'Geist',sans-serif!important;font-size:1.1rem!important;font-weight:600!important;}
h3{font-family:'Geist',sans-serif!important;font-size:.92rem!important;font-weight:600!important;}

/* ══════════════════════════════════════
   LIQUID GLASS TOP NAV
══════════════════════════════════════ */
.topnav-glass{
  position:sticky;top:0;z-index:1000;
  background:rgba(8,12,24,.82);
  backdrop-filter:blur(48px) saturate(200%);
  -webkit-backdrop-filter:blur(48px) saturate(200%);
  border-bottom:1px solid var(--glass-border);
  padding:0 1.6rem;
  display:flex;align-items:center;gap:.6rem;
  height:60px;
  box-shadow:0 1px 0 rgba(255,255,255,.04),0 8px 32px rgba(0,0,0,.45);
  margin-bottom:1.4rem;
}
.topnav-logo{
  font-family:'Geist',sans-serif;font-size:1.32rem;font-weight:900;
  background:linear-gradient(135deg,#60a5fa 20%,#22d3ee 80%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;white-space:nowrap;flex-shrink:0;letter-spacing:-.06em;
}
.topnav-pills{
  flex:1;display:flex;align-items:center;gap:3px;
  overflow-x:auto;padding:0 .4rem;scrollbar-width:none;
}
.topnav-pills::-webkit-scrollbar{display:none;}

/* Individual pill — visual only (not clickable) */
.npill{
  display:inline-flex;align-items:center;gap:5px;
  padding:.34rem .82rem;border-radius:50px;
  font-size:.77rem;font-weight:500;
  white-space:nowrap;color:var(--text2);
  background:transparent;border:1px solid transparent;
  pointer-events:none;transition:all .18s;
}
.npill.is-active{
  color:#e2e8f0;
  background:linear-gradient(135deg,rgba(37,99,235,.4) 0%,rgba(6,182,212,.18) 100%);
  border:1px solid rgba(96,165,250,.32);
  box-shadow:0 2px 16px rgba(37,99,235,.22),inset 0 1px 0 rgba(147,197,253,.1);
}
.npill-icon{opacity:.7;font-size:.75rem;}

/* INVISIBLE click overlay row */
.tnav-overlay{
  position:relative;margin-top:-60px;height:60px;z-index:999;
}
.tnav-overlay .stButton>button{
  background:transparent!important;border:none!important;
  color:transparent!important;font-size:0!important;
  box-shadow:none!important;border-radius:50px!important;
  width:100%!important;height:60px!important;
  padding:0!important;cursor:pointer!important;
}
.tnav-overlay .stButton>button:hover{
  background:rgba(255,255,255,.03)!important;
  transform:none!important;box-shadow:none!important;
}

/* ══════════════════════════════════════
   ALL BUTTONS — liquid glass baseline
══════════════════════════════════════ */
.stButton>button{
  font-family:'Inter',sans-serif!important;
  font-weight:500!important;font-size:.81rem!important;
  border-radius:12px!important;
  border:1px solid var(--glass-border)!important;
  color:var(--text2)!important;
  background:var(--glass-bg)!important;
  padding:.48rem .95rem!important;
  transition:all .18s cubic-bezier(.4,0,.2,1)!important;
  box-shadow:0 2px 12px rgba(0,0,0,.2),inset 0 1px 0 rgba(255,255,255,.05)!important;
  backdrop-filter:blur(12px)!important;
  white-space:nowrap!important;
  display:inline-flex!important;align-items:center!important;justify-content:center!important;gap:5px!important;
}
.stButton>button:hover{
  background:rgba(59,130,246,.14)!important;
  border-color:rgba(96,165,250,.3)!important;
  color:var(--text)!important;
  box-shadow:0 4px 18px rgba(37,99,235,.18),inset 0 1px 0 rgba(255,255,255,.06)!important;
  transform:translateY(-1px)!important;
}
.stButton>button:active{transform:scale(.97)!important;}

/* PRIMARY */
.btn-primary .stButton>button{
  background:linear-gradient(135deg,#2563eb,#1d4ed8)!important;
  border-color:rgba(59,130,246,.55)!important;
  color:#fff!important;font-weight:600!important;
  box-shadow:0 4px 18px rgba(37,99,235,.38),inset 0 1px 0 rgba(255,255,255,.16)!important;
}
.btn-primary .stButton>button:hover{
  background:linear-gradient(135deg,#3b82f6,#2563eb)!important;
  box-shadow:0 6px 26px rgba(37,99,235,.48)!important;
  transform:translateY(-1px)!important;
}

/* DANGER */
.btn-danger .stButton>button{
  background:rgba(239,68,68,.1)!important;
  border-color:rgba(239,68,68,.25)!important;
  color:#fca5a5!important;
}
.btn-danger .stButton>button:hover{
  background:rgba(239,68,68,.18)!important;
  border-color:rgba(239,68,68,.4)!important;
  transform:translateY(-1px)!important;
}

/* ══════════════════════════════════════
   STORY CIRCLES — the circle IS the button
══════════════════════════════════════ */
/* Publish circle */
.story-pub .stButton>button{
  width:62px!important;height:62px!important;
  border-radius:50%!important;padding:0!important;
  background:rgba(6,182,212,.08)!important;
  border:2px dashed rgba(6,182,212,.45)!important;
  color:#22d3ee!important;font-size:1.55rem!important;font-weight:300!important;
  box-shadow:0 4px 16px rgba(0,0,0,.35)!important;
  transition:all .2s cubic-bezier(.34,1.56,.64,1)!important;
  margin:0 auto!important;display:flex!important;
}
.story-pub .stButton>button:hover{
  background:rgba(6,182,212,.18)!important;
  border-color:rgba(6,182,212,.72)!important;
  box-shadow:0 0 24px rgba(6,182,212,.22),0 4px 16px rgba(0,0,0,.35)!important;
  transform:scale(1.05)!important;
}
.story-pub-open .stButton>button{
  background:rgba(6,182,212,.22)!important;
  border:2px solid rgba(6,182,212,.65)!important;
  color:#22d3ee!important;font-size:1.2rem!important;
  box-shadow:0 0 20px rgba(6,182,212,.28)!important;
  transform:rotate(45deg)!important;
}

/* Regular story circles */
.story-circ .stButton>button{
  width:62px!important;height:62px!important;
  border-radius:50%!important;padding:0!important;
  background:linear-gradient(135deg,#1e3a8a,#2563eb)!important;
  border:2px solid rgba(255,255,255,.14)!important;
  color:white!important;font-family:'Geist',sans-serif!important;
  font-weight:700!important;font-size:1rem!important;
  box-shadow:0 4px 16px rgba(0,0,0,.4)!important;
  transition:all .2s cubic-bezier(.34,1.56,.64,1)!important;
  margin:0 auto!important;display:flex!important;
}
.story-circ .stButton>button:hover{
  border-color:rgba(59,130,246,.6)!important;
  box-shadow:0 0 0 3px rgba(59,130,246,.2),0 6px 22px rgba(0,0,0,.45)!important;
  transform:translateY(-3px) scale(1.06)!important;
}
/* Followed = green ring */
.story-fol .stButton>button{
  border-color:rgba(34,197,94,.5)!important;
  box-shadow:0 0 0 2.5px rgba(34,197,94,.18),0 4px 16px rgba(0,0,0,.4)!important;
}
.story-fol .stButton>button:hover{
  border-color:rgba(34,197,94,.75)!important;
  box-shadow:0 0 0 3px rgba(34,197,94,.22),0 6px 22px rgba(0,0,0,.45)!important;
  transform:translateY(-3px) scale(1.06)!important;
}

/* COMPOSE PROMPT BAR — single button styled as text field */
.compose-prompt .stButton>button{
  width:100%!important;
  background:rgba(255,255,255,.04)!important;
  border:1px solid var(--glass-border)!important;
  border-radius:40px!important;
  color:var(--muted)!important;
  font-size:.875rem!important;font-weight:400!important;
  padding:.72rem 1.4rem!important;
  text-align:left!important;justify-content:flex-start!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04)!important;
  backdrop-filter:blur(12px)!important;
  transition:border-color .18s,background .18s!important;
}
.compose-prompt .stButton>button:hover{
  background:rgba(255,255,255,.06)!important;
  border-color:rgba(59,130,246,.28)!important;
  color:var(--text2)!important;
  transform:none!important;box-shadow:none!important;
}

/* ══════════════════════════════════════
   INPUTS
══════════════════════════════════════ */
.stTextInput input,.stTextArea textarea{
  background:rgba(255,255,255,.04)!important;
  border:1px solid var(--glass-border)!important;
  border-radius:12px!important;color:var(--text)!important;
  font-family:'Inter',sans-serif!important;font-size:.875rem!important;
  transition:all .18s!important;
}
.stTextInput input:focus,.stTextArea textarea:focus{
  border-color:rgba(59,130,246,.45)!important;
  box-shadow:0 0 0 3px rgba(59,130,246,.1)!important;
  background:rgba(255,255,255,.06)!important;
}
.stTextInput label,.stTextArea label,
.stSelectbox label,.stFileUploader label,.stNumberInput label{
  color:var(--muted)!important;font-size:.68rem!important;
  letter-spacing:.07em!important;text-transform:uppercase!important;font-weight:600!important;
}

/* ══════════════════════════════════════
   GLASS CARDS
══════════════════════════════════════ */
.card{
  background:var(--glass-bg);
  backdrop-filter:blur(24px) saturate(160%);
  border:1px solid var(--glass-border);
  border-radius:20px;
  box-shadow:0 4px 24px rgba(0,0,0,.3),inset 0 1px 0 rgba(255,255,255,.05);
  position:relative;overflow:hidden;
  transition:border-color .2s,box-shadow .2s;
}
.card::after{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.08),transparent);pointer-events:none;}
.card:hover{border-color:var(--glass-border2);box-shadow:0 8px 40px rgba(0,0,0,.4);}

/* POST CARD */
.post{
  background:var(--glass-bg);border:1px solid var(--glass-border);
  border-radius:20px;margin-bottom:.85rem;overflow:hidden;
  box-shadow:0 2px 20px rgba(0,0,0,.25);
  animation:fadeUp .28s cubic-bezier(.34,1.56,.64,1) both;
  transition:border-color .18s,box-shadow .18s;position:relative;
}
.post::after{content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.07),transparent);pointer-events:none;}
.post:hover{border-color:var(--glass-border2);box-shadow:0 8px 32px rgba(0,0,0,.4);}
@keyframes fadeUp{from{opacity:0;transform:translateY(12px);}to{opacity:1;transform:translateY(0);}}

/* COMPOSE AREA */
.compose-area{
  background:rgba(255,255,255,.05);border:1px solid rgba(59,130,246,.2);
  border-radius:20px;padding:1.2rem 1.4rem;margin-bottom:.9rem;
  box-shadow:0 4px 24px rgba(0,0,0,.2),inset 0 1px 0 rgba(255,255,255,.06);
  animation:fadeUp .22s ease both;
}

/* TABS */
.stTabs [data-baseweb="tab-list"]{
  background:rgba(255,255,255,.03)!important;border:1px solid var(--glass-border)!important;
  border-radius:12px!important;padding:4px!important;gap:2px!important;
  backdrop-filter:blur(20px)!important;
}
.stTabs [data-baseweb="tab"]{
  background:transparent!important;color:var(--muted)!important;
  border-radius:9px!important;font-size:.80rem!important;
  font-family:'Inter',sans-serif!important;font-weight:500!important;
}
.stTabs [aria-selected="true"]{
  background:rgba(59,130,246,.18)!important;color:#93c5fd!important;
  border:1px solid rgba(59,130,246,.25)!important;
}
.stTabs [data-baseweb="tab-panel"]{background:transparent!important;padding-top:.9rem!important;}

/* SELECT, FILE, EXPANDER */
.stSelectbox [data-baseweb="select"]{background:rgba(255,255,255,.04)!important;border:1px solid var(--glass-border)!important;border-radius:12px!important;}
.stFileUploader section{background:rgba(255,255,255,.03)!important;border:1.5px dashed rgba(59,130,246,.25)!important;border-radius:14px!important;}
.stExpander{background:rgba(255,255,255,.03)!important;border:1px solid var(--glass-border)!important;border-radius:14px!important;}

/* AVATAR */
.av{border-radius:50%;background:linear-gradient(135deg,#1e3a8a,#2563eb);
  display:flex;align-items:center;justify-content:center;
  font-family:'Geist',sans-serif;font-weight:700;color:white;
  flex-shrink:0;overflow:hidden;border:1.5px solid rgba(255,255,255,.12);}
.av img{width:100%;height:100%;object-fit:cover;border-radius:50%;}

/* TAGS */
.tag{display:inline-block;background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.18);
  border-radius:20px;padding:2px 10px;font-size:.67rem;color:#93c5fd;margin:2px;font-weight:500;}

/* BADGES */
.badge-on  {display:inline-block;background:rgba(251,191,36,.1); border:1px solid rgba(251,191,36,.25); border-radius:20px;padding:2px 10px;font-size:.67rem;font-weight:600;color:#fcd34d;}
.badge-pub {display:inline-block;background:rgba(34,197,94,.1);  border:1px solid rgba(34,197,94,.25);  border-radius:20px;padding:2px 10px;font-size:.67rem;font-weight:600;color:#4ade80;}
.badge-done{display:inline-block;background:rgba(167,139,250,.1);border:1px solid rgba(167,139,250,.25);border-radius:20px;padding:2px 10px;font-size:.67rem;font-weight:600;color:#c4b5fd;}
.badge-rec {display:inline-block;background:rgba(6,182,212,.1);  border:1px solid rgba(6,182,212,.25);  border-radius:20px;padding:2px 10px;font-size:.67rem;font-weight:600;color:#22d3ee;}

/* METRICS */
.mbox{background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:16px;padding:1rem;text-align:center;}
.mval{font-family:'Geist',sans-serif;font-size:2rem;font-weight:700;background:linear-gradient(135deg,#60a5fa,#22d3ee);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mlbl{font-size:.66rem;color:var(--muted);margin-top:4px;letter-spacing:.07em;text-transform:uppercase;}

/* PROG BAR */
.prog-wrap{height:4px;background:rgba(255,255,255,.06);border-radius:4px;overflow:hidden;margin:.2rem 0 .45rem;}
.prog-fill{height:100%;border-radius:4px;transition:width .6s ease;}

/* ONLINE */
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.5;transform:scale(.8)}}
.dot-on {display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--ok);animation:pulse 2s infinite;margin-right:5px;vertical-align:middle;}
.dot-off{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--muted);margin-right:5px;vertical-align:middle;}

/* SIDEBAR CARD */
.sc{background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:18px;padding:1rem;margin-bottom:.75rem;}
/* SEARCH CARD */
.scard{background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:14px;padding:.95rem 1.15rem;margin-bottom:.6rem;transition:border-color .15s;}
.scard:hover{border-color:var(--glass-border2);}
/* CHAT */
.bme  {background:linear-gradient(135deg,rgba(37,99,235,.5),rgba(6,182,212,.22));border:1px solid rgba(59,130,246,.22);border-radius:18px 18px 4px 18px;padding:.6rem .95rem;max-width:68%;margin-left:auto;margin-bottom:6px;font-size:.84rem;line-height:1.6;}
.bthem{background:rgba(255,255,255,.05);border:1px solid var(--glass-border);border-radius:18px 18px 18px 4px;padding:.6rem .95rem;max-width:68%;margin-bottom:6px;font-size:.84rem;line-height:1.6;}
.cmt{background:rgba(255,255,255,.04);border:1px solid var(--glass-border);border-radius:12px;padding:.6rem .95rem;margin-bottom:.35rem;}
/* ABOX */
.abox{background:rgba(255,255,255,.04);border:1px solid rgba(59,130,246,.18);border-radius:14px;padding:1.1rem;margin-bottom:.8rem;}
.pbox{background:rgba(6,182,212,.04);border:1px solid rgba(6,182,212,.18);border-radius:14px;padding:1rem;margin-bottom:.75rem;}
.img-rc{background:rgba(6,182,212,.04);border:1px solid rgba(6,182,212,.15);border-radius:14px;padding:1rem;margin-bottom:.6rem;}
/* DIVIDER */
.dtxt{display:flex;align-items:center;gap:.8rem;margin:.9rem 0;font-size:.66rem;color:var(--muted);letter-spacing:.08em;text-transform:uppercase;font-weight:600;}
.dtxt::before,.dtxt::after{content:'';flex:1;height:1px;background:var(--glass-border);}
/* PROFILE HERO */
.prof-hero{background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:24px;padding:2rem;display:flex;gap:1.5rem;align-items:flex-start;box-shadow:0 4px 32px rgba(0,0,0,.35);position:relative;overflow:hidden;margin-bottom:1.2rem;}
.prof-hero::after{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.08),transparent);pointer-events:none;}
.prof-photo{width:88px;height:88px;border-radius:50%;background:linear-gradient(135deg,#1e3a8a,#2563eb);border:2px solid rgba(255,255,255,.14);flex-shrink:0;overflow:hidden;display:flex;align-items:center;justify-content:center;font-size:1.9rem;font-weight:700;color:white;}
.prof-photo img{width:100%;height:100%;object-fit:cover;border-radius:50%;}
/* PERSON ROW */
.person-row{display:flex;align-items:center;gap:9px;padding:.5rem .5rem;border-radius:10px;border:1px solid transparent;transition:all .15s;margin-bottom:2px;}
.person-row:hover{background:rgba(255,255,255,.04);border-color:var(--glass-border);}
/* MISC */
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,.1);border-radius:4px;}
hr{border:none;border-top:1px solid var(--glass-border)!important;margin:1rem 0;}
label{color:var(--text2)!important;}
.stCheckbox label,.stRadio label{color:var(--text)!important;}
.stAlert{background:rgba(255,255,255,.04)!important;border:1px solid var(--glass-border)!important;border-radius:14px!important;}
input[type="number"]{background:rgba(255,255,255,.04)!important;border:1px solid var(--glass-border)!important;border-radius:12px!important;color:var(--text)!important;}
.pw{animation:fadeIn .22s ease both;}
@keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
/* RADIO FILTERS */
.stRadio>div{display:flex!important;gap:5px!important;flex-wrap:wrap!important;}
.stRadio>div>label{background:var(--glass-bg)!important;border:1px solid var(--glass-border)!important;border-radius:50px!important;padding:.3rem .82rem!important;font-size:.76rem!important;font-weight:500!important;color:var(--text2)!important;cursor:pointer!important;transition:all .18s!important;}
.stRadio>div>label:hover{border-color:var(--glass-border2)!important;color:var(--text)!important;}
/* ANALYSIS */
.chart-glass{background:var(--glass-bg);border:1px solid var(--glass-border);border-radius:14px;padding:.75rem;margin-bottom:.75rem;}
.ref-item{background:rgba(6,182,212,.04);border:1px solid rgba(6,182,212,.14);border-radius:11px;padding:.6rem .9rem;margin-bottom:.4rem;font-size:.78rem;color:var(--text2);line-height:1.6;}
.str-ok {background:rgba(34,197,94,.07);border:1px solid rgba(34,197,94,.2);border-radius:9px;padding:.36rem .72rem;font-size:.75rem;color:#4ade80;margin-bottom:.3rem;}
.str-imp{background:rgba(251,191,36,.07);border:1px solid rgba(251,191,36,.2);border-radius:9px;padding:.36rem .72rem;font-size:.75rem;color:#fbbf24;margin-bottom:.3rem;}
/* STORY LABELS */
.slabel{text-align:center;font-size:.64rem;font-weight:500;color:var(--text2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:72px;margin:3px auto 0;}
.ssubl {text-align:center;font-size:.57rem;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:72px;margin:0 auto;}
</style>""",unsafe_allow_html=True)

# ─── HELPERS ───────────────────────────────────────
def avh(initials,sz=40,photo=None,bg="linear-gradient(135deg,#1e3a8a,#2563eb)"):
    fs=max(sz//3,9)
    if photo: return f'<div class="av" style="width:{sz}px;height:{sz}px"><img src="{photo}"/></div>'
    return f'<div class="av" style="width:{sz}px;height:{sz}px;font-size:{fs}px;background:{bg}">{initials}</div>'
def tags_html(tags): return ' '.join(f'<span class="tag">{t}</span>' for t in (tags or []))
def badge(s):
    cls={"Publicado":"badge-pub","Concluído":"badge-done"}.get(s,"badge-on")
    return f'<span class="{cls}">{s}</span>'
def prog_bar(pct,color="#3b82f6"): return f'<div class="prog-wrap"><div class="prog-fill" style="width:{pct}%;background:{color}"></div></div>'
def pc():
    return dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#64748b",family="Inter",size=11),margin=dict(l=10,r=10,t=40,b=10),
                xaxis=dict(showgrid=False,color="#64748b",tickfont=dict(size=10)),
                yaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,.05)",color="#64748b",tickfont=dict(size=10)))

USER_GRADS=[
    ("135deg","#1e3a8a","#2563eb"),("135deg","#064e3b","#059669"),
    ("135deg","#4c1d95","#7c3aed"),("135deg","#7c2d12","#ea580c"),
    ("135deg","#831843","#db2777"),("135deg","#1e3a5f","#0ea5e9"),
]
def ugrad(email):
    d,c1,c2=USER_GRADS[hash(email)%len(USER_GRADS)]
    return f"linear-gradient({d},{c1},{c2})"

# ─── AUTH ──────────────────────────────────────────
def page_login():
    _,col,_=st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown("""<div style="text-align:center;margin-bottom:3rem">
          <div style="font-family:'Geist',sans-serif;font-size:4rem;font-weight:900;
            background:linear-gradient(135deg,#60a5fa 20%,#22d3ee 80%);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
            letter-spacing:-.08em;line-height:.9;margin-bottom:.8rem">Nebula</div>
          <div style="color:#334155;font-size:.66rem;letter-spacing:.28em;text-transform:uppercase;font-weight:600">
            Rede do Conhecimento Científico</div></div>""",unsafe_allow_html=True)
        tab_in,tab_up=st.tabs(["  🔑 Entrar  ","  ✦ Criar conta  "])
        with tab_in:
            email=st.text_input("E-mail",placeholder="seu@email.com",key="li_e")
            pw=st.text_input("Senha",placeholder="••••••••",type="password",key="li_p")
            st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
            if st.button("→ Entrar",use_container_width=True,key="btn_li"):
                u=st.session_state.users.get(email)
                if not u: st.error("E-mail não encontrado.")
                elif u["password"]!=hp(pw): st.error("Senha incorreta.")
                elif u.get("2fa_enabled"):
                    c=code6(); st.session_state.pending_2fa={"email":email,"code":c}; st.session_state.page="2fa"; st.rerun()
                else:
                    st.session_state.logged_in=True; st.session_state.current_user=email
                    record(area_to_tags(u.get("area","")),1.0); st.session_state.page="feed"; st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)
            st.markdown('<div style="text-align:center;color:#334155;font-size:.7rem;margin-top:.7rem">Demo: demo@nebula.ai / demo123</div>',unsafe_allow_html=True)
        with tab_up:
            n_name=st.text_input("Nome completo",key="su_n"); n_email=st.text_input("E-mail",key="su_e")
            n_area=st.text_input("Área de pesquisa",key="su_a"); n_pw=st.text_input("Senha",type="password",key="su_p"); n_pw2=st.text_input("Confirmar senha",type="password",key="su_p2")
            st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
            if st.button("✓ Criar conta",use_container_width=True,key="btn_su"):
                if not all([n_name,n_email,n_area,n_pw,n_pw2]): st.error("Preencha todos os campos.")
                elif n_pw!=n_pw2: st.error("Senhas não coincidem.")
                elif len(n_pw)<6: st.error("Mínimo 6 caracteres.")
                elif n_email in st.session_state.users: st.error("E-mail já cadastrado.")
                else:
                    c=code6(); st.session_state.pending_verify={"email":n_email,"name":n_name,"pw":hp(n_pw),"area":n_area,"code":c}; st.session_state.page="verify_email"; st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)

def page_verify_email():
    pv=st.session_state.pending_verify
    _,col,_=st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown(f"""<div class="card" style="padding:2rem;text-align:center">
          <div style="font-size:2.5rem;margin-bottom:1rem;opacity:.7">✉</div><h2>Verifique seu e-mail</h2>
          <div style="background:rgba(37,99,235,.07);border:1px solid rgba(59,130,246,.18);border-radius:14px;padding:1.2rem;margin:1.2rem 0">
            <div style="font-size:.62rem;color:#475569;text-transform:uppercase;letter-spacing:.1em;margin-bottom:6px;font-weight:600">Código (demo)</div>
            <div style="font-family:'Geist',sans-serif;font-size:2.8rem;font-weight:900;letter-spacing:.32em;color:#60a5fa">{pv['code']}</div>
          </div></div>""",unsafe_allow_html=True)
        typed=st.text_input("Código",max_chars=6,key="ev_c")
        st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
        if st.button("✓ Verificar",use_container_width=True,key="btn_ev"):
            if typed.strip()==pv["code"]:
                st.session_state.users[pv["email"]]={"name":pv["name"],"password":pv["pw"],"bio":"","area":pv["area"],"followers":0,"following":0,"verified":True,"2fa_enabled":False,"photo_b64":None}
                save_db(); st.session_state.pending_verify=None; st.session_state.logged_in=True; st.session_state.current_user=pv["email"]
                record(area_to_tags(pv["area"]),2.0); st.session_state.page="feed"; st.rerun()
            else: st.error("Código inválido.")
        st.markdown('</div>',unsafe_allow_html=True)
        if st.button("← Voltar",key="btn_ev_bk"): st.session_state.page="login"; st.rerun()

def page_2fa():
    p2=st.session_state.pending_2fa
    _,col,_=st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown(f"""<div class="card" style="padding:2rem;text-align:center">
          <div style="font-size:2.5rem;margin-bottom:1rem;opacity:.7">⚿</div><h2>Verificação 2FA</h2>
          <div style="background:rgba(37,99,235,.07);border:1px solid rgba(59,130,246,.18);border-radius:14px;padding:1rem;margin:1rem 0">
            <div style="font-family:'Geist',sans-serif;font-size:2.8rem;font-weight:900;letter-spacing:.28em;color:#60a5fa">{p2['code']}</div>
          </div></div>""",unsafe_allow_html=True)
        typed=st.text_input("Código",max_chars=6,key="fa_c",label_visibility="collapsed")
        st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
        if st.button("✓ Verificar",use_container_width=True,key="btn_fa"):
            if typed.strip()==p2["code"]:
                st.session_state.logged_in=True; st.session_state.current_user=p2["email"]
                st.session_state.pending_2fa=None; st.session_state.page="feed"; st.rerun()
            else: st.error("Código inválido.")
        st.markdown('</div>',unsafe_allow_html=True)
        if st.button("← Voltar",key="btn_fa_bk"): st.session_state.page="login"; st.rerun()

# ─── TOP NAV ───────────────────────────────────────
NAV=[
    ("feed",     "Feed",      "◈"),
    ("search",   "Artigos",   "⊗"),
    ("knowledge","Conexões",  "⊙"),
    ("folders",  "Pastas",    "▣"),
    ("analytics","Análises",  "◎"),
    ("img_search","Imagem",   "⊞"),
    ("chat",     "Chat",      "◻"),
    ("settings", "Perfil",    "⊛"),
]

def render_topnav():
    u=guser(); name=u.get("name","?"); photo=u.get("photo_b64"); in_=ini(name)
    cur=st.session_state.page; notif=len(st.session_state.notifications)
    pills="".join(
        f'<span class="npill{"  is-active" if cur==k else ""}">'
        f'<span class="npill-icon">{icon}</span>{lbl}</span>'
        for k,lbl,icon in NAV
    )
    av_inner=(f"<img src='{photo}' style='width:100%;height:100%;object-fit:cover;border-radius:50%'/>" if photo else in_)
    nb=(f'<span style="background:#ef4444;color:white;border-radius:10px;padding:1px 7px;font-size:.6rem;font-weight:700;margin-right:4px">{notif}</span>' if notif else '')
    g=ugrad(st.session_state.current_user or "")
    st.markdown(
        f'<div class="topnav-glass">'
        f'<div class="topnav-logo">Nebula</div>'
        f'<div class="topnav-pills">{pills}</div>'
        f'<div style="display:flex;align-items:center;gap:7px;flex-shrink:0">{nb}'
        f'<div style="width:34px;height:34px;border-radius:50%;background:{g};'
        f'display:flex;align-items:center;justify-content:center;'
        f'font-family:Geist,sans-serif;font-size:.72rem;font-weight:700;color:white;'
        f'border:1.5px solid rgba(255,255,255,.14);overflow:hidden;">{av_inner}</div></div></div>',
        unsafe_allow_html=True)
    # Invisible overlay
    st.markdown('<div class="tnav-overlay">',unsafe_allow_html=True)
    cols=st.columns([1.4]+[1]*len(NAV)+[.55])
    for i,(key,lbl,_) in enumerate(NAV):
        with cols[i+1]:
            if st.button(lbl,key=f"tnav_{key}",use_container_width=True):
                st.session_state.profile_view=None; st.session_state.page=key; st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)

# ─── PROFILE ───────────────────────────────────────
def page_profile(target_email):
    tu=st.session_state.users.get(target_email,{})
    if not tu:
        st.error("Perfil não encontrado.")
        if st.button("← Voltar",key="bk_err"): st.session_state.profile_view=None; st.rerun()
        return
    tname=tu.get("name","?"); tin=ini(tname); tphoto=tu.get("photo_b64")
    email=st.session_state.current_user; is_me=email==target_email
    is_fol=target_email in st.session_state.followed
    user_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==target_email]
    total_likes=sum(p["likes"] for p in user_posts)
    g=ugrad(target_email)
    if st.button("← Voltar ao Feed",key="back_prof"): st.session_state.profile_view=None; st.rerun()
    photo_html=f'<img src="{tphoto}"/>' if tphoto else f'<span style="font-size:2rem">{tin}</span>'
    v_badge=('<span style="font-size:.7rem;color:#22d3ee;margin-left:6px">✓ Verificado</span>' if tu.get("verified") else "")
    st.markdown(
        f'<div class="prof-hero"><div class="prof-photo" style="background:{g}">{photo_html}</div>'
        f'<div style="flex:1;z-index:1">'
        f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;margin-bottom:.3rem">'
        f'<h1 style="margin:0">{tname}</h1>{v_badge}</div>'
        f'<div style="color:#60a5fa;font-size:.84rem;font-weight:500;margin-bottom:.4rem">{tu.get("area","")}</div>'
        f'<div style="color:#94a3b8;font-size:.82rem;line-height:1.68;margin-bottom:.9rem;max-width:560px">{tu.get("bio","Sem biografia.")}</div>'
        f'<div style="display:flex;gap:2rem;flex-wrap:wrap">'
        f'<div><span style="font-family:Geist,sans-serif;font-weight:800;font-size:1.1rem">{tu.get("followers",0)}</span><span style="color:#475569;font-size:.73rem"> seguidores</span></div>'
        f'<div><span style="font-family:Geist,sans-serif;font-weight:800;font-size:1.1rem">{tu.get("following",0)}</span><span style="color:#475569;font-size:.73rem"> seguindo</span></div>'
        f'<div><span style="font-family:Geist,sans-serif;font-weight:800;font-size:1.1rem">{len(user_posts)}</span><span style="color:#475569;font-size:.73rem"> pesquisas</span></div>'
        f'<div><span style="font-family:Geist,sans-serif;font-weight:800;font-size:1.1rem">{fmt_num(total_likes)}</span><span style="color:#475569;font-size:.73rem"> curtidas</span></div>'
        f'</div></div></div>',unsafe_allow_html=True)
    if not is_me:
        c1,c2,_=st.columns([1,1,3])
        with c1:
            lbl_f="✓ Seguindo" if is_fol else "+ Seguir"
            if st.button(lbl_f,key="pf_fol",use_container_width=True):
                if is_fol: st.session_state.followed.remove(target_email); tu["followers"]=max(0,tu.get("followers",0)-1)
                else: st.session_state.followed.append(target_email); tu["followers"]=tu.get("followers",0)+1
                save_db(); st.rerun()
        with c2:
            if st.button("◻ Mensagem",key="pf_chat",use_container_width=True):
                if target_email not in st.session_state.chat_messages: st.session_state.chat_messages[target_email]=[]
                st.session_state.active_chat=target_email; st.session_state.page="chat"; st.rerun()
    st.markdown('<div class="dtxt">Pesquisas Publicadas</div>',unsafe_allow_html=True)
    if user_posts:
        for p in sorted(user_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="profile",show_author=False)
    else:
        st.markdown('<div class="card" style="padding:2.5rem;text-align:center;color:#64748b">Nenhuma pesquisa publicada ainda.</div>',unsafe_allow_html=True)

# ─── POST CARD ─────────────────────────────────────
def render_post(post,ctx="feed",show_author=True,compact=False):
    email=st.session_state.current_user; pid=post["id"]
    liked=email in post.get("liked_by",[]); saved=email in post.get("saved_by",[])
    aemail=post.get("author_email",""); aphoto=get_photo(aemail); ain=post.get("avatar","??")
    aname=post.get("author","?"); aarea=post.get("area",""); dt=time_ago(post.get("date",""))
    views=post.get("views",random.randint(80,500)); abstract=post.get("abstract","")
    if compact and len(abstract)>200: abstract=abstract[:200]+"…"
    g=ugrad(aemail)
    if show_author:
        av_html=(f'<div class="av" style="width:42px;height:42px;background:{g}"><img src="{aphoto}"/></div>'
                 if aphoto else f'<div class="av" style="width:42px;height:42px;background:{g};font-size:13px">{ain}</div>')
        v_mark=(' <span style="font-size:.62rem;color:#22d3ee">✓</span>' if st.session_state.users.get(aemail,{}).get("verified") else "")
        header=(f'<div style="padding:.95rem 1.2rem .7rem;display:flex;align-items:center;gap:10px;border-bottom:1px solid rgba(255,255,255,.05)">'
                f'{av_html}<div style="flex:1;min-width:0"><div style="font-family:Geist,sans-serif;font-weight:700;font-size:.88rem">{aname}{v_mark}</div>'
                f'<div style="color:#64748b;font-size:.67rem;margin-top:1px">{aarea} · {dt}</div></div>{badge(post["status"])}</div>')
    else:
        header=(f'<div style="padding:.4rem 1.2rem .25rem;display:flex;justify-content:space-between;align-items:center">'
                f'<span style="color:#64748b;font-size:.67rem">{dt}</span>{badge(post["status"])}</div>')
    st.markdown(f'<div class="post">{header}<div style="padding:.8rem 1.2rem">'
                f'<div style="font-family:Geist,sans-serif;font-size:1rem;font-weight:700;margin-bottom:.42rem;line-height:1.42">{post["title"]}</div>'
                f'<div style="color:#94a3b8;font-size:.82rem;line-height:1.68;margin-bottom:.65rem">{abstract}</div>'
                f'<div>{tags_html(post.get("tags",[]))}</div></div></div>',unsafe_allow_html=True)
    heart="♥" if liked else "♡"; book="◆" if saved else "◇"; nc=len(post.get("comments",[]))
    ca,cb,cc,cd,ce,cf=st.columns([1.1,1,.75,.65,1,1.1])
    with ca:
        if st.button(f"{heart} {fmt_num(post['likes'])}",key=f"lk_{ctx}_{pid}",use_container_width=True):
            if liked: post["liked_by"].remove(email); post["likes"]=max(0,post["likes"]-1)
            else: post["liked_by"].append(email); post["likes"]+=1; record(post.get("tags",[]),1.5)
            save_db(); st.rerun()
    with cb:
        if st.button(f"◻ {nc}" if nc else "◻ Comentar",key=f"cm_{ctx}_{pid}",use_container_width=True):
            k=f"cmt_{ctx}_{pid}"; st.session_state[k]=not st.session_state.get(k,False); st.rerun()
    with cc:
        if st.button(book,key=f"sv_{ctx}_{pid}",use_container_width=True):
            if saved: post["saved_by"].remove(email)
            else: post["saved_by"].append(email)
            save_db(); st.rerun()
    with cd:
        if st.button("↗",key=f"sh_{ctx}_{pid}",use_container_width=True):
            k=f"shr_{ctx}_{pid}"; st.session_state[k]=not st.session_state.get(k,False); st.rerun()
    with ce:
        st.markdown(f'<div style="text-align:center;color:#64748b;font-size:.70rem;padding:.5rem 0">{fmt_num(views)} views</div>',unsafe_allow_html=True)
    with cf:
        if show_author and aemail:
            first=aname.split()[0] if aname else "?"
            if st.button(f"⊛ {first}",key=f"vp_{ctx}_{pid}",use_container_width=True):
                st.session_state.profile_view=aemail; st.rerun()
    if st.session_state.get(f"shr_{ctx}_{pid}",False):
        url=f"https://nebula.ai/post/{pid}"; te=post['title'][:50].replace(" ","%20")
        st.markdown(f'<div class="card" style="padding:.9rem 1.2rem;margin-bottom:.5rem">'
                    f'<div style="font-family:Geist,sans-serif;font-weight:600;font-size:.82rem;margin-bottom:.7rem;color:#94a3b8">↗ Compartilhar pesquisa</div>'
                    f'<div style="display:flex;gap:.5rem;flex-wrap:wrap">'
                    f'<a href="https://twitter.com/intent/tweet?text={te}" target="_blank" style="text-decoration:none"><div style="background:rgba(29,161,242,.08);border:1px solid rgba(29,161,242,.18);border-radius:9px;padding:.35rem .7rem;font-size:.72rem;color:#1da1f2">✕ Twitter</div></a>'
                    f'<a href="https://linkedin.com/sharing/share-offsite/?url={url}" target="_blank" style="text-decoration:none"><div style="background:rgba(10,102,194,.08);border:1px solid rgba(10,102,194,.18);border-radius:9px;padding:.35rem .7rem;font-size:.72rem;color:#0a66c2">in LinkedIn</div></a>'
                    f'<a href="https://wa.me/?text={te}%20{url}" target="_blank" style="text-decoration:none"><div style="background:rgba(37,211,102,.07);border:1px solid rgba(37,211,102,.15);border-radius:9px;padding:.35rem .7rem;font-size:.72rem;color:#25d366">◎ WhatsApp</div></a>'
                    f'</div></div>',unsafe_allow_html=True)
    if st.session_state.get(f"cmt_{ctx}_{pid}",False):
        for c in post.get("comments",[]):
            c_in=ini(c["user"]); c_email=next((e for e,u in st.session_state.users.items() if u.get("name")==c["user"]),"")
            c_photo=get_photo(c_email); c_g=ugrad(c_email)
            st.markdown(f'<div class="cmt"><div style="display:flex;align-items:center;gap:8px;margin-bottom:.25rem">{avh(c_in,28,c_photo,c_g)}<span style="font-size:.76rem;font-weight:600;color:#60a5fa">{c["user"]}</span></div><div style="font-size:.79rem;color:#94a3b8;line-height:1.55;padding-left:36px">{c["text"]}</div></div>',unsafe_allow_html=True)
        nc_txt=st.text_input("",placeholder="💬 Escreva um comentário…",key=f"ci_{ctx}_{pid}",label_visibility="collapsed")
        st.markdown('<div class="btn-primary" style="display:inline-block">',unsafe_allow_html=True)
        if st.button("→ Enviar",key=f"cs_{ctx}_{pid}"):
            if nc_txt:
                uu=guser(); post["comments"].append({"user":uu.get("name","Você"),"text":nc_txt})
                record(post.get("tags",[]),.8); save_db(); st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)

# ─── FEED ──────────────────────────────────────────
def page_feed():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    email=st.session_state.current_user; u=guser()
    uname=u.get("name","?"); uphoto=u.get("photo_b64"); uin=ini(uname)
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    compose_open=st.session_state.get("compose_open",False)
    col_main,col_side=st.columns([2,.9],gap="medium")

    with col_main:
        # ════ STORY ROW ════
        story_list=[(ue,ud) for ue,ud in users.items() if ue!=email][:7]
        n_cols=1+len(story_list)
        scols=st.columns(n_cols)

        # Publish circle — single button
        with scols[0]:
            cls="story-pub-open" if compose_open else "story-pub"
            st.markdown(f'<div class="{cls}" style="display:flex;justify-content:center">',unsafe_allow_html=True)
            if st.button("+" if not compose_open else "×",key="btn_pub_circle"):
                st.session_state.compose_open=not compose_open; st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)
            st.markdown(f'<div class="slabel" style="color:{"#22d3ee" if compose_open else "#60a5fa"}">{"Fechar" if compose_open else "Publicar"}</div>',unsafe_allow_html=True)

        # Researcher circles — each IS a single button
        for ci,(ue,ud) in enumerate(story_list):
            sname=ud.get("name","?"); sin=ini(sname); sphoto=ud.get("photo_b64")
            is_fol=ue in st.session_state.followed; online=random.Random(ue).random()>0.45
            first=sname.split()[0]; short_a=ud.get("area","")[:11]
            fol_cls=" story-fol" if is_fol else ""
            with scols[ci+1]:
                if sphoto:
                    # photo user: HTML circle + overlapping button (same height)
                    g=ugrad(ue)
                    st.markdown(
                        f'<div style="position:relative;width:62px;height:62px;margin:0 auto 0;border-radius:50%;'
                        f'background:{g};border:2px solid {"rgba(34,197,94,.5)" if is_fol else "rgba(255,255,255,.14)"};'
                        f'overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,.4);cursor:pointer">'
                        f'<img src="{sphoto}" style="width:100%;height:100%;object-fit:cover"/></div>',
                        unsafe_allow_html=True)
                    # invisible button overlay ON TOP of photo
                    st.markdown(f'<div style="margin-top:-62px;opacity:0;height:62px">',unsafe_allow_html=True)
                    if st.button(first,key=f"sc_{ue}",use_container_width=True,help=f"Ver perfil de {sname}"):
                        st.session_state.profile_view=ue; st.rerun()
                    st.markdown('</div>',unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="story-circ{fol_cls}" style="display:flex;justify-content:center">',unsafe_allow_html=True)
                    if st.button(sin,key=f"sc_{ue}",help=f"Ver perfil de {sname}"):
                        st.session_state.profile_view=ue; st.rerun()
                    st.markdown('</div>',unsafe_allow_html=True)
                if online and is_fol:
                    st.markdown('<div style="width:7px;height:7px;border-radius:50%;background:#22c55e;margin:3px auto 2px;box-shadow:0 0 5px #22c55e;animation:pulse 2s infinite"></div>',unsafe_allow_html=True)
                else:
                    st.markdown('<div style="height:12px"></div>',unsafe_allow_html=True)
                st.markdown(f'<div class="slabel">{first}</div>',unsafe_allow_html=True)
                st.markdown(f'<div class="ssubl">{short_a}</div>',unsafe_allow_html=True)

        st.markdown("<div style='height:8px'></div>",unsafe_allow_html=True)

        # ════ COMPOSE ════
        if compose_open:
            st.markdown('<div class="compose-area">',unsafe_allow_html=True)
            g=ugrad(email)
            av_c=(f'<div class="av" style="width:44px;height:44px;background:{g}"><img src="{uphoto}"/></div>'
                  if uphoto else f'<div class="av" style="width:44px;height:44px;font-size:14px;background:{g}">{uin}</div>')
            st.markdown(f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:1rem">'
                        f'{av_c}<div><div style="font-family:Geist,sans-serif;font-weight:700;font-size:.92rem">{uname}</div>'
                        f'<div style="font-size:.68rem;color:#64748b">{u.get("area","Pesquisador")}</div></div></div>',unsafe_allow_html=True)
            np_t=st.text_input("✦ Título *",key="np_t",placeholder="Ex: Efeitos da meditação na neuroplasticidade…")
            np_ab=st.text_area("◎ Resumo / Abstract *",key="np_ab",height=110,placeholder="Descreva sua pesquisa…")
            c1c,c2c=st.columns(2)
            with c1c: np_tg=st.text_input("⊗ Tags (vírgula)",key="np_tg",placeholder="neurociência, fMRI")
            with c2c: np_st=st.selectbox("Status",["Em andamento","Publicado","Concluído"],key="np_st")
            cpub,ccan=st.columns([2,1])
            with cpub:
                st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
                if st.button("→ Publicar Pesquisa",key="btn_pub",use_container_width=True):
                    if not np_t or not np_ab: st.warning("Título e resumo são obrigatórios.")
                    else:
                        tags=[t.strip() for t in np_tg.split(",") if t.strip()] if np_tg else []
                        new_p={"id":len(st.session_state.feed_posts)+200+random.randint(0,99),
                               "author":uname,"author_email":email,"avatar":uin,"area":u.get("area",""),
                               "title":np_t,"abstract":np_ab,"tags":tags,"likes":0,"comments":[],
                               "status":np_st,"date":datetime.now().strftime("%Y-%m-%d"),
                               "liked_by":[],"saved_by":[],"connections":tags[:3],"views":1}
                        st.session_state.feed_posts.insert(0,new_p)
                        record(tags,2.0); save_db(); st.session_state.compose_open=False; st.success("✓ Publicado!"); st.rerun()
                st.markdown('</div>',unsafe_allow_html=True)
            with ccan:
                if st.button("✕ Cancelar",key="btn_cancel",use_container_width=True):
                    st.session_state.compose_open=False; st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)
        else:
            # COMPOSE PROMPT — single-click bar
            g=ugrad(email)
            av_c2=(f'<div class="av" style="width:40px;height:40px;flex-shrink:0;background:{g}"><img src="{uphoto}"/></div>'
                   if uphoto else f'<div class="av" style="width:40px;height:40px;font-size:13px;flex-shrink:0;background:{g}">{uin}</div>')
            ac,bc=st.columns([.06,1],gap="small")
            with ac:
                st.markdown(f'<div style="padding-top:6px">{av_c2}</div>',unsafe_allow_html=True)
            with bc:
                st.markdown('<div class="compose-prompt">',unsafe_allow_html=True)
                if st.button(f"✦ No que você está pesquisando, {uname.split()[0]}?",
                             key="open_compose",use_container_width=True):
                    st.session_state.compose_open=True; st.rerun()
                st.markdown('</div>',unsafe_allow_html=True)

        # FILTER
        ff=st.radio("",["◈ Todos","⊙ Seguidos","◆ Salvos","⊗ Populares"],
                    horizontal=True,key="ff",label_visibility="collapsed")

        # RECS
        recs=get_recs(email,2)
        if recs and "Seguidos" not in ff and "Salvos" not in ff:
            st.markdown('<div class="dtxt"><span class="badge-rec">⊙ Recomendado para você</span></div>',unsafe_allow_html=True)
            for p in recs: render_post(p,ctx="rec",compact=True)
            st.markdown('<div class="dtxt">Mais pesquisas</div>',unsafe_allow_html=True)

        # POSTS
        posts=list(st.session_state.feed_posts)
        if "Seguidos" in ff: posts=[p for p in posts if p.get("author_email") in st.session_state.followed]
        elif "Salvos" in ff: posts=[p for p in posts if email in p.get("saved_by",[])]
        elif "Populares" in ff: posts=sorted(posts,key=lambda p:p["likes"],reverse=True)
        else: posts=sorted(posts,key=lambda p:p.get("date",""),reverse=True)
        if not posts:
            st.markdown('<div class="card" style="padding:3.5rem;text-align:center"><div style="font-size:2.5rem;margin-bottom:1rem;opacity:.3">◎</div><div style="color:#64748b;font-family:Geist,sans-serif">Nenhuma pesquisa aqui ainda.</div></div>',unsafe_allow_html=True)
        else:
            for p in posts: render_post(p,ctx="feed")

    with col_side:
        sq=st.text_input("",placeholder="⊙ Buscar pesquisadores…",key="ppl_s",label_visibility="collapsed")
        st.markdown('<div class="sc">',unsafe_allow_html=True)
        st.markdown('<div style="font-family:Geist,sans-serif;font-weight:700;font-size:.83rem;margin-bottom:.9rem;display:flex;justify-content:space-between"><span>Quem seguir</span><span style="font-size:.65rem;color:#64748b;font-weight:400">Sugestões</span></div>',unsafe_allow_html=True)
        shown_n=0
        for ue,ud in list(users.items()):
            if ue==email or shown_n>=5: continue
            rname=ud.get("name","?")
            if sq and sq.lower() not in rname.lower() and sq.lower() not in ud.get("area","").lower(): continue
            shown_n+=1; is_fol=ue in st.session_state.followed
            uphoto_r=ud.get("photo_b64"); uin_r=ini(rname); rg=ugrad(ue)
            online=random.Random(ue+"x").random()>0.45; dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            st.markdown(f'<div class="person-row">{avh(uin_r,34,uphoto_r,rg)}<div style="flex:1;min-width:0"><div style="font-size:.80rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{dot}{rname}</div><div style="font-size:.64rem;color:#64748b">{ud.get("area","")[:22]}</div></div></div>',unsafe_allow_html=True)
            cb_f,cb_v=st.columns(2)
            with cb_f:
                if st.button("✓ Seguindo" if is_fol else "+ Seguir",key=f"sf_{ue}",use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"]=max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                    save_db(); st.rerun()
            with cb_v:
                if st.button("⊛ Perfil",key=f"svr_{ue}",use_container_width=True):
                    st.session_state.profile_view=ue; st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)
        st.markdown('<div class="sc">',unsafe_allow_html=True)
        st.markdown('<div style="font-family:Geist,sans-serif;font-weight:700;font-size:.83rem;margin-bottom:.85rem">⊗ Em Alta</div>',unsafe_allow_html=True)
        for i,(topic,cnt) in enumerate([("Quantum ML","34 pesquisas"),("CRISPR 2026","28 pesquisas"),("Neuroplasticidade","22 pesquisas"),("LLMs Científicos","19 pesquisas"),("Matéria Escura","15 pesquisas")]):
            st.markdown(f'<div style="padding:.42rem .4rem;border-radius:10px;margin-bottom:2px"><div style="font-size:.62rem;color:#64748b">#{i+1}</div><div style="font-size:.80rem;font-weight:600">{topic}</div><div style="font-size:.62rem;color:#64748b">{cnt}</div></div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)
        if st.session_state.notifications:
            st.markdown('<div class="sc">',unsafe_allow_html=True)
            st.markdown('<div style="font-family:Geist,sans-serif;font-weight:700;font-size:.83rem;margin-bottom:.75rem">◻ Atividade</div>',unsafe_allow_html=True)
            for notif in st.session_state.notifications[:3]:
                st.markdown(f'<div style="font-size:.72rem;color:#94a3b8;padding:.35rem 0;border-bottom:1px solid var(--glass-border)">· {notif}</div>',unsafe_allow_html=True)
            st.markdown('</div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ─── SEARCH ────────────────────────────────────────
def render_web_article(a,idx=0,ctx="web"):
    src_c="#22d3ee" if a.get("origin")=="semantic" else "#a78bfa"
    src_n="Semantic Scholar" if a.get("origin")=="semantic" else "CrossRef"
    cite=f" · {a['citations']} cit." if a.get("citations") else ""
    uid=re.sub(r'[^a-zA-Z0-9]','',f"{ctx}_{idx}_{str(a.get('doi',''))[:10]}")[:32]
    is_saved=any(s.get('doi')==a.get('doi') for s in st.session_state.saved_articles)
    abstract=(a.get("abstract","") or "")[:260]+("…" if len(a.get("abstract",""))>260 else "")
    st.markdown(f'<div class="scard"><div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:.35rem">'
                f'<div style="flex:1;font-family:Geist,sans-serif;font-size:.9rem;font-weight:700">{a["title"]}</div>'
                f'<span style="font-size:.62rem;color:{src_c};background:rgba(6,182,212,.06);border-radius:8px;padding:2px 8px;white-space:nowrap;flex-shrink:0">{src_n}</span>'
                f'</div><div style="color:#64748b;font-size:.68rem;margin-bottom:.38rem">{a["authors"]} · <em>{a["source"]}</em> · {a["year"]}{cite}</div>'
                f'<div style="color:#94a3b8;font-size:.79rem;line-height:1.65">{abstract}</div></div>',unsafe_allow_html=True)
    ca,cb,cc=st.columns(3)
    with ca:
        lbl_sv="◆ Salvo" if is_saved else "◇ Salvar"
        if st.button(lbl_sv,key=f"svw_{uid}"):
            if is_saved: st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]; st.toast("Removido")
            else: st.session_state.saved_articles.append(a); st.toast("Salvo!")
            save_db(); st.rerun()
    with cb:
        if st.button("⊗ Citar",key=f"ctw_{uid}"): st.toast(f'{a["authors"]} ({a["year"]}). {a["title"]}.')
    with cc:
        if a.get("url"): st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:#60a5fa;font-size:.79rem;text-decoration:none;line-height:2.5;display:block">↗ Abrir artigo</a>',unsafe_allow_html=True)

def page_search():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1rem;margin-bottom:.4rem">⊗ Busca Acadêmica</h1>',unsafe_allow_html=True)
    st.markdown('<p style="color:#64748b;font-size:.80rem;margin-bottom:1rem">Semantic Scholar · CrossRef · Nebula</p>',unsafe_allow_html=True)
    c1,c2=st.columns([4,1])
    with c1: q=st.text_input("",placeholder="CRISPR · quantum ML · dark matter…",key="sq",label_visibility="collapsed")
    with c2:
        st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
        if st.button("⊗ Buscar",use_container_width=True,key="btn_s"):
            if q:
                with st.spinner("Buscando…"):
                    nb=[p for p in st.session_state.feed_posts if q.lower() in p["title"].lower() or q.lower() in p["abstract"].lower() or any(q.lower() in t.lower() for t in p.get("tags",[]))]
                    ss_r=search_ss(q,6); cr_r=search_cr(q,4)
                    st.session_state.search_results={"nebula":nb,"ss":ss_r,"cr":cr_r}; st.session_state.last_sq=q; record([q.lower()],.3)
        st.markdown('</div>',unsafe_allow_html=True)
    if st.session_state.get("search_results") and st.session_state.get("last_sq"):
        res=st.session_state.search_results; neb=res.get("nebula",[]); ss=res.get("ss",[]); cr=res.get("cr",[])
        web=ss+[x for x in cr if not any(x["title"].lower()==s["title"].lower() for s in ss)]
        t1,t2,t3=st.tabs([f"  ◈ Todos ({len(neb)+len(web)})  ",f"  ◎ Nebula ({len(neb)})  ",f"  ⊗ Internet ({len(web)})  "])
        with t1:
            if neb:
                st.markdown('<div style="font-size:.64rem;color:#60a5fa;font-weight:700;margin-bottom:.5rem;letter-spacing:.09em;text-transform:uppercase">Na Nebula</div>',unsafe_allow_html=True)
                for p in neb: render_post(p,ctx="srch_all",compact=True)
            if web:
                if neb: st.markdown('<hr>',unsafe_allow_html=True)
                st.markdown('<div style="font-size:.64rem;color:#22d3ee;font-weight:700;margin-bottom:.5rem;letter-spacing:.09em;text-transform:uppercase">Bases Acadêmicas</div>',unsafe_allow_html=True)
                for idx,a in enumerate(web): render_web_article(a,idx=idx,ctx="all_w")
            if not neb and not web: st.info("Nenhum resultado.")
        with t2:
            if neb: [render_post(p,ctx="srch_neb",compact=True) for p in neb]
            else: st.info("Nenhuma pesquisa na Nebula.")
        with t3:
            if web: [render_web_article(a,idx=idx,ctx="web_t") for idx,a in enumerate(web)]
            else: st.info("Nenhum artigo online.")
    st.markdown('</div>',unsafe_allow_html=True)

# ─── KNOWLEDGE ─────────────────────────────────────
def page_knowledge():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1rem;margin-bottom:1rem">⊙ Rede de Conexões</h1>',unsafe_allow_html=True)
    email=st.session_state.current_user; users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    def get_tags(ue):
        ud=users.get(ue,{}); tags=set(area_to_tags(ud.get("area","")))
        for p in st.session_state.feed_posts:
            if p.get("author_email")==ue: tags.update(t.lower() for t in p.get("tags",[]))
        return tags
    rlist=list(users.keys()); rtags={ue:get_tags(ue) for ue in rlist}
    edges=[]
    for i in range(len(rlist)):
        for j in range(i+1,len(rlist)):
            e1,e2=rlist[i],rlist[j]; common=list(rtags[e1]&rtags[e2]); is_fol=e2 in st.session_state.followed or e1 in st.session_state.followed
            if common or is_fol: edges.append((e1,e2,common[:5],len(common)+(2 if is_fol else 0)))
    n=len(rlist); pos={}
    for idx,ue in enumerate(rlist):
        angle=2*3.14159*idx/max(n,1); r_d=0.36+0.05*((hash(ue)%5)/4)
        pos[ue]={"x":0.5+r_d*np.cos(angle),"y":0.5+r_d*np.sin(angle),"z":0.5+0.12*((idx%4)/3-.35)}
    fig=go.Figure()
    for e1,e2,common,strength in edges:
        p1=pos[e1]; p2=pos[e2]; alpha=min(0.55,0.10+strength*0.06)
        fig.add_trace(go.Scatter3d(x=[p1["x"],p2["x"],None],y=[p1["y"],p2["y"],None],z=[p1["z"],p2["z"],None],
            mode="lines",line=dict(color=f"rgba(59,130,246,{alpha:.2f})",width=min(4,1+strength)),hoverinfo="none",showlegend=False))
    ncolors=["#22d3ee" if ue==email else ("#60a5fa" if ue in st.session_state.followed else "#2563eb") for ue in rlist]
    nsizes=[24 if ue==email else (18 if ue in st.session_state.followed else max(12,10+sum(1 for e1,e2,_,__ in edges if e1==ue or e2==ue))) for ue in rlist]
    ntext=[users.get(ue,{}).get("name","?").split()[0] for ue in rlist]
    nhover=[f"<b>{users.get(ue,{}).get('name','?')}</b><br>{users.get(ue,{}).get('area','')}<extra></extra>" for ue in rlist]
    fig.add_trace(go.Scatter3d(x=[pos[ue]["x"] for ue in rlist],y=[pos[ue]["y"] for ue in rlist],z=[pos[ue]["z"] for ue in rlist],
        mode="markers+text",marker=dict(size=nsizes,color=ncolors,opacity=.9,line=dict(color="rgba(147,197,253,.22)",width=1.5)),
        text=ntext,textposition="top center",textfont=dict(color="#64748b",size=9,family="Inter"),
        hovertemplate=nhover,showlegend=False))
    fig.update_layout(height=440,scene=dict(xaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),yaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),zaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),bgcolor="rgba(0,0,0,0)"),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig,use_container_width=True)
    c1,c2,c3,c4=st.columns(4)
    for col,(v,l) in zip([c1,c2,c3,c4],[(len(rlist),"Pesquisadores"),(len(edges),"Conexões"),(len(st.session_state.followed),"Seguindo"),(len(st.session_state.feed_posts),"Pesquisas")]):
        with col: st.markdown(f'<div class="mbox"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>',unsafe_allow_html=True)
    st.markdown("<hr>",unsafe_allow_html=True)
    t1,t2,t3=st.tabs(["  ◈ Mapa  ","  ⊙ Minhas Conexões  ","  ◎ Todos  "])
    with t1:
        for e1,e2,common,strength in sorted(edges,key=lambda x:-x[3])[:20]:
            n1=users.get(e1,{}); n2=users.get(e2,{})
            ts=tags_html(common[:4]) if common else '<span style="color:#64748b;font-size:.70rem">seguimento</span>'
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><span style="font-size:.82rem;font-weight:700;font-family:Geist,sans-serif;color:#60a5fa">{n1.get("name","?")}</span><span style="color:#64748b">↔</span><span style="font-size:.82rem;font-weight:700;font-family:Geist,sans-serif;color:#60a5fa">{n2.get("name","?")}</span><div style="flex:1">{ts}</div><span style="font-size:.67rem;color:#22d3ee;font-weight:700">{strength}pt</span></div></div>',unsafe_allow_html=True)
    with t2:
        my_conn=[(e1,e2,c,s) for e1,e2,c,s in edges if e1==email or e2==email]
        if not my_conn: st.info("Siga pesquisadores e publique pesquisas para ver conexões.")
        for e1,e2,common,strength in sorted(my_conn,key=lambda x:-x[3]):
            other=e2 if e1==email else e1; od=users.get(other,{}); og=ugrad(other)
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">{avh(ini(od.get("name","?")),38,get_photo(other),og)}<div style="flex:1"><div style="font-weight:700;font-size:.86rem;font-family:Geist,sans-serif">{od.get("name","?")}</div><div style="font-size:.69rem;color:#64748b">{od.get("area","")}</div></div>{tags_html(common[:3])}</div></div>',unsafe_allow_html=True)
            cv,cm_b,_=st.columns([1,1,4])
            with cv:
                if st.button("⊛ Perfil",key=f"kv_{other}",use_container_width=True): st.session_state.profile_view=other; st.rerun()
            with cm_b:
                if st.button("◻ Chat",key=f"kc_{other}",use_container_width=True):
                    if other not in st.session_state.chat_messages: st.session_state.chat_messages[other]=[]
                    st.session_state.active_chat=other; st.session_state.page="chat"; st.rerun()
    with t3:
        sq2=st.text_input("",placeholder="⊙ Buscar…",key="all_s",label_visibility="collapsed")
        for ue,ud in users.items():
            if ue==email: continue
            rn=ud.get("name","?"); uarea=ud.get("area","")
            if sq2 and sq2.lower() not in rn.lower() and sq2.lower() not in uarea.lower(): continue
            is_fol=ue in st.session_state.followed; og=ugrad(ue)
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:10px">{avh(ini(rn),38,get_photo(ue),og)}<div style="flex:1"><div style="font-size:.86rem;font-weight:700;font-family:Geist,sans-serif">{rn}</div><div style="font-size:.69rem;color:#64748b">{uarea}</div></div></div></div>',unsafe_allow_html=True)
            ca2,cb2,cc2=st.columns(3)
            with ca2:
                if st.button("⊛ Perfil",key=f"av_{ue}",use_container_width=True): st.session_state.profile_view=ue; st.rerun()
            with cb2:
                if st.button("✓ Seguindo" if is_fol else "+ Seguir",key=f"af_{ue}",use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"]=max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                    save_db(); st.rerun()
            with cc2:
                if st.button("◻ Chat",key=f"ac_{ue}",use_container_width=True):
                    if ue not in st.session_state.chat_messages: st.session_state.chat_messages[ue]=[]
                    st.session_state.active_chat=ue; st.session_state.page="chat"; st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)

# ─── FOLDERS — Intelligent Analysis ───────────────
def render_doc_analysis(fname,an,area=""):
    rel=an.get("relevance_score",0); kws=an.get("keywords",[]); topics=an.get("topics",{})
    authors=an.get("authors",[]); years=an.get("years",[]); refs=an.get("references",[])
    refs_online=an.get("references_online",[]); strengths=an.get("strengths",[]); improvements=an.get("improvements",[])
    col_c="#22c55e" if rel>=70 else ("#f59e0b" if rel>=45 else "#ef4444")
    st.markdown(f'<div class="abox"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.6rem">'
                f'<div style="font-family:Geist,sans-serif;font-weight:700;font-size:.9rem">{fname}</div>'
                f'<div style="text-align:right"><div style="font-family:Geist,sans-serif;font-size:1.3rem;font-weight:800;color:{col_c}">{rel}%</div>'
                f'<div style="font-size:.6rem;color:#64748b;text-transform:uppercase;letter-spacing:.07em">Relevância</div></div></div>'
                f'{prog_bar(rel,col_c)}'
                f'<div style="font-size:.79rem;color:#94a3b8;line-height:1.65;margin-top:.4rem">{an.get("summary","")}</div></div>',unsafe_allow_html=True)
    t1,t2,t3,t4,t5=st.tabs(["  ⊗ Palavras-chave  ","  ◎ Temas  ","  ⊛ Autores & Anos  ","  ▣ Referências  ","  ✦ Melhorias  "])
    with t1:
        if kws:
            weights=[max(1,12-i) for i in range(len(kws))]
            fig=go.Figure(go.Bar(x=weights[:20],y=kws[:20],orientation='h',
                marker=dict(color=weights[:20],colorscale=[[0,"#1e3a8a"],[.5,"#2563eb"],[1,"#22d3ee"]]),
                text=kws[:20],textposition='inside',textfont=dict(color='white',size=9)))
            fig.update_layout(height=380,title=dict(text="Palavras-chave",font=dict(color="#f1f5f9",family="Geist",size=12)),yaxis=dict(showticklabels=False),**pc())
            st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
            st.plotly_chart(fig,use_container_width=True)
            st.markdown('</div>',unsafe_allow_html=True)
            st.markdown(tags_html(kws[:20]),unsafe_allow_html=True)
        else: st.info("Análise de texto não disponível para este formato.")
    with t2:
        if topics:
            cols_palette=["#2563eb","#06b6d4","#7c3aed","#059669","#ea580c","#db2777","#0ea5e9","#65a30d","#f59e0b","#ef4444"]
            fig_pie=go.Figure(go.Pie(labels=list(topics.keys()),values=list(topics.values()),hole=0.52,
                marker=dict(colors=cols_palette[:len(topics)],line=dict(color=["#080c18"]*15,width=2)),
                textfont=dict(color="white",size=9)))
            fig_pie.update_layout(height=300,title=dict(text="Distribuição Temática",font=dict(color="#f1f5f9",family="Geist",size=12)),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(font=dict(color="#64748b",size=9)),margin=dict(l=0,r=0,t=40,b=0))
            st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
            st.plotly_chart(fig_pie,use_container_width=True)
            st.markdown('</div>',unsafe_allow_html=True)
            for i,(topic,score) in enumerate(list(topics.items())[:6]):
                color=cols_palette[i%len(cols_palette)]
                st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:.4rem"><span style="font-size:.78rem;color:#94a3b8;width:180px;flex-shrink:0">{topic}</span><div style="flex:1">{prog_bar(min(100,score*20),color)}</div><span style="font-size:.70rem;color:#64748b;width:25px;text-align:right">{score}</span></div>',unsafe_allow_html=True)
        else: st.info("Análise temática não disponível.")
    with t3:
        if authors:
            st.markdown('<div style="font-size:.64rem;color:#64748b;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.5rem;font-weight:600">Autores Identificados</div>',unsafe_allow_html=True)
            for author in authors:
                st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:.4rem 0;border-bottom:1px solid var(--glass-border)">{avh(ini(author),28,None,ugrad(author))}<span style="font-size:.82rem;color:#f1f5f9">{author}</span></div>',unsafe_allow_html=True)
        else: st.markdown('<div style="color:#64748b;font-size:.78rem;margin-bottom:.8rem">Nenhum autor identificado.</div>',unsafe_allow_html=True)
        if years:
            yl=[y for y,_ in years[:8]]; yv=[c for _,c in years[:8]]
            fig_y=go.Figure(go.Bar(x=yl,y=yv,marker=dict(color=yv,colorscale=[[0,"#1e3a8a"],[1,"#22d3ee"]]),
                text=yv,textposition="outside",textfont=dict(color="#94a3b8",size=9)))
            fig_y.update_layout(height=200,title=dict(text="Anos Mencionados",font=dict(color="#f1f5f9",family="Geist",size=11)),**pc())
            st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
            st.plotly_chart(fig_y,use_container_width=True)
            st.markdown('</div>',unsafe_allow_html=True)
    with t4:
        st.markdown('<div style="font-size:.64rem;color:#64748b;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.6rem;font-weight:600">Referências no Documento</div>',unsafe_allow_html=True)
        if refs:
            for r in refs[:10]: st.markdown(f'<div class="ref-item">· {r}</div>',unsafe_allow_html=True)
        else: st.markdown('<div style="color:#64748b;font-size:.78rem;margin-bottom:.7rem">Nenhuma referência estruturada encontrada.</div>',unsafe_allow_html=True)
        st.markdown('<div class="dtxt">⊗ Artigos Relacionados Online</div>',unsafe_allow_html=True)
        if refs_online:
            for ref in refs_online[:5]:
                url_html=f'<a href="{ref["url"]}" target="_blank" style="color:#60a5fa;text-decoration:none;font-size:.71rem">↗ Abrir</a>' if ref.get("url") else ""
                st.markdown(f'<div class="scard"><div style="font-family:Geist,sans-serif;font-size:.86rem;font-weight:700;margin-bottom:.3rem">{ref["title"]}</div>'
                            f'<div style="color:#64748b;font-size:.68rem;margin-bottom:.3rem">{ref["authors"]} · {ref["venue"]} · {ref["year"]}</div>'
                            f'<div style="color:#94a3b8;font-size:.77rem;line-height:1.6">{ref["abstract"][:180]}…</div>'
                            f'<div style="margin-top:.35rem">{url_html}</div></div>',unsafe_allow_html=True)
        else: st.markdown('<div style="color:#64748b;font-size:.78rem">Execute a análise para buscar referências online.</div>',unsafe_allow_html=True)
    with t5:
        if strengths:
            st.markdown('<div style="font-size:.64rem;color:#64748b;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.6rem;font-weight:600">✦ Pontos Fortes</div>',unsafe_allow_html=True)
            for s in strengths: st.markdown(f'<div class="str-ok">✓ {s}</div>',unsafe_allow_html=True)
        if improvements:
            st.markdown('<div style="font-size:.64rem;color:#64748b;text-transform:uppercase;letter-spacing:.08em;margin:.8rem 0 .6rem;font-weight:600">→ Pontos a Melhorar</div>',unsafe_allow_html=True)
            for imp in improvements: st.markdown(f'<div class="str-imp">→ {imp}</div>',unsafe_allow_html=True)
        if not strengths and not improvements: st.info("Execute a análise completa para ver recomendações.")

def page_folders():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1rem;margin-bottom:1rem">▣ Pastas de Pesquisa</h1>',unsafe_allow_html=True)
    u=guser(); area=u.get("area","")
    c1,c2,_=st.columns([2,1.2,1.5])
    with c1: nf_name=st.text_input("▣ Nome da pasta",placeholder="Ex: Genômica Comparativa",key="nf_n")
    with c2: nf_desc=st.text_input("Descrição",placeholder="Breve descrição",key="nf_d")
    st.markdown('<div class="btn-primary" style="display:inline-block">',unsafe_allow_html=True)
    if st.button("▣ Criar pasta",key="btn_nf"):
        if nf_name.strip():
            if nf_name not in st.session_state.folders:
                st.session_state.folders[nf_name]={"desc":nf_desc,"files":[],"notes":"","analyses":{}}; save_db(); st.success(f"✓ '{nf_name}' criada!"); st.rerun()
            else: st.warning("Pasta já existe.")
        else: st.warning("Digite um nome.")
    st.markdown('</div>',unsafe_allow_html=True)
    st.markdown("<hr>",unsafe_allow_html=True)
    if not st.session_state.folders:
        st.markdown('<div class="card" style="text-align:center;padding:4.5rem"><div style="font-size:2.5rem;opacity:.2;margin-bottom:1rem">▣</div><div style="color:#64748b;font-family:Geist,sans-serif">Nenhuma pasta criada ainda</div></div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True); return
    # Folder grid summary
    fcols=st.columns(3)
    for idx,(fname,fdata) in enumerate(list(st.session_state.folders.items())):
        if not isinstance(fdata,dict): fdata={"files":fdata,"desc":"","notes":"","analyses":{}}; st.session_state.folders[fname]=fdata
        files=fdata.get("files",[]); analyses=fdata.get("analyses",{})
        all_kws=list({kw for an in analyses.values() for kw in an.get("keywords",[])[:3]})
        with fcols[idx%3]:
            st.markdown(f'<div class="card" style="padding:1.2rem;text-align:center;margin-bottom:.6rem">'
                        f'<div style="font-size:2rem;opacity:.5;margin-bottom:7px">▣</div>'
                        f'<div style="font-family:Geist,sans-serif;font-weight:700;font-size:.95rem">{fname}</div>'
                        f'<div style="color:#64748b;font-size:.68rem;margin-top:2px">{fdata.get("desc","")}</div>'
                        f'<div style="font-size:.70rem;color:#60a5fa;margin-top:.4rem">{len(files)} arquivo(s) · {len(analyses)} analisado(s)</div>'
                        f'<div style="margin-top:.4rem">{tags_html(all_kws[:3])}</div></div>',unsafe_allow_html=True)
    # Expanders
    for fname,fdata in list(st.session_state.folders.items()):
        if not isinstance(fdata,dict): fdata={"files":fdata,"desc":"","notes":"","analyses":{}}; st.session_state.folders[fname]=fdata
        files=fdata.get("files",[]); analyses=fdata.get("analyses",{})
        with st.expander(f"▣ {fname}  —  {len(files)} arquivo(s)  ·  {len(analyses)} análise(s)"):
            up=st.file_uploader("",type=None,key=f"up_{fname}",label_visibility="collapsed",accept_multiple_files=True)
            if up:
                fb=st.session_state.folder_bytes.setdefault(fname,{})
                for uf in up:
                    if uf.name not in files: files.append(uf.name)
                    uf.seek(0); fb[uf.name]=uf.read()
                fdata["files"]=files; save_db(); st.success(f"✓ {len(up)} arquivo(s) adicionado(s)!")
            if files:
                st.markdown('<div style="margin:.7rem 0">',unsafe_allow_html=True)
                for f in files:
                    ft=get_ftype(f); ha=f in analyses
                    icon_map={"PDF":"PDF","Word":"DOC","Planilha":"XLS","Dados":"CSV","Código Python":"PY","Notebook":"NB","Apresentação":"PPT","Imagem":"IMG","Markdown":"MD"}
                    ic=icon_map.get(ft,ft[:3])
                    ab_badge=f'<span class="badge-pub" style="font-size:.6rem;margin-left:6px">✓ analisado</span>' if ha else ''
                    st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:.42rem 0;border-bottom:1px solid var(--glass-border)"><span style="background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.18);border-radius:6px;padding:2px 7px;font-size:.62rem;color:#93c5fd;font-weight:600;flex-shrink:0">{ic}</span><span style="font-size:.78rem;color:#94a3b8;flex:1">{f}</span>{ab_badge}</div>',unsafe_allow_html=True)
                st.markdown('</div>',unsafe_allow_html=True)
            else: st.markdown('<p style="color:#64748b;font-size:.74rem;text-align:center;padding:.5rem">Arraste arquivos — PDF, DOCX, XLSX, CSV…</p>',unsafe_allow_html=True)
            st.markdown('<hr>',unsafe_allow_html=True)
            ca_btn,cb_btn,_=st.columns([1.5,1.2,2])
            with ca_btn:
                st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
                if st.button("◎ Analisar documentos",key=f"analyze_{fname}",use_container_width=True):
                    if files:
                        pb=st.progress(0,"Iniciando…")
                        fb=st.session_state.folder_bytes.get(fname,{})
                        for fi,f in enumerate(files):
                            pb.progress((fi+1)/len(files),f"Analisando: {f[:30]}…")
                            an=analyze_document(f,fb.get(f,b""),get_ftype(f),area); analyses[f]=an
                        fdata["analyses"]=analyses
                        all_kws=list({kw for an in analyses.values() for kw in an.get("keywords",[])[:5]})
                        if all_kws:
                            with st.spinner("⊗ Buscando referências online…"):
                                refs_online=search_refs_online(all_kws[:6],n=5)
                                for an in analyses.values(): an["references_online"]=refs_online
                        save_db(); pb.empty(); st.success("✓ Análise completa!"); st.rerun()
                    else: st.warning("Adicione arquivos antes de analisar.")
                st.markdown('</div>',unsafe_allow_html=True)
            with cb_btn:
                st.markdown('<div class="btn-danger">',unsafe_allow_html=True)
                if st.button("✕ Excluir pasta",key=f"df_{fname}",use_container_width=True):
                    del st.session_state.folders[fname]
                    if fname in st.session_state.folder_bytes: del st.session_state.folder_bytes[fname]
                    save_db(); st.rerun()
                st.markdown('</div>',unsafe_allow_html=True)
            if analyses:
                st.markdown('<div class="dtxt">◎ Análises Inteligentes</div>',unsafe_allow_html=True)
                rel_scores={f:an.get("relevance_score",0) for f,an in analyses.items()}
                if len(rel_scores)>1:
                    fig_ov=go.Figure(go.Bar(x=list(rel_scores.values()),y=[f[:22] for f in rel_scores.keys()],orientation='h',
                        marker=dict(color=list(rel_scores.values()),colorscale=[[0,"#1e3a8a"],[.5,"#2563eb"],[1,"#22c55e"]],line=dict(color="#080c18",width=1)),
                        text=[f"{v}%" for v in rel_scores.values()],textposition="outside",textfont=dict(color="#94a3b8",size=9)))
                    fig_ov.update_layout(height=max(110,len(analyses)*38),title=dict(text="Relevância por Documento",font=dict(color="#f1f5f9",family="Geist",size=11)),**pc(),yaxis=dict(showgrid=False,color="#64748b",tickfont=dict(size=8)))
                    st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
                    st.plotly_chart(fig_ov,use_container_width=True)
                    st.markdown('</div>',unsafe_allow_html=True)
                all_topics=defaultdict(int)
                for an in analyses.values():
                    for t,s in an.get("topics",{}).items(): all_topics[t]+=s
                if all_topics:
                    cols_p=["#2563eb","#06b6d4","#7c3aed","#059669","#ea580c","#db2777","#0ea5e9","#65a30d","#f59e0b","#ef4444"]
                    fig_tp=go.Figure(go.Pie(labels=list(all_topics.keys()),values=list(all_topics.values()),hole=0.5,
                        marker=dict(colors=cols_p[:len(all_topics)],line=dict(color=["#080c18"]*15,width=2)),textfont=dict(color="white",size=9)))
                    fig_tp.update_layout(height=270,title=dict(text="Distribuição Temática da Pasta",font=dict(color="#f1f5f9",family="Geist",size=11)),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(font=dict(color="#64748b",size=8)),margin=dict(l=0,r=0,t=38,b=0))
                    st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
                    st.plotly_chart(fig_tp,use_container_width=True)
                    st.markdown('</div>',unsafe_allow_html=True)
                for f,an in analyses.items():
                    with st.expander(f"◎ Análise: {f}"):
                        render_doc_analysis(f,an,area)
            st.markdown('<hr>',unsafe_allow_html=True)
            note=st.text_area("◻ Notas",value=fdata.get("notes",""),key=f"note_{fname}",height=70,placeholder="Anotações…")
            if st.button("▣ Salvar nota",key=f"sn_{fname}",use_container_width=True): fdata["notes"]=note; save_db(); st.success("✓ Nota salva!")
    st.markdown('</div>',unsafe_allow_html=True)

# ─── ANALYTICS ─────────────────────────────────────
def page_analytics():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1rem;margin-bottom:1rem">◎ Painel de Pesquisa</h1>',unsafe_allow_html=True)
    email=st.session_state.current_user; d=st.session_state.stats_data; pcc=pc()
    t1,t2,t3,t4=st.tabs(["  ▣ Pastas  ","  ◈ Publicações  ","  ◎ Impacto  ","  ⊙ Interesses  "])
    with t1:
        folders=st.session_state.folders
        if not folders: st.markdown('<div class="card" style="text-align:center;padding:3.5rem;color:#64748b">Crie pastas e analise documentos.</div>',unsafe_allow_html=True)
        else:
            all_an={f:an for fd in folders.values() if isinstance(fd,dict) for f,an in fd.get("analyses",{}).items()}
            tf=sum(len(fd.get("files",[]) if isinstance(fd,dict) else fd) for fd in folders.values())
            all_kws=[kw for an in all_an.values() for kw in an.get("keywords",[])]
            all_topics=defaultdict(int)
            for an in all_an.values():
                for t,s in an.get("topics",{}).items(): all_topics[t]+=s
            c1,c2,c3,c4=st.columns(4)
            for col,(v,l) in zip([c1,c2,c3,c4],[(len(folders),"Pastas"),(tf,"Arquivos"),(len(all_an),"Analisados"),(len(set(all_kws[:100])),"Palavras-chave")]):
                with col: st.markdown(f'<div class="mbox"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>',unsafe_allow_html=True)
            if all_topics:
                fig_t=go.Figure(go.Bar(x=list(all_topics.values())[:8],y=list(all_topics.keys())[:8],orientation='h',
                    marker=dict(color=list(range(min(8,len(all_topics)))),colorscale=[[0,"#1e3a8a"],[.5,"#2563eb"],[1,"#22d3ee"]]),
                    text=[str(v) for v in list(all_topics.values())[:8]],textposition="outside",textfont=dict(color="#94a3b8",size=9)))
                fig_t.update_layout(height=280,title=dict(text="Temas por Frequência",font=dict(color="#f1f5f9",family="Geist",size=13)),**pcc,yaxis=dict(showgrid=False,color="#64748b",tickfont=dict(size=9)))
                st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
                st.plotly_chart(fig_t,use_container_width=True)
                st.markdown('</div>',unsafe_allow_html=True)
            if all_kws:
                kw_freq=Counter(all_kws).most_common(15)
                fig_kw=go.Figure(go.Bar(x=[c for _,c in kw_freq],y=[w for w,_ in kw_freq],orientation='h',
                    marker=dict(color=[c for _,c in kw_freq],colorscale=[[0,"#0c1424"],[.5,"#2563eb"],[1,"#22d3ee"]]),
                    text=[w for w,_ in kw_freq],textposition='inside',textfont=dict(color='white',size=8)))
                fig_kw.update_layout(height=320,title=dict(text="Top Palavras-chave",font=dict(color="#f1f5f9",family="Geist",size=12)),yaxis=dict(showticklabels=False),**pcc)
                st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
                st.plotly_chart(fig_kw,use_container_width=True)
                st.markdown('</div>',unsafe_allow_html=True)
            if all_an:
                rv=[an.get("relevance_score",0) for an in all_an.values()]
                fig_rel=go.Figure(go.Histogram(x=rv,nbinsx=10,marker=dict(color="#2563eb",line=dict(color="#080c18",width=1))))
                fig_rel.update_layout(height=190,title=dict(text="Distribuição de Relevância",font=dict(color="#f1f5f9",family="Geist",size=11)),**pcc)
                st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
                st.plotly_chart(fig_rel,use_container_width=True)
                st.markdown('</div>',unsafe_allow_html=True)
    with t2:
        my_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==email]
        if not my_posts: st.markdown('<div class="card" style="text-align:center;padding:2.5rem;color:#64748b">Publique pesquisas para ver métricas.</div>',unsafe_allow_html=True)
        else:
            c1,c2,c3=st.columns(3)
            with c1: st.markdown(f'<div class="mbox"><div class="mval">{len(my_posts)}</div><div class="mlbl">Pesquisas</div></div>',unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="mbox"><div class="mval">{sum(p["likes"] for p in my_posts)}</div><div class="mlbl">Curtidas</div></div>',unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="mbox"><div class="mval">{sum(len(p.get("comments",[])) for p in my_posts)}</div><div class="mlbl">Comentários</div></div>',unsafe_allow_html=True)
            titles_s=[p["title"][:18]+"…" for p in my_posts]
            fig_eng=go.Figure()
            fig_eng.add_trace(go.Bar(name="♥ Curtidas",x=titles_s,y=[p["likes"] for p in my_posts],marker_color="#2563eb",marker_line=dict(color="#080c18",width=1)))
            fig_eng.add_trace(go.Bar(name="◻ Comentários",x=titles_s,y=[len(p.get("comments",[])) for p in my_posts],marker_color="#06b6d4",marker_line=dict(color="#080c18",width=1)))
            fig_eng.update_layout(barmode="group",title=dict(text="Engajamento",font=dict(color="#f1f5f9",family="Geist",size=13)),height=250,**pcc,legend=dict(font=dict(color="#64748b")))
            st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
            st.plotly_chart(fig_eng,use_container_width=True)
            st.markdown('</div>',unsafe_allow_html=True)
            for p in sorted(my_posts,key=lambda x:x.get("date",""),reverse=True):
                st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;justify-content:space-between"><div style="font-family:Geist,sans-serif;font-size:.9rem;font-weight:700">{p["title"][:55]}{"…" if len(p["title"])>55 else ""}</div>{badge(p["status"])}</div><div style="font-size:.71rem;color:#64748b;margin-top:.4rem">{p.get("date","")} · ♥ {p["likes"]} · ◻ {len(p.get("comments",[]))} · ⊙ {p.get("views",0)}</div><div style="margin-top:.4rem">{tags_html(p.get("tags",[])[:4])}</div></div>',unsafe_allow_html=True)
    with t3:
        c1,c2,c3=st.columns(3)
        with c1: st.markdown(f'<div class="mbox"><div class="mval">{d.get("h_index",4)}</div><div class="mlbl">Índice H</div></div>',unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="mbox"><div class="mval">{d.get("fator_impacto",3.8):.1f}</div><div class="mlbl">Fator Impacto</div></div>',unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="mbox"><div class="mval">{len(st.session_state.saved_articles)}</div><div class="mlbl">Artigos Salvos</div></div>',unsafe_allow_html=True)
        st.markdown("<hr>",unsafe_allow_html=True)
        nh=st.number_input("Índice H",0,200,d.get("h_index",4),key="e_h")
        nfi=st.number_input("Fator de impacto",0.0,100.0,float(d.get("fator_impacto",3.8)),step=0.1,key="e_fi")
        nn=st.text_area("Notas",value=d.get("notes",""),key="e_notes",height=80)
        if st.button("▣ Salvar métricas",key="btn_save_m"): d.update({"h_index":nh,"fator_impacto":nfi,"notes":nn}); st.success("✓ Salvo!")
    with t4:
        prefs=st.session_state.user_prefs.get(email,{})
        if prefs:
            top=sorted(prefs.items(),key=lambda x:-x[1])[:12]; mx=max(s for _,s in top) if top else 1
            cats=[t for t,_ in top[:8]]; vals=[round(s/mx*100) for _,s in top[:8]]
            if len(cats)>=3:
                fig_r=go.Figure(go.Scatterpolar(r=vals+[vals[0]],theta=cats+[cats[0]],fill='toself',line=dict(color="#3b82f6"),fillcolor="rgba(59,130,246,.18)"))
                fig_r.update_layout(height=270,polar=dict(bgcolor="rgba(0,0,0,0)",radialaxis=dict(visible=True,gridcolor="rgba(255,255,255,.07)",color="#64748b",tickfont=dict(size=8)),angularaxis=dict(gridcolor="rgba(255,255,255,.07)",color="#64748b",tickfont=dict(size=9))),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=40,r=40,t=20,b=20))
                st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
                st.plotly_chart(fig_r,use_container_width=True)
                st.markdown('</div>',unsafe_allow_html=True)
            c1,c2=st.columns(2)
            for i,(tag,score) in enumerate(top):
                pct=int(score/mx*100); color="#2563eb" if pct>70 else ("#3b82f6" if pct>40 else "#1e3a8a")
                with (c1 if i%2==0 else c2):
                    st.markdown(f'<div style="display:flex;justify-content:space-between;font-size:.77rem;margin-bottom:2px"><span style="color:#94a3b8">{tag}</span><span style="color:#60a5fa;font-weight:600">{pct}%</span></div>{prog_bar(pct,color)}',unsafe_allow_html=True)
        else: st.info("Interaja com pesquisas para construir seu perfil de interesses.")
    st.markdown('</div>',unsafe_allow_html=True)

# ─── IMAGE ANALYSIS ────────────────────────────────
def page_img_search():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1rem;margin-bottom:.4rem">⊞ Análise Visual Científica</h1>',unsafe_allow_html=True)
    st.markdown('<p style="color:#64
