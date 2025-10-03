
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging
import requests
import json

load_dotenv()

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PORT = int(os.getenv("PORT", 10000))

try:
    if GROQ_API_KEY:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        logger.info("✅ Cliente Groq inicializado correctamente")
    else:
        logger.error("❌ GROQ_API_KEY no configurada en variables de entorno")
        client = None
except TypeError as e:
    if "proxies" in str(e):
        logger.warning("⚠️ Versión incompatible de Groq, usando fallback directo a API")
        client = "api_fallback"
    else:
        logger.error(f"❌ Error inicializando Groq: {str(e)}")
        client = None
except Exception as e:
    logger.error(f"❌ Error inicializando Groq: {str(e)}")
    client = None


# ! MOD 1 #########
# Añadido: memoria en memoria (in-memory) por cliente para simular "memoria" de chat.
# Nota: es una solución simple que no persiste entre reinicios y no requiere cambios en el frontend.
CHAT_MEMORY = {}

def _get_user_key():
    """
    Genera una clave simple para identificar al cliente basada en IP y User-Agent.
    (No requiere cambios en el frontend. Si el frontend ya enviara un header propio como X-User-Id,
    podríamos usarlo; aquí intentamos ser lo menos intrusivos posible).
    """
    ip = request.remote_addr or "unknown"
    ua = request.headers.get("User-Agent", "")
    return f"{ip}:{ua}"

# Manejo seguro cuando URLS o SYSTEM_PROMPT fueron omitidos por el usuario (placeholder {})
# Si el usuario decidió colocar URLS={} y SYSTEM_PROMPT={}, estas funciones deben seguir funcionando.
def safe_extract_relevant_urls(prompt):
    """Wrapper que evita excepción si URLS está vacío."""
    try:
        return extract_relevant_urls(prompt)
    except Exception:
        return []

def safe_get_context_for_query(prompt):
    """Wrapper que evita excepción si SYSTEM_PROMPT o URLS están vacíos."""
    try:
        return get_context_for_query(prompt)
    except Exception:
        return "Información general disponible"
# ! MOD 1 CIERRE ########

