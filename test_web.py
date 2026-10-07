"""웹 대시보드 API 테스트.  실행: python test_web.py"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_web.db")
os.environ["ROOM_PASSWORD"] = "test-pass"
if os.environ["DATABASE_URL"].startswith("sqlite") and os.path.exists("test_web.db"):
    os.remove("test_web.db")

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

c = TestClient(app)
H = {"X-Room-Password": "test-pass"}

assert c.get("/").status_code == 200 and "거지방" in c.get("/").text
assert c.head("/").status_code == 200
assert c.get("/health").json() == {"ok": True}
assert c.post("/api/login", headers={"X-Room-Password": "wrong"}).status_code == 401
assert c.post("/api/login").status_code == 401
assert c.post("/api/login", headers=H).json() == {"ok": True}

def add(name, amount, category="음식", memo=""):
    r = c.post("/api/expenses", headers=H, json={"name": name, "amount": amount, "category": category, "memo": memo})
    assert r.status_code == 200, r.text
    return r.json()["id"]

add("효진", 8900, "음식", "햄버거")
add("효진", 12000, "교통", "택시")
coffee = add("효진", 4500, "카페", "아아")
add("민수", 50000, "쇼핑", "운동화")
add("지우", 3000)
assert c.post("/api/expenses", headers=H, json={"name": "x", "amount": 0}).status_code == 422
assert c.post("/api/expenses", headers=H, json={"name": "", "amount": 100}).status_code == 400
assert c.post("/api/expenses", json={"name": "x", "amount": 100}).status_code == 401

s = c.get("/api/summary", params={"me": "효진"}, headers=H).json()
assert [r["name"] for r in s["ranking"]] == ["민수", "효진", "지우"]
assert s["ranking"][1]["total"] == 25400 and s["room_total"] == 78400
assert s["me"]["total"] == 25400 and s["me"]["count"] == 3
assert s["me"]["categories"][0] == {"category": "교통", "total": 12000, "count": 1}
assert sorted(s["members"]) == ["민수", "지우", "효진"]
assert len(s["recent"]) == 5 and s["recent"][0]["name"] == "지우"

# 다른 사람 기록은 못 지움, 내 것은 지움
assert c.delete(f"/api/expenses/{coffee}", params={"name": "민수"}, headers=H).status_code == 404
assert c.delete(f"/api/expenses/{coffee}", params={"name": "효진"}, headers=H).status_code == 200
assert c.get("/api/summary", params={"me": "효진"}, headers=H).json()["me"]["total"] == 20900

# 지난달은 비어 있음, 잘못된 월 형식은 400
assert c.get("/api/summary", params={"month": "2020-01"}, headers=H).json()["ranking"] == []
assert c.get("/api/summary", params={"month": "abc"}, headers=H).status_code == 400

# 홈 화면 앱: manifest·아이콘
m = c.get("/manifest.webmanifest").json()
assert m["name"] == "거지방" and m["display"] == "standalone"
for n in (180, 192, 512):
    r = c.get(f"/icon-{n}.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.content[:4] == b"\x89PNG"
assert c.get("/icon-999.png").status_code == 404

# 프로필 사진: 큰 사진 → 160px JPEG로 저장, 요약에 포함, 삭제
import base64, io
from PIL import Image
buf = io.BytesIO(); Image.new("RGB", (1200, 800), (200, 80, 40)).save(buf, "PNG")
url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
r = c.put("/api/avatar", headers=H, json={"name": "효진", "image": url})
assert r.status_code == 200 and r.json()["bytes"] < 20000, r.text
av = c.get("/api/summary", params={"me": "효진"}, headers=H).json()["avatars"]
assert list(av) == ["효진"] and av["효진"].startswith("data:image/jpeg;base64,")
img = Image.open(io.BytesIO(base64.b64decode(av["효진"].split(",", 1)[1])))
assert img.size == (160, 160)
c.put("/api/avatar", headers=H, json={"name": "효진", "image": url})  # 다시 올려도 한 장만 유지
assert len(c.get("/api/summary", headers=H).json()["avatars"]) == 1
assert c.put("/api/avatar", headers=H, json={"name": "효진", "image": "data:image/png;base64,aGVsbG8="}).status_code == 400
assert c.put("/api/avatar", headers=H, json={"name": "효진", "image": "not-base64!!"}).status_code == 400
assert c.put("/api/avatar", json={"name": "효진", "image": url}).status_code == 401
assert c.delete("/api/avatar", params={"name": "효진"}, headers=H).status_code == 200
assert c.get("/api/summary", headers=H).json()["avatars"] == {}

# 카톡 스킬 엔드포인트도 여전히 동작
r = c.post("/skill", json={"userRequest": {"utterance": "!순위", "user": {"id": "u"}}})
assert r.json()["version"] == "2.0"
print("✅ 웹 API 테스트 통과")
