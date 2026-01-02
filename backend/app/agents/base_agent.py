from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAgent(ABC):

    DEFAULT_CONTEXT = 'Asistente disponible'

    def __init__(self, user_message: str, context: Dict[str, Any], intent: str):
        self.user_message = user_message
        self.context = context
        self.intent = intent

    def handle(self) -> Dict[str, Any]:
        try:
            resolution = self._resolve()

            base_response = {
                "action": self.intent,
                "context": resolution.get("context", self.DEFAULT_CONTEXT),
                "context_reset": resolution.get("context_reset", False),
                "memory_used": resolution.get("memory_used", 0),
                "relevant_urls": resolution.get("relevant_urls", []),
                "response": resolution["response"],
                "success": True
            }

            # =====================================================
            # 🔑 PROPAGAR CAMPOS ADICIONALES DEL AGENTE
            # =====================================================

            # Campos extra explícitos (tu mecanismo existente)
            extra_fields = resolution.get("extra", {})
            if isinstance(extra_fields, dict):
                base_response.update(extra_fields)

            # Campo awaiting (CLAVE para estado conversacional)
            if "awaiting" in resolution:
                base_response["awaiting"] = resolution["awaiting"]

            return base_response

        except Exception as e:
            return {
                "action": self.intent,
                "context": "Error en la instancia de agente general😣😣",
                "context_reset": False,
                "memory_used": 0,
                "relevant_urls": [],
                "response": (
                    f"Lo siento, ha ocurrido un error al procesar tu solicitud: {str(e)}"
                ),
                "success": False
            }

    @abstractmethod
    def _resolve(self) -> Dict[str, Any]:
        """
        Debe regresar al menos:
        {
          "response": str
        }

        Opcionales:
        - context
        - context_reset
        - memory_used
        - relevant_urls
        - awaiting            <-- 🔑 IMPORTANTE
        - extra (dict con campos específicos del intent)
        """
        raise NotImplementedError
