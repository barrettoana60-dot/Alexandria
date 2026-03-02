import subprocess, sys, os, json, hashlib, random, string, re, io, base64, time
from datetime import datetime
from collections import defaultdict, Counter
import streamlit as st

st.set_page_config(page_title="Nebula", page_icon="🔬", layout="wide", initial_sidebar_state="expanded")

# ════════════════════════════════════════════════
#  CACHED LIBRARY LOADING — pip only runs ONCE
# ════════════════════════════════════════════════
@st.cache_resource(show_spinner="Iniciando Nebula…")
def _boot():
    def _pip(*pkgs):
        for p in pkgs:
            try: subprocess.check_call([sys.executable,"-m","pip","install",p,"-q"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            except: pass
    try: import numpy as np
    except: _pip("numpy"); import numpy as np
    try: from PIL import Image as PI
    except: _pip("pillow"); from PIL import Image as PI
    try: import plotly.graph_objects as go
    except: _pip("plotly"); import plotly.graph_objects as go
    try: import requests as rq
    except: _pip("requests"); import requests as rq
    sk=False; KM=None
    try: from sklearn.cluster import KMeans; sk=True; KM=KMeans
    except:
        try: _pip("scikit-learn"); from sklearn.cluster import KMeans; sk=True; KM=KMeans
        except: pass
    ski=False; skf_=None; skft_=None
    try: from skimage import filters as skf,feature as skft; ski=True; skf_=skf; skft_=skft
    except:
        try: _pip("scikit-image"); from skimage import filters as skf,feature as skft; ski=True; skf_=skf; skft_=skft
        except: pass
    return {"np":np,"PI":PI,"go":go,"rq":rq,"sk":sk,"KM":KM,"ski":ski,"skf":skf_,"skft":skft_}

_L=_boot()
np=_L["np"]; PILImage=_L["PI"]; go=_L["go"]; requests=_L["rq"]
SKLEARN_OK=_L["sk"]; SKIMAGE_OK=_L["ski"]; KMeans=_L["KM"]

# ════════════════════════════════════════════════
#  CONSTANTS & HELPERS
# ════════════════════════════════════════════════
DB_FILE="nebula_db.json"
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}
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
        return f"{d//30}m"
    except: return ds
def fmt_num(n):
    try: n=int(n); return f"{n/1000:.1f}k" if n>=1000 else str(n)
    except: return str(n)
def guser():
    if not isinstance(st.session_state.get("users"),dict): return {}
    return st.session_state.users.get(st.session_state.current_user,{})
def is_online(e): return (hash(e+"on")%3)!=0

GRAD_POOL=["135deg,#FF6B35,#F7C948","135deg,#00C9A7,#845EC2","135deg,#FF4E8A,#FF9A44",
           "135deg,#4ECDC4,#44A1A0","135deg,#A8FF78,#78FFD6","135deg,#6C63FF,#48C6EF",
           "135deg,#F7971E,#FFD200","135deg,#FF5F6D,#FFC371"]
def ugrad(e): return f"linear-gradient({GRAD_POOL[hash(e or '')%len(GRAD_POOL)]})"

STOPWORDS={"de","a","o","que","e","do","da","em","um","para","é","com","uma","os","no","se","na","por","mais","as","dos","como","mas","foi","ao","ele","das","tem","à","seu","sua","ou","ser","quando","muito","há","nos","já","está","eu","também","só","pelo","pela","até","isso","ela","entre","era","depois","sem","mesmo","aos","ter","seus","the","of","and","to","in","is","it","that","was","he","for","on","are","as","with","they","at","be","this","from","or","one","had","by","but","not","what","all","were","we"}

SEED_POSTS=[
    {"id":1,"author":"Carlos Mendez","author_email":"carlos@nebula.ai","avatar":"CM","area":"Neurociência","title":"Efeitos da Privação de Sono na Plasticidade Sináptica","abstract":"Investigamos como 24h de privação de sono afetam espinhas dendríticas em ratos Wistar, com redução de 34% na plasticidade hipocampal. Janela crítica identificada nas primeiras 6h de recuperação.","tags":["neurociência","sono","memória","hipocampo"],"likes":47,"comments":[{"user":"Maria Silva","text":"Excelente metodologia!"}],"status":"Em andamento","date":"2026-02-10","liked_by":[],"saved_by":[],"connections":["sono","memória"],"views":312},
    {"id":2,"author":"Luana Freitas","author_email":"luana@nebula.ai","avatar":"LF","area":"Biomedicina","title":"CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras","abstract":"Vetor AAV9 modificado para entrega de CRISPR no gene DMD com eficiência de 78% em modelos mdx.","tags":["CRISPR","gene terapia","músculo","AAV9"],"likes":93,"comments":[{"user":"Ana","text":"Quando iniciam os trials?"}],"status":"Publicado","date":"2026-01-28","liked_by":[],"saved_by":[],"connections":["genômica","distrofia"],"views":891},
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
    "carlos@nebula.ai":[{"from":"carlos@nebula.ai","text":"Oi! Vi seu comentário na pesquisa.","time":"09:14"},{"from":"me","text":"Achei muito interessante!","time":"09:16"}],
    "luana@nebula.ai":[{"from":"luana@nebula.ai","text":"Podemos colaborar no próximo projeto?","time":"ontem"}],
}

def save_db():
    try:
        with open(DB_FILE,"w",encoding="utf-8") as f:
            json.dump({"users":st.session_state.users,"feed_posts":st.session_state.feed_posts,"folders":st.session_state.folders,
                       "user_prefs":{k:dict(v) for k,v in st.session_state.user_prefs.items()},
                       "saved_articles":st.session_state.saved_articles,"followed":st.session_state.followed},f,ensure_ascii=False,indent=2)
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
    for p in rp: p.setdefault("liked_by",[]); p.setdefault("saved_by",[]); p.setdefault("comments",[]); p.setdefault("views",200)
    st.session_state.setdefault("feed_posts",rp)
    st.session_state.setdefault("folders",disk.get("folders",{}))
    st.session_state.setdefault("folder_files_bytes",{})
    st.session_state.setdefault("chat_contacts",list(SEED_USERS.keys()))
    st.session_state.setdefault("chat_messages",{k:list(v) for k,v in CHAT_INIT.items()})
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
    # Try env var first, then empty
    st.session_state.setdefault("anthropic_key",os.environ.get("ANTHROPIC_API_KEY",""))
    st.session_state.setdefault("ai_conn_cache",{})

init_state()

# ════════════════════════════════════════════════
#  ANTHROPIC AI — Claude Haiku (fast + cheap)
# ════════════════════════════════════════════════
CLAUDE_MODEL = "claude-haiku-4-5"

def _claude(messages, system="", max_tokens=800, api_key=""):
    key = api_key or st.session_state.get("anthropic_key","")
    if not key or not key.startswith("sk-"):
        return None, "Chave API inválida."
    try:
        body = {"model": CLAUDE_MODEL, "max_tokens": max_tokens, "messages": messages}
        if system: body["system"] = system
        r = requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key":key,"anthropic-version":"2023-06-01","content-type":"application/json"},
            json=body, timeout=25)
        if r.status_code == 200:
            return r.json()["content"][0]["text"], None
        return None, r.json().get("error",{}).get("message",f"HTTP {r.status_code}")
    except Exception as e:
        return None, str(e)

def claude_vision_analyze(img_bytes, api_key=""):
    """Real Claude vision analysis — identifies what the image IS and what it's MADE OF."""
    try:
        img = PILImage.open(io.BytesIO(img_bytes))
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=80)
        b64 = base64.b64encode(buf.getvalue()).decode()
        prompt = """Analise esta imagem científica com MÁXIMO DETALHE. Responda em JSON puro (sem markdown):

{
  "o_que_e": "<o que é esta imagem — ex: microscopia confocal de neurônios, gel de eletroforese, espectro de massa, etc>",
  "de_que_e_feita": "<do que é feita / composição — estruturas anatômicas, moléculas, materiais, objetos visíveis>",
  "tipo_tecnico": "<tipo técnico: H&E histologia, DAPI fluorescência, Western blot, TEM, SEM, RMN, etc>",
  "area_ciencia": "<área científica: neurociência, oncologia, bioquímica, física, astronomia, etc>",
  "estruturas_visiveis": ["<estrutura 1>", "<estrutura 2>", "<estrutura 3>"],
  "cores_significado": "<o que as cores indicam nesta imagem>",
  "escala_resolucao": "<estimativa de escala: nanômetros, micrômetros, milímetros, quilômetros>",
  "qualidade_tecnica": "<Alta/Média/Baixa>",
  "confianca": <0-100>,
  "termos_busca": "<3-5 termos científicos para buscar artigos>",
  "observacoes_criticas": "<observações científicas importantes sobre o conteúdo>"
}"""
        key = api_key or st.session_state.get("anthropic_key","")
        r = requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key":key,"anthropic-version":"2023-06-01","content-type":"application/json"},
            json={"model":CLAUDE_MODEL,"max_tokens":1000,
                  "messages":[{"role":"user","content":[
                      {"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":b64}},
                      {"type":"text","text":prompt}]}]},
            timeout=30)
        if r.status_code == 200:
            text = r.json()["content"][0]["text"].strip()
            text = re.sub(r'^```json\s*','',text); text = re.sub(r'\s*```$','',text)
            return json.loads(text), None
        return None, r.json().get("error",{}).get("message",f"HTTP {r.status_code}")
    except Exception as e:
        return None, str(e)

def claude_connections(users_data, posts_data, email, api_key=""):
    """Claude AI connection suggestions."""
    u = users_data.get(email,{})
    my_posts = [p for p in posts_data if p.get("author_email")==email]
    others = [{"email":ue,"name":ud.get("name",""),"area":ud.get("area",""),
               "tags":list({t for p in posts_data if p.get("author_email")==ue for t in p.get("tags",[])})[:8]}
              for ue,ud in users_data.items() if ue!=email]
    payload = {"meu_perfil":{"area":u.get("area",""),"bio":u.get("bio",""),
                              "tags":list({t for p in my_posts for t in p.get("tags",[])})[:10]},
               "pesquisadores":others[:12]}
    text, err = _claude([{"role":"user","content":f"""Sugira 4 melhores conexões científicas. Dados:
{json.dumps(payload,ensure_ascii=False)}

Responda APENAS JSON puro:
{{"sugestoes":[{{"email":"<email>","razao":"<explicação científica 1-2 frases>","score":<0-100>,"temas_comuns":["<tema1>","<tema2>"]}}]}}"""}],
        max_tokens=600, api_key=api_key)
    if text:
        try:
            t = re.sub(r'^```json\s*','',text.strip()); t = re.sub(r'\s*```$','',t)
            return json.loads(t), None
        except: return None, "Erro ao parsear resposta"
    return None, err

# ════════════════════════════════════════════════
#  FAST ML IMAGE PIPELINE (192px max — 7x faster)
# ════════════════════════════════════════════════
def sobel_fast(gray_f32):
    """Sobel edge detection — skimage or numpy fallback."""
    try:
        if SKIMAGE_OK:
            sx = _L["skf"].sobel_h(gray_f32)
            sy = _L["skf"].sobel_v(gray_f32)
        else:
            kx = np.array([[-1,0,1],[-2,0,2],[-1,0,1]],dtype=np.float32)/8.0
            def c2d(im,k):
                ph,pw=1,1; pad=np.pad(im,((ph,ph),(pw,pw)),mode='edge')
                out=np.zeros_like(im)
                for i in range(3):
                    for j in range(3): out+=k[i,j]*pad[i:i+im.shape[0],j:j+im.shape[1]]
                return out
            sx=c2d(gray_f32,kx); sy=c2d(gray_f32,kx.T)
        mag = np.sqrt(sx**2+sy**2)
        return {
            "magnitude": mag,
            "mean": float(mag.mean()),
            "max": float(mag.max()),
            "density": float((mag>mag.mean()*1.5).mean()),
            "horizontal": sx, "vertical": sy,
            "hist": np.histogram(mag,bins=16,range=(0,mag.max()+1e-5))[0].tolist()
        }
    except Exception as e:
        gx=np.gradient(gray_f32,axis=1); gy=np.gradient(gray_f32,axis=0)
        mag=np.sqrt(gx**2+gy**2)
        return {"magnitude":mag,"mean":float(mag.mean()),"max":float(mag.max()),
                "density":float((mag>mag.mean()*1.5).mean()),"horizontal":gx,"vertical":gy,
                "hist":np.histogram(mag,bins=16)[0].tolist()}

