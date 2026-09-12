# 사용자 지속 지침

**사용자가 별도로 요청하지 않는 한 옷·로봇·그리퍼·마네킹의 성질과 설정값을
변경하지 않는다.** 기록/재생이나 평가 오류 수정 때문에 물리 파라미터, 형상,
크기, 재질, 마찰, 구동 속도, 파지 설정, 마네킹 포즈 등을 임의 조정하지 않는다.
**2026-09-13 사용자 최신 지시로 현재까지의 누적 작업을 커밋하고 GitHub에 푸시하는
것이 명시적으로 승인되었다.** 아래 과거 절의 “커밋/푸시 없음·금지”는 당시 상태이며,
이번 게시를 막는 지시가 아니다. 향후 새 작업을 자동으로 게시하라는 상시 승인은 아니다.
또한 사용자는 replay 배속을 더 이상 수정하지 말라고 요청했다.

# 인계 시작점 — 2026-09-13, 누적 구현 게시

## Git 및 게시 범위

- 저장소: `/home/seoyul/PhyRC_2027`, 브랜치 `main`.
- GitHub: `git@github.com:0x4A656F6E2053656F79756C/PhyRC_2027.git` (`origin`).
- 이 인계 회차 직전 HEAD/origin/main은 `ac73e41`:
  `Show inline animated demonstration in GitHub README`. README GIF는 이미 게시된 상태.
- 이번 누적 변경의 커밋 제목:
  **`Add lossless teleop replay, policy cameras, and itemized dressing evaluation`**.
  실제 커밋/원격 일치는 `git log -1 --oneline`, `git rev-parse HEAD origin/main`으로 확인.
  자기 자신을 포함하는 커밋 해시는 이 문서에 하드코딩하지 않는다.
- 이번 게시에는 아래 구현 코드/검사 스크립트/설정/README/상세 문서 및 기존
  `docs/PhyRC_proposals.pdf`가 포함된다. ignored `output/`, `cache/`, `.runtime/` 및
  실제 teleop 기록/평가 결과/사용자 슬롯은 로컬에 보존하며 Git에 포함되지 않는다.
- PDF 주의: 평가 규칙을 읽은 원본은 `/home/seoyul/Downloads/PhyRC_proposals.pdf`
  (SHA256 `514b5398b9815e0b0b63718e81e148aa8b2c9ac559644b45ffa6fc3ac1b7c037`).
  기존 docs 사본의 SHA256은 `cc156654cc6cdfc5eb59200f87c942053273551e9f216be151e84dfa0c588f77`로
  서로 다르다. 기존 docs 사본을 임의 교체하지 않았다. 최종 규칙은 사용자가 직접
  지정한 짧은 소매/집기/접촉시각/항목별 분리 수정까지 반영된 v4이다.

## 현재 제공하는 기능

1. 정책 관측 contract **0.3.0**, RGB/Depth 카메라 총 5개:
   외부 overview + 로봇 0/1 손목 + 로봇 0/1 상부 head.
   기본 256×256, RGB/depth/valid mask 및 카메라 K/pose/timestamp 정보.
   overview는 마네킹에 zoom-in된 구도이고 randomized spawn 위치/각도를 reset마다
   한 번 반영한다. 머리/손목 시점은 실제 링크를 따라간다. GUI viewport와 별도.
   `config/policy_interface.json`, `Policy/sensors.py`, `docs/POLICY_INTERFACE.md` 참고.
2. `--full-record 1`: 사용자 입력 전부터 매 physics tick(240Hz) 전체 상태 기록.
   v2 무손실 chunk/고정 길이 비동기 writer 큐, 큐 포화 시 block, 프레임 drop 없음.
   종료 시 모든 저장을 drain. 천 정점/속도, 로봇 링크/관절/제어, native 앵커,
   이벤트/tick/카메라/초기 및 복원 경계 평가 기준 데이터 포함. RGBD 영상 저장과 다름.
3. replay는 **저장된 3D 상태를 적용**하며 새 FEM 물리를 계산하지 않는다.
   `--verify`는 정점/링크의 정확한 readback을 확인한다. solver 내부 상태 복원이 아니며
   중간부터 실제 물리 시뮬레이션을 재개하거나 비트 동일 재시뮬레이션을 보장하지 않는다.
4. live teleop(F6 시작/F7 종료), 학습 정책, CPU 또는 시각 replay에서 같은 측정/채점.
   v4 항목은 pickup5 / first sleeve5 / opposite shoulder5 / second sleeve5 /
   Overall dressing30(10n+20m). Overall을 45점 묶음으로 해석하면 안 된다.
   예전 짧은 소매 완전 착의 만점 예외는 Overall30에만 적용되고 각5점은 별도 판정.
   최고 진행도/기득점은 유지한다. 과거 순간 coverage1 때문에 50점이어도
   `dressing_complete=false`일 수 있으므로 결과 의미를 혼동하지 말 것.
5. points/s 분모는 **최초 충돌 메시 접촉부터 종료까지의 physics tick 차이**.
   사용자 승인 기준은 authored collider 표면 거리 ≤ 기존 contact offset 합
   (현재 기본 옷8mm + 사람6mm). PhysX native collision event와 동일 보장 아님.
   첫 접촉 후 떨어져도 시간은 계속 흐르고, 접촉 전 집기 점수는 보존된다.
   무접촉/접촉 후0초는 N/A (`final_score=null`). 결과와 진단값은 저장한다.

## 최신 사용자 기록과 실행 명령

사용자 기록: `output/full_teleop/20260912T155015_750407Z_b796e7/`.
6802상태, 6800 physics ticks. 옛 v2 기록이므로 충돌 기준 sidecar 추출을 이미 수행함:
`output/evaluation/contact_contexts/20260912T155015_750407Z_b796e7.json`.

```bash
# 새 전체 기록. 기존에 쓰던 환경 변수 옵션은 그대로 병행 가능.
PHYRC_ACCEPT_EULA=1 ./run.sh gui --full-record 1

# 사용자가 마지막으로 요청한 시각 replay + 평가
PHYRC_ACCEPT_EULA=1 ./run.sh replay \
  /output/full_teleop/20260912T155015_750407Z_b796e7 \
  --evaluate /output/evaluation/replay_visual

# 화면/Isaac/GPU 없이 같은 기록 평가 (호스트 Python + NumPy)
python3 scripts/evaluate_replay.py \
  output/full_teleop/20260912T155015_750407Z_b796e7 \
  --output output/evaluation/replay_contact_v4

# 다른 옛 v2 기록에 접촉 기준이 없을 경우에만 1회 CPU USD export
PHYRC_ACCEPT_EULA=1 ./run.sh cpu /scripts/export_replay_contact.py \
  /output/full_teleop/<실행ID>
```

- 시각 replay 점수는 **터미널**에 출력된다. viewport 위 점수 HUD는 구현하지 않았다.
- 출력 DIR/평가실행ID/{samples.jsonl,result.json}. v4 `result.score_items`가 항목별 점수.
  접촉 구간 입력 스키마는 `phase1-measurements-v3`, 결과는 `phase1-live-v4` /
  `phase1-scores-v4`, scoring revision은 `separate-dressing-items-v4`.
- reset/LOAD를 가로지르는 평가는 무효. 전체 기록을 기본으로 사용하고 필요하면
  --start-tick/--end-tick (시각 replay: --evaluation-start-tick/--evaluation-end-tick).
  F6나 선택 구간 시작은 집기/접촉 전이어야 한다. 이미 접촉해 시작하면
  started_in_contact=true이며 그 이전 이력을 복원했다고 주장하지 않는다.
- 사용자 기록의 최초 접촉은 tick4496 (18.733333초), `HandHull_left`.
  이후9.6초, 각5/5/5/5/30점, 총50/50, 최종 **5.208333333333334 points/s**.
  최신 항목별 재채점: `output/separate_score_items/user_result.json`.
  원본 v3 trace/result: `output/evaluation/replay_contact_v3/20260912T164109_039752Z_41982d/`.
- 기존 v1 기록은 앵커 증거가 빠져 정확한 전체 평가 불가, 재생은 가능.
  알려진 v2/v3 소스는 명시 이행 허용. 알 수 없는 소스 해시 불일치를 만났다고
  검증을 무조건 끄거나 임의로 허용 목록에 넣지 말 것.

## 검증 및 다음 작업 시 주의

- 이번 게시 전 현재 소스 CPU 테스트 **48개 전부 PASS**:
  archive6, clock4, contact geometry5, scorer20, live/session geometry9, replay4.
  정책 관측 계약 검사(`scripts/check_policy_contract.py`)도 PASS.
  증거는 로컬 `output/publish_checks/cpu_checks.json` 및 개별 로그.
- 최근 실제 GPU teleop→archive→replay 평가: 118상태/112연속ticks,
  F6/F7 trace와 점수 동일. `output/full_record_checks/bde9dad318/report.json`.
  이 GPU 시험은 v3 시점의 짧은 무접촉(N/A) 구간이다. 이후 v4 항목 분리는
  CPU 회귀 검사, 실제 v3 archive headless CLI 이행, 사용자568샘플 재채점으로 검증.
- CPU/GPU 렌더 replay 118상태 readback PASS 이력은
  `output/recording_optimization/verification.json`. 5카메라 실GPU 검증 등은 아래 이력 참고.
- 접촉 직전 tick4495=False, tick4496=True를 직접 확인한 자료:
  `output/contact_timing/first_contact_boundary.json` / `verification.json`.
- 저장 최적화 writer-only 256 실제상태 시험: 3.62→2.69초(~26% 감소), 완전 동일 배열.
  전체 teleop FPS 개선율이라고 해석하면 안 된다. replay는 매 상태마다 USD/앱 갱신하므로
  --speed32도 빠르지 않을 수 있음. 사용자는 배속 추가 수정 중단을 명시함.
- production 객체 설정/물리 변경 금지. 사용자 슬롯은 임의로 덮지 말 것.
  GPU 시험은 별도 `STRETCH4_STATE_DIR`을 사용해야 함(일반 main은 F1 자동 저장).
  실행 중 사용자 GUI를 임의 종료하거나 옆에 GPU 시험을 띄워 메모리 경쟁시키지 말 것.
- 현재 수정한 소스는 관련 `.runtime/DexGarmentLab/` 파일에 동기화된 상태.
  이미 실행 중인 GUI는 새 모듈을 적용하려면 재시작이 필요하다.
  `./run.sh prepare`는 자산을 재준비하므로 코드 동기화 목적으로 불필요하게 실행하지 말 것.
- 이 인계에 별도 신규 기능 미완료 요청은 없음. HUD 등 후속 기능은 사용자 요청 후 진행.
  아래 세부 이력은 과거 단계의 점수/버전/미커밋 상태를 포함하므로 상단 v4 상태가 우선.

---

# 최신 수정 — 2026-09-13, 5/5/5/30 항목별 독립 채점 v4

- 사용자: First sleeve5 / opposite shoulder5 / second sleeve5 / Overall dressing30을
  dressing45로 묶지 말고 분류하여 평가 요청. pickup5는 그대로 별도 유지.
- evaluation.points()가 score_items 5개를 생성. 각 points/max_points, 5점 단계의
  achieved/획득 시각, Overall의 n/m/좌우/10점·20점 기여/실측 환산점수/override 표시.
  overall_dressing_points와 max_overall_dressing_points의 의미는 이제 **30점**.
  raw_points는 5개 항목 합계50, breakdown의 기존6개 하위항목 유지(중복 합산 금지).
