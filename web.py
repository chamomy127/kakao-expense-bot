"""웹 대시보드: 화면(/)과 API(/api/*)

- 셋이 공유하는 방 비밀번호 하나(환경변수 ROOM_PASSWORD)로 잠금
- 사용자는 이름으로 구분 (가입 없음)
"""
import base64
import binascii
import hmac
import os
from io import BytesIO
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, desc, func, select

from PIL import Image, ImageOps, UnidentifiedImageError

from db import KST, avatars, engine, expenses
from icons import icon_png

ROOM = "web"  # 웹 대시보드 기록은 이 방 ID로 저장 (카톡 스킬 기록과 분리)
INDEX_HTML = Path(__file__).with_name("index.html")
ICON_SIZES = (180, 192, 512)
AVATAR_PX = 160
MAX_UPLOAD = 2_000_000  # 업로드 원본 최대 2MB (폰에서 미리 줄여서 보냄)

router = APIRouter()


# ── 인증 ────────────────────────────────────────────────────────
def check_password(x_room_password: str | None) -> None:
    expected = os.getenv("ROOM_PASSWORD", "")
    if not expected:
        raise HTTPException(503, "서버에 ROOM_PASSWORD 환경변수가 설정되지 않았어요.")
    given = (x_room_password or "").encode()
    if not hmac.compare_digest(given, expected.encode()):
        raise HTTPException(401, "비밀번호가 틀렸어요.")


# ── 유틸 ────────────────────────────────────────────────────────
def month_range(month: str | None) -> tuple[datetime, datetime, str]:
    """'2026-10' → (그달 1일 0시 KST, 다음달 1일 0시 KST, '2026-10')"""
    now = datetime.now(KST)
    try:
        y, m = (int(x) for x in month.split("-")) if month else (now.year, now.month)
        start = datetime(y, m, 1, tzinfo=KST)
    except Exception:
        raise HTTPException(400, "month는 YYYY-MM 형식이어야 해요.")
    end = datetime(y + (m == 12), m % 12 + 1, 1, tzinfo=KST)
    return start, end, f"{y:04d}-{m:02d}"


def clean_name(name: str) -> str:
    name = " ".join(name.split())
    if not 1 <= len(name) <= 20:
        raise HTTPException(400, "이름은 1~20자로 해주세요.")
    return name


class NewExpense(BaseModel):
    name: str
    amount: int = Field(gt=0, le=100_000_000)
    category: str = "기타"
    memo: str = ""


# ── 화면 ────────────────────────────────────────────────────────
@router.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def index():
    return HTMLResponse(INDEX_HTML.read_text(encoding="utf-8"),
                        headers={"Cache-Control": "no-cache"})


# ── 홈 화면 앱(PWA) ─────────────────────────────────────────────
@router.get("/manifest.webmanifest")
def manifest():
    return JSONResponse({
        "name": "거지방",
        "short_name": "거지방",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#f6f5f2",
        "theme_color": "#2f6fdb",
        "lang": "ko",
        "icons": [
            {"src": f"/icon-{n}.png", "sizes": f"{n}x{n}", "type": "image/png", "purpose": "any"}
            for n in ICON_SIZES
        ],
    }, media_type="application/manifest+json")


