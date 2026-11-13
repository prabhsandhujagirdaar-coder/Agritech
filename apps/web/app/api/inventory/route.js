import { NextResponse } from "next/server";

const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const farmerId = searchParams.get("farmer_id");
  const cropType = searchParams.get("crop_type");
  const statusParam = searchParams.get("status");

  try {
    const url = new URL(`${BACKEND_API_URL}/api/v1/inventory`);
    if (farmerId) url.searchParams.set("farmer_id", farmerId);
    if (cropType) url.searchParams.set("crop_type", cropType);
    if (statusParam) url.searchParams.set("status", statusParam);

    const headers = {
      "Content-Type": "application/json",
    };
    if (request.headers.get("x-role")) headers["X-Role"] = request.headers.get("x-role");
    if (request.headers.get("x-farmer-id")) headers["X-Farmer-ID"] = request.headers.get("x-farmer-id");

    const res = await fetch(url.toString(), {
      method: "GET",
      cache: "no-store",
      headers,
    });

    if (!res.ok) {
      const errorText = await res.text();
      return NextResponse.json({ detail: errorText || "Failed to fetch inventory" }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { detail: error.message || "Failed to connect to backend inventory service" },
      { status: 503 }
    );
  }
}

export async function POST(request) {
  try {
    const body = await request.json();
    const headers = {
      "Content-Type": "application/json",
    };
    if (request.headers.get("x-role")) headers["X-Role"] = request.headers.get("x-role");
    if (request.headers.get("x-farmer-id")) headers["X-Farmer-ID"] = request.headers.get("x-farmer-id");

    const res = await fetch(`${BACKEND_API_URL}/api/v1/inventory`, {
      method: "POST",
      cache: "no-store",
      headers,
      body: JSON.stringify(body),
    });

    const data = await res.json();
    if (!res.ok) {
      return NextResponse.json({ detail: data.detail || "Creating inventory item failed" }, { status: res.status });
    }

    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { detail: error.message || "Failed to connect to backend inventory service" },
      { status: 503 }
    );
  }
}

