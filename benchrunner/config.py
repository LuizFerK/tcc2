CONFIG = {
    'seed': 123,
    'scale': 100,
    'timestamp_start': "2023-01-01T00:00:00Z",
    'timestamp_end': "2023-01-02T00:00:00Z",
    'log_interval': "10s",
    'use_case': "iot",
    'query_type': "high-load",
    'workers': 4,
    
    # InfluxDB overrides
    'influx_urls': "http://localhost:8086",
    'influx_token': "my-super-secret-auth-token",
    'influx_org': "my-org",
    
    # TimescaleDB overrides
    'timescale_host': "localhost",
    'timescale_port': "5432",
    'timescale_user': "postgres",
    'timescale_pass': "postgrespassword123",
}