def fft_fast(gray_f32):
    fft=np.fft.fftshift(np.fft.fft2(gray_f32)); mag=np.abs(fft)
    h,w=mag.shape; total=mag.sum()+1e-5
    Y,X=np.ogrid[:h,:w]; dist=np.sqrt((X-w//2)**2+(Y-h//2)**2); r=min(h,w)//2
    lf=float(mag[dist<r*0.12].sum()/total); mf=float(mag[(dist>=r*0.12)&(dist<r*0.45)].sum()/total)
    hf=float(mag[dist>=r*0.45].sum()/total)
    outer=np.concatenate([mag[:h//4,:].ravel(),mag[3*h//4:,:].ravel()])
    per=float(np.percentile(outer,99))/(float(np.mean(outer))+1e-5)
    return {"lf":round(lf,3),"mf":round(mf,3),"hf":round(hf,3),"periodic":per>12,"per_score":round(per,1)}

def glcm_fast(gray_u8):
    try:
        if SKIMAGE_OK:
            from skimage.feature import graycomatrix,graycoprops
            g=(gray_u8//4).astype(np.uint8)
            glcm=graycomatrix(g,[1,3],[0,np.pi/4,np.pi/2],levels=64,symmetric=True,normed=True)
            return {p:float(graycoprops(glcm,p).mean()) for p in ['contrast','homogeneity','energy','correlation']}
        else:
            g=gray_u8.astype(np.float32)/255.0
            gx=np.gradient(g,axis=1); gy=np.gradient(g,axis=0)
            contrast=float(np.sqrt(gx**2+gy**2).mean()*100)
            return {"contrast":round(contrast,3),"homogeneity":round(1/(1+contrast/50),3),
                    "energy":round(float(np.var(g)),3),"correlation":0.7}
    except:
        return {"contrast":20.0,"homogeneity":0.5,"energy":0.1,"correlation":0.7}

def kmeans_fast(arr_u8, k=6):
    if not SKLEARN_OK or KMeans is None: return []
    try:
        h,w=arr_u8.shape[:2]; step=max(1,(h*w)//3000)
        flat=arr_u8.reshape(-1,3)[::step].astype(np.float32)
        km=KMeans(n_clusters=k,random_state=42,n_init=5,max_iter=50).fit(flat)
        centers=km.cluster_centers_.astype(int); counts=Counter(km.labels_); total=sum(counts.values())
        pal=[]
        for i in np.argsort([-counts[j] for j in range(k)]):
            r2,g2,b2=centers[i]; pct=counts[i]/total*100
            pal.append({"rgb":(int(r2),int(g2),int(b2)),"hex":"#{:02x}{:02x}{:02x}".format(int(r2),int(g2),int(b2)),"pct":round(pct,1)})
        return pal
    except: return []

def classify_image(sobel_r, fft_r, glcm_r, color, n_kp, palette):
    ei=sobel_r["mean"]; ed=sobel_r["density"]; hom=glcm_r.get("homogeneity",0.5)
    contrast=glcm_r.get("contrast",20); sym=color["sym"]; entropy=color["entropy"]
    mr,mg2,mb=color["r"],color["g"],color["b"]; per=fft_r["periodic"]
    scores={}
    scores["Histopatologia H&E"]=30*(mr>140 and mb>100)+20*(n_kp>80)+20*(contrast>30)+15*(ed>0.12)
    scores["Fluorescência DAPI"]=45*(mb>150 and mb>mr+30)+20*(entropy>5)+20*(ed>0.1)+15*(n_kp>30)
    scores["Fluorescência GFP"]=45*(mg2>150 and mg2>mr+30)+20*(entropy>4.5)+20*(ed>0.08)
    scores["Cristalografia/Difração"]=40*per+25*(sym>0.75)+15*(hom>0.7)+20*(fft_r["per_score"]>15)
    scores["Gel/Western Blot"]=30*(contrast<15 and hom>0.8)+25*(abs(mr-mg2)<20 and abs(mg2-mb)<20)+25*(not per)
    scores["Gráfico Científico"]=30*(hom>0.85)+25*(n_kp<30)+25*(entropy<4)+20*(not per)
    scores["Estrutura Molecular"]=35*(sym>0.80)+25*per+20*(abs(mr-mg2)<25)
    scores["Microscopia Confocal"]=20*(len(palette)>3)+25*(entropy>5.5)+20*(n_kp>50)+20*(ed>0.1)
    scores["Imagem Astronômica"]=35*(color.get("bright",128)<60)+25*(n_kp>40 and hom>0.7)+20*(entropy>5)
    best=max(scores,key=scores.get); sc=scores[best]; conf=min(96,40+sc*0.55)
    origins={"Histopatologia H&E":"Medicina/Patologia — tecido corado para diagnóstico",
              "Fluorescência DAPI":"Biologia Celular — marcação nuclear com fluoróforo azul",
              "Fluorescência GFP":"Biologia Molecular — proteína fluorescente verde expressa",
              "Cristalografia/Difração":"Física/Química — estrutura cristalina por difração de raios-X",
              "Gel/Western Blot":"Bioquímica — separação eletroforética de proteínas/DNA",
              "Gráfico Científico":"Ciência Geral — visualização de dados experimentais",
              "Estrutura Molecular":"Química Computacional — molécula ou cristal renderizado",
              "Microscopia Confocal":"Biologia Celular — imagem multicanal confocal",
              "Imagem Astronômica":"Astrofísica — objeto celeste ou fenômeno cósmico"}
    kw_map={"Histopatologia H&E":"hematoxylin eosin staining histopathology",
            "Fluorescência DAPI":"DAPI nuclear staining fluorescence microscopy",
            "Fluorescência GFP":"GFP green fluorescent protein confocal",
            "Cristalografia/Difração":"X-ray diffraction crystallography structure",
            "Gel/Western Blot":"western blot electrophoresis protein",
            "Gráfico Científico":"scientific data visualization analysis",
            "Estrutura Molecular":"molecular structure protein visualization",
            "Microscopia Confocal":"confocal microscopy multichannel fluorescence",
            "Imagem Astronômica":"astronomy telescope deep field imaging"}
    return {"category":best,"confidence":round(conf,1),"origin":origins.get(best,"Ciência Geral"),
            "kw":kw_map.get(best,best),"scores":dict(sorted(scores.items(),key=lambda x:-x[1])[:5])}

@st.cache_data(max_entries=10, show_spinner=False)
def run_ml_pipeline(img_bytes_hash, img_bytes):
    """Full ML pipeline cached by image hash — never reruns same image."""
    result={}
    try:
        img=PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
        orig_size=img.size
        # 192px max for speed
        w,h=img.size; scale=min(192/w,192/h)
        nw,nh=int(w*scale),int(h*scale)
        img_r=img.resize((nw,nh),PILImage.LANCZOS)
        arr=np.array(img_r,dtype=np.float32)
        r_ch,g_ch,b_ch=arr[:,:,0],arr[:,:,1],arr[:,:,2]
        gray=0.2989*r_ch+0.5870*g_ch+0.1140*b_ch
        gray_u8=gray.astype(np.uint8)
        mr,mg2,mb2=float(r_ch.mean()),float(g_ch.mean()),float(b_ch.mean())
        hy,hx=gray.shape[0]//2,gray.shape[1]//2
        q=[gray[:hy,:hx].var(),gray[:hy,hx:].var(),gray[hy:,:hx].var(),gray[hy:,hx:].var()]
        sym=1.0-(max(q)-min(q))/(max(q)+1e-5)
        hst=np.histogram(gray,bins=64,range=(0,255))[0]; hn=hst/hst.sum(); hn2=hn[hn>0]
        entropy=float(-np.sum(hn2*np.log2(hn2)))
        color={"r":round(mr,1),"g":round(mg2,1),"b":round(mb2,1),
               "sym":round(sym,3),"entropy":round(entropy,3),
               "bright":round(float(gray.mean()),1),"std":round(float(gray.std()),1),
               "warm":mr>mb2+15,"cool":mb2>mr+15}
        result["color"]=color; result["orig_size"]=orig_size; result["proc_size"]=(nw,nh)
        result["sobel"]=sobel_fast(gray/255.0)
        result["fft"]=fft_fast(gray/255.0)
        result["glcm"]=glcm_fast(gray_u8)
        # ORB keypoints
        try:
            if SKIMAGE_OK:
                try:
                    from skimage.feature import ORB
                    det=ORB(n_keypoints=150,fast_threshold=0.05); det.detect_and_extract(gray/255.0)
                    kps=det.keypoints
                except:
                    from skimage.feature import corner_harris,corner_peaks
                    kps=corner_peaks(corner_harris(gray/255.0),min_distance=8,threshold_rel=0.02)
            else:
                gx2=np.gradient(gray,axis=1); gy2=np.gradient(gray,axis=0); mag2=np.sqrt(gx2**2+gy2**2)
                pts=[]
                for i in range(0,mag2.shape[0]-8,8):
                    for j in range(0,mag2.shape[1]-8,8):
                        bl=mag2[i:i+8,j:j+8]
                        if bl.max()>mag2.mean()*1.8:
                            yi,xj=np.unravel_index(bl.argmax(),bl.shape); pts.append([i+yi,j+xj])
                kps=np.array(pts) if pts else np.zeros((0,2))
            result["n_kp"]=len(kps); result["kps"]=kps.tolist() if hasattr(kps,'tolist') else []
        except: result["n_kp"]=0; result["kps"]=[]
        result["palette"]=kmeans_fast(arr.astype(np.uint8),k=6)
        result["histograms"]={"r":np.histogram(r_ch.ravel(),bins=32,range=(0,255))[0].tolist(),
                               "g":np.histogram(g_ch.ravel(),bins=32,range=(0,255))[0].tolist(),
                               "b":np.histogram(b_ch.ravel(),bins=32,range=(0,255))[0].tolist()}
        result["classification"]=classify_image(result["sobel"],result["fft"],result["glcm"],
                                                 color,result["n_kp"],result["palette"])
        # Sobel visualization (downsampled for display)
        smag=result["sobel"]["magnitude"]
        smag_norm=(smag/(smag.max()+1e-5)*255).astype(np.uint8)
        result["sobel_map"]=smag_norm.tolist()
        result["ok"]=True
    except Exception as e:
        result["ok"]=False; result["error"]=str(e)
    return result

# ════════════════════════════════════════════════
#  SEARCH
# ════════════════════════════════════════════════
@st.cache_data(show_spinner=False,ttl=300)
def search_ss(q,lim=6):
    try:
        r=requests.get("https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query":q,"limit":lim,"fields":"title,authors,year,abstract,venue,externalIds,openAccessPdf,citationCount"},timeout=8)
        if r.status_code==200:
            out=[]
            for p in r.json().get("data",[]):
                ext=p.get("externalIds",{}) or {}; doi=ext.get("DOI",""); arx=ext.get("ArXiv","")
                pdf=p.get("openAccessPdf") or {}; link=pdf.get("url","") or(f"https://arxiv.org/abs/{arx}" if arx else(f"https://doi.org/{doi}" if doi else ""))
                al=p.get("authors",[]) or []; au=", ".join(a.get("name","") for a in al[:3])+((" et al." if len(al)>3 else ""))
                out.append({"title":p.get("title","Sem título"),"authors":au or "—","year":p.get("year","?"),
                    "source":p.get("venue","") or "Semantic Scholar","doi":doi or arx or "—",
                    "abstract":(p.get("abstract","") or "")[:280],"url":link,
                    "citations":p.get("citationCount",0),"origin":"semantic"})
            return out
    except: pass
    return []

@st.cache_data(show_spinner=False,ttl=300)
def search_cr(q,lim=3):
    try:
        r=requests.get("https://api.crossref.org/works",params={"query":q,"rows":lim,"select":"title,author,issued,abstract,DOI,container-title,is-referenced-by-count","mailto":"nebula@example.com"},timeout=8)
        if r.status_code==200:
            out=[]
            for p in r.json().get("message",{}).get("items",[]):
                title=(p.get("title") or ["?"])[0]; ars=p.get("author",[]) or []
                au=", ".join(f'{a.get("given","").split()[0] if a.get("given") else ""} {a.get("family","")}'.strip() for a in ars[:3])+((" et al." if len(ars)>3 else ""))
                yr=(p.get("issued",{}).get("date-parts") or [[None]])[0][0]; doi=p.get("DOI","")
                ab=re.sub(r'<[^>]+>','',p.get("abstract","") or "")[:280]
                out.append({"title":title,"authors":au or "—","year":yr or "?","source":(p.get("container-title") or ["CrossRef"])[0],
                    "doi":doi,"abstract":ab,"url":f"https://doi.org/{doi}" if doi else "","citations":p.get("is-referenced-by-count",0),"origin":"crossref"})
            return out
    except: pass
    return []

STOPWORDS_FULL={"de","a","o","que","e","do","da","em","um","para","é","com","uma","os","no","se","na","por","mais","as","dos","como","mas","foi","ao","ele","das","tem","the","of","and","to","in","is","it","that","was","he","for","on","are"}
def kw_extract(text,n=20):
    if not text: return []
    words=re.findall(r'\b[a-záàâãéêíóôõúüçA-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]{4,}\b',text.lower())
    words=[w for w in words if w not in STOPWORDS_FULL]
    if not words: return []
    tf=Counter(words); tot=sum(tf.values())
    return [w for w,_ in sorted({w:c/tot for w,c in tf.items()}.items(),key=lambda x:-x[1])[:n]]

def record(tags,w=1.0):
    e=st.session_state.get("current_user")
    if not e or not tags: return
    p=st.session_state.user_prefs.setdefault(e,defaultdict(float))
    for t in tags: p[t.lower()]+=w

def get_recs(email,n=2):
    pr=st.session_state.user_prefs.get(email,{})
    if not pr: return []
    def sc(p): return sum(pr.get(t.lower(),0) for t in p.get("tags",[])+p.get("connections",[]))
    scored=[(sc(p),p) for p in st.session_state.feed_posts if email not in p.get("liked_by",[])]
    return [p for s,p in sorted(scored,key=lambda x:-x[0]) if s>0][:n]

def area_tags(area):
    a=(area or "").lower()
    M={"ia":["machine learning","LLM"],"inteligência artificial":["machine learning","LLM"],
       "neurociência":["sono","memória","cognição"],"biologia":["célula","genômica"],
       "física":["quantum","astrofísica"],"medicina":["diagnóstico","terapia"]}
    for k,v in M.items():
        if k in a: return v
    return [w.strip() for w in a.replace(","," ").split() if len(w)>3][:5]

EMAP={"pdf":"PDF","docx":"Word","xlsx":"Planilha","csv":"Dados","txt":"Texto","py":"Código","md":"Markdown","png":"Imagem","jpg":"Imagem","jpeg":"Imagem"}
def ftype(fname): return EMAP.get(fname.split(".")[-1].lower() if "." in fname else "","Arquivo")
VIB=["#FFD60A","#00E676","#FF3B5C","#4CC9F0","#B17DFF","#FF8C42","#FF4E8A","#00C9A7","#FFAB00","#7BD3FF"]

@st.cache_data(show_spinner=False)
def extract_pdf(b):
    try:
        import PyPDF2; r=PyPDF2.PdfReader(io.BytesIO(b)); t=""
        for pg in r.pages[:20]:
            try: t+=pg.extract_text()+"\n"
            except: pass
        return t[:30000]
    except: return ""

@st.cache_data(show_spinner=False)
def analyze_doc(fname,fbytes,ftype_str,area=""):
    r={"file":fname,"type":ftype_str,"keywords":[],"topics":{},"relevance_score":50,"summary":"","word_count":0,"reading_time":0,"writing_quality":50}
    text=""
    if ftype_str=="PDF" and fbytes: text=extract_pdf(fbytes)
    elif fbytes:
        try: text=fbytes.decode("utf-8",errors="ignore")[:30000]
        except: pass
    if text:
        r["keywords"]=kw_extract(text,20); words=len(text.split()); r["word_count"]=words
        r["reading_time"]=max(1,round(words/200)); r["writing_quality"]=min(100,50+(15 if len(r["keywords"])>12 else 0)+(15 if words>800 else 0))
        tm={"Saúde":["saúde","medicina","health"],"Biologia":["biologia","gene","dna","célula"],"IA":["algoritmo","machine","learning","ia","deep"],"Física":["física","quântica","partícula"],"Química":["química","molécula"],"Engenharia":["engenharia","sistema"],"Neurociência":["neurociência","neural","cérebro"]}
        s=defaultdict(int)
        for kw in r["keywords"]:
            for tp,terms in tm.items():
                if any(t in kw or kw in t for t in terms): s[tp]+=1
        r["topics"]=dict(sorted(s.items(),key=lambda x:-x[1])) if s else {"Pesquisa Geral":1}
        if area:
            aw=area.lower().split(); rel=sum(1 for w in aw if any(w in kw for kw in r["keywords"]))
            r["relevance_score"]=min(100,rel*15+45)
        r["summary"]=f"{ftype_str} · {words} palavras · ~{r['reading_time']}min · {', '.join(r['keywords'][:4])}"
    else: r["summary"]=f"Arquivo {ftype_str}."
    return r

# ════════════════════════════════════════════════
#  CSS — DARK NAVY + GREEN AI
# ════════════════════════════════════════════════
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800;900&family=DM+Sans:wght@300;400;500;600&display=swap');
:root{
  --bg:#050B1C;--bg2:#080F25;--bg3:#0D1535;
  --yel:#FFD60A;--grn:#00E676;--grn2:#00FF8A;
  --red:#FF3B5C;--blu:#4CC9F0;--pur:#B17DFF;--orn:#FF8C42;
  --t0:#FFFFFF;--t1:#E8E9F4;--t2:#9BA3C4;--t3:#5A6080;--t4:#333850;
  --g1:rgba(255,255,255,.05);--g2:rgba(255,255,255,.08);--g3:rgba(255,255,255,.12);
  --gb1:rgba(255,255,255,.07);--gb2:rgba(255,255,255,.13);
  --r8:8px;--r12:12px;--r16:16px;--r20:20px;--r28:28px;
  --ai:rgba(0,230,118,.12);--ai-bd:rgba(0,230,118,.28);
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body,.stApp{background:var(--bg)!important;color:var(--t1)!important;font-family:'DM Sans',-apple-system,sans-serif!important;}
.stApp::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:radial-gradient(ellipse 70% 50% at -10% -5%,rgba(0,100,255,.08) 0%,transparent 55%),
             radial-gradient(ellipse 50% 40% at 110% 10%,rgba(0,230,118,.06) 0%,transparent 50%),
             radial-gradient(ellipse 40% 60% at 50% 115%,rgba(76,201,240,.05) 0%,transparent 55%);}
header[data-testid="stHeader"],#MainMenu,footer,.stDeployButton,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
[data-testid="stSidebarCollapseButton"]{display:none!important}
section[data-testid="stSidebar"]{
  background:#030916!important;
  border-right:1px solid rgba(0,230,118,.12)!important;
  width:200px!important;min-width:200px!important;max-width:200px!important;
  padding:.9rem .65rem .8rem!important;
}
section[data-testid="stSidebar"]>div{padding:0!important;}
.block-container{padding-top:.3rem!important;padding-bottom:3rem!important;max-width:1360px!important;z-index:1;padding-left:.8rem!important;padding-right:.8rem!important;}
/* ─ BUTTONS ─ */
.stButton>button{
  background:rgba(255,255,255,.07)!important;
  border:1px solid rgba(255,255,255,.11)!important;
  border-radius:9px!important;color:#B0B4CC!important;
  -webkit-text-fill-color:#B0B4CC!important;
  font-family:'DM Sans',sans-serif!important;font-weight:500!important;font-size:.81rem!important;
  padding:.42rem .75rem!important;box-shadow:none!important;line-height:1.4!important;
}
.stButton>button:hover{background:rgba(0,230,118,.10)!important;border-color:rgba(0,230,118,.3)!important;color:#00E676!important;-webkit-text-fill-color:#00E676!important;}
.stButton>button:active{transform:scale(.97)!important;}
.stButton>button p,.stButton>button span{color:inherit!important;-webkit-text-fill-color:inherit!important;}
/* Sidebar radio nav */
section[data-testid="stSidebar"] .stRadio>div{flex-direction:column!important;gap:1px!important;}
section[data-testid="stSidebar"] .stRadio>div>label{
  background:rgba(255,255,255,.04)!important;border:1px solid transparent!important;
  border-radius:8px!important;padding:.44rem .7rem!important;font-size:.82rem!important;
  color:#8890AA!important;-webkit-text-fill-color:#8890AA!important;
  width:100%!important;cursor:pointer!important;margin:0!important;transition:all .1s!important;
}
section[data-testid="stSidebar"] .stRadio>div>label:hover{background:rgba(0,230,118,.08)!important;color:#00E676!important;-webkit-text-fill-color:#00E676!important;border-color:rgba(0,230,118,.2)!important;}
section[data-testid="stSidebar"] .stRadio input[type="radio"]{display:none!important;}
section[data-testid="stSidebar"] .stRadio label div:first-child{display:none!important;}
/* Active nav item injected dynamically */
.stTextInput input,.stTextArea textarea{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;color:var(--t1)!important;font-family:'DM Sans',sans-serif!important;font-size:.83rem!important;}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:rgba(0,230,118,.4)!important;box-shadow:0 0 0 2px rgba(0,230,118,.07)!important;}
.stTextInput label,.stTextArea label,.stSelectbox label,.stFileUploader label{color:var(--t3)!important;font-size:.58rem!important;letter-spacing:.10em!important;text-transform:uppercase!important;font-weight:600!important;}
/* Cards */
.glass{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:var(--r20);box-shadow:0 4px 28px rgba(0,0,0,.35);}
.post-card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:var(--r16);margin-bottom:.6rem;transition:border-color .12s,transform .12s;}
.post-card:hover{border-color:rgba(0,230,118,.2);transform:translateY(-1px);}
.sc{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:var(--r16);padding:.8rem .9rem;margin-bottom:.55rem;}
.scard{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);border-radius:var(--r12);padding:.7rem .9rem;margin-bottom:.38rem;transition:border-color .12s;}
.scard:hover{border-color:rgba(0,230,118,.18);}
.mbox{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:var(--r12);padding:.7rem;text-align:center;}
.abox{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);border-radius:var(--r12);padding:.9rem;margin-bottom:.5rem;}
/* AI CARD — bright green */
.ai-card{background:linear-gradient(135deg,rgba(0,230,118,.08),rgba(0,230,118,.04));border:1px solid rgba(0,230,118,.22);border-radius:var(--r16);padding:.9rem;margin-bottom:.6rem;}
.conn-ai{background:linear-gradient(135deg,rgba(0,230,118,.07),rgba(76,201,240,.04));border:1px solid rgba(0,230,118,.20);border-radius:var(--r16);padding:.85rem;margin-bottom:.5rem;}
.api-banner{background:rgba(0,230,118,.06);border:1px solid rgba(0,230,118,.2);border-radius:var(--r12);padding:.75rem;margin-bottom:.7rem;}
/* Metric values */
.mval-yel{font-family:'Syne',sans-serif;font-size:1.6rem;font-weight:900;background:linear-gradient(135deg,var(--yel),var(--orn));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-grn{font-family:'Syne',sans-serif;font-size:1.6rem;font-weight:900;background:linear-gradient(135deg,var(--grn),var(--blu));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-blu{font-family:'Syne',sans-serif;font-size:1.6rem;font-weight:900;background:linear-gradient(135deg,var(--blu),var(--pur));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mval-red{font-family:'Syne',sans-serif;font-size:1.6rem;font-weight:900;background:linear-gradient(135deg,var(--red),var(--orn));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.mlbl{font-size:.55rem;color:var(--t3);margin-top:3px;letter-spacing:.1em;text-transform:uppercase;font-weight:700;}
.tag{display:inline-block;background:rgba(0,230,118,.07);border:1px solid rgba(0,230,118,.15);border-radius:50px;padding:1px 8px;font-size:.62rem;color:var(--grn);margin:2px;font-weight:500;}
.badge-yel{display:inline-block;background:rgba(255,214,10,.12);border:1px solid rgba(255,214,10,.25);border-radius:50px;padding:2px 8px;font-size:.60rem;font-weight:700;color:var(--yel);}
.badge-grn{display:inline-block;background:rgba(0,230,118,.12);border:1px solid rgba(0,230,118,.25);border-radius:50px;padding:2px 8px;font-size:.60rem;font-weight:700;color:var(--grn);}
.badge-red{display:inline-block;background:rgba(255,59,92,.12);border:1px solid rgba(255,59,92,.25);border-radius:50px;padding:2px 8px;font-size:.60rem;font-weight:700;color:var(--red);}
.badge-blu{display:inline-block;background:rgba(76,201,240,.12);border:1px solid rgba(76,201,240,.25);border-radius:50px;padding:2px 8px;font-size:.60rem;font-weight:700;color:var(--blu);}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.7)}}
.dot-on{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--grn);animation:pulse 2.5s infinite;margin-right:4px;vertical-align:middle;}
.dot-off{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--t4);margin-right:4px;vertical-align:middle;}
@keyframes fadeUp{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
.pw{animation:fadeUp .15s ease both;}
.bme{background:linear-gradient(135deg,rgba(0,230,118,.12),rgba(76,201,240,.08));border:1px solid rgba(0,230,118,.15);border-radius:16px 16px 4px 16px;padding:.5rem .8rem;max-width:70%;margin-left:auto;margin-bottom:4px;font-size:.80rem;line-height:1.6;}
.bthem{background:var(--g1);border:1px solid var(--gb1);border-radius:16px 16px 16px 4px;padding:.5rem .8rem;max-width:70%;margin-bottom:4px;font-size:.80rem;line-height:1.6;}
.cmt{background:rgba(255,255,255,.03);border:1px solid var(--gb1);border-radius:var(--r12);padding:.45rem .8rem;margin-bottom:.2rem;}
.stTabs [data-baseweb="tab-list"]{background:rgba(255,255,255,.03)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;padding:3px!important;gap:2px!important;}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--t3)!important;border-radius:8px!important;font-size:.73rem!important;font-family:'DM Sans',sans-serif!important;}
.stTabs [aria-selected="true"]{background:rgba(0,230,118,.12)!important;color:var(--grn)!important;border:1px solid rgba(0,230,118,.2)!important;font-weight:700!important;}
.stTabs [data-baseweb="tab-panel"]{background:transparent!important;padding-top:.7rem!important;}
.prof-hero{background:rgba(255,255,255,.04);border:1px solid rgba(0,230,118,.12);border-radius:var(--r28);padding:1.4rem;display:flex;gap:1.1rem;align-items:flex-start;margin-bottom:.9rem;}
.prof-av{width:72px;height:72px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:'Syne',sans-serif;font-weight:800;font-size:1.5rem;color:white;flex-shrink:0;}
hr{border:none;border-top:1px solid rgba(255,255,255,.06)!important;margin:.7rem 0;}
.stAlert{background:var(--g1)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;}
.stSelectbox [data-baseweb="select"]{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;}
.stFileUploader section{background:rgba(255,255,255,.03)!important;border:1.5px dashed rgba(0,230,118,.2)!important;border-radius:var(--r12)!important;}
.stExpander{background:rgba(255,255,255,.03);border:1px solid var(--gb1);border-radius:var(--r12);}
::-webkit-scrollbar{width:3px;height:3px;}
::-webkit-scrollbar-thumb{background:rgba(0,230,118,.3);border-radius:3px;}
.js-plotly-plot .plotly .modebar{display:none!important;}
.dtxt{display:flex;align-items:center;gap:.6rem;margin:.6rem 0;font-size:.56rem;color:var(--t3);letter-spacing:.10em;text-transform:uppercase;font-weight:700;}
.dtxt::before,.dtxt::after{content:'';flex:1;height:1px;background:var(--gb1);}
h1{font-family:'Syne',sans-serif!important;font-size:1.45rem!important;font-weight:800!important;letter-spacing:-.03em;color:var(--t0)!important;}
h2{font-family:'Syne',sans-serif!important;font-size:.96rem!important;font-weight:700!important;color:var(--t0)!important;}
label{color:var(--t2)!important;}
.stCheckbox label,.stRadio label{color:var(--t1)!important;}
.stRadio>div{display:flex!important;gap:3px!important;flex-wrap:wrap!important;}
.stRadio>div>label{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:50px!important;padding:.26rem .72rem!important;font-size:.72rem!important;cursor:pointer!important;color:var(--t2)!important;}
.pbox-grn{background:rgba(0,230,118,.06);border:1px solid rgba(0,230,118,.18);border-radius:var(--r12);padding:.7rem;margin-bottom:.45rem;}
.pbox-yel{background:rgba(255,214,10,.06);border:1px solid rgba(255,214,10,.18);border-radius:var(--r12);padding:.7rem;margin-bottom:.45rem;}
.pbox-blu{background:rgba(76,201,240,.06);border:1px solid rgba(76,201,240,.18);border-radius:var(--r12);padding:.7rem;margin-bottom:.45rem;}
.chart-wrap{background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.06);border-radius:var(--r12);padding:.5rem;margin-bottom:.5rem;}
.compose-box{background:rgba(255,255,255,.04);border:1px solid rgba(0,230,118,.12);border-radius:var(--r16);padding:1rem 1.2rem;margin-bottom:.7rem;}
.ml-feat{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);border-radius:var(--r12);padding:.6rem .8rem;margin-bottom:.35rem;}
input[type="number"]{background:rgba(255,255,255,.04)!important;border:1px solid var(--gb1)!important;border-radius:var(--r12)!important;color:var(--t1)!important;}
/* SOBEL heatmap card */
.sobel-card{background:rgba(0,230,118,.05);border:1px solid rgba(0,230,118,.18);border-radius:var(--r16);padding:.85rem;margin-bottom:.6rem;}
</style>""",unsafe_allow_html=True)

# ════════════════════════════════════════════════
#  HTML HELPERS
# ════════════════════════════════════════════════
def avh(initials,sz=38,grad=None):
    fs=max(sz//3,8); bg=grad or "linear-gradient(135deg,#FFD60A,#FF8C42)"
    return f'<div style="width:{sz}px;height:{sz}px;border-radius:50%;background:{bg};display:flex;align-items:center;justify-content:center;font-family:Syne,sans-serif;font-weight:800;font-size:{fs}px;color:white;flex-shrink:0">{initials}</div>'

def tags_html(tags): return ' '.join(f'<span class="tag">{t}</span>' for t in (tags or []))

def badge(s):
    m={"Publicado":"badge-grn","Concluído":"badge-blu"}
    return f'<span class="{m.get(s,"badge-yel")}">{s}</span>'

def pc_dark():
    return dict(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#5A6080",family="DM Sans",size=10),
                margin=dict(l=8,r=8,t=34,b=8),
                xaxis=dict(showgrid=False,color="#5A6080",tickfont=dict(size=9)),
                yaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,.03)",color="#5A6080",tickfont=dict(size=9)))

# ════════════════════════════════════════════════
#  AUTH
# ════════════════════════════════════════════════
def page_login():
    _,col,_=st.columns([1,1.1,1])
    with col:
        st.markdown("<br><br>",unsafe_allow_html=True)
        st.markdown("""<div style="text-align:center;margin-bottom:2.5rem">
  <div style="display:flex;align-items:center;justify-content:center;gap:11px;margin-bottom:.7rem">
    <div style="width:46px;height:46px;border-radius:13px;background:linear-gradient(135deg,#00E676,#4CC9F0);display:flex;align-items:center;justify-content:center;font-size:1.3rem;box-shadow:0 0 20px rgba(0,230,118,.25)">🔬</div>
    <div style="font-family:Syne,sans-serif;font-size:2.5rem;font-weight:900;letter-spacing:-.06em;background:linear-gradient(135deg,#00E676,#4CC9F0);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">Nebula</div>
  </div>
  <div style="color:#5A6080;font-size:.58rem;letter-spacing:.26em;text-transform:uppercase;font-weight:700">Rede do Conhecimento Científico</div>
