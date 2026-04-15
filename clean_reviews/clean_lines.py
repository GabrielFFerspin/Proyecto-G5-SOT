import pandas as pd
import csv

INPUT = "reviews_en.csv"
OUTPUT = "reviews_clean_lines.csv"

# 1. Leer línea a línea y filtrar CSV malformado
good_rows = []
with open(INPUT, "r", encoding="utf-8", errors="ignore") as f:
    reader = csv.reader(f)
    header = next(reader)
    n_fields = len(header)

    good_rows.append(header)

    for row in reader:
        if len(row) == n_fields:
            good_rows.append(row)

# 2. Crear DataFrame limpio
df = pd.DataFrame(good_rows[1:], columns=header)

# 3. Limpieza extra (opcional, defensiva)
df["review_body"] = (
    df["review_body"]
    .astype(str)
    .str.replace('"', '""', regex=False)
)

# 4. Exportar CSV compatible con Neo4j
df.to_csv(
    OUTPUT,
    index=False,
    quotechar='"',
    quoting=csv.QUOTE_ALL
)

print(f"✅ CSV limpio generado: {OUTPUT}")
print(f"Filas finales: {len(df)}")