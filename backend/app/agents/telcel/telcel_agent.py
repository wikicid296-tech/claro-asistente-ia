import os
import re
from typing import Dict, Any, List
from urllib.parse import urlencode

from app.services.telcel_rag_service import TelcelRAGService
from app.services.response_synthesis_service import synthesize_answer
from app.services.groq_service import get_groq_client, get_groq_api_key
from app.agents.telcel.about_telcel import TELCEL_ABOUT_TEXT


class TelcelAgent:
    """
    Agente conversacional dedicado a Telcel.
    (Versión instrumentada para diagnóstico)
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

        print("\n================ TELCEL AGENT =================")
        print(f"🧾 user_message original: {self.user_message}")

        # =====================================================
        # 0️⃣ Canonical query
        # =====================================================
        original_query = self.user_message.strip()
        canonical_query = original_query.lower()

        print(f"🔁 canonical_query inicial: {canonical_query}")

        alias_prefix = ""
        context_label = "📱 Telcel"

        # =====================================================
        # 1️⃣ Alias Claro México → Telcel
        # =====================================================
        if "claro méxico" in canonical_query or "claro mexico" in canonical_query:
            print("🔀 Alias detectado: Claro México → Telcel")

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

            print(f"🔁 canonical_query tras alias: {canonical_query}")

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
            print("ℹ️ About Telcel activado")

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
        # 3️⃣ Retrieval
        # =====================================================
        print("📡 Ejecutando RAG Telcel...")
        documents = self._retrieve_documents(canonical_query)

        print(f"📄 Documentos recuperados: {len(documents)}")

        # =====================================================
        # 4️⃣ No coverage
        # =====================================================
        if not documents:
            print("🚫 NO COVERAGE: no se encontraron documentos")
            return self._no_coverage_response(
                alias_prefix=alias_prefix,
                context_label=context_label,
                canonical_query=canonical_query,
            )

        # =====================================================
        # 5️⃣ Síntesis
        # =====================================================
        print("🧠 Ejecutando síntesis...")
        synthesized = synthesize_answer(
            user_question=canonical_query,
            documents=documents,
            domain_name="Telcel",
            groq_client=self.groq_client,
            groq_api_key=self.groq_api_key,
        )

        response_text = str(synthesized.get("response") or "")
        raw_urls = synthesized.get("relevant_urls", [])

        # Normalización defensiva
        if isinstance(raw_urls, str):
            print("⚠️ relevant_urls es string, normalizando a lista vacía")
            relevant_urls = []
        elif isinstance(raw_urls, list):
            relevant_urls = raw_urls
        else:
            relevant_urls = []
        print("📝 Respuesta sintetizada:")
        print(response_text[:500], "..." if len(response_text) > 500 else "")
        print(f"🔗 relevant_urls iniciales: {relevant_urls}")

        # =====================================================
        # 6️⃣ Evaluación comercial
        # =====================================================
        is_commercial = self._is_commercial_query(canonical_query)
        print(f"💰 ¿Es query comercial?: {is_commercial}")
        has_actionable = self._has_actionable_commercial_info(
            response_text,
            relevant_urls,
        )


        print(f"✅ ¿Respuesta tiene info comercial accionable?: {has_actionable}")

        if is_commercial and not has_actionable:
            print("⚠️ Comercial SIN info accionable → evaluando buscador")

            search_query = self._build_search_query(canonical_query)
            print(f"🔎 search_query generada: '{search_query}'")

            if search_query:
                search_url = self._build_telcel_search_link(search_query)
                print(f"🌐 URL buscador generada: {search_url}")

                response_text += (
                    "\n\n🔎 **Nota:** La información encontrada en los documentos es "
                    "general y no incluye precios o disponibilidad actualizada. "
                    "Para una consulta directa y vigente, puedes usar el buscador "
                    "oficial de Telcel."
                )

                relevant_urls.append(search_url)
            else:
                print("❌ search_query vacía → NO se genera URL")
        else:
            print("🟢 NO se activa fallback a buscador")

        print("================ FIN TELCEL AGENT =================\n")

        return {
            "success": True,
            "action": "telcel",
            "context": context_label,
            "context_reset": False,
            "memory_used": 0,
            "response": alias_prefix + response_text,
            "relevant_urls": relevant_urls,
        }

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def _retrieve_documents(self, query: str) -> List[Dict[str, Any]]:
        return self.telcel_rag.retrieve(
            query=query,
            datasets=["telcel_basico", "tarifas"],
            k=5,
        )

    def _is_commercial_query(self, query: str) -> bool:
        return any(k in query for k in (
            "precio", "precios", "costo", "costos",
            "comprar", "venta", "equipos", "modelos"
        ))
    def _is_actionable_commercial_url(self, url: str) -> bool:
        """
        Define URLs realmente accionables para compra / consulta de equipos.
        """
        return any(p in url for p in (
            "/buscador",
            "/tienda",
            "/equipos",
            "/smartphone",
            "query="
        ))


    def _has_actionable_commercial_info(
        self,
        response: str,
        relevant_urls: List[str],
    ) -> bool:
        """
        Considera accionable SOLO si hay señal de precio REAL (monto),
        o links de compra/búsqueda. No basta con que aparezca la palabra 'precios'.
        """
        text = (response or "").lower()

        # ---------------------------------------------------------
        # 1) Señales fuertes de precio real (monto)
        # ---------------------------------------------------------
        has_currency_amount = bool(re.search(r"\$\s*\d", text))  # $ 123
        has_pesos_amount = bool(re.search(r"\b\d[\d.,]*\s*(pesos)\b", text))  # 12,999 pesos
        has_mxn_amount_1 = bool(re.search(r"\bmxn\s*\d", text))  # mxn 12999
        has_mxn_amount_2 = bool(re.search(r"\b\d[\d.,]*\s*mxn\b", text))  # 12,999 mxn

        if has_currency_amount:
            print("✅ actionable: detecté patrón de precio con '$ + dígitos'")
            return True
        if has_pesos_amount:
            print("✅ actionable: detecté patrón 'dígitos + pesos'")
            return True
        if has_mxn_amount_1 or has_mxn_amount_2:
            print("✅ actionable: detecté patrón con 'MXN' y monto")
            return True

        # ---------------------------------------------------------
        # 2) URLs realmente comerciales (no noticias/políticas/planes)
        # ---------------------------------------------------------
        for url in (relevant_urls or []):
            u = (url or "").lower()
            if any(p in u for p in ("/buscador", "query=", "/tienda", "/equipos", "/smartphone")):
                print(f"✅ actionable: URL comercial detectada: {url}")
                return True

        # ---------------------------------------------------------
        # 3) Si no hay monto ni URL comercial, NO es accionable
        # ---------------------------------------------------------
        print("❌ actionable: NO hay monto de precio ni URL comercial")
        return False




    def _build_search_query(self, canonical_query: str) -> str:
        stopwords = {
            "quiero", "saber", "informacion", "información",
            "sobre", "los", "las", "de", "del", "que",
            "puedo", "encontrar", "tener", "tienes",
            "precio", "precios", "costo", "costos",
            "equipos", "modelo", "modelos",
            "en", "para", "telcel"
        }

        tokens = re.findall(r"\b[a-z0-9]+\b", canonical_query)
        filtered = [
            t for t in tokens
            if t not in stopwords and len(t) > 2
        ]

        return " ".join(filtered[:4])

    def _build_telcel_search_link(self, search_query: str) -> str:
        params = {
            "query": search_query,
            "mundo": "Personas",
            "subseccion": "Hazlo ahora",
        }
        return f"https://www.telcel.com/buscador?{urlencode(params)}"

    # --------------------------------------------------
    # No coverage
    # --------------------------------------------------

    def _no_coverage_response(
        self,
        *,
        alias_prefix: str,
        context_label: str,
        canonical_query: str,
    ) -> Dict[str, Any]:

        print("🚨 NO COVERAGE fallback activado")

        urls = []

        if self._is_commercial_query(canonical_query):
            search_query = self._build_search_query(canonical_query)
            print(f"🔎 search_query (no coverage): '{search_query}'")

            if search_query:
                url = self._build_telcel_search_link(search_query)
                print(f"🌐 URL buscador (no coverage): {url}")
                urls.append(url)

        return {
            "success": True,
            "action": "telcel",
            "context": context_label,
            "context_reset": False,
            "memory_used": 0,
            "response": (
                alias_prefix
                + "No encontré información específica en mis documentos sobre ese tema. "
                "Puedes consultar directamente el buscador oficial de Telcel para "
                "obtener información actualizada."
            ),
            "relevant_urls": urls,
        }
