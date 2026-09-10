"""Read-only setup guidance; optional bounded GPU probe using an existing image.

Never installs packages, pulls images, changes drivers or restarts Docker.
PASS is scoped to each check, not a claim of full Isaac Sim compatibility.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = 'https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html'


def command(args, timeout=10):
    try:
        result = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=timeout, check=False)
        return result.returncode, (result.stdout + result.stderr).strip()
    except FileNotFoundError:
        return 127, 'Command not found'
    except subprocess.TimeoutExpired:
        return 124, f'Timed out after {timeout}s'
    except OSError as error:
        return 1, str(error)


def inspect_os(system, machine, release):
    if system != 'Linux':
        return 'FAIL', f'{system}: this launcher supports Linux, not native Windows/macOS'
    if machine.lower() not in ('x86_64', 'amd64'):
        return 'FAIL', f'{machine}: this project release targets x86_64'
    name = release.get('PRETTY_NAME', release.get('ID', 'unknown Linux'))
    if release.get('ID') == 'ubuntu' and release.get('VERSION_ID') in ('22.04', '24.04'):
        return 'PASS', f'{name}: supported OS range; no OS reinstall needed'
    return 'CHECK', f'{name}: outside the documented Ubuntu 22.04/24.04 range; do not auto-upgrade the OS'


def diagnose(gpu=False):
    rows = []

    def add(name, status, detail, next_step=''):
        rows.append(dict(check=name, status=status, detail=detail, next=next_step))

    try:
        release = platform.freedesktop_os_release() if platform.system() == 'Linux' else {}
    except (AttributeError, OSError):
        release = {}
    status, detail = inspect_os(platform.system(), platform.machine(), release)
    add('OS', status, detail, '' if status == 'PASS' else 'README.md#environment-route')

    for tool in ('git', 'curl', 'xauth', 'flock'):
        available = shutil.which(tool)
        add(tool, 'PASS' if available else 'MISSING', available or 'Not installed or not on PATH',
            '' if available else 'README.md#host-tools')

    if shutil.which('nvidia-smi'):
        rc, output = command(['nvidia-smi', '--query-gpu=name,driver_version,memory.total',
                              '--format=csv,noheader,nounits'])
        if rc:
            add('Host NVIDIA driver', 'FAIL', output[:240], 'README.md#driver')
        else:
            devices = []
            for values in csv.reader(output.splitlines()):
                if len(values) == 3:
                    try:
                        devices.append((values[0].strip(), values[1].strip(), float(values[2])))
                    except ValueError:
                        pass
            add('Host NVIDIA driver', 'PASS' if devices else 'CHECK',
                '; '.join(f'{name}, driver {driver}, {memory:.0f} MiB' for name, driver, memory in devices)
                or 'NVML responded, but GPU details could not be parsed', 'README.md#driver')
            # Name and memory are only a preliminary hardware screen, not the
            # official model/performance or Vulkan/PhysX compatibility checker.
            preliminary = len(devices) == 1 and 'RTX' in devices[0][0].upper() and devices[0][2] >= 15000
            add('RTX / VRAM precheck', 'PASS' if preliminary else 'CHECK',
                'RTX-class GPU and approximately 16GB+ VRAM reported; actual compatibility still needs smoke'
                if preliminary else 'Check GPU model, active adapter and VRAM against official requirements',
                'README.md#simulation-check')
    else:
        add('Host NVIDIA driver', 'MISSING', 'nvidia-smi is not on PATH; inspect the driver setup', 'README.md#driver')

    docker_ok = False
    image_ok = False
    image = os.environ.get('PHYRC_IMAGE', 'phyrc-2027:isaac-6.0.1')
    if not shutil.which('docker'):
        add('Docker', 'MISSING', 'Docker CLI not installed or not on PATH', 'README.md#docker')
    else:
        rc, output = command(['docker', 'info', '--format', '{{.ServerVersion}}'])
        docker_ok = rc == 0
        add('Docker', 'PASS' if docker_ok else 'FAIL',
            f'Server {output}; daemon reachable as current user' if docker_ok else output[:240],
            '' if docker_ok else 'README.md#docker')
        if docker_ok:
            rc, output = command(['docker', 'image', 'inspect', '--format', '{{.Id}}', image])
            image_ok = rc == 0
            add('Project image', 'PASS' if image_ok else 'MISSING',
                f'{image}: {output[:19]}' if image_ok else f'{image} not available locally; nothing downloaded',
                '' if image_ok else 'README.md#project-install')

    if not gpu:
        add('Container GPU', 'CHECK', 'Not run: use --gpu after license acceptance and image build',
            'README.md#container-gpu')
    elif os.environ.get('PHYRC_ACCEPT_EULA') != '1':
        add('Container GPU', 'CHECK', 'Not started: read NVIDIA terms and set PHYRC_ACCEPT_EULA=1 if you agree',
            'README.md#project-install')
    elif not docker_ok or not image_ok:
        add('Container GPU', 'CHECK', 'Not started: usable Docker and an existing project image are required',
            'README.md#project-install')
    else:
        name = 'phyrc-doctor-' + uuid.uuid4().hex[:12]
        try:
            rc, output = command(['docker', 'run', '--rm', '--pull=never', '--name', name,
                                  '--network=none', '--gpus', 'all',
                                  '-e', 'NVIDIA_DRIVER_CAPABILITIES=compute,utility',
                                  '--entrypoint', 'nvidia-smi', image,
                                  '--query-gpu=name,driver_version', '--format=csv,noheader'], timeout=20)
        finally:
            # A killed/timed-out Docker client can leave its container running.
            # Remove only this invocation's uniquely named diagnostic container.
            command(['docker', 'rm', '-f', name], timeout=5)
        add('Container GPU', 'PASS' if rc == 0 else 'FAIL',
            f'NVML access works: {output[:200]}; not a Vulkan/PhysX test' if rc == 0 else output[:240],
            'README.md#simulation-check' if rc == 0 else 'README.md#container-gpu')

    display = os.environ.get('DISPLAY', '')
    authority = Path(os.environ.get('XAUTHORITY') or str(Path.home() / '.Xauthority'))
    gui_ok = False
    if (display.startswith(':') or display.startswith('unix:')) and authority.is_file() and shutil.which('xauth'):
        rc, cookie = command(['xauth', '-f', str(authority), 'nlist', display])
        gui_ok = rc == 0 and bool(cookie.strip())
        # Never include the authentication cookie in logs or JSON output.
    add('Local GUI session', 'PASS' if gui_ok else 'CHECK',
        'Local DISPLAY and Xauthority cookie found; monitor/rendering not tested'
        if gui_ok else 'No usable local Xauthority session detected; headless smoke may still work',
        'README.md#gui-session')

    try:
        free = shutil.disk_usage(ROOT).free / (1024 ** 3)
        add('Project disk space', 'PASS' if free >= 100 else 'CHECK',
            f'{free:.1f} GiB free on project filesystem; Docker may use another disk',
            '' if free >= 100 else 'README.md#environment-route')
    except OSError as error:
        add('Project disk space', 'CHECK', str(error), 'README.md#environment-route')

    try:
        assets = json.loads((ROOT / 'config/assets.lock.json').read_text())['assets']
        missing = [asset['path'] for asset in assets if not (ROOT / asset['path']).is_file()]
        add('Input assets', 'MISSING' if missing else 'PASS',
            f'{len(missing)} missing; run prepare' if missing else 'All inputs present; prepare checks SHA256',
            'README.md#project-install' if missing else '')
    except (OSError, ValueError, KeyError, TypeError) as error:
        add('Input assets', 'FAIL', f'Cannot read asset manifest: {error}', 'README.md#project-install')
    ready = (ROOT / '.runtime/DexGarmentLab/Assets/Garment/Tops/Modelink/t_shirt_short.usd').is_file()
    add('Prepared runtime', 'PASS' if ready else 'MISSING',
        'Generated shirt exists; rerun prepare after source/config changes' if ready else 'Run prepare after build',
        '' if ready else 'README.md#project-install')
    return rows


def exit_status(rows):
    if any(row['status'] in ('FAIL', 'MISSING') for row in rows):
        return 1
    return 2 if any(row['status'] == 'CHECK' for row in rows) else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gpu', action='store_true', help='Probe NVML in a local image, without pulling or starting Isaac Sim')
    parser.add_argument('--json', action='store_true', help='Print machine-readable results without writing a report')
    args = parser.parse_args()
    rows = diagnose(args.gpu)
    code = exit_status(rows)
    if args.json:
        print(json.dumps({'checks': rows, 'exit_code': code, 'requirements': REQUIREMENTS,
                          'scope': 'prerequisites only; run smoke for actual simulation compatibility'}, indent=2))
    else:
        for row in rows:
            print(f"[{row['status']:7}] {row['check']}: {row['detail']}")
            if row['next']:
                print(f"          Next: {row['next']}")
        print('\nNo host configuration changed; no package/image downloads performed.')
        print('0=prechecks pass, 1=missing/problem, 2=additional checks needed.')
        print('Do not replace a working driver just to match the reference version.')
        print('Next: follow the indicated README sections, then run ./run.sh smoke.')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
