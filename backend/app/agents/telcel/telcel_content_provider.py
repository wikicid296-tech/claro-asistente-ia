# agents/telcel/telcel_content_provider.py

def get_telcel_content() -> dict:
    """
    Contenido simulado de Telcel México derivado de datos públicos del IFT.
    """

    return {
        "brand": "Telcel",
        "region": "México",
        "segments": {
            "prepago": {
                "name": "Amigo Sin Límite",
                "price_range": "$10 – $80 MXN",
                "validity_range_days": "1 – 13 días",
                "features": [
                    "Minutos y SMS ilimitados",
                    "Datos para navegación",
                    "Redes sociales ilimitadas",
                    "Cobertura nacional"
                ]
            }
        },
        "examples": [
            "Amigo Sin Límite 10",
            "Amigo Sin Límite 20",
            "Amigo Sin Límite 30"
        ],
        "site_url": "https://www.telcel.com"
    }
