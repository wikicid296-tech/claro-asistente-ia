import os
from typing import Dict, Any, List

from app.services.telcel_rag_service import TelcelRAGService
from app.services.response_synthesis_service import synthesize_answer
from app.services.groq_service import get_groq_client, get_groq_api_key
from app.agents.telcel.about_telcel import TELCEL_ABOUT_TEXT


class TelcelAgent:
    """
    Agente conversacional dedicado a Telcel.

    Responsabilidades:
    - Resolver alias de marca (Claro México → Telcel)
    - Normalizar la query canónica
    - Ejecutar retrieval + síntesis
    - Emitir fallback guiado cuando no hay información
    - Permitir continuidad conversacional
    """

    def __init__(
        self,
        *,
        user_message: str,
        context: Dict[str, Any],
        intent: str = "telcel",
    ):
        self.user_message = user_message
        self.context = context or {}
        self.intent = intent

        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise RuntimeError("MONGO_URI no está configurada")

        self.telcel_rag = TelcelRAGService(
            mongo_uri=mongo_uri,
            db_name="telcel_rag",
            collection_name="embeddings2",
        )

        self.groq_client = get_groq_client()
        self.groq_api_key = get_groq_api_key()

    # --------------------------------------------------
    # Entry point
    # --------------------------------------------------

    def handle(self) -> Dict[str, Any]:
        """
        Punto único de entrada del agente.
        """

        # =====================================================
        # 0️⃣ Normalización inicial
        # =====================================================
        original_query = self.user_message.strip()
        canonical_query = original_query.lower()

        alias_prefix = ""
        context_label = "📱 Telcel"

        # =====================================================
        # 1️⃣ Resolver alias: Claro México → Telcel
        # =====================================================
        if "claro méxico" in canonical_query or "claro mexico" in canonical_query:
            alias_prefix = (
                "Para aclararte: en México, la marca **Claro** opera bajo el nombre "
                "**Telcel**, por lo que la información que te compartiré corresponde "
                "a los servicios y promociones de Telcel en México.\n\n"
            )
            context_label = "📱 Telcel (Claro México)"
            canonical_query = (
                canonical_query
                .replace("claro méxico", "telcel")
                .replace("claro mexico", "telcel")
            )

        # =====================================================
        # 2️⃣ About Telcel
        # =====================================================
        if canonical_query in {
            "que es telcel",
            "qué es telcel",
            "informacion sobre telcel",
            "información sobre telcel",
            "info sobre telcel",
            "hablame de telcel",
            "háblame de telcel",
            "empresa telcel",
            "telcel que es",
        }:
            return {
                "success": True,
                "action": "telcel",
                "context": context_label,
                "context_reset": False,
                "memory_used": 0,
                "response": alias_prefix + TELCEL_ABOUT_TEXT,
                "relevant_urls": [],
            }

        # =====================================================
        # 3️⃣ Retrieval (SIEMPRE con query canónica)
        # =====================================================
        documents = self._retrieve_documents(canonical_query)

        # =====================================================
        # 4️⃣ No coverage → fallback guiado
        # =====================================================
        if not documents:
            return self._no_coverage_response(
                alias_prefix=alias_prefix,
                context_label=context_label,
            )

        # =====================================================
        # 5️⃣ Síntesis (SIEMPRE con query canónica)
        # =====================================================
        synthesized = synthesize_answer(
            user_question=canonical_query,
            documents=documents,
            domain_name="Telcel",
            groq_client=self.groq_client,
            groq_api_key=self.groq_api_key,
        )

        response_text = str(synthesized.get("response") or "")

        return {
            "success": True,
            "action": "telcel",
            "context": context_label,
            "context_reset": False,
            "memory_used": 0,
            "response": alias_prefix + response_text,
            "relevant_urls": synthesized.get("relevant_urls", []),
        }

    # --------------------------------------------------
    # Retrieval
    # --------------------------------------------------

    def _retrieve_documents(self, query: str) -> List[Dict[str, Any]]:
        """
        Ejecuta retrieval RAG Telcel usando la query canónica.
        """
        return self.telcel_rag.retrieve(
            query=query,
            datasets=["telcel_basico", "tarifas"],
            k=5,
        )

    # --------------------------------------------------
    # Fallback guiado
    # --------------------------------------------------

    def _no_coverage_response(
        self,
        *,
        alias_prefix: str,
        context_label: str,
    ) -> Dict[str, Any]:
        """
        Respuesta cuando no hay documentos relevantes.
        Activa continuidad conversacional.
        """

        return {
            "success": True,
            "action": "telcel",
            "context": context_label,
            "context_reset": False,
            "memory_used": 0,
            "awaiting": "telcel_subdomain",
            "response": (
                alias_prefix
                + "No tengo información específica sobre ese tema en mis documentos, "
                "pero puedo ayudarte con **planes**, **promociones** o "
                "**equipos disponibles en Telcel**.\n\n"
                "¿Sobre cuál te gustaría saber más?"
            ),
        }
