#!/bin/bash
set -euo pipefail

: "${ORACLE_APP_PASSWORD:?ORACLE_APP_PASSWORD is required}"
: "${APP_RW_PASSWORD:?APP_RW_PASSWORD is required}"
: "${AUTH_R_PASSWORD:?AUTH_R_PASSWORD is required}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'oracle_readonly') THEN
    CREATE ROLE oracle_readonly NOLOGIN;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'auth_readonly') THEN
    CREATE ROLE auth_readonly NOLOGIN;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'oracle_app') THEN
    CREATE USER oracle_app WITH PASSWORD '${ORACLE_APP_PASSWORD}';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'auth_app') THEN
    CREATE USER auth_app WITH PASSWORD '${AUTH_R_PASSWORD}';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rw') THEN
    CREATE USER app_rw WITH PASSWORD '${APP_RW_PASSWORD}';
  END IF;
END
\$\$;

GRANT oracle_readonly TO oracle_app;
GRANT auth_readonly TO auth_app;

ALTER ROLE oracle_app SET default_transaction_read_only = on;
ALTER ROLE oracle_app SET statement_timeout = '15s';
ALTER ROLE oracle_app SET idle_in_transaction_session_timeout = '30s';

ALTER ROLE auth_app SET default_transaction_read_only = on;
ALTER ROLE auth_app SET statement_timeout = '15s';
ALTER ROLE auth_app SET idle_in_transaction_session_timeout = '30s';

GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO oracle_app;
GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO auth_app;
GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO app_rw;
SQL