import { NextResponse } from "next/server";

export async function GET(request) {
  const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";
  const { searchParams } = new URL(request.url);
  const buyerName = searchParams.get("buyer_name");

  try {
    const url = new URL(`${BACKEND_API_URL}/api/v1/orders`);
    if (buyerName) {
      url.searchParams.set("buyer_name", buyerName);
    }

    const res = await fetch(url.toString(), {
      method: "GET",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
    });

    if (!res.ok) {
      const errorText = await res.text();
      return NextResponse.json({ detail: errorText || "Failed to fetch orders" }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { detail: error.message || "Failed to connect to backend orders service" },
      { status: 503 }
    );
  }
}

export async function POST(request) {
  const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

  try {
    const body = await request.json();

    const res = await fetch(`${BACKEND_API_URL}/api/v1/orders`, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    if (!res.ok) {
      return NextResponse.json({ detail: data.detail || "Order placement failed" }, { status: res.status });
    }

    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { detail: error.message || "Failed to submit demo order to backend" },
      { status: 503 }
    );
  }
}
