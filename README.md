# 주간보고 자동화 프로그램 사용 가이드

코드를 몰라도 이 문서만 따라 하면 프로그램을 설정하고, 병원을 추가하고, 매주 자동으로 Slack에 보고서가 오도록 만들 수 있습니다.

## 이 프로그램이 하는 일

매주 다음 데이터를 모아 병원별 보고서를 만들고, 각 병원의 Slack 채널로 `[병원명_날짜 주간보고]` 제목의 `.txt` 파일을 첨부해 자동 전송합니다.

- 구글 애널리틱스(GA4) 웹사이트 유입 통계 (+ 전주 대비 증감률)
- 네이버 검색에서 우리 블로그가 몇 위에 노출되는지
- 블로그에 지난주 새로 올라온 글 목록
- 유입이 크게 변동했을 때 관련 있을 만한 최근 의료 이슈 뉴스 자동 검색
- 스마트플레이스 방문/예약 수치 자동 수집(사무실 컴퓨터에서, 7단계 참고) — 실패 시 수동 입력값 사용
- 담당자가 직접 입력하는 수치(카페 침투, 영수증 리뷰 등)
- 코드를 몰라도 쓸 수 있는 사무실 내부 관리자 웹페이지(8단계 참고): 클라이언트 추가/실적 수정/지난 보고서 확인/즉시 실행

## 준비물 체크리스트

- [ ] 네이버 오픈API 애플리케이션 (Client ID / Client Secret)
- [ ] 구글 클라우드 GA4 서비스 계정 JSON 키 파일
- [ ] Slack 봇 토큰 (파일 첨부 전송을 위해 Incoming Webhook 대신 Bot Token 사용)
- [ ] (자동화하려면) GitHub 계정 및 저장소
- [ ] (스마트플레이스 자동 수집을 쓰려면) 병원별 네이버 로그인 정보

## 폴더 구조

| 경로 | 설명 |
|---|---|
| `.env` | API 키 등 비밀 값을 넣는 파일 (직접 만들어야 함, 깃허브에 절대 올리면 안 됨) |
| `config/clients.json` | 관리하는 병원(클라이언트) 목록과 설정 |
| `config/manual_status.json` | 자동 수집이 안 되는 수치를 매주 손으로 입력하는 파일 |
| `config/ga4-service-account.json` | 구글에서 받은 GA4 인증 키 파일 (직접 이 이름으로 저장) |
| `config/smart_place_credentials.json` | 병원별 네이버 로그인 정보 (7단계, 로컬 전용) |
| `admin/` | 사무실 내부용 관리자 웹페이지 (8단계) |
| `reports/` | 매주 생성되는 보고서(.md)가 쌓이는 폴더 |

---

## 1단계. 네이버 API 키 발급 및 설정

1. https://developers.naver.com/apps/#/register 접속 후 로그인
2. "애플리케이션 등록" 클릭 → 이름은 아무거나 입력
3. "사용 API"에서 **검색** 을 체크 (블로그 검색, 뉴스 검색에 사용됩니다)
4. 등록 완료 후 화면에 표시되는 **Client ID**, **Client Secret** 값을 복사
5. 프로젝트 최상위 폴더에 `.env` 파일을 새로 만들고 아래처럼 입력 (파일명 앞에 점(`.`) 포함, 확장자 없음):

```
NAVER_CLIENT_ID=여기에_Client_ID_붙여넣기
NAVER_CLIENT_SECRET=여기에_Client_Secret_붙여넣기
```

## 2단계. 구글 GA4 서비스 계정 JSON 발급 및 설정

