import { NextResponse } from "next/server";

function getBackendBaseUrl() {
  const rawUrl = process.env.BACKEND_API_URL || process.env.ML_API_URL || "http://127.0.0.1:8000";
  return rawUrl.trim().replace(/\/+$/, "").replace("://localhost:", "://127.0.0.1:");
}

function resolveTargetUrl(params, search) {
  const baseUrl = getBackendBaseUrl();
  const subpath = Array.isArray(params?.path) ? params.path.join("/") : "";
  const prefix = baseUrl.endsWith("/api/v1") ? baseUrl : `${baseUrl}/api/v1`;
  return `${prefix}/simulations/${subpath}${search || ""}`;
}

export async function GET(request, { params }) {
  const { search } = new URL(request.url);
  const targetUrl = resolveTargetUrl(params, search);

  try {
    const res = await fetch(targetUrl, {
      method: "GET",
      headers: { "Accept": "application/json" },
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json(
      { detail: error.message || "Failed to reach backend simulation endpoint." },
      { status: 503 }
    );
  }
}

export async function POST(request, { params }) {
  const { search } = new URL(request.url);
  const targetUrl = resolveTargetUrl(params, search);

  try {
    let body = {};
    try {
      body = await request.json();
    } catch {
      body = {};
    }

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
      { detail: error.message || "Failed to reach backend simulation endpoint." },
      { status: 503 }
    );
  }
}

export async function PATCH(request, { params }) {
  const { search } = new URL(request.url);
  const targetUrl = resolveTargetUrl(params, search);

  try {
    const body = await request.json();
    const res = await fetch(targetUrl, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json(
      { detail: error.message || "Failed to update simulation controls." },
      { status: 503 }
    );
  }
}

