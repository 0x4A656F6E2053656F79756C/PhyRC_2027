# 참가자 정책 입력·행동 규칙 및 teleop 학습 데이터

이 문서와 [`config/policy_interface.json`](../config/policy_interface.json)이 참가자용
관측·행동의 허용 목록이다. 학습 및 정책 실행에는 아래 공개 관측과 로봇 행동만
사용한다. 환경 설정·물리·형상·마찰·구동 속도·파지 알고리즘은 이 기능에서 바꾸지 않는다.

## 허용 observation

모든 로봇 배열의 순서는 robot_0, robot_1이다. 카메라 순서는 overview,
robot_0_wrist, robot_1_wrist, robot_0_head, robot_1_head이다. 기본 이미지 크기는 256×256.

| 공개 키 | 실행 시 shape | dtype / 의미 |
|---|---|---|
| `rgb` | `(5,256,256,3)` | uint8 RGB. 외부 1개, 손목 2개, 상부 2개 |
| `depth` | `(5,256,256,1)` | float32, 광학 Z 깊이(m), invalid=0 |
| `depth_valid` | `(5,256,256,1)` | bool, 유효 깊이 마스크 |
| `joint_position` | `(2,13)` | float32, 관절 위치(m 또는 rad) |
| `joint_velocity` | `(2,13)` | float32, 관절 속도(m/s 또는 rad/s) |
| `base_pose_world` | `(2,7)` | float32, **로봇** 월드 xyz + wxyz |
| `base_twist_world` | `(2,6)` | float32, 로봇 월드 선속도 xyz + 각속도 xyz |
| `grasp_pose_base` | `(2,7)` | float32, 로봇 base 기준 그리퍼 중심 xyz + wxyz |
| `fingertip_position_base` | `(2,2,3)` | float32, base 기준 두 fingertip 링크 원점(m) |
| `fingertip_origin_distance` | `(2,1)` | float32, 두 링크 원점 거리. 접촉면 사이 간격이 아님 |
| `controller_target` | `(2,9)` | float32, lift/arm/yaw/pitch/roll/grip_pos/base_fwd/base_strafe/base_turn 목표 |
| `gripper_close_command` | `(2,1)` | bool, 닫힘 명령 상태. 잡기 성공 정답이 아님 |
| `simulation_time_s` | scalar | float64, 시뮬레이션 시간(s) |
| `previous_action` | `(2,9)` | float32, 직전 구간에 적용한 정규화 명령, 에피소드 시작은 0 |

외부 카메라와 **로봇 자체**의 월드 pose/twist는 이 트랙에서 허용한다. 로봇 월드
위치는 이상적인 시뮬레이터 localization이며 실제 로봇의 noisy odometry와 다르다.
마네킹·옷·의자의 월드 위치를 허용한다는 뜻은 아니다. 정적 카메라 보정·관절 이름·단위·
행동 스케일은 공개 인터페이스 해석에 사용하는 규격이다. 실제 episode의 spawn seed,
물체 위치, 동적인 카메라 월드 행렬 등 감사 메타데이터는 정책 입력으로 사용하지 않는다.

관측은 일반적인 시각 로봇 정책의 RGB-D 및 proprioception 구성이다. 관절별 인덱스와
좌표계 상세는 [정책 인터페이스](POLICY_INTERFACE.md)를 참고한다.

## 허용 action

정책은 float32 `(2,9)`, 모든 성분이 `[-1,1]`인 명령을 출력한다. HDF5에서는 같은
배열을 robot_0의 9개, robot_1의 9개 순서로 펼친 `(18,)`로 저장한다.