1. https://console.cloud.google.com 접속, 로그인
2. 상단에서 새 프로젝트 생성 (또는 기존 프로젝트 선택)
3. 좌측 메뉴 "API 및 서비스 > 라이브러리"에서 **Google Analytics Data API** 검색 후 "사용 설정" 클릭
4. "API 및 서비스 > 사용자 인증 정보" → "사용자 인증 정보 만들기" → **서비스 계정** 선택 → 이름 입력 후 생성
5. 생성된 서비스 계정 클릭 → "키" 탭 → "키 추가" → "새 키 만들기" → **JSON** 선택 → 자동으로 파일이 다운로드됨
6. 다운로드된 파일 이름을 바꿔서 정확히 이 위치에 저장: `config/ga4-service-account.json`
7. **중요**: JSON 파일을 텍스트 에디터로 열어보면 `"client_email": "xxxx@xxxx.iam.gserviceaccount.com"` 값이 있습니다. 이 이메일 주소를 **GA4에도 등록**해야 데이터를 가져올 수 있습니다.
   - Google Analytics 접속 → 관리(톱니바퀴) → 해당 속성의 "속성 액세스 관리" → "+" → 위 이메일 주소를 **뷰어** 권한으로 추가
8. `.env` 파일에 아래 줄 추가 (경로가 6번과 일치해야 함):

```
GA4_CREDENTIALS_PATH=./config/ga4-service-account.json
```

## 3단계. Slack 자동 전송 설정 (봇 토큰 + 파일 첨부)

보고서를 `.txt` 파일로 첨부해서 보내려면 Incoming Webhook이 아니라 **Slack 봇(Bot Token)** 방식을 써야 합니다.

1. https://api.slack.com/apps 접속 → "Create New App" → "From scratch"
2. 앱 이름 입력(예: `주간보고봇`), 보고서를 보낼 워크스페이스 선택 → "Create App"
3. 좌측 메뉴 "OAuth & Permissions" 클릭
4. 페이지 중간 **"Scopes" > "Bot Token Scopes"** 에서 "Add an OAuth Scope" 클릭 → 아래 2개 추가:
   - `files:write` (파일 업로드용)
   - `chat:write` (채널에 메시지/파일 전송용)
5. 같은 페이지 맨 위로 스크롤 → **"Install to Workspace"** 클릭 → 권한 허용
6. 설치 완료 후 이 페이지 상단에 나오는 **"Bot User OAuth Token"** (`xoxb-`로 시작) 복사
7. `.env` 파일에 추가:

```
SLACK_BOT_TOKEN=여기에_복사한_xoxb-토큰_붙여넣기
```

8. 보고서를 받을 Slack 채널에 이 봇을 초대해야 합니다: 해당 채널에서 채팅창에 `/invite @주간보고봇` 입력 (3번에서 지은 앱 이름) → 봇이 채널 멤버로 추가됨
9. 그 채널의 **채널 ID**를 확인합니다: 채널 이름 클릭 → 맨 아래로 스크롤하면 "채널 ID" 표시(`C`로 시작하는 문자열), 또는 채널 우클릭 → "링크 복사" 했을 때 URL 맨 끝부분이 채널 ID입니다.
10. 확인한 채널 ID를 `config/clients.json`의 해당 병원 `slack.channel_id` 값에 넣습니다 (4단계 참고).

지금까지 `.env` 파일은 아래 4줄이 채워진 상태여야 합니다.

```
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
GA4_CREDENTIALS_PATH=./config/ga4-service-account.json
SLACK_BOT_TOKEN=xoxb-...
```

## 4단계. 클라이언트(병원) 추가하기

`config/clients.json` 파일을 열어서 `"clients"` 배열 안에 아래 블록을 통째로 복사해 추가하고, 값만 병원에 맞게 바꿉니다. **기존 항목 뒤에 콤마(`,`)를 꼭 붙여야** 문법 오류가 나지 않습니다.