- 이전 짧은 소매 완전착의 예외는 Overall30에만 유지. completion시 세5점 단계를
  일괄 _award하던 코드 제거. 첫/둘째소매는 실제 wrist 측정, 반대어깨5는 독립
  beyond-shoulder 증거가 있어야 함. 완전 착의만으로 어깨5 자동 지급하지 않음.
- 최초 접촉 기준 시간(v3), 최고 진행도 유지, pickup3초 조건은 유지.
  live/replay/policy/측정CLI 콘솔 진행 및 최종에 5개 항목과Overall의10/20 기여를 표시.
  format_score_items 공통 사용. scoring_revision=separate-dressing-items-v4,
  출력 phase1-live-v4/phase1-scores-v4, 입력 measurements-v3 그대로.
- v2 및 직전 v3의 알려진 scoring/live source 해시를 replay 이행 허용 목록에 추가.
  물리·측정 geometry 수학은 변경 없음. 기록당시/현재 해시는 결과에 보존.
- 검증: scoring20 + live/session/geometry9 + replay4 CPU검사 PASS. 독립 어깨 점수,
  부분 덮임 수식, 전체항목 합50, shortsleeve override가 다른 항목에 번지지 않음 검증.
- 사용자 원본 20260912T155015_750407Z_b796e7의 기존568측정샘플을 현재 scorer로 재채점:
  pickup5, first5, shoulder5, second5, Overall30(10+20), raw50, post-contact9.6초,
  5.208333333333334 points/s 그대로. output/separate_score_items/user_result.json.
  이 작업은 원본 측정값 재채점이며 새로운 물리 실행이 아님. 원본 보존.
- 실제 v3 archive로 headless 평가 CLI/해시 이행/항목 출력도 PASS.
  output/separate_score_items/verification.json 및 replay_cli.log 참고.
- 소스 evaluation/evaluation_live/evaluation_replay runtime 동기화 완료.
  물리/객체설정/배속/recording주기 변경 없음. 커밋/푸시 없음.

---

# 최신 수정 — 2026-09-13, 최초 옷/마네킹 접촉 기준 points/s (v3)

- 사용자 요청: points/s의 시간을 옷과 마네킹 collision mesh의 최초 접촉부터 계산.
  후속 확인에 사용자가 **“충돌 메시 접촉 판정으로 진행”**을 명시적으로 승인함.
  PhysX deformable native contact report는 제공되지 않으며 기존 기록에도 없음.
  현재 SDK 110.1.13 DeformableBodyView 및 NVIDIA 최신 제한사항으로 확인.
- 승인된 기준: 활성화된 authored 마네킹 충돌 표면과 옷 삼각형 표면 사이 거리 ≤
  두 물체의 기존 contact offset 합. 사용자 기록은 옷 0.008m + 사람 0.006m.
  CollisionBody(SDF source mesh), HandHull_left/right(convex source mesh)를 포함,
  비활성 시각 mesh/비기하 SkelRoot 제외. 구 모드의 손은 analytic sphere 사용.
  cooked SDF/hull/speculative PhysX contact, tick 사이 접촉과 동일 보장 아님.
  이 한계는 metadata/docs에 명시. 물리 설정·오프셋·형상·재질 등은 변경하지 않음.
- Policy/evaluation_contact.py: 정적 삼각형 BVH broadphase와 vertex/triangle,
  edge/edge, edge/face distance/intersection 검사. 모든 physics tick에서 최초 접촉을
  검출하며 최초 접촉 이후에는 추가 접촉 검사 생략(시간은 계속 누적).
  read-only USD export 및 checksum-bound legacy v2 sidecar loader도 포함.
- Policy/evaluation_clock.py: 정수 tick 시계. 최초 접촉은 latch, 이후 분리돼도
  계속 흘러감. raw point/집기 3초/최고 진행도/착의 조건은 유지. 준비 시간만 분모 제외.
  최초 접촉이 없거나 post-contact time이 0이면 final_score=null / N/A. 원점수는 보존.
  no-contact seed를 빼서 유리하게 평균내지 않고 points/s 집계를 거절.
- live/session/replay 공통 샘플: first_contact_time_s, physics_tick, physics_dt_s,
  first_contact_tick 추가. first_contact는 접촉 전 null, 이후 불변. 20Hz로 올림하지 않음.
  final task_time_s=(last_tick-first_contact_tick)*dt. raw measurement time_s/마일스톤/
  집기 타이머는 원래 episode 시간. phase1-live-v3/phase1-measurements-v3/
  phase1-scores-v3, scoring_revision=short-sleeve-contact-clock-v3.
  v1/v2 입력은 legacy 전체시간 방식. contact traces의 v2 포장/혼합 집계는 거절.
  기존 episode time limit은 전체 episode 제한으로 유지(점수 분모와 별도).
- 새 full recording의 evaluation_context에 충돌 geometry/offset 포함하므로 CPU
  NumPy replay 평가 가능. 기존 v2는 scene.usdc로 1회 context export하면 새기준 사용:
  PHYRC_ACCEPT_EULA=1 ./run.sh cpu /scripts/export_replay_contact.py /output/full_teleop/ID
  output/evaluation/contact_contexts/ID.json에 manifest/scene 해시와 결합해 저장,
  원본 archive는 수정하지 않음. 기존 확인된 v2 평가 소스 2개 해시를 v3로 명시 이행.
  result metadata에 recorded/current source hashes, 접촉 criterion/한계 남김.
- scripts/evaluate_replay.py/replay_teleop.py는 sidecar 자동 발견, --contact-context
  추가. 배속/프레임 표시/재생 pacing 관련 코드는 사용자 지시에 따라 변경하지 않음.
- 사용자 기록 20260912T155015_750407Z_b796e7은 context export 및 6802상태 전수 평가 완료.
  최초 접촉 tick4496 = 18.7333333333초, /World/Human/HandHull_left.
  직접 이웃 프레임 검사: tick4495 False, 4496 True. 종료 tick6800,
  post-contact9.6초, raw50/50, final5.208333333333334points/s.
  결과: output/evaluation/replay_contact_v3/20260912T164109_039752Z_41982d/result.json
  전체568샘플, 현재 scorer로 trace 재채점시 시간/점수 정확히 동일.
  raw50은 기존 최고coverage 점수가 유지되어 얻은 값이며 결과 dressing_complete는
  false임. 실제 full-dressing confirmation 성공이라고 주장하지 말 것.
- CPU검사: clock4, collision5, scorer19, live geometry/session9, replay4 모두 PASS.
  준비시간만 늘린 동작의 동일rate, 20Hz 사이 최초접촉tick, 접촉 전 pickup5보존,
  무접촉 N/A, 단일 tick 접촉/파지끊김, 삼각형 면/모서리, 구, rigid 변환 검증.
- 실제 GPU teleop→record→replay 평가 검사 PASS: 118상태/112tick 보존,
  F6/F7 실시간 trace/result 모두 replay와 일치. 이 짧은 GPU 구간은 무접촉 N/A임.
  최종 소스 GPU 보고서: output/full_record_checks/bde9dad318/report.json.
  사용자 원본 기록은 실제 물리 상태로 비영점 접촉/score 재평가 검증을 수행함.
  output/contact_timing/verification.json 및 *_tests.log, first_contact_boundary.json 참고.
- 변경한 evaluation 5모듈 runtime 동기화. 기존 원본 기록/사용자 슬롯 보존,
  시험 GPU는 독립 슬롯 경로. 커밋·푸시 없음. GUI는 재시작해야 새 live 시간이 적용됨.

---

# 최신 수정 — 2026-09-13, 무손실 기록 최적화와 replay 상태 평가

- 사용자 요청: 기존 모든 프레임/정밀도/물리를 보존해 기록을 최적화한 뒤,
  replay 상태만으로 평가하도록 구현. 커밋/푸시하지 않음.
- StateArchive v2: 16개 상태씩 고정 길이 큐(4 chunk)에 넘겨 별도 스레드에서
  같은 shape/dtype 배열을 stack하고 DEFLATE level 1로 무손실 압축, fsync/해시/
  manifest 반영. 큐가 차면 block, 프레임을 버리지 않음. close는 drain/join.
  writer 오류를 producer로 전달하고 complete:false 유지. Reader는 v1/v2 모두 읽음.
- 원본 실제 기록 20260912T144830_638434Z_a3396e의 첫 256상태로 전/후 저장 시험:
  최종 drain 포함 3.6176→2.6916초(~26% 감소), append p95 216.4→0.65ms,
  새 최대 append 181.5ms(큐 backpressure), 모든 필드 dtype/shape/바이트 동일.
  저장 파일 87,516,273→86,523,665 bytes. GPU capture/render 제외 writer 시험임.
  output/recording_optimization/benchmark.json과 baseline source/script 보존.
- 새 전체 기록에 native attachment 존재/anchor mask/local offsets, grasp link index,
  초기/after-reset/load 평가 context(토폴로지/구멍/팔/목/머리/테이블/문턱값/소스 해시)를
  저장. 어떤 객체의 성질/설정/물리/기하도 수정하지 않음.
- Policy/evaluation_replay.py: CPU NumPy로 저장된 상태에서 실제 앵커 오차/높이 상승을
  다시 계산하고 IsaacMeasurements.physical_from_state/measure 및 EvaluationSession을
  공유해 동일 240Hz 중단 체크/20Hz 채점. 소스 해시가 다르면 묵시적 재채점 거절.
- scripts/evaluate_replay.py RECORDING --output DIR [--start-tick N --end-tick N]:
  Isaac/GPU 없이 평가. scripts/replay_teleop.py --evaluate DIR
  [--evaluation-start-tick N --evaluation-end-tick N]으로 3D replay와 함께 평가 가능.
  출력 DIR/실행ID/{samples.jsonl,result.json}. time=선택한 physics tick 차이*dt.
  기본 전체구간, reset/LOAD를 가로지르면 invalid. 시작 tick의 마지막 복원 상태 사용.
  평가 전 잡기/들기 이력을 소급하지 않으므로 구간은 집기 전에 시작해야 함.
  F6/F7 실시간 결과와 비교하려면 구간 tick이 일치해야 함. 자동 F6/F7 구간 추출은 없음.
- 이전 v1 기록은 여전히 replay/검증 가능하지만 앵커/평가기준 정보가 없어 정확한
  전체 평가 거절. 누락된 데이터를 추정하거나 0점으로 확정하지 않음. 원본 기록 보존.
- CPU: archive 6개(느린 writer/큐 포화/ownership/error 포함), 기존 scoring 17개,
  geometry/session 7개, 새 replay 4개 PASS. replay 합성 시험은 50점 및 1-tick
  파지 해제 후 45점 사례에서 live 실제 physical_sample과 모든 trace/result 동일.
  source: scripts/check_replay_evaluation.py. 합성 50점은 실제 GPU 완전 착의 검증이 아님.
- 실제 GPU teleop 검사: 두 로봇 이동/문자키/P reset/F2 save+load/Esc,
  118상태/112연속physics ticks 모두 보존. 기존 사용자 슬롯 대신 시험 전용 경로 사용.
  추가 F6/F7 구간 tick 4~56의 실시간 trace/result와 replay 재평가 전부 동일(PASS).
  이 짧은 실제 구간은 0점이며 실제 GPU 비영점 착의 성공을 주장하지 않음.
  output/full_record_checks/c36ee6254e/report.json 및 recordings/20260912T152037_340951Z_ba6093.
