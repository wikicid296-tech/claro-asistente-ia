#!/usr/bin/env bash
# build.sh - Script de construcción para Render

echo "🚀 Iniciando build en Render..."
echo "================================"

echo "📦 Actualizando pip..."
pip install --upgrade pip

echo "📚 Instalando dependencias de Python..."
pip install -r requirements.txt

echo "🌐 Descargando Chromium para pyppeteer..."
python -m pyppeteer.install

echo "✅ Build completado exitosamente!"
echo "================================"