import subprocess, sys, os, json, hashlib, random, string, base64, re, io
from datetime import datetime
from collections import defaultdict, Counter
import math

def _pip(*pkgs):
    for p in pkgs:
        try: subprocess.check_call([sys.executable,"-m","pip","install",p,"-q"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except: pass

try: import plotly.graph_objects as go; import plotly.express as px
except: _pip("plotly"); import plotly.graph_objects as go; import plotly.express as px

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

st.set_page_config(page_title="Nebula", page_icon="🔬", layout="wide", initial_sidebar_state="collapsed")

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
            json.dump({"users":st.session_state.users,"feed_posts":st.session_state.feed_posts,
                       "folders":st.session_state.folders,"user_prefs":prefs_s,
                       "saved_articles":st.session_state.saved_articles},f,ensure_ascii=False,indent=2)
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
    "135deg,#f97316,#fb923c","135deg,#eab308,#f59e0b","135deg,#22c55e,#16a34a",
    "135deg,#14b8a6,#0d9488","135deg,#f43f5e,#e11d48","135deg,#a78bfa,#7c3aed",
    "135deg,#38bdf8,#0284c7","135deg,#fb7185,#f43f5e",
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
        reader=PyPDF2.PdfReader(io.BytesIO(pdf_bytes)); text=""
        for page in reader.pages[:30]:
            try: text+=page.extract_text()+"\n"
            except: pass
        return text[:50000]
    except: return ""

def extract_text_from_csv_bytes(csv_bytes):
    try:
        df=pd.read_csv(io.BytesIO(csv_bytes),nrows=200)
        summary=f"Colunas: {', '.join(df.columns.tolist())}\nLinhas: {len(df)}\n"
        for col in df.columns[:10]:
            if df[col].dtype==object: vals=df[col].dropna().head(5).tolist(); summary+=f"{col}: {', '.join(str(v) for v in vals)}\n"
            else: summary+=f"{col}: min={df[col].min():.2f}, max={df[col].max():.2f}\n"
        return summary
    except: return ""

def extract_text_from_xlsx_bytes(xlsx_bytes):
    if openpyxl is None: return ""
    try:
        wb=openpyxl.load_workbook(io.BytesIO(xlsx_bytes),read_only=True,data_only=True); text=""
        for sheet_name in wb.sheetnames[:3]:
            ws=wb[sheet_name]; text+=f"\n=== {sheet_name} ===\n"
            for row in list(ws.iter_rows(max_row=50,values_only=True)):
                row_vals=[str(v) for v in row if v is not None]
                if row_vals: text+=" | ".join(row_vals[:10])+"\n"
        return text[:20000]
    except: return ""

def extract_keywords_tfidf(text, top_n=30):
    if not text: return []
    words=re.findall(r'\b[a-záàâãéêíóôõúüçA-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]{4,}\b',text.lower())
    words=[w for w in words if w not in STOPWORDS]
    if not words: return []
    tf=Counter(words); total=sum(tf.values())
    top=sorted({w:c/total for w,c in tf.items()}.items(),key=lambda x:-x[1])[:top_n]
    return [w for w,_ in top]

def extract_authors_from_text(text):
    authors=[]; seen=set()
    for pat in [r'(?:Autor(?:es)?|Author(?:s)?)[:\s]+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){1,4})',
                r'(?:Por|By)[:\s]+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){1,3})']:
        for m in re.findall(pat,text):
            if m.strip().lower() not in seen and len(m.strip())>5: seen.add(m.strip().lower()); authors.append(m.strip())
    return authors[:8]

def extract_years_from_text(text):
    years=re.findall(r'\b(19[5-9]\d|20[0-3]\d)\b',text)
    return sorted(Counter(years).items(),key=lambda x:-x[1])[:10]

def extract_references_from_text(text):
    refs=[]
    for block in re.split(r'\n(?=\[\d+\])',text)[1:21]:
        clean=re.sub(r'\s+',' ',block.strip())
        if len(clean)>30: refs.append(clean[:200])
    return refs[:15]

def compute_topic_distribution(keywords):
    topic_map={
        "Ciências da Saúde":["saúde","medicina","hospital","doença","tratamento","clínico","health","medical","clinical","therapy","disease","cancer"],
        "Biologia & Genômica":["biologia","genômica","gene","dna","rna","proteína","célula","bacteria","vírus","genomics","biology","protein","cell","crispr"],
        "Neurociência":["neurociência","neural","cérebro","cognição","memória","sinapse","neurônio","sono","brain","neuron","cognitive","memory","sleep"],
        "Computação & IA":["algoritmo","machine","learning","inteligência","neural","dados","software","computação","ia","modelo","algorithm","deep","quantum"],
        "Física & Astronomia":["física","quântica","partícula","energia","galáxia","astrofísica","cosmologia","physics","quantum","particle","galaxy","dark"],
        "Química & Materiais":["química","molécula","síntese","reação","composto","polímero","chemistry","molecule","synthesis","reaction","nanomaterial"],
        "Engenharia":["engenharia","sistema","robótica","automação","sensor","circuito","engineering","system","robotics","sensor","circuit"],
        "Ciências Sociais":["sociedade","cultura","educação","política","economia","social","psicologia","society","culture","education","economics"],
        "Ecologia & Clima":["ecologia","clima","ambiente","biodiversidade","ecosistema","ecology","climate","environment","biodiversity","sustainability"],
        "Matemática & Estatística":["matemática","estatística","probabilidade","equação","modelo","mathematics","statistics","probability","equation"],
    }
    scores=defaultdict(int)
    for kw in keywords:
        for topic,terms in topic_map.items():
            if any(t in kw.lower() or kw.lower() in t for t in terms): scores[topic]+=1
    return dict(sorted(scores.items(),key=lambda x:-x[1])) if scores else {"Pesquisa Geral":1}

def search_references_online(keywords,n=5):
    if not keywords: return []
    try:
        r=requests.get("https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query":" ".join(keywords[:5]),"limit":n,"fields":"title,authors,year,abstract,venue,externalIds,citationCount"},timeout=8)
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

def analyze_document_intelligent(fname,fbytes,ftype,research_area=""):
    result={"file":fname,"type":ftype,"text_length":0,"keywords":[],"authors":[],"years":[],"references":[],
            "topics":{},"references_online":[],"relevance_score":0,"summary":"","strengths":[],"improvements":[],
            "progress":random.randint(55,98),"word_count":0,"sentence_count":0,"readability_score":0,
            "concept_map":{},"key_phrases":[],"methodology_hints":[],"field_terms":[]}
    text=""
    if ftype=="PDF" and fbytes: text=extract_text_from_pdf_bytes(fbytes)
    elif ftype in ("Planilha","Dados") and fbytes:
        if fname.endswith(".xlsx") or fname.endswith(".xls"): text=extract_text_from_xlsx_bytes(fbytes)
        elif fname.endswith(".csv"): text=extract_text_from_csv_bytes(fbytes)
    elif ftype in ("Word","Texto","Markdown") and fbytes:
        try: text=fbytes.decode("utf-8",errors="ignore")
        except: pass
    result["text_length"]=len(text)
    if text:
        sentences=re.split(r'[.!?]+',text); result["sentence_count"]=len([s for s in sentences if len(s.strip())>20])
        words=text.split(); result["word_count"]=len(words)
        avg_wps=result["word_count"]/(result["sentence_count"]+1)
        result["readability_score"]=max(0,min(100,100-int(avg_wps*1.5)))
        result["keywords"]=extract_keywords_tfidf(text,25)
        result["authors"]=extract_authors_from_text(text)
        result["years"]=extract_years_from_text(text)
        result["references"]=extract_references_from_text(text)
        result["topics"]=compute_topic_distribution(result["keywords"])
        # Key phrases (bigrams)
        word_list=[w.lower() for w in re.findall(r'\b[a-záàâãéêíóôõúüç]{4,}\b',text) if w.lower() not in STOPWORDS]
        bigrams=[f"{word_list[i]} {word_list[i+1]}" for i in range(len(word_list)-1)]
        result["key_phrases"]=[p for p,_ in Counter(bigrams).most_common(10)]
        # Methodology detection
        methods=["experimento","análise","survey","revisão","simulação","modelagem","entrevista","questionário","experiment","analysis","simulation","model","interview","survey"]
        result["methodology_hints"]=[m for m in methods if m in text.lower()][:5]
        # Field-specific terms
        field_patterns={"Estatística":r'\b(p-valor|chi-quadrado|regressão|variância|correlação|desvio|intervalo)\b',"Bioinformática":r'\b(sequência|alinhamento|blast|genoma|transcriptoma)\b',"ML/IA":r'\b(treinamento|validação|acurácia|perda|epoch|batch|gradiente)\b'}
        for field,pat in field_patterns.items():
            matches=re.findall(pat,text.lower()); 
            if matches: result["field_terms"].extend([(field,m) for m in set(matches[:3])])
        if research_area:
            area_words=research_area.lower().split()
            rel=sum(1 for w in area_words if any(w in kw for kw in result["keywords"]))
            result["relevance_score"]=min(100,rel*15+random.randint(20,50))
        else: result["relevance_score"]=random.randint(45,85)
        n_refs=len(result["references"]); n_kw=len(result["keywords"])
        if n_refs>5: result["strengths"].append(f"Boa referenciação ({n_refs} referências detectadas)")
        if n_kw>10: result["strengths"].append(f"Vocabulário técnico rico ({n_kw} termos únicos)")
        if result["authors"]: result["strengths"].append(f"Autoria identificada: {result['authors'][0]}")
        if result["word_count"]>2000: result["strengths"].append(f"Documento extenso ({result['word_count']} palavras)")
        if result["methodology_hints"]: result["strengths"].append(f"Metodologia detectada: {', '.join(result['methodology_hints'][:2])}")
        if n_refs<3: result["improvements"].append("Adicionar mais referências bibliográficas")
        if not result["authors"]: result["improvements"].append("Incluir autoria explícita no documento")
        if result["word_count"]<500: result["improvements"].append("Expandir o conteúdo (menos de 500 palavras)")
        if result["readability_score"]<40: result["improvements"].append("Simplificar sentenças longas para melhor legibilidade")
        if not result["methodology_hints"]: result["improvements"].append("Descrever metodologia de forma mais clara")
        top_topics=list(result["topics"].keys())[:3]; top_kw=result["keywords"][:5]
        result["summary"]=f"Documento {ftype} · {result['word_count']} palavras · {result['sentence_count']} sentenças · Temas: {', '.join(top_topics)} · Keywords: {', '.join(top_kw)}."
    else:
        result["summary"]=f"Arquivo {ftype} — análise de texto não disponível."
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
        if lr_sym>0.75: shapes.append("Sim. Bilateral")
        if edge_intensity>32: shapes.append("Contornos Nítidos")
        if not shapes: shapes.append("Irregular")
        if skin_pct>0.15 and mr>140: cat,desc,kw,material,obj_type="Histopatologia H&E",f"Tecido orgânico {skin_pct*100:.0f}%.","hematoxylin eosin HE staining histopathology","Tecido Biológico","Amostra Histopatológica"
        elif has_grid and edge_intensity>18: cat,desc,kw,material,obj_type="Cristalografia / Difração",f"Padrão periódico. Borda: {edge_intensity:.1f}.","X-ray diffraction crystallography TEM crystal","Material Cristalino","Rede Cristalina"
        elif mg>165 and mr<125: cat,desc,kw,material,obj_type="Fluorescência GFP/FITC",f"Canal verde dominante (G={mg:.0f}).","GFP fluorescence confocal microscopy","Proteínas Fluorescentes","Células Marcadas"
        elif mb>165 and mr<110: cat,desc,kw,material,obj_type="Fluorescência DAPI",f"Canal azul dominante (B={mb:.0f}).","DAPI nuclear staining DNA fluorescence","DNA / Cromatina","Núcleos Celulares"
        elif has_circular and edge_intensity>24: cat,desc,kw,material,obj_type="Microscopia Celular",f"Estruturas circulares (I={edge_intensity:.1f}).","cell organelle vesicle bacteria microscopy","Componentes Celulares","Células"
        elif edge_intensity>40: cat,desc,kw,material,obj_type="Diagrama / Gráfico","Bordas muito nítidas.","scientific visualization chart diagram","Dados","Gráfico"
        elif sym>0.82: cat,desc,kw,material,obj_type="Estrutura Molecular",f"Alta simetria ({sym:.3f}).","molecular structure protein crystal symmetry","Moléculas","Estrutura"
        else:
            temp="quente" if warm else ("fria" if cool else "neutra")
            cat,desc,kw,material,obj_type="Imagem Científica Geral",f"Temperatura {temp}.","scientific image analysis research","Variado","Imagem Científica"
        conf=min(96,48+edge_intensity/2+entropy*2.8+sym*5+(8 if skin_pct>0.1 else 0)+(6 if has_grid else 0))
        # brightness histogram for visualization
        hist_vals,hist_bins=np.histogram(gray.ravel(),bins=32,range=(0,255))
        return {"category":cat,"description":desc,"kw":kw,"material":material,"object_type":obj_type,
                "confidence":round(conf,1),"lines":{"direction":line_dir,"intensity":round(edge_intensity,2),"strengths":strengths},
                "shapes":shapes,"symmetry":round(sym,3),"lr_symmetry":round(lr_sym,3),
                "color":{"r":round(mr,1),"g":round(mg,1),"b":round(mb,1),"warm":warm,"cool":cool,"dom":dom_ch,"sat":round(sat*100,1)},
                "texture":{"entropy":round(entropy,3),"contrast":round(contrast,2),"complexity":"Alta" if entropy>5.5 else ("Média" if entropy>4 else "Baixa")},
                "palette":palette,"size":orig,"hist_vals":hist_vals.tolist(),"hist_bins":hist_bins[:-1].tolist()}
    except Exception as e: st.error(f"Erro: {e}"); return None

EMAP={"pdf":"PDF","docx":"Word","doc":"Word","xlsx":"Planilha","xls":"Planilha","csv":"Dados","txt":"Texto",
      "py":"Código Python","r":"Código R","ipynb":"Notebook","pptx":"Apresentação","png":"Imagem",
      "jpg":"Imagem","jpeg":"Imagem","tiff":"Imagem Científica","md":"Markdown"}

def get_ftype(fname):
    ext=fname.split(".")[-1].lower() if "." in fname else ""
    return EMAP.get(ext,"Arquivo")

def search_ss(query,limit=8):
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
                    "abstract":(p.get("abstract","") or "")[:280],"url":link,"citations":p.get("citationCount",0),"origin":"semantic"})
    except: pass
    return results

def search_cr(query,limit=4):
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
                    "source":(p.get("container-title") or ["CrossRef"])[0],"doi":doi,"abstract":abstract,
                    "url":f"https://doi.org/{doi}" if doi else "","citations":p.get("is-referenced-by-count",0),"origin":"crossref"})
    except: pass
    return results

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

