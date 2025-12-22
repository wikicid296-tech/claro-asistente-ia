from typing import Dict, Any
import os

from app.agents.base_agent import BaseAgent
from app.agents.claro.country_detector import detect_country
from app.agents.claro.claro_collections import resolve_claro_collection
from app.services.generic_rag_service import GenericRAGService
from app.services.response_synthesis_service import synthesize_answer
from app.services.groq_service import get_groq_client, get_groq_api_key


class ClaroAgent(BaseAgent):

    def _resolve(self) -> Dict[str, Any]:
        from app.agents.claro.about_claro import CLARO_ABOUT_TEXT

        if self.user_message.strip().lower() in {
             "que es claro",
    "qué es claro",
    "que es claro?",
    "qué es claro?",

    # Información general
    "informacion sobre claro",
    "información sobre claro",
    "informacion de claro",
    "información de claro",
    "info sobre claro",
    "info de claro",

    # Descripciones / explicaciones
    "explicame que es claro",
    "explícame que es claro",
    "explicame claro",
    "explícame claro",
    "describe claro",
    "descripcion de claro",
    "descripción de claro",

    # Identidad corporativa
    "empresa claro",
    "claro empresa",
    "claro telecomunicaciones",
    "claro operador",
    "claro operadora",

    # Formas conversacionales
    "hablame de claro",
    "háblame de claro",
    "quiero saber que es claro",
    "quiero saber de claro",
    "dime que es claro",
    "dime sobre claro",

    # Con contexto de marca
    "que empresa es claro",
    "qué empresa es claro",
    "claro que es",
    "claro que hace",
    "claro que servicios ofrece"
        }:
            return {
                "response": CLARO_ABOUT_TEXT,
                "context": "📡 Claro",
            }

        # 1️⃣ Detectar país
        country = detect_country(self.user_message)

        if country == "unknown":
            return {
                "response": (
                    "¿Podrías indicarme el país de Claro al que te refieres? "
                    "Por ejemplo: Claro México, Claro Colombia, etc."
                ),
                "context": "📡 Claro",
            }

        # 2️⃣ Resolver colección
        collection = resolve_claro_collection(country)

        if not collection:
            return {
                "response": "No contamos con información de Claro para ese país.",
                "context": "📡 Claro",
            }

        # 3️⃣ Inicializar RAG
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise RuntimeError("MONGO_URI no está configurada")


        from app.agents.claro.claro_collections import resolve_claro_vector_config

        vector_config = resolve_claro_vector_config(country)

        if not vector_config:
            return {
                "response": "No contamos con información de Claro para ese país.",
                "context": "📡 Claro",
            }

        rag_service = GenericRAGService(
            mongo_uri=mongo_uri,
            db_name="claro_rag",
            collection_name=vector_config["collection"],
            vector_index=vector_config["vector_index"],
)

        # 4️⃣ Retrieval
        documents = rag_service.retrieve(
            query=self.user_message,
            k=5,
        )
        print("🌍 País detectado:", country)
        print("📦 Colección resuelta:", collection)
        print("📄 Docs recuperados:", len(documents))
        if not documents:
            return {
                "response": (
                    "No encontré información relevante de Claro para tu consulta."
                ),
                "context": f"📡 Claro {country.upper()}",
            }


        # 5️⃣ Síntesis (reuse Groq)
        groq_client = get_groq_client()
        groq_api_key = get_groq_api_key()

        synthesized = synthesize_answer(
            user_question=self.user_message,
            documents=documents,
            domain_name=f"Claro {country.upper()}",
            groq_client=groq_client,
            groq_api_key=groq_api_key,
        )

        return {
            "response": synthesized["response"],
            "relevant_urls": synthesized.get("relevant_urls", []),
            "context": f"📡 Claro {country.upper()}",
        }
