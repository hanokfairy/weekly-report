# 주간보고 자동화 프로그램 사용 가이드

코드를 몰라도 이 문서만 따라 하면 프로그램을 설정하고, 병원을 추가하고, 매주 자동으로 Slack에 보고서가 오도록 만들 수 있습니다.

## 이 프로그램이 하는 일

매주 다음 데이터를 모아 마크다운 보고서를 만들고 Slack 채널로 자동 전송합니다.

- 구글 애널리틱스(GA4) 웹사이트 유입 통계 (+ 전주 대비 증감률)
- 네이버 검색에서 우리 블로그가 몇 위에 노출되는지
- 블로그에 지난주 새로 올라온 글 목록
- 유입이 크게 변동했을 때 관련 있을 만한 최근 의료 이슈 뉴스 자동 검색
- 담당자가 직접 입력하는 수치(카페 침투, 영수증 리뷰, 스마트플레이스 방문/예약 등)

## 준비물 체크리스트

- [ ] 네이버 오픈API 애플리케이션 (Client ID / Client Secret)
- [ ] 구글 클라우드 GA4 서비스 계정 JSON 키 파일
- [ ] Slack Incoming Webhook URL
- [ ] (자동화하려면) GitHub 계정 및 저장소

## 폴더 구조

| 경로 | 설명 |
|---|---|
| `.env` | API 키 등 비밀 값을 넣는 파일 (직접 만들어야 함, 깃허브에 절대 올리면 안 됨) |
| `config/clients.json` | 관리하는 병원(클라이언트) 목록과 설정 |
| `config/manual_status.json` | 자동 수집이 안 되는 수치를 매주 손으로 입력하는 파일 |
| `config/ga4-service-account.json` | 구글에서 받은 GA4 인증 키 파일 (직접 이 이름으로 저장) |
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

## 3단계. Slack 자동 전송 설정

1. https://api.slack.com/apps 접속 → "Create New App" → "From scratch"
2. 앱 이름 입력, 보고서를 보낼 워크스페이스 선택 → "Create App"
3. 좌측 메뉴 "Incoming Webhooks" 클릭 → 우측 상단 토글을 켜서 활성화
4. 페이지 하단 "Add New Webhook to Workspace" 클릭
5. 보고서를 받을 채널을 선택하고 "허용" 클릭
6. 생성된 Webhook URL 복사 (`https://hooks.slack.com/services/...` 형태)
7. `.env` 파일에 추가:

```
SLACK_WEBHOOK_URL=여기에_복사한_URL_붙여넣기
```

지금까지 `.env` 파일은 아래 4줄이 채워진 상태여야 합니다.

```
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
GA4_CREDENTIALS_PATH=./config/ga4-service-account.json
SLACK_WEBHOOK_URL=...
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
  "slack": { "webhook_env": "SLACK_WEBHOOK_URL", "channel_name": "#채널이름" }
}
```

- `property_id`: GA4 관리 화면 → "속성 설정"에서 확인
- `target_blog_id`: 네이버 블로그 주소 `blog.naver.com/이부분`
- `alert_threshold_pct`: 전주 대비 유입이 이 %만큼 변하면 관련 뉴스를 자동 검색 (기본 15)
- `news_keywords`: 유입 급변 시 검색할 진료과/이슈 키워드 (비워두면 `naver_rank.keywords`의 앞 3개를 자동 사용)

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
- `reports/오늘날짜.md` 파일이 생성됨
- 설정한 Slack 채널로 메시지가 자동 전송됨

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
| `SLACK_WEBHOOK_URL` | 3단계에서 만든 Slack Webhook URL |
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

## 문제 해결 (자주 겪는 문제)

| 증상 | 확인할 것 |
|---|---|
| Slack 메시지가 안 옴 | `SLACK_WEBHOOK_URL` 값이 정확한지, Webhook이 원하는 채널에 연결됐는지 |
| GA4 수치가 전부 0 | 서비스 계정 이메일이 GA4 속성에 "뷰어" 권한으로 추가됐는지, `property_id`가 숫자만 있는지 |
| 네이버 순위가 전부 "순위권 밖" | `target_blog_id` 값이 `blog.naver.com/` 뒤의 아이디와 정확히 일치하는지 |
| GitHub Actions 실행이 빨간색(실패) | Actions 탭에서 해당 실행 클릭 → 로그 확인 (대부분 Secret 이름 오타나 값 누락이 원인) |
| 로컬 실행 시 "환경 변수 ... 설정되지 않았습니다" 오류 | `.env` 파일이 프로젝트 최상위 폴더에 있는지, 이름에 오타가 없는지 확인 |
| 터미널에서 "command not found: python" 또는 "command not found: pip" | Python이 설치 안 된 것. 5단계의 Python 설치 안내를 따라 설치 후, `python`/`pip` 대신 `python3`/`pip3` 사용 |
