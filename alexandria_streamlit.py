import streamlit as st
import hashlib
import random
import string
import time
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import json
import base64
from io import BytesIO

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="ResearchNet",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
#  GLOBAL CSS — Dark Navy + Black + Liquid Glass
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Syne:wght@400;700;800&display=swap');

:root {
  --bg-deep:    #020818;
  --bg-dark:    #050d1f;
  --bg-card:    rgba(8, 20, 50, 0.85);
  --blue-900:   #0a1628;
  --blue-800:   #0d1f3c;
  --blue-700:   #0f2952;
  --blue-600:   #1a3a6b;
  --blue-400:   #2d6be4;
  --blue-300:   #4d8ef0;
  --blue-200:   #7cb3ff;
  --accent:     #3b7cf4;
  --accent2:    #00c6ff;
  --text-prime: #e8f0ff;
  --text-sec:   #8aa4cc;
  --text-muted: #4a6080;
  --border:     rgba(45, 107, 228, 0.2);
  --glass-bg:   rgba(13, 31, 60, 0.6);
  --glass-bdr:  rgba(77, 142, 240, 0.25);
  --danger:     #ff4757;
  --success:    #2ed573;
}

*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp {
  background: var(--bg-deep) !important;
  color: var(--text-prime) !important;
  font-family: 'Space Grotesk', sans-serif !important;
}

/* Animated mesh background */
.stApp::before {
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 60% at 20% 10%, rgba(29,78,216,0.12) 0%, transparent 60%),
    radial-gradient(ellipse 60% 80% at 80% 90%, rgba(0,198,255,0.07) 0%, transparent 60%),
    radial-gradient(ellipse 40% 40% at 60% 40%, rgba(59,124,244,0.05) 0%, transparent 50%);
  pointer-events: none;
  z-index: 0;
}

/* Sidebar */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, var(--blue-900) 0%, var(--bg-deep) 100%) !important;
  border-right: 1px solid var(--border) !important;
  padding-top: 1rem !important;
}
section[data-testid="stSidebar"] * { color: var(--text-prime) !important; }

/* Headers */
h1, h2, h3, h4 {
  font-family: 'Syne', sans-serif !important;
  color: var(--text-prime) !important;
  letter-spacing: -0.02em;
}

/* Inputs */
.stTextInput input,
.stTextArea textarea,
.stSelectbox select,
.stMultiSelect [data-baseweb="select"] {
  background: var(--blue-800) !important;
  border: 1px solid var(--glass-bdr) !important;
  border-radius: 12px !important;
  color: var(--text-prime) !important;
  font-family: 'Space Grotesk', sans-serif !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px rgba(59,124,244,0.2) !important;
}

/* Liquid Glass Button */
.stButton > button {
  background: linear-gradient(135deg,
    rgba(59,124,244,0.35) 0%,
    rgba(0,198,255,0.18) 50%,
    rgba(59,124,244,0.25) 100%) !important;
  backdrop-filter: blur(20px) saturate(180%) !important;
  -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
  border: 1px solid rgba(124,179,255,0.35) !important;
  border-radius: 16px !important;
  color: var(--text-prime) !important;
  font-family: 'Space Grotesk', sans-serif !important;
  font-weight: 600 !important;
  font-size: 0.9rem !important;
  padding: 0.55rem 1.4rem !important;
  transition: all 0.3s cubic-bezier(0.4,0,0.2,1) !important;
  position: relative !important;
  overflow: hidden !important;
  letter-spacing: 0.02em !important;
  box-shadow:
    0 4px 24px rgba(59,124,244,0.2),
    inset 0 1px 0 rgba(255,255,255,0.12),
    inset 0 -1px 0 rgba(0,0,0,0.2) !important;
}
.stButton > button::before {
  content: '';
  position: absolute;
  top: 0; left: -100%;
  width: 100%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent);
  transition: left 0.5s ease !important;
}
.stButton > button:hover::before { left: 100%; }
.stButton > button:hover {
  background: linear-gradient(135deg,
    rgba(59,124,244,0.55) 0%,
    rgba(0,198,255,0.3) 50%,
    rgba(59,124,244,0.45) 100%) !important;
  border-color: rgba(124,179,255,0.6) !important;
  box-shadow:
    0 8px 32px rgba(59,124,244,0.35),
    0 0 0 1px rgba(124,179,255,0.2),
    inset 0 1px 0 rgba(255,255,255,0.18) !important;
  transform: translateY(-1px) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* Cards */
.glass-card {
  background: var(--glass-bg);
  backdrop-filter: blur(16px) saturate(160%);
  -webkit-backdrop-filter: blur(16px) saturate(160%);
  border: 1px solid var(--glass-bdr);
  border-radius: 20px;
  padding: 1.5rem;
  margin-bottom: 1rem;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.glass-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 48px rgba(0,0,0,0.5), 0 0 0 1px rgba(77,142,240,0.2);
}

/* Avatar circle */
.avatar {
  width: 42px; height: 42px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--blue-600), var(--accent));
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 1rem; color: white;
  border: 2px solid var(--glass-bdr);
  flex-shrink: 0;
}

/* Tag pill */
.tag {
  display: inline-block;
  background: rgba(59,124,244,0.15);
  border: 1px solid rgba(59,124,244,0.3);
  border-radius: 20px;
  padding: 2px 10px;
  font-size: 0.72rem;
  color: var(--blue-200);
  margin: 2px;
  font-weight: 500;
}

/* Metrics */
.metric-box {
  background: var(--glass-bg);
  border: 1px solid var(--glass-bdr);
  border-radius: 16px;
  padding: 1.2rem;
  text-align: center;
}
.metric-value {
  font-family: 'Syne', sans-serif;
  font-size: 2rem;
  font-weight: 800;
  background: linear-gradient(135deg, var(--blue-300), var(--accent2));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.metric-label { font-size: 0.78rem; color: var(--text-sec); margin-top: 4px; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg-deep); }
::-webkit-scrollbar-thumb { background: var(--blue-600); border-radius: 3px; }

/* Divider */
hr { border-color: var(--border) !important; }

/* Logo text */
.logo-text {
  font-family: 'Syne', sans-serif;
  font-size: 1.6rem;
  font-weight: 800;
  background: linear-gradient(135deg, #7cb3ff, #00c6ff);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.03em;
}

/* Notification dot */
.notif-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--accent); display: inline-block; margin-left: 6px;
}

/* Chat bubble */
.chat-bubble-me {
  background: linear-gradient(135deg, rgba(59,124,244,0.4), rgba(0,198,255,0.2));
  border: 1px solid rgba(77,142,240,0.3);
  border-radius: 18px 18px 4px 18px;
  padding: 0.8rem 1.1rem;
  margin: 0.4rem 0;
  max-width: 75%;
  margin-left: auto;
  font-size: 0.88rem;
}
.chat-bubble-other {
  background: var(--glass-bg);
  border: 1px solid var(--glass-bdr);
  border-radius: 18px 18px 18px 4px;
  padding: 0.8rem 1.1rem;
  margin: 0.4rem 0;
  max-width: 75%;
  font-size: 0.88rem;
}

/* Folder card */
.folder-card {
  background: var(--glass-bg);
  border: 1px solid var(--glass-bdr);
  border-radius: 16px;
  padding: 1.2rem;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: center;
}
.folder-card:hover {
  border-color: var(--accent);
  background: rgba(59,124,244,0.12);
  transform: scale(1.02);
}

