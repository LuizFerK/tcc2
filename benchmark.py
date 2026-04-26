#!/usr/bin/env python3
import sys
import os
import argparse
import subprocess

import benchrunner.config as cfg
from benchrunner import influxdb, timescaledb, iotdb, metrics

ALL_TESTS = [
    'batch-small', 'batch-large', 'out-of-order', 'write',
    'read', 'latest-point', 'downsample', 'range-query', 'value-filter',
]


def ensure_docker_running():
    running = subprocess.run(
        ['docker', 'compose', 'ps', '--services', '--filter', 'status=running'],
        capture_output=True, text=True,
    ).stdout.strip().splitlines()
    needed = {'iotdb', 'influxdb', 'timescaledb'}
    if not needed.issubset(set(running)):
        print('[+] Starting databases via docker compose...')
        subprocess.run(['docker', 'compose', 'up', '-d'], check=True)
    else:
        print('[+] All database containers already running.')


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

    ensure_docker_running()

    print('\n==================================================')
    print(f' Scale:     {cfg.current_scale.upper()}')
    print(f' Databases: {", ".join(dbs)}')
    print(f' Tests:     {", ".join(tests)}')
    print('==================================================')

    for db in dbs:
        for t in tests:
            print(f'\n--- {db.upper()} → {t.upper()} ---')
            try:
                db_funcs[db](t)
            except Exception as e:
                print(f'[!] Benchmark failed for {db} ({t}): {e}')
                sys.exit(1)

    metrics.print_summary()

    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results', f'{args.scale}.csv')
    metrics.write_csv(csv_path)


if __name__ == '__main__':
    main()
