#!/usr/bin/env python3
import sys
import os
import time
import argparse
import subprocess
import urllib.request
import urllib.error

import benchrunner.config as cfg
from benchrunner import influxdb, timescaledb, iotdb, metrics

ALL_TESTS = [
    'batch-small', 'batch-large', 'out-of-order', 'write',
    'read', 'latest-point', 'downsample', 'range-query', 'value-filter',
]


def _wait_ready(service: str, timeout: int = 90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if service == 'influxdb':
                urllib.request.urlopen('http://localhost:8086/health', timeout=2)
                return
            elif service == 'timescaledb':
                r = subprocess.run(
                    ['docker', 'exec', 'timescaledb', 'pg_isready', '-U', 'postgres'],
                    capture_output=True,
                )
                if r.returncode == 0:
                    return
            elif service == 'iotdb':
                r = subprocess.run(
                    ['docker', 'exec', 'iotdb',
                     '/iotdb/sbin/start-cli.sh', '-h', '127.0.0.1', '-p', '6667',
                     '-u', 'root', '-pw', 'root', '-e', 'show version'],
                    capture_output=True, timeout=10,
                )
                if r.returncode == 0:
                    return
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError(f'{service} did not become ready within {timeout}s')


def start_db(service: str):
    print(f'[+] Starting {service}...')
    subprocess.run(['docker', 'compose', 'up', '-d', service], check=True)
    _wait_ready(service)
    print(f'[+] {service} is ready.')


def stop_db(service: str):
    print(f'[+] Stopping {service}...')
    subprocess.run(['docker', 'compose', 'stop', service], check=True)


def main():
    parser = argparse.ArgumentParser(description='Time-Series Database Benchmark Runner')
    parser.add_argument('--db', choices=['all', 'influxdb', 'timescaledb', 'iotdb'], default='all')
    parser.add_argument('--test', choices=['all'] + ALL_TESTS, default='all')

    parser.add_argument(
        '--scale', choices=['small', 'medium', 'large'], default='small',
        help='small ~2 min | medium ~10 min | large ~1 h  (default: small)',
    )

    args = parser.parse_args()

    cfg.current_scale = args.scale

    db_funcs = {
        'influxdb':    influxdb.run,
        'timescaledb': timescaledb.run,
        'iotdb':       iotdb.run,
    }

    dbs   = list(db_funcs.keys()) if args.db == 'all' else [args.db]
    tests = ALL_TESTS if args.test == 'all' else [args.test]

    print('\n==================================================')
    print(f' Scale:     {cfg.current_scale.upper()}')
    print(f' Databases: {", ".join(dbs)}')
    print(f' Tests:     {", ".join(tests)}')
    print('==================================================')

    for db in dbs:
        start_db(db)
        try:
            for t in tests:
                print(f'\n--- {db.upper()} → {t.upper()} ---')
                try:
                    db_funcs[db](t)
                except Exception as e:
                    print(f'[!] Benchmark failed for {db} ({t}): {e}')
                    sys.exit(1)
        finally:
            stop_db(db)

    metrics.print_summary()

    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results', f'{args.scale}.csv')
    metrics.write_csv(csv_path)


if __name__ == '__main__':
    main()
