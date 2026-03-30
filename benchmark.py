#!/usr/bin/env python3
import sys
import argparse
from benchrunner.config import CONFIG
from benchrunner import influxdb, timescaledb, iotdb

def main():
    parser = argparse.ArgumentParser(description="Time-Series Database Benchmark Runner")
    parser.add_argument("--db", choices=["all", "influxdb", "timescaledb", "iotdb"], default="all",
                        help="Which database to benchmark")
    parser.add_argument("--test", choices=["all", "write", "read"], default="all",
                        help="Which test to run (write/ingestion or read/aggregation)")
    
    parser.add_argument("--scale", type=int, help="Override the scale parameter")
    parser.add_argument("--seed", type=int, help="Override the seed parameter")
    parser.add_argument("--workers", type=int, help="Override worker count")
    
    args = parser.parse_args()
    
    if args.scale: CONFIG['scale'] = args.scale
    if args.seed: CONFIG['seed'] = args.seed
    if args.workers: CONFIG['workers'] = args.workers

    db_funcs = {
        "influxdb": {"write": influxdb.write, "read": influxdb.read},
        "timescaledb": {"write": timescaledb.write, "read": timescaledb.read},
        "iotdb": {"write": iotdb.write, "read": iotdb.read}
    }

    dbs_to_run = list(db_funcs.keys()) if args.db == "all" else [args.db]
    tests_to_run = ["write", "read"] if args.test == "all" else [args.test]

    print("==================================================")
    print(" Starting Benchmarks")
    print(f" Databases: {', '.join(dbs_to_run)}")
    print(f" Tests:     {', '.join(tests_to_run)}")
    print("==================================================")

    for db in dbs_to_run:
        for t in tests_to_run:
            print(f"\n--- Running {db.upper()} -> {t.upper()} ---")
            try:
                db_funcs[db][t]()
            except Exception as e:
                print(f"[!] Benchmark failed for {db} ({t}): {e}")
                sys.exit(1)

if __name__ == "__main__":
    main()
