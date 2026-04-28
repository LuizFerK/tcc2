# IoT Time-Series Database Benchmark

Undergraduate thesis (TCC) project comparing three time-series databases — **Apache IoTDB**, **InfluxDB**, and **TimescaleDB** — across nine workload scenarios representative of real IoT deployments.

---

## Overview

IoT systems produce continuous streams of sensor readings that must be ingested at high rates and queried efficiently for monitoring and analytics. Different databases take fundamentally different architectural approaches to this problem:

- **Apache IoTDB** is purpose-built for IoT time-series data, using a custom columnar file format (TsFile) and a native binary RPC protocol (Thrift SESSION_BY_TABLET).
- **InfluxDB 2.x** is a purpose-built time-series database using the TSM (Time-Structured Merge Tree) storage engine, exposed via an HTTP line-protocol API.
- **TimescaleDB** is a PostgreSQL extension that adds time-series capabilities (hypertables, time_bucket aggregation) on top of a full relational engine with WAL, MVCC, and B-tree indexes.

The benchmark uses [iot-benchmark](https://github.com/thulab/iot-benchmark) (Tsinghua University) as the workload generator, which simulates IoT sensor devices writing and querying time-series data.

---

## Architecture

```
benchmark.py              ← CLI entry point (--db, --test, --scale)
benchrunner/
  config.py               ← connection settings + scale parameters
  influxdb.py             ← InfluxDB 2.x driver (updates config, invokes benchmark)
  timescaledb.py          ← TimescaleDB driver
  iotdb.py                ← IoTDB driver (delegates to iot_benchmark.py)
  iot_benchmark.py        ← IoTDB config writer + subprocess runner
  metrics.py              ← Docker stats monitor + output parser + result table
iot-benchmark/            ← git submodule (thulab/iot-benchmark)
  influxdb-2.0/           ← Java benchmark client for InfluxDB
  timescaledb/            ← Java benchmark client for TimescaleDB
  iotdb-1.3/              ← Java benchmark client for IoTDB
docker-compose.yml        ← IoTDB + InfluxDB + TimescaleDB containers
flake.nix                 ← Nix dev shell + build + benchmark apps
scripts/
  init-timescaledb.sql    ← Forces MD5 auth for the legacy JDBC driver bundled in iot-benchmark
```

**How a benchmark run works:**

1. `benchmark.py` starts the Docker containers if not already running.
2. For each (database, test) pair, the Python driver writes the correct parameters to the Java benchmark client's `conf/config.properties`.
3. The Java client is invoked via `bash benchmark.sh`; a background thread polls `docker stats` every second to collect CPU and memory samples.
4. After the run, `metrics.py` parses the Result Matrix and Latency Matrix from the Java client's stdout, combines them with the Docker samples, and appends a row to the results table.

---

## Tech Stack

| Layer               | Technology                                                            |
|---------------------|-----------------------------------------------------------------------|
| Workload generator  | [iot-benchmark](https://github.com/thulab/iot-benchmark) (Java, Maven)|
| Orchestration       | Python 3                                                              |
| Database containers | Docker Compose                                                        |
| Dev environment     | Nix flake (`nix develop`, `nix run`)                                  |
| IoTDB               | apache/iotdb:1.3.0-standalone                                         |
| InfluxDB            | influxdb:2.7-alpine                                                   |
| TimescaleDB         | timescale/timescaledb:latest-pg15                                     |

---

## Prerequisites

- JDK 17
- Maven
- Docker and Docker Compose
- Python 3
- Docker daemon running

---

## Setup

```bash
# Clone with submodule
git clone --recurse-submodules <repo-url>
cd tcc2
```

### Nix

```bash
# Enter dev shell (provides java, mvn, docker, python)
nix develop

# Build the Java benchmark clients (one-time)
nix run .#build
```

### Non-Nix

```bash
# Build the Java benchmark clients (one-time)
cd iot-benchmark && mvn -pl influxdb-2.0,timescaledb,iotdb-1.3 package -DskipTests -q && cd ..
```

---

## Running

```bash
# Full suite, all databases, small scale (~5 min)
python3 benchmark.py

# Single database, single test
python3 benchmark.py --db influxdb --test write

# All tests, specific database, medium scale
python3 benchmark.py --db timescaledb --scale medium
```

### Options

| Flag      | Default | Values                                                 |
|-----------|---------|--------------------------------------------------------|
| `--db`    | `all`   | `all`, `influxdb`, `timescaledb`, `iotdb`              |
| `--scale` | `small` | `small` (~5 min), `medium` (~30 min), `large` (~2 h)   |

`--test` (default `all`): `all`, `write`, `out-of-order`, `batch-small`, `batch-large`, `read`, `latest-point`, `downsample`, `range-query`, `value-filter`

### Scale parameters

| Scale  | Clients | Devices | Sensors | Batch size | Loops |
|--------|---------|---------|---------|------------|-------|
| small  | 5       | 10      | 10      | 100        | 1000  |
| medium | 5       | 10      | 10      | 100        | 5000  |
| large  | 10      | 50      | 20      | 100        | 5000  |

---

## Test Types

When `--test all` is used, tests run in this order: write variants first (each clears and re-seeds the database), then read variants (which all operate on the data written by the baseline `write` test).

### Write tests

| Test           | What it measures                                                                                                                              |
|----------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| `write`        | Baseline sequential ingestion - ordered timestamps, default batch size                                                                        |
| `out-of-order` | 20% late-arriving data (Poisson distribution) - simulates network-delayed IoT sensors; reveals write-amplification from out-of-order handling |
| `batch-small`  | `BATCH_SIZE=1` - one write request per data point; isolates per-request protocol overhead (HTTP round-trip, WAL flush, Thrift call)           |
| `batch-large`  | `BATCH_SIZE=1000` - large batches; tests bulk-loading efficiency and where each database's batching ceiling lies                              |

### Read tests

| Test           | Queries active                                | What it measures                                                                           |
|----------------|-----------------------------------------------|--------------------------------------------------------------------------------------------|
| `read`         | All 10 supported types                        | Comprehensive read baseline - all analytics patterns equally weighted                      |
| `latest-point` | `LATEST_POINT`                                | Real-time monitoring - "current sensor value"; tests last-value index vs full reverse scan |
| `downsample`   | `GROUP_BY`                                    | Dashboard aggregation - time-bucketed averages; tests native downsampling push-down        |
| `range-query`  | `TIME_RANGE`                                  | Bulk data export - sequential scan over a time window; tests decompression throughput      |
| `value-filter` | `VALUE_RANGE`, `AGG_VALUE`, `AGG_RANGE_VALUE` | Threshold alerting - "readings above X"; tests predicate pushdown into the storage layer   |

---

## Results

**Column definitions**

| Column       | Meaning                                                                                                    |
|--------------|------------------------------------------------------------------------------------------------------------|
| Time (s)     | Wall-clock duration of the entire benchmark run                                                            |
| Throughput   | Points ingested or returned per second, as reported by iot-benchmark                                       |
| Avg Lat      | Mean per-operation latency across all client threads                                                       |
| P99 Lat      | 99th-percentile latency — 99% of operations completed faster than this value; the remaining 1% took longer |
| Avg/Peak CPU | Average and maximum CPU usage of the database container sampled every second via `docker stats`            |
| Avg/Peak Mem | Average and maximum RSS of the database container over the same interval                                   |

### Small scale

| DB          | Test         | Time (s) | Throughput        | Avg Lat   | P99 Lat    | Avg CPU | Peak CPU | Avg Mem    | Peak Mem   |
|-------------|--------------|----------|-------------------|-----------|------------|---------|----------|------------|------------|
| INFLUXDB    | BATCH-SMALL  | 19.35    | 5168.85 pts/s     | 9.12 ms   | 14.74 ms   | 2.5%    | 4.3%     | 118.9 MB   | 125.5 MB   |
| INFLUXDB    | BATCH-LARGE  | 45.58    | 2193904.61 pts/s  | 22.00 ms  | 205.07 ms  | 22.0%   | 32.7%    | 596.7 MB   | 926.0 MB   |
| INFLUXDB    | OUT-OF-ORDER | 36.66    | 272760.59 pts/s   | 17.72 ms  | 45.44 ms   | 5.9%    | 13.6%    | 318.8 MB   | 925.0 MB   |
| INFLUXDB    | WRITE        | 22.76    | 439381.68 pts/s   | 10.81 ms  | 39.77 ms   | 6.3%    | 18.2%    | 253.2 MB   | 320.7 MB   |
| INFLUXDB    | READ         | 28.98    | 3618.15 pts/s     | 28.22 ms  | 269.51 ms  | 41.7%   | 52.1%    | 305.3 MB   | 318.0 MB   |
| INFLUXDB    | LATEST-POINT | 12.12    | 412.43 pts/s      | 10.85 ms  | 19.67 ms   | 34.1%   | 51.3%    | 301.1 MB   | 313.8 MB   |
| INFLUXDB    | DOWNSAMPLE   | 8.10     | 8021.25 pts/s     | 6.85 ms   | 14.36 ms   | 25.6%   | 47.2%    | 292.6 MB   | 297.8 MB   |
| INFLUXDB    | RANGE-QUERY  | 7.75     | 31606.13 pts/s    | 6.50 ms   | 14.36 ms   | 23.9%   | 44.4%    | 291.6 MB   | 292.9 MB   |
| INFLUXDB    | VALUE-FILTER | 92.24    | 936.26 pts/s      | 89.85 ms  | 341.34 ms  | 46.4%   | 53.8%    | 316.7 MB   | 328.9 MB   |
| TIMESCALEDB | BATCH-SMALL  | 22.45    | 4454.53 pts/s     | 10.67 ms  | 15.96 ms   | 2.3%    | 3.4%     | 5443.3 MB  | 5446.7 MB  |
| TIMESCALEDB | BATCH-LARGE  | 622.87   | 160546.88 pts/s   | 302.36 ms | 1069.12 ms | 31.4%   | 39.5%    | 5474.6 MB  | 5496.8 MB  |
| TIMESCALEDB | OUT-OF-ORDER | 75.65    | 132189.13 pts/s   | 36.52 ms  | 250.11 ms  | 21.8%   | 32.5%    | 5478.6 MB  | 5494.8 MB  |
| TIMESCALEDB | WRITE        | 74.81    | 133677.05 pts/s   | 36.05 ms  | 246.52 ms  | 23.8%   | 33.9%    | 5516.7 MB  | 5534.7 MB  |
| TIMESCALEDB | READ         | 13.45    | 7945.08 pts/s     | 12.96 ms  | 275.42 ms  | 57.3%   | 83.6%    | 5545.3 MB  | 5560.3 MB  |
| TIMESCALEDB | LATEST-POINT | 1.61     | 3102.08 pts/s     | 0.50 ms   | 1.59 ms    | 7.4%    | 14.9%    | 5519.4 MB  | 5519.4 MB  |
| TIMESCALEDB | DOWNSAMPLE   | 1.83     | 35454.63 pts/s    | 0.72 ms   | 1.84 ms    | 6.9%    | 20.8%    | 5523.8 MB  | 5532.7 MB  |
| TIMESCALEDB | RANGE-QUERY  | 1.73     | 144191.68 pts/s   | 0.64 ms   | 1.66 ms    | 6.4%    | 19.2%    | 5523.5 MB  | 5531.6 MB  |
| TIMESCALEDB | VALUE-FILTER | 40.81    | 2157.80 pts/s     | 40.12 ms  | 251.06 ms  | 74.8%   | 90.3%    | 5552.9 MB  | 5561.3 MB  |
| IOTDB       | BATCH-SMALL  | 4.12     | 24268.33 pts/s    | 1.54 ms   | 1.19 ms    | 0.3%    | 0.7%     | 12469.4 MB | 12482.6 MB |
| IOTDB       | BATCH-LARGE  | 7.20     | 13897642.72 pts/s | 2.91 ms   | 9.99 ms    | 6.6%    | 36.9%    | 12513.3 MB | 12533.8 MB |
| IOTDB       | OUT-OF-ORDER | 5.22     | 1917405.53 pts/s  | 2.02 ms   | 2.73 ms    | 1.9%    | 10.3%    | 12544.0 MB | 12564.5 MB |
| IOTDB       | WRITE        | 4.69     | 2130911.33 pts/s  | 1.77 ms   | 1.99 ms    | 0.8%    | 3.8%     | 12573.3 MB | 12574.7 MB |
| IOTDB       | READ         | 3.47     | 29649.05 pts/s    | 2.26 ms   | 20.46 ms   | 15.2%   | 28.2%    | 12554.2 MB | 12574.7 MB |
| IOTDB       | LATEST-POINT | 1.91     | 2617.04 pts/s     | 0.78 ms   | 2.81 ms    | 5.1%    | 14.8%    | 12550.8 MB | 12554.2 MB |
| IOTDB       | DOWNSAMPLE   | 2.19     | 29697.05 pts/s    | 1.07 ms   | 3.01 ms    | 4.8%    | 13.8%    | 12554.2 MB | 12554.2 MB |
| IOTDB       | RANGE-QUERY  | 2.48     | 100916.37 pts/s   | 1.35 ms   | 3.81 ms    | 5.1%    | 14.3%    | 12554.2 MB | 12554.2 MB |
| IOTDB       | VALUE-FILTER | 5.03     | 17504.97 pts/s    | 3.79 ms   | 14.22 ms   | 17.4%   | 42.3%    | 12556.8 MB | 12564.5 MB |

### Medium scale

| DB          | Test         | Time (s) | Throughput        | Avg Lat   | P99 Lat    | Avg CPU | Peak CPU | Avg Mem    | Peak Mem   |
|-------------|--------------|----------|-------------------|-----------|------------|---------|----------|------------|------------|
| INFLUXDB    | BATCH-SMALL  | 106.88   | 4678.00 pts/s     | 10.56 ms  | 36.41 ms   | 4.5%    | 7.0%     | 192.4 MB   | 207.7 MB   |
| INFLUXDB    | BATCH-LARGE  | 240.45   | 2079443.35 pts/s  | 23.81 ms  | 238.84 ms  | 23.7%   | 36.8%    | 1812.1 MB  | 3152.9 MB  |
| INFLUXDB    | OUT-OF-ORDER | 200.75   | 249071.69 pts/s   | 19.88 ms  | 102.65 ms  | 7.6%    | 21.8%    | 693.3 MB   | 3145.7 MB  |
| INFLUXDB    | WRITE        | 137.49   | 363669.90 pts/s   | 13.59 ms  | 210.95 ms  | 8.8%    | 18.8%    | 502.9 MB   | 664.9 MB   |
| INFLUXDB    | READ         | 605.70   | 871.99 pts/s      | 121.21 ms | 1330.58 ms | 52.3%   | 57.5%    | 713.8 MB   | 790.5 MB   |
| INFLUXDB    | LATEST-POINT | 117.40   | 212.95 pts/s      | 23.18 ms  | 32.34 ms   | 49.8%   | 54.3%    | 270.4 MB   | 285.8 MB   |
| INFLUXDB    | DOWNSAMPLE   | 37.34    | 8702.82 pts/s     | 7.17 ms   | 11.80 ms   | 38.7%   | 45.2%    | 252.1 MB   | 255.4 MB   |
| INFLUXDB    | RANGE-QUERY  | 38.67    | 31679.75 pts/s    | 7.45 ms   | 15.17 ms   | 35.6%   | 44.0%    | 254.3 MB   | 256.6 MB   |
| INFLUXDB    | VALUE-FILTER | 2003.30  | 210.46 pts/s      | 396.15 ms | 1363.74 ms | 46.9%   | 50.2%    | 304.4 MB   | 335.2 MB   |
| TIMESCALEDB | BATCH-SMALL  | 110.59   | 4521.20 pts/s     | 10.91 ms  | 36.46 ms   | 4.1%    | 6.1%     | 5450.6 MB  | 5458.9 MB  |
| TIMESCALEDB | BATCH-LARGE  | 3104.23  | 161070.48 pts/s   | 308.38 ms | 1036.76 ms | 31.0%   | 40.0%    | 6042.1 MB  | 8177.7 MB  |
| TIMESCALEDB | OUT-OF-ORDER | 396.24   | 126186.45 pts/s   | 38.71 ms  | 263.93 ms  | 24.7%   | 36.4%    | 8160.1 MB  | 8178.7 MB  |
| TIMESCALEDB | WRITE        | 396.41   | 126131.18 pts/s   | 38.72 ms  | 252.60 ms  | 26.0%   | 34.6%    | 8185.3 MB  | 8201.2 MB  |
| TIMESCALEDB | READ         | 284.43   | 1891.76 pts/s     | 57.25 ms  | 1672.74 ms | 77.4%   | 87.9%    | 8227.4 MB  | 8233.0 MB  |
| TIMESCALEDB | LATEST-POINT | 3.79     | 6588.95 pts/s     | 0.53 ms   | 1.56 ms    | 13.7%   | 34.7%    | 8184.6 MB  | 8192.0 MB  |
| TIMESCALEDB | DOWNSAMPLE   | 4.54     | 71508.71 pts/s    | 0.67 ms   | 1.74 ms    | 13.9%   | 35.9%    | 8184.3 MB  | 8191.0 MB  |
| TIMESCALEDB | RANGE-QUERY  | 4.09     | 305461.28 pts/s   | 0.59 ms   | 1.61 ms    | 13.5%   | 34.8%    | 8184.3 MB  | 8191.0 MB  |
| TIMESCALEDB | VALUE-FILTER | 891.75   | 482.07 pts/s      | 175.07 ms | 1299.50 ms | 76.6%   | 88.3%    | 8228.8 MB  | 8236.0 MB  |
| IOTDB       | BATCH-SMALL  | 6.26     | 79923.31 pts/s    | 0.51 ms   | 1.29 ms    | 4.9%    | 21.9%    | 12520.6 MB | 12533.8 MB |
| IOTDB       | BATCH-LARGE  | 25.17    | 19868484.80 pts/s | 2.22 ms   | 10.28 ms   | 23.0%   | 48.5%    | 12573.5 MB | 12595.2 MB |
| IOTDB       | OUT-OF-ORDER | 8.30     | 6021299.84 pts/s  | 0.67 ms   | 1.82 ms    | 8.4%    | 37.4%    | 12625.9 MB | 12656.6 MB |
| IOTDB       | WRITE        | 7.84     | 6378193.32 pts/s  | 0.65 ms   | 2.01 ms    | 6.5%    | 30.1%    | 12680.5 MB | 12697.6 MB |
| IOTDB       | READ         | 34.21    | 15215.53 pts/s    | 6.62 ms   | 78.49 ms   | 34.9%   | 45.6%    | 12699.8 MB | 12707.8 MB |
| IOTDB       | LATEST-POINT | 4.98     | 5018.40 pts/s     | 0.75 ms   | 2.65 ms    | 13.6%   | 30.1%    | 12707.8 MB | 12707.8 MB |
| IOTDB       | DOWNSAMPLE   | 7.58     | 42888.90 pts/s    | 1.26 ms   | 4.06 ms    | 17.2%   | 35.0%    | 12707.8 MB | 12707.8 MB |
| IOTDB       | RANGE-QUERY  | 8.53     | 146541.98 pts/s   | 1.46 ms   | 4.40 ms    | 17.6%   | 32.9%    | 12707.8 MB | 12707.8 MB |
| IOTDB       | VALUE-FILTER | 98.46    | 4366.15 pts/s     | 19.17 ms  | 73.48 ms   | 38.5%   | 41.5%    | 12715.2 MB | 12718.1 MB |

### Large scale

| DB          | Test         | Time (s) | Throughput        | Avg Lat   | P99 Lat    | Avg CPU | Peak CPU | Avg Mem    | Peak Mem   |
|-------------|--------------|----------|-------------------|-----------|------------|---------|----------|------------|------------|
| INFLUXDB    | BATCH-SMALL  | 311.34   | 16059.65 pts/s    | 12.38 ms  | 40.09 ms   | 10.5%   | 16.3%    | 317.4 MB   | 393.6 MB   |
| INFLUXDB    | BATCH-LARGE  | 1335.88  | 3742857.63 pts/s  | 52.96 ms  | 374.60 ms  | 44.4%   | 74.1%    | 1607.4 MB  | 2573.3 MB  |
| INFLUXDB    | OUT-OF-ORDER | 657.13   | 760888.17 pts/s   | 26.08 ms  | 254.05 ms  | 25.5%   | 51.1%    | 1012.2 MB  | 1494.0 MB  |
| INFLUXDB    | WRITE        | 424.39   | 1178162.42 pts/s  | 16.85 ms  | 170.92 ms  | 31.0%   | 44.8%    | 1073.5 MB  | 1395.7 MB  |
| INFLUXDB    | READ         | 847.93   | 1253.83 pts/s     | 168.61 ms | 1808.87 ms | 85.3%   | 91.3%    | 1034.4 MB  | 1517.6 MB  |
| INFLUXDB    | LATEST-POINT | 174.01   | 287.34 pts/s      | 34.48 ms  | 50.98 ms   | 76.6%   | 86.2%    | 372.5 MB   | 389.5 MB   |
| INFLUXDB    | DOWNSAMPLE   | 50.96    | 12755.81 pts/s    | 9.91 ms   | 16.04 ms   | 69.8%   | 80.2%    | 356.1 MB   | 369.8 MB   |
| INFLUXDB    | RANGE-QUERY  | 47.75    | 51306.92 pts/s    | 9.26 ms   | 15.88 ms   | 67.2%   | 77.5%    | 353.8 MB   | 367.9 MB   |
| INFLUXDB    | VALUE-FILTER | 2705.08  | 314.59 pts/s      | 537.48 ms | 1859.91 ms | 83.7%   | 88.8%    | 518.3 MB   | 577.1 MB   |
| TIMESCALEDB | BATCH-SMALL  | 281.1    | 17787.12 pts/s    | 11.14 ms  | 40.78 ms   | 10.7%   | 14.1%    | 7061.2 MB  | 7065.6 MB  |
| TIMESCALEDB | BATCH-LARGE  | 3600.0   | 421972.11 pts/s   | 473.67 ms | 1639.20 ms | 53.7%   | 77.8%    | 9428.0 MB  | 10291.2 MB |
| TIMESCALEDB | OUT-OF-ORDER | 1811.92  | 275951.00 pts/s   | 71.10 ms  | 455.19 ms  | 36.5%   | 68.6%    | 9682.7 MB  | 12113.9 MB |
| TIMESCALEDB | WRITE        | 1393.68  | 358761.62 pts/s   | 54.36 ms  | 272.88 ms  | 47.4%   | 70.3%    | 9348.4 MB  | 9572.4 MB  |
| TIMESCALEDB | READ         | 999.82   | 1083.29 pts/s     | 194.14 ms | 4232.60 ms | 97.7%   | 99.7%    | 9623.5 MB  | 9660.4 MB  |
| TIMESCALEDB | LATEST-POINT | 4.18     | 11964.72 pts/s    | 0.60 ms   | 1.44 ms    | 26.5%   | 68.7%    | 9455.1 MB  | 9468.9 MB  |
| TIMESCALEDB | DOWNSAMPLE   | 4.85     | 133990.23 pts/s   | 0.74 ms   | 1.59 ms    | 28.5%   | 71.5%    | 9454.6 MB  | 9467.9 MB  |
| TIMESCALEDB | RANGE-QUERY  | 4.49     | 556226.83 pts/s   | 0.67 ms   | 1.52 ms    | 27.4%   | 70.0%    | 9453.8 MB  | 9466.9 MB  |
| TIMESCALEDB | VALUE-FILTER | 3231.41  | 268.51 pts/s      | 629.15 ms | 3945.32 ms | 98.3%   | 100.0%   | 9630.1 MB  | 9658.4 MB  |
| IOTDB       | BATCH-SMALL  | 10.11    | 494743.40 pts/s   | 0.35 ms   | 0.50 ms    | 9.3%    | 41.6%    | 12165.1 MB | 12185.6 MB |
| IOTDB       | BATCH-LARGE  | 181.41   | 27562372.45 pts/s | 6.93 ms   | 67.48 ms   | 47.0%   | 95.1%    | 15070.8 MB | 15564.8 MB |
| IOTDB       | OUT-OF-ORDER | 30.63    | 16326483.43 pts/s | 1.09 ms   | 2.04 ms    | 26.4%   | 64.2%    | 15517.3 MB | 15564.8 MB |
| IOTDB       | WRITE        | 28.55    | 17511476.59 pts/s | 1.04 ms   | 1.48 ms    | 17.4%   | 56.4%    | 15556.7 MB | 15575.0 MB |
| IOTDB       | READ         | 36.92    | 28404.80 pts/s    | 7.07 ms   | 82.77 ms   | 70.2%   | 85.1%    | 15553.5 MB | 15575.0 MB |
| IOTDB       | LATEST-POINT | 4.38     | 11427.87 pts/s    | 0.64 ms   | 1.35 ms    | 20.3%   | 56.5%    | 15751.7 MB | 15820.8 MB |
| IOTDB       | DOWNSAMPLE   | 9.94     | 65411.74 pts/s    | 1.74 ms   | 4.84 ms    | 47.3%   | 79.7%    | 15820.8 MB | 15820.8 MB |
| IOTDB       | RANGE-QUERY  | 7.47     | 334858.48 pts/s   | 1.25 ms   | 2.98 ms    | 38.4%   | 61.7%    | 15820.8 MB | 15820.8 MB |
| IOTDB       | VALUE-FILTER | 113.56   | 7640.84 pts/s     | 22.29 ms  | 76.59 ms   | 76.6%   | 88.7%    | 15892.0 MB | 15933.4 MB |

---

## Analysis

### Write performance

IoTDB dominates write throughput at every batch size. The gap is explained by three compounding factors:

**Protocol overhead.** IoTDB's SESSION_BY_TABLET uses a binary Thrift RPC over TCP — one syscall submits a typed columnar tablet directly into the TsFile write buffer. InfluxDB requires an HTTP request with line-protocol text parsing. TimescaleDB goes through the full PostgreSQL stack: TCP, libpq, parser, planner, WAL write, MVCC row format.

**Memory buffering.** IoTDB pre-allocates a large JVM heap (~12 GB in these results) and buffers incoming tablets in memory before flushing to disk. It is essentially writing to RAM until the memtable fills. InfluxDB's TSM cache is capped at 1 GB by default. TimescaleDB writes synchronously through the WAL before acknowledging, offering stronger durability but lower raw throughput.

**Batch size sensitivity.** The `batch-small` vs `batch-large` comparison shows this clearly:

| DB          | BATCH-SMALL pts/s | BATCH-LARGE pts/s |  Ratio |
|-------------|-------------------|-------------------|--------|
| InfluxDB    |             5,169 |         2,193,905 |   424x |
| TimescaleDB |             4,455 |           160,547 |    36x |
| IoTDB       |            24,268 |        13,897,643 |   573x |

InfluxDB and IoTDB are extremely sensitive to batch size because of per-request overhead (HTTP round-trip and Thrift call respectively). TimescaleDB's lower ratio reflects PostgreSQL's WAL flush cost dominating even for small batches — the per-row overhead is already high, so larger batches help less.

**Out-of-order writes.** InfluxDB handles them nearly as fast as sequential writes (272K vs 439K pts/s). TimescaleDB is similar (132K vs 134K) since PostgreSQL's B-tree index updates are order-independent. IoTDB slows down slightly (1.9M vs 2.1M) because its LSM-tree must compact disordered entries into sorted TsFile chunks.

### Read performance

The `Throughput (pts/s)` column for read tests sums the point counts of all active query types. This means `read` (10 types) appears higher than isolated single-type tests purely because more queries are running — it is not a sign that mixed workloads are faster. **Latency** is the meaningful metric for reads.

**Value-filter queries are the clearest differentiator.** Finding records that match a value predicate (`sensor > threshold`) cannot be answered from time-based indexes alone. Each database must either do a full chunk scan or maintain a secondary index:

| DB          | Value-filter avg lat | Value-filter P99 lat |
|-------------|----------------------|----------------------|
| IoTDB       |              3.79 ms |             14.22 ms |
| TimescaleDB |             40.12 ms |            251.06 ms |
| InfluxDB    |             89.85 ms |            341.34 ms |

IoTDB stores min/max statistics per TsFile chunk and uses them to skip chunks that cannot contain matching values. InfluxDB has no equivalent — it scans all TSM blocks. TimescaleDB relies on PostgreSQL's BRIN index, which gives partial pruning but still scans substantially more data than IoTDB's statistics-based approach.

**Downsampling (GROUP BY time buckets)** is where TimescaleDB shows strength relative to InfluxDB despite its write disadvantage:

| DB          | Downsample avg lat |
|-------------|--------------------|
| TimescaleDB |            0.72 ms |
| IoTDB       |            1.07 ms |
| InfluxDB    |            6.85 ms |

TimescaleDB's `time_bucket()` aggregation runs entirely inside the PostgreSQL executor with its hot shared_buffers cache. InfluxDB's Flux aggregation engine has higher per-query overhead.

### The latest-point throughput illusion

The `pts/s` figure for `latest-point` appears low compared to `range-query` because the two queries return fundamentally different amounts of data per call: a range query returns hundreds of points per call (high pts/s), while latest-point returns exactly one point per call (pts/s ≈ queries/second). **Latency** is the correct metric here:

| DB          | Latest-point avg lat | Range-query avg lat |
|-------------|----------------------|---------------------|
| TimescaleDB |          **0.50 ms** |             0.64 ms |
| IoTDB       |          **0.78 ms** |             1.35 ms |
| InfluxDB    |         **10.85 ms** |             6.50 ms |

TimescaleDB and IoTDB are actually *faster* for latest-point than for range queries — TimescaleDB via a `SELECT ... ORDER BY time DESC LIMIT 1` reverse B-tree scan, and IoTDB via a dedicated in-memory last-value cache that bypasses TsFile entirely. InfluxDB has no equivalent shortcut and must seek to the tail of each series in its TSM blocks, making it the only database where latest-point is slower than a range scan.

### Memory usage

IoTDB's dominant write throughput comes with a significant cost: it occupies ~12 GB of RAM throughout the run, compared to InfluxDB's ~300–900 MB and TimescaleDB's ~5.5 GB. IoTDB buffers all incoming tablets in a JVM heap before flushing columnar TsFile segments to disk. This is an architectural trade-off — high write throughput in exchange for high memory pressure. In memory-constrained IoT gateway deployments this would be a disqualifying factor.

TimescaleDB's 5.5 GB figure requires context. PostgreSQL's `shared_buffers` is set to the default 128 MB, yet `docker stats` reports ~5.4 GB from the very first test. The gap is the Linux OS page cache: PostgreSQL bypasses `shared_buffers` for large sequential scans and relies heavily on the kernel's file system cache, which the container's cgroup accounts toward its RSS. After the first few tests warm the file system cache, most of TimescaleDB's reported memory is OS-managed page cache rather than database-controlled buffers. This inflates the comparison: InfluxDB and IoTDB manage their own in-process caches (TSM cache and JVM heap respectively), so their `docker stats` numbers reflect real application memory more directly.

### Summary

| Workload                          | Best DB     | Reason                                    |
|-----------------------------------|-------------|-------------------------------------------|
| High-rate sequential ingestion    | IoTDB       | Binary tablet protocol + memory buffering |
| Large-batch bulk loading          | IoTDB       | Vectorised columnar write path            |
| Single-point streaming (BATCH=1)  | IoTDB       | Lower Thrift overhead vs HTTP/WAL         |
| Out-of-order tolerance            | InfluxDB    | Higher absolute OOO pts/s at every scale  |
| Dashboard downsampling            | TimescaleDB | time_bucket() in hot shared_buffers       |
| Bulk time-range export            | TimescaleDB | Chunk pruning + warm OS page cache        |
| Threshold alerting (value filter) | IoTDB       | Chunk statistics for early pruning        |
| Real-time last-value lookup       | TimescaleDB | Sub-millisecond reverse index scan        |
| Memory efficiency                 | InfluxDB    | TSM cache capped at 1 GB by default       |

IoTDB is the clear winner for write-heavy workloads but requires substantial memory and is purpose-built for the IoT domain. TimescaleDB trades raw write speed for SQL compatibility, mature tooling, and surprisingly strong read performance once data is cached. InfluxDB occupies the middle ground: better write throughput than TimescaleDB, better memory efficiency than IoTDB, but weaker on complex read patterns.

---

## Medium-scale validation

Running the same workload with 5× more loops (5,000 vs 1,000) confirms most of the small-scale analysis but also surfaces two false positives and several new findings.

### What held up

**IoTDB write dominance is structural, not a warm-up artifact.** At medium scale the gap widens: IoTDB reaches 6.4 M pts/s vs InfluxDB's 363 K and TimescaleDB's 126 K. The throughput *increases* with dataset size (2.1 M → 6.4 M for sequential write), which is consistent with JVM JIT compilation saturating the Thrift write path after enough iterations. The small-scale numbers understate IoTDB's ceiling.

**TimescaleDB downsample is genuinely cache-resident.** Latency is 0.72 ms at small and 0.67 ms at medium — effectively constant. Because `time_bucket()` queries scan a fixed time window (not the full dataset), the query cost does not grow with total data volume once the relevant chunks are in shared_buffers. This is the strongest validation in the dataset.

**IoTDB's value-filter chunk-statistics advantage is a constant factor, not asymptotic.** All three databases scale roughly linearly with data size for value-filter:

| DB          | Small avg lat | Medium avg lat | Ratio | Expected (5×) |
|-------------|---------------|----------------|-------|---------------|
| IoTDB       |     3.79 ms   |    19.17 ms    |  5.1× |     5×        |
| TimescaleDB |    40.12 ms   |   175.07 ms    |  4.4× |     5×        |
| InfluxDB    |    89.85 ms   |   396.15 ms    |  4.4× |     5×        |

IoTDB remains ~5–20× faster in absolute terms, but the gap does not grow with scale. The chunk-statistics skip is a pruning optimisation, not an index.

### False positives corrected

**"InfluxDB handles out-of-order writes nearly as fast as sequential" — this was imprecise.** The actual drop is 38% at small scale (272 K vs 439 K pts/s) and 32% at medium (249 K vs 363 K pts/s). That is a consistent and significant overhead, not a negligible one. The correct statement is that InfluxDB tolerates out-of-order writes with moderate throughput cost, which is markedly better than IoTDB's TSM compaction path. Two separate metrics matter here and they point in different directions:

- **Absolute OOO throughput**: InfluxDB leads at every scale (272 K vs 132 K pts/s at small), so it is the better choice when raw ingestion rate under disorder matters.
- **Relative OOO degradation**: TimescaleDB is more tolerant — it loses less than 1% throughput from OOO at small and medium scales, versus InfluxDB's 32–38%. TimescaleDB's B-tree index updates are order-independent, so late-arriving rows incur no extra cost until the hypertable grows large enough to trigger chunk decompression (which only surfaces at large scale, where TimescaleDB's OOO penalty reaches 23%).

**InfluxDB's memory footprint was understated.** The small-scale description of "~300–900 MB" and the claim that the TSM cache is "capped at 1 GB by default" are misleading at scale. At medium scale, batch-large and out-of-order peak at **3.1 GB**, and the summary table's "memory efficiency" win for InfluxDB only holds for the small write test. Total process RSS includes WAL buffers, the series index, and Go runtime overhead well beyond the TSM cache limit.

### New findings from medium scale

**InfluxDB latest-point latency scales with dataset size; TimescaleDB and IoTDB do not.**

| DB          | Small avg lat | Medium avg lat |
|-------------|---------------|----------------|
| InfluxDB    |   10.85 ms    |    23.18 ms    |
| IoTDB       |    0.78 ms    |     0.75 ms    |
| TimescaleDB |    0.50 ms    |     0.53 ms    |

TimescaleDB's reverse B-tree scan and IoTDB's in-memory last-value cache are O(1) with respect to total stored data. InfluxDB must seek to the end of each series' TSM file blocks, and that seek cost grows as more files accumulate. In any long-running deployment this gap will compound.

**TimescaleDB read P99 latency degrades sharply at medium scale** (275 ms → 1672 ms for the mixed `READ` workload). The average improves relative to InfluxDB (57 ms vs 121 ms), but the tail grows faster. Queries that fall outside the shared_buffers warm region trigger full chunk scans with no bounding index, producing unbounded tail latency as the dataset grows.

**IoTDB reads scale sublinearly.** The mixed `READ` average latency increases only 2.9× for 5× more data (2.26 ms → 6.62 ms). This is better than InfluxDB (4.3×) or TimescaleDB (4.4×), suggesting IoTDB's JVM heap cache covers a proportionally larger share of the working set as queries run longer.

### Revised summary

The summary table from the small-scale analysis stands, with two corrections:

- **Out-of-order tolerance**: InfluxDB delivers higher absolute OOO throughput at every scale. However, TimescaleDB has a smaller *relative* degradation from OOO (<1% at small/medium, 23% at large) compared to InfluxDB's consistent 32–38% drop. The summary table winner (InfluxDB) is correct for absolute pts/s but should not be read as "handles disorder more gracefully."
- **Memory efficiency**: InfluxDB wins only at small scale; at medium scale its peak RSS (3.1 GB) is comparable to or worse than TimescaleDB's starting footprint.

---

## Large-scale validation

The large scale (10 clients, 50 devices, 20 sensors, 5,000 loops) contains roughly **20× more data than medium** and **100× more than small**. At this volume several trends from the medium analysis sharpen into clearer patterns and two new failure modes emerge.

### What continues to hold

**IoTDB write dominance widens.** The absolute gap grows at every scale:

| DB          | Small pts/s | Medium pts/s | Large pts/s |
|-------------|-------------|--------------|-------------|
| IoTDB       |   2,130,911 |    6,378,193 |  17,511,476 |
| InfluxDB    |     439,381 |      363,669 |   1,178,162 |
| TimescaleDB |     133,677 |      126,131 |     358,761 |

IoTDB WRITE throughput scales superlinearly with both dataset size and client count, reflecting continued JIT saturation of the Thrift write path. The ratio over InfluxDB is consistent (~5–17× depending on scale); the ratio over TimescaleDB grows from 16× to 50× between small and large.

**TimescaleDB downsample and latest-point remain constant-latency across all three scales.**

| DB          | Downsample small | Downsample medium | Downsample large |
|-------------|------------------|-------------------|------------------|
| TimescaleDB |      0.72 ms     |       0.67 ms     |      0.74 ms     |
| IoTDB       |      1.07 ms     |       1.26 ms     |      1.74 ms     |
| InfluxDB    |      6.85 ms     |       7.17 ms     |      9.91 ms     |

| DB          | Latest-point small | Latest-point medium | Latest-point large |
|-------------|--------------------|---------------------|--------------------|
| TimescaleDB |       0.50 ms      |        0.53 ms      |       0.60 ms      |
| IoTDB       |       0.78 ms      |        0.75 ms      |       0.64 ms      |
| InfluxDB    |      10.85 ms      |       23.18 ms      |      34.48 ms      |

TimescaleDB downsample stays sub-millisecond across 100× data growth. The `time_bucket()` result is fully validated as cache-resident and query-window-bounded. InfluxDB latest-point shows a clean linear progression (10.85 → 23.18 → 34.48 ms), confirming the TSM tail-seek cost grows proportionally with stored files. This is now a three-point regression with no ambiguity.

**IoTDB's value-filter advantage becomes sublinear, not just a constant factor.** This is the biggest revision from the medium-scale analysis, which only showed a constant-factor difference:

| DB          | Small avg lat | Medium avg lat | Large avg lat | Small→Large ratio | Data ratio |
|-------------|---------------|----------------|---------------|-------------------|------------|
| IoTDB       |     3.79 ms   |    19.17 ms    |    22.29 ms   |        5.9×       |   100×     |
| TimescaleDB |    40.12 ms   |   175.07 ms    |   629.15 ms   |       15.7×       |   100×     |
| InfluxDB    |    89.85 ms   |   396.15 ms    |   537.48 ms   |        6.0×       |   100×     |

IoTDB's value-filter latency grew only 5.9× for 100× more data. At medium scale it appeared linear; at large scale it breaks from linearity. IoTDB's chunk min/max statistics skip increasingly large fractions of the dataset as the data grows denser — the pruning ratio improves with scale. TimescaleDB grows 15.7×, worse than linear, consistent with BRIN index becoming less effective as more non-contiguous pages must be read. InfluxDB at 6.0× is surprisingly sublinear too, likely because the TSM block structure allows skipping entire files based on time-range metadata even for value predicates.

### New findings from large scale

**TimescaleDB out-of-order penalty surfaces at large scale.** At small and medium it was effectively zero (OOO ≈ WRITE throughput). At large scale it degrades to 276 K vs 358 K pts/s — a **23% drop**. As the hypertable grows, inserting out-of-order rows forces writes into older, already-compressed chunks, triggering decompression-recompression cycles that do not appear at smaller volumes. This reverses the earlier assessment that TimescaleDB is insensitive to write order.

**TimescaleDB becomes CPU-saturated on reads at large scale.** The mixed `READ` workload averages **97.7% CPU** (peak 99.7%), and value-filter averages **98.3%** (peak 100%). P99 latency for `READ` reaches 4,232 ms. This is not a storage bottleneck — it is the query executor running out of compute. At this point adding more RAM or faster disks would not help; only a stronger CPU or horizontal sharding would. InfluxDB reaches 85% CPU on read but does not saturate. IoTDB peaks at 70% for the same workload.

**IoTDB batch-small throughput breaks the expected ceiling.** Across scales: 24,268 → 79,923 → **494,743 pts/s**, with average latency *decreasing* from 1.54 ms to 0.35 ms as load increases. (Note: the small-scale run also produces an anomalous P99 of 1.19 ms — lower than its own 1.54 ms average — which is statistically only possible if a small fraction of operations had very large outliers, likely JVM GC pauses, pulling the average above the 99th percentile on a short run. This artifact does not appear at medium or large scale and does not affect the throughput figures.) This is only possible if the JVM JIT compiler is progressively optimising the hot Thrift serialisation path during the run. At large scale, the benchmark runs long enough for the JIT to reach peak compilation, making the large-scale batch-small numbers the most representative of IoTDB's steady-state single-point ingestion throughput.

**TimescaleDB batch-large hits the benchmark timeout at large scale** (exactly 3,600 s). The P99 of 1,639 ms and average latency of 473 ms reflect a database under sustained WAL pressure: with 50 devices and 100-row batches, each write touches 50 hypertable partitions and triggers 50 WAL flushes, and the cumulative cost exhausts the time budget before the full loop count completes.

**IoTDB memory footprint grows beyond its pre-allocated heap at large scale** (~15.5 GB vs ~12.7 GB at medium). The JVM heap expanded to accommodate the larger write buffer and series index. The earlier claim that IoTDB memory is a fixed pre-allocation only holds up to medium scale; at large volumes the heap grows dynamically. It remains below 16 GB, still far below a hypothetical equal-memory-budget comparison with TimescaleDB (~9.7 GB) or InfluxDB (~1.5 GB at large WRITE), but the "fixed cost" framing was too strong.

### Final summary across all scales

| Claim from original analysis                                  | Status after large-scale data                                                  |
|---------------------------------------------------------------|--------------------------------------------------------------------------------|
| IoTDB dominates write throughput                              | **Confirmed and strengthened** — gap widens to 50× over TimescaleDB            |
| TimescaleDB downsample is cache-resident and constant-latency | **Confirmed** — sub-ms across 100× data growth                                 |
| TimescaleDB/IoTDB latest-point is O(1) w.r.t. dataset size    | **Confirmed** — both stay flat; InfluxDB shows clean linear growth             |
| IoTDB value-filter advantage is a constant factor             | **Partially wrong** — at large scale it becomes sublinear (5.9× for 100× data) |
| TimescaleDB OOO cost is negligible                            | **Wrong at large scale** — 23% penalty emerges from chunk decompression        |
| InfluxDB memory is ~300–900 MB                                | **Wrong** — peaks at 2.6 GB at large BATCH-LARGE                               |
| IoTDB memory is a fixed pre-allocation                        | **Overstated** — heap grows to ~15.5 GB at large scale                         |
| TimescaleDB P99 tail latency grows with data                  | **Confirmed and severe** — 275 ms → 1,672 ms → 4,232 ms across scales          |

---

## Limitations

- **Cache warm-up:** Read tests run sequentially on the same dataset. Later tests benefit from warmer OS page cache and DB in-memory structures. For production-quality isolation, each test should flush caches and restart containers.
- **Default configurations:** No database was tuned beyond what is necessary to run the benchmark (TimescaleDB uses PostgreSQL's default `shared_buffers=128 MB`). Tuning each database to use equal memory budgets would narrow some gaps.
- **IoTDB memory buffering:** IoTDB's write throughput is partly a consequence of deferred durability — data lives in RAM until the memtable is flushed. The numbers reflect in-memory write acknowledgement, not guaranteed persistence.
- **Single-node, single-machine:** All three databases and the benchmark clients ran on the same host. Network latency (relevant for InfluxDB's HTTP API) is near zero, which flattens a real-world disadvantage.

---

## Test Environment

### Host machine

| Component | Details                                                                    |
|-----------|----------------------------------------------------------------------------|
| CPU       | Intel Core i5-11400F (6 cores / 12 threads, 2.60 GHz base, 4.40 GHz boost) |
| RAM       | 32 GB                                                                      |
| Disk      | 500 GB                                                                     |
| OS        | NixOS (Linux 6.12)                                                         |

### Docker containers

All three containers run on the same host with no explicit CPU or memory limits set — each competes for the full machine resources during its benchmark run.

| Container   | Image                                               |
|-------------|-----------------------------------------------------|
| IoTDB       | `apache/iotdb:1.3.0-standalone`                     |
| InfluxDB    | `influxdb:2.7-alpine`                               |
| TimescaleDB | `timescale/timescaledb:latest-pg15` (PostgreSQL 15) |
