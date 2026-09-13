# 정책 학습 데이터 안내

이 문서는 참가자가 수집한 파일을 학습에 연결하는 방법과 숫자의 의미를 설명합니다.
[실제 CSV 예제](../examples/teleop/README.md) · [모든 예제 열 사전](../examples/teleop/columns.csv)

## 수집부터 완료까지

```bash
./run.sh gui --training-record 1
# 조종 중 점수도 보려면:
./run.sh gui --training-record 1 --evaluate 1
```

시작부터 자동 기록합니다. ESC로 종료하면 이미지 변환이 시작되며 `[Dataset export] READY`가 최종 완료 표시입니다.
`capture.json`의 `status=ready`, `complete=true`를 확인합니다. `recording`은 수집 중,
`awaiting_export`는 변환 대기, `incomplete`는 정상 구간을 마치지 못한 상태입니다.
이미지 변환 중에는 원본 상태에서 렌더링하며 새로운 물리 계산으로 시연을 다시 생성하지 않습니다.
따라서 저장 이미지가 당시 모니터를 OS 화면 녹화한 픽셀과 완전히 동일하다는 뜻은 아니지만,
관측 경계의 장면 상태·카메라 자세·시뮬레이션 시각을 동일하게 사용합니다.

`--full-record 1`만으로는 카메라와 동기화된 학습 HDF5가 생기지 않습니다.
학습 목적에는 **`--training-record 1`**을 사용하세요.
기본 조종 후 변환 모드가 권장됩니다. `--training-render live`는 수집 중 RGB-D를 생성하므로 느릴 수 있습니다.

## 시간과 한 행의 의미

```text
obs[t] ── action[t]를 0.05초 적용 ── next_obs[t] (= 같은 에피소드의 obs[t+1])
```

20Hz 정책 명령 하나를 60Hz 제어3회, 240Hz 물리12회 동안 유지합니다.
중간 키 변화는 다음 정책 경계에 반영됩니다. 임의 프레임 건너뛰기나 액션 평균으로 학습 라벨을 만들지 않습니다.
0.05초는 시뮬레이션 시간입니다. 느린 PC에서 실제로0.5초가 걸려도 데이터 간격은0.05초입니다.
깊이·RGB·로봇 상태는 같은 관측 시각에 맞춥니다. 초기 준비 tick 때문에 첫 `simulation_time_s`가0보다 클 수 있습니다.

## HDF5 구조

```text
policy.hdf5
  data/demo_0/
    obs/<공개 관측 키>       (N, ...)
    next_obs/<공개 관측 키>  (N, ...)
    actions                 (N,18), float32
    rewards                 (N,), 기본0
    dones                   (N,), 마지막 종료표시
    terminated, truncated   (N,)
  data/demo_1/ ...           P 초기화 등으로 나뉜 다음 에피소드
```

`N`은 완료된 action 구간 수입니다. `obs`와 `next_obs`가 각각 N개이므로 고유 관측 시점은 연속 에피소드에서 N+1개입니다.
정책 로더는 미완료 파일/에피소드를 거부합니다. `dones=1`은 착의 성공이 아닙니다.
보상0은 모방학습용 기본 placeholder이며 평가 점수와 다릅니다.

