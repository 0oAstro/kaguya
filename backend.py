import os
import cv2
import numpy as np
import pandas as pd
import base64
import io
from PIL import Image
from typing import Optional, List, Dict, Any
import asyncio
import logging

# FastAPI imports
from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ML and Spotify imports
import tensorflow as tf
from tensorflow.keras.models import load_model
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import urllib.parse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Kaguya Music Mood API",
    description="AI-powered mood detection from video stream with Spotify playlist recommendations",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================
# Global Variables and Models
# ==============================

# Mood model and face cascade
mood_model = None
face_cascade = None
spotify_client = None
spotify_oauth = None

# Store created playlist URLs to avoid duplicates
created_playlists = {}  # {mood: playlist_url}

# Mood mapping
MOOD_LABELS = {
    0: "Angry",
    1: "Disgust", 
    2: "Fear",
    3: "Happy",
    4: "Sad",
    5: "Surprise",
    6: "Neutral"
}

# ==============================
# Pydantic Models
# ==============================

class MoodDetectionRequest(BaseModel):
    image_base64: str

class MoodDetectionResponse(BaseModel):
    mood: str
    confidence: float
    playlist_url: Optional[str] = None
    recommendations: List[Dict[str, Any]] = []

class PlaylistRequest(BaseModel):
    mood: str
    limit: int = 20

class PlaylistResponse(BaseModel):
    mood: str
    playlist_url: Optional[str] = None
    tracks: List[Dict[str, Any]] = []

class SpotifyAuthResponse(BaseModel):
    auth_url: str
    
class CreatePlaylistRequest(BaseModel):
    mood: str
    track_ids: List[str]
    access_token: str
    user_id: Optional[str] = None

# ==============================
# Initialization Functions
# ==============================

def load_mood_model():
    """Load the pre-trained mood detection model"""
    global mood_model
    try:
        model_path = "MoodDetector.h5"
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        mood_model = load_model(model_path, compile=False)
        logger.info("✅ Mood detection model loaded successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to load mood model: {e}")
        return False

def load_face_cascade():
    """Load OpenCV face cascade"""
    global face_cascade
    try:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)
        
        if face_cascade.empty():
            raise Exception("Failed to load face cascade")
        
        logger.info("✅ Face cascade loaded successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to load face cascade: {e}")
        return False

def initialize_spotify():
    """Initialize Spotify client with OAuth support for playlist creation"""
    global spotify_client, spotify_oauth
    try:
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            logger.warning("Spotify credentials not found - playlist creation will be disabled")
            return False
        
        # Initialize OAuth for playlist creation with automatic token management
        redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8000/callback")
        spotify_oauth = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="playlist-modify-public playlist-modify-private user-read-private",
            cache_path=".spotify_cache",
            show_dialog=False
        )
        
        # Also keep the basic client for search functionality
        auth_manager = SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret
        )
        spotify_client = spotipy.Spotify(auth_manager=auth_manager)
        
        # Test the connection
        spotify_client.search(q="test", type="track", limit=1)
        logger.info("✅ Spotify client initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize Spotify client: {e}")
        return False

def get_authenticated_spotify_client():
    """Get an authenticated Spotify client for playlist creation"""
    try:
        if not spotify_oauth:
            return None
            
        # Try to get cached token
        token_info = spotify_oauth.get_cached_token()
        
        if not token_info:
            logger.info("No cached Spotify token found - playlist creation will use search URLs")
            return None
            
        # Create authenticated client
        sp = spotipy.Spotify(auth=token_info['access_token'])
        
        # Test if token is still valid
        try:
            sp.current_user()
            logger.info("✅ Using authenticated Spotify client for playlist creation")
            return sp
        except Exception as e:
            logger.warning(f"Spotify token invalid: {e}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting authenticated Spotify client: {e}")
        return None

# ==============================
# Mood Detection Functions
# ==============================