- CPU USD replay 118상태 전부 exact readback+평가 PASS:
  output/recording_optimization/replay_cpu.json (이전 첫 GPU 검사 실행 07caae8939).
  호스트 standalone evaluate_replay CLI도 실데이터 tick4~56 실행 성공.
- GPU 렌더링 replay도 118상태 전부 렌더 이후 exact readback 및 평가 PASS.
  live/호스트 standalone/render replay result 동일. replay_render.json, verification.json 참고.
- 변경한 Policy teleop_recording/evaluation_live/evaluation_replay만 runtime에 동기화.
  README와 FULL_TELEOP_RECORDING/PHASE1_EVALUATION 문서 업데이트.

---

# 최신 수정 — 2026-09-12, 전체 기록 중 문자 입력 오류

- 사용자 실행 crazy_mestorf의 실제 로그에서 on_keyboard_event 5220행의
  `AttributeError: 'str' object has no attribute 'name'` 반복을 확인함.
- Carb KEY_PRESS/KEY_RELEASE는 enum, CHAR 이벤트는 str임. 기록 코드가
  문자에도 .name을 읽어 실패함. 문자열은 그대로, enum은 .name을 사용하도록
  실제 콜백만 수정함. 키 매핑·입력 시점·물리/로봇/천/마네킹 설정은 변경 없음.
- `scripts/check_teleop_keyboard.py`: GPU/GUI 없이 실제 Carb input plugin과
  테스트 프로세스에만 속한 논리 키보드로 생산 콜백을 검사.
  영문/한글 CHAR로 원본 콜백 오류 2회를 정확히 재현한 뒤 수정 콜백 정상 확인.
  KEY_PRESS/REPEAT/RELEASE, F6, SPACE, ESCAPE, 이벤트 순서/정수 tick 보존 PASS.
  `output/recording_input_fix/before.json`, `after.json`에 증거 저장.
- 기존 archive 무손실/경계/무결성 CPU 검사 4개 PASS.
  GPU 전체 기록 시험에도 CHAR 사례를 추가했지만 이번에는 추가 GPU 앱을 띄우지 않음.
- teleop 전체 AST에서 콜백을 제외한 부분 및 config JSON 해시가 작업 전과 같음을
  확인함. 수정한 teleop 파일만 runtime에 동기화. 사용자 GUI는 종료하지 않음.
- 현재 실행은 옛 콜백이므로 사용자가 정상 종료 후 다시 --full-record 1로 실행해야 함.
  오류 발생 중의 기존 기록 `output/full_teleop/20260912T143937_362992Z_81c0e0`은
  보존함. 당시 누락된 CHAR 이벤트는 복원했다고 주장하지 않는다.
- 커밋·푸시하지 않음.

---

# 최신 추가 — 2026-09-12, 사용자 요청 평가 규칙 v2

- 짧은 소매의 완전 착의에 만점을 주고 집기 3초 채점을 수정해 달라는 요청 반영.
- 사용자 기록 `output/evaluation/teleop/20260912T133854_105771Z_9caf87`에서는
  파지가 11.15초부터였지만 전체 천 이탈이 19.25초부터여서 집기 5점이 22.25초에
  부여됐음. 기존 최종 원점수는 30.5/50, 양팔 덮임 비율은 각각 0.35였음.
- `short-sleeve-completion-v2`: 동일 그리퍼의 실제 앵커가 그 파지 최초 측정 위치보다
  중앙값 5cm 이상 올라가고 건강한 native attachment를 3초 연속 유지하면 5점.
  옷자락이 테이블에 남아 있어도 됨. physics 240Hz에서 모든 중단을 확인.
  앵커 p95 오차 ≤3.5cm 유지. 평가 전 동작을 소급하지 않으므로 F6은 잡기 전에 누름.
- 양손이 서로 다른 cuff 밖으로 나오고 가슴→목→머리가 collar를 통과하고,
  머리 피부가 collar 평면 바깥인 상태가 0.5초 유지되면 착의 45/45점을 확정함.
  내부 neck 관절의 노출을 강제하지 않음. 피부 최소 거리 허용치는 -5mm.
  집기 5점은 독립이며 합계 최대 50점. 짧은 소매가 하박 전체를 덮을 필요 없음.
- 최고 덮임 진행도·단계·완료 원점수는 유지함. 실제 순간 덮임 비율은 기록에 보존하며
  `coverage_score_overridden`으로 점수만 만점 처리함. 실제 비율을 1로 바꾸지 않음.
- points/s = 원점수/전체 평가 시간은 유지하여 rate는 시간 때문에 하락할 수 있음.
  터미널에 pickup 타이머, dressing/45, TOTAL/50, rate를 분리 표시함.
- measurement-v2는 `gripper_lifted`와 `dressing_complete`가 필수.
  v1은 전체 이탈 조건으로 fallback하고 새 목 증거가 없으면 완료 override는 하지 않음.
  최고 진행도는 새 규칙으로 재채점되므로 결과의 revision을 함께 확인해야 함.
- evaluation 3모듈, CLI 2개, 문서와 회귀 검사 수정. runtime 평가 3모듈 동기화.
  현재 GUI는 이미 옛 모듈을 로드했으므로 재시작해야 적용됨. 사용자 GUI는 보존함.
- 검증: CPU 채점 17개 + 기하학/세션 7개 통과. 짧은 소매, 손/머리 노출,
  잘못된 목 구멍·머리 걸림·손 미노출 거절, 부분 들기와 타이머·점수 유지 검사 포함.
  USD 장면에서 측정기를 생성하고 기존 F슬롯 5개를 읽는 검사도 완료. 슬롯 변경 없음.
- 신규 GPU 실시간 검증은 미완료. 사용자 GUI가 실행 중이어서 별도 검사 프로세스의
  GPU 메모리 할당(64MiB)이 실패하고 PhysX가 종료됨. 앞선 초기화 대기 검사도
  해당 검사 프로세스만 종료했음. 사용자 GUI 프로세스는 생존 확인함.
  GUI를 닫은 후 독립 실행 검증이 남아 있음. `output/evaluation_revision/`의
  verification.json, *_tests.log, slots.json, gpu*.log 참고.
- 기존 카메라·teleop 기록 변경 보존. 커밋·푸시하지 않음.

---

# 최신 추가 — 2026-09-12, 양쪽 로봇 위쪽 RGB-D 카메라

- 각 Stretch의 위쪽 카메라를 정책 입력에 추가해 달라는 요청 반영.
- policy contract 0.3.0: 기본 카메라 5개. 기존 0 overview / 1 robot_0_wrist /
  2 robot_1_wrist 유지, 3 robot_0_head / 4 robot_1_head 추가.
- head는 실제 PhysX camera_center_link에 장착. 로컬 eye=(0.0017,0,0),
  target=(1.0017,0,0), up=(0,0,-1). 모델 중앙 카메라가 베이스 +X 방향으로
  약 35도 아래를 바라보며 영상 위아래도 확인. HFOV70도/clip0.05–5m는
  명시적 시뮬레이션 설정이며 하드웨어 센서 보정/스테레오 노이즈 모델은 아님.
- 모든 시점 RGB/depth/depth_valid 및 카메라 행렬·타임스탬프 제공.
  head pan/tilt action은 없음. 베이스 이동/회전에 따라 head 시점이 움직임.
- 실제 GPU seed42: 5시점 (5,256,256,3), RGB/깊이 유효성, 영상 방향,
  각 head의 base 상대 자세 유지 및 실제 이동, overview 고정 PASS.
  결과 output/head_cameras/report.json, observations.npz, 카메라별 PNG.
  Downloads/PhyRC_robot_0_head_camera.png 및 PhyRC_robot_1_head_camera.png 저장.
- policy_smoke.py의 3개 고정 루프를 실제 카메라 개수로 변경하고 contract 검사 갱신.
  CPU policy contract 및 diff check PASS. sensors.py runtime 동기화.
- 3시점 학습 모델은 기존 config 또는 어댑터에서 rgb/depth/depth_valid[:3] 필요.
- 기존 작업 보존, 이번에도 커밋/푸시하지 않음.

---

# 최신 추가 — 2026-09-12, 마네킹 spawn에 맞춘 외부 카메라

- 이전 고정 시작 구도보다 줌인하고 마네킹 무작위 yaw/위치를 따라 달라는 후속 요청 반영.
- overview 기준 eye=(0,2.8,2.25)m, target=(0,0.45,1.0)m, HFOV=60도.
  `mount=human_spawn`은 매 reset에 마네킹 outer randomSpawn 변환을 기준 카메라에
  적용하고 이후 rollout 중 고정한다. 마네킹 뒤쪽 시점 유지. GUI 카메라는 별개.
- `Policy/sensors.py` reset_episode, `environment.py` 두 reset 경로 연결.
  슬롯은 `stages.py` restore_placement에서 camera-only delta 메타데이터를 보존한다.
  실제 human/cloth physics나 슬롯 파일은 변경하지 않는다.
- GPU seed42(+21.52도)/43(-28.80도)/42 반복: RGB-D, 카메라 위치/시선 방향,
  step 중 고정, 같은 seed 구도 exact 재현 PASS. `output/overview_follow_spawn/report.json`.
- 실제 이미지 `output/overview_follow_spawn/overview_seed_42.png`, `overview_seed_43.png`.
  Downloads에 `PhyRC_overview_follow_seed_42.png`, `PhyRC_overview_follow_seed_43.png` 복사.
- CPU USD 합성 슬롯 복원/무작위화 없는 기준 구도, 기존 policy contract, diff check PASS.
- sensors.py/environment.py/stages.py runtime 동기화. config는 /project 직접 로드.
- 기존 평가/전체 teleop 기록 관련 미커밋 작업 보존. 이번에도 커밋/푸시하지 않음.

---

# 최신 추가 — 2026-09-12, 외부 정책 카메라 구도 변경

- 사용자 요청: overview를 Isaac Sim 기본 실행 화면 구도로 맞춤.
- `config/policy_interface.json`: overview eye=(0,3.15,2.7), target=(0,0,0.4),
  HFOV=60도로 변경. BaseEnv 기본 viewport 위치/방향/수평 시야각과 일치.
- 기본 정책 해상도 256×256 유지. GUI 종횡비에 따라 수직 시야는 다름.
  GUI 환경변수/사용자 시점 이동은 policy 고정 카메라에 자동 전파하지 않음.
- `docs/POLICY_INTERFACE.md` 설명 갱신. config는 /project에서 직접 읽으므로 runtime 복사 불필요.
- 실제 Isaac 캡처: `output/overview_startup_view/overview.png` (512×512 preview, seed42).
  `report.json`: viewport pose 최대 차이 8.96e-9, HFOV 60.000000665도, RGB/depth 유효성 확인.
  CPU `scripts/check_policy_contract.py` 및 `git diff --check` 통과.
- 이번 변경도 커밋/푸시하지 않음. 아래 기존 평가/기록 작업 상태 유지.

---

# 최신 인계 — 2026-09-12, 전체 teleop 기록 및 정확한 3D 상태 replay

이 절이 아래 기록보다 우선한다. 평가 작업 및 이번 전체 기록 기능은 **미커밋으로 유지**했다.
마지막 커밋·원격 HEAD는 계속 `ac73e41`이다. 사용자 PDF/기존 F슬롯은 보존했다.

- 사용자 요구: 실행 파라미터가 1이면 시작부터 모든 teleop 동작을 정확한 시점에 기록하고,
  종료 시 자동 저장한 다음 동일하게 replay할 수 있어야 함.
