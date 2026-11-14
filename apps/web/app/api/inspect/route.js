import { NextResponse } from "next/server";

/**
 * Resolves candidate backend URLs with IPv4/IPv6 fallback for local dev.
 */
function getCandidateBaseUrls() {
  const envUrl = process.env.ML_API_URL || process.env.BACKEND_API_URL;
  const urls = [];

  if (envUrl) {
    const clean = envUrl.trim().replace(/\/+$/, "");
    urls.push(clean);
    if (clean.includes("localhost")) {
      urls.push(clean.replace("localhost", "127.0.0.1"));
    } else if (clean.includes("127.0.0.1")) {
      urls.push(clean.replace("127.0.0.1", "localhost"));
    }
  } else {
    urls.push("http://127.0.0.1:8000");
    urls.push("http://localhost:8000");
  }

  return [...new Set(urls)];
}

export async function POST(request) {
  const requestId =
    request.headers.get("x-request-id") ||
    `insp_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;

  try {
    const { searchParams } = new URL(request.url);
    const formData = await request.formData();
    const file = formData.get("file");

    if (!file) {
      return NextResponse.json(
        {
          detail: "No produce image file uploaded. Please upload a JPEG, PNG, or WEBP image.",
          error_category: "validation",
          request_id: requestId,
        },
        { status: 400, headers: { "X-Request-ID": requestId } }
      );
    }

    const mode = searchParams.get("mode") || formData.get("mode") || "manual";
    const fruit = searchParams.get("fruit") || formData.get("fruit") || "guava";

    // Read byte buffer into memory to prevent Node.js stream duplex/pipe exhaustion
    const arrayBuffer = await file.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    const fileName = file.name || "produce_specimen.jpg";
    const fileType = file.type || "image/jpeg";
    const blob = new Blob([buffer], { type: fileType });

    const candidateUrls = getCandidateBaseUrls();
    let lastError = null;
    let res = null;
    let attemptedUrl = "";

    for (const baseUrl of candidateUrls) {
      attemptedUrl = `${baseUrl}/api/v1/cnn/inspect?mode=${encodeURIComponent(mode)}&fruit=${encodeURIComponent(fruit)}`;
      try {
        const backendFormData = new FormData();
        backendFormData.append("file", blob, fileName);

        res = await fetch(attemptedUrl, {
          method: "POST",
          body: backendFormData,
          headers: {
            "X-Request-ID": requestId,
          },
          signal: AbortSignal.timeout(30000), // 30s timeout
        });
        // Request reached backend successfully
        break;
      } catch (fetchErr) {
        lastError = fetchErr;
        const code = fetchErr?.cause?.code || "";
        // Continue to fallback URL if connection refused or address resolution failed
        if (code === "ECONNREFUSED" || code === "ENOTFOUND" || fetchErr.message === "fetch failed") {
          continue;
        }
        break;
      }
    }

    if (!res) {
      // All candidate URLs failed to establish connection
      const errCode = lastError?.cause?.code || "CONNECTION_FAILED";
      const isConnRefused = errCode === "ECONNREFUSED" || lastError?.message === "fetch failed";

      const diagnosticMsg = isConnRefused
        ? `FastAPI inspection backend is offline or unreachable on port 8000 (${errCode}). Please verify that the backend server is running.`
        : `Network request to inspection backend failed: ${lastError?.message || "Unknown network error"} (${errCode}).`;

      return NextResponse.json(
        {
          detail: diagnosticMsg,
          error_category: "network",
          error_code: errCode,
          request_id: requestId,
          hint: "Ensure the FastAPI backend server is active on port 8000 by running '.\\start.bat' in PowerShell.",
          attempted_url: attemptedUrl,
        },
        { status: 503, headers: { "X-Request-ID": requestId } }
      );
    }

    if (!res.ok) {
      const errorText = await res.text();
      let errorDetail;
      let errorCategory = "backend_error";
      try {
        const parsed = JSON.parse(errorText);
        errorDetail = parsed.detail || errorText;
        if (res.status === 400 || res.status === 415 || res.status === 422) {
          errorCategory = "validation";
        } else if (res.status === 503) {
          errorCategory = "model_unavailable";
        }
      } catch {
        errorDetail = errorText || `Multi-fruit inspection failed with HTTP ${res.status}.`;
      }

      return NextResponse.json(
        {
          detail: errorDetail,
          error_category: errorCategory,
          status_code: res.status,
          request_id: requestId,
        },
        { status: res.status, headers: { "X-Request-ID": requestId } }
      );
    }

    const data = await res.json();
    return NextResponse.json(data, {
      headers: { "X-Request-ID": requestId },
    });
  } catch (error) {
    const errCode = error?.cause?.code || "UNHANDLED_EXCEPTION";
    return NextResponse.json(
      {
        detail: error.message || "Unexpected failure while processing produce inspection proxy request.",
        error_category: "proxy_exception",
        error_code: errCode,
        request_id: requestId,
      },
      { status: 500, headers: { "X-Request-ID": requestId } }
    );
  }
}
