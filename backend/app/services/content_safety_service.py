from openai import OpenAI
import logging
import os

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def check_content_safety(text: str) -> dict:
    response = client.moderations.create(
        model="omni-moderation-latest",
        input=text
    )

    result = response.results[0]

    return {
        "flagged": result.flagged,
        "categories": result.categories,
        "scores": result.category_scores
    }
