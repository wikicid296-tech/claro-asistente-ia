import json
import pandas as pd
from bs4 import BeautifulSoup

# =============================================================
# 1. CARGAR ARCHIVO JSON
# =============================================================

input_file = "cursos_response.json"

with open(input_file, "r", encoding="utf-8") as f:
    api_response = json.load(f)

df = pd.DataFrame(api_response)


# =============================================================
# 2. LIMPIAR HTML DEL CAMPO resourceDescription
# =============================================================

def clean_html(html_text):
    if not isinstance(html_text, str):
        return ""
    return BeautifulSoup(html_text, "html.parser").get_text().strip()

df["resourceDescriptionClean"] = df["resourceDescription"].apply(clean_html)
df = df.fillna("")


# =============================================================
# 3. AGRUPAR POR CURSO (courseId + courseName)
#    - Lista de recursos por curso
#    - Descripción unificada del curso
# =============================================================

grouped = df.groupby(["courseId", "courseName"]).agg({
    "resourceName": lambda x: list(x),                        # lista de nombres de recursos
    "resourceDescriptionClean": lambda x: " ".join(x),        # unir todas las descripciones
}).reset_index()


# =============================================================
# 4. CONSTRUIR TEXTO COMPLETO PARA EMBEDDINGS POR CURSO
# =============================================================

def build_course_text(row):
    recursos = "\n - ".join(row["resourceName"])  # listado de temas
    descripcion = row["resourceDescriptionClean"]

    return (
        f"{row['courseName']}\n\n"
        f"Temas del curso:\n - {recursos}\n\n"
        f"Descripción general del curso:\n{descripcion}"
    )

grouped["textForEmbedding"] = grouped.apply(build_course_text, axis=1)


# =============================================================
# 5. MOSTRAR EJEMPLOS DEL NUEVO DATAFRAME
# =============================================================

print("\n🟢 DataFrame agrupado por curso:")
print(grouped.head())


# =============================================================
# 6. GUARDAR RESULTADO
# =============================================================

grouped.to_pickle("cursos_dataframe_agrupado.pkl")
grouped.to_csv("cursos_dataframe_agrupado.csv", index=False, encoding="utf-8")

print("\n✅ DataFrame agrupado creado correctamente.")
print("   → cursos_dataframe_agrupado.pkl")
print("   → cursos_dataframe_agrupado.csv\n")
