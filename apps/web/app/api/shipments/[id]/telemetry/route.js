import { NextResponse } from "next/server";

export async function GET(request, { params }) {
  const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";
  const { id } = params;

  // Pass through skip and limit query params
  const { searchParams } = new URL(request.url);
  const query = new URLSearchParams();
  if (searchParams.has("skip")) {
    query.set("skip", searchParams.get("skip"));
  }
  if (searchParams.has("limit")) {
    query.set("limit", searchParams.get("limit"));
  }
  const queryString = query.toString() ? `?${query.toString()}` : "";

  try {
    const res = await fetch(`${BACKEND_API_URL}/api/shipments/${id}/telemetry${queryString}`, {
      method: "GET",
      headers: {
        "Accept": "application/json",
      },
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });

    if (!res.ok) {
      const errorText = await res.text();
      let errorDetail;
      try {
        errorDetail = JSON.parse(errorText).detail;
      } catch {
        errorDetail = errorText || `Failed to fetch telemetry for shipment ${id}.`;
      }
      return NextResponse.json({ detail: errorDetail }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { detail: error.message || "Backend service offline." },
      { status: 503 }
    );
  }
}

export async function POST(request, { params }) {
  const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";
  const { id } = params;

  try {
    const body = await request.json();

    const res = await fetch(`${BACKEND_API_URL}/api/shipments/${id}/telemetry`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10000),
    });

    if (!res.ok) {
      const errorText = await res.text();
      let errorDetail;
      try {
        errorDetail = JSON.parse(errorText).detail;
      } catch {
        errorDetail = errorText || `Failed to add telemetry reading for shipment ${id}.`;
      }
      return NextResponse.json({ detail: errorDetail }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json(
      { detail: error.message || "Backend service offline." },
      { status: 503 }
    );
  }
}
