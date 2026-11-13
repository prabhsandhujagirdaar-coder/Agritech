import { NextResponse } from "next/server";

export async function GET() {
  const ML_API_URL = process.env.ML_API_URL || "http://127.0.0.1:8000";
  const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

  // Check ML API (Person A)
  const checkMlHealth = async () => {
    const startTime = Date.now();
    try {
      const res = await fetch(`${ML_API_URL}/health`, {
        method: "GET",
        cache: "no-store",
        signal: AbortSignal.timeout(3000),
      });

      if (!res.ok) {
        throw new Error(`ML API returned status: ${res.status}`);
      }

      const data = await res.json();
      return {
        status: data.status || "healthy",
        api_status: data.api_status || "online",
        model: data.model || "N/A",
        model_version: data.model_version || "2.0.0",
        device: data.device || "N/A",
        model_available: data.model_available ?? true,
        model_status: data.model_status || (data.model_available ? "ready" : "unavailable"),
        target_crop: data.target_crop || "guava",
        message: data.message || "",
        database: data.database || { enabled: false, connected: null, message: "File-based persistence active." },
        latencyMs: Date.now() - startTime,
      };
    } catch (error) {
      return {
        status: "offline",
        api_status: "offline",
        model: "N/A",
        model_version: null,
        device: "N/A",
        model_available: false,
        model_status: "unavailable",
        target_crop: "guava",
        message: "Failed to connect to FastAPI backend",
        database: { enabled: false, connected: false, message: "FastAPI backend unreachable" },
        latencyMs: null,
        error: error.message || "Failed to reach ML API",
      };
    }
  };

  // Check Backend API (Person B)
  const checkBackendHealth = async () => {
    const startTime = Date.now();
    try {
      const res = await fetch(`${BACKEND_API_URL}/health`, {
        method: "GET",
        cache: "no-store",
        signal: AbortSignal.timeout(3000),
      });

      if (!res.ok) {
        return {
          status: "offline",
          api_status: "offline",
          latencyMs: null,
          error: `Backend returned status ${res.status}`,
        };
      }

      const data = await res.json();
      return {
        status: data.status || "healthy",
        api_status: data.api_status || "online",
        database: data.database || { enabled: false, connected: null, message: "File-based persistence active." },
        latencyMs: Date.now() - startTime,
      };
    } catch (err) {
      return {
        status: "offline",
        api_status: "offline",
        database: { enabled: false, connected: false, message: "FastAPI backend unreachable" },
        latencyMs: null,
        error: err.message || "FastAPI connection failed",
      };
    }
  };

  const [mlHealth, backendHealth] = await Promise.all([
    checkMlHealth(),
    checkBackendHealth(),
  ]);

  const responseBody = {
    ...mlHealth,
    backend: backendHealth,
    database: backendHealth.database || mlHealth.database,
  };

  const statusCode = backendHealth.status !== "offline" ? 200 : 503;
  return NextResponse.json(responseBody, { status: statusCode });
}