| 열 | 명령 | + 방향 / 실제 속도 환산 |
|---|---|---|
| 0 | base_forward_velocity | 로봇 전방, 값 × BASE_LINEAR_RATE (m/s) |
| 1 | base_left_velocity | 로봇 왼쪽, 값 × BASE_LINEAR_RATE (m/s) |
| 2 | base_yaw_velocity | +Z 기준 반시계, 값 × BASE_ANGULAR_RATE (rad/s) |
| 3 | lift_velocity | 상승, 값 × LIFT_RATE (m/s) |
| 4 | arm_extension_velocity | 팔 신장, 값 × ARM_RATE (m/s), 4개 신축 관절의 총 길이 |
| 5 | wrist_yaw_velocity | 값 × WRIST_RATE (rad/s) |
| 6 | wrist_pitch_velocity | 값 × WRIST_RATE (rad/s) |
| 7 | wrist_roll_velocity | 값 × WRIST_RATE (rad/s) |
| 8 | gripper_command | `< -0.5` 열기, `> 0.5` 닫기, 그 외 이전 개폐 의도 유지 |

기존 속도·가속도·관절 제한·cloth/grasp 제어를 그대로 거친다. action은 **요청 명령**이며
측정된 관절 속도와 같다는 뜻이 아니다. 실제 적용된 제어 목표도 60Hz로 감사 파일에
기록한다. 무효 shape, NaN/Inf, 범위를 벗어난 action은 거부한다.

## 금지된 내부 정보 사용 및 심사

참가자는 학습 데이터 생성, 학습, 추론에서 허용 목록 밖의 시뮬레이터 정답 정보를
사용해서는 안 된다. 예를 들어 옷 정점·입자 좌표/속도, 정답 segmentation, 마네킹·옷·
의자 좌표, 충돌 메시, native grasp의 정점/앵커/성공 상태, 평가기 내부 기하 판정값은
정책 입력 또는 행동 정답 생성에 사용할 수 없다. 내부 옷 정점이나 물체 위치를 읽어
목표점을 만들고 로봇을 추종시키는 제어, 그러한 제어기로 시연을 생성하거나 교사 정책을
학습하여 증류하는 우회 방식도 금지한다. 허용 영상으로 위치를 **추정**하여 행동을
만드는 것은 가능하다. 저장된 raw replay 궤적을 답안처럼 재생하는 것은 정책 실행이 아니다.

**주최 측이 자체 구축·운영하는 검증 프로세스를 통해 금지 정보 사용 또는 평가 환경
우회가 확인된 제출물은 심사에서 제외한다.** 참가자는 검증에 필요한 학습 코드,
데이터 출처·생성 방법, 체크포인트 및 실행 방법을 제출할 수 있어야 한다. 주최 측은
제출 자료와 실행 로그를 검토하고, 별도 초기 상태에서 재평가하여 규정 준수를 확인한다.
단순히 성능이 높다는 이유만으로 위반을 판정하지 않는다.

현재 공개 코드의 구현 범위: 허용 observation 스키마 검사, 데이터 로더의 필드 제한,
평가기의 action 검사와 실행 결과 기록이다. `evaluate_policy.py`의 Python 어댑터는
시뮬레이터와 같은 프로세스에서 실행되므로 **보안 격리나 모든 부정 사용의 자동 탐지를
보장하지 않는다.** 최종 심사용 격리 실행·제출물 감사 체계는 주최 측의 별도 운영 영역이다.
이 문서의 심사 규정을 기존 로컬 실행기가 완전한 탐지 시스템이라는 주장으로 해석하면 안 된다.

기존 `privileged_debug`, raw full recording, `audit.hdf5`, 평가용 JSON은 주최 측의
재현·검증·점수 확인용이다. 정책 학습 입력이나 행동 정답 생성에 사용하지 않는다.
성공/실패·점수 라벨은 시연 선별 및 결과 분석용이며 기본 모방학습 로더는 반환하지 않는다.
기존 저장소의 물체 기하를 직접 읽는 grasp 연구·진단 스크립트는 참가자 규정 준수
baseline이 아니다. 규정 적용 시 허용 관측만 사용하는 코드로 구분해야 한다.

## 수집 실행

```bash
PHYRC_ACCEPT_EULA=1 ./run.sh gui --training-record 1
```

