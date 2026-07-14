import os
import sys
import json
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path

# Load .env file into environment
env_path = Path('.env')
env = os.environ.copy()
if env_path.is_file():
    for line in env_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            env[key] = value
            os.environ[key] = value

# Ensure token present
API_TOKEN = env.get('FUNPAYHUB_API_TOKEN')
if not API_TOKEN:
    print('ERROR: FUNPAYHUB_API_TOKEN missing')
    sys.exit(1)

HUB_URL = 'http://127.0.0.1:5000'

print('Starting local hub...')
proc = subprocess.Popen(
    [sys.executable, 'funpayhub_main.py'],
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding='utf-8',
    errors='replace'
)

try:
    # wait for ready
    start = time.time()
    while time.time() - start < 30:
        try:
            req = urllib.request.Request(HUB_URL + '/health', headers={'X-API-Token': API_TOKEN})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.getcode() == 200:
                    print('Hub ready')
                    break
        except Exception:
            time.sleep(1)
    else:
        print('Hub not ready in time')
        raise

    print('Calling /api/lots/create_all dry_run=False...')
    url = HUB_URL + '/api/lots/create_all'
    data = json.dumps({'dry_run': False}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={
        'Content-Type': 'application/json',
        'X-API-Token': API_TOKEN
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode('utf-8'))
        print('API response:', json.dumps(body, ensure_ascii=False))

    time.sleep(1)
finally:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