- 구현 명령:
  - `./run.sh gui --full-record 1` 또는 `STRETCH4_FULL_RECORD=1 ./run.sh gui`.
  - `./run.sh replay output/full_teleop/<실행 ID> [--verify] [--free-camera] [--speed 1]`.
  - 기본 off, `--full-record 0` 가능. `--no-randomization`과 함께 사용 가능.
- `Policy/teleop_recording.py`: 시작 장면 USD, 매 physics-step 로봇 전체 링크 자세,
  관절/베이스 속도·제어값·파지 정점, 천 정점/속도, 사람/의자와 카메라,
  keyboard press/release + control held keys를 기록. 정수 tick과 이벤트 순서 사용.
  16상태 단위 lossless NPZ + atomic manifest, event journal. 밀리면 대기하며 drop하지 않음.
  시작은 첫 사용자 키 입력 전, 앱/셰이더 로딩 후. P/F슬롯 LOAD는 전후 상태를 같은 tick의
  경계로 남기며 PhysX 뷰 재생성 내부 단계를 일반 teleop 궤적에 이어 붙이지 않는다.
- `Policy/teleop_playback.py`, `scripts/replay_teleop.py`: 기록한 3D 상태를 직접 적용한다.
  **키 입력을 다시 넣어 FEM을 재계산하는 기능이 아니며, 내부 solver 상태를 복원하지 않는다.**
  물리/FEM 재시뮬레이션으로 bitwise 동일 궤적을 보장할 수 없어서 상태 playback을 선택했다.
  사용자에게 이 구분을 설명했다. 실제 wall-clock/디스플레이 시간 오차 0이나 픽셀 동일성을
  보장하지 않는다. 처리 속도가 부족해도 기록 스텝을 건너뛰지 않는다.
- replay는 원본 USD를 변경하지 않고 임시 사본의 physics API를 렌더링 전에 제거한다.
  Isaac 6의 `OmniPhysics*` API도 반드시 제거해야 한다. `Physics*`/`Physx*`만 제거하면
  background deformable cooking이 계속 발생한다. authored apiSchemas 전체 토큰을 사용한다.
- 자동 저장: Esc/창 닫기/Ctrl+C/SIGTERM의 정상 종료 경로. SIGKILL/전원 차단은
  최신 완성 chunk까지만 복구 가능, `complete=false`와 `--allow-incomplete`로 구분한다.
- 검증:
  - `scripts/check_teleop_recording.py`: CPU 무손실, 시간 경계, 파일/이벤트 무결성 4 tests PASS.
  - `scripts/check_full_teleop.py`: 실제 teleop main에 합성 keyboard 입력.
    두 로봇 lift/arm, gripper 입력, P reset, F2 save/load, Esc 종료 검증 PASS.
    기록: `output/full_record_checks/2a6b564b13/recordings/20260912T112840_867052Z_62e6e8/`.
    112개 연속 physics tick, 경계 포함 118개 상태. 로봇 joint 변화 각각 약 0.532/0.527.
  - 실제 로그에서 W press tick=4, control 적용 tick=4, 최초 반영 physics tick=5 확인.
  - SIGTERM 자동 저장도 별도 실제 teleop 실행으로 PASS:
    `output/full_record_checks/c081035bdc/report.json`, 118상태, complete=true,
    exact_input_application_tick=true. `signal_stop.log` 및 `latest.json` 참조.
  - CPU 및 GPU 렌더링 replay 모두 118개 전 상태의 천 vertices / robot xyz+quaternion
    exact array readback PASS. renderer 갱신 후에도 확인.
    `output/full_record_checks/replay_cpu.json`, `replay_gpu.json`.
    `replay_final.png` 시각 확인 완료. source scene SHA256 불변 확인.
  - 마지막 합성 기록의 크기는 약 53MiB (초기 scene 약 14MiB 포함); 장기 녹화 저장량 큼.
  - 상세 사용법 및 보장 범위: `docs/FULL_TELEOP_RECORDING.md`.
- 실행용 `.runtime`에는 수정한 teleop 및 새 recording/playback 모듈을 동기화했다.
  생성 에셋 재생성이나 사용자 슬롯 변경은 하지 않는다.

---

# 이전 인계 — 2026-09-12, teleop 및 학습 정책 실시간 평가 연결

이 절이 아래 초기 채점 구현 기록보다 우선한다. **평가 관련 작업은 계속 미커밋이며,
사용자 지시대로 커밋·푸시하지 않는다.** 원격 마지막 커밋은 README GIF의 `ac73e41`이다.

- 후속 사용자 요구: 직접 teleop할 때와 나중에 학습한 로봇 정책을 실행할 때 모두 평가 가능해야 함.
- 완료: 공통 `Policy/evaluation_live.py` (`IsaacMeasurements`, `EvaluationSession`) 및
  `Policy/evaluation_geometry.py`를 추가했다. 실제 천 위치/native attachment/포즈 적용 관절을 읽는다.
- GUI: 기존 `./run.sh gui`, **F6 시작 / F7 종료·저장**, 1초마다 터미널 점수 출력.
  결과는 `output/evaluation/teleop/<실행 ID>/result.json`, 이력 `samples.jsonl`.
  P reset, 기존 F슬롯 LOAD, 비유한 상태 복구는 평가 무효. 슬롯 SAVE는 계속.
  Esc 종료 시 진행 중 평가 저장. 평가를 시작하지 않으면 physics 측정 콜백도 없음.
- 정책: `scripts/evaluate_policy.py`가 여러 seed를 reset해 동일 측정기로 평가한다.
  `--policy` Python 어댑터 + `--checkpoint`, `--seeds`, `--seconds` 지원.
  기본 actor_rgbd, measured_state 선택 가능. `--zero-policy`는 중립 행동 테스트용.
  `scripts/phase1_torchscript_policy.py`는 Dict[str, Tensor] -> (2,9) TorchScript 어댑터.
  일반 state_dict/checkpoint 모델에는 해당 구조와 전처리를 복원하는 어댑터가 필요하다.
- 포즈 적용 시 `phyrc:posedJointPositions` 읽기용 메타데이터만 추가했다.
  기존 skeleton은 bind pose로 남기 때문에 원래 skeleton query는 평가 관절로 부적합하다.
  물리 파라미터·천 형상·기존 조작 속도는 변경하지 않았다.
- 기하학 기준은 `phase1-centreline-v1`: 가상 cap으로 닫은 천 내부에 들어간 팔
  중심선 길이 비율(40표본), 커프 통과를 함께 요구. 이는 PDF의 미정 사항에 대한 구현 정의다.
  짧은 소매 정상 착의가 팔 전체 길이 100%를 덮지는 않는다. 실제 완전 착의/오삽입 장면
  전체에 대한 정확도 검증은 미완료이며 공식 경기 판정으로 확정됐다고 설명하지 않는다.
- 파지/테이블 이탈은 physics 240Hz, 기하학 및 점수 기록은 20Hz.
  geometry 표본 사이 한 스텝 파지 상실도 다음 점수 표본에 반영해 연속 3초 판정을 끊는다.
- 검증 완료:
  - `scripts/check_phase1_evaluation.py`: CPU 채점 13 tests PASS.
  - `scripts/check_phase1_live.py`: CPU 기하학·파지 중단·세션 lifecycle 5 tests PASS.
  - 실제 Isaac 중립 정책 seed42/43 실행: `output/evaluation/integration_check/`, 각 0.2초/0점.
  - 실제 teleop main에 headless 합성 키 입력: `scripts/check_phase1_teleop.py`,
    `output/evaluation/teleop_integration/report.json` passed=true.
    F6/F7, P 무효, F1 LOAD 무효, Esc 저장 검증. 테스트 전용 슬롯만 사용.
  - TorchScript 테스트 checkpoint를 실제 로드해 actor_rgbd seed42/43 실행:
    `output/evaluation/saved_policy_check/summary_20260912T102654_311977Z_168575/scores.json`.
    각 0.2초/0점. 이 모델은 합성 중립 행동 모델이며 학습 성능 증거가 아니다.
  - 마지막 GPU 프로세스 정상 종료, 활성 프로젝트 컨테이너 없음.
- 사용법은 `docs/PHASE1_EVALUATION.md`. README에도 F6/F7 및 정책 실행기 안내를 추가했다.
- 실행용 `.runtime`에는 수정한 teleop 파일과 evaluation*.py만 동기화했다.
  생성 에셋이나 사용자 저장 슬롯을 재생성/덮어쓰지 않았다.

---

# 초기 인계 — 2026-09-12, README GIF 및 Phase 1 채점

이 절이 아래 기록보다 우선한다.

- 사용자 요청 1: GitHub README에서 직접 동작을 볼 수 있게 수정 후 커밋·푸시.
  - 완료: `ac73e41` (`Show inline animated demonstration in GitHub README`).
  - 원본 35.8초/8배속 전·후면 영상을 800×225, 6fps, 약 9.9MiB 반복 GIF로 변환.
  - `README.md`와 `docs/videos/Front_Back_8x.gif`만 해당 커밋에 포함.
  - GitHub README HTML에 `img` 및 `data-animated-image`가 표시되는 것 확인.
  - `origin/main` SHA가 `ac73e41c74d109e4e9d73e497dfff586066c4abe`임을 확인.
- 사용자 요청 2: Downloads PDF의 Phase 1 기준으로 평가 함수와 최종 점수 출력 작성.
  **사용자가 이 작업 이후 커밋·푸시하지 말라고 명시했다. 아래 변경은 미커밋으로 유지한다.**
  - 기준: `/home/seoyul/Downloads/PhyRC_proposals.pdf`, 6쪽 IX.E.a.
    SHA256 `514b5398b9815e0b0b63718e81e148aa8b2c9ac559644b45ffa6fc3ac1b7c037`.
  - `src/DexGarmentLab/Policy/evaluation.py`: 5+5+5+5+10*n+20*m (최대 50점),
    총 시뮬레이션 작업 시간으로 나눈 points/s, 여러 seed 및 제출 집계,
    기존 DressingEnv에 연결할 수 있는 측정 콜백 evaluator.
  - `scripts/evaluate_phase1.py`: 측정 JSON 또는 `--demo`를 채점하고 최종 점수 출력.
  - `scripts/check_phase1_evaluation.py`: CPU 테스트 13개 모두 통과.
  - `docs/PHASE1_EVALUATION.md`: 측정 계약, 사용법, PDF 미정 사항에 대한 가정.
  - README 평가 안내와 이 handoff도 미커밋 변경이다.
  - `output/evaluation/demo_measurements.json`, `demo_scores.json`: 합성 예제,
    50/10과 20/10의 평균 3.5 points/s. 실제 Isaac 성능 결과가 아니다.
  - 실제 손목 통과/팔 덮임 등 장면 측정기는 새로 구현하지 않았다. 현재 info만으로
    모든 지표를 얻을 수 없어 검증된 측정 콜백 또는 측정 로그가 필요하다.
    GPU 자동 착의 평가를 완료했다고 설명하지 않는다.
  - Python compile, diff whitespace 검사 통과. 물리·형상·기존 정책 코드 변경 없음.
- `docs/PhyRC_proposals.pdf`는 요청된 Downloads 파일과 해시가 다르다.
  기존 untracked 파일을 수정하거나 커밋하지 않고 보존했다.

---

# 다음 에이전트 인계 — 2026-09-12 03:00 KST

이 문서 상단이 현재 상태의 기준이다. 아래 과거 기록의 실행 중인 컨테이너,
미커밋 상태, 다음 작업 지시는 이 상단과 충돌하면 과거 정보로 취급한다.

