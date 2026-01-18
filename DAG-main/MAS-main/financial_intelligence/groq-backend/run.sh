#!/bin/bash

# WebGPT Startup Script

echo "🚀 Starting WebGPT Server..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found! Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env file. Please add your API keys!"
        echo "   - OPENAI_API_KEY"
        echo "   - TAVILY_API_KEY"
        exit 1
    else
        echo "❌ .env.example not found!"
        exit 1
    fi
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Run the FastAPI server
echo "✨ Starting FastAPI server on http://localhost:8000"
echo "📚 API docs available at http://localhost:8000/docs"
echo ""
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload