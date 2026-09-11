> **현재 작업: 목둘레 보존 높이 축소·스폰 랜덤화·손 충돌 정렬 (2026-09-11)**
>
> 접촉 정지 수정 기준점은 `6c73e5c`이며 GitHub에 push했습니다.
> 그 이후 작업은 옷 높이를 10/12로 줄이되 목둘레와 인접 정점을 그대로 유지합니다.
> FEM solver는 64회, 로봇 속도는 원래 설정의 90%, 접촉 보정은 기본 24회입니다.
> 접촉 보정의 마지막 결과를 재검사하도록 수정했으며, 해결되지 않은 교차의
> 안전 되돌림은 유지합니다. 재현 시험 결과와 한계는
> [접촉 정지 수정 기록](docs/CONTACT_GUARD_FIX_20260911.md)을 참고하세요.
> 과거 복구 상태와 시험 기록은 현재 설정을 뜻하지 않습니다.

### 현재 배치 및 손 충돌 설정

`./run.sh prepare`로 런타임 코드와 옷 에셋을 다시 준비한 뒤 실행하세요.
이미 실행 중인 GUI에는 파일 수정이 즉시 적용되지 않습니다.

```bash
./run.sh gui                          # 사람·의자: 반경 10cm, 회전 ±30° / 옷: 상자 네 곳 중 하나
./run.sh gui --no-randomization       # 랜덤화 해제, 원래 사람 위치 및 세 번째 상자
STRETCH4_RANDOMIZE=0 ./run.sh gui     # 같은 기능의 환경 변수
HUMAN_SPAWN_SEED=42 STRETCH4_GARMENT_SPAWN_SEED=42 ./run.sh gui
```

사람과 의자는 함께 움직입니다. 옷의 방향·크기와 상자·로봇의 위치는 랜덤화하지 않습니다.
손 충돌의 기본값은 `STRETCH4_HUMAN_HAND_COLLIDER=fitted`입니다. 시각 메쉬의 손 전체와
손목 경계로 닫힌 볼록 메쉬를 만들며, 손가락 사이의 틈만 매끈하게 연결합니다.
기존 손목 구는 `STRETCH4_HUMAN_HAND_COLLIDER=sphere`로 비교할 수 있습니다.
손 메쉬의 최대 확장 여유는 `STRETCH4_HUMAN_HAND_HULL_MARGIN=0.001`m입니다.

새 F슬롯은 `output/states_neckfixed_shortheight_handfit_mesh4/`에 저장합니다.
옛 슬롯은 삭제하지 않지만 변경 전 옷·손 형상이나 다른 사람 배치의 슬롯은 불러오지 않습니다.
F슬롯은 solver·속도 등 Python 설정을 과거 값으로 되돌리지 않습니다.
세부 내용은 [형상 및 배치 변경 기록](docs/GEOMETRY_PLACEMENT_20260911.md)을 참고하세요.

# PhyRC 2027

Isaac Sim **6.0.1**에서 두 대의 Stretch4로 티셔츠를 조작하는 로컬 GUI teleop 환경입니다.
이 저장소는 현재 작동 중인 FEM 천 시뮬레이션과 사용자 수정 사항을 분리한 유지보수용 스냅샷입니다.
Gymnasium 정책 환경과 작은 모방학습 예제를 포함합니다. 학습 데이터, 과거 백업,
개인 F1-F5 저장 파일은 Git에 포함하지 않습니다.
옷 집기 실험은 [학습 복원 기록](docs/GRASP_LEARNING_20260911.md), 관측·행동 명세는
[정책 인터페이스](docs/POLICY_INTERFACE.md)를 참고하세요.
학습 복원 전 코드는 GitHub 태그 `pre-grasp-learning-20260911`로 보존했습니다.

**설치 경로는 Docker 방식 하나로 통일합니다.** Isaac Sim을 호스트에 별도로 설치하거나
Conda/ROS/시스템 CUDA Toolkit을 추가로 설치할 필요는 없습니다. NVIDIA 드라이버는 호스트에 필요합니다.
아래 순서를 처음부터 따르면 컨테이너 안에 Isaac Sim 6.0.1과 프로젝트 실행 환경이 설치됩니다.

## 1. 준비할 컴퓨터와 계정

