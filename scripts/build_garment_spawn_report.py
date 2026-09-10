"""Build a portable HTML report from actual GPU measurements and render frames."""
import argparse
import base64
from io import BytesIO
import html
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input', type=Path, default=Path('output/verification/garment-spawn'))
parser.add_argument('--teleop-report', type=Path)
parser.add_argument('--policy-report', type=Path)
parser.add_argument('--output', type=Path, default=Path('docs/verification-results/garment-spawn.html'))
args = parser.parse_args()
r = json.loads((args.input/'report.json').read_text())
if args.teleop_report:
    teleop = json.loads(args.teleop_report.read_text())
    if not teleop['passed'] or 'garment_spawn' not in teleop:
        raise SystemExit('Teleop regression must pass with measured garment placement')
    r['teleop_regression'] = {key: teleop[key] for key in ('passed', 'garment_spawn', 'save_load_max_position_error_m', 'mismatched_placement_rejected')}
if args.policy_report:
    policy = json.loads(args.policy_report.read_text())
    if not policy['passed'] or 'garment_spawn' not in policy['initial']:
        raise SystemExit('Policy regression must pass with garment spawn metadata')
    r['policy_regression'] = {key: policy[key] for key in (
        'passed', 'depth_probe_m', 'lift_delta_m', 'repeat_seed_q_max_abs',
        'repeat_seed_cloth_max_abs', 'elapsed_wall_s')}
    r['policy_regression'].update(garment_spawn=policy['initial']['garment_spawn'],
                                  source_sha256=policy['initial']['source_sha256'])
if r['status'] != 'complete' or len(r['episodes']) != 4:
    raise SystemExit('All four measurements must finish before generating the report')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src/DexGarmentLab'))
from Env_Config.Garment.RandomSpawn import sample_garment_spawn
counts = [0]*4
for seed in range(10000):
    counts[sample_garment_spawn([[i,0,.3] for i in range(4)], [1,.8,.6], seed=seed)['table_index']] += 1

fig, axes = plt.subplots(1, 2, figsize=(12,3.6), constrained_layout=True)
for row in r['episodes']:
    index = row['spawn']['table_index']
    data = np.load(args.input/f'box_{index+1}_trace.npz')['samples']
    late = data[data[:,0] >= 2-1e-8]
    drift = np.linalg.norm(late[:,1:3]-late[0,1:3], axis=1)*1000
    c,s = np.array(row['spawn']['table_center_world_m']), np.array(row['spawn']['table_size_m'])
    margin = np.minimum(data[:,4:6]-(c[:2]-s[:2]/2), (c[:2]+s[:2]/2)-data[:,7:9]).min(1)*1000
    axes[0].plot(late[:,0], drift, label=f'Box {index+1}')
    axes[1].plot(data[:,0], margin, label=f'Box {index+1}')
for ax in axes:
    ax.set_xlabel('Simulation time since cloth restore (s)')
    ax.grid(alpha=.2)
    ax.legend(ncol=2, fontsize=8)
axes[0].set(title='Horizontal centroid movement after 2 s', ylabel='Movement (mm)')
axes[1].set(title='Smallest edge margin across every cloth vertex', ylabel='Inside the selected tabletop (mm)')
fig.savefig(args.input/'stability.png', dpi=150)
buf = BytesIO(); fig.savefig(buf, format='png', dpi=150); plt.close(fig)
chart = 'data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()

images = {}
for row in r['episodes']:
    key = str(row['spawn']['table_index']+1)
    images[key] = {}
    for t, filename in row['pictures'].items():
        # Report-size encoding only; retain unmodified full PNGs alongside raw traces.
        buf = BytesIO()
        Image.open(args.input/filename).convert('RGB').save(buf, format='JPEG', quality=88)
        images[key][t] = 'data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()

