"""End-to-end exercise of the real API using httpx ASGI transport."""
import asyncio, os, sys, pathlib

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_e2e.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-e2e-only"
os.environ["DEBUG"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"
import logging
logging.disable(logging.WARNING)
pathlib.Path("test_e2e.db").unlink(missing_ok=True)

import httpx
from app.main import app
from app.db import init_db

SAMPLE = pathlib.Path("/tmp/sample_resume.txt").read_bytes()
JD = """Senior Backend Engineer
We require strong experience with Python and Go, and expertise in distributed systems.
• Must have experience with Kubernetes and Docker in production
• Experience with PostgreSQL, Kafka and event-driven architecture
• Familiar with Terraform and infrastructure as code
• Experience mentoring engineers and leading technical projects"""

def check(label, cond, extra=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{(' — ' + str(extra)) if extra and not cond else ''}")
    if not cond:
        globals()["FAILED"] = True

FAILED = False

async def main():
    global FAILED
    await init_db()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        print("\n[health]")
        r = await c.get("/api/health")
        check("health 200", r.status_code == 200, r.text)
        check("reports ai availability", "ai_available" in r.json())

        print("\n[auth]")
        r = await c.post("/api/auth/register", json={"email":"JANE@Example.com","password":"weak"})
        check("weak password rejected 422", r.status_code == 422, r.status_code)

        r = await c.post("/api/auth/register", json={
            "email":"JANE@Example.com","password":"Str0ngPassw0rd","full_name":"Jane Martinez",
            "target_role":"Senior Backend Engineer"})
        check("register 201", r.status_code == 201, r.text[:200])
        tokens = r.json()
        access, refresh = tokens["access_token"], tokens["refresh_token"]

        r = await c.post("/api/auth/register", json={"email":"jane@example.com","password":"Str0ngPassw0rd"})
        check("duplicate email 409 (case-insensitive)", r.status_code == 409, r.status_code)

        r = await c.get("/api/auth/me")
        check("unauthenticated me 401", r.status_code == 401, r.status_code)

        auth = {"Authorization": f"Bearer {access}"}
        r = await c.get("/api/auth/me", headers=auth)
        check("me 200", r.status_code == 200, r.text[:200])
        check("email normalised to lowercase", r.json()["email"] == "jane@example.com", r.json().get("email"))

        r = await c.post("/api/auth/login", json={"email":"jane@example.com","password":"wrong"})
        check("bad password 401", r.status_code == 401, r.status_code)

        r = await c.post("/api/auth/refresh", json={"refresh_token": refresh})
        check("refresh 200", r.status_code == 200, r.text[:200])
        new_refresh = r.json()["refresh_token"]
        r = await c.post("/api/auth/refresh", json={"refresh_token": refresh})
        check("replayed refresh token rejected 401", r.status_code == 401, r.status_code)
        r = await c.post("/api/auth/refresh", json={"refresh_token": new_refresh})
        check("rotated token also revoked after reuse-detection", r.status_code == 401, r.status_code)

        # Re-login to get a clean session after the reuse lockout.
        r = await c.post("/api/auth/login", json={"email":"jane@example.com","password":"Str0ngPassw0rd"})
        check("re-login 200", r.status_code == 200, r.text[:200])
        auth = {"Authorization": f"Bearer {r.json()['access_token']}"}

        print("\n[resumes]")
        r = await c.post("/api/resumes", headers=auth,
                         files={"file": ("resume.exe", b"MZ\x00binary", "application/octet-stream")})
        check("bad extension 415", r.status_code == 415, r.status_code)

        r = await c.post("/api/resumes", headers=auth,
                         files={"file": ("tiny.txt", b"too short", "text/plain")})
        check("unreadable file 422", r.status_code == 422, r.status_code)

        r = await c.post("/api/resumes", headers=auth,
                         files={"file": ("resume.txt", SAMPLE, "text/plain")})
        check("upload 201", r.status_code == 201, r.text[:300])
        resume = r.json()
        rid = resume["id"]
        check("word_count parsed", resume["word_count"] > 100, resume.get("word_count"))

        r = await c.get("/api/resumes", headers=auth)
        check("list resumes returns 1", len(r.json()) == 1, len(r.json()))

        print("\n[analysis — no job description]")
        r = await c.post(f"/api/resumes/{rid}/analyze", headers=auth,
                         json={"include_ai": False})
        check("analyze 201", r.status_code == 201, r.text[:300])
        a1 = r.json()
        check("status complete", a1["status"] == "complete", a1.get("status"))
        check("score in range", 0 <= a1["overall_score"] <= 100, a1.get("overall_score"))
        check("findings present", len(a1["findings"]) > 3, len(a1["findings"]))
        check("priorities present", len(a1["priorities"]) > 0, len(a1["priorities"]))
        check("band + verdict set", bool(a1["band"]) and bool(a1["verdict"]), (a1.get("band"), a1.get("verdict")))
        check("job-match marked n/a", any(c["category"]=="keywords" and not c["applicable"] for c in a1["category_scores"]))
        check("no keyword report", a1["keyword_report"] is None)
        check("ai opted out -> no review, no error", a1["ai_review"] is None and a1["ai_error"] is None, a1.get("ai_error"))

        r = await c.post(f"/api/resumes/{rid}/analyze", headers=auth, json={"include_ai": True})
        a_ai = r.json()
        import os as _os
        if _os.environ.get("OPENAI_API_KEY"):
            check("ai review returned", a_ai["ai_review"] is not None, a_ai.get("ai_error"))
        else:
            check("ai requested but unconfigured -> explains why",
                  a_ai["ai_review"] is None and bool(a_ai["ai_error"]), a_ai.get("ai_error"))
        print(f"      score={a1['overall_score']:.1f} ({a1['band']}) findings={len(a1['findings'])} in {a1['duration_ms']}ms")

        print("\n[analysis — with job description]")
        r = await c.post(f"/api/resumes/{rid}/analyze", headers=auth,
                         json={"job_description": JD, "target_role":"Senior Backend Engineer", "include_ai": False})
        check("analyze 201", r.status_code == 201, r.text[:300])
        a2 = r.json()
        check("keyword report present", a2["keyword_report"] is not None)
        check("job-match now applicable", any(c["category"]=="keywords" and c["applicable"] for c in a2["category_scores"]))
        kr = a2["keyword_report"]
        print(f"      score={a2['overall_score']:.1f} coverage={kr['coverage']:.0%} matched={kr['matched_count']}/{kr['total_count']}")

        print("\n[history + ownership]")
        r = await c.get("/api/analyses", headers=auth)
        check("history has 3", len(r.json()) == 3, len(r.json()))
        check("history carries filename", r.json()[0]["resume_filename"] == "resume.txt")

        r = await c.get(f"/api/analyses/{a1['id']}", headers=auth)
        check("analysis detail 200", r.status_code == 200)

        r = await c.get("/api/stats", headers=auth)
        st = r.json()
        check("stats counts", st["resume_count"]==1 and st["analysis_count"]==3, st)

        # A second user must not see or touch the first user's data.
        r = await c.post("/api/auth/register", json={"email":"mallory@example.com","password":"Str0ngPassw0rd"})
        other = {"Authorization": f"Bearer {r.json()['access_token']}"}
        r = await c.get(f"/api/resumes/{rid}", headers=other)
        check("cross-user resume access 404", r.status_code == 404, r.status_code)
        r = await c.get(f"/api/analyses/{a1['id']}", headers=other)
        check("cross-user analysis access 404", r.status_code == 404, r.status_code)
        r = await c.post(f"/api/resumes/{rid}/analyze", headers=other, json={"include_ai": False})
        check("cross-user analyze 404", r.status_code == 404, r.status_code)
        r = await c.get("/api/resumes", headers=other)
        check("other user sees no resumes", r.json() == [], r.json())

        print("\n[compare]")
        # Chronological order on this resume: a1 (no JD) -> a_ai -> a2 (JD).
        r = await c.get(f"/api/analyses/{a2['id']}/compare", headers=auth)
        check("auto compare 200", r.status_code == 200, r.text[:200])
        cmpb = r.json()
        check("baseline is the immediately previous review",
              cmpb["baseline"]["id"] == a_ai["id"], (cmpb["baseline"]["id"], a_ai["id"]))
        check("delta fields present",
              all(k in cmpb["delta"] for k in ("overall", "categories", "resolved", "introduced", "still_open")))
        expected = round(a2["overall_score"] - a_ai["overall_score"], 1)
        check("overall delta arithmetic", abs(cmpb["delta"]["overall"] - expected) < 0.06,
              (cmpb["delta"]["overall"], expected))
        check("per-category deltas present", len(cmpb["delta"]["categories"]) >= 4,
              len(cmpb["delta"]["categories"]))
        r = await c.get(f"/api/analyses/{a2['id']}/compare", params={"with": a1["id"]}, headers=auth)
        check("explicit baseline honoured", r.status_code == 200 and r.json()["baseline"]["id"] == a1["id"],
              r.text[:150])
        r = await c.get(f"/api/analyses/{a2['id']}/compare", params={"with": a2["id"]}, headers=auth)
        check("self-compare rejected 400", r.status_code == 400, r.status_code)
        r = await c.get(f"/api/analyses/{a1['id']}/compare", headers=auth)
        check("earliest review has no baseline 404", r.status_code == 404, r.status_code)
        r = await c.get(f"/api/analyses/{a2['id']}/compare", headers=other)
        check("cross-user compare 404", r.status_code == 404, r.status_code)

        print("\n[ai retry endpoint]")
        r = await c.post(f"/api/analyses/{a2['id']}/ai", headers=auth)
        check("ai retry without key 503", r.status_code == 503, r.status_code)
        r = await c.post(f"/api/analyses/{a2['id']}/ai", headers=other)
        check("cross-user ai retry 404", r.status_code == 404, r.status_code)

        print("\n[account deletion]")
        r = await c.request("DELETE", "/api/auth/me", headers=other, json={"password": "WrongPassw0rd"})
        check("wrong password 400", r.status_code == 400, r.status_code)
        r = await c.request("DELETE", "/api/auth/me", headers=other, json={"password": "Str0ngPassw0rd"})
        check("account deleted 200", r.status_code == 200, r.text[:150])
        r = await c.post("/api/auth/login", json={"email": "mallory@example.com", "password": "Str0ngPassw0rd"})
        check("deleted account can't sign in", r.status_code == 401, r.status_code)

        print("\n[deletion cascade]")
        r = await c.delete(f"/api/resumes/{rid}", headers=auth)
        check("delete resume 200", r.status_code == 200, r.text[:200])
        r = await c.get("/api/analyses", headers=auth)
        check("analyses cascaded away", r.json() == [], r.json())

    pathlib.Path("test_e2e.db").unlink(missing_ok=True)
    print("\n" + ("SOME CHECKS FAILED" if FAILED else "ALL CHECKS PASSED"))
    return 1 if FAILED else 0

sys.exit(asyncio.run(main()))