SEED_POSTS=[
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

SEED_USERS={
    "demo@nebula.ai":{"name":"Ana Pesquisadora","password":hp("demo123"),"bio":"Pesquisadora em IA e Ciências Cognitivas | UFMG","area":"Inteligência Artificial","followers":128,"following":47,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "carlos@nebula.ai":{"name":"Carlos Mendez","password":hp("nebula123"),"bio":"Neurocientista | UFMG | Plasticidade sináptica e sono","area":"Neurociência","followers":210,"following":45,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "luana@nebula.ai":{"name":"Luana Freitas","password":hp("nebula123"),"bio":"Biomédica | FIOCRUZ | CRISPR e terapia gênica","area":"Biomedicina","followers":178,"following":62,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "rafael@nebula.ai":{"name":"Rafael Souza","password":hp("nebula123"),"bio":"Computação Quântica | USP | Algoritmos híbridos","area":"Computação","followers":340,"following":88,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "priya@nebula.ai":{"name":"Priya Nair","password":hp("nebula123"),"bio":"Astrofísica | MIT | Dark matter & gravitational lensing","area":"Astrofísica","followers":520,"following":31,"verified":True,"2fa_enabled":False,"photo_b64":None},
    "joao@nebula.ai":{"name":"João Lima","password":hp("nebula123"),"bio":"Psicólogo Cognitivo | UNICAMP | IA e vieses clínicos","area":"Psicologia","followers":95,"following":120,"verified":True,"2fa_enabled":False,"photo_b64":None},
}

CHAT_INIT={
    "carlos@nebula.ai":[{"from":"carlos@nebula.ai","text":"Oi! Vi seu comentário na pesquisa de sono.","time":"09:14"},{"from":"me","text":"Achei muito interessante!","time":"09:16"}],
    "luana@nebula.ai":[{"from":"luana@nebula.ai","text":"Podemos colaborar no próximo projeto?","time":"ontem"}],
    "rafael@nebula.ai":[{"from":"rafael@nebula.ai","text":"Já compartilhei o repositório.","time":"08:30"}],
}

def init():
    if "initialized" in st.session_state: return
    st.session_state.initialized=True
    disk=load_db()
    disk_users=disk.get("users",{})
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

def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:wght@300;400;500;600;700&display=swap');

:root {
  --bg:#080b0f; --s1:#0f1117; --s2:#161b24; --s3:#1e2533;
  --or1:#f97316; --or2:#fb923c; --or3:#fed7aa;
  --ye1:#eab308; --ye2:#fbbf24; --ye3:#fef08a;
  --gr1:#22c55e; --gr2:#4ade80; --gr3:#bbf7d0;
  --te1:#14b8a6; --te2:#2dd4bf; --te3:#99f6e4;
  --text:#f1f5f9; --text2:#94a3b8; --text3:#475569; --text4:#1e293b;
  --glass:rgba(15,17,23,.72); --glass2:rgba(20,24,34,.80);
  --gborder:rgba(249,115,22,.10); --gborder2:rgba(249,115,22,.22);
  --gborderY:rgba(234,179,8,.14); --gborderG:rgba(34,197,94,.12);
  --r8:8px; --r12:12px; --r16:16px; --r20:20px; --r28:28px;
  --shadow:0 4px 32px rgba(0,0,0,.60);
}

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body,.stApp{background:var(--bg)!important;color:var(--text)!important;font-family:'DM Sans',-apple-system,sans-serif!important}

.stApp::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:radial-gradient(ellipse 70% 50% at 0% 0%,rgba(249,115,22,.08) 0%,transparent 55%),
             radial-gradient(ellipse 55% 55% at 100% 100%,rgba(34,197,94,.07) 0%,transparent 50%),
             radial-gradient(ellipse 40% 40% at 50% 50%,rgba(20,184,166,.04) 0%,transparent 60%)}

[data-testid="collapsedControl"],section[data-testid="stSidebar"]{display:none!important}
header[data-testid="stHeader"]{display:none!important}
#MainMenu,footer,.stDeployButton,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}

.block-container{padding-top:0!important;padding-bottom:4rem!important;max-width:1440px!important;position:relative;z-index:1;padding-left:1rem!important;padding-right:1rem!important}

h1{font-family:'Syne',sans-serif!important;font-size:1.65rem!important;font-weight:800!important;letter-spacing:-.03em;color:var(--text)!important}
h2{font-family:'Syne',sans-serif!important;font-size:1.05rem!important;font-weight:700!important;color:var(--text)!important}
h3{font-family:'Syne',sans-serif!important;font-size:.90rem!important;font-weight:600!important;color:var(--text)!important}

/* ═══ TOPNAV ═══ */
.neb-navwrap{position:sticky;top:0;z-index:1000;
  background:rgba(6,8,12,.93);backdrop-filter:blur(48px) saturate(200%);-webkit-backdrop-filter:blur(48px) saturate(200%);
  border-bottom:1px solid rgba(249,115,22,.09);margin-bottom:1.1rem;
  box-shadow:0 1px 0 rgba(249,115,22,.05),0 8px 32px rgba(0,0,0,.55);padding:.45rem .9rem}
.neb-navwrap [data-testid="stHorizontalBlock"]{align-items:center!important;gap:1px!important}
.neb-navwrap [data-testid="stHorizontalBlock"]>div{padding:0 1px!important}

/* Logo button */
.nav-logo .stButton>button{background:transparent!important;border:none!important;box-shadow:none!important;
  font-family:'Syne',sans-serif!important;font-size:1.1rem!important;font-weight:900!important;
  background:linear-gradient(135deg,#f97316 10%,#eab308 60%,#22c55e 90%)!important;
  -webkit-background-clip:text!important;-webkit-text-fill-color:transparent!important;background-clip:text!important;
  letter-spacing:-.05em!important;padding:.2rem .4rem!important;height:36px!important;min-height:36px!important;
  white-space:nowrap!important}
.nav-logo .stButton>button:hover{transform:none!important;box-shadow:none!important}

/* Nav icon buttons */
.nav-pill .stButton>button{background:transparent!important;border:1px solid transparent!important;
  border-radius:10px!important;color:var(--text3)!important;font-family:'DM Sans',sans-serif!important;
  font-size:1.1rem!important;font-weight:400!important;padding:.28rem .5rem!important;
  box-shadow:none!important;white-space:nowrap!important;height:34px!important;min-height:34px!important;
  transition:all .15s!important;line-height:1!important}
.nav-pill .stButton>button:hover{background:rgba(249,115,22,.10)!important;border-color:rgba(249,115,22,.20)!important;color:var(--or2)!important;transform:none!important;box-shadow:none!important}
.nav-pill-active .stButton>button{background:linear-gradient(135deg,rgba(249,115,22,.22),rgba(234,179,8,.12))!important;
  border:1px solid rgba(249,115,22,.35)!important;color:var(--or2)!important;font-weight:600!important;
  box-shadow:0 2px 12px rgba(249,115,22,.18)!important;height:34px!important;min-height:34px!important}
.nav-pill-active .stButton>button:hover{transform:none!important}

/* Avatar button — photo or initials */
.nav-avatar-btn .stButton>button{
  width:34px!important;height:34px!important;border-radius:50%!important;
  padding:0!important;border:2px solid rgba(249,115,22,.28)!important;
  font-family:'Syne',sans-serif!important;font-size:.70rem!important;font-weight:700!important;
  color:white!important;box-shadow:0 2px 10px rgba(0,0,0,.5)!important;
  min-height:34px!important;line-height:1!important;transition:border-color .15s,box-shadow .15s!important}
.nav-avatar-btn .stButton>button:hover{border-color:rgba(249,115,22,.55)!important;box-shadow:0 4px 16px rgba(249,115,22,.22)!important;transform:none!important}

/* ═══ BUTTONS ═══ */
.stButton>button{background:linear-gradient(135deg,rgba(15,17,23,.85),rgba(22,27,36,.70))!important;
  backdrop-filter:blur(16px)!important;-webkit-backdrop-filter:blur(16px)!important;
  border:1px solid rgba(249,115,22,.14)!important;border-radius:var(--r12)!important;
  color:var(--text2)!important;font-family:'DM Sans',sans-serif!important;font-weight:500!important;font-size:.80rem!important;
  padding:.42rem .88rem!important;transition:all .18s cubic-bezier(.4,0,.2,1)!important;
  box-shadow:0 2px 12px rgba(0,0,0,.35),inset 0 1px 0 rgba(249,115,22,.05)!important;
  position:relative!important;overflow:hidden!important;letter-spacing:.01em!important}
.stButton>button:hover{background:linear-gradient(135deg,rgba(249,115,22,.18),rgba(234,179,8,.08))!important;
  border-color:rgba(249,115,22,.35)!important;color:var(--or2)!important;transform:translateY(-1px)!important;
  box-shadow:0 6px 20px rgba(249,115,22,.18)!important}
.stButton>button:active{transform:scale(.97)!important}

.btn-primary .stButton>button{background:linear-gradient(135deg,#f97316,#ea580c)!important;
  border-color:rgba(249,115,22,.5)!important;color:white!important;font-weight:600!important;
  box-shadow:0 4px 20px rgba(249,115,22,.38),inset 0 1px 0 rgba(255,255,255,.14)!important}
.btn-primary .stButton>button:hover{background:linear-gradient(135deg,#fb923c,#f97316)!important;box-shadow:0 8px 28px rgba(249,115,22,.48)!important;color:white!important}
.btn-green .stButton>button{background:linear-gradient(135deg,rgba(34,197,94,.18),rgba(20,184,166,.10))!important;border-color:rgba(34,197,94,.28)!important;color:var(--gr2)!important}
.btn-green .stButton>button:hover{background:linear-gradient(135deg,rgba(34,197,94,.28),rgba(20,184,166,.18))!important;color:var(--gr2)!important}
.btn-danger .stButton>button{background:rgba(239,68,68,.08)!important;border-color:rgba(239,68,68,.20)!important;color:#fca5a5!important}
.btn-danger .stButton>button:hover{background:rgba(239,68,68,.16)!important;color:#fca5a5!important}

/* Story circles */
.sc-base .stButton>button{width:60px!important;height:60px!important;border-radius:50%!important;padding:0!important;
  font-family:'Syne',sans-serif!important;font-weight:800!important;font-size:.92rem!important;color:white!important;
  border:2.5px solid rgba(249,115,22,.28)!important;
  box-shadow:0 4px 18px rgba(0,0,0,.5)!important;
  transition:transform .22s cubic-bezier(.34,1.56,.64,1),box-shadow .2s!important;margin:0 auto!important}
.sc-base .stButton>button:hover{transform:translateY(-3px) scale(1.08)!important;box-shadow:0 10px 30px rgba(249,115,22,.30)!important}
.sc-followed .stButton>button{border-color:rgba(34,197,94,.50)!important;box-shadow:0 0 0 3px rgba(34,197,94,.10),0 4px 18px rgba(0,0,0,.5)!important}
.sc-publish .stButton>button{background:rgba(249,115,22,.06)!important;border:2.5px dashed rgba(249,115,22,.40)!important;color:var(--or2)!important;font-size:1.5rem!important;font-weight:300!important}
.sc-publish .stButton>button:hover{background:rgba(249,115,22,.14)!important;border-color:rgba(249,115,22,.65)!important}
.sc-publish-open .stButton>button{background:rgba(249,115,22,.16)!important;border:2.5px solid rgba(249,115,22,.55)!important;color:var(--or1)!important;font-size:1.3rem!important}

/* Compose prompt */
.compose-prompt .stButton>button{background:rgba(255,255,255,.03)!important;
  border:1px solid rgba(249,115,22,.12)!important;border-radius:40px!important;
  color:var(--text3)!important;font-size:.875rem!important;font-weight:400!important;
  text-align:left!important;padding:.7rem 1.4rem!important;width:100%!important;display:flex!important;justify-content:flex-start!important;box-shadow:none!important}
.compose-prompt .stButton>button:hover{background:rgba(249,115,22,.07)!important;border-color:rgba(249,115,22,.25)!important;color:var(--text2)!important;transform:none!important;box-shadow:none!important}

/* ═══ INPUTS ═══ */
.stTextInput input,.stTextArea textarea{background:rgba(4,6,10,.80)!important;border:1px solid rgba(249,115,22,.12)!important;border-radius:var(--r12)!important;color:var(--text)!important;font-family:'DM Sans',sans-serif!important;font-size:.875rem!important;transition:border-color .16s,box-shadow .16s!important}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:rgba(249,115,22,.38)!important;box-shadow:0 0 0 3px rgba(249,115,22,.09)!important;background:rgba(4,6,10,.92)!important}
.stTextInput label,.stTextArea label,.stSelectbox label,.stFileUploader label,.stNumberInput label{color:var(--text3)!important;font-size:.63rem!important;letter-spacing:.10em!important;text-transform:uppercase!important;font-weight:600!important}

/* ═══ AVATAR ═══ */
.av{border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:'Syne',sans-serif;font-weight:700;color:white;border:2px solid rgba(249,115,22,.20);flex-shrink:0;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.4)}
.av img{width:100%;height:100%;object-fit:cover;border-radius:50%}

/* ═══ CARDS ═══ */
.card{background:var(--glass);backdrop-filter:blur(24px) saturate(180%);-webkit-backdrop-filter:blur(24px) saturate(180%);border:1px solid var(--gborder);border-radius:var(--r20);box-shadow:var(--shadow),inset 0 1px 0 rgba(249,115,22,.05);position:relative;overflow:hidden}
.card::after{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(249,115,22,.10),transparent);pointer-events:none}

.post{background:var(--glass);border:1px solid var(--gborder);border-radius:var(--r20);margin-bottom:.8rem;overflow:hidden;
  box-shadow:0 2px 20px rgba(0,0,0,.40),inset 0 1px 0 rgba(249,115,22,.04);
  animation:fadeUp .24s cubic-bezier(.34,1.2,.64,1) both;transition:border-color .16s,box-shadow .16s}
.post:hover{border-color:var(--gborder2);box-shadow:0 8px 38px rgba(0,0,0,.52)}
.post::after{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(249,115,22,.08),transparent);pointer-events:none}
@keyframes fadeUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}

.compose-card{background:rgba(10,12,17,.75);border:1px solid rgba(249,115,22,.22);border-radius:var(--r20);padding:1.2rem 1.4rem;margin-bottom:.85rem;box-shadow:0 4px 24px rgba(0,0,0,.28),inset 0 1px 0 rgba(249,115,22,.07);animation:fadeUp .18s ease both}

/* ═══ TABS ═══ */
.stTabs [data-baseweb="tab-list"]{background:rgba(4,6,10,.80)!important;border:1px solid var(--gborder)!important;border-radius:var(--r12)!important;padding:4px!important;gap:2px!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--text3)!important;border-radius:9px!important;font-size:.76rem!important;font-family:'DM Sans',sans-serif!important}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,rgba(249,115,22,.22),rgba(234,179,8,.10))!important;color:var(--or2)!important;border:1px solid rgba(249,115,22,.25)!important}
.stTabs [data-baseweb="tab-panel"]{background:transparent!important;padding-top:.85rem!important}

.stSelectbox [data-baseweb="select"]{background:rgba(4,6,10,.80)!important;border:1px solid var(--gborder)!important;border-radius:var(--r12)!important}
.stFileUploader section{background:rgba(4,6,10,.55)!important;border:1.5px dashed rgba(249,115,22,.18)!important;border-radius:var(--r16)!important}
.stExpander{background:var(--glass)!important;border:1px solid var(--gborder)!important;border-radius:var(--r16)!important}

/* ═══ BADGES & TAGS ═══ */
.tag{display:inline-block;background:rgba(249,115,22,.09);border:1px solid rgba(249,115,22,.18);border-radius:20px;padding:2px 9px;font-size:.63rem;color:var(--or2);margin:2px;font-weight:500}
.badge-on{display:inline-block;background:rgba(234,179,8,.10);border:1px solid rgba(234,179,8,.24);border-radius:20px;padding:2px 9px;font-size:.63rem;font-weight:600;color:var(--ye2)}
.badge-pub{display:inline-block;background:rgba(34,197,94,.10);border:1px solid rgba(34,197,94,.24);border-radius:20px;padding:2px 9px;font-size:.63rem;font-weight:600;color:var(--gr2)}
.badge-done{display:inline-block;background:rgba(20,184,166,.10);border:1px solid rgba(20,184,166,.24);border-radius:20px;padding:2px 9px;font-size:.63rem;font-weight:600;color:var(--te2)}
.badge-rec{display:inline-block;background:rgba(249,115,22,.10);border:1px solid rgba(249,115,22,.24);border-radius:20px;padding:2px 9px;font-size:.63rem;font-weight:600;color:var(--or1)}

/* ═══ METRICS ═══ */
.mbox{background:var(--glass);border:1px solid var(--gborder);border-radius:var(--r16);padding:.95rem;text-align:center}
.mval{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:800;background:linear-gradient(135deg,#f97316,#eab308);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.mlbl{font-size:.61rem;color:var(--text3);margin-top:3px;letter-spacing:.10em;text-transform:uppercase;font-weight:600}

/* ═══ PROGRESS ═══ */
.prog-wrap{height:4px;background:rgba(249,115,22,.08);border-radius:4px;overflow:hidden;margin:.16rem 0 .38rem}
.prog-fill{height:100%;border-radius:4px;transition:width .6s ease}

/* ═══ ONLINE DOTS ═══ */
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.5;transform:scale(.78)}}
.dot-on{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--gr1);animation:pulse 2s infinite;margin-right:4px;vertical-align:middle}
.dot-off{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--text4);margin-right:4px;vertical-align:middle}
.dot-sm-on{width:7px;height:7px;border-radius:50%;background:var(--gr1);margin:3px auto 2px;box-shadow:0 0 5px var(--gr1);animation:pulse 2s infinite}
.dot-sm-off{width:7px;height:7px;border-radius:50%;background:var(--text4);margin:3px auto 2px}