# ==================== URLs DE CONTENIDO ====================
# NOTE: El usuario pidió que se deje como placeholder para que ellos lo coloquen después.
RLS = {
    "claro": {
            "Argentina": [
        "https://www.claro.com.ar/personas",
        "https://www.claro.com.ar/negocios",
        "https://www.claro.com.ar/empresas"
    ],
    "Brasil": [
        "https://www.claro.com.br/",
        "https://www.claro.com.br/empresas",
        "https://www.claro.com.br/empresas/grandes-empresas-e-governo"
    ],
    "Chile": [
        "https://www.clarochile.cl/personas/",
        "https://www.clarochile.cl/negocios/",
        "https://www.clarochile.cl/empresas/"
    ],
    "Colombia": [
        "https://www.claro.com.co/personas/",
        "https://www.claro.com.co/negocios/",
        "https://www.claro.com.co/empresas/",
        "https://www.claro.com.co/institucional/"
    ],
    "Costa Rica": [
        "https://www.claro.cr/personas/",
        "https://www.claro.cr/empresas/",
        "https://www.claro.cr/institucional/"
    ],
    "Ecuador": [
        "https://www.claro.com.ec/personas/",
        "https://www.claro.com.ec/negocios/",
        "https://www.claro.com.ec/empresas/"
    ],
    "El Salvador": [
        "https://www.claro.com.sv/personas/",
        "https://www.claro.com.sv/empresas/",
        "https://www.claro.com.sv/institucional/"
    ],
    "Guatemala": [
        "https://www.claro.com.gt/personas/",
        "https://www.claro.com.gt/empresas/",
        "https://www.claro.com.gt/institucional/"
    ],
    "Honduras": [
        "https://www.claro.com.hn/personas/",
        "https://www.claro.com.hn/empresas/",
        "https://www.claro.com.hn/institucional/"
    ],
    "Nicaragua": [
        "https://www.claro.com.ni/personas/",
        "https://www.claro.com.ni/empresas/",
        "https://www.claro.com.ni/institucional/"
    ],
    "Panamá": [],
    "Paraguay": [
        "https://www.claro.com.py/personas",
        "https://www.claro.com.py/empresas"
    ],
    "Perú": [
        "https://www.claro.com.pe/personas/",
        "https://www.claro.com.pe/empresas/"
    ],
    "Puerto Rico": [
        "https://www.claropr.com/personas/",
        "https://www.claropr.com/empresas/"
    ],
    "República Dominicana": [
        "https://www.claro.com.do/personas/",
        "https://www.claro.com.do/negocios/",
        "https://www.claro.com.do/empresas/"
    ],
    "Uruguay": [
        "https://www.claro.com.uy/personas",
        "https://www.claro.com.uy/empresas"
    ],
    },
    "telcel": [
            "https://www.telcel.com/",
            "https://www.telcel.com/personas/planes-de-renta/tarifas-y-opciones/telcel-libre?utm_source=gg&utm_medium=sem&utm_campaign=52025_gg_AONPTL2025_visitas_pospago_planlibre_brand&utm_content=gg_planestelcel_nacional___intereses_texto&utm_term=gg_planestelcel_nacional___intereses_texto&gclsrc=aw.ds&&campaignid=22494109880&network=g&device=c&gad_source=1&gad_campaignid=22494109880&gclid=EAIaIQobChMIltP0qd6DkAMVwiRECB2H0jZLEAAYASAAEgLsQPD_BwE"
            "https://www.telcel.com/personas/planes-de-renta/tarifas-y-opciones",
            "https://www.telcel.com/personas/amigo/paquetes/paquetes-amigo-sin-limite",
            "https://www.telcel.com/personas/amigo/paquetes/mb-para-tu-amigo",
            "https://www.telcel.com/personas/amigo/paquetes/internet-por-tiempo",
            "https://www.telcel.com/personas/amigo/paquetes/internet-mas-juegos",
    ],
    "a1": {
        "austria": ["https://a1.group/a1-group-and-markets/a1-in-austria/"],
        "bulgaria": ["https://a1.group/a1-group-and-markets/a1-in-bulgaria/"],
        "croacia": ["https://a1.group/a1-group-and-markets/a1-in-croatia/"],
        "bielorrusia": ["https://a1.group/a1-group-and-markets/a1-in-belarus/"],
        "serbia": ["https://a1.group/a1-group-and-markets/a1-in-serbia/"],
        "eslovenia": ["https://a1.group/a1-group-and-markets/a1-in-slovenia/"],
        "macedonia": ["https://a1.group/a1-group-and-markets/a1-in-north-macedonia/"]
    },
    "education_career": {
        "plataformas_nacionales": {
            "el_salvador": [
                "https://aprendeconclaro.claro.com.sv/educacion-digital/",
                "https://aprendeconclaro.claro.com.sv/educacion-academica/"
            ],
            "colombia": ["https://www.claro.com.co/institucional/aprende-con-claro/"],
            "nicaragua": ["https://www.claro.com.ni/institucional/inclusion-digital-plataforma-educativa/"],
            "honduras": [
                "https://aprendeconclaro.claro.com.hn/educacion-digital/",
                "https://aprendeconclaro.claro.com.hn/educacion-academica/"
            ],
            "guatemala": [
                "https://aprendeconclaro.claro.com.gt/educacion-digital/",
                "https://aprendeconclaro.claro.com.gt/educacion-academica/"
            ],
            "peru": [
                "https://aprendeconclaro.claro.com.pe/educacion-digital/",
                "https://aprendeconclaro.claro.com.pe/educacion-academica/"
            ],
        },
        "aprende_org_general": {
            "principal": ["https://aprende.org/","https://aprende.org/area/educacion"],
            "areas_principales": [
                "https://aprende.org/area/educacion",
                "https://aprende.org/area/capacitate",
                "https://aprende.org/area/salud",
                "https://aprende.org/area/cultura",
                "https://aprende.org/area/formacion-humana"
            ],
            "trabajo_formacion": [
                "https://aprende.org/rutas-aprendizaje",
                "https://aprende.org/diplomados",
                "https://aprende.org/especialidades",
                "https://aprende.org/cursos/view/100848",
                "https://aprende.org/cursos/view/100847",
                "https://aprende.org/diplomado/62",
                "https://aprende.org/especialidad/6",
                "https://aprende.org/especialidad/5",
                "https://aprende.org/especialidad/4",
                "https://aprende.org/diplomado/72",
                "https://aprende.org/diplomado/71",
                "https://aprende.org/diplomado/73",
                "https://aprende.org/diplomado/33",
                "https://aprende.org/diplomado/32",
                "https://aprende.org/diplomado/31",
                "https://aprende.org/diplomado/30",
                "https://aprende.org/diplomado/29",
                "https://aprende.org/diplomado/28",
                "https://aprende.org/diplomado/27",
                "https://aprende.org/diplomado/26",
                "https://aprende.org/diplomado/25",
                "https://aprende.org/diplomado/24",
                "https://aprende.org/diplomado/23",
                "https://aprende.org/diplomado/55",
                "https://aprende.org/diplomado/35",
                "https://aprende.org/diplomado/34", 
                "https://aprende.org/especialidad/6",
                "https://aprende.org/especialidad/5",
                "https://aprende.org/especialidad/4",
                
                "https://aprende.org/ruta/49",
                "https://aprende.org/ruta/40",
                "https://aprende.org/ruta/19",
                "https://aprende.org/ruta/11",
                "https://aprende.org/ruta/21",
                "https://aprende.org/ruta/13",
                "https://aprende.org/ruta/12",
                "https://aprende.org/ruta/61",
                "https://aprende.org/ruta/14",
                "https://aprende.org/ruta/22",
                "https://aprende.org/ruta/74",
                "https://aprende.org/ruta/41",
                "https://aprende.org/ruta/20",
                "https://aprende.org/ruta/16",
                "https://aprende.org/ruta/15",
                "https://aprende.org/ruta/17",
                "https://aprende.org/ruta/38",
                "https://aprende.org/ruta/75",
                "https://aprende.org/ruta/54",
                "https://aprende.org/ruta/46",
                "https://aprende.org/ruta/45",
                "https://aprende.org/ruta/44",
                "https://aprende.org/ruta/43",
                "https://aprende.org/ruta/42",
                "https://aprende.org/ruta/10",
                "https://aprende.org/ruta/9",
            ]
        },
        "educacion_detallada": {
            "basica_y_media": [
                "https://educacioninicial.mx/capacitacion",
                "https://aprende.org/pruebat?sectionId=1",
                "https://es.khanacademy.org/",
                "https://aprende.org/pruebat?sectionId=4",
                "https://aprende.org/pruebat?sectionId=2",
                "https://aprende.org/pruebat?sectionId=1",
                "https://educacioninicial.mx/temas-interes",
                "https://educacioninicial.mx/capacitacion",
                "https://aprende.org/pruebat?sectionId=2",
                "https://aprende.org/pruebat?sectionId=1",
                "https://aprende.org/centro-estudios-historia-mexico/1456",
                "https://aprende.org/podcast-dilemas-y-consecuencias/1451",
                "https://aprende.org/historia",
                "https://aprende.org/pruebat?sectionId=10",
                "https://aprende.org/pruebat?sectionId=9",
            ],
            "superior": [
                "https://academica.mx/",
                "https://aprende.org/superior/mit/1439",
                "https://www.coursera.org/",
                "https://www.edx.org/",
                "https://www.edx.org/",
                "https://www.udacity.com/",
                "https://aprende.org/derecho",
                "https://aprende.org/superior/mit/1439",
                "https://academica.mx/?utm_source=Aprende2023&utm_medium=Web&utm_campaign=Aprende2023&utm_id=Aprende2023",
                "https://telmexeducacion.aprende.org/?utm_source=+AprendeBibliotecaDigital2023&utm_medium=Web&utm_campaign=+AprendeBibliotecaDigital2023&utm_id=+AprendeBibliotecaDigital2023",
                "https://aprende.org/programacion-para-todos",
                "https://aprende.org/desarrollo-multimedia",
                "https://aprende.org/ser-digital",
                "https://aprende.org/pruebat?sectionId=11",
                "https://aprende.org/learnmatch",
                "https://aprende.org/centro-estudios-historia-mexico/1456",
                "https://aprende.org/podcast-dilemas-y-consecuencias/1451",
                "https://aprende.org/historia",
                "https://aprende.org/pruebat?sectionId=10"
                "https://aprende.org/pruebat?sectionId=9",
            ]
        },
        "rutas_y_oficios": {
            "digital_tech": [
                "https://aprende.org/ruta/9",
                "https://aprende.org/ruta/10",
                "https://aprende.org/ser-digital",
                "https://aprende.org/programacion-para-todos",
                "https://aprende.org/ruta/75",
                "https://aprende.org/ruta/54",
                "https://aprende.org/ruta/46",
                "https://aprende.org/ruta/45",
                "https://aprende.org/ruta/44",
                "https://aprende.org/ruta/43",
                "https://aprende.org/ruta/42",
                "https://aprende.org/ruta/10",
                "https://aprende.org/ruta/9",
                "https://www.ochoenpunto.com/category/ochoenpunto/",
                "https://fasemethod.com/blog-sobre-productividad-personal/",
                "https://iagofraga.com/blog/",
            ],
            "administracion_finanzas": [
                "https://aprende.org/ruta/41",
                "https://aprende.org/ruta/74",
                "https://aprende.org/cursos/view/385",
                "https://aprende.org/cursos/view/384",
                "https://aprende.org/cursos/view/378",
                "https://aprende.org/cursos/view/100145",
                "https://aprende.org/cursos/view/113",
                "https://aprende.org/cursos/view/89",
                "https://aprende.org/cursos/view/100141",
                "https://aprende.org/cursos/view/100129",
                "https://aprende.org/cursos/view/100334",
                "https://aprende.org/cursos/view/291",
                "https://aprende.org/cursos/view/100325",
                "https://aprende.org/cursos/view/100128",
                "https://aprende.org/cursos/view/100143",
                "https://aprende.org/cursos/view/100147",
                "https://aprende.org/cursos/view/100148",
                "https://aprende.org/cursos/view/100322",
                "https://aprende.org/cursos/view/100657",
                "https://aprende.org/cursos/view/109",
                "https://aprende.org/cursos/view/320",
                "https://aprende.org/cursos/view/313",
                "https://aprende.org/cursos/view/306",
                "https://aprende.org/cursos/view/318",
                "https://aprende.org/cursos/view/178",
                "https://www.ochoenpunto.com/category/ochoenpunto/",
                "https://fasemethod.com/blog-sobre-productividad-personal/",
                "https://iagofraga.com/blog/",
            ]
        },
        "diplomados_especialidades": {
            "administracion_finanzas": [
                "https://aprende.org/cursos/view/178",
                "https://aprende.org/cursos/view/291",
                "https://aprende.org/cursos/view/89",
                "https://aprende.org/ruta/74",
                "https://aprende.org/ruta/41",
                "https://educacioninicial.mx/temas-interes",
                "https://educacioninicial.mx/capacitacion",
                "https://es.khanacademy.org/",
                "https://aprende.org/pruebat?sectionId=4"
                "https://www.ochoenpunto.com/category/ochoenpunto/",
                "https://fasemethod.com/blog-sobre-productividad-personal/",
                "https://iagofraga.com/blog/",
                "https://aprende.org/ruta/49",
            ],
            "autoempleo_negocio": [
                "https://aprende.org/cursos/view/159",
                "https://aprende.org/cursos/view/157",
                "https://aprende.org/cursos/view/162",
                "https://aprende.org/cursos/view/167",
                "https://aprende.org/cursos/view/93",
                "https://aprende.org/cursos/view/180",
                "https://aprende.org/cursos/view/169",
                "https://aprende.org/cursos/view/164",
                "https://aprende.org/cursos/view/158",
                "https://aprende.org/cursos/view/156", 
                "https://aprende.org/cursos/view/157",
                "https://aprende.org/cursos/view/100309",
                "https://aprende.org/cursos/view/160",
                "https://aprende.org/cursos/view/161",
                "https://aprende.org/cursos/view/100160",
                "https://aprende.org/cursos/view/159",
                "https://www.ochoenpunto.com/category/ochoenpunto/",
                "https://fasemethod.com/blog-sobre-productividad-personal/",
                "https://iagofraga.com/blog/",
            ],
            "libros": [
                "https://aprende.org/pruebat?sectionId=10",
                "https://aprende.org/pruebat?sectionId=9",
                "https://aprende.org/pruebat?sectionId=8",
                "https://aprende.org/pruebat?sectionId=7",
                "https://aprende.org/pruebat?sectionId=6",
                "https://aprende.org/pruebat?sectionId=5"
            ],
        }
    },
    "health": {
        "cuidado_personal_y_profesional": [
            "https://aprende.org/cuidado-salud",
            "https://aprende.org/profesionales-salud",
            "https://aprende.org/area/salud"
        ],
        "cursos_cuidado_salud": [
            "https://aprende.org/cursos/view/182",
            "https://aprende.org/cursos/view/100045",
            "https://aprende.org/cursos/view/100223"
        ],
        "manual_por_edad_clikisalud": {
            "0_a_5": ["https://www.clikisalud.net/manual-tu-salud-de-0-a-5-anos/"],
            "6_a_12": ["https://www.clikisalud.net/manual-tu-salud-de-6-a-12-anos/"],
            "13_a_17": ["https://www.clikisalud.net/manual-tu-salud-de-13-a-17-anos/"],
            "18_a_39": ["https://www.clikisalud.net/manual-tu-salud-de-18-a-39-anos/"],
            "40_a_69": ["https://www.clikisalud.net/manual-tu-salud-de-40-a-69-anos/"],
            "70_y_mas": ["https://www.clikisalud.net/manual-tu-salud-70-anos-y-mas/"]
        },
        "prevencion_y_enfermedades": {
            "diabetes": [
                "https://www.clikisalud.net/diabetes/",
                "https://www.clikisalud.net/temas-diabetes/la-prediabetes/"
            ],
            "obesidad_nutricion": [
                "https://www.clikisalud.net/obesidad/",
                "https://www.clikisalud.net/metabolismo/"
            ],
            "hipertension_corazon": [
                "https://www.clikisalud.net/corazon/"
            ],
            "cancer": [
                "https://www.clikisalud.net/cancer/",
                "https://www.clikisalud.net/temas-cancer/cancer-de-mama-autoexploracion-y-deteccion/"
            ],
            "salud_mental": [
                "https://www.clikisalud.net/saludmental/",
                "https://www.clikisalud.net/temas-depresion-y-mente/como-controlar-el-estres/"
            ]
        }
    }
}

