import pandas as pd
from openai import OpenAI
from tqdm import tqdm



df = pd.read_pickle("cursos_dataframe_agrupado.pkl")

print(f"🟢 Cursos a procesar: {len(df)}")




client = OpenAI(api_key="")   

EMBED_MODEL = "text-embedding-3-large"



# FUNCIÓN PARA GENERAR EMBEDDINGS


def get_embedding(text):
    text = text.replace("\n", " ").strip()
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=text
    )
    return response.data[0].embedding



embeddings = []

print("\n🔄 Generando embeddings por curso...\n")

for text in tqdm(df["textForEmbedding"], desc="Embedding cursos"):
    try:
        emb = get_embedding(text)
    except Exception as e:
        print("❌ Error generando embedding:", e)
        emb = []
    embeddings.append(emb)

df["embedding"] = embeddings




df.to_pickle("cursos_embeddings.pkl")    
df.to_csv("cursos_embeddings.csv", index=False, encoding="utf-8")

print("\n✅ Embeddings generados con éxito.")
print("   → cursos_embeddings.pkl (recomendado para uso posterior)")
print("   → cursos_embeddings.csv (para revisar en Excel)\n")
