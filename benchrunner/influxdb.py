import os
import re
from benchrunner.config import CONFIG, get_scale_params
from benchrunner import metrics

# InfluxDB 2.x does not support GROUP_BY_DESC (pos 12) or SET_OPERATION (pos 13)
WRITE_PROPORTION = '1:0:0:0:0:0:0:0:0:0:0:0:0'
READ_PROPORTION  = '0:1:1:1:1:1:1:1:1:1:1:0:0'

CONFIG_PATH = (
    'iot-benchmark/influxdb-2.0/target/iot-benchmark-influxdb-2.0'
    '/iot-benchmark-influxdb-2.0/conf/config.properties'
)
CWD = (
    'iot-benchmark/influxdb-2.0/target/iot-benchmark-influxdb-2.0'
    '/iot-benchmark-influxdb-2.0'
)

def update_config(test_type):
    if not os.path.exists(CONFIG_PATH):
        print(f'[!] IoT-Benchmark config not found at {CONFIG_PATH}')
        print('    Run: nix run .#build')
        return False

    scale = get_scale_params()
    is_write = test_type == 'write'
    props = {
        'DB_SWITCH':            'InfluxDB-2.x',
        'HOST':                 CONFIG['influx_host'],
        'PORT':                 CONFIG['influx_port'],
        'TOKEN':                CONFIG['influx_token'],
        'INFLUXDB_ORG':         CONFIG['influx_org'],
        'DB_NAME':              CONFIG['influx_bucket'],
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
    print('\n[*] Running IoT-Benchmark for InfluxDB 2.x (write)...')
    if update_config('write'):
        metrics.run_and_capture('influxdb', 'write', 'bash benchmark.sh', cwd=CWD)

def read():
    print('\n[*] Running IoT-Benchmark for InfluxDB 2.x (read)...')
    if update_config('read'):
        metrics.run_and_capture('influxdb', 'read', 'bash benchmark.sh', cwd=CWD)
