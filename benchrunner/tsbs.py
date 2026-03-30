import os
import subprocess
from benchrunner.config import CONFIG

def generate_data(fmt):
    out_file = f"/tmp/{fmt}-data.gz"
    print(f"[*] Generating TSBS data for {fmt} -> {out_file}")
    cmd = (
        f"tsbs_generate_data "
        f"--use-case={CONFIG['use_case']} "
        f"--seed={CONFIG['seed']} "
        f"--scale={CONFIG['scale']} "
        f"--timestamp-start={CONFIG['timestamp_start']} "
        f"--timestamp-end={CONFIG['timestamp_end']} "
        f"--log-interval={CONFIG['log_interval']} "
        f"--format={fmt} | gzip > {out_file}"
    )
    subprocess.run(cmd, shell=True, check=True)
    return out_file

def load(fmt, load_cmd, extra_args):
    data_file = f"/tmp/{fmt}-data.gz"
    if not os.path.exists(data_file):
        print(f"[!] Data file {data_file} not found. Generating first...")
        generate_data(fmt)
        
    print(f"[*] Loading TSBS data for {fmt} using {load_cmd}")
    cmd = f"zcat {data_file} | {load_cmd} --workers={CONFIG['workers']} " + " ".join(extra_args)
    subprocess.run(cmd, shell=True, check=True)

def generate_queries(fmt):
    out_file = f"/tmp/{fmt}-queries.gz"
    print(f"[*] Generating TSBS queries for {fmt} -> {out_file}")
    cmd = (
        f"tsbs_generate_queries "
        f"--use-case={CONFIG['use_case']} "
        f"--seed={CONFIG['seed']} "
        f"--scale={CONFIG['scale']} "
        f"--timestamp-start={CONFIG['timestamp_start']} "
        f"--timestamp-end={CONFIG['timestamp_end']} "
        f"--format={fmt} "
        f"--query-type={CONFIG['query_type']} | gzip > {out_file}"
    )
    subprocess.run(cmd, shell=True, check=True)
    return out_file

def run_queries(fmt, run_cmd_name, extra_args):
    query_file = f"/tmp/{fmt}-queries.gz"
    if not os.path.exists(query_file):
        print(f"[!] Query file {query_file} not found. Generating first...")
        generate_queries(fmt)
        
    print(f"[*] Running TSBS queries for {fmt} using {run_cmd_name}")
    cmd = f"zcat {query_file} | {run_cmd_name} --workers={CONFIG['workers']} " + " ".join(extra_args)
    subprocess.run(cmd, shell=True, check=True)
