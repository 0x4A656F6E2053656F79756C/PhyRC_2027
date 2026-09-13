# Phase 1 평가 함수 — 소매 상박 덮임·손 노출·목·브이넥 / 마지막 득점 기준 points/s v9

참가자 실행·채점 안내는 [대회 평가 가이드](competition/EVALUATION.md)를 참고하세요.
`./run.sh gui --evaluate 1`로 시작부터 자동 평가할 수 있습니다.

현재 `scoring_revision=pickup-excluded-last-award-v9`입니다. 기존 집기/소매/어깨의 독립 항목
20점은 유지하고, 사용자 요청에 따라 Overall dressing 30점을 재배분했습니다.
로봇·그리퍼·옷·마네킹의 물리/형상/설정은 변경하지 않습니다.

## 점수

| 항목 | 점수와 조건 |
|---|---|
| 집기 | 같은 그리퍼로 실제 잡은 부분을 들어 올려 3초 유지: 5 |
| 첫 소매 | 첫 번째 손이 소매 구멍 밖으로 나옴: 5 |
| 반대 어깨 | 옷 일부가 반대쪽 어깨 관절을 넘어감: 5 |
| 두 번째 소매 | 다른 손이 다른 소매 구멍 밖으로 나옴: 5 |
| Overall — 왼쪽 상박 | 해당 소매가 왼쪽 상박 일부를 덮으면 5, 아니면 0 |
| Overall — 오른쪽 상박 | 해당 소매가 오른쪽 상박 일부를 덮으면 5, 아니면 0 |
| Overall — 목 | 목 구멍 통과(정상 목/머리 노출)를 확인하면 즉시 10; 유지 시간 없음 |
| Overall — 브이넥 앞뒤 | 목이 나온 상태에서 브이넥 앞면이 마네킹 앞을 향함을 0.5초 연속 확인: 10 |
| 합계 | 최대 50 |

상박은 **길이 비율 없이 0점 또는 5점**입니다. 해당 팔이 통과하는 소매 영역 안에
어깨–팔꿈치 중심선의 일부가 들어가면 인정합니다. 몸통 천이 상박을 덮거나 단순히
소매 표면에 접촉하는 것만으로는 점수를 주지 않습니다. **하박은 배점에서 제외합니다.**

소매 영역은 현재 티셔츠의 원래 평평한 메시에서 밑단의 좌우 몸통 경계 바깥에 있는
삼각형 중 각 커프와 연결된 부분으로 고정합니다. 변형 후 위치로 소매 정체성을 바꾸지
않습니다. 소매 뿌리와 커프를 계산용으로만 닫아 상박 선분의 내부 진입을 검사합니다.
경계를 걸치는 삼각형은 보수적으로 제외하므로 뿌리의 한 메시 띠 정도는 인정 범위에서
제외될 수 있습니다. 길이 비율이나 40개 표본으로 점수를 계산하지 않습니다.

소매 통과 점수는 팔 경로가 커프 구멍을 통과하고 커프가 손목보다 어깨 쪽에 있으며,
손목과 손끝이 모두 옷 밖에 있어야 합니다. 손목만 들어갔거나 손끝만 나왔으면 0점입니다.
먼저 손이 나온 팔이 첫 번째 팔이고, 동시에 나오면 왼팔 우선입니다.
두 팔이 같은 커프를 통과한 경우 소매 통과 및 상박 점수 모두 인정하지 않습니다.

목은 가슴이 옷 내부, 머리가 collar 밖이고 머리 피부가 neckline에 걸리지 않은지를
기존 기하 판정으로 확인합니다. `neck_passed=true`가 처음 측정된 표본에서 목 10점을
즉시 확정하며, 0.5초 노출을 기다리지 않습니다. 평가 표본 주기는 기존 20Hz입니다.
브이넥 앞면은 옷 자산의 `vneck` material subset에 속한
정점들의 정체성을 추적합니다. 마네킹의 어깨·목으로 해부학적 앞쪽을 계산하므로 spawn
회전에 따라 함께 회전합니다. collar 중심에서 브이넥 영역 중심으로 향하는 방향을
몸통 수직축에 수직인 평면에 투영하여 앞쪽과 45도 이내이고, 투영 길이가 2cm 이상인
경우 올바른 앞면으로 인정합니다. 2cm 미만으로 접힌 모호한 상태에는 방향 점수를 주지
않습니다. **목이 나오기 전의 방향 일치는 점수를 주지 않습니다.**