기존 환경 변수 옵션은 그대로 사용할 수 있다. `--training-record 1`은 240Hz 전체
기록도 자동으로 켠다. 일반 `gui` 및 `--full-record 1`만 사용한 teleop의 입력 방식은
바뀌지 않는다. h5py 3.16.0이 필요하며 Docker 의존성에 명시되어 있다. 기존 준비된
런타임에는 변경된 코드 파일을 동기화하거나 설치 절차에 따라 준비해야 한다.

- 기존 키로 조작한다. 두 로봇 동시 제어 가능.
- 학습 모드에서는 입력과 그리퍼 toggle을 **20Hz 경계에서 샘플링**한다. 명령을
  다음 3개 제어 tick(각 1/60초), 12개 물리 tick(각 1/240초) 동안 유지한다.
  중간 키 변경은 다음 경계에 반영되며, 키 이벤트 자체는 원본 기록에 남는다.
  같은 구간에서 두 번 toggle하면 서로 상쇄된다.
- `ESC` 또는 SIGINT/SIGTERM으로 종료하면 진행 중인 최대 1개 정책 구간을 마친 뒤
  저장한다. P reset 또는 저장 슬롯 LOAD는 구간 경계에서 처리하고 새 episode를 만든다.
  SAVE는 episode를 나누지 않는다. F6/F7 수동 평가와 별도로 수집 전체 구간을 자동 평가한다.
- 프로세스 강제 종료, 디스크 오류, 실제 앱이 먼저 닫혀 마지막 구간을 마칠 수 없는 경우
  `complete=false`로 남거나 파일 복구가 필요하다. 불완전 파일은 기본 학습 로더가 거부한다.
  마지막 부분 구간의 상태·이벤트는 full recording에 남으며 정상 20Hz sample로 위장하지 않는다.