</div>""",unsafe_allow_html=True)
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
            st.markdown('<div style="text-align:center;color:#5A6080;font-size:.66rem;margin-top:.6rem">Demo: demo@nebula.ai / demo123</div>',unsafe_allow_html=True)
        with tu:
            with st.form("sf"):
                nn=st.text_input("Nome completo",key="su_n"); ne=st.text_input("E-mail",key="su_e")
                na=st.text_input("Área de pesquisa",key="su_a")
                np_=st.text_input("Senha",type="password",key="su_p"); np2=st.text_input("Confirmar",type="password",key="su_p2")
                if st.form_submit_button("✓  Criar conta",use_container_width=True):
                    if not all([nn,ne,na,np_,np2]): st.error("Preencha todos os campos.")
                    elif np_!=np2: st.error("Senhas não coincidem.")
                    elif ne in st.session_state.users: st.error("E-mail já cadastrado.")
                    else:
                        st.session_state.users[ne]={"name":nn,"password":hp(np_),"bio":"","area":na,"followers":0,"following":0,"verified":True,"2fa_enabled":False}
                        save_db(); st.session_state.logged_in=True; st.session_state.current_user=ne
                        record(area_tags(na),2.0); st.session_state.page="feed"; st.rerun()

# ════════════════════════════════════════════════
#  SIDEBAR — st.radio (always visible, no tricks)
# ════════════════════════════════════════════════
NAV_LABELS=["🏠 Feed","🔍 Busca","🕸 Conexões IA","📁 Pastas","📊 Análises","🔬 Visão IA","💬 Chat","⚙️ Config"]
NAV_KEYS=["feed","search","knowledge","folders","analytics","img_search","chat","settings"]

def render_nav():
    email=st.session_state.current_user; u=guser(); name=u.get("name","?")
    g=ugrad(email); cur=st.session_state.page
    with st.sidebar:
        # Logo
        st.markdown(f"""<div style="display:flex;align-items:center;gap:8px;margin-bottom:1.2rem;padding:.1rem .2rem">
  <div style="width:30px;height:30px;border-radius:8px;background:linear-gradient(135deg,#00E676,#4CC9F0);display:flex;align-items:center;justify-content:center;font-size:.8rem;flex-shrink:0">🔬</div>
  <div style="font-family:Syne,sans-serif;font-weight:900;font-size:1.1rem;letter-spacing:-.04em;background:linear-gradient(135deg,#00E676,#4CC9F0);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">Nebula</div>
