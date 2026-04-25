import os
import re
from benchrunner.config import CONFIG, get_scale_params
from benchrunner import metrics

CONFIG_PATH = (
    'iot-benchmark/influxdb-2.0/target/iot-benchmark-influxdb-2.0'
    '/iot-benchmark-influxdb-2.0/conf/config.properties'
)
CWD = (
    'iot-benchmark/influxdb-2.0/target/iot-benchmark-influxdb-2.0'
    '/iot-benchmark-influxdb-2.0'
)

# InfluxDB 2.x does not support GROUP_BY_DESC (slot 12) or SET_OPERATION (slot 13).
TEST_CONFIGS = {
    # Baseline sequential ingestion — establishes raw insert throughput under ordered data.
    'write':        {'OPERATION_PROPORTION': '1:0:0:0:0:0:0:0:0:0:0:0:0', 'IS_DELETE_DATA': 'true',  'IS_OUT_OF_ORDER': 'false'},
    # 20 % out-of-order writes (Poisson distribution) — simulates late-arriving IoT sensor data;
    # reveals write-amplification from LSM compaction and timestamp re-ordering overhead.
    'out-of-order': {'OPERATION_PROPORTION': '1:0:0:0:0:0:0:0:0:0:0:0:0', 'IS_DELETE_DATA': 'true',  'IS_OUT_OF_ORDER': 'true',  'OUT_OF_ORDER_RATIO': '0.2', 'OUT_OF_ORDER_MODE': '1'},
    # Single-point writes (BATCH_SIZE=1) — isolates per-request overhead: one HTTP line-protocol
    # call per data point, exposing the cost of high-frequency individual sensor pushes.
    'batch-small':  {'OPERATION_PROPORTION': '1:0:0:0:0:0:0:0:0:0:0:0:0', 'IS_DELETE_DATA': 'true',  'IS_OUT_OF_ORDER': 'false', 'BATCH_SIZE_PER_WRITE': '1'},
    # Large batch writes (BATCH_SIZE=1000) — simulates historical bulk loading; tests how well
    # the HTTP line-protocol batching and the TSM write path amortise per-request overhead.
    'batch-large':  {'OPERATION_PROPORTION': '1:0:0:0:0:0:0:0:0:0:0:0:0', 'IS_DELETE_DATA': 'true',  'IS_OUT_OF_ORDER': 'false', 'BATCH_SIZE_PER_WRITE': '1000'},
    # All 10 supported read query types equally weighted — comprehensive read baseline.
    'read':         {'OPERATION_PROPORTION': '0:1:1:1:1:1:1:1:1:1:1:0:0', 'IS_DELETE_DATA': 'false', 'IS_OUT_OF_ORDER': 'false'},
    # LATEST_POINT only — the #1 real-time IoT query ("current sensor reading"); tests whether
    # InfluxDB maintains a last-value index or falls back to a full reverse range scan.
    'latest-point': {'OPERATION_PROPORTION': '0:0:0:0:0:0:0:0:1:0:0:0:0', 'IS_DELETE_DATA': 'false', 'IS_OUT_OF_ORDER': 'false'},
    # GROUP_BY (time-bucketed aggregation) only — core dashboard downsampling pattern;
    # tests InfluxDB's native GROUP BY time() aggregation push-down efficiency.
    'downsample':   {'OPERATION_PROPORTION': '0:0:0:0:0:0:0:1:0:0:0:0:0', 'IS_DELETE_DATA': 'false', 'IS_OUT_OF_ORDER': 'false'},
    # TIME_RANGE only — bulk data export for a time window; tests sequential scan throughput
    # and TSM file decompression speed when streaming historical data.
    'range-query':  {'OPERATION_PROPORTION': '0:0:1:0:0:0:0:0:0:0:0:0:0', 'IS_DELETE_DATA': 'false', 'IS_OUT_OF_ORDER': 'false'},
    # VALUE_RANGE + AGG_VALUE + AGG_RANGE_VALUE — threshold-based alerting queries
    # ("find readings above X"); tests predicate pushdown into the TSM storage layer.
    'value-filter': {'OPERATION_PROPORTION': '0:0:0:1:0:1:1:0:0:0:0:0:0', 'IS_DELETE_DATA': 'false', 'IS_OUT_OF_ORDER': 'false'},
}


def update_config(test_type):
    if not os.path.exists(CONFIG_PATH):
        print(f'[!] IoT-Benchmark config not found at {CONFIG_PATH}')
        print('    Run: nix run .#build')
        return False

    scale = get_scale_params()
    test_cfg = TEST_CONFIGS[test_type]
    props = {
        'DB_SWITCH':           'InfluxDB-2.x',
        'HOST':                CONFIG['influx_host'],
        'PORT':                CONFIG['influx_port'],
        'TOKEN':               CONFIG['influx_token'],
        'INFLUXDB_ORG':        CONFIG['influx_org'],
        'DB_NAME':             CONFIG['influx_bucket'],
        'BENCHMARK_WORK_MODE': 'testWithDefaultPath',
        'CSV_OUTPUT':          'true',
        **scale,
        **test_cfg,  # test-specific props override scale (e.g. BATCH_SIZE_PER_WRITE)
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


def run(test_type):
    print(f'\n[*] Running IoT-Benchmark for InfluxDB 2.x ({test_type})...')
    if update_config(test_type):
        metrics.run_and_capture('influxdb', test_type, 'bash benchmark.sh', cwd=CWD)


def write():
    run('write')


def read():
    run('read')
