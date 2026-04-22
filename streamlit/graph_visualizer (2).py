# graph_visualizer.py
# Proyecto G5 SOT — Visualización subgrafo Neo4j con pyvis

from neo4j import GraphDatabase
from pyvis.network import Network

NODE_STYLES = {
    "Product":  {"color": "#4ec9b0", "size": 20},
    "Category": {"color": "#e67e22", "size": 45},
    "Reviewer": {"color": "#9b59b6", "size": 10},
}
EDGE_COLORS = {
    "CO_PURCHASED": "#4ec9b0",
    "BELONGS_TO":   "#e67e22",
    "REVIEWED":     "#9b59b6",
    "ACTIVE_IN":    "#3498db",
}
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
    "stabilization": {"enabled": true, "iterations": 150}
  },
  "edges": {
    "smooth": {"type": "continuous"},
    "arrows": {"to": {"enabled": true, "scaleFactor": 0.5}}
  },
  "interaction": {
    "hover": true, "tooltipDelay": 100,
    "zoomView": true, "dragView": true
  }
}
"""

Q_SUBGRAPH_TOP_RATED = """
MATCH (p:Product)-[:BELONGS_TO]->(c:Category)
WHERE p.review_count >= 5
RETURN p.product_id AS pid, p.title AS title,
       p.bayesian_score AS score, p.avg_stars AS stars,
       p.review_count AS reviews, c.name AS category,
       null AS pid2, null AS title2, null AS score2,
       null AS stars2, null AS reviews2, null AS category2,
       null AS weight
ORDER BY p.bayesian_score DESC LIMIT 15
"""

Q_SUBGRAPH_COPURCHASE = """
MATCH (p1:Product {product_id: $pid})-[co:CO_PURCHASED]-(p2:Product)
MATCH (p1)-[:BELONGS_TO]->(c1:Category)
MATCH (p2)-[:BELONGS_TO]->(c2:Category)
RETURN p1.product_id AS pid, p1.title AS title,
       p1.bayesian_score AS score, p1.avg_stars AS stars,
       p1.review_count AS reviews, c1.name AS category,
       p2.product_id AS pid2, p2.title AS title2,
       p2.bayesian_score AS score2, p2.avg_stars AS stars2,
       p2.review_count AS reviews2, c2.name AS category2,
       co.weight AS weight
ORDER BY co.weight DESC LIMIT 15
"""

Q_SUBGRAPH_COPURCHASE_GENERIC = """
MATCH (p1:Product)-[co:CO_PURCHASED]->(p2:Product)
MATCH (p1)-[:BELONGS_TO]->(c1:Category)
MATCH (p2)-[:BELONGS_TO]->(c2:Category)
RETURN p1.product_id AS pid, p1.title AS title,
       p1.bayesian_score AS score, p1.avg_stars AS stars,
       p1.review_count AS reviews, c1.name AS category,
       p2.product_id AS pid2, p2.title AS title2,
       p2.bayesian_score AS score2, p2.avg_stars AS stars2,
       p2.review_count AS reviews2, c2.name AS category2,
       co.weight AS weight
ORDER BY co.weight DESC LIMIT 10
"""

Q_SUBGRAPH_AFFINITY = """
MATCH (p1:Product)-[co:CO_PURCHASED {cross_cat: true}]->(p2:Product)
MATCH (p1)-[:BELONGS_TO]->(c1:Category)
MATCH (p2)-[:BELONGS_TO]->(c2:Category)
RETURN p1.product_id AS pid, p1.title AS title,
       p1.bayesian_score AS score, p1.avg_stars AS stars,
       p1.review_count AS reviews, c1.name AS category,
       p2.product_id AS pid2, p2.title AS title2,
       p2.bayesian_score AS score2, p2.avg_stars AS stars2,
       p2.review_count AS reviews2, c2.name AS category2,
       co.weight AS weight
ORDER BY co.weight DESC LIMIT 20
"""

Q_SUBGRAPH_BY_CATEGORY = """
MATCH (p:Product)-[:BELONGS_TO]->(c:Category {name: $cat})
WHERE p.review_count >= 3
RETURN p.product_id AS pid, p.title AS title,
       p.bayesian_score AS score, p.avg_stars AS stars,
       p.review_count AS reviews, c.name AS category,
       null AS pid2, null AS title2, null AS score2,
       null AS stars2, null AS reviews2, null AS category2,
       null AS weight
ORDER BY p.bayesian_score DESC LIMIT 15
"""

Q_SUBGRAPH_COMBINED = """
MATCH (p:Product)-[:BELONGS_TO]->(c:Category)
WHERE p.review_count >= 5
OPTIONAL MATCH (p)-[co:CO_PURCHASED]-(p2:Product)
OPTIONAL MATCH (p2)-[:BELONGS_TO]->(c2:Category)
RETURN p.product_id AS pid, p.title AS title,
       p.bayesian_score AS score, p.avg_stars AS stars,
       p.review_count AS reviews, c.name AS category,
       p2.product_id AS pid2, p2.title AS title2,
       p2.bayesian_score AS score2, p2.avg_stars AS stars2,
       p2.review_count AS reviews2, c2.name AS category2,
       co.weight AS weight