/* Search input */
.search-wrap {
  position: relative;
  margin-bottom: 1.5rem;
}

/* Badges */
.badge-online {
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--success); display: inline-block; margin-right: 6px;
}
.badge-offline {
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--text-muted); display: inline-block; margin-right: 6px;
}

/* Selectbox */
.stSelectbox [data-baseweb="select"] {
  background: var(--blue-800) !important;
  border-radius: 12px !important;
  border: 1px solid var(--glass-bdr) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  background: var(--blue-900) !important;
  border-radius: 12px !important;
  padding: 4px !important;
  gap: 4px !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  color: var(--text-sec) !important;
  border-radius: 10px !important;
  font-family: 'Space Grotesk', sans-serif !important;
  font-weight: 500 !important;
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, rgba(59,124,244,0.4), rgba(0,198,255,0.2)) !important;
  color: var(--text-prime) !important;
  border: 1px solid rgba(77,142,240,0.3) !important;
}
.stTabs [data-baseweb="tab-panel"] {
  background: transparent !important;
  padding: 1rem 0 !important;
}

/* Radio */
.stRadio label { color: var(--text-prime) !important; }
.stCheckbox label { color: var(--text-prime) !important; }

/* Progress */
.stProgress > div > div {
  background: linear-gradient(90deg, var(--accent), var(--accent2)) !important;
  border-radius: 4px !important;
}

/* Info / warning / success boxes */
.stAlert {
  background: var(--glass-bg) !important;
  border-radius: 12px !important;
  border: 1px solid var(--glass-bdr) !important;
  color: var(--text-prime) !important;
}

/* Expander */
.stExpander {
  background: var(--glass-bg) !important;
  border: 1px solid var(--glass-bdr) !important;
  border-radius: 16px !important;
}
.stExpander summary { color: var(--text-prime) !important; }

/* File uploader */
.stFileUploader {
  background: var(--glass-bg) !important;
  border: 1px dashed var(--glass-bdr) !important;
  border-radius: 16px !important;
}

