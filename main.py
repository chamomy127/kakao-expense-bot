"""
지출 기록 서버
- 웹 대시보드: /  (web.py, index.html)
- 카카오 i 오픈빌더 스킬: /skill  (아래 코드)

명령어
  !지출 8900원 음식 햄버거   → 지출 기록 (금액 / 카테고리 / 메모)
  !순위 [전체]               → 이 방에서 이번 달(또는 전체) 지출 TOP 3
  !통계 [전체]               → 내 카테고리별 지출 통계
  !닉네임 효진               → 순위에 표시될 이름 등록
  !취소                      → 내 마지막 지출 기록 삭제
  !도움말
"""
import re
from datetime import datetime

from fastapi import FastAPI, Request
from sqlalchemy import delete, desc, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from db import KST, engine, expenses, nicknames
import web

app = FastAPI()
app.include_router(web.router)


# ── 오픈빌더 요청/응답 헬퍼 ───────────────────────────────────────
def extract_ids(body: dict) -> tuple[str, str, str]:
    """(방 ID, 유저 ID, 발화) 추출. 그룹채팅이 아니면 방 ID는 'dm:<유저>'"""
    req = body.get("userRequest", {}) or {}
    user = req.get("user", {}) or {}
    props = user.get("properties", {}) or {}
    user_id = props.get("botUserKey") or props.get("plusfriendUserKey") or user.get("id") or "unknown"

    chat = req.get("chat", {}) or {}
    chat_props = chat.get("properties", {}) or {}
    room_id = chat_props.get("botGroupKey") or chat.get("id")
    if not room_id:
        room_id = f"dm:{user_id}"

    utterance = (req.get("utterance") or "").strip()
    return room_id, user_id, utterance


def reply(text: str) -> dict:
    return {
        "version": "2.0",
        "template": {"outputs": [{"simpleText": {"text": text[:1000]}}]},
    }


def won(n: int) -> str:
    return f"{n:,}원"


def month_start_kst() -> datetime:
    now = datetime.now(KST)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def display_name(conn, room_id: str, user_id: str) -> str:
    name = conn.execute(
        select(nicknames.c.name).where(
            nicknames.c.room_id == room_id, nicknames.c.user_id == user_id
        )
    ).scalar()
    return name or f"익명{user_id[-4:]}"


# ── 명령어 처리 ─────────────────────────────────────────────────
AMOUNT_RE = re.compile(r"^([\d,]+)\s*(원)?$")
HELP = (
    "💸 지출봇 사용법\n"
    "!지출 8900원 음식 햄버거\n"
    "!순위  (이번 달 TOP3, '!순위 전체'는 누적)\n"
    "!통계  (내 카테고리별 통계)\n"
    "!닉네임 홍길동  (순위에 보일 이름)\n"
    "!취소  (마지막 기록 삭제)"
)


def cmd_spend(conn, room_id, user_id, args: list[str]) -> str:
    if not args:
        return "형식: !지출 8900원 음식 햄버거"
    m = AMOUNT_RE.match(args[0])
    if not m:
        return "금액을 못 알아봤어요 😅\n예) !지출 8900원 음식 햄버거"
    amount = int(m.group(1).replace(",", ""))
    if amount <= 0 or amount > 100_000_000:
        return "금액은 1원 ~ 1억원 사이로 입력해 주세요."
    category = args[1] if len(args) > 1 else "기타"
    memo = " ".join(args[2:])[:200]

    conn.execute(expenses.insert().values(
        room_id=room_id, user_id=user_id, amount=amount,
        category=category[:50], memo=memo, created_at=datetime.now(KST),
    ))
    month_total = conn.execute(
        select(func.coalesce(func.sum(expenses.c.amount), 0)).where(
            expenses.c.room_id == room_id,
            expenses.c.user_id == user_id,
            expenses.c.created_at >= month_start_kst(),
        )
    ).scalar()
    name = display_name(conn, room_id, user_id)
    line = f"✅ {name}님 {won(amount)} [{category}]"
    if memo:
        line += f" {memo}"
    return f"{line} 기록 완료!\n이번 달 누적: {won(month_total)}"