```json
{
  "id": "새병원_영문고유아이디",
  "name": "새병원 표시 이름",
  "ga4": {
    "property_id": "GA4 속성 ID (숫자만)"
  },
  "naver_rank": {
    "keywords": ["체크하고 싶은 검색 키워드1", "키워드2"],
    "target_blog_id": "네이버 블로그 아이디",
    "max_rank": 30
  },
  "blogs": [
    { "name": "메인 블로그", "rss_url": "https://rss.blog.naver.com/블로그아이디.xml" }
  ],
  "alert_threshold_pct": 15,
  "news_keywords": ["진료과목 키워드1", "진료과목 키워드2"],
  "slack": { "channel_id": "채널ID(C로 시작)", "channel_name": "#채널이름" }
}
```

- `property_id`: GA4 관리 화면 → "속성 설정"에서 확인
- `target_blog_id`: 네이버 블로그 주소 `blog.naver.com/이부분`
- `alert_threshold_pct`: 전주 대비 유입이 이 %만큼 변하면 관련 뉴스를 자동 검색 (기본 15)
- `news_keywords`: 유입 급변 시 검색할 진료과/이슈 키워드 (비워두면 `naver_rank.keywords`의 앞 3개를 자동 사용)
- `slack.channel_id`: 3단계 8~9번에서 확인한 채널 ID (실제로 전송에 사용되는 값). `channel_name`은 사람이 보기 위한 메모일 뿐 프로그램에서 사용하지 않습니다.

각 병원마다 Slack으로 `[병원명_날짜 주간보고]` 라는 제목의 `.txt` 파일이 개별 전송됩니다.

병원을 여러 개 등록하면 프로그램 실행 한 번으로 전부 처리되어 하나의 보고서로 합쳐집니다.

**추가로 `config/manual_status.json`에도 같은 `id`로 항목을 넣어야** "채널별 진행 현황", "스마트플레이스 통계" 섹션이 채워집니다 (자동 수집이 불가능한 값이라 매주 사람이 직접 입력).

## 5단계. 로컬 컴퓨터에서 실행해보기

### Python이 설치되어 있지 않다면 먼저 설치

터미널에 `python3 --version`을 입력했을 때 "command not found"가 뜨면 Python이 없는 것입니다.

1. https://www.python.org/downloads/macos/ 접속 → "Download Python 3.x.x" 클릭해 `.pkg` 다운로드
2. 다운로드한 파일 더블클릭 → "계속"만 눌러서 설치
3. **터미널 앱을 완전히 껐다가 다시 켜기**
4. `python3 --version` 입력해서 버전이 뜨는지 확인

### 실행하기

터미널(맥은 "터미널" 앱, 윈도우는 "명령 프롬프트"/PowerShell)을 열고:

```
cd 프로젝트가_있는_폴더경로
pip3 install -r requirements.txt
python3 main.py
```

> macOS는 `python`/`pip`가 아니라 **`python3`/`pip3`** 명령어를 씁니다.

정상적으로 끝나면:
- `reports/오늘날짜.md` 파일이 생성됨 (전체 병원 통합본, 로컬 기록용)
- 병원별로 설정한 Slack 채널에 `[병원명_날짜 주간보고]` 제목의 `.txt` 파일이 첨부되어 전송됨

---

## 6단계. GitHub Actions로 매주 자동 실행하기

사람이 매번 `python main.py`를 실행하지 않아도, GitHub이 매주 월요일 아침에 대신 실행해주도록 설정할 수 있습니다. 워크플로 파일(`.github/workflows/weekly-report.yml`)은 이미 만들어져 있으니, 아래 절차만 따라 하면 됩니다.

### 6-1. 이 폴더를 GitHub 저장소로 만들기

터미널에서 프로젝트 폴더 안에 들어가 실행:

```
git init
git add .
git commit -m "init"
```

