import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// Create mood-specific playlist URLs
const createMoodPlaylistUrl = (mood: string, tracks: any[]) => {
  const trackNames = tracks.slice(0, 5).map(track => `${track.name} ${track.artist}`).join(' ');
  const searchQuery = encodeURIComponent(`${mood} mood ${trackNames}`);
  return `https://open.spotify.com/search/${searchQuery}`;
};

// Mock data for development
const mockMoodData = {
  mood: 'happy',
  confidence: 0.85,
  playlist_url: '',  // Will be dynamically generated
  recommendations: [
    { name: 'Good as Hell', artist: 'Lizzo', preview_url: 'https://p.scdn.co/mp3-preview/...' },
    { name: 'Happy', artist: 'Pharrell Williams', preview_url: 'https://p.scdn.co/mp3-preview/...' },
    { name: 'Can\'t Stop the Feeling!', artist: 'Justin Timberlake', preview_url: 'https://p.scdn.co/mp3-preview/...' },
    { name: 'Uptown Funk', artist: 'Mark Ronson ft. Bruno Mars', preview_url: 'https://p.scdn.co/mp3-preview/...' },
    { name: 'September', artist: 'Earth, Wind & Fire', preview_url: 'https://p.scdn.co/mp3-preview/...' },
    { name: 'Sunshine', artist: 'Matisyahu', preview_url: 'https://p.scdn.co/mp3-preview/...' },
    { name: 'Walking on Sunshine', artist: 'Katrina and the Waves', preview_url: 'https://p.scdn.co/mp3-preview/...' },
    { name: 'Good Vibes', artist: 'Chris Janson', preview_url: 'https://p.scdn.co/mp3-preview/...' },
    { name: 'Three Little Birds', artist: 'Bob Marley', preview_url: 'https://p.scdn.co/mp3-preview/...' },
    { name: 'I Got You (I Feel Good)', artist: 'James Brown', preview_url: 'https://p.scdn.co/mp3-preview/...' },
  ],
};

const moods = ['happy', 'sad', 'energetic', 'calm', 'melancholic', 'excited', 'relaxed'];

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // Try backend first - it will handle Spotify auth internally
    try {
      const response = await fetch(`${BACKEND_URL}/mood-and-playlist`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(30000), // 30 second timeout
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Using real backend data:', data.mood);
        return NextResponse.json(data);
      } else {
        const errorText = await response.text();
        console.log(`Backend error ${response.status}: ${errorText}`);
      }
    } catch (backendError) {
      console.log('Backend not available:', backendError);
    }
    
    // Backend not available or failed, return mock data without playlist URL
    const randomMood = moods[Math.floor(Math.random() * moods.length)];
    const mockResponse = {
      ...mockMoodData,
      mood: randomMood,
      confidence: 0.7 + Math.random() * 0.3, // Random confidence between 0.7-1.0
      playlist_url: null, // No playlist URL for mock data - only show real playlists
    };
    
    // Add a delay to simulate processing
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    return NextResponse.json(mockResponse);
    
  } catch (error) {
    console.error('Error in mood detection API:', error);
    return NextResponse.json(
      { 
        error: 'Failed to process mood detection',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
