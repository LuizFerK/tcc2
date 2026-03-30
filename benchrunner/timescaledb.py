from benchrunner.config import CONFIG
from benchrunner import tsbs

def write():
    extra_args = [
        f"--host={CONFIG['timescale_host']}",
        f"--port={CONFIG['timescale_port']}",
        f"--user={CONFIG['timescale_user']}",
        f"--pass={CONFIG['timescale_pass']}"
    ]
    tsbs.load("timescaledb", "tsbs_load_timescaledb", extra_args)

def read():
    extra_args = [
        f"--hosts={CONFIG['timescale_host']}",
        f"--port={CONFIG['timescale_port']}",
        f"--user={CONFIG['timescale_user']}",
        f"--pass={CONFIG['timescale_pass']}"
    ]
    tsbs.run_queries("timescaledb", "tsbs_run_queries_timescaledb", extra_args)
