# Simple API Tests

Basic tests for the Kaguya Music Mood API endpoints.

## Setup

Dependencies are managed with `uv`. All required packages are already added to the project.

## Running Tests

```bash
# Run all simple tests
./run_simple_tests.sh

# Or run with uv directly  
uv run pytest test_simple.py -v
```

## Test Coverage

The simple tests cover:

- ✅ Root endpoint (`/`)
- ✅ Health check (`/health`) 
- ✅ Get available moods (`/moods`)
- ✅ Mood detection with invalid data
- ✅ Playlist with invalid mood
- ✅ Playlist with valid mood
- ✅ Upload image endpoint validation

## Test Results

All tests should pass with status codes:
- `200` for successful requests
- `400` for bad requests (invalid data)
- `422` for validation errors
- `503` for service unavailable (when models not loaded)

The tests are designed to work whether or not you have:
- Spotify credentials configured
- The MoodDetector.h5 model file
- Proper environment setup

This makes them useful for CI/CD and basic functionality verification.
