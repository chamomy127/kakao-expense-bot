"""오픈빌더 스킬 요청을 흉내 내서 봇을 테스트합니다.  실행: python test_bot.py"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
if os.path.exists("test.db"):
    os.remove("test.db")

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)
ROOM = "group-abc"


def say(user: str, text: str, room: str = ROOM) -> str:
    body = {
        "userRequest": {
            "utterance": text,
            "user": {"id": user, "properties": {"botUserKey": user}},
            "chat": {"id": room, "type": "botGroupKey", "properties": {"botGroupKey": room}},
        }
    }
    r = client.post("/skill", json=body)
    assert r.status_code == 200
    out = r.json()["template"]["outputs"][0]["simpleText"]["text"]
    print(f"[{user}] {text}\n{out}\n")
    return out


say("u_hyojin", "!닉네임 효진")
say("u_minsu", "!닉네임 민수")
assert "기록 완료" in say("u_hyojin", "!지출 8900원 음식 햄버거")
say("u_hyojin", "!지출 12,000원 교통 택시")
say("u_hyojin", "!지출 4500 음식 커피")
say("u_minsu", "!지출 50000원 쇼핑 운동화")
say("u_jiwoo", "!지출 3000원 음식")
say("u_dahye", "!지출 1000원 기타")
say("u_other", "!지출 999999원 쇼핑", room="other-room")  # 다른 방 → 순위에 안 나와야 함

rank = say("u_hyojin", "!순위")
assert "민수 - 50,000원" in rank and "효진 - 25,400원" in rank
assert "999,999" not in rank and "익명" in rank and rank.count("\n") == 3

stats = say("u_hyojin", "!통계")
assert "총 25,400원 (3건)" in stats and "음식 13,400원" in stats

assert "금액을 못" in say("u_hyojin", "!지출 만원 음식")
assert "삭제" in say("u_hyojin", "!취소")
assert "총 20,900원" in say("u_hyojin", "!통계 전체")
assert "사용법" in say("u_hyojin", "안녕")
print("✅ 모든 테스트 통과")