/* Slider */
.stSlider [data-baseweb="slider"] .rc-slider-track {
  background: var(--accent) !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SESSION STATE INITIALIZATION
# ─────────────────────────────────────────────
def init_state():
    defaults = {
        "logged_in": False,
        "current_user": None,
        "page": "login",
        "users": {
            "demo@researchnet.com": {
                "name": "Ana Pesquisadora",
                "password": hash_pw("demo123"),
                "photo": None,
                "bio": "Pesquisadora em IA e Ciências Cognitivas",
                "area": "Inteligência Artificial",
                "followers": 128,
                "following": 47,
                "2fa_enabled": False,
                "phone": "",
            }
        },
        "pending_2fa": None,
        "2fa_code": None,
        "2fa_email": None,
        "feed_posts": [
            {
                "id": 1,
                "author": "Carlos Mendez",
                "avatar": "CM",
                "area": "Neurociência",
                "title": "Efeitos da Privação de Sono na Plasticidade Sináptica",
                "abstract": "Este estudo investigou como períodos de privação de sono de 24h afetam a densidade de espinhas dendríticas em ratos Wistar, mostrando redução de 34% na plasticidade hipocampal.",
                "tags": ["neurociência", "sono", "memória"],
                "likes": 47,
                "comments": [
                    {"user": "Maria Silva", "text": "Excelente metodologia! Já vi resultados similares em humanos."},
                    {"user": "João Lima", "text": "Quais foram os critérios de exclusão?"}
                ],
                "status": "Em andamento",
                "date": "2026-02-10",
                "liked_by": [],
                "connections": ["sono", "memória", "hipocampo"],
            },
            {
                "id": 2,
                "author": "Luana Freitas",
                "avatar": "LF",
                "area": "Biomedicina",
                "title": "CRISPR-Cas9 no Tratamento de Distrofias Musculares Raras",
                "abstract": "Desenvolvemos um vetor AAV9 modificado para entrega precisa de edições CRISPR no gene DMD, com eficiência de 78% em modelos murinos mdx.",
                "tags": ["CRISPR", "gene terapia", "músculo"],
                "likes": 93,
                "comments": [
                    {"user": "Ana Pesquisadora", "text": "Fascinante! Quais são os próximos passos para trials humanos?"}
                ],
                "status": "Publicado",
                "date": "2026-01-28",
                "liked_by": [],
                "connections": ["edição genética", "distrofia", "AAV9"],
            },
            {
                "id": 3,
                "author": "Rafael Souza",
                "avatar": "RS",
                "area": "Ciência da Computação",
                "title": "Redes Neurais Quântico-Clássicas para Otimização Combinatória",
                "abstract": "Propomos uma arquitetura híbrida variacional que combina qubits supercondutores com camadas densas clássicas para resolver instâncias do TSP com 40% menos iterações.",
                "tags": ["quantum ML", "otimização", "TSP"],
                "likes": 201,
                "comments": [],
                "status": "Em andamento",
                "date": "2026-02-15",
                "liked_by": [],
                "connections": ["computação quântica", "machine learning", "otimização"],
            },
        ],
        "folders": {
            "📁 IA & Machine Learning": ["artigo_gpt4.pdf", "redes_conv.pdf"],
            "📁 Bioinformática": ["genomica_2025.pdf"],
            "📁 Favoritos": [],
        },
        "chat_contacts": [
            {"name": "Carlos Mendez", "avatar": "CM", "online": True, "last": "Ótimo, vou revisar!"},
            {"name": "Luana Freitas", "avatar": "LF", "online": False, "last": "Podemos colaborar no próximo semestre."},
            {"name": "Rafael Souza", "avatar": "RS", "online": True, "last": "Compartilhei o repositório."},
        ],
        "chat_messages": {
            "Carlos Mendez": [
                {"from": "Carlos Mendez", "text": "Oi! Vi seu comentário na minha pesquisa.", "time": "09:14"},
                {"from": "me", "text": "Sim! Achei muito interessante o método que você usou.", "time": "09:16"},
                {"from": "Carlos Mendez", "text": "Ótimo, vou revisar!", "time": "09:17"},
            ],
            "Luana Freitas": [
                {"from": "Luana Freitas", "text": "Podemos colaborar no próximo semestre.", "time": "ontem"},
            ],
            "Rafael Souza": [
                {"from": "Rafael Souza", "text": "Compartilhei o repositório.", "time": "08:30"},
            ],
        },
        "active_chat": None,
        "knowledge_nodes": [
            {"id": "IA", "connections": ["Machine Learning", "Otimização", "Redes Neurais"]},
            {"id": "Neurociência", "connections": ["Memória", "Sono", "Plasticidade"]},
            {"id": "Genômica", "connections": ["CRISPR", "AAV9", "Edição Genética"]},
            {"id": "Computação Quântica", "connections": ["Otimização", "Machine Learning"]},
        ],
        "search_results": [],
        "followed_researchers": ["Carlos Mendez", "Luana Freitas"],
        "stats_data": {
            "views": [12, 34, 28, 67, 89, 110, 95, 134, 160, 178, 201, 230],
            "citations": [0, 1, 1, 2, 3, 4, 4, 6, 7, 8, 10, 12],
            "months": ["Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez", "Jan", "Fev"],
        },
        "notifications": [
            "Carlos Mendez curtiu sua pesquisa",
            "Nova conexão de conhecimento: IA ↔ Computação Quântica",
            "Luana Freitas comentou em um artigo que você segue",
        ],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def generate_code() -> str:
    return ''.join(random.choices(string.digits, k=6))

def get_user():
    return st.session_state.users.get(st.session_state.current_user, {})

init_state()

# ─────────────────────────────────────────────
#  HELPER RENDER FUNCTIONS
# ─────────────────────────────────────────────
def render_logo():
    st.markdown('<div class="logo-text">🔬 ResearchNet</div>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--text-muted);font-size:0.78rem;margin:0 0 1.5rem">A rede do conhecimento científico</p>', unsafe_allow_html=True)

def glass_card(content_html: str):
    st.markdown(f'<div class="glass-card">{content_html}</div>', unsafe_allow_html=True)

def avatar_html(initials: str, size: int = 42):
    return f'<div style="width:{size}px;height:{size}px;border-radius:50%;background:linear-gradient(135deg,#1a3a6b,#2d6be4);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:{size//3}px;color:white;border:2px solid rgba(77,142,240,0.3);flex-shrink:0;">{initials}</div>'

def status_badge(status: str):
    color = "#2ed573" if status == "Publicado" else "#ffa502"
    return f'<span style="background:rgba({",".join(str(int(c*255)) for c in px.colors.hex_to_rgb(color))},0.15);border:1px solid {color};border-radius:20px;padding:2px 10px;font-size:0.72rem;color:{color};font-weight:600;">{status}</span>'

def tag_html(tags):
    return " ".join(f'<span class="tag">{t}</span>' for t in tags)

# ─────────────────────────────────────────────
#  PAGES
# ─────────────────────────────────────────────

# ── LOGIN / CADASTRO ──────────────────────────
def page_login():
    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        st.markdown("<br><br>", unsafe_allow_html=True)
        render_logo()
        st.markdown('<h2 style="margin-bottom:0.3rem;">Bem-vindo de volta</h2>', unsafe_allow_html=True)
        st.markdown('<p style="color:var(--text-sec);margin-bottom:2rem;font-size:0.9rem;">Entre na sua conta para continuar pesquisando</p>', unsafe_allow_html=True)

        tab_login, tab_cadastro = st.tabs(["  Entrar  ", "  Criar conta  "])

        with tab_login:
            email = st.text_input("E-mail", placeholder="seu@email.com", key="login_email")
            pw    = st.text_input("Senha", type="password", placeholder="••••••••", key="login_pw")
            if st.button("Entrar →", use_container_width=True, key="btn_login"):
                if email in st.session_state.users:
                    user = st.session_state.users[email]
                    if user["password"] == hash_pw(pw):
                        if user.get("2fa_enabled"):
                            code = generate_code()
                            st.session_state["2fa_code"]    = code
                            st.session_state["2fa_email"]   = email
                            st.session_state["pending_2fa"] = True
                            st.session_state.page = "2fa"
                            st.rerun()
                        else:
                            st.session_state.logged_in    = True
                            st.session_state.current_user = email
                            st.session_state.page = "feed"
                            st.rerun()
                    else:
                        st.error("Senha incorreta.")
                else:
                    st.error("E-mail não encontrado.")

        with tab_cadastro:
            n_name  = st.text_input("Nome completo", placeholder="Dr. Maria Silva", key="reg_name")
            n_email = st.text_input("E-mail", placeholder="seu@email.com", key="reg_email")
            n_area  = st.text_input("Área de pesquisa", placeholder="Bioinformática, IA, etc.", key="reg_area")
            n_pw    = st.text_input("Senha", type="password", placeholder="Mínimo 6 caracteres", key="reg_pw")
            n_pw2   = st.text_input("Confirmar senha", type="password", placeholder="••••••••", key="reg_pw2")
            if st.button("Criar conta →", use_container_width=True, key="btn_register"):
                if not all([n_name, n_email, n_area, n_pw, n_pw2]):
                    st.error("Preencha todos os campos.")
                elif n_pw != n_pw2:
                    st.error("Senhas não coincidem.")
                elif len(n_pw) < 6:
                    st.error("Senha muito curta (mínimo 6 caracteres).")
                elif n_email in st.session_state.users:
                    st.error("E-mail já cadastrado.")
                else:
                    st.session_state.users[n_email] = {
                        "name": n_name,
                        "password": hash_pw(n_pw),
                        "photo": None,
                        "bio": "",
                        "area": n_area,
                        "followers": 0,
                        "following": 0,
                        "2fa_enabled": False,
                        "phone": "",
                    }
                    st.success("Conta criada! Faça login.")


# ── 2FA ───────────────────────────────────────
def page_2fa():
    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        st.markdown("<br><br>", unsafe_allow_html=True)
        render_logo()
        st.markdown('<h2>Verificação em 2 etapas</h2>', unsafe_allow_html=True)
        code = st.session_state.get("2fa_code", "------")
        st.info(f"🔐 Código de verificação enviado para seu e-mail: **{code}**\n\n*(Em produção, um e-mail real seria enviado via SMTP)*")
        typed = st.text_input("Digite o código de 6 dígitos", max_chars=6, placeholder="000000")
        if st.button("Verificar →", use_container_width=True):
            if typed == code:
                email = st.session_state["2fa_email"]
                st.session_state.logged_in    = True
                st.session_state.current_user = email
                st.session_state.page = "feed"
                st.session_state.pending_2fa  = False
                st.rerun()
            else:
                st.error("Código inválido. Tente novamente.")
        if st.button("← Voltar ao login"):
            st.session_state.page = "login"
            st.rerun()


# ── SIDEBAR (após login) ───────────────────────
def render_sidebar():
    with st.sidebar:
        render_logo()
        user = get_user()
        name = user.get("name", "Usuário")
        initials = "".join(w[0].upper() for w in name.split()[:2])
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:1.5rem;padding:12px;background:var(--glass-bg);border:1px solid var(--glass-bdr);border-radius:14px;">
          {avatar_html(initials, 48)}
          <div>
            <div style="font-weight:700;font-size:0.95rem;">{name}</div>
            <div style="color:var(--text-muted);font-size:0.75rem;">{user.get('area','')}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Notificações
        notifs = st.session_state.notifications
        if notifs:
            with st.expander(f"🔔 Notificações ({len(notifs)})"):
                for n in notifs:
                    st.markdown(f'<div style="font-size:0.8rem;color:var(--text-sec);padding:6px 0;border-bottom:1px solid var(--border);">{n}</div>', unsafe_allow_html=True)

        st.markdown("---")
        pages = {
            "🏠  Feed":           "feed",
            "📂  Pastas":         "folders",
            "🔍  Buscar Artigos": "search",
            "🧠  Rede de Conhec.":"knowledge",
            "💬  Chat":           "chat",
            "📊  Análises":       "analytics",
            "🖼️  Busca por Imagem":"image_search",
            "⚙️  Configurações":  "settings",
        }
        for label, key in pages.items():
            active = st.session_state.page == key
            btn_style = "color:var(--accent) !important;" if active else ""
            if st.button(label, use_container_width=True, key=f"nav_{key}"):
                st.session_state.page = key
                st.rerun()

        st.markdown("---")
        if st.button("🚪  Sair", use_container_width=True):
            st.session_state.logged_in    = False
            st.session_state.current_user = None
            st.session_state.page = "login"
            st.rerun()


# ── FEED ──────────────────────────────────────
def page_feed():
    st.markdown('<h1 style="margin-bottom:0.2rem;">Feed de Pesquisas</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--text-sec);margin-bottom:1.5rem;">Acompanhe pesquisas em andamento da comunidade científica</p>', unsafe_allow_html=True)

    col_feed, col_side = st.columns([2, 0.85])

    with col_feed:
        # Publicar nova pesquisa
        with st.expander("✍️ Publicar nova pesquisa"):
            np_title    = st.text_input("Título da pesquisa", key="np_title")
            np_abstract = st.text_area("Resumo / Abstract", key="np_abstract", height=100)
            np_tags     = st.text_input("Tags (separadas por vírgula)", key="np_tags")
            np_status   = st.selectbox("Status", ["Em andamento", "Publicado", "Concluído"], key="np_status")
            if st.button("Publicar →", key="btn_publish"):
                if np_title and np_abstract:
                    user = get_user()
                    name = user.get("name", "Usuário")
                    initials = "".join(w[0].upper() for w in name.split()[:2])
                    tags = [t.strip() for t in np_tags.split(",") if t.strip()] if np_tags else []
                    new_post = {
                        "id": len(st.session_state.feed_posts) + 1,
                        "author": name,
                        "avatar": initials,
                        "area": user.get("area", ""),
                        "title": np_title,
                        "abstract": np_abstract,
                        "tags": tags,
                        "likes": 0,
                        "comments": [],
                        "status": np_status,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "liked_by": [],
                        "connections": tags[:3],
                    }
                    st.session_state.feed_posts.insert(0, new_post)
                    st.success("Pesquisa publicada!")
                    st.rerun()

        for post in st.session_state.feed_posts:
            render_feed_card(post)

    with col_side:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;margin-bottom:1rem;">👥 Pesquisadores Seguidos</div>', unsafe_allow_html=True)
        for c in st.session_state.chat_contacts:
            online_icon = "🟢" if c["online"] else "⚫"
            following   = c["name"] in st.session_state.followed_researchers
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f'{online_icon} **{c["name"]}**', unsafe_allow_html=True)
            with col_b:
                btn_lbl = "✓" if following else "+"
                if st.button(btn_lbl, key=f"follow_{c['name']}"):
                    if following:
                        st.session_state.followed_researchers.remove(c["name"])
                    else:
                        st.session_state.followed_researchers.append(c["name"])
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="glass-card" style="margin-top:1rem;">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:Syne,sans-serif;font-weight:700;margin-bottom:0.8rem;">🔥 Áreas em Alta</div>', unsafe_allow_html=True)
        for area, count in [("Quantum ML", 42), ("CRISPR 2026", 38), ("Neuroplasticidade", 31), ("LLMs Científicos", 27)]:
            st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--border);font-size:0.85rem;"><span>{area}</span><span style="color:var(--blue-300);">{count} posts</span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def render_feed_card(post):
    user = get_user()
    email = st.session_state.current_user
    liked = email in post["liked_by"]

    st.markdown(f"""
    <div class="glass-card">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:1rem;">
        {avatar_html(post['avatar'])}
        <div style="flex:1;">
          <div style="font-weight:600;">{post['author']}</div>
          <div style="color:var(--text-muted);font-size:0.78rem;">{post['area']} · {post['date']}</div>
        </div>
        {status_badge(post['status'])}
      </div>
      <h3 style="margin:0 0 0.6rem;font-size:1.05rem;">{post['title']}</h3>
      <p style="color:var(--text-sec);font-size:0.87rem;line-height:1.6;margin-bottom:0.8rem;">{post['abstract']}</p>
      <div style="margin-bottom:0.8rem;">{tag_html(post['tags'])}</div>
    </div>
    """, unsafe_allow_html=True)

    # Actions row
    col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
    with col1:
        heart = "❤️" if liked else "🤍"
        if st.button(f"{heart} {post['likes']}", key=f"like_{post['id']}"):
            if liked:
                post["liked_by"].remove(email)
                post["likes"] -= 1
            else:
                post["liked_by"].append(email)
                post["likes"] += 1
            st.rerun()
    with col2:
        if st.button(f"💬 {len(post['comments'])}", key=f"cmt_toggle_{post['id']}"):
            key = f"show_cmt_{post['id']}"
            st.session_state[key] = not st.session_state.get(key, False)
            st.rerun()
    with col3:
        if st.button("🔗", key=f"share_{post['id']}"):
            st.toast("Link copiado!")

    if st.session_state.get(f"show_cmt_{post['id']}", False):
        for c in post["comments"]:
            st.markdown(f'<div style="background:var(--blue-900);border-radius:10px;padding:8px 12px;margin:4px 0;font-size:0.83rem;"><strong>{c["user"]}</strong>: {c["text"]}</div>', unsafe_allow_html=True)
        new_cmt = st.text_input("Adicionar comentário...", key=f"cmt_input_{post['id']}")
        if st.button("Enviar", key=f"cmt_send_{post['id']}"):
            if new_cmt:
                post["comments"].append({"user": get_user().get("name", "Você"), "text": new_cmt})
                st.rerun()


