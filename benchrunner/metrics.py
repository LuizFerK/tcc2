import sys
import subprocess
import re
import threading
import time
import os

RESULTS = []

WRITE_TESTS = {'write', 'out-of-order', 'batch-small', 'batch-large'}

READ_OPS = {
    'PRECISE_POINT', 'TIME_RANGE', 'VALUE_RANGE',
    'AGG_RANGE', 'AGG_VALUE', 'AGG_RANGE_VALUE',
    'GROUP_BY', 'LATEST_POINT',
    'RANGE_QUERY_DESC', 'VALUE_RANGE_QUERY_DESC', 'GROUP_BY_DESC',
}

def get_docker_cores():
    try:
        res = subprocess.run(['docker', 'info', '--format', '{{.NCPU}}'], capture_output=True, text=True)
        return int(res.stdout.strip())
    except Exception:
        return os.cpu_count() or 1

DOCKER_CORES = get_docker_cores()


class DockerMonitor:
    def __init__(self, container_name):
        self.container_name = container_name
        self.running = False
        self.cpu_samples = []
        self.mem_samples_mb = []
        self.thread = None

    def _parse_mem(self, mem_str):
        try:
            val = float(re.search(r'[\d.]+', mem_str).group())
            if 'GiB' in mem_str or 'GB' in mem_str:
                return val * 1024
            elif 'MiB' in mem_str or 'MB' in mem_str:
                return val
            elif 'KiB' in mem_str or 'KB' in mem_str:
                return val / 1024
            return val / (1024 * 1024)
        except Exception:
            return 0.0

    def _monitor_loop(self):
        while self.running:
            try:
                res = subprocess.run(
                    ['docker', 'stats', self.container_name, '--no-stream',
                     '--format', '{{.CPUPerc}},{{.MemUsage}}'],
                    capture_output=True, text=True,
                )
                if res.returncode == 0:
                    line = res.stdout.strip()
                    if line and ',' in line:
                        cpu_s, mem_s = line.split(',', 1)
                        raw_cpu = float(cpu_s.replace('%', '').strip() or 0)
                        self.cpu_samples.append(raw_cpu / DOCKER_CORES)
                        self.mem_samples_mb.append(self._parse_mem(mem_s.split('/')[0].strip()))
            except Exception:
                pass
            time.sleep(1)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=3)

    def get_metrics(self):
        avg_cpu  = sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0.0
        peak_cpu = max(self.cpu_samples) if self.cpu_samples else 0.0
        avg_mem  = sum(self.mem_samples_mb) / len(self.mem_samples_mb) if self.mem_samples_mb else 0.0
        peak_mem = max(self.mem_samples_mb) if self.mem_samples_mb else 0.0
        return f'{avg_cpu:.1f}%', f'{peak_cpu:.1f}%', f'{avg_mem:.1f} MB', f'{peak_mem:.1f} MB'


def run_and_capture(db_name, test_type, cmd, cwd=None):
    print(f'\n[>>>] {cmd}  (cwd: {cwd})')
    monitor = DockerMonitor(db_name.lower())
    monitor.start()

    process = subprocess.Popen(
        cmd, shell=True, cwd=cwd,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    lines = []
    for line in process.stdout:
        sys.stdout.write(line)
        lines.append(line)
    process.wait()
    monitor.stop()

    avg_cpu, peak_cpu, avg_mem, peak_mem = monitor.get_metrics()

    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd)

    _parse_and_store(db_name, test_type, ''.join(lines), avg_cpu, peak_cpu, avg_mem, peak_mem)


def _parse_result_matrix(output):
    """Return dict: operation_name -> (ok_ops, ok_points, throughput)"""
    result = {}
    # Find the Result Matrix section
    m = re.search(r'Result Matrix[-]+\n(.+?)(?=\n[-]{10,})', output, re.S)
    if not m:
        return result
    for line in m.group(1).splitlines():
        parts = line.split()
        if len(parts) >= 6:
            try:
                name, ok_op, ok_pt, fail_op, fail_pt, tput = parts[0], int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]), float(parts[5])
                result[name] = (ok_op, ok_pt, tput)
            except (ValueError, IndexError):
                pass
    return result


