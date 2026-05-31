"""Verify the optional ADMIN_TOKEN guard on admin write endpoints.

- When ADMIN_TOKEN is empty: all endpoints remain open (local demo mode).
- When ADMIN_TOKEN is set: admin write endpoints require X-Admin-Token.
- Learner endpoints are never affected.

Run from the backend directory::

    python scripts/admin_guard_test.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient

# Force-reload the admin_auth module so we can set ADMIN_TOKEN before import.
# Simpler approach: import, test with empty token, then monkeypatch for guarded mode.

from app.admin_auth import ADMIN_TOKEN as _ORIG_TOKEN
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


# ── Un-guarded mode (default for local demo) ───────────────────────
print("Admin Guard Test — un-guarded mode (ADMIN_TOKEN=\"\")\n")

# Admin write endpoints should work without token
resp = client.post("/api/import/sample")
check("POST /api/import/sample (no token, un-guarded)",
      resp.status_code == 200,
      f"status={resp.status_code}")

resp = client.post("/api/notes/9999/approve")
check("POST /api/notes/{id}/approve (no token, un-guarded)",
      resp.status_code in (200, 404),  # 404 = note doesn't exist, but guard didn't block
      f"status={resp.status_code}")

resp = client.post("/api/notes/9999/reject")
check("POST /api/notes/{id}/reject (no token, un-guarded)",
      resp.status_code in (200, 404),
      f"status={resp.status_code}")

resp = client.post("/api/contributions/9999/approve",
                   json={"comment": "test"})
check("POST /api/contributions/{id}/approve (no token, un-guarded)",
      resp.status_code in (200, 404),
      f"status={resp.status_code}")

resp = client.post("/api/contributions/9999/reject",
                   json={"comment": "test"})
check("POST /api/contributions/{id}/reject (no token, un-guarded)",
      resp.status_code in (200, 404),
      f"status={resp.status_code}")

resp = client.post("/api/contributions/9999/request-revision",
                   json={"comment": "test"})
check("POST /api/contributions/{id}/request-revision (no token, un-guarded)",
      resp.status_code in (200, 404),
      f"status={resp.status_code}")

resp = client.post("/api/exercises",
                   json={"title": "test", "stem": "test stem", "answer": "1", "difficulty": 1})
check("POST /api/exercises (no token, un-guarded)",
      resp.status_code == 200,
      f"status={resp.status_code}")

# Learner endpoints should always work
resp = client.get("/api/health")
check("GET /api/health (learner, un-guarded)",
      resp.status_code == 200,
      f"status={resp.status_code}")

# ── Guarded mode (ADMIN_TOKEN set) ─────────────────────────────────
print("\nAdmin Guard Test — guarded mode (ADMIN_TOKEN=\"test-token\")\n")

import app.admin_auth  # noqa: E402
app.admin_auth.ADMIN_TOKEN = "test-token"

# Re-create the client to pick up the changed module state.
# The dependency reads ADMIN_TOKEN at call time, so we don't need a new client.
# But the module-level ADMIN_TOKEN was already imported; we mutated it above.

TOKEN = "test-token"
WRONG_TOKEN = "wrong-token"

# Without token: should get 403
resp = client.post("/api/import/sample")
check("POST /api/import/sample (no token, guarded)",
      resp.status_code == 403,
      f"status={resp.status_code} body={resp.text}")

# Wrong token: should get 403
resp = client.post("/api/import/sample", headers={"X-Admin-Token": WRONG_TOKEN})
check("POST /api/import/sample (wrong token, guarded)",
      resp.status_code == 403,
      f"status={resp.status_code} body={resp.text}")

# Correct token: should succeed
resp = client.post("/api/import/sample", headers={"X-Admin-Token": TOKEN})
check("POST /api/import/sample (correct token, guarded)",
      resp.status_code == 200,
      f"status={resp.status_code} body={resp.text}")

# Admin note endpoints
resp = client.post("/api/notes/9999/approve", headers={"X-Admin-Token": TOKEN})
check("POST /api/notes/{id}/approve (correct token, guarded)",
      resp.status_code in (200, 404),
      f"status={resp.status_code}")

resp = client.post("/api/notes/9999/approve")  # no token
check("POST /api/notes/{id}/approve (no token, guarded)",
      resp.status_code == 403,
      f"status={resp.status_code}")

# Admin contribution endpoints
resp = client.post("/api/contributions/9999/approve",
                   json={"comment": "test"},
                   headers={"X-Admin-Token": TOKEN})
check("POST /api/contributions/{id}/approve (correct token, guarded)",
      resp.status_code in (200, 404),
      f"status={resp.status_code}")

resp = client.post("/api/contributions/9999/approve",
                   json={"comment": "test"})  # no token
check("POST /api/contributions/{id}/approve (no token, guarded)",
      resp.status_code == 403,
      f"status={resp.status_code}")

# Admin exercise endpoint
resp = client.post("/api/exercises",
                   json={"title": "test", "stem": "test stem", "answer": "1", "difficulty": 1},
                   headers={"X-Admin-Token": TOKEN})
check("POST /api/exercises (correct token, guarded)",
      resp.status_code == 200,
      f"status={resp.status_code}")

resp = client.post("/api/exercises",
                   json={"title": "test", "stem": "test stem", "answer": "1", "difficulty": 1})  # no token
check("POST /api/exercises (no token, guarded)",
      resp.status_code == 403,
      f"status={resp.status_code}")

# Learner endpoints should still work WITHOUT token
resp = client.get("/api/health")
check("GET /api/health (learner, guarded)",
      resp.status_code == 200,
      f"status={resp.status_code}")

resp = client.get("/api/stats")
check("GET /api/stats (learner, guarded)",
      resp.status_code == 200,
      f"status={resp.status_code}")

resp = client.get("/api/knowledge-points")
check("GET /api/knowledge-points (learner, guarded)",
      resp.status_code == 200,
      f"status={resp.status_code}")

resp = client.post("/api/exercises/9999/attempts",
                   json={"result": "wrong"})
check("POST /api/exercises/{id}/attempts (learner, guarded)",
      resp.status_code in (200, 400, 404),  # 400/404 = exercise doesn't exist, guard didn't block
      f"status={resp.status_code}")

# Restore original token for cleanliness
app.admin_auth.ADMIN_TOKEN = _ORIG_TOKEN

# Summary
print(f"\n{passed} passed, {failed} failed")

if failed > 0:
    print("ADMIN GUARD TEST FAILED")
    sys.exit(1)
else:
    print("ADMIN GUARD TEST PASSED")
    sys.exit(0)