def cmd_rank(conn, room_id, user_id, args) -> str:
    all_time = bool(args) and args[0] == "전체"
    q = (
        select(expenses.c.user_id, func.sum(expenses.c.amount).label("total"))
        .where(expenses.c.room_id == room_id)
        .group_by(expenses.c.user_id)
        .order_by(desc("total"))
        .limit(3)
    )
    if not all_time:
        q = q.where(expenses.c.created_at >= month_start_kst())
    rows = conn.execute(q).all()
    title = "누적" if all_time else f"{datetime.now(KST).month}월"
    if not rows:
        return f"아직 {title} 지출 기록이 없어요."
    medals = ["🥇", "🥈", "🥉"]
    lines = [f"💰 {title} 지출 TOP 3"]
    for i, r in enumerate(rows):
        lines.append(f"{medals[i]} {display_name(conn, room_id, r.user_id)} - {won(int(r.total))}")
    return "\n".join(lines)


def cmd_stats(conn, room_id, user_id, args) -> str:
    all_time = bool(args) and args[0] == "전체"
    q = (
        select(
            expenses.c.category,
            func.sum(expenses.c.amount).label("total"),
            func.count().label("cnt"),
        )
        .where(expenses.c.room_id == room_id, expenses.c.user_id == user_id)
        .group_by(expenses.c.category)
        .order_by(desc("total"))
    )
    if not all_time:
        q = q.where(expenses.c.created_at >= month_start_kst())
    rows = conn.execute(q).all()
    name = display_name(conn, room_id, user_id)
    title = "누적" if all_time else f"{datetime.now(KST).month}월"
    if not rows:
        return f"{name}님의 {title} 지출 기록이 없어요."

    grand = sum(int(r.total) for r in rows)
    top = rows[0]
    lines = [
        f"📊 {name}님의 {title} 지출 통계",
        f"총 {won(grand)} ({sum(r.cnt for r in rows)}건)",
        f"최다 카테고리: {top.category} {won(int(top.total))}",
        "",
    ]
    for r in rows[:8]:
        pct = int(r.total) * 100 / grand
        bar = "■" * max(1, round(pct / 10))
        lines.append(f"{r.category} {won(int(r.total))} ({pct:.0f}%, {r.cnt}건) {bar}")
    if len(rows) > 8:
        lines.append(f"…외 {len(rows) - 8}개 카테고리")
    return "\n".join(lines)


def cmd_nick(conn, room_id, user_id, args) -> str:
    if not args:
        return "형식: !닉네임 홍길동"
    name = " ".join(args)[:30]
    values = dict(room_id=room_id, user_id=user_id, name=name)
    ins = pg_insert if engine.dialect.name == "postgresql" else sqlite_insert
    stmt = ins(nicknames).values(**values).on_conflict_do_update(
        index_elements=["room_id", "user_id"], set_={"name": name}
    )
    conn.execute(stmt)
    return f"👍 이제 '{name}'(으)로 표시돼요."


def cmd_undo(conn, room_id, user_id, args) -> str:
    row = conn.execute(
        select(expenses).where(
            expenses.c.room_id == room_id, expenses.c.user_id == user_id
        ).order_by(desc(expenses.c.id)).limit(1)
    ).first()
    if not row:
        return "삭제할 기록이 없어요."
    conn.execute(delete(expenses).where(expenses.c.id == row.id))
    return f"🗑️ 삭제: {won(row.amount)} [{row.category}] {row.memo}".rstrip()


COMMANDS = {
    "지출": cmd_spend,
    "순위": cmd_rank,
    "통계": cmd_stats,
    "닉네임": cmd_nick,
    "취소": cmd_undo,
}


# ── 엔드포인트 ──────────────────────────────────────────────────
@app.post("/skill")
async def skill(request: Request):
    body = await request.json()
    room_id, user_id, text = extract_ids(body)

    if not text.startswith("!"):
        return reply(HELP)

    parts = text[1:].split()
    cmd, args = (parts[0], parts[1:]) if parts else ("", [])

    handler = COMMANDS.get(cmd)
    if handler is None:
        return reply(HELP)

    try:
        with engine.begin() as conn:
            return reply(handler(conn, room_id, user_id, args))
    except Exception as e:  # 오픈빌더는 실패 응답 시 에러 말풍선을 띄우므로 항상 200으로 응답
        print("ERROR:", repr(e))
        return reply("앗, 처리 중 오류가 났어요. 잠시 후 다시 시도해 주세요.")


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"ok": True}
