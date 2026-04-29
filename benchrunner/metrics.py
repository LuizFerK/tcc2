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
        return avg_cpu, peak_cpu, avg_mem, peak_mem


def update_properties_file(path, props):
    if not os.path.exists(path):
        print(f'[!] Config not found at {path}')
        print('    Run: nix run .#build')
        return False
    with open(path) as f:
        content = f.read()
    for k, v in props.items():
        if re.search(f'^{k}=', content, re.M):
            content = re.sub(f'^{k}=.*$', f'{k}={v}', content, flags=re.M)
        else:
            content += f'\n{k}={v}'
    with open(path, 'w') as f:
        f.write(content)
    return True


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
    result = {}
    m = re.search(r'Result Matrix[-]+\n(.+?)(?=\n[-]{10,})', output, re.S)
    if not m:
        return result
    for line in m.group(1).splitlines():
        parts = line.split()
        if len(parts) >= 6:
            try:
                name, ok_op, ok_pt, tput = parts[0], int(parts[1]), int(parts[2]), float(parts[5])
                result[name] = (ok_op, ok_pt, tput)
            except (ValueError, IndexError):
                pass
    return result


def _parse_latency_matrix(output):
    result = {}
    m = re.search(r'Latency \(ms\) Matrix[-]+\n(.+?)(?=\n[-]{10,})', output, re.S)
    if not m:
        return result
    for line in m.group(1).splitlines():
        parts = line.split()
        # columns: op AVG MIN P10 P25 MEDIAN P75 P90 P95 P99 P999 MAX SLOWEST
        if len(parts) >= 10:
            try:
                result[parts[0]] = (float(parts[1]), float(parts[9]))
            except (ValueError, IndexError):
                pass
    return result


def _parse_elapsed(output):
    m = re.search(r'Test elapsed time.*?:\s*([\d.]+)\s*second', output, re.I)
    return float(m.group(1)) if m else None


def _parse_and_store(db_name, test_type, output, avg_cpu, peak_cpu, avg_mem, peak_mem):
    res_matrix = _parse_result_matrix(output)
    lat_matrix = _parse_latency_matrix(output)
    elapsed    = _parse_elapsed(output)

    if test_type in WRITE_TESTS:
        row = res_matrix.get('INGESTION', (0, 0, 0.0))
        lat = lat_matrix.get('INGESTION', (0.0, 0.0))
        throughput = row[2]
        avg_lat_ms = lat[0]
        p99_lat_ms = lat[1]
    else:
        active = {op: v for op, v in res_matrix.items() if op in READ_OPS and v[0] > 0}
        throughput = sum(v[2] for v in active.values())
        if active:
            avg_lat_ms = sum(lat_matrix[op][0] for op in active if op in lat_matrix) / len(active)
            p99_lat_ms = max((lat_matrix[op][1] for op in active if op in lat_matrix), default=0.0)
        else:
            avg_lat_ms = p99_lat_ms = 0.0

    RESULTS.append({
        'db':           db_name.upper(),
        'test':         test_type.upper(),
        'time_s':       elapsed,
        'throughput':   throughput,
        'avg_lat_ms':   avg_lat_ms,
        'p99_lat_ms':   p99_lat_ms,
        'avg_cpu_pct':  avg_cpu,
        'peak_cpu_pct': peak_cpu,
        'avg_mem_mb':   avg_mem,
        'peak_mem_mb':  peak_mem,
    })


def _format_result(r):
    return {
        'DB':         r['db'],
        'Test':       r['test'],
        'Time (s)':   str(r['time_s']) if r['time_s'] is not None else 'N/A',
        'Throughput': f"{r['throughput']:.2f} pts/s",
        'Avg Lat':    f"{r['avg_lat_ms']:.2f} ms",
        'P99 Lat':    f"{r['p99_lat_ms']:.2f} ms",
        'Avg CPU':    f"{r['avg_cpu_pct']:.1f}%",
        'Peak CPU':   f"{r['peak_cpu_pct']:.1f}%",
        'Avg Mem':    f"{r['avg_mem_mb']:.1f} MB",
        'Peak Mem':   f"{r['peak_mem_mb']:.1f} MB",
    }


def print_summary():
    cols = ['DB', 'Test', 'Time (s)', 'Throughput', 'Avg Lat', 'P99 Lat', 'Avg CPU', 'Peak CPU', 'Avg Mem', 'Peak Mem']
    rows = [_format_result(r) for r in RESULTS]
    widths = {c: max(len(c), max((len(str(row[c])) for row in rows), default=0)) for c in cols}

    header = '| ' + ' | '.join(f'{c:<{widths[c]}}' for c in cols) + ' |'
    sep    = '|' + '|'.join('-' * (widths[c] + 2) for c in cols) + '|'

    print('\n' + header)
    print(sep)
    for row in rows:
        print('| ' + ' | '.join(f'{str(row[c]):<{widths[c]}}' for c in cols) + ' |')
    print()


def write_csv(path):
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
                r['db'], r['test'], r['time_s'] or 0,
                r['throughput'], r['avg_lat_ms'], r['p99_lat_ms'],
                r['avg_cpu_pct'], r['peak_cpu_pct'], r['avg_mem_mb'], r['peak_mem_mb'],
            ])
    print(f'[+] Results written to {path}')
