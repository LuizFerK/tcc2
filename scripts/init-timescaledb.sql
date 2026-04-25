-- Re-hash password as MD5 for compatibility with the old JDBC driver
-- bundled in iot-benchmark's timescaledb module (postgresql-9.1-901.jdbc4.jar).
-- Without this, auth type 10 (SCRAM-SHA-256) is sent and the driver rejects it.
SET password_encryption = 'md5';
ALTER USER postgres WITH PASSWORD 'postgrespassword123';