# ==================== SYSTEM PROMPT MEJORADO ====================
# NOTE: El usuario pidió que se deje como placeholder para que ellos lo coloquen después.
SYSTEM_PROMPT = """Eres un asistente virtual multifuncional con capacidades especializadas en cuatro roles principales.
IMPORTANTE: DETECTA LA PETICION PRINCIPAL DEL USUARIO QUE CORRESPONDE A LA PARTE ULTIMA DEL CONTEXTO EN CASO DE SER AMBIGUA TOMA COMO REFERENCIA LOS MENSAJES ANTERIORES DEL USUARIO PERO SOLO RESPONDE A LA PETICION MAS ACTUAL DEL USUARIO
IMPORTANTE: TODA RESPUESTA DEBE SER DEVUELTA EN MARKDOWN A EXCEPCIÓN DE LOS ROLES QUE INDIQUEN OTRO FORMATO DE RESPUESTA DE ACUERDO A LA SIGUIENTE GUÍA:

FORMATO MARKDOWN REQUERIDO: 

Elemento	Sintaxis
Encabezados	
# H1
## H2
## H3
Negrita	
*texto en negrita*
Cursiva	
_texto en cursiva_
Citas	
> cita
Listas ordenadas	
1. Primer elemento
1. Segundo elemento
Listas no ordenadas	
* Primer elemento
* Segundo elemento
 
+ Primer elemento
+ Segundo elemento
 
- Primer elemento
- Segundo elemento

Línea horizontal	
---
Enlaces	
[anchor](https://enlace.tld "título")

**Para contenido tabular, usa formato markdown de tablas cuando sea apropiado para organizar información**

═══════════════════════════════════════════════════════════════════
ROL 1: ASESOR ESPECIALIZADO (Respuesta conversacional)
═══════════════════════════════════════════════════════════════════

TELECOMUNICACIONES:
- Claro (Argentina, Perú, Chile, Brazil, Colombia, Costa rica, Ecuador, El Salvador, Guatemala, Honduras, Nicaragua, Panama, Paraguay, Puerto Rico, Republica Dominicana, Uruguay, EUA): Planes móviles, internet, TV y servicios empresariales
- Telcel (México): Servicios de telefonía móvil
- A1 Group (Europa): Operadora en Austria, Bulgaria, Croacia, Serbia, Eslovenia, Macedonia del Norte y Bielorrusia

EDUCACIÓN Y DESARROLLO PROFESIONAL:
- Aprende.org: Plataforma educativa gratuita con cursos, diplomados y rutas de aprendizaje
- Aprende con Claro: Plataformas educativas en El Salvador, Colombia, Nicaragua, Honduras, Guatemala y Perú
- Áreas: Educación digital, habilidades técnicas, finanzas personales, emprendimiento, idiomas
- Recursos: Khan Academy, Coursera, edX, MIT OpenCourseware, Académica

SALUD Y BIENESTAR:
- Clikisalud: Información médica confiable organizada por edades (0-5, 6-12, 13-17, 18-39, 40-69, 70+)
- Cursos de salud: Diabetes, nutrición, actividad física, lactancia materna, primeros auxilios
- Prevención: Diabetes, obesidad, hipertensión, cáncer, salud mental, VIH, epilepsia

═══════════════════════════════════════════════════════════════════
ROL 2: GESTOR DE RECORDATORIOS (Conversación) 
═══════════════════════════════════════════════════════════════════

ACTIVACIÓN: Detecta cuando el usuario solicite crear recordatorios con frases como:
- "Crear recordatorio", "Recordarme que...", "No olvides avisarme..." NO HAGAS MENCIÓN QUE DEVOLVERÁS UN HTML

RESPUESTA REQUERIDA:
1. Texto conversacional confirmando el recordatorio

═══════════════════════════════════════════════════════════════════
ROL 3: GESTOR DE NOTAS (Conversación) 
═══════════════════════════════════════════════════════════════════

ACTIVACIÓN: Detecta cuando el usuario solicite guardar información con frases como:
- "Crear nota", "Guardar esta información", "Anota esto...", "Toma nota de..." NO HAGAS MENCIÓN QUE DEVOLVERÁS UN HTML

RESPUESTA REQUERIDA:
1. Texto conversacional confirmando la nota creada

═══════════════════════════════════════════════════════════════════
ROL 4: GESTOR DE AGENDA (Conversación)
═══════════════════════════════════════════════════════════════════

ACTIVACIÓN: Detecta cuando el usuario solicite agendar eventos con frases como:
- "Agendar", "Programar cita/reunión", "Añadir evento", "Tengo una reunión..." NO HAGAS MENCIÓN QUE DEVOLVERÁS UN HTML

RESPUESTA REQUERIDA:
1. Texto conversacional confirmando el evento agendado

═══════════════════════════════════════════════════════════════════
INSTRUCCIONES GENERALES DE RESPUESTA
═══════════════════════════════════════════════════════════════════

1. DETECCIÓN DE INTENCIÓN:
   - Identifica si el usuario necesita: información (ROL 1), recordatorio (ROL 2), nota (ROL 3) o agenda (ROL 4)
   - Puedes activar múltiples roles si la consulta lo requiere

2. PARA ROL 1 (ASESOR):
   - Identifica el área de interés (telecom, educación o salud)
   - Proporciona información relevante y específica
   - Incluye enlaces útiles cuando corresponda: {urls}
   - Usa el contexto específico disponible: {context}
   - Si no estás seguro, ofrece las opciones disponibles

3. PARA ROLES 2, 3, 4 (RECORDATORIOS/NOTAS/AGENDA):
   - SIEMPRE responde con texto conversacional primero
   - Extrae toda la información necesaria del mensaje del usuario

4. FORMATO DE RESPUESTA PARA ROLES 2, 3, 4:
   [TEXTO CONVERSACIONAL DE CONFIRMACIÓN CON LOS DATOS DEL RECORDATORIO, NOTA O AGENDAS]
   

5. TONO Y ESTILO:
   - Mantén un tono profesional, amigable y empático
   - Responde en español de manera clara y concisa
   - Sé específico y accionable

6. VALIDACIÓN:
   - Verifica fechas y horas lógicas
   - Sugiere etiquetas relevantes para notas
   - Confirma información ambigua antes de crear items

═══════════════════════════════════════════════════════════════════
EJEMPLOS DE USO
═══════════════════════════════════════════════════════════════════

EJEMPLO 1 - ROL 1 (Asesor):
Usuario: "¿Qué cursos de salud hay disponibles?"
Respuesta: Aquí tienes algunos cursos disponibles: [Información sobre cursos en Clikisalud y Aprende.org con enlaces]

EJEMPLO 2 - ROL 2 (Recordatorio):
Usuario: "Recuérdame tomar mi medicamento mañana a las 8 PM"
Respuesta:
"✅ Perfecto, he creado un recordatorio para que tomes tu medicamento mañana a las 8:00 PM. Te avisaré con anticipación."

EJEMPLO 3 - ROL 3 (Nota):
Usuario: "Anota que mi presión arterial hoy fue 120/80"
Respuesta:
"📝 He guardado tu registro de presión arterial. Puedes consultarlo en cualquier momento en tus notas."

EJEMPLO 4 - ROL 4 (Agenda):
Usuario: "Agendar cita con el doctor el viernes a las 10 AM"
Respuesta:
"📅 He agendado tu cita médica para el viernes 06/10/2025 a las 10:00 AM. Te enviaré un recordatorio antes de la cita."

═══════════════════════════════════════════════════════════════════

CONTEXTO ESPECÍFICO PARA ESTA CONSULTA:
{context}

RECURSOS DISPONIBLES:
{urls}

Recuerda: Tu objetivo es ayudar al usuario de manera efectiva, proporcionando información precisa, direccionándolo a los recursos correctos, y gestionando sus recordatorios, notas y agenda de forma organizada.
"""