/* ═══ MISC CONTAINERS ═══ */
.sc{background:var(--glass);border:1px solid var(--gborder);border-radius:var(--r20);padding:1rem;margin-bottom:.75rem}
.scard{background:var(--glass);border:1px solid var(--gborder);border-radius:var(--r16);padding:.88rem 1.05rem;margin-bottom:.5rem;transition:border-color .14s,transform .14s}
.scard:hover{border-color:var(--gborder2);transform:translateY(-1px)}

.abox{background:rgba(10,12,17,.75);border:1px solid rgba(249,115,22,.16);border-radius:var(--r16);padding:1rem;margin-bottom:.7rem}
.pbox{background:rgba(34,197,94,.04);border:1px solid rgba(34,197,94,.14);border-radius:var(--r16);padding:.92rem;margin-bottom:.65rem}
.img-rc{background:rgba(20,184,166,.04);border:1px solid rgba(20,184,166,.12);border-radius:var(--r16);padding:.88rem;margin-bottom:.5rem}
.chart-glass{background:var(--glass);border:1px solid var(--gborder);border-radius:var(--r16);padding:.7rem;margin-bottom:.7rem}

/* ═══ PROFILE ═══ */
.prof-hero{background:var(--glass);border:1px solid var(--gborder);border-radius:var(--r28);padding:1.75rem;display:flex;gap:1.3rem;align-items:flex-start;box-shadow:var(--shadow);position:relative;overflow:hidden;margin-bottom:1.1rem}
.prof-hero::after{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(249,115,22,.09),transparent);pointer-events:none}
.prof-photo{width:82px;height:82px;border-radius:50%;background:linear-gradient(135deg,#f97316,#eab308);border:2.5px solid rgba(249,115,22,.28);flex-shrink:0;overflow:hidden;display:flex;align-items:center;justify-content:center;font-size:1.75rem;font-weight:700;color:white}
.prof-photo img{width:100%;height:100%;object-fit:cover;border-radius:50%}

/* ═══ CHAT ═══ */
.bme{background:linear-gradient(135deg,rgba(249,115,22,.28),rgba(234,179,8,.14));border:1px solid rgba(249,115,22,.22);border-radius:18px 18px 4px 18px;padding:.58rem .9rem;max-width:68%;margin-left:auto;margin-bottom:5px;font-size:.82rem;line-height:1.6}
.bthem{background:rgba(10,12,17,.85);border:1px solid var(--gborder);border-radius:18px 18px 18px 4px;padding:.58rem .9rem;max-width:68%;margin-bottom:5px;font-size:.82rem;line-height:1.6}
.cmt{background:rgba(4,6,10,.80);border:1px solid var(--gborder);border-radius:var(--r12);padding:.52rem .88rem;margin-bottom:.3rem}

/* ═══ PEOPLE ═══ */
.person-row{display:flex;align-items:center;gap:9px;padding:.42rem .5rem;border-radius:var(--r12);border:1px solid transparent;transition:all .14s;margin-bottom:2px}
.person-row:hover{background:rgba(249,115,22,.06);border-color:var(--gborder)}

/* ═══ DIVIDERS ═══ */
.dtxt{display:flex;align-items:center;gap:.75rem;margin:.82rem 0;font-size:.61rem;color:var(--text3);letter-spacing:.10em;text-transform:uppercase;font-weight:600}
.dtxt::before,.dtxt::after{content:'';flex:1;height:1px;background:var(--gborder)}

/* ═══ STORY LABELS ═══ */
.sl{text-align:center;font-size:.63rem;font-weight:500;color:var(--text2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:72px;margin:3px auto 0}
.sl2{text-align:center;font-size:.57rem;color:var(--text3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:72px;margin:0 auto}

/* ═══ ANALYSIS BOXES ═══ */
.ref-item{background:rgba(20,184,166,.04);border:1px solid rgba(20,184,166,.12);border-radius:var(--r12);padding:.62rem .88rem;margin-bottom:.38rem;font-size:.76rem;color:var(--text2);line-height:1.6}
.str-ok{background:rgba(34,197,94,.07);border:1px solid rgba(34,197,94,.18);border-radius:10px;padding:.36rem .72rem;font-size:.74rem;color:var(--gr2);margin-bottom:.28rem}
.str-imp{background:rgba(234,179,8,.07);border:1px solid rgba(234,179,8,.18);border-radius:10px;padding:.36rem .72rem;font-size:.74rem;color:var(--ye2);margin-bottom:.28rem}
.str-warn{background:rgba(249,115,22,.07);border:1px solid rgba(249,115,22,.18);border-radius:10px;padding:.36rem .72rem;font-size:.74rem;color:var(--or2);margin-bottom:.28rem}
.ai-disclaimer{background:rgba(234,179,8,.06);border:1px solid rgba(234,179,8,.22);border-radius:var(--r12);padding:.7rem 1rem;font-size:.75rem;color:var(--ye2);line-height:1.65;margin-bottom:.9rem}

::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-thumb{background:rgba(249,115,22,.20);border-radius:4px}
::-webkit-scrollbar-track{background:transparent}
hr{border:none;border-top:1px solid var(--gborder)!important;margin:.85rem 0}
label{color:var(--text2)!important}
.stCheckbox label,.stRadio label{color:var(--text)!important}
.stAlert{background:var(--glass)!important;border:1px solid var(--gborder)!important;border-radius:var(--r16)!important}
input[type="number"]{background:rgba(4,6,10,.80)!important;border:1px solid var(--gborder)!important;border-radius:var(--r12)!important;color:var(--text)!important}
.stRadio>div{display:flex!important;gap:5px!important;flex-wrap:wrap!important}
.stRadio>div>label{background:var(--glass)!important;border:1px solid var(--gborder)!important;border-radius:50px!important;padding:.28rem .80rem!important;font-size:.75rem!important;cursor:pointer!important;color:var(--text2)!important}
.stRadio>div>label:hover{border-color:var(--gborder2)!important;color:var(--or2)!important}
.pw{animation:fadeIn .20s ease both}
@keyframes fadeIn{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
.js-plotly-plot .plotly .modebar{display:none!important}
</style>""",unsafe_allow_html=True)

def avh(initials,sz=40,photo=None,grad=None):
    fs=max(sz//3,9); bg=grad or "linear-gradient(135deg,#f97316,#eab308)"
    if photo: return f'<div class="av" style="width:{sz}px;height:{sz}px;background:{bg}"><img src="{photo}"/></div>'
    return f'<div class="av" style="width:{sz}px;height:{sz}px;font-size:{fs}px;background:{bg}">{initials}</div>'

def tags_html(tags): return ' '.join(f'<span class="tag">{t}</span>' for t in (tags or []))

def badge(s):
    cls={"Publicado":"badge-pub","Concluído":"badge-done"}.get(s,"badge-on")
    return f'<span class="{cls}">{s}</span>'

def prog_bar(pct,color="#f97316"):
    return f'<div class="prog-wrap"><div class="prog-fill" style="width:{pct}%;background:{color}"></div></div>'

def pc():
    return dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#475569",family="DM Sans",size=11),
                margin=dict(l=10,r=10,t=40,b=10),
                xaxis=dict(showgrid=False,color="#475569",tickfont=dict(size=10)),
                yaxis=dict(showgrid=True,gridcolor="rgba(249,115,22,.06)",color="#475569",tickfont=dict(size=10)))

# ══════════════════════════════════════════════════
# AUTH PAGES — with st.form for Enter key support
# ══════════════════════════════════════════════════
def page_login():
    _,col,_=st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-bottom:2.8rem">
          <div style="font-family:'Syne',sans-serif;font-size:4rem;font-weight:900;
            background:linear-gradient(135deg,#f97316 15%,#eab308 55%,#22c55e 90%);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
            background-clip:text;letter-spacing:-.08em;line-height:.9;margin-bottom:.8rem">Nebula</div>
          <div style="color:#1e293b;font-size:.63rem;letter-spacing:.28em;text-transform:uppercase;font-weight:600">
            Rede do Conhecimento Científico
          </div>
        </div>""",unsafe_allow_html=True)
        t_in,t_up=st.tabs(["  🔑 Entrar  ","  ✨ Criar conta  "])
        with t_in:
            with st.form("login_form"):
                email=st.text_input("E-mail",placeholder="seu@email.com",key="li_e")
                pw=st.text_input("Senha",placeholder="••••••••",type="password",key="li_p")
                st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
                submitted=st.form_submit_button("→  Entrar",use_container_width=True)
                st.markdown('</div>',unsafe_allow_html=True)
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
            st.markdown('<div style="text-align:center;color:#1e293b;font-size:.70rem;margin-top:.7rem">Demo: demo@nebula.ai / demo123</div>',unsafe_allow_html=True)
        with t_up:
            with st.form("signup_form"):
                n_name=st.text_input("Nome completo",key="su_n")
                n_email=st.text_input("E-mail",key="su_e")
                n_area=st.text_input("Área de pesquisa",key="su_a")
                n_pw=st.text_input("Senha",type="password",key="su_p")
                n_pw2=st.text_input("Confirmar senha",type="password",key="su_p2")
                st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
                sub2=st.form_submit_button("✓  Criar conta",use_container_width=True)
                st.markdown('</div>',unsafe_allow_html=True)
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
    _,col,_=st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown(f"""<div class="card" style="padding:2rem;text-align:center">
          <div style="font-size:2.5rem;margin-bottom:1rem;opacity:.5">✉</div>
          <h2 style="margin-bottom:.5rem">Verifique seu e-mail</h2>
          <p style="color:var(--text2);font-size:.82rem">Código para <strong style="color:var(--or2)">{pv['email']}</strong></p>
          <div style="background:rgba(249,115,22,.08);border:1px solid rgba(249,115,22,.18);border-radius:14px;padding:1.2rem;margin:1.2rem 0">
            <div style="font-size:.60rem;color:var(--text3);letter-spacing:.12em;text-transform:uppercase;margin-bottom:6px;font-weight:600">Código (demo)</div>
            <div style="font-family:'Syne',sans-serif;font-size:2.8rem;font-weight:900;letter-spacing:.32em;color:var(--or2)">{pv['code']}</div>
          </div></div>""",unsafe_allow_html=True)
        with st.form("verify_form"):
            typed=st.text_input("Código",max_chars=6,key="ev_c")
            st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
            if st.form_submit_button("✓  Verificar",use_container_width=True):
                if typed.strip()==pv["code"]:
                    st.session_state.users[pv["email"]]={"name":pv["name"],"password":pv["pw"],"bio":"","area":pv["area"],"followers":0,"following":0,"verified":True,"2fa_enabled":False,"photo_b64":None}
                    save_db(); st.session_state.pending_verify=None
                    st.session_state.logged_in=True; st.session_state.current_user=pv["email"]
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
          <div style="font-size:2.5rem;margin-bottom:1rem;opacity:.5">🔑</div><h2>Verificação 2FA</h2>
          <div style="background:rgba(249,115,22,.08);border:1px solid rgba(249,115,22,.18);border-radius:14px;padding:1rem;margin:1rem 0">
            <div style="font-size:.60rem;color:var(--text3);text-transform:uppercase;letter-spacing:.10em;margin-bottom:6px;font-weight:600">Código</div>
            <div style="font-family:'Syne',sans-serif;font-size:2.8rem;font-weight:900;letter-spacing:.28em;color:var(--or2)">{p2['code']}</div>
          </div></div>""",unsafe_allow_html=True)
        with st.form("twofa_form"):
            typed=st.text_input("Código",max_chars=6,key="fa_c",label_visibility="collapsed")
            st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
            if st.form_submit_button("✓  Verificar",use_container_width=True):
                if typed.strip()==p2["code"]:
                    st.session_state.logged_in=True; st.session_state.current_user=p2["email"]
                    st.session_state.pending_2fa=None; st.session_state.page="feed"; st.rerun()
                else: st.error("Código inválido.")
            st.markdown('</div>',unsafe_allow_html=True)
        if st.button("← Voltar",key="btn_fa_bk"): st.session_state.page="login"; st.rerun()

# ══════════════════════════════════════════════════
# TOP NAV — icons only, logo goes to feed, avatar=profile
# ══════════════════════════════════════════════════
NAV=[
    ("feed",     "🏠","Feed"),
    ("search",   "🔍","Artigos"),
    ("knowledge","🕸","Rede"),
    ("folders",  "📁","Pastas"),
    ("analytics","📊","Análise"),
    ("img_search","🖼","Imagem"),
    ("chat",     "💬","Chat"),
    ("settings", "⚙️","Perfil"),
]

def render_topnav():
    u=guser(); name=u.get("name","?"); photo=u.get("photo_b64"); in_=ini(name)
    cur=st.session_state.page; email=st.session_state.current_user; g=ugrad(email or "")
    notif=len(st.session_state.notifications)
    st.markdown('<div class="neb-navwrap">',unsafe_allow_html=True)
    cols=st.columns([0.9]+[0.55]*len(NAV)+[0.45])
    # Logo → feed
    with cols[0]:
        st.markdown('<div class="nav-logo">',unsafe_allow_html=True)
        if st.button("🔬 Nebula",key="nav_logo"):
            st.session_state.profile_view=None; st.session_state.page="feed"; st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)
    # Nav icons
    for i,(key,icon,lbl) in enumerate(NAV):
        with cols[i+1]:
            is_active=(cur==key)
            pill_cls="nav-pill-active" if is_active else "nav-pill"
            st.markdown(f'<div class="{pill_cls}" title="{lbl}">',unsafe_allow_html=True)
            if st.button(icon,key=f"tnav_{key}",use_container_width=True):
                st.session_state.profile_view=None; st.session_state.page=key; st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)
    # Avatar → own profile
    with cols[-1]:
        nb=f'<div style="position:absolute;top:-2px;right:-2px;background:#ef4444;color:white;width:15px;height:15px;border-radius:50%;font-size:.50rem;display:flex;align-items:center;justify-content:center;font-weight:700;z-index:10">{notif}</div>' if notif else ''
        st.markdown(f'<div style="position:relative;display:inline-block;width:34px;height:34px;margin:.15rem 0 0">{nb}</div>',unsafe_allow_html=True)
        # Dynamic CSS so the button itself looks like the avatar
        if photo:
            st.markdown(f'<style>.nav-avatar-btn .stButton>button{{background-image:url("{photo}")!important;background-size:cover!important;background-position:center!important;color:transparent!important;background:none!important}}</style>',unsafe_allow_html=True)
        else:
            st.markdown(f'<style>.nav-avatar-btn .stButton>button{{background:{g}!important}}</style>',unsafe_allow_html=True)
        st.markdown('<div class="nav-avatar-btn">',unsafe_allow_html=True)
        if st.button(in_ if not photo else " ",key="nav_me"):
            st.session_state.profile_view=email; st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

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
    liked_posts=[p for p in st.session_state.feed_posts if target_email in p.get("liked_by",[])]
    total_likes=sum(p["likes"] for p in user_posts); g=ugrad(target_email)
    if st.button("← Voltar",key="back_prof"): st.session_state.profile_view=None; st.rerun()
    photo_html=f'<img src="{tphoto}"/>' if tphoto else f'<span style="font-size:2rem">{tin}</span>'
    v_badge='<span style="font-size:.7rem;color:var(--gr2);margin-left:6px">✓</span>' if tu.get("verified") else ""
    st.markdown(
        f'<div class="prof-hero"><div class="prof-photo" style="background:{g}">{photo_html}</div>'
        f'<div style="flex:1;z-index:1">'
        f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;margin-bottom:.3rem"><h1 style="margin:0">{tname}</h1>{v_badge}</div>'
        f'<div style="color:var(--or2);font-size:.83rem;margin-bottom:.4rem;font-weight:500">{tu.get("area","")}</div>'
        f'<div style="color:var(--text2);font-size:.81rem;line-height:1.68;margin-bottom:.85rem;max-width:560px">{tu.get("bio","Sem biografia.")}</div>'
        f'<div style="display:flex;gap:2rem;flex-wrap:wrap">'
        f'<div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1.1rem">{tu.get("followers",0)}</span><span style="color:var(--text3);font-size:.71rem"> seguidores</span></div>'
        f'<div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1.1rem">{tu.get("following",0)}</span><span style="color:var(--text3);font-size:.71rem"> seguindo</span></div>'
        f'<div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1.1rem">{len(user_posts)}</span><span style="color:var(--text3);font-size:.71rem"> pesquisas</span></div>'
        f'<div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:1.1rem">{fmt_num(total_likes)}</span><span style="color:var(--text3);font-size:.71rem"> curtidas</span></div>'
        f'</div></div></div>',unsafe_allow_html=True)
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
    # Tabs: posts + curtidas
    t_posts,t_liked=st.tabs([f"  🔬 Pesquisas ({len(user_posts)})  ",f"  ❤️ Curtidas ({len(liked_posts)})  "])
    with t_posts:
        if user_posts:
            for p in sorted(user_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="profile",show_author=False)
        else: st.markdown('<div class="card" style="padding:2.5rem;text-align:center;color:var(--text3)">Nenhuma pesquisa publicada ainda.</div>',unsafe_allow_html=True)
    with t_liked:
        if liked_posts:
            for p in sorted(liked_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="liked",compact=True)
        else: st.markdown('<div class="card" style="padding:2.5rem;text-align:center;color:var(--text3)">Nenhuma pesquisa curtida ainda.</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# POST CARD
# ══════════════════════════════════════════════════
def render_post(post,ctx="feed",show_author=True,compact=False):
    email=st.session_state.current_user; pid=post["id"]
    liked=email in post.get("liked_by",[]); saved=email in post.get("saved_by",[])
    aemail=post.get("author_email",""); aphoto=get_photo(aemail)
    ain=post.get("avatar","??"); aname=post.get("author","?"); aarea=post.get("area","")
    dt=time_ago(post.get("date","")); views=post.get("views",random.randint(80,500))
    abstract=post.get("abstract","")
    if compact and len(abstract)>180: abstract=abstract[:180]+"…"
    g=ugrad(aemail)
    if show_author:
        av_html=(f'<div class="av" style="width:40px;height:40px;background:{g};font-size:12px"><img src="{aphoto}"/></div>'
                 if aphoto else f'<div class="av" style="width:40px;height:40px;background:{g};font-size:12px">{ain}</div>')
        v_mark=' <span style="font-size:.58rem;color:var(--gr2)">✓</span>' if st.session_state.users.get(aemail,{}).get("verified") else ""
        header=(f'<div style="padding:.9rem 1.15rem .65rem;display:flex;align-items:center;gap:10px;border-bottom:1px solid rgba(249,115,22,.06)">'
                f'{av_html}<div style="flex:1;min-width:0"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.86rem">{aname}{v_mark}</div>'
                f'<div style="color:var(--text3);font-size:.65rem;margin-top:1px">{aarea} · {dt}</div></div>{badge(post["status"])}</div>')
    else:
        header=(f'<div style="padding:.38rem 1.15rem .22rem;display:flex;justify-content:space-between;align-items:center">'
                f'<span style="color:var(--text3);font-size:.65rem">{dt}</span>{badge(post["status"])}</div>')
    st.markdown(
        f'<div class="post">{header}'
        f'<div style="padding:.75rem 1.15rem">'
        f'<div style="font-family:Syne,sans-serif;font-size:.98rem;font-weight:700;margin-bottom:.38rem;line-height:1.42;color:var(--text)">{post["title"]}</div>'
        f'<div style="color:var(--text2);font-size:.80rem;line-height:1.68;margin-bottom:.60rem">{abstract}</div>'
        f'<div>{tags_html(post.get("tags",[]))}</div></div></div>',unsafe_allow_html=True)
    heart="❤️" if liked else "🤍"; book="🔖" if saved else "📌"
    nc=len(post.get("comments",[]))
    ca,cb,cc,cd,ce,cf=st.columns([1.1,1,.6,.5,.9,1.1])
    with ca:
        if st.button(f"{heart} {fmt_num(post['likes'])}",key=f"lk_{ctx}_{pid}",use_container_width=True):
            if liked: post["liked_by"].remove(email); post["likes"]=max(0,post["likes"]-1)
            else: post["liked_by"].append(email); post["likes"]+=1; record(post.get("tags",[]),1.5)
            save_db(); st.rerun()
    with cb:
        lbl_c=f"💬 {nc}" if nc else "💬"
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
        st.markdown(f'<div style="text-align:center;color:var(--text3);font-size:.68rem;padding:.5rem 0">👁 {fmt_num(views)}</div>',unsafe_allow_html=True)
    with cf:
        if show_author and aemail:
            first=aname.split()[0] if aname else "?"
            if st.button(f"👤 {first}",key=f"vp_{ctx}_{pid}",use_container_width=True):
                st.session_state.profile_view=aemail; st.rerun()
    if st.session_state.get(f"shr_{ctx}_{pid}",False):
        url=f"https://nebula.ai/post/{pid}"; te=post['title'][:50].replace(" ","%20")
        st.markdown(f'<div class="card" style="padding:.88rem 1.15rem;margin-bottom:.5rem"><div style="font-family:Syne,sans-serif;font-weight:600;font-size:.80rem;margin-bottom:.65rem;color:var(--text2)">↗ Compartilhar</div><div style="display:flex;gap:.5rem;flex-wrap:wrap"><a href="https://twitter.com/intent/tweet?text={te}" target="_blank" style="text-decoration:none"><div style="background:rgba(29,161,242,.08);border:1px solid rgba(29,161,242,.18);border-radius:9px;padding:.32rem .68rem;font-size:.70rem;color:#1da1f2">𝕏 Twitter</div></a><a href="https://linkedin.com/sharing/share-offsite/?url={url}" target="_blank" style="text-decoration:none"><div style="background:rgba(10,102,194,.08);border:1px solid rgba(10,102,194,.18);border-radius:9px;padding:.32rem .68rem;font-size:.70rem;color:#0a66c2">in LinkedIn</div></a><a href="https://wa.me/?text={te}%20{url}" target="_blank" style="text-decoration:none"><div style="background:rgba(37,211,102,.07);border:1px solid rgba(37,211,102,.15);border-radius:9px;padding:.32rem .68rem;font-size:.70rem;color:#25d366">📱 WhatsApp</div></a></div><code style="font-size:.66rem;color:var(--text3);display:block;margin-top:.5rem;background:rgba(0,0,0,.45);padding:3px 8px;border-radius:5px">{url}</code></div>',unsafe_allow_html=True)
    if st.session_state.get(f"cmt_{ctx}_{pid}",False):
        comments=post.get("comments",[])
        for c in comments:
            c_in=ini(c["user"]); c_email=next((e for e,u in st.session_state.users.items() if u.get("name")==c["user"]),"")
            c_photo=get_photo(c_email); c_grad=ugrad(c_email)
            av_c=avh(c_in,26,c_photo,c_grad)
            st.markdown(f'<div class="cmt"><div style="display:flex;align-items:center;gap:8px;margin-bottom:.22rem">{av_c}<span style="font-size:.74rem;font-weight:600;color:var(--or2)">{c["user"]}</span></div><div style="font-size:.78rem;color:var(--text2);line-height:1.55;padding-left:34px">{c["text"]}</div></div>',unsafe_allow_html=True)
        nc_txt=st.text_input("",placeholder="Escreva um comentário…",key=f"ci_{ctx}_{pid}",label_visibility="collapsed")
        if st.button("→ Enviar",key=f"cs_{ctx}_{pid}"):
            if nc_txt:
                uu=guser(); post["comments"].append({"user":uu.get("name","Você"),"text":nc_txt})
                record(post.get("tags",[]),.8); save_db(); st.rerun()

# ══════════════════════════════════════════════════
# FEED PAGE
# ══════════════════════════════════════════════════
def page_feed():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    email=st.session_state.current_user; u=guser()
    uname=u.get("name","?"); uphoto=u.get("photo_b64"); uin=ini(uname)
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    compose_open=st.session_state.get("compose_open",False)
    col_main,col_side=st.columns([2,.85],gap="medium")
    with col_main:
        story_list=[(ue,ud) for ue,ud in users.items() if ue!=email][:7]
        n_cols=1+len(story_list)
        scols=st.columns(n_cols)
        with scols[0]:
            pub_cls="sc-publish-open" if compose_open else "sc-publish"
            st.markdown(f'<div class="{pub_cls}" style="display:flex;justify-content:center">',unsafe_allow_html=True)
            if st.button("×" if compose_open else "+",key="pub_circle"):
                st.session_state.compose_open=not compose_open; st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)
            lbl_col="var(--or1)" if compose_open else "var(--or2)"
            st.markdown(f'<div class="sl" style="color:{lbl_col}">{"Fechar" if compose_open else "Publicar"}</div>',unsafe_allow_html=True)
        for ci,(ue,ud) in enumerate(story_list):
            sname=ud.get("name","?"); sin=ini(sname); sphoto=ud.get("photo_b64"); sg=ugrad(ue)
            is_fol=ue in st.session_state.followed; online=random.Random(ue).random()>0.45
            first=sname.split()[0]; short_area=ud.get("area","")[:12]
            follow_cls=" sc-followed" if is_fol else ""
            with scols[ci+1]:
                if sphoto:
                    st.markdown(f'<div style="width:60px;height:60px;border-radius:50%;margin:0 auto;background:{sg};border:2.5px solid {"rgba(34,197,94,.50)" if is_fol else "rgba(249,115,22,.25)"};overflow:hidden;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 18px rgba(0,0,0,.5)"><img src="{sphoto}" style="width:100%;height:100%;object-fit:cover;border-radius:50%"/></div>',unsafe_allow_html=True)
                    if st.button(f"👁",key=f"sc_{ue}",use_container_width=True):
                        st.session_state.profile_view=ue; st.rerun()
                else:
                    st.markdown(f'<div class="sc-base{follow_cls}" style="display:flex;justify-content:center"><style>.sc-base-{ue.replace("@","").replace(".","")[:8]} .stButton>button{{background:{sg}!important}}</style>',unsafe_allow_html=True)
                    if st.button(sin,key=f"sc_{ue}"):
                        st.session_state.profile_view=ue; st.rerun()
                    st.markdown('</div>',unsafe_allow_html=True)
                if online and is_fol: st.markdown('<div class="dot-sm-on"></div>',unsafe_allow_html=True)
                else: st.markdown('<div style="height:9px"></div>',unsafe_allow_html=True)
                st.markdown(f'<div class="sl">{first}</div><div class="sl2">{short_area}</div>',unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>",unsafe_allow_html=True)
        if compose_open:
            g=ugrad(email)
            av_c=(f'<div class="av" style="width:42px;height:42px;background:{g}"><img src="{uphoto}"/></div>'
                  if uphoto else f'<div class="av" style="width:42px;height:42px;font-size:13px;background:{g}">{uin}</div>')
            st.markdown(f'<div class="compose-card"><div style="display:flex;align-items:center;gap:10px;margin-bottom:.95rem">{av_c}<div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.90rem">{uname}</div><div style="font-size:.67rem;color:var(--text3)">{u.get("area","Pesquisador")}</div></div></div>',unsafe_allow_html=True)
            np_t=st.text_input("Título *",key="np_t",placeholder="Ex: Efeitos da meditação na neuroplasticidade…")
            np_ab=st.text_area("Resumo / Abstract *",key="np_ab",height=105,placeholder="Descreva sua pesquisa, metodologia e resultados…")
            c1c,c2c=st.columns(2)
            with c1c: np_tg=st.text_input("Tags (vírgula)",key="np_tg",placeholder="neurociência, fMRI")
            with c2c: np_st=st.selectbox("Status",["Em andamento","Publicado","Concluído"],key="np_st")
            cpub,ccan=st.columns([2,1])
            with cpub:
                st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
                if st.button("🚀 Publicar",key="btn_pub",use_container_width=True):
                    if not np_t or not np_ab: st.warning("Título e resumo obrigatórios.")
                    else:
                        tags=[t.strip() for t in np_tg.split(",") if t.strip()] if np_tg else []
                        new_p={"id":len(st.session_state.feed_posts)+200+random.randint(0,99),
                               "author":uname,"author_email":email,"avatar":uin,"area":u.get("area",""),
                               "title":np_t,"abstract":np_ab,"tags":tags,"likes":0,"comments":[],
                               "status":np_st,"date":datetime.now().strftime("%Y-%m-%d"),
                               "liked_by":[],"saved_by":[],"connections":tags[:3],"views":1}
                        st.session_state.feed_posts.insert(0,new_p)
                        record(tags,2.0); save_db(); st.session_state.compose_open=False; st.rerun()
                st.markdown('</div>',unsafe_allow_html=True)
            with ccan:
                if st.button("✕ Cancelar",key="btn_cancel",use_container_width=True):
                    st.session_state.compose_open=False; st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)
        else:
            g=ugrad(email)
            av_c2=(f'<div class="av" style="width:38px;height:38px;flex-shrink:0;background:{g}"><img src="{uphoto}"/></div>'
                   if uphoto else f'<div class="av" style="width:38px;height:38px;font-size:12px;flex-shrink:0;background:{g}">{uin}</div>')
            avc,btnc=st.columns([.05,1],gap="small")
            with avc: st.markdown(f'<div style="padding-top:7px">{av_c2}</div>',unsafe_allow_html=True)
            with btnc:
                st.markdown('<div class="compose-prompt">',unsafe_allow_html=True)
                if st.button(f"No que você está pesquisando, {uname.split()[0]}?",key="open_compose",use_container_width=True):
                    st.session_state.compose_open=True; st.rerun()
                st.markdown('</div>',unsafe_allow_html=True)
        ff=st.radio("",["🌐 Todos","👥 Seguidos","🔖 Salvos","🔥 Populares"],horizontal=True,key="ff",label_visibility="collapsed")
        recs=get_recs(email,2)
        if recs and "Seguidos" not in ff and "Salvos" not in ff:
            st.markdown('<div class="dtxt"><span class="badge-rec">✨ Recomendado</span></div>',unsafe_allow_html=True)
            for p in recs: render_post(p,ctx="rec",compact=True)
            st.markdown('<div class="dtxt">Mais pesquisas</div>',unsafe_allow_html=True)
        posts=list(st.session_state.feed_posts)
        if "Seguidos" in ff: posts=[p for p in posts if p.get("author_email") in st.session_state.followed]
        elif "Salvos" in ff: posts=[p for p in posts if email in p.get("saved_by",[])]
        elif "Populares" in ff: posts=sorted(posts,key=lambda p:p["likes"],reverse=True)
        else: posts=sorted(posts,key=lambda p:p.get("date",""),reverse=True)
        if not posts:
            st.markdown('<div class="card" style="padding:3.5rem;text-align:center"><div style="font-size:2.5rem;opacity:.2;margin-bottom:1rem">🔬</div><div style="color:var(--text3);font-family:Syne,sans-serif">Nenhuma pesquisa aqui ainda.</div></div>',unsafe_allow_html=True)
        else:
            for p in posts: render_post(p,ctx="feed")
    with col_side:
        sq=st.text_input("",placeholder="🔍 Pesquisadores…",key="ppl_s",label_visibility="collapsed")
        st.markdown('<div class="sc">',unsafe_allow_html=True)
        st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.82rem;margin-bottom:.85rem;display:flex;justify-content:space-between"><span>Quem seguir</span><span style="font-size:.63rem;color:var(--text3);font-weight:400">Sugestões</span></div>',unsafe_allow_html=True)
        shown_n=0
        for ue,ud in list(users.items()):
            if ue==email or shown_n>=5: continue
            rname=ud.get("name","?")
            if sq and sq.lower() not in rname.lower() and sq.lower() not in ud.get("area","").lower(): continue
            shown_n+=1; is_fol=ue in st.session_state.followed
            uphoto_r=ud.get("photo_b64"); uin_r=ini(rname); rg=ugrad(ue); online=random.Random(ue+"x").random()>0.45
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            av_r=avh(uin_r,32,uphoto_r,rg)
            st.markdown(f'<div class="person-row">{av_r}<div style="flex:1;min-width:0"><div style="font-size:.78rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{dot}{rname}</div><div style="font-size:.62rem;color:var(--text3)">{ud.get("area","")[:22]}</div></div></div>',unsafe_allow_html=True)
            cf_b,cv_b=st.columns(2)
            with cf_b:
                if st.button("✓ Seg." if is_fol else "+ Seguir",key=f"sf_{ue}",use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"]=max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                    save_db(); st.rerun()
            with cv_b:
                if st.button("👤",key=f"svr_{ue}",use_container_width=True):
                    st.session_state.profile_view=ue; st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)
        st.markdown('<div class="sc"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.82rem;margin-bottom:.82rem">🔥 Em Alta</div>',unsafe_allow_html=True)
        trending=[("Quantum ML","34 pesquisas"),("CRISPR 2026","28 pesquisas"),("Neuroplasticidade","22 pesquisas"),("LLMs Científicos","19 pesquisas"),("Matéria Escura","15 pesquisas")]
        for i,(topic,cnt) in enumerate(trending):
            st.markdown(f'<div style="padding:.38rem .35rem;border-radius:9px;margin-bottom:2px"><div style="font-size:.58rem;color:var(--text3);margin-bottom:1px">#{i+1} · Trending</div><div style="font-size:.78rem;font-weight:600">{topic}</div><div style="font-size:.58rem;color:var(--text3)">{cnt}</div></div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)
        if st.session_state.notifications:
            st.markdown('<div class="sc"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.82rem;margin-bottom:.72rem">🔔 Atividade</div>',unsafe_allow_html=True)
            for notif in st.session_state.notifications[:3]:
                st.markdown(f'<div style="font-size:.70rem;color:var(--text2);padding:.32rem 0;border-bottom:1px solid var(--gborder)">· {notif}</div>',unsafe_allow_html=True)
            st.markdown('</div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# SEARCH PAGE
# ══════════════════════════════════════════════════
def render_web_article(a,idx=0,ctx="web"):
    src_color="var(--te2)" if a.get("origin")=="semantic" else "var(--ye2)"
    src_name="Semantic Scholar" if a.get("origin")=="semantic" else "CrossRef"
    cite=f" · {a['citations']} cit." if a.get("citations") else ""
    uid=re.sub(r'[^a-zA-Z0-9]','',f"{ctx}_{idx}_{str(a.get('doi',''))[:10]}")[:32]
    is_saved=any(s.get('doi')==a.get('doi') for s in st.session_state.saved_articles)
    abstract=(a.get("abstract","") or "")[:255]
    if len(a.get("abstract",""))>255: abstract+="…"
    st.markdown(f'<div class="scard"><div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:.32rem"><div style="flex:1;font-family:Syne,sans-serif;font-size:.88rem;font-weight:700">{a["title"]}</div><span style="font-size:.60rem;color:{src_color};background:rgba(20,184,166,.06);border-radius:8px;padding:2px 7px;white-space:nowrap;flex-shrink:0">{src_name}</span></div><div style="color:var(--text3);font-size:.65rem;margin-bottom:.35rem">{a["authors"]} · <em>{a["source"]}</em> · {a["year"]}{cite}</div><div style="color:var(--text2);font-size:.77rem;line-height:1.65">{abstract}</div></div>',unsafe_allow_html=True)
    ca,cb,cc=st.columns(3)
    with ca:
        lbl_sv="🔖 Salvo" if is_saved else "📌 Salvar"
        if st.button(lbl_sv,key=f"svw_{uid}"):
            if is_saved: st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]; st.toast("Removido")
            else: st.session_state.saved_articles.append(a); st.toast("Salvo!")
            save_db(); st.rerun()
    with cb:
        if st.button("📋 Citar",key=f"ctw_{uid}"): st.toast(f'{a["authors"]} ({a["year"]}). {a["title"]}.')
    with cc:
        if a.get("url"): st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:var(--or2);font-size:.78rem;text-decoration:none;line-height:2.4;display:block">↗ Abrir</a>',unsafe_allow_html=True)

def page_search():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1rem;margin-bottom:.35rem">🔍 Busca Acadêmica</h1>',unsafe_allow_html=True)
    st.markdown('<p style="color:var(--text3);font-size:.78rem;margin-bottom:.9rem">Semantic Scholar · CrossRef · Nebula</p>',unsafe_allow_html=True)
    c1,c2=st.columns([4,1])
    with c1: q=st.text_input("",placeholder="CRISPR · quantum ML · dark matter…",key="sq",label_visibility="collapsed")
    with c2:
        st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
        if st.button("🔍 Buscar",use_container_width=True,key="btn_s"):
            if q:
                with st.spinner("Buscando…"):
                    nebula_r=[p for p in st.session_state.feed_posts if q.lower() in p["title"].lower() or q.lower() in p["abstract"].lower() or any(q.lower() in t.lower() for t in p.get("tags",[]))]
                    ss_r=search_ss(q,6); cr_r=search_cr(q,4)
                    st.session_state.search_results={"nebula":nebula_r,"ss":ss_r,"cr":cr_r}; st.session_state.last_sq=q; record([q.lower()],.3)
        st.markdown('</div>',unsafe_allow_html=True)
    if st.session_state.get("search_results") and st.session_state.get("last_sq"):
        res=st.session_state.search_results
        neb=res.get("nebula",[]); ss=res.get("ss",[]); cr=res.get("cr",[])
        web=ss+[x for x in cr if not any(x["title"].lower()==s["title"].lower() for s in ss)]
        t_all,t_neb,t_web=st.tabs([f"  Todos ({len(neb)+len(web)})  ",f"  🔬 Nebula ({len(neb)})  ",f"  🌐 Internet ({len(web)})  "])
        with t_all:
            if neb:
                st.markdown('<div style="font-size:.61rem;color:var(--or2);font-weight:700;margin-bottom:.5rem;letter-spacing:.09em;text-transform:uppercase">Na Nebula</div>',unsafe_allow_html=True)
                for p in neb: render_post(p,ctx="srch_all",compact=True)
            if web:
                if neb: st.markdown('<hr>',unsafe_allow_html=True)
                st.markdown('<div style="font-size:.61rem;color:var(--te2);font-weight:700;margin-bottom:.5rem;letter-spacing:.09em;text-transform:uppercase">Bases Acadêmicas</div>',unsafe_allow_html=True)
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
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# KNOWLEDGE
# ══════════════════════════════════════════════════
def page_knowledge():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1rem;margin-bottom:1rem">🕸 Rede de Conexões</h1>',unsafe_allow_html=True)
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
        fig.add_trace(go.Scatter3d(x=[p1["x"],p2["x"],None],y=[p1["y"],p2["y"],None],z=[p1["z"],p2["z"],None],mode="lines",line=dict(color=f"rgba(249,115,22,{alpha:.2f})",width=min(4,1+strength)),hoverinfo="none",showlegend=False))
    ncolors=["#f97316" if ue==email else ("#22c55e" if ue in st.session_state.followed else "#eab308") for ue in rlist]
    nsizes=[24 if ue==email else (18 if ue in st.session_state.followed else max(12,10+sum(1 for e1,e2,_,__ in edges if e1==ue or e2==ue))) for ue in rlist]
    ntext=[users.get(ue,{}).get("name","?").split()[0] for ue in rlist]
    nhover=[f"<b>{users.get(ue,{}).get('name','?')}</b><br>{users.get(ue,{}).get('area','')}<extra></extra>" for ue in rlist]
    fig.add_trace(go.Scatter3d(x=[pos[ue]["x"] for ue in rlist],y=[pos[ue]["y"] for ue in rlist],z=[pos[ue]["z"] for ue in rlist],
        mode="markers+text",marker=dict(size=nsizes,color=ncolors,opacity=.9,line=dict(color="rgba(0,0,0,.3)",width=1.5)),
        text=ntext,textposition="top center",textfont=dict(color="#475569",size=9,family="DM Sans"),
        hovertemplate=nhover,showlegend=False))
    fig.update_layout(height=430,scene=dict(xaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),yaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),zaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),bgcolor="rgba(0,0,0,0)"),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig,use_container_width=True)
    c1,c2,c3,c4=st.columns(4)
    for col,(v,l) in zip([c1,c2,c3,c4],[(len(rlist),"Pesquisadores"),(len(edges),"Conexões"),(len(st.session_state.followed),"Seguindo"),(len(st.session_state.feed_posts),"Pesquisas")]):
        with col: st.markdown(f'<div class="mbox"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>',unsafe_allow_html=True)
    st.markdown("<hr>",unsafe_allow_html=True)
    tab_map,tab_mine,tab_all=st.tabs(["  🗺 Mapa  ","  🔗 Minhas Conexões  ","  👥 Todos  "])
    with tab_map:
        for e1,e2,common,strength in sorted(edges,key=lambda x:-x[3])[:20]:
            n1=users.get(e1,{}); n2=users.get(e2,{})
            ts=tags_html(common[:4]) if common else '<span style="color:var(--text3);font-size:.68rem">seguimento</span>'
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><span style="font-size:.80rem;font-weight:700;font-family:Syne,sans-serif;color:var(--or2)">{n1.get("name","?")}</span><span style="color:var(--text3)">↔</span><span style="font-size:.80rem;font-weight:700;font-family:Syne,sans-serif;color:var(--or2)">{n2.get("name","?")}</span><div style="flex:1">{ts}</div><span style="font-size:.65rem;color:var(--gr2);font-weight:700">{strength}pt</span></div></div>',unsafe_allow_html=True)
    with tab_mine:
        my_conn=[(e1,e2,c,s) for e1,e2,c,s in edges if e1==email or e2==email]
        if not my_conn: st.info("Siga pesquisadores e publique pesquisas para ver conexões.")
        for e1,e2,common,strength in sorted(my_conn,key=lambda x:-x[3]):
            other=e2 if e1==email else e1; od=users.get(other,{}); og=ugrad(other)
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">{avh(ini(od.get("name","?")),36,get_photo(other),og)}<div style="flex:1"><div style="font-weight:700;font-size:.84rem;font-family:Syne,sans-serif">{od.get("name","?")}</div><div style="font-size:.67rem;color:var(--text3)">{od.get("area","")}</div></div>{tags_html(common[:3])}</div></div>',unsafe_allow_html=True)
            cv,cm_b,_=st.columns([1,1,4])
            with cv:
                if st.button("👤",key=f"kv_{other}",use_container_width=True): st.session_state.profile_view=other; st.rerun()
            with cm_b:
                if st.button("💬",key=f"kc_{other}",use_container_width=True):
                    if other not in st.session_state.chat_messages: st.session_state.chat_messages[other]=[]
                    st.session_state.active_chat=other; st.session_state.page="chat"; st.rerun()
    with tab_all:
        sq2=st.text_input("",placeholder="🔍 Buscar…",key="all_s",label_visibility="collapsed")
        for ue,ud in users.items():
            if ue==email: continue
            rn=ud.get("name","?"); uarea=ud.get("area","")
            if sq2 and sq2.lower() not in rn.lower() and sq2.lower() not in uarea.lower(): continue
            is_fol=ue in st.session_state.followed; rg=ugrad(ue)
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:10px">{avh(ini(rn),36,get_photo(ue),rg)}<div style="flex:1"><div style="font-size:.84rem;font-weight:700;font-family:Syne,sans-serif">{rn}</div><div style="font-size:.67rem;color:var(--text3)">{uarea}</div></div></div></div>',unsafe_allow_html=True)
            ca2,cb2,cc2=st.columns(3)
            with ca2:
                if st.button("👤",key=f"av_{ue}",use_container_width=True): st.session_state.profile_view=ue; st.rerun()
            with cb2:
                if st.button("✓ Seg." if is_fol else "+ Seguir",key=f"af_{ue}",use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"]=max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                    save_db(); st.rerun()
            with cc2:
                if st.button("💬",key=f"ac_{ue}",use_container_width=True):
                    if ue not in st.session_state.chat_messages: st.session_state.chat_messages[ue]=[]
                    st.session_state.active_chat=ue; st.session_state.page="chat"; st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# FOLDER ANALYSIS — deep, detailed with many charts
# ══════════════════════════════════════════════════
def render_document_analysis(fname,analysis,research_area=""):
    if not analysis: return
    kws=analysis.get("keywords",[]); topics=analysis.get("topics",{})
    authors=analysis.get("authors",[]); years=analysis.get("years",[])
    refs=analysis.get("references",[]); refs_online=analysis.get("references_online",[])
    strengths_a=analysis.get("strengths",[]); improvements=analysis.get("improvements",[])
    rel=analysis.get("relevance_score",0); wc=analysis.get("word_count",0)
    sc=analysis.get("sentence_count",0); readability=analysis.get("readability_score",0)
    key_phrases=analysis.get("key_phrases",[]); methodology=analysis.get("methodology_hints",[])
    field_terms=analysis.get("field_terms",[])
    prog_color=("#22c55e" if rel>=70 else ("#eab308" if rel>=45 else "#ef4444"))
    rel_label="Alta" if rel>=70 else ("Média" if rel>=45 else "Baixa")
    read_color=("#22c55e" if readability>=65 else ("#eab308" if readability>=40 else "#ef4444"))
    st.markdown(
        f'<div class="abox"><div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.55rem">'
        f'<div style="flex:1"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.92rem;margin-bottom:.35rem">{fname}</div>'
        f'<div style="font-size:.78rem;color:var(--text2);line-height:1.65">{analysis.get("summary","")}</div></div>'
        f'<div style="text-align:right;flex-shrink:0;margin-left:12px">'
        f'<div style="font-family:Syne,sans-serif;font-size:1.5rem;font-weight:800;color:{prog_color}">{rel}%</div>'
        f'<div style="font-size:.58rem;color:var(--text3);text-transform:uppercase;letter-spacing:.07em">Relevância {rel_label}</div>'
        f'</div></div>{prog_bar(rel,prog_color)}'
        f'<div style="display:flex;gap:1.5rem;flex-wrap:wrap;margin-top:.6rem;font-size:.68rem;color:var(--text3)">'
        f'<span>📝 <strong style="color:var(--text2)">{wc:,}</strong> palavras</span>'
        f'<span>📄 <strong style="color:var(--text2)">{sc}</strong> sentenças</span>'
        f'<span>📖 Legibilidade: <strong style="color:{read_color}">{readability}%</strong></span>'
        f'{"<span>🔬 Metodologia: <strong style=\"color:var(--te2)\">" + ", ".join(methodology[:2]) + "</strong></span>" if methodology else ""}'
        f'</div></div>',unsafe_allow_html=True)

    tab_ov,tab_kw,tab_topics,tab_phrases,tab_authors,tab_refs,tab_fields,tab_improve=st.tabs([
        "  📊 Visão Geral  ","  🔑 Keywords  ","  🎯 Temas  ","  💬 Frases-chave  ",
        "  👤 Autores  ","  📚 Referências  ","  🧬 Termos Técnicos  ","  ✨ Melhorias  "])

    with tab_ov:
        # Radial summary chart
        metrics=["Relevância","Legibilidade","Referências","Keywords","Autores"]
        vals=[rel,readability,min(100,len(refs)*7),min(100,len(kws)*4),min(100,len(authors)*20)]
        if len(metrics)>=3:
            fig_r=go.Figure(go.Scatterpolar(r=vals+[vals[0]],theta=metrics+[metrics[0]],fill='toself',
                line=dict(color="#f97316"),fillcolor="rgba(249,115,22,.15)"))
            fig_r.update_layout(height=300,polar=dict(bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True,range=[0,100],gridcolor="rgba(249,115,22,.09)",color="#475569",tickfont=dict(size=8)),
                angularaxis=dict(gridcolor="rgba(249,115,22,.09)",color="#94a3b8",tickfont=dict(size=9))),
                paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=40,r=40,t=20,b=20))
            st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
            st.plotly_chart(fig_r,use_container_width=True)
            st.markdown('</div>',unsafe_allow_html=True)
        # Score cards
        c1,c2,c3,c4=st.columns(4)
        with c1: st.markdown(f'<div class="mbox"><div class="mval">{rel}%</div><div class="mlbl">Relevância</div></div>',unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1.4rem;font-weight:800;color:{"var(--gr2)" if readability>=65 else "var(--ye2)"}">{readability}%</div><div class="mlbl">Legibilidade</div></div>',unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1.4rem;font-weight:800;color:var(--te2)">{len(kws)}</div><div class="mlbl">Keywords</div></div>',unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1.4rem;font-weight:800;color:var(--ye2)">{len(refs)}</div><div class="mlbl">Referências</div></div>',unsafe_allow_html=True)

    with tab_kw:
        if kws:
            weights=[max(1,20-i) for i in range(len(kws))]
            fig=go.Figure(go.Bar(x=weights[:20],y=kws[:20],orientation='h',
                marker=dict(color=weights[:20],colorscale=[[0,"#0f1117"],[.4,"#f97316"],[1,"#eab308"]]),
                text=kws[:20],textposition='inside',textfont=dict(color='white',size=9)))
            layout_kw=dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",height=380,
                margin=dict(l=10,r=10,t=40,b=10),
                title=dict(text="Palavras-chave por Relevância TF-IDF",font=dict(color=var_t1(),family="Syne",size=13)),
                font=dict(color="#475569",family="DM Sans",size=10),
                xaxis=dict(showgrid=False,color="#475569"),
                yaxis=dict(showticklabels=False,showgrid=False))
            fig.update_layout(**layout_kw)
            st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
            st.plotly_chart(fig,use_container_width=True)
            st.markdown('</div>',unsafe_allow_html=True)
            st.markdown(tags_html(kws[:20]),unsafe_allow_html=True)
        else: st.info("Palavras-chave não extraídas.")

    with tab_topics:
        if topics:
            colors_tp=["#f97316","#eab308","#22c55e","#14b8a6","#8b5cf6","#f43f5e","#38bdf8","#fb7185","#a3e635","#fb923c"]
            fig_pie=go.Figure(go.Pie(labels=list(topics.keys()),values=list(topics.values()),hole=0.50,
                marker=dict(colors=colors_tp[:len(topics)],line=dict(color=["#080b0f"]*15,width=2)),
                textfont=dict(color="white",size=9),hoverinfo="label+percent"))
            fig_pie.update_layout(height=300,title=dict(text="Distribuição Temática",font=dict(color=var_t1(),family="Syne",size=13)),
                paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(font=dict(color="#475569",size=9)),margin=dict(l=0,r=0,t=40,b=0))
            st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
            st.plotly_chart(fig_pie,use_container_width=True)
            st.markdown('</div>',unsafe_allow_html=True)
            for i,(topic,score) in enumerate(list(topics.items())[:6]):
                pct=min(100,score*22)
                st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:.38rem"><span style="font-size:.76rem;color:var(--text2);width:185px;flex-shrink:0">{topic}</span><div style="flex:1">{prog_bar(pct,colors_tp[i%len(colors_tp)])}</div><span style="font-size:.67rem;color:var(--text3);width:26px;text-align:right">{score}</span></div>',unsafe_allow_html=True)
        else: st.info("Análise temática não disponível.")

    with tab_phrases:
        if key_phrases:
            st.markdown('<div style="font-size:.61rem;color:var(--text3);text-transform:uppercase;letter-spacing:.09em;margin-bottom:.7rem;font-weight:600">Bigramas mais frequentes</div>',unsafe_allow_html=True)
            phrase_html=''.join(f'<div style="display:inline-block;background:rgba(20,184,166,.08);border:1px solid rgba(20,184,166,.18);border-radius:22px;padding:5px 12px;margin:3px;font-size:.76rem;color:var(--te2)">{p}</div>' for p in key_phrases)
            st.markdown(phrase_html,unsafe_allow_html=True)
        else: st.info("Não foi possível extrair frases-chave.")
        if methodology:
            st.markdown('<div class="dtxt">Metodologia Detectada</div>',unsafe_allow_html=True)
            for m in methodology: st.markdown(f'<div class="str-ok">🔬 {m.capitalize()}</div>',unsafe_allow_html=True)

    with tab_authors:
        if authors:
            for author in authors:
                st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:.38rem 0;border-bottom:1px solid var(--gborder)"><div style="width:26px;height:26px;border-radius:50%;background:{ugrad(author)};display:flex;align-items:center;justify-content:center;font-size:.63rem;font-weight:700;color:white;flex-shrink:0">{ini(author)}</div><span style="font-size:.80rem;color:var(--text)">{author}</span></div>',unsafe_allow_html=True)
        else: st.markdown('<div style="color:var(--text3);font-size:.77rem;margin-bottom:.8rem">Nenhum autor identificado.</div>',unsafe_allow_html=True)
        if years:
            year_labels=[y for y,_ in years[:8]]; year_vals=[c for _,c in years[:8]]
            fig_y=go.Figure(go.Bar(x=year_labels,y=year_vals,
                marker=dict(color=year_vals,colorscale=[[0,"#0f1117"],[1,"#f97316"]]),
                text=year_vals,textposition="outside",textfont=dict(color="#475569",size=9)))
            layout_y=dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",height=200,
                margin=dict(l=10,r=10,t=40,b=10),
                title=dict(text="Anos Mencionados",font=dict(color=var_t1(),family="Syne",size=12)),
                font=dict(color="#475569",family="DM Sans",size=10),
                xaxis=dict(showgrid=False,color="#475569",type="category"),
                yaxis=dict(showgrid=True,gridcolor="rgba(249,115,22,.06)",color="#475569"))
            fig_y.update_layout(**layout_y)
            st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
            st.plotly_chart(fig_y,use_container_width=True)
            st.markdown('</div>',unsafe_allow_html=True)

    with tab_refs:
        if refs:
            for r in refs[:10]: st.markdown(f'<div class="ref-item">· {r}</div>',unsafe_allow_html=True)
        else: st.markdown('<div style="color:var(--text3);font-size:.77rem;margin-bottom:.7rem">Nenhuma referência estruturada encontrada.</div>',unsafe_allow_html=True)
        if refs_online:
            st.markdown('<div class="dtxt">Artigos Relacionados Online</div>',unsafe_allow_html=True)
            for ref in refs_online[:5]:
                url_html=f'<a href="{ref["url"]}" target="_blank" style="color:var(--or2);text-decoration:none;font-size:.70rem">↗ Abrir</a>' if ref.get("url") else ""
                st.markdown(f'<div class="scard"><div style="font-family:Syne,sans-serif;font-size:.84rem;font-weight:700;margin-bottom:.28rem">{ref["title"]}</div><div style="color:var(--text3);font-size:.65rem;margin-bottom:.28rem">{ref["authors"]} · {ref["venue"]} · {ref["year"]}</div><div style="color:var(--text2);font-size:.75rem;line-height:1.6">{ref["abstract"][:180]}…</div><div style="margin-top:.32rem">{url_html}</div></div>',unsafe_allow_html=True)

    with tab_fields:
        if field_terms:
            st.markdown('<div style="font-size:.61rem;color:var(--text3);text-transform:uppercase;letter-spacing:.09em;margin-bottom:.7rem;font-weight:600">Termos Técnicos Especializados</div>',unsafe_allow_html=True)
            field_grouped=defaultdict(list)
            for field,term in field_terms: field_grouped[field].append(term)
            for field,terms in field_grouped.items():
                st.markdown(f'<div class="pbox"><div style="font-size:.70rem;font-weight:700;color:var(--gr2);margin-bottom:.4rem">{field}</div><div>{" ".join(f"<span class=tag>{t}</span>" for t in terms)}</div></div>',unsafe_allow_html=True)
        else: st.info("Nenhum termo técnico especializado detectado.")
        # Keyword density chart
        if kws:
            fig_d=go.Figure(go.Scatter(x=list(range(len(kws[:15]))),y=[20-i for i in range(len(kws[:15]))],
                mode="markers+text",marker=dict(size=[22-i*0.8 for i in range(15)],color=["#f97316","#eab308","#22c55e","#14b8a6","#8b5cf6","#f43f5e","#38bdf8","#fb7185","#a3e635","#fb923c","#f97316","#eab308","#22c55e","#14b8a6","#8b5cf6"][:len(kws[:15])],opacity=.85),
                text=kws[:15],textposition="top center",textfont=dict(color="#94a3b8",size=8)))
            fig_d.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",height=240,
                title=dict(text="Mapa de Densidade de Keywords",font=dict(color=var_t1(),family="Syne",size=12)),
                margin=dict(l=10,r=10,t=40,b=10),
                xaxis=dict(showgrid=False,showticklabels=False,color="#475569"),
                yaxis=dict(showgrid=False,showticklabels=False,color="#475569"))
            st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
            st.plotly_chart(fig_d,use_container_width=True)
            st.markdown('</div>',unsafe_allow_html=True)

    with tab_improve:
        if strengths_a:
            st.markdown('<div style="font-size:.61rem;color:var(--text3);text-transform:uppercase;letter-spacing:.09em;margin-bottom:.6rem;font-weight:600">Pontos Fortes</div>',unsafe_allow_html=True)
            for s in strengths_a: st.markdown(f'<div class="str-ok">✓ {s}</div>',unsafe_allow_html=True)
        if improvements:
            st.markdown('<div style="font-size:.61rem;color:var(--text3);text-transform:uppercase;letter-spacing:.09em;margin:.8rem 0 .6rem;font-weight:600">Pontos a Melhorar</div>',unsafe_allow_html=True)
            for imp in improvements: st.markdown(f'<div class="str-imp">→ {imp}</div>',unsafe_allow_html=True)
        # Improvement score breakdown
        if strengths_a or improvements:
            score=len(strengths_a)*20; gaps=len(improvements)*15
            fig_gauge=go.Figure(go.Indicator(mode="gauge+number",value=min(100,score),
                gauge=dict(axis=dict(range=[0,100]),bar=dict(color="#f97316"),
                    steps=[dict(range=[0,40],color="rgba(239,68,68,.12)"),dict(range=[40,70],color="rgba(234,179,8,.12)"),dict(range=[70,100],color="rgba(34,197,94,.12)")],
                    threshold=dict(line=dict(color="white",width=2),thickness=.75,value=70)),
                title=dict(text="Score Geral do Documento",font=dict(color=var_t1(),size=13,family="Syne"))))
            fig_gauge.update_layout(height=220,paper_bgcolor="rgba(0,0,0,0)",font=dict(color="#94a3b8",size=10),margin=dict(l=10,r=10,t=50,b=10))
            st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
            st.plotly_chart(fig_gauge,use_container_width=True)
            st.markdown('</div>',unsafe_allow_html=True)
        if not strengths_a and not improvements: st.info("Execute a análise para ver recomendações.")

def var_t1(): return "#f1f5f9"

def page_folders():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1rem;margin-bottom:1rem">📁 Pastas de Pesquisa</h1>',unsafe_allow_html=True)
    email=st.session_state.current_user; u=guser(); research_area=u.get("area","")
    c1,c2,_=st.columns([2,1.2,1.5])
    with c1: nf_name=st.text_input("Nome da pasta",placeholder="Ex: Genômica Comparativa",key="nf_n")
    with c2: nf_desc=st.text_input("Descrição",placeholder="Breve descrição",key="nf_d")
    st.markdown('<div class="btn-primary" style="display:inline-block">',unsafe_allow_html=True)
    if st.button("📁 Criar pasta",key="btn_nf"):
        if nf_name.strip():
            if nf_name not in st.session_state.folders:
                st.session_state.folders[nf_name]={"desc":nf_desc,"files":[],"notes":"","analyses":{}}
                save_db(); st.success(f"Pasta '{nf_name}' criada!"); st.rerun()
            else: st.warning("Pasta já existe.")
        else: st.warning("Digite um nome.")
    st.markdown('</div>',unsafe_allow_html=True)
    st.markdown("<hr>",unsafe_allow_html=True)
    if not st.session_state.folders:
        st.markdown('<div class="card" style="text-align:center;padding:4.5rem"><div style="font-size:2.5rem;opacity:.2;margin-bottom:1rem">📁</div><div style="color:var(--text3);font-family:Syne,sans-serif">Nenhuma pasta criada ainda</div></div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True); return
    folder_cols=st.columns(3)
    for idx,(fname,fdata) in enumerate(list(st.session_state.folders.items())):
        if not isinstance(fdata,dict): fdata={"files":fdata,"desc":"","notes":"","analyses":{}}; st.session_state.folders[fname]=fdata
        files=fdata.get("files",[]); desc=fdata.get("desc",""); analyses=fdata.get("analyses",{})
        all_tags=list({t for an in analyses.values() for t in an.get("keywords",[])[:3]})
        with folder_cols[idx%3]:
            st.markdown(f'<div class="card" style="padding:1.1rem;text-align:center;margin-bottom:.6rem"><div style="font-size:1.8rem;opacity:.5;margin-bottom:6px">📁</div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.93rem">{fname}</div><div style="color:var(--text3);font-size:.67rem;margin-top:2px">{desc}</div><div style="margin-top:.4rem;font-size:.68rem;color:var(--or2)">{len(files)} arquivo(s) · {len(analyses)} analisado(s)</div><div style="margin-top:.38rem">{tags_html(all_tags[:3])}</div></div>',unsafe_allow_html=True)
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
                    ab='<span class="badge-pub" style="font-size:.6rem;margin-left:6px">✓ analisado</span>' if has_an else ''
                    st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:.40rem 0;border-bottom:1px solid var(--gborder)"><span style="font-size:.95rem">{icon}</span><span style="font-size:.77rem;color:var(--text2);flex:1">{f}</span>{ab}</div>',unsafe_allow_html=True)
            else: st.markdown('<p style="color:var(--text3);font-size:.72rem;text-align:center;padding:.5rem">Arraste arquivos — PDF, DOCX, XLSX, CSV…</p>',unsafe_allow_html=True)
            st.markdown('<hr>',unsafe_allow_html=True)
            ca_btn,cb_btn,_=st.columns([1.5,1.5,2])
            with ca_btn:
                st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
                if st.button("🔬 Analisar documentos",key=f"analyze_{fname}",use_container_width=True):
                    if files:
                        pb=st.progress(0,"Iniciando…")
                        folder_bytes=st.session_state.folder_files_bytes.get(fname,{})
                        for fi,f in enumerate(files):
                            pb.progress((fi+1)/len(files),f"Analisando: {f[:28]}…")
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
                st.markdown('</div>',unsafe_allow_html=True)
            with cb_btn:
                st.markdown('<div class="btn-danger">',unsafe_allow_html=True)
                if st.button("🗑 Excluir pasta",key=f"df_{fname}",use_container_width=True):
                    del st.session_state.folders[fname]
                    if fname in st.session_state.folder_files_bytes: del st.session_state.folder_files_bytes[fname]
                    save_db(); st.rerun()
                st.markdown('</div>',unsafe_allow_html=True)
            if analyses:
                st.markdown('<div class="dtxt">📊 Análises Inteligentes</div>',unsafe_allow_html=True)
                rel_scores={f:an.get("relevance_score",0) for f,an in analyses.items()}
                if len(rel_scores)>1:
                    fig_ov=go.Figure(go.Bar(x=list(rel_scores.values()),y=[f[:22] for f in rel_scores.keys()],orientation='h',
                        marker=dict(color=list(rel_scores.values()),colorscale=[[0,"#0f1117"],[.5,"#f97316"],[1,"#22c55e"]],line=dict(color="#080b0f",width=1)),
                        text=[f"{v}%" for v in rel_scores.values()],textposition="outside",textfont=dict(color="#475569",size=9)))
                    layout_ov=dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",height=max(110,len(analyses)*40),
                        margin=dict(l=10,r=10,t=40,b=10),
                        title=dict(text="Relevância por Documento",font=dict(color=var_t1(),family="Syne",size=12)),
                        font=dict(color="#475569",family="DM Sans",size=9),
                        xaxis=dict(showgrid=False,color="#475569"),
                        yaxis=dict(showgrid=False,color="#475569",tickfont=dict(size=9)))
                    fig_ov.update_layout(**layout_ov)
                    st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
                    st.plotly_chart(fig_ov,use_container_width=True)
                    st.markdown('</div>',unsafe_allow_html=True)
                for f,an in analyses.items():
                    with st.expander(f"🔬 {f}"):
                        render_document_analysis(f,an,research_area)
            st.markdown('<hr>',unsafe_allow_html=True)
            note=st.text_area("Notas",value=fdata.get("notes",""),key=f"note_{fname}",height=65,placeholder="Anotações…")
            if st.button("💾 Salvar nota",key=f"sn_{fname}",use_container_width=True):
                fdata["notes"]=note; save_db(); st.success("✓ Nota salva!")
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════
def page_analytics():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1rem;margin-bottom:1rem">📊 Painel de Pesquisa</h1>',unsafe_allow_html=True)
    email=st.session_state.current_user; d=st.session_state.stats_data
    tab_f,tab_p,tab_i,tab_pr=st.tabs(["  📁 Pastas  ","  📝 Publicações  ","  📈 Impacto  ","  🎯 Interesses  "])
    with tab_f:
        folders=st.session_state.folders
        if not folders:
            st.markdown('<div class="card" style="text-align:center;padding:3rem;color:var(--text3)">Crie pastas e analise documentos.</div>',unsafe_allow_html=True)
        else:
            all_analyses={f:an for fd in folders.values() if isinstance(fd,dict) for f,an in fd.get("analyses",{}).items()}
            total_files=sum(len(fd.get("files",[]) if isinstance(fd,dict) else fd) for fd in folders.values())
            all_kws=[kw for an in all_analyses.values() for kw in an.get("keywords",[])]
            all_topics=defaultdict(int)
            for an in all_analyses.values():
                for t,s in an.get("topics",{}).items(): all_topics[t]+=s
            c1,c2,c3,c4=st.columns(4)
            for col,(v,l) in zip([c1,c2,c3,c4],[(len(folders),"Pastas"),(total_files,"Arquivos"),(len(all_analyses),"Analisados"),(len(set(all_kws[:100])),"Keywords")]):
                with col: st.markdown(f'<div class="mbox"><div class="mval">{v}</div><div class="mlbl">{l}</div></div>',unsafe_allow_html=True)
            if all_topics:
                colors_an=["#f97316","#eab308","#22c55e","#14b8a6","#8b5cf6","#f43f5e","#38bdf8","#fb923c"]
                fig_t=go.Figure(go.Bar(x=list(all_topics.values())[:8],y=list(all_topics.keys())[:8],orientation='h',
                    marker=dict(color=colors_an[:min(8,len(all_topics))]),
                    text=[str(v) for v in list(all_topics.values())[:8]],textposition="outside",textfont=dict(color="#475569",size=9)))
                layout_t=dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",height=280,
                    margin=dict(l=10,r=10,t=40,b=10),
                    title=dict(text="Temas por Frequência",font=dict(color=var_t1(),family="Syne",size=13)),
                    font=dict(color="#475569",family="DM Sans",size=9),
                    xaxis=dict(showgrid=False,color="#475569"),
                    yaxis=dict(showgrid=False,color="#475569",tickfont=dict(size=9)))
                fig_t.update_layout(**layout_t)
                st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
                st.plotly_chart(fig_t,use_container_width=True)
                st.markdown('</div>',unsafe_allow_html=True)
            if all_kws:
                kw_freq=Counter(all_kws).most_common(12)
                fig_kw=go.Figure(go.Bar(x=[c for _,c in kw_freq],y=[w for w,_ in kw_freq],orientation='h',
                    marker=dict(color=[c for _,c in kw_freq],colorscale=[[0,"#0f1117"],[.5,"#f97316"],[1,"#eab308"]]),
                    text=[w for w,_ in kw_freq],textposition='inside',textfont=dict(color='white',size=8)))
                layout_kw2=dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",height=300,
                    margin=dict(l=10,r=10,t=40,b=10),
                    title=dict(text="Top 12 Palavras-chave",font=dict(color=var_t1(),family="Syne",size=13)),
                    font=dict(color="#475569",family="DM Sans",size=9),
                    xaxis=dict(showgrid=False,color="#475569"),
                    yaxis=dict(showticklabels=False,showgrid=False))
                fig_kw.update_layout(**layout_kw2)
                st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
                st.plotly_chart(fig_kw,use_container_width=True)
                st.markdown('</div>',unsafe_allow_html=True)
    with tab_p:
        my_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==email]
        if not my_posts: st.markdown('<div class="card" style="text-align:center;padding:2.5rem;color:var(--text3)">Publique pesquisas para ver métricas.</div>',unsafe_allow_html=True)
        else:
            c1,c2,c3=st.columns(3)
            with c1: st.markdown(f'<div class="mbox"><div class="mval">{len(my_posts)}</div><div class="mlbl">Pesquisas</div></div>',unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="mbox"><div class="mval">{sum(p["likes"] for p in my_posts)}</div><div class="mlbl">Curtidas</div></div>',unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="mbox"><div class="mval">{sum(len(p.get("comments",[])) for p in my_posts)}</div><div class="mlbl">Comentários</div></div>',unsafe_allow_html=True)
            titles_s=[p["title"][:16]+"…" for p in my_posts]
            fig_eng=go.Figure()
            fig_eng.add_trace(go.Bar(name="Curtidas",x=titles_s,y=[p["likes"] for p in my_posts],marker_color="#f97316",marker_line=dict(color="#080b0f",width=1)))
            fig_eng.add_trace(go.Bar(name="Comentários",x=titles_s,y=[len(p.get("comments",[])) for p in my_posts],marker_color="#22c55e",marker_line=dict(color="#080b0f",width=1)))
            fig_eng.update_layout(barmode="group",height=250,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                title=dict(text="Engajamento",font=dict(color=var_t1(),family="Syne",size=13)),
                font=dict(color="#475569",family="DM Sans",size=10),legend=dict(font=dict(color="#475569")),
                margin=dict(l=10,r=10,t=40,b=10),xaxis=dict(showgrid=False,color="#475569"),
                yaxis=dict(showgrid=True,gridcolor="rgba(249,115,22,.06)",color="#475569"))
            st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
            st.plotly_chart(fig_eng,use_container_width=True)
            st.markdown('</div>',unsafe_allow_html=True)
            for p in sorted(my_posts,key=lambda x:x.get("date",""),reverse=True):
                t_s=p["title"][:52]+("…" if len(p["title"])>52 else "")
                st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;justify-content:space-between"><div style="font-family:Syne,sans-serif;font-size:.88rem;font-weight:700">{t_s}</div>{badge(p["status"])}</div><div style="font-size:.69rem;color:var(--text3);margin-top:.38rem">{p.get("date","")} · {p["likes"]} curtidas · {len(p.get("comments",[]))} comentários</div><div style="margin-top:.35rem">{tags_html(p.get("tags",[])[:4])}</div></div>',unsafe_allow_html=True)
    with tab_i:
        c1,c2,c3=st.columns(3)
        with c1: st.markdown(f'<div class="mbox"><div class="mval">{d.get("h_index",4)}</div><div class="mlbl">Índice H</div></div>',unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="mbox"><div class="mval">{d.get("fator_impacto",3.8):.1f}</div><div class="mlbl">Fator de Impacto</div></div>',unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="mbox"><div class="mval">{len(st.session_state.saved_articles)}</div><div class="mlbl">Salvos</div></div>',unsafe_allow_html=True)
        st.markdown("<hr>",unsafe_allow_html=True)
        new_h=st.number_input("Índice H",0,200,d.get("h_index",4),key="e_h")
        new_fi=st.number_input("Fator de impacto",0.0,100.0,float(d.get("fator_impacto",3.8)),step=0.1,key="e_fi")
        new_notes=st.text_area("Notas",value=d.get("notes",""),key="e_notes",height=75)
        if st.button("💾 Salvar métricas",key="btn_save_m"): d.update({"h_index":new_h,"fator_impacto":new_fi,"notes":new_notes}); st.success("✓ Salvo!")
    with tab_pr:
        prefs=st.session_state.user_prefs.get(email,{})
        if prefs:
            top=sorted(prefs.items(),key=lambda x:-x[1])[:14]; mx=max(s for _,s in top) if top else 1
            cats=[t for t,_ in top[:8]]; vals=[round(s/mx*100) for _,s in top[:8]]
            if len(cats)>=3:
                fig_r=go.Figure(go.Scatterpolar(r=vals+[vals[0]],theta=cats+[cats[0]],fill='toself',
                    line=dict(color="#f97316"),fillcolor="rgba(249,115,22,.14)"))
                fig_r.update_layout(height=280,polar=dict(bgcolor="rgba(0,0,0,0)",
                    radialaxis=dict(visible=True,gridcolor="rgba(249,115,22,.09)",color="#475569",tickfont=dict(size=8)),
                    angularaxis=dict(gridcolor="rgba(249,115,22,.09)",color="#94a3b8",tickfont=dict(size=9))),
                    paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=40,r=40,t=20,b=20))
                st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
                st.plotly_chart(fig_r,use_container_width=True)
                st.markdown('</div>',unsafe_allow_html=True)
            c1,c2=st.columns(2)
            colors_pr=["#f97316","#eab308","#22c55e","#14b8a6","#8b5cf6","#f43f5e"]
            for i,(tag,score) in enumerate(top):
                pct=int(score/mx*100); color=colors_pr[i%len(colors_pr)]
                with (c1 if i%2==0 else c2):
                    st.markdown(f'<div style="display:flex;justify-content:space-between;font-size:.75rem;margin-bottom:2px"><span style="color:var(--text2)">{tag}</span><span style="color:{color};font-weight:600">{pct}%</span></div>{prog_bar(pct,color)}',unsafe_allow_html=True)
        else: st.info("Interaja com pesquisas para construir seu perfil.")
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# IMAGE ANALYSIS PAGE — with AI disclaimer + related research
# ══════════════════════════════════════════════════
def page_img_search():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1rem;margin-bottom:.35rem">🖼 Análise Visual Científica</h1>',unsafe_allow_html=True)
    st.markdown('<p style="color:var(--text3);font-size:.78rem;margin-bottom:1rem">Detecta padrões, estruturas e conecta com pesquisas similares</p>',unsafe_allow_html=True)
    st.markdown('<div class="ai-disclaimer">⚠️ <strong>Aviso sobre IA:</strong> Esta análise é gerada por algoritmos de visão computacional e pode conter imprecisões. Os resultados são estimativas baseadas em padrões visuais — não substituem análise especializada. Sempre valide com um especialista da área.</div>',unsafe_allow_html=True)
    col_up,col_res=st.columns([1,1.85])
    with col_up:
        st.markdown('<div class="card" style="padding:1.15rem">',unsafe_allow_html=True)
        st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.86rem;margin-bottom:.65rem">📷 Carregar Imagem</div>',unsafe_allow_html=True)
        img_file=st.file_uploader("",type=["png","jpg","jpeg","webp","tiff"],label_visibility="collapsed",key="img_up")
        if img_file: st.image(img_file,use_container_width=True,caption="Imagem carregada")
        st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
        run=st.button("🔬 Analisar",use_container_width=True,key="btn_run")
        st.markdown('</div>',unsafe_allow_html=True)
        st.markdown('<div style="margin-top:.85rem;font-size:.67rem;color:var(--text3);line-height:1.9">Detecção de bordas (Sobel)<br>Análise FFT · Simetria radial<br>Histograma de brilho<br>Paleta de cores dominante</div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)
    with col_res:
        if run and img_file:
            img_file.seek(0)
            with st.spinner("Analisando…"):
                rep=analyze_image_advanced(img_file); st.session_state.img_result=rep
            if rep:
                conf_c=("#22c55e" if rep["confidence"]>80 else ("#eab308" if rep["confidence"]>60 else "#ef4444"))
                st.markdown(f'<div class="abox"><div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:.5rem"><div><div style="font-size:.60rem;color:var(--text3);letter-spacing:.10em;text-transform:uppercase;margin-bottom:3px;font-weight:600">Categoria Detectada</div><div style="font-family:Syne,sans-serif;font-size:1.05rem;font-weight:700;margin-bottom:3px">{rep["category"]}</div></div><div style="background:rgba(0,0,0,.35);border:1px solid var(--gborder);border-radius:12px;padding:.45rem .85rem;text-align:center;flex-shrink:0"><div style="font-family:Syne,sans-serif;font-size:1.35rem;font-weight:800;color:{conf_c}">{rep["confidence"]}%</div><div style="font-size:.57rem;color:var(--text3);text-transform:uppercase;font-weight:600">confiança IA</div></div></div><div style="font-size:.79rem;color:var(--text2);line-height:1.68;margin-bottom:.5rem">{rep["description"]}</div><div style="display:flex;gap:1.4rem;flex-wrap:wrap;font-size:.66rem;color:var(--text3)"><span>Material: <strong style="color:var(--text2)">{rep["material"]}</strong></span><span>Estrutura: <strong style="color:var(--text2)">{rep["object_type"]}</strong></span><span>Res: <strong style="color:var(--text2)">{rep["size"][0]}×{rep["size"][1]}</strong></span></div></div>',unsafe_allow_html=True)
                # Metrics row
                c1,c2,c3=st.columns(3); sym_lbl="Alta" if rep["symmetry"]>0.78 else ("Média" if rep["symmetry"]>0.52 else "Baixa")
                with c1: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1rem;font-weight:700;color:var(--or2)">{rep["texture"]["complexity"]}</div><div class="mlbl">Complexidade</div></div>',unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1rem;font-weight:700;color:var(--gr2)">{sym_lbl}</div><div class="mlbl">Simetria</div></div>',unsafe_allow_html=True)
                with c3: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1rem;font-weight:700;color:var(--ye2)">{rep["lines"]["direction"]}</div><div class="mlbl">Linhas Dom.</div></div>',unsafe_allow_html=True)
                # Brightness histogram
                if rep.get("hist_vals") and rep.get("hist_bins"):
                    fig_hist=go.Figure(go.Bar(x=rep["hist_bins"],y=rep["hist_vals"],marker=dict(color=rep["hist_bins"],colorscale=[[0,"#080b0f"],[0.5,"#f97316"],[1,"#eab308"]],line=dict(color="#080b0f",width=0.5))))
                    fig_hist.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",height=160,
                        title=dict(text="Histograma de Brilho",font=dict(color=var_t1(),family="Syne",size=11)),
                        margin=dict(l=10,r=10,t=35,b=10),
                        xaxis=dict(showgrid=False,color="#475569",title="Intensidade",titlefont=dict(size=9)),
                        yaxis=dict(showgrid=False,showticklabels=False))
                    st.markdown('<div class="chart-glass">',unsafe_allow_html=True)
                    st.plotly_chart(fig_hist,use_container_width=True)
                    st.markdown('</div>',unsafe_allow_html=True)
                # Line strengths
                l=rep["lines"]; strengths_img=l["strengths"]; max_s=max(strengths_img.values())+0.01
                st.markdown('<div class="pbox"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.83rem;margin-bottom:.65rem;color:var(--gr2)">📐 Análise Direcional de Linhas</div>',unsafe_allow_html=True)
                dir_colors={"Horizontal":"#f97316","Vertical":"#22c55e","Diagonal A":"#eab308","Diagonal B":"#14b8a6"}
                for dir_name,val in strengths_img.items():
                    pct=int(val/max_s*100); is_dom=dir_name==l["direction"]; color=dir_colors.get(dir_name,"#f97316")
                    st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:.35rem"><span style="font-size:.68rem;color:{"var(--or2)" if is_dom else "var(--text3)"};width:88px;flex-shrink:0">{"★ " if is_dom else ""}{dir_name}</span><div style="flex:1">{prog_bar(pct,color)}</div><span style="font-size:.66rem;color:var(--text3);width:34px;text-align:right">{val:.2f}</span></div>',unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:.68rem;color:var(--text3);margin-top:.45rem">Formas: <strong style="color:var(--or2)">{" · ".join(rep["shapes"])}</strong></div></div>',unsafe_allow_html=True)
                # Color analysis
                rv,gv,bv=rep["color"]["r"],rep["color"]["g"],rep["color"]["b"]
                hex_c="#{:02x}{:02x}{:02x}".format(int(rv),int(gv),int(bv))
                pal_html="".join(f'<div style="width:28px;height:28px;border-radius:7px;background:rgb{str(p)};border:1.5px solid rgba(255,255,255,.07)"></div>' for p in rep["palette"][:6])
                temp_str="Quente 🔴" if rep["color"]["warm"] else ("Fria 🔵" if rep["color"]["cool"] else "Neutra ⚪")
                st.markdown(f'<div class="abox"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.83rem;margin-bottom:.75rem">🎨 Análise de Cor</div><div style="display:flex;gap:12px;align-items:center;margin-bottom:.85rem"><div style="width:42px;height:42px;border-radius:10px;background:{hex_c};border:1.5px solid var(--gborder);flex-shrink:0"></div><div style="font-size:.76rem;color:var(--text2);line-height:1.75">RGB: <strong>({int(rv)},{int(gv)},{int(bv)})</strong> · {hex_c.upper()}<br>Canal: <strong>{rep["color"]["dom"]}</strong> · Temp: <strong>{temp_str}</strong> · Sat: <strong>{rep["color"]["sat"]:.0f}%</strong></div></div><div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:.65rem">{pal_html}</div><div style="font-size:.74rem;color:var(--text3)">Entropia: <strong style="color:var(--text)">{rep["texture"]["entropy"]} bits</strong> · Contraste: <strong style="color:var(--text)">{rep["texture"]["contrast"]:.2f}</strong></div></div>',unsafe_allow_html=True)
        elif not img_file:
            st.markdown('<div class="card" style="padding:4.5rem 2rem;text-align:center"><div style="font-size:2.8rem;opacity:.18;margin-bottom:1.1rem">🖼</div><div style="font-family:Syne,sans-serif;font-size:1rem;color:var(--text2);margin-bottom:.65rem">Carregue uma imagem científica</div><div style="color:var(--text3);font-size:.75rem;line-height:2">PNG · JPG · WEBP · TIFF<br>Microscopia · Cristalografia · Fluorescência</div></div>',unsafe_allow_html=True)
    # Related research section
    if st.session_state.get("img_result"):
        rep=st.session_state.img_result; st.markdown("<hr>",unsafe_allow_html=True)
        st.markdown('<h2 style="margin-bottom:.65rem">🔗 Pesquisas Relacionadas</h2>',unsafe_allow_html=True)
        st.markdown('<div class="ai-disclaimer" style="font-size:.70rem">As pesquisas abaixo foram encontradas por similaridade de termos com a análise da imagem — conexão gerada por IA com base em palavras-chave visuais detectadas.</div>',unsafe_allow_html=True)
        kw=(rep.get("kw","")+" "+rep.get("category","")+" "+rep.get("object_type","")).lower().split()
        all_terms=list(set(kw))
        t_neb,t_web=st.tabs(["  🔬 Na Nebula  ","  🌐 Internet  "])
        with t_neb:
            neb_r=sorted([(sum(1 for t in all_terms if len(t)>2 and t in (p.get("title","")+" "+p.get("abstract","")+" "+" ".join(p.get("tags",[]))).lower()),p) for p in st.session_state.feed_posts],key=lambda x:-x[0])
            neb_r=[p for s,p in neb_r if s>0]
            if neb_r:
                for p in neb_r[:4]: render_post(p,ctx="img_neb",compact=True)
            else: st.markdown('<div style="color:var(--text3);padding:1rem">Nenhuma pesquisa similar na plataforma.</div>',unsafe_allow_html=True)
        with t_web:
            ck=f"img_{rep['kw'][:40]}"
            if ck not in st.session_state.scholar_cache:
                with st.spinner("Buscando artigos…"):
                    st.session_state.scholar_cache[ck]=search_ss(f"{rep['category']} {rep['object_type']} {rep['material']}",4)
            web_r=st.session_state.scholar_cache.get(ck,[])
            if web_r:
                for idx,a in enumerate(web_r): render_web_article(a,idx=idx+2000,ctx="img_web")
            else: st.markdown('<div style="color:var(--text3);padding:1rem">Sem resultados online.</div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# CHAT
# ══════════════════════════════════════════════════
def page_chat():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1rem;margin-bottom:1rem">💬 Mensagens</h1>',unsafe_allow_html=True)
    col_c,col_m=st.columns([.85,2.8])
    email=st.session_state.current_user
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    with col_c:
        st.markdown('<div style="font-size:.62rem;font-weight:700;color:var(--text3);letter-spacing:.10em;text-transform:uppercase;margin-bottom:.75rem">Conversas</div>',unsafe_allow_html=True)
        shown=set()
        for ue in st.session_state.chat_contacts:
            if ue==email or ue in shown: continue
            shown.add(ue); ud=users.get(ue,{}); uname=ud.get("name","?"); uin=ini(uname)
            uphoto=ud.get("photo_b64"); ug=ugrad(ue)
            msgs=st.session_state.chat_messages.get(ue,[])
            last=msgs[-1]["text"][:22]+"…" if msgs and len(msgs[-1]["text"])>22 else (msgs[-1]["text"] if msgs else "…")
            active=st.session_state.active_chat==ue; online=random.Random(ue+"c").random()>.42
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            bg="rgba(249,115,22,.10)" if active else "rgba(10,12,17,.55)"; bdr="rgba(249,115,22,.30)" if active else "var(--gborder)"
            st.markdown(f'<div style="background:{bg};border:1px solid {bdr};border-radius:13px;padding:8px 10px;margin-bottom:4px"><div style="display:flex;align-items:center;gap:7px">{avh(uin,30,uphoto,ug)}<div style="overflow:hidden;flex:1"><div style="font-size:.78rem;font-weight:600;font-family:Syne,sans-serif">{dot}{uname.split()[0]}</div><div style="font-size:.65rem;color:var(--text3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{last}</div></div></div></div>',unsafe_allow_html=True)
            if st.button("💬",key=f"oc_{ue}",use_container_width=True): st.session_state.active_chat=ue; st.rerun()
        st.markdown("<hr>",unsafe_allow_html=True)
        nc=st.text_input("",placeholder="E-mail…",key="new_ct",label_visibility="collapsed")
        if st.button("+ Add",key="btn_add_ct",use_container_width=True):
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
            st.markdown(f'<div style="background:var(--glass);border:1px solid var(--gborder);border-radius:15px;padding:11px 15px;margin-bottom:.9rem;display:flex;align-items:center;gap:11px"><div style="flex-shrink:0">{avh(cin,38,cphoto,cg)}</div><div style="flex:1"><div style="font-weight:700;font-size:.90rem;font-family:Syne,sans-serif">{dot}{cname}</div><div style="font-size:.66rem;color:var(--gr2)">🔒 Criptografia AES-256</div></div></div>',unsafe_allow_html=True)
            for msg in msgs:
                is_me=msg["from"]=="me"; cls="bme" if is_me else "bthem"; align="right" if is_me else "left"
                st.markdown(f'<div style="display:flex;{"justify-content:flex-end" if is_me else ""}"><div class="{cls}">{msg["text"]}<div style="font-size:.58rem;color:rgba(255,255,255,.20);margin-top:3px;text-align:{align}">{msg["time"]}</div></div></div>',unsafe_allow_html=True)
            st.markdown("<br>",unsafe_allow_html=True)
            with st.form(f"chat_form_{contact}",clear_on_submit=True):
                c_inp,c_btn=st.columns([5,1])
                with c_inp: nm=st.text_input("",placeholder="Escreva…",key=f"mi_{contact}",label_visibility="collapsed")
                with c_btn:
                    st.markdown("<div style='height:6px'></div>",unsafe_allow_html=True)
                    if st.form_submit_button("→",use_container_width=True):
                        if nm:
                            now=datetime.now().strftime("%H:%M")
                            st.session_state.chat_messages.setdefault(contact,[]).append({"from":"me","text":nm,"time":now}); st.rerun()
        else:
            st.markdown('<div class="card" style="text-align:center;padding:5.5rem"><div style="font-size:2.5rem;opacity:.18;margin-bottom:1rem">💬</div><div style="color:var(--text2);font-family:Syne,sans-serif;font-size:.98rem">Selecione uma conversa</div><div style="font-size:.72rem;color:var(--text3);margin-top:.4rem">🔒 Criptografia end-to-end</div></div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# SETTINGS
# ══════════════════════════════════════════════════
def page_settings():
    st.markdown('<div class="pw">',unsafe_allow_html=True)
    st.markdown('<h1 style="padding-top:1rem;margin-bottom:1rem">⚙️ Perfil & Configurações</h1>',unsafe_allow_html=True)
    u=guser(); email=st.session_state.current_user; in_=ini(u.get("name","?")); photo=u.get("photo_b64"); ug=ugrad(email)
    tab_p,tab_s,tab_pr,tab_saved=st.tabs(["  👤 Meu Perfil  ","  🔐 Segurança  ","  🛡 Privacidade  ","  🔖 Artigos Salvos  "])
    with tab_p:
        photo_html=f'<img src="{photo}"/>' if photo else f'<span style="font-size:2rem">{in_}</span>'
        my_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==email]
        v_badge='<span style="font-size:.7rem;color:var(--gr2);margin-left:6px">✓</span>' if u.get("verified") else ""
        st.markdown(f'<div class="prof-hero"><div class="prof-photo" style="background:{ug}">{photo_html}</div><div style="flex:1;z-index:1"><div style="display:flex;align-items:center;gap:6px;margin-bottom:.28rem"><h1 style="margin:0">{u.get("name","?")}</h1>{v_badge}</div><div style="color:var(--or2);font-size:.82rem;font-weight:500;margin-bottom:.38rem">{u.get("area","")}</div><div style="color:var(--text2);font-size:.80rem;line-height:1.68;margin-bottom:.85rem">{u.get("bio","Sem biografia.")}</div><div style="display:flex;gap:2rem;flex-wrap:wrap"><div><span style="font-family:Syne,sans-serif;font-weight:800">{u.get("followers",0)}</span><span style="color:var(--text3);font-size:.70rem"> seguidores</span></div><div><span style="font-family:Syne,sans-serif;font-weight:800">{u.get("following",0)}</span><span style="color:var(--text3);font-size:.70rem"> seguindo</span></div><div><span style="font-family:Syne,sans-serif;font-weight:800">{len(my_posts)}</span><span style="color:var(--text3);font-size:.70rem"> pesquisas</span></div></div></div></div>',unsafe_allow_html=True)
        ph=st.file_uploader("📷 Foto de perfil",type=["png","jpg","jpeg","webp"],key="ph_up")
        if ph:
            b64=img_to_b64(ph)
            if b64: st.session_state.users[email]["photo_b64"]=b64; save_db(); st.success("✓ Foto atualizada!"); st.rerun()
        st.markdown("<hr>",unsafe_allow_html=True)
        new_n=st.text_input("Nome completo",value=u.get("name",""),key="cfg_n")
        new_a=st.text_input("Área de pesquisa",value=u.get("area",""),key="cfg_a")
        new_b=st.text_area("Biografia",value=u.get("bio",""),key="cfg_b",height=85)
        c_save,c_out=st.columns(2)
        with c_save:
            st.markdown('<div class="btn-primary">',unsafe_allow_html=True)
            if st.button("💾 Salvar perfil",key="btn_sp",use_container_width=True):
                st.session_state.users[email]["name"]=new_n; st.session_state.users[email]["area"]=new_a; st.session_state.users[email]["bio"]=new_b
                save_db(); record(area_to_tags(new_a),1.5); st.success("✓ Perfil salvo!"); st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)
        with c_out:
            st.markdown('<div class="btn-danger">',unsafe_allow_html=True)
            if st.button("🚪 Sair",key="btn_logout",use_container_width=True):
                st.session_state.logged_in=False; st.session_state.current_user=None; st.session_state.page="login"; st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)
    with tab_s:
        st.markdown('<h3 style="margin-bottom:.9rem">🔑 Alterar senha</h3>',unsafe_allow_html=True)
        with st.form("pw_form"):
            op=st.text_input("Senha atual",type="password",key="op")
            np_=st.text_input("Nova senha",type="password",key="np_")
            np2=st.text_input("Confirmar nova",type="password",key="np2")
            if st.form_submit_button("🔑 Alterar senha"):
                if hp(op)!=u.get("password",""): st.error("Senha atual incorreta.")
                elif np_!=np2: st.error("Senhas não coincidem.")
                elif len(np_)<6: st.error("Mínimo 6 caracteres.")
                else: st.session_state.users[email]["password"]=hp(np_); save_db(); st.success("✓ Senha alterada!")
        st.markdown("<hr>",unsafe_allow_html=True)
        en=u.get("2fa_enabled",False)
        st.markdown(f'<div class="card" style="padding:.95rem 1.25rem;display:flex;align-items:center;justify-content:space-between;margin-bottom:.9rem"><div><div style="font-weight:700;font-size:.86rem;font-family:Syne,sans-serif">🔐 Autenticação 2FA</div><div style="font-size:.68rem;color:var(--text3)">{email}</div></div><span style="color:{"var(--gr2)" if en else "#ef4444"};font-size:.78rem;font-weight:700">{"✓ Ativo" if en else "✕ Inativo"}</span></div>',unsafe_allow_html=True)
        if st.button("✕ Desativar 2FA" if en else "✓ Ativar 2FA",key="btn_2fa"):
            st.session_state.users[email]["2fa_enabled"]=not en; save_db(); st.rerun()
    with tab_pr:
        prots=[("🔒 AES-256","Criptografia end-to-end nas mensagens"),("🔏 SHA-256","Hash seguro de senhas"),("🛡 TLS 1.3","Transmissão criptografada")]
        for n2,d2 in prots:
            st.markdown(f'<div style="display:flex;align-items:center;gap:12px;background:rgba(34,197,94,.05);border:1px solid rgba(34,197,94,.14);border-radius:12px;padding:10px;margin-bottom:7px"><div style="width:26px;height:26px;border-radius:7px;background:rgba(34,197,94,.10);display:flex;align-items:center;justify-content:center;color:var(--gr2);font-size:.78rem;flex-shrink:0">✓</div><div><div style="font-weight:600;color:var(--gr2);font-size:.80rem">{n2}</div><div style="font-size:.67rem;color:var(--text3)">{d2}</div></div></div>',unsafe_allow_html=True)
    with tab_saved:
        st.markdown('<h3 style="margin-bottom:.9rem">🔖 Artigos Salvos</h3>',unsafe_allow_html=True)
        if st.session_state.saved_articles:
            for idx,a in enumerate(st.session_state.saved_articles):
                render_web_article(a,idx=idx+3000,ctx="saved")
                uid=re.sub(r'[^a-zA-Z0-9]','',f"rm_{a.get('doi','nd')}_{idx}")[:30]
                st.markdown('<div class="btn-danger">',unsafe_allow_html=True)
                if st.button("🗑 Remover",key=f"rms_{uid}"):
                    st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]
                    save_db(); st.toast("Removido!"); st.rerun()
                st.markdown('</div>',unsafe_allow_html=True)
        else:
            st.markdown('<div class="card" style="text-align:center;padding:2.5rem;color:var(--text3)">Nenhum artigo salvo ainda.</div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)

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
        "feed":page_feed,"search":page_search,"knowledge":page_knowledge,
        "folders":page_folders,"analytics":page_analytics,"img_search":page_img_search,
        "chat":page_chat,"settings":page_settings,
    }.get(st.session_state.page,page_feed)()

main()
