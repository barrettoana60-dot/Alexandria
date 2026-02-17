import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
from datetime import datetime
import hashlib
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Nexus Science",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILIZAÇÃO CSS (LIQUID GLASS & DARK BLUE THEME) ---
# Aqui definimos a paleta Azul Escuro/Preto e o efeito de vidro
st.markdown("""
<style>
    /* Fundo Geral */
    .stApp {
        background: linear-gradient(135deg, #02040a 0%, #0d1b2a 100%);
        color: #e0e0e0;
    }

    /* Remove padding padrão */
    .block-container {
        padding-top: 2rem;
    }

    /* Efeito Liquid Glass (Vidro Líquido) para Cards */
    .glass-card {
        background: rgba(20, 30, 50, 0.4);
        border-radius: 16px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(100, 149, 237, 0.1);
        padding: 20px;
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    
    .glass-card:hover {
        border: 1px solid rgba(100, 149, 237, 0.3);
        transform: translateY(-2px);
    }

    /* Inputs Modernos */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
        background-color: rgba(10, 15, 25, 0.6) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
    }

    /* Botões Liquid Glass */
    .stButton > button {
        background: linear-gradient(135deg, rgba(30, 58, 138, 0.6), rgba(30, 58, 138, 0.2));
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 12px;
        padding: 10px 24px;
        backdrop-filter: blur(4px);
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        width: 100%;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.8), rgba(30, 58, 138, 0.4));
        box-shadow: 0 0 15px rgba(59, 130, 246, 0.6);
        border-color: rgba(255, 255, 255, 0.6);
    }
    
    /* Sidebar Customizada */
    section[data-testid="stSidebar"] {
        background-color: #05080f;
        border-right: 1px solid #1e293b;
    }

    /* Títulos */
    h1, h2, h3 {
        color: #f8fafc;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 300;
    }
    
    /* Chat bubbles */
    .user-msg {
        background: rgba(37, 99, 235, 0.3);
        padding: 10px;
        border-radius: 10px 10px 0 10px;
        margin: 5px 0;
        text-align: right;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .bot-msg {
        background: rgba(255, 255, 255, 0.05);
        padding: 10px;
        border-radius: 10px 10px 10px 0;
        margin: 5px 0;
        border: 1px solid rgba(255,255,255,0.05);
    }

</style>
""", unsafe_allow_html=True)

# --- GERENCIAMENTO DE ESTADO ---
if 'page' not in st.session_state:
    st.session_state.page = 'Login'
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'messages' not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": "Bem-vindo ao chat criptografado."}]

# --- FUNÇÕES AUXILIARES ---

def mock_encryption(data):
    """Simula criptografia SHA-256 para demonstração"""
    return hashlib.sha256(data.encode()).hexdigest()

def render_glass_card(title, content, extra_html=""):
    st.markdown(f"""
    <div class="glass-card">
        <h3 style="margin-top:0;">{title}</h3>
        <p style="font-size: 0.95rem; opacity: 0.8;">{content}</p>
        {extra_html}
    </div>
    """, unsafe_allow_html=True)

# --- PÁGINAS ---

def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; margin-bottom: 30px;'>NEXUS SCIENCE</h1>", unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Login", "Cadastro"])
        
        with tab1:
            email = st.text_input("E-mail", key="login_email")
            password = st.text_input("Senha", type="password", key="login_pass")
            if st.button("Entrar", key="btn_login"):
                if email and password:
                    st.success("Autenticado com sucesso!")
                    time.sleep(1)
                    st.session_state.authenticated = True
                    st.session_state.page = "Feed"
                    st.rerun()
                else:
                    st.error("Preencha todos os campos.")
        
        with tab2:
            st.text_input("Nome Completo")
            st.text_input("E-mail Acadêmico")
            st.text_input("Senha", type="password")
            st.text_input("Confirmar Senha", type="password")
            st.markdown("*Ao cadastrar, enviaremos um código 2FA para seu e-mail.*")
            if st.button("Criar Conta", key="btn_register"):
                st.info("Código de verificação enviado para o e-mail.")

