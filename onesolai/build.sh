#!/usr/bin/env bash
# build.sh — Render build script for OneSol AI Hub
# Runs automatically on every deploy.

set -o errexit   # Stop on any error

echo "🔧 Installing Python dependencies..."
pip install -r requirements.txt

echo "📦 Collecting static files..."
python manage.py collectstatic --no-input

echo "🗃️  Running database migrations..."
python manage.py migrate --no-input

echo "✅ Build complete!"