def detect_mood_from_image(image_array: np.ndarray) -> tuple:
    """
    Detect mood from a face image array
    Returns: (mood_name, confidence)
    """
    try:
        if mood_model is None:
            raise Exception("Mood model not loaded")
        
        # Convert to grayscale if needed
        if len(image_array.shape) == 3:
            gray_image = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        else:
            gray_image = image_array
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray_image, 1.3, 5)
        
        if len(faces) == 0:
            return None, 0.0
        
        # Get the largest face
        largest_face = max(faces, key=lambda face: face[2] * face[3])
        x, y, w, h = largest_face
        
        # Extract face region
        face_roi = gray_image[y:y+h, x:x+w]
        
        # Resize to model input size (48x48)
        face_resized = cv2.resize(face_roi, (48, 48))
        
        # Normalize and reshape for model
        face_normalized = face_resized.astype('float32') / 255.0
        face_input = np.expand_dims(face_normalized, axis=0)
        face_input = np.expand_dims(face_input, axis=-1)
        
        # Predict mood
        predictions = mood_model.predict(face_input, verbose=0)
        mood_index = np.argmax(predictions[0])
        confidence = float(np.max(predictions[0]))
        
        mood_name = MOOD_LABELS.get(mood_index, "Unknown")
        
        return mood_name, confidence
        
    except Exception as e:
        logger.error(f"Error in mood detection: {e}")
        return None, 0.0

def base64_to_image(base64_string: str) -> np.ndarray:
    """Convert base64 string to image array"""
    try:
        # Remove data URL prefix if present
        if "," in base64_string:
            base64_string = base64_string.split(",")[1]
        
        # Decode base64
        image_data = base64.b64decode(base64_string)
        
        # Convert to PIL Image
        pil_image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if needed
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Convert to numpy array
        image_array = np.array(pil_image)
        
        return image_array
        
    except Exception as e:
        logger.error(f"Error converting base64 to image: {e}")
        raise HTTPException(status_code=400, detail="Invalid image data")

# ==============================
# Spotify Integration Functions
# ==============================

def get_mood_search_query(mood: str) -> str:
    """Map mood to Spotify search parameters"""
    mood_queries = {
        "Happy": "happy upbeat pop dance bollywood energetic",
        "Sad": "sad melancholic acoustic emotional hindi heartbreak",
        "Angry": "angry rock metal aggressive rap hindi",
        "Fear": "ambient dark atmospheric calm soothing",
        "Surprise": "electronic experimental pop energetic dance",
        "Disgust": "rock alternative metal angry",
        "Neutral": "pop indie chill relaxed"
    }
    return mood_queries.get(mood, "pop music")

