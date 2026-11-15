import fs from "fs";
import path from "path";

const FRONTEND_URL = process.env.FRONTEND_URL || "http://localhost:3000";
const BACKEND_URL = "http://127.0.0.1:8000";

const results = [];

function recordResult(testName, passed, details) {
  results.push({ testName, passed, details });
  console.log(`[${passed ? "PASS" : "FAIL"}] ${testName}`);
  if (details) console.log(`       Details: ${typeof details === "string" ? details : JSON.stringify(details)}`);
}

async function runTests() {
  console.log("=================================================================");
  console.log("  AgriChain AI — Produce Specimen Inspection Test Suite");
  console.log("=================================================================\n");

  // Test 1: Backend Health
  try {
    const res = await fetch(`${BACKEND_URL}/health`);
    const data = await res.json();
    const passed = res.ok && data.status === "healthy" && data.model_available === true;
    recordResult("1. FastAPI Backend Health Check (/health)", passed, {
      status: res.status,
      target_crop: data.target_crop,
      model_available: data.model_available,
      device: data.device,
    });
  } catch (err) {
    recordResult("1. FastAPI Backend Health Check (/health)", false, err.message);
  }

  // Load test images
  const guavaPath = "ml/data/guava_classification/Local Sindhi/Green/1.jpg";
  const guavaBuffer = fs.readFileSync(guavaPath);

  // Test 2: Auto Mode Identification & Inspection (Guava specimen)
  try {
    const blob = new Blob([guavaBuffer], { type: "image/jpeg" });
    const formData = new FormData();
    formData.append("file", blob, "test_guava.jpg");
    formData.append("mode", "auto");
    formData.append("fruit", "guava");

    const res = await fetch(`${FRONTEND_URL}/api/inspect?mode=auto&fruit=guava`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    const passed =
      res.ok &&
      data.mode === "auto" &&
      data.identified_fruit === "guava" &&
      data.classification &&
      data.classification.predicted_class !== undefined &&
      res.headers.has("x-request-id");

    recordResult("2. Auto Mode: Identify Species & Inspect Produce (Guava)", passed, {
      status: res.status,
      identified_fruit: data.identified_fruit,
      maturity_verdict: data.classification?.predicted_class,
      confidence: data.classification?.confidence,
      requestId: res.headers.get("x-request-id"),
    });
  } catch (err) {
    recordResult("2. Auto Mode: Identify Species & Inspect Produce (Guava)", false, err.message);
  }

  // Test 3: Manual Mode Guava Inspection
  try {
    const blob = new Blob([guavaBuffer], { type: "image/jpeg" });
    const formData = new FormData();
    formData.append("file", blob, "test_guava.jpg");
    formData.append("mode", "manual");
    formData.append("fruit", "guava");

    const res = await fetch(`${FRONTEND_URL}/api/inspect?mode=manual&fruit=guava`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    const passed =
      res.ok &&
      data.mode === "manual" &&
      data.target_fruit === "guava" &&
      data.classification &&
      ["Green", "Mature Green", "Ripe"].includes(data.classification.predicted_class);

    recordResult("3. Manual Mode: Guava Harvest Maturity (ResNet18)", passed, {
      status: res.status,
      target_fruit: data.target_fruit,
      predicted_class: data.classification?.predicted_class,
      confidence: data.classification?.confidence,
    });
  } catch (err) {
    recordResult("3. Manual Mode: Guava Harvest Maturity (ResNet18)", false, err.message);
  }

  // Test 4: Manual Mode Banana Inspection
  try {
    const blob = new Blob([guavaBuffer], { type: "image/jpeg" }); // Using image payload for routing test
    const formData = new FormData();
    formData.append("file", blob, "test_banana.jpg");
    formData.append("mode", "manual");
    formData.append("fruit", "banana");

    const res = await fetch(`${FRONTEND_URL}/api/inspect?mode=manual&fruit=banana`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    const passed =
      res.ok &&
      data.mode === "manual" &&
      data.target_fruit === "banana" &&
      data.classification &&
      data.classification.model_name === "resnet18";

    recordResult("4. Manual Mode: Banana Ripeness Classifier (ResNet18)", passed, {
      status: res.status,
      target_fruit: data.target_fruit,
      predicted_class: data.classification?.predicted_class,
      model: data.classification?.model_name,
    });
  } catch (err) {
    recordResult("4. Manual Mode: Banana Ripeness Classifier (ResNet18)", false, err.message);
  }

  // Test 5: Manual Mode Apple YOLOv8n Detection
  try {
    const blob = new Blob([guavaBuffer], { type: "image/jpeg" });
    const formData = new FormData();
    formData.append("file", blob, "test_apple.jpg");
    formData.append("mode", "manual");
    formData.append("fruit", "apple");

    const res = await fetch(`${FRONTEND_URL}/api/inspect?mode=manual&fruit=apple`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    const passed =
      res.ok &&
      data.mode === "manual" &&
      data.target_fruit === "apple" &&
      data.task_type === "object_detection" &&
      data.detection &&
      data.detection.license &&
      data.detection.license.includes("CC BY-NC 4.0");

    recordResult("5. Manual Mode: Apple YOLOv8n Object Detection (CC BY-NC 4.0)", passed, {
      status: res.status,
      task_type: data.task_type,
      model: data.detection?.model_name,
      license: data.detection?.license,
      box_count: data.detection?.apple_count,
    });
  } catch (err) {
    recordResult("5. Manual Mode: Apple YOLOv8n Object Detection (CC BY-NC 4.0)", false, err.message);
  }

  // Test 6: Mango Gated Policy (Zero Synthetic Predictions)
  try {
    const blob = new Blob([guavaBuffer], { type: "image/jpeg" });
    const formData = new FormData();
    formData.append("file", blob, "test_mango.jpg");
    formData.append("mode", "manual");
    formData.append("fruit", "mango");

    const res = await fetch(`${FRONTEND_URL}/api/inspect?mode=manual&fruit=mango`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    const passed =
      res.ok &&
      data.target_fruit === "mango" &&
      data.status === "unavailable" &&
      data.task_type === "unavailable" &&
      data.classification === null &&
      data.unavailable_reason.includes("unavailable");

    recordResult("6. Gated Mango Inspection: Honest Deficit Disclosure", passed, {
      status: res.status,
      target_fruit: data.target_fruit,
      status_field: data.status,
      unavailable_reason: data.unavailable_reason.substring(0, 60) + "...",
    });
  } catch (err) {
    recordResult("6. Gated Mango Inspection: Honest Deficit Disclosure", false, err.message);
  }

  // Test 7: Invalid Media Type Rejection
  try {
    const textBlob = new Blob(["this is plain text not an image"], { type: "text/plain" });
    const formData = new FormData();
    formData.append("file", textBlob, "notes.txt");
    formData.append("mode", "manual");
    formData.append("fruit", "guava");

    const res = await fetch(`${FRONTEND_URL}/api/inspect?mode=manual&fruit=guava`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    const passed = res.status === 415 || res.status === 400;

    recordResult("7. Security & Validation: Reject Non-Image File Format", passed, {
      status: res.status,
      expected: "415 Unsupported Media Type or 400 Bad Request",
      detail: data.detail,
      error_category: data.error_category,
    });
  } catch (err) {
    recordResult("7. Security & Validation: Reject Non-Image File Format", false, err.message);
  }

  // Test 8: Empty / Missing File Payload Rejection
  try {
    const formData = new FormData();
    formData.append("mode", "manual");
    formData.append("fruit", "guava");

    const res = await fetch(`${FRONTEND_URL}/api/inspect?mode=manual&fruit=guava`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    const passed = res.status === 400 && data.error_category === "validation";

    recordResult("8. Validation: Reject Empty Specimen Upload", passed, {
      status: res.status,
      error_category: data.error_category,
      detail: data.detail,
    });
  } catch (err) {
    recordResult("8. Validation: Reject Empty Specimen Upload", false, err.message);
  }

  console.log("\n=================================================================");
  const allPassed = results.every((r) => r.passed);
  console.log(`  VERDICT: ${allPassed ? "ALL 8 INSPECTION FLOW TESTS PASSED 100%" : "SOME TESTS FAILED"}`);
  console.log("=================================================================\n");

  if (!allPassed) {
    process.exit(1);
  }
}

runTests();
