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

+---------------------+-----------------------------------------------------------------------+
| Layer               | Technology                                                            |
|---------------------|-----------------------------------------------------------------------|
| Workload generator  | [iot-benchmark](https://github.com/thulab/iot-benchmark) (Java, Maven)|
| Orchestration       | Python 3                                                              |
| Database containers | Docker Compose                                                        |
| Dev environment     | Nix flake (`nix develop`, `nix run`)                                  |
| IoTDB               | apache/iotdb:1.3.0-standalone                                         |
| InfluxDB            | influxdb:2.7-alpine                                                   |
| TimescaleDB         | timescale/timescaledb:latest-pg15                                     |
+---------------------+-----------------------------------------------------------------------+

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

+-----------+---------+--------------------------------------------------------+
| Flag      | Default | Values                                                 |
|-----------|---------|--------------------------------------------------------|
| `--db`    | `all`   | `all`, `influxdb`, `timescaledb`, `iotdb`              |
| `--scale` | `small` | `small` (~5 min), `medium` (~30 min), `large` (~2 h)   |
+-----------+---------+--------------------------------------------------------+

`--test` (default `all`): `all`, `write`, `out-of-order`, `batch-small`, `batch-large`, `read`, `latest-point`, `downsample`, `range-query`, `value-filter`

### Scale parameters

+--------+---------+---------+---------+------------+-------+
| Scale  | Clients | Devices | Sensors | Batch size | Loops |
|--------|---------|---------|---------|------------|-------|
| small  | 5       | 10      | 10      | 100        | 1000  |
| medium | 5       | 10      | 10      | 100        | 5000  |
| large  | 10      | 50      | 20      | 100        | 5000  |
+--------+---------+---------+---------+------------+-------+

---

## Test Types

When `--test all` is used, tests run in this order: write variants first (each clears and re-seeds the database), then read variants (which all operate on the data written by the baseline `write` test).

### Write tests

+----------------+-----------------------------------------------------------------------------------------------------------------------------------------------+
| Test           | What it measures                                                                                                                              |
|----------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| `write`        | Baseline sequential ingestion - ordered timestamps, default batch size                                                                        |
| `out-of-order` | 20% late-arriving data (Poisson distribution) - simulates network-delayed IoT sensors; reveals write-amplification from out-of-order handling |
| `batch-small`  | `BATCH_SIZE=1` - one write request per data point; isolates per-request protocol overhead (HTTP round-trip, WAL flush, Thrift call)           |
| `batch-large`  | `BATCH_SIZE=1000` - large batches; tests bulk-loading efficiency and where each database's batching ceiling lies                              |
+----------------+-----------------------------------------------------------------------------------------------------------------------------------------------+

### Read tests

+----------------+-----------------------------------------------+--------------------------------------------------------------------------------------------+
| Test           | Queries active                                | What it measures                                                                           |
|----------------|-----------------------------------------------|--------------------------------------------------------------------------------------------|
| `read`         | All 10 supported types                        | Comprehensive read baseline - all analytics patterns equally weighted                      |
| `latest-point` | `LATEST_POINT`                                | Real-time monitoring - "current sensor value"; tests last-value index vs full reverse scan |
| `downsample`   | `GROUP_BY`                                    | Dashboard aggregation - time-bucketed averages; tests native downsampling push-down        |
| `range-query`  | `TIME_RANGE`                                  | Bulk data export - sequential scan over a time window; tests decompression throughput      |
| `value-filter` | `VALUE_RANGE`, `AGG_VALUE`, `AGG_RANGE_VALUE` | Threshold alerting - "readings above X"; tests predicate pushdown into the storage layer   |
+----------------+-----------------------------------------------+--------------------------------------------------------------------------------------------+

---

## Results

### Small scale

```
+-------------+--------------+----------+-------------------+-----------+------------+---------+----------+------------+------------+
| DB          | Test         | Time (s) | Throughput        | Avg Lat   | P99 Lat    | Avg CPU | Peak CPU | Avg Mem    | Peak Mem   |
+-------------+--------------+----------+-------------------+-----------+------------+---------+----------+------------+------------+
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
+-------------+--------------+----------+-------------------+-----------+------------+---------+----------+------------+------------+
```

### Medium scale

```
+-------------+--------------+----------+-------------------+-----------+------------+---------+----------+------------+------------+
| DB          | Test         | Time (s) | Throughput        | Avg Lat   | P99 Lat    | Avg CPU | Peak CPU | Avg Mem    | Peak Mem   |
+-------------+--------------+----------+-------------------+-----------+------------+---------+----------+------------+------------+
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
+-------------+--------------+----------+-------------------+-----------+------------+---------+----------+------------+------------+
```

---

## Analysis

### Write performance

IoTDB dominates write throughput at every batch size. The gap is explained by three compounding factors:

**Protocol overhead.** IoTDB's SESSION_BY_TABLET uses a binary Thrift RPC over TCP — one syscall submits a typed columnar tablet directly into the TsFile write buffer. InfluxDB requires an HTTP request with line-protocol text parsing. TimescaleDB goes through the full PostgreSQL stack: TCP, libpq, parser, planner, WAL write, MVCC row format.

**Memory buffering.** IoTDB pre-allocates a large JVM heap (~12 GB in these results) and buffers incoming tablets in memory before flushing to disk. It is essentially writing to RAM until the memtable fills. InfluxDB's TSM cache is capped at 1 GB by default. TimescaleDB writes synchronously through the WAL before acknowledging, offering stronger durability but lower raw throughput.

**Batch size sensitivity.** The `batch-small` vs `batch-large` comparison shows this clearly:

+-------------+-------------------+-------------------+--------+
| DB          | BATCH-SMALL pts/s | BATCH-LARGE pts/s |  Ratio |
|-------------|-------------------|-------------------|--------|
| InfluxDB    |             5,169 |         2,193,905 |   424x |
| TimescaleDB |             4,455 |           160,547 |    36x |
| IoTDB       |            24,268 |        13,897,643 |   573x |
+-------------+-------------------+-------------------+--------+

InfluxDB and IoTDB are extremely sensitive to batch size because of per-request overhead (HTTP round-trip and Thrift call respectively). TimescaleDB's lower ratio reflects PostgreSQL's WAL flush cost dominating even for small batches — the per-row overhead is already high, so larger batches help less.

**Out-of-order writes.** InfluxDB handles them nearly as fast as sequential writes (272K vs 439K pts/s). TimescaleDB is similar (132K vs 134K) since PostgreSQL's B-tree index updates are order-independent. IoTDB slows down slightly (1.9M vs 2.1M) because its LSM-tree must compact disordered entries into sorted TsFile chunks.

### Read performance

The `Throughput (pts/s)` column for read tests sums the point counts of all active query types. This means `read` (10 types) appears higher than isolated single-type tests purely because more queries are running — it is not a sign that mixed workloads are faster. **Latency** is the meaningful metric for reads.

**Value-filter queries are the clearest differentiator.** Finding records that match a value predicate (`sensor > threshold`) cannot be answered from time-based indexes alone. Each database must either do a full chunk scan or maintain a secondary index:

+-------------+----------------------+----------------------+
| DB          | Value-filter avg lat | Value-filter P99 lat |
|-------------|----------------------|----------------------|
| IoTDB       |              3.79 ms |             14.22 ms |
| TimescaleDB |             40.12 ms |            251.06 ms |
| InfluxDB    |             89.85 ms |            341.34 ms |
+-------------+----------------------+----------------------+

IoTDB stores min/max statistics per TsFile chunk and uses them to skip chunks that cannot contain matching values. InfluxDB has no equivalent — it scans all TSM blocks. TimescaleDB relies on PostgreSQL's BRIN index, which gives partial pruning but still scans substantially more data than IoTDB's statistics-based approach.

**Downsampling (GROUP BY time buckets)** is where TimescaleDB shows strength relative to InfluxDB despite its write disadvantage:

+-------------+--------------------+
| DB          | Downsample avg lat |
|-------------|--------------------|
| TimescaleDB |            0.72 ms |
| IoTDB       |            1.07 ms |
| InfluxDB    |            6.85 ms |
+-------------+--------------------+

TimescaleDB's `time_bucket()` aggregation runs entirely inside the PostgreSQL executor with its hot shared_buffers cache. InfluxDB's Flux aggregation engine has higher per-query overhead.

### The latest-point throughput illusion

The `pts/s` figure for `latest-point` appears low compared to `range-query` because the two queries return fundamentally different amounts of data per call: a range query returns hundreds of points per call (high pts/s), while latest-point returns exactly one point per call (pts/s ≈ queries/second). **Latency** is the correct metric here:

+-------------+----------------------+---------------------+
| DB          | Latest-point avg lat | Range-query avg lat |
|-------------|----------------------|---------------------|
| TimescaleDB |          **0.50 ms** |             0.64 ms |
| IoTDB       |          **0.78 ms** |             1.35 ms |
| InfluxDB    |         **10.85 ms** |             6.50 ms |
+-------------+----------------------+---------------------+

TimescaleDB and IoTDB are actually *faster* for latest-point than for range queries — TimescaleDB via a `SELECT ... ORDER BY time DESC LIMIT 1` reverse B-tree scan, and IoTDB via a dedicated in-memory last-value cache that bypasses TsFile entirely. InfluxDB has no equivalent shortcut and must seek to the tail of each series in its TSM blocks, making it the only database where latest-point is slower than a range scan.

### Memory usage

IoTDB's dominant write throughput comes with a significant cost: it occupies ~12 GB of RAM throughout the run, compared to InfluxDB's ~300–900 MB and TimescaleDB's ~5.5 GB. IoTDB buffers all incoming tablets in a JVM heap before flushing columnar TsFile segments to disk. This is an architectural trade-off — high write throughput in exchange for high memory pressure. In memory-constrained IoT gateway deployments this would be a disqualifying factor.

### Summary

+-----------------------------------+-------------+-------------------------------------------+
| Workload                          | Best DB     | Reason                                    |
|-----------------------------------|-------------|-------------------------------------------|
| High-rate sequential ingestion    | IoTDB       | Binary tablet protocol + memory buffering |
| Large-batch bulk loading          | IoTDB       | Vectorised columnar write path            |
| Single-point streaming (BATCH=1)  | IoTDB       | Lower Thrift overhead vs HTTP/WAL         |
| Out-of-order tolerance            | InfluxDB    | TSM handles disorder cheaply              |
| Dashboard downsampling            | TimescaleDB | time_bucket() in hot shared_buffers       |
| Bulk time-range export            | TimescaleDB | Chunk pruning + warm OS page cache        |
| Threshold alerting (value filter) | IoTDB       | Chunk statistics for early pruning        |
| Real-time last-value lookup       | TimescaleDB | Sub-millisecond reverse index scan        |
| Memory efficiency                 | InfluxDB    | TSM cache capped at 1 GB by default       |
+-----------------------------------+-------------+-------------------------------------------+

IoTDB is the clear winner for write-heavy workloads but requires substantial memory and is purpose-built for the IoT domain. TimescaleDB trades raw write speed for SQL compatibility, mature tooling, and surprisingly strong read performance once data is cached. InfluxDB occupies the middle ground: better write throughput than TimescaleDB, better memory efficiency than IoTDB, but weaker on complex read patterns.

---

## Medium-scale validation

Running the same workload with 5× more loops (5,000 vs 1,000) confirms most of the small-scale analysis but also surfaces two false positives and several new findings.

### What held up

**IoTDB write dominance is structural, not a warm-up artifact.** At medium scale the gap widens: IoTDB reaches 6.4 M pts/s vs InfluxDB's 363 K and TimescaleDB's 126 K. The throughput *increases* with dataset size (2.1 M → 6.4 M for sequential write), which is consistent with JVM JIT compilation saturating the Thrift write path after enough iterations. The small-scale numbers understate IoTDB's ceiling.

**TimescaleDB downsample is genuinely cache-resident.** Latency is 0.72 ms at small and 0.67 ms at medium — effectively constant. Because `time_bucket()` queries scan a fixed time window (not the full dataset), the query cost does not grow with total data volume once the relevant chunks are in shared_buffers. This is the strongest validation in the dataset.

**IoTDB's value-filter chunk-statistics advantage is a constant factor, not asymptotic.** All three databases scale roughly linearly with data size for value-filter:

+-------------+---------------+----------------+-------+---------------+
| DB          | Small avg lat | Medium avg lat | Ratio | Expected (5×) |
|-------------|---------------|----------------|-------|---------------|
| IoTDB       |     3.79 ms   |    19.17 ms    |  5.1× |     5×        |
| TimescaleDB |    40.12 ms   |   175.07 ms    |  4.4× |     5×        |
| InfluxDB    |    89.85 ms   |   396.15 ms    |  4.4× |     5×        |
+-------------+---------------+----------------+-------+---------------+

IoTDB remains ~5–20× faster in absolute terms, but the gap does not grow with scale. The chunk-statistics skip is a pruning optimisation, not an index.

### False positives corrected

**"InfluxDB handles out-of-order writes nearly as fast as sequential" — this was imprecise.** The actual drop is 38% at small scale (272 K vs 439 K pts/s) and 32% at medium (249 K vs 363 K pts/s). That is a consistent and significant overhead, not a negligible one. The correct statement is that InfluxDB tolerates out-of-order writes with moderate throughput cost, which is still markedly better than IoTDB's TSM compaction path and roughly equivalent to TimescaleDB.

**InfluxDB's memory footprint was understated.** The small-scale description of "~300–900 MB" and the claim that the TSM cache is "capped at 1 GB by default" are misleading at scale. At medium scale, batch-large and out-of-order peak at **3.1 GB**, and the summary table's "memory efficiency" win for InfluxDB only holds for the small write test. Total process RSS includes WAL buffers, the series index, and Go runtime overhead well beyond the TSM cache limit.

### New findings from medium scale

**InfluxDB latest-point latency scales with dataset size; TimescaleDB and IoTDB do not.**

+-------------+---------------+----------------+
| DB          | Small avg lat | Medium avg lat |
|-------------|---------------|----------------|
| InfluxDB    |   10.85 ms    |    23.18 ms    |
| IoTDB       |    0.78 ms    |     0.75 ms    |
| TimescaleDB |    0.50 ms    |     0.53 ms    |
+-------------+---------------+----------------+

TimescaleDB's reverse B-tree scan and IoTDB's in-memory last-value cache are O(1) with respect to total stored data. InfluxDB must seek to the end of each series' TSM file blocks, and that seek cost grows as more files accumulate. In any long-running deployment this gap will compound.

**TimescaleDB read P99 latency degrades sharply at medium scale** (275 ms → 1672 ms for the mixed `READ` workload). The average improves relative to InfluxDB (57 ms vs 121 ms), but the tail grows faster. Queries that fall outside the shared_buffers warm region trigger full chunk scans with no bounding index, producing unbounded tail latency as the dataset grows.

**IoTDB reads scale sublinearly.** The mixed `READ` average latency increases only 2.9× for 5× more data (2.26 ms → 6.62 ms). This is better than InfluxDB (4.3×) or TimescaleDB (4.4×), suggesting IoTDB's JVM heap cache covers a proportionally larger share of the working set as queries run longer.

### Revised summary

The summary table from the small-scale analysis stands, with two corrections:

- **Out-of-order tolerance**: InfluxDB is better than TimescaleDB but the advantage is moderate (~30–38% throughput penalty), not negligible.
- **Memory efficiency**: InfluxDB wins only at small scale; at medium scale its peak RSS (3.1 GB) is comparable to or worse than TimescaleDB's starting footprint.

---

## Limitations

- **Cache warm-up:** Read tests run sequentially on the same dataset. Later tests benefit from warmer OS page cache and DB in-memory structures. For production-quality isolation, each test should flush caches and restart containers.
- **Default configurations:** No database was tuned beyond what is necessary to run the benchmark (TimescaleDB uses PostgreSQL's default `shared_buffers=128 MB`). Tuning each database to use equal memory budgets would narrow some gaps.
- **IoTDB memory buffering:** IoTDB's write throughput is partly a consequence of deferred durability — data lives in RAM until the memtable is flushed. The numbers reflect in-memory write acknowledgement, not guaranteed persistence.
- **Single-node, single-machine:** All three databases and the benchmark clients ran on the same host. Network latency (relevant for InfluxDB's HTTP API) is near zero, which flattens a real-world disadvantage.

---

## Test Environment

### Host machine

+-----------+----------------------------------------------------------------------------+
| Component | Details                                                                    |
|-----------|----------------------------------------------------------------------------|
| CPU       | Intel Core i5-11400F (6 cores / 12 threads, 2.60 GHz base, 4.40 GHz boost) |
| RAM       | 32 GB                                                                      |
| Disk      | 500 GB                                                                     |
| OS        | NixOS (Linux 6.12)                                                         |
+-----------+----------------------------------------------------------------------------+

### Docker containers

All three containers run on the same host with no explicit CPU or memory limits set — each competes for the full machine resources during its benchmark run.

+-------------+-----------------------------------------------------+
| Container   | Image                                               |
|-------------|-----------------------------------------------------|
| IoTDB       | `apache/iotdb:1.3.0-standalone`                     |
| InfluxDB    | `influxdb:2.7-alpine`                               |
| TimescaleDB | `timescale/timescaledb:latest-pg15` (PostgreSQL 15) |
+-------------+-----------------------------------------------------+