def feed_page():
    st.title("Feed de Pesquisa")
    
    # Área de postagem
    with st.container():
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        col1, col2 = st.columns([6, 1])
        with col1:
            st.text_input("Compartilhe o progresso da sua pesquisa...", label_visibility="collapsed")
        with col2:
            st.button("Publicar")
        st.markdown('</div>', unsafe_allow_html=True)

    # Posts Simulados
    posts = [
        {"author": "Dra. Elena Fisher", "role": "Neurociência", "content": "Acabei de publicar os resultados preliminares sobre plasticidade sináptica. O modelo de ML identificou padrões inéditos.", "likes": 342, "comments": 45},
        {"author": "Prof. James Chen", "role": "Física Quântica", "content": "Buscando colaboradores para revisão de artigo sobre emaranhamento em temperaturas ambientes. Alguém disponível?", "likes": 120, "comments": 89},
        {"author": "Lab. BioTech Alpha", "role": "Empresa", "content": "Nova patente registrada! O sequenciamento agora é 50% mais rápido com nosso novo algoritmo.", "likes": 1500, "comments": 201}
    ]

    for post in posts:
        html_content = f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
            <span style="font-size: 0.8rem; color: #6495ED;">❤️ {post['likes']} • 💬 {post['comments']}</span>
            <button style="background: none; border: 1px solid #6495ED; color: #6495ED; border-radius: 5px; cursor: pointer;">Conectar</button>
        </div>
        """
        render_glass_card(f"{post['author']} <span style='font-size:0.7rem; color: #aaa;'>{post['role']}</span>", post['content'], html_content)

def folders_page():
    st.title("Minhas Pastas & Biblioteca")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        st.button("+ Nova Pasta")
        st.button("Importar PDF")
    
    # Grid de pastas simulado
    folders = ["Tese Doutorado", "Artigos IA Generativa", "Referências Bioquímica", "Projetos Pendentes", "Leitura de Fim de Semana", "Conferência 2026"]
    
    cols = st.columns(3)
    for i, folder in enumerate(folders):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="glass-card" style="text-align: center; padding: 30px;">
                <h1 style="font-size: 40px;">📁</h1>
                <h4>{folder}</h4>
                <p style="font-size: 0.8rem; opacity: 0.6;">12 items • Atualizado há 2h</p>
            </div>
            """, unsafe_allow_html=True)

def graph_page():
    st.title("Rede de Conhecimento")
    st.markdown("Visualize como sua pesquisa se conecta com outros tópicos globais.")
    
    # Criar um grafo aleatório para visualização
    G = nx.random_geometric_graph(50, 0.25)
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = G.nodes[edge[0]]['pos']
        x1, y1 = G.nodes[edge[1]]['pos']
        edge_x.append(x0)
        edge_x.append(x1)
        edge_x.append(None)
        edge_y.append(y0)
        edge_y.append(y1)
        edge_y.append(None)

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#4a6fa5'),
        hoverinfo='none',
        mode='lines')

    node_x = []
    node_y = []
    for node in G.nodes():
        x, y = G.nodes[node]['pos']
        node_x.append(x)
        node_y.append(y)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        hoverinfo='text',
        marker=dict(
            showscale=True,
            colorscale='Bluered',
            color=[],
            size=10,
            colorbar=dict(thickness=15, title='Conexões', xanchor='left', titleside='right'),
            line_width=2))

    node_adjacencies = []
    node_text = []
    for node, adjacencies in enumerate(G.adjacency()):
        node_adjacencies.append(len(adjacencies[1]))
        node_text.append(f'Pesquisador #{node}<br>Conexões: {len(adjacencies[1])}')

    node_trace.marker.color = node_adjacencies
    node_trace.text = node_text

    fig = go.Figure(data=[edge_trace, node_trace],
                 layout=go.Layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=0,l=0,r=0,t=0),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                    )
    
    st.plotly_chart(fig, use_container_width=True)

