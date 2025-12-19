from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from openai import OpenAI
import os


class TelcelRAGService:
    """
    Servicio de retrieval RAG para Telcel.

    Responsabilidad ÚNICA:
    - Vectorizar la query (OpenAI)
    - Ejecutar MongoDB Vector Search
    - Devolver documentos relevantes

    NO sanitiza.
    NO sintetiza.
    NO genera respuestas finales.
    """

    def __init__(
        self,
        mongo_uri: str,
        db_name: str ="telcel_rag",
        collection_name: str = 'embeddings2',
        *,
        openai_model: str = "text-embedding-3-large",
        vector_index: str = "vector_index2",
    ):
        self.mongo_client = MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000
    )
        self.collection = self.mongo_client[db_name][collection_name]

        self.openai_client = OpenAI(api_key= os.getenv("OPENAI_API_KEY"))
        self.openai_model = openai_model
        self.vector_index = vector_index

    # --------------------------------------------------
    # Embedding de la query (OpenAI)
    # --------------------------------------------------

    def embed_query(self, query: str) -> List[float]:
        response = self.openai_client.embeddings.create(
            model=self.openai_model,
            input=query
        )

        # Forzamos list[float] (Pylance + Mongo friendly)
        return list(response.data[0].embedding)

    # --------------------------------------------------
    # Vector Search
    # --------------------------------------------------

    def retrieve(
    self,
    *,
    query: str,
    datasets: Optional[List[str]] = None,
    k: int = 5,
    num_candidates: int = 40,  # 🔒 Render-safe
    ) -> List[Dict[str, Any]]:
        """
        Recupera documentos relevantes desde MongoDB usando Vector Search.

        - SOLO filtra por campos garantizados (dataset)
        - El resto del refinamiento se hace vía reranking
        """

        # 1️⃣ Embedding de la query
        query_embedding = self.embed_query(query)

        # 2️⃣ Vector Search base (ligero)
        vector_search = {
            "$vectorSearch": {
                "index": self.vector_index,
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": num_candidates,
                "limit": k,
            }
        }

        # 3️⃣ Filtro SEGURO (solo dataset)
        if datasets:
            vector_search["$vectorSearch"]["filter"] = {
                "dataset": {"$in": datasets}
            }

        pipeline = [
            vector_search,
            {
                "$project": {
                    "_id": 1,
                    "titulo": 1,
                    "texto": 1,
                    "url": 1,
                    "categoria": 1,
                    "subtipo": 1,
                    "dataset": 1,
                    "es_temporal": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            }
        ]

        # 4️⃣ Ejecución protegida
        try:
            docs = list(self.collection.aggregate(pipeline))
        except Exception as e:
            # ⚠️ Nunca mates el worker
            print(f"[TelcelRAGService] Error en vector search: {e}")
            return []

        return docs
