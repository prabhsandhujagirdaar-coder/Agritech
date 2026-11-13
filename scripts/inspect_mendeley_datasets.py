import urllib.request
import json

mango_url = "https://data.mendeley.com/public-api/datasets/x6bcr3fkj5"
req = urllib.request.Request(mango_url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
with urllib.request.urlopen(req, timeout=15) as resp:
    mango_data = json.loads(resp.read().decode('utf-8'))

files = mango_data.get("files", [])
found_140 = [f for f in files if "140" in f.get("filename")]
print("Found with 140:", [f.get("filename") for f in found_140])














