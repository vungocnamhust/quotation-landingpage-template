#!/bin/bash
set -e

# Creates the separate notification database on the shared PostgreSQL instance
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE notification'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'notification')\gexec
    GRANT ALL PRIVILEGES ON DATABASE notification TO "$POSTGRES_USER";
EOSQL
