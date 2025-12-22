import unicodedata

CLARO_COUNTRIES = {
    "argentina": "ar",
    "brasil": "br",
    "chile": "cl",
    "colombia": "co",
    "costa rica": "cr",
    "ecuador": "ec",
    "el salvador": "sv",
    "guatemala": "gt",
    "honduras": "hn",
    "nicaragua": "ni",
    "paraguay": "py",
    "perú": "pe",
    "peru": "pe",
    "puerto rico": "pr",
    "república dominicana": "do",
    "republica dominicana": "do",
    "uruguay": "uy",
    "estados unidos": "us",
    "usa": "us",
    "eeuu": "us",
    "españa": "es",
    "espana": "es",
}


def normalize(text: str) -> str:
    """
    - lowercase
    - elimina acentos
    - normaliza espacios
    """
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.split())


def detect_country(user_message: str) -> str:
    text = normalize(user_message)

    # 🔒 Match determinístico por nombre completo
    for country_name, code in CLARO_COUNTRIES.items():
        if country_name in text:
            return code

    return "unknown"
