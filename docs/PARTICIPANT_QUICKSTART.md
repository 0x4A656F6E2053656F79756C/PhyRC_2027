# 참가자: 새 clone에서 빠른 학습까지

현재 release 후보 브랜치는 `feat/policy-learning-env`이다. main에 합쳐지기
전에는 이 브랜치를 지정한다. 저장소가 비공개이므로 GitHub 접근 권한이 필요하다.
Ubuntu/NVIDIA RTX/Docker GPU 환경이 준비되어 있으면 다음으로 시작한다.
호스트 준비가 필요한 경우 [README](../README.md)의 진단·설치 순서를 따른다.

```bash
git clone --branch feat/policy-learning-env \
  git@github.com:0x4A656F6E2053656F79756C/PhyRC_2027.git PhyRC_2027_participant
cd PhyRC_2027_participant
./run.sh doctor

# README의 NVIDIA EULA/privacy 링크를 확인하고 동의한 경우 설정한다.
export PHYRC_ACCEPT_EULA=1
./run.sh build
./run.sh prepare
./run.sh doctor --gpu
./run.sh train-demo
```

`doctor`는 build/prepare 전 이미지·자산 누락을 보고할 수 있다. 해당 준비를
마친 뒤 다시 검사한다. Docker 이미지·고정 의존성·자산 다운로드를 준비하므로
처음 설치 전체가 수 초 안에 끝나지는 않는다. 준비된 환경의 학습 예제는
작은 실제 rollout을 이용하며 실행 시간은 `output/train-demo/report.json`에 나온다.

2026-09-10, RTX 5080 16GB에서 새 GitHub clone으로 위 과정을 검증했다.
프로젝트 runtime/자산/캐시를 복사하지 않았고, 기존 호스트와 Docker 이미지
레이어는 재사용했다. 같은 코드 `d152661`에서 측정한 결과는 다음과 같다.

| 실행 | 시작부터 학습·평가 완료까지 |
|---|---:|
| 새 clone의 첫 학습 실행(첫 RTX 셰이더 컴파일 포함) | 약 6분 49초 |
| 캐시 생성 후 재실행 | 약 1분 50초 |

두 실행 모두 22cm 목표의 마지막 8스텝 평균 오차가 학습 전 14.69cm에서
학습 후 **2.09mm**로 줄었다. 이 시간은 build/prepare 다운로드 시간을 포함하지
않으며, 다른 컴퓨터의 실행 속도를 보장하지 않는다.
[새 clone 검증 기록](verification-results/participant-clone.json)에 수치를 남겼다.

추가 센서/API 검증은 `./run.sh policy-smoke`로 수행한다. 세 카메라의 PNG와
RGB-D NPZ, 상세 검증 JSON은 `output/policy-smoke/`에 저장된다.

## 학습 예제의 결과

`train-demo`는 실제 두 로봇·사람·셔츠 장면을 실행한 다음:

1. 학습 전 신경망으로 로봇 0의 lift 높이 22cm 목표를 평가한다.
2. 12cm와 30cm 목표의 피드백 제어기로 실제 시범 64개를 수집한다.
3. 작은 PyTorch 정책을 500회 업데이트한다.
4. 같은 seed의 22cm 목표를 다시 실행해 실제 높이 오차를 비교한다.

보상 기반 강화학습이 아닌 작은 **모방학습(behavior cloning)** 예제다.
기본 `measured_state` 관측의 실제 lift와 명령 목표를 사용한다. RGB-D 학습,
소매 끼우기나 완전한 옷 입히기 성공을 학습한 모델은 아니다.

- `policy.pt`: 학습 전후 가중치와 입출력 의미
- `trajectories.npz`: 시범 및 학습 전후 실제 rollout
- `report.json`: loss, 검증 목표 오차, 실행 시간, 통과 여부

```bash
./run.sh train-demo --seed 7 --epochs 500
cat output/train-demo/report.json
```

자기 정책은 [정책 인터페이스](POLICY_INTERFACE.md)의 예제를 `scripts/my_policy.py`로
저장하고 `./run.sh python /scripts/my_policy.py`로 실행한다.
환경은 Gymnasium `Dict` 관측과 `(2,9)` Box action이다. 학습 라이브러리에 따라
관측 선택·영상 전처리와 action flatten/unflatten wrapper를 추가한다.
일반 PPO 예제를 설치 없이 바로 실행할 수 있는 벡터 환경은 아직 제공하지 않는다.