def search_page():
    st.title("Buscador Científico")
    
    search_type = st.radio("Modo de Busca:", ["Artigos", "Imagem (Visual Search)"], horizontal=True)
    
    if search_type == "Artigos":
        col1, col2 = st.columns([5, 1])
        with col1:
            st.text_input("Digite palavras-chave, DOI ou autor...", placeholder="Ex: CRISPR Cas-9 efficiency")
        with col2:
            st.button("Pesquisar", use_container_width=True)
            
        st.markdown("### Resultados")
        render_glass_card("Advances in Genomic Editing", "Autores: J. Doe, M. Smith. <br>Journal: Nature (2025).<br>Citações: 124", "<button>Ler PDF</button>")
        render_glass_card("Machine Learning in Proteomics", "Autores: A. Turing AI Lab. <br>Journal: Science Robotics.<br>Citações: 89", "<button>Ler PDF</button>")
        
    else:
        st.file_uploader("Arraste uma imagem de gráfico, fórmula ou célula...", type=['png', 'jpg'])
        st.button("Analisar Imagem")
        st.markdown("""
        <div style="text-align:center; padding: 20px; opacity: 0.5;">
            O sistema irá localizar artigos que contenham figuras similares.
        </div>
        """, unsafe_allow_html=True)

def analytics_page():
    st.title("Análise de Performance")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Leituras Totais", "1,204", "+12%")
    with col2:
        st.metric("Citações", "34", "+2")
    with col3:
        st.metric("Índice H (Simulado)", "12", "0")
        
    # Gráfico simulado
    df = pd.DataFrame({
        "Data": pd.date_range(start="2025-01-01", periods=30),
        "Visualizações": np.random.randint(10, 100, 30),
        "Engajamento": np.random.randint(5, 50, 30)
    })
    
    fig = px.area(df, x="Data", y=["Visualizações", "Engajamento"], template="plotly_dark", title="Impacto da Pesquisa")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

def chat_page():
    st.title("Chat Criptografado")
    st.caption("🔒 Criptografia ponta-a-ponta ativa.")
    
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            align = "user-msg" if msg["role"] == "user" else "bot-msg"
            st.markdown(f'<div class="{align}">{msg["content"]}</div>', unsafe_allow_html=True)
            
    prompt = st.chat_input("Digite sua mensagem...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Resposta simulada
        st.session_state.messages.append({"role": "assistant", "content": f"Recebi sua mensagem sobre '{prompt}'. Vamos analisar isso."})
        st.rerun()

def settings_page():
    st.title("Configurações")
    
    with st.container():
        st.markdown("### Perfil")
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image("https://ui-avatars.com/api/?name=User+Name&background=0D8ABC&color=fff&size=200", width=150)
            st.button("Alterar Foto")
        with col2:
            st.text_input("Nome de Exibição", value="Dr. Usuário Exemplo")
            st.text_area("Bio", value="Pesquisador focado em IA e Ética.")
            
    st.divider()
    
    st.markdown("### Segurança")
    with st.expander("Alterar E-mail e Senha"):
        st.text_input("Novo E-mail")
        st.text_input("Nova Senha", type="password")
        st.button("Atualizar Credenciais")

    with st.expander("Autenticação de Dois Fatores (2FA)"):
        st.toggle("Ativar 2FA via E-mail")
        st.text_input("Código de verificação (Simulação)")
        st.button("Confirmar")

# --- NAVEGAÇÃO PRINCIPAL ---

if st.session_state.authenticated:
    with st.sidebar:
        st.markdown("## NEXUS")
        if st.button("🏠 Feed Principal"): st.session_state.page = "Feed"
        if st.button("📁 Minhas Pastas"): st.session_state.page = "Pastas"
        if st.button("🔍 Buscador"): st.session_state.page = "Busca"
        if st.button("🕸️ Rede Global"): st.session_state.page = "Network"
        if st.button("📊 Estatísticas"): st.session_state.page = "Analytics"
        if st.button("💬 Chat Privado"): st.session_state.page = "Chat"
        st.divider()
        if st.button("⚙️ Configurações"): st.session_state.page = "Settings"
        if st.button("🚪 Sair"): 
            st.session_state.authenticated = False
            st.rerun()

    # Roteamento
    if st.session_state.page == "Feed": feed_page()
    elif st.session_state.page == "Pastas": folders_page()
    elif st.session_state.page == "Busca": search_page()
    elif st.session_state.page == "Network": graph_page()
    elif st.session_state.page == "Analytics": analytics_page()
    elif st.session_state.page == "Chat": chat_page()
    elif st.session_state.page == "Settings": settings_page()

else:
    login_page()
