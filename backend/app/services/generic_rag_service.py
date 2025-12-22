from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from openai import OpenAI
import os


class GenericRAGService:

    def __init__(
        self,
        mongo_uri: str,
        db_name: str,
        collection_name: str,
        *,
        vector_index: str = "vector_index",
        openai_model: str = "text-embedding-3-large",
    ):
        self.mongo_client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
        )

        self.collection = self.mongo_client[db_name][collection_name]
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.openai_model = openai_model
        self.vector_index = vector_index

    def embed_query(self, query: str) -> List[float]:
        response = self.openai_client.embeddings.create(
            model=self.openai_model,
            input=query,
        )
        return list(response.data[0].embedding)

    def retrieve(
        self,
        *,
        query: str,
        k: int = 5,
        num_candidates: int = 40,
    ) -> List[Dict[str, Any]]:

        query_embedding = self.embed_query(query)
        print()

        pipeline = [
            {
                "$vectorSearch": {
                    "index": self.vector_index,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": num_candidates,
                    "limit": k,
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "titulo": 1,
                    "texto": 1,
                    "url": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        try:
            return list(self.collection.aggregate(pipeline))
        except Exception as e:
            print(f"[GenericRAGService] Vector search error: {e}")
            return []
