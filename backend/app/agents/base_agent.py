from abc import ABC, abstractmethod
from typing import Any, Dict, List

class BaseAgent(ABC):
    
    DEFAULT_CONTEXT = 'Asistente disponible'
    
    def __init__(self,user_message: str,context: Dict[str,Any],intent: str ) :
        self.user_message = user_message
        self.context = context
        self.intent = intent
        
    def handle(self)-> Dict[str,Any]:
        try:
            resolution = self._resolve()
            base_response ={
                "action": self.intent,
                "context": resolution.get("context", self.DEFAULT_CONTEXT),
                "context_reset": resolution.get("context_reset", False),
                "memory_used": resolution.get("memory_used", 0),
                "relevant_urls": resolution.get("relevant_urls", []),
                "response": resolution["response"],
                "success": True
            }
            extra_fields = resolution.get("extra",{})
            base_response.update(extra_fields)
            return base_response
        
        except Exception as e:
            base_response = {
                "action": self.intent,
                "context": "Error en la instancia de agente general😣😣",
                "context_reset": False,
                "memory_used": 0,
                "relevant_urls": [],
                "response": f"Lo siento, ha ocurrido un error al procesar tu solicitud: {str(e)}",
                "success": False
            }
            return base_response
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
        - extra (dict con campos específicos del intent)
        """
        raise NotImplementedError
        