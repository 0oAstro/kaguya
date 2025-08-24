#!/bin/bash

echo "🧪 Running Simple API Tests..."

# Set test environment variables
export SPOTIFY_CLIENT_ID="test_id"
export SPOTIFY_CLIENT_SECRET="test_secret"

# Run simple tests
uv run pytest test_simple.py -v

echo "✅ Simple tests completed!"