기본 구조는 [robomimic 데이터 형식](https://robomimic.github.io/docs/datasets/overview.html)을 따릅니다.
모델별 이미지 전처리와 PhyRC 온라인 rollout 어댑터는 필요합니다. 임의 프레임을 학습/검증으로 섞기보다 에피소드 단위로 나누세요.

## 공개 observation 필드와 좌표계

HDF5는 비영상 배열을 한 줄로 펼칩니다. 예를 들어 `(2,13)` 관절 위치는 `(26,)`입니다.
**robot_0의 모든 값 다음 robot_1의 모든 값** 순서이며 quaternion 순서는 **w,x,y,z**입니다.
월드는 Z 위쪽, 길이는m입니다. base는 로봇 전방X/왼쪽Y/위쪽Z, 카메라 광학축은 오른쪽X/아래Y/전방Z입니다.

| 필드 | 원래 shape | 펼친 열의 의미 / 단위 |
|---|---|---|
| joint_position | `(2,13)` | 로봇당 아래13개 관절 위치, m 또는 rad |
| joint_velocity | `(2,13)` | 같은 순서, m/s 또는 rad/s |
| base_pose_world | `(2,7)` | 로봇당 x,y,z,qw,qx,qy,qz |
| base_twist_world | `(2,6)` | 로봇당 vx,vy,vz,wx,wy,wz (m/s,rad/s) |
| grasp_pose_base | `(2,7)` | 로봇 base 기준 그리퍼 중심 x,y,z,qw,qx,qy,qz |
| fingertip_position_base | `(2,2,3)` | 로봇당 손끝 링크0의xyz, 링크1의xyz (m) |
| fingertip_origin_distance | `(2,1)` | 두 손끝 링크 원점 간 거리(m); 접촉면 사이 간격이 아님 |
| controller_target | `(2,9)` | 아래 목표 열 순서. 실제 관절 위치와 구분 |
| gripper_close_command | `(2,1)` | bool, 닫힘 의도; 잡기 성공 센서가 아님 |
| previous_action | `(2,9)` | 이전 구간의 정규화 action; 시작 시0 |
| simulation_time_s | scalar | 시뮬레이션 시각(s); HDF5/CSV에서는 원소1개 |

현재 예제의 로봇당 관절 순서는 다음과 같습니다. 제출 버전의 관절 이름·단위를 기준으로 해석하세요.

| 로봇 내 인덱스 | 관절 | 위치 단위 |
|---:|---|---|
| 0,1,2 | wheel_0_joint, wheel_1_joint, wheel_2_joint | rad |
| 3 | lift_joint | m |
| 4,5,6,7 | arm_l1_joint, arm_l2_joint, arm_l3_joint, arm_l4_joint | m |
| 8,9,10 | wrist_yaw_joint, wrist_pitch_joint, wrist_roll_joint | rad |
| 11,12 | gripper_finger_left_joint, gripper_finger_right_joint | rad |

예: `joint_position[3]`은 robot_0 리프트, `[16]`은 robot_1 리프트입니다.
베이스 action은 관절 배열의 wheel 각속도를 직접 지정하는 명령이 아닙니다.

`controller_target`의 로봇당 순서:
`lift(m), arm(총 신장 m), yaw(rad), pitch(rad), roll(rad), grip_pos(rad), base_fwd(m/s), base_strafe(m/s), base_turn(rad/s)`.
이 목표의 `base_strafe`는 오른쪽 양수이고, 공개 action `base_left_velocity`는 왼쪽 양수입니다.
이름이 다른 두 열의 부호를 그대로 비교하지 마세요.

### 카메라

| 카메라 ID | 위치 | depth 유효 범위 |
|---|---|---|
| overview | 마네킹 정면을 보는 외부 카메라. 초기 spawn에 맞춰 배치 후 고정 | 0.05–10m |
| robot_0_wrist | 로봇0 손목 | 0.03–3m |
| robot_1_wrist | 로봇1 손목 | 0.03–3m |
| robot_0_head | 로봇0 상단 | 0.05–5m |
| robot_1_head | 로봇1 상단 | 0.05–5m |

로봇 카메라는 각 로봇과 함께 이동합니다. 모든 카메라가 RGB·depth·depth_valid를 제공합니다.
HDF5 키는 `overview_rgb`, `robot_0_wrist_depth`, `robot_1_head_depth_valid` 등입니다.
RGB는 `(256,256,3)` uint8, depth/mask는 `(256,256,1)` float32/bool입니다.
Depth는 광학 Z 거리이며 유클리드 광선 길이가 아닙니다. 무효 depth=0, mask=false입니다.
카메라 행렬·자유 viewport는 감사 정보로, 허용된 이미지 observation과 구분합니다.

## Action: −1, 0, 1이 정상인 이유

키보드는 양/음 방향 키를 누르거나 떼는 입력이므로 이동·회전 action은 −1,0,1입니다.
양/음 키를 동시에 누르면 상쇄되어0이 됩니다. 정책은 `[-1,1]` 안의 연속값도 사용할 수 있습니다.
CSV의 `robot_0.*`9개 다음 `robot_1.*`9개가 HDF5 `(18,)`의 순서입니다.

| 로봇당 열 | 키 | 단위 해석 |
|---:|---|---|
| 0 | base_forward_velocity | 값×BASE_LINEAR_RATE, 전방 m/s |
| 1 | base_left_velocity | 값×BASE_LINEAR_RATE, 왼쪽 m/s |
| 2 | base_yaw_velocity | 값×BASE_ANGULAR_RATE, 반시계 rad/s |
| 3 | lift_velocity | 값×LIFT_RATE, 상승 m/s |
| 4 | arm_extension_velocity | 값×ARM_RATE, 네 신축 관절 총 신장 m/s |
| 5 | wrist_yaw_velocity | 값×WRIST_RATE, rad/s |
| 6 | wrist_pitch_velocity | 값×WRIST_RATE, rad/s |
| 7 | wrist_roll_velocity | 값×WRIST_RATE, rad/s |
| 8 | gripper_command | >0.5 닫기, <−0.5 열기, 나머지 이전 의도 유지 |

실제 예제에 기록된 스케일은 BASE_LINEAR_RATE=0.616, BASE_ANGULAR_RATE=2.86,
LIFT_RATE=1.54, ARM_RATE=1.21, WRIST_RATE=5.5입니다.
이는 요청 명령의 환산값입니다. 관절 제한/가속/물리 반응을 거친 측정 속도는 다를 수 있으며,
각 수집 파일의 `resolved_runtime_rates`를 우선합니다. 대회 환경 스케일을 임의 변경하지 마세요.

예제 actions CSV의 sample247은 robot_1.gripper_command=1입니다. 그 시점에 닫기를 요청했다는 뜻이며,
이후0은 열기가 아니라 이전 닫힘 의도의 유지입니다. robot_0/1 wrist yaw·roll은 이 시연에서 조작하지 않아 모두0입니다.
이 예제 하나가 모든 동작을 학습할 만큼 다양하다는 뜻은 아닙니다.

## CSV 열람 파일

| 파일 | 한 행의 의미 |
|---|---|
| demo_0_actions.csv | action 구간1개. sample, obs/next 시각, start/end tick, 정규화18개 명령 |
| demo_0_obs.csv | 구간 직전의 전체 비영상 공개 관측 |
| demo_0_next_obs.csv | 구간 직후의 전체 비영상 공개 관측 |
| demo_0_applied_targets.csv | 제어1회. sample당 control_substep0,1,2가 있음. 감사용 |
| demo_0_evaluation.csv | 구간 종료 시 점수/분모/상태. 시연 선별·분석용 |
| video_frame_index.csv | 열람 MP4 프레임과 원본 관측/tick 매핑 |
| columns.csv | 위 CSV 모든 열의 정의·단위·예시값 |

CSV는 UTF-8 BOM으로 Excel/LibreOffice에서 열 수 있습니다. `-0.0`은 수치상0입니다.
`sample`은 에피소드 내0부터 시작하는 행 번호, `physics_tick`은 원본 기록의 물리 tick입니다.
`first_contact_tick`은 평가 에피소드 시작 기준이고 −1이면 아직 접촉하지 않았습니다.
`score_time_s`는 최초 접촉부터 **마지막 착의 득점까지**입니다. 영상/전체 에피소드 경과 시간과 구분하세요.

## 학습용과 감사용의 구분

학습은 `policy.hdf5`의 허용 관측/action으로 진행합니다.
`audit.hdf5`, `evaluation/`, raw archive의 물체 정답 상태·카메라 pose·실제 적용 목표는 검증/재현용이며 정책 입력이나 행동 라벨 생성용이 아닙니다.
성공 시연은 감사 metadata의 `success_known=true`와 `success=true`를 확인해 선별합니다.
이 판정은 현재 평가 조건에 따른 달성 이력이며 종료 프레임의 착의 상태를 보증하는 표시는 아닙니다.

## 변환 재시도와 검사

아래 `<실행ID>`를 자신의 기록 폴더 이름으로 바꿉니다.

```bash
# 정상 종료됐고 이미지 생성만 완료되지 않은 기록
./run.sh python /scripts/export_policy_dataset.py /output/full_teleop/<실행ID>

# HDF5의 공개 관측·action 명세 검사
./run.sh cpu /scripts/inspect_policy_dataset.py \
  /output/policy_datasets/<실행ID>/policy.hdf5

# 원본 전체 기록과 HDF5의 관측·action·카메라 대응 검사
./run.sh cpu /scripts/check_deferred_dataset.py \
  /output/full_teleop/<실행ID> /output/policy_datasets/<실행ID>
```

검사 결과 `passed=true`는 저장/동기화 검증 통과이며 착의 성공을 뜻하지 않습니다.
완료된 HDF5는 exporter가 덮어쓰지 않습니다. 기존 파일은 보존하고 필요하면 `--output /output/다른폴더`를 사용하세요.
미완료 원본은 자동 변환 대상이 아닙니다. 수집을 다시 진행하는 것이 기본 경로입니다.
