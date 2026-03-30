import os
import re
import subprocess

def update_config(work_mode):
    config_path = "iot-benchmark/iotdb-1.3/target/iot-benchmark-iotdb-1.3/iot-benchmark-iotdb-1.3/conf/config.properties"
    if not os.path.exists(config_path):
        print(f"[!] IoT-Benchmark config not found at {config_path}")
        print("    Did you compile the iot-benchmark tool?")
        return False
        
    print(f"[*] Updating IoT-Benchmark config to work_mode={work_mode}")
    with open(config_path, 'r') as f:
        content = f.read()
        
    props = {
        'DB_SWITCH': 'IoTDB-130-SESSION_BY_TABLET',
        'HOST': '127.0.0.1',
        'PORT': '6667',
        'USERNAME': 'root',
        'PASSWORD': 'root',
        'BENCHMARK_WORK_MODE': work_mode,
        'DEVICE_NUMBER': '100',
        'SENSOR_NUMBER': '10',
        'DATA_TYPE': 'DOUBLE',
        'LOOP': '155',
        'CLIENT_NUMBER': '10',
        'BATCH_SIZE_PER_WRITE': '100',
        'CSV_OUTPUT': 'true'
    }
    
    for k, v in props.items():
        if re.search(f"^{k}=.*$", content, flags=re.MULTILINE):
            content = re.sub(f"^{k}=.*$", f"{k}={v}", content, flags=re.MULTILINE)
        else:
            content += f"\n{k}={v}\n"
    
    with open(config_path, 'w') as f:
        f.write(content)
    return True

def run(work_mode):
    if not update_config(work_mode):
        return
        
    cwd = "iot-benchmark/iotdb-1.3/target/iot-benchmark-iotdb-1.3/iot-benchmark-iotdb-1.3"
    print(f"[*] Running IoT-Benchmark for Apache IoTDB ({work_mode})...")
    
    cmd = ["./benchmark.sh"]
    subprocess.run(cmd, cwd=cwd, check=True)