이후 GitHub 웹사이트(https://github.com/new)에서 새 저장소를 만들고, 그 페이지에 안내되는 명령어(`git remote add origin ...`, `git push -u origin main` 등)를 그대로 복사해서 실행하면 코드가 업로드됩니다.

> `.env`와 `config/ga4-service-account.json`은 `.gitignore`에 이미 등록되어 있어 실수로 깃허브에 올라가지 않습니다. (비밀번호/키가 담긴 파일이므로 매우 중요합니다.)

### 6-2. GitHub 저장소에 비밀 값(Secrets) 등록하기

저장소 페이지 → **Settings** → 좌측 **Secrets and variables** → **Actions** → **New repository secret** 을 눌러 아래 4개를 하나씩 등록합니다.

| Secret 이름 | 값 |
|---|---|
| `NAVER_CLIENT_ID` | 1단계에서 발급받은 네이버 Client ID |
| `NAVER_CLIENT_SECRET` | 1단계에서 발급받은 네이버 Client Secret |
| `SLACK_BOT_TOKEN` | 3단계에서 발급받은 `xoxb-`로 시작하는 Slack Bot Token |
| `GA4_SERVICE_ACCOUNT_JSON` | 2단계에서 다운로드한 JSON 파일을 **텍스트 에디터로 열어 전체 내용을 그대로 복사**해서 붙여넣기 |

`.env` 파일이나 로컬 JSON 파일은 GitHub에 올라가지 않으므로, 이 4개의 Secret이 그 역할을 대신합니다.

### 6-3. 자동 실행 확인하기

- 아무 설정 없이 두면 **매주 월요일 오전 9시(한국시간)** 에 자동 실행됩니다.
- 지금 바로 테스트하고 싶다면: 저장소의 **Actions** 탭 → 좌측 "Weekly Report" 클릭 → 우측 "Run workflow" 버튼 클릭 → 즉시 실행됩니다.
- 실행이 끝나면 `reports/` 폴더에 그날 날짜의 보고서 파일이 자동으로 커밋되어 저장소에 기록으로 남고, 동시에 Slack으로도 전송됩니다.
- 실행 결과(성공/실패)는 Actions 탭에서 확인할 수 있습니다. 실패하면 로그를 눌러 어떤 단계에서 멈췄는지 볼 수 있습니다.

### 6-4. 중요: 매주 손으로 입력하는 값은 자동화 이후에도 사람이 갱신해야 함

GitHub Actions는 **그 시점에 저장소에 저장돼 있는** `config/manual_status.json` 값을 그대로 사용합니다. 즉, 자동화를 걸어도 다음 작업은 계속 사람이 해야 합니다.

1. 매주 자동 실행 전(예: 월요일 오전 8시까지), GitHub 웹사이트에서 저장소 → `config/manual_status.json` 파일 열기
2. 우측 상단 연필(✏️) 아이콘 클릭 → 그 주 실적 값으로 수정
3. 하단 "Commit changes" 클릭 (코드를 몰라도 됨, 숫자만 바꾸면 됨)

이 과정을 건너뛰면 지난주 값 그대로 보고서에 들어가니 주의하세요.

---

## 7단계. 스마트플레이스 자동 수집 설정 (사무실 컴퓨터에서 실행)

스마트플레이스(네이버 플레이스 센터)는 공식 공개 API가 없어서, **병원별 네이버 계정으로 로그인해 화면의 수치를 읽어오는 방식**으로 자동화합니다. 네이버가 클라우드(GitHub Actions)에서의 로그인을 "새로운 환경"으로 인식해 자꾸 인증을 요구할 수 있어서, 이 기능은 **사무실 컴퓨터(이 저장소가 있는 Mac)에서만** 실행합니다.

### 7-1. 설치

```
pip3 install -r requirements.txt -r requirements-local.txt
playwright install chromium
```

### 7-2. 병원별 네이버 로그인 정보 입력

1. `config/smart_place_credentials.example.json`을 복사해서 `config/smart_place_credentials.json`으로 저장 (이 파일은 `.gitignore`에 등록되어 있어 GitHub에는 절대 올라가지 않습니다)
2. 병원마다 네이버 로그인 아이디/비밀번호, 그리고 **스마트플레이스 통계(방문/예약) 페이지 URL**을 채웁니다.
   - URL 확인법: 브라우저에서 https://new.smartplace.naver.com 로그인 → 해당 병원 플레이스 선택 → 방문자/예약 수치가 보이는 통계 화면으로 이동 → 그때 주소창의 URL을 그대로 복사

### 7-3. 최초 1회 수동 로그인

네이버는 낯선 환경에서 로그인하면 휴대폰 인증 등을 요구할 수 있어서, 병원마다 **최초 1회는 사람이 직접** 인증을 통과시켜야 합니다.

```
python3 scrape_smart_place.py --interactive
```

브라우저 창이 뜨면 인증을 완료하세요. 한 번 통과하면 `config/.smart_place_sessions/` 폴더에 로그인 상태가 저장되어, 이후에는 사람 개입 없이 자동으로 동작합니다.

### 7-4. 매주 자동 실행되도록 예약 (launchd)

GitHub Actions가 매주 월요일 09:00(KST)에 보고서를 보내므로, 그 전인 **월요일 07:30**에 스마트플레이스 수치를 먼저 수집해 GitHub에 반영해두면 됩니다.

`~/Library/LaunchAgents/com.weeklyreport.smartplace.plist` 파일을 아래 내용으로 만들고(경로의 `/Users/designer/weekly-report`는 실제 프로젝트 경로로 맞춰주세요):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.weeklyreport.smartplace</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/Users/designer/weekly-report/scrape_smart_place.py</string>
  </array>
  <key>WorkingDirectory</key><string>/Users/designer/weekly-report</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>1</integer>
    <key>Hour</key><integer>7</integer>
    <key>Minute</key><integer>30</integer>
  </dict>
  <key>StandardOutPath</key><string>/tmp/smartplace.log</string>
  <key>StandardErrorPath</key><string>/tmp/smartplace.log</string>
</dict>
</plist>
```

등록:

```
launchctl load ~/Library/LaunchAgents/com.weeklyreport.smartplace.plist
```

**중요한 한계**: 이건 네이버가 공식 지원하는 기능이 아니라 화면을 읽어오는 방식이라, 네이버가 화면 구성을 바꾸면 동작이 멈출 수 있고, 보안 정책상 세션이 만료되어 다시 `--interactive`로 로그인해야 할 수도 있습니다. 자동 수집이 실패해도 기존 수치는 그대로 유지되며, 실패 시 해당 병원 Slack 채널로 "자동 수집 실패, 수동 확인 필요" 알림이 전송됩니다.

---

## 8단계. 관리자 페이지 (사무실 내부 전용)

코드를 몰라도 브라우저에서 클라이언트 추가/실적 수정/지난 보고서 확인/즉시 실행을 할 수 있는 페이지입니다. **사무실 내부망에서만** 접속 가능하도록 만들어져 있고 (인터넷에 노출 X), 로그인한 사람은 전체 클라이언트를 동일한 권한으로 관리합니다.

### 8-1. 사용자 계정 만들기

1. 터미널에서 비밀번호 해시 생성:
   ```
   python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('원하는비밀번호'))"
   ```
2. `admin/users.example.json`을 복사해서 `admin/users.json`으로 저장 (역시 `.gitignore` 처리되어 GitHub에 올라가지 않음)
3. 아래처럼 사용자 이름과 방금 생성한 해시값을 넣습니다 (여러 명 추가 가능):
   ```json
   { "혜진": "위에서 생성된 긴 해시값", "민수": "또 다른 해시값" }
   ```

### 8-2. 실행

```
python3 admin/app.py
```

같은 컴퓨터에서는 `http://localhost:5000`으로 접속합니다. 사무실의 다른 컴퓨터에서 접속하려면:

