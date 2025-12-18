from agents.base_agent import BaseAgent
from agents.telcel.telcel_content_provider import get_telcel_content


class TelcelAgent(BaseAgent):
    """
    Agente especializado en información comercial general de Telcel México.
    """

    def _resolve(self) -> dict:
        content = get_telcel_content()
        prepago = content["segments"]["prepago"]

        response = (
            f"Telcel ofrece planes prepago como {prepago['name']}, "
            f"con recargas que van de {prepago['price_range']} "
            f"y vigencias de {prepago['validity_range_days']}. "
            "Incluyen minutos y SMS ilimitados, datos para navegación "
            "y redes sociales ilimitadas con cobertura nacional."
        )

        return {
            "response": response,
            "context": "📱 Información general de Telcel (datos de referencia IFT)",
            "relevant_urls": [content["site_url"]],
            "memory_used": 0
        }
