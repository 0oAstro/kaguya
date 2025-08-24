#!/bin/bash

# Kaguya Music Mood API - Startup Script

echo "🎵 Starting Kaguya Music Mood API Backend..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please create a .env file with your Spotify credentials:"
    echo ""
    echo "SPOTIFY_CLIENT_ID=your_client_id_here"
    echo "SPOTIFY_CLIENT_SECRET=your_client_secret_here"
    echo "SPOTIFY_MARKET=IN"
    echo ""
    exit 1
fi

# Check if MoodDetector.h5 exists
if [ ! -f "MoodDetector.h5" ]; then
    echo "❌ MoodDetector.h5 model file not found!"
    echo "Please ensure the mood detection model is in the project root."
    exit 1
fi

# Check if dependencies are installed
echo "📦 Checking dependencies..."
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📥 Installing dependencies with uv..."
    uv sync
fi

# Start the server
echo "🚀 Starting FastAPI server..."
echo "🌐 API will be available at: http://localhost:8000"
echo "📖 Documentation at: http://localhost:8000/docs"
echo "❤️  Health check at: http://localhost:8000/health"
echo ""

# Run with uvicorn via uv
uv run uvicorn backend:app --host 0.0.0.0 --port 8000 --reload &
pnpm run dev