## 1. 사용자의 최신 요청과 현재 상태

- **최신 커밋 상태**: GitHub 원격 `origin/main`에 완전 푸시 완료 (최신 커밋: `dbee8c7`).
  - `git status` 클린 (단, 사용자가 절대 건드리지 말라고 지정한 `docs/PhyRC_proposals.pdf`는 untracked로 보존).
- **티셔츠 앞면 V넥 컷아웃 및 형상 (V-Neck Cutout)**:
  - 처음 티셔츠가 스폰되어 상자/테이블 위에 놓였을 때 천장(ceiling, 앞면, $Z < -0.0005\,\text{m}$)을 향하는 면에 V넥 개구부 적용.
  - 뒷면 목둘레 및 목 개구부(칼라) 기본 둘레를 축소/확대하지 않고 보존하면서, 앞면만 시각적으로 선명한 대칭 V자 형태로 컷아웃.
  - 정밀 2-다양체(manifold) 유지: 총 39개 내부 삼각형 제거, 9개 경계 재봉합 삼각형 추가.
  - 꼭짓점(Apex, $v1169$)을 $Y=0.360$ (깊이 $8.6\,\text{cm}$)로 완만하게 당겨 삼각형 뒤집힘(flipped faces) 없이 4개의 매니폴드 경계 루프(목둘레 1개, 소매 커프 2개, 밑단 1개) 완벽 유지.
  - 롱 셔츠(`t_shirt.usd`, 5115 pts, 10030 faces)와 숏 셔츠(`t_shirt_short.usd`, 4020 pts, 7836 faces) 모두 호환 매핑 적용.
  - **옷의 물리 특성(FEM 솔버, 질량, 강성, 마찰 등) 일절 변경 없음**.
- **V넥 노란색 보색 줄무늬 (Yellow Stripe Band)**:
  - 옷의 밑단(hem) 줄무늬 두께($4.2 \sim 4.9\,\text{cm}$)와 균형을 맞추기 위해 V넥 보색 밴드 폭을 **$4.1\,\text{cm}$** ($W=0.041\,\text{m}$)로 확장.
  - 쿼드(quad) 격자 대칭성에 맞춰 V선 좌우 대칭으로 균일하게 확장되며, 어깨선이나 뒷면 목덜미로 누출되지 않도록 경계 제한.
  - 메쉬에 `vneck` GeomSubset(`materialBind`)으로 등록되고, `Teleop_TShirt_Stretch4_Env.py`에서 밑단과 동일한 노란색 보색 재질(`_mat`, `GARMENT_HEM_BY_COLOR`)이 바인딩됨.
  - 확인용 이미지:
    - 2D 전개도: `output/smooth_preview.png`
    - Isaac Sim 3D 시뮬레이션 테이블 위 렌더: `output/sim_vneck_closeup.png`
- **README 동작 예시 영상 추가 (Demonstration Video)**:
  - `~/Documents/PhyRC_Video/20260912/Front_Back_8x.mp4` (25.8MB, 8배속 전/후면 듀얼 뷰)를 `docs/videos/Front_Back_8x.mp4`로 복사.
  - `.gitignore`에 `!docs/videos/*.mp4` 예외 등록하여 정상 추적.
  - `README.md`의 `# PhyRC 2027` 바로 아래 `### 동작 예시 (Demonstration)` 섹션에 HTML5 비디오 플레이어 및 마크다운 링크 추가.
  - 8번 GUI teleop 튜토리얼 항목에 V넥 줄무늬 시각 확인 안내 추가.
- **휠 들림 방지(Wheel-Lift Prevention) 기능 (커밋 `1ec4d48`에 반영 및 푸시됨)**:
  - Layer 1 (명령 클램핑: `target_lin_vel[2] = min(cur_lin_vel[2], 0.0)`) + Layer 2 (240Hz physics pre-step P-컨트롤러: $z\_err > 0$ 시 하향 복원 속도 주입).
  - 환경변수 `STRETCH4_PREVENT_WHEEL_LIFT` 토글 지원 (기본값 1).
- **회귀 검증**:
  - `./run.sh prepare`: 롱/숏 에셋 모두 오류 없이 생성 완료.
  - `./run.sh policy-smoke`: `POLICY-SMOKE-PASS /output/policy-smoke/report.json` 통과.
- **Git 커밋 이력**:
  - `dbee8c7`: `Add V-neck cutout with matching yellow stripe and operation demo video` (최신 HEAD, origin/main 푸시 완료)
  - `1ec4d48`: `Add wheel-lift prevention and update handoff documentation`
  - `026fb5e`: `Update handoff document branch reference to main`

## 2. 완료 범위와 미완료 범위

| 항목 | 확인된 결과 |
|---|---|
| 티셔츠 세로/가로 길이 및 소매 크기 | 이전 원본(`output/t_shirt_short_prev_0.7.usd`, 높이 0.556m, 가로 0.679m, 소매 좌 62.8mm/우 61.1mm)으로 100% 완전 원복 완료 |
| 노란 줄무늬 위치 | 밑단 최하단 테두리 Y [-0.2232m, -0.1697m]에 `hem` GeomSubset(460개 면) 바인딩 원복 완료 |
| 로봇 속도 설정 | 10% 상향 유지 (LIFT 1.54, ARM 1.21, WRIST 5.5, BASE 0.616/2.86, ACCEL 1.32/4.40) |
| 마찰 계수 설정 | 옷-마네킹 0.0 (min combine, 무마찰), 옷-그리퍼 0.5 (max combine), 옷-상자 0.5 (max combine) 정상 유지 |
| 카메라 시점 | `BaseEnv.py` 기본 시작 시점이 거리 약 3.9m (`eye=[0, 3.15, 2.7]`, `target=[0, 0, 0.4]`)로 줌인됨 |
| 두 로봇 동시 집기·들기 | 수정된 structured policy로 기준 위치 3회, +1cm 1회, −1cm 1회 모두 통과 |
| 동시 들기 유지 | 각 로봇 약 9~10cm 상승, 두 실제 grasp를 유지한 채 2초 공동 유지 |
| 한 로봇 소매 집기 | upper-middle 소매 위치에서 약 8.75cm 상승, 1초 유지 반복 통과 |
| 두 팔 삽입 | 미완료. 연속 이동에서 소매가 팔 밖으로 가거나 로봇이 넘어지는 실패 |
| 한 팔 삽입 | 손 통과 장면과 47개 연속 정상 crossing step(2.35초)은 확인. 최종 안정 유지와 반복 성공은 실패 |

## 3. 현재 GUI 상태와 작업 슬롯

- GUI 컨테이너: 현재 활성 컨테이너 없음 (`docker ps` 클린).
- 직접 실행 명령어:
  ```bash
  PHYRC_ACCEPT_EULA=1 \
  STRETCH4_RANDOMIZE=0 \
  STRETCH4_SHOW_COLLIDER=0 \
  STRETCH4_STATE_DIR=/output/manual_control_20260911_1905/states \
  ./run.sh gui
  ```
- 백업 경로: `output/t_shirt_short_prev_0.7.usd`, `output/manual_control_backup_20260911_1941/`.
- 보존 원본 슬롯: `/home/seoyul/PhyRC_backups/dressing_stages_20260911_155147/` (15개 파일 SHA256 불변 유지).

## 4. 물리 및 제어 설정 요약

- FEM 64, 로봇 속도 10% 추가 상향 (LIFT 1.54, ARM 1.21, WRIST 5.5, BASE 0.616/2.86), contact guard 최종 재검사 및 기본 24회 repair.
- 뒤통수 둥글게 수정, 전체 손에 맞춘 collider, 목을 보존한 옷 높이 10/12 (0.556m).
- 옷-마네킹 마찰 0.0 / combine=min (완전 무마찰 유지).
- 그리퍼 마찰 0.5 / combine=max (손가락/핑거팁 8개 콜라이더, 파지력 복원).
- 상자(테이블) 마찰 0.5 / combine=max (옷이 상자 위에서 얼음처럼 미끄러지지 않도록 복원).
- native attachment 및 성공을 위한 물리/충돌 허용치 완화 없음.

## 5. Git 상태

- 작업 경로: `/home/seoyul/PhyRC_2027`.
- 브랜치: `main`.
- origin: `git@github.com:0x4A656F6E2053656F79756C/PhyRC_2027.git`.
- 수정 파일: 없음 (작업 트리 클린).
- `docs/PhyRC_proposals.pdf`는 무관한 untracked 파일이다. 보존하고 커밋에 넣지 않는다.

## 6. 다음 에이전트가 읽을 소스와 결과

주요 상세 문서:

- `docs/GRASP_LEARNING_20260911.md`: 실험 결과, 재현 명령, 정책 범위.
- `docs/POLICY_INTERFACE.md`: 관측/행동/시간 간격과 환경 계약.
- `docs/verification-results/continuous-dressing-20260911.json`: 삽입 실패 증거(현재 thread v4까지; 중단된 oriented 결과는 아래 로컬 report 참조).
- `docs/verification-results/policy-smoke-20260911.json`: 전체 GPU 환경 smoke 결과.
- `docs/verification-results/pickup-policy-invariants-20260911.json`: structured 정책 CPU 검증.

주요 소스:

- `src/DexGarmentLab/Policy/`: 복원한 contract/state/sensors/environment 및 새 stages/pickup_policy/dressing_task/material_policy.
- `scripts/train_dual_grasp.py`, `scripts/train_grasp.py`: 실제 집기와 연속 삽입 실험.
- `scripts/check_policy_contract.py`, `scripts/check_pickup_policy.py`, `scripts/policy_smoke.py`.
- `run.sh`: `train-grasp`(dual), `train-single-grasp`, `train-demo`, `policy-smoke`.
- teleop의 공통 초기화 및 `drive_robot(..., commands=None)` 숫자 명령 경로를 추출했다. 키보드 경로는 유지했다.
- 과거 정책 인터페이스/작은 lift BC는 `e409213`에서 복원했다. 과거에도 완성된 dressing/RL은 아니었다.
- 정책은 20Hz, control 60Hz, physics 240Hz. 기본 reward는 0이고 evaluator 주입을 지원한다.

체크포인트:

| 디렉터리 | 범위 |
|---|---|
| `checkpoints/dual_pickup_20260911/` | structured dual planner v4, 650개 실제 transition. `evaluations.json`에 5회 통과, offset 재검증 pending=false |
| `checkpoints/cuff_pickup_20260911/` | structured single cuff planner v3, 241개 transition. upper-middle target transfer도 실험 기록 |
| `checkpoints/grasp_pickup_20260911/` | 초기 한 로봇 옷자락 pickup MLP. 팔 삽입 정책 아님 |

정책 해시:

- dual: `8a7f5cceb4b06dab0e9f696378f6bab9eaeb912c8c26535a022f3187ac14dd68`.
- cuff: `c50b8a34aef5b4e49a3f76221db7c71842f56bf9dc010d62a255dd2db94c62f1`.

## 7. 마지막 실험의 정확한 중단 지점

- `output/single_thread_oriented_v1/report.json`: `status=paused_by_user`, `success=false`.
- headless 컨테이너 `thirsty_kare` / `36545019c568`를 사용자 요청으로 중단했다. 이전 실행 세션 `16407`은 활성 학습이 아니다.
- 실제 F1 한 로봇 pickup(약 8.77cm), raise, carry까지 성공 후 첫 cuff normal alignment 도중 중단했다.
- 마지막 기록의 normal alignment cosine 약 0.402로 목표 0.75에 미달했다. 전체 orientation/insertion 검증은 완료되지 않았다.
- 보존된 단계 스냅샷:
  `output/single_thread_oriented_v1/states/slot_RELOADED_0.npz`,
  `slot_MATERIAL_TEACHER_RAISE.npz`, `slot_MATERIAL_TEACHER_CARRY.npz`.
