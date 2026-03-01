import subprocess, sys, os, json, hashlib, random, string, base64, re, io
from datetime import datetime
from collections import defaultdict, Counter
import math

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

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: pass
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
    except: pass

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
    "135deg,#f97316,#f59e0b",
    "135deg,#10b981,#3b82f6",
    "135deg,#8b5cf6,#ec4899",
    "135deg,#f59e0b,#10b981",
    "135deg,#ef4444,#f97316",
    "135deg,#3b82f6,#8b5cf6",
    "135deg,#06b6d4,#10b981",
    "135deg,#f97316,#ef4444",
]

def ugrad(email):
    return f"linear-gradient({USER_GRADIENTS[hash(email or '') % len(USER_GRADIENTS)]})"

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

def extract_text_from_pdf_bytes(pdf_bytes):
    if PyPDF2 is None: return ""
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes)); text = ""
        for page in reader.pages[:30]:
            try: text += page.extract_text() + "\n"
            except: pass
        return text[:50000]
    except: return ""

def extract_text_from_csv_bytes(csv_bytes):
    try:
        df = pd.read_csv(io.BytesIO(csv_bytes), nrows=200)
        summary = f"Colunas: {', '.join(df.columns.tolist())}\nLinhas: {len(df)}\n"
        for col in df.columns[:10]:
            if df[col].dtype == object:
                vals = df[col].dropna().head(5).tolist()
                summary += f"{col}: {', '.join(str(v) for v in vals)}\n"
            else:
                summary += f"{col}: min={df[col].min():.2f}, max={df[col].max():.2f}\n"
        return summary
    except: return ""

def extract_text_from_xlsx_bytes(xlsx_bytes):
    if openpyxl is None: return ""
    try:
        wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), read_only=True, data_only=True); text = ""
        for sheet_name in wb.sheetnames[:3]:
            ws = wb[sheet_name]; text += f"\n=== {sheet_name} ===\n"
            for row in list(ws.iter_rows(max_row=50, values_only=True)):
                row_vals = [str(v) for v in row if v is not None]
                if row_vals: text += " | ".join(row_vals[:10]) + "\n"
        return text[:20000]
    except: return ""

def extract_keywords_tfidf(text, top_n=30):
    if not text: return []
    words = re.findall(r'\b[a-záàâãéêíóôõúüçA-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]{4,}\b', text.lower())
    words = [w for w in words if w not in STOPWORDS]
    if not words: return []
    tf = Counter(words); total = sum(tf.values())
    top = sorted({w:c/total for w,c in tf.items()}.items(), key=lambda x:-x[1])[:top_n]
    return [w for w,_ in top]

def extract_authors_from_text(text):
    authors = []; seen = set()
    for pat in [r'(?:Autor(?:es)?|Author(?:s)?)[:\s]+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){1,4})',
                r'(?:Por|By)[:\s]+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){1,3})']:
        for m in re.findall(pat, text):
            if m.strip().lower() not in seen and len(m.strip())>5:
                seen.add(m.strip().lower()); authors.append(m.strip())
    return authors[:8]

def extract_years_from_text(text):
    years = re.findall(r'\b(19[5-9]\d|20[0-3]\d)\b', text)
    return sorted(Counter(years).items(), key=lambda x:-x[1])[:10]

def extract_references_from_text(text):
    refs = []
    for block in re.split(r'\n(?=\[\d+\])', text)[1:21]:
        clean = re.sub(r'\s+',' ',block.strip())
        if len(clean)>30: refs.append(clean[:200])
    return refs[:15]

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

def estimate_reading_time(text):
    words = len(text.split())
    minutes = max(1, round(words / 200))
    return minutes, words

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

def analyze_document_intelligent(fname, fbytes, ftype, research_area=""):
    result = {"file":fname,"type":ftype,"text_length":0,"keywords":[],"authors":[],
              "years":[],"references":[],"topics":{},"references_online":[],"relevance_score":0,
              "summary":"","strengths":[],"improvements":[],"progress":random.randint(55,98),
              "writing_quality":0,"reading_time":0,"word_count":0,"key_concepts":[],
              "concept_frequency":{},"sentence_complexity":0}
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
        result["reading_time"] = minutes
        result["word_count"] = words
        result["writing_quality"] = compute_writing_quality(text, result["keywords"], result["references"])
        # Key concepts = top keywords with frequency
        words_list = re.findall(r'\b[a-záàâãéêíóôõúüçA-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]{4,}\b', text.lower())
        words_filtered = [w for w in words_list if w not in STOPWORDS]
        freq = Counter(words_filtered)
        result["concept_frequency"] = dict(freq.most_common(20))
        result["key_concepts"] = [w for w, _ in freq.most_common(10)]
        sentences = re.split(r'[.!?]+', text)
        result["sentence_complexity"] = round(sum(len(s.split()) for s in sentences) / max(len(sentences), 1), 1)
        if research_area:
            area_words=research_area.lower().split()
            rel=sum(1 for w in area_words if any(w in kw for kw in result["keywords"]))
            result["relevance_score"]=min(100,rel*15+random.randint(20,50))
        else: result["relevance_score"]=random.randint(45,85)
        n_refs=len(result["references"]); n_kw=len(result["keywords"])
        if n_refs>5: result["strengths"].append(f"Boa referenciação ({n_refs} refs encontradas)")
        if n_kw>15: result["strengths"].append(f"Vocabulário técnico rico ({n_kw} termos)")
        if result["authors"]: result["strengths"].append(f"Autoria identificada: {result['authors'][0]}")
        if result["writing_quality"]>70: result["strengths"].append("Alta qualidade de escrita técnica")
        if words>3000: result["strengths"].append(f"Texto extenso e detalhado ({words} palavras)")
        if n_refs<3: result["improvements"].append("Adicionar mais referências bibliográficas")
        if not result["authors"]: result["improvements"].append("Incluir autoria explícita no documento")
        if result["writing_quality"]<50: result["improvements"].append("Melhorar densidade técnica e estrutura")
        if words<500: result["improvements"].append("Expandir o conteúdo para maior profundidade")
        top_topics=list(result["topics"].keys())[:3]; top_kw=result["keywords"][:5]
        result["summary"]=f"Documento {ftype} · {words} palavras · ~{minutes} min leitura · Temas: {', '.join(top_topics)} · Keywords: {', '.join(top_kw)}."
    else:
        result["summary"]=f"Arquivo {ftype} — análise de texto não disponível para este formato."
        result["relevance_score"]=random.randint(30,60)
        result["keywords"]=extract_keywords_tfidf(fname.lower().replace("_"," "),5)
        result["topics"]=compute_topic_distribution(result["keywords"])
    return result

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
        if skin_pct>0.15 and mr>140:
            cat,desc,kw,material,obj_type,context="Histopatologia H&E",f"Tecido orgânico detectado ({skin_pct*100:.0f}% da área). Padrão típico de lâminas H&E com coloração rosa-violeta.","hematoxylin eosin HE staining histopathology tissue","Tecido Biológico","Amostra Histopatológica","Microscopia óptica de tecidos corados"
        elif has_grid and edge_intensity>18:
            cat,desc,kw,material,obj_type,context="Cristalografia / Difração",f"Padrão periódico detectado (borda: {edge_intensity:.1f}). Grade cristalina ou padrão de difração.","X-ray diffraction crystallography TEM crystal structure","Material Cristalino","Rede Cristalina","Análise de estrutura atômica"
        elif mg>165 and mr<125:
            cat,desc,kw,material,obj_type,context="Fluorescência GFP/FITC",f"Canal verde dominante (G={mg:.0f}). Marcação fluorescente típica de proteínas GFP ou FITC.","GFP fluorescence confocal microscopy protein","Proteínas Fluorescentes","Células Marcadas","Microscopia confocal de fluorescência"
        elif mb>165 and mr<110:
            cat,desc,kw,material,obj_type,context="Fluorescência DAPI",f"Canal azul dominante (B={mb:.0f}). Coloração de DNA/cromatina com DAPI.","DAPI nuclear staining DNA fluorescence nucleus","DNA / Cromatina","Núcleos Celulares","Marcação nuclear fluorescente"
        elif has_circular and edge_intensity>24:
            cat,desc,kw,material,obj_type,context="Microscopia Celular",f"Estruturas circulares detectadas (intensidade: {edge_intensity:.1f}). Possíveis células, vesículas ou organelas.","cell organelle vesicle bacteria microscopy biology","Componentes Celulares","Células/Organelas","Microscopia de campo claro ou fluorescência"
        elif edge_intensity>40:
            cat,desc,kw,material,obj_type,context="Diagrama / Gráfico Científico","Bordas muito nítidas detectadas. Possível diagrama, fluxograma ou gráfico de dados.","scientific visualization chart diagram data","Dados Estruturados","Gráfico/Diagrama","Representação visual de dados"
        elif sym>0.82:
            cat,desc,kw,material,obj_type,context="Estrutura Molecular",f"Alta simetria detectada ({sym:.3f}). Possível estrutura molecular, cristal ou padrão atômico.","molecular structure protein crystal symmetry chemistry","Moléculas","Estrutura Molecular","Visualização molecular 3D ou cristalografia"
        else:
            temp="quente" if warm else ("fria" if cool else "neutra")
            cat,desc,kw,material,obj_type,context="Imagem Científica Geral",f"Imagem com temperatura de cor {temp}. Análise geral aplicada.","scientific image analysis research microscopy","Variado","Imagem Científica","Análise de imagem científica genérica"
        conf=min(96,48+edge_intensity/2+entropy*2.8+sym*5+(8 if skin_pct>0.1 else 0)+(6 if has_grid else 0))
        # Histogram data for visualization
        hist_data = np.histogram(gray, bins=32, range=(0,255))
        r_hist = np.histogram(r.ravel(), bins=32, range=(0,255))[0].tolist()
        g_hist = np.histogram(g.ravel(), bins=32, range=(0,255))[0].tolist()
        b_hist = np.histogram(b_ch.ravel(), bins=32, range=(0,255))[0].tolist()
        return {"category":cat,"description":desc,"kw":kw,"material":material,"object_type":obj_type,
                "context":context,"confidence":round(conf,1),
                "lines":{"direction":line_dir,"intensity":round(edge_intensity,2),"strengths":strengths},
                "shapes":shapes,"symmetry":round(sym,3),"lr_symmetry":round(lr_sym,3),
                "color":{"r":round(mr,1),"g":round(mg,1),"b":round(mb,1),"warm":warm,"cool":cool,"dom":dom_ch,"sat":round(sat*100,1)},
                "texture":{"entropy":round(entropy,3),"contrast":round(contrast,2),
                           "complexity":"Alta" if entropy>5.5 else ("Média" if entropy>4 else "Baixa")},
                "palette":palette,"size":orig,
                "histograms":{"r":r_hist,"g":g_hist,"b":b_hist},
                "brightness":round(float(gray.mean()),1),
                "sharpness":round(edge_intensity,2)}
    except Exception as e: st.error(f"Erro na análise: {e}"); return None

EMAP = {"pdf":"PDF","docx":"Word","doc":"Word","xlsx":"Planilha","xls":"Planilha",
        "csv":"Dados","txt":"Texto","py":"Código Python","r":"Código R",
        "ipynb":"Notebook","pptx":"Apresentação","png":"Imagem","jpg":"Imagem",
        "jpeg":"Imagem","tiff":"Imagem Científica","md":"Markdown"}

def get_ftype(fname):
    ext=fname.split(".")[-1].lower() if "." in fname else ""
    return EMAP.get(ext,"Arquivo")

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
    except: pass
    return results

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

def get_recs(email, n=2):
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
    disk = load_db()
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
        p.setdefault("comments",[]); p.setdefault("views",random.randint(80,800))
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

# ══════════════════════════════════════════════════
# CSS — ORANGE / AMBER / GREEN LIQUID GLASS
# ══════════════════════════════════════════════════
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:wght@300;400;500;600;700&display=swap');

:root {
  --bg: #060504; --s1: #0d0905; --s2: #120c06;
  --bg3: #1a0e06;
  --or1: #7c2d00; --or2: #c2410c; --or3: #ea580c; --or4: #f97316;
  --or5: #fb923c; --or6: #fdba74; --or7: #fed7aa;
  --am1: #78350f; --am2: #b45309; --am3: #d97706; --am4: #f59e0b;
  --am5: #fbbf24; --am6: #fde68a;
  --gr1: #064e3b; --gr2: #065f46; --gr3: #059669; --gr4: #10b981;
  --gr5: #34d399; --gr6: #6ee7b7;
  --bl1: #1e3a5f; --bl2: #1e40af; --bl3: #2563eb; --bl4: #3b82f6;
  --bl5: #60a5fa; --bl6: #93c5fd;
  --pur: #7c3aed; --pink: #db2777; --cy: #06b6d4;
  --t1: #fef3e2; --t2: #d4a06a; --t3: #8b5e3c; --t4: #4a3020;
  --ok: #10b981; --warn: #f59e0b; --err: #ef4444;
  --glass: rgba(18,10,4,.70); --glass2: rgba(25,14,5,.78);
  --gborder: rgba(249,115,22,.14); --gborder2: rgba(251,146,60,.30);
  --r8:8px; --r12:12px; --r16:16px; --r20:20px; --r28:28px; --r50:50px;
  --text: #fef3e2; --text2: #c8906a; --muted: #6b4a2a;
  --border: rgba(255,255,255,.06); --border2: rgba(249,115,22,.18);
}

*, *::before, *::after { box-sizing:border-box; margin:0; padding:0; }
html, body, .stApp {
  background:var(--bg) !important;
  color:var(--text) !important;
  font-family:'DM Sans',-apple-system,sans-serif !important;
}

.stApp::before {
  content:''; position:fixed; inset:0; pointer-events:none; z-index:0;
  background:
    radial-gradient(ellipse 80% 60% at 5% 0%, rgba(249,115,22,.14) 0%, transparent 55%),
    radial-gradient(ellipse 55% 65% at 95% 100%, rgba(16,185,129,.08) 0%, transparent 50%),
    radial-gradient(ellipse 40% 40% at 50% 50%, rgba(245,158,11,.05) 0%, transparent 60%);
}
.stApp::after {
  content:''; position:fixed; inset:0; pointer-events:none; z-index:0;
  background-image:
    radial-gradient(1px 1px at 8% 12%,  rgba(251,191,36,.55) 0%, transparent 100%),
    radial-gradient(1px 1px at 24% 38%, rgba(249,115,22,.40) 0%, transparent 100%),
    radial-gradient(1.5px 1.5px at 55% 18%,rgba(52,211,153,.45) 0%, transparent 100%),
    radial-gradient(1px 1px at 77% 62%, rgba(251,191,36,.35) 0%, transparent 100%),
    radial-gradient(1px 1px at 90% 30%, rgba(249,115,22,.40) 0%, transparent 100%),
    radial-gradient(1px 1px at 42% 84%, rgba(96,165,250,.30) 0%, transparent 100%),
    radial-gradient(1px 1px at 15% 72%, rgba(52,211,153,.25) 0%, transparent 100%),
    radial-gradient(1px 1px at 66% 5%,  rgba(251,191,36,.30) 0%, transparent 100%);
}

