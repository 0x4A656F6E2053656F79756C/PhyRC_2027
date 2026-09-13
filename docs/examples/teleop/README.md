# 실제 teleop 데이터 예제

이 예제는 `20260913T153054_259148Z_0e4bae` 실행에서 수집한 자료입니다.
**1,142개 action 구간 / 고유 관측1,143개 / 20Hz / 시뮬레이션57.1초**.
원본 관측·action·카메라 자세 및 obs/next_obs 연속성 대조 검사를 통과했습니다.
평가 결과는 집기5/50점, 착의 점수0/45, success=false입니다. 성공 시연 예제가 아닙니다.

![5개 RGB 카메라](../../videos/sample_cameras_rgb.gif)

[5개 RGB MP4](../../videos/sample_all_cameras_rgb.mp4) · [Depth MP4](../../videos/sample_all_cameras_depth.mp4) ·
[Teleop viewport MP4](../../videos/sample_teleop_viewport.mp4)

GitHub에서 바로 볼 때는 위 GIF와 CSV를 사용하세요.
clone 후 이 폴더의 **[index.html](index.html)**을 브라우저로 열면 MP4와 숫자 예시를 한 화면에서 확인할 수 있습니다.
GitHub 파일 화면에서는 HTML이 앱으로 실행되지 않습니다.

## 파일

- [actions](demo_0_actions.csv): 1,142개 구간의 정규화18개 명령과 적용 시각.
- [obs](demo_0_obs.csv) / [next_obs](demo_0_next_obs.csv): 구간 직전/직후의 비영상 공개 관측 전체.
- [applied targets](demo_0_applied_targets.csv): 60Hz 제어3,426행. 감사용이며 정책 행동 라벨로 사용하지 않습니다.
- [evaluation](demo_0_evaluation.csv): 평가/시연 선별용이며 정책 입력이 아닙니다.
- [columns](columns.csv): 모든 CSV 열356개의 단위·인덱스·의미·첫 행 예시값.
- [video frame index](video_frame_index.csv): 미리보기와 원본 tick/시각 대응.
- [contract](contract.json), [HDF5 schema](hdf5_schema.json), [validation](validation.json).

모든 숫자 행을 보존했습니다. 영상은4개 관측당1개 및 마지막 관측을 포함한5fps/287프레임 미리보기입니다.
마지막 프레임 표시 때문에 MP4는57.4초이고 실제 시뮬레이션 구간은57.1초입니다.
실제 사람이 조작한 벽시계 시간은 약595.7초입니다. RGB/depth 미리보기 GIF는 그중16–28초 구간입니다.
상단 시각은 원본 관측의 simulation_time_s입니다.

원본 policy.hdf5 약3.16GB와 audit.hdf5 약182MB는 Git에 포함하지 않았습니다.
MP4/GIF와 CSV는 파일 구조를 이해하기 위한 예제이며 완전한 학습 데이터셋 배포가 아닙니다.
수집에는 `./run.sh gui --training-record 1`을 사용하세요.

각 키의 의미는 [데이터 가이드](../../competition/DATA.md), 허용 범위는 [참가 규칙](../../competition/RULES.md)을 따릅니다.