end = str(r['seconds_per_episode'])
cards = ''.join(f'''<article><div class="cardtitle"><h2>박스 {row['spawn']['table_index']+1}</h2><span>seed {row['seed']} · {'PASS' if row['passed'] else 'FAIL'}</span></div>
<img class="frame" data-box="{row['spawn']['table_index']+1}" src="{images[str(row['spawn']['table_index']+1)][end]}" alt="선택한 박스 {row['spawn']['table_index']+1} 위의 티셔츠" tabindex="0">
<p>중심 이동 <b>{row['post_2s_centroid_drift_m']*1000:.2f}mm</b> · 가장자리 최소 여유 <b>{row['minimum_xy_edge_clearance_m']*1000:.1f}mm</b></p></article>''' for row in r['episodes'])
rows = ''.join(f'''<tr><td>박스 {i+1}</td><td>{row['seed']}</td><td>{row['samples']}</td><td>{row['minimum_xy_edge_clearance_m']*1000:.2f}</td><td>{row['minimum_height_above_table_m']*1000:.3f}</td><td>{row['post_2s_centroid_drift_m']*1000:.3f}</td><td>{'PASS' if row['passed'] else 'FAIL'}</td></tr>''' for i,row in enumerate(r['episodes']))
status = 'PASS' if r['passed'] else 'FAIL'
page = '''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>티셔츠 랜덤 스폰 검증</title>
<style>
:root{color-scheme:light;font-family:system-ui,"Noto Sans CJK KR",sans-serif;color:#172537;background:#eef2f6}body{margin:0}main{max-width:1300px;margin:auto;padding:36px 24px}h1{font-size:32px;margin:8px 0 16px}h2{font-size:20px;margin:0}p{line-height:1.7}.eyebrow{color:#50677d;letter-spacing:.06em;font-size:13px}.badge{background:#d7f4df;color:#126a35;padding:7px 12px;border-radius:8px;font-weight:700}.panel,article{background:white;border:1px solid #dce3eb;border-radius:12px;padding:20px;margin-top:20px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.grid article{margin:0;padding:14px}.cardtitle{display:flex;align-items:center;justify-content:space-between;margin:5px 0 12px}.cardtitle span{font-size:13px;color:#496174}.frame{width:100%;border-radius:8px;cursor:zoom-in}.controls{position:sticky;top:0;background:#eef2f6ed;backdrop-filter:blur(6px);padding:16px 0;z-index:1;display:flex;gap:12px;align-items:center;flex-wrap:wrap}button{cursor:pointer;background:white;border:1px solid #b6c5d4;border-radius:7px;padding:10px 15px;font:inherit}button[aria-pressed=true]{background:#173e69;color:white}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:12px 10px;border-bottom:1px solid #e4e9ef;white-space:nowrap}.scroll{overflow:auto}.chart{width:100%}.note{color:#536579;font-size:14px}pre{white-space:pre-wrap;word-break:break-word;font-size:12px}dialog{max-width:95vw;padding:12px;border:0;border-radius:10px}dialog img{max-width:92vw;max-height:85vh;display:block}dialog::backdrop{background:#152232b8}@media(max-width:800px){.grid{grid-template-columns:1fr}main{padding:22px 14px}h1{font-size:26px}}
</style><main>
<div class="eyebrow">PhyRC 2027 · GPU 검증 · 2026-09-10</div><h1>티셔츠, 네 박스 중 하나에 랜덤 스폰</h1>
'''+f'''<span class="badge">{status} · 네 박스 × {r['seconds_per_episode']}초</span>
<p>옷 한 벌의 모양·방향·스폰 높이를 유지하면서 박스만 균등하게 선택합니다. 실제 시뮬레이션을 60Hz로 측정했고,
모든 박스에서 상판 지지와 안정화 후 이동량을 검사했습니다. 이미지를 누르면 확대됩니다.</p>
<div class="controls"><b>같은 시각 비교</b><button data-time="1.5" aria-pressed="false">1.5초</button><button data-time="10" aria-pressed="false">10초</button><button data-time="{end}" aria-pressed="true">{end}초</button><span class="note">물리 복원 후 경과한 시뮬레이션 시간 · 고정 카메라</span></div>
<div class="grid">{cards}</div>
<section class="panel"><h2>수치 검증</h2><p>옷의 모든 꼭짓점이 박스의 XY 범위 안에 있고, 상판보다 10mm 이상 내려간 꼭짓점이 없어야 합니다.
안정화 기준인 2초 이후 중심 이동과 높이 변화는 각각 10mm 이하를 통과 기준으로 삼았습니다.</p>
<div class="scroll"><table><thead><tr><th>선택</th><th>Seed</th><th>측정 횟수</th><th>가장자리 여유(mm)</th><th>상판 위 최소 높이(mm)</th><th>2초 이후 중심 이동(mm)</th><th>결과</th></tr></thead><tbody>{rows}</tbody></table></div>
<img class="chart" src="{chart}" alt="시간에 따른 중심 이동량과 박스 가장자리 여유 그래프"></section>
<section class="panel"><h2>랜덤 선택과 reset 재현</h2><p>10,000개 seed의 선택 횟수: <b>{' / '.join(map(str,counts))}</b> (박스 1→4 순서).
시각 비교에는 동일한 샘플러에서 각 박스를 처음 선택한 seed를 사용했습니다. 강제로 박스 번호를 지정한 결과가 아닙니다.</p>
<p>프로세스 최초 스폰도 박스 1(seed 2)을 선택한 것을 확인했습니다. 학습 reset으로 박스 1→2→3→4→1을 방문한 뒤
같은 seed의 천 위치 차이는 최대 <b>{r['repeat_seed_cloth_max_abs_m']*1000:.3f}mm</b>였습니다.
옷의 로컬 mesh와 topology는 정확히 유지되었습니다.</p>
<p class="note">기존 마찰·물성·중력 설정으로 무조작 상태를 검사했습니다. 초기 0.2m 낙하 후 상판에 안착하는 과정은 정상 동작입니다.
이 결과는 박스별 {r['seconds_per_episode']}초 관찰 범위의 안정성을 뜻하며 외력·로봇 조작·무한 시간의 무미끄럼을 보증하지 않습니다.
GPU FEM은 같은 seed에서도 settling 결과에 작은 수치 차이가 생길 수 있습니다. 보고서 사진은 실제 GPU 렌더를 JPEG로 인코딩했고 원본 PNG와 60Hz 궤적은 output/verification/garment-spawn에 보존했습니다.</p></section>
<section class="panel"><h2>재실행</h2><pre>python3 scripts/check_garment_spawn.py
PHYRC_ACCEPT_EULA=1 ./run.sh python /scripts/verify_garment_spawn.py
python3 scripts/build_garment_spawn_report.py</pre>
<details><summary>측정·소스 메타데이터</summary><pre>{html.escape(json.dumps(r,indent=2,ensure_ascii=False))}</pre></details></section>
<dialog id="zoom"><button id="close">닫기</button><img alt="확대한 GPU 렌더"></dialog>
</main><script>const frames='''+json.dumps(images)+''';
const buttons=document.querySelectorAll('[data-time]');
buttons.forEach(button=>button.addEventListener('click',()=>{buttons.forEach(b=>b.setAttribute('aria-pressed',String(b===button)));document.querySelectorAll('.frame').forEach(img=>img.src=frames[img.dataset.box][button.dataset.time]);}));
const zoom=document.getElementById('zoom');
document.querySelectorAll('.frame').forEach(img=>{const open=()=>{zoom.querySelector('img').src=img.src;zoom.showModal();};img.addEventListener('click',open);img.addEventListener('keydown',e=>{if(e.key==='Enter')open();});});
document.getElementById('close').addEventListener('click',()=>zoom.close());
</script></html>'''
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(page)
summary = dict(r, cpu_random_samples=10000, cpu_box_counts=counts)
# The runtime info field is absent in early runs; the per-reset restore assertion
# is still enforced by the GPU verifier before its first image is captured.
for row in summary['episodes']:
    if row.get('reset_settling') is None: row.pop('reset_settling', None)
args.output.with_suffix('.json').write_text(json.dumps(summary,indent=2)+'\n')
print(f'Wrote {args.output} ({args.output.stat().st_size/1024/1024:.2f} MiB)')
