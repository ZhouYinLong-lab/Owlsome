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

# 7. POST /api/exercises
resp = client.post("/api/exercises",
                   json={"title": "smoke test exercise",
                         "stem": "设二元函数 f(x,y) 在点 (0,0) 附近有定义。若沿直线 y=kx 趋近时极限结果与 k 有关，能否说明二重极限存在？为什么？",
                         "answer": "不能，因为二重极限要求沿所有路径趋近时结果都相同。仅沿直线不够。",
                         "difficulty": 2})
body = resp.json()
exercise_id = body.get("id")
ok = resp.status_code == 200 and exercise_id is not None
check("POST /api/exercises",
      ok,
      f"status={resp.status_code} exercise_id={exercise_id}")

# 8. POST /api/exercises/recommend
resp = client.post("/api/exercises/recommend",
                   json={"exercise_id": exercise_id, "top_k": 3})
body = resp.json()
ok = resp.status_code == 200 and isinstance(body.get("candidates"), list)
check("POST /api/exercises/recommend",
      ok,
      f"status={resp.status_code} candidates={len(body.get('candidates', [])) if isinstance(body, dict) else 'n/a'}")

# 9. POST /api/exercises/{id}/link (bind first recommendation if available)
link_ok = False
candidates = body.get("candidates", []) if isinstance(body, dict) else []
if candidates and exercise_id:
    first_kp = candidates[0].get("knowledge_point_id")
    if first_kp:
        resp = client.post(f"/api/exercises/{exercise_id}/link",
                           json={"knowledge_point_id": first_kp,
                                 "confidence": 1.0,
                                 "reason": "smoke test auto-link"})
        body = resp.json()
        link_ok = resp.status_code == 200 and body.get("exercise_id") == exercise_id
check("POST /api/exercises/{id}/link",
      link_ok,
      f"exercise_id={exercise_id} first_kp={first_kp if candidates else 'n/a'}")
if link_ok and first_kp:
    linked_kp_id = first_kp
else:
    linked_kp_id = None

# 10. GET /api/knowledge-points/{id}/exercises
if linked_kp_id:
    resp = client.get(f"/api/knowledge-points/{linked_kp_id}/exercises")
    body = resp.json()
    ok = resp.status_code == 200 and isinstance(body, list) and len(body) > 0
    check("GET /api/knowledge-points/{id}/exercises",
          ok,
          f"status={resp.status_code} count={len(body) if isinstance(body, list) else 'n/a'}")
else:
    check("GET /api/knowledge-points/{id}/exercises",
          True,
          "skipped (no linked knowledge point)")
    ok = True  # skip is not a failure

# 11. POST /api/exercises/{id}/attempts (result=wrong)
if exercise_id:
    resp = client.post(f"/api/exercises/{exercise_id}/attempts",
                       json={"knowledge_point_id": linked_kp_id,
                             "result": "wrong",
                             "note": "smoke test attempt"})
    body = resp.json()
    ok = resp.status_code == 200 and body.get("result") == "wrong"
    check("POST /api/exercises/{id}/attempts",
          ok,
          f"status={resp.status_code} result={body.get('result') if isinstance(body, dict) else 'n/a'}")
else:
    check("POST /api/exercises/{id}/attempts",
          True,
          "skipped (no exercise created)")
    ok = True  # skip is not a failure

# Summary
print(f"\n{passed} passed, {failed} failed")

if failed > 0:
    print("SMOKE TEST FAILED")
    sys.exit(1)
else:
    print("SMOKE TEST PASSED")
    sys.exit(0)
