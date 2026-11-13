import sys, asyncio, io
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from starlette.datastructures import Headers
from starlette.formparsers import MultiPartParser

boundary = "----WebKitFormBoundaryTest"
content_type = f"multipart/form-data; boundary={boundary}"
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="test.jpg"\r\n'
    f"Content-Type: image/jpeg\r\n\r\n"
    f"test image content\r\n"
    f"--{boundary}--\r\n"
).encode("utf-8")

async def stream():
    yield body

headers = Headers({"content-type": content_type})
parser = MultiPartParser(headers, stream())

try:
    form = asyncio.run(parser.parse())
    print("Form keys:", list(form.keys()))
    print("File filename:", form["file"].filename)
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
