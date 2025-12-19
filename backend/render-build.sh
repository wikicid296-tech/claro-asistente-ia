#!/usr/bin/env bash
# render-build.sh

set -o errexit

echo "📦 Instalando dependencias de Python..."
pip install --upgrade pip
pip install -r requirements.txt


echo "✅ Build completado exitosamente"