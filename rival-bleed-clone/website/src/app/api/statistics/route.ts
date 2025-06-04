import { NextResponse } from 'next/server';

export async function GET(req: Request) {
    try {
        const response = await fetch('http://127.0.0.1:1274/statistics');
        
        if (!response.ok) {
            return NextResponse.json({ error: 'Failed to fetch data' }, { status: response.status });
        }
    
        const data = await response.json();
        return NextResponse.json(data)
    } catch (error) {
        return NextResponse.json({ error: 'Failed to fetch data' }, { status: 500 });
    }
};