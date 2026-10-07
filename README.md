# 거지방

친구들끼리 쓰는 지출 기록 웹 대시보드 (FastAPI + Postgres).
링크를 단톡방에 공유하면 각자 폰 브라우저에서 바로 사용합니다.

## 기능
- **잠금**: 셋이 공유하는 방 비밀번호 하나 (서버 환경변수 `ROOM_PASSWORD`)
- **이름 선택**: 가입 없이 이름만 고르면 그 폰에서 기억
- **지출 추가**: 금액 + 카테고리(음식·카페·교통·쇼핑·술·생활·기타·직접 입력) + 메모
- **순위**: 이 달 지출 많은 순 (TOP 3 메달, 막대에 마우스/터치하면 건수·비율)
- **내 카테고리 통계**: 카테고리별 금액·비율·건수
- **최근 기록**: 30건, "내 것만" 필터, 내 기록만 삭제 가능
- **월 이동**: ‹ › 로 지난 달 보기

## 파일
| 파일 | 역할 |
|---|---|
| `main.py` | 앱 시작점 (+ 카카오 오픈빌더 스킬 `/skill`, 지금은 미사용) |
| `web.py` | 대시보드 화면 `/` 과 API `/api/*` |
| `index.html` | 대시보드 화면 (HTML/CSS/JS 한 파일) |
| `db.py` | DB 연결·테이블 |
| `test_web.py`, `test_bot.py` | 테스트 |

## 로컬 실행
```bash
pip install -r requirements.txt
python test_web.py
ROOM_PASSWORD=1234 uvicorn main:app --port 8000   # http://localhost:8000
```

## 배포 (Render + Neon + UptimeRobot)
[DEPLOY.md](DEPLOY.md)의 STEP 1~4 그대로. 환경변수에 아래를 넣으면 됩니다.

| Key | Value |
|---|---|
| `DATABASE_URL` | Neon 접속 주소 |
| `ROOM_PASSWORD` | 친구들과 공유할 방 비밀번호 |
| `PYTHON_VERSION` | `3.12.6` |

UptimeRobot 모니터 주소는 `https://<서비스>.onrender.com/health` 또는 `/` 둘 다 OK.
(DEPLOY.md의 STEP 5~7 카카오 설정은 그룹채팅 봇 제휴 조건 때문에 사용하지 않습니다.)