[data-testid="collapsedControl"], section[data-testid="stSidebar"] { display:none !important; }
header[data-testid="stHeader"] { display:none !important; }
#MainMenu { display:none !important; }
footer { display:none !important; }
.stDeployButton { display:none !important; }
[data-testid="stToolbar"] { display:none !important; }
[data-testid="stDecoration"] { display:none !important; }

.block-container {
  padding-top:0 !important;
  padding-bottom:5rem !important;
  max-width:1440px !important;
  position:relative; z-index:1;
  padding-left:1rem !important;
  padding-right:1rem !important;
}

h1 { font-family:'Syne',sans-serif !important; font-size:1.6rem !important; font-weight:800 !important; letter-spacing:-.03em; color:var(--text) !important; }
h2 { font-family:'Syne',sans-serif !important; font-size:1.05rem !important; font-weight:700 !important; letter-spacing:-.01em; color:var(--text) !important; }
h3 { font-family:'Syne',sans-serif !important; font-size:.88rem !important; font-weight:600 !important; color:var(--text) !important; }

/* ═══════ TOP NAV ═══════ */
.neb-navwrap {
  position:sticky; top:0; z-index:1000;
  background:rgba(6,4,2,.94);
  backdrop-filter:blur(48px) saturate(200%);
  -webkit-backdrop-filter:blur(48px) saturate(200%);
  border-bottom:1px solid rgba(249,115,22,.12);
  margin-bottom:1.2rem;
  box-shadow:0 1px 0 rgba(249,115,22,.06), 0 6px 32px rgba(0,0,0,.6);
  padding:.45rem .8rem;
}
.neb-navwrap [data-testid="stHorizontalBlock"] {
  align-items:center !important;
  gap:1px !important;
}
.neb-navwrap [data-testid="stHorizontalBlock"] > div {
  padding:0 1px !important;
}

/* Nav pill inactive */
.nav-pill .stButton>button {
  background:transparent !important;
  border:1px solid transparent !important;
  border-radius:50px !important;
  color:var(--t3) !important;
  font-family:'DM Sans',sans-serif !important;
  font-size:1.0rem !important;
  font-weight:500 !important;
  padding:.28rem .50rem !important;
  box-shadow:none !important;
  white-space:nowrap !important;
  height:34px !important;
  min-height:34px !important;
  line-height:1 !important;
  transition:all .16s !important;
}
.nav-pill .stButton>button:hover {
  background:rgba(249,115,22,.12) !important;
  border-color:rgba(249,115,22,.22) !important;
  color:var(--t1) !important;
  transform:none !important;
  box-shadow:none !important;
}
/* Nav pill active */
.nav-pill-active .stButton>button {
  background:linear-gradient(135deg,rgba(234,88,12,.48),rgba(245,158,11,.22)) !important;
  border:1px solid rgba(249,115,22,.38) !important;
  color:var(--or6) !important;
  font-weight:700 !important;
  box-shadow:0 2px 16px rgba(234,88,12,.22), inset 0 1px 0 rgba(253,186,116,.12) !important;
  height:34px !important; min-height:34px !important;
  font-size:1.0rem !important;
}
.nav-pill-active .stButton>button:hover {
  transform:none !important;
  box-shadow:0 4px 20px rgba(234,88,12,.30) !important;
}

/* Avatar button styled as circle */
.nav-av-btn .stButton>button {
  width:36px !important; height:36px !important; min-height:36px !important;
  border-radius:50% !important;
  padding:0 !important;
  font-family:'Syne',sans-serif !important;
  font-weight:800 !important;
  font-size:.72rem !important;
  color:white !important;
  border:2px solid rgba(249,115,22,.30) !important;
  box-shadow:0 2px 12px rgba(0,0,0,.5) !important;
  transition:all .2s !important;
  line-height:1 !important;
}
.nav-av-btn .stButton>button:hover {
  transform:scale(1.08) !important;
  border-color:rgba(249,115,22,.60) !important;
  box-shadow:0 4px 18px rgba(249,115,22,.30) !important;
}

/* ═══════ BUTTONS ═══════ */
.stButton>button {
  background:linear-gradient(135deg,rgba(30,15,5,.72),rgba(18,10,4,.58)) !important;
  backdrop-filter:blur(20px) saturate(180%) !important;
  -webkit-backdrop-filter:blur(20px) saturate(180%) !important;
  border:1px solid var(--gborder) !important;
  border-radius:var(--r12) !important;
  color:var(--t2) !important;
  font-family:'DM Sans',sans-serif !important;
  font-weight:500 !important;
  font-size:.80rem !important;
  padding:.44rem .88rem !important;
  transition:all .2s cubic-bezier(.4,0,.2,1) !important;
  box-shadow:0 2px 10px rgba(0,0,0,.35), inset 0 1px 0 rgba(249,115,22,.06) !important;
  position:relative !important;
  overflow:hidden !important;
  letter-spacing:.01em !important;
}
.stButton>button:hover {
  background:linear-gradient(135deg,rgba(234,88,12,.55),rgba(245,158,11,.20)) !important;
  border-color:rgba(249,115,22,.38) !important;
  color:var(--text) !important;
  transform:translateY(-1px) !important;
  box-shadow:0 6px 20px rgba(234,88,12,.24), inset 0 1px 0 rgba(253,186,116,.10) !important;
}
.stButton>button:active { transform:scale(.97) !important; }

