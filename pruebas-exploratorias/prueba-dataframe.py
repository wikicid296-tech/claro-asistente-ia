import pandas as pd
from bs4 import BeautifulSoup
import json

# =============================================================
# 1. Cargar archivo JSON grande desde disco
# =============================================================

# Ruta al archivo JSON
input_file = "cursos_response.json"

# Abrir y cargar
with open(input_file, "r", encoding="utf-8") as f:
    api_response = json.load(f)   # api_response será una lista de dicts


# =============================================================
# 2. Función utilitaria para limpiar HTML en resourceDescription
# =============================================================

# Función robusta para limpiar HTML
def clean_html(html_text):
    if not isinstance(html_text, str):
        return ""
    return BeautifulSoup(html_text, "html.parser").get_text().strip()

# Aplicar limpieza


# =============================================================
# 3. Convertir a DataFrame y normalizar
# =============================================================

df = pd.DataFrame(api_response)

# Crear columna limpia de descripción
df["resourceDescriptionClean"] = df["resourceDescription"].apply(clean_html)

# Reemplazar nulos por vacío
df = df.fillna("")


# =============================================================
# 4. Preparar texto para embeddings
# =============================================================

df["textForEmbedding"] = (
    df["courseName"].astype(str)
    + " - "
    + df["resourceName"].astype(str)
    + ". "
    + df["resourceDescriptionClean"].astype(str)
)


# =============================================================
# 5. Reordenar columnas para limpieza
# =============================================================

df = df[
    [
        "courseId",
        "courseName",
        "resourceName",
        "resourceDescriptionClean",
        "resourceRedirection",
        "resourcePoster",
        "textForEmbedding",
    ]
]


# =============================================================
# 6. Imprimir primeras filas
# =============================================================

print(df.head())

# =============================================================
# 7. (Opcional) Guardar DataFrame a CSV
# =============================================================

df.to_csv("cursos_dataframe.csv", index=False, encoding="utf-8")
print("Archivo 'cursos_dataframe.csv' generado correctamente.")
