# Time-Series Database Benchmark Suite

This repository provides a reproducible environment for benchmarking three major time-series databases: **InfluxDB (v2)**, **TimescaleDB**, and **Apache IoTDB**. 

It utilizes two standard benchmarking tools:
1. **TSBS (Time Series Benchmark Suite):** Using the QuestDB fork for native InfluxDB v2 support. Used to benchmark InfluxDB and TimescaleDB.
2. **IoT-Benchmark:** Developed by Tsinghua University. Used to benchmark Apache IoTDB.

---

## Table of Contents
1. [Cloning the Repository](#1-cloning-the-repository)
2. [Environment Setup](#2-environment-setup)
   - [Option A: NixOS / Nix Package Manager (Automated)](#option-a-nixos--nix-package-manager-automated)
   - [Option B: Non-NixOS (Manual Setup)](#option-b-non-nixos-manual-setup)
3. [Pre-Flight: InfluxDB DBRP Mapping](#3-pre-flight-influxdb-dbrp-mapping)
4. [Running the Benchmarks](#4-running-the-benchmarks)
   - [InfluxDB v2](#influxdb-v2-tsbs)
   - [TimescaleDB](#timescaledb-tsbs)
   - [Apache IoTDB](#apache-iotdb-iot-benchmark)

---

## 1. Cloning the Repository

Because this project uses Git Submodules to lock in the exact versions of the benchmark tools, you **must** clone the repository recursively:

```bash
git clone --recursive <your-repo-url>
cd <your-repo-directory>
```
*(If you already cloned it normally, run `git submodule update --init` to fetch the tools).*

---

## 2. Environment Setup

### Option A: NixOS / Nix Package Manager (Automated)
If you are using Nix with flakes enabled, setup is completely automated. The flake will install all toolchains, start the databases, compile the benchmark tools, and patch system variables automatically.

Just run:
```bash
nix develop
```
Once the compilation finishes, you will see a `Environment Ready!` message, and you can skip directly to **Step 3**.

### Option B: Non-NixOS (Manual Setup)
If you are on Ubuntu, macOS, or another standard OS, you will need to manually install the dependencies and compile the tools.

**Prerequisites:**
* Docker and Docker Compose
* Go (1.16+)
* Java (JDK 17)
* Maven (3.6+)
* GNU Make & Git

**Step 1: Start the Databases**
```bash
docker compose up -d
```

**Step 2: Compile TSBS (QuestDB Fork)**
```bash
cd questdb-tsbs
make all
export PATH=$PWD/bin:$PATH
cd ..
```

**Step 3: Compile IoT-Benchmark**
```bash
cd iot-benchmark
mvn clean package -pl influxdb-2.0,timescaledb,iotdb-1.3 -am -Dmaven.test.skip=true -U
cd ..
```

---

## 3. Pre-Flight: InfluxDB DBRP Mapping

**CRITICAL STEP FOR ALL USERS**
InfluxDB v2 uses "Buckets" instead of traditional databases. TSBS still attempts to write to a legacy v1 database named `benchmark`. You must create a mapping inside the InfluxDB container to redirect this traffic, otherwise, your writes will fail with a `404 no dbrp mapping found` error.

Run these commands in your terminal while the containers are running:

**For standard Bash/Zsh:**
```bash
BUCKET_ID=$(docker exec influxdb influx bucket list --org my-org --token my-super-secret-auth-token | grep my-bucket | awk '{print $1}')

docker exec influxdb influx v1 dbrp create \
  --db benchmark \
  --rp autogen \
  --bucket-id $BUCKET_ID \
  --default \
  --org my-org \
  --token my-super-secret-auth-token
```
*(Note for Fish shell users: use `set BUCKET_ID (docker exec...)` instead).*

---

## 4. Running the Benchmarks

Below are the commands to run the ingestion (write) and aggregation (read) tests. Ensure you are inside the root directory of the project before starting.

### InfluxDB v2 (TSBS)

**1. Generate Data:**
```bash
tsbs_generate_data --use-case="iot" --seed=123 --scale=100 \
  --timestamp-start="2023-01-01T00:00:00Z" \
  --timestamp-end="2023-01-02T00:00:00Z" \
  --log-interval="10s" --format="influx" | gzip > /tmp/influx-data.gz
```

**2. Load Data (Ingestion Benchmark):**
```bash
cat /tmp/influx-data.gz | gunzip | tsbs_load_influx \
  --urls="http://localhost:8086" \
  --auth-token="my-super-secret-auth-token" \
  --workers=4
```

**3. Generate & Run Queries (Read Benchmark):**
```bash
tsbs_generate_queries --use-case="iot" --seed=123 --scale=100 \
  --timestamp-start="2023-01-01T00:00:00Z" --timestamp-end="2023-01-02T00:00:00Z" \
  --format="influx" --query-type="high-load" | gzip > /tmp/influx-queries-high-load.gz

cat /tmp/influx-queries-high-load.gz | gunzip | tsbs_run_queries_influx \
  --urls="http://localhost:8086" \
  --auth-token="my-super-secret-auth-token" \
  --workers=4
```

---

### TimescaleDB (TSBS)

**1. Generate Data:**
```bash
tsbs_generate_data --use-case="iot" --seed=123 --scale=100 \
  --timestamp-start="2023-01-01T00:00:00Z" \
  --timestamp-end="2023-01-02T00:00:00Z" \
  --log-interval="10s" --format="timescaledb" | gzip > /tmp/timescale-data.gz
```

**2. Load Data (Ingestion Benchmark):**
```bash
cat /tmp/timescale-data.gz | gunzip | tsbs_load_timescaledb \
  --host="localhost" --port="5432" --user="postgres" --pass="postgrespassword123" --workers=4
```

**3. Generate & Run Queries (Read Benchmark):**
```bash
tsbs_generate_queries --use-case="iot" --seed=123 --scale=100 \
  --timestamp-start="2023-01-01T00:00:00Z" --timestamp-end="2023-01-02T00:00:00Z" \
  --format="timescaledb" --query-type="high-load" | gzip > /tmp/timescale-queries-high-load.gz

cat /tmp/timescale-queries-high-load.gz | gunzip | tsbs_run_queries_timescaledb \
  --host="localhost" --port="5432" --user="postgres" --pass="postgrespassword123" --workers=4
```

---

### Apache IoTDB (IoT-Benchmark)

Because IoT-Benchmark compiles into specific release folders, you must navigate into the compiled IoTDB directory to run tests.

**1. Navigate to the compiled directory:**
```bash
cd iot-benchmark/iotdb-1.3/target/iot-benchmark-iotdb-1.3/iot-benchmark-iotdb-1.3
```

**2. Configure the test:**
Edit the `conf/config.properties` file. Use the following baseline for an apples-to-apples ingestion test against the TSBS dataset:

```properties
DB_SWITCH=IoTDB-130-SESSION_BY_TABLET
HOST=127.0.0.1
PORT=6667
USERNAME=root
PASSWORD=root

# To test Writes: insertTest | To test Reads: queryTest
BENCHMARK_WORK_MODE=insertTest

# Dataset Size (1.55 Million Rows total)
DEVICE_NUMBER=100
SENSOR_NUMBER=10
DATA_TYPE=DOUBLE
LOOP=155

# Concurrency
CLIENT_NUMBER=10
BATCH_SIZE_PER_WRITE=100
CSV_OUTPUT=true
```

**3. Run the Benchmark:**
```bash
./benchmark.sh
```
*(Results will be printed to the console and saved as a CSV in the `data/` directory).*