1. 이 Mac의 LAN IP 확인: 시스템 설정 → Wi-Fi/네트워크 → IP 주소 확인 (예: `192.168.0.15`)
2. 다른 컴퓨터 브라우저에서 `http://192.168.0.15:5000` 접속

### 8-3. Mac 부팅 시 자동 실행 (선택)

7-4와 같은 방식으로 `launchd` 등록 시 `KeepAlive`를 `true`로 설정하면, Mac이 켜져 있는 동안 관리자 페이지가 항상 떠 있게 만들 수 있습니다. 필요하시면 요청해주시면 plist 파일까지 만들어드릴게요.

### 8-4. 페이지에서 할 수 있는 것

- **대시보드**: 클라이언트별 최신 스마트플레이스 수치 확인, "지금 실행" 버튼으로 즉시 보고서 생성 + Slack 전송
- **설정 수정**: `clients.json`을 직접 열지 않고 폼으로 GA4/네이버/블로그/Slack 설정 추가·수정
- **실적 수치 편집**: `manual_status.json`의 채널 진행 현황/스마트플레이스 수치를 폼으로 편집
- **지난 보고서 보기**: `reports/` 폴더의 과거 보고서를 클라이언트별로 모아서 확인

페이지에서 저장 버튼을 누르면 자동으로 `git commit + push`까지 되어, 다음 GitHub Actions 실행(매주 월요일 09:00)에 바로 반영됩니다.

