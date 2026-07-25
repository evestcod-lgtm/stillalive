#!/bin/bash
# StillAliveGhost Backend Startup Script

set -e

echo "🚀 StillAliveGhost Backend Starting..."

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "✓ Created .env file. Edit it with your API keys."
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt || pip install -r requirements.txt --break-system-packages

# Start server
echo "✓ Starting FastAPI server on http://0.0.0.0:8000"
python -m uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload
