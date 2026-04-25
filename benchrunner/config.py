SCALES = {
    'small':  {'CLIENT_NUMBER': '5',  'DEVICE_NUMBER': '10',  'SENSOR_NUMBER': '10', 'BATCH_SIZE_PER_WRITE': '100', 'LOOP': '1000'},
    'medium': {'CLIENT_NUMBER': '10', 'DEVICE_NUMBER': '50',  'SENSOR_NUMBER': '20', 'BATCH_SIZE_PER_WRITE': '100', 'LOOP': '5000'},
    'large':  {'CLIENT_NUMBER': '20', 'DEVICE_NUMBER': '100', 'SENSOR_NUMBER': '50', 'BATCH_SIZE_PER_WRITE': '100', 'LOOP': '10000'},
}

CONFIG = {
    'scale': 'small',

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

def get_scale_params():
    return SCALES[CONFIG['scale']]
