# 옷 입히기 정책 인터페이스 — 0.2.0

두 Stretch4와 FEM 티셔츠 장면에 Gymnasium `reset/step`, 실제 로봇 상태,
RGB-D 센서를 연결한 실험용 환경이다. 명세는
[`config/policy_interface.json`](../config/policy_interface.json), 구현은
[`Policy/`](../src/DexGarmentLab/Policy/)에 있다.

기존 teleop와 동일한 구동기·천 제어·native grasp를 사용한다. 이후 물리 패치가
정책 데이터 형태와 얽히지 않도록 상태 읽기, 스키마, 센서, 환경 어댑터를 분리했다.
착의 성공 판정과 보상은 별도 evaluator로 주입한다. 기본 보상은 0이고
성공 종료는 없으며, 기본 400스텝(20초)에서 시간 제한 종료한다.

## 2026-09-11 복원 범위

`e409213`의 Gymnasium·관측·학습 예제를 현재 물리에 연결했다.
과거 RGB-D 검증 수치는 당시 결과이며, 현재 실행 결과와 구분해야 한다.
현재 옷 집기 실험과 실행 방법은 [GRASP_LEARNING_20260911.md](GRASP_LEARNING_20260911.md)를 참고한다.
`DressingEnv(initial_slot="/output/.../slot_F1.npz", profile="measured_state")`는
저장된 사람·의자 배치를 물리 초기화 전에 적용하고, 매 에피소드에 읽기 전용으로
상태를 복원한다. 마찰은 현재 코드 값을 쓰며 PhysX 내부 이력의 비트 단위 재현은 보장하지 않는다.

## 참가자가 실행하기

새 clone 설치는 [README](../README.md)를 따른다.
이미 준비된 checkout에서는 다음 두 명령으로 검증·학습한다.

```bash
export PHYRC_ACCEPT_EULA=1
./run.sh policy-smoke
./run.sh train-demo
```

학습 예제는 실제 장면에서 로봇 0의 **lift 높이 제어**를 모방학습한다.
64개 실제 시범 transition → 작은 PyTorch 신경망 → 별도 목표에서 실제 rollout
순서다. 완전한 옷 입히기 정책이나 RGB-D 기반 학습 성능을 뜻하지 않는다.
`output/train-demo/`에 가중치, 학습 전후 궤적, 수치 결과가 저장된다.

연구자 스크립트는 프로젝트의 `scripts/` 폴더에 넣고 다음처럼 실행한다.

```bash
./run.sh python /scripts/my_policy.py
```

```python
import sys
sys.path.insert(0, '/project/src/DexGarmentLab')
import numpy as np
from Policy.environment import DressingEnv

env = DressingEnv(profile='actor_rgbd', resolution=(256, 256),
                  max_episode_steps=400, render_mode='rgb_array')
# Torch는 Isaac 애플리케이션이 시작된 다음 import한다.
obs, info = env.reset(seed=42)
action = np.zeros(env.action_space.shape, dtype=np.float32)
action[0, 3] = 0.1  # 현재 기본값에서 robot_0 lift 속도 0.126 m/s 요청
obs, reward, terminated, truncated, info = env.step(action)
image = env.render()  # 마지막 관측의 overview RGB; 물리 진행 없음
# 여기서 결과를 먼저 저장한다. Isaac close()는 프로세스를 즉시 종료할 수 있다.
env.close()
```

Isaac 애플리케이션은 프로세스 전역이다. **프로세스당 환경 하나**를 사용하고,
학습 중 episode는 같은 인스턴스의 `reset()`으로 시작한다. close 후 재생성,
한 프로세스의 벡터 환경, GUI와 학습의 동시 실행은 지원하지 않는다.
기본은 headless RTX 렌더링이며 GPU가 필요하다. `measured_state` 프로필은
카메라를 생성하지 않아 작은 제어 실험에 더 빠르다.

## 관측과 좌표계

중앙 정책이 두 로봇의 action을 동시에 출력한다. 카메라 순서는
`overview`, `robot_0_wrist`, `robot_1_wrist`이다. 기본 H=W=256이며
`resolution=(width,height)` 또는 별도 config 파일로 바꾼다.