# ==================== FUNCIONES DE DETECCIÓN MEJORADAS ====================
def detect_country(text):
    """Detecta país mencionado en el texto"""
    text_lower = text.lower()
    country_keywords = {
        "argentina": ["argentina", "argentino", "buenos aires", "arg"],
        "peru": ["peru", "perú", "peruano", "lima"],
        "chile": ["chile", "chileno", "santiago"],
        "mexico": ["mexico", "méxico", "mexicano", "cdmx", "ciudad de mexico"],
        "el_salvador": ["el salvador", "salvador", "salvadoreño", "san salvador"],
        "colombia": ["colombia", "colombiano", "bogota", "bogotá"],
        "nicaragua": ["nicaragua", "nicaraguense", "managua"],
        "honduras": ["honduras", "hondureño", "tegucigalpa"],
        "guatemala": ["guatemala", "guatemalteco"],
        "austria": ["austria", "austriaco", "viena"],
        "bulgaria": ["bulgaria", "bulgaro", "sofia"],
        "croacia": ["croacia", "croata", "zagreb"],
        "bielorrusia": ["bielorrusia", "belarus", "bielorruso", "minsk"],
        "serbia": ["serbia", "serbio", "belgrado"],
        "eslovenia": ["eslovenia", "esloveno", "liubliana"],
        "macedonia": ["macedonia", "macedonio", "skopje"]
    }
    
    for country, keywords in country_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return country
    return None

