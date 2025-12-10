import pandas as pd
from openai import OpenAI
import json
import math
import os

client = OpenAI(api_key="")  
VECTOR_STORE_ID = ""    

df = pd.read_pickle("cursos_dataframe_agrupado.pkl")
print(f"🟢 Cursos a procesar: {len(df)}")



batch_size = 100
num_batches = math.ceil(len(df) / batch_size)

for batch_idx in range(num_batches):
    start = batch_idx * batch_size
    end = start + batch_size
    df_batch = df.iloc[start:end]

    print(f"\n📦 Subiendo batch {batch_idx + 1}/{num_batches} ({len(df_batch)} cursos)")

    # Crear un archivo JSON válido
    batch_docs = []

    for _, row in df_batch.iterrows():
        batch_docs.append({
            "id": f"curso-{row['courseId']}-{batch_idx}",
            "text": row["textForEmbedding"],
            "metadata": {
                "courseId": int(row["courseId"]),
                "courseName": row["courseName"],
                "num_recursos": len(row["resourceName"])
            }
        })

    json_path = f"cursos_batch_{batch_idx + 1}.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(batch_docs, f, ensure_ascii=False)

    # Subir archivo JSON al vector store
    batch = client.vector_stores.file_batches.upload_and_poll(
        vector_store_id=VECTOR_STORE_ID,
        files=[open(json_path, "rb")]
    )

    print(f"   ✔ Batch {batch_idx + 1} subido correctamente.")

    os.remove(json_path)

print("\n🎉 TODOS LOS BATCHES FUERON SUBIDOS EXITOSAMENTE 🎉")
print("Vector Store listo:", VECTOR_STORE_ID)