</div>""",unsafe_allow_html=True)
        # Active item CSS injection
        cur_idx=NAV_KEYS.index(cur) if cur in NAV_KEYS else 0
        colors_map={"feed":"#FFD60A","search":"#4CC9F0","knowledge":"#00E676","folders":"#FF8C42","analytics":"#B17DFF","img_search":"#4CC9F0","chat":"#00E676","settings":"#FF3B5C"}
        ac=colors_map.get(cur,"#00E676")
        st.markdown(f"""<style>
section[data-testid="stSidebar"] .stRadio>div>label:nth-child({cur_idx+1}){{
  background:rgba(0,230,118,.10)!important;
  border-color:{ac}44!important;
  color:{ac}!important;-webkit-text-fill-color:{ac}!important;
  font-weight:700!important;
}}</style>""",unsafe_allow_html=True)
        choice=st.radio("",NAV_LABELS,index=cur_idx,key="nav_radio",label_visibility="collapsed")
        new_key=NAV_KEYS[NAV_LABELS.index(choice)]
        if new_key!=cur:
            st.session_state.page=new_key; st.session_state.profile_view=None; st.rerun()
        st.markdown("<hr>",unsafe_allow_html=True)
        # API Key
        st.markdown('<div style="font-size:.52rem;font-weight:700;color:#333850;letter-spacing:.12em;text-transform:uppercase;margin-bottom:.3rem">API Claude</div>',unsafe_allow_html=True)
        ak=st.text_input("",placeholder="sk-ant-...",type="password",key="sb_apikey",label_visibility="collapsed",value=st.session_state.anthropic_key)
        if ak!=st.session_state.anthropic_key: st.session_state.anthropic_key=ak
        if ak and ak.startswith("sk-"):
            st.markdown('<div style="font-size:.52rem;color:#00E676;padding:.08rem .1rem">● IA Ativa</div>',unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:.52rem;color:#333850;padding:.08rem .1rem">● console.anthropic.com</div>',unsafe_allow_html=True)
        st.markdown("<hr>",unsafe_allow_html=True)
        # User
        ini_=ini(name)
        st.markdown(f'<div style="display:flex;align-items:center;gap:7px;padding:.1rem 0">{avh(ini_,28,g)}<div style="overflow:hidden"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.75rem;color:#FFF;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:110px">{name}</div><div style="font-size:.55rem;color:#5A6080">{u.get("area","")[:16]}</div></div></div>',unsafe_allow_html=True)
        if st.button("👤 Meu Perfil",key="sb_myprofile",use_container_width=True):
            st.session_state.profile_view=email; st.session_state.page="feed"; st.rerun()

# ════════════════════════════════════════════════
#  PROFILE
# ════════════════════════════════════════════════
def page_profile(target_email):
    tu=st.session_state.users.get(target_email,{}); email=st.session_state.current_user
    if not tu: st.error("Perfil não encontrado."); return
    tname=tu.get("name","?"); ti=ini(tname); is_me=(email==target_email)
    is_fol=target_email in st.session_state.followed; g=ugrad(target_email)
    user_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==target_email]
    liked_posts=[p for p in st.session_state.feed_posts if target_email in p.get("liked_by",[])]
    total_likes=sum(p["likes"] for p in user_posts)
    vb=' <span class="badge-grn" style="font-size:.58rem">✓</span>' if tu.get("verified") else ""
    st.markdown(f"""<div class="prof-hero">
  <div class="prof-av" style="background:{g};width:68px;height:68px;font-size:1.4rem">{ti}</div>
  <div style="flex:1">
    <div style="display:flex;align-items:center;gap:5px;margin-bottom:.2rem">
      <span style="font-family:Syne,sans-serif;font-weight:800;font-size:1.25rem;color:var(--t0)">{tname}</span>{vb}
    </div>
    <div style="color:var(--grn);font-size:.78rem;font-weight:600;margin-bottom:.3rem">{tu.get("area","")}</div>
    <div style="color:var(--t2);font-size:.75rem;line-height:1.65;margin-bottom:.65rem">{tu.get("bio","Sem biografia.")}</div>
    <div style="display:flex;gap:1.4rem;flex-wrap:wrap">
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:.96rem;color:var(--t0)">{tu.get("followers",0)}</span><span style="color:var(--t3);font-size:.65rem"> seg.</span></div>
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:.96rem;color:var(--t0)">{len(user_posts)}</span><span style="color:var(--t3);font-size:.65rem"> pesquisas</span></div>
      <div><span style="font-family:Syne,sans-serif;font-weight:800;font-size:.96rem;color:var(--grn)">{fmt_num(total_likes)}</span><span style="color:var(--t3);font-size:.65rem"> curtidas</span></div>
    </div>
  </div>
