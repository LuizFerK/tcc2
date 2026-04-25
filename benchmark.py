#!/usr/bin/env python3
import sys
import argparse
import subprocess

from benchrunner.config import CONFIG
from benchrunner import influxdb, timescaledb, iotdb, metrics


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
    parser.add_argument('--test', choices=['all', 'write', 'read'], default='all')

    scale_group = parser.add_mutually_exclusive_group()
    scale_group.add_argument('--small',  action='store_true',
                             help='5 clients · 10 devices · 10 sensors · 1000 ops  (default)')
    scale_group.add_argument('--medium', action='store_true',
                             help='10 clients · 50 devices · 20 sensors · 5000 ops')
    scale_group.add_argument('--large',  action='store_true',
                             help='20 clients · 100 devices · 50 sensors · 10000 ops')

    args = parser.parse_args()

    if args.medium:
        CONFIG['scale'] = 'medium'
    elif args.large:
        CONFIG['scale'] = 'large'
    else:
        CONFIG['scale'] = 'small'

    db_funcs = {
        'influxdb':    {'write': influxdb.write,    'read': influxdb.read},
        'timescaledb': {'write': timescaledb.write, 'read': timescaledb.read},
        'iotdb':       {'write': iotdb.write,       'read': iotdb.read},
    }

    dbs   = list(db_funcs.keys()) if args.db == 'all' else [args.db]
    tests = ['write', 'read']     if args.test == 'all' else [args.test]

    ensure_docker_running()

    print('\n==================================================')
    print(f' Scale:     {CONFIG["scale"].upper()}')
    print(f' Databases: {", ".join(dbs)}')
    print(f' Tests:     {", ".join(tests)}')
    print('==================================================')

    for db in dbs:
        for t in tests:
            print(f'\n--- {db.upper()} → {t.upper()} ---')
            try:
                db_funcs[db][t]()
            except Exception as e:
                print(f'[!] Benchmark failed for {db} ({t}): {e}')
                sys.exit(1)

    metrics.print_summary()


if __name__ == '__main__':
    main()
