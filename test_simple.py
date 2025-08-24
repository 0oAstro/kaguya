"""
Simple tests for the Kaguya Music Mood API
"""
import pytest
from fastapi.testclient import TestClient
from backend import app

# Create test client
client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint works"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data

def test_get_moods():
    """Test getting available moods"""
    response = client.get("/moods")
    assert response.status_code == 200
    data = response.json()
    assert "moods" in data
    assert isinstance(data["moods"], list)

def test_mood_detection_invalid_data():
    """Test mood detection with invalid data"""
    response = client.post("/detect-mood", json={
        "image_base64": "invalid_data"
    })
    # Should return error (400 or 503)
    assert response.status_code in [400, 503]

def test_playlist_invalid_mood():
    """Test playlist with invalid mood"""
    response = client.get("/playlist/InvalidMood")
    assert response.status_code in [400, 503]  # Invalid mood or service unavailable

def test_playlist_valid_mood():
    """Test playlist with valid mood"""
    response = client.get("/playlist/Happy")
    # Should work if Spotify is configured, otherwise 503
    assert response.status_code in [200, 503]

def test_upload_image_no_file():
    """Test upload endpoint without file"""
    response = client.post("/upload-image")
    assert response.status_code == 422  # Validation error

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
