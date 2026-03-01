import subprocess, sys, os, json, hashlib, random, string, base64, re, io
from datetime import datetime
from collections import defaultdict, Counter
import math

# --- PIP INSTALLATION (kept for robustness, but ideally pre-installed) ---
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

st.set_page_config(page_title="Nebula", page_icon="🔬", layout="wide",
                   initial_sidebar_state="collapsed")

DB_FILE = "nebula_db.json"

# --- CACHED FUNCTIONS FOR PERFORMANCE ---
@st.cache_data(ttl=3600, show_spinner=False) # Cache the database loading for 1 hour
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except json.JSONDecodeError:
            st.error("Erro ao carregar o banco de dados. O arquivo pode estar corrompido.")
            return {}
        except Exception as e:
            st.error(f"Erro inesperado ao carregar o banco de dados: {e}")
            return {}
    return {}

def save_db():
    try:
        prefs_s = {k:dict(v) for k,v in st.session_state.user_prefs.items()}
        with open(DB_FILE,"w",encoding="utf-8") as f:
            json.dump({"users":st.session_state.users,
                       "feed_posts":st.session_state.feed_posts,
                       "folders":st.session_state.folders,
                       "user_prefs":prefs_s,
                       "saved_articles":st.session_state.saved_articles},
                      f,ensure_ascii=False,indent=2)
    except Exception as e:
        st.error(f"Erro ao salvar o banco de dados: {e}")

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
def time_ago(date_str):
    try:
        dt=datetime.strptime(date_str,"%Y-%m-%d"); delta=datetime.now()-dt
        if delta.days==0: return "hoje"
        if delta.days==1: return "ontem"
        if delta.days<7: return f"{delta.days}d"
        if delta.days<30: return f"{delta.days//7}sem"
        return f"{delta.days//30}m"
    except: return date_str
def fmt_num(n):
    try:
        n=int(n)
        return f"{n/1000:.1f}k" if n>=1000 else str(n)
    except: return str(n)
def guser():
    if not isinstance(st.session_state.get("users"),dict): return {}
    return st.session_state.users.get(st.session_state.current_user,{})
def get_photo(email):
    u=st.session_state.get("users",{})
    if not isinstance(u,dict): return None
    return u.get(email,{}).get("photo_b64")

USER_GRADIENTS = [
    "135deg,#f97316,#f59e0b","135deg,#10b981,#3b82f6","135deg,#8b5cf6,#ec4899",
    "135deg,#f59e0b,#10b981","135deg,#ef4444,#f97316","135deg,#3b82f6,#8b5cf6",
    "135deg,#06b6d4,#10b981","135deg,#f97316,#ef4444",
]
def ugrad(email): return f"linear-gradient({USER_GRADIENTS[hash(email or '') % len(USER_GRADIENTS)]})"

def is_online(email): return (hash(email+"online") % 3) != 0

STOPWORDS = {
    "de","a","o","que","e","do","da","em","um","para","é","com","uma","os","no","se",
    "na","por","mais","as","dos","como","mas","foi","ao","ele","das","tem","à","seu",
    "sua","ou","ser","quando","muito","há","nos","já","está","eu","também","só","pelo",
    "pela","até","isso","ela","entre","era","depois","sem","mesmo","aos","ter","seus",
    "the","of","and","to","in","is","it","that","was","he","for","on","are","as","with",
    "they","at","be","this","from","or","one","had","by","but","not","what","all","were",
    "we","when","your","can","said","there","use","an","each","which","she","do","how",
    "their","if","will","up","other","about","out","many","then","them","these","so",
}

@st.cache_data(show_spinner=False)
def extract_text_from_pdf_bytes(pdf_bytes):
    if PyPDF2 is None: return ""
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes)); text = ""
        for page in reader.pages[:30]: # Limit pages for performance
            try: text += page.extract_text() + "\n"
            except: pass
        return text[:50000] # Limit text length
    except: return ""

@st.cache_data(show_spinner=False)
def extract_text_from_csv_bytes(csv_bytes):
    try:
        df = pd.read_csv(io.BytesIO(csv_bytes), nrows=200) # Limit rows
        summary = f"Colunas: {', '.join(df.columns.tolist())}\nLinhas: {len(df)}\n"
        for col in df.columns[:10]: # Limit columns
            if df[col].dtype == object: summary += f"{col}: {', '.join(str(v) for v in df[col].dropna().head(5).tolist())}\n"
            else: summary += f"{col}: min={df[col].min():.2f}, max={df[col].max():.2f}\n"
        return summary
    except: return ""

@st.cache_data(show_spinner=False)
def extract_text_from_xlsx_bytes(xlsx_bytes):
    if openpyxl is None: return ""
    try:
        wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), read_only=True, data_only=True); text = ""
        for sheet_name in wb.sheetnames[:3]: # Limit sheets
            ws = wb[sheet_name]; text += f"\n=== {sheet_name} ===\n"
            for row in list(ws.iter_rows(max_row=50, values_only=True)): # Limit rows
                row_vals = [str(v) for v in row if v is not None]
                if row_vals: text += " | ".join(row_vals[:10]) + "\n" # Limit columns
        return text[:20000] # Limit text length
    except: return ""

@st.cache_data(show_spinner=False)
def extract_keywords_tfidf(text, top_n=30):
    if not text: return []
    words = re.findall(r'\b[a-záàâãéêíóôõúüçA-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]{4,}\b', text.lower())
    words = [w for w in words if w not in STOPWORDS]
    if not words: return []
    tf = Counter(words); total = sum(tf.values())
    top = sorted({w:c/total for w,c in tf.items()}.items(), key=lambda x:-x[1])[:top_n]
    return [w for w,_ in top]

@st.cache_data(show_spinner=False)
def extract_authors_from_text(text):
    authors = []; seen = set()
    for pat in [r'(?:Autor(?:es)?|Author(?:s)?)[:\s]+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){1,4})',
                r'(?:Por|By)[:\s]+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){1,3})']:
        for m in re.findall(pat, text):
            if m.strip().lower() not in seen and len(m.strip())>5:
                seen.add(m.strip().lower()); authors.append(m.strip())
    return authors[:8]

@st.cache_data(show_spinner=False)
def extract_years_from_text(text):
    years = re.findall(r'\b(19[5-9]\d|20[0-3]\d)\b', text)
    return sorted(Counter(years).items(), key=lambda x:-x[1])[:10]

@st.cache_data(show_spinner=False)
def extract_references_from_text(text):
    refs = []
    for block in re.split(r'\n(?=|$\d+$|)', text)[1:21]:
        clean = re.sub(r'\s+',' ',block.strip())
        if len(clean)>30: refs.append(clean[:200])
    return refs[:15]

@st.cache_data(show_spinner=False)
def compute_topic_distribution(keywords):
    topic_map = {
        "Saúde & Medicina": ["saúde","medicina","hospital","doença","tratamento","clínico","health","medical","clinical","therapy","disease","cancer"],
        "Biologia & Genômica": ["biologia","genômica","gene","dna","rna","proteína","célula","bacteria","vírus","genomics","biology","protein","cell","crispr"],
        "Neurociência": ["neurociência","neural","cérebro","cognição","memória","sinapse","neurônio","sono","brain","neuron","cognitive","memory","sleep"],
        "Computação & IA": ["algoritmo","machine","learning","inteligência","neural","dados","software","computação","ia","modelo","algorithm","deep","quantum"],
        "Física & Astronomia": ["física","quântica","partícula","energia","galáxia","astrofísica","cosmologia","physics","quantum","particle","galaxy","dark"],
        "Química & Materiais": ["química","molécula","síntese","reação","composto","polímero","chemistry","molecule","synthesis","reaction","nanomaterial"],
        "Engenharia": ["engenharia","sistema","robótica","automação","sensor","circuito","engineering","system","robotics","sensor","circuit"],
        "Ciências Sociais": ["sociedade","cultura","educação","política","economia","social","psicologia","society","culture","education","economics"],
        "Ecologia & Clima": ["ecologia","clima","ambiente","biodiversidade","ecosistema","ecology","climate","environment","biodiversity","sustainability"],
        "Matemática & Estatística": ["matemática","estatística","probabilidade","equação","modelo","mathematics","statistics","probability","equation"],
    }
    scores = defaultdict(int)
    for kw in keywords:
        for topic, terms in topic_map.items():
            if any(t in kw.lower() or kw.lower() in t for t in terms): scores[topic] += 1
    return dict(sorted(scores.items(), key=lambda x:-x[1])) if scores else {"Pesquisa Geral": 1}

@st.cache_data(show_spinner=False)
def estimate_reading_time(text):
    words = len(text.split()); return max(1, round(words/200)), words

@st.cache_data(show_spinner=False)
def compute_writing_quality(text, keywords, references):
    score = 50
    if len(keywords) > 15: score += 15
    if len(references) > 8: score += 15
    sentences = re.split(r'[.!?]+', text)
    avg_len = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
    if 10 < avg_len < 30: score += 10
    technical_density = len([k for k in keywords if len(k) > 7]) / max(len(keywords), 1)
    if technical_density > 0.5: score += 10
    return min(100, score)

@st.cache_data(show_spinner=False)
def search_references_online(keywords, n=5):
    if not keywords: return []
    try:
        r = requests.get("https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query":" ".join(keywords[:5]),"limit":n,
                    "fields":"title,authors,year,abstract,venue,externalIds,citationCount"},timeout=8)
        if r.status_code==200:
            results=[]
            for p in r.json().get("data",[]):
                ext=p.get("externalIds",{}) or {}; doi=ext.get("DOI",""); arxiv=ext.get("ArXiv","")
                url=f"https://arxiv.org/abs/{arxiv}" if arxiv else (f"https://doi.org/{doi}" if doi else "")
                alist=p.get("authors",[]) or []; authors=", ".join(a.get("name","") for a in alist[:3])
                if len(alist)>3: authors+=" et al."
                results.append({"title":p.get("title","?"),"authors":authors or "—","year":p.get("year","?"),
                    "venue":p.get("venue","") or "—","abstract":(p.get("abstract","") or "")[:200],
                    "url":url,"citations":p.get("citationCount",0),"doi":doi})
            return results
    except: pass
    return []

@st.cache_data(show_spinner=False)
def analyze_document_intelligent(fname, fbytes, ftype, research_area=""):
    result = {"file":fname,"type":ftype,"text_length":0,"keywords":[],"authors":[],
              "years":[],"references":[],"topics":{},"references_online":[],"relevance_score":0,
              "summary":"","strengths":[],"improvements":[],"writing_quality":0,"reading_time":0,
              "word_count":0,"key_concepts":[],"concept_frequency":{},"sentence_complexity":0}
    text = ""
    if ftype=="PDF" and fbytes: text=extract_text_from_pdf_bytes(fbytes)
    elif ftype in ("Planilha","Dados") and fbytes:
        if fname.endswith(".xlsx") or fname.endswith(".xls"): text=extract_text_from_xlsx_bytes(fbytes)
        elif fname.endswith(".csv"): text=extract_text_from_csv_bytes(fbytes)
    elif ftype in ("Word","Texto","Markdown") and fbytes:
        try: text=fbytes.decode("utf-8",errors="ignore")
        except: pass
    result["text_length"]=len(text)
    if text:
        result["keywords"]=extract_keywords_tfidf(text,30)
        result["authors"]=extract_authors_from_text(text)
        result["years"]=extract_years_from_text(text)
        result["references"]=extract_references_from_text(text)
        result["topics"]=compute_topic_distribution(result["keywords"])
        minutes, words = estimate_reading_time(text)
        result["reading_time"]=minutes; result["word_count"]=words
        result["writing_quality"]=compute_writing_quality(text,result["keywords"],result["references"])
        words_list=re.findall(r'\b[a-záàâãéêíóôõúüçA-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]{4,}\b',text.lower())
        words_filtered=[w for w in words_list if w not in STOPWORDS]
        freq=Counter(words_filtered)
        result["concept_frequency"]=dict(freq.most_common(20))
        result["key_concepts"]=[w for w,_ in freq.most_common(10)]
        sentences=re.split(r'[.!?]+',text)
        result["sentence_complexity"]=round(sum(len(s.split()) for s in sentences)/max(len(sentences),1),1)
        if research_area:
            area_words=research_area.lower().split()
            rel=sum(1 for w in area_words if any(w in kw for kw in result["keywords"]))
            result["relevance_score"]=min(100,rel*15+45)
        else: result["relevance_score"]=65
        n_refs=len(result["references"]); n_kw=len(result["keywords"])
        if n_refs>5: result["strengths"].append(f"Boa referenciação ({n_refs} refs)")
        if n_kw>15: result["strengths"].append(f"Vocabulário técnico rico ({n_kw} termos)")
        if result["authors"]: result["strengths"].append(f"Autoria: {result['authors'][0]}")
        if result["writing_quality"]>70: result["strengths"].append("Alta qualidade técnica")
        if words>3000: result["strengths"].append(f"Texto detalhado ({words} palavras)")
        if n_refs<3: result["improvements"].append("Adicionar mais referências")
        if not result["authors"]: result["improvements"].append("Incluir autoria explícita")
        if result["writing_quality"]<50: result["improvements"].append("Melhorar densidade técnica")
        if words<500: result["improvements"].append("Expandir o conteúdo")
        top_topics=list(result["topics"].keys())[:3]; top_kw=result["keywords"][:5]
        result["summary"]=f"{ftype} · {words} palavras · ~{minutes} min · Temas: {', '.join(top_topics)} · {', '.join(top_kw)}."
    else:
        result["summary"]=f"Arquivo {ftype} — análise de texto não disponível."
        result["relevance_score"]=50
        result["keywords"]=extract_keywords_tfidf(fname.lower().replace("_"," "),5)
        result["topics"]=compute_topic_distribution(result["keywords"])
    return result

@st.cache_data(show_spinner=False)
def analyze_image_advanced(uploaded_file_bytes):
    try:
        img=PILImage.open(io.BytesIO(uploaded_file_bytes)).convert("RGB"); orig=img.size
        small=img.resize((512,512)); arr=np.array(small,dtype=np.float32)
        r,g,b_ch=arr[:,:,0],arr[:,:,1],arr[:,:,2]
        mr,mg,mb=float(r.mean()),float(g.mean()),float(b_ch.mean())
        gray=arr.mean(axis=2)
        gx=np.pad(np.diff(gray,axis=1),((0,0),(0,1)),mode='edge')
        gy=np.pad(np.diff(gray,axis=0),((0,1),(0,0)),mode='edge')
        edge_intensity=float(np.sqrt(gx**2+gy**2).mean())
        h_s=float(np.abs(gy).mean()); v_s=float(np.abs(gx).mean())
        d1=float(np.abs(gx+gy).mean()); d2=float(np.abs(gx-gy).mean())
        strengths={"Horizontal":h_s,"Vertical":v_s,"Diagonal A":d1,"Diagonal B":d2}
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
        if lr_sym>0.75: shapes.append("Simetria Bilateral")
        if edge_intensity>32: shapes.append("Contornos Nítidos")
        if not shapes: shapes.append("Irregular")
        if skin_pct>0.15 and mr>140: cat,desc,kw,material,obj_type,context="Histopatologia H&E",f"Tecido orgânico detectado ({skin_pct*100:.0f}% da área).","hematoxylin eosin HE staining histopathology tissue","Tecido Biológico","Amostra Histopatológica","Microscopia óptica de tecidos corados"
        elif has_grid and edge_intensity>18: cat,desc,kw,material,obj_type,context="Cristalografia / Difração",f"Padrão periódico detectado (borda: {edge_intensity:.1f}).","X-ray diffraction crystallography TEM crystal structure","Material Cristalino","Rede Cristalina","Análise de estrutura atômica"
        elif mg>165 and mr<125: cat,desc,kw,material,obj_type,context="Fluorescência GFP/FITC",f"Canal verde dominante (G={mg:.0f}).","GFP fluorescence confocal microscopy protein","Proteínas Fluorescentes","Células Marcadas","Microscopia confocal de fluorescência"
        elif mb>165 and mr<110: cat,desc,kw,material,obj_type,context="Fluorescência DAPI",f"Canal azul dominante (B={mb:.0f}).","DAPI nuclear staining DNA fluorescence nucleus","DNA / Cromatina","Núcleos Celulares","Marcação nuclear fluorescente"
        elif has_circular and edge_intensity>24: cat,desc,kw,material,obj_type,context="Microscopia Celular",f"Estruturas circulares detectadas (intensidade: {edge_intensity:.1f}).","cell organelle vesicle bacteria microscopy biology","Componentes Celulares","Células/Organelas","Microscopia de campo claro"
        elif edge_intensity>40: cat,desc,kw,material,obj_type,context="Diagrama / Gráfico Científico","Bordas muito nítidas detectadas.","scientific visualization chart diagram data","Dados Estruturados","Gráfico/Diagrama","Representação visual de dados"
        elif sym>0.82: cat,desc,kw,material,obj_type,context="Estrutura Molecular",f"Alta simetria detectada ({sym:.3f}).","molecular structure protein crystal symmetry chemistry","Moléculas","Estrutura Molecular","Visualização molecular 3D"
        else:
            temp="quente" if warm else ("fria" if cool else "neutra")
            cat,desc,kw,material,obj_type,context="Imagem Científica Geral",f"Temperatura de cor {temp}.","scientific image analysis research microscopy","Variado","Imagem Científica","Análise genérica"
        conf=min(96,48+edge_intensity/2+entropy*2.8+sym*5+(8 if skin_pct>0.1 else 0)+(6 if has_grid else 0))
        r_hist=np.histogram(r.ravel(),bins=32,range=(0,255))[0].tolist()
        g_hist=np.histogram(g.ravel(),bins=32,range=(0,255))[0].tolist()
        b_hist=np.histogram(b_ch.ravel(),bins=32,range=(0,255))[0].tolist()
        return {"category":cat,"description":desc,"kw":kw,"material":material,"object_type":obj_type,
                "context":context,"confidence":round(conf,1),
                "lines":{"direction":line_dir,"intensity":round(edge_intensity,2),"strengths":strengths},
                "shapes":shapes,"symmetry":round(sym,3),"lr_symmetry":round(lr_sym,3),
                "color":{"r":round(mr,1),"g":round(mg,1),"b":round(mb,1),"warm":warm,"cool":cool,"dom":dom_ch,"sat":round(sat*100,1)},
                "texture":{"entropy":round(entropy,3),"contrast":round(contrast,2),
                           "complexity":"Alta" if entropy>5.5 else ("Média" if entropy>4 else "Baixa")},
                "palette":palette,"size":orig,
                "histograms":{"r":r_hist,"g":g_hist,"b":b_hist},
                "brightness":round(float(gray.mean()),1),"sharpness":round(edge_intensity,2)}
    except Exception as e: st.error(f"Erro na análise: {e}"); return None

EMAP = {"pdf":"PDF","docx":"Word","doc":"Word","xlsx":"Planilha","xls":"Planilha",
        "csv":"Dados","txt":"Texto","py":"Código Python","r":"Código R",
        "ipynb":"Notebook","pptx":"Apresentação","png":"Imagem","jpg":"Imagem",
        "jpeg":"Imagem","tiff":"Imagem Científica","md":"Markdown"}

def get_ftype(fname):
    ext=fname.split(".")[-1].lower() if "." in fname else ""
    return EMAP.get(ext,"Arquivo")

@st.cache_data(show_spinner=False)
def search_ss(query, limit=8):
    results=[]
    try:
        r=requests.get("https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query":query,"limit":limit,"fields":"title,authors,year,abstract,venue,externalIds,openAccessPdf,citationCount"},timeout=9)
        if r.status_code==200:
            for p in r.json().get("data",[]):
                ext=p.get("externalIds",{}) or {}; doi=ext.get("DOI",""); arxiv=ext.get("ArXiv","")
                pdf=p.get("openAccessPdf") or {}
                link=pdf.get("url","") or (f"https://arxiv.org/abs/{arxiv}" if arxiv else (f"https://doi.org/{doi}" if doi else ""))
                alist=p.get("authors",[]) or []; authors=", ".join(a.get("name","") for a in alist[:3])
                if len(alist)>3: authors+=" et al."
                results.append({"title":p.get("title","Sem título"),"authors":authors or "—","year":p.get("year","?"),
                    "source":p.get("venue","") or "Semantic Scholar","doi":doi or arxiv or "—",
                    "abstract":(p.get("abstract","") or "")[:280],"url":link,
                    "citations":p.get("citationCount",0),"origin":"semantic"})
            return results
    except: pass
    return []

@st.cache_data(show_spinner=False)
def search_cr(query, limit=4):
    results=[]
    try:
        r=requests.get("https://api.crossref.org/works",
            params={"query":query,"rows":limit,"select":"title,author,issued,abstract,DOI,container-title,is-referenced-by-count","mailto":"nebula@example.com"},timeout=9)
        if r.status_code==200:
            for p in r.json().get("message",{}).get("items",[]):
                title=(p.get("title") or ["Sem título"])[0]
                ars=p.get("author",[]) or []
                authors=", ".join(f'{a.get("given","").split()[0] if a.get("given") else ""} {a.get("family","")}'.strip() for a in ars[:3])
                if len(ars)>3: authors+=" et al."
                year=(p.get("issued",{}).get("date-parts") or [[None]])[0][0]
                doi=p.get("DOI",""); abstract=re.sub(r'<[^>]+>','',p.get("abstract","") or "")[:280]
                results.append({"title":title,"authors":authors or "—","year":year or "?",
                    "source":(p.get("container-title") or ["CrossRef"])[0],"doi":doi,
                    "abstract":abstract,"url":f"https://doi.org/{doi}" if doi else "",
                    "citations":p.get("is-referenced-by-count",0),"origin":"crossref"})
    except: pass
    return results

def record(tags, w=1.0):
    email=st.session_state.get("current_user")
    if not email or not tags: return
    prefs=st.session_state.user_prefs.setdefault(email,defaultdict(float))
    for t in tags: prefs[t.lower()]+=w

@st.cache_data(show_spinner=False)
def get_recs(email, n=2, feed_posts_data): # Pass feed_posts_data explicitly for caching
    prefs=st.session_state.user_prefs.get(email,{})
    if not prefs: return []
    def score(p): return sum(prefs.get(t.lower(),0) for t in p.get("tags",[])+p.get("connections",[]))
    scored=[(score(p),p) for p in feed_posts_data if email not in p.get("liked_by",[])]
    return [p for s,p in sorted(scored,key=lambda x:-x[0]) if s>0][:n]

@st.cache_data(show_spinner=False)
def area_to_tags(area):
    a=(area or "").lower()
    M={"ia":["machine learning","LLM"],"inteligência artificial":["machine learning","LLM"],
       "neurociência":["sono","memória","cognição"],"biologia":["célula","genômica"],"física":["quantum","astrofísica"],
       "medicina":["diagnóstico","terapia"],"astronomia":["cosmologia","galáxia"],"computação":["algoritmo","redes"],
       "psicologia":["cognição","comportamento"],"genômica":["DNA","CRISPR"]}
    for k,v in M.items():
        if k in a: return v
    return [w.strip() for w in a.replace(","," ").split() if len(w)>3][:5]

SEED_POSTS = [
    {"id":1,"author":"Carlos Mendez","author_email":"carlos@nebula.ai","avatar":"CM","area":"Neurociência",
     "title":"Efeitos da Privação de Sono na Plasticidade Sináptica",
     "abstract":"Investigamos como 24h de privação de sono afetam espinhas dendríticas em ratos Wistar, com redução de 34% na plasticidade hipocampal. Janela crítica identificada nas primeiras 6h de recuperação.",
     "tags":["neurociência","sono","memória","hipocampo"],"likes":47,
     "comments":[{"user":"Maria Silva","text":"Excelente metodologia!"},{"user":"João Lima","text":"Quais os critérios de exclusão?"}],
     "status":"Em andamento","date":"2026-02-10","liked_by":[],"saved_by":[],"connections":["sono","memória"],"views":312},
    {"id":2,"author":"Luana Freitas","author_email":"luana@nebula.ai","avatar":"LF","area":"Biomedicina",
     "title":"CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras",
     "abstract":"Vetor AAV9 modificado para entrega de CRISPR no gene DMD com eficiência de 78% em modelos mdx. Publicação em Cell prevista Q2 2026.",
     "tags":["CRISPR","gene terapia","músculo","AAV9"],"likes":93,
     "comments":[{"user":"Ana","text":"Quando iniciam os trials clínicos?"}],
     "status":"Publicado","date":"2026-01-28","liked_by":[],"saved_by":[],"connections":["genômica","distrofia"],"views":891},
    {"id":3,"author":"Rafael Souza","author_email":"rafael@nebula.ai","avatar":"RS","area":"Computação",
     "title":"Redes Neurais Quântico-Clássicas para Otimização Combinatória",
     "abstract":"Arquitetura híbrida variacional combinando qubits supercondutores com camadas densas clássicas. TSP resolvido com 40% menos iterações.",
     "tags":["quantum ML","otimização","TSP"],"likes":201,
     "comments":[],"status":"Em andamento","date":"2026-02-15","liked_by":[],"saved_by":[],"connections":["computação quântica"],"views":1240},
    {"id":4,"author":"Priya Nair","author_email":"priya@nebula.ai","avatar":"PN","area":"Astrofísica",
     "title":"Detecção de Matéria Escura via Lentes Gravitacionais Fracas",
     "abstract":"Mapeamento com 100M de galáxias do DES Y3. Tensão de 2.8σ com ΛCDM em escalas < 1 Mpc.",
     "tags":["astrofísica","matéria escura","cosmologia","DES"],"likes":312,
     "comments":[],"status":"Publicado","date":"2026-02-01","liked_by":[],"saved_by":[],"connections":["cosmologia"],"views":2180},
    {"id":5,"author":"João Lima","author_email":"joao@nebula.ai","avatar":"JL","area":"Psicologia",
     "title":"Viés de Confirmação em Decisões Médicas Assistidas por IA",
     "abstract":"Estudo duplo-cego com 240 médicos revelou que sistemas de IA mal calibrados amplificam vieses cognitivos em 22% dos casos.",
     "tags":["psicologia","IA","cognição","medicina"],"likes":78,
     "comments":[{"user":"Carlos M.","text":"Muito relevante!"}],
     "status":"Publicado","date":"2026-02-08","liked_by":[],"saved_by":[],"connections":["cognição","IA"],"views":456},
]

SEED_USERS = {
    "demo@nebula.ai":{"name":"Ana Pesquisadora","password":hp("demo123"),"bio":"Pesquisadora em IA e Ciências Cognitivas | UFMG","area":"Inteligência Artificial","followers":128,"following":47,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "carlos@nebula.ai":{"name":"Carlos Mendez","password":hp("nebula123"),"bio":"Neurocientista | UFMG | Plasticidade sináptica e sono","area":"Neurociência","followers":210,"following":45,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "luana@nebula.ai":{"name":"Luana Freitas","password":hp("nebula123"),"bio":"Biomédica | FIOCRUZ | CRISPR e terapia gênica","area":"Biomedicina","followers":178,"following":62,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "rafael@nebula.ai":{"name":"Rafael Souza","password":hp("nebula123"),"bio":"Computação Quântica | USP | Algoritmos híbridos","area":"Computação","followers":340,"following":88,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "priya@nebula.ai":{"name":"Priya Nair","password":hp("nebula123"),"bio":"Astrofísica | MIT | Dark matter & gravitational lensing","area":"Astrofísica","followers":520,"following":31,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "joao@nebula.ai":{"name":"João Lima","password":hp("nebula123"),"bio":"Psicólogo Cognitivo | UNICAMP | IA e vieses clínicos","area":"Psicologia","followers":95,"following":120,"verified":True,"2fa_enabled":False,"photo_b64":None},
}

CHAT_INIT = {
    "carlos@nebula.ai":[{"from":"carlos@nebula.ai","text":"Oi! Vi seu comentário na pesquisa de sono.","time":"09:14"},{"from":"me","text":"Achei muito interessante!","time":"09:16"}],
    "luana@nebula.ai":[{"from":"luana@nebula.ai","text":"Podemos colaborar no próximo projeto?","time":"ontem"}],
    "rafael@nebula.ai":[{"from":"rafael@nebula.ai","text":"Já compartilhei o repositório.","time":"08:30"}],
}

def init():
    if "initialized" in st.session_state: return
    st.session_state.initialized = True
    disk = load_db() # Use cached load_db
    disk_users = disk.get("users",{})
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
        p.setdefault("liked_by",[]); p.setdefault("saved_by",[])
        p.setdefault("comments",[]); p.setdefault("views",200)
    st.session_state.setdefault("feed_posts",raw_posts)
    st.session_state.setdefault("folders",disk.get("folders",{}))
    st.session_state.setdefault("folder_files_bytes",{})
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

# ══════════════════════════════════════════════════════════════════
#  CSS — LIQUID GLASS, CLARO, MODERNO, CORES VIBRANTES
# ══════════════════════════════════════════════════════════════════
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cabinet+Grotesk:wght@400;500;600;700;800;900&family=Satoshi:wght@300;400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');

:root {
  /* Backgrounds - Base escura para contraste com o liquid glass */
  --bg:    #080808;
  --s1:    #101010;
  --s2:    #181818;
  --s3:    #202020;
  --s4:    #282828;

  /* Cores vibrantes para acentos */
  --or1: #FF9800; /* Laranja */
  --or2: #FFA726;
  --or3: #FFB74D;
  --or4: #FFCC80;

  --am1: #FFEB3B; /* Amarelo */
  --am2: #FFEE58;
  --am3: #FFF176;
  --am4: #FFF59D;

  --gr1: #4CAF50; /* Verde */
  --gr2: #66BB6A;
  --gr3: #81C784;
  --gr4: #A5D6A7;

  --bl1: #2196F3; /* Azul */
  --bl2: #42A5F5;
  --bl3: #64B5F6;
  --bl4: #90CAF9;

  /* Texto - Ajustado para contraste em fundo mais claro */
  --t0: #FFFFFF;   /* headings */
  --t1: #E0E0E0;   /* primary */
  --t2: #B0B0B0;   /* secondary */
  --t3: #808080;   /* muted */
  --t4: #505050;   /* very muted */

  /* Glass surfaces — Mais claro e translúcido */
  --glass:  rgba(255, 255, 255, 0.15); /* Mais opaco para o efeito de vidro */
  --glass2: rgba(255, 255, 255, 0.20); /* Um pouco mais opaco para contraste */
  --glassl: rgba(255, 255, 255, 0.08); /* Overlay leve, mais visível */

  /* Borders - Mais sutis */
  --gb1: rgba(255, 255, 255, 0.10);
  --gb2: rgba(255, 255, 255, 0.15);
  --gb3: rgba(255, 255, 255, 0.20);

  /* Status */
  --ok: #66BB6A; /* Verde */
  --warn: #FFEB3B; /* Amarelo */
  --err: #EF5350; /* Vermelho */

  /* Radii */
  --r6:6px; --r10:10px; --r14:14px; --r18:18px; --r24:24px; --r32:32px;
}

*, *::before, *::after { box-sizing:border-box; margin:0; padding:0; }

html, body, .stApp {
  background: var(--bg) !important;
  color: var(--t1) !important;
  font-family: 'Outfit', -apple-system, sans-serif !important;
}

/* ── Ambient background - Mais etéreo ── */
.stApp::before {
  content:''; position:fixed; inset:0; pointer-events:none; z-index:0;
  background:
    radial-gradient(ellipse 70% 55% at 0% 0%, rgba(255,152,0,.06) 0%, transparent 55%), /* Laranja suave */
    radial-gradient(ellipse 50% 60% at 100% 100%, rgba(76,175,80,.04) 0%, transparent 50%), /* Verde suave */
    radial-gradient(ellipse 35% 35% at 55% 40%, rgba(33,150,243,.02) 0%, transparent 60%); /* Azul suave */
}
/* ── Subtle star field - Mais discreto ── */
.stApp::after {
  content:''; position:fixed; inset:0; pointer-events:none; z-index:0;
  background-image:
    radial-gradient(1px 1px at 12% 18%, rgba(255,235,59,.2) 0%, transparent 100%), /* Amarelo */
    radial-gradient(1px 1px at 34% 52%, rgba(255,152,0,.15) 0%, transparent 100%), /* Laranja */
    radial-gradient(1.2px 1.2px at 67% 15%, rgba(76,175,80,.2) 0%, transparent 100%), /* Verde */
    radial-gradient(1px 1px at 82% 70%, rgba(255,235,59,.1) 0%, transparent 100%), /* Amarelo */
    radial-gradient(1px 1px at 48% 88%, rgba(33,150,243,.08) 0%, transparent 100%), /* Azul */
    radial-gradient(1px 1px at 20% 76%, rgba(76,175,80,.1) 0%, transparent 100%), /* Verde */
    radial-gradient(1px 1px at 90% 25%, rgba(255,152,0,.12) 0%, transparent 100%); /* Laranja */
}

/* ── Hide Streamlit chrome ── */
[data-testid="collapsedControl"], section[data-testid="stSidebar"] { display:none !important; }
header[data-testid="stHeader"]   { display:none !important; }
#MainMenu, footer, .stDeployButton { display:none !important; }
[data-testid="stToolbar"], [data-testid="stDecoration"] { display:none !important; }

.block-container {
  padding-top:0 !important; padding-bottom:4rem !important;
  max-width:1420px !important; position:relative; z-index:1;
  padding-left:.9rem !important; padding-right:.9rem !important;
}

/* ═══════════════════════════════════════
   TYPOGRAPHY
═══════════════════════════════════════ */
h1 { font-family:'Outfit',sans-serif !important; font-size:1.55rem !important;
     font-weight:800 !important; letter-spacing:-.03em; color:var(--t0) !important; }
h2 { font-family:'Outfit',sans-serif !important; font-size:1.02rem !important;
     font-weight:700 !important; letter-spacing:-.01em; color:var(--t0) !important; }
h3 { font-family:'Outfit',sans-serif !important; font-size:.88rem !important;
     font-weight:600 !important; color:var(--t1) !important; }

/* ═══════════════════════════════════════
   TOP NAV - Icon-only pills
═══════════════════════════════════════ */
.neb-navwrap {
  position:sticky; top:0; z-index:1000;
  background:rgba(8,8,8,.85); /* Fundo escuro, mais translúcido */
  backdrop-filter:blur(40px) saturate(180%);
  -webkit-backdrop-filter:blur(40px) saturate(180%);
  border-bottom:1px solid var(--gb1);
  padding:.42rem .9rem;
  box-shadow:0 1px 0 rgba(255,255,255,.05), 0 4px 24px rgba(0,0,0,.5);
  margin-bottom:1.1rem;
}
.neb-navwrap [data-testid="stHorizontalBlock"] {
  align-items:center !important; gap:0 !important;
}
.neb-navwrap [data-testid="stHorizontalBlock"] > div { padding:0 2px !important; }

/* Logo button */
.nav-logo .stButton>button {
  background:transparent !important; border:none !important;
  font-family:'Outfit',sans-serif !important; font-size:.95rem !important;
  font-weight:800 !important; letter-spacing:-.04em !important;
  background:linear-gradient(135deg,var(--or1),var(--am1),var(--gr1)) !important; /* Cores vibrantes */
  -webkit-background-clip:text !important; -webkit-text-fill-color:transparent !important;
  background-clip:text !important;
  padding:.28rem .5rem !important; box-shadow:none !important;
  height:36px !important; min-height:36px !important;
}
.nav-logo .stButton>button:hover { transform:none !important; box-shadow:none !important; }

/* Nav pills - Icon only */
.nav-pill .stButton>button {
  background:transparent !important; border:1px solid transparent !important;
  border-radius:var(--r32) !important; color:var(--t3) !important;
  font-family:'Outfit',sans-serif !important; font-size:.95rem !important; /* Increased font size for icons */
  font-weight:500 !important; padding:.26rem .55rem !important;
  box-shadow:none !important; white-space:nowrap !important;
  height:32px !important; min-height:32px !important;
  transition:all .15s !important;
  display:flex; align-items:center; justify-content:center; /* Center icon */
}
.nav-pill .stButton>button:hover {
  background:rgba(255,255,255,.10) !important; /* Mais claro */
  border-color:rgba(255,255,255,.15) !important;
  color:var(--t1) !important; transform:none !important; box-shadow:none !important;
}
.nav-pill-active .stButton>button {
  background:linear-gradient(135deg,rgba(255,152,0,.25),rgba(255,235,59,.15)) !important; /* Laranja/Amarelo */
  border:1px solid rgba(255,255,255,.2) !important;
  color:var(--or1) !important; font-weight:700 !important;
  box-shadow:0 2px 14px rgba(255,152,0,.1), inset 0 1px 0 rgba(255,255,255,.05) !important;
  height:32px !important; min-height:32px !important; font-size:.95rem !important;
}
.nav-pill-active .stButton>button:hover { transform:none !important; }

/* Avatar button */
.nav-av .stButton>button {
  width:34px !important; height:34px !important; min-height:34px !important;
  border-radius:50% !important; padding:0 !important;
  font-family:'Outfit',sans-serif !important; font-weight:800 !important;
  font-size:.70rem !important; color:white !important;
  border:2px solid rgba(255,255,255,.15) !important;
  box-shadow:0 2px 10px rgba(0,0,0,.4) !important;
  transition:all .18s !important; line-height:1 !important;
  background-size: cover !important; /* Ensure image covers button */
  background-position: center !important; /* Center image */
  color: transparent !important; /* Hide initials if image is present */
}
.nav-av .stButton>button:hover {
  transform:scale(1.10) !important;
  border-color:rgba(255,255,255,.3) !important;
  box-shadow:0 4px 16px rgba(255,152,0,.15) !important; /* Laranja suave */
}

/* ═══════════════════════════════════════
   BUTTONS
═══════════════════════════════════════ */
.stButton>button {
  background:var(--glass) !important;
  backdrop-filter:blur(16px) !important; -webkit-backdrop-filter:blur(16px) !important;
  border:1px solid var(--gb1) !important; border-radius:var(--r10) !important;
  color:var(--t2) !important; font-family:'Outfit',sans-serif !important;
  font-weight:500 !important; font-size:.78rem !important;
  padding:.40rem .82rem !important;
  transition:all .18s cubic-bezier(.4,0,.2,1) !important;
  box-shadow:0 1px 8px rgba(0,0,0,.3) !important;
  letter-spacing:.005em !important;
}
.stButton>button:hover {
  background:linear-gradient(135deg,rgba(255,152,0,.2),rgba(255,235,59,.1)) !important; /* Laranja/Amarelo */
  border-color:rgba(255,255,255,.2) !important;
  color:var(--t0) !important;
  transform:translateY(-1px) !important;
  box-shadow:0 4px 16px rgba(255,152,0,.1) !important;
}
.stButton>button:active { transform:scale(.97) !important; }

/* Primary */
.btn-primary .stButton>button {
  background:linear-gradient(135deg,var(--or1),var(--am1)) !important; /* Laranja/Amarelo */
  border-color:rgba(255,255,255,.25) !important;
  color:white !important;
  font-weight:600 !important;
  box-shadow:0 4px 18px rgba(255,152,0,.2), inset 0 1px 0 rgba(255,255,255,.12) !important;
}
.btn-primary .stButton>button:hover {
  background:linear-gradient(135deg,var(--or2),var(--am2)) !important;
  box-shadow:0 7px 24px rgba(255,152,0,.25) !important;
}
/* Danger */
.btn-danger .stButton>button {
  background:rgba(239,83,80,.07) !important; /* Vermelho */
  border-color:rgba(239,83,80,.20) !important; color:#EF5350 !important;
}
.btn-danger .stButton>button:hover {
  background:rgba(239,83,80,.14) !important;
  border-color:rgba(239,83,80,.32) !important;
}
/* Green */
.btn-green .stButton>button {
  background:linear-gradient(135deg,rgba(76,175,80,.25),rgba(102,187,106,.1)) !important; /* Verde */
  border-color:rgba(76,175,80,.2) !important;
  color:var(--gr2) !important;
}

/* Compose prompt */
.compose-prompt .stButton>button {
  background:rgba(255,255,255,.05) !important; /* Mais claro */
  border:1px solid var(--gb1) !important; border-radius:var(--r32) !important;
  color:var(--t3) !important; font-size:.84rem !important; font-weight:400 !important;
  text-align:left !important; padding:.68rem 1.3rem !important; width:100% !important;
  display:flex !important; justify-content:flex-start !important; box-shadow:none !important;
}
.compose-prompt .stButton>button:hover {
  background:rgba(255,255,255,.10) !important;
  border-color:rgba(255,255,255,.15) !important;
  color:var(--t2) !important;
  transform:none !important; box-shadow:none !important;
}

/* ═══════════════════════════════════════
   INPUTS
═══════════════════════════════════════ */
.stTextInput input, .stTextArea textarea {
  background:rgba(8,8,8,.88) !important; /* Fundo escuro para contraste */
  border:1px solid var(--gb1) !important; border-radius:var(--r10) !important;
  color:var(--t1) !important; font-family:'Outfit',sans-serif !important;
  font-size:.84rem !important; transition:border-color .15s, box-shadow .15s !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color:rgba(255,255,255,.3) !important;
  box-shadow:0 0 0 3px rgba(255,255,255,.05) !important;
}
.stTextInput label,.stTextArea label,.stSelectbox label,.stFileUploader label,.stNumberInput label {
  color:var(--t3) !important; font-size:.62rem !important;
  letter-spacing:.09em !important; text-transform:uppercase !important; font-weight:600 !important;
}

/* ═══════════════════════════════════════
   AVATARS
═══════════════════════════════════════ */
.av {
  border-radius:50%; background:linear-gradient(135deg,var(--or1),var(--am1));
  display:flex; align-items:center; justify-content:center;
  font-family:'Outfit',sans-serif; font-weight:700; color:white;
  border:1.5px solid rgba(255,255,255,.1);
  flex-shrink:0; overflow:hidden;
  box-shadow:0 2px 8px rgba(0,0,0,.35);
}
.av img { width:100%; height:100%; object-fit:cover; border-radius:50%; }

/* ═══════════════════════════════════════
   CARDS - More liquid glass effect
═══════════════════════════════════════ */
.card {
  background:var(--glass); backdrop-filter:blur(24px) saturate(150%);
  -webkit-backdrop-filter:blur(24px) saturate(150%);
  border:1px solid var(--gb1); border-radius:var(--r18);
  box-shadow:0 3px 24px rgba(0,0,0,.40), inset 0 1px 0 rgba(255,255,255,.04);
  position:relative; overflow:hidden;
}
.card::after {
  content:''; position:absolute; top:0; left:0; right:0; height:1px;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.09),transparent);
  pointer-events:none;
}

/* Post card */
.post {
  background:var(--glass); border:1px solid var(--gb1); border-radius:var(--r18);
  margin-bottom:.75rem; overflow:hidden; position:relative;
  box-shadow:0 2px 16px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.03);
  animation:fadeUp .22s cubic-bezier(.34,1.1,.64,1) both;
  transition:border-color .16s, box-shadow .16s;
}
.post:hover {
  border-color:rgba(255,255,255,.18);
  box-shadow:0 6px 28px rgba(0,0,0,.45), 0 0 0 1px rgba(255,255,255,.05);
}
.post::after {
  content:''; position:absolute; top:0; left:0; right:0; height:1px;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.06),transparent);
  pointer-events:none;
}

/* Compose card */
.compose-card {
  background:rgba(8,8,8,.80); border:1px solid rgba(255,255,255,.22);
  border-radius:var(--r18); padding:1.15rem 1.35rem; margin-bottom:.85rem;
  box-shadow:0 3px 20px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.06);
  animation:fadeUp .16s ease both;
}

/* Sidebar sections */
.sc {
  background:var(--glass); border:1px solid var(--gb1);
  border-radius:var(--r18); padding:1rem 1.05rem; margin-bottom:.7rem;
}
/* Search result card */
.scard {
  background:var(--glass); border:1px solid var(--gb1); border-radius:var(--r14);
  padding:.85rem 1.05rem; margin-bottom:.5rem;
  transition:border-color .14s, transform .14s;
}
.scard:hover { border-color:var(--gb2); transform:translateY(-1px); }

/* Analytics box */
.abox {
  background:rgba(8,8,8,.80); border:1px solid rgba(255,255,255,.14);
  border-radius:var(--r14); padding:.95rem; margin-bottom:.7rem;
}
.pbox {
  background:rgba(76,175,80,.04); border:1px solid rgba(76,175,80,.15); /* Verde */
  border-radius:var(--r14); padding:.9rem; margin-bottom:.65rem;
}
.img-rc {
  background:rgba(76,175,80,.04); border:1px solid rgba(76,175,80,.13); /* Verde */
  border-radius:var(--r14); padding:.85rem; margin-bottom:.5rem;
}
.chart-glass {
  background:var(--glass); border:1px solid var(--gb1);
  border-radius:var(--r14); padding:.7rem; margin-bottom:.7rem;
}

/* Metrics box */
.mbox {
  background:var(--glass); border:1px solid var(--gb1);
  border-radius:var(--r14); padding:.9rem; text-align:center;
}
.mval {
  font-family:'Outfit',sans-serif; font-size:1.65rem; font-weight:800;
  background:linear-gradient(135deg,var(--or1),var(--am1)); /* Laranja/Amarelo */
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.mval-green {
  font-family:'Outfit',sans-serif; font-size:1.65rem; font-weight:800;
  background:linear-gradient(135deg,var(--gr1),var(--bl1)); /* Verde/Azul */
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.mlbl { font-size:.60rem; color:var(--t3); margin-top:3px; letter-spacing:.09em; text-transform:uppercase; font-weight:600; }

/* Alerts */
.ai-warn {
  background:rgba(255,235,59,.07); border:1px solid rgba(255,235,59,.20); /* Amarelo */
  border-radius:var(--r10); padding:.65rem .95rem; margin:.45rem 0;
}
.str-ok  { background:rgba(76,175,80,.07); border:1px solid rgba(76,175,80,.18); border-radius:9px; padding:.36rem .72rem; font-size:.74rem; color:var(--gr2); margin-bottom:.28rem; } /* Verde */
.str-imp { background:rgba(255,235,59,.07); border:1px solid rgba(255,235,59,.18); border-radius:9px; padding:.36rem .72rem; font-size:.74rem; color:var(--am2); margin-bottom:.28rem; } /* Amarelo */
.ref-item { background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.15); border-radius:var(--r10); padding:.6rem .85rem; font-size:.76rem; color:var(--t2); line-height:1.6; }

/* ═══════════════════════════════════════
   TABS
═══════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
  background:rgba(8,8,8,.88) !important; /* Fundo escuro */
  border:1px solid var(--gb1) !important; border-radius:var(--r10) !important;
  padding:3px !important; gap:2px !important;
}
.stTabs [data-baseweb="tab"] {
  background:transparent !important; color:var(--t3) !important;
  border-radius:8px !important; font-size:.76rem !important;
  font-family:'Outfit',sans-serif !important; font-weight:500 !important;
}
.stTabs [aria-selected="true"] {
  background:linear-gradient(135deg,rgba(255,152,0,.25),rgba(255,235,59,.15)) !important; /* Laranja/Amarelo */
  color:var(--or1) !important; border:1px solid rgba(255,255,255,.2) !important;
  font-weight:700 !important;
}
.stTabs [data-baseweb="tab-panel"] { background:transparent !important; padding-top:.85rem !important; }

/* ═══════════════════════════════════════
   BADGES / TAGS
═══════════════════════════════════════ */
.tag {
  display:inline-block; background:rgba(255,255,255,.09);
  border:1px solid rgba(255,255,255,.18);
  border-radius:20px;
  padding:2px 8px; font-size:.62rem; color:var(--t1); margin:2px; font-weight:500;
}
.badge-on   { display:inline-block; background:rgba(255,235,59,.10); border:1px solid rgba(255,235,59,.22); border-radius:20px; padding:2px 8px; font-size:.62rem; font-weight:600; color:var(--am2); } /* Amarelo */
.badge-pub  { display:inline-block; background:rgba(76,175,80,.10); border:1px solid rgba(76,175,80,.22); border-radius:20px; padding:2px 8px; font-size:.62rem; font-weight:600; color:var(--gr2); } /* Verde */
.badge-done { display:inline-block; background:rgba(139,92,246,.10); border:1px solid rgba(139,92,246,.22); border-radius:20px; padding:2px 8px; font-size:.62rem; font-weight:600; color:#c4b5fd; }
.badge-rec  { display:inline-block; background:rgba(255,152,0,.10); border:1px solid rgba(255,152,0,.22); border-radius:20px; padding:2px 8px; font-size:.62rem; font-weight:600; color:var(--or1); } /* Laranja */

/* ═══════════════════════════════════════
   INDICATORS / MISC
═══════════════════════════════════════ */
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.5;transform:scale(.75)} }
.dot-on  { display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--gr1); animation:pulse 2.5s infinite; margin-right:4px; vertical-align:middle; } /* Verde */
.dot-off { display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--t4); margin-right:4px; vertical-align:middle; }

/* Removed prog-wrap and prog-fill as requested */

@keyframes fadeUp { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
.pw { animation:fadeIn .18s ease both; }
@keyframes fadeIn { from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:translateY(0)} }

/* Chat bubbles */
.bme   { background:linear-gradient(135deg,rgba(255,152,0,.25),rgba(255,235,59,.15)); border:1px solid rgba(255,255,255,.2); border-radius:18px 18px 4px 18px; padding:.56rem .88rem; max-width:68%; margin-left:auto; margin-bottom:5px; font-size:.82rem; line-height:1.6; } /* Laranja/Amarelo */
.bthem { background:var(--glass); border:1px solid var(--gb1); border-radius:18px 18px 18px 4px; padding:.56rem .88rem; max-width:68%; margin-bottom:5px; font-size:.82rem; line-height:1.6; }
.cmt   { background:rgba(8,8,8,.88); border:1px solid var(--gb1); border-radius:var(--r10); padding:.52rem .85rem; margin-bottom:.28rem; }

/* Profile hero */
.prof-hero {
  background:var(--glass); backdrop-filter:blur(30px) saturate(180%); -webkit-backdrop-filter:blur(30px) saturate(180%);
  border:1px solid var(--gb1); border-radius:var(--r24);
  padding:1.6rem; display:flex; gap:1.3rem; align-items:flex-start;
  box-shadow:0 5px 32px rgba(0,0,0,.40); position:relative; overflow:hidden; margin-bottom:1.1rem;
}
.prof-photo {
  width:80px; height:80px; border-radius:50%;
  background:linear-gradient(135deg,var(--or1),var(--am1));
  border:2px solid rgba(255,255,255,.15);
  flex-shrink:0; overflow:hidden;
  display:flex; align-items:center; justify-content:center;
  font-size:1.7rem; font-weight:700; color:white;
  box-shadow:0 4px 16px rgba(0,0,0,.4);
}
.prof-photo img { width:100%; height:100%; object-fit:cover; border-radius:50%; }

/* Person row */
.person-row {
  display:flex; align-items:center; gap:8px; padding:.42rem .48rem;
  border-radius:var(--r10); border:1px solid transparent; transition:all .14s; margin-bottom:2px;
}
.person-row:hover { background:rgba(255,255,255,.08); border-color:var(--gb1); }

/* Divider */
.dtxt {
  display:flex; align-items:center; gap:.7rem; margin:.8rem 0;
  font-size:.60rem; color:var(--t3); letter-spacing:.09em; text-transform:uppercase; font-weight:600;
}
.dtxt::before,.dtxt::after { content:''; flex:1; height:1px; background:var(--gb1); }

