import { NextResponse } from "next/server";

function getBackendBaseUrl() {
  const rawUrl = process.env.BACKEND_API_URL || process.env.ML_API_URL || "http://127.0.0.1:8000";
  return rawUrl.trim().replace(/\/+$/, "").replace("://localhost:", "://127.0.0.1:");
}

export async function GET(request, { params }) {
  const baseUrl = getBackendBaseUrl();
  const { id } = params;

  const targetUrl = baseUrl.endsWith("/api/v1")
    ? `${baseUrl}/facilities/${encodeURIComponent(id)}`
    : `${baseUrl}/api/facilities/${encodeURIComponent(id)}`;

  try {
    let res = await fetch(targetUrl, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });

    if (res.status === 404 && !baseUrl.endsWith("/api/v1")) {
      const fallbackUrl = `${baseUrl}/api/v1/facilities/${encodeURIComponent(id)}`;
      res = await fetch(fallbackUrl, {
        method: "GET",
        headers: { Accept: "application/json" },
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
        errorDetail = errorText || `Failed to fetch facility ${id}.`;
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
