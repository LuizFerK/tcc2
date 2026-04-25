import os
import re
import subprocess

from benchrunner.config import CONFIG, get_scale_params

# Read-only proportion: all 11 read query types, skip GROUP_BY_DESC (pos 12) and SET_OPERATION (pos 13)
WRITE_PROPORTION = '1:0:0:0:0:0:0:0:0:0:0:0:0'
READ_PROPORTION  = '0:1:1:1:1:1:1:1:1:1:1:1:0'

CONFIG_PATH = (
    'iot-benchmark/iotdb-1.3/target/iot-benchmark-iotdb-1.3'
    '/iot-benchmark-iotdb-1.3/conf/config.properties'
)
CWD = (
    'iot-benchmark/iotdb-1.3/target/iot-benchmark-iotdb-1.3'
    '/iot-benchmark-iotdb-1.3'
)

def update_config(test_type):
    if not os.path.exists(CONFIG_PATH):
        print(f'[!] IoT-Benchmark config not found at {CONFIG_PATH}')
        print('    Run: nix run .#build')
        return False

    scale = get_scale_params()
    is_write = test_type == 'write'
    props = {
        'DB_SWITCH':            'IoTDB-130-SESSION_BY_TABLET',
        'HOST':                 '127.0.0.1',
        'PORT':                 '6667',
        'USERNAME':             'root',
        'PASSWORD':             'root',
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

from benchrunner import metrics

def run(test_type):
    print(f'\n[*] Running IoT-Benchmark for Apache IoTDB ({test_type})...')
    if not update_config(test_type):
        return
    metrics.run_and_capture('iotdb', test_type, 'bash benchmark.sh', cwd=CWD)
