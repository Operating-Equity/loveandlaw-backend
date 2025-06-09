#!/bin/bash
# Quick start script for LoveAndLaw backend

echo "🚀 Starting LoveAndLaw Backend Setup..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install minimal dependencies
echo "📥 Installing dependencies..."
pip install -r requirements-minimal.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "Please add your GROQ_API_KEY to the .env file"
    exit 1
fi

# Check if Elasticsearch is running
echo "🔍 Checking Elasticsearch..."
if ! curl -s http://localhost:9200 > /dev/null; then
    echo "⚠️  Elasticsearch is not running!"
    echo "Run: ./start-elasticsearch.sh"
    exit 1
fi

# Load sample data
echo "📊 Loading sample lawyer data..."
python scripts/populate_lawyers.py

# Start the server
echo "✨ Starting LoveAndLaw API server..."
echo "📍 API will be available at: http://localhost:8000"
echo "📚 API docs: http://localhost:8000/docs"
echo ""
python run_minimal.py