/* Misc */
hr { border:none; border-top:1px solid var(--gb1) !important; margin:.85rem 0; }
label { color:var(--t2) !important; }
.stCheckbox label,.stRadio label { color:var(--t1) !important; }
.stAlert { background:var(--glass) !important; border:1px solid var(--gb1) !important; border-radius:var(--r14) !important; }
.stSelectbox [data-baseweb="select"] { background:rgba(8,8,8,.88) !important; border:1px solid var(--gb1) !important; border-radius:var(--r10) !important; }
.stFileUploader section { background:rgba(8,8,8,.55) !important; border:1.5px dashed rgba(255,255,255,.18) !important; border-radius:var(--r14) !important; }
.stExpander { background:var(--glass); border:1px solid var(--gb1); border-radius:var(--r14); }
.stRadio > div { display:flex !important; gap:4px !important; flex-wrap:wrap !important; }
.stRadio > div > label { background:var(--glass) !important; border:1px solid var(--gb1) !important; border-radius:50px !important; padding:.28rem .78rem !important; font-size:.74rem !important; cursor:pointer !important; color:var(--t2) !important; }
.stRadio > div > label:hover { border-color:var(--gb2) !important; color:var(--t1) !important; }
input[type="number"] { background:rgba(8,8,8,.88) !important; border:1px solid var(--gb1) !important; border-radius:var(--r10) !important; color:var(--t1) !important; }
::-webkit-scrollbar { width:4px; height:4px; }
::-webkit-scrollbar-thumb { background:var(--s4); border-radius:4px; }
.js-plotly-plot .plotly .modebar { display:none !important; }
</style>""", unsafe_allow_html=True)

# ════════════════════════════════
# HTML HELPERS
# ════════════════════════════════
def avh(initials, sz=40, photo=None, grad=None):
    fs=max(sz//3,9); bg=grad or "linear-gradient(135deg,var(--or1),var(--am1))"
    if photo: return f'<div class="av" style="width:{sz}px;height:{sz}px;background:{bg}"><img src="{photo}"/></div>'
    return f'<div class="av" style="width:{sz}px;height:{sz}px;font-size:{fs}px;background:{bg}">{initials}</div>'

def tags_html(tags): return ' '.join(f'<span class="tag">{t}</span>' for t in (tags or []))

def badge(s):
    cls={"Publicado":"badge-pub","Concluído":"badge-done"}.get(s,"badge-on")
    return f'<span class="{cls}">{s}</span>'

# Removed prog_bar as requested

def pc():
    return dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="var(--t3)",family="Outfit",size=11), # Adjusted to t3
                margin=dict(l=10,r=10,t=40,b=10),
                xaxis=dict(showgrid=False,color="var(--t3)",tickfont=dict(size=10)),
                yaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,.05)",color="var(--t3)",tickfont=dict(size=10)))

CHART_COLORS = ["#FF9800","#FFEB3B","#4CAF50","#2196F3","#8b5cf6","#ec4899","#06b6d4","#fbbf24","#34d399","#60a5fa"] # Updated vibrant colors

# ════════════════════════════════
# AUTH PAGES
# ════════════════════════════════
def page_login():
    _,col,_ = st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-bottom:2.5rem">
          <div style="font-family:'Outfit',sans-serif;font-size:4rem;font-weight:900;
            background:linear-gradient(135deg,var(--or1) 15%,var(--am1) 55%,var(--gr1) 100%); /* Cores vibrantes */
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            background-clip:text;letter-spacing:-.06em;line-height:.9;margin-bottom:.7rem">Nebula</div>
          <div style="color:var(--t3);font-size:.62rem;letter-spacing:.26em;text-transform:uppercase;font-weight:600">
            Rede do Conhecimento Científico
          </div>
        </div>""", unsafe_allow_html=True)
        t_in,t_up = st.tabs(["  🔑 Entrar  ","  ✨ Criar conta  "])
        with t_in:
            with st.form("login_form"):
                email=st.text_input("E-mail",placeholder="seu@email.com",key="li_e")
                pw=st.text_input("Senha",placeholder="••••••••",type="password",key="li_p")
                st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
                submitted=st.form_submit_button("→  Entrar",use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                if submitted:
                    u=st.session_state.users.get(email)
                    if not u: st.error("E-mail não encontrado.")
                    elif u["password"]!=hp(pw): st.error("Senha incorreta.")
                    elif u.get("2fa_enabled"):
                        c=code6(); st.session_state.pending_2fa={"email":email,"code":c}
                        st.session_state.page="2fa"; st.rerun()
                    else:
                        st.session_state.logged_in=True; st.session_state.current_user=email
                        record(area_to_tags(u.get("area","")),1.0)
                        st.session_state.page="feed"; st.rerun()
            st.markdown('<div style="text-align:center;color:var(--t3);font-size:.69rem;margin-top:.7rem">Demo: demo@nebula.ai / demo123</div>', unsafe_allow_html=True)
        with t_up:
            with st.form("signup_form"):
                n_name=st.text_input("Nome completo",key="su_n")
                n_email=st.text_input("E-mail",key="su_e")
                n_area=st.text_input("Área de pesquisa",key="su_a")
                n_pw=st.text_input("Senha",type="password",key="su_p")
                n_pw2=st.text_input("Confirmar senha",type="password",key="su_p2")
                st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
                sub2=st.form_submit_button("✓  Criar conta",use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                if sub2:
                    if not all([n_name,n_email,n_area,n_pw,n_pw2]): st.error("Preencha todos os campos.")
                    elif n_pw!=n_pw2: st.error("Senhas não coincidem.")
                    elif len(n_pw)<6: st.error("Mínimo 6 caracteres.")
                    elif n_email in st.session_state.users: st.error("E-mail já cadastrado.")
                    else:
                        c=code6(); st.session_state.pending_verify={"email":n_email,"name":n_name,"pw":hp(n_pw),"area":n_area,"code":c}
                        st.session_state.page="verify_email"; st.rerun()

def page_verify_email():
    pv=st.session_state.pending_verify
    _,col,_ = st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card" style="padding:2rem;text-align:center">
          <div style="font-size:2rem;margin-bottom:.8rem;opacity:.5">✉</div>
          <h2 style="margin-bottom:.4rem">Verifique seu e-mail</h2>
          <p style="color:var(--t2);font-size:.82rem">Código para <strong style="color:var(--or1)">{pv['email']}</strong></p>
          <div style="background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.18);border-radius:12px;padding:1rem;margin:1rem 0">
            <div style="font-size:.59rem;color:var(--t3);letter-spacing:.12em;text-transform:uppercase;margin-bottom:5px;font-weight:600">Código (demo)</div>
            <div style="font-family:'Outfit',sans-serif;font-size:2.6rem;font-weight:900;letter-spacing:.28em;color:var(--or1)">{pv['code']}</div>
          </div>
        </div>""", unsafe_allow_html=True)
        with st.form("verify_form"):
            typed=st.text_input("Código",max_chars=6,key="ev_c")
            st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
            sub=st.form_submit_button("✓  Verificar",use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if sub:
                if typed.strip()==pv["code"]:
                    st.session_state.users[pv["email"]]={"name":pv["name"],"password":pv["pw"],"bio":"","area":pv["area"],"followers":0,"following":0,"verified":True,"2fa_enabled":False,"photo_b64":None}
                    save_db(); st.session_state.pending_verify=None
                    st.session_state.logged_in=True; st.session_state.current_user=pv["email"]
                    record(area_to_tags(pv["area"]),2.0); st.session_state.page="feed"; st.rerun()
                else: st.error("Código inválido.")
        if st.button("← Voltar",key="btn_ev_bk"): st.session_state.page="login"; st.rerun()

def page_2fa():
    p2=st.session_state.pending_2fa
    _,col,_ = st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="card" style="padding:2rem;text-align:center">
          <div style="font-size:2rem;margin-bottom:.8rem;opacity:.5">🔑</div>
          <h2 style="margin-bottom:.4rem">Verificação 2FA</h2>
          <div style="background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.18);border-radius:12px;padding:.9rem;margin:1rem 0">
            <div style="font-size:.59rem;color:var(--t3);text-transform:uppercase;letter-spacing:.10em;margin-bottom:5px;font-weight:600">Código</div>
            <div style="font-family:'Outfit',sans-serif;font-size:2.6rem;font-weight:900;letter-spacing:.26em;color:var(--or1)">{p2['code']}</div>
          </div>
        </div>""", unsafe_allow_html=True)
        with st.form("twofa_form"):
            typed=st.text_input("Código",max_chars=6,key="fa_c",label_visibility="collapsed")
            st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
            sub=st.form_submit_button("✓  Verificar",use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if sub:
                if typed.strip()==p2["code"]:
                    st.session_state.logged_in=True; st.session_state.current_user=p2["email"]
                    st.session_state.pending_2fa=None; st.session_state.page="feed"; st.rerun()
                else: st.error("Código inválido.")
        if st.button("← Voltar",key="btn_fa_bk"): st.session_state.page="login"; st.rerun()

# ════════════════════════════════
# TOP NAV — compact, icon-only pills
# ════════════════════════════════
NAV = [
    ("feed","🏠"), # Feed (now the default page, but still listed for clarity)
    ("search","🔍"), # Artigos
    ("knowledge","🕸"), # Conexões
    ("folders","📁"), # Pastas
    ("analytics","📊"), # Análises
    ("img_search","🔬"), # Imagem
    ("chat","💬"), # Chat
]

def render_topnav():
    u=guser(); name=u.get("name","?"); photo=u.get("photo_b64")
    in_=ini(name); cur=st.session_state.page
    email=st.session_state.current_user; g=ugrad(email or "")
    notif=len(st.session_state.notifications)
    st.markdown('<div class="neb-navwrap">', unsafe_allow_html=True)
    # Adjust column widths based on number of nav items
    num_nav_items = len(NAV) - 1 # Exclude 'feed' from explicit buttons
    cols=st.columns([.9] + [.65]*num_nav_items + [.5])

    with cols[0]:
        st.markdown('<div class="nav-logo">', unsafe_allow_html=True)
        if st.button("🔬 Nebula",key="nav_logo"):
            st.session_state.profile_view=None; st.session_state.page="feed"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    nav_col_idx = 1
    for i,(key,label) in enumerate(NAV):
        # Skip 'feed' button as logo now handles it
        if key == "feed": continue

        with cols[nav_col_idx]:
            active=(cur==key)
            cls="nav-pill-active" if active else "nav-pill"
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if st.button(label,key=f"tnav_{key}",use_container_width=True):
                st.session_state.profile_view=None; st.session_state.page=key; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        nav_col_idx += 1

    with cols[nav_col_idx]: # This is the last column for the avatar
        nb=""
        if notif: nb=f'<div style="position:absolute;top:-1px;right:-1px;background:var(--err);color:white;width:13px;height:13px;border-radius:50%;font-size:.46rem;display:flex;align-items:center;justify-content:center;font-weight:700;z-index:10;pointer-events:none">{notif}</div>'
        st.markdown(f'<div style="position:relative;display:inline-block">{nb}</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-av">', unsafe_allow_html=True)

        # Dynamic CSS for avatar button background-image
        if photo:
            st.markdown(f"""
                <style>
                    /* Target the specific button by its key or parent structure */
                    div[data-testid="stHorizontalBlock"] > div:nth-child({num_nav_items + 2}) .nav-av .stButton > button {{ /* +2 because of logo col and 0-indexing */
                        background-image: url("{photo}") !important;
                        background-size: cover !important;
                        background-position: center !important;
                        color: transparent !important; /* Hide initials */
                        font-size: 0 !important; /* Ensure initials are not visible */
                    }}
                </style>
            """, unsafe_allow_html=True)
            btn_label=" " # Empty label if photo is present
        else:
            st.markdown(f"""
                <style>
                    div[data-testid="stHorizontalBlock"] > div:nth-child({num_nav_items + 2}) .nav-av .stButton > button {{
                        background: {g} !important;
                    }}
                </style>
            """, unsafe_allow_html=True)
            btn_label=in_

        if st.button(btn_label,key="nav_me"):
            st.session_state.profile_view=email; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════
# PROFILE + SETTINGS (merged)
# ════════════════════════════════
def page_profile(target_email):
    tu=st.session_state.users.get(target_email,{})
    if not tu:
        st.error("Perfil não encontrado.")
        return
    tname=tu.get("name","?"); tin=ini(tname); tphoto=tu.get("photo_b64")
    email=st.session_state.current_user; is_me=(email==target_email)
    is_fol=target_email in st.session_state.followed
    user_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==target_email]
    liked_posts=[p for p in st.session_state.feed_posts if target_email in p.get("liked_by",[])]
    total_likes=sum(p["likes"] for p in user_posts); g=ugrad(target_email)

    photo_html=f'<img src="{tphoto}"/>' if tphoto else f'<span style="font-size:1.85rem;font-family:Outfit,sans-serif">{tin}</span>'
    v_badge=' <span style="font-size:.68rem;color:var(--gr1);margin-left:5px">✓</span>' if tu.get("verified") else ""
    st.markdown(f"""
    <div class="prof-hero">
      <div class="prof-photo" style="background:{g}">{photo_html}</div>
      <div style="flex:1;z-index:1">
        <div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;margin-bottom:.25rem">
          <h1 style="margin:0">{tname}</h1>{v_badge}
        </div>
        <div style="color:var(--or1);font-size:.82rem;margin-bottom:.4rem;font-weight:600">{tu.get("area","")}</div>
        <div style="color:var(--t2);font-size:.80rem;line-height:1.65;margin-bottom:.85rem;max-width:540px">{tu.get("bio","Sem biografia.")}</div>
        <div style="display:flex;gap:1.8rem;flex-wrap:wrap">
          <div><span style="font-family:Outfit,sans-serif;font-weight:800;font-size:1.05rem">{tu.get("followers",0)}</span><span style="color:var(--t3);font-size:.70rem"> seguidores</span></div>
          <div><span style="font-family:Outfit,sans-serif;font-weight:800;font-size:1.05rem">{tu.get("following",0)}</span><span style="color:var(--t3);font-size:.70rem"> seguindo</span></div>
          <div><span style="font-family:Outfit,sans-serif;font-weight:800;font-size:1.05rem">{len(user_posts)}</span><span style="color:var(--t3);font-size:.70rem"> pesquisas</span></div>
          <div><span style="font-family:Outfit,sans-serif;font-weight:800;font-size:1.05rem">{fmt_num(total_likes)}</span><span style="color:var(--t3);font-size:.70rem"> curtidas</span></div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    if not is_me:
        c1,c2,_=st.columns([1,1,3])
        with c1:
            if st.button("✓ Seguindo" if is_fol else "+ Seguir",key="pf_fol",use_container_width=True):
                if is_fol: st.session_state.followed.remove(target_email); tu["followers"]=max(0,tu.get("followers",0)-1)
                else: st.session_state.followed.append(target_email); tu["followers"]=tu.get("followers",0)+1
                save_db(); st.rerun()
        with c2:
            if st.button("💬 Mensagem",key="pf_chat",use_container_width=True):
                if target_email not in st.session_state.chat_messages: st.session_state.chat_messages[target_email]=[]
                st.session_state.active_chat=target_email; st.session_state.page="chat"; st.rerun()
        # Tabs for other user: posts + liked
        tab_posts,tab_liked=st.tabs([f"  📝 Pesquisas ({len(user_posts)})  ",f"  ❤️ Curtidas ({len(liked_posts)})  "])
        with tab_posts:
            if user_posts:
                for p in sorted(user_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="profile",show_author=False)
            else: st.markdown('<div class="card" style="padding:2rem;text-align:center;color:var(--t3)">Nenhuma pesquisa publicada.</div>', unsafe_allow_html=True)
        with tab_liked:
            if liked_posts:
                for p in sorted(liked_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="prof_liked",compact=True)
            else: st.markdown('<div class="card" style="padding:2rem;text-align:center;color:var(--t3)">Nenhuma curtida.</div>', unsafe_allow_html=True)
    else:
        # MY PROFILE — merged with settings
        d=st.session_state.stats_data
        tab_my_data,tab_activity,tab_security=st.tabs([
            "  ✏️ Meus Dados  ",
            f"  ✨ Atividade ({len(user_posts) + len(liked_posts) + len(st.session_state.saved_articles)})  ",
            "  🔐 Segurança  ",
        ])
        with tab_my_data:
            st.markdown('<h3 style="margin-bottom:.9rem">Informações do Perfil</h3>', unsafe_allow_html=True)
            ph=st.file_uploader("📷 Foto de perfil",type=["png","jpg","jpeg","webp"],key="ph_up")
            if ph:
                b64=img_to_b64(ph)
                if b64: st.session_state.users[email]["photo_b64"]=b64; save_db(); st.success("✓ Foto atualizada!"); st.rerun()
            if tphoto:
                st.image(tphoto, width=100, caption="Sua foto atual", use_column_width=False)
                if st.button("Remover foto", key="remove_photo"):
                    st.session_state.users[email]["photo_b64"] = None
                    save_db()
                    st.success("Foto removida!")
                    st.rerun()

            new_n=st.text_input("Nome completo",value=tu.get("name",""),key="cfg_n")
            new_a=st.text_input("Área de pesquisa",value=tu.get("area",""),key="cfg_a")
            new_b=st.text_area("Biografia",value=tu.get("bio",""),key="cfg_b",height=88)
            c_save,c_out=st.columns(2)
            with c_save:
                st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
                if st.button("💾 Salvar Dados",key="btn_sp",use_container_width=True):
                    st.session_state.users[email]["name"]=new_n
                    st.session_state.users[email]["area"]=new_a
                    st.session_state.users[email]["bio"]=new_b
                    save_db(); record(area_to_tags(new_a),1.5); st.success("✓ Perfil salvo!"); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with c_out:
                st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                if st.button("🚪 Sair",key="btn_logout",use_container_width=True):
                    st.session_state.logged_in=False; st.session_state.current_user=None; st.session_state.page="login"; st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("<hr>", unsafe_allow_html=True)
            # Quick stats
            st.markdown('<h3 style="margin-bottom:.9rem">Minhas Métricas</h3>', unsafe_allow_html=True)
            c1,c2,c3=st.columns(3)
            with c1: st.markdown(f'<div class="mbox"><div class="mval">{d.get("h_index",4)}</div><div class="mlbl">Índice H</div></div>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="mbox"><div class="mval">{d.get("fator_impacto",3.8):.1f}</div><div class="mlbl">Fator Impacto</div></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="mbox"><div class="mval-green">{sum(p["likes"] for p in user_posts)}</div><div class="mlbl">Curtidas Totais</div></div>', unsafe_allow_html=True)
            new_h=st.number_input("Índice H",0,200,d.get("h_index",4),key="e_h")
            new_fi=st.number_input("Fator de impacto",0.0,100.0,float(d.get("fator_impacto",3.8)),step=0.1,key="e_fi")
            if st.button("💾 Salvar Métricas",key="btn_save_m"):
                d.update({"h_index":new_h,"fator_impacto":new_fi}); st.success("✓ Salvo!")
        with tab_activity:
            st.markdown('<h3 style="margin-bottom:.9rem">Minhas Publicações</h3>', unsafe_allow_html=True)
            if user_posts:
                for p in sorted(user_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="myprof",show_author=False)
            else: st.markdown('<div class="card" style="padding:2rem;text-align:center;color:var(--t3)">Nenhuma pesquisa publicada.</div>', unsafe_allow_html=True)
            st.markdown('<hr>', unsafe_allow_html=True)
            st.markdown('<h3 style="margin-bottom:.9rem">Minhas Curtidas</h3>', unsafe_allow_html=True)
            if liked_posts:
                for p in sorted(liked_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="mylk",compact=True)
            else: st.markdown('<div class="card" style="padding:2rem;text-align:center;color:var(--t3)">Nenhuma curtida.</div>', unsafe_allow_html=True)
            st.markdown('<hr>', unsafe_allow_html=True)
            st.markdown('<h3 style="margin-bottom:.9rem">Meus Artigos Salvos</h3>', unsafe_allow_html=True)
            if st.session_state.saved_articles:
                for idx,a in enumerate(st.session_state.saved_articles):
                    render_web_article(a,idx=idx+3000,ctx="saved")
                    uid=re.sub(r'[^a-zA-Z0-9]','',f"rm_{a.get('doi','nd')}_{idx}")[:30]
                    st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                    if st.button("🗑 Remover",key=f"rms_{uid}"):
                        st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]
                        save_db(); st.toast("Removido!"); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="card" style="padding:2.5rem;text-align:center;color:var(--t3)">Nenhum artigo salvo.</div>', unsafe_allow_html=True)
        with tab_security:
            st.markdown('<h3 style="margin-bottom:.9rem">🔑 Alterar senha</h3>', unsafe_allow_html=True)
            with st.form("change_pw_form"):
                op=st.text_input("Senha atual",type="password",key="op")
                np_=st.text_input("Nova senha",type="password",key="np_")
                np2=st.text_input("Confirmar",type="password",key="np2")
                if st.form_submit_button("🔑 Alterar Senha"):
                    if hp(op)!=tu.get("password",""): st.error("Senha atual incorreta.")
                    elif np_!=np2: st.error("Não coincidem.")
                    elif len(np_)<6: st.error("Mínimo 6 caracteres.")
                    else: st.session_state.users[email]["password"]=hp(np_); save_db(); st.success("✓ Alterada!")
            st.markdown("<hr>", unsafe_allow_html=True)
            en=tu.get("2fa_enabled",False)
            st.markdown(f'<div class="card" style="padding:.9rem 1.2rem;display:flex;align-items:center;justify-content:space-between;margin-bottom:.9rem"><div><div style="font-weight:700;font-size:.87rem">🔐 2FA — {"<span style=\'color:var(--gr1)\'>Ativo</span>" if en else "<span style=\'color:var(--err)\'>Inativo</span>"}</div><div style="font-size:.69rem;color:var(--t3)">{email}</div></div></div>', unsafe_allow_html=True)
            if st.button("✕ Desativar 2FA" if en else "✓ Ativar 2FA",key="btn_2fa"):
                st.session_state.users[email]["2fa_enabled"]=not en; save_db(); st.rerun()
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown('<h3 style="margin-bottom:.9rem">Protocolos de Segurança</h3>', unsafe_allow_html=True)
            prots=[("🔒 AES-256","Criptografia end-to-end"),("🔏 SHA-256","Hash de senhas"),("🛡 TLS 1.3","Transmissão segura")]
            for n2,d2 in prots:
                st.markdown(f'<div style="display:flex;align-items:center;gap:10px;background:rgba(76,175,80,.05);border:1px solid rgba(76,175,80,.13);border-radius:10px;padding:10px;margin-bottom:7px"><div style="width:26px;height:26px;border-radius:7px;background:rgba(76,175,80,.10);display:flex;align-items:center;justify-content:center;color:var(--gr1);font-size:.75rem;flex-shrink:0">✓</div><div><div style="font-weight:600;color:var(--gr1);font-size:.80rem">{n2}</div><div style="font-size:.68rem;color:var(--t3)">{d2}</div></div></div>', unsafe_allow_html=True)

# ════════════════════════════════
# POST CARD
# ════════════════════════════════
def render_post(post, ctx="feed", show_author=True, compact=False):
    email=st.session_state.current_user; pid=post["id"]
    liked=email in post.get("liked_by",[]); saved=email in post.get("saved_by",[])
    aemail=post.get("author_email",""); aphoto=get_photo(aemail)
    ain=post.get("avatar","??"); aname=post.get("author","?"); aarea=post.get("area","")
    dt=time_ago(post.get("date","")); views=post.get("views",200)
    abstract=post.get("abstract","")
    if compact and len(abstract)>200: abstract=abstract[:200]+"…"
    g=ugrad(aemail)
    if show_author:
        av_html=(f'<div class="av" style="width:40px;height:40px;background:{g};font-size:12px"><img src="{aphoto}"/></div>'
                 if aphoto else f'<div class="av" style="width:40px;height:40px;background:{g};font-size:12px">{ain}</div>')
        v_mark=' <span style="font-size:.58rem;color:var(--gr1)">✓</span>' if st.session_state.users.get(aemail,{}).get("verified") else ""
        header=(f'<div style="padding:.85rem 1.15rem .6rem;display:flex;align-items:center;gap:9px;border-bottom:1px solid rgba(255,255,255,.06)">'
                f'{av_html}'
                f'<div style="flex:1;min-width:0">'
                f'<div style="font-family:Outfit,sans-serif;font-weight:700;font-size:.86rem">{aname}{v_mark}</div>'
                f'<div style="color:var(--t3);font-size:.65rem;margin-top:1px">{aarea} · {dt}</div>'
                f'</div>{badge(post["status"])}</div>')
    else:
        header=(f'<div style="padding:.4rem 1.15rem .2rem;display:flex;justify-content:space-between;align-items:center">'
                f'<span style="color:var(--t3);font-size:.65rem">{dt}</span>{badge(post["status"])}</div>')
    st.markdown(
        f'<div class="post">{header}'
        f'<div style="padding:.7rem 1.15rem">'
        f'<div style="font-family:Outfit,sans-serif;font-size:.95rem;font-weight:700;margin-bottom:.35rem;line-height:1.4;color:var(--t0)">{post["title"]}</div>'
        f'<div style="color:var(--t2);font-size:.80rem;line-height:1.65;margin-bottom:.55rem">{abstract}</div>'
        f'<div>{tags_html(post.get("tags",[]))}</div>'
        f'</div></div>', unsafe_allow_html=True)
    heart="❤️" if liked else "🤍"; book="🔖" if saved else "📌"
    nc=len(post.get("comments",[]))
    ca,cb,cc,cd,ce,cf=st.columns([1.1,1,.7,.6,1,1.1])
    with ca:
        if st.button(f"{heart} {fmt_num(post['likes'])}",key=f"lk_{ctx}_{pid}",use_container_width=True):
            if liked: post["liked_by"].remove(email); post["likes"]=max(0,post["likes"]-1)
            else: post["liked_by"].append(email); post["likes"]+=1; record(post.get("tags",[]),1.5)
            save_db(); st.rerun()
    with cb:
        if st.button(f"💬 {nc}" if nc else "💬",key=f"cm_{ctx}_{pid}",use_container_width=True):
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
        st.markdown(f'<div style="text-align:center;color:var(--t3);font-size:.69rem;padding:.48rem 0">👁 {fmt_num(views)}</div>', unsafe_allow_html=True)
    with cf:
        if show_author and aemail:
            if st.button(f"👤 {aname.split()[0]}",key=f"vp_{ctx}_{pid}",use_container_width=True):
                st.session_state.profile_view=aemail; st.rerun()
    if st.session_state.get(f"shr_{ctx}_{pid}",False):
        url=f"https://nebula.ai/post/{pid}"; te=post['title'][:50].replace(" ","%20")
        st.markdown(
            f'<div class="card" style="padding:.85rem 1.15rem;margin-bottom:.48rem">'
            f'<div style="font-family:Outfit,sans-serif;font-weight:600;font-size:.80rem;margin-bottom:.6rem;color:var(--t2)">↗ Compartilhar</div>'
            f'<div style="display:flex;gap:.45rem;flex-wrap:wrap">'
            f'<a href="https://twitter.com/intent/tweet?text={te}" target="_blank" style="text-decoration:none"><div style="background:rgba(29,161,242,.08);border:1px solid rgba(29,161,242,.16);border-radius:8px;padding:.32rem .65rem;font-size:.70rem;color:#1da1f2">𝕏 Twitter</div></a>'
            f'<a href="https://linkedin.com/sharing/share-offsite/?url={url}" target="_blank" style="text-decoration:none"><div style="background:rgba(10,102,194,.08);border:1px solid rgba(10,102,194,.16);border-radius:8px;padding:.32rem .65rem;font-size:.70rem;color:#0a66c2">in LinkedIn</div></a>'
            f'<a href="https://wa.me/?text={te}%20{url}" target="_blank" style="text-decoration:none"><div style="background:rgba(37,211,102,.07);border:1px solid rgba(37,211,102,.14);border-radius:8px;padding:.32rem .65rem;font-size:.70rem;color:#25d366">📱 WhatsApp</div></a>'
            f'</div></div>', unsafe_allow_html=True)
    if st.session_state.get(f"cmt_{ctx}_{pid}",False):
        comments=post.get("comments",[])
        for c in comments:
            c_in=ini(c["user"]); c_email=next((e for e,u in st.session_state.users.items() if u.get("name")==c["user"]),"")
            c_photo=get_photo(c_email); c_grad=ugrad(c_email)
            st.markdown(f'<div class="cmt"><div><div style="display:flex;align-items:center;gap:7px;margin-bottom:.22rem">{avh(c_in,26,c_photo,c_grad)}<span style="font-size:.74rem;font-weight:600;color:var(--or1)">{c["user"]}</span></div><div style="font-size:.78rem;color:var(--t2);line-height:1.55;padding-left:33px">{c["text"]}</div></div></div>', unsafe_allow_html=True)
        nc_txt=st.text_input("",placeholder="Escreva um comentário…",key=f"ci_{ctx}_{pid}",label_visibility="collapsed")
        if st.button("→ Enviar",key=f"cs_{ctx}_{pid}"):
            if nc_txt:
                uu=guser(); post["comments"].append({"user":uu.get("name","Você"),"text":nc_txt})
                record(post.get("tags",[]),.8); save_db(); st.rerun()

# ════════════════════════════════
# FEED — no stories row
# ════════════════════════════════
def page_feed():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    email=st.session_state.current_user; u=guser()
    uname=u.get("name","?"); uphoto=u.get("photo_b64"); uin=ini(uname)
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    compose_open=st.session_state.get("compose_open",False)
    col_main,col_side=st.columns([2,.9],gap="medium")
    with col_main:
        # Compose area
        g=ugrad(email)
        if compose_open:
            av_c=(f'<div class="av" style="width:42px;height:42px;background:{g}"><img src="{uphoto}"/></div>'
                  if uphoto else f'<div class="av" style="width:42px;height:42px;font-size:13px;background:{g}">{uin}</div>')
            st.markdown(f'<div class="compose-card"><div style="display:flex;align-items:center;gap:9px;margin-bottom:.95rem">{av_c}<div><div style="font-family:Outfit,sans-serif;font-weight:700;font-size:.90rem">{uname}</div><div style="font-size:.67rem;color:var(--t3)">{u.get("area","Pesquisador")}</div></div></div>', unsafe_allow_html=True)
            np_t=st.text_input("Título *",key="np_t",placeholder="Ex: Efeitos da meditação na neuroplasticidade…")
            np_ab=st.text_area("Resumo / Abstract *",key="np_ab",height=108,placeholder="Descreva sua pesquisa…")
            c1c,c2c=st.columns(2)
            with c1c: np_tg=st.text_input("Tags (vírgula)",key="np_tg",placeholder="neurociência, fMRI")
            with c2c: np_st=st.selectbox("Status",["Em andamento","Publicado","Concluído"],key="np_st")
            cpub,ccan=st.columns([2,1])
            with cpub:
                st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
                if st.button("🚀 Publicar",key="btn_pub",use_container_width=True):
                    if not np_t or not np_ab: st.warning("Título e resumo obrigatórios.")
                    else:
                        tags=[t.strip() for t in np_tg.split(",") if t.strip()] if np_tg else []
                        new_p={"id":len(st.session_state.feed_posts)+200+hash(np_t)%99,
                               "author":uname,"author_email":email,"avatar":uin,"area":u.get("area",""),
                               "title":np_t,"abstract":np_ab,"tags":tags,"likes":0,"comments":[],
                               "status":np_st,"date":datetime.now().strftime("%Y-%m-%d"),
                               "liked_by":[],"saved_by":[],"connections":tags[:3],"views":1}
                        st.session_state.feed_posts.insert(0,new_p)
                        record(tags,2.0); save_db(); st.session_state.compose_open=False; st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with ccan:
                if st.button("✕ Cancelar",key="btn_cancel",use_container_width=True):
                    st.session_state.compose_open=False; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            av_c2=(f'<div class="av" style="width:38px;height:38px;flex-shrink:0;background:{g}"><img src="{uphoto}"/></div>'
                   if uphoto else f'<div class="av" style="width:38px;height:38px;font-size:12px;flex-shrink:0;background:{g}">{uin}</div>')
            avc,btnc=st.columns([.05,1],gap="small")
            with avc: st.markdown(f'<div style="padding-top:6px">{av_c2}</div>', unsafe_allow_html=True)
            with btnc:
                st.markdown('<div class="compose-prompt">', unsafe_allow_html=True)
                if st.button(f"No que você está pesquisando, {uname.split()[0]}?",key="open_compose",use_container_width=True):
                    st.session_state.compose_open=True; st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # Feed filter
        ff=st.radio("",["🌐 Todos","👥 Seguidos","🔖 Salvos","🔥 Populares"],
                    horizontal=True,key="ff",label_visibility="collapsed")
        # Recommendations
        recs=get_recs(email,2, st.session_state.feed_posts) # Pass feed_posts_data
        if recs and "Seguidos" not in ff and "Salvos" not in ff:
            st.markdown('<div class="dtxt"><span class="badge-rec">✨ Recomendado</span></div>', unsafe_allow_html=True)
            for p in recs: render_post(p,ctx="rec",compact=True)
            st.markdown('<div class="dtxt">Mais pesquisas</div>', unsafe_allow_html=True)
        posts=list(st.session_state.feed_posts)
        if "Seguidos" in ff: posts=[p for p in posts if p.get("author_email") in st.session_state.followed]
        elif "Salvos" in ff: posts=[p for p in posts if email in p.get("saved_by",[])]
        elif "Populares" in ff: posts=sorted(posts,key=lambda p:p["likes"],reverse=True)
        else: posts=sorted(posts,key=lambda p:p.get("date",""),reverse=True)
        if not posts:
            st.markdown('<div class="card" style="padding:3rem;text-align:center"><div style="font-size:2rem;opacity:.2;margin-bottom:.8rem">🔬</div><div style="color:var(--t3)">Nenhuma pesquisa aqui ainda.</div></div>', unsafe_allow_html=True)
        else:
            for p in posts: render_post(p,ctx="feed")

    with col_side:
        # Search people
        sq=st.text_input("",placeholder="🔍 Buscar pesquisadores…",key="ppl_s",label_visibility="collapsed")
        st.markdown('<div class="sc">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:Outfit,sans-serif;font-weight:700;font-size:.82rem;margin-bottom:.85rem;display:flex;justify-content:space-between"><span>Quem seguir</span><span style="font-size:.64rem;color:var(--t3);font-weight:400">Sugestões</span></div>', unsafe_allow_html=True)
        shown_n=0
        for ue,ud in list(users.items()):
            if ue==email or shown_n>=5: continue
            rname=ud.get("name","?")
            if sq and sq.lower() not in rname.lower() and sq.lower() not in ud.get("area","").lower(): continue
            shown_n+=1; is_fol=ue in st.session_state.followed
            uphoto_r=ud.get("photo_b64"); uin_r=ini(rname); rg=ugrad(ue)
            online=is_online(ue)
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            av_r=avh(uin_r,32,uphoto_r,rg)
            st.markdown(f'<div class="person-row">{av_r}<div style="flex:1;min-width:0"><div style="font-size:.78rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{dot}{rname}</div><div style="font-size:.62rem;color:var(--t3)">{ud.get("area","")[:22]}</div></div></div>', unsafe_allow_html=True)
            cf_b,cv_b=st.columns(2)
            with cf_b:
                if st.button("✓ Seg." if is_fol else "+ Seguir",key=f"sf_{ue}",use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"]=max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                    save_db(); st.rerun()
            with cv_b:
                if st.button("👤 Perfil",key=f"svr_{ue}",use_container_width=True):
                    st.session_state.profile_view=ue; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        # Trending
        st.markdown('<div class="sc">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:Outfit,sans-serif;font-weight:700;font-size:.82rem;margin-bottom:.82rem">🔥 Em Alta</div>', unsafe_allow_html=True)
        trending=[("Quantum ML","34"),("CRISPR 2026","28"),("Neuroplasticidade","22"),("LLMs Científicos","19"),("Matéria Escura","15")]
        for i,(topic,cnt) in enumerate(trending):
            color=CHART_COLORS[i]
            st.markdown(f'<div style="padding:.38rem .32rem;border-radius:9px;margin-bottom:2px"><div><div style="font-size:.59rem;color:var(--t3);margin-bottom:1px">#{i+1}</div><div style="font-size:.78rem;font-weight:600;color:var(--t0)">{topic}</div><div style="font-size:.59rem;color:var(--t3)">{cnt} pesquisas</div></div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        # Notifications
        if st.session_state.notifications:
            st.markdown('<div class="sc">', unsafe_allow_html=True)
            st.markdown('<div style="font-family:Outfit,sans-serif;font-weight:700;font-size:.82rem;margin-bottom:.72rem">🔔 Atividade</div>', unsafe_allow_html=True)
            for notif in st.session_state.notifications[:3]:
                st.markdown(f'<div style="font-size:.71rem;color:var(--t2);padding:.32rem 0;border-bottom:1px solid var(--gb1)">· {notif}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════
# SEARCH
# ════════════════════════════════
def render_web_article(a, idx=0, ctx="web"):
    src_color="var(--gr1)" if a.get("origin")=="semantic" else "var(--am1)"
    src_name="Semantic Scholar" if a.get("origin")=="semantic" else "CrossRef"
    cite=f" · {a['citations']} cit." if a.get("citations") else ""
    uid=re.sub(r'[^a-zA-Z0-9]','',f"{ctx}_{idx}_{str(a.get('doi',''))[:10]}")[:32]
    is_saved=any(s.get('doi')==a.get('doi') for s in st.session_state.saved_articles)
    abstract=(a.get("abstract","") or "")[:260]
    if len(a.get("abstract",""))>260: abstract+="…"
    st.markdown(f'<div class="scard"><div style="display:flex;align-items:flex-start;gap:7px;margin-bottom:.32rem"><div style="flex:1;font-family:Outfit,sans-serif;font-size:.88rem;font-weight:700">{a["title"]}</div><span style="font-size:.60rem;color:{src_color};background:rgba(255,255,255,.05);border-radius:7px;padding:2px 7px;white-space:nowrap;flex-shrink:0">{src_name}</span></div><div style="color:var(--t3);font-size:.66rem;margin-bottom:.35rem">{a["authors"]} · <em>{a["source"]}</em> · {a["year"]}{cite}</div><div style="color:var(--t2);font-size:.78rem;line-height:1.62">{abstract}</div></div>', unsafe_allow_html=True)
    ca,cb,cc=st.columns(3)
    with ca:
        if st.button("🔖 Salvo" if is_saved else "📌 Salvar",key=f"svw_{uid}"):
            if is_saved: st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]; st.toast("Removido")
            else: st.session_state.saved_articles.append(a); st.toast("Salvo!")
            save_db(); st.rerun()
    with cb:
        if st.button("📋 Citar",key=f"ctw_{uid}"): st.toast(f'{a["authors"]} ({a["year"]}). {a["title"]}.')
    with cc:
        if a.get("url"):
            st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:var(--or1);font-size:.78rem;text-decoration:none;line-height:2.4;display:block">↗ Abrir artigo</a>', unsafe_allow_html=True)

def page_search():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.35rem">🔍 Busca Acadêmica</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.78rem;margin-bottom:.9rem">Semantic Scholar · CrossRef · Nebula</p>', unsafe_allow_html=True)
    c1,c2=st.columns([4,1])
    with c1: q=st.text_input("",placeholder="CRISPR · quantum ML · dark matter · neuroplasticidade…",key="sq",label_visibility="collapsed")
    with c2:
        st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
        if st.button("🔍 Buscar",use_container_width=True,key="btn_s"):
            if q:
                with st.spinner("Buscando…"):
                    nebula_r=[p for p in st.session_state.feed_posts if q.lower() in p["title"].lower() or q.lower() in p["abstract"].lower() or any(q.lower() in t.lower() for t in p.get("tags",[]))]
                    ss_r=search_ss(q,6); cr_r=search_cr(q,4)
                    st.session_state.search_results={"nebula":nebula_r,"ss":ss_r,"cr":cr_r}
                    st.session_state.last_sq=q; record([q.lower()],.3)
        st.markdown('</div>', unsafe_allow_html=True)
    if st.session_state.get("search_results") and st.session_state.get("last_sq"):
        res=st.session_state.search_results
        neb=res.get("nebula",[]); ss=res.get("ss",[]); cr=res.get("cr",[])
        web=ss+[x for x in cr if not any(x["title"].lower()==s["title"].lower() for s in ss)]
        t_all,t_neb,t_web=st.tabs([f"  Todos ({len(neb)+len(web)})  ",f"  🔬 Nebula ({len(neb)})  ",f"  🌐 Internet ({len(web)})  "])
        with t_all:
            if neb:
                st.markdown('<div style="font-size:.61rem;color:var(--or1);font-weight:700;margin-bottom:.45rem;letter-spacing:.09em;text-transform:uppercase">Na Nebula</div>', unsafe_allow_html=True)
                for p in neb: render_post(p,ctx="srch_all",compact=True)
            if web:
                if neb: st.markdown('<hr>', unsafe_allow_html=True)
                st.markdown('<div style="font-size:.61rem;color:var(--gr1);font-weight:700;margin-bottom:.45rem;letter-spacing:.09em;text-transform:uppercase">Bases Acadêmicas</div>', unsafe_allow_html=True)
                for idx,a in enumerate(web): render_web_article(a,idx=idx,ctx="all_w")
            if not neb and not web: st.info("Nenhum resultado.")
        with t_neb:
            for p in neb: render_post(p,ctx="srch_neb",compact=True)
            if not neb: st.info("Nenhuma pesquisa na Nebula.")
        with t_web:
            for idx,a in enumerate(web): render_web_article(a,idx=idx,ctx="web_t")
            if not web: st.info("Nenhum artigo online.")
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════
# KNOWLEDGE
# ════════════════════════════════
def page_knowledge():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.9rem">🕸 Rede de Conexões</h1>', unsafe_allow_html=True)
    email=st.session_state.current_user
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    @st.cache_data(show_spinner=False)
    def get_user_tags(ue_local, all_users, all_posts):
        ud=all_users.get(ue_local,{}); tags=set(area_to_tags(ud.get("area","")))
        for p in all_posts:
            if p.get("author_email")==ue_local: tags.update(t.lower() for t in p.get("tags",[]))
        return tags

    rlist=list(users.keys()); rtags={ue:get_user_tags(ue, users, st.session_state.feed_posts) for ue in rlist}
    edges=[]
    for i in range(len(rlist)):
        for j in range(i+1,len(rlist)):
            e1,e2=rlist[i],rlist[j]; common=list(rtags[e1]&rtags[e2])
            is_fol=e2 in st.session_state.followed or e1 in st.session_state.followed
            if common or is_fol: edges.append((e1,e2,common[:5],len(common)+(2 if is_fol else 0)))
    n=len(rlist); pos={}
    for idx,ue in enumerate(rlist):
        angle=2*3.14159*idx/max(n,1); r_d=0.36+0.05*((hash(ue)%5)/4)
        pos[ue]={"x":0.5+r_d*np.cos(angle),"y":0.5+r_d*np.sin(angle),"z":0.5+0.12*((idx%4)/3-.35)}
    fig=go.Figure()
    for e1,e2,common,strength in edges:
        p1=pos[e1]; p2=pos[e2]; alpha=min(0.55,0.10+strength*0.06)
        fig.add_trace(go.Scatter3d(x=[p1["x"],p2["x"],None],y=[p1["y"],p2["y"],None],z=[p1["z"],p2["z"],None],
            mode="lines",line=dict(color=f"rgba(255,255,255,{alpha:.2f})",width=min(4,1+strength)),hoverinfo="none",showlegend=False)) # White for liquid glass
    ncolors=["#FF9800" if ue==email else ("#4CAF50" if ue in st.session_state.followed else "#FFEB3B") for ue in rlist] # Laranja/Verde/Amarelo
    nsizes=[24 if ue==email else (18 if ue in st.session_state.followed else max(12,10+sum(1 for e1,e2,_,__ in edges if e1==ue or e2==ue))) for ue in rlist]
    ntext=[users.get(ue,{}).get("name","?").split()[0] for ue in rlist]
    nhover=[f"<b>{users.get(ue,{}).get('name','?')}</b><br>{users.get(ue,{}).get('area','')}<extra></extra>" for ue in rlist]
    fig.add_trace(go.Scatter3d(x=[pos[ue]["x"] for ue in rlist],y=[pos[ue]["y"] for ue in rlist],z=[pos[ue]["z"] for ue in rlist],
        mode="markers+text",marker=dict(size=nsizes,color=ncolors,opacity=.9,line=dict(color="rgba(255,255,255,.12)",width=1.5)), # White border
        text=ntext,textposition="top center",textfont=dict(color="var(--t3)",size=9,family="Outfit"), # Adjusted to t3
        hovertemplate=nhover,showlegend=False))
    fig.update_layout(height=430,scene=dict(xaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),yaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),zaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),bgcolor="rgba(0,0,0,0)"),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig,use_container_width=True)
    c1,c2,c3,c4=st.columns(4)
    for col,(v,l) in zip([c1,c2,c3,c4],[(len(rlist),"Pesquisadores"),(len(edges),"Conexões"),(len(st.session_state.followed),"Seguindo"),(len(st.session_state.feed_posts),"Pesquisas")]):
        with col: st.markdown(f'<div class="mbox"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    tab_map,tab_mine,tab_all=st.tabs(["  🗺 Mapa  ","  🔗 Minhas Conexões  ","  👥 Todos  "])
    with tab_map:
        for e1,e2,common,strength in sorted(edges,key=lambda x:-x[3])[:20]:
            n1=users.get(e1,{}); n2=users.get(e2,{})
            ts=tags_html(common[:4]) if common else '<span style="color:var(--t3);font-size:.68rem">seguimento</span>'
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:7px;flex-wrap:wrap"><span style="font-size:.80rem;font-weight:700;font-family:Outfit,sans-serif;color:var(--or1)">{n1.get("name","?")}</span><span style="color:var(--t3)">↔</span><span style="font-size:.80rem;font-weight:700;font-family:Outfit,sans-serif;color:var(--or1)">{n2.get("name","?")}</span><div style="flex:1">{ts}</div><span style="font-size:.65rem;color:var(--gr1);font-weight:700">{strength}pt</span></div></div>', unsafe_allow_html=True)
    with tab_mine:
        my_conn=[(e1,e2,c,s) for e1,e2,c,s in edges if e1==email or e2==email]
        if not my_conn: st.info("Siga pesquisadores e publique pesquisas.")
        for e1,e2,common,strength in sorted(my_conn,key=lambda x:-x[3]):
            other=e2 if e1==email else e1; od=users.get(other,{}); og=ugrad(other)
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:9px;flex-wrap:wrap">{avh(ini(od.get("name","?")),36,get_photo(other),og)}<div style="flex:1"><div><div style="font-weight:700;font-size:.84rem;font-family:Outfit,sans-serif">{od.get("name","?")}</div><div style="font-size:.68rem;color:var(--t3)">{od.get("area","")}</div></div></div>{tags_html(common[:3])}</div></div>', unsafe_allow_html=True)
            cv,cm_b,_=st.columns([1,1,4])
            with cv:
                if st.button("👤 Perfil",key=f"kv_{other}",use_container_width=True): st.session_state.profile_view=other; st.rerun()
            with cm_b:
                if st.button("💬 Chat",key=f"kc_{other}",use_container_width=True):
                    if other not in st.session_state.chat_messages: st.session_state.chat_messages[other]=[]
                    st.session_state.active_chat=other; st.session_state.page="chat"; st.rerun()
    with tab_all:
        sq2=st.text_input("",placeholder="🔍 Buscar…",key="all_s",label_visibility="collapsed")
        for ue,ud in users.items():
            if ue==email: continue
            rn=ud.get("name","?"); uarea=ud.get("area","")
            if sq2 and sq2.lower() not in rn.lower() and sq2.lower() not in uarea.lower(): continue
            is_fol=ue in st.session_state.followed; rg=ugrad(ue)
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:9px">{avh(ini(rn),36,get_photo(ue),rg)}<div style="flex:1"><div style="font-size:.84rem;font-weight:700;font-family:Outfit,sans-serif">{rn}</div><div style="font-size:.68rem;color:var(--t3)">{uarea}</div></div></div></div>', unsafe_allow_html=True)
            ca2,cb2,cc2=st.columns(3)
            with ca2:
                if st.button("👤 Perfil",key=f"av_{ue}",use_container_width=True): st.session_state.profile_view=ue; st.rerun()
            with cb2:
                if st.button("✓ Seguindo" if is_fol else "+ Seguir",key=f"af_{ue}",use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"]=max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                    save_db(); st.rerun()
            with cc2:
                if st.button("💬 Chat",key=f"ac_{ue}",use_container_width=True):
                    if ue not in st.session_state.chat_messages: st.session_state.chat_messages[ue]=[]
                    st.session_state.active_chat=ue; st.session_state.page="chat"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════
# FOLDERS
# ════════════════════════════════
def render_document_analysis(fname, analysis, research_area=""):
    if not analysis: return
    kws=analysis.get("keywords",[]); topics=analysis.get("topics",{})
    authors=analysis.get("authors",[]); years=analysis.get("years",[])
    refs=analysis.get("references",[]); refs_online=analysis.get("references_online",[])
    strengths_a=analysis.get("strengths",[]); improvements=analysis.get("improvements",[])
    rel=analysis.get("relevance_score",0); wq=analysis.get("writing_quality",0)
    rt=analysis.get("reading_time",0); wc=analysis.get("word_count",0)
    sc=analysis.get("sentence_complexity",0); cf=analysis.get("concept_frequency",{})
    rel_color="var(--gr1)" if rel>=70 else ("var(--am1)" if rel>=45 else "var(--err)")
    wq_color="var(--gr1)" if wq>=70 else ("var(--am1)" if wq>=45 else "var(--err)")
    wq_label="Excelente" if wq>=80 else ("Boa" if wq>=60 else ("Regular" if wq>=40 else "Básica"))
    st.markdown(f'''
    <div class="abox">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:9px;margin-bottom:.55rem">
        <div style="flex:1">
          <div style="font-family:Outfit,sans-serif;font-weight:700;font-size:.88rem;margin-bottom:.28rem">{fname}</div>
          <div style="font-size:.78rem;color:var(--t2);line-height:1.62">{analysis.get("summary","")}</div>
        </div>
        <div style="display:flex;gap:.75rem;flex-shrink:0">
          <div style="text-align:center"><div style="font-family:Outfit,sans-serif;font-size:1.2rem;font-weight:800;color:{rel_color}">{rel}%</div><div style="font-size:.57rem;color:var(--t3);text-transform:uppercase;letter-spacing:.07em">Relevância</div></div>
          <div style="text-align:center"><div style="font-family:Outfit,sans-serif;font-size:1.2rem;font-weight:800;color:{wq_color}">{wq}%</div><div style="font-size:.57rem;color:var(--t3);text-transform:uppercase;letter-spacing:.07em">Qualidade</div></div>
        </div>
      </div>
      <div style="display:flex;gap:1.1rem;flex-wrap:wrap;margin-top:.45rem;font-size:.65rem;color:var(--t3)">
        <span>📖 ~{rt} min</span><span>📝 {wc} palavras</span><span>🔑 {len(kws)} keywords</span>
        <span>📚 {len(refs)} refs</span><span>✍️ <strong style="color:{wq_color}">{wq_label}</strong></span>
        <span>📐 {sc:.1f} pal/frase</span>
      </div>
    </div>''', unsafe_allow_html=True)
    tab_kw,tab_topics,tab_authors,tab_refs,tab_improve=st.tabs(["  🔑 Keywords  ","  🎯 Temas  ","  👤 Autores  ","  📚 Refs  ","  ✨ Melhorias  "])
    with tab_kw:
        if kws:
            weights=[max(1,25-i) for i in range(len(kws))]
            fig=go.Figure(go.Bar(x=weights[:20],y=kws[:20],orientation='h',
                marker=dict(color=weights[:20],colorscale=[[0,"var(--s2)"],[.4,"var(--or1)"],[.7,"var(--am1)"],[1,"var(--gr1)"]],line=dict(color="var(--s2)",width=1)), # Dark bg, Laranja/Amarelo/Verde
                text=kws[:20],textposition='inside',textfont=dict(color='white',size=9)))
            layout={**pc(),'height':max(310,len(kws[:20])*17),'yaxis':dict(showticklabels=False),'title':dict(text="TF-IDF Keywords",font=dict(color=var_t1(),family="Outfit",size=12))}
            fig.update_layout(**layout)
            st.markdown('<div class="chart-glass">', unsafe_allow_html=True)
            st.plotly_chart(fig,use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(tags_html(kws[:25]), unsafe_allow_html=True)
        else: st.info("Palavras-chave não extraídas.")
    with tab_topics:
        if topics:
            fig_pie=go.Figure(go.Pie(labels=list(topics.keys()),values=list(topics.values()),hole=0.50,
                marker=dict(colors=CHART_COLORS[:len(topics)],line=dict(color=["var(--s2)"]*15,width=2)), # Dark border
                textfont=dict(color="white",size=9),hoverinfo="label+percent"))
            fig_pie.update_layout(height=290,title=dict(text="Distribuição Temática",font=dict(color=var_t1(),family="Outfit",size=12)),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(font=dict(color="var(--t3)",size=9)),margin=dict(l=0,r=0,t=38,b=0))
            st.markdown('<div class="chart-glass">', unsafe_allow_html=True)
            st.plotly_chart(fig_pie,use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            for i,(topic,score) in enumerate(list(topics.items())[:8]):
                st.markdown(f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:.38rem"><span style="font-size:.76rem;color:var(--t2);flex:1">{topic}</span><span style="font-size:.68rem;color:var(--t3);width:26px;text-align:right">{score}</span></div>', unsafe_allow_html=True)
        else: st.info("Análise temática não disponível.")
    with tab_authors:
        if authors:
            for author in authors:
                g_a=ugrad(author)
                st.markdown(f'<div style="display:flex;align-items:center;gap:7px;padding:.38rem 0;border-bottom:1px solid var(--gb1)"><div style="width:26px;height:26px;border-radius:50%;background:{g_a};display:flex;align-items:center;justify-content:center;font-size:.63rem;font-weight:700;color:white;flex-shrink:0">{ini(author)}</div><span style="font-size:.80rem;color:var(--t1)">{author}</span></div>', unsafe_allow_html=True)
        else: st.markdown('<div style="color:var(--t3);font-size:.77rem">Nenhum autor identificado.</div>', unsafe_allow_html=True)
        if years:
            yl=[y for y,_ in years[:8]]; yv=[c for _,c in years[:8]]
            fig_y=go.Figure(go.Bar(x=yl,y=yv,marker=dict(color=yv,colorscale=[[0,"var(--s2)"],[.5,"var(--or1)"],[1,"var(--am1)"]]),text=yv,textposition="outside",textfont=dict(color="var(--t3)",size=9))) # Dark bg, Laranja/Amarelo
            fig_y.update_layout(height=185,title=dict(text="Anos Citados",font=dict(color=var_t1(),family="Outfit",size=11)),**pc())
            st.markdown('<div class="chart-glass">', unsafe_allow_html=True)
            st.plotly_chart(fig_y,use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    with tab_refs:
        if refs:
            st.markdown(f'<div style="font-size:.61rem;color:var(--t3);text-transform:uppercase;letter-spacing:.09em;margin-bottom:.55rem;font-weight:600">{len(refs)} Referências</div>', unsafe_allow_html=True)
            for r in refs[:12]: st.markdown(f'<div class="ref-item">· {r}</div>', unsafe_allow_html=True)
        else: st.markdown('<div style="color:var(--t3);font-size:.77rem">Nenhuma referência estruturada.</div>', unsafe_allow_html=True)
        if refs_online:
            st.markdown('<div class="dtxt">Artigos Relacionados Online</div>', unsafe_allow_html=True)
            for i,ref in enumerate(refs_online[:5]):
                url_html=f'<a href="{ref["url"]}" target="_blank" style="color:var(--or1);text-decoration:none;font-size:.70rem">↗ Abrir</a>' if ref.get("url") else ""
                st.markdown(f'<div class="scard"><div style="font-family:Outfit,sans-serif;font-size:.84rem;font-weight:700;margin-bottom:.28rem">{ref["title"]}</div><div style="color:var(--t3);font-size:.65rem;margin-bottom:.28rem">{ref["authors"]} · {ref["year"]}</div><div style="color:var(--t2);font-size:.76rem;line-height:1.58">{ref["abstract"][:175]}…</div><div style="margin-top:.3rem">{url_html}</div></div>', unsafe_allow_html=True)
    with tab_improve:
        wq_color2="var(--gr1)" if wq>=70 else ("var(--am1)" if wq>=45 else "var(--err)")
        st.markdown(f'<div class="pbox"><div style="font-family:Outfit,sans-serif;font-weight:700;font-size:.83rem;margin-bottom:.65rem;color:var(--gr1)">📊 Qualidade de Escrita</div><div style="font-size:.74rem;color:var(--t2);margin-bottom:.7rem">Qualidade: <strong style="color:{wq_color2}">{wq}% — {wq_label}</strong> · Complexidade: <strong>{sc:.1f} pal/frase</strong></div></div>', unsafe_allow_html=True) # Removed prog_bar
        if strengths_a:
            st.markdown('<div style="font-size:.61rem;color:var(--t3);text-transform:uppercase;letter-spacing:.09em;margin-bottom:.5rem;font-weight:600">✓ Pontos Fortes</div>', unsafe_allow_html=True)
            for s in strengths_a: st.markdown(f'<div class="str-ok">✓ {s}</div>', unsafe_allow_html=True)
        if improvements:
            st.markdown('<div style="font-size:.61rem;color:var(--t3);text-transform:uppercase;letter-spacing:.09em;margin:.7rem 0 .5rem;font-weight:600">→ Sugestões</div>', unsafe_allow_html=True)
            for imp in improvements: st.markdown(f'<div class="str-imp">→ {imp}</div>', unsafe_allow_html=True)

def var_t1(): return "#E0E0E0" # Adjusted to new t1

def page_folders():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.9rem">📁 Pastas de Pesquisa</h1>', unsafe_allow_html=True)
    email=st.session_state.current_user; u=guser(); research_area=u.get("area","")
    c1,c2,_=st.columns([2,1.2,1.5])
    with c1: nf_name=st.text_input("Nome da pasta",placeholder="Ex: Genômica Comparativa",key="nf_n")
    with c2: nf_desc=st.text_input("Descrição",placeholder="Breve descrição",key="nf_d")
    st.markdown('<div class="btn-primary" style="display:inline-block">', unsafe_allow_html=True)
    if st.button("📁 Criar pasta",key="btn_nf"):
        if nf_name.strip():
            if nf_name not in st.session_state.folders:
                st.session_state.folders[nf_name]={"desc":nf_desc,"files":[],"notes":"","analyses":{}}
                save_db(); st.success(f"Pasta '{nf_name}' criada!"); st.rerun()
            else: st.warning("Pasta já existe.")
        else: st.warning("Digite um nome.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    if not st.session_state.folders:
        st.markdown('<div class="card" style="text-align:center;padding:4rem"><div style="font-size:2.2rem;opacity:.2;margin-bottom:.8rem">📁</div><div style="color:var(--t3)">Nenhuma pasta criada</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True); return
    folder_cols=st.columns(3)
    for idx,(fname,fdata) in enumerate(list(st.session_state.folders.items())):
        if not isinstance(fdata,dict): fdata={"files":fdata,"desc":"","notes":"","analyses":{}}; st.session_state.folders[fname]=fdata
        files=fdata.get("files",[]); analyses=fdata.get("analyses",{})
        all_tags=list({t for an in analyses.values() for t in an.get("keywords",[])[:3]})
        with folder_cols[idx%3]:
            st.markdown(f'<div class="card" style="padding:1.1rem;text-align:center;margin-bottom:.55rem"><div style="font-size:1.8rem;opacity:.45;margin-bottom:6px">📁</div><div style="font-family:Outfit,sans-serif;font-weight:700;font-size:.92rem">{fname}</div><div style="color:var(--t3);font-size:.66rem;margin-top:2px">{fdata.get("desc","")}</div><div style="margin-top:.38rem;font-size:.68rem;color:var(--or1)">{len(files)} arquivo(s) · {len(analyses)} analisado(s)</div><div style="margin-top:.35rem">{tags_html(all_tags[:3])}</div></div>', unsafe_allow_html=True)
    for fname,fdata in list(st.session_state.folders.items()):
        if not isinstance(fdata,dict): fdata={"files":fdata,"desc":"","notes":"","analyses":{}}; st.session_state.folders[fname]=fdata
        files=fdata.get("files",[]); analyses=fdata.get("analyses",{})
        with st.expander(f"📁 {fname} — {len(files)} arquivo(s)"):
            up=st.file_uploader("",type=None,key=f"up_{fname}",label_visibility="collapsed",accept_multiple_files=True)
            if up:
                for uf in up:
                    if uf.name not in files: files.append(uf.name)
                    if fname not in st.session_state.folder_files_bytes: st.session_state.folder_files_bytes[fname]={}
                    uf.seek(0); st.session_state.folder_files_bytes[fname][uf.name]=uf.read()
                fdata["files"]=files; save_db(); st.success(f"{len(up)} arquivo(s) adicionado(s)!")
            if files:
                for f in files:
                    ftype=get_ftype(f); has_an=f in analyses
                    icon={"PDF":"📄","Word":"📝","Planilha":"📊","Dados":"📈","Código Python":"🐍","Notebook":"📓","Apresentação":"📽","Imagem":"🖼","Markdown":"📋"}.get(ftype,"📄")
                    ab='<span class="badge-pub" style="font-size:.59rem;margin-left:5px">✓</span>' if has_an else ''
                    st.markdown(f'<div style="display:flex;align-items:center;gap:7px;padding:.40rem 0;border-bottom:1px solid var(--gb1)"><span>{icon}</span><span style="font-size:.77rem;color:var(--t2);flex:1">{f}</span>{ab}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<p style="color:var(--t3);font-size:.73rem;text-align:center;padding:.45rem">Arraste arquivos — PDF, DOCX, XLSX, CSV…</p>', unsafe_allow_html=True)
            st.markdown('<hr>', unsafe_allow_html=True)
            ca_btn,cb_btn,_=st.columns([1.5,1.5,2])
            with ca_btn:
                st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
                if st.button("🔬 Analisar",key=f"analyze_{fname}",use_container_width=True):
                    if files:
                        pb=st.progress(0,"Iniciando análise…")
                        folder_bytes=st.session_state.folder_files_bytes.get(fname,{})
                        for fi,f in enumerate(files):
                            pb.progress((fi+1)/len(files),f"Analisando: {f[:30]}…")
                            fbytes=folder_bytes.get(f,b""); ftype=get_ftype(f)
                            an=analyze_document_intelligent(f,fbytes,ftype,research_area)
                            analyses[f]=an
                        fdata["analyses"]=analyses
                        all_kw=list({kw for an in analyses.values() for kw in an.get("keywords",[])[:5]})
                        if all_kw:
                            with st.spinner("Buscando referências online…"):
                                refs_online=search_references_online(all_kw[:6],n=5)
                                for an in analyses.values(): an["references_online"]=refs_online
                        save_db(); pb.empty(); st.success("✓ Análise completa!"); st.rerun()
                    else: st.warning("Adicione arquivos antes.")
                st.markdown('</div>', unsafe_allow_html=True)
            with cb_btn:
                st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
                if st.button("🗑 Excluir",key=f"df_{fname}",use_container_width=True):
                    del st.session_state.folders[fname]
                    if fname in st.session_state.folder_files_bytes: del st.session_state.folder_files_bytes[fname]
                    save_db(); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            if analyses:
                st.markdown('<div class="dtxt">Análises Inteligentes</div>', unsafe_allow_html=True)
                for f,an in analyses.items():
                    with st.expander(f"🔬 {f}"):
                        render_document_analysis(f,an,research_area)
            st.markdown('<hr>', unsafe_allow_html=True)
            note=st.text_area("Notas",value=fdata.get("notes",""),key=f"note_{fname}",height=65,placeholder="Anotações…")
            if st.button("💾 Salvar nota",key=f"sn_{fname}"):
                fdata["notes"]=note; save_db(); st.success("✓ Nota salva!")
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════
# ANALYTICS
# ════════════════════════════════
def page_analytics():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.9rem">📊 Painel de Pesquisa</h1>', unsafe_allow_html=True)
    email=st.session_state.current_user; d=st.session_state.stats_data
    tab_f,tab_p,tab_i,tab_pr=st.tabs(["  📁 Pastas  ","  📝 Publicações  ","  📈 Impacto  ","  🎯 Interesses  "])
    with tab_f:
        folders=st.session_state.folders
        if not folders:
            st.markdown('<div class="card" style="text-align:center;padding:3rem;color:var(--t3)">Crie pastas e analise documentos.</div>', unsafe_allow_html=True)
        else:
            all_analyses={f:an for fd in folders.values() if isinstance(fd,dict) for f,an in fd.get("analyses",{}).items()}
            total_files=sum(len(fd.get("files",[]) if isinstance(fd,dict) else fd) for fd in folders.values())
            all_kws=[kw for an in all_analyses.values() for kw in an.get("keywords",[])]
            all_topics=defaultdict(int)
            for an in all_analyses.values():
                for t,s in an.get("topics",{}).items(): all_topics[t]+=s
            c1,c2,c3,c4=st.columns(4)
            for col,(v,l) in zip([c1,c2,c3,c4],[(len(folders),"Pastas"),(total_files,"Arquivos"),(len(all_analyses),"Analisados"),(len(set(all_kws[:100])),"Keywords")]):
                with col: st.markdown(f'<div class="mbox"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>', unsafe_allow_html=True)
            if all_topics:
                fig_t=go.Figure(go.Bar(x=list(all_topics.values())[:8],y=list(all_topics.keys())[:8],orientation='h',marker=dict(color=CHART_COLORS[:8]),text=[str(v) for v in list(all_topics.values())[:8]],textposition="outside",textfont=dict(color="var(--t3)",size=9)))
                layout_t={**pc(),'height':270,'yaxis':dict(showgrid=False,color="var(--t3)",tickfont=dict(size=9)),'title':dict(text="Temas",font=dict(color=var_t1(),family="Outfit",size=12))}
                fig_t.update_layout(**layout_t)
                st.markdown('<div class="chart-glass">', unsafe_allow_html=True)
                st.plotly_chart(fig_t,use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
    with tab_p:
        my_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==email]
        if not my_posts:
            st.markdown('<div class="card" style="text-align:center;padding:2.5rem;color:var(--t3)">Publique pesquisas para ver métricas.</div>', unsafe_allow_html=True)
        else:
            c1,c2,c3=st.columns(3)
            with c1: st.markdown(f'<div class="mbox"><div class="mval">{len(my_posts)}</div><div class="mlbl">Pesquisas</div></div>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="mbox"><div class="mval">{sum(p["likes"] for p in my_posts)}</div><div class="mlbl">Curtidas</div></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="mbox"><div class="mval">{sum(len(p.get("comments",[])) for p in my_posts)}</div><div class="mlbl">Comentários</div></div>', unsafe_allow_html=True)
            titles_s=[p["title"][:16]+"…" for p in my_posts]
            fig_eng=go.Figure()
            fig_eng.add_trace(go.Bar(name="Curtidas",x=titles_s,y=[p["likes"] for p in my_posts],marker_color=CHART_COLORS[0]))
            fig_eng.add_trace(go.Bar(name="Comentários",x=titles_s,y=[len(p.get("comments",[])) for p in my_posts],marker_color=CHART_COLORS[2]))
            fig_eng.update_layout(barmode="group",title=dict(text="Engajamento",font=dict(color=var_t1(),family="Outfit",size=12)),height=250,**pc(),legend=dict(font=dict(color="var(--t3)")))
            st.markdown('<div class="chart-glass">', unsafe_allow_html=True)
            st.plotly_chart(fig_eng,use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            for p in sorted(my_posts,key=lambda x:x.get("date",""),reverse=True):
                t_s=p["title"][:55]+("…" if len(p["title"])>55 else "")
                st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;justify-content:space-between"><div style="font-family:Outfit,sans-serif;font-size:.88rem;font-weight:700">{t_s}</div>{badge(p["status"])}</div><div style="font-size:.70rem;color:var(--t3);margin-top:.38rem">{p.get("date","")} · {p["likes"]} curtidas · {len(p.get("comments",[]))} comentários · {p.get("views",0)} views</div><div style="margin-top:.38rem">{tags_html(p.get("tags",[])[:4])}</div></div>', unsafe_allow_html=True)
    with tab_i:
        c1,c2,c3=st.columns(3)
        with c1: st.markdown(f'<div class="mbox"><div class="mval">{d.get("h_index",4)}</div><div class="mlbl">Índice H</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="mbox"><div class="mval">{d.get("fator_impacto",3.8):.1f}</div><div class="mlbl">Fator de Impacto</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="mbox"><div class="mval-green">{len(st.session_state.saved_articles)}</div><div class="mlbl">Artigos Salvos</div></div>', unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)
        new_h=st.number_input("Índice H",0,200,d.get("h_index",4),key="e_h_ana") # Changed key to avoid conflict
        new_fi=st.number_input("Fator de impacto",0.0,100.0,float(d.get("fator_impacto",3.8)),step=0.1,key="e_fi_ana") # Changed key
        new_notes=st.text_area("Notas",value=d.get("notes",""),key="e_notes",height=78)
        if st.button("💾 Salvar métricas",key="btn_save_m_ana"): # Changed key
            d.update({"h_index":new_h,"fator_impacto":new_fi,"notes":new_notes}); st.success("✓ Salvo!")
    with tab_pr:
        prefs=st.session_state.user_prefs.get(email,{})
        if prefs:
            top=sorted(prefs.items(),key=lambda x:-x[1])[:14]; mx=max(s for _,s in top) if top else 1
            cats=[t for t,_ in top[:8]]; vals=[round(s/mx*100) for _,s in top[:8]]
            if len(cats)>=3:
                fig_r=go.Figure(go.Scatterpolar(r=vals+[vals[0]],theta=cats+[cats[0]],fill='toself',
                    line=dict(color="#FF9800"),fillcolor="rgba(255,152,0,.13)")) # Laranja
                fig_r.update_layout(height=275,polar=dict(bgcolor="rgba(0,0,0,0)",radialaxis=dict(visible=True,gridcolor="rgba(255,255,255,.07)",color="var(--t3)",tickfont=dict(size=8)),angularaxis=dict(gridcolor="rgba(255,255,255,.07)",color="var(--t3)",tickfont=dict(size=9))),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=40,r=40,t=18,b=18))
                st.markdown('<div class="chart-glass">', unsafe_allow_html=True)
                st.plotly_chart(fig_r,use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            c1,c2=st.columns(2)
            for i,(tag,score) in enumerate(top):
                with (c1 if i%2==0 else c2):
                    st.markdown(f'<div style="display:flex;justify-content:space-between;font-size:.76rem;margin-bottom:2px"><span style="color:var(--t2)">{tag}</span><span style="color:var(--or1);font-weight:600">{round(score,1)}</span></div>', unsafe_allow_html=True)
        else: st.info("Interaja com pesquisas para construir seu perfil.")
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════
# IMAGE ANALYSIS
# ════════════════════════════════
def page_img_search():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.35rem">🔬 Análise Visual Científica</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.78rem;margin-bottom:1.1rem">Detecta padrões, estruturas e conecta com pesquisas similares</p>', unsafe_allow_html=True)
    col_up,col_res=st.columns([1,1.9])
    with col_up:
        st.markdown('<div class="card" style="padding:1.1rem">', unsafe_allow_html=True)
        img_file=st.file_uploader("📷 Carregar Imagem",type=["png","jpg","jpeg","webp","tiff"],key="img_up")
        uploaded_img_bytes = None
        if img_file:
            uploaded_img_bytes = img_file.read()
            st.image(uploaded_img_bytes,use_container_width=True,caption="Imagem carregada")
        st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
        run=st.button("🔬 Analisar",use_container_width=True,key="btn_run")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="ai-warn" style="margin-top:.85rem"><div style="font-size:.67rem;color:var(--am1);font-weight:700;margin-bottom:2px">⚠️ Aviso</div><div style="font-size:.64rem;color:var(--t2);line-height:1.62">Análise por algoritmos computacionais. Não substitui especialistas.</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col_res:
        if run and uploaded_img_bytes:
            with st.spinner("Analisando…"):
                rep=analyze_image_advanced(uploaded_img_bytes); st.session_state.img_result=rep
            if rep:
                conf_c="var(--gr1)" if rep["confidence"]>80 else ("var(--am1)" if rep["confidence"]>60 else "var(--err)")
                st.markdown(f'''
                <div class="abox">
                  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:9px;margin-bottom:.5rem">
                    <div>
                      <div style="font-size:.59rem;color:var(--t3);letter-spacing:.09em;text-transform:uppercase;margin-bottom:3px;font-weight:600">Categoria</div>
                      <div style="font-family:Outfit,sans-serif;font-size:1.05rem;font-weight:700;margin-bottom:3px">{rep["category"]}</div>
                      <div style="font-size:.77rem;color:var(--t2);margin-bottom:.38rem">{rep["context"]}</div>
                    </div>
                    <div style="background:rgba(8,8,8,.4);border:1px solid var(--gb1);border-radius:12px;padding:.55rem .9rem;text-align:center;flex-shrink:0">
                      <div style="font-family:Outfit,sans-serif;font-size:1.45rem;font-weight:800;color:{conf_c}">{rep["confidence"]}%</div>
                      <div style="font-size:.57rem;color:var(--t3);text-transform:uppercase;font-weight:600">confiança</div>
                    </div>
                  </div>
                  <div style="font-size:.79rem;color:var(--t2);line-height:1.65;margin-bottom:.5rem">{rep["description"]}</div>
                  <div style="display:flex;gap:1.4rem;flex-wrap:wrap;font-size:.65rem;color:var(--t3)">
                    <span>Material: <strong style="color:var(--t2)">{rep["material"]}</strong></span>
                    <span>Resolução: <strong style="color:var(--t2)">{rep["size"][0]}×{rep["size"][1]}</strong></span>
                    <span>Brilho: <strong style="color:var(--t2)">{rep["brightness"]}</strong></span>
                  </div>
                </div>''', unsafe_allow_html=True)
                c1,c2,c3=st.columns(3)
                sym_lbl="Alta" if rep["symmetry"]>0.78 else ("Média" if rep["symmetry"]>0.52 else "Baixa")
                with c1: st.markdown(f'<div class="mbox"><div style="font-family:Outfit,sans-serif;font-size:.95rem;font-weight:700;color:var(--or1)">{rep["texture"]["complexity"]}</div><div class="mlbl">Complexidade</div></div>', unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="mbox"><div style="font-family:Outfit,sans-serif;font-size:.95rem;font-weight:700;color:var(--gr1)">{sym_lbl}</div><div class="mlbl">Simetria</div></div>', unsafe_allow_html=True)
                with c3: st.markdown(f'<div class="mbox"><div style="font-family:Outfit,sans-serif;font-size:.95rem;font-weight:700;color:var(--am1)">{rep["lines"]["direction"]}</div><div class="mlbl">Dir. Linhas</div></div>', unsafe_allow_html=True)
                l=rep["lines"]; s_img=l["strengths"]; max_s=max(s_img.values())+0.01
                st.markdown('<div class="pbox"><div style="font-family:Outfit,sans-serif;font-weight:700;font-size:.82rem;margin-bottom:.65rem;color:var(--gr1)">📐 Análise de Linhas</div>', unsafe_allow_html=True)
                for dir_name,val in s_img.items():
                    is_dom=dir_name==l["direction"]
                    st.markdown(f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:.35rem"><span style="font-size:.68rem;color:{"var(--gr1)" if is_dom else "var(--t3)"};flex:1">{"★ " if is_dom else ""}{dir_name}</span><span style="font-size:.66rem;color:var(--t3);width:34px;text-align:right">{val:.1f}</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:.68rem;color:var(--t3);margin-top:.45rem">Formas: <strong style="color:var(--gr1)">{" · ".join(rep["shapes"])}</strong></div></div>', unsafe_allow_html=True)
                rv,gv,bv=rep["color"]["r"],rep["color"]["g"],rep["color"]["b"]
                hex_c="#{:02x}{:02x}{:02x}".format(int(rv),int(gv),int(bv))
                pal_html="".join(f'<div style="width:26px;height:26px;border-radius:6px;background:rgb{str(p)};border:1.5px solid rgba(255,255,255,.06)"></div>' for p in rep["palette"][:7])
                temp_str="Quente" if rep["color"]["warm"] else ("Fria" if rep["color"]["cool"] else "Neutra")
                st.markdown(f'<div class="abox"><div style="font-family:Outfit,sans-serif;font-weight:700;font-size:.82rem;margin-bottom:.72rem">🎨 Cor & Paleta</div><div style="display:flex;gap:10px;align-items:center;margin-bottom:.8rem"><div style="width:40px;height:40px;border-radius:10px;background:{hex_c};border:1.5px solid var(--gb1);flex-shrink:0"></div><div style="font-size:.77rem;color:var(--t2);line-height:1.72">RGB: <strong>({int(rv)},{int(gv)},{int(bv)})</strong> · {hex_c.upper()}<br>Dominante: <strong>{rep["color"]["dom"]}</strong> · {temp_str} · Sat: <strong>{rep["color"]["sat"]:.0f}%</strong></div></div><div style="display:flex;gap:4px;flex-wrap:wrap">{pal_html}</div></div>', unsafe_allow_html=True)
                if rep.get("histograms"):
                    h=rep["histograms"]; bins_x=list(range(0,256,8))[:32]
                    fig_h=go.Figure()
                    fig_h.add_trace(go.Scatter(x=bins_x,y=h["r"][:32],fill='tozeroy',name='R',line=dict(color='rgba(255,152,0,.8)',width=1.5),fillcolor='rgba(255,152,0,.10)')) # Laranja
                    fig_h.add_trace(go.Scatter(x=bins_x,y=h["g"][:32],fill='tozeroy',name='G',line=dict(color='rgba(76,175,80,.8)',width=1.5),fillcolor='rgba(76,175,80,.10)')) # Verde
                    fig_h.add_trace(go.Scatter(x=bins_x,y=h["b"][:32],fill='tozeroy',name='B',line=dict(color='rgba(33,150,243,.8)',width=1.5),fillcolor='rgba(33,150,243,.10)')) # Azul
                    fig_h.update_layout(height=172,title=dict(text="Histograma RGB",font=dict(color=var_t1(),family="Outfit",size=11)),**pc(),legend=dict(font=dict(color="var(--t3)",size=9)),margin=dict(l=10,r=10,t=32,b=8))
                    st.markdown('<div class="chart-glass">', unsafe_allow_html=True)
                    st.plotly_chart(fig_h,use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
        elif not img_file:
            st.markdown('<div class="card" style="padding:4.5rem 2rem;text-align:center"><div style="font-size:2.8rem;opacity:.18;margin-bottom:1rem">🔬</div><div style="font-family:Outfit,sans-serif;font-size:1rem;color:var(--t2)">Carregue uma imagem científica</div><div style="font-size:.74rem;color:var(--t3);margin-top:.45rem;line-height:1.9">PNG · JPG · WEBP · TIFF<br>Microscopia · Cristalografia · Fluorescência</div></div>', unsafe_allow_html=True)
    if st.session_state.get("img_result"):
        rep=st.session_state.img_result; st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<h2 style="margin-bottom:.65rem">🔗 Pesquisas Relacionadas</h2>', unsafe_allow_html=True)
        kw=(rep.get("kw","")+" "+rep.get("category","")).lower().split(); all_terms=list(set(kw))
        t_neb,t_fol,t_web=st.tabs(["  🔬 Na Nebula  ","  📁 Nas Pastas  ","  🌐 Internet  "])
        with t_neb:
            neb_r=sorted([(sum(1 for t in all_terms if len(t)>2 and t in (p.get("title","")+" "+p.get("abstract","")+" "+" ".join(p.get("tags",[]))).lower()),p) for p in st.session_state.feed_posts],key=lambda x:-x[0])
            neb_r=[p for s,p in neb_r if s>0]
            if neb_r:
                for p in neb_r[:4]: render_post(p,ctx="img_neb",compact=True)
            else: st.markdown('<div style="color:var(--t3);padding:.9rem">Nenhuma pesquisa similar.</div>', unsafe_allow_html=True)
        with t_fol:
            fm=[]
            for fn,fd in st.session_state.folders.items():
                if not isinstance(fd,dict): continue
                fkws=list({kw for an in fd.get("analyses",{}).values() for kw in an.get("keywords",[])})
                sc=sum(1 for t in all_terms if len(t)>2 and any(t in ft for ft in fkws))
                if sc>0: fm.append((sc,fn,fd))
            fm.sort(key=lambda x:-x[0])
            if fm:
                for _,fn,fd in fm[:4]:
                    an_kws=list({kw for an in fd.get("analyses",{}).values() for kw in an.get("keywords",[])[:4]})
                    st.markdown(f'<div class="img-rc"><div style="font-family:Outfit,sans-serif;font-size:.89rem;font-weight:700;margin-bottom:.28rem">📁 {fn}</div><div style="color:var(--t3);font-size:.67rem;margin-bottom:.38rem">{len(fd.get("files",[]))} arquivos</div><div>{tags_html(an_kws[:6])}</div></div>', unsafe_allow_html=True)
            else: st.markdown('<div style="color:var(--t3);padding:.9rem">Nenhum documento relacionado.</div>', unsafe_allow_html=True)
        with t_web:
            ck=f"img_{rep['kw'][:40]}"
            if ck not in st.session_state.scholar_cache:
                with st.spinner("Buscando artigos…"):
                    st.session_state.scholar_cache[ck]=search_ss(f"{rep['category']} {rep['object_type']} {rep['material']}",4)
            web_r=st.session_state.scholar_cache.get(ck,[])
            if web_r:
                for idx,a in enumerate(web_r): render_web_article(a,idx=idx+2000,ctx="img_web")
            else: st.markdown('<div style="color:var(--t3);padding:.9rem">Sem resultados online.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════
# CHAT
# ════════════════════════════════
def page_chat():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:.8rem;margin-bottom:.9rem">💬 Mensagens</h1>', unsafe_allow_html=True)
    col_c,col_m=st.columns([.85,2.8])
    email=st.session_state.current_user
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    with col_c:
        st.markdown('<div style="font-size:.61rem;font-weight:700;color:var(--t3);letter-spacing:.09em;text-transform:uppercase;margin-bottom:.75rem">Conversas</div>', unsafe_allow_html=True)
        shown=set()
        for ue in st.session_state.chat_contacts:
            if ue==email or ue in shown: continue
            shown.add(ue); ud=users.get(ue,{}); uname=ud.get("name","?"); uin=ini(uname)
            uphoto=ud.get("photo_b64"); ug=ugrad(ue)
            msgs=st.session_state.chat_messages.get(ue,[])
            last=msgs[-1]["text"][:22]+"…" if msgs and len(msgs[-1]["text"])>22 else (msgs[-1]["text"] if msgs else "Iniciar")
            active=st.session_state.active_chat==ue; online=is_online(ue)
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            bg="rgba(255,255,255,.11)" if active else "rgba(8,8,8,.65)"; bdr="rgba(255,255,255,.28)" if active else "var(--gb1)"
            st.markdown(f'<div style="background:{bg};border:1px solid {bdr};border-radius:12px;padding:8px 10px;margin-bottom:4px"><div style="display:flex;align-items:center;gap:7px">{avh(uin,30,uphoto,ug)}<div style="overflow:hidden;flex:1"><div style="font-size:.78rem;font-weight:600;font-family:Outfit,sans-serif">{dot}{uname}</div><div style="font-size:.65rem;color:var(--t3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{last}</div></div></div></div>', unsafe_allow_html=True)
            if st.button("💬",key=f"oc_{ue}",use_container_width=True): st.session_state.active_chat=ue; st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
        nc=st.text_input("",placeholder="E-mail para adicionar…",key="new_ct",label_visibility="collapsed")
        if st.button("+ Adicionar",key="btn_add_ct",use_container_width=True):
            if nc in users and nc!=email:
                if nc not in st.session_state.chat_contacts: st.session_state.chat_contacts.append(nc)
                st.rerun()
            elif nc: st.toast("Usuário não encontrado.")
    with col_m:
        if st.session_state.active_chat:
            contact=st.session_state.active_chat; cd=users.get(contact,{}); cname=cd.get("name","?"); cin=ini(cname)
            cphoto=cd.get("photo_b64"); cg=ugrad(contact)
            msgs=st.session_state.chat_messages.get(contact,[]); online=is_online(contact)
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            st.markdown(f'<div style="background:var(--glass);border:1px solid var(--gb1);border-radius:14px;padding:11px 15px;margin-bottom:.9rem;display:flex;align-items:center;gap:11px"><div style="flex-shrink:0">{avh(cin,38,cphoto,cg)}</div><div style="flex:1"><div style="font-weight:700;font-size:.90rem;font-family:Outfit,sans-serif">{dot}{cname}</div><div style="font-size:.66rem;color:var(--gr1)">🔒 AES-256 ativo</div></div></div>', unsafe_allow_html=True)
            for msg in msgs:
                is_me=msg["from"]=="me"; cls="bme" if is_me else "bthem"
                st.markdown(f'<div style="display:flex;{"justify-content:flex-end" if is_me else ""}"<div class="{cls}">{msg["text"]}<div style="font-size:.58rem;color:rgba(255,255,255,.20);margin-top:2px;text-align:{"right" if is_me else "left"}">{msg["time"]}</div></div></div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            c_inp,c_btn=st.columns([5,1])
            with c_inp: nm=st.text_input("",placeholder="Escreva uma mensagem…",key=f"mi_{contact}",label_visibility="collapsed")
            with c_btn:
                st.markdown("<div style='height:5px'></div>", unsafe_allow_html=True)
                if st.button("→",key=f"ms_{contact}",use_container_width=True):
                    if nm:
                        now=datetime.now().strftime("%H:%M")
                        st.session_state.chat_messages.setdefault(contact,[]).append({"from":"me","text":nm,"time":now}); st.rerun()
        else:
            st.markdown('<div class="card" style="text-align:center;padding:5.5rem"><div style="font-size:2.2rem;opacity:.18;margin-bottom:.9rem">💬</div><div style="font-family:Outfit,sans-serif;font-size:.98rem;color:var(--t2)">Selecione uma conversa</div><div style="font-size:.72rem;color:var(--t3);margin-top:.45rem">🔒 End-to-end criptografado</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════
# ROUTER
# ════════════════════════════════
def main():
    inject_css()
    if not st.session_state.logged_in:
        p=st.session_state.page
        if p=="verify_email": page_verify_email()
        elif p=="2fa": page_2fa()
        else: page_login()
        return
    render_topnav()
    if st.session_state.profile_view:
        page_profile(st.session_state.profile_view); return
    {
        "feed":page_feed,"search":page_search,"knowledge":page_knowledge,
        "folders":page_folders,"analytics":page_analytics,"img_search":page_img_search,
        "chat":page_chat,
    }.get(st.session_state.page,page_feed)()

main()
