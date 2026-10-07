# 카톡 지출봇 (카카오 i 오픈빌더 + FastAPI)

## 명령어
| 입력 | 동작 |
|---|---|
| `!지출 8900원 음식 햄버거` | 금액 / 카테고리 / 메모 저장 (`8,900원`, `8900` 모두 OK, 카테고리 생략 시 "기타") |
| `!순위` / `!순위 전체` | 이 방의 이번 달 / 누적 지출 TOP 3 |
| `!통계` / `!통계 전체` | 내 카테고리별 금액·비율·건수 |
| `!닉네임 효진` | 순위·통계에 보일 이름 등록 |
| `!취소` | 내 마지막 기록 삭제 |

> **왜 닉네임 명령이 있나?** 오픈빌더는 개인정보 보호 때문에 카톡 닉네임을 넘겨주지 않고 익명 ID(botUserKey)만 줍니다. 등록 안 한 사람은 `익명xxxx`로 표시돼요.

## 1. 로컬 실행
```bash
pip install -r requirements.txt
python test_bot.py            # 테스트
uvicorn main:app --port 8000  # 서버 실행 → POST /skill
```

> 👉 **무료 배포 전체 과정은 [DEPLOY.md](DEPLOY.md)에 단계별로 정리돼 있어요.** 아래는 요약입니다.

## 2. DB 준비 (무료 Postgres)
Supabase 또는 Neon에서 프로젝트를 만들고 연결 문자열을 복사 →
`DATABASE_URL=postgresql://user:pw@host:5432/db` 환경변수로 설정. 테이블은 서버 시작 시 자동 생성.
(환경변수가 없으면 SQLite 파일을 쓰는데, 무료 호스팅은 재시작 시 파일이 날아가니 배포 땐 Postgres 권장)

## 3. 서버 배포 (예: Render)
1. 이 폴더를 GitHub에 올림
2. Render → New Web Service → 저장소 선택
3. Build: `pip install -r requirements.txt` / Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Environment에 `DATABASE_URL` 추가 → 배포 후 `https://xxx.onrender.com/skill` 주소 확보

⚠️ 오픈빌더는 스킬 응답을 **5초** 안에 받아야 합니다. Render 무료 플랜은 15분 미사용 시 잠들어서 첫 요청이 느릴 수 있어요 → 유료 플랜, Railway/Fly.io, 또는 주기적 핑(UptimeRobot)으로 해결.

## 4. 카카오 설정
1. **카카오톡 채널** 개설: center-pf.kakao.com
2. **오픈빌더** (chatbot.kakao.com)에서 봇 생성 → 채널 연결
3. **스킬** 메뉴 → 스킬 생성 → URL에 `https://.../skill` 입력
4. **시나리오 → 폴백 블록**에서 "스킬데이터 사용" 선택 후 위 스킬 연결
   (모든 `!` 명령이 폴백으로 들어와 서버에서 분기하므로 블록을 여러 개 만들 필요 없음)
5. 배포 → 1:1 채팅으로 먼저 테스트
6. **그룹채팅 사용 설정**: 봇 설정에서 그룹채팅 기능을 켜고 단톡방에 봇(채널)을 초대.
   이 기능은 승인/조건이 필요할 수 있으니 오픈빌더 공식 문서·공지에서 최신 조건을 확인하세요.
   그룹채팅 요청에는 방 식별자(`userRequest.chat` / `botGroupKey`)가 오고, 코드가 이를 방 ID로 씁니다.
   1:1 대화에서는 `dm:<유저>` 방으로 따로 집계돼요.

## 구조
- `expenses(room_id, user_id, amount, category, memo, created_at)`
- `nicknames(room_id, user_id, name)`
- 순위·통계는 방(room_id) 단위로 분리 집계, 월 기준은 한국시간(KST)
