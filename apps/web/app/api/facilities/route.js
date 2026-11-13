import { NextResponse } from "next/server";

function getBackendBaseUrl() {
  const rawUrl = process.env.BACKEND_API_URL || process.env.ML_API_URL || "http://127.0.0.1:8000";
  return rawUrl.trim().replace(/\/+$/, "").replace("://localhost:", "://127.0.0.1:");
}

export async function GET(request) {
  const baseUrl = getBackendBaseUrl();
  const { search } = new URL(request.url);

  // Primary route is /api/facilities, fallback is /api/v1/facilities
  const targetUrl = baseUrl.endsWith("/api/v1")
    ? `${baseUrl}/facilities${search}`
    : `${baseUrl}/api/facilities${search}`;

  try {
    let res = await fetch(targetUrl, {
      method: "GET",
      headers: {
        "Accept": "application/json",
      },
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });

    if (res.status === 404 && !baseUrl.endsWith("/api/v1")) {
      const fallbackUrl = `${baseUrl}/api/v1/facilities${search}`;
      res = await fetch(fallbackUrl, {
        method: "GET",
        headers: {
          "Accept": "application/json",
        },
        cache: "no-store",
        signal: AbortSignal.timeout(10000),
      });
    }

    if (!res.ok) {
      const errorText = await res.text();
      let errorDetail;
      try {
        errorDetail = JSON.parse(errorText).detail;
      } catch {
        errorDetail = errorText || "Failed to fetch storage facilities from backend.";
      }
      return NextResponse.json({ detail: errorDetail }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    const isConnRefused = error.message?.includes("fetch failed") || error.code === "ECONNREFUSED" || error.cause?.code === "ECONNREFUSED";
    const detail = isConnRefused
      ? "Backend facility service offline. Ensure the FastAPI backend is running on port 8000 (http://127.0.0.1:8000)."
      : (error.message || "Failed to connect to backend facility service.");
    return NextResponse.json(
      { detail },
      { status: 503 }
    );
  }
}

export async function POST(request) {
  const baseUrl = getBackendBaseUrl();

  const targetUrl = baseUrl.endsWith("/api/v1")
    ? `${baseUrl}/facilities`
    : `${baseUrl}/api/facilities`;

  try {
    const body = await request.json();

    let res = await fetch(targetUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10000),
    });

    if (res.status === 404 && !baseUrl.endsWith("/api/v1")) {
      const fallbackUrl = `${baseUrl}/api/v1/facilities`;
      res = await fetch(fallbackUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(10000),
      });
    }

    if (!res.ok) {
      const errorText = await res.text();
      let errorDetail;
      try {
        errorDetail = JSON.parse(errorText).detail;
      } catch {
        errorDetail = errorText || "Failed to register storage facility on backend.";
      }
      return NextResponse.json({ detail: errorDetail }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    const isConnRefused = error.message?.includes("fetch failed") || error.code === "ECONNREFUSED" || error.cause?.code === "ECONNREFUSED";
    const detail = isConnRefused
      ? "Backend facility service offline. Ensure the FastAPI backend is running on port 8000 (http://127.0.0.1:8000)."
      : (error.message || "Failed to register storage facility on backend.");
    return NextResponse.json(
      { detail },
      { status: 503 }
    );
  }
}
