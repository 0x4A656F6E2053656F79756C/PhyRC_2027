# 전체 teleop 기록과 3D replay

```bash
# 시작부터 자동 기록. 종료하면 자동 저장.
PHYRC_ACCEPT_EULA=1 ./run.sh gui --full-record 1

# 동일한 환경 변수 방식
STRETCH4_FULL_RECORD=1 ./run.sh gui

# 기록 폴더를 선택해 재생
./run.sh replay output/full_teleop/<실행 ID>
```

`--full-record 0` 또는 옵션 생략 시 기본 teleop입니다.
`--no-randomization`과 함께 사용할 수 있습니다.
기록은 로봇·천 초기화가 끝나고 **첫 사용자 입력을 받기 전** 시작됩니다.
Isaac 앱/셰이더 로딩 과정은 대상이 아닙니다. F9/F10 MP4 녹화와는 별도 기능입니다.

## 기록 내용과 종료

기본 경로는 `output/full_teleop/<실행 ID>/`이며 터미널에도 출력합니다.
`STRETCH4_FULL_RECORD_DIR=/output/my_teleop`으로 바꿀 수 있습니다.

- 초기 장면의 USD 스냅샷, 로봇 링크/관절 이름, 원본 소스 해시와 배치 정보.
- 매 physics 단계의 천 정점 위치·속도, 로봇 전체 링크 위치·자세,
  관절 위치·속도, 베이스 속도, 제어 목표, 파지 대상 정점과 오프셋.
- 실제 native attachment 존재 여부, 앵커 마스크·로컬 오프셋.
  평가용 소매/목 구멍 토폴로지와 마네킹 팔·목·머리 표면 정보도 초기/복원 경계에 저장.
- 사람·의자 위치와 카메라 위치·렌즈.
- 키 누름·떼기, modifier, 이벤트 순서, 입력을 관측한 단조 시계 값.
- 각 제어 프레임의 held keys와 제어 시간 간격.
- P 초기화 및 F슬롯 불러오기 전후 상태와 순서.

**Esc, 일반 창 종료, Ctrl+C, SIGTERM은 저장을 마무리하는 경로를 사용합니다.**
16개 상태씩 저장 작업 큐에 넘기고, 별도 스레드가 무손실 NPZ chunk와 manifest를
디스크에 반영합니다. 정상 종료는 대기 중인 모든 chunk의 저장을 기다립니다.
사용자 슬롯은 일반 teleop 기능대로 동작하고, replay에서는 기록된 상태 전환을 보여 줍니다.

파일 구조:

```text
<실행 ID>/
  scene.usdc          # 초기 3D 장면
  manifest.json       # 완료 여부, 파일 해시, 시간 기준, 프레임 수
  events.jsonl        # 순서 및 physics tick이 붙은 입력/제어 이벤트
  chunk_000000.npz    # 무손실 상태 배열 (최대 16개 상태)
  chunk_000001.npz
  ...
```

최종 `manifest.json`의 `complete: true`가 정상 완료 표시입니다.
SIGKILL, 전원 차단, 디스크 오류처럼 종료 처리를 실행할 수 없는 경우에는
마지막 디스크 반영 이후의 메모리 데이터까지 보장할 수 없습니다.
미완료 기록은 기본 replay가 거절하며, `--allow-incomplete`를 지정하면
이미 반영된 chunk를 검사·재생할 수 있습니다. 원본 기록을 수정하지 않습니다.

## “정확히 동일”의 범위

시간 기준은 **정수 physics tick**입니다. 현재 240Hz 설정에서는 tick 240이
1초입니다. 입력은 앱이 실제로 처리한 tick과 순서로 기록하고, 시간 값을
반복해서 더해 누적 오차를 만들지 않습니다. reset/load는 같은 tick의 순서 있는
전후 경계로 저장합니다. 이때 PhysX 뷰를 재생성하는 내부 초기화 단계는
teleop 궤적에 이어 붙이지 않고, 명시적인 상태 전환으로 기록합니다.

배열은 원래 부동소수점 자료형을 유지해 저장합니다. **기본 replay는 저장된
3D 상태를 그대로 적용하며 FEM 물리를 다시 계산하지 않습니다.** 따라서 천이
다르게 떨어지거나 그립이 조금씩 달라지는 재시뮬레이션 오차가 누적되지 않습니다.
마우스로 관찰할 수 있는 3D 장면이며, 영상 파일을 재생하는 기능이 아닙니다.