- 중단 순간의 alignment 최종 상태는 저장하지 못했다. 위 carry 스냅샷을 정확한 중단 상태라고 설명하지 말 것.

이전 중요한 연속 실험:

| 경로 (`output/` 아래) | 결과 |
|---|---|
| `dual_continuous_v3` | 동시 집기 이후 reference 경로 이동, 실제 grasp 유지/최종 visual 교차 0이나 양 소매 모두 삽입 실패 |
| `dual_material_v1` | 동시 집기 성공 후 carry 중 한 로봇 넘어짐 |
| `single_cuff_v5` | upper-middle 집기/운반 성공, F3 wrist rotation에서 anchor 오차 6cm 초과 |
| `single_thread_v2` | 정렬/이동 성공, 옷이 팔 아래/바깥으로 지나감. 이미지에서 삽입 아님 확인 |
| `single_thread_v3` | 47개 정상 crossing step, 손 통과 시각 확인. 이후 anchor 오차 약 3.5cm 경계, 최종 유지 실패 |
| `single_thread_v4` | 40 crossing step 이후 멈춤/3초 유지 제어를 추가했으나, 재실험은 해당 gate 이전 anchor 오차 6.067cm로 중단 |

## 8. 현재 코드에 있지만 아직 검증되지 않은 실험 옵션

`Policy/material_policy.py`와 `scripts/train_grasp.py`:

- `--orient-cuff`: 관측한 소매 입구 normal을 팔 방향으로 회전시키며 중심을 추종한다.
  각도 보정은 0.25배, 최대 0.25rad; plane ratio >=0.6이면 회전을 유지한다.
  첫 GPU 실험이 사용자 요청으로 중단되어 효과는 미확인이다.
- `--release-after-insertion`: **컴파일만 통과, GPU 미실행**.
  정상 grasp 상태에서 40 crossing step + visual 교차 0 확인 후 일반 open 명령,
  12 tick 대기, 바깥 방향 6cm 후퇴, 총 80 post-insertion step 확인을 시도한다.
  최종 후보는 실제 attachment 해제, 실제 후퇴 >=4cm, 지속 crossing, visual 교차 0을 요구한다.
  이는 release 가설용 코드이며 성공 사례/검증된 기능으로 취급하지 않는다.
- release 소스는 oriented 실험이 모듈을 로드한 뒤 바뀌었다. 각 실험 output에 캡처한 소스/해시가 그 실험의 기준이다.
- 정상 held-grasp 후보 기준: anchor p95 <=3.5cm, upright, 40개 연속 crossing,
  visual 교차 0 및 추가 정지 유지 60 step. anchor >6cm 또는 grasp 상실 시 중단한다.
- 안정적인 물리 teacher가 성공해야만 material policy를 학습하고 저장/재로드한 뒤
  새 F1에서 집기부터 전체 연속 경로를 평가하도록 구현했다. 아직 그 단계에 도달한 성공 teacher가 없다.
- `arm_insertion_verified`는 렌더링을 직접 확인하기 전 true로 바꾸지 않는다.

## 9. 검증 및 재개 순서

이미 완료한 검증:

- GPU policy smoke: 실제 RGB-D freshness/depth, 8개 행동 0.4초, seed reset, invalid action, termination/truncation 통과.
  반복 reset cloth 차이 최대 약 0.9995mm.
- CPU policy contract 및 structured weights의 zero-error/1cm 방향 반응/phase gate 검증 통과.
- 당시 Python compile, shell 문법, whitespace 검사 통과. 최신 선택적 release 옵션은 compile만 통과했다.
- 중단 뒤 `cp -a src/DexGarmentLab/. .runtime/DexGarmentLab/` 실행 후 현재 GUI를 시작했다.
- Isaac GPU simulator는 한 번에 하나만 실행한다. CPU-only 검사는 실행 중 컨테이너에서 가능하다.
  `/project`는 컨테이너 안에서 읽기 전용이고 결과는 `/output`에 쓴다.

사용자가 재개를 요청하면:

1. 현재 GUI/사용자 수동 작업 상태를 먼저 확인하고 필요한 사용자 상태를 보존한다.
2. 원본 F1 GUI 자동 덮어쓰기 문제와 실제 학습 입력 경로를 구분한다.
3. 상세 문서 및 thread v3/v4 이미지/anchor trace를 읽고 삽입 실패 원인을 확인한다.
4. oriented 중단 결과를 정리하고, orientation 또는 release 가설 중 하나를 제한된 실험으로 검증한다.
   물리 설정이나 성공 판정 문턱을 낮추어 성공으로 만들지 않는다.
5. F1 실제 집기부터 연속 진행하고 저장 상태를 중간 복원하지 않는다. 삽입 후 안정 유지와 렌더를 확인한다.
6. 성공 teacher가 생기면 학습/체크포인트 재로드/새 F1 반복 평가까지 수행한다.
7. 새 결과를 docs/evidence/handoff에 반영하고 intended 파일만 최종 stage/commit/push한다.

지금은 위 재개 절차를 실행하지 말고 사용자의 다음 지시를 기다린다.

---

# 과거 기록 — 아래 실행 상태와 지시는 현재 상태가 아님

# CURRENT UPDATE: 2026-09-11, user stages preserved and gripper friction trial

This update supersedes earlier GUI-stopped and uncommitted-geometry statements.

- User launched `happy_cori`; its scene was visually inspected with the
  mannequin wearing the shirt and both grippers released. It has now been
  closed normally at the user’s request; its --rm container is gone.
- F1–F5 stages are preserved read-only with verified hashes outside the project:
  `/home/seoyul/PhyRC_backups/dressing_stages_20260911_155147/`.
  Future F-key writes cannot overwrite them. Do not point a GUI at this archive.
- Geometry/randomization follow-up was committed as `007e7cd`.
- Gripper friction now defaults to 0.2 using only eight finger/fingertip materials
  with combine=max. Cloth remains 0; mannequin remains 0/min. Native attachments
  and guards are unchanged. The historical pre-zero cloth coefficient was 0.2.
- Source and runtime were updated, and the current live GUI received the same
  material change through Script Editor without restart. CPU actual-asset USD
  isolation/rollback checks and live effective bindings passed. No post-change
  physical pull/slip measurement or dressing replay has been performed.
- User clarified that rollback must be through code, with no extra GUI windows.
  The temporary panel and Script Editor were closed, the Script Editor extension
  disabled, and the local panel-creation scripts retired. Production source and
  runtime contain no panel creation. Future normal launches create no trial UI.
- Keep gripper friction at 0.2 unless the user requests rollback. To roll back
  through code, change the `STRETCH4_GRIPPER_CONTACT_FRICTION` fallback from 0.2
  to 0 in `ZeroSceneFriction.py` and synchronize source/runtime. Geometry and
  human friction remain unchanged. Friction is isolated in commit `83dd0ec`.
- Shutdown snapshot is preserved at
  `/home/seoyul/PhyRC_backups/gui_shutdown_20260911_160840/shutdown_state.npz`.
  F1–F5 active and archived copies were checksum-verified unchanged afterward.
- Pre-change live snapshot: `output/friction_trial_20260911/before_live/slot_LIVE.npz`.
  See `docs/GRIPPER_FRICTION_20260911.md` for evidence, backup and restore details.
- The unrelated `docs/PhyRC_proposals.pdf` remains untracked and preserved.

---

# Latest handoff: contact guard correction installed, 2026-09-11

This section supersedes the historical notes below, especially statements that
head rounding is rolled back or that no full-scene reproduction exists.

- Project: `/home/seoyul/PhyRC_2027`; original Documents project remains separate.
- Native FEM garment solver: 64. Motion defaults: 90% of the original rates.
- Posterior head is rounded in both visual geometry and derived collision mesh.
- Source and runtime now contain the tested contact-guard correction: final
  post-repair recheck, default 24 repairs, optional
  `STRETCH4_CONTACT_GUARD_ITERATIONS` from 1 to 128.
- Collision protection and genuine unresolved-contact fallback remain enabled.
- Full native-FEM replay reproduced the original persistent freeze, including
  persistence after both grippers opened. Rounded-head/90%-speed tests completed
  9760 physics steps without a whole rollback, for both corrected and legacy
  guards. Do not claim the full-scene difference is solely due to the guard fix.
- The final-check defect and its correction were independently verified on
  exact captured failure inputs on the GPU.
- Details and evidence paths: `docs/CONTACT_GUARD_FIX_20260911.md`.
- Audit root: `/home/seoyul/PhyRC_diagnostics/head_freeze_u2hIuWWo`.
- Original GUI was backed up through `event_0008_user_marker`, physics step
  131196, then its recorder was flushed and container stopped. Backups:
  `goal_v3/final_gui_checkpoint.tar` and `goal_v3/before_guard_install.tar`.
- Final GUI launcher: `launch_final_gui_v4.sh` under the audit root. Container:
  `phyrc-audit-final`. Session pointer: `active_final_gui.json`. Verify the real
  process, `runtime_config.json`, `self_test.json` and observations before
  claiming it is running; a pointer file alone is not proof.
- Final GUI uses private slot copies and the latest backed-up original GUI F5.
  Earlier slot contents remain in the backup; project output slots are untouched.
- Hardware investigation found container-specific NVIDIA device-access loss
  consistent with a later systemd reload, not proof of a new GPU hardware fault
  or the cause of the earlier freeze. No host driver/Docker reinstall was done.
- Do not use `goal_v3/raw_pre_failure_seeds`: experimental, unused, missing the
  final production velocity cap. See its `DO_NOT_USE.md`; regeneration approval
  is still pending and is not needed for the already completed valid replays.
- No commit or push was made for this correction. Preserve unrelated files,
  including `docs/PhyRC_proposals.pdf`.

---

# Historical handoff below (may describe superseded state)

# Current investigation: intermittent cloth freeze, cause not established

2026-09-11. The user requested investigation of apparent cloth detachment and
freezing that can recover without input. The pre-head rollback below remains
active; no additional production physics/control changes were made.

- Audit evidence and scripts: `~/PhyRC_diagnostics/head_freeze_u2hIuWWo/`.
  Read its `FINDINGS.md` before drawing conclusions from previous smoke tests.
- Preserved audit-start output and a user-approved live snapshot. The snapshot
  reported both robots holding 256 vertices; its timing relative to spontaneous
  recovery is unknown. The user's original F-slots were preserved.
- Original-image/full-original-stage and migrated-image/Home-stage GPU replays
  used the same pre-head main, shirt geometry and fixtures. Both executed the
  protection callbacks, and both showed transient centimeter-scale grip errors
  without missing attachment prims. The exact prolonged freeze was not reproduced.
- Both opposed-lift/wait replays completed with 5,760 pre/post/sweep calls and no
  full-cloth rollback. Their trajectories and correction counts differed; no
  repeat-control study was completed to attribute that difference.
- Earlier global-rollback speculation is NOT a confirmed root cause. F-slot
  loading clears guard caches and rebuilds attachments, so it does not preserve
  all internal simulator history needed to reproduce a transient lock.
- A passive diagnostic GUI is launched with `launch_observer.sh`, original image
  `phyrc-stretch4:isaac-6.0.1`, read-only Home runtime, container `phyrc-audit-live`.
  It restores the captured live snapshot, uses isolated slots, samples errors
  before/after guarding and can save up to eight separate event snapshots.
  Query whether it is still running before any GPU launch.
