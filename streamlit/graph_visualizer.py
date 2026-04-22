# graph_visualizer.py
# Proyecto G5 SOT — Visualización de subgrafo Neo4j con pyvis
# Conecta directamente a AuraDB y renderiza el subgrafo
# correspondiente a cada intent en Streamlit

from neo4j import GraphDatabase
from pyvis.network import Network
import json

# ── Colores por label de nodo ─────────────────────────────────────
NODE_STYLES = {
    "Product":  {"color": "#4ec9b0", "size": 20},   # teal
    "Category": {"color": "#e67e22", "size": 45},   # naranja grande
    "Reviewer": {"color": "#9b59b6", "size": 10},   # morado pequeño
}

# ── Colores por tipo de relación ──────────────────────────────────
EDGE_COLORS = {
    "CO_PURCHASED": "#4ec9b0",
    "BELONGS_TO":   "#e67e22",
    "REVIEWED":     "#9b59b6",
    "ACTIVE_IN":    "#3498db",
}

# ── Opciones de física del grafo ──────────────────────────────────
PHYSICS_OPTIONS = """
{
  "physics": {
    "enabled": true,
    "forceAtlas2Based": {
      "gravitationalConstant": -50,
      "centralGravity": 0.01,
      "springLength": 120,
      "springConstant": 0.08,
      "damping": 0.4,
      "avoidOverlap": 0.8
    },
    "solver": "forceAtlas2Based",
    "stabilization": {
      "enabled": true,
      "iterations": 150
    }
  },
  "edges": {
    "smooth": {
      "type": "continuous"
    },
    "arrows": {
      "to": {
        "enabled": true,
        "scaleFactor": 0.5
      }
    }
  },
  "interaction": {
    "hover": true,
    "tooltipDelay": 100,
    "zoomView": true,
    "dragView": true
  }
}
"""

# ══════════════════════════════════════════════════════════════════
# QUERIES POR INTENT
# ══════════════════════════════════════════════════════════════════

# top_rated / generic — top productos por bayesian_score
Q_SUBGRAPH_TOP_RATED = """
MATCH (p:Product)-[:BELONGS_TO]->(c:Category)
WHERE p.review_count >= 5
RETURN p.product_id    AS pid,
       p.title         AS title,
       p.bayesian_score AS score,
       p.avg_stars     AS stars,
       p.review_count  AS reviews,
       p.category      AS cat_name,
       c.name          AS category,
       'BELONGS_TO'    AS rel_type,
       null            AS pid2,
       null            AS title2,
       null            AS weight
ORDER BY p.bayesian_score DESC
LIMIT 15
"""

# copurchase / similar_to CON product_id
Q_SUBGRAPH_COPURCHASE = """
MATCH (p1:Product {product_id: $pid})-[co:CO_PURCHASED]-(p2:Product)
MATCH (p1)-[:BELONGS_TO]->(c1:Category)
MATCH (p2)-[:BELONGS_TO]->(c2:Category)
RETURN p1.product_id    AS pid,
       p1.title         AS title,
       p1.bayesian_score AS score,
       p1.avg_stars     AS stars,
       p1.review_count  AS reviews,
       c1.name          AS category,
       p2.product_id    AS pid2,
       p2.title         AS title2,
       p2.bayesian_score AS score2,
       p2.avg_stars     AS stars2,
       p2.review_count  AS reviews2,
       c2.name          AS category2,
       co.weight        AS weight,
       co.cross_cat     AS cross_cat,
       'CO_PURCHASED'   AS rel_type
ORDER BY co.weight DESC
LIMIT 15
"""

# copurchase SIN product_id — pares globales
Q_SUBGRAPH_COPURCHASE_GENERIC = """
MATCH (p1:Product)-[co:CO_PURCHASED]->(p2:Product)
MATCH (p1)-[:BELONGS_TO]->(c1:Category)
MATCH (p2)-[:BELONGS_TO]->(c2:Category)
RETURN p1.product_id    AS pid,
       p1.title         AS title,
       p1.bayesian_score AS score,
       p1.avg_stars     AS stars,
       p1.review_count  AS reviews,
       c1.name          AS category,
       p2.product_id    AS pid2,
       p2.title         AS title2,
       p2.bayesian_score AS score2,
       p2.avg_stars     AS stars2,
       p2.review_count  AS reviews2,
       c2.name          AS category2,
       co.weight        AS weight,
       co.cross_cat     AS cross_cat,
       'CO_PURCHASED'   AS rel_type
ORDER BY co.weight DESC
LIMIT 10
"""