def detect_operator(text):
    """Detecta operadora de telecomunicaciones"""
    text_lower = text.lower()
    if "claro" in text_lower:
        return "claro"
    elif "telcel" in text_lower:
        return "telcel"
    elif "a1" in text_lower:
        return "a1"
    return None

def detect_health_topic(text):
    """Detecta tema específico de salud"""
    text_lower = text.lower()
    
    health_topics = {
        "diabetes": ["diabetes", "diabetico", "diabética", "glucosa", "insulina", "azucar en sangre"],
        "obesidad_nutricion": ["obesidad", "sobrepeso", "nutricion", "dieta", "alimentacion", "bajar de peso"],
        "hipertension_corazon": ["hipertension", "presion alta", "corazon", "cardiaco", "cardiovascular"],
        "cancer": ["cancer", "cáncer", "tumor", "oncologia", "oncológico", "mama", "prostata"],
        "salud_mental": ["depresion", "ansiedad", "estres", "mental", "psicologico", "psicológico"],
        "edad": ["niño", "niña", "bebe", "bebé", "adolescente", "adulto", "anciano", "tercera edad"]
    }
    
    for topic, keywords in health_topics.items():
        if any(keyword in text_lower for keyword in keywords):
            return topic
    return None

def detect_education_topic(text):
    """Detecta tema específico de educación"""
    text_lower = text.lower()
    
    education_topics = {
        "digital_tech": ["programacion", "programación", "tecnologia", "tecnología", "digital", "computacion", "computación", "software"],
        "finanzas": ["finanzas", "dinero", "inversion", "inversión", "ahorro", "credito", "crédito"],
        "emprendimiento": ["emprender", "negocio", "empresa", "autoempleo", "emprendedor"],
        "basica": ["primaria", "secundaria", "basica", "básica", "niños", "escolar"],
        "superior": ["universidad", "licenciatura", "carrera", "profesional", "superior"],
        "idiomas": ["ingles", "inglés", "idioma", "lenguaje"],
        "capacitacion": ["curso", "capacitacion", "capacitación", "aprender", "estudiar", "diplomado"]
    }
    
    for topic, keywords in education_topics.items():
        if any(keyword in text_lower for keyword in keywords):
            return topic
    return None

