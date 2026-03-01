
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
  height:34px !important; min-height:34px !important;
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
# ========================= FEED / POSTS =========================
def render_post(post):
    user = st.session_state.users.get(post["author"], {})
    name = user.get("name", post["author"])
    area = user.get("area", "Pesquisa")

    photo = user.get("photo_b64")
    if photo:
        avatar = f"<img src='{photo}' class='avatar-img'/>"
    else:
        avatar = f"<div class='avatar' style='background:{ugrad(post['author'])}'>{ini(name)}</div>"

    st.markdown(f"""
    <div class="post-card">
        <div class="post-header">
            {avatar}
            <div>
                <div class="post-author">{name}</div>
                <div class="post-area">{area} • {time_ago(post["date"])}</div>
            </div>
        </div>

        <div class="post-title">{post["title"]}</div>
        <div class="post-desc">{post["description"]}</div>

        <div class="post-tags">
            {" ".join([f"<span class='tag'>{t}</span>" for t in post.get("tags", [])])}
        </div>

        <div class="post-actions">
            <span>❤️ {fmt_num(post.get("likes",0))}</span>
            <span>💬 {fmt_num(post.get("comments",0))}</span>
            <span>🔖</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def page_feed():
    st.markdown("<h2 class='section-title'>Feed de Pesquisas</h2>", unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='new-post-box'>", unsafe_allow_html=True)

        col1, col2 = st.columns([1,8])
        with col1:
            user = guser()
            photo = user.get("photo_b64")
            if photo:
                st.markdown(f"<img src='{photo}' class='avatar-img-lg'/>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='avatar-lg' style='background:{ugrad(st.session_state.current_user)}'>{ini(user.get('name','J'))}</div>", unsafe_allow_html=True)

        with col2:
            title = st.text_input("Título da pesquisa")
            desc = st.text_area("Descrição")
            tags = st.text_input("Tags separadas por vírgula")

            if st.button("Publicar"):
                if title.strip():
                    st.session_state.feed_posts.insert(0,{
                        "author": st.session_state.current_user,
                        "title": title,
                        "description": desc,
                        "tags": [t.strip() for t in tags.split(",") if t.strip()],
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "likes": 0,
                        "comments": 0
                    })
                    save_db()
                    st.success("Publicado!")
                else:
                    st.warning("Digite um título")

        st.markdown("</div>", unsafe_allow_html=True)

    for post in st.session_state.feed_posts:
        render_post(post)


# ========================= PERFIL + CONFIG =========================
def page_profile():
    user = guser()

    st.markdown("<h2 class='section-title'>Perfil & Configurações</h2>", unsafe_allow_html=True)

    col1, col2 = st.columns([1,3])

    with col1:
        photo = user.get("photo_b64")
        if photo:
            st.markdown(f"<img src='{photo}' class='avatar-img-xl'/>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='avatar-xl' style='background:{ugrad(st.session_state.current_user)}'>{ini(user.get('name','J'))}</div>", unsafe_allow_html=True)

        new_photo = st.file_uploader("Alterar foto", type=["png","jpg","jpeg"])
        if new_photo:
            st.session_state.users[st.session_state.current_user]["photo_b64"] = img_to_b64(new_photo)
            save_db()
            st.success("Foto atualizada")

    with col2:
        name = st.text_input("Nome", value=user.get("name",""))
        area = st.text_input("Área", value=user.get("area",""))
        bio = st.text_area("Bio", value=user.get("bio",""))

        if st.button("Salvar alterações"):
            st.session_state.users[st.session_state.current_user].update({
                "name": name,
                "area": area,
                "bio": bio
            })
            save_db()
            st.success("Perfil atualizado")

        st.markdown("---")

        st.subheader("Segurança")
        if st.button("Gerar código 2FA"):
            code = code6()
            st.session_state.users[st.session_state.current_user]["2fa"] = code
            save_db()
            st.info(f"Código gerado: {code}")


# ========================= PASTAS =========================
def page_folders():
    st.markdown("<h2 class='section-title'>Pastas de Pesquisa</h2>", unsafe_allow_html=True)

    folders = st.session_state.folders.get(st.session_state.current_user, [])

    new_folder = st.text_input("Nova pasta")
    if st.button("Criar pasta"):
        if new_folder:
            folders.append({"name": new_folder, "files":[]})
            st.session_state.folders[st.session_state.current_user] = folders
            save_db()
            st.success("Pasta criada")

    for f in folders:
        with st.expander(f["name"]):
            up = st.file_uploader(f"Upload em {f['name']}", key=f["name"], accept_multiple_files=True)
            if up:
                for file in up:
                    f["files"].append(file.name)
                save_db()
                st.success("Arquivos adicionados")

            for file in f["files"]:
                st.write("📄", file)


# ========================= CHAT =========================
def page_chat():
    st.markdown("<h2 class='section-title'>Chat</h2>", unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    msg = st.text_input("Mensagem")
    if st.button("Enviar"):
        st.session_state.messages.append(("você", msg))

    for u,m in st.session_state.messages:
        st.markdown(f"**{u}:** {m}")


# ========================= NAVEGAÇÃO =========================
def navbar():
    cols = st.columns(6)
    pages = ["Feed","Perfil","Pastas","Chat","Conexões","Buscar"]

    for i,p in enumerate(pages):
        if cols[i].button(p):
            st.session_state.page = p


# ========================= MAIN =========================
if "users" not in st.session_state:
    st.session_state.users = {}
if "feed_posts" not in st.session_state:
    st.session_state.feed_posts = []
if "folders" not in st.session_state:
    st.session_state.folders = {}
if "saved_articles" not in st.session_state:
    st.session_state.saved_articles = []
if "current_user" not in st.session_state:
    st.session_state.current_user = "guest"
if "page" not in st.session_state:
    st.session_state.page = "Feed"

navbar()

if st.session_state.page == "Feed":
    page_feed()
elif st.session_state.page == "Perfil":
    page_profile()
elif st.session_state.page == "Pastas":
    page_folders()
elif st.session_state.page == "Chat":
    page_chat()
else:
    page_feed() 
# ========================= ANÁLISE DE TEXTO CIENTÍFICO =========================
def extract_keywords(text, top_n=10):
    words = re.findall(r'\b[a-zA-ZÀ-ÿ]{4,}\b', text.lower())
    words = [w for w in words if w not in STOPWORDS]
    freq = Counter(words)
    return [w for w,_ in freq.most_common(top_n)]

def extract_authors(text):
    # padrão simples: Nomes Próprios (Capitalizados)
    names = re.findall(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', text)
    return list(set(names))[:10]

def extract_years(text):
    years = re.findall(r'\b(19|20)\d{2}\b', text)
    return list(set(years))

def analyze_document(text):
    return {
        "keywords": extract_keywords(text),
        "authors": extract_authors(text),
        "years": extract_years(text)
    }


# ========================= BUSCA DE ARTIGOS (API ARXIV SIMPLES) =========================
def search_arxiv(query):
    url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=5"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return []

        entries = res.text.split("<entry>")
        results = []

        for e in entries[1:]:
            title = re.search(r"<title>(.*?)</title>", e, re.S)
            summary = re.search(r"<summary>(.*?)</summary>", e, re.S)
            link = re.search(r"<id>(.*?)</id>", e)

            results.append({
                "title": title.group(1).strip() if title else "",
                "summary": summary.group(1).strip()[:300] if summary else "",
                "link": link.group(1) if link else ""
            })

        return results
    except Exception:
        return []


def page_search():
    st.markdown("<h2 class='section-title'>Buscar Artigos Científicos</h2>", unsafe_allow_html=True)

    query = st.text_input("Digite tema ou palavra-chave")

    if st.button("Buscar"):
        results = search_arxiv(query)

        if not results:
            st.warning("Nenhum resultado encontrado")
        else:
            for r in results:
                st.markdown(f"""
                <div class="post-card">
                    <div class="post-title">{r['title']}</div>
                    <div class="post-desc">{r['summary']}</div>
                    <a href="{r['link']}" target="_blank">Abrir artigo</a>
                </div>
                """, unsafe_allow_html=True)


# ========================= ANÁLISE DE IMAGEM =========================
def analyze_image(uploaded_file):
    image = PILImage.open(uploaded_file)
    arr = np.array(image)

    avg_color = arr.mean(axis=(0,1))
    brightness = arr.mean()
    contrast = arr.std()

    return {
        "avg_color": avg_color,
        "brightness": brightness,
        "contrast": contrast
    }

def page_image_analysis():
    st.markdown("<h2 class='section-title'>Análise de Imagem Científica</h2>", unsafe_allow_html=True)

    img = st.file_uploader("Envie uma imagem", type=["png","jpg","jpeg"])

    if img:
        st.image(img, width=300)

        data = analyze_image(img)

        st.write("### Resultados")
        st.write(f"Cor média RGB: {data['avg_color']}")
        st.write(f"Brilho médio: {data['brightness']:.2f}")
        st.write(f"Contraste: {data['contrast']:.2f}")

        # histograma
        arr = np.array(PILImage.open(img))
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=arr[:,:,0].flatten(), name='R'))
        fig.add_trace(go.Histogram(x=arr[:,:,1].flatten(), name='G'))
        fig.add_trace(go.Histogram(x=arr[:,:,2].flatten(), name='B'))
        st.plotly_chart(fig, use_container_width=True)


# ========================= GRAFO DE CONEXÕES =========================
def build_graph():
    users = list(st.session_state.users.keys())
    edges = []

    for u in users:
        for v in users:
            if u != v and random.random() > 0.7:
                edges.append((u,v))

    return users, edges


def page_connections():
    st.markdown("<h2 class='section-title'>Conexões Científicas</h2>", unsafe_allow_html=True)

    users, edges = build_graph()

    if not users:
        st.info("Sem usuários suficientes para gerar grafo")
        return

    pos = {}
    angle = 2 * math.pi / len(users)

    for i,u in enumerate(users):
        pos[u] = (math.cos(i*angle), math.sin(i*angle))

    edge_x = []
    edge_y = []

    for u,v in edges:
        x0,y0 = pos[u]
        x1,y1 = pos[v]
        edge_x += [x0,x1,None]
        edge_y += [y0,y1,None]

    node_x = []
    node_y = []
    texts = []

    for u,(x,y) in pos.items():
        node_x.append(x)
        node_y.append(y)
        texts.append(u)

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=edge_x, y=edge_y,
                             line=dict(width=1),
                             hoverinfo='none',
                             mode='lines'))

    fig.add_trace(go.Scatter(x=node_x, y=node_y,
                             mode='markers+text',
                             text=texts,
                             textposition="top center",
                             marker=dict(size=20)))

    st.plotly_chart(fig, use_container_width=True)


# ========================= INTEGRAR NOVAS PÁGINAS =========================
def router_extra_pages():
    if st.session_state.page == "Buscar":
        page_search()
    elif st.session_state.page == "Imagem":
        page_image_analysis()
    elif st.session_state.page == "Conexões":
        page_connections()
# ========================= OTIMIZAÇÃO DE PERFORMANCE =========================
st.set_option('client.showErrorDetails', False)

# cache leve para evitar recarregar tudo
@st.cache_data
def cached_users():
    return st.session_state.users

@st.cache_data
def cached_posts():
    return st.session_state.feed_posts


# ========================= CARREGAMENTO INICIAL =========================
def init_system():
    db = load_db()

    st.session_state.users = db.get("users", {})
    st.session_state.feed_posts = db.get("feed_posts", [])
    st.session_state.folders = db.get("folders", {})
    st.session_state.user_prefs = db.get("user_prefs", {})
    st.session_state.saved_articles = db.get("saved_articles", [])

    if "current_user" not in st.session_state:
        st.session_state.current_user = "guest"

    if "page" not in st.session_state:
        st.session_state.page = "Feed"


# ========================= MENU PRINCIPAL =========================
def navbar_full():
    cols = st.columns(7)

    menu = ["Feed", "Perfil", "Pastas", "Chat", "Conexões", "Buscar", "Imagem"]

    for i, item in enumerate(menu):
        if cols[i].button(item, use_container_width=True):
            st.session_state.page = item


# ========================= ROTEADOR FINAL =========================
def router():
    page = st.session_state.page

    if page == "Feed":
        page_feed()
    elif page == "Perfil":
        page_profile()
    elif page == "Pastas":
        page_folders()
    elif page == "Chat":
        page_chat()
    elif page == "Conexões":
        page_connections()
    elif page == "Buscar":
        page_search()
    elif page == "Imagem":
        page_image_analysis()
    else:
        page_feed()


# ========================= FOOTER =========================
def footer():
    st.markdown("""
    <hr>
    <div style='text-align:center; opacity:0.6'>
        🔬 Nebula Research Network • Plataforma científica social
    </div>
    """, unsafe_allow_html=True)


# ========================= APP PRINCIPAL =========================
def main():
    init_system()

    # navbar
    navbar_full()

    # conteúdo
    router()

    # rodapé
    footer()

    # salvar banco sempre que algo mudar
    save_db()


# ========================= EXECUÇÃO =========================
if __name__ == "__main__":
    main()