45도 허용·2cm 최소 구분·각 10점 배분은 이번 요청에 따른 평가 설계이며
원래 PDF가 정한 수치가 아닙니다. 뒤집어 입으면 목 점수는 가능하지만 앞뒤 점수는 0입니다.
옷의 안감/겉감 뒤집힘까지 판별하는 규칙은 아닙니다.

점수는 기존처럼 획득 이력을 보존합니다. 상박의 소매 덮임 달성과 확인된 목·앞뒤 점수는 나중에
옷이 벗겨져도 회수하지 않습니다. 현재 수치는 진단에 별도로 남습니다. 기존의 전체 팔
`10n+20m`와 착의 완료에 의한 Overall 30점 일괄 override는 **현재 기준에서 사용하지 않습니다.**

성공은 양쪽 손의 소매 노출·정상 목/머리 노출·올바른 앞뒤 방향이 함께 0.5초 확인된
달성 이력입니다. `success_evaluated=true`, `success=true`로 성공 시연을 선별하며
50점이나 `dones=1`로 선별하지 않습니다. 종료 프레임만 평가한 성공 조건은 아닙니다.

## points/s 공식

`points/s = (누적 총점 − 실제 획득한 집기 점수) / (마지막 착의 득점 시각 − 최초 접촉 시각)`

모든 시각은 시뮬레이션 시간입니다. 각 득점 시점의 **누적 평균**이며, 직전 득점과의
차분 점수를 직전 구간 시간으로 나눈 순간 비율이 아닙니다. 추가 착의 득점 없이 기다리면
최종 points/s도 유지됩니다. 다음 득점까지 오래 걸리면 새로 계산된 비율이 낮아질 수 있습니다.

`raw_points`(최대50)와 `rate_points`(최대45)를 구분합니다. `excluded_pickup_points`는
분자에서 뺀 실제 집기 점수이고, `task_time_s`는 위 공식의 분모입니다.
`last_score_award_time_s`/`last_score_award_tick`은 분모 종료 시점이며 득점 전에는 null입니다.
`contact_elapsed_time_s`는 최초 접촉부터 현재/에피소드 종료까지의 시간,
`elapsed_episode_time_s`는 준비 포함 에피소드 시간으로 분모와 별도로 보존합니다.
콘솔 `contact +`는 실제 접촉 이후 경과, `RATE .../45 over ...s`는 채점 분자/분모입니다.

## 결과 읽기

`score_items`에는 pickup / first_sleeve / opposite_shoulder / second_sleeve /
overall_dressing의 다섯 항목이 유지됩니다. Overall의 `components`는
`left_upper_arm`, `right_upper_arm`, `neck`, `front_orientation`입니다.
`component_max_points`, `upper_arm_sleeve_covered`, `current_upper_arm_sleeve_covered`,
`neck_confirmed_at_s`, `front_confirmed_at_s`도 제공합니다.
콘솔은 시작 시 한 번, 이후 **항목 점수·착의 성공 여부·최초 접촉 상태가 바뀔 때만**
출력합니다. 20Hz 평가 표본마다 변경을 확인하므로 1초 사이에 발생한 점수 변화도
즉시 표시합니다. 시간·집기 유지 카운터·points/s 변화만으로 같은 점수 행을 반복하지
않습니다. `sim`은 평가 시작 이후 시뮬레이션 시간, `contact +`는 최초 접촉 이후 시간입니다.
종료 시 최종 점수는 항상 출력합니다. `samples.jsonl`은 표본을 생략하지 않고 계속 저장합니다.
Headless CLI는 전체 JSON의 콘솔 중복 출력을 기본 생략하며 `--json`으로 요청할 수 있습니다.
Visual replay도 콘솔에 평가 결과 JSON을 반복하지 않으며 결과 파일에는 전체 내용을 보존합니다.