# category_affinity — co-compras cross-categoría
Q_SUBGRAPH_AFFINITY = """
MATCH (p1:Product)-[co:CO_PURCHASED {cross_cat: true}]->(p2:Product)
MATCH (p1)-[:BELONGS_TO]->(c1:Category)
MATCH (p2)-[:BELONGS_TO]->(c2:Category)
RETURN p1.product_id    AS pid,
       p1.title         AS title,
       p1.bayesian_score AS score,
       p1.avg_stars     AS stars,
       p1.review_count  AS reviews,
       c1.name          AS category,
       p2.product_id    AS pid2,
       p2.title         AS title2,
       p2.bayesian_score AS score2,
       p2.avg_stars     AS stars2,
       p2.review_count  AS reviews2,
       c2.name          AS category2,
       co.weight        AS weight,
       true             AS cross_cat,
       'CO_PURCHASED'   AS rel_type
ORDER BY co.weight DESC
LIMIT 20
"""

# top_by_category — top productos de una categoría
Q_SUBGRAPH_BY_CATEGORY = """
MATCH (p:Product)-[:BELONGS_TO]->(c:Category {name: $cat})
WHERE p.review_count >= 3
RETURN p.product_id    AS pid,
       p.title         AS title,
       p.bayesian_score AS score,
       p.avg_stars     AS stars,
       p.review_count  AS reviews,
       c.name          AS category,
       'BELONGS_TO'    AS rel_type,
       null AS pid2, null AS title2,
       null AS weight
ORDER BY p.bayesian_score DESC
LIMIT 15
"""

# combined_score — bayesian + co-compra
Q_SUBGRAPH_COMBINED = """
MATCH (p:Product)-[:BELONGS_TO]->(c:Category)
WHERE p.review_count >= 5
OPTIONAL MATCH (p)-[co:CO_PURCHASED]-(p2:Product)
OPTIONAL MATCH (p2)-[:BELONGS_TO]->(c2:Category)
RETURN p.product_id    AS pid,
       p.title         AS title,
       p.bayesian_score AS score,
       p.avg_stars     AS stars,
       p.review_count  AS reviews,
       c.name          AS category,
       p2.product_id   AS pid2,
       p2.title        AS title2,
       p2.bayesian_score AS score2,
       c2.name         AS category2,
       co.weight       AS weight,
       'CO_PURCHASED'  AS rel_type
ORDER BY p.bayesian_score DESC
LIMIT 10
"""


# ══════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL
# ══════════════════════════════════════════════════════════════════