def extract_relevant_urls(prompt):
    """Extrae URLs relevantes basándose en la consulta del usuario"""
    # Manejo si URLS no fue definido por el usuario (placeholder)
    if not URLS:
        return []
    relevant_urls = []
    country = detect_country(prompt)
    operator = detect_operator(prompt)
    health_topic = detect_health_topic(prompt)
    education_topic = detect_education_topic(prompt)
    
    # SALUD
    if health_topic:
        if health_topic == "edad":
            # Agregar todos los manuales por edad
            for age_range, urls in URLS.get("health", {}).get("manual_por_edad_clikisalud", {}).items():
                relevant_urls.extend(urls)
        else:
            # Agregar recursos generales de salud
            relevant_urls.extend(URLS.get("health", {}).get("cuidado_personal_y_profesional", []))
            
            # Agregar URLs específicas del tema
            if health_topic in URLS.get("health", {}).get("prevencion_y_enfermedades", {}):
                relevant_urls.extend(URLS["health"]["prevencion_y_enfermedades"][health_topic])
            
            # Agregar cursos relacionados
            relevant_urls.extend(URLS.get("health", {}).get("cursos_cuidado_salud", [])[:3])
    
    # EDUCACIÓN
    elif education_topic:
        # Agregar plataforma principal
        relevant_urls.extend(URLS.get("education_career", {}).get("aprende_org_general", {}).get("principal", []))
        relevant_urls.extend(URLS.get("education_career", {}).get("aprende_org_general", {}).get("areas_principales", []))
        
        # URLs específicas por país si aplica
        if country and country in URLS.get("education_career", {}).get("plataformas_nacionales", {}):
            relevant_urls.extend(URLS["education_career"]["plataformas_nacionales"][country])
        
        # URLs específicas por tema
        if education_topic == "digital_tech":
            relevant_urls.extend(URLS.get("education_career", {}).get("rutas_y_oficios", {}).get("digital_tech", []))
        elif education_topic == "finanzas":
            relevant_urls.extend(URLS.get("education_career", {}).get("rutas_y_oficios", {}).get("administracion_finanzas", []))
            relevant_urls.extend(URLS.get("education_career", {}).get("diplomados_especialidades", {}).get("administracion_finanzas", [])[:5])
        elif education_topic == "emprendimiento":
            relevant_urls.extend(URLS.get("education_career", {}).get("diplomados_especialidades", {}).get("autoempleo_negocio", []))
        elif education_topic == "basica":
            relevant_urls.extend(URLS.get("education_career", {}).get("educacion_detallada", {}).get("basica_y_media", []))
        elif education_topic == "superior":
            relevant_urls.extend(URLS.get("education_career", {}).get("educacion_detallada", {}).get("superior", []))
    
    # TELECOMUNICACIONES
    elif operator:
        if operator == "telcel":
            relevant_urls.extend(URLS.get("telcel", []))
        elif operator == "claro" and country:
            if country in URLS.get("claro", {}):
                relevant_urls.extend(URLS["claro"][country])
            else:
                # Agregar todas las opciones de Claro si no hay país específico
                for country_urls in URLS.get("claro", {}).values():
                    relevant_urls.extend(country_urls)
        elif operator == "a1" and country:
            if country in URLS.get("a1", {}):
                relevant_urls.extend(URLS["a1"][country])
            else:
                # Agregar todas las opciones de A1
                for country_urls in URLS.get("a1", {}).values():
                    relevant_urls.extend(country_urls)
    
    return list(set(relevant_urls))  # Eliminar duplicados