1. NVIDIA RTX GPU가 있는 x86-64 PC에 Ubuntu Desktop 22.04 또는 24.04 LTS를 설치합니다.
2. 실제 모니터를 GPU에 연결하고 로컬 데스크톱에 로그인합니다. 이 튜토리얼은 SSH/VNC/WSL GUI 경로를 지원하지 않습니다.
3. RAM 32GB 이상, VRAM 16GB급 RTX GPU, SSD 여유 공간 100GB 이상을 프로젝트 준비 기준으로 잡습니다. 큰 컨테이너와 최초 셰이더 캐시를 위한 여유입니다.
4. 인터넷 연결과 `sudo` 권한이 필요합니다. 비공개 저장소이므로 소유자에게 GitHub 계정의 저장소 접근 권한을 받아야 합니다.

하드웨어 호환성의 최종 기준은 [NVIDIA Isaac Sim 요구사항](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html)입니다.
CPU 전용 PC나 RTX 기능이 없는 GPU에서 작동한다고 보장하지 않습니다.
기존 작업 호스트는 Ubuntu 22.04.5 / RTX 5080 16GB / 드라이버 580.178.04였습니다.
다른 호스트의 드라이버 버전을 무조건 이 숫자로 내리지 말고 해당 GPU와 Isaac 버전의 호환성을 확인하세요.

## 2. Ubuntu와 NVIDIA 드라이버

