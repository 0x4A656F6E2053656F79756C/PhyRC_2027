# 설치와 첫 실행

이 가이드는 **Ubuntu Desktop 22.04/24.04 x86-64, 로컬 모니터, NVIDIA RTX GPU**에서 Docker로 실행하는 경로입니다.
Isaac Sim은 이미지에 포함되므로 호스트에 별도 설치하지 않습니다.
실제로 확인한 장비와 새 체크아웃 검증 범위는 [검증 결과](VERIFICATION.md)에 있습니다.

## 저장소에 무엇이 포함되나요?

시뮬레이션 실행 코드, 두 로봇의 키보드 조종, 학습 데이터 수집·변환, 정책 실행·평가 코드와
로봇·마네킹·티셔츠의 원본 자산이 포함되어 있습니다.
Isaac Sim 본체와 Python 패키지는 `build`에서, 추가 텍스처·재질은 `prepare`에서 내려받습니다.
다운로드 자산은 저장소에 지정된 해시로 파일이 맞는지 확인하고, 실행용 장면은 제공된 코드로 생성합니다.
따라서 기존 개발자의 실행 폴더를 따로 복사할 필요는 없습니다.
참가자가 학습할 모델과 수집할 시연은 별도로 준비합니다.

## 준비 사항

- NVIDIA RTX GPU와 호환 드라이버. 검증에 사용한 장비는 RTX5080 16GB, RAM64GB, Ubuntu22.04입니다.
- 프로젝트 준비 여유로 RAM32GB 이상, VRAM16GB급, SSD100GB 이상의 여유를 권장합니다. 장시간 RGB-D 시연을 저장하려면 추가 공간이 필요합니다.
- NVIDIA의 [Isaac Sim 6.0.1 요구사항](https://docs.isaacsim.omniverse.nvidia.com/6.0.1/installation/requirements.html)을 확인하세요. 드라이버는 자신의 GPU와 호환되는 버전을 사용합니다.
- 인터넷, 저장소 접근 권한, 패키지 설치를 위한 관리자 권한이 필요합니다.
- 아래 GUI 경로는 로컬 Linux 데스크톱용입니다. CPU만 있는 PC, WSL/원격 데스크톱 GUI 경로는 이 가이드의 검증 범위가 아닙니다.

## 1. 기본 도구와 NVIDIA 드라이버

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates gnupg python3 xauth util-linux unzip
nvidia-smi
```

`nvidia-smi`가 없거나 실패하면 Ubuntu의 추가 드라이버 도구 또는 [NVIDIA 설치 안내](https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/)로 먼저 드라이버를 구성하고 재부팅하세요.
GUI는 모니터가 연결된 데스크톱 세션에서 실행합니다. 로그인 시 Ubuntu on Xorg를 선택하면 Xauthority 인증 경로를 사용할 수 있습니다.

## 2. Docker Engine

이미 설치되어 있다면 `docker run --rm hello-world`를 먼저 확인합니다.
새 설치는 [Docker 공식 Ubuntu 안내](https://docs.docker.com/engine/install/ubuntu/)를 따르세요. 기본 명령은 다음과 같습니다.

```bash
sudo install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo tee /etc/apt/keyrings/docker.asc >/dev/null
sudo chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' \
  "$(dpkg --print-architecture)" "$VERSION_CODENAME" \
  | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

로그아웃 후 다시 로그인하여 그룹 변경을 적용한 뒤:

```bash
docker run --rm hello-world
```

프로젝트 명령은 일반 사용자로 실행합니다. Docker 그룹 접근은 높은 권한을 부여하므로 공유 장비에서는 관리자 지침을 따르세요.

## 3. NVIDIA Container Toolkit

[공식 설치 안내](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)에 따라 Docker GPU 실행을 구성합니다.

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor --yes --output /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's|deb https://|deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://|g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
docker run --rm --gpus all ubuntu:24.04 nvidia-smi
```

마지막 명령에서 GPU가 표시되어야 합니다. Docker 재시작은 다른 컨테이너에 영향을 줄 수 있으므로 공유 장비에서는 관리자와 일정을 맞춥니다.

## 4. 저장소 복제

```bash
git clone \
  https://github.com/0x4A656F6E2053656F79756C/PhyRC_2027.git
cd PhyRC_2027
./run.sh doctor
```

저장소 접근이 제한된 경우에는 참가자 계정의 접근 권한과 GitHub 인증이 필요합니다.
인증이 필요한 경우 자신의 계정으로 GitHub CLI 또는 SSH를 설정합니다. 다른 사람의 토큰·키를 복사하지 마세요.

## 5. 환경 구성

```bash
./run.sh build
./run.sh prepare
./run.sh smoke
```

- `build`: 지정된 Isaac Sim6.0.1 이미지와 Python 의존성을 설치합니다.
- `prepare`: 필수 자산을 내려받고 실행 장면을 준비합니다. 첫 설치와 배포 업데이트 후 실행합니다.
- `smoke`: 실제 장면의 초기화·간단한 조작을 검사합니다. 성공 시 `PHYRC-SMOKE-PASS`가 출력됩니다.

별도 EULA 환경 변수 입력은 필요 없습니다. 실행기는 NVIDIA 컨테이너에 필요한 EULA/개인정보 관련 변수를 전달합니다.
사용자는 [NVIDIA 컨테이너 이용 안내](https://docs.isaacsim.omniverse.nvidia.com/6.0.1/installation/install_container.html),
[소프트웨어 이용 조건](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement/),
[개인정보 정책](https://www.nvidia.com/en-us/about-nvidia/privacy-policy/)을 확인하고 해당 조건에 따라 사용해야 합니다.
이 프로젝트의 실행 옵션 변경이 NVIDIA의 이용 조건을 없애는 것은 아닙니다.
자산별 출처 및 조건은 [THIRD_PARTY.md](../../THIRD_PARTY.md)에 있습니다.

처음에는 이미지 다운로드·셰이더 컴파일로 오래 걸릴 수 있습니다.
빈 캐시로 실행한 설치 검사에서는 장면이 열린 뒤 첫 조작 검사까지 수 분이 더 걸렸고, 전체 약 6분 후 통과했습니다.
처음 장면이 보이거나 초기화 메시지가 나왔다고 즉시 준비가 끝난 것은 아닙니다. `PHYRC-SMOKE-PASS`를 확인하세요. `latest`나 다른 Isaac 버전으로 임의 교체하지 마세요.
NGC가 인증을 요청하면 NVIDIA 안내에 따라 자신의 계정으로 `docker login nvcr.io`를 수행합니다.

## 6. 조종과 수집

```bash
./run.sh gui
./run.sh gui --training-record 1 --evaluate 1
```

두 명령은 동시에 실행하지 않습니다. 같은 checkout에서는 한 번에 실행 하나만 지원합니다.
수집을 종료할 때는 viewport에서 `ESC`를 누르고 터미널의 `[Dataset export] READY`까지 기다립니다.
[키 조작표](../../README.md#2-teleop-조종) · [데이터 확인](DATA.md)

## 자주 만나는 문제

| 증상 | 확인할 것 |
|---|---|
| Docker permission denied | Docker 그룹 등록 후 로그아웃/로그인 여부 |
| 컨테이너에서 GPU가 보이지 않음 | NVIDIA Container Toolkit과 위 GPU 확인 명령 |
| DISPLAY/Xauthority 오류 | 로컬 그래픽 세션, viewport 실행 터미널, xauth 설치 |
| Run prepare first | `./run.sh prepare` 완료 여부 |
| active prepare/run | 이전 실행이 종료됐는지 확인 |
| 창은 닫혔는데 HDF5가 없음 | 자동 변환 중일 수 있음. READY까지 기다리고 capture.json 상태 확인 |
| complete=false | 정상 정책 구간을 마치기 전에 종료됨. ESC로 다시 수집 |
| 실제 조작이 영상보다 느림 | 영상/정책 주기는 시뮬레이션 시간 기준이며 PC 처리 속도와 다름 |

호스트의 `output/`은 컨테이너에서 `/output/`, 저장소는 읽기용 `/project/`, `scripts/`는 `/scripts/`입니다.
예를 들어 호스트 `output/checkpoints/policy.pt`는 컨테이너 명령에서 `/output/checkpoints/policy.pt`입니다.