키 입력만 같은 시점에 다시 넣어 GPU FEM을 계산하면 같은 천 궤적을 비트 단위로
보장할 수 없습니다. 이 기록은 내부 접촉 캐시/솔버 이력을 복원하는 체크포인트도
아니므로, replay 중간부터 물리 시뮬레이션을 재개하는 기능은 제공하지 않습니다.
입력 이벤트와 실제 상태는 함께 보존되어 후속 분석에 사용할 수 있습니다.

모든 기록 스텝을 재생합니다. GPU/디스크가 느리면 실제 화면 재생은 느려질 수
있지만, 따라잡기 위해 상태를 건너뛰지 않습니다. **시뮬레이션 시간과 상태의
정확성을 보존하며, 모니터의 표시 시각이나 운영체제 입력 지연까지 0으로 만드는
기능은 아닙니다.** 렌더링 픽셀의 동일성도 보장 범위에 포함하지 않습니다.

전체 정점과 속도를 240Hz로 보존하므로 기록 모드는 저장량과 실행 부하가 큽니다.
파일 쓰기가 밀리면 시뮬레이션을 기다리게 하며, 프레임 누락이나 손실 압축으로
대신하지 않습니다. 기본 큐는 4개 chunk이며, 수집 중인 chunk와 저장 중인 chunk 및
압축 작업 메모리는 별도입니다. 큐 크기가 고정되어 장시간 실행해도 계속 늘지 않습니다.

2026-09-13부터 `phyrc-full-teleop-v2` 형식으로 같은 크기/자료형의 배열을 chunk
단위로 묶고 DEFLATE level 1로 무손실 압축합니다. 이전 v1 기록도 계속 재생됩니다.
수집 주기 240Hz, 배열 자료형, 입력 이벤트 순서, reset/load 경계는 유지합니다.
GPU→CPU 상태 읽기와 렌더링 비용은 남으므로 실시간 1배속을 보장하지 않습니다.

실제 기존 기록의 256개 상태로 저장 부분을 비교한 시험에서 최종 저장 대기 포함
3.62초 → 2.69초(약 26% 감소), append 지연 p95 216.4ms → 0.65ms였습니다.
큐를 빠르게 채우는 시험의 최대 append 지연은 여전히 181.5ms였습니다.
모든 필드의 shape/dtype/바이트가 일치했습니다. 전체 teleop FPS 측정값은 아닙니다.
원본 결과: `output/recording_optimization/benchmark.json`.

## 저장된 물리 상태로 평가하기

**이 변경 이후에 새로 전체 기록한 실행**은 Isaac Sim을 실행하지 않고 NumPy만으로
평가할 수 있습니다. 기록 당시의 천 정점과 로봇/앵커 상태에서 파지 오차와 상승량,
소매/목 통과, 팔 덮임을 다시 계산합니다. 영상 분석이나 FEM 재시뮬레이션은 아닙니다.

```bash
# 새 실행을 처음부터 전체 기록하고 정상 종료
PHYRC_ACCEPT_EULA=1 ./run.sh gui --full-record 1

# 호스트 터미널: Isaac/GPU 없이 기록 전체를 평가 (NumPy 필요)
python3 scripts/evaluate_replay.py output/full_teleop/<실행 ID> \
  --output output/evaluation/replay

# 화면으로 replay하면서 같은 상태를 평가
PHYRC_ACCEPT_EULA=1 ./run.sh replay output/full_teleop/<실행 ID> \
  --verify --evaluate /output/evaluation/replay
```

터미널에 `FINAL SCORE`가 출력되고, 지정한 출력 폴더 아래 실행별 폴더에
`samples.jsonl`과 `result.json`이 생깁니다. `raw_points`는 50점 만점 원점수,
`overall_dressing_points`는 팔 덮임 30점 만점, `final_score`는 원점수/최초 접촉 이후 시간입니다.
`score_items`에는 집기/첫 소매/반대쪽 어깨/다른 소매 각 5점과 Overall dressing 30점이
독립 항목으로 저장되고, 콘솔에도 각각 출력됩니다. 45점 묶음으로 출력하지 않습니다.
replay 속도와 PC 처리 시간은 점수의 시간 계산에 들어가지 않습니다.

