if [ ! -f "$PWD/iot-benchmark/influxdb-2.0/target/iot-benchmark-influxdb-2.0/iot-benchmark-influxdb-2.0/benchmark.sh" ] || \
   [ ! -f "$PWD/iot-benchmark/timescaledb/target/iot-benchmark-timescaledb/iot-benchmark-timescaledb/benchmark.sh" ] || \
   [ ! -f "$PWD/iot-benchmark/iotdb-1.3/target/iot-benchmark-iotdb-1.3/iot-benchmark-iotdb-1.3/benchmark.sh" ]; then
  echo "[+] Building iot-benchmark modules (first time setup)..."
  (
    cd "$PWD/iot-benchmark"
    mvn -pl influxdb-2.0,timescaledb,iotdb-1.3 -am package -DskipTests -U
    find . -path "*/target/*" -name "*.sh" \
      -exec sed -i 's|#!/bin/bash\b|#!/usr/bin/env bash|g' {} +
  )
  echo "[+] Build complete."
else
  echo "[+] iot-benchmark already built, skipping."
fi

echo "======================================================================="
echo " TCC IoT Benchmark — dev shell                                         "
echo "======================================================================="
echo "  python3 benchmark.py                       run all DBs, small scale  "
echo "  python3 benchmark.py --scale medium        medium scale (~30 min)    "
echo "  python3 benchmark.py --scale large         large scale (~2 h)        "
echo "  python3 benchmark.py --db iotdb            iotdb only                "
echo "  python3 benchmark.py --test write          write only                "
echo "  python3 charts.py                          all sources, en-us        "
echo "  python3 charts.py --source medium          single source             "
echo "  python3 charts.py --language pt-br         portuguese labels         "
echo "-----------------------------------------------------------------------"
echo "  nix run .#fmt                              format files              "
echo "  nix run .#thesis                           compile thesis            "
echo "  nix run .#slides-pdf                       export all slides to PDF  "
echo "======================================================================="