- A bare-variable forwarding compatibility difference in run.sh was identified
  but not changed: some original FEEL aliases need a STRETCH4_ prefix in the new
  launcher. Neither observed GUI had such overrides. It is not the established
  cause of the current incident.
- No complete recovery or stability certification is claimed. Investigation
  files and the worktree have not been committed or pushed during this audit.

---

# Previous: diagnostic restoration to immediately before the head edit

2026-09-10. The user requested a rollback for investigation, not a physics fix.
The active maintenance checkout remains `~/PhyRC_2027`. This section supersedes
all physical-state and verification claims below.

- Restored the exact archived teleop main, resize_shirt.py, make_wearable_shirt.py and both generated Modelink USDs from the snapshot immediately before the combined head-rounding/height-restoration request.
- Removed the head-rounding helper from source and generated runtime. The original posterior head shape is therefore restored, including its known protrusion.
- Removed SHIRT_HEIGHT_SCALE from geometry.json. The shirt retains the earlier uniform 1.2 enlargement and collar-area correction; the later Y-only 10/12 transform is no longer applied. The original archived generator recomputes its pre-head mass metadata when prepare is explicitly run.
- Native grasp, contact guards, robot control, physics rates and solver settings were not edited. The standalone migration launcher remains in place, rather than installing the incompatible original-project launcher.
- Complete pre-rollback project/Git/runtime files, excluding disposable caches and separately preserved output, are in `~/PhyRC_backups/20260910_234215_before_pre_head_restore/current-project-with-git-runtime.tar.gz`. The previous output directory was moved intact to `output-current/` in that same backup directory. The rollback input archive is also copied there as `pre-head-source-assets.tar.gz`.
- Copied the historical F1-F4 slots to `output/states_large20_neck20_near1m_mesh4/`. F1 is automatically overwritten at GUI startup; the historical originals remain preserved outside this checkout. The historical LIVE is copied separately to `output/pre_head_reference/live_before.npz`; it was not automatically loaded or substituted for an F-slot.
- The original `~/Documents/PhyRC_6.0.1` files and currently running GUI `youthful_lederberg` were left untouched. That existing GUI still runs the post-head-edit original source; close it before launching the restored Home checkout. Do not run two GPU SimulationApps at once.
- No preparation, simulation, syntax checks or verification were run after restoration. Existing smoke assertions and scene baselines require the post-head rounded geometry and do not certify this diagnostic rollback. Tests were intentionally not modified.
- Changes are left uncommitted and unpushed for the user's comparison. Git history and the unrelated untracked proposal PDF are preserved. The source checksum manifest describes the restored inputs, not a passing runtime test.

Launch only after closing the existing original-project GUI:

```bash
cd ~/PhyRC_2027
export PHYRC_ACCEPT_EULA=1
./run.sh gui
```

---

# Historical migration record (post-head-edit baseline, not current physics)

# PhyRC_2027 maintenance handoff

2026-09-10: minimal standalone migration and installation/teleop verification
completed. This repository, rather than the old patch pipeline, is the maintained
working source going forward.

## Repository and operation

- GitHub: https://github.com/0x4A656F6E2053656F79756C/PhyRC_2027, private, branch `main`, SSH origin.
- Local folder: `~/Documents/PhyRC_2027`. Git identity uses the user's existing global configuration.
- Authenticated GitHub CLI: `~/.local/bin/gh`. Credentials are in the OS keyring, never this repository.
- Read README.md for fresh-machine installation and teleop; read THIRD_PARTY.md before any public redistribution.
- Commands: `export PHYRC_ACCEPT_EULA=1`, then `./run.sh build`, `./run.sh prepare`, `./run.sh smoke`, `./run.sh gui`.
- Only one GPU SimulationApp at a time. Verification GUI was closed with Escape.
- Source edits belong in `src/DexGarmentLab`, not generated `.runtime`. Do not reapply old `patch_stage.py` onto these already-patched files.

## What is included

Sixteen current runtime Python files, the three original geometry-generation
helpers, the compatibility shim, container/launcher/downloader code, and four
indispensable local asset files (robot USD, Modelink source USD, female USD and
its JPEG). Exact public downloads for those custom inputs were not established.

The floor JPEG and linen material USD/BaseColor/Roughness are downloaded from
pinned public revisions and checksum-checked. Isaac Sim and Python libraries are
installed from external sources. No old caches, trained policies, datasets,
backup archives or user F1-F5 slots are committed. Submodules are intentionally
absent: the executed teleop was an extensively modified local snapshot, not an
unmodified upstream checkout with a known matching commit.

## Latest simulation configuration

- Isaac Sim6.0.1 native surface FEM; physics240Hz, render/control60Hz, TGS, solver32, collision updates4/iterations4.
- One blue shirt/yellow hem, four tables, two Stretch4 robots.
- Sleeve reach .375 and straight T rest sleeves; global resize1.2 followed by height10/12, keeping the widened X/Z dimensions.
- The height restoration also changes the collar shape; do not describe the final collar as still exactly +20% area.
- Cloth15946 vertices/31464 triangles after refinement; density18.3216174, mass approximately129.763g, thickness10mm, Young25000, bend450.
- Human Y.45 and chair follow, total1m move toward tables. Arm spread10 degrees per side, elevation input20.
- RoundHead runs before CollisionBody creation;625 vertices trimmed. Both visual and collision meshes retain the rounded posterior skull.
- Control rates, safety guards, native grasp and contact settings are unchanged from the original active source.
- Default slots: `output/states_shortheight_roundhead_mesh4`. F1 is overwritten with initial state each launch. Older-geometry slots are not compatible merely because node counts match.

## Verification and preservation

See docs/VERIFICATION.md and its JSON evidence. Original/new/clean-export scene
fingerprints match. Two-robot unloaded movement, gripper toggle, zero-error
checkpoint save/load and actual GUI keyboard control passed. First initialization
can spend about5-6minutes cooking physics/rendering resources; this is documented
in README, not hidden by distributing old caches.

Original source and user slots remain under
`~/Documents/PhyRC_6.0.1/isaac-upgrade-docker`. Do not overwrite or remove them.
Local migration logs are `/tmp/phyrc2027-*.log`; full diagnostics/screenshots are
under this repository's ignored `output/` directory. Clean export used
`/tmp/phyrc2027-clean-Xgk02A`, which is not a runtime dependency.

Known scope limits: same existing host/driver/Docker infrastructure, not a fresh
OS installation; no loaded-grasp retention, high-load dressing or cross-GPU
trajectory certificate. Preserve these distinctions in future reports. Existing
legacy whitespace/comments were retained to preserve source byte identity.

## Future changes

Use a feature branch, edit maintained source/configuration, prepare with GUI
closed, run smoke and GUI checks, and commit only the intended source/docs.
Keep generated assets, cached downloads and private user states out of Git.
Changing geometry/physics requires a new slot namespace and appropriate
regression tests. Confirm custom asset redistribution rights before making the
repository public.
# CURRENT HANDOFF: 2026-09-11, GUI closed at user's request

## Read this before any earlier "fixed" or "passed" statements

The assistant previously described the issue as "resolved" too broadly.
The accurate conclusion has THREE separate scopes:

1. A specific SurfaceContactGuard defect was reproduced and fixed: the old loop
   used the intersection count BEFORE its final repair to decide full rollback.
   The corrected loop checks AFTER the last repair. Both graph and host-driven
   paths retain safe rollback when intersections genuinely remain.
2. A recorded native-FEM sequence reproduced persistent freezing in the original
   head / 80% speed / legacy-16 configuration. It did not reproduce in rounded
   head / 90% speed / corrected-24. However, rounded head / 90% / legacy-16 ALSO
   passed. Thus the full-scene improvement cannot be attributed solely to the
   guard fix. The independent exact-input GPU replay establishes the guard bug,
   not universal immunity to future freezes.
3. AFTER that checkpoint, shirt height and hand collision geometry were changed.
   The latest geometry has passed the measurements below, but the actual
   two-arm threading / over-head pulling / lowering / release sequence has NOT
   been demonstrated or verified with this latest geometry.

Do NOT tell the user that the latest version is proven unable to freeze.
Do NOT present an idle scene, an unloaded arm demo, or zero detailed sweeps while
the cloth is far from the person as evidence that the dressing regression passed.

## Repository and preserved checkpoint

- Work in ~/PhyRC_2027, NOT the old Documents project (the terminal CWD may still
  be ~/Documents/PhyRC_6.0.1/isaac-upgrade-docker).
- Last explicitly committed/pushed checkpoint: 6c73e5c, branch
  feat/policy-learning-env, origin
  git@github.com:0x4A656F6E2053656F79756C/PhyRC_2027.git.
- That checkpoint includes the contact fix, rounded head, solver 64, 90% command
  rates, tighter compliance, and the enlarged-height shirt with wrist spheres.
- Subsequent height/randomization/hand-hull changes remain separate working
  changes. This handoff/GUI-shutdown turn did NOT commit or push anything.
- Preserve the unrelated docs/PhyRC_proposals.pdf and all user slots/backups.
  Do not restore an archived main file wholesale over the current changes.

## Current production/runtime state

- SurfaceContactGuard: default 24 repairs plus a final check; genuine unresolved
  crossings still cause safe rollback. Native FEM solver iterations: 64.
- Original robot command rates multiplied by 0.9:
  lift 1.26, arm 0.99, wrist 4.5, base linear 0.504, angular 2.34,
  linear acceleration 1.08, angular acceleration 3.6.
- Compliance thresholds: global .315/.45, local .495/.72.
- Rounded visual and collision head retained; visual arm lengths unchanged.
- Shirt overall raw-Y height reduced by 10/12 below a protected collar band.
  All collar-loop and adjacent-ring coordinates stay fixed during this edit.
  Width/depth and surface-area mass normalization are retained; identical FEM
  response after changing rest shape is NOT claimed.
- Default hand mode is fitted: full posed hand plus forearm cut seam, closed
  convex hull, <=1 mm radial vertex expansion, 2 mm seam overlap, native hull
  limit 256. Left/right hulls have 76/78 vertices and 148/152 triangles.
  Native shapes, guard triangles, and collider visualization use these hulls.
  Finger gaps are closed; this is not independent articulated finger collision.
  Explicit legacy comparison: STRETCH4_HUMAN_HAND_COLLIDER=sphere.
- Historical startup randomization helpers restored from 91107e2 without
  restoring its unrelated policy/sensor code: human and chair together in a
  10 cm disk / yaw +/-30 degrees; shirt chooses one of four unchanged tables.
  STRETCH4_RANDOMIZE=0 or ./run.sh gui --no-randomization disables both.
  HUMAN_SPAWN_SEED and STRETCH4_GARMENT_SPAWN_SEED reproduce placement.
  This is constructor/startup placement, not a claim that every P reset resamples.
- New normal slot directory: output/states_neckfixed_shortheight_handfit_mesh4.
  Saves include a geometry revision and human/chair transforms; old or
  mismatching slots are rejected before applying them. Do not bypass this
  rejection to force an old failure F5 into the new rest shape/colliders.
- src and .runtime source copies were updated in the implementation turn.
  BOTH generated shirt assets were rebuilt successfully in the GUI-launch turn
  using ./run.sh cpu /scripts/prepare_assets.py. It is no longer merely a JSON edit.
- No driver/Docker reinstall, GPU reset, or robot-geometry edit was performed.