기본 평가 구간은 tick 0부터 마지막 physics tick까지입니다. F6/F7은 필수가 아니며
기록 후 구간을 선택할 수 있습니다. 실시간 F6/F7 점수와 비교하려면 시작/종료 tick도
같아야 합니다. 최초 접촉 전 준비 시간은 분모에서 제외하고, 접촉 이후에는 종료까지 셉니다.
P 초기화나 슬롯 LOAD를 가로지르는 시도는 실시간 평가처럼 무효입니다.

```bash
# 예: 기록 시작 후 1~5초 구간을 검사하고, 그 안의 최초 접촉부터 시간을 계산
python3 scripts/evaluate_replay.py output/full_teleop/<실행 ID> \
  --start-tick 240 --end-tick 1200 --output output/evaluation/replay

# 화면 replay의 대응 옵션
PHYRC_ACCEPT_EULA=1 ./run.sh replay output/full_teleop/<실행 ID> \
  --evaluate /output/evaluation/replay \
  --evaluation-start-tick 240 --evaluation-end-tick 1200
```

시작 tick에 LOAD/reset 경계가 있으면 그 tick의 마지막 복원 상태를 시작점으로
사용합니다. 집기 기준 높이는 선택한 평가 시작 이후의 최초 파지에서 정하므로,
들어 올리기 전에 시작하는 구간을 선택하세요. 판정은 실시간과 같이 20Hz이며
집기 중단은 모든 240Hz physics tick에서 확인합니다. 알 수 없는 평가 소스 버전이거나 기록이 미완료·손상된 경우에는 유효한 최종 점수를
출력하지 않습니다. 확인된 기존 v2 평가 소스는 접촉 시간 v3로 명시적으로 재채점하고,
결과에 기록 당시/현재 소스 해시를 모두 남깁니다.

접촉 판정은 **충돌 메시 표면 간 거리 ≤ 기존 contact offset 합**입니다.
현재 기본값은 옷 8mm + 사람 6mm이며, 몸통/양손 콜라이더를 모두 사용합니다.
PhysX 내부 충돌 이벤트와 동일하다는 보장은 없으며, 사용자가 승인한 기하학적 기준입니다.
첫 접촉 이후 떨어져도 시계는 계속 흐르고, 접촉 전 집기 점수는 유지합니다.
접촉이 없거나 접촉 이후 시간이 0이면 `final_score=null`(N/A)이고 원점수는 남습니다.

새 기록은 충돌 기준 메시/offset도 포함하여 NumPy만으로 평가됩니다. **이전 v2 기록**은
보존된 `scene.usdc`에서 CPU로 접촉 기준을 한 번 추출하면 새 기준으로 채점할 수 있습니다:

```bash
PHYRC_ACCEPT_EULA=1 ./run.sh cpu /scripts/export_replay_contact.py \
  /output/full_teleop/<실행 ID>
```

원본 기록은 수정하지 않으며 `output/evaluation/contact_contexts/<실행 ID>.json`에
원본 manifest/scene 해시와 결합해 저장합니다. 이후 원래의 `evaluate_replay.py` 명령을
그대로 사용하면 자동으로 읽습니다. 다른 위치의 파일은 `--contact-context`로 지정합니다.

사용자 기록 `20260912T155015_750407Z_b796e7`은 추출을 완료했습니다. 최초 접촉은
원본 tick 4496(18.733333초), 콜라이더는 `HandHull_left`입니다. tick 4495는 비접촉,
4496은 접촉으로 독립 확인했습니다. 종료 tick 6800까지 9.6초이고 원점수 50점,
최종 **5.208333 points/s**입니다. 원본 상태에 대한 기하학적 판정 결과입니다.

**기존 v1 기록은 재생·상태 검증은 가능하지만, 정확한 전체 평가에 필요한 native
앵커 정보와 평가 기준 정보가 부족해 이 기능은 거절합니다.** 빠진 값을 추정해
집기 점수를 부여하지 않습니다. 기존 `output/evaluation/` 평가 결과는 보존합니다.

## replay 옵션과 검증