새 측정 입력은 `phase1-measurements-v7`, 집계 결과는 `phase1-scores-v9`입니다.
각 샘플에는 기존 필드 및 목/방향 진단에 더해 `upper_arm_sleeve_covered: {left, right}`와
`hand_out_of_sleeve: {left, right}`, `neck_passed` 불리언이 필요합니다.
`neck_passed`는 현재 기하 통과 판정이며 `neck_out`과 동일해야 합니다.
`rate_rule="pickup-excluded-last-award-v9"`도 필요합니다. `arm_coverage`와
`upper_arm_coverage` 비율은 과거 진단 호환용이며 새 배점에는 사용하지 않습니다.
옛 v1~v3 측정 로그는 legacy v5 점수, v4 로그는 과거 35% 비율 기반 v6 점수로만 읽습니다.
v5 측정 로그는 과거 목 0.5초 조건의 v7 점수로만 읽습니다.
v6 측정 로그는 과거 집기 포함/종료 시각 분모의 v8 점수로 읽습니다.
새 측정/옛 측정을 한 집계에 섞을 수 없습니다. 새 기준은 원본 상태에서 다시 측정해야 합니다.
live/replay 결과 파일의 외부 컨테이너 `phase1-live-v4`는 유지하고 내부
`scoring_revision`과 `score_breakdown_version`으로 새 배점을 구분합니다.

### 최초 접촉부터 시간 측정

기본 live/headless/visual 평가는 **시뮬레이션 시간**으로 집기 3초, 방향/착의 완료 0.5초와
points/s를 모두 계산합니다. 서로 다른 PC의 처리 지연이나 replay 배속은 채점 시간이
아닙니다. `output/evaluation/recorded_wall_v7/`의 실제 시간 재채점은 별도 비교 실험이며
기본 평가 기준을 변경한 것이 아닙니다. 대회 운영 시 실제 추론 시간 제한은 별도로 정하고
주최 측의 통제된 장비에서 최종 정책 평가를 수행하는 것을 권장합니다.


- 선택한 연속 평가 구간의 모든 physics tick(240Hz)을 검사하여 첫 접촉을 고정합니다.
  `(마지막 착의 득점 tick - 최초 접촉 tick) × physics_dt_s`가 points/s의 분모입니다.
  다음 착의 득점이 있으면 종료 tick을 갱신하며, 접촉이 끊긴 구간도 포함합니다.
  마지막 득점 후 대기 시간, 준비 시간, replay 배속은 분모에 포함하지 않습니다.
- 집기 5점과 3초 유지 이력은 항목별 총점(50점)에 보존하지만,
  **points/s의 분자에서는 실제 획득한 집기 점수만 제외**합니다(최대45점).
  집기 미달성 시 5점을 임의 차감하지 않습니다. 집기를 나중에 달성해도 분모 종료 시점은 갱신하지 않습니다.
- **사용자가 승인한 기하학적 접촉 기준**입니다. 활성화된 마네킹의 충돌 메시와
  천 삼각형 표면 사이 거리가 두 물체의 기존 contact offset 합 이하면 접촉입니다.
  기본 장면은 옷 8mm + 마네킹 6mm = 14mm입니다. 몸통과 양손 충돌 메시를 모두
  포함하고 비활성 시각 메시는 제외합니다. 삼각형 꼭짓점뿐 아니라 모서리/면 교차와
  모서리 간 거리도 검사하며, 구형 손 콜라이더는 구 반지름을 사용합니다.
