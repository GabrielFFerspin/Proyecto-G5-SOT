import streamlit as st
import requests
import json
import pandas as pd
import time
import streamlit.components.v1 as components
from graph_visualizer import render_subgraph

# ══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE PÁGINA
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="G5 Knowledge Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ══════════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════════
API_URL = "https://qr6y691cs3.execute-api.eu-west-3.amazonaws.com/prod/g5-lambda-sot"  # ← pon tu password aquí

# Colores e iconos por intent detectado
INTENT_BADGES = {
    "top_rated":        ("🏆", "#2ecc71", "Top Rated"),
    "top_by_category":  ("📂", "#3498db", "Por Categoría"),
    "copurchase":       ("🔗", "#e67e22", "Co-Compras"),
    "similar_to":       ("🔍", "#9b59b6", "Similares"),
    "category_affinity":("🗺️",  "#1abc9c", "Afinidad"),
    "combined_score":   ("⚡", "#e74c3c", "Score Combinado"),
    "generic":          ("💬", "#95a5a6", "General"),
    "error":            ("❌", "#e74c3c", "Error"),
}

# Preguntas de ejemplo por categoría
EXAMPLE_QUESTIONS = [
    "¿Cuáles son los productos mejor valorados?",
    "¿Cuáles son los mejores juguetes?",
    "¿Qué productos de deportes son los más valorados?",
    "¿Cuáles son los mejores videojuegos?",
    "¿Qué productos se compran juntos habitualmente?",
    "¿Qué categorías tienen más afinidad entre sí?",
    "¿Cuál es el mejor producto más popular overall?",
]

