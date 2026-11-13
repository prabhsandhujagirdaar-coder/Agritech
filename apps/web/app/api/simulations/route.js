import { NextResponse } from "next/server";

function getBackendBaseUrl() {
  const rawUrl = process.env.BACKEND_API_URL || process.env.ML_API_URL || "http://127.0.0.1:8000";
  return rawUrl.trim().replace(/\/+$/, "").replace("://localhost:", "://127.0.0.1:");
}

export async function GET(request) {
  const baseUrl = getBackendBaseUrl();
  const { search } = new URL(request.url);

  const targetUrl = baseUrl.endsWith("/api/v1")
    ? `${baseUrl}/simulations${search}`
    : `${baseUrl}/api/v1/simulations${search}`;

  try {
    const res = await fetch(targetUrl, {
      method: "GET",
      headers: { "Accept": "application/json" },
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });

    if (!res.ok) {
      const errorText = await res.text();
      return NextResponse.json({ detail: errorText || "Backend error" }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { detail: "Backend simulation service offline. Ensure backend is running at http://127.0.0.1:8000." },
      { status: 503 }
    );
  }
}

export async function POST(request) {
  const baseUrl = getBackendBaseUrl();
  const targetUrl = baseUrl.endsWith("/api/v1")
    ? `${baseUrl}/simulations`
    : `${baseUrl}/api/v1/simulations`;

  try {
    const body = await request.json();
    const res = await fetch(targetUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json(
      { detail: error.message || "Failed to contact simulation backend." },
      { status: 503 }
    );
  }
}