# ── PASTAS ────────────────────────────────────
def page_folders():
    st.markdown('<h1>📂 Pastas de Pesquisa</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--text-sec);margin-bottom:1.5rem;">Organize seus artigos e pesquisas em pastas temáticas</p>', unsafe_allow_html=True)

    col_new, _ = st.columns([2, 3])
    with col_new:
        new_folder = st.text_input("Nova pasta", placeholder="ex: Biofísica Molecular", key="new_folder_name")
        if st.button("➕ Criar pasta", key="btn_new_folder"):
            if new_folder:
                key = f"📁 {new_folder}"
                if key not in st.session_state.folders:
                    st.session_state.folders[key] = []
                    st.success(f"Pasta '{new_folder}' criada!")
                    st.rerun()

    st.markdown("---")
    cols = st.columns(3)
    for idx, (fname, files) in enumerate(st.session_state.folders.items()):
        with cols[idx % 3]:
            st.markdown(f"""
            <div class="folder-card">
              <div style="font-size:2rem;margin-bottom:8px;">📁</div>
              <div style="font-weight:700;font-size:0.95rem;">{fname.replace('📁 ','')}</div>
              <div style="color:var(--text-muted);font-size:0.78rem;margin-top:4px;">{len(files)} arquivo(s)</div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("Ver arquivos"):
                if files:
                    for f in files:
                        st.markdown(f'<div style="font-size:0.83rem;padding:4px 0;color:var(--text-sec);">📄 {f}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div style="font-size:0.83rem;color:var(--text-muted);">Pasta vazia</div>', unsafe_allow_html=True)

                uploaded = st.file_uploader("Adicionar arquivo", key=f"upload_{fname}", label_visibility="collapsed")
                if uploaded:
                    if uploaded.name not in st.session_state.folders[fname]:
                        st.session_state.folders[fname].append(uploaded.name)
                        st.success("Arquivo adicionado!")
                        st.rerun()

            if st.button("🗑️ Excluir pasta", key=f"del_folder_{fname}"):
                del st.session_state.folders[fname]
                st.rerun()


# ── BUSCA DE ARTIGOS ──────────────────────────
MOCK_ARTICLES = [
    {"title": "Transformer Models for Scientific Discovery", "authors": "Smith, J. et al.", "year": 2025, "journal": "Nature Machine Intelligence", "doi": "10.1038/s42256-025-0001", "abstract": "We present a novel transformer architecture fine-tuned on PubMed and arXiv datasets for automated hypothesis generation.", "tags": ["LLM", "IA", "ciência"]},
    {"title": "CRISPR-Cas13 for RNA Knockdown in Neurons", "authors": "Oliveira, R. et al.", "year": 2024, "journal": "Cell", "doi": "10.1016/j.cell.2024.02.033", "abstract": "Demonstramos eficiência de 92% no knockdown de transcritos específicos em neurônios corticais usando Cas13d.", "tags": ["CRISPR", "neurociência", "RNA"]},
    {"title": "Quantum Advantage in Drug Discovery", "authors": "Chen, L. et al.", "year": 2025, "journal": "Science", "doi": "10.1126/science.adm1234", "abstract": "Using variational quantum eigensolvers, we reduced conformational search space for protein-ligand docking by 10^4.", "tags": ["quantum", "fármacos", "proteínas"]},
    {"title": "Sleep and Synaptic Homeostasis: 2025 Update", "authors": "Tononi, G. et al.", "year": 2025, "journal": "Neuron", "doi": "10.1016/j.neuron.2025.01.010", "abstract": "Extended synaptic homeostasis hypothesis with new fMRI evidence showing overnight spine density normalization.", "tags": ["sono", "sinapses", "memória"]},
    {"title": "Federated Learning for Medical Imaging Privacy", "authors": "Kumar, P. et al.", "year": 2026, "journal": "The Lancet Digital Health", "doi": "10.1016/S2589-7500(26)00021-3", "abstract": "Multi-institution federated framework achieves 94.2% diagnostic accuracy without sharing raw patient images.", "tags": ["privacidade", "ML médico", "federado"]},
]

def page_search():
    st.markdown('<h1>🔍 Busca de Artigos Científicos</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--text-sec);margin-bottom:1.5rem;">Busque artigos exclusivamente dentro da base científica da ResearchNet</p>', unsafe_allow_html=True)

    col_s, col_f = st.columns([3, 1])
    with col_s:
        query = st.text_input("", placeholder="🔍  Buscar por título, autor, área...", key="search_query", label_visibility="collapsed")
    with col_f:
        year_filter = st.selectbox("Ano", ["Todos", "2026", "2025", "2024"], key="year_filter", label_visibility="collapsed")

    if query:
        q = query.lower()
        results = [
            a for a in MOCK_ARTICLES
            if q in a["title"].lower() or q in a["abstract"].lower()
            or any(q in t for t in a["tags"])
            or q in a["authors"].lower()
        ]
        if year_filter != "Todos":
            results = [a for a in results if str(a["year"]) == year_filter]

        if results:
            st.markdown(f'<p style="color:var(--text-sec);margin-bottom:1rem;">{len(results)} resultado(s) encontrado(s)</p>', unsafe_allow_html=True)
            for art in results:
                render_article_card(art)
        else:
            st.markdown('<div class="glass-card" style="text-align:center;"><div style="font-size:2.5rem;">🔭</div><div style="color:var(--text-muted);margin-top:0.5rem;">Nenhum resultado encontrado. Tente outros termos.</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:var(--text-muted);font-size:0.9rem;margin-bottom:1rem;">Artigos em destaque:</div>', unsafe_allow_html=True)
        for art in MOCK_ARTICLES[:3]:
            render_article_card(art)

def render_article_card(art):
    st.markdown(f"""
    <div class="glass-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;">
        <div style="flex:1;">
          <h3 style="margin:0 0 0.4rem;font-size:1rem;">{art['title']}</h3>
          <div style="color:var(--text-muted);font-size:0.78rem;margin-bottom:0.5rem;">
            {art['authors']} · <em>{art['journal']}</em> · {art['year']}
          </div>
          <p style="color:var(--text-sec);font-size:0.85rem;line-height:1.5;margin-bottom:0.6rem;">{art['abstract']}</p>
          <div>{tag_html(art['tags'])}</div>
        </div>
      </div>
      <div style="margin-top:0.8rem;font-size:0.78rem;color:var(--text-muted);">DOI: {art['doi']}</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 5])
    with c1:
        if st.button("💾 Salvar", key=f"save_art_{art['doi']}"):
            first_folder = list(st.session_state.folders.keys())[0]
            fname = f"{art['title'][:30]}.pdf"
            if fname not in st.session_state.folders[first_folder]:
                st.session_state.folders[first_folder].append(fname)
            st.toast("Salvo na primeira pasta!")
    with c2:
        if st.button("🔗 Citar", key=f"cite_art_{art['doi']}"):
            st.toast("Citação copiada!")


