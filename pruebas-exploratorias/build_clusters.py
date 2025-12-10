import json
import ast
import numpy as np
import pandas as pd
from collections import Counter
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize


EMBED_COL = "embedding"
ID_COL = "courseId"
NAME_COL = "courseName"

INPUT_CSV = "cursos_embeddings.csv"
OUTPUT_CSV = "courses_with_clusters.csv"
OUTPUT_NPZ = "courses_cluster_pack.npz"

K = 25
RANDOM_STATE = 42


def robust_read_csv(path: str) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "latin1"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def parse_embedding(value):
    """
    Devuelve:
      - list[float] si es válido
      - None si está vacío/NaN/dañado
    """
    if value is None:
        return None

    # Pandas NaN
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, list):
        return value if len(value) > 0 else None

    if not isinstance(value, str):
        return None

    s = value.strip()
    if not s or s.lower() in ("nan", "none", "null"):
        return None

    # Intento JSON
    try:
        obj = json.loads(s)
        if isinstance(obj, list) and len(obj) > 0:
            return obj
    except Exception:
        pass

    # Fallback seguro
    try:
        obj = ast.literal_eval(s)
        if isinstance(obj, list) and len(obj) > 0:
            return obj
    except Exception:
        return None

    return None


def main():
    df = robust_read_csv(INPUT_CSV)

    if EMBED_COL not in df.columns:
        raise SystemExit(f"No existe la columna '{EMBED_COL}' en el CSV.")

    # Parse embeddings
    parsed = df[EMBED_COL].apply(parse_embedding)

    # Calcula longitudes válidas
    lengths = [len(v) for v in parsed if isinstance(v, list)]
    if not lengths:
        raise SystemExit("No hay embeddings válidos para clusterizar.")

    # Usa la dimensión más común
    dim_counts = Counter(lengths)
    target_dim, target_count = dim_counts.most_common(1)[0]

    print(f"Dimensión más común detectada: {target_dim} (n={target_count})")
    if len(dim_counts) > 1:
        print("Otras dimensiones encontradas:", dict(dim_counts))

    # Filtro filas válidas y consistentes
    mask_valid = parsed.apply(lambda v: isinstance(v, list) and len(v) == target_dim)
    df_clean = df[mask_valid].copy()
    embeddings = parsed[mask_valid].tolist()

    print(f"Filas totales: {len(df)}")
    print(f"Filas con embedding válido y consistente: {len(df_clean)}")
    print(f"Filas descartadas: {len(df) - len(df_clean)}")

    # Construye matriz
    X = np.array(embeddings, dtype=np.float32)
    Xn = normalize(X)

    # KMeans
    km = KMeans(n_clusters=K, random_state=RANDOM_STATE, n_init="auto")
    labels = km.fit_predict(Xn)

    df_clean["cluster"] = labels.astype(int)

    # Guarda CSV limpio con cluster
    df_clean.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

    # Pack de inferencia
    ids = df_clean[ID_COL].astype(str).to_numpy()
    names = df_clean[NAME_COL].astype(str).to_numpy() if NAME_COL in df_clean.columns else np.array([""] * len(df_clean))

    np.savez(
        OUTPUT_NPZ,
        ids=ids,
        names=names,
        X=Xn.astype(np.float32),
        labels=labels.astype(np.int32),
        centroids=km.cluster_centers_.astype(np.float32),
        k=np.array([K], dtype=np.int32),
        dim=np.array([target_dim], dtype=np.int32),
    )

    print(f"OK. Clusters guardados en: {OUTPUT_CSV}")
    print(f"Pack guardado en: {OUTPUT_NPZ}")


if __name__ == "__main__":
    main()