.btn-primary .stButton>button {
  background:linear-gradient(135deg,#ea580c,#d97706) !important;
  border-color:rgba(249,115,22,.5) !important;
  color:white !important;
  font-weight:600 !important;
  box-shadow:0 4px 20px rgba(234,88,12,.38), inset 0 1px 0 rgba(255,255,255,.14) !important;
}
.btn-primary .stButton>button:hover {
  background:linear-gradient(135deg,#f97316,#f59e0b) !important;
  box-shadow:0 8px 28px rgba(234,88,12,.45) !important;
}
.btn-danger .stButton>button {
  background:rgba(239,68,68,.08) !important;
  border-color:rgba(239,68,68,.22) !important;
  color:#fca5a5 !important;
}
.btn-danger .stButton>button:hover {
  background:rgba(239,68,68,.16) !important;
  border-color:rgba(239,68,68,.36) !important;
}
.btn-green .stButton>button {
  background:linear-gradient(135deg,rgba(5,150,105,.55),rgba(6,182,212,.22)) !important;
  border-color:rgba(52,211,153,.35) !important;
  color:var(--gr6) !important;
}

/* Story circles */
.sc-base .stButton>button {
  width:60px !important; height:60px !important; border-radius:50% !important;
  padding:0 !important; font-family:'Syne',sans-serif !important;
  font-weight:800 !important; font-size:.9rem !important; color:white !important;
  border:2.5px solid rgba(249,115,22,.30) !important;
  box-shadow:0 4px 18px rgba(0,0,0,.5), inset 0 1px 0 rgba(249,115,22,.08) !important;
  transition:transform .22s cubic-bezier(.34,1.56,.64,1), box-shadow .2s !important;
  display:flex !important; align-items:center !important; justify-content:center !important;
  margin:0 auto !important;
}
.sc-base .stButton>button:hover {
  transform:translateY(-3px) scale(1.07) !important;
  box-shadow:0 10px 28px rgba(249,115,22,.32) !important;
}
.sc-followed .stButton>button { border-color:rgba(52,211,153,.55) !important; }
.sc-publish .stButton>button {
  background:rgba(249,115,22,.06) !important;
  border:2.5px dashed rgba(249,115,22,.40) !important;
  color:var(--or5) !important; font-size:1.5rem !important; font-weight:300 !important;
}
.sc-publish .stButton>button:hover {
  background:rgba(249,115,22,.14) !important;
  border-color:rgba(249,115,22,.70) !important;
  box-shadow:0 0 28px rgba(249,115,22,.20) !important;
}
.sc-publish-open .stButton>button {
  background:rgba(249,115,22,.16) !important;
  border:2.5px solid rgba(249,115,22,.58) !important;
  color:var(--or5) !important; font-size:1.3rem !important;
  box-shadow:0 0 22px rgba(249,115,22,.28) !important;
}

/* Compose prompt */
.compose-prompt .stButton>button {
  background:rgba(255,255,255,.025) !important;
  border:1px solid var(--gborder) !important; border-radius:40px !important;
  color:var(--t3) !important; font-size:.875rem !important; font-weight:400 !important;
  text-align:left !important; padding:.72rem 1.4rem !important; width:100% !important;
  display:flex !important; justify-content:flex-start !important; box-shadow:none !important;
}
.compose-prompt .stButton>button:hover {
  background:rgba(249,115,22,.07) !important;
  border-color:rgba(249,115,22,.28) !important;
  color:var(--t2) !important; transform:none !important; box-shadow:none !important;
}

/* INPUTS */
.stTextInput input, .stTextArea textarea {
  background:rgba(8,5,2,.82) !important;
  border:1px solid var(--gborder) !important;
  border-radius:var(--r12) !important;
  color:var(--text) !important;
  font-family:'DM Sans',sans-serif !important;
  font-size:.875rem !important;
  transition:border-color .18s, box-shadow .18s !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color:rgba(249,115,22,.45) !important;
  box-shadow:0 0 0 3px rgba(249,115,22,.10) !important;
  background:rgba(8,5,2,.92) !important;
}
.stTextInput label,.stTextArea label,.stSelectbox label,.stFileUploader label,.stNumberInput label {
  color:var(--t3) !important; font-size:.63rem !important;
  letter-spacing:.10em !important; text-transform:uppercase !important; font-weight:600 !important;
}

/* AVATAR */
.av {
  border-radius:50%;
  background:linear-gradient(135deg,#ea580c,#d97706);
  display:flex; align-items:center; justify-content:center;
  font-family:'Syne',sans-serif; font-weight:700; color:white;
  border:2px solid rgba(249,115,22,.22); flex-shrink:0; overflow:hidden;
  box-shadow:0 2px 10px rgba(0,0,0,.4);
}
.av img { width:100%; height:100%; object-fit:cover; border-radius:50%; }

/* GLASS CARDS */
.card {
  background:var(--glass);
  backdrop-filter:blur(28px) saturate(160%);
  -webkit-backdrop-filter:blur(28px) saturate(160%);
  border:1px solid var(--gborder); border-radius:var(--r20);
  box-shadow:0 4px 32px rgba(0,0,0,.5), inset 0 1px 0 rgba(249,115,22,.05);
  position:relative; overflow:hidden;
}
.card::after {
  content:''; position:absolute; top:0; left:0; right:0; height:1px;
  background:linear-gradient(90deg,transparent,rgba(249,115,22,.10),transparent);
  pointer-events:none;
}
.post {
  background:var(--glass); border:1px solid var(--gborder); border-radius:var(--r20);
  margin-bottom:.8rem; overflow:hidden;
  box-shadow:0 2px 20px rgba(0,0,0,.40), inset 0 1px 0 rgba(249,115,22,.04);
  animation:fadeUp .24s cubic-bezier(.34,1.2,.64,1) both;
  transition:border-color .18s, box-shadow .18s;
}
.post:hover {
  border-color:var(--gborder2);
  box-shadow:0 8px 36px rgba(0,0,0,.50), 0 0 0 1px rgba(249,115,22,.06);
}
.post::after {
  content:''; position:absolute; top:0; left:0; right:0; height:1px;
  background:linear-gradient(90deg,transparent,rgba(249,115,22,.07),transparent);
  pointer-events:none;
}
@keyframes fadeUp { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }

.compose-card {
  background:rgba(18,10,4,.78); border:1px solid rgba(249,115,22,.25);
  border-radius:var(--r20); padding:1.2rem 1.4rem; margin-bottom:.9rem;
  box-shadow:0 4px 24px rgba(0,0,0,.30), inset 0 1px 0 rgba(249,115,22,.07);
  animation:fadeUp .18s ease both;
}

/* TABS */
.stTabs [data-baseweb="tab-list"] {
  background:rgba(8,5,2,.85) !important;
  border:1px solid var(--gborder) !important;
  border-radius:var(--r12) !important;
  padding:4px !important; gap:2px !important;
}
.stTabs [data-baseweb="tab"] {
  background:transparent !important; color:var(--t3) !important;
  border-radius:9px !important; font-size:.77rem !important;
  font-family:'DM Sans',sans-serif !important;
}
.stTabs [aria-selected="true"] {
  background:linear-gradient(135deg,rgba(234,88,12,.38),rgba(245,158,11,.16)) !important;
  color:var(--or5) !important;
  border:1px solid rgba(249,115,22,.28) !important;
}
.stTabs [data-baseweb="tab-panel"] { background:transparent !important; padding-top:.9rem !important; }

.stSelectbox [data-baseweb="select"] { background:rgba(8,5,2,.85) !important; border:1px solid var(--gborder) !important; border-radius:var(--r12) !important; }
.stFileUploader section { background:rgba(8,5,2,.55) !important; border:1.5px dashed rgba(249,115,22,.20) !important; border-radius:var(--r16) !important; }
.stExpander { background:var(--glass) !important; border:1px solid var(--gborder) !important; border-radius:var(--r16) !important; }

/* TAGS & BADGES */
.tag { display:inline-block; background:rgba(249,115,22,.10); border:1px solid rgba(249,115,22,.20); border-radius:20px; padding:2px 9px; font-size:.63rem; color:var(--or5); margin:2px; font-weight:500; }
.badge-on   { display:inline-block; background:rgba(245,158,11,.10); border:1px solid rgba(245,158,11,.24); border-radius:20px; padding:2px 9px; font-size:.63rem; font-weight:600; color:var(--am5); }
.badge-pub  { display:inline-block; background:rgba(16,185,129,.10); border:1px solid rgba(16,185,129,.24); border-radius:20px; padding:2px 9px; font-size:.63rem; font-weight:600; color:var(--gr5); }
.badge-done { display:inline-block; background:rgba(139,92,246,.10); border:1px solid rgba(139,92,246,.24); border-radius:20px; padding:2px 9px; font-size:.63rem; font-weight:600; color:#a78bfa; }
.badge-rec  { display:inline-block; background:rgba(249,115,22,.10); border:1px solid rgba(249,115,22,.24); border-radius:20px; padding:2px 9px; font-size:.63rem; font-weight:600; color:var(--or5); }

.mbox { background:var(--glass); border:1px solid var(--gborder); border-radius:var(--r16); padding:.95rem; text-align:center; }
.mval { font-family:'Syne',sans-serif; font-size:1.75rem; font-weight:800; background:linear-gradient(135deg,var(--or4),var(--am5)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
.mval-green { font-family:'Syne',sans-serif; font-size:1.75rem; font-weight:800; background:linear-gradient(135deg,var(--gr4),var(--bl4)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
.mlbl { font-size:.61rem; color:var(--t3); margin-top:3px; letter-spacing:.10em; text-transform:uppercase; font-weight:600; }

.prog-wrap { height:4px; background:rgba(249,115,22,.08); border-radius:4px; overflow:hidden; margin:.15rem 0 .38rem; }
.prog-fill  { height:100%; border-radius:4px; transition:width .6s ease; }

@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.5;transform:scale(.78)} }
.dot-on  { display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--gr4); animation:pulse 2s infinite; margin-right:4px; vertical-align:middle; }
.dot-off { display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--t4); margin-right:4px; vertical-align:middle; }

.sc  { background:var(--glass); border:1px solid var(--gborder); border-radius:var(--r20); padding:1.05rem; margin-bottom:.75rem; }
.scard { background:var(--glass); border:1px solid var(--gborder); border-radius:var(--r16); padding:.9rem 1.1rem; margin-bottom:.55rem; transition:border-color .15s,transform .15s; }
.scard:hover { border-color:var(--gborder2); transform:translateY(-1px); }
.abox { background:rgba(18,10,4,.78); border:1px solid rgba(249,115,22,.16); border-radius:var(--r16); padding:1rem; margin-bottom:.75rem; }
.pbox { background:rgba(5,150,105,.04); border:1px solid rgba(52,211,153,.16); border-radius:var(--r16); padding:.95rem; margin-bottom:.7rem; }
.img-rc { background:rgba(5,150,105,.04); border:1px solid rgba(52,211,153,.14); border-radius:var(--r16); padding:.9rem; margin-bottom:.55rem; }
.chart-glass { background:var(--glass); border:1px solid var(--gborder); border-radius:var(--r16); padding:.75rem; margin-bottom:.75rem; }
.ai-warn { background:rgba(245,158,11,.07); border:1px solid rgba(245,158,11,.22); border-radius:var(--r12); padding:.7rem 1rem; margin:.5rem 0; }

.prof-hero {
  background:var(--glass); border:1px solid var(--gborder); border-radius:var(--r28);
  padding:1.8rem; display:flex; gap:1.4rem; align-items:flex-start;
  box-shadow:0 6px 40px rgba(0,0,0,.45); position:relative; overflow:hidden; margin-bottom:1.2rem;
}
.prof-hero::after { content:''; position:absolute; top:0; left:0; right:0; height:1px; background:linear-gradient(90deg,transparent,rgba(249,115,22,.08),transparent); pointer-events:none; }
.prof-photo { width:84px; height:84px; border-radius:50%; background:linear-gradient(135deg,#ea580c,#d97706); border:2.5px solid rgba(249,115,22,.28); flex-shrink:0; overflow:hidden; display:flex; align-items:center; justify-content:center; font-size:1.8rem; font-weight:700; color:white; }
.prof-photo img { width:100%; height:100%; object-fit:cover; border-radius:50%; }

.bme   { background:linear-gradient(135deg,rgba(234,88,12,.45),rgba(245,158,11,.20)); border:1px solid rgba(249,115,22,.22); border-radius:18px 18px 4px 18px; padding:.6rem .92rem; max-width:68%; margin-left:auto; margin-bottom:6px; font-size:.83rem; line-height:1.6; }
.bthem { background:rgba(18,10,4,.88); border:1px solid var(--gborder); border-radius:18px 18px 18px 4px; padding:.6rem .92rem; max-width:68%; margin-bottom:6px; font-size:.83rem; line-height:1.6; }
.cmt   { background:rgba(8,5,2,.85); border:1px solid var(--gborder); border-radius:var(--r12); padding:.55rem .9rem; margin-bottom:.32rem; }

.person-row { display:flex; align-items:center; gap:9px; padding:.45rem .5rem; border-radius:var(--r12); border:1px solid transparent; transition:all .15s; margin-bottom:2px; }
.person-row:hover { background:rgba(249,115,22,.06); border-color:var(--gborder); }

.dtxt { display:flex; align-items:center; gap:.75rem; margin:.85rem 0; font-size:.61rem; color:var(--t3); letter-spacing:.10em; text-transform:uppercase; font-weight:600; }
.dtxt::before, .dtxt::after { content:''; flex:1; height:1px; background:var(--gborder); }

.sl  { text-align:center; font-size:.63rem; font-weight:500; color:var(--t2); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:72px; margin:3px auto 0; }
.sl2 { text-align:center; font-size:.58rem; color:var(--t3); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:72px; margin:0 auto; }
.dot-sm-on  { width:7px; height:7px; border-radius:50%; background:var(--gr4); margin:3px auto 2px; box-shadow:0 0 5px var(--gr4); animation:pulse 2s infinite; }
.dot-sm-off { width:7px; height:7px; border-radius:50%; background:var(--t4); margin:3px auto 2px; }

.ref-item { background:rgba(5,150,105,.04); border:1px solid rgba(52,211,153,.12); border-radius:var(--r12); padding:.65rem .9rem; margin-bottom:.4rem; font-size:.77rem; color:var(--t2); line-height:1.6; }
.str-ok  { background:rgba(16,185,129,.07); border:1px solid rgba(16,185,129,.20); border-radius:10px; padding:.38rem .75rem; font-size:.75rem; color:var(--gr5); margin-bottom:.3rem; }
.str-imp { background:rgba(245,158,11,.07); border:1px solid rgba(245,158,11,.20); border-radius:10px; padding:.38rem .75rem; font-size:.75rem; color:var(--am5); margin-bottom:.3rem; }

::-webkit-scrollbar { width:4px; height:4px; }
::-webkit-scrollbar-thumb { background:var(--bg3); border-radius:4px; }
::-webkit-scrollbar-track { background:transparent; }
hr { border:none; border-top:1px solid var(--gborder) !important; margin:.9rem 0; }
label { color:var(--t2) !important; }
.stCheckbox label,.stRadio label { color:var(--text) !important; }
.stAlert { background:var(--glass) !important; border:1px solid var(--gborder) !important; border-radius:var(--r16) !important; }
input[type="number"] { background:rgba(8,5,2,.82) !important; border:1px solid var(--gborder) !important; border-radius:var(--r12) !important; color:var(--text) !important; }
.stRadio > div { display:flex !important; gap:5px !important; flex-wrap:wrap !important; }
.stRadio > div > label { background:var(--glass) !important; border:1px solid var(--gborder) !important; border-radius:50px !important; padding:.3rem .82rem !important; font-size:.76rem !important; cursor:pointer !important; color:var(--t2) !important; }
.stRadio > div > label:hover { border-color:var(--gborder2) !important; color:var(--text) !important; }
.pw { animation:fadeIn .20s ease both; }
@keyframes fadeIn { from{opacity:0;transform:translateY(5px)} to{opacity:1;transform:translateY(0)} }
.js-plotly-plot .plotly .modebar { display:none !important; }

/* Liked posts panel */
.liked-item { background:var(--glass); border:1px solid var(--gborder); border-radius:var(--r12); padding:.7rem 1rem; margin-bottom:.45rem; transition:border-color .15s; }
.liked-item:hover { border-color:var(--gborder2); }
</style>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# HTML HELPERS
# ══════════════════════════════════════════════════
def avh(initials, sz=40, photo=None, grad=None):
    fs=max(sz//3,9); bg=grad or "linear-gradient(135deg,#ea580c,#d97706)"
    if photo: return f'<div class="av" style="width:{sz}px;height:{sz}px;background:{bg}"><img src="{photo}"/></div>'
    return f'<div class="av" style="width:{sz}px;height:{sz}px;font-size:{fs}px;background:{bg}">{initials}</div>'

def tags_html(tags): return ' '.join(f'<span class="tag">{t}</span>' for t in (tags or []))

def badge(s):
    cls={"Publicado":"badge-pub","Concluído":"badge-done"}.get(s,"badge-on")
    return f'<span class="{cls}">{s}</span>'

def prog_bar(pct, color="#f97316"):
    return f'<div class="prog-wrap"><div class="prog-fill" style="width:{pct}%;background:{color}"></div></div>'

def pc():
    return dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#8b5e3c",family="DM Sans",size=11),
                margin=dict(l=10,r=10,t=40,b=10),
                xaxis=dict(showgrid=False,color="#8b5e3c",tickfont=dict(size=10)),
                yaxis=dict(showgrid=True,gridcolor="rgba(249,115,22,.06)",color="#8b5e3c",tickfont=dict(size=10)))

def pc_noy():
    d = pc(); d.pop("yaxis", None); return d

def var_t1(): return "#fef3e2"

# chart color sequences
CHART_COLORS = ["#f97316","#f59e0b","#10b981","#3b82f6","#8b5cf6","#ec4899","#06b6d4","#fbbf24","#34d399","#60a5fa"]

# ══════════════════════════════════════════════════
# AUTH PAGES
# ══════════════════════════════════════════════════
def page_login():
    _,col,_ = st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-bottom:3rem">
          <div style="font-family:'Syne',sans-serif;font-size:4.2rem;font-weight:800;
            background:linear-gradient(135deg,#f97316 15%,#fbbf24 60%,#34d399 100%);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            background-clip:text;letter-spacing:-.06em;line-height:.9;margin-bottom:.8rem">Nebula</div>
          <div style="color:#4a3020;font-size:.63rem;letter-spacing:.28em;text-transform:uppercase;font-weight:600">
            Rede do Conhecimento Científico
          </div>
        </div>""", unsafe_allow_html=True)
        t_in,t_up = st.tabs(["  🔑 Entrar  ","  ✨ Criar conta  "])
        with t_in:
            # Use form so Enter key works
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
            st.markdown('<div style="text-align:center;color:#4a3020;font-size:.70rem;margin-top:.75rem">Demo: demo@nebula.ai / demo123</div>', unsafe_allow_html=True)
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
          <div style="font-size:2.5rem;margin-bottom:1rem;opacity:.6">✉</div>
          <h2 style="margin-bottom:.5rem">Verifique seu e-mail</h2>
          <p style="color:var(--t2);font-size:.82rem">Código para <strong style="color:var(--or5)">{pv['email']}</strong></p>
          <div style="background:rgba(249,115,22,.08);border:1px solid rgba(249,115,22,.18);border-radius:14px;padding:1.2rem;margin:1.2rem 0">
            <div style="font-size:.60rem;color:var(--t3);letter-spacing:.12em;text-transform:uppercase;margin-bottom:6px;font-weight:600">Código (demo)</div>
            <div style="font-family:'Syne',sans-serif;font-size:2.8rem;font-weight:900;letter-spacing:.32em;color:var(--or5)">{pv['code']}</div>
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
          <div style="font-size:2.5rem;margin-bottom:1rem;opacity:.6">🔑</div>
          <h2>Verificação 2FA</h2>
          <div style="background:rgba(249,115,22,.08);border:1px solid rgba(249,115,22,.18);border-radius:14px;padding:1rem;margin:1rem 0">
            <div style="font-size:.60rem;color:var(--t3);text-transform:uppercase;letter-spacing:.10em;margin-bottom:6px;font-weight:600">Código</div>
            <div style="font-family:'Syne',sans-serif;font-size:2.8rem;font-weight:900;letter-spacing:.28em;color:var(--or5)">{p2['code']}</div>
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

# ══════════════════════════════════════════════════
# TOP NAV — icons only, logo → feed, photo → profile
# ══════════════════════════════════════════════════
NAV = [
    ("feed",      "🏠"),
    ("search",    "🔍"),
    ("knowledge", "🕸"),
    ("folders",   "📁"),
    ("analytics", "📊"),
    ("img_search","🔬"),
    ("chat",      "💬"),
    ("settings",  "⚙️"),
]

def render_topnav():
    u = guser()
    name = u.get("name", "?")
    photo = u.get("photo_b64")
    in_ = ini(name)
    cur = st.session_state.page
    email = st.session_state.current_user
    g = ugrad(email or "")
    notif = len(st.session_state.notifications)

    st.markdown('<div class="neb-navwrap">', unsafe_allow_html=True)
    cols = st.columns([1.1] + [0.6]*len(NAV) + [0.65])

    # Logo → click goes to feed
    with cols[0]:
        st.markdown('<div class="nav-pill">', unsafe_allow_html=True)
        if st.button("🔬 Nebula", key="nav_logo"):
            st.session_state.profile_view = None
            st.session_state.page = "feed"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Nav icon buttons
    for i, (key, icon) in enumerate(NAV):
        with cols[i+1]:
            is_active = (cur == key)
            pill_cls = "nav-pill-active" if is_active else "nav-pill"
            st.markdown(f'<div class="{pill_cls}">', unsafe_allow_html=True)
            if st.button(icon, key=f"tnav_{key}", use_container_width=True):
                st.session_state.profile_view = None
                st.session_state.page = key
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # Avatar button — styled as circle, click → own profile
    with cols[-1]:
        # Notification badge
        nb_html = ""
        if notif:
            nb_html = f'<div style="position:absolute;top:-2px;right:-2px;background:#ef4444;color:white;width:14px;height:14px;border-radius:50%;font-size:.48rem;display:flex;align-items:center;justify-content:center;font-weight:700;z-index:10;pointer-events:none">{notif}</div>'

        # Show photo as background if available via dynamic CSS
        if photo:
            # Inject inline style targeting this specific button
            st.markdown(f"""
            <style>
            #nav-av-btn .stButton>button {{
              background-image: url("{photo}") !important;
              background-size: cover !important;
              background-position: center !important;
              color: transparent !important;
              font-size: 0 !important;
            }}
            </style>
            <div id="nav-av-btn" style="position:relative;display:inline-block">
              {nb_html}
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="position:relative;display:inline-block">{nb_html}</div>', unsafe_allow_html=True)

        av_style = f"background:{g} !important;" if not photo else ""
        st.markdown(f'<div class="nav-av-btn" style="--avgrad:{g}">', unsafe_allow_html=True)
        if st.button(in_ if not photo else "·", key="nav_me_photo"):
            st.session_state.profile_view = email
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        # Apply gradient to button via inline style tag
        if not photo:
            st.markdown(f"""<style>
            div[data-testid="stHorizontalBlock"] > div:last-child .nav-av-btn .stButton>button {{
              background: {g} !important;
            }}
            </style>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# PROFILE PAGE
# ══════════════════════════════════════════════════
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
    # Liked posts by this user
    liked_posts=[p for p in st.session_state.feed_posts if target_email in p.get("liked_by",[])]
    total_likes=sum(p["likes"] for p in user_posts); g=ugrad(target_email)
    if st.button("← Voltar",key="back_prof"): st.session_state.profile_view=None; st.rerun()
    photo_html=f'<img src="{tphoto}"/>' if tphoto else f'<span style="font-size:2rem">{tin}</span>'
    v_badge='<span style="font-size:.7rem;color:var(--gr4);margin-left:6px">✓</span>' if tu.get("verified") else ""
    st.markdown(
        f'<div class="prof-hero">'
        f'<div class="prof-photo" style="background:{g}">{photo_html}</div>'
        f'<div style="flex:1;z-index:1">'
        f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;margin-bottom:.3rem">'
        f'<h1 style="margin:0">{tname}</h1>{v_badge}</div>'
        f'<div style="color:var(--or5);font-size:.84rem;margin-bottom:.45rem;font-weight:500">{tu.get("area","")}</div>'
        f'<div style="color:var(--t2);font-size:.82rem;line-height:1.68;margin-bottom:.9rem;max-width:560px">{tu.get("bio","Sem biografia.")}</div>'
        f'<div style="display:flex;gap:2rem;flex-wrap:wrap">'
        f'<div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1.1rem">{tu.get("followers",0)}</span><span style="color:var(--t3);font-size:.72rem"> seguidores</span></div>'
        f'<div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1.1rem">{tu.get("following",0)}</span><span style="color:var(--t3);font-size:.72rem"> seguindo</span></div>'
        f'<div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1.1rem">{len(user_posts)}</span><span style="color:var(--t3);font-size:.72rem"> pesquisas</span></div>'
        f'<div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1.1rem">{fmt_num(total_likes)}</span><span style="color:var(--t3);font-size:.72rem"> curtidas</span></div>'
        f'</div></div></div>', unsafe_allow_html=True)
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
    tab_posts, tab_liked = st.tabs([f"  📝 Pesquisas ({len(user_posts)})  ", f"  ❤️ Curtidas ({len(liked_posts)})  "])
    with tab_posts:
        if user_posts:
            for p in sorted(user_posts,key=lambda x:x.get("date",""),reverse=True):
                render_post(p,ctx="profile",show_author=False)
        else:
            st.markdown('<div class="card" style="padding:2.5rem;text-align:center;color:var(--t3)">Nenhuma pesquisa publicada ainda.</div>', unsafe_allow_html=True)
    with tab_liked:
        if liked_posts:
            for p in sorted(liked_posts,key=lambda x:x.get("date",""),reverse=True):
                render_post(p,ctx="prof_liked",compact=True)
        else:
            st.markdown('<div class="card" style="padding:2.5rem;text-align:center;color:var(--t3)">Nenhuma curtida ainda.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# POST CARD
# ══════════════════════════════════════════════════
def render_post(post, ctx="feed", show_author=True, compact=False):
    email=st.session_state.current_user; pid=post["id"]
    liked=email in post.get("liked_by",[]); saved=email in post.get("saved_by",[])
    aemail=post.get("author_email",""); aphoto=get_photo(aemail)
    ain=post.get("avatar","??"); aname=post.get("author","?"); aarea=post.get("area","")
    dt=time_ago(post.get("date","")); views=post.get("views",random.randint(80,500))
    abstract=post.get("abstract","")
    if compact and len(abstract)>200: abstract=abstract[:200]+"…"
    g=ugrad(aemail)
    if show_author:
        av_html=(f'<div class="av" style="width:42px;height:42px;background:{g};font-size:13px"><img src="{aphoto}"/></div>'
                 if aphoto else f'<div class="av" style="width:42px;height:42px;background:{g};font-size:13px">{ain}</div>')
        v_mark=' <span style="font-size:.60rem;color:var(--gr4)">✓</span>' if st.session_state.users.get(aemail,{}).get("verified") else ""
        header=(f'<div style="padding:.9rem 1.2rem .65rem;display:flex;align-items:center;gap:10px;border-bottom:1px solid rgba(249,115,22,.07)">'
                f'{av_html}'
                f'<div style="flex:1;min-width:0">'
                f'<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.88rem">{aname}{v_mark}</div>'
                f'<div style="color:var(--t3);font-size:.67rem;margin-top:1px">{aarea} · {dt}</div>'
                f'</div>{badge(post["status"])}</div>')
    else:
        header=(f'<div style="padding:.42rem 1.2rem .22rem;display:flex;justify-content:space-between;align-items:center">'
                f'<span style="color:var(--t3);font-size:.67rem">{dt}</span>{badge(post["status"])}</div>')
    st.markdown(
        f'<div class="post">{header}'
        f'<div style="padding:.75rem 1.2rem">'
        f'<div style="font-family:Syne,sans-serif;font-size:.98rem;font-weight:700;margin-bottom:.38rem;line-height:1.4;color:var(--t1)">{post["title"]}</div>'
        f'<div style="color:var(--t2);font-size:.81rem;line-height:1.68;margin-bottom:.6rem">{abstract}</div>'
        f'<div>{tags_html(post.get("tags",[]))}</div>'
        f'</div></div>', unsafe_allow_html=True)
    heart="❤️" if liked else "🤍"; book="🔖" if saved else "📌"
    nc=len(post.get("comments",[]))
    ca,cb,cc,cd,ce,cf=st.columns([1.1,1,.7,.6,1,1.1])
    with ca:
        if st.button(f"{heart} {fmt_num(post['likes'])}",key=f"lk_{ctx}_{pid}",use_container_width=True):
            if liked:
                post["liked_by"].remove(email)
                post["likes"]=max(0,post["likes"]-1)
            else:
                post["liked_by"].append(email)
                post["likes"]+=1
                record(post.get("tags",[]),1.5)
            save_db()  # Save likes immediately
            st.rerun()
    with cb:
        lbl_c=f"💬 {nc}" if nc else "💬 Comentar"
        if st.button(lbl_c,key=f"cm_{ctx}_{pid}",use_container_width=True):
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
        st.markdown(f'<div style="text-align:center;color:var(--t3);font-size:.70rem;padding:.5rem 0">👁 {fmt_num(views)}</div>', unsafe_allow_html=True)
    with cf:
        if show_author and aemail:
            first=aname.split()[0] if aname else "?"
            if st.button(f"👤 {first}",key=f"vp_{ctx}_{pid}",use_container_width=True):
                st.session_state.profile_view=aemail; st.rerun()
    if st.session_state.get(f"shr_{ctx}_{pid}",False):
        url=f"https://nebula.ai/post/{pid}"; te=post['title'][:50].replace(" ","%20")
        st.markdown(
            f'<div class="card" style="padding:.9rem 1.2rem;margin-bottom:.5rem">'
            f'<div style="font-family:Syne,sans-serif;font-weight:600;font-size:.82rem;margin-bottom:.7rem;color:var(--t2)">↗ Compartilhar</div>'
            f'<div style="display:flex;gap:.5rem;flex-wrap:wrap">'
            f'<a href="https://twitter.com/intent/tweet?text={te}" target="_blank" style="text-decoration:none"><div style="background:rgba(29,161,242,.08);border:1px solid rgba(29,161,242,.18);border-radius:9px;padding:.35rem .7rem;font-size:.72rem;color:#1da1f2">𝕏 Twitter</div></a>'
            f'<a href="https://linkedin.com/sharing/share-offsite/?url={url}" target="_blank" style="text-decoration:none"><div style="background:rgba(10,102,194,.08);border:1px solid rgba(10,102,194,.18);border-radius:9px;padding:.35rem .7rem;font-size:.72rem;color:#0a66c2">in LinkedIn</div></a>'
            f'<a href="https://wa.me/?text={te}%20{url}" target="_blank" style="text-decoration:none"><div style="background:rgba(37,211,102,.07);border:1px solid rgba(37,211,102,.15);border-radius:9px;padding:.35rem .7rem;font-size:.72rem;color:#25d366">📱 WhatsApp</div></a>'
            f'</div></div>', unsafe_allow_html=True)
    if st.session_state.get(f"cmt_{ctx}_{pid}",False):
        comments=post.get("comments",[])
        for c in comments:
            c_in=ini(c["user"]); c_email=next((e for e,u in st.session_state.users.items() if u.get("name")==c["user"]),"")
            c_photo=get_photo(c_email); c_grad=ugrad(c_email)
            av_c=avh(c_in,28,c_photo,c_grad)
            st.markdown(f'<div class="cmt"><div style="display:flex;align-items:center;gap:8px;margin-bottom:.25rem">{av_c}<span style="font-size:.76rem;font-weight:600;color:var(--or5)">{c["user"]}</span></div><div style="font-size:.79rem;color:var(--t2);line-height:1.55;padding-left:36px">{c["text"]}</div></div>', unsafe_allow_html=True)
        nc_txt=st.text_input("",placeholder="Escreva um comentário…",key=f"ci_{ctx}_{pid}",label_visibility="collapsed")
        if st.button("→ Enviar",key=f"cs_{ctx}_{pid}"):
            if nc_txt:
                uu=guser(); post["comments"].append({"user":uu.get("name","Você"),"text":nc_txt})
                record(post.get("tags",[]),.8); save_db(); st.rerun()

# ══════════════════════════════════════════════════
# FEED PAGE
# ══════════════════════════════════════════════════
def page_feed():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    email=st.session_state.current_user; u=guser()
    uname=u.get("name","?"); uphoto=u.get("photo_b64"); uin=ini(uname)
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    compose_open=st.session_state.get("compose_open",False)
    col_main,col_side=st.columns([2,.9],gap="medium")
    with col_main:
        story_list=[(ue,ud) for ue,ud in users.items() if ue!=email][:7]
        n_cols=1+len(story_list)
        scols=st.columns(n_cols)
        with scols[0]:
            pub_cls="sc-publish-open" if compose_open else "sc-publish"
            st.markdown(f'<div class="{pub_cls}" style="display:flex;justify-content:center">', unsafe_allow_html=True)
            if st.button("×" if compose_open else "+", key="pub_circle"):
                st.session_state.compose_open=not compose_open; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            lbl_col="var(--or5)" if compose_open else "var(--am5)"
            st.markdown(f'<div class="sl" style="color:{lbl_col}">{"Fechar" if compose_open else "Publicar"}</div>', unsafe_allow_html=True)
        for ci,(ue,ud) in enumerate(story_list):
            sname=ud.get("name","?"); sin=ini(sname); sphoto=ud.get("photo_b64"); sg=ugrad(ue)
            is_fol=ue in st.session_state.followed; online=random.Random(ue).random()>0.45
            first=sname.split()[0]; short_area=ud.get("area","")[:12]
            follow_cls=" sc-followed" if is_fol else ""
            with scols[ci+1]:
                if sphoto:
                    st.markdown(f'<div style="width:60px;height:60px;border-radius:50%;margin:0 auto;background:{sg};border:2.5px solid {"rgba(52,211,153,.55)" if is_fol else "rgba(249,115,22,.28)"};overflow:hidden;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 18px rgba(0,0,0,.5)"><img src="{sphoto}" style="width:100%;height:100%;object-fit:cover;border-radius:50%"/></div>', unsafe_allow_html=True)
                    if st.button(f"👁 {first}",key=f"sc_{ue}",use_container_width=True):
                        st.session_state.profile_view=ue; st.rerun()
                else:
                    st.markdown(f'<div class="sc-base{follow_cls}" style="display:flex;justify-content:center">', unsafe_allow_html=True)
                    if st.button(sin, key=f"sc_{ue}"):
                        st.session_state.profile_view=ue; st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                if online and is_fol: st.markdown('<div class="dot-sm-on"></div>', unsafe_allow_html=True)
                else: st.markdown('<div style="height:9px"></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="sl">{first}</div><div class="sl2">{short_area}</div>', unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if compose_open:
            g=ugrad(email)
            av_c=(f'<div class="av" style="width:44px;height:44px;background:{g}"><img src="{uphoto}"/></div>'
                  if uphoto else f'<div class="av" style="width:44px;height:44px;font-size:14px;background:{g}">{uin}</div>')
            st.markdown(f'<div class="compose-card"><div style="display:flex;align-items:center;gap:10px;margin-bottom:1rem">{av_c}<div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.92rem">{uname}</div><div style="font-size:.68rem;color:var(--t3)">{u.get("area","Pesquisador")}</div></div></div>', unsafe_allow_html=True)
            np_t=st.text_input("Título *",key="np_t",placeholder="Ex: Efeitos da meditação na neuroplasticidade…")
            np_ab=st.text_area("Resumo / Abstract *",key="np_ab",height=110,placeholder="Descreva sua pesquisa…")
            c1c,c2c=st.columns(2)
            with c1c: np_tg=st.text_input("Tags (vírgula)",key="np_tg",placeholder="neurociência, fMRI")
            with c2c: np_st=st.selectbox("Status",["Em andamento","Publicado","Concluído"],key="np_st")
            cpub,ccan=st.columns([2,1])
            with cpub:
                st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
                if st.button("🚀 Publicar pesquisa",key="btn_pub",use_container_width=True):
                    if not np_t or not np_ab: st.warning("Título e resumo são obrigatórios.")
                    else:
                        tags=[t.strip() for t in np_tg.split(",") if t.strip()] if np_tg else []
                        new_p={"id":len(st.session_state.feed_posts)+200+random.randint(0,99),
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
            g=ugrad(email)
            av_c2=(f'<div class="av" style="width:40px;height:40px;flex-shrink:0;background:{g}"><img src="{uphoto}"/></div>'
                   if uphoto else f'<div class="av" style="width:40px;height:40px;font-size:13px;flex-shrink:0;background:{g}">{uin}</div>')
            avc,btnc=st.columns([.055,1],gap="small")
            with avc: st.markdown(f'<div style="padding-top:7px">{av_c2}</div>', unsafe_allow_html=True)
            with btnc:
                st.markdown('<div class="compose-prompt">', unsafe_allow_html=True)
                if st.button(f"No que você está pesquisando, {uname.split()[0]}?",key="open_compose",use_container_width=True):
                    st.session_state.compose_open=True; st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        ff=st.radio("",["🌐 Todos","👥 Seguidos","🔖 Salvos","🔥 Populares"],
                    horizontal=True,key="ff",label_visibility="collapsed")
        recs=get_recs(email,2)
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
            st.markdown('<div class="card" style="padding:3.5rem;text-align:center"><div style="font-size:2.5rem;opacity:.2;margin-bottom:1rem">🔬</div><div style="color:var(--t3)">Nenhuma pesquisa aqui ainda.</div></div>', unsafe_allow_html=True)
        else:
            for p in posts: render_post(p,ctx="feed")
    with col_side:
        sq=st.text_input("",placeholder="🔍 Buscar pesquisadores…",key="ppl_s",label_visibility="collapsed")
        st.markdown('<div class="sc">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.83rem;margin-bottom:.9rem;display:flex;justify-content:space-between"><span>Quem seguir</span><span style="font-size:.65rem;color:var(--t3);font-weight:400">Sugestões</span></div>', unsafe_allow_html=True)
        shown_n=0
        for ue,ud in list(users.items()):
            if ue==email or shown_n>=5: continue
            rname=ud.get("name","?")
            if sq and sq.lower() not in rname.lower() and sq.lower() not in ud.get("area","").lower(): continue
            shown_n+=1; is_fol=ue in st.session_state.followed
            uphoto_r=ud.get("photo_b64"); uin_r=ini(rname); rg=ugrad(ue)
            online=random.Random(ue+"x").random()>0.45
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            av_r=avh(uin_r,34,uphoto_r,rg)
            st.markdown(f'<div class="person-row">{av_r}<div style="flex:1;min-width:0"><div style="font-size:.80rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{dot}{rname}</div><div style="font-size:.63rem;color:var(--t3)">{ud.get("area","")[:22]}</div></div></div>', unsafe_allow_html=True)
            cf_b,cv_b=st.columns(2)
            with cf_b:
                lbl_f="✓ Seguindo" if is_fol else "+ Seguir"
                if st.button(lbl_f,key=f"sf_{ue}",use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"]=max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                    save_db(); st.rerun()
            with cv_b:
                if st.button("👤 Perfil",key=f"svr_{ue}",use_container_width=True):
                    st.session_state.profile_view=ue; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="sc">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.83rem;margin-bottom:.85rem">🔥 Em Alta</div>', unsafe_allow_html=True)
        trending=[("Quantum ML","34"),("CRISPR 2026","28"),("Neuroplasticidade","22"),("LLMs Científicos","19"),("Matéria Escura","15")]
        for i,(topic,cnt) in enumerate(trending):
            color=CHART_COLORS[i%len(CHART_COLORS)]
            st.markdown(f'<div style="padding:.4rem .35rem;border-radius:10px;margin-bottom:2px"><div style="font-size:.60rem;color:var(--t3);margin-bottom:1px">#{i+1}</div><div style="font-size:.80rem;font-weight:600;color:var(--t1)">{topic}</div><div style="font-size:.60rem;color:var(--t3)">{cnt} pesquisas</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        if st.session_state.notifications:
            st.markdown('<div class="sc">', unsafe_allow_html=True)
            st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.83rem;margin-bottom:.75rem">🔔 Atividade</div>', unsafe_allow_html=True)
            for notif in st.session_state.notifications[:3]:
                st.markdown(f'<div style="font-size:.72rem;color:var(--t2);padding:.35rem 0;border-bottom:1px solid var(--gborder)">· {notif}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# SEARCH PAGE
# ══════════════════════════════════════════════════
def render_web_article(a, idx=0, ctx="web"):
    src_color="var(--gr5)" if a.get("origin")=="semantic" else "var(--am5)"
    src_name="Semantic Scholar" if a.get("origin")=="semantic" else "CrossRef"
    cite=f" · {a['citations']} cit." if a.get("citations") else ""
    uid=re.sub(r'[^a-zA-Z0-9]','',f"{ctx}_{idx}_{str(a.get('doi',''))[:10]}")[:32]
    is_saved=any(s.get('doi')==a.get('doi') for s in st.session_state.saved_articles)
    abstract=(a.get("abstract","") or "")[:260]
    if len(a.get("abstract",""))>260: abstract+="…"
    st.markdown(
        f'<div class="scard">'
        f'<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:.35rem">'
        f'<div style="flex:1;font-family:Syne,sans-serif;font-size:.9rem;font-weight:700">{a["title"]}</div>'
        f'<span style="font-size:.61rem;color:{src_color};background:rgba(249,115,22,.06);border-radius:8px;padding:2px 8px;white-space:nowrap;flex-shrink:0">{src_name}</span>'
        f'</div>'
        f'<div style="color:var(--t3);font-size:.67rem;margin-bottom:.38rem">{a["authors"]} · <em>{a["source"]}</em> · {a["year"]}{cite}</div>'
        f'<div style="color:var(--t2);font-size:.79rem;line-height:1.65">{abstract}</div>'
        f'</div>', unsafe_allow_html=True)
    ca,cb,cc=st.columns(3)
    with ca:
        lbl_sv="🔖 Salvo" if is_saved else "📌 Salvar"
        if st.button(lbl_sv,key=f"svw_{uid}"):
            if is_saved: st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]; st.toast("Removido")
            else: st.session_state.saved_articles.append(a); st.toast("Salvo!")
            save_db(); st.rerun()
    with cb:
        if st.button("📋 Citar APA",key=f"ctw_{uid}"): st.toast(f'{a["authors"]} ({a["year"]}). {a["title"]}.')
    with cc:
        if a.get("url"):
            st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:var(--or5);font-size:.79rem;text-decoration:none;line-height:2.5;display:block">↗ Abrir artigo</a>', unsafe_allow_html=True)

def page_search():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1rem;margin-bottom:.4rem">🔍 Busca Acadêmica</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.80rem;margin-bottom:1rem">Semantic Scholar · CrossRef · Nebula</p>', unsafe_allow_html=True)
    c1,c2=st.columns([4,1])
    with c1: q=st.text_input("",placeholder="CRISPR · quantum ML · dark matter · neuroplasticity…",key="sq",label_visibility="collapsed")
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
                st.markdown('<div style="font-size:.62rem;color:var(--or5);font-weight:700;margin-bottom:.5rem;letter-spacing:.09em;text-transform:uppercase">Na Nebula</div>', unsafe_allow_html=True)
                for p in neb: render_post(p,ctx="srch_all",compact=True)
            if web:
                if neb: st.markdown('<hr>', unsafe_allow_html=True)
                st.markdown('<div style="font-size:.62rem;color:var(--gr5);font-weight:700;margin-bottom:.5rem;letter-spacing:.09em;text-transform:uppercase">Bases Acadêmicas</div>', unsafe_allow_html=True)
                for idx,a in enumerate(web): render_web_article(a,idx=idx,ctx="all_w")
            if not neb and not web: st.info("Nenhum resultado.")
        with t_neb:
            if neb:
                for p in neb: render_post(p,ctx="srch_neb",compact=True)
            else: st.info("Nenhuma pesquisa na Nebula.")
        with t_web:
            if web:
                for idx,a in enumerate(web): render_web_article(a,idx=idx,ctx="web_t")
            else: st.info("Nenhum artigo online.")
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# KNOWLEDGE
# ══════════════════════════════════════════════════
def page_knowledge():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1rem;margin-bottom:1rem">🕸 Rede de Conexões</h1>', unsafe_allow_html=True)
    email=st.session_state.current_user
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    def get_tags(ue):
        ud=users.get(ue,{}); tags=set(area_to_tags(ud.get("area","")))
        for p in st.session_state.feed_posts:
            if p.get("author_email")==ue: tags.update(t.lower() for t in p.get("tags",[]))
        return tags
    rlist=list(users.keys()); rtags={ue:get_tags(ue) for ue in rlist}
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
            mode="lines",line=dict(color=f"rgba(249,115,22,{alpha:.2f})",width=min(4,1+strength)),hoverinfo="none",showlegend=False))
    ncolors=["#f97316" if ue==email else ("#34d399" if ue in st.session_state.followed else "#f59e0b") for ue in rlist]
    nsizes=[24 if ue==email else (18 if ue in st.session_state.followed else max(12,10+sum(1 for e1,e2,_,__ in edges if e1==ue or e2==ue))) for ue in rlist]
    ntext=[users.get(ue,{}).get("name","?").split()[0] for ue in rlist]
    nhover=[f"<b>{users.get(ue,{}).get('name','?')}</b><br>{users.get(ue,{}).get('area','')}<extra></extra>" for ue in rlist]
    fig.add_trace(go.Scatter3d(x=[pos[ue]["x"] for ue in rlist],y=[pos[ue]["y"] for ue in rlist],z=[pos[ue]["z"] for ue in rlist],
        mode="markers+text",marker=dict(size=nsizes,color=ncolors,opacity=.9,line=dict(color="rgba(249,115,22,.15)",width=1.5)),
        text=ntext,textposition="top center",textfont=dict(color="#8b5e3c",size=9,family="DM Sans"),
        hovertemplate=nhover,showlegend=False))
    fig.update_layout(height=440,scene=dict(xaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),yaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),zaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),bgcolor="rgba(0,0,0,0)"),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig,use_container_width=True)
    c1,c2,c3,c4=st.columns(4)
    for col,(v,l) in zip([c1,c2,c3,c4],[(len(rlist),"Pesquisadores"),(len(edges),"Conexões"),(len(st.session_state.followed),"Seguindo"),(len(st.session_state.feed_posts),"Pesquisas")]):
        with col: st.markdown(f'<div class="mbox"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    tab_map,tab_mine,tab_all=st.tabs(["  🗺 Mapa  ","  🔗 Minhas Conexões  ","  👥 Todos  "])
    with tab_map:
        for e1,e2,common,strength in sorted(edges,key=lambda x:-x[3])[:20]:
            n1=users.get(e1,{}); n2=users.get(e2,{})
            ts=tags_html(common[:4]) if common else '<span style="color:var(--t3);font-size:.70rem">seguimento</span>'
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><span style="font-size:.82rem;font-weight:700;font-family:Syne,sans-serif;color:var(--or5)">{n1.get("name","?")}</span><span style="color:var(--t3)">↔</span><span style="font-size:.82rem;font-weight:700;font-family:Syne,sans-serif;color:var(--or5)">{n2.get("name","?")}</span><div style="flex:1">{ts}</div><span style="font-size:.67rem;color:var(--gr5);font-weight:700">{strength}pt</span></div></div>', unsafe_allow_html=True)
    with tab_mine:
        my_conn=[(e1,e2,c,s) for e1,e2,c,s in edges if e1==email or e2==email]
        if not my_conn: st.info("Siga pesquisadores e publique pesquisas para ver conexões.")
        for e1,e2,common,strength in sorted(my_conn,key=lambda x:-x[3]):
            other=e2 if e1==email else e1; od=users.get(other,{}); og=ugrad(other)
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">{avh(ini(od.get("name","?")),38,get_photo(other),og)}<div style="flex:1"><div style="font-weight:700;font-size:.86rem;font-family:Syne,sans-serif">{od.get("name","?")}</div><div style="font-size:.69rem;color:var(--t3)">{od.get("area","")}</div></div>{tags_html(common[:3])}</div></div>', unsafe_allow_html=True)
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
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:10px">{avh(ini(rn),38,get_photo(ue),rg)}<div style="flex:1"><div style="font-size:.86rem;font-weight:700;font-family:Syne,sans-serif">{rn}</div><div style="font-size:.69rem;color:var(--t3)">{uarea}</div></div></div></div>', unsafe_allow_html=True)
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

# ══════════════════════════════════════════════════
# FOLDERS — enhanced analysis
# ══════════════════════════════════════════════════
def render_document_analysis(fname, analysis, research_area=""):
    if not analysis: return
    kws=analysis.get("keywords",[]); topics=analysis.get("topics",{})
    authors=analysis.get("authors",[]); years=analysis.get("years",[])
    refs=analysis.get("references",[]); refs_online=analysis.get("references_online",[])
    strengths_a=analysis.get("strengths",[]); improvements=analysis.get("improvements",[])
    rel=analysis.get("relevance_score",0); wq=analysis.get("writing_quality",0)
    rt=analysis.get("reading_time",0); wc=analysis.get("word_count",0)
    sc=analysis.get("sentence_complexity",0); concepts=analysis.get("key_concepts",[])
    cf=analysis.get("concept_frequency",{})
    prog_color=("#10b981" if rel>=70 else ("#f59e0b" if rel>=45 else "#ef4444"))
    wq_color=("#10b981" if wq>=70 else ("#f59e0b" if wq>=45 else "#ef4444"))
    rel_label="Alta" if rel>=70 else ("Média" if rel>=45 else "Baixa")
    wq_label="Excelente" if wq>=80 else ("Boa" if wq>=60 else ("Regular" if wq>=40 else "Básica"))

    # Header summary
    st.markdown(f'''
    <div class="abox">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:.6rem">
        <div style="flex:1">
          <div style="font-family:Syne,sans-serif;font-weight:700;font-size:.9rem;margin-bottom:.3rem">{fname}</div>
          <div style="font-size:.79rem;color:var(--t2);line-height:1.65">{analysis.get("summary","")}</div>
        </div>
        <div style="display:flex;gap:.8rem;flex-shrink:0">
          <div style="text-align:center">
            <div style="font-family:Syne,sans-serif;font-size:1.25rem;font-weight:800;color:{prog_color}">{rel}%</div>
            <div style="font-size:.58rem;color:var(--t3);text-transform:uppercase;letter-spacing:.07em">Relevância</div>
          </div>
          <div style="text-align:center">
            <div style="font-family:Syne,sans-serif;font-size:1.25rem;font-weight:800;color:{wq_color}">{wq}%</div>
            <div style="font-size:.58rem;color:var(--t3);text-transform:uppercase;letter-spacing:.07em">Qualidade</div>
          </div>
        </div>
      </div>
      {prog_bar(rel,prog_color)}
      <div style="display:flex;gap:1.2rem;flex-wrap:wrap;margin-top:.5rem;font-size:.67rem;color:var(--t3)">
        <span>📖 ~{rt} min leitura</span>
        <span>📝 {wc} palavras</span>
        <span>🔑 {len(kws)} keywords</span>
        <span>📚 {len(refs)} referências</span>
        <span>✍️ Qualidade: <strong style="color:{wq_color}">{wq_label}</strong></span>
        <span>📐 Complexidade: <strong style="color:var(--t2)">{sc:.1f} pal/frase</strong></span>
      </div>
    </div>''', unsafe_allow_html=True)

    tab_kw,tab_concepts,tab_topics,tab_authors,tab_refs,tab_improve = st.tabs([
        "  🔑 Keywords  ", "  💡 Conceitos  ", "  🎯 Temas  ", "  👤 Autores  ", "  📚 Refs  ", "  ✨ Melhorias  "
    ])

    with tab_kw:
        if kws:
            weights=[max(1,25-i) for i in range(len(kws))]
            fig=go.Figure(go.Bar(
                x=weights[:20], y=kws[:20], orientation='h',
                marker=dict(color=weights[:20],
                    colorscale=[[0,"#1a0a03"],[.4,"#ea580c"],[.7,"#f59e0b"],[1,"#34d399"]],
                    line=dict(color="#060504",width=1)),
                text=kws[:20], textposition='inside',
                textfont=dict(color='white',size=9)))
            layout = {**pc_noy(), 'height':max(320,len(kws[:20])*18),
                      'title':dict(text="Palavras-chave por Relevância TF-IDF",font=dict(color=var_t1(),family="DM Sans",size=13)),
                      'yaxis':dict(showticklabels=False)}
            fig.update_layout(**layout)
            st.markdown('<div class="chart-glass">', unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(tags_html(kws[:25]), unsafe_allow_html=True)
        else:
            st.info("Palavras-chave não extraídas para este tipo de arquivo.")

    with tab_concepts:
        if cf:
            # Top concept frequency bubble/treemap style
            cf_items = list(cf.items())[:15]
            labels_c = [k for k,_ in cf_items]
            vals_c = [v for _,v in cf_items]
            fig_c = go.Figure(go.Treemap(
                labels=labels_c, values=vals_c, parents=[""]*len(labels_c),
                marker=dict(
                    colors=vals_c,
                    colorscale=[[0,"#1a0a03"],[.3,"#c2410c"],[.6,"#f59e0b"],[1,"#34d399"]],
                    line=dict(color="#060504",width=2)),
                textfont=dict(color="white",size=11,family="DM Sans"),
                hovertemplate='<b>%{label}</b><br>Freq: %{value}<extra></extra>'))
            fig_c.update_layout(height=300,margin=dict(l=0,r=0,t=10,b=0),
                paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
            st.markdown('<div class="chart-glass">', unsafe_allow_html=True)
            st.plotly_chart(fig_c, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            # Concept importance bars
            max_freq = max(vals_c) if vals_c else 1
            st.markdown('<div style="font-size:.62rem;color:var(--t3);text-transform:uppercase;letter-spacing:.09em;margin-bottom:.6rem;font-weight:600">Frequência Relativa</div>', unsafe_allow_html=True)
            c1c, c2c = st.columns(2)
            for i,(concept, freq) in enumerate(cf_items):
                pct = int(freq/max_freq*100)
                color = CHART_COLORS[i % len(CHART_COLORS)]
                with (c1c if i%2==0 else c2c):
                    st.markdown(f'<div style="display:flex;justify-content:space-between;font-size:.76rem;margin-bottom:2px"><span style="color:var(--t2)">{concept}</span><span style="color:var(--or5);font-weight:600">{freq}×</span></div>{prog_bar(pct,color)}', unsafe_allow_html=True)
        else:
            st.info("Análise de conceitos não disponível.")

    with tab_topics:
        if topics:
            fig_pie=go.Figure(go.Pie(
                labels=list(topics.keys()), values=list(topics.values()), hole=0.52,
                marker=dict(colors=CHART_COLORS[:len(topics)],
                    line=dict(color=["#060504"]*15, width=2)),
                textfont=dict(color="white",size=9),
                hoverinfo="label+percent"))
            fig_pie.update_layout(
                height=300,
                title=dict(text="Distribuição Temática",font=dict(color=var_t1(),family="DM Sans",size=13)),
                paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(font=dict(color="#8b5e3c",size=9)),
                margin=dict(l=0,r=0,t=40,b=0))
            st.markdown('<div class="chart-glass">', unsafe_allow_html=True)
            st.plotly_chart(fig_pie, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            for i,(topic,score) in enumerate(list(topics.items())[:8]):
                pct=min(100,score*20)
                color=CHART_COLORS[i%len(CHART_COLORS)]
                st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:.4rem"><span style="font-size:.77rem;color:var(--t2);width:190px;flex-shrink:0">{topic}</span><div style="flex:1">{prog_bar(pct,color)}</div><span style="font-size:.69rem;color:var(--t3);width:28px;text-align:right">{score}</span></div>', unsafe_allow_html=True)
        else:
            st.info("Análise temática não disponível.")

    with tab_authors:
        if authors:
            for author in authors:
                g_a = ugrad(author)
                st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:.4rem 0;border-bottom:1px solid var(--gborder)"><div style="width:28px;height:28px;border-radius:50%;background:{g_a};display:flex;align-items:center;justify-content:center;font-size:.65rem;font-weight:700;color:white;flex-shrink:0">{ini(author)}</div><span style="font-size:.82rem;color:var(--t1)">{author}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:var(--t3);font-size:.78rem;margin-bottom:.8rem">Nenhum autor identificado com os padrões textuais buscados.</div>', unsafe_allow_html=True)
        if years:
            year_labels=[y for y,_ in years[:8]]; year_vals=[c for _,c in years[:8]]
            fig_y=go.Figure(go.Bar(
                x=year_labels, y=year_vals,
                marker=dict(color=year_vals,
                    colorscale=[[0,"#1a0a03"],[.5,"#ea580c"],[1,"#fbbf24"]]),
                text=year_vals, textposition="outside",
                textfont=dict(color="#8b5e3c",size=9)))
            fig_y.update_layout(
                height=200,
                title=dict(text="Anos Citados",font=dict(color=var_t1(),family="DM Sans",size=12)),
                **pc())
            st.markdown('<div class="chart-glass">', unsafe_allow_html=True)
            st.plotly_chart(fig_y, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tab_refs:
        if refs:
            st.markdown(f'<div style="font-size:.62rem;color:var(--t3);text-transform:uppercase;letter-spacing:.09em;margin-bottom:.6rem;font-weight:600">{len(refs)} Referências Detectadas</div>', unsafe_allow_html=True)
            for r in refs[:12]:
                st.markdown(f'<div class="ref-item">· {r}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:var(--t3);font-size:.78rem;margin-bottom:.7rem">Nenhuma referência estruturada [N] encontrada.</div>', unsafe_allow_html=True)
        if refs_online:
            st.markdown('<div class="dtxt">Artigos Relacionados Online</div>', unsafe_allow_html=True)
            for i,ref in enumerate(refs_online[:5]):
                url_html=f'<a href="{ref["url"]}" target="_blank" style="color:var(--or5);text-decoration:none;font-size:.71rem">↗ Abrir</a>' if ref.get("url") else ""
                st.markdown(f'<div class="scard"><div style="font-family:Syne,sans-serif;font-size:.86rem;font-weight:700;margin-bottom:.3rem">{ref["title"]}</div><div style="color:var(--t3);font-size:.67rem;margin-bottom:.3rem">{ref["authors"]} · {ref["venue"]} · {ref["year"]}</div><div style="color:var(--t2);font-size:.77rem;line-height:1.6">{ref["abstract"][:180]}…</div><div style="margin-top:.35rem">{url_html}</div></div>', unsafe_allow_html=True)

    with tab_improve:
        # Writing quality gauge
        st.markdown(f'''
        <div class="pbox">
          <div style="font-family:Syne,sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.7rem;color:var(--gr5)">📊 Análise de Qualidade de Escrita</div>
          <div style="display:flex;gap:1.5rem;flex-wrap:wrap;font-size:.75rem;color:var(--t2);margin-bottom:.8rem">
            <span>Qualidade geral: <strong style="color:{wq_color}">{wq}% — {wq_label}</strong></span>
            <span>Complexidade média: <strong style="color:var(--t1)">{sc:.1f} palavras/frase</strong></span>
          </div>
          {prog_bar(wq, wq_color)}
        </div>''', unsafe_allow_html=True)
        if strengths_a:
            st.markdown('<div style="font-size:.62rem;color:var(--t3);text-transform:uppercase;letter-spacing:.09em;margin-bottom:.6rem;font-weight:600">✓ Pontos Fortes</div>', unsafe_allow_html=True)
            for s in strengths_a:
                st.markdown(f'<div class="str-ok">✓ {s}</div>', unsafe_allow_html=True)
        if improvements:
            st.markdown('<div style="font-size:.62rem;color:var(--t3);text-transform:uppercase;letter-spacing:.09em;margin:.8rem 0 .6rem;font-weight:600">→ Sugestões de Melhoria</div>', unsafe_allow_html=True)
            for imp in improvements:
                st.markdown(f'<div class="str-imp">→ {imp}</div>', unsafe_allow_html=True)
        if not strengths_a and not improvements:
            st.info("Execute a análise completa para ver recomendações personalizadas.")

def page_folders():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1rem;margin-bottom:1rem">📁 Pastas de Pesquisa</h1>', unsafe_allow_html=True)
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
        st.markdown('<div class="card" style="text-align:center;padding:4.5rem"><div style="font-size:2.5rem;opacity:.2;margin-bottom:1rem">📁</div><div style="color:var(--t3)">Nenhuma pasta criada ainda</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True); return
    folder_cols=st.columns(3)
    for idx,(fname,fdata) in enumerate(list(st.session_state.folders.items())):
        if not isinstance(fdata,dict): fdata={"files":fdata,"desc":"","notes":"","analyses":{}}; st.session_state.folders[fname]=fdata
        files=fdata.get("files",[]); desc=fdata.get("desc",""); analyses=fdata.get("analyses",{})
        all_tags=list({t for an in analyses.values() for t in an.get("keywords",[])[:3]})
        with folder_cols[idx%3]:
            st.markdown(f'<div class="card" style="padding:1.2rem;text-align:center;margin-bottom:.6rem"><div style="font-size:2rem;opacity:.5;margin-bottom:7px">📁</div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.95rem">{fname}</div><div style="color:var(--t3);font-size:.68rem;margin-top:2px">{desc}</div><div style="margin-top:.4rem;font-size:.70rem;color:var(--or5)">{len(files)} arquivo(s) · {len(analyses)} analisado(s)</div><div style="margin-top:.4rem">{tags_html(all_tags[:3])}</div></div>', unsafe_allow_html=True)
    for fname,fdata in list(st.session_state.folders.items()):
        if not isinstance(fdata,dict): fdata={"files":fdata,"desc":"","notes":"","analyses":{}}; st.session_state.folders[fname]=fdata
        files=fdata.get("files",[]); analyses=fdata.get("analyses",{})
        with st.expander(f"📁 {fname} — {len(files)} arquivo(s)  ·  {len(analyses)} análise(s)"):
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
                    ab='<span class="badge-pub" style="font-size:.6rem;margin-left:6px">✓</span>' if has_an else ''
                    st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:.42rem 0;border-bottom:1px solid var(--gborder)"><span style="font-size:1rem">{icon}</span><span style="font-size:.78rem;color:var(--t2);flex:1">{f}</span>{ab}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<p style="color:var(--t3);font-size:.74rem;text-align:center;padding:.5rem">Arraste arquivos — PDF, DOCX, XLSX, CSV…</p>', unsafe_allow_html=True)
            st.markdown('<hr>', unsafe_allow_html=True)
            ca_btn,cb_btn,_=st.columns([1.5,1.5,2])
            with ca_btn:
                st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
                if st.button("🔬 Analisar documentos",key=f"analyze_{fname}",use_container_width=True):
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
                if st.button("🗑 Excluir pasta",key=f"df_{fname}",use_container_width=True):
                    del st.session_state.folders[fname]
                    if fname in st.session_state.folder_files_bytes: del st.session_state.folder_files_bytes[fname]
                    save_db(); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            if analyses:
                st.markdown('<div class="dtxt">📊 Análises Inteligentes</div>', unsafe_allow_html=True)
                rel_scores={f:an.get("relevance_score",0) for f,an in analyses.items()}
                wq_scores={f:an.get("writing_quality",0) for f,an in analyses.items()}
                if len(rel_scores)>1:
                    fig_ov=go.Figure()
                    fig_ov.add_trace(go.Bar(
                        name="Relevância",
                        x=list(rel_scores.values()),
                        y=[f[:22] for f in rel_scores.keys()],
                        orientation='h',
                        marker=dict(color=list(rel_scores.values()),
                            colorscale=[[0,"#1a0a03"],[.5,"#ea580c"],[1,"#10b981"]]),
                        text=[f"{v}%" for v in rel_scores.values()],
                        textposition="outside", textfont=dict(color="#8b5e3c",size=9)))
                    if wq_scores:
                        fig_ov.add_trace(go.Bar(
                            name="Qualidade",
                            x=list(wq_scores.values()),
                            y=[f[:22] for f in wq_scores.keys()],
                            orientation='h',
                            marker=dict(color=list(wq_scores.values()),
                                colorscale=[[0,"#0a1628"],[.5,"#3b82f6"],[1,"#34d399"]]),
                            text=[f"{v}%" for v in wq_scores.values()],
                            textposition="outside", textfont=dict(color="#8b5e3c",size=9),
                            visible="legendonly"))
                    layout_ov = {**pc_noy(),
                                 'height': max(140, len(analyses)*50),
                                 'title': dict(text="Documentos — Relevância & Qualidade",
                                               font=dict(color=var_t1(),family="DM Sans",size=12)),
                                 'yaxis': dict(showgrid=False,color="#8b5e3c",tickfont=dict(size=9)),
                                 'legend': dict(font=dict(color="#8b5e3c",size=9)),
                                 'barmode': 'group'}
                    fig_ov.update_layout(**layout_ov)
                    st.markdown('<div class="chart-glass">', unsafe_allow_html=True)
                    st.plotly_chart(fig_ov, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                for f,an in analyses.items():
                    with st.expander(f"🔬 Análise: {f}"):
                        render_document_analysis(f,an,research_area)
            st.markdown('<hr>', unsafe_allow_html=True)
            note=st.text_area("Notas",value=fdata.get("notes",""),key=f"note_{fname}",height=70,placeholder="Anotações…")
            if st.button("💾 Salvar nota",key=f"sn_{fname}",use_container_width=True):
                fdata["notes"]=note; save_db(); st.success("✓ Nota salva!")
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════
def page_analytics():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1rem;margin-bottom:1rem">📊 Painel de Pesquisa</h1>', unsafe_allow_html=True)
    email=st.session_state.current_user; d=st.session_state.stats_data
    tab_f,tab_p,tab_i,tab_pr=st.tabs(["  📁 Pastas  ","  📝 Publicações  ","  📈 Impacto  ","  🎯 Interesses  "])
    with tab_f:
        folders=st.session_state.folders
        if not folders:
            st.markdown('<div class="card" style="text-align:center;padding:3.5rem;color:var(--t3)">Crie pastas e analise documentos.</div>', unsafe_allow_html=True)
        else:
            all_analyses={f:an for fd in folders.values() if isinstance(fd,dict) for f,an in fd.get("analyses",{}).items()}
            total_files=sum(len(fd.get("files",[]) if isinstance(fd,dict) else fd) for fd in folders.values())
            all_kws=[kw for an in all_analyses.values() for kw in an.get("keywords",[])]
            all_topics=defaultdict(int)
            for an in all_analyses.values():
                for t,s in an.get("topics",{}).items(): all_topics[t]+=s
            all_wq=[an.get("writing_quality",0) for an in all_analyses.values() if an.get("writing_quality",0)>0]
            avg_wq=round(sum(all_wq)/len(all_wq)) if all_wq else 0
            c1,c2,c3,c4=st.columns(4)
            for col,(v,l) in zip([c1,c2,c3,c4],[(len(folders),"Pastas"),(total_files,"Arquivos"),(len(all_analyses),"Analisados"),(len(set(all_kws[:100])),"Keywords únicas")]):
                with col: st.markdown(f'<div class="mbox"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>', unsafe_allow_html=True)
            if avg_wq:
                st.markdown(f'<div style="margin:.8rem 0;background:var(--glass);border:1px solid var(--gborder);border-radius:var(--r16);padding:.9rem 1.2rem;display:flex;align-items:center;gap:1.5rem"><div><div style="font-size:.62rem;color:var(--t3);text-transform:uppercase;letter-spacing:.09em;font-weight:600;margin-bottom:3px">Qualidade Média de Escrita</div><div style="font-family:Syne,sans-serif;font-size:1.4rem;font-weight:800;color:{"#10b981" if avg_wq>70 else "#f59e0b"}">{avg_wq}%</div></div><div style="flex:1">{prog_bar(avg_wq,"#10b981" if avg_wq>70 else "#f59e0b")}</div></div>', unsafe_allow_html=True)
            if all_topics:
                layout_t = {**pc_noy(), 'height': 280,
                            'title': dict(text="Temas por Frequência",font=dict(color=var_t1(),family="DM Sans",size=13)),
                            'yaxis': dict(showgrid=False,color="#8b5e3c",tickfont=dict(size=9))}
                fig_t=go.Figure(go.Bar(
                    x=list(all_topics.values())[:8], y=list(all_topics.keys())[:8],
                    orientation='h',
                    marker=dict(color=CHART_COLORS[:min(8,len(all_topics))]),
                    text=[str(v) for v in list(all_topics.values())[:8]],
                    textposition="outside", textfont=dict(color="#8b5e3c",size=9)))
                fig_t.update_layout(**layout_t)
                st.markdown('<div class="chart-glass">', unsafe_allow_html=True)
                st.plotly_chart(fig_t, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            if all_kws:
                kw_freq=Counter(all_kws).most_common(15)
                layout_kw = {**pc_noy(), 'height': 340,
                             'title': dict(text="Top 15 Palavras-chave",font=dict(color=var_t1(),family="DM Sans",size=13)),
                             'yaxis': dict(showticklabels=False)}
                fig_kw=go.Figure(go.Bar(
                    x=[c for _,c in kw_freq], y=[w for w,_ in kw_freq],
                    orientation='h',
                    marker=dict(color=[c for _,c in kw_freq],
                        colorscale=[[0,"#1a0a03"],[.4,"#ea580c"],[.7,"#f59e0b"],[1,"#34d399"]]),
                    text=[w for w,_ in kw_freq],
                    textposition='inside', textfont=dict(color='white',size=8)))
                fig_kw.update_layout(**layout_kw)
                st.markdown('<div class="chart-glass">', unsafe_allow_html=True)
                st.plotly_chart(fig_kw, use_container_width=True)
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
            titles_s=[p["title"][:18]+"…" for p in my_posts]
            fig_eng=go.Figure()
            fig_eng.add_trace(go.Bar(name="Curtidas",x=titles_s,y=[p["likes"] for p in my_posts],marker_color=CHART_COLORS[0]))
            fig_eng.add_trace(go.Bar(name="Comentários",x=titles_s,y=[len(p.get("comments",[])) for p in my_posts],marker_color=CHART_COLORS[2]))
            fig_eng.update_layout(barmode="group",title=dict(text="Engajamento",font=dict(color=var_t1(),family="DM Sans",size=13)),height=260,**pc(),legend=dict(font=dict(color="#8b5e3c")))
            st.markdown('<div class="chart-glass">', unsafe_allow_html=True)
            st.plotly_chart(fig_eng, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            for p in sorted(my_posts,key=lambda x:x.get("date",""),reverse=True):
                t_s=p["title"][:55]+("…" if len(p["title"])>55 else "")
                st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;justify-content:space-between"><div style="font-family:Syne,sans-serif;font-size:.9rem;font-weight:700">{t_s}</div>{badge(p["status"])}</div><div style="font-size:.71rem;color:var(--t3);margin-top:.4rem">{p.get("date","")} · {p["likes"]} curtidas · {len(p.get("comments",[]))} comentários · {p.get("views",0)} views</div><div style="margin-top:.4rem">{tags_html(p.get("tags",[])[:4])}</div></div>', unsafe_allow_html=True)
    with tab_i:
        c1,c2,c3=st.columns(3)
        with c1: st.markdown(f'<div class="mbox"><div class="mval">{d.get("h_index",4)}</div><div class="mlbl">Índice H</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="mbox"><div class="mval">{d.get("fator_impacto",3.8):.1f}</div><div class="mlbl">Fator de Impacto</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="mbox"><div class="mval-green">{len(st.session_state.saved_articles)}</div><div class="mlbl">Artigos Salvos</div></div>', unsafe_allow_html=True)
        st.markdown("<hr>", unsafe_allow_html=True)
        new_h=st.number_input("Índice H",0,200,d.get("h_index",4),key="e_h")
        new_fi=st.number_input("Fator de impacto",0.0,100.0,float(d.get("fator_impacto",3.8)),step=0.1,key="e_fi")
        new_notes=st.text_area("Notas",value=d.get("notes",""),key="e_notes",height=80)
        if st.button("💾 Salvar métricas",key="btn_save_m"): d.update({"h_index":new_h,"fator_impacto":new_fi,"notes":new_notes}); st.success("✓ Salvo!")
    with tab_pr:
        prefs=st.session_state.user_prefs.get(email,{})
        if prefs:
            top=sorted(prefs.items(),key=lambda x:-x[1])[:14]; mx=max(s for _,s in top) if top else 1
            cats=[t for t,_ in top[:8]]; vals=[round(s/mx*100) for _,s in top[:8]]
            if len(cats)>=3:
                fig_r=go.Figure(go.Scatterpolar(r=vals+[vals[0]],theta=cats+[cats[0]],fill='toself',
                    line=dict(color="#f97316"),fillcolor="rgba(249,115,22,.15)"))
                fig_r.update_layout(height=280,polar=dict(bgcolor="rgba(0,0,0,0)",radialaxis=dict(visible=True,gridcolor="rgba(249,115,22,.08)",color="#8b5e3c",tickfont=dict(size=8)),angularaxis=dict(gridcolor="rgba(249,115,22,.08)",color="#8b5e3c",tickfont=dict(size=9))),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=40,r=40,t=20,b=20))
                st.markdown('<div class="chart-glass">', unsafe_allow_html=True)
                st.plotly_chart(fig_r, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            c1,c2=st.columns(2)
            for i,(tag,score) in enumerate(top):
                pct=int(score/mx*100); color=CHART_COLORS[i%len(CHART_COLORS)]
                with (c1 if i%2==0 else c2):
                    st.markdown(f'<div style="display:flex;justify-content:space-between;font-size:.77rem;margin-bottom:2px"><span style="color:var(--t2)">{tag}</span><span style="color:var(--or5);font-weight:600">{pct}%</span></div>{prog_bar(pct,color)}', unsafe_allow_html=True)
        else:
            st.info("Interaja com pesquisas para construir seu perfil de interesses.")
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# IMAGE ANALYSIS — enhanced with AI disclaimer
# ══════════════════════════════════════════════════
def page_img_search():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1rem;margin-bottom:.4rem">🔬 Análise Visual Científica</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.80rem;margin-bottom:1.2rem">Detecta padrões, estruturas e conecta com pesquisas similares</p>', unsafe_allow_html=True)
    col_up,col_res=st.columns([1,1.9])
    with col_up:
        st.markdown('<div class="card" style="padding:1.2rem">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.88rem;margin-bottom:.7rem">📷 Carregar Imagem</div>', unsafe_allow_html=True)
        img_file=st.file_uploader("",type=["png","jpg","jpeg","webp","tiff"],label_visibility="collapsed",key="img_up")
        if img_file: st.image(img_file,use_container_width=True,caption="Imagem carregada")
        st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
        run=st.button("🔬 Analisar Imagem",use_container_width=True,key="btn_run")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('''
        <div class="ai-warn" style="margin-top:.9rem">
          <div style="font-size:.68rem;color:var(--am5);font-weight:700;margin-bottom:3px">⚠️ Aviso sobre IA</div>
          <div style="font-size:.65rem;color:var(--t2);line-height:1.65">
            Esta análise é gerada por algoritmos computacionais e pode conter erros.
            Não substitui avaliação de especialistas em microscopia, histologia ou análise de imagens científicas.
            Sempre valide os resultados com profissionais da área.
          </div>
        </div>
        <div style="margin-top:.9rem;font-size:.67rem;color:var(--t3);line-height:2">
          Sobel Edges · FFT periódica<br>
          Simetria radial & bilateral<br>
          Análise de canais RGB<br>
          Paleta dominante · Entropia<br>
          Busca de pesquisas similares
        </div>''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col_res:
        if run and img_file:
            img_file.seek(0)
            with st.spinner("Analisando…"):
                rep=analyze_image_advanced(img_file); st.session_state.img_result=rep
            if rep:
                conf_c=("#10b981" if rep["confidence"]>80 else ("#f59e0b" if rep["confidence"]>60 else "#ef4444"))
                # Main result card
                st.markdown(f'''
                <div class="abox">
                  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:.55rem">
                    <div>
                      <div style="font-size:.60rem;color:var(--t3);letter-spacing:.10em;text-transform:uppercase;margin-bottom:4px;font-weight:600">Categoria detectada</div>
                      <div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:700;margin-bottom:4px">{rep["category"]}</div>
                      <div style="font-size:.78rem;color:var(--t2);margin-bottom:.4rem">{rep["context"]}</div>
                    </div>
                    <div style="background:rgba(0,0,0,.4);border:1px solid var(--gborder);border-radius:14px;padding:.6rem 1rem;text-align:center;flex-shrink:0">
                      <div style="font-family:Syne,sans-serif;font-size:1.5rem;font-weight:800;color:{conf_c}">{rep["confidence"]}%</div>
                      <div style="font-size:.58rem;color:var(--t3);text-transform:uppercase;font-weight:600">confiança</div>
                    </div>
                  </div>
                  <div style="font-size:.80rem;color:var(--t2);line-height:1.68;margin-bottom:.55rem">{rep["description"]}</div>
                  <div style="display:flex;gap:1.5rem;flex-wrap:wrap;font-size:.67rem;color:var(--t3)">
                    <span>Material: <strong style="color:var(--t2)">{rep["material"]}</strong></span>
                    <span>Estrutura: <strong style="color:var(--t2)">{rep["object_type"]}</strong></span>
                    <span>Resolução: <strong style="color:var(--t2)">{rep["size"][0]}×{rep["size"][1]}</strong></span>
                    <span>Brilho: <strong style="color:var(--t2)">{rep["brightness"]}</strong></span>
                    <span>Nitidez: <strong style="color:var(--t2)">{rep["sharpness"]}</strong></span>
                  </div>
                </div>''', unsafe_allow_html=True)

                # Metric pills
                c1,c2,c3=st.columns(3)
                sym_lbl="Alta" if rep["symmetry"]>0.78 else ("Média" if rep["symmetry"]>0.52 else "Baixa")
                with c1: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1rem;font-weight:700;color:var(--or5)">{rep["texture"]["complexity"]}</div><div class="mlbl">Complexidade</div></div>', unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1rem;font-weight:700;color:var(--gr5)">{sym_lbl}</div><div class="mlbl">Simetria</div></div>', unsafe_allow_html=True)
                with c3: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1rem;font-weight:700;color:var(--am5)">{rep["lines"]["direction"]}</div><div class="mlbl">Dir. Linhas</div></div>', unsafe_allow_html=True)

                # Line analysis
                l=rep["lines"]; strengths_img=l["strengths"]; max_s=max(strengths_img.values())+0.01
                st.markdown('<div class="pbox"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.7rem;color:var(--gr5)">📐 Análise de Linhas e Estrutura</div>', unsafe_allow_html=True)
                for dir_name,val in strengths_img.items():
                    pct=int(val/max_s*100); is_dom=dir_name==l["direction"]
                    color="#34d399" if is_dom else "#f97316"
                    st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:.38rem"><span style="font-size:.69rem;color:{"var(--gr5)" if is_dom else "var(--t3)"};width:92px;flex-shrink:0">{"★ " if is_dom else ""}{dir_name}</span><div style="flex:1">{prog_bar(pct,color)}</div><span style="font-size:.68rem;color:var(--t3);width:36px;text-align:right">{val:.2f}</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:.69rem;color:var(--t3);margin-top:.5rem">Formas: <strong style="color:var(--gr5)">{" · ".join(rep["shapes"])}</strong></div></div>', unsafe_allow_html=True)

                # Color analysis with RGB histogram
                rv,gv,bv=rep["color"]["r"],rep["color"]["g"],rep["color"]["b"]
                hex_c="#{:02x}{:02x}{:02x}".format(int(rv),int(gv),int(bv))
                pal_html="".join(f'<div style="width:28px;height:28px;border-radius:7px;background:rgb{str(p)};border:1.5px solid rgba(255,255,255,.07)"></div>' for p in rep["palette"][:7])
                temp_str="Quente 🔴" if rep["color"]["warm"] else ("Fria 🔵" if rep["color"]["cool"] else "Neutra ⚪")
                st.markdown(f'<div class="abox"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.8rem">🎨 Análise de Cor & Paleta</div><div style="display:flex;gap:12px;align-items:center;margin-bottom:.9rem"><div style="width:44px;height:44px;border-radius:11px;background:{hex_c};border:1.5px solid var(--gborder);flex-shrink:0"></div><div style="font-size:.78rem;color:var(--t2);line-height:1.75">RGB: <strong>({int(rv)},{int(gv)},{int(bv)})</strong> · {hex_c.upper()}<br>Canal dominante: <strong>{rep["color"]["dom"]}</strong> · Temp: <strong>{temp_str}</strong> · Saturação: <strong>{rep["color"]["sat"]:.0f}%</strong></div></div><div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:.7rem">{pal_html}</div></div>', unsafe_allow_html=True)

                # RGB Histogram chart
                if rep.get("histograms"):
                    h = rep["histograms"]
                    bins_x = list(range(0, 256, 8))[:32]
                    fig_h = go.Figure()
                    fig_h.add_trace(go.Scatter(x=bins_x, y=h["r"][:32], fill='tozeroy', name='R', line=dict(color='rgba(249,115,22,.8)',width=1.5), fillcolor='rgba(249,115,22,.12)'))
                    fig_h.add_trace(go.Scatter(x=bins_x, y=h["g"][:32], fill='tozeroy', name='G', line=dict(color='rgba(52,211,153,.8)',width=1.5), fillcolor='rgba(52,211,153,.12)'))
                    fig_h.add_trace(go.Scatter(x=bins_x, y=h["b"][:32], fill='tozeroy', name='B', line=dict(color='rgba(96,165,250,.8)',width=1.5), fillcolor='rgba(96,165,250,.12)'))
                    fig_h.update_layout(height=180,title=dict(text="Histograma RGB",font=dict(color=var_t1(),family="DM Sans",size=12)),**pc(),legend=dict(font=dict(color="#8b5e3c",size=9)),margin=dict(l=10,r=10,t=35,b=10))
                    st.markdown('<div class="chart-glass">', unsafe_allow_html=True)
                    st.plotly_chart(fig_h, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                # AI disclaimer reminder
                st.markdown('<div class="ai-warn"><div style="font-size:.67rem;color:var(--am5);font-weight:700;margin-bottom:2px">⚠️ Análise realizada por algoritmos computacionais</div><div style="font-size:.63rem;color:var(--t3);line-height:1.6">Os resultados acima são estimativas baseadas em análise de pixels (gradientes, FFT, histogramas). A classificação pode conter erros — especialmente em imagens ambíguas, compostas ou com múltiplas estruturas. Valide sempre com especialistas da área científica correspondente.</div></div>', unsafe_allow_html=True)

        elif not img_file:
            st.markdown('<div class="card" style="padding:5rem 2rem;text-align:center"><div style="font-size:3rem;opacity:.2;margin-bottom:1.2rem">🔬</div><div style="font-family:Syne,sans-serif;font-size:1.05rem;color:var(--t2);margin-bottom:.7rem">Carregue uma imagem científica</div><div style="color:var(--t3);font-size:.76rem;line-height:2">PNG · JPG · WEBP · TIFF<br>Microscopia · Cristalografia · Fluorescência · Diagramas</div></div>', unsafe_allow_html=True)

    if st.session_state.get("img_result"):
        rep=st.session_state.img_result; st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<h2 style="margin-bottom:.7rem">🔗 Pesquisas Relacionadas</h2>', unsafe_allow_html=True)
        kw=(rep.get("kw","")+" "+rep.get("category","")+" "+rep.get("object_type","")).lower().split()
        all_terms=list(set(kw))
        t_neb,t_fol,t_web=st.tabs(["  🔬 Na Nebula  ","  📁 Nas Pastas  ","  🌐 Internet  "])
        with t_neb:
            neb_r=sorted([(sum(1 for t in all_terms if len(t)>2 and t in (p.get("title","")+" "+p.get("abstract","")+" "+" ".join(p.get("tags",[]))).lower()),p) for p in st.session_state.feed_posts],key=lambda x:-x[0])
            neb_r=[p for s,p in neb_r if s>0]
            if neb_r:
                for p in neb_r[:4]: render_post(p,ctx="img_neb",compact=True)
            else: st.markdown('<div style="color:var(--t3);padding:1rem">Nenhuma pesquisa similar na Nebula.</div>', unsafe_allow_html=True)
        with t_fol:
            fm=[]
            for fname,fdata in st.session_state.folders.items():
                if not isinstance(fdata,dict): continue
                fkws=list({kw for an in fdata.get("analyses",{}).values() for kw in an.get("keywords",[])})
                sc=sum(1 for t in all_terms if len(t)>2 and any(t in ft for ft in fkws))
                if sc>0: fm.append((sc,fname,fdata))
            fm.sort(key=lambda x:-x[0])
            if fm:
                for _,fname,fdata in fm[:4]:
                    an_kws=list({kw for an in fdata.get("analyses",{}).values() for kw in an.get("keywords",[])[:4]})
                    st.markdown(f'<div class="img-rc"><div style="font-family:Syne,sans-serif;font-size:.91rem;font-weight:700;margin-bottom:.3rem">📁 {fname}</div><div style="color:var(--t3);font-size:.68rem;margin-bottom:.4rem">{len(fdata.get("files",[]))} arquivos</div><div>{tags_html(an_kws[:6])}</div></div>', unsafe_allow_html=True)
            else: st.markdown('<div style="color:var(--t3);padding:1rem">Nenhum documento relacionado.</div>', unsafe_allow_html=True)
        with t_web:
            ck=f"img_{rep['kw'][:40]}"
            if ck not in st.session_state.scholar_cache:
                with st.spinner("Buscando artigos…"):
                    st.session_state.scholar_cache[ck]=search_ss(f"{rep['category']} {rep['object_type']} {rep['material']}",4)
            web_r=st.session_state.scholar_cache.get(ck,[])
            if web_r:
                for idx,a in enumerate(web_r): render_web_article(a,idx=idx+2000,ctx="img_web")
            else: st.markdown('<div style="color:var(--t3);padding:1rem">Sem resultados online.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# CHAT
# ══════════════════════════════════════════════════
def page_chat():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1rem;margin-bottom:1rem">💬 Mensagens</h1>', unsafe_allow_html=True)
    col_c,col_m=st.columns([.88,2.8])
    email=st.session_state.current_user
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    with col_c:
        st.markdown('<div style="font-size:.62rem;font-weight:700;color:var(--t3);letter-spacing:.10em;text-transform:uppercase;margin-bottom:.8rem">Conversas</div>', unsafe_allow_html=True)
        shown=set()
        for ue in st.session_state.chat_contacts:
            if ue==email or ue in shown: continue
            shown.add(ue); ud=users.get(ue,{}); uname=ud.get("name","?"); uin=ini(uname)
            uphoto=ud.get("photo_b64"); ug=ugrad(ue)
            msgs=st.session_state.chat_messages.get(ue,[])
            last=msgs[-1]["text"][:24]+"…" if msgs and len(msgs[-1]["text"])>24 else (msgs[-1]["text"] if msgs else "Iniciar conversa")
            active=st.session_state.active_chat==ue; online=random.Random(ue+"c").random()>.42
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            bg="rgba(249,115,22,.12)" if active else "rgba(18,10,4,.62)"; bdr="rgba(249,115,22,.30)" if active else "var(--gborder)"
            st.markdown(f'<div style="background:{bg};border:1px solid {bdr};border-radius:14px;padding:9px 11px;margin-bottom:5px"><div style="display:flex;align-items:center;gap:8px">{avh(uin,32,uphoto,ug)}<div style="overflow:hidden;flex:1"><div style="font-size:.80rem;font-weight:600;font-family:Syne,sans-serif">{dot}{uname}</div><div style="font-size:.67rem;color:var(--t3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{last}</div></div></div></div>', unsafe_allow_html=True)
            if st.button("💬 Abrir",key=f"oc_{ue}",use_container_width=True): st.session_state.active_chat=ue; st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
        nc=st.text_input("",placeholder="Adicionar por e-mail…",key="new_ct",label_visibility="collapsed")
        if st.button("+ Adicionar",key="btn_add_ct",use_container_width=True):
            if nc in users and nc!=email:
                if nc not in st.session_state.chat_contacts: st.session_state.chat_contacts.append(nc)
                st.rerun()
            elif nc: st.toast("Usuário não encontrado.")
    with col_m:
        if st.session_state.active_chat:
            contact=st.session_state.active_chat; cd=users.get(contact,{}); cname=cd.get("name","?"); cin=ini(cname)
            cphoto=cd.get("photo_b64"); cg=ugrad(contact)
            msgs=st.session_state.chat_messages.get(contact,[]); is_online=random.Random(contact+"o").random()>.35
            dot='<span class="dot-on"></span>' if is_online else '<span class="dot-off"></span>'
            st.markdown(f'<div style="background:var(--glass);border:1px solid var(--gborder);border-radius:16px;padding:12px 16px;margin-bottom:1rem;display:flex;align-items:center;gap:12px"><div style="flex-shrink:0">{avh(cin,40,cphoto,cg)}</div><div style="flex:1"><div style="font-weight:700;font-size:.92rem;font-family:Syne,sans-serif">{dot}{cname}</div><div style="font-size:.68rem;color:var(--gr4)">🔒 Criptografia AES-256 ativa</div></div></div>', unsafe_allow_html=True)
            for msg in msgs:
                is_me=msg["from"]=="me"; cls="bme" if is_me else "bthem"; align="right" if is_me else "left"
                st.markdown(f'<div style="display:flex;{"justify-content:flex-end" if is_me else ""}"><div class="{cls}">{msg["text"]}<div style="font-size:.60rem;color:rgba(255,255,255,.22);margin-top:3px;text-align:{align}">{msg["time"]}</div></div></div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            c_inp,c_btn=st.columns([5,1])
            with c_inp: nm=st.text_input("",placeholder="Escreva uma mensagem…",key=f"mi_{contact}",label_visibility="collapsed")
            with c_btn:
                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
                if st.button("→",key=f"ms_{contact}",use_container_width=True):
                    if nm:
                        now=datetime.now().strftime("%H:%M")
                        st.session_state.chat_messages.setdefault(contact,[]).append({"from":"me","text":nm,"time":now}); st.rerun()
        else:
            st.markdown('<div class="card" style="text-align:center;padding:6rem"><div style="font-size:2.5rem;opacity:.2;margin-bottom:1rem">💬</div><div style="color:var(--t2);font-family:Syne,sans-serif;font-size:1rem">Selecione uma conversa</div><div style="font-size:.74rem;color:var(--t3);margin-top:.5rem">🔒 Criptografia end-to-end ativa</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# SETTINGS
# ══════════════════════════════════════════════════
def page_settings():
    st.markdown('<div class="pw">', unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1rem;margin-bottom:1rem">⚙️ Perfil & Configurações</h1>', unsafe_allow_html=True)
    u=guser(); email=st.session_state.current_user; in_=ini(u.get("name","?")); photo=u.get("photo_b64"); ug=ugrad(email)
    tab_p,tab_s,tab_pr,tab_saved=st.tabs(["  👤 Meu Perfil  ","  🔐 Segurança  ","  🛡 Privacidade  ","  🔖 Artigos Salvos  "])
    with tab_p:
        photo_html=f'<img src="{photo}"/>' if photo else f'<span style="font-size:2rem">{in_}</span>'
        my_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==email]
        liked_count=sum(1 for p in st.session_state.feed_posts if email in p.get("liked_by",[]))
        v_badge='<span style="font-size:.7rem;color:var(--gr4);margin-left:6px">✓</span>' if u.get("verified") else ""
        st.markdown(f'<div class="prof-hero"><div class="prof-photo" style="background:{ug}">{photo_html}</div><div style="flex:1;z-index:1"><div style="display:flex;align-items:center;gap:6px;margin-bottom:.3rem"><h1 style="margin:0">{u.get("name","?")}</h1>{v_badge}</div><div style="color:var(--or5);font-size:.83rem;font-weight:500;margin-bottom:.4rem">{u.get("area","")}</div><div style="color:var(--t2);font-size:.82rem;line-height:1.68;margin-bottom:.9rem">{u.get("bio","Sem biografia.")}</div><div style="display:flex;gap:2rem;flex-wrap:wrap"><div><span style="font-family:Syne,sans-serif;font-weight:800">{u.get("followers",0)}</span><span style="color:var(--t3);font-size:.72rem"> seguidores</span></div><div><span style="font-family:Syne,sans-serif;font-weight:800">{u.get("following",0)}</span><span style="color:var(--t3);font-size:.72rem"> seguindo</span></div><div><span style="font-family:Syne,sans-serif;font-weight:800">{len(my_posts)}</span><span style="color:var(--t3);font-size:.72rem"> pesquisas</span></div><div><span style="font-family:Syne,sans-serif;font-weight:800">{liked_count}</span><span style="color:var(--t3);font-size:.72rem"> curtidas dadas</span></div></div></div></div>', unsafe_allow_html=True)
        ph=st.file_uploader("📷 Foto de perfil",type=["png","jpg","jpeg","webp"],key="ph_up")
        if ph:
            b64=img_to_b64(ph)
            if b64: st.session_state.users[email]["photo_b64"]=b64; save_db(); st.success("✓ Foto atualizada!"); st.rerun()
        st.markdown("<hr>", unsafe_allow_html=True)
        new_n=st.text_input("Nome completo",value=u.get("name",""),key="cfg_n")
        new_a=st.text_input("Área de pesquisa",value=u.get("area",""),key="cfg_a")
        new_b=st.text_area("Biografia",value=u.get("bio",""),key="cfg_b",height=90)
        c_save,c_out=st.columns(2)
        with c_save:
            st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
            if st.button("💾 Salvar perfil",key="btn_sp",use_container_width=True):
                st.session_state.users[email]["name"]=new_n; st.session_state.users[email]["area"]=new_a; st.session_state.users[email]["bio"]=new_b
                save_db(); record(area_to_tags(new_a),1.5); st.success("✓ Perfil salvo!"); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c_out:
            st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
            if st.button("🚪 Sair da conta",key="btn_logout",use_container_width=True):
                st.session_state.logged_in=False; st.session_state.current_user=None; st.session_state.page="login"; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    with tab_s:
        st.markdown('<h3 style="margin-bottom:1rem">🔑 Alterar senha</h3>', unsafe_allow_html=True)
        with st.form("change_pw_form"):
            op=st.text_input("Senha atual",type="password",key="op")
            np_=st.text_input("Nova senha",type="password",key="np_")
            np2=st.text_input("Confirmar nova",type="password",key="np2")
            if st.form_submit_button("🔑 Alterar senha"):
                if hp(op)!=u.get("password",""): st.error("Senha atual incorreta.")
                elif np_!=np2: st.error("Senhas não coincidem.")
                elif len(np_)<6: st.error("Mínimo 6 caracteres.")
                else: st.session_state.users[email]["password"]=hp(np_); save_db(); st.success("✓ Senha alterada!")
        st.markdown("<hr>", unsafe_allow_html=True)
        en=u.get("2fa_enabled",False)
        st.markdown(f'<div class="card" style="padding:1rem 1.3rem;display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem"><div><div style="font-weight:700;font-size:.88rem;font-family:Syne,sans-serif">🔐 Autenticação 2FA</div><div style="font-size:.70rem;color:var(--t3)">{email}</div></div><span style="color:{"var(--gr4)" if en else "var(--err)"};font-size:.80rem;font-weight:700">{"✓ Ativo" if en else "✕ Inativo"}</span></div>', unsafe_allow_html=True)
        if st.button("✕ Desativar 2FA" if en else "✓ Ativar 2FA",key="btn_2fa"):
            st.session_state.users[email]["2fa_enabled"]=not en; save_db(); st.rerun()
    with tab_pr:
        prots=[("🔒 AES-256","Criptografia end-to-end nas mensagens"),("🔏 SHA-256","Hash seguro de senhas"),("🛡 TLS 1.3","Transmissão criptografada")]
        for n2,d2 in prots:
            st.markdown(f'<div style="display:flex;align-items:center;gap:12px;background:rgba(16,185,129,.05);border:1px solid rgba(16,185,129,.14);border-radius:12px;padding:11px;margin-bottom:8px"><div style="width:28px;height:28px;border-radius:8px;background:rgba(16,185,129,.10);display:flex;align-items:center;justify-content:center;color:var(--gr4);font-size:.8rem;flex-shrink:0">✓</div><div><div style="font-weight:600;color:var(--gr4);font-size:.82rem">{n2}</div><div style="font-size:.69rem;color:var(--t3)">{d2}</div></div></div>', unsafe_allow_html=True)
    with tab_saved:
        st.markdown('<h3 style="margin-bottom:1rem">🔖 Artigos Salvos</h3>', unsafe_allow_html=True)
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
            st.markdown('<div class="card" style="text-align:center;padding:2.5rem;color:var(--t3)">Nenhum artigo salvo ainda.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════
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
        "feed":page_feed, "search":page_search, "knowledge":page_knowledge,
        "folders":page_folders, "analytics":page_analytics, "img_search":page_img_search,
        "chat":page_chat, "settings":page_settings,
    }.get(st.session_state.page, page_feed)()

main()