- 충돌 메시/offset/마찰/포즈/solver 설정을 변경하지 않습니다. 실제 PhysX 내부
  충돌 이벤트·충격량 판정과 같다는 보장은 없습니다. SDF/convex cooking 후의 형상,
  speculative contact, physics tick 사이의 접촉도 차이가 날 수 있습니다.
  [NVIDIA 제한사항](https://docs.isaacsim.omniverse.nvidia.com/latest/physics/physics_resources.html)은
  deformable contact report 미지원을 명시합니다.
- 접촉이 없으면 `score_status=no_contact`, 시간 0, `final_score=null`(터미널 N/A)입니다.
  마지막 착의 득점이 접촉 이전/접촉 순간이면 양의 득점 경과 시간이 없어 N/A입니다.
  접촉 후 착의 점수가 전혀 없으면 `score_status=no_dressing_points`, points/s=0입니다. 준비 시간을 분모로 쓰거나
  무한대 점수를 만들지 않습니다. 이 경우 원점수와 진단 결과를 저장하고,
  **집계용 `ranking_score=0`으로 모든 seed의 평균에 포함합니다.** 에피소드의 실제
  비율 `final_score=null`과 `ranking_status=no_contact/awaiting_elapsed_time`은 유지합니다.
  제출의 `final_score`는 모든 episode `ranking_score`의 산술평균입니다.
  예를 들어 정상 10 points/s와 무접촉 실패가 한 번씩 있으면 제출 점수는 5입니다.
  모든 seed가 무접촉이어도 집계 결과 0을 저장하고 정상 종료합니다.
  측정 누락·잘못된 시간·NaN·잘못된 seed 같은 입력 오류는 여전히 거부합니다.
- `first_contact_tick`, `first_contact_time_s`, `task_time_s`, `elapsed_episode_time_s`로
  접촉과 제외된 준비 시간을 확인할 수 있습니다. tick/시간은 선택한 평가 구간 기준이며,
  replay metadata의 `recording_first_contact_tick`은 원본 기록의 절대 tick입니다.
  `first_contact_collider`에는 첫 접촉한 콜라이더 경로가 남습니다.
- F6/평가 시작은 잡기·접촉 전이어야 합니다. 시작부터 접촉해 있으면
  `started_in_contact=true`이고 시작 tick 0부터 셉니다. 그보다 이전 접촉 시점을
  복원했다는 뜻은 아닙니다. 공정 비교에는 동일한 초기화·종료 기준의 전체 시도를 쓰세요.
  기존 episode time limit은 전체 시도 제한이며 점수 분모와 별도입니다.

### 집기 5점의 조건

기존에는 옷 **전체**가 테이블·바닥에서 1cm 이상 떨어져야 3초 타이머가
시작됐습니다. 실제 사용자 기록에서는 그리퍼 0의 파지가 11.15초부터였지만
전체 이탈이 19.25초부터여서 22.25초에 5점이 부여됐습니다.

현재는 각 그리퍼의 실제 native attachment가 생성된 시점의 앵커 높이를
기준으로, **잡은 정점들의 높이 증가량 중앙값이 5cm 이상**이면 들어 올림으로
인정합니다. 옷자락이 테이블에 남아 있어도 됩니다. 해당 조건을 동일 그리퍼로
연속 3 시뮬레이션 초 유지하면 5점입니다.

- 닫기 명령만으로는 인정하지 않습니다. 유효 앵커와 native attachment가 있어야
  하고 앵커 위치 오차 p95가 3.5cm 이하여야 합니다.
- 놓기/파지 실패/들어 올림 조건 상실은 그리퍼별 타이머를 초기화합니다.
  다른 그리퍼의 짧은 유지 시간을 이어 붙이지 않습니다.
- **F6은 잡기 전에 누릅니다.** 평가 전에 이미 잡고 들어 올린 동작의 이력은
  소급 판정할 수 없습니다. 평가 시작 시 이미 잡았다면 그때부터의 상승을 측정합니다.
- `pickup_diagnostics`에 앵커 수·오차·높이 증가량·들어 올림 여부를 저장하고,
  결과의 `pickup_hold_seconds`에 그리퍼별 연속 시간을 반환합니다.

## 직접 teleop 평가

```bash
./run.sh gui
# 모든 3D 동작 기록도 함께 사용하려면:
./run.sh gui --full-record 1
```

1. 장면 준비 후 **조작 전 F6**: 평가 시작.
2. 기존 키로 조작. 매 시뮬레이션 1초에 집기 타이머와 점수 출력.
3. **F7**: 종료, `FINAL SCORE` 출력 및 저장.

`output/evaluation/teleop/<실행 ID>/result.json`은 결과,
`samples.jsonl`은 시간별 측정 이력입니다. `STRETCH4_EVALUATION_DIR`로
저장 위치를 바꿀 수 있습니다. 전체 teleop 기록은 별도 기능이며 F6과 무관하게
첫 조작 전부터 기록합니다.

평가 중 P 초기화, F슬롯 LOAD, 비유한 상태 복구는 해당 평가를 무효 처리합니다.
슬롯 SAVE는 평가를 이어갑니다. Esc는 평가를 종료·저장합니다.
0초 실행이나 측정 오류는 유효한 점수를 내지 않습니다.
이미 일부 입힌 상태에서 시작하면 `started_with_arm_inserted=true`로 표시됩니다.
코드 변경 전에 실행한 GUI는 재시작해야 새 평가기가 적용됩니다.

## 전체 기록/replay 상태로 평가

새 버전에서 `--full-record 1`로 기록하면 F6을 누르지 않았어도 기록 후 평가할 수
있습니다. 기록에 보존한 실제 천 정점·로봇 자세·native 파지 앵커와 평가 기준점으로
동일한 측정/채점 코드를 실행합니다. 새 물리 시뮬레이션을 시작하지 않습니다.

```bash
# Isaac/GPU 없이 실행 (호스트 Python + NumPy)
python3 scripts/evaluate_replay.py output/full_teleop/<실행 ID> \
  --output output/evaluation/replay

# 3D 재생과 평가를 함께 실행
./run.sh replay output/full_teleop/<실행 ID> \
  --evaluate /output/evaluation/replay
```

기본은 전체 구간이며, `--start-tick`/`--end-tick`으로 평가 구간을 선택할 수 있습니다.
화면 replay에서는 `--evaluation-start-tick`/`--evaluation-end-tick`입니다.
실시간 평가와 비교하려면 구간과 평가 소스 버전이 같아야 합니다.
reset/LOAD가 포함된 구간은 무효이며, 이전 v1 기록은 앵커 정보가 부족하여 정확한
전체 평가를 지원하지 않습니다. 새로 기록해야 합니다.
저장 위치와 상세 사용법은 [전체 기록 안내](FULL_TELEOP_RECORDING.md#저장된-물리-상태로-평가하기)를 참고하세요.

### 기존 full replay를 v7로 재평가

새 기록은 소매 영역과 브이넥 정체성을 평가 context v3에 함께 저장합니다. 이전 기록도 원본
`scene.usdc`의 원래 소매 메시와 vneck 영역을 읽어 재평가할 수 있습니다. 호스트 Python에 USD가
없으면 기록별로 아래 CPU 명령을 한 번 실행합니다. 이전 v6용 sidecar도 한 번 재생성해야 합니다. 원본은 수정하지 않고 해시로
원본과 연결된 `evaluation/quality_contexts/<ID>.json` 파일을 별도로 만듭니다.

```bash
./run.sh cpu /scripts/export_replay_quality.py \
  /output/full_teleop/<실행ID>
```

이후 위의 headless/visual 평가 명령을 그대로 사용합니다. 다른 위치에 저장했다면
`--quality-context <경로>`로 전달합니다. 브이넥 표식이나 원본 토폴로지가 없으면
방향 점수를 추정하지 않고 명확한 오류를 반환합니다.

## 학습한 정책 평가

```bash
# 중립 행동으로 실행 경로 확인
STRETCH4_RANDOMIZE=1 ./run.sh python \
  /scripts/evaluate_policy.py --zero-policy --profile measured_state \
  --seeds 42 43 --seconds 5

# TorchScript 모델 예시: 실제 파일 경로로 교체
STRETCH4_RANDOMIZE=1 ./run.sh python \
  /scripts/evaluate_policy.py \
  --policy /scripts/phase1_torchscript_policy.py \
  --checkpoint /output/my_training/policy.ts \
  --seeds 42 43 44 45 46 --seconds 60
```

seed마다 초기화한 후 지정한 시간까지 실행합니다. 완전 착의 판정만으로
자동 조기 종료하지 않습니다. teleop과 같은 `EvaluationSession`을 사용합니다.
현재 기본 `actor_rgbd`에는 카메라 5개가 있으므로 모델의 입력과 전처리를
학습 때와 일치시켜야 합니다. `--profile measured_state`는 카메라 없는 관측입니다.

다른 모델 형식은 `load_policy(*, checkpoint, observation_space, action_space)`를
정의한 Python 어댑터를 `--policy`에 지정합니다. 반환 객체는
`policy(obs) -> float32 (2,9), [-1,1]` 계약을 따릅니다. 선택적 `policy.reset()`은
각 seed 시작에 호출합니다. 일반 state_dict를 TorchScript로 이름만 바꿔 쓸 수 없습니다.

결과는 `output/evaluation/policy/episodes/<실행 ID>/`와
`output/evaluation/policy/summary_<실행 ID>/scores.json`에 저장됩니다.
정책/측정 예외는 평가 실패이며 해당 seed를 조용히 제외하지 않습니다.
접촉 이후 시간이 있는 실패 동작은 0점/부분 점수로 평균에 포함합니다.
접촉이 없거나 접촉 직후 종료한 seed는 실제 비율 N/A, 집계 기여도 0으로 포함합니다.
`success_count`, `success_evaluated_episode_count`, `success_rate`도 별도 출력합니다.
옛 로그처럼 완료 측정이 없는 episode가 포함되면 성공률은 `null`이며 실패로 추정하지 않습니다.

## 기록된 측정값의 오프라인 채점

```bash
# 합성 예제: 실제 시뮬레이션 성능 결과가 아님
python3 scripts/evaluate_phase1.py --demo \
  --write-demo-input output/evaluation/demo_measurements.json \
  --output output/evaluation/demo_scores.json

python3 scripts/evaluate_phase1.py \
  --input output/evaluation/measurements.json \
  --output output/evaluation/scores.json
```

새 입력은 `schema_version=phase1-measurements-v4`이며 다음과 같습니다.
각 제출에는 중복되지 않는 seed가 최소 2개 필요하고 제출끼리 seed 집합이 같아야 합니다.

```json
{
  "schema_version": "phase1-measurements-v4",
  "submissions": [{
    "submission_id": "policy-v1",
    "episodes": [{"seed": 42, "samples": []}, {"seed": 43, "samples": []}]
  }]
}
```

v4 샘플 예시 (`physics_tick`/`physics_dt_s`/`first_contact_tick`은 정수 시간 정밀도를 보존하는 추가 필드):

```json
{
  "time_s": 0.0,
  "first_contact_time_s": null,
  "physics_tick": 0,
  "physics_dt_s": 0.004166666666666667,
  "first_contact_tick": null,
  "gripper_holding": [false, false],
  "gripper_lifted": [false, false],
  "garment_lifted_clear": false,
  "wrist_in_sleeve": {"left": false, "right": false},
  "garment_beyond_shoulder": {"left": false, "right": false},
  "arm_coverage": {"left": 0.0, "right": 0.0},
  "dressing_complete": false,
  "upper_arm_coverage": {"left": 0.0, "right": 0.0},
  "neck_out": false,
  "front_facing": false
}
```

`first_contact_time_s`는 접촉 전 null, 접촉 후에는 처음 발생한 동일 시각을 계속
기록합니다. 20Hz 샘플 시각으로 올림하지 않고 240Hz에서 검출한 시각을 사용합니다.
`garment_lifted_clear`는 전체 옷 이탈의 진단값으로 남겨 둡니다. v2 집기 채점은
그리퍼별 `gripper_lifted`를 사용합니다. `arm_coverage`는 순간 측정치이고 최고값
누적은 채점기가 수행합니다. 좌우는 사람의 해부학적 좌우입니다.
첫 샘플은 0초, 마지막은 종료 시점이며 기본 간격은 최대 0.05초입니다.
중복·역행 시간, 누락, NaN/Inf, 잘못된 비율은 거부합니다.

접촉 필드 없는 이전 v1/v2 측정 로그는 과거의 전체 시간 방식으로만 채점하며,
새 접촉 기준 점수와 혼합 비교하면 안 됩니다. `--demo`는 옛 배점 비교용 합성 v3 예제입니다. 새 v7 예제는 `scripts/check_sleeve_scoring.py`에 있습니다.
이전 v1 입력도 읽지만 새 집기/목 측정이 없으면 전체 이탈 기반 집기 조건으로
대체하고 완전 착의 override는 하지 않습니다. 옛 영상 없는 측정 로그만으로
목 통과 여부나 집기 시점의 높이를 복원할 수 없습니다. v2 최고 진행도 규칙으로
재채점되므로 기존 결과와 비교할 때 `scoring_revision`을 함께 확인해야 합니다.

## 실제 장면 측정과 한계

`Policy/evaluation_live.py`가 실제 천 정점, PhysX 파지 앵커, 포즈를 적용한
사람 관절/피부를 읽습니다. 로봇 제어/천 물리는 변경하지 않습니다.

- 소매: rest mesh의 양 끝 커프를 식별하고 어깨–팔꿈치–손목–손끝 경로가
  커프 다각형을 통과하는지 검사합니다. 두 팔이 같은 구멍에 들어가면 거절합니다.
- 손 노출: 커프가 손목보다 어깨 쪽에 있고 손목·손끝이 천 바깥이어야 합니다.
- 상박 덮임: 해당 소매만 계산용으로 닫고 상박 선분이 그 내부에 들어가는지 검사합니다.
  선분과 삼각형의 교차 구간을 검사하므로 표본 사이의 짧은 덮임도 인정합니다.
  실제 메시에는 면을 추가하지 않습니다. 전체 옷 내부 비율은 과거 진단용으로만 남습니다.
- 목: 커프를 제외한 두 개구부 중 둘레가 작은 collar를 사용합니다. 가슴에서
  목·머리로 이어지는 경로가 collar를 통과하고 가슴은 내부, 머리 관절은 외부이며
  머리 피부가 collar 평면 바깥에 있어야 합니다(5mm 허용).
  평면의 위쪽 방향은 마네킹 가슴→머리 기준으로 고정합니다. 인접 천의 접힘으로
  법선 부호가 뒤집혀 정상 목 노출을 취소하던 문제를 수정했습니다. 판정 metadata의
  `neck_clearance_normal_basis=anatomical_chest_to_head`로 수정 적용을 확인합니다. 골격의 neck 관절은
  정상 neckline 아래에 있을 수 있어 그 관절 자체의 노출을 강제하지 않습니다.
- 찌그러진 개구부의 평면성 한계는 0.6으로 보수적으로 판정합니다.
- 집기 조건은 240Hz, 소매/목/진행도는 20Hz로 측정합니다. 샘플 사이의 파지·상승
  조건 중단도 다음 샘플에 반영합니다. 착의 확인은 연속 0.5초입니다.

현재는 정적인 마네킹과 네 개구부의 단일 티셔츠를 지원합니다. 다른 의복이나
움직이는 사람에는 확장이 필요합니다. 개구부가 심하게 접히거나 천을 관통한
비정상 상태는 기하학적 판정의 한계가 있으며, 모든 착의/오삽입 사례에 대한
정확도가 검증된 공식 경기 판정기는 아닙니다.

## 자신의 rollout 또는 학습 보상에 연결

```python
from Policy.evaluation_live import EvaluationSession

session = EvaluationSession.for_policy(env, '/output/my_policy_evaluation')
obs, info = env.reset(seed=42)
session.start({'mode': 'policy', 'seed': 42})
try:
    while True:
        obs, reward, terminated, truncated, info = env.step(policy(obs))
        if not session.active:
            raise RuntimeError('Evaluation measurement failed')
        if terminated or truncated:
            break
except BaseException:
    session.finish(reason='rollout_exception', valid=False, take_final=False)
    raise
else:
    report = session.finish(reason='rollout_end')
# 반드시 finish 후 env.reset()/env.close() 호출
```

`Phase1TaskEvaluator(measure=..., config=...)`를 `DressingEnv(evaluator=...)`에
연결할 수도 있습니다. 측정 콜백은 위 계약을 반환하고 시간은 환경의
`info['episode_time_s']`를 사용합니다. 이 어댑터만으로 실제 측정 콜백이 자동
설치되지는 않습니다. reward는 원점수 증가량이며 최종 points/s와 다릅니다.
새 측정이 있으면 `info['task']['success']`에 확인된 착의 결과를 제공합니다.
환경 기본 reward는 여전히 0이고 기본 정책 평가 실행기는 학습을 수행하지 않습니다.

회귀 검사:

```bash
python3 scripts/check_phase1_evaluation.py
python3 scripts/check_phase1_live.py
```
