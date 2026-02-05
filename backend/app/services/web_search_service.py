from logging import Logger
from openai import OpenAI
import dotenv
import re
from openai.types.responses import WebSearchToolParam

OPENAI_API_KEY = dotenv.get_key(".env", "OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


def sanitize_preserving_markdown(text: str) -> str:
    """
    Elimina residuos técnicos de citas SIN alterar el formato Markdown.
    """
    if not text:
        return text

    # Elimina unicode privado usado por marcadores internos
    text = re.sub(r'[\uE200-\uE2FF]', '', text)

    # Elimina residuos degradados tipo DciteTurn0finance0, citeTurn1, etc.
    text = re.sub(r'\b[Dd]?cite[Tt]urn\d+[A-Za-z0-9]*\b', '', text)

    # Elimina residuos tipo turn0finance0
    text = re.sub(r'\bturn\d+[A-Za-z0-9]*\b', '', text)

    return text.strip()


def run_web_search(user_query: str) -> dict:
    try:
        response = client.responses.create(
            model="gpt-4.1",
            tools=[WebSearchToolParam(type="web_search")],
            input=f"Busca información actual y confiable sobre: {user_query}",
            max_output_tokens=1800,
        )

        # Seguridad: no renderizar respuestas incompletas
        if response.status != "completed":
            return {
                "content": "La información no pudo recuperarse completamente en este momento.",
                "sources": [],
            }

        text_blocks: list[str] = []
        sources: set[str] = set()

        for item in response.output:
            if item.type == "message":
                for block in item.content:
                    if block.type == "output_text":
                        if block.text:
                            clean_text = sanitize_preserving_markdown(block.text)
                            if clean_text:
                                text_blocks.append(clean_text)

                        # Las fuentes se recolectan SIN insertarlas en el texto
                        for ann in block.annotations or []:
                            url = getattr(ann, "url", None)
                            if url:
                                sources.add(url)

        return {
            "content": "\n\n".join(text_blocks).strip(),
            "sources": sorted(sources),
        }

    except Exception as e:
        Logger.info(f"Error during web search: {e}")
        return {
            "content": "No fue posible realizar la búsqueda web en este momento.",
            "sources": [],
            "error": str(e),
        }