Ubuntu가 없다면 [Ubuntu Desktop 설치 안내](https://ubuntu.com/tutorials/install-ubuntu-desktop)를 따라 설치합니다.
설치 시 기존 디스크를 지우는 선택지는 데이터가 삭제되므로 주의하세요.
이후 `Ctrl+Alt+T`로 터미널을 열고 기본 도구를 설치합니다.

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates gnupg python3 xauth util-linux unzip gh ubuntu-drivers-common
ubuntu-drivers devices
```

`소프트웨어 및 업데이트 > 추가 드라이버`에서 GPU에 맞는 NVIDIA 권장 드라이버를 선택하고 재부팅합니다.
Secure Boot 사용 시 설치 중 안내되는 MOK 등록도 완료해야 합니다.
재부팅 후 다음 명령이 GPU 정보를 출력해야 합니다.

```bash
nvidia-smi
```

드라이버 설치에 문제가 있으면 [NVIDIA 드라이버 설치 안내](https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/)를 확인합니다.
로그인 화면의 톱니바퀴에서 `Ubuntu on Xorg`를 선택하면 아래 Xauthority 기반 GUI 실행 경로가 단순해집니다.

## 3. Docker Engine

아래는 새 Ubuntu용 설치 흐름입니다. 이미 Docker/Podman이 설치된 PC라면 먼저
[Docker 공식 Ubuntu 설치 문서](https://docs.docker.com/engine/install/ubuntu/)의 충돌 패키지 안내를 확인하세요.

```bash
sudo install -d -m 0755 /etc/apt/keyrings
curl --fail --silent --show-error --location https://download.docker.com/linux/ubuntu/gpg \
  | sudo tee /etc/apt/keyrings/docker.asc >/dev/null
sudo chmod 0644 /etc/apt/keyrings/docker.asc
. /etc/os-release
printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' \
  "$(dpkg --print-architecture)" "$VERSION_CODENAME" \
  | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

**로그아웃 후 다시 로그인**하여 그룹 변경을 적용합니다. `docker` 그룹은 사실상 관리자 수준 권한을 줍니다.
프로젝트 전체를 `sudo ./run.sh ...`로 실행하면 호스트 파일 권한과 GUI 인증이 꼬일 수 있으므로 사용하지 않습니다.

```bash
docker run --rm hello-world
```

## 4. NVIDIA Container Toolkit

[NVIDIA 공식 설치 문서](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)에 따라
Docker가 호스트 GPU를 사용할 수 있도록 설정합니다. 이 단계의 Docker 재시작은 다른 실행 중 컨테이너에도 영향을 줄 수 있습니다.

```bash
curl -fSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor --yes --output /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's|deb https://|deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://|g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
docker run --rm --gpus all ubuntu:24.04 nvidia-smi
```

마지막 명령에서도 같은 GPU가 보여야 다음 단계로 진행할 수 있습니다.

## 5. GitHub 인증과 프로젝트 복제

브라우저에서 본인 계정으로 로그인해 저장소 접근 권한을 확인한 후 다음을 실행합니다.
`gh auth login`이 보여 주는 일회용 코드를 브라우저에 입력합니다. 비밀번호나 토큰을 README나 커밋에 넣지 마세요.

```bash
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
mkdir -p "$HOME/Documents"
cd "$HOME/Documents"
git clone https://github.com/0x4A656F6E2053656F79756C/PhyRC_2027.git
cd PhyRC_2027
./run.sh doctor
```

현재는 submodule이 없으므로 `--recursive`가 필요 없습니다. 이유와 자산별 출처는 [THIRD_PARTY.md](THIRD_PARTY.md)에 있습니다.
소유자 계정의 SSH 키를 다른 컴퓨터에 복사하지 마세요. 각 사용자는 자기 계정과 인증 수단을 사용합니다.

## 6. Isaac Sim 6.0.1 설치와 자산 생성

먼저 [Isaac Sim 컨테이너 설치 및 라이선스 안내](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_container.html),
[NVIDIA 소프트웨어 라이선스](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement/),
[개인정보 정책](https://www.nvidia.com/en-us/about-nvidia/privacy-policy/)을 읽습니다.
동의하는 경우에만 다음 변수를 설정합니다. 실행기는 이를 NVIDIA 컨테이너의 EULA/개인정보 동의 변수로 전달합니다.
새 터미널을 열면 이 `export`를 다시 해야 합니다.

```bash
export PHYRC_ACCEPT_EULA=1
./run.sh build
./run.sh prepare
```

`build`가 공식 NVIDIA 컨테이너를 내려받고 최소 Python 의존성을 설치합니다.
기반 이미지는 **6.0.1 태그와 SHA256 digest**로 고정되어 있습니다. `latest`나 다른 Isaac 버전으로 바꾸지 마세요.
처음에는 이미지 다운로드와 설치로 시간이 걸립니다. 인터넷 속도와 저장장치에 따라 달라집니다.
NGC 다운로드가 인증을 요구하면 공식 컨테이너 문서에 따라 자신의 NGC 계정/API 키로 `docker login nvcr.io`를 수행합니다.

`prepare`는 외부 파일의 SHA256을 검사하고 `.runtime/`에 실행용 복사본과 티셔츠 USD를 생성합니다.
기존 `PhyRC_6.0.1`, 별도 DexGarmentLab/RCareWorld 폴더, 수동으로 복사한 캐시가 필요하지 않습니다.
전체 `Garment.zip`, `Human.zip`, `Robots.zip`, 학습 데이터는 받지 않습니다.

| 항목 | 저장 위치 | Git 포함 여부 |
|---|---|---|
| 수정된 실행 Python 16개 | `src/DexGarmentLab/` | 포함 |
| 필수 로컬 입력 USD/텍스처 | `assets/custom/` | 포함, 재배포 권리 확인 필요 |
| 외부 바닥 JPEG | `assets/downloads/` | 제외, 잠긴 HF revision에서 다운로드 |
| 기본 천 재질 USD와 참조 텍스처 2개 | `assets/downloads/Material/` | 제외, 잠긴 GitHub commit에서 다운로드 |
| 생성 USD와 실행 복사본 | `.runtime/` | 제외, `prepare`로 재생성 |
| Isaac/셰이더/패키지 캐시 | `cache/` | 제외 |
| 사용자 저장과 녹화 | `output/` | 제외 |

## 7. 설치 확인

다른 Isaac Sim GUI/시뮬레이션을 종료한 뒤 실행합니다. 동일 GPU에서 여러 SimulationApp을 동시에 띄우지 않습니다.

```bash
./run.sh smoke
```

실제 teleop 메인 루프가 장면을 생성한 다음 두 로봇에 짧은 lift 입력을 전달하고,
그리퍼 토글과 천 상태의 저장/변경/복원을 수행합니다. 성공하면 `PHYRC-SMOKE-PASS`가 출력됩니다.
결과는 `output/verification/smoke.json`이며, 사용자 슬롯과 분리된 임시 슬롯만 사용합니다.
초기 실행에는 물리 충돌 메시 준비와 셰이더·GPU 커널 생성으로 시간이 걸릴 수 있습니다.
이관 검증 호스트에서 새 프로젝트 캐시를 사용한 첫 검사는 약 5분 37초가 걸렸습니다.
장면 초기화 뒤 한동안 출력이 없을 수 있으므로 최초 실행을 몇 초 만에 실패로 판단하지 마세요.
GUI 첫 실행에서도 `Physics Tasks` 준비 화면에 몇 분 머무를 수 있습니다.
이 검사는 설치 smoke test이지 강한 당김/완전 착의/장시간 안정성을 보증하는 시험은 아닙니다.

## 8. GUI teleop 튜토리얼

```bash
./run.sh gui
```

1. 초기 로딩이 끝나고 터미널에 두 로봇의 조작 설명과 초기 F1 저장 메시지가 나타날 때까지 기다립니다.
2. 파란 티셔츠와 노란 아랫단, 두 로봇, 네 테이블, 앉아 있는 마네킹과 의자가 보이는지 확인합니다.
3. 뷰포트를 클릭해 키보드 포커스를 줍니다. `W`를 짧게 눌러 로봇 1의 lift가 올라가는지 확인하고 `S`로 내립니다.
4. `I/K`, `J/L`, `U/O`로 베이스 위치와 방향을 맞춘 뒤 `A/D`로 팔을 조절하여 손가락 끝을 옷 가장자리에 접근시킵니다.
5. 손가락 끝이 천을 집을 위치에 있을 때 `Space`를 한 번 누릅니다. 가까이 갔다고 자동으로 잡히지는 않습니다.
6. `W/S`와 손목 키로 천을 조작합니다. `Space`를 다시 누르면 놓습니다. 키는 길게 누르기보다 짧게 나눠 처음 동작을 확인하세요.
7. 로봇 2는 방향키와 숫자 키패드로 조작합니다. 일반 상단 숫자키와 키패드는 다릅니다. 키패드가 있는 키보드와 Num Lock 상태를 확인하세요.
8. 원하는 자세에서 빈 `F2`를 눌러 저장하고 조금 움직인 뒤 다시 `F2`를 눌러 복원합니다. 종료는 `Esc`입니다.

| 기능 | 로봇 1 | 로봇 2 |
|---|---|---|
| 베이스 전진 / 후진 | `I` / `K` | `↑` / `↓` |
| 베이스 좌 / 우 | `J` / `L` | `←` / `→` |
| 베이스 회전 | `U` / `O` | 키패드 `/` / `*` |
| lift 위 / 아래 | `W` / `S` | 키패드 `8` / `2` |
| 팔 수축 / 확장 | `A` / `D` | 키패드 `4` / `6` |
| 손목 yaw | `Q` / `E` | 키패드 `7` / `9` |
| 손목 pitch | `R` / `V` | 키패드 `-` / `+` |
| 손목 roll | `Z` / `C` | 키패드 `1` / `3` |
| 잡기 / 놓기 토글 | 상단 `0` 또는 `Space` | 키패드 `0` 또는 `Enter` |

`STRETCH4_SHOW_COLLIDER=0 ./run.sh gui`로 충돌 메시 표시 없이 볼 수 있습니다.
기본값 `1`은 기존 작업의 collision 시각화 모드입니다. 렌더용 메시와 충돌 메시 모두 뒤통수 수정이 적용됩니다.

## 9. 저장, 복원, 녹화

- `F1`은 **실행할 때마다 초기 상태로 덮어씁니다.** 장기 저장에 쓰지 마세요.
- `F2`~`F5`: 비어 있으면 저장, 이미 있으면 불러오기입니다.
- `Shift+F2`~`Shift+F5`: 기존 슬롯을 현재 상태로 덮어씁니다.
- `F12` 두 번: 슬롯 전체 삭제입니다. 복구 기능이 없으므로 주의하세요.
- `P`: 현재 실행의 시작 상태로 초기화합니다.
- `F9` / `F10`: 녹화 시작 / 종료. 영상은 `output/recordings/`에 남습니다.
- 기본 슬롯은 `output/states_shortheight_roundhead_mesh4/`입니다. `output/`은 Git에 들어가지 않으므로 따로 백업하세요.

```bash
# 저장해 둔 F2에서 시작
STRETCH4_LOAD_SLOT=F2 ./run.sh gui
# 다른 실험의 저장 슬롯과 분리
STRETCH4_STATE_DIR=/output/my_experiment ./run.sh gui
```

이전 옷 형상/사람 위치로 만든 슬롯을 최신 형상에 로드하지 마세요. 정점 수가 같아도 물리 rest shape가 다를 수 있습니다.
기존 프로젝트의 사용자 저장 슬롯은 이 저장소로 복사하지 않았으며 원래 위치에 그대로 있습니다.

## 10. 현재 유지하는 설정

| 항목 | 현재 기준 |
|---|---|
| 물리 | Isaac Sim 6.0.1 surface-deformable FEM, 240Hz, TGS, solver 32 |
| 렌더 / 제어 | 60Hz 기준, 물리 스텝에서 접촉 보호 및 그립 처리 |
| 티셔츠 | 한 벌, 15,946 정점 / 31,464 삼각형, T자 rest sleeves |
| 크기 | 기존 +20% 전체 확대 후 높이 방향만 `10/12`, 넓어진 폭 유지 |
| 목구멍 | 중간 단계 면적 확대 후 높이 복원도 적용됨; 최종 면적을 여전히 +20%라고 해석하지 않음 |
| 질량 / 두께 | 약 129.763g / 10mm, 면적 변화에 따라 밀도 보정 |
| 사람 / 의자 | 원래보다 박스 방향으로 총 1m, 사람 기본 Y=0.45 |
| 팔 / 머리 | 양팔 spread 각 10도, elevation 입력 20도, 둥글게 다듬은 뒤통수의 visual/collision 동기화 |

형상 생성 입력은 `config/geometry.json`, 실제 제어/물성 기본값은 `src/DexGarmentLab/`가 기준입니다.
과거 코드 주석에 남은 4.5/5.1 버전 이름은 수정 이력이며 이 저장소의 지원 Isaac 버전을 의미하지 않습니다.
`STRETCH4_SHIRT=original/wearable` 또는 `STRETCH4_HUMAN=biped` 같은 과거 대체 자산 모드는 최소 배포에 포함하지 않습니다.

## 11. 문제 해결

- `permission denied /var/run/docker.sock`: 로그아웃/로그인 후 `id`에 `docker` 그룹이 있는지 확인합니다.
- `could not select device driver ... gpu`: Container Toolkit 설정과 `docker ... nvidia-smi`부터 확인합니다.
- 검은 화면/창 생성 실패: 실제 로컬 모니터, Xorg 세션, `echo "$DISPLAY"`, `xauth list`를 확인합니다. `xhost +`로 전체 접근을 허용하지 마세요.
- 권한 오류: 저장소를 일반 사용자로 clone/실행했는지 확인합니다. 컨테이너는 UID 1234와 호스트 사용자의 GID를 사용하며 실행 폴더만 그룹 쓰기 가능하게 준비합니다.
- 첫 실행이 느림: 최초 셰이더/확장/GPU 커널 준비를 기다립니다. 드라이버가 멈춘 경우와 구분해서 로그를 확인하세요.
- `Asset checksum mismatch`: 임의 파일로 덮어쓰지 말고 manifest에 적힌 정확한 입력을 복원합니다.
- 프록시가 HTTP Range를 막음: 다음 전체 압축파일 대체 경로를 사용합니다. 다운로드량은 약 2.49GB입니다.

```bash
mkdir -p assets/downloads
curl -fL --retry 3 -o assets/downloads/Scene.zip \
  https://huggingface.co/datasets/wayrise/DexGarmentLab/resolve/2ba4092676006bc98c257e7b822de39526fd9692/Scene.zip
unzip -p assets/downloads/Scene.zip Scene/kitchen/kitchen_7/textures/2K-tiling_30_basecolor.jpg \
  > assets/downloads/2K-tiling_30_basecolor.jpg
python3 scripts/fetch_assets.py --check
./run.sh prepare
```

## 12. 유지보수 흐름

```bash
git switch -c change/short-description
# src/, scripts/, config/에서 필요한 부분만 수정
# 실행 중 GUI를 종료한 다음:
./run.sh prepare
./run.sh smoke
./run.sh gui
# GUI 확인 후 종료하고 필요한 파일만 명시적으로 stage
git status --short
git add <changed-source-or-document-paths>
git commit -m "Describe the behavior change"
git push -u origin HEAD
```

`.runtime/`를 직접 고치면 다음 `prepare`에서 소스 복사본으로 덮어써집니다. 수정은 `src/`에서 합니다.
물성/형상/노드 수를 바꿀 때는 저장 슬롯 경로도 분리하고, 새 기준값과 검증 범위를 함께 기록합니다.
외부 자산을 바꿀 때는 다운로드 revision, SHA256, 출처와 권리를 갱신합니다.
`config/source-snapshot.sha256`는 최초 이관 당시 스냅샷 기록이며, 이후 정상 수정에 맞춰 무조건 덮어쓰는 최신 파일 목록이 아닙니다.
이미지/패키지 버전 변경은 별도 작업으로 검증하세요.

이관 검증 결과와 한계는 [docs/VERIFICATION.md](docs/VERIFICATION.md)에 기록합니다.

### Gripper friction trial

Finger and fingertip contacts default to coefficient **0.2**, the cloth coefficient
used immediately before the historical frictionless patch. Cloth and mannequin
materials remain zero; native grasp attachments remain enabled. Set
`STRETCH4_GRIPPER_CONTACT_FRICTION=0 ./run.sh gui` to restore the previous zero
contact friction on the next launch. This override is forwarded by the launcher.
No extra friction controls or diagnostic windows are created in the GUI.
For code rollback, change the `STRETCH4_GRIPPER_CONTACT_FRICTION` fallback
from `0.2` to `0` in `Env_Config/Garment/ZeroSceneFriction.py`, then synchronize
the maintained source to the runtime (normally `./run.sh prepare` with GUI closed).
See [trial evidence and preserved F1–F5 stages](docs/GRIPPER_FRICTION_20260911.md).
