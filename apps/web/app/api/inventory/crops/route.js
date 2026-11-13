import { NextResponse } from "next/server";

const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_API_URL}/api/v1/inventory/crops`, {
      method: "GET",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json(
      { detail: error.message || "Failed to fetch crop catalogue" },
      { status: 503 }
    );
  }
}

