import { NextResponse } from "next/server";

const CONNECTED_NODE = "EU-NL-LOAD1";

export async function GET() {
  try {
    const nodeInfo = CONNECTED_NODE;

    return NextResponse.json({
      status: "healthy",
      timestamp: new Date().toISOString(),
      node: nodeInfo,
      uptime: process.uptime(),
    });
  } catch (error) {
    return NextResponse.json({
      status: "healthy",
      timestamp: new Date().toISOString(),
      error: "Error retrieving node information",
    });
  }
}
