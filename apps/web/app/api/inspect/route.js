import { NextResponse } from "next/server";

export async function POST(request) {
  try {
    const { searchParams } = new URL(request.url);
    const formData = await request.formData();
    const file = formData.get("file");

    if (!file) {
      return NextResponse.json(
        { detail: "No produce image file uploaded." },
        { status: 400 }
      );
    }

    const mode = searchParams.get("mode") || formData.get("mode") || "manual";
    const fruit = searchParams.get("fruit") || formData.get("fruit") || "guava";

    const backendFormData = new FormData();
    backendFormData.append("file", file);

    const ML_API_URL = process.env.ML_API_URL || "http://127.0.0.1:8000";

    const res = await fetch(
      `${ML_API_URL}/api/v1/cnn/inspect?mode=${encodeURIComponent(mode)}&fruit=${encodeURIComponent(fruit)}`,
      {
        method: "POST",
        body: backendFormData,
      }
    );

    if (!res.ok) {
      const errorText = await res.text();
      let errorDetail;
      try {
        errorDetail = JSON.parse(errorText).detail;
      } catch {
        errorDetail = errorText || "Multi-fruit inspection failed on backend.";
      }
      return NextResponse.json(
        { detail: errorDetail },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { detail: error.message || "Inspection backend service offline or unreachable." },
      { status: 503 }
    );
  }
}