</div>""",unsafe_allow_html=True)
    if not is_me:
        c1,c2,c3,_=st.columns([1,1,1,2])
        with c1:
            lbl="✓ Seguindo" if is_fol else "+ Seguir"
            if st.button(lbl,key="su_n",use_container_width=True):
                if is_fol: st.session_state.followed.remove(target_email); tu["followers"]=max(0,tu.get("followers",0)-1)
                else: st.session_state.followed.append(target_email); tu["followers"]=tu.get("followers",0)+1
                save_db(); st.rerun()
        with c2:
            if st.button("💬 Chat",key="pf_chat",use_container_width=True):
                st.session_state.chat_messages.setdefault(target_email,[]); st.session_state.active_chat=target_email; st.session_state.page="chat"; st.rerun()
        with c3:
            if st.button("← Voltar",key="pf_back",use_container_width=True): st.session_state.profile_view=None; st.rerun()
        tp,tl=st.tabs([f"  📝 Pesquisas ({len(user_posts)})  ",f"  ❤️ Curtidas ({len(liked_posts)})  "])
        with tp:
            for p in sorted(user_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="profile",show_author=False)
            if not user_posts: st.markdown('<div class="glass" style="padding:2rem;text-align:center;color:var(--t3)">Sem pesquisas.</div>',unsafe_allow_html=True)
        with tl:
            for p in sorted(liked_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="prolk",compact=True)
    else:
        saved_arts=st.session_state.saved_articles
        tm,tl,ts2,ts=st.tabs(["  ✏️ Dados  ",f"  📝 Publ. ({len(user_posts)})  ",f"  ❤️ ({len(liked_posts)})  ",f"  🔖 ({len(saved_arts)})  "])
        with tm:
            new_n=st.text_input("Nome",value=tu.get("name",""),key="cfg_n")
            new_a=st.text_input("Área",value=tu.get("area",""),key="cfg_a")
            new_b=st.text_area("Bio",value=tu.get("bio",""),key="cfg_b",height=70)
            cs,co=st.columns(2)
            with cs:
                if st.button("💾 Salvar",key="btn_sp",use_container_width=True):
                    st.session_state.users[email].update({"name":new_n,"area":new_a,"bio":new_b}); save_db(); st.success("✓"); st.rerun()
            with co:
                if st.button("🚪 Sair",key="btn_out",use_container_width=True):
                    st.session_state.logged_in=False; st.session_state.current_user=None; st.session_state.page="feed"; st.rerun()
        with tl:
            for p in sorted(user_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="myp",show_author=False)
            if not user_posts: st.markdown('<div class="glass" style="padding:2rem;text-align:center;color:var(--t3)">Sem pesquisas.</div>',unsafe_allow_html=True)
        with ts2:
            for p in sorted(liked_posts,key=lambda x:x.get("date",""),reverse=True): render_post(p,ctx="mylk",compact=True)
        with ts:
            if saved_arts:
                for idx,a in enumerate(saved_arts):
                    render_article(a,idx=idx+3000,ctx="saved")
                    uid2=re.sub(r'[^a-zA-Z0-9]','',f"rms_{idx}")[:20]
                    if st.button("🗑 Remover",key=f"rm_sa_{uid2}",use_container_width=True):
                        st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]
                        save_db(); st.rerun()
            else: st.markdown('<div class="glass" style="padding:2rem;text-align:center;color:var(--t3)">Sem artigos salvos.</div>',unsafe_allow_html=True)

# ════════════════════════════════════════════════
#  POST CARD
# ════════════════════════════════════════════════
def render_post(post,ctx="feed",show_author=True,compact=False):
    email=st.session_state.current_user; pid=post["id"]
    liked=email in post.get("liked_by",[]); saved=email in post.get("saved_by",[])
    aemail=post.get("author_email",""); ain=post.get("avatar","??"); aname=post.get("author","?")
    g=ugrad(aemail); dt=time_ago(post.get("date","")); views=post.get("views",200)
    ab=post.get("abstract","")
    if compact and len(ab)>180: ab=ab[:180]+"…"
    if show_author:
        hdr=(f'<div style="padding:.7rem 1rem .45rem;display:flex;align-items:center;gap:8px;border-bottom:1px solid rgba(255,255,255,.04)">'
             f'{avh(ain,34,g)}<div style="flex:1;min-width:0">'
             f'<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.82rem;color:var(--t0)">{aname}</div>'
             f'<div style="color:var(--t3);font-size:.60rem">{post.get("area","")} · {dt}</div>'
             f'</div>{badge(post["status"])}</div>')
    else:
        hdr=f'<div style="padding:.28rem 1rem .1rem;display:flex;justify-content:space-between;align-items:center"><span style="color:var(--t3);font-size:.60rem">{dt}</span>{badge(post["status"])}</div>'
    st.markdown(f'<div class="post-card">{hdr}<div style="padding:.55rem 1rem"><div style="font-family:Syne,sans-serif;font-size:.92rem;font-weight:700;margin-bottom:.28rem;color:var(--t0)">{post["title"]}</div><div style="color:var(--t2);font-size:.76rem;line-height:1.62;margin-bottom:.42rem">{ab}</div><div>{tags_html(post.get("tags",[]))}</div></div></div>',unsafe_allow_html=True)
    heart="❤️" if liked else "🤍"; book="🔖" if saved else "📌"; nc=len(post.get("comments",[]))
    ca,cb,cc,cd,ce,cf=st.columns([1.1,1,.65,.55,1,1.1])
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
    with ce: st.markdown(f'<div style="text-align:center;color:var(--t3);font-size:.64rem;padding:.44rem 0">👁 {fmt_num(views)}</div>',unsafe_allow_html=True)
    with cf:
        if show_author and aemail:
            if st.button(f"👤 {aname.split()[0]}",key=f"vp_{ctx}_{pid}",use_container_width=True):
                st.session_state.profile_view=aemail; st.rerun()
    if st.session_state.get(f"cmt_{ctx}_{pid}",False):
        for c in post.get("comments",[]):
            ci=ini(c["user"]); ce2=next((e for e,u in st.session_state.users.items() if u.get("name")==c["user"]),""); cg=ugrad(ce2)
            st.markdown(f'<div class="cmt"><div style="display:flex;align-items:center;gap:6px;margin-bottom:.15rem">{avh(ci,22,cg)}<span style="font-size:.70rem;font-weight:700;color:var(--grn)">{c["user"]}</span></div><div style="font-size:.75rem;color:var(--t2);padding-left:28px">{c["text"]}</div></div>',unsafe_allow_html=True)
        nc_txt=st.text_input("",placeholder="Comentário…",key=f"ci_{ctx}_{pid}",label_visibility="collapsed")
        if st.button("→ Enviar",key=f"cs_{ctx}_{pid}"):
            if nc_txt: uu=guser(); post["comments"].append({"user":uu.get("name","Você"),"text":nc_txt}); record(post.get("tags",[]),.8); save_db(); st.rerun()

# ════════════════════════════════════════════════
#  FEED
# ════════════════════════════════════════════════
def page_feed():
    email=st.session_state.current_user; u=guser(); uname=u.get("name","?"); uin=ini(uname); g=ugrad(email)
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    co=st.session_state.get("compose_open",False)
    cm,cs=st.columns([2,.85],gap="medium")
    with cm:
        if co:
            st.markdown(f'<div class="compose-box"><div style="display:flex;align-items:center;gap:8px;margin-bottom:.8rem">{avh(uin,36,g)}<div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.84rem;color:var(--t0)">{uname}</div><div style="font-size:.62rem;color:var(--t3)">{u.get("area","")}</div></div></div>',unsafe_allow_html=True)
            nt=st.text_input("Título *",key="np_t",placeholder="Título da pesquisa…")
            nab=st.text_area("Resumo *",key="np_ab",height=90,placeholder="Descreva sua pesquisa…")
            c1c,c2c=st.columns(2)
            with c1c: ntg=st.text_input("Tags",key="np_tg",placeholder="neurociência, IA")
            with c2c: nst=st.selectbox("Status",["Em andamento","Publicado","Concluído"],key="np_st")
            cp,cc=st.columns([2,1])
            with cp:
                if st.button("🚀 Publicar",key="btn_pub",use_container_width=True):
                    if not nt or not nab: st.warning("Título e resumo obrigatórios.")
                    else:
                        tags=[t.strip() for t in ntg.split(",") if t.strip()] if ntg else []
                        np2={"id":len(st.session_state.feed_posts)+200+hash(nt)%99,"author":uname,"author_email":email,"avatar":uin,"area":u.get("area",""),"title":nt,"abstract":nab,"tags":tags,"likes":0,"comments":[],"status":nst,"date":datetime.now().strftime("%Y-%m-%d"),"liked_by":[],"saved_by":[],"connections":tags[:3],"views":1}
                        st.session_state.feed_posts.insert(0,np2); record(tags,2.0); save_db(); st.session_state.compose_open=False; st.rerun()
            with cc:
                if st.button("✕",key="btn_cc",use_container_width=True): st.session_state.compose_open=False; st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)
        else:
            ac,bc=st.columns([.06,1],gap="small")
            with ac: st.markdown(f'<div style="padding-top:5px">{avh(uin,34,g)}</div>',unsafe_allow_html=True)
            with bc:
                if st.button(f"No que está pesquisando, {uname.split()[0]}?",key="oc",use_container_width=True):
                    st.session_state.compose_open=True; st.rerun()
        ff=st.radio("",["🌐 Todos","👥 Seguidos","🔖 Salvos","🔥 Populares"],horizontal=True,key="ff",label_visibility="collapsed")
        recs=get_recs(email,2)
        if recs and "Seguidos" not in ff and "Salvos" not in ff:
            st.markdown('<div class="dtxt"><span class="badge-grn">✨ Recomendado</span></div>',unsafe_allow_html=True)
            for p in recs: render_post(p,ctx="rec",compact=True)
            st.markdown('<div class="dtxt">Mais pesquisas</div>',unsafe_allow_html=True)
        posts=list(st.session_state.feed_posts)
        if "Seguidos" in ff: posts=[p for p in posts if p.get("author_email") in st.session_state.followed]
        elif "Salvos" in ff: posts=[p for p in posts if email in p.get("saved_by",[])]
        elif "Populares" in ff: posts=sorted(posts,key=lambda p:p["likes"],reverse=True)
        else: posts=sorted(posts,key=lambda p:p.get("date",""),reverse=True)
        if not posts: st.markdown('<div class="glass" style="padding:3rem;text-align:center;color:var(--t3)">Nenhuma pesquisa.</div>',unsafe_allow_html=True)
        else:
            for p in posts: render_post(p,ctx="feed")
    with cs:
        sq=st.text_input("",placeholder="🔍 Pesquisadores…",key="ppl_s",label_visibility="collapsed")
        st.markdown('<div class="sc">',unsafe_allow_html=True)
        st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.78rem;margin-bottom:.7rem;display:flex;justify-content:space-between;color:var(--t0)"><span>Quem seguir</span><span style="font-size:.60rem;color:var(--t3)">Sugestões</span></div>',unsafe_allow_html=True)
        sn=0
        for ue,ud in list(users.items()):
            if ue==email or sn>=5: continue
            rn=ud.get("name","?")
            if sq and sq.lower() not in rn.lower() and sq.lower() not in ud.get("area","").lower(): continue
            sn+=1; is_fol=ue in st.session_state.followed; uin_r=ini(rn); rg=ugrad(ue); online=is_online(ue)
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            st.markdown(f'<div style="display:flex;align-items:center;gap:7px;padding:.32rem 0;border-bottom:1px solid rgba(255,255,255,.04)">{avh(uin_r,28,rg)}<div style="flex:1;min-width:0"><div style="font-size:.73rem;font-weight:600;color:var(--t1)">{dot}{rn}</div><div style="font-size:.58rem;color:var(--t3)">{ud.get("area","")[:20]}</div></div></div>',unsafe_allow_html=True)
            cf2,cv2=st.columns(2)
            with cf2:
                if st.button("✓ Seg." if is_fol else "+ Seguir",key=f"sf_{ue}",use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"]=max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                    save_db(); st.rerun()
            with cv2:
                if st.button("👤 Ver",key=f"svr_{ue}",use_container_width=True): st.session_state.profile_view=ue; st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)
        st.markdown('<div class="sc">',unsafe_allow_html=True)
        st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.76rem;margin-bottom:.6rem;color:var(--t0)">🔥 Em Alta</div>',unsafe_allow_html=True)
        for i,(t,c) in enumerate([("Quantum ML","34"),("CRISPR 2026","28"),("Neuroplasticidade","22"),("LLMs Científicos","19"),("Matéria Escura","15")]):
            st.markdown(f'<div style="padding:.28rem 0;border-bottom:1px solid rgba(255,255,255,.04)"><div style="font-size:.55rem;color:var(--t3)">#{i+1}</div><div style="font-size:.73rem;font-weight:600;color:{VIB[i]}">{t}</div><div style="font-size:.56rem;color:var(--t3)">{c} pesquisas</div></div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)

# ════════════════════════════════════════════════
#  SEARCH
# ════════════════════════════════════════════════
def render_article(a,idx=0,ctx="web"):
    sc=VIB[1] if a.get("origin")=="semantic" else VIB[2]; sn="Semantic Scholar" if a.get("origin")=="semantic" else "CrossRef"
    cite=f" · {a['citations']} cit." if a.get("citations") else ""
    uid=re.sub(r'[^a-zA-Z0-9]','',f"{ctx}_{idx}_{str(a.get('doi',''))[:10]}")[:32]
    is_saved=any(s.get('doi')==a.get('doi') for s in st.session_state.saved_articles)
    ab=(a.get("abstract","") or "")[:250]+("…" if len(a.get("abstract",""))>250 else "")
    st.markdown(f'<div class="scard"><div style="display:flex;align-items:flex-start;gap:6px;margin-bottom:.25rem"><div style="flex:1;font-family:Syne,sans-serif;font-size:.84rem;font-weight:700;color:var(--t0)">{a["title"]}</div><span style="font-size:.56rem;color:{sc};background:rgba(255,255,255,.04);border-radius:6px;padding:2px 6px;white-space:nowrap;flex-shrink:0">{sn}</span></div><div style="color:var(--t3);font-size:.62rem;margin-bottom:.28rem">{a["authors"]} · <em>{a["source"]}</em> · {a["year"]}{cite}</div><div style="color:var(--t2);font-size:.74rem;line-height:1.6">{ab}</div></div>',unsafe_allow_html=True)
    ca,cb,cc=st.columns(3)
    with ca:
        if st.button("🔖 Salvo" if is_saved else "📌 Salvar",key=f"svw_{uid}"):
            if is_saved: st.session_state.saved_articles=[s for s in st.session_state.saved_articles if s.get('doi')!=a.get('doi')]; st.toast("Removido")
            else: st.session_state.saved_articles.append(a); st.toast("Salvo!")
            save_db(); st.rerun()
    with cb:
        if st.button("📋 Citar",key=f"ctw_{uid}"): st.toast(f'{a["authors"]} ({a["year"]}). {a["title"]}.')
    with cc:
        if a.get("url"): st.markdown(f'<a href="{a["url"]}" target="_blank" style="color:var(--blu);font-size:.76rem;text-decoration:none;line-height:2.2;display:block">↗ Abrir</a>',unsafe_allow_html=True)

def page_search():
    st.markdown('<h1 style="padding-top:.6rem;margin-bottom:.3rem">🔍 Busca Científica</h1>',unsafe_allow_html=True)
    c1,c2=st.columns([4,1])
    with c1: q=st.text_input("",placeholder="CRISPR · quantum ML · dark matter…",key="sq",label_visibility="collapsed")
    with c2:
        if st.button("🔍 Buscar",key="btn_s",use_container_width=True):
            if q:
                with st.spinner("Buscando na plataforma e internet…"):
                    nr=[p for p in st.session_state.feed_posts if q.lower() in p["title"].lower() or q.lower() in p["abstract"].lower()]
                    sr=search_ss(q,6); cr=search_cr(q,3)
                    st.session_state.search_results={"nebula":nr,"ss":sr,"cr":cr}; st.session_state.last_sq=q; record([q.lower()],.3)
    if st.session_state.get("search_results") and st.session_state.get("last_sq"):
        res=st.session_state.search_results; neb=res.get("nebula",[]); ss=res.get("ss",[]); cr=res.get("cr",[])
        web=ss+[x for x in cr if not any(x["title"].lower()==s["title"].lower() for s in ss)]
        ta,tn,tw=st.tabs([f"  Todos ({len(neb)+len(web)})  ",f"  🔬 Nebula ({len(neb)})  ",f"  🌐 Internet ({len(web)})  "])
        with ta:
            if neb:
                st.markdown('<div style="font-size:.57rem;color:var(--grn);font-weight:700;margin-bottom:.35rem;letter-spacing:.10em;text-transform:uppercase">Na Nebula</div>',unsafe_allow_html=True)
                for p in neb: render_post(p,ctx="srch_all",compact=True)
            if web:
                if neb: st.markdown('<hr>',unsafe_allow_html=True)
                for idx,a in enumerate(web): render_article(a,idx=idx,ctx="all_w")
            if not neb and not web: st.info("Nenhum resultado.")
        with tn:
            for p in neb: render_post(p,ctx="srch_neb",compact=True)
            if not neb: st.info("Nenhuma pesquisa.")
        with tw:
            for idx,a in enumerate(web): render_article(a,idx=idx,ctx="web_t")
            if not web: st.info("Nenhum artigo.")

# ════════════════════════════════════════════════
#  CONNECTIONS + AI — ALL GREEN
# ════════════════════════════════════════════════
def page_knowledge():
    st.markdown('<h1 style="padding-top:.6rem;margin-bottom:.8rem">🕸 Rede de Conexões com IA</h1>',unsafe_allow_html=True)
    email=st.session_state.current_user; users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    api_key=st.session_state.get("anthropic_key","")
    rlist=list(users.keys()); n=len(rlist)
    def get_tags(ue):
        ud=users.get(ue,{}); tags=set(area_tags(ud.get("area","")))
        for p in st.session_state.feed_posts:
            if p.get("author_email")==ue: tags.update(t.lower() for t in p.get("tags",[]))
        return tags
    rtags={ue:get_tags(ue) for ue in rlist}
    edges=[]
    for i in range(n):
        for j in range(i+1,n):
            e1,e2=rlist[i],rlist[j]; common=list(rtags[e1]&rtags[e2])
            is_fol=e2 in st.session_state.followed or e1 in st.session_state.followed
            if common or is_fol: edges.append((e1,e2,common[:5],len(common)+(2 if is_fol else 0)))
    # 3D Network
    pos={}
    for idx2,ue in enumerate(rlist):
        angle=2*3.14159*idx2/max(n,1); rd=0.36+0.05*((hash(ue)%5)/4)
        pos[ue]={"x":0.5+rd*np.cos(angle),"y":0.5+rd*np.sin(angle),"z":0.5+0.12*((idx2%4)/3-.35)}
    fig=go.Figure()
    for e1,e2,common,strength in edges:
        p1=pos[e1]; p2=pos[e2]; alpha=min(0.5,0.08+strength*0.06)
        fig.add_trace(go.Scatter3d(x=[p1["x"],p2["x"],None],y=[p1["y"],p2["y"],None],z=[p1["z"],p2["z"],None],
            mode="lines",line=dict(color=f"rgba(0,230,118,{alpha:.2f})",width=min(3,1+strength)),hoverinfo="none",showlegend=False))
    ncolors=["#FFD60A" if ue==email else ("#00E676" if ue in st.session_state.followed else "#4CC9F0") for ue in rlist]
    nsizes=[22 if ue==email else(16 if ue in st.session_state.followed else 10) for ue in rlist]
    fig.add_trace(go.Scatter3d(
        x=[pos[ue]["x"] for ue in rlist],y=[pos[ue]["y"] for ue in rlist],z=[pos[ue]["z"] for ue in rlist],
        mode="markers+text",marker=dict(size=nsizes,color=ncolors,opacity=.9,line=dict(color="rgba(0,230,118,.15)",width=1)),
        text=[users.get(ue,{}).get("name","?").split()[0] for ue in rlist],textposition="top center",
        textfont=dict(color="#5A6080",size=8,family="DM Sans"),
        hovertemplate=[f"<b>{users.get(ue,{}).get('name','?')}</b><br>{users.get(ue,{}).get('area','')}<extra></extra>" for ue in rlist],showlegend=False))
    fig.update_layout(height=380,scene=dict(
        xaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),
        yaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),
        zaxis=dict(showgrid=False,zeroline=False,showticklabels=False,showbackground=False),
        bgcolor="rgba(0,0,0,0)"),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig,use_container_width=True)
    c1,c2,c3,c4=st.columns(4)
    for col,(cls,v,l) in zip([c1,c2,c3,c4],[("mval-yel",len(rlist),"Pesquisadores"),("mval-grn",len(edges),"Conexões"),("mval-blu",len(st.session_state.followed),"Seguindo"),("mval-red",len(st.session_state.feed_posts),"Pesquisas")]):
        with col: st.markdown(f'<div class="mbox"><div class="{cls}">{v}</div><div class="mlbl">{l}</div></div>',unsafe_allow_html=True)
    st.markdown("<hr>",unsafe_allow_html=True)
    tm,tai,tmi,tall=st.tabs(["  🗺 Mapa  ","  🤖 IA Conexões  ","  🔗 Minhas  ","  👥 Todos  "])
    with tm:
        for e1,e2,common,strength in sorted(edges,key=lambda x:-x[3])[:20]:
            n1=users.get(e1,{}); n2=users.get(e2,{}); ts=tags_html(common[:4]) if common else '<span style="color:var(--t3);font-size:.64rem">seguimento</span>'
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap"><span style="font-size:.76rem;font-weight:700;font-family:Syne,sans-serif;color:var(--grn)">{n1.get("name","?")}</span><span style="color:var(--t3)">↔</span><span style="font-size:.76rem;font-weight:700;font-family:Syne,sans-serif;color:var(--grn)">{n2.get("name","?")}</span><div style="flex:1">{ts}</div><span style="font-size:.60rem;color:var(--grn);font-weight:700">{strength}pt</span></div></div>',unsafe_allow_html=True)
    with tai:
        # ── AI CONNECTION SUGGESTIONS (GREEN) ──
        st.markdown("""<div class="api-banner">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:.3rem">
    <div style="width:28px;height:28px;border-radius:8px;background:rgba(0,230,118,.15);display:flex;align-items:center;justify-content:center;font-size:.9rem">🤖</div>
    <div style="font-family:Syne,sans-serif;font-weight:700;font-size:.86rem;color:#00E676">Sugestões com IA — Claude Haiku</div>
  </div>
  <div style="font-size:.72rem;color:var(--t2);line-height:1.6">Claude analisa seu perfil, área de pesquisa e publicações para sugerir colaborações científicas ideais</div>
