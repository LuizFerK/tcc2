import os
import re

from benchrunner.config import get_scale_params

CONFIG_PATH = (
    'iot-benchmark/iotdb-1.3/target/iot-benchmark-iotdb-1.3'
    '/iot-benchmark-iotdb-1.3/conf/config.properties'
)
CWD = (
    'iot-benchmark/iotdb-1.3/target/iot-benchmark-iotdb-1.3'
    '/iot-benchmark-iotdb-1.3'
)

# IoTDB supports all 11 query types including GROUP_BY_DESC (slot 12).
# SET_OPERATION (slot 13) is unsupported by the SESSION_BY_TABLET client → always 0.
TEST_CONFIGS = {
    # Baseline sequential ingestion using the native Thrift SESSION_BY_TABLET protocol;
    # establishes the upper bound of raw insert throughput for a purpose-built TSDB.
    'write':        {'OPERATION_PROPORTION': '1:0:0:0:0:0:0:0:0:0:0:0:0', 'IS_DELETE_DATA': 'true',  'IS_OUT_OF_ORDER': 'false'},
    # 20 % out-of-order writes (Poisson) — tests how IoTDB's LSM-tree (TsFile) handles
    # late-arriving tablets; reveals compaction overhead vs. sequential ingestion.
    'out-of-order': {'OPERATION_PROPORTION': '1:0:0:0:0:0:0:0:0:0:0:0:0', 'IS_DELETE_DATA': 'true',  'IS_OUT_OF_ORDER': 'true',  'OUT_OF_ORDER_RATIO': '0.2', 'OUT_OF_ORDER_MODE': '1'},
    # Single-point writes (BATCH_SIZE=1) — tablet of size 1 per Thrift call; exposes
    # the minimum per-operation overhead of the binary RPC protocol.
    'batch-small':  {'OPERATION_PROPORTION': '1:0:0:0:0:0:0:0:0:0:0:0:0', 'IS_DELETE_DATA': 'true',  'IS_OUT_OF_ORDER': 'false', 'BATCH_SIZE_PER_WRITE': '1'},
    # Large batch writes (BATCH_SIZE=1000) — tests IoTDB's columnar TsFile vectorised
    # write path and how batching affects memory-to-disk flush throughput.
    'batch-large':  {'OPERATION_PROPORTION': '1:0:0:0:0:0:0:0:0:0:0:0:0', 'IS_DELETE_DATA': 'true',  'IS_OUT_OF_ORDER': 'false', 'BATCH_SIZE_PER_WRITE': '1000'},
    # All 11 supported read types (including GROUP_BY_DESC, unique to IoTDB) equally weighted.
    'read':         {'OPERATION_PROPORTION': '0:1:1:1:1:1:1:1:1:1:1:1:0', 'IS_DELETE_DATA': 'false', 'IS_OUT_OF_ORDER': 'false'},
    # LATEST_POINT only — tests IoTDB's dedicated last-value cache, which avoids a full
    # TsFile scan and returns the latest timestamp in O(1) for monitored time series.
    'latest-point': {'OPERATION_PROPORTION': '0:0:0:0:0:0:0:0:1:0:0:0:0', 'IS_DELETE_DATA': 'false', 'IS_OUT_OF_ORDER': 'false'},
    # GROUP_BY (time-bucketed aggregation) only — tests IoTDB's native pre-aggregated
    # statistics stored in TsFile chunk metadata for fast downsampling without full scans.
    'downsample':   {'OPERATION_PROPORTION': '0:0:0:0:0:0:0:1:0:0:0:0:0', 'IS_DELETE_DATA': 'false', 'IS_OUT_OF_ORDER': 'false'},
    # TIME_RANGE only — sequential scan of TsFile chunks for a time window; tests
    # columnar decompression throughput (SNAPPY/LZ4) for bulk historical data export.
    'range-query':  {'OPERATION_PROPORTION': '0:0:1:0:0:0:0:0:0:0:0:0:0', 'IS_DELETE_DATA': 'false', 'IS_OUT_OF_ORDER': 'false'},
    # VALUE_RANGE + AGG_VALUE + AGG_RANGE_VALUE — threshold alerting; tests IoTDB's
    # min/max statistics in chunk metadata for early-pruning of irrelevant chunks.
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
        'DB_SWITCH':           'IoTDB-130-SESSION_BY_TABLET',
        'HOST':                '127.0.0.1',
        'PORT':                '6667',
        'USERNAME':            'root',
        'PASSWORD':            'root',
        'BENCHMARK_WORK_MODE': 'testWithDefaultPath',
        'CSV_OUTPUT':          'true',
        **scale,
        **test_cfg,
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