class GraphVisualizer:

    def __init__(self, uri: str, user: str, password: str):
        # Conectar a Neo4j AuraDB directamente
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.driver.verify_connectivity()

    def close(self):
        # Cerrar conexión con Neo4j
        if self.driver:
            self.driver.close()

    def _new_network(self) -> Network:
        # Crear red pyvis con tema oscuro
        net = Network(
            height="520px",
            width="100%",
            bgcolor="#0f1117",
            font_color="#d4d4d4",
            notebook=False,
            directed=True,
        )
        net.set_options(PHYSICS_OPTIONS)
        return net

    def _add_product_node(self, net: Network, pid: str, title: str,
                          score: float, stars: float,
                          reviews: int, category: str):
        # Añadir nodo :Product si no existe ya
        if pid in [n["id"] for n in net.nodes]:
            return
        short_title = (title[:35] + "...") if title and len(title) > 35 else (title or pid)
        tooltip = (
            f"📦 {title or pid}\n"
            f"🏷️ {category}\n"
            f"⭐ {round(stars or 0, 2)} | 📊 Score: {round(score or 0, 4)}\n"
            f"💬 {reviews or 0} reseñas"
        )
        style = NODE_STYLES["Product"]
        net.add_node(
            pid,
            label=short_title,
            title=tooltip,
            color=style["color"],
            size=style["size"],
            font={"color": "#d4d4d4", "size": 11},
            shape="dot",
        )

    def _add_category_node(self, net: Network, category: str):
        # Añadir nodo :Category si no existe ya
        if not category:
            return
        node_id = f"cat_{category}"
        if node_id in [n["id"] for n in net.nodes]:
            return
        labels_map = {
            "Toys_and_Games":      "🧸 Toys",
            "Sports_and_Outdoors": "🏃 Sports",
            "Video_Games":         "🎮 Video Games",
        }
        style = NODE_STYLES["Category"]
        net.add_node(
            node_id,
            label=labels_map.get(category, category),
            title=f"📂 Categoría: {category}",
            color=style["color"],
            size=style["size"],
            font={"color": "#ffffff", "size": 14, "bold": True},
            shape="diamond",
        )

    def _add_belongs_to(self, net: Network, pid: str, category: str):
        # Añadir arista BELONGS_TO entre Product y Category
        if not pid or not category:
            return
        cat_id = f"cat_{category}"
        edge_id = f"{pid}__{cat_id}"
        existing = [(e["from"], e["to"]) for e in net.edges]
        if (pid, cat_id) not in existing:
            net.add_edge(
                pid, cat_id,
                color=EDGE_COLORS["BELONGS_TO"],
                width=1,
                title="BELONGS_TO",
                arrows="to",
            )

    def _add_copurchase_edge(self, net: Network, pid1: str,
                              pid2: str, weight: int):
        # Añadir arista CO_PURCHASED con grosor proporcional al peso
        if not pid1 or not pid2:
            return
        existing = [(e["from"], e["to"]) for e in net.edges]
        if (pid1, pid2) not in existing and (pid2, pid1) not in existing:
            w = min(int(weight or 1), 10)  # max grosor = 10
            net.add_edge(
                pid1, pid2,
                color=EDGE_COLORS["CO_PURCHASED"],
                width=w,
                title=f"CO_PURCHASED\nPeso: {weight}",
                arrows="to",
            )

    def _build_simple_graph(self, records) -> Network:
        # Construye grafo para top_rated / top_by_category
        net = self._new_network()
        for r in records:
            pid      = r.get("pid")
            title    = r.get("title")
            score    = r.get("score") or 0
            stars    = r.get("stars") or 0
            reviews  = r.get("reviews") or 0
            category = r.get("category")
            if pid:
                self._add_product_node(net, pid, title,
                                       score, stars, reviews, category)
            if category:
                self._add_category_node(net, category)
            if pid and category:
                self._add_belongs_to(net, pid, category)
        return net

    def _build_copurchase_graph(self, records) -> Network:
        # Construye grafo para copurchase / similar_to / affinity
        net = self._new_network()
        for r in records:
            pid1     = r.get("pid")
            title1   = r.get("title")
            score1   = r.get("score") or 0
            stars1   = r.get("stars") or 0
            reviews1 = r.get("reviews") or 0
            cat1     = r.get("category")

            pid2     = r.get("pid2")
            title2   = r.get("title2")
            score2   = r.get("score2") or 0
            stars2   = r.get("stars2") or 0
            reviews2 = r.get("reviews2") or 0
            cat2     = r.get("category2")
            weight   = r.get("weight") or 1

            # Nodo producto 1
            if pid1:
                self._add_product_node(net, pid1, title1,
                                       score1, stars1, reviews1, cat1)
            # Nodo producto 2
            if pid2:
                self._add_product_node(net, pid2, title2,
                                       score2, stars2, reviews2, cat2)
            # Categorías
            if cat1:
                self._add_category_node(net, cat1)
            if cat2:
                self._add_category_node(net, cat2)
            # BELONGS_TO
            if pid1 and cat1:
                self._add_belongs_to(net, pid1, cat1)
            if pid2 and cat2:
                self._add_belongs_to(net, pid2, cat2)
            # CO_PURCHASED
            if pid1 and pid2:
                self._add_copurchase_edge(net, pid1, pid2, weight)
        return net

    def get_subgraph(self, intent: str,
                     entity_id: str = None,
                     category: str = None) -> str:
        # Seleccionar query según intent y construir grafo
        with self.driver.session(database="e5d261e6") as session:

            if intent in ("copurchase", "similar_to") and entity_id:
                records = session.run(
                    Q_SUBGRAPH_COPURCHASE, {"pid": entity_id}
                ).data()
                net = self._build_copurchase_graph(records)

            elif intent in ("copurchase", "similar_to") and not entity_id:
                records = session.run(Q_SUBGRAPH_COPURCHASE_GENERIC).data()
                net = self._build_copurchase_graph(records)

            elif intent == "category_affinity":
                records = session.run(Q_SUBGRAPH_AFFINITY).data()
                net = self._build_copurchase_graph(records)

            elif intent == "top_by_category" and category:
                records = session.run(
                    Q_SUBGRAPH_BY_CATEGORY, {"cat": category}
                ).data()
                net = self._build_simple_graph(records)

            elif intent == "combined_score":
                records = session.run(Q_SUBGRAPH_COMBINED).data()
                net = self._build_copurchase_graph(records)

            else:
                # top_rated, generic, fallback
                records = session.run(Q_SUBGRAPH_TOP_RATED).data()
                net = self._build_simple_graph(records)

        return net.generate_html()


# ══════════════════════════════════════════════════════════════════
# FUNCIÓN STANDALONE — para usar desde app.py
# ══════════════════════════════════════════════════════════════════

def render_subgraph(intent: str, entity_id: str = None,
                    category: str = None,
                    uri: str = "",
                    user: str = "e5d261e6",
                    password: str = "") -> str:
    """
    Crea GraphVisualizer, genera el subgrafo HTML y cierra conexión.
    Devuelve el HTML del grafo o un mensaje de error.
    """
    try:
        viz = GraphVisualizer(uri, user, password)
        html = viz.get_subgraph(intent, entity_id, category)
        viz.close()
        return html
    except Exception as e:
        return f"""
        <div style="color:#e74c3c; padding:1rem; text-align:center;
                    font-family:monospace; background:#1e1e2e;
                    border-radius:8px;">
          ❌ Error conectando a Neo4j: {str(e)}
        </div>
        """