# ── REDE DE CONHECIMENTO ──────────────────────
def page_knowledge():
    st.markdown('<h1>🧠 Rede de Conhecimento</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--text-sec);margin-bottom:1.5rem;">Conecte tópicos de pesquisa e descubra relações entre áreas do conhecimento</p>', unsafe_allow_html=True)

    # Build network graph with plotly
    nodes_x = [0.5, 0.15, 0.85, 0.5, 0.15, 0.85, 0.5, 0.3, 0.7, 0.2, 0.8, 0.5]
    nodes_y = [0.9, 0.7, 0.7, 0.5, 0.35, 0.35, 0.2, 0.6, 0.6, 0.5, 0.5, 0.35]
    node_labels = ["IA", "Machine Learning", "Otimização", "Neurociência", "Memória",
                   "Sono", "Genômica", "Redes Neurais", "Quantum ML", "Plasticidade",
                   "CRISPR", "Proteômica"]
    node_sizes = [30, 22, 22, 30, 18, 18, 28, 20, 24, 18, 22, 20]
    node_colors = ["#3b7cf4","#2d6be4","#1a5abf","#4d8ef0","#7cb3ff",
                   "#00c6ff","#3b7cf4","#2d6be4","#00b4d8","#7cb3ff","#4d8ef0","#2d6be4"]

    edges = [(0,1),(0,2),(0,7),(0,8),(1,8),(1,2),(3,4),(3,5),(3,9),(4,5),(6,10),(6,11),(8,2)]
    edge_x, edge_y = [], []
    for s, e in edges:
        edge_x += [nodes_x[s], nodes_x[e], None]
        edge_y += [nodes_y[s], nodes_y[e], None]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(color="rgba(45,107,228,0.35)", width=2),
        hoverinfo="none"
    ))
    fig.add_trace(go.Scatter(
        x=nodes_x, y=nodes_y, mode="markers+text",
        marker=dict(size=node_sizes, color=node_colors,
                    line=dict(color="rgba(124,179,255,0.4)", width=2),
                    opacity=0.9),
        text=node_labels, textposition="top center",
        textfont=dict(color="white", size=11, family="Space Grotesk"),
        hoverinfo="text"
    ))
    fig.update_layout(
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=420,
        font=dict(color="white"),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown('<h3>➕ Adicionar nova conexão</h3>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        t1 = st.text_input("Tópico A", placeholder="ex: Epigenética")
    with c2:
        t2 = st.text_input("Tópico B", placeholder="ex: Câncer")
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Conectar →", key="btn_connect"):
            if t1 and t2:
                st.session_state.knowledge_nodes.append({"id": t1, "connections": [t2]})
                st.session_state.notifications.insert(0, f"Nova conexão criada: {t1} ↔ {t2}")
                st.success(f"Conexão {t1} ↔ {t2} adicionada à rede!")
                st.rerun()

    st.markdown("---")
    st.markdown('<h3>🔗 Conexões salvas</h3>', unsafe_allow_html=True)
    for node in st.session_state.knowledge_nodes:
        for conn in node["connections"]:
            st.markdown(f"""
            <div style="background:var(--glass-bg);border:1px solid var(--glass-bdr);border-radius:12px;
                        padding:10px 16px;margin-bottom:8px;display:flex;align-items:center;gap:12px;">
              <span style="background:rgba(59,124,244,0.2);border-radius:8px;padding:4px 12px;font-weight:600;font-size:0.85rem;">{node['id']}</span>
              <span style="color:var(--text-muted);">↔</span>
              <span style="background:rgba(0,198,255,0.15);border-radius:8px;padding:4px 12px;font-weight:600;font-size:0.85rem;">{conn}</span>
            </div>
            """, unsafe_allow_html=True)


# ── CHAT ──────────────────────────────────────
def page_chat():
    st.markdown('<h1>💬 Chat Seguro</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--text-sec);margin-bottom:1rem;">Mensagens criptografadas end-to-end 🔐</p>', unsafe_allow_html=True)

    col_contacts, col_msgs = st.columns([0.9, 2.5])

    with col_contacts:
        st.markdown('<div style="font-weight:700;margin-bottom:1rem;">Conversas</div>', unsafe_allow_html=True)
        for c in st.session_state.chat_contacts:
            online_dot = '<span class="badge-online"></span>' if c["online"] else '<span class="badge-offline"></span>'
            is_active  = st.session_state.active_chat == c["name"]
            bg = "rgba(59,124,244,0.2)" if is_active else "var(--glass-bg)"
            bdr = "rgba(59,124,244,0.5)" if is_active else "var(--glass-bdr)"
            st.markdown(f"""
            <div style="background:{bg};border:1px solid {bdr};border-radius:14px;padding:12px;margin-bottom:8px;cursor:pointer;">
              <div style="display:flex;align-items:center;gap:10px;">
                {avatar_html(c['avatar'], 36)}
                <div>
                  <div style="font-size:0.88rem;font-weight:600;">{online_dot}{c['name']}</div>
                  <div style="font-size:0.75rem;color:var(--text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:110px;">{c['last']}</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Abrir", key=f"open_chat_{c['name']}", use_container_width=True):
                st.session_state.active_chat = c["name"]
                st.rerun()

    with col_msgs:
        if st.session_state.active_chat:
            contact = st.session_state.active_chat
            msgs = st.session_state.chat_messages.get(contact, [])

            st.markdown(f"""
            <div style="background:var(--glass-bg);border:1px solid var(--glass-bdr);border-radius:16px;padding:16px;margin-bottom:1rem;">
              <div style="display:flex;align-items:center;gap:12px;">
                {avatar_html(contact[:2].upper(), 40)}
                <div>
                  <div style="font-weight:700;">{contact}</div>
                  <div style="font-size:0.78rem;color:var(--success);">🔒 Criptografia ativada</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Messages
            for msg in msgs:
                is_me = msg["from"] == "me"
                bubble_class = "chat-bubble-me" if is_me else "chat-bubble-other"
                align = "flex-end" if is_me else "flex-start"
                st.markdown(f"""
                <div style="display:flex;justify-content:{align};margin:4px 0;">
                  <div class="{bubble_class}">
                    <div>{msg['text']}</div>
                    <div style="font-size:0.7rem;color:var(--text-muted);margin-top:4px;text-align:right;">{msg['time']}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

            new_msg = st.text_input("Mensagem...", key=f"msg_input_{contact}", label_visibility="collapsed", placeholder="Digite uma mensagem segura...")
            if st.button("Enviar 🔒", key=f"send_msg_{contact}"):
                if new_msg:
                    now = datetime.now().strftime("%H:%M")
                    if contact not in st.session_state.chat_messages:
                        st.session_state.chat_messages[contact] = []
                    st.session_state.chat_messages[contact].append({"from": "me", "text": new_msg, "time": now})
                    for c in st.session_state.chat_contacts:
                        if c["name"] == contact:
                            c["last"] = new_msg[:40]
                    st.rerun()
        else:
            st.markdown("""
            <div class="glass-card" style="text-align:center;padding:3rem;">
              <div style="font-size:3rem;margin-bottom:1rem;">💬</div>
              <div style="color:var(--text-muted);">Selecione uma conversa para começar</div>
              <div style="color:var(--text-muted);font-size:0.8rem;margin-top:0.5rem;">Todas as mensagens são criptografadas AES-256</div>
            </div>
            """, unsafe_allow_html=True)


# ── ANALYTICS ─────────────────────────────────
def page_analytics():
    st.markdown('<h1>📊 Análise da sua Pesquisa</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--text-sec);margin-bottom:1.5rem;">Métricas detalhadas de impacto e alcance científico</p>', unsafe_allow_html=True)

    data = st.session_state.stats_data

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    kpis = [
        ("230", "Visualizações (Fev)", "📈"),
        ("12", "Citações totais", "📚"),
        ("47", "Seguidores", "👥"),
        ("3", "Pesquisas ativas", "🔬"),
    ]
    for col, (val, lbl, icon) in zip([c1, c2, c3, c4], kpis):
        with col:
            st.markdown(f"""
            <div class="metric-box">
              <div style="font-size:1.6rem;">{icon}</div>
              <div class="metric-value">{val}</div>
              <div class="metric-label">{lbl}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        fig_views = go.Figure()
        fig_views.add_trace(go.Scatter(
            x=data["months"], y=data["views"],
            fill="tozeroy",
            fillcolor="rgba(59,124,244,0.15)",
            line=dict(color="#3b7cf4", width=2.5),
            mode="lines+markers",
            marker=dict(size=6, color="#7cb3ff"),
            name="Visualizações"
        ))
        fig_views.update_layout(
            title=dict(text="Visualizações por mês", font=dict(color="white", family="Syne")),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8aa4cc"), height=280,
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis=dict(showgrid=False, color="#4a6080"),
            yaxis=dict(showgrid=True, gridcolor="rgba(45,107,228,0.1)", color="#4a6080"),
        )
        st.plotly_chart(fig_views, use_container_width=True)

    with col_g2:
        fig_cit = go.Figure()
        fig_cit.add_trace(go.Bar(
            x=data["months"], y=data["citations"],
            marker=dict(
                color=data["citations"],
                colorscale=[[0,"#0a1628"],[0.5,"#2d6be4"],[1,"#00c6ff"]],
                line=dict(color="rgba(77,142,240,0.4)", width=1)
            ),
            name="Citações"
        ))
        fig_cit.update_layout(
            title=dict(text="Citações por mês", font=dict(color="white", family="Syne")),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8aa4cc"), height=280,
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis=dict(showgrid=False, color="#4a6080"),
            yaxis=dict(showgrid=True, gridcolor="rgba(45,107,228,0.1)", color="#4a6080"),
        )
        st.plotly_chart(fig_cit, use_container_width=True)

    col_g3, col_g4 = st.columns(2)
    with col_g3:
        labels = ["IA", "Neurociência", "Genômica", "Quantum"]
        values = [42, 28, 18, 12]
        fig_pie = go.Figure(go.Pie(
            labels=labels, values=values,
            hole=0.6,
            marker=dict(colors=["#3b7cf4","#00c6ff","#7cb3ff","#2d6be4"],
                        line=dict(color="var(--bg-deep)", width=2)),
            textfont=dict(color="white"),
        ))
        fig_pie.update_layout(
            title=dict(text="Áreas de interesse do seu público", font=dict(color="white", family="Syne")),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8aa4cc"), height=280,
            margin=dict(l=10, r=10, t=40, b=10),
            legend=dict(font=dict(color="white")),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_g4:
        countries = ["Brasil", "EUA", "Portugal", "Alemanha", "Argentina"]
        readers   = [95, 62, 38, 25, 10]
        fig_bar = go.Figure(go.Bar(
            x=readers, y=countries, orientation="h",
            marker=dict(color=["#3b7cf4","#2d6be4","#7cb3ff","#1a3a6b","#4d8ef0"],
                        line=dict(color="rgba(77,142,240,0.3)", width=1))
        ))
        fig_bar.update_layout(
            title=dict(text="Leitores por país", font=dict(color="white", family="Syne")),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8aa4cc"), height=280,
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis=dict(showgrid=True, gridcolor="rgba(45,107,228,0.1)", color="#4a6080"),
            yaxis=dict(showgrid=False, color="#8aa4cc"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # H-index
    st.markdown("---")
    st.markdown('<h3>🎯 Índice de Impacto</h3>', unsafe_allow_html=True)
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        st.markdown("""<div class="metric-box">
          <div class="metric-value">h-4</div>
          <div class="metric-label">Índice H estimado</div>
        </div>""", unsafe_allow_html=True)
    with cc2:
        st.markdown("""<div class="metric-box">
          <div class="metric-value">3.8</div>
          <div class="metric-label">Fator de impacto médio</div>
        </div>""", unsafe_allow_html=True)
    with cc3:
        st.markdown("""<div class="metric-box">
          <div class="metric-value">94%</div>
          <div class="metric-label">Taxa de aceitação</div>
        </div>""", unsafe_allow_html=True)


# ── BUSCA POR IMAGEM ──────────────────────────
def page_image_search():
    st.markdown('<h1>🖼️ Busca por Imagem</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--text-sec);margin-bottom:1.5rem;">Faça upload de uma imagem para identificar conceitos, estruturas ou organismos e encontrar pesquisas relacionadas</p>', unsafe_allow_html=True)

    col_up, col_res = st.columns([1, 1.5])
    with col_up:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div style="font-weight:600;margin-bottom:1rem;">📤 Upload de imagem</div>', unsafe_allow_html=True)
        uploaded_img = st.file_uploader("", type=["png","jpg","jpeg","webp"], label_visibility="collapsed")
        category = st.selectbox("Tipo de conteúdo", ["Detectar automaticamente", "Estrutura molecular", "Célula / Tecido", "Organismo", "Gráfico científico", "Fórmula / Equação"])
        if st.button("🔍 Analisar imagem", use_container_width=True, key="btn_img_search"):
            if uploaded_img:
                st.session_state["img_analyzed"] = True
                st.session_state["img_category"] = category
            else:
                st.warning("Por favor, faça upload de uma imagem primeiro.")
        st.markdown('</div>', unsafe_allow_html=True)

        if uploaded_img:
            st.image(uploaded_img, caption="Imagem carregada", use_container_width=True)

    with col_res:
        if st.session_state.get("img_analyzed"):
            st.markdown("""
            <div class="glass-card">
              <div style="font-weight:700;margin-bottom:1rem;">🤖 Análise da IA</div>
              <div style="background:rgba(59,124,244,0.1);border-radius:12px;padding:12px;margin-bottom:1rem;">
                <div style="font-size:0.85rem;color:var(--text-sec);">Estrutura detectada</div>
                <div style="font-weight:700;font-size:1.1rem;margin-top:4px;">Neurônio Piramidal Cortical</div>
                <div style="font-size:0.82rem;color:var(--text-muted);margin-top:4px;">Confiança: 87% · Camada V, Córtex Motor</div>
              </div>
              <div style="font-size:0.85rem;color:var(--text-sec);margin-bottom:0.5rem;">Termos relacionados:</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(tag_html(["neurônio piramidal", "axônio", "dendrites", "córtex", "Layer V"]), unsafe_allow_html=True)

            st.markdown('<div style="font-weight:600;margin-top:1.5rem;margin-bottom:0.8rem;">📚 Pesquisas encontradas:</div>', unsafe_allow_html=True)
            mock_results = [
                {"title": "Morphology of Layer V Pyramidal Neurons in Motor Cortex", "match": "94%"},
                {"title": "Dendritic Integration in Cortical Neurons: 2025 Review", "match": "88%"},
                {"title": "Cortical Circuit Connectivity and Behavior", "match": "76%"},
            ]
            for r in mock_results:
                st.markdown(f"""
                <div style="background:var(--glass-bg);border:1px solid var(--glass-bdr);border-radius:12px;padding:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;">
                  <div style="font-size:0.87rem;font-weight:500;">{r['title']}</div>
                  <span style="background:rgba(46,213,115,0.15);border:1px solid rgba(46,213,115,0.3);border-radius:12px;padding:2px 10px;font-size:0.75rem;color:#2ed573;font-weight:600;white-space:nowrap;margin-left:12px;">{r['match']}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="glass-card" style="text-align:center;padding:3rem;">
              <div style="font-size:3.5rem;margin-bottom:1rem;">🔭</div>
              <div style="color:var(--text-muted);font-size:0.95rem;">Faça upload de uma imagem e clique em Analisar para encontrar pesquisas relacionadas</div>
              <div style="margin-top:1.5rem;">
                <span class="tag">Estruturas moleculares</span>
                <span class="tag">Células e tecidos</span>
                <span class="tag">Gráficos científicos</span>
                <span class="tag">Equações</span>
              </div>
            </div>
            """, unsafe_allow_html=True)


# ── CONFIGURAÇÕES ─────────────────────────────
def page_settings():
    st.markdown('<h1>⚙️ Configurações</h1>', unsafe_allow_html=True)

    user  = get_user()
    email = st.session_state.current_user

    tab_profile, tab_security, tab_privacy = st.tabs([
        "  👤 Perfil  ", "  🔒 Segurança  ", "  🛡️ Privacidade & Cripto  "
    ])

    # ── PERFIL
    with tab_profile:
        st.markdown('<h3>Informações pessoais</h3>', unsafe_allow_html=True)
        name = user.get("name", "")
        initials = "".join(w[0].upper() for w in name.split()[:2])

        col_av, col_form = st.columns([0.7, 2])
        with col_av:
            st.markdown(avatar_html(initials, 80), unsafe_allow_html=True)
            photo = st.file_uploader("Alterar foto", type=["png","jpg","jpeg"], label_visibility="collapsed")
            if photo:
                st.session_state.users[email]["photo"] = photo.name
                st.success("Foto atualizada!")

        with col_form:
            new_name  = st.text_input("Nome completo", value=user.get("name",""), key="cfg_name")
            new_email = st.text_input("E-mail", value=email, key="cfg_email")
            new_area  = st.text_input("Área de pesquisa", value=user.get("area",""), key="cfg_area")
            new_bio   = st.text_area("Biografia", value=user.get("bio",""), key="cfg_bio", height=90)

            if st.button("💾 Salvar perfil", key="btn_save_profile"):
                st.session_state.users[email]["name"]  = new_name
                st.session_state.users[email]["area"]  = new_area
                st.session_state.users[email]["bio"]   = new_bio
                if new_email != email and new_email not in st.session_state.users:
                    st.session_state.users[new_email] = st.session_state.users.pop(email)
                    st.session_state.current_user = new_email
                st.success("Perfil atualizado!")
                st.rerun()

    # ── SEGURANÇA
    with tab_security:
        st.markdown('<h3>Alterar senha</h3>', unsafe_allow_html=True)
        old_pw  = st.text_input("Senha atual", type="password", key="old_pw")
        new_pw  = st.text_input("Nova senha", type="password", key="new_pw")
        new_pw2 = st.text_input("Confirmar nova senha", type="password", key="new_pw2")

        if st.button("🔑 Alterar senha", key="btn_change_pw"):
            if hash_pw(old_pw) != user["password"]:
                st.error("Senha atual incorreta.")
            elif new_pw != new_pw2:
                st.error("As novas senhas não coincidem.")
            elif len(new_pw) < 6:
                st.error("Nova senha muito curta.")
            else:
                st.session_state.users[email]["password"] = hash_pw(new_pw)
                st.success("Senha alterada com sucesso!")

        st.markdown("---")
        st.markdown('<h3>Autenticação de dois fatores (2FA)</h3>', unsafe_allow_html=True)
        st.markdown('<p style="color:var(--text-sec);font-size:0.88rem;">Ao ativar, um código de 6 dígitos será enviado para seu e-mail a cada login.</p>', unsafe_allow_html=True)

        enabled_2fa = user.get("2fa_enabled", False)
        col_2fa, col_2fa_btn = st.columns([3, 1])
        with col_2fa:
            st.markdown(f"""
            <div style="background:var(--glass-bg);border:1px solid var(--glass-bdr);border-radius:14px;padding:16px;display:flex;align-items:center;justify-content:space-between;">
              <div>
                <div style="font-weight:600;">2FA por e-mail</div>
                <div style="color:var(--text-muted);font-size:0.8rem;">{email}</div>
              </div>
              <span style="color:{'#2ed573' if enabled_2fa else '#ff4757'};font-weight:700;">{'✅ Ativo' if enabled_2fa else '❌ Inativo'}</span>
            </div>
            """, unsafe_allow_html=True)

        with col_2fa_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            lbl = "Desativar" if enabled_2fa else "Ativar 2FA"
            if st.button(lbl, key="btn_toggle_2fa"):
                if not enabled_2fa:
                    demo_code = generate_code()
                    st.session_state.users[email]["2fa_enabled"] = True
                    st.success(f"2FA ativado! Código de confirmação (demo): **{demo_code}**")
                else:
                    st.session_state.users[email]["2fa_enabled"] = False
                    st.success("2FA desativado.")
                st.rerun()

        st.markdown("---")
        st.markdown('<h3>📱 Simulação de envio de código</h3>', unsafe_allow_html=True)
        if st.button("📧 Enviar código de teste ao e-mail", key="btn_test_code"):
            code = generate_code()
            st.session_state["test_code"] = code
            st.info(f"Código gerado: **{code}**\n\nEm produção, seria enviado via SMTP para **{email}**")

        if st.session_state.get("test_code"):
            typed_code = st.text_input("Digite o código recebido para validar:", max_chars=6, key="verify_test")
            if st.button("Verificar código", key="btn_verify_test"):
                if typed_code == st.session_state["test_code"]:
                    st.success("✅ Código verificado com sucesso! Sistema de 2FA funcionando.")
                else:
                    st.error("❌ Código inválido.")

    # ── PRIVACIDADE
    with tab_privacy:
        st.markdown('<h3>🔐 Criptografia e privacidade</h3>', unsafe_allow_html=True)
        st.markdown("""
        <div class="glass-card">
          <div style="font-weight:700;margin-bottom:1rem;font-size:1.05rem;">Proteções ativas na sua conta</div>
          <div style="display:grid;gap:12px;">
            <div style="display:flex;align-items:center;gap:12px;padding:12px;background:rgba(46,213,115,0.08);border:1px solid rgba(46,213,115,0.2);border-radius:12px;">
              <span style="font-size:1.4rem;">🔒</span>
              <div><div style="font-weight:600;color:#2ed573;">AES-256</div><div style="font-size:0.8rem;color:var(--text-sec);">Criptografia de mensagens end-to-end</div></div>
            </div>
            <div style="display:flex;align-items:center;gap:12px;padding:12px;background:rgba(46,213,115,0.08);border:1px solid rgba(46,213,115,0.2);border-radius:12px;">
              <span style="font-size:1.4rem;">🛡️</span>
              <div><div style="font-weight:600;color:#2ed573;">SHA-256</div><div style="font-size:0.8rem;color:var(--text-sec);">Hash de senhas com salt criptográfico</div></div>
            </div>
            <div style="display:flex;align-items:center;gap:12px;padding:12px;background:rgba(46,213,115,0.08);border:1px solid rgba(46,213,115,0.2);border-radius:12px;">
              <span style="font-size:1.4rem;">🔑</span>
              <div><div style="font-weight:600;color:#2ed573;">TLS 1.3</div><div style="font-size:0.8rem;color:var(--text-sec);">Transmissão segura de dados (HTTPS)</div></div>
            </div>
            <div style="display:flex;align-items:center;gap:12px;padding:12px;background:rgba(46,213,115,0.08);border:1px solid rgba(46,213,115,0.2);border-radius:12px;">
              <span style="font-size:1.4rem;">👁️</span>
              <div><div style="font-weight:600;color:#2ed573;">Zero Knowledge</div><div style="font-size:0.8rem;color:var(--text-sec);">Pesquisas privadas não são acessadas pela plataforma</div></div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<h3>🕵️ Controle de visibilidade</h3>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            vis_profile = st.selectbox("Visibilidade do perfil", ["Público", "Só seguidores", "Privado"], key="vis_profile")
            vis_research = st.selectbox("Visibilidade das pesquisas", ["Público", "Só seguidores", "Privado"], key="vis_research")
        with c2:
            vis_stats = st.selectbox("Visibilidade das estatísticas", ["Público", "Privado"], key="vis_stats")
            vis_network = st.selectbox("Visibilidade da rede de conhec.", ["Público", "Só seguidores", "Privado"], key="vis_net")
        if st.button("💾 Salvar configurações de privacidade", key="btn_save_privacy"):
            st.success("Configurações de privacidade salvas!")


# ─────────────────────────────────────────────
#  ROUTER
# ─────────────────────────────────────────────
def main():
    if not st.session_state.logged_in:
        if st.session_state.page == "2fa":
            page_2fa()
        else:
            page_login()
        return

    render_sidebar()

    page = st.session_state.page
    if   page == "feed":          page_feed()
    elif page == "folders":       page_folders()
    elif page == "search":        page_search()
    elif page == "knowledge":     page_knowledge()
    elif page == "chat":          page_chat()
    elif page == "analytics":     page_analytics()
    elif page == "image_search":  page_image_search()
    elif page == "settings":      page_settings()
    else:
        st.session_state.page = "feed"
        st.rerun()

if __name__ == "__main__":
    main()
