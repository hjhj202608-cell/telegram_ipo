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
