SCALES = {
    # ~1-2 min:  low schema, low loop count
    'small':  {'CLIENT_NUMBER': '5',  'DEVICE_NUMBER': '10', 'SENSOR_NUMBER': '10', 'BATCH_SIZE_PER_WRITE': '100', 'LOOP': '1000'},
    # ~10 min:   same schema, 5× more loops
    'medium': {'CLIENT_NUMBER': '5',  'DEVICE_NUMBER': '10', 'SENSOR_NUMBER': '10', 'BATCH_SIZE_PER_WRITE': '100', 'LOOP': '5000'},
    # ~1 hour:   10× more series + 5× more loops
    'large':  {'CLIENT_NUMBER': '10', 'DEVICE_NUMBER': '50', 'SENSOR_NUMBER': '20', 'BATCH_SIZE_PER_WRITE': '100', 'LOOP': '5000'},
}

CONFIG = {
    # InfluxDB
    'influx_host':   'localhost',
    'influx_port':   '8086',
    'influx_token':  'my-super-secret-auth-token',
    'influx_org':    'my-org',
    'influx_bucket': 'my-bucket',

    # TimescaleDB
    'timescale_host': 'localhost',
    'timescale_port': '5432',
    'timescale_user': 'postgres',
    'timescale_pass': 'postgrespassword123',
    'timescale_db':   'timescaledb',
}

current_scale = 'small'

def get_scale_params():
    return SCALES[current_scale]
