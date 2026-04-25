import os
import re
from benchrunner.config import CONFIG, get_scale_params
from benchrunner import metrics

# TimescaleDB: GROUP_BY_DESC (pos 12) unsupported → set to 0; SET_OPERATION (pos 13) → 0
WRITE_PROPORTION = '1:0:0:0:0:0:0:0:0:0:0:0:0'
READ_PROPORTION  = '0:1:1:1:1:1:1:1:1:1:1:0:0'

CONFIG_PATH = (
    'iot-benchmark/timescaledb/target/iot-benchmark-timescaledb'
    '/iot-benchmark-timescaledb/conf/config.properties'
)
CWD = (
    'iot-benchmark/timescaledb/target/iot-benchmark-timescaledb'
    '/iot-benchmark-timescaledb'
)

def update_config(test_type):
    if not os.path.exists(CONFIG_PATH):
        print(f'[!] IoT-Benchmark config not found at {CONFIG_PATH}')
        print('    Run: nix run .#build')
        return False

    scale = get_scale_params()
    is_write = test_type == 'write'
    props = {
        'DB_SWITCH':            'TimescaleDB',
        'HOST':                 CONFIG['timescale_host'],
        'PORT':                 CONFIG['timescale_port'],
        'USERNAME':             CONFIG['timescale_user'],
        'PASSWORD':             CONFIG['timescale_pass'],
        'DB_NAME':              CONFIG['timescale_db'],
        'BENCHMARK_WORK_MODE':  'testWithDefaultPath',
        'OPERATION_PROPORTION': WRITE_PROPORTION if is_write else READ_PROPORTION,
        'IS_DELETE_DATA':       'true' if is_write else 'false',
        'CSV_OUTPUT':           'true',
        **scale,
    }

    with open(CONFIG_PATH, 'r') as f:
        content = f.read()
    for k, v in props.items():
        if re.search(f'^{k}=', content, re.M):
            content = re.sub(f'^{k}=.*$', f'{k}={v}', content, flags=re.M)
        else:
            content += f'\n{k}={v}'
    with open(CONFIG_PATH, 'w') as f:
        f.write(content)
    return True

def write():
    print('\n[*] Running IoT-Benchmark for TimescaleDB (write)...')
    if update_config('write'):
        metrics.run_and_capture('timescaledb', 'write', 'bash benchmark.sh', cwd=CWD)

def read():
    print('\n[*] Running IoT-Benchmark for TimescaleDB (read)...')
    if update_config('read'):
        metrics.run_and_capture('timescaledb', 'read', 'bash benchmark.sh', cwd=CWD)
