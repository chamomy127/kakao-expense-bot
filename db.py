"""DB 연결과 테이블 정의 (카톡 스킬·웹 대시보드 공용)"""
import os
from datetime import timedelta, timezone

from sqlalchemy import (
    Column, DateTime, Integer, LargeBinary, MetaData, String, Table, create_engine,
)

# 로컬: SQLite / 배포: Neon 등 Postgres URL을 DATABASE_URL에 넣으면 됨
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./expense.db")
# Postgres 주소는 psycopg(v3) 드라이버를 쓰도록 스킴 통일
for _old in ("postgres://", "postgresql://"):
    if DATABASE_URL.startswith(_old):
        DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len(_old):]

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
meta = MetaData()

expenses = Table(
    "expenses", meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("room_id", String(128), index=True, nullable=False),
    Column("user_id", String(128), index=True, nullable=False),
    Column("amount", Integer, nullable=False),
    Column("category", String(50), nullable=False),
    Column("memo", String(200), nullable=False, default=""),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

nicknames = Table(
    "nicknames", meta,
    Column("room_id", String(128), primary_key=True),
    Column("user_id", String(128), primary_key=True),
    Column("name", String(30), nullable=False),
)

# 웹 대시보드 프로필 사진 (160x160 JPEG, 장당 10KB 안팎)
avatars = Table(
    "avatars", meta,
    Column("room_id", String(128), primary_key=True),
    Column("name", String(30), primary_key=True),
    Column("image", LargeBinary, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

meta.create_all(engine)

KST = timezone(timedelta(hours=9))