| 관측 키 | 기본 shape | dtype / 의미 |
|---|---|---|
| `joint_position`, `joint_velocity` | 각각 `(2,13)` | float32, 실제 관절 위치·속도 |
| `base_pose_world` | `(2,7)` | float32, xyz + wxyz quaternion |
| `base_twist_world` | `(2,6)` | float32, 선속도 xyz + 각속도 xyz |
| `grasp_pose_base` | `(2,7)` | float32, base 기준 grasp 중심 pose |
| `fingertip_position_base` | `(2,2,3)` | float32, 왼쪽·오른쪽 fingertip 링크 원점 |
| `fingertip_origin_distance` | `(2,1)` | float32, 두 링크 원점 거리(m) |
| `controller_target` | `(2,9)` | float32, 실제 상태와 구별되는 제어 목표 |
| `gripper_close_command` | `(2,1)` | bool, 닫힘 의도이며 잡기 성공 센서가 아님 |
| `simulation_time_s` | scalar | float64, 물리 시간(s) |
| `rgb` | `(3,H,W,3)` | uint8, RGB |
| `depth` | `(3,H,W,1)` | float32, 광학축 Z 깊이(m), invalid=0 |
| `depth_valid` | `(3,H,W,1)` | bool, 유한하고 clipping 범위 내인 깊이 |
| `previous_action` | `(2,9)` | float32, 이번 관측까지 적용한 action; reset 시 0 |

`measured_state`는 표의 RGB/depth/depth_valid/previous_action을 제외한다.
`actor_rgbd`는 전체를 제공한다. 이미지가 없으면 0 영상으로 대신하지 않고 오류를 낸다.
배열 shape·dtype·유한성·범위를 검사하며 Gymnasium Dict/Box 공간도 제공한다.

월드는 오른손 좌표계, +Z 위, 길이는 m이다. 로봇 base는 +X 전방, +Y 왼쪽,
+Z 위이다. 모든 공개 quaternion은 **wxyz**이고 PhysX의 xyzw에서 변환한다.
카메라 광학 좌표는 +X 오른쪽, +Y 아래, +Z 전방이다.

base/grasp/fingertip은 실제 PhysX 텐서에서 읽는다. base 월드 pose는 이상적인
시뮬레이터 위치 측정이며 noisy odometry가 아니다. USD의 정적 human/chair
행렬은 row-vector convention이고, 카메라 info 행렬은 명시적으로 column-vector이다.

### 관절과 그리퍼

실제 관절 이름·인덱스·단위·한계는 `info['state']['robots'][i]['joints']`에서 확인한다.
인덱스를 연구 코드 전체에 복사하지 말고 이름으로 찾는다.

| 현재 인덱스 | 관절 | 단위 / 실제 한계 |
|---|---|---|
| 0–2 | `wheel_0_joint` … `wheel_2_joint` | rad, 연속 회전 |
| 3 | `lift_joint` | m, 0–1.2 |
| 4–7 | `arm_l1_joint` … `arm_l4_joint` | m, 각각 0–0.13, 총 0.52 |
| 8 | `wrist_yaw_joint` | rad, 약 −1.135–4.276 |
| 9 | `wrist_pitch_joint` | rad, 약 −4.276–1.135 |
| 10 | `wrist_roll_joint` | rad, 약 −1.135–4.276 |
| 11–12 | left/right finger joint | **rad**, 0–0.5 |

finger q는 선형 aperture(m)가 아니다. fingertip 원점 간 거리도 접촉면 안쪽
틈새 폭이 아니다. 접촉력/촉각 센서는 아직 없으며 `grasp_attached`와
`native_attachment_present`는 privileged 시뮬레이터 진단 정보다.

`controller_target` 열은 lift, arm(4관절 합), yaw, pitch, roll, grip_pos,
base_fwd, **base_strafe(기존 제어기의 오른쪽 양수)**, base_turn 순서다.
원래 제어기 표기를 보존하며, 공개 action의 왼쪽 양수와 부호가 다름에 유의한다.

## RGB-D 센서

overview는 고정 월드 카메라, 손목 두 대는 실제 `gripper_camera_link`를 따라간다.
초기 에셋의 이 링크는 +X가 위, −Y가 fingertip 쪽이다. config의 mount-local
`eye_mount_m`, `target_mount_m`, `up_mount`로 한 번 정한 외부변환을 유지한다.
그리퍼나 물체를 매번 추적하도록 시선을 바꾸지 않는다.

기본 HFOV 70도, overview clip 0.05–10m, wrist clip 0.03–3m이다.
각 카메라 info에 다음을 제공한다.

- `intrinsics`: pinhole K, fx=fy, cx=W/2, cy=H/2
- `world_from_optical_column_vectors`: 광학 좌표 → 월드 4×4 행렬
- `mount_from_usd_camera_column_vectors`: 고정 장착 외부변환
- `resolution_wh`, `clip_m`, `timestamp_simulation_s`

RGB와 `distance_to_image_plane` RTX annotator를 같은 물리 상태에서 읽는다.
`World.render()`로 물리 상태를 렌더 장면에 반영한 뒤 Replicator의
`step(delta_time=0, wait_for_render=True)`로 해당 capture 완료를 기다린다.
센서 읽기 전후 물리 시간이 달라지면 실패한다.
shader 준비 때문에 첫 읽기는 더 오래 걸린다. 시간표시는 벽시계가 아니다.
센서는 현재 장면의 시야·가림을 그대로 보여 주며, 최초 손목 시야에서
티셔츠가 보인다고 가정하지 않는다. 연구자가 카메라 장착값을 변경할 수 있다.

## Action과 실행 시간

`float32[2,9]`, 모든 값은 [-1,1]. NaN/Inf, 잘못된 shape/dtype/범위는
물리를 진행하기 전에 거부한다. 순서는 `/World/Stretch4`, `/World/Stretch4_2`이다.

| 열 | 정규화 action | 기본 최대 크기 |
|---|---|---|
| 0 | base 전진 속도 | 0.504m/s |
| 1 | base 왼쪽 속도 | 0.504m/s |
| 2 | base yaw 속도, +Z 기준 반시계 양수 | 2.34rad/s |
| 3 | lift 속도 | 1.26m/s |
| 4 | telescoping arm 전체 신장 속도 | 0.99m/s |
| 5–7 | wrist yaw/pitch/roll 속도 | 각각 4.5rad/s |
| 8 | gripper 의도 | <−0.5 열기, >0.5 닫기, 나머지 유지 |

실제 스케일은 실행 시 기존 `STRETCH4_*` 설정을 읽는다. 목표 위치는 관절
한계로 제한되고 기존 천 하중 제약·base 가속도 제한이 적용된다. 따라서
요청한 속도와 측정된 운동이 다를 수 있다. `controller_target`과 실제 q를
함께 기록한다. wheel 회전은 base 운동 중 측정할 수 있지만 **현재 base
구동은 root-wrench 속도 servo**이며 개별 wheel torque/velocity action은 없다.

0 action은 현재 관절 목표와 그리퍼 의도를 유지하고 base 요청 속도를 0으로
한다. base는 가속도 제한에 따라 감속한다. 반복 close는 toggle되지 않는다.
손가락이 닫힌 뒤 기존 settle 지연을 거쳐 잡기를 시도하며, 범위 내 천이
없으면 close 상태여도 attachment는 없다.

한 `step()`은 60Hz 제어 3틱, 기본 240Hz 물리 12스텝, **0.05초**를 진행한다.
physics Hz를 바꾸려면 60의 정수배여야 한다. wall-clock 실행 속도와는 무관하다.
현재 어댑터의 policy/control 주기는 고정이며 config가 다른 값을 요구하면 거부한다.

## Reset, 종료와 실패

`initial_slot`을 지정하지 않은 기본 `reset(seed=42)`는 seed 42의 배치를 직접 재현한다. `seed=None`은 Gym RNG에서
다음 seed를 뽑고 info에 기록한다. human 중심 반지름 10cm 원판과 yaw −30~+30도에서
human과 chair를 하나의 강체 변환으로 함께 배치한다. 누적 회전·이동을 하지 않는다.
같은 episode seed의 별도 RNG stream에서 네 박스 중 하나를 균등하게 고르고
티셔츠를 그 상판 중심 위에 둔다. 옷의 방향·모양·기존 0.2m 스폰 여유 높이는
유지하며, 박스 안의 추가 XY jitter는 넣지 않는다. `info['garment_spawn']`에
선택한 0-based table index, prim path, seed, 박스 크기와 스폰 위치를 기록한다.
매 reset은 고정 초기 옷 템플릿에서 새 박스까지의 평행이동을 다시 계산한다.
GUI 실행의 옷 seed는 `STRETCH4_GARMENT_SPAWN_SEED`, 없으면
`HUMAN_SPAWN_SEED`, 둘 다 없으면 새 난수 seed를 쓴다. 사람의 기존 seed 결과는
변하지 않는다. GUI의 P는 해당 실행의 초기 박스를 유지하고 학습 reset은 다시 선택한다.
기존 checkpoint는 옷의 실제 world-space 위치를 저장·복원하므로 계속 사용할 수 있다.

reset은 physics callback을 해제하고 native attachment를 제거한 뒤 물리 뷰를
재생성한다. 초기 로봇/천 상태, 속도, 제어 의도와 이력을 초기화하고 새 배치의
body contact guard를 다시 만든다. 기본 90 제어틱(1.5초)을 중립 상태로 진행한다.
reset 반환 전에 base 선속도 ≤0.05m/s, finger open 오차 ≤0.03rad를 확인한다.
미달하면 reset 실패로 보고하며 `settle_ticks`를 늘리거나 물리를 점검한다.
이는 전체 천이 완전히 정지했다는 판정이 아니다. 측정 결과는 `reset_settling`에 있다.

`info['episode_time_s']`는 reset의 settling 이후부터 시작하고,
`simulation_time_s`는 실제 물리 clock이다. 기본 reset은 사용자 F슬롯을 사용하지 않는다.
`initial_slot`을 명시하면 해당 파일을 읽기 전용으로 복원하며, 원본 파일에 저장하지 않는다. seed는 배치를 재현하며 천 초기 복원은 1e-7m 이내인지 검사한다.
같은 GPU에서도 FEM settling 후 천 vertex가 약 2.2mm 달라질 수 있다.
검증은 5mm 이내를 허용하며 bitwise 천 궤적 재현을 약속하지 않는다.

`step`은 `(obs, reward, terminated, truncated, info)`를 반환한다.
종료 후에는 reset이 필요하다. 잘못된 action은 그대로 거부하고,
진행 중 비유한 물리 상태·센서 실패·evaluator 예외는 episode를 무효화하는
예외로 보고한다. 숨은 checkpoint 복구나 자동 reset으로 transition을 이어붙이지 않는다.

## 교체 가능한 보상과 성공 평가

```python
class TaskEvaluator:
    def reset(self, initial_info):  # 선택 사항: episode별 이력 초기화
        pass

    def __call__(self, previous_obs, action, next_obs, info):
        # 연구자가 검증한 garment landmark / 착의 / 안전성 지표를 계산한다.
        reward = 0.0
        terminated = False
        return reward, terminated, {'success_evaluated': False}

env = DressingEnv(evaluator=TaskEvaluator())
```

evaluator에 넘기는 `info['state']`에는 garment centroid/AABB와 실제 로봇·grasp
진단이 있다. 전체 천 vertex/velocity/topology는 `Policy.state.snapshot()`의
두 번째 반환값에서 별도로 얻을 수 있다. actor 관측에 몰래 섞지 않는다.
새 작업에서는 셔츠 opening/소매 landmark, 입힘 진행률, 관통·과도한 변형,
잡기 안정성을 먼저 검증한 뒤 보상·성공 기준을 정해야 한다.

`Policy.contract`와 pose helper는 Isaac 없이 numpy로 읽을 수 있어 데이터셋 도구나
차후 로봇/센서 패치가 물리 앱을 부팅할 필요가 없다. 연구 결과에는 schema version,
코드 commit, config, runtime rates, seed, 카메라 보정값을 함께 남긴다.

## 검증과 현재 범위

`./run.sh policy-smoke`는 실제 GPU에서 shape/dtype, RGB-D 유효성, 알려진 물체의
metric depth와 센서 갱신, 정확한 action 시간, 모든 연속 action 채널, 반복 gripper
의도, reset 배치 재현, 시간 제한과 evaluator 종료를 검사한다.
`python3 scripts/check_policy_contract.py`는 CPU에서 스키마·좌표·단위 변환을 검사한다.
이전 결과는 [검증 기록](VERIFICATION.md), 현재 복원 후 결과는
[학습 복원 기록](GRASP_LEARNING_20260911.md)을 참고한다.

Gymnasium 계약은 [공식 Env API](https://gymnasium.farama.org/api/env/),
렌더 센서는 [Isaac Sim 카메라 문서](https://docs.isaacsim.omniverse.nvidia.com/latest/sensors/isaacsim_sensors_camera.html)를 참고했다.

## Current restored-environment verification (2026-09-11)

The full GPU smoke passed at 128×128 with current geometry/friction. A moved
depth probe measured 0.9000001/1.2000000 m, eight actions advanced 0.40000002 s,
repeated-seed joint differences were zero and settled cloth differences were
at most 0.9995 mm. Controls, invalid input, reset and termination/truncation
checks passed. See [the result](verification-results/policy-smoke-20260911.json).
This validates the environment interface, not arm insertion or a trained RL agent.
