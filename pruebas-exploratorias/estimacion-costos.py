import pandas as pd
import tiktoken

df = pd.read_pickle("cursos_dataframe_agrupado.pkl")

encoding = tiktoken.encoding_for_model("text-embedding-3-large")

df["tokens"] = df["textForEmbedding"].apply(lambda t: len(encoding.encode(t)))

total_tokens = df["tokens"].sum()

price_per_million = 0.13  # USD
estimated_cost = (total_tokens / 1_000_000) * price_per_million

print("Cursos:", len(df))
print("Tokens totales:", total_tokens)
print("Costo estimado: $", round(estimated_cost, 5), "USD")
