from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
from typing import List, Dict, Any
from app.services.embedding_model import EMBEDDING_MODEL
from app.services.response_synthesis_service import synthesize_answer
from app.services.groq_service import run_groq_completion




class TelcelRAGService:

    def __init__(self, mongo_uri: str, db_name: str, collection_name: str):
        self.client = MongoClient(mongo_uri)
        self.col = self.client[db_name][collection_name]

    def search(self, query: str) -> List[Dict[str, Any]]:

        query_embedding = EMBEDDING_MODEL.encode(
            ["query: " + query],
            normalize_embeddings=True
        )[0]


        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": query_embedding.tolist(),
                    "numCandidates": 100,
                    "limit": 5
                }
            },
            {
                "$project": {
                    "titulo": 1,
                    "texto": 1,
                    "url": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]

        return list(self.col.aggregate(pipeline))
