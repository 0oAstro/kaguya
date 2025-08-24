import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ mood: string }> }
) {
  try {
    const { mood } = await params;
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get('limit') || '20';
    
    const response = await fetch(`${BACKEND_URL}/playlist/${mood}?limit=${limit}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`);
    }

    const data = await response.json();
    
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error calling backend:', error);
    return NextResponse.json(
      { error: 'Failed to get playlist' },
      { status: 500 }
    );
  }
}
