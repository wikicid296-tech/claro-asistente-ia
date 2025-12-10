
import json
import logging
import os
from functools import lru_cache
from typing import Optional, TYPE_CHECKING, Any, Dict, List

from app.config import settings

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from openai import OpenAI as OpenAIType
else:
    OpenAIType = Any


# ============================================================
# 1. KEY MANAGEMENT
# ============================================================

def get_openai_api_key() -> Optional[str]:
    return (
        getattr(settings, "OPENAI_API_KEY", None)
        or os.getenv("OPENAI_API_KEY")
    )


def get_vector_store_id() -> Optional[str]:
    return (
        getattr(settings, "OPENAI_VECTOR_STORE_ID", None)
        or getattr(settings, "VECTOR_STORE_ID", None)
        or os.getenv("OPENAI_VECTOR_STORE_ID")
        or os.getenv("VECTOR_STORE_ID")
    )


# ============================================================
# 2. CLIENT BUILDER
# ============================================================

def build_openai_client() -> Optional["OpenAIType"]:
    api_key = get_openai_api_key()

    if not api_key:
        logger.warning("OPENAI_API_KEY no configurada")
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        logger.info("Cliente OpenAI inicializado correctamente")
        return client
    except Exception as e:
        logger.error(f"Error inicializando el cliente OpenAI: {e}", exc_info=True)
        return None


@lru_cache(maxsize=1)
def get_openai_client() -> Optional["OpenAIType"]:
    return build_openai_client()


# ============================================================
# 3. VECTOR SEARCH  (FUNCIÓN NECESARIA PARA Aprende Flow)
# ============================================================

def buscar_curso_directo(query: str, k: int = 10):
    """
    Búsqueda directa en el Vector Store.
    Extrae la metadata REAL que viene incrustada como JSON dentro del texto del chunk,
    igual que tu implementación original.
    """

    client = get_openai_client()
    vector_store_id = get_vector_store_id()

    if not client or not vector_store_id:
        logger.error("OpenAI client o VECTOR_STORE_ID no configurados.")
        return []

    try:
        print("\n🔍 Ejecutando búsqueda directa en OpenAI Vector Store...")

        response = client.vector_stores.search(
            vector_store_id=vector_store_id,
            query=query
        )

        print("\n📌 RAW RESPONSE:")
        print(response)

        resultados = []

        for item in response.data:
            print("\n🔹 ITEM RAW:")
            print(item)

            texto = ""
            if hasattr(item, "content") and item.content:
                texto = item.content[0].text or ""

            # ============================
            # 1. EXTRAER JSON INCRUSTADO
            # ============================
            extracted_meta = {}
            try:
                first_brace = texto.find("{")
                last_brace = texto.rfind("}")

                if first_brace != -1 and last_brace != -1:
                    json_str = texto[first_brace:last_brace+1]
                    extracted_meta = json.loads(json_str)

            except Exception as e:
                print(f"⚠️ No se pudo parsear metadata del texto: {e}")

            # ============================
            # 2. OBTENER FIELDSET COMO ANTES
            # ============================
            course_id = extracted_meta.get("courseId")
            course_name = extracted_meta.get("courseName")

            processed = {
                "id": course_id,
                "score": getattr(item, "score", None),
                "metadata": extracted_meta,
                "courseName": course_name,
                "courseId": course_id,
            }

            print("\n✅ PROCESSED ITEM:")
            print(json.dumps(processed, indent=2, ensure_ascii=False))

            resultados.append(processed)

        print("\n🎯 RESULTADO FINAL PARA API:")
        print(json.dumps(resultados, indent=2, ensure_ascii=False))

        return resultados

    except Exception as e:
        logger.error(f"Error en búsqueda directa: {e}", exc_info=True)
        return []