```bash
# 각 상태를 적용한 뒤 천 정점/로봇 자세가 기록과 같은지 확인하며 재생
./run.sh replay output/full_teleop/<실행 ID> --verify

# 녹화된 카메라 대신 자유로운 시점으로 보기
./run.sh replay output/full_teleop/<실행 ID> --free-camera

# 빠르게 전체 상태 검사 (시각화 없이, CPU USD 사용)
./run.sh cpu /scripts/replay_teleop.py \
  /output/full_teleop/<실행 ID> --verify-only \
  --report /output/replay_verification.json
```

`--speed 1`은 원래 시뮬레이션 속도를 목표로 하고, `--speed 2`는 두 배속을
목표로 합니다. `--speed 0`은 대기 없이 순서대로 재생합니다. 처리 속도가 부족해도
프레임을 건너뛰지는 않습니다. 마지막 상태까지 보여 준 뒤 replay 앱이 종료됩니다.

검증은 chunk 체크섬·연속 tick·프레임 수를 확인하고, `--verify` 또는
`--verify-only`에서는 각 프레임의 천 정점과 로봇 위치·quaternion을 USD에서
다시 읽어 기록 배열과 정확히 일치하는지 검사합니다. 렌더링 모드에서는 화면
갱신 후에도 상태가 바뀌지 않았는지 검사합니다. replay 장면의 물리 API는
메모리의 session layer에서 비활성화하므로 새 solver가 상태를 덮어쓰지 않습니다.

`scene.usdc`에는 장면 geometry가 포함되며 텍스처 경로는 같은 프로젝트의
컨테이너/런타임 자산 경로를 참조합니다. 현재 프로젝트 환경에서 재생하는
형식이며, 다른 컴퓨터로 옮길 때는 참조 텍스처도 함께 준비해야 합니다.

코드: `Policy/teleop_recording.py`, `Policy/teleop_playback.py`, `Policy/evaluation_replay.py`,
`scripts/replay_teleop.py`, `scripts/evaluate_replay.py`.
기록 파일은 `output/` 아래에 있어 Git에 포함되지 않습니다.

## 확인한 결과

2026-09-12 실제 Isaac teleop 루프에서 두 로봇의 lift/arm 이동, 그리퍼 입력,
P 초기화, F2 저장·불러오기와 종료를 검사했습니다. 112개 연속 physics tick과
전후 경계를 포함한 118개 상태를 기록했습니다. W 입력이 tick 4에 처리되고,
동일 tick의 제어 변경이 physics tick 5부터 반영되는 것을 확인했습니다.

CPU replay와 GPU 렌더링 replay 모두 118개 상태 전부의 천 정점 및 로봇
위치·quaternion을 정확히 일치하는 배열로 다시 읽었습니다. 렌더링 이후의 상태
유지와 최종 장면 이미지도 확인했습니다. 이 검증은 짧은 이동/초기화/상태 복원
시험이며 장시간 착의 궤적의 실제 실행 성능을 측정한 결과는 아닙니다.
Esc 종료 외에 SIGTERM을 보낸 실제 실행에서도 118개 상태의 자동 저장과
`complete: true`를 확인했습니다.

2026-09-12 GUI 문자 입력 오류 수정: Carb의 KEY_PRESS/KEY_RELEASE 입력은 enum이지만
CHAR 입력은 문자열입니다. 기록 코드가 모든 입력에 `.name`을 읽어 발생하던
AttributeError를 수정했습니다. `scripts/check_teleop_keyboard.py`는 GPU/GUI 없이
실제 Carb 키보드 이벤트를 생산 콜백에 전달해 영문·한글 CHAR, 누름·반복·떼기,
F6·SPACE·Esc 처리와 기록 순서·tick을 검증합니다. 기존 콜백의 오류 재현과
수정 콜백의 정상 동작을 모두 확인했습니다. 수정 전에 실행한 GUI는 재시작해야 합니다.

2026-09-13 최적화 후 실제 GPU teleop도 118상태/112 physics tick 보존을 확인했고,
CPU USD 및 GPU 렌더링 replay에서 118상태 모두 정확히 복원했습니다.
실제 F6/F7 구간(tick 4~56)의 모든 평가 샘플과 최종 점수가 live/replay에서 같았습니다.
이 짧은 실제 구간은 0점입니다. 별도 합성 물리 상태 시험에서는 50점 및 한 tick 파지
해제 후 45점 사례의 모든 샘플/점수 일치도 확인했습니다. 실제 GPU 완전 착의 성공
시험을 의미하지는 않습니다. `output/recording_optimization/verification.json` 참고.