Relevant working files: scripts/resize_shirt.py, scripts/make_wearable_shirt.py,
scripts/prepare_assets.py, config/geometry.json, config/source-snapshot.sha256,
run.sh, src/DexGarmentLab/Env_Config/Randomization.py,
src/DexGarmentLab/Env_Config/Human/RandomSpawn.py,
src/DexGarmentLab/Env_Config/Garment/RandomSpawn.py,
src/DexGarmentLab/Env_Config/Human/HandSphereColliders.py,
src/DexGarmentLab/Env_StandAlone/Teleop_TShirt_Stretch4_Env.py,
README.md and docs/GEOMETRY_PLACEMENT_20260911.md.

## Completed latest-geometry checks, and their limits

Audit root A = ~/PhyRC_diagnostics/head_freeze_u2hIuWWo.
Current launch root D = A/geometry_gui_20260911_131503.

- D/asset_placement_checks.json: both generated shirts passed. Measured height
  ratios: full 0.8333333177148262, cropped 0.8333333258887214.
  BOTH collar area ratios = 1.0, centred-collar Hausdorff distance = 0.0.
  Topology vertex counts retained: full 5134, cropped 4039 before refinement.
- CPU placement checks passed fixed placement, seeded placement reproducibility,
  and configured human radius/yaw limits. These are NOT full randomized
  dressing/contact trials.
- A/hand_alignment_baseline_20260911.json and
  A/hand_alignment_fitted_20260911.json compare the captured real posed visual
  mesh with actual guard geometry. Old wrist spheres left 98.0794% / 97.3008%
  of visual hand vertices outside, with max protrusion 91.9213 / 84.9095 mm.
  Body reconstruction error was 1.21039e-7 m including the 3 mm body skin.
  The new hulls cover 100% of both visual hand sets without changing the arms.
- docs/verification-results/hand-alignment-20260911.json contains that measurement.
- D/monitor_v2/runtime_config.json confirms the live GUI's solver=64,
  graph guard budget=24, enabled convexHull hands and 100% hand coverage.
- The latest GUI was launched with randomization OFF for comparison. Its shirt
  remained on the original third table; neither gripper held it at shutdown.
- Last inspected v2 sample: 4312 actual pre- and post-physics callbacks,
  17.9667 simulated seconds, 359 finite position/velocity/joint samples,
  cloth motion 0.000389159 m per 12-step sample, max speed 0.118095 m/s.
  Detailed sweeps=0, rollback=0, cloth/body AABBs disjoint, no attachments.
  These establish actual simulation/measurement progress, NOT head-contact safety.

## Diagnostic mistake and correction

- D/gui_probe.py (v1) counted detailed guard sweeps but labeled them physics
  steps. It also initialized finite=True before measuring any tensors.
  The shirt was outside the body AABB, so the detailed guard correctly skipped;
  the monitor incorrectly displayed 0 "physics steps" and no measured motion.
- D/basic_demo_report.json is INVALID as stability/freeze-recovery evidence.
  See D/V1_MEASUREMENT_LIMITATION.md. The shirt/placement and live hand geometry
  checks are independent and were not invalidated by that monitor mistake.
- The user explicitly approved the diagnostic correction.
- D/monitor_v2/gui_probe.py now counts actual pre/post callbacks independently,
  samples live cloth position/velocity and robot joints every 12 physics steps,
  records detailed sweeps/rollback streaks separately, and measures native
  attachment anchor residuals when a grasp exists. Idle cloth is not
  automatically classified as a failed guard or a solved regression.
- Logging files: monitor_v2/latest.json, observations.jsonl, commands.jsonl,
  events.jsonl. The diagnostic wrapper adds measurement overhead but does not
  replace the production solver/control algorithms.
- GUI controls: Mark / save state; Visual / collision; Replay recorded pull.
  External marker request: touch D/monitor_v2/capture.request.

## Recorded motion: available, but not yet replayed on the latest geometry

- Historical protocol: A/goal_v3/control_protocol_64_80pct.json.
  Source: A/live_failure_20260911_013102/commands.jsonl.
- It begins with BOTH grippers already holding cloth in an intermediate pose.
  It does not contain the original pickup and arm-threading setup.
- There are 2200 input frames; releases occur at frame 693 (rig 0) and 1713
  (rig 1). The v2 replay additionally waits 240 control frames after the inputs.
- The v2 button requires two current-geometry native grasps and backs up the
  starting state. It replays the recorded movement/grip intents through normal
  drive_robot and make_gripper_toggle, without injecting cloth/base/joint poses.
  Any physical keyboard input cancels replay.
- Checking two grasps does NOT establish historical pose equivalence. Stage the
  actual arm/head-adjacent pose with the NEW shirt before using it. A run from
  an arbitrary two-hand table grasp is not the historical failure scenario.
- Replay was NOT started in this turn: both grippers were empty. No current-
  geometry recorded_pull_report.json passing result has been obtained.
- Next useful action: launch the current GUI, prepare a compatible new-geometry
  two-hand/threaded state with the user, save it, then test the pull/over-head/
  lower/release sequence and a sufficiently long no-input wait. Record robot
  anchor residuals and cloth motion as well as guard flags. Report only the
  tested state/sequence and distinguish old/new starting geometry.

## GUI shutdown and exact continuation state

- User explicitly requested that the current GUI be closed.
- Saved successfully before shutdown:
  D/monitor_v2/marker_1789101126635080851/slot_F5.npz.
  Associated measurements.json includes the current state and recent history.
  Nothing was held; this is NOT the historical frozen pose.
- D/monitor_v2/gui_shutdown_state_backup.tar preserves its slot library plus
  that final marker. D/monitor_v2/handoff_before_close.md preserves this
  handoff before the latest update.
- Container phyrc-current-geometry-v2 was stopped, not removed. Earlier
  phyrc-current-geometry and phyrc-audit-final were also already stopped.
- Launcher: D/monitor_v2/launch_gui.sh. Because the stopped named container
  remains, rerunning its docker run line with the same name will conflict.
  Use docker start -ai phyrc-current-geometry-v2 for the existing container,
  or deliberately choose a fresh container name.
- Its startup loads the private states/slot_F5.npz saved BEFORE the v2 monitor
  restart. To resume the exact shutdown marker instead, preserve existing
  states and copy the marker slot to monitor_v2/states/slot_F5.npz before start.
  Both are current-geometry slots; do not substitute an old enlarged-shirt F5.
- A/active_current_geometry_gui.json records the STOPPED status. Older
  active_final_gui.json refers to a stopped historical session, not a live GUI.
- All recordings/large backups remain local and are not installation assets.

## Earlier evidence worth retaining

- docs/CONTACT_GUARD_FIX_20260911.md documents the actual guard repair.
- Positive old-configuration native reproduction:
  A/goal_v3/traced_replay_v5_20260911_025635/report.json.
- Rounded-head / corrected-24 / 90% sequence:
  A/goal_v3/traced_replay_v6_20260911_031300/report.json.
- Rounded-head / legacy-16 / 90% matched control:
  A/goal_v3/traced_replay_v7_20260911_032839/report.json.
- Exact failed-input GPU reports: A/guard_gpu_v3_baseline/report.json and
  A/guard_gpu_v3_candidate{16,24,32}_fresh/report.json.
  The two solver-64 captures were already clear AFTER repair 16; the solver-32
  capture required repair 17. The stale final check and repair budget are
  distinct issues.
- Hardware investigation: A/goal_v3/hardware_20260911/REPORT.md found no evidence
  of a new persistent GPU compute fault in its bounded checks. It was not an
  exhaustive hardware health guarantee. A later old-container NVML access issue
  could not explain the earlier freeze; do not conflate those timestamps.
- A/goal_v3/raw_pre_failure_seeds contains UNUSED experimental seeds with
  pre-final-velocity-cap data. DO_NOT_USE.md explains the issue. They were never
  used for the successful evidence; do not revive or silently fix them.

---

# 2026-09-11: follow-up geometry and placement changes

The freeze-fix checkpoint below is committed and pushed as 6c73e5c on
feat/policy-learning-env. Follow-up changes are separate from that checkpoint.

- Shirt height is now generated at 10/12 of the enlarged height. The complete
  collar boundary and its adjacent ring keep their coordinates; only the body
  below them is compressed. Surface-area mass normalization remains active.
- Restore the historical startup human/chair randomization (10 cm disk, yaw
  +/-30 degrees) and independent uniform selection of one of four shirt tables.
  STRETCH4_RANDOMIZE=0 or ./run.sh gui --no-randomization restores fixed placement.
  HUMAN_SPAWN_SEED and STRETCH4_GARMENT_SPAWN_SEED reproduce placement.
- Captured real GUI geometry confirmed that 98.08% of left-hand and 97.30% of
  right-hand visible vertices were outside the old wrist spheres; the maximum
  protrusions were 91.92 mm and 84.91 mm. Body reconstruction agreed within
  0.000122 mm, so this was wrist-only coverage, not an arm-length mismatch.
- Default fitted hand convex hulls cover complete posed visual hands and their
  cut forearm seams. Visual arm/head geometry is unchanged. Native collision,
  contact guard and collider visualization use the hand hull geometry; sphere
  mode remains available explicitly. Hulls close finger gaps, not detailed
  independent finger contact. Fewer hand triangles do not disable guard logic.
- New slot directory is states_neckfixed_shortheight_handfit_mesh4; saved geometry
  revision and human/chair placement must match before loading. Old files remain.
- Re-prepare assets before launching the changed GUI. The old live diagnostic GUI
  does not hot-reload these changes. Runtime follow-up verification, if performed,
  is separate from the freeze checkpoint's completed tests. See
  docs/GEOMETRY_PLACEMENT_20260911.md and any associated diagnostic reports.
- The guard fix, rounded head, solver 64, robot rates 90%, and tighter compliance
  are retained. No driver/Docker installation or robot geometry change is part
  of this follow-up. No earlier policy/sensor work was restored incidentally.

## Historical: geometry/randomization changes BEFORE checkpoint

This checkpoint preserves the verified contact-freeze fix before the next
shirt-height, placement-randomization, and hand-collider changes.

- SurfaceContactGuard now checks the geometry AFTER its final permitted repair;
  default budget is 24 repairs plus a final check. Unresolved crossings still
  trigger safe rollback. Native FEM solver iterations are independently 64.
- Robot command rates are 90% of the original rates; tighter compliance limits
  remain enabled. Rounded visual and collision head geometry is restored.
- The recorded native-FEM sequence reproduced persistent freeze with the original
  head/80%/legacy guard. Rounded head/90%/corrected guard passed the same sequence;
  rounded head/90%/legacy guard also passed. Do not attribute the complete scene
  improvement solely to the guard change. Exact failed-input GPU replay separately
  demonstrates the guard defect and correction. See docs/CONTACT_GUARD_FIX_20260911.md.
- The final diagnostic GUI uses container phyrc-audit-final. The prior problematic
  F5 pose was reloaded successfully at 2026-09-11 05:41:07 KST (load epoch 2).
  This checkpoint was saved after both grippers opened. F5 restores poses, not
  historical solver settings or complete internal PhysX contact history.
- Local recordings/backups are under ~/PhyRC_diagnostics/head_freeze_u2hIuWWo/;
  they are not required installation assets and are not included in Git.
- Shirt height is still the enlarged value at this checkpoint. The requested
  10/12 height reduction with unchanged collar geometry, placement randomization,
  and visual-hand collider alignment are the NEXT changes, not verified here.
