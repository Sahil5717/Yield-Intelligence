"""
Integration Test Suite for Yield Intelligence Platform
Run: cd backend && python test_integration.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from api import app
from starlette.testclient import TestClient

client = TestClient(app)
passed = 0
failed = 0
errors = []

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        errors.append(f"{name}: {detail}")
        print(f"  ❌ {name}: {detail}")

print("═══ YIELD INTELLIGENCE — INTEGRATION TESTS ═══\n")

# ──── BOOT ────
print("BOOT")
r = client.get("/api/health")
test("Health endpoint exists", r.status_code == 200)

r = client.post("/api/load-mock-data")
test("Mock data loads", r.status_code == 200, f"got {r.status_code}")
d = r.json() if r.status_code == 200 else {}
test("Mock data has 4800+ rows", d.get("rows", 0) >= 4800, f"got {d.get('rows')}")
test("Engines auto-run on boot", d.get("engines_run") == True)

r = client.get("/api/health")
test("Health shows healthy after boot", r.json().get("status") == "healthy", f"got {r.json().get('status')}")

# ──── FULL STATE (frontend contract) ────
print("\nFULL STATE")
r = client.get("/api/full-state")
test("Full state returns 200", r.status_code == 200)
s = r.json() if r.status_code == 200 else {}

test("Has rows array", isinstance(s.get("rows"), list) and len(s["rows"]) > 0, f"got {len(s.get('rows', []))}")
if s.get("rows"):
    r0 = s["rows"][0]
    for f in ["ch", "spend", "month", "ct"]:
        test(f"rows[0] has '{f}'", f in r0, f"keys: {list(r0.keys())[:8]}")

test("Has opt.channels", isinstance(s.get("opt", {}).get("channels"), list) and len(s["opt"]["channels"]) > 0)
if s.get("opt", {}).get("channels"):
    c0 = s["opt"]["channels"][0]
    for f in ["cS", "oS", "chg", "cR", "oR", "mROI", "channel"]:
        test(f"opt.channels[0] has '{f}'", f in c0)

test("Has opt.summary", isinstance(s.get("opt", {}).get("summary"), dict))
if s.get("opt", {}).get("summary"):
    for f in ["cRev", "oRev", "uplift", "cROI", "oROI"]:
        test(f"opt.summary has '{f}'", f in s["opt"]["summary"])

test("Has pl.totalRisk", "totalRisk" in s.get("pl", {}))
test("Has pl.leak.total", "total" in s.get("pl", {}).get("leak", {}))
test("Has pl.exp.total", "total" in s.get("pl", {}).get("exp", {}))
test("Has pl.cost.total", "total" in s.get("pl", {}).get("cost", {}))

test("Has recs array", isinstance(s.get("recs"), list) and len(s["recs"]) > 0)
if s.get("recs"):
    for f in ["type", "ch", "impact", "rationale", "conf", "effort"]:
        test(f"recs[0] has '{f}'", f in s["recs"][0])

test("Has attr models", isinstance(s.get("attr"), dict) and len(s["attr"]) > 0)
test("Has curves", isinstance(s.get("curves"), dict) and len(s["curves"]) > 0)
test("Has tS > 0", s.get("tS", 0) > 0)
test("Has apiMode=True", s.get("apiMode") == True)
test("Has warnings list", isinstance(s.get("warnings"), list))

# ──── ALL ENDPOINTS ────
print("\nENDPOINTS")
endpoints = [
    ("GET", "/api/health"), ("GET", "/api/data-readiness"), ("GET", "/api/current-state"),
    ("GET", "/api/full-state"), ("GET", "/api/response-curves"), ("GET", "/api/recommendations"),
    ("GET", "/api/pillars"), ("GET", "/api/trend-analysis"), ("GET", "/api/funnel-analysis"),
    ("GET", "/api/roi-analysis"), ("GET", "/api/sensitivity"), ("GET", "/api/business-case"),
    ("GET", "/api/markov-attribution"), ("GET", "/api/forecast"), ("GET", "/api/cross-channel"),
    ("GET", "/api/shapley"),
    ("POST", "/api/optimize?total_budget=30000000"),
    ("POST", "/api/adstock"), ("POST", "/api/run-analysis"), ("POST", "/api/mmm"),
]
for m, ep in endpoints:
    r = client.get(ep) if m == "GET" else client.post(ep)
    test(f"{m} {ep}", r.status_code == 200, f"got {r.status_code}")

# ──── UPLOAD FLOW ────
print("\nUPLOAD FLOW")
csv_path = os.path.join(os.path.dirname(__file__), "..", "templates", "campaign_performance_template.csv")
if os.path.exists(csv_path):
    with open(csv_path, "rb") as f:
        r = client.post("/api/upload", files={"file": ("test.csv", f, "text/csv")})
    test("Upload CSV", r.status_code == 200, f"got {r.status_code}")
    
    r = client.post("/api/run-analysis")
    test("Run analysis after upload", r.status_code == 200, f"got {r.status_code}")
    
    r = client.get("/api/full-state")
    test("Full state after upload", r.status_code == 200)
    s2 = r.json() if r.status_code == 200 else {}
    test("Upload data produces warnings", len(s2.get("warnings", [])) > 0, "no warnings for small dataset")
else:
    test("Template CSV exists", False, f"not found at {csv_path}")

# ──── GUARDRAILS ────
print("\nGUARDRAILS")
# Reload mock data for proper optimization
client.post("/api/load-mock-data")
r = client.post("/api/optimize?total_budget=100&objective=balanced")
o = r.json() if r.status_code == 200 else {}
test("Tiny budget returns 200", r.status_code == 200)
test("Tiny budget triggers guardrail", len(o.get("optimizer_info", {}).get("warnings", [])) > 0)
test("Tiny budget uplift is 0%", o.get("summary", {}).get("uplift_pct", -1) == 0.0)

# Normal optimization should produce positive uplift
r = client.post("/api/optimize?total_budget=30000000&objective=balanced")
o = r.json() if r.status_code == 200 else {}
test("Normal budget produces positive uplift", o.get("summary", {}).get("uplift_pct", 0) > 0, 
     f"got {o.get('summary', {}).get('uplift_pct')}")

# ──── RESULTS ────
print(f"\n{'═'*50}")
print(f"  PASSED: {passed}  |  FAILED: {failed}  |  TOTAL: {passed+failed}")
print(f"{'═'*50}")
if errors:
    print("\nFailures:")
    for e in errors:
        print(f"  • {e}")
else:
    print("\n  ALL TESTS PASS ✅")
print()
