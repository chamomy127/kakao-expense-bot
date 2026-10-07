# 무료 배포 가이드: Render(서버) + Neon(DB) + UptimeRobot(잠 깨우기)

전체 흐름
```
카톡 단톡방 → 카카오 오픈빌더 → Render의 main.py (/skill) → Neon Postgres
                                      ↑ 10분마다 깨움: UptimeRobot
```
소요 시간: 30분~1시간 · 비용: 0원 · 필요한 계정: GitHub, Neon, Render, UptimeRobot, 카카오

> 무료 플랜 조건은 바뀔 수 있으니 가입할 때 각 서비스의 요금제 페이지를 한 번 확인하세요.

---

## STEP 1. 코드를 GitHub에 올리기
1. github.com 로그인 → 오른쪽 위 **+ → New repository**
2. 이름: `kakao-expense-bot`, **Private** 선택 → Create
3. 생성된 페이지에서 **uploading an existing file** 클릭
4. 이 폴더의 파일을 드래그해서 올림: `main.py`, `requirements.txt`, `test_bot.py`, `README.md`, `DEPLOY.md`, `.gitignore`
   (`.gitignore`는 숨김 파일이라 안 보이면 생략해도 됨)
5. **Commit changes**

## STEP 2. Neon에서 DB 만들기
1. neon.tech → **Sign up** (GitHub 계정으로 가입하면 편함)
2. **Create project**
   - Project name: `kakao-expense-bot`
   - Postgres version: 기본값
   - Region: **AWS Asia Pacific (Singapore)** 등 한국과 가까운 곳
3. 생성되면 대시보드의 **Connect** 버튼 → Connection string 복사
   ```
   postgresql://neondb_owner:비밀번호@ep-xxxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   ```
   - "Pooled connection" 옵션이 있으면 켜진 주소(호스트에 `-pooler` 포함)를 쓰는 걸 추천
4. 이 주소는 **비밀번호가 들어있으니** 메모장에만 잠깐 두고 어디에도 공유하지 마세요.

테이블은 서버가 처음 켜질 때 자동으로 생성됩니다. 따로 할 건 없어요.

## STEP 3. Render에 서버 올리기
1. render.com → GitHub로 가입 → **New + → Web Service**
2. **Build and deploy from a Git repository** → GitHub 연결 → `kakao-expense-bot` 선택
3. 설정값
   | 항목 | 값 |
   |---|---|
   | Name | `kakao-expense-bot` (주소가 됨) |
   | Region | **Singapore** (Neon과 같은 지역) |
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
   | Instance Type | **Free** |
4. **Environment Variables** (Advanced 안에 있을 수 있음)
   | Key | Value |
   |---|---|
   | `DATABASE_URL` | STEP 2에서 복사한 주소 |
   | `PYTHON_VERSION` | `3.12.6` |
5. **Create Web Service** → 로그에 `Application startup complete` 뜨면 성공
6. 왼쪽 위에 보이는 주소 확인: `https://kakao-expense-bot-xxxx.onrender.com`
   - 브라우저로 열어서 `{"ok":true}` 나오면 정상
   - **스킬 URL은 이 주소 + `/skill`** 입니다

## STEP 4. UptimeRobot으로 잠 안 들게 하기
Render 무료 서버는 15분간 요청이 없으면 잠들고, 깨어나는 데 수십 초가 걸려서 카톡 5초 제한에 걸립니다.
1. uptimerobot.com 가입 → **+ New monitor**
2. Monitor Type: **HTTP(s)**
3. URL: `https://kakao-expense-bot-xxxx.onrender.com/` (끝에 `/skill` 아님!)
4. Monitoring Interval: **5분** (무료 최소값)
5. **Create Monitor** → 상태가 초록색 Up이면 완료

> Render 무료 플랜은 한 달 사용 시간 한도가 있는데(대략 750시간), 서버 1개를 24시간 돌리는 정도는 들어갑니다. 다른 무료 서비스를 같이 돌리면 한도를 나눠 쓰니 주의.

## STEP 5. 카카오 채널 + 오픈빌더 연결
1. **채널 만들기**: center-pf.kakao.com → 새 채널 만들기 (이름 예: 우리방 지출봇) → 채널 **공개** 설정
2. **봇 만들기**: chatbot.kakao.com → **+ 봇 만들기 → 카카오톡 챗봇**
3. 봇 설정 → **카카오톡 채널 연결**에서 방금 만든 채널 선택
4. 왼쪽 **스킬 → 생성**
   - 이름: `지출봇`
   - URL: `https://kakao-expense-bot-xxxx.onrender.com/skill`
   - **기본 스킬로 설정** 체크 → 저장
   - 같은 화면 **스킬 서버로 전송** 테스트 → 응답에 `version: 2.0`이 오면 연결 OK
5. **시나리오 → 기본 시나리오 → 폴백 블록**
   - 파라미터 설정에서 스킬: `지출봇` 선택
   - 봇 응답: **스킬데이터 사용** 선택 → 저장
6. 왼쪽 **배포 → 배포** 클릭

## STEP 6. 테스트
1. 카톡에서 채널 검색 → 채널 추가 → 1:1 채팅
2. `!도움말` → 사용법 나오면 성공
3. `!닉네임 효진`, `!지출 8900원 음식 햄버거`, `!순위`, `!통계` 순서로 확인

## STEP 7. 단톡방에 넣기
1. 오픈빌더 봇 설정에서 **그룹채팅** 관련 메뉴를 찾아 활성화
   (계정·채널 조건이나 신청/승인이 필요할 수 있음. 오픈빌더 공지·도움말에서 현재 조건 확인)
2. 활성화되면 카톡 단톡방 → 메뉴 → 봇/채널 초대
3. 셋 다 `!닉네임 이름` 한 번씩 등록하면 끝

---

## 문제 해결
| 증상 | 확인할 것 |
|---|---|
| 카톡에서 아무 응답 없음/에러 말풍선 | Render 로그에 요청이 찍히는지, 스킬 URL 끝이 `/skill`인지, 배포 버튼 눌렀는지 |
| 첫 메시지만 실패 | 서버가 잠들어 있었음 → UptimeRobot 동작 확인 |
| Render 로그에 DB 연결 에러 | `DATABASE_URL` 오타, 주소 끝 `?sslmode=require` 유지 |
| 응답은 오는데 "오류가 났어요" | Render 로그의 `ERROR:` 줄 확인 |
| 데이터 직접 보고 싶음 | Neon 대시보드 → **Tables** 또는 **SQL Editor**에서 `select * from expenses;` |

## 코드 수정 후 반영
GitHub에서 파일 수정 → Commit하면 Render가 자동으로 재배포합니다(1~3분).
