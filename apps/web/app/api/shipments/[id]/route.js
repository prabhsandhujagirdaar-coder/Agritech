import { NextResponse } from "next/server";

export async function GET(request, { params }) {
  const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";
  const { id } = params;

  try {
    const res = await fetch(`${BACKEND_API_URL}/api/shipments/${id}`, {
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
        errorDetail = errorText || `Failed to fetch shipment ${id} from backend.`;
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
