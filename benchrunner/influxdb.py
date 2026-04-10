import subprocess
from benchrunner.config import CONFIG
from benchrunner import tsbs

def pre_flight():
    print("[*] Running InfluxDB pre-flight DBRP mapping...")
    try:
        res = subprocess.run([
            "docker", "exec", "influxdb", "influx", "bucket", "list",
            "--org", CONFIG['influx_org'],
            "--token", CONFIG['influx_token']
        ], capture_output=True, text=True, check=True)
        
        bucket_id = None
        for line in res.stdout.splitlines():
            if "my-bucket" in line:
                bucket_id = line.split()[0]
                break
                
        if not bucket_id:
            print("[!] Could not find 'my-bucket'. Returning...")
            return

        try:
           subprocess.run([
                "docker", "exec", "influxdb", "influx", "v1", "dbrp", "create",
                "--db", "benchmark",
                "--rp", "autogen",
                "--bucket-id", bucket_id,
                "--default",
                "--org", CONFIG['influx_org'],
                "--token", CONFIG['influx_token']
           ], capture_output=True, text=True, check=True)
           print("[*] DBRP mapping created successfully.")
        except subprocess.CalledProcessError as e:
           if "exists" in e.stderr:
               print("[*] DBRP mapping already exists.")
           else:
               print(f"[!] Warning: DBRP mapping creation failed: {e.stderr}")
    except Exception as e:
        print(f"[!] Pre-flight failed: {e}")

def write():
    pre_flight()
    extra_args = [
        f"--urls={CONFIG['influx_urls']}",
        f"--auth-token={CONFIG['influx_token']}"
    ]
    tsbs.load("influxdb", "influx", "tsbs_load_influx", extra_args)

def read():
    extra_args = [
        f"--urls={CONFIG['influx_urls']}",
        f"--auth-token={CONFIG['influx_token']}"
    ]
    tsbs.run_queries("influxdb", "influx", "tsbs_run_queries_influx", extra_args)