@router.get("/icon-{size}.png")
def icon(size: int):
    if size not in ICON_SIZES:
        raise HTTPException(404)
    return Response(icon_png(size), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=604800"})


# ── API ─────────────────────────────────────────────────────────
@router.post("/api/login")
def login(x_room_password: str | None = Header(None)):
    check_password(x_room_password)
    return {"ok": True}


@router.get("/api/summary")
def summary(
    me: str = Query(""),
    month: str | None = Query(None),
    x_room_password: str | None = Header(None),
):
    check_password(x_room_password)
    start, end, label = month_range(month)
    in_month = (
        (expenses.c.room_id == ROOM)
        & (expenses.c.created_at >= start)
        & (expenses.c.created_at < end)
    )
    with engine.connect() as conn:
        members = [r[0] for r in conn.execute(
            select(expenses.c.user_id).where(expenses.c.room_id == ROOM)
            .group_by(expenses.c.user_id).order_by(expenses.c.user_id)
        )]
        ranking = [
            {"name": r.user_id, "total": int(r.total), "count": int(r.cnt)}
            for r in conn.execute(
                select(expenses.c.user_id,
                       func.sum(expenses.c.amount).label("total"),
                       func.count().label("cnt"))
                .where(in_month).group_by(expenses.c.user_id)
                .order_by(desc("total"))
            )
        ]
        my_cats = [
            {"category": r.category, "total": int(r.total), "count": int(r.cnt)}
            for r in conn.execute(
                select(expenses.c.category,
                       func.sum(expenses.c.amount).label("total"),
                       func.count().label("cnt"))
                .where(in_month & (expenses.c.user_id == me))
                .group_by(expenses.c.category).order_by(desc("total"))
            )
        ] if me else []
        avatar_map = {
            r.name: "data:image/jpeg;base64," + base64.b64encode(r.image).decode()
            for r in conn.execute(
                select(avatars.c.name, avatars.c.image).where(avatars.c.room_id == ROOM)
            )
        }
        recent = [
            {"id": r.id, "name": r.user_id, "amount": r.amount,
             "category": r.category, "memo": r.memo,
             "created_at": r.created_at.astimezone(KST).isoformat()
             if r.created_at.tzinfo else r.created_at.replace(tzinfo=KST).isoformat()}
            for r in conn.execute(
                select(expenses).where(in_month)
                .order_by(desc(expenses.c.created_at), desc(expenses.c.id)).limit(30)
            )
        ]
    return {
        "month": label,
        "members": members,
        "ranking": ranking,
        "room_total": sum(r["total"] for r in ranking),
        "me": {
            "name": me,
            "total": sum(c["total"] for c in my_cats),
            "count": sum(c["count"] for c in my_cats),
            "categories": my_cats,
        },
        "recent": recent,
        "avatars": avatar_map,
    }


@router.post("/api/expenses")
def add_expense(body: NewExpense, x_room_password: str | None = Header(None)):
    check_password(x_room_password)
    name = clean_name(body.name)
    category = " ".join(body.category.split())[:20] or "기타"
    memo = " ".join(body.memo.split())[:100]
    with engine.begin() as conn:
        new_id = conn.execute(expenses.insert().values(
            room_id=ROOM, user_id=name, amount=body.amount,
            category=category, memo=memo, created_at=datetime.now(KST),
        )).inserted_primary_key[0]
    return {"ok": True, "id": new_id}


@router.delete("/api/expenses/{expense_id}")
def remove_expense(expense_id: int, name: str = Query(...),
                   x_room_password: str | None = Header(None)):
    check_password(x_room_password)
    with engine.begin() as conn:
        res = conn.execute(delete(expenses).where(
            (expenses.c.id == expense_id) & (expenses.c.room_id == ROOM)
            & (expenses.c.user_id == name)
        ))
    if res.rowcount == 0:
        raise HTTPException(404, "내 기록만 지울 수 있어요.")
    return {"ok": True}


# ── 프로필 사진 ─────────────────────────────────────────────────
class NewAvatar(BaseModel):
    name: str
    image: str  # data:image/...;base64,....


def to_avatar_jpeg(data_url: str) -> bytes:
    """업로드된 이미지를 가운데 기준 정사각형 160px JPEG로 다시 만든다 (이미지가 아니면 거절)"""
    try:
        b64 = data_url.split(",", 1)[1] if data_url.startswith("data:") else data_url
        raw = base64.b64decode(b64, validate=True)
    except (IndexError, binascii.Error):
        raise HTTPException(400, "이미지 형식이 올바르지 않아요.")
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(413, "사진이 너무 커요.")
    try:
        img = Image.open(BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "이미지 파일만 올릴 수 있어요.")
    img = ImageOps.exif_transpose(img).convert("RGB")
    img = ImageOps.fit(img, (AVATAR_PX, AVATAR_PX), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, "JPEG", quality=85, optimize=True)
    return buf.getvalue()


@router.put("/api/avatar")
def set_avatar(body: NewAvatar, x_room_password: str | None = Header(None)):
    check_password(x_room_password)
    name = clean_name(body.name)
    jpeg = to_avatar_jpeg(body.image)
    with engine.begin() as conn:
        conn.execute(delete(avatars).where(
            (avatars.c.room_id == ROOM) & (avatars.c.name == name)))
        conn.execute(avatars.insert().values(
            room_id=ROOM, name=name, image=jpeg, updated_at=datetime.now(KST)))
    return {"ok": True, "bytes": len(jpeg)}


@router.delete("/api/avatar")
def remove_avatar(name: str = Query(...), x_room_password: str | None = Header(None)):
    check_password(x_room_password)
    with engine.begin() as conn:
        conn.execute(delete(avatars).where(
            (avatars.c.room_id == ROOM) & (avatars.c.name == name)))
    return {"ok": True}
