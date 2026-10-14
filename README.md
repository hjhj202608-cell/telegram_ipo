# 공모주 업무 Telegram 자동 알림

GitHub Actions 또는 외부 스케줄러가 한국시간 평일 오전에 `ipo_alert.py`를 실행해 공모주 일정을 확인하고, 당일 업무가 있을 때만 Telegram Bot으로 알림을 보냅니다. PC와 Codex가 꺼져 있어도 GitHub Actions 환경에서 실행됩니다.

## 알림 규칙

현재 코드 기준 알림 규칙은 다음과 같습니다.

- 수요예측 기간 중 영업일: `종목명 수요예측 N일차입니다. 수요예측시작:MM.DD, 수요예측마감 MM.DD`
- 수요예측 마지막 날: `종목명 수요예측 마감일 입니다.`
- 공모청약 첫날: `종목명 공모주 청약일 1일차입니다.`
- 납입일 2영업일 전: `종목명 납입일 2영업일 전입니다. 공문을 작성하세요. 종목명 납입일 MM.DD`
- 납입일: `종목명 납입일 입니다. 수신팀에게 메신저를 보내세요.`
- 상장일: `종목명 상장일입니다. 매도공문을 작성하세요.`
- 상장일 + 15일 확약분 매도일: `종목명 15일 확약분 매도일 입니다. 매도공문을 작성하세요.`
  - 상장일 + 15일이 주말 또는 한국 공휴일이면 다음 영업일에 알림을 보냅니다.
- 상장일 + 2영업일: `종목명 매도대금 입금일 입니다. 매도대금을 회수하세요.`

## GitHub Secrets

GitHub 저장소의 `Settings > Secrets and variables > Actions`에 다음 값을 등록합니다.

- `TELEGRAM_BOT_TOKEN`: Telegram BotFather에서 발급받은 Bot token
- `TELEGRAM_CHAT_ID`: 알림을 받을 Telegram chat ID

선택 환경변수:

- `DRY_RUN=1`: 메시지를 출력만 하고 Telegram으로 발송하지 않습니다.
- `FORCE_SEND=1`: `state/sent.json`에 같은 날짜가 있어도 재발송합니다.
- `ALERT_DATE=YYYY-MM-DD`: 특정 기준일로 알림을 테스트합니다.

## 일정 원본

일정 수집은 다음 공개 페이지를 사용합니다.

- 1차 원천: 38커뮤니케이션 공모주 일정
- 보조 원천: IPO Korea

코드는 38커뮤니케이션 데이터를 우선 사용하고, 누락된 항목이 있을 때 IPO Korea 데이터로 보완합니다. 실제 업무 처리 전에는 주관사 공지, 청약 배정 공문, 거래소/예탁원 기준 일정과 최종 대조해야 합니다.

## 수동 시험

GitHub Actions에서 수동 실행할 때는 먼저 `DRY_RUN=1`로 메시지 내용을 확인합니다. 정상 출력 확인 후 `DRY_RUN`을 끄면 Telegram으로 발송됩니다.

로컬 테스트 예시:

```powershell
$env:DRY_RUN='1'
$env:ALERT_DATE='2026-10-14'
python ipo_alert.py
```

## 07시 정시 실행 안정화

GitHub Actions의 `schedule` 이벤트는 GitHub 큐 상황에 따라 지연될 수 있으므로 07시대 정시 알림의 기본 트리거로만 의존하지 않습니다. 운영용 1차 트리거는 외부 스케줄러에서 GitHub `repository_dispatch` API를 호출하고, GitHub `schedule`은 백업 트리거로 둡니다.

외부 스케줄러 설정값:

- 시간: 한국시간 평일 07:05
- Method: `POST`
- URL: `https://api.github.com/repos/hjhj202608-cell/telegram_ipo/dispatches`
- Headers:
  - `Accept: application/vnd.github+json`
  - `Authorization: Bearer <GitHub fine-grained token>`
  - `X-GitHub-Api-Version: 2022-11-28`
- Body:

```json
{
  "event_type": "ipo-alert",
  "client_payload": {
    "force_send": "false"
  }
}
```

토큰 권한:

- Repository: `hjhj202608-cell/telegram_ipo`
- Permission: Contents `Read and write`

중복 발송은 `state/sent.json`으로 차단합니다. 외부 스케줄러, GitHub 백업 schedule, 수동 실행 모두 발송 성공 시 같은 날짜를 기록합니다.

## 운영 점검 사항

- `holidays` 패키지가 설치되어 있어야 한국 공휴일 기준 영업일 계산이 반영됩니다. 미설치 시 토요일/일요일만 비영업일로 처리됩니다.
- Telegram 단일 메시지는 4096자를 초과하면 발송하지 않습니다.
- 일정 원천 페이지 구조가 바뀌면 수집 로직이 실패할 수 있습니다.
