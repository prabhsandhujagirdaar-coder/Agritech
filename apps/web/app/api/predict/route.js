import { NextResponse } from "next/server";
import { CLASS_LABELS, GUAVA_CLASS_LABELS } from "../../../lib/constants";

export async function POST(request) {
  try {
    const formData = await request.formData();
    const file = formData.get("file");

    if (!file) {
      return NextResponse.json(
        { detail: "No file uploaded." },
        { status: 400 }
      );
    }

    const backendFormData = new FormData();
    backendFormData.append("file", file);

    const ML_API_URL = process.env.ML_API_URL || "http://127.0.0.1:8000";

    const res = await fetch(`${ML_API_URL}/predict`, {
      method: "POST",
      body: backendFormData,
    });

    if (!res.ok) {
      const errorText = await res.text();
      let errorDetail;
      try {
        errorDetail = JSON.parse(errorText).detail;
      } catch {
        errorDetail = errorText || "Prediction failed on backend.";
      }
      return NextResponse.json(
        { detail: errorDetail },
        { status: res.status }
      );
    }

    const data = await res.json();

    // Preserve exact numeric class index from backend model while ensuring
    // human-readable label and compatibility with class / class_index fields.
    const numericIndex =
      typeof data.class_index === "number"
        ? data.class_index
        : typeof data.class === "number"
        ? data.class
        : null;

    const isGuava = (data.target_crop || "").toLowerCase() === "guava";
    const defaultLabelMap = isGuava ? GUAVA_CLASS_LABELS : CLASS_LABELS;

    const enriched = {
      ...data,
      class: numericIndex !== null ? numericIndex : data.class,
      class_index: numericIndex !== null ? numericIndex : data.class_index,
      label:
        data.label ||
        (numericIndex !== null && defaultLabelMap[numericIndex]) ||
        undefined,
    };

    return NextResponse.json(enriched);
  } catch (error) {
    return NextResponse.json(
      { detail: error.message || "Prediction backend service offline." },
      { status: 503 }
    );
  }
}

