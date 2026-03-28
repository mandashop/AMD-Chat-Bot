# 🤖 AMD Chat Bot Spec

## Why
사용자가 그룹 채팅의 통계, 출석 관리, 환율 및 가상화폐 변환을 편리하게 이용하고, 관리자가 1:1 채팅을 통해 손쉽게 그룹을 관리할 수 있는 텔레그램 봇이 필요합니다. RENDER 무료 서버에서 24시간 동작할 수 있도록 UptimeRobot 연동을 고려한 웹 서버 구조도 요구됩니다.

## What Changes
- 텔레그램 봇 기본 설정 및 웹훅/폴링 기반 서버 구축 (RENDER 무료 티어 대응)
- UptimeRobot 모니터링을 위한 `/ping` 엔드포인트 구현 (15분 절전모드 방지)
- 여러 그룹 지원 (멀티 그룹 데이터베이스 구조)
- 채팅 통계 기능 추가 (/stats, /rank, /mystats 등)
- 출석체크 기능 추가 (ㅊㅊ, 출첵, /attend, /attendrank 등)
- 환율/가상화폐 변환 기능 추가 (KRW>USDT 등)
- 관리자 기능 구현 (그룹 채팅 전용 /admin, 봇 및 유저의 관리자 권한 확인 포함, 인라인 버튼 기반 UI 및 뒤로가기 지원)
- 자동화 스케줄러 추가 (월말 랭킹 공지, 자정 출석 초기화, 탈퇴 계정 자동 추방 등)
- 데이터베이스 백업 및 다운로드 기능 구현

## Impact
- Affected specs: 텔레그램 그룹 관리, 사용자 통계, 환율 정보 제공, 자동화 관리
- Affected code: `bot.py`, `config.py`, `database.py`, `scheduler.py`, `handlers/` 디렉터리 등 전체 신규 생성

## ADDED Requirements
### Requirement: 웹 서버 및 Uptime 모니터링
The system SHALL provide a web server running on a specific port for Render deployment, including a health check endpoint.
#### Scenario: UptimeRobot Ping
- **WHEN** UptimeRobot requests `/ping`
- **THEN** 서버는 `200 OK`와 함께 상태 정보를 반환하여 절전 모드를 방지한다.

### Requirement: 채팅 및 출석 통계
The system SHALL provide tracking for messages and daily attendance.
#### Scenario: Daily Attendance
- **WHEN** 사용자가 그룹에서 "출첵"을 입력할 때
- **THEN** 시스템은 사용자의 출석 횟수를 증가시키고 확인 메시지를 보낸다.

### Requirement: 환율 변환
The system SHALL provide currency and crypto conversion using Exchangerate and CoinGecko APIs.
#### Scenario: Convert Currency
- **WHEN** 사용자가 "KRW40000>USDT"를 입력할 때
- **THEN** 시스템은 API를 호출하여 환율을 계산하고 결과를 응답한다.

### Requirement: 관리자 메뉴
The system SHALL provide an interactive admin menu via group chats, verifying both bot and user permissions.
#### Scenario: Admin Settings
- **WHEN** 관리자가 봇이 포함된 그룹 채팅에서 `/admin`을 입력할 때
- **THEN** 봇은 자신의 관리자 권한과 사용자의 정보 변경 권한(can_change_info)을 확인한 뒤, 인라인 키보드가 포함된 그룹별 관리자 설정 메뉴를 표시한다.
