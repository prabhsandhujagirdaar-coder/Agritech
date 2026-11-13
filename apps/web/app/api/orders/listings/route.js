import { NextResponse } from "next/server";

export async function GET() {
  const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

  try {
    const res = await fetch(`${BACKEND_API_URL}/api/v1/orders/listings`, {
      method: "GET",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
    });

    if (!res.ok) {
      const errorText = await res.text();
      return NextResponse.json({ detail: errorText || "Failed to fetch listings" }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { detail: error.message || "Failed to connect to marketplace listings service" },
      { status: 503 }
    );
  }
}
