from openai import OpenAI
import dotenv
from openai.types.responses import WebSearchToolParam

OPENAI_API_KEY = dotenv.get_key(".env", "OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def run_web_search(user_query: str) -> dict:
    try:
        response = client.responses.create(
            model="gpt-4.1",
            tools=[WebSearchToolParam(type="web_search")],
            input=f"Busca información actual y confiable sobre: {user_query}",
            max_output_tokens=1200,
        )

        text_blocks: list[str] = []
        sources: set[str] = set()

        for item in response.output:
            if getattr(item, "type", None) == "message":
                for c in getattr(item, "content", []):
                    if getattr(c, "type", None) == "output_text":
                        if c.text:
                            text_blocks.append(c.text)

                        for cite in getattr(c, "citations", []) or []:
                            url = getattr(cite, "url", None)
                            if url:
                                sources.add(url)

        return {
            "content": "\n".join(text_blocks).strip(),
            "sources": list(sources),
        }

    except Exception as e:
        return {
            "content": "No fue posible realizar la búsqueda web en este momento.",
            "sources": [],
            "error": str(e),
        }