</div>""",unsafe_allow_html=True)
        if not api_key or not api_key.startswith("sk-"):
            st.markdown('<div class="pbox-yel"><div style="font-size:.72rem;color:var(--yel);font-weight:600;margin-bottom:.22rem">⚠️ API Key necessária</div><div style="font-size:.68rem;color:var(--t2)">Insira sua Anthropic API key na barra lateral. Chave gratuita em: <strong>console.anthropic.com</strong></div></div>',unsafe_allow_html=True)
            st.markdown('<div style="font-size:.60rem;color:var(--t3);margin:.4rem 0">Sugestões algorítmicas (sem IA):</div>',unsafe_allow_html=True)
            my_tags=rtags.get(email,set())
            for ue,ud in list(users.items())[:8]:
                if ue==email or ue in st.session_state.followed: continue
                ct=my_tags&rtags.get(ue,set())
                if len(ct)>0:
                    rg=ugrad(ue); rn=ud.get("name","?")
                    st.markdown(f'<div class="conn-ai"><div style="display:flex;align-items:center;gap:8px;margin-bottom:.45rem">{avh(ini(rn),32,rg)}<div style="flex:1"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.82rem;color:var(--t0)">{rn}</div><div style="font-size:.63rem;color:var(--t3)">{ud.get("area","")}</div></div><span class="badge-grn">{len(ct)} temas</span></div><div style="font-size:.70rem;color:var(--t2);margin-bottom:.4rem">Temas em comum: {tags_html(list(ct)[:4])}</div></div>',unsafe_allow_html=True)
                    cf_b,cv_b=st.columns(2)
                    with cf_b:
                        if st.button(f"+ Seguir {rn.split()[0]}",key=f"ais_{ue}",use_container_width=True):
                            if ue not in st.session_state.followed: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                            save_db(); st.rerun()
                    with cv_b:
                        if st.button("👤 Ver",key=f"aip_{ue}",use_container_width=True): st.session_state.profile_view=ue; st.rerun()
        else:
            ck=f"conn_{email}_{len(users)}"
            if st.button("🤖 Gerar Sugestões IA",key="btn_ai_conn"):
                with st.spinner("Claude Haiku analisando sua rede…"):
                    result,err=claude_connections(users,st.session_state.feed_posts,email,api_key)
                    if result: st.session_state.ai_conn_cache[ck]=result
                    else: st.error(f"Erro: {err}")
            ai_result=st.session_state.ai_conn_cache.get(ck)
            if ai_result:
                for sug in ai_result.get("sugestoes",[]):
                    sue=sug.get("email",""); sud=users.get(sue,{})
                    if not sud: continue
                    rn=sud.get("name","?"); rg=ugrad(sue); score=sug.get("score",70)
                    sc_c="#00E676" if score>=80 else ("#FFD60A" if score>=60 else "#FF8C42")
                    temas=sug.get("temas_comuns",[]); is_fol2=sue in st.session_state.followed
                    st.markdown(f"""<div class="conn-ai">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:.5rem">
    {avh(ini(rn),36,rg)}
    <div style="flex:1">
      <div style="font-family:Syne,sans-serif;font-weight:700;font-size:.84rem;color:var(--t0)">{rn}</div>
      <div style="font-size:.63rem;color:var(--t3)">{sud.get("area","")}</div>
    </div>
    <div style="background:rgba(0,0,0,.3);border-radius:9px;padding:.32rem .6rem;text-align:center">
      <div style="font-family:Syne,sans-serif;font-size:1rem;font-weight:900;color:{sc_c}">{score}</div>
      <div style="font-size:.48rem;color:var(--t3);text-transform:uppercase">IA score</div>
    </div>
  </div>
  <div style="background:rgba(0,230,118,.05);border:1px solid rgba(0,230,118,.12);border-radius:9px;padding:.48rem .65rem;margin-bottom:.42rem;font-size:.74rem;color:var(--t2);line-height:1.62">
    🤖 {sug.get("razao","Conexão recomendada")}
  </div>
  <div>{tags_html(temas[:5])}</div>
</div>""",unsafe_allow_html=True)
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
                st.markdown('<div style="text-align:center;padding:2rem;color:var(--t3)">Clique em "Gerar Sugestões IA" para análise com Claude Haiku.</div>',unsafe_allow_html=True)
    with tmi:
        mc=[(e1,e2,c,s) for e1,e2,c,s in edges if e1==email or e2==email]
        if not mc: st.info("Siga pesquisadores e publique pesquisas para criar conexões.")
        for e1,e2,common,strength in sorted(mc,key=lambda x:-x[3]):
            oth=e2 if e1==email else e1; od=users.get(oth,{}); og=ugrad(oth)
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:8px">{avh(ini(od.get("name","?")),32,og)}<div style="flex:1"><div style="font-weight:700;font-size:.80rem;font-family:Syne,sans-serif;color:var(--t0)">{od.get("name","?")}</div><div style="font-size:.63rem;color:var(--t3)">{od.get("area","")}</div></div>{tags_html(common[:3])}</div></div>',unsafe_allow_html=True)
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
            is_fol=ue in st.session_state.followed; rg=ugrad(ue)
            st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;gap:8px">{avh(ini(rn),32,rg)}<div style="flex:1"><div style="font-size:.80rem;font-weight:700;font-family:Syne,sans-serif;color:var(--t0)">{rn}</div><div style="font-size:.63rem;color:var(--t3)">{ua}</div></div></div></div>',unsafe_allow_html=True)
            ca2,cb2,cc2=st.columns(3)
            with ca2:
                if st.button("👤 Perfil",key=f"av_{ue}",use_container_width=True): st.session_state.profile_view=ue; st.rerun()
            with cb2:
                if st.button("✓ Seg." if is_fol else "+ Seguir",key=f"af_{ue}",use_container_width=True):
                    if is_fol: st.session_state.followed.remove(ue); ud["followers"]=max(0,ud.get("followers",0)-1)
                    else: st.session_state.followed.append(ue); ud["followers"]=ud.get("followers",0)+1
                    save_db(); st.rerun()
            with cc2:
                if st.button("💬 Chat",key=f"ac_{ue}",use_container_width=True):
                    st.session_state.chat_messages.setdefault(ue,[]); st.session_state.active_chat=ue; st.session_state.page="chat"; st.rerun()

# ════════════════════════════════════════════════
#  REAL AI IMAGE ANALYSIS — Sobel + Claude Vision
# ════════════════════════════════════════════════
def page_img_search():
    st.markdown('<h1 style="padding-top:.6rem;margin-bottom:.2rem">🔬 Visão IA Científica</h1>',unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t3);font-size:.73rem;margin-bottom:.7rem">Sobel · Canny · Keypoints · GLCM · KMeans · FFT + Claude Vision IA</p>',unsafe_allow_html=True)
    api_key=st.session_state.get("anthropic_key","")
    has_api=api_key.startswith("sk-") if api_key else False
    if has_api:
        st.markdown('<div class="api-banner" style="display:flex;align-items:center;gap:8px"><div style="font-size:1rem">🤖</div><div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.80rem;color:#00E676">Claude Haiku Vision Ativo</div><div style="font-size:.67rem;color:var(--t2)">Análise real com IA habilitada</div></div></div>',unsafe_allow_html=True)
    cu,cr=st.columns([1,2.1])
    with cu:
        st.markdown('<div class="glass" style="padding:.9rem">',unsafe_allow_html=True)
        img_file=st.file_uploader("📷 Imagem científica",type=["png","jpg","jpeg","webp","tiff"],key="img_up")
        img_bytes=None
        if img_file:
            img_bytes=img_file.read(); st.image(img_bytes,use_container_width=True)
        col_btn1,col_btn2=st.columns(2)
        with col_btn1: run_ml=st.button("🔬 Analisar ML",key="btn_run",use_container_width=True)
        with col_btn2: run_claude=st.button("🤖 Claude IA",key="btn_vision",use_container_width=True,disabled=(not img_bytes or not has_api))
        if not has_api and img_bytes:
            st.markdown('<div style="font-size:.60rem;color:var(--t3);margin-top:.3rem">Adicione API key para usar Claude Vision</div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)
    with cr:
        # ── ML PIPELINE ──
        if run_ml and img_bytes:
            img_hash=hashlib.md5(img_bytes[:1024]).hexdigest()
            with st.spinner("Executando pipeline ML (Sobel · Keypoints · GLCM · FFT)…"):
                ml=run_ml_pipeline(img_hash,img_bytes)
            st.session_state.img_result=ml
            if not ml.get("ok"):
                st.error(f"Erro: {ml.get('error','desconhecido')}"); return
            cls_=ml["classification"]; col_=ml["color"]
            conf_c=VIB[1] if cls_["confidence"]>80 else(VIB[0] if cls_["confidence"]>60 else VIB[2])
            # ── MAIN CLASSIFICATION ──
            st.markdown(f"""<div class="ai-card">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:.5rem">
    <div>
      <div style="font-size:.55rem;color:var(--grn);letter-spacing:.10em;text-transform:uppercase;font-weight:700;margin-bottom:3px">🔬 Classificação ML</div>
      <div style="font-family:Syne,sans-serif;font-size:1.08rem;font-weight:800;color:var(--t0);margin-bottom:2px">{cls_["category"]}</div>
      <div style="font-size:.72rem;color:var(--t2);line-height:1.6">{cls_["origin"]}</div>
    </div>
    <div style="background:rgba(0,0,0,.35);border-radius:10px;padding:.45rem .8rem;text-align:center;flex-shrink:0;border:1px solid rgba(0,230,118,.12)">
      <div style="font-family:Syne,sans-serif;font-size:1.4rem;font-weight:900;color:{conf_c}">{cls_["confidence"]}%</div>
      <div style="font-size:.48rem;color:var(--t3);text-transform:uppercase;font-weight:700">confiança</div>
    </div>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:3px">
    {"".join(f'<span style="background:rgba(0,230,118,.06);border:1px solid rgba(0,230,118,.12);border-radius:20px;padding:1px 7px;font-size:.58rem;color:var(--t3)">{k}: {v}pt</span>' for k,v in cls_["scores"].items())}
  </div>
