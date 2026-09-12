# Phase 1 평가 함수 — 항목별 독립 채점 v4

현재 규칙은 제공된 `/home/seoyul/Downloads/PhyRC_proposals.pdf` 6쪽 IX.E.a를
바탕으로 **2026-09-12 짧은 소매/집기 수정과 2026-09-13 최초 접촉 기준 시간**을
적용했습니다. 이후 요청에 따라 5점 단계 3개와 Overall dressing 30점을 각각
독립 판정·출력하며, 현재 `scoring_revision=separate-dressing-items-v4`입니다.
현재 구현과 실행 방법은 이 문서 및 저장소의 평가/기록 스크립트에 포함되어 있습니다.

## 점수와 이번 변경

| 항목 | 점수 |
|---|---:|
| 실제로 잡은 부분을 들어 올려 같은 그리퍼로 연속 3초 유지 | 5 |
| 첫 번째 손목의 소매 삽입 | 5 |
| 반대쪽 어깨를 넘어감 | 5 |
| 두 번째 소매 삽입 | 5 |
| Overall dressing: 첫 번째 팔 n, 두 번째 팔 m | 10 × n + 20 × m (최대 30) |

- **양쪽 손이 서로 다른 소매 밖으로 나오고, 머리가 목 구멍 밖으로 나와
  목에 걸린 정상 위치가 0.5초 연속 확인되면 Overall dressing 항목을 30/30점으로 확정합니다.**
  앞서 요청한 짧은 소매 만점 예외를 이 30점 항목에 유지합니다. 실제 n/m 측정값을
  1로 바꾸지 않으며, `full_dressing_override`와 `measured_coverage_points`로 구분합니다.
  세 개의 5점 항목은 각각 손목 삽입/반대쪽 어깨 통과/다른 소매 삽입 증거로만
  부여합니다. 완전 착의 표시만으로 반대쪽 어깨 통과 5점을 자동 부여하지 않습니다.
- 집기 5점은 별도이며, 집기까지 달성하면 총 50/50점입니다.
- 단계 점수와 팔별 최고 진행도는 한 평가 안에서 유지합니다. 측정 흔들림이나
  옷을 다시 벗기는 동작으로 이미 얻은 원점수를 회수하지 않습니다.
  완전 착의가 한번 확인되면 해당 점수도 유지됩니다. 이는 최종 상태의 품질만
  채점하던 이전 방식과 다른, 달성 이력 기준입니다.
- `final_score = raw_points / task_time_s` (points/s)는 유지합니다.
  **task_time_s는 옷과 마네킹 충돌 메시가 최초 접촉한 tick부터 종료까지**입니다.
  원점수가 같더라도 시간이 늘어나면 이 비율은 내려갑니다.
  터미널은 pickup / dressing / TOTAL 원점수와 rate를 따로 표시합니다.
- 여러 초기 상태에서는 seed별 points/s의 산술평균을 사용합니다.
  여러 제출을 한 파일에서 채점하면 제출 전체 평균의 최댓값을 선택합니다.
  평균 방식과 기하학적 판정 허용치는 구현 정의이며 PDF가 확정한 규칙은 아닙니다.

### 항목별 결과 읽기

콘솔의 진행/최종 출력과 `result.json`의 `result.score_items`에는 다음 다섯 항목이 있습니다.

| 키 | 항목 | 만점 |
|---|---|---:|
| `pickup` | 옷 집기·들기 유지 | 5 |
| `first_sleeve` | 첫 소매에 손목 넣기 | 5 |
| `opposite_shoulder` | 옷 일부가 반대쪽 어깨 관절을 넘어감 | 5 |
| `second_sleeve` | 다른 소매 입히기 | 5 |
| `overall_dressing` | 팔 덮임: 10×n + 20×m | 30 |

각 항목에는 `points`, `max_points`가 있으며, 5점 항목에는 `achieved`와 획득 시각도
있습니다. Overall dressing에는 `n`, `m`, `first_arm_points`(/10),
`second_arm_points`(/20), 완전 착의 예외 적용 여부가 별도로 있습니다.
n/m은 기존처럼 각 팔의 최고 측정 진행도이며, 순간 덮임은 `current_arm_coverage`입니다.
원점수는 이 다섯 항목의 합(최대 50)이고, points/s는 합계/접촉 이후 시간입니다.