ORDER BY p.bayesian_score DESC LIMIT 10
"""


class GraphVisualizer:

    def __init__(self, uri: str, user: str, password: str,
                 database: str = "e5d261e6"):
        self.database = database
        self.driver   = GraphDatabase.driver(uri, auth=(user, password))
        self.driver.verify_connectivity()

    def close(self):
        if self.driver:
            self.driver.close()

    def _new_network(self) -> Network:
        net = Network(
            height="520px", width="100%",
            bgcolor="#0f1117", font_color="#d4d4d4",
            notebook=False, directed=True,
        )
        net.set_options(PHYSICS_OPTIONS)
        return net

    def _add_product_node(self, net, pid, title, score, stars, reviews, category):
        if not pid:
            return
        if pid in [n["id"] for n in net.nodes]:
            return
        short   = (title[:35] + "...") if title and len(title) > 35 else (title or pid)
        tooltip = (
            f"📦 {title or pid}\n"
            f"🏷️ {category}\n"
            f"⭐ {round(stars or 0, 2)} | Score: {round(score or 0, 4)}\n"
            f"💬 {reviews or 0} reseñas"
        )
        s = NODE_STYLES["Product"]
        net.add_node(pid, label=short, title=tooltip,
                     color=s["color"], size=s["size"],
                     font={"color": "#d4d4d4", "size": 11}, shape="dot")

    def _add_category_node(self, net, category):
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
        s = NODE_STYLES["Category"]
        net.add_node(node_id, label=labels_map.get(category, category),
                     title=f"📂 Categoría: {category}",
                     color=s["color"], size=s["size"],
                     font={"color": "#ffffff", "size": 14}, shape="diamond")

    def _add_belongs_to(self, net, pid, category):
        if not pid or not category:
            return
        cat_id   = f"cat_{category}"
        existing = [(e["from"], e["to"]) for e in net.edges]
        if (pid, cat_id) not in existing:
            net.add_edge(pid, cat_id, color=EDGE_COLORS["BELONGS_TO"],
                         width=1, title="BELONGS_TO")

    def _add_copurchase_edge(self, net, pid1, pid2, weight):
        if not pid1 or not pid2:
            return
        existing = [(e["from"], e["to"]) for e in net.edges]
        if (pid1, pid2) not in existing and (pid2, pid1) not in existing:
            w = min(int(weight or 1), 10)
            net.add_edge(pid1, pid2, color=EDGE_COLORS["CO_PURCHASED"],
                         width=w, title=f"CO_PURCHASED | Peso: {weight}")

    def _build_simple_graph(self, records) -> Network:
        net = self._new_network()
        for r in records:
            pid = r.get("pid"); title = r.get("title")
            score = r.get("score") or 0; stars = r.get("stars") or 0
            reviews = r.get("reviews") or 0; category = r.get("category")
            self._add_product_node(net, pid, title, score, stars, reviews, category)
            self._add_category_node(net, category)
            self._add_belongs_to(net, pid, category)
        return net

    def _build_copurchase_graph(self, records) -> Network:
        net = self._new_network()
        for r in records:
            pid1 = r.get("pid"); title1 = r.get("title")
            score1 = r.get("score") or 0; stars1 = r.get("stars") or 0
            rev1 = r.get("reviews") or 0; cat1 = r.get("category")
            pid2 = r.get("pid2"); title2 = r.get("title2")
            score2 = r.get("score2") or 0; stars2 = r.get("stars2") or 0
            rev2 = r.get("reviews2") or 0; cat2 = r.get("category2")
            weight = r.get("weight") or 1
            self._add_product_node(net, pid1, title1, score1, stars1, rev1, cat1)
            self._add_product_node(net, pid2, title2, score2, stars2, rev2, cat2)
            self._add_category_node(net, cat1)
            self._add_category_node(net, cat2)
            self._add_belongs_to(net, pid1, cat1)
            self._add_belongs_to(net, pid2, cat2)
            self._add_copurchase_edge(net, pid1, pid2, weight)
        return net

    def get_subgraph(self, intent: str,
                     entity_id: str = None,
                     category:  str = None) -> str:
        with self.driver.session(database=self.database) as session:
            if intent in ("copurchase", "similar_to") and entity_id:
                records = session.run(Q_SUBGRAPH_COPURCHASE, {"pid": entity_id}).data()
                net = self._build_copurchase_graph(records)
            elif intent in ("copurchase", "similar_to"):
                records = session.run(Q_SUBGRAPH_COPURCHASE_GENERIC).data()
                net = self._build_copurchase_graph(records)
            elif intent == "category_affinity":
                records = session.run(Q_SUBGRAPH_AFFINITY).data()
                net = self._build_copurchase_graph(records)
            elif intent == "top_by_category" and category:
                records = session.run(Q_SUBGRAPH_BY_CATEGORY, {"cat": category}).data()
                net = self._build_simple_graph(records)
            elif intent == "combined_score":
                records = session.run(Q_SUBGRAPH_COMBINED).data()
                net = self._build_copurchase_graph(records)
            else:
                records = session.run(Q_SUBGRAPH_TOP_RATED).data()
                net = self._build_simple_graph(records)
        return net.generate_html()


def render_subgraph(intent:    str,
                    entity_id: str = None,
                    category:  str = None,
                    uri:       str = "",
                    user:      str = "e5d261e6",
                    password:  str = "",
                    database:  str = "e5d261e6") -> str:
    try:
        viz  = GraphVisualizer(uri, user, password, database)
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
