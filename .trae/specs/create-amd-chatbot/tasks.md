# Tasks
- [x] Task 1: 프로젝트 초기화 및 기본 서버 구성
  - [x] SubTask 1.1: Python 프로젝트 설정 (requirements.txt 생성 등)
  - [x] SubTask 1.2: RENDER 배포용 Flask/FastAPI 기반 기본 웹 서버 구축 (UptimeRobot용 `/ping` 라우트 포함)
  - [x] SubTask 1.3: 텔레그램 봇 초기화 및 `config.py` 환경 변수 연동

- [x] Task 2: 데이터베이스 설계 및 구현
  - [x] SubTask 2.1: SQLite 기반의 데이터베이스 구조 설계 (유저 통계, 출석, 관리자 설정, 금칙어 등을 그룹별(chat_id)로 관리)
  - [x] SubTask 2.2: 멀티 그룹 지원을 고려한 데이터베이스 CRUD 헬퍼 함수 구현

- [x] Task 3: 채팅 통계 및 출석 기능 구현
  - [x] SubTask 3.1: 메시지 이벤트 리스너 추가 및 채팅 수 카운트 기능 구현
  - [x] SubTask 3.2: `/stats`, `/rank`, `/mystats` 명령어 핸들러 구현
  - [x] SubTask 3.3: 출석체크 키워드(ㅊㅊ, 출첵, 출석체크) 감지 및 데이터 저장 기능 구현
  - [x] SubTask 3.4: `/attend`, `/attendrank` 명령어 핸들러 구현

- [x] Task 4: 환율 및 가상화폐 변환 기능 구현
  - [x] SubTask 4.1: Exchangerate API 및 CoinGecko API 연동 클라이언트 구현
  - [x] SubTask 4.2: `KRW40000>USDT`, `USDT1000>KRW` 등 변환 포맷 파싱 및 결과 응답 핸들러 구현

- [x] Task 5: 그룹 채팅 전용 관리자 기능 구현 (/admin)
  - [x] SubTask 5.1: 봇의 관리자 여부 및 유저의 정보 변경 권한(can_change_info) 확인 로직 구현
  - [x] SubTask 5.2: 그룹별 `/admin` 기본 인라인 키보드 메뉴 및 네비게이션(뒤로가기) 구현
  - [x] SubTask 5.3: 동일 메시지 반복 방지 설정, 사용자명 변경 알림, 금칙어 필터 메뉴 구현 (chat_id 기반)
  - [x] SubTask 5.4: 예약 메시지 발송 및 반복 게시 설정 메뉴 구현 (chat_id 기반)
  - [x] SubTask 5.5: 통계 초기화 및 그룹별 데이터 내보내기 기능 구현

- [x] Task 6: 자동화 및 스케줄러 기능 구현 (멀티 그룹 대응)
  - [x] SubTask 6.1: APScheduler 연동
  - [x] SubTask 6.2: 매일 자정 출석 초기화 및 매월 말일 23:59 그룹별 랭킹 자동 공지 및 초기화 구현
  - [x] SubTask 6.3: 그룹별 탈퇴한 계정 추방 작업 스케줄링

- [x] Task 7: 테스트 및 Github 업로드 준비
  - [x] SubTask 7.1: `.gitignore`, `README.md` 작성 및 `.env` 템플릿 작성

# Task Dependencies
- [Task 3], [Task 4], [Task 5], [Task 6] depends on [Task 1] and [Task 2]
- [Task 7] depends on all previous tasks
