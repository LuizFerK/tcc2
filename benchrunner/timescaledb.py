from benchrunner.config import CONFIG, get_scale_params
from benchrunner import metrics

CONFIG_PATH = (
    'iot-benchmark/timescaledb/target/iot-benchmark-timescaledb'
    '/iot-benchmark-timescaledb/conf/config.properties'
)
CWD = (
    'iot-benchmark/timescaledb/target/iot-benchmark-timescaledb'
    '/iot-benchmark-timescaledb'
)

# TimescaleDB does not support GROUP_BY_DESC (slot 12) or SET_OPERATION (slot 13).
TEST_CONFIGS = {
    # Baseline sequential ingestion — establishes raw insert throughput for a PostgreSQL-backed
    # time-series store under ordered data; benchmarks the full WAL + MVCC write path.
    'write':        {'OPERATION_PROPORTION': '1:0:0:0:0:0:0:0:0:0:0:0:0', 'IS_DELETE_DATA': 'true',  'IS_OUT_OF_ORDER': 'false'},
    # 20 % out-of-order writes — simulates late-arriving sensor data; stresses PostgreSQL's
    # page-level locking and hypertable chunk routing under non-monotonic timestamps.
    'out-of-order': {'OPERATION_PROPORTION': '1:0:0:0:0:0:0:0:0:0:0:0:0', 'IS_DELETE_DATA': 'true',  'IS_OUT_OF_ORDER': 'true',  'OUT_OF_ORDER_RATIO': '0.2', 'OUT_OF_ORDER_MODE': '1'},
    # Single-point writes (BATCH_SIZE=1) — one JDBC statement per data point; exposes the cost
    # of WAL flush and row-level overhead when devices stream individual readings.
    'batch-small':  {'OPERATION_PROPORTION': '1:0:0:0:0:0:0:0:0:0:0:0:0', 'IS_DELETE_DATA': 'true',  'IS_OUT_OF_ORDER': 'false', 'BATCH_SIZE_PER_WRITE': '1'},
    # Large batch writes (BATCH_SIZE=1000) — tests COPY-style bulk insert efficiency;
    # shows how well JDBC batch execution amortises WAL and index update overhead.
    'batch-large':  {'OPERATION_PROPORTION': '1:0:0:0:0:0:0:0:0:0:0:0:0', 'IS_DELETE_DATA': 'true',  'IS_OUT_OF_ORDER': 'false', 'BATCH_SIZE_PER_WRITE': '1000'},
    # All 10 supported read query types equally weighted — comprehensive read baseline.
    'read':         {'OPERATION_PROPORTION': '0:1:1:1:1:1:1:1:1:1:1:0:0', 'IS_DELETE_DATA': 'false', 'IS_OUT_OF_ORDER': 'false'},
    # LATEST_POINT only — "current sensor value" query; tests whether TimescaleDB's
    # last() aggregate or a reverse index scan is faster than a naïve MAX(time) lookup.
    'latest-point': {'OPERATION_PROPORTION': '0:0:0:0:0:0:0:0:1:0:0:0:0', 'IS_DELETE_DATA': 'false', 'IS_OUT_OF_ORDER': 'false'},
    # GROUP_BY (time-bucketed aggregation) only — exercises TimescaleDB's time_bucket()
    # function and chunk-level aggregation push-down for dashboard downsampling workloads.
    'downsample':   {'OPERATION_PROPORTION': '0:0:0:0:0:0:0:1:0:0:0:0:0', 'IS_DELETE_DATA': 'false', 'IS_OUT_OF_ORDER': 'false'},
    # TIME_RANGE only — sequential scan over a time window; tests chunk pruning efficiency
    # and columnar compression (if enabled) for historical data export.
    'range-query':  {'OPERATION_PROPORTION': '0:0:1:0:0:0:0:0:0:0:0:0:0', 'IS_DELETE_DATA': 'false', 'IS_OUT_OF_ORDER': 'false'},
    # VALUE_RANGE + AGG_VALUE + AGG_RANGE_VALUE — threshold alerting queries; tests how well
    # PostgreSQL's B-tree / BRIN indexes push predicates into hypertable chunk scans.
    'value-filter': {'OPERATION_PROPORTION': '0:0:0:1:0:1:1:0:0:0:0:0:0', 'IS_DELETE_DATA': 'false', 'IS_OUT_OF_ORDER': 'false'},
}


def update_config(test_type):
    props = {
        'DB_SWITCH':           'TimescaleDB',
        'HOST':                CONFIG['timescale_host'],
        'PORT':                CONFIG['timescale_port'],
        'USERNAME':            CONFIG['timescale_user'],
        'PASSWORD':            CONFIG['timescale_pass'],
        'DB_NAME':             CONFIG['timescale_db'],
        'BENCHMARK_WORK_MODE': 'testWithDefaultPath',
        'CSV_OUTPUT':          'true',
        **get_scale_params(),
        **TEST_CONFIGS[test_type],
    }
    return metrics.update_properties_file(CONFIG_PATH, props)


def run(test_type):
    print(f'\n[*] Running IoT-Benchmark for TimescaleDB ({test_type})...')
    if update_config(test_type):
        metrics.run_and_capture('timescaledb', test_type, 'bash benchmark.sh', cwd=CWD)
