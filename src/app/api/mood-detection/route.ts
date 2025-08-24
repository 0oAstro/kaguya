import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// Mock mood data for development
const mockMoods = ['happy', 'sad', 'energetic', 'calm', 'melancholic', 'excited', 'relaxed'];

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // Try backend first - mood detection only
    try {
      const response = await fetch(`${BACKEND_URL}/detect-mood`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(15000), // 15 second timeout
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Using real backend mood detection:', data.mood);
        return NextResponse.json(data);
      } else {
        const errorText = await response.text();
        console.log(`Backend error ${response.status}: ${errorText}`);
      }
    } catch (backendError) {
      console.log('Backend not available:', backendError);
    }
    
    // Backend not available, return mock mood data
    const randomMood = mockMoods[Math.floor(Math.random() * mockMoods.length)];
    const mockResponse = {
      mood: randomMood,
      confidence: 0.7 + Math.random() * 0.3, // Random confidence between 0.7-1.0
    };
    
    // Add a delay to simulate processing
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    return NextResponse.json(mockResponse);
    
  } catch (error) {
    console.error('Error in mood detection API:', error);
    return NextResponse.json(
      { 
        error: 'Failed to detect mood',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