이 방식은 정책 action 한 번에 여러 내부 물리 step을 수행하는 고정 주기 제어 방식이다.
기존 60Hz 시연을 평균내거나 단순 subsampling하여 다른 명령 라벨을 만들지 않는다.
기존 archive를 이 형식으로 변환하는 exporter는 이번 기능에 포함되지 않으며, 새 수집부터
동일한 정책 주기를 사용한다. [ManiSkill 제어 문서](https://maniskill.readthedocs.io/en/latest/user_guide/concepts/controllers.html)

## 시간 동기화와 viewport

순서는 `obs[t] 캡처 → action[t] 선택/적용 → 12 physics ticks → obs[t+1] 캡처`다.
5개 카메라는 같은 시뮬레이션 시점에 동기 렌더링하고 PhysX 로봇 상태를 읽는다.
렌더링 전후 full recorder의 tick과 시뮬레이션 시간이 변하지 않았는지 검사한다.
카메라 timestamp와 로봇 timestamp가 다르거나 제어 구간이 정확히 12 tick이 아니면
기록을 오류로 종료한다. 이전 이미지를 복제해서 누락을 채우지 않는다.

사용자가 조작하는 viewport의 카메라 pose/lens를 캡처 시작 시 고정 복사하여, 렌더링
도중 마우스 이벤트가 와도 해당 이미지와 카메라 메타데이터가 어긋나지 않게 한다.
같은 tick의 RGB·카메라 행렬·lens·timestamp를 감사 파일에 저장한다.
viewport RGB는 시작 시 화면 비율을 반영한 폭 256의 별도
render product이며, UI 패널·마우스·collider overlay를 포함하는 화면 녹화가 아니다.
GUI 해상도나 renderer 차이까지 포함한 화면 픽셀 동일성을 보장하지 않는다.
**이 자유 시점 viewport 영상은 허용된 5개 정책 카메라와 별개이고 정책 입력으로 금지한다.**

저장은 압축 손실이 없는 HDF5 LZF이며 RGB는 uint8, 깊이는 float32 m, mask는 bool이다.
쓰기/렌더링이 느리면 시뮬레이션의 실제 시간 진행이 느려진다. 프레임을 버려 속도를
맞추지 않는다. 20Hz는 wall-clock FPS가 아니라 시뮬레이션 시간 주기다. 기존 raw 기록은
모든 240Hz 물리 상태를 계속 보존한다. 배속·물리 파라미터는 변경하지 않는다.

## 파일 및 로딩

```text
output/policy_datasets/<실행ID>/
  policy.hdf5          공개 관측·행동, 모방학습용
  audit.hdf5           viewport, 카메라 행렬, tick, 제어 목표, 점수, seed, 버전 등
  evaluation/<ID>/    episode별 samples.jsonl 및 result.json
output/full_teleop/<동일 실행ID>/
  manifest.json, events.jsonl, scene.usdc, chunk_*.npz
```

`policy.hdf5`는 robomimic의 `data/demo_N/{obs,next_obs,actions,rewards,dones}` 구조를
따른다. `data.attrs.total`, `demo_N.attrs.num_samples`가 샘플 수다. RGB-D는 카메라별
`overview_rgb`, `robot_0_wrist_depth` 등으로 분리한다. 비영상 관측은 1차원으로
펼쳐 저장하며 원래 shape는 contract에 있다. `terminated/truncated`도 저장한다.
기본 reward는 0인 **모방학습용 placeholder**이고 최종 점수와 다르다. 사용자가 종료한
episode는 `truncated=1`, `dones=1`; 성공으로 자동 종료하지 않는다.
robomimic의 온라인 rollout에는 PhyRC 환경 등록/어댑터가 별도로 필요하다.
[robomimic 데이터 구조](https://robomimic.github.io/docs/datasets/overview.html)

감사 파일에는 obs/next_obs에 대응하는 영상·메타데이터, `(3,2,9)` 제어 목표,
3개 control 시작 tick, action 시작/종료 tick, 항목별 점수와 최초 접촉 tick을 저장한다.
점수 열 순서는 pickup, first_sleeve, opposite_shoulder, second_sleeve, overall_dressing이다.
최초 접촉 tick은 **해당 episode 시작 기준**이며 -1은 무접촉이다. action tick은 raw archive
기준이다. 각 episode metadata의 start_tick을 더하면 같은 기준으로 비교할 수 있다.
최종 성공 여부·종료 사유·점수는 episode attribute의 result_json과 평가 JSON에 있다.
성공 라벨은 평가기의 정의이며 실제 완전 착의를 독립적으로 보증하는 라벨은 아니다.

```bash
# Isaac/GPU 없이 파일 검사 (프로젝트 컨테이너의 Python/h5py 사용)
PHYRC_ACCEPT_EULA=1 ./run.sh cpu /scripts/inspect_policy_dataset.py \
  /output/policy_datasets/<실행ID>/policy.hdf5
```

```python
import sys
sys.path.insert(0, '/project/src/DexGarmentLab')
from Policy.dataset_reader import PolicyDataset

dataset = PolicyDataset('/output/policy_datasets/<실행ID>/policy.hdf5')
obs, action = dataset[0]
image = obs['robot_0_head_rgb']   # HWC uint8
robot_actions = action.reshape(2, 9)
# torch.utils.data.DataLoader(dataset, batch_size=32, shuffle=True)로 배치 로딩 가능.
# 영상 CHW 변환/정규화, depth/mask 처리 및 action history 사용은 모델에 맞게 수행.
dataset.close()
```

학습/검증 분할은 프레임이 아니라 episode·초기 상태 단위로 한다. 연속 프레임을 무작위로
양쪽에 나누면 거의 같은 장면이 학습·검증에 동시에 들어간다. 원본 및 감사 파일을
학습 로더에 전달하지 않는다. `PolicyDataset`은 허용 관측과 action만 반환하고 추가
관측 키, 불완전 episode, 다른 카메라·행동 규격을 거부한다.
