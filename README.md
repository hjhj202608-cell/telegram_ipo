# 공모주 업무 카카오톡 자동 알림

GitHub Actions가 평일 오전 7시 30분(한국시간)에 실행되어 공모주 일정을 확인하고, 당일 업무가 있을 때만 카카오톡 나에게 보내기로 알립니다. PC와 Codex가 꺼져 있어도 실행됩니다.

알림 규칙:

- 수요예측 3영업일차: 일임사에 1차 참여의견 문의
- 수요예측 마지막 날: 참여의견 확인 및 최종 참여 여부 확정
- 공모청약 첫날: 일임사의 정상 청약 여부 확인
- 납입일: 납입금액과 계좌 확인 후 자금 송금
- 상장일: 상장 및 매매 개시 상황 확인

GitHub 저장소의 Settings > Secrets and variables > Actions에 KAKAO_REST_API_KEY, KAKAO_CLIENT_SECRET, KAKAO_REFRESH_TOKEN을 등록합니다.

일정 원본은 DART 기반 정보를 제공하는 IPO Korea 공개 페이지를 사용합니다. 실제 업무 전에는 메시지의 KIND 버튼과 주관사 공지로 변경 여부를 최종 확인하세요.

수동 시험은 GitHub의 Actions > IPO Kakao Alert > Run workflow에서 dry_run을 켠 채 실행합니다. 정상 출력 확인 후 dry_run을 끄면 카카오톡으로 발송됩니다.

## 07시 정시 실행 안정화

GitHub Actions의 `schedule` 이벤트는 GitHub 큐 상황에 따라 수 시간 지연될 수 있으므로 07시대 정시 알림의 기본 트리거로 사용하지 않습니다. 운영용 1차 트리거는 외부 스케줄러에서 GitHub `repository_dispatch` API를 호출하고, GitHub `schedule`은 백업 트리거로만 둡니다.

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
