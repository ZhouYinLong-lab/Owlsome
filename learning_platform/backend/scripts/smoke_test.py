from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
failed = 0
passed = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global failed, passed
    if condition:
        passed += 1
        print(f"  ok  {label}")
    else:
        failed += 1
        print(f"  FAIL {label}" + (f"  -- {detail}" if detail else ""))


print("Owlsome Learning v0.1 Smoke Test\n")

# 1. GET /api/health
resp = client.get("/api/health")
check("GET /api/health", resp.status_code == 200 and resp.json().get("ok") is True,
      f"status={resp.status_code} body={resp.text}")

# 2. GET /api/stats
resp = client.get("/api/stats")
ok = resp.status_code == 200 and isinstance(resp.json(), dict)
check("GET /api/stats", ok, f"status={resp.status_code} body={resp.text}")

# 3. POST /api/import/sample
resp = client.post("/api/import/sample")
body = resp.json()
ok = resp.status_code == 200 and body.get("ok") is True
check("POST /api/import/sample", ok, f"status={resp.status_code} body={resp.text}")

# 4. GET /api/knowledge-points
resp = client.get("/api/knowledge-points")
body = resp.json()
ok = resp.status_code == 200 and isinstance(body, list) and len(body) > 0
check("GET /api/knowledge-points",
      ok,
      f"status={resp.status_code} count={len(body) if isinstance(body, list) else 'n/a'}")

# 5. POST /api/personal-spaces/from-sample
resp = client.post("/api/personal-spaces/from-sample")
body = resp.json()
ok = resp.status_code == 200 and body.get("ok") is True
check("POST /api/personal-spaces/from-sample",
      ok,
      f"status={resp.status_code} body={resp.text}")

# 6. GET /api/personal-spaces
resp = client.get("/api/personal-spaces")
body = resp.json()
ok = resp.status_code == 200 and isinstance(body, list) and len(body) > 0
check("GET /api/personal-spaces",
      ok,
      f"status={resp.status_code} count={len(body) if isinstance(body, list) else 'n/a'}")

# Summary
print(f"\n{passed} passed, {failed} failed")

if failed > 0:
    print("SMOKE TEST FAILED")
    sys.exit(1)
else:
    print("SMOKE TEST PASSED")
    sys.exit(0)