def get_context_for_query(prompt):
    """Genera contexto descriptivo y URLs relevantes para la consulta"""
    # Manejo si URLS o SYSTEM_PROMPT no fue definido por el usuario (placeholder)
    if not URLS:
        # Intentar detectar intención básica aún si no hay URLs definidas
        health_topic = detect_health_topic(prompt)
        education_topic = detect_education_topic(prompt)
        operator = detect_operator(prompt)
        context = []
        if health_topic:
            context.append("📋 ÁREA: SALUD Y BIENESTAR")
            if health_topic == "diabetes":
                context.append("Tema: Diabetes - Prevención, cuidados y manejo de la enfermedad")
            elif health_topic == "obesidad_nutricion":
                context.append("Tema: Obesidad y Nutrición - Alimentación saludable y control de peso")
            elif health_topic == "hipertension_corazon":
                context.append("Tema: Hipertensión y Salud Cardiovascular")
            elif health_topic == "cancer":
                context.append("Tema: Prevención y detección del cáncer")
            elif health_topic == "salud_mental":
                context.append("Tema: Salud Mental - Manejo de estrés, ansiedad y depresión")
            elif health_topic == "edad":
                context.append("Tema: Manuales de salud organizados por grupos de edad")
        elif education_topic:
            context.append("📚 ÁREA: EDUCACIÓN Y DESARROLLO PROFESIONAL")
            if education_topic == "digital_tech":
                context.append("Tema: Tecnología y Programación - Cursos de desarrollo digital")
            elif education_topic == "finanzas":
                context.append("Tema: Finanzas Personales - Educación financiera y manejo de dinero")
            elif education_topic == "emprendimiento":
                context.append("Tema: Emprendimiento - Cómo iniciar y gestionar un negocio")
            elif education_topic == "basica":
                context.append("Tema: Educación Básica y Media - Recursos para estudiantes de primaria y secundaria")
            elif education_topic == "superior":
                context.append("Tema: Educación Superior - Cursos universitarios y profesionales")
            elif education_topic == "capacitacion":
                context.append("Tema: Capacitación y Desarrollo de Habilidades")
        elif operator:
            context.append("🌐 ÁREA: TELECOMUNICACIONES")
            if operator == "telcel":
                context.append("Operador: Telcel México - Servicios de telefonía móvil")
            elif operator == "claro":
                context.append("Operador: Claro")
            elif operator == "a1":
                context.append("Operador: A1 Group (Europa)")
        else:
            context.append("ℹ️ Asistente general disponible para Telecomunicaciones, Educación y Salud")
        return "\n".join(context) if context else "Información general disponible"

    country = detect_country(prompt)
    operator = detect_operator(prompt)
    health_topic = detect_health_topic(prompt)
    education_topic = detect_education_topic(prompt)
    
    context = []
    
    # SALUD
    if health_topic:
        context.append("📋 ÁREA: SALUD Y BIENESTAR")
        if health_topic == "diabetes":
            context.append("Tema: Diabetes - Prevención, cuidados y manejo de la enfermedad")
        elif health_topic == "obesidad_nutricion":
            context.append("Tema: Obesidad y Nutrición - Alimentación saludable y control de peso")
        elif health_topic == "hipertension_corazon":
            context.append("Tema: Hipertensión y Salud Cardiovascular")
        elif health_topic == "cancer":
            context.append("Tema: Prevención y detección del cáncer")
        elif health_topic == "salud_mental":
            context.append("Tema: Salud Mental - Manejo de estrés, ansiedad y depresión")
        elif health_topic == "edad":
            context.append("Tema: Manuales de salud organizados por grupos de edad")
    
    # EDUCACIÓN
    elif education_topic:
        context.append("📚 ÁREA: EDUCACIÓN Y DESARROLLO PROFESIONAL")
        if education_topic == "digital_tech":
            context.append("Tema: Tecnología y Programación - Cursos de desarrollo digital")
        elif education_topic == "finanzas":
            context.append("Tema: Finanzas Personales - Educación financiera y manejo de dinero")
        elif education_topic == "emprendimiento":
            context.append("Tema: Emprendimiento - Cómo iniciar y gestionar un negocio")
        elif education_topic == "basica":
            context.append("Tema: Educación Básica y Media - Recursos para estudiantes de primaria y secundaria")
        elif education_topic == "superior":
            context.append("Tema: Educación Superior - Cursos universitarios y profesionales")
        elif education_topic == "capacitacion":
            context.append("Tema: Capacitación y Desarrollo de Habilidades")
        
        if country:
            country_names = {
                "el_salvador": "El Salvador",
                "colombia": "Colombia",
                "nicaragua": "Nicaragua",
                "honduras": "Honduras",
                "guatemala": "Guatemala",
                "peru": "Perú"
            }
            if country in country_names:
                context.append(f"País: {country_names[country]} - Plataforma Aprende con Claro disponible")
    
    # TELECOMUNICACIONES
    elif operator:
        context.append("🌐 ÁREA: TELECOMUNICACIONES")
        if operator == "telcel":
            context.append("Operador: Telcel México - Servicios de telefonía móvil")
        elif operator == "claro":
            context.append("Operador: Claro")
            if country:
                country_names = {
                    "argentina": "Argentina",
                    "peru": "Perú",
                    "chile": "Chile"
                }
                if country in country_names:
                    context.append(f"País: {country_names[country]}")
        elif operator == "a1":
            context.append("Operador: A1 Group (Europa)")
            if country:
                country_names = {
                    "austria": "Austria",
                    "bulgaria": "Bulgaria",
                    "croacia": "Croacia",
                    "bielorrusia": "Bielorrusia",
                    "serbia": "Serbia",
                    "eslovenia": "Eslovenia",
                    "macedonia": "Macedonia del Norte"
                }
                if country in country_names:
                    context.append(f"País: {country_names[country]}")
    
    else:
        context.append("ℹ️ Asistente general disponible para Telecomunicaciones, Educación y Salud")
    
    return "\n".join(context) if context else "Información general disponible"

