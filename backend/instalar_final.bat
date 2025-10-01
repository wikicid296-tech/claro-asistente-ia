@echo off
cd /d "C:\Users\floreseh\Documents\telecom-copilot\backend"
echo Instalando dependencias compatibles con Python 3.13...

pip install fastapi uvicorn python-dotenv groq beautifulsoup4 requests python-multipart aiohttp

echo.
echo Verificando instalaciones...
python -c "import fastapi; print('✅ FastAPI instalado')"
python -c "import uvicorn; print('✅ Uvicorn instalado')" 
python -c "import groq; print('✅ Groq instalado')"
python -c "import bs4; print('✅ BeautifulSoup4 instalado')"
python -c "import aiohttp; print('✅ aiohttp instalado')"

echo.
echo Iniciando servidor...
python app.py
pause
