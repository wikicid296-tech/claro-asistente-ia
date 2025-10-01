from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from services import process_chat_message
import logging
import asyncio

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Telecom Copilot API", version="1.0.0")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos de datos
class ChatRequest(BaseModel):
    message: str
    action: str = None

class ChatResponse(BaseModel):
    success: bool
    response: str
    error: str = None

# Endpoint principal del chat
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        logger.info(f"Procesando mensaje: {request.message}")
        
        response = await process_chat_message(request.message, request.action)
        
        return ChatResponse(
            success=True,
            response=response
        )
    except Exception as e:
        logger.error(f"Error en endpoint /api/chat: {str(e)}")
        return ChatResponse(
            success=False,
            response="",
            error=str(e)
        )

# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "Telecom Copilot API"}

# Servir el frontend
@app.get("/")
async def serve_frontend():
    return FileResponse('../frontend/index.html')

# Servir archivos estáticos del frontend
app.mount("/", StaticFiles(directory="../frontend"), name="frontend")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)