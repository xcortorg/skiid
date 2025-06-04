import { NextResponse } from 'next/server';

const API_KEY = '';

export async function GET(
  request: Request,
  { params }: { params: { userId: string } }
) {
  try {
    const response = await fetch(`https://api.evict.bot/avatars/${params.userId}?t=${Date.now()}`, {
      headers: {
        'Authorization': API_KEY
      }
    });

    if (!response.ok) {
      throw new Error('Failed to fetch avatars');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: 'Failed to load avatar history' }, { status: 500 });
  }
} 