def search_spotify_by_mood(mood: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search Spotify for tracks based on mood"""
    try:
        if spotify_client is None:
            raise Exception("Spotify client not initialized")
        
        search_query = get_mood_search_query(mood)
        market = os.getenv("SPOTIFY_MARKET", "US")
        
        # Search for tracks with higher limit to account for duplicates
        search_limit = min(limit * 2, 50)  # Search more tracks to filter duplicates
        
        results = spotify_client.search(
            q=search_query, 
            type='track', 
            limit=search_limit,
            market=market
        )
        
        tracks = []
        seen_track_ids = set()  # Track unique track IDs
        
        for track in results['tracks']['items']:
            if not track:
                continue
            
            # Skip if we've already seen this track ID
            if track['id'] in seen_track_ids:
                continue
                
            # Get artist name
            artist_name = track['artists'][0]['name'] if track['artists'] else "Unknown Artist"
            
            # Get album image
            image_url = None
            if track['album']['images']:
                # Get medium size image (usually index 1)
                if len(track['album']['images']) > 1:
                    image_url = track['album']['images'][1]['url']
                else:
                    image_url = track['album']['images'][0]['url']
            
            track_info = {
                'id': track['id'],
                'name': track['name'],
                'artist': artist_name,
                'album': track['album']['name'],
                'image_url': image_url,
                'preview_url': track['preview_url'],
                'spotify_url': track['external_urls']['spotify'],
                'duration_ms': track['duration_ms'],
                'popularity': track['popularity']
            }
            
            tracks.append(track_info)
            seen_track_ids.add(track['id'])
            
            # Stop if we have enough unique tracks
            if len(tracks) >= limit:
                break
        
        logger.info(f"Found {len(tracks)} unique tracks for mood '{mood}' (filtered from {len(results['tracks']['items'])} total)")
        return tracks
        
    except Exception as e:
        logger.error(f"Error searching Spotify: {e}")
        return []

def create_spotify_playlist_url(tracks: List[Dict[str, Any]], mood: str = None) -> str:
    """Create a Spotify playlist URL from track data (fallback for non-authenticated users)"""
    try:
        if not tracks:
            return None
        
        # Try to get track IDs first for a more direct link
        track_ids = [track.get('id') for track in tracks if track.get('id')]
        
        if track_ids:
            # Create a search URL with specific tracks for better results
            track_names = []
            for track in tracks[:5]:  # Use first 5 tracks
                if track.get('name') and track.get('artist'):
                    track_names.append(f"{track['name']} {track['artist']}")
            
            if track_names:
                search_query = " ".join(track_names)
                if mood:
                    search_query = f"{mood} {search_query}"
                encoded_query = urllib.parse.quote(search_query)
                return f"https://open.spotify.com/search/{encoded_query}"
        
        # Fallback: create search URL with track names
        track_names = []
        for track in tracks[:5]:  # Limit to first 5 tracks for search
            if track.get('name') and track.get('artist'):
                track_names.append(f"{track['name']} {track['artist']}")
        
        if track_names:
            search_query = " ".join(track_names)
            if mood:
                search_query = f"{mood} mood {search_query}"
            encoded_query = urllib.parse.quote(search_query)
            return f"https://open.spotify.com/search/{encoded_query}"
        
        # Ultimate fallback: mood-based search
        mood_search = mood.lower() if mood else "mood"
        return f"https://open.spotify.com/search/{mood_search}%20music"
        
    except Exception as e:
        logger.error(f"Error creating playlist URL: {e}")
        return f"https://open.spotify.com/search/mood%20music"

def create_actual_spotify_playlist(tracks: List[Dict[str, Any]], mood: str) -> str:
    """Create an actual Spotify playlist with tracks using backend authentication"""
    try:
        if not tracks:
            return None
            
        # Check if we already created a playlist for this mood
        if mood in created_playlists:
            logger.info(f"✅ Reusing existing playlist for mood '{mood}': {created_playlists[mood]}")
            return created_playlists[mood]
            
        # Get authenticated Spotify client
        sp = get_authenticated_spotify_client()
        if not sp:
            logger.info("No authenticated Spotify client - no playlist created")
            return None
            
        # Get user info
        user_info = sp.current_user()
        user_id = user_info['id']
        
        # Create playlist
        playlist_name = f"kaguya {mood.lower()} mood"
        playlist_description = f"curated {mood.lower()} playlist generated by kaguya ai mood detection"
        
        playlist = sp.user_playlist_create(
            user=user_id,
            name=playlist_name,
            public=True,
            description=playlist_description
        )
        
        # Get track URIs (ensure no duplicates)
        track_uris = []
        seen_uris = set()
        for track in tracks[:50]:  # Spotify allows max 100 tracks per request, we'll use 50
            if track.get('id'):
                track_uri = f"spotify:track:{track['id']}"
                if track_uri not in seen_uris:
                    track_uris.append(track_uri)
                    seen_uris.add(track_uri)
        
        # Add tracks to playlist
        if track_uris:
            sp.playlist_add_items(playlist['id'], track_uris)
        
        playlist_url = playlist['external_urls']['spotify']
        
        # Store the playlist URL to avoid duplicates
        created_playlists[mood] = playlist_url
        
        logger.info(f"✅ Created public Spotify playlist: {playlist['name']} with {len(track_uris)} tracks")
        return playlist_url
        
    except Exception as e:
        logger.error(f"Error creating Spotify playlist: {e}")
        # Don't return search URLs - only real playlists
        return None

# ==============================
# API Endpoints
# ==============================

@app.on_event("startup")
async def startup_event():
    """Initialize models and services on startup"""
    logger.info("🚀 Starting Kaguya Music Mood API...")
    
    # Load mood detection model
    if not load_mood_model():
        logger.error("Failed to load mood model - mood detection will not work")
    
    # Load face cascade
    if not load_face_cascade():
        logger.error("Failed to load face cascade - face detection will not work")
    
    # Initialize Spotify
    if not initialize_spotify():
        logger.error("Failed to initialize Spotify - music recommendations will not work")
    
    logger.info("✅ Startup complete!")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Kaguya Music Mood API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "detect_mood": "/detect-mood",
            "get_playlist": "/playlist/{mood}",
            "mood_and_playlist": "/mood-and-playlist",
            "spotify_setup": "/spotify-setup",
            "spotify_auth_url": "/spotify-auth-url", 
            "spotify_callback": "/callback",
            "spotify_token": "/spotify-token",
            "cleanup": "/cleanup"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "mood_model_loaded": mood_model is not None,
        "face_cascade_loaded": face_cascade is not None,
        "spotify_search_available": spotify_client is not None,
        "spotify_playlist_creation": get_authenticated_spotify_client() is not None
    }

@app.post("/detect-mood", response_model=MoodDetectionResponse)
async def detect_mood(request: MoodDetectionRequest):
    """Detect mood from base64 encoded image"""
    try:
        if mood_model is None or face_cascade is None:
            raise HTTPException(status_code=503, detail="Mood detection models not loaded")
        
        # Convert base64 to image
        image_array = base64_to_image(request.image_base64)
        
        # Detect mood
        mood, confidence = detect_mood_from_image(image_array)
        
        if mood is None:
            raise HTTPException(status_code=400, detail="No face detected in image")
        
        return MoodDetectionResponse(
            mood=mood,
            confidence=confidence
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in mood detection endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/playlist/{mood}", response_model=PlaylistResponse)
async def get_playlist_by_mood(mood: str, limit: int = 20):
    """Get Spotify playlist recommendations based on mood"""
    try:
        if spotify_client is None:
            raise HTTPException(status_code=503, detail="Spotify client not initialized")
        
        # Validate mood
        if mood not in MOOD_LABELS.values():
            raise HTTPException(status_code=400, detail=f"Invalid mood. Valid moods: {list(MOOD_LABELS.values())}")
        
        # Search for tracks
        tracks = search_spotify_by_mood(mood, limit)
        
        if not tracks:
            raise HTTPException(status_code=404, detail=f"No tracks found for mood: {mood}")
        
        # Try to create actual playlist - only return real playlist URLs
        playlist_url = create_actual_spotify_playlist(tracks, mood)
        if playlist_url:
            logger.info(f"✅ Real playlist created: {playlist_url}")
        else:
            logger.info("⚠️ No playlist created - only real playlists are returned")
        
        return PlaylistResponse(
            mood=mood,
            playlist_url=playlist_url,
            tracks=tracks
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in playlist endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/mood-and-playlist", response_model=MoodDetectionResponse)
async def detect_mood_and_get_playlist(request: MoodDetectionRequest, limit: int = 20):
    """Detect mood from image and return Spotify playlist recommendations"""
    try:
        if mood_model is None or face_cascade is None:
            raise HTTPException(status_code=503, detail="Mood detection models not loaded")
        
        if spotify_client is None:
            raise HTTPException(status_code=503, detail="Spotify client not initialized")
        
        # Convert base64 to image
        image_array = base64_to_image(request.image_base64)
        
        # Detect mood
        mood, confidence = detect_mood_from_image(image_array)
        
        if mood is None:
            raise HTTPException(status_code=400, detail="No face detected in image")
        
        # Get playlist recommendations
        tracks = search_spotify_by_mood(mood, limit)
        
        # Try to create actual playlist - only return real playlist URLs
        playlist_url = None
        if tracks:
            playlist_url = create_actual_spotify_playlist(tracks, mood)
            if playlist_url:
                logger.info(f"✅ Real playlist created and will be shown in QR code: {playlist_url}")
            else:
                logger.info("⚠️ No playlist created - QR code will not be shown")
        else:
            logger.warning(f"⚠️ No tracks found for mood '{mood}'")
        
        return MoodDetectionResponse(
            mood=mood,
            confidence=confidence,
            playlist_url=playlist_url,
            recommendations=tracks or []
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in mood and playlist endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/spotify-setup")
async def spotify_setup_info():
    """Get information about Spotify setup status"""
    try:
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        has_credentials = bool(client_id and client_secret)
        
        auth_client = get_authenticated_spotify_client()
        is_authenticated = auth_client is not None
        
        user_info = None
        if is_authenticated:
            try:
                user_info = auth_client.current_user()
            except:
                is_authenticated = False
        
        status_message = ""
        if is_authenticated:
            status_message = "✅ Ready to create real playlists!"
        elif has_credentials:
            status_message = "⚠️ Credentials found but not authenticated - visit /spotify-auth-url to setup"
        else:
            status_message = "❌ No Spotify credentials - add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET to .env"
        
        return {
            "has_credentials": has_credentials,
            "is_authenticated": is_authenticated,
            "user_info": {
                "id": user_info.get('id') if user_info else None,
                "display_name": user_info.get('display_name') if user_info else None
            } if user_info else None,
            "status": "ready" if is_authenticated else "needs_auth" if has_credentials else "needs_credentials",
            "message": status_message,
            "playlist_creation": "enabled" if is_authenticated else "disabled"
        }
        
    except Exception as e:
        logger.error(f"Error getting Spotify setup info: {e}")
        return {
            "has_credentials": False,
            "is_authenticated": False,
            "user_info": None,
            "status": "error",
            "message": "❌ Error checking Spotify setup",
            "playlist_creation": "disabled"
        }

@app.get("/spotify-auth-url")
async def get_spotify_auth_url():
    """Get Spotify authorization URL for manual authentication"""
    try:
        if not spotify_oauth:
            raise HTTPException(status_code=503, detail="Spotify OAuth not configured")
        
        auth_url = spotify_oauth.get_authorize_url()
        redirect_uri = spotify_oauth.redirect_uri
        
        return {
            "auth_url": auth_url,
            "redirect_uri": redirect_uri,
            "setup_instructions": [
                "FIRST TIME SETUP:",
                "1. Go to https://developer.spotify.com/dashboard",
                "2. Select your app (or create one)",
                "3. Click 'Edit Settings'", 
                f"4. Add '{redirect_uri}' to Redirect URIs",
                "5. Save the settings",
                "",
                "THEN AUTHENTICATE:",
                "6. Visit the auth_url below",
                "7. Authorize the application",
                "8. You'll be redirected back with the authorization code",
                "9. Copy the code shown on the callback page",
                "10. Use POST /spotify-token with that code"
            ],
            "example_redirect": f"Example: {redirect_uri}?code=ABC123... (copy the ABC123... part)"
        }
        
    except Exception as e:
        logger.error(f"Error getting Spotify auth URL: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/callback")
async def spotify_callback(code: str = None, error: str = None):
    """Handle Spotify OAuth callback and display the authorization code"""
    if error:
        return {
            "error": error,
            "message": "Authorization was denied or failed",
            "instructions": "Please try the authorization process again"
        }
    
    if not code:
        return {
            "error": "no_code",
            "message": "No authorization code received",
            "instructions": "Please try the authorization process again"
        }
    
    # Return the code so user can see it
    return {
        "success": True,
        "authorization_code": code,
        "message": "Authorization successful! Use the code below.",
        "instructions": [
            f"Your authorization code is: {code}",
            "",
            "Now send a POST request to /spotify-token with this code:",
            f"curl -X POST 'http://localhost:8000/spotify-token?code={code}'",
            "",
            "Or use any HTTP client to POST to /spotify-token with the code parameter"
        ],
        "auto_setup_url": f"http://localhost:8000/spotify-token?code={code}"
    }

@app.post("/spotify-token")
async def set_spotify_token(code: str):
    """Manually set Spotify token from authorization code"""
    try:
        if not spotify_oauth:
            raise HTTPException(status_code=503, detail="Spotify OAuth not configured")
        
        try:
            # Get access token
            token_info = spotify_oauth.get_access_token(code, as_dict=True)
            
            if not token_info:
                raise HTTPException(status_code=400, detail="Failed to get access token - check if code is correct")
            
            # Test the token by getting user info
            sp = spotipy.Spotify(auth=token_info['access_token'])
            user_info = sp.current_user()
            
            logger.info(f"✅ Spotify token successfully set for user: {user_info.get('display_name', user_info.get('id'))}")
            
            return {
                "status": "success",
                "message": "Spotify authentication successful - real playlists will now be created",
                "user": {
                    "id": user_info.get('id'),
                    "display_name": user_info.get('display_name'),
                    "email": user_info.get('email')
                },
                "expires_in": token_info.get("expires_in")
            }
            
        except spotipy.SpotifyException as e:
            logger.error(f"Spotify API error: {e}")
            if "invalid_grant" in str(e):
                raise HTTPException(status_code=400, detail="Invalid or expired authorization code")
            raise HTTPException(status_code=400, detail=f"Spotify error: {e}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting Spotify token: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/cleanup")
async def cleanup_kaguya_playlists():
    """Delete all kaguya playlists from Spotify account"""
    try:
        # Get authenticated Spotify client
        sp = get_authenticated_spotify_client()
        if not sp:
            raise HTTPException(status_code=503, detail="No authenticated Spotify client available")
        
        # Get user info
        user_info = sp.current_user()
        user_id = user_info['id']
        
        # Get all user playlists
        playlists = []
        offset = 0
        limit = 50
        
        while True:
            user_playlists = sp.current_user_playlists(limit=limit, offset=offset)
            playlists.extend(user_playlists['items'])
            
            if len(user_playlists['items']) < limit:
                break
            offset += limit
        
        # Filter kaguya playlists
        kaguya_playlists = []
        for playlist in playlists:
            if playlist['name'].lower().startswith('kaguya'):
                kaguya_playlists.append(playlist)
        
        if not kaguya_playlists:
            return {
                "status": "success",
                "message": "No kaguya playlists found to delete",
                "deleted_count": 0,
                "deleted_playlists": []
            }
        
        # Delete each kaguya playlist
        deleted_playlists = []
        for playlist in kaguya_playlists:
            try:
                sp.user_playlist_unfollow(user_id, playlist['id'])
                deleted_playlists.append({
                    "name": playlist['name'],
                    "id": playlist['id'],
                    "url": playlist['external_urls']['spotify']
                })
                logger.info(f"🗑️ Deleted playlist: {playlist['name']}")
            except Exception as e:
                logger.error(f"Failed to delete playlist {playlist['name']}: {e}")
        
        # Clear the stored playlist URLs
        global created_playlists
        created_playlists.clear()
        
        logger.info(f"🧹 Cleanup complete: deleted {len(deleted_playlists)} kaguya playlists")
        
        return {
            "status": "success",
            "message": f"Successfully deleted {len(deleted_playlists)} kaguya playlists",
            "deleted_count": len(deleted_playlists),
            "deleted_playlists": deleted_playlists
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ==============================
# WebSocket for Real-time Video Stream
# ==============================

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/video-mood")
async def websocket_video_mood(websocket: WebSocket):
    """WebSocket endpoint for real-time mood detection from video stream"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive base64 image data
            data = await websocket.receive_json()
            
            if "image" not in data:
                await manager.send_personal_message(
                    {"error": "No image data provided"}, 
                    websocket
                )
                continue
            
            try:
                # Convert base64 to image
                image_array = base64_to_image(data["image"])
                
                # Detect mood
                mood, confidence = detect_mood_from_image(image_array)
                
                response = {
                    "mood": mood,
                    "confidence": confidence,
                    "timestamp": data.get("timestamp")
                }
                
                # Optionally get playlist for detected mood
                if mood and data.get("include_playlist", False):
                    tracks = search_spotify_by_mood(mood, limit=10)
                    response["recommendations"] = tracks[:5]  # Send top 5
                
                await manager.send_personal_message(response, websocket)
                
            except Exception as e:
                logger.error(f"Error processing video frame: {e}")
                await manager.send_personal_message(
                    {"error": "Failed to process frame"}, 
                    websocket
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected from video mood WebSocket")

# ==============================
# Additional Endpoints
# ==============================

@app.get("/moods")
async def get_available_moods():
    """Get list of available moods"""
    return {
        "moods": list(MOOD_LABELS.values()),
        "mood_descriptions": {
            "Happy": "Upbeat, energetic, positive music",
            "Sad": "Melancholic, emotional, slow music", 
            "Angry": "Aggressive, rock, metal music",
            "Fear": "Calming, ambient, soothing music",
            "Surprise": "Experimental, electronic, dynamic music",
            "Disgust": "Alternative, rock music",
            "Neutral": "Balanced, popular, chill music"
        }
    }

@app.post("/upload-image")
async def upload_image_mood_detection(file: UploadFile = File(...)):
    """Upload image file for mood detection (alternative to base64)"""
    try:
        if mood_model is None or face_cascade is None:
            raise HTTPException(status_code=503, detail="Mood detection models not loaded")
        
        # Read uploaded file
        contents = await file.read()
        
        # Convert to PIL Image
        pil_image = Image.open(io.BytesIO(contents))
        
        # Convert to RGB if needed
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Convert to numpy array
        image_array = np.array(pil_image)
        
        # Detect mood
        mood, confidence = detect_mood_from_image(image_array)
        
        if mood is None:
            raise HTTPException(status_code=400, detail="No face detected in image")
        
        return {
            "mood": mood,
            "confidence": confidence,
            "filename": file.filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload image endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )
