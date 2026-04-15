import pandas as pd
import csv

INPUT = "reviews_en.csv"
OUTPUT = "reviews_neo4j.tsv"

# Lee tolerante (para sobrevivir a filas corruptas)
df = pd.read_csv(
    INPUT,
    engine="python",
    on_bad_lines="skip"
)

# Asegura que existen estas columnas (ajusta si tu CSV usa otros nombres)
cols = ["review_id","stars","review_title","product_id","product_category","review_body","reviewer_id","language"]
df = df[[c for c in cols if c in df.columns]]

# Limpieza fuerte para evitar que Neo4j interprete comillas / saltos
text_cols = [c for c in ["review_title","review_body","product_category","language","product_id","review_id","reviewer_id"] if c in df.columns]
for c in text_cols:
    df[c] = (df[c].astype(str)
                  .str.replace("\r\n", " ", regex=False)
                  .str.replace("\n", " ", regex=False)
                  .str.replace("\r", " ", regex=False)
                  .str.replace("\t", " ", regex=False)
                  .str.replace('"', "", regex=False)   # clave: eliminar comillas
            )

# stars a entero si existe
if "stars" in df.columns:
    df["stars"] = pd.to_numeric(df["stars"], errors="coerce").fillna(0).astype(int)

# Exporta TSV sin quoting (y sin comillas)
df.to_csv(
    OUTPUT,
    sep="\t",
    index=False,
    quoting=csv.QUOTE_NONE,
    escapechar="\\"
)

print(f"✅ Generado {OUTPUT} con {len(df)} filas")