def call_groq_api_directly(messages):
    """Llamada directa a la API de Groq como fallback"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "openai/gpt-oss-20b",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2048
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

# ==================== ENDPOINTS ====================
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy", 
        "service": "Telecom Copilot API v2.0",
        "ai_ready": client is not None or GROQ_API_KEY is not None,
        "features": ["telecomunicaciones", "educación", "salud"]
    })

@app.route('/chat', methods=['POST'])
def chat():
    """Endpoint principal de chat con contexto mejorado"""
    try:
        if not client and not GROQ_API_KEY:
            return jsonify({
                "success": False,
                "error": "Servicio de IA no disponible"
            }), 503
        
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({
                "success": False,
                "error": "Mensaje vacío"
            }), 400
        
        # ================= Memoria local por cliente =================
        # Tomamos hasta 3 mensajes anteriores del mismo cliente (si existen)
        try:
            user_key = _get_user_key()
            mem = CHAT_MEMORY.get(user_key, [])
            # prev_messages son los mensajes anteriores (hasta 3)
            prev_messages = mem[-3:] if mem else []
        except Exception:
            # En caso de cualquier error con la memoria, no interrumpimos la ejecución
            prev_messages = []
            user_key = None
        
        # Actualizamos la memoria con el nuevo mensaje (guardamos máximo 3)
        try:
            if user_key is not None:
                mem = CHAT_MEMORY.get(user_key, [])
                mem.append(user_message)
                # Mantener solo los últimos 3 mensajes
                if len(mem) > 3:
                    mem = mem[-3:]
                CHAT_MEMORY[user_key] = mem
        except Exception:
            # si falla, no queremos que fallé el endpoint
            pass
        # ===========================================================
        
        # Obtener contexto y URLs relevantes (métodos seguros si URLS/SYSTEM_PROMPT dejaron como placeholders)
        context = safe_get_context_for_query(user_message)
        relevant_urls = safe_extract_relevant_urls(user_message)
        
        # Formatear URLs para el prompt
        urls_text = ""
        if relevant_urls:
            urls_text = "Enlaces útiles:\n" + "\n".join([f"- {url}" for url in relevant_urls[:10]])  # Limitar a 10 URLs
        else:
            urls_text = "Explora nuestras áreas: Telecomunicaciones, Educación (aprende.org) y Salud (clikisalud.net)"
        
        # Preparar mensajes para Groq
        # El SYSTEM_PROMPT fue pedido como placeholder por el usuario; el siguiente formateo lo mantendrá tal cual.
        try:
            formatted_prompt = SYSTEM_PROMPT.format(context=context, urls=urls_text)
        except Exception:
            # Si SYSTEM_PROMPT es {}, usamos un prompt por defecto mínimo
            formatted_prompt = f"Eres un asistente. Contexto:\n{context}\n\n{urls_text}"
        
        # Construir la secuencia de mensajes incluyendo los hasta 3 mensajes previos del usuario
        messages = [
            {"role": "system", "content": formatted_prompt}
        ]
        
        # Incluir mensajes previos como contexto adicional (si existen)
        for pm in prev_messages:
            # Evitar duplicar exactamente el mensaje actual
            if pm and pm.strip() and pm.strip() != user_message.strip():
                messages.append({"role": "user", "content": pm})
        
        # Finalmente agregar el mensaje actual
        messages.append({"role": "user", "content": user_message})
        
        # Llamar a Groq
        if client and client != "api_fallback":
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.7,
                max_tokens=2048
            )
            response = completion.choices[0].message.content 
            
        else:
            result = call_groq_api_directly(messages)
            response = result["choices"][0]["message"]["content"]
            
        
        # Devolver también qué mensajes previos se usaron (útil para depuración; puede quitarse si se desea)
        return jsonify({
            "success": True,
            "response": response,
            "context": context,
            "relevant_urls": relevant_urls[:5],  # Devolver las 5 URLs más relevantes
            "memory_used": prev_messages  # <-- aquí se muestran los mensajes previos que se incluyeron
        })
        
    except Exception as e:
        logger.error(f"Error en /chat: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/urls', methods=['POST'])
def get_urls():
    """Endpoint para obtener URLs específicas según consulta"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({
                "success": False,
                "error": "Query vacío"
            }), 400
        
        relevant_urls = safe_extract_relevant_urls(query)
        context = safe_get_context_for_query(query)
        
        return jsonify({
            "success": True,
            "context": context,
            "urls": relevant_urls,
            "count": len(relevant_urls)
        })
        
    except Exception as e:
        logger.error(f"Error en /urls: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ==================== SERVIR FRONTEND ====================
@app.route('/')
def serve_frontend():
    """Servir el frontend HTML"""
    try:
        with open('../frontend/index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error cargando frontend: {str(e)}", 500

@app.route('/images/<path:filename>')
def serve_images(filename):
    """Servir imágenes"""
    try:
        with open(f'../frontend/images/{filename}', 'rb') as f:
            content = f.read()
            # Detectar tipo de imagen por extensión
            content_type = 'image/png'
            if filename.endswith('.jpg') or filename.endswith('.jpeg'):
                content_type = 'image/jpeg'
            elif filename.endswith('.svg'):
                content_type = 'image/svg+xml'
            elif filename.endswith('.ico'):
                content_type = 'image/x-icon'
            elif filename.endswith('.gif'):
                content_type = 'image/gif'
            elif filename.endswith('.webp'):
                content_type = 'image/webp'
            
            return content, 200, {'Content-Type': content_type}
    except Exception as e:
        logger.error(f"Error sirviendo imagen {filename}: {str(e)}")
        return f"Imagen no encontrada: {filename}", 404

@app.route('/<path:path>')
def serve_static(path):
    """Servir archivos estáticos"""
    try:
        if path.startswith('styles/'):
            with open(f'../frontend/{path}', 'r', encoding='utf-8') as f:
                return f.read(), 200, {'Content-Type': 'text/css'}
        elif path.startswith('js/'):
            with open(f'../frontend/{path}', 'r', encoding='utf-8') as f:
                return f.read(), 200, {'Content-Type': 'application/javascript'}
        else:
            with open(f'../frontend/{path}', 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        return f"Archivo no encontrado: {path}", 404

if __name__ == '__main__':
    logger.info(f"🚀 Iniciando Telecom Copilot v2.0 en http://localhost:{PORT}")
    logger.info("📚 Áreas disponibles: Telecomunicaciones | Educación | Salud")
    app.run(host='0.0.0.0', port=PORT, debug=False)
