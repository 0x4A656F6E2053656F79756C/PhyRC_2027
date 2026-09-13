# 평가 실행과 점수 해석

평가는 실제 장면의 옷·마네킹·그리퍼 상태에서 판정합니다. 이미지의 외형만 보고 채점하지 않습니다.
현재 점수 규칙은 `pickup-excluded-last-award-v9`입니다.

## Teleop 시작부터 자동 평가

```bash
./run.sh gui --evaluate 1
# 학습 데이터도 수집:
./run.sh gui --training-record 1 --evaluate 1
```

처음 제어를 시작하기 전에 평가가 자동 시작됩니다. F6/F7을 누를 필요가 없습니다.
ESC로 종료하면 `output/evaluation/teleop/<평가ID>/result.json`과 `samples.jsonl`이 저장됩니다.
P 초기화나 저장 슬롯 복원은 현재 실시간 평가 시도를 무효 종료하고 다음 시도로 다시 시작합니다.
정식 비교에는 동일한 초기화/종료 조건의 연속 시도를 사용하세요.

학습 기록 자체도 에피소드별 평가를 자동 저장합니다. 기본 모드에서는 종료 후 변환 중 채점하며,
`--evaluate 1`을 추가하면 조종 중 점수도 볼 수 있습니다. `--training-render live`는 이미 자체 실시간 평가를 사용합니다.
오류로 중단된 실시간 평가는 유효 점수로 처리하지 않습니다.

## Replay 재채점

```bash
# 화면 없이 원본 상태를 읽어 재채점 (GPU 없이 CPU 실행)
./run.sh cpu /scripts/evaluate_replay.py \
  /output/full_teleop/<실행ID> --output /output/evaluation/replay_check

# Isaac Sim 화면으로 보면서 같은 원본 상태를 채점
./run.sh replay output/full_teleop/<실행ID> \
  --evaluate /output/evaluation/replay_visual
```

replay 평가는 기록된 물리 상태·접촉 기하·파지 기록을 읽습니다. 단순 MP4 재생으로 채점하는 기능이 아닙니다.
새 물리 계산으로 정확한 solver 이력을 재현했다는 뜻도 아닙니다.
replay 배속이나 컴퓨터의 처리 시간은 채점 시각에 영향을 주지 않습니다.

## 항목별 점수

| 항목 | 최대 | 조건 |
|---|---:|---|
| pickup | 5 | 같은 그리퍼로 잡은 영역을 파지 직후 기준5cm 이상 들어 올려 시뮬레이션3초 유지 |
| first_sleeve | 5 | 첫 손이 해당 소매 구멍을 통과해 밖으로 나옴 |
| opposite_shoulder | 5 | 옷 일부가 반대쪽 어깨 관절을 넘어감 |
| second_sleeve | 5 | 다른 손이 다른 소매 구멍 밖으로 나옴 |
| overall_dressing: left_upper_arm | 5 | 왼팔의 해당 소매가 상박 일부를 덮음 |
| overall_dressing: right_upper_arm | 5 | 오른팔의 해당 소매가 상박 일부를 덮음 |
| overall_dressing: neck | 10 | 정상적인 목 구멍 통과가 확인되면 즉시 획득 |
| overall_dressing: front_orientation | 10 | 목이 나온 상태에서 브이넥 앞면이 마네킹 앞을 향함을0.5초 확인 |
| **총점** | **50** | Overall30점 포함 |

소매 통과에는 손목과 손끝이 밖으로 나오는 증거가 필요합니다. 두 팔이 같은 소매를 통과한 것은 인정하지 않습니다.
상박은 소매 덮임의 성공/실패로5점 또는0점이며 길이 비율로 계산하지 않습니다. 몸통 천의 덮임과 하박은 점수가 아닙니다.
목은 가슴이 옷 내부에 있고 머리/목이 목 구멍 밖으로 정상 노출됐는지 확인합니다. 목 점수에 유지 시간은 없습니다.
브이넥 방향은 앞쪽45도 이내 및 앞면 방향 투영 길이2cm 이상의 구분 가능한 상태를 사용합니다. 뒤로 입으면 방향 점수는0입니다.

달성 점수는 이후 상태가 달라져도 보존합니다.
**착의 성공**은 양손이 서로 다른 소매 밖에 있고 목/머리 노출과 올바른 앞뒤 방향이 함께0.5초 확인된 달성 이력입니다.
총점50점과 성공 시연은 같은 의미가 아니므로 결과의 `success`를 별도로 확인하세요.

## points/s와 실패

```text
분자 = raw_points − 실제 획득한 pickup 점수          최대45점
분모 = 마지막 착의 득점 시각 − 최초 접촉 시각        시뮬레이션 초
points/s = 분자 / 분모
```

최초 접촉은240Hz 물리 tick에서 옷과 마네킹의 충돌 메시 접촉 범위를 검사해 고정합니다.
PhysX solver 내부 충돌 이벤트 그 자체를 기록한 값은 아닙니다.
득점은20Hz 평가 표본에서 판정합니다. 접촉 이후 떨어진 구간도 다음 득점까지의 시간에 포함합니다.

- 추가 착의 득점 없이 기다리면 마지막 득점 시각과 points/s를 유지합니다.
- 집기를 나중에 달성해도 분자/분모가 변하지 않습니다. 항목별 총점에는 집기5점이 남습니다.
- 새 착의 점수를 얻으면 누적 점수와 최초 접촉부터의 시간으로 다시 계산합니다. 오래 걸리면 비율이 내려갈 수 있습니다.
- 접촉 후 착의0점은 `no_dressing_points`, points/s=0입니다.
- 무접촉은 `no_contact`, 측정 rate는 null입니다. 양수 득점의 분모가0이면 `awaiting_elapsed_time`, rate는 null입니다.
- 이런 null rate 실패도 집계용0점으로 포함합니다. 실패 seed를 빼고 평균을 높이지 않습니다.
- 여러 공통 seed의 결과는 모든 에피소드 점수의 산술평균입니다.

## 결과 JSON 필드

| 필드 | 의미 |
|---|---|
| valid | 평가 기록의 유효성. false면 정상 점수로 사용하지 않음 |
| result.raw_points | 집기 포함 누적 총점, 최대50 |
| result.score_items | 집기/첫 소매/어깨/두 번째 소매/Overall 항목별 값 |
| result.rate_points | 집기를 제외한 분자, 최대45 |
| result.task_time_s | 위 points/s 분모 |
| result.first_contact_time_s | 에피소드 시작 기준 최초 접촉 시각 |
| result.last_score_award_time_s | 마지막 착의 득점 시각 |
| result.elapsed_episode_time_s | 준비 시간 포함 전체 에피소드 시간 |
| result.contact_elapsed_time_s | 접촉부터 현재/종료까지의 전체 시간 |
| result.final_score | points/s 또는 null |
| result.score_status | scored / no_contact / no_dressing_points / awaiting_elapsed_time |
| result.success | 착의 성공 조건 달성 여부 |

터미널은 점수·성공 여부·최초 접촉 상태가 달라질 때 출력하며 종료 결과는 항상 저장합니다.
`samples.jsonl`에는 출력되지 않은 표본도 포함됩니다. 최종 정책은 [정책 실행 가이드](POLICY.md)의 여러 seed 평가를 사용하세요.