def _parse_latency_matrix(output):
    """Return dict: operation_name -> (avg_ms, p99_ms)"""
    result = {}
    m = re.search(r'Latency \(ms\) Matrix[-]+\n(.+?)(?=\n[-]{10,})', output, re.S)
    if not m:
        return result
    for line in m.group(1).splitlines():
        parts = line.split()
        # columns: op AVG MIN P10 P25 MEDIAN P75 P90 P95 P99 P999 MAX SLOWEST
        if len(parts) >= 10:
            try:
                name = parts[0]
                avg_ms = float(parts[1])
                p99_ms = float(parts[9])
                result[name] = (avg_ms, p99_ms)
            except (ValueError, IndexError):
                pass
    return result


def _parse_elapsed(output):
    m = re.search(r'Test elapsed time.*?:\s*([\d.]+)\s*second', output, re.I)
    return m.group(1) if m else 'N/A'


def _parse_and_store(db_name, test_type, output, avg_cpu, peak_cpu, avg_mem, peak_mem):
    res_matrix = _parse_result_matrix(output)
    lat_matrix = _parse_latency_matrix(output)
    elapsed    = _parse_elapsed(output)

    if test_type in WRITE_TESTS:
        row = res_matrix.get('INGESTION', (0, 0, 0.0))
        lat = lat_matrix.get('INGESTION', (0.0, 0.0))
        throughput = f'{row[2]:.2f} pts/s'
        avg_lat    = f'{lat[0]:.2f} ms'
        p99_lat    = f'{lat[1]:.2f} ms'
    else:
        active = {op: v for op, v in res_matrix.items() if op in READ_OPS and v[0] > 0}
        total_tput = sum(v[2] for v in active.values())
        throughput = f'{total_tput:.2f} pts/s'
        if active:
            avg_lat_val = sum(lat_matrix[op][0] for op in active if op in lat_matrix) / len(active)
            p99_lat_val = max((lat_matrix[op][1] for op in active if op in lat_matrix), default=0.0)
        else:
            avg_lat_val = p99_lat_val = 0.0
        avg_lat = f'{avg_lat_val:.2f} ms'
        p99_lat = f'{p99_lat_val:.2f} ms'

    RESULTS.append({
        'DB':         db_name.upper(),
        'Test':       test_type.upper(),
        'Time (s)':   elapsed,
        'Throughput': throughput,
        'Avg Lat':    avg_lat,
        'P99 Lat':    p99_lat,
        'Avg CPU':    avg_cpu,
        'Peak CPU':   peak_cpu,
        'Avg Mem':    avg_mem,
        'Peak Mem':   peak_mem,
    })


def print_summary():
    cols = ['DB', 'Test', 'Time (s)', 'Throughput', 'Avg Lat', 'P99 Lat', 'Avg CPU', 'Peak CPU', 'Avg Mem', 'Peak Mem']
    widths = {c: max(len(c), max((len(str(r[c])) for r in RESULTS), default=0)) for c in cols}

    sep = '+' + '+'.join('-' * (widths[c] + 2) for c in cols) + '+'
    header = '|' + '|'.join(f' {c:<{widths[c]}} ' for c in cols) + '|'

    print('\n' + sep)
    print(header)
    print(sep)
    for r in RESULTS:
        print('|' + '|'.join(f' {str(r[c]):<{widths[c]}} ' for c in cols) + '|')
    print(sep + '\n')


def _parse_float(s):
    """Extract the leading float from a formatted string like '9.12 ms' or '2.5%'."""
    try:
        return float(re.search(r'[\d.]+', str(s)).group())
    except (AttributeError, ValueError):
        return 0.0


def write_csv(path):
    """Write RESULTS to a CSV file compatible with charts.py."""
    import csv
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'db', 'test', 'time_s',
            'throughput_pts_s', 'avg_lat_ms', 'p99_lat_ms',
            'avg_cpu_pct', 'peak_cpu_pct', 'avg_mem_mb', 'peak_mem_mb',
        ])
        for r in RESULTS:
            writer.writerow([
                r['DB'],
                r['Test'],
                _parse_float(r['Time (s)']),
                _parse_float(r['Throughput']),
                _parse_float(r['Avg Lat']),
                _parse_float(r['P99 Lat']),
                _parse_float(r['Avg CPU']),
                _parse_float(r['Peak CPU']),
                _parse_float(r['Avg Mem']),
                _parse_float(r['Peak Mem']),
            ])
    print(f'[+] Results written to {path}')