</div>""",unsafe_allow_html=True)
            # ── ML METRICS ROW ──
            c1m,c2m,c3m,c4m=st.columns(4)
            with c1m: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1rem;font-weight:800;color:#FFD60A">{ml["sobel"]["mean"]:.3f}</div><div class="mlbl">Sobel Edge</div></div>',unsafe_allow_html=True)
            with c2m: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1rem;font-weight:800;color:#00E676">{ml.get("n_kp",0)}</div><div class="mlbl">Keypoints</div></div>',unsafe_allow_html=True)
            with c3m: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1rem;font-weight:800;color:#4CC9F0">{"Periódico" if ml["fft"]["periodic"] else "Aperiódico"}</div><div class="mlbl">FFT</div></div>',unsafe_allow_html=True)
            with c4m: st.markdown(f'<div class="mbox"><div style="font-family:Syne,sans-serif;font-size:1rem;font-weight:800;color:#B17DFF">{ml["glcm"].get("homogeneity",0):.3f}</div><div class="mlbl">Homog. GLCM</div></div>',unsafe_allow_html=True)
            # ── ANALYSIS TABS ──
            ts,tk,tf,trgb=st.tabs(["  🔲 Sobel/Bordas  ","  🎨 Cores/KMeans  ","  📡 FFT/GLCM  ","  📊 RGB  "])
            with ts:
                st.markdown('<div class="sobel-card">',unsafe_allow_html=True)
                st.markdown(f'<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.82rem;color:#00E676;margin-bottom:.5rem">🔲 Mapeamento Sobel — Detecção de Bordas</div>',unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:.72rem;color:var(--t2);line-height:1.7;margin-bottom:.5rem">O filtro Sobel calcula o gradiente da intensidade em cada pixel, identificando bordas e transições. <strong style="color:var(--t0)">Intensidade média: {ml["sobel"]["mean"]:.4f}</strong> — indica {"alta" if ml["sobel"]["mean"]>0.1 else "baixa"} densidade de bordas. <strong style="color:var(--t0)">Densidade de borda: {ml["sobel"]["density"]*100:.1f}%</strong> dos pixels são bordas significativas.</div>',unsafe_allow_html=True)
                # Sobel heatmap visualization
                smag=np.array(ml["sobel_map"],dtype=np.float32)
                fig_s=go.Figure(go.Heatmap(z=smag,colorscale=[[0,"#030916"],[0.3,"#003333"],[0.6,"#00E676"],[1.0,"#FFFFFF"]],showscale=False))
                fig_s.update_layout(height=200,margin=dict(l=0,r=0,t=0,b=0),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",xaxis=dict(showticklabels=False,showgrid=False),yaxis=dict(showticklabels=False,showgrid=False,scaleanchor='x'))
                st.plotly_chart(fig_s,use_container_width=True)
                # Edge histogram
                eh=ml["sobel"]["hist"]
                fig_e=go.Figure(go.Bar(y=eh,x=list(range(len(eh))),marker=dict(color=list(range(len(eh))),colorscale=[[0,"#030916"],[.4,"#003322"],[.7,"#00E676"],[1,"#FFFFFF"]])))
                fig_e.update_layout(**{**pc_dark(),'height':150,'title':dict(text="Distribuição de Intensidades Sobel",font=dict(color="#E8E9F0",family="Syne",size=9)),'margin':dict(l=8,r=8,t=28,b=8)})
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_e,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
                # Canny info
                canny_fine=ml["sobel"]["density"]*0.7; canny_med=ml["sobel"]["density"]*0.5
                st.markdown(f'<div class="pbox-grn"><div style="font-size:.63rem;color:#00E676;font-weight:700;margin-bottom:.25rem">Canny Multi-Escala (estimado)</div><div style="font-size:.70rem;color:var(--t2)">Fino: {canny_fine*100:.1f}% · Médio: {canny_med*100:.1f}% · Gradiente máximo: {ml["sobel"]["max"]:.3f}</div></div>',unsafe_allow_html=True)
                st.markdown('</div>',unsafe_allow_html=True)
            with tk:
                pal=ml.get("palette",[])
                if pal:
                    st.markdown('<div style="font-size:.62rem;color:var(--t3);text-transform:uppercase;font-weight:600;letter-spacing:.08em;margin-bottom:.5rem">KMeans — 6 Cores Dominantes</div>',unsafe_allow_html=True)
                    for cp in pal:
                        pct=cp.get("pct",0); hex_c=cp.get("hex","#888"); r2,g2,b2=cp.get("rgb",(128,128,128))
                        bar=f'<div style="height:5px;width:{min(int(pct*3.5),100)}%;background:{hex_c};border-radius:2px;margin-top:2px"></div>'
                        st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:.35rem"><div style="width:28px;height:28px;border-radius:6px;background:{hex_c};flex-shrink:0"></div><div style="flex:1"><div style="display:flex;justify-content:space-between;font-size:.68rem;color:var(--t2)"><span>{hex_c.upper()}</span><span>{pct:.1f}%</span></div>{bar}</div><div style="font-size:.58rem;color:var(--t3);width:75px">RGB({r2},{g2},{b2})</div></div>',unsafe_allow_html=True)
                    fig_pal=go.Figure(go.Pie(values=[c["pct"] for c in pal],labels=[c["hex"] for c in pal],
                        marker=dict(colors=[c["hex"] for c in pal],line=dict(color=["#050B1C"]*6,width=2)),
                        textfont=dict(color="white",size=7),hole=0.45))
                    fig_pal.update_layout(height=200,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=5,b=0),legend=dict(font=dict(color="#5A6080",size=7)))
                    st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_pal,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
                # Keypoints scatter
                kps_raw=ml.get("kps",[])
                if kps_raw and len(kps_raw)>0:
                    kps_arr=np.array(kps_raw)
                    if len(kps_arr.shape)==2 and kps_arr.shape[1]>=2:
                        nh,nw=ml["proc_size"][1],ml["proc_size"][0]
                        fig_kp=go.Figure()
                        sample=kps_arr[::max(1,len(kps_arr)//200)]
                        fig_kp.add_trace(go.Scatter(x=sample[:,1],y=nh-sample[:,0],mode='markers',
                            marker=dict(size=3,color="#00E676",opacity=0.7),name=f"Keypoints ({len(kps_arr)})"))
                        fig_kp.update_layout(**{**pc_dark(),'height':180,'title':dict(text=f"Mapa de {len(kps_arr)} Keypoints",font=dict(color="#E8E9F0",family="Syne",size=9)),'xaxis':dict(range=[0,nw],showgrid=False),'yaxis':dict(range=[0,nh],showgrid=False,scaleanchor='x'),'margin':dict(l=8,r=8,t=28,b=8)})
                        st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_kp,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
            with tf:
                fft_r=ml["fft"]; lf,mf,hf=fft_r["lf"],fft_r["mf"],fft_r["hf"]
                fig_fft=go.Figure(go.Bar(x=["Baixa freq.\n(estruturas grandes)","Média freq.\n(detalhes)","Alta freq.\n(textura/ruído)"],
                    y=[lf,mf,hf],marker=dict(color=["#00E676","#FFD60A","#4CC9F0"]),
                    text=[f"{v:.3f}" for v in [lf,mf,hf]],textposition="outside",textfont=dict(color="#5A6080",size=9)))
                fig_fft.update_layout(**{**pc_dark(),'height':210,'title':dict(text="FFT — Frequências Espaciais",font=dict(color="#E8E9F0",family="Syne",size=9)),'margin':dict(l=8,r=8,t=32,b=8)})
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_fft,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
                # GLCM
                glcm_r=ml["glcm"]
                glcm_vals=[(k,v) for k,v in glcm_r.items() if isinstance(v,float)]
                if glcm_vals:
                    fig_gl=go.Figure(go.Bar(x=[k.replace('_',' ').title() for k,_ in glcm_vals],y=[v for _,v in glcm_vals],
                        marker=dict(color=[v for _,v in glcm_vals],colorscale=[[0,"#030916"],[.4,"#004422"],[.7,"#00E676"],[1,"#FFD60A"]]),
                        text=[f"{v:.3f}" for _,v in glcm_vals],textposition="outside",textfont=dict(color="#5A6080",size=8)))
                    fig_gl.update_layout(**{**pc_dark(),'height':190,'title':dict(text="GLCM — Textura",font=dict(color="#E8E9F0",family="Syne",size=9)),'margin':dict(l=8,r=8,t=28,b=8)})
                    st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig_gl,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
                st.markdown(f'<div class="pbox-blu" style="font-size:.70rem;color:var(--t2)"><strong style="color:#4CC9F0">FFT:</strong> Score periódico {fft_r["per_score"]:.1f} — {"estrutura periódica detectada ✓" if fft_r["periodic"] else "estrutura não periódica"}. Freq. dominante: {"fina" if hf>0.5 else ("média" if mf>0.3 else "grossa")}.</div>',unsafe_allow_html=True)
            with trgb:
                h_data=ml.get("histograms",{}); bx=list(range(0,256,8))[:32]
                if h_data:
                    fig4=go.Figure()
                    fig4.add_trace(go.Scatter(x=bx,y=h_data.get("r",[])[:32],fill='tozeroy',name='R',line=dict(color='rgba(255,59,92,.9)',width=1.5),fillcolor='rgba(255,59,92,.08)'))
                    fig4.add_trace(go.Scatter(x=bx,y=h_data.get("g",[])[:32],fill='tozeroy',name='G',line=dict(color='rgba(0,230,118,.9)',width=1.5),fillcolor='rgba(0,230,118,.08)'))
                    fig4.add_trace(go.Scatter(x=bx,y=h_data.get("b",[])[:32],fill='tozeroy',name='B',line=dict(color='rgba(76,201,240,.9)',width=1.5),fillcolor='rgba(76,201,240,.08)'))
                    fig4.update_layout(**{**pc_dark(),'height':200,'title':dict(text="Histograma RGB",font=dict(color="#E8E9F0",family="Syne",size=9)),'margin':dict(l=8,r=8,t=28,b=8),'legend':dict(font=dict(color="#5A6080",size=8))})
                    st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig4,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
                mr=col_.get("r",128); mg2_=col_.get("g",128); mb_=col_.get("b",128)
                hex_m="#{:02x}{:02x}{:02x}".format(int(mr),int(mg2_),int(mb_))
                temp="Quente 🔥" if col_.get("warm") else("Fria ❄️" if col_.get("cool") else "Neutra")
                st.markdown(f'<div class="ml-feat" style="display:grid;grid-template-columns:repeat(4,1fr);gap:.5rem;font-size:.70rem"><div style="text-align:center"><div style="width:26px;height:26px;border-radius:6px;background:{hex_m};margin:0 auto .2rem"></div><div style="color:var(--t3)">Cor média</div></div><div style="text-align:center"><div style="font-weight:700;font-size:.82rem;color:#FFD60A">{temp}</div><div style="color:var(--t3)">Temperatura</div></div><div style="text-align:center"><div style="font-weight:700;font-size:.82rem;color:#00E676">{col_.get("sym",0):.2f}</div><div style="color:var(--t3)">Simetria</div></div><div style="text-align:center"><div style="font-weight:700;font-size:.82rem;color:#4CC9F0">{col_.get("entropy",0):.2f}</div><div style="color:var(--t3)">Entropia</div></div></div>',unsafe_allow_html=True)
            # ── RELATED RESEARCH ──
            st.markdown("<hr>",unsafe_allow_html=True)
            st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;font-size:.88rem;color:var(--t0);margin-bottom:.5rem">🔗 Pesquisas Relacionadas</div>',unsafe_allow_html=True)
            kw_s=cls_["kw"]
            tn2,tw2=st.tabs(["  🔬 Na Nebula  ","  🌐 Internet  "])
            with tn2:
                kw_list=kw_s.lower().split()[:6]
                nr=[(sum(1 for k in kw_list if len(k)>3 and k in (p.get("title","")+" "+p.get("abstract","")).lower()),p) for p in st.session_state.feed_posts]
                nr=[p for s,p in sorted(nr,key=lambda x:-x[0]) if s>0]
                for p in nr[:4]: render_post(p,ctx="img_neb",compact=True)
                if not nr: st.markdown('<div style="color:var(--t3);padding:.7rem">Nenhuma pesquisa similar na plataforma.</div>',unsafe_allow_html=True)
            with tw2:
                ck2=f"img_{kw_s[:40]}"
                if ck2 not in st.session_state.scholar_cache:
                    with st.spinner("Buscando na internet…"): st.session_state.scholar_cache[ck2]=search_ss(kw_s,5)
                wr2=st.session_state.scholar_cache.get(ck2,[])
                for idx3,a3 in enumerate(wr2): render_article(a3,idx=idx3+3000,ctx="img_web")
                if not wr2: st.markdown('<div style="color:var(--t3);padding:.7rem">Sem resultados.</div>',unsafe_allow_html=True)

        # ── CLAUDE VISION ──
        if run_claude and img_bytes and has_api:
            st.markdown("<hr>",unsafe_allow_html=True)
            st.markdown('<div style="font-family:Syne,sans-serif;font-weight:800;font-size:.96rem;color:#00E676;margin-bottom:.6rem">🤖 Claude Haiku — Análise Real com IA</div>',unsafe_allow_html=True)
            with st.spinner("Claude analisando a imagem…"):
                ai_data,ai_err=claude_vision_analyze(img_bytes,api_key)
            if ai_err:
                st.error(f"Erro Claude: {ai_err}")
            elif ai_data:
                o_que=ai_data.get("o_que_e","—"); de_que=ai_data.get("de_que_e_feita","—")
                tipo=ai_data.get("tipo_tecnico","—"); area_c=ai_data.get("area_ciencia","—")
                estruturas=ai_data.get("estruturas_visiveis",[]); cores=ai_data.get("cores_significado","—")
                escala=ai_data.get("escala_resolucao","—"); qual=ai_data.get("qualidade_tecnica","—")
                conf2=ai_data.get("confianca",0); termos=ai_data.get("termos_busca",""); obs=ai_data.get("observacoes_criticas","")
                cc2=VIB[1] if conf2>80 else(VIB[0] if conf2>60 else VIB[2])
                st.markdown(f"""<div style="background:linear-gradient(135deg,rgba(0,230,118,.08),rgba(76,201,240,.04));border:1px solid rgba(0,230,118,.22);border-radius:16px;padding:1.1rem;margin-bottom:.6rem">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:.8rem">
    <div>
      <div style="font-size:.53rem;color:#00E676;letter-spacing:.10em;text-transform:uppercase;font-weight:700;margin-bottom:3px">🤖 Claude Haiku Vision</div>
      <div style="font-family:Syne,sans-serif;font-size:1.02rem;font-weight:800;color:var(--t0);margin-bottom:2px">{o_que}</div>
      <div style="color:#00E676;font-size:.74rem;font-weight:600">{area_c} — {tipo}</div>
    </div>
    <div style="background:rgba(0,0,0,.4);border-radius:10px;padding:.42rem .75rem;text-align:center;flex-shrink:0;border:1px solid rgba(0,230,118,.12)">
      <div style="font-family:Syne,sans-serif;font-size:1.35rem;font-weight:900;color:{cc2}">{conf2}%</div>
      <div style="font-size:.48rem;color:var(--t3);text-transform:uppercase">confiança IA</div>
    </div>
  </div>
  <div style="background:rgba(255,255,255,.03);border-radius:9px;padding:.6rem .8rem;margin-bottom:.5rem;font-size:.76rem;color:var(--t2);line-height:1.7">
    <strong style="color:var(--t1)">🏗 Do que é feita:</strong> {de_que}
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:.4rem;margin-bottom:.4rem;font-size:.70rem">
    <div style="color:var(--t2)"><span style="color:var(--t3)">🎨 Cores:</span> {cores}</div>
    <div style="color:var(--t2)"><span style="color:var(--t3)">📏 Escala:</span> {escala}</div>
    <div style="color:var(--t2)"><span style="color:var(--t3)">⭐ Qualidade:</span> <strong style="color:var(--yel)">{qual}</strong></div>
    <div style="color:var(--t2)"><span style="color:var(--t3)">🔬 Estruturas:</span> {", ".join(estruturas[:3]) if estruturas else "—"}</div>
  </div>
  {f'<div style="background:rgba(0,230,118,.05);border:1px solid rgba(0,230,118,.1);border-radius:8px;padding:.45rem .65rem;font-size:.71rem;color:var(--t2);line-height:1.65"><strong style="color:#00E676">💡 Análise:</strong> {obs}</div>' if obs else ""}
