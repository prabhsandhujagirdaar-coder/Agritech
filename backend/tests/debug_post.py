import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app
from tests.test_client_compat import TestClient

client = TestClient(app)
with client:
    bogus = ("report.pdf", b"%PDF-1.4 fake pdf data", "application/pdf")
    r5 = client.post("/predict", files={"file": bogus})
    print("test_05 status:", r5.status_code, r5.text)
