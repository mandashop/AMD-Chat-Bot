# Cloudflare Workers 봇 배포 완벽 가이드

이 가이드는 GitHub 저장소에서 Cloudflare Workers로 봇을 배포하는 전체 과정을 설명합니다.

---

## 📋 준비사항

1. **GitHub 계정** (https://github.com)
2. **Cloudflare 계정** (https://dash.cloudflare.com/sign-up)
3. **Telegram Bot Token** (@BotFather에서 발급)

---

## 1단계: GitHub Secrets 설정

GitHub 저장소에 Cloudflare와 Telegram 봇 정보를 안전하게 저장합니다.

### 1.1 저장소 설정 페이지 접속
1. 브라우저에서 GitHub 저장소 열기: `https://github.com/mandashop/AMDCHAT-3.29-`
2. 상단 메뉴에서 **Settings** 클릭
3. 왼쪽 사이드바에서 **Secrets and variables** → **Actions** 클릭

### 1.2 Secrets 추가
**New repository secret** 버튼을 클릭하여 다음 3개를 추가:

#### Secret 1: CLOUDFLARE_API_TOKEN
1. Name: `CLOUDFLARE_API_TOKEN`
2. Value: (아래에서 생성)

**Cloudflare API Token 생성 방법:**
1. https://dash.cloudflare.com/profile/api-tokens 접속
2. **Create Token** 클릭
3. **Custom token** 선택
4. 설정:
   - Token name: `GitHub Actions Deploy`
   - Permissions:
     - Zone: Read (선택사항)
     - Cloudflare Workers: Edit
   - Account Resources: Include - Your Account
5. **Continue to summary** → **Create Token**
6. **토큰 복사** (한 번만 표시됨!)

#### Secret 2: CLOUDFLARE_ACCOUNT_ID
1. Name: `CLOUDFLARE_ACCOUNT_ID`
2. Value: (아래에서 확인)

**Account ID 확인 방법:**
1. https://dash.cloudflare.com 접속
2. 오른쪽 사이드바에서 **Account ID** 복사

#### Secret 3: BOT_TOKEN
1. Name: `BOT_TOKEN`
2. Value: Telegram Bot Token (@BotFather에서 받은 토큰)

---

## 2단계: Cloudflare KV Namespace 생성

봇이 데이터를 저장할 수 있는 저장소를 만듭니다.

### 2.1 KV Namespace 생성
1. https://dash.cloudflare.com 접속
2. 왼쪽 메뉴에서 **Workers & Pages** 클릭
3. 상단 **KV** 탭 클릭
4. **Create a namespace** 버튼 클릭
5. Namespace name: `AMDCHAT_KV`
6. **Add** 클릭

### 2.2 Namespace ID 복사
1. 생성된 `AMDCHAT_KV` 클릭
2. **Namespace ID** 복사 (예: `b240ff936bdd4564a367f62032599502`)

### 2.3 GitHub에서 wrangler.toml 수정
1. GitHub 저장소에서 `wrangler.toml` 파일 클릭
2. 오른쪽 상단 연필 아이콘 (Edit) 클릭
3. 다음 부분을 수정:

```toml
[[kv_namespaces]]
binding = "KV"
id = "YOUR_KV_NAMESPACE_ID"  # ← 여기에 복사한 ID 붙여넣기
```

예시:
```toml
[[kv_namespaces]]
binding = "KV"
id = "b240ff936bdd4564a367f62032599502"
```

4. 아래로 스크롤 → **Commit changes...** 클릭
5. "Update KV namespace ID" 메시지 입력 → **Commit changes**

---

## 3단계: 자동 배포 (GitHub Actions)

코드를 푸시하면 자동으로 Cloudflare에 배포됩니다.

### 3.1 배포 확인
1. GitHub 저장소에서 **Actions** 탭 클릭
2. **Deploy to Cloudflare Workers** 워크플로우 확인
3. 초록색 ✓ 표시가 나타나면 성공!

### 3.2 수동 배포 (선택사항)
1. Actions 탭 → **Deploy to Cloudflare Workers** 클릭
2. **Run workflow** 버튼 클릭
3. **Run workflow** 확인

---

## 4단계: Telegram Webhook 설정

Telegram이 Cloudflare Workers로 메시지를 별낼 수 있도록 설정합니다.

### 4.1 Workers URL 확인
1. https://dash.cloudflare.com 접속
2. **Workers & Pages** 클릭
3. **amdchat-bot** 클릭
4. 오른쪽 상단의 URL 복사 (예: `https://amdchat-bot.your-account.workers.dev`)

### 4.2 Webhook 설정
브라우저 주소창에 다음 URL 입력:

```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://amdchat-bot.your-account.workers.dev
```

예시:
```
https://api.telegram.org/bot123456789:ABCdefGHIjklMNOpqrsTUVwxyz/setWebhook?url=https://amdchat-bot.your-account.workers.dev
```

**성공 응답:**
```json
{"ok":true,"result":true,"description":"Webhook was set"}
```

### 4.3 Webhook 확인
```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
```

---

## 5단계: 봇 테스트

Telegram에서 봇을 테스트합니다.

### 5.1 그룹에 봇 추가
1. Telegram에서 그룹 채팅 열기
2. 멤버 추가 → @your_bot_username 검색
3. 봇을 관리자로 지정 (메시지 삭제 권한 필요)

### 5.2 명령어 테스트
- `/start` - 시작 메시지
- `/help` - 도움말
- `/mystats` - 내 메시지 수량
- `/rank` - 채팅 순위 Top 10
- `/attend` 또는 `ㅊㅊ`, `출첵`, `출석체크` - 출석체크
- `/attendrank` - 출석 순위 Top 10

### 5.3 중복 메시지 테스트
같은 메시지를 5번 이상 복사/붙여넣기 하면 자동으로 삭제됩니다.

---

## 🔧 문제 해결

### 배포 실패 (GitHub Actions)
1. **Actions** 탭에서 실패한 워크플로우 클릭
2. 빨간색 X 표시된 단계 클릭
3. 로그 확인하여 오류 파악

**일반적인 오류:**
- `CLOUDFLARE_API_TOKEN` 잘못됨 → 토큰 재생성
- `CLOUDFLARE_ACCOUNT_ID` 잘못됨 → Account ID 확인
- KV Namespace ID 잘못됨 → wrangler.toml 수정

### 봇이 응답하지 않음
1. **Webhook 확인:**
   ```
   https://api.telegram.org/bot<TOKEN>/getWebhookInfo
   ```
   
2. **Cloudflare Workers 로그 확인:**
   - Dashboard → Workers & Pages → amdchat-bot → Logs

3. **봇이 관리자인지 확인:**
   - 그룹 설정 → 관리자 → 봇 확인

### 메시지 삭제 안됨
봇에게 **메시지 삭제 권한**이 필요합니다:
1. 그룹 설정 → 관리자
2. 봇 클릭
3. "메시지 삭제" 권한 활성화

---

## 📊 묶은 플랜 제한

Cloudflare Workers 묶은 플랜:
- 일일 100,000 요청
- KV 읽기: 일일 100,000회
- KV 쓰기: 일일 1,000회
- KV 저장: 1GB

일반적인 Telegram 그룹에서는 충분합니다.

---

## 🔄 코드 업데이트

코드를 수정하면 자동으로 배포됩니다:

1. GitHub에서 파일 수정
2. Commit changes
3. Actions 탭에서 배포 확인
4. 완료 후 자동 적용

---

## 📝 요약

| 단계 | 작업 | 위치 |
|------|------|------|
| 1 | GitHub Secrets 3개 설정 | GitHub Settings |
| 2 | KV Namespace 생성 | Cloudflare Dashboard |
| 3 | wrangler.toml 수정 | GitHub |
| 4 | 자동 배포 확인 | GitHub Actions |
| 5 | Telegram Webhook 설정 | 브라우저 URL |
| 6 | 봇 테스트 | Telegram |

**완료!** 🎉
