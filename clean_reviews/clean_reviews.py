
import pandas as pd

df = pd.read_csv(
    "reviews_en.csv",
    engine="python",
    on_bad_lines="skip"
)

# Opcional: limpiar comillas raras
df["review_body"] = df["review_body"].str.replace('"', '""', regex=False)

df.to_csv("reviews_clean.csv", index=False, quotechar='"', quoting=1)