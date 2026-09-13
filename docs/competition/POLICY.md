# 수집 데이터로 정책 학습하고 실행하기

사용 가능한 학습 입력/행동은 [참가 규칙](RULES.md)을 따릅니다.
환경은 시뮬레이션 0.05초마다(20Hz) 공개 관측을 제공하며 정책은 두 로봇의 명령을 동시에 출력합니다.
출력 배열 `(2,9)`는 로봇 2대에 각각 9개 명령을 보낸다는 뜻입니다.
[용어·배열 표기 안내](GLOSSARY.md)에서 관측·액션·학습 구간과 파일 형식을 설명합니다.

## 1. 데이터 로딩

`PolicyDataset`은 완료된 `policy.hdf5`에서 공개 관측과 action만 반환합니다.
아래 예제를 저장소 루트에서 사용할 수 있습니다. NumPy/h5py와 원하는 학습 프레임워크를 준비하세요.

```python
import sys
sys.path.insert(0, 'src/DexGarmentLab')
from Policy.dataset_reader import PolicyDataset

path = 'output/policy_datasets/<실행ID>/policy.hdf5'
dataset = PolicyDataset(path, observation_keys=[
    'overview_rgb', 'robot_0_wrist_rgb', 'robot_1_wrist_rgb',
    'robot_0_head_rgb', 'robot_1_head_rgb',
    'joint_position', 'joint_velocity', 'previous_action',
])
obs, action = dataset[0]
# obs['overview_rgb']: uint8 (256,256,3)
# obs['joint_position']: float32 (26,)
# action: float32 (18,), robot_0의9개 다음 robot_1의9개
print(len(dataset), action.shape)
dataset.close()
```

다른 허용 관측 키나 depth를 추가할 수 있습니다. 감사 파일이나 raw archive를 입력으로 추가하지 마세요.
모방학습은 obs에서 사람이 다음0.05초에 적용한 action을 예측합니다.
모델 구조·전처리·손실함수·학습 프레임워크는 참가자가 선택합니다.

- RGB: uint8 HWC를 모델에 맞게 CHW/float로 변환합니다. 일반적으로255로 나눠 사용합니다.
- Depth: m 단위 float32와 유효 mask를 함께 처리합니다. 무효0을 가까운 물체로 오해하지 않도록 합니다.
- 로봇 상태: 훈련 데이터로 정규화 통계를 계산하고 추론에도 같은 통계를 적용합니다.
- Action: 원래 `[-1,1]` 명세를 유지합니다. 두 로봇/관절 순서를 바꾸지 않습니다.
- 연속 영상은 상관성이 크므로 같은 에피소드의 인접 프레임을 train/validation에 섞지 않습니다.
- 여러 초기 배치와 여러 시도를 수집합니다. 제공된 부분 시연 하나로 완전 착의 학습이 검증된 것은 아닙니다.
- 장기 동작에는 이전 관측/행동을 사용하는 모델도 가능합니다. 에피소드 reset에서 메모리를 초기화합니다.

기본 `rewards=0`은 RL용 착의 보상으로 설계된 값이 아닙니다.
점수·성공 라벨은 시연 선별/분석에 사용하고 내부 정답 정보로 행동 라벨을 만들지 마세요.

## 2. 추론 어댑터: 학습 모델과 시뮬레이터 연결

어댑터는 시뮬레이터의 관측을 모델 입력으로 바꾸고, 모델 출력을 로봇 명령으로 바꾸는 연결 코드입니다.
`load_policy(checkpoint, observation_space, action_space)`가 함수처럼 호출할 수 있는 정책 객체를 반환하도록 Python 파일을 만듭니다.
`checkpoint`는 저장한 모델 가중치 파일이고, `observation_space`와 `action_space`는 입력·출력의 크기와 허용 범위를 설명하는 객체입니다.
평가기에서 전달하는 실행 관측은 CSV/HDF5와 달리 실행용 배열 크기입니다:
관절 `(2,13)`, action `(2,9)`, RGB `(5,256,256,3)`, depth `(5,256,256,1)`.
카메라 순서는 외부, 로봇0손목, 로봇1손목, 로봇0상단, 로봇1상단입니다.
HDF5에서는 카메라별 키로 분리되므로 같은 전처리로 맞추어야 합니다.

```python
# participant/policy.py
import numpy as np

def load_policy(checkpoint, observation_space, action_space):
    # 여기에서 참가자 모델/체크포인트와 학습 때의 전처리를 로드합니다.
    model = load_your_model(checkpoint)

    class Policy:
        def reset(self):
            # recurrent state/action history 등 에피소드 메모리 초기화
            reset_your_model_state(model)

        def __call__(self, obs):
            inputs = preprocess_public_observations(obs)
            prediction = predict_your_action(model, inputs)
            return np.asarray(prediction, dtype=np.float32).reshape(2, 9)

    return Policy()
```

위 `load_your_model` 등은 참가자가 구현할 함수 자리입니다.
Torch 등 모델 의존성은 평가기가 Isaac Sim을 시작한 뒤 어댑터를 로드하므로 어댑터 내부에서 불러올 수 있습니다.
출력 배열 크기·범위·유한성(NaN 또는 무한대가 없는지) 검사를 통과해야 합니다. 모델 출력에 맞는 범위 제한은 참가자 어댑터에서 처리하세요.
정책에는 공개 observation만 제공됩니다. 같은 프로세스의 다른 시뮬레이터 API를 직접 읽어 정보를 우회하지 마세요.

## 3. 로컬 평가

인터페이스가 실행되는지만 먼저 확인하려면 중립 action 예제를 사용합니다.

```bash
./run.sh python /scripts/evaluate_policy.py \
  --policy /project/examples/zero_policy.py \
  --seeds 42 43 --seconds 1 --output /output/evaluation/adapter_check
```

이는 학습된 착의 정책이 아니며0점이어도 정상입니다. 학습한 정책은 다음과 같이 평가합니다.

```bash
./run.sh python /scripts/evaluate_policy.py \
  --policy /project/participant/policy.py \
  --checkpoint /output/checkpoints/policy.pt \
  --seeds 42 43 --seconds 60 --output /output/evaluation/my_policy
```

`--seconds`는 시뮬레이션 에피소드 제한입니다. `--seeds`는 무작위 초기 배치를 선택하는 번호이며 서로 다른 2개 이상을 지정합니다.
관측은 기본 `actor_rgbd`이며 허용 비영상 상태만 쓰는 실험은 `--profile measured_state`로 실행할 수 있습니다.
여러 seed 평가에서는 randomization을 켭니다. `--no-randomization`/`STRETCH4_RANDOMIZE=0`은 이 실행에 사용할 수 없습니다.

결과는 실행별 폴더의 `scores.json`, 측정 trace 및 에피소드별 평가 JSON에 남습니다.
로컬 연습 점수와 최종 심사를 구분하세요. 동일 프로세스에서 환경을 여러 개 동시에 실행하거나 GUI와 GPU 평가를 함께 실행하는 구성은 지원하지 않습니다.

## 제출 준비

코드 버전, 체크포인트, 모델 전처리/관측 키, 라이브러리 버전, 데이터 출처 및 위와 같은 재현 가능한 실행 명령을 준비합니다.
학습/검증 에피소드 구분과 성공 시연 선별 기준도 기록하세요. 상세 제출 일정과 제출처는 주최 측 안내를 따릅니다.