**v4의 `overall_dressing_points`/`max_overall_dressing_points`는 30점 항목만 뜻합니다.**
예전 45점 묶음을 읽던 외부 코드는 `score_items` 또는 이 새 의미에 맞게 수정해야 합니다.
`breakdown`의 10점/20점 하위 항목은 기존 이름을 유지하며, 이를 Overall 점수에 다시
더하면 중복입니다. `schema_version=phase1-live-v4` 또는 `phase1-scores-v4`로 구분합니다.
샘플 입력 형식은 접촉 시각을 담는 `phase1-measurements-v3` 그대로입니다.

### 최초 접촉부터 시간 측정

- 선택한 연속 평가 구간의 모든 physics tick(240Hz)을 검사하여 첫 접촉을 고정합니다.
  `(종료 tick - 최초 접촉 tick) × physics_dt_s`가 points/s의 분모입니다.
  접촉 뒤 다시 떨어져도 시간은 계속 흐릅니다. 준비 시간과 replay 배속은 제외합니다.
- 접촉 전에 얻은 집기 점수와 3초 유지 이력은 그대로 보존합니다.
  점수·진행도·목/소매 판정 조건을 바꾸지 않았습니다.
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
  접촉한 순간에 끝나도 양의 경과 시간이 없어 N/A입니다. 준비 시간을 분모로 쓰거나
  무한대 점수를 만들지 않습니다. 이 경우 원점수와 진단 결과는 저장하지만, 해당
  seed를 제외해 평균을 높이지 않고 제출의 points/s 집계를 거절합니다.
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
PHYRC_ACCEPT_EULA=1 ./run.sh gui
# 모든 3D 동작 기록도 함께 사용하려면:
PHYRC_ACCEPT_EULA=1 ./run.sh gui --full-record 1
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
PHYRC_ACCEPT_EULA=1 ./run.sh replay output/full_teleop/<실행 ID> \
  --evaluate /output/evaluation/replay
```

기본은 전체 구간이며, `--start-tick`/`--end-tick`으로 평가 구간을 선택할 수 있습니다.
화면 replay에서는 `--evaluation-start-tick`/`--evaluation-end-tick`입니다.
실시간 평가와 비교하려면 구간과 평가 소스 버전이 같아야 합니다.
reset/LOAD가 포함된 구간은 무효이며, 이전 v1 기록은 앵커 정보가 부족하여 정확한
전체 평가를 지원하지 않습니다. 새로 기록해야 합니다.
저장 위치와 상세 사용법은 [전체 기록 안내](FULL_TELEOP_RECORDING.md#저장된-물리-상태로-평가하기)를 참고하세요.

## 학습한 정책 평가

```bash
# 중립 행동으로 실행 경로 확인
PHYRC_ACCEPT_EULA=1 STRETCH4_RANDOMIZE=1 ./run.sh python \
  /scripts/evaluate_policy.py --zero-policy --profile measured_state \
  --seeds 42 43 --seconds 5

# TorchScript 모델 예시: 실제 파일 경로로 교체
PHYRC_ACCEPT_EULA=1 STRETCH4_RANDOMIZE=1 ./run.sh python \
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
접촉이 없거나 접촉 직후 종료한 seed는 N/A이며 평균 점수를 만들지 않습니다.

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

새 입력은 `schema_version=phase1-measurements-v2`이며 다음과 같습니다.
각 제출에는 중복되지 않는 seed가 최소 2개 필요하고 제출끼리 seed 집합이 같아야 합니다.

```json
{
  "schema_version": "phase1-measurements-v3",
  "submissions": [{
    "submission_id": "policy-v1",
    "episodes": [{"seed": 42, "samples": []}, {"seed": 43, "samples": []}]
  }]
}
```

v3 샘플 예시 (`physics_tick`/`physics_dt_s`/`first_contact_tick`은 정수 시간 정밀도를 보존하는 추가 필드):

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
  "dressing_complete": false
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
새 접촉 기준 점수와 혼합 비교하면 안 됩니다. 새 데모는 접촉 시각 0인 합성 v3 예제입니다.
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
- 부분 덮임: 계산용으로 네 개구부를 닫아, 팔 중심선 길이에 균등한 40개 표본이
  천 내부에 있는 비율을 측정합니다. 실제 메시에는 면을 추가하지 않습니다.
- 목: 커프를 제외한 두 개구부 중 둘레가 작은 collar를 사용합니다. 가슴에서
  목·머리로 이어지는 경로가 collar를 통과하고 가슴은 내부, 머리 관절은 외부이며
  머리 피부가 collar 평면 바깥에 있어야 합니다(5mm 허용). 골격의 neck 관절은
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
