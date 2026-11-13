import { NextResponse } from "next/server";

const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

export async function GET(request, { params }) {
  const { id } = params;
  try {
    const res = await fetch(`${BACKEND_API_URL}/api/v1/inventory/${id}`, {
      method: "GET",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json(
      { detail: error.message || "Failed to retrieve inventory item" },
      { status: 503 }
    );
  }
}

export async function PUT(request, { params }) {
  const { id } = params;
  try {
    const body = await request.json();
    const headers = { "Content-Type": "application/json" };
    if (request.headers.get("x-role")) headers["X-Role"] = request.headers.get("x-role");
    if (request.headers.get("x-farmer-id")) headers["X-Farmer-ID"] = request.headers.get("x-farmer-id");

    const res = await fetch(`${BACKEND_API_URL}/api/v1/inventory/${id}`, {
      method: "PUT",
      cache: "no-store",
      headers,
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json(
      { detail: error.message || "Failed to update inventory item" },
      { status: 503 }
    );
  }
}

export async function DELETE(request, { params }) {
  const { id } = params;
  try {
    const headers = { "Content-Type": "application/json" };
    if (request.headers.get("x-role")) headers["X-Role"] = request.headers.get("x-role");
    if (request.headers.get("x-farmer-id")) headers["X-Farmer-ID"] = request.headers.get("x-farmer-id");

    const res = await fetch(`${BACKEND_API_URL}/api/v1/inventory/${id}`, {
      method: "DELETE",
      cache: "no-store",
      headers,
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json(
      { detail: error.message || "Failed to delete inventory item" },
      { status: 503 }
    );
  }
}