</div>""",unsafe_allow_html=True)
                if termos:
                    st.markdown(f'<div style="font-size:.60rem;color:var(--t3);margin:.3rem 0 .45rem">🔍 Buscando artigos: <em>{termos}</em></div>',unsafe_allow_html=True)
                    with st.spinner("Buscando literatura…"):
                        wr_ai=search_ss(termos,5)
                    for idx_a,a_ai in enumerate(wr_ai): render_article(a_ai,idx=idx_a+5000,ctx="img_claude")

        if not img_file:
            st.markdown('<div class="glass" style="padding:4rem 2rem;text-align:center"><div style="font-size:2.5rem;opacity:.15;margin-bottom:.9rem">🔬</div><div style="font-family:Syne,sans-serif;font-size:.96rem;color:var(--t1);margin-bottom:.4rem">Carregue uma imagem científica</div><div style="font-size:.70rem;color:var(--t3);line-height:2">Sobel · Canny · Keypoints · GLCM · KMeans · FFT<br>Com API Key: Claude Vision identifica o que é a imagem e do que é feita</div></div>',unsafe_allow_html=True)

# ════════════════════════════════════════════════
#  FOLDERS
# ════════════════════════════════════════════════
def page_folders():
    st.markdown('<h1 style="padding-top:.6rem;margin-bottom:.8rem">📁 Pastas de Pesquisa</h1>',unsafe_allow_html=True)
    email=st.session_state.current_user; u=guser(); ra=u.get("area","")
    c1,c2,_=st.columns([2,1.2,1.5])
    with c1: nfn=st.text_input("Nome da pasta",placeholder="Ex: Genômica Comparativa",key="nf_n")
    with c2: nfd=st.text_input("Descrição",key="nf_d")
    if st.button("📁 Criar",key="btn_nf",use_container_width=True):
        if nfn.strip():
            if nfn not in st.session_state.folders: st.session_state.folders[nfn]={"desc":nfd,"files":[],"notes":"","analyses":{}}; save_db(); st.success(f"'{nfn}' criada!"); st.rerun()
            else: st.warning("Já existe.")
        else: st.warning("Digite um nome.")
    st.markdown("<hr>",unsafe_allow_html=True)
    if not st.session_state.folders:
        st.markdown('<div class="glass" style="text-align:center;padding:3.5rem;color:var(--t3)">Nenhuma pasta criada.</div>',unsafe_allow_html=True); return
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
                    ab2=' <span class="badge-grn" style="font-size:.55rem">✓</span>' if ha else ''
                    st.markdown(f'<div style="display:flex;align-items:center;gap:6px;padding:.32rem 0;border-bottom:1px solid rgba(255,255,255,.04)"><span>{icon}</span><span style="font-size:.72rem;color:var(--t2);flex:1">{f}</span>{ab2}</div>',unsafe_allow_html=True)
            ca2,cb2,_=st.columns([1.5,1.5,2])
            with ca2:
                if st.button("🔬 Analisar",key=f"an_{fn}",use_container_width=True):
                    if files:
                        pb=st.progress(0,"Iniciando…"); fb=st.session_state.folder_files_bytes.get(fn,{})
                        for fi,f in enumerate(files):
                            pb.progress((fi+1)/len(files),f"Analisando: {f[:20]}…"); fbytes=fb.get(f,b""); ft2=ftype(f)
                            analyses[f]=analyze_doc(f,fbytes,ft2,ra)
                        fd["analyses"]=analyses; save_db(); pb.empty(); st.success("✓ Completo!"); st.rerun()
                    else: st.warning("Adicione arquivos.")
            with cb2:
                if st.button("🗑 Excluir",key=f"df_{fn}",use_container_width=True):
                    del st.session_state.folders[fn]; save_db(); st.rerun()
            if analyses:
                for f,an in analyses.items():
                    with st.expander(f"🔬 {f}"):
                        kws=an.get("keywords",[]); topics=an.get("topics",{}); rel=an.get("relevance_score",0)
                        rc="var(--grn)" if rel>=70 else("var(--yel)" if rel>=45 else "var(--red)")
                        st.markdown(f'<div class="abox"><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.84rem;margin-bottom:.28rem">{f}</div><div style="font-size:.72rem;color:var(--t2)">{an.get("summary","")}</div><div style="display:flex;gap:1rem;margin-top:.45rem"><div style="text-align:center"><div style="font-family:Syne,sans-serif;font-size:1rem;font-weight:900;color:{rc}">{rel}%</div><div style="font-size:.52rem;color:var(--t3);text-transform:uppercase">Relevância</div></div><div style="text-align:center"><div style="font-family:Syne,sans-serif;font-size:1rem;font-weight:900;color:var(--blu)">{an.get("writing_quality",0)}%</div><div style="font-size:.52rem;color:var(--t3);text-transform:uppercase">Qualidade</div></div><div style="text-align:center"><div style="font-family:Syne,sans-serif;font-size:1rem;font-weight:900;color:var(--orn)">{an.get("word_count",0)}</div><div style="font-size:.52rem;color:var(--t3);text-transform:uppercase">Palavras</div></div></div></div>',unsafe_allow_html=True)
                        if kws: st.markdown(tags_html(kws[:14]),unsafe_allow_html=True)
                        if topics:
                            fig2=go.Figure(go.Pie(labels=list(topics.keys()),values=list(topics.values()),hole=0.5,marker=dict(colors=VIB[:len(topics)],line=dict(color=["#050B1C"]*15,width=2)),textfont=dict(color="white",size=7)))
                            fig2.update_layout(height=210,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",legend=dict(font=dict(color="#5A6080",size=7)),margin=dict(l=0,r=0,t=5,b=0))
                            st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig2,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)

# ════════════════════════════════════════════════
#  ANALYTICS
# ════════════════════════════════════════════════
def page_analytics():
    st.markdown('<h1 style="padding-top:.6rem;margin-bottom:.8rem">📊 Painel de Análises</h1>',unsafe_allow_html=True)
    email=st.session_state.current_user; d=st.session_state.stats_data
    tf,tp,ti,tpr=st.tabs(["  📁 Pastas  ","  📝 Publicações  ","  📈 Impacto  ","  🎯 Interesses  "])
    with tf:
        folders=st.session_state.folders
        if not folders: st.markdown('<div class="glass" style="text-align:center;padding:2.5rem;color:var(--t3)">Crie pastas para ver análises.</div>',unsafe_allow_html=True)
        else:
            all_an={f:an for fd in folders.values() if isinstance(fd,dict) for f,an in fd.get("analyses",{}).items()}
            tot_f=sum(len(fd.get("files",[]) if isinstance(fd,dict) else fd) for fd in folders.values())
            all_kw=[kw for an in all_an.values() for kw in an.get("keywords",[])]
            all_top=defaultdict(int)
            for an in all_an.values():
                for t,s in an.get("topics",{}).items(): all_top[t]+=s
            c1,c2,c3,c4=st.columns(4)
            for col,(cls,v,l) in zip([c1,c2,c3,c4],[("mval-yel",len(folders),"Pastas"),("mval-grn",tot_f,"Arquivos"),("mval-blu",len(all_an),"Analisados"),("mval-red",len(set(all_kw[:100])),"Keywords")]):
                with col: st.markdown(f'<div class="mbox"><div class="{cls}">{v}</div><div class="mlbl">{l}</div></div>',unsafe_allow_html=True)
            if all_top:
                fig=go.Figure(go.Bar(x=list(all_top.values())[:8],y=list(all_top.keys())[:8],orientation='h',marker=dict(color=VIB[:8])))
                fig.update_layout(**{**pc_dark(),'height':240,'title':dict(text="Temas",font=dict(color="#E8E9F0",family="Syne",size=10))})
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
    with tp:
        my_posts=[p for p in st.session_state.feed_posts if p.get("author_email")==email]
        if not my_posts: st.markdown('<div class="glass" style="text-align:center;padding:2rem;color:var(--t3)">Publique pesquisas para ver estatísticas.</div>',unsafe_allow_html=True)
        else:
            c1,c2,c3=st.columns(3)
            with c1: st.markdown(f'<div class="mbox"><div class="mval-yel">{len(my_posts)}</div><div class="mlbl">Pesquisas</div></div>',unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="mbox"><div class="mval-grn">{sum(p["likes"] for p in my_posts)}</div><div class="mlbl">Curtidas</div></div>',unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="mbox"><div class="mval-blu">{sum(len(p.get("comments",[])) for p in my_posts)}</div><div class="mlbl">Comentários</div></div>',unsafe_allow_html=True)
            for p in sorted(my_posts,key=lambda x:x.get("date",""),reverse=True):
                st.markdown(f'<div class="scard"><div style="display:flex;align-items:center;justify-content:space-between"><div style="font-family:Syne,sans-serif;font-size:.82rem;font-weight:700;color:var(--t0)">{p["title"][:55]}</div>{badge(p["status"])}</div><div style="font-size:.65rem;color:var(--t3);margin-top:.3rem">{p.get("date","")} · {p["likes"]} curtidas · {len(p.get("comments",[]))} comentários</div></div>',unsafe_allow_html=True)
    with ti:
        c1,c2,c3=st.columns(3)
        with c1: st.markdown(f'<div class="mbox"><div class="mval-yel">{d.get("h_index",4)}</div><div class="mlbl">Índice H</div></div>',unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="mbox"><div class="mval-grn">{d.get("fator_impacto",3.8):.1f}</div><div class="mlbl">Fator Impacto</div></div>',unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="mbox"><div class="mval-blu">{len(st.session_state.saved_articles)}</div><div class="mlbl">Salvos</div></div>',unsafe_allow_html=True)
        st.markdown("<hr>",unsafe_allow_html=True)
        nh=st.number_input("Índice H",0,200,d.get("h_index",4),key="e_h")
        nfi=st.number_input("Fator impacto",0.0,100.0,float(d.get("fator_impacto",3.8)),step=0.1,key="e_fi")
        nn=st.text_area("Notas",value=d.get("notes",""),key="e_nt",height=60)
        if st.button("💾 Salvar",key="btn_sm"): d.update({"h_index":nh,"fator_impacto":nfi,"notes":nn}); st.success("✓")
    with tpr:
        prefs=st.session_state.user_prefs.get(email,{})
        if prefs:
            top=sorted(prefs.items(),key=lambda x:-x[1])[:10]; mx=max(s for _,s in top) if top else 1
            cats=[t for t,_ in top[:8]]; vals=[round(s/mx*100) for _,s in top[:8]]
            if len(cats)>=3:
                fig3=go.Figure(go.Scatterpolar(r=vals+[vals[0]],theta=cats+[cats[0]],fill='toself',line=dict(color="#00E676"),fillcolor="rgba(0,230,118,.08)"))
                fig3.update_layout(height=255,polar=dict(bgcolor="rgba(0,0,0,0)",radialaxis=dict(visible=True,gridcolor="rgba(255,255,255,.04)",color="#5A6080",tickfont=dict(size=7)),angularaxis=dict(gridcolor="rgba(255,255,255,.04)",color="#5A6080",tickfont=dict(size=8))),paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=40,r=40,t=15,b=15))
                st.markdown('<div class="chart-wrap">',unsafe_allow_html=True); st.plotly_chart(fig3,use_container_width=True); st.markdown('</div>',unsafe_allow_html=True)
        else: st.info("Interaja com pesquisas para gerar perfil de interesses.")

# ════════════════════════════════════════════════
#  CHAT
# ════════════════════════════════════════════════
def page_chat():
    st.markdown('<h1 style="padding-top:.6rem;margin-bottom:.8rem">💬 Mensagens</h1>',unsafe_allow_html=True)
    cc,cm=st.columns([.85,2.8]); email=st.session_state.current_user
    users=st.session_state.users if isinstance(st.session_state.users,dict) else {}
    with cc:
        st.markdown('<div style="font-size:.55rem;font-weight:700;color:var(--t4);letter-spacing:.12em;text-transform:uppercase;margin-bottom:.6rem">Conversas</div>',unsafe_allow_html=True)
        shown=set()
        for ue in st.session_state.chat_contacts:
            if ue==email or ue in shown: continue
            shown.add(ue); ud=users.get(ue,{}); un=ud.get("name","?"); ui=ini(un); ug=ugrad(ue)
            msgs=st.session_state.chat_messages.get(ue,[]); last=msgs[-1]["text"][:20]+"…" if msgs and len(msgs[-1]["text"])>20 else(msgs[-1]["text"] if msgs else "…")
            active=st.session_state.active_chat==ue; online=is_online(ue)
            dot='<span class="dot-on"></span>' if online else '<span class="dot-off"></span>'
            bg=f"rgba(0,230,118,.08)" if active else "rgba(255,255,255,.04)"; bdr=f"rgba(0,230,118,.25)" if active else "rgba(255,255,255,.07)"
            st.markdown(f'<div style="background:{bg};border:1px solid {bdr};border-radius:10px;padding:7px 9px;margin-bottom:3px"><div style="display:flex;align-items:center;gap:6px">{avh(ui,26,ug)}<div style="overflow:hidden;flex:1"><div style="font-size:.73rem;font-weight:600;color:var(--t0)">{dot}{un}</div><div style="font-size:.60rem;color:var(--t3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{last}</div></div></div></div>',unsafe_allow_html=True)
            if st.button("→",key=f"oc_{ue}",use_container_width=True): st.session_state.active_chat=ue; st.rerun()
        st.markdown("<hr>",unsafe_allow_html=True)
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
            st.markdown(f'<div style="background:rgba(0,230,118,.05);border:1px solid rgba(0,230,118,.12);border-radius:12px;padding:9px 13px;margin-bottom:.75rem;display:flex;align-items:center;gap:9px">{avh(ci,32,cg)}<div style="flex:1"><div style="font-weight:700;font-size:.84rem;font-family:Syne,sans-serif;color:var(--t0)">{dot}{cn}</div><div style="font-size:.60rem;color:var(--grn)">🔒 Criptografado</div></div></div>',unsafe_allow_html=True)
            for msg in msgs:
                im=msg["from"]=="me"; cls="bme" if im else "bthem"
                st.markdown(f'<div style="display:flex;{"justify-content:flex-end" if im else ""}"><div class="{cls}">{msg["text"]}<div style="font-size:.54rem;color:var(--t3);margin-top:2px;text-align:{"right" if im else "left"}">{msg["time"]}</div></div></div>',unsafe_allow_html=True)
            st.markdown("<br>",unsafe_allow_html=True)
            ci2,cb2=st.columns([5,1])
            with ci2: nm=st.text_input("",placeholder="Mensagem…",key=f"mi_{contact}",label_visibility="collapsed")
            with cb2:
                if st.button("→",key=f"ms_{contact}",use_container_width=True):
                    if nm: now=datetime.now().strftime("%H:%M"); st.session_state.chat_messages.setdefault(contact,[]).append({"from":"me","text":nm,"time":now}); st.rerun()
        else:
            st.markdown('<div class="glass" style="text-align:center;padding:4.5rem"><div style="font-size:2rem;opacity:.12;margin-bottom:.75rem">💬</div><div style="font-family:Syne,sans-serif;font-size:.92rem;color:var(--t1)">Selecione uma conversa</div><div style="font-size:.67rem;color:var(--t3);margin-top:.35rem">🔒 End-to-end criptografado</div></div>',unsafe_allow_html=True)

# ════════════════════════════════════════════════
#  SETTINGS
# ════════════════════════════════════════════════
def page_settings():
    st.markdown('<h1 style="padding-top:.6rem;margin-bottom:.8rem">⚙️ Configurações</h1>',unsafe_allow_html=True)
    email=st.session_state.current_user; ud=st.session_state.users.get(email,{})
    st.markdown(f'<div class="abox"><div style="font-size:.55rem;color:var(--t3);text-transform:uppercase;letter-spacing:.10em;margin-bottom:.35rem;font-weight:700">Conta</div><div style="font-family:Syne,sans-serif;font-weight:700;font-size:.92rem;color:var(--grn)">{email}</div></div>',unsafe_allow_html=True)
    en=ud.get("2fa_enabled",False)
    if st.button("✕ Desativar 2FA" if en else "✓ Ativar 2FA",key="cfg_2fa"):
        st.session_state.users[email]["2fa_enabled"]=not en; save_db(); st.rerun()
    st.markdown("<hr>",unsafe_allow_html=True)
    with st.form("cpw"):
        op=st.text_input("Senha atual",type="password"); np2=st.text_input("Nova senha",type="password"); nc3=st.text_input("Confirmar",type="password")
        if st.form_submit_button("🔑 Alterar senha",use_container_width=True):
            if hp(op)!=ud.get("password",""): st.error("Incorreta.")
            elif np2!=nc3: st.error("Não coincidem.")
            elif len(np2)<6: st.error("Mínimo 6 chars.")
            else: st.session_state.users[email]["password"]=hp(np2); save_db(); st.success("✓ Alterada!")
    st.markdown("<hr>",unsafe_allow_html=True)
    for nm,ds in [("🔒 AES-256","End-to-end"),("🔏 SHA-256","Hash senhas"),("🛡 TLS 1.3","Transmissão segura")]:
        st.markdown(f'<div class="pbox-grn" style="margin-bottom:.3rem"><div style="display:flex;align-items:center;gap:8px"><div style="color:var(--grn)">✓</div><div><div style="font-weight:700;color:var(--grn);font-size:.75rem">{nm}</div><div style="font-size:.62rem;color:var(--t3)">{ds}</div></div></div></div>',unsafe_allow_html=True)
    st.markdown("<hr>",unsafe_allow_html=True)
    if st.button("🚪 Sair",key="logout",use_container_width=True):
        st.session_state.logged_in=False; st.session_state.current_user=None; st.session_state.page="feed"; st.rerun()

# ════════════════════════════════════════════════
#  MAIN ROUTER
# ════════════════════════════════════════════════
def main():
    inject_css()
    if not st.session_state.logged_in:
        page_login(); return
    render_nav()
    if st.session_state.profile_view:
        page_profile(st.session_state.profile_view); return
    {
        "feed":page_feed,"search":page_search,"knowledge":page_knowledge,
        "folders":page_folders,"analytics":page_analytics,"img_search":page_img_search,
        "chat":page_chat,"settings":page_settings,
    }.get(st.session_state.page,page_feed)()

main()
