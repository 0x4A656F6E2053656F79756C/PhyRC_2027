# 랜덤화 직전 버전 복원 — 2026-09-10

사용자 요청에 따라 `104d6b0`을 기준으로 복원했습니다. 첫 커밋 `c5d57e5`와
시뮬레이션 소스는 같으며, 그 사이 추가된 설치 안내와 `doctor` 진단 도구는
유지합니다. 이력을 삭제하지 않고 복원 커밋을 추가합니다.

| 첫 커밋 이후 추가 사항 | 관련 커밋 | 이번 복원 |
| --- | --- | --- |
| 환경별 설치 안내, doctor 진단, 새 clone·Home 경로 검증 기록 | bf234d3, 0f8780a, 104d6b0 | 유지 |
| 사람·의자 위치 반지름 10cm 및 방향 ±30° 랜덤화 | a5c3824 | 제거 |
| observation/action 명세, 상태 측정, RGB-D 센서, Gymnasium reset/step, 간단한 학습 예제 및 참가자 안내 | d152661, d4bd2c4 | 제거 |
| 티셔츠가 네 박스 중 하나에 스폰되는 랜덤화 및 안정성 HTML 보고서 | e409213, a47b300 | 제거 |
| --no-randomization 실행 옵션 | 91107e2 | 제거: 이제 원래 고정 배치로 실행 |
| 물리 스텝 사이 천 삼각형의 충돌 누락을 막는 추가 패치 | 55b9ded | 제거: 원래 충돌 코드로 복원 |
| 두 로봇 native grasp 및 회전 일관성 검증 코드·기록 | 0ba8c25 | 제거 |

후속 코드와 보고서는 `backup/pre-randomization-rollback-0ba8c25` 브랜치에
보존되어 있습니다. 원래 네 박스·두 로봇·티셔츠, 팔 자세와 길이, native grasp,
기존 충돌 가드는 유지됩니다. 이번 복원은 랜덤화 옵션만 끄는 것보다 넓은
범위로, 학습 환경과 후속 충돌 패치도 되돌립니다.

실행 중이던 GUI를 종료하고 기존 runtime을 보존한 뒤 재생성했습니다.
소스 16개와 실제 실행 복사본 모두 기준 커밋과 바이트 단위로 일치합니다.
GPU smoke에서 원래 장면과의 일치, 두 로봇 움직임, 그리퍼 토글,
유한한 천 좌표와 저장/복원 오차 0을 확인했습니다. 실제 옷 입히기 전체 동작이나
옷 정지 현상의 원인을 검증한 결과는 아닙니다.

측정 결과: [rollback evidence](verification-results/pre-randomization-rollback.json).
원래 사용자 슬롯 2개는 내용과 수정 시간을 유지했고, 별도 복사본 및 이전 runtime과
GUI 로그는 `output/rollback-backup-0ba8c25`에 있습니다.

```bash
export PHYRC_ACCEPT_EULA=1
./run.sh gui
# Visual mesh 표시:
STRETCH4_SHOW_COLLIDER=0 ./run.sh gui
```
