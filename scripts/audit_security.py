import os
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
EXCLUDE = {".git", ".venv", "node_modules", ".next", "build", ".dart_tool", "guava_classification"}

patterns = [
    ("GitHub Personal Access Token", re.compile(r"ghp_[A-Za-z0-9_]{30,}")),
    ("GitHub Fine-Grained Token", re.compile(r"github_pat_[A-Za-z0-9_]{30,}")),
    ("AWS Access Key ID", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Private RSA/SSH Key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Generic Secret Assignment", re.compile(r"""(?:api_key|secret_key|private_key|auth_token)\s*=\s*['\"][A-Za-z0-9_\-]{20,}['\"]""", re.IGNORECASE)),
]

findings = []
scanned_count = 0

for root_dir, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in EXCLUDE]
    for f in files:
        if f.endswith((".py", ".js", ".mjs", ".json", ".yaml", ".yml", ".env", ".ps1", ".bat", ".sh")):
            fp = Path(root_dir) / f
            scanned_count += 1
            try:
                content = fp.read_text(encoding="utf-8", errors="ignore")
                for name, pat in patterns:
                    for match in pat.finditer(content):
                        # Mask matching string
                        val = match.group(0)
                        masked = val[:6] + "..." + val[-4:] if len(val) > 10 else "***"
                        rel = fp.relative_to(root)
                        findings.append((str(rel), name, masked))
            except Exception:
                pass

print(f"Scanned {scanned_count} configuration and source files.")
if findings:
    print(f"WARNING: {len(findings)} potential secret pattern(s) identified:")
    for file_path, name, masked in findings:
        print(f"  - {file_path} [{name}]: {masked}")
else:
    print("SUCCESS: Zero exposed credentials, tokens, or private keys detected.")
