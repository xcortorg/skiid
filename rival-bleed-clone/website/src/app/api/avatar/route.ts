import { NextResponse } from 'next/server';

export async function GET(req: Request) {
    try {
        const response = await fetch('http://23.160.168.147:1274/avatar.png');

        if (!response.ok) {
            return NextResponse.json({ error: 'Failed to fetch data' }, { status: response.status });
        }

        return new Response(response.body, {
            headers: { 'Content-Type': 'image/png' },
            status: response.status,
        });
    } catch (error) {
        return NextResponse.json({ error: 'Failed to fetch data' }, { status: 500 });
    }
}
