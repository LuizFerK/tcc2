import sys
import subprocess
import re
import threading
import time
import os

RESULTS = []

def get_docker_cores():
    try:
        res = subprocess.run(["docker", "info", "--format", "{{.NCPU}}"], capture_output=True, text=True)
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
            val = float(re.search(r"[\d\.]+", mem_str).group())
            if "GiB" in mem_str or "GB" in mem_str:
                return val * 1024
            elif "MiB" in mem_str or "MB" in mem_str:
                return val
            elif "KiB" in mem_str or "KB" in mem_str:
                return val / 1024
            elif "B" in mem_str:
                return val / (1024 * 1024)
            return val
        except:
            return 0.0

    def _monitor_loop(self):
        while self.running:
            try:
                res = subprocess.run(
                    ["docker", "stats", self.container_name, "--no-stream", "--format", "{{.CPUPerc}},{{.MemUsage}}"],
                    capture_output=True, text=True
                )
                if res.returncode == 0:
                    output = res.stdout.strip()
                    if output and "," in output:
                        parts = output.split(',')
                        if len(parts) == 2:
                            cpu_str = parts[0].replace('%', '').strip()
                            mem_str = parts[1].split('/')[0].strip()
                            raw_cpu = float(cpu_str) if cpu_str else 0.0
                            self.cpu_samples.append(raw_cpu / DOCKER_CORES)
                            self.mem_samples_mb.append(self._parse_mem(mem_str))
            except Exception:
                pass
            time.sleep(1)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            # Let the thread finish its last sleep cycle
            self.thread.join(timeout=2)
            
    def get_metrics(self):
        avg_cpu = sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0.0
        peak_cpu = max(self.cpu_samples) if self.cpu_samples else 0.0
        avg_mem = sum(self.mem_samples_mb) / len(self.mem_samples_mb) if self.mem_samples_mb else 0.0
        peak_mem = max(self.mem_samples_mb) if self.mem_samples_mb else 0.0
        return f"{avg_cpu:.1f}%", f"{peak_cpu:.1f}%", f"{avg_mem:.1f} MB", f"{peak_mem:.1f} MB"


def run_and_capture(db_name, test_type, cmd, cwd=None):
    print(f"\n[>>>] Running: {cmd}")
    
    monitor = DockerMonitor(db_name.lower())
    monitor.start()

    process = subprocess.Popen(
        cmd, shell=True, cwd=cwd,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    
    output_lines = []
    for line in process.stdout:
        sys.stdout.write(line)
        output_lines.append(line)
        
    process.wait()
    monitor.stop()
    
    avg_cpu, peak_cpu, avg_mem, peak_mem = monitor.get_metrics()
    
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd)
        
    output = "".join(output_lines)
    parse_metrics(db_name, test_type, output, avg_cpu, peak_cpu, avg_mem, peak_mem)


def parse_metrics(db_name, test_type, output, avg_cpu, peak_cpu, avg_mem, peak_mem):
    metric = {
        "DB": db_name.upper(), 
        "Test": test_type.upper(), 
        "Time (s)": "N/A", 
        "Rate": "N/A",
        "Avg CPU": avg_cpu,
        "Peak CPU": peak_cpu,
        "Avg Mem": avg_mem,
        "Peak Mem": peak_mem
    }
    
    if test_type == "write" and db_name in ["influxdb", "timescaledb"]:
        m = re.search(r"loaded\s+\d+\s+metrics in\s+([\d\.]+)sec\s+.*\(mean rate\s+([\d\.]+)\s+metrics/sec\)", output)
        if m:
            metric["Time (s)"] = m.group(1)
            metric["Rate"] = m.group(2) + " metrics/s"
            
    elif test_type == "read" and db_name in ["influxdb", "timescaledb"]:
        m = re.search(r"wall clock time:\s*([\d\.]+)\s*sec", output)
        if m:
            metric["Time (s)"] = m.group(1)
            
    elif db_name == "iotdb":
        m_rate = re.search(r"(INGESTION|PRECISE_POINT|TIME_RANGE)\s+\d+\s+\d+\s+\d+\s+\d+\s+([\d\.]+)", output)
        if m_rate:
             metric["Rate"] = m_rate.group(2) + " points/s"
             
        m_time = re.search(r"Cost Time:\s*([\d\.]+)\s*s", output, re.IGNORECASE)
        if m_time:
             metric["Time (s)"] = m_time.group(1)
        else:
             m_time2 = re.search(r"cost\s+([\d\.]+)\s*seconds", output, re.IGNORECASE)
             if m_time2: metric["Time (s)"] = m_time2.group(1)

    RESULTS.append(metric)


def print_summary():
    print("\n" + "="*115)
    print(f"{'DATABASE':<15} | {'TEST':<8} | {'TIME (s)':<10} | {'RATE':<20} | {'AVG CPU':<9} | {'PEAK CPU':<9} | {'AVG MEM':<10} | {'PEAK MEM':<10}")
    print("-" * 115)
    for r in RESULTS:
        print(f"{r['DB']:<15} | {r['Test']:<8} | {r['Time (s)']:<10} | {r['Rate']:<20} | {r['Avg CPU']:<9} | {r['Peak CPU']:<9} | {r['Avg Mem']:<10} | {r['Peak Mem']:<10}")
    print("="*115 + "\n")