# ══════════════════════════════════════════════════════════════════
# CSS PERSONALIZADO
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
  /* Fondo y tipografía general */
  .main { background-color: #0f1117; }

  /* Caja de respuesta */
  .answer-box {
    background: linear-gradient(135deg, #1e1e2e, #16213e);
    border-left: 4px solid #4ec9b0;
    border-radius: 8px;
    padding: 1.2rem 1.5rem;
    margin: 1rem 0;
    color: #d4d4d4;
    font-size: 0.97rem;
    line-height: 1.7;
  }

  /* Badge de intent */
  .intent-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: bold;
    margin-right: 0.5rem;
    margin-top: 0.5rem;
  }

  /* Tarjeta de métrica */
  .metric-card {
    background: linear-gradient(135deg, #1e1e2e, #16213e);
    border-radius: 10px;
    padding: 1.2rem;
    text-align: center;
    border: 1px solid #2d2d4e;
    margin-bottom: 1rem;
  }
  .metric-value {
    font-size: 2rem;
    font-weight: bold;
    color: #4ec9b0;
  }
  .metric-label {
    font-size: 0.85rem;
    color: #888;
    margin-top: 0.3rem;
  }

  /* Header */
  .app-header {
    text-align: center;
    padding: 1.5rem 0 0.5rem 0;
  }
  .app-title {
    font-size: 2.4rem;
    font-weight: bold;
    background: linear-gradient(90deg, #4ec9b0, #9cdcfe);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .app-subtitle {
    color: #666;
    font-size: 0.9rem;
    margin-top: 0.3rem;
  }

  /* Contexto */
  .context-box {
    background: #1e1e2e;
    border-radius: 6px;
    padding: 0.8rem 1rem;
    font-family: monospace;
    font-size: 0.8rem;
    color: #888;
    white-space: pre-wrap;
    max-height: 300px;
    overflow-y: auto;
  }

  /* Botones de ejemplo */
  div.stButton > button {
    width: 100%;
    border-radius: 8px;
    border: 1px solid #2d2d4e;
    background: #1e1e2e;
    color: #d4d4d4;
    transition: all 0.2s;
  }
  div.stButton > button:hover {
    border-color: #4ec9b0;
    color: #4ec9b0;
  }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# SESSION STATE — guardar última respuesta
# ══════════════════════════════════════════════════════════════════
if "last_answer"  not in st.session_state:
    st.session_state.last_answer  = None
if "last_intent"  not in st.session_state:
    st.session_state.last_intent  = None
if "last_context" not in st.session_state:
    st.session_state.last_context = None
if "last_category" not in st.session_state:
    st.session_state.last_category = None
if "prefill_question" not in st.session_state:
    st.session_state.prefill_question = ""

# ══════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL — llamar a la API Lambda
# ══════════════════════════════════════════════════════════════════

def call_api(question, product_id=None, category=None):
    payload = {"question": question}
    if product_id and product_id.strip():
        payload["product_id"] = product_id.strip()
    # NEW: forzar categoría si se pasa directamente
    if category:
        payload["category"] = category

    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        raw  = response.json()
        body = raw.get("body", raw)
        if isinstance(body, str):
            body = json.loads(body)
        return body
    except requests.exceptions.Timeout:
        return {"error": "⏱️ Timeout — inténtalo de nuevo."}
    except Exception as e:
        return {"error": f"❌ Error: {str(e)}"}


# ══════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<div class="app-header">
  <div class="app-title">🧠 G5 Knowledge Assistant</div>
  <div class="app-subtitle">
    Powered by Neo4j AuraDB · Amazon Bedrock Nova Micro · AWS Lambda · API Gateway
  </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# ══════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs([
    "💬 Pregunta al Asistente",
    "📊 Explorar Grafo",
    "🏆 Top Productos"
])

# ──────────────────────────────────────────────────────────────────
# TAB 1 — Pregunta al Asistente
# ──────────────────────────────────────────────────────────────────
with tab1:
    col_main, col_side = st.columns([2, 1])

    with col_main:
        st.markdown("### 💬 Haz una pregunta al grafo de conocimiento")

        # Input de pregunta
        question = st.text_input(
            label="Pregunta",
            value=st.session_state.prefill_question,
            placeholder="Ej: ¿Cuáles son los mejores juguetes?",
            label_visibility="collapsed"
        )

        # Opciones avanzadas — product_id opcional
        with st.expander("🔧 Opciones avanzadas"):
            product_id = st.text_input(
                "Product ID (opcional — para co-compras de un producto concreto)",
                placeholder="Ej: B087NN2K41",
                help="Si lo rellenas, la consulta de co-compras se hará sobre este producto específico."
            )

        # Botón principal
        btn_ask = st.button("🔍 Preguntar", type="primary", use_container_width=True)

        # Ejecutar query
        if btn_ask and question:
            with st.spinner("🔄 Consultando Neo4j + Bedrock..."):
                t0   = time.time()
                body = call_api(question, product_id if "product_id" in dir() else None)
                elapsed = time.time() - t0

            if "error" in body:
                st.error(body["error"])
            else:
                # Guardar en session state
                st.session_state.last_answer   = body.get("answer", "")
                st.session_state.last_intent   = body.get("intent", "generic")
                st.session_state.last_context  = body.get("context", "")
                st.session_state.last_category = body.get("category")

        elif btn_ask and not question:
            st.warning("⚠️ Escribe una pregunta primero.")

        # Mostrar respuesta si existe
        if st.session_state.last_answer:
            # Badges de intent y categoría
            intent = st.session_state.last_intent or "generic"
            icon, color, label = INTENT_BADGES.get(intent, ("💬", "#95a5a6", intent))
            cat    = st.session_state.last_category

            badge_html = (
                f'<span class="intent-badge" style="background:{color}22; ' +
                f'color:{color}; border:1px solid {color};">{icon} {label}</span>'
            )
            if cat:
                badge_html += (
                    f'<span class="intent-badge" style="background:#3498db22;' +
                    f'color:#3498db; border:1px solid #3498db;">📂 {cat}</span>'
                )

            st.markdown(badge_html, unsafe_allow_html=True)

            # Respuesta
            st.markdown(
                f'<div class="answer-box">{st.session_state.last_answer}</div>',
                unsafe_allow_html=True
            )

            # Contexto del grafo
            with st.expander("📊 Ver datos del grafo (contexto Neo4j)"):
            
            # Contexto del grafo + subgrafo interactivo
            # 1. Texto del contexto (como antes)
                st.markdown(
                    f'<div class="context-box">{st.session_state.last_context}</div>',
                    unsafe_allow_html=True
                )

                st.divider()

                # 2. Subgrafo Neo4j interactivo
                st.markdown("**🕸️ Subgrafo Neo4j — nodos reales**")
                st.caption("🔵 Producto · 🟠 Categoría | Grosor arista = peso co-compra")

            with st.spinner("Renderizando subgrafo..."):
                graph_html = render_subgraph(
                    intent    = st.session_state.last_intent or "generic",
                    entity_id = st.session_state.get("last_entity_id"),
                    category  = st.session_state.last_category,
                    uri       = NEO4J_URI,
                    user      = NEO4J_USER,
                    password  = NEO4J_PASSWORD,
                )
            components.html(graph_html, height=540, scrolling=False)
                

    # Columna lateral — preguntas de ejemplo
    with col_side:
        st.markdown("### 💡 Preguntas de ejemplo")
        st.caption("Haz clic para rellenar la pregunta automáticamente")

        for i, example in enumerate(EXAMPLE_QUESTIONS):
            if st.button(example, key=f"ex_{i}"):
                st.session_state.prefill_question = example
                st.rerun()

# ──────────────────────────────────────────────────────────────────
# TAB 2 — Explorar Grafo
# ──────────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### 📊 Estado del Grafo de Conocimiento — Neo4j AuraDB")

    # Métricas principales
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("""
        <div class="metric-card">
          <div class="metric-value">107,021</div>
          <div class="metric-label">🛍️ Productos</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="metric-card">
          <div class="metric-value">43,299</div>
          <div class="metric-label">👥 Reviewers</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="metric-card">
          <div class="metric-value">19,167</div>
          <div class="metric-label">🔗 Co-Compras</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown("""
        <div class="metric-card">
          <div class="metric-value">190,750</div>
          <div class="metric-label">⭐ Reseñas</div>
        </div>""", unsafe_allow_html=True)

    st.divider()

    col_chart, col_schema = st.columns([1, 1])

    with col_chart:
        st.markdown("#### 📦 Distribución de Reseñas por Categoría")
        df_cat = pd.DataFrame({
            "Categoría": [
                "Sports & Outdoors",
                "Video Games",
                "Toys & Games"
            ],
            "Reseñas": [65883, 65577, 59290]
        }).set_index("Categoría")
        st.bar_chart(df_cat, color="#4ec9b0", height=300)

    with col_schema:
        st.markdown("#### 🗺️ Esquema del Grafo")
        st.markdown("""
        ```
        NODOS
        ─────────────────────────────
        (:Product)   → 107,021
          product_id, title, category
          bayesian_score, avg_stars
          review_count

        (:Reviewer)  →  43,299
          reviewer_id, review_count
          avg_stars

        (:Category)  →       3
          name

        RELACIONES
        ─────────────────────────────
        REVIEWED     → 190,750
          stars, timestamp, year
          bayesian_score

        CO_PURCHASED →  19,167
          weight, cross_cat

        BELONGS_TO   → 107,021

        ACTIVE_IN    →  27,831
          review_count, avg_stars
        ```
        """)

    st.divider()

    # Afinidad entre categorías
    st.markdown("#### 🔗 Afinidad entre Categorías (CO_PURCHASED cross-cat)")
    df_aff = pd.DataFrame([
        {"Origen": "Toys & Games", "Destino": "Sports & Outdoors",
         "Aristas": 1450, "Peso Total": 2915},
        {"Origen": "Sports & Outdoors", "Destino": "Toys & Games",
         "Aristas": 1279, "Peso Total": 2577},
        {"Origen": "Video Games", "Destino": "Toys & Games",
         "Aristas": 217,  "Peso Total": 444},
        {"Origen": "Sports & Outdoors", "Destino": "Video Games",
         "Aristas": 214,  "Peso Total": 432},
        {"Origen": "Video Games", "Destino": "Sports & Outdoors",
         "Aristas": 183,  "Peso Total": 366},
        {"Origen": "Toys & Games", "Destino": "Video Games",
         "Aristas": 156,  "Peso Total": 313},
    ])
    st.dataframe(df_aff, use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────────────────────────
# TAB 3 — Top Productos
# ──────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("### 🏆 Top Productos por Categoría")
    st.caption("Ordenados por Bayesian Score — pondera rating y volumen de reseñas")

    col_toys, col_sports, col_vg = st.columns(3)

    categories = [
        (col_toys,   "🧸 Toys & Games",     "¿Cuáles son los mejores juguetes?"),
        (col_sports, "🏃 Sports & Outdoors", "¿Qué productos de deportes son los más valorados?"),
        (col_vg,     "🎮 Video Games",       "¿Cuáles son los mejores videojuegos?"),
    ]

    for col, title, question_cat in categories:
        with col:
            st.markdown(f"#### {title}")
            if st.button(f"Cargar {title}", key=f"btn_{title}",
                         use_container_width=True):
                with st.spinner("Consultando..."):
                    body = call_api(question_cat)

                if "error" in body:
                    st.error(body["error"])
                else:
                    context = body.get("context", "")
                    rows    = []
                    for line in context.split("\n"):
                        if "Título:" in line and "Score" in line:
                            try:
                                parts  = {p.split(":")[0].strip(): ":".join(p.split(":")[1:]).strip()
                                          for p in line.split("|")}
                                titulo = parts.get("Título", "N/A")[:40] + "..."
                                score  = parts.get("Score bayesiano", "N/A")
                                stars  = parts.get("Avg stars", "N/A")
                                revs   = parts.get("Reviews", "N/A")
                                rows.append({
                                    "Producto": titulo,
                                    "Score": score,
                                    "⭐": stars,
                                    "Reviews": revs
                                })
                            except Exception:
                                continue

                    if rows:
                        st.dataframe(
                            pd.DataFrame(rows),
                            use_container_width=True,
                            hide_index=True
                        )

                    with st.expander("🤖 Respuesta Bedrock"):
                        st.markdown(body.get("answer", ""))

# ══════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════
st.divider()
st.markdown("""
<div style="text-align:center; color:#444; font-size:0.8rem; padding:1rem 0">
  G5 SOT · Neo4j AuraDB · Amazon Bedrock · AWS Lambda · API Gateway · Glue · Athena<br>
  190,750 reseñas · 107,021 productos · 3 categorías · Bayesian Score
</div>
""", unsafe_allow_html=True)