---

## 문제 해결 (자주 겪는 문제)

| 증상 | 확인할 것 |
|---|---|
| Slack 메시지/파일이 안 옴 | `SLACK_BOT_TOKEN`이 정확한지, 봇이 해당 채널에 초대(`/invite @봇이름`)되어 있는지, `clients.json`의 `channel_id`가 맞는지 |
| Slack 전송 시 `not_in_channel` 오류 | 봇이 채널 멤버가 아닌 것. 채널에서 `/invite @봇이름` 실행 |
| Slack 전송 시 `missing_scope` 오류 | Slack App의 "OAuth & Permissions"에서 `files:write`, `chat:write` 스코프가 추가·설치됐는지 확인 |
| GA4 수치가 전부 0 | 서비스 계정 이메일이 GA4 속성에 "뷰어" 권한으로 추가됐는지, `property_id`가 숫자만 있는지 |
| 네이버 순위가 전부 "순위권 밖" | `target_blog_id` 값이 `blog.naver.com/` 뒤의 아이디와 정확히 일치하는지 |
| GitHub Actions 실행이 빨간색(실패) | Actions 탭에서 해당 실행 클릭 → 로그 확인 (대부분 Secret 이름 오타나 값 누락이 원인) |
| `scrape_smart_place.py` 실행 시 `SmartPlaceLoginRequired` 오류 | 세션이 만료된 것. `python3 scrape_smart_place.py --interactive`로 다시 로그인 |
| `scrape_smart_place.py`가 방문자 수를 못 찾음 | 네이버가 스마트플레이스 화면 구성을 바꾼 것. `src/smart_place_scraper.py`의 라벨 문자열(`VISITS_LABEL` 등) 확인 필요 |
| 관리자 페이지 접속이 안 됨 (다른 컴퓨터에서) | Mac의 방화벽 설정, 같은 Wi-Fi/네트워크에 연결되어 있는지, LAN IP가 맞는지 확인 |
| 관리자 페이지에서 저장 시 git 관련 오류 | 스마트플레이스 스크립트나 GitHub Actions가 동시에 push 중일 수 있음. 잠시 후 다시 저장 시도 |
| 로컬 실행 시 "환경 변수 ... 설정되지 않았습니다" 오류 | `.env` 파일이 프로젝트 최상위 폴더에 있는지, 이름에 오타가 없는지 확인 |
| 터미널에서 "command not found: python" 또는 "command not found: pip" | Python이 설치 안 된 것. 5단계의 Python 설치 안내를 따라 설치 후, `python`/`pip` 대신 `python3`/`pip3` 사용 |
