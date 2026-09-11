# 다음 에이전트 인계 — 2026-09-12 00:23 KST

이 문서 상단이 현재 상태의 기준이다. 아래 과거 기록의 실행 중인 컨테이너,
미커밋 상태, 다음 작업 지시는 이 상단과 충돌하면 과거 정보로 취급한다.

## 1. 사용자의 최신 요청과 현재 상태

- 사용자의 최신 요청: "로봇 속도를 10% 올려줘" 프롬프트를 주었을 때 나온 결과(커밋 `4185bf2` 기반 형상 + 10% 속도 상향)로 옷의 형상(세로 길이, 소매 크기 등)을 원복 요청.
- **옷 형상 및 애셋 완전 원복 (`007e7cd` / `4185bf2` 기준)**:
  - `config/geometry.json`: 원복 (`SHIRT_HEIGHT_SCALE: 0.8333333333333334`, `SHIRT_CUFF_SCALE: 1.65`, `HEM_STRIPE_WIDTH: 0.05`).
  - `scripts/prepare_assets.py`: `extra = ['0.7']`로 원복 (`t_shirt_short.usd` 생성 기준).
  - `scripts/resize_shirt.py` 및 `scripts/make_wearable_shirt.py`: 원복.
  - `t_shirt_short.usd` 재생성 완료:
    - 버텍스 4,039개, 페이스 7,866개.
    - 백업 애셋 `output/t_shirt_short_prev_0.7.usd`와 100% 동일(최대 오차 0.0, 완전 일치) 확인.
    - 전체 세로 높이: $0.556001\,\text{m}$ ($0.556\,\text{m}$)
    - 전체 가로 폭: $0.678778\,\text{m}$ ($0.679\,\text{m}$)
    - 소매 커프 반경: 좌 $62.83\,\text{mm}$ (지름 $125.66\,\text{mm}$) / 우 $61.12\,\text{mm}$ (지름 $122.25\,\text{mm}$)
    - 칼라 반경: $42.88\,\text{mm}$ (지름 $85.75\,\text{mm}$)
    - 노란 줄무늬: 밑단 460개 면 ($Y \in [-0.2232, -0.1697]\,\text{m}$)
- **로봇 제어 속도 (+10% 상향 유지)**:
  - `Teleop_TShirt_Stretch4_Env.py`: 사용자가 "로봇 속도를 10% 올려줘"에서 요청했던 +10% 상향 설정 유지.
    - `LIFT_RATE = 1.54` (기존 1.40)
    - `ARM_RATE = 1.21` (기존 1.10)
    - `WRIST_RATE = 5.50` (기존 5.00)
    - `BASE_LINEAR_RATE = 0.616` (기존 0.56)
    - `BASE_ANGULAR_RATE = 2.86` (기존 2.60)
    - `BASE_LINEAR_ACCEL = 1.32` (기존 1.20)
    - `BASE_ANGULAR_ACCEL = 4.40` (기존 4.00)
- `Teleop_TShirt_Stretch4_Env.py`의 `STATE_DIR` (`/output/states_neckfixed_shortheight_handfit_mesh4`) 및 `_STATE_GEOMETRY_REVISION` (`20260911_neckfixed_shortheight_handfit_v1`) 원복 및 `.runtime/DexGarmentLab/` 동기화 완료.
- `scripts/check_gripper_friction.py` 및 `scripts/check_policy_contract.py` 회귀 테스트 통과.

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
- 브랜치: `feat/policy-learning-env`.
- origin: `git@github.com:0x4A656F6E2053656F79756C/PhyRC_2027.git`.
- 수정 파일: `src/DexGarmentLab/Env_StandAlone/Teleop_TShirt_Stretch4_Env.py`, `NEXT_AGENT_HANDOFF.md`.
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
